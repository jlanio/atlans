# Armadilhas conhecidas

Quase todo defeito desta plataforma é silencioso: o fluxo termina verde e o
dado está errado. A lista abaixo é o que já mordeu, com o motivo.

## Execução

- **Pin em nó de saída suprime a escrita.** O modo Pin devolve o resultado
  salvo em vez de executar o nó. Num nó de saída isso significa que nada é
  gravado, nenhum e-mail sai — e a execução reporta sucesso, com o
  `rowsInserted` da execução em que foi fixado. Pin serve para nó CARO a
  montante, nunca para nó terminal.
- **4xx e 5xx do `HttpRequest` contam como sucesso.** Não há
  `raise_for_status`: um 401 vira saída normal e o fluxo segue. Se o fluxo
  depende da resposta, ponha um `Conditional` sobre `status_code` logo depois.
- **Resposta binária do `HttpRequest` vira texto.** O corpo passa por
  `response.json()` e cai para `response.text`. Um ZIP ou um shapefile é
  decodificado como string irrecuperável.
- **Não há suporte a raster.** O motor trabalha com vetor. Pedido que envolve
  imagem de satélite ou modelo de elevação não tem fluxo possível aqui — diga
  isso em vez de montar um que não roda.
- **URL de download dura 5 minutos.** As URLs pré-assinadas de artefato e de
  arquivo do Drive expiram rápido; use-as na hora, não as guarde. Conteúdo
  que ficou no executor (`content_location: "executor"`) não tem download
  remoto nenhum.

## Validação

- **Validação e execução não são a mesma coisa.** A validação simula: resolve
  o schema de cada nó e percorre o grafo sem gravar linha nem enviar e-mail. O
  único acesso externo é o do `DatabaseSpatialQuery`, que abre conexão para
  descobrir as colunas. Um nó `WFS` NÃO é sondado: URL errada passa. O que a
  validação faz é conferir o catálogo — `unknown_source` (fonte que ninguém
  catalogou) e `failing_source` (fonte que falhou na última verificação) são
  avisos; ver o tópico `sources`.
- **O relatório vem inteiro.** Nome de nó inexistente não interrompe a
  checagem do resto: ele entra como `unknown_node` no `report.errors[]` junto
  com tudo o mais. Os códigos que derrubam a definição são `unknown_node`,
  `duplicate_node_id`, `cycle`, `invalid_credential_id` e `construction_error`
  — nesse caso a tool devolve o erro `validation` com o `report` junto, e nada
  é gravado. Corrija tudo e revalide uma vez só.
- **`schema_source` diz de onde saiu o schema de cada nó.** `static` (do
  catálogo), `simulated` (o nó rodou a simulação), `declared` (deduzido da
  definição: `output_vars` do `PythonScript`, `rules`/`fallback_output` do
  `Switch`, `ports` do `SubWorkflowInput`) ou `unknown` (nó de saída dinâmica
  sem nada declarável — schema vazio, mas o nó continua na resposta). `unknown`
  não é reprovação; é "só se sabe em execução".
- **`disabled_nodes` e `subworkflow_errors` podem vir `null`.** Não é lista
  vazia: é "não foi checado". Sem `workspace_id` a validação não abre sessão
  de banco, então não há como saber se um nó está desabilitado na instalação
  nem se o sub-fluxo referenciado existe. Informe `workspace_id` quando o
  fluxo tiver sub-fluxo ou credencial — `report.hints` pede isso.
- **Chaves reservadas.** Ao iterar os schemas por `node_id`, pule toda chave
  que começa com `__` (`__report__`, `__edge_diagnostics__` e o que vier).

## Estrutura

- **Propriedade inventada some.** Não vira erro de execução: o nó a descarta e
  roda com o default. A validação a acusa como aviso `undeclared_property` —
  leia os avisos.
- **`from_key` inexistente não derruba a run**, só omite a porta. A checagem é
  estática: `edge_from_key_unknown`.
- **Aresta sem chave saindo de nó com várias saídas** espalha tudo e o filho
  fica dependendo da ordem das chaves do pai: `edge_spread_ambiguous`.
- **`fallback_output: ""` no `Switch`** emite a porta `''`, que nenhuma aresta
  consegue nomear — a fiação a partir dela está morta. A chave ausente cai no
  default; a chave presente e vazia, não.
- **Propriedade `object` escrita como texto ilegível** (`rules` do `Switch`,
  `queryParams`, `headers`) falha na validação de parâmetros antes de o nó
  executar: `invalid_json_property`.
