"use client"

import { useEffect, useId, useMemo, useRef, useState } from "react"
import {
  TbAlertTriangle, TbBan, TbCheck, TbLoader2, TbPlus, TbRefresh, TbX,
} from "react-icons/tb"
import { Badge } from "@/app/components/ui/badge"
import { Button } from "@/app/components/ui/button"
import { Input } from "@/app/components/ui/input"
import { Label } from "@/app/components/ui/label"
import { GisFlowService } from "@/service/GisFlowService"
import type { IWorkspaceNotificationTarget } from "@/service/types"
import { createToast } from "@/utils/createToast"
import { isHostAllowed, validateAllowlistPattern } from "@/lib/hostname-allowlist"
import { useFetchData } from "@/app/hooks/useFetchData"
import { SheetSection } from "./section-shell"

interface Props {
  workspaceId: string
  canManage: boolean
  /** Flags blocked workflows for the navigation's alert badge. */
  onAlertChange?: (hasAlert: boolean) => void
}

/**
 * Host allowlist for the workspace's webhooks.
 *
 * The column already existed and was already blocking notifications in
 * production — with no UI at all. Whoever set up a webhook and did not receive
 * it had no way to find out why: the block only showed up as a warning in the
 * server log. Hence the preview: the section shows, for each workflow that
 * notifies, whether the current list lets it through.
 */
