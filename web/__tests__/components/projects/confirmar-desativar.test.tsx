import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import { ConfirmarDesativar, textoDeDesativar } from "@/app/components/projects/confirmar-desativar"

afterEach(cleanup)

const agendado = { name: "Consolidação de outorgas", has_schedule_trigger: true, has_webhook_trigger: false }
const manual = { name: "Recorte por município", has_schedule_trigger: false, has_webhook_trigger: false }

describe("textoDeDesativar", () => {
  it("com agendamento ou webhook fala do gatilho; sem eles, do sumiço", () => {
    expect(textoDeDesativar(agendado)).toBe("O agendamento e o webhook deixam de disparar até você ativar de novo. Execuções em andamento continuam.")
    expect(textoDeDesativar({ ...manual, has_webhook_trigger: true })).toMatch(/deixam de disparar/)
    expect(textoDeDesativar(manual)).toBe("Ele some dos gatilhos e não pode ser executado até você ativar de novo.")
  })
})

describe("ConfirmarDesativar", () => {
  it("título com o nome, texto da variante, e Desativar devolve o workflow", () => {
    const onConfirm = vi.fn()
    render(<ConfirmarDesativar workflow={agendado} onConfirm={onConfirm} onCancel={() => {}} />)
    expect(screen.getByRole("dialog", { name: "Desativar «Consolidação de outorgas»?" })).toBeInTheDocument()
    expect(screen.getByText(/deixam de disparar/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Desativar" }))
    expect(onConfirm).toHaveBeenCalledWith(agendado)
  })

  it("Cancelar chama onCancel; sem workflow, nada é renderizado", () => {
    const onCancel = vi.fn()
    const { rerender } = render(<ConfirmarDesativar workflow={manual} onConfirm={() => {}} onCancel={onCancel} />)
    expect(screen.getByText(/some dos gatilhos/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }))
    expect(onCancel).toHaveBeenCalledTimes(1)
    rerender(<ConfirmarDesativar workflow={null} onConfirm={() => {}} onCancel={onCancel} />)
    expect(screen.queryByRole("dialog")).toBeNull()
  })
})
