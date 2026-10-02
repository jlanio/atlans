"use client"

import { TbKey, TbPlus } from "react-icons/tb"
import { Skeleton } from "@/app/components/ui/skeleton"
import * as Estado from "@/app/components/shared/estados"

/**
 * Estados da tela de Tokens de acesso (contrato padrao-telas.md §3):
 * carregando, erro de carga e primeiro uso. Não há busca nem filtro aqui, então
 * não existe o «sem resultado». Aqui ficam o skeleton e as frases da tela; a
 * moldura de cada estado é a de `shared/estados.tsx`.
 */

/**
 * Primeira carga: o cabeçalho real fica por cima (o `index` sempre o renderiza,
 * com o subtítulo em esqueleto), e aqui vai o desenho das linhas — com a altura
 * do cartão de verdade (nome, prefixo e a linha de escopos), para a troca não
 * pular.
 */
export function SkeletonDeTokens() {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label="Carregando os tokens de acesso"
      className="flex flex-col gap-3"
    >
      {[0, 1, 2].map(i => <LinhaFantasma key={i} />)}
    </div>
  )
}

/**
 * Mais alta no telefone: ali o EntityCard empilha o botão «Revogar» numa
 * segunda linha, e um esqueleto baixo encolhia a lista quando os dados chegavam.
 */
function LinhaFantasma() {
  return (
    <div className="flex h-[132px] items-center gap-3 rounded-lg border bg-card px-3 shadow-xs sm:h-[92px]">
      <Skeleton className="size-8 shrink-0 rounded-md" />
      <div className="flex flex-1 flex-col gap-1.5">
        <div className="flex items-center gap-2">
          <Skeleton className="h-3.5 w-1/3" />
          <Skeleton className="h-4 w-14 rounded-full" />
        </div>
        <Skeleton className="h-3 w-24" />
        <div className="flex items-center gap-1.5">
          <Skeleton className="h-4 w-20 rounded-full" />
          <Skeleton className="h-4 w-28 rounded-full" />
          <Skeleton className="hidden h-3 w-40 sm:block" />
        </div>
      </div>
      <Skeleton className="hidden h-8 w-20 rounded-md sm:block" />
    </div>
  )
}

/**
 * A listagem caiu na 1ª carga. Só toma a tela quando nunca houve carga aceita —
 * recarga que falha sobre lista pronta mantém o que havia e avisa por toast
 * (ver `index`). `mensagem` é a do servidor; sem ela, a orientação de sempre.
 */
export function ErroDeCarga({ mensagem, onTentar }: { mensagem?: string | null; onTentar: () => void }) {
  return (
    <Estado.ErroDeCarga
      titulo="Não foi possível carregar os tokens de acesso."
      mensagem={mensagem || "Verifique a conexão e tente novamente."}
      onTentar={onTentar}
    />
  )
}

/**
 * Sem nenhum token: a tela ensina o que é um token e que ele herda as
 * permissões da conta. Criar é uma ação pessoal — todo mundo pode, então o CTA
 * é incondicional (não há «peça a um editor» aqui).
 */
export function VazioPrimeiroUso({ onCriar }: { onCriar: () => void }) {
  return (
    <Estado.VazioPrimeiroUso
      icone={TbKey}
      titulo="Crie o primeiro token de acesso"
      descricao={
        <>
          Um token deixa um agente de IA ou uma integração usar o Atlans em seu nome — pela API ou
          pelo servidor MCP. Ele herda as permissões da sua conta e nunca vai além delas: você
          escolhe o que ele pode fazer, em quais workspaces e por quanto tempo.
        </>
      }
      cta={{ rotulo: "Criar o primeiro token", icone: TbPlus, onClick: onCriar }}
    />
  )
}
