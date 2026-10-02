"use client"

// Seção «Armazenamento» das Configurações do admin: uso do MinIO por
// workspace, saúde do tracking e a purga (irreversível) por escopo.

import { useState } from "react"
import { GisFlowService } from "@/service/GisFlowService"
import type { IStorageUsageAdmin, IStorageWorkspaceUsage, ITrackingHealth } from "@/service/types"
import { Badge } from "@/app/components/ui/badge"
import { Button } from "@/app/components/ui/button"
import { Label } from "@/app/components/ui/label"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/app/components/ui/dialog"
import { TbAlertTriangle, TbCircleCheck, TbDatabase, TbTrash } from "react-icons/tb"
import { createToast } from "@/utils/createToast"
import { cn } from "@/lib/utils"
import { formatBytes } from "@/utils/formatters"
import { CABECALHO_DE_COLUNAS, CELULA_COM_ROTULO, DESTAQUE_DA_FICHA, LINHA_EMPILHADA } from "@/app/components/shared/tabela-empilhada"
import { formatarInteiro, plural } from "@/lib/formatos"
import { VazioEmCirculo } from "./estados"

// ── Armazenamento (MinIO) ─────────────────────────────────────────────────────

/**
 * Indicadores de saúde do tracking: alerta quando há drift silencioso
 * (pending abandonado, artefato sem tamanho, órfãos). Reconciliação roda
 * 1×/hora no servidor para auto-corrigir parte disso. As pendências saem no
 * padrão âmbar/vermelho do contrato (§3.4), não mais num bloco custom.
 */
function SaudeDoTracking({ health }: { health: ITrackingHealth }) {
  const issues: Array<{ tom: "warn" | "danger"; label: string; detail: string }> = []

  if (health.pending_drive_files > 0) {
    issues.push({
      tom: "warn",
      label: `${plural(health.pending_drive_files, "arquivo")} no Drive pending`,
      detail: `${formatBytes(health.pending_drive_bytes)} — uploads não confirmados. Reconciliação remove após 24h.`,
    })
  }
  const recuperaveis = health.null_size_artifacts - (health.unrecoverable_size_artifacts ?? 0)
  if (recuperaveis > 0) {
    issues.push({
      tom: "warn",
      label: `${plural(recuperaveis, "artefato")} sem tamanho conhecido`,
      detail: "MinIO indisponível no momento da gravação. Reconciliação tenta preencher periodicamente.",
    })
  }
  if ((health.unrecoverable_size_artifacts ?? 0) > 0) {
    issues.push({
      tom: "danger",
      label: `${plural(health.unrecoverable_size_artifacts ?? 0, "artefato")} com tamanho irrecuperável`,
      detail: "O objeto não está no MinIO (upload falhou) ou ficou no disco do executor. A reconciliação já desistiu — só a purga resolve.",
    })
  }
  if ((health.orphaned_workspace_artifacts ?? 0) > 0) {
    issues.push({
      tom: "danger",
      label: `${plural(health.orphaned_workspace_artifacts ?? 0, "artefato")} de workspace deletado`,
      detail: "Inacessíveis a qualquer usuário e ocupando disco. Aparecem como '(workspace deletado)' abaixo — use a purga para liberar.",
    })
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
        Saúde do tracking
        {issues.length === 0 && (
          <span className="flex items-center gap-1 font-normal text-green-600 dark:text-green-400">
            <TbCircleCheck className="shrink-0" aria-hidden="true" /> tudo em dia
          </span>
        )}
      </div>
      {issues.map((it, idx) => (
        <p
          key={idx}
          role="status"
          className={cn(
            "flex items-start gap-2 rounded-md border px-3 py-1.5 text-xs",
            it.tom === "danger"
              ? "border-red-500/30 bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-400"
              : "border-amber-500/30 bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400",
          )}
        >
          <TbAlertTriangle size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
          <span>
            <span className="font-medium">{it.label}.</span>{" "}
            <span className="opacity-90">{it.detail}</span>
          </span>
        </p>
      ))}
      <p className="text-[11px] text-muted-foreground">
        Reconciliação automática roda 1×/hora.
      </p>
    </div>
  )
}

/**
 * Diálogo de purga. Ação irreversível: apaga objetos do MinIO e as linhas do
 * banco. Por isso a confirmação exige escolher o escopo e ver o que será
 * removido antes — e o backend ainda revalida o workspace_id no corpo.
 */
