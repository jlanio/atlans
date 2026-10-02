# Assistente — montar fluxos por linguagem natural

O assistente é um painel no editor onde a pessoa descreve o que quer e o fluxo aparece no canvas. Por
baixo, ele conversa com um modelo de linguagem que tem acesso às **mesmas 42 ferramentas** que o
servidor MCP expõe a um agente externo — catálogo de nós, guia de autoria, validação, execução.

É a primeira vez que a plataforma consome o próprio MCP.

## Como ele entrega: `desenhar_no_canvas`

O assistente tem uma ferramenta que **não existe no MCP** e nunca aparece para um cliente
externo: `desenhar_no_canvas(definition, nota?)`. O canvas é do editor, e só faz sentido para
quem está olhando para ele.

**Ela é a entrega.** Enquanto o modelo não a chamar, a tela de quem pediu está vazia — por
melhor que ele tenha explicado. O prompt manda chamá-la cedo e repetidamente: o fluxo cresce
enquanto ele monta, em vez de aparecer inteiro no fim.

Isso conserta um defeito de desenho. Antes, pôr o fluxo na tela era **efeito colateral** de uma
chamada a `validate_workflow` — o painel lia a definição do argumento daquela ferramenta.
Funcionava quando o modelo validava, e nada o obrigava a validar: pedindo *"lê o shapefile e
faz buffer de 500 m"*, ele podia ler o Drive, executar e devolver o GeoJSON. Pedido atendido,
canvas vazio. Nenhuma instrução conserta isso, porque não havia nada cujo nome fosse
"entregue o fluxo". Agora há, e `validate_workflow` voltou a ser meio.

**Executar exige ter desenhado antes.** `run_workflow` é recusado enquanto não houver fluxo na
tela — é o mesmo caminho que produzia a resposta-dado. A recusa é de ordem, não de escopo:
desenhou, pode rodar (com o aval em texto de sempre).

**O desenho entra sozinho.** Num canvas vazio, sempre. Num canvas que já tem trabalho, o
primeiro desenho da conversa espera um clique — e daí em diante ela desenha sem interromper.
`Ctrl+Z` desfaz. Desenhar **não salva**: o Salvar do editor continua sendo de quem está usando.

## O que ele faz, e o que ele não faz

| | |
|---|---|
| **monta e edita** | lê o guia, consulta o catálogo, confere cada propriedade em `describe_node`, rascunha a definição e valida até o relatório ficar limpo |
| **mostra** | ao fim, o painel exibe um cartão com o fluxo pronto e o botão **Aplicar no canvas** |
| **executa** | roda o fluxo com acompanhamento nó a nó — **depois de pedir aval em texto** |
| **NÃO grava** | `create_workflow` e `update_workflow` não existem para ele. Quem aplica no canvas é você, pelo botão do editor |
| **NÃO apaga** | agendamento e arquivo do Drive estão fora do alcance dele |

### Por que o portão de escrita é duro

A alternativa era confiar no texto do prompt para o modelo pedir confirmação antes de gravar.
Promessa de texto não é garantia: um modelo que não pergunta grava, e aí o botão de aplicar vira
decoração.

A regra não é uma lista escrita à mão — ela é derivada de `GUARDAS`
(`app/mcp/guardas.py`): **toda ferramenta que não é somente-leitura está fora**, exceto
`validate_workflow` (que simula e não persiste nada) e `run_workflow` (a exceção deliberada). Uma
ferramenta de escrita nova nasce bloqueada.

E vale em dois lugares, pela mesma razão que o MCP separa `list_tools` de `call_tool`: escondida da
lista que o modelo vê (conforto) **e recusada no despacho** (a garantia — mesmo que o modelo a
nomeie porque leu num exemplo, alucinou, ou alguém mandou no texto de um fluxo compartilhado).

## Superfícies

O laço (`app/services/assistente_service.py`) é um só; o que muda entre o assistente do **editor** e o
assistente da **Home** é um pacote de seis coisas, reunido numa `Superficie`:

| | o que varia |
|---|---|
| `instrucoes` | o bloco de sistema que corrige onde a política do MCP não vale ali |
| `ferramentas_extras` | as ferramentas LOCAIS que abrem a lista do modelo (o desenho no canvas; o globo e as respostas rápidas na Home) — não existem no MCP |
| `executores_locais` | o que essas ferramentas fazem, sem ir ao servidor |
| `permitida` | quais tools do MCP entram na lista |
| `portao` | a checagem antes de despachar ao servidor |
| `quadros_extras` | os quadros SSE que aquela superfície emite depois de uma ferramenta |

