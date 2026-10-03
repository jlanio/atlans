# Atlans screen patterns

Contract for visual and interaction consistency across the screens of the web application
(`web/`). Extracted from the four screens already redesigned — **Dashboard**, **Histórico** (History)
(`/observability`), **Projetos** (Projects) and **Workspaces** — and from the shell. Every new or
standardized screen follows this document. It is an implementation guide, not a product guide: it preserves
each screen's function and information architecture; it aligns the page frame, states, tokens,
accessibility and microcopy.

Living references: `web/app/globals.css` (tokens) and
`docs/specs/{dashboard,projetos,historico-metricas}.md`.

---

### 0. Shell and page frame
- **Root layout**: `sidebar/index.tsx` → `SidebarProvider` + `AppSidebar` + `<main class="flex-1 overflow-auto bg-card flex flex-col">` with a sticky `AppHeader` (`app-header.tsx`) and the content below.
- **`AppHeader`** (`web/app/components/app-header.tsx`): sticky bar `h-12 px-4 border-b border-border bg-background/95 backdrop-blur z-40`. Shows the `WorkspaceSwitcher`; `right` slot reserved. It is `app-region-drag` (desktop window). Fullscreen canvas routes (`/workflow/`) return `null`.
- **`PageRoot`** (`web/app/components/page-root.tsx`): EVERY screen is wrapped in `<PageRoot>`. It provides `<main class="flex justify-center w-full px-safe">` + an inner column `flex flex-col gap-4 px-4 py-6 sm:gap-6 sm:px-8 sm:py-8 max-w-6xl w-full` with a CSS entrance fade (`animate-in fade-in slide-in-from-bottom-2 duration-350 ease-out`). Smaller padding on phones; `px-safe` covers the notch. Vertical spacing between top-level blocks is PageRoot's `gap-4 sm:gap-6` — do not repeat margins.
- **Exception — the Home (`/`)**: it is full-bleed like the editor canvas, and does NOT follow the items above. The `(dashboard)` layout is shared, and a `ShellSidebar` (client, `usePathname`) swaps the frame: on `/` it renders the **`HomeSidebar`** (group *Meus → Agendamentos, Artefatos, Chats* (Mine → Schedules, Artifacts, Chats); brand linking to `/projects`; `UserSidebar` footer), on the other routes the usual `AppSidebar`. The `AppHeader` returns `null` on `/` (as on `/workflow/`). The page is `<HomeView>` — `relative h-svh w-full overflow-hidden`, without `PageRoot` — with the globe in full screen. The Home is **always dark**, regardless of the app theme: the root of `HomeView` and of `HomeSidebar` carries `className="home dark"`, and the `.home` block in `globals.css` overrides the neutrals with the near-black scale (`#050505`/`#0f0f0f`/`#171717`/`#262626`/`#ececec`), keeping the terracotta of `.dark`.

