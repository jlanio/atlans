// web/app/components/local-badge.tsx
//
// Badge for content that stays on an executor's disk (LGPD).
//
// Shared between Drive and Artifacts because it is the SAME state, produced by
// the same choices — "Manter apenas no executor" (keep only on the executor) on
// the output node, or the machine policy in the desktop app. The two screens
// had different badges (amber with "Apenas no executor" there, orange with
// "Executor" here) and nothing tied one to the other; worse, the Artifacts
// screen decided by heuristic (`executor_id && !size_bytes`) and precisely the
// artifacts that locality produces — which DO have a size — got no badge at all.
//
// It is just the icon, no text: in a list, a written pill competes with the
// file name, which is what the person is looking for. The full explanation goes
// in the `title` — whoever needs it stops on the icon, and whoever already knows
// what the badge means reads the list without noise.
import { TbDeviceDesktop } from "react-icons/tb"

/** The content lives on an executor's disk, not in the platform's storage. */
export function isLocalDoExecutor(item: { content_location?: string | null }): boolean {
  return item.content_location === "executor"
}

/** The badge texts. Default: the Portuguese of Drive and Artifacts; the translated Home passes its own. */
export interface LocalTexts {
  /** What the screen reader announces. */
  rotulo: string
  /** The `title`, with the executor (its first 8 characters) when known. */
  titulo: (executorId: string | null | undefined) => string
}

export const TEXTOS_DO_LOCAL_PT: LocalTexts = {
  rotulo: "Conteúdo apenas no executor",
  titulo: (executorId) => {
    const onde = executorId ? `executor ${executorId.slice(0, 8)}…` : "executor de origem"
    return (
      `O conteúdo permanece no ${onde} e nunca foi enviado para a nuvem. ` +
      "Não pode ser baixado pela plataforma, mas continua disponível para " +
      "workflows que rodem nesse executor."
    )
  },
}

export function LocalBadge({
  executorId, textos = TEXTOS_DO_LOCAL_PT,
}: { executorId?: string | null; textos?: LocalTexts }) {
  return (
    <span
      // `inline-flex`, not `inline`: aligns the icon to the file name's baseline
      // instead of leaving it hanging.
      className="inline-flex shrink-0 items-center text-amber-600 dark:text-amber-400"
      title={textos.titulo(executorId)}
      // The `title` is a mouse tooltip; the `aria-label` is what the screen reader
      // announces, and without it the badge simply does not exist for those who cannot see.
      aria-label={textos.rotulo}
      role="img"
    >
      <TbDeviceDesktop size={14} />
    </span>
  )
}
