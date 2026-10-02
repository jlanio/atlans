# app/core/constants.py
"""
Constantes globais do Atlas Studio.
Centraliza magic strings e valores fixos usados em múltiplos módulos.
"""
from flow.utils.fuso import fuso_padrao_do_agendamento

# ── node_stats ────────────────────────────────────────────────────────────────
# Chave reservada dentro do JSON node_stats para metadados globais da execução.
# Formato: WorkflowRun.node_stats["__run_meta__"] = {"retry_count": int, ...}
NODE_STATS_RUN_META_KEY = "__run_meta__"

# Nó interno publicado ao final de cada execução para sinalizar conclusão ao WebSocket.
WORKFLOW_COMPLETE_NODE = "__workflow_complete__"

# ── Redis TTLs (em segundos) ──────────────────────────────────────────────────
REDIS_TTL_1H  = 3_600       # 1 hora — cache de workflows, tokens
REDIS_TTL_24H = 86_400      # 24 horas — idempotência de execução, refresh tokens

# ── Security headers ──────────────────────────────────────────────────────────
HSTS_MAX_AGE = 31_536_000   # 1 ano — Strict-Transport-Security max-age


# ── Agendamento ───────────────────────────────────────────────────────────────
# O fuso que vale quando o agendamento nao diz qual e o seu.
#
# Havia TRES respostas para essa pergunta, e elas discordavam: o no
# `ScheduleTrigger` mandava um fuso fixo, o schema `ScheduleBase` usava outro
# (mesmo offset, nome diferente) e a coluna nula caia em
# **UTC** dentro do agendador — quatro horas de diferenca, em silencio, entre o
# que a tela mostrava e a hora em que o cron disparava.
#
# Agora e um valor so, e os tres pontos o importam. Ele vem do ambiente
# (AGENDAMENTO_FUSO_PADRAO, lido em `flow/utils/fuso.py`, que o no tambem usa),
# com UTC quando a instalacao nao o define.
#
# Trocar o valor de uma instalacao que ja tem agendamentos NAO e detalhe:
# `timezone` entra no `_mesma_configuracao` (`app/core/scheduling/hooks.py`),
# entao o proximo save de cada workflow agendado sem fuso explicito recria o
# schedule — o que zera o `next_run_at` e pula a ocorrencia do dia. Por isso o
# valor se define antes de criar agendamentos, e um deploy pode conferir que
# ele esta no .env antes de subir.
FUSO_PADRAO_DO_AGENDAMENTO = fuso_padrao_do_agendamento()

# Teto de eventos guardados no histórico de um run (`workflow:{run}:history`).
# O rpush era ilimitado: um executor comprometido (ou com bug) podia empurrar
# mensagens de até 16 MB em loop e estourar a memória do Redis — que também
# guarda presença, blacklist de tokens e contadores de rate limit. O frontend só
# reconstrói o canvas com os eventos recentes, então truncar o início é seguro.
MAX_EVENTOS_NO_HISTORICO = 5000
