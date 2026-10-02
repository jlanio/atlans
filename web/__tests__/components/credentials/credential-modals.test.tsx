import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, cleanup, waitFor, fireEvent } from "@testing-library/react"

/**
 * Regressoes dos modais de credencial. O caso mais grave e o primeiro:
 *
 * O backend faz `self.data = {...}` no encrypt_and_store — SUBSTITUI o blob de
 * segredos inteiro, sem merge — e so pula a re-encriptacao quando `data` chega
 * vazio. Logo um `data` PARCIAL e destrutivo: se a busca dos segredos falhasse e
 * o usuario salvasse, os outros campos eram apagados, e `_build_postgres_dsn`
 * preenchia o que faltava com defaults, gerando `postgresql://:@localhost:5432/`.
 * Uma credencial plausivel e quebrada, que so falha na execucao do workflow.
 *
 * Por isso o modal de editar tem que bloquear o Salvar enquanto os segredos nao
 * chegam, e continuar bloqueado se a busca falhar.
 */

const getCredentialTypes = vi.fn()
const getCredentialData = vi.fn()
const createCredential = vi.fn()
const updateCredential = vi.fn()

vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: {
    getCredentialTypes: (...a: unknown[]) => getCredentialTypes(...a),
    getCredentialData: (...a: unknown[]) => getCredentialData(...a),
    createCredential: (...a: unknown[]) => createCredential(...a),
    updateCredential: (...a: unknown[]) => updateCredential(...a),
    testCredential: vi.fn().mockResolvedValue({ data: { ok: true, message: "ok" } }),
  },
}))

vi.mock("@/utils/createToast", () => ({
  createToast: { error: vi.fn(), success: vi.fn(), info: vi.fn(), loading: vi.fn() },
}))

const CREDENCIAL = { id: "cred-1", name: "pg-prod", type: "postgresql" }

vi.mock("@/context/useCredentialsContext", () => ({
  useCredentialsContext: () => ({
    credentials: [CREDENCIAL],
    setCredentialsContext: vi.fn(),
  }),
}))

const TIPO_PG = {
  type: "postgresql",
  label: "PostgreSQL / PostGIS",
  description: "",
  node_types: ["datasource"],
  fields: [
    { key: "host", label: "Host", type: "text", required: true, placeholder: "localhost" },
    { key: "password", label: "Senha", type: "password", required: true, placeholder: "" },
  ],
}

// Valor fake dos segredos nas fixtures. Centralizado num ponto só para o
// detect-secrets nao acusar cada `password: "..."` espalhado pelos testes.
const SEGREDO_FAKE = "s3cr3t" // pragma: allowlist secret

import { Dialog } from "@/app/components/ui/dialog"
import ConfigureCredential from "@/app/components/credentials/dialog-content/configure-credential"
import CreateCredential from "@/app/components/credentials/dialog-content/create-credential"

function renderConfigure() {
  return render(
    <Dialog open>
      <ConfigureCredential configureCredentialId="cred-1" setConfigureCredentialId={vi.fn()} />
    </Dialog>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  getCredentialTypes.mockResolvedValue({ data: [TIPO_PG] })
})

afterEach(() => cleanup())

describe("ConfigureCredential — bloqueio contra perda de segredo", () => {
  it("mantem o Salvar desabilitado enquanto os segredos nao carregam", async () => {
    // Promise que nunca resolve: simula a busca em voo.
    getCredentialData.mockReturnValue(new Promise(() => {}))
    renderConfigure()

    const salvar = await screen.findByRole("button", { name: /salvar/i })
    expect(salvar).toBeDisabled()
  })

  it("mantem o Salvar desabilitado e avisa quando a busca dos segredos falha", async () => {
    getCredentialData.mockResolvedValue({ error: { message: "falha de rede" } })
    renderConfigure()

    // O aviso precisa ser role=alert para ser anunciado.
    const aviso = await screen.findByRole("alert")
    expect(aviso.textContent).toMatch(/não foi possível carregar/i)

    expect(screen.getByRole("button", { name: /salvar/i })).toBeDisabled()
    expect(updateCredential).not.toHaveBeenCalled()
  })

  it("libera o Salvar depois que os segredos chegam", async () => {
    getCredentialData.mockResolvedValue({
      data: { ...CREDENCIAL, data: { host: "db.local", password: SEGREDO_FAKE } },
    })
    renderConfigure()

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /salvar/i })).not.toBeDisabled()
    })
    // E os campos do schema aparecem, nao o editor livre (que mostraria os
    // valores em texto claro).
    expect(screen.getByLabelText(/host/i)).toBeInTheDocument()
  })
})

