import csv
import io
from decimal import Decimal

from conftest import FIX

from observatorio import balance, puente
from observatorio.ingest import imig
from observatorio.ingest.base import run_ingestion


def _load(con, path=FIX / "imig-muestra.csv"):
    return run_ingestion(con, imig.dataset_def(), imig.load, local_file=path)


def _rows():
    return list(csv.DictReader(open(FIX / "imig-muestra.csv", encoding="utf-8-sig")))


def _write(tmp_path, rows, fieldnames=None):
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=fieldnames or list(rows[0]))
    w.writeheader()
    w.writerows(rows)
    p = tmp_path / "imig.csv"
    p.write_text(out.getvalue(), encoding="utf-8")
    return p


def test_identidades_se_cumplen_en_datos_reales():
    for r in _rows():
        dp, df = imig.check_identities(r)
        assert abs(dp) <= imig.TOLERANCIA_M and abs(df) <= imig.TOLERANCIA_M


def test_carga_y_balance_acumulado(env):
    res = _load(env)
    assert res["status"] == "ok" and res["rows"] == 6
    b = balance.balance(env, 2025)
    assert b["periodo"].startswith("ene–mar 2025") and b["parcial"]
    assert b["comparado_con"] == "mismos 3 meses de 2024"
    cards = {c["etiqueta"]: c for c in b["cards"]}
    exp = sum(imig.to_dec(r["resultado_primario"]) for r in _rows() if r["indice_tiempo"].startswith("2025"))
    assert Decimal(cards["Resultado primario"]["valor_millones"]) == exp.quantize(Decimal("0.1"))
    ing = Decimal(cards["Ingresos totales"]["valor_millones"])
    gas = Decimal(cards["Gasto primario"]["valor_millones"])
    assert abs((ing - gas) - exp) <= Decimal("0.2")


def test_sin_ipc_no_hay_variacion_real(env):
    _load(env)
    for c in balance.balance(env, 2025)["cards"]:
        assert c["var_real_pct"] is None   # no se cargó IPC en este test


def test_cuenta_que_no_cierra_falla(env, tmp_path):
    rows = _rows()
    rows[0]["resultado_primario"] = str(Decimal(rows[0]["resultado_primario"]) + 1000)
    res = _load(env, _write(tmp_path, rows))
    assert res["status"] == "failed" and "no cierra" in res["error"]


def test_columna_nueva_sin_clasificar_falla(env, tmp_path):
    rows = _rows()
    for r in rows:
        r["impuesto_nuevo"] = "1.0"
    res = _load(env, _write(tmp_path, rows))
    assert res["status"] == "failed" and "sin clasificar" in res["error"]


def test_celda_vacia_falla(env, tmp_path):
    rows = _rows()
    rows[1]["ganancias"] = ""
    res = _load(env, _write(tmp_path, rows))
    assert res["status"] == "failed" and "celda vacía" in res["error"]


def test_sin_datos(env):
    assert balance.balance(env, 2025)["estado"] == "sin_datos"
    assert puente.puente(env, 2025)["estado"] == "no_disponible"