function PurgeStorageDialog({
  ws, onClose, onPurged,
}: {
  ws: IStorageWorkspaceUsage
  onClose: () => void
  onPurged: () => void
}) {
  const [scope, setScope] = useState<"all" | "artifacts" | "drive">("all")
  const [purging, setPurging] = useState(false)

  const alvo = scope === "all"
    ? { arquivos: ws.drive_files + ws.artifact_files, bytes: ws.total_bytes }
    : scope === "drive"
      ? { arquivos: ws.drive_files, bytes: ws.drive_bytes }
      : { arquivos: ws.artifact_files, bytes: ws.artifacts_bytes }

  async function purgar() {
    setPurging(true)
    try {
      const res = await GisFlowService.purgeWorkspaceStorage(ws.workspace_id, scope)
      if (res?.error) {
        createToast.error("Falha ao purgar", res.error.message)
        return
      }
      const r = res.data
      const resumo = `${plural(r?.artifacts ?? 0, "artefato")} e ${plural(r?.drive_files ?? 0, "arquivo")} removidos.`

      // Nem tudo que ficou para trás ficou pelo mesmo motivo, e a diferença
      // importa para quem administra: falha de storage e executor offline se
      // resolvem repetindo a purga; catalogado e sem-rastro, não. Reportar só
      // `skipped_s3_errors` fazia o resto ser contado como removido.
      const paraTentarDeNovo =
        (r?.skipped_s3_errors ?? 0) + (r?.pending_executor ?? 0)
      const preservados =
        (r?.skipped_catalogados ?? 0) + (r?.skipped_sem_rastro ?? 0)

      if (paraTentarDeNovo > 0 || preservados > 0) {
        const partes = [resumo]
        if (paraTentarDeNovo > 0) {
          partes.push(
            `${paraTentarDeNovo} mantido(s) por falha no storage ou executor offline — repita para tentar de novo.`,
          )
        }
        if (preservados > 0) {
          partes.push(
            `${preservados} preservado(s): o conteúdo vive no executor e só ele pode removê-lo.`,
          )
        }
        createToast.info("Purga parcial", partes.join(" "))
      } else {
        createToast.success(
          `Liberado ${formatBytes((r?.artifact_bytes ?? 0) + (r?.drive_bytes ?? 0))}`,
          resumo,
        )
      }
      onPurged()
      onClose()
    } catch {
      createToast.error("Falha ao purgar o armazenamento do workspace.")
    } finally {
      setPurging(false)
    }
  }

  return (
    <Dialog open onOpenChange={open => { if (!open && !purging) onClose() }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Purgar armazenamento</DialogTitle>
          <DialogDescription>
            {ws.workspace_deleted
              ? "Este workspace foi deletado — os dados abaixo estão órfãos, inacessíveis a qualquer usuário."
              : <>Os arquivos de <span className="font-medium text-foreground">{ws.workspace_name}</span> serão apagados definitivamente.</>}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <Label className="text-xs">O que remover</Label>
            <div className="flex gap-2">
              {([
                { v: "all", label: "Tudo" },
                { v: "drive", label: "Drive" },
                { v: "artifacts", label: "Artefatos" },
              ] as const).map(opt => (
                <Button
                  key={opt.v}
                  type="button"
                  size="sm"
                  variant={scope === opt.v ? "default" : "outline"}
                  onClick={() => setScope(opt.v)}
                  disabled={purging}
                  className="max-md:h-10"
                >
                  {opt.label}
                </Button>
              ))}
            </div>
          </div>

          <div className="rounded-md border border-red-500/30 bg-red-50 p-3 text-xs dark:bg-red-500/10">
            <div className="flex items-start gap-2">
              <TbAlertTriangle className="mt-0.5 shrink-0 text-red-500" aria-hidden="true" />
              <div>
                <p className="font-medium text-foreground tabular-nums">
                  {plural(alvo.arquivos, "arquivo")} · {formatBytes(alvo.bytes)}
                </p>
                <p className="mt-0.5 text-muted-foreground">
                  Esta ação não pode ser desfeita. Os objetos saem do MinIO e os
                  registros, do banco.
                </p>
              </div>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={purging} className="max-md:h-10">Cancelar</Button>
          <Button variant="destructive" onClick={purgar} disabled={purging || alvo.arquivos === 0} className="max-md:h-10">
            {purging ? "Purgando..." : "Purgar definitivamente"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function StorageUsageSection({ data, onRefresh }: { data: IStorageUsageAdmin; onRefresh: () => void }) {
  const { totals, by_workspace, tracking_health } = data
  const drivePct = totals.total_bytes > 0 ? (totals.drive_bytes / totals.total_bytes) * 100 : 50
  const [purgeTarget, setPurgeTarget] = useState<IStorageWorkspaceUsage | null>(null)

  return (
    <div className="flex flex-col gap-5">
      {/* Resumo geral */}
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
        <div>
          <span className="text-muted-foreground">Drive:</span>{" "}
          <span className="font-semibold tabular-nums">{formatBytes(totals.drive_bytes)}</span>{" "}
          <span className="text-xs text-muted-foreground tabular-nums">({plural(totals.drive_files, "arquivo")})</span>
        </div>
        <div>
          <span className="text-muted-foreground">Artefatos:</span>{" "}
          <span className="font-semibold tabular-nums">{formatBytes(totals.artifacts_bytes)}</span>{" "}
          <span className="text-xs text-muted-foreground tabular-nums">({plural(totals.artifact_files, "arquivo")})</span>
        </div>
        <div>
          <span className="text-muted-foreground">Total:</span>{" "}
          <span className="font-bold text-foreground tabular-nums">{formatBytes(totals.total_bytes)}</span>
        </div>
      </div>

      {/* Barra de proporção */}
      {totals.total_bytes > 0 && (
        <div className="flex flex-col gap-1.5">
          <div className="flex h-2.5 overflow-hidden rounded-full bg-muted">
            <div className="bg-blue-500 transition-all" style={{ width: `${drivePct}%` }} />
            <div className="bg-amber-500 transition-all" style={{ width: `${100 - drivePct}%` }} />
          </div>
          <div className="flex justify-between text-[11px] text-muted-foreground">
            <span className="flex items-center gap-1"><span className="inline-block size-2 rounded-full bg-blue-500" /> Drive</span>
            <span className="flex items-center gap-1"><span className="inline-block size-2 rounded-full bg-amber-500" /> Artefatos</span>
          </div>
        </div>
      )}

      {/* Saúde do tracking — opcional (campo pode estar ausente em deploys mistos) */}
      {tracking_health && <SaudeDoTracking health={tracking_health} />}

      {/* Tabela por workspace */}
      {by_workspace.length > 0 ? (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-xs md:min-w-[560px]">
            <thead className={CABECALHO_DE_COLUNAS}>
              <tr className="border-b border-border bg-muted/50">
                <th className="px-3 py-2 text-left font-medium text-muted-foreground">Workspace</th>
                <th className="px-3 py-2 text-right font-medium text-muted-foreground">Drive</th>
                <th className="px-3 py-2 text-right font-medium text-muted-foreground">Artefatos</th>
                <th className="px-3 py-2 text-right font-medium text-muted-foreground">Total</th>
                <th className="w-10 px-3 py-2" aria-label="Ações" />
              </tr>
            </thead>
            <tbody>
              {by_workspace.map(ws => (
                <tr key={ws.workspace_id} className={`border-b border-border last:border-b-0 ${LINHA_EMPILHADA}`}>
                  <td className={`px-3 py-2 ${DESTAQUE_DA_FICHA}`}>
                    <div className="font-medium text-foreground">
                      {ws.workspace_name}
                      {/* Lixeira e purgado são situações diferentes: o primeiro
                          ainda é restaurável na seção Lixeira, o segundo já
                          perdeu a linha e só resta liberar o espaço. */}
                      {ws.workspace_state === "trashed" && (
                        <Badge variant="outline" className="ml-2 px-1 py-0 text-[11px]">na lixeira</Badge>
                      )}
                      {(ws.workspace_state === "purged" || (!ws.workspace_state && ws.workspace_deleted)) && (
                        <Badge variant="destructive" className="ml-2 px-1 py-0 text-[11px]">órfão</Badge>
                      )}
                    </div>
                    <div className="text-muted-foreground">{ws.owner_username}</div>
                  </td>
                  <td data-rotulo="drive" className={`px-3 py-2 text-right tabular-nums text-muted-foreground ${CELULA_COM_ROTULO}`}>
                    {formatBytes(ws.drive_bytes)}
                    <span className="ml-1 text-[11px]">({formatarInteiro(ws.drive_files)})</span>
                  </td>
                  <td data-rotulo="artefatos" className={`px-3 py-2 text-right tabular-nums text-muted-foreground ${CELULA_COM_ROTULO}`}>
                    {formatBytes(ws.artifacts_bytes)}
                    <span className="ml-1 text-[11px]">({formatarInteiro(ws.artifact_files)})</span>
                  </td>
                  <td data-rotulo="total" className={`px-3 py-2 text-right font-medium tabular-nums text-foreground ${CELULA_COM_ROTULO}`}>
                    {formatBytes(ws.total_bytes)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-7 text-muted-foreground hover:text-red-500 max-md:size-10"
                      title={`Purgar arquivos de ${ws.workspace_name}`}
                      aria-label={`Purgar arquivos de ${ws.workspace_name}`}
                      disabled={ws.total_bytes === 0 && ws.drive_files === 0 && ws.artifact_files === 0}
                      onClick={() => setPurgeTarget(ws)}
                    >
                      <TbTrash className="size-4" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <VazioEmCirculo icone={TbDatabase} titulo="Nenhum arquivo armazenado" descricao="Nenhum workspace consumiu disco do MinIO ainda." />
      )}

      {purgeTarget && (
        <PurgeStorageDialog
          ws={purgeTarget}
          onClose={() => setPurgeTarget(null)}
          onPurged={onRefresh}
        />
      )}
    </div>
  )
}
