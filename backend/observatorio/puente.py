"""Puente cuantificado entre el resultado de la Administración Nacional (Presupuesto Abierto) y el
resultado oficial base caja del Sector Público Nacional (IMIG).

Cada paso es una cifra publicada, la diferencia entre dos cifras publicadas o un residual. Nada
se ajusta para que cierre: los controles comparan cifras publicadas por separado y, si no
coinciden, el puente lo informa. Fuentes:
  * Presupuesto Abierto (cierre, AN, percibido/devengado)          -> fiscal_observation
  * Cuenta de Inversión, Cuadro 35 (SPNF por subsector, devengado) -> aif_observation
  * Boletín Fiscal 4º trimestre (AN devengado provisorio y SPN caja) -> published_figure
  * IMIG (SPN caja)                                                -> series_observation
"""
from __future__ import annotations

import sqlite3
from decimal import Decimal

from .ingest import imig
from .metrics import provenance
from .money import centavos_to_millones
from .sync import INTERESES_PREFIX

# Las cifras del Boletín y del IMIG vienen redondeadas a 0,1 M$ (= 10.000.000 centavos).
UNIDAD_PUB = 10_000_000
INTERESES_CI = "II.intereses_y_otras_rentas_de_la_propiedad.intereses"
SUBSECTORES = (
    ("adm_central", "Administración Central"), ("org_descentralizados", "Organismos descentralizados"),
    ("inst_seguridad_social", "Instituciones de seguridad social"), ("total_an", "Total Administración Nacional"),
    ("universidades", "Universidades nacionales"), ("empresas", "Empresas públicas"),
    ("fondos_fiduciarios", "Fondos fiduciarios"), ("entes_publicos", "Entes públicos"),
    ("eliminaciones", "Eliminaciones de consolidación"), ("total_spnf", "Total SPNF"),
)


# Rótulos cortos para gráficos (el concepto completo va en la tabla).
ROTULOS = {
    "Resultado primario AN — cierre": "AN cierre", "Resultado financiero AN — cierre": "AN cierre",
    "Resultado primario AN — detalle de Presupuesto Abierto": "AN (PA)",
    "Resultado financiero AN — detalle de Presupuesto Abierto": "AN (PA)",
    "Revisión entre el corte provisorio del Boletín y el cierre": "Revisión de corte",
    "Resultado primario AN — corte provisorio": "AN provisorio", "Resultado financiero AN — corte provisorio": "AN provisorio",
    "Caja vs. devengado y otras diferencias de registro dentro de la AN (no descompuesto)": "Base caja (residual)",
    "Resultado primario AN base caja, con todas las rentas": "AN caja",
    "Resultado financiero AN base caja, con rentas e intereses brutos": "AN caja",
    "Se excluyen las rentas percibidas del BCRA": "− Rentas BCRA",
    "Se excluyen las rentas cobradas por el FGS y otros a otros entes públicos": "− Rentas FGS",
    "Se excluyen los intereses que la AN paga a otros entes públicos": "+ Intereses intra-SP",
    "Resultado primario AN base caja, nueva metodología": "AN caja s/rentas",
    "Resultado financiero AN base caja, nueva metodología": "AN caja s/rentas",
    "Aporte de INSSJyP, fondos fiduciarios, otros entes y empresas (por su resultado operativo)": "+ Resto SPN",
    "Resultado primario SPN base caja (IMIG)": "SPN caja (IMIG)",
    "Resultado financiero SPN base caja (IMIG)": "SPN caja (IMIG)",
}


def _m(c: int | None) -> str | None:
    return None if c is None else str(centavos_to_millones(c))


def _pa(con, ej):
    dg, dr = f"pa_credito_anual_{ej}", f"pa_recursos_anual_{ej}"
    if con.execute("SELECT 1 FROM fiscal_observation WHERE dataset_id=? LIMIT 1", (dg,)).fetchone() is None:
        return None

    def s(ds, etapa, extra="", args=()):
        return con.execute(f"SELECT COALESCE(SUM(importe_centavos),0) FROM fiscal_observation WHERE dataset_id=? "
                           f"AND etapa=? {extra}", (ds, etapa, *args)).fetchone()[0]
    ing, gas = s(dr, "percibido"), s(dg, "devengado")
    intr = s(dg, "devengado", "AND economico LIKE ?", (INTERESES_PREFIX + "%",))
    return {"ingresos": ing, "gastos": gas, "intereses": intr, "gasto_primario": gas - intr,
            "rentas": s(dr, "percibido", "AND recurso_tipo='16'"),
            "resultado_primario": ing - (gas - intr), "resultado_financiero": ing - gas}


