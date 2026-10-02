import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import type { ApiToken, ApiTokenCreated, IWorkspace } from "@/service/types"

/**
 * Comportamento da LISTA de tokens de acesso (/settings/tokens):
 * - precedência dos estados: skeleton → erro (só na 1ª carga) → primeiro uso → lista;
 * - selos sempre traduzidos, com o aviso «Expira em N dias» perto do fim;
 * - escopos como chips, workspaces com nomes resolvidos, último uso e criação;
 * - revogar troca a linha no lugar (o token continua, como «Revogado»);
 * - criar pelo cabeçalho põe o token novo no topo, sem guardar o segredo.
 */

// ── Dublês ───────────────────────────────────────────────────────────────────
const svc = vi.hoisted(() => ({
  listApiTokens: vi.fn(),
  listWorkspaces: vi.fn(),
  createApiToken: vi.fn(),
  revokeApiToken: vi.fn(),
}))
vi.mock("@/service/GisFlowService", () => ({ GisFlowService: svc }))

vi.mock("@/utils/createToast", () => ({
  createToast: { error: vi.fn(), success: vi.fn(), info: vi.fn(), loading: vi.fn(), warning: vi.fn() },
}))

const sessao = vi.hoisted(() => ({ status: "authenticated" }))
vi.mock("next-auth/react", () => ({
  useSession: () => ({ data: { user: { id_hash: "me" } }, status: sessao.status }),
}))

import { createToast } from "@/utils/createToast"
import TokensDeAcesso, { diasAteExpirar, textoDeExpiracao, textoDeWorkspaces } from "@/app/components/tokens"

const ok = <T,>(data: T) => ({ success: true, status: 200, data })
const falhou = (message = "boom", status = 500) => ({ success: false, status, error: { name: "AxiosError", message } })

// ── Massa ────────────────────────────────────────────────────────────────────
const DIA = 86_400_000
const emDias = (n: number) => new Date(Date.now() + n * DIA).toISOString()

// Segredo sintético, num ponto só, para o detect-secrets não acusar a fixture.
const SEGREDO_FAKE = "atl_teste_0000000000000000000000000000" // pragma: allowlist secret

function token(extra: Partial<ApiToken> & Pick<ApiToken, "id" | "name">): ApiToken {
  return {
    token_prefix: "atl_xxxxxx",
    scopes: ["workflows:read"],
    workspace_ids: null,
    expires_at: emDias(60),
    last_used_at: null,
    revoked_at: null,
    created_at: emDias(-3),
    status: "active",
    ...extra,
  }
}

const TOKENS: ApiToken[] = [
  token({ id: "t1", name: "agente de relatórios", token_prefix: "atl_ab12cd", scopes: ["runs:execute", "workflows:read"], last_used_at: emDias(-0.1) }),
  token({ id: "t2", name: "cursor do fulano", token_prefix: "atl_ef34gh", scopes: ["drive:read"], workspace_ids: ["ws-1", "ws-2"], expires_at: emDias(5), created_at: emDias(-10) }),
  token({ id: "t3", name: "antigo", token_prefix: "atl_ij56kl", scopes: ["workflows:write"], workspace_ids: ["ws-1"], expires_at: emDias(-2), last_used_at: emDias(-30), created_at: emDias(-100), status: "expired" }),
  token({ id: "t4", name: "vazado", token_prefix: "atl_mn78op", scopes: ["drive:write"], revoked_at: emDias(-1), created_at: emDias(-20), status: "revoked" }),
]

const WORKSPACES: IWorkspace[] = [
  { id_hash: "ws-1", name: "Bacia", description: null, owner_id: "me", is_default: true, my_role: "owner" },
  { id_hash: "ws-2", name: "Cadastro", description: null, owner_id: "me", is_default: false, my_role: "editor" },
]

beforeEach(() => {
  vi.clearAllMocks()
  sessao.status = "authenticated"
  svc.listApiTokens.mockResolvedValue(ok(TOKENS))
  svc.listWorkspaces.mockResolvedValue(ok(WORKSPACES))
})
afterEach(cleanup)

