"use client"
import { useEffect, useState } from "react"
import { useParams } from "next/navigation"
import { motion, AnimatePresence } from "framer-motion"
import { GisFlowService, IWorkflowVersion } from "@/service/GisFlowService"
import { useFlowContext } from "@/context/useFlowContext"
import { Button } from "../../ui/button"
import { Skeleton } from "../../ui/skeleton"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "../../ui/tooltip"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "../../ui/sheet"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../../ui/dialog"
import {
  TbHistory,
  TbRestore,
  TbClock,
  TbAlertTriangle,
  TbMessageCircle,
} from "react-icons/tb"
import { createToast } from "@/utils/createToast"
import "dayjs/locale/pt-br"
import { dayjs, formatLocal, fromNowLocal } from "@/lib/dayjs"
import { dadoOuAviso } from "@/lib/respostas"

dayjs.locale("pt-br")

const _stagger = { hidden: {}, show: { transition: { staggerChildren: 0.04 } } }
const _fadeUp  = { hidden: { opacity: 0, y: 8 }, show: { opacity: 1, y: 0, transition: { duration: 0.25 } } }

// Fade overlay covering the whole screen during the restore
function RestoreOverlay({ visible, version }: { visible: boolean; version: number | null }) {
  const [opacity, setOpacity] = useState(0)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    if (visible) {
      setMounted(true)
      const raf = requestAnimationFrame(() => setOpacity(1))
      return () => cancelAnimationFrame(raf)
    } else {
      setOpacity(0)
      const timer = setTimeout(() => setMounted(false), 400)
      return () => clearTimeout(timer)
    }
  }, [visible])

  if (!mounted) return null

  return (
    <div
      className="fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-background gap-4"
      style={{ opacity, transition: "opacity 400ms ease" }}
    >
      <div className="w-10 h-10 rounded-full border-4 border-muted border-t-primary animate-spin" />
      <p className="text-sm text-muted-foreground">
        Restaurando versão {version}…
      </p>
    </div>
  )
}

