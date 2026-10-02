"use client"

// web/app/components/workflow/assistente/index.tsx
//
// A gaveta do assistente — coluna ANCORADA à direita do canvas.
//
// **Não é o `Sheet`** do shadcn: aquilo é sobreposição modal com overlay, e
// escurecer o canvas seria esconder justamente o que a conversa está montando.
// Aqui a gaveta é irmã flex do React Flow: o canvas ENCOLHE, os dois ficam
// visíveis, e dá para ver o fluxo aparecer enquanto se lê a explicação. É o
// mesmo motivo pelo qual o `run-panel` deixou de ser um Sheet.
//
// O arraste vem do `useResizablePanel`, que já resolve pointer capture,
// teclado, clamp de viewport e a memória da largura no `localStorage`.

import { useCallback, useEffect, useState } from "react"
import { TbDotsVertical, TbPlayerStopFilled, TbSend, TbSparkles, TbX } from "react-icons/tb"

import { Button } from "@/app/components/ui/button"
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/app/components/ui/dropdown-menu"
import { Textarea } from "@/app/components/ui/textarea"
import { cn } from "@/lib/utils"
import { useResizablePanel } from "@/app/hooks/useResizablePanel"
import { useAssistenteEditor } from "@/app/hooks/workflow/useAssistenteEditor"
import { useAssistenteEditorStore } from "@/app/stores/assistenteEditorStore"
import { AvisoDeCotaCheia } from "@/app/components/home/assistente/aviso-de-cota"
import type { ResultadoDaProposta } from "../utils/aplicar-proposta"
import Conversa from "@/app/components/home/assistente/conversa"
import CartaoProposta from "./cartao-proposta"
import UsoDaCota from "@/app/components/home/assistente/uso-da-cota"

const CHAVE_LARGURA = "atlans:assistente:largura"

// A F4 renomeou a chave da largura (era atlans:copiloto:largura) sem migração.
// Copia a antiga para a nova UMA vez, no carregamento do módulo (só no
// cliente), antes de qualquer useResizablePanel ler a preferência.
;(function migrarLarguraLegada() {
  try {
    if (typeof window === "undefined") return
    if (window.localStorage.getItem(CHAVE_LARGURA) !== null) return
    const legada = window.localStorage.getItem("atlans:copiloto:largura")
    if (legada !== null) window.localStorage.setItem(CHAVE_LARGURA, legada)
  } catch { /* preferência descartável */ }
})()

interface Props {
  /** O fluxo aberto. Ausente na tela de criar — o backend guarda essa conversa à parte. */
  workflowId?: string
  /**
   * Abre por padrão quando não há preferência guardada. Verdadeiro na tela de
   * criar, onde o canvas nasce vazio e a gaveta é o caminho mais curto.
   */
  abrirPorPadrao?: boolean
  onAplicar: (resultado: ResultadoDaProposta) => void
}

