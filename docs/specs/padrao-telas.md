# Padrão de telas do Atlans

Contrato de consistência visual e de interação para as telas da aplicação web
(`web/`). Extraído das quatro telas já redesenhadas — **Dashboard**, **Histórico**
(`/observability`), **Projetos** e **Workspaces** — e do shell. Toda tela nova ou
padronizada segue este documento. É guia de implementação, não de produto: preserva
a função e a arquitetura de informação de cada tela; alinha casca, estados, tokens,
acessibilidade e microcopy.

Referências vivas: `web/app/globals.css` (tokens) e
`docs/specs/{dashboard,projetos,historico-metricas}.md`.

---

### 0. Shell e casca da página
- **Layout raiz**: `sidebar/index.tsx` → `SidebarProvider` + `AppSidebar` + `<main class="flex-1 overflow-auto bg-card flex flex-col">` com `AppHeader` sticky (`app-header.tsx`) e o conteúdo abaixo.
- **`AppHeader`** (`web/app/components/app-header.tsx`): barra sticky `h-12 px-4 border-b border-border bg-background/95 backdrop-blur z-40`. Mostra o `WorkspaceSwitcher`; slot `right` reservado. É `app-region-drag` (janela desktop). Rotas de canvas fullscreen (`/workflow/`) retornam `null`.
- **`PageRoot`** (`web/app/components/page-root.tsx`): TODA tela é envolvida por `<PageRoot>`. Ele dá `<main class="flex justify-center w-full px-safe">` + miolo `flex flex-col gap-4 px-4 py-6 sm:gap-6 sm:px-8 sm:py-8 max-w-6xl w-full` com fade de entrada em CSS (`animate-in fade-in slide-in-from-bottom-2 duration-350 ease-out`). Padding menor no telefone; `px-safe` cobre o notch. Espaçamento vertical entre blocos de topo é o `gap-4 sm:gap-6` do PageRoot — não repita margens.
- **Exceção — a Home (`/`)**: é full-bleed como o canvas do editor, e NÃO segue os itens acima. O layout `(dashboard)` é compartilhado, e um `ShellSidebar` (client, `usePathname`) troca a casca: em `/` renderiza o **`HomeSidebar`** (grupo *Meus → Agendamentos, Artefatos, Chats*; marca linkando `/projects`; rodapé `UserSidebar`), nas demais rotas o `AppSidebar` de sempre. O `AppHeader` retorna `null` em `/` (como em `/workflow/`). A página é `<HomeView>` — `relative h-svh w-full overflow-hidden`, sem `PageRoot` — com o globo em tela cheia. A Home é **sempre escura**, independente do tema do app: a raiz da `HomeView` e do `HomeSidebar` leva `className="home dark"`, e o bloco `.home` em `globals.css` sobrescreve os neutros para a escala quase preta (`#050505`/`#0f0f0f`/`#171717`/`#262626`/`#ececec`), mantendo a terracota do `.dark`.

