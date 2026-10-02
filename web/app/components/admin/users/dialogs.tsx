"use client"

import { useState, useEffect } from "react"
import { TbAlertTriangle, TbBan, TbCheck, TbTrash, TbUserShield, TbServer, TbShieldOff } from "react-icons/tb"
import { GisFlowService, IAdminUser } from "@/service/GisFlowService"
import { Button } from "@/app/components/ui/button"
import { Input } from "@/app/components/ui/input"
import { Label } from "@/app/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/app/components/ui/dialog"
import { DropdownMenuItem } from "@/app/components/ui/dropdown-menu"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/app/components/ui/select"
import { DeleteDialog } from "@/app/components/shared/DeleteDialog"
import { useAcaoDeDialogo } from "@/app/hooks/useAcaoDeDialogo"
import { createToast } from "@/utils/createToast"
import { plural } from "@/lib/formatos"

/*
 * Os seis diálogos de ação da tela Admin › Usuários, extraídos da página para
 * que o `page.tsx` fique só com composição e estado. O ciclo de cada ação —
 * aberto, executando, toast, fechar, `onCompleted` — é o `useAcaoDeDialogo`, e
 * a confirmação por digitação (o nome, REVOGAR) é a do `DeleteDialog`: antes
 * cada diálogo tinha a sua cópia, e o Enter do campo chamava a ação sem olhar
 * se ela já estava em voo. Enquanto a ação roda, o diálogo não fecha
 * (`bloqueado`). As chamadas de serviço, a sequência cota→revoke, os textos e
 * as props são os de antes; cores de status seguem os pares claro/escuro
 * sancionados e os botões usam variant/token.
 */

// ── Diálogo: Suspender ─────────────────────────────────────────────────────────

