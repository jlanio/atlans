# Home refactor — decisions

Approved previewer: https://claude.ai/artifact/LKnVqCYZFXQYYh76aUXQZd (version 6).
Outside this document: everything that belongs to the map/globe (basemap, atmosphere, borders, labels).

| PR | scope | status |
|---|---|---|
| 1 | first-visit hero, highlighted bar, transition, conversation in the center (stack) | **applied** |
| 2 | quick replies and the animated mark on the pending item — **delivered** (2026-09-19); still pending: the mark on the bar icon and in the hero status, the shimmering verb and the timer; the interaction animations (§6) came in right after | partial |
| 3 | scheduling and alert (cards, email through `SendEmail`, in-app notice) | pending |

## Goal

Improve the visuals when you open the site: the dialog bar highlighted, in the center, and the conversation
unfolding right there — without opening the side panel by default as before (`homeStore.painel` started
at `"aberto"`).

## 1. When the hero appears

- It is the **initial state of every visit to the site** (loading the page). It is not "the user's
  first time": no flag, no `localStorage`, no server query.
- It applies **also without login**: the Home opens anonymously with the same hero; the first send opens the sign-in
  modal (login/sign-up) over the globe, and the message goes out on its own when the login succeeds
  (`docs/assistant.md`, "The Home without a session and the sign-in modal").
- It ends at the **first visible token of the first reply** — text, error or card. Reasoning
  (`pensando`) and tool calls are still "processing": the bar stays in the center, with the
  status. *Decided in PR 1: the first token, and not the end of the reply — the bar slides away while the
  reply starts, which hides the latency.*
- Opening an old chat (replay) or the panel (Ctrl+I, chevron) also ends the hero: there is a conversation
  to read.
- Once ended, it does not come back during this page load. "Nova conversa" (New conversation) in the middle of the session falls into the normal layout,
  empty.

## 2. Hero layout

- The globe fills the screen with its northern part visible and a gradient toward the south until it fades out (`.home-veu`,
  an overlay that disappears in the transition).
