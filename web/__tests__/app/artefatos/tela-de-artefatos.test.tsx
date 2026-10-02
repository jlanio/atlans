/**
 * Tela de Artefatos — o que a pessoa vê enquanto a lista carrega, pagina,
 * recarrega, filtra e falha.
 *
 * Caracterização escrita ANTES de o `useArtifactsQuery` trocar o estado feito à
 * mão (seq, offset, loading/loadingMore) pelo `useInfiniteQuery`: os mesmos
 * testes passam nas duas versões. A tela é montada inteira — o contrato é o
 * que aparece (skeleton, contagens, cartão, aviso âmbar, "Ver mais"), não o
 * formato do hook.
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { configure, render, screen, waitFor, fireEvent, within, act } from "@testing-library/react"
import { QueryClientProvider } from "@tanstack/react-query"
import type { IArtifactItem } from "@/service/types"

// Cem linhas com Checkbox do Radix custam centenas de ms no jsdom; com a suíte
// inteira em paralelo, o 1 s padrão do `waitFor` viraria intermitência. E o
// prazo de cada teste tem de caber mais de um `waitFor` desses: com os 5 s
// padrão, um só consumia o teste inteiro sob carga.
configure({ asyncUtilTimeout: 5000 })
vi.setConfig({ testTimeout: 20_000 })

vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: {
    getArtifacts: vi.fn(),
    deleteArtifact: vi.fn(),
    batchDeleteArtifacts: vi.fn(),
    getArtifactDownloadUrl: vi.fn(() => "/terra/artifacts/x/download"),
    getArtifactDownload: vi.fn(),
  },
}))

// Workspace trocável: o seletor do cabeçalho troca o contexto SEM remontar a
// página. `loading` é o gate do `enabled` (a lista espera o workspace).
const ws: { current: { id_hash: string; name: string } | null; loading: boolean } = {
  current: { id_hash: "ws-a", name: "A" },
  loading: false,
}
vi.mock("@/context/WorkspaceContext", () => ({
  useWorkspace: () => ({ current: ws.current, canEdit: true, loading: ws.loading }),
}))

vi.mock("@/utils/createToast", () => ({
  createToast: { success: vi.fn(), error: vi.fn(), info: vi.fn(), warning: vi.fn() },
}))

import { GisFlowService } from "@/service/GisFlowService"
import { criarClienteDeConsultas } from "@/lib/consultas"
import ArtifactsPage from "@/app/(dashboard)/artifacts/page"

const getArtifacts = vi.mocked(GisFlowService.getArtifacts)

type Resposta = Awaited<ReturnType<typeof GisFlowService.getArtifacts>>

function artefato(id: string, extra: Partial<IArtifactItem> = {}): IArtifactItem {
  return {
    id_hash: id, workspace_id: "ws-a", workflow_id: "wf-1", workflow_name: "Bacias",
    run_id: `run-${id}-000000`, node_id: null, output_key: `saida_${id}`,
    filename: `${id}.geojson`, format: "geojson", size_bytes: 1024, features: 3,
    protected: false, is_published: false, is_portal_active: false, is_pinned: false,
    executor_id: null, content_location: "minio",
    created_at: "2026-08-28T12:00:00", expires_at: null,
    ...extra,
  }
}

/** `n` artefatos com ids `${prefixo}${de}`…, na ordem do servidor. */
function itens(prefixo: string, de: number, n: number, extra: Partial<IArtifactItem> = {}) {
  return Array.from({ length: n }, (_, i) => artefato(`${prefixo}${de + i}`, extra))
}

const ok = (items: IArtifactItem[], total: number): Resposta =>
  ({ success: true, status: 200, data: { items, total } }) as Resposta

const falha = (message?: string): Resposta =>
  ({ success: false, status: 500, error: { name: "AxiosError", message } }) as Resposta

/** Servidor de mentira: `total` artefatos por aba, fatiados por limit/offset. */
function servidor(totais: { execution?: number; publication?: number }) {
  getArtifacts.mockImplementation(async (p = {}) => {
    const total = totais[p.kind ?? "execution"] ?? 0
    const de = p.offset ?? 0
    const n = Math.max(0, Math.min(p.limit ?? 50, total - de))
    const prefixo = p.kind === "publication" ? "p" : "a"
    return ok(itens(prefixo, de, n), total)
  })
}

