"use client"

import { GisFlowService } from "@/service/GisFlowService"
import type { ApiToken } from "@/service/types"
import { DeleteDialog } from "@/app/components/shared/DeleteDialog"
import { createToast } from "@/utils/createToast"

interface RevokeTokenProps {
  token: ApiToken
  /** Recebe o token já marcado como revogado — a lista troca a linha no lugar,
   *  sem um GET a mais. */
  onRevoked: (token: ApiToken) => void
  onClose: () => void
}

/**
 * Revogar é definitivo e imediato, mas não apaga: o token continua na lista
 * como «Revogado», para o dono saber o que existiu. Daí o `DeleteDialog` com o
 * verbo certo — «Excluir» descreveria a ação errada.
 */
const RevokeToken = ({ token, onRevoked, onClose }: RevokeTokenProps) => {
  async function handleConfirm() {
    const res = await GisFlowService.revokeApiToken(token.id)
    // Sem isto o item sumia da lista e reaparecia no próximo refresh, sem
    // mensagem nenhuma.
    if (res.error) {
      createToast.error("Não foi possível revogar o token", res.error.message)
      return
    }
    // O backend devolve o token revogado; se o corpo vier vazio, marcamos aqui.
    onRevoked(res.data ?? { ...token, status: "revoked", revoked_at: new Date().toISOString() })
    createToast.success("Token revogado", token.name)
    onClose()
  }

  return (
    <DeleteDialog
      title={`Revogar o token «${token.name}»`}
      description={`Agentes que usam «${token.name}» param de funcionar na hora.`}
      note="A revogação não pode ser desfeita. Se precisar, crie outro token."
      confirmLabel="Revogar"
      loadingLabel="Revogando…"
      onConfirm={handleConfirm}
    />
  )
}

export default RevokeToken
