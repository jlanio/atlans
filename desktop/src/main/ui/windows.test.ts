// desktop/src/main/ui/windows.test.ts
//
// Regression of "Abrir painel" (open panel) "does nothing".
//
// The red button in the title bar HIDES the window instead of quitting the app
// — it lives in the tray, and closing it in the middle of a job would be
// destructive. After that, the tray menu called `focus()` on a hidden window,
// and `focus()` does not make anything visible: the menu item looked dead,
// with no error anywhere.
//
// The bug is ONE missing line, and that is exactly why it comes back if
// nobody locks it down.
import { describe, expect, it, vi } from 'vitest'

vi.mock('electron', () => ({ BrowserWindow: vi.fn(), shell: {} }))
vi.mock('../paths.js', () => ({
  IS_DEV: false,
  ICONE_APP: 'build/icon.ico',
  arquivoDoApp: (...p: string[]) => p.join('/'),
}))

const { trazerParaFrente } = await import('./windows.js')

function janela(estado: { minimizada?: boolean; visivel?: boolean }) {
  return {
    isMinimized: vi.fn(() => estado.minimizada ?? false),
    isVisible: vi.fn(() => estado.visivel ?? true),
    restore: vi.fn(),
    show: vi.fn(),
    focus: vi.fn(),
  }
}

describe('trazerParaFrente', () => {
  it('janela ESCONDIDA é mostrada — o caso do botão vermelho', () => {
    const w = janela({ visivel: false })
    trazerParaFrente(w)

    expect(w.show).toHaveBeenCalledOnce()
    expect(w.focus).toHaveBeenCalledOnce()
  })

  it('janela minimizada é restaurada', () => {
    const w = janela({ minimizada: true })
    trazerParaFrente(w)

    expect(w.restore).toHaveBeenCalledOnce()
    expect(w.focus).toHaveBeenCalledOnce()
  })

  it('minimizada E escondida: restaura e mostra', () => {
    // Happens when minimizing and then closing via the tray, or when restoring a
    // Windows session.
    const w = janela({ minimizada: true, visivel: false })
    trazerParaFrente(w)

    expect(w.restore).toHaveBeenCalledOnce()
    expect(w.show).toHaveBeenCalledOnce()
    expect(w.focus).toHaveBeenCalledOnce()
  })

  it('janela já visível só recebe foco', () => {
    // `show()` on a visible window is harmless, but `restore()` on a
    // non-minimized window may reposition it — better not to call what is not
    // needed.
    const w = janela({ visivel: true })
    trazerParaFrente(w)

    expect(w.restore).not.toHaveBeenCalled()
    expect(w.show).not.toHaveBeenCalled()
    expect(w.focus).toHaveBeenCalledOnce()
  })

  it('foco vem por último, depois de restaurar e mostrar', () => {
    // Focusing before the window exists on screen has no effect on Windows.
    const ordem: string[] = []
    const w = {
      isMinimized: () => true,
      isVisible: () => false,
      restore: () => { ordem.push('restore') },
      show: () => { ordem.push('show') },
      focus: () => { ordem.push('focus') },
    }
    trazerParaFrente(w)
    expect(ordem).toEqual(['restore', 'show', 'focus'])
  })
})

// ── External link and panel navigation ──────────────────────────────────────
// `shell.openExternal` hands the destination to the OS: only http(s) and mailto
// pass, the same allowlist as the web window. And the panel never navigates
// away.

describe('protegerNavegacao', () => {
  async function montar() {
    const electron = await import('electron')
    const abrir = vi.fn(async () => undefined)
    ;(electron.shell as { openExternal?: unknown }).openExternal = abrir
    const { protegerNavegacao } = await import('./windows.js')
    let aoAbrir: ((d: { url: string }) => { action: string }) | undefined
    type Listener = (e: { preventDefault: () => void }, url: string) => void
    const ouvintes: Record<string, Listener> = {}
    const conteudo = {
      setWindowOpenHandler: vi.fn((f) => { aoAbrir = f }),
      on: vi.fn((evento: string, f: Listener) => { ouvintes[evento] = f }),
      getURL: vi.fn(() => 'http://localhost:5173/#log'),
    }
    protegerNavegacao(conteudo as never)
    return {
      abrir, aoAbrir: aoAbrir!,
      aoNavegar: ouvintes['will-navigate']!, aoRedirecionar: ouvintes['will-redirect']!,
    }
  }

  it('window.open com https vai ao navegador e a janela nova é negada', async () => {
    const { abrir, aoAbrir } = await montar()
    expect(aoAbrir({ url: 'https://atlans.example.org/docs' })).toEqual({ action: 'deny' })
    expect(abrir).toHaveBeenCalledWith('https://atlans.example.org/docs')
  })

  it.each(['file:///C:/Windows/System32/calc.exe', 'smb://atacante/compartilhamento', 'javascript:alert(1)'])(
    'esquema perigoso (%s) não chega ao SO',
    async (url) => {
      const { abrir, aoAbrir } = await montar()
      expect(aoAbrir({ url })).toEqual({ action: 'deny' })
      expect(abrir).not.toHaveBeenCalled()
    },
  )

  it('navegar o painel para fora é impedido e o destino seguro vai ao navegador', async () => {
    const { abrir, aoNavegar } = await montar()
    const evento = { preventDefault: vi.fn() }
    aoNavegar(evento, 'https://exemplo.com/pagina')
    expect(evento.preventDefault).toHaveBeenCalledOnce()
    expect(abrir).toHaveBeenCalledWith('https://exemplo.com/pagina')
  })

  it('navegar para um esquema perigoso é impedido e descartado', async () => {
    const { abrir, aoNavegar } = await montar()
    const evento = { preventDefault: vi.fn() }
    aoNavegar(evento, 'file:///etc/passwd')
    expect(evento.preventDefault).toHaveBeenCalledOnce()
    expect(abrir).not.toHaveBeenCalled()
  })

  it('recarregar a própria página passa — é o reload completo do Vite em dev', async () => {
    const { abrir, aoNavegar } = await montar()
    const evento = { preventDefault: vi.fn() }
    aoNavegar(evento, 'http://localhost:5173/')
    expect(evento.preventDefault).not.toHaveBeenCalled()
    expect(abrir).not.toHaveBeenCalled()
  })

  it('redirect para outra origem durante uma recarga é barrado', async () => {
    const { abrir, aoRedirecionar } = await montar()
    const evento = { preventDefault: vi.fn() }
    aoRedirecionar(evento, 'https://outro.exemplo/')
    expect(evento.preventDefault).toHaveBeenCalledOnce()
    expect(abrir).toHaveBeenCalledWith('https://outro.exemplo/')
  })

  it('mesmaPagina compara esquema, host e caminho — não hash nem query', async () => {
    const { mesmaPagina } = await import('./windows.js')
    expect(mesmaPagina('file:///app/dist/renderer/index.html#log', 'file:///app/dist/renderer/index.html')).toBe(true)
    expect(mesmaPagina('http://localhost:5173/#log', 'http://localhost:5173/?t=1')).toBe(true)
    expect(mesmaPagina('http://localhost:5173/', 'http://localhost:5174/')).toBe(false)
    expect(mesmaPagina('file:///app/dist/renderer/index.html', 'file:///etc/passwd')).toBe(false)
    expect(mesmaPagina('lixo', 'http://localhost:5173/')).toBe(false)
  })
})
