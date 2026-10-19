"""Cálculos sobre la base local. Todo importe sale con unidad, universo, etapa y procedencia."""
from __future__ import annotations

import sqlite3
from decimal import Decimal

from .money import centavos_to_millones
from .sync import INTERESES_PREFIX

UNIDAD = "millones de pesos corrientes"
BASE_MIXTA = ("Recursos en base percibido y gastos en base devengado (convención de la cuenta "
              "Ahorro-Inversión-Financiamiento de la Administración Nacional). No es base caja.")
ADV_RENTAS = ("Los recursos incluyen 'Rentas de la propiedad', que pueden contener flujos dentro del "
              "sector público (p.ej. utilidades del BCRA, rentas del FGS). La metodología del IMIG "
              "(Secretaría de Hacienda) los trata de otro modo: no comparar resultados entre fuentes "
              "sin conciliar.")
BY_GASTO = {
    "finalidad": ("substr(finalidad_funcion,1,instr(finalidad_funcion,'.')-1)", "finalidad"),
    "funcion": ("finalidad_funcion", "finalidad_funcion"),
    "jurisdiccion": ("substr(programa,1,instr(programa,'.')-1)", "jurisdiccion"),
    "programa": ("programa", "programa"),
    "inciso": ("inciso", "inciso"),
    "economico": ("economico", "economico"),
}
BY_RECURSO = {"tipo": ("recurso_tipo", "recurso_tipo"), "clase": ("recurso_clase", "recurso_clase")}


def _fmt(c: int | None) -> str | None:
    return None if c is None else str(centavos_to_millones(c))


def provenance(con: sqlite3.Connection, dataset_id: str) -> dict:
    ds = con.execute("SELECT d.*, s.organismo, s.licencia FROM dataset d JOIN source s "
                     "USING(source_id) WHERE dataset_id=?", (dataset_id,)).fetchone()
    if ds is None:
        return {"dataset_id": dataset_id, "estado": "no_registrado"}
    ok = con.execute("SELECT r.*, a.path, a.size_bytes FROM ingestion_run r LEFT JOIN raw_artifact a "
                     "USING(run_id) WHERE r.dataset_id=? AND r.status IN ('ok') "
                     "ORDER BY r.run_id DESC LIMIT 1", (dataset_id,)).fetchone()
    last = con.execute("SELECT run_id, status, started_at, error FROM ingestion_run WHERE dataset_id=? "
                       "ORDER BY run_id DESC LIMIT 1", (dataset_id,)).fetchone()
    checked = con.execute("SELECT MAX(started_at) FROM ingestion_run WHERE dataset_id=? AND "
                          "status IN ('ok','unchanged')", (dataset_id,)).fetchone()[0]
    return {
        "dataset_id": dataset_id, "nombre": ds["nombre"], "organismo": ds["organismo"],
        "url": ds["url"], "licencia": ds["licencia"], "universo": ds["universo"],
        "nivel_gobierno": ds["nivel_gobierno"], "unidad": ds["unidad"],
        "metodologia": ds["metodologia"], "granularidad": ds["granularidad"],
        "run_id": ok["run_id"] if ok else None,
        "sha256": ok["sha256"] if ok else None,
        "archivo_crudo": ok["path"] if ok else None,
        "fecha_publicacion_fuente": ok["fecha_publicacion"] if ok else None,
        "fecha_descarga": ok["finished_at"] if ok else None,
        "ultima_verificacion": checked,
        "ultimo_intento": dict(last) if last else None,
        "estado": "ok" if ok else "sin_datos",
        "desactualizado": bool(last and last["status"] == "failed"),
    }


def _has(con, dataset_id) -> bool:
    return con.execute("SELECT 1 FROM fiscal_observation WHERE dataset_id=? LIMIT 1",
                       (dataset_id,)).fetchone() is not None


def _sum(con, dataset_id, etapa, extra="", args=()) -> int | None:
    if not _has(con, dataset_id):
        return None
    return con.execute(f"SELECT COALESCE(SUM(importe_centavos),0) FROM fiscal_observation "
                       f"WHERE dataset_id=? AND etapa=? {extra}", (dataset_id, etapa, *args)).fetchone()[0]


def _figure(valor, *, etiqueta, etapa, periodo, datasets, con, base=None, formula=None, adv=()):
    prov = [provenance(con, d) for d in datasets]
    return {
        "etiqueta": etiqueta, "valor_millones": _fmt(valor),
        "estado": "ok" if valor is not None else "sin_datos",
        "unidad": UNIDAD, "etapa": etapa, "periodo": periodo,
        "universo": prov[0].get("universo") if prov else None, "base": base,
        "formula": formula, "advertencias": list(adv), "procedencia": prov,
    }


def _cobertura(con, ejercicio) -> str:
    f = con.execute("SELECT fecha_publicacion FROM ingestion_run WHERE dataset_id=? AND status='ok' "
                    "ORDER BY run_id DESC LIMIT 1", (f"pa_credito_anual_{ejercicio}",)).fetchone()
    return f"ejercicio {ejercicio}, ejecución acumulada al {f[0]}" if f else f"ejercicio {ejercicio}"


