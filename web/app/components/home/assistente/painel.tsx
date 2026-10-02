"use client"

// web/app/components/home/assistente/painel.tsx
//
// A conversa FLUTUANTE sobre o globo — fork da gaveta do editor (`assistente/
// index.tsx`), com o contrato de altura do #111 e sem os `nowheel/nopan/nodrag`
// (aqui não há React Flow embaixo). O aberto/recolhido vive no `homeStore`; a
// largura, no `useResizablePanel`.

import { useCallback, useEffect, useRef } from "react"
import { TbChevronDown, TbPencilPlus, TbPlayerStopFilled, TbSend, TbSparkles } from "react-icons/tb"

import { Button } from "@/app/components/ui/button"
import { Textarea } from "@/app/components/ui/textarea"
import { cn } from "@/lib/utils"
import { useIsMobile } from "@/hooks/use-mobile"
import { useResizablePanel } from "@/app/hooks/useResizablePanel"
import { useHomeStore } from "@/app/stores/homeStore"
import Conversa from "@/app/components/home/assistente/conversa"
import type { TurnoDoAssistente } from "@/app/components/home/assistente/quadros"
import type { IAssistenteEstado } from "@/service/types"
import type { ResultadoDaDecisao } from "@/app/hooks/home/useAssistente"
import BadgeArtefatos from "./badge-artefatos"
import {
  AvisoDeAnexosRecusados, ChipsDeAnexo, ConviteDeSoltura,
  anexosProntos, comReferencia, sugestaoParaAnexos,
} from "@/app/components/home/assistente/anexos"
import { BotaoMais, ChipDeLocalizacao } from "@/app/components/home/assistente/mais"
import { AvisoDeCotaCheia } from "@/app/components/home/assistente/aviso-de-cota"
import UsoDaCota from "@/app/components/home/assistente/uso-da-cota"
import { useExtrasDoAssistente } from "./extras"
import MarcaAnimada from "./marca-animada"
import { useIdiomaDaTela, useTextos } from "../i18n"

const CHAVE_LARGURA = "atlans:home:largura"

interface Props {
  estado: IAssistenteEstado | null
  turnos: TurnoDoAssistente[]
  correndo: boolean
  /** O replay da conversa selecionada ainda está vindo. */
  carregandoReplay?: boolean
  /** Devolve o foco ao campo quando o painel abriu por atalho/botão. */
  autoFoco?: boolean
  enviar: (mensagem: string) => Promise<void> | void
  confirmar: (toolUseId: string, token: string, decisao: "confirmar" | "recusar") => Promise<ResultadoDaDecisao> | void
  parar: () => void
  /** Anexa arquivos escolhidos no "+" (o mesmo caminho do arraste). */
  aoAnexar?: (arquivos: File[]) => void
  /** Aciona o controle de localização do globo (o "Usar minha localização" do "+"). */
  aoPedirLocalizacao?: () => void
}

