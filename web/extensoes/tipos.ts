// web/extensoes/tipos.ts
//
// O que uma extensão do web pode pendurar na tela. É o par do registro do
// servidor (`app/extensoes/__init__.py`): o núcleo nunca importa uma extensão
// pelo nome, e cada ponto de encaixe abaixo tem um padrão para quando não há
// extensão nenhuma — a distribuição livre.

import type { ComponentType, ReactNode } from "react"
import type { IPainelDoModelo } from "@/service/types"

/** As props do envoltório do painel do modelo do assistente (admin). */
export interface PropsDoEnvoltorioDoPainel {
  /** O painel como o servidor mandou, com os campos que a extensão soma. */
  painel: IPainelDoModelo
  /** O modelo escolhido na lista, ainda não salvo (o que se simula). */
  escolhido: string
  /** Uma gravação em curso, no núcleo ou na extensão: os botões esperam juntos. */
  ocupado: boolean
  aoOcupar: (ocupado: boolean) => void
  /** Depois de salvar algo, recarrega o painel. */
  aoTrocar: () => void
  /** O seletor do modelo, do núcleo: o envoltório decide onde ele fica. */
  children: ReactNode
}

export interface ExtensaoDoWeb {
  nome: string
  /** Montados uma vez na casca do app (`SidebarRoot`), nas duas cascas: modais
   *  e efeitos globais. */
  camadas?: ComponentType[]
  /** Itens a mais no menu da conta. Cada um desenha o próprio item do menu. */
  itensDaConta?: ComponentType<{ portalClassName?: string }>[]
  /** O que oferecer quando a cota do assistente estoura (ao lado do aviso). */
  ofertaDaCota?: ComponentType<{ plano: string | null | undefined; assinaturasAtivas: boolean | undefined }>
  /** O painel de admin do modelo do assistente. */
  painelDoModelo?: {
    /** Envolve o seletor do modelo com o que a extensão soma à tela. */
    Envoltorio: ComponentType<PropsDoEnvoltorioDoPainel>
    /** Uma frase a mais na apresentação da seção. */
    apoio?: string
  }
}
