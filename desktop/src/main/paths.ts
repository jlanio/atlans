// desktop/src/main/paths.ts
//
// Onde tudo mora.
//
// Regra central: **nada do usuario e gravado no diretorio de instalacao.** Ele e
// substituido inteiro a cada atualizacao, e o que estivesse la (config, certs,
// artefatos) sumiria — ou pior, sobreviveria como orfao que o desinstalador nao
// remove. O executor ja expoe as variaveis para redirecionar tudo isso
// (executor/config.py); aqui so apontamos para o perfil do usuario.
import { app } from 'electron'
import fs from 'node:fs'
import path from 'node:path'
import { SERVIDOR } from '../shared/servidor.js'

/**
 * O nome e definido AQUI, no topo do modulo que le `getPath('userData')`, e nao
 * no index.ts.
 *
 * Isso nao e estilo: `import` em ESM e avaliado ANTES de qualquer instrucao de
 * topo do modulo importador. Um `app.setName()` na primeira linha do index.ts
 * roda DEPOIS deste modulo ja ter calculado `USER_DATA` — e o nome usado seria
 * o `productName` do package.json, levando os dados do usuario para uma pasta
 * diferente da documentada.
 *
 * Estar no mesmo modulo que le o caminho torna a ordem impossivel de quebrar.
 */
app.setName('AtlansExecutor')

/**
 * Nomes de pasta usados por versoes anteriores, migrados uma unica vez.
 *
 * `AtlasExecutor` e `Atlas Executor` (sem o "n") vem de uma grafia errada do
 * nome da plataforma; os com espaco vem do periodo em que o `setName` nao
 * surtia efeito e o Electron caia no `productName`. (A lista chegou a trazer
 * o proprio `AtlansExecutor` no lugar do nome sem o "n" — um renomear em massa
 * que alcancou a propria lista de nomes antigos — e a migracao nunca achava a
 * pasta velha.)
 *
 * A migracao existe porque a pasta guarda o CERTIFICADO mTLS: perde-la
 * significa refazer o enrollment, o que exige um OTP novo gerado por um admin.
 * Renomear e barato; obrigar o usuario a isso, nao.
 */
const NOMES_ANTIGOS = ['AtlasExecutor', 'Atlas Executor', 'Atlans Executor']

/** Em dev os recursos vem da raiz do repo; empacotado, de resources/. */
export const IS_DEV = !app.isPackaged

/**
 * Raiz do codigo do app — `desktop/` em dev, `resources/app.asar` empacotado.
 *
 * Usado no lugar de `import.meta.dirname` porque o main e o preload sao
 * empacotados como **CJS** (o preload com `sandbox: true` so aceita CJS), e em
 * CJS `import.meta.dirname` e `undefined`. O esbuild avisa, mas o efeito so
 * apareceria em runtime, no app empacotado, como `path.join(undefined, ...)`.
 */
export const APP_PATH = app.getAppPath()

export const arquivoDoApp = (...partes: string[]): string => path.join(APP_PATH, ...partes)

/**
 * Raiz do payload Python: `resources/{python,executor,flow}`.
 *
 * O layout NAO e arbitrario — executor/job_executor.py insere o diretorio-pai
 * de `executor/` no sys.path para importar `flow.executor`, entao `flow/`
 * precisa ser irmao de `executor/`. E tambem o valor de `cwd` e `PYTHONPATH`
 * do spawn.
 */
export const RESOURCES = IS_DEV
  ? path.resolve(app.getAppPath(), '..')      // desktop/ -> raiz do repo
  : process.resourcesPath

export const PYTHON_EXE = IS_DEV
  // Em dev usamos o runtime empacotado se ele existir (npm run runtime), e
  // caimos no Python do sistema se nao — assim da para iterar na UI sem
  // reconstruir 390 MB a cada mudanca.
  ? resolverPythonDev()
  : path.join(RESOURCES, 'python', 'python.exe')

function resolverPythonDev(): string {
  const embarcado = path.join(app.getAppPath(), 'resources', 'python', 'python.exe')
  return fs.existsSync(embarcado) ? embarcado : 'python'
}

/** `%APPDATA%\AtlansExecutor` — definido por app.setName() no boot. */
export const USER_DATA = app.getPath('userData')

export const CONFIG_DIR = path.join(USER_DATA, 'config')
export const ENV_FILE = path.join(CONFIG_DIR, '.env')
export const CERT_DIR = path.join(USER_DATA, 'certs')
export const LOG_DIR = path.join(USER_DATA, 'logs')

/**
 * Artefatos vao para o HOME, nao para %APPDATA%: sao arquivos de trabalho do
 * usuario (GeoJSON, GeoParquet, shapefiles), que ele precisa achar no
 * Explorer. Escondê-los em AppData seria hostil. Sobrescrivivel no onboarding.
 */
export const ARTIFACTS_DIR_PADRAO = path.join(app.getPath('home'), 'AtlansExecutor', 'artifacts')

/**
 * Move os dados de uma pasta com nome antigo, se houver. Idempotente.
 *
 * Executada antes de `garantirDiretorios`: uma vez que os diretorios existam,
 * a migracao passa a ser no-op (nao sobrescreve dados atuais com os antigos).
 */
export function migrarDadosAntigos(): string | null {
  if (fs.existsSync(USER_DATA)) return null

  const raiz = path.dirname(USER_DATA)
  for (const antigo of NOMES_ANTIGOS) {
    const origem = path.join(raiz, antigo)
    if (origem === USER_DATA || !fs.existsSync(origem)) continue
    try {
      fs.renameSync(origem, USER_DATA)
      return antigo
    } catch {
      // Pasta em uso, ou permissao. Nao e fatal: o app segue com a pasta nova
      // vazia e o usuario refaz o vinculo.
    }
  }
  return null
}

