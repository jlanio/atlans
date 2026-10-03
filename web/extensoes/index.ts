// web/extensoes/index.ts
//
// The web's extensions: what an installation has beyond the core. The core
// reads from here, and only from here; the list of extensions present is in
// `instaladas.ts` (in the free distribution, the empty list from `nenhuma.ts`).
// See `tipos.ts`.

import { INSTALADAS } from "@/extensoes/instaladas"
import type { ExtensaoDoWeb, PropsDoEnvoltorioDoPainel } from "./tipos"

export type { ExtensaoDoWeb, PropsDoEnvoltorioDoPainel }
/** What every extension piece on the screen passes through: if it fails, it drops out on its own. */
export { LimiteDaExtensao } from "./limite"

export const EXTENSOES: readonly ExtensaoDoWeb[] = INSTALADAS