export function SuspendUserDialog({ user, onCompleted }: { user: IAdminUser; onCompleted: () => void }) {
  const [reason, setReason] = useState("")
  const acao = useAcaoDeDialogo(() => GisFlowService.suspendUser(user.id_hash, reason || undefined), {
    sucesso: `Usuário «${user.username}» suspenso.`,
    erro: mensagem => mensagem ?? "Erro ao suspender usuário.",
    aoConcluir: onCompleted,
  })

  function handleClose(val: boolean) {
    if (!val) setReason("")
    acao.setAberto(val)
  }

  return (
    <Dialog open={acao.aberto} onOpenChange={handleClose}>
      <DialogTrigger asChild>
        {/* Item em âmbar (cautela) com o par escuro sancionado. */}
        <DropdownMenuItem
          className="text-amber-600 focus:text-amber-600 dark:text-amber-400 dark:focus:text-amber-400"
          onSelect={e => { e.preventDefault(); acao.setAberto(true) }}
        >
          <TbBan className="mr-2" aria-hidden="true" /> Suspender
        </DropdownMenuItem>
      </DialogTrigger>
      <DialogContent className="max-w-md" bloqueado={acao.executando}>
        <DialogHeader>
          <DialogTitle>Suspender usuário</DialogTitle>
          <DialogDescription>
            O usuário <span className="font-semibold text-foreground">«{user.username}»</span> não
            poderá mais acessar a plataforma enquanto estiver suspenso.
          </DialogDescription>
        </DialogHeader>
        <div className="py-2 flex flex-col gap-2">
          <Label htmlFor="suspend-reason">Motivo (opcional)</Label>
          <Input
            id="suspend-reason"
            placeholder="Ex: violação dos termos de uso"
            value={reason}
            onChange={e => setReason(e.target.value)}
            className="max-md:h-10"
          />
        </div>
        <DialogFooter>
          <Button variant="outline" className="max-md:h-10" disabled={acao.executando} onClick={() => handleClose(false)}>Cancelar</Button>
          {/* Âmbar de cautela com par escuro — sancionado pelo contrato (§6). */}
          <Button
            className="bg-amber-600 text-white hover:bg-amber-600/90 dark:bg-amber-500 dark:text-amber-950 dark:hover:bg-amber-500/90 max-md:h-10"
            disabled={acao.executando}
            onClick={acao.executar}
          >
            {acao.executando ? "Suspendendo…" : "Suspender"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Diálogo: Reativar ──────────────────────────────────────────────────────────

export function ReactivateUserDialog({ user, onCompleted }: { user: IAdminUser; onCompleted: () => void }) {
  const acao = useAcaoDeDialogo(() => GisFlowService.reactivateUser(user.id_hash), {
    sucesso: `Usuário «${user.username}» reativado.`,
    erro: mensagem => mensagem ?? "Erro ao reativar usuário.",
    aoConcluir: onCompleted,
  })

  return (
    <Dialog open={acao.aberto} onOpenChange={acao.setAberto}>
      <DialogTrigger asChild>
        {/* Verde de sucesso com o par escuro sancionado. */}
        <DropdownMenuItem
          className="text-green-600 focus:text-green-600 dark:text-green-400 dark:focus:text-green-400"
          onSelect={e => { e.preventDefault(); acao.setAberto(true) }}
        >
          <TbCheck className="mr-2" aria-hidden="true" /> Reativar
        </DropdownMenuItem>
      </DialogTrigger>
      <DialogContent className="max-w-sm" bloqueado={acao.executando}>
        <DialogHeader>
          <DialogTitle>Reativar usuário</DialogTitle>
          <DialogDescription>
            O usuário <span className="font-semibold text-foreground">«{user.username}»</span> poderá
            acessar a plataforma novamente.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" className="max-md:h-10" disabled={acao.executando} onClick={() => acao.setAberto(false)}>Cancelar</Button>
          <Button className="max-md:h-10" disabled={acao.executando} onClick={acao.executar}>
            {acao.executando ? "Reativando…" : "Reativar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Diálogo: Excluir (soft-delete) ─────────────────────────────────────────────

export function DeleteUserDialog({ user, onCompleted }: { user: IAdminUser; onCompleted: () => void }) {
  const acao = useAcaoDeDialogo(() => GisFlowService.adminDeleteUser(user.id_hash), {
    sucesso: `Usuário «${user.username}» excluído.`,
    erro: mensagem => mensagem ?? "Erro ao excluir usuário.",
    aoConcluir: onCompleted,
  })

  return (
    <Dialog open={acao.aberto} onOpenChange={acao.setAberto}>
      <DialogTrigger asChild>
        <DropdownMenuItem
          className="text-destructive focus:text-destructive"
          onSelect={e => { e.preventDefault(); acao.setAberto(true) }}
        >
          <TbTrash className="mr-2" aria-hidden="true" /> Excluir
        </DropdownMenuItem>
      </DialogTrigger>
      <DeleteDialog
        className="max-w-md"
        title="Excluir usuário"
        description={
          <>
            Esta ação marca o usuário como excluído (soft delete). Para confirmar, digite o nome:
            <code className="block mt-2 bg-muted px-2 py-1 rounded font-mono text-sm select-all">
              {user.username}
            </code>
          </>
        }
        confirmarDigitando={user.username}
        onConfirm={acao.executar}
      />
    </Dialog>
  )
}

// ── Diálogo: Alterar role ──────────────────────────────────────────────────────

export function ChangeRoleDialog({ user, onCompleted }: { user: IAdminUser; onCompleted: () => void }) {
  const [newRole, setNewRole] = useState(user.role === "admin" ? "user" : "admin")
  const acao = useAcaoDeDialogo(() => GisFlowService.updateUserRole(user.id_hash, newRole), {
    sucesso: `Role de «${user.username}» alterado para ${newRole === "admin" ? "admin" : "usuário"}.`,
    erro: mensagem => mensagem ?? "Erro ao alterar role.",
    aoConcluir: onCompleted,
  })

  return (
    <Dialog open={acao.aberto} onOpenChange={acao.setAberto}>
      <DialogTrigger asChild>
        <DropdownMenuItem onSelect={e => { e.preventDefault(); acao.setAberto(true) }}>
          <TbUserShield className="mr-2" aria-hidden="true" /> Alterar role
        </DropdownMenuItem>
      </DialogTrigger>
      <DialogContent className="max-w-sm" bloqueado={acao.executando}>
        <DialogHeader>
          <DialogTitle>Alterar role</DialogTitle>
          <DialogDescription>
            Alterar o role de <span className="font-semibold text-foreground">«{user.username}»</span>.
          </DialogDescription>
        </DialogHeader>
        <div className="py-2">
          <Select value={newRole} onValueChange={setNewRole}>
            <SelectTrigger className="max-md:h-10">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="admin">Admin</SelectItem>
              <SelectItem value="user">Usuário</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <DialogFooter>
          <Button variant="outline" className="max-md:h-10" disabled={acao.executando} onClick={() => acao.setAberto(false)}>Cancelar</Button>
          <Button className="max-md:h-10" disabled={acao.executando || newRole === user.role} onClick={acao.executar}>
            {acao.executando ? "Alterando…" : "Confirmar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Diálogo: Cota de executores ────────────────────────────────────────────────

export function ChangeAgentQuotaDialog({ user, onCompleted }: { user: IAdminUser; onCompleted: () => void }) {
  const [quota, setQuota] = useState(user.agent_quota)
  const acao = useAcaoDeDialogo(() => GisFlowService.updateUserAgentQuota(user.id_hash, quota), {
    sucesso: `Cota de executores de «${user.username}» definida para ${quota}.`,
    erro: mensagem => mensagem ?? "Erro ao alterar cota de executores.",
    aoConcluir: onCompleted,
  })
  const open = acao.aberto

  // Estatísticas pegas ao abrir o diálogo — usadas para avisar quando reduzir
  // a cota deixa executores existentes "órfãos" e oferecer revogação em lote.
  const [created, setCreated]           = useState<number | null>(null)
  const [statsLoading, setStatsLoading] = useState(false)
  const [revokeOpen, setRevokeOpen]     = useState(false)

  function handleClose(val: boolean) {
    if (!val) { setQuota(user.agent_quota); setCreated(null) }
    acao.setAberto(val)
  }

  // Carrega stats ao abrir
  useEffect(() => {
    if (!open) return
    setStatsLoading(true)
    GisFlowService.getUserAgentStats(user.id_hash).then(res => {
      if (res.data) setCreated(res.data.created)
      setStatsLoading(false)
    })
  }, [open, user.id_hash])

  // O botão e o Enter com a mesma regra: a cota atual não tem o que salvar.
  const podeSalvar = quota !== user.agent_quota

  // Cota baixa demais para acomodar todos os executores existentes.
  const reducingBelowExisting = created != null && quota < created

  return (
    <>
      <Dialog open={open} onOpenChange={handleClose}>
        <DialogTrigger asChild>
          <DropdownMenuItem onSelect={e => { e.preventDefault(); acao.setAberto(true) }}>
            <TbServer className="mr-2" aria-hidden="true" /> Cota de executores
          </DropdownMenuItem>
        </DialogTrigger>
        <DialogContent className="max-w-sm" bloqueado={acao.executando}>
          <DialogHeader>
            <DialogTitle>Cota de executores</DialogTitle>
            <DialogDescription>
              Quantos executores dedicados <span className="font-semibold text-foreground">«{user.username}»</span> pode
              criar. <span className="font-medium text-foreground">0</span> bloqueia a criação.
            </DialogDescription>
          </DialogHeader>

          <div className="py-2 flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="executor-quota">Limite de executores dedicados</Label>
              <Input
                id="executor-quota"
                type="number"
                min={0}
                max={100}
                value={quota}
                onChange={e => setQuota(Math.max(0, Math.min(100, Number(e.target.value))))}
                onKeyDown={e => e.key === "Enter" && podeSalvar && acao.executar()}
                className="tabular-nums max-md:h-10"
              />
              <p className="text-xs text-muted-foreground">
                {statsLoading
                  ? "Carregando uso atual…"
                  : created != null
                    ? <>Atualmente possui <span className="font-medium text-foreground tabular-nums">{created}</span> {created === 1 ? "executor próprio ativo" : "executores próprios ativos"}.</>
                    : null}
              </p>
            </div>

            {reducingBelowExisting && (
              // Aviso âmbar canônico do contrato (§3.4): par claro/escuro sancionado.
              <div className="flex items-start gap-2 rounded-md border border-amber-500/30 bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:bg-amber-500/10 dark:text-amber-400">
                <TbAlertTriangle className="shrink-0 mt-0.5" size={14} aria-hidden="true" />
                <div className="flex flex-col gap-1.5">
                  <p>
                    Reduzindo para <span className="font-medium tabular-nums">{quota}</span>, mas o
                    usuário tem <span className="font-medium tabular-nums">{created}</span> {created === 1 ? "executor" : "executores"}.
                    Os existentes <span className="font-medium">continuam ativos</span> e ele os mantém.
                  </p>
                  <p className="text-muted-foreground">
                    Para também revogar acesso aos existentes (caso esteja removendo o operador):
                  </p>
                  <Button
                    type="button"
                    variant="destructive"
                    size="sm"
                    className="h-8 px-2 text-xs self-start max-md:h-10"
                    disabled={acao.executando}
                    onClick={() => setRevokeOpen(true)}
                  >
                    <TbShieldOff className="mr-1.5 size-3.5" aria-hidden="true" />
                    Revogar todos ({created})
                  </Button>
                </div>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" className="max-md:h-10" disabled={acao.executando} onClick={() => handleClose(false)}>Cancelar</Button>
            <Button className="max-md:h-10" disabled={acao.executando || !podeSalvar} onClick={acao.executar}>
              {acao.executando ? "Salvando…" : "Salvar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <RevokeAllAgentsDialog
        open={revokeOpen}
        onOpenChange={setRevokeOpen}
        user={user}
        count={created ?? 0}
        targetQuota={quota}
        onCompleted={() => {
          setRevokeOpen(false)
          acao.setAberto(false)
          onCompleted()
        }}
      />
    </>
  )
}

// ── Sub-diálogo: Revogar todos os executores do usuário ─────────────────────────

function RevokeAllAgentsDialog({
  open, onOpenChange, user, count, targetQuota, onCompleted,
}: {
  open: boolean
  onOpenChange: (val: boolean) => void
  user: IAdminUser
  count: number
  targetQuota: number
  onCompleted: () => void
}) {
  const acao = useAcaoDeDialogo(async () => {
    // Sequência segura: cota PRIMEIRO (fecha a janela de criar executor novo
    // durante a revogação), depois revoke-all.
    const quotaRes = await GisFlowService.updateUserAgentQuota(user.id_hash, targetQuota)
    if (quotaRes.error) {
      return { error: { name: "cota", message: "Erro ao atualizar cota — abortando revogação." } }
    }
    const revRes = await GisFlowService.revokeAllUserAgents(user.id_hash)
    // Sem corpo também é falha: o toast de sucesso é feito das contagens.
    return revRes.error || revRes.data ? revRes : { error: { name: "sem-corpo" } }
  }, {
    sucesso: ({ revoked_count, affected_workspaces }) =>
      `${plural(revoked_count, "executor", "executores")} revogado${revoked_count === 1 ? "" : "s"} · ${plural(affected_workspaces, "workspace")} no pool default.`,
    erro: mensagem => mensagem ?? "Erro ao revogar executores.",
    aoConcluir: onCompleted,
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DeleteDialog
        className="max-w-md"
        title={
          <span className="flex items-center gap-2">
            <TbShieldOff className="text-destructive" aria-hidden="true" />
            Revogar todos os executores
          </span>
        }
        description={
          <>
            Esta ação encerra e invalida o cert mTLS de{" "}
            <span className="font-semibold text-foreground tabular-nums">{count}</span> {count === 1 ? "executor criado" : "executores criados"}
            {" "}por <span className="font-semibold text-foreground">«{user.username}»</span>.
          </>
        }
        confirmarDigitando="REVOGAR"
        rotuloDigitando={<>Para confirmar, digite <span className="font-mono font-medium">REVOGAR</span>:</>}
        confirmLabel={`Revogar ${count} ${count === 1 ? "executor" : "executores"}`}
        loadingLabel="Revogando…"
        onConfirm={acao.executar}
      >
        <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs space-y-1.5">
          <p className="flex items-start gap-2">
            <TbAlertTriangle className="text-destructive shrink-0 mt-0.5" aria-hidden="true" />
            <span>
              Jobs em execução nesses executores continuam até terminar. Jobs enfileirados localmente
              são descartados. Workspaces que apontam para algum desses executores caem no pool default.
            </span>
          </p>
          <p className="text-muted-foreground pl-5">
            A cota será definida para <span className="font-medium text-foreground tabular-nums">{targetQuota}</span> antes
            da revogação, impedindo criação durante o processo.
          </p>
        </div>
      </DeleteDialog>
    </Dialog>
  )
}

// ── Diálogo: Ação em massa ──────────────────────────────────────────────────────

export function BulkActionDialog({ action, userIds, onCompleted, onClose }: {
  action: "suspend" | "reactivate" | "delete"
  userIds: string[]
  onCompleted: () => void
  onClose: () => void
}) {
  const labels = {
    suspend:    { title: "Suspender em massa",  btn: "Suspender",  btnLoading: "Suspendendo…", variant: "default" as const },
    reactivate: { title: "Reativar em massa",   btn: "Reativar",   btnLoading: "Reativando…",  variant: "default" as const },
    delete:     { title: "Excluir em massa",    btn: "Excluir",    btnLoading: "Excluindo…",   variant: "destructive" as const },
  }
  const label = labels[action]

  const acao = useAcaoDeDialogo(() => {
    const fn = action === "suspend"
      ? GisFlowService.bulkSuspendUsers
      : action === "reactivate"
        ? GisFlowService.bulkReactivateUsers
        : GisFlowService.bulkDeleteUsers
    return fn(userIds)
  }, {
    // Com falha parcial o toast é de erro (abaixo), não de sucesso.
    sucesso: d => (d && d.errors.length === 0
      ? `${plural(d.processed, "usuário")} processado${d.processed === 1 ? "" : "s"}.`
      : null),
    erro: () => "Erro na operação em massa.",
    aoConcluir: d => {
      if (!d) return
      if (d.errors.length > 0) {
        const firstReason = (d.errors[0] as { error?: string })?.error
        const suffix = firstReason
          ? d.errors.length === 1
            ? ` — ${firstReason}`
            : ` — ${firstReason} (e ${plural(d.errors.length - 1, "outro")})`
          : ""
        createToast.error(`${plural(d.processed, "processado")}, ${plural(d.errors.length, "erro")}${suffix}`)
      }
      onCompleted()
    },
  })

  // Fecha com sucesso ou com falha — como sempre fechou.
  async function handleBulk() {
    await acao.executar()
    onClose()
  }

  return (
    <Dialog open onOpenChange={(v) => { if (!v) onClose() }}>
      <DialogContent className="max-w-sm" bloqueado={acao.executando}>
        <DialogHeader>
          <DialogTitle>{label.title}</DialogTitle>
          <DialogDescription>
            Esta ação será aplicada a <span className="font-semibold text-foreground tabular-nums">{userIds.length}</span> {userIds.length === 1 ? "usuário" : "usuários"}.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" className="max-md:h-10" disabled={acao.executando} onClick={onClose}>Cancelar</Button>
          <Button variant={label.variant} className="max-md:h-10" disabled={acao.executando} onClick={handleBulk}>
            {acao.executando ? label.btnLoading : label.btn}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
