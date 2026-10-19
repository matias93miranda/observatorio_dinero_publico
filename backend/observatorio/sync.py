"""Sincronización bajo demanda + conciliación de agregados contra totales publicados."""
from __future__ import annotations

import sqlite3
from functools import partial
from pathlib import Path

from .db import now_iso
from .ingest import presupuesto_abierto as pa
from .ingest import series_tiempo as st
from .ingest.base import run_ingestion

DEFAULT_EJERCICIOS = (2025, 2026)

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
    for sid in st.SERIES:
        go(st.series_def(sid), st.make_loader(sid))
    for ej in ejercicios:
        reconcile(con, ej)
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
    con.execute("DELETE FROM reconciliation WHERE comparacion LIKE ?", (f"{ejercicio}:%",))
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
