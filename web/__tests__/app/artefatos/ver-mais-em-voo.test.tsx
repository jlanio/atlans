/**
 * Tela de Artefatos — um "Ver mais" em voo não sobrevive à saída da chave.
 *
 * O `queryFn` não aborta a requisição, e o `gcTime: 0` do cliente só descarta a
 * consulta ociosa. Sem o cancelamento na saída, a consulta da chave deixada
 * seguia viva com o "Ver mais" em voo: voltar à aba (ou remontar a tela, com o
 * provedor do layout de pé) pegava carona nessa busca e mostrava a lista
 * guardada, sem skeleton e sem pedir a 1ª página de novo — e a página velha do
 * "Ver mais" entrava na tela quando respondia. O hook feito à mão de antes
 * começava do zero nos dois casos.
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { configure, render, screen, waitFor, fireEvent, within, act } from "@testing-library/react"
import { QueryClientProvider, type QueryClient } from "@tanstack/react-query"
import type { IArtifactItem } from "@/service/types"

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
vi.mock("@/context/WorkspaceContext", () => ({
  useWorkspace: () => ({ current: { id_hash: "ws-a", name: "A" }, canEdit: true, loading: false }),
}))
vi.mock("@/utils/createToast", () => ({
  createToast: { success: vi.fn(), error: vi.fn(), info: vi.fn(), warning: vi.fn() },
}))

import { GisFlowService } from "@/service/GisFlowService"
import { criarClienteDeConsultas } from "@/lib/consultas"
import ArtifactsPage from "@/app/(dashboard)/artifacts/page"

const getArtifacts = vi.mocked(GisFlowService.getArtifacts)
type Resposta = Awaited<ReturnType<typeof GisFlowService.getArtifacts>>

function artefato(id: string): IArtifactItem {
  return {
    id_hash: id, workspace_id: "ws-a", workflow_id: "wf-1", workflow_name: "Bacias",
    run_id: `run-${id}-000000`, node_id: null, output_key: `saida_${id}`,
    filename: `${id}.geojson`, format: "geojson", size_bytes: 1024, features: 3,
    protected: false, is_published: false, is_portal_active: false, is_pinned: false,
    executor_id: null, content_location: "minio",
    created_at: "2026-08-28T12:00:00", expires_at: null,
  }
}
const itens = (prefixo: string, de: number, n: number) =>
  Array.from({ length: n }, (_, i) => artefato(`${prefixo}${de + i}`))
const ok = (items: IArtifactItem[], total: number): Resposta =>
  ({ success: true, status: 200, data: { items, total } }) as Resposta

/** Servidor: 120 de execução e 3 de publicação; `prefixo` é o conteúdo de agora
 *  da aba de execução (muda quando uma execução nova grava artefatos). */
function servidor(prefixo: string) {
  getArtifacts.mockImplementation(async (p = {}) => {
    const kind = p.kind ?? "execution"
    const total = kind === "publication" ? 3 : 120
    const de = p.offset ?? 0
    const n = Math.max(0, Math.min(p.limit ?? 50, total - de))
    return ok(itens(kind === "publication" ? "p" : prefixo, de, n), total)
  })
}

function deferido<T>() {
  let resolve!: (v: T) => void
  const promise = new Promise<T>(r => { resolve = r })
  return { promise, resolve }
}

const linhas = () => document.querySelectorAll("tbody tr").length
const verMais = () => screen.queryByRole("button", { name: /^(Ver mais|Carregando…)/ })
const aba = (nome: string) =>
  within(screen.getByRole("group", { name: "Tipo de artefato" })).getByRole("button", { name: nome })
const tique = () => act(async () => { await new Promise(r => setTimeout(r, 30)) })
const buscasDaPrimeiraPagina = () =>
  getArtifacts.mock.calls.filter(c => (c[0]?.kind ?? "execution") === "execution" && (c[0]?.offset ?? 0) === 0).length

function montar(cliente: QueryClient) {
  return render(<QueryClientProvider client={cliente}><ArtifactsPage /></QueryClientProvider>)
}

/** Lista com 50 de 120 e um "Ver mais" pendurado, que responde com `velho…`. */
async function comVerMaisEmVoo() {
  await waitFor(() => expect(linhas()).toBe(50))
  const pagina2 = deferido<Resposta>()
  getArtifacts.mockImplementationOnce(() => pagina2.promise)
  fireEvent.click(verMais()!)
  await waitFor(() => expect(verMais()).toHaveTextContent("Carregando…"))
  return () => pagina2.resolve(ok(itens("velho", 50, 50), 120))
}

beforeEach(() => {
  vi.clearAllMocks()
  getArtifacts.mockReset()
})

describe("Artefatos — Ver mais em voo e a saída da chave", () => {
  it("ida e volta de aba: a aba volta do zero e a página velha não entra", async () => {
    servidor("a")
    montar(criarClienteDeConsultas())
    const responderVelho = await comVerMaisEmVoo()

    servidor("n")
    const antes = buscasDaPrimeiraPagina()
    fireEvent.click(aba("Publicação"))
    await waitFor(() => expect(linhas()).toBe(3))
    fireEvent.click(aba("Execução"))

    await waitFor(() => expect(screen.getByLabelText("Selecionar n0.geojson")).toBeInTheDocument())
    expect(buscasDaPrimeiraPagina() - antes).toBe(1)
    expect(linhas()).toBe(50)

    responderVelho()
    await tique()
    expect(screen.queryByLabelText("Selecionar velho50.geojson")).toBeNull()
    expect(linhas()).toBe(50)
  })

  it("sair da tela e voltar com o provedor de pé: a tela volta do zero", async () => {
    const cliente = criarClienteDeConsultas()
    servidor("a")
    const primeira = montar(cliente)
    const responderVelho = await comVerMaisEmVoo()

    servidor("n")
    primeira.unmount()
    const antes = buscasDaPrimeiraPagina()
    montar(cliente)

    expect(screen.getByRole("status", { name: "Carregando os artefatos" })).toBeInTheDocument()
    await waitFor(() => expect(screen.getByLabelText("Selecionar n0.geojson")).toBeInTheDocument())
    expect(buscasDaPrimeiraPagina() - antes).toBe(1)

    responderVelho()
    await tique()
    expect(screen.queryByLabelText("Selecionar velho50.geojson")).toBeNull()
    expect(linhas()).toBe(50)
  })
})
