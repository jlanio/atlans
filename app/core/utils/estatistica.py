"""Success rate and percentile: the two calculations the numbers screens repeat.

Each was written more than once, and the copies had already diverged. The
workflow detail's rate was `(total - falhas) / total` — a running or
canceled run counted as a success — while History and the per-workflow and
per-executor views used the spec's. The percentile with linear interpolation
existed in History and in cost per plan, identical except for the empty case.
This is the single version; what each screen does with missing data remains
its own decision.
"""
from __future__ import annotations

import math
from typing import Optional, Sequence


def taxa_de_sucesso(sucesso: int, falha: int) -> float:
    """Completed ÷ (completed + failed), to 4 decimal places; 0.0 with no denominator.

    Running and canceled runs stay OUT of the denominator (spec
    historico-metricas §3): a spike of in-progress runs must not drag the
    rate down, and canceling is not failing.
    """
    denominador = sucesso + falha
    return round(sucesso / denominador, 4) if denominador else 0.0


def percentil_linear(valores: Sequence[float], p: float) -> Optional[float]:
    """The `p` percentile (0–1) with linear interpolation between neighbors — the
    same semantics as PostgreSQL's `percentile_cont`, so the number computed in
    Python matches the SQL one. `None` with no values: "no data" is not zero.

    Interpolates instead of taking the nearest neighbor because, with few
    samples, the neighbor jumps in large steps from one day to the next.
    """
    if not valores:
        return None
    ordenados = sorted(valores)
    posicao = p * (len(ordenados) - 1)
    baixo = math.floor(posicao)
    alto = math.ceil(posicao)
    if baixo == alto:
        return float(ordenados[baixo])
    return float(ordenados[baixo] + (ordenados[alto] - ordenados[baixo]) * (posicao - baixo))
