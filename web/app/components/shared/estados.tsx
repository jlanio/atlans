"use client"

import type { ReactNode } from "react"
import type { IconType } from "react-icons"
import { TbAlertTriangle, TbFilterOff } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import { cn } from "@/lib/utils"

/**
 * Molduras dos estados de tela (contrato screen-patterns.md §3): o cartão
 * centralizado de erro, vazio e sem-resultado, e a linha âmbar de falha parcial.
 * Cada tela guarda no seu `estados.tsx` só o que é dela — os Skeleton*, que
 * desenham o layout real, e as frases — e monta os estados com estas peças.
 *
 * Antes cada tela recopiava a moldura, e as cópias divergiram: só três
 * anunciavam o erro ao leitor de tela, uma não pintava a borda destrutiva e
 * três não tinham onde pôr a mensagem do servidor. Aqui o anúncio
 * (`role="alert"`, §5) vem do tom do cartão, não de quem lembra de pô-lo.
 */

type Tom = "erro" | "neutro"

/**
 * - `compacto` (padrão): erro, sem-resultado e o vazio de uma seção — ícone de
 *   26 px, título `text-sm`, o botão logo abaixo da frase.
 * - `amplo`: o vazio que toma a tela (primeiro uso, sem acesso) — ícone de
 *   36 px, título `text-base`, e a ação primária (ou os passos) abaixo do texto.
 */
type Tamanho = "compacto" | "amplo"

/**
 * O cartão centralizado (§3.2 e §3.3). `tom="erro"` pinta a moldura
 * destrutiva — borda e círculo do ícone — e anuncia o cartão (`role="alert"`).
 */
export function CartaoDeEstado({
  icone: Icone, tom = "neutro", tamanho = "compacto", titulo, descricao, acao, children, tituloId, className,
}: {
  icone: IconType
  tom?: Tom
  tamanho?: Tamanho
  titulo: ReactNode
  descricao?: ReactNode
  /** Botão(ões) sob o texto. */
  acao?: ReactNode
  /** Conteúdo entre o texto e a ação (os passos do primeiro uso). */
  children?: ReactNode
  /** `id` do título, para uma região rotulada por ele (`aria-labelledby`). */
  tituloId?: string
  className?: string
}) {
  const erro = tom === "erro"
  const amplo = tamanho === "amplo"
  return (
    <div
      role={erro ? "alert" : undefined}
      className={cn(
        "flex flex-col items-center justify-center rounded-lg border bg-card px-6 py-14 text-center shadow-xs",
        amplo ? "gap-5" : "gap-3",
        erro && "border-destructive/20",
        className,
      )}
    >
      <div
        className={cn(
          "rounded-full",
          amplo ? "p-5" : "p-3",
          erro ? "border border-destructive/20 bg-destructive/10" : "bg-muted/60",
        )}
      >
        <Icone
          size={amplo ? 36 : 26}
          className={erro ? "text-destructive" : "text-muted-foreground/50"}
          aria-hidden="true"
        />
      </div>
      {amplo ? (
        <>
          <div className="flex max-w-md flex-col gap-1.5">
            <p id={tituloId} className="text-base font-semibold text-foreground">{titulo}</p>
            {descricao && <p className="text-sm text-muted-foreground">{descricao}</p>}
          </div>
          {children}
          {acao}
        </>
      ) : (
        <div className="flex max-w-[360px] flex-col items-center gap-0.5">
          <p id={tituloId} className="text-sm font-medium">{titulo}</p>
          {descricao && <p className="text-xs text-muted-foreground">{descricao}</p>}
          {children}
          {acao && <div className="mt-2 flex flex-wrap items-center justify-center gap-2">{acao}</div>}
        </div>
      )}
    </div>
  )
}

/**
 * A fonte-espinha caiu na 1ª carga (§3.2): o cartão de erro toma o lugar do
 * conteúdo. Só entra quando nunca houve carga aceita — a recarga que falha
 * sobre dados na tela vira toast ou `AvisoAmbar`, e esse gate é de quem compõe
 * a tela. `mensagem` é a do servidor, quando a tela a tem.
 */
export function ErroDeCarga({ titulo, mensagem, onTentar, className }: {
  /** "Não foi possível carregar os arquivos" — a frase é da tela. */
  titulo: string
  mensagem?: string | null
  onTentar?: () => void
  className?: string
}) {
  return (
    <CartaoDeEstado
      tom="erro"
      icone={TbAlertTriangle}
      titulo={titulo}
      descricao={mensagem || undefined}
      acao={onTentar && (
        <Button variant="outline" size="sm" onClick={onTentar} className="max-md:h-10">Tentar de novo</Button>
      )}
      className={className}
    />
  )
}

