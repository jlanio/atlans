"use client"

import { useEffect, useMemo } from "react"
import { useUpdateNodeInternals } from "@xyflow/react"

import { INodeContext } from "@/context/useFlowContext"

/** Assinatura dos pontos de conexão de um nó: quais existem, e em que ordem. */
function assinaturaDeHandles(n: INodeContext): string {
  const portas = (lista: unknown) =>
    ((lista ?? []) as { name: string }[]).map(p => p.name).join(",")
  return `${n.id}:${portas(n.data?.inputs)}>${portas(n.data?.outputs)}`
}

/**
 * Avisa o React Flow quando os pontos de conexão de um nó mudam.
 *
 * O React Flow MEDE os handles de cada nó uma vez e guarda posições e ids num
 * registro interno. Handles acrescentados a um nó já renderizado são
 * desenhados pelo React, mas não entram nesse registro — e o resultado é o
 * sintoma que não parece um bug de estado: os pontos aparecem na tela e
 * simplesmente não aceitam conexão. `updateNodeInternals` força a remedição.
 *
 * Vale para QUALQUER origem de portas dinâmicas, e não só para as do Script
 * Python: o contrato dos sub-fluxos (`useSubWorkflowContractSync`) muda os
 * mesmos campos e tinha o mesmo defeito, só que ninguém tinha esbarrado nele.
 * A regra é uma só — mudou o conjunto de handles, remeça — então mora num
 * lugar só.
 *
 * Roda DEPOIS de `data.inputs` já ter mudado: a dependência é a assinatura dos
 * handles, não a das portas. Medir antes de o React ter posto os elementos no
 * DOM leria o nó do jeito antigo, e o efeito não voltaria a rodar.
 */
export function useHandleRegistrySync(nodes: INodeContext[]) {
  const updateNodeInternals = useUpdateNodeInternals()

  // No corpo do hook, a varredura acontecia a cada render do canvas — inclusive
  // por quadro de arraste, e por mudança de tema ou de status de save. O canvas
  // entrega uma projeção que só troca de identidade quando um nó entra, sai ou
  // tem o `data` substituído, e é isso que dá valor ao useMemo aqui.
  const assinatura = useMemo(() => nodes.map(assinaturaDeHandles).join("|"), [nodes])

  useEffect(() => {
    if (!nodes.length) return
    updateNodeInternals(nodes.map(n => n.id))
    // Só a assinatura: arrastar um nó muda `nodes` e não muda handle nenhum, e
    // remedir tudo a cada quadro de um arrasto custaria caro à toa.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assinatura])
}
