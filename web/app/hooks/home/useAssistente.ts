"use client"

// web/app/hooks/home/useAssistente.ts
//
// The consumer of the Home assistant's stream — sibling of `useAssistenteEditor`,
// with which it shares the stream reading (`home/assistente/stream.ts`). The
// differences: the route is `/assistente` (persisted conversation, keyed by
// `conversa_id` and not by workflow); the 1st `conversa` frame teaches the id of
// a new conversation; there is `carregar` (the replay) and `confirmar` (the 2nd
// SSE of the click). No `Authorization` for the same reason as the editor: the
// `/terra` proxy authenticates via the session cookie.

import { useCallback, useEffect, useRef, useState } from "react"

import { GisFlowService } from "@/service/GisFlowService"
import type { IAssistantState, IQuadroDoReplay } from "@/service/types"
import { useHomeStore } from "@/app/stores/homeStore"
import { useScreenLanguage } from "@/app/components/home/i18n"
import { API_URL } from "@/utils/env"
import {
  aplicarQuadro, emptyTurn,
  type SSEFrame, type AssistantTurn,
} from "@/app/components/home/assistente/quadros"
import {
  NO_CONNECTION, applyQuota, applyToTurn, erroDaResposta, lerQuadrosSSE, nextTurnId,
  type RouteErrors,
} from "@/app/components/home/assistente/stream"

/**
 * What happened to a confirmation decision. There are THREE cases, not a
 * boolean, because the card handles each one differently:
 * - `valeu`: the server accepted it (the response became a stream) — the card
 *   stays locked. Also applies to a "Parar" (stop) mid-stream: the key has
 *   already been consumed, and unlocking would reopen a card that can no
 *   longer be decided.
 * - `expirada`: 409 — the key had already been consumed or expired. It stays
 *   locked (clicking again would only yield another 409), with the microcopy
 *   that says so instead of "Decidido." (decided).
 * - `falhou`: the decision never took effect (transport, or an error that did
 *   not consume the key) — the card becomes clickable again, otherwise the
 *   action has no way at all to be redone.
 */
export type DecisionResult = "valeu" | "expirada" | "falhou"

export interface Agente {
  estado: IAssistantState | null
  consultando: boolean
  /**
   * The state query FAILED (network, 502, timeout). Distinct from `estado` with
   * `ativo: false`, which is "turned off in this installation": a two-second 502
   * must not be read as "the assistant does not exist here".
   */
  falhou: boolean
  /** Redoes the state query — the Home's "Tentar de novo" (try again). */
  reconsultar: () => void
  turnos: AssistantTurn[]
  /** The replay of the selected conversation is on its way. */
  carregandoReplay: boolean
  correndo: boolean
  enviar: (mensagem: string) => Promise<void>
  /** Tells the card what to do: lock, lock as expired, or unlock. */
  confirmar: (toolUseId: string, token: string, decisao: "confirmar" | "recusar") => Promise<DecisionResult>
  parar: () => void
}

interface Choices {
  /** A conversa selecionada (dos Chats); `null`/ausente = conversa nova. */
  conversaId?: string | null
  /** Preferred workspace for the workflows the assistant creates. */
  workspaceId?: string | null
  /**
   * Called when the conversation gets activity: on the 1st `conversa` frame of
   * each message (id, title, whether it was just born — the store learns the new
   * id) and when a confirmation is accepted (just the id: the 2nd SSE does not
   * emit `conversa`, but the server stamps `updated_at` when closing it).
   */
  onConversa?: (info: { id: string; titulo?: string; nova: boolean }) => void
  /**
   * Without a session: does not query `/estado` (it would become a 401 at the
   * proxy and the Home would show "não foi possível falar com o assistente"
   * (could not reach the assistant) in place of the bar) and leaves `estado`
   * null — the Home renders the bar, and the first send opens the sign-in
   * modal. When the session arrives (login in the modal, or in another tab),
   * the query goes out.
   */
  anonimo?: boolean
}

