// Formata duração em ms para string legível (ex: "123ms" ou "1.23s")
export function formatDuration(ms?: number | null): string | null {
  if (ms == null) return null
  if (ms < 1000) return `${Math.round(ms)}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

/**
 * Formata bytes na maior unidade que couber.
 *
 * Havia quatro cópias disto, em duas famílias incompatíveis: `/artifacts` e
 * `/drive` paravam em MB (um arquivo de 3 GB virava "3072.0 MB"), enquanto
 * `/dashboard` e `/admin/settings` escalavam até TB com precisão adaptativa.
 * Esta é a segunda — a que de fato serve para os tamanhos que o Drive recebe.
 *
 * Precisão adaptativa: 2 casas abaixo de 10, 1 casa abaixo de 100, inteiro
 * acima. Mantém a largura da coluna estável sem perder resolução nos valores
 * pequenos.
 */
export function formatBytes(bytes: number | null | undefined): string {
  if (bytes == null) return "—"
  if (bytes === 0) return "0 B"
  const units = ["B", "KB", "MB", "GB", "TB"]
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  const val = bytes / Math.pow(1024, i)
  const texto = val < 10 ? val.toFixed(2) : val < 100 ? val.toFixed(1) : String(Math.round(val))
  return `${texto} ${units[i]}`
}

/**
 * Classe de cor para uma taxa de sucesso (0..1).
 *
 * A regra estava copiada em quatro telas, e uma delas divergia: três usavam
 * `>= 0.9 verde / >= 0.7 âmbar / resto vermelho`, e `/observability/[id]` usava
 * `>= 0.9 verde / < 0.5 vermelho / resto âmbar`. O efeito era um workflow com
 * 60% de sucesso aparecendo VERMELHO em três telas e ÂMBAR na quarta — o mesmo
 * número, dois julgamentos opostos, dependendo de onde o usuário olhasse.
 *
 * Unificado na regra da maioria (o limiar de 0.7), que é também a mais
 * conservadora: 60% passa a ser vermelho em todos os lugares.
 *
 * `tom` cobre a diferença de paleta que já existia entre as telas
 * (`text-amber-600` no card de executor, `text-yellow-500` nas tabelas).
 */
export function successRateColor(rate: number | null | undefined, tom: "amber" | "yellow" = "yellow"): string {
  if (rate == null) return "text-muted-foreground"
  if (rate >= 0.9) return tom === "amber" ? "text-green-600 dark:text-green-400" : "text-green-500"
  if (rate >= 0.7) return tom === "amber" ? "text-amber-600 dark:text-amber-400" : "text-yellow-500"
  return tom === "amber" ? "text-red-500 dark:text-red-400" : "text-red-500"
}
