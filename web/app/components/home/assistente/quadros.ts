// web/app/components/home/assistente/quadros.ts
//
// The assistant's frames: decoding the `text/event-stream` and turning each
// frame into the conversation the panel draws.
//
// Pure on purpose. The classic bug of stream readers is the frame SPLIT IN
// HALF between two `read()` calls — the network does not respect message
// boundaries, and a `JSON.parse` on half a frame takes down the whole
// conversation. That needs tests, and testing it through a fake `fetch` inside
// a hook inside a component is the most expensive way of not looking at the problem.
//
// The frame contract is in `docs/assistente/editor.md` §"The SSE frames".
import type { CanvasDefinition } from "@/service/types"

export interface SSEFrame {
  evento: string
  dados: Record<string, unknown>
}

/**
 * SSE frame decoder, remembering what was left over from the previous chunk.
 *
 * Returns the COMPLETE frames of each feed and keeps the rest — which may be
 * half a line, half a frame, or ten and a half frames.
 */
/**
 * The `cota` frame — the window's running total after each model response,
 * with the ceiling. It is not a turn block: the hooks intercept it before
 * `aplicarQuadro` and update `estado.cota`, and that is how the donut rises
 * DURING the turn, without querying `/estado`. The server only emits it when
 * there is Redis to count; a malformed frame counts as none.
 */
export function cotaDoQuadro(quadro: SSEFrame): { gasto: number; teto: number } | null {
  if (quadro.evento !== "cota") return null
  const { gasto, teto } = quadro.dados
  if (typeof gasto !== "number" || typeof teto !== "number") return null
  if (!Number.isFinite(gasto) || !Number.isFinite(teto) || gasto < 0 || teto <= 0) return null
  return { gasto, teto }
}

export function criarDecodificador() {
  let resto = ""

  return function feed(pedaco: string): SSEFrame[] {
    // Normalize on the accumulated buffer, not on the chunk: a `\r\n` cut in the
    // middle (the `\r` in one chunk, the `\n` in the next) only becomes a line
    // ending after the two are joined.
    resto = (resto + pedaco).replace(/\r\n/g, "\n")

    const partes = resto.split("\n\n")
    resto = partes.pop() ?? ""

    return partes.map(decodificarUm).filter((q): q is SSEFrame => q !== null)
  }
}

function decodificarUm(bruto: string): SSEFrame | null {
  let evento = ""
  const dados: string[] = []

  for (const linha of bruto.split("\n")) {
    if (!linha || linha.startsWith(":")) continue // empty line or comment (heartbeat)

    const corte = linha.indexOf(":")
    const campo = corte === -1 ? linha : linha.slice(0, corte)
    let valor = corte === -1 ? "" : linha.slice(corte + 1)
    if (valor.startsWith(" ")) valor = valor.slice(1)

    if (campo === "event") evento = valor
    else if (campo === "data") dados.push(valor)
  }

  if (!evento || !dados.length) return null

  try {
    const corpo: unknown = JSON.parse(dados.join("\n"))
    // A frame without an object in `data` is not a frame from this server.
    // Discarding is better than inventing an event for it: the end of the
    // conversation does not depend on the `fim` frame arriving — what ends it is
    // the stream closing.
    if (!corpo || typeof corpo !== "object" || Array.isArray(corpo)) return null
    return { evento, dados: corpo as Record<string, unknown> }
  } catch {
    return null
  }
}

// ── A conversa ───────────────────────────────────────────────────────────────

export interface AssistantError {
  code: string
  message: string
  hint?: string
  /** On `loop_limit`: the surface's round ceiling (the translated sentence cites it). */
  teto?: number
}

export interface WorkflowProposal {
  definicao: CanvasDefinition
  nos: number
  arestas: number
  /**
   * `true` when it came from `desenhar_no_canvas`: it is meant to go on screen
   * NOW, without a button. `false`/absent when it came from `validate_workflow`,
   * which only brings the verdict on what is already drawn.
   *
   * The distinction exists because the same frame serves two roles ever since
   * delivering stopped being a side effect of validating.
   */
  desenhar?: boolean
  /** One line from the model about what changed in this drawing. */
  nota?: string
  /** `null` when the validation report could not be read. */
  ok: boolean | null
  erros: number | null
  avisos: number | null
}

export interface Progresso {
  concluidos: number
  total: number | null
  mensagem: string | null
}

// ── Frames only from the Home assistant ──────────────────────────────────────
// The editor never emits them; they are additive and the editor panel ignores them.

/** A workflow the assistant created — the badge next to the chat opens `/workflow/{id}`. */
export interface AssistantWorkflow {
  workflow_id: string
  nome: string
}