### 1. Cabeçalho de página (padrão fixo)
Primeiro filho do `PageRoot`, sempre este esqueleto:
```
<div className="flex flex-wrap items-start justify-between gap-3 sm:gap-4">
  <div className="min-w-0">
    <h1 className="text-2xl font-semibold text-foreground">Título</h1>
    {subtitulo ? <p className="text-sm font-medium text-muted-foreground">…</p> : <Skeleton className="mt-1 h-4 w-64" />}
  </div>
  <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto"> {/* ações à direita */} </div>
</div>
```
- **h1**: `text-2xl font-semibold text-foreground`. Workspaces usa `text-2xl` também (não `text-xl`). Uma palavra/curto.
- **Subtítulo**: `text-sm font-medium text-muted-foreground`, uma frase que diz o ESCOPO/estado ("Execuções dos seus workflows · comparado com os 30 dias anteriores"; "10 workflows em 3 grupos · 8 ativos"). Enquanto não há o que contar (1ª carga), vira `<Skeleton className="mt-1 h-4 w-64" />` — nunca escreve "— ativos".
- **Ações à direita**: agrupadas em `flex ... gap-2`, `w-full sm:w-auto` (empilham no telefone). Hierarquia: **1 ação primária** (`<Button>` default, laranja) à direita de tudo; secundárias em `variant="outline"`; **Atualizar** sempre `variant="ghost" size="sm"` com `<TbRefresh size={14} className={carregando ? "motion-safe:animate-spin" : undefined}/>` + rótulo "Atualizar". No **Histórico** o Atualizar é seguido do **Frescor** ("atualizado há 20 s", `text-xs tabular-nums text-muted-foreground`, relógio próprio via `textoDeFrescor` de `observability/cabecalho.tsx`) — atualmente esse frescor é exclusivo do Histórico; Dashboard, Projetos e Workspaces não o renderizam.
- **Toggles de escopo/período**: grupo `role="group" aria-label` `inline-flex h-8 w-full overflow-hidden rounded-md border bg-card max-md:h-10 sm:w-auto`; botões com `aria-pressed`, `border-l first:border-l-0`, ativo = `bg-accent text-foreground`, inativo = `text-muted-foreground hover:bg-accent/60`.
- **Telefone**: quando há 3+ ações, o secundário vai para um menu `⋯` (`DropdownMenu`, gatilho `variant="outline" size="icon" size-10 shrink-0 md:hidden`) e o primário ocupa a linha (`flex-1 max-md:h-10 md:flex-none`). Ver `projects/cabecalho.tsx`.
- Ícones dos botões: `react-icons/tb`, `size={14}`–`15`.

### 2. Seções e cartões
Duas formas, ambas com a MESMA moldura:
- **Cartão base**: `rounded-lg border bg-card shadow-xs`. Nunca hex; sempre `bg-card` + `border` (herda `border-border`). Sombra é sempre `shadow-xs` (não `shadow-sm`/`md` salvo hover). O hero de destaque usa `rounded-xl` (Workspaces `workspace-hero`, SaudeHero atenção/crítico).
- **Seção com título**: `<section aria-labelledby="X-titulo" class="flex min-w-0 flex-col rounded-lg border bg-card shadow-xs">`; cabeçalho interno `px-4 pt-4 pb-1` com `<h2 id="X-titulo" class="text-sm font-semibold">` + linha de apoio `text-xs text-muted-foreground`. Corpo em `px-2 pb-2 pt-1` (listas) ou `px-4 pb-4`.
- **Eyebrow / título de faixa fora de cartão**: `text-[11px] font-semibold uppercase tracking-wide text-muted-foreground` (ex.: "Resumo do período · últimos 30 dias", "Outros workspaces", "Sem grupo"). Alguns usam `tracking-[0.08em]`/`[0.1em]`.
- **Indicador/stat**: `relative flex min-w-0 flex-col gap-1.5 overflow-hidden rounded-lg border bg-card p-3 shadow-xs sm:p-4`; título `text-[11px] font-semibold uppercase tracking-wide text-muted-foreground` + ícone `text-muted-foreground`; valor `text-2xl font-semibold leading-none tabular-nums tracking-tight`; sparkline absoluto no canto. Ver `observability/indicadores.tsx`.
- **Hero de destaque** (workspace ativo, saúde em alerta): `relative overflow-hidden rounded-xl border bg-card shadow-xs` + friso de identidade/tom `absolute inset-y-0 left-0 w-1.5` (a cor de identidade entra só como friso — sem brilho difuso/degradê no fundo) + `motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-1 motion-safe:duration-300`.
- **Linha/row de lista** (item clicável): `flex items-center gap-3 rounded-lg border bg-card px-3 py-2.5 shadow-xs`, hover `hover:bg-accent/40`/`hover:border-muted-foreground/30`. Item de lista dentro de cartão-seção é `<button>` full-width com `grid ... rounded-md px-2 py-2 text-left hover:bg-accent/60 focus-visible:bg-accent/60 focus-visible:ring-[3px] focus-visible:ring-ring/50`.

