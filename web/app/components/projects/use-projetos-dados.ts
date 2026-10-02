"use client"

import { useCallback, useEffect, useMemo, useRef, useState, type Dispatch, type SetStateAction } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import { useWorkspace } from "@/context/WorkspaceContext"
import { createToast } from "@/utils/createToast"
import type { IResponse } from "@/service/types"
import type { IWorkflow, IWorkflowGroup } from "@/service/types"
import type { IWorkflowMetricsRow } from "@/service/types"
import { JANELA_EM_DIAS } from "./como-anda"

/**
 * Dados de Projetos (docs/specs/projects.md §3.3).
 *
 * Três chamadas partem juntas por workspace: listagem, grupos e métricas
 * (`/observability/metrics/workflows`, janela de 30 dias). As duas primeiras
 * são obrigatórias — sem elas não há estante; a terceira é a coluna "como
 * anda", e a lista sai completa sem ela, com um aviso discreto. Nada de
 * cache local: a listagem já é magra e o backend guarda as métricas por 45 s.
 */

export interface DadosDeProjetos {
  workflows: IWorkflow[]
  grupos: IWorkflowGroup[]
  /** Por `workflow_hash`; nulo quando as métricas falharam (a coluna some). */
  metricas: Map<string, IWorkflowMetricsRow> | null
  /** Primeira carga do workspace (skeleton). */
  carregando: boolean
  /** Recargas seguintes (o botão gira, a lista fica). */
  atualizando: boolean
  /** Listagem ou grupos falharam — estado de erro com "Tentar de novo". */
  erro: string | null
  /** Só as métricas falharam — aviso discreto acima da lista. */
  metricasIndisponiveis: boolean
  /** Carimbo (ms) da última resposta aceita, para o "atualizado há X". */
  atualizadoEm: number | null
  /** "Atualizar" passa `force: true` para furar o cache das métricas no backend. */
  recarregar: (opcoes?: { force?: boolean }) => void
  /** Mutações otimistas do `index` (ativar, mover, excluir…); aceitam valor ou função. */
  definirWorkflows: Dispatch<SetStateAction<IWorkflow[]>>
  definirGrupos: Dispatch<SetStateAction<IWorkflowGroup[]>>
}

/** As métricas se atualizam sozinhas neste ritmo com a aba visível; a listagem, não. */
export const INTERVALO_DAS_METRICAS_MS = 60_000

const ERRO_PADRAO = "Não foi possível carregar os projetos."

function mapaDeMetricas(linhas: IWorkflowMetricsRow[]): Map<string, IWorkflowMetricsRow> {
  return new Map(linhas.map(l => [l.workflow_hash, l]))
}

/** `allSettled` nunca rejeita; o service também não — mas um `throw` inesperado não pode derrubar a tela. */
function resposta<T>(r: PromiseSettledResult<IResponse<T> | null>): IResponse<T> | null {
  return r.status === "fulfilled" ? r.value : null
}

function mensagemDe(...respostas: (IResponse<unknown> | null)[]): string {
  for (const r of respostas) {
    if (r?.error) return r.error.message ?? ERRO_PADRAO
  }
  return ERRO_PADRAO
}

