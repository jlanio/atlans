/**
 * The refusal of an upload on the /drive screen: the label comes from the CODE the server
 * sends (`error` in the body), never from a piece of the sentence.
 *
 * The old classification looked for "extensão"/"não permitida" in the text, and the
 * backend writes "Extensao '.pdf' nao permitida." (without accents): the extension
 * refusal showed up as "Falha no envio" (upload failed), with the generic error icon.
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
    // The response as the backend sends it: 422, the code and the sentence without accents.
    servico.uploadDriveFile.mockResolvedValue({
      status: 422, success: false,
      error: { name: "AxiosError", message: "Extensao '.pdf' nao permitida.", code: "extension_not_allowed" },
    })

    await enviar("relatorio.pdf")

    expect(await screen.findByText("Extensão não permitida")).toBeInTheDocument()
    expect(screen.queryByText("Falha no envio")).toBeNull()
    // The server's sentence is still the detail the person reads.
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
