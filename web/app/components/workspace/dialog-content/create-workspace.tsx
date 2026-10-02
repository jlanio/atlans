"use client"

import { useId, useState } from "react"
import { TbLoader2 } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import {
  DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/app/components/ui/dialog"
import { Input } from "@/app/components/ui/input"
import { Label } from "@/app/components/ui/label"
import { createToast } from "@/utils/createToast"
import { useWorkspace } from "@/context/WorkspaceContext"

export function CreateWorkspaceDialog({ onClose }: { onClose: () => void }) {
  const { createWorkspace, setCurrent } = useWorkspace()
  const nameId = useId()
  const descId = useId()

  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [saving, setSaving] = useState(false)

  async function handleCreate() {
    if (!name.trim() || saving) return
    setSaving(true)
    try {
      const ws = await createWorkspace(name.trim(), description.trim() || undefined)
      setCurrent(ws)
      createToast.success(`Workspace "${ws.name}" criado.`)
      onClose()
    } catch (e) {
      // O context lança com a mensagem do backend. Substituí-la por um texto
      // genérico apagava justamente o motivo da recusa.
      createToast.error(e instanceof Error ? e.message : "Erro ao criar workspace.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <DialogContent
      bloqueado={saving}
    >
      <DialogHeader>
        <DialogTitle>Novo workspace</DialogTitle>
        <DialogDescription>
          Um ambiente isolado para workflows, arquivos e execuções.
        </DialogDescription>
      </DialogHeader>

      <div className="grid gap-4">
        <div className="grid gap-1.5">
          <Label htmlFor={nameId}>Nome</Label>
          <Input
            id={nameId}
            value={name}
            onChange={e => setName(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleCreate()}
            placeholder="Meu workspace"
            disabled={saving}
            autoFocus
          />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor={descId}>Descrição (opcional)</Label>
          <Input
            id={descId}
            value={description}
            onChange={e => setDescription(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleCreate()}
            placeholder="Descrição do workspace"
            disabled={saving}
          />
        </div>
      </div>

      <DialogFooter>
        <Button variant="outline" onClick={onClose} disabled={saving}>Cancelar</Button>
        <Button onClick={handleCreate} disabled={saving || !name.trim()} className="gap-1.5">
          {saving && <TbLoader2 className="size-4 animate-spin" aria-hidden="true" />}
          {saving ? "Criando…" : "Criar"}
        </Button>
      </DialogFooter>
    </DialogContent>
  )
}
