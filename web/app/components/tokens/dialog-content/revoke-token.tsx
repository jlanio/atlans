"use client"

import { GisFlowService } from "@/service/GisFlowService"
import type { ApiToken } from "@/service/types"
import { DeleteDialog } from "@/app/components/shared/DeleteDialog"
import { createToast } from "@/utils/createToast"

interface RevokeTokenProps {
  token: ApiToken
  /** Receives the token already marked as revoked — the list swaps the row in
   *  place, without an extra GET. */
  onRevoked: (token: ApiToken) => void
  onClose: () => void
}

/**
 * Revoking is final and immediate, but doesn't delete: the token stays in the list
 * as "Revogado", so the owner knows what existed. Hence the `DeleteDialog` with
 * the right verb — "Excluir" would describe the wrong action.
 */
const RevokeToken = ({ token, onRevoked, onClose }: RevokeTokenProps) => {
  async function handleConfirm() {
    const res = await GisFlowService.revokeApiToken(token.id)
    // Without this the item vanished from the list and reappeared on the next
    // refresh, with no message at all.
    if (res.error) {
      createToast.error("Não foi possível revogar o token", res.error.message)
      return
    }
    // The backend returns the revoked token; if the body comes back empty, we mark it here.
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
