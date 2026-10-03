"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import {
  TbAlertTriangle, TbExternalLink, TbInfoCircle, TbLoader2, TbLock, TbPlus, TbRefresh, TbServer, TbX,
} from "react-icons/tb"
import { Badge } from "@/app/components/ui/badge"
import { Button } from "@/app/components/ui/button"
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/app/components/ui/dialog"
import { GisFlowService, IExecutor } from "@/service/GisFlowService"
import type { IPolicyMember, IWorkspacePolicy, PolicyTerminal } from "@/service/types"
import { createToast } from "@/utils/createToast"
import { cn } from "@/lib/utils"
import { ExecutorTypeBadge } from "@/app/components/executor-type-badge"
import { useFetchData } from "@/app/hooks/useFetchData"
import { SheetSection } from "./section-shell"
import {
  capacityFull, modeClass, countOnline, describeCapacity, describePolicy, politicaEmAlerta,
  modeLabel, rotuloDoStatus, poolHealth, noSignal, type Capacidade,
} from "../politica"

interface Props {
  workspaceId: string
  canManage: boolean
  /** Flags a policy in alert (inactive member, chain with no one online) for the navigation. */
  onAlertChange?: (hasAlert: boolean) => void
}

/** One operation in flight at a time: add/remove/terminal would trample each other on the same policy. */
type Operacao = `incluir:${string}` | `remover:${string}` | "terminal"

/**
 * Editor for the workspace's execution policy
 * (docs/specs/executor-isolation-routing.md, §9).
 *
 * Three blocks: the primary executors, the optional fallback and the last
 * resort — what happens when none of them is available: fail (default) or the
 * pool. Choosing the pool asks for confirmation because it changes where the
 * DATA runs; under a platform administrator's floor it is not even offered.
 * Removing the last primary also asks for confirmation: it erases the fallback
 * and returns the workspace to the pool.
 *
 * While the server does not route by the policy (flag off), the editor is a
 * preview and says so BEFORE anything else: promising isolation that the next
 * run does not have would be worse than not having the screen at all.
 */
