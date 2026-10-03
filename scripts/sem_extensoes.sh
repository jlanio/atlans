#!/usr/bin/env bash
# scripts/sem_extensoes.sh
# The extensions cut: leaves the tree as the free distribution will have it,
# without the code of any extension (app/extensoes/<nome>/ and
# web/extensoes/<nome>/) or their tests (tests/extensoes/ and
# web/__tests__/extensoes/), and with the web's list of installed extensions
# empty. The registry on each side (app/extensoes/__init__.py and the loose
# files in web/extensoes) stays: it is core.
#
# DESTRUCTIVE on purpose. Runs in the CI's throwaway checkout (the "sem
# extensões" (without extensions) jobs) and in the export of the public
# repository. To see the result on your machine, run it in a separate copy (a
# `git worktree add`, for example).

set -euo pipefail

cd "$(dirname "$0")/.."

# Each subfolder of app/extensoes is an extension (its __pycache__ goes with it).
find app/extensoes -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} +
rm -rf tests/extensoes

# Same on the web side; and the list of installed ones is left empty.
find web/extensoes -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} +
rm -rf web/__tests__/extensoes
cat > web/extensoes/instaladas.ts <<'TS'
// web/extensoes/instaladas.ts
//
// As extensões desta instalação: nenhuma. Para somar uma, ponha a pasta dela
// em web/extensoes/ e o objeto que ela exporta nesta lista (ver `tipos.ts`).

import type { ExtensaoDoWeb } from "./tipos"

export const INSTALADAS: ExtensaoDoWeb[] = []
TS

echo "sem_extensoes: a árvore agora é a da distribuição livre."