**O editor é o `EDITOR`, e é o default de tudo** — `conversar`, `montar_sistema` e
`ferramentas_para_o_modelo` caem nele quando ninguém passa superfície. Então tudo o que este
documento descreve do editor continua valendo byte a byte: o desenho no canvas, o portão de escrita
duro, o quadro `proposta`.

A **Home** (`app/services/assistente_superficie.py`) é a outra superfície. As diferenças são de produto,
não de mecânica:

- **A entrega é uma camada no globo**, não um desenho no canvas — `exibir_no_globo` no lugar de
  `desenhar_no_canvas`, e a resposta chega ao globo sozinha quando uma execução do assistente termina.
  A segunda ferramenta local, `sugerir_respostas`, oferece à pessoa até três continuações curtas
  (os chips sob a resposta) pelo quadro `respostas_rapidas`.
- **Alcance completo** (os seis escopos do PAT, contra os quatro do editor), porque o assistente cria
  e roda os PRÓPRIOS fluxos — marcados `origem="assistente"` pela identidade, escondidos das
  listagens — sem pedir permissão.
- **Confirmação por clique** para o que mexe no que já existia (editar/rodar um fluxo da pessoa,
  agendamentos, apagar arquivo do Drive, publicar, restaurar, ligar/desligar). O portão guarda a ação
  no Redis por 15 min e emite um quadro `confirmacao`; o clique executa os argumentos ARMAZENADOS, no
  servidor — nunca uma promessa de texto, nunca os argumentos que o cliente mandar no clique.

A API que serve a Home (conversas persistidas, o endpoint de confirmação, o globo) é descrita à parte;
esta seção cobre só a fronteira do laço. A outra fronteira — quem fala com o modelo — é o cliente do
OpenRouter, abaixo; um runtime futuro (o Hermes) trocaria uma das duas, nunca o meio.

## Ligar

O assistente é **opcional**. Sem chave ele simplesmente não existe, e o resto do editor continua
inteiro — o comportamento certo para quem roda o Atlans numa instalação própria e não quer a
dependência externa.

```bash
# .env da API
LLM_API_KEY=sk-or-v1-...         # ou OPENROUTER_API_KEY, o nome antigo
#LLM_BASE_URL=                   # vazio = https://openrouter.ai/api/v1; ou um gateway, ou um servidor local
#ASSISTENTE_ATIVO=true           # false/0/off/no desliga mesmo havendo chave
#ASSISTENTE_MODELO=              # o nome no catálogo do provedor; reiniciar basta
#ASSISTENTE_ATRIBUICAO=false     # true: o nome e o FRONTEND_URL vão como atribuição no OpenRouter
```

Fora do OpenRouter, qualquer servidor com a API da OpenAI (`/chat/completions` em stream, com
ferramentas) serve: um gateway como o LiteLLM, ou um servidor local como o Ollama, o vLLM e o
llama.cpp. Exemplo com o Ollama:

```bash
LLM_BASE_URL=http://ollama:11434/v1
LLM_API_KEY=local                # o Ollama não pede chave; qualquer valor não vazio liga o assistente
ASSISTENTE_MODELO=qwen3:14b      # um modelo que saiba chamar ferramentas
```

Fora do OpenRouter, o pedido vai só no formato da API da OpenAI: sem os campos próprios dele
(`reasoning`, `usage.include`, o cache de prompt), que a própria OpenAI recusa, e com
`stream_options.include_usage`, que é como esses servidores mandam a contagem de tokens no stream.
A cota diária depende dessa contagem: um servidor que não a manda deixa a cota sem contar, e o log
da API avisa na primeira resposta assim. Sem preço no catálogo do provedor, a tela de custo do admin
mostra o custo como desconhecido.

A chave é da **plataforma**, não do usuário: quem paga os tokens é a instalação. O teto por pessoa
está abaixo. Se o seu deploy reescreve o `.env` do servidor a partir de uma cópia guardada fora dele
(um segredo do CI, por exemplo), a chave tem de estar **nessa cópia**, e não só editada no servidor.

## O provedor: OpenRouter