type Deferido<T> = { promise: Promise<T>; resolve: (v: T) => void }
function deferido<T>(): Deferido<T> {
  let resolve!: (v: T) => void
  const promise = new Promise<T>(r => { resolve = r })
  return { promise, resolve }
}

function renderizar() {
  const cliente = criarClienteDeConsultas()
  const arvore = () => (
    <QueryClientProvider client={cliente}>
      <ArtifactsPage />
    </QueryClientProvider>
  )
  const r = render(arvore())
  return { ...r, rerenderizar: () => r.rerender(arvore()) }
}

// ── O que a tela mostra ─────────────────────────────────────────────────────

const linhas = () => document.querySelectorAll("tbody tr").length
const skeleton = () => screen.queryByRole("status", { name: "Carregando os artefatos" })
const busca = () => screen.queryByRole("textbox", { name: "Buscar artefatos" })
const botaoAtualizar = () => screen.getByRole("button", { name: "Atualizar a lista de artefatos" })
const verMais = () => screen.queryByRole("button", { name: /^(Ver mais|Carregando…)/ })
const aba = (nome: string) => within(screen.getByRole("group", { name: "Tipo de artefato" })).getByRole("button", { name: nome })
const ultimaChamada = () => getArtifacts.mock.calls.at(-1)![0]!

/** A frase sob o título, ou `null` quando ela é o esqueleto. */
function subtitulo(): string | null {
  const irmao = screen.getByRole("heading", { name: "Artefatos" }).nextElementSibling
  return irmao?.tagName === "P" ? irmao.textContent : null
}

/** O contador da aba ativa (o total do servidor), ou `null` se não há. */
function contagemDaAba(): string | null {
  const ativa = within(screen.getByRole("group", { name: "Tipo de artefato" }))
    .getAllByRole("button")
    .find(b => b.getAttribute("aria-pressed") === "true")!
  return ativa.querySelector("span")?.textContent ?? null
}

/** Um tique a mais para uma resposta atrasada ter a chance de (não) pintar. */
const mais_um_tique = () => act(async () => { await new Promise(r => setTimeout(r, 20)) })

beforeEach(() => {
  vi.clearAllMocks()
  getArtifacts.mockReset()
  ws.current = { id_hash: "ws-a", name: "A" }
  ws.loading = false
})

// ── 1ª carga ────────────────────────────────────────────────────────────────

