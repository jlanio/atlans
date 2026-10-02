"use client"

import { Dialog } from "@/app/components/ui/dialog"
import { DeleteDialog } from "@/app/components/shared/DeleteDialog"
import { formatarInteiro, plural } from "@/lib/formatos"

/**
 * Confirmação da exclusão em lote de artefatos. Envolve o `shared/DeleteDialog`
 * (que carrega a trava contra duplo clique e o bloqueio de fechar no meio da
 * operação) no lugar do diálogo reimplementado à mão que a tela tinha — e que,
 * de quebra, trazia a microcopy sem acento.
 *
 * `nomeUnico` é o nome do arquivo quando há um só alvo: mostrado entre aspas
 * angulares, no tom das demais telas. Em lote não se listam os nomes — o número
 * é o que importa.
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
