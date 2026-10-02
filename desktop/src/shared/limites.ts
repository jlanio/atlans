// desktop/src/shared/limites.ts
//
// Padrões e faixas das variáveis de execução que a tela de Ajustes edita — o
// espelho, num lugar só, de `executor/config.py`.
//
// Quem manda é o executor: ele lê cada variável com
// `executor/_ambiente.py::ler_int`, que descarta o valor fora da faixa e usa o
// padrão. Uma faixa diferente aqui faz a tela mentir — e, pior, faz o salvar
// gravar o número DELA por cima do que o executor usava. `limites.test.ts` lê
// `executor/config.py` e falha se os dois lados divergirem.
//
// Em `shared/` porque o main (leitura e gravação do `.env`) e o renderer (a
// validação da tela) precisam dos MESMOS números, e o renderer não pode
// importar valor de `src/main` (ver vite.config.ts). Um JSON em `executor/`,
// lido pelo Python e importado aqui, seria fonte única de verdade; mas o
// servidor de desenvolvimento do Vite só serve arquivos de dentro de
// `desktop/` (`server.fs.allow`), e o renderer quebraria em `npm run dev`.

export interface Faixa {
  /** O que o executor usa quando a variável falta ou é inválida. */
  padrao: number
  min: number
  /** `null` quando o executor não impõe teto. */
  max: number | null
}

export const LIMITES = {
  /** EXECUTOR_MAX_CONCURRENT */
  workers: { padrao: 4, min: 1, max: 256 },
  /** EXECUTOR_MAX_QUEUE_SIZE */
  filaMax: { padrao: 50, min: 1, max: 10_000 },
  /**
   * EXECUTOR_JOB_TIMEOUT. Sem teto, como no executor: a tela tinha um de
   * 86 400 s, e com 100 000 no `.env` mostrava 3600 enquanto o executor usava
   * 100 000 — e salvar qualquer ajuste gravava o 3600.
   */
  timeoutS: { padrao: 3600, min: 1, max: null },
} as const satisfies Record<string, Faixa>

export function dentroDaFaixa(n: number, faixa: Faixa): boolean {
  return Number.isSafeInteger(n) && n >= faixa.min && (faixa.max === null || n <= faixa.max)
}

/**
 * O inteiro que o executor enxerga num valor do `.env`, ou o padrão.
 *
 * Imita o `int()` do Python sobre o que o python-dotenv entrega: espaços nas
 * pontas, sinal e `_` entre dígitos valem; o comentário de fim de linha
 * (` # ...`) já foi descartado pelo dotenv; qualquer outra coisa é inválida.
 * O `parseInt` de antes lia "8x" como 8 — a tela mostrava 8 workers e o
 * executor, que recusa "8x", rodava com 4.
 */
export function inteiroDoEnv(bruto: string | undefined, faixa: Faixa): number {
  const m = /^\s*([+-]?\d+(?:_\d+)*)(?:\s+#.*)?\s*$/.exec(bruto ?? '')
  const n = m ? Number(m[1]!.replace(/_/g, '')) : Number.NaN
  return dentroDaFaixa(n, faixa) ? n : faixa.padrao
}