describe("Artefatos — 1ª carga", () => {
  it("espera o workspace: sem busca e com skeleton enquanto ele carrega", async () => {
    servidor({ execution: 3 })
    ws.loading = true
    const { rerenderizar } = renderizar()

    expect(skeleton()).toBeInTheDocument()
    expect(subtitulo()).toBeNull()
    expect(busca()).toBeNull()
    expect(botaoAtualizar()).toBeDisabled()
    await mais_um_tique()
    expect(getArtifacts).not.toHaveBeenCalled()

    ws.loading = false
    rerenderizar()
    await waitFor(() => expect(linhas()).toBe(3))
    expect(getArtifacts).toHaveBeenCalledTimes(1)
    expect(ultimaChamada()).toMatchObject({ workspace_id: "ws-a", offset: 0 })
  })

  it("skeleton até a resposta; depois a tabela, as contagens e o Ver mais", async () => {
    const primeira = deferido<Resposta>()
    getArtifacts.mockReturnValueOnce(primeira.promise)
    renderizar()

    await waitFor(() => expect(getArtifacts).toHaveBeenCalledTimes(1))
    expect(getArtifacts.mock.calls[0][0]).toEqual({
      kind: "execution", search: undefined, fmt: undefined, workspace_id: "ws-a", limit: 50, offset: 0,
    })
    expect(skeleton()).toBeInTheDocument()
    expect(subtitulo()).toBeNull()
    // A barra de filtros espera a 1ª carga: não há o que filtrar ainda.
    expect(busca()).toBeNull()
    expect(botaoAtualizar()).toBeDisabled()

    primeira.resolve(ok(itens("a", 0, 50), 120))
    await waitFor(() => expect(linhas()).toBe(50))
    expect(skeleton()).toBeNull()
    expect(subtitulo()).toBe("120 artefatos de execução")
    expect(contagemDaAba()).toBe("120")
    expect(screen.getByText("50 de 120 artefatos")).toBeInTheDocument()
    expect(verMais()).toHaveTextContent("Ver mais (70 restantes)")
    expect(busca()).toBeInTheDocument()
    expect(botaoAtualizar()).toBeEnabled()
  })

  it("o Ver mais conta no singular quando falta um só", async () => {
    servidor({ execution: 51 })
    renderizar()
    await waitFor(() => expect(linhas()).toBe(50))
    expect(verMais()).toHaveTextContent("Ver mais (1 restante)")
  })

  it("1ª carga que falha: cartão com a mensagem, sem barra de filtros e sem nova tentativa sozinha", async () => {
    getArtifacts.mockResolvedValueOnce(falha("Servidor fora do ar"))
    renderizar()

    const cartao = await screen.findByRole("alert")
    expect(cartao).toHaveTextContent("Não foi possível carregar os artefatos")
    expect(cartao).toHaveTextContent("Servidor fora do ar")
    expect(busca()).toBeNull()
    expect(subtitulo()).toBeNull()
    expect(skeleton()).toBeNull()
    expect(botaoAtualizar()).toBeEnabled()
    await mais_um_tique()
    expect(getArtifacts).toHaveBeenCalledTimes(1)

    // "Tentar de novo" volta ao skeleton e pede a 1ª página.
    const segunda = deferido<Resposta>()
    getArtifacts.mockReturnValueOnce(segunda.promise)
    fireEvent.click(within(cartao).getByRole("button", { name: "Tentar de novo" }))
    await waitFor(() => expect(skeleton()).toBeInTheDocument())
    expect(screen.queryByRole("alert")).toBeNull()
    expect(getArtifacts).toHaveBeenCalledTimes(2)
    expect(ultimaChamada()).toMatchObject({ offset: 0 })

    segunda.resolve(ok(itens("a", 0, 3), 3))
    await waitFor(() => expect(linhas()).toBe(3))
    expect(subtitulo()).toBe("3 artefatos de execução")
    expect(busca()).toBeInTheDocument()
  })

  it("falha sem mensagem usa a frase padrão", async () => {
    getArtifacts.mockResolvedValueOnce(falha(undefined))
    renderizar()
    const cartao = await screen.findByRole("alert")
    expect(cartao).toHaveTextContent("Erro ao carregar artefatos.")
  })

  it("lista vazia sem recorte é o primeiro uso, com o substantivo da aba", async () => {
    servidor({ execution: 0, publication: 0 })
    renderizar()

    await waitFor(() => expect(subtitulo()).toBe("Nenhum artefato ainda"))
    // O subtítulo e o título do cartão de primeiro uso.
    expect(screen.getAllByText("Nenhum artefato ainda")).toHaveLength(2)
    expect(contagemDaAba()).toBeNull()
    expect(verMais()).toBeNull()

    fireEvent.click(aba("Publicação"))
    await waitFor(() => expect(subtitulo()).toBe("Nenhuma publicação ainda"))
  })
})

// ── Ver mais ────────────────────────────────────────────────────────────────

