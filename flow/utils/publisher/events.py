from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Sequence

from flow.utils.logger import get_logger

logger = get_logger(__name__)

# ── Vocabulário do evento ────────────────────────────────────────────────────
#
# `status` descreve o CICLO DE VIDA do nó e só isso. Severidade e origem da
# mensagem viajam em campos próprios (`level` e `kind`) — antes tudo era
# empilhado em `status` ("started"/"completed"/"failed" convivendo com "debug" e
# "log"), o que forçava o painel de execução a filtrar por negação ("tudo que
# não é erro nem print") e tornava impossível distinguir stdout de ciclo de vida.

KIND_LIFECYCLE = "lifecycle"   # started / completed / failed de um nó
KIND_STDOUT    = "stdout"      # linha de print() capturada de dentro do nó
KIND_DEBUG     = "debug"       # resumo de inputs/outputs (debug mode)

LEVEL_INFO  = "info"
LEVEL_WARN  = "warn"
LEVEL_ERROR = "error"


class WorkflowEventPublisher(ABC):
    """
    Interface abstrata para publicação de eventos de workflow.
    Cada evento deve ter a mesma estrutura JSON:
      {
        "run_id": str,
        "node": str,                  # id do nó ou "__workflow_complete__"
        "kind": str,                  # "lifecycle" | "stdout" | "debug"
        "level": str,                 # "info" | "warn" | "error"
        "status": str,                # "started" | "completed" | "failed"
        "timestamp": float,           # epoch seconds UTC
        "duration_ms": Optional[float], # somente em completed/failed
        "error": Optional[str],       # só em failed
        "extra": Optional[dict]       # quaisquer outros metadados (branch, overhead…)
      }
    """
    @abstractmethod
    def publish_event(
        self,
        run_id: str,
        node: str,
        status: str,
        timestamp: Optional[float] = None,
        duration_ms: Optional[float] = None,
        error: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
        kind: str = KIND_LIFECYCLE,
        level: str = LEVEL_INFO,
    ) -> None:
        """
        :param run_id:      identificador da execução
        :param node:        identificador do nó (ou '__workflow_complete__')
        :param status:      "started", "completed" ou "failed"
        :param timestamp:   momento do evento (em segundos desde epoch UTC). Se None, será preenchido automaticamente.
        :param duration_ms: duração do nó em ms (para completed/failed)
        :param error:       string com stack/message se falhou
        :param extra:       outros dados (p.ex.: branch, overhead_ms…)
        :param kind:        origem da linha — lifecycle / stdout / debug
        :param level:       severidade — info / warn / error
        """
        ...


def publish_stdout(publisher, run_id: str, node_id: str, lines: Sequence[str]) -> None:
    """Publica um LOTE de linhas de print() capturadas de dentro de um nó.

    kind=stdout é o que separa isto do ciclo de vida: no painel de execução a
    saída do usuário vive numa aba própria, agrupada por nó, sem ícone/status/
    duração por linha (um print não tem nenhuma das três coisas).

    O lote é o ponto: um evento POR LINHA fazia `for i in range(50000): print(i)`
    estourar a fila de 500 slots — que é compartilhada por todos os jobs e pelo
    GeoSync — e o rate limit do servidor, derrubando telemetria de OUTROS
    workflows junto. Quem agrega é o emissor (`_LoggingStream` do PythonScript),
    que fecha o lote a cada ~200 ms ou a cada N linhas.

    `extra['lines']` é a ÚNICA fonte de verdade (uma entrada por linha impressa).
    Não existe mais `extra['message']`: publicar o mesmo texto duas vezes dobrava
    o payload e um lote de 200 linhas de ~160 caracteres passava dos 64 KB de
    `TETO_NODE_EVENT_BYTES` (flow/utils/publisher/reducao.py); o sender então
    reduzia o evento aos campos de controle — que não incluíam `extra` — e o
    painel perdia as 200 linhas de uma vez, em silêncio. Hoje a redução guarda o
    prefixo de `lines` que cabe, mas o lote ainda tem de caber inteiro. Quem
    consome lê `lines` e junta por \\n se precisar de texto.

    Mora aqui, e não em flow/executor/events.py, porque quem chama é um nó —
    importar o pacote `flow.executor` de dentro de `flow.nodes` fecharia o ciclo
    executor → registry → nodes → executor.
    """
    if not (publisher and run_id and lines):
        return
    linhas = list(lines)
    try:
        publisher.publish_event(
            run_id=run_id,
            node=node_id,
            status="log",
            extra={"lines": linhas},
            kind=KIND_STDOUT,
            level=LEVEL_INFO,
        )
    except Exception as exc:
        # Publicar saída nunca pode derrubar a execução do script do usuário —
        # mas engolir sem rastro esconderia um publisher quebrado.
        logger.debug("Falha ao publicar stdout do nó %s: %s", node_id, exc)
