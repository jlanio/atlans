import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import type { ApiToken, ApiTokenCreated, IWorkspace } from "@/service/types"

/**
 * Token dialogs: create (2 steps) and revoke.
 *
 * The most delicate point is step 2: the secret appears ONCE, has to be
 * copyable, and the connection snippets must NEVER embed the real secret —
 * they carry `${ATLANS_TOKEN}`, so that pasting a command into a chat doesn't leak the token.
 */

const svc = vi.hoisted(() => ({
  createApiToken: vi.fn(),
  revokeApiToken: vi.fn(),
}))
vi.mock("@/service/GisFlowService", () => ({ GisFlowService: svc }))

vi.mock("@/utils/createToast", () => ({
  createToast: { error: vi.fn(), success: vi.fn(), info: vi.fn(), loading: vi.fn(), warning: vi.fn() },
}))

import { createToast } from "@/utils/createToast"
import { Dialog } from "@/app/components/ui/dialog"
import CreateToken, { CLIENTES, DOCS_MCP, URL_DO_MCP, snippetCom, urlDoMcp } from "@/app/components/tokens/dialog-content/create-token"
import RevokeToken from "@/app/components/tokens/dialog-content/revoke-token"

const ok = <T,>(data: T) => ({ success: true, status: 200, data })
const falhou = (message: string, status = 500) => ({ success: false, status, error: { name: "AxiosError", message } })

// Synthetic secret, in a single place, so detect-secrets doesn't flag the fixture.
const SEGREDO_FAKE = "atl_teste_0000000000000000000000000000" // pragma: allowlist secret

const WORKSPACES: IWorkspace[] = [
  { id_hash: "ws-1", name: "Bacia", description: null, owner_id: "me", is_default: true, my_role: "owner" },
  { id_hash: "ws-2", name: "Cadastro", description: null, owner_id: "me", is_default: false, my_role: "editor" },
]

const TOKEN: ApiToken = {
  id: "t1", name: "agente", token_prefix: "atl_ab12cd", scopes: ["workflows:read"], workspace_ids: null,
  expires_at: "2027-01-01T00:00:00", last_used_at: null, revoked_at: null, created_at: "2026-09-01T00:00:00", status: "active",
}
const CRIADO: ApiTokenCreated = { ...TOKEN, token: SEGREDO_FAKE }

let writeText: ReturnType<typeof vi.fn>

function clipboard(valor: unknown) {
  Object.defineProperty(navigator, "clipboard", { value: valor, configurable: true, writable: true })
}

beforeEach(() => {
  vi.clearAllMocks()
  writeText = vi.fn().mockResolvedValue(undefined)
  clipboard({ writeText })
  svc.createApiToken.mockResolvedValue(ok(CRIADO))
})
afterEach(cleanup)

function renderCriar(workspaces: IWorkspace[] = WORKSPACES) {
  const onCreated = vi.fn()
  const onClose = vi.fn()
  render(
    <Dialog open>
      <CreateToken workspaces={workspaces} onCreated={onCreated} onClose={onClose} />
    </Dialog>,
  )
  return { onCreated, onClose, dialogo: screen.getByRole("dialog") }
}

const escopo = (dialogo: HTMLElement, rotulo: string) => within(dialogo).getByRole("button", { name: new RegExp(`^${rotulo}`) })
const criar = (dialogo: HTMLElement) => fireEvent.click(within(dialogo).getByRole("button", { name: "Criar token" }))
const nomear = (dialogo: HTMLElement, nome: string) => fireEvent.change(within(dialogo).getByLabelText("Nome"), { target: { value: nome } })

/** Cria com nome e um escopo, e espera o passo 2. */
async function criarBasico(dialogo: HTMLElement) {
  nomear(dialogo, "Agente")
  fireEvent.click(escopo(dialogo, "Ler fluxos"))
  criar(dialogo)
  return await within(dialogo).findByLabelText("Segredo do token")
}