/** A linha (li de topo) de um token, pelo nome. */
function linha(nome: string) {
  return screen.getByText(nome).closest("li[data-token-status]") as HTMLElement
}

// ── Testes ───────────────────────────────────────────────────────────────────
describe("Tokens de acesso — lista", () => {
  it("mostra o skeleton na 1ª carga e depois os cartões com selos traduzidos", async () => {
    render(<TokensDeAcesso />)
    expect(screen.getByRole("heading", { level: 1, name: "Tokens de acesso" })).toBeInTheDocument()
    expect(screen.getByRole("status", { name: /carregando os tokens de acesso/i })).toHaveAttribute("aria-busy", "true")

    await screen.findByText("agente de relatórios")
    expect(screen.queryByRole("status", { name: /carregando/i })).toBeNull()

    // Selos: sempre em português, valor cru só em data-status.
    expect(screen.getByText("Ativo")).toHaveAttribute("data-status", "active")
    expect(screen.getByText("Expira em 5 dias")).toHaveAttribute("data-status", "active")
    expect(screen.getByText("Expirado")).toHaveAttribute("data-status", "expired")
    expect(screen.getByText("Revogado")).toHaveAttribute("data-status", "revoked")
    expect(screen.queryByText("active")).toBeNull()
    expect(screen.queryByText("revoked")).toBeNull()

    // Subtítulo de escopo com a contagem na frente (o zero some).
    expect(screen.getByText("4 tokens · 2 ativos — valem só para o que a sua conta já pode fazer")).toBeInTheDocument()

    // Só listou e traduziu ids em nomes — nada mais.
    expect(svc.listApiTokens).toHaveBeenCalledTimes(1)
    expect(svc.listWorkspaces).toHaveBeenCalledTimes(1)
  })

  it("cada cartão traz prefixo, escopos como chips, workspaces, último uso e criação", async () => {
    render(<TokensDeAcesso />)
    const t1 = await waitFor(() => linha("agente de relatórios"))
    expect(t1).toHaveTextContent("atl_ab12cd…")
    // Chips na ordem canônica, não na ordem em que o backend mandou.
    const chips = within(within(t1).getByRole("list", { name: "Escopos" })).getAllByRole("listitem").map(li => li.textContent)
    expect(chips).toEqual(["Ler fluxos", "Executar fluxos"])
    expect(t1).toHaveTextContent("Todos os workspaces")
    expect(t1).toHaveTextContent(/Último uso: há/)
    expect(t1).toHaveTextContent(/Criado há 3 dias/)

    const t2 = linha("cursor do fulano")
    expect(t2).toHaveTextContent("2 workspaces: Bacia, Cadastro")
    expect(t2).toHaveTextContent("Nunca usado")

    expect(linha("antigo")).toHaveTextContent("Workspace: Bacia")

    // Revogar só para quem ainda não foi revogado.
    expect(screen.getByRole("button", { name: "Revogar o token agente de relatórios" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Revogar o token antigo" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Revogar o token vazado" })).toBeNull()
  })

  it("sem tokens: vazio de primeiro uso com o escopo da tela e o CTA que abre o diálogo", async () => {
    svc.listApiTokens.mockResolvedValue(ok([]))
    render(<TokensDeAcesso />)
    const cta = await screen.findByRole("button", { name: /criar o primeiro token/i })
    expect(screen.getByText("Para agentes e integrações — valem só para o que a sua conta já pode fazer")).toBeInTheDocument()
    expect(screen.getByText(/herda as permissões da sua conta/i)).toBeInTheDocument()

    fireEvent.click(cta)
    const dialogo = await screen.findByRole("dialog")
    expect(within(dialogo).getByText("Novo token de acesso")).toBeInTheDocument()
  })

  it("erro na 1ª carga toma a tela (não o vazio) e «Tentar de novo» recarrega", async () => {
    svc.listApiTokens.mockResolvedValueOnce(falhou("rede caiu")).mockResolvedValueOnce(ok(TOKENS))
    render(<TokensDeAcesso />)

    const alerta = await screen.findByRole("alert")
    expect(alerta).toHaveTextContent("Não foi possível carregar os tokens de acesso.")
    expect(screen.queryByRole("button", { name: /criar o primeiro token/i })).toBeNull()

    fireEvent.click(within(alerta).getByRole("button", { name: "Tentar de novo" }))
    await screen.findByText("agente de relatórios")
    expect(screen.queryByRole("alert")).toBeNull()
    expect(svc.listApiTokens).toHaveBeenCalledTimes(2)
  })

  it("recarga que falha sobre lista pronta mantém a lista e avisa por toast", async () => {
    svc.listApiTokens.mockResolvedValueOnce(ok(TOKENS)).mockResolvedValueOnce(falhou("timeout"))
    render(<TokensDeAcesso />)
    await screen.findByText("agente de relatórios")

    fireEvent.click(screen.getByRole("button", { name: "Atualizar a lista de tokens" }))
    await waitFor(() => expect(createToast.error).toHaveBeenCalledWith("Não foi possível atualizar os tokens de acesso", "timeout"))
    expect(screen.getByText("agente de relatórios")).toBeInTheDocument()
    expect(screen.queryByRole("alert")).toBeNull()
  })

  it("sessão não autenticada desliga o skeleton sem buscar nada", async () => {
    sessao.status = "unauthenticated"
    render(<TokensDeAcesso />)
    await waitFor(() => expect(screen.queryByRole("status", { name: /carregando/i })).toBeNull())
    expect(svc.listApiTokens).not.toHaveBeenCalled()
  })
})

