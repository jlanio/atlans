// web/app/components/home/assistente/stream.ts
//
// A leitura do stream do assistente, em um lugar só.
//
// Os dois consumidores — `useAssistente` (Home) e `useAssistenteEditor` (gaveta
// do editor) — nasceram um fork do outro, e as cópias já tinham divergido: a do
// editor não soltava o leitor no `finally`, e um "Parar" (ou a troca de fluxo)
// que abortava a leitura no meio deixava a conexão pendurada até o servidor
// desistir sozinho.
//
// O que é de cada hook fica nele: a rota e o corpo do POST, o quadro `conversa`,
// o replay e a confirmação (só a Home) — e a tabela de status de
// `erroDaResposta`, que difere DE PROPÓSITO entre as duas rotas e por isso entra
// aqui por parâmetro.
//
// Decodificar os quadros e aplicá-los ao turno é de `quadros.ts`, puro.
import type { Dispatch, SetStateAction } from "react"

import type { IAssistenteEstado } from "@/service/types"
import {
  aplicarQuadro,
  cotaDoQuadro,
  criarDecodificador,
  type QuadroSSE,
  type TurnoDoAssistente,
} from "./quadros"

/** O erro do turno que a rede cortou: o `fetch` rejeitou ou o stream rompeu. */
export const SEM_CONEXAO = {
  code: "sem_conexao",
  message: "A conversa foi interrompida.",
  hint: "confira a conexão e tente de novo",
}

let sequencia = 0
/** Id de turno — chave de render e alvo de `aplicarNoTurno`. Único na aba. */
export const proximoIdDeTurno = () => `t${++sequencia}`

/** Aplica um quadro ao turno `id`, sem tocar nos outros. */
export function aplicarNoTurno(
  setTurnos: Dispatch<SetStateAction<TurnoDoAssistente[]>>,
  id: string,
  quadro: QuadroSSE,
): void {
  setTurnos((anteriores) => anteriores.map((t) => (t.id === id ? aplicarQuadro(t, quadro) : t)))
}

/**
 * O quadro `cota` não é bloco de turno: é o acumulado da janela, cobrado a cada
 * resposta do modelo, e sobe o gasto no estado — o donut anda DURANTE o turno.
 * O prazo fica o que era: a releitura do `/estado` ao fim do turno é quem o
 * atualiza. Devolve se o quadro era de cota (e já foi tratado).
 */
export function aplicarCota(
  setEstado: Dispatch<SetStateAction<IAssistenteEstado | null>>,
  quadro: QuadroSSE,
): boolean {
  const cota = cotaDoQuadro(quadro)
  if (!cota) return false
  setEstado((atual) => atual
    ? { ...atual, cota: { gasto: cota.gasto, teto: cota.teto, reabre_em_segundos: atual.cota?.reabre_em_segundos ?? null } }
    : atual)
  return true
}

/**
 * Lê o `text/event-stream` até o fim, entregando cada quadro COMPLETO a
 * `tratar` — um quadro partido entre dois `read()` espera o resto.
 *
 * Rejeita com o erro da leitura: o `AbortError` do "Parar" e a queda de rede
 * chegam a quem chamou, que decide o que cada um vira no turno.
 */
export async function lerQuadrosSSE(
  corpo: ReadableStream<Uint8Array>,
  tratar: (quadro: QuadroSSE) => void,
): Promise<void> {
  const leitor = corpo.getReader()
  const decodificar = criarDecodificador()
  // `stream: true` no decodificador de texto pelo mesmo motivo do de quadros:
  // um caractere de vários bytes (e o português é cheio deles) pode nascer num
  // `read()` e terminar no seguinte.
  const utf8 = new TextDecoder()
  try {
    for (;;) {
      const { done, value } = await leitor.read()
      if (done) {
        // O `decode()` final esvazia o que sobrou de um caractere partido no
        // último pedaço. Na prática o stream termina no `\n\n` do `fim`, mas
        // depender disso seria depender do formato do quadro.
        for (const quadro of decodificar(utf8.decode())) tratar(quadro)
        return
      }
      for (const quadro of decodificar(utf8.decode(value, { stream: true }))) tratar(quadro)
    }
  } finally {
    // Solta o leitor mesmo quando o abort (ou um quadro que o `tratar` não
    // digeriu) corta a leitura no meio — senão a conexão fica pendurada até o
    // servidor desistir sozinho.
    await leitor.cancel().catch(() => {})
  }
}

/** O código e a frase de cada status que a rota recusa ANTES de virar stream. */
export type ErrosDaRota = Record<number, { code: string; message: string }>

/**
 * O corpo de erro da API quando a resposta nem chegou a virar stream.
 *
 * A forma é `{error, message, status_code}` (`app/core/utils/error_handlers.py`),
 * e o 503 do assistente desligado vem com `detail`: a frase do servidor, quando
 * há, vence a da tabela. O que não puder ser lido vira a frase da tabela (ou um
 * "A API respondeu N." honesto) em vez de "undefined".
 *
 * `padroes` é a tabela da ROTA, e as duas diferem de propósito: o 429 da Home é
 * `muitas_requisicoes` porque, no stream dela, `rate_limited` é a cota DIÁRIA;
 * o 409 do editor é a conversa em andamento no fluxo, o da Home é a
 * confirmação que expirou.
 */
export async function erroDaResposta(resposta: Response, padroes: ErrosDaRota): Promise<Record<string, unknown>> {
  const padrao = padroes[resposta.status] ?? { code: "erro_http", message: `A API respondeu ${resposta.status}.` }
  try {
    const corpo = await resposta.json()
    const mensagem = corpo?.message ?? corpo?.detail
    return typeof mensagem === "string" && mensagem ? { ...padrao, message: mensagem } : padrao
  } catch {
    return padrao
  }
}
