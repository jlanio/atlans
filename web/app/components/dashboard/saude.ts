import type { INowBlock } from "@/service/types"
import { formatarDuracao, plural } from "@/lib/formatos"

/**
 * Saúde do painel — o tom e o veredito de UMA frase do topo do Dashboard
 * (docs/specs/dashboard.md §3.4). Puro: recebe o instante (`now`) que as
 * métricas já trazem, um `temAtencao` (para o tom) e a contagem por tipo dos
 * itens da lista "Precisa de atenção" (`ResumoDaAtencao`), ambos derivados no
 * `index` de `observability/atencao.ts` — assim a saúde não reimplementa
 * `top_failing` e ainda diz "2 workflows falhando" em vez de um genérico.
 *
 * O tom pinta a faixa (verde/âmbar/vermelho) e o veredito diz por quê, juntando
 * os 1–2 motivos mais graves. Quem sabe de cor, ícone e envelope é o
 * `saude-hero.tsx`; aqui só mora a decisão.
 */

export type TomDeSaude = "calmo" | "atencao" | "critico"

/**
 * Contagem por tipo dos itens de "Precisa de atenção" (o `index` conta a lista
 * que `montarAtencao` já montou). Alimenta os motivos específicos da saúde sem
 * reler `top_failing`. As presas NÃO entram aqui: elas têm motivo próprio (com
 * o "há X"), e recontá-las duplicaria o veredito.
 */
export interface ResumoDaAtencao {
  /** Workflows com falhas repetidas na lista. */
  falhas: number
  /** Executores no teto na lista. */
  saturado: number
}

/**
 * O tom da saúde. Crítico manda sobre atenção; atenção sobre calmo.
 *
 * - crítico: há execução presa OU a frota inteira caiu (com executores).
 * - atenção: parte da frota offline, confirmações atrasadas (admin), OU há
 *   itens na lista "Precisa de atenção" (`temAtencao`, vindo do `index`).
 * - calmo: nada acima.
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
 * Motivos da saúde, do mais grave para o menos, para o veredito escolher os
 * 1–2 primeiros. Exportado para teste. Ordem de gravidade (spec §3.4): presa(s)
 * → frota inteira caída → workflows falhando → frota parcial → executores no
 * teto → confirmações atrasadas. As contagens de falhas/teto vêm do `resumo`
 * (a lista já montada no `index`), então dizemos "2 workflows falhando" em vez
 * de um genérico, sem reler `top_failing`.
 */
export function motivosDeSaude(now: INowBlock | null | undefined, resumo: ResumoDaAtencao): string[] {
  const motivos: string[] = []

  // 1. Presas: `now.stuck` já vem da mais antiga para a mais nova; o "há X" é o
  // dela. Sem a lista (só a contagem) mostramos apenas o número.
  const presas = now?.stuck_count ?? 0
  if (presas > 0) {
    const maisAntiga = now?.stuck?.[0]
    const quanto = maisAntiga ? ` há ${formatarDuracao(maisAntiga.elapsed_seconds)}` : ""
    motivos.push(`${plural(presas, "execução presa", "execuções presas")}${quanto}`)
  }

  const { online, total } = now?.executors ?? { online: 0, total: 0 }
  if (total > 0 && online === 0) {
    // 2. Frota inteira caiu (crítico).
    motivos.push(`frota offline: ${online} de ${total}`)
  }

  // 3. Workflows falhando (repetidas): a contagem vem da lista de atenção; as
  // presas NÃO são recontadas aqui — já têm motivo próprio acima.
  if (resumo.falhas > 0) {
    motivos.push(plural(resumo.falhas, "workflow falhando", "workflows falhando"))
  }

  if (total > 0 && online > 0 && online < total) {
    // 4. Frota parcialmente offline.
    motivos.push(`frota parcialmente offline: ${online} de ${total}`)
  }

  // 5. Executores no teto.
  if (resumo.saturado > 0) {
    motivos.push(plural(resumo.saturado, "executor no teto", "executores no teto"))
  }

  const acks = now?.overdue_acks ?? 0
  if (acks > 0) {
    // 6. Confirmações atrasadas (só admin).
    motivos.push(plural(acks, "confirmação atrasada", "confirmações atrasadas"))
  }

  return motivos
}

/**
 * Veredito de uma frase. No calmo, tranquiliza — "nada rodando ainda" quando o
 * escopo tem workflows mas nenhuma execução (§3.10), senão "nada pedindo
 * atenção agora". Nos demais, "Precisa de você:" seguido dos 1–2 motivos mais
 * graves juntados por "e".
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
