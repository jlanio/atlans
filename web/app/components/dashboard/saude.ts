import type { INowBlock } from "@/service/types"
import { formatarDuracao, plural } from "@/lib/formatos"

/**
 * Dashboard health — the tone and the ONE-sentence verdict at the top of the
 * Dashboard (docs/specs/dashboard.md §3.4). Pure: receives the instant (`now`)
 * the metrics already bring, a `temAtencao` (for the tone) and the count per
 * type of the items in the "Precisa de atenção" list (`ResumoDaAtencao`), both
 * derived in `index` from `observability/atencao.ts` — so health doesn't
 * reimplement `top_failing` and still says "2 workflows falhando" instead of
 * something generic.
 *
 * The tone paints the strip (green/amber/red) and the verdict says why, joining
 * the 1–2 most serious reasons. The one that knows about color, icon and
 * envelope is `saude-hero.tsx`; only the decision lives here.
 */

export type TomDeSaude = "calmo" | "atencao" | "critico"

/**
 * Count per type of the "Precisa de atenção" items (`index` counts the list
 * `montarAtencao` already built). Feeds health's specific reasons without
 * rereading `top_failing`. Stuck runs do NOT go in here: they have their own
 * reason (with the "há X"), and counting them again would duplicate the verdict.
 */
export interface ResumoDaAtencao {
  /** Workflows with repeated failures in the list. */
  falhas: number
  /** Executors at their ceiling in the list. */
  saturado: number
}

/**
 * The health tone. Critical overrides attention; attention overrides calm.
 *
 * - critical: there is a stuck run OR the whole fleet is down (with executors).
 * - attention: part of the fleet offline, overdue acknowledgments (admin), OR
 *   there are items in the "Precisa de atenção" list (`temAtencao`, from `index`).
 * - calm: none of the above.
 */
export function tomDeSaude(now: INowBlock | null | undefined, temAtencao: boolean): TomDeSaude {
  const { online, total } = now?.executors ?? { online: 0, total: 0 }
  const presas = now?.stuck_count ?? 0
  if (presas > 0 || (total > 0 && online === 0)) return "critico"

  const acks = now?.overdue_acks ?? 0
  if ((total > 0 && online < total) || acks > 0 || temAtencao) return "atencao"

  return "calmo"
}

/**
 * Health reasons, from most to least serious, for the verdict to pick the
 * first 1–2. Exported for testing. Order of severity (spec §3.4): stuck run(s)
 * → whole fleet down → workflows failing → partial fleet → executors at
 * ceiling → overdue acknowledgments. The failure/ceiling counts come from
 * `resumo` (the list already built in `index`), so we say "2 workflows
 * falhando" instead of something generic, without rereading `top_failing`.
 */
export function motivosDeSaude(now: INowBlock | null | undefined, resumo: ResumoDaAtencao): string[] {
  const motivos: string[] = []

  // 1. Stuck runs: `now.stuck` already comes oldest to newest; the "há X" is the
  // oldest one's. Without the list (only the count) we show just the number.
  const presas = now?.stuck_count ?? 0
  if (presas > 0) {
    const maisAntiga = now?.stuck?.[0]
    const quanto = maisAntiga ? ` há ${formatarDuracao(maisAntiga.elapsed_seconds)}` : ""
    motivos.push(`${plural(presas, "execução presa", "execuções presas")}${quanto}`)
  }

  const { online, total } = now?.executors ?? { online: 0, total: 0 }
  if (total > 0 && online === 0) {
    // 2. Whole fleet down (critical).
    motivos.push(`frota offline: ${online} de ${total}`)
  }

  // 3. Workflows failing (repeatedly): the count comes from the attention list;
  // stuck runs are NOT counted again here — they already have their own reason above.
  if (resumo.falhas > 0) {
    motivos.push(plural(resumo.falhas, "workflow falhando", "workflows falhando"))
  }

  if (total > 0 && online > 0 && online < total) {
    // 4. Frota parcialmente offline.
    motivos.push(`frota parcialmente offline: ${online} de ${total}`)
  }

  // 5. Executors at their ceiling.
  if (resumo.saturado > 0) {
    motivos.push(plural(resumo.saturado, "executor no teto", "executores no teto"))
  }

  const acks = now?.overdue_acks ?? 0
  if (acks > 0) {
    // 6. Overdue acknowledgments (admin only).
    motivos.push(plural(acks, "confirmação atrasada", "confirmações atrasadas"))
  }

  return motivos
}

/**
 * One-sentence verdict. In calm, it reassures — "nada rodando ainda" when the
 * scope has workflows but no run (§3.10), otherwise "nada pedindo atenção
 * agora". In the others, "Precisa de você:" followed by the 1–2 most serious
 * reasons joined by "e".
 */
export function veredito(
  now: INowBlock | null | undefined,
  tom: TomDeSaude,
  resumo: ResumoDaAtencao,
  semExecucoes = false,
): string {
  if (tom === "calmo") {
    return semExecucoes ? "Tudo tranquilo — nada rodando ainda." : "Tudo tranquilo — nada pedindo atenção agora."
  }
  const motivos = motivosDeSaude(now, resumo).slice(0, 2)
  if (motivos.length === 0) return "Precisa de você."
  return `Precisa de você: ${motivos.join(" e ")}.`
}
