"use client"

import { useEffect, useReducer, type ReactNode } from "react"
import { useEdges, useNodes, useStoreApi } from "@xyflow/react"
import { TbAlertTriangle, TbCheck, TbCloudCheck, TbCloudOff, TbLoader, TbPencil } from "react-icons/tb"
import { INodeContext } from "@/context/useFlowContext"
import { useWorkflowSaveStore } from "@/app/stores/workflowSaveStore"
import { montarPayloadDoGrafo, useSaveWorkflow } from "@/app/hooks/workflow/useSaveWorkflow"
import { rotuloDeSalvo } from "./utils/rotulo-de-salvo"
import { cn } from "@/lib/utils"

/** Inatividade exigida antes de comparar o grafo com o último snapshot. */
const ATRASO_DA_DETECCAO_MS = 300

/** Cadência com que "Salvo há N min" é recalculado em repouso. */
const TIQUE_DO_RELOGIO_MS = 30_000

/**
 * Detecta edições não salvas comparando o grafo com o último snapshot.
 *
 * Mora aqui, e não em `useSaveWorkflow`, porque aquele hook está montado em
 * vários pontos da árvore do canvas (editor, botão Salvar, botão Executar, este
 * chip) — a detecção rodava uma vez por montagem a cada quadro de arraste, cada
 * passada mapeando todos os nós e serializando o grafo inteiro. Este indicador
 * é o único ponto montado uma vez só, e é ele quem mostra o resultado.
 *
 * A comparação é adiada: durante um arraste `nodes` troca de identidade a cada
 * pointermove, e comparar por quadro fazia fluxos com Script Python ou SQL
 * grandes virarem slideshow. O preço é o rótulo aparecer até 300ms depois da
 * edição.
 */
function useDeteccaoDeAlteracoes() {
  // Assinaturas só como GATILHO: quem lê o grafo é o `getState()` lá embaixo,
  // depois do atraso. Este componente não renderiza nada dependente delas, então
  // o custo por quadro de arraste é um render vazio e um re-agendamento.
  const nodes = useNodes<INodeContext>()
  const edges = useEdges()
  const workflowName = useWorkflowSaveStore(s => s.workflowName)
  const lastSavedSnapshot = useWorkflowSaveStore(s => s.lastSavedSnapshot)
  const flowStore = useStoreApi()

  useEffect(() => {
    if (!lastSavedSnapshot) return

    const timer = setTimeout(() => {
      const { nodes: nosAtuais, edges: arestasAtuais } = flowStore.getState()
      const { nodesReq, edgesReq } = montarPayloadDoGrafo(
        nosAtuais as unknown as INodeContext[],
        arestasAtuais,
      )
      const store = useWorkflowSaveStore.getState()

      if (!store.isDirty(nodesReq, edgesReq, store.workflowName)) {
        // Voltou ao estado salvo (desfez a edição, apagou o que tinha criado): o
        // aviso não tem mais razão de existir. Só o 'unsaved' é derrubado — os
        // outros estados não são deduzidos do grafo.
        if (store.saveStatus === 'unsaved') store.setStatus('idle')
        return
      }

      // Autocorreção APENAS dentro da janela de hidratação (ver
      // `autocorrigirSnapshot`): o snapshot inicial, tirado logo após
      // setNodes/setEdges, pode divergir sutilmente do estado atual porque o
      // ReactFlow ainda estava medindo dimensions/positions.
      //
      // A regra é de TEMPO, não "a primeira diferença que aparecer". Como esta
      // comparação é debounced, a primeira diferença que ela vê já é o resultado
      // FINAL do arraste (ou do Aplicar no modal): uma flag de uso único engolia
      // a edição inteira dentro do snapshot de referência — sem "Não salvo",
      // com Ctrl+S caindo no early-return do isDirty e com o Executar mandando o
      // executor rodar a definição anterior.
      if (store.autocorrigirSnapshot(nodesReq, edgesReq, store.workflowName)) return

      // Um save em voo, uma falha e o pedido de nome não são estados que o grafo
      // desfaz. A remedição do ReactFlow também troca a identidade de `nodes`,
      // e rebaixava "Falha ao salvar" a "Não salvo" logo depois da falha —
      // levando junto o botão de tentar de novo.
      if (store.saveStatus === 'idle' || store.saveStatus === 'saved') store.setStatus('unsaved')
    }, ATRASO_DA_DETECCAO_MS)

    return () => clearTimeout(timer)
  }, [nodes, edges, workflowName, lastSavedSnapshot, flowStore])
}

