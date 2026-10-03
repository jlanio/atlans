// web/app/components/workflow/utils/colunas-conhecidas.ts
//
// Which columns reach a node, according to the last run.
//
// Configuring a Join or a filter required guessing the column name — or
// running the workflow, looking at the result, coming back and typing it. The
// executor now records each output's columns (`output_columns` in the event and
// in node_stats), and here they become suggestions right where the question
// comes up.
//
// It is deliberately a HINT, not a validation: the workflow may have changed
// since the run, and the right column may not be in the list. Nothing is
// blocked for not being listed here.

/** Per-node state this lookup needs — what the canvas already keeps. */
export interface NoComColunas {
  id: string
  output_columns?: Record<string, string[]> | null
}

/** Edge, in the format React Flow keeps on the canvas. */
export interface ArestaComChave {
  source: string
  target: string
  data?: { from_key?: string; to_key?: string } | Record<string, unknown>
}

function chaveDeOrigem(aresta: ArestaComChave): string | undefined {
  const dados = (aresta.data ?? {}) as { from_key?: string }
  return dados.from_key || undefined
}

/**
 * Columns reaching the `alvo` node, grouped by input port.
 *
 * The result's key is the name under which the data arrives (`to_key`, or
 * `from_key` when there is no renaming) — the same name the executor uses. In a
 * two-input node like Join, it is what separates "columns of A" from
 * "columns of B", which is exactly the question of whoever is configuring it.
 *
 * A missing `from_key` means the edge spreads ALL the previous node's outputs:
 * then the columns of all of them apply.
 */
export function colunasQueChegam(
  arestas: ArestaComChave[],
  nos: NoComColunas[],
  alvo: string,
): Record<string, string[]> {
  const porId = new Map(nos.map(n => [n.id, n]))
  const saida: Record<string, string[]> = {}

  const acrescentar = (porta: string, colunas: string[] | undefined) => {
    if (!colunas?.length) return
    const atuais = saida[porta] ?? []
    // No repeats: two edges can bring the same column to the same port.
    saida[porta] = [...new Set([...atuais, ...colunas])]
  }

  for (const aresta of arestas) {
    if (aresta.target !== alvo) continue

    const origem = porId.get(aresta.source)
    const colunasPorChave = origem?.output_columns
    if (!colunasPorChave) continue

    const dados = (aresta.data ?? {}) as { to_key?: string }
    const deChave = chaveDeOrigem(aresta)

    if (deChave) {
      acrescentar(dados.to_key || deChave, colunasPorChave[deChave])
      continue
    }
    // No `from_key`: the previous node spreads everything it produced.
    for (const [chave, colunas] of Object.entries(colunasPorChave)) {
      acrescentar(dados.to_key || chave, colunas)
    }
  }

  return saida
}

/** A node's known columns, as `knownColumnsStore` keeps them. */
export interface ColunasConhecidasDoNo {
  porPorta: Record<string, string[]>
  /** false = came from rehydrating the last persisted run, and the workflow may
   *  have changed since then — the suggestion's label warns about it. */
  fresh: boolean
  /** true = the source stat came truncated (8KB cut) — the list may be
   *  reduced to the first 50 columns per port. */
  parciais?: boolean
}

export interface SugestaoDeColunas {
  porPorta: Record<string, string[]>
  todas: string[]
  desatualizadas: boolean
  parciais: boolean
}

export const SEM_SUGESTAO: SugestaoDeColunas = { porPorta: {}, todas: [], desatualizadas: false, parciais: false }

/**
 * Everything the configuration modal needs to know about the columns reaching
 * the `alvo` node: per port, the total, and what the label should warn about.
 *
 * `desatualizadas` and `parciais` are an OR over the contributing PARENTS: it
 * takes only one of them coming from rehydration (or from a truncated stat) for
 * the whole list to deserve the warning — claiming "last run" with data from an
 * earlier run, or completeness with a cut list, would be lying in the most
 * common case.
 */
export function sugestaoParaNo(
  arestas: ArestaComChave[],
  porNo: ReadonlyMap<string, ColunasConhecidasDoNo>,
  alvo: string,
): SugestaoDeColunas {
  if (porNo.size === 0) return SEM_SUGESTAO
  const nos: NoComColunas[] = []
  for (const [id, colunas] of porNo) nos.push({ id, output_columns: colunas.porPorta })
  const porPorta = colunasQueChegam(arestas, nos, alvo)
  const todas = [...new Set(Object.values(porPorta).flat())]
  const desatualizadas = todas.length > 0 && arestas.some(a =>
    a.target === alvo && porNo.get(a.source)?.fresh === false)
  const parciais = todas.length > 0 && arestas.some(a =>
    a.target === alvo && porNo.get(a.source)?.parciais === true)
  return { porPorta, todas, desatualizadas, parciais }
}
