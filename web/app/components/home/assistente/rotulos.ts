// web/app/components/home/assistente/rotulos.ts
//
// Tool name in the screen's language, for the panel's timeline. The table
// lives in the Home dictionary (`i18n/secoes/assistente.ts`, `ferramentas`).
//
// `search_nodes` and `get_authoring_guide` are API names; someone building a
// workflow has no reason to learn them to understand that the assistant is
// looking for a node. The house pattern is the same as `status-rotulos.ts`: the
// raw value never reaches the screen.
//
// The table covers all tools, not only those the assistant can reach, because
// the `ferramenta` frame is emitted BEFORE dispatch: a name the gate rejects
// still shows up here once, followed by the step in error.

import { IDIOMA_PADRAO, type Idioma } from "@/lib/idioma"
import { textosDe } from "../i18n"

export function rotuloDaFerramenta(nome: string, idioma: Idioma = IDIOMA_PADRAO): string {
  const tabela = textosDe(idioma).assistente.ferramentas
  return Object.hasOwn(tabela, nome) ? tabela[nome] : nome
}

/**
 * A short detail of the call, taken from the argument summary.
 *
 * The server summary already collapses what is large (`definition` becomes
 * `{__campos__: 2}`), so there is only short text here — and even so the
 * selection is by known key, not "the first value that fits": a new argument
 * must not start dumping content onto the screen by accident.
 */
const DETALHE = ["query", "topic", "name", "search", "node_name", "workflow_id", "run_id", "file_id"]

export function detalheDaChamada(argumentos: Record<string, unknown>): string | null {
  for (const chave of DETALHE) {
    const valor = argumentos[chave]
    if (typeof valor === "string" && valor.trim()) return valor.length > 48 ? `${valor.slice(0, 45)}…` : valor
  }
  return null
}
