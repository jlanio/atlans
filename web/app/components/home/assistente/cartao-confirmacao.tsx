"use client"
import { TbCheck, TbX } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import { rotuloDaFerramenta } from "@/app/components/home/assistente/rotulos"
import { IDIOMA_PADRAO, type Idioma } from "@/lib/idioma"
import { textosDe, useIdiomaDaTela } from "../i18n"
import type { ConfirmacaoDoAssistente } from "@/app/components/home/assistente/quadros"

interface Props {
  confirmacao: ConfirmacaoDoAssistente
  /** Already clicked in this session — the buttons lock. */
  decidido: boolean
  /**
   * The server answered 409: the key had already been consumed (or expired). The
   * card stays locked — retrying would only render another 409 —, but instead of
   * "Decidido." (decided) it shows the microcopy that explains.
   */
  expirado?: boolean
  /** A stream is in progress — another confirmation cannot be triggered. */
  ocupado: boolean
  onDecidir: (toolUseId: string, token: string, decisao: "confirmar" | "recusar") => void
}

/**
 * The argument keys that describe THE TARGET of the action (the label comes from the dictionary).
 *
 * The selection is by KNOWN key, not "everything that came": the server summary
 * already collapses what is large, but a new argument must not start dumping
 * content into the card by accident. The order is reading order — the name before
 * the id, because the name is what tells what the action touches.
 */
const CAMPOS: readonly string[] = [
  "name",
  "workflow_name",
  "file_name",
  "path",
  "cron",
  "timezone",
  "access",
  "active",
  "version_number",
  "workflow_id",
  "schedule_id",
  "job_id",
  "file_id",
  "run_id",
]

const MAX_LINHAS = 4

/** The readable pairs of the argument summary: `[rótulo, valor]`. */
export function descreverAlvo(
  argumentos: Record<string, unknown>,
  idioma: Idioma = IDIOMA_PADRAO,
): Array<[string, string]> {
  const t = textosDe(idioma).assistente.confirmacao
  const linhas: Array<[string, string]> = []
  for (const chave of CAMPOS) {
    const rotulo = t.campos[chave]
    if (linhas.length >= MAX_LINHAS) break
    const bruto = argumentos[chave]
    if (bruto == null) continue
    if (typeof bruto === "object") continue // already collapsed by the server
    const valor = String(typeof bruto === "boolean" ? (bruto ? t.sim : t.nao) : bruto).trim()
    if (!valor) continue
    linhas.push([rotulo, valor.length > 72 ? `${valor.slice(0, 69)}…` : valor])
  }
  return linhas
}

/**
 * The click-to-confirm card. It never sends the arguments — only the
 * `tool_use_id`, the `token` and the decision; what runs are the args STORED on
 * the server. Without a token (key gone on replay) the buttons are dead.
 *
 * The arguments are SHOWN (not sent): the gate is the only barrier against
 * destructive actions, and "Apagar arquivo do Drive · a3f9c2e1…" asks for a blind click.
 */
export default function CartaoConfirmacao({ confirmacao, decidido, expirado = false, ocupado, onDecidir }: Props) {
  const { tool_use_id, token, acao } = confirmacao
  const semToken = !token
  const travado = decidido || ocupado || semToken
  // Two doors into the same dead end: the key vanished on replay, or the server
  // rejected the one that was sent. The sentence is the same because the way out is the same.
  const semSaida = expirado || (semToken && !decidido)
  const idioma = useIdiomaDaTela()
  const t = textosDe(idioma).assistente.confirmacao
  const rotulo = rotuloDaFerramenta(acao.tool, idioma)
  const linhas = descreverAlvo(acao.argumentos, idioma)
  const tituloId = `confirmacao-${tool_use_id}`

  return (
    <div
      role="group"
      aria-labelledby={tituloId}
      className="rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2.5"
    >
      {/* The screen reader goes SILENT when the assistant stops to wait for a
          click: the "respondendo" announcement disappears and nothing takes its place. */}
      {!decidido && !semToken && (
        <p role="status" className="sr-only">{t.pendente(rotulo)}</p>
      )}
      <p id={tituloId} className="text-xs font-semibold text-amber-400">{t.titulo(rotulo)}</p>

      {linhas.length > 0 ? (
        <dl className="mt-1 space-y-0.5">
          {linhas.map(([campo, valor]) => (
            <div key={campo} className="flex gap-1.5 text-xs text-amber-400/70">
              <dt className="shrink-0">{campo}:</dt>
              <dd className="min-w-0 break-words">{valor}</dd>
            </div>
          ))}
        </dl>
      ) : (
        acao.alvo && <p className="mt-0.5 break-words text-xs text-amber-400/70">{acao.alvo}</p>
      )}

      <div className="mt-2 flex gap-2 max-md:gap-3">
        <Button
          size="sm"
          className="h-7 gap-1 max-md:h-10"
          disabled={travado}
          onClick={() => onDecidir(tool_use_id, token, "confirmar")}
        >
          <TbCheck size={14} aria-hidden="true" /> {t.confirmar}
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="h-7 gap-1 max-md:h-10"
          disabled={travado}
          onClick={() => onDecidir(tool_use_id, token, "recusar")}
        >
          <TbX size={14} aria-hidden="true" /> {t.recusar}
        </Button>
      </div>

      {decidido && !expirado && <p className="mt-1.5 text-[11px] text-amber-400/70">{t.decidido}</p>}
      {semSaida && (
        <p className="mt-1.5 text-[11px] text-amber-400/70">{t.semSaida}</p>
      )}
      {/* The deadline exists on the server (15 min) and existed nowhere on the
          screen: someone coming back from lunch clicked and got an error. */}
      {!decidido && !semToken && (
        <p className="mt-1.5 text-[11px] text-amber-400/70">{t.prazo}</p>
      )}
    </div>
  )
}
