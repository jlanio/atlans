// desktop/src/shared/executor-status.ts
//
// The REDACTED status of the local executor that the web window can read.
//
// This is the only data that crosses the preload/web.ts bridge (main → web,
// read-only). It exists so the web UI, running INSIDE the desktop app, can say
// "this computer's executor is online" — something it does not know from the
// server's point of view, which sees the account's executors but not which of
// them is the machine in front of the user.
//
// `derivarStatus` is the ONLY point that serializes for the bridge: everything
// that goes out passes through here, so the redaction (what is safe to expose)
// can be reviewed in a single place. Nothing beyond these fields crosses — no
// certificate, OTP, server_url, paths, log, resource metrics or history.
import type { EstadoApp } from '../main/state/store.js'
import type { EstadoConfiguracao } from '../main/state/config.js'

/** IPC channels of the bridge. Single source for the preload and main (like ipc.ts). */
export const CANAIS_WEB = {
  /** web → main, with a response: the current status (used on the first render). */
  status: 'atlas-web:executor-status',
  /** main → web, push: novo status quando a assinatura muda. */
  statusMudou: 'atlas-web:executor-status-mudou',
} as const

export type EstadoExecutorLocal = 'online' | 'ocupado' | 'offline' | 'sem-vinculo'

export interface StatusExecutorLocal {
  /** Bumped if the format changes; the web does feature detection on top of this. */
  versaoContrato: 1
  /**
   * PUBLIC identity of this executor — the same `id_hash` the server already
   * shows the logged-in user (it is the enrollment's `executor_id`). Lets the
   * web match "this computer" with the row in the Executores list. It is not a
   * secret: the secrets are the certificate and the OTP, which never cross.
   */
  executorId: string | null
  vinculado: boolean
  estado: EstadoExecutorLocal
  emExecucao: number
  capacidade: number | null
}

/**
 * Derives the public status from the live state + the configuration.
 *
 * Mirrors the logic of the tray's `estadoDoIcone` and adds the "sem-vinculo"
 * case (without enrollment there is no executor to show). `emExecucao` is only
 * meaningful when online/busy — otherwise it is 0, so the UI never says
 * "offline · 2 em execução" (offline · 2 running).
 */
export function derivarStatus(
  estado: Pick<EstadoApp, 'supervisor' | 'snapshot'>,
  cfg: Pick<EstadoConfiguracao, 'configurado' | 'executorId'>,
): StatusExecutorLocal {
  const snap = estado.snapshot

  let est: EstadoExecutorLocal
  if (!cfg.configurado) {
    est = 'sem-vinculo'
  } else if (estado.supervisor !== 'running' || !snap || snap.conn_state !== 'connected') {
    est = 'offline'
  } else if ((snap.running_count ?? 0) > 0) {
    est = 'ocupado'
  } else {
    est = 'online'
  }

  const ativo = est === 'online' || est === 'ocupado'
  return {
    versaoContrato: 1,
    executorId: cfg.executorId,
    vinculado: cfg.configurado,
    estado: est,
    emExecucao: ativo ? (snap?.running_count ?? 0) : 0,
    capacidade: snap?.max_concurrent ?? null,
  }
}

/**
 * Short key to deduplicate broadcasts.
 *
 * The executor state is re-evaluated on every tick (≈12 Hz with the executor
 * active), but what the bridge carries rarely changes. Comparing the signature
 * avoids sending a structured clone to the window on every tick for nothing —
 * same guard as the tray.
 */
export function assinaturaStatus(s: StatusExecutorLocal): string {
  return [s.estado, s.executorId ?? '', s.emExecucao, s.capacidade ?? '', s.vinculado ? 1 : 0].join('|')
}
