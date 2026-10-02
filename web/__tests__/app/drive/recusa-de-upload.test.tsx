/**
 * A recusa de um upload na tela /drive: o rótulo sai do CÓDIGO que o servidor
 * manda (`error` do corpo), nunca de um trecho da frase.
 *
 * A classificação antiga procurava "extensão"/"não permitida" no texto, e o
 * backend escreve "Extensao '.pdf' nao permitida." (sem acento): a recusa por
 * extensão aparecia como «Falha no envio», com o ícone de erro genérico.
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, cleanup } from "@testing-library/react"

vi.mock("next-auth/react", () => ({ useSession: () => ({ data: { user: { access_token: "t" } }, status: "authenticated" }) }))

const servico = vi.hoisted(() => ({ getDriveFiles: vi.fn(), uploadDriveFile: vi.fn() }))
vi.mock("@/service/GisFlowService", () => ({ GisFlowService: servico }))

vi.mock("@/context/WorkspaceContext", () => ({
  useWorkspace: () => ({ current: { id_hash: "ws-a", name: "A" }, canEdit: true }),
}))

import DrivePage from "@/app/(dashboard)/drive/page"

beforeEach(() => {
  cleanup()
  servico.getDriveFiles.mockReset()
  servico.uploadDriveFile.mockReset()
  servico.getDriveFiles.mockResolvedValue({ status: 200, success: true, data: { items: [], total: 0 } })
})

async function enviar(nome: string) {
  const { container } = render(<DrivePage />)
  const campo = container.querySelector<HTMLInputElement>('input[type="file"]')
  expect(campo).not.toBeNull()
  fireEvent.change(campo!, { target: { files: [new File(["x"], nome)] } })
}

describe("Drive — o rótulo da recusa", () => {
  it("a recusa por extensão cai na categoria de extensão", async () => {
    // A resposta como o backend a manda: 422, o código e a frase sem acento.
    servico.uploadDriveFile.mockResolvedValue({
      status: 422, success: false,
      error: { name: "AxiosError", message: "Extensao '.pdf' nao permitida.", code: "extension_not_allowed" },
    })

    await enviar("relatorio.pdf")

    expect(await screen.findByText("Extensão não permitida")).toBeInTheDocument()
    expect(screen.queryByText("Falha no envio")).toBeNull()
    // A frase do servidor continua sendo o detalhe que a pessoa lê.
    expect(screen.getByText("Extensao '.pdf' nao permitida.")).toBeInTheDocument()
  })

  it("arquivo vazio tem o rótulo de vazio", async () => {
    servico.uploadDriveFile.mockResolvedValue({
      status: 422, success: false,
      error: { name: "AxiosError", message: "Arquivo vazio.", code: "empty_file" },
    })

    await enviar("dados.csv")

    expect(await screen.findByText("Arquivo vazio")).toBeInTheDocument()
  })
})
