import { describe, it, expect, beforeEach, vi } from "vitest"

// The service resolves (does not reject) on error: it returns { data: undefined, error }.
// That is exactly the shape the store needs to tell apart from "empty list".
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
    // Scenario: a user editing for more than 5 min presses Ctrl+K and the backend
    // returns 502. Before, `res?.data ?? []` stored an empty list and the drawer,
    // the palette and command-add-node went empty without any message.
    getNodes.mockReturnValueOnce(ok([{ name: "Postgres" }]))
    await catalogo().ensureNodesAPI()
    const bom = catalogo().nodesAPI
    expect(bom).toHaveLength(1)

    useWorkflowCatalogStore.setState({ nodesFetchedAt: null }) // forces the refetch
    getNodes.mockReturnValueOnce(falha())
    const devolvido = await catalogo().ensureNodesAPI()

    expect(devolvido).toBe(bom)
    expect(catalogo().nodesAPI).toBe(bom)
    // TTL not stamped: the next call tries again instead of serving the error.
    expect(catalogo().nodesFetchedAt).toBeNull()

    getNodes.mockReturnValueOnce(ok([{ name: "Postgres" }, { name: "HTTP" }]))
    await catalogo().ensureNodesAPI()
    expect(catalogo().nodesAPI).toHaveLength(2)
  })

  it("refetch com conteúdo idêntico mantém a MESMA referência do array", async () => {
    // Invariant that protects the canvas: the hydration effect subscribes to
    // nodesAPI, and a new reference with the same content redrew the graph over
    // the user's edits.
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

    // Creating/editing/deleting a credential in /credentials invalidates the stamp —
    // otherwise the new credential would only show up in the node's select after 5 min.
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
