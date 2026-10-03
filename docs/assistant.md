# Home assistant — conversations over the globe

The Home assistant is the assistant of **another surface**. The loop is the same
(`app/services/assistente_service.py`), the authorization is the same (the MCP tools,
through the same `call_tool`), the token quota is the same (`assistente:tokens:{user}`).
What changes is the `HOME` surface package (`app/services/assistente_superficie.py`)
and the fact that the conversation is **persisted in the database** — see "Surfaces" in
`docs/editor-assistant.md` for the boundary of the loop.

This document is the **API** (`/assistente`): the routes, the SSE frames, the
click confirmation and the persistence.

## The page (the Home, `/`)

The assistant lives on the **Home** — the `/` route, everyone's landing page (it opens
**without login**; sign-in is requested on the first send — see "The Home without a session"). It is
a full-screen **3D globe** (MapLibre GL, `globe` projection, over Google's hybrid
imagery) that receives the output geometries of runs; the conversation floats
over it. The shell is "like Claude Code": a single `HomeSidebar`, with the brand at the
top, **Nova conversa** (New conversation), and the group **Meus → Agendamentos, Artefatos, Chats**
(Mine → Schedules, Artifacts, Chats); the footer is the usual `UserSidebar` (Tema, Configurações,
Sair — Theme, Settings, Sign out — with no navigation shortcut); without a session, the footer becomes
**Entrar** (Sign in) and **Criar conta** (Create account). The
Home is **always dark** (the near-black `.home` palette in `globals.css`),
regardless of the app's theme.

**Anyone who does not administer the system cannot reach any page other than the Home.** That is the
product's direction — the Home is the ONLY page for non-admins, with the rest migrating
over little by little. Today this is access control, not just what is offered: the
middleware (`web/proxy.ts`) sends any page outside it back to `/`
(`/projects`, `/workflow/…`, `/drive`, `/settings/tokens`, `/admin`,
`/dashboard`…) when the role is not admin — the `/terra` proxy, which the Home
lives on, and the `public/` files stay outside the gate; a session without a role fails
closed. Before that, the exits from the Home itself had already been closed, in this
order:

| exit | state |
|---|---|
| Sidebar brand → `/projects` | admin only. Without an `href`, the `Marca` becomes a `<span>`: both the destination **and** the hover highlight that said "this is clickable" go away |
| Agendamentos (Schedules) row → `/workflow/{id}` | closed. The row is a `<div>`: a `<button>` with no action would promise a click that does not happen |
| **Ctrl+K palette** | **does not open on `/` for non-admins** (`paletaDisponivel`) |
| **Workflow badge → `/workflow/{id}`** | **replaced**: the strip now shows the conversation's ARTIFACTS, and clicking puts one on the globe |
| Account menu → `/settings/tokens` | **closed**: the "Tokens de acesso" (Access tokens) item left the menu; and the route, like every page outside `/`, sends non-admins back to `/` (the admin gets there through the Ctrl+K palette or the URL) |
| `signOut` | open — the only exit from the app |