### 3. Estados (contrato — os quatro estados canônicos)
As molduras dos estados moram numa peça só, `components/shared/estados.tsx` — `CartaoDeEstado`, `ErroDeCarga`, `VazioPrimeiroUso`, `SemResultado`/`textoDeSemResultado` e `AvisoAmbar`: use-a, não recopie o cartão. Cada tela guarda no seu `estados.tsx` só os Skeleton* (que desenham o layout real) e as SUAS frases, e a composição fica no `index`; telas sem módulo próprio (Histórico, Workspaces, o editor, o portal) usam as mesmas peças inline. Ordem de precedência no `index`: **carregando → erro (só se nunca houve carga aceita) → primeiro uso → conteúdo**; dentro do conteúdo, **sem resultado** e **avisos de falha parcial** por seção.

1. **Skeleton da 1ª carga**: desenha o layout REAL (mesmas alturas/grids) para a troca não pular. Wrapper `role="status" aria-busy="true" aria-label="Carregando …"`. Usa `<Skeleton>` (`ui/skeleton.tsx`, shimmer). O cabeçalho real fica por cima (o `index` sempre o renderiza); o skeleton cobre só os blocos. Alturas típicas: indicadores `h-24`, gráfico `h-56`, listas `h-48`/`h-56`, hero `h-11`/`h-48`.
2. **Erro** (fonte-espinha caiu na 1ª carga): cartão centralizado `flex flex-col items-center justify-center gap-3 rounded-lg border border-destructive/20 bg-card px-6 py-14 text-center shadow-xs`; ícone `TbAlertTriangle` em círculo `border border-destructive/20 bg-destructive/10 p-3 text-destructive`; título `text-sm font-medium` "Não foi possível carregar …"; mensagem `text-xs text-muted-foreground`; `<Button variant="outline" size="sm" className="mt-2 max-md:h-10">Tentar de novo</Button>`; `role="alert"` (§5). Peça: `ErroDeCarga({ titulo, mensagem, onTentar })` — o anúncio vem do tom `erro` do `CartaoDeEstado`, não de quem compõe a tela lembrar dele; `mensagem` é a do servidor, quando a tela a tem. Só toma a tela se `atualizadoEm == null` — recarga que falha sobre lista pronta NÃO apaga a tela (mantém o que havia + toast).
3. **Vazio / primeiro uso**: cartão centralizado `rounded-lg border bg-card px-6 py-14 text-center shadow-xs`; ícone em círculo `bg-muted/60 p-5` com ícone `text-muted-foreground/50`; título `text-base font-semibold`; parágrafo `text-sm text-muted-foreground`; opcionalmente passos numerados; CTA primário se `canEdit`, senão "Peça a um editor do workspace…". Distingue **primeiro uso** (sem nada) de **sem resultado** (recorte ativo, ícone `TbFilterOff`, oferece "Limpar filtros"). Peças: `VazioPrimeiroUso` (o cartão `amplo`: ícone 36, `gap-5`, `passos?`, `cta` para quem `podeCriar`, senão "Peça a um editor do workspace para {pedirA}.") e `SemResultado` (o cartão `compacto` do §3.2 em tom neutro — ícone 26, `p-3`, título `text-sm font-medium`, dica `text-xs` —, com a frase de `textoDeSemResultado`). O vazio de uma seção (Histórico, Admin › Configurações) é o `CartaoDeEstado` compacto.
4. **Falha parcial por seção (aviso âmbar)**: uma linha, NÃO derruba o bloco — `role="status"` `flex flex-wrap items-center gap-x-2 gap-y-1 rounded-md border border-amber-500/30 bg-amber-50 px-3 py-1.5 text-xs text-amber-700 dark:bg-amber-500/10 dark:text-amber-400` + `TbAlertTriangle size={14}` + texto + botão "Tentar de novo" inline (`underline-offset-2 hover:underline focus-visible:ring-[3px] max-md:min-h-10`). Peça: `AvisoAmbar` (`shared/estados.tsx`); `rotuloDoBotao` traduz o botão onde a tela fala outros idiomas (a Home).
   - Variante "dado velho" (Histórico): `<p role="alert" class="rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive">…{" Mostrando a última leitura."}</p>` — usada por seção quando há leitura anterior na tela.

