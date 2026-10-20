"""Criterios contables y cambios metodológicos, con cita textual verificada contra el crudo.

Cada nota con `cita` se verifica buscando el texto en el PDF guardado del dataset indicado
(comparación sin espacios, porque la extracción de texto de PDF parte palabras: 'entr e').
Si la cita no aparece, la nota queda 'no_encontrada_en_crudo' y la interfaz lo muestra.
Las notas sin cita son hallazgos propios: llevan el procedimiento para reproducirlos.
"""
from __future__ import annotations

import sqlite3
import unicodedata
from dataclasses import dataclass

from . import config
from .db import now_iso

BOLETIN = "onp_boletin_2025_t4"
BOLETIN_URL = "https://www.mecon.gob.ar/onp/documentos/boletin/4totrim25/4totrim25.pdf"
CGN_MET = "cgn_ci_2025_metodologia_spnf"
CGN_MET_URL = ("https://www.argentina.gob.ar/sites/default/files/"
               "gestion-financiera-consolidada_aspectos_generales_y_metodologicos-tomoi-2025.pdf")
CI35_URL = "https://www.argentina.gob.ar/sites/default/files/cuadro35-tomoi-2025.xlsx"


@dataclass(frozen=True)
class Nota:
    nota_id: str
    tema: str
    aplica_a: str
    resumen: str
    fuente_url: str
    ubicacion: str
    cita: str | None = None
    dataset: str | None = None
    desde: str | None = None
    hasta: str | None = None


