import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, cleanup, waitFor, fireEvent } from "@testing-library/react"

/**
 * Behavior of the credentials LIST (/credentials):
 * - edit/delete/duplicate actions are owner-only — someone who only received the
 *   shared credential does not see the menu (the backend would refuse anyway,
 *   but letting the click fail with a 403 would be terrible UX);
 * - "Compartilhada" / "Compartilhada comigo" badge;
 * - search filters the list;
 * - the usage warning on deletion is a discreet line, not an alert panel.
 */

const getCredentials = vi.fn()
const getCredentialTypes = vi.fn()
const getCredentialsUsage = vi.fn()
const getCredentialData = vi.fn()
const deleteCredentialById = vi.fn()

vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: {
    getCredentials: (...a: unknown[]) => getCredentials(...a),
    getCredentialTypes: (...a: unknown[]) => getCredentialTypes(...a),
    getCredentialsUsage: (...a: unknown[]) => getCredentialsUsage(...a),
    getCredentialData: (...a: unknown[]) => getCredentialData(...a),
    deleteCredentialById: (...a: unknown[]) => deleteCredentialById(...a),
  },
}))

vi.mock("@/utils/createToast", () => ({
  createToast: { error: vi.fn(), success: vi.fn(), info: vi.fn(), loading: vi.fn() },
}))

vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: { user: { id_hash: "me" } }, status: "authenticated" }),
}))

vi.mock("@/context/WorkspaceContext", () => ({
  useWorkspace: () => ({ current: { id_hash: "ws1", name: "Meu WS" } }),
}))

// A credentials context real enough: the index reads `credentials` from here.
const CREDS = [
  { id: "c1", name: "pg minha",     type: "postgresql",  owner_id: "me",    workspace_id: null,  created_at: "2026-01-01T00:00:00", updated_at: "2026-01-01T00:00:00" },
  { id: "c2", name: "api de fulano", type: "http_bearer", owner_id: "outro", workspace_id: "ws1", created_at: "2026-01-02T00:00:00", updated_at: "2026-01-02T00:00:00" },
  { id: "c3", name: "s3 compartilhada", type: "s3",       owner_id: "me",    workspace_id: "ws1", created_at: "2026-01-03T00:00:00", updated_at: "2026-01-03T00:00:00" },
]

vi.mock("@/context/useCredentialsContext", () => ({
  useCredentialsContext: () => ({ credentials: CREDS, setCredentialsContext: vi.fn() }),
}))

const TYPES = [
  { type: "postgresql", label: "PostgreSQL / PostGIS", description: "", node_types: [], fields: [] },
  { type: "http_bearer", label: "HTTP Bearer Token", description: "", node_types: [], fields: [] },
  { type: "s3", label: "Amazon S3", description: "", node_types: [], fields: [] },
]

import CredentialsActions from "@/app/components/credentials/index"
import { Dialog } from "@/app/components/ui/dialog"
import DeleteCredential from "@/app/components/credentials/dialog-content/delete-credential"

beforeEach(() => {
  vi.clearAllMocks()
  getCredentials.mockResolvedValue({ data: CREDS })
  getCredentialTypes.mockResolvedValue({ data: TYPES })
  getCredentialsUsage.mockResolvedValue({ data: { c1: { node_count: 2, workflow_count: 1 } } })
})

afterEach(() => cleanup())

async function renderList() {
  render(<CredentialsActions />)
  // waits to leave the skeleton
  await screen.findByText("pg minha")
}

describe("Lista de credenciais — ações owner-only", () => {
  it("mostra o menu de ações só nas credenciais do próprio usuário", async () => {
    await renderList()
    // Own (c1) and own-shared (c3): have a menu.
    expect(screen.getByRole("button", { name: /ações da credencial pg minha/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /ações da credencial s3 compartilhada/i })).toBeInTheDocument()
    // Shared by someone else (c2): does NOT have a menu.
    expect(screen.queryByRole("button", { name: /ações da credencial api de fulano/i })).toBeNull()
  })

  it("marca a compartilhada-comigo e a compartilhada-por-mim", async () => {
    await renderList()
    // c2 is someone else's, shared with me
    expect(screen.getByText("Compartilhada comigo")).toBeInTheDocument()
    // c3 is mine, shared with the workspace
    expect(screen.getByText("Compartilhada")).toBeInTheDocument()
  })
})

describe("Lista de credenciais — busca", () => {
  it("filtra pelos termos digitados", async () => {
    await renderList()
    const busca = screen.getByRole("textbox", { name: /buscar credenciais/i })
    fireEvent.change(busca, { target: { value: "fulano" } })
    await waitFor(() => {
      expect(screen.getByText("api de fulano")).toBeInTheDocument()
      expect(screen.queryByText("pg minha")).toBeNull()
      expect(screen.queryByText("s3 compartilhada")).toBeNull()
    })
  })

  it("oferece limpar filtros quando nada corresponde", async () => {
    await renderList()
    const busca = screen.getByRole("textbox", { name: /buscar credenciais/i })
    fireEvent.change(busca, { target: { value: "zzz-nao-existe" } })
    const limpar = await screen.findByRole("button", { name: /limpar filtros/i })
    fireEvent.click(limpar)
    await waitFor(() => expect(screen.getByText("pg minha")).toBeInTheDocument())
  })
})

describe("Exclusão — aviso de uso discreto (não gritante)", () => {
  it("mostra uma linha de aviso quando a credencial está em uso", async () => {
    render(
      <Dialog open>
        <DeleteCredential deleteCredentialId="c1" setDeleteCredentialId={vi.fn()} usageCount={2} />
      </Dialog>,
    )
    const aviso = await screen.findByText(/em uso em 2 nós de workflow/i)
    expect(aviso).toBeInTheDocument()
    // Discreet: a muted line, NOT a panel with role=alert.
    expect(aviso.tagName.toLowerCase()).toBe("p")
    expect(aviso.getAttribute("role")).not.toBe("alert")
  })

  it("não mostra aviso quando a credencial não está em uso", async () => {
    render(
      <Dialog open>
        <DeleteCredential deleteCredentialId="c1" setDeleteCredentialId={vi.fn()} usageCount={0} />
      </Dialog>,
    )
    await screen.findByText(/excluir credencial/i)
    expect(screen.queryByText(/em uso em/i)).toBeNull()
  })
})
