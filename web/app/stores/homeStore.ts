import { create } from "zustand"
import type { ModoDeEntrada } from "@/lib/entrada"
import type { UploadErrorType } from "@/app/components/drive/resultado-upload"

/**
 * Home state shared by the shell (Chats in HomeSidebar), the floating panel and
 * the globe. In a store because these three have no cheap common ancestor —
 * HomeSidebar is a sibling of the panel in the shell tree, and the keyboard
 * shortcut lives in a global effect.
 *
 * - `conversaId`: the active conversation (highlighted in Chats; the panel opens
 *   it). Kept in memory — the selection belongs to the session, not a preference
 *   to remember.
 * - `painel`: "aberto" (the floating conversation on the side) or "barra" (the
 *   command bar, with the conversation's last exchange in the center). Starts at
 *   "barra" on EVERY visit — the panel is on demand (Ctrl+I, the chevron,
 *   "Expandir") — and is not saved: the preference went away along with the
 *   first-visit hero, which would ignore any remembered state.
 * - `pedidosDeCamada`: a QUEUE of "put this artifact on the globe" requests,
 *   written by the Artifacts list (in HomeSidebar) and drained by HomeView, which
 *   is the one that has `useCamadas`. A queue, not a single slot, so as not to
 *   lose quick clicks on different artifacts; HomeView consumes only what it
 *   dispatched. The layer state itself lives in `useCamadas` (in HomeView) — the
 *   store only carries the REQUEST from one sibling in the tree to the other,
 *   which have no cheap common ancestor.
 * - `decididos`: the confirmations already clicked. Kept HERE, and not in the
 *   panel, because collapsing the panel unmounts it and the turns (with the
 *   token) survive: keeping the decision in the component left the card
 *   clickable again on reopen, and the second click hits an already consumed
 *   token (409).
 * - `expirados`: the confirmations the server refused with 409 (key already
 *   consumed or expired). They stay decided — there is nothing to redo —, except
 *   that the card swaps "Decidido." (decided) for the microcopy that explains why.
 * - `rascunho`: the assistant text being edited, shared by the panel and the
 *   bar. Kept HERE because Ctrl+I swaps one for the other and UNMOUNTS whichever
 *   was on screen: in a `useState` of each box, the shortcut erased what had
 *   already been typed. In memory — a draft belongs to the session, not a
 *   preference to save.
 * - `meu`: which items of HomeSidebar's Meu (mine) group (Agendamentos,
 *   Artefatos, Chats) are open. Persisted in `atlans:home:meu` because, in a
 *   `useState` of the item, the open/closed state died every time the drawer
 *   opened on the phone (the Sheet unmounts its children on close), when leaving
 *   `/` and coming back (the shell switches sidebar) and when crossing 768px —
 *   and the person reopened everything again.
 * - `anuncioDeConversa`: the last "this conversation got activity" that the
 *   assistant stream announced — the 1st `conversa` frame of each message (id,
 *   title, whether it is new) and the accepted confirmation. The Chats list lives
 *   in HomeSidebar, a SIBLING of HomeView: this is how it finds out, without a GET.
 *   It is a SLOT, and not a queue like `pedidosDeCamada`: the list may be
 *   unmounted (the phone drawer closed) and a queue would grow with nobody to
 *   drain it. The slot holds a NEW object on each announcement, and the list
 *   compares identity with what already existed when it mounted — the mount load
 *   brings the truth. In memory.
 * - `entrada`: the requested sign-in modal (login/sign-up) — by the bar, on the
 *   first send without a session, or by HomeSidebar's Entrar/Criar conta (sign
 *   in/create account) buttons, a sibling of HomeView in the tree (the same
 *   reason as `pedidosDeCamada`). `null` = closed. In memory.
 * - `envioPendente`: the message that the first send without a session left
 *   waiting for login — HomeView sends it on its own when the session arrives.
 *   Closing the modal without signing in discards it (the text stays in
 *   `rascunho`, visible in the bar); completing sign-in keeps it. In memory:
 *   firing a stored message on an F5 would be a surprise.
 * - `anexos` and `arrastandoArquivo`: the files dropped on the Home, on their way
 *   to the workspace Drive. Kept HERE for the same reason as `rascunho`: Ctrl+I
 *   swaps the bar for the panel and UNMOUNTS whichever was on screen — in a
 *   `useState` of the box, the chips (and the `arrastando` that lights up the
 *   box) vanished on the shortcut, while the uploads kept running with nothing on
 *   screen. In memory: an F5 loses the `File` anyway, and what has already been
 *   uploaded is in the Drive.
 */

