// desktop/src/main/python/ndjson.ts
//
// Leitor tolerante do stdout do executor.
//
// Duas armadilhas classicas, ambas tratadas aqui:
//
// 1. O evento `data` de um stream NAO respeita fronteira de linha. Uma linha
//    chega partida em dois chunks, ou dois eventos chegam num chunk so. Sem o
//    buffer acumulador, um JSON.parse de metade de uma linha derruba o parser
//    justamente sob carga, que e quando as linhas ficam grandes.
//
// 2. O executor executa codigo de terceiros (nos de workflow, incluindo
//    PythonScript). Um `print()` ali cai no MESMO stdout. Por isso o framing:
//    toda linha valida comeca por `{"v":1,`, e o que nao casa nao e evento —
//    vai para o log como texto bruto, em vez de virar erro de parse.
import { FRAMING, type ExecutorEvent } from '../../shared/events.js'

/** Teto de uma linha. Espelha _LINHA_MAX de json_runtime.py, com folga. */
const LINHA_MAX = 1024 * 1024

export interface NdjsonHandlers {
  /** Linha valida, ja parseada. */
  onEvent: (evt: ExecutorEvent) => void
  /**
   * Linha que nao e evento: `print()` de um no, aviso de biblioteca nativa
   * escrito direto no fd 1, lixo. Nunca e erro — e informacao para o painel de
   * log.
   */
  onRaw: (linha: string) => void
}

export class NdjsonParser {
  private buffer = ''

  constructor(private readonly handlers: NdjsonHandlers) {}

  /** Consome um chunk do stream. Nunca lanca. */
  push(chunk: string): void {
    // Um `split` unico por chunk, e nao um `slice` por linha: o laco anterior
    // reatribuia `buffer = buffer.slice(corte + 1)` a cada linha, e como um
    // chunk de stream chega com dezenas de KB e centenas de linhas, o custo era
    // a soma de N copias do resto — quadratico, no thread que atende tray,
    // janelas e IPC. Um chunk de 64 KB com 300 linhas copiava ~10 MB de string.
    const partes = (this.buffer + chunk).split('\n')
    // O ultimo pedaco e o que veio DEPOIS do ultimo `\n`: linha incompleta, que
    // volta ao buffer para o proximo chunk fechar.
    this.buffer = partes.pop() ?? ''

    for (const linha of partes) this.consumirLinha(linha)

    // Uma linha unica maior que o teto so pode ter vindo de saida binaria ou de
    // um no descontrolado. Descartar o buffer e melhor que crescer sem limite
    // ate o processo do app morrer por memoria. O resto retido acima e o UNICO
    // ponto onde uma linha sem `\n` pode crescer, entao a guarda vive aqui.
    if (this.buffer.length > LINHA_MAX) {
      this.handlers.onRaw(
        `[linha descartada: ${this.buffer.length} bytes sem quebra de linha]`,
      )
      this.buffer = ''
    }
  }

  /**
   * Processa o que sobrou sem `\n`. Chamar quando o stream fecha: a ultima
   * linha antes de um crash costuma ser a mais interessante, e ela nao tem
   * quebra de linha no fim.
   */
  flush(): void {
    const resto = this.buffer
    this.buffer = ''
    if (resto.trim()) this.consumirLinha(resto)
  }

  private consumirLinha(bruta: string): void {
    // \r sobra quando o Python escreve em modo texto no Windows.
    const linha = bruta.replace(/\r$/, '')
    if (!linha.trim()) return

    if (!linha.startsWith(FRAMING)) {
      this.handlers.onRaw(linha)
      return
    }
    let evt: ExecutorEvent
    try {
      evt = JSON.parse(linha) as ExecutorEvent
    } catch {
      // Comecava com o framing mas nao era JSON valido — linha truncada por um
      // crash no meio da escrita. Vale mais como texto que como nada.
      this.handlers.onRaw(linha)
      return
    }
    if (typeof (evt as { t?: unknown }).t !== 'string') {
      this.handlers.onRaw(linha)
      return
    }
    this.handlers.onEvent(evt)
  }
}

/**
 * Divide o stderr em linhas. O log humano vem formatado de la e nao precisa de
 * parse — so de nao ser cortado no meio, pelo mesmo motivo do item 1 acima.
 */
export class LineSplitter {
  private buffer = ''

  constructor(private readonly onLine: (linha: string) => void) {}

  push(chunk: string): void {
    // Mesmo motivo do parser acima — e este e o caminho MAIS quente dos dois,
    // porque carrega o log humano inteiro do executor.
    const partes = (this.buffer + chunk).split('\n')
    this.buffer = partes.pop() ?? ''

    for (const parte of partes) {
      const linha = parte.replace(/\r$/, '')
      if (linha.trim()) this.onLine(linha)
    }
    if (this.buffer.length > LINHA_MAX) this.buffer = ''
  }

  flush(): void {
    const resto = this.buffer.replace(/\r$/, '')
    this.buffer = ''
    if (resto.trim()) this.onLine(resto)
  }
}
