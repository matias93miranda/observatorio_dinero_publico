"""Sincronización bajo demanda + conciliación de agregados contra totales publicados."""
from __future__ import annotations

import sqlite3
from functools import partial
from pathlib import Path

from . import metodologia
from .db import now_iso
from .ingest import boletin_fiscal as bf
from .ingest import cuenta_inversion as ci
from .ingest import imig
from .ingest import presupuesto_abierto as pa
from .ingest import series_tiempo as st
from .ingest.base import run_ingestion

DEFAULT_EJERCICIOS = (2025, 2026)
# Publicaciones de cierre con conector (verificadas a mano: el nombre de archivo no es predecible).
CI_EJERCICIOS = (2025,)
BOLETINES_T4 = tuple(ej for (ej, t) in bf.BOLETINES if t == 4)

# Medida de totales -> (dataset de líneas, flujo, etapa, sólo_primario)
RECONCILE_MAP = {
    "credito_presupuestado": ("credito", "gasto", "presupuestado", False),
    "credito_vigente": ("credito", "gasto", "vigente", False),
    "credito_devengado": ("credito", "gasto", "devengado", False),
    "gasto_primario_presupuestado": ("credito", "gasto", "presupuestado", True),
    "gasto_primario_vigente": ("credito", "gasto", "vigente", True),
    "gasto_primario_devengado": ("credito", "gasto", "devengado", True),
    "recurso_inicial": ("recursos", "recurso", "recurso_inicial", False),
    "recurso_vigente": ("recursos", "recurso", "recurso_vigente", False),
    "recurso_ingresado_percibido": ("recursos", "recurso", "percibido", False),
}
# Intereses y primas de deuda en el clasificador económico (gasto primario = total - esto).
INTERESES_PREFIX = "2131"


def sync_all(con: sqlite3.Connection, ejercicios=DEFAULT_EJERCICIOS, *, force=False,
             local_files: dict[str, Path] | None = None) -> list[dict]:
    local_files = local_files or {}
    results = []

    def go(ds, loader):
        results.append(run_ingestion(con, ds, loader, force=force,
                                     local_file=local_files.get(ds.dataset_id)))

    tot = pa.totales_def()
    go(tot, partial(pa.load_totales, ds=tot))
    for ej in ejercicios:
        c, r = pa.credito_def(ej), pa.recursos_def(ej)
        go(c, partial(pa.load_credito, ds=c))
        go(r, partial(pa.load_recursos, ds=r))
    go(imig.dataset_def(), imig.load)
    for sid in st.SERIES:
        go(st.series_def(sid), st.make_loader(sid))
    for ej in CI_EJERCICIOS:
        d = ci.cuadro35_def(ej)
        go(d, ci.make_loader(ej, d))
        go(ci.metodologia_def(ej), ci.load_documento)
    for ej in BOLETINES_T4:
        d = bf.dataset_def(ej, 4)
        go(d, bf.make_loader(ej, 4, d))
    for ej in ejercicios:
        reconcile(con, ej)
    for ej in CI_EJERCICIOS:
        reconcile_cuenta_inversion(con, ej)
    metodologia.refresh(con)
    return results


def sum_lines(con, dataset_id: str, etapa: str, primario: bool) -> int | None:
    if con.execute("SELECT 1 FROM fiscal_observation WHERE dataset_id=? LIMIT 1",
                   (dataset_id,)).fetchone() is None:
        return None
    q = "SELECT COALESCE(SUM(importe_centavos),0) FROM fiscal_observation WHERE dataset_id=? AND etapa=?"
    args = [dataset_id, etapa]
    if primario:
        q += " AND economico NOT LIKE ?"
        args.append(INTERESES_PREFIX + "%")
    return con.execute(q, args).fetchone()[0]