describe("CreateToken — passo 1 (formulário)", () => {
  it("valida nome e escopo antes de chamar a API", async () => {
    const { dialogo } = renderCriar()
    criar(dialogo)
    expect(await within(dialogo).findByText("O nome do token é obrigatório")).toBeInTheDocument()
    expect(within(dialogo).getByText("Escolha pelo menos um escopo")).toBeInTheDocument()
    expect(svc.createApiToken).not.toHaveBeenCalled()
  })

  it("envia o payload certo: nome aparado, escopos na ordem canônica, workspaces todos marcados, 90 dias", async () => {
    const { dialogo, onCreated } = renderCriar()
    nomear(dialogo, "  Agente de relatórios  ")
    // Clicks out of order on purpose: the payload comes out in canonical order.
    const executar = escopo(dialogo, "Executar fluxos")
    fireEvent.click(executar)
    fireEvent.click(escopo(dialogo, "Ler fluxos"))
    expect(executar).toHaveAttribute("aria-pressed", "true")
    // The workspace checkboxes all start checked.
    expect(within(dialogo).getByRole("checkbox", { name: "Bacia" })).toHaveAttribute("aria-checked", "true")
    expect(within(dialogo).getByRole("checkbox", { name: "Cadastro" })).toHaveAttribute("aria-checked", "true")

    criar(dialogo)
    await waitFor(() => expect(svc.createApiToken).toHaveBeenCalledWith({
      name: "Agente de relatórios",
      scopes: ["workflows:read", "runs:execute"],
      workspace_ids: ["ws-1", "ws-2"],
      expires_in_days: 90,
    }))
    await waitFor(() => expect(onCreated).toHaveBeenCalledWith(CRIADO))
    expect(createToast.success).toHaveBeenCalledWith("Token criado", "agente")
  })

  it("«Somente leitura» marca só ler fluxos e ler o Drive", async () => {
    const { dialogo } = renderCriar()
    fireEvent.click(escopo(dialogo, "Executar fluxos"))
    fireEvent.click(within(dialogo).getByRole("button", { name: "Somente leitura" }))
    expect(escopo(dialogo, "Ler fluxos")).toHaveAttribute("aria-pressed", "true")
    expect(escopo(dialogo, "Ler o Drive")).toHaveAttribute("aria-pressed", "true")
    expect(escopo(dialogo, "Executar fluxos")).toHaveAttribute("aria-pressed", "false")
    expect(escopo(dialogo, "Criar e editar fluxos")).toHaveAttribute("aria-pressed", "false")

    nomear(dialogo, "Leitor")
    criar(dialogo)
    await waitFor(() => expect(svc.createApiToken).toHaveBeenCalledWith(expect.objectContaining({
      scopes: ["workflows:read", "drive:read"],
    })))
  })

  it("«Todos os workspaces» desabilita a lista e envia null", async () => {
    const { dialogo } = renderCriar()
    fireEvent.click(within(dialogo).getByRole("checkbox", { name: /todos os workspaces, inclusive os que eu entrar depois/i }))
    expect(within(dialogo).getByRole("checkbox", { name: "Bacia" })).toBeDisabled()
    expect(within(dialogo).getByRole("checkbox", { name: "Cadastro" })).toBeDisabled()

    nomear(dialogo, "Agente")
    fireEvent.click(escopo(dialogo, "Ler fluxos"))
    criar(dialogo)
    await waitFor(() => expect(svc.createApiToken).toHaveBeenCalledWith(expect.objectContaining({ workspace_ids: null })))
  })

  it("desmarcar um workspace tira-o do payload; desmarcar todos bloqueia o envio", async () => {
    const { dialogo } = renderCriar()
    nomear(dialogo, "Agente")
    fireEvent.click(escopo(dialogo, "Ler fluxos"))
    fireEvent.click(within(dialogo).getByRole("checkbox", { name: "Bacia" }))
    criar(dialogo)
    await waitFor(() => expect(svc.createApiToken).toHaveBeenCalledWith(expect.objectContaining({ workspace_ids: ["ws-2"] })))
  })

  it("sem nenhum workspace marcado (e sem «Todos»), não envia e explica", async () => {
    const { dialogo } = renderCriar()
    nomear(dialogo, "Agente")
    fireEvent.click(escopo(dialogo, "Ler fluxos"))
    fireEvent.click(within(dialogo).getByRole("checkbox", { name: "Bacia" }))
    fireEvent.click(within(dialogo).getByRole("checkbox", { name: "Cadastro" }))
    criar(dialogo)
    expect(await within(dialogo).findByText(/escolha pelo menos um workspace/i)).toBeInTheDocument()
    expect(svc.createApiToken).not.toHaveBeenCalled()
  })

  it("sem workspaces carregados, orienta a marcar «Todos»", () => {
    const { dialogo } = renderCriar([])
    expect(within(dialogo).getByText(/nenhum workspace carregado/i)).toBeInTheDocument()
    expect(within(dialogo).queryByRole("list", { name: "Workspaces do token" })).toBeNull()
  })

  it("erro da API (409 no teto) mantém o passo 1 e mostra a mensagem do backend", async () => {
    svc.createApiToken.mockResolvedValue(falhou("Você já tem 20 tokens ativos", 409))
    const { dialogo, onCreated } = renderCriar()
    nomear(dialogo, "Agente")
    fireEvent.click(escopo(dialogo, "Ler fluxos"))
    criar(dialogo)
    await waitFor(() => expect(createToast.error).toHaveBeenCalledWith("Não foi possível criar o token", "Você já tem 20 tokens ativos"))
    expect(within(dialogo).getByRole("button", { name: "Criar token" })).toBeInTheDocument()
    expect(within(dialogo).queryByLabelText("Segredo do token")).toBeNull()
    expect(onCreated).not.toHaveBeenCalled()
  })
})

