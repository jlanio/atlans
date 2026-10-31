import { INodesPropertyAPI, IVisibleWhen } from "@/service/types"

type Valores = Record<string, unknown> | undefined

function regraVale(regra: IVisibleWhen | IVisibleWhen[], valores: Valores): boolean {
  const regras = Array.isArray(regra) ? regra : [regra]
  return regras.every(r => r.in.includes(valores?.[r.field] as string | number | boolean))
}

function regraConhecida(r: unknown): r is IVisibleWhen {
  return !!r && typeof (r as IVisibleWhen).field === "string" && Array.isArray((r as IVisibleWhen).in)
}

/** A rule or an AND list of rules — what each item of `any` may be. */
function itemConhecido(item: unknown): item is IVisibleWhen | IVisibleWhen[] {
  return Array.isArray(item) ? item.every(regraConhecida) : regraConhecida(item)
}

/**
 * Whether a field shows, by its declarative `visibleWhen`: a rule (`field`'s
 * current value is in `in`), a list of rules (AND) or `{ any: [...] }` (OR of
 * rules or lists).
 *
 * A shape it does not know shows the field — in `any` as anywhere else: a
 * schema newer than this editor would otherwise hide a field the node needs
 * (or break the form on `r.in`), with nothing on screen saying why.
 */
export function campoVisivel(visibleWhen: INodesPropertyAPI["visibleWhen"], valores: Valores): boolean {
  if (!visibleWhen) return true
  if (!Array.isArray(visibleWhen) && "any" in visibleWhen) {
    const alternativas = visibleWhen.any
    if (!Array.isArray(alternativas) || !alternativas.every(itemConhecido)) return true
    return alternativas.some(r => regraVale(r, valores))
  }
  const regras = Array.isArray(visibleWhen) ? visibleWhen : [visibleWhen]
  if (!regras.every(regraConhecida)) return true
  return regraVale(regras, valores)
}
