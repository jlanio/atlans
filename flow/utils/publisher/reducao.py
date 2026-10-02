# flow/utils/publisher/reducao.py
"""
Redução de um node_event que passou do teto de bytes do protocolo WS.

Regra ÚNICA dos dois lados do fio: o executor a aplica antes de enviar
(`_dumps_event` em executor/connection.py) e o servidor a reaplica antes de
republicar no Redis (`_serialize_node_event` em
app/api/routers/executor_ws/resultados.py) — defesa contra executor com bug ou
comprometido, para quem a auto-limitação do executor não vale nada.

Eram duas cópias, e divergiram: o executor preservava `duration_ms` e as linhas
de stdout que coubessem, mas jogava fora o `extra` inteiro; o servidor cortava
só as chaves pesadas do `extra` e mantinha `output_columns`. Com o mesmo teto
dos dois lados, o executor entregava o evento já reduzido e a regra do servidor
nunca rodava: um `completed` com traceback grande chegava ao painel sem a
sugestão de coluna do editor.

Teto e listas de campos são parte do protocolo. Servidor e executores são
atualizados em momentos diferentes, e o evento que um lado reduz o outro tem de
aceitar como está.
"""
import json
from typing import Any, Callable

from flow.utils.publisher.events import KIND_STDOUT

# Teto de BYTES de um node_event (`json.dumps` escapa com ensure_ascii, então
# len(str) == bytes). Vale nos dois lados: no executor, um `print()` de um
# GeoJSON grande estourava o frame do WS e o servidor fechava com 1009,
# derrubando a sessão inteira; no servidor, o histórico do run tem teto de
# QUANTIDADE de eventos, não de bytes, e o Redis do compose não tem maxmemory —
# evento de MB crescia até o OOM-kill, levando junto dispatch, auth e o consumer
# de resultados.
#
# O produtor de stdout já fecha o lote em ~24 KB de texto (_STDOUT_FLUSH_BYTES
# em flow/nodes/action/python_script.py), então passar daqui é exceção.
TETO_NODE_EVENT_BYTES = 64 * 1024

# Campos que sobrevivem até o último degrau — sem eles o evento é inútil para o
# painel. `type` é o que roteia a mensagem no servidor (que o tira antes de
# republicar, então lá ele nem está no evento); `duration_ms` é o tempo do nó
# que o painel mostra.
CAMPOS_DE_CONTROLE = (
    "type", "run_id", "node", "status", "kind", "level", "timestamp", "duration_ms",
)

# Chaves de `extra` que carregam o peso do evento: stack de erro, resumo de
# inputs/outputs do debug mode, lote de linhas de stdout e o diff de schema
# drift (quem monta o `extra` é flow/executor/events.py e
# flow/utils/publisher/events.py). `output_columns` fica DE FORA de propósito: é
# o que o editor usa para sugerir nome de coluna.
CHAVES_PESADAS_DO_EXTRA = ("traceback", "debug_output", "lines", "schema_drift")

# Teto de caracteres de cada campo de controle preservado, para o próprio
# evento reduzido não poder ser grande (nada garante que `node` seja curto — ou
# sequer uma string).
TETO_POR_CAMPO = 512

# Teto de caracteres de `error` no primeiro degrau.
TETO_DO_ERRO = 8 * 1024

_MARCA_DE_CORTE = "…[truncado]"


