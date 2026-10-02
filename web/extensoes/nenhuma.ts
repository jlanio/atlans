// web/extensoes/nenhuma.ts
//
// Nenhuma extensão: o que `instaladas.ts` é na distribuição livre (o
// `scripts/sem_extensoes.sh` o reescreve assim). O `tsconfig.nucleo.json` e o
// `vitest --mode nucleo` apontam `@/extensoes/instaladas` para cá, para
// conferir o núcleo sem apagar nada.

import type { ExtensaoDoWeb } from "./tipos"

export const INSTALADAS: ExtensaoDoWeb[] = []
