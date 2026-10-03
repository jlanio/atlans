"use client"

import React, { useState } from "react"
import {
  TbFileDownload, TbLock, TbDownloadOff, TbDatabase,
} from "react-icons/tb"
import { GisFlowService } from "@/service/GisFlowService"
import type { IArtifactItem } from "@/service/types"
import { Button } from "@/app/components/ui/button"
import { Checkbox } from "@/app/components/ui/checkbox"
import { LocalBadge, isLocalDoExecutor } from "@/app/components/local-badge"
import { COLUMN_HEADER, CARD_HIGHLIGHT, STACKED_ROW } from "@/app/components/shared/tabela-empilhada"
import { formatBytes } from "@/utils/formatters"
import { formatInteger, formatarQuando } from "@/lib/formatos"
import type { ArtifactTab } from "@/app/(dashboard)/artifacts/use-artifacts-query"
import {
  FormatBadge, RetencaoHint, ActivePortalBadge, PortalAnteriorBadge, CachePinBadge,
} from "./badges"

// ── Row: execution artifact ───────────────────────────────────────────────────

// React.memo: the table reaches hundreds of rows and each one mounts a Radix
// Checkbox (with its own state and context). Without this, typing in the search
// or checking ONE row re-rendered all the others.
const ExecutionRow = React.memo(function ExecutionRow({
  item, selected, onToggle,
}: {
  item: IArtifactItem; selected: boolean; onToggle: (id: string) => void
}) {
  const downloadUrl = GisFlowService.getArtifactDownloadUrl(item.id_hash)
  const [downloading, setDownloading] = useState(false)
  const agentOnly = isLocalDoExecutor(item)

  async function handleDownload() {
    setDownloading(true)
    try {
      // `getArtifactDownload` carries the JWT (Bearer) to the platform and returns the
      // MinIO pre-signed URL — the path that respects `item.protected`. Navigating
      // to it in a new tab downloads via the `Content-Disposition: attachment` the
      // signature already carries, WITHOUT pulling the whole file into an
      // in-memory blob (the synchronous `revokeObjectURL` aborted large downloads
      // on Firefox/Safari). We do not use `window.open(getArtifactDownloadUrl)` of
      // the public endpoint: top-level navigation does not carry the Bearer, and a
      // `protected` artifact would regress to 401.
      const res = await GisFlowService.getArtifactDownload(item.id_hash)
      if (res.error) throw new Error(res.error.message ?? `HTTP ${res.status}`)
      const data = res.data
      if (!data?.download_url) throw new Error("download_url ausente")
      window.open(data.download_url, "_blank")
    } catch {
      window.open(downloadUrl, "_blank")
    } finally {
      setDownloading(false)
    }
  }

  return (
    <tr className={`border-b border-border/50 transition-colors hover:bg-accent/40 ${STACKED_ROW}`}>
      <td className="w-8 py-2.5 pl-3 pr-1">
        <Checkbox
          checked={selected}
          onCheckedChange={() => onToggle(item.id_hash)}
          aria-label={`Selecionar ${item.filename}`}
        />
      </td>
      <td className="px-3 py-2.5">
        <p className="max-w-[160px] truncate text-sm font-medium text-foreground" title={item.workflow_name}>
          {item.workflow_name}
        </p>
        <p className="font-mono text-[10px] text-muted-foreground" title={item.run_id}>
          run {item.run_id.slice(0, 8)}…
        </p>
      </td>
      <td className={`px-3 py-2.5 ${CARD_HIGHLIGHT}`}>
        <div className="flex flex-wrap items-center gap-1.5">
          <p className="max-w-[220px] truncate font-mono text-sm text-foreground" title={item.output_key}>{item.output_key}</p>
          <FormatBadge format={item.format} />
          {agentOnly && <LocalBadge executorId={item.executor_id} />}
          {item.is_pinned && <CachePinBadge />}
          {item.protected && (
            <TbLock size={11} className="shrink-0 text-muted-foreground" aria-label="Download protegido por token" />
          )}
        </div>
        <p className="max-w-[200px] truncate text-[10px] text-muted-foreground">{item.filename}</p>
      </td>
      <td className="whitespace-nowrap px-3 py-2.5 text-xs tabular-nums text-muted-foreground">
        <div className="flex flex-col gap-0.5">
          {item.features != null && <span>{formatInteger(item.features)} feat.</span>}
          <span>{formatBytes(item.size_bytes)}</span>
        </div>
      </td>
      <td className="whitespace-nowrap px-3 py-2.5 text-xs text-muted-foreground">
        <div className="flex flex-col gap-0.5">
          <span className="tabular-nums">{formatarQuando(item.created_at)}</span>
          <RetencaoHint expiresAt={item.expires_at} />
        </div>
      </td>
      <td className="px-3 py-2.5 text-right">
        {agentOnly ? (
          <span
            className="inline-flex items-center gap-1 text-xs text-muted-foreground"
            title="O conteúdo permanece no executor e não pode ser baixado pela plataforma."
          >
            <TbDownloadOff size={13} aria-hidden="true" /> Sem download
          </span>
        ) : (
          <Button variant="ghost" size="sm" className="h-7 gap-1 text-xs max-md:h-10" onClick={handleDownload} disabled={downloading}>
            <TbFileDownload size={13} aria-hidden="true" />
            {downloading ? "…" : "Download"}
          </Button>
        )}
      </td>
    </tr>
  )
})

