// desktop/src/renderer/components/TitleBar.tsx
//
// Title bar drawn by the app (the window uses `frame: false`).
//
// A deliberate hybrid: the LOOK is macOS's (solid colored circles), but the
// POSITION and ORDER are Windows's — on the right, minimize / maximize / close,
// with close in the corner. That is where a Windows user's hand already goes,
// and leaving "close" anywhere else in the group would create a hybrid that
// matches neither system.
//
// The only reaction to the mouse is the function's glyph appearing inside the
// circle under the cursor — one at a time, only the one being pointed at.
//
// `-webkit-app-region: drag` makes the bar drag the window; the buttons need
// an explicit `no-drag`, otherwise the click becomes the start of a drag and
// never fires.
import { useState } from 'react'
import { cn } from '../lib/utils.js'

type Semaforo = 'fechar' | 'minimizar' | 'maximizar'

// macOS traffic-light colors. They are fixed values on purpose, not design
// system tokens: the user recognizes this specific red/yellow/green as "window
// controls", and swapping them for the product's terracotta palette would take
// away precisely the familiarity that motivates using them.
const CORES: Record<Semaforo, string> = {
  fechar: 'bg-[#ff5f57]',
  minimizar: 'bg-[#febc2e]',
  maximizar: 'bg-[#28c840]',
}

// Dark shade of the circle's own color, as on macOS: a black or white glyph
// would clash with the colored background instead of settling into it.
const TINTA: Record<Semaforo, string> = {
  fechar: '#7a0a04',
  minimizar: '#8a5a00',
  maximizar: '#0a5c17',
}

function Glifo({ tipo, maximizada }: { tipo: Semaforo; maximizada: boolean }) {
  const comum = {
    // `group-hover/semaforo` matches the `group/semaforo` of the button ITSELF —
    // each circle is its own group, so only the one under the cursor reveals
    // the glyph. `pointer-events-none` on the svg keeps it from stealing the
    // button's hover and making the icon flicker when the mouse moves inside
    // the circle.
    className:
      'pointer-events-none absolute inset-0 m-auto opacity-0 transition-opacity duration-150 group-hover/semaforo:opacity-100 group-focus-visible/semaforo:opacity-100',
    stroke: TINTA[tipo],
    strokeWidth: 1.3,
    strokeLinecap: 'round' as const,
    fill: 'none',
    'aria-hidden': true,
  }

  if (tipo === 'fechar') {
    return <svg {...comum} width="6" height="6" viewBox="0 0 6 6"><path d="M1 1l4 4M5 1L1 5" /></svg>
  }
  if (tipo === 'minimizar') {
    return <svg {...comum} width="7" height="2" viewBox="0 0 7 2"><path d="M0.6 1h5.8" /></svg>
  }
  return (
    <svg {...comum} width="7" height="7" viewBox="0 0 7 7">
      {maximizada
        // Restore: arrows pointing inward.
        ? <path d="M3.6 0.9v2.3H1.3M3.4 6.1V3.8h2.3" />
        // Maximizar: cantos opostos, apontando para fora.
        : <path d="M1 3.2V1h2.2M6 3.8V6H3.8" />}
    </svg>
  )
}

function Botao({
  tipo, rotulo, maximizada, aoClicar,
}: {
  tipo: Semaforo
  rotulo: string
  maximizada: boolean
  aoClicar: () => void
}) {
  return (
    <button
      type="button"
      onClick={aoClicar}
      aria-label={rotulo}
      title={rotulo}
      // `app-region: no-drag` is mandatory: inside a drag area, the click would be
      // consumed by the gesture of moving the window.
      style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}
      // The CIRCLE is 12px, but the target does not have to be: `p-1.5 -m-1.5`
      // grows the clickable area to 24px without moving the drawing or
      // changing the bar height. They were three 12px targets side by side —
      // the app's first tab stops, and with no focus ring.
      //
      // `focus-visible` (and not `focus`): someone who clicks sees no ring;
      // someone who tabs does. Without it, the keyboard went through the three
      // window controls blind.
      className={cn(
        'group/semaforo relative -m-1.5 box-content size-3 rounded-full p-1.5 outline-none',
        'transition-transform active:scale-90',
        'focus-visible:ring-ring/70 focus-visible:ring-2',
        'bg-clip-content',
        CORES[tipo],
      )}
    >
      <Glifo tipo={tipo} maximizada={maximizada} />
    </button>
  )
}

export function TitleBar({ titulo }: { titulo?: string }) {
  // Only tracked to choose the label between "Maximizar" and "Restaurar" — the
  // button does not change appearance.
  const [maximizada, setMaximizada] = useState(false)

  const alternarMaximizar = () => {
    void window.atlas.janela('alternar-maximizar').then(setMaximizada)
  }

  return (
    <header
      style={{ WebkitAppRegion: 'drag' } as React.CSSProperties}
      // Double click on the bar toggles maximize — expected behavior on both
      // systems.
      onDoubleClick={alternarMaximizar}
      className="relative flex h-9 shrink-0 items-center justify-end border-b border-border/60 bg-sidebar px-3 select-none"
    >
      {/* Title centered in the WINDOW, not in the remaining space: `absolute`
          keeps the width of the button group from shifting it to the left. */}
      <span className="pointer-events-none absolute inset-x-0 text-center text-xs font-medium text-muted-foreground">
        {titulo ?? 'Atlans Executor'}
      </span>

      {/* Windows order: close last, in the window corner. The hover belongs to
          each button (`group/semaforo`), not to this container. */}
      <div className="flex items-center gap-2">
        <Botao tipo="minimizar" rotulo="Minimizar" maximizada={maximizada}
               aoClicar={() => void window.atlas.janela('minimizar')} />
        <Botao tipo="maximizar" rotulo={maximizada ? 'Restaurar' : 'Maximizar'} maximizada={maximizada}
               aoClicar={alternarMaximizar} />
        <Botao tipo="fechar" rotulo="Fechar" maximizada={maximizada}
               aoClicar={() => void window.atlas.janela('fechar')} />
      </div>
    </header>
  )
}
