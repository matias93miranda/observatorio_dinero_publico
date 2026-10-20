"""Exporta las respuestas de la API a archivos JSON para publicar la plataforma como sitio estático.

Se llama a los mismos endpoints que usa la interfaz (con TestClient): el sitio publicado muestra exactamente
lo que devuelve la API local, sin recalcular nada. El nombre de cada archivo sale de la ruta y los parámetros
con la misma regla que `clave()` en frontend/src/api.ts. Las rutas absolutas de la máquina que exporta se
reemplazan por rutas relativas al directorio de datos.

Uso: python -m observatorio.export_static ../frontend/public/data
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from . import config
from .api import app

GASTO_CLS = ("finalidad", "funcion", "jurisdiccion", "inciso", "programa")
ETAPAS = ("devengado", "pagado", "comprometido", "vigente", "presupuestado")


def clave(path: str, params: dict) -> str:
    base = path.removeprefix("/api/").replace("/", "_")
    partes = [f"{k}={params[k]}" for k in sorted(params)]
    return re.sub(r"[^A-Za-z0-9_.=-]", "-", "__".join([base, *partes]))


def pedidos(ejercicios: list[int]) -> list[tuple[str, dict]]:
    out: list[tuple[str, dict]] = [("/api/ejercicios", {}), ("/api/meta", {}), ("/api/metodologia", {}),
                                   ("/api/bridge/historico", {}), ("/api/timeseries", {"metric": "totales_anuales"}),
                                   ("/api/coverage", {})]
    for ej in ejercicios:
        out += [(p, {"ejercicio": ej}) for p in ("/api/balance", "/api/bridge", "/api/cuenta-inversion", "/api/summary")]
        out += [("/api/reconciliation", {"prefix": f"{pre}:{ej}:"}) for pre in ("ci35", "cruce")]
        out += [("/api/expenditures", {"ejercicio": ej, "classification": c, "etapa": e, "limit": 30})
                for c in GASTO_CLS for e in ETAPAS]
        out += [("/api/revenues", {"ejercicio": ej, "classification": c, "etapa": "percibido", "limit": 30})
                for c in ("tipo", "clase")]
    return out


def export(out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    c = TestClient(app)
    ejercicios = c.get("/api/ejercicios").json()
    locales = sorted({str(config.DATA_DIR.resolve()) + "/", str(config.DATA_DIR) + "/"}, key=len, reverse=True)
    n = 0
    for path, params in pedidos(ejercicios):
        r = c.get(path, params=params)
        if r.status_code != 200:
            raise SystemExit(f"{path} {params}: HTTP {r.status_code} {r.text[:200]}")
        txt = json.dumps(r.json(), ensure_ascii=False, separators=(",", ":"))
        for loc in locales:
            txt = txt.replace(loc, "")
        (out_dir / f"{clave(path, params)}.json").write_text(txt, encoding="utf-8")
        n += 1
    return n


if __name__ == "__main__":
    dest = Path(sys.argv[1] if len(sys.argv) > 1 else "../frontend/public/data")
    print(f"{export(dest)} archivos en {dest}")
