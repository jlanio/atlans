import { useState, useRef, useEffect, useCallback } from "react";

export type ToolState = 'onFocus' | 'leave' | 'disable'

const DELAY_STATE = 500

export const useTools = () => {

  const [toolState, setToolState] = useState<ToolState>('disable')
  const toolStateRef = useRef<ToolState>('disable')

  // `useCallback` with no dependencies: the parents pass this function inside
  // `onMouseEnter`/`onMouseLeave` down to the node card. While it was declared
  // loose in the hook body, it was born with a new identity on every render and
  // no memoization downstream could hold anything.
  const handleToolState = useCallback((state: ToolState) => {
    setToolState(state)
    toolStateRef.current = state
  }, [])

  // The delayed collapse becomes a cancelable timer: with the earlier `await` the
  // timer outlived the node's unmount and still attempted a setState.
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
