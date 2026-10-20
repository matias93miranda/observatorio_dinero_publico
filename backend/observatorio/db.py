import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import config

SCHEMA_VERSION = 2


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path: Path | None = None) -> sqlite3.Connection:
    path = Path(path or config.DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    # FastAPI puede abrir la conexión (dependencia) y usarla (endpoint) en hilos distintos;
    # cada request usa su propia conexión, así que no se comparte entre requests.
    con = sqlite3.connect(path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    return con


def init_db(con: sqlite3.Connection) -> None:
    sql = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
    con.executescript(sql)
    # Las tablas nuevas se crean con IF NOT EXISTS: una base v1 queda en v2 sin perder datos.
    cur = con.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
    if cur is None or cur < SCHEMA_VERSION:
        con.execute("INSERT INTO schema_version VALUES (?, ?)", (SCHEMA_VERSION, now_iso()))
    con.commit()