describe("Tokens de acesso — revogar", () => {
  it("confirma, chama revokeApiToken e a linha vira «Revogado» no lugar", async () => {
    svc.revokeApiToken.mockResolvedValue(ok({ ...TOKENS[0], status: "revoked", revoked_at: emDias(0) }))
    render(<TokensDeAcesso />)
    await screen.findByText("agente de relatórios")

    fireEvent.click(screen.getByRole("button", { name: "Revogar o token agente de relatórios" }))
    const dialogo = await screen.findByRole("dialog")
    expect(dialogo).toHaveTextContent("Agentes que usam «agente de relatórios» param de funcionar na hora.")

    fireEvent.click(within(dialogo).getByRole("button", { name: "Revogar" }))
    await waitFor(() => expect(svc.revokeApiToken).toHaveBeenCalledWith("t1"))

    // Não some da lista: o botão some, o selo muda e a contagem acompanha.
    await waitFor(() => expect(screen.queryByRole("button", { name: "Revogar o token agente de relatórios" })).toBeNull())
    expect(linha("agente de relatórios")).toHaveAttribute("data-token-status", "revoked")
    expect(screen.getByText("agente de relatórios")).toBeInTheDocument()
    expect(screen.getByText("4 tokens · 1 ativo — valem só para o que a sua conta já pode fazer")).toBeInTheDocument()
    expect(createToast.success).toHaveBeenCalledWith("Token revogado", "agente de relatórios")
    expect(svc.listApiTokens).toHaveBeenCalledTimes(1)
  })

  it("falha na revogação avisa e não mexe na lista", async () => {
    svc.revokeApiToken.mockResolvedValue(falhou("sem permissão", 403))
    render(<TokensDeAcesso />)
    await screen.findByText("agente de relatórios")

    fireEvent.click(screen.getByRole("button", { name: "Revogar o token agente de relatórios" }))
    const dialogo = await screen.findByRole("dialog")
    fireEvent.click(within(dialogo).getByRole("button", { name: "Revogar" }))

    await waitFor(() => expect(createToast.error).toHaveBeenCalledWith("Não foi possível revogar o token", "sem permissão"))
    expect(linha("agente de relatórios")).toHaveAttribute("data-token-status", "active")
    // O diálogo segue aberto (a falha não fecha), então a página atrás está
    // aria-hidden — `hidden: true` para enxergar o botão que continua lá.
    expect(screen.getByRole("button", { name: "Revogar o token agente de relatórios", hidden: true })).toBeInTheDocument()
    expect(screen.getByRole("dialog")).toBeInTheDocument()
  })
})

