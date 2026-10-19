import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("ODP_DATA_DIR", ROOT / "data"))
RAW_DIR = DATA_DIR / "raw"
DB_PATH = Path(os.environ.get("ODP_DB", DATA_DIR / "observatorio.sqlite"))
USER_AGENT = "ObservatorioDineroPublico/0.1 (uso local, investigación)"
HTTP_TIMEOUT = float(os.environ.get("ODP_HTTP_TIMEOUT", "120"))
