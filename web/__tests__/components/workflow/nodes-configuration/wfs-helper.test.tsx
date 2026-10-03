import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"

/**
 * The WFS node's layer picker lists with the node's credential: a GeoServer
 * hides protected layers from anonymous users, and the anonymous list swapped
 * the text field for a dropdown without them — the protected layer became unreachable.
 */
const http = vi.hoisted(() => ({ get: vi.fn() }))
vi.mock("axios", () => {
  class AxiosError extends Error {
    response?: { data?: unknown }
  }
  const isAxiosError = (e: unknown) => e instanceof AxiosError
  return { default: { get: http.get, isAxiosError }, AxiosError, isAxiosError }
})
import { AxiosError } from "axios"
import WFSHelper from "@/app/components/workflow/nodes-configuration/wfs-helper"

type Valores = Record<string, string | number | boolean>

const URL_WFS = "https://geo.exemplo.gov.br/geoserver/ows"
const CAMADAS = [
  { name: "ns:publica", title: "Pública" },
  { name: "ns:protegida", title: "Protegida" },
]

// `{}` mounts without a workflow (a not-yet-saved workflow); the default is workflow "wf1".
function montar(valores: Valores, { workflowId }: { workflowId?: string } = { workflowId: "wf1" }) {
  const setNodeField = vi.fn()
  const r = render(<WFSHelper values={valores} setNodeField={setNodeField} workflowId={workflowId} />)
  return { ...r, setNodeField }
}

function buscar() {
  fireEvent.click(screen.getByTitle("Buscar camadas disponíveis"))
}

beforeEach(() => {
  http.get.mockReset()
  http.get.mockResolvedValue({ data: { layers: CAMADAS } })
})
afterEach(cleanup)

describe("WFSHelper — a credencial do nó na listagem", () => {
  it("sem credencial, pede só a URL", async () => {
    montar({ url: URL_WFS, typeName: "" })
    buscar()
    await waitFor(() => expect(http.get).toHaveBeenCalledTimes(1))
    expect(http.get.mock.calls[0][1]).toEqual({ params: { url: URL_WFS } })
    expect(await screen.findByText("2 camada(s) encontrada(s)")).toBeTruthy()
  })

  it("com credencial, manda o id dela e o fluxo em edição", async () => {
    montar({ url: URL_WFS, typeName: "", credential_id: "cred-1" })
    buscar()
    await waitFor(() => expect(http.get).toHaveBeenCalledTimes(1))
    expect(http.get.mock.calls[0][1]).toEqual({
      params: { url: URL_WFS, credential_id: "cred-1", workflow_id: "wf1" },
    })
    expect(await screen.findByText("2 camada(s) encontrada(s) com a credencial do nó")).toBeTruthy()
  })

  it("num fluxo ainda não salvo, vai só a credencial (o alcance é o de quem pede)", async () => {
    montar({ url: URL_WFS, typeName: "", credential_id: "cred-1" }, {})
    buscar()
    await waitFor(() => expect(http.get).toHaveBeenCalledTimes(1))
    expect(http.get.mock.calls[0][1]).toEqual({ params: { url: URL_WFS, credential_id: "cred-1" } })
  })

  it("trocada a credencial, a lista deixa de valer e o campo de texto volta", async () => {
    const { rerender, setNodeField } = montar({ url: URL_WFS, typeName: "ns:protegida", credential_id: "cred-1" })
    buscar()
    expect(await screen.findByRole("combobox")).toBeTruthy()

    rerender(<WFSHelper values={{ url: URL_WFS, typeName: "ns:protegida", credential_id: "" }} setNodeField={setNodeField} workflowId="wf1" />)
    expect(screen.queryByRole("combobox")).toBeNull()
    expect((screen.getByPlaceholderText("namespace:camada") as HTMLInputElement).value).toBe("ns:protegida")
    expect(screen.getByText(/A credencial do nó mudou/)).toBeTruthy()
  })

  it("buscar de novo com a credencial nova e falhar deixa só o erro, sem o aviso de 'mudou'", async () => {
    const { rerender, setNodeField } = montar({ url: URL_WFS, typeName: "", credential_id: "cred-1" })
    buscar()
    expect(await screen.findByRole("combobox")).toBeTruthy()

    rerender(<WFSHelper values={{ url: URL_WFS, typeName: "", credential_id: "cred-2" }} setNodeField={setNodeField} workflowId="wf1" />)
    expect(screen.getByText(/A credencial do nó mudou/)).toBeTruthy()

    const erro = Object.assign(new AxiosError("Request failed with status code 403"), {
      response: { data: { message: "A credencial deste nó não está ao seu alcance." } },
    })
    http.get.mockRejectedValue(erro)
    buscar()
    expect(await screen.findByText("A credencial deste nó não está ao seu alcance.")).toBeTruthy()
    expect(screen.queryByText(/A credencial do nó mudou/)).toBeNull()
  })

  it("a camada gravada fora da lista continua à vista no dropdown", async () => {
    montar({ url: URL_WFS, typeName: "ns:so_com_outra_chave" })
    buscar()
    const combo = await screen.findByRole("combobox")
    expect(combo.textContent).toContain("ns:so_com_outra_chave")
  })

  it("mostra a mensagem da API (o corpo de erro é `{message}`)", async () => {
    const erro = Object.assign(new AxiosError("Request failed with status code 403"), {
      response: { data: { message: "A credencial deste nó não está ao seu alcance." } },
    })
    http.get.mockRejectedValue(erro)
    montar({ url: URL_WFS, typeName: "", credential_id: "cred-alheia" })
    buscar()
    expect(await screen.findByText("A credencial deste nó não está ao seu alcance.")).toBeTruthy()
    // No list: the text field remains available.
    expect(screen.getByPlaceholderText("namespace:camada")).toBeTruthy()
  })
})
