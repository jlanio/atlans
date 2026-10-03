"use client"

import { Handle, HandleProps, Position } from "@xyflow/react"
import { HTMLAttributes } from "react"
import { cn } from "@/lib/utils"
import { corDoTom, tomDoHandle } from "../../utils/exec-colors"

/**
 * A canvas node's port — the point where the edge leaves and where it arrives.
 *
 * It was born from two twin 17-line files (`source.tsx` and `target.tsx`) that
 * diverged exactly where they shouldn't: the output was a 6px circle and the
 * input an 8×12 rectangle, with no intent declared anywhere, and both hard-coded
 * `!bg-white` — in the dark theme the port became the highest-contrast element on
 * the canvas, stronger than the node title.
 *
 * Here the shape says the DIRECTION (output is a solid pin, input is a hollow
 * socket), the stroke says the STATE (free is dashed) and the color comes from the
 * same execution vocabulary as the edge. The visual rules live in `globals.css`,
 * under `.react-flow__handle.rf-handle`: it needs higher specificity than React
 * Flow's own, and solving that with `!important` on a utility class was what
 * kept the caller from overriding anything.
 */

export type DirecaoDaPorta = "saida" | "entrada"

interface PortaProps
  extends Omit<HandleProps, "type" | "position">,
    Omit<HTMLAttributes<HTMLDivElement>, "id"> {
  direcao: DirecaoDaPorta
  /** Port with no edge attached.
   *
   *  The only thing that carried this information was the "+" stub beside it,
   *  which LOD hides when zoomed out — the information went away with it. */
  livre?: boolean
}

const Porta = ({ direcao, livre, className, style, ...props }: PortaProps) => {
  const saida = direcao === "saida"
  // The Conditional's `true`/`false` are born green/red and STAY THAT WAY: the port
  // says which branch it is, and the edge says what happened to it. See the
  // comment on `--rf-handle-tom` in globals.css for why the port doesn't
  // follow the node status.
  //
  // Only on the OUTPUT: the map describes routing branches, which are the
  // Conditional's outputs. Applied to the input, a dynamic-port node with an input
  // named `true` would get a green socket announcing a branch that doesn't exist.
  const ramo = saida ? tomDoHandle(props.id) : undefined

  return (
    <Handle
      {...props}
      type={saida ? "source" : "target"}
      position={saida ? Position.Right : Position.Left}
      data-livre={livre ? "true" : "false"}
      style={{
        ...(ramo ? ({ "--rf-handle-ramo": corDoTom(ramo) } as React.CSSProperties) : null),
        ...style,
      }}
      className={cn(
        // `z-10` comes from the two files this one replaced, and isn't decorative:
        // `.exec-card` is `isolate`, and the `::after` that draws the execution ring
        // is generated last — at `z-index: auto` it paints ON TOP of the
        // ports, cutting each one in half during a run.
        "rf-handle z-10",
        saida ? "rf-handle-saida" : "rf-handle-entrada",
        className,
      )}
    />
  )
}

/** Node output — solid pin, on the right. */
export const HandleSource = (props: Omit<PortaProps, "direcao">) => (
  <Porta {...props} direcao="saida" />
)

/** Node input — hollow socket, on the left. */
export const HandleTarget = (props: Omit<PortaProps, "direcao">) => (
  <Porta {...props} direcao="entrada" />
)
