import type { IWorkflow, IWorkflowGroup } from "@/service/types"
import { fromBackend } from "@/lib/dayjs"
import { FILTERS, type Filtro, type Ordem } from "./projetos-url"
import type { HowItsGoing } from "./como-anda"
import { resumirAgendamento, type ScheduleSummary } from "./gatilho"

/**
 * Projects chips, search and sorting (docs/specs/projects.md §3.6). Pure:
 * the `index` builds the context once per render ("como anda" and schedule
 * summary per workflow) and each predicate only reads.
 */

export interface FilterContext {
  comoAndaPorHash: Map<string, HowItsGoing>
  resumoDoAgendamentoPorHash: Map<string, ScheduleSummary | null>
}

/** The bar's chips, in screen order. `pausado` and `nunca` exist only in the URL. */
export const CHIP_FILTERS: Filtro[] = [
  "todos", "ativos", "inativos", "executando", "falha", "agendados", "webhook", "subfluxos", "portal",
  "assistente",
]

export const FILTER_LABEL: Record<Filtro, string> = {
  todos: "Todos",
  ativos: "Ativos",
  inativos: "Inativos",
  executando: "Em execução",
  falha: "Com falha",
  agendados: "Agendados",
  webhook: "Webhook",
  subfluxos: "Sub-fluxos",
  portal: "Com portal",
  assistente: "Assistente",
  pausado: "Agendamento pausado",
  nunca: "Ainda não executou",
}

export const SORT_LABEL: Record<Ordem, string> = {
  nome: "Nome",
  execucao: "Última execução",
  alterado: "Alterado",
}

/** Published and accessible portal — the "Portal público/privado" badge and the "Com portal" chip use the same rule. */
export function hasPortal(wf: Pick<IWorkflow, "has_publish_map" | "portal_access">): boolean {
  return !!wf.has_publish_map && wf.portal_access !== "disabled"
}

function isPaused(wf: IWorkflow, contexto: FilterContext): boolean {
  // The context summary is the source; without it (a workflow that arrived after
  // the context was built), derive from the item itself — it is cheap and keeps
  // a chip and a row from disagreeing.
  const resumo = contexto.resumoDoAgendamentoPorHash.get(wf.id_hash) ?? resumirAgendamento(wf.schedule, wf.flag_ative)
  return resumo?.estado === "pausado"
}

export function predicadoDoFiltro(filtro: Filtro, contexto: FilterContext): (wf: IWorkflow) => boolean {
  switch (filtro) {
    case "todos": return () => true
    case "ativos": return wf => wf.flag_ative
    case "inativos": return wf => !wf.flag_ative
    // Reads the already-derived "como anda", not raw `runningHashes`: the row
    // shows "Em execução" also when the metrics say `running` with no live run
    // in the context (45 s cache window). Chip, filter and row would disagree.
    case "executando": return wf => contexto.comoAndaPorHash.get(wf.id_hash)?.tipo === "executando"
    case "falha": return wf => contexto.comoAndaPorHash.get(wf.id_hash)?.tipo === "falhou"
    case "agendados": return wf => !!wf.has_schedule_trigger
    case "webhook": return wf => !!wf.has_webhook_trigger
    case "subfluxos": return wf => !!wf.is_subworkflow
    case "portal": return wf => hasPortal(wf)
    // Who CREATED the workflow, not who triggered it: an assistant workflow
    // run by hand still belongs to the assistant.
    case "assistente": return wf => wf.origem === "assistente"
    case "pausado": return wf => isPaused(wf, contexto)
    case "nunca": return wf => contexto.comoAndaPorHash.get(wf.id_hash)?.tipo === "nunca"
  }
}

/** Count of each chip over the WHOLE list (not the filtered one), as the spec asks. */
export function contarPorFiltro(workflows: IWorkflow[], contexto: FilterContext): Record<Filtro, number> {
  const contagem = Object.fromEntries(FILTERS.map(f => [f, 0])) as Record<Filtro, number>
  const predicates = FILTERS.map(f => [f, predicadoDoFiltro(f, contexto)] as const)
  for (const wf of workflows) {
    for (const [f, casa] of predicates) if (casa(wf)) contagem[f]++
  }
  return contagem
}

/** No accents, no case, no leading/trailing spaces: "Outorgas" matches "outorga", "Bacia do Rio" matches "rio". */
export function normalizeSearch(texto: string | null | undefined): string {
  return (texto ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim()
}

/**
 * Name, description and group name: whoever types "hidrologia" wants to see the
 * workflows in the Hidrologia group, even if none has the word in its name.
 */
export function matchesSearch(wf: IWorkflow, groupsById: Map<string, IWorkflowGroup>, q: string): boolean {
  const termo = normalizeSearch(q)
  if (!termo) return true
  if (normalizeSearch(wf.name).includes(termo)) return true
  if (normalizeSearch(wf.description).includes(termo)) return true
  const grupo = wf.group_id ? groupsById.get(wf.group_id) : undefined
  return !!grupo && normalizeSearch(grupo.name).includes(termo)
}

function byName(a: IWorkflow, b: IWorkflow): number {
  return a.name.localeCompare(b.name, "pt-BR", { numeric: true })
}

function instantOf(iso: string | null | undefined): number {
  return fromBackend(iso)?.valueOf() ?? 0
}

function runInstant(wf: IWorkflow, contexto: FilterContext): number | null {
  const comoAnda = contexto.comoAndaPorHash.get(wf.id_hash)
  return comoAnda && "instante" in comoAnda ? comoAnda.instante : null
}

/**
 * Sorted copy. Name in pt-BR; "execução" puts the most recent (or in progress)
 * first and those that never ran last; "alterado" is `updated_at` desc.
 * Ties fall back to the name, so the list does not shift between renders.
 */
export function ordenar(workflows: IWorkflow[], ordem: Ordem, contexto: FilterContext): IWorkflow[] {
  const lista = [...workflows]
  switch (ordem) {
    case "nome":
      return lista.sort(byName)
    case "alterado":
      return lista.sort((a, b) => (instantOf(b.updated_at) - instantOf(a.updated_at)) || byName(a, b))
    case "execucao":
      return lista.sort((a, b) => {
        const ia = runInstant(a, contexto)
        const ib = runInstant(b, contexto)
        if (ia == null && ib == null) return byName(a, b)
        if (ia == null) return 1
        if (ib == null) return -1
        return (ib - ia) || byName(a, b)
      })
  }
}
