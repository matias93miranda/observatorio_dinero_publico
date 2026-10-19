"""Balance fiscal oficial (IMIG, SPNF, base caja) y puente con Presupuesto Abierto."""
from __future__ import annotations

import sqlite3
from decimal import Decimal

from .ingest import imig
from .metrics import pct_change, provenance
from .money import centavos_to_millones

IPC_ID = "148.3_INIVELNAL_DICI_M_26"
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
Q = Decimal("0.1")  # se muestra con la precisión típica de publicación del IMIG


def _q(d: Decimal | None) -> str | None:
    return None if d is None else str(d.quantize(Q))


def _q_pct(d: Decimal | None) -> str | None:
    return None if d is None else str(d.quantize(Decimal("0.01")))


def _month_values(con, col: str, periods: list[str]) -> dict[str, Decimal]:
    if not periods:
        return {}
    marks = ",".join("?" * len(periods))
    return {p: imig.to_dec(v) for p, v in con.execute(
        f"SELECT periodo, valor_original FROM series_observation WHERE series_id=? AND periodo IN ({marks})",
        (f"imig.{col}", *periods)) if v is not None}


def _ipc(con) -> dict[str, Decimal]:
    return {p: Decimal(v) for p, v in con.execute(
        "SELECT periodo, valor_original FROM series_observation WHERE series_id=? AND valor_original IS NOT NULL",
        (IPC_ID,))}


def months_available(con, ejercicio: int) -> list[str]:
    return [r[0] for r in con.execute(
        "SELECT periodo FROM series_observation WHERE series_id='imig.resultado_primario' "
        "AND periodo LIKE ? AND valor_original IS NOT NULL ORDER BY periodo", (f"{ejercicio}-%",))]


def _sum_cols(con, cols, periods, ipc=None, base=None):
    """Suma nominal y, si hay IPC para todos los meses, suma real (cada mes deflactado por su IPC)."""
    nominal, real, complete = Decimal(0), Decimal(0), True
    for c in cols:
        vals = _month_values(con, c, periods)
        if len(vals) != len(periods):
            return None, None
        nominal += sum(vals.values())
        if ipc is not None:
            for p, v in vals.items():
                if p in ipc:
                    real += v * ipc[base] / ipc[p]
                else:
                    complete = False
    return nominal, (real if ipc is not None and complete else None)


def balance(con: sqlite3.Connection, ejercicio: int) -> dict:
    meses = months_available(con, ejercicio)
    prov = [provenance(con, "imig_mensual"), provenance(con, "st_ipc_nacional")]
    if not meses:
        return {"estado": "sin_datos", "ejercicio": ejercicio, "procedencia": prov}
    n = len(meses)
    previos = [f"{ejercicio - 1}{m[4:]}" for m in meses]
    if len(months_available(con, ejercicio - 1)) < 1 or not all(
            p in months_available(con, ejercicio - 1) for p in previos):
        previos = []
    ipc = _ipc(con)
    base = max(ipc) if ipc else None
    periodo = (f"{ejercicio} (año completo)" if n == 12
               else f"{MESES[0]}–{MESES[int(meses[-1][5:]) - 1]} {ejercicio} (acumulado {n} meses)")

    def linea(etiqueta, cols, signo_bueno=1, nota=None):
        cur_n, cur_r = _sum_cols(con, cols, meses, ipc, base)
        prev_n, prev_r = _sum_cols(con, cols, previos, ipc, base) if previos else (None, None)
        var_real = None
        if cur_r is not None and prev_r is not None and prev_r > 0 and cur_r > 0:
            var_real = pct_change(cur_r, prev_r)
        return {"etiqueta": etiqueta, "valor_millones": _q(cur_n), "estado": "ok" if cur_n is not None else "sin_datos",
                "anterior_millones": _q(prev_n),
                "var_nominal_pct": _q_pct(pct_change(cur_n, prev_n)) if prev_n and prev_n > 0 and cur_n and cur_n > 0 else None,
                "var_real_pct": _q_pct(var_real),
                "real_millones": _q(cur_r), "anterior_real_millones": _q(prev_r), "nota": nota}

    ing, gas = list(imig.INGRESOS), list(imig.GASTOS_PRIMARIOS)
    cards = [
        linea("Ingresos totales", ing),
        linea("Gasto primario", gas),
        linea("Resultado primario", ["resultado_primario"],
              nota="Ingresos totales − gasto primario. Las variaciones % no se calculan si algún valor es ≤ 0."),
        linea("Intereses netos", ["intereses_netos"]),
        linea("Resultado financiero", ["resultado_financiero"], nota="Resultado primario − intereses netos."),
    ]
    grupos = []
    for flujo, mapping in (("ingreso", imig.INGRESOS), ("gasto primario", imig.GASTOS_PRIMARIOS)):
        for g in dict.fromkeys(v[0] for v in mapping.values()):
            cols = [c for c, (gg, _) in mapping.items() if gg == g]
            item = linea(imig.GRUPOS[g], cols)
            item["flujo"] = flujo
            item["detalle"] = [linea(mapping[c][1], [c]) | {"columna": c} for c in cols]
            grupos.append(item)
    return {
        "estado": "ok", "ejercicio": ejercicio, "periodo": periodo, "meses": meses,
        "comparado_con": f"mismos {n} meses de {ejercicio - 1}" if previos else None,
        "universo": "Sector Público Nacional no Financiero", "base": "caja",
        "unidad": imig.UNIDAD,
        "unidad_real": f"millones de pesos de {base} (cada mes deflactado por IPC INDEC)" if base else None,
        "parcial": n < 12, "cards": cards, "grupos": grupos, "procedencia": prov,
    }


