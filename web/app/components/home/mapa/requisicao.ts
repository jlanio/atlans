/**
 * Transforma requisições do MapLibre para o globo da Home. UMA coisa, e nada
 * além — retornar `undefined` deixa o MapLibre seguir com a requisição crua:
 *
 * Os tiles das camadas do assistente vêm de `/terra/assistente/tiles/…`, o proxy
 * same-origin autenticado por cookie de sessão: basta `credentials:
 * "same-origin"` (o proxy injeta o Bearer do servidor). Nunca Authorization
 * aqui — o navegador não tem o token do servidor.
 *
 * O basemap (o servidor de tiles que a instalação configurou) passa cru: não
 * há chave a anexar. A CARTO, que exigia `?key=` no CDN dela, saiu da Home.
 */

const PREFIXO_TILES_AGENTE = "/terra/assistente/tiles/";

export interface RequisicaoTransformada {
  url: string;
  // Restrito ao que o MapLibre aceita (nunca "omit").
  credentials?: "same-origin" | "include";
}

/** O `transformRequest` do MapLibre, pronto para ir ao construtor. */
export function transformarRequisicao(url: string): RequisicaoTransformada | undefined {
  // Tiles do assistente (proxy same-origin): manda o cookie de sessão.
  if (ehTileDoAgente(url)) {
    return { url, credentials: "same-origin" };
  }
  return undefined;
}

/** `true` se a URL é um tile do assistente pelo proxy `/terra`. */
export function ehTileDoAgente(url: string): boolean {
  try {
    return new URL(url, base()).pathname.startsWith(PREFIXO_TILES_AGENTE);
  } catch {
    // URL relativa sem base resolvível (ex.: em teste): checa o prefixo cru.
    return url.startsWith(PREFIXO_TILES_AGENTE);
  }
}

function base(): string {
  return typeof window !== "undefined" && window.location?.origin
    ? window.location.origin
    : "http://localhost";
}
