"use client"

import { TbFile, TbSearch, TbWorld } from "react-icons/tb"
import { Input } from "@/app/components/ui/input"
import { cn } from "@/lib/utils"
import { formatarInteiro } from "@/lib/formatos"
import type { ArtifactTab } from "@/app/(dashboard)/artifacts/use-artifacts-query"

/**
 * Controles de Artefatos: as abas e o filtro de formato viram grupos de toggle
 * canônicos (contrato §1) — `role="group"`, `aria-pressed`, ativo em `bg-accent`
 * —, no lugar das abas com borda inferior e dos botões default/outline soltos
 * que a tela tinha. A busca segue igual (vai ao servidor com debounce na
 * página); aqui é só o campo.
 */

const ABAS: { valor: ArtifactTab; rotulo: string; icone: typeof TbFile }[] = [
  { valor: "execution",   rotulo: "Execução",   icone: TbFile },
  { valor: "publication", rotulo: "Publicação", icone: TbWorld },
]

/** Execução × Publicação. O contador é o total do SERVIDOR da aba aberta. */
export function AbasDeArtefatos({ tab, total, onTab }: {
  tab: ArtifactTab; total: number; onTab: (t: ArtifactTab) => void
}) {
  return (
    <div
      role="group"
      aria-label="Tipo de artefato"
      className="inline-flex h-8 overflow-hidden rounded-md border bg-card max-md:h-10"
    >
      {ABAS.map(({ valor, rotulo, icone: Icone }) => {
        const ativo = valor === tab
        return (
          <button
            key={valor}
            type="button"
            aria-pressed={ativo}
            onClick={() => onTab(valor)}
            className={cn(
              "flex items-center gap-1.5 px-3 text-xs font-medium outline-none transition-colors",
              "border-l first:border-l-0 focus-visible:z-10 focus-visible:ring-[3px] focus-visible:ring-ring/50",
              ativo ? "bg-accent text-foreground" : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
            )}
          >
            <Icone size={14} aria-hidden="true" />
            {rotulo}
            {/* Só mostra a contagem da aba ATIVA: o total é do servidor para o
                filtro aberto, e não há como saber o da outra aba sem uma segunda
                requisição. */}
            {ativo && total > 0 && (
              <span className="rounded-full bg-background/70 px-1.5 py-0.5 text-[10px] tabular-nums">
                {formatarInteiro(total)}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}

/** Campo de busca (o debounce e a ida ao servidor moram na página). */
export function BuscaDeArtefatos({ valor, onChange }: {
  valor: string; onChange: (v: string) => void
}) {
  return (
    <div className="relative w-full max-w-xs">
      <TbSearch size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
      <Input
        placeholder="Buscar por workflow, chave ou arquivo…"
        value={valor}
        onChange={e => onChange(e.target.value)}
        aria-label="Buscar artefatos"
        className="h-8 pl-8 text-sm max-md:h-10"
      />
    </div>
  )
}

/**
 * Filtro de formato como grupo de toggle. "Todos" ("all") é sempre o primeiro;
 * só aparece quando há mais de um formato acumulado (senão o filtro não separa
 * nada).
 */
export function FiltroDeFormato({ formatos, atual, onFormato }: {
  formatos: string[]; atual: string; onFormato: (f: string) => void
}) {
  if (formatos.length <= 1) return null
  const opcoes = ["all", ...formatos]
  return (
    <div
      role="group"
      aria-label="Formato"
      className="inline-flex h-8 overflow-hidden rounded-md border bg-card max-md:h-10"
    >
      {opcoes.map(f => {
        const ativo = atual === f
        return (
          <button
            key={f}
            type="button"
            aria-pressed={ativo}
            onClick={() => onFormato(f)}
            className={cn(
              "px-3 text-xs font-medium outline-none transition-colors",
              "border-l first:border-l-0 focus-visible:z-10 focus-visible:ring-[3px] focus-visible:ring-ring/50",
              ativo ? "bg-accent text-foreground" : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
            )}
          >
            {f === "all" ? "Todos" : f.toUpperCase()}
          </button>
        )
      })}
    </div>
  )
}
