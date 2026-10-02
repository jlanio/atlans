"use client"

import { TbCloudUpload, TbInbox } from "react-icons/tb"
import { Skeleton } from "@/app/components/ui/skeleton"
import * as Estado from "@/app/components/shared/estados"

/**
 * Os quatro estados do Drive (contrato §3): skeleton da 1ª carga, erro de
 * espinha, vazio de primeiro uso e sem resultado. A composição (qual mostrar)
 * fica no `page.tsx`; aqui ficam o skeleton e as frases, com a moldura de
 * `shared/estados.tsx`.
 */

/**
 * Primeira carga: desenha a LISTA real — cabeçalho de colunas + linhas com a
 * altura de verdade — para a troca para o conteúdo não pular a página. O
 * cabeçalho real da página fica por cima (o `page.tsx` sempre o renderiza).
 */
export function SkeletonDoDrive() {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label="Carregando os arquivos"
      className="overflow-hidden rounded-lg border bg-card shadow-xs"
    >
      {/* Cabeçalho de colunas. */}
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
 * A listagem caiu na 1ª carga: sem ela não há Drive, então o bloco de erro toma
 * o lugar. Só entra quando NUNCA houve carga aceita — uma recarga que falha
 * sobre a lista pronta a mantém (o `page.tsx` faz esse gate).
 */
export function ErroDeCarga({ mensagem, onTentar }: { mensagem: string; onTentar: () => void }) {
  return <Estado.ErroDeCarga titulo="Não foi possível carregar os arquivos" mensagem={mensagem} onTentar={onTentar} />
}

/**
 * Primeiro uso: o workspace não tem nenhum arquivo. Convida a enviar quando quem
 * olha pode editar; senão explica que só um editor faz isso.
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

/** "Nenhum arquivo com «q»" / "…com este filtro" / "…com «q» e este filtro". */
export function textoDeSemResultado(busca: string, ext: string): string {
  return Estado.textoDeSemResultado({ nada: "Nenhum arquivo", termo: busca, comFiltro: ext !== "" })
}

/** Busca ou chip de extensão sem nenhuma linha: a saída óbvia é limpar o recorte. */
export function SemResultado({ busca, ext, onLimpar }: { busca: string; ext: string; onLimpar: () => void }) {
  return (
    <Estado.SemResultado
      texto={textoDeSemResultado(busca, ext)}
      dica="Ajuste a busca ou o tipo, ou limpe o recorte."
      onLimpar={onLimpar}
    />
  )
}
