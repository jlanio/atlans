// web/app/components/home/assistente/quadros.ts
//
// Os quadros do assistente: decodificar o `text/event-stream` e transformar cada
// quadro na conversa que o painel desenha.
//
// Puras de propósito. O defeito clássico de quem lê stream é o quadro PARTIDO
// AO MEIO entre dois `read()` — a rede não respeita fronteira de mensagem, e um
// `JSON.parse` em cima de meio quadro derruba a conversa inteira. Isso precisa
// de teste, e testar por dentro de um `fetch` de mentira dentro de um hook
// dentro de um componente é a maneira mais cara de não olhar para o problema.
//
// O contrato dos quadros está em `docs/assistente/editor.md` §"Os quadros do SSE".
import type { CanvasDefinition } from "@/service/types"

export interface QuadroSSE {
  evento: string
  dados: Record<string, unknown>
}

/**
 * Decodificador de quadros SSE, com memória do que sobrou do pedaço anterior.
 *
 * Devolve os quadros COMPLETOS de cada alimentada e guarda o resto — que pode
 * ser meia linha, meio quadro, ou dez quadros e meio.
 */
/**
 * O quadro `cota` — o acumulado da janela depois de cada resposta do modelo,
 * com o teto. Não é bloco de turno: os hooks o interceptam antes de
 * `aplicarQuadro` e atualizam o `estado.cota`, e é assim que o donut sobe
 * DURANTE o turno, sem consultar `/estado`. O servidor só o emite quando há
 * Redis para contar; um quadro malformado vale como nenhum.
 */
export function cotaDoQuadro(quadro: QuadroSSE): { gasto: number; teto: number } | null {
  if (quadro.evento !== "cota") return null
  const { gasto, teto } = quadro.dados
  if (typeof gasto !== "number" || typeof teto !== "number") return null
  if (!Number.isFinite(gasto) || !Number.isFinite(teto) || gasto < 0 || teto <= 0) return null
  return { gasto, teto }
}

export function criarDecodificador() {
  let resto = ""

  return function alimentar(pedaco: string): QuadroSSE[] {
    // Normaliza no acumulado, e não no pedaço: um `\r\n` cortado no meio (o
    // `\r` num pedaço, o `\n` no seguinte) só vira fim de linha depois de
    // juntar os dois.
    resto = (resto + pedaco).replace(/\r\n/g, "\n")

    const partes = resto.split("\n\n")
    resto = partes.pop() ?? ""

    return partes.map(decodificarUm).filter((q): q is QuadroSSE => q !== null)
  }
}

function decodificarUm(bruto: string): QuadroSSE | null {
  let evento = ""
  const dados: string[] = []

  for (const linha of bruto.split("\n")) {
    if (!linha || linha.startsWith(":")) continue // linha vazia ou comentário (heartbeat)

    const corte = linha.indexOf(":")
    const campo = corte === -1 ? linha : linha.slice(0, corte)
    let valor = corte === -1 ? "" : linha.slice(corte + 1)
    if (valor.startsWith(" ")) valor = valor.slice(1)

    if (campo === "event") evento = valor
    else if (campo === "data") dados.push(valor)
  }

  if (!evento || !dados.length) return null

  try {
    const corpo: unknown = JSON.parse(dados.join("\n"))
    // Quadro sem objeto no `data` não é quadro deste servidor. Descartar é
    // melhor que inventar um evento para ele: o fim da conversa não depende do
    // quadro `fim` chegar — quem encerra é o fechamento do stream.
    if (!corpo || typeof corpo !== "object" || Array.isArray(corpo)) return null
    return { evento, dados: corpo as Record<string, unknown> }
  } catch {
    return null
  }
}

// ── A conversa ───────────────────────────────────────────────────────────────

export interface ErroDoAssistente {
  code: string
  message: string
  hint?: string
  /** No `loop_limit`: o teto de voltas da superfície (a frase traduzida o cita). */
  teto?: number
}

export interface PropostaDeFluxo {
  definicao: CanvasDefinition
  nos: number
  arestas: number
  /**
   * `true` quando veio de `desenhar_no_canvas`: é para pôr na tela AGORA, sem
   * botão. `false`/ausente quando veio de `validate_workflow`, que só traz o
   * veredito do que já está desenhado.
   *
   * A distinção existe porque o mesmo quadro serve a dois papéis desde que
   * entregar deixou de ser efeito colateral de validar.
   */
  desenhar?: boolean
  /** Uma linha do modelo sobre o que mudou neste desenho. */
  nota?: string
  /** `null` quando o relatório da validação não pôde ser lido. */
  ok: boolean | null
  erros: number | null
  avisos: number | null
}

export interface Progresso {
  concluidos: number
  total: number | null
  mensagem: string | null
}

// ── Quadros só do assistente da Home ─────────────────────────────────────────
// O editor nunca os emite; são aditivos e o painel do editor os ignora.

