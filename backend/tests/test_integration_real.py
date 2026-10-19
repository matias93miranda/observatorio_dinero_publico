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
