"""Infraestructura común de ingesta: descarga, checksum, registro de corridas.

Reglas:
  * El archivo crudo se guarda tal cual llegó, con su SHA-256.
  * Un fallo de descarga o de validación deja la corrida en 'failed' y NO toca los
    datos ya cargados de ese dataset (la carga reemplaza todo en una transacción).
  * Si el SHA-256 coincide con la última corrida OK, la corrida queda 'unchanged'.
"""
from __future__ import annotations

import hashlib
import sqlite3
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .. import config
from ..db import now_iso


class IngestError(RuntimeError):
    """Error legible para mostrar en la interfaz."""


@dataclass(frozen=True)
class SourceDef:
    source_id: str
    organismo: str
    base_url: str
    licencia: str | None
    frecuencia_publicada: str | None
    notas: str | None = None


@dataclass(frozen=True)
class DatasetDef:
    dataset_id: str
    source: SourceDef
    nombre: str
    url: str
    universo: str
    nivel_gobierno: str
    unidad: str
    cobertura_temporal: str | None = None
    granularidad: str | None = None
    metodologia: str | None = None


def register(con: sqlite3.Connection, ds: DatasetDef) -> None:
    s = ds.source
    con.execute(
        "INSERT OR REPLACE INTO source VALUES (?,?,?,?,?,?)",
        (s.source_id, s.organismo, s.base_url, s.licencia, s.frecuencia_publicada, s.notas),
    )
    con.execute(
        "INSERT OR REPLACE INTO dataset VALUES (?,?,?,?,?,?,?,?,?,?)",
        (ds.dataset_id, s.source_id, ds.nombre, ds.url, ds.universo, ds.nivel_gobierno,
         ds.cobertura_temporal, ds.granularidad, ds.unidad, ds.metodologia),
    )


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": config.USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=config.HTTP_TIMEOUT) as r, open(tmp, "wb") as f:
            if r.status != 200:
                raise IngestError(f"HTTP {r.status} al descargar {url}")
            while chunk := r.read(1 << 20):
                f.write(chunk)
    except IngestError:
        tmp.unlink(missing_ok=True)
        raise
    except Exception as e:  # red, DNS, timeout, HTTP 4xx/5xx
        tmp.unlink(missing_ok=True)
        raise IngestError(f"No se pudo descargar {url}: {e}") from e
    if tmp.stat().st_size == 0:
        tmp.unlink()
        raise IngestError(f"Descarga vacía desde {url}")
    tmp.replace(dest)


def last_ok_sha(con: sqlite3.Connection, dataset_id: str) -> str | None:
    row = con.execute(
        "SELECT sha256 FROM ingestion_run WHERE dataset_id=? AND status='ok' "
        "ORDER BY run_id DESC LIMIT 1", (dataset_id,)).fetchone()
    return row[0] if row else None


def start_run(con: sqlite3.Connection, ds: DatasetDef) -> int:
    cur = con.execute(
        "INSERT INTO ingestion_run (dataset_id, started_at, status, url) VALUES (?,?,?,?)",
        (ds.dataset_id, now_iso(), "running", ds.url))
    con.commit()
    return cur.lastrowid


def finish_run(con: sqlite3.Connection, run_id: int, status: str, *, sha256=None,
               fecha_publicacion=None, rows_loaded=None, error=None) -> None:
    con.execute(
        "UPDATE ingestion_run SET finished_at=?, status=?, sha256=COALESCE(?, sha256), "
        "fecha_publicacion=?, rows_loaded=?, error=? WHERE run_id=?",
        (now_iso(), status, sha256, fecha_publicacion, rows_loaded, error, run_id))
    con.commit()


def fetch_artifact(con: sqlite3.Connection, ds: DatasetDef, run_id: int,
                   local_file: Path | None = None) -> tuple[Path, str]:
    """Descarga (o toma un archivo local, para pruebas) y lo registra como raw_artifact."""
    fname = ds.url.rstrip("/").split("/")[-1].split("?")[0] or "download"
    if not Path(fname).suffix:
        fname += ".csv"
    stamp = now_iso().replace(":", "").replace("+0000", "Z")
    dest = config.RAW_DIR / ds.source.source_id / ds.dataset_id / f"{stamp}_{fname}"
    if local_file is not None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(Path(local_file).read_bytes())
    else:
        download(ds.url, dest)
    sha = sha256_file(dest)
    con.execute(
        "UPDATE ingestion_run SET sha256=? WHERE run_id=?", (sha, run_id))
    con.execute(
        "INSERT INTO raw_artifact (run_id, path, size_bytes, sha256, formato, downloaded_at) "
        "VALUES (?,?,?,?,?,?)",
        (run_id, str(dest.relative_to(config.RAW_DIR)), dest.stat().st_size, sha,
         dest.suffix.lstrip("."), now_iso()))
    con.commit()
    return dest, sha


def run_ingestion(con: sqlite3.Connection, ds: DatasetDef, loader, *, force=False,
                  local_file: Path | None = None) -> dict:
    """Orquesta una corrida. `loader(con, path, run_id) -> (rows, fecha_publicacion)`
    debe hacer DELETE+INSERT del dataset sin commitear; acá se commitea o se revierte."""
    register(con, ds)
    con.commit()
    run_id = start_run(con, ds)
    try:
        path, sha = fetch_artifact(con, ds, run_id, local_file)
        if not force and sha == last_ok_sha(con, ds.dataset_id):
            # mismo contenido que la última carga: no duplicar el crudo en disco
            path.unlink(missing_ok=True)
            con.execute("DELETE FROM raw_artifact WHERE run_id=?", (run_id,))
            finish_run(con, run_id, "unchanged", sha256=sha)
            return {"dataset_id": ds.dataset_id, "run_id": run_id, "status": "unchanged"}
        rows, fecha_pub = loader(con, path, run_id)
        con.commit()
    except Exception as e:
        con.rollback()
        msg = str(e) if isinstance(e, IngestError) else f"{type(e).__name__}: {e}"
        finish_run(con, run_id, "failed", error=msg)
        return {"dataset_id": ds.dataset_id, "run_id": run_id, "status": "failed", "error": msg}
    finish_run(con, run_id, "ok", sha256=sha, fecha_publicacion=fecha_pub, rows_loaded=rows)
    return {"dataset_id": ds.dataset_id, "run_id": run_id, "status": "ok", "rows": rows,
            "fecha_publicacion": fecha_pub}
