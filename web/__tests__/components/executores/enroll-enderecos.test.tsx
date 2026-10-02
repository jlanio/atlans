/**
 * Matrícula de executor — os comandos usam os endereços DESTA instalação.
 *
 * Antes, a tela trazia o host dos executores e o site de uma instalação
 * específica fixos no código: numa instalação de outra pessoa, o quickstart
 * mandava rodar `curl <site do dono>/executores/install | bash`. Agora os dois
 * vêm do servidor, junto com o OTP.
 */
import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent, within } from "@testing-library/react"
import type { IExecutorEnrollmentOtpResponse } from "@/service/types"

vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: { getDesktopInstaller: vi.fn(async () => ({ success: false, status: 404, data: null })) },
}))
vi.mock("@/lib/desktop", () => ({ ponteDesktop: () => null }))

import { EnrollConnect, SERVIDOR_A_PREENCHER } from "@/app/components/executores/enroll"

function otp(extra: Partial<IExecutorEnrollmentOtpResponse> = {}): IExecutorEnrollmentOtpResponse {
  return {
    otp: "otp-secreto", expires_at: "2026-10-02T12:00:00Z", executor_id: "exe-1",
    server_url: "https://agents.atlans.example.org", public_url: "https://atlans.example.org",
    ...extra,
  }
}

const comando = () => document.querySelector("pre")!.textContent ?? ""
const metodo = (titulo: string) => fireEvent.click(screen.getByText(titulo))

describe("EnrollConnect — endereços da instalação", () => {
  it("o quickstart baixa o install.sh do site desta instalação", () => {
    render(<EnrollConnect otp={otp()} />)
    metodo("Quickstart")
    expect(comando()).toContain("curl -fsSL https://atlans.example.org/executores/install | bash")
    expect(screen.queryByRole("alert")).toBeNull()
  })

  it("Python e Docker apontam para o host dos executores desta instalação", () => {
    render(<EnrollConnect otp={otp()} />)
    metodo("Python local")
    expect(comando()).toContain("--server=https://agents.atlans.example.org")
    metodo("Docker")
    expect(comando()).toContain("--server=https://agents.atlans.example.org")
  })

  it("o deep link do app leva o servidor desta instalação", () => {
    render(<EnrollConnect otp={otp()} />)
    metodo("App Windows")
    const link = screen.getByRole("link", { name: /abrir no app/i })
    expect(new URL(link.getAttribute("href")!).searchParams.get("server")).toBe("https://agents.atlans.example.org")
  })

  it("sem o host dos executores, os comandos levam um marcador e a tela avisa", () => {
    render(<EnrollConnect otp={otp({ server_url: "" })} />)
    const aviso = screen.getByRole("alert")
    expect(aviso).toHaveTextContent("AGENTS_URL")
    expect(within(aviso).getByText(SERVIDOR_A_PREENCHER)).toBeInTheDocument()
    metodo("Python local")
    expect(comando()).toContain(`--server=${SERVIDOR_A_PREENCHER}`)
    // O install.sh servido também sai sem o host: o quickstart leva a flag.
    metodo("Quickstart")
    expect(comando()).toContain(`--server=${SERVIDOR_A_PREENCHER}`)
  })

  it("com o host dos executores, o quickstart não repete a flag (o install.sh servido já o traz)", () => {
    render(<EnrollConnect otp={otp()} />)
    metodo("Quickstart")
    expect(comando()).not.toContain("--server")
  })

  it("sem o site no OTP, o quickstart usa a origem da página", () => {
    render(<EnrollConnect otp={otp({ public_url: "" })} />)
    metodo("Quickstart")
    expect(comando()).toContain(`curl -fsSL ${window.location.origin}/executores/install`)
  })
})
