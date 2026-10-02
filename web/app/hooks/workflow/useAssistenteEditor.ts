"use client"

// web/app/hooks/workflow/useAssistenteEditor.ts
//
// O consumidor do stream do assistente e a máquina de estado da conversa.
//
// **Não é `EventSource`**: ele é GET e não manda corpo, e a conversa precisa de
// um. E **não é o `axios`** do `GisFlowService`: axios não entrega stream no
// navegador — o `onDownloadProgress` devolve a resposta acumulada, o que é a
// mesma coisa que esperar o fim. Então `fetch` + `response.body.getReader()`,
// padrão novo nesta web (o único streaming de hoje é WebSocket, em
// `useExecuteWorkflow.ts`). A leitura em si — e o que mais é igual ao da Home —
// mora em `home/assistente/stream.ts`.
//
// **Sem `Authorization` de propósito.** A rota passa pelo proxy `/terra`, que
// autentica o upstream com o access token do SERVIDOR, renovado pelo
// middleware, e IGNORA o header do cliente (`app/terra/[...path]/route.ts`:63).
// Mandar o token daqui não autenticaria nada e reintroduziria o defeito que
// aquele comentário registra: numa sessão longa, o token do cliente envelhece e
// vira 401 no backend sem que ninguém tenha saído.
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

/** Os status que `/assistente/editor/conversa` recusa antes do stream. Não é a
 *  tabela da Home de propósito — ver `erroDaResposta`. */
const ERROS_DA_ROTA: ErrosDaRota = {
  409: { code: "conversa_em_andamento", message: "Já há uma conversa em andamento neste fluxo." },
  429: { code: "rate_limited", message: "Muitas mensagens em pouco tempo. Espere um instante." },
  503: { code: "desligado", message: "O assistente não está disponível nesta instalação." },
}

export interface Assistente {
  estado: IAssistenteEstado | null
  /** Enquanto o `GET /estado` não volta, o painel não deve decidir nada. */
  consultando: boolean
  turnos: TurnoDoAssistente[]
  correndo: boolean
  enviar: (mensagem: string) => Promise<void>
  parar: () => void
  esquecer: () => Promise<void>
}

/**
 * @param workflowId  o fluxo aberto no editor. Ausente na tela de criar — o
 *                    backend guarda essa conversa sob a chave `novo`.
 */
export function useAssistenteEditor(workflowId?: string): Assistente {
  const [estado, setEstado] = useState<IAssistenteEstado | null>(null)
  const [consultando, setConsultando] = useState(true)
  const [turnos, setTurnos] = useState<TurnoDoAssistente[]>([])
  const [correndo, setCorrendo] = useState(false)

  const abortoRef = useRef<AbortController | null>(null)

  // Trocar de fluxo é trocar de conversa: o histórico do fluxo anterior não tem
  // nada a ver com este, e o stream dele não pode continuar escrevendo aqui.
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
      // Erro de rede aqui não é motivo para esconder o painel para sempre; o
      // `null` deixa quem chama tratar "não sei" separado de "desligado".
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

        // O quadro `cota` atualiza o estado e não entra na conversa.
        await lerQuadrosSSE(resposta.body, (quadro) => {
          if (!aplicarCota(setEstado, quadro)) aplicarNoTurno(setTurnos, idDoTurno, quadro)
        })
      } catch (erro) {
        // Parar é decisão de quem está usando, não falha: o turno fica como
        // está, com o que já chegou.
        if (!(erro instanceof DOMException && erro.name === "AbortError")) {
          aplicarNoTurno(setTurnos, idDoTurno, { evento: "erro", dados: SEM_CONEXAO })
        }
      } finally {
        // Fim do turno é o fechamento do STREAM, e não a chegada do quadro
        // `fim`. Aba fechada, conexão caída ou proxy que desistiu terminam a
        // conversa sem quadro nenhum, e o painel não pode ficar girando.
        if (abortoRef.current === controle) abortoRef.current = null
        setCorrendo(false)
        // A cota foi cobrada durante o turno. Sem esta releitura o painel
        // mostraria para sempre o gasto da montagem, e a pessoa só descobriria
        // o teto ao esbarrar nele.
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
