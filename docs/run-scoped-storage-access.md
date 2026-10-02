# Escopo de storage por run (follow-up de segurança)

**Status:** aberto — plano acordado, não implementado.

## Problema

Os endpoints de storage do executor autorizam pelo **workspace do executor**, não
pelo **workspace do run**. Como `get_agent_workspace_ids` devolve *todos* os
workspaces quando `is_default=True` (`app/services/user_executor_service.py`) e
todo workflow sem `target_agent_id` é roteado ao executor default, a checagem é
sempre verdadeira nesse caminho. Na prática o `id_hash` do arquivo (ou a `s3_key`)
funciona como credencial portátil: quem o conhece, lê — de qualquer workspace.

Não há validação da origem do id: `driveFileId` vai cru da definição JSON do
workflow para o nó. O único ponto em `app/` que sequer inspeciona o campo é o
relatório de move (`app/services/workflow_move_report.py`, que define
`_DRIVE_ID_PROP = "driveFileId"` e emite `drive_refs_out_of_scope`) — em nenhum
momento da leitura de arquivo o id é validado contra o workspace do run.

### Cenário sem adivinhação de id

1. Uma pessoa é membro dos workspaces **X** e **Y** e vê legitimamente, na UI de
   Y, os ids dos arquivos do Drive.
2. Ela cria um workflow **em X** com `driveFileId` de um arquivo de **Y**, ligado
   a um `DataOutput`.
3. O run de X pede o arquivo; o servidor entrega (executor default → todos os
   workspaces); o dado de Y vira artefato **de X**, visível para membros de X que
   nunca tiveram acesso a Y.

Variante: a pessoa é **removida de Y** e os ids que anotou continuam funcionando
a partir de qualquer workflow em X — a revogação de acesso não revoga nada.

### Interação com o move de workflow

`POST /workflows/{id}/move` torna esse caminho mais fácil de exercitar **sem má
intenção**: um workflow legítimo, com `driveFileId` de arquivos do workspace A,
passa a rodar no workspace B e continua lendo os arquivos de A — porque o
executor default enxerga todos os workspaces. O move avisa disso
(`drive_refs_out_of_scope`), mas o aviso é informativo: quem ignorar segue com um
fluxo que lê dados fora do próprio tenant.

Isso não muda a correção proposta abaixo, só aumenta a chance de o cenário
aparecer em uso normal. Quando o enforcement por run entrar, esses fluxos passam
a falhar de forma visível — que é o comportamento desejado.

### Nota histórica

A regra correta existia no código: `wf.workspace_id != workspace_id →
PermissionError`, dentro de `_resolve_server` no `drive_resolver`. Estava em dois
lugares errados — num branch inalcançável (o motor nunca roda no servidor) e do
lado do cliente, onde o próprio executor conferia a si mesmo. O branch foi
removido na limpeza do modo in-server; a intenção precisa voltar, agora no
servidor e derivada de dados que o cliente não escolhe.

## Endpoints afetados

Todos em `app/api/routers/drive_router.py`:

| Endpoint | Autorização atual | Usado por |
|---|---|---|
| `GET /drive/executor-download/{id_hash}` | `wf.workspace_id in executor._resolved_ws_ids` | leitores de Drive, DataInput |
| `GET /drive/executor-download-artifact/{id_hash}` | `artifact.workspace_id in ...` | DataInput (contexto Artefatos) |
| `POST /drive/executor-presign-download` | `svc.presign_download` — checagem própria (segmento de workspace p/ `pin-cache/`+`artifacts/`, lookup em `WorkspaceFile` p/ `drive/`) | pin cache, send_email (modo link) |
| `POST /drive/executor-presign-upload` | `_validate_agent_s3_key` (segmento de workspace na s3_key) | pin cache, response_node, artefatos |
| `POST /drive/executor-upload-url` | `_validate_agent_s3_key` + `ws_id in ...` | DataOutput com entrada no Drive |

## Correção proposta

O executor envia o run (`task_id`, já disponível como `self._task_id` em todo nó
— ver `flow/nodes/base.py`) e o servidor deriva a autorização da própria linha de
`WorkflowRun`, sem confiar no valor enviado para nada além da busca:

1. carrega o `WorkflowRun` pelo `task_id`;
2. confere que `run.host == f"executor:{executor.id_hash}"` — o run foi despachado
   para *este* executor (mesmo cruzamento que `_query_run_belongs_to_agent` já faz
   em `executor_ws_router.py`);
3. confere que o recurso pertence a `run.workspace_id` (em vez de "algum
   workspace do executor").

> Esquema das chaves (âncora do passo 3): os prefixos aceitos são `drive/`,
> `pin-cache/` e `artifacts/`, todos no formato `{prefixo}/{workspace_id}/…`
> (artefatos como `artifacts/{workspace_id}/{task_id}/arquivo`). É esse
> `{workspace_id}` embutido — hoje comparado com "algum workspace do executor" —
> que a checagem por run passa a comparar com `run.workspace_id`.

O padrão de referência já existe em `_authorize_key`
(`app/api/routers/change_detector_router.py`), que resolve o workspace do
workflow antes de liberar a chave.

## Rollout

Executores são externos/on-premise e atualizam de forma independente: se o
servidor passar a **exigir** o `task_id` de imediato, todo executor que ainda não
subiu quebra em qualquer leitura do Drive. Três passos:

1. **Executor** passa a enviar o `task_id` (header ou query) nos cinco endpoints.
2. **Servidor** aceita o campo como opcional: quando presente, aplica a checagem
   por run; quando ausente, mantém o comportamento atual e loga em `warning` com
   o `executor_id` e o `executor_version` do handshake.
3. **Enforcement** depois que os logs mostrarem a frota atualizada — o
   `executor_version` chega no handshake (`executor_ws_router.py`), então dá para
   gatear por versão mínima em vez de data.

## Itens menores relacionados

- `local_fallback=True` (em `flow/utils/artifact_helpers.py`) devolve a `s3_key`
  do MinIO mesmo quando o upload falhou e o artefato ficou só no disco do
  executor. O servidor registra um `Artifact` apontando para objeto inexistente.
  O flag hoje é informativo — o servidor poderia usá-lo para marcar o artefato.
- `count_orphaned_pinned_artifacts` (`app/core/storage_reconciliation.py`) apenas
  audita pins órfãos de workflow deletado; não remove.