export function ExecutorSection({ workspaceId, canManage, onAlertChange }: Props) {
  // Loading is `useFetchData`: concurrent loads (Refresh twice, retry,
  // switching workspaces) — only the most recent writes, and an earlier one
  // arriving later does not swap a freshly read policy for a stale snapshot.
  // The generation guard, which this section used to write by hand, is its
  // job. `firstLoad` is the skeleton; on reload the policy stays on screen.
  const { data, loading, firstLoad, error, refetch: load, setData } = useFetchData(
    async () => {
      const [polRes, myRes] = await Promise.all([
        GisFlowService.getWorkspacePolicy(workspaceId),
        GisFlowService.getMyAgents(),
      ])
      if (polRes.error || !polRes.data || myRes.error) {
        return { error: { message: polRes.error?.message ?? myRes.error?.message } }
      }
      // Keeps all of them (including pending/revoked): it is the list that gives
      // the NAME of the legacy pointer in the preview and why there are no candidates.
      return { data: { politica: polRes.data, executores: myRes.data ?? [] } }
    },
    "Não foi possível carregar a política de execução.",
    [workspaceId],
  )
  const politica = data?.politica ?? null
  const executores = useMemo<IExecutor[]>(() => data?.executores ?? [], [data])
  /** The policy a write returned (or the re-read): replaces only that. */
  const setPolicy = (nova: IWorkspacePolicy) => setData(atual => atual && { ...atual, politica: nova })
  const [operacao, setOperation] = useState<Operacao | null>(null)
  const [confirmPool, setConfirmPool] = useState(false)
  const [confirmRemoval, setConfirmRemoval] = useState<IPolicyMember | null>(null)

  const alerta = politica ? politicaEmAlerta(politica) : false
  useEffect(() => {
    if (!loading && !error) onAlertChange?.(alerta)
  }, [alerta, loading, error, onAlertChange])

  const emVigor = politica?.policy_routing_enabled === true
  const previewSuffix = emVigor ? "" : " (vale quando o roteamento por política for ativado)"

  /** Re-reads only the policy — DELETE answers 204, without the recomputed policy. */
  async function reloadPolicy(): Promise<IWorkspacePolicy | null> {
    const res = await GisFlowService.getWorkspacePolicy(workspaceId)
    if (res.error || !res.data) {
      // The removal succeeded; only the re-read failed. The success toast already
      // went out — the screen asks for a reload instead of turning into a full error.
      createToast.error("Não foi possível reler a política", "Clique em Atualizar.")
      return null
    }
    setPolicy(res.data)
    return res.data
  }

  async function incluir(executor: IExecutor, tier: 1 | 2) {
    if (operacao) return
    setOperation(`incluir:${executor.id_hash}`)
    const res = await GisFlowService.addWorkspacePolicyMember(workspaceId, executor.id_hash, tier)
    setOperation(null)
    if (res.error || !res.data) {
      createToast.error("Erro ao incluir o executor", res.error?.message)
      return
    }
    setPolicy(res.data)
    createToast.success(
      tier === 1
        ? `${executor.name} incluído entre os principais.`
        : `${executor.name} incluído como reserva.`,
    )
  }

  function requestRemoval(membro: IPolicyMember) {
    if (!politica) return
    const lastPrimary = membro.tier === 1 && politica.primary.length === 1
    // The last primary takes down the fallback and returns the workspace to the
    // pool: it is the sensitive direction (nothing → everything on shared machines).
    if (lastPrimary) { setConfirmRemoval(membro); return }
    remover(membro)
  }

  async function remover(membro: IPolicyMember) {
    if (operacao || !politica) return
    setConfirmRemoval(null)
    const wasLastPrimary = membro.tier === 1 && politica.primary.length === 1
    const hadFallback = politica.fallback.length > 0
    setOperation(`remover:${membro.id_hash}`)
    const res = await GisFlowService.removeWorkspacePolicyMember(workspaceId, membro.id_hash)
    if (res.error) {
      setOperation(null)
      createToast.error("Erro ao remover o executor", res.error.message)
      return
    }
    // Emptying the primary takes the fallback down with it (spec §4.3): only the
    // re-read shows what is left.
    await reloadPolicy()
    setOperation(null)
    if (wasLastPrimary) {
      createToast.success(
        `${membro.name} removido. O workspace voltou a usar o pool compartilhado.`
        + (hadFallback ? " Os executores de reserva também saíram." : ""),
      )
    } else {
      createToast.success(`${membro.name} removido da política.`)
    }
  }

  async function applyTerminal(terminal: PolicyTerminal, confirmado = false) {
    if (!politica || operacao) return
    if (terminal === politica.effective_terminal) return
    if (terminal === "pool" && !confirmado) { setConfirmPool(true); return }
    setConfirmPool(false)
    setOperation("terminal")
    const res = await GisFlowService.setWorkspaceFallback(workspaceId, terminal)
    setOperation(null)
    if (res.error || !res.data) {
      createToast.error("Erro ao alterar o último recurso", res.error?.message)
      return
    }
    setPolicy(res.data)
    createToast.success(
      (terminal === "pool"
        ? "O pool compartilhado passa a ser o último recurso."
        : "Sem último recurso: a execução falha quando nenhum executor da política estiver disponível.")
      + previewSuffix,
    )
  }

  const inPolicy = new Set(
    [...(politica?.primary ?? []), ...(politica?.fallback ?? [])].map(m => m.id_hash),
  )
  // Candidates: MY active dedicated executors that are not in any tier yet.
  // The pool is not a tier (spec Q3): `is_default` is left out.
  const dedicados = executores.filter(e => !e.is_default)
  const candidatos = dedicados.filter(e => e.status === "active" && !inPolicy.has(e.id_hash))
  const hasPrimary = (politica?.primary.length ?? 0) > 0
  const underFloor = politica?.isolation_floor === "no_pool"
  const ocupado = operacao !== null

  // Name of the legacy pointer, so the preview says what holds TODAY. In quotes:
  // an executor named "executor" left the sentence meaningless.
  const legacyName = politica?.target_executor_id
    ? executores.find(e => e.id_hash === politica.target_executor_id)?.name
    : undefined
  const legado = politica?.target_executor_id
    ? (legacyName
      ? `o executor «${legacyName}»`
      : "um executor que não está mais na sua lista (removido ou sem acesso)")
    : "o pool compartilhado"

  // Shared with no candidate: a single message, instead of five disabled
  // blocks. The whole editor screen presupposes a dedicated executor.
  const nothingToEdit = politica?.mode === "pool" && candidatos.length === 0 && !underFloor

  return (
    <>
      <SheetSection
        title="Política de execução"
        description={
          <>
            Em quais executores os workflows deste workspace rodam, e o que acontece quando eles caem.{" "}
            <span className="font-medium text-teal-600 dark:text-teal-400">Compartilhado</span> usa o
            pool da plataforma.{" "}
            <span className="font-medium text-purple-600 dark:text-purple-400">Isolado</span> roda só
            nos executores principais e de reserva deste workspace e falha quando nenhum está disponível.{" "}
            <span className="font-medium text-purple-600 dark:text-purple-400">Dedicado + pool</span>{" "}
            tenta os dedicados e usa o pool como último recurso.
            {!canManage && " Apenas administradores podem alterar."}
          </>
        }
        // Two wide actions (the "Gerenciar executores" link + Atualizar) in the
        // top-right corner squeezed the title in a narrow panel; they move down
        // to a line of their own, below the description.
        actionBelow
        action={
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              onClick={load}
              // Locked during a write: reloading in the middle of a change overwrote
              // the in-flight value and the success toast lied.
              disabled={loading || ocupado}
              aria-label="Atualizar política"
              title="Atualizar"
            >
              <TbRefresh className={`size-4 ${loading ? "animate-spin" : ""}`} />
            </Button>
            <Button variant="ghost" size="sm" asChild className="gap-1 text-xs text-muted-foreground">
              <Link href="/executores">
                Gerenciar executores
                <TbExternalLink className="size-3.5" />
              </Link>
            </Button>
          </div>
        }
        loading={firstLoad}
        error={error}
        onRetry={load}
      >
        {politica && (
          <div className="space-y-5">
            {/* ── Preview: BEFORE everything, because it changes the meaning of everything ── */}
            {!emVigor && (
              <p
                role="note"
                className="flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-foreground"
              >
                <TbInfoCircle className="mt-0.5 size-4 shrink-0 text-amber-700 dark:text-amber-400" aria-hidden="true" />
                <span>
                  <span className="font-semibold">Ainda não está em vigor.</span> Hoje as execuções
                  deste workspace vão para {legado}. O que você configurar aqui fica salvo e passa a
                  valer quando o administrador da plataforma ativar o roteamento por política.
                </span>
              </p>
            )}

            {/* ── Resumo ─────────────────────────────────────────────────── */}
            <div
              className={cn(
                "flex items-center gap-2 rounded-md border px-3 py-2 text-sm",
                alerta && "border-amber-500/40 bg-amber-500/5",
              )}
            >
              <div
                className={cn(
                  "flex size-7 shrink-0 items-center justify-center rounded-md",
                  alerta ? "bg-amber-500/15 text-amber-700 dark:text-amber-400" : "bg-accent",
                )}
              >
                {alerta
                  ? <TbAlertTriangle className="size-4" aria-hidden="true" />
                  : <TbServer className="size-4" aria-hidden="true" />}
              </div>
              <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-2 gap-y-1">
                <Badge
                  variant="outline"
                  className={cn("gap-1 px-1.5 py-0 text-[10px]", modeClass(politica.mode), !emVigor && "border-dashed")}
                >
                  {underFloor && <TbLock size={10} aria-hidden="true" />}
                  {modeLabel(politica.mode)}{!emVigor && " · prévia"}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {politica.mode === "pool"
                    ? (poolHealth(politica) ?? "Pool compartilhado")
                    : underFloor && !hasPrimary
                      ? "Sem executor principal: nada roda até você incluir um"
                      : describePolicy(politica)}
                </span>
              </div>
              {ocupado && (
                <TbLoader2 className="size-4 shrink-0 animate-spin text-muted-foreground" aria-hidden="true" />
              )}
            </div>

            {underFloor && (
              <p className="flex items-start gap-2 text-xs text-muted-foreground">
                <TbLock className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
                <span>
                  <span className="font-medium text-foreground">Isolamento obrigatório.</span> O
                  administrador da plataforma definiu que este workspace nunca usa o pool
                  compartilhado; o último recurso fica fixo em «Falhar a execução».
                </span>
              </p>
            )}

            {nothingToEdit ? (
              <div className="space-y-3 rounded-md border border-dashed px-4 py-4 text-sm">
                <p>
                  Este workspace usa o pool compartilhado: qualquer executor compartilhado assume as
                  execuções. Para isolar as execuções em máquinas só suas, você precisa de um{" "}
                  <span className="font-medium">executor dedicado</span>
                  {dedicados.length > 0 && " ativo"}.
                </p>
                {dedicados.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    Seus executores dedicados não estão ativos ({dedicados.map(e => `${e.name}: ${rotuloDoStatus(e.status)}`).join(", ")}).
                    Só executores ativos entram na política.
                  </p>
                )}
                {canManage && (
                  <Button variant="outline" size="sm" asChild>
                    <Link href="/executores">
                      <TbPlus size={14} aria-hidden="true" />
                      {dedicados.length > 0 ? "Ver meus executores" : "Criar executor dedicado"}
                    </Link>
                  </Button>
                )}
              </div>
            ) : (
              <>
                {/* ── Tiers ──────────────────────────────────────────────── */}
                <Nivel
                  titulo="Executores principais"
                  rotulo="principal"
                  membros={politica.primary}
                  disponiveis={politica.available_primary}
                  vazio={emVigor
                    ? "Nenhum executor principal: o workspace é Compartilhado e tudo roda no pool."
                    : "Nenhum executor principal. Inclua um abaixo para começar a política."}
                  canManage={canManage}
                  ocupado={ocupado}
                  operacao={operacao}
                  onRemover={requestRemoval}
                />
                {hasPrimary ? (
                  <Nivel
                    titulo="Executores de reserva"
                    rotulo="reserva"
                    membros={politica.fallback}
                    disponiveis={politica.available_fallback}
                    vazio="Sem reserva: se nenhum principal estiver disponível, vale o último recurso abaixo."
                    canManage={canManage}
                    ocupado={ocupado}
                    operacao={operacao}
                    onRemover={requestRemoval}
                  />
                ) : (
                  <p className="text-xs text-muted-foreground">
                    Reserva e último recurso aparecem depois que houver um executor principal.
                  </p>
                )}

                {/* ── Last resort ────────────────────────────────────────── */}
                {hasPrimary && (
                  <div className="space-y-1.5">
                    <div className="flex items-baseline justify-between gap-2">
                      <h4
                        id={`terminal-${workspaceId}`}
                        className="text-xs font-semibold uppercase tracking-wider text-muted-foreground"
                      >
                        Último recurso
                      </h4>
                      <span className="text-xs text-muted-foreground">Quando nenhum deles estiver disponível</span>
                    </div>
                    <TerminalGroup
                      labelledBy={`terminal-${workspaceId}`}
                      selecionado={politica.effective_terminal}
                      disabled={!canManage || ocupado}
                      poolBloqueado={underFloor}
                      detalhePool={poolHealth(politica) ?? undefined}
                      onEscolher={applyTerminal}
                    />
                    {underFloor && (
                      <p className="text-xs text-amber-700 dark:text-amber-400">
                        Bloqueado pelo administrador da plataforma.
                      </p>
                    )}
                  </div>
                )}

                {/* ── Candidatos ─────────────────────────────────────────── */}
                {canManage && (
                  <div className="space-y-1.5">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Incluir executor
                    </h4>
                    {candidatos.length === 0 ? (
                      <p className="rounded-md border border-dashed px-3 py-2 text-xs text-muted-foreground">
                        {dedicados.length === 0
                          ? "Você não tem executores dedicados. Crie um em Executores para isolar este workspace."
                          : dedicados.some(e => e.status === "active")
                            ? "Todos os seus executores dedicados ativos já estão na política."
                            : `Seus executores dedicados não estão ativos (${dedicados.map(e => rotuloDoStatus(e.status)).join(", ")}). Só executores ativos entram na política.`}
                      </p>
                    ) : (
                      <ul className="divide-y rounded-md border">
                        {candidatos.map(e => (
                          <li key={e.id_hash} className="flex items-center gap-2 px-3 py-1.5 text-sm">
                            <PresenceDot online={e.online} />
                            <span className="min-w-0 flex-1 truncate">{e.name}</span>
                            <Carga capacidade={e.capacity} />
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-7 gap-1 text-xs"
                              disabled={ocupado}
                              onClick={() => incluir(e, 1)}
                              aria-label={`Incluir ${e.name} entre os principais`}
                            >
                              {operacao === `incluir:${e.id_hash}`
                                ? <TbLoader2 size={12} className="animate-spin" aria-hidden="true" />
                                : <TbPlus size={12} aria-hidden="true" />}
                              Principal
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-7 gap-1 text-xs"
                              disabled={ocupado || !hasPrimary}
                              title={!hasPrimary ? "Defina um executor principal antes." : undefined}
                              onClick={() => incluir(e, 2)}
                              aria-label={`Incluir ${e.name} como reserva`}
                            >
                              <TbPlus size={12} aria-hidden="true" />
                              Reserva
                            </Button>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </SheetSection>

      {/* Confirmation: "pool" changes where this workspace's DATA can run. */}
      <Dialog open={confirmPool} onOpenChange={setConfirmPool}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Usar o pool como último recurso?</DialogTitle>
            <DialogDescription>
              Quando nenhum executor da política estiver disponível, as execuções deste workspace
              — e os dados que elas processam — poderão rodar em executores compartilhados da
              plataforma. Você pode voltar para «Falhar a execução» quando quiser.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmPool(false)}>Cancelar</Button>
            <Button onClick={() => applyTerminal("pool", true)}>Permitir o pool</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Confirmation: the last primary takes the fallback with it and returns
          the workspace to the pool. */}
      <Dialog open={confirmRemoval !== null} onOpenChange={o => { if (!o) setConfirmRemoval(null) }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Remover o último executor principal?</DialogTitle>
            <DialogDescription>
              Sem executor principal, este workspace volta a ser Compartilhado: tudo roda no pool
              da plataforma.
              {(politica?.fallback.length ?? 0) > 0 && (
                <> Os executores de reserva ({politica?.fallback.map(m => m.name).join(", ")}) também
                saem da política.</>
              )}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmRemoval(null)}>Cancelar</Button>
            <Button variant="destructive" onClick={() => confirmRemoval && remover(confirmRemoval)}>
              Remover
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

// ── Pieces ───────────────────────────────────────────────────────────────────

function Nivel({
  titulo, rotulo, membros, disponiveis, vazio, canManage, ocupado, operacao, onRemover,
}: {
  titulo: string
  /** How the tier is named in the remove button's label. */
  rotulo: string
  membros: IPolicyMember[]
  disponiveis: number
  vazio: string
  canManage: boolean
  ocupado: boolean
  operacao: Operacao | null
  onRemover: (m: IPolicyMember) => void
}) {
  return (
    <section aria-label={titulo} className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-2">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {titulo}
        </h4>
        {membros.length > 0 && (
          <span className={cn(
            "text-xs tabular-nums",
            disponiveis === 0 ? "font-medium text-amber-700 dark:text-amber-400" : "text-muted-foreground",
          )}>
            {countOnline(disponiveis, membros.length, noSignal(membros))}
          </span>
        )}
      </div>
      {membros.length === 0 ? (
        <p className="rounded-md border border-dashed px-3 py-2 text-xs text-muted-foreground">{vazio}</p>
      ) : (
        <ul className="divide-y rounded-md border">
          {membros.map(m => {
            const inativo = m.status !== "active"
            return (
              <li
                key={m.id_hash}
                className={cn("flex items-center gap-2 px-3 py-1.5 text-sm", inativo && "bg-amber-500/5")}
              >
                <PresenceDot online={m.online} />
                <span className="min-w-0 flex-1 truncate font-medium">{m.name}</span>
                <Carga capacidade={m.capacity} />
                <ExecutorTypeBadge type={m.executor_type} size="sm" />
                {inativo && (
                  <Badge
                    variant="outline"
                    className="border-amber-500/40 px-1 py-0 text-[9px] leading-tight text-amber-700 dark:text-amber-400"
                  >
                    {rotuloDoStatus(m.status)}
                  </Badge>
                )}
                {canManage && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-7 shrink-0"
                    disabled={ocupado}
                    onClick={() => onRemover(m)}
                    aria-label={`Remover ${m.name} do nível ${rotulo}`}
                    title="Remover"
                  >
                    {operacao === `remover:${m.id_hash}`
                      ? <TbLoader2 className="size-3.5 animate-spin" aria-hidden="true" />
                      : <TbX className="size-3.5" aria-hidden="true" />}
                  </Button>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}

/**
 * Three-state presence dot: online, offline and NO SIGNAL (Redis down or
 * reconnecting). The third exists so as not to paint "offline" an executor
 * that simply could not be queried.
 */
function PresenceDot({ online }: { online: boolean | null }) {
  const texto = online === true ? "online" : online === false ? "offline" : "sem sinal"
  return (
    <span
      className={cn(
        "inline-block size-2 shrink-0 rounded-full",
        online === true && "bg-green-500",
        online === false && "bg-muted-foreground/40",
        online === null && "border border-dashed border-muted-foreground/70",
      )}
      title={texto}
    >
      <span className="sr-only">{texto}</span>
    </span>
  )
}

/**
 * The executor's load, as it publishes it: this is what gives meaning to
 * "online" — an online, full executor does not get the next job now. Hidden
 * when no capacity is published (offline, no signal, old version).
 */
function Carga({ capacidade }: { capacidade: Capacidade }) {
  const texto = describeCapacity(capacidade)
  if (!texto) return null
  const cheio = capacityFull(capacidade)
  return (
    <span
      className={cn(
        "hidden shrink-0 text-xs tabular-nums sm:inline",
        cheio ? "font-medium text-amber-700 dark:text-amber-400" : "text-muted-foreground",
      )}
      title={cheio ? "Sem folga: execuções e fila no teto" : "Execuções em andamento / teto do executor"}
    >
      {texto}{cheio && " · cheio"}
    </span>
  )
}

const OPTIONS: { valor: PolicyTerminal; titulo: string; descricao: string }[] = [
  {
    valor: "fail",
    titulo: "Falhar a execução",
    descricao: "Nada sai deste workspace: a execução falha e você é avisado. Modo Isolado.",
  },
  {
    valor: "pool",
    titulo: "Usar o pool compartilhado",
    descricao: "A execução vai para um executor compartilhado da plataforma. Modo Dedicado + pool.",
  },
]

/**
 * A real radio group: arrows move the choice, a single tab stop.
 * Cards instead of dots because each option needs a sentence about its
 * consequence — but the keyboard has to work as in a radio.
 */
function TerminalGroup({
  labelledBy, selecionado, disabled, poolBloqueado, detalhePool, onEscolher,
}: {
  labelledBy: string
  selecionado: PolicyTerminal
  disabled: boolean
  poolBloqueado: boolean
  detalhePool?: string
  onEscolher: (t: PolicyTerminal) => void
}) {
  function isEnabled(valor: PolicyTerminal) {
    return !disabled && !(valor === "pool" && poolBloqueado)
  }

  function aoTeclar(e: React.KeyboardEvent<HTMLDivElement>) {
    if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key)) return
    e.preventDefault()
    const outra: PolicyTerminal = selecionado === "fail" ? "pool" : "fail"
    if (isEnabled(outra)) onEscolher(outra)
  }

  return (
    <div
      role="radiogroup"
      aria-labelledby={labelledBy}
      onKeyDown={aoTeclar}
      className="grid gap-2 sm:grid-cols-2"
    >
      {OPTIONS.map(o => {
        const ativa = selecionado === o.valor
        const bloqueada = o.valor === "pool" && poolBloqueado
        return (
          <button
            key={o.valor}
            type="button"
            role="radio"
            aria-checked={ativa}
            aria-disabled={!isEnabled(o.valor) || undefined}
            disabled={disabled}
            tabIndex={ativa ? 0 : -1}
            onClick={() => isEnabled(o.valor) && onEscolher(o.valor)}
            className={cn(
              "flex flex-col items-start gap-0.5 rounded-md border px-3 py-2 text-left text-sm transition-colors",
              ativa ? "border-primary bg-primary/5" : "hover:bg-muted/60",
              (disabled || bloqueada) && "cursor-not-allowed opacity-70 hover:bg-transparent",
            )}
          >
            <span className="flex items-center gap-1.5 font-medium">
              {bloqueada && <TbLock size={12} aria-hidden="true" />}
              {o.titulo}
              {o.valor === "fail" && (
                <span className="rounded border px-1 text-[9px] font-normal uppercase tracking-wide text-muted-foreground">
                  padrão
                </span>
              )}
            </span>
            <span className="text-xs text-muted-foreground">{o.descricao}</span>
            {o.valor === "pool" && detalhePool && !bloqueada && (
              <span className="text-xs tabular-nums text-muted-foreground">{detalhePool}</span>
            )}
          </button>
        )
      })}
    </div>
  )
}