def bridge(con: sqlite3.Connection, ejercicio: int) -> dict:
    """Puente entre el balance oficial (IMIG) y la ejecución de la AN (Presupuesto Abierto).
    Solo se arma para ejercicios cerrados con 12 meses de IMIG: con cortes distintos no son comparables."""
    meses = months_available(con, ejercicio)
    dg, dr = f"pa_credito_anual_{ejercicio}", f"pa_recursos_anual_{ejercicio}"
    prov = [provenance(con, "imig_mensual"), provenance(con, dg), provenance(con, dr)]
    has_pa = con.execute("SELECT 1 FROM fiscal_observation WHERE dataset_id=? LIMIT 1", (dg,)).fetchone()
    if len(meses) < 12 or not has_pa:
        return {"estado": "no_comparable", "ejercicio": ejercicio, "procedencia": prov,
                "motivo": "El puente solo se arma con 12 meses de IMIG y el cierre de Presupuesto Abierto del "
                          "mismo ejercicio. Con cortes distintos la diferencia mezclaría períodos."}

    def pa_sum(ds, etapa, extra="", args=()):
        c = con.execute(f"SELECT SUM(importe_centavos) FROM fiscal_observation WHERE dataset_id=? AND etapa=? {extra}",
                        (ds, etapa, *args)).fetchone()[0]
        return centavos_to_millones(c)

    an_ing = pa_sum(dr, "percibido")
    an_gp = pa_sum(dg, "devengado") - pa_sum(dg, "devengado", "AND economico LIKE '2131%'")
    an_rentas = pa_sum(dr, "percibido", "AND recurso_tipo='16'")
    s_ing, _ = _sum_cols(con, list(imig.INGRESOS), meses)
    s_gp, _ = _sum_cols(con, list(imig.GASTOS_PRIMARIOS), meses)
    s_rentas, _ = _sum_cols(con, [c for c, (g, _) in imig.INGRESOS.items() if g == "rentas"], meses)
    filas = [
        ("Ingresos totales", an_ing, s_ing),
        ("  de los cuales: rentas de la propiedad", an_rentas, s_rentas),
        ("Gasto primario", an_gp, s_gp),
        ("Resultado primario", an_ing - an_gp, s_ing - s_gp),
    ]
    return {
        "estado": "ok", "ejercicio": ejercicio, "unidad": imig.UNIDAD,
        "filas": [{"concepto": c, "an_presupuesto_abierto": _q(a), "spnf_imig": _q(s), "diferencia": _q(a - s)}
                  for c, a, s in filas],
        "causas_conocidas": [
            "Universo: el IMIG agrega al SPNF (AN + fondos fiduciarios, empresas y otros entes); Presupuesto Abierto cubre solo la AN.",
            "Base: el IMIG es caja; Presupuesto Abierto registra gastos devengados y recursos percibidos.",
            "Rentas de la propiedad: el IMIG solo computa rentas del FGS cobradas al sector privado y público financiero y "
            "un 'resto'. Presupuesto Abierto registra todas las rentas percibidas por la AN, sin distinguir si el pagador es otro ente público.",
            "Transferencias intra-SPNF (p.ej. AN → fondos fiduciarios) se consolidan en el IMIG y no en la AN.",
        ],
        "advertencia": "La diferencia no está descompuesta partida por partida: las causas listadas son cualitativas. "
                       "Cuantificar cada una requiere fuentes adicionales (pendiente).",
        "procedencia": prov,
    }
