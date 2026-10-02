"use client"

// web/app/hooks/home/useAssistente.ts
//
// O consumidor do stream do assistente da Home — irmão de `useAssistenteEditor`,
// com quem divide a leitura do stream (`home/assistente/stream.ts`). As
// diferenças: a rota é `/assistente` (conversa persistida, chaveada por
// `conversa_id` e não por fluxo); o 1º quadro `conversa` ensina o id de uma
// conversa nova; há `carregar` (o replay) e `confirmar` (o 2º SSE do clique).
// Sem `Authorization` pelo mesmo motivo do editor: o proxy `/terra` autentica
// pelo cookie de sessão.

import { useCallback, useEffect, useRef, useState } from "react"

import { GisFlowService } from "@/service/GisFlowService"
import type { IAssistenteEstado, IQuadroDoReplay } from "@/service/types"
import { useHomeStore } from "@/app/stores/homeStore"
import { useIdiomaDaTela } from "@/app/components/home/i18n"
import { API_URL } from "@/utils/env"
import {
  aplicarQuadro, turnoVazio,
  type QuadroSSE, type TurnoDoAssistente,
} from "@/app/components/home/assistente/quadros"
import {
  SEM_CONEXAO, aplicarCota, aplicarNoTurno, erroDaResposta, lerQuadrosSSE, proximoIdDeTurno,
  type ErrosDaRota,
} from "@/app/components/home/assistente/stream"

/**
 * O que aconteceu com uma decisão de confirmação. São TRÊS casos, e não um
 * booleano, porque o cartão trata cada um de um jeito:
 * - `valeu`: o servidor aceitou (a resposta virou stream) — o cartão fica
 *   travado. Vale também para um "Parar" no meio do stream: a chave já foi
 *   consumida, e destravar reabriria um cartão que não pode mais ser decidido.
 * - `expirada`: 409 — a chave já tinha sido consumida ou venceu. Continua
 *   travado (clicar de novo só renderia outro 409), com a microcópia que diz
 *   isso em vez de "Decidido.".
 * - `falhou`: a decisão não chegou a valer (transporte, ou um erro que não
 *   consumiu a chave) — o cartão volta a ser clicável, senão a ação fica sem
 *   caminho nenhum para ser refeita.
 */
export type ResultadoDaDecisao = "valeu" | "expirada" | "falhou"

export interface Agente {
  estado: IAssistenteEstado | null
  consultando: boolean
  /**
   * A consulta de estado FALHOU (rede, 502, timeout). Distinto de `estado` com
   * `ativo: false`, que é "desligado nesta instalação": um 502 de dois segundos
   * não pode ser lido como "o assistente não existe aqui".
   */
  falhou: boolean
  /** Refaz a consulta de estado — o "Tentar de novo" da Home. */
  reconsultar: () => void
  turnos: TurnoDoAssistente[]
  /** O replay da conversa selecionada está a caminho. */
  carregandoReplay: boolean
  correndo: boolean
  enviar: (mensagem: string) => Promise<void>
  /** Diz ao cartão o que fazer: travar, travar como expirada, ou destravar. */
  confirmar: (toolUseId: string, token: string, decisao: "confirmar" | "recusar") => Promise<ResultadoDaDecisao>
  parar: () => void
}

interface Opcoes {
  /** A conversa selecionada (dos Chats); `null`/ausente = conversa nova. */
  conversaId?: string | null
  /** Workspace preferido para os fluxos que o assistente criar. */
  workspaceId?: string | null
  /**
   * Chamado quando a conversa ganha atividade: no 1º quadro `conversa` de cada
   * mensagem (id, título, se acabou de nascer — o store aprende o id novo) e
   * quando uma confirmação é aceita (só o id: o 2º SSE não emite `conversa`,
   * mas o servidor carimba `updated_at` ao fechá-lo).
   */
  onConversa?: (info: { id: string; titulo?: string; nova: boolean }) => void
  /**
   * Sem sessão: não consulta o `/estado` (viraria 401 no proxy e a Home
   * mostraria "não foi possível falar com o assistente" no lugar da barra) e
   * deixa `estado` nulo — a Home renderiza a barra, e o primeiro envio abre
   * o modal de entrada. Quando a sessão chegar (login no modal, ou noutra aba),
   * a consulta sai.
   */
  anonimo?: boolean
}

