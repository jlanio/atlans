"use client"

import { TbPlus, TbSitemap } from "react-icons/tb"
import { Skeleton } from "@/app/components/ui/skeleton"
import * as Estado from "@/app/components/shared/estados"
import { formatarInteiro } from "@/lib/formatos"
import { ESTADO_PADRAO, type Filtro } from "./projetos-url"

/**
 * Estados da tela de Projetos (docs/specs/projects.md §3.10): carregando,
 * vazio de primeiro uso, sem resultado, erro de carga e métricas
 * indisponíveis. Cada um diz o que aconteceu e o que fazer a seguir. Aqui
 * ficam o skeleton e as frases; a moldura é a de `shared/estados.tsx`.
 */

/**
 * Primeira carga: o cabeçalho real fica por cima (quem compõe a página o
 * renderiza), e aqui vai o desenho da lista — um grupo com três linhas e duas
 * soltas, com a altura da linha de verdade, para a troca não pular.
 */
export function SkeletonDeProjetos() {
  return (
    <div role="status" aria-busy="true" aria-label="Carregando projetos" className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5 rounded-lg border bg-muted/30 p-2.5">
        <div className="flex items-center gap-2 px-1 py-1.5">
          <Skeleton className="size-4 rounded" />
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-3 w-24" />
        </div>
        {[0, 1, 2].map(i => <LinhaFantasma key={i} />)}
      </div>
      <div className="flex flex-col gap-1.5">
        {[0, 1].map(i => <LinhaFantasma key={i} />)}
      </div>
    </div>
  )
}

function LinhaFantasma() {
  return (
    <div className="flex h-14 items-center gap-3 rounded-lg border bg-card px-3 shadow-xs">
      <Skeleton className="size-[34px] shrink-0 rounded-lg" />
      <div className="flex flex-1 flex-col gap-1.5">
        <Skeleton className="h-3.5 w-1/3" />
        <Skeleton className="h-3 w-1/2" />
      </div>
      <Skeleton className="hidden h-3.5 w-40 md:block" />
      <Skeleton className="size-8 rounded-md" />
    </div>
  )
}

const PASSOS: { titulo: string; detalhe: string }[] = [
  { titulo: "Desenhe", detalhe: "Ligue os nós de leitura, processamento e saída no editor." },
  { titulo: "Execute uma vez", detalhe: "Rode pela lista e confira o resultado." },
  { titulo: "Agende ou exponha", detalhe: "Um horário, um webhook, um arquivo que chega — ou um portal." },
]

/** Sem workflow e sem grupo: a tela ensina o que é um workflow e por onde começar. */
export function VazioPrimeiroUso({ canEdit, onCriar }: { canEdit: boolean; onCriar: () => void }) {
  return (
    <Estado.VazioPrimeiroUso
      icone={TbSitemap}
      titulo="Comece pelo primeiro workflow"
      descricao={
        <>
          Um workflow encadeia nós de leitura, processamento e saída. Ele roda quando você manda,
          num horário, ou quando um webhook ou um arquivo chega.
        </>
      }
      passos={PASSOS}
      cta={{ rotulo: "Criar o primeiro workflow", icone: TbPlus, onClick: onCriar }}
      podeCriar={canEdit}
      pedirA="criar o primeiro workflow"
    />
  )
}

/** "Nenhum workflow com «q»" / "…com este filtro" / "…com «q» e este filtro". */
export function textoDeSemResultado(q: string, filtro: Filtro): string {
  return Estado.textoDeSemResultado({ nada: "Nenhum workflow", termo: q, comFiltro: filtro !== ESTADO_PADRAO.filtro })
}

/**
 * Busca ou chip sem nenhuma linha. `semFiltro` é quantos casariam só com a
 * busca: quando há, a saída óbvia é tirar o chip, e a tela diz isso.
 */
export function SemResultado({ q, filtro, semFiltro, onLimpar }: {
  q: string
  filtro: Filtro
  semFiltro: number | null
  onLimpar: () => void
}) {
  const termo = q.trim()
  return (
    <Estado.SemResultado
      texto={textoDeSemResultado(q, filtro)}
      dica={semFiltro != null && semFiltro > 0 && termo
        ? `Há ${formatarInteiro(semFiltro)} com «${termo}» sem o filtro.`
        : undefined}
      onLimpar={onLimpar}
    />
  )
}

/** Listagem ou grupos falharam: sem eles não há estante. */
export function ErroDeCarga({ mensagem, onTentar }: { mensagem: string; onTentar: () => void }) {
  return <Estado.ErroDeCarga titulo="Não foi possível carregar os projetos" mensagem={mensagem} onTentar={onTentar} />
}

/** Só as métricas falharam: a lista continua inteira, sem a coluna "como anda". */
export function MetricasIndisponiveis({ onTentar }: { onTentar: () => void }) {
  return (
    <Estado.AvisoAmbar onTentar={onTentar}>
      Sem dados de execução agora — a lista continua completa.
    </Estado.AvisoAmbar>
  )
}