describe("Tokens de acesso — criar pelo cabeçalho", () => {
  it("o token novo entra no topo da lista e o segredo aparece só no diálogo", async () => {
    const criado: ApiTokenCreated = { ...token({ id: "t9", name: "agente novo", token_prefix: "atl_novo00", created_at: emDias(0) }), token: SEGREDO_FAKE }
    svc.createApiToken.mockResolvedValue(ok(criado))
    render(<TokensDeAcesso />)
    await screen.findByText("agente de relatórios")

    fireEvent.click(screen.getByRole("button", { name: "Novo token" }))
    const dialogo = await screen.findByRole("dialog")
    fireEvent.change(within(dialogo).getByLabelText("Nome"), { target: { value: "agente novo" } })
    fireEvent.click(within(dialogo).getByRole("button", { name: /^Ler fluxos/ }))
    fireEvent.click(within(dialogo).getByRole("button", { name: "Criar token" }))

    await waitFor(() => expect(svc.createApiToken).toHaveBeenCalledWith({
      name: "agente novo",
      scopes: ["workflows:read"],
      workspace_ids: ["ws-1", "ws-2"],
      expires_in_days: 90,
    }))
    expect(await within(dialogo).findByLabelText("Segredo do token")).toHaveTextContent(SEGREDO_FAKE)

    // Atrás do diálogo a lista já tem o token novo — no topo, e sem o segredo.
    const linhas = document.querySelectorAll("li[data-token-status]")
    expect(linhas).toHaveLength(5)
    expect(linhas[0]).toHaveTextContent("agente novo")
    expect(linhas[0]).toHaveTextContent("atl_novo00…")
    expect(linhas[0]).not.toHaveTextContent(SEGREDO_FAKE)

    fireEvent.click(within(dialogo).getByRole("button", { name: "Concluir" }))
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull())
    expect(screen.getByText("5 tokens · 3 ativos — valem só para o que a sua conta já pode fazer")).toBeInTheDocument()
  })
})

describe("Tokens de acesso — formatações", () => {
  const nomes = new Map([["ws-1", "Bacia"], ["ws-2", "Cadastro"]])

  it("textoDeWorkspaces: todos, um, vários, e sem nomes resolvidos", () => {
    expect(textoDeWorkspaces(null, nomes)).toBe("Todos os workspaces")
    expect(textoDeWorkspaces([], nomes)).toBe("Nenhum workspace")
    expect(textoDeWorkspaces(["ws-1"], nomes)).toBe("Workspace: Bacia")
    expect(textoDeWorkspaces(["ws-9"], nomes)).toBe("1 workspace")
    expect(textoDeWorkspaces(["ws-1", "ws-2"], nomes)).toBe("2 workspaces: Bacia, Cadastro")
    expect(textoDeWorkspaces(["ws-1", "ws-9"], nomes)).toBe("2 workspaces: Bacia")
    expect(textoDeWorkspaces(["ws-8", "ws-9"], nomes)).toBe("2 workspaces")
  })

  it("textoDeExpiracao e diasAteExpirar", () => {
    expect(textoDeExpiracao(0)).toBe("Expira hoje")
    expect(textoDeExpiracao(-1)).toBe("Expira hoje")
    expect(textoDeExpiracao(1)).toBe("Expira em 1 dia")
    expect(textoDeExpiracao(12)).toBe("Expira em 12 dias")
    const agora = Date.parse("2026-09-13T12:00:00Z")
    expect(diasAteExpirar("2026-09-20T12:00:00Z", agora)).toBe(7)
    expect(diasAteExpirar("2026-09-13T18:00:00Z", agora)).toBe(1)
    expect(diasAteExpirar("2026-09-10T12:00:00Z", agora)).toBe(-3)
    expect(diasAteExpirar(null, agora)).toBeNull()
  })
})