def reduzir_node_event(
    evento: dict,
    payload: str,
    teto: int = TETO_NODE_EVENT_BYTES,
    *,
    default: Callable[[Any], Any] | None = None,
) -> str:
    """JSON do node_event reduzido a no máximo `teto` bytes.

    `payload` é o JSON do evento inteiro, que quem chama já serializou para
    medir; se ele cabe, volta como está. Senão o evento desce em degraus, cada
    um medido serializado (nunca estimado), e o primeiro que couber vence:

      1. Sem o peso: sai de `extra` o que está em CHAVES_PESADAS_DO_EXTRA e
         `error` é encurtado; o resto fica — `extra.output_columns`,
         `duration_ms`, a categoria do erro.
      2. Só os CAMPOS_DE_CONTROLE, coagidos a escalares curtos: um valor que
         não é string nem escalar vira repr cortado — senão o teto seria
         burlado justamente pelo caminho que o impõe.
      3. Rede de segurança, se nem os campos coagidos couberem: o indispensável
         para correlacionar o evento. O teto é garantia, não intenção.

    Num evento de stdout as linhas SÃO o conteúdo: nos degraus 1 e 2 volta o
    maior prefixo de `extra['lines']` que ainda cabe, com um marcador do que
    ficou de fora. Zerar `extra` mostrava a aba de saída do nó vazia, como se o
    script não tivesse impresso nada.

    O evento reduzido sai marcado com `__truncated__` e `__original_size__`.
    `default` é o do `json.dumps`: o executor passa o dele (Timestamp, numpy…);
    o servidor não precisa, o evento dele veio de JSON.
    """
    if len(payload) <= teto:
        return payload

    def _dumps(obj: dict) -> str:
        return json.dumps(obj, default=default)

    marcas = {"__truncated__": True, "__original_size__": len(payload)}
    extra = evento.get("extra")
    linhas = extra.get("lines") if isinstance(extra, dict) else None
    if evento.get("kind") != KIND_STDOUT or not isinstance(linhas, list):
        linhas = []

    # Degrau 1 — só quando há o que cortar: sem corte o candidato teria o
    # tamanho do original e o dumps seria desperdício.
    reduzido = dict(evento)
    houve_corte = False
    if isinstance(extra, dict) and any(k in extra for k in CHAVES_PESADAS_DO_EXTRA):
        reduzido["extra"] = {
            k: v for k, v in extra.items() if k not in CHAVES_PESADAS_DO_EXTRA
        }
        houve_corte = True
    erro = evento.get("error")
    if isinstance(erro, str) and len(erro) > TETO_DO_ERRO:
        reduzido["error"] = erro[:TETO_DO_ERRO] + _MARCA_DE_CORTE
        houve_corte = True
    if houve_corte:
        reduzido.update(marcas)
        candidato = _dumps(reduzido)
        if len(candidato) <= teto:
            return _com_as_linhas_que_cabem(reduzido, linhas, teto, _dumps) or candidato

    # Degrau 2.
    minimo: dict = {}
    for campo in CAMPOS_DE_CONTROLE:
        if campo not in evento:
            continue
        valor = evento[campo]
        if isinstance(valor, str):
            minimo[campo] = valor[:TETO_POR_CAMPO]
        elif valor is None or isinstance(valor, (bool, int, float)):
            minimo[campo] = valor
        else:
            minimo[campo] = repr(valor)[:TETO_POR_CAMPO]
    minimo.update(marcas)
    resultado = _com_as_linhas_que_cabem(minimo, linhas, teto, _dumps) or json.dumps(minimo)
    if len(resultado) <= teto:
        return resultado

    # Degrau 3.
    seguro = {"type": str(evento["type"])[:64]} if "type" in evento else {}
    seguro.update({
        "run_id": str(evento.get("run_id", ""))[:TETO_POR_CAMPO],
        "node": str(evento.get("node", ""))[:TETO_POR_CAMPO],
        "status": str(evento.get("status", ""))[:64],
        **marcas,
    })
    return json.dumps(seguro)


def _com_as_linhas_que_cabem(
    base: dict, linhas: list, teto: int, dumps: Callable[[dict], str],
) -> str | None:
    """`base` com o maior prefixo de `linhas` que cabe no teto.

    None quando não há linhas ou quando nem o marcador do corte cabe.

    Corta por BUSCA BINÁRIA sobre o resultado já serializado, e não por
    estimativa de caracteres: `json.dumps` escapa com ensure_ascii, então uma
    linha de acentos/emoji cresce até 6x e um orçamento contado em `len(str)`
    estouraria o teto exatamente no caso que este ramo existe para salvar. São
    ~log2(n) serializações de um payload de 64 KB — irrelevante num caminho que
    só roda quando o evento já é excepcional.
    """
    if not linhas:
        return None
    extra_base = base.get("extra") if isinstance(base.get("extra"), dict) else {}

    def _serializar(quantas: int) -> str:
        corte = [linha if isinstance(linha, str) else str(linha) for linha in linhas[:quantas]]
        perdidas = len(linhas) - quantas
        if perdidas > 0:
            corte.append(f"[{perdidas} linha(s) desta rajada nao couberam no evento]")
        return dumps({**base, "extra": {**extra_base, "lines": corte}})

    if len(_serializar(0)) > teto:
        return None
    baixo, alto = 0, len(linhas)
    while baixo < alto:
        meio = (baixo + alto + 1) // 2
        if len(_serializar(meio)) <= teto:
            baixo = meio
        else:
            alto = meio - 1
    return _serializar(baixo)
