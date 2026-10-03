// desktop/src/renderer/components/StatusBar.tsx
//
// Status bar at the bottom of the WINDOW — full width, below the sidebar and
// the content.
//
// The executor state does not belong to any screen: it applies to all of them.
// While it lived in the sidebar footer, it competed for space with the
// navigation and was squeezed into 192px; and while it lived in the Painel
// header, it vanished when switching tabs. Here it is window chrome, like an
// editor's status bar — always in the same place, always legible, without
// costing content height.
//
// What goes in: what is checked at a glance and not clicked often. Lifecycle
// actions remain in the sidebar, where the target is large.
import {
  TbAlertTriangle, TbCircleX, TbFolder, TbFolderSymlink, TbList,
} from 'react-icons/tb'
import type { EstadoApp } from '../../main/state/store.js'
import type { InfoApp } from '../../shared/ipc.js'
import { gb, nivelDoDisco } from '../../shared/disco.js'
import { cn } from '../lib/utils.js'

/** Colored status dot. The color is the same language as the tray icon. */
export function Ponto({ estado }: { estado: EstadoApp }) {
  const snap = estado.snapshot
  const conectado = estado.supervisor === 'running' && snap?.conn_state === 'connected'
  const ocupado = conectado && snap.running_count > 0
  const erro = estado.supervisor === 'failed'

  const cor = erro ? 'bg-destructive'
    : ocupado ? 'bg-blue-400'
    : conectado ? 'bg-green-400'
    : 'bg-muted-foreground'

  return (
    <span
      className="relative flex size-2 shrink-0"
      // The color is the only clue to the connection state in this strip; without an
      // accessible label, the LED does not exist for screen reader users.
      role="img"
      aria-label={`Estado: ${rotuloStatus(estado)}`}
    >
      {/* Breathing, not `animate-ping`.
          The ring that expands every second lives in the window's ONLY
          permanent chrome — an app that stays open all day in the background —
          and continuous peripheral motion is tiring without saying anything
          new. Breathing communicates "alive" just as clearly and without the
          strobe. See the prefers-reduced-motion block in index.css: under it
          the LED stays lit, not off. */}
      <span className={cn(
        'relative inline-flex size-2 rounded-full transition-colors duration-500',
        ocupado && 'animate-pulso-vivo',
        cor,
      )} />
    </span>
  )
}

export function rotuloStatus(estado: EstadoApp): string {
  const snap = estado.snapshot
  switch (estado.supervisor) {
    case 'stopped': return 'Parado'
    case 'starting': return 'Iniciando…'
    case 'draining': return 'Encerrando…'
    case 'restarting': return 'Reiniciando…'
    case 'failed': return 'Parado por erro'
    case 'running':
      if (!snap) return 'Conectando…'
      if (snap.conn_state === 'connected') {
        return snap.running_count > 0 ? `${snap.running_count} em execução` : 'Conectado'
      }
      return snap.conn_state === 'reconnecting' ? 'Reconectando…' : 'Sem conexão'
  }
}

/** Detail that only makes sense in some states — empty in the others. */
function detalhe(estado: EstadoApp): string | null {
  const snap = estado.snapshot
  if (!snap) return null
  // Without this, the user keeps clicking Reconectar without knowing there is
  // already a scheduled attempt.
  if (snap.conn_state === 'reconnecting' && snap.next_retry_in_s != null) {
    return `nova tentativa em ${Math.ceil(snap.next_retry_in_s)}s`
  }
  if (estado.supervisor === 'draining') {
    return `${snap.running_count} em andamento, ${snap.result_queue_size} a confirmar`
  }
  if (snap.queued > 0) return `${snap.queued} na fila`
  return null
}

/**
 * Status bar shortcut.
 *
 * Five ad-hoc `<button>`s shared the same look and none had a focus ring: the
 * whole bar was invisible to keyboard users. The target was also just the
 * text — `px-1.5 py-0.5` gives click area without changing the height of the
 * strip, which is fixed.
 */
const ATALHO = [
  'flex shrink-0 items-center gap-1 rounded-sm px-1.5 py-0.5 outline-none',
  'transition-colors underline-offset-4 hover:underline',
  'focus-visible:ring-ring/50 focus-visible:ring-2',
].join(' ')

