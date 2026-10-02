# Assistente da Home — conversas sobre o globo

O assistente da Home é o assistente de **outra superfície**. O laço é o mesmo
(`app/services/assistente_service.py`), a autorização é a mesma (as tools do MCP,
pelo mesmo `call_tool`), a cota de tokens é a mesma (`assistente:tokens:{user}`).
O que muda é o pacote da superfície `HOME` (`app/services/assistente_superficie.py`)
e o fato de a conversa ser **persistida no banco** — veja "Superfícies" em
`docs/editor-assistant.md` para a fronteira do laço.

Este documento é a **API** (`/assistente`): as rotas, os quadros do SSE, a
confirmação por clique e a persistência.

## A página (a Home, `/`)

O assistente vive na **Home** — a rota `/`, a landing de todo mundo (ela abre
**sem login**; a entrada é pedida no primeiro envio — ver "A Home sem sessão"). É
um **globo 3D** em tela cheia (MapLibre GL, projeção `globe`, sobre a imagem
híbrida do Google) que recebe as geometrias de saída das execuções; a conversa flutua
sobre ele. A casca é "como o Claude Code": um `HomeSidebar` só, com a marca no
topo, **Nova conversa**, e o grupo **Meus → Agendamentos, Artefatos, Chats**; o
rodapé é o `UserSidebar` de sempre (Tema, Configurações, Sair — sem
atalho de navegação); sem sessão, o rodapé vira **Entrar** e **Criar conta**. A
Home é **sempre escura** (paleta quase preta `.home` em `globals.css`),
independente do tema do app.

**Quem não administra o sistema não alcança outra página além da Home.** É a
direção do produto — a Home é a ÚNICA página de quem não é admin, migrando o resto
aos poucos. Hoje isso é controle de acesso, não só oferta: o
middleware (`web/proxy.ts`) devolve `/` para qualquer página fora dela
(`/projects`, `/workflow/…`, `/drive`, `/settings/tokens`, `/admin`,
`/dashboard`…) quando o papel não é admin — o proxy `/terra`, do qual a Home
vive, e os arquivos do `public/` ficam fora do portão; sessão sem papel falha
fechada. Antes disso, as saídas da própria Home já tinham sido fechadas, nesta
ordem:

| saída | estado |
|---|---|
| Marca do sidebar → `/projects` | só admin. Sem `href`, o `Marca` vira `<span>`: some o destino **e** o realce de hover que dizia "isto é clicável" |
| Linha de Agendamentos → `/workflow/{id}` | fechada. A linha é `<div>`: um `<button>` sem ação prometeria um clique que não acontece |
| **Paleta Ctrl+K** | **não abre em `/` para quem não é admin** (`paletaDisponivel`) |
| **Badge do fluxo → `/workflow/{id}`** | **substituído**: a faixa passou a mostrar os ARTEFATOS da conversa, e clicar põe no globo |
| Menu de conta → `/settings/tokens` | **fechada**: o item "Tokens de acesso" saiu do menu; e a rota, como toda página fora de `/`, devolve `/` a quem não é admin (o admin chega pela paleta Ctrl+K ou pela URL) |
| `signOut` | aberta — a única saída do app |

