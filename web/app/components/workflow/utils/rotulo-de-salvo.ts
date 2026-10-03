import { dayjs } from "@/lib/dayjs"

/**
 * Text of the save chip at rest: WHEN the last save was, at the precision that
 * answers the question of the moment.
 *
 * In the first few minutes the question is "did I just save?" — hence minutes.
 * After that it is "was it today?" — hence the time. Before today, day and
 * time, and not "3 days ago": a long relative time forces you to do math to
 * know whether it was before or after something else you remember.
 */
export function rotuloDeSalvo(savedAt: number, agora: number = Date.now()): string {
  const decorrido = Math.max(0, agora - savedAt)
  if (decorrido < 60_000) return "Salvo agora"
  if (decorrido < 3_600_000) return `Salvo há ${Math.floor(decorrido / 60_000)} min`

  const momento = dayjs(savedAt)
  if (momento.isSame(dayjs(agora), "day")) return `Salvo às ${momento.format("HH:mm")}`
  return `Salvo em ${momento.format("DD/MM")} às ${momento.format("HH:mm")}`
}
