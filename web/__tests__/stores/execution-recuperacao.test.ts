/**
 * Recuperação do stream de execução.
 *
 * O canal executor→servidor→browser é lossy em TODAS as camadas (fila do
 * executor, inbox do servidor, buffer do espectador, rate limit), e o servidor
 * fecha o socket com código 1000 mesmo quando a assinatura do Redis termina sem
 * o `__workflow_complete__`. O cliente tratava esse 1000 como encerramento
 * normal e não fazia nada: os nós ficavam girando e o painel dizia "Executando"
 * para sempre, com o run já concluído no banco e no log do executor.
 *
 * Estes testes cobram as três defesas que fecham esse buraco:
 *   1. nenhum nó sobrevive ao fim do run em `started`;
 *   2. queda com o run aberto reconcilia pela API;
 *   3. run ainda vivo faz o cliente reconectar, e fechamento intencional não.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest"
import { renderHook, act, waitFor } from "@testing-library/react"
import { useWorkflowExecutionStore, RUN_ENCERRADO } from "@/app/stores/workflowExecutionStore"
import type { INodeStatusWorkFlow } from "@/context/useFlowContext"

const RUN = "run-x"

let workflowAtual = "wf-a"
const runsPorWorkflow: Record<string, { run_id: string; status: string }[]> = {}
/** Status que a API devolve para o run — o que o `onclose` vai consultar. */
let statusNaApi = "running"

const nosDoCanvas = [
  { id: "n1", position: { x: 0, y: 0 }, data: {} },
  { id: "n2", position: { x: 0, y: 0 }, data: {} },
]

vi.mock("next/navigation", () => ({ useParams: () => ({ id: workflowAtual }) }))
vi.mock("next-auth/react", () => ({ useSession: () => ({ data: null }) }))
vi.mock("@/app/hooks/workflow/useSaveWorkflow", () => ({
  useSaveWorkflow: () => ({ saveWorkflow: vi.fn(async () => ({ error: null })) }),
}))

const getRunDetail = vi.fn(async () => ({ data: { status: statusNaApi } }))

vi.mock("@/service/GisFlowService", () => ({
  GisFlowService: {
    getObservabilityRuns: vi.fn(async ({ workflow_id }: { workflow_id: string }) => ({
      data: { runs: runsPorWorkflow[workflow_id] ?? [] },
    })),
    getRunDetail: (...args: unknown[]) => getRunDetail(...(args as [])),
    executeWorkflow: vi.fn(),
  },
}))

vi.mock("@/utils/createToast", () => ({
  createToast: { error: vi.fn(), info: vi.fn(), success: vi.fn() },
}))
vi.mock("@/utils/env", () => ({ getWsUrl: () => "ws://teste" }))
vi.mock("@xyflow/react", async (importOriginal) => ({
  ...(await importOriginal<object>()),
  useNodes: () => nosDoCanvas,
  useEdges: () => [],
  useReactFlow: () => ({ getNodes: () => nosDoCanvas }),
}))

class SocketFalso {
  static abertos: SocketFalso[] = []
  onopen: (() => void) | null = null
  onmessage: ((ev: { data: string }) => void) | null = null
  onerror: ((err: unknown) => void) | null = null
  onclose: ((ev: { code: number }) => void) | null = null
  fechadoCom: number | null = null

  constructor(public url: string) {
    SocketFalso.abertos.push(this)
  }
  send() {}
  /** Fechamento pedido pelo CÓDIGO (intencional). */
  close(code = 1000) {
    this.fechadoCom = code
    this.onclose?.({ code })
  }
  /** Queda vinda do SERVIDOR — o caso que precisa de recuperação. */
  cairDoServidor(code = 1000) {
    this.onclose?.({ code })
  }
}

const quadros = new Map<number, FrameRequestCallback>()
let proximoQuadro = 1

async function anexar() {
  const { useExecuteWorkflow } = await import("@/app/hooks/workflow/useExecuteWorkflow")
  const view = renderHook(() => useExecuteWorkflow())
  await waitFor(() => expect(SocketFalso.abertos.length).toBeGreaterThan(0))
  return { view, ws: SocketFalso.abertos[0] }
}

