"use client"

import { TbAlertTriangle, TbCircleCheck } from "react-icons/tb"

export interface TestResult {
  ok: boolean
  message: string
}

/**
 * Resultado do "Testar credencial", compartilhado pelos modais de criar e editar.
 *
 * Três correções em relação ao parágrafo solto que existia duplicado nos dois:
 *
 * - Ícone junto da cor. Cor sozinha não carrega significado para quem não a
 *   distingue.
 * - Variante `dark:`. `text-green-600` sobre `bg-green-500/10` fica abaixo de
 *   4.5:1 no tema escuro — mesmo problema que a listagem já corrigiu.
 * - Live region. `role="status"` para sucesso e `role="alert"` para falha, senão
 *   o resultado não é anunciado a leitor de tela.
 *
 * A `message` vem do backend e é renderizada literalmente de propósito: para
 * postgresql/mysql/s3 ela reporta conexão real, e para os outros tipos o
 * backend responde "Campos validados com sucesso" — que é a verdade, já que
 * nesses casos ele não toca na rede. Não reescrevemos a mensagem aqui para não
 * prometer mais do que foi feito.
 */
export function TestResultBanner({ result }: { result: TestResult | null }) {
  if (!result) return null

  const Icon = result.ok ? TbCircleCheck : TbAlertTriangle

  return (
    <p
      role={result.ok ? "status" : "alert"}
      aria-live="polite"
      className={`flex items-start gap-1.5 rounded px-2 py-1.5 text-xs ${
        result.ok
          ? "bg-green-500/10 text-green-700 dark:text-green-400"
          : "bg-destructive/10 text-destructive"
      }`}
    >
      <Icon className="mt-px size-3.5 shrink-0" aria-hidden="true" />
      <span className="min-w-0">{result.message}</span>
    </p>
  )
}