**As saídas da tabela eram OFERTA; o controle de acesso é o middleware** — que
devolve `/` a quem não é admin fora da Home (desde o #155) e, sem sessão, só
deixa a Home abrir: qualquer outra página vai para a Home com o modal de entrada
(ver "A Home sem sessão e o modal de entrada", no fim desta seção).

Duas notas sobre as duas últimas:

- **A paleta não abre, em vez de filtrar item a item**, porque HOJE todo item
  dela sai da Home: os oito estáticos não-admin levam a outras rotas, e os
  dinâmicos são um por fluxo (`/workflow/{id}`) e um por credencial — estes nem
  passavam pela `itensVisiveis`. Filtrar deixaria uma caixa vazia. De brinde, o
  `loadItems` não roda: some o `getWorkflows()` que disparava a cada Ctrl+K na
  Home. Fora de `/`, e para admin, nada muda.
- **A faixa de badges supera a decisão 4** ("o usuário nunca vê o fluxo, a não
  ser que clique no badge"): o fluxo deixa de ser alcançável pela Home. Ele
  continua em Projetos, com o interruptor "mostrar os do assistente" ligado,
  para quem chegar lá. O quadro `fluxo` segue sendo emitido e decodificado — o
  que some é a oferta.

- **A rota** mora em `web/app/(dashboard)/page.tsx` (o grupo não contribui
  segmento). O layout `(dashboard)` é compartilhado; um `ShellSidebar` (client,
  `usePathname`) escolhe `HomeSidebar` em `/` e `AppSidebar` nas demais rotas. O
  `AppHeader` retorna `null` em `/`, como no canvas.
- **O grupo Meus do `HomeSidebar`** (Agendamentos, Artefatos, Chats) são três
  itens colapsáveis com a MESMA linha (`home/linha.tsx`: `LinhaDoMeu` +
  `GatilhoDeAcoes`): o texto principal é `min-w-0 flex-1` e trunca com
  reticências e `title`; o "⋯" é irmão no flex, nunca sobre o texto — no
  telefone o alvo de 40px só empurra o título. O aberto/fechado dos três é
  lembrado no navegador (`atlans:home:meu`, lido em `hidratar()`), então
  sobrevive à gaveta do telefone, à troca de rota e ao redimensionar; só Chats
  nasce aberto. Fechar um item ESCONDE a lista (`hidden`), não a desmonta —
  reabrir não refaz requisições nem perde o "Ver mais" —, e a lista só monta
  depois de hidratar (no telefone o primeiro render ainda é o ramo desktop, e
  montar ali disparava um GET perdido). No **trilho de 3rem** (Ctrl+B, o
  gatilho ou a borda arrastável, o `SidebarRail`), clicar um item expande a
  barra E o abre — nunca alterna um estado invisível; a marca fica como glifo
  (para o admin, ainda o link para Projetos, com tooltip) e só o wordmark some.
- **Portais na paleta da Home.** Todo `*Content` do Radix aberto a partir da
  Home (os menus "⋯", tooltips, `RenomearDialog`, `DeleteDialog`,
  `MetadataDialog`, `ExecuteParamsDialog`, o menu de conta e as Preferências)
  vai ao `<body>`, fora da árvore `.home dark`, e por isso leva `home-portal`
  (globals.css). Os componentes compartilhados ganharam `className` /
  `portalClassName` opcionais para isso; fora da Home, nada muda.
- **O basemap é a imagem híbrida da instalação** (satélite + vias e rótulos,
  `MAPA_HIBRIDO_URL`; sem ela, o satélite `MAPA_SATELITE_URL` e, sem este, as
  ruas do OpenStreetMap — `web/lib/fundos-do-mapa.ts`), a mesma que o portal
  `/share` oferece no alternador dele. Não há estado "sem basemap". É o **único**
  basemap da Home (o Dark Matter da CARTO, que exigia chave gratuita, saiu),
  então a Home **não tem alternador**: o `Globo` monta o `MapLibreMap` com
  `basemapInicial="hybrid"` e `basemapToggle={false}`. Raster na esfera deforma
  um pouco ao mudar de zoom (o MapLibre recomenda vetorial para o globo); com a
  imagem como basemap único isso é permanente e aceito.
- **A atribuição nunca é escrita por nós.** Todo basemap que usamos já declara a
  própria na fonte (`MAPA_*_CREDITO`; "© OpenStreetMap contributors" nas ruas padrão).
  Passar um `customAttribution` por cima **não substituía** a da fonte — o
  MapLibre concatena os dois com `" | "`, e a Home mostrava a mesma coisa duas
  vezes.
- **A chrome do mapa é discreta** (`controlesDiscretos`): zoom, bússola e escala
  vestem um vidro translúcido em vez da caixa branca sólida do MapLibre; o
  ícone fica em 0,65 de opacidade e sobe a 1 no hover/foco (no toque o piso é
  mais alto, porque não há hover para revelar). A atribuição entra em modo
  `compact`: vira um **"ⓘ" que abre no clique**. Ela fica discreta, nunca some —
  os termos dos provedores (e a ODbL do OSM) a exigem, e um clique é a
  forma que o próprio MapLibre oferece para isso. O portal segue no padrão do
  MapLibre.
- **Os Chats** são a lista de conversas (`GET /assistente/conversas`): renomear
  (`PATCH`) e apagar (`DELETE`, soft) pelo menu ⋯ de cada linha. Clicar num chat
  abre o painel com o **replay** daquela conversa. A lista **espelha o servidor
  sem F5**: o 1º quadro `conversa` de cada mensagem (id, título, `nova`) e a
  confirmação aceita viram um anúncio na store (`anuncioDeConversa` — um slot,
  não uma fila: a lista pode estar desmontada) que a `ChatsLista` aplica sem
  GET (`useConversas.anunciar`): a conversa nova entra no topo com o título, a
  existente sobe; renomear também sobe (o servidor carimba `updated_at` no
  PATCH). Apagar a conversa **ativa** deixa a Home como o botão "Nova conversa"
  (o stream em curso para; painel e pilha esvaziam; a mensagem seguinte cria
  outra, em vez de bater num 404). No rodapé, "Ver mais" pede a página
  seguinte e "Tentar de novo" refaz **o que falhou** (a página, ou a recarga);
  a recarga relê todas as páginas já na tela, em paralelo e tudo-ou-nada,
  porque o servidor apara `limit` em 100 em silêncio.
- **Meus → Agendamentos** (`GET /me/schedules`, `useAgendamentos`): os agendamentos
  da pessoa entre TODOS os workspaces, ativos e pausados (o pausado mostra o
  `motivoPausa` de `resumirAgendamento`). O menu ⋯
  — só para operator+ NAQUELE workspace (`hasMinRole` por item, pois a lista cruza
  vários) — traz pausar/ativar (`PUT /workflows/{id}/schedules/{job}`, otimista) e
  rodar agora (busca `params_schema`, abre o `ExecuteParamsDialog` se houver). A
  linha NÃO abre mais o fluxo no editor (é uma das saídas fechadas): por isso é
  `<div>` e não `<button>` — um botão sem ação prometeria um clique que não
  acontece. O fluxo do assistente leva um selo. Religar não dispara na hora (o
  `schedule_service` zera `next_run_at`).
- **Meus → Artefatos** (`useAcervo`): o acervo do workspace atual — artefatos de
  execução (`GET /artifacts`) e arquivos do Drive (`GET /drive`) na MESMA lista,
  unidos por `Promise.allSettled` (a falha de uma fonte não derruba a outra),
  distinguidos só por ícone e pelo estado **permanente / efêmero / local no
  executor** (cor neutra no formato; `LocalBadge`/`RetencaoHint` no estado). O
  painel **não troca de workspace**: segue o `current` do `WorkspaceContext` (o
  padrão da pessoa, ou o último usado). O `WorkspaceSwitcher` que vivia no topo
  saiu por decisão de produto e volta depois, em outro lugar da casca — como o
  `AppHeader` também não aparece em `/`, hoje a Home inteira opera num escopo só.
  Clicar num artefato geojson/publicado o põe no globo (a lista enfileira o pedido na store; o
  HomeView o drena para `useCamadas.adicionar`); arquivo do Drive não vai ao globo
  na v1 — abre os metadados. O menu ⋯: exibir no globo, baixar, metadados, excluir
  (excluir por editor+). Acima de 150 itens a lista vira virtual
  (`@tanstack/react-virtual`).
- **A conversa ao centro, e o painel sob demanda.** Todo acesso começa no
  **hero**: o globo velado rumo ao sul, a chamada ("Menos ferramentas. **Mais
  respostas.**" / "Pergunte em português. O Atlans escolhe os dados e monta cada
  etapa — você recebe o resultado.") e a barra de comando grande ao centro,
  com sugestões digitadas e chips. A chamada existe para dizer que **escolher a
  operação não é trabalho de quem pergunta** — por isso o placeholder da barra e
  o convite do painel são a mesma pergunta ("O que você quer saber?"), e não um
  pedido de comando; mudar um deles sozinho reabre a contradição que o
  comentário de `Primeira()` em `painel.tsx` registra. **Assim que a pessoa
  ENVIA** a barra escorrega para o rodapé e a última troca aparece acima dela, na
  **faixa** (`assistente/pilha.tsx`): a legenda do globo, colada à barra — a
  pergunta numa linha e, da resposta, só o último texto (cortado em 4 linhas),
  os erros, os cartões, as respostas rápidas e o passo em curso; o resto fica no
  painel. O gatilho é o ENVIO (`agente.correndo`), não o primeiro token de
  TEXTO: com o assistente consultando o catálogo e o WFS (várias ferramentas)
  antes de escrever, esperar o texto deixava a barra travada no centro por
  segundos, sem carregar o diálogo (relato de uso). Enquanto o assistente
  pensa, o item pendente (faixa e painel) mostra a **marca animada** do site
  (`assistente/marca-animada.tsx`: três nós, sem o fundo laranja; parada e
  inteira sob `prefers-reduced-motion`), **e a barra do rodapé mostra o PASSO da
  vez** (`assistente/etapa.tsx`): "Pensando…", ou a ferramenta em curso com o
  rótulo do painel («Consultando o guia · edges»); some quando a resposta começa
  a ser escrita, porque aí ela já aparece na faixa. Os movimentos
  são poucos e curtos — o flash ao enviar, o cursor no parágrafo que está sendo
  escrito, o pop do cartão de camada, a faixa deslizando para a lateral ao
  expandir e o painel entrando da direita — e todos zeram sob
  `prefers-reduced-motion`. **Expandir**,
  o chevron ou Ctrl+I levam a
  conversa inteira ao painel flutuante (`assistente/painel.tsx`, fork da gaveta
  do editor); "Recolher" volta ao centro. As decisões estão em
  `docs/home-refactor.md`. `useAgente` (fork de `useAssistente`) consome os SSE de
  `/assistente`: `enviar` (`POST /conversa`), `confirmar` (`POST /confirmacoes`, o 2º
  stream do clique) e `carregar` (o replay). Os quadros novos (`fluxo`/`camada`/
  `confirmacao`) são aditivos em `web/app/components/home/assistente/quadros.ts` — o editor os ignora.
- **A entrega chega ao globo**: cada quadro `camada` vira uma busca em
  `GET /assistente/camadas/{id}` (`useCamadas`) e uma `MapLayer` — GeoJSON pela URL
  pré-assinada (em memória; teto de 25 MB) ou tiles MVT de uma camada publicada.
  O mesmo artefato aparece em TRÊS recortes, que não se duplicam: o
  `CartaoCamada` inline é o momento "entrou no globo" e **rola** com a conversa;
  a **faixa de badges**, entre o cabeçalho e o rolo, é o índice fixo do que a
  conversa toda produziu, e clicar um põe no globo (pela fila do `homeStore`,
  igual à lista de Artefatos); o **painel de camadas** (canto do globo) é o que
  está no globo AGORA, com olho, enquadrar, **baixar** e remover. Os fluxos que o
  assistente criou não aparecem em lugar nenhum da Home.
- **Baixar do próprio painel de camadas**, sem ir procurar o mesmo arquivo na
  lista de Artefatos. O ícone aparece ao passar o mouse na linha (onde HÁ mouse:
  no toque é permanente, e o foco do teclado sempre o revela), e **só quando o
  servidor disse que há arquivo** — `CamadaDoGlobo.baixavel`, que é diferente de
  `available`: uma camada publicada aparece no globo com o conteúdo no PostGIS e
  pode não ter arquivo no storage, e um artefato marcado `keepLocal` nunca sai do
  executor. Nos dois o download responderia 409/404, e botão vivo que falha é
  pior que botão ausente. Quem baixa é `lib/baixar-artefato`, um caminho só para
  as três telas que precisam dele.

### A barra lateral

- **A borda redimensiona.** Ela sempre mostrou `cursor-w-resize` e só sabia
  **recolher** — quem arrastava para ler o nome inteiro de um artefato via a
  barra fechar na cara. Agora, expandida, ela é um separador
  (`role="separator"`, o padrão WAI-ARIA de janela): arrastar redimensiona entre
  180 e 480 px, ←/→ ajustam pelo teclado (com Shift, em passos maiores),
  Home/End vão aos limites e o duplo clique volta aos 256 px. **Recolhida** ela
  continua o botão que expande, que é o único caminho de volta do trilho de 3rem
  por ali; recolher segue no `SidebarTrigger` do cabeçalho e no Ctrl/Cmd+B.
- **A largura sobrevive ao F5**, no mesmo molde do recolhido: um cookie
  (`sidebar_width`) que o layout lê **no servidor** e devolve como
  `defaultWidth`. Em `localStorage` a barra nasceria com 16 rem e saltaria no
  primeiro efeito. O valor é saneado no provider, então cookie adulterado não
  estica nada.
- **O nome do artefato é cortado NO MEIO**, não no fim (`NomeDeArquivo`).
  `truncate` comia justamente a versão e a extensão: numa lista de `…_v1`,
  `…_v2`, `…_v3` todas as linhas viravam o mesmo prefixo. O corte encosta no
  separador (`_`, `-`, `.`) mais próximo para não partir palavra no meio, e o
  `data-nome` carrega o nome íntegro para quem precisa dele como um valor só.
  Vale para NOME DE ARQUIVO; título de conversa é prosa, e ali o corte no fim
  continua certo.

### A Home sem sessão e o modal de entrada

A Home **abre sem login**: globo, hero (título, frase, a barra com as sugestões
digitadas e os chips) — tudo à vista, e **nenhuma requisição** sai (o `useAgente`
não consulta o `/assistente/estado` quando `anonimo`; o sidebar não monta o grupo
Meu; o `WorkspaceContext` e o `ActiveRunsContext` já ficavam parados sem
sessão). O sidebar anônimo mostra a marca, o gatilho de recolher, a **vitrine do
catálogo** e, no rodapé, **Entrar** e **Criar conta**.

- **A vitrine** (`VitrineDoCatalogo`, em `home-sidebar.tsx`) ocupa o corpo que
  antes era o convite "Entre para ver seus chats, artefatos e agendamentos.": o
  tamanho do catálogo (25.492 camadas, 76 instituições, 11 países) e três fitas
  deslizantes de siglas — duas do Brasil e uma dos países, sob os rótulos
  BRASIL e FORA DO BRASIL. A troca é de argumento: prova verificável no lugar de
  uma promessa de recurso, e o vocabulário de quem já procurou um WFS na mão no
  lugar de três palavras que quem chega não conhece.
  Os números e os nomes são CONSTANTES em `web/lib/catalogo.ts` — a casca
  anônima não faz requisição —, presos à semente de `catalogo/geoservicos/` por
  `tests/unit/test_vitrine_do_catalogo.py`, que recalcula tudo e falha dizendo o
  número novo. As fitas param inteiras em `prefers-reduced-motion`
  (`.home-fita`, em globals.css), e o grupo some no trilho de 3rem.

- **O primeiro envio pede a entrada.** Enter, "Enviar" ou um chip + Enter abrem
  o **modal de entrada** (`web/app/components/home/entrada/`) sobre o globo, no
  tema da Home (`home-portal`) e com o fundo levemente ofuscado; a mensagem fica
  **pendente** (`homeStore.envioPendente`) e o texto continua na barra. O modal é
  **fechável** (Esc, X, clique fora — não durante um envio): fechar sem entrar
  desiste do envio, e o texto fica na barra.
- **O login bem-sucedido não navega**: o `signIn` do next-auth (sem redirect)
  grava o cookie e atualiza o `useSession` da aba; a Home consulta o `/estado` e
  **manda a mensagem pendente sozinha** (respeitando a cota estourada, como a
  barra). Com `callbackUrl` (o admin que pediu `/projects` sem sessão) a pessoa
  vai para lá, sem enviar nada.
- **O cadastro** é um painel do mesmo modal; criada a conta, o modal troca para
  "Verifique seu e-mail" (com o reenvio do link) — a conta exige verificar o
  e-mail antes do primeiro login, e a mensagem fica esperando na barra.
- **A verificação do e-mail é do mesmo painel**, `verificar`. Sem token ele é a
  tela de "abra o link do e-mail", com o reenvio
  (`POST /auth/resend-verification`); **com** o token do link ele o gasta no
  `GET /auth/verify-email`, ativa a conta e volta ao login já com o aviso. O
  token vale UMA vez por modal (ele continua na URL depois de gasto): voltar ao
  painel — pelo 403 do login, ou pelo "Reenviar" de uma falha — dá a tela do
  reenvio, não um segundo GET com um link que já não vale. O "Reenviar e-mail de
  verificação" do erro 403 é um BOTÃO, e leva o que foi digitado quando aquilo
  já é um e-mail (o campo aceita e-mail OU usuário).
- **O caminho da senha também é do modal**, nos painéis `recuperar` ("Esqueceu
  a senha?", `POST /auth/forgot-password`) e `redefinir` ("Nova senha",
  `POST /auth/reset-password` com o token do e-mail). O "Esqueceu a senha?" do
  login é um BOTÃO que troca de painel, não um link: navegar levaria para fora
  da Home e jogaria fora a mensagem pendente. O sucesso do pedido é mostrado
  mesmo quando o servidor recusa — dizer "este e-mail não existe" entregaria
  quem tem conta aqui, e o backend já responde igual nos dois casos.
- **Os painéis do e-mail** (`verificar`, `recuperar`, `redefinir`) **abrem COM
  ou SEM sessão**, ao contrário de `entrar` e `cadastro`: quem esqueceu a senha
  — ou ainda não verificou o e-mail — costuma ter uma sessão velha no mesmo
  navegador, e o link chega nele; com o portão de `anonimo` valendo para todos,
  esse link abria a Home e não fazia nada. Pelo mesmo motivo a sessão que chega
  no meio não os fecha: o token é de uso único. A regra é uma só, em
  `ehPainelDeEmail` (`web/lib/entrada.ts`).
- **As rotas.** `/login`, `/register`, `/verify-email`, `/forgot-password` e
  `/reset-password` viraram redirecionamentos para `/?entrar=1`, `/?cadastro=1`,
  `/?verificar=1&token=…`, `/?recuperar=1` e `/?redefinir=1&token=…`
  (`web/lib/entrada.ts`; só um `callbackUrl` interno passa). As três últimas
  ficam de pé porque é o que está escrito nos e-mails **já enviados**; sem token,
  `/reset-password` cai no painel que pede um link novo e `/verify-email` na
  tela do reenvio. **Nenhuma tela deste fluxo é mais uma página**: com a
  verificação foi embora a última `AuthShell`, e a casca saiu do código. O middleware manda para a entrada
  quem pede uma página sem sessão ou com a sessão vencida. Em `/` o middleware
  **nunca redireciona** — nem com a sessão vencida, que o `SessionSync` limpa no
  cliente (redirecioná-la para um destino dentro do matcher seria um laço);
  nesse instante a Home e o sidebar a tratam como anônima. Sair cai na Home
  anônima.

## O que ele faz de diferente do editor

- **A entrega é uma camada no globo**, não um desenho no canvas. O assistente
  cria e roda os PRÓPRIOS fluxos (marcados `origem="assistente"` pela
  identidade) SEM clique — é assim que a resposta chega ao globo — e põe uma
  saída de execução no globo com `exibir_no_globo`.
- **Os fluxos dele aparecem no painel inteiro, com selo.** Projetos, Dashboard,
  Histórico, paleta (⌘K) e o seletor de sub-fluxo do editor listam os fluxos do
  assistente ao lado dos demais, sempre com o selo da faísca
  (`shared/selo-assistente.tsx`) — antes eles só apareciam nos Agendamentos da
  Home e passavam despercebidos. O recorte "só os do assistente" é um chip nas
  duas telas de lista: `/projects?filtro=assistente` (predicado local) e
  `/observability?assistente=1` (que vira `workflow_origem=assistente` em
  `GET /observability/runs`, e um filtro local na visão "Por workflow"). O
  padrão de `GET /workflows` continua ESCONDENDO-OS: quem quer inclui
  `assistente=1` — é o que essas telas passaram a fazer.
- **Respostas rápidas.** Ao terminar uma resposta que abre continuação natural,
  o assistente chama `sugerir_respostas` (a segunda ferramenta local; até três
  frases curtas, como a pessoa as diria) e elas aparecem como chips sob a
  resposta, na faixa e no painel; o clique manda a frase como a próxima
  mensagem, e o turno novo tira os chips da tela.
- **Alcance completo, com confirmação por clique.** Ele tem os seis escopos do
  PAT (`escopo_do_assistente`). O que segura o destrutivo não é a ausência de
  escopo: é o **portão de confirmação verificado no servidor**. Editar/rodar um
  fluxo que a pessoa criou, mexer em agendamento, apagar arquivo do Drive,
  publicar, restaurar, ligar/desligar — tudo isso pede um clique.
- **Conversas persistidas**, várias por pessoa, sem prazo (as tabelas
  `conversas` e `mensagens`), no lugar do transcrito no Redis com TTL de 24 h do
  editor.
- **Catálogo antes de prospectar.** Para dado externo (WFS) o roteiro manda
  chamar `search_sources` e `describe_source` ANTES de qualquer outra coisa — a
  fonte vem pré-mapeada do catálogo (`docs/sources.md`), sem rede e sem chute de
  `url`/`typeName`. Só quando o catálogo não tem a fonte ele sonda
  (`probe_source`) e registra (`register_source`) — as duas passam SEM clique
  (`ESCRITAS_SEM_CLIQUE`): sondar e guardar uma fonte é a via normal de trabalho,
  não uma ação destrutiva.

## Arrastar arquivos para o Drive

A tela `/drive` tem a zona de envio desde sempre, mas o middleware devolve `/`
para quem não administra o sistema (`web/proxy.ts`) — então, na prática, o
usuário comum nunca alcançou um campo de upload. A Home é a única página dele, e
a regra da casa manda todo fluxo visual para dentro dela.

**O gesto.** Arrastar um ou mais arquivos para qualquer canto da Home acende a
**caixa do assistente** (o alvo visual), e soltar os leva ao Drive do workspace
ativo. A área que ACEITA é a janela inteira (`useArrasteDeArquivos`, um listener
global); só o realce é da caixa — nenhum véu cobre o globo. Os arquivos viram
**chips na caixa** (`anexos.tsx`): um spinner enquanto sobem, um ✓ quando chegam.

**A mensagem leva o que subiu.** Enviar uma pergunta com anexos prontos acrescenta
ao texto a linha «Arquivos que acabei de enviar ao Drive deste workspace: …»
(`comReferencia`) — sem ela, «analise isso» chega ao assistente sem nenhum «isso»
(ele enxerga o workspace por `list_drive_files`, mas não sabe QUAIS arquivos são
os desta pergunta). Só os PRONTOS são citados e só eles saem da caixa ao enviar;
o que ainda sobe fica (não estava na mensagem) e o recusado também (nunca teve
relação com ela). Com anexo pronto, a caixa passa a sugerir «Analise <arquivo>»
no lugar das frases do hero.

**Os filtros são os do backend, e não são reescritos.** Extensão permitida,
extensão interna perigosa (`notas.sh.csv`), teto em MB e arquivo vazio vivem
todos em `drive_service.py`/`drive_router.py`, valem para qualquer caminho de
upload e este caminho manda ao mesmo `POST /drive/upload`. A recusa é traduzida
com a MESMA `classifyUploadError` da tela `/drive` e mostrada no MESMO painel
(`ResultadoDoUpload`), num aviso à parte dos chips — o recusado não entra na
mensagem, e deixá-lo na fileira faria a pessoa mandar a pergunta achando que ele
foi. A única checagem feita ANTES de subir é o papel no workspace
(`useWorkspace().canEdit`, o espelho do papel `editor` que o Drive exige): subir um
arquivo inteiro para colher um 403 previsível é desperdício de rede. Sem sessão,
soltar abre o modal de entrada — a mesma porta do primeiro envio.

**Estado na store, não no componente.** Os anexos e o `arrastando` vivem no
`homeStore`, pelo mesmo motivo do rascunho: Ctrl+I troca a barra pelo painel e
DESMONTA quem estava na tela — num `useState` da caixa, os chips sumiriam no
atalho com os uploads ainda correndo. Por isso a barra E o painel montam as
mesmas peças (o achado 4 da 3ª revisão: um recurso numa superfície e não na
outra é uma venda que some conforme a tela).

## Rotas

Todas exigem sessão JWT (o PAT é para clientes externos, que falam por `/mcp`).

| | |
|---|---|
| `POST /assistente/conversa` | `{mensagem, conversa_id?, workspace_id?}` → `text/event-stream`. `conversa_id` nulo cria uma conversa nova; o 1º quadro devolve id, título e `nova` |
| `POST /assistente/conversas/{id}/confirmacoes/{tool_use_id}` | `{token, decisao}` → `text/event-stream`. Executa (ou recusa) uma ação e RETOMA a conversa no mesmo stream |
| `GET /assistente/conversas?limit&offset` | as minhas conversas não apagadas, mais recentemente ativas em cima (`updated_at`, carimbado ao fim de cada turno e no renomear). `limit` é aparado em **100 sem aviso**; `offset` é livre |
| `GET /assistente/conversas/{id}` | o **replay** da conversa, em quadros (para o painel reaplicar) |
| `PATCH /assistente/conversas/{id}` | `{titulo}` — renomear |
| `DELETE /assistente/conversas/{id}` | soft delete (204): some da lista, o histórico fica |
| `GET /assistente/estado` | `{ativo, motivo?, cota?, plano, assinaturas_ativas}` — a cota é a MESMA do editor; sem extensão, `plano` é `null` e `assinaturas_ativas` é `false` |

`GET /assistente/camadas/{id}` e `GET /assistente/tiles/…` (as camadas do globo) moram no
`assistente_camadas_router` e têm portão de MEMBRO — não são conversa.

## Os quadros do SSE

O vocabulário do editor mais quatro: `conversa` (o primeiro, sempre), `fluxo`,
`camada` e `respostas_rapidas`. Os do editor (`pensando`, `texto`, `cota`, `ferramenta`,
`progresso`, `ferramenta_fim`, `erro`, `fim`) valem igual; `proposta` (o canvas)
não aparece.

| `event` | `data` | quando |
|---|---|---|
| `conversa` | `{conversa_id, titulo, nova}` | **sempre o primeiro** de `POST /conversa` — o cliente aprende o id de uma conversa nova |
| `fluxo` | `{workflow_id, nome}` | um `create_workflow` do assistente deu certo. **Não é renderizado**: a Home não oferece caminho para o editor. Segue no contrato porque o servidor o emite e o replay o reconstrói |
| `camada` | `{artifact_id, nome?, format?, available, hint?}` | uma saída GeoJSON de uma execução, ou um `exibir_no_globo`. É PONTEIRO; a verdade é `GET /assistente/camadas/{id}` |
| `confirmacao` | `{tool_use_id, token, acao{tool, argumentos, alvo}}` | uma ação que mexe no que já existia espera o clique |
| `respostas_rapidas` | `{opcoes: [até 3 frases]}` | um `sugerir_respostas` do assistente: continuações curtas que a pessoa escolhe com um clique (viram a próxima mensagem dela). Valem só para aquela vez — a web só as desenha no último turno, fora do stream; o replay as traz de volta enquanto forem as do último turno |

O `fim` é sempre o último, mesmo quando deu errado — como no editor. Um `: ping`
(comentário SSE, ignorado pelo decodificador) sai a cada 15 s no silêncio, para
o stream não morrer atrás de um proxy numa execução longa.

## A confirmação, por dentro

Nunca por texto. O portão da Home intercepta a chamada confirmável, guarda
`{token, tool, args}` no Redis por 15 min sob
`agente:confirmacao:{user}:{conversa}:{tool_use_id}`, emite o quadro
`confirmacao` e devolve ao modelo um `tool_result` NÃO-erro "aguardando" — um
erro faria o modelo repetir a chamada e duplicar o botão. O prompt manda o
modelo dizer uma linha e encerrar o turno.

O clique (`POST /conversas/{id}/confirmacoes/{tool_use_id}`) **valida** no
handler, em ordem:

1. **posse** — a conversa é da pessoa (senão 404);
2. **existência** — a chave ainda está no Redis (senão 409, expirou);
3. **token** — `hmac.compare_digest` com o token guardado (senão 403).

O **consumo** (o `delete` one-shot) NÃO é feito no handler: ele mora no gerador
do stream, **sob a trava** e imediatamente antes de executar. Se o cliente cair
entre o retorno do handler e o efeito rodar, a confirmação sobrevive e pode ser
refeita — consumir no handler a apagaria mesmo sem a ação ter acontecido, e a
ação confirmada se perderia sem repetição. A trava serializa as abas, então o
`delete` ainda decide a corrida: quem apagou executa (`delete` = 1), quem chegou
depois perde (`delete` = 0, e um quadro de erro fecha o stream).

Aí ele executa os argumentos **ARMAZENADOS** — nunca os que o cliente mandar no
clique — por `chamar_no_servidor`, sob o escopo do assistente, injeta uma
mensagem de usuário gerada pelo servidor (`[Ação confirmada pela pessoa pelo
botão]…`, ou `[Ação recusada pela pessoa]`) e **retoma** o laço no mesmo SSE. A
mensagem sintética é gravada com `meta={"tipo":"confirmacao",…}`.

**O prefixo `[Ação` é do servidor.** Uma mensagem digitada que comece com ele é
recusada com 422 (`POST /conversa`) — senão alguém forjaria "a pessoa confirmou".

## A persistência

O transcrito fica no **banco**, não no cliente — a mesma razão do editor: um
`tool_result` é a palavra do servidor, e um cliente que guardasse o transcrito
poderia reescrevê-lo. `POST /conversa` aceita **apenas** a mensagem nova
(`extra="forbid"`), e a grava no handler (antes do stream). Os turnos do
assistente são gravados **incrementalmente**, turno a turno, pelo gancho
`ao_fechar_turno` do laço — não num blob no fim. Fechar a aba no meio não perde
o que já veio.

- `conversas` — id, dona (FK `users`), workspace/fluxo de contexto (opcionais),
  título, origem, `tokens_total`, datas, `deleted_at` (soft delete).
- `mensagens` — `ordem` única por conversa, papel, `blocos` (o conteúdo VERBATIM
  na forma que a API aceita de volta), `meta` (a marca da confirmação).

`mensagens.blocos` guarda inclusive a `signature` do bloco de raciocínio: sem
ela, a API recusa a próxima volta na retomada.

## O replay

`GET /assistente/conversas/{id}` devolve a conversa nos **mesmos quadros do SSE**,
para o painel reaplicar pelo mesmo caminho de um quadro ao vivo. Duas regras:

- um `tool_result` **nunca** sai (é a palavra do servidor, não conteúdo de
  tela); o `fluxo`/`camada` de uma execução — e as `respostas_rapidas` de um
  `sugerir_respostas` — são reconstruídos pelo mesmo `quadros_extras` da Home,
  casando cada `tool_use` com o seu resultado;
- uma `confirmacao` só reaparece **com o token** se a chave dela ainda existe no
  Redis — uma chave sumida (decidida ou expirada) não vira botão morto.

## Limites conhecidos

- **A cota é compartilhada com o editor** (`assistente:tokens:{user}`): o modelo é
  o mesmo, o orçamento por pessoa é um só. Sem `OPENROUTER_API_KEY`, `POST` responde
  503 e `GET /estado` responde `ativo:false` — nunca 404.
- **Sem Redis não há confirmação nem trava**: uma ação confirmável é recusada
  fechada (não há como guardar o token para validar o clique). É a degradação do
  resto da plataforma — a API nem sobe sem Redis.
- **Arrastar arquivo com o assistente indisponível não mostra os chips.** A
  caixa (barra ou painel) é quem desenha os anexos; enquanto o `/estado` carrega
  ela some por um aviso, e se ele falhou (`ativo:false`, 502) a caixa não monta.
  O upload ao Drive é independente e ACONTECE de qualquer jeito — o arquivo
  aparece na tela `/drive` —, mas o retorno na Home só surge quando/se a caixa
  voltar. O caso é estreito: sem assistente, nada mais na Home funciona também.
- **Os anexos são da sessão, não da conversa.** Um F5 perde o `File` (e os chips
  ainda em `enviando`); o que já subiu está no Drive. Trocar de conversa não
  limpa os chips — eles são "o que acabei de soltar", não parte do histórico.
  **Trocar de WORKSPACE, sim, limpa:** os arquivos foram para o Drive do
  workspace anterior, e a referência da mensagem casa com o workspace da
  conversa — mantê-los apontaria para arquivos que o assistente do novo
  workspace não acha.
- **Sem caminho por teclado.** O envio é só por arraste (o botão de clipe é um
  follow-up). Quem não usa mouse não importa arquivo pela Home — não é
  regressão (a tela `/drive`, que tem o campo acessível, já é inalcançável para
  quem não é admin), mas fica registrado como o próximo passo.
- **Deploy não roda migração.** Ao subir esta versão:
  `docker compose exec api-prod alembic upgrade head`.