def ci35(con, ej) -> dict[tuple[str, str], int | None] | None:
    rows = con.execute("SELECT concepto_id, subsector, importe_centavos FROM aif_observation WHERE dataset_id=?",
                       (f"cgn_ci_{ej}_cuadro35",)).fetchall()
    return {(r[0], r[1]): r[2] for r in rows} or None


def _bol(con, ej) -> dict[str, int] | None:
    rows = con.execute("SELECT figure_id, importe_centavos FROM published_figure WHERE dataset_id=?",
                       (f"onp_boletin_{ej}_t4",)).fetchall()
    return {r[0]: r[1] for r in rows} or None


def _imig(con, ej) -> dict[str, int] | None:
    meses = [r[0] for r in con.execute(
        "SELECT periodo FROM series_observation WHERE series_id='imig.resultado_primario' AND periodo LIKE ? "
        "AND valor_original IS NOT NULL", (f"{ej}-%",))]
    if len(meses) != 12:
        return None

    def tot(cols):
        t = Decimal(0)
        for c in cols:
            vals = [imig.to_dec(r[0]) for r in con.execute(
                "SELECT valor_original FROM series_observation WHERE series_id=? AND periodo LIKE ?",
                (f"imig.{c}", f"{ej}-%")) if r[0] is not None]
            if len(vals) != 12:
                return None
            t += sum(vals)
        return int(t * 100_000_000)
    return {"resultado_primario": tot(["resultado_primario"]), "resultado_financiero": tot(["resultado_financiero"]),
            "ingresos": tot(list(imig.INGRESOS)),
            "rentas": tot([c for c, (g, _) in imig.INGRESOS.items() if g == "rentas"])}


def _check(nombre, a, b, tol, nota=None):
    if a is None or b is None:
        return {"control": nombre, "estado": "sin_dato", "diferencia_millones": None, "nota": nota}
    d = a - b
    return {"control": nombre, "estado": "coincide" if abs(d) <= tol else "discrepa",
            "diferencia_millones": _m(d), "tolerancia_millones": _m(tol), "nota": nota}


def _cadena(pasos):
    """Acumula: los 'punto' fijan el nivel; los demás suman. Marca si un punto no coincide con lo acumulado."""
    acc, out = None, []
    for p in pasos:
        if p["tipo"].startswith("punto"):
            if acc is not None and p["valor"] is not None and abs(acc - p["valor"]) > UNIDAD_PUB:
                p["advertencia"] = f"lo acumulado ({_m(acc)}) no coincide con el punto publicado"
            acc = p["valor"]
        elif p["valor"] is not None and acc is not None:
            acc += p["valor"]
        out.append({k: x for k, x in p.items() if k != "valor"}
                   | {"valor_millones": _m(p["valor"]), "acumulado_millones": _m(acc)})
    return out


