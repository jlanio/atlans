"use client"

// web/app/components/workflow/assistente/cartao-proposta.tsx
//
// O cartão da proposta — e, agora, DOIS papéis.
//
// `desenhar: true` vem de `desenhar_no_canvas` e significa "põe na tela agora".
// O fluxo aparece sozinho, enquanto o modelo monta: é o que torna a construção
// incremental em vez de um único despejo no fim.
//
// `desenhar: false` vem de `validate_workflow` e traz só o veredito do que já
// está desenhado. Não há botão: o fluxo já está lá.
//
// A exceção é o canvas que JÁ TEM trabalho. Aí o primeiro desenho da conversa
// espera um clique — e depois dele a conversa desenha sozinha, sem interromper
// de novo. Não é `window.confirm`: ele trava a thread, e travar a thread no
// meio de um stream é parar de ler o stream.
//
// O assistente continua NÃO gravando: desenhar é rascunho no canvas, e o Salvar
// do editor continua sendo de quem está usando.

import { useEffect, useMemo, useRef } from "react"
import { useNodes } from "@xyflow/react"
import { TbAlertTriangle, TbCheck, TbWand } from "react-icons/tb"

import { Button } from "@/app/components/ui/button"
import { INodeContext } from "@/context/useFlowContext"
import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore"
import { plural } from "@/lib/formatos"
import { aplicarProposta, type ResultadoDaProposta } from "../utils/aplicar-proposta"
import type { PropostaDeFluxo } from "@/app/components/home/assistente/quadros"

interface Props {
  proposta: PropostaDeFluxo
  onAplicar: (resultado: ResultadoDaProposta) => void
  /** A conversa já pode desenhar sozinha num canvas que tinha trabalho. */
  liberado: boolean
  /** Chamado no primeiro desenho aceito, para os seguintes não perguntarem. */
  onLiberar: () => void
}

export default function CartaoProposta({ proposta, onAplicar, liberado, onLiberar }: Props) {
  const nodesAPI = useWorkflowCatalogStore(s => s.nodesAPI)
  // Assina o canvas AQUI, e não na gaveta: só este cartão precisa reagir ao que
  // está desenhado, e assinar lá em cima re-renderizaria a conversa inteira a
  // cada quadro de um arraste.
  const nos = useNodes<INodeContext>()

  const resultado = useMemo(
    () => aplicarProposta(proposta.definicao, nodesAPI, nos),
    [proposta.definicao, nodesAPI, nos],
  )

  const { novos, alterados, removidos } = resultado.resumo

  // Canvas vazio: nada a perder, desenha sempre. Canvas com trabalho: só depois
  // do primeiro aceite da conversa.
  const canvasVazio = nos.length === 0
  const desenhaSozinho = proposta.desenhar === true
    && resultado.catalogoPronto
    && (canvasVazio || liberado)

  // Uma vez por cartão. Sem a trava, qualquer re-render do canvas (um arraste,
  // um zoom) reaplicaria a mesma proposta e desfaria o que a pessoa acabou de
  // mexer — e `resultado` muda de identidade a cada render, então a lista de
  // dependências sozinha não segura.
  const jaDesenhou = useRef(false)
  useEffect(() => {
    if (!desenhaSozinho || jaDesenhou.current) return
    jaDesenhou.current = true
    onAplicar(resultado)
  }, [desenhaSozinho, onAplicar, resultado])
  // `ok: null` é "não sei" — o relatório da validação não pôde ser lido. Tratar
  // como "passou" seria oferecer aplicar um fluxo que ninguém confirmou.
  const validou = proposta.ok === true && (proposta.erros ?? 0) === 0

  return (
    <div className="mt-2 rounded-lg border bg-card p-3 shadow-xs" data-testid="cartao-proposta">
      <div className="flex items-start gap-2">
        <span className="mt-0.5 shrink-0" aria-hidden="true">
          {proposta.desenhar || validou
            ? <TbCheck size={16} className="text-green-600 dark:text-green-400" />
            : <TbAlertTriangle size={16} className="text-amber-600 dark:text-amber-400" />}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-foreground">
            {proposta.desenhar
              ? (desenhaSozinho ? "Desenhado no canvas" : "Pronto para desenhar")
              : (validou ? "Validação limpa" : "Validação com pendências")}
          </p>
          {proposta.nota && (
            <p className="break-words text-xs text-muted-foreground">{proposta.nota}</p>
          )}
          <p className="text-xs tabular-nums text-muted-foreground">
            {plural(proposta.nos, "nó", "nós")} · {plural(proposta.arestas, "ligação", "ligações")}
            {proposta.avisos ? ` · ${plural(proposta.avisos, "aviso")}` : ""}
          </p>
        </div>
      </div>

      {!proposta.desenhar && !validou && (
        <p role="status" className="mt-2 rounded-md border border-amber-500/30 bg-amber-50 px-2.5 py-1.5 text-xs text-amber-700 dark:bg-amber-500/10 dark:text-amber-400">
          {proposta.erros != null && proposta.erros > 0
            ? `A validação apontou ${plural(proposta.erros, "erro")}. Peça o ajuste antes de aplicar.`
            : "A validação não pôde ser lida. Peça para validar de novo antes de aplicar."}
        </p>
      )}

      {!resultado.catalogoPronto && (
        <p role="status" className="mt-2 rounded-md border border-amber-500/30 bg-amber-50 px-2.5 py-1.5 text-xs text-amber-700 dark:bg-amber-500/10 dark:text-amber-400">
          O catálogo de nós ainda não carregou.
        </p>
      )}

      {/* A contagem do que MUDA no canvas. Só aparece quando há canvas: num
          fluxo vazio "4 novos" não informa nada que os 4 nós já não digam. */}
      {(alterados > 0 || removidos > 0) && (
        <p className="mt-2 text-xs tabular-nums text-muted-foreground">
          {[
            novos > 0 ? `${novos} ${novos === 1 ? "novo" : "novos"}` : null,
            alterados > 0 ? `${alterados} ${alterados === 1 ? "alterado" : "alterados"}` : null,
            removidos > 0 ? `${removidos} ${removidos === 1 ? "removido" : "removidos"}` : null,
          ].filter(Boolean).join(" · ")}
          {removidos > 0 && (
            <span className="block text-destructive">
              Aplicar substitui o canvas. O que não estiver no fluxo proposto some.
            </span>
          )}
        </p>
      )}

      {/* O botão só existe no caso que precisa de aceite: o primeiro desenho
          de uma conversa num canvas que já tinha trabalho. Depois dele, a
          conversa desenha sozinha e o rodapé some — interromper a cada nó seria
          o oposto de acompanhar o fluxo crescer. */}
      {proposta.desenhar && !desenhaSozinho && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            className="max-md:h-10"
            disabled={!resultado.catalogoPronto}
            onClick={() => {
              // A trava ANTES de liberar: liberar torna `desenhaSozinho`
              // verdadeiro, o efeito dispara, e sem isto o mesmo desenho
              // entraria duas vezes no canvas.
              jaDesenhou.current = true
              onLiberar()
              onAplicar(resultado)
            }}
          >
            <TbWand size={14} aria-hidden="true" />
            Desenhar no canvas
          </Button>
          <span className="min-w-0 text-[11px] text-muted-foreground">
            Desta vez em diante, esta conversa desenha sozinha. Ctrl+Z desfaz.
          </span>
        </div>
      )}

      {proposta.desenhar && desenhaSozinho && (
        <p className="mt-2 text-[11px] text-muted-foreground">
          Desenhar não salva — o Salvar continua seu.
        </p>
      )}
    </div>
  )
}
