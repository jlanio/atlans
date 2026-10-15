/**
 * Backspace inside a dialog over the canvas must not delete nodes.
 *
 * React Flow listens for its delete key on the DOCUMENT, and it only ignores
 * the press when it comes from a text input/select/textarea or from inside an
 * element marked `.nokey` (`isInputDOMNode` in @xyflow/system). The node
 * configuration modal is a portal full of buttons, Radix selects and switches,
 * and the double-click that opens it leaves the node selected: Backspace on any
 * of them deleted the node being configured, with all its edges. The same goes
 * for every dialog opened over the canvas — the pin dialog, the run parameters,
 * the sub-workflow viewer — and for what Radix renders in its own portal at the
 * end of the body (a select's options, a dialog or sheet opened from the
 * modal), which no marked root contains.
 *
 * A real `<ReactFlow>`, with its real key listener; only the URL (Next's
 * router) and the server are in memory.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { useEffect, type ReactNode } from "react"
import { Node, ReactFlow, ReactFlowProvider, useStoreApi } from "@xyflow/react"

const url = vi.hoisted(() => ({ sp: new URLSearchParams(""), pathname: "/workflow/abc" }))
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: (destino: string) => { url.sp = new URLSearchParams(destino.split("?")[1] ?? "") },
    push: () => {},
  }),
  usePathname: () => url.pathname,
  useSearchParams: () => url.sp,
  useParams: () => ({}),
}))
vi.mock("@monaco-editor/react", () => ({
  default: () => <div data-testid="monaco" />,
  Editor: () => <div data-testid="monaco" />,
  useMonaco: () => null,
  loader: { config: () => {} },
}))
// The sub-workflow viewer fetches the child's definition; still loading is
// enough — its bar, with the buttons, is already on screen.
vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: { getWorkflowById: () => new Promise(() => {}) },
}))

import NodeConfigModal from "@/app/components/workflow/node-config-modal"
import PinDialog from "@/app/components/workflow/custom-nodes/tools/pin-dialog"
import ExecuteParamsDialog from "@/app/components/workflow/execute-params-dialog"
import SubflowViewer from "@/app/components/workflow/subflow-viewer"
import { useSubflowDrilldownStore } from "@/app/stores/subflowDrilldownStore"

/** Selected, as the double-click that opens the modal leaves it. */
const NO: Node = {
  id: "n1",
  position: { x: 0, y: 0 },
  selected: true,
  data: {
    name: "Buffer",
    alias: "Buffer",
    description: "",
    type: "spatial",
    properties: { distance: "10", modo: "a" },
    fields: [
      { name: "distance", label: "Distância", type: "number", default: 10 },
      {
        name: "modo", label: "Modo", type: "select", default: "a",
        options: [{ value: "a", label: "Alfa" }, { value: "b", label: "Beta" }],
      },
    ],
    inputs: [],
    outputs: [],
  },
}

/** The React Flow store, to tell whether the node is still there. */
const loja = {} as { api: ReturnType<typeof useStoreApi> }
function Sonda() {
  const api = useStoreApi()
  useEffect(() => { loja.api = api }, [api])
  return null
}

function montar(extra?: ReactNode) {
  return render(
    <ReactFlowProvider>
      <div style={{ width: 800, height: 600 }}>
        <ReactFlow defaultNodes={[NO]} defaultEdges={[]} />
      </div>
      <Sonda />
      <NodeConfigModal />
      {extra}
    </ReactFlowProvider>,
  )
}

const noExiste = () => loja.api.getState().nodes.some(n => n.id === "n1")

/**
 * Press AND release, like a keyboard does. React Flow remembers the keys held
 * down and only matches when the held set is exactly its key: a press without
 * its release would leave the key in that set and silently disarm the next
 * Backspace — the test would pass for the wrong reason.
 */
function tecla(alvo: Element, key: string) {
  fireEvent.keyDown(alvo, { key, code: key })
  fireEvent.keyUp(alvo, { key, code: key })
}
const backspace = (alvo: Element) => tecla(alvo, "Backspace")

/** Focus moves Radix state (the highlighted option), so it goes through `act`. */
const focar = (alvo: Element) => act(() => (alvo as HTMLElement).focus())

