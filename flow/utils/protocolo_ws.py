# flow/utils/protocolo_ws.py
"""
Vocabulário do protocolo WebSocket executor ↔ servidor.

Os dois lados importam daqui: o executor (executor/connection.py) e o servidor
(app/api/routers/executor_ws_router.py e o pacote
app/api/routers/executor_ws/). `app` e `executor` nunca se importam; o que é dos
dois mora em `flow/`, que vai nas duas imagens. O teto e a redução de node_event
moram ao lado do evento, em flow/utils/publisher/reducao.py.

Mudar um valor daqui é mudar o fio. Servidor e executores são atualizados em
momentos diferentes (o executor roda na máquina do cliente), então todo valor
tem de continuar entendido pelo lado antigo: um tipo novo só é seguro depois que
o lado que o recebe já o conhece.
"""
from typing import Callable

# ── Versão ───────────────────────────────────────────────────────────────────
# A que o executor declara no handshake e as que o servidor aceita (fora delas:
# `error` unsupported_protocol_version e close 4426). Bump major só em breaking
# change — e o servidor passa a aceitar as duas antes de algum executor declarar
# a nova.
PROTOCOL_VERSION = "1.0"

SUPPORTED_PROTOCOL_VERSIONS = frozenset({PROTOCOL_VERSION})

# ── Tipos de mensagem ────────────────────────────────────────────────────────
# Executor → servidor: o que o loop de recebimento do servidor trata
# (executor_ws_router.py). Tipo fora daqui não tem efeito lá.
TIPOS_DO_EXECUTOR = frozenset({
    "handshake", "heartbeat", "capacity", "job_result", "node_event",
    "sync_event", "ack", "inventario",
})

# Resposta do servidor a uma mensagem que ele recusou, com `reason` (JSON
# inválido, campo obrigatório ausente, capacity inválida, mensagem antes do
# handshake, versão não suportada) e o detalhe do motivo. Só informa: a
# mensagem recusada já foi descartada, e o executor apenas registra.
TIPO_ERRO = "error"

# Servidor → executor. É a allowlist do executor: o resto é descartado antes de
# qualquer processamento. `control` e `cancel` exigem ainda assinatura Ed25519
# (_SIGNED_SERVER_MESSAGES em executor/connection.py).
TIPOS_DO_SERVIDOR = frozenset({"job", "drive_event", "control", "cancel", TIPO_ERRO})

# ── Chaves reservadas de `stats` do job_result ───────────────────────────────
# Controle: sobrevivem à truncagem, que só derruba os stats por nó. Sem
# `__response__` o BRPOP do webhook síncrono fica preso até o timeout; as demais
# alimentam artefatos, métricas e pins.
CHAVES_DE_CONTROLE_STATS = (
    "__response__",
    "__artifacts__",
    "__metrics__",
    "__updated_pinned_outputs__",
)

# Marcas da truncagem. `__control_dropped__` diz que nem as chaves de controle
# couberam: o servidor transforma isso em erro explícito para o webhook
# síncrono, em vez de deixar o BRPOP esperar o timeout.
STATS_TRUNCADO = "__truncated__"
STATS_TAMANHO_ORIGINAL = "__original_size__"
STATS_CONTROLE_DESCARTADO = "__control_dropped__"


def reduzir_stats(
    stats: dict,
    tamanho_original: int,
    teto: int,
    serializar: Callable[[dict], str],
) -> tuple[dict, str, bool]:
    """Trunca o `stats` de um job_result que passou do `teto`, em dois degraus.

    1. Derruba os stats por nó e preserva as CHAVES_DE_CONTROLE_STATS;
    2. se nem elas couberem, derruba tudo e marca STATS_CONTROLE_DESCARTADO.

    Os dois lados aplicam, cada um com o seu teto e a sua régua: o executor
    mede a mensagem inteira contra o frame do WS (`_dumps_result`); o servidor
    mede só `stats`, contra o teto do que ele guarda (`_cap_job_result`). Por
    isso `serializar` é de quem chama: recebe os stats reduzidos e devolve o
    JSON que é medido contra `teto`.

    `tamanho_original` vai para STATS_TAMANHO_ORIGINAL nos dois degraus — é o
    tamanho de antes de qualquer corte.

    Devolve `(stats_reduzidos, json_medido, controle_preservado)`.
    """
    mantidas = (
        {k: stats[k] for k in CHAVES_DE_CONTROLE_STATS if k in stats}
        if isinstance(stats, dict) else {}
    )
    reduzidos = {**mantidas, STATS_TRUNCADO: True, STATS_TAMANHO_ORIGINAL: tamanho_original}
    try:
        serializado = serializar(reduzidos)
    except (TypeError, ValueError):
        # Chave de controle não serializável (ou recursiva): conta como grande.
        serializado = None
    if serializado is not None and len(serializado) <= teto:
        return reduzidos, serializado, True

    reduzidos = {
        STATS_TRUNCADO: True,
        STATS_TAMANHO_ORIGINAL: tamanho_original,
        STATS_CONTROLE_DESCARTADO: True,
    }
    return reduzidos, serializar(reduzidos), False


# ── `system_info` do handshake ───────────────────────────────────────────────
# O executor coleta (`_collect_system_info` em executor/sysinfo.py) e o servidor
# persiste só estes campos, cada um coagido ao tipo do seu grupo
# (`_sanitize_system_info` em app/api/routers/executor_ws/protocolo.py). Campo
# novo no executor que não entrar aqui é descartado pelo servidor — com um
# WARNING a cada conexão.
SYSTEM_INFO_TEXTOS = ("hostname", "os_name", "os_version")

SYSTEM_INFO_NUMEROS = ("cpu_cores", "ram_total_gb", "disk_total_gb")

SYSTEM_INFO_BOOLEANOS = ("container",)
