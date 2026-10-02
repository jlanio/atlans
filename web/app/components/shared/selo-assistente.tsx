import { TbSparkles } from "react-icons/tb"

import { cn } from "@/lib/utils"

/**
 * Selo "criado pelo assistente" — o mesmo em toda lista do painel.
 *
 * Os fluxos que o assistente da Home cria são fluxos completos como os
 * outros: aparecem em Projetos, no Dashboard, no Histórico, na paleta e nos
 * seletores. O selo é o que diz de onde vieram, para não se confundirem com o
 * que a pessoa montou no editor — sem ele "passavam despercebidos".
 *
 * Mesma faísca dos Agendamentos da Home (o molde), em `primary`; forma e
 * tamanho do selo de sub-fluxo, para os dois conviverem na mesma linha.
 *
 * `compacto` deixa só o ícone, para lugares onde o texto não cabe (linhas de
 * uma tabela densa, item de paleta). O `title`/`aria-label` continuam lá: a
 * informação não pode depender de reconhecer o desenho.
 */
export function SeloAssistente({
  origem, compacto = false, className,
}: {
  origem: string | null | undefined
  compacto?: boolean
  className?: string
}) {
  if (origem !== "assistente") return null

  const rotulo = "Fluxo criado pelo assistente"

  if (compacto) {
    return (
      <TbSparkles
        size={12}
        className={cn("shrink-0 text-primary", className)}
        title={rotulo}
        aria-label={rotulo}
      />
    )
  }

  return (
    <span
      title={rotulo}
      aria-label={rotulo}
      className={cn(
        "inline-flex shrink-0 items-center gap-1 rounded bg-primary/10 px-1.5 py-px text-[10px] font-medium text-primary",
        className,
      )}
    >
      <TbSparkles size={11} aria-hidden="true" /> assistente
    </span>
  )
}
