"use client"

// web/app/hooks/workflow/useAssistenteEditor.ts
//
// The assistant stream consumer and the conversation state machine.
//
// **It is not `EventSource`**: that is GET and sends no body, and the
// conversation needs one. And **it is not the `axios`** of `GisFlowService`:
// axios does not deliver a stream in the browser — `onDownloadProgress` returns
// the accumulated response, which is the same as waiting for the end. So
// `fetch` + `response.body.getReader()`, a new pattern in this web app (the only
// streaming today is WebSocket, in `useExecuteWorkflow.ts`). The reading itself
// — and whatever else is the same as the Home's — lives in
// `home/assistente/stream.ts`.
//
// **No `Authorization`, on purpose.** The route goes through the `/terra` proxy,
// which authenticates upstream with the SERVER's access token, renewed by the
// middleware, and IGNORES the client header (`app/terra/[...path]/route.ts`:63).
// Sending the token from here would authenticate nothing and would reintroduce
// the defect that comment records: in a long session, the client token ages and
// turns into a 401 in the backend without anyone having logged out.
import { useCallback, useEffect, useRef, useState } from "react"

import { GisFlowService } from "@/service/GisFlowService"
import type { IAssistenteEstado } from "@/service/types"
import { API_URL } from "@/utils/env"
import { turnoVazio, type TurnoDoAssistente } from "@/app/components/home/assistente/quadros"
import {
  SEM_CONEXAO,
  aplicarCota,
  aplicarNoTurno,
  erroDaResposta,
  lerQuadrosSSE,
  proximoIdDeTurno,
  type ErrosDaRota,
} from "@/app/components/home/assistente/stream"

/** The statuses that `/assistente/editor/conversa` refuses before the stream. It
 *  is not the Home's table on purpose — see `erroDaResposta`. */
const ERROS_DA_ROTA: ErrosDaRota = {
  409: { code: "conversa_em_andamento", message: "Já há uma conversa em andamento neste fluxo." },
  429: { code: "rate_limited", message: "Muitas mensagens em pouco tempo. Espere um instante." },
  503: { code: "desligado", message: "O assistente não está disponível nesta instalação." },
}

export interface Assistente {
  estado: IAssistenteEstado | null
  /** Until `GET /estado` comes back, the panel should not decide anything. */
  consultando: boolean
  turnos: TurnoDoAssistente[]
  correndo: boolean
  enviar: (mensagem: string) => Promise<void>
  parar: () => void
  esquecer: () => Promise<void>
}

/**
 * @param workflowId  the workflow open in the editor. Absent on the create
 *                    screen — the backend stores that conversation under the
 *                    key `novo`.
 */
export function useAssistenteEditor(workflowId?: string): Assistente {
  const [estado, setEstado] = useState<IAssistenteEstado | null>(null)
  const [consultando, setConsultando] = useState(true)
  const [turnos, setTurnos] = useState<TurnoDoAssistente[]>([])
  const [correndo, setCorrendo] = useState(false)

  const abortoRef = useRef<AbortController | null>(null)

  // Switching workflow means switching conversation: the previous workflow's
  // history has nothing to do with this one, and its stream must not keep
  // writing here.
  useEffect(() => {
    setTurnos([])
    setCorrendo(false)
    return () => {
      abortoRef.current?.abort()
      abortoRef.current = null
    }
  }, [workflowId])

  useEffect(() => {
    let vivo = true
    setConsultando(true)
    GisFlowService.estadoDoAssistente().then(({ data }) => {
      if (!vivo) return
      // A network error here is no reason to hide the panel forever; `null` lets
      // the caller treat "don't know" separately from "turned off".
      setEstado(data ?? null)
      setConsultando(false)
    })
    return () => {
      vivo = false
    }
  }, [])

  const parar = useCallback(() => {
    abortoRef.current?.abort()
    abortoRef.current = null
    setCorrendo(false)
  }, [])

  const enviar = useCallback(
    async (mensagem: string) => {
      const texto = mensagem.trim()
      if (!texto || abortoRef.current) return

      const controle = new AbortController()
      abortoRef.current = controle

      const idDoTurno = proximoIdDeTurno()
      setTurnos(anteriores => [
        ...anteriores,
        { id: proximoIdDeTurno(), papel: "user", texto, blocos: [] },
        turnoVazio(idDoTurno),
      ])
      setCorrendo(true)

      try {
        const resposta = await fetch(`${API_URL}/assistente/editor/conversa`, {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
          body: JSON.stringify({ mensagem: texto, workflow_id: workflowId ?? null }),
          signal: controle.signal,
        })

        if (!resposta.ok || !resposta.body) {
          aplicarNoTurno(setTurnos, idDoTurno, {
            evento: "erro",
            dados: await erroDaResposta(resposta, ERROS_DA_ROTA),
          })
          return
        }

        // The `cota` frame updates the state and does not enter the conversation.
        await lerQuadrosSSE(resposta.body, (quadro) => {
          if (!aplicarCota(setEstado, quadro)) aplicarNoTurno(setTurnos, idDoTurno, quadro)
        })
      } catch (erro) {
        // Stopping is the user's decision, not a failure: the turn stays as it is,
        // with whatever has already arrived.
        if (!(erro instanceof DOMException && erro.name === "AbortError")) {
          aplicarNoTurno(setTurnos, idDoTurno, { evento: "erro", dados: SEM_CONEXAO })
        }
      } finally {
        // The end of the turn is the closing of the STREAM, not the arrival of the
        // `fim` frame. A closed tab, a dropped connection or a proxy that gave up
        // end the conversation with no frame at all, and the panel cannot keep
        // spinning.
        if (abortoRef.current === controle) abortoRef.current = null
        setCorrendo(false)
        // The quota was charged during the turn. Without this re-read the panel
        // would forever show the spend as of mount, and the person would only
        // discover the ceiling by running into it.
        void GisFlowService.estadoDoAssistente().then(({ data }) => {
          if (data) setEstado(data)
        })
      }
    },
    [workflowId],
  )

  const esquecer = useCallback(async () => {
    parar()
    setTurnos([])
    await GisFlowService.esquecerConversaDoAssistente(workflowId)
  }, [parar, workflowId])

  return { estado, consultando, turnos, correndo, enviar, parar, esquecer }
}
