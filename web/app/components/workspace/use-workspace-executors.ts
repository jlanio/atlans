"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { GisFlowService, IExecutor } from "@/service/GisFlowService"
import type { IWorkspacePolicy } from "@/service/types"
import { createToast } from "@/utils/createToast"
import type { Workspace } from "@/context/WorkspaceContext"

/** Valor do <Select> para "pool da plataforma" — o backend representa como null. */
export const POOL = "__default__"

/**
 * O "alvo" que o seletor rápido representa, lido da política.
 *
 * Segue o que o roteamento LÊ: com a flag ligada, o nível principal; com ela
 * desligada, o ponteiro legado — que é o que decide para onde a execução vai
 * até a virada. Mostrar o nível enquanto o servidor roteia pelo ponteiro
 * seria afirmar um destino que a próxima execução não vai ter.
 */
export function alvoDaPolitica(p: IWorkspacePolicy): string | null {
  return p.policy_routing_enabled
    ? (p.primary[0]?.id_hash ?? null)
    : (p.target_executor_id ?? null)
}

/**
 * Executor de cada workspace da lista, para a troca rápida no próprio card.
 *
 * Vive aqui, e não dentro do card, por três motivos: `getMyAgents` é UMA
 * chamada para a tela inteira; a troca precisa de rollback; e "não consegui
 * ler" NÃO pode virar "pool da plataforma" — o card estaria mentindo sobre para
 * onde as execuções daquele workspace vão.
 */
