// desktop/src/shared/ipc.ts
//
// Contrato entre o main process e o renderer. Fonte da verdade dos nomes de
// canal: o preload, o main e o renderer importam DAQUI, entao renomear um canal
// quebra a compilacao em vez de virar um handler que nunca dispara.
import type { CommandName } from './events.js'
import type { EstadoApp, LoteLog } from '../main/state/store.js'
import type { ConfigExecucao, ConfigGeoSync, EstadoConfiguracao, PastaInvalida } from '../main/state/config.js'
import type { PedidoDeepLink } from '../main/deeplink.js'
import type { ResultadoStatus } from '../main/python/status.js'
import type { PedidoEnroll, ResultadoEnroll } from '../main/python/enroll.js'
import type { EstadoAutostart } from '../main/ui/autostart.js'

export const CANAIS = {
  /** renderer -> main, com resposta. */
  estado: 'atlas:estado',
  iniciar: 'atlas:iniciar',
  parar: 'atlas:parar',
  reiniciar: 'atlas:reiniciar',
  forcar: 'atlas:forcar',
  comando: 'atlas:comando',
  info: 'atlas:info',
  configuracao: 'atlas:configuracao',
  enrolar: 'atlas:enrolar',
  refazerEnrollment: 'atlas:refazer-enrollment',
  escolherPasta: 'atlas:escolher-pasta',
  abrirCaminho: 'atlas:abrir-caminho',
  autostart: 'atlas:autostart',
  janela: 'atlas:janela',
  geosync: 'atlas:geosync',
  salvarGeosync: 'atlas:salvar-geosync',
  workspaces: 'atlas:workspaces',
  deepLinkPendente: 'atlas:deep-link-pendente',
  execucao: 'atlas:execucao',
  salvarExecucao: 'atlas:salvar-execucao',
  exportarLog: 'atlas:exportar-log',
  abrirJanelaLog: 'atlas:abrir-janela-log',
  log: 'atlas:log',

  /** main -> renderer, push. */
  aoAtualizarEstado: 'atlas:estado-mudou',
  aoReceberDeepLink: 'atlas:deep-link',
  aoReceberLog: 'atlas:log-lote',
} as const

export const ACOES_JANELA = ['minimizar', 'alternar-maximizar', 'fechar', 'esta-maximizada'] as const
export type AcaoJanela = (typeof ACOES_JANELA)[number]

export interface InfoApp {
  versao: string
  versaoElectron: string
  envFile: string
  certDir: string
  logDir: string
  artifactsDir: string
  dev: boolean
}

/** Superficie exposta ao renderer pelo preload, via contextBridge. */
export interface AtlasApi {
  estado(): Promise<EstadoApp>
  info(): Promise<InfoApp>
  configuracao(): Promise<EstadoConfiguracao>
  /** Roda o enrollment. Em caso de sucesso o executor é iniciado em seguida. */
  enrolar(pedido: PedidoEnroll): Promise<ResultadoEnroll>
  /**
   * Para o executor e descarta o certificado atual, devolvendo o app ao
   * formulário de vínculo. Usado quando o servidor revogou ou removeu o
   * executor — o certificado em disco continua válido localmente, mas inútil.
   */
  refazerEnrollment(): Promise<EstadoConfiguracao>
  iniciar(): Promise<void>
  /**
   * Pede o shutdown ordenado e VOLTA na hora.
   *
   * Não espera a drenagem: ela leva até 150 s, e segurar a promessa até lá
   * mantinha a janela inteira em "ocupado" — inclusive os botões "Forçar", que
   * são a única saída da espera. O progresso chega sozinho pela assinatura de
   * estado (`supervisor: 'draining'` + `running_count` dos snapshots).
   */
  parar(): Promise<void>
  /**
   * Para e sobe de novo, nesta ordem. Resolve quando o executor voltou.
   *
   * Existe porque o sequenciamento não cabe mais no renderer: com `parar`
   * retornando na hora, um `parar()` seguido de `iniciar()` do outro lado
   * chamaria `start()` com o processo antigo ainda vivo — e ele sairia sem
   * fazer nada, deixando o executor parado depois da drenagem.
   */
  reiniciar(): Promise<void>
  forcar(): Promise<void>
  comando(cmd: CommandName): Promise<boolean>
  escolherPasta(atual?: string): Promise<string | null>
  abrirCaminho(caminho: string): Promise<void>
  /**
   * Lê (sem argumento) ou define o "iniciar com o Windows".
   *
   * Devolve o estado RELIDO do registro, não o pedido: a escrita pode ser
   * bloqueada por política de grupo, e o item pode estar desativado no
   * Gerenciador de Tarefas mesmo com a entrada presente.
   */
  autostart(ativar?: boolean): Promise<EstadoAutostart>
  /**
   * Controles da janela sem moldura. `fechar` esconde em vez de encerrar — o
   * app vive no tray e o executor continua rodando.
   */
  janela(acao: AcaoJanela): Promise<boolean>

  geosync(): Promise<ConfigGeoSync>
  /** Grava e devolve as pastas rejeitadas — vazio significa que salvou tudo. */
  salvarGeosync(cfg: ConfigGeoSync): Promise<{ salvo: boolean; invalidas: PastaInvalida[] }>
  /**
   * Workspaces acessíveis a este executor.
   *
   * A consulta spawna um segundo interpretador Python e fala com o servidor por
   * mTLS — vários segundos, até 30 com a rede ruim. Por isso o resultado é
   * guardado no main pela sessão: `atualizar: true` (o botão "Atualizar" da
   * tela) é o que força a consulta de novo.
   */
  workspaces(atualizar?: boolean): Promise<ResultadoStatus>
  /** Pedido de vínculo que chegou antes do renderer montar. Consumido uma vez. */
  deepLinkPendente(): Promise<PedidoDeepLink | null>

  execucao(): Promise<ConfigExecucao>
  salvarExecucao(cfg: ConfigExecucao): Promise<ConfigExecucao>
  /** Salva o log visível num arquivo escolhido pelo usuário. Devolve o caminho. */
  exportarLog(texto: string): Promise<string | null>
  /**
   * Abre (ou traz para frente) uma janela só com o log.
   *
   * Serve para acompanhar o log ao lado de outra coisa — o painel do app, o
   * Studio no navegador, um editor. Numa janela só, ler o log significa perder
   * de vista todo o resto.
   */
  abrirJanelaLog(): Promise<void>

  /**
   * Buffer de log completo. Usado uma vez, quando a janela monta.
   *
   * O log NÃO viaja no estado: ele é append-only e grande, e mandá-lo inteiro a
   * cada mudança custava ~150-200 KB por janela por broadcast. Ver o cabeçalho
   * de `main/state/store.ts`.
   */
  log(): Promise<LoteLog>

  /** Retornam a funcao de cancelamento — o renderer precisa dela no cleanup. */
  aoAtualizarEstado(fn: (e: EstadoApp) => void): () => void
  /** Só as linhas NOVAS desde o último lote. */
  aoReceberLog(fn: (lote: LoteLog) => void): () => void
  /** Vínculo pedido por `atlans://enroll?…`. O app NUNCA enrola sozinho:
   *  o formulário é preenchido e a confirmação é do usuário. */
  aoReceberDeepLink(fn: (p: PedidoDeepLink) => void): () => void
}

declare global {
  interface Window {
    atlas: AtlasApi
  }
}
