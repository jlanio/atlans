// desktop/src/main/python/enroll.ts
//
// Enrollment from the app: runs `python -m executor enroll` as a one-shot
// process and returns the typed result.
//
// Two security choices:
//
// 1. The OTP goes through **stdin**, not argv. A process's command line is
//    readable by any other process of the same user (Task Manager, `wmic`,
//    `Get-CimInstance Win32_Process`). The OTP is single-use and lasts 24 h,
//    but there is no reason to expose it when stdin costs the same.
//
// 2. `--json` makes Python emit a single object on stdout, with the human log
//    going to stderr. Without it, we would be left parsing the Portuguese
//    report — the same mistake that rotted the previous app.
import { spawn } from 'node:child_process'
import { PYTHON_EXE, RESOURCES, ambienteDoSpawn, envDoExecutor } from '../paths.js'
import { ARTIFACTS_DIR_PADRAO, CERT_DIR } from '../paths.js'
import { SERVIDOR } from '../../shared/servidor.js'

/** Mirrors the `codigo` values emitted by executor/enrollment.py::_cli_main. */
export type CodigoEnroll =
  | 'otp_ausente'
  | 'executor_id_ausente'
  | 'enroll_recusado'
  | 'signing_key_conflict'
  | 'saida_invalida'
  | 'timeout'

export type ResultadoEnroll =
  | {
      ok: true
      executor_id: string
      serial: string | null
      fingerprint: string | null
      expires_at: string | null
      cert_dir: string
      env_path: string
    }
  | { ok: false; codigo: CodigoEnroll; erro: string; cert_dir?: string }

/**
 * The server is NOT part of the request: it is the constant {@link SERVIDOR}.
 *
 * Accepting it here would reopen the hole the constant closes — the renderer
 * and the deep link are untrusted input, and a `servidor` coming from them
 * would decide whom this machine binds to.
 */
export interface PedidoEnroll {
  executorId: string
  otp: string
}

/** Enrollment should not take longer than this; beyond it, the server is hung. */
const TIMEOUT_MS = 120_000

export function enrolar(pedido: PedidoEnroll): Promise<ResultadoEnroll> {
  return new Promise((resolve) => {
    const proc = spawn(PYTHON_EXE, [
      '-X', 'utf8', '-m', 'executor', 'enroll',
      '--json',
      '--otp-stdin',
      `--executor-id=${pedido.executorId}`,
      `--server=${SERVIDOR}`,
      `--cert-dir=${CERT_DIR}`,
    ], {
      cwd: RESOURCES,
      env: ambienteDoSpawn(envDoExecutor(ARTIFACTS_DIR_PADRAO)),
      windowsHide: true,
      stdio: ['pipe', 'pipe', 'pipe'],
    })

    let saida = ''
    let erro = ''
    let terminou = false

    const finalizar = (r: ResultadoEnroll) => {
      if (terminou) return
      terminou = true
      clearTimeout(timer)
      resolve(r)
    }

    const timer = setTimeout(() => {
      proc.kill()
      finalizar({
        ok: false, codigo: 'timeout',
        erro: `O enrollment não respondeu em ${TIMEOUT_MS / 1000}s. Verifique o endereço do servidor e a conexão.`,
      })
    }, TIMEOUT_MS)

    proc.stdout.setEncoding('utf8')
    proc.stdout.on('data', (c: string) => { saida += c })
    proc.stderr.setEncoding('utf8')
    proc.stderr.on('data', (c: string) => { erro += c })

    proc.on('error', (e) => finalizar({
      ok: false, codigo: 'enroll_recusado',
      erro: `Não foi possível executar o enrollment: ${e.message}`,
    }))

    proc.on('close', () => {
      // Python emits exactly one JSON line; taking the last non-empty one
      // tolerates a native-library warning written to fd 1 before it.
      const linha = saida.split('\n').map((l) => l.trim()).filter(Boolean).pop()
      if (!linha) {
        finalizar({
          ok: false, codigo: 'saida_invalida',
          erro: erro.trim() || 'O enrollment terminou sem produzir resultado.',
        })
        return
      }
      try {
        finalizar(JSON.parse(linha) as ResultadoEnroll)
      } catch {
        finalizar({
          ok: false, codigo: 'saida_invalida',
          erro: erro.trim() || `Resposta não reconhecida do enrollment: ${linha.slice(0, 200)}`,
        })
      }
    })

    proc.stdin.write(pedido.otp + '\n')
    proc.stdin.end()
  })
}
