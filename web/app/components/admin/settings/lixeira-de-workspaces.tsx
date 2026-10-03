"use client"

// "Lixeira de workspaces" (workspace trash) section of the admin Settings:
// restore or permanently discard the RECORD (the bytes already left on soft delete).

import { useState } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import type { IWorkspaceTrash } from "@/service/types"
import { Button } from "@/app/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/app/components/ui/dialog"
import { DeleteDialog } from "@/app/components/shared/DeleteDialog"
import { useAcaoDeDialogo } from "@/app/hooks/useAcaoDeDialogo"
import { TbAlertTriangle, TbArchive, TbRestore, TbTrashX } from "react-icons/tb"
import { formatLocal } from "@/lib/dayjs"
import { CABECALHO_DE_COLUNAS, CELULA_COM_ROTULO, DESTAQUE_DA_FICHA, LINHA_EMPILHADA } from "@/app/components/shared/tabela-empilhada"
import { formatarInteiro, formatarQuando, plural } from "@/lib/formatos"
import { VazioEmCirculo } from "./estados"

// ── Workspace trash ────────────────────────────────────────────────────────────

/**
 * Permanent discard of the workspace RECORD — not to be confused with the purge
 * in the Storage section, which deletes bytes. Here the files are already gone:
 * the soft delete purges the Drive at once and expires the artifacts. What is
 * left is the row.
 *
 * Type-to-confirm on the client + `confirm` revalidated on the server: the button
 * sits next to each table row, and now over other users' workspaces.
 */
function PurgeWorkspaceDialog({ ws, onClose, onPurged }: {
  ws: IWorkspaceTrash
  onClose: () => void
  onPurged: () => void
}) {
  const acao = useAcaoDeDialogo(() => GisFlowService.purgeWorkspace(ws.id_hash), {
    sucesso: `Workspace "${ws.name}" excluído permanentemente.`,
    erro: mensagem => ["Falha ao excluir", mensagem],
    aoConcluir: () => { onPurged(); onClose() },
  })

  return (
    // While deleting, the exits are locked by `DeleteDialog`.
    <Dialog open onOpenChange={open => { if (!open) onClose() }}>
      <DeleteDialog
        title="Excluir workspace permanentemente"
        description={
          <>
            O registro de <span className="font-medium text-foreground">{ws.name}</span> some do
            banco. Depois disso não há como restaurar.
          </>
        }
        confirmarDigitando={ws.name}
        rotuloDigitando={<>Para confirmar, digite <span className="font-medium text-foreground">{ws.name}</span></>}
        confirmLabel="Excluir permanentemente"
        loadingLabel="Excluindo..."
        onConfirm={acao.executar}
      >
        <div className="rounded-md border border-red-500/30 bg-red-50 p-3 text-xs dark:bg-red-500/10">
          <div className="flex items-start gap-2">
            <TbAlertTriangle className="mt-0.5 shrink-0 text-red-500" aria-hidden="true" />
            <div className="space-y-1">
              <p className="font-medium text-foreground">
                {plural(ws.workflows, "workflow")} {ws.workflows === 1 ? "deixa" : "deixam"} de ser {ws.workflows === 1 ? "restaurável" : "restauráveis"}
              </p>
              <p className="text-muted-foreground">
                Os arquivos do Drive já foram removidos no momento da exclusão — esta ação
                descarta o registro, não os dados. Os membros saem junto.
              </p>
            </div>
          </div>
        </div>
      </DeleteDialog>
    </Dialog>
  )
}