const VersionHistory = () => {

  const { id } = useParams<{ id: string }>()
  const { reloadWorkflow } = useFlowContext()
  const [sheetOpen, setSheetOpen] = useState(false)
  const [versions, setVersions] = useState<IWorkflowVersion[]>([])
  const [loading, setLoading] = useState(false)
  // The list didn't arrive: "nenhuma versão salva" would be a false statement.
  const [falhou, setFailed] = useState(false)
  const [restoring, setRestoring] = useState<number | null>(null)
  const [confirmVersion, setConfirmVersion] = useState<number | null>(null)
  const [overlayVisible, setOverlayVisible] = useState(false)

  async function loadVersions() {
    if (!id) return
    setLoading(true)
    const versoes = dadoOuAviso(await GisFlowService.getWorkflowVersions(id), "Erro ao carregar versões")
    if (versoes) setVersions(versoes)
    setFailed(versoes === null)
    setLoading(false)
  }

  async function confirmRestore() {
    if (!id || confirmVersion === null) return
    const version = confirmVersion
    setConfirmVersion(null)
    setRestoring(version)
    const restaurado = dadoOuAviso(await GisFlowService.restoreWorkflowVersion(id, version), "Erro ao restaurar versão")
    if (!restaurado) {
      setRestoring(null)
      return
    }
    setSheetOpen(false)
    setOverlayVisible(true)
    await reloadWorkflow?.()
    setOverlayVisible(false)
    setRestoring(null)
    createToast.success(`Versão ${version} restaurada com sucesso`)
  }

  return (
    <TooltipProvider delayDuration={300}>
      <RestoreOverlay visible={overlayVisible} version={restoring} />

      <Sheet open={sheetOpen} onOpenChange={open => { setSheetOpen(open); if (open) loadVersions() }}>
        <SheetTrigger asChild>
          <Button variant="outline" size="icon" title="Histórico de versões">
            <TbHistory />
          </Button>
        </SheetTrigger>

        {/* A fixed `w-96` (384px) is wider than a 360px phone, and the panel
            spilled past the side instead of taking up the screen. */}
        <SheetContent side="right" className="w-full sm:w-96 flex flex-col gap-0 p-0">
          <SheetHeader className="px-5 pt-5 pb-3 border-b">
            <SheetTitle className="flex items-center gap-2 text-base pr-8">
              <TbHistory className="h-4 w-4 text-muted-foreground" />
              Histórico de versões
            </SheetTitle>
            <div className="flex items-center justify-between gap-2 mt-0.5">
              <p className="text-xs text-muted-foreground">
                Snapshots automáticos criados em cada mudança significativa.
              </p>
              {!loading && versions.length > 0 && (
                <span className="text-xs font-medium text-muted-foreground shrink-0">
                  {versions.length} {versions.length === 1 ? "salva" : "salvas"}
                </span>
              )}
            </div>
          </SheetHeader>

          <div className="flex-1 overflow-y-auto px-5 py-4">
            {/* Loading — skeletons */}
            {loading && (
              <ul className="flex flex-col gap-3">
                {[0, 1, 2, 3].map(i => (
                  <li key={i} className="flex gap-3">
                    <Skeleton className="h-3 w-3 rounded-full mt-2 shrink-0" />
                    <div className="flex-1 flex flex-col gap-2">
                      <Skeleton className="h-4 w-24" />
                      <Skeleton className="h-3 w-32" />
                    </div>
                  </li>
                ))}
              </ul>
            )}

            {/* Empty state — or the failure, which is not the same thing */}
            {!loading && versions.length === 0 && (
              <div className="flex flex-col items-center justify-center py-12 gap-4 text-center">
                <div className="rounded-full bg-muted/60 p-5">
                  <TbHistory size={32} className="text-muted-foreground/40" />
                </div>
                {falhou ? (
                  <div className="space-y-1">
                    <p className="text-sm font-semibold">Não foi possível carregar as versões</p>
                    <p className="text-xs text-muted-foreground max-w-[260px]">
                      Feche e abra o histórico para tentar de novo.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-1">
                    <p className="text-sm font-semibold">Nenhuma versão salva ainda</p>
                    <p className="text-xs text-muted-foreground max-w-[260px]">
                      Versões são criadas automaticamente quando você faz mudanças significativas no workflow.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* List — timeline with cards */}
            {!loading && versions.length > 0 && (
              <motion.ul
                className="flex flex-col gap-2 relative"
                variants={_stagger}
                initial="hidden"
                animate="show"
              >
                {/* Timeline vertical line */}
                <div className="absolute left-[5px] top-2 bottom-2 w-px bg-border" aria-hidden />

                <AnimatePresence>
                  {versions.map((v, i) => {
                    const isLatest = i === 0
                    return (
                      // No `layout`: the per-render measured projection (layout thrash)
                      // isn't needed — enter/exit go through variants.
                      <motion.li
                        key={v.version_number ?? `${v.created_at}-${i}`}
                        variants={_fadeUp}
                        className="flex gap-3 group"
                      >
                        {/* Timeline dot */}
                        <div className="relative z-10 mt-2.5 shrink-0">
                          <div
                            className={
                              isLatest
                                ? "h-3 w-3 rounded-full bg-primary ring-4 ring-primary/15"
                                : "h-3 w-3 rounded-full bg-muted-foreground/40 group-hover:bg-muted-foreground/70 transition-colors"
                            }
                          />
                        </div>

                        {/* Card */}
                        <div
                          className={
                            "flex-1 rounded-lg border p-3.5 transition-all " +
                            (isLatest
                              ? "bg-primary/5 border-primary/30"
                              : "bg-card border-border hover:bg-accent/40 hover:border-border/80")
                          }
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex flex-col gap-0.5 min-w-0">
                              <div className="flex items-center gap-2">
                                <p className="text-sm font-semibold">Versão {v.version_number}</p>
                                {isLatest && (
                                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-primary/15 text-primary border border-primary/20 font-medium">
                                    Mais recente
                                  </span>
                                )}
                              </div>
                              <p className="text-[11px] text-muted-foreground">
                                {formatLocal(v.created_at)}
                              </p>
                              <span className="flex items-center gap-1 text-[10px] text-muted-foreground/70">
                                <TbClock className="h-2.5 w-2.5" />
                                {fromNowLocal(v.created_at)}
                              </span>
                            </div>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button
                                  variant={isLatest ? "secondary" : "ghost"}
                                  size="sm"
                                  className="shrink-0 h-7 px-2 gap-1"
                                  disabled={restoring !== null}
                                  onClick={() => setConfirmVersion(v.version_number)}
                                >
                                  <TbRestore
                                    className={`h-3.5 w-3.5 ${restoring === v.version_number ? "animate-spin" : ""}`}
                                  />
                                  <span className="text-xs hidden sm:inline">Restaurar</span>
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent side="left" className="max-w-[200px]">
                                <p className="text-xs">
                                  Substitui o workflow atual por esta versão. Mudanças não salvas serão perdidas.
                                </p>
                              </TooltipContent>
                            </Tooltip>
                          </div>

                          {v.change_note && (
                            <div className="mt-2.5 flex items-start gap-1.5 rounded-md bg-muted/40 px-2.5 py-1.5">
                              <TbMessageCircle className="h-3 w-3 text-muted-foreground shrink-0 mt-0.5" />
                              <p className="text-xs text-foreground/80 break-words">{v.change_note}</p>
                            </div>
                          )}
                        </div>
                      </motion.li>
                    )
                  })}
                </AnimatePresence>
              </motion.ul>
            )}
          </div>
        </SheetContent>
      </Sheet>

      {/* Restore confirmation dialog */}
      <Dialog open={confirmVersion !== null} onOpenChange={() => setConfirmVersion(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <span className="rounded-full bg-yellow-500/10 p-1.5 border border-yellow-500/20">
                <TbAlertTriangle className="h-4 w-4 text-yellow-600" />
              </span>
              Restaurar versão {confirmVersion}?
            </DialogTitle>
            <DialogDescription className="pt-2">
              O workflow será revertido para o estado da versão {confirmVersion}.
            </DialogDescription>
          </DialogHeader>

          <ul className="flex flex-col gap-2 text-sm">
            <li className="flex items-start gap-2">
              <span className="text-yellow-600 mt-0.5">•</span>
              <span>Mudanças não salvas no editor serão perdidas.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-muted-foreground mt-0.5">•</span>
              <span className="text-muted-foreground">
                Você pode reverter salvando uma nova versão depois.
              </span>
            </li>
          </ul>

          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmVersion(null)}>
              Cancelar
            </Button>
            <Button onClick={confirmRestore} className="gap-1.5">
              <TbRestore className="h-4 w-4" />
              Restaurar versão {confirmVersion}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </TooltipProvider>
  )
}

export default VersionHistory