/** Pointer to an output on the globe; the source of truth is `GET /assistente/camadas/{id}`. */
export interface AssistantLayer {
  artifact_id: string
  nome?: string
  format?: string
  available: boolean
  hint?: string
}

/** An action that touches what already existed, waiting for the confirmation click. */
export interface AssistantConfirmation {
  tool_use_id: string
  token: string
  acao: { tool: string; argumentos: Record<string, unknown>; alvo?: string }
}

export type AssistantBlock =
  | { tipo: "texto"; texto: string }
  | { tipo: "pensando"; texto: string }
  | {
      tipo: "ferramenta"
      id: string
      nome: string
      argumentos: Record<string, unknown>
      estado: "correndo" | "ok" | "erro"
      progresso?: Progresso
    }
  | { tipo: "proposta"; proposta: WorkflowProposal }
  | { tipo: "fluxo"; fluxo: AssistantWorkflow }
  | { tipo: "camada"; camada: AssistantLayer }
  | { tipo: "confirmacao"; confirmacao: AssistantConfirmation }
  // Quick replies from the Home assistant: short continuations the person picks
  // with a click. They hold only for that one time — whoever draws them only
  // does so on the last turn, outside the stream.
  | { tipo: "respostas_rapidas"; opcoes: string[] }
  | { tipo: "erro"; erro: AssistantError }

export interface AssistantTurn {
  id: string
  papel: "user" | "assistant"
  /** Only for `papel: "user"`. The model turn is a list of blocks. */
  texto?: string
  blocos: AssistantBlock[]
}

export const emptyTurn = (id: string): AssistantTurn => ({
  id,
  papel: "assistant",
  blocos: [],
})

/**
 * Applies a frame to the turn in progress and returns the new turn.
 *
 * Immutable: the panel re-renders by identity, and mutating the turn in place
 * would make React see no change at all across a whole stream.
 *
 * The blocks are a TIMELINE, not separate fields, because the model
 * alternates: it thinks, writes, calls three tools, writes again. Keeping all
 * the text in a single field would lose what came before and after each call —
 * which is precisely the explanation that keeps someone from applying a workflow
 * without understanding it.
 */
export function aplicarQuadro(turno: AssistantTurn, quadro: SSEFrame): AssistantTurn {
  const { evento, dados } = quadro

  switch (evento) {
    case "texto":
      return { ...turno, blocos: accumulate(turno.blocos, "texto", texto(dados.texto)) }

    case "pensando":
      return { ...turno, blocos: accumulate(turno.blocos, "pensando", texto(dados.texto)) }

    case "ferramenta":
      return {
        ...turno,
        blocos: [
          ...turno.blocos,
          {
            tipo: "ferramenta",
            id: String(dados.id ?? ""),
            nome: String(dados.nome ?? ""),
            argumentos: objeto(dados.argumentos),
            estado: "correndo",
          },
        ],
      }

    case "progresso": {
      // With a round's tools running in parallel, several are "running" at the
      // same time — the frame carries the owner's `id` and that is how the bar
      // finds the right card. Without an `id` (old backend, replay of a
      // conversation recorded earlier), the usual criterion applies: the one running.
      const dono = dados.id == null ? null : String(dados.id)
      return {
        ...turno,
        blocos: mapTool(
          turno.blocos,
          b => (dono !== null ? b.id === dono : b.estado === "correndo"),
          b => ({
            ...b,
            progresso: {
              concluidos: numero(dados.concluidos) ?? 0,
              total: numero(dados.total),
              mensagem: dados.mensagem == null ? null : String(dados.mensagem),
            },
          }),
        ),
      }
    }

    case "ferramenta_fim":
      return {
        ...turno,
        blocos: mapTool(
          turno.blocos,
          b => b.id === String(dados.id ?? ""),
          b => ({ ...b, estado: dados.erro ? "erro" : "ok" }),
        ),
      }

    case "proposta":
      return {
        ...turno,
        blocos: [
          ...turno.blocos,
          {
            tipo: "proposta",
            proposta: {
              definicao: (dados.definicao ?? {}) as CanvasDefinition,
              nos: numero(dados.nos) ?? 0,
              arestas: numero(dados.arestas) ?? 0,
              desenhar: dados.desenhar === true,
              nota: typeof dados.nota === "string" ? dados.nota : undefined,
              ok: typeof dados.ok === "boolean" ? dados.ok : null,
              erros: numero(dados.erros),
              avisos: numero(dados.avisos),
            },
          },
        ],
      }

    case "fluxo":
      return {
        ...turno,
        blocos: [
          ...turno.blocos,
          {
            tipo: "fluxo",
            fluxo: { workflow_id: String(dados.workflow_id ?? ""), nome: String(dados.nome ?? "") },
          },
        ],
      }

    case "camada":
      return {
        ...turno,
        blocos: [
          ...turno.blocos,
          {
            tipo: "camada",
            camada: {
              artifact_id: String(dados.artifact_id ?? ""),
              nome: typeof dados.nome === "string" ? dados.nome : undefined,
              format: typeof dados.format === "string" ? dados.format : undefined,
              available: dados.available === true,
              hint: typeof dados.hint === "string" ? dados.hint : undefined,
            },
          },
        ],
      }

    case "confirmacao":
      return {
        ...turno,
        blocos: [
          ...turno.blocos,
          { tipo: "confirmacao", confirmacao: confirmationFrom(dados) },
        ],
      }

    case "respostas_rapidas": {
      // Without a valid option there is no block: an empty group of chips would be
      // a hole in the answer. The cleanup mirrors the server's (trimmed, no
      // duplicates, three at most) — defense in depth, not the rule.
      const opcoes = textos(dados.opcoes)
      if (!opcoes.length) return turno
      return { ...turno, blocos: [...turno.blocos, { tipo: "respostas_rapidas", opcoes }] }
    }

    case "erro":
      return {
        ...turno,
        blocos: [
          ...turno.blocos,
          {
            tipo: "erro",
            erro: {
              code: String(dados.code ?? "erro"),
              message: String(dados.message ?? "Algo deu errado."),
              hint: dados.hint == null ? undefined : String(dados.hint),
              ...(typeof dados.teto === "number" ? { teto: dados.teto } : {}),
            },
          },
        ],
      }

    case "fim":
      return {
        ...turno,
        // The `fim` closes the tools left open. The turn may have ended in the
        // middle of one (round ceiling, tab closed, model down), and a step
        // spinning forever would lie about what happened.
        blocos: turno.blocos.map(b =>
          b.tipo === "ferramenta" && b.estado === "correndo" ? { ...b, estado: "erro" } : b,
        ),
      }

    default:
      // A frame from a newer server. Ignoring it is the right behavior: the old
      // panel keeps working instead of breaking on the upgrade.
      return turno
  }
}

