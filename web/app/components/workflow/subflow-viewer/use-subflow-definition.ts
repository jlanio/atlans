"use client"
import { useEffect, useReducer, useState } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import type { IWorkflow } from "@/service/types"

/**
 * Cache por hash, no módulo (e não numa ref do componente): descer e voltar pela
 * trilha remonta o visualizador, e sem isto cada passo refaria a mesma busca.
 * Um sub-fluxo é lido muitas vezes e editado poucas — e o botão de recarregar
 * dá a saída para o caso raro.
 *
 * Teto porque a sessão é longa e uma definition não é pequena: sem ele, visitar
 * muitos sub-fluxos segura todos eles em memória até a página recarregar.
 * Descarte pelo mais antigo, que num drill-down é o nível de que já se saiu.
 */
const cache = new Map<string, IWorkflow>()
const MAX_EM_CACHE = 12

function guardar(hash: string, workflow: IWorkflow) {
  if (cache.size >= MAX_EM_CACHE) {
    const maisAntigo = cache.keys().next().value
    if (maisAntigo !== undefined) cache.delete(maisAntigo)
  }
  cache.set(hash, workflow)
}

export interface SubflowDefinition {
  workflow: IWorkflow | null
  carregando: boolean
  erro: string | null
  recarregar(): void
}

/**
 * Carrega o workflow de um sub-fluxo pelo hash.
 *
 * `workflow` é lido do cache no render, e não guardado em estado: guardado, ele
 * sobrevivia à troca de nível e o visualizador desenhava o grafo do nível
 * ANTERIOR enquanto o novo carregava — com o agravante de que as ressalvas,
 * comparando os eventos do nível novo contra o grafo velho, acusavam todos os
 * nós como "não existem mais no grafo". Lendo do cache, ou o grafo certo já está
 * lá, ou não há grafo — e a tela mostra que está carregando.
 *
 * Nenhum endpoint novo: `GET /workflows/{hash}` já devolve a definition, e a
 * autorização dele cobre o caso — um sub-fluxo só pode ser chamado de dentro do
 * mesmo workspace do pai (validate_subworkflow_references_against_db), então
 * quem alcança o pai alcança o filho.
 */
export function useSubflowDefinition(workflowHash: string | null): SubflowDefinition {
  // Só para repintar quando o fetch popula o cache — o dado em si vem do Map.
  const [, repintar] = useReducer((n: number) => n + 1, 0)
  const [versao, setVersao] = useState(0)
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  const workflow = workflowHash ? cache.get(workflowHash) ?? null : null

  useEffect(() => {
    if (!workflowHash || cache.has(workflowHash)) {
      setCarregando(false)
      setErro(null)
      return
    }

    let cancelado = false
    setCarregando(true)
    setErro(null)

    GisFlowService.getWorkflowById(workflowHash).then(res => {
      if (cancelado) return
      setCarregando(false)
      if (res?.error || !res?.data) {
        setErro(res?.error?.message ?? "Não foi possível carregar o sub-fluxo.")
        return
      }
      guardar(workflowHash, res.data)
      repintar()
    })

    return () => { cancelado = true }
  }, [workflowHash, versao])

  return {
    workflow,
    carregando,
    erro,
    recarregar: () => {
      if (workflowHash) cache.delete(workflowHash)
      setVersao(v => v + 1)
    },
  }
}
