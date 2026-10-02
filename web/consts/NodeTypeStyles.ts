// Mapa de estilos visuais por tipo de nó — fonte única de verdade.
// Usado pelo IconRoot (cards no canvas) e NodeConfigModal (header do modal).

export const TYPE_STYLES: Record<string, { stripe: string; bg: string; icon: string; label: string }> = {
  trigger:    { stripe: "bg-violet-500",  bg: "bg-violet-500/10",  icon: "text-violet-500",  label: "text-violet-400"  },
  action:     { stripe: "bg-sky-500",     bg: "bg-sky-500/10",     icon: "text-sky-500",     label: "text-sky-400"     },
  spatial:    { stripe: "bg-emerald-500", bg: "bg-emerald-500/10", icon: "text-emerald-400", label: "text-emerald-400" },
  datasource: { stripe: "bg-amber-500",   bg: "bg-amber-500/10",   icon: "text-amber-500",   label: "text-amber-400"   },
  output:     { stripe: "bg-rose-500",    bg: "bg-rose-500/10",    icon: "text-rose-400",    label: "text-rose-400"    },
  control:    { stripe: "bg-orange-400",  bg: "bg-orange-400/10",  icon: "text-orange-400",  label: "text-orange-300"  },
}

/** Nome e descrição de cada tipo, em português.
 *
 *  Estavam escritos três vezes — no cabeçalho do drawer, na lista de nós e nos
 *  cartões de categoria — e já divergiam: "Fontes de dados" num lugar, "Fontes"
 *  no outro. Ficam aqui junto das cores porque respondem à mesma pergunta ("o
 *  que este tipo é"), e porque foi a separação delas que deixou as três cópias
 *  se afastarem sem ninguém notar. */
export const TYPE_INFO: Record<string, { nome: string; descricao: string }> = {
  trigger:    { nome: "Triggers",         descricao: "Inicia o workflow" },
  action:     { nome: "Ações",            descricao: "Transformações e operações" },
  spatial:    { nome: "Espacial",         descricao: "Operações geoespaciais" },
  datasource: { nome: "Fontes de dados",  descricao: "Arquivos e banco de dados" },
  output:     { nome: "Saídas",           descricao: "Exporta e envia resultados" },
  control:    { nome: "Controle",         descricao: "Lógica e fluxo condicional" },
}

/** Nome de exibição do tipo, com recuo para o próprio identificador. */
export const nomeDoTipo = (tipo: string): string =>
  (Object.prototype.hasOwnProperty.call(TYPE_INFO, tipo) ? TYPE_INFO[tipo]?.nome : undefined)
  ?? tipo.charAt(0).toUpperCase() + tipo.slice(1)

export const DEFAULT_STYLE = {
  stripe: "bg-muted-foreground",
  bg: "bg-muted",
  icon: "text-muted-foreground",
  label: "text-muted-foreground",
}

/** Descrição do tipo, vazia para o que o mapa não conhece. */
export const descricaoDoTipo = (tipo: string): string =>
  (Object.prototype.hasOwnProperty.call(TYPE_INFO, tipo) ? TYPE_INFO[tipo]?.descricao : undefined) ?? ""

/** Estilo do tipo, com recuo para o neutro.
 *
 *  `TYPE_STYLES[t] ?? DEFAULT_STYLE` lia pela cadeia de protótipo: um tipo vindo
 *  da API chamado `constructor` devolvia a função `Object`, que é truthy — o
 *  `??` não disparava e `estilo.bg` saía `undefined`. */
export const estiloDoTipo = (tipo: string) =>
  Object.prototype.hasOwnProperty.call(TYPE_STYLES, tipo) ? TYPE_STYLES[tipo] : DEFAULT_STYLE