### 4. Grid e espaçamento
- Espaço entre blocos de topo: herdado do `PageRoot` (`gap-4 sm:gap-6`). Dentro de uma seção multi-parte: `flex flex-col gap-3`.
- **Grid de indicadores**: `grid grid-cols-2 gap-3 lg:grid-cols-4`.
- **Duas colunas conteúdo/lateral**: `grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]` (Dashboard) ou `lg:grid-cols-[minmax(0,1.55fr)_minmax(300px,1fr)]` (Histórico). Sempre 1 coluna abaixo de `lg`; no telefone a lista mais acionável vem primeiro.
- **Grid de cards/linhas**: `grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3` (Workspaces).
- **`gap`**: `gap-4` entre blocos maiores, `gap-3` dentro de seção, `gap-2`/`gap-2.5` entre linhas/botões, `gap-0.5`/`gap-1` entre itens de lista dentro de cartão.
- `min-w-0` em todo contêiner flex/grid que contém texto truncável; `truncate` no que pode estourar. Conteúdo largo rola em `overflow-x-auto` próprio — o body é `overflow-x: clip`.

### 5. Acessibilidade
- Seções: `<section aria-labelledby="X-titulo">` com `<h2 id="X-titulo">` (mesmo quando o h2 é `sr-only`, como no SaudeHero calmo).
- `aria-busy` nos contêineres em carregamento; `role="status" aria-busy="true" aria-label` nos skeletons; `role="alert"` em erros.
- Itens de lista são `<button>` com `aria-label` completo (nome + detalhe + ação); grupos de toggle com `aria-pressed`; abas com `role="tabpanel"`/`aria-labelledby`.
- **Foco**: sempre `focus-visible:ring-[3px] focus-visible:ring-ring/50` (botões shadcn já trazem `focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]`). `outline-none` só junto com um ring visível.
- **Alvos ≥40px no telefone**: `max-md:h-10` em botões/chips/campos, `max-md:min-h-10`/`min-h-10` em links e itens clicáveis, `size-10` em botões-ícone mobile. Ícone decorativo `coarse:opacity-40`; affordance só-hover (setas) escondida no ponteiro grosso (variante `coarse`).
- **Movimento**: toda animação sob `motion-safe:` (spin do Atualizar, entrada de heros, ping do "em execução"). `globals.css` congela animações do canvas em `prefers-reduced-motion`.
- Ícones puramente visuais: `aria-hidden="true"`.

### 6. Dark/Light — tokens
- **Nunca hex solto** em superfície/texto/borda. Use tokens: `bg-card`, `text-foreground`, `text-muted-foreground`, `border`/`border-border`, `bg-background`, `bg-accent`, `bg-muted`, `text-primary`, `bg-destructive`/`text-destructive`, `ring-ring`. Definidos em `oklch` em `globals.css` (`:root` claro, `.dark` escuro), primário laranja/terracota.
- **Exceção documentada — cores de status**: os únicos literais permitidos são os pares Tailwind de status, sempre com o par dark: `bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-400` (sucesso), `red` (falha/erro), `blue` (em andamento/fila), `amber` (presa/cancelado/aviso), `yellow` (pendente), `purple` (cache). Padrão canônico em `shared/StatusBadge.tsx`. Pontos de estado: `bg-green-500`/`bg-amber-500`/`bg-red-500`/`bg-blue-500`.
- Gráfico (Recharts) usa hex fixo nas 4 séries (`#22c55e/#ef4444/#3b82f6/#f59e0b`) porque `fill` de SVG não aceita classe — igual nos dois temas, definido em `grafico-por-dia.tsx SERIES`.
- Aviso âmbar: `border-amber-500/30 bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400`.
- `tabular-nums` em todo número (contagens, durações, percentuais, frescor).

