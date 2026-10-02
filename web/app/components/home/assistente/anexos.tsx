"use client"

// web/app/components/home/assistente/anexos.tsx
//
// Os arquivos soltos sobre a Home, mostrados DENTRO da caixa do assistente.
//
// Três peças, e as três são montadas pela barra e pelo painel — as duas
// superfícies onde se escreve. Montar só numa repetiria o bug que o
// `AvisoDeCotaCheia` existe para não repetir: um recurso que some conforme a
// tela. Ctrl+I troca uma pela outra, e é por isso que o estado mora na store,
// não aqui.
//
// - `ConviteDeSoltura`: a linha que aparece na caixa enquanto o arquivo está no
//   ar. É o único realce do arraste — nenhum véu cobre o globo.
// - `ChipsDeAnexo`: o que está subindo e o que já está no Drive.
// - `AvisoDeAnexosRecusados`: o que o servidor recusou, com o MESMO painel da
//   tela `/drive` (`ResultadoDoUpload`) e a mesma classificação do motivo.
//   Fica fora dos chips de propósito: o recusado não entra na mensagem, e
//   deixá-lo na fileira faria a pessoa mandar a pergunta achando que ele foi.

import { TbCheck, TbLoader2, TbPaperclip, TbX } from "react-icons/tb"

import { ResultadoDoUpload, type UploadError } from "@/app/components/drive/resultado-upload"
import { IDIOMA_PADRAO, type Idioma } from "@/lib/idioma"
import { textosDe, useIdiomaDaTela, useTextos } from "../i18n"
import { FORMATOS } from "../i18n/formatos"
import { cn } from "@/lib/utils"
import type { Anexo } from "@/app/stores/homeStore"
import { formatBytes } from "@/utils/formatters"

// ── O texto que viaja com a mensagem ─────────────────────────────────────────

/** Os que de fato chegaram ao Drive. Só eles podem ser citados. */
export function anexosProntos(anexos: Anexo[]): Anexo[] {
  return anexos.filter((a) => a.estado === "pronto")
}

/**
 * Acrescenta à mensagem a lista do que acabou de subir.
 *
 * Sem isto, «analise isso» chega ao assistente sem nenhum «isso»: ele tem a
 * ferramenta `list_drive_files` e enxerga o workspace inteiro, mas não tem como
 * saber QUAIS dos arquivos de lá são os desta pergunta. A linha é a tradução
 * literal dos chips que a pessoa está vendo na caixa — nada é anexado sem estar
 * à vista.
 *
 * Os que ainda estão subindo ficam de fora: citá-los seria mandar o assistente
 * procurar um arquivo que talvez nem exista.
 */
export function comReferencia(texto: string, anexos: Anexo[], idioma: Idioma = IDIOMA_PADRAO): string {
  const nomes = anexosProntos(anexos).map((a) => a.nome)
  if (nomes.length === 0) return texto
  const lista = textosDe(idioma).assistente.anexos.referencia(nomes.join(", "))
  return texto ? `${texto}\n\n${lista}` : lista
}

/**
 * A pergunta que a caixa passa a oferecer quando há anexo pronto.
 *
 * Toma o lugar das sugestões digitadas do hero (que falam de focos de calor e
 * desmatamento): oferecer «Mostre os focos de calor» a quem acabou de soltar um
 * shapefile é ignorar o que a pessoa fez. `null` quando não há nada pronto —
 * aí a caixa volta ao placeholder de sempre.
 */
export function sugestaoParaAnexos(anexos: Anexo[], idioma: Idioma = IDIOMA_PADRAO): string | null {
  const nomes = anexosProntos(anexos).map((a) => a.nome)
  if (nomes.length === 0) return null
  const t = textosDe(idioma).assistente.anexos
  if (nomes.length === 1) return t.analise(nomes[0])
  const outros = nomes.length - 1
  return t.analiseMais(nomes[0], t.arquivos(outros, FORMATOS[idioma].inteiro(outros)))
}

/** As recusas, na forma que o painel da tela `/drive` consome. */
export function recusasDe(anexos: Anexo[], idioma: Idioma = IDIOMA_PADRAO): UploadError[] {
  return anexos
    .filter((a) => a.estado === "recusado")
    .map((a) => ({
      fileName: a.nome,
      detail: a.motivo ?? textosDe(idioma).assistente.anexos.servidorRecusou,
      type: a.tipo ?? "other",
    }))
}

// ── As peças ─────────────────────────────────────────────────────────────────

/** A linha de convite, enquanto o arquivo está no ar sobre a página. */
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
 * A fileira de chips: o que está subindo e o que já está no Drive.
 *
 * O × só existe depois que o arquivo chegou. Durante o envio ele seria uma
 * promessa falsa — a requisição continuaria correndo e o arquivo apareceria no
 * Drive de qualquer jeito, sem nada na tela dizendo isso.
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
 * O que o servidor recusou. É o painel da tela `/drive`, inteiro: mesma
 * classificação, mesmos rótulos, mesmo texto de motivo.
 *
 * Ele some só quando a pessoa fecha — enviar a mensagem não o leva junto,
 * porque a recusa não tem nada a ver com a pergunta e ainda precisa ser lida.
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
