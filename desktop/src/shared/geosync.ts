// desktop/src/shared/geosync.ts
//
// Constantes do GeoSync compartilhadas entre main e renderer.
//
// Moram em `shared/` e não em `main/state/config.ts` por um motivo concreto: o
// renderer roda no Chromium, sem `node:fs` nem `electron`. Importar um VALOR de
// um módulo do main arrasta essas dependências para o bundle da tela, e a
// página morre em branco no primeiro load — sem erro visível, porque a janela
// já pintou o fundo antes do React tentar montar. Tipos podem vir do main (são
// apagados na compilação); valores, não.

/**
 * `EXECUTOR_SYNC_INTERVAL` que o app grava a cada salvar do GeoSync — escolha
 * DESTE app, e não o padrão do executor (30 s, que só vale quando a linha falta
 * no `.env`). O `.env.example`, que semeia o `.env` no enrollment, traz o
 * mesmo 10. `limites.test.ts` confere que o executor aceita o valor.
 */
export const INTERVALO_SYNC = 10

/** Direções aceitas por `EXECUTOR_SYNC_MODE`. */
export const MODOS_SYNC = ['upload', 'download', 'bidirectional', 'catalog'] as const
export type ModoSync = (typeof MODOS_SYNC)[number]

/** Valores aceitos por `EXECUTOR_SYNC_CONFLICT_STRATEGY`. */
export const ESTRATEGIAS = ['local-wins', 'remote-wins', 'keep-both'] as const
export type EstrategiaConflito = (typeof ESTRATEGIAS)[number]

/**
 * O que o executor faz quando `EXECUTOR_SYNC_MODE` / `_CONFLICT_STRATEGY` faltam
 * no `.env` — os padrões de `executor/config.py` (`limites.test.ts` compara).
 *
 * A tela caía em `bidirectional` e mentia: o executor rodava `upload`, e salvar
 * qualquer ajuste do GeoSync gravava o `bidirectional` da tela, passando a
 * baixar do Drive sem ninguém ter escolhido. `upload` é também o padrão
 * seguro: nada que aconteça no Drive apaga ou sobrescreve arquivo local.
 */
export const PADRAO_SYNC = {
  modo: 'upload',
  conflito: 'remote-wins',
} as const satisfies { modo: ModoSync; conflito: EstrategiaConflito }
