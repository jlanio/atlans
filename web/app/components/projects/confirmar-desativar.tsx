"use client"

import { Button } from "@/app/components/ui/button"
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/app/components/ui/dialog"
import type { IWorkflow } from "@/service/types"

type Alvo = Pick<IWorkflow, "name" | "has_schedule_trigger" | "has_webhook_trigger">

interface Props<T extends Alvo> {
  /** Null closes the dialog. */
  workflow: T | null
  onConfirm: (workflow: T) => void
  onCancel: () => void
}

/**
 * What deactivating pauses, said before pausing: with a schedule or webhook
 * the consequence is the trigger stops firing; without them, it is the
 * workflow disappearing from the triggers and not being runnable.
 */
export function textoDeDesativar(wf: Alvo): string {
  return wf.has_schedule_trigger || wf.has_webhook_trigger
    ? "O agendamento e o webhook deixam de disparar até você ativar de novo. Execuções em andamento continuam."
    : "Ele some dos gatilhos e não pode ser executado até você ativar de novo."
}

/**
 * Confirmation of "Desativar…" (deactivate, docs/specs/projects.md §3.9). The
 * switch left the card because the risky action lived in the most visible
 * place, with no confirmation; here it says what it pauses. The toggle itself
 * is optimistic, with rollback, in the page composer.
 */
export function ConfirmarDesativar<T extends Alvo>({ workflow, onConfirm, onCancel }: Props<T>) {
  return (
    <Dialog open={workflow != null} onOpenChange={aberto => { if (!aberto) onCancel() }}>
      <DialogContent className="max-w-md">
        {workflow && (
          <>
            <DialogHeader>
              <DialogTitle>Desativar «{workflow.name}»?</DialogTitle>
              <DialogDescription>{textoDeDesativar(workflow)}</DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={onCancel}>Cancelar</Button>
              <Button onClick={() => onConfirm(workflow)}>Desativar</Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
