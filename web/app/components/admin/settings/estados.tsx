"use client"

import type { IconType } from "react-icons"
import { Skeleton } from "@/app/components/ui/skeleton"
import * as Estado from "@/app/components/shared/estados"

/**
 * Estados da tela de Admin › Configurações (contrato §3): skeleton da 1ª carga
 * por seção, cartão de erro quando a fonte da seção cai antes de haver qualquer
 * leitura, vazios com ícone-em-círculo e o aviso âmbar de falha parcial. Os
 * skeletons e as frases ficam aqui; a moldura é a de `shared/estados.tsx`.
 *
 * Como cada seção mora dentro de uma casca `<section>` que já desenha a moldura
 * (borda + `bg-card`) e o cabeçalho, os skeletons aqui são só o CORPO — não
 * repetem a borda, senão a seção teria duas.
 */

// ── Skeletons de 1ª carga (corpo da seção) ──────────────────────────────────

/**
 * Visão geral: os quatro indicadores (altura real `h-24`) e o bloco de
 * pendências. `aria-busy` no wrapper para o leitor de tela anunciar a espera.
 */
export function SkeletonVisaoGeral() {
  return (
    <div role="status" aria-busy="true" aria-label="Carregando a visão geral" className="flex flex-col gap-5">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-24 w-full rounded-lg" />)}
      </div>
      <div className="flex flex-col gap-2">
        <Skeleton className="h-4 w-28" />
        {[0, 1, 2].map(i => <Skeleton key={i} className="h-12 w-full rounded-md" />)}
      </div>
    </div>
  )
}

/**
 * Tabela empilhável (Armazenamento, Lixeira, Isolamento): uma faixa de
 * cabeçalho e algumas linhas com a altura de verdade, para a troca para o
 * conteúdo não pular a página.
 */
export function SkeletonDeTabela({ linhas = 4, rotulo }: { linhas?: number; rotulo: string }) {
  return (
    <div role="status" aria-busy="true" aria-label={rotulo} className="flex flex-col gap-2.5">
      <Skeleton className="h-8 w-full rounded-md" />
      {Array.from({ length: linhas }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full rounded-md" />
      ))}
    </div>
  )
}

/**
 * Formulário curto (Whitelist, Retenção, Drive): o rótulo, a linha de campo +
 * botão e a nota de ajuda.
 */
export function SkeletonDeFormulario({ rotulo }: { rotulo: string }) {
  return (
    <div role="status" aria-busy="true" aria-label={rotulo} className="flex flex-col gap-3">
      <Skeleton className="h-3 w-40" />
      <div className="flex gap-2">
        <Skeleton className="h-9 w-32 rounded-md" />
        <Skeleton className="h-9 w-24 rounded-md" />
      </div>
      <Skeleton className="h-3 w-full max-w-md" />
    </div>
  )
}

/**
 * Nodes: a linha de resumo + busca e alguns grupos recolhidos.
 */
export function SkeletonDeNodes() {
  return (
    <div role="status" aria-busy="true" aria-label="Carregando os nodes" className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <Skeleton className="h-3 w-48" />
        <Skeleton className="h-8 w-40 rounded-md" />
      </div>
      {[0, 1, 2].map(i => <Skeleton key={i} className="h-9 w-full rounded-md" />)}
    </div>
  )
}

// ── Erro (a fonte da seção caiu antes de haver leitura) ──────────────────────

/**
 * A leitura de uma seção falhou e não há nada em tela: o corpo dá lugar ao
 * cartão de erro. Antes o `error` do `useFetchData` era ignorado e a seção
 * ficava simplesmente em branco — sem dizer que falhou nem como tentar de novo.
 *
 * Numa RECARGA com dados já na tela isto não aparece (o hook mantém o que
 * havia); é o `AvisoDeSecao` que cobre essa falha parcial.
 */
export function CartaoDeErro({
  mensagem, onTentar,
}: {
  mensagem?: string
  onTentar: () => void
}) {
  return <Estado.ErroDeCarga titulo="Não foi possível carregar as configurações" mensagem={mensagem} onTentar={onTentar} />
}

// ── Vazio (a leitura foi bem, mas não há nada a listar) ──────────────────────

/**
 * Vazio de uma seção — Armazenamento sem arquivos, Lixeira vazia, Drive sem
 * extensões. Ícone-em-círculo e uma frase; substitui o `<p italic>` solto que
 * havia antes, que não se distinguia de um rótulo qualquer.
 */
export function VazioEmCirculo({
  icone, titulo, descricao,
}: {
  icone: IconType
  titulo: string
  descricao?: string
}) {
  return <Estado.CartaoDeEstado icone={icone} titulo={titulo} descricao={descricao} />
}

// ── Aviso âmbar (falha parcial de uma seção, sem derrubar o bloco) ───────────

/**
 * Falha parcial por seção (§3.4): a fonte daquele bloco caiu numa recarga, mas
 * havia dado em tela. A linha âmbar de `shared/estados.tsx`, com o "Tentar de
 * novo" inline.
 */
export { AvisoAmbar as AvisoDeSecao } from "@/app/components/shared/estados"
