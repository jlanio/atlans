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

  // Só o dono edita nome e descrição: `update_workspace` no backend passa por
  // `_get_owned_workspace`, enquanto membros e executor aceitam admin. Um admin
  // vê os campos travados, com a regra escrita — esconder a seção faria o painel
  // mudar de forma sem explicar por quê.
  const canEdit = workspace.my_role === "owner"

  const [name, setName] = useState(workspace.name)
  const [description, setDescription] = useState(workspace.description ?? "")
  const [saving, setSaving] = useState(false)

  // O objeto muda sob os pés a cada reload (polling de 90s, volta de foco, ou
  // renomeação feita em outra aba). Sincronizar cegamente apagaria o que o
  // usuário está digitando no meio da edição, então `touched` protege o
  // rascunho: quem tem alteração pendente decide o que fazer com ela.
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
      // Salvo: o rascunho virou o valor de verdade, então volta a acompanhar
      // o servidor.
      touched.current = false
      createToast.success("Workspace atualizado.")
    } catch (e) {
      // O context lança com a mensagem real do backend; engoli-la aqui era o que
      // transformava qualquer 403/422 num "Erro ao atualizar" sem pista nenhuma.
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