export default function Painel({
  estado, turnos, correndo, carregandoReplay = false, autoFoco = false,
  enviar, confirmar, parar, aoAnexar, aoPedirLocalizacao,
}: Props) {
  const recolher = useHomeStore((s) => s.recolherBarra)
  const novaConversa = useHomeStore((s) => s.novaConversa)
  // Os cartões (confirmação, camada, respostas rápidas) e a regra "clicou,
  // travou" vivem no hook partilhado com a faixa ao centro: são a MESMA
  // conversa em duas vistas.
  const extras = useExtrasDoAssistente({ confirmar, correndo, enviar })
  const isMobile = useIsMobile()
  const idioma = useIdiomaDaTela()
  const t = useTextos().assistente

  // O rascunho também vive na store: Ctrl+I recolhe para a barra e DESMONTA
  // este painel — num estado local, o atalho apagava o que estava escrito.
  // Partilhado com a barra, o texto atravessa a troca nos dois sentidos.
  const rascunho = useHomeStore((s) => s.rascunho)
  const definirRascunho = useHomeStore((s) => s.definirRascunho)
  // Os anexos, pelo mesmo motivo: o recurso não pode sumir só porque a pessoa
  // recolheu a barra em painel (a gaveta do editor foi o achado 4 da revisão 3
  // — um recurso numa superfície e não na outra).
  const anexos = useHomeStore((s) => s.anexos)
  const arrastando = useHomeStore((s) => s.arrastandoArquivo)
  const removerAnexo = useHomeStore((s) => s.removerAnexo)
  const limparAnexosProntos = useHomeStore((s) => s.limparAnexosProntos)
  const descartarAnexosRecusados = useHomeStore((s) => s.descartarAnexosRecusados)
  const campoRef = useRef<HTMLTextAreaElement>(null)

  // Alternar desmonta o componente focado e o foco cai no <body>: o próximo Tab
  // recomeça do topo do documento. Só quando a troca foi pedida (atalho/botão) —
  // roubar o foco na carga da página seria pior.
  useEffect(() => {
    if (autoFoco) campoRef.current?.focus()
  }, [autoFoco])

  const { width, isResizing, resizeHandleProps } = useResizablePanel({
    storageKey: CHAVE_LARGURA,
    defaultWidth: 420,
    minWidth: 340,
    maxWidth: 600,
    side: "right",
    enabled: !isMobile,
  })

  const submeter = useCallback(() => {
    const texto = rascunho.trim()
    // Com anexo pronto e campo vazio, o envio é a referência sozinha — quem
    // soltou o arquivo já disse o que quer. Só os PRONTOS entram e só eles saem.
    if (!texto && anexosProntos(anexos).length === 0) return
    if (correndo) return
    definirRascunho("")
    void enviar(comReferencia(texto, anexos, idioma))
    limparAnexosProntos()
  }, [rascunho, correndo, enviar, definirRascunho, anexos, limparAnexosProntos, idioma])

  const cota = estado?.cota ?? null
  const estourou = cota != null && cota.gasto >= cota.teto

  // A pergunta sugerida quando há anexo pronto — a mesma da barra.
  const sugestaoDeAnexo = sugestaoParaAnexos(anexos, idioma)
  const temAnexoPronto = sugestaoDeAnexo !== null

  return (
    <aside
      // A largura vai por CSS var, e o telefone é decidido por MEDIA QUERY e
      // não por JS: o `useIsMobile` devolve `false` no 1º render de cada
      // instância, e um painel de 420px ancorado à direita nascia com 84px
      // fora da tela num telefone de 360px antes de saltar para tela cheia.
      //
      // `absolute` e não `fixed`: a raiz da HomeView já é `relative` e começa
      // DEPOIS do sidebar. Fixo, o canto de referência era o da viewport, e o
      // painel/barra pintavam por cima do HomeSidebar.
      style={{ "--largura-painel": `${width}px` } as React.CSSProperties}
      className={cn(
        // Entra da direita, com fade (globals.css); zero sob `prefers-reduced-motion`.
        "home dark home-painel-entra absolute z-30 flex flex-col overflow-hidden rounded-xl border border-border bg-background shadow-2xl",
        "max-md:inset-x-3 max-md:bottom-3 max-md:top-16 max-md:pb-safe",
        "md:bottom-6 md:right-6 md:h-[min(640px,calc(100svh-6rem))] md:max-h-[calc(100svh-3rem)] md:w-[var(--largura-painel)]",
        !isResizing && "motion-safe:transition-[width]",
      )}
      aria-label={t.painel.titulo}
    >
      {!isMobile && (
        <div
          {...resizeHandleProps}
          // Depois do spread: o hook rotula a alça em português (é dele o
          // resto do app); aqui ela fala o idioma da Home.
          aria-label={t.painel.redimensionar}
          title={t.painel.dicaRedimensionar}
          className="group/alca absolute inset-y-0 -left-1 z-10 w-2 cursor-col-resize touch-none focus-visible:outline-none"
        >
          <span className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-transparent transition-colors group-hover/alca:bg-primary group-focus-visible/alca:bg-primary" />
        </div>
      )}

      <header className="flex h-11 shrink-0 items-center gap-2 border-b border-border px-3">
        <TbSparkles size={16} className="text-primary" aria-hidden="true" />
        <h2 className="flex-1 truncate text-sm font-semibold">{t.painel.titulo}</h2>

        <Button
          variant="ghost"
          size="icon"
          onClick={() => novaConversa()}
          className="size-8 max-md:size-10"
          aria-label={t.painel.novaConversa}
          title={t.painel.novaConversa}
        >
          <TbPencilPlus size={15} aria-hidden="true" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => recolher()}
          className="size-8 max-md:size-10"
          aria-label={t.painel.recolher}
          title={t.painel.recolher}
        >
          <TbChevronDown size={15} aria-hidden="true" />
        </Button>
      </header>

      <BadgeArtefatos turnos={turnos} />

      <Conversa
        turnos={turnos}
        correndo={correndo}
        extras={extras}
        nome={t.nome}
        // A conversa vazia padrão é a do EDITOR: manda descrever um fluxo e
        // fala em aplicar no canvas, que aqui não existe.
        vazio={carregandoReplay ? <CarregandoConversa /> : <Primeira />}
        // O item pendente com a marca do site: aqui quem pensa é o site.
        indicador={MarcaAnimada}
        // O cursor terracota no fim do parágrafo que está sendo escrito.
        cursorAoEscrever
      />

      {estourou && cota && (
        <AvisoDeCotaCheia
          cota={cota}
          plano={estado?.plano}
          assinaturasAtivas={estado?.assinaturas_ativas}
          className="mx-3 mb-2 shrink-0 justify-start rounded-md px-2.5 py-1.5"
        />
      )}

      <AvisoDeAnexosRecusados anexos={anexos} onFechar={descartarAnexosRecusados} className="mx-3 mb-2 shrink-0" />

      <form
        className="shrink-0 border-t border-border p-2"
        // O realce do arraste na gaveta segue o mesmo contrato da barra
        // (`data-arraste`), só que aqui o alvo é o composer, não uma pílula.
        data-arraste={arrastando}
        onSubmit={(e) => { e.preventDefault(); submeter() }}
      >
        {arrastando && <ConviteDeSoltura className="mb-2 px-1" />}
        <ChipsDeAnexo anexos={anexos} onRemover={removerAnexo} className="mb-2 px-0.5" />
        <ChipDeLocalizacao className="mb-2 px-0.5" />
        <div className="flex items-end gap-2">
          {(aoAnexar || aoPedirLocalizacao) && (
            <BotaoMais aoAnexar={aoAnexar} aoLocalizar={aoPedirLocalizacao} className="size-9 max-md:size-10" />
          )}
          <Textarea
            ref={campoRef}
            value={rascunho}
            onChange={(e) => definirRascunho(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submeter() }
            }}
            rows={2}
            maxLength={8000}
            disabled={estourou}
            placeholder={sugestaoDeAnexo ?? t.barra.placeholder}
            className="max-h-40 min-h-[2.75rem] resize-none text-sm"
            aria-label={t.barra.rotuloDoCampo}
          />
          {correndo ? (
            <Button type="button" variant="outline" size="icon" onClick={parar} className="size-9 shrink-0 max-md:size-10" aria-label={t.painel.parar} title={t.painel.parar}>
              <TbPlayerStopFilled size={14} aria-hidden="true" />
            </Button>
          ) : (
            <Button type="submit" size="icon" disabled={(!rascunho.trim() && !temAnexoPronto) || estourou} className="size-9 shrink-0 active:scale-90 max-md:size-10" aria-label={t.barra.enviar}>
              <TbSend size={15} aria-hidden="true" />
            </Button>
          )}
        </div>
        {cota != null && (
          <div className="mt-1.5 flex justify-end">
            <UsoDaCota cota={cota} />
          </div>
        )}
      </form>
    </aside>
  )
}

