/**
 * The assistant drawer, end to end: message → stream → card → Apply.
 *
 * The test that justifies this file is the **Apply doesn't save** one. The
 * assistant doesn't save, by a hard gate on the server, and the button is the
 * only bridge between the conversation and the canvas. If one day it starts
 * calling the write route "for convenience", the whole gate becomes decoration —
 * and the owner's decision was precisely that saving belongs to the person,
 * through the Save button.
 *
 * The `fetch` is fake, but the stream is real: a `ReadableStream` that
 * delivers the frames the way the network does, in chunks that don't respect
 * frame boundaries.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, cleanup, fireEvent, waitFor } from "@testing-library/react"

// `vi.mock` is hoisted to the top of the file, so the factory can't close
// over a module variable — hence `vi.hoisted`.
const servico = vi.hoisted(() => ({
  estadoDoAssistente: vi.fn(async () => ({ data: { ativo: true, motivo: null as string | null, cota: null }, error: null })),
  esquecerConversaDoAssistente: vi.fn(async () => ({ data: undefined, error: null })),
}))
vi.mock("@/service/GisFlowService", () => ({ GisFlowService: servico }))

// A fake extension with an offer at full quota: the drawer is one of the three
// surfaces of the notice, and the offer has to reach here too.
vi.mock("@/extensoes", async (original) => ({
  ...(await original<typeof import("@/extensoes")>()),
  EXTENSOES: [{
    nome: "teste",
    ofertaDaCota: ({ plano, assinaturasAtivas }: { plano?: string | null; assinaturasAtivas?: boolean }) => (
      <button type="button">oferta {plano} {String(assinaturasAtivas)}</button>
    ),
  }],
}))

// The card subscribes to the canvas via `useNodes`. Here the canvas is empty —
// it's the create screen, which is where the drawer starts out open.
vi.mock("@xyflow/react", async (original) => ({
  ...(await original<Record<string, unknown>>()),
  useNodes: vi.fn(() => []),
}))

import AssistantPanel from "@/app/components/workflow/assistente"
import { useAssistantEditorStore } from "@/app/stores/assistenteEditorStore"
import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore"
import type { INodesAPI } from "@/service/types"

const catalogo = [
  {
    name: "DriveFile", alias: "Arquivo do Drive", description: "Lê", type: "trigger",
    properties: [{ name: "file_id", label: "Arquivo", type: "string", default: "" }],
    outputs: [{ name: "output" }],
  },
  {
    name: "Buffer", alias: "Buffer", description: "Buffer", type: "action",
    properties: [{ name: "distance", label: "Distância", type: "string", default: "" }],
    outputs: [{ name: "output" }],
  },
] as unknown as INodesAPI[]

const DEFINICAO = {
  nodes: [
    { id: "a", name: "DriveFile", properties: { file_id: "mun.shp" } },
    { id: "b", name: "Buffer", properties: { distance: "500" } },
  ],
  edges: [{ source: "a", target: "b" }],
}

const quadro = (evento: string, dados: unknown) =>
  `event: ${evento}\ndata: ${JSON.stringify(dados)}\n\n`

/** The frames of a conversation that builds and validates a workflow. */
function conversationBody(): string {
  return (
    quadro("pensando", { texto: "preciso do catálogo" }) +
    quadro("texto", { texto: "Vou montar " }) +
    quadro("texto", { texto: "o fluxo." }) +
    quadro("ferramenta", { id: "t1", nome: "search_nodes", argumentos: { query: "buffer" } }) +
    quadro("ferramenta_fim", { id: "t1", nome: "search_nodes", erro: false }) +
    // Draws BEFORE validating: that's the order of the new contract, and it's
    // what makes the build incremental. Validating became a check of what's
    // already on the screen.
    quadro("ferramenta", { id: "t2", nome: "desenhar_no_canvas", argumentos: { definition: { __campos__: 2 } } }) +
    quadro("ferramenta_fim", { id: "t2", nome: "desenhar_no_canvas", erro: false }) +
    quadro("proposta", { definicao: DEFINICAO, nos: 2, arestas: 1, desenhar: true, nota: "montei o buffer" }) +
    quadro("ferramenta", { id: "t3", nome: "validate_workflow", argumentos: { definition: { __campos__: 2 } } }) +
    quadro("ferramenta_fim", { id: "t3", nome: "validate_workflow", erro: false }) +
    quadro("proposta", { definicao: DEFINICAO, nos: 2, arestas: 1, ok: true, erros: 0, avisos: 0 }) +
    quadro("fim", { transcrito: [], uso: { total: 1234 }, voltas: 2, ok: true })
  )
}

