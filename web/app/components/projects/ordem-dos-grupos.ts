/**
 * New group order when dropping a group on another.
 *
 * The dragged one takes the target's position, and the rest slide. Separated
 * from the screen for being the only piece with logic: removing from one index
 * and inserting at another has a pitfall — after the removal, the indexes ahead
 * of the original moved back one slot, and using the old index inserts in the
 * wrong place.
 *
 * Returns the SAME list when there is nothing to move, so the caller can
 * compare by identity before firing the save on the server.
 */
export function moverGrupo(
  ordem: string[],
  sourceId: string,
  targetId: string,
): string[] {
  if (sourceId === targetId) return ordem

  const de = ordem.indexOf(sourceId)
  const para = ordem.indexOf(targetId)
  // Id not in the list: the screen is working with a different set than the
  // one at hand. Moving blindly would save a made-up order.
  if (de < 0 || para < 0) return ordem

  const proximo = [...ordem]
  proximo.splice(para, 0, ...proximo.splice(de, 1))
  return proximo
}