### 7. Microcopy (pt-BR)
- **Tom**: direto, minúsculo nos rótulos de apoio, frase curta. Verbos no infinitivo/imperativo nos botões ("Criar workflow", "Novo grupo", "Atualizar", "Tentar de novo", "Usar", "Configurar", "Limpar filtros"). Nomes de entidades entre aspas angulares: `«{nome}»`.
- **Deep-links padronizados**: "Ver no Histórico →" (`TbArrowRight size={13}`), "Ver em andamento →", "Ver execuções". Link em `text-primary text-xs font-medium underline-offset-2 hover:underline`.
- **Erros**: "Não foi possível carregar o painel/os projetos/…" + botão "Tentar de novo". Falha parcial: "Não foi possível carregar {a atividade recente / o gráfico / as próximas execuções}." / "Sem dados de execução agora — a lista continua completa." / "Mostrando a última leitura."
- **Vazios**: "Nada rodou ainda", "Comece pelo primeiro workflow", "Nenhum workspace encontrado", "Nenhuma execução recente.", "Sem execuções no período.", "Nenhum workflow com «{q}»".
- **Frescor**: "atualizado agora" / "atualizado há 20 s" / "atualizado há 3 min" / "atualizado há 2 h" (grão grosso, `textoDeFrescor`).
- **Status em pt-BR** via `shared/status-rotulos.ts` (`rotuloDoStatus`); o valor cru fica em `data-status`. Origem/categoria/nível: `rotuloDaOrigem`/`rotuloDaCategoria`/`rotuloDoNivel` em `observability/formatos.ts` ("manual", "webhook", "agendado", "reexecução", "tempo esgotado", "sem executor"…).
- **Plurais e números**: sempre por `plural(n, "singular")` e `formatarInteiro` (milhar pt-BR "1.284"); percentual com vírgula "96,4%" (`formatarPercentual`); pontos "−1,1 pt" (`formatarPontos`); duração por extenso "4 min 02 s" / "2 h 14 min" (`formatarDuracao`); tempo relativo "há 6 min" (`formatarQuando`/`formatarInicio`). Zero some do subtítulo ("0 agendados" não aparece).
### 8. Componentes reutilizáveis (não reinventar)

