"""Conector IMIG: Informe Mensual de Ingresos y Gastos del Sector Público Nacional no Financiero.

Es la fuente del resultado fiscal oficial (base caja) que publica la Secretaría de Hacienda.
Archivo verificado 2026-10-19 (53 columnas, 2016-01 en adelante):
  https://infra.datos.gob.ar/catalog/sspm/dataset/452/distribution/452.3/download/imig-mensual.csv
Valores en millones de pesos corrientes, con punto decimal. Algunos traen artefactos de float
(p.ej. '3057162.3000000003'): se conserva el texto y para sumar se redondea a 1e-6 M$ (1 peso).
"""
from __future__ import annotations

import csv
import sqlite3
from decimal import Decimal
from pathlib import Path

from .base import DatasetDef, IngestError, SourceDef

HACIENDA = SourceDef(
    source_id="hacienda_imig",
    organismo="Secretaría de Hacienda (MECON), vía catálogo SSPM de datos.gob.ar",
    base_url="https://datos.gob.ar/dataset/sspm-ingresos-gastos-sector-publico-nacional-no-financiero",
    licencia="CC BY 4.0 (catálogo datos.gob.ar)",
    frecuencia_publicada="mensual",
)
URL = "https://infra.datos.gob.ar/catalog/sspm/dataset/452/distribution/452.3/download/imig-mensual.csv"
UNIDAD = "millones de pesos corrientes"
PRECISION = Decimal("0.000001")
# Tolerancia de las identidades contables, en M$. Componentes publicados redondeados (mayormente a
# 0,1 M$) sobre ~50 columnas: el error de redondeo acumulado posible es < 50 × 0,05 = 2,5 M$.
TOLERANCIA_M = Decimal("2.5")

# columna -> (grupo, etiqueta). El orden de grupos define la cuenta.
INGRESOS = {
    "iva_neto_reintegros": ("tributarios", "IVA neto de reintegros"),
    "ganancias": ("tributarios", "Ganancias"),
    "aportes_contribuciones_seguridad_social": ("seguridad_social", "Aportes y contribuciones a la seguridad social"),
    "debitos_creditos": ("tributarios", "Débitos y créditos"),
    "bienes_personales": ("tributarios", "Bienes personales"),
    "impuestos_internos": ("tributarios", "Impuestos internos"),
    "combustibles": ("tributarios", "Combustibles"),
    "derechos_exportacion": ("tributarios", "Derechos de exportación"),
    "derechos_importacion": ("tributarios", "Derechos de importación"),
    "resto_tributarios": ("tributarios", "Resto tributarios"),
    "fgs_cobradas_sector_privado_sector_publico_financiero": ("rentas", "Rentas FGS cobradas al sector privado y público financiero"),
    "resto_rentas_propiedad": ("rentas", "Resto rentas de la propiedad"),
    "ingresos_no_tributarios": ("otros_ingresos", "Ingresos no tributarios"),
    "transferencias_corrientes": ("otros_ingresos", "Transferencias corrientes"),
    "resto_ingresos_corrientes": ("otros_ingresos", "Resto ingresos corrientes"),
    "ingresos_capital": ("otros_ingresos", "Ingresos de capital"),
}
GASTOS_PRIMARIOS = {
    "jubilaciones_pensiones_contributivas": ("prestaciones_sociales", "Jubilaciones y pensiones contributivas"),
    "asignacion_familiares_hijo": ("prestaciones_sociales", "Asignaciones familiares y AUH"),
    "pensiones_no_contributivas": ("prestaciones_sociales", "Pensiones no contributivas"),
    "prestaciones_inssjp": ("prestaciones_sociales", "Prestaciones INSSJP (PAMI)"),
    "otros_programas": ("prestaciones_sociales", "Otros programas sociales"),
    "energia": ("subsidios_economicos", "Subsidios: energía"),
    "transporte": ("subsidios_economicos", "Subsidios: transporte"),
    "otras_funciones": ("subsidios_economicos", "Subsidios: otras funciones"),
    "salarios": ("funcionamiento", "Salarios"),
    "otros_gastos_funcionamiento": ("funcionamiento", "Otros gastos de funcionamiento"),
    "transferencias_corrientes_provincias_educacion": ("transf_provincias", "Transf. corrientes a provincias: educación"),
    "transferencias_corrientes_provincias_seguridad_social": ("transf_provincias", "Transf. corrientes a provincias: seguridad social"),
    "transferencias_corrientes_provincias_desarrollo_social": ("transf_provincias", "Transf. corrientes a provincias: desarrollo social"),
    "transferencias_corrientes_provincias_salud": ("transf_provincias", "Transf. corrientes a provincias: salud"),
    "transferencias_corrientes_provincias_otras": ("transf_provincias", "Transf. corrientes a provincias: otras"),
    "otros_corrientes_transferencias_universidades": ("otros_corrientes", "Transferencias a universidades"),
    "otros_corrientes_deficit_operativo_empresas_publicas": ("otros_corrientes", "Déficit operativo de empresas públicas"),
    "otros_corrientes_resto": ("otros_corrientes", "Otros gastos corrientes"),
    "capital_energia_nacion": ("capital", "Capital: energía (Nación)"),
    "capital_energia_tranferencias_provincias": ("capital", "Capital: energía (a provincias)"),
    "capital_transporte_nacion": ("capital", "Capital: transporte (Nación)"),
    "capital_transporte_tranferencias_provincias": ("capital", "Capital: transporte (a provincias)"),
    "capital_educacion_nacion": ("capital", "Capital: educación (Nación)"),
    "capital_educacion_tranferencias_provincias": ("capital", "Capital: educación (a provincias)"),
    "capital_vivienda_nacion": ("capital", "Capital: vivienda (Nación)"),
    "capital_vivienda_tranferencias_provincias": ("capital", "Capital: vivienda (a provincias)"),
    "capital_agua_potable_alcatarillado_nacion": ("capital", "Capital: agua y cloacas (Nación)"),
    "capital_agua_potable_alcatarillado_tranferencias_provincias": ("capital", "Capital: agua y cloacas (a provincias)"),
    "capital_otros_nacion": ("capital", "Capital: otros (Nación)"),
    "capital_otros_tranferencias_provincias": ("capital", "Capital: otros (a provincias)"),
    "fondo_federal_solidario": ("capital", "Fondo Federal Solidario"),
}
RESULTADOS = {
    "resultado_primario": "Resultado primario",
    "intereses_netos": "Intereses netos",
    "resultado_financiero": "Resultado financiero",
}
# Presentes en el archivo pero fuera de la cuenta principal (meta FMI 2016-2019): se guardan, no se usan.
OTRAS = {"programa_inversiones_prioritarias", "resultado_primario_pip"}
GRUPOS = {
    "tributarios": "Ingresos tributarios", "seguridad_social": "Aportes y contribuciones a la seguridad social",
    "rentas": "Rentas de la propiedad", "otros_ingresos": "Otros ingresos (no tributarios, transferencias, capital)",
    "prestaciones_sociales": "Prestaciones sociales", "subsidios_economicos": "Subsidios económicos",
    "funcionamiento": "Gastos de funcionamiento", "transf_provincias": "Transferencias corrientes a provincias",
    "otros_corrientes": "Otros gastos corrientes", "capital": "Gastos de capital",
}


