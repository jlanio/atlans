"use client"

/**
 * O bloco "Vistas na última execução — clique para adicionar".
 *
 * Extraído do ChipsField porque a mesma lista aparece em QUATRO lugares — o
 * campo de fichas, as três seções do editor do SetFields e os editores de
 * Ordenar/Switch — e cada cópia divergiria no rótulo, no aviso de teto e no
 * aviso de frescor. Quem chama decide o que fazer com o nome escolhido
 * (`onEscolher`) e já entrega a lista FILTRADA do que ainda faz sentido
 * oferecer; o `totalConhecido` (sem filtro) é o que dispara o aviso de teto.
 */
import { MAX_COLUNAS_SUGERIDAS } from "./chips-field"

interface Props {
  /** Nomes a oferecer — já sem os que o campo atual usa (oferecer o que já
   *  está lá é ruído). Lista vazia não renderiza nada. */
  nomes: string[]
  onEscolher: (nome: string) => void
  /** Total de colunas conhecidas ANTES do filtro do chamador — é sobre ele
   *  que vale o aviso "(as primeiras 200)" do teto do executor. */
  totalConhecido?: number
  /** true quando as sugestões vieram da re-hidratação de um run PERSISTIDO
   *  (não desta sessão): o rótulo avisa que a lista pode ter mudado. */
  desatualizadas?: boolean
  /** true quando o stat de origem veio truncado (corte de 8KB reduz cada
   *  lista às primeiras 50): o rótulo avisa que a lista é parcial em vez de
   *  afirmar completude. */
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
        {/* O executor corta em MAX_COLUNAS por saída. Sem este aviso, uma
            tabela larga pareceria ter só 200 colunas. */}
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