### 1. Page header (fixed pattern)
First child of `PageRoot`, always this skeleton:
```
<div className="flex flex-wrap items-start justify-between gap-3 sm:gap-4">
  <div className="min-w-0">
    <h1 className="text-2xl font-semibold text-foreground">Título</h1>
    {subtitulo ? <p className="text-sm font-medium text-muted-foreground">…</p> : <Skeleton className="mt-1 h-4 w-64" />}
  </div>
  <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto"> {/* actions on the right */} </div>
</div>
```
- **h1**: `text-2xl font-semibold text-foreground`. Workspaces uses `text-2xl` too (not `text-xl`). One word/short.
- **Subtitle**: `text-sm font-medium text-muted-foreground`, one sentence that states the SCOPE/state ("Execuções dos seus workflows · comparado com os 30 dias anteriores" (Runs of your workflows · compared with the previous 30 days); "10 workflows em 3 grupos · 8 ativos" (10 workflows in 3 groups · 8 active)). While there is nothing to count (1st load), it becomes `<Skeleton className="mt-1 h-4 w-64" />` — it never writes "— ativos".
- **Actions on the right**: grouped in `flex ... gap-2`, `w-full sm:w-auto` (they stack on phones). Hierarchy: **1 primary action** (default `<Button>`, orange) to the right of everything; secondary ones in `variant="outline"`; **Atualizar** (Refresh) is always `variant="ghost" size="sm"` with `<TbRefresh size={14} className={carregando ? "motion-safe:animate-spin" : undefined}/>` + the label "Atualizar". On **Histórico**, Atualizar is followed by the **freshness** indicator ("atualizado há 20 s" (updated 20 s ago), `text-xs tabular-nums text-muted-foreground`, its own clock via `textoDeFrescor` from `observability/cabecalho.tsx`) — currently this freshness indicator is exclusive to Histórico; Dashboard, Projetos and Workspaces do not render it.
- **Scope/period toggles**: group `role="group" aria-label` `inline-flex h-8 w-full overflow-hidden rounded-md border bg-card max-md:h-10 sm:w-auto`; buttons with `aria-pressed`, `border-l first:border-l-0`, active = `bg-accent text-foreground`, inactive = `text-muted-foreground hover:bg-accent/60`.
- **Phone**: when there are 3+ actions, the secondary ones go into a `⋯` menu (`DropdownMenu`, trigger `variant="outline" size="icon" size-10 shrink-0 md:hidden`) and the primary one takes the whole row (`flex-1 max-md:h-10 md:flex-none`). See `projects/cabecalho.tsx`.
- Button icons: `react-icons/tb`, `size={14}`–`15`.

### 2. Sections and cards
Two forms, both with the SAME frame:
- **Base card**: `rounded-lg border bg-card shadow-xs`. Never hex; always `bg-card` + `border` (inherits `border-border`). The shadow is always `shadow-xs` (not `shadow-sm`/`md` except on hover). The highlight hero uses `rounded-xl` (Workspaces `workspace-hero`, SaudeHero attention/critical).
- **Section with a title**: `<section aria-labelledby="X-titulo" class="flex min-w-0 flex-col rounded-lg border bg-card shadow-xs">`; inner header `px-4 pt-4 pb-1` with `<h2 id="X-titulo" class="text-sm font-semibold">` + a supporting line `text-xs text-muted-foreground`. Body in `px-2 pb-2 pt-1` (lists) or `px-4 pb-4`.
- **Eyebrow / band title outside a card**: `text-[11px] font-semibold uppercase tracking-wide text-muted-foreground` (e.g. "Resumo do período · últimos 30 dias" (Period summary · last 30 days), "Outros workspaces" (Other workspaces), "Sem grupo" (No group)). Some use `tracking-[0.08em]`/`[0.1em]`.
- **Indicator/stat**: `relative flex min-w-0 flex-col gap-1.5 overflow-hidden rounded-lg border bg-card p-3 shadow-xs sm:p-4`; title `text-[11px] font-semibold uppercase tracking-wide text-muted-foreground` + icon `text-muted-foreground`; value `text-2xl font-semibold leading-none tabular-nums tracking-tight`; absolutely positioned sparkline in the corner. See `observability/indicadores.tsx`.
- **Highlight hero** (active workspace, health on alert): `relative overflow-hidden rounded-xl border bg-card shadow-xs` + identity/tone stripe `absolute inset-y-0 left-0 w-1.5` (the identity color comes in only as a stripe — no diffuse glow/gradient in the background) + `motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-1 motion-safe:duration-300`.
- **List line/row** (clickable item): `flex items-center gap-3 rounded-lg border bg-card px-3 py-2.5 shadow-xs`, hover `hover:bg-accent/40`/`hover:border-muted-foreground/30`. A list item inside a section card is a full-width `<button>` with `grid ... rounded-md px-2 py-2 text-left hover:bg-accent/60 focus-visible:bg-accent/60 focus-visible:ring-[3px] focus-visible:ring-ring/50`.