describe("Artefatos — Ver mais", () => {
  it("pede o offset acumulado, trava o botão sem trocar a tabela por skeleton e soma até o fim", async () => {
    servidor({ execution: 120 })
    renderizar()
    await waitFor(() => expect(linhas()).toBe(50))

    const segunda = deferido<Resposta>()
    getArtifacts.mockReturnValueOnce(segunda.promise)
    fireEvent.click(verMais()!)
    await waitFor(() => expect(verMais()).toHaveTextContent("Carregando…"))
    expect(verMais()).toBeDisabled()
    expect(ultimaChamada()).toMatchObject({ offset: 50, limit: 50 })
    // Paginar não é recarregar: a tabela, o subtítulo e o Atualizar ficam.
    expect(linhas()).toBe(50)
    expect(skeleton()).toBeNull()
    expect(subtitulo()).toBe("120 artefatos de execução")
    expect(botaoAtualizar()).toBeEnabled()

    segunda.resolve(ok(itens("a", 50, 50), 120))
    await waitFor(() => expect(linhas()).toBe(100))
    expect(screen.getByText("100 de 120 artefatos")).toBeInTheDocument()
    expect(verMais()).toHaveTextContent("Ver mais (20 restantes)")

    fireEvent.click(verMais()!)
    await waitFor(() => expect(linhas()).toBe(120))
    expect(ultimaChamada()).toMatchObject({ offset: 100 })
    expect(verMais()).toBeNull()
    expect(screen.getByText("120 de 120 artefatos")).toBeInTheDocument()
    expect(getArtifacts).toHaveBeenCalledTimes(3)
  })

  it("falha no Ver mais: lista e total ficam, aviso âmbar, e o botão tenta o mesmo offset", async () => {
    servidor({ execution: 120 })
    renderizar()
    await waitFor(() => expect(linhas()).toBe(50))

    getArtifacts.mockResolvedValueOnce(falha("A página 2 caiu"))
    fireEvent.click(verMais()!)
    const aviso = await screen.findByText("A página 2 caiu")
    expect(aviso.closest('[role="status"]')).toBeInTheDocument()
    expect(screen.queryByRole("alert")).toBeNull()
    expect(linhas()).toBe(50)
    expect(verMais()).toHaveTextContent("Ver mais (70 restantes)")
    expect(verMais()).toBeEnabled()
    expect(subtitulo()).toBe("120 artefatos de execução")
    expect(contagemDaAba()).toBe("120")
    // Com erro na tela, a contagem "N de M" sai da barra.
    expect(screen.queryByText("50 de 120 artefatos")).toBeNull()

    // Tentar de novo: o aviso sai já no clique, não só quando a página chega.
    const denovo = deferido<Resposta>()
    getArtifacts.mockReturnValueOnce(denovo.promise)
    fireEvent.click(verMais()!)
    await waitFor(() => expect(verMais()).toHaveTextContent("Carregando…"))
    expect(screen.queryByText("A página 2 caiu")).toBeNull()
    expect(ultimaChamada()).toMatchObject({ offset: 50 })

    denovo.resolve(ok(itens("a", 50, 50), 120))
    await waitFor(() => expect(linhas()).toBe(100))
    expect(screen.getByText("100 de 120 artefatos")).toBeInTheDocument()
  })
})

// ── Recarga ─────────────────────────────────────────────────────────────────