const CHAVE_MEU = "atlans:home:meu"

type Painel = "aberto" | "barra"

/** The three items of the Meu group, in the order they appear in the bar. */
export type ItemDoMeu = "agendamentos" | "artefatos" | "chats"
export type EstadoDoMeu = Record<ItemDoMeu, boolean>
/** The usual: only Chats starts open. Also the SSR default. */
export const MEU_PADRAO: EstadoDoMeu = { agendamentos: false, artefatos: false, chats: true }

/** A request to show an artifact on the globe. `nome` is the suggested label. */
export interface PedidoDeCamada {
  artifactId: string
  nome?: string
}

/**
 * "This conversation got activity": the 1st `conversa` frame of each message
 * (id, title, whether it was just born) or an accepted confirmation (only the
 * id). The same shape as the `info` of `useAssistente`'s `onConversa`.
 */
export interface AnuncioDeConversa {
  id: string
  titulo?: string
  nova: boolean
}

/** Where a file dropped on the Home is on its journey to the Drive. */
export type EstadoDoAnexo = "enviando" | "pronto" | "recusado"

/**
 * A file dropped on the Home.
 *
 * `recusado` is always the SERVER's verdict — the Drive filters (allowed
 * extension, dangerous inner extension, MB ceiling, empty file, role in the
 * workspace) all live there, and the client does not rewrite them. `motivo` is
 * the text the server returned and `tipo` is the classification from
 * `classifyUploadError`, the same as the `/drive` screen's — which is why the
 * two labels never diverge.
 */
export interface Anexo {
  /** Render key. It is not the Drive id: the file may never even get there. */
  id: string
  nome: string
  bytes: number
  estado: EstadoDoAnexo
  /** The detail the server returned, when `recusado`. */
  motivo?: string
  tipo?: UploadErrorType
}

/**
 * The person's LAST known position, coming from the MapLibre control on the
 * globe (the `geolocate` event). It is in the store for the same reason as
 * `rascunho`: the chip that shows it lives in BOTH composers (bar and panel), and
 * Ctrl+I unmounts whichever is on screen. In memory — it is the session's
 * physical position, not a preference to save, and an F5 relocates. The keys
 * mirror the body the backend receives.
 *
 * Position and INTENT are separate states on purpose: the globe writes the
 * position on every follow tick, but it only goes into the assistant turn when
 * `compartilharLocalizacao` is on — which ONLY a gesture by the person turns on
 * ("Usar minha localização" (use my location) in the "+") and the chip's ×
 * turns off. Without the separation, the next GPS tick undid the × on its own
 * and the coordinate went back into the turn with no gesture at all (finding
 * from the 2026-09-24 adversarial review).
 */
export interface Localizacao {
  lat: number
  lon: number
  /** Accuracy radius in meters (the browser's `accuracy`); `null` if absent. */
  precisao_m: number | null
}

/**
 * Reads the remembered Meu group. Starts from the default and only copies keys
 * whose value is boolean: a partial JSON (old version), corrupted or with junk
 * breaks nothing — it falls back to the default key by key.
 */
function meuLembrado(): EstadoDoMeu | null {
  if (typeof window === "undefined") return null
  try {
    const cru = window.localStorage.getItem(CHAVE_MEU)
    if (!cru) return null
    const lido: unknown = JSON.parse(cru)
    if (!lido || typeof lido !== "object") return null
    const meu = { ...MEU_PADRAO }
    for (const nome of Object.keys(MEU_PADRAO) as ItemDoMeu[]) {
      const valor = (lido as Record<string, unknown>)[nome]
      if (typeof valor === "boolean") meu[nome] = valor
    }
    return meu
  } catch {
    return null
  }
}

