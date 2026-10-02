/**
 * A gaveta do assistente, de ponta a ponta: mensagem → stream → cartão → Aplicar.
 *
 * O teste que dá razão a este arquivo é o do **Aplicar não salva**. O assistente
 * não grava por portão duro no servidor, e o botão é a única ponte entre a
 * conversa e o canvas. Se um dia ele passar a chamar a rota de escrita "por
 * conveniência", o portão inteiro vira decoração — e a decisão do dono era
 * justamente que gravar é da pessoa, pelo botão Salvar.
 *
 * O `fetch` é de mentira, mas o stream é de verdade: um `ReadableStream` que
 * entrega os quadros do jeito que a rede entrega, em pedaços que não respeitam
 * fronteira de quadro.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, cleanup, fireEvent, waitFor } from "@testing-library/react"

// `vi.mock` é içado para o topo do arquivo, então a fábrica não pode fechar
// sobre variável de módulo — daí `vi.hoisted`.
const servico = vi.hoisted(() => ({
  estadoDoAssistente: vi.fn(async () => ({ data: { ativo: true, motivo: null as string | null, cota: null }, error: null })),
  esquecerConversaDoAssistente: vi.fn(async () => ({ data: undefined, error: null })),
}))
vi.mock("@/service/GisFlowService", () => ({ GisFlowService: servico }))

// Uma extensão de mentira com oferta na cota cheia: a gaveta é uma das três
// superfícies do aviso, e a oferta tem de chegar aqui também.
vi.mock("@/extensoes", async (original) => ({
  ...(await original<typeof import("@/extensoes")>()),
  EXTENSOES: [{
    nome: "teste",
    ofertaDaCota: ({ plano, assinaturasAtivas }: { plano?: string | null; assinaturasAtivas?: boolean }) => (
      <button type="button">oferta {plano} {String(assinaturasAtivas)}</button>
    ),
  }],
}))

// O cartão assina o canvas por `useNodes`. Aqui o canvas está vazio — é a tela
// de criar, que é onde a gaveta nasce aberta.
vi.mock("@xyflow/react", async (original) => ({
  ...(await original<Record<string, unknown>>()),
  useNodes: vi.fn(() => []),
}))

import AssistentePainel from "@/app/components/workflow/assistente"
import { useAssistenteEditorStore } from "@/app/stores/assistenteEditorStore"
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

/** Os quadros de uma conversa que monta e valida um fluxo. */
function corpoDaConversa(): string {
  return (
    quadro("pensando", { texto: "preciso do catálogo" }) +
    quadro("texto", { texto: "Vou montar " }) +
    quadro("texto", { texto: "o fluxo." }) +
    quadro("ferramenta", { id: "t1", nome: "search_nodes", argumentos: { query: "buffer" } }) +
    quadro("ferramenta_fim", { id: "t1", nome: "search_nodes", erro: false }) +
    // Desenha ANTES de validar: e a ordem do contrato novo, e e o que torna a
    // montagem incremental. Validar virou conferencia do que ja esta na tela.
    quadro("ferramenta", { id: "t2", nome: "desenhar_no_canvas", argumentos: { definition: { __campos__: 2 } } }) +
    quadro("ferramenta_fim", { id: "t2", nome: "desenhar_no_canvas", erro: false }) +
    quadro("proposta", { definicao: DEFINICAO, nos: 2, arestas: 1, desenhar: true, nota: "montei o buffer" }) +
    quadro("ferramenta", { id: "t3", nome: "validate_workflow", argumentos: { definition: { __campos__: 2 } } }) +
    quadro("ferramenta_fim", { id: "t3", nome: "validate_workflow", erro: false }) +
    quadro("proposta", { definicao: DEFINICAO, nos: 2, arestas: 1, ok: true, erros: 0, avisos: 0 }) +
    quadro("fim", { transcrito: [], uso: { total: 1234 }, voltas: 2, ok: true })
  )
}

