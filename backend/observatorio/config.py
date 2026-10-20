import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("ODP_DATA_DIR", ROOT / "data"))
RAW_DIR = DATA_DIR / "raw"
DB_PATH = Path(os.environ.get("ODP_DB", DATA_DIR / "observatorio.sqlite"))
# Solo ASCII: urllib codifica el header en latin-1 y argentina.gob.ar responde 403 a "investigación"
# (verificado 2026-10-19).
USER_AGENT = "ObservatorioDineroPublico/0.1 (uso local, investigacion)"
HTTP_TIMEOUT = float(os.environ.get("ODP_HTTP_TIMEOUT", "120"))
