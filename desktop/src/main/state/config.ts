// desktop/src/main/state/config.ts
//
// Leitura e escrita do `.env` do executor.
//
// A escrita e reimplementada aqui em vez de chamar o Python so para gravar uma
// linha, e espelha `executor/_env_utils.py::persist_env_var`: preserva
// comentarios, ordem e chaves que o app nao conhece. Reescrever o arquivo
// inteiro a partir de um dicionario apagaria EXECUTOR_HOST_ALIASES, MINIO_*,
// LOG_FILE_AGENT e tudo mais que o usuario ou o enrollment tenham colocado la.
import fs from 'node:fs'
import path from 'node:path'
import { CERT_DIR, ENV_FILE } from '../paths.js'
import { SERVIDOR } from '../../shared/servidor.js'
import {
  ESTRATEGIAS, INTERVALO_SYNC, MODOS_SYNC, PADRAO_SYNC,
  type EstrategiaConflito, type ModoSync,
} from '../../shared/geosync.js'
import { LIMITES, inteiroDoEnv } from '../../shared/limites.js'

/** Arquivos que o enrollment produz. Sem os dois, `assert_enrolled` barra o boot. */
const CERT_OBRIGATORIOS = ['cert.pem', 'key.pem']

/**
 * Material de identidade DESTE executor, descartado ao refazer o enrollment.
 *
 * A lista e explicita, e nao um `rm -rf` do cert dir, porque a pasta guarda
 * tambem coisas que devem SOBREVIVER:
 *
 *   - `server_signing.pub` — a chave Ed25519 do servidor, fixada por TOFU.
 *     Apaga-la reabriria a janela que o pinning fecha: o proximo boot aceitaria
 *     qualquer chave que respondesse no endereco configurado.
 *   - `atlans-root.crt` / `atlans-ca-bundle.crt` — trust store da CA interna,
 *     montado pelo `_ca_bootstrap`. Nao tem relacao com a identidade do
 *     executor e rebaixa-lo so custa um download a mais.
 */
const ARQUIVOS_DE_IDENTIDADE = [
  'cert.pem', 'chain.pem', 'ca.pem', 'key.pem', 'x25519_key.pem',
]

export interface EstadoConfiguracao {
  configurado: boolean
  executorId: string | null
  /** Passo que falta — espelha o `step` do evento `state: failed`. */
  falta: 'config' | 'enrollment' | null
}

export function lerConfiguracao(): EstadoConfiguracao {
  const env = lerEnv()
  const executorId = (env.EXECUTOR_ID || '').trim() || null
  const temCertificado = CERT_OBRIGATORIOS.every((f) => fs.existsSync(path.join(CERT_DIR, f)))

  return {
    configurado: Boolean(executorId) && temCertificado,
    executorId,
    falta: !executorId ? 'config' : !temCertificado ? 'enrollment' : null,
  }
}

/**
 * Descarta o certificado atual para que um enrollment novo possa ser feito.
 *
 * Necessario porque o enrollment nao e idempotente do ponto de vista do
 * servidor: um executor revogado ou removido continua com cert valido em disco,
 * e o executor sobe, conecta e leva um close 4404 — indefinidamente. Sem apagar
 * o material, o formulario de vinculo nem apareceria (`lerConfiguracao` diria
 * "configurado").
 *
 * O `EXECUTOR_ID` do `.env` e PRESERVADO: vira o valor inicial do formulario.
 * Quando o executor foi recriado no servidor o ID muda, e o usuario o
 * substitui; quando foi apenas revogado, ele continua valendo.
 */
export function descartarEnrollment(): { removidos: string[] } {
  const removidos: string[] = []
  for (const nome of ARQUIVOS_DE_IDENTIDADE) {
    const alvo = path.join(CERT_DIR, nome)
    if (!fs.existsSync(alvo)) continue
    try {
      fs.rmSync(alvo, { force: true })
      removidos.push(nome)
    } catch {
      // Arquivo em uso por um executor que ainda nao encerrou. Quem chama para
      // o processo antes; se mesmo assim falhar, o enrollment seguinte
      // sobrescreve.
    }
  }
  return { removidos }
}

// ── GeoSync ──────────────────────────────────────────────────────────────────

/**
 * Uma pasta, não uma lista.
 *
 * `EXECUTOR_SYNC_DIRS` aceita várias separadas por vírgula, mas o GeoSync
 * sincroniza tudo contra UM workspace: várias pastas despejam árvores
 * diferentes no mesmo Drive, e o mapeamento de volta (Drive → qual pasta?)
 * fica ambíguo assim que dois arquivos coincidem de nome. Uma pasta raiz
 * mantém a correspondência um-para-um.
 */
