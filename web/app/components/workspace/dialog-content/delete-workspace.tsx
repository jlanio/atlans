"use client"

import { TbAlertTriangle } from "react-icons/tb"
import { DeleteDialog } from "@/app/components/shared/DeleteDialog"
import { useAcaoDeDialogo } from "@/app/hooks/useAcaoDeDialogo"
import { useWorkspace, Workspace } from "@/context/WorkspaceContext"

/**
 * Exclusão de workspace, com confirmação por digitação do nome.
 *
 * A digitação é reservada a esta ação: ao contrário de remover um membro ou sair
 * (ambos desfazíveis por um novo convite), aqui os arquivos do Drive somem para
 * valer e só um administrador da plataforma pode restaurar o resto.
 */
export function DeleteWorkspaceDialog({
  workspace, onDeleted,
}: {
  workspace: Workspace
  onDeleted: () => void
}) {
  const { deleteWorkspace } = useWorkspace()
  const acao = useAcaoDeDialogo(() => deleteWorkspace(workspace.id_hash), {
    sucesso: [
      `Workspace "${workspace.name}" removido.`,
      "Os workflows foram desativados. Um administrador pode restaurar.",
    ],
    erro: mensagem => mensagem ?? "Erro ao remover workspace.",
    aoConcluir: onDeleted,
  })

  return (
    <DeleteDialog
      title="Remover workspace"
      description="Esta ação afeta os workflows, os agendamentos e os arquivos do workspace."
      confirmarDigitando={workspace.name}
      rotuloDigitando={<>Para confirmar, digite <strong className="text-foreground">{workspace.name}</strong></>}
      confirmLabel="Remover"
      loadingLabel="Removendo…"
      onConfirm={acao.executar}
    >
      {/* O que acontece de fato: sem isto o usuário assume que só o
          workspace some, e descobre depois que os crons pararam e que os
          arquivos do Drive não voltam. */}
      <div className="space-y-1.5 rounded-md border border-amber-500/25 bg-amber-500/5 p-3 text-xs">
        <div className="flex items-start gap-2">
          <TbAlertTriangle className="mt-0.5 shrink-0 text-amber-500" aria-hidden="true" />
          <div className="space-y-1">
            <p className="text-foreground">
              Os workflows deste workspace são desativados e os agendamentos param de
              executar.
            </p>
            <p className="text-muted-foreground">
              Os arquivos do Drive são apagados definitivamente. O workspace vai para a
              lixeira — apenas um administrador da plataforma pode restaurá-lo.
            </p>
          </div>
        </div>
      </div>
    </DeleteDialog>
  )
}