- The globe **spins slowly** while the hero is on screen: half a degree per second westward, in
  linear 1 s steps (`giroLento` in `MapLibreMap`, as in the previewer). A gesture from the user
  pauses the spin for 2.5 s; with `prefers-reduced-motion` it does not spin. At the first token the spin stops
  and the map **returns to Brazil** (the Globe's `center`/`zoom`) in 900 ms, along with the bar.
- The bar sits in the **center**; above it, the title and the phrase the Home already used ("Peça uma análise
  espacial…" (Ask for a spatial analysis…)); below it, three suggestion chips.

## 3. Dialog bar

- More prominence: 56 px tall and 16 px text in the hero (footer: 44 px / 14 px), a discreet orange ring and
  glow, the icon in a tinted circle. On focus the glow rises a little.
- **Typed-out suggestions** in the field while it is empty, with a blinking orange cursor, cycling through
  four product phrases (`SUGGESTIONS` in `barra.tsx`). **Tab** accepts, **Enter** sends (empty
  sends the current suggestion); any key interrupts; deleting everything brings the suggestion back. Clickable
  chips fill in the field.
- After the first token, the **same element** slides to the footer and shrinks into today's
  bar — 900 ms, `cubic-bezier(.22,.9,.3,1)` (`.home-barra` in `globals.css`); no motion with
  `prefers-reduced-motion`.
- Sending **does not open the panel**: the conversation stays in the center. The chevron opens the side panel.

## 4. Conversation in the center

- A **strip** attached to the bar, in place of the panel — the globe's caption (product decision on
  2026-09-19, the previewer's Option 4; before it was a stack of loose text, with a gradient at the top and
  scrolling, and the reply slid upward during the stream). The strip is fixed, with a nearly
  black background, no gradient and no scrolling, and shows only the **last exchange** (2 items): the question on one line
  ("Você · …" (You · …), truncated, the full text in the `title`) and, from the reply, **what remained** — the last
  text cut to 4 lines, the errors and the cards — and **what is live** while the turn runs
  ("Trabalhando…" (Working…) or the step in progress). Reasoning, completed steps and earlier texts are left for
  the panel. Below the items, the footer: the "N mensagens anteriores" (N earlier messages) counter on the left and
  **Expandir** (Expand) on the right.
- **Expandir** (a link in the stack, the bar's chevron or **Ctrl+I**) takes everything to the side panel as it already
  did; the panel has its own field; "Recolher" (Collapse) goes back to the center. While the panel is open,
  the bar and the stack disappear.
- A single conversation model feeds both views: the stack is the same `Conversa` as the panel,
  clipped to the last turns, and the cards (confirmation, layer) come from the same hook
  (`useAssistantExtras`). Nothing is duplicated.
- The "panel open/collapsed" preference **is no longer saved** in the browser: the hero would ignore it
  anyway, and the panel became on-demand.
- The reply can bring **quick replies**: up to three chips under the text (`sugerir_respostas`,
  a local tool of the assistant; `respostas_rapidas` frame), in the strip and in the panel. They are valid only
  for that one time: only on the last turn and outside the stream; clicking sends the phrase as the next
  message and the new turn removes them from the screen; on replay, those of the last turn come back. (Delivered on
  2026-09-19, together with the animated mark on the pending item.)

## 5. Processing

- *PR 1:* while processing, the chips give way to a status line ("Trabalhando…" (Working…)) with "Esc para
  parar" (Esc to stop); **Esc actually cancels** (`agente.parar`), except from inside a dialog or menu, where the
  key already has an owner. The bar icon becomes the product's activity indicator (`ExecActivity`).
- The **animated mark** — the site's mark without the orange background, just the graph of three nodes and three lines
  in orange; a stroke travels each edge (n1 → n2 → n3 → n1) and lights up the node on arrival, a
  2.4 s cycle with a light breathing of the whole (`assistente/marca-animada.tsx`, CSS in `globals.css`;
  still and complete under `prefers-reduced-motion`) — **went into the conversation's pending item** (strip and
  panel), by product decision on 2026-09-19. The sidebar's static mark keeps two nodes.
- *Pending:* the same mark on the bar icon and in the hero's status line and, next to it, in the
  Claude Code style, the shimmering verb that changes every ~1.7 s ("Trabalhando…", the step in progress) and the
  timer.

## 6. Interaction animations (PR 2)

- **Delivered (2026-09-19):** on send, a terracotta ring flashes on the bar's box (`data-flash`, the
  `::after` of `.home-barra-caixa` — opacity only, because a `box-shadow` does not interpolate between lists
  of different sizes) and the send button sinks (`active:scale-90`, also in the panel).
- In the strip, **nothing slides**: the strip and each new message come in with just a short fade (the same
  duration token as the hero, zeroed by `prefers-reduced-motion`), and there is no exit animation — the
  text simply swaps. (Delivered with the strip on 2026-09-19; it replaces the slide with scaling and the upward
  fade planned here.)
- **Delivered:** the paragraph being written ends in a terracotta cursor (`cursorAoEscrever`
  of `Conversa`, the same `.home-caret` as the typed-out suggestion; it disappears when a tool follows it or the
  turn ends); the layer card pops when it arrives (`home-pop`, ~320 ms with overshoot).
- **Delivered:** when expanding to the side, the strip slides to the right and fades out, the bar fades out and
  the panel comes in from the right (~300 ms). The HomeView keeps the strip and the bar mounted for `SAIDA_MS`
  (`useSaida`) — without clicks and without stealing focus from the panel — and collapsing within that window cancels it.
  Everything zeroes under `prefers-reduced-motion` (the flash, of fixed duration, is turned off separately).

## 7. Scheduling and alert (PR 3)

- The reply to an analysis ends by offering scheduling: "Quer que eu rode isso todo dia e te
  avise — aqui e por e-mail — se passar de N?" (Want me to run this every day and let you know — here and by
  email — if it goes over N?), with the quick reply "Sim, agende e me avise" (Yes, schedule it and let me know).
- On accepting, the reply brings two cards: **Agendamento** (Schedule) (every day · 07:00 · active) and **Alerta** (Alert)
  (notice if > 500 fire hotspots · watching); the new item appears under **Agendamentos** (Schedules) in the sidebar.
