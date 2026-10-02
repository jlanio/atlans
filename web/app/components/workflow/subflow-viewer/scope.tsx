"use client"
import { createContext, PropsWithChildren, useContext, useMemo } from "react"
import { INodeStatusWorkFlow } from "@/context/useFlowContext"

/** O que o card de um nó precisa saber sobre a execução dele. */
export type EstadoDeNo = Pick<
  INodeStatusWorkFlow,
  "status" | "error" | "duration" | "cache_hit"
>

/**
 * "Este nó está sendo desenhado no visualizador de sub-fluxo, não no editor."
 *
 * Separado do estado de execução de propósito. Quem lê só isto — a barra de
 * ferramentas do nó, o botão "+" de criar conexão — precisa de um booleano que
 * NUNCA muda enquanto o visualizador está aberto. Se lessem o mesmo contexto do
 * estado, re-renderizariam junto com ele: oito vezes por segundo durante um run
 * ao vivo, para todos os nós, por uma informação constante.
 */
const SubflowReadOnlyContext = createContext(false)

/** Estado de cada nó do sub-fluxo aberto, indexado pelo id LOCAL. */
const SubflowStatusContext = createContext<Map<string, EstadoDeNo> | null>(null)

/** true quando desenhado dentro do visualizador. Estável enquanto ele durar. */
export function useSubflowReadOnly(): boolean {
  return useContext(SubflowReadOnlyContext)
}

/**
 * Estado de execução dos nós do sub-fluxo, ou `null` fora do visualizador.
 *
 * Existe porque a fonte do estado muda junto com o contexto. No canvas do editor
 * ela é `statusWorkflow.nodes`, que o `useExecuteWorkflow` semeia a partir dos
 * próprios nós do canvas e depois só atualiza por id — nós de dentro de um
 * sub-fluxo nunca entram lá, porque o id deles chega prefixado e não casa com
 * nenhum. Quem conhece esses nós é a linha do tempo do painel, que cria uma
 * linha para cada id prefixado que aparece nos eventos.
 *
 * O escopo entrega o estado já resolvido, em vez de um prefixo para o card
 * aplicar: assim o card tem UM ponto de leitura, e a regra de qual fonte vale em
 * qual contexto fica num lugar só.
 */
export function useSubflowStatus(): Map<string, EstadoDeNo> | null {
  return useContext(SubflowStatusContext)
}

export function SubflowScope({
  estadoPorId,
  children,
}: PropsWithChildren<{ estadoPorId: Map<string, EstadoDeNo> }>) {
  // O provider do booleano fica por fora e com valor literal: seu contexto nunca
  // é invalidado, então os consumidores dele não acompanham o estado.
  const status = useMemo(() => estadoPorId, [estadoPorId])
  return (
    <SubflowReadOnlyContext.Provider value={true}>
      <SubflowStatusContext.Provider value={status}>
        {children}
      </SubflowStatusContext.Provider>
    </SubflowReadOnlyContext.Provider>
  )
}