def summary(con: sqlite3.Connection, ejercicio: int) -> dict:
    dg, dr = f"pa_credito_anual_{ejercicio}", f"pa_recursos_anual_{ejercicio}"
    per = _cobertura(con, ejercicio)
    gasto = _sum(con, dg, "devengado")
    pagado = _sum(con, dg, "pagado")
    interes = _sum(con, dg, "devengado", "AND economico LIKE ?", (INTERESES_PREFIX + "%",))
    ingreso = _sum(con, dr, "percibido")
    primario = None if gasto is None or interes is None else gasto - interes
    res_prim = None if ingreso is None or primario is None else ingreso - primario
    res_fin = None if ingreso is None or gasto is None else ingreso - gasto
    cards = [
        _figure(ingreso, etiqueta="Ingresos totales (corrientes + capital)", etapa="percibido",
                periodo=per, datasets=[dr], con=con, adv=[ADV_RENTAS]),
        _figure(gasto, etiqueta="Gasto total (corriente + capital)", etapa="devengado",
                periodo=per, datasets=[dg], con=con),
        _figure(pagado, etiqueta="Gasto total pagado", etapa="pagado", periodo=per, datasets=[dg],
                con=con, adv=["Pagado ≠ devengado: la diferencia es deuda flotante, no ahorro."]),
        _figure(interes, etiqueta="Intereses y primas de deuda", etapa="devengado", periodo=per,
                datasets=[dg], con=con, formula="Σ clasificador económico 2131*"),
        _figure(primario, etiqueta="Gasto primario", etapa="devengado", periodo=per, datasets=[dg],
                con=con, formula="gasto total − intereses (2131*)"),
        _figure(res_prim, etiqueta="Resultado primario", etapa="percibido − devengado", periodo=per,
                datasets=[dr, dg], con=con, base=BASE_MIXTA,
                formula="ingresos percibidos − gasto primario devengado", adv=[ADV_RENTAS]),
        _figure(res_fin, etiqueta="Resultado financiero", etapa="percibido − devengado", periodo=per,
                datasets=[dr, dg], con=con, base=BASE_MIXTA,
                formula="ingresos percibidos − gasto total devengado", adv=[ADV_RENTAS]),
    ]
    # Centavos como texto: superan 2^53 y un cliente JS los redondearía.
    rec = [{k: (str(v) if k.endswith("_centavos") and v is not None else v) for k, v in dict(r).items()}
           for r in con.execute(
        "SELECT comparacion, total_calculado_centavos, total_publicado_centavos, diferencia_centavos, "
        "tolerancia_centavos, conclusion, checked_at FROM reconciliation WHERE comparacion LIKE ? "
        "ORDER BY rec_id", (f"{ejercicio}:%",))]
    return {"ejercicio": ejercicio, "universo": "Administración Nacional", "cards": cards,
            "conciliacion": rec}


def breakdown(con, ejercicio: int, flujo: str, by: str, etapa: str, parent: str | None = None,
              limit: int = 50) -> dict:
    table = BY_GASTO if flujo == "gasto" else BY_RECURSO
    if by not in table:
        raise ValueError(f"clasificación no soportada: {by}; opciones {sorted(table)}")
    expr, clasif = table[by]
    ds = f"pa_{'credito' if flujo == 'gasto' else 'recursos'}_anual_{ejercicio}"
    if not _has(con, ds):
        return {"estado": "sin_datos", "items": [], "procedencia": [provenance(con, ds)]}
    extra, args = "", []
    if parent and by == "funcion":
        extra, args = "AND finalidad_funcion LIKE ?", [parent + ".%"]
    elif parent and by == "programa":
        extra, args = "AND programa LIKE ?", [parent + ".%"]
    rows = con.execute(
        f"SELECT {expr} AS code, SUM(importe_centavos) AS c FROM fiscal_observation "
        f"WHERE dataset_id=? AND etapa=? {extra} GROUP BY code ORDER BY c DESC",
        (ds, etapa, *args)).fetchall()
    total = sum(r["c"] for r in rows)
    labels = {r["code"]: r["label"] for r in con.execute(
        "SELECT code, label FROM dimension_category WHERE clasificador=? AND ejercicio=?",
        (clasif, ejercicio))}
    items = [{"code": r["code"], "label": labels.get(r["code"], r["code"]),
              "valor_millones": _fmt(r["c"]),
              "participacion": str((Decimal(r["c"]) / Decimal(total)).quantize(Decimal("0.0001")))
              if total else None} for r in rows[:limit]]
    return {"estado": "ok", "ejercicio": ejercicio, "flujo": flujo, "clasificacion": by,
            "etapa": etapa, "unidad": UNIDAD, "periodo": _cobertura(con, ejercicio),
            "total_millones": _fmt(total), "items": items, "n_categorias": len(rows),
            "nota": "Descomposición por clasificador presupuestario; no representa pagos rastreados "
                    "a destinatarios.", "procedencia": [provenance(con, ds)]}


