"use client"

// web/app/components/home/assistente/extras.tsx
//
// Os blocos que a `Conversa` não conhece — a `confirmacao`, a `camada` e as
// `respostas_rapidas` da Home — desenhados do MESMO jeito nas duas vistas da
// conversa: o painel lateral e a faixa ao centro. Um modelo, dois lugares, um
// renderizador para os cartões; sem isto o cartão de confirmação existiria duas
// vezes, e a regra "clicou, travou" (que vive na store para sobreviver ao
// desmontar) teria duas cópias para divergir.

import { useCallback } from "react"

import { useHomeStore } from "@/app/stores/homeStore"
import type { ContextoDoBloco } from "@/app/components/home/assistente/conversa"
import type { BlocoDoAssistente } from "@/app/components/home/assistente/quadros"
import type { ResultadoDaDecisao } from "@/app/hooks/home/useAssistente"
import CartaoConfirmacao from "./cartao-confirmacao"
import CartaoCamada from "./cartao-camada"
import RespostasRapidas from "./respostas-rapidas"

export type Confirmar = (
  toolUseId: string, token: string, decisao: "confirmar" | "recusar",
) => Promise<ResultadoDaDecisao> | void

export type Enviar = (mensagem: string) => Promise<void> | void

/**
 * O `extras` da `Conversa` para a Home. `correndo` trava os cartões enquanto um
 * stream está no ar (o clique dispararia um segundo SSE por cima do primeiro) e
 * esconde as respostas rápidas (o `enviar` do hook volta em silêncio durante o
 * stream, e um chip que não faz nada é um botão morto).
 */
export function useExtrasDoAssistente({
  confirmar, correndo, enviar,
}: { confirmar: Confirmar; correndo: boolean; enviar: Enviar }) {
  // As confirmações já clicadas vivem na store, e não aqui: recolher o painel o
  // DESMONTA, e os turnos (com o token) sobrevivem — um Set local ressuscitava
  // o cartão decidido, e o segundo clique batia num token já consumido.
  const decididos = useHomeStore((s) => s.decididos)
  const expirados = useHomeStore((s) => s.expirados)
  const marcarDecidido = useHomeStore((s) => s.marcarDecidido)
  const desmarcarDecidido = useHomeStore((s) => s.desmarcarDecidido)
  const marcarExpirado = useHomeStore((s) => s.marcarExpirado)

  const onDecidir = useCallback(
    (toolUseId: string, token: string, decisao: "confirmar" | "recusar") => {
      if (decididos[toolUseId] || correndo) return
      marcarDecidido(toolUseId)
      // A marca é otimista, e o desfecho decide o que fica na tela: só uma
      // falha de transporte destrava (a ação não aconteceu e precisa de outra
      // chance). Um 409 mantém travado — a chave já foi consumida ou venceu, e
      // reabrir o cartão só ofereceria um clique que erra de novo.
      void Promise.resolve(confirmar(toolUseId, token, decisao)).then((resultado) => {
        if (resultado === "falhou") desmarcarDecidido(toolUseId)
        else if (resultado === "expirada") marcarExpirado(toolUseId)
      })
    },
    [decididos, correndo, confirmar, marcarDecidido, desmarcarDecidido, marcarExpirado],
  )

  return useCallback(
    (bloco: BlocoDoAssistente, contexto: ContextoDoBloco) => {
      if (bloco.tipo === "confirmacao") {
        return (
          <CartaoConfirmacao
            confirmacao={bloco.confirmacao}
            decidido={!!decididos[bloco.confirmacao.tool_use_id]}
            expirado={!!expirados[bloco.confirmacao.tool_use_id]}
            ocupado={correndo}
            onDecidir={onDecidir}
          />
        )
      }
      if (bloco.tipo === "camada") return <CartaoCamada camada={bloco.camada} />
      if (bloco.tipo === "respostas_rapidas") {
        // Valem só para aquela vez: só no ÚLTIMO turno e fora do stream. O
        // clique manda a frase como a próxima mensagem — o turno novo tira os
        // chips da tela sozinho; digitar também. No replay os do último turno
        // voltam: a conversa ESTÁ naquele ponto.
        if (!contexto.ultimoTurno || correndo) return null
        return <RespostasRapidas opcoes={bloco.opcoes} onEscolher={enviar} />
      }
      // `fluxo` NÃO é renderizado em lugar nenhum — nem aqui, nem na faixa de
      // badges, que mostra os artefatos. A Home é a única página de quem não
      // administra o sistema, e o fluxo do assistente não é alcançável daqui;
      // ele continua em Projetos, com o interruptor "mostrar os do assistente"
      // ligado. O quadro segue chegando e sendo decodificado — o que some é a
      // oferta.
      return null
    },
    [decididos, expirados, correndo, onDecidir, enviar],
  )
}
