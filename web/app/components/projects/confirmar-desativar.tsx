"use client"

import { Button } from "@/app/components/ui/button"
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/app/components/ui/dialog"
import type { IWorkflow } from "@/service/types"

type Alvo = Pick<IWorkflow, "name" | "has_schedule_trigger" | "has_webhook_trigger">

interface Props<T extends Alvo> {
  /** Nulo fecha o diálogo. */
  workflow: T | null
  onConfirm: (workflow: T) => void
  onCancel: () => void
}

/**
 * O que desativar pausa, dito antes de pausar: com agendamento ou webhook a
 * consequência é o gatilho parar de disparar; sem eles, é o workflow sumir
 * dos gatilhos e não poder ser executado.
 */
export function textoDeDesativar(wf: Alvo): string {
  return wf.has_schedule_trigger || wf.has_webhook_trigger
    ? "O agendamento e o webhook deixam de disparar até você ativar de novo. Execuções em andamento continuam."
    : "Ele some dos gatilhos e não pode ser executado até você ativar de novo."
}

/**
 * Confirmação de "Desativar…" (docs/specs/projetos.md §3.9). O interruptor
 * saiu do card porque a ação arriscada morava no lugar mais visível, sem
 * confirmação; aqui ela diz o que pausa. A troca em si é otimista, com
 * reversão, em quem compõe a página.
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
