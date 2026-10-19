"""Conector de la API Series de Tiempo (datos.gob.ar). Sin token.

Documentación: https://www.argentina.gob.ar/datos-abiertos/api-series-de-tiempo
Se descarga una serie por pedido en formato CSV; el texto de cada valor se conserva tal cual.
Celda vacía = la fuente no publica valor => NULL.
"""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from .base import DatasetDef, IngestError, SourceDef

ST = SourceDef(
    source_id="series_tiempo",
    organismo="Secretaría de Innovación / datos.gob.ar (series de INDEC y Secretaría de Hacienda)",
    base_url="https://apis.datos.gob.ar/series/api/",
    licencia="CC BY 4.0 (según catálogo de datos.gob.ar)",
    frecuencia_publicada="según serie",
)
API = "https://apis.datos.gob.ar/series/api/series/"

# id_serie -> (dataset_id, nombre, unidad, universo, metodología)
SERIES = {
    "148.3_INIVELNAL_DICI_M_26": (
        "st_ipc_nacional", "IPC Nivel General Nacional, base dic-2016=100 (INDEC)",
        "índice dic-2016=100", "Total país (precios al consumidor)",
        "Deflactor para series reales. Disponible desde 2016-12."),
    "172.3_TL_RECAION_M_0_0_17": (
        "st_recaudacion_total", "Recaudación tributaria total mensual",
        "millones de pesos corrientes", "Recaudación tributaria nacional (ARCA/DNIAF), bruta de coparticipación",
        "Recaudación bruta antes de distribución a provincias: no es ingreso presupuestario de la AN."),
}


def series_def(series_id: str) -> DatasetDef:
    dsid, nombre, unidad, universo, met = SERIES[series_id]
    return DatasetDef(
        dataset_id=dsid, source=ST, nombre=nombre,
        url=f"{API}?ids={series_id}&format=csv&limit=5000", universo=universo,
        nivel_gobierno="nacional", unidad=unidad, granularidad="mensual", metodologia=met)


def make_loader(series_id: str):
    dsid, _, unidad, _, _ = SERIES[series_id]

    def load(con: sqlite3.Connection, path: Path, run_id: int):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            reader = csv.reader(fh)
            header = next(reader, None)
            if not header or header[0] != "indice_tiempo" or len(header) != 2:
                raise IngestError(f"{dsid}: encabezado inesperado {header}")
            con.execute("DELETE FROM series_observation WHERE series_id=?", (series_id,))
            n, last = 0, None
            for row in reader:
                if len(row) != 2:
                    raise IngestError(f"{dsid}: fila malformada {row}")
                periodo = row[0][:7]
                valor = row[1].strip() or None
                con.execute("INSERT INTO series_observation VALUES (?,?,?,?,?,?)",
                            (series_id, dsid, run_id, periodo, valor, unidad))
                n += 1
                if valor is not None:
                    last = periodo
        if n == 0:
            raise IngestError(f"{dsid}: serie vacía")
        return n, f"último período con dato: {last}"
    return load