export interface ConfigGeoSync {
  pasta: string | null
  modo: ModoSync
  conflito: EstrategiaConflito
  workspaceId: string | null
}

export function lerGeoSync(): ConfigGeoSync {
  const env = lerEnv()
  const modo = env.EXECUTOR_SYNC_MODE as ModoSync
  const conflito = env.EXECUTOR_SYNC_CONFLICT_STRATEGY as EstrategiaConflito

  return {
    // Só a primeira entra: um `.env` com várias pastas (editado à mão, ou
    // vindo de uma configuração anterior) não deve fazer a tela mostrar algo
    // que ela não consegue representar.
    pasta: (env.EXECUTOR_SYNC_DIRS ?? '').split(',').map((p) => p.trim()).filter(Boolean)[0] ?? null,
    // Sem valor válido, o que o executor usa — ver PADRAO_SYNC.
    modo: MODOS_SYNC.includes(modo) ? modo : PADRAO_SYNC.modo,
    conflito: ESTRATEGIAS.includes(conflito) ? conflito : PADRAO_SYNC.conflito,
    workspaceId: (env.EXECUTOR_WORKSPACE_ID || '').trim() || null,
  }
}

/** Pasta rejeitada na gravação. Ver `validarPasta`. */
export interface PastaInvalida { caminho: string; motivo: string }

/**
 * `EXECUTOR_SYNC_DIRS` é uma lista separada por VÍRGULA, e o Python a divide
 * cegamente (`config.py`: `SYNC_DIRS.split(",")`). Uma pasta com vírgula no nome
 * viraria duas entradas inexistentes, e o GeoSync sincronizaria nada sem dizer
 * por quê. Barrar na UI é o único ponto em que dá para explicar isso.
 */
export function validarPasta(pasta: string | null): PastaInvalida | null {
  if (!pasta) return null
  if (pasta.includes(',')) {
    return { caminho: pasta, motivo: 'o caminho contém vírgula, que separa as pastas na configuração' }
  }
  if (!fs.existsSync(pasta)) return { caminho: pasta, motivo: 'a pasta não existe' }
  return null
}

export function gravarGeoSync(cfg: ConfigGeoSync): void {
  gravarEnv({
    EXECUTOR_SYNC_DIRS: cfg.pasta ?? '',
    EXECUTOR_SYNC_MODE: cfg.modo,
    EXECUTOR_SYNC_INTERVAL: String(INTERVALO_SYNC),
    EXECUTOR_SYNC_CONFLICT_STRATEGY: cfg.conflito,
    // Vazio e valido: significa "auto-detectar", que e o que o executor faz
    // quando ha exatamente um workspace acessivel.
    EXECUTOR_WORKSPACE_ID: cfg.workspaceId ?? '',
  })
}

// ── Execução ─────────────────────────────────────────────────────────────────

/**
 * O servidor não está aqui: ele é a constante {@link SERVIDOR}, e por isso não
 * é ajuste. Ver o cabeçalho de `shared/servidor.ts`.
 */
export interface ConfigExecucao {
  workers: number
  filaMax: number
  timeoutS: number
  artifactsDir: string
  nivelLog: NivelLog
}

export type NivelLog = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR'
export const NIVEIS_LOG: NivelLog[] = ['DEBUG', 'INFO', 'WARNING', 'ERROR']

/**
 * Os números passam pelas faixas de `shared/limites.ts`, o espelho das de
 * `executor/config.py`: o Python descarta o valor fora da faixa e cai no
 * padrão, então aceitar outro aqui faria a UI mostrar 500 workers com o
 * executor rodando 4, sem nada explicando a diferença.
 */
export function lerExecucao(artifactsDirPadrao: string): ConfigExecucao {
  const env = lerEnv()
  const nivel = (env.LOG_LEVEL || '').toUpperCase() as NivelLog
  return {
    workers: inteiroDoEnv(env.EXECUTOR_MAX_CONCURRENT, LIMITES.workers),
    filaMax: inteiroDoEnv(env.EXECUTOR_MAX_QUEUE_SIZE, LIMITES.filaMax),
    timeoutS: inteiroDoEnv(env.EXECUTOR_JOB_TIMEOUT, LIMITES.timeoutS),
    artifactsDir: (env.EXECUTOR_ARTIFACTS_DIR || '').trim() || artifactsDirPadrao,
    nivelLog: NIVEIS_LOG.includes(nivel) ? nivel : 'INFO',
  }
}

