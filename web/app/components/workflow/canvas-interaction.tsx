"use client"

import { createContext, PropsWithChildren, useContext } from "react"
import { useIsMobile } from "@/hooks/use-mobile"

/**
 * "This canvas is being operated by touch, on a phone screen."
 *
 * It isn't the same as `useSubflowReadOnly`, even though both result in less
 * editing on screen. That one is a property of the CONTEXT (the node is being
 * drawn inside a sub-workflow viewer, where it isn't even editable); this one is
 * a property of the DEVICE. A node can be in both states, in neither, or in just
 * one, and what each one hides is different — mixing them would let a layout
 * rule erase a domain rule.
 *
 * Why a context and not `useIsMobile()` in each component: the hook sets up a
 * `matchMedia` with a listener per instance. With 50 nodes on the canvas, each
 * with a card, tools and connection points, that's hundreds of listeners
 * watching the SAME media query and re-rendering together on every screen
 * rotation. Here the query is watched once and the value flows down via context.
 *
 * The gate is the width, not the pointer type: a tablet in landscape has coarse
 * touch but plenty of room for the editor, and degrading it would take away
 * capability for no gain at all. It's the narrow screen that can't accommodate
 * dragging a node, pulling a connection and still hitting an 8px handle.
 */
const CanvasReadOnlyContext = createContext(false)

/** true when the canvas should behave as a viewer (phone). */
export function useCanvasReadOnly(): boolean {
  return useContext(CanvasReadOnlyContext)
}

/** Watches the media query ONCE and distributes the result. */
export function CanvasInteractionProvider({ children }: PropsWithChildren) {
  const readOnly = useIsMobile()
  return (
    <CanvasReadOnlyContext.Provider value={readOnly}>
      {children}
    </CanvasReadOnlyContext.Provider>
  )
}

/**
 * Same answer as the context, for whoever is ABOVE the provider and can't
 * consume it — today only the canvas itself, which needs the value to build the
 * `<ReactFlow>` props. A second watch of the media query, not one per node.
 */
export const useCanvasReadOnlyRoot = useIsMobile
