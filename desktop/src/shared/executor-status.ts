// desktop/src/shared/executor-status.ts
//
// O status REDIGIDO do executor local que a janela web pode ler.
//
// Este é o único dado que atravessa a ponte do preload/web.ts (main → web, só
// leitura). Ele existe para a UI web, rodando DENTRO do app desktop, poder
// dizer "o executor deste computador está online" — algo que ela não sabe pela
// ótica do servidor, que enxerga os executores da conta mas não qual deles é a
// máquina à frente do usuário.
//
// `derivarStatus` é o ÚNICO ponto que serializa para a ponte: tudo o que sai
// passa por aqui, então a redação (o que é seguro expor) fica revisável num só
// lugar. Nada além destes campos cruza — sem certificado, OTP, server_url,
// caminhos, log, métricas de recurso ou histórico.
import type { EstadoApp } from '../main/state/store.js'
import type { EstadoConfiguracao } from '../main/state/config.js'

/** Canais IPC da ponte. Fonte única para o preload e o main (como ipc.ts). */
export const CANAIS_WEB = {
  /** web → main, com resposta: o status atual (usado no primeiro render). */
  status: 'atlas-web:executor-status',
  /** main → web, push: novo status quando a assinatura muda. */
  statusMudou: 'atlas-web:executor-status-mudou',
} as const

export type EstadoExecutorLocal = 'online' | 'ocupado' | 'offline' | 'sem-vinculo'

export interface StatusExecutorLocal {
  /** Sobe se o formato mudar; a web faz feature-detect por cima disto. */
  versaoContrato: 1
  /**
   * Identidade PÚBLICA deste executor — o mesmo `id_hash` que o servidor já
   * mostra ao usuário logado (é o `executor_id` do enrollment). Deixa a web
   * casar "este computador" com a linha da lista de Executores. Não é segredo:
   * os segredos são o certificado e o OTP, que nunca cruzam.
   */
  executorId: string | null
  vinculado: boolean
  estado: EstadoExecutorLocal
  emExecucao: number
  capacidade: number | null
}

/**
 * Deriva o status público a partir do estado vivo + a configuração.
 *
 * Espelha a lógica de `estadoDoIcone` da bandeja e acrescenta o caso
 * "sem-vinculo" (sem enrollment não há executor a mostrar). `emExecucao` só é
 * significativo quando online/ocupado — fora disso é 0, para a UI nunca dizer
 * "offline · 2 em execução".
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
 * Chave curta para deduplicar broadcasts.
 *
 * O estado do executor é reavaliado a cada tick (≈12 Hz com o executor ativo),
 * mas o que a ponte carrega muda raramente. Comparar a assinatura evita mandar
 * um structured clone à janela a cada tick por nada — mesma guarda da bandeja.
 */
export function assinaturaStatus(s: StatusExecutorLocal): string {
  return [s.estado, s.executorId ?? '', s.emExecucao, s.capacidade ?? '', s.vinculado ? 1 : 0].join('|')
}
