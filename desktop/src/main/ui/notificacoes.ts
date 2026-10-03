// desktop/src/main/ui/notificacoes.ts
//
// Windows notifications.
//
// A background agent that fails silently is the classic failure mode: the app
// lives in the tray, the window is usually closed, and the person only finds
// out the executor stopped through the work that did not run.
//
// ## What does NOT notify
//
// No "workflow completed". On a machine that runs dozens a day, that becomes
// noise, and the person turns off notifications for the whole app — including
// the three that matter. The yardstick here is: **notify only what requires
// human action and will not resolve itself.**
//
// Connection failures are also left out: the executor reconnects with backoff,
// and a thirty-second network blip is nobody's business.
//
// ## Why a pure function
//
// `avaliarNotificacao` decides without touching Electron. What turns a
// notification system into spam is duplication — notifying on every snapshot
// tick, or re-notifying the same condition — and that is exactly what can be
// locked down with tests when the decision is separate from the effect.
import { Notification } from 'electron'
import { ICONE_APP } from '../paths.js'
import type { AppState } from '../state/store.js'
// The thresholds live in `shared/` because the SCREEN needs them too and
// cannot import values from here (this module pulls in `electron`). A green
// bar while the notification has already warned would be worse than sharing
// two numbers.
import { DISCO_BAIXO_GB, DISCO_CRITICO_GB } from '../../shared/disco.js'

export { DISCO_BAIXO_GB, DISCO_CRITICO_GB }

export interface Aviso {
  /**
   * Identity of the condition, not of the message.
   *
   * Two consecutive reads with the same key are the SAME situation, and the
   * second does not become a notification. That is what separates "warning"
   * from "hammering": the snapshot arrives every second.
   */
  chave: string
  titulo: string
  corpo: string
  urgente: boolean
}

/**
 * Decides what deserves a notification in the current state. `null` = nothing
 * to say.
 *
 * One condition at a time, by priority: an executor stopped by an error makes
 * disk space irrelevant, and two stacked toasts compete with each other.
 */
export function avaliarNotificacao(estado: AppState): Aviso | null {
  // ── 1. Revoked ─────────────────────────────────────────────────────────────
  // The most serious case: it is not a failure that passes. The executor is
  // down until someone redoes the link, and nothing in the system will fix
  // that on its own.
  if (estado.supervisor === 'failed' && estado.passoFase === 'revoked') {
    return {
      chave: 'revoked',
      titulo: 'Executor removido do servidor',
      corpo: 'Esta máquina não é mais reconhecida e parou de receber execuções. '
           + 'Abra o painel e refaça o vínculo com um OTP novo.',
      urgente: true,
    }
  }

  // ── 2. Stopped by an error ─────────────────────────────────────────────────
  if (estado.supervisor === 'failed') {
    return {
      // The step goes into the key: a certificate error after a configuration
      // error are different problems, and the second deserves to be reported.
      chave: `failed:${estado.passoFase ?? '?'}`,
      titulo: 'O executor parou',
      corpo: estado.detalheFase ?? estado.detalheSupervisor
           ?? 'Abra o painel para ver o motivo.',
      urgente: true,
    }
  }

  // ── 3. Disk ────────────────────────────────────────────────────────────────
  // Only with the executor running: warning about disk for a stopped
  // executor is noise about a problem that does not exist yet.
  const livre = estado.snapshot?.artifacts_disk_free_gb
  if (estado.supervisor === 'running' && typeof livre === 'number') {
    if (livre < DISCO_CRITICO_GB) {
      return {
        chave: 'disco:critico',
        titulo: 'Disco quase cheio',
        corpo: `Restam ${livre.toFixed(1)} GB na pasta de artefatos. Workflows `
             + 'já podem falhar ao gravar o resultado.',
        urgente: true,
      }
    }
    if (livre < DISCO_BAIXO_GB) {
      return {
        chave: 'disco:baixo',
        titulo: 'Pouco espaço em disco',
        corpo: `Restam ${livre.toFixed(1)} GB na pasta de artefatos. Os arquivos `
             + 'mantidos apenas nesta máquina não têm cópia em outro lugar.',
        urgente: false,
      }
    }
  }

  return null
}

// ── Efeito ───────────────────────────────────────────────────────────────────

let lastKey: string | null = null

/**
 * Notifies when the condition CHANGES.
 *
 * Called on every store update — once per second with the executor running.
 * Without the comparison with the previous key, an executor stopped by an
 * error would generate one toast per second until someone intervened.
 *
 * `aoClicar` leads to the panel: a notification that says "open the panel"
 * and opens nothing when clicked is worse than none at all.
 */
export function notificarSeMudou(estado: AppState, aoClicar: () => void): void {
  const aviso = avaliarNotificacao(estado)
  const chave = aviso?.chave ?? null

  // Going back to normal RE-ARMS: if the problem returns after being resolved,
  // it is reported again. Without this, an executor that fails, is restarted
  // and fails again would stay silent the second time.
  if (chave === lastKey) return
  lastKey = chave
  if (!aviso) return

  if (!Notification.isSupported()) return
  try {
    const n = new Notification({
      title: aviso.titulo,
      body: aviso.corpo,
      icon: ICONE_APP,
      // `urgency` only has an effect on Linux; on Windows Electron ignores it.
      // It stays for portability, not because it changes anything here.
      urgency: aviso.urgente ? 'critical' : 'normal',
    })
    n.on('click', aoClicar)
    n.show()
  } catch {
    // Notifications are a convenience. A Windows with toasts disabled by
    // policy must not take down the app's state loop.
  }
}

/** For the tests: discards the memory of the last condition. */
export function _resetarMemoria(): void {
  lastKey = null
}
