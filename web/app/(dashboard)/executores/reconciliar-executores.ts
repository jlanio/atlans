import type { IExecutor } from "@/service/types"

/**
 * Reconciles the poll response against the previous list, preserving the
 * IDENTITY of the objects that did not change.
 *
 * The 15s auto-refresh re-parses the JSON and returns new objects even for
 * executors identical to the previous cycle. Since ExecutorCard's `React.memo`
 * compares props shallowly, it missed on 100% of ticks: the whole list
 * re-rendered and the memo saved nothing — it only served as a justification
 * for removing the list's reload visual feedback.
 *
 * Returns the previous array itself when NOTHING changed (neither content, nor
 * order, nor size), so the derived `useMemo`s also stop recomputing.
 */

// JSON signature memoized by object identity. An executor preserved across
// ticks keeps the same reference, so its signature is serialized only once
// (and not twice — old + new — every 15s cycle as before). The comparison is
// still over the whole JSON: no displayed field slips through.
const signatureCache = new WeakMap<IExecutor, string>()
function assinatura(e: IExecutor): string {
  let s = signatureCache.get(e)
  if (s === undefined) {
    // Safe: the objects come from JSON.parse of the same response, stable key order.
    s = JSON.stringify(e)
    signatureCache.set(e, s)
  }
  return s
}

export function reconciliarExecutores(
  anteriores: IExecutor[],
  recebidos: IExecutor[],
): IExecutor[] {
  const byId = new Map(anteriores.map(e => [e.id_hash, e]))
  let mudou = recebidos.length !== anteriores.length

  const reconciled = recebidos.map((novo, i) => {
    const velho = byId.get(novo.id_hash)
    if (velho && assinatura(velho) === assinatura(novo)) {
      if (anteriores[i] !== velho) mudou = true  // mesmo conjunto, ordem diferente
      return velho
    }
    mudou = true
    return novo
  })

  return mudou ? reconciled : anteriores
}