NOTAS = (
    Nota("caja_spn_2017_rentas_intra_sp",
         tema="Rentas del BCRA y del FGS e intereses intra-sector público en el resultado base caja",
         aplica_a="IMIG / resultado base caja del Sector Público Nacional (Secretaría de Hacienda)",
         desde="2017",
         resumen=("Desde 2017 el resultado base caja excluye de los ingresos las rentas de la propiedad que el FGS "
                  "cobra por deuda intra-sector público y las provenientes del BCRA, y excluye de los gastos los "
                  "intereses pagados dentro del sector público. Antes de 2017 la serie del IMIG no es comparable "
                  "sin ajuste en rentas e intereses."),
         cita=("A partir del año 2017, se cambia la metodología de exposición del resultado fiscal en base caja del "
               "Sector Público Nacional. Por el lado de los recursos se exponen las rentas de la propiedad netas, de "
               "las percibidas por la Administración Nacional de Seguridad Social a través del Fondo de Garantía de "
               "Sustentabilidad (FGS) por pagos de intereses provenientes del Sector Público Nacional (originadas en "
               "operaciones de financiamiento intra sector público nacional y de las provenientes del Banco Central de "
               "la República Argentina). Del mismo modo, por el lado de los gastos, los intereses también se reflejan "
               "por el neto, es decir que se excluyen aquellos pagados intra sector público nacional."),
         dataset=BOLETIN, fuente_url=BOLETIN_URL, ubicacion="Boletín Fiscal 4T-2025, p. 6"),
    Nota("an_metodologia_habitual",
         tema="La Administración Nacional mantiene la exposición habitual (con todas las rentas)",
         aplica_a="Presupuesto Abierto, Cuenta de Inversión (columna AN), Boletín Fiscal cuadro 1",
         resumen=("Los resultados de la AN, empresas, entes y fondos fiduciarios incluyen todas las rentas de la "
                  "propiedad (BCRA y FGS incluidas) y los intereses brutos. Por eso el resultado de la AN no es "
                  "comparable con el del IMIG sin restar esas rentas."),
         cita=("En lo que respecta al resultado fiscal de la Administración Nacional, las Empresas y Sociedades del "
               "Estado, los Entes Públicos excluidos expresamente de la Administración Nacional y los Fondos "
               "Fiduciarios, se mantiene la metodología de exposición habitual."),
         dataset=BOLETIN, fuente_url=BOLETIN_URL, ubicacion="Boletín Fiscal 4T-2025, p. 6"),
    Nota("bcra_utilidades_2025",
         tema="Utilidades del BCRA ingresadas en 2025",
         aplica_a="Rentas de la propiedad de la AN 2025 (Presupuesto Abierto, Cuenta de Inversión, Boletín)",
         desde="2025", hasta="2025",
         resumen=("En 2025 la AN percibió 11.976.386,7 M$ de rentas del BCRA (0,0 en 2024), correspondientes a "
                  "utilidades del ejercicio 2024 del BCRA. Explican la mayor parte de la diferencia de rentas entre "
                  "la AN y el IMIG en 2025."),
         cita=("el incremento en las Rentas de la Propiedad se deriva de los ingresos generados por el BCRA en "
               "concepto de utilidades correspondientes el ejercicio 2024."),
         dataset=BOLETIN, fuente_url=BOLETIN_URL, ubicacion="Boletín Fiscal 4T-2025, p. 33 (monto: cuadro 5, p. 62)"),
    Nota("boletin_momentos_registro",
         tema="Momento de registro en el Boletín Fiscal (base devengado)",
         aplica_a="Boletín Fiscal, cuentas AIF base devengado de AN, fondos fiduciarios, entes y empresas",
         resumen="AN: ingresos percibidos. Fondos fiduciarios, otros entes y empresas: ingresos devengados. Gastos: devengado en todos.",
         cita=("En lo que se refiere a los ingresos en la Administración Nacional la ejecución corresponde a los "
               "ingresos percibidos, mientras que el criterio utilizado para los Fondos Fiduciarios, Otros Entes y "
               "Empresas Públicas es el devengado. Por su parte, en la ejecución de los gastos se aplica en todos los "
               "subsectores el momento del devengado."),
         dataset=BOLETIN, fuente_url=BOLETIN_URL, ubicacion="Boletín Fiscal 4T-2025, p. 5"),
    Nota("deuda_exigible_no_es_flotante",
         tema="Devengado − pagado no es el saldo de deuda flotante",
         aplica_a="Presupuesto Abierto (crédito devengado y pagado), Boletín Fiscal cuadro 1",
         resumen=("La diferencia devengado − pagado de un archivo de ejecución es gasto devengado del ejercicio que "
                  "seguía impago a la fecha de corte del archivo (un flujo del ejercicio). No es el saldo de deuda "
                  "flotante: ese stock incluye obligaciones impagas de ejercicios anteriores, que se cancelan como "
                  "aplicaciones financieras (excluidas de los archivos de crédito de Presupuesto Abierto). En la "
                  "cuenta AIF, el devengado impago al cierre aparece como 'deuda exigible' dentro de las fuentes "
                  "financieras."),
         cita=("Sobre los coeficientes de ejecución repercuten los montos correspondientes a Deuda Exigible dentro "
               "de las fuentes financieras (por erogaciones devengadas no pagadas al cierre del período bajo análisis)"),
         dataset=BOLETIN, fuente_url=BOLETIN_URL, ubicacion="Boletín Fiscal 4T-2025, p. 57 (nota al cuadro 1)"),
    Nota("cgn_momento_registro",
         tema="Momento de registro en la Cuenta de Inversión (SPNF consolidado)",
         aplica_a="Cuenta de Inversión, Cuadro 35",
         resumen=("Devengado para erogaciones y recaudado para recursos; las transferencias entre entes del "
                  "universo se registran devengadas de ambos lados para poder eliminarlas."),
         cita=("El momento de registro empleado para las diferentes operaciones incluidas en el presente estado ha "
               "sido, en términos generales, el del devengado para las erogaciones y el del recaudado para los "
               "recursos."),
         dataset=CGN_MET, fuente_url=CGN_MET_URL, ubicacion="Gestión Financiera Consolidada, aspectos metodológicos"),
    Nota("cgn_no_consolida_compraventa",
         tema="Operaciones intra-SPNF que la Cuenta de Inversión no elimina",
         aplica_a="Cuenta de Inversión, Cuadro 35 (columna Eliminaciones)",
         resumen=("Solo se eliminan transferencias y contribuciones figurativas. Las compras y ventas de bienes y "
                  "servicios y los pagos de tributos entre subsectores quedan sin consolidar (cuentan dos veces en "
                  "ingresos y gastos totales, sin efecto sobre el resultado del conjunto)."),
         cita=("no se ha consolidado la compraventa de bienes y servicios, ni los pagos de tributos que realizan "
               "entre sí los distintos subsectores"),
         dataset=CGN_MET, fuente_url=CGN_MET_URL, ubicacion="Gestión Financiera Consolidada, aspectos metodológicos"),
    Nota("cgn_cobertura_incompleta_2025",
         tema="Entes sin información en el consolidado 2025",
         aplica_a="Cuenta de Inversión 2025, Cuadro 35",
         desde="2025", hasta="2025",
         resumen="Dos fondos fiduciarios no presentaron su cuenta AIF y quedaron fuera del consolidado.",
         cita=("no se contó con información del Fondo Fiduciario de Infraestructura Regional ni del Fondo "
               "Fiduciario para el Desarrollo de Energías Renovables"),
         dataset=CGN_MET, fuente_url=CGN_MET_URL, ubicacion="Gestión Financiera Consolidada, aspectos metodológicos"),
    Nota("ci35_ref_error_2025",
         tema="Celdas con error de fórmula en el Cuadro 35 publicado",
         aplica_a="Cuenta de Inversión 2025, Cuadro 35, celdas K52 y K53",
         desde="2025", hasta="2025",
         resumen=("El total SPNF de 'Transferencias de capital a provincias y municipios' y de 'Otras' figura como "
                  "#REF! en el archivo oficial. Se guardan como error, sin valor; no se reconstruyen."),
         fuente_url=CI35_URL, ubicacion="cuadro35-tomoi-2025.xlsx, celdas K52:K53"),
    Nota("cortes_an_2025",
         tema="Tres cortes publicados de la ejecución 2025 de la AN",
         aplica_a="Presupuesto Abierto (totales y detalle), Boletín Fiscal 4T-2025, Cuenta de Inversión 2025",
         desde="2025", hasta="2025",
         resumen=("La fila 2025 de totales-de-presupuesto.csv, el Boletín Fiscal 4T (datos provisorios) y la Cuenta "
                  "de Inversión (cierre) dan cifras distintas para la AN. Los archivos de detalle de Presupuesto "
                  "Abierto coinciden con la Cuenta de Inversión: ese es el cierre. La diferencia con los cortes "
                  "previos es revisión, no error, y se muestra como tal."),
         fuente_url=CI35_URL,
         ubicacion=("Reproducir: comparar la columna E (Total AN) del Cuadro 35 con la suma de credito-anual-2025 y "
                    "recursos-anual-2025; ver conciliaciones 'cruce:2025:*'")),
    Nota("cortes_an_sin_ci",
         tema="Sin Cuenta de Inversión conectada, no se sabe qué corte de la AN es el cierre",
         aplica_a="Puente AN → IMIG de los ejercicios sin Cuadro 35 cargado",
         resumen=("La diferencia entre el detalle de Presupuesto Abierto y el Boletín Fiscal del 4º trimestre se "
                  "muestra como diferencia entre dos cortes publicados. Solo en 2025 se verificó (contra la Cuenta "
                  "de Inversión) que el detalle de Presupuesto Abierto es el cierre; en los demás años no se afirma."),
         fuente_url=BOLETIN_URL,
         ubicacion="Reproducir: /api/bridge?ejercicio=AAAA devuelve partida_es_cierre=false"),
    Nota("boletin_2022_rentas_emisiones_primarias",
         tema="Rentas de la propiedad 2022 de la AN incluyen las asociadas a emisiones primarias del Tesoro",
         aplica_a="Boletín Fiscal 4T-2022, cuadro 1 (AN, recaudado/devengado)",
         desde="2022", hasta="2022",
         resumen=("En 2022 las rentas de la propiedad percibidas por la AN contemplan las asociadas a emisiones "
                  "primarias del Tesoro (primas de colocación). Inflan la fila de rentas frente a otros años; no "
                  "son rentas del BCRA ni del FGS."),
         cita="Las rentas de la propiedad percibidas contemplan aquellas asociadas a emisiones primarias del Tesoro Nacional.",
         dataset="onp_boletin_2022_t4",
         fuente_url="https://www.mecon.gob.ar/onp/documentos/boletin/4totrim22/4totrim22.pdf",
         ubicacion="Boletín Fiscal 4T-2022, p. 63 (nota (1) al cuadro 1)"),
    Nota("universo_imig_vs_ci",
         tema="Universos distintos: SPN base caja (IMIG) y SPNF de la Cuenta de Inversión",
         aplica_a="IMIG, Boletín Fiscal cuadros 4-5, Cuenta de Inversión Cuadro 35",
         resumen=("En la base caja, las empresas públicas entran solo por su resultado operativo neto "
                  "(superávit/déficit operativo) y las universidades como destino de transferencias. En el Cuadro 35 "
                  "de la Cuenta de Inversión, empresas y universidades son subsectores con todos sus ingresos y "
                  "gastos. Por eso los totales de ingresos y gastos no se comparan entre ambas fuentes; solo los "
                  "resultados, y con puente."),
         fuente_url=BOLETIN_URL,
         ubicacion="Boletín Fiscal 4T-2025, cuadros 4 (p. 61) y 5 (p. 62); Cuenta de Inversión 2025, Cuadro 35"),
)