### 3. States (contract — the four canonical states)
The state frames live in a single piece, `components/shared/estados.tsx` — `CartaoDeEstado`, `ErroDeCarga`, `VazioPrimeiroUso`, `SemResultado`/`textoDeSemResultado` and `AvisoAmbar`: use it, do not re-copy the card. Each screen keeps in its own `estados.tsx` only the Skeleton* (which draw the real layout) and ITS OWN phrases, and the composition lives in the `index`; screens without their own module (Histórico, Workspaces, the editor, the portal) use the same pieces inline. Order of precedence in the `index`: **loading → error (only if there has never been an accepted load) → first use → content**; within the content, **no results** and **partial-failure warnings** per section.

1. **1st-load skeleton**: draws the REAL layout (same heights/grids) so the swap does not jump. Wrapper `role="status" aria-busy="true" aria-label="Carregando …"`. Uses `<Skeleton>` (`ui/skeleton.tsx`, shimmer). The real header stays on top (the `index` always renders it); the skeleton covers only the blocks. Typical heights: indicators `h-24`, chart `h-56`, lists `h-48`/`h-56`, hero `h-11`/`h-48`.
2. **Error** (the backbone source failed on the 1st load): centered card `flex flex-col items-center justify-center gap-3 rounded-lg border border-destructive/20 bg-card px-6 py-14 text-center shadow-xs`; `TbAlertTriangle` icon in a circle `border border-destructive/20 bg-destructive/10 p-3 text-destructive`; title `text-sm font-medium` "Não foi possível carregar …" (Could not load …); message `text-xs text-muted-foreground`; `<Button variant="outline" size="sm" className="mt-2 max-md:h-10">Tentar de novo</Button>`; `role="alert"` (§5). Piece: `ErroDeCarga({ titulo, mensagem, onTentar })` — the announcement comes from the `erro` tone of `CartaoDeEstado`, not from whoever composes the screen remembering it; `mensagem` is the server's, when the screen has it. It only takes over the screen if `atualizadoEm == null` — a reload that fails over a ready list does NOT wipe the screen (it keeps what was there + a toast).
3. **Empty / first use**: centered card `rounded-lg border bg-card px-6 py-14 text-center shadow-xs`; icon in a circle `bg-muted/60 p-5` with icon `text-muted-foreground/50`; title `text-base font-semibold`; paragraph `text-sm text-muted-foreground`; optionally numbered steps; primary CTA if `canEdit`, otherwise "Peça a um editor do workspace…" (Ask a workspace editor…). It distinguishes **first use** (nothing at all) from **no results** (active filter, `TbFilterOff` icon, offers "Limpar filtros" (Clear filters)). Pieces: `VazioPrimeiroUso` (the `amplo` card: icon 36, `gap-5`, `passos?`, `cta` for whoever `podeCriar`, otherwise "Peça a um editor do workspace para {pedirA}.") and `SemResultado` (the `compacto` card of §3.2 in a neutral tone — icon 26, `p-3`, title `text-sm font-medium`, hint `text-xs` —, with the phrase from `textoDeSemResultado`). A section's empty state (Histórico, Admin › Configurações) is the compact `CartaoDeEstado`.
4. **Partial failure per section (amber warning)**: one line, it does NOT bring down the block — `role="status"` `flex flex-wrap items-center gap-x-2 gap-y-1 rounded-md border border-amber-500/30 bg-amber-50 px-3 py-1.5 text-xs text-amber-700 dark:bg-amber-500/10 dark:text-amber-400` + `TbAlertTriangle size={14}` + text + an inline "Tentar de novo" (Try again) button (`underline-offset-2 hover:underline focus-visible:ring-[3px] max-md:min-h-10`). Piece: `AvisoAmbar` (`shared/estados.tsx`); `rotuloDoBotao` translates the button where the screen speaks other languages (the Home).
   - "Stale data" variant (Histórico): `<p role="alert" class="rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive">…{" Mostrando a última leitura."}</p>` — used per section when there is a previous reading on screen.