describe("Modais de credencial — botao de teste estavel", () => {
  it("renderiza o botao de teste sempre, desabilitado quando nao ha o que testar", async () => {
    render(
      <Dialog open>
        <CreateCredential setCreateModalState={vi.fn()} />
      </Dialog>,
    )

    // Antes ele so era montado quando `data` tinha chave, entao aparecia e
    // desaparecia enquanto o usuario digitava, deslocando os outros botoes e
    // entrando/saindo da ordem de tabulacao.
    const testar = await screen.findByRole("button", { name: /testar credencial/i })
    expect(testar).toBeDisabled()
  })

  it("nao promete 'testar conexao', porque o backend nao conecta em todos os tipos", async () => {
    render(
      <Dialog open>
        <CreateCredential setCreateModalState={vi.fn()} />
      </Dialog>,
    )
    await screen.findByRole("button", { name: /testar credencial/i })
    expect(screen.queryByRole("button", { name: /testar conexão/i })).toBeNull()
  })
})

describe("Resultado do teste — nao pode piscar e desaparecer", () => {
  it("permanece na tela depois do clique em testar", async () => {
    getCredentialData.mockResolvedValue({
      data: { ...CREDENCIAL, data: { host: "db.local", password: SEGREDO_FAKE } },
    })
    renderConfigure()

    const testar = await screen.findByRole("button", { name: /testar credencial/i })
    await waitFor(() => expect(testar).not.toBeDisabled())

    fireEvent.click(testar)

    // O efeito que invalida o resultado depende do valor SERIALIZADO de `data`.
    // Se dependesse do objeto (form.watch devolve referencia nova por render),
    // ele limparia o banner no render seguinte ao proprio teste.
    const banner = await screen.findByRole("status")
    expect(banner.textContent).toMatch(/ok/i)

    await new Promise(r => setTimeout(r, 50))
    expect(screen.getByRole("status")).toBeInTheDocument()
  })
})

describe("Correcoes de revisao", () => {
  it("mascara o valor no editor livre MAS oferece como revelar", async () => {
    // Mascarar sem toggle deixaria a edicao as cegas: era o efeito colateral de
    // uma correcao de seguranca aplicada pela metade.
    getCredentialTypes.mockResolvedValue({ data: [] })   // sem catalogo -> editor livre
    getCredentialData.mockResolvedValue({
      data: { ...CREDENCIAL, data: { token_custom: SEGREDO_FAKE } },
    })
    renderConfigure()

    const valor = await screen.findByLabelText("Valor de token_custom")
    expect(valor).toHaveAttribute("type", "password")

    const olho = screen.getByRole("button", { name: /mostrar valor de token_custom/i })
    expect(olho).toHaveAttribute("aria-pressed", "false")
    fireEvent.click(olho)

    await waitFor(() => {
      expect(screen.getByLabelText("Valor de token_custom")).toHaveAttribute("type", "text")
    })
  })

  it("avisa quando o catalogo de tipos falha no modal de editar", async () => {
    getCredentialTypes.mockResolvedValue({ error: { message: "falha" } })
    getCredentialData.mockResolvedValue({
      data: { ...CREDENCIAL, data: { host: "db.local" } },
    })
    renderConfigure()

    await waitFor(() => {
      const alertas = screen.getAllByRole("alert").map(n => n.textContent ?? "")
      expect(alertas.some(t => /tipos de credencial/i.test(t))).toBe(true)
    })
  })
})