describe("Artefatos — recarga", () => {
  it("Atualizar: skeleton no lugar da tabela e UMA requisição da 1ª página, que substitui a lista", async () => {
    servidor({ execution: 120 })
    renderizar()
    await waitFor(() => expect(linhas()).toBe(50))
    fireEvent.click(verMais()!)
    await waitFor(() => expect(linhas()).toBe(100))

    const antes = getArtifacts.mock.calls.length
    const recarga = deferido<Resposta>()
    getArtifacts.mockReturnValueOnce(recarga.promise)
    fireEvent.click(botaoAtualizar())
    await waitFor(() => expect(skeleton()).toBeInTheDocument())
    expect(linhas()).toBe(0)
    expect(verMais()).toBeNull()
    expect(subtitulo()).toBeNull()
    expect(botaoAtualizar()).toBeDisabled()
    // A barra e as contagens do que havia ficam durante a recarga.
    expect(busca()).toBeInTheDocument()
    expect(screen.getByText("100 de 120 artefatos")).toBeInTheDocument()
    expect(contagemDaAba()).toBe("120")

    recarga.resolve(ok(itens("n", 0, 50), 121))
    await waitFor(() => expect(linhas()).toBe(50))
    expect(getArtifacts.mock.calls.length).toBe(antes + 1)
    expect(ultimaChamada()).toMatchObject({ offset: 0, limit: 50 })
    expect(screen.getByLabelText("Selecionar n0.geojson")).toBeInTheDocument()
    expect(subtitulo()).toBe("121 artefatos de execução")
    expect(screen.getByText("50 de 121 artefatos")).toBeInTheDocument()
    expect(verMais()).toHaveTextContent("Ver mais (71 restantes)")

    // O Ver mais seguinte continua do que a recarga trouxe.
    fireEvent.click(verMais()!)
    await waitFor(() => expect(ultimaChamada()).toMatchObject({ offset: 50 }))
  })

  it("Atualizar que falha: a lista inteira fica, com o aviso âmbar; o Tentar de novo do aviso recarrega", async () => {
    servidor({ execution: 120 })
    renderizar()
    await waitFor(() => expect(linhas()).toBe(50))
    fireEvent.click(verMais()!)
    await waitFor(() => expect(linhas()).toBe(100))

    getArtifacts.mockResolvedValueOnce(falha("Sem conexão com o servidor"))
    fireEvent.click(botaoAtualizar())
    const aviso = await screen.findByText("Sem conexão com o servidor")
    const linhaAmbar = aviso.closest('[role="status"]') as HTMLElement
    expect(linhaAmbar).toBeInTheDocument()
    expect(screen.queryByRole("alert")).toBeNull()
    expect(linhas()).toBe(100)
    expect(verMais()).toHaveTextContent("Ver mais (20 restantes)")
    expect(subtitulo()).toBe("120 artefatos de execução")
    expect(botaoAtualizar()).toBeEnabled()

    // O Tentar de novo do aviso é a mesma recarga: o aviso sai no clique, o
    // skeleton entra, e a contagem do que havia volta à barra enquanto isso.
    const denovo = deferido<Resposta>()
    getArtifacts.mockReturnValueOnce(denovo.promise)
    fireEvent.click(within(linhaAmbar).getByRole("button", { name: "Tentar de novo" }))
    await waitFor(() => expect(skeleton()).toBeInTheDocument())
    expect(screen.queryByText("Sem conexão com o servidor")).toBeNull()
    expect(screen.getByText("100 de 120 artefatos")).toBeInTheDocument()
    expect(ultimaChamada()).toMatchObject({ offset: 0 })

    denovo.resolve(ok(itens("a", 0, 50), 120))
    await waitFor(() => expect(linhas()).toBe(50))
    expect(screen.queryByText("Sem conexão com o servidor")).toBeNull()
  })

  it("Atualizar com o Ver mais em voo: a recarga vence e a página atrasada é descartada", async () => {
    servidor({ execution: 120 })
    renderizar()
    await waitFor(() => expect(linhas()).toBe(50))

    const pagina2 = deferido<Resposta>()
    const recarga = deferido<Resposta>()
    getArtifacts.mockReturnValueOnce(pagina2.promise).mockReturnValueOnce(recarga.promise)
    fireEvent.click(verMais()!)
    await waitFor(() => expect(verMais()).toHaveTextContent("Carregando…"))
    fireEvent.click(botaoAtualizar())
    await waitFor(() => expect(skeleton()).toBeInTheDocument())
    expect(ultimaChamada()).toMatchObject({ offset: 0 })

    recarga.resolve(ok(itens("n", 0, 50), 120))
    await waitFor(() => expect(linhas()).toBe(50))
    pagina2.resolve(ok(itens("velho", 50, 50), 120))
    await mais_um_tique()
    expect(linhas()).toBe(50)
    expect(screen.queryByLabelText("Selecionar velho50.geojson")).toBeNull()
    expect(verMais()).toHaveTextContent("Ver mais (70 restantes)")
    expect(verMais()).toBeEnabled()
  })

  it("excluir recarrega a partir da 1ª página", async () => {
    servidor({ execution: 120 })
    vi.mocked(GisFlowService.deleteArtifact).mockResolvedValue({ success: true, status: 204 })
    renderizar()
    await waitFor(() => expect(linhas()).toBe(50))
    fireEvent.click(verMais()!)
    await waitFor(() => expect(linhas()).toBe(100))

    fireEvent.click(screen.getByLabelText("Selecionar a3.geojson"))
    fireEvent.click(screen.getByRole("button", { name: "Excluir 1" }))
    const dialogo = await screen.findByRole("dialog")
    const antes = getArtifacts.mock.calls.length
    fireEvent.click(within(dialogo).getByRole("button", { name: "Excluir" }))

    await waitFor(() => expect(GisFlowService.deleteArtifact).toHaveBeenCalledWith("a3"))
    await waitFor(() => expect(linhas()).toBe(50))
    expect(getArtifacts.mock.calls.length).toBe(antes + 1)
    expect(ultimaChamada()).toMatchObject({ offset: 0 })
  })
})

// ── Filtros ─────────────────────────────────────────────────────────────────