| Componente | Arquivo | Uso |
|---|---|---|
| `PageRoot` | `components/page-root.tsx` | Envelope obrigatório de toda tela (max-w-6xl, padding responsivo, gap, fade de entrada). |
| Shell | `components/sidebar/index.tsx`, `sidebar/app-sidebar.tsx`, `app-header.tsx` | Casca: sidebar colapsável + main scrollável + header sticky. Telas só respeitam o header sticky. |
| `Skeleton` | `components/ui/skeleton.tsx` | Placeholder com shimmer; base de todo estado de 1ª carga, com alturas reais. |
| `StatusBadge` | `components/shared/StatusBadge.tsx` | Selo de status (fonte canônica das cores de status + rótulo pt-BR). |
| `status-rotulos` | `components/shared/status-rotulos.ts` | `rotuloDoStatus(status)` → pt-BR. Nunca exibir status cru. |
| `Sparkline` | `components/shared/Sparkline.tsx` | Mini-gráfico SVG (`currentColor`), usado nos indicadores. |
| `EntityCard` | `components/shared/EntityCard.tsx` | Card genérico de entidade (leading + título + badge + descrição + ações). |
| `DeleteDialog` | `components/shared/DeleteDialog.tsx` | Confirmação de exclusão reutilizável (ação destrutiva): `confirmarDigitando` para o "digite X para confirmar", `children` para os avisos. |
| `useAcaoDeDialogo` | `hooks/useAcaoDeDialogo.ts` | Ciclo de um diálogo de ação (abrir, executar, toast, fechar) com guarda de reentrada: o Enter e o clique chamam o mesmo `executar`, e a ação roda uma vez só. |
| `bloqueado` | `components/ui/dialog.tsx` (`DialogContent`) | Operação em voo: trava Esc, clique fora e o `X` de uma vez. Não copiar o trio `onEscapeKeyDown` + `onInteractOutside` + `closeDisabled`. |
| `useFetchData` | `hooks/useFetchData.ts` | Carga de tela: 1ª carga × recarga, erro, guarda de resposta velha (geração), gate de sessão, `atualizadoEm` e `onErroComDados` (o toast da recarga). O auto-refresh e a volta à aba chamam `recarregarEmFundo`, não o `refetch`: com a 1ª carga em erro, o cartão fica na tela durante a tentativa, em vez de sair e voltar (e ser anunciado de novo) a cada tique. Não reescrever loading/erro à mão. |
| `Indicadores` | `components/observability/indicadores.tsx` | Grid de 4 stat-cards com tendência e sparkline. |
| `GraficoPorDia` | `components/observability/grafico-por-dia.tsx` | Seção-cartão "Execuções por dia" (barras via next/dynamic). |
| `formatos` | `components/observability/formatos.ts` | Toda formatação pt-BR: `formatarInteiro/Percentual/Pontos/Duracao/Inicio/Quando`, `plural`, `rotuloDaOrigem/Categoria/Nivel`. Usar sempre. |
| `textoDeFrescor` | `components/observability/cabecalho.tsx` | "atualizado há N" (grão grosso). Reusado por todos os cabeçalhos. |
| Estados de tela | `components/shared/estados.tsx` | Molduras dos estados do §3: `CartaoDeEstado` (tom `erro`/`neutro` — `role="alert"` automático no erro —, tamanho `compacto`/`amplo`), `ErroDeCarga`, `VazioPrimeiroUso`, `SemResultado`/`textoDeSemResultado`, `AvisoAmbar`. Usar `shared/estados.tsx` — não copiar a estrutura; o `estados.tsx` de cada tela guarda só os Skeleton* e as frases. |
| `ui/*` (shadcn) | `components/ui/*` | Primitivos: Button (default/outline/ghost/destructive; sizes default h-9, sm h-8, icon size-9), Dialog, Sheet, Select, DropdownMenu, Input, Switch, Tooltip, Separator. Foco ring-[3px] embutido. |

### 9. Escopo deste lote (redesenho de consistência)

**Telas padronizadas** (preservam função/IA; alinham casca, estados, tokens, a11y,
microcopy): **Autenticação** (login já é a referência; nivelar cadastro, recuperar
senha, redefinir senha, verificar e-mail — extrair uma casca `AuthShell`, migrar às
classes `.auth-*`, `aria-hidden` no fundo decorativo; desde a Home aberta sem login, as
CINCO são painéis do **modal de entrada da Home** — `components/home/entrada/`, no tema
dela — e as rotas antigas só redirecionam para lá, de modo que nenhuma segue a
`AuthShell`), **Credenciais**, **Drive**,
**Executores** (manter o "trilho"-tabela denso como variante deliberada), **Artefatos**,
**Admin › Configurações**, **Admin › Usuários**, **Portal de compartilhamento** (`/share`
— corrigir a página de erro, microcopy acentuada, estados vazios, foco/alvos; manter o
mapa e a identidade de marca), e afinações no **shell** (CommandPalette, NotificationBell,
ExecutorLocalBadge, TitleSidebar).

**Sem mudança de backend** em nenhuma tela — é um passe 100% web.

**Fora do lote — Editor de workflow (canvas React Flow):** o canvas é o núcleo do
produto e tela cheia (sem `PageRoot`/`AppHeader`, por contrato). Não é redesenhado aqui.
Apenas um passe cosmético mínimo e de baixo risco no *chrome* flutuante: `shadow-sm →
shadow-xs` em `workflow-location`/`global-save-indicator`, `ring-2 → ring-[3px]` no botão
do save-indicator, tokenizar as cores do MiniMap, e trocar o erro ad-hoc de
`/workflow/[id]` pelo cartão de erro do §3.2. Nada de canvas/nós/arestas/execução/Monaco.

### 10. Dados de tela: `@tanstack/react-query` (migração em curso)