/** `deleteElements` is asynchronous: give it the chance to run before saying it did not. */
const assentar = () => act(() => new Promise(resolve => setTimeout(resolve, 0)))

async function abrirModal() {
  url.sp = new URLSearchParams("cn=n1")
  montar()
  return screen.findByRole("button", { name: "Aplicar" })
}

beforeEach(() => {
  url.sp = new URLSearchParams("")
  // Radix Select asks for these on open; jsdom does not implement them.
  window.HTMLElement.prototype.hasPointerCapture = vi.fn()
  window.HTMLElement.prototype.releasePointerCapture = vi.fn()
})
afterEach(() => {
  cleanup()
  useSubflowDrilldownStore.getState().close()
})

describe("Backspace com o foco no canvas — continua apagando", () => {
  it("o nó selecionado é apagado, como sempre", async () => {
    montar()
    const no = await waitFor(() => {
      const el = document.querySelector('.react-flow__node[data-id="n1"]')
      expect(el).not.toBeNull()
      return el!
    })

    focar(no)
    backspace(no)

    await waitFor(() => expect(noExiste()).toBe(false))
  })
})

describe("Backspace dentro do modal de configuração — não apaga o nó", () => {
  it("num botão do rodapé", async () => {
    const aplicar = await abrirModal()
    const cancelar = screen.getByRole("button", { name: "Cancelar" })

    for (const botao of [cancelar, aplicar]) {
      focar(botao)
      backspace(botao)
    }
    await assentar()

    expect(noExiste()).toBe(true)
  })

  it("numa opção aberta de um select (o Radix a desenha fora do modal)", async () => {
    await abrirModal()
    tecla(screen.getByRole("combobox"), "Enter")
    const opcao = await screen.findByRole("option", { name: "Beta" })

    focar(opcao)
    backspace(opcao)
    await assentar()

    expect(noExiste()).toBe(true)
  })

  it("no diálogo de descartar alterações, aberto por cima do modal", async () => {
    await abrirModal()
    fireEvent.change(screen.getByDisplayValue("10"), { target: { value: "25" } })
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }))
    const continuar = await screen.findByRole("button", { name: "Continuar editando" })

    focar(continuar)
    backspace(continuar)
    await assentar()

    expect(noExiste()).toBe(true)
  })

  it("no guia de expressões, aberto pelo cabeçalho do modal", async () => {
    await abrirModal()
    fireEvent.click(screen.getByTitle("Guia de expressoes Jinja"))
    const fechar = await screen.findByRole("button", { name: "Fechar" })

    focar(fechar)
    backspace(fechar)
    await assentar()

    expect(noExiste()).toBe(true)
  })
})

describe("Backspace nos outros diálogos abertos por cima do canvas — não apaga o nó", () => {
  it("no diálogo de fixar o output (pin)", async () => {
    montar(<PinDialog nodeId="n1" workflowId="wf" onClose={() => {}} />)
    const umaHora = await screen.findByRole("button", { name: "1 hora" })

    focar(umaHora)
    backspace(umaHora)
    await assentar()

    expect(noExiste()).toBe(true)
  })

  it("no diálogo de parâmetros da execução", async () => {
    montar(
      <ExecuteParamsDialog
        open
        paramsSchema={{ reprocessar: { type: "boolean" } }}
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    )
    const chave = await screen.findByRole("switch")

    focar(chave)
    backspace(chave)
    await assentar()

    expect(noExiste()).toBe(true)
  })

  it("no visualizador de sub-fluxo — Backspace como 'voltar' não apaga o nó de onde se desceu", async () => {
    // Opened from the SubWorkflow's toolbar, a click that selects the node in
    // the editor. The viewer's own canvas does not delete (`deleteKeyCode` null),
    // but the editor's listener is on the same document.
    useSubflowDrilldownStore.getState().open([{ canvasNodeId: "n1", workflowHash: "filho", label: "Filho" }])
    montar(<SubflowViewer rootLabel="Pai" />)
    const fechar = await screen.findByTitle("Fechar (Esc)")

    focar(fechar)
    backspace(fechar)
    await assentar()

    expect(noExiste()).toBe(true)
  })
})
