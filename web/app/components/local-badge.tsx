// web/app/components/local-badge.tsx
//
// Marca de conteúdo que permanece no disco de um executor (LGPD).
//
// Compartilhado entre o Drive e os Artefatos porque é o MESMO estado, produzido
// pelas mesmas escolhas — "Manter apenas no executor" no nó de saída, ou a
// política da máquina no app desktop. As duas telas tinham marcas diferentes
// (âmbar com "Apenas no executor" ali, laranja com "Executor" aqui) e nada
// ligava uma à outra; pior, a tela de Artefatos decidia por heurística
// (`executor_id && !size_bytes`) e justamente os artefatos que a localidade
// produz — que TÊM tamanho — ficavam sem marca nenhuma.
//
// É só o ícone, sem texto: numa lista, uma pílula escrita compete com o nome do
// arquivo, que é o que a pessoa está procurando. A explicação inteira vai no
// `title` — quem precisa dela para no ícone, e quem já sabe o que a marca
// significa lê a lista sem ruído.
import { TbDeviceDesktop } from "react-icons/tb"

/** O conteúdo mora no disco de um executor, e não no armazenamento da plataforma. */
export function isLocalDoExecutor(item: { content_location?: string | null }): boolean {
  return item.content_location === "executor"
}

/** Os textos da marca. Padrão: o português do Drive e dos Artefatos; a Home traduzida passa os dela. */
export interface TextosDoLocal {
  /** O que o leitor de tela anuncia. */
  rotulo: string
  /** O `title`, com o executor (os 8 primeiros caracteres) quando conhecido. */
  titulo: (executorId: string | null | undefined) => string
}

export const TEXTOS_DO_LOCAL_PT: TextosDoLocal = {
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
}: { executorId?: string | null; textos?: TextosDoLocal }) {
  return (
    <span
      // `inline-flex` e não `inline`: alinha o ícone à linha de base do nome do
      // arquivo em vez de deixá-lo pendurado.
      className="inline-flex shrink-0 items-center text-amber-600 dark:text-amber-400"
      title={textos.titulo(executorId)}
      // O `title` é tooltip do mouse; o `aria-label` é o que o leitor de tela
      // anuncia, e sem ele a marca simplesmente não existe para quem não vê.
      aria-label={textos.rotulo}
      role="img"
    >
      <TbDeviceDesktop size={14} />
    </span>
  )
}
