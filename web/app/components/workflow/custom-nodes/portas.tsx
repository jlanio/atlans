import { INodePortAPI } from "@/service/types"
import AddConnectionHandle from "./add-connection-handle"
import AddInputHandle from "./add-input-handle"
import { HandleSource, HandleTarget } from "./handle"
import { portTopStyle } from "../utils/node-metrics"

/**
 * A card's connection points, drawn from `data.outputs` / `data.inputs`.
 *
 * One rule for every card, and it is the same rule the editor uses to anchor
 * the edges (`resolveSourceHandle`, `sourceHandleDaChave`, `inputHandle`,
 * `reancorarArestasDoNo`): one NAMED handle per port when the node has 2+ ports,
 * a single ANONYMOUS handle otherwise. A card that draws anything else leaves
 * edges pointing at handles that do not exist, and React Flow stops drawing them
 * ("Couldn't create edge for source handle id", error 008) while they stay in
 * the workflow and keep running. That is what the HTTP Request did: its card
 * drew one anonymous output for its three ports (status_code, headers, body),
 * so switching an edge's output on the badge made the edge vanish — and so did
 * every reload, because the anchoring restored the port name.
 *
 * Each card used to repeat this rendering on its own; the copies diverged.
 */

/** Output handles in use, `"__default__"` standing for the anonymous one. */
export type PortasEmUso = ReadonlySet<string>

export function PortasDeSaida({ nodeId, outputs, nodeHeight, emUso }: {
  nodeId: string
  outputs: INodePortAPI[]
  nodeHeight: number
  emUso: PortasEmUso
}) {
  if (outputs.length <= 1) {
    return (
      <AddConnectionHandle nodeId={nodeId} connectionVisible={!emUso.has("__default__")}>
        <HandleSource livre={!emUso.has("__default__")} />
      </AddConnectionHandle>
    )
  }
  return (
    <>
      {outputs.map((port, i) => {
        const ts = portTopStyle(i, outputs.length, nodeHeight)
        return (
          <AddConnectionHandle
            key={port.name}
            nodeId={nodeId}
            label={port.name}
            handleId={port.name}
            connectionVisible={!emUso.has(port.name)}
            style={ts}
          >
            <HandleSource
              id={port.name}
              className="port-top"
              livre={!emUso.has(port.name)}
              style={ts}
            />
          </AddConnectionHandle>
        )
      })}
    </>
  )
}

/** Inputs (left) — a dashed line distinguishes them from outputs. */
export function PortasDeEntrada({ inputs, nodeHeight, emUso }: {
  inputs: INodePortAPI[]
  nodeHeight: number
  emUso: PortasEmUso
}) {
  if (inputs.length <= 1) {
    return <HandleTarget livre={!emUso.has("__default__")} />
  }
  return (
    <>
      {inputs.map((port, i) => {
        const ts = portTopStyle(i, inputs.length, nodeHeight)
        return (
          <AddInputHandle
            key={port.name}
            label={port.name}
            connectionVisible={!emUso.has(port.name)}
            style={ts}
          >
            <HandleTarget
              id={port.name}
              className="port-top"
              livre={!emUso.has(port.name)}
              style={ts}
              title={port.name}
            />
          </AddInputHandle>
        )
      })}
    </>
  )
}
