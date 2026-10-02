#!/usr/bin/env bash
# scripts/sem_extensoes.sh
# O corte das extensões: deixa a árvore como a distribuição livre a terá, sem o
# código de nenhuma extensão (app/extensoes/<nome>/ e web/extensoes/<nome>/) nem
# os testes delas (tests/extensoes/ e web/__tests__/extensoes/), e com a lista
# das extensões instaladas do web vazia. O registro de cada lado
# (app/extensoes/__init__.py e os arquivos soltos de web/extensoes) fica: é
# núcleo.
#
# DESTRUTIVO de propósito. Roda no checkout descartável do CI (os jobs «sem
# extensões») e na exportação do repositório público. Para ver o resultado na
# sua máquina, rode numa cópia à parte (um `git worktree add`, por exemplo).

set -euo pipefail

cd "$(dirname "$0")/.."

# Cada subpasta de app/extensoes é uma extensão (o __pycache__ vai junto).
find app/extensoes -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} +
rm -rf tests/extensoes

# No web, idem; e a lista das instaladas fica vazia.
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
