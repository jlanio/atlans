"use client"

// web/app/components/home/assistente/anexos.tsx
//
// The files dropped on the Home, shown INSIDE the assistant's box.
//
// Three pieces, and all three are mounted by the bar and by the panel — the two
// surfaces where one writes. Mounting in only one would repeat the bug that
// `AvisoDeCotaCheia` exists to avoid: a feature that disappears depending on the
// screen. Ctrl+I swaps one for the other, and that is why the state lives in the
// store, not here.
//
// - `ConviteDeSoltura`: the line that appears in the box while the file is in
//   the air. It is the drag's only highlight — no veil covers the globe.
// - `ChipsDeAnexo`: what is uploading and what is already in the Drive.
// - `AvisoDeAnexosRecusados`: what the server rejected, with the SAME panel as
//   the `/drive` screen (`ResultadoDoUpload`) and the same reason classification.
//   It stays out of the chips on purpose: the rejected file doesn't go into the
//   message, and leaving it in the row would make the person send the question
//   thinking it went along.

import { TbCheck, TbLoader2, TbPaperclip, TbX } from "react-icons/tb"

import { ResultadoDoUpload, type UploadError } from "@/app/components/drive/resultado-upload"
import { IDIOMA_PADRAO, type Idioma } from "@/lib/idioma"
import { textosDe, useIdiomaDaTela, useTextos } from "../i18n"
import { FORMATOS } from "../i18n/formatos"
import { cn } from "@/lib/utils"
import type { Anexo } from "@/app/stores/homeStore"
import { formatBytes } from "@/utils/formatters"

// ── The text that travels with the message ───────────────────────────────────

/** The ones that actually reached the Drive. Only they can be cited. */
export function anexosProntos(anexos: Anexo[]): Anexo[] {
  return anexos.filter((a) => a.estado === "pronto")
}

/**
 * Appends to the message the list of what was just uploaded.
 *
 * Without this, "analise isso" (analyze this) reaches the assistant without any
 * "this": it has the `list_drive_files` tool and sees the whole workspace, but
 * has no way to know WHICH of the files there are the ones for this question.
 * The line is the literal translation of the chips the person sees in the box —
 * nothing is attached without being in view.
 *
 * The ones still uploading are left out: citing them would send the assistant
 * looking for a file that may not even exist.
 */
export function comReferencia(texto: string, anexos: Anexo[], idioma: Idioma = IDIOMA_PADRAO): string {
  const nomes = anexosProntos(anexos).map((a) => a.nome)
  if (nomes.length === 0) return texto
  const lista = textosDe(idioma).assistente.anexos.referencia(nomes.join(", "))
  return texto ? `${texto}\n\n${lista}` : lista
}

/**
 * The question the box starts offering when there is a ready attachment.
 *
 * It takes the place of the hero's typed suggestions (which talk about fire
 * hotspots and deforestation): offering "Mostre os focos de calor" to someone
 * who just dropped a shapefile is ignoring what the person did. `null` when
 * nothing is ready — then the box goes back to the usual placeholder.
 */
export function sugestaoParaAnexos(anexos: Anexo[], idioma: Idioma = IDIOMA_PADRAO): string | null {
  const nomes = anexosProntos(anexos).map((a) => a.nome)
  if (nomes.length === 0) return null
  const t = textosDe(idioma).assistente.anexos
  if (nomes.length === 1) return t.analise(nomes[0])
  const outros = nomes.length - 1
  return t.analiseMais(nomes[0], t.arquivos(outros, FORMATOS[idioma].inteiro(outros)))
}

/** The rejections, in the shape the `/drive` screen's panel consumes. */
export function recusasDe(anexos: Anexo[], idioma: Idioma = IDIOMA_PADRAO): UploadError[] {
  return anexos
    .filter((a) => a.estado === "recusado")
    .map((a) => ({
      fileName: a.nome,
      detail: a.motivo ?? textosDe(idioma).assistente.anexos.servidorRecusou,
      type: a.tipo ?? "other",
    }))
}

// ── The pieces ───────────────────────────────────────────────────────────────

/** The invitation line, while the file is in the air over the page. */
export function ConviteDeSoltura({ className }: { className?: string }) {
  const t = useTextos().assistente.anexos
  return (
    <p
      data-testid="convite-de-soltura"
      className={cn("flex items-center gap-2 text-[12.5px] font-medium text-primary", className)}
    >
      <TbPaperclip size={14} aria-hidden="true" />
      {t.solte}
    </p>
  )
}

/**
 * The row of chips: what is uploading and what is already in the Drive.
 *
 * The × only exists after the file has arrived. During the upload it would be a
 * false promise — the request would keep running and the file would appear in
 * the Drive anyway, with nothing on screen saying so.
 */
export function ChipsDeAnexo({
  anexos, onRemover, className,
}: {
  anexos: Anexo[]
  onRemover: (id: string) => void
  className?: string
}) {
  const t = useTextos().assistente.anexos
  const visiveis = anexos.filter((a) => a.estado !== "recusado")
  if (visiveis.length === 0) return null

  return (
    <ul
      data-testid="chips-de-anexo"
      aria-label={t.rotuloDosChips}
      className={cn("flex list-none flex-wrap gap-1.5 p-0", className)}
    >
      {visiveis.map((anexo) => {
        const pronto = anexo.estado === "pronto"
        return (
          <li
            key={anexo.id}
            className="flex min-w-0 max-w-full items-center gap-1.5 rounded-md border border-border/60 bg-secondary px-2 py-1 text-[11.5px]"
          >
            {pronto ? (
              <TbCheck size={13} className="shrink-0 text-emerald-400" aria-hidden="true" />
            ) : (
              <TbLoader2 size={13} className="shrink-0 animate-spin text-primary motion-reduce:animate-none" aria-hidden="true" />
            )}
            <span className="min-w-0 truncate text-foreground" title={`${anexo.nome} · ${formatBytes(anexo.bytes)}`}>
              {anexo.nome}
            </span>
            <span className="sr-only">{pronto ? t.noDrive : t.enviando}</span>
            {pronto && (
              <button
                type="button"
                onClick={() => onRemover(anexo.id)}
                aria-label={t.tirar(anexo.nome)}
                className="shrink-0 rounded-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <TbX size={12} aria-hidden="true" />
              </button>
            )}
          </li>
        )
      })}
    </ul>
  )
}

/**
 * What the server rejected. It is the `/drive` screen's panel, whole: same
 * classification, same labels, same reason text.
 *
 * It only goes away when the person closes it — sending the message doesn't take
 * it along, because the rejection has nothing to do with the question and still
 * needs to be read.
 */
export function AvisoDeAnexosRecusados({
  anexos, onFechar, className,
}: {
  anexos: Anexo[]
  onFechar: () => void
  className?: string
}) {
  const idioma = useIdiomaDaTela()
  const t = useTextos().assistente.anexos
  const recusas = recusasDe(anexos, idioma)
  if (recusas.length === 0) return null
  return (
    <div data-testid="anexos-recusados" className={cn("text-left", className)}>
      <ResultadoDoUpload sucessos={0} erros={recusas} onFechar={onFechar} textos={t.resultado} />
    </div>
  )
}