export function gravarExecucao(cfg: ConfigExecucao): void {
  gravarEnv({
    EXECUTOR_MAX_CONCURRENT: String(inteiroDoEnv(String(cfg.workers), LIMITES.workers)),
    EXECUTOR_MAX_QUEUE_SIZE: String(inteiroDoEnv(String(cfg.filaMax), LIMITES.filaMax)),
    EXECUTOR_JOB_TIMEOUT: String(inteiroDoEnv(String(cfg.timeoutS), LIMITES.timeoutS)),
    EXECUTOR_ARTIFACTS_DIR: cfg.artifactsDir.trim(),
    // Reafirmado a cada gravação, e não lido de `cfg`: se alguém editou o
    // `.env` à mão para outro endereço, salvar qualquer ajuste devolve o
    // arquivo ao servidor correto em vez de preservar a alteração.
    EXECUTOR_SERVER_URL: SERVIDOR,
    LOG_LEVEL: NIVEIS_LOG.includes(cfg.nivelLog) ? cfg.nivelLog : 'INFO',
  })
}

/**
 * Diretório de artefatos que o spawn deve usar.
 *
 * O `.env` vence sobre o padrão: sem isto, configurar a pasta na tela de
 * Ajustes gravava o valor mas o executor continuava escrevendo no diretório
 * padrão — o usuário mudaria e nada aconteceria.
 */
export function artifactsDirEfetivo(padrao: string): string {
  return (lerEnv().EXECUTOR_ARTIFACTS_DIR || '').trim() || padrao
}

export function lerEnv(): Record<string, string> {
  if (!fs.existsSync(ENV_FILE)) return {}
  const valores: Record<string, string> = {}
  for (const linha of fs.readFileSync(ENV_FILE, 'utf8').split(/\r?\n/)) {
    const t = linha.trim()
    if (!t || t.startsWith('#')) continue
    const i = t.indexOf('=')
    if (i <= 0) continue
    const chave = t.slice(0, i).trim()
    let valor = t.slice(i + 1).trim()
    // dotenv aceita valor entre aspas e comentario no fim da linha (` # ...`,
    // com espaco antes); tira os dois para que a comparacao e o uso batam com
    // o que o Python enxerga. Sem isto, `EXECUTOR_SYNC_MODE=bidirectional # x`
    // nao era reconhecido, a tela caia no padrao e salvar o GeoSync trocava o
    // modo do executor.
    const entreAspas = /^(["'])(.*)\1(?:\s+#.*)?$/.exec(valor)
    valor = entreAspas ? entreAspas[2]! : valor.replace(/\s+#.*$/, '')
    valores[chave] = valor
  }
  return valores
}

/**
 * Grava (ou atualiza) chaves no `.env`, idempotente.
 *
 * Regras, iguais as de `_env_utils.persist_env_var`:
 *   - chave existente e reescrita NO LUGAR, mantendo a posicao no arquivo;
 *   - chave nova vai para o fim;
 *   - comentarios e linhas em branco sobrevivem;
 *   - uma chave comentada (`# EXECUTOR_X=`) NAO conta como existente.
 */
export function gravarEnv(valores: Record<string, string>): void {
  fs.mkdirSync(path.dirname(ENV_FILE), { recursive: true })

  const original = fs.existsSync(ENV_FILE) ? fs.readFileSync(ENV_FILE, 'utf8') : ''
  const linhas = original ? original.split(/\r?\n/) : []
  const pendentes = new Map(Object.entries(valores))

  const saida = linhas.map((linha) => {
    const t = linha.trim()
    if (!t || t.startsWith('#')) return linha
    const i = t.indexOf('=')
    if (i <= 0) return linha
    const chave = t.slice(0, i).trim()
    if (!pendentes.has(chave)) return linha
    const novo = `${chave}=${pendentes.get(chave)}`
    pendentes.delete(chave)
    return novo
  })

  if (pendentes.size) {
    // Um arquivo que termina em `\n` produz um elemento vazio no fim do split.
    // Empurrar a chave nova depois dele criaria uma linha em branco — e outra a
    // cada escrita seguinte, ate o `.env` ficar cheio de vazios. Sao removidos
    // so no FIM: linhas em branco no meio separam secoes e sao intencionais.
    while (saida.length && saida[saida.length - 1]!.trim() === '') saida.pop()
    for (const [chave, valor] of pendentes) saida.push(`${chave}=${valor}`)
  }

  // Arquivo sempre termina em quebra de linha: sem isso, a proxima chave
  // adicionada gruda na ultima linha e vira `A=1B=2`.
  const texto = saida.join('\n').replace(/\n*$/, '\n')
  fs.writeFileSync(ENV_FILE, texto, { encoding: 'utf8', mode: 0o600 })
}
