"use client"

import { useEffect, useMemo, useState } from "react"
import { TbRefresh, TbUserPlus } from "react-icons/tb"
import { motion, AnimatePresence } from "framer-motion"
import { Button } from "@/app/components/ui/button"
import { Dialog } from "@/app/components/ui/dialog"
import { DeleteDialog } from "@/app/components/shared/DeleteDialog"
import { GisFlowService } from "@/service/GisFlowService"
import type { IWorkspaceMember } from "@/service/types"
import { createToast } from "@/utils/createToast"
import { Workspace } from "@/context/WorkspaceContext"
import { useFetchData } from "@/app/hooks/useFetchData"
import { InviteMemberDialog } from "../dialog-content/invite-member"
import { MemberRow } from "./member-row"
import { SheetSection } from "./section-shell"

interface Props {
  workspace: Workspace
  canManage: boolean
  currentUserId: string | null
  /** Notifica a contagem para o badge da navegação. */
  onCountChange?: (count: number) => void
}

export function MembersSection({ workspace, canManage, currentUserId, onCountChange }: Props) {
  // A carga é o `useFetchData`, com o workspace como dep: trocar de workspace
  // com a lista do anterior em voo não deixa mais a resposta velha vencer.
  // No erro a lista NÃO vira []: era isso que fazia uma falha de rede virar
  // "Nenhum membro convidado ainda" na tela. `loading` é qualquer carga em voo
  // (a seção troca a lista pelo skeleton, como sempre).
  const { data, loading, error, refetch: load, setData } = useFetchData(
    () => GisFlowService.listWorkspaceMembers(workspace.id_hash),
    "Não foi possível carregar os membros.",
    [workspace.id_hash],
  )
  const members = useMemo(() => data ?? [], [data])
  const setMembers = (atualizar: (anterior: IWorkspaceMember[]) => IWorkspaceMember[]) =>
    setData(anterior => atualizar(anterior ?? []))
  const [savingUserId, setSavingUserId] = useState<string | null>(null)
  const [inviteOpen, setInviteOpen] = useState(false)
  const [removeTarget, setRemoveTarget] = useState<IWorkspaceMember | null>(null)

  useEffect(() => {
    if (!error) onCountChange?.(members.length)
  }, [members.length, error, onCountChange])

  async function handleRoleChange(userId: string, role: string) {
    if (savingUserId) return
    const previous = members.find(m => m.user_id === userId)?.role
    setSavingUserId(userId)
    // Otimista: o select já mostra o novo valor enquanto o PUT viaja. O rollback
    // abaixo é o que impede a tela de afirmar um papel que o servidor recusou.
    setMembers(prev => prev.map(m => (m.user_id === userId ? { ...m, role } : m)))

    const res = await GisFlowService.updateWorkspaceMemberRole(workspace.id_hash, userId, role)
    if (res.error) {
      setMembers(prev =>
        prev.map(m => (m.user_id === userId && previous ? { ...m, role: previous } : m)),
      )
      createToast.error(res.error.message ?? "Erro ao atualizar o papel.")
    } else {
      createToast.success("Papel atualizado.")
    }
    setSavingUserId(null)
  }

  async function confirmRemove() {
    if (!removeTarget) return
    const res = await GisFlowService.removeWorkspaceMember(workspace.id_hash, removeTarget.user_id)
    if (res.error) {
      createToast.error(res.error.message ?? "Erro ao remover membro.")
      return
    }
    setMembers(prev => prev.filter(m => m.user_id !== removeTarget.user_id))
    createToast.success(`${removeTarget.username} removido.`)
    setRemoveTarget(null)
  }

  return (
    <>
      <SheetSection
        title="Membros"
        description={
          canManage
            ? "Quem tem acesso a este workspace e o que cada um pode fazer."
            : "Quem tem acesso a este workspace. Apenas administradores podem alterar."
        }
        action={
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="icon"
              onClick={load}
              disabled={loading}
              aria-label="Atualizar membros"
              title="Atualizar"
            >
              <TbRefresh className={`size-4 ${loading ? "animate-spin" : ""}`} />
            </Button>
            {canManage && (
              <Button variant="outline" size="sm" className="gap-1.5" onClick={() => setInviteOpen(true)}>
                <TbUserPlus className="size-4" />
                Adicionar
              </Button>
            )}
          </div>
        }
        loading={loading}
        error={error}
        onRetry={load}
        isEmpty={members.length === 0}
        emptyMessage="Nenhum membro neste workspace."
      >
        <div className="space-y-2">
          <AnimatePresence initial={false}>
            {members.map(member => (
              // Sem `layout`: a projeção medida por render (layout thrash) não é
              // necessária — entrada/saída seguem via initial/animate/exit.
              <motion.div
                key={member.user_id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 8 }}
                transition={{ duration: 0.15 }}
              >
                <MemberRow
                  member={member}
                  canManage={canManage}
                  currentUserId={currentUserId}
                  savingUserId={savingUserId}
                  onRoleChange={handleRoleChange}
                  onRemove={setRemoveTarget}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </SheetSection>

      {inviteOpen && (
        <InviteMemberDialog
          workspaceId={workspace.id_hash}
          onClose={() => setInviteOpen(false)}
          onInvited={member => {
            setMembers(prev => [...prev, member])
            setInviteOpen(false)
          }}
        />
      )}

      <Dialog open={!!removeTarget} onOpenChange={o => { if (!o) setRemoveTarget(null) }}>
        {removeTarget && (
          <DeleteDialog
            title="Remover membro"
            description={
              `${removeTarget.username} perde o acesso aos workflows, arquivos e ` +
              `execuções de "${workspace.name}". Você pode convidá-lo novamente depois.`
            }
            confirmLabel="Remover"
            loadingLabel="Removendo…"
            onConfirm={confirmRemove}
          />
        )}
      </Dialog>
    </>
  )
}
