"use client"

import { useId, useRef, useState } from "react"
import { TbLoader2 } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import { Input } from "@/app/components/ui/input"
import { Label } from "@/app/components/ui/label"
import {
  DialogClose, DialogContent, DialogDescription,
  DialogFooter, DialogHeader, DialogTitle,
} from "@/app/components/ui/dialog"

interface DeleteDialogProps {
  /** May carry an icon along (the batch revocation carries the shield). */
  title: React.ReactNode
  /** May carry markup: the highlighted name, the block with the text to type. */
  description: React.ReactNode
  /**
   * DISCREET note below the description (e.g. "em uso em N nós"). Deliberately a
   * muted line, not a colored panel — the extra context must not shout louder
   * than the confirmation itself.
   */
  note?: React.ReactNode
  /**
   * Warnings between the description and the confirmation: what the action takes
   * with it (the crons that stop, the files that don't come back) or the conflict
   * that calls for the "mesmo assim" (anyway). Unlike `note`, these are panels —
   * and the panel belongs to the caller.
   */
  children?: React.ReactNode
  /**
   * Confirmation by typing: the button only unlocks when the field holds EXACTLY
   * this text (the resource name, "REVOGAR"). Reserved for what can't be undone.
   * Enter in the field confirms through the same path as the button, with the same
   * lock — Enter was where the double submit slipped through in the copies of this
   * that each dialog had.
   */
  confirmarDigitando?: string
  /**
   * The prompt above the field ("Para confirmar, digite …"). Without it the prompt
   * stays in the `description`, with the text in a copyable block.
   */
  rotuloDigitando?: React.ReactNode
  /** May be async — the dialog awaits and locks the buttons while it runs. */
  onConfirm: () => void | Promise<void>
  /**
   * Verb of the confirm button. Not every destructive action is a deletion:
   * "Remover" a member and "Sair" a workspace need the same lock against a
   * double click, but labeling them "Excluir" would describe the wrong action.
   */
  confirmLabel?: string
  /**
   * Label while running — pass the gerund ("Removendo…", "Saindo…").
   * Without it the fallback is `${confirmLabel}…`, which is not correct Portuguese
   * for any verb other than the already-covered case of "Excluir".
   */
  loadingLabel?: string
  /**
   * Label of the button that CLOSES without acting. The default fits almost
   * everything, but there are cases where "Cancelar" next to "Cancelar assinatura"
   * says two opposite things with the same word — there, pass what the person is
   * choosing ("Manter plano").
   */
  cancelLabel?: string
  /**
   * The screen-reader name of the `X`, passed on to `DialogContent`. Without it,
   * the usual "Fechar"; the Home, which speaks three languages, passes its own.
   */
  closeLabel?: string
  /**
   * Class of the `DialogContent`. The Home opens this dialog over a nearly black
   * screen and passes `home-portal` (the content is portaled to <body>, outside the
   * tree that declares its palette); the action dialogs pass the width.
   */
  className?: string
}

// Generic delete confirmation dialog.
//
// The "deleting" state is INTERNAL on purpose: consumers only hand over an
// `onConfirm` (which may be async) and get the lock for free, with no signature change.
// Without it, a double click on "Excluir" fired two DELETEs — and since the delete
// actions remove the item from the list optimistically, the second request hit an
// already-removed resource.
export function DeleteDialog({ onConfirm, className, closeLabel, ...resto }: DeleteDialogProps) {
  const [isDeleting, setIsDeleting] = useState(false)
  // A ref and not just state: the field's Enter and the click can arrive in the
  // same tick, before "deleting" is drawn.
  const emVoo = useRef(false)

  async function handleConfirm() {
    if (emVoo.current) return
    emVoo.current = true
    setIsDeleting(true)
    try {
      await onConfirm()
    } finally {
      // If onConfirm closed the dialog, this setState lands on an unmounted
      // component and React ignores it; if it failed, the button works again.
      emVoo.current = false
      setIsDeleting(false)
    }
  }

  return (
    // Closing in the middle of the deletion leaves the user not knowing whether it
    // happened: `bloqueado` locks all three exits (Esc, click-outside and the X).
    <DialogContent className={className} bloqueado={isDeleting} closeLabel={closeLabel}>
      <Confirmacao {...resto} isDeleting={isDeleting} onConfirmar={handleConfirm} />
    </DialogContent>
  )
}

/**
 * The dialog's core, mounted INSIDE the portal: it unmounts when the dialog closes,
 * and what was typed doesn't survive a reopen. The `DeleteDialog` itself stays
 * mounted when its user leaves it inside a closed `Dialog` — which is the case of
 * dialogs opened from a menu item.
 */
function Confirmacao({
  title, description, note, children, confirmarDigitando, rotuloDigitando,
  isDeleting, onConfirmar,
  cancelLabel = "Cancelar",
  confirmLabel = "Excluir",
  loadingLabel = confirmLabel === "Excluir" ? "Excluindo…" : `${confirmLabel}…`,
}: Omit<DeleteDialogProps, "onConfirm" | "className" | "closeLabel"> & {
  isDeleting: boolean
  onConfirmar: () => void
}) {
  const [digitado, setDigitado] = useState("")
  const campoId = useId()
  const liberado = confirmarDigitando === undefined || digitado === confirmarDigitando

  function confirmar() {
    if (liberado) onConfirmar()
  }

  return (
    <>
      <DialogHeader>
        <DialogTitle>{title}</DialogTitle>
        <DialogDescription>{description}</DialogDescription>
      </DialogHeader>
      {note && (
        <p className="-mt-1 text-xs text-muted-foreground">{note}</p>
      )}
      {children}
      {confirmarDigitando !== undefined && (
        <div className="grid gap-1.5">
          {rotuloDigitando && <Label htmlFor={campoId}>{rotuloDigitando}</Label>}
          <Input
            id={campoId}
            value={digitado}
            onChange={e => setDigitado(e.target.value)}
            // `repeat`: holding Enter must not turn into a second confirmation
            // when the first one comes back with the 409 of the "mesmo assim".
            onKeyDown={e => { if (e.key === "Enter" && !e.repeat) confirmar() }}
            placeholder={confirmarDigitando}
            autoComplete="off"
            // Read-only, and not `disabled`: the browser takes focus away from a
            // disabled field, and after a failure (or the 409) Enter did
            // nothing until the person clicked back into it. Enter in the middle
            // of the action falls into the lock in `handleConfirm`.
            readOnly={isDeleting}
            className="max-md:h-10"
          />
        </div>
      )}
      <DialogFooter>
        <DialogClose asChild>
          <Button variant="outline" disabled={isDeleting} className="max-md:h-10">{cancelLabel}</Button>
        </DialogClose>
        <Button onClick={confirmar} variant="destructive" disabled={isDeleting || !liberado} className="gap-1 max-md:h-10">
          {isDeleting && <TbLoader2 className="size-4 animate-spin" aria-hidden="true" />}
          {isDeleting ? loadingLabel : confirmLabel}
        </Button>
      </DialogFooter>
    </>
  )
}
