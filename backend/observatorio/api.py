"""API local (no son endpoints oficiales). Ejecutar: uvicorn observatorio.api:app"""
from __future__ import annotations

import os
import secrets
import threading

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import balance, config, db, metrics, sync

app = FastAPI(title="Observatorio del Dinero Público Argentino (API local)", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["GET", "POST"], allow_headers=["*"])
_sync_lock = threading.Lock()


def get_con():
    con = db.connect()
    db.init_db(con)
    try:
        yield con
    finally:
        con.close()


def require_admin(x_admin_token: str | None = Header(default=None)):
    """/api/admin/* exige el token definido en ODP_ADMIN_TOKEN (nunca incrustado en el frontend)."""
    expected = os.environ.get("ODP_ADMIN_TOKEN")
    if not expected:
        raise HTTPException(403, "Sincronización por API deshabilitada: definí ODP_ADMIN_TOKEN "
                                 "o usá la CLI (python -m observatorio.cli sync).")
    if not x_admin_token or not secrets.compare_digest(x_admin_token, expected):
        raise HTTPException(401, "Token de administración inválido")


@app.get("/api/health")
def health(con=Depends(get_con)):
    n = con.execute("SELECT COUNT(*) FROM ingestion_run WHERE status='ok'").fetchone()[0]
    return {"ok": True, "db": str(config.DB_PATH), "corridas_ok": n}


@app.get("/api/sources")
def sources(con=Depends(get_con)):
    return [dict(r) for r in con.execute("SELECT * FROM source ORDER BY source_id")]


@app.get("/api/datasets")
def datasets(con=Depends(get_con)):
    return [dict(r) for r in con.execute("SELECT * FROM dataset ORDER BY dataset_id")]


@app.get("/api/coverage")
def coverage(con=Depends(get_con)):
    return metrics.coverage(con)


@app.get("/api/ejercicios")
def ejercicios(con=Depends(get_con)):
    rows = con.execute(
        "SELECT DISTINCT ejercicio FROM fiscal_observation UNION SELECT DISTINCT CAST(substr(periodo,1,4) AS INT) "
        "FROM series_observation WHERE series_id='imig.resultado_primario' ORDER BY 1 DESC")
    return [r[0] for r in rows]


@app.get("/api/summary")
def summary(ejercicio: int, scope: str = "administracion_nacional", con=Depends(get_con)):
    if scope != "administracion_nacional":
        raise HTTPException(400, "Por ahora solo hay cobertura de la Administración Nacional")
    return metrics.summary(con, ejercicio)


@app.get("/api/balance")
def fiscal_balance(ejercicio: int, con=Depends(get_con)):
    """Balance oficial: IMIG, Sector Público Nacional no Financiero, base caja."""
    return balance.balance(con, ejercicio)


@app.get("/api/bridge")
def fiscal_bridge(ejercicio: int, con=Depends(get_con)):
    return balance.bridge(con, ejercicio)


@app.get("/api/expenditures")
def expenditures(ejercicio: int, classification: str = "finalidad", etapa: str = "devengado",
                 parent: str | None = None, limit: int = Query(50, le=500), con=Depends(get_con)):
    if etapa not in ("presupuestado", "vigente", "comprometido", "devengado", "pagado"):
        raise HTTPException(400, f"etapa inválida para gastos: {etapa}")
    try:
        return metrics.breakdown(con, ejercicio, "gasto", classification, etapa, parent, limit)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/revenues")
def revenues(ejercicio: int, classification: str = "tipo", etapa: str = "percibido",
             limit: int = Query(50, le=500), con=Depends(get_con)):
    if etapa not in ("recurso_inicial", "recurso_vigente", "percibido"):
        raise HTTPException(400, f"etapa inválida para recursos: {etapa}")
    try:
        return metrics.breakdown(con, ejercicio, "recurso", classification, etapa, None, limit)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/transfers")
def transfers(con=Depends(get_con)):
    rows = [dict(r) for r in con.execute("SELECT * FROM transfer WHERE relacion_comprobada=1")]
    return {"estado": "ok" if rows else "sin_datos", "items": rows,
            "nota": "Solo se listan transferencias con evidencia pagador→receptor. "
                    "Todavía no hay una fuente conectada que la provea (etapa V2)."}


@app.get("/api/timeseries")
def timeseries(metric: str, desde: str | None = Query(None, alias="from"),
               hasta: str | None = Query(None, alias="to"), con=Depends(get_con)):
    if metric == "totales_anuales":
        return metrics.annual_series(con)
    return metrics.series_monthly(con, metric, desde, hasta)


@app.get("/api/observations/{obs_id}/provenance")
def obs_provenance(obs_id: int, con=Depends(get_con)):
    p = metrics.observation_provenance(con, obs_id)
    if p is None:
        raise HTTPException(404, "Observación inexistente")
    return p


@app.post("/api/admin/sync", dependencies=[Depends(require_admin)])
def admin_sync(force: bool = False, con=Depends(get_con)):
    if not _sync_lock.acquire(blocking=False):
        raise HTTPException(409, "Ya hay una sincronización en curso")
    try:
        return sync.sync_all(con, force=force)
    finally:
        _sync_lock.release()


_dist = config.ROOT / "frontend" / "dist"
if _dist.is_dir():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        return FileResponse(_dist / "index.html")