export function useAssistente({ conversaId, workspaceId, onConversa, anonimo = false }: Choices): Agente {
  const [estado, setAppState] = useState<IAssistantState | null>(null)
  const [consultando, setQuerying] = useState(true)
  const [falhou, setFailed] = useState(false)
  const [turnos, setTurns] = useState<AssistantTurn[]>([])
  const [carregandoReplay, setLoadingReplay] = useState(false)
  const [correndo, setRunning] = useState(false)
  const [tentativa, setAttempt] = useState(0)

  const abortRef = useRef<AbortController | null>(null)
  // The screen language goes with the turn (the assistant answers in it). By ref,
  // read at send time like the location: switching language does not recreate `enviar`.
  const screenLanguage = useScreenLanguage()
  const languageRef = useRef(screenLanguage)
  useEffect(() => { languageRef.current = screenLanguage }, [screenLanguage])
  /** The assistant turn being written — to mark it if it stops. */
  const currentTurnRef = useRef<string | null>(null)
  // The conversation currently ON SCREEN. Distinct from the prop: the prop changes
  // by external selection (Chats) AND by onConversa (new id) — only external selection reloads.
  const loadedRef = useRef<string | null | undefined>(undefined)
  const onConversationRef = useRef(onConversa)
  onConversationRef.current = onConversa

  // The service's `get()` never rejects: a 502 comes back as `success: false`
  // with `data` undefined. Reading only `data` turned the transient outage into
  // "assistant turned off" and made the panel AND the bar vanish, saying nothing.
  //
  // `anonimo` is in the deps on purpose: the SessionProvider hears the login done
  // in another tab (BroadcastChannel) and `status` becomes "authenticated" without
  // remounting anything — without the dep, the Home left anonymous mode with a
  // null `estado` and fell into the "não está disponível nesta instalação" (not
  // available in this installation) notice.
  useEffect(() => {
    if (anonimo) {
      setAppState(null)
      setFailed(false)
      setQuerying(false)
      return
    }
    let vivo = true
    setQuerying(true)
    GisFlowService.estadoDoAgente().then(({ success, data }) => {
      if (!vivo) return
      setFailed(!success || !data)
      if (success && data) setAppState(data)
      setQuerying(false)
    })
    return () => { vivo = false }
  }, [tentativa, anonimo])

  const reconsultar = useCallback(() => setAttempt((n) => n + 1), [])

  const parar = useCallback(() => {
    if (!abortRef.current) return
    abortRef.current.abort()
    abortRef.current = null
    // A turn cut off mid-sentence looks exactly like a completed one. Without
    // this mark the person thinks the answer is over — or that the execution
    // stopped, which is not true on the server side.
    if (currentTurnRef.current) {
      applyToTurn(setTurns, currentTurnRef.current, { evento: "erro", dados: INTERRUPTED })
      currentTurnRef.current = null
    }
    setRunning(false)
  }, [])

  // The stream has to die with the Home: without this, leaving for /projects kept
  // the `for(;;)` reading, the connection open and the server generating tokens
  // against the quota for a response nobody is going to read anymore.
  useEffect(() => () => { abortRef.current?.abort() }, [])

  const carregar = useCallback(async (id: string) => {
    parar()
    // Clear BEFORE the network trip: the panel kept drawing the previous
    // conversation while the replay was coming, and on a slow network you could
    // read and reply thinking you were already in the new chat.
    setTurns([])
    setLoadingReplay(true)
    const { success, data } = await GisFlowService.lerConversa(id)
    // Only apply if it is still the requested conversation (quick chat switch).
    if (loadedRef.current !== id) return
    setTurns(success && data ? reconstruirTurnos(data.quadros) : [])
    setLoadingReplay(false)
  }, [parar])

  // Conversation selection: reload the replay (or clear for a new one). An id that
  // came from onConversa (stream in progress) already matches carregadoRef → no reload.
  useEffect(() => {
    const alvo = conversaId ?? null
    if (alvo === loadedRef.current) return
    parar()
    loadedRef.current = alvo
    if (alvo) void carregar(alvo)
    else { setTurns([]); setLoadingReplay(false) }
  }, [conversaId, carregar, parar])

  const reloadQuota = useCallback(() => {
    void GisFlowService.estadoDoAgente().then(({ data }) => { if (data) setAppState(data) })
  }, [])

  /** Consumes an SSE from `/assistente`, applying the frames to the `turnId` turn. */
  const consumir = useCallback(async (resposta: Response, turnId: string) => {
    if (!resposta.ok || !resposta.body) {
      applyToTurn(setTurns, turnId, { evento: "erro", dados: await erroDaResposta(resposta, ROUTE_ERRORS) })
      return
    }
    const tratar = (quadro: SSEFrame) => {
      if (applyQuota(setAppState, quadro)) return
      if (quadro.evento === "conversa") {
        const id = String(quadro.dados.conversa_id ?? "")
        if (id) {
          // The new id is already the "loaded" one: keeps the echo selection from reloading.
          loadedRef.current = id
          onConversationRef.current?.({
            id,
            titulo: typeof quadro.dados.titulo === "string" ? quadro.dados.titulo : undefined,
            nova: quadro.dados.nova === true,
          })
        }
        return
      }
      applyToTurn(setTurns, turnId, quadro)
    }
    await lerQuadrosSSE(resposta.body, tratar)
  }, [])

  const enviar = useCallback(async (mensagem: string) => {
    const texto = mensagem.trim()
    if (!texto || abortRef.current) return

    const controle = new AbortController()
    abortRef.current = controle
    const turnId = nextTurnId()
    currentTurnRef.current = turnId
    setTurns((anteriores) => [
      ...anteriores,
      { id: nextTurnId(), papel: "user", texto, blocos: [] },
      emptyTurn(turnId),
    ])
    setRunning(true)

    try {
      // The location goes into the body only when the person SHARED it (the "+"
      // turns it on; the × turns it off) and there is a position. Read from the
      // store AT send time — neither prop nor ref: the position changes on every
      // tick of follow mode, and any subscription would recreate callbacks or
      // re-render the Home for nothing. Without it, the turn is byte for byte the
      // usual one.
      const corpo: Record<string, unknown> = {
        mensagem: texto,
        conversa_id: conversaId ?? null,
        workspace_id: workspaceId ?? null,
      }
      const { compartilharLocalizacao, localizacao } = useHomeStore.getState()
      if (compartilharLocalizacao && localizacao) corpo.localizacao = localizacao
      // In Portuguese the body stays byte for byte as before (the server's default).
      if (languageRef.current !== "pt-BR") corpo.idioma = languageRef.current
      const resposta = await fetch(`${API_URL}/assistente/conversa`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
        body: JSON.stringify(corpo),
        signal: controle.signal,
      })
      await consumir(resposta, turnId)
    } catch (erro) {
      if (!(erro instanceof DOMException && erro.name === "AbortError")) {
        applyToTurn(setTurns, turnId, { evento: "erro", dados: NO_CONNECTION })
      }
    } finally {
      if (abortRef.current === controle) abortRef.current = null
      if (currentTurnRef.current === turnId) currentTurnRef.current = null
      setRunning(false)
      reloadQuota()
    }
  }, [conversaId, workspaceId, consumir, reloadQuota])

  const confirmar = useCallback(async (
    toolUseId: string, token: string, decisao: "confirmar" | "recusar",
  ): Promise<DecisionResult> => {
    const id = loadedRef.current
    if (!id || abortRef.current) return "falhou"

    const controle = new AbortController()
    abortRef.current = controle
    const turnId = nextTurnId()
    currentTurnRef.current = turnId
    // A new assistant turn for the executed action and the resumed response.
    setTurns((anteriores) => [...anteriores, emptyTurn(turnId)])
    setRunning(true)

    // It stays OUTSIDE the try: when "Parar" aborts the stream read the decision
    // has already taken effect on the server, and this is the value the catch
    // returns. Reading `false` there unlocked a card whose key the server had
    // just consumed.
    let resultado: DecisionResult = "falhou"

    try {
      // The confirmation RESUMES the model's loop — and the resumption must still
      // know the "near me": the server does not store the coordinate (it lives
      // only in the stream's prompt), so the client resends it here, with the
      // same rule as the send (shared and present).
      const corpo: Record<string, unknown> = { token, decisao }
      const { compartilharLocalizacao, localizacao } = useHomeStore.getState()
      if (compartilharLocalizacao && localizacao) corpo.localizacao = localizacao
      if (languageRef.current !== "pt-BR") corpo.idioma = languageRef.current
      const resposta = await fetch(
        `${API_URL}/assistente/conversas/${encodeURIComponent(id)}/confirmacoes/${encodeURIComponent(toolUseId)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
          body: JSON.stringify(corpo),
          signal: controle.signal,
        },
      )
      // The decision "took" when the response became a stream. 409 is a separate
      // case: the key has ALREADY been consumed (or expired), so there is nothing
      // to redo — the card stays locked, just saying so. Other errors leave the
      // action undone, and then unlocking is the only way back.
      resultado = resposta.ok && resposta.body
        ? "valeu"
        : resposta.status === 409
          ? "expirada"
          : "falhou"
      // The accepted decision is activity in the conversation (the server stamps
      // `updated_at` when closing the stream): notify whoever lists, as the
      // `conversa` frame would — no title, just the id.
      if (resultado === "valeu") onConversationRef.current?.({ id, nova: false })
      await consumir(resposta, turnId)
      return resultado
    } catch (erro) {
      if (erro instanceof DOMException && erro.name === "AbortError") return resultado
      applyToTurn(setTurns, turnId, { evento: "erro", dados: NO_CONNECTION })
      return "falhou"
    } finally {
      if (abortRef.current === controle) abortRef.current = null
      if (currentTurnRef.current === turnId) currentTurnRef.current = null
      setRunning(false)
      reloadQuota()
    }
  }, [consumir, reloadQuota])

  return {
    estado, consultando, falhou, reconsultar,
    turnos, carregandoReplay, correndo, enviar, confirmar, parar,
  }
}

const INTERRUPTED = { code: "interrompida", message: "Resposta interrompida.", hint: "o que já foi disparado no servidor continua" }

/** The statuses that `/assistente` (and the confirmation) rejects before the stream.
 *  It is not the editor's table on purpose — see `erroDaResposta`. */
const ROUTE_ERRORS: RouteErrors = {
  403: { code: "token_invalido", message: "Esta confirmação não confere mais." },
  404: { code: "nao_encontrada", message: "Conversa não encontrada." },
  409: { code: "expirada", message: "A confirmação expirou ou já foi decidida." },
  422: { code: "rejeitada", message: "Mensagem recusada." },
  // It is not `rate_limited`: that code, in the stream, is the assistant's DAILY
  // quota — in English and Spanish the screen would say "wait a moment" to
  // someone who can only come back tomorrow.
  429: { code: "muitas_requisicoes", message: "Muitas mensagens em pouco tempo. Espere um instante." },
  503: { code: "desligado", message: "O assistente não está disponível nesta instalação." },
}

/** Rebuilds the turns from the replay frames (`GET /conversas/{id}`). */
export function reconstruirTurnos(quadros: IQuadroDoReplay[]): AssistantTurn[] {
  const turnos: AssistantTurn[] = []
  let assistente: AssistantTurn | null = null

  for (const q of quadros) {
    const meta = q.dados?.meta as { tipo?: string } | undefined
    if (q.tipo === "usuario") {
      // A synthetic confirmation message (generated by the server) is not the
      // person speaking — it does not become a bubble. The assistant's reply to it stays below.
      if (meta?.tipo === "confirmacao") continue
      if (assistente) { turnos.push(assistente); assistente = null }
      turnos.push({ id: nextTurnId(), papel: "user", texto: String(q.dados.texto ?? ""), blocos: [] })
      continue
    }
    if (q.tipo === "conversa") continue // hook metadata, not a turn
    if (q.tipo === "fim") {
      if (assistente) assistente = aplicarQuadro(assistente, { evento: "fim", dados: q.dados })
      continue
    }
    if (!assistente) assistente = emptyTurn(nextTurnId())
    assistente = aplicarQuadro(assistente, { evento: q.tipo, dados: q.dados })
  }
  if (assistente) turnos.push(assistente)
  return turnos
}
