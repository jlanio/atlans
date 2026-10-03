/**
 * Transforms MapLibre requests for the Home globe. ONE thing, and nothing
 * else — returning `undefined` lets MapLibre go on with the raw request:
 *
 * The tiles of the assistant's layers come from `/terra/assistente/tiles/…`,
 * the same-origin proxy authenticated by session cookie: `credentials:
 * "same-origin"` is enough (the proxy injects the server's Bearer). Never
 * Authorization here — the browser does not have the server's token.
 *
 * The basemap (the tile server the installation configured) passes raw: there
 * is no key to attach. CARTO, which required `?key=` on its CDN, left the Home.
 */

const PREFIXO_TILES_AGENTE = "/terra/assistente/tiles/";

export interface RequisicaoTransformada {
  url: string;
  // Restricted to what MapLibre accepts (never "omit").
  credentials?: "same-origin" | "include";
}

/** MapLibre's `transformRequest`, ready to go into the constructor. */
export function transformarRequisicao(url: string): RequisicaoTransformada | undefined {
  // Assistant tiles (same-origin proxy): send the session cookie.
  if (ehTileDoAgente(url)) {
    return { url, credentials: "same-origin" };
  }
  return undefined;
}

/** `true` if the URL is an assistant tile through the `/terra` proxy. */
export function ehTileDoAgente(url: string): boolean {
  try {
    return new URL(url, base()).pathname.startsWith(PREFIXO_TILES_AGENTE);
  } catch {
    // Relative URL with no resolvable base (e.g. in a test): check the raw prefix.
    return url.startsWith(PREFIXO_TILES_AGENTE);
  }
}

function base(): string {
  return typeof window !== "undefined" && window.location?.origin
    ? window.location.origin
    : "http://localhost";
}
