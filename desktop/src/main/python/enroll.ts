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
export type EnrollCode =
  | 'otp_ausente'
  | 'executor_id_ausente'
  | 'enroll_recusado'
  /** Local, not from Python: another enrollment of this app is still running. */
  | 'enroll_em_andamento'
  | 'signing_key_conflict'
  | 'saida_invalida'
  | 'timeout'

export type EnrollResult =
  | {
      ok: true
      executor_id: string
      serial: string | null
      fingerprint: string | null
      expires_at: string | null
      cert_dir: string
      env_path: string
    }
  | { ok: false; codigo: EnrollCode; erro: string; cert_dir?: string }

/**
 * The server is NOT part of the request: it is the constant {@link SERVIDOR}.
 *
 * Accepting it here would reopen the hole the constant closes — the renderer
 * and the deep link are untrusted input, and a `servidor` coming from them
 * would decide whom this machine binds to.
 */
export interface EnrollRequest {
  executorId: string
  otp: string
}

/** Enrollment should not take longer than this; beyond it, the server is hung. */
const TIMEOUT_MS = 120_000

/**
 * The enrollment in progress, if any.
 *
 * Only the renderer's `enviando` flag kept a second one from starting — not a
 * double IPC, nor a deep link push crossing a manual submit. Two processes
 * each write `cert.pem.new`/`key.pem.new` and replace file by file
 * (executor/enrollment.py), so the pair on disk could end up with the cert of
 * one run and the key of the other: a machine that can no longer connect.
 */
let emCurso: Promise<EnrollResult> | null = null

export function enrolar(pedido: EnrollRequest): Promise<EnrollResult> {
  if (emCurso) {
    return Promise.resolve({
      // Its own code: `enroll_recusado` made the form say the SERVER refused
      // and mark the OTP red, while the first run could still succeed with it.
      ok: false, codigo: 'enroll_em_andamento',
      erro: 'Já há um enrollment em andamento — aguarde o resultado.',
    })
  }
  const atual = executar(pedido)
  emCurso = atual
  const liberar = () => { if (emCurso === atual) emCurso = null }
  atual.then(liberar, liberar)
  return atual
}

function executar(pedido: EnrollRequest): Promise<EnrollResult> {
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

    const finish = (r: EnrollResult) => {
      if (terminou) return
      terminou = true
      clearTimeout(timer)
      resolve(r)
    }

    const timer = setTimeout(() => {
      proc.kill()
      finish({
        ok: false, codigo: 'timeout',
        erro: `O enrollment não respondeu em ${TIMEOUT_MS / 1000}s. Verifique o endereço do servidor e a conexão.`,
      })
    }, TIMEOUT_MS)

    proc.stdout.setEncoding('utf8')
    proc.stdout.on('data', (c: string) => { saida += c })
    proc.stderr.setEncoding('utf8')
    proc.stderr.on('data', (c: string) => { erro += c })
    // Writing the OTP to a process that died at startup (or never started)
    // fails asynchronously, as an 'error' on stdin; without a listener that is
    // an uncaught exception in main. The reason joins the stderr text, which is
    // what the user sees if no result comes out.
    proc.stdin.on('error', (e) => { erro += `\n[app] stdin do enrollment: ${e.message}` })

    proc.on('error', (e) => finish({
      ok: false, codigo: 'enroll_recusado',
      erro: `Não foi possível executar o enrollment: ${e.message}`,
    }))

    proc.on('close', () => {
      // Python emits exactly one JSON line; taking the last non-empty one
      // tolerates a native-library warning written to fd 1 before it.
      const linha = saida.split('\n').map((l) => l.trim()).filter(Boolean).pop()
      if (!linha) {
        finish({
          ok: false, codigo: 'saida_invalida',
          erro: erro.trim() || 'O enrollment terminou sem produzir resultado.',
        })
        return
      }
      try {
        finish(JSON.parse(linha) as EnrollResult)
      } catch {
        finish({
          ok: false, codigo: 'saida_invalida',
          erro: erro.trim() || `Resposta não reconhecida do enrollment: ${linha.slice(0, 200)}`,
        })
      }
    })

    proc.stdin.write(pedido.otp + '\n')
    proc.stdin.end()
  })
}