**The exits in the table were what was OFFERED; the access control is the middleware** — which
sends non-admins outside the Home back to `/` (since #155) and, without a session, only
lets the Home open: any other page goes to the Home with the sign-in modal
(see "The Home without a session and the sign-in modal", at the end of this section).

Two notes on the last two:

- **The palette does not open, instead of filtering item by item**, because TODAY every item
  in it leaves the Home: the eight static non-admin ones lead to other routes, and the
  dynamic ones are one per workflow (`/workflow/{id}`) and one per credential — these did not even
  go through `itensVisiveis`. Filtering would leave an empty box. As a bonus, the
  `loadItems` does not run: the `getWorkflows()` that fired on every Ctrl+K on the
  Home goes away. Outside `/`, and for admins, nothing changes.
- **The badge strip supersedes decision 4** ("the user never sees the workflow, unless
  they click the badge"): the workflow is no longer reachable from the Home. It
  remains in Projects, with the "mostrar os do assistente" (show the assistant's ones) switch on,
  for whoever gets there. The `fluxo` frame is still emitted and decoded — what
  goes away is the offer.

- **The route** lives in `web/app/(dashboard)/page.tsx` (the group does not contribute a
  segment). The `(dashboard)` layout is shared; a `ShellSidebar` (client,
  `usePathname`) picks `HomeSidebar` on `/` and `AppSidebar` on the other routes. The
  `AppHeader` returns `null` on `/`, as on the canvas.
- **The Meus (Mine) group of the `HomeSidebar`** (Agendamentos, Artefatos, Chats) are three
  collapsible items with the SAME row (`home/linha.tsx`: `LinhaDoMeu` +
  `GatilhoDeAcoes`): the main text is `min-w-0 flex-1` and truncates with an
  ellipsis and a `title`; the "⋯" is a flex sibling, never over the text — on the
  phone the 40px target just pushes the title. The open/closed state of the three is
  remembered in the browser (`atlans:home:meu`, read in `hidratar()`), so it
  survives the phone drawer, a route change and resizing; only Chats
  starts open. Closing an item HIDES the list (`hidden`), it does not unmount it —
  reopening does not redo requests nor lose the "Ver mais" (See more) —, and the list only mounts
  after hydrating (on the phone the first render is still the desktop branch, and
  mounting there fired a wasted GET). On the **3rem rail** (Ctrl+B, the
  trigger or the draggable edge, the `SidebarRail`), clicking an item expands the
  bar AND opens it — it never toggles an invisible state; the brand stays as a glyph
  (for the admin, still the link to Projects, with a tooltip) and only the wordmark goes away.
- **Portals in the Home palette.** Every Radix `*Content` opened from the
  Home (the "⋯" menus, tooltips, `RenameDialog`, `DeleteDialog`,
  `MetadataDialog`, `ExecuteParamsDialog`, the account menu and the Preferences)
  goes to the `<body>`, outside the `.home dark` tree, and that is why it carries `home-portal`
  (globals.css). The shared components gained optional `className` /
  `portalClassName` for this; outside the Home, nothing changes.
- **The basemap is the installation's hybrid imagery** (satellite + roads and labels,
  `MAPA_HIBRIDO_URL`; without it, the `MAPA_SATELITE_URL` satellite and, without that, the
  OpenStreetMap streets — `web/lib/fundos-do-mapa.ts`), the same one the `/share`
  portal offers in its switcher. There is no "no basemap" state. It is the **only**
  basemap of the Home (CARTO's Dark Matter, which required a free key, was removed),
  so the Home **has no switcher**: the `Globo` mounts the `MapLibreMap` with
  `basemapInicial="hybrid"` and `basemapToggle={false}`. Raster on the sphere distorts
  a little when the zoom changes (MapLibre recommends vector for the globe); with the
  imagery as the only basemap this is permanent and accepted.
- **The attribution is never written by us.** Every basemap we use already declares its
  own in the source (`MAPA_*_CREDITO`; "© OpenStreetMap contributors" on the default streets).
  Passing a `customAttribution` on top **did not replace** the source's —
  MapLibre concatenates the two with `" | "`, and the Home showed the same thing twice.
- **The map chrome is discreet** (`controlesDiscretos`): zoom, compass and scale
  wear a translucent glass instead of MapLibre's solid white box; the
  icon sits at 0.65 opacity and rises to 1 on hover/focus (on touch the floor is
  higher, because there is no hover to reveal it). The attribution goes into
  `compact` mode: it becomes an **"ⓘ" that opens on click**. It stays discreet, it never disappears —
  the providers' terms (and OSM's ODbL) require it, and a click is the
  way MapLibre itself offers for this. The portal keeps MapLibre's
  default.
- **The Chats** are the list of conversations (`GET /assistente/conversas`): rename
  (`PATCH`) and delete (`DELETE`, soft) through the ⋯ menu of each row. Clicking a chat
  opens the panel with the **replay** of that conversation. The list **mirrors the server
  without F5**: the 1st `conversa` frame of each message (id, title, `nova`) and the
  accepted confirmation become an announcement in the store (`anuncioDeConversa` — a slot,
  not a queue: the list may be unmounted) that the `ChatsLista` applies without a
  GET (`useConversas.anunciar`): the new conversation enters at the top with its title, the
  existing one moves up; renaming also moves it up (the server stamps `updated_at` on the
  PATCH). Deleting the **active** conversation leaves the Home as the "Nova conversa" button does
  (the ongoing stream stops; panel and stack empty out; the next message creates
  another, instead of hitting a 404). In the footer, "Ver mais" (See more) requests the next
  page and "Tentar de novo" (Try again) redoes **what failed** (the page, or the reload);
  the reload rereads every page already on screen, in parallel and all-or-nothing,
  because the server silently clips `limit` at 100.
- **Meus → Agendamentos** (Mine → Schedules; `GET /me/schedules`, `useAgendamentos`): the person's
  schedules across ALL workspaces, active and paused (the paused one shows the
  `motivoPausa` from `resumirAgendamento`). The ⋯ menu
  — only for operator+ IN THAT workspace (`hasMinRole` per item, since the list spans
  several) — offers pause/activate (`PUT /workflows/{id}/schedules/{job}`, optimistic) and
  run now (fetches `params_schema`, opens the `ExecuteParamsDialog` if there is one). The
  row NO LONGER opens the workflow in the editor (it is one of the closed exits): that is why it is a
  `<div>` and not a `<button>` — a button with no action would promise a click that does not
  happen. The assistant's workflow carries a badge. Turning it back on does not trigger right away (the
  `schedule_service` resets `next_run_at`).
- **Meus → Artefatos** (Mine → Artifacts; `useAcervo`): the collection of the current workspace — run
  artifacts (`GET /artifacts`) and Drive files (`GET /drive`) in the SAME list,
  joined by `Promise.allSettled` (the failure of one source does not bring down the other),
  distinguished only by icon and by the **permanent / ephemeral / local on the
  executor** state (neutral color on the format; `LocalBadge`/`RetencaoHint` on the state). The
  panel **does not switch workspaces**: it follows the `current` of the `WorkspaceContext` (the
  person's default, or the last one used). The `WorkspaceSwitcher` that lived at the top
  was removed by product decision and will come back later, somewhere else in the shell — since the
  `AppHeader` does not appear on `/` either, today the whole Home operates in a single scope.
  Clicking a geojson/published artifact puts it on the globe (the list queues the request in the store; the
  HomeView drains it into `useCamadas.adicionar`); a Drive file does not go to the globe
  in v1 — it opens the metadata. The ⋯ menu: show on the globe, download, metadata, delete
  (delete for editor+). Above 150 items the list becomes virtual
  (`@tanstack/react-virtual`).
- **The conversation in the center, and the panel on demand.** Every visit starts on the
  **hero**: the globe veiled toward the south, the headline ("Menos ferramentas. **Mais
  respostas.**" / "Pergunte em português. O Atlans escolhe os dados e monta cada
  etapa — você recebe o resultado." — "Fewer tools. More answers." / "Ask in Portuguese. Atlans
  picks the data and builds each step — you get the result.") and the large command bar in the center,
  with typed suggestions and chips. The headline exists to say that **choosing the
  operation is not the job of whoever is asking** — that is why the bar's placeholder and
  the panel's invitation are the same question ("O que você quer saber?" — "What do you want to
  know?"), and not a request for a command; changing one of them alone reopens the contradiction that the
  comment on `Primeira()` in `painel.tsx` records. **As soon as the person
  SENDS**, the bar slides down to the footer and the latest exchange appears above it, in the
  **strip** (`assistente/pilha.tsx`): the globe's caption, attached to the bar — the
  question on one line and, from the answer, only the latest text (cut at 4 lines),
  the errors, the cards, the quick replies and the step in progress; the rest stays in the
  panel. The trigger is the SEND (`agente.correndo`), not the first TEXT
  token: with the assistant querying the catalog and the WFS (several tools)
  before writing, waiting for the text left the bar stuck in the center for
  seconds, without loading the dialog (usage report). While the assistant
  thinks, the pending item (strip and panel) shows the site's **animated brand**
  (`assistente/marca-animada.tsx`: three nodes, without the orange background; still and
  whole under `prefers-reduced-motion`), **and the footer bar shows the current
  STEP** (`assistente/etapa.tsx`): "Pensando…" (Thinking…), or the tool in progress with the
  panel's label ("Consultando o guia · edges" — "Consulting the guide · edges"); it goes away when the
  answer starts being written, because by then it already appears in the strip. The movements
  are few and short — the flash on send, the cursor in the paragraph being
  written, the pop of the layer card, the strip sliding to the side on
  expanding and the panel coming in from the right — and all of them drop to zero under
  `prefers-reduced-motion`. **Expandir** (Expand),
  the chevron or Ctrl+I take the
  whole conversation to the floating panel (`assistente/painel.tsx`, a fork of the editor's
  drawer); "Recolher" (Collapse) goes back to the center. The decisions are in
  `docs/home-refactor.md`. `useAgente` (a fork of `useAssistente`) consumes the SSE from
  `/assistente`: `enviar` (`POST /conversa`), `confirmar` (`POST /confirmacoes`, the 2nd
  stream of the click) and `carregar` (the replay). The new frames (`fluxo`/`camada`/
  `confirmacao`) are additive in `web/app/components/home/assistente/quadros.ts` — the editor ignores them.
- **The delivery reaches the globe**: each `camada` frame becomes a fetch from
  `GET /assistente/camadas/{id}` (`useCamadas`) and a `MapLayer` — GeoJSON through the
  pre-signed URL (in memory; 25 MB ceiling) or MVT tiles of a published layer.
  The same artifact appears in THREE views, which do not duplicate each other: the
  inline `CartaoCamada` is the "it got onto the globe" moment and **scrolls** with the conversation;
  the **badge strip**, between the header and the scroll, is the fixed index of what the
  whole conversation produced, and clicking one puts it on the globe (through the `homeStore` queue,
  same as the Artefatos list); the **layers panel** (corner of the globe) is what
  is on the globe NOW, with eye, zoom-to-fit, **download** and remove. The workflows the
  assistant created do not appear anywhere on the Home.
- **Downloading from the layers panel itself**, without going to look for the same file in the
  Artefatos list. The icon appears on hovering the row (where there IS a mouse:
  on touch it is permanent, and keyboard focus always reveals it), and **only when the
  server said there is a file** — `GlobeLayer.baixavel`, which is different from
  `available`: a published layer appears on the globe with its content in PostGIS and
  may not have a file in storage, and an artifact marked `keepLocal` never leaves the
  executor. In both cases the download would respond 409/404, and a live button that fails is
  worse than an absent button. What downloads is `lib/baixar-artefato`, a single path for
  the three screens that need it.

### The sidebar

- **The edge resizes.** It always showed `cursor-w-resize` and only knew how to
  **collapse** — whoever dragged it to read the full name of an artifact saw the
  bar close in their face. Now, when expanded, it is a separator
  (`role="separator"`, the WAI-ARIA window splitter pattern): dragging resizes between
  180 and 480 px, ←/→ adjust from the keyboard (with Shift, in larger steps),
  Home/End go to the limits and double-click returns to 256 px. **Collapsed**, it
  remains the button that expands, which is the only way back from the 3rem rail
  from there; collapsing stays in the header's `SidebarTrigger` and in Ctrl/Cmd+B.
- **The width survives F5**, in the same mold as the collapsed state: a cookie
  (`sidebar_width`) that the layout reads **on the server** and returns as
  `defaultWidth`. In `localStorage` the bar would be born at 16 rem and jump on the
  first effect. The value is sanitized in the provider, so a tampered cookie does not
  stretch anything.
- **The artifact name is cut IN THE MIDDLE**, not at the end (`NomeDeArquivo`).
  `truncate` ate precisely the version and the extension: in a list of `…_v1`,
  `…_v2`, `…_v3` every row became the same prefix. The cut snaps to the nearest
  separator (`_`, `-`, `.`) so as not to split a word in the middle, and the
  `data-nome` carries the whole name for whoever needs it as a single value.
  This applies to FILE NAMES; a conversation title is prose, and there the cut at the end
  is still right.

### The Home without a session and the sign-in modal

The Home **opens without login**: globe, hero (title, sentence, the bar with the typed
suggestions and the chips) — all in view, and **no request** goes out (the `useAgente`
does not query `/assistente/estado` when `anonimo`; the sidebar does not mount the
Meu group; the `WorkspaceContext` and the `ActiveRunsContext` were already idle without a
session). The anonymous sidebar shows the brand, the collapse trigger, the **catalog
showcase** and, in the footer, **Entrar** (Sign in) and **Criar conta** (Create account).

- **The showcase** (`CatalogShowcase`, in `home-sidebar.tsx`) takes up the body that
  used to be the invitation "Entre para ver seus chats, artefatos e agendamentos." (Sign in to see your
  chats, artifacts and schedules.): the size of the catalog (25,492 layers, 76 institutions, 11
  countries) and three sliding ribbons of acronyms — two from Brazil and one of the countries, under the labels
  BRASIL and OUTSIDER DO BRASIL (BRAZIL and OUTSIDE BRAZIL). The change is one of argument: verifiable proof in place of
  a feature promise, and the vocabulary of someone who has already hunted for a WFS by hand in
  place of three words that a newcomer does not know.
  The numbers and the names are CONSTANTS in `web/lib/catalogo.ts` — the anonymous
  shell makes no request —, pinned to the `catalogo/geoservicos/` seed by
  `tests/unit/test_vitrine_do_catalogo.py`, which recomputes everything and fails stating the
  new number. The ribbons stop completely under `prefers-reduced-motion`
  (`.home-fita`, in globals.css), and the group disappears on the 3rem rail.

- **The first send asks for sign-in.** Enter, "Enviar" (Send) or a chip + Enter open
  the **sign-in modal** (`web/app/components/home/entrada/`) over the globe, in the
  Home theme (`home-portal`) and with the background slightly dimmed; the message stays
  **pending** (`homeStore.envioPendente`) and the text remains in the bar. The modal is
  **dismissible** (Esc, X, click outside — not during a send): closing without signing in
  gives up the send, and the text stays in the bar.
- **A successful login does not navigate**: next-auth's `signIn` (without redirect)
  writes the cookie and updates the tab's `useSession`; the Home queries `/estado` and
  **sends the pending message on its own** (respecting an exhausted quota, as the
  bar does). With a `callbackUrl` (the admin who requested `/projects` without a session) the person
  goes there, without sending anything.
- **Registration** is a panel of the same modal; once the account is created, the modal switches to
  "Verifique seu e-mail" (Check your email) (with the link resend) — the account requires verifying the
  email before the first login, and the message stays waiting in the bar.
- **Email verification belongs to the same panel**, `verificar`. Without a token it is the
  "open the link in the email" screen, with the resend
  (`POST /auth/resend-verification`); **with** the token from the link it spends it on
  `GET /auth/verify-email`, activates the account and goes back to the login already with the notice. The
  token is good ONCE per modal (it stays in the URL after being spent): going back to the
  panel — through the login's 403, or through the "Reenviar" (Resend) of a failure — gives the
  resend screen, not a second GET with a link that is no longer valid. The "Reenviar e-mail de
  verificação" (Resend verification email) of the 403 error is a BUTTON, and carries what was typed when that
  is already an email (the field accepts email OR username).
- **The password path also belongs to the modal**, in the `recuperar` ("Esqueceu
  a senha?" — "Forgot your password?", `POST /auth/forgot-password`) and `redefinir` ("Nova senha" — "New
  password", `POST /auth/reset-password` with the token from the email) panels. The login's "Esqueceu a senha?"
  is a BUTTON that switches panels, not a link: navigating would take the user out
  of the Home and throw away the pending message. The success of the request is shown
  even when the server refuses — saying "this email does not exist" would give away
  who has an account here, and the backend already responds the same way in both cases.
- **The email panels** (`verificar`, `recuperar`, `redefinir`) **open WITH
  or WITHOUT a session**, unlike `entrar` and `cadastro`: whoever forgot their password
  — or has not yet verified their email — often has an old session in the same
  browser, and the link lands there; with the `anonimo` gate applying to everyone,
  that link opened the Home and did nothing. For the same reason a session that arrives
  midway does not close them: the token is single-use. There is a single rule, in
  `ehPainelDeEmail` (`web/lib/entrada.ts`).
- **The routes.** `/login`, `/register`, `/verify-email`, `/forgot-password` and
  `/reset-password` became redirects to `/?entrar=1`, `/?cadastro=1`,
  `/?verificar=1&token=…`, `/?recuperar=1` and `/?redefinir=1&token=…`
  (`web/lib/entrada.ts`; only an internal `callbackUrl` passes through). The last three
  stay up because that is what is written in the emails **already sent**; without a token,
  `/reset-password` falls into the panel that asks for a new link and `/verify-email` into the
  resend screen. **No screen of this flow is a page anymore**: with the
  verification went the last `AuthShell`, and the shell left the code. The middleware sends to sign-in
  anyone who requests a page without a session or with an expired session. On `/` the middleware
  **never redirects** — not even with an expired session, which the `SessionSync` clears on the
  client (redirecting it to a destination inside the matcher would be a loop);
  at that moment the Home and the sidebar treat it as anonymous. Signing out lands on the anonymous
  Home.

## What it does differently from the editor

- **The delivery is a layer on the globe**, not a drawing on the canvas. The assistant
  creates and runs its OWN workflows (marked `origem="assistente"` by the
  identity) WITHOUT a click — that is how the answer reaches the globe — and puts a
  run output on the globe with `exibir_no_globo`.
- **Its workflows appear across the whole dashboard, with a badge.** Projects, Dashboard,
  History, the palette (⌘K) and the editor's sub-workflow picker list the assistant's
  workflows alongside the others, always with the spark badge
  (`shared/selo-assistente.tsx`) — before, they only appeared in the Home's Agendamentos
  (Schedules) and went unnoticed. The "only the assistant's" view is a chip on the
  two list screens: `/projects?filtro=assistente` (a local predicate) and
  `/observability?assistente=1` (which becomes `workflow_origem=assistente` in
  `GET /observability/runs`, and a local filter in the "Por workflow" (By workflow) view). The
  default of `GET /workflows` still HIDES THEM: whoever wants them includes
  `assistente=1` — which is what these screens now do.
- **Quick replies.** When finishing an answer that opens a natural follow-up,
  the assistant calls `sugerir_respostas` (the second local tool; up to three
  short sentences, as the person would say them) and they appear as chips under the
  answer, in the strip and in the panel; the click sends the sentence as the next
  message, and the new turn takes the chips off the screen.
- **Full reach, with click confirmation.** It has the six
  PAT scopes (`assistant_scope`). What holds back destructive actions is not the absence of a
  scope: it is the **confirmation gate verified on the server**. Editing/running a
  workflow the person created, touching a schedule, deleting a Drive file,
  publishing, restoring, turning on/off — all of this asks for a click.
- **Persisted conversations**, several per person, with no expiry (the
  `conversas` and `mensagens` tables), in place of the editor's transcript in Redis with a 24 h
  TTL.
- **Catalog before hunting.** For external data (WFS) the playbook says to
  call `search_sources` and `describe_source` BEFORE anything else — the
  source comes pre-mapped from the catalog (`docs/sources.md`), with no network and no guessing of
  `url`/`typeName`. Only when the catalog does not have the source does it probe
  (`probe_source`) and register (`register_source`) — both go through WITHOUT a click
  (`ESCRITAS_SEM_CLIQUE`): probing and storing a source is the normal way of working,
  not a destructive action.

## Dragging files to the Drive

The `/drive` screen has had the upload zone from the start, but the middleware sends
anyone who does not administer the system back to `/` (`web/proxy.ts`) — so, in practice, the
regular user never reached an upload field. The Home is their only page, and
the house rule sends every visual flow into it.

**The gesture.** Dragging one or more files onto any corner of the Home lights up the
**assistant box** (the visual target), and dropping them takes them to the Drive of the active
workspace. The area that ACCEPTS is the whole window (`useArrasteDeArquivos`, a global
listener); only the highlight belongs to the box — no veil covers the globe. The files become
**chips in the box** (`anexos.tsx`): a spinner while they upload, a ✓ when they arrive.

**The message carries what was uploaded.** Sending a question with finished attachments appends
to the text the line "Arquivos que acabei de enviar ao Drive deste workspace: …" (Files I just
sent to this workspace's Drive: …) (`comReferencia`) — without it, "analise isso" (analyze this)
reaches the assistant without any "this"
(it sees the workspace through `list_drive_files`, but does not know WHICH files are
the ones for this question). Only the FINISHED ones are cited and only they leave the box on send;
what is still uploading stays (it was not in the message) and so does what was refused (it never had
anything to do with it). With a finished attachment, the box starts suggesting "Analise <arquivo>"
(Analyze <file>) in place of the hero's sentences.

**The filters are the backend's, and they are not rewritten.** Allowed extension,
dangerous inner extension (`notas.sh.csv`), MB ceiling and empty file all live
in `drive_service.py`/`drive_router.py`, apply to any upload
path, and this path sends to the same `POST /drive/upload`. The refusal is translated
with the SAME `classifyUploadError` as the `/drive` screen and shown in the SAME panel
(`UploadResult`), in a notice separate from the chips — the refused file does not enter the
message, and leaving it in the row would make the person send the question thinking it
went. The only check done BEFORE uploading is the role in the workspace
(`useWorkspace().canEdit`, the mirror of the `editor` role that the Drive requires): uploading a
whole file to collect a predictable 403 is a waste of network. Without a session,
dropping opens the sign-in modal — the same door as the first send.

**State in the store, not in the component.** The attachments and `arrastando` live in the
`homeStore`, for the same reason as the draft: Ctrl+I swaps the bar for the panel and
UNMOUNTS whatever was on screen — in a `useState` of the box, the chips would disappear on the
shortcut with the uploads still running. That is why the bar AND the panel mount the
same pieces (finding 4 of the 3rd review: a feature on one surface and not on the
other is a promise that disappears depending on the screen).

## Routes

All of them require a JWT session (the PAT is for external clients, which talk through `/mcp`).

| | |
|---|---|
| `POST /assistente/conversa` | `{mensagem, conversa_id?, workspace_id?}` → `text/event-stream`. A null `conversa_id` creates a new conversation; the 1st frame returns id, title and `nova` |
| `POST /assistente/conversas/{id}/confirmacoes/{tool_use_id}` | `{token, decisao}` → `text/event-stream`. Executes (or refuses) an action and RESUMES the conversation in the same stream |
| `GET /assistente/conversas?limit&offset` | my non-deleted conversations, most recently active on top (`updated_at`, stamped at the end of each turn and on rename). `limit` is clipped at **100 without warning**; `offset` is free |
| `GET /assistente/conversas/{id}` | the **replay** of the conversation, in frames (for the panel to reapply) |
| `PATCH /assistente/conversas/{id}` | `{titulo}` — rename |
| `DELETE /assistente/conversas/{id}` | soft delete (204): it leaves the list, the history stays |
| `GET /assistente/estado` | `{ativo, motivo?, cota?, plano, assinaturas_ativas}` — the quota is the SAME as the editor's; without the extension, `plano` is `null` and `assinaturas_ativas` is `false` |

`GET /assistente/camadas/{id}` and `GET /assistente/tiles/…` (the globe's layers) live in the
`assistente_camadas_router` and have a MEMBER gate — they are not conversation.

## The SSE frames

The editor's vocabulary plus four: `conversa` (the first, always), `fluxo`,
`camada` and `respostas_rapidas`. The editor's (`pensando`, `texto`, `cota`, `ferramenta`,
`progresso`, `ferramenta_fim`, `erro`, `fim`) apply the same way; `proposta` (the canvas)
does not appear.

| `event` | `data` | when |
|---|---|---|
| `conversa` | `{conversa_id, titulo, nova}` | **always the first** of `POST /conversa` — the client learns the id of a new conversation |
| `fluxo` | `{workflow_id, nome}` | a `create_workflow` by the assistant succeeded. **It is not rendered**: the Home offers no path to the editor. It stays in the contract because the server emits it and the replay rebuilds it |
| `camada` | `{artifact_id, nome?, format?, available, hint?}` | a GeoJSON output of a run, or an `exibir_no_globo`. It is a POINTER; the truth is `GET /assistente/camadas/{id}` |
| `confirmacao` | `{tool_use_id, token, acao{tool, argumentos, alvo}}` | an action that touches what already existed waits for the click |
| `respostas_rapidas` | `{opcoes: [até 3 frases]}` | a `sugerir_respostas` by the assistant: short follow-ups that the person picks with a click (they become their next message). They are good only for that one time — the web only draws them on the last turn, outside the stream; the replay brings them back as long as they are the last turn's |

The `fim` is always the last, even when something went wrong — as in the editor. A `: ping`
(an SSE comment, ignored by the decoder) goes out every 15 s of silence, so that
the stream does not die behind a proxy during a long run.

## The confirmation, from the inside

Never by text. The Home's gate intercepts the confirmable call, stores
`{token, tool, args}` in Redis for 15 min under
`agente:confirmacao:{user}:{conversa}:{tool_use_id}`, emits the
`confirmacao` frame and returns to the model a NON-error "waiting" `tool_result` — an
error would make the model repeat the call and duplicate the button. The prompt tells the
model to say one line and end the turn.

The click (`POST /conversas/{id}/confirmacoes/{tool_use_id}`) **validates** in the
handler, in order:

1. **ownership** — the conversation belongs to the person (otherwise 404);
2. **existence** — the key is still in Redis (otherwise 409, it expired);
3. **token** — `hmac.compare_digest` with the stored token (otherwise 403).

The **consumption** (the one-shot `delete`) is NOT done in the handler: it lives in the
stream generator, **under the lock** and immediately before executing. If the client drops
between the handler's return and the effect running, the confirmation survives and can be
redone — consuming it in the handler would erase it even without the action having happened, and the
confirmed action would be lost with no retry. The lock serializes the tabs, so the
`delete` still decides the race: whoever deleted executes (`delete` = 1), whoever arrived
later loses (`delete` = 0, and an error frame closes the stream).

Then it executes the **STORED** arguments — never the ones the client sends with the
click — through `chamar_no_servidor`, under the assistant's scope, injects a
server-generated user message (`[Ação confirmada pela pessoa pelo
botão]…`, or `[Ação recusada pela pessoa]`) and **resumes** the loop in the same SSE. The
synthetic message is recorded with `meta={"tipo":"confirmacao",…}`.

**The `[Ação` prefix belongs to the server.** A typed message that starts with it is
refused with 422 (`POST /conversa`) — otherwise someone could forge "the person confirmed".

## Persistence

The transcript lives in the **database**, not on the client — the same reason as the editor: a
`tool_result` is the server's word, and a client that stored the transcript
could rewrite it. `POST /conversa` accepts **only** the new message
(`extra="forbid"`), and records it in the handler (before the stream). The assistant's
turns are recorded **incrementally**, turn by turn, through the loop's
`ao_fechar_turno` hook — not in a blob at the end. Closing the tab midway does not lose
what has already come.

- `conversas` — id, owner (FK `users`), context workspace/workflow (optional),
  title, origin, `tokens_total`, dates, `deleted_at` (soft delete).
- `mensagens` — `ordem` unique per conversation, role, `blocos` (the content VERBATIM
  in the form the API accepts back), `meta` (the confirmation mark).

`mensagens.blocos` stores even the `signature` of the reasoning block: without
it, the API refuses the next round on resumption.

## The replay

`GET /assistente/conversas/{id}` returns the conversation in the **same SSE frames**,
for the panel to reapply through the same path as a live frame. Two rules:

- a `tool_result` **never** goes out (it is the server's word, not screen
  content); the `fluxo`/`camada` of a run — and the `respostas_rapidas` of a
  `sugerir_respostas` — are rebuilt by the Home's same `quadros_extras`,
  matching each `tool_use` with its result;
- a `confirmacao` only reappears **with the token** if its key still exists in
  Redis — a vanished key (decided or expired) does not become a dead button.

## Known limits

- **The quota is shared with the editor** (`assistente:tokens:{user}`): the model is
  the same, the budget per person is a single one. Without `OPENROUTER_API_KEY`, `POST` responds
  503 and `GET /estado` responds `ativo:false` — never 404.
- **Without Redis there is no confirmation and no lock**: a confirmable action is refused
  closed (there is no way to store the token to validate the click). It is the degradation of the
  rest of the platform — the API does not even start without Redis.
- **Dragging a file with the assistant unavailable does not show the chips.** The
  box (bar or panel) is what draws the attachments; while `/estado` loads
  it gives way to a notice, and if it failed (`ativo:false`, 502) the box does not mount.
  The upload to the Drive is independent and HAPPENS anyway — the file
  appears on the `/drive` screen —, but the feedback on the Home only shows up when/if the box
  comes back. The case is narrow: without the assistant, nothing else on the Home works either.
- **The attachments belong to the session, not to the conversation.** An F5 loses the `File` (and the chips
  still in `enviando`); what has already been uploaded is in the Drive. Switching conversations does not
  clear the chips — they are "what I just dropped", not part of the history.
  **Switching WORKSPACES, however, does clear them:** the files went to the Drive of the
  previous workspace, and the message's reference matches the conversation's
  workspace — keeping them would point to files that the assistant of the new
  workspace cannot find.
- **No keyboard path.** Uploading is drag-only (the paperclip button is a
  follow-up). Someone who does not use a mouse cannot import files through the Home — it is not a
  regression (the `/drive` screen, which has the accessible field, is already unreachable for
  non-admins), but it is recorded as the next step.
- **Deploy does not run migrations.** When rolling out this version:
  `docker compose exec api-prod alembic upgrade head`.