### 4. Grid and spacing
- Space between top-level blocks: inherited from `PageRoot` (`gap-4 sm:gap-6`). Inside a multi-part section: `flex flex-col gap-3`.
- **Indicator grid**: `grid grid-cols-2 gap-3 lg:grid-cols-4`.
- **Two columns, content/side**: `grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]` (Dashboard) or `lg:grid-cols-[minmax(0,1.55fr)_minmax(300px,1fr)]` (Histórico). Always 1 column below `lg`; on phones the most actionable list comes first.
- **Card/row grid**: `grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3` (Workspaces).
- **`gap`**: `gap-4` between larger blocks, `gap-3` inside a section, `gap-2`/`gap-2.5` between rows/buttons, `gap-0.5`/`gap-1` between list items inside a card.
- `min-w-0` on every flex/grid container that holds truncatable text; `truncate` on whatever can overflow. Wide content scrolls in its own `overflow-x-auto` — the body is `overflow-x: clip`.

### 5. Accessibility
- Sections: `<section aria-labelledby="X-titulo">` with `<h2 id="X-titulo">` (even when the h2 is `sr-only`, as in the calm SaudeHero).
- `aria-busy` on loading containers; `role="status" aria-busy="true" aria-label` on skeletons; `role="alert"` on errors.
- List items are `<button>` with a complete `aria-label` (name + detail + action); toggle groups with `aria-pressed`; tabs with `role="tabpanel"`/`aria-labelledby`.
- **Focus**: always `focus-visible:ring-[3px] focus-visible:ring-ring/50` (shadcn buttons already come with `focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]`). `outline-none` only together with a visible ring.
- **Targets ≥40px on phones**: `max-md:h-10` on buttons/chips/fields, `max-md:min-h-10`/`min-h-10` on links and clickable items, `size-10` on mobile icon buttons. Decorative icon `coarse:opacity-40`; hover-only affordance (arrows) hidden on a coarse pointer (`coarse` variant).
- **Motion**: every animation under `motion-safe:` (the Atualizar spin, hero entrances, the "em execução" (running) ping). `globals.css` freezes canvas animations under `prefers-reduced-motion`.
- Purely visual icons: `aria-hidden="true"`.

### 6. Dark/Light — tokens
- **Never a loose hex** on surface/text/border. Use tokens: `bg-card`, `text-foreground`, `text-muted-foreground`, `border`/`border-border`, `bg-background`, `bg-accent`, `bg-muted`, `text-primary`, `bg-destructive`/`text-destructive`, `ring-ring`. Defined in `oklch` in `globals.css` (`:root` light, `.dark` dark), orange/terracotta primary.
- **Documented exception — status colors**: the only literals allowed are the Tailwind status pairs, always with the dark pair: `bg-green-100 text-green-700 dark:bg-green-500/15 dark:text-green-400` (success), `red` (failure/error), `blue` (in progress/queued), `amber` (stuck/cancelled/warning), `yellow` (pending), `purple` (cache). Canonical pattern in `shared/StatusBadge.tsx`. State dots: `bg-green-500`/`bg-amber-500`/`bg-red-500`/`bg-blue-500`.
- The chart (Recharts) uses fixed hex for the 4 series (`#22c55e/#ef4444/#3b82f6/#f59e0b`) because SVG `fill` does not accept a class — the same in both themes, defined in `grafico-por-dia.tsx SERIES`.
- Amber warning: `border-amber-500/30 bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400`.
- `tabular-nums` on every number (counts, durations, percentages, freshness).

