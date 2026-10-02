"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { useReactFlow, Edge } from "@xyflow/react"
import { INodeContext } from "@/context/useFlowContext"
import { GisFlowService } from "@/service/GisFlowService"
import type { IWorkflowContract } from "@/service/types"
import { reancorarArestasDoNo } from "@/app/components/workflow/utils/node-ports"


const DEBOUNCE_MS = 300

/**
 * Sincroniza portas (inputs/outputs) dinamicas dos nodes SubWorkflow com o
 * contrato declarado pelo workflow alvo (SubWorkflowInput + SubWorkflowOutput).
 *
 * Por que: o catalogo /nodes nao tem como prever as chaves de cada
 * sub-fluxo. Renderizamos handles dinamicos no canvas buscando o contract
 * por workflowHash configurado em cada node SubWorkflow.
 *
 * Estrategia anti-loop:
 *   - cache em memoria por hash (evita re-fetch entre re-renders)
 *   - comparacao de portas atual vs nova antes de setNodes (evita
 *     re-render desnecessario do ReactFlow)
 */
export function useSubWorkflowContractSync(nodes: INodeContext[]) {
  const { setNodes, setEdges } = useReactFlow<INodeContext, Edge>()
  const cacheRef = useRef<Map<string, IWorkflowContract | null>>(new Map())
  const inflightRef = useRef<Set<string>>(new Set())

  // Chave estavel para o dep array: re-roda apenas quando hashes mudam
  // (add/remove de SubWorkflow ou edicao de workflowHash). Memoizada porque no
  // corpo do hook a varredura rodava a cada render do canvas — o canvas passa
  // uma projecao de `nodes` que ignora mudanca de posicao.
  const subworkflowSignature = useMemo(() => nodes
    .filter((n) => (n.data as { name?: string })?.name === "SubWorkflow")
    .map((n) => `${n.id}:${((n.data?.properties ?? {}) as { workflowHash?: string }).workflowHash ?? ""}`)
    .join("|"), [nodes])

  // Debounce: operador digitando hash caractere-por-caractere nao deve
  // disparar uma request por keystroke. Aguarda 300ms de inatividade.
  const [debouncedSignature, setDebouncedSignature] = useState(subworkflowSignature)
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSignature(subworkflowSignature), DEBOUNCE_MS)
    return () => clearTimeout(t)
  }, [subworkflowSignature])

  useEffect(() => {
    const subworkflowNodes = nodes.filter(
      (n) => (n.data as { name?: string })?.name === "SubWorkflow",
    )
    if (subworkflowNodes.length === 0) return

    let cancelled = false

    const hashDoNo = (node: INodeContext) =>
      String(((node.data?.properties ?? {}) as Record<string, unknown>).workflowHash ?? "").trim()

    async function syncAll() {
      // Busca os contratos em PARALELO. Antes era um `await` por nó dentro do
      // laço — um waterfall de N requisições, cada uma esperando a anterior.
      // Coleta os hashes ainda não cacheados nem em voo, marca em voo, e resolve
      // todos juntos; só então aplica as portas por nó, lendo o cache. A ordem
      // entre nós não importa (cada applyPorts mira um id disjunto e é idempotente).
      const aBuscar = new Set<string>()
      for (const node of subworkflowNodes) {
        const hash = hashDoNo(node)
        if (hash && cacheRef.current.get(hash) === undefined && !inflightRef.current.has(hash)) {
          aBuscar.add(hash)
        }
      }

      if (aBuscar.size > 0) {
        await Promise.all(
          [...aBuscar].map(async (hash) => {
            inflightRef.current.add(hash)
            try {
              const resp = await GisFlowService.getWorkflowContract(hash)
              cacheRef.current.set(hash, resp?.data ?? null)
            } catch {
              cacheRef.current.set(hash, null)
            } finally {
              inflightRef.current.delete(hash)
            }
          }),
        )
        if (cancelled) return
      }

      for (const node of subworkflowNodes) {
        const hash = hashDoNo(node)
        // Sem hash: limpa portas dinâmicas. Hash em voo de uma rodada anterior
        // (ainda não cacheado): `?? null` aplica portas vazias, como antes.
        const contract = hash ? (cacheRef.current.get(hash) ?? null) : null
        const inputs = (contract?.inputs ?? []).map((p) => ({
          name: p.name,
          description: p.description ?? undefined,
        }))
        const outputs = (contract?.outputs ?? []).map((p) => ({
          name: p.name,
          description: p.description ?? undefined,
        }))
        applyPorts(node.id, inputs, outputs)
      }
    }

    function applyPorts(
      nodeId: string,
      inputs: { name: string; description?: string }[],
      outputs: { name: string; description?: string }[],
    ) {
      setNodes((nds) =>
        nds.map((n) => {
          if (n.id !== nodeId) return n
          const currentInputs = (n.data?.inputs ?? []) as { name: string }[]
          const currentOutputs = (n.data?.outputs ?? []) as { name: string }[]
          const sameInputs =
            currentInputs.length === inputs.length &&
            currentInputs.every((p, i) => p.name === inputs[i]?.name)
          const sameOutputs =
            currentOutputs.length === outputs.length &&
            currentOutputs.every((p, i) => p.name === outputs[i]?.name)
          if (sameInputs && sameOutputs) return n
          return {
            ...n,
            data: { ...n.data, inputs, outputs },
          }
        }),
      )

      // Re-ancora as arestas cujo handle se perdeu no load, agora que as portas
      // do contrato chegaram — corrige o colapso "tudo na primeira entrada" ao
      // dar F5. A lógica é pura (`reancorarArestasDoNo`) e idempotente: devolve o
      // MESMO array quando nada muda, para não realimentar `useEdgesState`.
      setEdges((eds) =>
        reancorarArestasDoNo(
          eds,
          nodeId,
          inputs.map((p) => p.name),
          outputs.map((p) => p.name),
        ),
      )
    }

    syncAll()

    return () => {
      cancelled = true
    }
    // Re-roda apenas quando a assinatura debounced muda — opera deixou de
    // digitar por DEBOUNCE_MS.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSignature])
}
