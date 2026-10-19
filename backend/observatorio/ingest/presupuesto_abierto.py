"""Conector de Presupuesto Abierto (datos abiertos, descarga directa, sin token).

Catálogo verificado 2026-10-19: https://www.presupuestoabierto.gob.ar/sici/rest-api/catalog/site
Archivos: https://dgsiaf-repo.mecon.gob.ar/repository/pa/datasets/...
Unidad: millones de pesos corrientes (verificado contra serie_pib_anual.csv, que está en pesos).
Universo: Administración Nacional (Sector Público Nacional no Financiero, subsector AN).
"""
from __future__ import annotations

import csv
import io
import re
import sqlite3
import zipfile
from pathlib import Path

from ..money import AmountError, millones_to_centavos
from .base import DatasetDef, IngestError, SourceDef

PA = SourceDef(
    source_id="presupuesto_abierto",
    organismo="Oficina Nacional de Presupuesto - Secretaría de Hacienda (MECON)",
    base_url="https://www.presupuestoabierto.gob.ar/sici/datos-abiertos",
    licencia="CC BY 4.0",
    frecuencia_publicada="diaria (R/P1D) para el ejercicio vigente; cierre anual para ejercicios previos",
)
REPO = "https://dgsiaf-repo.mecon.gob.ar/repository/pa/datasets"
UNIVERSO_AN = "Administración Nacional"
UNIDAD = "millones de pesos corrientes"

CREDITO_MEDIDAS = {
    "credito_presupuestado": "presupuestado",
    "credito_vigente": "vigente",
    "credito_comprometido": "comprometido",
    "credito_devengado": "devengado",
    "credito_pagado": "pagado",
}
RECURSO_MEDIDAS = {
    "recurso_inicial": "recurso_inicial",
    "recurso_vigente": "recurso_vigente",
    "recurso_ingresado_percibido": "percibido",
}
CREDITO_COLS = {
    "ejercicio_presupuestario", "caracter_id", "caracter_desc", "jurisdiccion_id",
    "jurisdiccion_desc", "servicio_id", "servicio_desc", "programa_id", "programa_desc",
    "finalidad_id", "finalidad_desc", "funcion_id", "funcion_desc", "inciso_id", "inciso_desc",
    "clasificador_economico_8_digitos_id", "clasificador_economico_8_digitos_desc",
    "fuente_financiamiento_id", "fuente_financiamiento_desc", "ubicacion_geografica_id",
    "ubicacion_geografica_desc", "sector_desc", "subsector_desc", "ultima_actualizacion_fecha",
    *CREDITO_MEDIDAS,
}
RECURSO_COLS = {
    "ejercicio_presupuestario", "caracter_id", "caracter_desc", "jurisdiccion_id",
    "jurisdiccion_desc", "servicio_id", "servicio_desc", "tipo_id", "tipo_desc", "clase_id",
    "clase_desc", "fuente_financiamiento_id", "clasificador_economico_8_digitos_id",
    "clasificador_economico_8_digitos_desc", "sector_desc", "subsector_desc",
    "ultima_actualizacion_fecha", *RECURSO_MEDIDAS,
}
TOTALES_MEDIDAS = [
    "credito_presupuestado", "credito_vigente", "credito_devengado", "recurso_inicial",
    "recurso_vigente", "recurso_ingresado_percibido", "gasto_primario_presupuestado",
    "gasto_primario_vigente", "gasto_primario_devengado",
]


def totales_def() -> DatasetDef:
    return DatasetDef(
        dataset_id="pa_totales", source=PA,
        nombre="Total Presupuesto y ejecución de gastos y recursos",
        url=f"{REPO}/totales-de-presupuesto.zip", universo=UNIVERSO_AN, nivel_gobierno="nacional",
        unidad=UNIDAD, cobertura_temporal="2007-ejercicio vigente", granularidad="anual",
        metodologia="Gastos en base devengado; recursos en base percibido. Gasto primario = "
                    "gasto total menos intereses y primas (clasificador económico 2131).")


def credito_def(ejercicio: int, agrupacion: str = "anual") -> DatasetDef:
    return DatasetDef(
        dataset_id=f"pa_credito_{agrupacion}_{ejercicio}", source=PA,
        nombre=f"Presupuesto de gastos y su ejecución detallada - agrupación {agrupacion} {ejercicio}",
        url=f"{REPO}/{ejercicio}/credito-{agrupacion}-{ejercicio}.zip", universo=UNIVERSO_AN,
        nivel_gobierno="nacional", unidad=UNIDAD, cobertura_temporal=str(ejercicio),
        granularidad=f"{agrupacion}; línea = jurisdicción x servicio x programa x ... x objeto",
        metodologia="Gastos corrientes y de capital (clasificador económico 2.1 y 2.2). "
                    "No incluye aplicaciones financieras (amortización de deuda) ni gastos figurativos.")


