import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, cleanup, waitFor, fireEvent, within } from "@testing-library/react"

// Execution policy editor (workspace panel, "Execução" section).
// Contracts from spec §9 that the screen promises:
//
// 1. FAIL is the default — and it's what appears selected in an Isolated workspace.
// 2. Under a platform administrator floor, the pool isn't even offered, and the
//    reason is written out.
// 3. Choosing the pool asks for CONFIRMATION before saving: it changes where the data runs.
// 4. With the routing flag off, the editor declares itself a PREVIEW — before
//    anything else — and says what applies today.
// 5. The pool is not a tier: shared executors are not candidates.
// 6. Removing the LAST primary asks for confirmation: it takes the fallback with
//    it and returns the workspace to the pool.

vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: {
    getWorkspacePolicy: vi.fn(),
    getMyAgents: vi.fn(),
    addWorkspacePolicyMember: vi.fn(),
    removeWorkspacePolicyMember: vi.fn(),
    setWorkspaceFallback: vi.fn(),
  },
}))

vi.mock("@/utils/createToast", () => ({
  createToast: { success: vi.fn(), error: vi.fn(), info: vi.fn() },
}))

// The section loads through `useFetchData`, which waits for the authenticated session.
vi.mock("next-auth/react", () => ({ useSession: () => ({ status: "authenticated" }) }))

import { GisFlowService } from "@/service/GisFlowService"
import { createToast } from "@/utils/createToast"
import { ExecutorSection } from "@/app/components/workspace/settings-sheet/executor-section"
import { isolada, membro, politica } from "../../fixtures/politica"

const getPolicy = vi.mocked(GisFlowService.getWorkspacePolicy)
const getMyAgents = vi.mocked(GisFlowService.getMyAgents)
const addMember = vi.mocked(GisFlowService.addWorkspacePolicyMember)
const removeMember = vi.mocked(GisFlowService.removeWorkspacePolicyMember)
const setFallback = vi.mocked(GisFlowService.setWorkspaceFallback)

/* eslint-disable @typescript-eslint/no-explicit-any */
function ok<T>(data: T) { return { status: 200, success: true, data } as any }

const meus = [
  { id_hash: "ex-1", name: "geo-01", status: "active", online: true, executor_type: "dedicated", is_default: false },
  { id_hash: "ex-2", name: "geo-02", status: "active", online: false, executor_type: "dedicated", is_default: false },
  { id_hash: "ex-pool", name: "pool-01", status: "active", online: true, executor_type: "default", is_default: true },
]

beforeEach(() => {
  cleanup()
  vi.clearAllMocks()
  getMyAgents.mockResolvedValue(ok(meus))
  getPolicy.mockResolvedValue(ok(isolada()))
})

function abrir(props: Partial<React.ComponentProps<typeof ExecutorSection>> = {}) {
  return render(<ExecutorSection workspaceId="ws-a" canManage {...props} />)
}

describe("editor da política — último recurso", () => {
  it("Falhar vem selecionado num workspace Isolado, marcado como padrão", async () => {
    abrir()
    const falhar = await screen.findByRole("radio", { name: /Falhar a execução/ })
    expect(falhar.getAttribute("aria-checked")).toBe("true")
    expect(within(falhar).getByText("padrão")).toBeTruthy()
    expect(screen.getByRole("radio", { name: /Usar o pool/ }).getAttribute("aria-checked")).toBe("false")
  })

  it("sob piso, o pool fica bloqueado com o motivo escrito", async () => {
    getPolicy.mockResolvedValue(ok(isolada({ isolation_floor: "no_pool" })))
    abrir()
    const pool = await screen.findByRole("radio", { name: /Usar o pool/ })
    expect(pool.getAttribute("aria-disabled")).toBe("true")
    expect(screen.getByText(/Bloqueado pelo administrador da plataforma/)).toBeTruthy()
    expect(screen.getByText(/Isolamento obrigatório/)).toBeTruthy()
    fireEvent.click(pool)
    expect(setFallback).not.toHaveBeenCalled()
  })

  it("escolher o pool pede confirmação e só grava depois dela", async () => {
    setFallback.mockResolvedValue(ok(isolada({ mode: "dedicated_pool", fallback_terminal: "pool", effective_terminal: "pool", pool: { total: 2, available: 2 } })))
    abrir()
    fireEvent.click(await screen.findByRole("radio", { name: /Usar o pool/ }))

    const dialogo = await screen.findByRole("dialog")
    expect(within(dialogo).getByText(/Usar o pool como último recurso/)).toBeTruthy()
    expect(setFallback).not.toHaveBeenCalled()

    fireEvent.click(within(dialogo).getByRole("button", { name: "Permitir o pool" }))
    await waitFor(() => expect(setFallback).toHaveBeenCalledWith("ws-a", "pool"))
    // The saved policy is the one the server returned: the selection follows it.
    await waitFor(() =>
      expect(screen.getByRole("radio", { name: /Usar o pool/ }).getAttribute("aria-checked")).toBe("true"))
  })

  it("as setas do teclado movem a escolha, como num rádio", async () => {
    abrir()
    const grupo = await screen.findByRole("radiogroup")
    fireEvent.keyDown(grupo, { key: "ArrowRight" })
    // Going to the pool → goes through the confirmation, doesn't save directly.
    expect(await screen.findByRole("dialog")).toBeTruthy()
    expect(setFallback).not.toHaveBeenCalled()
  })

  it("sem executor principal, reserva e último recurso nem aparecem", async () => {
    getPolicy.mockResolvedValue(ok(politica()))
    abrir()
    expect(await screen.findByText(/aparecem depois que houver um executor principal/)).toBeTruthy()
    expect(screen.queryByRole("radiogroup")).toBeNull()
  })
})

