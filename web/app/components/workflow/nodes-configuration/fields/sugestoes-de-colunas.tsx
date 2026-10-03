"use client"

/**
 * The "Vistas na última execução — clique para adicionar" (seen in the last
 * execution — click to add) block.
 *
 * Extracted from ChipsField because the same list appears in FOUR places — the
 * chips field, the three sections of the SetFields editor and the Sort/Switch
 * editors — and each copy would diverge in the label, the ceiling warning and
 * the freshness warning. The caller decides what to do with the chosen name
 * (`onEscolher`) and already hands over the FILTERED list of what still makes
 * sense to offer; `totalConhecido` (unfiltered) is what triggers the ceiling
 * warning.
 */
import { MAX_COLUNAS_SUGERIDAS } from "./chips-field"

interface Props {
  /** Names to offer — already without the ones the current field uses (offering
   *  what is already there is noise). An empty list renders nothing. */
  nomes: string[]
  onEscolher: (nome: string) => void
  /** Total known columns BEFORE the caller's filter — it is against this
   *  that the "(as primeiras 200)" warning of the executor's ceiling applies. */
  totalConhecido?: number
  /** true when the suggestions came from re-hydrating a PERSISTED run (not
   *  from this session): the label warns that the list may have changed. */
  desatualizadas?: boolean
  /** true when the source stat came truncated (the 8KB cut reduces each list
   *  to the first 50): the label warns that the list is partial instead of
   *  claiming completeness. */
  parciais?: boolean
}

const SugestoesDeColunas = ({ nomes, onEscolher, totalConhecido, desatualizadas = false, parciais = false }: Props) => {
  if (nomes.length === 0) return null
  return (
    <div className="flex flex-col gap-1">
      <p className="text-[11px] text-muted-foreground">
        {desatualizadas
          ? "Vistas em execução anterior (podem ter mudado) — clique para adicionar"
          : "Vistas na última execução — clique para adicionar"}
        {parciais && " (lista parcial)"}
        {/* The executor cuts at MAX_COLUNAS per output. Without this warning, a
            wide table would look like it had only 200 columns. */}
        {(totalConhecido ?? nomes.length) >= MAX_COLUNAS_SUGERIDAS && " (as primeiras 200)"}:
      </p>
      <div className="flex flex-wrap gap-1">
        {nomes.map(nome => (
          <button
            key={nome}
            type="button"
            onClick={() => onEscolher(nome)}
            className="rounded border border-dashed border-border px-1.5 py-px font-mono text-[11px] text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground"
          >
            {nome}
          </button>
        ))}
      </div>
    </div>
  )
}

export default SugestoesDeColunas
