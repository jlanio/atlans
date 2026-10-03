import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, cleanup, waitFor, fireEvent } from "@testing-library/react"

/**
 * Regressions of the credential modals. The most serious case is the first:
 *
 * The backend does `self.data = {...}` in encrypt_and_store — it REPLACES the whole
 * secrets blob, with no merge — and only skips re-encryption when `data` arrives
 * empty. So a PARTIAL `data` is destructive: if fetching the secrets failed and
 * the user saved, the other fields were wiped, and `_build_postgres_dsn`
 * filled in what was missing with defaults, producing `postgresql://:@localhost:5432/`.
 * A plausible but broken credential, which only fails when the workflow runs.
 *
 * That is why the edit modal has to block Save while the secrets have not
 * arrived, and stay blocked if the fetch fails.
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

const PG_TYPE = {
  type: "postgresql",
  label: "PostgreSQL / PostGIS",
  description: "",
  node_types: ["datasource"],
  fields: [
    { key: "host", label: "Host", type: "text", required: true, placeholder: "localhost" },
    { key: "password", label: "Senha", type: "password", required: true, placeholder: "" },
  ],
}

// Fake value of the secrets in the fixtures. Centralized in a single place so
// detect-secrets does not flag each `password: "..."` scattered across the tests.
const FAKE_SECRET = "s3cr3t" // pragma: allowlist secret

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
  getCredentialTypes.mockResolvedValue({ data: [PG_TYPE] })
})

afterEach(() => cleanup())

describe("ConfigureCredential — bloqueio contra perda de segredo", () => {
  it("mantem o Salvar desabilitado enquanto os segredos nao carregam", async () => {
    // A Promise that never resolves: simulates the fetch in flight.
    getCredentialData.mockReturnValue(new Promise(() => {}))
    renderConfigure()

    const salvar = await screen.findByRole("button", { name: /salvar/i })
    expect(salvar).toBeDisabled()
  })

  it("mantem o Salvar desabilitado e avisa quando a busca dos segredos falha", async () => {
    getCredentialData.mockResolvedValue({ error: { message: "falha de rede" } })
    renderConfigure()

    // The warning needs to be role=alert to be announced.
    const aviso = await screen.findByRole("alert")
    expect(aviso.textContent).toMatch(/não foi possível carregar/i)

    expect(screen.getByRole("button", { name: /salvar/i })).toBeDisabled()
    expect(updateCredential).not.toHaveBeenCalled()
  })

  it("libera o Salvar depois que os segredos chegam", async () => {
    getCredentialData.mockResolvedValue({
      data: { ...CREDENCIAL, data: { host: "db.local", password: FAKE_SECRET } },
    })
    renderConfigure()

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /salvar/i })).not.toBeDisabled()
    })
    // And the schema fields show up, not the free-form editor (which would show the
    // values in plain text).
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

    // Before, it was only mounted when `data` had a key, so it appeared and
    // disappeared while the user typed, shifting the other buttons and
    // entering/leaving the tab order.
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
      data: { ...CREDENCIAL, data: { host: "db.local", password: FAKE_SECRET } },
    })
    renderConfigure()

    const testar = await screen.findByRole("button", { name: /testar credencial/i })
    await waitFor(() => expect(testar).not.toBeDisabled())

    fireEvent.click(testar)

    // The effect that invalidates the result depends on the SERIALIZED value of `data`.
    // If it depended on the object (form.watch returns a new reference per render),
    // it would clear the banner on the render right after the test itself.
    const banner = await screen.findByRole("status")
    expect(banner.textContent).toMatch(/ok/i)

    await new Promise(r => setTimeout(r, 50))
    expect(screen.getByRole("status")).toBeInTheDocument()
  })
})

describe("Correcoes de revisao", () => {
  it("mascara o valor no editor livre MAS oferece como revelar", async () => {
    // Masking without a toggle would leave editing blind: it was the side effect of
    // a security fix applied halfway.
    getCredentialTypes.mockResolvedValue({ data: [] })   // no catalog -> free-form editor
    getCredentialData.mockResolvedValue({
      data: { ...CREDENCIAL, data: { token_custom: FAKE_SECRET } },
    })
    renderConfigure()

    const valor = await screen.findByLabelText("Valor de token_custom")
    expect(valor).toHaveAttribute("type", "password")

    const eyeButton = screen.getByRole("button", { name: /mostrar valor de token_custom/i })
    expect(eyeButton).toHaveAttribute("aria-pressed", "false")
    fireEvent.click(eyeButton)

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
