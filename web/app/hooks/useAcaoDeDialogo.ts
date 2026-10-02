"use client"

import { useCallback, useRef, useState } from "react"
import type { IResponse } from "@/service/types"
import { createToast } from "@/utils/createToast"

/** O texto de um toast: a frase, ou título + descrição. */
export type TextoDeToast = string | readonly [titulo: string, descricao?: string]

/** O erro do serviço, com o código de domínio quando houver (o 409 da política). */
export type ErroDaAcao = NonNullable<IResponse<unknown>["error"]>

/**
 * O que a ação devolve: a resposta do serviço (`data` no sucesso, `error` na
 * falha) — ou nada, para a ação que só lança quando falha. A validação do
 * formulário fica FORA da ação (no `disabled` do botão e no Enter): uma ação
 * que volta sem erro é um sucesso.
 */
type RespostaDaAcao<R> = { data?: R; error?: ErroDaAcao | null } | void

export interface OpcoesDaAcao<R> {
  /** Toast do sucesso: texto fixo, ou função do que o servidor devolveu. `null`: sem toast. */
  sucesso: TextoDeToast | null | ((dados: R) => TextoDeToast | null)
  /**
   * Toast da falha, a partir da mensagem do servidor (`undefined` quando não
   * veio nenhuma). `null`: o diálogo mostra o erro na própria tela — o 409 da
   * política vira o aviso do «mesmo assim» — e o toast não sai.
   */
  erro: (mensagem: string | undefined, erro: ErroDaAcao) => TextoDeToast | null
  /** Depois do sucesso, com o diálogo já fechado — tipicamente recarregar a lista. */
  aoConcluir?: (dados: R) => void
}

export interface AcaoDeDialogo {
  aberto: boolean
  /** Abrir/fechar. Fechar no meio da ação é ignorado — a mesma trava do `bloqueado`. */
  setAberto: (aberto: boolean) => void
  /** A ação está em voo: é o `bloqueado` do DialogContent e o `disabled` dos botões. */
  executando: boolean
  /**
   * Roda a ação. Chamada de novo enquanto ela está em voo — o Enter do campo e
   * o clique do botão, o Enter repetido — devolve a MESMA ação, sem chamar o
   * serviço outra vez. Resolve depois do toast e do `aoConcluir`.
   */
  executar: () => Promise<void>
}

/**
 * O ciclo de um diálogo de ação: aberto → executando → toast → fecha →
 * `aoConcluir`. Os diálogos de Admin › Usuários, de Executores e da lixeira de
 * workspaces repetiam isso cada um com o seu `[open, loading]`, e a cópia
 * divergiu onde doía: o campo chamava a mesma função do botão no Enter, a
 * função não olhava o `loading` — só o botão, por estar `disabled`, ficava
 * protegido —, e Enter duas vezes numa ação lenta disparava a chamada duas
 * vezes. Aqui Enter e clique passam pelo mesmo `executar`, e a guarda vale
 * para os dois.
 */
export function useAcaoDeDialogo<R = unknown>(
  fn: () => Promise<RespostaDaAcao<R>>,
  opcoes: OpcoesDaAcao<R>,
): AcaoDeDialogo {
  const [aberto, setAbertoState] = useState(false)
  const [executando, setExecutando] = useState(false)
  // Ref e não só estado: o segundo Enter pode chegar antes de o React desenhar
  // o "executando" — a guarda tem de valer já no mesmo tique.
  const emVoo = useRef<Promise<void> | null>(null)

  // Lidos de refs para `executar` ter identidade constante; o valor que vale é
  // o do render em que a ação foi CONFIRMADA (ver `executar`).
  const fnRef = useRef(fn)
  const opcoesRef = useRef(opcoes)
  fnRef.current = fn
  opcoesRef.current = opcoes

  const setAberto = useCallback((valor: boolean) => {
    if (!valor && emVoo.current) return
    setAbertoState(valor)
  }, [])

  const executar = useCallback(() => {
    if (emVoo.current) return emVoo.current
    // A ação e os textos de QUANDO se confirmou: mexer no formulário durante a
    // espera não muda o que foi enviado nem o que o toast vai dizer.
    const acao = fnRef.current
    const { sucesso, erro, aoConcluir } = opcoesRef.current
    setExecutando(true)

    const rodada = (async () => {
      let res: RespostaDaAcao<R>
      try {
        res = await acao()
      } catch (e) {
        res = { error: { name: "Error", message: e instanceof Error ? e.message : undefined } }
      }
      setExecutando(false)
      if (res?.error) {
        const texto = erro(res.error.message, res.error)
        if (texto) mostrar(createToast.error, texto)
        return
      }
      const dados = res?.data as R
      const texto = typeof sucesso === "function" ? sucesso(dados) : sucesso
      if (texto) mostrar(createToast.success, texto)
      setAbertoState(false)
      aoConcluir?.(dados)
    })().finally(() => { emVoo.current = null })

    emVoo.current = rodada
    return rodada
  }, [])

  return { aberto, setAberto, executando, executar }
}

function mostrar(toast: (titulo: string, descricao?: string) => unknown, texto: TextoDeToast) {
  if (typeof texto === "string") toast(texto)
  else toast(texto[0], texto[1])
}
