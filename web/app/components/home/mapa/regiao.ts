// web/app/components/home/mapa/regiao.ts
//
// De onde o globo da Home começa — e para onde ele volta quando a resposta
// chega. Antes era sempre a América do Sul; agora é a região de quem abre a
// página, sem pedir permissão de localização a ninguém:
//
//   1. o FUSO do navegador (`Intl…timeZone`) → a cidade de referência do fuso
//      (tabela IANA em `fusos.gerado.ts`). É o sinal mais fino: distingue o
//      leste do oeste dos EUA, e Manaus de São Paulo;
//   2. o PAÍS da conexão (`CF-IPCountry`, quando a Cloudflare o manda) → o
//      centro dos fusos daquele país. Cobre o navegador que esconde o fuso
//      (o "UTC", ou o fuso da Islândia, dos modos de privacidade — abaixo);
//   3. o CONTINENTE do nome do fuso (`Europe/…`, `Asia/…`) para um fuso que a
//      tabela não conheça;
//   4. um centro neutro (o meridiano de Greenwich, a 20° N).
//
// É o globo que segue a REGIÃO, não o idioma: uma brasileira com a tela em
// inglês continua vendo o Brasil.

import { FUSOS, PAISES } from "./fusos.gerado"

/**
 * A reserva quando nenhum sinal diz a região: neutra, sem país de preferência.
 * No zoom do hero, o meridiano de Greenwich a 20° N mostra a Europa, a África e
 * o Atlântico. (Era o Brasil, o país da primeira instalação.)
 */
export const CENTRO_PADRAO_DO_GLOBO: [number, number] = [0, 20]

// No zoom do hero o globo aparece inteiro; centrado num polo ele mostraria
// quase só gelo. A latitude é contida numa faixa em que o continente da pessoa
// continua no quadro (Oslo, Helsinque e Moscou caem a 50° N).
const LATITUDE_MAXIMA = 50
const LATITUDE_MINIMA = -45

const CONTINENTES: Readonly<Record<string, readonly [number, number]>> = {
  Europe: [15, 50],
  Africa: [20, 5],
  Asia: [90, 30],
  Australia: [134, -25],
  Pacific: [170, -15],
  Atlantic: [-30, 30],
  Indian: [70, -10],
  America: [-75, 10],
}

// Os navegadores que resistem a impressão digital (Firefox com
// `privacy.resistFingerprinting`, Tor Browser, Mullvad Browser) não dizem
// "UTC": dizem o fuso da Islândia, que tem offset zero o ano todo. Para eles
// o fuso não é sinal nenhum — sem isto, todo usuário desses navegadores abria
// o globo sobre o Atlântico Norte, e o país da conexão nunca era consultado.
// Só a própria Islândia (pelo país da conexão) mantém o fuso; sem país, vale
// o centro neutro, como para o "UTC".
const FUSOS_DOS_MODOS_DE_PRIVACIDADE = new Set(["Atlantic/Reykjavik", "Iceland"])

/** O fuso do navegador, ou `null` onde não houver (`Intl` ausente, SSR exótico). */
export function fusoDoNavegador(): string | null {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || null
  } catch {
    return null
  }
}

export function centroDaRegiao(sinais: { fuso?: string | null; pais?: string | null }): [number, number] {
  const pais = sinais.pais?.trim().toUpperCase() || null
  const informado = sinais.fuso?.trim() || null
  const fuso = informado && FUSOS_DOS_MODOS_DE_PRIVACIDADE.has(informado) && pais !== "IS" ? null : informado
  const alvo =
    (fuso ? FUSOS[fuso] : undefined)
    ?? (pais ? PAISES[pais] : undefined)
    ?? (fuso ? CONTINENTES[fuso.split("/")[0]] : undefined)
    ?? CENTRO_PADRAO_DO_GLOBO
  const [lon, lat] = alvo
  return [lon, Math.min(LATITUDE_MAXIMA, Math.max(LATITUDE_MINIMA, lat))]
}
