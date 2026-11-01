/**
 * The confirmation card says WHY a click is asked for a workflow the assistant
 * wrote itself: the nodes that act outside the platform (`acao.efeitos`).
 */
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import ConfirmationCard from "@/app/components/home/assistente/cartao-confirmacao"

vi.mock("next/navigation", () => ({ usePathname: () => "/" }))

const base = { tool_use_id: "tu1", token: "TOK" }

describe("cartão de confirmação", () => {
  it("lista os nós que agem fora da plataforma", () => {
    render(
      <ConfirmationCard
        confirmacao={{ ...base, acao: { tool: "create_workflow", argumentos: {}, efeitos: ["SendEmail (n4)", "HttpRequest (n5)"] } }}
        decidido={false}
        ocupado={false}
        onDecidir={() => {}}
      />,
    )
    expect(screen.getByText("Age fora da plataforma: SendEmail (n4), HttpRequest (n5)")).toBeTruthy()
  })

  it("sem efeitos, não mostra a linha", () => {
    render(
      <ConfirmationCard
        confirmacao={{ ...base, acao: { tool: "delete_schedule", argumentos: {}, alvo: "sch-1" } }}
        decidido={false}
        ocupado={false}
        onDecidir={() => {}}
      />,
    )
    expect(screen.queryByText(/Age fora da plataforma/)).toBeNull()
  })
})
