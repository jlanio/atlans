"use client"

import { TbCloudUpload, TbInbox } from "react-icons/tb"
import { Skeleton } from "@/app/components/ui/skeleton"
import * as Estado from "@/app/components/shared/estados"

/**
 * The four Drive states (contract §3): 1st-load skeleton, spine error,
 * first-use empty state and no results. The composition (which one to show)
 * lives in `page.tsx`; the skeleton and the sentences live here, with the
 * frame from `shared/estados.tsx`.
 */

/**
 * First load: draws the real LIST — column header + rows at their real height
 * — so the swap to the content doesn't make the page jump. The page's real
 * header sits on top (`page.tsx` always renders it).
 */
export function SkeletonDoDrive() {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label="Carregando os arquivos"
      className="overflow-hidden rounded-lg border bg-card shadow-xs"
    >
      {/* Column header. */}
      <div className="flex items-center gap-4 border-b bg-muted/40 px-4 py-2.5">
        <Skeleton className="h-3 w-16" />
        <Skeleton className="ml-auto hidden h-3 w-16 lg:block" />
        <Skeleton className="hidden h-3 w-16 lg:block" />
        <Skeleton className="hidden h-3 w-24 lg:block" />
      </div>
      {/* Linhas. */}
      {[0, 1, 2, 3, 4].map(i => (
        <div key={i} className="flex items-center gap-3 border-b border-border/60 px-4 py-3 last:border-b-0">
          <Skeleton className="size-4 shrink-0 rounded" />
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="ml-auto hidden h-5 w-14 rounded-full lg:block" />
          <Skeleton className="hidden h-3.5 w-16 lg:block" />
          <Skeleton className="hidden h-3.5 w-24 lg:block" />
          <Skeleton className="size-7 shrink-0 rounded-md" />
        </div>
      ))}
    </div>
  )
}

/**
 * The listing failed on the 1st load: without it there is no Drive, so the error
 * block takes its place. Only shown when there was NEVER an accepted load — a
 * reload that fails over the ready list keeps it (`page.tsx` does this gate).
 */
export function ErroDeCarga({ mensagem, onTentar }: { mensagem: string; onTentar: () => void }) {
  return <Estado.ErroDeCarga titulo="Não foi possível carregar os arquivos" mensagem={mensagem} onTentar={onTentar} />
}

/**
 * First use: the workspace has no files at all. Invites an upload when the viewer
 * can edit; otherwise explains that only an editor can do it.
 */
export function VazioPrimeiroUso({ canEdit, onEnviar }: { canEdit: boolean; onEnviar: () => void }) {
  return (
    <Estado.VazioPrimeiroUso
      icone={TbInbox}
      titulo="Nenhum arquivo ainda"
      descricao={
        <>
          Os arquivos de entrada — GeoJSON, Shapefile, CSV, KML, GeoPackage e outros — ficam
          aqui e alimentam os nós de leitura dos seus workflows.
        </>
      }
      cta={{ rotulo: "Enviar arquivos", icone: TbCloudUpload, onClick: onEnviar }}
      podeCriar={canEdit}
      pedirA="enviar os primeiros arquivos"
    />
  )
}

/** "Nenhum arquivo com "q"" / "…com este filtro" / "…com "q" e este filtro". */
export function textoDeSemResultado(busca: string, ext: string): string {
  return Estado.textoDeSemResultado({ nada: "Nenhum arquivo", termo: busca, comFiltro: ext !== "" })
}

/** Search or extension chip with no rows: the obvious way out is to clear the slice. */
export function SemResultado({ busca, ext, onLimpar }: { busca: string; ext: string; onLimpar: () => void }) {
  return (
    <Estado.SemResultado
      texto={textoDeSemResultado(busca, ext)}
      dica="Ajuste a busca ou o tipo, ou limpe o recorte."
      onLimpar={onLimpar}
    />
  )
}