Prova feita em **Artefatos** (`(dashboard)/artifacts/use-artifacts-query.ts`, presa por `__tests__/app/artefatos/tela-de-artefatos.test.tsx`); as demais telas seguem nos hooks feitos à mão até migrarem.

- **Cliente**: `ProvedorDeConsultas` (`components/provedor-de-consultas.tsx`) envolve o layout `(dashboard)`, a Home inclusive. Os padrões (`lib/consultas.ts`) são os das telas de hoje: sem nova tentativa, sem releitura no foco nem na reconexão, **sem cache** (`staleTime`/`gcTime` 0) e `networkMode: "always"`. Migrar não muda o que a tela mostra; cache, releitura e repetição são decisão de cada consulta. O logout recarrega a página, e o cache vai junto — se um dia a troca de usuário acontecer sem recarga, é preciso um `queryClient.clear()` no `SessionSync`.
- **Consulta**: as opções numa função (`queryOptions`/`infiniteQueryOptions`), com TODOS os filtros na chave — é a chave que descarta a resposta de um filtro velho (sai o `seq`/`geracao`). O `queryFn` lança quando `res.error` vem preenchido: o service não lança, e só um erro que sobe põe a consulta em erro sem apagar o dado.
- **Saída da chave**: sair dela (outro filtro, outra aba, outra tela) cancela a busca da chave deixada — `cancelQueries({ queryKey, exact: true })` no cleanup de um efeito sobre a consulta. O `queryFn` não aborta a requisição e o `gcTime: 0` só descarta a consulta ociosa: sem o cancelamento, um "Ver mais" em voo mantinha viva a consulta deixada, e a volta pegava carona nela, com a lista guardada e sem skeleton.
- **Estados (§3)**: `loading = isPending || (isFetching && !isFetchingNextPage)`. O gate `atualizadoEm` é da montagem, não da chave: o `dataUpdatedAt` zera com o filtro novo, e o filtro que falha depois de uma carga aceita é aviso âmbar, não cartão. O erro sai da tela enquanto uma nova busca está em voo.
- **"Ver mais"**: `useInfiniteQuery` com `getNextPageParam` derivando o offset das páginas; `fetchNextPage` tem identidade estável (acabou o offset em ref). Recarregar volta à 1ª página com `cancelQueries` + `client.infiniteQuery({ ...opcoes, pages: 1, staleTime: 0 })` — o `refetch()` refaria, uma a uma, todas as páginas abertas.
- **Cache e lista anterior**: `staleTime` + `gcTime` explícitos só onde a tela já guarda dado (o TTL de 60 s do Histórico). `placeholderData: keepPreviousData` só onde a tela já mantém a lista anterior durante a troca (o Drive, pelo `useFetchData`); Artefatos zera a lista de propósito e não o usa.
- **Polling**: `refetchInterval: N` (já pausa com a aba oculta) + `refetchOnWindowFocus: true` com `staleTime: N` — relê ao voltar só se o intervalo venceu, como o `setInterval` + `visibilitychange` de hoje.
- **Mutações**: `invalidateQueries` pela chave. O dedup de GET em voo e a época de escrita de `service/http.ts` ficam até a última leitura sair do caminho manual.

**Ordem da migração**: (1) `observability/use-execucoes.ts`, gêmeo da prova (`with_total` só na página 0, `has_more` no `getNextPageParam`); (2) na Home, `useConversas` e `useAgendamentos` ("Ver mais" com `geracao`); (3) o `useFetchData` por dentro, com a mesma interface e uma chave por chamador — Credenciais, Tokens, settings-sheet, Admin, Executores, Drive e Planos de uma vez, presos pelos testes do próprio hook; (4) os de polling com várias fontes — `use-projetos-dados`, `use-dashboard-dados`, `use-historico-dados` (`useQueries`, uma consulta por fonte, o TTL como `staleTime`); (5) `useAcervo`; (6) os contextos (execuções ativas, notificações, workspaces) e, por último, o dedup e a época de `service/http.ts`.