function lembrarMeu(meu: EstadoDoMeu): void {
  try {
    window.localStorage.setItem(CHAVE_MEU, JSON.stringify(meu))
  } catch {
    /* disposable preference */
  }
}

interface HomeState {
  conversaId: string | null
  painel: Painel
  /** False until the hydration effect runs — before that, only the SSR default. */
  hidratado: boolean
  /** Pending "show on globe" requests, drained by HomeView. */
  pedidosDeCamada: PedidoDeCamada[]
  /** `tool_use_id` → decidido. Sobrevive a recolher/reabrir o painel. */
  decididos: Record<string, true>
  /** `tool_use_id` → the server answered 409: decided, but with no effect. */
  expirados: Record<string, true>
  /** The text being edited, shared by the panel and the bar. */
  rascunho: string
  /** Open/closed state of each item of the Meu group. Persisted in `atlans:home:meu`. */
  meu: EstadoDoMeu
  /** The stream's last announcement; `null` until the first message. See the header. */
  anuncioDeConversa: AnuncioDeConversa | null
  /** The requested sign-in modal (login or sign-up); `null` = closed. */
  entrada: ModoDeEntrada | null
  /** The message of the first send without a session, waiting for login. */
  envioPendente: string | null
  /** The files dropped on the Home, in the order they arrived. */
  anexos: Anexo[]
  /** A drag WITH FILES is over the Home: the box lights up and invites. */
  arrastandoArquivo: boolean
  /** The LAST known position (from the globe); only goes into the turn with `compartilharLocalizacao`. */
  localizacao: Localizacao | null
  /** The person ASKED for the location to go into the conversation ("+ → Usar minha localização"); the × turns it off. */
  compartilharLocalizacao: boolean
}

interface HomeActions {
  selecionarConversa(id: string | null): void
  /** Starts a new conversation: clears the selection. The surface stays as it is. */
  novaConversa(): void
  abrirPainel(): void
  /** Collapses the panel into the bar (the conversation goes back to the center). */
  recolherBarra(): void
  alternarPainel(): void
  /**
   * Marks the end of SSR (from here on, switching surface returns focus) and
   * reads the Meu group remembered in the browser. Does NOT write.
   */
  hidratar(): void
  /** Queues an artifact for the globe (from the Artifacts list, in the sidebar). */
  pedirCamada(artifactId: string, nome?: string): void
  /**
   * Removes from the front of the queue the `n` requests already dispatched. It
   * is not `limparFila`: a click that landed between HomeView's render and its
   * effect would be erased without ever reaching the globe — the artifact simply
   * would not appear.
   */
  consumirFila(n: number): void
  /** Marks a confirmation as decided (the card locks). */
  marcarDecidido(toolUseId: string): void
  /** Returns the card to the clickable state — the confirmation failed on the server. */
  desmarcarDecidido(toolUseId: string): void
  /**
   * The key had already been consumed (or expired) when the click arrived: the
   * card STAYS locked — redoing it would only render another 409 —, and the
   * microcopy now says why.
   */
  marcarExpirado(toolUseId: string): void
  /** Stores the text being edited (panel and bar write to the same draft). */
  definirRascunho(texto: string): void
  /** Opens/closes an item of the Meu group and remembers the preference. */
  alternarItemDoMeu(nome: ItemDoMeu): void
  /** Opens an item of the Meu group (idempotent) — used by the click on the 3rem rail. */
  abrirItemDoMeu(nome: ItemDoMeu): void
  /** Records an announcement. Always a new object: identity is the contract. */
  anunciarConversa(anuncio: AnuncioDeConversa): void
  /** Opens the sign-in modal in the requested mode (the bar and the sidebar request it). */
  pedirEntrada(modo: ModoDeEntrada): void
  /**
   * Closes the modal WITHOUT signing in (Esc, X, click outside): gives up on the
   * pending send — a later login must not fire a forgotten message. The text
   * stays in `rascunho`.
   */
  fecharEntrada(): void
  /** Login succeeded: closes the modal and KEEPS the pending send for HomeView to send. */
  concluirEntrada(): void
  definirEnvioPendente(texto: string | null): void
  /** A drag with files entered the Home (or left it). */
  definirArrastandoArquivo(arrastando: boolean): void
  /** Queues the freshly dropped files, already in `enviando`. */
  adicionarAnexos(novos: Anexo[]): void
  /** An attachment's upload finished (or was refused): fixes its row. */
  atualizarAnexo(id: string, mudanca: Partial<Omit<Anexo, "id">>): void
  /** The chip's ×. Deletes nothing from the Drive — only removes it from the bar. */
  removerAnexo(id: string): void
  /**
   * The message was sent: the READY ones leave (the reference to them already
   * traveled along). The ones still uploading stay, because they were not in the
   * message; the refused ones too, because they never had anything to do with it
   * and the person still needs to read the reason.
   */
  limparAnexosProntos(): void
  /** Closes the warning about the refused ones. */
  descartarAnexosRecusados(): void
  /**
   * Empties the whole list — used when the active WORKSPACE changes: the
   * attachments are "what I just sent to THIS workspace's Drive", and the
   * message's reference (`comReferencia`) matches the conversation's workspace.
   * Once the workspace changes, the chips would point to files that are in
   * another Drive — the new workspace's assistant cannot find them.
   */
  limparAnexos(): void
  /** Stores the last known position (from the globe's `geolocate` event). Does NOT turn on sharing. */
  definirLocalizacao(loc: Localizacao): void
  /** The "+" gesture: the location starts going into the turns. */
  ligarLocalizacao(): void
  /**
   * The chip's ×: the location LEAVES the conversation and STAYS out — the follow
   * ticks keep updating the position, but nothing goes back into the turn until a
   * new gesture. Does not turn off follow on the globe and does not erase the last
   * position (turning it back on via "+" comes back at once, without waiting for
   * a new GPS fix).
   */
  limparLocalizacao(): void
}