def reconcile(con: sqlite3.Connection, ejercicio: int, tolerancia_centavos: int = 0) -> list[dict]:
    """Compara suma de líneas anuales vs totales publicados.

    Tolerancia 0: ambos archivos vienen del mismo sistema (e-SIDIF) con 8 decimales en
    millones (= centavos); se verificó coincidencia exacta el 2026-10-19. Una diferencia
    suele indicar que los archivos se actualizaron en fechas distintas.
    """
    out = []
    con.execute("DELETE FROM reconciliation WHERE comparacion LIKE ? AND comparacion LIKE '%vs pa_totales'",
                (f"{ejercicio}:%",))
    for medida, (kind, _flujo, etapa, prim) in RECONCILE_MAP.items():
        ds = f"pa_{kind}_anual_{ejercicio}"
        calc = sum_lines(con, ds, etapa, prim)
        row = con.execute("SELECT importe_centavos FROM published_total WHERE dataset_id='pa_totales' "
                          "AND ejercicio=? AND medida=?", (ejercicio, medida)).fetchone()
        pub = row[0] if row else None
        if calc is None or pub is None:
            concl, diff = "sin_dato", None
        else:
            diff = calc - pub
            concl = "coincide" if abs(diff) <= tolerancia_centavos else "discrepa"
        rec = dict(comparacion=f"{ejercicio}:{medida}: suma {ds} vs pa_totales",
                   total_calculado_centavos=calc, total_publicado_centavos=pub,
                   diferencia_centavos=diff, tolerancia_centavos=tolerancia_centavos,
                   conclusion=concl)
        con.execute("INSERT INTO reconciliation (comparacion, total_calculado_centavos, "
                    "total_publicado_centavos, diferencia_centavos, tolerancia_centavos, "
                    "conclusion, checked_at) VALUES (?,?,?,?,?,?,?)",
                    (rec["comparacion"], calc, pub, diff, tolerancia_centavos, concl, now_iso()))
        out.append(rec)
    con.commit()
    return out


# Cruce Presupuesto Abierto (detalle) vs Cuenta de Inversión, Cuadro 35, columna Total AN.
# Tolerancia 1 $: el xlsx de la CGN guarda dobles (≈16 cifras) y los importes superan 10^14 $.
CRUCE_CI = (
    ("ingresos totales (percibido)", "recursos", "percibido", False, "VI"),
    ("gastos totales (devengado)", "credito", "devengado", False, "VII"),
    ("intereses (económico 2131*)", "credito", "devengado", "solo_intereses",
     "II.intereses_y_otras_rentas_de_la_propiedad.intereses"),
)
TOLERANCIA_CI = 100


def reconcile_cuenta_inversion(con: sqlite3.Connection, ejercicio: int) -> list[dict]:
    out = []
    prefix = f"cruce:{ejercicio}:"
    con.execute("DELETE FROM reconciliation WHERE comparacion LIKE ?", (prefix + "%",))
    for nombre, kind, etapa, filtro, concepto in CRUCE_CI:
        ds = f"pa_{kind}_anual_{ejercicio}"
        if filtro == "solo_intereses":
            row = con.execute("SELECT SUM(importe_centavos) FROM fiscal_observation WHERE dataset_id=? AND etapa=? "
                              "AND economico LIKE ?", (ds, etapa, INTERESES_PREFIX + "%")).fetchone()
            calc = row[0]
        else:
            calc = sum_lines(con, ds, etapa, False)
        r = con.execute("SELECT importe_centavos FROM aif_observation WHERE dataset_id=? AND concepto_id=? "
                        "AND subsector='total_an'", (f"cgn_ci_{ejercicio}_cuadro35", concepto)).fetchone()
        pub = r[0] if r else None
        diff = None if calc is None or pub is None else calc - pub
        concl = "sin_dato" if diff is None else ("coincide" if abs(diff) <= TOLERANCIA_CI else "discrepa")
        comp = f"{prefix}{nombre}: suma {ds} vs Cuenta de Inversión Cuadro 35 (Total AN)"
        con.execute("INSERT INTO reconciliation (comparacion, total_calculado_centavos, total_publicado_centavos, "
                    "diferencia_centavos, tolerancia_centavos, conclusion, checked_at) VALUES (?,?,?,?,?,?,?)",
                    (comp, calc, pub, diff, TOLERANCIA_CI, concl, now_iso()))
        out.append(dict(comparacion=comp, diferencia_centavos=diff, conclusion=concl))
    con.commit()
    return out
