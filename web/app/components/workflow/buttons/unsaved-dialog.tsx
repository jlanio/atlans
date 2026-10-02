"use client"

import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/app/components/ui/dialog"
import { Button } from "@/app/components/ui/button"
import { Input } from "@/app/components/ui/input"
import { Label } from "@/app/components/ui/label"
import { useWorkflowSaveStore } from "@/app/stores/workflowSaveStore"

interface UnsavedDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Chamado ao confirmar — salva com o nome preenchido */
  onSave: () => void
  /** Chamado ao descartar — navega sem salvar */
  onDiscard: () => void
}

export default function UnsavedDialog({ open, onOpenChange, onSave, onDiscard }: UnsavedDialogProps) {
  const workflowName = useWorkflowSaveStore(s => s.workflowName)
  const setWorkflowName = useWorkflowSaveStore(s => s.setWorkflowName)
  const [localName, setLocalName] = useState(workflowName ?? "")

  function handleSave() {
    if (!localName.trim()) return
    setWorkflowName(localName.trim())
    // Pequeno delay para o estado propagar antes do save
    requestAnimationFrame(() => onSave())
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Salvar workflow</DialogTitle>
          <DialogDescription>
            O workflow ainda nao possui um nome. Informe um nome para salvar ou descarte as alteracoes.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-2 py-2">
          <Label htmlFor="wf-name">Nome do workflow</Label>
          <Input
            id="wf-name"
            value={localName}
            onChange={e => setLocalName(e.target.value)}
            placeholder="Ex: Analise de cobertura vegetal"
            autoFocus
            onKeyDown={e => { if (e.key === "Enter") handleSave() }}
          />
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={onDiscard}>
            Descartar
          </Button>
          <Button onClick={handleSave} disabled={!localName.trim()}>
            Salvar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