def dataset_def() -> DatasetDef:
    return DatasetDef(
        dataset_id="imig_mensual", source=HACIENDA,
        nombre="IMIG - Ingresos y gastos del Sector Público Nacional no Financiero (mensual)",
        url=URL, universo="Sector Público Nacional no Financiero", nivel_gobierno="nacional",
        unidad=UNIDAD, cobertura_temporal="2016-01 en adelante", granularidad="mensual; ~50 conceptos",
        metodologia="Base caja. Resultado primario = ingresos totales − gasto primario; "
                    "resultado financiero = resultado primario − intereses netos. Es el resultado fiscal "
                    "oficial que publica la Secretaría de Hacienda.")


def to_dec(text: str) -> Decimal:
    return Decimal(text).quantize(PRECISION)


def check_identities(row: dict[str, str]) -> tuple[Decimal, Decimal]:
    """Devuelve (desvío primario, desvío financiero) en M$."""
    ing = sum(to_dec(row[c]) for c in INGRESOS)
    gas = sum(to_dec(row[c]) for c in GASTOS_PRIMARIOS)
    rp, it, rf = (to_dec(row[c]) for c in RESULTADOS)
    return (ing - gas) - rp, (rp - it) - rf


def load(con: sqlite3.Connection, path: Path, run_id: int):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        cols = set(reader.fieldnames or [])
        esperadas = set(INGRESOS) | set(GASTOS_PRIMARIOS) | set(RESULTADOS) | {"indice_tiempo"}
        if faltan := esperadas - cols:
            raise IngestError(f"IMIG: cambio de esquema, faltan columnas {sorted(faltan)}")
        if nuevas := cols - esperadas - OTRAS:
            raise IngestError(f"IMIG: columnas nuevas sin clasificar {sorted(nuevas)}; "
                              f"revisar si cambian la cuenta antes de cargar")
        con.execute("DELETE FROM series_observation WHERE dataset_id='imig_mensual'")
        n, last, peor = 0, None, Decimal(0)
        for line, row in enumerate(reader, start=2):
            periodo = row["indice_tiempo"][:7]
            for c in esperadas - {"indice_tiempo"} | (OTRAS & cols):
                v = (row[c] or "").strip()
                if not v and c not in OTRAS:
                    raise IngestError(f"IMIG línea {line}: celda vacía en {c} (no se toma como 0)")
                con.execute("INSERT INTO series_observation VALUES (?,?,?,?,?,?)",
                            (f"imig.{c}", "imig_mensual", run_id, periodo, v or None, UNIDAD))
            dp, df = check_identities(row)
            peor = max(peor, abs(dp), abs(df))
            if abs(dp) > TOLERANCIA_M or abs(df) > TOLERANCIA_M:
                raise IngestError(f"IMIG {periodo}: no cierra la cuenta (desvío primario {dp} M$, "
                                  f"financiero {df} M$; tolerancia {TOLERANCIA_M})")
            n += 1
            last = periodo
    if n == 0:
        raise IngestError("IMIG: archivo sin filas")
    return n, f"último mes: {last}; desvío máx. de identidades {peor} M$"