### 7. Microcopy (pt-BR)
- **Tone**: direct, lowercase in supporting labels, short sentences. Verbs in the infinitive/imperative on buttons ("Criar workflow" (Create workflow), "Novo grupo" (New group), "Atualizar" (Refresh), "Tentar de novo" (Try again), "Usar" (Use), "Configurar" (Configure), "Limpar filtros" (Clear filters)). Entity names in angle quotes: `«{nome}»`.
- **Standardized deep links**: "Ver no Histórico →" (See in History →) (`TbArrowRight size={13}`), "Ver em andamento →" (See in progress →), "Ver execuções" (See runs). Link in `text-primary text-xs font-medium underline-offset-2 hover:underline`.
- **Errors**: "Não foi possível carregar o painel/os projetos/…" (Could not load the dashboard/the projects/…) + a "Tentar de novo" button. Partial failure: "Não foi possível carregar {a atividade recente / o gráfico / as próximas execuções}." (Could not load {the recent activity / the chart / the upcoming runs}.) / "Sem dados de execução agora — a lista continua completa." (No run data right now — the list is still complete.) / "Mostrando a última leitura." (Showing the last reading.)
- **Empty states**: "Nada rodou ainda" (Nothing has run yet), "Comece pelo primeiro workflow" (Start with the first workflow), "Nenhum workspace encontrado" (No workspace found), "Nenhuma execução recente." (No recent runs.), "Sem execuções no período." (No runs in the period.), "Nenhum workflow com «{q}»" (No workflow with "{q}").
- **Freshness**: "atualizado agora" / "atualizado há 20 s" / "atualizado há 3 min" / "atualizado há 2 h" (updated now / 20 s ago / 3 min ago / 2 h ago; coarse grain, `textoDeFrescor`).
- **Status in pt-BR** via `shared/status-rotulos.ts` (`rotuloDoStatus`); the raw value stays in `data-status`. Origin/category/level: `rotuloDaOrigem`/`rotuloDaCategoria`/`rotuloDoNivel` in `observability/formatos.ts` ("manual", "webhook", "agendado" (scheduled), "reexecução" (re-run), "tempo esgotado" (timed out), "sem executor" (no executor)…).
- **Plurals and numbers**: always through `plural(n, "singular")` and `formatarInteiro` (pt-BR thousands "1.284"); percentage with a comma "96,4%" (`formatarPercentual`); points "−1,1 pt" (`formatarPontos`); duration spelled out "4 min 02 s" / "2 h 14 min" (`formatarDuracao`); relative time "há 6 min" (6 min ago) (`formatarQuando`/`formatarInicio`). Zero disappears from the subtitle ("0 agendados" (0 scheduled) does not appear).
### 8. Reusable components (do not reinvent)

