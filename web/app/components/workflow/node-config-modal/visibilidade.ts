import { INodesPropertyAPI, IVisibleWhen } from "@/service/types"

type Valores = Record<string, unknown> | undefined

function regraVale(regra: IVisibleWhen | IVisibleWhen[], valores: Valores): boolean {
  const regras = Array.isArray(regra) ? regra : [regra]
  return regras.every(r => r.in.includes(valores?.[r.field] as string | number | boolean))
}

/**
 * Whether a field shows, by its declarative `visibleWhen`: a rule (`field`'s
 * current value is in `in`), a list of rules (AND) or `{ any: [...] }` (OR of
 * rules or lists).
 *
 * A shape it does not know shows the field: a schema newer than this editor
 * would otherwise hide a field the node needs, with nothing on screen saying why.
 */
export function campoVisivel(visibleWhen: INodesPropertyAPI["visibleWhen"], valores: Valores): boolean {
  if (!visibleWhen) return true
  if (!Array.isArray(visibleWhen) && "any" in visibleWhen) {
    return Array.isArray(visibleWhen.any) && visibleWhen.any.some(r => regraVale(r, valores))
  }
  const regras = Array.isArray(visibleWhen) ? visibleWhen : [visibleWhen]
  if (!regras.every(r => r && typeof r.field === "string" && Array.isArray(r.in))) return true
  return regraVale(regras, valores)
}
