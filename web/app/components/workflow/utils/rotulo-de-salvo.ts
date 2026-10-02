import { dayjs } from "@/lib/dayjs"

/**
 * Texto do chip de salvamento em repouso: QUANDO foi o último save, na precisão
 * que responde a pergunta do momento.
 *
 * Nos primeiros minutos a pergunta é "acabei de salvar?" — daí minutos. Depois
 * disso é "foi hoje?" — daí a hora. Antes de hoje, dia e hora, e não "há 3
 * dias": um relativo longo obriga a fazer conta para saber se foi antes ou
 * depois de outra coisa que se lembra.
 */
export function rotuloDeSalvo(salvoEm: number, agora: number = Date.now()): string {
  const decorrido = Math.max(0, agora - salvoEm)
  if (decorrido < 60_000) return "Salvo agora"
  if (decorrido < 3_600_000) return `Salvo há ${Math.floor(decorrido / 60_000)} min`

  const momento = dayjs(salvoEm)
  if (momento.isSame(dayjs(agora), "day")) return `Salvo às ${momento.format("HH:mm")}`
  return `Salvo em ${momento.format("DD/MM")} às ${momento.format("HH:mm")}`
}
