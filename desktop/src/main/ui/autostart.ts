// desktop/src/main/ui/autostart.ts
//
// Iniciar junto com o Windows.
//
// Usa `setLoginItemSettings`, que escreve em
// HKCU\Software\Microsoft\Windows\CurrentVersion\Run — sem privilegio de
// administrador e sem tarefa agendada.
//
// Deliberadamente NAO e um Servico do Windows: servico roda fora da sessao do
// usuario, e o GeoSync precisa dela — unidades de rede mapeadas, `%USERPROFILE%`
// e as permissoes de quem de fato usa os arquivos. Um servico tambem exigiria
// instalacao com elevacao, que e o que o instalador per-user evita.
//
// ## Duas armadilhas da API, ambas comprovadas na maquina
//
// 1. **`openAtLogin` compara os ARGUMENTOS.** `getLoginItemSettings()` sem
//    opcoes assume `args: []`, e o comando gravado aqui termina em `--hidden`.
//    A leitura devolvia `false` com a entrada gravada e correta no registro —
//    o resultado era um checkbox que ligava e voltava sozinho. Toda leitura
//    precisa usar o MESMO `path`/`args` da escrita.
//
// 2. **`openAtLogin` ignora a desativacao do Gerenciador de Tarefas.** O
//    usuario pode desligar o item em Inicializar; a entrada continua no
//    registro (`openAtLogin: true`) e o app simplesmente nao sobe.
//    `executableWillLaunchAtLogin` e quem responde "vai executar de verdade?".
//
// O nome da entrada no registro e o AppUserModelID (`app.atlans.executor`,
// definido no index.ts) — trocar aquele ID orfana esta entrada.
import { app } from 'electron'

/** Faz o app subir sem janela: so tray + spawn do executor. */
export const ARG_OCULTO = '--hidden'

export function iniciadoOculto(): boolean {
  return process.argv.includes(ARG_OCULTO)
}

export interface EstadoAutostart {
  /** A entrada existe e o comando bate exatamente com o deste app. */
  ativo: boolean
  /**
   * O Windows vai MESMO executar no logon.
   *
   * Difere de `ativo` quando o item foi desativado em Gerenciador de Tarefas →
   * Inicializar: a entrada continua no registro, mas nao roda.
   */
  efetivo: boolean
  /** O comando que fica no registro. Exibido na UI para nao ser magica. */
  comando: string
  /** Rodando por `npm run dev` — ver a nota em `alvo()`. */
  dev: boolean
  /** Mensagem quando o registro recusou a escrita (politica de grupo, AV). */
  erro: string | null
}

/**
 * Executavel e argumentos da entrada de logon.
 *
 * Em dev o executavel e o `electron.exe` do node_modules, e sem o caminho do
 * projeto o Windows subiria o app PADRAO do Electron a cada logon — uma janela
 * cinza que nao tem relacao nenhuma com o Atlans, e que sobreviveria ao fim do
 * `npm run dev`. Mesmo tratamento de `registrarProtocolo` em deeplink.ts.
 */
function alvo(): { path: string; args: string[] } {
  if (process.defaultApp && process.argv.length >= 2) {
    return { path: process.execPath, args: [process.argv[1]!, ARG_OCULTO] }
  }
  return { path: process.execPath, args: [ARG_OCULTO] }
}

function comandoDe({ path, args }: { path: string; args: string[] }): string {
  return [path.includes(' ') ? `"${path}"` : path, ...args].join(' ')
}

/**
 * Ultima leitura do registro.
 *
 * `getLoginItemSettings` e consulta SINCRONA a HKCU\...\Run (e a StartupApproved,
 * para `executableWillLaunchAtLogin`), e o tray a chamava a cada atualizacao de
 * estado — pelo menos uma vez por segundo com o executor rodando, e ate doze
 * numa rajada de ERROR. I/O sincrono no thread que atende janelas, bandeja e
 * IPC, para um valor que so muda quando o proprio usuario clica no menu da
 * bandeja ou no checkbox de Ajustes.
 */
let cache: EstadoAutostart | null = null

/** Le do registro de fato e repovoa o cache. */
export function lerAutostart(): EstadoAutostart {
  const a = alvo()
  const base = { comando: comandoDe(a), dev: Boolean(process.defaultApp) }
  try {
    // Os MESMOS path/args da escrita — ver a armadilha 1 no cabecalho.
    const s = app.getLoginItemSettings(a)
    cache = { ...base, ativo: s.openAtLogin, efetivo: s.executableWillLaunchAtLogin, erro: null }
  } catch (e) {
    cache = { ...base, ativo: false, efetivo: false, erro: (e as Error).message }
  }
  return cache
}

/**
 * O booleano do menu da bandeja, servido do cache.
 *
 * O unico jeito de este valor mudar por fora do app e o usuario desativar a
 * entrada no Gerenciador de Tarefas — que ja hoje nao aparecia sem reabrir a
 * tela de Ajustes, e ela continua forcando releitura pelo IPC.
 */
export function autostartAtivo(): boolean {
  return (cache ?? lerAutostart()).ativo
}

/**
 * Liga ou desliga, e devolve o estado RELIDO do registro.
 *
 * Reler em vez de confiar no pedido: se a escrita foi bloqueada (politica de
 * grupo, antivirus), a UI precisa mostrar o estado real, e nao o desejado. A
 * releitura tambem e o que repovoa o cache com o valor RELIDO — este e o unico
 * caminho pelo qual o autostart muda com o app aberto.
 */
export function definirAutostart(ativar: boolean): EstadoAutostart {
  const a = alvo()
  try {
    app.setLoginItemSettings({ openAtLogin: ativar, path: a.path, args: a.args })
  } catch (e) {
    return { ...lerAutostart(), erro: (e as Error).message }
  }
  return lerAutostart()
}
