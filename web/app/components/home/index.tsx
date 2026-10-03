"use client"
import { useCallback, useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { useSession } from "next-auth/react"
import { TbAlertTriangle, TbRefresh } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import { cn } from "@/lib/utils"
import { usePrefereMenosMovimento } from "@/app/hooks/usePrefereMenosMovimento"
import { useWorkspace } from "@/context/WorkspaceContext"
import { useIsMobile } from "@/hooks/use-mobile"
import { useHomeStore } from "@/app/stores/homeStore"
import { useAssistente } from "@/app/hooks/home/useAssistente"
import { useAnexos } from "@/app/hooks/home/useAnexos"
import { useArrasteDeArquivos } from "@/app/hooks/home/useArrasteDeArquivos"
import { useCamadas } from "@/app/hooks/home/useCamadas"
import Globo from "./globo"
import Painel from "./assistente/painel"
import Barra from "./assistente/barra"
import { etapaDaConversa } from "./assistente/etapa"
import Pilha from "./assistente/pilha"
import PainelCamadas from "./painel-camadas"
import ModalDeEntrada from "./entrada/modal-de-entrada"
import { ehPainelDeEmail, type EntryMode } from "@/lib/entrada"
import { baixarArtefato } from "@/lib/baixar-artefato"
import { createToast } from "@/utils/createToast"
import { useScreenLanguage, useTexts } from "./i18n"

/** The bar takes 900 ms from the center to the footer and the veil 15% longer (globals.css). */
export const TRANSITION_DURATION_MS = 1050
/** A faixa e a barra saindo quando o painel abre: `--home-dur × .33` (globals.css). */
export const SAIDA_MS = 300

/**
 * The Home: the full-screen globe with the floating conversation over it.
 * `className="home dark"` on the root applies the near-black palette
 * (globals.css) and pins the dark theme — the Home is ALWAYS dark, regardless of
 * the app theme. It is full-bleed `h-svh` like the editor canvas; the AppHeader
 * returns null on `/`.
 *
 * This root is `relative` AND is the reference frame for the floating surfaces
 * (panel, bar, layers), which are `absolute` inside it: it starts after the
 * sidebar, so nothing else paints — or receives clicks — over it.
 *
 * The conversation lives in `useAssistente` (SSE from `/assistente`); the layers it puts on the
 * globe, in `useCamadas` (derived from the turns, with the active conversation's
 * lifecycle).
 *
 * The HERO is the initial state of every visit: the globe veiled toward the
 * south, the large bar in the center with typed suggestions and chips. It ends
 * at the first visible token of the first answer — the bar slides to the
 * footer, the veil disappears and the conversation's last exchange appears in
 * the center (the stack). The side panel is on demand.
 *
 * WITHOUT A SESSION the Home opens the same way (globe, hero, bar with the
 * suggestions and the chips) and makes no request at all: `useAssistente` does
 * not query `/estado` (`anonimo`) and the sidebar does not mount the lists. The
 * first submission opens the SIGN-IN MODAL (`entrada/`) over the globe, with the
 * pending message; a successful login swaps the tab's session without
 * navigating, the modal closes and the message goes out on its own — closing
 * the modal without signing in abandons it (the text stays in the bar).
 * `?entrar=1`/`?cadastro=1` (the destination of /login, /register and the
 * middleware) open the modal on arrival; `?verificar=1&token=…`,
 * `?recuperar=1` and `?redefinir=1&token=…` (the destinations of /verify-email,
 * /forgot-password and /reset-password) open the e-mail panels, with or
 * without a session; `callbackUrl` takes the admin back to the page they requested.
 */
export default function HomeView({
  entrada,
  tokenDoLink,
  callbackUrl,
  paisDaConexao,
}: {
  /** O modal de entrada nasce aberto neste painel (`?entrar=1`, `?redefinir=1`…). */
  entrada?: EntryMode
  /** The token from the e-mail link (`?redefinir=1&token=…`, `?verificar=1&token=…`). */
  tokenDoLink?: string
  /** Where to go after login (internal; comes sanitized from the page). */
  callbackUrl?: string
  /** The connection's country (`CF-IPCountry`): the globe's fallback when the browser hides the time zone. */
  paisDaConexao?: string | null
} = {}) {
  const conversaId = useHomeStore((s) => s.conversaId)
  const painel = useHomeStore((s) => s.painel)
  const hidratado = useHomeStore((s) => s.hidratado)
  const idioma = useScreenLanguage()
  const t = useTexts()
  const hidratar = useHomeStore((s) => s.hidratar)
  const alternar = useHomeStore((s) => s.alternarPainel)
  const selecionar = useHomeStore((s) => s.selecionarConversa)
  const pedidosDeCamada = useHomeStore((s) => s.pedidosDeCamada)
  const consumirFila = useHomeStore((s) => s.consumirFila)
  useEffect(() => { hidratar() }, [hidratar])

  // Without a session — or with an expired session, in the instant between this
  // render and SessionSync's `signOut` — the Home is the anonymous one: nothing
  // here may hit `/terra` (/estado would go out without a token, or with the
  // expired one, and become a 401). The SessionProvider receives the session from
  // the server (`null` included), so the status is known from the first render.
  const { data: sessao, status: sessionStatus } = useSession()
  const anonimo = sessionStatus === "unauthenticated" || sessao?.error === "RefreshTokenExpired"
  const router = useRouter()
  const requestedSignIn = useHomeStore((s) => s.entrada)
  const envioPendente = useHomeStore((s) => s.envioPendente)
  const pedirEntrada = useHomeStore((s) => s.pedirEntrada)
  const fecharEntrada = useHomeStore((s) => s.fecharEntrada)
  const concluirEntrada = useHomeStore((s) => s.concluirEntrada)
  const definirEnvioPendente = useHomeStore((s) => s.definirEnvioPendente)
  const definirRascunho = useHomeStore((s) => s.definirRascunho)
  // Location: the globe writes the latest position (aoLocalizar), the "+" turns
  // sharing on, the chip shows it and the × turns it off. HomeView does NOT
  // subscribe to the position — each follow-mode tick re-rendered the whole tree
  // (globe, stack, panel, bar) just to pass along a value useAssistente reads from
  // the store at send time. Only (stable) actions come in here.
  const definirLocalizacao = useHomeStore((s) => s.definirLocalizacao)
  const ligarLocalizacao = useHomeStore((s) => s.ligarLocalizacao)
  const limparLocalizacao = useHomeStore((s) => s.limparLocalizacao)

  // The page language for screen readers and hyphenation. The `lang` on the Home
  // root covers its tree; the one on <html> covers what Radix portals to <body>
  // (menus, dialogs) — and goes back to the previous one when the Home leaves,
  // because the rest of the app stays in Portuguese.
  useEffect(() => {
    const anterior = document.documentElement.lang
    document.documentElement.lang = idioma
    return () => { document.documentElement.lang = anterior }
  }, [idioma])
  // The location failure becomes a toast HERE because the only other signal is the
  // control button, in the corner of the globe — invisible on the phone with the panel open.
  const aoErroDeLocalizacao = useCallback((codigo: number) => {
    if (codigo === 1) {
      // Permission denied: the sharing request will not happen — turn it off so the
      // state does not stay armed waiting for a fix that never comes.
      limparLocalizacao()
      createToast.error(t.casca.localizacao.negada, t.casca.localizacao.negadaDica)
    } else {
      createToast.error(t.casca.localizacao.falhou, t.casca.localizacao.falhouDica)
    }
  }, [limparLocalizacao, t])

  const { current, canEdit } = useWorkspace()

  // ── Dragging files to the Drive ────────────────────────────────────────────
  // The whole window accepts the file; what lights up is the assistant's box
  // (`data-arraste`). The filters are the backend's — this path sends to the
  // same `POST /drive/upload` and translates the rejection. The state lives in the
  // store because Ctrl+I unmounts the bar and the chips would go with it.
  const definirArrastandoArquivo = useHomeStore((s) => s.definirArrastandoArquivo)
  const receiveAttachments = useAnexos({
    workspaceId: current?.id_hash ?? null,
    // `canEdit` mirrors the `editor` role the Drive requires: predicting the 403 spares
    // the network for those who are only readers. Anonymous is `false` here, but
    // `receber` already detours to login before looking at this.
    podeEnviar: canEdit,
    anonimo,
    aoExigirLogin: () => pedirEntrada("entrar"),
    aoAvisar: (titulo, detalhe) => createToast.error(titulo, detalhe),
  })
  useArrasteDeArquivos({
    // Without a session the drag is still listened to: dropping opens the login (the
    // same door as the first submission), instead of the browser opening the file.
    ativo: true,
    aoArrastar: definirArrastandoArquivo,
    aoSoltar: receiveAttachments.receber,
  })

  // Switching the active workspace empties the attachments: they are "what I just
  // sent to THIS workspace's Drive", and the message's reference matches the
  // conversation's workspace. Keeping them would point to files in another
  // Drive, which the new workspace's assistant does not find. Only on a SWITCH —
  // the initial null→ws (nothing to clear) does not count.
  const limparAnexos = useHomeStore((s) => s.limparAnexos)
  const workspaceAnterior = useRef(current?.id_hash ?? null)
  useEffect(() => {
    const agora = current?.id_hash ?? null
    if (workspaceAnterior.current !== null && workspaceAnterior.current !== agora) limparAnexos()
    workspaceAnterior.current = agora
  }, [current?.id_hash, limparAnexos])

  // The id the STREAM announced (1st `conversa` frame). Kept because it is what
  // distinguishes "the new conversation got an id" from "the person opened another
  // chat": in both cases `conversaId` goes from null to an id. It is a SINGLE-USE
  // marker: the comparison below consumes it. Kept forever, it came to mean
  // "any id the stream has already announced in this session", and reopening
  // that conversation from Chats later did not switch the layers' scope.
  const idDoStream = useRef<string | null>(null)
  const anunciar = useHomeStore((s) => s.anunciarConversa)
  const assistente = useAssistente({
    conversaId,
    workspaceId: current?.id_hash ?? null,
    // The whole announcement (id, title, new) goes to the store BEFORE the
    // selection: the Chats list, in the sidebar, inserts the row and
    // `aria-current` lights up on it in the same cycle. See `anunciarConversa`.
    onConversa: (info) => { anunciar(info); idDoStream.current = info.id; selecionar(info.id) },
    anonimo,
  })

  // The scope of the globe's layers: it changes when the person opens ANOTHER
  // conversation (or starts a new one), not when the ongoing conversation learns
  // its own id — then the layers on screen are its own.
  const escopo = useRef("nova:0")
  const previousConversation = useRef<string | null | undefined>(undefined)
  const novas = useRef(0)
  if (previousConversation.current !== conversaId) {
    const anunciado = idDoStream.current
    idDoStream.current = null // consumed: it holds for THIS switch, and only for it
    if (!conversaId || conversaId !== anunciado) {
      escopo.current = conversaId ?? `nova:${++novas.current}`
    }
    previousConversation.current = conversaId
  }

  const camadas = useCamadas(assistente.turnos, escopo.current)
  const { adicionar: addLayer } = camadas

  // The "+"'s "Usar minha localização" turns sharing on AND triggers the SAME
  // globe control (the corner button): the globe follows the person and
  // `geolocate` lifts the coordinate via `aoLocalizar`. The order matters: turn
  // on first, so the first fix already goes in shared. When already following,
  // `localizar()` only re-emits the last position (it never turns tracking off —
  // trigger is a toggle). `refMapa` is stable (useCamadas' useRef), so the
  // callback is not recreated.
  const refMapa = camadas.refMapa
  const requestLocation = useCallback(() => {
    ligarLocalizacao()
    refMapa.current?.localizar()
  }, [ligarLocalizacao, refMapa])

  // ── Sign-in: the first submission without a session ────────────────────────
  // The message stays pending, goes back to the box (the bar's submeter()
  // emptied it — empty in the hero, it would start typing the current
  // suggestion again) and the sign-in modal opens over the globe. When login
  // succeeds, it goes out on its own (the effect below). Closing the modal
  // without signing in abandons the submission, but the text stays in the bar.
  const requireLogin = useCallback((texto: string) => {
    definirRascunho(texto)
    definirEnvioPendente(texto)
    pedirEntrada("entrar")
  }, [definirRascunho, definirEnvioPendente, pedirEntrada])

  // `?entrar=1`/`?cadastro=1`: the modal starts open — once, and only without a
  // session (logged in, the query is ignored). The panels that come from an
  // E-MAIL LINK (password and verification) are the exception — see
  // `ehPainelDeEmail`, which explains why.
  const requestedFromUrl = useRef(false)
  const doEmail = ehPainelDeEmail(entrada)
  useEffect(() => {
    if (requestedFromUrl.current || !entrada || (!anonimo && !doEmail)) return
    requestedFromUrl.current = true
    pedirEntrada(entrada)
  }, [anonimo, entrada, doEmail, pedirEntrada])

  // The session arrived (via the modal, or via a login in another tab) with the
  // modal open: close it, keeping the pending message. The e-mail panels stay,
  // for the same reason — closing them from under someone using the link is
  // burning a single-use token.
  useEffect(() => {
    if (!anonimo && requestedSignIn && !ehPainelDeEmail(requestedSignIn)) concluirEntrada()
  }, [anonimo, requestedSignIn, concluirEntrada])

  // Login succeeded inside the modal. With `callbackUrl` (the admin who requested
  // /projects without a session) the person goes there — and the pending message
  // makes no sense outside the Home.
  const onSignIn = useCallback(() => {
    concluirEntrada()
    if (callbackUrl && callbackUrl !== "/") {
      definirEnvioPendente(null)
      router.push(callbackUrl)
      router.refresh()
    }
  }, [concluirEntrada, callbackUrl, definirEnvioPendente, router])

  // Sending on its own — an effect, not a callback: the login switches the status
  // to "authenticated" (signIn without redirect), `anonimo` drops, useAssistente
  // queries /estado and only THEN can it send. An exceeded quota follows the
  // bar's rule: the message stays in the box, with the notice.
  const { enviar: sendToAgent, correndo, parar, estado } = assistente
  useEffect(() => {
    if (anonimo || !envioPendente || correndo || estado?.ativo !== true) return
    const cota = estado.cota
    if (cota && cota.gasto >= cota.teto) return
    definirEnvioPendente(null)
    definirRascunho("")
    void sendToAgent(envioPendente)
  }, [anonimo, envioPendente, correndo, estado, sendToAgent, definirEnvioPendente, definirRascunho])

  // Logout done in another tab during a stream: the Home becomes anonymous without
  // remounting, and a stream that kept running would go against a session that
  // no longer exists. The conversation on screen stays until reload.
  useEffect(() => {
    if (anonimo) parar()
  }, [anonimo, parar])

  // ── The first-visit hero ───────────────────────────────────────────────────
  // Initial state of EVERY visit (page load), with no flag or localStorage. It
  // ends as soon as the person SENDS — the instant the stream starts
  // (`correndo`), and not only at the first visible token: the bar slides to the
  // footer and the strip loads already with the reasoning indicator (the
  // `Conversa` draws "Pensando" for the turn that has no block yet).
  //
  // Before, the trigger was the first TEXT token — reasoning and tools did not
  // count, and the bar stayed centered "processing". With the assistant querying
  // the catalog and WFS (several tools) before writing, that phase is long: the
  // bar looked stuck in the middle of the screen, without loading the dialog
  // (the owner's report). Sliding on send gives immediate feedback — the
  // question and "Pensando" appear in the strip, and the bar gets the "Parar".
  //
  // Replay (opening an old chat), the panel (Ctrl+I) and an artifact put on the
  // globe from the list also end it: in all three there is a conversation/layer
  // to see. Once ended it does not come back in this load — "nova conversa"
  // falls into the normal, empty layout.
  const [hero, setHero] = useState(true)
  const heroEnds =
    assistente.correndo || assistente.turnos.length > 0 || assistente.carregandoReplay ||
    painel === "aberto" || pedidosDeCamada.length > 0
  useEffect(() => {
    if (hero && heroEnds) setHero(false)
  }, [hero, heroEnds])

  // The title and the sentence leave the DOM after the transition, or immediately
  // without motion: mounted and invisible, they would be ghost focus targets.
  const reduceMotion = usePrefereMenosMovimento()
  const [heroInDom, setHeroInDom] = useState(true)
  useEffect(() => {
    if (hero) return
    if (reduceMotion) { setHeroInDom(false); return }
    const t = setTimeout(() => setHeroInDom(false), TRANSITION_DURATION_MS)
    return () => clearTimeout(t)
  }, [hero, reduceMotion])

  // Esc interrupts the answer in progress (the status's "Esc para parar"). Not from
  // inside a dialog or menu: there Esc already has an owner, and closing both at
  // once would be a surprise.
  useEffect(() => {
    if (!correndo) return
    function onEscape(e: KeyboardEvent) {
      if (e.key !== "Escape" || e.defaultPrevented) return
      const alvo = e.target as HTMLElement | null
      if (alvo?.closest?.('[role="dialog"], [role="menu"], [role="listbox"]')) return
      parar()
    }
    window.addEventListener("keydown", onEscape)
    return () => window.removeEventListener("keydown", onEscape)
  }, [correndo, parar])

  // Ctrl+I toggles open/bar. The effect lives HERE, not in the Painel: collapsing
  // unmounts the Painel, and the listener went with it — the shortcut advertised
  // in the tooltip itself ("Recolher (Ctrl+I)") only worked once and never reopened.
  //
  // There is no focus guard, and none is needed: the assistant field is the
  // cursor's default position on this screen, and blocking the shortcut there
  // would block it almost always. What the shortcut must not do is cost the text
  // already typed — that is why the draft lives in homeStore (shared by the panel
  // and the bar) and not in the `useState` of whatever the swap unmounts.
  useEffect(() => {
    function aoTeclar(e: KeyboardEvent) {
      if (!(e.ctrlKey || e.metaKey) || e.altKey) return
      if (e.key.toLowerCase() !== "i") return
      // Inside the sign-in modal (or any dialog) the shortcut does not
      // toggle the panel behind it.
      const alvo = e.target as HTMLElement | null
      if (alvo?.closest?.('[role="dialog"]')) return
      e.preventDefault()
      alternar()
    }
    window.addEventListener("keydown", aoTeclar)
    return () => window.removeEventListener("keydown", aoTeclar)
  }, [alternar])

  // Drains the "exibir no globo" requests the Artefatos list (in the sidebar)
  // enqueues: sidebar and globe are siblings in the tree, so the request goes
  // through the store. `adicionar` deduplicates (art:<id>), so a repeat only
  // re-frames. It consumes only what it dispatched — a click landing between the
  // render and the effect would be erased without ever reaching the globe.
  useEffect(() => {
    if (pedidosDeCamada.length === 0) return
    const dispatchedCount = pedidosDeCamada.length
    for (const p of pedidosDeCamada) void addLayer(p.artifactId, p.nome)
    consumirFila(dispatchedCount)
  }, [pedidosDeCamada, addLayer, consumirFila])

  // On the phone the panel is opaque and covers the whole screen: the new layer
  // was framed on the globe BEHIND it, and nothing said there was a result.
  // Collapsing to the bar shows the delivery; the "X no globo" card stays in the
  // conversation and the bar brings it back in one tap. Without saving the
  // preference — the screen was what decided.
  // Download a layer's source file, from the globe panel itself — without
  // going to look for the same thing in the Artefatos list. The panel only offers
  // the action when the server said there is a file (`baixavel`), so getting here
  // and failing is an exception, not routine: hence the toast instead of a row state.
  const downloadLayer = useCallback(async (artifactId: string, nome: string) => {
    const erro = await baixarArtefato(artifactId, t.listas.artefatos.download)
    if (erro) createToast.error(t.casca.baixarCamadaFalhou(nome), erro)
  }, [t])

  const isMobile = useIsMobile()
  const recolherBarra = useHomeStore((s) => s.recolherBarra)
  const layerCount = camadas.camadas.length
  const previousLayerCount = useRef(0)
  useEffect(() => {
    if (isMobile && layerCount > previousLayerCount.current) recolherBarra()
    previousLayerCount.current = layerCount
  }, [isMobile, layerCount, recolherBarra])

  // Toggling panel/bar unmounts whatever had focus and it falls to <body>. Only a
  // REQUESTED swap returns focus — on page load it would be focus theft.
  const previousPanel = useRef<string | null>(null)
  const autoFoco = previousPanel.current !== null && previousPanel.current !== painel
  if (hidratado) previousPanel.current = painel

  return (
    <div lang={idioma} className="home dark relative h-svh w-full overflow-hidden bg-background text-foreground">
      {/* The `<h1>` is what the screen reader announces first and what the search
          engine indexes — so it says what the page DOES, not what it shows. */}
      <h1 className="sr-only">{t.casca.titulo}</h1>

      {/* Spinning slowly in the hero; at the first token it returns to the opener's region (the Globo's `center`). */}
      <Globo
        layers={camadas.camadas}
        mapaRef={camadas.refMapa}
        girando={hero}
        pais={paisDaConexao}
        aoLocalizar={definirLocalizacao}
        aoErroDeLocalizacao={aoErroDeLocalizacao}
      />

      {/* The veil: the globe in view to the north, fading out toward the south. Disappears with the hero. */}
      <div className="home-veu" data-visivel={hero} aria-hidden="true" />
      {heroInDom && (
        <div className="home-hero-texto" data-visivel={hero} aria-hidden={!hero}>
          {/* The second half in the brand's terracotta (`--primary`, the same
              orange as the button and the focus ring): "Menos ferramentas"
              alone can read as a poorer platform, and it is the contrast
              between the halves that undoes that — they need to be seen as a
              pair, not as a sentence that continues. `text-wrap:balance`
              balances the lines when a narrow screen breaks the pair.

              Swapping the gray for it was the OWNER's call, and it has a
              measured cost: the terracotta (#e7723b) has almost the same
              luminance as the veiled cloud (#9e9c96), so over cloud the
              contrast drops from 1.64:1 to 1.11:1 — over ocean it RISES, from
              5.41:1 to 6.19:1. Neither reached WCAG's 3:1, and there what
              separates glyph from image is the halo, not the ratio; whoever
              needs the number has to change the BACKGROUND. See
              `.home-hero-texto` in globals.css. */}
          {/* Legibility over the satellite imagery (the halo) belongs to the CSS,
              not here: it needs `@supports`, which an arbitrary utility cannot
              express. See `.home-hero-texto h2, p` in globals.css. */}
          <h2 className="mb-2.5 text-[clamp(24px,3.2vw,32px)] font-semibold leading-[1.22] tracking-tight text-foreground [text-wrap:balance]">
            {t.casca.hero.antes} <span className="text-primary">{t.casca.hero.destaque}</span>
          </h2>
          <p className="mx-auto max-w-[48ch] text-[15px] text-[#c2c2c2]">
            {t.casca.hero.subtitulo}
          </p>
        </div>
      )}

      <PainelCamadas
        camadas={camadas.camadas}
        avisos={camadas.avisos}
        carregando={camadas.carregando}
        onAlternar={camadas.alternarVisivel}
        onRemover={camadas.remover}
        onEnquadrar={camadas.enquadrar}
        onDispensarAviso={camadas.dispensarAviso}
        onBaixar={downloadLayer}
      />

      <AssistantOrNotice
        assistente={assistente}
        painel={painel}
        autoFoco={autoFoco}
        hero={hero}
        anonimo={anonimo}
        enviar={anonimo ? requireLogin : assistente.enviar}
        aoAnexar={receiveAttachments.receber}
        aoPedirLocalizacao={requestLocation}
      />

      {/* The sign-in (login, sign-up, verification and the password path),
          portaled to <body> with the Home palette. */}
      <ModalDeEntrada
        modo={requestedSignIn}
        tokenDoLink={tokenDoLink}
        comEnvioPendente={envioPendente !== null}
        onFechar={fecharEntrada}
        onEntrou={onSignIn}
      />
    </div>
  )
}

/**
 * Panel, bar — or the reason there is neither.
 *
 * There are THREE states, and before there was only an `ativo === true` gate: a
 * two-second 502 on `/assistente/estado` left the person with the globe and literally
 * nothing else — no field, no notice, no "try again", and no way to tell
 * "disabled on this installation" from "the network went down".
 *
 * And a fourth, WITHOUT A SESSION: nothing was queried (`estado` null, on
 * purpose), and the bar shows up all the same — `enviar` there is the gate that
 * opens the sign-in modal, not the stream.
 */
function AssistantOrNotice({
  assistente, painel, autoFoco, hero, anonimo, enviar, aoAnexar, aoPedirLocalizacao,
}: {
  assistente: ReturnType<typeof useAssistente>
  painel: "aberto" | "barra"
  autoFoco: boolean
  hero: boolean
  /** Without a session: skips the notices and shows the bar; `enviar` is the login gate. */
  anonimo: boolean
  enviar: (mensagem: string) => Promise<void> | void
  /** Attaches files chosen in the "+" (the same path as dragging). */
  aoAnexar: (arquivos: File[]) => void
  /** Triggers the globe's location control (the "+"'s "Usar minha localização"). */
  aoPedirLocalizacao: () => void
}) {
  // Opening the panel does not unmount the strip and the bar right away: they stay
  // for a moment, leaving (the strip slides to the side, the bar fades out), while
  // the panel enters from the right. Without motion the delay is zero. Hooks
  // BEFORE the early returns below (the order must be the same on every render).
  const t = useTexts()
  const screenLanguage = useScreenLanguage()
  const reduceMotion = usePrefereMenosMovimento()
  const { montado: centerMounted, saindo } = useSaida(painel === "aberto", reduceMotion ? 0 : SAIDA_MS)

  // The height of the bar's extras (chips/invitation/rejected notice/step),
  // measured by it and passed to the strip as clearance: without it the bar would
  // grow upward and cover the strip's "Expandir" (the same bug as the quota pill).
  const [folgaExtras, setExtrasSlack] = useState(0)

  // The current step (reasoning or the tool in progress), for the bar to show in
  // the footer while the assistant works. `null` when stopped or writing.
  const etapa = etapaDaConversa(assistente.turnos, assistente.correndo, screenLanguage)

  if (!anonimo) {
    if (assistente.consultando) {
      return (
        <div
          className={cn(
            "absolute left-1/2 z-30 w-[min(560px,calc(100%-2rem))] -translate-x-1/2 animate-pulse rounded-full border border-border bg-background/60 pb-safe",
            hero ? "top-1/2 h-14 -translate-y-1/2" : "bottom-6 h-11",
          )}
          aria-hidden="true"
        />
      )
    }

    if (assistente.falhou) {
      return (
        <Aviso
          texto={t.casca.assistenteFalhou}
          acao={<Button size="sm" variant="outline" className="gap-1.5 max-md:h-10" onClick={assistente.reconsultar}>
            <TbRefresh size={14} aria-hidden="true" /> {t.comum.tentarDeNovo}
          </Button>}
        />
      )
    }

    if (assistente.estado?.ativo !== true) {
      // The server's `motivo` is for administrators, and in Portuguese ("defina
      // OPENROUTER_API_KEY"): in the other languages the dictionary notice applies.
      const motivo = screenLanguage === "pt-BR" ? assistente.estado?.motivo : null
      return <Aviso texto={motivo || t.casca.assistenteIndisponivel} />
    }
  }

  return (
    <>
      {painel === "aberto" && (
        <Painel
          estado={assistente.estado}
          turnos={assistente.turnos}
          correndo={assistente.correndo}
          carregandoReplay={assistente.carregandoReplay}
          autoFoco={autoFoco}
          enviar={enviar}
          confirmar={assistente.confirmar}
          parar={assistente.parar}
          aoAnexar={aoAnexar}
          aoPedirLocalizacao={aoPedirLocalizacao}
        />
      )}
      {centerMounted && (
        <>
          {/* The last exchange in the center. Not during the hero: there what you see is the status. */}
          {!hero && (
            <Pilha
              turnos={assistente.turnos}
              correndo={assistente.correndo}
              confirmar={assistente.confirmar}
              enviar={enviar}
              saindo={saindo}
              // With the quota exceeded the bar grows upward (the amber pill) and
              // would cover the strip's footer — the strip moves up with it (the
              // covered "Expandir" bug, the owner's screenshot from 2026-09-19).
              comAvisoDeCota={
                assistente.estado?.cota != null && assistente.estado.cota.gasto >= assistente.estado.cota.teto
              }
              // The attachment chips and the rejected notice grow the bar upward
              // the same way; the clearance is MEASURED because their height
              // varies (they wrap, the rejected card is tall).
              folgaExtras={folgaExtras}
            />
          )}
          <Barra
            enviar={enviar}
            correndo={assistente.correndo}
            estado={assistente.estado}
            // While leaving, the bar must NOT take focus: its effect runs after the
            // panel's (sibling order) and would steal the cursor just placed there.
            autoFoco={autoFoco && !saindo}
            variante={hero ? "hero" : "rodape"}
            parar={assistente.parar}
            saindo={saindo}
            aoMedirExtras={setExtrasSlack}
            etapa={etapa}
            aoAnexar={aoAnexar}
            aoPedirLocalizacao={aoPedirLocalizacao}
          />
        </>
      )}
    </>
  )
}

/**
 * The animated exit of the strip and the bar when the panel opens: both stay
 * mounted for `ms` with `saindo` on (the CSS slides and fades), and only then
 * unmount. Opening and collapsing within the delay cancels — the timer is
 * cleared and they stay, without `saindo`. With `ms = 0` (no motion) they
 * unmount on the next tick, with no visible frame. They start unmounted if the
 * panel is already open on mount.
 *
 * `saindo` is DERIVED (`aberto && montado`), not state: it holds already in the
 * render in which the panel opens. As state set by an effect it would arrive one
 * render later — and in that render the bar would still receive `autoFoco` and
 * steal focus from the freshly mounted panel.
 */
function useSaida(aberto: boolean, ms: number): { montado: boolean; saindo: boolean } {
  const [montado, setMounted] = useState(!aberto)
  useEffect(() => {
    if (!aberto) {
      setMounted(true)
      return
    }
    if (!montado) return
    const timer = setTimeout(() => setMounted(false), ms)
    return () => clearTimeout(timer)
  }, [aberto, montado, ms])
  return { montado, saindo: aberto && montado }
}

/** In place of the command bar, with the same framing. */
function Aviso({ texto, acao }: { texto: string; acao?: React.ReactNode }) {
  return (
    <div
      role="status"
      className="home dark absolute bottom-6 left-1/2 z-30 flex w-[min(560px,calc(100%-2rem))] -translate-x-1/2 items-center gap-2 rounded-full border border-border bg-background/95 px-4 py-2 pb-safe text-sm text-muted-foreground shadow-2xl backdrop-blur"
    >
      <TbAlertTriangle size={16} className="shrink-0 text-amber-400" aria-hidden="true" />
      <span className="min-w-0 flex-1">{texto}</span>
      {acao}
    </div>
  )
}