def puente(con: sqlite3.Connection, ej: int) -> dict:
    pa, ci, bol, im = _pa(con, ej), ci35(con, ej), _bol(con, ej), _imig(con, ej)
    prov = [provenance(con, d) for d in (f"pa_credito_anual_{ej}", f"pa_recursos_anual_{ej}",
                                          f"cgn_ci_{ej}_cuadro35", f"onp_boletin_{ej}_t4", "imig_mensual")]
    faltan = [n for n, v in (("Presupuesto Abierto (cierre)", pa), ("Cuenta de Inversión, Cuadro 35", ci),
                             ("Boletín Fiscal 4º trimestre", bol), ("IMIG con 12 meses", im)) if v is None]
    if pa is None or bol is None or im is None:
        return {"estado": "no_disponible", "ejercicio": ej, "faltan": faltan, "procedencia": prov,
                "motivo": "El puente cuantificado necesita el cierre de Presupuesto Abierto, el Boletín Fiscal del "
                          "4º trimestre y los 12 meses del IMIG del mismo ejercicio."}

    # El detalle de PA solo se llama "cierre" si la Cuenta de Inversión del mismo año lo confirma.
    es_cierre = ci is not None
    corte = "cierre" if es_cierre else "detalle de Presupuesto Abierto"
    n_corte = ["cortes_an_2025"] if ej == 2025 else ([] if es_cierre else ["cortes_an_sin_ci"])
    n_bcra = ["caja_spn_2017_rentas_intra_sp"] + (["bcra_utilidades_2025"] if ej == 2025 else [])
    n_rentas_dev = ["boletin_2022_rentas_emisiones_primarias"] if ej == 2022 else []
    rp_caja_con_rentas = bol["an_caja.resultado_primario_sin_rentas"] + bol["an_caja.rentas_bcra"] + bol["an_caja.rentas_fgs_y_otros"]
    rf_caja_bruto = (bol["an_caja.resultado_financiero"] + bol["an_caja.rentas_bcra"] + bol["an_caja.rentas_fgs_y_otros"]
                     - bol["an_caja.intereses_intra_sp"])
    PA, B1, B5, IM = ("Presupuesto Abierto (credito/recursos-anual)", "Boletín Fiscal 4T, cuadro 1",
                      "Boletín Fiscal 4T, cuadro 5", "IMIG")

    def paso(tipo, categoria, concepto, valor, fuente, notas=(), universo=None, base=None):
        return {"tipo": tipo, "categoria": categoria, "concepto": concepto, "valor": valor, "fuente": fuente,
                "notas": list(notas), "universo": universo, "base": base, "rotulo": ROTULOS.get(concepto, categoria)}

    primario = _cadena([
        paso("punto_calculado", "punto de partida", f"Resultado primario AN — {corte}", pa["resultado_primario"], PA,
             ["an_metodologia_habitual"], "Administración Nacional", "percibido / devengado"),
        paso("diferencia_derivada", "corte de publicación (revisión)",
             "Revisión entre el corte provisorio del Boletín y el cierre",
             bol["an_dev.resultado_primario"] - pa["resultado_primario"], f"{B1} − {PA}", n_corte),
        paso("punto_publicado", "punto intermedio", "Resultado primario AN — corte provisorio",
             bol["an_dev.resultado_primario"], B1, [], "Administración Nacional", "recaudado / devengado"),
        paso("residual", "base contable",
             "Caja vs. devengado y otras diferencias de registro dentro de la AN (no descompuesto)",
             rp_caja_con_rentas - bol["an_dev.resultado_primario"], f"{B5} − {B1}",
             ["boletin_momentos_registro", "deuda_exigible_no_es_flotante"] + n_rentas_dev),
        paso("punto_derivado", "punto intermedio", "Resultado primario AN base caja, con todas las rentas",
             rp_caja_con_rentas, f"{B5}: resultado sin rentas + rentas BCRA + rentas FGS y otros", [],
             "Administración Nacional", "caja"),
        paso("ajuste_publicado", "rentas de la propiedad: BCRA (criterio metodológico)",
             "Se excluyen las rentas percibidas del BCRA", -bol["an_caja.rentas_bcra"], B5,
             n_bcra),
        paso("ajuste_publicado", "operaciones intra-sector público: rentas del FGS y otros",
             "Se excluyen las rentas cobradas por el FGS y otros a otros entes públicos",
             -bol["an_caja.rentas_fgs_y_otros"], B5, ["caja_spn_2017_rentas_intra_sp"]),
        paso("punto_publicado", "punto intermedio", "Resultado primario AN base caja, nueva metodología",
             bol["an_caja.resultado_primario_sin_rentas"], B5, [], "Administración Nacional", "caja"),
        paso("ajuste_publicado", "institucional",
             "Aporte de INSSJyP, fondos fiduciarios, otros entes y empresas (por su resultado operativo)",
             bol["resto_caja.resultado_primario"], B5, ["universo_imig_vs_ci"]),
        paso("punto_publicado", "punto de llegada", "Resultado primario SPN base caja (IMIG)",
             bol["spn_caja.resultado_primario"], B5, [], "Sector Público Nacional", "caja"),
    ])
    financiero = _cadena([
        paso("punto_calculado", "punto de partida", f"Resultado financiero AN — {corte}", pa["resultado_financiero"], PA,
             ["an_metodologia_habitual"], "Administración Nacional", "percibido / devengado"),
        paso("diferencia_derivada", "corte de publicación (revisión)",
             "Revisión entre el corte provisorio del Boletín y el cierre",
             bol["an_dev.resultado_financiero"] - pa["resultado_financiero"], f"{B1} − {PA}", n_corte),
        paso("punto_publicado", "punto intermedio", "Resultado financiero AN — corte provisorio",
             bol["an_dev.resultado_financiero"], B1, [], "Administración Nacional", "recaudado / devengado"),
        paso("residual", "base contable",
             "Caja vs. devengado y otras diferencias de registro dentro de la AN (no descompuesto)",
             rf_caja_bruto - bol["an_dev.resultado_financiero"], f"{B5} − {B1}", ["boletin_momentos_registro"]),
        paso("punto_derivado", "punto intermedio", "Resultado financiero AN base caja, con rentas e intereses brutos",
             rf_caja_bruto, f"{B5}: resultado + rentas BCRA + rentas FGS − intereses intra-SP", [],
             "Administración Nacional", "caja"),
        paso("ajuste_publicado", "rentas de la propiedad: BCRA (criterio metodológico)",
             "Se excluyen las rentas percibidas del BCRA", -bol["an_caja.rentas_bcra"], B5,
             n_bcra),
        paso("ajuste_publicado", "operaciones intra-sector público: rentas del FGS y otros",
             "Se excluyen las rentas cobradas por el FGS y otros a otros entes públicos",
             -bol["an_caja.rentas_fgs_y_otros"], B5, ["caja_spn_2017_rentas_intra_sp"]),
        paso("ajuste_publicado", "operaciones intra-sector público: intereses",
             "Se excluyen los intereses que la AN paga a otros entes públicos", bol["an_caja.intereses_intra_sp"], B5,
             ["caja_spn_2017_rentas_intra_sp"]),
        paso("punto_publicado", "punto intermedio", "Resultado financiero AN base caja, nueva metodología",
             bol["an_caja.resultado_financiero"], B5, [], "Administración Nacional", "caja"),
        paso("ajuste_publicado", "institucional",
             "Aporte de INSSJyP, fondos fiduciarios, otros entes y empresas (por su resultado operativo)",
             bol["resto_caja.resultado_financiero"], B5, ["universo_imig_vs_ci"]),
        paso("punto_publicado", "punto de llegada", "Resultado financiero SPN base caja (IMIG)",
             bol["spn_caja.resultado_financiero"], B5, [], "Sector Público Nacional", "caja"),
    ])
    T = UNIDAD_PUB
    # 12 meses redondeados a 0,1 M$ contra un total anual redondeado: hasta 13 medias unidades.
    T_IMIG = 13 * T // 2
    nota_imig = "Tolerancia 0,65 M$: suma de 12 cifras mensuales redondeadas a 0,1 M$ contra un total redondeado."
    controles = [
        _check("Llegada del puente = resultado primario del IMIG (suma de 12 meses)",
               bol["spn_caja.resultado_primario"], im["resultado_primario"], T_IMIG, nota_imig),
        _check("Llegada del puente = resultado financiero del IMIG (suma de 12 meses)",
               bol["spn_caja.resultado_financiero"], im["resultado_financiero"], T_IMIG, nota_imig),
        _check("Boletín: AN + resto = SPN (resultado primario, publicados por separado)",
               bol["an_caja.resultado_primario_sin_rentas"] + bol["resto_caja.resultado_primario"],
               bol["spn_caja.resultado_primario"], 2 * T),
        _check("Rentas AN: netas de caja + BCRA + FGS y otros = rentas devengadas del cuadro 1",
               bol["an_caja.rentas_netas"] + bol["an_caja.rentas_bcra"] + bol["an_caja.rentas_fgs_y_otros"],
               bol["an_dev.rentas_propiedad"], 3 * T,
               "Si coincide, las rentas no tienen diferencia de base: todo el residual de base está en otros rubros."),
        _check("Intereses AN: netos de caja + intra-SP = intereses devengados del cuadro 1",
               bol["an_caja.intereses_netos"] + bol["an_caja.intereses_intra_sp"], bol["an_dev.intereses"], 2 * T,
               "Si coincide, el residual de base del resultado financiero es igual al del primario."),
        _check("Intereses intra-SP pagados = rentas cobradas por el FGS y otros (AN + resto, ambos lados)",
               bol["an_caja.intereses_intra_sp"] + bol["resto_caja.intereses_intra_sp"],
               bol["an_caja.rentas_fgs_y_otros"] + bol.get("resto_caja.rentas_fgs_y_otros", 0), 4 * T,
               "Las dos caras de la misma operación intra-sector público (columna total del cuadro 5)."),
    ]
    if ci is not None:
        ci_rp = (None if None in (ci.get(("XI", "total_an")), ci.get((INTERESES_CI, "total_an")))
                 else ci[("XI", "total_an")] + ci[(INTERESES_CI, "total_an")])
        controles.insert(0, _check("Partida: resultado primario AN de Presupuesto Abierto = Cuenta de Inversión "
                                   "(Cuadro 35, columna AN)", pa["resultado_primario"], ci_rp, 100,
                                   "Tolerancia 1 $: el xlsx guarda los importes en doble precisión."))
    return {
        "estado": "ok", "ejercicio": ej, "unidad": "millones de pesos corrientes", "partida_es_cierre": es_cierre,
        "resultado_primario": primario, "resultado_financiero": financiero, "controles": controles,
        "tipos": {
            "punto_calculado": "Calculado desde los archivos de Presupuesto Abierto",
            "punto_publicado": "Cifra publicada tal cual",
            "punto_derivado": "Suma de cifras publicadas",
            "ajuste_publicado": "Cifra publicada que la metodología excluye o agrega",
            "diferencia_derivada": "Diferencia entre dos cifras publicadas (revisión entre cortes)",
            "residual": "Diferencia no descompuesta: las fuentes disponibles no la abren por concepto",
        },
        "comparacion_rentas": _rentas(pa, ci, bol, im),
        "faltan": faltan, "procedencia": prov,
    }


