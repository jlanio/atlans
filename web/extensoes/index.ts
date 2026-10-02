// web/extensoes/index.ts
//
// As extensões do web: o que uma instalação tem além do núcleo. O núcleo lê
// daqui, e só daqui; quem lista as extensões presentes é `instaladas.ts` (na
// distribuição livre, a lista vazia de `nenhuma.ts`). Ver `tipos.ts`.

import { INSTALADAS } from "@/extensoes/instaladas"
import type { ExtensaoDoWeb, PropsDoEnvoltorioDoPainel } from "./tipos"

export type { ExtensaoDoWeb, PropsDoEnvoltorioDoPainel }
/** Por onde passa cada peça de extensão na tela: se ela falhar, sai sozinha. */
export { LimiteDaExtensao } from "./limite"

export const EXTENSOES: readonly ExtensaoDoWeb[] = INSTALADAS
