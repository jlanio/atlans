import type { IExecutor } from "@/service/types"

/**
 * Reconcilia a resposta do poll contra a lista anterior, preservando a
 * IDENTIDADE dos objetos que não mudaram.
 *
 * O auto-refresh de 15s reparseia o JSON e devolve objetos novos mesmo para
 * executores idênticos ao ciclo anterior. Como o `React.memo` do ExecutorCard
 * compara props de forma rasa, ele errava em 100% dos ticks: a lista inteira
 * re-renderizava e o memo não economizava nada — só serviu de justificativa
 * para tirar o feedback visual de recarga da lista.
 *
 * Devolve o próprio array anterior quando NADA mudou (nem conteúdo, nem ordem,
 * nem tamanho), para que os `useMemo` derivados também parem de recalcular.
 */

// Assinatura JSON memoizada por identidade de objeto. Um executor preservado
// entre ticks mantém a mesma referência, então sua assinatura é serializada uma
// única vez (e não duas — velho + novo — a cada ciclo de 15s como antes). A
// comparação continua sendo a do JSON inteiro: nenhum campo exibido escapa.
const assinaturaCache = new WeakMap<IExecutor, string>()
function assinatura(e: IExecutor): string {
  let s = assinaturaCache.get(e)
  if (s === undefined) {
    // Seguro: os objetos vêm de JSON.parse da mesma resposta, ordem de chaves estável.
    s = JSON.stringify(e)
    assinaturaCache.set(e, s)
  }
  return s
}

export function reconciliarExecutores(
  anteriores: IExecutor[],
  recebidos: IExecutor[],
): IExecutor[] {
  const porId = new Map(anteriores.map(e => [e.id_hash, e]))
  let mudou = recebidos.length !== anteriores.length

  const reconciliados = recebidos.map((novo, i) => {
    const velho = porId.get(novo.id_hash)
    if (velho && assinatura(velho) === assinatura(novo)) {
      if (anteriores[i] !== velho) mudou = true  // mesmo conjunto, ordem diferente
      return velho
    }
    mudou = true
    return novo
  })

  return mudou ? reconciliados : anteriores
}
