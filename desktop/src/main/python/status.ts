// desktop/src/main/python/status.ts
//
// Consulta `python -m executor status --json`, que fala com o servidor usando o
// certificado mTLS do executor.
//
// A consulta passa pelo Python de proposito: a chamada exige o cert do
// executor, o trust store da CA interna e a normalizacao de `wss://` para
// `https://`. Reimplementar isso em Node seria uma segunda implementacao de
// autenticacao para manter em dia — e a primeira a divergir quando a CA mudasse.
import { spawn } from 'node:child_process'
import {
  ARTIFACTS_DIR_PADRAO, PYTHON_EXE, RESOURCES, ambienteDoSpawn, envDoExecutor,
} from '../paths.js'

export interface Workspace {
  id_hash: string
  name?: string
}

export type ResultadoStatus =
  | { ok: true; executor_id: string; server_url: string; status: string | null; workspaces: Workspace[] }
  | { ok: false; codigo: 'config' | 'enrollment' | 'revoked' | 'rede' | 'http' | 'resposta' | 'falha'; erro: string }

const TIMEOUT_MS = 30_000

// ── Cache ────────────────────────────────────────────────────────────────────
//
// A consulta paga caro: cold start do interpretador empacotado, `bootstrap_ca()`
// (que pode montar o trust store), import de httpx/cryptography e um round-trip
// HTTPS — ate 30 s com a rede ruim. Sem cache, abrir a aba GeoSync repetia tudo,
// e a tela ficava com esqueleto pulsando enquanto o Python subia.
//
// So o SUCESSO e guardado: cachear uma falha de rede deixaria o botao
// "Tentar de novo" mentindo. A lista de workspaces de um executor muda por acao
// no Studio, e nao sozinha, entao um valor da sessao atual e bom o bastante —
// e `forcar` cobre quem quiser reconsultar.

let cache: ResultadoStatus | null = null
/** Consulta em voo, para dois pedidos simultaneos nao darem dois spawns. */
let emVoo: Promise<ResultadoStatus> | null = null
/**
 * Serie da consulta valida.
 *
 * Sobe a cada consulta nova E a cada `invalidarStatus()`. Uma consulta leva ate
 * 30 s; nesse intervalo o vinculo pode ter sido refeito (certificado novo,
 * outros workspaces) ou o usuario pode ter clicado "Atualizar". O resultado da
 * consulta vencida ainda e entregue a quem o pediu, mas NAO vira cache — sem
 * isso o `.then` da consulta velha repovoava o cache com os workspaces do
 * vinculo ANTIGO, e a aba GeoSync (que consulta uma vez so e fica montada pela
 * vida do app) oferecia um destino que este certificado nao alcanca mais.
 */
let serie = 0

/**
 * Consulta com cache de sessao.
 *
 * `forcar` e o botao "Atualizar" da tela: quem clica ali esta dizendo que o
 * servidor mudou, e devolver o cache — ou uma consulta em voo iniciada ANTES da
 * mudanca — seria ignorar o pedido.
 */
export function consultarStatusCacheado(forcar = false): Promise<ResultadoStatus> {
  if (!forcar && cache) return Promise.resolve(cache)
  if (emVoo && !forcar) return emVoo

  const minhaSerie = ++serie
  const p: Promise<ResultadoStatus> = consultarStatus()
    // `consultarStatus` resolve ate nos erros, mas o `spawn` pode lancar de
    // forma sincrona (argumento invalido, cwd inexistente). Sem este catch a
    // rejeicao vazava para o `invoke` do renderer como erro de IPC — e, pior,
    // deixava `emVoo` preso para sempre, congelando a tela em "carregando".
    .catch((e: unknown): ResultadoStatus => ({
      ok: false, codigo: 'falha', erro: e instanceof Error ? e.message : String(e),
    }))
    .then((r) => {
      if (r.ok && minhaSerie === serie) cache = r
      return r
    })
    .finally(() => {
      // So limpa se ainda for a consulta corrente: uma consulta vencida nao
      // pode derrubar a que a substituiu.
      if (emVoo === p) emVoo = null
    })
  emVoo = p
  return p
}

/**
 * Esquece o vinculo consultado.
 *
 * Obrigatorio ao descartar ou refazer o enrollment: os workspaces sao os que
 * AQUELE certificado alcanca, e mostrar a lista do vinculo antigo depois de
 * trocar de executor faria a pessoa escolher um destino que nao existe mais.
 *
 * Solta tambem a consulta EM VOO — ela foi feita com o certificado velho, e
 * mante-la era o caminho pelo qual o dado invalidado voltava.
 */
export function invalidarStatus(): void {
  cache = null
  emVoo = null
  serie++
}

/** A consulta crua. Privada: quem chama de fora passa pelo cache acima. */
function consultarStatus(): Promise<ResultadoStatus> {
  return new Promise((resolve) => {
    const proc = spawn(PYTHON_EXE, ['-X', 'utf8', '-m', 'executor', 'status', '--json'], {
      cwd: RESOURCES,
      env: ambienteDoSpawn(envDoExecutor(ARTIFACTS_DIR_PADRAO)),
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    })

    let saida = ''
    let erro = ''
    let terminou = false
    const finalizar = (r: ResultadoStatus) => {
      if (terminou) return
      terminou = true
      clearTimeout(timer)
      resolve(r)
    }

    const timer = setTimeout(() => {
      proc.kill()
      finalizar({ ok: false, codigo: 'rede', erro: 'O servidor não respondeu a tempo.' })
    }, TIMEOUT_MS)

    proc.stdout.setEncoding('utf8')
    proc.stdout.on('data', (c: string) => { saida += c })
    proc.stderr.setEncoding('utf8')
    proc.stderr.on('data', (c: string) => { erro += c })

    proc.on('error', (e) => finalizar({ ok: false, codigo: 'falha', erro: e.message }))

    proc.on('close', () => {
      // O `_ca_bootstrap` escreve linhas informativas antes do JSON; pegar a
      // ultima nao-vazia as ignora.
      const linha = saida.split('\n').map((l) => l.trim()).filter(Boolean).pop()
      if (!linha) {
        finalizar({ ok: false, codigo: 'falha', erro: erro.trim() || 'Sem resposta.' })
        return
      }
      try {
        finalizar(JSON.parse(linha) as ResultadoStatus)
      } catch {
        finalizar({ ok: false, codigo: 'resposta', erro: erro.trim() || linha.slice(0, 200) })
      }
    })
  })
}
