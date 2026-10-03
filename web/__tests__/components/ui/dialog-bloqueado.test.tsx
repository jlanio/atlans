import { describe, it, expect, vi, afterEach } from "vitest"
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react"
import { Dialog, DialogContent, DialogTitle } from "@/app/components/ui/dialog"

/**
 * `bloqueado` on DialogContent: during an in-flight operation, the dialog's
 * THREE exits are locked — Esc, click outside and the X. Previously each dialog
 * copied the trio `onEscapeKeyDown` + `onInteractOutside` + `closeDisabled`, and
 * whoever forgot one of the three left a door open in the middle of submitting.
 */

afterEach(cleanup)

function montar(bloqueado: boolean, extra: Partial<React.ComponentProps<typeof DialogContent>> = {}) {
  const onOpenChange = vi.fn()
  render(
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent bloqueado={bloqueado} aria-describedby={undefined} {...extra}>
        <DialogTitle>Diálogo</DialogTitle>
      </DialogContent>
    </Dialog>,
  )
  return onOpenChange
}

/**
 * A real click outside the dialog. Radix only starts listening for the outside
 * click one tick after opening, and with the primary button it defers the
 * dismissal from `pointerdown` to the `click` that follows.
 */
async function clickOutside() {
  const tick = () => act(async () => { await new Promise(r => setTimeout(r, 0)) })
  await tick()
  fireEvent.pointerDown(document.body, { button: 0 })
  fireEvent.click(document.body, { button: 0 })
  await tick()
}

describe("DialogContent — bloqueado", () => {
  it("travado: Esc e clique fora não fecham, e o X fica desabilitado (visível)", async () => {
    const onOpenChange = montar(true)
    const dialogo = screen.getByRole("dialog")

    fireEvent.keyDown(dialogo, { key: "Escape", code: "Escape" })
    await clickOutside()

    expect(onOpenChange).not.toHaveBeenCalled()
    expect(screen.getByRole("button", { name: "Fechar" })).toBeDisabled()
  })

  it("solto: as três saídas voltam a fechar", async () => {
    const onOpenChange = montar(false)

    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape", code: "Escape" })
    expect(onOpenChange).toHaveBeenLastCalledWith(false)

    onOpenChange.mockClear()
    await clickOutside()
    expect(onOpenChange).toHaveBeenLastCalledWith(false)

    const fechar = screen.getByRole("button", { name: "Fechar" })
    expect(fechar).toBeEnabled()
    fireEvent.click(fechar)
    expect(onOpenChange).toHaveBeenLastCalledWith(false)
  })

  it("os handlers de quem chama continuam rodando por cima da trava", () => {
    const onEscapeKeyDown = vi.fn()
    montar(true, { onEscapeKeyDown })
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape", code: "Escape" })
    expect(onEscapeKeyDown).toHaveBeenCalledTimes(1)
  })
})
