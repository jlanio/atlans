# Refactor da Home — decisões

Previewer aprovado: https://claude.ai/artifact/LKnVqCYZFXQYYh76aUXQZd (versão 6).
Fora deste documento: tudo o que é do mapa/globo (basemap, atmosfera, fronteiras, rótulos).

| PR | escopo | estado |
|---|---|---|
| 1 | hero do primeiro acesso, barra em destaque, transição, conversa ao centro (pilha) | **aplicado** |
| 2 | respostas rápidas e a marca animada no item pendente — **entregues** (2026-09-19); ainda pendentes: a marca no ícone da barra e no status do hero, o verbo cintilante e o cronômetro; as animações das interações (§6) entraram em seguida | parcial |
| 3 | agendamento e alerta (cartões, e-mail pelo `SendEmail`, aviso in-app) | pendente |

## Objetivo

Melhorar o visual ao acessar o site: a barra de diálogo em destaque, no centro, e a conversa
evoluindo ali mesmo — sem abrir o painel lateral por padrão como antes (`homeStore.painel` começava
em `"aberto"`).

## 1. Quando o hero aparece

- É o **estado inicial de todo acesso ao site** (carregar a página). Não é "primeira vez do
  usuário": sem flag, sem `localStorage`, sem consulta ao servidor.
- Vale **também sem login**: a Home abre anônima com o mesmo hero; o primeiro envio abre o modal
  de entrada (login/cadastro) sobre o globo, e a mensagem vai sozinha quando o login dá certo
  (`docs/assistant.md`, "A Home sem sessão e o modal de entrada").
- Termina no **primeiro token visível da primeira resposta** — texto, erro ou cartão. Raciocínio
  (`pensando`) e chamadas de ferramenta ainda são "processando": a barra fica no centro, com o
  status. *Decidido no PR 1: primeiro token, e não o fim da resposta — a barra escorrega enquanto a
  resposta começa, o que esconde a latência.*
- Abrir um chat antigo (replay) ou o painel (Ctrl+I, chevron) também encerra o hero: há conversa
  para ler.
- Uma vez encerrado, não volta nesta carga. "Nova conversa" no meio da sessão cai no layout normal,
  vazio.

## 2. Layout do hero

- O globo ocupa a tela com a parte norte visível e um degradê para o sul até sumir (`.home-veu`,
  um overlay que some na transição).
- O globo **gira devagar** enquanto o hero está na tela: meio grau por segundo para oeste, em
  passos lineares de 1 s (`giroLento` no `MapLibreMap`, como no previewer). Um gesto da pessoa
  pausa o giro por 2,5 s; com `prefers-reduced-motion` ele não gira. No primeiro token o giro para
  e o mapa **volta ao Brasil** (o `center`/`zoom` do Globo) em 900 ms, junto com a barra.
