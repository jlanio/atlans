// desktop/src/main/python/ndjson.ts
//
// Tolerant reader of the executor's stdout.
//
// Two classic pitfalls, both handled here:
//
// 1. A stream's `data` event does NOT respect line boundaries. One line
//    arrives split across two chunks, or two events arrive in a single chunk.
//    Without the accumulating buffer, a JSON.parse of half a line brings the
//    parser down precisely under load, which is when lines get large.
//
// 2. The executor runs third-party code (workflow nodes, including
//    PythonScript). A `print()` there lands on the SAME stdout. Hence the
//    framing: every valid line starts with `{"v":1,`, and whatever does not
//    match is not an event — it goes to the log as raw text instead of
//    becoming a parse error.
import { FRAMING, type ExecutorEvent } from '../../shared/events.js'

/** Ceiling for one line. Mirrors _LINHA_MAX in json_runtime.py, with headroom. */
const LINHA_MAX = 1024 * 1024

export interface NdjsonHandlers {
  /** Valid line, already parsed. */
  onEvent: (evt: ExecutorEvent) => void
  /**
   * Line that is not an event: a node's `print()`, a native-library warning
   * written straight to fd 1, garbage. It is never an error — it is
   * information for the log panel.
   */
  onRaw: (linha: string) => void
}

export class NdjsonParser {
  private buffer = ''

  constructor(private readonly handlers: NdjsonHandlers) {}

  /** Consumes a chunk of the stream. Never throws. */
  push(chunk: string): void {
    // A single `split` per chunk, not one `slice` per line: the previous loop
    // reassigned `buffer = buffer.slice(corte + 1)` on every line, and since a
    // stream chunk arrives with tens of KB and hundreds of lines, the cost was
    // the sum of N copies of the remainder — quadratic, on the thread that
    // serves the tray, windows and IPC. A 64 KB chunk with 300 lines copied
    // ~10 MB of string.
    const partes = (this.buffer + chunk).split('\n')
    // The last piece is what came AFTER the last `\n`: an incomplete line, which
    // goes back to the buffer for the next chunk to complete.
    this.buffer = partes.pop() ?? ''

    for (const linha of partes) this.consumirLinha(linha)

    // A single line larger than the ceiling can only have come from binary output
    // or a runaway node. Discarding the buffer is better than growing without
    // bound until the app process dies of memory. The remainder retained above
    // is the ONLY place where a line without `\n` can grow, so the guard lives
    // here.
    if (this.buffer.length > LINHA_MAX) {
      this.handlers.onRaw(
        `[linha descartada: ${this.buffer.length} bytes sem quebra de linha]`,
      )
      this.buffer = ''
    }
  }

  /**
   * Processes what is left without `\n`. Call it when the stream closes: the
   * last line before a crash is usually the most interesting one, and it has
   * no trailing newline.
   */
  flush(): void {
    const resto = this.buffer
    this.buffer = ''
    if (resto.trim()) this.consumirLinha(resto)
  }

  private consumirLinha(bruta: string): void {
    // \r is left over when Python writes in text mode on Windows.
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
      // It started with the framing but was not valid JSON — a line truncated by a
      // crash mid-write. It is worth more as text than as nothing.
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
 * Splits stderr into lines. The human log comes formatted from there and needs
 * no parsing — only not to be cut in the middle, for the same reason as item 1
 * above.
 */
export class LineSplitter {
  private buffer = ''

  constructor(private readonly onLine: (linha: string) => void) {}

  push(chunk: string): void {
    // Same reason as the parser above — and this is the HOTTER path of the two,
    // because it carries the executor's entire human log.
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
