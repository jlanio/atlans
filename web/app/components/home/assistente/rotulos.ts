// web/app/components/home/assistente/rotulos.ts
//
// Nome de ferramenta no idioma da tela, para a linha do tempo do painel. A
// tabela mora no dicionário da Home (`i18n/secoes/assistente.ts`, `ferramentas`).
//
// `search_nodes` e `get_authoring_guide` são nomes de API; quem está montando
// um fluxo não tem por que aprendê-los para entender que o assistente está
// procurando um nó. O padrão da casa é o mesmo de `status-rotulos.ts`: o valor
// cru nunca vai para a tela.
//
// A tabela cobre as ferramentas todas, e não só as que o assistente alcança, porque
// o quadro `ferramenta` é emitido ANTES do despacho: um nome que o portão
// recusa ainda aparece aqui uma vez, seguido do passo em erro.

import { IDIOMA_PADRAO, type Idioma } from "@/lib/idioma"
import { textosDe } from "../i18n"

export function rotuloDaFerramenta(nome: string, idioma: Idioma = IDIOMA_PADRAO): string {
  const tabela = textosDe(idioma).assistente.ferramentas
  return Object.hasOwn(tabela, nome) ? tabela[nome] : nome
}

/**
 * Um detalhe curto da chamada, tirado do resumo dos argumentos.
 *
 * O resumo do servidor já colapsa o que é grande (`definition` vira
 * `{__campos__: 2}`), então aqui só há texto curto — e mesmo assim a escolha é
 * por chave conhecida, não "o primeiro valor que couber": um argumento novo não
 * pode passar a despejar conteúdo na tela por acidente.
 */
const DETALHE = ["query", "topic", "name", "search", "node_name", "workflow_id", "run_id", "file_id"]

export function detalheDaChamada(argumentos: Record<string, unknown>): string | null {
  for (const chave of DETALHE) {
    const valor = argumentos[chave]
    if (typeof valor === "string" && valor.trim()) return valor.length > 48 ? `${valor.slice(0, 45)}…` : valor
  }
  return null
}
