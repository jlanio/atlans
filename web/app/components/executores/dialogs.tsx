"use client"

// Executor management dialogs: create (2 steps), edit, revoke and remove,
// plus the primitives they share (SelectCard, Stepper) and the policy
// conflict warning.
//
// STANDARDIZATION, not a rewrite: the 2-step creation flow, the Stepper, the
// type-to-confirm of revocation, the policy conflict's `force` and all the API
// calls remain intact. Only the presentation was aligned: tokens, visible
// focus and motion under `motion-safe:`. Edit, revoke and remove follow the
// common cycle of action dialogs (`useAcaoDeDialogo`), and the two
// destructive ones are `DeleteDialog`: Enter and click go through the same lock.

import React, { useState } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import type { IExecutor, IExecutorCreatedResponse } from "@/service/GisFlowService"
import type { IExecutorEnrollmentOtpResponse, IResponse } from "@/service/types"
import { cn } from "@/lib/utils"
import { useAcaoDeDialogo } from "@/app/hooks/useAcaoDeDialogo"
import { DeleteDialog } from "@/app/components/shared/DeleteDialog"
import { Button } from "@/app/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/app/components/ui/dialog"
import { Input } from "@/app/components/ui/input"
import { Badge } from "@/app/components/ui/badge"
import { Label } from "@/app/components/ui/label"
import { DropdownMenuItem } from "@/app/components/ui/dropdown-menu"
import { createToast } from "@/utils/createToast"
import {
  TbPlus, TbCheck, TbInfoCircle, TbShieldOff, TbTrash, TbPencil,
  TbShieldLock, TbAlertTriangle, TbLock, TbWorld, TbSettings,
  TbChevronRight, TbArrowRight,
} from "react-icons/tb"
import { EnrollConnect } from "./enroll"

// ── Selectable card (executor type / connection method) ─────────────────────

export function SelectCard({ active, onClick, icon, title, desc, badge }: {
  active: boolean
  onClick?: () => void
  icon: React.ReactNode
  title: string
  desc: string
  badge?: string
}) {
  const clickable = !!onClick
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "flex items-start gap-2.5 rounded-lg border px-3 py-2.5 text-left outline-none transition-colors",
        "focus-visible:ring-[3px] focus-visible:ring-ring/50",
        active ? "border-primary bg-primary/10" : "border-border bg-transparent",
        clickable && !active && "hover:border-primary/40 hover:bg-muted/40",
        !clickable && "cursor-default",
      )}
    >
      <span className={cn(
        "flex size-7 shrink-0 items-center justify-center rounded-md border bg-background text-base",
        active ? "border-primary/30 text-primary" : "border-border text-muted-foreground",
      )}>
        {icon}
      </span>
      <span className="min-w-0">
        <span className="flex items-center gap-1.5 text-sm font-semibold text-foreground">
          {title}
          {badge && (
            <Badge variant="secondary" className="px-1.5 py-0 text-[9px] font-semibold uppercase tracking-wide">
              {badge}
            </Badge>
          )}
        </span>
        <span className="mt-0.5 block text-xs leading-snug text-muted-foreground">{desc}</span>
      </span>
    </button>
  )
}

// ── Step indicator ───────────────────────────────────────────────────────────

function Stepper({ steps, current }: { steps: string[]; current: number }) {
  return (
    <div className="flex items-center px-0.5 pb-3.5 pt-1">
      {steps.map((label, i) => {
        const n = i + 1
        const done = n < current
        const active = n === current
        const isLast = n === steps.length
        return (
          <div key={label} className={cn("flex items-center gap-2", isLast ? "flex-none" : "flex-1")}>
            <span
              className={cn(
                "flex size-6 shrink-0 items-center justify-center rounded-full border font-mono text-[11px] font-semibold transition-colors",
                active && "border-primary bg-primary text-primary-foreground ring-4 ring-primary/15",
                done && "border-primary bg-primary/10 text-primary",
                !active && !done && "border-border bg-muted text-muted-foreground",
              )}
            >
              {done ? <TbCheck className="size-3.5" aria-hidden="true" /> : n}
            </span>
            <span
              className={cn(
                "whitespace-nowrap text-xs font-semibold",
                active ? "inline" : "hidden sm:inline",
                active ? "text-foreground" : "text-muted-foreground",
              )}
            >
              {label}
            </span>
            {!isLast && (
              <span className={cn("h-0.5 flex-1 rounded-full", done ? "bg-primary" : "bg-border")} />
            )}
          </div>
        )
      })}
    </div>
  )
}