/**
 * O convite da Home. O da Conversa é o do EDITOR — manda descrever um fluxo e
 * fala em "aplicar no canvas", duas coisas que não existem em `/` e que ainda
 * contradiziam o placeholder logo abaixo ("O que você quer saber?").
 */
function Primeira() {
  const t = useTextos().assistente.painel
  return (
    <div className="flex min-h-full flex-col items-center justify-center gap-3 px-6 py-10 text-center">
      <span className="rounded-full bg-muted/60 p-4" aria-hidden="true">
        <TbSparkles size={22} className="text-muted-foreground/50" />
      </span>
      <p className="text-sm font-semibold text-foreground">{t.primeiraTitulo}</p>
      <p className="text-xs leading-relaxed text-muted-foreground">
        {t.primeiraTexto}
      </p>
      <p className="rounded-md bg-muted/50 px-2.5 py-2 text-left text-xs italic text-muted-foreground">
        {t.primeiraExemplo}
      </p>
    </div>
  )
}

/** O replay da conversa está a caminho — não é uma conversa vazia. */
function CarregandoConversa() {
  const t = useTextos().assistente.painel
  return (
    <div className="flex min-h-full flex-col justify-end gap-3 px-1 py-2" role="status">
      <span className="sr-only">{t.carregandoConversa}</span>
      <span className="h-3 w-2/5 animate-pulse rounded bg-muted/60" aria-hidden="true" />
      <span className="ml-auto h-8 w-3/5 animate-pulse rounded-lg bg-primary/10" aria-hidden="true" />
      <span className="h-3 w-4/5 animate-pulse rounded bg-muted/60" aria-hidden="true" />
      <span className="h-3 w-3/5 animate-pulse rounded bg-muted/60" aria-hidden="true" />
    </div>
  )
}
