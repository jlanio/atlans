"use client"

import { TbActivity, TbPlus } from "react-icons/tb"
import { Skeleton } from "@/app/components/ui/skeleton"
import * as Estado from "@/app/components/shared/estados"

/**
 * Estados da tela do Dashboard (docs/specs/dashboard.md §3.10): skeleton da 1ª
 * carga, erro de espinha, vazio de primeiro uso e o aviso âmbar de falha
 * parcial por seção. Cada um diz o que aconteceu e o que fazer a seguir; aqui
 * ficam o skeleton e as frases, com a moldura de `shared/estados.tsx`.
 */

/**
 * Primeira carga do escopo: o cabeçalho real fica por cima (o `index` o
 * renderiza sempre) e aqui vai o desenho dos blocos com a altura de verdade,
 * para a troca para o conteúdo não pular a página.
 */
export function SkeletonDoDashboard() {
  return (
    <div role="status" aria-busy="true" aria-label="Carregando o painel" className="flex flex-col gap-4 sm:gap-6">
      {/* Saúde: a linha fina do estado calmo. */}
      <Skeleton className="h-11 w-full rounded-lg" />
      {/* Atenção | Próximas. */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <Skeleton className="h-48 w-full rounded-lg" />
        <Skeleton className="h-48 w-full rounded-lg" />
      </div>
      {/* Resumo do período: 4 indicadores + gráfico. */}
      <div className="flex flex-col gap-3">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-24 w-full rounded-lg" />)}
        </div>
        <Skeleton className="h-56 w-full rounded-lg" />
      </div>
    </div>
  )
}

/**
 * Espinha (`metrics`) caiu na 1ª carga: sem ela não há saúde, atenção nem
 * indicadores, então o painel inteiro dá lugar ao bloco de erro. Numa recarga
 * com dados na tela o hook mantém o que havia e isto não aparece.
 */
export function ErroDoPainel({ mensagem, onTentar }: { mensagem: string; onTentar: () => void }) {
  return <Estado.ErroDeCarga titulo="Não foi possível carregar o painel" mensagem={mensagem} onTentar={onTentar} />
}

/**
 * Vazio de primeiro uso (§3.10): nada rodou e não há workflow no escopo. Só o
 * convite para criar o primeiro; os demais blocos não aparecem — não há o que
 * resumir nem rotear ainda.
 */
export function VazioDePrimeiroUso({ canEdit, onCriar }: { canEdit: boolean; onCriar: () => void }) {
  return (
    <Estado.VazioPrimeiroUso
      icone={TbActivity}
      titulo="Nada rodou ainda"
      descricao={
        <>
          Quando um workflow rodar — na mão, num horário, ou por um webhook ou arquivo — o
          painel passa a mostrar a saúde, o que precisa de você e como o período andou.
        </>
      }
      cta={{ rotulo: "Criar workflow", icone: TbPlus, onClick: onCriar }}
      podeCriar={canEdit}
      pedirA="criar o primeiro workflow"
    />
  )
}

/**
 * Falha parcial de uma seção (§3.10): a fonte daquele bloco caiu, mas o resto
 * do painel continua. A linha âmbar de `shared/estados.tsx`, com o "Tentar de
 * novo" que refaz a carga (o `index` liga ao `recarregar`).
 */
export { AvisoAmbar as AvisoDeSecao } from "@/app/components/shared/estados"