def ipc_annual_avg(con) -> dict[int, Decimal]:
    """Promedio anual del IPC solo para años con 12 meses publicados."""
    out: dict[int, list[Decimal]] = {}
    for r in con.execute("SELECT periodo, valor_original FROM series_observation WHERE "
                         "series_id='148.3_INIVELNAL_DICI_M_26' AND valor_original IS NOT NULL"):
        out.setdefault(int(r[0][:4]), []).append(Decimal(r[1]))
    return {y: sum(v) / 12 for y, v in out.items() if len(v) == 12}


def annual_series(con) -> dict:
    """Series anuales de totales publicados, nominales y reales (pesos del último año completo)."""
    rows = con.execute("SELECT ejercicio, medida, importe_centavos, ultima_actualizacion FROM "
                       "published_total WHERE dataset_id='pa_totales' ORDER BY ejercicio").fetchall()
    if not rows:
        return {"estado": "sin_datos", "series": {}, "procedencia": [provenance(con, "pa_totales")]}
    ipc = ipc_annual_avg(con)
    base_year = max(ipc) if ipc else None
    vigente = max(r["ejercicio"] for r in rows)
    series: dict[str, list] = {}
    for r in rows:
        nom = None if r["importe_centavos"] is None else centavos_to_millones(r["importe_centavos"])
        real = None
        if nom is not None and r["ejercicio"] in ipc and r["ejercicio"] != vigente:
            real = (nom * ipc[base_year] / ipc[r["ejercicio"]]).quantize(Decimal("0.000001"))
        series.setdefault(r["medida"], []).append({
            "ejercicio": r["ejercicio"], "nominal_millones": None if nom is None else str(nom),
            "real_millones": None if real is None else str(real),
            "parcial": r["ejercicio"] == vigente, "ultima_actualizacion": r["ultima_actualizacion"]})
    return {
        "estado": "ok", "unidad_nominal": UNIDAD,
        "unidad_real": f"millones de pesos de {base_year} (promedio anual IPC)" if base_year else None,
        "deflactor": "IPC Nivel General Nacional INDEC base dic-2016 (serie 148.3_INIVELNAL_DICI_M_26), "
                     "promedio de 12 meses; años sin 12 meses de IPC => real sin dato",
        "ejercicio_vigente_parcial": vigente,
        "series": series,
        "procedencia": [provenance(con, "pa_totales"), provenance(con, "st_ipc_nacional")],
    }


def pct_change(cur: Decimal | None, prev: Decimal | None) -> Decimal | None:
    if cur is None or prev is None or prev == 0:
        return None
    return 100 * (cur / prev - 1)


def real_change(nominal_pct: Decimal | None, inflation_pct: Decimal | None) -> Decimal | None:
    if nominal_pct is None or inflation_pct is None or inflation_pct == -100:
        return None
    return 100 * ((1 + nominal_pct / 100) / (1 + inflation_pct / 100) - 1)


def series_monthly(con, series_id: str, desde: str | None = None, hasta: str | None = None) -> dict:
    dsid = con.execute("SELECT dataset_id FROM series_observation WHERE series_id=? LIMIT 1",
                       (series_id,)).fetchone()
    if dsid is None:
        return {"estado": "sin_datos", "series_id": series_id, "datos": []}
    q, a = "SELECT periodo, valor_original, unidad FROM series_observation WHERE series_id=?", [series_id]
    if desde:
        q += " AND periodo>=?"; a.append(desde)
    if hasta:
        q += " AND periodo<=?"; a.append(hasta)
    rows = con.execute(q + " ORDER BY periodo", a).fetchall()
    return {"estado": "ok", "series_id": series_id, "unidad": rows[0]["unidad"] if rows else None,
            "datos": [{"periodo": r["periodo"], "valor": r["valor_original"]} for r in rows],
            "procedencia": [provenance(con, dsid[0])]}


def coverage(con) -> list[dict]:
    return [provenance(con, r[0]) | {
        "observaciones": con.execute("SELECT COUNT(*) FROM fiscal_observation WHERE dataset_id=?", (r[0],)).fetchone()[0]
        + con.execute("SELECT COUNT(*) FROM series_observation WHERE dataset_id=?", (r[0],)).fetchone()[0]
        + con.execute("SELECT COUNT(*) FROM published_total WHERE dataset_id=?", (r[0],)).fetchone()[0]}
        for r in con.execute("SELECT dataset_id FROM dataset ORDER BY dataset_id")]


def observation_provenance(con, obs_id: int) -> dict | None:
    r = con.execute("SELECT * FROM fiscal_observation WHERE obs_id=?", (obs_id,)).fetchone()
    if r is None:
        return None
    art = con.execute("SELECT path, sha256 FROM raw_artifact WHERE run_id=?", (r["run_id"],)).fetchone()
    return {"observacion": dict(r), "valor_millones": _fmt(r["importe_centavos"]),
            "linea_csv_original": r["source_line"],
            "archivo_crudo": art["path"] if art else None, "sha256": art["sha256"] if art else None,
            "dataset": provenance(con, r["dataset_id"])}
