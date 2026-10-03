import { cn } from "@/lib/utils"

/**
 * How many characters from the END always stay visible. Twelve cover what tells
 * one artifact from another in practice — `_v3.geojson`, `_2023.gpkg`,
 * `_final.shp` — without eating the width the beginning needs.
 */
const TAIL = 12

/** Where a file name changes subject. */
const SEPARATORS = "_-."
/**
 * How far the cut may MOVE FORWARD to land on a separator. It only moves
 * forward — moving back would lengthen the tail and eat the beginning, which is
 * what the narrow width has none of to spare.
 */
const WINDOW_SIZE = 5

/**
 * Where the tail starts. The raw count splits the word in the middle
 * (`…consolidad` + `o_v3.geojson`); pushed to the next `_` it falls where the
 * name changes subject (`…consolidado` + `_v3.geojson`). With no separator
 * nearby, the raw count applies — better an ugly cut than a giant tail.
 */
function tailStart(letras: string[]): number {
  const bruto = Math.max(0, letras.length - TAIL)
  if (bruto === 0) return 0
  const teto = Math.min(letras.length - 1, bruto + WINDOW_SIZE)
  for (let i = bruto; i <= teto; i++) {
    if (SEPARATORS.includes(letras[i])) return i
  }
  return bruto
}

/**
 * File name cut IN THE MIDDLE, not at the end.
 *
 * `truncate` eats exactly what identifies the artifact: in a list of
 * `focos_calor_MT_2024_consolidado_v1`, `…_v2`, `…_v3` every row became
 * "focos_calor_MT_2024_c…" — indistinguishable. Keeping the end brings back the
 * version and the extension, which is where the difference lives.
 *
 * Two adjacent `<span>`s with no space between them: the beginning shrinks with
 * an ellipsis (`truncate`), the end never shrinks (`shrink-0`). Screen readers
 * and copying still see the whole name — there is no duplicated or hidden text,
 * just one extra break point in the same text flow.
 *
 * Meant for FILE NAMES. A conversation title is prose and its end carries no
 * information — there, cutting at the end is still right.
 *
 * `data-nome` carries the WHOLE name in an attribute. It is the counterpart of
 * splitting the text: whoever needs the name as a single value (a test, an
 * automation, a selector) reads it from here, without the screen having to
 * repeat the text in a hidden node — repeated, it would come out duplicated
 * when copying the row.
 */
export function NomeDeArquivo({ nome, className }: { nome: string; className?: string }) {
  // `Array.from`, not `nome.slice`: `slice` counts UTF-16 units, and a file
  // with an emoji in its name (Drive accepts it) had the surrogate pair SPLIT
  // at the cut — both pieces showed up with "�". This counts code points,
  // which is what fixes the mojibake. A grapheme cluster can still be
  // separated from its variation selector (🗺️ is two code points), and then a
  // different glyph comes out — ugly, but legible, and no `Intl.Segmenter`.
  const letras = Array.from(nome)
  const corte = tailStart(letras)
  return (
    // `overflow-hidden` on the wrapper: at a width smaller than the tail itself
    // it would spill over what comes next instead of being clipped.
    <span data-nome={nome} className={cn("flex min-w-0 overflow-hidden whitespace-nowrap", className)}>
      <span className="truncate">{letras.slice(0, corte).join("")}</span>
      <span className="shrink-0">{letras.slice(corte).join("")}</span>
    </span>
  )
}
