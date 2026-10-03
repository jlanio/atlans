// Map of visual styles per node type — single source of truth.
// Used by IconRoot (cards on the canvas) and NodeConfigModal (modal header).

export const TYPE_STYLES: Record<string, { stripe: string; bg: string; icon: string; label: string }> = {
  trigger:    { stripe: "bg-violet-500",  bg: "bg-violet-500/10",  icon: "text-violet-500",  label: "text-violet-400"  },
  action:     { stripe: "bg-sky-500",     bg: "bg-sky-500/10",     icon: "text-sky-500",     label: "text-sky-400"     },
  spatial:    { stripe: "bg-emerald-500", bg: "bg-emerald-500/10", icon: "text-emerald-400", label: "text-emerald-400" },
  datasource: { stripe: "bg-amber-500",   bg: "bg-amber-500/10",   icon: "text-amber-500",   label: "text-amber-400"   },
  output:     { stripe: "bg-rose-500",    bg: "bg-rose-500/10",    icon: "text-rose-400",    label: "text-rose-400"    },
  control:    { stripe: "bg-orange-400",  bg: "bg-orange-400/10",  icon: "text-orange-400",  label: "text-orange-300"  },
}

/** Name and description of each type, in Portuguese.
 *
 *  They were written three times — in the drawer header, in the node list and
 *  in the category cards — and already diverged: "Fontes de dados" in one
 *  place, "Fontes" in another. They live here next to the colors because they
 *  answer the same question ("what this type is"), and because separating them
 *  is what let the three copies drift apart without anyone noticing. */
export const TYPE_INFO: Record<string, { nome: string; descricao: string }> = {
  trigger:    { nome: "Triggers",         descricao: "Inicia o workflow" },
  action:     { nome: "Ações",            descricao: "Transformações e operações" },
  spatial:    { nome: "Espacial",         descricao: "Operações geoespaciais" },
  datasource: { nome: "Fontes de dados",  descricao: "Arquivos e banco de dados" },
  output:     { nome: "Saídas",           descricao: "Exporta e envia resultados" },
  control:    { nome: "Controle",         descricao: "Lógica e fluxo condicional" },
}

/** Display name of the type, falling back to the identifier itself. */
export const nomeDoTipo = (tipo: string): string =>
  (Object.prototype.hasOwnProperty.call(TYPE_INFO, tipo) ? TYPE_INFO[tipo]?.nome : undefined)
  ?? tipo.charAt(0).toUpperCase() + tipo.slice(1)

export const DEFAULT_STYLE = {
  stripe: "bg-muted-foreground",
  bg: "bg-muted",
  icon: "text-muted-foreground",
  label: "text-muted-foreground",
}

/** Description of the type, empty for what the map does not know. */
export const descricaoDoTipo = (tipo: string): string =>
  (Object.prototype.hasOwnProperty.call(TYPE_INFO, tipo) ? TYPE_INFO[tipo]?.descricao : undefined) ?? ""

/** The type's style, falling back to neutral.
 *
 *  `TYPE_STYLES[t] ?? DEFAULT_STYLE` read through the prototype chain: a type
 *  coming from the API named `constructor` returned the `Object` function, which
 *  is truthy — the `??` did not fire and `estilo.bg` came out `undefined`. */
export const estiloDoTipo = (tipo: string) =>
  Object.prototype.hasOwnProperty.call(TYPE_STYLES, tipo) ? TYPE_STYLES[tipo] : DEFAULT_STYLE
