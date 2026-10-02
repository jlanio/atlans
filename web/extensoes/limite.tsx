"use client"

// web/extensoes/limite.tsx
//
// Uma extensão que falha não derruba o núcleo. Cada peça que uma extensão
// pendura na tela passa por aqui: se ela quebrar ao desenhar (um defeito dela,
// ou o pedaço carregado sob demanda que não chegou — deploy no meio, rede que
// caiu), o lugar mostra a `reserva`, que é o que o núcleo mostraria sem
// extensão nenhuma. Sem isto, o erro subiria até a raiz e o React desmontaria o
// app inteiro — inclusive o «Voltar ao padrão do ambiente» do painel do
// modelo, que existe justamente para quando algo dá errado.
//
// O erro não some: vai para o console, com o nome da extensão.

import { Component, type ErrorInfo, type ReactNode } from "react"

interface Props {
  /** O nome da extensão, para o registro do erro. */
  nome: string
  /** O que fica no lugar se a extensão falhar. Padrão: nada. */
  reserva?: ReactNode
  children: ReactNode
}

export class LimiteDaExtensao extends Component<Props, { falhou: boolean }> {
  state = { falhou: false }

  static getDerivedStateFromError() {
    return { falhou: true }
  }

  componentDidCatch(erro: Error, info: ErrorInfo) {
    console.error(`A extensão «${this.props.nome}» falhou e saiu da tela.`, erro, info.componentStack)
  }

  render() {
    return this.state.falhou ? (this.props.reserva ?? null) : this.props.children
  }
}
