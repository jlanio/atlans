"use client"

import type { ReactNode } from "react"
import { TbServerOff } from "react-icons/tb"
import { Skeleton } from "@/app/components/ui/skeleton"
import * as Estado from "@/app/components/shared/estados"

/**
 * Estados da tela de Executores (contrato §3): skeleton da 1ª carga, erro de
 * espinha, vazio de primeiro uso × sem-resultado e o aviso âmbar de falha
 * parcial das métricas. Cada um diz o que aconteceu e o que fazer a seguir;
 * aqui ficam o skeleton e as frases, com a moldura de `shared/estados.tsx`.
 *
 * Aqui o "conteúdo" é o TRILHO — tabela densa, variante deliberada — então o
 * skeleton desenha justamente ele: cabeçalho de colunas + linhas na altura
 * real (h-11), para a troca para a lista não pular a página.
 */

/** Primeira carga: o cabeçalho real fica por cima (o `index` sempre o renderiza). */
export function SkeletonDeExecutores() {
  return (
    <section
      role="status"
      aria-busy="true"
      aria-label="Carregando os executores"
      className="flex min-w-0 flex-col overflow-hidden rounded-lg border bg-card shadow-xs"
    >
      {/* Cabeçalho de colunas — some no telefone, onde a linha não tem colunas. */}
      <div className="hidden items-center gap-3 border-b border-border bg-muted/50 px-3 py-1.5 md:flex">
        <Skeleton className="h-3 w-4" />
        <Skeleton className="h-3 w-24" />
        <Skeleton className="ml-auto h-3 w-14" />
        <Skeleton className="h-3 w-16" />
      </div>
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex h-11 items-center gap-3 border-b border-border/60 px-3 last:border-b-0">
          <Skeleton className="size-2 shrink-0 rounded-full" />
          <Skeleton className="h-3.5 w-40" />
          <Skeleton className="ml-auto hidden h-3 w-16 md:block" />
          <Skeleton className="hidden h-3 w-20 md:block" />
        </div>
      ))}
    </section>
  )
}

/**
 * Espinha (a listagem) caiu na 1ª carga: sem ela não há trilho, então o bloco
 * de erro toma o lugar. Só aparece quando `data == null` — uma recarga que
 * falha sobre uma lista já pronta mantém o que havia (ver o `index`).
 */
export function ErroDosExecutores({ mensagem, onTentar }: { mensagem: string; onTentar: () => void }) {
  return <Estado.ErroDeCarga titulo="Não foi possível carregar os executores" mensagem={mensagem} onTentar={onTentar} />
}

/**
 * Vazio de primeiro uso (contrato §3.3): distingue "não há executor" de "não há
 * resultado". A mensagem muda conforme o papel — admin registra o primeiro;
 * usuário comum pede acesso. `acao` é o CTA primário (o diálogo de criação),
 * renderizado só quando quem vê pode criar.
 */
export function VazioDeExecutores({ isAdmin, acao }: { isAdmin: boolean; acao?: ReactNode }) {
  return (
    <Estado.VazioPrimeiroUso
      icone={TbServerOff}
      titulo={isAdmin ? "Nenhum executor ainda" : "Nenhum executor disponível para você"}
      descricao={isAdmin
        ? "Executores são as máquinas que rodam seus workflows de forma distribuída. Registre o primeiro para começar a despachar execuções."
        : "Os workflows precisam de um executor para rodar. Peça a um administrador acesso a um executor dedicado ou ao pool compartilhado."}
      acao={acao}
      podeCriar={isAdmin}
    />
  )
}

/**
 * Recorte ativo sem nenhuma linha (contrato §3.3): a saída óbvia é limpar o
 * filtro, e a tela diz isso — o ícone `TbFilterOff` separa do vazio de fato.
 */
export function SemResultado({ onLimpar }: { onLimpar: () => void }) {
  return <Estado.SemResultado texto="Nenhum executor com este filtro" onLimpar={onLimpar} />
}

/**
 * Falha parcial (contrato §3.4): só as métricas de execução caíram; o trilho
 * continua inteiro, sem os números de histórico. Uma linha âmbar discreta com
 * o "Tentar de novo" que refaz a carga das métricas.
 */
export function AvisoDeMetricas({ onTentar }: { onTentar: () => void }) {
  return (
    <Estado.AvisoAmbar onTentar={onTentar}>
      Sem dados de execução agora — a lista continua completa.
    </Estado.AvisoAmbar>
  )
}
