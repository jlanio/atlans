"use client"

import { useWorkflowExecutionStore } from "@/app/stores/workflowExecutionStore";
import { useTools } from "@/app/hooks/workflow/useTools";
import { cn } from "@/lib/utils";
import { EdgeProps, EdgeLabelRenderer, useStoreApi, getSmoothStepPath } from "@xyflow/react"
import { MdDelete } from "react-icons/md"
import { useState } from "react"
import { getLaneOffset } from "../utils/edge-bundling"
import { getCandidateKeys, sourceHandleDaChave } from "../utils/resolve-edge-keys"
import { corDoTom, tomDaAresta } from "../utils/exec-colors"
import { useSubflowReadOnly, useSubflowStatus } from "../subflow-viewer/scope"

// The Conditional's routing handles. Only decides whether the badge becomes a key
// selector — the COLOR comes from `tomDaAresta`, which already knows these same handles.
const BRANCH_HANDLE = new Set(["true", "false"])

const CustomEdge = ({
  id,
  source,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourceHandleId,
  sourcePosition,
  targetPosition,
  data,
}: EdgeProps) => {
  const [hovered, setHovered] = useState(false)
  const [editando, setEditing] = useState(false)
  const store = useStoreApi()
  const { toolState, handleToolState } = useTools()
  // Filled in only when the edge is being drawn inside the sub-workflow viewer —
  // see subflow-viewer/scope. Zero cost in the editor: `useContext` without a
  // provider returns the literal default and never re-renders.
  const inViewer = useSubflowReadOnly()
  const subflowStatus = useSubflowStatus()
  // Scalar selectors by id: subscribing to `statusWorkflow` (a new object on every
  // WS message) re-rendered ALL visible edges, and each one also rebuilt its own
  // Map over the whole node list.
  const statusCanvas = useWorkflowExecutionStore(s => s.statusById.get(source)?.status)
  const inLosingBranch = useWorkflowExecutionStore(s => !!s.losingEdgeIds?.has(id))

  // Same rule as the card (see icon-root): inside the viewer the state comes from
  // the scope. `statusById` only knows the nodes of the editor canvas — the
  // child's ids arrive prefixed and match none, so the sub-workflow edge read the
  // status of the PARENT node that happened to have the same local id.
  const sourceStatus = subflowStatus ? subflowStatus.get(source)?.status : statusCanvas
  // `losingEdgeIds` is computed over the editor canvas edges and doesn't know the
  // child's graph — applying it in here would dash edges by id
  // coincidence.
  const isLosing = !inViewer && inLosingBranch

  // Its own lane when more than one edge connects the same pair of nodes.
  // `getState()` instead of `useEdges()` on purpose: it doesn't create a
  // subscription per edge, and the EdgeRenderer already re-renders this component
  // when the edges array changes.
  const lane = getLaneOffset(store.getState().edges, id)

  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    borderRadius: 10,
    centerX: (sourceX + targetX) / 2 + lane,
  })

  const handleKey = sourceHandleId ?? ""

  const color = corDoTom(tomDaAresta(sourceStatus, handleKey, isLosing))

  // Hover and execution no longer share the same effect. Before, hovering over an
  // IDLE edge during a run made it look alive — the canvas's strongest channel
  // ("data flowing") triggered by a reading gesture.
  const edgeActive = sourceStatus === "started" && !isLosing
  // A rejected branch recedes via dashes + neutral + a bit of opacity. DEEP
  // opacity remains reserved for the path highlight: the two channels
  // multiply, and overdoing it here would completely erase a rejected edge that
  // is inside the focused path.
  const edgeOpacity = isLosing ? 0.45 : 0.85

  const label = (data?.from_key as string) ?? (handleKey || null)
  const isToolOpen = toolState !== "disable"

  // Data outputs of the source node. Switching only makes sense when there's more
  // than one — with just one there's no choice, and routing handles (true/false)
  // define the branch, not the data.
  // No useMemo on purpose: the deps would be [store, source], which never change,
  // and the list would freeze. Dynamic-port nodes (SubWorkflow) change their
  // outputs after mount, and the selector would start offering ports that no
  // longer exist. `getState()` doesn't create a subscription and the call is O(ports).
  const candidatos = getCandidateKeys(
    store.getState().nodeLookup.get(source)?.data as Parameters<typeof getCandidateKeys>[0],
  )
  const canSwitch = candidatos.length > 1 && !BRANCH_HANDLE.has(handleKey)

  const chooseKey = (nome: string) => {
    const atual = store.getState().edgeLookup.get(id)
    if (!atual) return
    // F9: on a multi-output node the invariant is sourceHandle == from_key; changing
    // only from_key left source_handle (old port) and from_key (new port) in
    // disagreement, and resolveSourceHandle (edge-persistence) re-anchored the line
    // to the OLD port after reload.
    //
    // But only what the node draws as a handle is a REAL port — and that is
    // `outputs` with 2+ outputs, never a field without `port`. Syncing the
    // sourceHandle with a field without a connection point (which the selector
    // offers via getCandidateKeys) pointed the line at a nonexistent handle and
    // React Flow stopped drawing it: the edge VANISHED on choosing the key.
    // `sourceHandleDaChave` returns `undefined` when there's nothing to change;
    // otherwise the named handle or `null` (anonymous, which still clears a ghost
    // handle already stored).
    const saidas = (store.getState().nodeLookup.get(source)?.data as { outputs?: Array<{ name?: string }> } | undefined)?.outputs
    const newHandle = sourceHandleDaChave(saidas, nome)
    // Emits as an EdgeChange instead of a direct setEdges: that's what makes the
    // change go through `handleEdgesChange` on the canvas and enter the
    // undo/redo history. With setEdges, the change was persisted (autosave watches
    // `edges`) but Ctrl+Z didn't undo it.
    store.getState().triggerEdgeChanges([{
      id,
      type: "replace",
      item: {
        ...atual,
        sourceHandle: newHandle === undefined ? atual.sourceHandle : newHandle,
        data: { ...atual.data, from_key: nome },
      },
    }])
    setEditing(false)
  }

  return (
    <>
      <g style={{ "--exec-color": color } as React.CSSProperties}>
        {/* Glow under the active line. A wide, translucent stroke, not a
            `filter: blur()`: an SVG filter per edge is expensive and creates its
            own surface. It comes FIRST because in SVG whatever is drawn earlier
            stays behind. */}
        {edgeActive && (
          <path
            data-role="edge-glow"
            d={edgePath}
            fill="none"
            stroke="var(--exec-color)"
            strokeWidth={7}
            strokeLinecap="round"
            className="edge-glow-pulse"
            style={{ pointerEvents: "none" }}
          />
        )}

        {/* Main edge — a losing branch gets an explicit dash pattern instead of
            just opacity, making it clear the branch was rejected rather than
            looking "not yet executed". */}
        <path
          data-role="edge-path"
          d={edgePath}
          fill="none"
          stroke="var(--exec-color)"
          strokeWidth={hovered ? 2.5 : 1.5}
          strokeOpacity={edgeOpacity}
          strokeLinecap="round"
          strokeDasharray={isLosing ? "3 5" : undefined}
        />

        {/* Flow — dashes marching in the direction of the data.

            Active: two streams in parallax. A single stream reads as a
            sliding dashed line; two of different gauge and speed read as
            traffic. The dasharrays exactly close the period of the matching
            keyframe (3+8=11, 9+20=29), otherwise the loop jumps.

            Under the cursor: ONE stream and no glow. Crisp enough to teach the
            direction, without passing for a live edge. */}
        {edgeActive ? (
          <>
            <path
              data-role="edge-flow"
              d={edgePath}
              fill="none"
              stroke="var(--exec-color)"
              strokeWidth={1.4}
              strokeLinecap="round"
              strokeDasharray="3 8"
              className="edge-flow-fast"
              style={{ pointerEvents: "none" }}
            />
            <path
              data-role="edge-flow"
              d={edgePath}
              fill="none"
              stroke="var(--exec-color)"
              strokeWidth={2.6}
              strokeLinecap="round"
              strokeDasharray="9 20"
              className="edge-flow-slow"
              style={{ pointerEvents: "none" }}
            />
          </>
        ) : hovered && (
          <path
            data-role="edge-flow"
            d={edgePath}
            fill="none"
            stroke="var(--exec-color)"
            strokeWidth={2.4}
            strokeLinecap="round"
            strokeDasharray="6 12"
            className="edge-flow-hint"
            style={{ pointerEvents: "none" }}
          />
        )}

        {/* Invisible hover area (to make click/hover easier) */}
        <path
          d={edgePath}
          fill="none"
          stroke="transparent"
          strokeWidth={32}
          onMouseEnter={() => { setHovered(true); handleToolState("onFocus") }}
          onMouseLeave={() => { setHovered(false); handleToolState("leave") }}
          style={{ pointerEvents: "stroke", cursor: "pointer" }}
        />
      </g>

      <EdgeLabelRenderer>
        {/* Badge with the label (from_key or true/false) — edge midpoint.
            With more than one candidate it becomes a button: it was the only way
            to fix the key later, since before, choosing wrong forced you to
            delete the edge and redo the connection. On hover it moves up a line
            to make room for the delete button, instead of disappearing. */}
        {(label || canSwitch) && (
          <div
            data-edge-id={id}
            data-role="edge-label"
            className={cn(
              "absolute z-[20] transition-transform duration-150",
              canSwitch ? "pointer-events-auto" : "pointer-events-none",
            )}
            style={{
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`
                + (isToolOpen ? " translateY(-16px)" : ""),
              // `EdgeLabelRenderer` is a portal: this div is not inside the
              // edge's <g> and wouldn't inherit the variable from there.
              "--exec-color": color,
            } as React.CSSProperties}
            onMouseEnter={() => { setHovered(true); handleToolState("onFocus") }}
            onMouseLeave={() => { setHovered(false); handleToolState("leave") }}
          >
            {canSwitch ? (
              <button
                type="button"
                title="Trocar a saída que passa por esta aresta"
                onClick={() => setEditing(v => !v)}
                className="text-[10px] font-mono px-1 rounded cursor-pointer hover:brightness-125"
                // `color-mix` and not a hex alpha suffix: the color is now a
                // token (`var(--exec-*)`), and appending "22" to it isn't a color.
                style={{
                  background: "color-mix(in oklch, var(--exec-color) 12%, transparent)",
                  color: "var(--exec-color)",
                  border: "1px solid color-mix(in oklch, var(--exec-color) 32%, transparent)",
                }}
              >
                {label || "escolher"} ▾
              </button>
            ) : (
              <span
                className="text-[10px] font-mono px-1 rounded"
                style={{
                  background: "color-mix(in oklch, var(--exec-color) 12%, transparent)",
                  color: "var(--exec-color)",
                  border: "1px solid color-mix(in oklch, var(--exec-color) 32%, transparent)",
                }}
              >
                {label}
              </span>
            )}

            {editando && (
              <div
                className="absolute left-1/2 top-full mt-1 -translate-x-1/2 z-[30] min-w-36
                           rounded-md border border-border bg-popover shadow-md overflow-hidden"
                onMouseLeave={() => setEditing(false)}
              >
                {candidatos.map(porta => (
                  <button
                    key={porta.name}
                    type="button"
                    onClick={() => chooseKey(porta.name)}
                    className={cn(
                      "block w-full text-left px-2 py-1 text-[11px] font-mono transition-colors",
                      porta.name === data?.from_key
                        ? "bg-accent text-accent-foreground"
                        : "hover:bg-accent/50",
                    )}
                  >
                    {porta.name}
                    {porta.description && (
                      <span className="block text-[9px] text-muted-foreground font-sans truncate">
                        {porta.description}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Delete button — visible on hover/active tool */}
        <div
          data-edge-id={id}
          data-role="edge-delete"
          onMouseEnter={() => { setHovered(true); handleToolState("onFocus") }}
          onMouseLeave={() => { setHovered(false); handleToolState("leave") }}
          className={cn(
            "absolute transition-opacity duration-200",
            isToolOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
          )}
          style={{
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            pointerEvents: "all",
          }}
        >
          <button
            // Same reason as the key change: a direct `setEdges` doesn't generate an
            // EdgeChange, so deleting an edge via the button never entered the
            // history and Ctrl+Z didn't bring it back.
            onClick={() => store.getState().triggerEdgeChanges([{ id, type: "remove" }])}
            className="group !pointer-events-auto bg-background/80 border border-border rounded-full p-0.5 shadow-sm hover:border-destructive transition-colors cursor-pointer"
          >
            <MdDelete size={13} className="group-hover:text-destructive text-muted-foreground transition-colors" />
          </button>
        </div>
      </EdgeLabelRenderer>
    </>
  )
}

export default CustomEdge