O modelo chega pelo [OpenRouter](https://openrouter.ai): um roteador com uma chave e uma API só para
modelos da Anthropic, da OpenAI, do Google e abertos. Trocar de modelo é trocar `ASSISTENTE_MODELO`
pelo nome do catálogo (`fornecedor/modelo`, ex.: `anthropic/claude-opus-5`, `openai/gpt-5`,
`google/gemini-2.5-pro`; a lista viva está em [openrouter.ai/models](https://openrouter.ai/models)) e
reiniciar a API. O padrão é `anthropic/claude-opus-5`.

**Quem fala com ele é um módulo só**, `app/services/openrouter.py`, sobre `httpx` — nenhum SDK de
fornecedor entra na imagem, e um único pool de conexões por processo serve todas as conversas. Ele usa
a API nativa do OpenRouter (`POST /chat/completions`, em stream) e traduz nos dois sentidos:

| | |
|---|---|
| **transcrito** | é do **projeto**, não do provedor: `text`, `thinking`, `tool_use` e `tool_result`, em dicionários puros. É o que o Redis (editor) e o Postgres (Home) guardam, o que o replay lê e o que a confirmação por clique casa pelo `tool_use_id`. Na ida vira `system`/`user`/`assistant` (`tool_calls`)/`tool`; na volta, o stream é remontado nesses blocos |
| **raciocínio** | pedido com `reasoning.effort = high` (o OpenRouter traduz para o que cada família aceita). O texto resumido sai no quadro `pensando`; os `reasoning_details` voltam **verbatim** na volta seguinte, que é o que o modelo precisa para continuar o raciocínio entre chamadas de ferramenta |
| **cache de prompt** | dois pontos de corte: o prefixo estável (ferramentas + sistema) e a última mensagem humana. O OpenRouter repassa aos provedores que têm cache explícito e ignora nos que cacheiam sozinhos |
| **cota** | a contagem vem no último quadro do stream (`usage.include`). `entrada` já inclui o que veio do cache; a cota soma entrada + saída. O custo em créditos (dólares) vai no `fim` e no log da API, como informação |
| **falhas** | rede, 429 e 5xx **antes do corpo** são retentados (3 tentativas); um 400 com raciocínio guardado é refeito uma vez sem ele. Um stream que morre no meio, ou que termina sem `finish_reason` (um 200 de gateway com HTML), é `modelo_indisponivel`, nunca uma resposta pela metade. Uma resposta sem bloco nenhum não entra no transcrito, e uma mensagem do assistente sem texto e sem chamada não vai ao provedor |
| **paradas** | `stop` encerra; `tool_calls` roda as ferramentas; `length` (cortada por `max_tokens`) **não roda ferramenta nenhuma** — o argumento pode ter chegado pela metade; `content_filter` vira `recusado` |

Um bloco `thinking` antigo — de quando o transcrito vinha de outra API e carregava uma `signature`
— continua no banco para o replay e é **omitido** na ida: o que já foi pensado em turnos passados não
é necessário, e reenviá-lo num formato que o provedor não reconhece derrubaria a conversa.

## O painel

Uma gaveta ancorada à direita do canvas, no editor (`/workflow/[id]`) e na tela de criar
(`/workflow/create`). **Não é sobreposição**: o canvas encolhe e os dois ficam visíveis — dá para ver
o fluxo aparecer enquanto se lê a explicação, que é o que impede alguém de aplicar sem entender.

| | |
|---|---|
| abrir/fechar | `Ctrl+I`, ou o botão de estrela no canto do canvas |
| padrão | **aberta** na tela de criar (o canvas nasce vazio), **fechada** no editor de um fluxo pronto |
| largura | 300–560 px, arrastável pela borda; a preferência fica no navegador |
| telefone | vira folha de altura cheia |
| recomeçar | menu `⋯` → *Recomeçar a conversa* (apaga o histórico daquele fluxo, nunca o fluxo) |

Sem `LLM_API_KEY` (ou `OPENROUTER_API_KEY`) na instalação, nada disso aparece — nem a gaveta, nem o botão.

## Cota

### Quando ela estoura, a saída

O aviso de cota cheia (`aviso-de-cota.tsx`) pode carregar a oferta de uma extensão
(`ofertaDaCota`, ver `docs/architecture.md`, Extensões do web). Sem extensão, o aviso fica
sozinho.

O componente é um só de propósito. O texto vivia duplicado em **três** superfícies — a barra
da Home, o painel flutuante da Home e a gaveta do assistente no editor; enquanto era só aviso, a
duplicação custava pouco, mas um botão que existe numa superfície e não na outra é uma venda
que some conforme a tela de onde a pessoa bateu no teto. A casca continua de cada uma (cápsula
na barra, bloco nas outras duas); o conteúdo é do componente.

As cores são **cientes de tema** por causa da terceira: a Home força `dark` nas suas cascas,
mas a gaveta do editor segue o tema de quem olha, e fixar a paleta escura pintaria âmbar-400
sobre fundo claro.

`GET /assistente/editor/estado` e `/assistente/estado` trazem `plano` e `assinaturas_ativas`, que o
registro de extensões preenche (sem extensão: `null` e `false`). O aviso também diz o prazo
**real** de reabertura — o servidor manda `reabre_em_segundos`, o donut logo abaixo já o usava, e
«algumas horas» era a tela sabendo mais do que contava.

A cota é por **token acumulado** numa janela de 24 h, e não por mensagem. O motivo é direto: uma
mensagem que dispara dez chamadas de ferramenta custa dez vezes uma que não dispara nenhuma. Contar
mensagens mediria a coisa errada e daria a mesma cota para o "obrigado!" e para o fluxo de vinte nós.

| | |
|---|---|
| teto | **o da instalação**: `ASSISTENTE_TETO_DE_TOKENS_POR_DIA` (padrão 1 500 000), igual para todos. Quem responde é `teto_do_assistente.plano_e_teto()`, que pergunta ao registro de extensões (`app/extensoes`): numa instalação com uma extensão de planos, o teto é o do plano de cada pessoa, que o admin edita |
| janela | 24 h a partir da primeira conversa |
| onde | Redis, chave `assistente:tokens:{user_id}` |
| consulta | `GET /assistente/editor/estado` devolve gasto, teto, quando reabre e o `plano` que dá aquele teto; durante o turno o stream manda o acumulado a cada resposta do modelo (quadro `cota`), com o MESMO teto — o laço resolve o plano uma vez e o carrega até a cobrança, senão o donut oscilaria no meio da resposta |
| na tela | um donut com o percentual fica SOB o campo de mensagem (barra e painel da Home, gaveta do editor) — `uso-da-cota.tsx`; terracota até 79%, âmbar dali em diante, contagem de reabertura quando estoura; o tooltip traz o detalhe (gasto, teto, percentual, prazo). Sobe durante o turno pelo quadro `cota` e é relido do `/estado` quando o stream fecha |

> **O teto atual é folgado de propósito e ainda não foi medido.** Ele saiu de uma estimativa: as
> definições das ferramentas somavam ~22 KB (~6,9 k tokens, o prefixo estável que o cache guarda) quando eram 38 — hoje são 42 —, e
> o que domina o custo são os **resultados** — o índice do catálogo tem ~10 KB, uma definição inteira
> outro tanto. O número definitivo tem de sair de uma sessão real montando um fluxo de verdade.
>
> **Desde 2026-09-21 a medição existe**: `uso_do_assistente` grava o consumo real de cada volta.

### Dois freios, e um não depende do Redis

A cota diária degrada **aberta** quando o Redis some, como todo o resto do módulo de cotas. Mas
gasto é dinheiro, não carga — por isso existe também um teto de **voltas do laço**
(`TETO_DE_VOLTAS`, contador em memória) que fecha a conversa de qualquer jeito. Um modelo preso num
ciclo de ferramentas é o jeito mais rápido de gastar muito sem ninguém perceber.

## Qual modelo: env como piso, banco por cima

`ASSISTENTE_MODELO` continua sendo o padrão — uma instalação nova sobe funcionando sem
ninguém configurar nada. Existindo uma escolha salva pelo admin (`SystemConfig`, chave
`assistente.modelo`), ela vence. Trocar de modelo é decisão de operação, e exigir deploy
para isso era o que fazia o operador não trocar.

**Não há tabela nova**: `SystemConfig` já é o chaveiro de configuração global, com os
mesmos requisitos — uma linha, lida muito, escrita raramente.

O modelo é resolvido **uma vez por conversa**, junto do teto da cota. Resolver a cada
volta deixaria o admin trocar o modelo no meio de um raciocínio em curso, mudando o
comportamento no meio do caminho; quem já começou termina no modelo em que começou.

`assistente_config_service.modelo_em_uso` nunca devolve vazio: Redis fora, banco fora ou
linha corrompida caem no padrão do ambiente. Ficar sem modelo significaria o assistente
inteiro fora do ar por causa de uma configuração, e o padrão é sempre melhor que nada.
Cache no Redis com TTL de 5 min, invalidado ao salvar — sem a invalidação, a troca
demora até cinco minutos para valer e o admin conclui que o botão está quebrado.

### `/admin/assistente/modelo` — a troca com o custo na frente

Só admin. O `GET` devolve o modelo em uso e o catálogo do provedor
(`openrouter.listar_modelos`, com os preços **já convertidos para dólares por milhão de
tokens**). Uma extensão pode somar campos à resposta, e o `?simular=<id>` chega a ela, para
recalcular o que depende do modelo sem salvar nada.

#### O `PUT` SONDA antes de salvar

**«Está no catálogo» não quer dizer «serve».** O provedor lista algumas centenas de
modelos, e entre eles há variantes que o endpoint de conversa recusa por inteiro (as
`:batch` — «cannot be used with the chat/completions endpoint»), modelos sem suporte a
ferramentas (e o assistente manda as 42 em toda chamada) e modelos cujo teto de saída é
menor que o nosso `MAX_TOKENS`.

Foi assim que o assistente caiu em produção: um id válido, escolhido do catálogo, salvo sem
conferência — e todo usuário passou a ver «não consegui falar com o modelo» enquanto quem
trocou não via nada.

Antes de gravar, `openrouter.sondar_modelo` faz uma chamada real com a **forma** do pedido
de verdade (as mesmas ferramentas, o mesmo `max_tokens`, o mesmo esforço) e conteúdo
mínimo. Filtrar por campos do catálogo seria adivinhar quais campos existem e manter a
adivinhação em dia; uma chamada responde certo sobre todos os casos de uma vez — inclusive
os que ninguém previu, como a variante de batch, que não estava em lista de suspeitos
nenhuma.

Três regras da sonda:

- **A recusa do provedor vira 400 com as palavras dele.** Quem troca lê «cannot be used
  with the chat/completions endpoint» no clique.
- **Só `status` de HTTP bloqueia.** Um stream que abre com 200 e termina sem quadro útil é
  detalhe de transmissão, não configuração — reprovar por isso barraria um modelo que
  funciona.
- **Voltar ao padrão (`modelo: null`) NUNCA é sondado.** É a saída de emergência: se o
  provedor estiver fora do ar com um modelo ruim salvo, sondá-la trancaria a porta na hora
  em que ela é necessária.

**Modelo sem preço conhecido vira `null`, nunca `0`.** Zero lê como «de graça», e é essa
leitura que faria escolher errado.

Provedor fora do ar não derruba a tela: o catálogo vem vazio com o motivo em
`catalogo_indisponivel`, e o admin continua podendo ver o que está em uso e voltar ao
padrão. Responder 500 ali trancaria a única saída.

A tela é a seção **Assistente** em `/dashboard/admin/settings`.

## Quanto custou: `uso_do_assistente`

Uma linha por **volta** do laço, gravada no mesmo ponto em que a cota é cobrada
(`cotas.cobrar_tokens_do_assistente`). Gravar ali, e não no fim da conversa, tem duas
consequências: a cota e o livro de consumo passam a contar a mesma coisa e não podem
divergir, e uma conversa abandonada no meio (aba fechada, stream morto) já deixou
registrado o que gastou até ali — somar só no fim perderia essas, e perderia **para
baixo**, o lado errado de errar num dado que vira decisão de preço.

| Coluna | Para quê |
|---|---|
| `modelo` | gravado, **não deduzido**. No dia da primeira troca de modelo, comparar antes e depois depende disto |
| `entrada` / `saida` | reprecificar com outro modelo — preço de entrada e de saída diferem em várias vezes |
| `cache_leitura` | recorte de `entrada`, informativo: custa ~10 % do preço de entrada mas conta inteiro na cota |
| `custo_usd` | o que o provedor disse que custou. `NUMERIC`, não `FLOAT`: são somas de dinheiro sobre milhares de linhas |

`uso_service.registrar_volta` **nunca levanta** e abre sessão própria (o laço roda
dentro de um gerador SSE e não tem sessão de request). É o mesmo raciocínio da cobrança
de cota: a conversa já aconteceu e já foi paga, e perder a anotação é melhor que jogar
fora o trabalho. Volta sem token nenhum não vira linha — uma linha de zeros puxaria a
mediana para baixo, e é a mediana que decide preço.

**Nenhum conteúdo mora aqui**: contagens, o modelo e o custo. A tabela responde de
quanto foi a conta, não do que se falou.

## A conversa

O histórico fica no **servidor**, não no navegador. Chave por `(usuário, fluxo)`: reabrir o editor
retoma a conversa daquele fluxo; a tela de criar tem a sua. TTL de 24 h.

Isso não é só conveniência. Um `tool_result` é a palavra do **servidor** sobre o que aconteceu; um
cliente que guardasse o transcrito poderia reescrevê-lo e dizer ao modelo o que quisesse — *"a
validação passou"*, *"o usuário é administrador"*. Por isso `POST /assistente/editor/conversa` aceita
**apenas** a mensagem nova, e recusa com 422 qualquer campo a mais.

Uma conversa por vez, por fluxo: duas abas no mesmo fluxo escreveriam no mesmo transcrito e o
embaralhariam. A segunda recebe `conversa_em_andamento`.

## Rotas

| | |
|---|---|
| `POST /assistente/editor/conversa` | `{mensagem, workflow_id?}` → `text/event-stream` |
| `GET /assistente/editor/estado` | `{ativo, motivo?, cota?, plano, assinaturas_ativas}` — o painel consulta antes de aparecer; sem extensão, `plano` é `null` e `assinaturas_ativas` é `false` |
| `DELETE /assistente/editor/conversa?workflow_id=` | esquece o histórico daquele fluxo (204) |

Todas exigem sessão JWT. **Não** aceitam token pessoal: o PAT é para clientes externos, que falam
por `/mcp`.

### Os quadros do SSE

Cada quadro é um `event:` nomeado com um `data:` JSON. O painel assina por tipo.

| `event` | `data` |
|---|---|
| `pensando` | `{texto}` — o raciocínio resumido do modelo |
| `texto` | `{texto}` — o que ele está escrevendo |
| `ferramenta` | `{id, nome, argumentos}` — **argumentos resumidos**: chaves e tamanhos, nunca o conteúdo |
| `progresso` | `{concluidos, total, mensagem, id?}` — o andamento nó a nó de uma execução; `id` é o `tool_use_id` da chamada dona (as ferramentas de uma volta rodam em paralelo — sem ele, o quadro pinta o card errado; ausente só em conversas gravadas antes do campo) |
| `cota` | `{gasto, teto}` — o acumulado da janela depois de cada resposta do modelo; só com Redis; não é bloco da conversa nem entra no replay |
| `ferramenta_fim` | `{id, nome, erro}` |
| `proposta` | `{definicao, nos, arestas, ok, erros, avisos}` — a definição validada, **inteira** |
| `erro` | `{code, message, hint?}` |
| `fim` | `{transcrito, uso, voltas, ok}` — **sempre o último**, mesmo quando deu errado |

O `fim` é sempre o último quadro de propósito: é ele que carrega o transcrito, e perder a conversa
porque o modelo tropeçou na oitava volta faria a pessoa recomeçar do zero. Quando houve falha, um
`erro` vem antes e o `fim` traz `ok: false`.

Fechar a aba no meio da resposta **não** perde a conversa: o gerador grava o transcrito num
`finally` blindado por `asyncio.shield`, para o cancelamento da desconexão não abortar a gravação a
meio caminho. E um turno longo não morre calado no proxy: o SSE do editor passa pelo mesmo batimento
(`: ping` a cada 15 s de silêncio, `app/api/routers/_streaming.py`) que o assistente da Home. A cota
já está protegida sem isso — ela é cobrada depois de cada chamada ao modelo, dentro do laço.

### O quadro `proposta`, e por que ele é a exceção

Todo quadro `ferramenta` leva os argumentos **resumidos** — chaves e tamanhos, nunca conteúdo. O
`proposta` é a única exceção, e ela é estreita de propósito: leva a definição INTEIRA, só de
`validate_workflow`, e só quando a ferramenta não falhou.

O motivo é direto. O assistente não grava; quem leva o fluxo ao canvas é o botão **Aplicar**. Com o
resumo, `definition` chegaria ao painel como `{"__campos__": 2}` — e o botão não teria o que aplicar.

A definição sai do **argumento**, e não do resultado: é o que o modelo pediu para validar, é o que o
servidor validou, e é exatamente o que será aplicado. Ler do resultado abriria espaço para os dois
divergirem.

`ok`, `erros` e `avisos` vêm do relatório da validação. `ok: null` significa que o relatório não pôde
ser lido — **não** significa que passou, e o painel desliga o Aplicar nesse caso.

### O Aplicar

O botão é local: ele monta o canvas a partir da definição e não chama rota nenhuma. Gravar continua
sendo o **Salvar** do editor, como em qualquer outra edição.

Aplicar **substitui** o canvas, mas **preserva a posição** de todo nó cujo `id` sobreviveu. Isso não é
detalhe: a definição do assistente não tem posição, e sem a preservação um fluxo de doze nós arrumado à
mão viraria uma fila horizontal. Os nós novos entram pelo mesmo auto-layout do botão de organizar, e
descem se caírem em cima de um card que já estava lá.

Antes do clique, o cartão mostra o que vai acontecer — `n novos · n alterados · n removidos` — porque
aplicar num canvas cheio é destrutivo. `Ctrl+Z` desfaz.

### Consumir no navegador

**Não é `EventSource`**: ele é GET, não manda cabeçalho, e a conversa precisa de corpo e de
`Authorization`. Use `fetch` e leia `response.body`:

```ts
const r = await fetch("/assistente/editor/conversa", {
  method: "POST",
  headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
  body: JSON.stringify({ mensagem, workflow_id }),
})
const leitor = r.body!.getReader()
// …decodificar os quadros `event:`/`data:` e despachar por tipo
```

Um quadro pode chegar **partido ao meio** entre dois `read()` — a rede não respeita fronteira de
mensagem. O decodificador precisa guardar o resto; o da web está em
`web/app/components/home/assistente/quadros.ts`, com esse caso coberto por teste.

Dentro da própria aplicação web o `Authorization` **não** é mandado: a chamada passa pelo proxy
`/terra`, que autentica a API com o token do servidor e ignora o header do cliente. O exemplo acima é
para quem fala direto com a API.

## Segurança

- **O assistente não ganha nada que você não tinha.** O escopo é o da sua sessão, com dois escopos a
  MENOS que um token pessoal completo (`triggers:manage` e `drive:write` ficam fora), e o portão
  acima tira todas as ferramentas de escrita menos `run_workflow`. A autorização é a mesma do MCP,
  pelo mesmo `call_tool` — não há uma segunda regra para divergir.
- **Texto de fluxo é dado, não instrução.** Nome de fluxo, nome de arquivo do Drive e mensagem de
  erro são escritos por pessoas do workspace, e num workspace compartilhado isso inclui terceiros. O
  MCP já os embrulha em `untrusted_data`, e o system prompt do assistente diz em voz alta que aquilo
  não se obedece.
- **Execução é real.** `run_workflow` dispara nós que escrevem em banco e publicam mapa. O assistente
  pede aval em texto e só executa no turno seguinte.
- **O argumento da chamada não vai inteiro para o SSE.** O quadro `ferramenta` leva chaves e
  tamanhos; a definição do fluxo e o texto de quem está usando ficam fora, porque o stream é log de
  alguém em algum momento.

## Limites conhecidos

- **Sessão longa acaba.** No teto de voltas a conversa termina com um aviso, em vez de continuar
  gastando. Compactação de contexto fica registrada como próximo passo.
- **Sem Redis a conversa não tem memória**: cada mensagem começa do zero, e a cota degrada aberta.
  É a mesma política do resto da plataforma — a API nem sobe sem Redis, então isso é um incidente de
  segundos, não um modo de operação.
- **Raster continua fora** do motor de fluxos, e o guia diz isso ao modelo.
- **A trava da conversa (Redis, 300 s) se renova** enquanto o turno corre, para não vencer no meio de
  uma conversa longa e deixar uma segunda aba entrar no mesmo transcrito; e a chave da cota diária
  ganha o prazo na mesma transação do `INCRBY` (`contar_na_janela`, em `app/core/redis.py`), para o
  teto nunca ficar imortal e travar o assistente para sempre — o mesmo contador das cotas do MCP e do
  rate limit do WebSocket.