export default function AssistentePainel({ workflowId, abrirPorPadrao = false, onAplicar }: Props) {
  const aberto = useAssistenteEditorStore(s => s.aberto)
  const fechar = useAssistenteEditorStore(s => s.fechar)
  const alternar = useAssistenteEditorStore(s => s.alternar)
  const hidratar = useAssistenteEditorStore(s => s.hidratar)

  const { estado, consultando, turnos, correndo, enviar, parar, esquecer } = useAssistenteEditor(workflowId)
  const [rascunho, setRascunho] = useState("")
  // O aceite de desenhar num canvas que JÁ TEM trabalho, uma vez por conversa.
  // Zera ao trocar de fluxo e ao recomeçar a conversa, pelos mesmos motivos que
  // a conversa zera: é outra conversa, e o consentimento não atravessa.
  const [liberado, setLiberado] = useState(false)
  useEffect(() => { setLiberado(false) }, [workflowId])

  useEffect(() => { hidratar(abrirPorPadrao) }, [hidratar, abrirPorPadrao])

  // Ctrl+I, no molde do Ctrl+` do dock de execução — e com a mesma guarda: sem
  // ela, o atalho dispararia enquanto alguém digita a query SQL de um nó.
  useEffect(() => {
    function editando(alvo: EventTarget | null) {
      const el = alvo as HTMLElement | null
      return !!el && (el.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName))
    }
    function aoTeclar(e: KeyboardEvent) {
      if (editando(e.target)) return
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "i") {
        e.preventDefault()
        alternar()
      }
    }
    window.addEventListener("keydown", aoTeclar)
    return () => window.removeEventListener("keydown", aoTeclar)
  }, [alternar])

  const { width, isResizing, resizeHandleProps } = useResizablePanel({
    storageKey: CHAVE_LARGURA,
    defaultWidth: 380,
    minWidth: 300,
    maxWidth: 560,
    side: "right",
    enabled: aberto,
  })

  const submeter = useCallback(() => {
    const texto = rascunho.trim()
    if (!texto || correndo) return
    setRascunho("")
    void enviar(texto)
  }, [rascunho, correndo, enviar])

  // Desligado na instalação: a gaveta não existe, e nada no editor muda. É o
  // comportamento certo para quem roda o Atlans sem a dependência externa.
  if (consultando || estado?.ativo !== true) return null

  if (!aberto) {
    return (
      <Button
        variant="outline"
        size="icon"
        onClick={alternar}
        title="Assistente (Ctrl+I)"
        aria-label="Abrir o assistente"
        className="absolute right-5 top-[4.5rem] z-10 size-11 rounded-lg shadow-lg max-md:hidden"
      >
        <TbSparkles size={20} aria-hidden="true" />
      </Button>
    )
  }

  const cota = estado.cota ?? null
  const estourou = cota != null && cota.gasto >= cota.teto

  return (
    <aside
      // nowheel/nopan/nodrag: sem eles o React Flow captura a rolagem da
      // conversa e o arraste da alça, e rolar a lista dava zoom no grafo.
      //
      // `max-h-svh` e o TETO, e sem ele o `overflow-y-auto` da conversa nao
      // rola nunca. A casca do dashboard e `min-h-svh` (`ui/sidebar.tsx`), que
      // e PISO e nao teto: como esta gaveta e o unico filho EM FLUXO do
      // container do editor — todo o resto la dentro e `absolute` —, a
      // contribuicao intrinseca dela e a conversa inteira, e a altura sobe pela
      // cadeia ate a pagina crescer. Ai a rolagem vai para o viewport em vez da
      // lista, e o campo de enviar sai da tela. O teto quebra essa
      // circularidade num ponto so.
      //
      // `h-full` FICA junto: sozinho, o `h-svh` desacoplaria a gaveta da caixa
      // que a contem e transbordaria no dia em que houvesse um cabecalho
      // acima. O par diz "seja a altura que te deram, mas nao passe de uma
      // tela".
      //
      // `svh` e nao `dvh`, e o motivo esta no piso: `dvh >= svh`, entao um teto
      // em `dvh` fica ACIMA do `min-h-svh` da casca e o defeito voltaria com a
      // barra de endereco retraida — intermitente, que e pior. Os usos de
      // `dvh` do repositorio (`ui/dialog.tsx` e os modais que o usam) sao o
      // caso oposto: caixas que precisam caber num alvo que se mexe. Esta e casca,
      // como o `h-svh` do container da sidebar, e casca nao pode refluir no
      // meio da rolagem.
      className={cn(
        "nowheel nopan nodrag relative z-20 flex h-full max-h-svh shrink-0 flex-col border-l border-border bg-background",
        // No telefone a gaveta toma a tela: um canvas de 360px dividido em dois
        // não serve para nenhum dos dois.
        "max-md:absolute max-md:inset-0 max-md:w-full max-md:border-l-0",
        !isResizing && "motion-safe:transition-[width]",
      )}
      style={{ width }}
      aria-label="Assistente"
      onContextMenu={e => e.stopPropagation()}
    >
      <div
        {...resizeHandleProps}
        className="group/alca absolute inset-y-0 -left-1 z-10 w-2 cursor-col-resize touch-none max-md:hidden focus-visible:outline-none"
      >
        <span className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-transparent transition-colors group-hover/alca:bg-primary group-focus-visible/alca:bg-primary" />
      </div>

      <header className="flex h-11 shrink-0 items-center gap-2 border-b border-border px-3">
        <TbSparkles size={16} className="text-primary" aria-hidden="true" />
        <h2 className="flex-1 truncate text-sm font-semibold">Assistente</h2>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="size-8 max-md:size-10" aria-label="Mais ações do assistente">
              <TbDotsVertical size={15} aria-hidden="true" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => { setLiberado(false); void esquecer() }}>
              Recomeçar a conversa
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <Button
          variant="ghost"
          size="icon"
          onClick={fechar}
          className="size-8 max-md:size-10"
          aria-label="Fechar o assistente"
          title="Fechar (Ctrl+I)"
        >
          <TbX size={15} aria-hidden="true" />
        </Button>
      </header>

      <Conversa
        turnos={turnos}
        correndo={correndo}
        proposta={(p) => (
          <CartaoProposta
            proposta={p}
            onAplicar={onAplicar}
            liberado={liberado}
            onLiberar={() => setLiberado(true)}
          />
        )}
      />

      {estourou && cota && (
        // A TERCEIRA superfície do aviso. Ela tinha ficado com a cópia antiga:
        // sem a oferta e dizendo «reabre em algumas horas» com o prazo exato
        // na mão — a oferta (de uma extensão, ver `web/extensoes`) sumia
        // conforme a tela em que a pessoa bateu no teto, que é justamente o
        // que o componente existe para impedir.
        <AvisoDeCotaCheia
          cota={cota}
          plano={estado.plano}
          assinaturasAtivas={estado.assinaturas_ativas}
          className="mx-3 mb-2 shrink-0 justify-start rounded-md px-2.5 py-1.5"
        />
      )}

      <form
        className="shrink-0 border-t border-border p-2"
        onSubmit={e => { e.preventDefault(); submeter() }}
      >
        <div className="flex items-end gap-2">
          <Textarea
            value={rascunho}
            onChange={e => setRascunho(e.target.value)}
            // Enter envia, Shift+Enter quebra linha — o que todo campo de
            // conversa faz, e o oposto do que um textarea faz sozinho.
            onKeyDown={e => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                submeter()
              }
            }}
            rows={2}
            maxLength={8000}
            disabled={estourou}
            placeholder="Descreva o fluxo que você quer…"
            className="max-h-40 min-h-[2.75rem] resize-none text-sm"
            aria-label="Mensagem para o assistente"
          />
          {correndo ? (
            <Button
              type="button"
              variant="outline"
              size="icon"
              onClick={parar}
              className="size-9 shrink-0 max-md:size-10"
              aria-label="Parar"
              title="Parar"
            >
              <TbPlayerStopFilled size={14} aria-hidden="true" />
            </Button>
          ) : (
            <Button
              type="submit"
              size="icon"
              disabled={!rascunho.trim() || estourou}
              className="size-9 shrink-0 max-md:size-10"
              aria-label="Enviar"
            >
              <TbSend size={15} aria-hidden="true" />
            </Button>
          )}
        </div>
        {cota != null && (
          <div className="mt-1.5 flex justify-end">
            <UsoDaCota cota={cota} superficie="editor" />
          </div>
        )}
      </form>
    </aside>
  )
}
