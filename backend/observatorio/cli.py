"""CLI: python -m observatorio.cli {init,sync,reconcile,status}"""
import argparse
import json

from . import db, metrics, sync


def main(argv=None):
    p = argparse.ArgumentParser(prog="observatorio")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    s = sub.add_parser("sync", help="descargar y cargar fuentes (bajo demanda)")
    s.add_argument("--ejercicios", type=int, nargs="+", default=list(sync.DEFAULT_EJERCICIOS))
    s.add_argument("--force", action="store_true", help="recargar aunque el SHA-256 no cambie")
    r = sub.add_parser("reconcile")
    r.add_argument("ejercicio", type=int)
    sub.add_parser("status")
    a = p.parse_args(argv)
    con = db.connect()
    db.init_db(con)
    if a.cmd == "sync":
        for res in sync.sync_all(con, a.ejercicios, force=a.force):
            print(json.dumps(res, ensure_ascii=False))
    elif a.cmd == "reconcile":
        for res in sync.reconcile(con, a.ejercicio):
            print(json.dumps(res, ensure_ascii=False))
    elif a.cmd == "status":
        for c in metrics.coverage(con):
            print(f"{c['dataset_id']:32} {c['estado']:9} obs={c['observaciones']:>8} "
                  f"pub={c['fecha_publicacion_fuente']} desc={c['fecha_descarga']}"
                  + ("  [ÚLTIMO INTENTO FALLÓ]" if c["desactualizado"] else ""))


if __name__ == "__main__":
    main()
