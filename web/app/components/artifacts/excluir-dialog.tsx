"use client"

import { Dialog } from "@/app/components/ui/dialog"
import { DeleteDialog } from "@/app/components/shared/DeleteDialog"
import { formatarInteiro, plural } from "@/lib/formatos"

/**
 * Confirmation of the batch deletion of artifacts. Wraps `shared/DeleteDialog`
 * (which carries the double-click lock and the block on closing mid-operation)
 * instead of the hand-reimplemented dialog the screen had — which, on top of
 * that, had its microcopy without accents.
 *
 * `nomeUnico` is the file name when there is a single target: shown in angle
 * quotes, in the tone of the other screens. In a batch the names are not
 * listed — the number is what matters.
 */
export function ExcluirArtefatosDialog({
  aberto, quantidade, nomeUnico, onConfirmar, onFechar,
}: {
  aberto: boolean
  quantidade: number
  nomeUnico: string | null
  onConfirmar: () => void | Promise<void>
  onFechar: () => void
}) {
  const umSo = quantidade === 1
  const titulo = umSo ? "Excluir artefato" : `Excluir ${plural(quantidade, "artefato")}`
  const descricao = umSo
    ? `O artefato${nomeUnico ? ` «${nomeUnico}»` : ""} será removido permanentemente e não poderá ser recuperado.`
    : `${formatarInteiro(quantidade)} artefatos serão removidos permanentemente e não poderão ser recuperados.`

  return (
    <Dialog open={aberto} onOpenChange={v => { if (!v) onFechar() }}>
      <DeleteDialog
        title={titulo}
        description={descricao}
        confirmLabel={umSo ? "Excluir" : `Excluir ${plural(quantidade, "artefato")}`}
        loadingLabel="Excluindo…"
        onConfirm={onConfirmar}
      />
    </Dialog>
  )
}