export function useWorkspaceExecutors(workspaces: Workspace[]) {
  const [executores, setExecutores] = useState<IExecutor[]>([])
  const [alvos, setAlvos] = useState<Record<string, string | null>>({})
  /** Política completa por workspace — níveis, terminal, piso e saúde. */
  const [politicas, setPoliticas] = useState<Record<string, IWorkspacePolicy>>({})
  /** Workspaces cuja leitura do executor falhou — estado "não sei", nem pool nem alvo. */
  const [desconhecidos, setDesconhecidos] = useState<Set<string>>(new Set())
  /** Falha ao listar MEUS executores: sem ela, todo alvo pareceria "removido". */
  const [erro, setErro] = useState<string | null>(null)
  const [salvando, setSalvando] = useState<Set<string>>(new Set())

  // Só a lista de ids entra na dependência: o array `workspaces` é recriado a
  // cada reload do context e dispararia o fetch em laço.
  const ids = workspaces.map(w => w.id_hash).join(",")

  // Época da carga: só serve para "uma carga MAIS NOVA vence a mais velha".
  // Uma `trocar` NÃO mexe aqui — invalidar a época inteira descartaria uma
  // recarga geral concorrente por completo (todos os OUTROS workspaces perdiam
  // o dado fresco).
  const epocaRef = useRef(0)
  // Ids com gravação em voo — preservados por qualquer recarga concorrente.
  const emVooRef = useRef<Set<string>>(new Set())
  // Relógio monotônico para ordenar escritas. Cada `carregar` guarda o carimbo
  // de quando COMEÇOU; cada `trocar` autoritativo carimba o workspace ao sair do
  // "em voo". Uma carga velha, ao mesclar, preserva o workspace cujo carimbo de
  // escrita é mais novo que seu início — protege a troca sem jogar fora o resto.
  const relogioRef = useRef(0)
  const escritoEmRef = useRef<Record<string, number>>({})

  const carregar = useCallback(async () => {
    const lista = ids ? ids.split(",") : []
    if (lista.length === 0) {
      setExecutores([]); setAlvos({}); setPoliticas({}); setDesconhecidos(new Set()); setErro(null)
      return
    }
    const minha = ++epocaRef.current
    const inicio = ++relogioRef.current   // carimbo de início desta carga
    // Uma leitura por workspace: a política traz junto o ponteiro legado
    // (`target_executor_id`), então o executor não precisa de leitura própria.
    const [meus, ...respostas] = await Promise.all([
      GisFlowService.getMyAgents(),
      ...lista.map(id => GisFlowService.getWorkspacePolicy(id)),
    ])
    if (minha !== epocaRef.current) return

    if (meus.error) {
      setErro(meus.error.message ?? "Não foi possível carregar seus executores.")
    } else {
      setErro(null)
      // Mantém inclusive revoked/inactive: é assim que se detecta um executor
      // removido que ainda está apontado como alvo do workspace.
      setExecutores(meus.data ?? [])
    }

    const mapa: Record<string, string | null> = {}
    const lidas: Record<string, IWorkspacePolicy> = {}
    const falhas = new Set<string>()
    lista.forEach((id, i) => {
      const r = respostas[i]
      if (r.error || !r.data) falhas.add(id)
      else { mapa[id] = alvoDaPolitica(r.data); lidas[id] = r.data }
    })
    // Um workspace é preservado (não sobrescrito por esta carga) quando tem uma
    // gravação EM VOO ou uma escrita autoritativa de `trocar` mais nova que o
    // início desta carga — o instantâneo aqui é anterior a ela.
    const preservar = (id: string) =>
      emVooRef.current.has(id) || (escritoEmRef.current[id] ?? 0) > inicio
    // Mescla (não substitui): uma recarga parcial não pode apagar o que já se
    // sabia, e o valor de uma troca (em voo ou recém-escrita) tem precedência.
    setAlvos(prev => {
      const merged = { ...prev, ...mapa }
      for (const id of Object.keys(merged)) if (preservar(id) && id in prev) merged[id] = prev[id]
      return merged
    })
    setPoliticas(prev => {
      const merged = { ...prev, ...lidas }
      for (const id of Object.keys(merged)) if (preservar(id) && id in prev) merged[id] = prev[id]
      return merged
    })
    // Um workspace protegido não vira "desconhecido" por uma falha de leitura
    // desta carga velha: seu valor autoritativo acabou de ser escrito.
    setDesconhecidos(new Set([...falhas].filter(id => !preservar(id))))
  }, [ids])

  useEffect(() => { carregar() }, [carregar])

  // O valor anterior sai de um ref: entre o clique e a resposta o mapa já foi
  // reescrito pela atualização otimista.
  const alvosRef = useRef<Record<string, string | null>>({})
  useEffect(() => { alvosRef.current = alvos }, [alvos])
  const desconhecidosRef = useRef<Set<string>>(new Set())
  useEffect(() => { desconhecidosRef.current = desconhecidos }, [desconhecidos])

  // Nome do executor para o toast — a lista já está na tela.
  const executoresRef = useRef<IExecutor[]>([])
  useEffect(() => { executoresRef.current = executores }, [executores])

  const trocar = useCallback(async (workspaceId: string, valor: string, nomeDoWorkspace?: string) => {
    if (emVooRef.current.has(workspaceId)) return
    const agentId = valor === POOL ? null : valor
    const anterior = alvosRef.current[workspaceId] ?? null
    // Se a leitura deste workspace havia FALHADO, "anterior" é `null` — que na
    // tela significa "pool da plataforma". Sem restaurar o desconhecido, uma
    // troca que falha faz o card afirmar pool, a mesma mentira que o estado
    // "não sei" existe para evitar.
    const eraDesconhecido = desconhecidosRef.current.has(workspaceId)

    // Conjunto, e não um id só: trocar dois cards em sequência apagava o
    // spinner do card errado e reabilitava um Select ainda em voo.
    emVooRef.current.add(workspaceId)
    setSalvando(s => new Set(s).add(workspaceId))
    setAlvos(prev => ({ ...prev, [workspaceId]: agentId }))
    setDesconhecidos(prev => {
      if (!prev.has(workspaceId)) return prev
      const s = new Set(prev); s.delete(workspaceId); return s
    })

    const res = await GisFlowService.setWorkspaceAgent(workspaceId, agentId)

    if (res.error) {
      emVooRef.current.delete(workspaceId)
      setSalvando(s => { const n = new Set(s); n.delete(workspaceId); return n })
      setAlvos(prev => ({ ...prev, [workspaceId]: anterior }))
      if (eraDesconhecido) setDesconhecidos(prev => new Set(prev).add(workspaceId))
      createToast.error("Erro ao trocar o executor", res.error.message)
      return
    }
    // O endpoint legado grava os dois lados (ponteiro e nível principal), mas
    // devolve só o ponteiro: a política deste workspace — níveis, modo, saúde —
    // é relida para o selo e a frase do painel não ficarem com a versão antiga.
    // Ainda "em voo" durante a releitura: uma recarga geral concorrente não
    // pode sobrescrever a troca com um instantâneo anterior a ela.
    const pol = await GisFlowService.getWorkspacePolicy(workspaceId)
    // Protege esta escrita contra uma recarga geral que começou ANTES e ainda
    // não respondeu (traz um instantâneo anterior a esta troca). Em vez de
    // invalidar a época inteira — que descartava o resultado dessa recarga para
    // TODOS os workspaces —, carimba SÓ este no relógio e só então sai do "em
    // voo": a carga velha, ao mesclar, vê o carimbo > seu início e preserva
    // este workspace, sem perder o dado fresco dos demais.
    escritoEmRef.current[workspaceId] = ++relogioRef.current
    emVooRef.current.delete(workspaceId)
    setSalvando(s => { const n = new Set(s); n.delete(workspaceId); return n })
    if (!pol.error && pol.data) {
      const lida = pol.data
      setPoliticas(prev => ({ ...prev, [workspaceId]: lida }))
      setAlvos(prev => ({ ...prev, [workspaceId]: alvoDaPolitica(lida) }))
    }
    // O toast diz o RESULTADO: onde este workspace passa a executar.
    const quem = nomeDoWorkspace ? `«${nomeDoWorkspace}»` : "O workspace"
    if (agentId === null) {
      createToast.success(`${quem} agora usa o pool compartilhado.`)
    } else {
      const nome = executoresRef.current.find(e => e.id_hash === agentId)?.name ?? "o executor escolhido"
      createToast.success(`${quem} agora executa em ${nome}.`)
    }
  }, [])

  return {
    executores, alvos, politicas, desconhecidos, erro, salvando, trocar,
    recarregar: carregar,
  }
}
