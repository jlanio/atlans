import type { IWorkflow, IWorkflowGroup } from "@/service/types"
import { fromBackend } from "@/lib/dayjs"
import { FILTROS, type Filtro, type Ordem } from "./projetos-url"
import type { ComoAnda } from "./como-anda"
import { resumirAgendamento, type ResumoDoAgendamento } from "./gatilho"

/**
 * Chips, busca e ordenação de Projetos (docs/specs/projects.md §3.6). Puro:
 * o `index` monta o contexto uma vez por render ("como anda" e resumo do
 * agendamento por workflow) e cada predicado só lê.
 */

export interface ContextoDeFiltro {
  comoAndaPorHash: Map<string, ComoAnda>
  resumoDoAgendamentoPorHash: Map<string, ResumoDoAgendamento | null>
}

/** Os chips da barra, na ordem da tela. `pausado` e `nunca` só existem na URL. */
export const FILTROS_DOS_CHIPS: Filtro[] = [
  "todos", "ativos", "inativos", "executando", "falha", "agendados", "webhook", "subfluxos", "portal",
  "assistente",
]

export const ROTULO_DO_FILTRO: Record<Filtro, string> = {
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

export const ROTULO_DA_ORDEM: Record<Ordem, string> = {
  nome: "Nome",
  execucao: "Última execução",
  alterado: "Alterado",
}

/** Portal publicado e acessível — o selo "Portal público/privado" e o chip "Com portal" usam a mesma regra. */
export function temPortal(wf: Pick<IWorkflow, "has_publish_map" | "portal_access">): boolean {
  return !!wf.has_publish_map && wf.portal_access !== "disabled"
}

function estaPausado(wf: IWorkflow, contexto: ContextoDeFiltro): boolean {
  // O resumo do contexto é a fonte; sem ele (workflow que chegou depois de
  // o contexto ser montado), deriva do próprio item — é barato e evita que
  // um chip e uma linha discordem.
  const resumo = contexto.resumoDoAgendamentoPorHash.get(wf.id_hash) ?? resumirAgendamento(wf.schedule, wf.flag_ative)
  return resumo?.estado === "pausado"
}

export function predicadoDoFiltro(filtro: Filtro, contexto: ContextoDeFiltro): (wf: IWorkflow) => boolean {
  switch (filtro) {
    case "todos": return () => true
    case "ativos": return wf => wf.flag_ative
    case "inativos": return wf => !wf.flag_ative
    // Lê o "como anda" já derivado, e não `runningHashes` cru: a linha marca
    // "Em execução" também quando as métricas dizem `running` sem run vivo no
    // contexto (janela de cache de 45 s). Chip, filtro e linha discordariam.
    case "executando": return wf => contexto.comoAndaPorHash.get(wf.id_hash)?.tipo === "executando"
    case "falha": return wf => contexto.comoAndaPorHash.get(wf.id_hash)?.tipo === "falhou"
    case "agendados": return wf => !!wf.has_schedule_trigger
    case "webhook": return wf => !!wf.has_webhook_trigger
    case "subfluxos": return wf => !!wf.is_subworkflow
    case "portal": return wf => temPortal(wf)
    // Quem CRIOU o fluxo, não quem o disparou: um fluxo do assistente
    // executado à mão continua sendo do assistente.
    case "assistente": return wf => wf.origem === "assistente"
    case "pausado": return wf => estaPausado(wf, contexto)
    case "nunca": return wf => contexto.comoAndaPorHash.get(wf.id_hash)?.tipo === "nunca"
  }
}

/** Contagem de cada chip sobre a lista INTEIRA (não a filtrada), como a spec pede. */
export function contarPorFiltro(workflows: IWorkflow[], contexto: ContextoDeFiltro): Record<Filtro, number> {
  const contagem = Object.fromEntries(FILTROS.map(f => [f, 0])) as Record<Filtro, number>
  const predicados = FILTROS.map(f => [f, predicadoDoFiltro(f, contexto)] as const)
  for (const wf of workflows) {
    for (const [f, casa] of predicados) if (casa(wf)) contagem[f]++
  }
  return contagem
}

/** Sem acento, sem caixa, sem espaço nas pontas: "Outorgas" casa "outorga", "Bacia do Rio" casa "rio". */
export function normalizarBusca(texto: string | null | undefined): string {
  return (texto ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim()
}

/**
 * Nome, descrição e nome do grupo: quem digita "hidrologia" quer ver os
 * workflows do grupo Hidrologia, mesmo que nenhum tenha a palavra no nome.
 */
export function casaBusca(wf: IWorkflow, gruposPorId: Map<string, IWorkflowGroup>, q: string): boolean {
  const termo = normalizarBusca(q)
  if (!termo) return true
  if (normalizarBusca(wf.name).includes(termo)) return true
  if (normalizarBusca(wf.description).includes(termo)) return true
  const grupo = wf.group_id ? gruposPorId.get(wf.group_id) : undefined
  return !!grupo && normalizarBusca(grupo.name).includes(termo)
}

function porNome(a: IWorkflow, b: IWorkflow): number {
  return a.name.localeCompare(b.name, "pt-BR", { numeric: true })
}

function instanteDe(iso: string | null | undefined): number {
  return fromBackend(iso)?.valueOf() ?? 0
}

function instanteDaExecucao(wf: IWorkflow, contexto: ContextoDeFiltro): number | null {
  const comoAnda = contexto.comoAndaPorHash.get(wf.id_hash)
  return comoAnda && "instante" in comoAnda ? comoAnda.instante : null
}

/**
 * Cópia ordenada. Nome em pt-BR; "execução" põe a mais recente (ou em curso)
 * primeiro e quem nunca rodou por último; "alterado" é `updated_at` desc.
 * Empates caem no nome, para a lista não mudar de lugar entre renders.
 */
export function ordenar(workflows: IWorkflow[], ordem: Ordem, contexto: ContextoDeFiltro): IWorkflow[] {
  const lista = [...workflows]
  switch (ordem) {
    case "nome":
      return lista.sort(porNome)
    case "alterado":
      return lista.sort((a, b) => (instanteDe(b.updated_at) - instanteDe(a.updated_at)) || porNome(a, b))
    case "execucao":
      return lista.sort((a, b) => {
        const ia = instanteDaExecucao(a, contexto)
        const ib = instanteDaExecucao(b, contexto)
        if (ia == null && ib == null) return porNome(a, b)
        if (ia == null) return 1
        if (ib == null) return -1
        return (ib - ia) || porNome(a, b)
      })
  }
}
