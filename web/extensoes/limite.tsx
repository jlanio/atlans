"use client"

// web/extensoes/limite.tsx
//
// An extension that fails does not take down the core. Every piece an extension
// hangs on the screen passes through here: if it breaks while rendering (a bug
// of its own, or the lazily loaded chunk that never arrived — a deploy midway,
// a dropped network), the spot shows the `reserva`, which is what the core
// would show with no extension at all. Without this, the error would bubble up
// to the root and React would unmount the whole app — including the "Voltar ao
// padrão do ambiente" (back to the environment default) of the model panel,
// which exists precisely for when something goes wrong.
//
// The error does not vanish: it goes to the console, with the extension's name.

import { Component, type ErrorInfo, type ReactNode } from "react"

interface Props {
  /** The extension's name, for logging the error. */
  nome: string
  /** What stays in place if the extension fails. Default: nothing. */
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