describe("CreateToken — passo 2 (segredo e conexão)", () => {
  it("mostra o segredo uma vez, avisa, copia pela área de transferência e «Concluir» fecha", async () => {
    const { dialogo, onClose } = renderCriar()
    const segredo = await criarBasico(dialogo)
    expect(segredo).toHaveTextContent(SEGREDO_FAKE)
    expect(within(dialogo).getByText("Token criado")).toBeInTheDocument()
    expect(within(dialogo).getByText("Este segredo não será mostrado de novo. Guarde-o agora.")).toBeInTheDocument()

    const copiar = within(dialogo).getByRole("button", { name: "Copiar" })
    fireEvent.click(copiar)
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(SEGREDO_FAKE))
    expect(await within(dialogo).findByRole("button", { name: "Copiado" })).toBeInTheDocument()

    fireEvent.click(within(dialogo).getByRole("button", { name: "Concluir" }))
    expect(onClose).toHaveBeenCalled()
  })

  it("sem navigator.clipboard, avisa em vez de falhar em silêncio", async () => {
    clipboard(undefined)
    const { dialogo } = renderCriar()
    await criarBasico(dialogo)
    fireEvent.click(within(dialogo).getByRole("button", { name: "Copiar" }))
    const aviso = await within(dialogo).findByRole("alert")
    expect(aviso).toHaveTextContent(/não foi possível copiar automaticamente/i)
    expect(within(dialogo).queryByRole("button", { name: "Copiado" })).toBeNull()
  })

  it("no desenvolvimento, o MCP é o da porta da API, que o next dev não repassa", () => {
    vi.stubEnv("NEXT_PUBLIC_API_PORT", "8000")
    try {
      expect(urlDoMcp()).toBe(`${window.location.protocol}//${window.location.hostname}:8000/mcp`)
    } finally {
      vi.unstubAllEnvs()
    }
  })

  it("os snippets trocam com o toggle, apontam para o MCP desta instalação e nunca embutem o segredo", async () => {
    const { dialogo } = renderCriar()
    await criarBasico(dialogo)
    const grupo = within(dialogo).getByRole("group", { name: "Cliente MCP" })
    const snippet = () => dialogo.querySelector("pre")!.textContent ?? ""
    // The address is that of the open page, not one hard-coded.
    const mcp = `${window.location.origin}/mcp`
    expect(urlDoMcp()).toBe(mcp)

    // Claude Code is the default.
    expect(within(grupo).getByRole("button", { name: "Claude Code" })).toHaveAttribute("aria-pressed", "true")
    expect(snippet()).toBe(`claude mcp add --transport http atlans ${mcp} --header "Authorization: Bearer \${ATLANS_TOKEN}"`)

    fireEvent.click(within(grupo).getByRole("button", { name: "Cursor, VS Code e Windsurf" }))
    expect(JSON.parse(snippet())).toEqual({
      mcpServers: { atlans: { url: mcp, headers: { Authorization: "Bearer ${ATLANS_TOKEN}" } } },
    })

    fireEvent.click(within(grupo).getByRole("button", { name: "mcp-remote" }))
    expect(snippet()).toBe(`npx mcp-remote ${mcp} --header "Authorization:\${AUTH_HEADER}"`)
    expect(within(dialogo).getByText(/defina AUTH_HEADER="Bearer …" no ambiente/i)).toBeInTheDocument()

    // None of the three carries the real secret; all point to the same server.
    for (const c of CLIENTES) {
      expect(c.snippet).not.toContain(SEGREDO_FAKE)
      expect(c.snippet).toContain(URL_DO_MCP)
    }
    // The server is already up: the footer says to connect and points to the docs.
    expect(dialogo).toHaveTextContent(`Conecte pelo comando acima. Limites e detalhes em ${DOCS_MCP}.`)

    // Copying the command copies the snippet with this installation's address, not the secret.
    fireEvent.click(within(dialogo).getByRole("button", { name: "Copiar comando" }))
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(snippetCom(CLIENTES[2].snippet, mcp)))
  })
})