describe("editor da política — prévia e alerta", () => {
  it("com a flag desligada, declara-se prévia ANTES de tudo e diz o que vale hoje", async () => {
    getPolicy.mockResolvedValue(ok(isolada({ policy_routing_enabled: false, target_executor_id: "ex-2" })))
    abrir()
    const nota = await screen.findByRole("note")
    expect(within(nota).getByText(/Ainda não está em vigor/)).toBeTruthy()
    expect(nota.textContent).toContain("geo-02")
    expect(screen.getByText(/Isolado · prévia/)).toBeTruthy()
  })

  it("avisa a navegação quando a cadeia não tem ninguém online", async () => {
    getPolicy.mockResolvedValue(ok(isolada({ available_primary: 0 })))
    const onAlertChange = vi.fn()
    abrir({ onAlertChange })
    await waitFor(() => expect(onAlertChange).toHaveBeenLastCalledWith(true))
  })

  it("quem não gerencia lê os níveis, mas não tem botões", async () => {
    abrir({ canManage: false })
    expect(await screen.findByText("geo-01")).toBeTruthy()
    expect(screen.queryByRole("button", { name: /Remover/ })).toBeNull()
    expect(screen.queryByText("Incluir executor")).toBeNull()
  })

  it("Compartilhado sem executor dedicado: uma mensagem só, com o caminho para criar um", async () => {
    getPolicy.mockResolvedValue(ok(politica()))
    getMyAgents.mockResolvedValue(ok([meus[2]]))
    abrir()
    expect(await screen.findByText(/você precisa de um/)).toBeTruthy()
    expect(screen.getByRole("link", { name: /Criar executor dedicado/ })).toBeTruthy()
    expect(screen.queryByText("Executores principais")).toBeNull()
  })
})

describe("editor da política — níveis", () => {
  it("mostra a carga que o executor publica, e marca quem está cheio", async () => {
    getPolicy.mockResolvedValue(ok(isolada({
      primary: [
        membro({ capacity: { running: 1, max_concurrent: 4, queued: 0, max_queue: 50 } }),
        membro({ id_hash: "ex-2", name: "geo-02", capacity: { running: 4, max_concurrent: 4, queued: 50, max_queue: 50 } }),
      ],
      available_primary: 2,
    })))
    abrir()
    expect(await screen.findByText("1 de 4 em execução")).toBeTruthy()
    expect(screen.getByText(/4 de 4 em execução · 50 na fila · cheio/)).toBeTruthy()
  })

  it("inclui um candidato entre os principais; o pool não é candidato", async () => {
    addMember.mockResolvedValue(ok(isolada({
      primary: [membro(), membro({ id_hash: "ex-2", name: "geo-02", online: false })], available_primary: 1,
    })))
    abrir()
    await screen.findByText("geo-01")
    expect(screen.queryByText("pool-01")).toBeNull()

    fireEvent.click(screen.getByRole("button", { name: "Incluir geo-02 entre os principais" }))
    await waitFor(() => expect(addMember).toHaveBeenCalledWith("ws-a", "ex-2", 1))
    expect(await screen.findByText("1 de 2 online")).toBeTruthy()
  })

  it("a reserva exige um principal", async () => {
    getPolicy.mockResolvedValue(ok(politica()))
    abrir()
    const reserva = await screen.findByRole("button", { name: "Incluir geo-01 como reserva" })
    expect((reserva as HTMLButtonElement).disabled).toBe(true)
  })

  it("remover uma reserva não pede confirmação e relê a política", async () => {
    getPolicy.mockResolvedValue(ok(isolada({ fallback: [membro({ id_hash: "ex-2", name: "geo-02", tier: 2 })] })))
    removeMember.mockResolvedValue({ status: 204, success: true } as any)
    abrir()
    fireEvent.click(await screen.findByRole("button", { name: "Remover geo-02 do nível reserva" }))
    await waitFor(() => expect(removeMember).toHaveBeenCalledWith("ws-a", "ex-2"))
    await waitFor(() => expect(getPolicy).toHaveBeenCalledTimes(2))
    expect(screen.queryByRole("dialog")).toBeNull()
  })

  it("remover o ÚLTIMO principal pede confirmação e diz que a reserva vai junto", async () => {
    getPolicy.mockResolvedValue(ok(isolada({ fallback: [membro({ id_hash: "ex-2", name: "geo-02", tier: 2 })] })))
    removeMember.mockResolvedValue({ status: 204, success: true } as any)
    abrir()
    fireEvent.click(await screen.findByRole("button", { name: "Remover geo-01 do nível principal" }))
    expect(removeMember).not.toHaveBeenCalled()

    const dialogo = await screen.findByRole("dialog")
    expect(within(dialogo).getByText(/Remover o último executor principal/)).toBeTruthy()
    expect(dialogo.textContent).toContain("geo-02")

    getPolicy.mockResolvedValue(ok(politica()))
    fireEvent.click(within(dialogo).getByRole("button", { name: "Remover" }))
    await waitFor(() => expect(removeMember).toHaveBeenCalledWith("ws-a", "ex-1"))
    await waitFor(() => expect(createToast.success).toHaveBeenCalledWith(expect.stringMatching(/voltou a usar o pool compartilhado.*reserva/)))
  })
})
