"use client"

import { useEffect, useMemo } from "react"
import { useReactFlow, Edge } from "@xyflow/react"

import { INodeContext } from "@/context/useFlowContext"
import { lerPortas, reconciliarPortas } from "@/app/components/workflow/utils/node-ports"

/**
 * Mantém `data.inputs`/`data.outputs` em dia com a propriedade `ports` dos nós
 * de portas dinâmicas — as ENTRADAS do Script Python / SubWorkflowOutput
 * (`dynamic_inputs`) e as SAÍDAS do SubWorkflowInput (`outputs_from_ports`).
 *
 * Sem isto a funcionalidade só valeria depois de recarregar a página: quem monta
 * os pontos de conexão a partir de `ports` é `loadNodes` (ao abrir o fluxo) e o
 * `addNode` (ao criar o nó), mas o "Aplicar" do painel de configuração grava
 * `data.properties` e NÃO recalcula `data.inputs`/`data.outputs`. A pessoa
 * definiria as portas, aplicaria, e o nó continuaria com um ponto anônimo.
 *
 * Um efeito, e não um remendo no `saveNodeConfig`, porque `properties` muda por
 * vários caminhos — aplicar, desfazer, refazer, colar um nó. Cobrir só um deles
 * deixaria os outros com o canvas descrevendo um nó que não é mais aquele.
 *
 * Espelha `useSubWorkflowContractSync`, inclusive na proteção contra laço: a
 * reconciliação devolve o mesmo array quando nada mudou, e é isso que impede o
 * efeito de se realimentar a cada render.
 */
export function useDynamicPortsSync(nodes: INodeContext[]) {
  const { setNodes } = useReactFlow<INodeContext, Edge>()

  // Assinatura estável para o dep array: só re-roda quando as portas de algum
  // nó dinâmico mudam, e não a cada movimento de nó no canvas. Memoizada porque
  // no corpo do hook a varredura rodava a cada render do canvas — o canvas passa
  // uma projeção de `nodes` que ignora mudança de posição.
  const assinatura = useMemo(() => nodes
    .filter(n => {
      const d = n.data as { dynamic_inputs?: boolean; outputs_from_ports?: boolean }
      return d?.dynamic_inputs || d?.outputs_from_ports
    })
    .map(n => `${n.id}:${lerPortas((n.data?.properties as Record<string, unknown>)?.ports).join(",")}`)
    .join("|"), [nodes])

  useEffect(() => {
    if (!assinatura) return
    setNodes(reconciliarPortas)
  }, [assinatura, setNodes])
}
