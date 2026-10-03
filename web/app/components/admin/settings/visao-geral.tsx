"use client"

// "Visão geral" (overview) of the admin Settings: the indicators, and the
// translation of the reads' raw state into actionable pending items (each one
// leads to its section).

import type { INodeAdminEntry, IStorageUsageAdmin, IWorkspacePolicyAdmin, IWorkspaceTrash } from "@/service/types"
import { semOndeRodar } from "@/app/components/admin/isolation-floor-section"
import { TbAlertTriangle, TbChevronRight, TbCircleCheck } from "react-icons/tb"
import { cn } from "@/lib/utils"
import { formatBytes } from "@/utils/formatters"
import { formatarInteiro, plural } from "@/lib/formatos"
import { SkeletonVisaoGeral } from "./estados"
import type { SectionId } from "./nav"

type Severity = "danger" | "warn" | "info"

export interface SettingsAlert {
  section: Exclude<SectionId, "overview">
  severity: Severity
  title: string
  detail: string
}

/**
 * Translates the raw state of the 4 calls into actionable pending items.
 *
 * The real usability gain is here: before, knowing that something needed
 * attention required opening each section and interpreting loose numbers. Each
 * alert carries the destination section, so the click leads straight to where
 * to act.
 */
export function buildAlerts(
  health: { webhook_whitelist: string[] } | null,
  retentionDays: number | null | undefined,
  storage: IStorageUsageAdmin | null,
  nodes: INodeAdminEntry[] | null,
  trash: IWorkspaceTrash[] | null,
  policies: IWorkspacePolicyAdmin[] | null = null,
): SettingsAlert[] {
  const alerts: SettingsAlert[] = []

  // A floor set on a workspace with no main executor: nothing runs in it, and the
  // owner has no way to loosen it — only the admin can fix it (or the owner adds one).
  for (const ws of (policies ?? []).filter(semOndeRodar)) {
    alerts.push({
      section: "execucao", severity: "warn",
      title: `«${ws.name}» exige isolamento e não tem executor principal`,
      detail: "Nada roda neste workspace até o dono incluir um executor dedicado, ou até o piso ser liberado.",
    })
  }

  if (trash && trash.length > 0) {
    const workflows = trash.reduce((acc, ws) => acc + ws.workflows, 0)
    alerts.push({
      section: "lixeira", severity: "info",
      title: `${plural(trash.length, "workspace")} na lixeira`,
      detail: workflows > 0
        ? `${plural(workflows, "workflow")} aguardando restauração — os agendamentos seguem parados.`
        : "Aguardando restauração ou exclusão definitiva.",
    })
  }

  if (health && health.webhook_whitelist.length === 0) {
    alerts.push({
      section: "seguranca", severity: "warn",
      title: "Webhook pode ir a qualquer destino",
      detail: "Nenhum domínio na whitelist — a notificação de fim de execução é enviada a qualquer host.",
    })
  }
  if (retentionDays == null) {
    alerts.push({
      section: "seguranca", severity: "info",
      title: "Artefatos não expiram",
      detail: "Sem prazo de retenção, o consumo de disco cresce indefinidamente.",
    })
  }

  const th = storage?.tracking_health
  if (th) {
    if ((th.orphaned_workspace_artifacts ?? 0) > 0) {
      alerts.push({
        section: "armazenamento", severity: "danger",
        title: `${plural(th.orphaned_workspace_artifacts ?? 0, "artefato")} de workspace deletado`,
        detail: "Inacessíveis a qualquer usuário e ocupando disco. Use a purga para liberar.",
      })
    }
    if ((th.unrecoverable_size_artifacts ?? 0) > 0) {
      alerts.push({
        section: "armazenamento", severity: "danger",
        title: `${plural(th.unrecoverable_size_artifacts ?? 0, "artefato")} com tamanho irrecuperável`,
        detail: "O objeto não está no MinIO ou ficou no disco do executor. A reconciliação já desistiu.",
      })
    }
    if (th.pending_drive_files > 0) {
      alerts.push({
        section: "armazenamento", severity: "warn",
        title: `${plural(th.pending_drive_files, "upload")} não confirmado(s)`,
        detail: `${formatBytes(th.pending_drive_bytes)} em arquivos pendentes. A reconciliação remove após 24h.`,
      })
    }
  }

  const disabled = nodes?.filter(n => !n.enabled).length ?? 0
  if (disabled > 0) {
    alerts.push({
      section: "nodes", severity: "warn",
      title: `${plural(disabled, "node")} desabilitado(s)`,
      detail: "Workflows que os utilizam falham ao executar até serem reabilitados.",
    })
  }

  return alerts
}

