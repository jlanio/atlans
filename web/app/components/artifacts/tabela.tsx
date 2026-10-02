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
import { CABECALHO_DE_COLUNAS, DESTAQUE_DA_FICHA, LINHA_EMPILHADA } from "@/app/components/shared/tabela-empilhada"
import { formatBytes } from "@/utils/formatters"
import { formatarInteiro, formatarQuando } from "@/lib/formatos"
import type { ArtifactTab } from "@/app/(dashboard)/artifacts/use-artifacts-query"
import {
  FormatBadge, RetencaoHint, PortalAtivoBadge, PortalAnteriorBadge, CachePinBadge,
} from "./badges"

// ── Linha: artefato de execução ───────────────────────────────────────────────

// React.memo: a tabela chega a centenas de linhas e cada uma monta um Checkbox
// do Radix (estado e contexto próprios). Sem isto, digitar na busca ou marcar
// UMA linha re-renderizava todas as outras.
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
      // `getArtifactDownload` leva o JWT (Bearer) à plataforma e devolve a URL
      // pré-assinada do MinIO — o caminho que respeita `item.protected`. Navegar
      // até ela numa aba nova baixa pelo `Content-Disposition: attachment` que a
      // assinatura já carrega, SEM puxar o arquivo inteiro para um blob em
      // memória (o `revokeObjectURL` síncrono abortava downloads grandes no
      // Firefox/Safari). Não usamos `window.open(getArtifactDownloadUrl)` do
      // endpoint público: navegação de topo não leva o Bearer, e o artefato
      // `protected` regrediria para 401.
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
    <tr className={`border-b border-border/50 transition-colors hover:bg-accent/40 ${LINHA_EMPILHADA}`}>
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
      <td className={`px-3 py-2.5 ${DESTAQUE_DA_FICHA}`}>
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
          {item.features != null && <span>{formatarInteiro(item.features)} feat.</span>}
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

// ── Linha: artefato de publicação ─────────────────────────────────────────────

const PublicationRow = React.memo(function PublicationRow({
  item, selected, onToggle,
}: {
  item: IArtifactItem; selected: boolean; onToggle: (id: string) => void
}) {
  return (
    <tr className={`border-b border-border/50 transition-colors hover:bg-accent/40 ${LINHA_EMPILHADA}`}>
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
      <td className={`px-3 py-2.5 ${DESTAQUE_DA_FICHA}`}>
        <div className="flex flex-wrap items-center gap-1.5">
          <p className="max-w-[220px] truncate font-mono text-sm text-foreground" title={item.output_key}>{item.output_key}</p>
          {item.is_portal_active && <PortalAtivoBadge />}
          {item.is_published && !item.is_portal_active && <PortalAnteriorBadge />}
        </div>
        <p className="max-w-[200px] truncate text-[10px] text-muted-foreground">{item.filename}</p>
      </td>
      <td className="whitespace-nowrap px-3 py-2.5 text-xs tabular-nums text-muted-foreground">
        {item.features != null ? `${formatarInteiro(item.features)} feat.` : "—"}
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

// ── Tabela reutilizável ────────────────────────────────────────────────────────

export const ArtifactTable = React.memo(function ArtifactTable({
  items, tab, selected, isOwner, onToggle, onToggleAll,
}: {
  items: IArtifactItem[]; tab: ArtifactTab; selected: Set<string>
  isOwner: boolean; onToggle: (id: string) => void; onToggleAll: () => void
}) {
  // "Todos" é a página carregada, não a coleção inteira — a seleção pode conter
  // ids de artefatos que já saíram da tela.
  const marcadosAqui = items.filter(i => selected.has(i.id_hash)).length
  const allSelected  = items.length > 0 && marcadosAqui === items.length
  const someSelected = marcadosAqui > 0 && marcadosAqui < items.length

  return (
    // Rolagem própria de `md` para cima: as colunas somam mais que a viewport
    // e o body contém a rolagem lateral da página — sem isto as últimas
    // ficariam inalcançáveis em vez de apenas fora de vista. No telefone não há
    // rolagem porque não há colunas: a linha vira ficha (tabela-empilhada.ts).
    <div className="overflow-hidden rounded-lg border bg-card shadow-xs">
      <div className="overflow-x-auto">
        <table className="w-full text-left md:min-w-[640px]">
          <thead className={CABECALHO_DE_COLUNAS}>
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
