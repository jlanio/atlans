// web/extensoes/tipos.ts
//
// What a web extension can hang on the screen. It is the counterpart of the
// server's registry (`app/extensoes/__init__.py`): the core never imports an
// extension by name, and each plug-in point below has a default for when there
// is no extension at all — the free distribution.

import type { ComponentType, ReactNode } from "react"
import type { IPainelDoModelo } from "@/service/types"

/** The props of the wrapper of the assistant's model panel (admin). */
export interface PropsDoEnvoltorioDoPainel {
  /** The panel as the server sent it, with the fields the extension adds. */
  painel: IPainelDoModelo
  /** The model chosen in the list, not yet saved (what is being simulated). */
  escolhido: string
  /** A save in progress, in the core or in the extension: the buttons wait together. */
  ocupado: boolean
  aoOcupar: (ocupado: boolean) => void
  /** After saving something, reloads the panel. */
  aoTrocar: () => void
  /** The core's model selector: the wrapper decides where it goes. */
  children: ReactNode
}

export interface ExtensaoDoWeb {
  nome: string
  /** Mounted once in the app shell (`SidebarRoot`), in both shells: modals
   *  and global effects. */
  camadas?: ComponentType[]
  /** Extra items in the account menu. Each one renders its own menu item. */
  itensDaConta?: ComponentType<{ portalClassName?: string }>[]
  /** What to offer when the assistant's quota runs out (next to the notice). */
  ofertaDaCota?: ComponentType<{ plano: string | null | undefined; assinaturasAtivas: boolean | undefined }>
  /** The admin panel for the assistant's model. */
  painelDoModelo?: {
    /** Wraps the model selector with what the extension adds to the screen. */
    Envoltorio: ComponentType<PropsDoEnvoltorioDoPainel>
    /** One more sentence in the section's introduction. */
    apoio?: string
  }
}
