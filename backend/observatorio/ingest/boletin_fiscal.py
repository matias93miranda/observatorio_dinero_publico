"""Conector Boletín Fiscal (Oficina Nacional de Presupuesto, Secretaría de Hacienda).

Publicación trimestral en PDF. El acumulado al 4º trimestre es la única publicación oficial
encontrada que descompone el paso de la Administración Nacional (base devengado) al resultado
base caja del Sector Público Nacional (el mismo que publica el IMIG): rentas del BCRA, rentas
del FGS e intereses intra-sector público, y el aporte de PAMI, fondos fiduciarios y otros entes.
Verificado 2026-10-19:
  https://www.mecon.gob.ar/onp/documentos/boletin/4totrim25/4totrim25.pdf (125 páginas)
El servidor no envía el certificado intermedio: ver observatorio/certs/README.md.

Las cifras NO se tipean: se extraen del texto del PDF crudo buscando la fila por su rótulo
exacto en una página dada. Si el rótulo no aparece una sola vez, o la página no contiene el
encabezado esperado del cuadro, la carga falla y se conserva la versión anterior.
"""
from __future__ import annotations

import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from .base import DatasetDef, IngestError, SourceDef

ONP = SourceDef(
    source_id="onp_boletin_fiscal",
    organismo="Oficina Nacional de Presupuesto (Secretaría de Hacienda, MECON)",
    base_url="https://www.mecon.gob.ar/onp/html/boletin/",
    licencia=None,
    frecuencia_publicada="trimestral",
)
CA_MECON = "sectigo_public_server_authentication_ca_dv_r36.pem"
UNIDAD = "millones de pesos corrientes"
NUM = r"-?\d{1,3}(?:\.\d{3})*,\d+"
LINE = re.compile(rf"^(.*?)\s+((?:{NUM}\s*)+)$")

AN = "Administración Nacional"
RESTO = "INSSJyP, fondos fiduciarios y otros entes (incluye resultado operativo de empresas públicas)"
SPN = "Sector Público Nacional (AN + INSSJyP + fondos fiduciarios + otros entes + empresas)"
DEV = "recaudado (recursos) / devengado (gastos), datos provisorios"
CAJA_NM = "caja, nueva metodología (sin rentas del BCRA ni del FGS; intereses netos de los intra-sector público)"


@dataclass(frozen=True)
class Fig:
    figure_id: str
    pagina: int
    cuadro: str
    rotulo: str        # rótulo exacto de la fila (se compara normalizado)
    col: int           # índice de la columna numérica (0 = primera)
    universo: str
    base: str
    concepto: str


@dataclass(frozen=True)
class Boletin:
    ejercicio: int
    trimestre: int
    archivo: str
    periodo: str
    marcas: dict[int, tuple[str, ...]]   # página -> textos que deben estar (identifican el cuadro)
    figuras: tuple[Fig, ...]


