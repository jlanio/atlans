import type { IExecutor, IPolicyMember, IWorkspacePolicy } from "@/service/types"
import { describePolicy, describeOutage, availableInChain, politicaEmAlerta, rotuloDoStatus } from "./politica"

/**
 * Reading of a workspace's executor, reduced to a single state.
 *
 * The active workspace's panel and the compact row show the same information
 * at two densities (a full sentence there, a short label here). The rules that
 * separate "pool", "removed", "inactive" and "don't know" lived inside the card
 * and would have to be copied — and a copy would diverge on the first fix.
 */

/** What the screen needs to know about an executor — fits both the `/executores/my`
 *  list and a policy member, which carries the same fields. */
export type BriefExecutor = Pick<IExecutor, "id_hash" | "name" | "status" | "executor_type"> & {
  online: boolean | null
}

export type ExecutorSummary =
  | { estado: "carregando" }
  /** The read failed: this is NOT pool, it is "don't know where runs go". */
  | { estado: "indefinido"; mensagem: string }
  | { estado: "pool" }
  /** Pointed at an executor that is no longer in the list (removed or no access). */
  | { estado: "sumido"; alvo: string }
  | { estado: "inativo"; executor: BriefExecutor }
  | { estado: "ok"; executor: BriefExecutor }
  /**
   * A policy IN EFFECT with more than one executor (a group in the primary
   * tier or a fallback): it is not a single target, and the quick picker does
   * not represent it — the panel shows the summary and sends you to the editor.
   */
  | { estado: "grupo"; politica: IWorkspacePolicy }

export interface SummaryEntry {
  /** Available executors (includes inactive ones, to recognize a removed target). */
  executores: IExecutor[]
  /** Current target: `null` = platform pool; `undefined` = not read yet. */
  alvo: string | null | undefined
  /** A leitura do executor DESTE workspace falhou. */
  alvoDesconhecido: boolean
  /** Failure listing the user's executors (applies to the whole screen). */
  erroExecutores: string | null
  /** The workspace's execution policy, when read; absent = target only. */
  politica?: IWorkspacePolicy | null
}

export const UNKNOWN_TARGET_MESSAGE = "Não foi possível ler o executor deste workspace."

function memberAsExecutor(m: IPolicyMember): BriefExecutor {
  return { id_hash: m.id_hash, name: m.name, status: m.status as IExecutor["status"], executor_type: m.executor_type, online: m.online }
}

export function resumirExecutor(e: SummaryEntry): ExecutorSummary {
  // "Gone" only makes sense when the executor LIST was read: if listing
  // failed, every target would look removed and the screen would paint an alert
  // on every workspace for a problem that is not theirs.
  if (e.erroExecutores) return { estado: "indefinido", mensagem: e.erroExecutores }
  if (e.alvoDesconhecido) return { estado: "indefinido", mensagem: UNKNOWN_TARGET_MESSAGE }
  // The group only takes over the screen when the policy is IN EFFECT. With the
  // flag off it is the legacy pointer that routes, and that is what the picker
  // shows — the policy appears as a preview, alongside.
  const emVigor = e.politica?.policy_routing_enabled === true
  if (emVigor && e.politica && (e.politica.primary.length > 1 || e.politica.fallback.length > 0)) {
    return { estado: "grupo", politica: e.politica }
  }
  if (e.alvo === undefined) return { estado: "carregando" }
  if (e.alvo === null) return { estado: "pool" }
  const alvo = e.alvo
  const executor: BriefExecutor | undefined =
    e.executores.find(x => x.id_hash === alvo)
    // A policy member that is not in MY list (added by a platform admin, for
    // example): the policy already carries name, status and presence.
    ?? (emVigor ? e.politica?.primary.map(memberAsExecutor).find(m => m.id_hash === alvo) : undefined)
  if (!executor) return { estado: "sumido", alvo }
  if (executor.status !== "active") return { estado: "inativo", executor }
  return { estado: "ok", executor }
}

/**
 * Deserves the triangle. An OFFLINE dedicated executor is only an alert when the
 * policy is in effect and is Isolated: then the next run fails. In legacy mode
 * (or with pool as last resort) the pool takes over, and gray is enough.
 */
export function inAlert(r: ExecutorSummary, politica?: IWorkspacePolicy | null): boolean {
  if (r.estado === "grupo") return politicaEmAlerta(r.politica)
  if (r.estado === "ok") {
    return r.executor.online === false && r.executor.executor_type === "dedicated"
      && politica?.policy_routing_enabled === true && politica.mode === "isolated"
  }
  return r.estado === "sumido" || r.estado === "inativo"
}

/** Sentence for the active workspace's panel: what the status means for runs. */
export function describeExecutor(r: ExecutorSummary, politica?: IWorkspacePolicy | null): string {
  switch (r.estado) {
    case "carregando": return ""
    case "indefinido": return r.mensagem
    case "pool": return "Pool compartilhado · qualquer executor compartilhado assume as execuções"
    // No "pick another": someone who does not manage reads the same sentence and cannot.
    case "sumido": return "Indisponível · o executor apontado foi removido ou você perdeu o acesso"
    case "inativo": return `${capitalize(rotuloDoStatus(r.executor.status))} · não recebe execuções`
    case "grupo": return describePolicy(r.politica)
    case "ok": {
      const conexao = r.executor.online === true ? "Online" : r.executor.online === false ? "Offline" : "Sem sinal"
      if (r.executor.executor_type !== "dedicated") return `${conexao} · executor compartilhado, fixado para este workspace`
      const queda = describeOutage(politica)
      if (r.executor.online === false && politica?.policy_routing_enabled && politica.mode === "isolated") {
        return "Offline · novas execuções vão falhar"
      }
      return `${conexao} · dedicado a este workspace · ${queda}`
    }
  }
}

/** Label for the compact row: fits next to the role in a 12px line. */
export function labelExecutor(r: ExecutorSummary): string {
  switch (r.estado) {
    case "carregando": return ""
    case "indefinido": return "Executor não lido"
    case "pool": return "Pool compartilhado"
    case "sumido": return "Executor indisponível"
    case "inativo": return `${r.executor.name} · ${rotuloDoStatus(r.executor.status)}`
    case "ok": return r.executor.name
    case "grupo": {
      // Short on purpose: the row has three columns and "geo-01 + reserva" was
      // truncated. The detail (primary/fallback/online) goes in the panel sentence.
      const total = r.politica.primary.length + r.politica.fallback.length
      return `${total} executores`
    }
  }
}

/**
 * Classes for the status dot next to the label, or `null` when there is nothing
 * to signal. The dot accompanies the text, never replaces it: color alone does
 * not distinguish "offline" from "pool" for someone who cannot see color.
 */
export function dotColor(r: ExecutorSummary, politica?: IWorkspacePolicy | null): string | null {
  switch (r.estado) {
    case "ok":
      if (inAlert(r, politica)) return "bg-amber-500"
      if (r.executor.online === null) return "border border-dashed border-muted-foreground/70"
      return r.executor.online ? "bg-green-500" : "bg-muted-foreground/40"
    case "pool": return "border border-muted-foreground/60"
    case "sumido":
    case "inativo": return "bg-amber-500"
    case "grupo":
      if (politicaEmAlerta(r.politica)) return "bg-amber-500"
      return availableInChain(r.politica) > 0 ? "bg-green-500" : "bg-muted-foreground/40"
    default: return null
  }
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1)
}
