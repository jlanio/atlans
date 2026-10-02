import type { IExecutor, IPolicyMember, IWorkspacePolicy } from "@/service/types"
import { descreverPolitica, descreverQueda, disponiveisNaCadeia, politicaEmAlerta, rotuloDoStatus } from "./politica"

/**
 * Leitura do executor de um workspace, reduzida a um estado só.
 *
 * O painel do ativo e a fileira compacta mostram a mesma informação em duas
 * densidades (frase por extenso lá, rótulo curto aqui). As regras que separam
 * "pool", "removido", "inativo" e "não sei" viviam dentro do card e teriam de
 * ser copiadas — e uma cópia divergiria na primeira correção.
 */

/** O que a tela precisa saber de um executor — serve tanto a lista `/executores/my`
 *  quanto um membro da política, que carrega os mesmos campos. */
export type ExecutorResumido = Pick<IExecutor, "id_hash" | "name" | "status" | "executor_type"> & {
  online: boolean | null
}

export type ResumoDoExecutor =
  | { estado: "carregando" }
  /** A leitura falhou: NÃO é pool, é "não sei para onde as execuções vão". */
  | { estado: "indefinido"; mensagem: string }
  | { estado: "pool" }
  /** Apontado para um executor que não está mais na lista (removido ou sem acesso). */
  | { estado: "sumido"; alvo: string }
  | { estado: "inativo"; executor: ExecutorResumido }
  | { estado: "ok"; executor: ExecutorResumido }
  /**
   * Política EM VIGOR com mais de um executor (grupo no principal ou uma
   * reserva): não é um alvo só, e o seletor rápido não a representa — o
   * painel mostra o resumo e manda para o editor.
   */
  | { estado: "grupo"; politica: IWorkspacePolicy }

export interface EntradaDoResumo {
  /** Executores disponíveis (inclui inativos, para reconhecer um alvo removido). */
  executores: IExecutor[]
  /** Alvo atual: `null` = pool da plataforma; `undefined` = ainda não lido. */
  alvo: string | null | undefined
  /** A leitura do executor DESTE workspace falhou. */
  alvoDesconhecido: boolean
  /** Falha ao listar os executores do usuário (vale para a tela toda). */
  erroExecutores: string | null
  /** Política de execução do workspace, quando lida; ausente = só o alvo. */
  politica?: IWorkspacePolicy | null
}

export const MENSAGEM_ALVO_DESCONHECIDO = "Não foi possível ler o executor deste workspace."

function membroComoExecutor(m: IPolicyMember): ExecutorResumido {
  return { id_hash: m.id_hash, name: m.name, status: m.status as IExecutor["status"], executor_type: m.executor_type, online: m.online }
}

export function resumirExecutor(e: EntradaDoResumo): ResumoDoExecutor {
  // "Sumido" só faz sentido quando a LISTA de executores foi lida: se a
  // listagem falhou, todo alvo pareceria removido e a tela pintaria alerta em
  // todos os workspaces por um problema que não é deles.
  if (e.erroExecutores) return { estado: "indefinido", mensagem: e.erroExecutores }
  if (e.alvoDesconhecido) return { estado: "indefinido", mensagem: MENSAGEM_ALVO_DESCONHECIDO }
  // O grupo só toma a tela quando a política VALE. Com a flag desligada é o
  // ponteiro legado que roteia, e é ele que o seletor mostra — a política
  // aparece como prévia, ao lado.
  const emVigor = e.politica?.policy_routing_enabled === true
  if (emVigor && e.politica && (e.politica.primary.length > 1 || e.politica.fallback.length > 0)) {
    return { estado: "grupo", politica: e.politica }
  }
  if (e.alvo === undefined) return { estado: "carregando" }
  if (e.alvo === null) return { estado: "pool" }
  const alvo = e.alvo
  const executor: ExecutorResumido | undefined =
    e.executores.find(x => x.id_hash === alvo)
    // Membro da política que não está na MINHA lista (incluído por um admin da
    // plataforma, por exemplo): a política já traz nome, status e presença.
    ?? (emVigor ? e.politica?.primary.map(membroComoExecutor).find(m => m.id_hash === alvo) : undefined)
  if (!executor) return { estado: "sumido", alvo }
  if (executor.status !== "active") return { estado: "inativo", executor }
  return { estado: "ok", executor }
}