/** Um fluxo que o assistente criou — o badge junto do chat abre `/workflow/{id}`. */
export interface FluxoDoAssistente {
  workflow_id: string
  nome: string
}

/** Ponteiro para uma saída no globo; a verdade é `GET /assistente/camadas/{id}`. */
export interface CamadaDoAssistente {
  artifact_id: string
  nome?: string
  format?: string
  available: boolean
  hint?: string
}

/** Uma ação que mexe no que já existia, esperando o clique de confirmação. */
export interface ConfirmacaoDoAssistente {
  tool_use_id: string
  token: string
  acao: { tool: string; argumentos: Record<string, unknown>; alvo?: string }
}

export type BlocoDoAssistente =
  | { tipo: "texto"; texto: string }
  | { tipo: "pensando"; texto: string }
  | {
      tipo: "ferramenta"
      id: string
      nome: string
      argumentos: Record<string, unknown>
      estado: "correndo" | "ok" | "erro"
      progresso?: Progresso
    }
  | { tipo: "proposta"; proposta: PropostaDeFluxo }
  | { tipo: "fluxo"; fluxo: FluxoDoAssistente }
  | { tipo: "camada"; camada: CamadaDoAssistente }
  | { tipo: "confirmacao"; confirmacao: ConfirmacaoDoAssistente }
  // Respostas rápidas do assistente da Home: continuações curtas que a pessoa
  // escolhe com um clique. Valem só para aquela vez — quem as desenha só o faz
  // no último turno, fora do stream.
  | { tipo: "respostas_rapidas"; opcoes: string[] }
  | { tipo: "erro"; erro: ErroDoAssistente }

export interface TurnoDoAssistente {
  id: string
  papel: "user" | "assistant"
  /** Só para `papel: "user"`. O turno do modelo é uma lista de blocos. */
  texto?: string
  blocos: BlocoDoAssistente[]
}

export const turnoVazio = (id: string): TurnoDoAssistente => ({
  id,
  papel: "assistant",
  blocos: [],
})

/**
 * Aplica um quadro ao turno em andamento e devolve o turno novo.
 *
 * Imutável: o painel re-renderiza por identidade, e mutar o turno no lugar
 * faria o React não ver mudança nenhuma num stream inteiro.
 *
 * Os blocos são uma LINHA DO TEMPO, e não campos separados, porque o modelo
 * alterna: pensa, escreve, chama três ferramentas, escreve de novo. Guardar o
 * texto todo num campo só perderia o que veio antes e o que veio depois de cada
 * chamada — que é justamente a explicação que impede alguém de aplicar um fluxo
 * sem entender.
 */