// Pending-item colors: the status pairs allowed by the contract (§6), with the
// full light/dark pair. `info` stays on neutral tokens.
const SEVERITY_STYLE: Record<Severity, string> = {
  danger: "border-red-500/30 bg-red-50 dark:bg-red-500/10",
  warn:   "border-amber-500/30 bg-amber-50 dark:bg-amber-500/10",
  info:   "border-border bg-muted/30",
}
const SEVERITY_ICON: Record<Severity, string> = {
  danger: "text-red-500",
  warn:   "text-amber-500",
  info:   "text-muted-foreground",
}

/**
 * Overview indicator, following the contract's stat pattern (§2): label in
 * small caps, value `text-2xl tabular-nums`. Clickable — it leads to the section
 * where the number is resolved — so it is a `<button>` with visible focus and a
 * touch target.
 */
function Indicador({
  rotulo, valor, apoio, onClick,
}: { rotulo: string; valor: string; apoio?: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="relative flex min-w-0 flex-col gap-1.5 overflow-hidden rounded-lg border bg-card p-3 text-left shadow-xs outline-none transition-colors hover:border-foreground/30 hover:bg-accent/40 focus-visible:ring-[3px] focus-visible:ring-ring/50 sm:p-4"
    >
      <span className="truncate text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{rotulo}</span>
      <span className="text-2xl font-semibold leading-none tabular-nums tracking-tight text-foreground">{valor}</span>
      {apoio && <span className="text-xs text-muted-foreground">{apoio}</span>}
    </button>
  )
}

export function OverviewSection({
  storage, nodes, retentionDays, whitelistCount, alerts, loading, onNavigate,
}: {
  storage: IStorageUsageAdmin | null
  nodes: INodeAdminEntry[] | null
  retentionDays: number | null | undefined
  whitelistCount: number
  alerts: SettingsAlert[]
  loading: boolean
  onNavigate: (s: SectionId) => void
}) {
  if (loading) return <SkeletonVisaoGeral />

  const enabled = nodes?.filter(n => n.enabled).length ?? 0
  const totalNodes = nodes?.length ?? 0
  const orfaos = storage?.by_workspace.filter(w => w.workspace_deleted).length ?? 0

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Indicador
          rotulo="Armazenamento"
          valor={formatBytes(storage?.totals.total_bytes ?? 0)}
          apoio={plural((storage?.totals.drive_files ?? 0) + (storage?.totals.artifact_files ?? 0), "arquivo")}
          onClick={() => onNavigate("armazenamento")}
        />
        <Indicador
          rotulo="Workspaces com dados"
          valor={formatarInteiro(storage?.by_workspace.length ?? 0)}
          apoio={orfaos > 0 ? plural(orfaos, "órfão", "órfãos") : "todos ativos"}
          onClick={() => onNavigate("armazenamento")}
        />
        <Indicador
          rotulo="Nodes ativos"
          valor={totalNodes ? `${formatarInteiro(enabled)}/${formatarInteiro(totalNodes)}` : "—"}
          apoio={totalNodes - enabled > 0 ? `${plural(totalNodes - enabled, "desabilitado")}` : "nenhum bloqueado"}
          onClick={() => onNavigate("nodes")}
        />
        <Indicador
          rotulo="Retenção"
          valor={retentionDays != null ? `${formatarInteiro(retentionDays)} dias` : "∞"}
          apoio={retentionDays != null ? "artefatos expiram" : "sem expiração"}
          onClick={() => onNavigate("seguranca")}
        />
      </div>

      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
          Pendências
          {alerts.length === 0 && (
            <span className="flex items-center gap-1 font-normal text-green-600 dark:text-green-400">
              <TbCircleCheck className="shrink-0" aria-hidden="true" /> nada requer atenção
            </span>
          )}
        </div>

        {alerts.map((a, i) => (
          <button
            key={i}
            onClick={() => onNavigate(a.section)}
            className={cn(
              "flex items-start gap-2 rounded-md border p-2.5 text-left text-xs outline-none transition-colors hover:border-foreground/30 focus-visible:ring-[3px] focus-visible:ring-ring/50 max-md:min-h-10",
              SEVERITY_STYLE[a.severity],
            )}
          >
            <TbAlertTriangle className={cn("mt-0.5 shrink-0", SEVERITY_ICON[a.severity])} aria-hidden="true" />
            <span className="flex-1">
              <span className="font-medium text-foreground">{a.title}.</span>{" "}
              <span className="text-muted-foreground">{a.detail}</span>
            </span>
            <TbChevronRight className="mt-0.5 shrink-0 text-muted-foreground" aria-hidden="true" />
          </button>
        ))}
      </div>

      <p className="text-[11px] text-muted-foreground">
        Whitelist de webhook: {whitelistCount > 0 ? plural(whitelistCount, "domínio", "domínios") : "vazia"} ·
        Reconciliação de armazenamento roda 1×/hora.
      </p>
    </div>
  )
}
