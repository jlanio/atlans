"use client"

// Diálogos de gestão do executor: criar (2 passos), editar, revogar e remover,
// mais os primitivos que eles compartilham (SelectCard, Stepper) e o aviso de
// conflito de política.
//
// PADRONIZAÇÃO, não reescrita: o fluxo de criação em 2 passos, o Stepper, a
// confirmação por digitação da revogação, o `force` do conflito de política e
// todas as chamadas de API permanecem intactos. Só a apresentação foi alinhada:
// tokens, foco visível e movimento sob `motion-safe:`. Editar, revogar e
// remover seguem o ciclo comum dos diálogos de ação (`useAcaoDeDialogo`), e os
// dois destrutivos são `DeleteDialog`: Enter e clique passam pela mesma trava.

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

// ── Card selecionável (tipo de executor / método de conexão) ────────────────

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

// ── Indicador de passos ──────────────────────────────────────────────────────

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
 * 409 da política de execução: o executor é o ÚNICO principal dos workspaces
 * listados. Sem isto o admin via um toast genérico e não tinha como purgar
 * um executor antigo; com isto ele sabe o custo e decide.
 */
export function ConflitoDePolitica({ workspaces, acao }: { workspaces: string[]; acao: "revogar" | "remover" }) {
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

// ── Dialog de criação ─────────────────────────────────────────────────────────

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
  const [loading, setLoading]         = useState(false)   // criacao do executor
  const [generating, setGenerating]   = useState(false)   // geracao do OTP
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
      // A lista so precisa recarregar se um executor chegou a ser criado.
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
    // capabilities, max_concurrent_jobs e max_queue_size sao controlados pelo
    // proprio executor (EXECUTOR_MAX_CONCURRENT / EXECUTOR_MAX_QUEUE_SIZE no .env
    // do host) — o backend aceita defaults se nao enviarmos.
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
    // Gera o OTP na sequencia — o passo "Ativar" ja abre com ele pronto.
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

      {/* Travado só durante a criação: fechar no meio dela deixava o executor
          criado fora da lista e o diálogo, ao reabrir, no passo 2. */}
      <DialogContent bloqueado={loading}>
        <DialogHeader className="pr-6">
          <DialogTitle>{META[step].t}</DialogTitle>
          <DialogDescription>{META[step].d}</DialogDescription>
        </DialogHeader>

        <Stepper steps={["Configurar", "Conectar"]} current={step} />

        {/* `min-w-0`: filho do grid do DialogContent. Sem isto, um conteúdo largo
            (o comando Docker do passo Conectar) força a largura do grid acima do
            `max-w-lg` e estoura/recorta o modal em vez de caber. */}
        <div key={step} className="min-w-0 motion-safe:animate-in motion-safe:fade-in-0 motion-safe:duration-200">
          {/* ── Passo 1: Configurar ─────────────────────────────────────────── */}
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

          {/* ── Passo 2: Conectar ───────────────────────────────────────────── */}
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

// ── Dialog de edição ─────────────────────────────────────────────────────────

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

  // O botão e o Enter com a mesma regra: nome com pelo menos 2 caracteres.
  const podeSalvar = name.trim().length >= 2

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
              onKeyDown={e => e.key === "Enter" && podeSalvar && acao.executar()}
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
          <Button onClick={acao.executar} disabled={!podeSalvar || acao.executando}>
            {acao.executando ? "Salvando…" : "Salvar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Revogar e remover: o 409 da política ─────────────────────────────────────

/**
 * O ciclo de ação de revogar e de remover, com o 409 da política de execução
 * no lugar de um toast: este executor é o ÚNICO principal de algum workspace.
 * A tela diz QUAIS (`ConflitoDePolitica`) e a confirmação seguinte vai com
 * `force` — o «… mesmo assim». Uma cópia só para os dois diálogos, que
 * repetiam este tratamento linha a linha.
 *
 * O conflito não é limpo ao fechar (como antes): reabrir mostra o aviso da
 * tentativa anterior e já oferece o «mesmo assim».
 */
function useAcaoComConflito(
  acao: (force: boolean) => Promise<IResponse<unknown>>,
  textos: { sucesso: string; erro: string; aoConcluir: () => void },
) {
  const [conflito, setConflito] = useState<string[] | null>(null)
  const dialogo = useAcaoDeDialogo(() => acao(conflito !== null), {
    sucesso: textos.sucesso,
    erro: (mensagem, erro) => {
      if (erro.code !== "workspace_policy_conflict") return [textos.erro, mensagem]
      setConflito((erro.workspaces ?? []).map(w => w.workspace_name))
      return null
    },
    aoConcluir: () => {
      setConflito(null)
      textos.aoConcluir()
    },
  })
  return { ...dialogo, conflito }
}

// ── Dialog de revogação ───────────────────────────────────────────────────────

export function RevokeAgentDialog({ executor, onRevoked }: { executor: IExecutor; onRevoked: () => void }) {
  const acao = useAcaoComConflito(
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
          <ConflitoDePolitica workspaces={acao.conflito} acao="revogar" />
        )}
      </DeleteDialog>
    </Dialog>
  )
}

// ── Dialog de remoção (soft-delete) ──────────────────────────────────────────

export function DeleteAgentDialog({ executor, onDeleted }: { executor: IExecutor; onDeleted: () => void }) {
  const acao = useAcaoComConflito(
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
          <ConflitoDePolitica workspaces={acao.conflito} acao="remover" />
        )}
      </DeleteDialog>
    </Dialog>
  )
}
