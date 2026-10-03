"use client"

import { useEffect, useId, useRef, useState } from "react"
import { TbLoader2 } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import { Input } from "@/app/components/ui/input"
import { Label } from "@/app/components/ui/label"
import { createToast } from "@/utils/createToast"
import { useWorkspace, Workspace } from "@/context/WorkspaceContext"
import { SheetSection } from "./section-shell"

export function GeneralSection({ workspace }: { workspace: Workspace }) {
  const { updateWorkspace } = useWorkspace()
  const nameId = useId()
  const descId = useId()

  // Only the owner edits name and description: `update_workspace` in the backend
  // goes through `_get_owned_workspace`, while members and executor accept admin.
  // An admin sees the fields locked, with the rule written out — hiding the
  // section would make the panel change shape without explaining why.
  const canEdit = workspace.my_role === "owner"

  const [name, setName] = useState(workspace.name)
  const [description, setDescription] = useState(workspace.description ?? "")
  const [saving, setSaving] = useState(false)

  // The object changes underfoot on every reload (90s polling, focus return, or
  // a rename made in another tab). Syncing blindly would erase what the user is
  // typing mid-edit, so `touched` protects the draft: whoever has a pending
  // change decides what to do with it.
  const touched = useRef(false)
  useEffect(() => {
    if (touched.current) return
    setName(workspace.name)
    setDescription(workspace.description ?? "")
  }, [workspace.id_hash, workspace.name, workspace.description])

  const dirty =
    name.trim() !== workspace.name ||
    description.trim() !== (workspace.description ?? "")

  async function handleSave() {
    if (!name.trim() || !dirty || saving) return
    setSaving(true)
    try {
      await updateWorkspace(workspace.id_hash, name.trim(), description.trim() || null)
      // Saved: the draft became the real value, so it goes back to following
      // the server.
      touched.current = false
      createToast.success("Workspace atualizado.")
    } catch (e) {
      // The context throws with the backend's real message; swallowing it here is
      // what turned any 403/422 into an "Erro ao atualizar" with no clue at all.
      createToast.error(e instanceof Error ? e.message : "Erro ao atualizar workspace.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <SheetSection
      title="Geral"
      description={canEdit ? undefined : "Apenas o dono pode editar o nome e a descrição."}
    >
      <div className="space-y-4">
        <div className="grid gap-1.5">
          <Label htmlFor={nameId}>Nome</Label>
          <Input
            id={nameId}
            value={name}
            onChange={e => { touched.current = true; setName(e.target.value) }}
            onKeyDown={e => e.key === "Enter" && handleSave()}
            disabled={!canEdit || saving}
            placeholder="Meu workspace"
          />
        </div>

        <div className="grid gap-1.5">
          <Label htmlFor={descId}>Descrição</Label>
          <Input
            id={descId}
            value={description}
            onChange={e => { touched.current = true; setDescription(e.target.value) }}
            onKeyDown={e => e.key === "Enter" && handleSave()}
            disabled={!canEdit || saving}
            placeholder="Opcional"
          />
        </div>

        {canEdit && (
          <div className="flex items-center gap-3">
            <Button onClick={handleSave} disabled={!dirty || !name.trim() || saving} className="gap-1.5">
              {saving && <TbLoader2 className="size-4 animate-spin" aria-hidden="true" />}
              {saving ? "Salvando…" : "Salvar"}
            </Button>
            {dirty && !saving && (
              <span className="text-xs text-muted-foreground">Alterações não salvas</span>
            )}
          </div>
        )}
      </div>
    </SheetSection>
  )
}