function RestoreWorkspaceDialog({ ws, onClose, onRestored }: {
  ws: IWorkspaceTrash
  onClose: () => void
  onRestored: () => void
}) {
  const acao = useAcaoDeDialogo(() => GisFlowService.restoreWorkspace(ws.id_hash), {
    sucesso: dados => [
      `Workspace "${ws.name}" restaurado.`,
      `${plural(dados?.workflows_restored ?? 0, "workflow")} devolvido(s), desativados. O dono precisa reativá-los.`,
    ],
    erro: mensagem => ["Falha ao restaurar", mensagem],
    aoConcluir: () => { onRestored(); onClose() },
  })

  return (
    <Dialog open onOpenChange={open => { if (!open) onClose() }}>
      <DialogContent bloqueado={acao.executando}>
        <DialogHeader>
          <DialogTitle>Restaurar workspace</DialogTitle>
          <DialogDescription>
            <span className="font-medium text-foreground">{ws.name}</span> volta para
            {" "}{ws.owner_username ?? "o dono"}, com {plural(ws.workflows, "workflow")}.
          </DialogDescription>
        </DialogHeader>

        {/* The admin restores, tells the owner, and the owner assumes everything
            came back. That is why the notice comes BEFORE confirming, not only in the toast. */}
        <div className="rounded-md border border-amber-500/30 bg-amber-50 p-3 text-xs dark:bg-amber-500/10">
          <div className="flex items-start gap-2">
            <TbAlertTriangle className="mt-0.5 shrink-0 text-amber-500" aria-hidden="true" />
            <div className="space-y-1">
              <p className="font-medium text-foreground">
                Os workflows voltam desativados, e os agendamentos também
              </p>
              <p className="text-muted-foreground">
                Não há registro de quais estavam ativos antes da exclusão — religar em bloco
                reativaria o que o dono tinha desligado de propósito. Avise-o para reativar o
                que ainda fizer sentido.
              </p>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={acao.executando} className="max-md:h-10">Cancelar</Button>
          <Button onClick={acao.executar} disabled={acao.executando} className="max-md:h-10">
            {acao.executando ? "Restaurando..." : "Restaurar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function WorkspaceTrashSection({ items, onChanged }: {
  items: IWorkspaceTrash[]
  onChanged: () => void
}) {
  const [restoreTarget, setRestoreTarget] = useState<IWorkspaceTrash | null>(null)
  const [purgeTarget, setPurgeTarget] = useState<IWorkspaceTrash | null>(null)

  if (items.length === 0) {
    return <VazioEmCirculo icone={TbArchive} titulo="A lixeira está vazia" descricao="Nenhum workspace aguardando restauração ou exclusão definitiva." />
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-xs md:min-w-[560px]">
          <thead className={CABECALHO_DE_COLUNAS}>
            <tr className="border-b border-border bg-muted/50">
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">Workspace</th>
              <th className="px-3 py-2 text-left font-medium text-muted-foreground">Removido em</th>
              <th className="px-3 py-2 text-right font-medium text-muted-foreground">Workflows</th>
              <th className="w-20 px-3 py-2" aria-label="Ações" />
            </tr>
          </thead>
          <tbody>
            {items.map(ws => (
              <tr key={ws.id_hash} className={`border-b border-border last:border-b-0 ${LINHA_EMPILHADA}`}>
                <td className={`px-3 py-2 ${DESTAQUE_DA_FICHA}`}>
                  <div className="font-medium text-foreground">{ws.name}</div>
                  <div className="text-muted-foreground">
                    {ws.owner_username ?? "(sem dono)"}
                    {ws.owner_email && <span className="ml-1 opacity-60">· {ws.owner_email}</span>}
                  </div>
                </td>
                <td data-rotulo="removido" className={`px-3 py-2 text-muted-foreground ${CELULA_COM_ROTULO}`}>
                  <div className="tabular-nums">{formatLocal(ws.deleted_at)}</div>
                  <div className="text-[11px] opacity-70 tabular-nums">{formatarQuando(ws.deleted_at)}</div>
                </td>
                <td data-rotulo="workflows" className={`px-3 py-2 text-right tabular-nums text-foreground ${CELULA_COM_ROTULO}`}>{formatarInteiro(ws.workflows)}</td>
                <td className="px-3 py-2">
                  <div className="flex justify-end gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-7 text-muted-foreground hover:text-foreground max-md:size-10"
                      title={`Restaurar ${ws.name}`}
                      aria-label={`Restaurar ${ws.name}`}
                      onClick={() => setRestoreTarget(ws)}
                    >
                      <TbRestore className="size-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-7 text-muted-foreground hover:text-red-500 max-md:size-10"
                      title={`Excluir ${ws.name} permanentemente`}
                      aria-label={`Excluir ${ws.name} permanentemente`}
                      onClick={() => setPurgeTarget(ws)}
                    >
                      <TbTrashX className="size-4" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {restoreTarget && (
        <RestoreWorkspaceDialog
          ws={restoreTarget}
          onClose={() => setRestoreTarget(null)}
          onRestored={onChanged}
        />
      )}
      {purgeTarget && (
        <PurgeWorkspaceDialog
          ws={purgeTarget}
          onClose={() => setPurgeTarget(null)}
          onPurged={onChanged}
        />
      )}
    </div>
  )
}
