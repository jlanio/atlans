// web/lib/fundos-do-mapa.ts
//
// Os fundos (basemaps) do mapa: ruas, satélite e satélite com rótulos.
//
// O código não traz servidor de tiles nenhum além do OpenStreetMap (as ruas):
// imagem de satélite exige um provedor e os termos dele, e cada instalação
// escolhe o seu. As URLs vêm do ambiente do servidor web — as MESMAS variáveis
// que a API usa para os nós Carta (`app/core/config.py`, MAPA_*) — lidas pelo
// layout raiz a cada pedido e passadas ao cliente por contexto
// (`app/components/share/fundos-do-mapa.tsx`). NEXT_PUBLIC_* não serviria: o
// valor seria gravado no build, e a imagem é a mesma para toda instalação.
//
// Sem satélite configurado, o portal não oferece o alternador, e a Home (que
// nasce no híbrido) cai no satélite e, sem ele, nas ruas.

/** Os três fundos que o mapa conhece. */
export type Basemap = "streets" | "satellite" | "hybrid"

export interface FundoDoMapa {
  /** Template com {z}, {x} e {y}. */
  url: string
  /** A atribuição exigida pelo provedor, em texto puro. */
  credito: string
}

export interface FundosDoMapa {
  ruas: FundoDoMapa
  satelite?: FundoDoMapa
  hibrido?: FundoDoMapa
}

export const RUAS_PADRAO: FundoDoMapa = {
  url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
  credito: "© OpenStreetMap contributors",
}

export const FUNDOS_PADRAO: FundosDoMapa = { ruas: RUAS_PADRAO }

function lerFundo(env: Record<string, string | undefined>, prefixo: string): FundoDoMapa | undefined {
  const url = (env[`MAPA_${prefixo}_URL`] ?? "").trim()
  if (!url) return undefined
  if (!/^https?:\/\//.test(url) || !["{z}", "{x}", "{y}"].every(m => url.includes(m))) {
    console.error(`MAPA_${prefixo}_URL não é um template de tiles (https://…/{z}/{x}/{y}…) — ignorada.`)
    return undefined
  }
  return { url, credito: (env[`MAPA_${prefixo}_CREDITO`] ?? "").trim() }
}

/** Os fundos desta instalação, a partir do ambiente do servidor (MAPA_*). */
export function lerFundosDoAmbiente(env: Record<string, string | undefined>): FundosDoMapa {
  const fundos: FundosDoMapa = { ruas: lerFundo(env, "RUAS") ?? RUAS_PADRAO }
  const satelite = lerFundo(env, "SATELITE")
  const hibrido = lerFundo(env, "HIBRIDO")
  if (satelite) fundos.satelite = satelite
  if (hibrido) fundos.hibrido = hibrido
  return fundos
}

/** O crédito vai como HTML no controle de atribuição do MapLibre: escapado. */
function escapar(texto: string): string {
  return texto.replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!)
}

/**
 * O fundo que o mapa usa para um basemap pedido: o híbrido cai no satélite, e o
 * satélite nas ruas, quando a instalação não os configurou.
 */
export function conjuntoDoFundo(fundos: FundosDoMapa, basemap: Basemap): { tiles: string[]; attribution: string } {
  const fundo =
    basemap === "hybrid" ? fundos.hibrido ?? fundos.satelite ?? fundos.ruas
    : basemap === "satellite" ? fundos.satelite ?? fundos.ruas
    : fundos.ruas
  return { tiles: [fundo.url], attribution: escapar(fundo.credito) }
}
