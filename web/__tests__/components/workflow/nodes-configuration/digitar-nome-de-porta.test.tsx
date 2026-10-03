/**
 * Typing a port name in the sub-workflow input/output nodes.
 *
 * The form's `HELPER_MAP` was built INSIDE the component, and the two port
 * editors were inline functions — a new element type on every render. React
 * doesn't reconcile that: it unmounts and remounts the whole subtree. The text
 * field was recreated from scratch on every keystroke and lost focus, so you
 * could only type one letter at a time, clicking back into the field in between.
 *
 * The map's other helpers are imported, stable references — that's why the
 * defect only showed up in these two.
 *
 * The test looks at the IDENTITY of the DOM node, which is the direct cause:
 * surviving the re-render, it keeps focus and the next keystroke reaches it.
 * Comparing only the value wouldn't be enough — with the remount the value even
 * shows up; what doesn't show up is the cursor.
 */
import { describe, it, expect, vi } from "vitest"
import { useState } from "react"
import { render, screen, fireEvent } from "@testing-library/react"
import { ReactFlowProvider } from "@xyflow/react"

import NodeConfigForm from "@/app/components/workflow/node-config-modal/node-config-form"
import { INodeContext } from "@/context/useFlowContext"

vi.mock("@monaco-editor/react", () => ({
  default: () => <div data-testid="monaco" />,
  Editor: () => <div data-testid="monaco" />,
  useMonaco: () => null,
  // The editor points the loader at `/monaco/vs` at module scope.
  loader: { config: () => {} },
}))

function noDe(name: string): INodeContext {
  return {
    id: "no-1",
    position: { x: 0, y: 0 },
    data: {
      name,
      alias: name,
      description: "",
      type: name === "SubWorkflowInput" ? "trigger" : "output",
      properties: { ports: JSON.stringify(["porta"]) },
      fields: [{ name: "ports", label: "Portas", type: "object", default: [] }],
      inputs: [],
      outputs: [],
    },
  } as unknown as INodeContext
}

/** Reproduces the modal's real cycle: each keystroke writes and re-renders the form. */
function Harness({ nodeName }: { nodeName: string }) {
  const [values, setValues] = useState<Record<string, string | number | boolean>>({
    ports: JSON.stringify(["porta"]),
  })
  return (
    <ReactFlowProvider>
      <NodeConfigForm
        nodeFound={noDe(nodeName)}
        values={values}
        setNodeField={(campo, valor) => setValues(v => ({ ...v, [campo]: valor }))}
        saveNodeConfig={() => {}}
        nodeName={nodeName}
        requiresCredential={false}
      />
    </ReactFlowProvider>
  )
}

describe.each(["SubWorkflowInput", "SubWorkflowOutput"])("%s", (nodeName) => {
  it("o campo sobrevive ao re-render, então o foco não se perde entre teclas", () => {
    render(<Harness nodeName={nodeName} />)

    const campo = screen.getByDisplayValue("porta") as HTMLInputElement
    campo.focus()
    expect(campo).toHaveFocus()

    fireEvent.change(campo, { target: { value: "g" } })

    // Same DOM node = React reconciled instead of remounting.
    expect(screen.getByDisplayValue("g")).toBe(campo)
    expect(campo).toHaveFocus()
  })

  it("o espaço digitado permanece e é explicado, em vez de sumir", () => {
    // The field applied `trim` on every keystroke: the space bar seemed not to
    // work, with nothing saying why. Keeping what was typed is what lets the
    // validation explain — and suggest the underscore.
    render(<Harness nodeName={nodeName} />)

    const campo = screen.getByDisplayValue("porta") as HTMLInputElement
    fireEvent.change(campo, { target: { value: "minha porta" } })

    expect(campo.value).toBe("minha porta")
    expect(screen.getByText(/Espaços não são aceitos/)).toBeInTheDocument()
  })

  it("acumula o nome inteiro, tecla a tecla", () => {
    render(<Harness nodeName={nodeName} />)

    const campo = screen.getByDisplayValue("porta") as HTMLInputElement
    campo.focus()

    for (const parcial of ["g", "ge", "geo", "geom", "geome", "geomet", "geometr", "geometry"]) {
      fireEvent.change(campo, { target: { value: parcial } })
    }

    expect(campo.value).toBe("geometry")
    expect(campo).toHaveFocus()
  })
})