export function NotificationsSection({ workspaceId, canManage, onAlertChange }: Props) {
  const inputId = useId()

  const [saveError, setSaveError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [draft, setDraft] = useState<string[]>([])

  const [newHost, setNewHost] = useState("")
  const [inputError, setInputError] = useState<string | null>(null)

  // Read when each response arrives: the load cannot depend on `draft`
  // without being redone on every keystroke.
  const dirtyRef = useRef(false)

  // Loading is `useFetchData`, with the workspace as a dep (and the guard against
  // a previous workspace's response). Its `error` is the READ failure, kept
  // separate from the write failure on purpose: `SheetSection` swaps the content
  // for the error, and using the same state for both would make a rejected PUT
  // wipe the chips, the field and the Save button off the screen — taking with
  // it the draft that caused the rejection, with no way to fix it.
  const { data, loading, error, refetch: load, setData } = useFetchData(
    () => GisFlowService.getWorkspaceNotifications(workspaceId),
    "Não foi possível carregar a allowlist.",
    [workspaceId], 0,
    {
      // The draft survives the refresh: "Atualizar" (Refresh) exists to bring the
      // current workflows, not to silently erase the edit in progress.
      onDados: dados => { if (!dirtyRef.current) setDraft(dados.allowlist ?? []) },
    },
  )
  const saved = useMemo(() => data?.allowlist ?? [], [data])
  const workflows = useMemo<IWorkspaceNotificationTarget[]>(() => data?.workflows ?? [], [data])

  const dirty = useMemo(
    () => draft.length !== saved.length || draft.some((h, i) => h !== saved[i]),
    [draft, saved],
  )

  useEffect(() => { dirtyRef.current = dirty }, [dirty])

  // Recomputed with the DRAFT, not with what is saved: this is what lets you see
  // the effect of a change before saving it. The backend recomputes and returns
  // the authoritative result on the PUT.
  const preview = useMemo(
    () => workflows.map(wf => ({ ...wf, allowed: isHostAllowed(wf.host, draft) })),
    [workflows, draft],
  )

  const blockedNow = preview.filter(wf => !wf.allowed)
  // The ones the pending edit would start blocking — the warning is only useful
  // if it separates "already blocked" from "you just blocked".
  const newBlocks = dirty
    ? preview.filter(wf => !wf.allowed && workflows.find(w => w.id_hash === wf.id_hash)?.allowed)
    : []

  useEffect(() => {
    if (!loading && !error) onAlertChange?.(workflows.some(wf => !wf.allowed))
  }, [workflows, loading, error, onAlertChange])

  function add() {
    const valor = newHost.trim().toLowerCase()
    const problema = validateAllowlistPattern(valor)
    if (problema) {
      setInputError(problema)
      return
    }
    if (draft.includes(valor)) {
      setInputError("Este host já está na lista.")
      return
    }
    setDraft(prev => [...prev, valor])
    setNewHost("")
    setInputError(null)
  }

  function remove(host: string) {
    setDraft(prev => prev.filter(h => h !== host))
  }

  async function save() {
    if (saving) return
    setSaving(true)
    const res = await GisFlowService.updateWorkspaceNotificationAllowlist(workspaceId, draft)
    if (res.error) {
      // The draft stays on screen: the backend's message usually points at the
      // exact entry that was rejected, and without the chips there would be
      // nothing to fix.
      const msg = res.error.message ?? "Erro ao salvar a allowlist."
      setSaveError(msg)
      createToast.error(msg)
    } else {
      setSaveError(null)
      setData({ allowlist: res.data?.allowlist ?? [], workflows: res.data?.workflows ?? [] })
      setDraft(res.data?.allowlist ?? [])
      createToast.success("Allowlist de notificações salva.")
    }
    setSaving(false)
  }

  return (
    <SheetSection
      title="Notificações"
      description={
        <>
          Restringe para quais hosts os workflows deste workspace podem enviar
          notificações. <strong className="text-foreground">Com a lista vazia, qualquer
          URL que passe na verificação de SSRF é aceita.</strong> Ao adicionar hosts, tudo
          que ficar de fora é bloqueado em silêncio após a execução.
          {!canManage && " Apenas administradores podem alterar."}
        </>
      }
      action={
        <Button
          variant="ghost"
          size="icon"
          onClick={load}
          disabled={loading}
          aria-label="Atualizar allowlist"
          title="Atualizar"
        >
          <TbRefresh className={`size-4 ${loading ? "animate-spin" : ""}`} />
        </Button>
      }
      loading={loading}
      error={error}
      onRetry={load}
    >
      <div className="space-y-5">
        {canManage && (
          <div className="grid gap-1.5">
            <Label htmlFor={inputId}>Adicionar host</Label>
            <div className="flex gap-2">
              <Input
                id={inputId}
                value={newHost}
                placeholder="exemplo.com ou *.exemplo.com"
                disabled={saving}
                aria-invalid={!!inputError}
                onChange={e => { setNewHost(e.target.value); setInputError(null) }}
                onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); add() } }}
              />
              <Button variant="outline" size="icon" onClick={add} disabled={saving} aria-label="Adicionar host">
                <TbPlus className="size-4" />
              </Button>
            </div>
            {inputError && <p className="text-xs text-destructive">{inputError}</p>}
          </div>
        )}

        <div className="space-y-2">
          {draft.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {draft.map(host => (
                <Badge key={host} variant="secondary" className="gap-1.5 font-mono text-xs">
                  {host}
                  {canManage && (
                    <button
                      type="button"
                      onClick={() => remove(host)}
                      disabled={saving}
                      aria-label={`Remover ${host}`}
                      className="transition-colors hover:text-destructive"
                    >
                      <TbX className="size-3" />
                    </button>
                  )}
                </Badge>
              ))}
            </div>
          ) : (
            <p className="text-sm italic text-muted-foreground">
              Nenhum host configurado — todas as notificações são permitidas.
            </p>
          )}

          {canManage && (
            <div className="space-y-2 pt-1">
              <div className="flex items-center gap-3">
                <Button size="sm" onClick={save} disabled={!dirty || saving} className="gap-1.5">
                  {saving && <TbLoader2 className="size-4 animate-spin" aria-hidden="true" />}
                  {saving ? "Salvando…" : "Salvar allowlist"}
                </Button>
                {dirty && !saving && (
                  <span className="text-xs text-muted-foreground">Alterações não salvas</span>
                )}
              </div>
              {saveError && (
                <p role="alert" className="flex items-start gap-1.5 text-xs text-destructive">
                  <TbAlertTriangle className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
                  {saveError}
                </p>
              )}
            </div>
          )}
        </div>

        {newBlocks.length > 0 && (
          <div
            role="alert"
            className="space-y-1.5 rounded-md border border-amber-500/25 bg-amber-500/5 p-3 text-xs"
          >
            <div className="flex items-start gap-2">
              <TbAlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-700 dark:text-amber-400" aria-hidden="true" />
              <div className="space-y-1">
                <p className="text-foreground">
                  Ao salvar, {newBlocks.length === 1
                    ? "1 workflow deixa"
                    : `${newBlocks.length} workflows deixam`}{" "}
                  de enviar notificação:
                </p>
                <ul className="list-inside list-disc text-muted-foreground">
                  {newBlocks.map(wf => (
                    <li key={wf.id_hash}>
                      {wf.name} <span className="font-mono">({wf.host || "host inválido"})</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        <div className="space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Workflows que notificam
          </h4>
          {preview.length === 0 ? (
            <p className="rounded-md border border-dashed px-3 py-6 text-center text-sm text-muted-foreground">
              Nenhum workflow deste workspace envia notificação.
            </p>
          ) : (
            <ul className="space-y-1.5">
              {preview.map(wf => (
                <li
                  key={wf.id_hash}
                  className={`flex items-center gap-2 rounded-md border px-3 py-2 text-sm ${
                    wf.allowed ? "" : "border-amber-500/40 bg-amber-500/5"
                  }`}
                >
                  {wf.allowed ? (
                    <TbCheck className="size-4 shrink-0 text-green-600" aria-hidden="true" />
                  ) : (
                    <TbBan className="size-4 shrink-0 text-amber-700 dark:text-amber-400" aria-hidden="true" />
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{wf.name}</p>
                    <p className="truncate font-mono text-xs text-muted-foreground">
                      {wf.host || wf.notification_url}
                    </p>
                  </div>
                  <span
                    className={`shrink-0 text-xs ${
                      wf.allowed ? "text-muted-foreground" : "text-amber-700 dark:text-amber-400"
                    }`}
                  >
                    {wf.allowed ? "Permitido" : "Bloqueado"}
                  </span>
                </li>
              ))}
            </ul>
          )}
          {blockedNow.length > 0 && !dirty && (
            <p className="text-xs text-muted-foreground">
              Notificações bloqueadas não geram erro na execução — elas simplesmente
              não são enviadas.
            </p>
          )}
        </div>
      </div>
    </SheetSection>
  )
}
