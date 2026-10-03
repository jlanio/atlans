"use client"

import { useCallback, useState } from "react"
import { IconType } from "react-icons"
import {
  TbAlertTriangle, TbBell, TbCheck, TbCopy, TbServer, TbSettings, TbUsers,
} from "react-icons/tb"
import { Badge } from "@/app/components/ui/badge"
import {
  Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle,
} from "@/app/components/ui/sheet"
import { createToast } from "@/utils/createToast"
import { hasMinRole, useWorkspace, Workspace } from "@/context/WorkspaceContext"
import { WorkspaceBadge } from "../workspace-badge"
import { roleLabel } from "../role-labels"
import { GeneralSection } from "./general-section"
import { MembersSection } from "./members-section"
import { ExecutorSection } from "./executor-section"
import { NotificationsSection } from "./notifications-section"
import { DangerSection } from "./danger-section"

export type SectionId = "geral" | "membros" | "executor" | "notificacoes" | "perigo"

// "Notificações" (webhook allowlist) was hidden while the rest of the
// vertical was already running: the column exists, the endpoint exists, and
// `run_result_consumer` BLOCKS webhooks outside the allowlist in production —
// only logging a warning on the server. Without this screen, whoever set up a
// webhook and stopped receiving it had no way to find out why or to fix it.
const SECTIONS: { id: SectionId; label: string; icon: IconType }[] = [
  { id: "geral",        label: "Geral",          icon: TbSettings },
  { id: "membros",      label: "Membros",        icon: TbUsers },
  { id: "executor",     label: "Execução",       icon: TbServer },
  { id: "notificacoes", label: "Notificações",   icon: TbBell },
  { id: "perigo",       label: "Zona de perigo", icon: TbAlertTriangle },
]

interface Props {
  /**
   * Derived from the workspace list, not kept in state: this way the header
   * follows a rename made in here, and the panel closes on its own if the
   * workspace ceases to exist.
   */
  workspace: Workspace | null
  currentUserId: string | null
  /**
   * Section open at start. Only read on mount — the screen remounts the panel
   * on every opening (`key`), so a shortcut like "Membros" lands here directly.
   */
  initialSection?: SectionId
  onClose: () => void
}