def recursos_def(ejercicio: int, agrupacion: str = "anual") -> DatasetDef:
    return DatasetDef(
        dataset_id=f"pa_recursos_{agrupacion}_{ejercicio}", source=PA,
        nombre=f"Estimación de recursos y su ejecución - agrupación {agrupacion} {ejercicio}",
        url=f"{REPO}/{ejercicio}/recursos-{agrupacion}-{ejercicio}.zip", universo=UNIVERSO_AN,
        nivel_gobierno="nacional", unidad=UNIDAD, cobertura_temporal=str(ejercicio),
        granularidad=f"{agrupacion}; línea = servicio x rubro x fuente",
        metodologia="Recursos corrientes y de capital (clasificador económico 1.1 y 1.2), base "
                    "percibido. No incluye fuentes financieras (endeudamiento, uso de activos).")


def _open_csv(path: Path):
    """Devuelve un iterador DictReader sobre el CSV (dentro del zip o suelto)."""
    if zipfile.is_zipfile(path):
        zf = zipfile.ZipFile(path)
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if len(names) != 1:
            raise IngestError(f"Se esperaba 1 CSV en {path.name}, hay {len(names)}: {names}")
        fh = io.TextIOWrapper(zf.open(names[0]), encoding="utf-8-sig", newline="")
    else:
        fh = open(path, encoding="utf-8-sig", newline="")
    return csv.DictReader(fh)


def _check_cols(reader: csv.DictReader, required: set[str], name: str) -> None:
    missing = required - set(reader.fieldnames or [])
    if missing:
        raise IngestError(f"Cambio de esquema en {name}: faltan columnas {sorted(missing)}")


_FECHA = re.compile(r"(\d{1,2} \w+ \d{4})")


def _fecha_pub(texto: str) -> str:
    m = _FECHA.search(texto or "")
    return m.group(1) if m else (texto or "")


def _amount(row: dict, col: str, line: int) -> int:
    try:
        return millones_to_centavos(row[col])
    except AmountError as e:
        raise IngestError(f"Línea {line}, columna {col}: {e}") from e


def _upsert_entity(con, ejercicio, row) -> str:
    eid = f"AN/{ejercicio}/{row['servicio_id']}"
    con.execute(
        "INSERT OR IGNORE INTO dimension_entity VALUES (?,?,?,?,?,?,?)",
        (eid, row["servicio_desc"], "nacional", row["caracter_desc"],
         row["jurisdiccion_id"], row["jurisdiccion_desc"], ejercicio))
    return eid


def _cat(con, clasificador, code, label, parent, ejercicio):
    con.execute("INSERT OR IGNORE INTO dimension_category VALUES (?,?,?,?,?)",
                (clasificador, code, label, parent, ejercicio))


def _check_universe(row, line):
    if row["subsector_desc"] != UNIVERSO_AN:
        raise IngestError(f"Línea {line}: universo inesperado {row['subsector_desc']!r}; "
                          f"no se mezclan universos sin regla de consolidación")


def _check_composicion(eco: str, prefixes: tuple[str, ...], line: int, que: str):
    """Las fórmulas (gasto primario, resultados) suponen que el archivo solo trae estas partidas.
    Si aparece otra (p.ej. gastos figurativos o aplicaciones financieras) se corta la carga."""
    if not eco.startswith(prefixes):
        raise IngestError(f"Línea {line}: clasificador económico {eco} fuera de {que} "
                          f"{prefixes}; revisar doble conteo antes de cargar")