describe("RevokeToken", () => {
  function renderRevogar() {
    const onRevoked = vi.fn()
    const onClose = vi.fn()
    render(
      <Dialog open>
        <RevokeToken token={TOKEN} onRevoked={onRevoked} onClose={onClose} />
      </Dialog>,
    )
    return { onRevoked, onClose, dialogo: screen.getByRole("dialog") }
  }

  it("diz o que acontece, usa o verbo certo e devolve o token revogado", async () => {
    const revogado: ApiToken = { ...TOKEN, status: "revoked", revoked_at: "2026-09-13T12:00:00" }
    svc.revokeApiToken.mockResolvedValue(ok(revogado))
    const { dialogo, onRevoked, onClose } = renderRevogar()
    expect(dialogo).toHaveTextContent("Revogar o token «agente»")
    expect(dialogo).toHaveTextContent("Agentes que usam «agente» param de funcionar na hora.")
    expect(within(dialogo).queryByRole("button", { name: /excluir/i })).toBeNull()

    fireEvent.click(within(dialogo).getByRole("button", { name: "Revogar" }))
    await waitFor(() => expect(svc.revokeApiToken).toHaveBeenCalledWith("t1"))
    await waitFor(() => expect(onRevoked).toHaveBeenCalledWith(revogado))
    expect(onClose).toHaveBeenCalled()
    expect(createToast.success).toHaveBeenCalledWith("Token revogado", "agente")
  })

  it("com corpo vazio no 200, marca como revogado localmente", async () => {
    svc.revokeApiToken.mockResolvedValue(ok(undefined))
    const { dialogo, onRevoked } = renderRevogar()
    fireEvent.click(within(dialogo).getByRole("button", { name: "Revogar" }))
    await waitFor(() => expect(onRevoked).toHaveBeenCalled())
    const enviado = onRevoked.mock.calls[0][0] as ApiToken
    expect(enviado.status).toBe("revoked")
    expect(enviado.revoked_at).toBeTruthy()
  })

  it("falha avisa, não fecha e não mexe na lista", async () => {
    svc.revokeApiToken.mockResolvedValue(falhou("token não encontrado", 404))
    const { dialogo, onRevoked, onClose } = renderRevogar()
    fireEvent.click(within(dialogo).getByRole("button", { name: "Revogar" }))
    await waitFor(() => expect(createToast.error).toHaveBeenCalledWith("Não foi possível revogar o token", "token não encontrado"))
    expect(onRevoked).not.toHaveBeenCalled()
    expect(onClose).not.toHaveBeenCalled()
    // The button works again after the failure.
    await waitFor(() => expect(within(dialogo).getByRole("button", { name: "Revogar" })).not.toBeDisabled())
  })
})
