# app/mcp/guardas.py
"""
A tabela tool → guarda: fonte única de quem pode chamar o quê.

Cada tool tem exatamente uma linha aqui, e essa linha é lida por três
consumidores: `list_tools` (esconde do catálogo o que o token não alcança),
`call_tool` (recusa a chamada com `forbidden_scope` e aplica a cota) e a
documentação. Mantê-los lendo a MESMA estrutura é o que impede o caso clássico
— a tool some da lista mas continua chamável, ou o doc promete um escopo e o
código exige outro.

Campos:
- `escopo`: o escopo do PAT exigido (None = nenhum; não existe tool sem escopo
  hoje, mas o campo é opcional para o caso de uma tool puramente informativa);
- `papel`: papel MÍNIMO no workspace. A guarda não o aplica — quem conhece o
  workspace da chamada é a tool, que chama `exigir_papel`. O campo fica aqui
  para a documentação e para os testes de paridade.
  Uma exceção, e ela é deliberada: `cancel_run` não chama `exigir_papel`,
  porque a conferência mora dentro de `workflow_execution_service.cancel_run`,
  junto do SELECT que carrega a execução. Foi para lá que ela foi movida de
  propósito — antes vivia só na rota REST, e qualquer outro chamador (uma tool
  daqui, um script, um job) cancelava execução de qualquer conta. Repetí-la na
  tool custaria uma consulta a mais e reabriria a chance de as duas cópias
  divergirem. Quem garante que ela continua lá é
  `test_cancelar_com_papel_de_viewer_e_recusado_pelo_servico_de_verdade`, o
  único teste de cancelamento que não dubla o serviço;
- `cota`: balde extra de rate limit ("validate", "run"); None = só o geral;
- `read_only` / `idempotente`: viram `readOnlyHint`/`idempotentHint` nas
  anotações da tool. `destructive_hint` é sempre False: o MCP do Atlans não
  apaga nada;
- `open_world`: vira `openWorldHint`. False para tudo, menos as duas tools do
  catálogo de fontes que SONDAM um WFS (`probe_source`, `register_source`) —
  elas falam com a internet aberta, pelo servidor, com guarda de SSRF, teto de
  bytes e o balde `probe`. Mentir `False` ali desinformaria o cliente que
  decide pelo hint.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Guarda:
    escopo: str | None
    papel: str | None
    cota: str | None
    read_only: bool
    idempotente: bool
    # Default no fim: as linhas existentes seguem intactas.
    open_world: bool = False


# As 42 tools, em oito blocos: leitura do catálogo (11), construção (5),
# execução (7, das quais três escrevem — `run_workflow`, `cancel_run` e
# `retry_run`), acervo (5, das quais duas escrevem — `restore_workflow_version`
# e `duplicate_workflow`), pins (3, das quais duas escrevem), gatilhos (4, das
# quais três escrevem), escrita no Drive (3, todas de escrita) e fontes (4, das
# quais uma escreve — `register_source`). Acrescentar
# aqui sem registrar a tool (ou o contrário) quebra o teste de paridade, que é
# justamente o ponto.
#
# A leitura de execuções (`get_run`, `list_runs`, `get_run_artifacts`) pede
# `workflows:read` + membro, e não `runs:execute`: é a mesma exigência da REST,
# onde `/observability` só pede ser membro do workspace do run.
# Cobrar `runs:execute` para LER obrigaria a dar permissão de disparar a quem só
# acompanha — e um escopo mais largo do que o necessário é o oposto do que a
# tabela existe para garantir.
GUARDAS: dict[str, Guarda] = {
    "list_workspaces":        Guarda("workflows:read",  None,       None,       True,  True),
    "list_workflows":         Guarda("workflows:read",  "viewer",   None,       True,  True),
    "get_workflow":           Guarda("workflows:read",  "viewer",   None,       True,  True),
    "get_workflow_contract":  Guarda("workflows:read",  "viewer",   None,       True,  True),
    "search_nodes":           Guarda("workflows:read",  None,       None,       True,  True),
    "describe_node":          Guarda("workflows:read",  None,       None,       True,  True),
    "list_credentials":       Guarda("workflows:read",  "viewer",   None,       True,  True),
    "list_drive_files":       Guarda("drive:read",      "viewer",   None,       True,  True),
    # Não idempotente: cada chamada assina uma URL nova, com validade própria.
    "get_drive_download_url": Guarda("drive:read",      "viewer",   None,       True,  False),
    "get_portal_info":        Guarda("workflows:read",  "viewer",   None,       True,  True),
    "get_authoring_guide":    Guarda("workflows:read",  None,       None,       True,  True),
    # Construção. `validate_workflow` não grava nada, mas simula o fluxo (lê
    # credenciais, monta o payload do executor) — por isso não é read_only e
    # paga o balde `validate`, que é o que impede varrer a plataforma a golpe
    # de validação. Criar e atualizar não são idempotentes: repetir a chamada
    # cria outro workflow ou outra versão.
    "validate_workflow":      Guarda("workflows:write", "editor",   "validate", False, True),
    "create_workflow":        Guarda("workflows:write", "editor",   "validate", False, False),
    "update_workflow":        Guarda("workflows:write", "editor",   "validate", False, False),
    "set_workflow_active":    Guarda("workflows:write", "editor",   None,       False, True),
    "set_portal_access":      Guarda("workflows:write", "editor",   None,       False, True),
    # Execução. O balde `run` soma-se ao geral, e a espera (`wait`) ainda passa
    # pelo teto de esperas simultâneas — despachar é a chamada mais cara que o
    # servidor oferece.
    "run_workflow":           Guarda("runs:execute",    "operator", "run",      False, False),
    "get_run":                Guarda("workflows:read",  "viewer",   None,       True,  True),
    "list_runs":              Guarda("workflows:read",  "viewer",   None,       True,  True),
    # Não idempotente: as URLs dos artefatos são assinadas na hora, com prazo.
    "get_run_artifacts":      Guarda("workflows:read",  "viewer",   None,       True,  False),
    # Fase 2 — execuções. Ler o log é leitura, como o resto da observabilidade.
    # Cancelar e reexecutar mexem no que está rodando: pedem `runs:execute` e
    # `operator`, o mesmo par que disparar.
    "get_run_events":         Guarda("workflows:read",  "viewer",   None,       True,  True),
    # Idempotente pelo EFEITO, não pela resposta: pedir a interrupção duas vezes
    # ao mesmo executor não interrompe duas vezes. A resposta pode variar — uma
    # execução já entregue é fechada pelo executor de volta, então as duas
    # chamadas costumam responder `requested`, e nenhuma delas é o fim. read_only
    # é False porque a chamada interrompe trabalho real.
    "cancel_run":             Guarda("runs:execute",    "operator", None,       False, True),
    # Não idempotente, e é o ponto: cada chamada DISPARA outra execução. Paga o
    # balde `run` pelo mesmo motivo que `run_workflow` — é despacho.
    "retry_run":              Guarda("runs:execute",    "operator", "run",      False, False),
    # Fase 2 — acervo. Ler o histórico e o que as execuções produziram é leitura,
    # como o resto; restaurar e duplicar escrevem, e pedem `editor`.
    "list_workflow_versions": Guarda("workflows:read",  "viewer",   None,       True,  True),
    "get_workflow_version":   Guarda("workflows:read",  "viewer",   None,       True,  True),
    # Não idempotente, e o motivo é o auto-snapshot: cada chamada grava uma
    # versão nova antes de trocar. Restaurar duas vezes seguidas leva ao mesmo
    # estado, mas deixa dois snapshots no histórico — o efeito no banco difere.
    "restore_workflow_version": Guarda("workflows:write", "editor", None,       False, False),
    # Não idempotente pelo mesmo motivo que `create_workflow`: cada chamada
    # produz um fluxo novo, com id novo.
    "duplicate_workflow":     Guarda("workflows:write", "editor",   None,       False, False),
    # Não idempotente: as URLs de download são assinadas na hora, com prazo —
    # mesma razão de `get_run_artifacts`.
    "list_artifacts":         Guarda("workflows:read",  "viewer",   None,       True,  False),

    # ── Pins ────────────────────────────────────────────────────────────────
    # As duas de escrita SÃO idempotentes, ao contrário das outras escritas do
    # servidor: fixar um nó já fixado reescreve a mesma entrada, e desfixar um
    # nó já desfixado não faz nada. Nenhuma das duas acumula estado a cada
    # chamada — é o que separa estas de `restore_workflow_version`, que deixa
    # um snapshot novo no histórico toda vez.
    #
    # `pin_node_output` reescreve `pinned_at`/`expires_at` a cada chamada, mas
    # isso é o VALOR do mesmo campo e não uma linha nova: repetir a chamada
    # continua levando ao mesmo estado, que é o que a dica promete a quem
    # decide se pode repetir com segurança.
    "list_pins":              Guarda("workflows:read",  "viewer",   None,       True,  True),
    "pin_node_output":        Guarda("workflows:write", "editor",   None,       False, True),
    "unpin_node_output":      Guarda("workflows:write", "editor",   None,       False, True),

    # ── Gatilhos ────────────────────────────────────────────────────────────
    # As três de escrita pedem `operator`, e não `editor`: AGENDAR É EXECUTAR.
    # Um schedule de um minuto dispara o fluxo com as credenciais do dono,
    # indefinidamente — é a mesma régua de `run_workflow`, e a mesma que a rota
    # REST aplica (`workflow_com_papel(ROLE_OPERATOR)` no `schedules_router`).
    #
    # `create_schedule` não é idempotente: cada chamada cria um `job_id` novo, e
    # repetir depois de um erro de rede deixaria DOIS agendamentos disparando o
    # mesmo fluxo. As outras duas endereçam um `job_id` que já existe, então
    # repetir leva ao mesmo estado.
    "list_schedules":         Guarda("workflows:read",  "viewer",   None,       True,  True),
    "create_schedule":        Guarda("triggers:manage", "operator", None,       False, False),
    "update_schedule":        Guarda("triggers:manage", "operator", None,       False, True),
    "delete_schedule":        Guarda("triggers:manage", "operator", None,       False, True),

    # ── Escrita no Drive ────────────────────────────────────────────────────
    # `editor`, e não `operator`: pôr e tirar arquivo é mexer no acervo do
    # workspace, não disparar execução. Mesma régua que a rota REST aplica
    # (`exigir_papel_no_workspace(..., ROLE_EDITOR)` no `drive_router`).
    #
    # `create_drive_upload_url` não é idempotente porque cada chamada cria uma
    # LINHA pendente nova e assina uma URL nova — repetir depois de um erro de
    # rede deixaria registros pendentes órfãos até a faxina passar. As outras
    # duas endereçam um `file_id` que já existe.
    "create_drive_upload_url": Guarda("drive:write",     "editor",   None,       False, False),
    "confirm_drive_upload":    Guarda("drive:write",     "editor",   None,       False, True),
    "delete_drive_file":       Guarda("drive:write",     "editor",   None,       False, True),

    # ── Fontes ──────────────────────────────────────────────────────────────
    # O catálogo de fontes pré-mapeadas: o que o assistente consulta ANTES de
    # prospectar. Buscar e descrever são leitura pura, sem rede. `probe_source`
    # não cria fonte, mas ATUALIZA o estado/esquema de uma já catalogada e fala
    # com a internet (uma das duas únicas open-world do servidor): por isso não
    # é read-only, pede `workflows:write` e paga o balde `probe` — a mesma
    # lógica de `validate_workflow`, que também não grava e também não é
    # read-only. `register_source` sonda E grava no acervo do workspace:
    # `editor`, a régua da escrita no Drive. As quatro são idempotentes — a
    # mesma URL+camada cai na mesma linha, e sondar duas vezes lê o mesmo.
    "search_sources":         Guarda("workflows:read",  "viewer",   None,       True,  True),
    "describe_source":        Guarda("workflows:read",  "viewer",   None,       True,  True),
    "probe_source":           Guarda("workflows:write", "editor",   "probe",    False, True, open_world=True),
    "register_source":        Guarda("workflows:write", "editor",   "probe",    False, True, open_world=True),
}