export function WorkspaceSettingsSheet({ workspace, currentUserId, initialSection = "geral", onClose }: Props) {
  const { current } = useWorkspace()
  const [section, setSection] = useState<SectionId>(initialSection)
  const [memberCount, setMemberCount] = useState<number | null>(null)
  const [executorAlert, setExecutorAlert] = useState(false)
  const [notificacoesAlert, setNotificacoesAlert] = useState(false)

  const canManage = hasMinRole(workspace?.my_role, "admin")

  // Stable: the sections receive these callbacks in effect dependencies, and a
  // new function on every render would put them in an update loop.
  const handleMemberCount = useCallback((n: number) => setMemberCount(n), [])
  const handleExecutorAlert = useCallback((v: boolean) => setExecutorAlert(v), [])
  const handleNotificacoesAlert = useCallback((v: boolean) => setNotificacoesAlert(v), [])

  async function copyId() {
    if (!workspace) return
    // Without the await/catch, a non-HTTPS origin (where `clipboard` is undefined)
    // or a denied permission produced a "copiado" (copied) with an empty clipboard.
    try {
      if (!navigator.clipboard) throw new Error("Clipboard indisponível")
      await navigator.clipboard.writeText(workspace.id_hash)
      createToast.success("ID do workspace copiado.")
    } catch {
      createToast.error("Não foi possível copiar o ID.")
    }
  }

  return (
    <Sheet open={!!workspace} onOpenChange={o => { if (!o) onClose() }}>
      <SheetContent
        side="right"
        // `SheetContent` is sm:max-w-sm without overflow; the panel needs width
        // for the rail + content, and a scroller of its own. The minimum is the
        // point at which the section rail still fits next to the content.
        resizable={{
          storageKey: "atlas_workspace_settings_width",
          defaultWidth: 640,
          minWidth: 460,
          maxWidth: 1280,
        }}
        className="flex w-full flex-col gap-0 p-0"
      >
        {workspace && (
          <>
            <SheetHeader className="shrink-0 border-b pr-12">
              <SheetTitle asChild>
                <div className="flex min-w-0 items-center gap-2">
                  <WorkspaceBadge
                    workspace={workspace}
                    size="md"
                    showName
                    showRole
                    currentUserId={currentUserId}
                  />
                </div>
              </SheetTitle>
              <SheetDescription asChild>
                <div className="flex flex-wrap items-center gap-1.5">
                  <Badge variant="outline" className="text-[10px]">
                    {roleLabel(workspace.my_role)}
                  </Badge>
                  {workspace.is_default && (
                    <Badge variant="secondary" className="text-[10px]">padrão</Badge>
                  )}
                  {current?.id_hash === workspace.id_hash && (
                    <span className="flex items-center gap-1 text-xs text-primary">
                      <TbCheck className="size-3.5" aria-hidden="true" />
                      Ativo
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={copyId}
                    title="Copiar ID do workspace"
                    className="inline-flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-foreground"
                  >
                    <TbCopy className="size-3" aria-hidden="true" />
                    <span className="font-mono">Copiar ID</span>
                  </button>
                </div>
              </SheetDescription>
            </SheetHeader>

            <div className="flex min-h-0 flex-1 flex-col sm:flex-row">
              <nav
                aria-label="Seções de configuração"
                className="flex shrink-0 gap-1 overflow-x-auto border-b p-2 sm:w-44 sm:flex-col sm:overflow-x-visible sm:border-b-0 sm:border-r"
              >
                {SECTIONS.map(({ id, label, icon: Icon }) => {
                  const ativo = section === id
                  const alerta =
                    (id === "executor" && executorAlert) ||
                    (id === "notificacoes" && notificacoesAlert)
                  return (
                    <button
                      key={id}
                      type="button"
                      onClick={() => setSection(id)}
                      aria-current={ativo ? "page" : undefined}
                      className={`flex shrink-0 items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-sm transition-colors sm:shrink ${
                        ativo
                          ? "bg-muted font-medium text-foreground"
                          : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
                      }`}
                    >
                      <Icon
                        className={`size-4 shrink-0 ${id === "perigo" ? "text-destructive" : ""}`}
                        aria-hidden="true"
                      />
                      <span className="truncate">{label}</span>
                      {id === "membros" && memberCount != null && (
                        <span className="ml-auto text-xs tabular-nums text-muted-foreground">
                          {memberCount}
                        </span>
                      )}
                      {alerta && (
                        <TbAlertTriangle
                          className="ml-auto size-3.5 shrink-0 text-amber-700 dark:text-amber-400"
                          aria-label="Requer atenção"
                        />
                      )}
                    </button>
                  )
                })}
              </nav>

              {/* All sections stay MOUNTED, just hidden — it is not waste.
                  Mounting on demand would make the rail's warnings ("Executor ⚠",
                  member count) appear only after visiting the section, which
                  makes them useless as warnings. It is two requests for a
                  single workspace on open. */}
              <div className="min-w-0 flex-1 overflow-y-auto p-4">
                <div hidden={section !== "geral"}>
                  <GeneralSection workspace={workspace} />
                </div>
                <div hidden={section !== "membros"}>
                  <MembersSection
                    workspace={workspace}
                    canManage={canManage}
                    currentUserId={currentUserId}
                    onCountChange={handleMemberCount}
                  />
                </div>
                <div hidden={section !== "executor"}>
                  <ExecutorSection
                    workspaceId={workspace.id_hash}
                    canManage={canManage}
                    onAlertChange={handleExecutorAlert}
                  />
                </div>
                <div hidden={section !== "notificacoes"}>
                  <NotificationsSection
                    workspaceId={workspace.id_hash}
                    canManage={canManage}
                    onAlertChange={handleNotificacoesAlert}
                  />
                </div>
                <div hidden={section !== "perigo"}>
                  <DangerSection workspace={workspace} onClosePanel={onClose} />
                </div>
              </div>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