/** Text that arrives in chunks becomes ONE block, not one block per delta. */
function accumulate(
  blocos: AssistantBlock[],
  tipo: "texto" | "pensando",
  novo: string,
): AssistantBlock[] {
  if (!novo) return blocos

  const ultimo = blocos[blocos.length - 1]
  if (ultimo?.tipo === tipo) {
    return [...blocos.slice(0, -1), { tipo, texto: ultimo.texto + novo }]
  }
  return [...blocos, { tipo, texto: novo }]
}

/** Applies `mudar` to the LAST tool that matches `casa`. */
function mapTool(
  blocos: AssistantBlock[],
  casa: (b: Extract<AssistantBlock, { tipo: "ferramenta" }>) => boolean,
  mudar: (b: Extract<AssistantBlock, { tipo: "ferramenta" }>) => AssistantBlock,
): AssistantBlock[] {
  for (let i = blocos.length - 1; i >= 0; i--) {
    const bloco = blocos[i]
    if (bloco.tipo === "ferramenta" && casa(bloco)) {
      const copia = [...blocos]
      copia[i] = mudar(bloco)
      return copia
    }
  }
  return blocos
}

const texto = (v: unknown): string => (typeof v === "string" ? v : "")

const objeto = (v: unknown): Record<string, unknown> =>
  v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : {}

/** A list of sentences: strings only, trimmed, no empty or repeated ones, `teto` at most. */
const textos = (v: unknown, teto = 3): string[] => {
  if (!Array.isArray(v)) return []
  const lista: string[] = []
  for (const item of v) {
    const frase = typeof item === "string" ? item.trim() : ""
    if (frase && !lista.includes(frase)) lista.push(frase)
    if (lista.length === teto) break
  }
  return lista
}

/** Extracts the confirmation from the frame: token and the action (tool + summarized args + target). */
function confirmationFrom(dados: Record<string, unknown>): AssistantConfirmation {
  const acao = objeto(dados.acao)
  return {
    tool_use_id: String(dados.tool_use_id ?? ""),
    token: String(dados.token ?? ""),
    acao: {
      tool: String(acao.tool ?? ""),
      argumentos: objeto(acao.argumentos),
      alvo: typeof acao.alvo === "string" ? acao.alvo : undefined,
    },
  }
}

const numero = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null)

