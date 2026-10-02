"""Taxa de sucesso e percentil: as duas contas que as telas de números repetem.

Cada uma estava escrita mais de uma vez, e as cópias já tinham divergido. A
taxa do detalhe do workflow era `(total - falhas) / total` — execução em
andamento ou cancelada contava como sucesso — enquanto o Histórico e as visões
por workflow e por executor usavam a da spec. O percentil com interpolação
linear existia no Histórico e no custo por plano, iguais a menos do caso vazio.
Aqui fica a versão única; o que cada tela faz com a ausência de dado continua
sendo decisão dela.
"""
from __future__ import annotations

import math
from typing import Optional, Sequence


def taxa_de_sucesso(sucesso: int, falha: int) -> float:
    """Concluídas ÷ (concluídas + falhas), em 4 casas; 0.0 sem denominador.

    Em andamento e canceladas ficam FORA do denominador (spec
    historico-metricas §3): um pico de execuções em curso não pode derrubar a
    taxa, e cancelar não é falhar.
    """
    denominador = sucesso + falha
    return round(sucesso / denominador, 4) if denominador else 0.0


def percentil_linear(valores: Sequence[float], p: float) -> Optional[float]:
    """O percentil `p` (0–1) com interpolação linear entre vizinhos — a mesma
    semântica do `percentile_cont` do PostgreSQL, para que o número calculado em
    Python bata com o do SQL. `None` sem valores: "sem dado" não é zero.

    Interpola em vez de pegar o vizinho mais próximo porque, com poucas
    amostras, o vizinho pula degraus grandes de um dia para o outro.
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