_C1 = "Cuadro 1 · AN · base recaudado/devengado"
_C5 = "Cuadro 5 · SPN · base caja"
_C4 = "Cuadro 4 · SPN · base caja"
BOLETINES = {
    (2025, 4): Boletin(
        ejercicio=2025, trimestre=4, archivo="4totrim25", periodo="2025 (acumulado al 4º trimestre)",
        marcas={57: ("CUADRO 1", "ADMINISTRACIÓN NACIONAL", "BASE RECAUDADO / DEVENGADO", "4to. TRIMESTRE DE 2025"),
                61: ("CUADRO 4", "SECTOR PÚBLICO NACIONAL", "BASE CAJA", "4to. TRIMESTRE DE 2025"),
                62: ("CUADRO 5", "SECTOR PUBLICO NACIONAL", "BASE CAJA", "4to. TRIMESTRE DE 2025")},
        figuras=(
            Fig("an_dev.recursos_totales", 57, _C1, "VI TOTAL RECURSOS (I+IV)", 1, AN, DEV, "Recursos totales"),
            Fig("an_dev.gastos_totales", 57, _C1, "VII TOTAL GASTOS (II+V)", 1, AN, DEV, "Gastos totales"),
            Fig("an_dev.intereses", 57, _C1, "Intereses", 1, AN, DEV, "Intereses"),
            Fig("an_dev.rentas_propiedad", 57, _C1, "Rentas de la Propiedad", 1, AN, DEV, "Rentas de la propiedad"),
            Fig("an_dev.resultado_primario", 57, _C1, "VIII RESULTADO PRIMARIO", 1, AN, DEV, "Resultado primario"),
            Fig("an_dev.resultado_financiero", 57, _C1, "IX RESULTADO FINANCIERO", 1, AN, DEV, "Resultado financiero"),
            Fig("an_caja.rentas_netas", 62, _C5, "Rentas de la Propiedad Netas (1)", 0, AN, CAJA_NM,
                "Rentas de la propiedad netas (sin BCRA ni FGS)"),
            Fig("an_caja.intereses_netos", 62, _C5, "Intereses Netos (2)", 0, AN, CAJA_NM, "Intereses netos"),
            Fig("an_caja.contribuciones_figurativas", 62, _C5, "IX CONTRIBUCIONES FIGURATIVAS", 0, AN, CAJA_NM,
                "Contribuciones figurativas recibidas"),
            Fig("an_caja.gastos_figurativos", 62, _C5, "X GASTOS FIGURATIVOS", 0, AN, CAJA_NM,
                "Gastos figurativos otorgados"),
            Fig("an_caja.resultado_primario_sin_rentas", 62, _C5, "XIV RESULTADO PRIMARIO SIN RENTAS (XI-XII)", 0,
                AN, CAJA_NM, "Resultado primario sin rentas"),
            Fig("an_caja.resultado_financiero", 62, _C5, "XV RESULTADO FINANCIERO (XI-XIII)", 0, AN, CAJA_NM,
                "Resultado financiero"),
            Fig("an_caja.rentas_bcra", 62, _C5, "- RENTAS DE LA PROPIEDAD PERCIBIDAS DEL BCRA", 0, AN, "caja",
                "Rentas de la propiedad percibidas del BCRA (excluidas del resultado)"),
            Fig("an_caja.rentas_fgs_y_otros", 62, _C5, "- RENTAS DE LA PROPIEDAD PERCIBIDAS DEL FGS Y OTROS", 0, AN,
                "caja", "Rentas de la propiedad percibidas por el FGS y otros (intra-sector público, excluidas)"),
            Fig("an_caja.intereses_intra_sp", 62, _C5, "- RENTAS DE LA PROPIEDAD PAGADAS SOBRE DEUDA", 0, AN, "caja",
                "Intereses pagados intra-sector público (excluidos del gasto)"),
            Fig("resto_caja.resultado_primario", 62, _C5, "XIV RESULTADO PRIMARIO SIN RENTAS (XI-XII)", 1, RESTO,
                CAJA_NM, "Resultado primario"),
            Fig("resto_caja.resultado_financiero", 62, _C5, "XV RESULTADO FINANCIERO (XI-XIII)", 1, RESTO, CAJA_NM,
                "Resultado financiero"),
            Fig("resto_caja.intereses_intra_sp", 62, _C5, "- RENTAS DE LA PROPIEDAD PAGADAS SOBRE DEUDA", 1, RESTO,
                "caja", "Intereses pagados intra-sector público (excluidos del gasto)"),
            Fig("spn_caja.ingresos", 62, _C5, "VI INGRESOS ANTES DE FIGURATIVAS (I+ IV)", 2, SPN, CAJA_NM,
                "Ingresos totales"),
            Fig("spn_caja.resultado_primario", 62, _C5, "XIV RESULTADO PRIMARIO SIN RENTAS (XI-XII)", 2, SPN, CAJA_NM,
                "Resultado primario"),
            Fig("spn_caja.resultado_financiero", 62, _C5, "XV RESULTADO FINANCIERO (XI-XIII)", 2, SPN, CAJA_NM,
                "Resultado financiero"),
            Fig("spn_caja.superavit_operativo_empresas", 61, _C4, "Superávit Operativo de Empresas Públicas", 4, SPN,
                CAJA_NM, "Superávit operativo de empresas públicas (las empresas entran por su resultado neto)"),
            Fig("spn_caja.deficit_operativo_empresas", 61, _C4, "Deficit Oper.Empresas Públicas", 4, SPN, CAJA_NM,
                "Déficit operativo de empresas públicas (las empresas entran por su resultado neto)"),
        )),
}


