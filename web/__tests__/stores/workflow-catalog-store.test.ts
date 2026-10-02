import { describe, it, expect, beforeEach, vi } from "vitest"

// O service resolve (não rejeita) em erro: devolve { data: undefined, error }.
// É exatamente esse formato que a store precisa distinguir de "lista vazia".
const getNodes = vi.fn()
const getCredentials = vi.fn()

vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: {
    getNodes: () => getNodes(),
    getCredentials: () => getCredentials(),
  },
}))

import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore"

const ok = <T,>(data: T) => Promise.resolve({ status: 200, success: true, data })
const falha = () =>
  Promise.resolve({ status: 502, success: false, error: { name: "AxiosError", message: "boom" } })

const catalogo = () => useWorkflowCatalogStore.getState()

describe("workflowCatalogStore — catálogo em memória com TTL", () => {
  beforeEach(() => {
    getNodes.mockReset()
    getCredentials.mockReset()
    useWorkflowCatalogStore.setState({
      nodesAPI: [],
      credentials: [],
      nodesFetchedAt: null,
      credentialsFetchedAt: null,
    })
  })

  it("falha de rede preserva o catálogo bom e não carimba o TTL", async () => {
    // Cenário: usuário editando há mais de 5 min aperta Ctrl+K e o backend
    // devolve 502. Antes, `res?.data ?? []` gravava lista vazia e o drawer, a
    // paleta e o command-add-node ficavam vazios sem nenhuma mensagem.
    getNodes.mockReturnValueOnce(ok([{ name: "Postgres" }]))
    await catalogo().ensureNodesAPI()
    const bom = catalogo().nodesAPI
    expect(bom).toHaveLength(1)

    useWorkflowCatalogStore.setState({ nodesFetchedAt: null }) // força o refetch
    getNodes.mockReturnValueOnce(falha())
    const devolvido = await catalogo().ensureNodesAPI()

    expect(devolvido).toBe(bom)
    expect(catalogo().nodesAPI).toBe(bom)
    // TTL não carimbado: a próxima chamada tenta de novo em vez de servir o erro.
    expect(catalogo().nodesFetchedAt).toBeNull()

    getNodes.mockReturnValueOnce(ok([{ name: "Postgres" }, { name: "HTTP" }]))
    await catalogo().ensureNodesAPI()
    expect(catalogo().nodesAPI).toHaveLength(2)
  })

  it("refetch com conteúdo idêntico mantém a MESMA referência do array", async () => {
    // Invariante que protege o canvas: o efeito de hidratação assina nodesAPI, e
    // uma referência nova com o mesmo conteúdo redesenhava o grafo por cima das
    // edições do usuário.
    getNodes.mockReturnValueOnce(ok([{ name: "Postgres" }]))
    await catalogo().ensureNodesAPI()
    const antes = catalogo().nodesAPI

    useWorkflowCatalogStore.setState({ nodesFetchedAt: null })
    getNodes.mockReturnValueOnce(ok([{ name: "Postgres" }]))
    await catalogo().ensureNodesAPI()

    expect(catalogo().nodesAPI).toBe(antes)
    expect(catalogo().nodesFetchedAt).not.toBeNull()
  })

  it("conteúdo diferente troca a referência", async () => {
    getNodes.mockReturnValueOnce(ok([{ name: "Postgres" }]))
    await catalogo().ensureNodesAPI()
    const antes = catalogo().nodesAPI

    useWorkflowCatalogStore.setState({ nodesFetchedAt: null })
    getNodes.mockReturnValueOnce(ok([{ name: "Postgres" }, { name: "HTTP" }]))
    await catalogo().ensureNodesAPI()

    expect(catalogo().nodesAPI).not.toBe(antes)
    expect(catalogo().nodesAPI).toHaveLength(2)
  })

  it("dentro do TTL não refaz o GET; invalidarCredenciais força a próxima busca", async () => {
    getCredentials.mockReturnValueOnce(ok([{ id: "1", name: "Postgres Dev", type: "postgresql" }]))
    await catalogo().ensureCredentials()
    expect(getCredentials).toHaveBeenCalledTimes(1)

    await catalogo().ensureCredentials()
    expect(getCredentials).toHaveBeenCalledTimes(1)

    // Criar/editar/excluir credencial em /credentials invalida o carimbo — senão
    // a credencial nova só apareceria no select do nó depois de 5 min.
    catalogo().invalidarCredenciais()
    getCredentials.mockReturnValueOnce(ok([
      { id: "1", name: "Postgres Dev", type: "postgresql" },
      { id: "2", name: "Postgres Prod", type: "postgresql" },
    ]))
    await catalogo().ensureCredentials()
    expect(getCredentials).toHaveBeenCalledTimes(2)
    expect(catalogo().credentials).toHaveLength(2)
  })

  it("falha em ensureCredentials preserva a lista boa", async () => {
    getCredentials.mockReturnValueOnce(ok([{ id: "1", name: "Postgres Dev", type: "postgresql" }]))
    await catalogo().ensureCredentials()
    const bom = catalogo().credentials

    catalogo().invalidarCredenciais()
    getCredentials.mockReturnValueOnce(falha())
    await catalogo().ensureCredentials()

    expect(catalogo().credentials).toBe(bom)
    expect(catalogo().credentialsFetchedAt).toBeNull()
  })
})