/** Um corpo SSE entregue em pedaços que CORTAM quadros ao meio, como a rede faz.
 *
 * O `pull` é ASSÍNCRONO de propósito: cede o loop entre um pedaço e outro, que é
 * o que a rede (e um runner de CI carregado) fazem. Com `pull` síncrono o stream
 * inteiro drenava dentro de um `waitFor` e escondia qualquer corrida entre o
 * teste e os quadros — inclusive a que derrubou o CI do #137. */
function streamPicado(corpo: string, pedacos = 7): ReadableStream<Uint8Array> {
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

let fetchFalso: ReturnType<typeof vi.fn>

beforeEach(() => {
  cleanup()
  servico.estadoDoAssistente.mockClear()
  servico.esquecerConversaDoAssistente.mockClear()
  useAssistenteEditorStore.setState({ aberto: true })
  useWorkflowCatalogStore.setState({ nodesAPI: catalogo })
  localStorage.clear()

  fetchFalso = vi.fn(async () => new Response(streamPicado(corpoDaConversa()), {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  }))
  vi.stubGlobal("fetch", fetchFalso)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

async function conversar() {
  render(<AssistentePainel workflowId="wf1" abrirPorPadrao onAplicar={aplicou} />)
  const campo = await screen.findByLabelText("Mensagem para o assistente")
  fireEvent.change(campo, { target: { value: "monta um buffer de 500m" } })
  fireEvent.submit(campo.closest("form")!)
  await screen.findAllByTestId("cartao-proposta")
  await waitFor(() => expect(screen.queryByLabelText("Parar")).toBeNull())
}

const aplicou = vi.fn()

describe("gaveta do assistente", () => {
  beforeEach(() => aplicou.mockClear())

  it("desenha a conversa a partir do stream, quadro a quadro", async () => {
    await conversar()

    expect(screen.getByText("monta um buffer de 500m")).toBeTruthy()
    expect(screen.getByText("Vou montar o fluxo.")).toBeTruthy()
    // Nome de ferramenta nunca vai cru para a tela — é o padrão de
    // `status-rotulos.ts`, e "search_nodes" não diz nada a quem monta fluxo.
    expect(screen.getByText("Procurando nós")).toBeTruthy()
    expect(screen.queryByText(/search_nodes/)).toBeNull()
    expect(screen.getByText("Validando o fluxo")).toBeTruthy()
  })

  it("no canvas vazio o fluxo entra sozinho, sem botão", async () => {
    // A tela de criar: não há trabalho a perder, então desenhar não pede nada.
    // É isto que torna a construção INCREMENTAL — sem botão a cada passo, o
    // fluxo cresce enquanto o modelo monta.
    await conversar()

    expect(aplicou).toHaveBeenCalled()
    expect(screen.getByText("Desenhado no canvas")).toBeTruthy()
    expect(screen.getByText("montei o buffer")).toBeTruthy()
    expect(screen.queryByRole("button", { name: /Desenhar no canvas/ })).toBeNull()
  })

  it("o veredito da validação aparece separado, e não redesenha", async () => {
    // Dois papéis no mesmo quadro: `desenhar_no_canvas` põe na tela,
    // `validate_workflow` confere. Se o veredito também desenhasse, cada
    // validação desfaria o que a pessoa mexeu entre um passo e outro.
    await conversar()

    expect(screen.getByText("Validação limpa")).toBeTruthy()
    expect(aplicou).toHaveBeenCalledTimes(1)
  })

  it("desenhar leva a definição ao canvas — e NÃO chama a rede", async () => {
    await conversar()

    // O que a rede já fez até aqui: o estado na montagem e o POST da conversa.
    const antesFetch = fetchFalso.mock.calls.length
    const antesServico =
      servico.estadoDoAssistente.mock.calls.length + servico.esquecerConversaDoAssistente.mock.calls.length

    expect(aplicou).toHaveBeenCalledTimes(1)
    const resultado = aplicou.mock.calls[0][0]
    expect(resultado.nodes.map((n: { id: string }) => n.id)).toEqual(["a", "b"])
    expect(resultado.edges).toHaveLength(1)

    // A asserção que importa: aplicar é local. Quem grava é o Salvar.
    expect(fetchFalso.mock.calls.length).toBe(antesFetch)
    expect(
      servico.estadoDoAssistente.mock.calls.length + servico.esquecerConversaDoAssistente.mock.calls.length,
    ).toBe(antesServico)
  })

  it("manda só a mensagem nova — o transcrito é do servidor", async () => {
    // Um cliente que guardasse o transcrito poderia reescrever um `tool_result`,
    // e um `tool_result` é a palavra do SERVIDOR sobre o que aconteceu. A rota
    // recusa campo a mais com 422; o painel não pode tentar mandar.
    await conversar()
    const [, init] = fetchFalso.mock.calls[0] as [string, RequestInit]
    expect(JSON.parse(String(init.body))).toEqual({
      mensagem: "monta um buffer de 500m",
      workflow_id: "wf1",
    })
  })

  it("validação com erro é dita em voz alta, e não some", async () => {
    // O fluxo com erro CONTINUA na tela: e onde a pessoa ve o problema. O que
    // o cartao faz e dizer que a validacao reprovou, para o modelo corrigir e
    // redesenhar — antes isso desligava um botao; agora e informacao.
    fetchFalso.mockImplementation(async () => new Response(
      streamPicado(
        quadro("proposta", { definicao: DEFINICAO, nos: 2, arestas: 1, ok: false, erros: 2, avisos: 0 }) +
        quadro("fim", { transcrito: [], uso: {}, voltas: 1, ok: true }),
      ),
      { status: 200 },
    ))

    await conversar()
    expect(screen.getByText("Validação com pendências")).toBeTruthy()
    expect(screen.getByText(/A validação apontou 2 erros/)).toBeTruthy()
    // Veredito nao desenha: nada foi aplicado no canvas por causa dele.
    expect(aplicou).not.toHaveBeenCalled()
  })

  it("num canvas com trabalho, o primeiro desenho espera o clique", async () => {
    // A decisao do dono: avisar UMA VEZ por conversa. Redesenhar sem aviso o
    // que alguem montou a mao e destrutivo demais para acontecer calado; pedir
    // a cada no seria o oposto de acompanhar o fluxo crescer.
    const { useNodes } = await import("@xyflow/react")
    vi.mocked(useNodes).mockReturnValue([
      { id: "ja-existia", position: { x: 0, y: 0 }, data: {} },
    ] as never)

    try {
      await conversar()

      const botao = screen.getByRole("button", { name: /Desenhar no canvas/ })
      expect(aplicou).not.toHaveBeenCalled()

      fireEvent.click(botao)
      expect(aplicou).toHaveBeenCalledTimes(1)
    } finally {
      vi.mocked(useNodes).mockReturnValue([] as never)
    }
  })

  it("um turno não recebe os quadros do outro", async () => {
    // A conversa tem vários turnos, e cada quadro pertence a UM deles. Sem o
    // endereçamento por id, a resposta nova seria escrita também na antiga — e
    // o painel passaria a mostrar duas vezes o que o modelo disse uma.
    await conversar()

    fetchFalso.mockImplementation(async () => new Response(
      streamPicado(
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
    // Aberto na store de propósito: nem assim a gaveta pode existir — e nem o
    // botão que a abre, que é o que sobra quando ela está fechada.
    useAssistenteEditorStore.setState({ aberto: true })

    const { container } = render(<AssistentePainel onAplicar={aplicou} />)
    await waitFor(() => expect(servico.estadoDoAssistente).toHaveBeenCalled())

    expect(container.querySelector("aside")).toBeNull()
    expect(screen.queryByLabelText("Abrir o assistente")).toBeNull()
    expect(container.firstChild).toBeNull()
  })

  it("falha na rota vira um erro na conversa, e não uma tela quebrada", async () => {
    fetchFalso.mockImplementation(async () => new Response(
      JSON.stringify({ error: "recusado", message: "Já há uma conversa em andamento neste fluxo." }),
      { status: 409 },
    ))

    render(<AssistentePainel workflowId="wf1" abrirPorPadrao onAplicar={aplicou} />)
    const campo = await screen.findByLabelText("Mensagem para o assistente")
    fireEvent.change(campo, { target: { value: "oi" } })
    fireEvent.submit(campo.closest("form")!)

    expect(await screen.findByText(/Já há uma conversa em andamento/)).toBeTruthy()
  })
  it("o raciocínio nasce recolhido — e o texto continua no DOM", async () => {
    // O resumo do pensamento chega em INGLÊS e não há como pedir outro idioma:
    // ele é gerado por um passo separado que não lê o system prompt. Recolher é
    // a resposta; apagar não seria, porque quem quiser auditar o que o modelo
    // pensou tem de conseguir chegar lá.
    await conversar()

    const bloco = document.querySelector("details")!
    expect(bloco.open).toBe(false)
    // O jsdom não esconde nada, então a asserção honesta é sobre VISIBILIDADE e
    // não sobre presença — e a presença é justamente o contrato que se quer:
    // Ctrl+F e leitor de tela continuam alcançando o texto.
    expect(screen.getByText("preciso do catálogo")).not.toBeVisible()
    expect(screen.getByText("Raciocínio")).toBeVisible()
  })

  it("clicar abre o raciocínio, e ele continua aberto no turno seguinte", async () => {
    // A segunda metade é o teste de regressão do `key={i}` de `Grupo`: os turnos
    // são reconstruídos imutavelmente a cada delta, e se o índice de um grupo
    // deslocasse, o bloco aberto trocaria de dono no meio da leitura.
    await conversar()

    fireEvent.click(document.querySelector("summary")!)
    expect(screen.getByText("preciso do catálogo")).toBeVisible()

    fetchFalso.mockImplementation(async () => new Response(
      streamPicado(
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
    const { container } = render(<AssistentePainel workflowId="wf1" abrirPorPadrao onAplicar={aplicou} />)
    await screen.findByLabelText("Mensagem para o assistente")

    // O PAR, e não metade dele. `h-full` sozinho pende de uma cadeia cujo topo
    // é `min-h-svh` — piso, não teto —, então a conversa cresce a página e a
    // rolagem vai para o viewport em vez da lista. `max-h-svh` sozinho
    // colapsaria no dia em que o container do editor deixasse de esticar os
    // filhos. Tirar qualquer um dos dois derruba este teste.
    const gaveta = container.querySelector("aside")!
    expect(gaveta.className).toContain("h-full")
    expect(gaveta.className).toContain("max-h-svh")
  })

  it("há UM container de rolagem, e ele existe mesmo com a conversa vazia", async () => {
    // O estado vazio era irmão do formulário e não rolava. Com o teto de altura
    // isso vira defeito: num viewport curto, ~300px de convite mais cabeçalho e
    // formulário empurram o campo de enviar para fora da tela e não há nada
    // para rolar — justamente em `/workflow/create`, onde a gaveta nasce aberta.
    const { container } = render(<AssistentePainel abrirPorPadrao onAplicar={aplicou} />)
    await screen.findByText("Descreva o fluxo que você quer")

    const rolagem = container.querySelectorAll("aside [class*='overflow-y-auto']")
    expect(rolagem).toHaveLength(1)
    expect(rolagem[0].className).toContain("min-h-0")
    // Contrato de classe, e não prova de rolagem: o jsdom não faz layout, então
    // `scrollHeight` e `clientHeight` são zero aqui. Quem prova é o editor
    // aberto com a conversa longa.
  })

  it("mostra o donut da cota sob o campo, com o percentual e a faixa", async () => {
    servico.estadoDoAssistente.mockResolvedValueOnce({
      data: { ativo: true, motivo: null, cota: { gasto: 1_230_000, teto: 1_500_000, reabre_em_segundos: 10_800 } },
      error: null,
    } as unknown as Awaited<ReturnType<typeof servico.estadoDoAssistente>>)
    render(<AssistentePainel workflowId="wf1" abrirPorPadrao onAplicar={aplicou} />)

    const donut = await screen.findByTestId("uso-da-cota")
    expect(donut.textContent).toBe("82%")
    expect(donut.dataset.faixa).toBe("alerta")
    // O mesmo detalhe da Home no aria-label: gasto, teto e percentual.
    expect(donut.getAttribute("aria-label")).toContain("1.230.000 de 1.500.000 tokens (82%)")
  })

  it("o aviso de cota não encolhe — é o único irmão da coluna que podia", async () => {
    servico.estadoDoAssistente.mockResolvedValueOnce({
      data: { ativo: true, motivo: null, cota: { gasto: 2_000_000, teto: 1_500_000, reabre_em: null } },
      error: null,
    } as unknown as Awaited<ReturnType<typeof servico.estadoDoAssistente>>)
    render(<AssistentePainel workflowId="wf1" abrirPorPadrao onAplicar={aplicou} />)
    // Pelo `data-testid`, e não pelo texto: o aviso virou o componente
    // compartilhado, e o texto mora num `<span>` DENTRO do parágrafo. Buscar
    // pelo texto devolveria o filho, cuja classe não é a que segura o layout —
    // o teste passaria a medir o elemento errado e pararia de proteger nada.
    const aviso = await screen.findByTestId("aviso-de-cota")

    // O cabeçalho e o formulário já têm `shrink-0`, e a conversa tem fator de
    // encolhimento escalado ZERO (`flex-basis: 0%`). Sem isto, o algoritmo mira
    // neste parágrafo quando o espaço fica negativo — e ele não tem o que dar.
    expect(aviso.className).toContain("shrink-0")
  })
})

describe("gaveta do assistente — a cota durante o turno", () => {
  it("o donut sobe com o quadro `cota` do stream, antes de o turno acabar", async () => {
    servico.estadoDoAssistente.mockResolvedValueOnce({
      data: { ativo: true, motivo: null, cota: { gasto: 0, teto: 1_000_000, reabre_em_segundos: null } },
      error: null,
    } as unknown as Awaited<ReturnType<typeof servico.estadoDoAssistente>>)
    // Um stream que manda a cota e fica aberto: o que a tela mostra veio do quadro.
    const aberto = new ReadableStream<Uint8Array>({
      start(c) { c.enqueue(new TextEncoder().encode('event: cota\ndata: {"gasto":300000,"teto":1000000}\n\n')) },
    })
    fetchFalso.mockImplementationOnce(async () => new Response(aberto, {
      status: 200, headers: { "Content-Type": "text/event-stream" },
    }))
    render(<AssistentePainel workflowId="wf1" abrirPorPadrao onAplicar={aplicou} />)
    const campo = await screen.findByLabelText("Mensagem para o assistente")
    expect((await screen.findByTestId("uso-da-cota")).textContent).toBe("0%")

    fireEvent.change(campo, { target: { value: "quanto gastei?" } })
    fireEvent.submit(campo.closest("form")!)

    await waitFor(() => expect(screen.getByTestId("uso-da-cota").textContent).toBe("30%"))
    expect(screen.getByLabelText("Parar")).toBeTruthy()
    expect(servico.estadoDoAssistente).toHaveBeenCalledTimes(1)
  })
})

// ── A cota cheia ─────────────────────────────────────────────────────────────
//
// A gaveta do editor é a TERCEIRA superfície do aviso de cota, e ela tinha
// ficado com a cópia antiga: sem a oferta e dizendo «reabre em algumas horas»
// com o prazo exato na mão. Uma oferta que existe na Home e não aqui some
// conforme a tela em que a pessoa bateu no teto — que é exatamente o que o
// componente compartilhado existe para impedir.

describe("cota cheia na gaveta do editor", () => {
  function comCota(over: Record<string, unknown> = {}) {
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
    comCota()
    render(<AssistentePainel workflowId="wf1" abrirPorPadrao onAplicar={aplicou} />)

    expect(await screen.findByTestId("aviso-de-cota")).toBeTruthy()
    expect(screen.getByRole("button", { name: "oferta free true" })).toBeTruthy()
  })

  it("diz o prazo REAL, não «algumas horas»", async () => {
    comCota()
    render(<AssistentePainel workflowId="wf1" abrirPorPadrao onAplicar={aplicou} />)

    const aviso = await screen.findByTestId("aviso-de-cota")
    expect(aviso.textContent).toContain("reabre em")
    expect(aviso.textContent).not.toContain("algumas horas")
  })
})
