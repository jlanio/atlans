// desktop/src/renderer/lib/useLog.test.ts
//
// A costura dos lotes de log. Testada como função pura porque a primeira versão
// vivia dentro do updater do `setState` e escondia três defeitos:
//
//   1. o updater roda DEPOIS do handler, e a comparação de `seq` lia um ref já
//      avançado — nenhum lote incremental entrava, e o log congelava logo após
//      montar. Um bug que só aparece em uso, e como "o log parou de atualizar";
//   2. havia um `window.atlas.log()` dentro do updater — efeito colateral numa
//      função que o React pode chamar duas vezes;
//   3. o carregamento inicial substituía o buffer e descartava as linhas que
//      chegassem no intervalo entre o main montar a resposta e ela chegar aqui.
//
// Os três são invisíveis em leitura casual e voltariam na primeira
// "simplificação".
import { describe, expect, it } from 'vitest'
import {
  LOG_VAZIO, MAX_LOG, mesclarLog, type EstadoLog, type LinhaVisivel,
} from './useLog.js'
import type { LinhaLog, LoteLog } from '../../main/state/store.js'

function linha(seq: number): LinhaLog {
  return { seq, ts: seq, level: 'INFO', alias: 'X', msg: `l${seq}` }
}

/**
 * Linha já no buffer local — com o texto de busca que `mesclarLog` acrescenta.
 *
 * O que chega pelo IPC é `LinhaLog`; o que fica guardado aqui é `LinhaVisivel`,
 * com `msg`+`alias` em minúsculas para o filtro do painel não refazer isso a
 * cada tecla.
 */
function guardada(seq: number): LinhaVisivel {
  const l = linha(seq)
  return { ...l, busca: `${l.alias}\n${l.msg}`.toLowerCase() }
}

function lote(seqs: number[], primeiroSeq = seqs[0] ?? 1): LoteLog {
  return { linhas: seqs.map(linha), primeiroSeq }
}

const seqs = (e: EstadoLog) => e.linhas.map((l) => l.seq)

describe('carregamento completo', () => {
  it('monta o buffer a partir do zero', () => {
    const { estado } = mesclarLog(LOG_VAZIO, lote([1, 2, 3]), 'completo')
    expect(seqs(estado)).toEqual([1, 2, 3])
    expect(estado.ultimoSeq).toBe(3)
  })

  it('PRESERVA as linhas que chegaram enquanto o snapshot vinha', () => {
    // Defeito 3. O push entrega 10 e 11 antes de a resposta de `atlas.log()`
    // (tirada em 9) chegar. Substituir sem mais perderia as duas para sempre,
    // porque `ultimoSeq` já passou delas e nenhum lote futuro as reenvia.
    const comPush = mesclarLog(LOG_VAZIO, lote([10, 11], 10), 'incremental').estado
    const { estado } = mesclarLog(comPush, lote([8, 9]), 'completo')

    expect(seqs(estado)).toEqual([8, 9, 10, 11])
    expect(estado.ultimoSeq).toBe(11)
  })

  it('não deixa o ultimoSeq andar para trás', () => {
    const adiantado: EstadoLog = { linhas: [guardada(50)], ultimoSeq: 50 }
    expect(mesclarLog(adiantado, lote([1, 2]), 'completo').estado.ultimoSeq).toBe(50)
  })
})

describe('lotes incrementais', () => {
  it('emenda as linhas novas', () => {
    // O caso que o defeito 1 quebrava: em uso, o log parava de atualizar.
    let e = mesclarLog(LOG_VAZIO, lote([1, 2]), 'completo').estado
    e = mesclarLog(e, lote([3, 4], 1), 'incremental').estado
    e = mesclarLog(e, lote([5], 1), 'incremental').estado

    expect(seqs(e)).toEqual([1, 2, 3, 4, 5])
    expect(e.ultimoSeq).toBe(5)
  })

  it('ignora linhas repetidas depois de um recarregamento', () => {
    const e = mesclarLog(LOG_VAZIO, lote([1, 2, 3]), 'completo').estado
    const r = mesclarLog(e, lote([2, 3, 4], 1), 'incremental')

    expect(seqs(r.estado)).toEqual([1, 2, 3, 4])
  })

  it('lote inteiramente repetido devolve o MESMO objeto', () => {
    // É o que permite ao hook não re-renderizar à toa.
    const e = mesclarLog(LOG_VAZIO, lote([1, 2, 3]), 'completo').estado
    expect(mesclarLog(e, lote([1, 2, 3], 1), 'incremental').estado).toBe(e)
  })

  it('lote vazio não mexe em nada', () => {
    const e = mesclarLog(LOG_VAZIO, lote([1]), 'completo').estado
    const r = mesclarLog(e, { linhas: [], primeiroSeq: 1 }, 'incremental')
    expect(r.estado).toBe(e)
    expect(r.recarregar).toBe(false)
  })
})

describe('buraco no meio', () => {
  it('pede recarga quando o main já descartou o que faltava', () => {
    // Estávamos em 5; o lote diz que a linha mais antiga que o main ainda tem é
    // a 900. As linhas 6..899 não existem mais em lugar nenhum, e emendar
    // produziria um log com um salto invisível.
    const e: EstadoLog = { linhas: [guardada(5)], ultimoSeq: 5 }
    const r = mesclarLog(e, lote([1000], 900), 'incremental')

    expect(r.recarregar).toBe(true)
    expect(r.estado).toBe(e)   // não mexe no buffer enquanto a recarga não vem
  })

  it('buffer cheio no main, mas SEM buraco, não pede recarga', () => {
    // O caso normal com o log lotado: o main já aparou o início (primeiroSeq
    // alto), mas nós estamos em dia. Confundir os dois faria o app recarregar o
    // log inteiro a cada lote — exatamente o custo que este desenho eliminou.
    const e: EstadoLog = { linhas: [guardada(1200)], ultimoSeq: 1200 }
    expect(mesclarLog(e, lote([1201], 201), 'incremental').recarregar).toBe(false)
  })

  it('buffer local vazio nunca pede recarga', () => {
    // Sem nada aplicado ainda, não há como haver buraco — e pedir recarga aqui
    // criaria um laço com o carregamento inicial.
    expect(mesclarLog(LOG_VAZIO, lote([500], 500), 'incremental').recarregar).toBe(false)
  })
})

describe('teto do buffer', () => {
  it('apara pelo início e mantém as mais novas', () => {
    const todas = Array.from({ length: MAX_LOG + 50 }, (_, i) => i + 1)
    const { estado } = mesclarLog(LOG_VAZIO, lote(todas), 'completo')

    expect(estado.linhas).toHaveLength(MAX_LOG)
    expect(estado.linhas[0]!.seq).toBe(51)
    expect(estado.ultimoSeq).toBe(MAX_LOG + 50)
  })

  it('vale também para a emenda incremental', () => {
    const e = mesclarLog(
      LOG_VAZIO, lote(Array.from({ length: MAX_LOG }, (_, i) => i + 1)), 'completo',
    ).estado
    const r = mesclarLog(e, lote([MAX_LOG + 1], 1), 'incremental')

    expect(r.estado.linhas).toHaveLength(MAX_LOG)
    expect(r.estado.linhas.at(-1)!.seq).toBe(MAX_LOG + 1)
  })
})
