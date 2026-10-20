"""Integridad, comparabilidad y consolidación: Cuenta de Inversión (Cuadro 35), Boletín Fiscal y puente."""
from decimal import Decimal

from conftest import FIX

from observatorio import metodologia, metrics, puente, sync
from observatorio.ingest import boletin_fiscal as bf
from observatorio.ingest import cuenta_inversion as ci
from observatorio.ingest.base import run_ingestion

C35 = FIX / "cuadro35-tomoi-2025.xlsx"
BOL = FIX / "boletin-4t2025-paginas.pdf"
CGN_PDF = FIX / "cgn-metodologia-spnf-2025.pdf"
M = 100_000_000  # centavos por millón

# IMIG real 2025 (resultado primario y financiero, M$), tal como figura en imig-mensual.csv el 2026-10-19.
IMIG_2025 = {
    "01": ("2434865.299999999", "599753.1999999988"), "02": ("1176915.3000000007", "310726.20000000077"),
    "03": ("745339.4999999981", "398909.2999999981"), "04": ("845949.0999999996", "572340.9999999997"),
    "05": ("1696917.3999999966", "662122.8999999968"), "06": ("790532.9000000004", "551234.2000000004"),
    "07": ("1749385.5000000019", "-168515.19999999832"), "08": ("1556864.0000000037", "390300.5000000035"),
    "09": ("696965.1000000015", "309623.40000000154"), "10": ("823924.8000000007", "517671.7000000007"),
    "11": ("2128009.399999995", "599953.7999999947"), "12": ("-2876449.600000005", "-3290301.900000005"),
}


def load_c35(con, path=C35):
    d = ci.cuadro35_def(2025)
    return run_ingestion(con, d, ci.make_loader(2025, d), local_file=path)


def load_bol(con, path=BOL):
    d = bf.dataset_def(2025, 4)
    return run_ingestion(con, d, bf.make_loader(2025, 4, d), local_file=path)


def cell(con, celda):
    return con.execute("SELECT importe_centavos, importe_original, estado FROM aif_observation WHERE celda=?",
                       (celda,)).fetchone()


def ci_val(con, concepto, sub):
    return con.execute("SELECT importe_centavos FROM aif_observation WHERE concepto_id=? AND subsector=?",
                       (concepto, sub)).fetchone()[0]


def insert_imig(con, data=IMIG_2025):
    con.execute("INSERT OR IGNORE INTO source VALUES ('t','t','t',NULL,NULL,NULL)")
    con.execute("INSERT OR IGNORE INTO dataset VALUES ('imig_mensual','t','t','t','t','nacional',NULL,NULL,'M$',NULL)")
    run = con.execute("INSERT INTO ingestion_run (dataset_id, started_at, status, url) VALUES "
                      "('imig_mensual','x','ok','x')").lastrowid
    for mes, (rp, rf) in data.items():
        for sid, v in (("imig.resultado_primario", rp), ("imig.resultado_financiero", rf)):
            con.execute("INSERT INTO series_observation VALUES (?,?,?,?,?,?)",
                        (sid, "imig_mensual", run, f"2025-{mes}", v, "M$"))
    con.commit()


