// web/app/components/workflow/utils/colunas-conhecidas.ts
//
// Quais colunas chegam a um nó, segundo a última execução.
//
// Configurar um Join ou um filtro exigia adivinhar o nome da coluna — ou
// executar o fluxo, olhar o resultado, voltar e digitar. O executor passou a
// gravar as colunas de cada saída (`output_columns` no evento e no node_stats),
// e aqui elas viram sugestão no ponto onde a pergunta aparece.
//
// É deliberadamente uma DICA, não uma validação: o fluxo pode ter mudado desde
// a execução, e a coluna certa pode não estar na lista. Nada é bloqueado por
// não constar aqui.

/** Estado por nó de que esta busca precisa — o que o canvas já guarda. */
export interface NoComColunas {
  id: string
  output_columns?: Record<string, string[]> | null
}

/** Aresta, no formato que o React Flow guarda no canvas. */
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
 * Colunas que chegam ao nó `alvo`, agrupadas pela porta de entrada.
 *
 * A chave do resultado é o nome pelo qual o dado chega (`to_key`, ou o
 * `from_key` quando não há renomeação) — o mesmo nome que o executor usa. Num
 * nó de duas entradas como o Join, é o que separa "colunas de A" de
 * "colunas de B", que é justamente a dúvida de quem configura.
 *
 * `from_key` ausente significa que a aresta espalha TODAS as saídas do nó
 * anterior: aí valem as colunas de todas elas.
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
    // Sem repetir: duas arestas podem trazer a mesma coluna para a mesma porta.
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
    // Sem `from_key`: o nó anterior espalha tudo o que produziu.
    for (const [chave, colunas] of Object.entries(colunasPorChave)) {
      acrescentar(dados.to_key || chave, colunas)
    }
  }

  return saida
}

/** Colunas conhecidas de um nó, como a `knownColumnsStore` as guarda. */
export interface ColunasConhecidasDoNo {
  porPorta: Record<string, string[]>
  /** false = veio da re-hidratação do último run persistido, e o fluxo pode
   *  ter mudado desde então — o rótulo da sugestão avisa. */
  fresh: boolean
  /** true = o stat de origem veio truncado (corte de 8KB) — a lista pode
   *  estar reduzida às primeiras 50 colunas por porta. */
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
 * Tudo que o modal de configuração precisa saber sobre as colunas que chegam
 * ao nó `alvo`: por porta, o total, e o que o rótulo deve avisar.
 *
 * `desatualizadas` e `parciais` são um OU sobre os PAIS que contribuem: basta
 * um deles vir da re-hidratação (ou de um stat truncado) para a lista inteira
 * merecer o aviso — afirmar "última execução" com dado de execução anterior,
 * ou completude com lista cortada, seria mentir no caso mais comum.
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