- A barra fica no **centro**; acima dela, o título e a frase que a Home já usava ("Peça uma análise
  espacial…"); abaixo, três chips de sugestão.

## 3. Barra de diálogo

- Mais destaque: 56 px de altura e texto de 16 px no hero (rodapé: 44 px / 14 px), anel e brilho
  laranja discretos, ícone num círculo tingido. No foco o brilho sobe um pouco.
- **Sugestões digitadas** no campo enquanto ele está vazio, com cursor laranja piscando, ciclando
  quatro frases do produto (`SUGESTOES` em `barra.tsx`). **Tab** aceita, **Enter** envia (vazio
  envia a sugestão da vez); qualquer tecla interrompe; apagar tudo traz a sugestão de volta. Chips
  clicáveis preenchem o campo.
- Depois do primeiro token, o **mesmo elemento** escorrega para o rodapé e encolhe para a barra de
  hoje — 900 ms, `cubic-bezier(.22,.9,.3,1)` (`.home-barra` em `globals.css`); sem movimento com
  `prefers-reduced-motion`.
- Enviar **não abre o painel**: a conversa segue ao centro. O chevron abre o painel lateral.

## 4. Conversa ao centro

- Uma **faixa** colada à barra, no lugar do painel — a legenda do globo (decisão de produto em
  2026-09-19, a Opção 4 do previewer; antes era uma pilha de texto solto, com degradê no topo e
  rolagem, e a resposta escorregava para cima durante o stream). A faixa é fixa, com fundo quase
  preto, sem degradê nem rolagem, e mostra só a **última troca** (2 itens): a pergunta numa linha
  ("Você · …", truncada, o texto inteiro no `title`) e, da resposta, **o que ficou** — o último
  texto cortado em 4 linhas, os erros e os cartões — e **o que está vivo** enquanto o turno corre
  ("Trabalhando…" ou o passo em curso). Raciocínio, passos concluídos e textos anteriores ficam para
  o painel. Abaixo dos itens, o rodapé: o contador "N mensagens anteriores" à esquerda e
  **Expandir** à direita.
- **Expandir** (link na pilha, chevron da barra ou **Ctrl+I**) leva tudo ao painel lateral como já
  ocorria; o painel tem o campo próprio; "Recolher" volta ao centro. Enquanto o painel está aberto,
  a barra e a pilha somem.
- Um único modelo de conversa alimenta as duas vistas: a pilha é a mesma `Conversa` do painel
  recortada aos últimos turnos, e os cartões (confirmação, camada) vêm do mesmo hook
  (`useExtrasDoAssistente`). Nada é duplicado.
- A preferência "painel aberto/recolhido" **não é mais gravada** no navegador: o hero a ignoraria
  de qualquer jeito, e o painel passou a ser sob demanda.
- A resposta pode trazer **respostas rápidas**: até três chips sob o texto (`sugerir_respostas`,
  uma ferramenta local do assistente; quadro `respostas_rapidas`), na faixa e no painel. Valem só
  para aquela vez: só no último turno e fora do stream; o clique manda a frase como a próxima
  mensagem e o turno novo os tira da tela; no replay, os do último turno voltam. (Entregue em
  2026-09-19, junto com a marca animada do item pendente.)

## 5. Processando

- *PR 1:* enquanto processa, os chips dão lugar a uma linha de status ("Trabalhando…") com "Esc para
  parar"; **Esc de fato cancela** (`agente.parar`), exceto de dentro de um diálogo ou menu, onde a
  tecla já tem dono. O ícone da barra vira o indicador de atividade do produto (`ExecActivity`).
- A **marca animada** — a marca do site sem o fundo laranja, só o grafo de três nós e três linhas
  em laranja; um traço percorre cada aresta (n1 → n2 → n3 → n1) e acende o nó ao chegar, ciclo de
  2,4 s com uma respiração leve do conjunto (`assistente/marca-animada.tsx`, CSS em `globals.css`;
  parada e inteira sob `prefers-reduced-motion`) — **entrou no item pendente da conversa** (faixa e
  painel), por decisão de produto em 2026-09-19. A marca estática do sidebar segue com dois nós.
- *Pendente:* a mesma marca no ícone da barra e na linha de status do hero e, ao lado, no estilo
  Claude Code, o verbo cintilante que troca a cada ~1,7 s ("Trabalhando…", o passo em curso) e o
  cronômetro.

## 6. Animações das interações (PR 2)

- **Entregue (2026-09-19):** ao enviar, um anel terracota pisca na caixa da barra (`data-flash`, o
  `::after` de `.home-barra-caixa` — só opacidade, porque um `box-shadow` não interpola entre listas
  de tamanhos diferentes) e o botão de enviar afunda (`active:scale-90`, também no painel).
- Na faixa, **nada desliza**: a faixa e cada mensagem nova entram só com um fade curto (o mesmo
  token de duração do hero, zerado por `prefers-reduced-motion`), e não há animação de saída — o
  texto só troca. (Entregue com a faixa em 2026-09-19; substitui o deslize com escala e o fade para
  cima planejados aqui.)
- **Entregue:** o parágrafo que está sendo escrito termina num cursor terracota (`cursorAoEscrever`
  da `Conversa`, o mesmo `.home-caret` da sugestão digitada; some quando uma ferramenta o segue ou o
  turno acaba); o cartão de camada pipoca ao chegar (`home-pop`, ~320 ms com sobressalto).
- **Entregue:** ao expandir para a lateral, a faixa desliza para a direita e apaga, a barra apaga e
  o painel entra da direita (~300 ms). A HomeView segura a faixa e a barra montadas por `SAIDA_MS`
  (`useSaida`) — sem cliques e sem roubar o foco do painel — e recolher dentro do prazo cancela.
  Tudo zera sob `prefers-reduced-motion` (o flash, de duração fixa, é desligado à parte).

## 7. Agendamento e alerta (PR 3)

- A resposta de uma análise termina oferecendo o agendamento: "Quer que eu rode isso todo dia e te
  avise — aqui e por e-mail — se passar de N?", com a resposta rápida "Sim, agende e me avise".
- Ao aceitar, a resposta traz dois cartões: **Agendamento** (todo dia · 07:00 · ativo) e **Alerta**
  (aviso se > 500 focos · vigiando); o item novo aparece em **Agendamentos** no sidebar.
- Quando o alerta dispara: notificação no topo do globo (com "Ver no globo" e fechar), mensagem
  "Alerta disparado" na conversa e **e-mail pelo nó `SendEmail`** que já existe no fluxo, com resumo
  e link. Na vida real, dispara na próxima execução.
- Onde entra: `schedule_service` + `execution_alert_service` com um fluxo terminando no
  `SendEmail`; o aviso **in-app** é o pedaço novo (canal a decidir: polling do estado ou evento).

## 8. Onde está no código (PR 1)

- `components/home/index.tsx`: o estado `hero` (inicial, encerra no primeiro token), o véu, o
  título, a transição e o Esc.
- `assistente/barra.tsx`: as variantes `hero`/`rodape` do mesmo elemento, as sugestões digitadas,
  os chips, o status "Trabalhando…" e o botão de parar.
- `assistente/pilha.tsx`: a última troca ao centro; `assistente/extras.tsx`: os cartões, partilhados
  com o painel.
- `stores/homeStore.ts`: `painel` começa em `"barra"` e não é gravado.
- `globals.css`, seção "Home: o hero do primeiro acesso": o véu, as transições e a pilha.

## 9. Localização no globo — "me achar e me locomover"

Previewer aprovado: https://claude.ai/artifact/4zTeXh5ooRGmSe8NT3L5Hb (versão 2).

O botão de localização do MapLibre no globo da Home, no modo **seguir**: mostra a
pessoa no mapa e acompanha em tempo real enquanto ela anda. É o único controle de
mapa que a Home ganha além do zoom/bússola/escala que já existiam.

Decisões de produto:

- **Só por clique** (opção A). O navegador exige um gesto para pedir a permissão,
  e puxar a localização sozinho ao abrir seria invasivo. O aviso de permissão é o
  do **navegador** (a aparência não é nossa) e aparece só na primeira vez; depois
  de autorizado, clicar localiza direto.
- **Botão no canto superior direito**, na mesma pilha de vidro discreto do zoom e
  da bússola — onde os controles do mapa já vivem. O painel da conversa abre em
  baixo à direita e não o cobre.
- **Localizar manda no globo**: o giro do hero pausa e a "volta ao Brasil" não
  dispara enquanto o seguir estiver ativo — senão o mapa puxaria a pessoa para
  longe no instante em que a encontrou.
- **Só na web na v1.** No app desktop a precisão cai no IP (sem GPS); fica
  desligado por ora.

Onde está no código:

- `components/share/MapLibreMap.tsx`: a prop `geolocalizar` (opt-in) adiciona o
  `GeolocateControl` (`trackUserLocation`), pausa o giro por um ref lido no laço,
  e o `_cssDoMapa` repinta o botão ativo e o ponto do usuário na cor da marca. Os
  textos do controle entram no `locale` em pt-BR.
- `components/home/globo.tsx`: passa `geolocalizar` — o `/share` não passa, e por
  isso não ganha o controle.
- `next.config.ts`: `Permissions-Policy: geolocation=(self)` — sem isso o próprio
  site fica proibido de pedir a localização.

## 10. Localização no assistente — "análise perto de mim"

Previewers aprovados: o fluxo (https://claude.ai/artifact/QK4bRnBzUqBrvszfsJmnR5)
e a posição do botão (https://claude.ai/artifact/8PjQ2Ra49t7N3WY2vA8zci).

A localização do globo (a §9) passa a **entrar na conversa**: a coordenada vira um
chip removível no compositor e viaja no turno, e o assistente a usa como ponto de
referência para pedidos relativos ("perto de mim", "num raio de N km").

Decisões de produto:

- **A coordenada entra por um menu "+", não por um botão sempre visível** (a opção
  **B'**). Como o compositor não tinha nenhum "+" (anexo era só arrasta-e-solta), o
  "+" novo dá um lar descobrível às DUAS ações: "Anexar arquivo" (o mesmo caminho
  do arraste) e "Usar minha localização". Um menu, e não dois botões soltos, para
  não inchar a pílula da barra.
- **O estado fica à vista e sob controle**: o chip mostra a coordenada e a precisão
  e some no ×; a precisão exata é o padrão (o "aproximar" ficou de follow-up).
- **Uma fonte só**: "Usar minha localização" aciona o MESMO `GeolocateControl` do
  globo (via `localizar()` no handle), então o mapa também segue a pessoa; o
  `geolocate` sobe a coordenada. Vale enquanto definida — os próximos turnos a
  levam sem relocalizar.

Ajustes da revisão adversarial (mesmo dia, antes do PR):

- **Intenção ≠ posição.** `compartilharLocalizacao` é estado à parte: o × desliga
  a intenção e ela FICA desligada — antes, o próximo tick do modo seguir
  regravava a posição e o chip ressuscitava sozinho, mandando de volta a
  coordenada que a pessoa acabara de remover.
- **O botão nativo do globo voltou a ser só "me achar no mapa"**: ele atualiza a
  última posição, mas NÃO anexa nada à conversa — só o gesto no "+" anexa.
- **`localizar()` nunca alterna para OFF**: o `trigger()` do MapLibre é um
  alternador (já seguindo, desligava o rastreio em silêncio); já ativo, o handle
  só reemite a última posição.
- **A confirmação reenvia a coordenada** (`DecisaoDeConfirmacao.localizacao`): a
  retomada do laço não esquece o "perto de mim" — o servidor não guarda a
  posição (ela vive só no prompt do stream, nunca no transcrito).
- **Permissão negada solta o giro do hero** (o MapLibre não emite
  `trackuserlocationend` nesse erro) **e vira toast** — o botão do controle fica
  escondido atrás do painel no telefone. Cair para o 2º plano (arrastar) NÃO
  devolve o giro: o watch segue vivo em zoom alto.
- **Histerese de ~25 m** na posição: o jitter de GPS parado não muda o texto do
  prompt (cache do histórico) nem re-renderiza os compositores a cada tick.

Onde está no código:

- `components/share/MapLibreMap.tsx`: a prop `aoLocalizar` (o evento `geolocate` →
  `{ lat, lon, precisao_m }`) e `localizar()` no handle (aciona o controle de fora
  do mapa).
- `components/home/assistente/mais.tsx`: `BotaoMais` (o menu "+") e
  `ChipDeLocalizacao` — montados pela barra e pelo painel.
- `stores/homeStore.ts`: `localizacao` + `definirLocalizacao`/`limparLocalizacao`
  (na store pelo mesmo motivo do `rascunho`/anexos: Ctrl+I troca as superfícies).
- `hooks/home/useAssistente.ts`: lê a localização por ref e a inclui no corpo do
  turno só quando definida (sem ela, o corpo é o de sempre).
- Backend: `schemas/assistente.py` (`Localizacao` + campo em `MensagemDaHome`),
  `api/routers/assistente_router.py` (`_localizacao_extra`, dobrada em
  `instrucoes_extras` como o workspace já fazia) e `services/assistente_superficie.py`
  (uma linha ensinando o modelo a usar a localização nos pedidos relativos).

Follow-ups: "aproximar (~1 km)" a um toque para quem não quiser o ponto cravado;
localização no app desktop (fica na web na v1, como a §9).

## 11. Idiomas e região — a Home em inglês e espanhol

Pedido: a Home em pt-BR, inglês e espanhol, escolhida sozinha pela
região de quem acessa, com uma escolha fixa nas Preferências — e o globo
começando (e voltando) na região da pessoa, não mais sempre na América do Sul.

**Qual idioma** (`lib/idioma.ts`, resolvido no layout do dashboard, no servidor —
a primeira pintura já sai no idioma certo):

1. a escolha nas Preferências (cookie `idioma`, 365 dias, o mesmo modelo do tema);
2. o `Accept-Language` do navegador, respeitando os pesos `q` — é o sinal mais
   fiel do que a pessoa LÊ;
3. o país da conexão (`CF-IPCountry`): lusófonos → pt-BR, hispanófonos → es,
   os demais → en — só quando o navegador mandou um `Accept-Language` sem
   nenhum dos três idiomas;
4. sem `Accept-Language`, pt-BR: todo navegador o manda, e quem não manda é
   robô de busca ou script (o Googlebot sai dos EUA e indexaria a Home em
   inglês); com ele, mas sem nenhum dos três idiomas e sem país útil, en.

Nas Preferências, "Automático" é uma opção de verdade (apaga o cookie e mostra o
idioma detectado); a troca vale na hora, sem recarregar. Um `router.refresh()`
traz a escolha que o servidor leu — se o cookie mudou noutra aba, a tela, o
cookie e as Preferências voltam a concordar.

**Só a Home traduz.** O `EscopoPelaRota` limita a tradução à rota `/`: a
administração (editor, projetos, admin) segue em português, e os componentes
compartilhados com ela — o menu da conta, a conversa do assistente do editor,
o campo de senha — não ficam metade em cada língua. Sem provider (testes, o
portal `/share`), vale o português.

**Os textos** moram em `components/home/i18n/secoes/` (casca, assistente,
entrada, listas), com o português como molde: `en` e `es` são `typeof pt`, então
chave faltando é erro de compilação. O português ficou byte a byte o de antes,
com uma exceção de propósito: as quatro ferramentas do catálogo de fontes
(`search_sources`, `describe_source`, `probe_source`, `register_source`), que
apareciam na linha do tempo com o nome cru da API, ganharam rótulo ("Procurando
fontes de dados"…) — também na conversa do assistente do editor, que usa a
mesma `Conversa`. Componentes de fora da Home que ela usa ganharam uma prop de
textos com o português como padrão (o mapa, o painel de recusas do Drive, o X do
diálogo, os rótulos de leitor de tela da barra lateral, o trilho de largura).

A casca do app (barra lateral, cabeçalho, conta, Preferências, as listas do
"Meus") mora no layout do dashboard, que TODA rota carrega — e importa os
textos de `i18n/da-casca` (comum, casca, listas), não do índice. Pelo índice,
o bloco do layout levava junto os dicionários do assistente e da entrada, nos
três idiomas (~20 KB gzip), para a administração inteira; a tabela de rotas do
`next build` não mostra isso. O teste `i18n-layout` segue os imports do layout
e falha se ele voltar a alcançar o índice. A barra lateral e o gatilho do menu
declaram o próprio `lang`: são irmãos da HomeView, e o `lang` do `<html>` só
troca num efeito, depois da hidratação.

**O que o servidor diz.** O servidor só fala português. Em inglês e espanhol,
as recusas FIXAS têm o texto do idioma, escolhido pelo status: no login a
credencial inválida (401), o e-mail não verificado (403 + `X-Error-Code`), a
conta indisponível (os outros 403) e o bloqueio (429, com os minutos do
`Retry-After`); no cadastro o "já em uso" (o único 400); nos links do e-mail
(verificar, redefinir) o token inválido (400 e 404); o "link reenviado" da
verificação; e o aviso do assistente desligado (o `motivo` do servidor é para
quem administra). A tradução por status vale só para a recusa que É do
servidor — o corpo do `http_exception_handler` (`error: "http_exception"`),
ver `entrada/recusas.ts`: o 429 do limitador por IP não é conta bloqueada
("muitas tentativas desta conexão"), e o 502 do proxy `/terra`, o 500
inesperado e a página de erro de uma CDN viram o erro genérico do idioma, não
"esta conta não pode entrar" nem o português do proxy. Os erros do assistente
com código conhecido também — a conversa travada por outra aba
(`conversa_em_andamento`) e o
`rate_limited` do stream é a cota DIÁRIA, e o 429 da própria rota ganhou código
próprio (`muitas_requisicoes`); o quadro do `loop_limit` leva o `teto` para a
frase citar o número. Em português segue a mensagem do servidor, a de sempre.
Continua como veio o que o servidor escreve caso a caso: a validação campo a
campo do cadastro, a dica de uma camada, o motivo da recusa de um arquivo, e
qualquer erro de código desconhecido.

**O assistente responde no idioma da tela.** O turno leva `idioma` (`en`/`es`;
ausente em português) e o router soma um bloco ao prompt, depois da regra de
idioma da instalação, dizendo que ela vale no lugar daquela. O bloco vai no
EXTRA não cacheado: o prompt em português fica byte a byte o de sempre. A
confirmação reenvia o idioma, como já fazia com a localização. Limitação: numa
instalação com `ASSISTENTE_IDIOMA` que não seja português, a tela em português
recebe a resposta no idioma da instalação — o turno em português não leva
`idioma`, e o servidor não tem como pedir o português (era assim antes também).

**O globo pela região** (`components/home/mapa/regiao.ts`), sem pedir permissão:
o fuso do navegador → a cidade de referência do fuso (tabela IANA gerada por
`web/scripts/gerar-fusos.mjs`); sem fuso útil, o país da conexão — e o fuso
dos modos de privacidade não é útil: o "UTC", e o fuso da Islândia que o
Firefox com `resistFingerprinting`, o Tor Browser e o Mullvad Browser informam
(só a própria Islândia, pelo país da conexão, o mantém); depois o continente do nome do fuso; por fim o Brasil de
antes. A latitude fica entre 45° S e 50° N para o globo não abrir num polo. O
centro é lido uma vez, na montagem, e serve de início e de volta do hero. É a
REGIÃO que decide o globo, não o idioma: uma brasileira com a tela em inglês
continua vendo o Brasil.

Follow-ups: a preferência é por navegador (cookie) — sincronizar entre
aparelhos pede uma coluna no usuário; o diálogo de parâmetros de execução, os
modais das extensões e os e-mails seguem em português; os títulos dos controles do mapa
(zoom, bússola) valem os da montagem — trocar de idioma sem recarregar não os
atualiza.
