from decimal import Decimal
from functools import partial

from conftest import FIX, col_sum, make_totales, zip_csv

from observatorio import metrics, sync
from observatorio.ingest import presupuesto_abierto as pa
from observatorio.ingest.base import run_ingestion


def _load_all(con, tmp_path, overrides=None):
    for ds, loader, src in [
        (pa.credito_def(2026), pa.load_credito, FIX / "credito-anual-2026-muestra.csv"),
        (pa.recursos_def(2026), pa.load_recursos, FIX / "recursos-anual-2026-muestra.csv"),
    ]:
        run_ingestion(con, ds, partial(loader, ds=ds), local_file=zip_csv(src, tmp_path / f"{ds.dataset_id}.zip"))
    tot = pa.totales_def()
    run_ingestion(con, tot, partial(pa.load_totales, ds=tot), local_file=make_totales(tmp_path, 2026, overrides))


def test_conciliacion_coincide(env, tmp_path):
    _load_all(env, tmp_path)
    recs = sync.reconcile(env, 2026)
    assert len(recs) == 9
    assert all(r["conclusion"] == "coincide" for r in recs), recs


def test_conciliacion_detecta_discrepancia(env, tmp_path):
    _load_all(env, tmp_path, {"credito_devengado": Decimal("1")})
    recs = {r["comparacion"].split(":")[1]: r for r in sync.reconcile(env, 2026)}
    assert recs["credito_devengado"]["conclusion"] == "discrepa"
    assert recs["credito_vigente"]["conclusion"] == "coincide"


def test_conciliacion_sin_dato(env, tmp_path):
    recs = sync.reconcile(env, 2026)
    assert all(r["conclusion"] == "sin_dato" for r in recs)


def test_gasto_primario_excluye_intereses(env, tmp_path):
    _load_all(env, tmp_path)
    s = {c["etiqueta"]: c for c in metrics.summary(env, 2026)["cards"]}
    cred = FIX / "credito-anual-2026-muestra.csv"
    total = col_sum(cred, "credito_devengado")
    inter = col_sum(cred, "credito_devengado",
                    lambda r: r["clasificador_economico_8_digitos_id"].startswith("2131"))
    assert inter > 0
    assert Decimal(s["Gasto total (corriente + capital)"]["valor_millones"]) == total
    assert Decimal(s["Gasto primario"]["valor_millones"]) == total - inter
    ing = col_sum(FIX / "recursos-anual-2026-muestra.csv", "recurso_ingresado_percibido")
    assert Decimal(s["Resultado financiero"]["valor_millones"]) == ing - total


def test_cada_cifra_tiene_procedencia(env, tmp_path):
    _load_all(env, tmp_path)
    for c in metrics.summary(env, 2026)["cards"]:
        assert c["unidad"] and c["etapa"] and c["periodo"] and c["universo"]
        for p in c["procedencia"]:
            assert p["url"].startswith("https://") and p["sha256"] and p["archivo_crudo"]


def test_sin_datos_no_es_cero(env):
    s = metrics.summary(env, 2026)
    for c in s["cards"]:
        assert c["valor_millones"] is None and c["estado"] == "sin_datos"
    assert metrics.breakdown(env, 2026, "gasto", "finalidad", "devengado")["estado"] == "sin_datos"


def test_breakdown_participaciones(env, tmp_path):
    _load_all(env, tmp_path)
    b = metrics.breakdown(env, 2026, "gasto", "funcion", "devengado")
    assert sum(Decimal(i["valor_millones"]) for i in b["items"]) == Decimal(b["total_millones"])
    assert "no representa pagos" in b["nota"]


def test_variaciones():
    assert metrics.pct_change(Decimal(110), Decimal(100)) == Decimal(10)
    assert metrics.pct_change(Decimal(1), Decimal(0)) is None
    assert metrics.pct_change(None, Decimal(1)) is None
    assert metrics.real_change(Decimal(10), Decimal(10)) == Decimal(0)
    assert metrics.real_change(Decimal(10), None) is None
