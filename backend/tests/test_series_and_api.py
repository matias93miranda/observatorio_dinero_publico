from conftest import FIX

from observatorio.ingest import series_tiempo as st
from observatorio.ingest.base import run_ingestion


def test_serie_hueco_es_null(env):
    sid = "148.3_INIVELNAL_DICI_M_26"
    res = run_ingestion(env, st.series_def(sid), st.make_loader(sid), local_file=FIX / "serie-con-hueco.csv")
    assert res["status"] == "ok" and res["rows"] == 3
    vals = dict(env.execute("SELECT periodo, valor_original FROM series_observation").fetchall())
    assert vals["2017-01"] == "101.5859"      # texto original, sin pasar por float
    assert vals["2017-02"] is None             # sin dato, no 0
    assert "2017-01" in res["fecha_publicacion"]


def test_api_basica(env, monkeypatch):
    from fastapi.testclient import TestClient
    from observatorio.api import app
    c = TestClient(app)
    assert c.get("/api/health").json()["ok"] is True
    assert c.get("/api/summary", params={"ejercicio": 2026}).json()["cards"][0]["estado"] == "sin_datos"
    assert c.get("/api/summary", params={"ejercicio": 2026, "scope": "provincias"}).status_code == 400
    assert c.get("/api/expenditures", params={"ejercicio": 2026, "etapa": "percibido"}).status_code == 400
    assert c.get("/api/transfers").json()["estado"] == "sin_datos"
    assert c.get("/api/observations/999/provenance").status_code == 404


def test_admin_sync_protegido(env, monkeypatch):
    from fastapi.testclient import TestClient
    from observatorio.api import app
    c = TestClient(app)
    monkeypatch.delenv("ODP_ADMIN_TOKEN", raising=False)
    assert c.post("/api/admin/sync").status_code == 403
    monkeypatch.setenv("ODP_ADMIN_TOKEN", "secreto")
    assert c.post("/api/admin/sync", headers={"X-Admin-Token": "otro"}).status_code == 401
