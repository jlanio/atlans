"use client"

import { useState } from "react"
import Link from "next/link"
import {
  TbAdjustments, TbAlertTriangle, TbFolders, TbLoader2, TbLock, TbServer, TbSettings, TbUsers,
} from "react-icons/tb"
import { Badge } from "@/app/components/ui/badge"
import { Button } from "@/app/components/ui/button"
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/app/components/ui/dialog"
import { Skeleton } from "@/app/components/ui/skeleton"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/app/components/ui/select"
import { ExecutorTypeBadge } from "@/app/components/executor-type-badge"
import { getWorkspaceIdentity } from "@/lib/workspace-identity"
import { cn } from "@/lib/utils"
import type { Workspace } from "@/context/WorkspaceContext"
import { roleLabel } from "./role-labels"
import { POOL } from "./use-workspace-executors"
import { WorkspaceAvatar } from "./workspace-avatar"
import type { SectionId } from "./settings-sheet"
import {
  dotColor, describeExecutor, inAlert, resumirExecutor, labelExecutor, type SummaryEntry,
} from "./executor-resumo"
import {
  modeClass, countOnline, policyActionLabel, modeLabel, rotuloDoStatus, poolHealth, noSignal,
} from "./politica"

interface Props extends SummaryEntry {
  workspace: Workspace
  salvandoExecutor: boolean
  podeGerenciar: boolean
  onTrocarExecutor: (valor: string) => void
  /** Opens the settings panel directly on the requested section. */
  onConfigurar: (secao: SectionId) => void
}

const PREVIEW_TITLE = "Prévia: passa a valer quando o roteamento por política for ligado. "
  + "Hoje as execuções seguem o executor selecionado."
const FLOOR_TITLE = "Isolamento obrigatório: definido pelo administrador da plataforma"

/**
 * Panel of the active workspace.
 *
 * The product works in ONE workspace at a time — the header and the editor
 * already revolve around it — and this screen now says the same: the active one
 * gets the identity color, the executor with its status spelled out, and the
 * shortcuts to where the work actually happens. Switching the executor lives
 * here, and only here: it is the screen's most frequent adjustment, and the
 * adjustment for the other workspaces goes through the settings panel.
 *
 * The quick picker is the most destructive action on the screen: going back to
 * the pool erases the whole policy and changes where the DATA goes. That is why
 * it asks for confirmation when there is a dedicated executor in play — the
 * same ceremony the editor requires for the "último recurso" (last resort).
 */
