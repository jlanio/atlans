import { create } from 'zustand'

// Colunas conhecidas por nó — a memória que alimenta "Vistas na última
// execução" nos campos que pedem nome de coluna.
//
// Vive numa store PRÓPRIA, fora da workflowExecutionStore, de propósito: o
// ciclo de vida é outro. O estado de execução nasce e morre com o run
// (`startExecution`/`resetExecution` zeram tudo, e devem zerar); as colunas
// são conhecimento acumulado sobre o WORKFLOW — clicar em Executar de novo,
// um erro de save ou a troca de aba não muda o que a última execução viu.
// Enquanto as colunas moravam no `statusWorkflow`, cada um dos ~6 caminhos de
// reset as apagava e a sugestão parecia funcionar "às vezes".
//
// O que zera esta store é UMA coisa só: abrir OUTRO workflow. Node ids são
// UUIDs, mas um workflow duplicado herda os ids do original — sem o corte por
// workflow, as colunas de A apareceriam como sugestão em B.

export interface ColunasDoNo {
  /** Colunas por porta de saída — o mesmo formato de `output_columns` que o
   *  executor publica no evento e grava no `node_stats`. `{}` é uma LÁPIDE:
   *  o nó completou ao vivo SEM publicar colunas, e a ausência é informação
   *  (impede a semeadura atrasada de ressuscitar dado mais velho). */
  porPorta: Record<string, string[]>
  /** Run de onde vieram. Rastreio para depuração, não identidade. */
  runId: string | null
  /** true  = vistas AO VIVO nesta sessão (evento de run);
   *  false = re-hidratadas do último run persistido — podem estar
   *          desatualizadas, e o rótulo da sugestão diz isso. */
  fresh: boolean
  /** true quando o stat de origem veio truncado (corte de 8KB do executor
   *  reduz cada lista às primeiras 50) — o rótulo avisa "lista parcial" em
   *  vez de afirmar completude. Só a re-hidratação sabe disso; evento ao
   *  vivo não carrega a marca. */
  parciais?: boolean
}

interface KnownColumnsState {
  /** Workflow dono das entradas de `porNo`. */
  workflowId: string | null
  porNo: Map<string, ColunasDoNo>
}

interface KnownColumnsActions {
  /** Chamado na troca/abertura de workflow: limpa se o workflow mudou, e NÃO
   *  toca em nada se é o mesmo — reabrir a mesma tela não apaga memória. */
  prepararParaWorkflow(workflowId: string | null): void
  /**
   * Escritas de um run AO VIVO, em lote (uma por quadro, como o resto do
   * pipeline de eventos). `porPorta === null` significa que o nó COMPLETOU sem
   * publicar colunas — saída não-tabular, ou a chave cortada no transporte — e
   * a entrada vira uma LÁPIDE (`porPorta: {}`, `fresh: true`): a sugestão para
   * de afirmar colunas que a última execução não produziu, e a lápide impede a
   * semeadura atrasada do run ANTERIOR de ressuscitá-las (um delete deixava o
   * resultado depender de qual resposta de rede chegasse por último).
   */
  aplicarDeExecucao(
    workflowId: string,
    runId: string,
    mudancas: Map<string, Record<string, string[]> | null>,
  ): void
  /**
   * Semeadura a partir do `node_stats` do último run persistido, na abertura
   * do workflow. Entra como `fresh: false` e NUNCA sobrescreve uma entrada
   * `fresh: true` (lápides incluídas) — se um run ao vivo já escreveu (a
   * resposta da API chegou atrasada), o dado mais novo vence.
   */
  semearDoHistorico(
    workflowId: string,
    runId: string,
    colunasPorNo: Record<string, { porPorta: Record<string, string[]>; parciais?: boolean }>,
  ): void
}

const VAZIO: Map<string, ColunasDoNo> = new Map()

export const useKnownColumnsStore = create<KnownColumnsState & KnownColumnsActions>((set) => ({
  workflowId: null,
  porNo: VAZIO,

  prepararParaWorkflow: (workflowId) => {
    set(state => (state.workflowId === workflowId
      ? state
      : { workflowId, porNo: new Map() }))
  },

  aplicarDeExecucao: (workflowId, runId, mudancas) => {
    if (mudancas.size === 0) return
    set(state => {
      // Escrita de outro workflow (rAF atrasado após a troca): recomeça só com
      // o que chegou — o filtro por run em `drenarLote` já barra quase tudo,
      // este é o cinto de segurança.
      const base = state.workflowId === workflowId ? state.porNo : VAZIO
      const porNo = new Map(base)
      for (const [nodeId, porPorta] of mudancas) {
        porNo.set(nodeId, { porPorta: porPorta ?? {}, runId, fresh: true })
      }
      return { workflowId, porNo }
    })
  },

  semearDoHistorico: (workflowId, runId, colunasPorNo) => {
    set(state => {
      // Resposta ATRASADA de outro workflow: ignora. A escrita ao vivo pode
      // adotar o workflow (o evento prova que é ele que está rodando); uma
      // resposta de API antiga não prova nada — virar a store por ela
      // colocaria as colunas de A na tela de B.
      if (state.workflowId !== null && state.workflowId !== workflowId) return state
      const porNo = new Map(state.porNo)
      for (const [nodeId, { porPorta, parciais }] of Object.entries(colunasPorNo)) {
        // Run ao vivo já escreveu neste nó (lápide incluída): a resposta da
        // API é mais velha.
        if (porNo.get(nodeId)?.fresh) continue
        porNo.set(nodeId, { porPorta, runId, fresh: false, parciais: !!parciais })
      }
      return { workflowId, porNo }
    })
  },
}))
