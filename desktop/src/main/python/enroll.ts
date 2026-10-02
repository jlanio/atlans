// desktop/src/main/python/enroll.ts
//
// Enrollment a partir do app: roda `python -m executor enroll` como processo
// one-shot e devolve o resultado tipado.
//
// Duas escolhas de seguranca:
//
// 1. O OTP vai pelo **stdin**, nao por argv. A linha de comando de um processo
//    e legivel por qualquer outro processo do mesmo usuario (Gerenciador de
//    Tarefas, `wmic`, `Get-CimInstance Win32_Process`). O OTP e de uso unico e
//    dura 24 h, mas nao ha motivo para expo-lo quando o stdin custa o mesmo.
//
// 2. `--json` faz o Python emitir um unico objeto no stdout, com o log humano
//    indo para o stderr. Sem isso, sobraria parsear o relatorio em portugues —
//    o mesmo erro que apodreceu o app anterior.
import { spawn } from 'node:child_process'
import { PYTHON_EXE, RESOURCES, ambienteDoSpawn, envDoExecutor } from '../paths.js'
import { ARTIFACTS_DIR_PADRAO, CERT_DIR } from '../paths.js'
import { SERVIDOR } from '../../shared/servidor.js'

/** Espelha os `codigo` emitidos por executor/enrollment.py::_cli_main. */
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
 * O servidor NÃO faz parte do pedido: ele é a constante {@link SERVIDOR}.
 *
 * Aceitá-lo aqui reabriria o buraco que a constante fecha — o renderer e o deep
 * link são entrada não confiável, e um `servidor` vindo deles decidiria contra
 * quem esta máquina se vincula.
 */
export interface PedidoEnroll {
  executorId: string
  otp: string
}

/** Enrollment nao deve levar mais que isso; acima disso e servidor pendurado. */
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
      // O Python emite exatamente uma linha JSON; pegar a ultima nao-vazia
      // tolera um aviso de biblioteca nativa que escreva no fd 1 antes dela.
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