describe("Artefatos — filtros", () => {
  it("trocar de aba zera a lista (skeleton, sem contagens), mantém a barra e busca a 1ª página da outra aba", async () => {
    servidor({ execution: 120, publication: 3 })
    renderizar()
    await waitFor(() => expect(linhas()).toBe(50))

    const publicacoes = deferido<Resposta>()
    getArtifacts.mockReturnValueOnce(publicacoes.promise)
    fireEvent.click(aba("Publicação"))
    await waitFor(() => expect(skeleton()).toBeInTheDocument())
    expect(linhas()).toBe(0)
    expect(subtitulo()).toBeNull()
    expect(contagemDaAba()).toBeNull()
    expect(screen.queryByText(/ de 120 artefatos$/)).toBeNull()
    expect(busca()).toBeInTheDocument()
    expect(ultimaChamada()).toMatchObject({ kind: "publication", offset: 0 })

    publicacoes.resolve(ok(itens("p", 0, 3, { is_published: true }), 3))
    await waitFor(() => expect(linhas()).toBe(3))
    expect(subtitulo()).toBe("3 publicações")
    expect(contagemDaAba()).toBe("3")
    expect(screen.getByText("3 de 3 publicações")).toBeInTheDocument()
  })

  it("voltar a uma aba já vista recomeça do zero: a tela não guarda cache", async () => {
    servidor({ execution: 120, publication: 3 })
    renderizar()
    await waitFor(() => expect(linhas()).toBe(50))
    fireEvent.click(verMais()!)
    await waitFor(() => expect(linhas()).toBe(100))
    fireEvent.click(aba("Publicação"))
    await waitFor(() => expect(linhas()).toBe(3))
    const antes = getArtifacts.mock.calls.length

    const volta = deferido<Resposta>()
    getArtifacts.mockReturnValueOnce(volta.promise)
    fireEvent.click(aba("Execução"))
    await waitFor(() => expect(skeleton()).toBeInTheDocument())
    expect(linhas()).toBe(0)
    // Nada da visita anterior enquanto a lista não chega: nem o total da aba,
    // nem o "N de M".
    expect(contagemDaAba()).toBeNull()
    expect(screen.queryByText(/ de 120 artefatos$/)).toBeNull()
    expect(ultimaChamada()).toMatchObject({ kind: "execution", offset: 0 })

    volta.resolve(ok(itens("a", 0, 50), 120))
    await waitFor(() => expect(linhas()).toBe(50))
    // Só a 1ª página, com uma requisição — não as duas que estavam abertas.
    expect(getArtifacts.mock.calls.length).toBe(antes + 1)
    expect(verMais()).toHaveTextContent("Ver mais (70 restantes)")
  })

  it("a busca vai ao servidor com debounce e sem espaços; sem resultado oferece Limpar filtros", async () => {
    servidor({ execution: 120 })
    renderizar()
    await waitFor(() => expect(linhas()).toBe(50))
    getArtifacts.mockClear()

    getArtifacts.mockResolvedValueOnce(ok([], 0))
    fireEvent.change(busca()!, { target: { value: "  bacia  " } })
    expect(getArtifacts).not.toHaveBeenCalled()
    await waitFor(() => expect(getArtifacts).toHaveBeenCalledTimes(1))
    expect(ultimaChamada()).toMatchObject({ search: "bacia", offset: 0 })

    await waitFor(() => expect(screen.getByText("Nenhum artefato com «bacia»")).toBeInTheDocument())
    expect(subtitulo()).toBe("Nenhum resultado para o filtro")

    fireEvent.click(screen.getByRole("button", { name: "Limpar filtros" }))
    await waitFor(() => expect(linhas()).toBe(50))
    expect(ultimaChamada().search).toBeUndefined()
    expect(busca()).toHaveValue("")
  })

  it("os chips de formato acumulam o que já veio; escolher um busca da 1ª página com fmt", async () => {
    getArtifacts.mockResolvedValueOnce(ok([
      ...itens("g", 0, 2, { format: "geojson" }),
      ...itens("c", 0, 1, { format: "csv", filename: "c0.csv" }),
    ], 3))
    renderizar()
    const grupo = await screen.findByRole("group", { name: "Formato" })
    expect(within(grupo).getAllByRole("button").map(b => b.textContent)).toEqual(["Todos", "CSV", "GEOJSON"])

    getArtifacts.mockResolvedValueOnce(ok(itens("c", 0, 1, { format: "csv", filename: "c0.csv" }), 1))
    fireEvent.click(within(grupo).getByRole("button", { name: "CSV" }))
    await waitFor(() => expect(linhas()).toBe(1))
    expect(ultimaChamada()).toMatchObject({ fmt: "csv", offset: 0 })
    // O servidor só devolveu CSV, e os chips continuam todos.
    const depois = screen.getByRole("group", { name: "Formato" })
    expect(within(depois).getAllByRole("button").map(b => b.textContent)).toEqual(["Todos", "CSV", "GEOJSON"])
  })

  it("a resposta atrasada de uma busca anterior não toma a tela da busca atual", async () => {
    servidor({ execution: 120 })
    renderizar()
    await waitFor(() => expect(linhas()).toBe(50))

    const lenta = deferido<Resposta>()
    const rapida = deferido<Resposta>()
    getArtifacts.mockReturnValueOnce(lenta.promise).mockReturnValueOnce(rapida.promise)
    fireEvent.change(busca()!, { target: { value: "rio" } })
    await waitFor(() => expect(ultimaChamada()).toMatchObject({ search: "rio" }))
    fireEvent.change(busca()!, { target: { value: "mar" } })
    await waitFor(() => expect(ultimaChamada()).toMatchObject({ search: "mar" }))

    rapida.resolve(ok(itens("mar", 0, 2), 2))
    await waitFor(() => expect(linhas()).toBe(2))
    lenta.resolve(ok(itens("rio", 0, 7), 7))
    await mais_um_tique()
    expect(linhas()).toBe(2)
    expect(screen.getByText("2 de 2 artefatos")).toBeInTheDocument()
    expect(subtitulo()).toBe("2 artefatos de execução")
  })

  it("trocar de workspace recomeça da 1ª página do novo workspace", async () => {
    servidor({ execution: 120 })
    const { rerenderizar } = renderizar()
    await waitFor(() => expect(linhas()).toBe(50))
    fireEvent.click(verMais()!)
    await waitFor(() => expect(linhas()).toBe(100))

    const novo = deferido<Resposta>()
    getArtifacts.mockReturnValueOnce(novo.promise)
    ws.current = { id_hash: "ws-b", name: "B" }
    rerenderizar()
    await waitFor(() => expect(skeleton()).toBeInTheDocument())
    expect(linhas()).toBe(0)
    expect(ultimaChamada()).toMatchObject({ workspace_id: "ws-b", offset: 0 })

    novo.resolve(ok(itens("b", 0, 5), 5))
    await waitFor(() => expect(linhas()).toBe(5))
    expect(subtitulo()).toBe("5 artefatos de execução")
  })

  it("filtro que falha depois de uma carga aceita: aviso âmbar sobre o vazio, e a barra fica", async () => {
    servidor({ execution: 120 })
    renderizar()
    await waitFor(() => expect(linhas()).toBe(50))

    getArtifacts.mockResolvedValueOnce(falha("Busca indisponível"))
    fireEvent.change(busca()!, { target: { value: "rio" } })
    const aviso = await screen.findByText("Busca indisponível")
    expect(aviso.closest('[role="status"]')).toBeInTheDocument()
    // Não é o cartão de erro: a barra fica, com o termo, para a pessoa sair dele.
    expect(screen.queryByRole("alert")).toBeNull()
    expect(busca()).toHaveValue("rio")
    expect(screen.getByText("Nenhum artefato com «rio»")).toBeInTheDocument()
    expect(subtitulo()).toBe("Nenhum resultado para o filtro")
    expect(linhas()).toBe(0)
    expect(verMais()).toBeNull()
  })
})

// ── Polling ─────────────────────────────────────────────────────────────────

describe("Artefatos — sem polling", () => {
  it("a lista não se refaz sozinha: nem com o tempo, nem ao voltar o foco, nem ao reconectar", async () => {
    servidor({ execution: 10 })
    renderizar()
    await waitFor(() => expect(linhas()).toBe(10))

    await act(async () => {
      window.dispatchEvent(new Event("focus"))
      document.dispatchEvent(new Event("visibilitychange", { bubbles: true }))
      window.dispatchEvent(new Event("online"))
      await new Promise(r => setTimeout(r, 50))
    })
    expect(getArtifacts).toHaveBeenCalledTimes(1)
  })
})
