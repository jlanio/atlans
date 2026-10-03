// web/extensoes/nenhuma.ts
//
// No extensions: what `instaladas.ts` is in the free distribution (the
// `scripts/sem_extensoes.sh` rewrites it this way). `tsconfig.nucleo.json` and
// `vitest --mode nucleo` point `@/extensoes/instaladas` here, to check the core
// without deleting anything.

import type { ExtensaoDoWeb } from "./tipos"

export const INSTALADAS: ExtensaoDoWeb[] = []
