"use client"

import { useState } from "react"
import { TbDoorExit, TbTrash } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import { Dialog } from "@/app/components/ui/dialog"
import { DeleteDialog } from "@/app/components/shared/DeleteDialog"
import { createToast } from "@/utils/createToast"
import { useWorkspace, Workspace } from "@/context/WorkspaceContext"
import { DeleteWorkspaceDialog } from "../dialog-content/delete-workspace"
import { SheetSection } from "./section-shell"

/**
 * The workspace's irreversible actions.
 *
 * Delete and leave are MUTUALLY EXCLUSIVE, not one disabled next to the
 * other: the owner cannot leave (they have no row in `workspace_members`, and
 * the backend answers 400), and a non-owner cannot delete. Showing the
 * forbidden button grayed out would only teach that something is out of reach.
 */
export function DangerSection({
  workspace, onClosePanel,
}: {
  workspace: Workspace
  onClosePanel: () => void
}) {
  const { leaveWorkspace } = useWorkspace()
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [leaveOpen, setLeaveOpen] = useState(false)

  const isOwner = workspace.my_role === "owner"

  async function handleLeave() {
    // The panel closes BEFORE awaiting: the target workspace is derived from the
    // list, and the reload that comes with leaving removes it from there — with
    // the panel open, the body would render with the target already null.
    onClosePanel()
    try {
      await leaveWorkspace(workspace.id_hash)
      createToast.success(`Você saiu de "${workspace.name}".`)
    } catch (e) {
      createToast.error(e instanceof Error ? e.message : "Erro ao sair do workspace.")
    }
  }

  return (
    <>
      <SheetSection title="Zona de perigo">
        <div className="space-y-3 rounded-md border border-destructive/30 p-4">
          {isOwner ? (
            workspace.is_default ? (
              <>
                <div className="space-y-1">
                  <p className="text-sm font-medium">Excluir workspace</p>
                  <p className="text-sm text-muted-foreground">
                    O workspace padrão não pode ser removido.
                  </p>
                </div>
              </>
            ) : (
              <>
                <div className="space-y-1">
                  <p className="text-sm font-medium">Excluir workspace</p>
                  <p className="text-sm text-muted-foreground">
                    Desativa os workflows, para os agendamentos e apaga os arquivos do
                    Drive. Só um administrador da plataforma pode restaurar.
                  </p>
                </div>
                <Button
                  variant="destructive"
                  size="sm"
                  className="gap-1.5"
                  onClick={() => setDeleteOpen(true)}
                >
                  <TbTrash className="size-4" />
                  Excluir workspace
                </Button>
              </>
            )
          ) : (
            <>
              <div className="space-y-1">
                <p className="text-sm font-medium">Sair do workspace</p>
                <p className="text-sm text-muted-foreground">
                  Você perde o acesso aos workflows, arquivos e execuções deste
                  workspace. Um administrador pode convidá-lo novamente.
                </p>
              </div>
              <Button
                variant="destructive"
                size="sm"
                className="gap-1.5"
                onClick={() => setLeaveOpen(true)}
              >
                <TbDoorExit className="size-4" />
                Sair do workspace
              </Button>
            </>
          )}

          {isOwner && !workspace.is_default && (
            <p className="border-t pt-3 text-xs text-muted-foreground">
              Como dono, você não pode sair deste workspace — exclua-o.
            </p>
          )}
        </div>
      </SheetSection>

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        {deleteOpen && (
          <DeleteWorkspaceDialog
            workspace={workspace}
            onDeleted={() => { setDeleteOpen(false); onClosePanel() }}
          />
        )}
      </Dialog>

      <Dialog open={leaveOpen} onOpenChange={setLeaveOpen}>
        {leaveOpen && (
          <DeleteDialog
            title={`Sair de "${workspace.name}"?`}
            description={
              "Você perde o acesso aos workflows, arquivos e execuções deste workspace. " +
              "Um administrador pode convidá-lo novamente."
            }
            confirmLabel="Sair"
            loadingLabel="Saindo…"
            onConfirm={handleLeave}
          />
        )}
      </Dialog>
    </>
  )
}
