#!/usr/bin/env node
// web/scripts/gerar-fusos.mjs
//
// Gera `app/components/home/mapa/fusos.gerado.ts` a partir da base IANA de
// fusos horários do sistema (pacote tzdata): de onde o globo da Home começa,
// sem pedir permissão de localização a ninguém.
//
//   FUSOS  — fuso → [lon, lat] da cidade de referência do fuso (zone.tab, e
//            zone1970.tab para o que faltar), mais os nomes ANTIGOS que alguns
//            navegadores ainda devolvem (Asia/Calcutta, America/Buenos_Aires…),
//            resolvidos pelos links do tzdata.zi;
//   PAISES — país (ISO 3166 alfa-2) → centro dos fusos daquele país, a reserva
//            quando o navegador não diz o fuso (ex.: "UTC" dos modos de
//            privacidade) mas a conexão diz o país.
//
// Uso: node scripts/gerar-fusos.mjs [diretório do zoneinfo]  (padrão /usr/share/zoneinfo)

import { readFileSync, writeFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

const ZONEINFO = process.argv[2] ?? "/usr/share/zoneinfo"
const SAIDA = join(dirname(fileURLToPath(import.meta.url)), "../app/components/home/mapa/fusos.gerado.ts")

/** ISO 6709 (±DDMM[SS]±DDDMM[SS]) → [lon, lat] em graus decimais. */
function coordenadas(iso) {
  const m = /^([+-])(\d{2})(\d{2})(\d{2})?([+-])(\d{3})(\d{2})(\d{2})?$/.exec(iso)
  if (!m) throw new Error(`coordenada ISO 6709 inválida: ${iso}`)
  const lat = (m[1] === "-" ? -1 : 1) * (Number(m[2]) + Number(m[3]) / 60 + Number(m[4] ?? 0) / 3600)
  const lon = (m[5] === "-" ? -1 : 1) * (Number(m[6]) + Number(m[7]) / 60 + Number(m[8] ?? 0) / 3600)
  return [lon, lat]
}

const arredonda = ([lon, lat]) => [Math.round(lon * 10) / 10, Math.round(lat * 10) / 10]

function linhas(arquivo) {
  return readFileSync(join(ZONEINFO, arquivo), "utf-8")
    .split("\n")
    .filter((l) => l && !l.startsWith("#"))
    .map((l) => l.split("\t"))
}

const fusos = new Map()
const porPais = new Map()

// zone.tab primeiro: uma linha por (país, fuso), com as coordenadas do próprio fuso.
for (const [pais, iso, fuso] of linhas("zone.tab")) {
  const c = coordenadas(iso)
  if (!fusos.has(fuso)) fusos.set(fuso, c)
  if (!porPais.has(pais)) porPais.set(pais, [])
  porPais.get(pais).push(c)
}
// zone1970.tab completa o que faltar.
for (const [, iso, fuso] of linhas("zone1970.tab")) {
  if (!fusos.has(fuso)) fusos.set(fuso, coordenadas(iso))
}
// Os links (nomes antigos e aliases): "L ALVO NOME". Repete até estabilizar,
// porque um link pode apontar para outro link.
const links = readFileSync(join(ZONEINFO, "tzdata.zi"), "utf-8")
  .split("\n")
  .filter((l) => l.startsWith("L "))
  .map((l) => l.split(/\s+/).slice(1, 3))
let mudou = true
while (mudou) {
  mudou = false
  for (const [alvo, nome] of links) {
    if (!fusos.has(nome) && fusos.has(alvo)) {
      fusos.set(nome, fusos.get(alvo))
      mudou = true
    }
  }
}

/** Média no espaço 3D: um país que cruza o antimeridiano (Fiji, Kiribati) não cai no meio do mundo. */
function centro(pontos) {
  let x = 0, y = 0, z = 0
  for (const [lon, lat] of pontos) {
    const a = (lat * Math.PI) / 180, b = (lon * Math.PI) / 180
    x += Math.cos(a) * Math.cos(b)
    y += Math.cos(a) * Math.sin(b)
    z += Math.sin(a)
  }
  const lon = (Math.atan2(y, x) * 180) / Math.PI
  const lat = (Math.atan2(z, Math.hypot(x, y)) * 180) / Math.PI
  return [lon, lat]
}

const par = ([lon, lat]) => `[${lon}, ${lat}]`
// Ordenação com idioma FIXO: sem ele o `localeCompare` usa o da máquina, e o
// arquivo gerado mudava de ordem conforme quem rodasse (em tcheco, Anchorage e
// Chicago trocam de lugar).
const ordem = (a, b) => a.localeCompare(b, "en")
const corpoFusos = [...fusos.entries()]
  .sort(([a], [b]) => ordem(a, b))
  .map(([nome, c]) => `  "${nome}": ${par(arredonda(c))},`)
  .join("\n")
const corpoPaises = [...porPais.entries()]
  .sort(([a], [b]) => ordem(a, b))
  .map(([pais, pontos]) => `  ${pais}: ${par(arredonda(centro(pontos)))},`)
  .join("\n")

// A versão do tzdata vai no cabeçalho: o mesmo script em outra versão da base
// gera outro arquivo, e o diff precisa dizer por quê.
const versao = /^# version (\S+)/m.exec(readFileSync(join(ZONEINFO, "tzdata.zi"), "utf-8"))?.[1] ?? "desconhecida"

const ts = `// web/app/components/home/mapa/fusos.gerado.ts
//
// GERADO por \`node scripts/gerar-fusos.mjs\` a partir da base IANA de fusos
// (tzdata ${versao}: zone.tab, zone1970.tab, tzdata.zi). Não edite à mão — rode o script.
// Coordenadas em [longitude, latitude], com uma casa decimal.

/** Fuso → [lon, lat] da cidade de referência do fuso. */
export const FUSOS: Readonly<Record<string, readonly [number, number]>> = {
${corpoFusos}
}

/** País (ISO 3166 alfa-2) → [lon, lat] do centro dos fusos daquele país. */
export const PAISES: Readonly<Record<string, readonly [number, number]>> = {
${corpoPaises}
}
`
writeFileSync(SAIDA, ts)
console.log(`fusos: ${fusos.size} · países: ${porPais.size} · ${Math.round(ts.length / 1024)} KB → ${SAIDA}`)
