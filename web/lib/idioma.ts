// web/lib/idioma.ts
//
// Os idiomas da Home e a regra que escolhe um deles por requisição. Puro de
// propósito: roda no servidor (o layout do dashboard resolve antes do primeiro
// byte, sem a página nascer em português e trocar depois) e nos testes.
//
// A ordem da decisão, do sinal mais forte ao mais fraco:
//   1. a escolha explícita da pessoa (Preferências → cookie `idioma`);
//   2. o idioma do navegador (`Accept-Language`) — o sinal mais fiel do que a
//      pessoa LÊ: uma brasileira com o navegador em inglês escolheu inglês, e
//      um turista americano no Brasil não quer a tela em português;
//   3. o país da conexão (`CF-IPCountry`, quando a Cloudflare o manda) — mas
//      SÓ quando o navegador mandou um `Accept-Language` que não atendemos;
//   4. o padrão: português se o pedido não trouxe `Accept-Language`; inglês se
//      trouxe, mas sem nenhum dos nossos idiomas (quem lê francês lê melhor
//      inglês que português).
//
// Sem `Accept-Language` o pedido não veio de um navegador — todo navegador o
// manda. Vem de robô de busca ou de script, e o país da conexão diria só onde
// fica o servidor dele: o Googlebot sai dos EUA e indexaria a Home em inglês.

export const IDIOMAS = ["pt-BR", "en", "es"] as const
export type Idioma = (typeof IDIOMAS)[number]

export const IDIOMA_PADRAO: Idioma = "pt-BR"

/** O cookie da escolha explícita — mesmo modelo do `theme` (ThemeContext). */
export const COOKIE_DO_IDIOMA = "idioma"

/** O nome de cada idioma nele mesmo: é assim que a pessoa o reconhece numa lista. */
export const NOME_DO_IDIOMA: Record<Idioma, string> = {
  "pt-BR": "Português (Brasil)",
  en: "English",
  es: "Español",
}

export function ehIdioma(valor: unknown): valor is Idioma {
  return typeof valor === "string" && (IDIOMAS as readonly string[]).includes(valor)
}

function _idiomaDaEtiqueta(etiqueta: string): Idioma | null {
  const base = etiqueta.trim().toLowerCase().split(/[-_]/)[0]
  if (base === "pt") return "pt-BR"
  if (base === "en") return "en"
  if (base === "es") return "es"
  return null
}

/**
 * O primeiro dos nossos idiomas na preferência do navegador, respeitando os
 * pesos `q` (`q=0` é recusa explícita). `"fr-FR,fr;q=0.9,en;q=0.8"` → `"en"`.
 */
export function idiomaDoAcceptLanguage(cabecalho: string | null | undefined): Idioma | null {
  if (!cabecalho) return null
  const itens = cabecalho
    .split(",")
    .map((parte, ordem) => {
      const [etiqueta, ...params] = parte.trim().split(";")
      const q = params
        .map((p) => p.trim())
        .find((p) => p.startsWith("q="))
      const peso = q ? Number(q.slice(2)) : 1
      return { etiqueta: etiqueta.trim(), peso: Number.isFinite(peso) ? peso : 0, ordem }
    })
    .filter((item) => item.etiqueta && item.peso > 0)
    // Peso maior primeiro; no empate vale a ordem do cabeçalho.
    .sort((a, b) => b.peso - a.peso || a.ordem - b.ordem)
  for (const { etiqueta } of itens) {
    const idioma = _idiomaDaEtiqueta(etiqueta)
    if (idioma) return idioma
  }
  return null
}

const PAISES_LUSOFONOS = new Set(["BR", "PT", "AO", "MZ", "CV", "GW", "ST", "TL"])
const PAISES_HISPANOFONOS = new Set([
  "ES", "MX", "GT", "HN", "SV", "NI", "CR", "PA", "CU", "DO", "PR",
  "CO", "VE", "EC", "PE", "BO", "CL", "AR", "PY", "UY", "GQ",
])

/**
 * O idioma pelo país da conexão (ISO 3166-1 alfa-2). `XX` (desconhecido) e
 * `T1` (Tor) são códigos da Cloudflare que não dizem nada — viram `null`.
 */
export function idiomaDoPais(pais: string | null | undefined): Idioma | null {
  const codigo = (pais ?? "").trim().toUpperCase()
  if (!/^[A-Z]{2}$/.test(codigo) || codigo === "XX" || codigo === "T1") return null
  if (PAISES_LUSOFONOS.has(codigo)) return "pt-BR"
  if (PAISES_HISPANOFONOS.has(codigo)) return "es"
  return "en"
}

export interface IdiomaResolvido {
  /** O que a tela usa: a escolha, ou o detectado quando não há escolha. */
  idioma: Idioma
  /** O que a detecção automática daria — as Preferências o mostram em "Automático". */
  detectado: Idioma
  /** A escolha explícita (cookie), ou `null` quando está no automático. */
  escolhido: Idioma | null
}

export function resolverIdioma(sinais: {
  cookie?: string | null
  acceptLanguage?: string | null
  pais?: string | null
}): IdiomaResolvido {
  const escolhido = ehIdioma(sinais.cookie) ? sinais.cookie : null
  const cabecalho = sinais.acceptLanguage?.trim()
  const detectado = cabecalho
    ? idiomaDoAcceptLanguage(cabecalho) ?? idiomaDoPais(sinais.pais) ?? "en"
    : IDIOMA_PADRAO
  return { idioma: escolhido ?? detectado, detectado, escolhido }
}
