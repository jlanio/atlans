"use client"

import { createContext, PropsWithChildren, useContext } from "react"
import { useIsMobile } from "@/hooks/use-mobile"

/**
 * "Este canvas está sendo operado por toque, numa tela de telefone."
 *
 * Não é o mesmo que `useSubflowReadOnly`, apesar de as duas coisas resultarem
 * em menos edição na tela. Aquele é uma propriedade do CONTEXTO (o nó está
 * sendo desenhado dentro do visualizador de um sub-fluxo, onde ele nem é
 * editável); este é uma propriedade do DISPOSITIVO. Um nó pode estar nos dois
 * estados, em nenhum, ou só num deles, e o que cada um esconde é diferente —
 * misturá-los faria uma regra de layout apagar uma regra de domínio.
 *
 * Por que um contexto e não `useIsMobile()` em cada componente: o hook monta um
 * `matchMedia` com listener por instância. Com 50 nós no canvas, cada um com
 * card, ferramentas e pontos de conexão, isso são centenas de listeners
 * observando a MESMA media query e re-renderizando juntos a cada rotação de
 * tela. Aqui a query é observada uma vez e o valor desce por contexto.
 *
 * O gate é a largura, não o tipo de ponteiro: um tablet em paisagem tem toque
 * grosso mas espaço de sobra para o editor, e degradá-lo tiraria capacidade sem
 * ganho nenhum. Quem é estreito é que não comporta arrastar nó, puxar conexão e
 * ainda acertar um handle de 8px.
 */
const CanvasReadOnlyContext = createContext(false)

/** true quando o canvas deve se comportar como visualizador (telefone). */
export function useCanvasReadOnly(): boolean {
  return useContext(CanvasReadOnlyContext)
}

/** Observa a media query UMA vez e distribui o resultado. */
export function CanvasInteractionProvider({ children }: PropsWithChildren) {
  const somenteLeitura = useIsMobile()
  return (
    <CanvasReadOnlyContext.Provider value={somenteLeitura}>
      {children}
    </CanvasReadOnlyContext.Provider>
  )
}

/**
 * Mesma resposta do contexto, para quem está ACIMA do provider e não pode
 * consumi-lo — hoje só o próprio canvas, que precisa do valor para montar as
 * props do `<ReactFlow>`. Uma segunda observação da media query, não uma por nó.
 */
export const useCanvasReadOnlyRoot = useIsMobile
