"use client"

import { TbKey, TbPlus } from "react-icons/tb"
import { Skeleton } from "@/app/components/ui/skeleton"
import * as Estado from "@/app/components/shared/estados"

/**
 * Estados da tela de Credenciais (contrato screen-patterns.md §3): carregando,
 * erro de carga, primeiro uso e sem resultado. Cada um diz o que aconteceu e o
 * que fazer a seguir. Aqui ficam o skeleton e as frases da tela; a moldura de
 * cada estado é a de `shared/estados.tsx`.
 */

/**
 * Primeira carga: o cabeçalho real fica por cima (o `index` sempre o renderiza,
 * com o subtítulo em esqueleto), e aqui vai o desenho da toolbar e das linhas —
 * com as mesmas alturas da lista de verdade, para a troca não pular.
 */
export function SkeletonDeCredenciais() {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label="Carregando as credenciais"
      className="flex flex-col gap-4"
    >
      {/* Fantasma da barra de busca/filtro/ordenar/agrupar. */}
      <div className="flex flex-wrap items-center gap-2">
        <Skeleton className="h-9 min-w-[12rem] flex-1 rounded-md max-md:h-10" />
        <Skeleton className="h-9 w-36 rounded-md max-md:h-10" />
        <Skeleton className="h-9 w-36 rounded-md max-md:h-10" />
        <Skeleton className="h-9 w-40 rounded-md max-md:h-10" />
      </div>
      <div className="flex flex-col gap-3">
        {[0, 1, 2].map(i => <LinhaFantasma key={i} />)}
      </div>
    </div>
  )
}

/**
 * Mais alta no telefone: ali o EntityCard empilha os selos numa segunda linha,
 * e um esqueleto baixo encolhia a lista no instante em que os dados chegavam.
 */
function LinhaFantasma() {
  return (
    <div className="flex h-[86px] items-center gap-3 rounded-lg border bg-card px-3 shadow-xs sm:h-[58px]">
      <Skeleton className="size-8 shrink-0 rounded-md" />
      <div className="flex flex-1 flex-col gap-1.5">
        <Skeleton className="h-3.5 w-1/3" />
        <Skeleton className="h-3 w-1/2" />
      </div>
      <Skeleton className="hidden h-5 w-24 rounded-full sm:block" />
      <Skeleton className="size-7 rounded-full" />
    </div>
  )
}

/**
 * A fonte-espinha (a listagem) caiu na 1ª carga. Só toma a tela quando nunca
 * houve carga aceita — recarga que falha sobre lista pronta mantém o que havia
 * e avisa por toast (ver `index`). `mensagem` é a do servidor; sem ela, a
 * orientação de sempre.
 */
export function ErroDeCarga({ mensagem, onTentar }: { mensagem?: string | null; onTentar: () => void }) {
  return (
    <Estado.ErroDeCarga
      titulo="Não foi possível carregar as credenciais."
      mensagem={mensagem || "Verifique a conexão e tente novamente."}
      onTentar={onTentar}
    />
  )
}

/**
 * Sem nenhuma credencial: a tela ensina o que é uma credencial e por onde
 * começar. Criar é uma ação pessoal (owner-only por natureza), então o CTA
 * aparece para quem pode; o fallback existe por contrato.
 */
export function VazioPrimeiroUso({ canEdit, onCriar }: { canEdit: boolean; onCriar: () => void }) {
  return (
    <Estado.VazioPrimeiroUso
      icone={TbKey}
      titulo="Comece pela primeira credencial"
      descricao={
        <>
          Credenciais guardam as conexões privadas — bancos, APIs e serviços — que seus workflows
          reutilizam nos nós, sem repetir segredos em cada um.
        </>
      }
      cta={{ rotulo: "Criar credencial", icone: TbPlus, onClick: onCriar }}
      podeCriar={canEdit}
      pedirA="criar a primeira credencial"
    />
  )
}

/** «Nenhuma credencial com «q»» / «…com este filtro» / «…com «q» e este filtro». */
export function textoDeSemResultado(q: string, comFiltro: boolean): string {
  return Estado.textoDeSemResultado({
    nada: "Nenhuma credencial",
    termo: q,
    comFiltro,
    semRecorte: "Nenhuma credencial corresponde ao filtro",
  })
}

/** Busca ou filtro de tipo sem nenhuma linha: a saída óbvia é limpar o recorte. */
export function SemResultado({ q, comFiltro, onLimpar }: {
  q: string
  comFiltro: boolean
  onLimpar: () => void
}) {
  return <Estado.SemResultado texto={textoDeSemResultado(q, comFiltro)} onLimpar={onLimpar} />
}
