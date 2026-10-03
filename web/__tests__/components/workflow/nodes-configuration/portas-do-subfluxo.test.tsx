/**
 * Sub-workflow port editor, after ports became connection points.
 *
 * While `ports` was just an allowlist, touching it was harmless. Now each port
 * is a handle on the canvas: renaming or removing one with an edge attached
 * leaves the edge pointing to a point that no longer exists — it disappears
 * from the canvas, keeps executing, and with no line drawn you can't even
 * delete it. It's the same reason the Python Script port editor locks.
 *
 * The lock applies only on the output side: `SubWorkflowInput` is a trigger, it
 * receives no edges, and there the ports aren't handles.
 */
import { describe, it, expect, afterEach } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"

import SubWorkflowPortsHelper from "@/app/components/workflow/nodes-configuration/sub-workflow-ports-helper"

afterEach(cleanup)

function montar(variant: "input" | "output", conexoes: number) {
  return render(
    <SubWorkflowPortsHelper
      values={{ ports: JSON.stringify(["focos", "mapa"]) }}
      setNodeField={() => {}}
      hasUnsaved={false}
      variant={variant}
      conexoesDeEntrada={conexoes}
    />,
  )
}

const botaoAdicionar = () => screen.getByRole("button", { name: /adicionar porta/i })

describe("SubWorkflowPortsHelper — trava com arestas ligadas", () => {
  it("saída com aresta ligada bloqueia a edição", () => {
    montar("output", 2)

    expect(botaoAdicionar()).toBeDisabled()
    for (const campo of screen.getAllByRole("textbox")) {
      expect(campo).toBeDisabled()
    }
    for (const remover of screen.getAllByTitle("Remover porta")) {
      expect(remover).toBeDisabled()
    }
  })

  it("o aviso diz quantas conexões impedem a edição", () => {
    montar("output", 2)
    expect(screen.getByText(/Há 2 conexões/)).toBeInTheDocument()
  })

  it("uma conexão só é dita no singular", () => {
    montar("output", 1)
    expect(screen.getByText(/Há 1 conexão/)).toBeInTheDocument()
  })

  it("saída sem aresta continua editável", () => {
    montar("output", 0)

    expect(botaoAdicionar()).not.toBeDisabled()
    expect(screen.queryByText(/Desconecte antes/)).not.toBeInTheDocument()
  })

  it("entrada nunca trava", () => {
    // SubWorkflowInput is a trigger: nothing arrives at it, and the edge count
    // the form passes is the node's — locking there would be a block with no cause.
    montar("input", 3)

    expect(botaoAdicionar()).not.toBeDisabled()
    expect(screen.queryByText(/Desconecte antes/)).not.toBeInTheDocument()
  })
})