/** An SSE body delivered in chunks that CUT frames in half, as the network does.
 *
 * The `pull` is ASYNCHRONOUS on purpose: it yields the loop between one chunk and
 * the next, which is what the network (and a loaded CI runner) do. With a
 * synchronous `pull` the whole stream drained inside one `waitFor` and hid any
 * race between the test and the frames — including the one that broke CI on #137. */
function chunkedStream(corpo: string, pedacos = 7): ReadableStream<Uint8Array> {
  const bytes = new TextEncoder().encode(corpo)
  const tamanho = Math.ceil(bytes.length / pedacos)
  let i = 0
  return new ReadableStream({
    async pull(controle) {
      await new Promise((r) => setTimeout(r, 0))
      if (i >= bytes.length) {
        controle.close()
        return
      }
      controle.enqueue(bytes.slice(i, i + tamanho))
      i += tamanho
    },
  })
}

let fakeFetch: ReturnType<typeof vi.fn>

beforeEach(() => {
  cleanup()
  servico.estadoDoAssistente.mockClear()
  servico.esquecerConversaDoAssistente.mockClear()
  useAssistantEditorStore.setState({ aberto: true })
  useWorkflowCatalogStore.setState({ nodesAPI: catalogo })
  localStorage.clear()

  fakeFetch = vi.fn(async () => new Response(chunkedStream(conversationBody()), {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  }))
  vi.stubGlobal("fetch", fakeFetch)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

async function conversar() {
  render(<AssistantPanel workflowId="wf1" abrirPorPadrao onAplicar={onApplied} />)
  const campo = await screen.findByLabelText("Mensagem para o assistente")
  fireEvent.change(campo, { target: { value: "monta um buffer de 500m" } })
  fireEvent.submit(campo.closest("form")!)
  await screen.findAllByTestId("cartao-proposta")
  await waitFor(() => expect(screen.queryByLabelText("Parar")).toBeNull())
}

const onApplied = vi.fn()

describe("gaveta do assistente", () => {
  beforeEach(() => onApplied.mockClear())

  it("desenha a conversa a partir do stream, quadro a quadro", async () => {
    await conversar()

    expect(screen.getByText("monta um buffer de 500m")).toBeTruthy()
    expect(screen.getByText("Vou montar o fluxo.")).toBeTruthy()
    // A tool name never goes raw to the screen — it's the `status-rotulos.ts`
    // pattern, and "search_nodes" says nothing to someone building a workflow.
    expect(screen.getByText("Procurando nós")).toBeTruthy()
    expect(screen.queryByText(/search_nodes/)).toBeNull()
    expect(screen.getByText("Validando o fluxo")).toBeTruthy()
  })

  it("no canvas vazio o fluxo entra sozinho, sem botão", async () => {
    // The create screen: there's no work to lose, so drawing asks for nothing.
    // This is what makes the build INCREMENTAL — no button at every step, the
    // workflow grows while the model builds it.
    await conversar()

    expect(onApplied).toHaveBeenCalled()
    expect(screen.getByText("Desenhado no canvas")).toBeTruthy()
    expect(screen.getByText("montei o buffer")).toBeTruthy()
    expect(screen.queryByRole("button", { name: /Desenhar no canvas/ })).toBeNull()
  })

  it("o veredito da validação aparece separado, e não redesenha", async () => {
    // Two roles in the same frame: `desenhar_no_canvas` puts it on the screen,
    // `validate_workflow` checks. If the verdict also drew, each validation
    // would undo what the person changed between one step and the next.
    await conversar()

    expect(screen.getByText("Validação limpa")).toBeTruthy()
    expect(onApplied).toHaveBeenCalledTimes(1)
  })

  it("desenhar leva a definição ao canvas — e NÃO chama a rede", async () => {
    await conversar()

    // What the network has done so far: the state on mount and the conversation's POST.
    const fetchCallsBefore = fakeFetch.mock.calls.length
    const serviceCallsBefore =
      servico.estadoDoAssistente.mock.calls.length + servico.esquecerConversaDoAssistente.mock.calls.length

    expect(onApplied).toHaveBeenCalledTimes(1)
    const resultado = onApplied.mock.calls[0][0]
    expect(resultado.nodes.map((n: { id: string }) => n.id)).toEqual(["a", "b"])
    expect(resultado.edges).toHaveLength(1)

    // The assertion that matters: applying is local. Saving is Save's job.
    expect(fakeFetch.mock.calls.length).toBe(fetchCallsBefore)
    expect(
      servico.estadoDoAssistente.mock.calls.length + servico.esquecerConversaDoAssistente.mock.calls.length,
    ).toBe(serviceCallsBefore)
  })

  it("manda só a mensagem nova — o transcrito é do servidor", async () => {
    // A client that kept the transcript could rewrite a `tool_result`, and a
    // `tool_result` is the SERVER's word on what happened. The route rejects
    // an extra field with 422; the panel must not try to send it.
    await conversar()
    const [, init] = fakeFetch.mock.calls[0] as [string, RequestInit]
    expect(JSON.parse(String(init.body))).toEqual({
      mensagem: "monta um buffer de 500m",
      workflow_id: "wf1",
    })
  })

  it("validação com erro é dita em voz alta, e não some", async () => {
    // The workflow with errors STAYS on the screen: that's where the person sees
    // the problem. What the card does is say that validation failed, so the
    // model fixes and redraws — this used to disable a button; now it's information.
    fakeFetch.mockImplementation(async () => new Response(
      chunkedStream(
        quadro("proposta", { definicao: DEFINICAO, nos: 2, arestas: 1, ok: false, erros: 2, avisos: 0 }) +
        quadro("fim", { transcrito: [], uso: {}, voltas: 1, ok: true }),
      ),
      { status: 200 },
    ))

    await conversar()
    expect(screen.getByText("Validação com pendências")).toBeTruthy()
    expect(screen.getByText(/A validação apontou 2 erros/)).toBeTruthy()
    // A verdict doesn't draw: nothing was applied to the canvas because of it.
    expect(onApplied).not.toHaveBeenCalled()
  })

  it("num canvas com trabalho, o primeiro desenho espera o clique", async () => {
    // The owner's decision: warn ONCE per conversation. Redrawing without warning
    // what someone built by hand is too destructive to happen silently; asking
    // at every node would be the opposite of following the workflow grow.
    const { useNodes } = await import("@xyflow/react")
    vi.mocked(useNodes).mockReturnValue([
      { id: "ja-existia", position: { x: 0, y: 0 }, data: {} },
    ] as never)

    try {
      await conversar()

      const botao = screen.getByRole("button", { name: /Desenhar no canvas/ })
      expect(onApplied).not.toHaveBeenCalled()

      fireEvent.click(botao)
      expect(onApplied).toHaveBeenCalledTimes(1)
    } finally {
      vi.mocked(useNodes).mockReturnValue([] as never)
    }
  })

  it("um turno não recebe os quadros do outro", async () => {
    // The conversation has several turns, and each frame belongs to ONE of them.
    // Without addressing by id, the new answer would also be written into the
    // old one — and the panel would show twice what the model said once.
    await conversar()

    fakeFetch.mockImplementation(async () => new Response(
      chunkedStream(
        quadro("texto", { texto: "Agora o segundo." }) +
        quadro("fim", { transcrito: [], uso: {}, voltas: 1, ok: true }),
      ),
      { status: 200 },
    ))
    const campo = screen.getByLabelText("Mensagem para o assistente")
    fireEvent.change(campo, { target: { value: "e agora?" } })
    fireEvent.submit(campo.closest("form")!)

    await screen.findByText("Agora o segundo.")
    expect(screen.getAllByText("Agora o segundo.")).toHaveLength(1)
    expect(screen.getAllByText("Vou montar o fluxo.")).toHaveLength(1)
  })

  it("instalação sem chave: o assistente não aparece em lugar nenhum", async () => {
    servico.estadoDoAssistente.mockResolvedValueOnce({
      data: { ativo: false, motivo: "não configurado", cota: null },
      error: null,
    })
    // Open in the store on purpose: even so the drawer can't exist — nor can
    // the button that opens it, which is what remains when it's closed.
    useAssistantEditorStore.setState({ aberto: true })

    const { container } = render(<AssistantPanel onAplicar={onApplied} />)
    await waitFor(() => expect(servico.estadoDoAssistente).toHaveBeenCalled())

    expect(container.querySelector("aside")).toBeNull()
    expect(screen.queryByLabelText("Abrir o assistente")).toBeNull()
    expect(container.firstChild).toBeNull()
  })

  it("falha na rota vira um erro na conversa, e não uma tela quebrada", async () => {
    fakeFetch.mockImplementation(async () => new Response(
      JSON.stringify({ error: "recusado", message: "Já há uma conversa em andamento neste fluxo." }),
      { status: 409 },
    ))

    render(<AssistantPanel workflowId="wf1" abrirPorPadrao onAplicar={onApplied} />)
    const campo = await screen.findByLabelText("Mensagem para o assistente")
    fireEvent.change(campo, { target: { value: "oi" } })
    fireEvent.submit(campo.closest("form")!)

    expect(await screen.findByText(/Já há uma conversa em andamento/)).toBeTruthy()
  })
  it("o raciocínio nasce recolhido — e o texto continua no DOM", async () => {
    // The thinking summary arrives in ENGLISH and there's no way to ask for
    // another language: it's generated by a separate step that doesn't read the
    // system prompt. Collapsing is the answer; deleting wouldn't be, because
    // whoever wants to audit what the model thought has to be able to get there.
    await conversar()

    const bloco = document.querySelector("details")!
    expect(bloco.open).toBe(false)
    // jsdom hides nothing, so the honest assertion is about VISIBILITY and
    // not about presence — and presence is exactly the contract we want:
    // Ctrl+F and screen readers still reach the text.
    expect(screen.getByText("preciso do catálogo")).not.toBeVisible()
    expect(screen.getByText("Raciocínio")).toBeVisible()
  })

  it("clicar abre o raciocínio, e ele continua aberto no turno seguinte", async () => {
    // The second half is the regression test for `Grupo`'s `key={i}`: the turns
    // are rebuilt immutably on every delta, and if a group's index shifted,
    // the open block would change owners mid-read.
    await conversar()

    fireEvent.click(document.querySelector("summary")!)
    expect(screen.getByText("preciso do catálogo")).toBeVisible()

    fakeFetch.mockImplementation(async () => new Response(
      chunkedStream(
        quadro("texto", { texto: "Agora o segundo." }) +
        quadro("fim", { transcrito: [], uso: {}, voltas: 1, ok: true }),
      ),
      { status: 200 },
    ))
    const campo = screen.getByLabelText("Mensagem para o assistente")
    fireEvent.change(campo, { target: { value: "e agora?" } })
    fireEvent.submit(campo.closest("form")!)
    await screen.findByText("Agora o segundo.")

    expect(screen.getByText("preciso do catálogo")).toBeVisible()
  })

  it("a gaveta tem teto de altura — é o que faz a conversa rolar", async () => {
    const { container } = render(<AssistantPanel workflowId="wf1" abrirPorPadrao onAplicar={onApplied} />)
    await screen.findByLabelText("Mensagem para o assistente")

    // The PAIR, not half of it. `h-full` alone hangs from a chain whose top is
    // `min-h-svh` — a floor, not a ceiling —, so the conversation grows the page
    // and the scroll goes to the viewport instead of the list. `max-h-svh` alone
    // would collapse the day the editor container stopped stretching its
    // children. Removing either of the two breaks this test.
    const gaveta = container.querySelector("aside")!
    expect(gaveta.className).toContain("h-full")
    expect(gaveta.className).toContain("max-h-svh")
  })

  it("há UM container de rolagem, e ele existe mesmo com a conversa vazia", async () => {
    // The empty state was a sibling of the form and didn't scroll. With the
    // height ceiling that becomes a defect: on a short viewport, ~300px of
    // invitation plus header and form push the send field off the screen and
    // there's nothing to scroll — precisely on `/workflow/create`, where the
    // drawer starts out open.
    const { container } = render(<AssistantPanel abrirPorPadrao onAplicar={onApplied} />)
    await screen.findByText("Descreva o fluxo que você quer")

    const rolagem = container.querySelectorAll("aside [class*='overflow-y-auto']")
    expect(rolagem).toHaveLength(1)
    expect(rolagem[0].className).toContain("min-h-0")
    // A class contract, not proof of scrolling: jsdom does no layout, so
    // `scrollHeight` and `clientHeight` are zero here. The proof is the editor
    // opened with the long conversation.
  })

  it("mostra o donut da cota sob o campo, com o percentual e a faixa", async () => {
    servico.estadoDoAssistente.mockResolvedValueOnce({
      data: { ativo: true, motivo: null, cota: { gasto: 1_230_000, teto: 1_500_000, reabre_em_segundos: 10_800 } },
      error: null,
    } as unknown as Awaited<ReturnType<typeof servico.estadoDoAssistente>>)
    render(<AssistantPanel workflowId="wf1" abrirPorPadrao onAplicar={onApplied} />)

    const donut = await screen.findByTestId("uso-da-cota")
    expect(donut.textContent).toBe("82%")
    expect(donut.dataset.faixa).toBe("alerta")
    // The same detail as Home in the aria-label: spent, ceiling and percentage.
    expect(donut.getAttribute("aria-label")).toContain("1.230.000 de 1.500.000 tokens (82%)")
  })

  it("o aviso de cota não encolhe — é o único irmão da coluna que podia", async () => {
    servico.estadoDoAssistente.mockResolvedValueOnce({
      data: { ativo: true, motivo: null, cota: { gasto: 2_000_000, teto: 1_500_000, reabre_em: null } },
      error: null,
    } as unknown as Awaited<ReturnType<typeof servico.estadoDoAssistente>>)
    render(<AssistantPanel workflowId="wf1" abrirPorPadrao onAplicar={onApplied} />)
    // By `data-testid`, not by text: the notice became the shared component,
    // and the text lives in a `<span>` INSIDE the paragraph. Searching by text
    // would return the child, whose class isn't the one holding the layout —
    // the test would measure the wrong element and stop protecting anything.
    const aviso = await screen.findByTestId("aviso-de-cota")

    // The header and the form already have `shrink-0`, and the conversation has
    // a scaled shrink factor of ZERO (`flex-basis: 0%`). Without this, the
    // algorithm targets this paragraph when the space goes negative — and it
    // has nothing to give.
    expect(aviso.className).toContain("shrink-0")
  })
})

describe("gaveta do assistente — a cota durante o turno", () => {
  it("o donut sobe com o quadro `cota` do stream, antes de o turno acabar", async () => {
    servico.estadoDoAssistente.mockResolvedValueOnce({
      data: { ativo: true, motivo: null, cota: { gasto: 0, teto: 1_000_000, reabre_em_segundos: null } },
      error: null,
    } as unknown as Awaited<ReturnType<typeof servico.estadoDoAssistente>>)
    // A stream that sends the quota and stays open: what the screen shows came from the frame.
    const aberto = new ReadableStream<Uint8Array>({
      start(c) { c.enqueue(new TextEncoder().encode('event: cota\ndata: {"gasto":300000,"teto":1000000}\n\n')) },
    })
    fakeFetch.mockImplementationOnce(async () => new Response(aberto, {
      status: 200, headers: { "Content-Type": "text/event-stream" },
    }))
    render(<AssistantPanel workflowId="wf1" abrirPorPadrao onAplicar={onApplied} />)
    const campo = await screen.findByLabelText("Mensagem para o assistente")
    expect((await screen.findByTestId("uso-da-cota")).textContent).toBe("0%")

    fireEvent.change(campo, { target: { value: "quanto gastei?" } })
    fireEvent.submit(campo.closest("form")!)

    await waitFor(() => expect(screen.getByTestId("uso-da-cota").textContent).toBe("30%"))
    expect(screen.getByLabelText("Parar")).toBeTruthy()
    expect(servico.estadoDoAssistente).toHaveBeenCalledTimes(1)
  })
})

// ── Full quota ───────────────────────────────────────────────────────────────
//
// The editor drawer is the THIRD surface of the quota notice, and it had
// been left with the old copy: without the offer and saying "reabre em
// algumas horas" (reopens in a few hours) with the exact deadline at hand. An
// offer that exists on Home and not here disappears depending on the screen
// where the person hit the ceiling — which is exactly what the shared
// component exists to prevent.

describe("cota cheia na gaveta do editor", () => {
  function withQuota(over: Record<string, unknown> = {}) {
    servico.estadoDoAssistente.mockResolvedValueOnce({
      data: {
        ativo: true,
        motivo: null,
        plano: "free",
        assinaturas_ativas: true,
        cota: { gasto: 1_500_000, teto: 1_500_000, reabre_em_segundos: 22_320 },
        ...over,
      },
      error: null,
    } as never)
  }

  it("a oferta da extensão chega aqui, com o plano da pessoa, como na Home", async () => {
    withQuota()
    render(<AssistantPanel workflowId="wf1" abrirPorPadrao onAplicar={onApplied} />)

    expect(await screen.findByTestId("aviso-de-cota")).toBeTruthy()
    expect(screen.getByRole("button", { name: "oferta free true" })).toBeTruthy()
  })

  it("diz o prazo REAL, não «algumas horas»", async () => {
    withQuota()
    render(<AssistantPanel workflowId="wf1" abrirPorPadrao onAplicar={onApplied} />)

    const aviso = await screen.findByTestId("aviso-de-cota")
    expect(aviso.textContent).toContain("reabre em")
    expect(aviso.textContent).not.toContain("algumas horas")
  })
})