export function WorkspaceHero({
  workspace, salvandoExecutor, podeGerenciar, onTrocarExecutor, onConfigurar, ...entrada
}: Props) {
  const identity = getWorkspaceIdentity(workspace)
  const politica = entrada.politica ?? null
  const emVigor = politica?.policy_routing_enabled === true
  const resumo = resumirExecutor(entrada)
  const alerta = inAlert(resumo, politica)
  const ponto = dotColor(resumo, politica)
  const papel = workspace.my_role === "owner" ? "Proprietário" : roleLabel(workspace.my_role)
  const [confirmPool, setConfirmPool] = useState(false)

  // Only active dedicated executors: a pool executor is not a target — the
  // "Pool compartilhado" item already is the pool. The current one, if it is
  // from the pool (old data), stays visible so the trigger does not render empty.
  const disponiveis = entrada.executores.filter(
    e => e.status === "active" && (!e.is_default || e.id_hash === entrada.alvo),
  )

  // Is there a dedicated executor in play? Then "pool" erases the policy and
  // changes where the data goes: confirmation first.
  const currentDedicated = resumo.estado === "ok" || resumo.estado === "inativo"
    ? (resumo.executor.executor_type === "dedicated" ? resumo.executor.name : null)
    : null
  const hasDedicated = currentDedicated !== null || (politica?.primary.length ?? 0) > 0

  function escolher(valor: string) {
    if (valor === POOL && hasDedicated) { setConfirmPool(true); return }
    onTrocarExecutor(valor)
  }

  const policyCount = politica && politica.mode !== "pool"
    ? countOnline(
        politica.available_primary + politica.available_fallback,
        politica.primary.length + politica.fallback.length,
        noSignal([...politica.primary, ...politica.fallback]),
      )
    : null

  return (
    <section
      aria-labelledby="workspace-ativo-nome"
      className="relative overflow-hidden rounded-xl border bg-card shadow-xs motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-1 motion-safe:duration-300"
    >
      {/* The identity color comes in only as a stripe — not as a flat background (which
          would swallow the text in both themes) nor as a diffuse glow. */}
      <span aria-hidden="true" className={cn("absolute inset-y-0 left-0 w-1.5", identity.bg)} />

      <div className="relative grid gap-5 p-5 pl-6 sm:p-6 sm:pl-7 lg:grid-cols-[minmax(0,1fr)_19rem] lg:gap-8">
        <div className="min-w-0">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.1em] text-primary">
            Workspace ativo
          </p>
          <div className="flex items-center gap-3.5">
            <WorkspaceAvatar workspace={workspace} size="xl" />
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                <h2 id="workspace-ativo-nome" className="text-xl font-semibold leading-tight text-balance">
                  {workspace.name}
                </h2>
                {workspace.is_default && (
                  <Badge variant="secondary" className="px-1.5 py-0 text-[11px]">padrão</Badge>
                )}
              </div>
              <p className="mt-0.5 text-sm text-muted-foreground">
                {workspace.description && (
                  <>{workspace.description} <span aria-hidden="true">·</span> </>
                )}
                {papel}
              </p>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <Button variant="outline" size="sm" asChild>
              <Link href="/projects"><TbFolders size={15} /> Projetos</Link>
            </Button>
            <Button variant="outline" size="sm" onClick={() => onConfigurar("membros")}>
              <TbUsers size={15} /> Membros
            </Button>
            <Button variant="outline" size="sm" asChild>
              <Link href="/executores"><TbServer size={15} /> Executores</Link>
            </Button>
            <Button variant="ghost" size="sm" onClick={() => onConfigurar("geral")}>
              <TbSettings size={15} /> Configurar
            </Button>
          </div>
        </div>

        {/* ── Executor ──────────────────────────────────────────────────── */}
        <div className="flex min-w-0 flex-col gap-2">
          <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
            {alerta
              ? <TbAlertTriangle size={13} className="text-amber-700 dark:text-amber-400" />
              : <TbServer size={13} />}
            Executor
          </span>

          {resumo.estado === "carregando" ? (
            <Skeleton className="h-9 w-full rounded-md" />
          ) : resumo.estado === "indefinido" ? (
            // "Couldn't read" is NOT "platform pool": claiming pool here
            // would be lying about where the runs go.
            <p className="text-sm text-muted-foreground">{resumo.mensagem}</p>
          ) : resumo.estado === "grupo" ? (
            // Group or fallback IN EFFECT: it is not a single target, and the quick
            // picker does not represent it. Adjusting goes through the editor (link below).
            <div className="flex min-w-0 items-center gap-2 rounded-md border bg-background/60 px-3 py-2 text-sm">
              <span className="min-w-0 flex-1 truncate font-medium">{labelExecutor(resumo)}</span>
            </div>
          ) : podeGerenciar ? (
            <div className="flex items-center gap-2">
              <Select
                value={entrada.alvo ?? POOL}
                onValueChange={escolher}
                // A second choice during the write was silently discarded;
                // locking the trigger says why.
                disabled={salvandoExecutor}
              >
                <SelectTrigger
                  className={cn("w-full", alerta && "border-amber-500/50")}
                  aria-busy={salvandoExecutor}
                  aria-label={`Executor de ${workspace.name}`}
                >
                  <SelectValue placeholder="Selecionar executor" />
                </SelectTrigger>
                <SelectContent className="max-w-(--radix-select-content-available-width)">
                  <SelectItem value={POOL}>
                    <span className="flex min-w-0 items-center gap-1.5">
                      <span className="truncate">Pool compartilhado</span>
                      <ExecutorTypeBadge type="default" size="sm" />
                    </span>
                  </SelectItem>
                  {/* The target that disappeared becomes a disabled item: without it the
                      trigger would render EMPTY and the warning below would have
                      no referent on screen. */}
                  {resumo.estado === "sumido" && (
                    <SelectItem value={resumo.alvo} disabled>
                      <span className="flex min-w-0 items-center gap-1.5">
                        <TbAlertTriangle size={12} className="shrink-0 text-amber-700 dark:text-amber-400" />
                        <span className="truncate">Executor indisponível</span>
                      </span>
                    </SelectItem>
                  )}
                  {resumo.estado === "inativo" && (
                    <SelectItem value={resumo.executor.id_hash} disabled>
                      <span className="flex min-w-0 items-center gap-1.5">
                        <TbAlertTriangle size={12} className="shrink-0 text-amber-700 dark:text-amber-400" />
                        <span className="truncate">{resumo.executor.name}</span>
                        <Badge variant="outline" className="shrink-0 px-1 py-0 text-[9px] leading-tight text-amber-700 dark:text-amber-400">
                          {rotuloDoStatus(resumo.executor.status)}
                        </Badge>
                      </span>
                    </SelectItem>
                  )}
                  {disponiveis.map(e => (
                    <SelectItem key={e.id_hash} value={e.id_hash}>
                      <span className="flex min-w-0 items-center gap-1.5">
                        <span
                          aria-hidden="true"
                          className={cn("inline-block size-2 shrink-0 rounded-full", e.online ? "bg-green-500" : "bg-muted-foreground/40")}
                        />
                        <span className="sr-only">{e.online ? "online" : "offline"}</span>
                        <span className="truncate">{e.name}</span>
                        <ExecutorTypeBadge type={e.executor_type} size="sm" />
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {/* Fixed slot: inserting/removing the spinner shrank the Select in the
                  middle of the interaction. */}
              <span className="flex size-4 shrink-0 items-center justify-center">
                {salvandoExecutor && <TbLoader2 size={15} className="animate-spin text-muted-foreground" />}
              </span>
            </div>
          ) : (
            <div className="flex min-w-0 flex-wrap items-center gap-1.5 rounded-md border bg-background/60 px-3 py-2 text-sm">
              {resumo.estado === "pool" ? (
                <>
                  <span className="text-muted-foreground">Pool compartilhado</span>
                  <ExecutorTypeBadge type="default" size="sm" />
                </>
              ) : resumo.estado === "sumido" ? (
                <span className="font-medium text-amber-700 dark:text-amber-400">Executor indisponível</span>
              ) : (
                <>
                  <span className="min-w-0 truncate font-medium">{resumo.executor.name}</span>
                  <ExecutorTypeBadge type={resumo.executor.executor_type} size="sm" />
                </>
              )}
            </div>
          )}

          {resumo.estado !== "carregando" && resumo.estado !== "indefinido" && (
            <p className={cn(
              "flex items-start gap-1.5 text-xs",
              alerta ? "text-amber-700 dark:text-amber-400" : "text-muted-foreground",
            )}>
              {ponto && <span aria-hidden="true" className={cn("mt-1 inline-block size-2 shrink-0 rounded-full", ponto)} />}
              <span>{describeExecutor(resumo, politica)}</span>
            </p>
          )}

          {/* A single line for the policy: the mode in effect (or the preview),
              the set's health and ONE control for the editor — where group,
              fallback and last resort are defined. */}
          {politica && resumo.estado !== "carregando" && resumo.estado !== "indefinido" && (
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
              <span>Política:</span>
              <Badge
                variant="outline"
                className={cn("gap-1 px-1.5 py-0 text-[10px]", modeClass(politica.mode), !emVigor && "border-dashed")}
                title={politica.isolation_floor === "no_pool" ? FLOOR_TITLE : !emVigor ? PREVIEW_TITLE : undefined}
              >
                {politica.isolation_floor === "no_pool" && <TbLock size={10} aria-hidden="true" />}
                {modeLabel(politica.mode)}{!emVigor && " · prévia"}
              </Badge>
              {politica.isolation_floor === "no_pool" && <span className="sr-only">{FLOOR_TITLE}</span>}
              {politica.mode === "pool"
                ? (poolHealth(politica) && <span>{poolHealth(politica)}</span>)
                : (politica.primary.length + politica.fallback.length > 1 && resumo.estado !== "grupo" && policyCount && (
                  <span>{policyCount}</span>
                ))}
              {podeGerenciar && (
                <button
                  type="button"
                  onClick={() => onConfigurar("executor")}
                  className="inline-flex items-center gap-1 underline-offset-2 hover:text-foreground hover:underline"
                >
                  <TbAdjustments size={12} aria-hidden="true" />
                  {policyActionLabel(politica.mode)}
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Going back to the pool with a dedicated executor in play: erases the
          policy and changes where the data goes. */}
      <Dialog open={confirmPool} onOpenChange={setConfirmPool}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Voltar ao pool compartilhado?</DialogTitle>
            <DialogDescription>
              As execuções de «{workspace.name}» deixam de ir para{" "}
              {currentDedicated ?? "os executores dedicados deste workspace"} e passam a rodar em
              qualquer executor compartilhado da plataforma, inclusive os dados que elas
              processam. A política de execução deste workspace (principais, reserva e último
              recurso) será apagada.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmPool(false)}>Cancelar</Button>
            <Button onClick={() => { setConfirmPool(false); onTrocarExecutor(POOL) }}>Usar o pool</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  )
}