def dataset_def(ejercicio: int, trimestre: int) -> DatasetDef:
    b = BOLETINES[(ejercicio, trimestre)]
    return DatasetDef(
        dataset_id=f"onp_boletin_{ejercicio}_t{trimestre}", source=ONP,
        nombre=f"Boletín Fiscal · {trimestre}º trimestre {ejercicio} (ONP)",
        url=f"https://www.mecon.gob.ar/onp/documentos/boletin/{b.archivo}/{b.archivo}.pdf",
        universo="Administración Nacional y Sector Público Nacional (según cuadro)",
        nivel_gobierno="nacional", unidad=UNIDAD, cobertura_temporal=b.periodo,
        granularidad="acumulado trimestral",
        metodologia="AN: recaudado/devengado (provisorio). SPN: base caja, metodología vigente desde 2017.",
        ca_extra=CA_MECON)


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper()
    return " ".join(s.split())


def to_centavos_millones(txt: str) -> int:
    d = Decimal(txt.replace(".", "").replace(",", "."))
    return int(d * 100_000_000)


def page_texts(path: Path) -> list[str]:
    try:
        import pypdf
    except ImportError as e:  # dependencia declarada en requirements.txt
        raise IngestError("Falta pypdf para leer el Boletín Fiscal (pip install -r requirements.txt)") from e
    return [p.extract_text() or "" for p in pypdf.PdfReader(path).pages]


def table_rows(text: str) -> list[tuple[str, list[str], str]]:
    out = []
    for raw in text.splitlines():
        m = LINE.match(raw.strip())
        if m:
            out.append((_norm(m.group(1)), re.findall(NUM, m.group(2)), raw.strip()))
    return out


def extract(b: Boletin, pages: list[str]) -> list[dict]:
    for pg, marcas in b.marcas.items():
        if pg > len(pages):
            raise IngestError(f"Boletín {b.archivo}: tiene {len(pages)} páginas, se esperaba al menos {pg}")
        norm = _norm(pages[pg - 1])
        falta = [m for m in marcas if _norm(m) not in norm]
        if falta:
            raise IngestError(f"Boletín {b.archivo}: la página {pg} no contiene {falta}; cambió la estructura")
    rows = {pg: table_rows(pages[pg - 1]) for pg in b.marcas}
    out = []
    for f in b.figuras:
        hits = [r for r in rows[f.pagina] if r[0] == _norm(f.rotulo)]
        if len(hits) != 1:
            raise IngestError(f"Boletín {b.archivo} p.{f.pagina}: la fila {f.rotulo!r} aparece {len(hits)} veces")
        _, nums, line = hits[0]
        if f.col >= len(nums):
            raise IngestError(f"Boletín {b.archivo} p.{f.pagina}: la fila {f.rotulo!r} tiene {len(nums)} columnas")
        out.append(dict(figure_id=f.figure_id, pagina=f.pagina, cuadro=f.cuadro, universo=f.universo,
                        base=f.base, concepto=f.concepto, valor_texto=nums[f.col],
                        importe_centavos=to_centavos_millones(nums[f.col]), linea=line))
    return out


def make_loader(ejercicio: int, trimestre: int, ds: DatasetDef):
    b = BOLETINES[(ejercicio, trimestre)]

    def load(con: sqlite3.Connection, path: Path, run_id: int):
        figs = extract(b, page_texts(path))
        con.execute("DELETE FROM published_figure WHERE dataset_id=?", (ds.dataset_id,))
        con.executemany(
            "INSERT INTO published_figure VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(ds.dataset_id, run_id, f["figure_id"], ejercicio, b.periodo, f["universo"], f["base"],
              f["concepto"], f["valor_texto"], f["importe_centavos"], UNIDAD, f["pagina"], f["cuadro"],
              f["linea"]) for f in figs])
        return len(figs), f"Boletín Fiscal {trimestre}º trimestre {ejercicio} (datos provisorios para la AN)"
    return load