def _squash(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).lower()
    return "".join(s.split()).replace("­", "")


def _raw_text(con: sqlite3.Connection, dataset_id: str) -> str | None:
    row = con.execute("SELECT a.path FROM raw_artifact a JOIN ingestion_run r USING(run_id) WHERE r.dataset_id=? "
                      "AND r.status='ok' ORDER BY r.run_id DESC LIMIT 1", (dataset_id,)).fetchone()
    if row is None or not (config.RAW_DIR / row[0]).exists():
        return None
    from .ingest.boletin_fiscal import page_texts
    return "".join(page_texts(config.RAW_DIR / row[0]))


def refresh(con: sqlite3.Connection) -> list[dict]:
    """Recarga las notas y verifica cada cita contra el crudo más reciente."""
    cache: dict[str, str | None] = {}
    out = []
    con.execute("DELETE FROM metodologia_nota")
    for n in NOTAS:
        if n.cita is None:
            estado = "hallazgo_reproducible"
        else:
            if n.dataset not in cache:
                txt = _raw_text(con, n.dataset)
                cache[n.dataset] = None if txt is None else _squash(txt)
            txt = cache[n.dataset]
            estado = ("crudo_no_disponible" if txt is None
                      else "verificada_en_crudo" if _squash(n.cita) in txt else "no_encontrada_en_crudo")
        con.execute("INSERT INTO metodologia_nota VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (n.nota_id, n.tema, n.aplica_a, n.desde, n.hasta, n.resumen, n.cita, n.dataset,
                     n.fuente_url, n.ubicacion, estado, now_iso()))
        out.append({"nota_id": n.nota_id, "estado_verificacion": estado})
    con.commit()
    return out


def listar(con: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in con.execute("SELECT * FROM metodologia_nota ORDER BY vigencia_desde, nota_id")]