def load_credito(con: sqlite3.Connection, path: Path, run_id: int, ds: DatasetDef):
    reader = _open_csv(path)
    _check_cols(reader, CREDITO_COLS, ds.dataset_id)
    mensual = "impacto_presupuestario_mes" in (reader.fieldnames or [])
    con.execute("DELETE FROM fiscal_observation WHERE dataset_id=?", (ds.dataset_id,))
    batch, n, fecha = [], 0, None
    for line, row in enumerate(reader, start=2):
        _check_universe(row, line)
        ej = int(row["ejercicio_presupuestario"])
        periodo = f"{ej}-{int(row['impacto_presupuestario_mes']):02d}" if mensual else str(ej)
        eid = _upsert_entity(con, ej, row)
        ff = f"{row['finalidad_id']}.{row['funcion_id']}"
        prog = f"{row['jurisdiccion_id']}.{row['servicio_id']}.{row['programa_id']}"
        eco = row["clasificador_economico_8_digitos_id"]
        _check_composicion(eco, ("21", "22"), line, "gasto corriente/capital")
        _cat(con, "finalidad", row["finalidad_id"], row["finalidad_desc"], None, ej)
        _cat(con, "finalidad_funcion", ff, row["funcion_desc"], row["finalidad_id"], ej)
        _cat(con, "jurisdiccion", row["jurisdiccion_id"], row["jurisdiccion_desc"], None, ej)
        _cat(con, "programa", prog, row["programa_desc"], row["jurisdiccion_id"], ej)
        _cat(con, "inciso", row["inciso_id"], row["inciso_desc"], None, ej)
        _cat(con, "economico", eco, row["clasificador_economico_8_digitos_desc"], None, ej)
        fecha = fecha or _fecha_pub(row["ultima_actualizacion_fecha"])
        for col, etapa in CREDITO_MEDIDAS.items():
            batch.append((ds.dataset_id, run_id, line, ej, periodo, "gasto", etapa, eid, ff, prog,
                          row["inciso_id"], eco, row["fuente_financiamiento_id"],
                          row["ubicacion_geografica_id"], None, None,
                          _amount(row, col, line), row[col]))
        n += 1
        if len(batch) >= 20000:
            _insert_obs(con, batch)
            batch.clear()
    _insert_obs(con, batch)
    if n == 0:
        raise IngestError(f"{ds.dataset_id}: archivo sin filas de datos")
    return n, fecha


def load_recursos(con: sqlite3.Connection, path: Path, run_id: int, ds: DatasetDef):
    reader = _open_csv(path)
    _check_cols(reader, RECURSO_COLS, ds.dataset_id)
    mensual = "impacto_presupuestario_mes" in (reader.fieldnames or [])
    con.execute("DELETE FROM fiscal_observation WHERE dataset_id=?", (ds.dataset_id,))
    batch, n, fecha = [], 0, None
    for line, row in enumerate(reader, start=2):
        _check_universe(row, line)
        ej = int(row["ejercicio_presupuestario"])
        periodo = f"{ej}-{int(row['impacto_presupuestario_mes']):02d}" if mensual else str(ej)
        eid = _upsert_entity(con, ej, row)
        tipo, clase = row["tipo_id"], f"{row['tipo_id']}.{row['clase_id']}"
        eco = row["clasificador_economico_8_digitos_id"]
        _check_composicion(eco, ("11", "12"), line, "recursos corrientes/capital")
        _cat(con, "recurso_tipo", tipo, row["tipo_desc"], None, ej)
        _cat(con, "recurso_clase", clase, row["clase_desc"], tipo, ej)
        _cat(con, "economico", eco, row["clasificador_economico_8_digitos_desc"], None, ej)
        fecha = fecha or _fecha_pub(row["ultima_actualizacion_fecha"])
        for col, etapa in RECURSO_MEDIDAS.items():
            batch.append((ds.dataset_id, run_id, line, ej, periodo, "recurso", etapa, eid, None,
                          None, None, eco, row["fuente_financiamiento_id"], None, tipo, clase,
                          _amount(row, col, line), row[col]))
        n += 1
        if len(batch) >= 20000:
            _insert_obs(con, batch)
            batch.clear()
    _insert_obs(con, batch)
    if n == 0:
        raise IngestError(f"{ds.dataset_id}: archivo sin filas de datos")
    return n, fecha


def _insert_obs(con, batch):
    con.executemany(
        "INSERT INTO fiscal_observation (dataset_id, run_id, source_line, ejercicio, periodo, "
        "flujo, etapa, entity_id, finalidad_funcion, programa, inciso, economico, "
        "fuente_financiamiento, ubicacion_geografica, recurso_tipo, recurso_clase, "
        "importe_centavos, importe_original) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", batch)


def load_totales(con: sqlite3.Connection, path: Path, run_id: int, ds: DatasetDef):
    reader = _open_csv(path)
    _check_cols(reader, {"ejercicio_presupuestario", "ultima_actualizacion_fecha",
                         *TOTALES_MEDIDAS}, ds.dataset_id)
    con.execute("DELETE FROM published_total WHERE dataset_id=?", (ds.dataset_id,))
    n, fecha = 0, None
    for line, row in enumerate(reader, start=2):
        ej = int(row["ejercicio_presupuestario"])
        upd = _fecha_pub(row["ultima_actualizacion_fecha"])
        fecha = upd  # la última fila es el ejercicio vigente
        for col in TOTALES_MEDIDAS:
            raw = (row.get(col) or "").strip()
            cent = _amount(row, col, line) if raw else None  # vacío => NULL, nunca 0
            con.execute("INSERT INTO published_total VALUES (?,?,?,?,?,?,?)",
                        (ds.dataset_id, run_id, ej, col, cent, raw or None, upd))
        n += 1
    if n == 0:
        raise IngestError("totales-de-presupuesto: sin filas")
    return n, fecha
