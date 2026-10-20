"""Contra la base real ya sincronizada. Ejecutar con: ODP_INTEGRATION=1 pytest"""
import os

import pytest

pytestmark = pytest.mark.skipif(not os.environ.get("ODP_INTEGRATION"), reason="requiere ODP_INTEGRATION=1 y base sincronizada")


def test_2026_coincide_con_totales_publicados():
    from observatorio import db, sync
    con = db.connect()
    recs = sync.reconcile(con, 2026)
    bad = [r for r in recs if r["conclusion"] != "coincide"]
    assert not bad, bad


def test_2025_cierre_pa_coincide_con_cuenta_de_inversion():
    from observatorio import db, sync
    con = db.connect()
    recs = sync.reconcile_cuenta_inversion(con, 2025)
    assert recs and all(r["conclusion"] == "coincide" for r in recs), recs


def test_2025_puente_real_cierra_con_controles():
    from observatorio import db, puente
    con = db.connect()
    p = puente.puente(con, 2025)
    assert p["estado"] == "ok"
    bad = [c for c in p["controles"] if c["estado"] != "coincide"]
    assert not bad, bad


def test_citas_metodologicas_reales_verificadas():
    from observatorio import db, metodologia
    con = db.connect()
    for r in metodologia.refresh(con):
        assert r["estado_verificacion"] in ("verificada_en_crudo", "hallazgo_reproducible"), r
