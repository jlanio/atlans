import { cn } from "@/lib/utils"

/**
 * Quantos caracteres do FIM ficam sempre visíveis. Doze cobrem o que distingue
 * um artefato do outro na prática — `_v3.geojson`, `_2023.gpkg`, `_final.shp` —
 * sem comer a largura que o começo precisa.
 */
const CAUDA = 12

/** Onde um nome de arquivo troca de assunto. */
const SEPARADORES = "_-."
/**
 * Quanto o corte pode AVANÇAR para encostar num separador. Só avança — recuar
 * alongaria a cauda e comeria o começo, que é o que a largura estreita não tem
 * para dar.
 */
const JANELA = 5

/**
 * Onde a cauda começa. A contagem crua parte a palavra no meio
 * (`…consolidad` + `o_v3.geojson`); empurrada até o `_` seguinte ela cai onde o
 * nome muda de assunto (`…consolidado` + `_v3.geojson`). Sem separador por
 * perto, vale a contagem crua — melhor um corte feio que uma cauda gigante.
 */
function inicioDaCauda(letras: string[]): number {
  const bruto = Math.max(0, letras.length - CAUDA)
  if (bruto === 0) return 0
  const teto = Math.min(letras.length - 1, bruto + JANELA)
  for (let i = bruto; i <= teto; i++) {
    if (SEPARADORES.includes(letras[i])) return i
  }
  return bruto
}

/**
 * Nome de arquivo cortado NO MEIO, e não no fim.
 *
 * `truncate` come justamente o que identifica o artefato: numa lista de
 * `focos_calor_MT_2024_consolidado_v1`, `…_v2`, `…_v3` todas as linhas viravam
 * "focos_calor_MT_2024_c…" — indistinguíveis. Preservar o fim devolve a versão
 * e a extensão, que é onde mora a diferença.
 *
 * Dois `<span>` adjacentes e sem espaço entre eles: o começo encolhe com
 * reticências (`truncate`), o fim nunca encolhe (`shrink-0`). Leitor de tela e
 * cópia continuam vendo o nome inteiro — não há texto duplicado nem escondido,
 * só um ponto de quebra a mais no mesmo fluxo de texto.
 *
 * Serve para NOME DE ARQUIVO. Título de conversa é prosa e o fim dele não
 * carrega informação — ali o corte no fim continua certo.
 *
 * `data-nome` carrega o nome ÍNTEGRO num atributo. É a contrapartida de
 * dividir o texto: quem precisa do nome como um valor só (um teste, uma
 * automação, um seletor) o lê daqui, sem que a tela precise repetir o texto
 * num nó escondido — repetido, ele sairia duplicado ao copiar a linha.
 */
export function NomeDeArquivo({ nome, className }: { nome: string; className?: string }) {
  // `Array.from`, e não `nome.slice`: `slice` conta unidades UTF-16, e um
  // arquivo com emoji no nome (o Drive aceita) tinha o par substituto PARTIDO
  // no corte — os dois pedaços apareciam com "\uFFFD". Isto conta pontos de
  // código, que é o que resolve a mojibake. Um cluster de grafemas ainda pode
  // ser separado do seu seletor de variação (🗺️ são dois pontos de código), e
  // aí sai um glifo diferente — feio, mas legível, e sem `Intl.Segmenter`.
  const letras = Array.from(nome)
  const corte = inicioDaCauda(letras)
  return (
    // `overflow-hidden` no envoltório: numa largura menor que a própria cauda
    // ela vazaria por cima do que vem depois em vez de ser recortada.
    <span data-nome={nome} className={cn("flex min-w-0 overflow-hidden whitespace-nowrap", className)}>
      <span className="truncate">{letras.slice(0, corte).join("")}</span>
      <span className="shrink-0">{letras.slice(corte).join("")}</span>
    </span>
  )
}