def insert_pa_sintetico(con, ingresos, rentas, gastos, intereses):
    """Presupuesto Abierto 2025 SINTÉTICO (4 líneas) con los totales dados, para probar el puente sin
    cargar los 113 mil registros reales. Las pruebas con datos reales están en test_integration_real."""
    con.execute("INSERT OR IGNORE INTO source VALUES ('t','t','t',NULL,NULL,NULL)")
    con.execute("INSERT OR IGNORE INTO dimension_entity VALUES ('AN/2025/1','x','nacional','x',NULL,NULL,2025)")
    for ds in ("pa_credito_anual_2025", "pa_recursos_anual_2025"):
        con.execute("INSERT OR IGNORE INTO dataset VALUES (?, 't','t','t','Administración Nacional','nacional',"
                    "NULL,NULL,'M$',NULL)", (ds,))
    run = con.execute("INSERT INTO ingestion_run (dataset_id, started_at, status, url) VALUES "
                      "('pa_credito_anual_2025','x','ok','x')").lastrowid
    lines = [("pa_recursos_anual_2025", "recurso", "percibido", None, "16", rentas),
             ("pa_recursos_anual_2025", "recurso", "percibido", None, "11", ingresos - rentas),
             ("pa_credito_anual_2025", "gasto", "devengado", "21310000", None, intereses),
             ("pa_credito_anual_2025", "gasto", "devengado", "21110000", None, gastos - intereses)]
    for i, (ds, flujo, etapa, eco, tipo, v) in enumerate(lines):
        con.execute("INSERT INTO fiscal_observation (dataset_id, run_id, source_line, ejercicio, periodo, flujo, etapa, "
                    "entity_id, economico, recurso_tipo, importe_centavos, importe_original) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (ds, run, i + 2, 2025, "2025", flujo, etapa, "AN/2025/1", eco, tipo, v, "sintético"))
    con.commit()


def pa_igual_a_ci(con):
    insert_pa_sintetico(con, ci_val(con, "VI", "total_an"), ci_val(con, "I.rentas_de_la_propiedad", "total_an"),
                        ci_val(con, "VII", "total_an"), ci_val(con, puente.INTERESES_CI, "total_an"))


# ---------- Integridad: Cuadro 35 ----------

def test_cuadro35_conserva_valores_y_no_inventa_ceros(env):
    res = load_c35(env)
    assert res["status"] == "ok" and res["rows"] == 580
    assert "2 celdas con error" in res["fecha_publicacion"]
    assert cell(env, "E56")[0] == 13481299232352140              # 134.812.992.323.521,40 $
    assert cell(env, "E56")[1] == "134812992323521.4"            # repr del valor del archivo
    for c in ("K52", "K53"):                                      # '#REF!' en el archivo oficial
        assert tuple(cell(env, c)) == (None, "#REF!", "error_formula")
    assert tuple(cell(env, "F27")) == (None, None, "vacia")       # vacía: NULL, nunca 0
    assert cell(env, "D47")[0] == 8669574                         # 86.695,74 $: montos chicos exactos


def test_cuadro35_identidades_y_discrepancias_del_original(env):
    load_c35(env)
    rows = env.execute("SELECT comparacion, diferencia_centavos, conclusion FROM reconciliation "
                       "WHERE comparacion LIKE 'ci35:2025:%'").fetchall()
    bad = {r[0]: r[1] for r in rows if r[2] != "coincide"}
    # Discrepancia real del archivo oficial (0,81 $): se informa, no se corrige.
    assert bad == {f"ci35:2025:XIV [{s}] = −XI (el financiamiento neto cubre el resultado)": 81
                   for s in ("adm_central", "total_an", "total_spnf")}
    assert sum(r[2] == "coincide" for r in rows) >= 170


def test_cuadro35_consolidacion(env):
    load_c35(env)
    subs = ("total_an", "universidades", "empresas", "fondos_fiduciarios", "entes_publicos")
    for concepto in ("VI", "VII", "I.transferencias_corrientes", "II.transferencias_corrientes", "IX", "X"):
        total = sum(ci_val(env, concepto, s) or 0 for s in subs) - (ci_val(env, concepto, "eliminaciones") or 0)
        assert abs(total - ci_val(env, concepto, "total_spnf")) <= ci.TOLERANCIA_CENTAVOS, concepto
    # Las figurativas se eliminan por completo: no quedan en el consolidado.
    assert ci_val(env, "IX", "total_spnf") == 0 and ci_val(env, "X", "total_spnf") == 0
    assert ci_val(env, "IX", "eliminaciones") == ci_val(env, "X", "eliminaciones")
    # La consolidación no altera resultados: el SPNF es la suma de los resultados de los subsectores.
    rf = sum(ci_val(env, "XI", s) for s in subs)
    assert abs(rf - ci_val(env, "XI", "total_spnf")) <= ci.TOLERANCIA_CENTAVOS
    assert ci_val(env, "III", "eliminaciones") == 0
    inst = puente.institucional(env, 2025)
    filas = {f["subsector"]: f for f in inst["filas"]}
    rp = sum(Decimal(filas[s]["resultado_primario"]) for s in subs)
    assert abs(rp - Decimal(filas["total_spnf"]["resultado_primario"])) < Decimal("0.000001")
    assert inst["universo"] == "Sector Público Nacional no Financiero" and "No es el resultado oficial" in inst["advertencia"]


def test_cuadro35_cambio_de_estructura_falla_y_conserva_lo_anterior(env, tmp_path):
    import openpyxl
    assert load_c35(env)["status"] == "ok"
    p = tmp_path / "c35.xlsx"
    wb = openpyxl.load_workbook(C35)
    wb.active["G6"] = "Bancos"
    wb.save(p)
    res = load_c35(env, p)
    assert res["status"] == "failed" and "columna G" in res["error"]
    assert cell(env, "E56")[0] == 13481299232352140


# ---------- Boletín Fiscal ----------

def test_boletin_extrae_cifras_del_pdf(env):
    res = load_bol(env)
    assert res["status"] == "ok" and res["rows"] == len(bf.BOLETINES[(2025, 4)].figuras)
    f = dict(env.execute("SELECT figure_id, valor_texto FROM published_figure").fetchall())
    assert f["an_caja.rentas_bcra"] == "11.976.386,7"
    assert f["spn_caja.resultado_primario"] == "11.769.218,7"
    assert f["an_caja.resultado_financiero"] == "-2.367.044,8"
    line = env.execute("SELECT linea_texto, pagina FROM published_figure WHERE figure_id='an_caja.rentas_bcra'").fetchone()
    assert "PERCIBIDAS DEL BCRA" in line[0] and line[1] == 62


def test_boletin_estructura_inesperada_falla(env, monkeypatch):
    b = bf.BOLETINES[(2025, 4)]
    roto = bf.Boletin(**{**b.__dict__, "marcas": {**b.marcas, 62: ("CUADRO 99",)}})
    monkeypatch.setitem(bf.BOLETINES, (2025, 4), roto)
    res = load_bol(env)
    assert res["status"] == "failed" and "cambió la estructura" in res["error"]
    assert env.execute("SELECT COUNT(*) FROM published_figure").fetchone()[0] == 0


# ---------- Metodología ----------

def test_citas_metodologicas_verificadas_en_crudo(env, monkeypatch):
    load_bol(env)
    run_ingestion(env, ci.metodologia_def(2025), ci.load_documento, local_file=CGN_PDF)
    estados = {r["nota_id"]: r["estado_verificacion"] for r in metodologia.refresh(env)}
    for n in metodologia.NOTAS:
        assert estados[n.nota_id] == ("verificada_en_crudo" if n.cita else "hallazgo_reproducible"), n.nota_id
    falsa = metodologia.Nota("falsa", tema="x", aplica_a="x", resumen="x", fuente_url="x", ubicacion="x",
                             cita="El BCRA no transfirió utilidades en 2025.", dataset=metodologia.BOLETIN)
    monkeypatch.setattr(metodologia, "NOTAS", metodologia.NOTAS + (falsa,))
    assert {r["nota_id"]: r["estado_verificacion"] for r in metodologia.refresh(env)}["falsa"] == "no_encontrada_en_crudo"


def test_citas_sin_crudo_no_se_dan_por_verificadas(env):
    estados = {r["estado_verificacion"] for r in metodologia.refresh(env)}
    assert "verificada_en_crudo" not in estados and "crudo_no_disponible" in estados


def test_advertencia_pagado_no_lo_llama_deuda_flotante():
    assert "No es el saldo de deuda flotante" in metrics.ADV_PAGADO
    assert "la diferencia es deuda flotante" not in metrics.ADV_PAGADO


# ---------- Puente ----------

def _escenario_completo(env):
    load_c35(env)
    load_bol(env)
    pa_igual_a_ci(env)
    insert_imig(env)


def test_puente_cierra_solo_con_cifras_publicadas(env):
    _escenario_completo(env)
    p = puente.puente(env, 2025)
    assert p["estado"] == "ok"
    assert all(c["estado"] == "coincide" for c in p["controles"]), p["controles"]
    for clave, llegada in (("resultado_primario", "11769218.7"), ("resultado_financiero", "1453819.1")):
        pasos = p[clave]
        assert Decimal(pasos[-1]["acumulado_millones"]) == Decimal(llegada)
        assert not any("advertencia" in s for s in pasos)
        assert [s for s in pasos if s["tipo"] == "residual"][0]["categoria"] == "base contable"
        assert all(s["tipo"] in p["tipos"] for s in pasos)
    cat = {s["categoria"]: s["valor_millones"] for s in p["resultado_primario"]}
    assert Decimal(cat["rentas de la propiedad: BCRA (criterio metodológico)"]) == Decimal("-11976386.7")
    assert Decimal(cat["base contable"]) == Decimal("553705.6")
    assert Decimal(cat["institucional"]) == Decimal("3879450.7")
    # La diferencia de base es igual en el primario y en el financiero: los intereses no tienen diferencia de base.
    rf_base = [s for s in p["resultado_financiero"] if s["tipo"] == "residual"][0]["valor_millones"]
    assert Decimal(rf_base) == Decimal(cat["base contable"])


def test_puente_no_fuerza_la_conciliacion(env):
    load_c35(env)
    load_bol(env)
    pa_igual_a_ci(env)
    alterado = dict(IMIG_2025)
    alterado["06"] = ("791532.9", alterado["06"][1])  # +1.000 M$ en junio
    insert_imig(env, alterado)
    p = puente.puente(env, 2025)
    ctrl = {c["control"]: c for c in p["controles"]}
    llegada = ctrl["Llegada del puente = resultado primario del IMIG (suma de 12 meses)"]
    assert llegada["estado"] == "discrepa" and Decimal(llegada["diferencia_millones"]) == Decimal("-1000")
    # Las cifras publicadas del puente no se tocaron.
    assert p["resultado_primario"][-1]["valor_millones"] == "11769218.7"


def test_puente_partida_distinta_de_ci_se_informa(env):
    load_c35(env)
    load_bol(env)
    insert_pa_sintetico(env, ci_val(env, "VI", "total_an") + 5 * M, 0, ci_val(env, "VII", "total_an"),
                        ci_val(env, puente.INTERESES_CI, "total_an"))
    insert_imig(env)
    ctrl = puente.puente(env, 2025)["controles"][0]
    assert ctrl["control"].startswith("Partida") and ctrl["estado"] == "discrepa"


def test_puente_sin_fuentes_no_disponible(env):
    load_c35(env)
    p = puente.puente(env, 2025)
    assert p["estado"] == "no_disponible" and "Boletín Fiscal 4º trimestre" in p["faltan"]


def test_cruce_presupuesto_abierto_vs_cuenta_de_inversion(env):
    load_c35(env)
    pa_igual_a_ci(env)
    assert all(r["conclusion"] == "coincide" for r in sync.reconcile_cuenta_inversion(env, 2025))
    env.execute("UPDATE fiscal_observation SET importe_centavos = importe_centavos + 1000 WHERE economico='21110000'")
    res = {r["comparacion"].split(":")[2]: r for r in sync.reconcile_cuenta_inversion(env, 2025)}
    assert res["gastos totales (devengado)"]["conclusion"] == "discrepa"
    assert res["intereses (económico 2131*)"]["conclusion"] == "coincide"


def test_conciliacion_pa_totales_no_borra_otros_cruces(env):
    load_c35(env)
    pa_igual_a_ci(env)
    sync.reconcile_cuenta_inversion(env, 2025)
    sync.reconcile(env, 2025)
    n = env.execute("SELECT COUNT(*) FROM reconciliation WHERE comparacion LIKE 'cruce:2025:%'").fetchone()[0]
    assert n == len(sync.CRUCE_CI)


# ---------- Comparabilidad: universos separados ----------

def test_cada_paso_y_vista_declara_universo_y_base(env):
    _escenario_completo(env)
    p = puente.puente(env, 2025)
    puntos = [s for s in p["resultado_primario"] if s["tipo"].startswith("punto")]
    assert {s["universo"] for s in puntos} == {"Administración Nacional", "Sector Público Nacional"}
    assert all(s["base"] for s in puntos)
    rentas = p["comparacion_rentas"]
    assert len({(r["fuente"], r["universo"], r["base"]) for r in rentas}) == len(rentas)


def test_api_puente_cuenta_inversion_metodologia(env, monkeypatch):
    from fastapi.testclient import TestClient
    from observatorio.api import app
    _escenario_completo(env)
    metodologia.refresh(env)
    c = TestClient(app)
    b = c.get("/api/bridge", params={"ejercicio": 2025}).json()
    assert b["estado"] == "ok" and isinstance(b["resultado_primario"][0]["valor_millones"], str)
    i = c.get("/api/cuenta-inversion", params={"ejercicio": 2025}).json()
    assert i["estado"] == "ok" and len(i["filas"]) == 10 and len(i["celdas_con_error"]) == 2
    assert len(c.get("/api/metodologia").json()) == len(metodologia.NOTAS)
    rec = c.get("/api/reconciliation", params={"prefix": "ci35:2025:"}).json()
    assert rec and all(isinstance(r["diferencia_centavos"], (str, type(None))) for r in rec)
