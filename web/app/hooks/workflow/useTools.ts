import { useState, useRef, useEffect, useCallback } from "react";

export type ToolState = 'onFocus' | 'leave' | 'disable'

const DELAY_STATE = 500

export const useTools = () => {

  const [toolState, setToolState] = useState<ToolState>('disable')
  const toolStateRef = useRef<ToolState>('disable')

  // `useCallback` sem dependências: os pais repassam esta função dentro de
  // `onMouseEnter`/`onMouseLeave` para o card do nó. Enquanto ela era declarada
  // solta no corpo do hook, nascia com identidade nova a cada render e nenhuma
  // memoização rio abaixo conseguia segurar nada.
  const handleToolState = useCallback((state: ToolState) => {
    setToolState(state)
    toolStateRef.current = state
  }, [])

  // O recolhimento tardio vira um timer cancelável: com o `await` de antes o
  // temporizador sobrevivia ao desmonte do nó e ainda tentava um setState.
  useEffect(() => {
    if (toolState !== 'leave') return
    const timer = setTimeout(() => {
      if (toolStateRef.current === "leave") handleToolState('disable')
    }, DELAY_STATE)
    return () => clearTimeout(timer)
  }, [toolState, handleToolState])

  return {
    toolState,
    handleToolState
  };
}
