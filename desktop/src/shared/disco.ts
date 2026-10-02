// desktop/src/shared/disco.ts
//
// Limiares de espaço em disco, compartilhados entre a tela e a notificação.
//
// Em `shared/` porque os DOIS lados precisam: o renderer para pintar a barra, o
// main para decidir a notificação. O renderer não pode importar valor de
// `main/ui/notificacoes.ts` (ele puxa `electron`, e o import derrubaria a
// página — o plugin do vite.config.ts barra isso no build), e o main importar
// de `renderer/` seria a dependência invertida.
//
// Divergir os dois números seria pior que duplicá-los: a barra ficaria verde
// enquanto a notificação já avisou, ou o contrário.

/** Abaixo disto, um workflow razoável já pode não conseguir gravar a saída. */
export const DISCO_BAIXO_GB = 5

/** Abaixo disto, é questão de tempo até falhar. */
export const DISCO_CRITICO_GB = 1

export type NivelDisco = 'ok' | 'baixo' | 'critico'

export function nivelDoDisco(livreGb: number | null | undefined): NivelDisco | null {
  if (typeof livreGb !== 'number') return null
  if (livreGb < DISCO_CRITICO_GB) return 'critico'
  if (livreGb < DISCO_BAIXO_GB) return 'baixo'
  return 'ok'
}

export function gb(n: number | null | undefined): string {
  if (typeof n !== 'number') return '—'
  // Abaixo de 10 GB a casa decimal é a diferença entre "dá para hoje" e "não
  // dá"; acima disso ela só polui.
  return n < 10 ? `${n.toFixed(1)} GB` : `${Math.round(n)} GB`
}
