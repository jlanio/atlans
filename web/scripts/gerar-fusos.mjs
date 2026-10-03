#!/usr/bin/env node
// web/scripts/gerar-fusos.mjs
//
// Generates `app/components/home/mapa/fusos.gerado.ts` from the system's IANA
// time zone database (tzdata package): where the Home's globe starts, without
// asking anyone for location permission.
//
//   FUSOS  — time zone → [lon, lat] of the zone's reference city (zone.tab, and
//            zone1970.tab for what is missing), plus the OLD names some
//            browsers still return (Asia/Calcutta, America/Buenos_Aires…),
//            resolved through the links in tzdata.zi;
//   PAISES — country (ISO 3166 alpha-2) → center of that country's time zones,
//            the fallback when the browser does not report the time zone (e.g.
//            "UTC" in privacy modes) but the connection reports the country.
//
// Usage: node scripts/gerar-fusos.mjs [zoneinfo directory]  (default /usr/share/zoneinfo)

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

// zone.tab first: one line per (country, time zone), with the zone's own coordinates.
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
// The links (old names and aliases): "L TARGET NAME". Repeats until stable,
// because a link can point to another link.
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

/** Average in 3D space: a country that crosses the antimeridian (Fiji, Kiribati) does not land in the middle of the world. */
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
// Sorting with a FIXED locale: without it `localeCompare` uses the machine's,
// and the generated file changed order depending on who ran it (in Czech,
// Anchorage and Chicago swap places).
const ordem = (a, b) => a.localeCompare(b, "en")
const corpoFusos = [...fusos.entries()]
  .sort(([a], [b]) => ordem(a, b))
  .map(([nome, c]) => `  "${nome}": ${par(arredonda(c))},`)
  .join("\n")
const corpoPaises = [...porPais.entries()]
  .sort(([a], [b]) => ordem(a, b))
  .map(([pais, pontos]) => `  ${pais}: ${par(arredonda(centro(pontos)))},`)
  .join("\n")

// The tzdata version goes in the header: the same script on another version of
// the database generates a different file, and the diff needs to say why.
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