export function StatusBar({
  estado, info, pastaGeosync, aoAbrirAjustes,
}: {
  estado: EstadoApp
  info: InfoApp | null
  /** GeoSync folder, when one is configured. */
  pastaGeosync: string | null
  aoAbrirAjustes: () => void
}) {
  // Counted in the main process, incrementally. Scanning the whole log here would
  // require it to travel in the state — which is exactly the cost the
  // incremental channel removed (see main/state/store.ts).
  const erros = estado.errosNoLog
  const extra = detalhe(estado)
  // Only with the executor running: the metric comes from its snapshot.
  const disco = estado.supervisor === 'running'
    ? nivelDoDisco(estado.snapshot?.artifacts_disk_free_gb)
    : null

  return (
    <footer className="flex h-7 shrink-0 items-center gap-3 border-t border-sidebar-border bg-sidebar px-3 text-xs text-muted-foreground">
      {/* Shortcuts and version on the LEFT; the state sits in the right
          corner, which is where a desktop app's status bar puts it — and
          where it is not pushed around when a shortcut appears or vanishes. */}
      {/* The LOG left the side navigation and opens in its OWN WINDOW. Reading
          a log is almost always comparing it with something else — the
          dashboard, the Studio, an editor — and a tab forces you to choose
          between the two. The window also needs no "active" state here: the
          window manager is in charge of it, and a highlight of ours would
          drift from reality as soon as the person closed it. */}
      <button type="button" onClick={() => window.atlas.abrirJanelaLog()}
              title="Abrir o log em uma janela separada"
              className={cn(ATALHO, 'hover:text-foreground')}>
        <TbList size={13} /> Log
      </button>

      {info && (
        <button type="button" onClick={() => window.atlas.abrirCaminho(info.artifactsDir)}
                title={`Abrir no Explorer: ${info.artifactsDir}`}
                className={cn(ATALHO, 'hover:text-foreground')}>
          <TbFolder size={13} /> Artefatos
        </button>
      )}
      {/* Only when one is configured. A shortcut to a nonexistent folder would
          be a button that does nothing — and the GeoSync folder is optional.
          The logs folder left this place: it is in Ajustes, with the other
          installation folders, and two things called "Log" in the same bar
          were confusing. */}
      {pastaGeosync && (
        <button type="button" onClick={() => window.atlas.abrirCaminho(pastaGeosync)}
                title={`Abrir no Explorer: ${pastaGeosync}`}
                className={cn(ATALHO, 'hover:text-foreground')}>
          <TbFolderSymlink size={13} /> GeoSync
        </button>
      )}
      {info && <span>v{info.versao}</span>}
      {info?.dev && <span className="font-medium text-primary">dev</span>}

      <span className="flex-1" />

      {/* Disk only appears when it is tight. A permanent "487 GB livres"
          (487 GB free) indicator takes up the bar to say nothing. */}
      {disco && disco !== 'ok' && (
        <button type="button" onClick={aoAbrirAjustes}
                title="Ver detalhes em Ajustes"
                className={cn(
                  ATALHO,
                  'animate-in fade-in-0 slide-in-from-right-2 duration-300',
                  disco === 'critico' ? 'text-destructive' : 'text-warning',
                )}>
          {/* Warning glyph, not the storage one: this item only exists when the
              disk is tight, and a neutral "database" icon made it just one
              more piece of information in the bar. */}
          <TbAlertTriangle size={13} />
          {gb(estado.snapshot?.artifacts_disk_free_gb)} livres
        </button>
      )}
      {erros > 0 && (
        <button type="button" onClick={() => window.atlas.abrirJanelaLog()}
                title="Abrir o log para ver os erros"
                className={cn(ATALHO, 'text-destructive animate-in fade-in-0 slide-in-from-right-2 duration-300')}>
          <TbCircleX size={13} />
          {/* "1 erro(s)" was the only parenthesized plural in the file. */}
          {erros > 99 ? '99+ erros' : `${erros} ${erros === 1 ? 'erro' : 'erros'}`}
        </button>
      )}
      {extra && <span className="truncate">{extra}</span>}
      <span className="flex items-center gap-2 border-l border-sidebar-border pl-3">
        <Ponto estado={estado} />
        <span className="text-foreground">{rotuloStatus(estado)}</span>
      </span>
    </footer>
  )
}
