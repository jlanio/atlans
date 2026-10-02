import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"
import { INodesPropertyAPI } from "@/service/types"
import { INodeContext } from "@/context/useFlowContext"

/**
 * Regressão: num workspace compartilhado, o campo Credencial mostrava o
 * placeholder "Escolha a credencial" quando o nó estava configurado com a
 * credencial de OUTRO membro — como se estivesse vazio.
 *
 * A lista vem de GET /credentials/, que o backend filtra por owner_id, então a
 * credencial alheia nunca está nela e o Select não acha item para o value.
 */

// A store é lida com seletor: useWorkflowCatalogStore(s => s.credentials).
let storeCredentials: Array<{ id: string; name: string; type: string }> = []
vi.mock("@/app/stores/workflowCatalogStore", () => ({
  useWorkflowCatalogStore: (selector: (s: unknown) => unknown) =>
    selector({ credentials: storeCredentials, setCredentials: vi.fn() }),
}))

let canEdit = true
vi.mock("@/context/WorkspaceContext", () => ({
  useWorkspace: () => ({ canEdit }),
}))

vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: {
    getCredentialTypes: vi.fn().mockResolvedValue({
      data: [
        { type: "postgresql", label: "PostgreSQL", node_types: ["datasource"], fields: [] },
        { type: "webhook_token", label: "Token Webhook", node_types: ["output"], fields: [] },
      ],
    }),
    getCredentials: vi.fn().mockResolvedValue({ data: [] }),
  },
}))

vi.mock("@/utils/createToast", () => ({
  createToast: { error: vi.fn(), success: vi.fn(), info: vi.fn(), loading: vi.fn() },
}))

// O diálogo de criação arrasta a árvore de credenciais inteira — irrelevante aqui.
vi.mock("@/app/components/credentials/dialog-content/create-credential", () => ({
  default: () => null,
}))

import CredentialField from "@/app/components/workflow/nodes-configuration/fields/credential-field"

const MINHA = { id: "cred-minha", name: "pg-homolog", type: "postgresql" }
const OUTRO_TIPO = { id: "cred-token", name: "token-portal", type: "webhook_token" }
const ID_ALHEIA = "cred-de-outro-usuario"

function makeField(overrides: Partial<INodesPropertyAPI> = {}): INodesPropertyAPI {
  return {
    name: "credential_id",
    type: "string",
    default: "",
    description: "Credencial",
    credential_types: ["postgresql"],
    ...overrides,
  } as INodesPropertyAPI
}

function makeNode(): INodeContext {
  return {
    id: "n1",
    type: "DefaultIcon",
    position: { x: 0, y: 0 },
    data: { name: "DatabaseQuery", type: "datasource", properties: {} },
  } as unknown as INodeContext
}

function renderField(selectedId: string, field = makeField()) {
  return render(
    <CredentialField
      field={field}
      nodeFound={makeNode()}
      setNodeField={vi.fn()}
      values={{ credential_id: selectedId }}
      required
    />,
  )
}

beforeEach(() => {
  storeCredentials = [MINHA, OUTRO_TIPO]
  canEdit = true
})
afterEach(cleanup)

describe("CredentialField — credencial que não está na lista do usuário", () => {
  it("credencial de outro usuário não cai no placeholder", async () => {
    renderField(ID_ALHEIA)

    expect(await screen.findByText("Credencial de outro usuário")).toBeDefined()
    expect(screen.queryByText("Escolha a credencial")).toBeNull()
  })

  it("avisa que escolher a própria substitui para todos", async () => {
    renderField(ID_ALHEIA)

    expect(await screen.findByText(/substitui para todos/i)).toBeDefined()
  })

  it("não expõe nome nem tipo da credencial alheia", async () => {
    renderField(ID_ALHEIA)

    await screen.findByText("Credencial de outro usuário")
    expect(screen.queryByText(ID_ALHEIA)).toBeNull()
  })
})

describe("CredentialField — credencial do próprio usuário", () => {
  it("mostra o nome quando o tipo é aceito pelo nó", async () => {
    renderField(MINHA.id)

    expect(await screen.findByText("pg-homolog")).toBeDefined()
    expect(screen.queryByText("Credencial de outro usuário")).toBeNull()
  })

  it("tipo incompatível mostra o nome e sinaliza o problema", async () => {
    // token-portal é do usuário, mas o nó só aceita postgresql: fica fora de
    // `filtered` e antes também caía no placeholder.
    renderField(OUTRO_TIPO.id)

    expect(await screen.findByText("token-portal")).toBeDefined()
    expect(await screen.findByText(/tipo aceito por este nó/i)).toBeDefined()
    expect(screen.queryByText("Escolha a credencial")).toBeNull()
  })
})

describe("CredentialField — sem credencial", () => {
  it("alerta que é obrigatório e não inventa credencial", async () => {
    // O texto do placeholder é interno do Radix e não vira nó de texto em
    // jsdom; o que importa é não aparecer rótulo de credencial nenhuma.
    renderField("")

    expect(await screen.findByText(/requer uma credencial/i)).toBeDefined()
    expect(screen.queryByText("Credencial de outro usuário")).toBeNull()
    expect(screen.queryByText("pg-homolog")).toBeNull()
    expect(screen.queryByText(/substitui para todos/i)).toBeNull()
  })
})

describe("CredentialField — viewer (somente leitura)", () => {
  beforeEach(() => { canEdit = false })

  it("indica que há credencial configurada, em vez de 'Edição Indisponível'", async () => {
    renderField(ID_ALHEIA)

    expect(await screen.findByText("Credencial de outro usuário")).toBeDefined()
    expect(screen.queryByText("Edição Indisponível")).toBeNull()
  })

  it("distingue o nó sem credencial nenhuma", async () => {
    renderField("")

    expect(await screen.findByText("Nenhuma credencial configurada")).toBeDefined()
  })

  it("não atribui a restrição ao dono do workspace", async () => {
    renderField(MINHA.id)

    // O gate é `canEdit` (editor+), não posse do workspace.
    expect(await screen.findByText(/papel neste workspace/i)).toBeDefined()
    expect(screen.queryByText(/dono do workspace/i)).toBeNull()
  })
})