export function useAssistente({ conversaId, workspaceId, onConversa, anonimo = false }: Opcoes): Agente {
  const [estado, setEstado] = useState<IAssistenteEstado | null>(null)
  const [consultando, setConsultando] = useState(true)
  const [falhou, setFalhou] = useState(false)
  const [turnos, setTurnos] = useState<TurnoDoAssistente[]>([])
  const [carregandoReplay, setCarregandoReplay] = useState(false)
  const [correndo, setCorrendo] = useState(false)
  const [tentativa, setTentativa] = useState(0)

  const abortoRef = useRef<AbortController | null>(null)
  // O idioma da tela vai no turno (o assistente responde nele). Por ref, lida
  // na hora do envio como a localização: trocar o idioma não recria `enviar`.
  const idiomaDaTela = useIdiomaDaTela()
  const idiomaRef = useRef(idiomaDaTela)
  useEffect(() => { idiomaRef.current = idiomaDaTela }, [idiomaDaTela])
  /** O turno do assistente que está sendo escrito — para marcá-lo se parar. */
  const turnoCorrenteRef = useRef<string | null>(null)
  // A conversa atualmente NA TELA. Distinta do prop: o prop muda por seleção
  // externa (Chats) E por onConversa (id novo) — só a seleção externa recarrega.
  const carregadoRef = useRef<string | null | undefined>(undefined)
  const onConversaRef = useRef(onConversa)
  onConversaRef.current = onConversa

  // O `get()` do serviço nunca rejeita: um 502 volta como `success: false` com
  // `data` indefinido. Ler só o `data` transformava a queda transitória em
  // "assistente desligado" e sumia com o painel E a barra, sem dizer nada.
  //
  // `anonimo` está nas deps de propósito: o SessionProvider ouve o login feito
  // noutra aba (BroadcastChannel) e `status` vira "authenticated" sem remontar
  // nada — sem a dep, a Home saía do modo anônimo com `estado` nulo e caía no
  // aviso "não está disponível nesta instalação".
  useEffect(() => {
    if (anonimo) {
      setEstado(null)
      setFalhou(false)
      setConsultando(false)
      return
    }
    let vivo = true
    setConsultando(true)
    GisFlowService.estadoDoAgente().then(({ success, data }) => {
      if (!vivo) return
      setFalhou(!success || !data)
      if (success && data) setEstado(data)
      setConsultando(false)
    })
    return () => { vivo = false }
  }, [tentativa, anonimo])

  const reconsultar = useCallback(() => setTentativa((n) => n + 1), [])

  const parar = useCallback(() => {
    if (!abortoRef.current) return
    abortoRef.current.abort()
    abortoRef.current = null
    // Um turno cortado no meio de uma frase é igualzinho a um concluído. Sem
    // esta marca a pessoa acha que a resposta acabou — ou que a execução parou,
    // o que não é verdade do lado do servidor.
    if (turnoCorrenteRef.current) {
      aplicarNoTurno(setTurnos, turnoCorrenteRef.current, { evento: "erro", dados: INTERROMPIDA })
      turnoCorrenteRef.current = null
    }
    setCorrendo(false)
  }, [])

  // O stream tem de morrer com a Home: sem isto, sair para /projects deixava o
  // `for(;;)` lendo, a conexão aberta e o servidor gerando tokens contra a cota
  // de uma resposta que ninguém mais vai ler.
  useEffect(() => () => { abortoRef.current?.abort() }, [])

  const carregar = useCallback(async (id: string) => {
    parar()
    // Limpa ANTES da viagem de rede: o painel continuava desenhando a conversa
    // anterior enquanto o replay vinha, e em rede lenta dava para ler e
    // responder achando que já se estava no chat novo.
    setTurnos([])
    setCarregandoReplay(true)
    const { success, data } = await GisFlowService.lerConversa(id)
    // Só aplica se ainda é a conversa pedida (troca rápida de chat).
    if (carregadoRef.current !== id) return
    setTurnos(success && data ? reconstruirTurnos(data.quadros) : [])
    setCarregandoReplay(false)
  }, [parar])

  // Seleção de conversa: recarrega o replay (ou limpa para uma nova). Um id que
  // veio de onConversa (stream em curso) já casa com carregadoRef → não recarrega.
  useEffect(() => {
    const alvo = conversaId ?? null
    if (alvo === carregadoRef.current) return
    parar()
    carregadoRef.current = alvo
    if (alvo) void carregar(alvo)
    else { setTurnos([]); setCarregandoReplay(false) }
  }, [conversaId, carregar, parar])

  const recarregarCota = useCallback(() => {
    void GisFlowService.estadoDoAgente().then(({ data }) => { if (data) setEstado(data) })
  }, [])

  /** Consome um SSE de `/assistente`, aplicando os quadros ao turno `idDoTurno`. */
  const consumir = useCallback(async (resposta: Response, idDoTurno: string) => {
    if (!resposta.ok || !resposta.body) {
      aplicarNoTurno(setTurnos, idDoTurno, { evento: "erro", dados: await erroDaResposta(resposta, ERROS_DA_ROTA) })
      return
    }
    const tratar = (quadro: QuadroSSE) => {
      if (aplicarCota(setEstado, quadro)) return
      if (quadro.evento === "conversa") {
        const id = String(quadro.dados.conversa_id ?? "")
        if (id) {
          // O id novo já é o "carregado": impede a seleção-eco de recarregar.
          carregadoRef.current = id
          onConversaRef.current?.({
            id,
            titulo: typeof quadro.dados.titulo === "string" ? quadro.dados.titulo : undefined,
            nova: quadro.dados.nova === true,
          })
        }
        return
      }
      aplicarNoTurno(setTurnos, idDoTurno, quadro)
    }
    await lerQuadrosSSE(resposta.body, tratar)
  }, [])

  const enviar = useCallback(async (mensagem: string) => {
    const texto = mensagem.trim()
    if (!texto || abortoRef.current) return

    const controle = new AbortController()
    abortoRef.current = controle
    const idDoTurno = proximoIdDeTurno()
    turnoCorrenteRef.current = idDoTurno
    setTurnos((anteriores) => [
      ...anteriores,
      { id: proximoIdDeTurno(), papel: "user", texto, blocos: [] },
      turnoVazio(idDoTurno),
    ])
    setCorrendo(true)

    try {
      // A localização entra no corpo só quando a pessoa a COMPARTILHOU (o "+"
      // liga; o × desliga) e há posição. Lida da store NA HORA do envio — nem
      // prop nem ref: a posição muda a cada tick do modo seguir, e qualquer
      // inscrição recriaria callbacks ou re-renderizaria a Home à toa. Sem ela,
      // o turno é byte a byte o de sempre.
      const corpo: Record<string, unknown> = {
        mensagem: texto,
        conversa_id: conversaId ?? null,
        workspace_id: workspaceId ?? null,
      }
      const { compartilharLocalizacao, localizacao } = useHomeStore.getState()
      if (compartilharLocalizacao && localizacao) corpo.localizacao = localizacao
      // Em português o corpo segue byte a byte o de antes (o padrão do servidor).
      if (idiomaRef.current !== "pt-BR") corpo.idioma = idiomaRef.current
      const resposta = await fetch(`${API_URL}/assistente/conversa`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
        body: JSON.stringify(corpo),
        signal: controle.signal,
      })
      await consumir(resposta, idDoTurno)
    } catch (erro) {
      if (!(erro instanceof DOMException && erro.name === "AbortError")) {
        aplicarNoTurno(setTurnos, idDoTurno, { evento: "erro", dados: SEM_CONEXAO })
      }
    } finally {
      if (abortoRef.current === controle) abortoRef.current = null
      if (turnoCorrenteRef.current === idDoTurno) turnoCorrenteRef.current = null
      setCorrendo(false)
      recarregarCota()
    }
  }, [conversaId, workspaceId, consumir, recarregarCota])

  const confirmar = useCallback(async (
    toolUseId: string, token: string, decisao: "confirmar" | "recusar",
  ): Promise<ResultadoDaDecisao> => {
    const id = carregadoRef.current
    if (!id || abortoRef.current) return "falhou"

    const controle = new AbortController()
    abortoRef.current = controle
    const idDoTurno = proximoIdDeTurno()
    turnoCorrenteRef.current = idDoTurno
    // Um turno novo do assistente para a ação executada e a resposta retomada.
    setTurnos((anteriores) => [...anteriores, turnoVazio(idDoTurno)])
    setCorrendo(true)

    // Fica FORA do try: quando o "Parar" aborta a leitura do stream a decisão
    // já valeu no servidor, e é este valor que o catch devolve. Ler `false` ali
    // destravava um cartão cuja chave o servidor tinha acabado de consumir.
    let resultado: ResultadoDaDecisao = "falhou"

    try {
      // A confirmação RETOMA o laço do modelo — e a retomada precisa continuar
      // sabendo o "perto de mim": o servidor não guarda a coordenada (ela vive
      // só no prompt do stream), então o cliente a reenvia aqui, com a mesma
      // regra do envio (compartilhada e presente).
      const corpo: Record<string, unknown> = { token, decisao }
      const { compartilharLocalizacao, localizacao } = useHomeStore.getState()
      if (compartilharLocalizacao && localizacao) corpo.localizacao = localizacao
      if (idiomaRef.current !== "pt-BR") corpo.idioma = idiomaRef.current
      const resposta = await fetch(
        `${API_URL}/assistente/conversas/${encodeURIComponent(id)}/confirmacoes/${encodeURIComponent(toolUseId)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
          body: JSON.stringify(corpo),
          signal: controle.signal,
        },
      )
      // A decisão "pegou" quando a resposta virou stream. O 409 é caso à parte:
      // a chave JÁ foi consumida (ou venceu), então não há o que refazer — o
      // cartão fica travado, só que dizendo isso. Os outros erros deixam a ação
      // por fazer, e aí destravar é o único caminho de volta.
      resultado = resposta.ok && resposta.body
        ? "valeu"
        : resposta.status === 409
          ? "expirada"
          : "falhou"
      // A decisão aceita é atividade na conversa (o servidor carimba `updated_at`
      // ao fechar o stream): avisa quem lista, como o quadro `conversa` faria —
      // sem título, só o id.
      if (resultado === "valeu") onConversaRef.current?.({ id, nova: false })
      await consumir(resposta, idDoTurno)
      return resultado
    } catch (erro) {
      if (erro instanceof DOMException && erro.name === "AbortError") return resultado
      aplicarNoTurno(setTurnos, idDoTurno, { evento: "erro", dados: SEM_CONEXAO })
      return "falhou"
    } finally {
      if (abortoRef.current === controle) abortoRef.current = null
      if (turnoCorrenteRef.current === idDoTurno) turnoCorrenteRef.current = null
      setCorrendo(false)
      recarregarCota()
    }
  }, [consumir, recarregarCota])

  return {
    estado, consultando, falhou, reconsultar,
    turnos, carregandoReplay, correndo, enviar, confirmar, parar,
  }
}

const INTERROMPIDA = { code: "interrompida", message: "Resposta interrompida.", hint: "o que já foi disparado no servidor continua" }

/** Os status que `/assistente` (e a confirmação) recusa antes do stream. Não é a
 *  tabela do editor de propósito — ver `erroDaResposta`. */
const ERROS_DA_ROTA: ErrosDaRota = {
  403: { code: "token_invalido", message: "Esta confirmação não confere mais." },
  404: { code: "nao_encontrada", message: "Conversa não encontrada." },
  409: { code: "expirada", message: "A confirmação expirou ou já foi decidida." },
  422: { code: "rejeitada", message: "Mensagem recusada." },
  // Não é `rate_limited`: esse código, no stream, é a cota DIÁRIA do
  // assistente — em inglês e espanhol a tela diria "espere um instante" a
  // quem só volta amanhã.
  429: { code: "muitas_requisicoes", message: "Muitas mensagens em pouco tempo. Espere um instante." },
  503: { code: "desligado", message: "O assistente não está disponível nesta instalação." },
}

/** Reconstrói os turnos a partir dos quadros do replay (`GET /conversas/{id}`). */
export function reconstruirTurnos(quadros: IQuadroDoReplay[]): TurnoDoAssistente[] {
  const turnos: TurnoDoAssistente[] = []
  let assistente: TurnoDoAssistente | null = null

  for (const q of quadros) {
    const meta = q.dados?.meta as { tipo?: string } | undefined
    if (q.tipo === "usuario") {
      // Mensagem sintética de confirmação (gerada pelo servidor) não é fala da
      // pessoa — não vira bolha. A resposta do assistente a ela continua abaixo.
      if (meta?.tipo === "confirmacao") continue
      if (assistente) { turnos.push(assistente); assistente = null }
      turnos.push({ id: proximoIdDeTurno(), papel: "user", texto: String(q.dados.texto ?? ""), blocos: [] })
      continue
    }
    if (q.tipo === "conversa") continue // metadado do hook, não é turno
    if (q.tipo === "fim") {
      if (assistente) assistente = aplicarQuadro(assistente, { evento: "fim", dados: q.dados })
      continue
    }
    if (!assistente) assistente = turnoVazio(proximoIdDeTurno())
    assistente = aplicarQuadro(assistente, { evento: q.tipo, dados: q.dados })
  }
  if (assistente) turnos.push(assistente)
  return turnos
}