/** Re-renderiza a cada tique enquanto `ativo`, para "há N min" não envelhecer. */
function useRelogio(ativo: boolean) {
  const [, tique] = useReducer((n: number) => n + 1, 0)
  useEffect(() => {
    if (!ativo) return
    const intervalo = setInterval(tique, TIQUE_DO_RELOGIO_MS)
    return () => clearInterval(intervalo)
  }, [ativo])
}

interface Rotulo {
  texto: string
  icone: ReactNode
  classe: string
}

/**
 * Estado do salvamento, ao lado do caminho do workflow.
 *
 * Fica visível SEMPRE que há algo a dizer — inclusive em repouso ("Salvo há 5
 * min"). A versão anterior era uma pílula centrada que sumia 3s depois do save
 * e não mostrava nada no estado normal: entre um "Salvo" que passava rápido e
 * um "Salvando…" que durava o tempo do PUT, a impressão era de que não havia
 * feedback nenhum. O erro ganhou estado próprio, com o retry no lugar em que
 * se lê a falha; antes ele caía em "Não salvo" e a mensagem ia embora com o
 * toast.
 *
 * Renderizar como filho de `<WorkflowLocation>`: é ela quem posiciona a fileira
 * sobre o canvas e dá aos filhos diretos o `pointer-events` (o retry precisa).
 */
const GlobalSaveIndicator = () => {
  const status = useWorkflowSaveStore(s => s.saveStatus)
  const lastSavedAt = useWorkflowSaveStore(s => s.lastSavedAt)
  const lastError = useWorkflowSaveStore(s => s.lastError)
  const { saveWorkflow } = useSaveWorkflow()
  useDeteccaoDeAlteracoes()

  const emRepouso = status === 'idle' && lastSavedAt !== null
  useRelogio(emRepouso)

  const rotulo: Rotulo | null = (() => {
    switch (status) {
      case 'idle':
        // Sem save conhecido (workflow novo) não há o que afirmar.
        return emRepouso
          ? { texto: rotuloDeSalvo(lastSavedAt), icone: <TbCloudCheck size={13} />, classe: "text-muted-foreground" }
          : null
      case 'unsaved':
        return { texto: "Alterações não salvas", icone: <TbPencil size={13} />, classe: "text-amber-500 border-amber-500/40" }
      case 'saving':
        return { texto: "Salvando…", icone: <TbLoader className="animate-spin" size={13} />, classe: "text-muted-foreground" }
      case 'saved':
        return { texto: "Salvo", icone: <TbCheck size={13} />, classe: "text-green-500 border-green-500/40" }
      case 'error':
        return { texto: "Falha ao salvar", icone: <TbAlertTriangle size={13} />, classe: "text-destructive border-destructive/40" }
      case 'needs_name':
        return { texto: "Sem nome", icone: <TbCloudOff size={13} />, classe: "text-amber-500 border-amber-500/40" }
    }
  })()

  if (!rotulo) return null

  return (
    <div
      role="status"
      // Em repouso o texto muda sozinho a cada minuto; anunciar isso num leitor
      // de tela seria um relógio falante. Os outros estados são resposta a uma
      // ação do usuário, e aí o anúncio é o feedback.
      aria-live={emRepouso ? "off" : "polite"}
      title={status === 'error' ? lastError ?? undefined : undefined}
      data-save-status={status}
      className={cn(
        "flex h-8 shrink-0 items-center gap-1.5 rounded-lg border border-border bg-background/85 px-2.5 text-xs font-medium shadow-xs backdrop-blur-sm transition-colors duration-200",
        rotulo.classe,
      )}
    >
      {rotulo.icone}
      <span>{rotulo.texto}</span>
      {status === 'error' && (
        <button
          type="button"
          onClick={() => { saveWorkflow() }}
          className="ml-1 rounded px-1.5 py-0.5 text-foreground underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
        >
          Tentar novamente
        </button>
      )}
    </div>
  )
}

export default GlobalSaveIndicator
