# flow/utils/backoff.py
"""
Politica unica de espera entre tentativas.

Antes deste modulo o backoff exponencial estava escrito a mao em dez trechos
espalhados por sete arquivos — o helper HTTP compartilhado, os nos de WFS e de
Requisicao HTTP, a espera do banco na subida da API, os dois lacos de reconexao
do Redis e os dois do GeoSync — cada um com sua propria decisao sobre
crescimento, teto e o que conta como transitorio.

So UM deles dispersava as tentativas: o laco de reconexao de
`executor/connection.py`, cujo comentario explica o motivo e o
`executor/config.py` documenta. Os outros nove retentavam em unissono. E isso
importa: quando o servidor volta de uma queda, a frota inteira de executores
bate nele no mesmo instante, contra um rate limit que e balde unico da
plataforma — a recuperacao vira uma segunda derrubada. O acerto ja existia na
casa e nao tinha como se propagar, porque nao havia onde morar.

O jitter aqui e PROPORCIONAL (50–100% do intervalo), e nao aditivo, por dois
motivos: e a forma ja validada no executor, e preserva o teto — um jitter somado
ao intervalo pode ultrapassar `teto`, um multiplicado nunca.

Por que nao `tenacity`: ela substituiria o LACO de tentativas, nao esta politica,
e so dois dos dez pontos tem laco separavel da logica de dominio — os outros
carregam classificacao de erro TLS, circuit breaker, agendamento persistido ou
reset por sessao saudavel. Alem disso, `flow/` roda no executor do Docker e no
do desktop com as dependencias do lock do executor
(`executor/requirements-full.txt`, com hash): adicionar a dependencia sem
regerar o lock quebraria os dois no import. Este modulo nao adiciona
dependencia nenhuma — depende so de `random`.
"""
import random

# Piso da faixa de jitter: a espera real fica entre 50% e 100% do intervalo
# calculado. Mesma faixa de `executor/connection.py`, que foi quem acertou
# primeiro.
FATOR_JITTER_MIN = 0.5

# Teto do expoente. `base ** tentativa` e aritmetica de PONTO FLUTUANTE, e
# estoura (`OverflowError`) por volta de 2**1024 — o `2 ** n` INTEIRO que este
# modulo substituiu tinha precisao arbitraria e nunca estourava. Contadores de
# tentativa sem limite superior existem de verdade na base: o
# `consecutive_errors` do ciclo do GeoSync so zera num ciclo bem-sucedido, e o
# `tentativas` do no de Requisicao HTTP vem do canvas.
#
# Cortar aqui nao muda valor nenhum devolvido: com `base > 1`, `inicial * 2**64`
# ja passa de 1e18, muitas ordens de grandeza acima de qualquer `teto` real, e o
# `min` satura de qualquer jeito.
_EXPOENTE_MAX = 64


def com_jitter(segundos: float) -> float:
    """Dispersa uma espera ja calculada.

    Para quando o intervalo NAO cresce exponencialmente — as escadas fixas de
    reconexao (`_RECONNECT_DELAYS`) sao tao sincronizadas quanto uma potencia de
    dois, e pelo mesmo motivo: todo mundo que caiu junto volta junto.
    """
    if segundos <= 0:
        return 0.0
    return segundos * (FATOR_JITTER_MIN + random.random() * (1.0 - FATOR_JITTER_MIN))


def espera_exponencial(
    tentativa: int,
    *,
    teto: float,
    inicial: float = 1.0,
    base: float = 2.0,
) -> float:
    """Espera apos a `tentativa`-esima falha (0 = a primeira), ja dispersa.

    O teto e aplicado ANTES do jitter, entao o retorno nunca o excede.
    """
    if tentativa < 0:
        tentativa = 0
    # `base <= 1` nao cresce, entao nao estoura — e cortar o expoente ali MUDARIA
    # o resultado, em vez de so evitar o estouro.
    if base > 1 and tentativa > _EXPOENTE_MAX:
        tentativa = _EXPOENTE_MAX
    return com_jitter(min(inicial * (base ** tentativa), teto))