| Component | File | Use |
|---|---|---|
| `PageRoot` | `components/page-root.tsx` | Mandatory envelope of every screen (max-w-6xl, responsive padding, gap, entrance fade). |
| Shell | `components/sidebar/index.tsx`, `sidebar/app-sidebar.tsx`, `app-header.tsx` | Frame: collapsible sidebar + scrollable main + sticky header. Screens only have to respect the sticky header. |
| `Skeleton` | `components/ui/skeleton.tsx` | Placeholder with shimmer; the basis of every 1st-load state, with real heights. |
| `StatusBadge` | `components/shared/StatusBadge.tsx` | Status badge (canonical source of the status colors + pt-BR label). |
| `status-rotulos` | `components/shared/status-rotulos.ts` | `rotuloDoStatus(status)` → pt-BR. Never display a raw status. |
| `Sparkline` | `components/shared/Sparkline.tsx` | SVG mini-chart (`currentColor`), used in the indicators. |
| `EntityCard` | `components/shared/EntityCard.tsx` | Generic entity card (leading + title + badge + description + actions). |
| `DeleteDialog` | `components/shared/DeleteDialog.tsx` | Reusable deletion confirmation (destructive action): `confirmarDigitando` for the "type X to confirm", `children` for the warnings. |
| `useAcaoDeDialogo` | `hooks/useAcaoDeDialogo.ts` | Lifecycle of an action dialog (open, execute, toast, close) with a reentrancy guard: Enter and the click call the same `executar`, and the action runs only once. |
| `bloqueado` | `components/ui/dialog.tsx` (`DialogContent`) | Operation in flight: locks Esc, outside click and the `X` all at once. Do not copy the `onEscapeKeyDown` + `onInteractOutside` + `closeDisabled` trio. |
| `useFetchData` | `hooks/useFetchData.ts` | Screen load: 1st load × reload, error, stale-response guard (generation), session gate, `atualizadoEm` and `onErroComDados` (the reload toast). Auto-refresh and returning to the tab call `recarregarEmFundo`, not `refetch`: with the 1st load in error, the card stays on screen during the attempt, instead of leaving and coming back (and being announced again) on every tick. Do not rewrite loading/error by hand. |
| `Indicadores` | `components/observability/indicadores.tsx` | Grid of 4 stat cards with trend and sparkline. |
| `GraficoPorDia` | `components/observability/grafico-por-dia.tsx` | Section card "Execuções por dia" (Runs per day) (bars via next/dynamic). |
| `formatos` | `components/observability/formatos.ts` | All pt-BR formatting: `formatarInteiro/Percentual/Pontos/Duracao/Inicio/Quando`, `plural`, `rotuloDaOrigem/Categoria/Nivel`. Always use it. |
| `textoDeFrescor` | `components/observability/cabecalho.tsx` | "atualizado há N" (updated N ago; coarse grain). Reused by every header. |
| Screen states | `components/shared/estados.tsx` | Frames for the states of §3: `CartaoDeEstado` (tone `erro`/`neutro` — automatic `role="alert"` on error —, size `compacto`/`amplo`), `ErroDeCarga`, `VazioPrimeiroUso`, `SemResultado`/`textoDeSemResultado`, `AvisoAmbar`. Use `shared/estados.tsx` — do not copy the structure; each screen's `estados.tsx` keeps only the Skeleton* and the phrases. |
| `ui/*` (shadcn) | `components/ui/*` | Primitives: Button (default/outline/ghost/destructive; sizes default h-9, sm h-8, icon size-9), Dialog, Sheet, Select, DropdownMenu, Input, Switch, Tooltip, Separator. Built-in ring-[3px] focus. |

### 9. Scope of this batch (consistency redesign)

**Standardized screens** (they preserve function/IA; they align frame, states, tokens, a11y,
microcopy): **Autenticação** (Authentication; login is already the reference; level up sign-up, password
recovery, password reset, email verification — extract an `AuthShell` frame, migrate to the
`.auth-*` classes, `aria-hidden` on the decorative background; since the Home opened up without login, all
FIVE are panels of the **Home sign-in modal** — `components/home/entrada/`, in its
theme — and the old routes only redirect there, so none of them follows the
`AuthShell`), **Credenciais** (Credentials), **Drive**,
**Executores** (Executors; keep the dense table-style "rail" as a deliberate variant), **Artefatos** (Artifacts),
**Admin › Configurações** (Settings), **Admin › Usuários** (Users), **Portal de compartilhamento** (Share portal; `/share`
— fix the error page, accented microcopy, empty states, focus/targets; keep the
map and the brand identity), and refinements in the **shell** (CommandPalette, NotificationBell,
ExecutorLocalBadge, TitleSidebar).

**No backend change** on any screen — it is a 100% web pass.

**Outside the batch — Workflow editor (React Flow canvas):** the canvas is the core of the
product and full-screen (no `PageRoot`/`AppHeader`, by contract). It is not redesigned here.
Only a minimal, low-risk cosmetic pass on the floating *chrome*: `shadow-sm →
shadow-xs` on `workflow-location`/`global-save-indicator`, `ring-2 → ring-[3px]` on the
save-indicator button, tokenizing the MiniMap colors, and replacing the ad-hoc error of
`/workflow/[id]` with the error card of §3.2. Nothing on canvas/nodes/edges/execution/Monaco.