export function aplicarQuadro(turno: TurnoDoAssistente, quadro: QuadroSSE): TurnoDoAssistente {
  const { evento, dados } = quadro

  switch (evento) {
    case "texto":
      return { ...turno, blocos: acumular(turno.blocos, "texto", texto(dados.texto)) }

    case "pensando":
      return { ...turno, blocos: acumular(turno.blocos, "pensando", texto(dados.texto)) }

    case "ferramenta":
      return {
        ...turno,
        blocos: [
          ...turno.blocos,
          {
            tipo: "ferramenta",
            id: String(dados.id ?? ""),
            nome: String(dados.nome ?? ""),
            argumentos: objeto(dados.argumentos),
            estado: "correndo",
          },
        ],
      }

    case "progresso": {
      // Com as ferramentas de uma volta rodando em paralelo, várias estão
      // "correndo" ao mesmo tempo — o quadro traz o `id` da dona e é por ele
      // que a barra acha o card certo. Sem `id` (backend antigo, replay de
      // conversa gravada antes), vale o critério de sempre: a que está correndo.
      const dono = dados.id == null ? null : String(dados.id)
      return {
        ...turno,
        blocos: mapearFerramenta(
          turno.blocos,
          b => (dono !== null ? b.id === dono : b.estado === "correndo"),
          b => ({
            ...b,
            progresso: {
              concluidos: numero(dados.concluidos) ?? 0,
              total: numero(dados.total),
              mensagem: dados.mensagem == null ? null : String(dados.mensagem),
            },
          }),
        ),
      }
    }

    case "ferramenta_fim":
      return {
        ...turno,
        blocos: mapearFerramenta(
          turno.blocos,
          b => b.id === String(dados.id ?? ""),
          b => ({ ...b, estado: dados.erro ? "erro" : "ok" }),
        ),
      }

    case "proposta":
      return {
        ...turno,
        blocos: [
          ...turno.blocos,
          {
            tipo: "proposta",
            proposta: {
              definicao: (dados.definicao ?? {}) as CanvasDefinition,
              nos: numero(dados.nos) ?? 0,
              arestas: numero(dados.arestas) ?? 0,
              desenhar: dados.desenhar === true,
              nota: typeof dados.nota === "string" ? dados.nota : undefined,
              ok: typeof dados.ok === "boolean" ? dados.ok : null,
              erros: numero(dados.erros),
              avisos: numero(dados.avisos),
            },
          },
        ],
      }

    case "fluxo":
      return {
        ...turno,
        blocos: [
          ...turno.blocos,
          {
            tipo: "fluxo",
            fluxo: { workflow_id: String(dados.workflow_id ?? ""), nome: String(dados.nome ?? "") },
          },
        ],
      }

    case "camada":
      return {
        ...turno,
        blocos: [
          ...turno.blocos,
          {
            tipo: "camada",
            camada: {
              artifact_id: String(dados.artifact_id ?? ""),
              nome: typeof dados.nome === "string" ? dados.nome : undefined,
              format: typeof dados.format === "string" ? dados.format : undefined,
              available: dados.available === true,
              hint: typeof dados.hint === "string" ? dados.hint : undefined,
            },
          },
        ],
      }

    case "confirmacao":
      return {
        ...turno,
        blocos: [
          ...turno.blocos,
          { tipo: "confirmacao", confirmacao: confirmacaoDe(dados) },
        ],
      }

    case "respostas_rapidas": {
      // Sem opção válida não há bloco: um grupo vazio de chips seria um buraco
      // na resposta. A limpeza espelha a do servidor (sem pontas, sem repetida,
      // três no máximo) — defesa em profundidade, não a regra.
      const opcoes = textos(dados.opcoes)
      if (!opcoes.length) return turno
      return { ...turno, blocos: [...turno.blocos, { tipo: "respostas_rapidas", opcoes }] }
    }

    case "erro":
      return {
        ...turno,
        blocos: [
          ...turno.blocos,
          {
            tipo: "erro",
            erro: {
              code: String(dados.code ?? "erro"),
              message: String(dados.message ?? "Algo deu errado."),
              hint: dados.hint == null ? undefined : String(dados.hint),
              ...(typeof dados.teto === "number" ? { teto: dados.teto } : {}),
            },
          },
        ],
      }

    case "fim":
      return {
        ...turno,
        // O `fim` fecha as ferramentas que ficaram em aberto. O turno pode ter
        // terminado no meio de uma (teto de voltas, aba fechada, modelo fora do
        // ar), e um passo girando para sempre mentiria sobre o que aconteceu.
        blocos: turno.blocos.map(b =>
          b.tipo === "ferramenta" && b.estado === "correndo" ? { ...b, estado: "erro" } : b,
        ),
      }

    default:
      // Quadro de um servidor mais novo. Ignorar é o comportamento certo: o
      // painel velho continua funcionando em vez de quebrar na atualização.
      return turno
  }
}

/** Texto que chega em pedaços vira UM bloco, e não um bloco por delta. */
function acumular(
  blocos: BlocoDoAssistente[],
  tipo: "texto" | "pensando",
  novo: string,
): BlocoDoAssistente[] {
  if (!novo) return blocos

  const ultimo = blocos[blocos.length - 1]
  if (ultimo?.tipo === tipo) {
    return [...blocos.slice(0, -1), { tipo, texto: ultimo.texto + novo }]
  }
  return [...blocos, { tipo, texto: novo }]
}

/** Aplica `mudar` à ÚLTIMA ferramenta que casa com `casa`. */
function mapearFerramenta(
  blocos: BlocoDoAssistente[],
  casa: (b: Extract<BlocoDoAssistente, { tipo: "ferramenta" }>) => boolean,
  mudar: (b: Extract<BlocoDoAssistente, { tipo: "ferramenta" }>) => BlocoDoAssistente,
): BlocoDoAssistente[] {
  for (let i = blocos.length - 1; i >= 0; i--) {
    const bloco = blocos[i]
    if (bloco.tipo === "ferramenta" && casa(bloco)) {
      const copia = [...blocos]
      copia[i] = mudar(bloco)
      return copia
    }
  }
  return blocos
}

const texto = (v: unknown): string => (typeof v === "string" ? v : "")

const objeto = (v: unknown): Record<string, unknown> =>
  v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : {}

/** Uma lista de frases: só strings, sem pontas, sem vazias nem repetidas, `teto` no máximo. */
const textos = (v: unknown, teto = 3): string[] => {
  if (!Array.isArray(v)) return []
  const lista: string[] = []
  for (const item of v) {
    const frase = typeof item === "string" ? item.trim() : ""
    if (frase && !lista.includes(frase)) lista.push(frase)
    if (lista.length === teto) break
  }
  return lista
}

/** Extrai a confirmação do quadro: token e a ação (tool + args resumidos + alvo). */
function confirmacaoDe(dados: Record<string, unknown>): ConfirmacaoDoAssistente {
  const acao = objeto(dados.acao)
  return {
    tool_use_id: String(dados.tool_use_id ?? ""),
    token: String(dados.token ?? ""),
    acao: {
      tool: String(acao.tool ?? ""),
      argumentos: objeto(acao.argumentos),
      alvo: typeof acao.alvo === "string" ? acao.alvo : undefined,
    },
  }
}

const numero = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null)