/**
 * Primeiro uso (§3.3): não há nada ainda e nenhum recorte ativo. Diz o que é e
 * por onde começar; a ação primária (`cta`, ou `acao` quando ela já vem pronta
 * — um diálogo com o próprio gatilho) aparece para quem `podeCriar`, e quem não
 * pode lê a quem pedir: `pedirA="criar o primeiro workflow"` vira "Peça a um
 * editor do workspace para criar o primeiro workflow.".
 */
export function VazioPrimeiroUso({
  icone, titulo, descricao, passos, cta, acao, podeCriar = true, pedirA,
}: {
  icone: IconType
  titulo: ReactNode
  descricao: ReactNode
  /** Passos numerados do "por onde começar". */
  passos?: readonly { titulo: string; detalhe: string }[]
  cta?: { rotulo: string; icone?: IconType; onClick: () => void }
  acao?: ReactNode
  podeCriar?: boolean
  pedirA?: string
}) {
  let final: ReactNode = null
  if (podeCriar) {
    const IconeDoCta = cta?.icone
    final = acao ?? (cta && (
      <Button onClick={cta.onClick} className="max-md:h-10">
        {IconeDoCta && <IconeDoCta size={15} aria-hidden="true" />} {cta.rotulo}
      </Button>
    ))
  } else if (pedirA) {
    final = <p className="text-sm text-muted-foreground">{`Peça a um editor do workspace para ${pedirA}.`}</p>
  }
  return (
    <CartaoDeEstado icone={icone} tamanho="amplo" titulo={titulo} descricao={descricao} acao={final}>
      {passos && passos.length > 0 && (
        <ol className="grid w-full max-w-lg gap-2 text-left sm:grid-cols-3">
          {passos.map((passo, i) => (
            <li key={passo.titulo} className="flex gap-2.5 rounded-md border bg-background/60 px-3 py-2.5">
              <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                {i + 1}
              </span>
              <span className="flex min-w-0 flex-col gap-0.5">
                <span className="text-sm font-medium">{passo.titulo}</span>
                <span className="text-xs text-muted-foreground">{passo.detalhe}</span>
              </span>
            </li>
          ))}
        </ol>
      )}
    </CartaoDeEstado>
  )
}

/**
 * A frase do sem-resultado: "Nenhum arquivo com «bacia» e este filtro" /
 * "…com «bacia»" / "…com este filtro". `sufixoFiltro` troca o "este filtro"
 * quando o recorte tem nome ("em GEOJSON"); `semRecorte` é o que dizer sem
 * termo nem filtro (por padrão, o próprio `nada`).
 */
export function textoDeSemResultado({ nada, termo, comFiltro, sufixoFiltro, semRecorte }: {
  /** "Nenhum arquivo", "Nenhuma credencial"… */
  nada: string
  termo: string
  comFiltro: boolean
  sufixoFiltro?: string
  semRecorte?: string
}): string {
  const t = termo.trim()
  if (t && comFiltro) return `${nada} com «${t}» ${sufixoFiltro ?? "e este filtro"}`
  if (t) return `${nada} com «${t}»`
  if (comFiltro) return `${nada} ${sufixoFiltro ?? "com este filtro"}`
  return semRecorte ?? nada
}

/**
 * Recorte ativo sem nenhuma linha (§3.3): o ícone `TbFilterOff` o separa do
 * vazio de fato, e a saída óbvia — limpar o recorte — vem no botão.
 */
export function SemResultado({ texto, dica, onLimpar }: {
  texto: string
  dica?: ReactNode
  onLimpar?: () => void
}) {
  return (
    <CartaoDeEstado
      icone={TbFilterOff}
      titulo={texto}
      descricao={dica}
      acao={onLimpar && (
        <Button variant="outline" size="sm" onClick={onLimpar} className="max-md:h-10">Limpar filtros</Button>
      )}
    />
  )
}

/**
 * Falha parcial de uma seção (§3.4): a fonte daquele bloco caiu, mas o resto
 * continua na tela — uma linha âmbar discreta (`role="status"`, não alerta)
 * com o "Tentar de novo" inline. `rotuloDoBotao` existe para a Home, que fala
 * três idiomas; sem ele o botão é o "Tentar de novo" de sempre.
 */
export function AvisoAmbar({ children, onTentar, rotuloDoBotao = "Tentar de novo" }: {
  children: ReactNode
  onTentar: () => void
  rotuloDoBotao?: string
}) {
  return (
    <p
      role="status"
      className="flex flex-wrap items-center gap-x-2 gap-y-1 rounded-md border border-amber-500/30 bg-amber-50 px-3 py-1.5 text-xs text-amber-700 dark:bg-amber-500/10 dark:text-amber-400"
    >
      <TbAlertTriangle size={14} className="shrink-0" aria-hidden="true" />
      <span>{children}</span>
      <button
        type="button"
        onClick={onTentar}
        className="inline-flex items-center rounded-sm font-medium underline-offset-2 outline-none hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50 max-md:min-h-10"
      >
        {rotuloDoBotao}
      </button>
    </p>
  )
}
