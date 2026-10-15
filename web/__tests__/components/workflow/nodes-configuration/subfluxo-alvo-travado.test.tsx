/**
 * The SubWorkflow's target workflow, while edges are connected to it.
 *
 * The node's handles come from the TARGET's contract: one input per port of
 * its SubWorkflowInput, one output per port of its SubWorkflowOutput. Switching
 * the target swaps those handles, and an edge anchored on a port the new target
 * does not have stops being drawn — it stays in the workflow, keeps running and
 * cannot be deleted, the same failure the port editors lock against. The target
 * selector had no lock at all.
 *
 * Choosing the FIRST target stays free: without a target applied the node has
 * no ports, so every edge sits on its anonymous handle and nothing can be left
 * pointing at a port that disappears. That is the common path — the "+" next
 * to a port creates the SubWorkflow already linked, and only then is it configured.
 */
import { describe, it, expect, afterEach, vi } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"
import { Edge, ReactFlowProvider } from "@xyflow/react"

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "pai" }),
}))
vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: {
    getWorkflows: () => Promise.resolve({
      data: [{ id_hash: "filho", name: "Filho" }, { id_hash: "outro", name: "Outro" }],
    }),
    getWorkflowContract: () => Promise.resolve({
      data: {
        inputs: [], outputs: [{ name: "r1" }, { name: "r2" }],
        has_input_node: true, has_output_node: true, is_active: true,
      },
    }),
  },
}))
vi.mock("@monaco-editor/react", () => ({
  default: () => <div data-testid="monaco" />,
  Editor: () => <div data-testid="monaco" />,
  useMonaco: () => null,
  loader: { config: () => {} },
}))

import SubWorkflowHelper from "@/app/components/workflow/nodes-configuration/sub-workflow-helper"
import NodeConfigForm from "@/app/components/workflow/node-config-modal/node-config-form"
import { INodeContext } from "@/context/useFlowContext"

afterEach(cleanup)

/** The SubWorkflow as the canvas holds it — `workflowHash` is the APPLIED target. */
function subfluxo(alvoAplicado: string): INodeContext {
  return {
    id: "sub",
    position: { x: 0, y: 0 },
    data: {
      name: "SubWorkflow",
      alias: "Sub-Workflow",
      description: "",
      type: "control",
      properties: { workflowHash: alvoAplicado, inputsMapping: "{}", timeoutSeconds: "300" },
      fields: [{ name: "workflowHash", label: "Sub-workflow", type: "string", default: "" }],
      inputs: [],
      outputs: alvoAplicado ? [{ name: "r1" }, { name: "r2" }] : [],
    },
  } as unknown as INodeContext
}

function montar(alvoAplicado: string, { entrada = 0, saida = 0 }: { entrada?: number; saida?: number }) {
  return render(
    <ReactFlowProvider initialNodes={[subfluxo(alvoAplicado)]}>
      <SubWorkflowHelper
        values={{ workflowHash: alvoAplicado || "filho" }}
        setNodeField={() => {}}
        hasUnsaved={false}
        nodeId="sub"
        conexoesDeEntrada={entrada}
        conexoesDeSaida={saida}
      />
    </ReactFlowProvider>,
  )
}

const seletorDoAlvo = () => screen.getByRole("combobox")
// The contract preview is the last thing to render; waiting for it keeps the
// effects of the mount inside the test.
const contratoCarregado = () => screen.findByText(/Outputs \(2\)/)

describe("SubWorkflowHelper — o workflow alvo trava com arestas ligadas", () => {
  it("com um alvo aplicado e uma aresta chegando, o alvo não troca", async () => {
    montar("filho", { entrada: 1 })
    await contratoCarregado()

    expect(seletorDoAlvo()).toBeDisabled()
    expect(screen.getByText(/Há 1 conexão neste nó/)).toBeInTheDocument()
    expect(screen.getByText(/Desconecte antes de trocar o workflow alvo/)).toBeInTheDocument()
  })

  it("as arestas que saem das portas do contrato também travam", async () => {
    montar("filho", { saida: 2 })
    await contratoCarregado()

    expect(seletorDoAlvo()).toBeDisabled()
    expect(screen.getByText(/Há 2 conexões neste nó/)).toBeInTheDocument()
  })

  it("sem aresta ligada, o alvo troca livre", async () => {
    montar("filho", {})
    await contratoCarregado()

    expect(seletorDoAlvo()).not.toBeDisabled()
    expect(screen.queryByText(/Desconecte antes/)).not.toBeInTheDocument()
  })

  it("sem alvo aplicado ainda, escolher o primeiro não trava, mesmo já ligado pelo '+'", async () => {
    // The form already holds the choice ("filho"), but it was not applied: the
    // node on the canvas has no ports yet, and every edge is anonymous.
    montar("", { entrada: 1 })
    await contratoCarregado()

    expect(seletorDoAlvo()).not.toBeDisabled()
    expect(screen.queryByText(/Desconecte antes/)).not.toBeInTheDocument()
  })
})

describe("NodeConfigForm — leva ao SubWorkflow as arestas dos dois lados", () => {
  it("uma aresta saindo da porta r2 trava a troca do alvo", async () => {
    const no = subfluxo("filho")
    const arestas: Edge[] = [
      { id: "e1", source: "sub", target: "buffer", sourceHandle: "r2", data: { from_key: "r2" } },
    ]
    render(
      <ReactFlowProvider initialNodes={[no]} initialEdges={arestas}>
        <NodeConfigForm
          nodeFound={no}
          values={no.data.properties}
          setNodeField={() => {}}
          saveNodeConfig={() => {}}
          nodeName="SubWorkflow"
          requiresCredential={false}
        />
      </ReactFlowProvider>,
    )
    await contratoCarregado()

    expect(seletorDoAlvo()).toBeDisabled()
    expect(screen.getByText(/Há 1 conexão neste nó/)).toBeInTheDocument()
  })
})
