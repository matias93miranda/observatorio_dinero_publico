import csv
import io
import zipfile
from decimal import Decimal
from pathlib import Path

import pytest

FIX = Path(__file__).parent / "fixtures"


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """Base y directorio de crudos aislados por test."""
    from observatorio import config
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "t.sqlite")
    from observatorio import db
    con = db.connect(tmp_path / "t.sqlite")
    db.init_db(con)
    yield con
    con.close()


def zip_csv(src: Path, dest: Path) -> Path:
    with zipfile.ZipFile(dest, "w") as z:
        z.write(src, src.name)
    return dest


def col_sum(path: Path, col: str, where=lambda r: True) -> Decimal:
    """Suma independiente (csv + Decimal) para contrastar con la base."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        return sum((Decimal(r[col].replace(",", ".")) for r in csv.DictReader(f) if where(r)),
                   Decimal(0))


def fmt(d: Decimal) -> str:
    return str(d).replace(".", ",")


def make_totales(tmp: Path, ejercicio: int, overrides: dict | None = None) -> Path:
    """Totales SINTÉTICOS: calculados desde las muestras reales para probar la conciliación."""
    cred, rec = FIX / "credito-anual-2026-muestra.csv", FIX / "recursos-anual-2026-muestra.csv"
    no_int = lambda r: not r["clasificador_economico_8_digitos_id"].startswith("2131")
    vals = {
        "credito_presupuestado": col_sum(cred, "credito_presupuestado"),
        "credito_vigente": col_sum(cred, "credito_vigente"),
        "credito_devengado": col_sum(cred, "credito_devengado"),
        "recurso_inicial": col_sum(rec, "recurso_inicial"),
        "recurso_vigente": col_sum(rec, "recurso_vigente"),
        "recurso_ingresado_percibido": col_sum(rec, "recurso_ingresado_percibido"),
        "gasto_primario_presupuestado": col_sum(cred, "credito_presupuestado", no_int),
        "gasto_primario_vigente": col_sum(cred, "credito_vigente", no_int),
        "gasto_primario_devengado": col_sum(cred, "credito_devengado", no_int),
    }
    vals.update(overrides or {})
    header = (FIX / "totales-encabezado.csv").read_text(encoding="utf-8-sig").strip().split(",")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    row = {"ejercicio_presupuestario": ejercicio,
           "ultima_actualizacion_fecha": f"Última actualización del ejercicio {ejercicio}: 16 Octubre 2026."}
    row.update({k: (fmt(v) if isinstance(v, Decimal) else v) for k, v in vals.items()})
    w.writerow([row[h] for h in header])
    p = tmp / "totales.csv"
    p.write_text(buf.getvalue(), encoding="utf-8")
    return p