### 10. Screen data: `@tanstack/react-query` (migration in progress)

Proven on **Artefatos** (`(dashboard)/artifacts/use-artifacts-query.ts`, pinned by `__tests__/app/artefatos/tela-de-artefatos.test.tsx`); the other screens stay on hand-written hooks until they migrate.

- **Client**: `ProvedorDeConsultas` (`components/provedor-de-consultas.tsx`) wraps the `(dashboard)` layout, the Home included. The defaults (`lib/consultas.ts`) are those of today's screens: no retry, no refetch on focus or on reconnect, **no cache** (`staleTime`/`gcTime` 0) and `networkMode: "always"`. Migrating does not change what the screen shows; cache, refetching and retrying are each query's decision. Logout reloads the page, and the cache goes with it — if one day a user switch happens without a reload, a `queryClient.clear()` in `SessionSync` will be needed.
- **Query**: the options in a function (`queryOptions`/`infiniteQueryOptions`), with ALL the filters in the key — it is the key that discards the response of a stale filter (out goes the `seq`/`geracao`). The `queryFn` throws when `res.error` comes back filled in: the service does not throw, and only an error that propagates puts the query in error without wiping the data.
- **Leaving the key**: leaving it (another filter, another tab, another screen) cancels the fetch of the key left behind — `cancelQueries({ queryKey, exact: true })` in the cleanup of an effect on the query. The `queryFn` does not abort the request and `gcTime: 0` only discards an idle query: without the cancellation, a "Ver mais" (See more) in flight kept the abandoned query alive, and coming back piggybacked on it, with the stored list and no skeleton.
- **States (§3)**: `loading = isPending || (isFetching && !isFetchingNextPage)`. The `atualizadoEm` gate belongs to the mount, not to the key: `dataUpdatedAt` resets with the new filter, and a filter that fails after an accepted load is an amber warning, not a card. The error leaves the screen while a new fetch is in flight.
- **"Ver mais"**: `useInfiniteQuery` with `getNextPageParam` deriving the offset from the pages; `fetchNextPage` has a stable identity (no more offset in a ref). Reloading goes back to the 1st page with `cancelQueries` + `client.infiniteQuery({ ...opcoes, pages: 1, staleTime: 0 })` — `refetch()` would redo, one by one, every open page.
- **Cache and previous list**: explicit `staleTime` + `gcTime` only where the screen already keeps data (Histórico's 60 s TTL). `placeholderData: keepPreviousData` only where the screen already keeps the previous list during the switch (the Drive, through `useFetchData`); Artefatos clears the list on purpose and does not use it.
- **Polling**: `refetchInterval: N` (it already pauses with the tab hidden) + `refetchOnWindowFocus: true` with `staleTime: N` — it refetches on return only if the interval has elapsed, like today's `setInterval` + `visibilitychange`.
- **Mutations**: `invalidateQueries` by key. The in-flight GET dedup and the write epoch of `service/http.ts` stay until the last read leaves the manual path.

**Migration order**: (1) `observability/use-execucoes.ts`, the proof's twin (`with_total` only on page 0, `has_more` in `getNextPageParam`); (2) on the Home, `useConversas` and `useAgendamentos` ("Ver mais" with `geracao`); (3) `useFetchData` from the inside, with the same interface and one key per caller — Credentials, Tokens, settings-sheet, Admin, Executors, Drive and Plans all at once, pinned by the hook's own tests; (4) the polling ones with several sources — `use-projetos-dados`, `use-dashboard-dados`, `use-historico-dados` (`useQueries`, one query per source, the TTL as `staleTime`); (5) `useAcervo`; (6) the contexts (active runs, notifications, workspaces) and, last of all, the dedup and the epoch of `service/http.ts`.