// ── Row: publication artifact ─────────────────────────────────────────────────

const PublicationRow = React.memo(function PublicationRow({
  item, selected, onToggle,
}: {
  item: IArtifactItem; selected: boolean; onToggle: (id: string) => void
}) {
  return (
    <tr className={`border-b border-border/50 transition-colors hover:bg-accent/40 ${STACKED_ROW}`}>
      <td className="w-8 py-2.5 pl-3 pr-1">
        <Checkbox
          checked={selected}
          onCheckedChange={() => onToggle(item.id_hash)}
          aria-label={`Selecionar ${item.filename}`}
        />
      </td>
      <td className="px-3 py-2.5">
        <p className="max-w-[160px] truncate text-sm font-medium text-foreground" title={item.workflow_name}>
          {item.workflow_name}
        </p>
        <p className="font-mono text-[10px] text-muted-foreground" title={item.run_id}>
          run {item.run_id.slice(0, 8)}…
        </p>
      </td>
      <td className={`px-3 py-2.5 ${CARD_HIGHLIGHT}`}>
        <div className="flex flex-wrap items-center gap-1.5">
          <p className="max-w-[220px] truncate font-mono text-sm text-foreground" title={item.output_key}>{item.output_key}</p>
          {item.is_portal_active && <ActivePortalBadge />}
          {item.is_published && !item.is_portal_active && <PortalAnteriorBadge />}
        </div>
        <p className="max-w-[200px] truncate text-[10px] text-muted-foreground">{item.filename}</p>
      </td>
      <td className="whitespace-nowrap px-3 py-2.5 text-xs tabular-nums text-muted-foreground">
        {item.features != null ? `${formatInteger(item.features)} feat.` : "—"}
      </td>
      <td className="whitespace-nowrap px-3 py-2.5 text-xs tabular-nums text-muted-foreground">
        {formatarQuando(item.created_at)}
      </td>
      <td className="px-3 py-2.5 text-right">
        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground" title="Armazenado no banco de dados (portal)">
          <TbDatabase size={13} aria-hidden="true" /> Banco
        </span>
      </td>
    </tr>
  )
})

// ── Reusable table ─────────────────────────────────────────────────────────────

export const ArtifactTable = React.memo(function ArtifactTable({
  items, tab, selected, isOwner, onToggle, onToggleAll,
}: {
  items: IArtifactItem[]; tab: ArtifactTab; selected: Set<string>
  isOwner: boolean; onToggle: (id: string) => void; onToggleAll: () => void
}) {
  // "Todos" (all) is the loaded page, not the whole collection — the selection
  // may contain ids of artifacts that have already left the screen.
  const checkedHere = items.filter(i => selected.has(i.id_hash)).length
  const allSelected  = items.length > 0 && checkedHere === items.length
  const someSelected = checkedHere > 0 && checkedHere < items.length

  return (
    // Own scrolling from `md` up: the columns add up to more than the viewport
    // and the body contains the page's horizontal scroll — without this the last
    // ones would be unreachable instead of merely out of view. On the phone there
    // is no scrolling because there are no columns: the row becomes a card
    // (tabela-empilhada.ts).
    <div className="overflow-hidden rounded-lg border bg-card shadow-xs">
      <div className="overflow-x-auto">
        <table className="w-full text-left md:min-w-[640px]">
          <thead className={COLUMN_HEADER}>
            <tr className="border-b border-border bg-muted/40 text-[11px] uppercase tracking-wide text-muted-foreground">
              <th className="w-8 py-2.5 pl-3 pr-1">
                {isOwner && (
                  <Checkbox
                    checked={allSelected ? true : someSelected ? "indeterminate" : false}
                    onCheckedChange={onToggleAll}
                    aria-label="Selecionar todos os artefatos carregados"
                  />
                )}
              </th>
              <th className="px-3 py-2.5 font-medium">Workflow</th>
              <th className="px-3 py-2.5 font-medium">{tab === "execution" ? "Artefato" : "Camada"}</th>
              <th className="px-3 py-2.5 font-medium">Detalhes</th>
              <th className="px-3 py-2.5 font-medium">Criado</th>
              <th className="px-3 py-2.5 text-right font-medium">Storage</th>
            </tr>
          </thead>
          <tbody>
            {items.map(item =>
              tab === "execution" ? (
                <ExecutionRow key={item.id_hash} item={item} selected={selected.has(item.id_hash)} onToggle={onToggle} />
              ) : (
                <PublicationRow key={item.id_hash} item={item} selected={selected.has(item.id_hash)} onToggle={onToggle} />
              )
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
})