/**
 * Execution policy 409: the executor is the ONLY primary of the listed
 * workspaces. Without this the admin saw a generic toast and had no way to
 * purge an old executor; with this they know the cost and decide.
 */
export function PolicyConflict({ workspaces, acao }: { workspaces: string[]; acao: "revogar" | "remover" }) {
  return (
    <p
      role="alert"
      className="flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs"
    >
      <TbAlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-700 dark:text-amber-400" aria-hidden="true" />
      <span>
        Este executor é o único principal da política de execução de{" "}
        <span className="font-medium">{workspaces.join(", ") || "alguns workspaces"}</span>.
        {" "}Ao {acao} mesmo assim, esses workspaces voltam ao pool compartilhado (a reserva deles
        também sai) e os donos são avisados por e-mail.
      </span>
    </p>
  )
}

// ── Creation dialog ───────────────────────────────────────────────────────────

export function CreateAgentDialog({ onCreated, executores, isAdmin, quota, ownedCount }: {
  onCreated: () => void
  executores: IExecutor[]
  isAdmin: boolean
  quota: number
  ownedCount: number
}) {
  const [open, setOpen]               = useState(false)
  const [step, setStep]               = useState<1 | 2>(1)
  const [name, setName]               = useState("")
  const [description, setDescription] = useState("")
  const [executorType, setExecutorType] = useState<"default" | "dedicated">("dedicated")
  const [loading, setLoading]         = useState(false)   // executor creation
  const [generating, setGenerating]   = useState(false)   // OTP generation
  const [created, setCreated]         = useState<IExecutorCreatedResponse | null>(null)
  const [otp, setOtp]                 = useState<IExecutorEnrollmentOtpResponse | null>(null)

  const defaultCount = executores.filter(a => a.executor_type === "default").length
  // Usuario comum: so cria dedicado e limitado pela cota individual.
  const quotaReached = !isAdmin && ownedCount >= quota
  const effectiveType: "default" | "dedicated" = isAdmin ? executorType : "dedicated"

  function handleClose(val: boolean) {
    if (!val) {
      const wasCreated = !!created
      setStep(1); setName(""); setDescription(""); setExecutorType("dedicated")
      setCreated(null); setOtp(null)
      setLoading(false); setGenerating(false)
      // The list only needs to reload if an executor actually got created.
      if (wasCreated) onCreated()
    }
    setOpen(val)
  }

  async function genOtp(execId: string) {
    setGenerating(true)
    const res = await GisFlowService.generateEnrollmentOtp(execId)
    setGenerating(false)
    if (res.error || !res.data) {
      createToast.error("Erro ao gerar OTP.", res.error?.message)
      return
    }
    setOtp(res.data)
  }

  async function handleCreate() {
    if (!name.trim() || loading) return
    setLoading(true)
    // capabilities, max_concurrent_jobs and max_queue_size are controlled by the
    // executor itself (EXECUTOR_MAX_CONCURRENT / EXECUTOR_MAX_QUEUE_SIZE in the
    // host's .env) — the backend accepts defaults if we don't send them.
    const res = await GisFlowService.createAgent({
      name: name.trim(),
      description: description.trim() || undefined,
      executor_type: effectiveType,
    })
    setLoading(false)
    if (res.error || !res.data) {
      createToast.error(res.error?.message ?? "Erro ao criar executor.")
      return
    }
    const c = res.data as IExecutorCreatedResponse
    setCreated(c)
    setStep(2)
    // Generates the OTP right after — the "Ativar" (activate) step already opens with it ready.
    genOtp(c.executor_id)
  }

  const canCreate = !!name.trim() && !loading && !quotaReached

  const META: Record<1 | 2, { t: string; d: string }> = {
    1: { t: "Registrar executor", d: "Nome e tipo. Os limites de execução vêm do host do executor." },
    2: { t: "Conectar o executor", d: "Escolha como rodar — na sua máquina ou na do operador. O app e os comandos já trazem o vínculo pronto." },
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogTrigger asChild>
        <Button className="max-md:h-10"><TbPlus className="mr-1.5" aria-hidden="true" /> Novo executor</Button>
      </DialogTrigger>

      {/* Locked only during creation: closing midway left the created executor
          out of the list and the dialog, on reopening, at step 2. */}
      <DialogContent bloqueado={loading}>
        <DialogHeader className="pr-6">
          <DialogTitle>{META[step].t}</DialogTitle>
          <DialogDescription>{META[step].d}</DialogDescription>
        </DialogHeader>

        <Stepper steps={["Configurar", "Conectar"]} current={step} />

        {/* `min-w-0`: child of the DialogContent grid. Without this, wide content
            (the Docker command of the Conectar step) forces the grid width above
            `max-w-lg` and overflows/clips the modal instead of fitting. */}
        <div key={step} className="min-w-0 motion-safe:animate-in motion-safe:fade-in-0 motion-safe:duration-200">
          {/* ── Step 1: Configurar ─────────────────────────────────────────── */}
          {step === 1 && (
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="ag-name">Nome *</Label>
                <Input
                  id="ag-name"
                  placeholder="ex: executor-producao-01"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && canCreate && handleCreate()}
                  autoFocus
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <Label>Tipo *</Label>
                {isAdmin ? (
                  <>
                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                      <SelectCard
                        active={executorType === "dedicated"}
                        onClick={() => setExecutorType("dedicated")}
                        icon={<TbLock />}
                        title="Dedicado"
                        desc="Só os seus workflows, isolado."
                      />
                      <SelectCard
                        active={executorType === "default"}
                        onClick={() => setExecutorType("default")}
                        icon={<TbWorld />}
                        title="Padrão"
                        desc="Pool compartilhado do workspace."
                      />
                    </div>
                    {executorType === "default" && defaultCount > 0 && (
                      <p className="flex items-center gap-1 text-xs text-muted-foreground">
                        <TbInfoCircle size={14} aria-hidden="true" />
                        Pool padrão atual: {defaultCount} executor(es).
                      </p>
                    )}
                  </>
                ) : (
                  <SelectCard
                    active
                    icon={<TbLock />}
                    title="Dedicado"
                    desc={`Só os seus workflows. Você usou ${ownedCount} de ${quota} da sua cota.`}
                  />
                )}
                {quotaReached && (
                  <p className="flex items-center gap-1 text-xs text-destructive">
                    <TbAlertTriangle size={14} aria-hidden="true" />
                    Você atingiu sua cota de executores dedicados.
                  </p>
                )}
              </div>

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="ag-desc">Descrição</Label>
                <Input
                  id="ag-desc"
                  placeholder="Opcional — ex.: máquina da sala 2, GPU"
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                />
              </div>

              <details className="group rounded-lg border border-border bg-muted/30">
                <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2 text-xs font-semibold text-muted-foreground [&::-webkit-details-marker]:hidden">
                  <TbSettings className="size-3.5" aria-hidden="true" />
                  Limites de execução paralela e fila
                  <TbChevronRight className="ml-auto size-3.5 transition-transform group-open:rotate-90" aria-hidden="true" />
                </summary>
                <div className="px-3 pb-2.5 text-xs leading-relaxed text-muted-foreground">
                  Configurados no host via{" "}
                  <code className="rounded bg-muted px-1 font-mono">EXECUTOR_MAX_CONCURRENT</code> e{" "}
                  <code className="rounded bg-muted px-1 font-mono">EXECUTOR_MAX_QUEUE_SIZE</code> no{" "}
                  <code className="rounded bg-muted px-1 font-mono">.env</code>. O servidor respeita o
                  que o executor reporta ao vivo — nada a preencher aqui.
                </div>
              </details>
            </div>
          )}

          {/* ── Step 2: Conectar ───────────────────────────────────────────── */}
          {step === 2 && (
            generating && !otp ? (
              <div className="py-10 text-center text-sm text-muted-foreground">Preparando o vínculo…</div>
            ) : otp ? (
              <EnrollConnect otp={otp} />
            ) : (
              <div className="flex flex-col items-start gap-3 py-8">
                <div className="flex items-start gap-2 text-sm text-muted-foreground">
                  <TbAlertTriangle className="mt-0.5 shrink-0 text-amber-700 dark:text-amber-400" aria-hidden="true" />
                  <span>Executor criado, mas o vínculo ainda não foi gerado.</span>
                </div>
                <Button size="sm" onClick={() => created && genOtp(created.executor_id)} disabled={generating}>
                  <TbShieldLock className="mr-1.5" aria-hidden="true" /> {generating ? "Gerando…" : "Gerar vínculo"}
                </Button>
              </div>
            )
          )}
        </div>

        <DialogFooter className="border-t border-border pt-4">
          {step === 1 && (
            <Button onClick={handleCreate} disabled={!canCreate} className="gap-1.5">
              {loading ? "Criando…" : <>Criar executor <TbArrowRight className="size-4" aria-hidden="true" /></>}
            </Button>
          )}
          {step === 2 && (
            <Button onClick={() => handleClose(false)}>Concluir</Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Edit dialog ──────────────────────────────────────────────────────────────

export function EditAgentDialog({ executor, onUpdated }: { executor: IExecutor; onUpdated: () => void }) {
  const [name, setName]               = useState(executor.name)
  const [description, setDescription] = useState(executor.description ?? "")
  const acao = useAcaoDeDialogo(() => GisFlowService.updateAgent(executor.id_hash, {
    name: name.trim(),
    description: description.trim() || undefined,
  }), {
    sucesso: "Executor atualizado.",
    erro: () => "Erro ao salvar alterações.",
    aoConcluir: onUpdated,
  })

  // The button and Enter follow the same rule: a name with at least 2 characters.
  const canSave = name.trim().length >= 2

  function handleClose(val: boolean) {
    if (!val) { setName(executor.name); setDescription(executor.description ?? "") }
    acao.setAberto(val)
  }

  return (
    <Dialog open={acao.aberto} onOpenChange={handleClose}>
      <DialogTrigger asChild>
        <DropdownMenuItem onSelect={e => { e.preventDefault(); acao.setAberto(true) }}>
          <TbPencil className="mr-2" aria-hidden="true" /> Editar executor
        </DropdownMenuItem>
      </DialogTrigger>

      <DialogContent className="max-w-md" bloqueado={acao.executando}>
        <DialogHeader>
          <DialogTitle>Editar executor</DialogTitle>
          <DialogDescription>Altere o nome ou a descrição do executor.</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4 py-1">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="edit-ag-name">Nome *</Label>
            <Input
              id="edit-ag-name"
              value={name}
              onChange={e => setName(e.target.value)}
              onKeyDown={e => e.key === "Enter" && canSave && acao.executar()}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="edit-ag-desc">Descrição</Label>
            <Input
              id="edit-ag-desc"
              placeholder="Opcional"
              value={description}
              onChange={e => setDescription(e.target.value)}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" disabled={acao.executando} onClick={() => handleClose(false)}>Cancelar</Button>
          <Button onClick={acao.executar} disabled={!canSave || acao.executando}>
            {acao.executando ? "Salvando…" : "Salvar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Revoke and remove: the policy 409 ────────────────────────────────────────

/**
 * The action cycle of revoke and remove, with the execution policy 409 in
 * place of a toast: this executor is the ONLY primary of some workspace.
 * The screen says WHICH ones (`PolicyConflict`) and the next confirmation
 * goes with `force` — the "… mesmo assim" (anyway). A single copy for both
 * dialogs, which repeated this handling line by line.
 *
 * The conflict is not cleared on close (as before): reopening shows the
 * warning from the previous attempt and already offers the "mesmo assim".
 */
function useActionWithConflict(
  acao: (force: boolean) => Promise<IResponse<unknown>>,
  textos: { sucesso: string; erro: string; aoConcluir: () => void },
) {
  const [conflito, setConflict] = useState<string[] | null>(null)
  const dialogo = useAcaoDeDialogo(() => acao(conflito !== null), {
    sucesso: textos.sucesso,
    erro: (mensagem, erro) => {
      if (erro.code !== "workspace_policy_conflict") return [textos.erro, mensagem]
      setConflict((erro.workspaces ?? []).map(w => w.workspace_name))
      return null
    },
    aoConcluir: () => {
      setConflict(null)
      textos.aoConcluir()
    },
  })
  return { ...dialogo, conflito }
}

// ── Revocation dialog ─────────────────────────────────────────────────────────

export function RevokeAgentDialog({ executor, onRevoked }: { executor: IExecutor; onRevoked: () => void }) {
  const acao = useActionWithConflict(
    force => GisFlowService.revokeAgent(executor.id_hash, force),
    { sucesso: "Executor revogado.", erro: "Erro ao revogar executor", aoConcluir: onRevoked },
  )

  return (
    <Dialog open={acao.aberto} onOpenChange={acao.setAberto}>
      <DialogTrigger asChild>
        <DropdownMenuItem
          className="text-destructive focus:text-destructive"
          onSelect={e => { e.preventDefault(); acao.setAberto(true) }}
        >
          <TbShieldOff className="mr-2" aria-hidden="true" /> Revogar executor
        </DropdownMenuItem>
      </DialogTrigger>

      <DeleteDialog
        className="max-w-md"
        title="Revogar executor"
        description={
          <>
            Esta ação impede o executor de conectar. Para confirmar, digite o nome do executor:
            <code className="mt-2 block select-all rounded bg-muted px-2 py-1 font-mono text-sm">
              {executor.name}
            </code>
          </>
        }
        confirmarDigitando={executor.name}
        confirmLabel={acao.conflito ? "Revogar mesmo assim" : "Revogar"}
        loadingLabel="Revogando…"
        onConfirm={acao.executar}
      >
        {acao.conflito && (
          <PolicyConflict workspaces={acao.conflito} acao="revogar" />
        )}
      </DeleteDialog>
    </Dialog>
  )
}

// ── Removal dialog (soft-delete) ─────────────────────────────────────────────

export function DeleteAgentDialog({ executor, onDeleted }: { executor: IExecutor; onDeleted: () => void }) {
  const acao = useActionWithConflict(
    force => GisFlowService.deleteAgent(executor.id_hash, force),
    { sucesso: "Executor removido.", erro: "Erro ao remover executor", aoConcluir: onDeleted },
  )

  return (
    <Dialog open={acao.aberto} onOpenChange={acao.setAberto}>
      <DialogTrigger asChild>
        <DropdownMenuItem
          className="text-destructive focus:text-destructive"
          onSelect={e => { e.preventDefault(); acao.setAberto(true) }}
        >
          <TbTrash className="mr-2" aria-hidden="true" /> Remover executor
        </DropdownMenuItem>
      </DialogTrigger>

      <DeleteDialog
        className="max-w-sm"
        title="Remover executor"
        description={
          <>
            O executor <span className="font-semibold text-foreground">{executor.name}</span> será
            ocultado permanentemente. O histórico de execuções é preservado, mas o executor
            não poderá ser reativado.
          </>
        }
        confirmLabel={acao.conflito ? "Remover mesmo assim" : "Remover"}
        loadingLabel="Removendo…"
        onConfirm={acao.executar}
      >
        {acao.conflito && (
          <PolicyConflict workspaces={acao.conflito} acao="remover" />
        )}
      </DeleteDialog>
    </Dialog>
  )
}
