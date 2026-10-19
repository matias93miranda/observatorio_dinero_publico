from functools import partial

from conftest import FIX, col_sum, zip_csv

from observatorio.ingest import presupuesto_abierto as pa
from observatorio.ingest.base import run_ingestion
from observatorio.money import millones_to_centavos


def _load_credito(con, tmp_path, **kw):
    ds = pa.credito_def(2026)
    z = zip_csv(FIX / "credito-anual-2026-muestra.csv", tmp_path / "c.zip")
    return run_ingestion(con, ds, partial(pa.load_credito, ds=ds), local_file=z, **kw)


def test_carga_credito_y_sumas_por_etapa(env, tmp_path):
    res = _load_credito(env, tmp_path)
    assert res["status"] == "ok" and res["rows"] == 41
    assert res["fecha_publicacion"] == "16 Octubre 2026"
    for col, etapa in pa.CREDITO_MEDIDAS.items():
        got = env.execute("SELECT SUM(importe_centavos) FROM fiscal_observation WHERE etapa=?",
                          (etapa,)).fetchone()[0]
        exp = col_sum(FIX / "credito-anual-2026-muestra.csv", col)
        assert got == millones_to_centavos(str(exp)), etapa


def test_texto_original_conservado_y_linea(env, tmp_path):
    _load_credito(env, tmp_path)
    r = env.execute("SELECT * FROM fiscal_observation WHERE source_line=2 AND etapa='presupuestado'").fetchone()
    assert r["importe_original"] == "112314,626039"
    assert r["entity_id"] == "AN/2026/312"
    assert r["finalidad_funcion"] == "1.1"


def test_crudo_guardado_con_sha(env, tmp_path):
    from observatorio import config
    from observatorio.ingest.base import sha256_file
    _load_credito(env, tmp_path)
    a = env.execute("SELECT * FROM raw_artifact").fetchone()
    assert sha256_file(config.RAW_DIR / a["path"]) == a["sha256"]


def test_sin_cambios_no_duplica(env, tmp_path):
    _load_credito(env, tmp_path)
    res = _load_credito(env, tmp_path)
    assert res["status"] == "unchanged"
    assert env.execute("SELECT COUNT(*) FROM raw_artifact").fetchone()[0] == 1
    assert env.execute("SELECT COUNT(*) FROM fiscal_observation").fetchone()[0] == 41 * 5


def test_cambio_de_esquema_falla_y_conserva_datos_previos(env, tmp_path):
    _load_credito(env, tmp_path)
    bad = tmp_path / "bad.csv"
    lines = (FIX / "credito-anual-2026-muestra.csv").read_text(encoding="utf-8-sig").splitlines()
    bad.write_text("\n".join([lines[0].replace("credito_devengado", "devengado_x")] + lines[1:]),
                   encoding="utf-8")
    ds = pa.credito_def(2026)
    res = run_ingestion(env, ds, partial(pa.load_credito, ds=ds), local_file=bad)
    assert res["status"] == "failed" and "faltan columnas" in res["error"]
    assert env.execute("SELECT COUNT(*) FROM fiscal_observation").fetchone()[0] == 41 * 5


def test_celda_vacia_falla_no_se_vuelve_cero(env, tmp_path):
    lines = (FIX / "credito-anual-2026-muestra.csv").read_text(encoding="utf-8-sig").splitlines()
    import csv, io
    rows = list(csv.reader(io.StringIO("\n".join(lines))))
    i = rows[0].index("credito_pagado")
    rows[1][i] = ""
    out = io.StringIO()
    csv.writer(out).writerows(rows)
    p = tmp_path / "vacio.csv"
    p.write_text(out.getvalue(), encoding="utf-8")
    ds = pa.credito_def(2026)
    res = run_ingestion(env, ds, partial(pa.load_credito, ds=ds), local_file=p)
    assert res["status"] == "failed" and "celda vacía" in res["error"]
    assert env.execute("SELECT COUNT(*) FROM fiscal_observation").fetchone()[0] == 0


def test_descarga_fallida_registra_error(env, monkeypatch):
    from observatorio.ingest import base
    ds = pa.credito_def(1900)  # URL inexistente
    def boom(url, dest):
        raise base.IngestError(f"No se pudo descargar {url}: HTTP Error 404")
    monkeypatch.setattr(base, "download", boom)
    res = run_ingestion(env, ds, partial(pa.load_credito, ds=ds))
    assert res["status"] == "failed" and "404" in res["error"]
    assert env.execute("SELECT COUNT(*) FROM fiscal_observation").fetchone()[0] == 0


def test_universo_distinto_se_rechaza(env, tmp_path):
    txt = (FIX / "credito-anual-2026-muestra.csv").read_text(encoding="utf-8-sig")
    p = tmp_path / "otro.csv"
    p.write_text(txt.replace("Administración Nacional", "Empresas Públicas", 1), encoding="utf-8")
    ds = pa.credito_def(2026)
    res = run_ingestion(env, ds, partial(pa.load_credito, ds=ds), local_file=p)
    assert res["status"] == "failed" and "universo" in res["error"]


def test_recursos(env, tmp_path):
    ds = pa.recursos_def(2026)
    z = zip_csv(FIX / "recursos-anual-2026-muestra.csv", tmp_path / "r.zip")
    res = run_ingestion(env, ds, partial(pa.load_recursos, ds=ds), local_file=z)
    assert res["status"] == "ok" and res["rows"] == 30
    got = env.execute("SELECT SUM(importe_centavos) FROM fiscal_observation WHERE etapa='percibido'").fetchone()[0]
    exp = col_sum(FIX / "recursos-anual-2026-muestra.csv", "recurso_ingresado_percibido")
    assert got == millones_to_centavos(str(exp))


def test_partida_fuera_de_composicion_se_rechaza(env, tmp_path):
    txt = (FIX / "credito-anual-2026-muestra.csv").read_text(encoding="utf-8-sig")
    p = tmp_path / "fig.csv"
    p.write_text(txt.replace(",21211000,", ",31100000,", 1), encoding="utf-8")
    ds = pa.credito_def(2026)
    res = run_ingestion(env, ds, partial(pa.load_credito, ds=ds), local_file=p)
    assert res["status"] == "failed" and "doble conteo" in res["error"]
