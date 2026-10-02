// desktop/src/renderer/lib/useLog.ts
//
// Buffer de log do renderer, alimentado pelo canal incremental.
//
// O log não vem dentro do estado: ele é append-only e grande, e mandá-lo
// inteiro a cada mudança custava ~150-200 KB de structured clone por janela,
// por broadcast — e havia um broadcast POR LINHA. Ver o cabeçalho de
// `main/state/store.ts`.
//
// A costura dos lotes mora em `mesclarLog`, que é PURA e testada. A primeira
// versão fazia isso dentro do updater do `setState` e tinha três defeitos que
// não aparecem em leitura casual:
//
//   1. o updater do `setState` roda DEPOIS do handler, e a comparação de `seq`
//      lia um ref que já havia sido avançado — nenhum lote incremental era
//      aplicado, e o log congelava logo após montar;
//   2. o updater disparava um `window.atlas.log()` — efeito colateral dentro de
//      função que o React pode chamar duas vezes;
//   3. o carregamento inicial SUBSTITUÍA o buffer, descartando as linhas que
//      chegassem entre o snapshot ser tirado no main e a promessa resolver aqui
//      — justo no boot, que é quando mais linha chega.
import { useEffect, useRef, useState } from 'react'
import type { LinhaLog, LoteLog } from '../../main/state/store.js'

/** Mesmo teto do main. Divergir só faria as duas pontas discordarem. */
export const MAX_LOG = 1000

/**
 * Linha com o texto de busca já em minúsculas.
 *
 * O filtro do painel chamava `msg.toLowerCase()` e `alias.toLowerCase()` para
 * cada uma das 1000 linhas A CADA TECLA digitada — duas mil alocações de string
 * por letra, e o atraso aparecia entre a tecla e a letra na tela. Aqui o custo é
 * pago UMA vez por linha, quando ela entra.
 *
 * Fica no renderer, e não em `LinhaLog` no main: o campo dobraria o tamanho de
 * cada lote de log no IPC, que é justamente o que este canal foi desenhado para
 * enxugar.
 */
export interface LinhaVisivel extends LinhaLog {
  /**
   * `alias` e `msg` em minúsculas, separados por uma quebra de linha.
   *
   * O separador não é enfeite: o campo de busca tem uma linha só, então nenhum
   * termo digitado casa atravessando os dois — o resultado é idêntico ao
   * `msg.includes(t) || alias.includes(t)` que havia antes.
   */
  busca: string
}

function comBusca(l: LinhaLog): LinhaVisivel {
  return { ...l, busca: (l.alias + '\n' + l.msg).toLowerCase() }
}

export interface EstadoLog {
  linhas: LinhaVisivel[]
  /** `seq` da última linha já incorporada. */
  ultimoSeq: number
}

export const LOG_VAZIO: EstadoLog = { linhas: [], ultimoSeq: 0 }

/**
 * Incorpora um lote ao buffer local.
 *
 * `modo: 'completo'` é a resposta de `atlas.log()` — o buffer inteiro do main.
 * `modo: 'incremental'` é um lote do canal push.
 *
 * Devolve `recarregar: true` quando o main já descartou linhas que este buffer
 * nunca viu; emendar nesse caso produziria um log com um salto invisível no
 * meio, o que é pior que recarregar.
 *
 * Devolve o MESMO objeto de estado quando nada muda — o chamador usa isso para
 * não renderizar à toa.
 */
export function mesclarLog(
  atual: EstadoLog,
  lote: LoteLog,
  modo: 'completo' | 'incremental',
): { estado: EstadoLog; recarregar: boolean } {
  if (lote.linhas.length === 0) return { estado: atual, recarregar: false }

  const ultimoDoLote = lote.linhas[lote.linhas.length - 1]!.seq

  if (modo === 'completo') {
    // As linhas que já temos e são MAIS NOVAS que o snapshot sobrevivem: elas
    // chegaram pelo push depois de o main montar a resposta, e substituir sem
    // mais as perderia para sempre (o `ultimoSeq` já teria passado delas).
    const posteriores = atual.linhas.filter((l) => l.seq > ultimoDoLote)
    const linhas = lote.linhas.map(comBusca).concat(posteriores)
    return {
      estado: {
        linhas: linhas.length > MAX_LOG ? linhas.slice(-MAX_LOG) : linhas,
        ultimoSeq: Math.max(atual.ultimoSeq, ultimoDoLote),
      },
      recarregar: false,
    }
  }

  // `primeiroSeq` é a linha mais antiga que o main ainda guarda. Se ela já é
  // posterior à próxima que esperávamos, o que faltou foi descartado lá.
  if (atual.ultimoSeq > 0 && lote.primeiroSeq > atual.ultimoSeq + 1) {
    return { estado: atual, recarregar: true }
  }

  // Um lote pode repetir linhas depois de um recarregamento.
  const novas = lote.linhas.filter((l) => l.seq > atual.ultimoSeq)
  if (novas.length === 0) return { estado: atual, recarregar: false }

  const linhas = atual.linhas.concat(novas.map(comBusca))
  return {
    estado: {
      linhas: linhas.length > MAX_LOG ? linhas.slice(-MAX_LOG) : linhas,
      ultimoSeq: Math.max(atual.ultimoSeq, ultimoDoLote),
    },
    recarregar: false,
  }
}

export function useLog(): LinhaVisivel[] {
  const [linhas, setLinhas] = useState<LinhaVisivel[]>(LOG_VAZIO.linhas)
  // A fonte da verdade é o ref, atualizado de forma SÍNCRONA. O state é só o
  // espelho para renderizar — foi misturar os dois que produziu o defeito 1.
  const estadoRef = useRef<EstadoLog>(LOG_VAZIO)

  useEffect(() => {
    let vivo = true

    const aplicar = (lote: LoteLog, modo: 'completo' | 'incremental') => {
      if (!vivo) return
      const { estado, recarregar } = mesclarLog(estadoRef.current, lote, modo)

      if (recarregar) {
        void window.atlas.log().then((l) => aplicar(l, 'completo'))
        return
      }
      if (estado === estadoRef.current) return   // nada novo: não re-renderiza

      estadoRef.current = estado
      setLinhas(estado.linhas)
    }

    // A assinatura vem ANTES do invoke: um lote que chegue enquanto a promessa
    // está no ar é aplicado, e `mesclarLog` no modo completo o preserva.
    const cancelar = window.atlas.aoReceberLog((l) => aplicar(l, 'incremental'))
    void window.atlas.log().then((l) => aplicar(l, 'completo'))

    return () => { vivo = false; cancelar() }
  }, [])

  return linhas
}