def _rentas(pa, ci, bol, im):
    def row(fuente, universo, base, c, nota=None):
        return {"fuente": fuente, "universo": universo, "base": base, "valor_millones": _m(c),
                "estado": "ok" if c is not None else "sin_datos", "nota": nota}
    return [
        row("Presupuesto Abierto (cierre)", "Administración Nacional", "percibido", pa["rentas"]),
        row("Cuenta de Inversión, Cuadro 35", "Administración Nacional", "percibido",
            ci.get(("I.rentas_de_la_propiedad", "total_an")) if ci else None),
        row("Boletín Fiscal 4T, cuadro 1", "Administración Nacional", "percibido (provisorio)",
            bol["an_dev.rentas_propiedad"]),
        row("Cuenta de Inversión, Cuadro 35", "Sector Público Nacional no Financiero", "percibido/devengado",
            ci.get(("I.rentas_de_la_propiedad", "total_spnf")) if ci else None,
            "Incluye universidades, empresas, fondos fiduciarios y entes."),
        row("Boletín Fiscal 4T, cuadro 5 / IMIG", "Sector Público Nacional", "caja, sin BCRA ni FGS",
            im["rentas"], "Rentas netas: sin rentas del BCRA ni del FGS (metodología 2017)."),
    ]


def institucional(con: sqlite3.Connection, ej: int) -> dict:
    """Cuenta AIF del SPNF por subsector (Cuenta de Inversión, Cuadro 35). Devengado; no es el IMIG."""
    ci = ci35(con, ej)
    prov = [provenance(con, f"cgn_ci_{ej}_cuadro35")]
    if ci is None:
        return {"estado": "sin_datos", "ejercicio": ej, "procedencia": prov}

    def v(cid, sub):
        return ci.get((cid, sub))

    filas = []
    for sub, nombre in SUBSECTORES:
        rf, intr = v("XI", sub), v(INTERESES_CI, sub)
        filas.append({
            "subsector": sub, "nombre": nombre,
            "ingresos_totales": _m(v("VI", sub)), "gastos_totales": _m(v("VII", sub)),
            "intereses": _m(intr), "rentas_propiedad": _m(v("I.rentas_de_la_propiedad", sub)),
            "resultado_primario": _m(None if rf is None or (intr is None and sub != "eliminaciones")
                                     else rf + (intr or 0)),
            "resultado_financiero": _m(rf),
            "contribuciones_figurativas": _m(v("IX", sub)), "gastos_figurativos": _m(v("X", sub)),
        })
    errores = [dict(r) for r in con.execute(
        "SELECT celda, concepto, subsector, importe_original FROM aif_observation WHERE dataset_id=? "
        "AND estado='error_formula'", (f"cgn_ci_{ej}_cuadro35",))]
    rec = con.execute("SELECT conclusion, COUNT(*) FROM reconciliation WHERE comparacion LIKE ? GROUP BY 1",
                      (f"ci35:{ej}:%",)).fetchall()
    return {
        "estado": "ok", "ejercicio": ej, "universo": "Sector Público Nacional no Financiero",
        "base": "devengado (gastos) / percibido (recursos); transferencias intra-SPNF devengadas",
        "unidad": "millones de pesos corrientes (el archivo está en pesos)", "filas": filas,
        "identidades": {r[0]: r[1] for r in rec}, "celdas_con_error": errores,
        "notas": ["cgn_momento_registro", "cgn_no_consolida_compraventa", "cgn_cobertura_incompleta_2025",
                  "universo_imig_vs_ci", "ci35_ref_error_2025"],
        "advertencia": ("No es el resultado oficial base caja (IMIG). Universidades y empresas entran con todos sus "
                        "ingresos y gastos; en el IMIG, las empresas solo por su resultado operativo."),
        "procedencia": prov,
    }