- When the alert fires: a notification at the top of the globe (with "Ver no globo" (See on the globe) and close), an
  "Alerta disparado" (Alert triggered) message in the conversation and an **email through the `SendEmail` node** that already exists in the workflow, with a summary
  and a link. In real life, it fires on the next run.
- Where it fits: `schedule_service` + `execution_alert_service` with a workflow ending in
  `SendEmail`; the **in-app** notice is the new piece (channel to be decided: state polling or event).

## 8. Where it is in the code (PR 1)

- `components/home/index.tsx`: the `hero` state (initial, ends at the first token), the veil, the
  title, the transition and Esc.
- `assistente/barra.tsx`: the `hero`/`rodape` variants of the same element, the typed-out suggestions,
  the chips, the "Trabalhando…" status and the stop button.
- `assistente/pilha.tsx`: the last exchange in the center; `assistente/extras.tsx`: the cards, shared
  with the panel.
- `stores/homeStore.ts`: `painel` starts at `"barra"` and is not saved.
- `globals.css`, section "Home: o hero do primeiro acesso" (Home: the first-visit hero): the veil, the transitions and the stack.

## 9. Location on the globe — "find me and get me around"

Approved previewer: https://claude.ai/artifact/4zTeXh5ooRGmSe8NT3L5Hb (version 2).

MapLibre's location button on the Home globe, in **follow** mode: it shows the
user on the map and tracks them in real time as they move. It is the only map
control the Home gains besides the zoom/compass/scale that already existed.

Product decisions:

- **Click only** (option A). The browser requires a gesture to ask for permission,
  and pulling the location on its own at open time would be invasive. The permission prompt is the
  **browser's** (its look is not ours) and appears only the first time; once
  authorized, clicking locates directly.
- **Button in the top-right corner**, in the same discreet glass stack as the zoom and
  the compass — where the map controls already live. The conversation panel opens at the
  bottom right and does not cover it.
- **Locating takes over the globe**: the hero spin pauses and the "return to Brazil" does not
  fire while follow is active — otherwise the map would pull the user
  away at the very moment it found them.
- **Web only in v1.** In the desktop app the accuracy falls back to IP (no GPS); it stays
  turned off for now.

Where it is in the code:

- `components/share/MapLibreMap.tsx`: the `geolocalizar` prop (opt-in) adds the
  `GeolocateControl` (`trackUserLocation`), pauses the spin through a ref read in the loop,
  and `_cssDoMapa` repaints the active button and the user's dot in the brand color. The
  control's texts go into the `locale` in pt-BR.
- `components/home/globo.tsx`: passes `geolocalizar` — `/share` does not pass it, and
  so it does not get the control.
- `next.config.ts`: `Permissions-Policy: geolocation=(self)` — without it the site
  itself is forbidden from asking for the location.

## 10. Location in the assistant — "analysis near me"