describe("recuperação do stream de execução", () => {
  beforeEach(() => {
    workflowAtual = "wf-a"
    statusNaApi = "running"
    runsPorWorkflow["wf-a"] = [{ run_id: RUN, status: "running" }]
    SocketFalso.abertos = []
    quadros.clear()
    proximoQuadro = 1
    getRunDetail.mockClear()
    vi.stubGlobal("WebSocket", SocketFalso)
    vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => {
      const id = proximoQuadro++
      quadros.set(id, cb)
      return id
    })
    vi.stubGlobal("cancelAnimationFrame", (id: number) => { quadros.delete(id) })
    // Jitter determinístico: o backoff vira exatamente a base.
    vi.spyOn(Math, "random").mockReturnValue(1)
    useWorkflowExecutionStore.getState().resetExecution()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  // ── 1. Nenhum nó sobrevive ao fim do run girando ────────────────────────

  it("nó preso em 'started' vira 'unknown' quando o run conclui", () => {
    const store = useWorkflowExecutionStore.getState()
    const nos = [
      { id: "n1", status: "completed" },
      { id: "n2", status: "started" },
    ] as INodeStatusWorkFlow[]
    store.startExecution(nos)
    store.completeExecution("completed", nos, [])

    const final = useWorkflowExecutionStore.getState()
    expect(final.statusById.get("n2")?.status).toBe("unknown")
    // O que de fato concluiu não pode ser rebaixado junto.
    expect(final.statusById.get("n1")?.status).toBe("completed")
    expect(final.isExecuting).toBe(false)
  })

  it("cancelamento continua devolvendo o nó a 'idle', não a 'unknown'", () => {
    // São desfechos diferentes: cancelar interrompeu o trabalho de verdade;
    // `unknown` é trabalho que provavelmente terminou e cuja notícia se perdeu.
    const store = useWorkflowExecutionStore.getState()
    const nos = [{ id: "n1", status: "started" }] as INodeStatusWorkFlow[]
    store.startExecution(nos)
    store.completeExecution("cancelled", nos, [])

    expect(useWorkflowExecutionStore.getState().statusById.get("n1")?.status).toBe("idle")
  })

  // ── 2. Queda com o run aberto reconcilia pela API ───────────────────────

  it("queda com código 1000 e run já concluído fecha o painel com o desfecho real", async () => {
    const { view, ws } = await anexar()
    expect(useWorkflowExecutionStore.getState().isExecuting).toBe(true)

    statusNaApi = "success"
    await act(async () => { ws.cairDoServidor(1000) })

    await waitFor(() => {
      const estado = useWorkflowExecutionStore.getState()
      expect(estado.isExecuting).toBe(false)
      expect(estado.statusWorkflow?.status).toBe("completed")
    })
    expect(getRunDetail).toHaveBeenCalled()
    // Reconciliou: não faz sentido reconectar a um run que já acabou.
    expect(SocketFalso.abertos).toHaveLength(1)

    view.unmount()
  })

  // ── 3. Run ainda vivo → reconecta; intencional → não ────────────────────

  it("queda com o run ainda em andamento reconecta com backoff", async () => {
    const { view, ws } = await anexar()
    statusNaApi = "running"

    vi.useFakeTimers()
    await act(async () => { ws.cairDoServidor(1000) })
    // A consulta à API é assíncrona; deixa a microtask resolver antes do timer.
    await act(async () => { await vi.advanceTimersByTimeAsync(1_100) })

    expect(SocketFalso.abertos.length).toBeGreaterThan(1)
    expect(SocketFalso.abertos[1].url).toContain(RUN)
    // O painel NÃO foi fechado: o run continua vivo.
    expect(useWorkflowExecutionStore.getState().isExecuting).toBe(true)

    view.unmount()
  })

  it("fechamento intencional (sair do workflow) não reconecta", async () => {
    const { view } = await anexar()
    statusNaApi = "running"

    vi.useFakeTimers()
    // Desmontar fecha o socket pelo caminho do próprio código.
    await act(async () => { view.unmount() })
    await act(async () => { await vi.advanceTimersByTimeAsync(5_000) })

    expect(SocketFalso.abertos).toHaveLength(1)
    // E não foi perguntar à API por um run que o usuário deixou para trás.
    expect(getRunDetail).not.toHaveBeenCalled()
  })

  // ── 4. Um dono só para o socket ─────────────────────────────────────────

  it("uma segunda instância do hook não abre um socket concorrente", async () => {
    // O hook é montado no botão Executar E na aba "Testar" do nó Webhook. Como
    // a store de execução é global, a segunda instância abria um WebSocket
    // paralelo para o mesmo run e, ao montar, chamava `startExecution` — que
    // zera o canvas de quem já estava acompanhando. Nos logs de produção isso
    // apareceu como três conexões ao mesmo run em 25 segundos.
    const { useExecuteWorkflow } = await import("@/app/hooks/workflow/useExecuteWorkflow")

    const dono = renderHook(() => useExecuteWorkflow())
    await waitFor(() => expect(SocketFalso.abertos).toHaveLength(1))

    const carona = renderHook(() => useExecuteWorkflow())
    // Tempo REAL para a cadeia assíncrona da re-anexação (consulta à API +
    // espera pela hidratação do canvas) completar. Com um `await
    // Promise.resolve()` o teste passaria mesmo SEM a correção, porque o
    // segundo socket ainda não teria sido aberto quando a asserção rodasse.
    await act(async () => { await new Promise(r => setTimeout(r, 60)) })

    expect(SocketFalso.abertos).toHaveLength(1)

    carona.unmount()
    dono.unmount()
  })

  // ── 5. Frame ilegível não derruba o lote ────────────────────────────────

  it("frame com JSON inválido é contabilizado e não lança", async () => {
    const { view, ws } = await anexar()
    const antes = useWorkflowExecutionStore.getState().droppedEvents

    expect(() => {
      act(() => { ws.onmessage?.({ data: '{"type":"events","events":[{bro' }) })
    }).not.toThrow()

    expect(useWorkflowExecutionStore.getState().droppedEvents).toBeGreaterThan(antes)
    view.unmount()
  })

  // ── 5b. Socket mudo (Safari) é recuperado sem depender do onclose ───────
  //
  // No Safari um WebSocket ocioso é derrubado em silêncio, SEM disparar
  // `onclose`. Como a reconexão vivia toda no `onclose`, a queda passava
  // despercebida: o painel girava para sempre, com o run já concluído no
  // servidor. O watchdog de inatividade fecha esse buraco — detecta o silêncio
  // e recupera pela API/replay, mesmo que o `onclose` nunca venha.

  it("socket mudo além do limite recupera mesmo sem onclose (caso Safari)", async () => {
    const { view, ws } = await anexar()
    expect(useWorkflowExecutionStore.getState().isExecuting).toBe(true)
    // A API sabe que o run terminou — o Safari só nunca recebeu os eventos.
    statusNaApi = "success"

    vi.useFakeTimers()
    // Arma o watchdog no relógio falso (o socket falso não dispara onopen só).
    act(() => { ws.onopen?.() })
    // Silêncio TOTAL: nenhum onmessage e — de propósito — nenhum onclose.
    await act(async () => { await vi.advanceTimersByTimeAsync(70_000) })

    // O watchdog assumiu o socket morto e reconciliou pela API.
    expect(getRunDetail).toHaveBeenCalled()
    expect(useWorkflowExecutionStore.getState().isExecuting).toBe(false)
    expect(useWorkflowExecutionStore.getState().statusWorkflow?.status).toBe("completed")

    view.unmount()
  })

  it("heartbeat (frame vazio) mantém o socket vivo e NÃO dispara o watchdog", async () => {
    const { view, ws } = await anexar()
    statusNaApi = "success"

    vi.useFakeTimers()
    act(() => { ws.onopen?.() })
    // A cada 20s chega um heartbeat (lote vazio). O silêncio nunca acumula, então
    // o watchdog não pode confundir uma conexão saudável com socket morto.
    for (let t = 0; t < 90_000; t += 20_000) {
      await act(async () => { await vi.advanceTimersByTimeAsync(20_000) })
      act(() => { ws.onmessage?.({ data: '{"type":"events","dropped":0,"events":[]}' }) })
    }

    expect(getRunDetail).not.toHaveBeenCalled()
    expect(useWorkflowExecutionStore.getState().isExecuting).toBe(true)

    view.unmount()
  })

  // ── 6. Lote atrasado não ressuscita um run já liquidado ─────────────────
  //
  // O cliente aplica eventos por quadro de `requestAnimationFrame`. Com a aba em
  // segundo plano o quadro NÃO roda, mas o WebSocket continua entregando: o lote
  // fica pendente enquanto o run termina e é liquidado. Ao voltar para a aba, o
  // quadro atrasado disparava e reaplicava eventos velhos por cima do desfecho —
  // o nó voltava a `started` e ficava girando para sempre, agora sem socket, sem
  // `isExecuting` e sem ninguém para liquidá-lo de novo. Era o que sobrava do
  // sintoma depois de as duas correções anteriores fecharem os caminhos de PERDA.

  function rodarQuadrosPendentes() {
    const pendentes = [...quadros.values()]
    quadros.clear()
    for (const cb of pendentes) cb(0)
  }

  it("quadro atrasado que roda depois da liquidação não devolve o nó a 'started'", async () => {
    const { view, ws } = await anexar()

    // Chegam eventos, mas o quadro fica pendente (aba em segundo plano).
    act(() => {
      ws.onmessage?.({ data: JSON.stringify({
        type: "events",
        events: [
          { run_id: RUN, node: "n1", status: "completed", kind: "lifecycle" },
          { run_id: RUN, node: "n2", status: "started",   kind: "lifecycle" },
        ],
      }) })
    })
    expect(quadros.size).toBeGreaterThan(0)

    // O run termina e o socket cai sem o `__workflow_complete__`.
    statusNaApi = "success"
    await act(async () => { ws.cairDoServidor(1000) })
    await waitFor(() => {
      expect(useWorkflowExecutionStore.getState().isExecuting).toBe(false)
    })

    // O usuário volta para a aba: o que estava agendado dispara agora.
    act(() => { rodarQuadrosPendentes() })

    const final = useWorkflowExecutionStore.getState()
    expect(final.statusById.get("n2")?.status).toBe("unknown")
    expect(final.statusById.get("n2")?.status).not.toBe("started")
    // Drenar ANTES de liquidar preserva o que de fato chegou: o `completed` do
    // n1 é informação legítima e não pode ser jogada fora junto com o lote.
    expect(final.statusById.get("n1")?.status).toBe("completed")
    expect(final.statusWorkflow?.status).toBe("completed")

    view.unmount()
  })

  it("updateNodeStatuses é inerte depois de o run ter desfecho", () => {
    const store = useWorkflowExecutionStore.getState()
    const nos = [{ id: "n1", status: "completed" }] as INodeStatusWorkFlow[]
    store.startExecution(nos)
    store.completeExecution("completed", nos, [])

    // Cinto de segurança da store: mesmo que algum caminho futuro escape das
    // guardas do hook, o desfecho é definitivo.
    useWorkflowExecutionStore.getState().updateNodeStatuses(
      [{ id: "n1", status: "started" }] as INodeStatusWorkFlow[], [],
    )

    const final = useWorkflowExecutionStore.getState()
    expect(final.statusById.get("n1")?.status).toBe("completed")
    expect(final.statusWorkflow?.status).toBe("completed")
    expect(final.isExecuting).toBe(false)
  })

  it("re-anexar a um run que o servidor diz vivo desfaz um encerramento precipitado", async () => {
    // A guarda de `updateNodeStatuses` torna o desfecho definitivo — o que seria
    // errado se o desfecho tivesse sido nosso engano. Aqui o cliente liquidou o
    // run (reconciliação em corrida / desistência) mas a API o reporta em
    // andamento: a re-anexação precisa re-semear, senão o replay é descartado
    // pela guarda e o canvas congela no desfecho errado.
    const store = useWorkflowExecutionStore.getState()
    store.startExecution([{ id: "n1", status: "started" }] as INodeStatusWorkFlow[])
    store.setTaskId(RUN)
    store.completeExecution("failed", store.statusWorkflow?.nodes ?? [], [])
    expect(useWorkflowExecutionStore.getState().isExecuting).toBe(false)

    const { view } = await anexar()
    await waitFor(() => {
      const estado = useWorkflowExecutionStore.getState()
      expect(estado.isExecuting).toBe(true)
      expect(RUN_ENCERRADO.has(estado.statusWorkflow?.status ?? "")).toBe(false)
    })

    view.unmount()
  })

  it("failExecution também liquida nó preso em 'started'", () => {
    const store = useWorkflowExecutionStore.getState()
    const nos = [
      { id: "n1", status: "completed" },
      { id: "n2", status: "started" },
    ] as INodeStatusWorkFlow[]
    store.startExecution(nos)
    store.updateNodeStatuses(nos, [])
    useWorkflowExecutionStore.getState().failExecution()

    const final = useWorkflowExecutionStore.getState()
    expect(final.statusById.get("n2")?.status).toBe("unknown")
    expect(final.statusById.get("n1")?.status).toBe("completed")
    expect(final.isExecuting).toBe(false)
  })
})