/**
 * Merece o triângulo. Um dedicado OFFLINE só é alerta quando a política vale
 * e é Isolado: aí a próxima execução falha. No legado (ou com último recurso
 * pool) o pool assume, e o cinza basta.
 */
export function emAlerta(r: ResumoDoExecutor, politica?: IWorkspacePolicy | null): boolean {
  if (r.estado === "grupo") return politicaEmAlerta(r.politica)
  if (r.estado === "ok") {
    return r.executor.online === false && r.executor.executor_type === "dedicated"
      && politica?.policy_routing_enabled === true && politica.mode === "isolated"
  }
  return r.estado === "sumido" || r.estado === "inativo"
}

/** Frase do painel do ativo: o que o status significa para as execuções. */
export function descreverExecutor(r: ResumoDoExecutor, politica?: IWorkspacePolicy | null): string {
  switch (r.estado) {
    case "carregando": return ""
    case "indefinido": return r.mensagem
    case "pool": return "Pool compartilhado · qualquer executor compartilhado assume as execuções"
    // Sem "escolha outro": quem não gerencia lê a mesma frase e não tem como.
    case "sumido": return "Indisponível · o executor apontado foi removido ou você perdeu o acesso"
    case "inativo": return `${capitalizar(rotuloDoStatus(r.executor.status))} · não recebe execuções`
    case "grupo": return descreverPolitica(r.politica)
    case "ok": {
      const conexao = r.executor.online === true ? "Online" : r.executor.online === false ? "Offline" : "Sem sinal"
      if (r.executor.executor_type !== "dedicated") return `${conexao} · executor compartilhado, fixado para este workspace`
      const queda = descreverQueda(politica)
      if (r.executor.online === false && politica?.policy_routing_enabled && politica.mode === "isolated") {
        return "Offline · novas execuções vão falhar"
      }
      return `${conexao} · dedicado a este workspace · ${queda}`
    }
  }
}

/** Rótulo da fileira compacta: cabe ao lado do papel numa linha de 12px. */
export function rotularExecutor(r: ResumoDoExecutor): string {
  switch (r.estado) {
    case "carregando": return ""
    case "indefinido": return "Executor não lido"
    case "pool": return "Pool compartilhado"
    case "sumido": return "Executor indisponível"
    case "inativo": return `${r.executor.name} · ${rotuloDoStatus(r.executor.status)}`
    case "ok": return r.executor.name
    case "grupo": {
      // Curto de propósito: a fileira tem três colunas e "geo-01 + reserva"
      // truncava. O detalhe (principais/reserva/online) fica na frase do painel.
      const total = r.politica.primary.length + r.politica.fallback.length
      return `${total} executores`
    }
  }
}

/**
 * Classes do ponto de status ao lado do rótulo, ou `null` quando não há o que
 * sinalizar. O ponto acompanha o texto, nunca o substitui: cor sozinha não
 * distingue "offline" de "pool" para quem não vê cor.
 */
export function corDoPonto(r: ResumoDoExecutor, politica?: IWorkspacePolicy | null): string | null {
  switch (r.estado) {
    case "ok":
      if (emAlerta(r, politica)) return "bg-amber-500"
      if (r.executor.online === null) return "border border-dashed border-muted-foreground/70"
      return r.executor.online ? "bg-green-500" : "bg-muted-foreground/40"
    case "pool": return "border border-muted-foreground/60"
    case "sumido":
    case "inativo": return "bg-amber-500"
    case "grupo":
      if (politicaEmAlerta(r.politica)) return "bg-amber-500"
      return disponiveisNaCadeia(r.politica) > 0 ? "bg-green-500" : "bg-muted-foreground/40"
    default: return null
  }
}

function capitalizar(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1)
}