export function useProjetosDados(opts: { intervaloDasMetricasMs?: number } = {}): DadosDeProjetos {
  const { intervaloDasMetricasMs = INTERVALO_DAS_METRICAS_MS } = opts
  const { current, loading: workspaceLoading } = useWorkspace()
  const workspaceId = current?.id_hash

  const [workflows, setWorkflows] = useState<IWorkflow[]>([])
  const [grupos, setGrupos] = useState<IWorkflowGroup[]>([])
  const [metricas, setMetricas] = useState<Map<string, IWorkflowMetricsRow> | null>(null)
  const [carregando, setCarregando] = useState(true)
  const [atualizando, setAtualizando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [metricasIndisponiveis, setMetricasIndisponiveis] = useState(false)
  const [atualizadoEm, setAtualizadoEm] = useState<number | null>(null)

  // Carimbo de sequência: trocar de workspace duas vezes seguidas dispara
  // duas cargas, e a mais lenta pode responder por último. Só a última
  // carga pedida escreve na tela.
  const seq = useRef(0)
  // Workspace cujos dados estão NA TELA (`undefined` = nunca carregou). É o
  // que separa skeleton (primeira carga deste workspace) de "o botão gira".
  const workspaceNaTela = useRef<string | null | undefined>(undefined)
  // O `recarregar` lê o workspace corrente sem trocar de identidade a cada
  // render (desce para o botão Atualizar).
  const workspaceRef = useRef(workspaceId)
  workspaceRef.current = workspaceId

  // Quando o "Atualizar" (force) escreveu métricas frescas. Um tick de fundo
  // que começou ANTES desse instante busca a versão em cache (45 s) e, se
  // chegar depois, sobrescreveria o fresco pelo velho — os dois não trocam
  // de sequência (o tick não incrementa `seq`). O tick confere este carimbo
  // e desiste quando um force o ultrapassou.
  const forcadasEm = useRef(0)

  // Assinatura da última resposta de métricas aceita. O tick de 60s reconstrói
  // o Map mesmo quando o payload é idêntico, e essa troca de identidade invalida
  // os `useMemo` da lista inteira (todas as linhas re-renderizam sem nada mudar).
  // Só escreve o estado quando o conteúdo de fato muda.
  const assinaturaMetricas = useRef<string>("")

  const carregar = useCallback(async (alvo: string | undefined, force: boolean) => {
    const mine = ++seq.current
    const primeiraDesteWorkspace = workspaceNaTela.current !== (alvo ?? null)
    if (primeiraDesteWorkspace) setCarregando(true)
    else setAtualizando(true)

    const [rWorkflows, rGrupos, rMetricas] = await Promise.allSettled([
      // Com os do assistente: eles são fluxos como os outros e a estante é
      // onde a pessoa acompanha o que existe. O chip "Assistente" recorta.
      GisFlowService.getWorkflows(alvo, { incluirDoAssistente: true }),
      GisFlowService.getWorkflowGroups(alvo),
      // Métricas sempre recortadas por workspace (spec §2.3): sem workspace
      // não há o que recortar — e a lista também virá vazia.
      alvo ? GisFlowService.getWorkflowMetricsList(JANELA_EM_DIAS, force, { workspace_id: alvo }) : Promise.resolve(null),
    ])
    if (mine !== seq.current) return

    const listagem = resposta(rWorkflows)
    const gruposRes = resposta(rGrupos)
    const metricasRes = resposta(rMetricas)

    if (listagem?.data && gruposRes?.data) {
      setWorkflows(listagem.data)
      setGrupos(gruposRes.data)
      setErro(null)
      setAtualizadoEm(Date.now())
      workspaceNaTela.current = alvo ?? null
    } else {
      // O que já estava na tela fica (é de quem recarregou); quem trocou de
      // workspace vê o bloco de erro por cima, porque `erro` manda na tela.
      const mensagem = mensagemDe(listagem, gruposRes)
      setErro(mensagem)
      // Sem carga aceita, o cartão de erro toma a tela e já anuncia a falha
      // (`role="alert"`); o toast repetiria o aviso ao leitor de tela. Ele é
      // da carga que falha com uma lista já na tela.
      if (workspaceNaTela.current !== undefined) createToast.error("Erro ao carregar projetos", mensagem)
    }

    if (!alvo) {
      assinaturaMetricas.current = ""
      setMetricas(new Map())
      setMetricasIndisponiveis(false)
    } else if (metricasRes?.data?.workflows) {
      if (force) forcadasEm.current = Date.now()
      // Alinha a assinatura para o primeiro tick de fundo não re-setar à toa.
      assinaturaMetricas.current = JSON.stringify(metricasRes.data.workflows)
      setMetricas(mapaDeMetricas(metricasRes.data.workflows))
      setMetricasIndisponiveis(false)
    } else {
      // Nulo, e não o mapa antigo: numa troca de workspace ele seria de
      // outra estante, e numa recarga a spec pede a lista sem a coluna.
      assinaturaMetricas.current = ""
      setMetricas(null)
      setMetricasIndisponiveis(true)
    }

    setCarregando(false)
    setAtualizando(false)
  }, [])

  // Recarrega ao trocar de workspace, esperando o context resolver qual é —
  // antes disso `current` é nulo e a chamada traria a lista de todos.
  useEffect(() => {
    if (workspaceLoading) return
    carregar(workspaceId, false)
  }, [workspaceLoading, workspaceId, carregar])

  // Só as métricas, sem ligar `carregando`/`atualizando` — senão a lista
  // piscaria a cada minuto. Não incrementa a sequência: uma carga completa
  // pedida no meio vence.
  useEffect(() => {
    if (workspaceLoading || !workspaceId || intervaloDasMetricasMs <= 0) return
    let ultimo = Date.now()
    async function atualizarMetricas() {
      // As métricas anotam a lista NA TELA. Sem ela (a 1ª carga falhou, ou a
      // do workspace novo ainda não chegou), o tick não tem o que anotar, e o
      // carimbo que ele grava tirava o cartão de erro da tela: ela passava a
      // dizer "primeiro uso" de uma estante que nem carregou.
      if (workspaceNaTela.current !== workspaceId) return
      const mine = seq.current
      const inicio = Date.now()
      ultimo = inicio
      const res = await GisFlowService.getWorkflowMetricsList(JANELA_EM_DIAS, false, { workspace_id: workspaceId })
      // Falhou, chegou tarde (outra carga assumiu), ou um "Atualizar" escreveu
      // dados frescos enquanto este tick buscava o cache: fica o que havia; o
      // próximo tick tenta de novo.
      if (mine !== seq.current || forcadasEm.current > inicio || !res.data?.workflows) return
      // Payload idêntico ao último aceito: não troca a identidade do Map, para
      // não re-renderizar a lista inteira a cada minuto sem motivo.
      const assinatura = JSON.stringify(res.data.workflows)
      if (assinatura === assinaturaMetricas.current) return
      assinaturaMetricas.current = assinatura
      setMetricas(mapaDeMetricas(res.data.workflows))
      setMetricasIndisponiveis(false)
      setAtualizadoEm(Date.now())
    }
    const timer = setInterval(() => {
      if (document.visibilityState === "visible") atualizarMetricas()
    }, intervaloDasMetricasMs)
    // Voltar para a aba depois de um tempo longe: atualiza na hora em vez de
    // esperar o próximo tick — mas não a cada alt-tab.
    const onVisibility = () => {
      if (document.visibilityState === "visible" && Date.now() - ultimo >= intervaloDasMetricasMs) atualizarMetricas()
    }
    document.addEventListener("visibilitychange", onVisibility)
    return () => {
      clearInterval(timer)
      document.removeEventListener("visibilitychange", onVisibility)
    }
  }, [workspaceLoading, workspaceId, intervaloDasMetricasMs])

  const recarregar = useCallback((opcoes: { force?: boolean } = {}) => {
    carregar(workspaceRef.current, opcoes.force ?? false)
  }, [carregar])

  return useMemo(() => ({
    workflows, grupos, metricas, carregando, atualizando, erro, metricasIndisponiveis, atualizadoEm,
    recarregar, definirWorkflows: setWorkflows, definirGrupos: setGrupos,
  }), [workflows, grupos, metricas, carregando, atualizando, erro, metricasIndisponiveis, atualizadoEm, recarregar])
}