Approved previewers: the flow (https://claude.ai/artifact/QK4bRnBzUqBrvszfsJmnR5)
and the button position (https://claude.ai/artifact/8PjQ2Ra49t7N3WY2vA8zci).

The globe's location (§9) now **enters the conversation**: the coordinate becomes a
removable chip in the composer and travels with the turn, and the assistant uses it as a reference
point for relative requests ("near me", "within a radius of N km").

Product decisions:

- **The coordinate comes in through a "+" menu, not an always-visible button** (option
  **B'**). Since the composer had no "+" at all (attaching was drag-and-drop only), the
  new "+" gives a discoverable home to BOTH actions: "Anexar arquivo" (Attach file) (the same path
  as dragging) and "Usar minha localização" (Use my location). One menu, and not two loose buttons, so as
  not to bloat the bar's pill.
- **The state stays in sight and under control**: the chip shows the coordinate and the accuracy
  and goes away on the ×; exact accuracy is the default ("aproximar" (approximate) was left as a follow-up).
- **A single source**: "Usar minha localização" triggers the SAME `GeolocateControl` as the
  globe (via `localizar()` on the handle), so the map also follows the user; the
  `geolocate` event passes the coordinate up. It holds while set — the next turns
  carry it without relocating.

Adjustments from the adversarial review (same day, before the PR):

- **Intent ≠ position.** `compartilharLocalizacao` is separate state: the × turns off
  the intent and it STAYS off — before, the next tick of follow mode
  rewrote the position and the chip came back to life on its own, sending back the
  coordinate the user had just removed.
- **The globe's native button is once again only "find me on the map"**: it updates the
  last position, but does NOT attach anything to the conversation — only the gesture on the "+" attaches.
- **`localizar()` never toggles to OFF**: MapLibre's `trigger()` is a
  toggle (when already following, it silently turned off tracking); when already active, the handle
  only re-emits the last position.
- **The confirmation resends the coordinate** (`ConfirmationDecision.localizacao`): the
  resumption of the loop does not forget the "near me" — the server does not store the
  position (it lives only in the stream's prompt, never in the transcript).
- **Denied permission releases the hero spin** (MapLibre does not emit
  `trackuserlocationend` on that error) **and becomes a toast** — the control's button is
  hidden behind the panel on a phone. Going to the background state (dragging) does NOT
  give the spin back: the watch stays alive at high zoom.
- **Hysteresis of ~25 m** on the position: the jitter of a stationary GPS does not change the prompt
  text (history cache) nor re-render the composers on every tick.

Where it is in the code:

- `components/share/MapLibreMap.tsx`: the `aoLocalizar` prop (the `geolocate` event →
  `{ lat, lon, precisao_m }`) and `localizar()` on the handle (triggers the control from outside
  the map).
- `components/home/assistente/mais.tsx`: `BotaoMais` (the "+" menu) and
  `ChipDeLocalizacao` — mounted by the bar and by the panel.
- `stores/homeStore.ts`: `localizacao` + `definirLocalizacao`/`limparLocalizacao`
  (in the store for the same reason as `rascunho`/attachments: Ctrl+I swaps the surfaces).
- `hooks/home/useAssistente.ts`: reads the location through a ref and includes it in the turn's
  body only when set (without it, the body is the usual one).
- Backend: `schemas/assistente.py` (`Localizacao` + a field in `HomeMessage`),
  `api/routers/assistente_router.py` (`_extra_location`, folded into
  `instrucoes_extras` as the workspace already was) and `services/assistente_superficie.py`
  (one line teaching the model to use the location in relative requests).

Follow-ups: one-tap "aproximar (~1 km)" (approximate) for those who do not want a pinpointed location;
location in the desktop app (it stays web-only in v1, like §9).

## 11. Languages and region — the Home in English and Spanish

Request: the Home in pt-BR, English and Spanish, chosen automatically by the
region of whoever visits, with a fixed choice in "Preferências" (Preferences) — and the globe
starting (and returning) at the user's region, no longer always in South America.

**Which language** (`lib/idioma.ts`, resolved in the dashboard layout, on the server —
the first paint already comes out in the right language):

1. the choice in "Preferências" (`idioma` cookie, 365 days, the same model as the theme);
2. the browser's `Accept-Language`, honoring the `q` weights — it is the most
   faithful signal of what the user READS;
3. the connection's country (`CF-IPCountry`): Portuguese-speaking → pt-BR, Spanish-speaking → es,
   the rest → en — only when the browser sent an `Accept-Language` with
   none of the three languages;
4. without `Accept-Language`, pt-BR: every browser sends it, and whoever does not is
   a search crawler or a script (Googlebot comes from the US and would index the Home in
   English); with it, but with none of the three languages and no useful country, en.

In "Preferências", "Automático" (Automatic) is a real option (it deletes the cookie and shows the
detected language); the change takes effect immediately, without reloading. A `router.refresh()`
brings back the choice the server read — if the cookie changed in another tab, the screen, the
cookie and "Preferências" agree again.

**Only the Home is translated.** `ScopeByRoute` limits translation to the `/` route: the
administration area (editor, projects, admin) stays in Portuguese, and the components
shared with it — the account menu, the editor assistant's conversation,
the password field — do not end up half in each language. Without a provider (tests, the
`/share` portal), Portuguese applies.

**The texts** live in `components/home/i18n/secoes/` (shell, assistant,
sign-in, lists), with Portuguese as the template: `en` and `es` are `typeof pt`, so
a missing key is a compile error. The Portuguese stayed byte-for-byte what it was before,
with one deliberate exception: the source catalog's four tools
(`search_sources`, `describe_source`, `probe_source`, `register_source`), which
showed up in the timeline with the raw API name, got a label ("Procurando
fontes de dados" (Looking for data sources)…) — also in the editor assistant's conversation, which uses the
same `Conversa`. Components from outside the Home that it uses got a texts prop
with Portuguese as the default (the map, the Drive rejections panel, the dialog's X,
the sidebar's screen-reader labels, the width rail).

The app shell (sidebar, header, account, "Preferências", the lists in
"Meus" (Mine)) lives in the dashboard layout, which EVERY route loads — and it imports the
texts from `i18n/da-casca` (common, shell, lists), not from the index. Through the index,
the layout chunk carried along the assistant and sign-in dictionaries, in
all three languages (~20 KB gzip), for the whole administration area; the route table of
`next build` does not show this. The `i18n-layout` test follows the layout's imports
and fails if it reaches the index again. The sidebar and the menu trigger
declare their own `lang`: they are siblings of the HomeView, and the `lang` of `<html>` only
changes in an effect, after hydration.

**What the server says.** The server only speaks Portuguese. In English and Spanish,
the FIXED rejections have text in the language, chosen by status: at login the
invalid credential (401), the unverified email (403 + `X-Error-Code`), the
unavailable account (the other 403s) and the lockout (429, with the minutes from
`Retry-After`); at sign-up the "already in use" (the only 400); in the email links
(verify, reset) the invalid token (400 and 404); the verification's "link resent";
and the notice that the assistant is turned off (the server's `motivo` is for
whoever administers). Translation by status applies only to a rejection that IS the
server's — the body of `http_exception_handler` (`error: "http_exception"`),
see `entrada/recusas.ts`: the 429 of the per-IP limiter is not a locked account
("too many attempts from this connection"), and the 502 of the `/terra` proxy, the unexpected 500
and a CDN's error page become the language's generic error, not
"this account cannot sign in" nor the proxy's Portuguese. The assistant's errors
with a known code too — the conversation locked by another tab
(`conversa_em_andamento`) and the
stream's `rate_limited` is the DAILY quota, and the route's own 429 got its own
code (`muitas_requisicoes`); the `loop_limit` frame carries the `teto` so the
sentence can cite the number. In Portuguese the server's message stays, the usual one.
What the server writes case by case stays as it came: the field-by-field
validation of the sign-up, a layer's hint, the reason a file was rejected, and
any error with an unknown code.

**The assistant replies in the screen's language.** The turn carries `idioma` (`en`/`es`;
absent in Portuguese) and the router adds a block to the prompt, after the installation's language
rule, saying that it applies in place of that one. The block goes in the
uncached EXTRA: the Portuguese prompt stays byte-for-byte the usual one. The
confirmation resends the language, as it already did with the location. Limitation: on an
installation with an `ASSISTENTE_IDIOMA` other than Portuguese, the screen in Portuguese
gets the reply in the installation's language — the turn in Portuguese does not carry
`idioma`, and the server has no way to ask for Portuguese (it was like this before too).

**The globe by region** (`components/home/mapa/regiao.ts`), without asking for permission:
the browser's time zone → the time zone's reference city (IANA table generated by
`web/scripts/gerar-fusos.mjs`); with no useful time zone, the connection's country — and the time zone
of privacy modes is not useful: "UTC", and the Iceland time zone that
Firefox with `resistFingerprinting`, Tor Browser and Mullvad Browser report
(only Iceland itself, through the connection's country, keeps it); then the continent from the time zone's name; finally the Brazil of
before. The latitude stays between 45° S and 50° N so the globe does not open at a pole. The
center is read once, on mount, and serves as the hero's start and return point. It is the
REGION that decides the globe, not the language: a Brazilian user with the screen in English
still sees Brazil.

Follow-ups: the preference is per browser (cookie) — syncing across
devices requires a column on the user; the run parameters dialog, the
extension modals and the emails stay in Portuguese; the titles of the map controls
(zoom, compass) are the ones from mount time — switching languages without reloading does not
update them.