/**
 * Ícone do app — o mesmo em janela, barra de tarefas, Alt+Tab e bandeja.
 *
 * Precisa ser passado explicitamente à `BrowserWindow`: sem ele, o Windows usa
 * o ícone do EXECUTÁVEL, que em `npm run dev` é o `electron.exe` — a janela
 * abre com o átomo cinza do Electron na barra de tarefas. Empacotado o
 * executável já é o certo, mas declarar aqui faz dev e produção mostrarem a
 * mesma coisa, que é o ponto de ter identidade visual.
 *
 * `.ico` e não `.png`: o formato carrega várias resoluções, e o Windows escolhe
 * a certa para cada contexto em vez de reescalar uma só e serrilhar.
 */
export const ICONE_APP = arquivoDoApp('build', 'icon.ico')

export function garantirDiretorios(): void {
  for (const dir of [CONFIG_DIR, CERT_DIR, LOG_DIR]) {
    fs.mkdirSync(dir, { recursive: true })
  }
}

/**
 * Variaveis que o executor entende, apontadas para o perfil do usuario.
 * Ver o cabecalho de executor/config.py para cada uma.
 */
export function envDoExecutor(artifactsDir: string): Record<string, string> {
  return {
    EXECUTOR_ENV_PATH: ENV_FILE,
    EXECUTOR_CERT_DIR: CERT_DIR,
    EXECUTOR_LOG_DIR: LOG_DIR,
    EXECUTOR_ARTIFACTS_DIR: artifactsDir,
    // O servidor é fixo (ver shared/servidor.ts) e vai por VARIÁVEL DE
    // AMBIENTE, não só pelo `.env`: o `load_dotenv()` do executor não
    // sobrescreve o que já está no ambiente, então mesmo um `.env` editado à
    // mão não consegue apontar esta instalação para outro servidor.
    EXECUTOR_SERVER_URL: SERVIDOR,
    // Versão do INSTALADOR, que é o que de fato define o código rodando aqui.
    //
    // Sem isto o executor cai no default de `executor/config.py` e o servidor
    // veria TODA máquina como "1.0.0" — impossível saber, do painel, quais já
    // receberam uma correção e quais ainda rodam a build antiga.
    EXECUTOR_VERSION: app.getVersion(),
  }
}

/**
 * Ambiente do processo Python.
 *
 * O que e REMOVIDO importa tanto quanto o que e adicionado:
 *
 * - `GDAL_DATA` / `PROJ_LIB` / `PROJ_DATA` / `GDAL_DRIVER_PATH`: numa maquina
 *   com QGIS ou ArcGIS instalado, essas variaveis apontam para os dados
 *   DAQUELA instalacao. O pyogrio/pyproj do bundle carregaria tabelas de
 *   projecao incompativeis com as DLLs que ele empacota, e o sintoma e um
 *   `to_crs()` que devolve coordenada errada em vez de estourar — o pior tipo
 *   de bug. O app antigo fazia `{...process.env}` cru e tinha exatamente essa
 *   classe de "funciona na minha maquina".
 * - `PYTHONHOME` / `PYTHONPATH` / `PYTHONSTARTUP`: apontariam para outro
 *   interpretador.
 * - `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE`: atrapalham o `_ca_bootstrap` do
 *   executor, que monta o proprio trust store combinado.
 * - `EXECUTOR_*` herdadas: o app e a unica fonte de verdade da configuracao.
 */
export function ambienteDoSpawn(extra: Record<string, string>): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = { ...process.env }

  for (const chave of [
    'PYTHONHOME', 'PYTHONPATH', 'PYTHONSTARTUP', 'PYTHONUSERBASE',
    'GDAL_DATA', 'GDAL_DRIVER_PATH', 'PROJ_LIB', 'PROJ_DATA',
    'SSL_CERT_FILE', 'REQUESTS_CA_BUNDLE',
  ]) delete env[chave]

  for (const chave of Object.keys(env)) {
    if (chave.startsWith('EXECUTOR_')) delete env[chave]
  }

  return {
    ...env,
    PYTHONPATH: RESOURCES,
    PYTHONUNBUFFERED: '1',
    PYTHONUTF8: '1',
    PYTHONIOENCODING: 'utf-8',

    // Canal estruturado no stdout. Sem isto o executor tentaria o painel rich
    // (que nao tem terminal) ou cairia em log solto.
    EXECUTOR_DASHBOARD: 'json',
    // Log humano sem escapes ANSI: ele vai para o painel de log da GUI, nao
    // para um terminal que saiba interpreta-los.
    LOG_COLOR: 'never',

    // O restart e responsabilidade DESTE processo. Ver supervisor.ts e a guarda
    // em executor/main.py::_restart_process.
    EXECUTOR_AUTO_RESTART: 'never',
    EXECUTOR_SUPERVISOR_PID: String(process.pid),

    // Espelha Dockerfile.executor: sem o teto, cada job de geoprocessamento
    // abre uma thread por core e o desktop do usuario trava.
    OMP_NUM_THREADS: '1',
    OPENBLAS_NUM_THREADS: '1',
    MKL_NUM_THREADS: '1',
    NUMEXPR_NUM_THREADS: '1',
    GDAL_NUM_THREADS: '1',

    ...extra,
  }
}
