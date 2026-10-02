/**
 * Nova ordem dos grupos ao soltar um grupo sobre outro.
 *
 * O arrastado assume a posição do alvo, e o resto desliza. Separado da tela por
 * ser o único pedaço com lógica: tirar de um índice e inserir em outro tem uma
 * armadilha — depois da remoção, os índices à frente do original andaram uma
 * casa para trás, e usar o índice antigo insere no lugar errado.
 *
 * Devolve a MESMA lista quando não há o que mover, para que quem chama possa
 * comparar por identidade antes de disparar a gravação no servidor.
 */
export function moverGrupo(
  ordem: string[],
  origemId: string,
  alvoId: string,
): string[] {
  if (origemId === alvoId) return ordem

  const de = ordem.indexOf(origemId)
  const para = ordem.indexOf(alvoId)
  // Id fora da lista: a tela está trabalhando com um conjunto diferente do que
  // tem em mãos. Mover às cegas gravaria uma ordem inventada.
  if (de < 0 || para < 0) return ordem

  const proximo = [...ordem]
  proximo.splice(para, 0, ...proximo.splice(de, 1))
  return proximo
}
