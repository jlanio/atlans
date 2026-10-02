# Servidor MCP do Atlans

O Atlans expõe um servidor **MCP** (Model Context Protocol) no caminho `/mcp`
do próprio site: numa instalação em `atlans.example.org`,
**`https://atlans.example.org/mcp`**. Os exemplos abaixo usam esse domínio; a
tela de tokens mostra os comandos já com o endereço da sua instalação. Qualquer
cliente que fale MCP sobre HTTP
(*streamable HTTP*) conecta com uma URL e um token pessoal, e passa a enxergar
os workspaces, os fluxos, o catálogo de nós, as credenciais e o Drive da conta
dona do token — **nada além do que essa conta já alcançava pela interface**.

Este documento é a fonte única para quem conecta um cliente: URL, token,
ferramentas, limites, erros e o que fazer quando não funciona.

## Sumário

- [O que é e o que dá para fazer](#o-que-é-e-o-que-dá-para-fazer)
- [Conectar](#conectar)
- [Autenticação](#autenticação)
- [Snippets por cliente](#snippets-por-cliente)
- [Escopos e ferramentas](#escopos-e-ferramentas)
- [Executar um fluxo](#executar-um-fluxo)
- [Resources](#resources)
- [Prompts](#prompts)
- [Limites](#limites)
- [Erros](#erros)
- [Segurança](#segurança)
- [Troubleshooting](#troubleshooting)
- [Changelog e versionamento](#changelog-e-versionamento)

---

## O que é e o que dá para fazer

MCP é um protocolo aberto para dar a um programa cliente acesso a *ferramentas*
(chamadas de função), *resources* (documentos endereçáveis por URI) e *prompts*
(roteiros prontos) de um sistema externo. O servidor do Atlans publica os três.

Com um token de leitura, o cliente conectado consegue:

- listar os workspaces e os fluxos que a conta alcança, com gatilhos,
  agendamento, estado do portal e data da última alteração;
- abrir um fluxo — resumo dos nós e das arestas, `params_schema`, pins,
  número de versões — e, sob pedido, a definition inteira **redigida**;
- ler o contrato de entrada e saída de um fluxo (`inputs`/`outputs`);
- pesquisar os 63 nós nativos e ler o schema de propriedades de cada um;
- listar credenciais (só metadados — nunca o segredo) e arquivos do Drive,
  e gerar uma URL de download temporária;
- ler o guia de autoria, tópico a tópico.

Com `workflows:write`, além disso:

- validar uma definition sem gravar nada e receber o relatório por nó e por
  aresta (erros, avisos, schema de saída, `params_schema` sugerido);
- criar e atualizar fluxos — sempre validando antes, por padrão;
- ativar e desativar um fluxo, e publicá-lo (ou despublicá-lo) no portal.

Com `runs:execute`, disparar uma execução e, se quiser, **esperar o desfecho**
na mesma chamada, com progresso nó a nó (ver
[Executar um fluxo](#executar-um-fluxo)).

Ler execuções — histórico, detalhe de uma delas e os artefatos que produziu —
pede só `workflows:read`, como na interface.

O que **não** entra, por decisão: apagar fluxo, CRUD de credenciais (nem
leitura do segredo), gestão de membros, de executores e de política de
workspace, mover fluxo entre workspaces e qualquer rota de `/admin`.

---

## Conectar

| Item | Valor |
|---|---|
| URL canônica | `https://<site>/mcp` (ex.: `https://atlans.example.org/mcp`) |
| Transporte | streamable HTTP (`POST` com SSE de resposta) |
| Autenticação | `Authorization: Bearer atl_pat_…` |
| Sessão | sem estado (*stateless*) — não há back-channel do servidor para o cliente |

`https://atlans.example.org/mcp/`, com barra final, atende igual: as duas grafias são
rotas exatas para o mesmo servidor e **nenhuma das duas redireciona**. Isso é
deliberado — um `307` faria o cliente repetir a requisição, e com ela o header
`Authorization`, para o endereço do `Location`. Prefira a forma sem barra, que é
a que os clientes trazem escrita.

O servidor recusa qualquer requisição que traga o header `Origin`, com `403`:
nesta fase só clientes que não são navegador se conectam (ver
[403 com menção a `Origin`](#403-com-menção-a-origin)).

Em desenvolvimento, com a API local, a URL é `http://localhost:8000/mcp`.

---

## Autenticação

O acesso é por **token pessoal** (PAT): cada conta cria, lista e revoga só os
próprios tokens, em **`/settings/tokens`** (pela paleta Ctrl+K, «Tokens de
acesso», ou pela URL), e o token age em nome de quem o criou — nunca use o de
outra pessoa, porque tudo o que ele fizer fica registrado em nome dela. Por
enquanto só o administrador do sistema alcança páginas fora da Home (o
`web/proxy.ts` devolve `/` aos demais, e o item saiu do menu da conta), então
hoje só administradores conseguem criar tokens; as mensagens de recusa do MCP
dizem isso. Ao criar você escolhe:

- **nome** — para reconhecer o token na lista e revogá-lo depois;
- **escopos** — `workflows:read`, `workflows:write`, `runs:execute`,
  `triggers:manage`, `drive:read`, `drive:write`. Dê só o que for usar;
- **workspaces** — a lista explícita dos atuais, ou «todos, inclusive os que
  eu entrar depois»;
- **validade** — 30, 90, 180 ou 365 dias.

O segredo (`atl_pat_` + 43 caracteres) aparece **uma única vez**, no momento da
criação. Guarde-o num gerenciador de segredos ou numa variável de ambiente.

Regras do envio:

- o token vai **sempre** no header `Authorization: Bearer atl_pat_…`;
- **nunca** em query string (`?token=`/`?access_token=`) — a requisição é
  recusada com 401 de propósito: query string vaza em log de proxy e histórico
  de navegador;
- o servidor **não** aceita o JWT de sessão da interface;
- toda falha de autenticação responde `401` com o header
  `WWW-Authenticate: Bearer realm="atlans-mcp"` (e `error="invalid_token"`
  quando o formato do segredo está certo mas o token não resolve — revogado,
  expirado, ou de um usuário suspenso).

O token é revogado automaticamente quando a senha do dono muda, quando a conta
é suspensa e quando a conta é excluída. Revogar na lista de tokens derruba o
acesso na hora.

---

## Snippets por cliente

Todos os exemplos leem o segredo de `ATLANS_TOKEN`, nunca da linha de comando:
um comando com o segredo literal fica no `~/.bash_history` e aparece em `ps`.

```bash
export ATLANS_TOKEN='atl_pat_…'   # do gerenciador de segredos, não do histórico
```

### Claude Code

```bash
claude mcp add --transport http atlans https://atlans.example.org/mcp --header "Authorization: Bearer ${ATLANS_TOKEN}"
```

### Cursor, VS Code e Windsurf

No `mcp.json` do cliente:

```json
{
  "mcpServers": {
    "atlans": {
      "url": "https://atlans.example.org/mcp",
      "headers": {
        "Authorization": "Bearer ${ATLANS_TOKEN}"
      }
    }
  }
}
```

Alguns clientes não interpolam variáveis de ambiente dentro do `mcp.json`;
nesses, substitua `${ATLANS_TOKEN}` pelo segredo e trate o arquivo como
segredo (fora do controle de versão, permissão `600`).

### mcp-remote

Para clientes que só falam MCP por stdio:

```bash
npx mcp-remote https://atlans.example.org/mcp --header "Authorization:${AUTH_HEADER}"
```

Defina `AUTH_HEADER="Bearer atl_pat_…"` no ambiente. A quebra em duas variáveis
é do próprio `mcp-remote`: ele corta o argumento no primeiro espaço.

### Conector MCP da API da Anthropic

O bloco `mcp_servers` não vale sozinho — é preciso declarar também o
`mcp_toolset` correspondente, com o mesmo `name`:

```python
import os
from anthropic import Anthropic

client = Anthropic()
resposta = client.beta.messages.create(
    model="claude-opus-5",
    max_tokens=16000,
    betas=["mcp-client-2025-11-20"],
    mcp_servers=[
        {
            "type": "url",
            "url": "https://atlans.example.org/mcp",
            "name": "atlans",
            "authorization_token": os.environ["ATLANS_TOKEN"],
        }
    ],
    tools=[{"type": "mcp_toolset", "mcp_server_name": "atlans"}],
    messages=[{"role": "user", "content": "Liste meus fluxos ativos."}],
)
```

### OpenAI Agents SDK

```python
import os
from agents import Agent
from agents.mcp import MCPServerStreamableHttp

servidor = MCPServerStreamableHttp(
    params={
        "url": "https://atlans.example.org/mcp",
        "headers": {"Authorization": f"Bearer {os.environ['ATLANS_TOKEN']}"},
    }
)
agente = Agent(name="Atlans", mcp_servers=[servidor])
```

---

## Escopos e ferramentas

A autorização tem duas camadas, e as duas precisam passar:

1. **escopo do token** — o que o token pede na criação;
2. **papel no workspace** — o que a conta tem lá dentro
   (`viewer` < `editor` < `operator` < `admin` < `owner`).

Uma ferramenta fora do escopo do token nem aparece em `tools/list`, e chamada
diretamente responde `forbidden_scope` nomeando o escopo que falta. Papel
insuficiente responde `forbidden`. Não existe escopo de administrador: um PAT
nunca atravessa o escopo de membro, mesmo que a conta seja admin da plataforma.

| Ferramenta | Escopo | Papel mínimo | O que faz |
|---|---|---|---|
| `list_workspaces` | `workflows:read` | membro | Workspaces alcançados pelo token, com o papel em cada um |
| `list_workflows` | `workflows:read` | membro | Fluxos do workspace (ou de todos), em itens leves |
| `get_workflow` | `workflows:read` | membro | Resumo do fluxo; `include_definition=true` traz a definition redigida |
| `get_workflow_contract` | `workflows:read` | membro | `inputs`/`outputs` declarados do fluxo |
| `search_nodes` | `workflows:read` | — | Índice compacto do catálogo de nós |
| `describe_node` | `workflows:read` | — | Propriedades, entradas e saídas de um nó |
| `list_credentials` | `workflows:read` | membro | Metadados das credenciais — nunca o segredo |
| `list_drive_files` | `drive:read` | membro | Arquivos do Drive do workspace |
| `get_drive_download_url` | `drive:read` | membro | URL pré-assinada de download (5 min) |
| `get_portal_info` | `workflows:read` | membro | Estado do portal do fluxo e a URL de compartilhamento |
| `get_authoring_guide` | `workflows:read` | — | Um tópico do guia de autoria |
| `validate_workflow` | `workflows:write` | editor | Valida uma definition sem gravar nada: relatório por nó e por aresta, nós desabilitados, sub-fluxos e `params_schema` sugerido. Recusa na entrada a definition com segredo em claro |
| `create_workflow` | `workflows:write` | editor | Cria um fluxo no workspace; valida antes por padrão e carimba a autoria com o dono do token |
| `update_workflow` | `workflows:write` | editor | Atualiza definition, nome, descrição ou `params_schema` — só os campos enviados mudam |
| `set_workflow_active` | `workflows:write` | editor | Ativa ou desativa o fluxo, sincronizando os agendamentos. Único caminho para `is_active` |
| `set_portal_access` | `workflows:write` | editor | Publica ou despublica no portal (`disabled`/`public`/`private`) e devolve a URL absoluta |
| `run_workflow` | `runs:execute` | operator | Dispara uma execução e, por padrão, espera o desfecho notificando o progresso |
| `get_run` | `workflows:read` | membro | Detalhe de uma execução: status, tempo, erro e o retrato de cada nó |
| `list_runs` | `workflows:read` | membro | Histórico de execuções, com filtros de workflow, workspace, status, origem, data e texto |
| `get_run_artifacts` | `workflows:read` | membro | Artefatos de uma execução, com URL temporária de download (5 min) |
| `get_run_events` | `workflows:read` | membro | Log bruto de uma execução — **dura 1 hora**; `availability` diz por que veio vazio |
| `cancel_run` | `runs:execute` | operator | Interrompe uma execução em andamento; `outcome` distingue pedido enviado, fechada e já terminada |
| `retry_run` | `runs:execute` | operator | Dispara execução NOVA do mesmo workflow — **não repete a anterior**: definição atual e padrões do `params_schema`, nunca os inputs originais |
| `list_workflow_versions` | `workflows:read` | viewer | Snapshots de um workflow: número, nota e data — sem a definition de cada um |
| `get_workflow_version` | `workflows:read` | viewer | Uma versão do histórico, com a definition **redigida** |
| `restore_workflow_version` | `workflows:write` | editor | Volta o workflow a uma versão anterior. **Reversível**: o estado atual vira snapshot antes da troca |
| `duplicate_workflow` | `workflows:write` | editor | Cópia no mesmo workspace. Pins, portal e histórico não acompanham; o agendamento acompanha desligado |
| `list_artifacts` | `workflows:read` | viewer | Os arquivos que as execuções produziram, no workspace indicado (ou em todos os do token), com filtros e paginação |
| `list_pins` | `workflows:read` | viewer | Quais saídas de nó estão congeladas. `cached` diz se o cache já existe; `expired` é relato, não ação |
| `pin_node_output` | `workflows:write` | editor | Congela a saída de um nó a partir da próxima execução. `ttl_hours` de 1 a 8760. Nó que grava arquivo é recusado |
| `unpin_node_output` | `workflows:write` | editor | Descongela e apaga o cache. `outcome=not_pinned`, sem erro, quando não havia pin |
| `list_schedules` | `workflows:read` | viewer | Quando o fluxo dispara sozinho. Traz `workflow_active`, porque o agendador ignora agendamento de fluxo inativo |
| `create_schedule` | `triggers:manage` | **operator** | Cron (5 campos), intervalo ou RRULE. Agendar é executar — daí o papel |
| `update_schedule` | `triggers:manage` | **operator** | Só os campos enviados. `active=false` pausa sem perder a configuração |
| `delete_schedule` | `triggers:manage` | **operator** | Exige `confirm=true`; sem ele, descreve o que seria apagado e não apaga |
| `create_drive_upload_url` | `drive:write` | editor | Passo 1 de 3: devolve URL que aceita PUT. **Não envia o arquivo** — quem faz o PUT é quem tem os bytes |
| `confirm_drive_upload` | `drive:write` | editor | Passo 3: mede o objeto real e publica no Drive. Acima do teto, recusa e apaga os bytes |
| `delete_drive_file` | `drive:write` | editor | Exige `confirm=true`. Sem lixeira. É também como se substitui um arquivo |
| `search_sources` | `workflows:read` | viewer | Busca no catálogo de fontes pré-mapeadas (camadas WFS conhecidas) por tema, SEM rede. Chame antes de preencher `url`/`typeName` |
| `describe_source` | `workflows:read` | viewer | A ficha de uma fonte: `node_snippet` pronto para colar, esquema (CRS, extensão, colunas) e estado da última verificação |
| `probe_source` | `workflows:write` | editor | Sonda um WFS fora do catálogo: camadas (GetCapabilities) e, com `type_name`, o esquema. Só metadados; não cria fonte, mas atualiza o estado de uma já catalogada e fala com a internet (balde `probe`, `openWorldHint`) |
| `register_source` | `workflows:write` | editor | Sonda e guarda uma camada no catálogo do workspace, com título, temas e dicas. Idempotente: a mesma URL+camada atualiza a linha |

As quatro ferramentas de fontes vivem em torno do **catálogo interno** de camadas
WFS pré-mapeadas (`docs/fontes.md`): a regra do guia é consultar `search_sources`
antes de preencher qualquer `url`/`typeName`, e só sondar (`probe_source`) e
registrar (`register_source`) o que o catálogo não tem. Essas duas são as únicas
ferramentas anotadas com `openWorldHint: true` — fazem o servidor falar com uma
URL pública (IP privado, loopback e link-local continuam bloqueados) — e gastam
o balde `probe`.

Ler execuções pede `workflows:read`, e não `runs:execute`: é a mesma exigência
da interface, onde acompanhar o histórico só depende de ser membro do workspace
do run. Um token de leitura acompanha o que outros dispararam; disparar é que
exige o escopo de execução e papel `operator`.

Duas coisas sobre execuções que a tool diz, e que valem estar aqui também porque
quem lê o doc costuma ser quem escreve o agente:

**O log dura uma hora.** `get_run_events` lê o histórico do Redis, com TTL de
3600 s. Depois disso os eventos não existem em lugar nenhum — o que resta da
execução é o `node_stats` de `get_run`, que está no banco e não expira. Quando a
lista vem vazia, `availability` diz o motivo (`em_andamento`, `expirada`,
`sem_eventos`, `indeterminada`) em vez de deixar o agente concluir sozinho que
"não houve saída".

**`retry_run` não repete a execução.** O Atlans não guarda os `inputs` de um run,
então reexecutar aquele exatamente não é possível: a tool dispara o workflow com
a **definição atual** e com os padrões que o `params_schema` declara — nunca os
inputs originais. A resposta traz `reused_inputs: false` e
`inputs_sent` com o que de fato foi mandado, para que isso não passe
despercebido. Um fluxo com parâmetro obrigatório sem padrão é recusado com
`validation`, em vez de gastar um executor numa execução condenada. Quem precisa
repetir de verdade usa `run_workflow(workflow_id, inputs=…)`. A execução nova é
marcada como origem `mcp`, e não `retry`: ela é indistinguível de um disparo
comum, e rotulá-la de outro jeito contaria no Histórico uma reexecução que não
aconteceu.

**`cancel_run` responde `already_finished` em dois casos diferentes**, porque o
núcleo usa um rótulo só: a execução já tinha terminado, ou não há executor
associado a ela — e no segundo caso ela pode continuar em `running`. Por isso a
resposta traz `status_before`, o estado no instante anterior ao pedido, e um
`hint` avisando quando os dois discordam. E chamar duas vezes é seguro, mas não
devolve necessariamente a mesma coisa: quem fecha uma execução já entregue é o
executor, de volta, então as duas chamadas costumam responder `requested`.

Três coisas sobre o acervo, pelo mesmo motivo:

**`restore_workflow_version` é reversível, e a resposta diz como.** Antes de
trocar a definition, o estado atual vira um snapshot novo no histórico — o
número dele volta em `snapshot_version`, e restaurar esse número
desfaz a operação. O que **não** é garantido é a ressincronização do
agendamento: ela é best-effort no núcleo, e se falhar a restauração ainda assim
vale, sem aviso na resposta. Para fluxo que depende de agenda, confirme com
`get_workflow`.

**A definition de uma versão sai sempre redigida.** O histórico guarda a
connection string cifrada; `get_workflow_version` a decifra para conferir que o
token não está corrompido e então **apaga o valor** antes de devolver. Não há
parâmetro para pedir o segredo — restaurar não precisa dele, porque o restore
copia o blob cifrado sem abri-lo.

**`list_artifacts` distingue as duas datas que a tool irmã confunde.** Um item
traz `content_expires_at` (quando o ARQUIVO sai da retenção — dias) e
`url_expires_at` (quando o LINK assinado vence — 5 minutos). Em
`get_run_artifacts`, `expires_at` significa a segunda; reaproveitar o nome aqui
para a primeira faria quem lê concluir que o download vale uma semana.

**`duplicate_workflow` deixa coisas para trás, de propósito.** Pins (apontam
para artefatos de execuções que a cópia nunca teve), estado do portal (uma cópia
não nasce publicada porque o original estava) e histórico de versões (descreve
edições que não aconteceram ali). O agendamento acompanha, mas **desligado**:
duplicar costuma preceder uma edição, e nascer disparando sozinho dobraria a
carga em silêncio.

Convenções de entrada, valendo para todas:

- `workflow_id` e `workspace_id` aceitam **id ou nome**; nome que casa com mais
  de um recurso devolve `ambiguous` com a lista de candidatos;
- `workspace_id` é **opcional** quando o token alcança exatamente um workspace;
- texto escrito por gente (nome, descrição, alias, mensagem de erro, nome de
  arquivo) sai sempre dentro de `untrusted_data`; ids, enums, números e datas
  ficam no topo da resposta;
- uma definition enviada a `validate_workflow`, `create_workflow` ou
  `update_workflow` **não pode carregar segredo em texto claro**: a chamada é
  recusada com `secret_in_definition`, que lista os caminhos dos campos (nunca
  os valores). Vale também para a que só valida — recusar na entrada é o que
  impede a senha de chegar ao caminho de validação. Credencial se referencia
  por `credential_id` (`list_credentials`);
- `validate_first=true` é o padrão de `create_workflow` e `update_workflow`:
  com erros no relatório, nada é gravado. `force=true` grava apesar dos erros
  comuns, mas **nunca** apesar dos fatais (nó inexistente, id duplicado, ciclo,
  `credential_id` que não é UUID) — esses recusam sempre, porque geram um fluxo
  que o executor nem consegue montar.

---

## Executar um fluxo

```text
run_workflow(workflow_id, inputs?, debug_mode=false, wait=true,
             timeout_seconds=120, idempotency_key?)
```

### `inputs` conferidos antes do despacho

`inputs` é conferido contra o `params_schema` do fluxo **antes** de a execução
ser despachada — um parâmetro trocado descoberto no meio da execução já custou
executor, escrita em banco e artefato errado. As regras:

- **coerção só a partir de texto.** `"5"` vira `5` (inteiro se for dígito puro,
  senão decimal), `"true"`/`"1"`/`"sim"` viram `true`, `"false"`/`"0"`/`"não"`
  viram `false`, e um `object` aceita objeto, lista ou o JSON correspondente em
  string. Quem manda `1` onde se declarou `boolean` recebe erro: em JSON,
  número é número;
- **string vazia nunca vira valor.** `""` num campo `number` é erro, não zero;
- **obrigatório sem valor e sem `default` é erro**; com `default`, o padrão é
  preenchido (e coagido pelas mesmas regras);
- **chave não declarada passa intacta** e é listada em `hints` — o gatilho de
  webhook tem o próprio `payload_schema`, validado no despacho;
- **`params_schema` ausente ou malformado não é erro**: os `inputs` seguem sem
  conferência e um aviso em `hints` diz que ninguém os conferiu.

Os problemas voltam agregados num único erro `validation`, com
`errors: [{path, message}]` — corrija tudo de uma vez. A mensagem nomeia o
campo e o tipo esperado e **nunca ecoa o valor recebido**.

### `wait`, prazos e status

Com `wait=true` (padrão) a chamada segura a resposta até a execução terminar,
notificando o progresso nó a nó, e devolve o desfecho completo: status,
duração, o retrato de cada nó, o erro e a lista de artefatos (sem link — para
baixar, chame `get_run_artifacts`). O prazo é `timeout_seconds`, entre **5 e
300 segundos**, com **120 s** por padrão; valor fora da faixa é ajustado para o
limite mais próximo.

Os status possíveis — e a diferença entre os dois últimos importa:

| `status` | Significa | O que fazer |
|---|---|---|
| `success` / `failed` / `cancelled` | Desfecho gravado | Ler o resultado |
| `running` | Ainda executando, ou o prazo acabou antes do fim | Consultar `get_run(run_id)`; a execução **continua** no servidor |
| `unknown` | O fluxo **terminou**, mas o desfecho ainda não foi gravado | Consultar `get_run(run_id)` daqui a pouco — **não execute de novo** |

`unknown` é o caso em que o evento de conclusão chegou antes de a linha do
histórico ser escrita. Chamá-lo de `running` faria o cliente esperar por um fim
que já aconteceu, e poderia convencê-lo a disparar a mesma execução outra vez.

Com `wait=false` a resposta volta na hora, com o `run_id` e `status: "running"`.

Na resposta com desfecho, `events_dropped` diz quantos eventos o buffer
descartou durante a espera: o progresso pode ter pulado nós. O desfecho, esse,
vem do banco e está inteiro.

### Idempotência e recusas

`idempotency_key` protege contra disparo repetido do mesmo fluxo pelo mesmo
usuário por 24 horas: a segunda chamada com a mesma chave devolve a execução
original, **mesmo que ela tenha falhado**. A chave vale por usuário — duas
pessoas com a mesma chave fazem duas execuções.

Recusas que acontecem antes de qualquer custo: fluxo desativado responde
`workflow_inactive` (ative com `set_workflow_active`), `inputs` inválidos
respondem `validation`, e o teto de esperas simultâneas responde `wait_limit`
sem despachar nada. Se não houver executor online, a resposta é `no_executor`.

---

## Resources

Resources são leitura endereçável por URI — úteis quando o cliente prefere
anexar um documento a fazer uma chamada de ferramenta. Todos exigem
`workflows:read` e respeitam o mesmo escopo de workspace.

| URI | Tipo | Conteúdo |
|---|---|---|
| `atlans://guide/authoring/{topic}` | `text/markdown` | Um tópico do guia: `overview`, `edges`, `credentials`, `expressions`, `inputs`, `sources`, `sql`, `pitfalls`, `recipes` |
| `atlans://catalog/nodes{?type}` | `application/json` | Índice do catálogo; sem `type`, a lista de tipos com a contagem de cada um |
| `atlans://catalog/nodes/{name}` | `application/json` | Definição completa de um nó |
| `atlans://workspaces/{id}/workflows` | `application/json` | Os fluxos de um workspace |
| `atlans://workflows/{id}` | `application/json` | Resumo do fluxo, com a definition redigida |
| `atlans://workflows/{id}/contract` | `application/json` | Contrato de entrada e saída do fluxo |
| `atlans://runs/{id}` | `application/json` | Uma execução com o retrato **completo** de cada nó — o mesmo de `get_run(node_stats="full")` |

O catálogo nunca sai como um blob único: `atlans://catalog/nodes` sem `type`
devolve o índice de tipos e a dica de filtrar, porque o JSON completo dos 63
nós passa de 78 KB.

`atlans://runs/{id}` traz `node_stats` completo (com `output_keys` e
`output_columns`) porque quem anexa uma execução ao contexto está investigando
uma falha; a ferramenta `get_run` continua oferecendo o resumo a quem só quer o
status. A mensagem de erro do run e a de cada nó saem higienizadas, dentro de
`untrusted_data`.

Todo resource respeita a mesma guarda da ferramenta de que é alias: leitura de
dados de workspace confere o escopo, exige o papel e deixa linha de auditoria.
`resources/read` não consome a cota de chamadas de ferramenta (ver
[Limites](#limites)).

---

## Prompts

Prompts são roteiros prontos: o cliente pede um pelo nome (`prompts/get`) com os
argumentos e recebe um texto que ORDENA as chamadas de ferramenta seguintes.
Não gastam cota e não exigem escopo nenhum do token (a conexão, essa, continua
exigindo o token): quem exige escopo e papel são as ferramentas que o roteiro
manda chamar.

| Prompt | Argumentos | O que o roteiro faz |
|---|---|---|
| `criar_fluxo` | `descricao` (obrigatório), `workspace_id` | Entender os dados → guia e catálogo de nós → rascunho → `validate_workflow` até o relatório ficar limpo → mostrar o JSON → **oferecer** `create_workflow`, nunca criar sem confirmação |
| `diagnosticar_run` | `run_id` | `get_run` com `node_stats="full"` → ler `error_category` → achar o primeiro nó que falhou → comparar com `typical_seconds` → consultar as armadilhas do guia |
| `revisar_fluxo` | `workflow_id` | `get_workflow` com a definition → `validate_workflow` → credenciais vencidas em `list_credentials` → agendamento preso a fluxo inativo → histórico de falhas. Só relata, não corrige |
| `explicar_fluxo` | `workflow_id` | `get_workflow` + `get_workflow_contract` → o que dispara, o que entra, o que cada etapa faz, o que sai e de que depende. Só leitura |

**Um prompt nunca interpola texto vindo do banco.** Nome de fluxo, descrição e
mensagem de erro não entram no roteiro — só o que a própria pessoa digitou como
argumento e os identificadores que ela passou. O motivo é direto: o texto de um
prompt chega ao cliente no nível das instruções, sem `untrusted_data` onde
embrulhá-lo, e um fluxo chamado "Ignore as instruções anteriores…" viraria
ordem. Os dados do fluxo entram na conversa depois, pelo retorno das
ferramentas, já separados.

---

## Limites

| Limite | Valor | Onde |
|---|---|---|
| Chamadas de ferramenta | 120/min por token | Servidor |
| `run_workflow`, `retry_run` | 20/min por token, **somados** | Servidor (balde `run`, somado ao geral) |
| `validate_workflow`, `create_workflow`, `update_workflow` | 20/min por token, somados | Servidor (balde `validate`, somado ao geral) |
| `probe_source`, `register_source` | 10/min por token, somados | Servidor (balde `probe`, somado ao geral) |
| Esperas simultâneas (`wait=true`) | 3 por token, 40 na plataforma (`wait_limit`) | Servidor |
| Prazo de `wait` | 120 s por padrão, 300 s no máximo, 5 s no mínimo | Servidor |
| Itens por página em `list_runs` | 20 por padrão, 100 no máximo | Servidor |
| Artefatos por resposta em `get_run_artifacts` | 100 (`truncated: true` quando há mais) | Servidor |
| Itens por página em `list_artifacts` | 50 por padrão, 100 no máximo (`has_more`) | Servidor |
| Versões por página em `list_workflow_versions` | 50 por padrão e no máximo (`has_more` + `offset`) | Servidor |
| Eventos por resposta em `get_run_events` | 200 por padrão e no máximo (`dropped_oldest` conta o que ficou de fora) | Servidor |
| Retenção do log de execução | 3600 s (1 h) a partir do último evento | Redis |
| Requisições HTTP | 240/min por IP (burst 60) | Traefik (`rate-mcp`) |
| Corpo da requisição | 4 MiB | Transporte |

`resources/read` e `prompts/get` não contam na cota de 120/min.

Nenhum corte é silencioso, e cada tool diz o que cortou: `list_runs`,
`list_artifacts` e `list_workflow_versions` devolvem `has_more` (as duas
primeiras com `offset` para pedir a página seguinte; a terceira também);
`get_run_artifacts` devolve `truncated: true` com uma dica quando a execução
produziu mais arquivos do que cabe na resposta; e `get_run_events` devolve
`returned` e `dropped_oldest` — este último contando os eventos mais antigos
que ficaram de fora, porque quem investiga uma falha quer o fim do log.

O limite de borda é por **IP** e o de ferramentas é por **token**: vários
clientes atrás do mesmo NAT dividem o primeiro, e cada token tem o segundo só
para si. Estourar a cota de chamadas devolve `rate_limited` com
`retry_after_seconds`; estourar o teto de esperas devolve `wait_limit`; no
Traefik, um `429` HTTP.

`run_workflow(wait=true)` segura a chamada até a execução terminar; passado o
prazo, a resposta volta com `status: "running"` e o `run_id` para consultar
depois, e a execução segue no servidor. O teto de esperas simultâneas existe
porque cada espera segura uma assinatura de eventos e uma resposta aberta: no
teto, execute com `wait=false` e acompanhe por `get_run(run_id)`. Artefatos
nunca trafegam pelo MCP — o que volta é uma URL pré-assinada.

Sem Redis no ar, as cotas **degradam abertas** (com aviso no log do servidor) e
o teto de esperas cai para um contador por processo: um incidente transitório
de infraestrutura não vira recusa de toda chamada.

---

## Erros

Toda falha de ferramenta volta como erro de tool do MCP, com a mensagem em JSON:

```json
{
  "code": "forbidden_scope",
  "message": "Este token não tem o escopo necessário: workflows:write.",
  "hint": "crie um token com esse escopo em /settings/tokens (hoje, página só de administradores do sistema)",
  "missing_scope": "workflows:write"
}
```

`code` e `message` estão sempre presentes; `hint` aparece quando existe uma
ação óbvia; os demais campos dependem do código.

| `code` | Quando | Campos extras |
|---|---|---|
| `unauthorized` | Token ausente, inválido, expirado ou revogado (chega como 401 HTTP, antes de qualquer ferramenta) | — |
| `forbidden` | Papel insuficiente no workspace, ou recurso fora do escopo do token | — |
| `forbidden_scope` | O token não pede o escopo que a ferramenta exige | `missing_scope` |
| `not_found` | Fluxo, arquivo, nó ou execução que não existe — ou que a conta não alcança | — |
| `ambiguous` | O nome informado casa com mais de um recurso | `candidates[]` |
| `validation` | Entrada inválida | `report` quando a recusa vem do lint de uma definition; `errors[{path, message}]` quando vem dos `inputs` ou da forma do corpo |
| `conflict` | Nome de fluxo já usado no workspace | `suggestion`, um nome alternativo derivado do que foi enviado (ausente quando não dá para deduzi-lo) |
| `workflow_inactive` | O fluxo está desativado e não pode ser executado | — |
| `no_executor` | Nenhum executor online para atender a execução | — |
| `unavailable_local` | O conteúdo só existe no executor; não há download remoto | — |
| `secret_in_definition` | A definition enviada carrega um segredo em claro | `paths[]` — o caminho de cada campo, nunca o valor |
| `rate_limited` | Cota de chamadas do token estourada | `retry_after_seconds` |
| `wait_limit` | Esperas simultâneas (`wait=true`) no teto do token ou da plataforma | — |
| `unavailable` | Dependência fora do ar (503) | — |
| `internal_error` | Falha não prevista; a mensagem é genérica de propósito | — |

Trate a lista de campos extras como um piso, não como um contrato fechado: um
campo novo pode aparecer numa versão menor, e o cliente deve ignorar o que não
conhece. O que não muda é o par `code` + `message`.

`not_found` vem antes de `forbidden` de propósito, e vai além disso: um fluxo
que existe no workspace de outra conta responde exatamente o mesmo `not_found`
de um identificador que nunca existiu — mesma frase, mesmo `hint`. A diferença
seria um jeito de descobrir, um id por vez, o que há do outro lado do muro.
Quando o recurso é da sua própria conta e é o *token* que não alcança (um token
emitido para um workspace só), a resposta é `forbidden`: aí não há existência a
esconder de quem já a vê na interface, e sim um alcance a explicar.

---

## Segurança

- **O token não alcança mais do que a conta já alcançava.** Escopo efetivo =
  escopos do token ∩ workspaces do token ∩ papel real em cada workspace. Não há
  caminho de administrador: um PAT de um admin da plataforma vê como membro.
- **Conteúdo de `untrusted_data` é dado, não instrução.** Nome de fluxo,
  descrição, alias, nome de arquivo e mensagem de erro são texto escrito por
  pessoas e podem conter qualquer coisa. O servidor os separa do resto da
  resposta justamente para que o cliente os trate como conteúdo.
- **Definitions saem redigidas.** `connectionString`, `Authorization` e demais
  chaves sensíveis viram `<REDACTED>`, inclusive aninhadas e dentro de listas,
  e toda string folha passa pelo redator de segredos. Credencial se referencia
  por `credential_id` — nunca colando o segredo na definition: uma definition
  com segredo em claro é **recusada na entrada** com `secret_in_definition`,
  antes de qualquer validação ou gravação, nas três ferramentas que recebem
  definition (`validate_workflow` inclusive). A recusa cita o caminho do campo
  e jamais o valor.
- **Mensagem de erro de execução é dado.** `error_message` e o `error` de cada
  nó saem redigidos (uma string de conexão vira `<REDACTED>`) e sempre dentro
  de `untrusted_data` — é o campo mais provável de carregar segredo ou uma
  frase de comando dirigida a quem lê a resposta. Na listagem de execuções ele
  vem resumido; o texto completo está em `get_run`. As notificações de
  progresso de `run_workflow` levam o nome do nó e o status, **nunca** o erro.
- **URL pré-assinada dura 5 minutos** e é uma capability portadora: quem tem o
  link baixa o arquivo, sem token. Não a registre em log nem a repasse.
- **Segredo nunca ecoa.** Nem em mensagem de erro, nem em log de auditoria — o
  que se registra da chamada é o prefixo do token, o usuário, a ferramenta, a
  duração e o resultado.

---

## Troubleshooting

### 401 com `WWW-Authenticate: Bearer`

O header `Authorization` não chegou, não é `Bearer`, ou o token não resolve.
Confira, nesta ordem: a variável de ambiente está exportada na sessão que roda
o cliente; o valor começa com `atl_pat_`; o token não está revogado nem
expirado (a lista em `/settings/tokens` mostra os dois); a conta não foi
suspensa. Um `error="invalid_token"` no header quer dizer que o formato está
certo e o token é que não vale mais — é preciso criar outro.

Se o token estiver na URL como `?token=`, mova-o para o header: query string é
recusada mesmo com o segredo correto.

### 421 Misdirected Request

O `Host` da requisição não está na lista aceita pelo transporte. Acontece ao
apontar o cliente para um domínio ou porta diferentes dos configurados. A lista
padrão aceita o host do `FRONTEND_URL` e, localmente, `localhost` ou `127.0.0.1`.
Para outro domínio, defina `MCP_ALLOWED_HOSTS`.

### 403 com menção a `Origin`

O cliente mandou um header `Origin`. O servidor recusa qualquer `Origin` de
propósito: nesta versão só clientes que não são navegador se conectam. Se o seu
cliente manda `Origin`, ele está rodando dentro de um navegador — esse caminho
depende de OAuth e ainda não existe.

### 429

Duas origens possíveis. Um `429` **HTTP** vem do Traefik: são 240 requisições
por minuto por IP, e o alívio é esperar ou espalhar as chamadas. Um erro de
ferramenta com `code: "rate_limited"` vem do servidor: é a cota do token, e
`retry_after_seconds` diz quanto falta para a janela virar.

### A ferramenta não aparece na lista

`tools/list` é filtrado pelo escopo do token. Se `create_workflow` não aparece,
o token não pede `workflows:write`. Escopo não se edita: crie outro token com os
escopos certos e revogue o antigo.

### URL de download não abre

Em produção, `MINIO_EXTERNAL_ENDPOINT` precisa ser o endereço público do S3 (ex.:
`https://s3.atlans.example.org`) — a
assinatura prende o host, e com `localhost` a URL só resolve de dentro do
Docker. A API registra um aviso no boot quando o valor aponta para um endereço
local. Lembre também que a URL vale 5 minutos.

---

## Changelog e versionamento

O servidor declara a própria versão no `initialize` (campo `version`), separada
da versão do protocolo MCP. É por ela que se confere qual contrato está no ar
depois de um deploy — ferramenta nova sobe a versão menor.

### 1.5.0

- Ferramentas de escrita no Drive: `create_drive_upload_url`,
  `confirm_drive_upload` e `delete_drive_file`. Com elas **os seis escopos do
  token passam a gatilhar alguma coisa** — `drive:write` era o último que a tela
  oferecia com descrição afirmativa e nada por trás.
- O upload são **três chamadas**, e o passo do meio não passa pelo MCP: a tool
  devolve uma URL pré-assinada e quem tem os bytes faz o PUT direto no storage.
  Mandar arquivo por JSON-RPC significaria base64 dentro da mensagem — um
  shapefile de 40 MB viraria 54 MB de texto no contexto de quem chamou. A
  consequência está dita na descrição: **um agente sem o arquivo em disco não
  consegue enviá-lo**, só repassar a URL.
- `confirm_drive_upload` mede o objeto REAL, não o tamanho declarado no passo 1.
  Acima do teto do workspace, recusa **e apaga os bytes**.
- `delete_drive_file` exige `confirm=true` e não tem lixeira. É também como se
  substitui um arquivo, porque **sobrescrever não é uma operação do Drive**.
- Documentado o que o Drive **não** tem, para o agente não descobrir tentando:
  ele é plano — sem renomear, sem mover, sem pasta.

### 1.4.0

- Ferramentas de gatilho: `list_schedules`, `create_schedule`, `update_schedule`
  e `delete_schedule`. É o escopo **`triggers:manage`** deixando de ser um chip
  no cartão do token sem nada por trás.
- As três de escrita pedem **`operator`**, não `editor`: agendar é executar —
  um schedule de um minuto dispara o fluxo com as credenciais do dono,
  indefinidamente. Mesma régua de `run_workflow` e da rota REST.
- `delete_schedule` exige `confirm=true`. Sem ele, descreve o que seria apagado
  e não apaga: a remoção não tem desfazer e falha em silêncio — nada quebra, a
  rotina só deixa de acontecer.
- `list_schedules` devolve **`workflow_active`** no topo. O agendador ignora
  agendamento de fluxo inativo, e nada no agendamento em si denuncia isso: era
  a causa mais comum de "o cron parou" sem nenhum sinal.
- **Fuso padrão unificado.** Havia três respostas para "qual fuso vale quando o
  agendamento não diz o seu?": o nó mandava um fuso fixo, o schema usava
  outro e a coluna nula caía em **UTC** dentro do agendador —
  quatro horas de diferença, em silêncio, entre a tela e o disparo. Agora é uma
  constante só. Sem migração e sem recriar schedule: o valor é o que o nó já
  mandava, então `_mesma_configuracao` continua concordando.

### 1.3.0

- Ferramentas de pin: `list_pins`, `pin_node_output` e `unpin_node_output`. As
  duas de escrita são **idempotentes** — únicas entre as escritas do servidor:
  fixar um nó já fixado reescreve a mesma entrada, e desfixar duas vezes não
  muda nada.
- `pin_node_output` **recusa nó que grava arquivo** (saída, publicação de mapa,
  e-mail, resposta de webhook). Congelar a saída deles fazia o executor pular a
  gravação: o fluxo terminava verde e sem produzir o arquivo. A rota REST
  passou a recusar no mesmo diff, então o pin fantasma não entra por nenhum
  caminho.
- Junto vieram cinco correções na REST de pins, que não tinha teste nenhum: o
  `GET /pins` deixou de estourar 500 com data malformada, `ttl_hours` ganhou
  faixa (`0` era aceito e virava "sem expiração"), o unpin passou a commitar
  ANTES de apagar do storage, a leitura do artefato de cache deixou de levantar
  com linha duplicada, e o `node_id` do corpo — obrigatório e ignorado — virou
  opcional com `extra="forbid"`.

### 1.2.0

- Ferramentas de acervo: `list_workflow_versions`, `get_workflow_version`
  (definition redigida), `restore_workflow_version` (com o número do snapshot
  anterior na resposta), `duplicate_workflow` (que recusa sub-fluxo quebrado
  antes de copiar e carimba a autoria de quem chamou) e `list_artifacts`.

### 1.1.0

- Ferramentas de execução: `get_run_events` (log bruto, com `availability`
  explicando por que a lista veio vazia), `cancel_run` (com `outcome` e
  `status_before` distinguindo pedido enviado, fechada aqui e já terminada) e
  `retry_run` (dispara execução nova do mesmo workflow, sem reaproveitar
  inputs).

### 1.0.0

- Servidor em `https://<site>/mcp`, transporte streamable HTTP sem estado.
- Autenticação por token pessoal no header `Authorization`.
- Ferramentas de descoberta e leitura: `list_workspaces`, `list_workflows`,
  `get_workflow`, `get_workflow_contract`, `search_nodes`, `describe_node`,
  `list_credentials`, `list_drive_files`, `get_drive_download_url`,
  `get_portal_info`, `get_authoring_guide`.
- Ferramentas de construção: `validate_workflow`, `create_workflow`,
  `update_workflow`, `set_workflow_active`, `set_portal_access` — com recusa de
  segredo em texto claro na definition (`secret_in_definition`) e validação
  antes de gravar por padrão.
- Ferramentas de execução: `run_workflow` (com `wait`, progresso nó a nó e
  conferência dos `inputs` contra o `params_schema`), `get_run`, `list_runs` e
  `get_run_artifacts`.
- Resources do guia de autoria, do catálogo de nós, dos workspaces, dos fluxos
  e das execuções (`atlans://runs/{id}`).
- Prompts `criar_fluxo`, `diagnosticar_run`, `revisar_fluxo` e `explicar_fluxo`.
- Cotas por token (geral, `validate`, `run` e `probe`), teto de esperas simultâneas e
  rate limit por IP na borda.

### Política de versionamento

A versão segue *semver* sobre o **contrato das ferramentas**:

- **maior** — remoção ou mudança incompatível no formato de saída;
- **menor** — ferramenta, resource, prompt ou campo novo;
- **correção** — ajuste que não muda o contrato.

Ferramenta que vai sair fica **pelo menos uma versão menor** marcada como
`deprecated` na descrição, dizendo o que usar no lugar, antes de sumir. Campo
novo pode aparecer a qualquer momento: trate a saída como um objeto aberto e
ignore o que não conhece.
