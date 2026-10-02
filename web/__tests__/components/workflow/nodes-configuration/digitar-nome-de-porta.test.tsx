/**
 * Digitar o nome de uma porta nos nós de entrada/saída de sub-fluxo.
 *
 * O `HELPER_MAP` do formulário era construído DENTRO do componente, e os dois
 * editores de porta eram funções inline — um tipo de elemento novo a cada
 * render. O React não reconcilia isso: desmonta e remonta a subárvore inteira.
 * O campo de texto era recriado do zero a cada tecla e perdia o foco, então só
 * dava para escrever uma letra por vez, clicando de volta no campo entre elas.
 *
 * Os outros helpers do mapa são referências importadas, estáveis — por isso o
 * defeito aparecia só nestes dois.
 *
 * O teste olha a IDENTIDADE do nó no DOM, que é a causa direta: sobrevivendo ao
 * re-render, ele mantém o foco e a tecla seguinte chega nele. Comparar só o
 * valor não bastaria — com o remount o valor até aparece, o que não aparece é o
 * cursor.
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
  // O editor aponta o loader para `/monaco/vs` no escopo do módulo.
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

/** Reproduz o ciclo real do modal: cada tecla grava e re-renderiza o formulário. */
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

    // Mesmo nó do DOM = o React reconciliou em vez de remontar.
    expect(screen.getByDisplayValue("g")).toBe(campo)
    expect(campo).toHaveFocus()
  })

  it("o espaço digitado permanece e é explicado, em vez de sumir", () => {
    // O campo aplicava `trim` a cada tecla: a barra de espaço parecia não
    // funcionar, sem nada dizendo por quê. Guardar o que foi digitado é o que
    // permite a validação explicar — e sugerir o underscore.
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
