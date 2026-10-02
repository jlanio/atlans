"use client"
import { TbCheck, TbX } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import { rotuloDaFerramenta } from "@/app/components/home/assistente/rotulos"
import { IDIOMA_PADRAO, type Idioma } from "@/lib/idioma"
import { textosDe, useIdiomaDaTela } from "../i18n"
import type { ConfirmacaoDoAssistente } from "@/app/components/home/assistente/quadros"

interface Props {
  confirmacao: ConfirmacaoDoAssistente
  /** Já clicado nesta sessão — os botões travam. */
  decidido: boolean
  /**
   * O servidor respondeu 409: a chave já tinha sido consumida (ou venceu). O
   * cartão continua travado — refazer só renderia outro 409 —, mas no lugar de
   * "Decidido." vai a microcópia que explica.
   */
  expirado?: boolean
  /** Há um stream em curso — não dá para disparar outra confirmação. */
  ocupado: boolean
  onDecidir: (toolUseId: string, token: string, decisao: "confirmar" | "recusar") => void
}

/**
 * As chaves dos argumentos que descrevem O ALVO da ação (o rótulo vem do dicionário).
 *
 * A escolha é por chave CONHECIDA, e não "tudo que veio": o resumo do servidor
 * já colapsa o que é grande, mas um argumento novo não pode passar a despejar
 * conteúdo dentro do cartão por acidente. A ordem é a de leitura — o nome antes
 * do id, porque é o nome que diz em que a ação mexe.
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

/** Os pares legíveis do resumo dos argumentos: `[rótulo, valor]`. */
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
    if (typeof bruto === "object") continue // já colapsado pelo servidor
    const valor = String(typeof bruto === "boolean" ? (bruto ? t.sim : t.nao) : bruto).trim()
    if (!valor) continue
    linhas.push([rotulo, valor.length > 72 ? `${valor.slice(0, 69)}…` : valor])
  }
  return linhas
}

/**
 * O cartão de confirmação por clique. Nunca manda os argumentos — só o
 * `tool_use_id`, o `token` e a decisão; o que roda são os args ARMAZENADOS no
 * servidor. Sem token (chave sumida no replay) os botões ficam mortos.
 *
 * Os argumentos são MOSTRADOS (não enviados): o portão é a única barreira contra
 * o destrutivo, e "Apagar arquivo do Drive · a3f9c2e1…" pede um clique às cegas.
 */
export default function CartaoConfirmacao({ confirmacao, decidido, expirado = false, ocupado, onDecidir }: Props) {
  const { tool_use_id, token, acao } = confirmacao
  const semToken = !token
  const travado = decidido || ocupado || semToken
  // Duas portas para o mesmo beco: a chave sumiu no replay, ou o servidor
  // recusou a que foi mandada. A frase é a mesma porque a saída é a mesma.
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
      {/* O leitor de tela fica MUDO quando o assistente para esperando um
          clique: o anúncio de "respondendo" some e nada toma o lugar dele. */}
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
      {/* O prazo existe no servidor (15 min) e não existia em lugar nenhum da
          tela: quem voltava do almoço clicava e levava um erro. */}
      {!decidido && !semToken && (
        <p className="mt-1.5 text-[11px] text-amber-400/70">{t.prazo}</p>
      )}
    </div>
  )
}
