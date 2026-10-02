/**
 * Cor de execução da aresta — mapeamento puro, testável.
 *
 * Existe como módulo próprio por dois motivos. O primeiro é dar superfície de
 * teste ao mapeamento: as ausências abaixo são deliberadas e não se explicam
 * sozinhas quando lidas no meio do componente. O segundo é acabar com os hex
 * crus que viviam no `custom-edges` — eram idênticos nos dois temas, enquanto o
 * card do mesmo nó já trocava de tom com o tema.
 */

/** Tom de execução — o mesmo vocabulário do card (globals.css, `.exec-card`). */
export type ExecTone = "idle" | "running" | "success" | "error" | "unknown"

const TOM_POR_STATUS: Record<string, ExecTone> = {
  started: "running",
  completed: "success",
  failed: "error",
  // `unknown` faltava: o card ficava âmbar e a aresta que saía dele caía no
  // cinza, dizendo duas coisas diferentes sobre o mesmo nó.
  unknown: "unknown",
  // `idle` está ausente DE PROPÓSITO — cai na cor do handle, para uma aresta
  // `true` continuar verde antes de qualquer execução.
  //
  // `cancelled` não entra: é status de WORKFLOW, nunca de nó. O cancelamento
  // devolve os nós a `idle` (ver `completeExecution` no workflowExecutionStore).
}

const TOM_POR_HANDLE: Record<string, ExecTone> = {
  true: "success",
  false: "error",
}

/** Busca no mapa SÓ o que ele mesmo declara.
 *
 *  Nome de porta é dado do usuário: `output_vars` é texto livre e as portas
 *  dinâmicas aceitam qualquer identificador. Com colchete cru, uma porta
 *  chamada `constructor` devolvia a função `Object` em vez de `undefined`, e a
 *  cor virava `var(--exec-function Object() { [native code] })` — `var()`
 *  inválido, propriedade descartada, porta invisível no canvas. */
function buscarTom(mapa: Record<string, ExecTone>, chave: string): ExecTone | undefined {
  // `hasOwnProperty.call` e nao `Object.hasOwn`: este e o unico modulo de cor no
  // caminho de render de TODA aresta, e `Object.hasOwn` e ES2022 — o projeto nao
  // declara browserslist e o bundle de polyfill do Next nao o cobre. Custa o
  // mesmo e nao tem piso de versao.
  return Object.prototype.hasOwnProperty.call(mapa, chave) ? mapa[chave] : undefined
}

/** Tom que o ID do handle sugere, sozinho — `undefined` quando o handle não é
 *  de roteamento.
 *
 *  Exposto para a PORTA do nó pintar-se com a mesma regra da aresta. Sem isto o
 *  handle teria de repetir o mapa `true → verde`, e as duas pontas da mesma
 *  ligação passariam a poder divergir sem ninguém notar. */
export function tomDoHandle(handle: string | null | undefined): ExecTone | undefined {
  return handle ? buscarTom(TOM_POR_HANDLE, handle) : undefined
}

/** Tom da aresta a partir do status da origem e do handle de saída. */
export function tomDaAresta(
  status: string | undefined,
  handle: string,
  perdedora: boolean,
): ExecTone {
  if (perdedora) return "idle"
  return (status ? buscarTom(TOM_POR_STATUS, status) : undefined)
    ?? buscarTom(TOM_POR_HANDLE, handle)
    ?? "idle"
}

/** Token CSS do tom — resolvido em `:root`/`.dark`, portanto sensível ao tema. */
export const corDoTom = (tom: ExecTone) => `var(--exec-${tom})`