export const useHomeStore = create<HomeState & HomeActions>((set) => ({
  conversaId: null,
  painel: "barra",
  hidratado: false,
  pedidosDeCamada: [],
  decididos: {},
  expirados: {},
  rascunho: "",
  meu: MEU_PADRAO,
  anuncioDeConversa: null,
  entrada: null,
  envioPendente: null,
  anexos: [],
  arrastandoArquivo: false,
  localizacao: null,
  compartilharLocalizacao: false,

  // A conversation switch takes the decisions with it: the tokens belong to turns
  // that left the screen. A NEW id coming from the stream (null → id) is the SAME
  // conversation, but then there is no earlier decision to lose. The draft STAYS:
  // it is what the person just typed, and dropping it on a chat switch is losing
  // their text.
  selecionarConversa: (id) =>
    set((state) => (state.conversaId === id ? {} : { conversaId: id, decididos: {}, expirados: {} })),
  novaConversa: () => set(() => ({ conversaId: null, decididos: {}, expirados: {} })),

  abrirPainel: () => set(() => ({ painel: "aberto" })),
  recolherBarra: () => set(() => ({ painel: "barra" })),
  alternarPainel: () => set((state) => ({ painel: state.painel === "aberto" ? "barra" : "aberto" })),

  // Reads the Meu group remembered in the browser. Does NOT write: only the
  // person's gesture writes. `painel` is not included: it starts at "barra" on
  // every visit (the hero).
  hidratar: () => set(() => ({ meu: meuLembrado() ?? MEU_PADRAO, hidratado: true })),

  pedirCamada: (artifactId, nome) =>
    set((state) => ({ pedidosDeCamada: [...state.pedidosDeCamada, { artifactId, nome }] })),
  consumirFila: (n) =>
    set((state) => (n <= 0 ? {} : { pedidosDeCamada: state.pedidosDeCamada.slice(n) })),

  marcarDecidido: (toolUseId) =>
    set((state) => ({ decididos: { ...state.decididos, [toolUseId]: true } })),
  desmarcarDecidido: (toolUseId) =>
    set((state) => {
      if (!(toolUseId in state.decididos)) return {}
      const copia = { ...state.decididos }
      delete copia[toolUseId]
      return { decididos: copia }
    }),
  marcarExpirado: (toolUseId) =>
    set((state) => ({
      decididos: { ...state.decididos, [toolUseId]: true },
      expirados: { ...state.expirados, [toolUseId]: true },
    })),

  definirRascunho: (texto) => set(() => ({ rascunho: texto })),

  alternarItemDoMeu: (nome) =>
    set((state) => {
      const meu = { ...state.meu, [nome]: !state.meu[nome] }
      lembrarMeu(meu)
      return { meu }
    }),
  abrirItemDoMeu: (nome) =>
    set((state) => {
      if (state.meu[nome]) return {}
      const meu = { ...state.meu, [nome]: true }
      lembrarMeu(meu)
      return { meu }
    }),

  // Always a new object, even with the same id: the Chats list only reacts to
  // identity changes, and "the same conversation got another message" IS another
  // announcement.
  anunciarConversa: (anuncio) => set(() => ({ anuncioDeConversa: { ...anuncio } })),

  pedirEntrada: (modo) => set(() => ({ entrada: modo })),
  fecharEntrada: () => set(() => ({ entrada: null, envioPendente: null })),
  concluirEntrada: () => set(() => ({ entrada: null })),
  definirEnvioPendente: (texto) => set(() => ({ envioPendente: texto })),

  definirArrastandoArquivo: (arrastando) =>
    set((state) => (state.arrastandoArquivo === arrastando ? {} : { arrastandoArquivo: arrastando })),

  adicionarAnexos: (novos) =>
    set((state) => (novos.length === 0 ? {} : { anexos: [...state.anexos, ...novos] })),

  // By id, not by index: uploads finish out of order and the person may remove
  // a chip midway.
  atualizarAnexo: (id, mudanca) =>
    set((state) => {
      if (!state.anexos.some((a) => a.id === id)) return {}
      return { anexos: state.anexos.map((a) => (a.id === id ? { ...a, ...mudanca } : a)) }
    }),

  removerAnexo: (id) =>
    set((state) => {
      const anexos = state.anexos.filter((a) => a.id !== id)
      return anexos.length === state.anexos.length ? {} : { anexos }
    }),

  limparAnexosProntos: () =>
    set((state) => {
      const anexos = state.anexos.filter((a) => a.estado !== "pronto")
      return anexos.length === state.anexos.length ? {} : { anexos }
    }),

  descartarAnexosRecusados: () =>
    set((state) => {
      const anexos = state.anexos.filter((a) => a.estado !== "recusado")
      return anexos.length === state.anexos.length ? {} : { anexos }
    }),

  limparAnexos: () => set((state) => (state.anexos.length === 0 ? {} : { anexos: [] })),

  // The globe's `geolocate` fires on every position update (follow mode).
  // Hysteresis of ~25 m (0.00025° ≈ 25 m at the equator): the GPS jitter of
  // someone STANDING STILL does not change the value — which stabilizes the text
  // that goes into the prompt between turns (otherwise every message invalidated
  // the history cache) and spares a chip re-render —, and a real displacement
  // updates normally. A clear improvement in accuracy also passes (the first
  // coarse IP/wifi fix becomes the fine GPS one even without moving).
  definirLocalizacao: (loc) =>
    set((state) => {
      const a = state.localizacao
      if (a) {
        const parado = Math.abs(a.lat - loc.lat) < 0.00025 && Math.abs(a.lon - loc.lon) < 0.00025
        const precisaoMelhorou =
          loc.precisao_m != null && (a.precisao_m == null || loc.precisao_m < a.precisao_m / 2)
        if (parado && !precisaoMelhorou) return {}
      }
      return { localizacao: loc }
    }),
  ligarLocalizacao: () => set((s) => (s.compartilharLocalizacao ? {} : { compartilharLocalizacao: true })),
  // Turns off ONLY the intent: the position stays as the last known one. That is
  // what makes the × persist — before, with the value zeroed, the next follow tick
  // rewrote it and the chip came back to life on its own.
  limparLocalizacao: () => set((s) => (s.compartilharLocalizacao ? { compartilharLocalizacao: false } : {})),
}))
