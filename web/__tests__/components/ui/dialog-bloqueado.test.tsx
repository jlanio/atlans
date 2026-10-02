import { describe, it, expect, vi, afterEach } from "vitest"
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react"
import { Dialog, DialogContent, DialogTitle } from "@/app/components/ui/dialog"

/**
 * `bloqueado` no DialogContent: durante uma operação em voo, as TRÊS saídas do
 * diálogo ficam travadas — Esc, clique fora e o X. Antes cada diálogo copiava o
 * trio `onEscapeKeyDown` + `onInteractOutside` + `closeDisabled`, e quem
 * esquecia uma das três deixava uma porta aberta no meio do envio.
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
 * Um clique de verdade fora do diálogo. O Radix só passa a ouvir o clique fora
 * um tique depois de abrir, e com o botão principal adia a dispensa do
 * `pointerdown` para o `click` que vem em seguida.
 */
async function clicarFora() {
  const tique = () => act(async () => { await new Promise(r => setTimeout(r, 0)) })
  await tique()
  fireEvent.pointerDown(document.body, { button: 0 })
  fireEvent.click(document.body, { button: 0 })
  await tique()
}

describe("DialogContent — bloqueado", () => {
  it("travado: Esc e clique fora não fecham, e o X fica desabilitado (visível)", async () => {
    const onOpenChange = montar(true)
    const dialogo = screen.getByRole("dialog")

    fireEvent.keyDown(dialogo, { key: "Escape", code: "Escape" })
    await clicarFora()

    expect(onOpenChange).not.toHaveBeenCalled()
    expect(screen.getByRole("button", { name: "Fechar" })).toBeDisabled()
  })

  it("solto: as três saídas voltam a fechar", async () => {
    const onOpenChange = montar(false)

    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape", code: "Escape" })
    expect(onOpenChange).toHaveBeenLastCalledWith(false)

    onOpenChange.mockClear()
    await clicarFora()
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
