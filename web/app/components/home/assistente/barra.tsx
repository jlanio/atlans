"use client"

// web/app/components/home/assistente/barra.tsx
//
// A barra de comando da Home, em DUAS variantes do MESMO elemento:
//
// - `hero`: o estado inicial de todo acesso. Centrada e maior (56 px, texto de
//   16 px), com anel e brilho discretos, sugestões DIGITADAS no campo vazio e
//   três chips abaixo. Enquanto o assistente processa a primeira pergunta, os
//   chips dão lugar a uma linha de status ("Trabalhando…", Esc para parar).
// - `rodape`: a barra de sempre, no rodapé, centrada NA ÁREA DO GLOBO (é
//   `absolute` dentro da raiz da HomeView, que já começa depois do sidebar).
//
// A troca é do MESMO nó do DOM: a HomeView muda `variante` no primeiro token da
// resposta e o CSS (`.home-barra`, em globals.css) anima posição, largura e
// altura em 900 ms; com `prefers-reduced-motion` a troca é imediata.
//
// Enviar NÃO abre o painel: a conversa segue ao centro (a faixa acima da
// barra). O chevron abre o painel lateral, para ler tudo.
//
// O envio tem sinal: um anel terracota pisca na caixa (`data-flash`, o `::after`
// de `.home-barra-caixa` em globals.css) e o botão afunda. E quando o painel
// abre, a barra não desmonta na hora: a HomeView a segura por um instante com
// `saindo`, e ela apaga com fade (`data-saindo`), sem cliques nem foco.
//
// A caixa também é o ALVO VISUAL do arraste de arquivos (`data-arraste`): quem
// aceita o arquivo é a janela inteira (`useArrasteDeArquivos`), mas o que
// acende é ela, e os arquivos viram chips logo acima — ver `anexos.tsx`.

import { useEffect, useRef, useState } from "react"
import { TbArrowUp, TbChevronUp, TbPlayerStopFilled, TbSparkles } from "react-icons/tb"

import { Button } from "@/app/components/ui/button"
import ExecActivity from "@/app/components/shared/exec-activity"
import {
  AvisoDeAnexosRecusados, ChipsDeAnexo, ConviteDeSoltura, comReferencia, sugestaoParaAnexos,
} from "@/app/components/home/assistente/anexos"
import { BotaoMais, ChipDeLocalizacao } from "@/app/components/home/assistente/mais"
import { AvisoDeCotaCheia } from "@/app/components/home/assistente/aviso-de-cota"
import { IndicadorDeEtapa, type Etapa } from "@/app/components/home/assistente/etapa"
import UsoDaCota from "@/app/components/home/assistente/uso-da-cota"
import MarcaAnimada from "@/app/components/home/assistente/marca-animada"
import { usePrefereMenosMovimento } from "@/app/hooks/usePrefereMenosMovimento"
import { useHomeStore } from "@/app/stores/homeStore"
import { cn } from "@/lib/utils"
import type { IAssistenteEstado } from "@/service/types"
import { useIdiomaDaTela, useTextos } from "../i18n"

export type VarianteDaBarra = "hero" | "rodape"

interface Props {
  enviar: (mensagem: string) => Promise<void> | void
  /** Há um stream em curso — o `enviar` do hook volta em silêncio. */
  correndo?: boolean
  estado?: IAssistenteEstado | null
  /** Devolve o foco ao campo quando a barra apareceu por atalho/botão. */
  autoFoco?: boolean
  /** `hero` no primeiro acesso; `rodape` depois da primeira resposta. */
  variante?: VarianteDaBarra
  /** Interrompe o stream: o botão de parar (e o Esc, pela HomeView). */
  parar?: () => void
  /** O painel abriu e a barra está saindo: fade, sem cliques, sem roubar o foco. */
  saindo?: boolean
  /**
   * A altura, em px, do que a barra empilha ACIMA da caixa (chips, convite,
   * aviso de recusados). A faixa (`Pilha`) é ancorada por baixo contando só a
   * caixa; sem saber desta altura, a barra cresceria para cima e cobriria o
   * "Expandir" da faixa — o mesmo bug do pill de cota (2026-09-19). A HomeView
   * repassa isto à faixa como folga. O aviso de cota NÃO entra aqui: ele já tem
   * a própria folga (`comAvisoDeCota`).
   */
  aoMedirExtras?: (altura: number) => void
  /** O passo atual da resposta (raciocínio ou a ferramenta em curso), mostrado
   *  no rodapé enquanto o assistente trabalha. `null` quando não há passo. */
  etapa?: Etapa | null
  /** Anexa arquivos escolhidos no "+" (o mesmo caminho do arraste). */
  aoAnexar?: (arquivos: File[]) => void
  /** Aciona o controle de localização do globo (o "Usar minha localização" do "+"). */
  aoPedirLocalizacao?: () => void
}

export default function Barra({
  enviar, correndo = false, estado, autoFoco = false, variante = "rodape", parar, saindo = false,
  aoMedirExtras, etapa = null, aoAnexar, aoPedirLocalizacao,
}: Props) {
  const idioma = useIdiomaDaTela()
  const t = useTextos().assistente
  const sugestoes = t.barra.sugestoes
  const abrir = useHomeStore((s) => s.abrirPainel)
  // O rascunho vive na store, partilhado com o painel: abrir/recolher (pelo
  // botão ou por Ctrl+I) desmonta esta caixa, e num estado local o que estava
  // escrito ia junto. Assim o texto simplesmente continua na caixa do outro.
  const rascunho = useHomeStore((s) => s.rascunho)
  const definirRascunho = useHomeStore((s) => s.definirRascunho)
  // Os arquivos soltos sobre a Home. Na store pelo mesmo motivo do rascunho:
  // Ctrl+I desmonta esta caixa e os chips iriam junto, com os uploads ainda
  // correndo e nada na tela dizendo isso.
  const anexos = useHomeStore((s) => s.anexos)
  const arrastando = useHomeStore((s) => s.arrastandoArquivo)
  const removerAnexo = useHomeStore((s) => s.removerAnexo)
  const limparAnexosProntos = useHomeStore((s) => s.limparAnexosProntos)
  const descartarAnexosRecusados = useHomeStore((s) => s.descartarAnexosRecusados)
  // Só para a medição/folga dos extras (o chip lê a store por conta própria).
  // Booleano DERIVADO de propósito: a posição muda a cada tick do modo seguir,
  // mas a altura dos extras só muda quando o chip entra/sai — inscrever no
  // objeto re-renderizava a barra (e re-media) a cada tick de GPS.
  const temLocalizacao = useHomeStore((s) => s.compartilharLocalizacao && s.localizacao !== null)
  const campoRef = useRef<HTMLInputElement>(null)
  // A régua dos extras acima da caixa: sua altura vira folga da faixa. Medida
  // em layout (antes da pintura) a cada mudança de conteúdo, e observada para
  // as quebras de linha que só o resize provoca.
  const extrasRef = useRef<HTMLDivElement>(null)
  const [focado, setFocado] = useState(false)
  // O flash do envio: liga ao enviar, desliga no fim da animação do `::after`
  // (o `animationend` do próprio elemento — um filho com animação infinita, como
  // o cursor, nunca o dispara). Sem movimento a animação é `none`, o flag fica
  // ligado sem efeito visível e o próximo envio o reusa.
  const [flash, setFlash] = useState(false)

  useEffect(() => {
    if (autoFoco) campoRef.current?.focus()
  }, [autoFoco])

  // O passo atual só no rodapé: no hero o "Trabalhando…" já ocupa esse espaço,
  // e o hero termina no envio de qualquer forma. Declarado AQUI (antes dos
  // efeitos) porque a medição abaixo depende dele: o indicador aparecer/sumir
  // muda a altura dos extras. Booleano de propósito — `etapa` é um objeto novo
  // por render, e como dep faria a medição rodar a cada quadro do stream; a
  // ALTURA só muda no aparecer/sumir (o rótulo trunca, nunca quebra linha).
  const mostrarEtapa = variante !== "hero" && etapa != null

  // Mede os extras a cada mudança de conteúdo (chips entram/saem, o aviso de
  // recusados abre/fecha, o passo aparece/some). `useEffect` e não
  // `useLayoutEffect` para não avisar no SSR (a convenção do repo); o atraso de
  // um quadro é imperceptível — os chips não animam, e o que este cálculo evita
  // é o overlap PERSISTENTE, não o de um quadro.
  useEffect(() => {
    if (extrasRef.current) aoMedirExtras?.(extrasRef.current.offsetHeight)
  }, [aoMedirExtras, anexos, arrastando, mostrarEtapa, temLocalizacao])

  // Observa o resize à parte: com muitos chips a fileira quebra em mais linhas
  // quando a janela estreita, sem que `anexos` mude. Montado uma vez (deps
  // estáveis), zera a folga só no DESMONTE real — a faixa não pode ficar
  // suspensa sobre uma barra que já saiu.
  useEffect(() => {
    const el = extrasRef.current
    if (!el || !aoMedirExtras) return
    const ro = new ResizeObserver(() => aoMedirExtras(el.offsetHeight))
    ro.observe(el)
    return () => { ro.disconnect(); aoMedirExtras(0) }
  }, [aoMedirExtras])

  const cota = estado?.cota ?? null
  const estourou = cota != null && cota.gasto >= cota.teto
  const bloqueado = correndo || estourou
  const hero = variante === "hero"

  // A pergunta que os anexos sugerem, quando há algum no Drive. Ela toma o
  // lugar das sugestões digitadas: oferecer "Mostre os focos de calor" a quem
  // acabou de soltar um shapefile é ignorar o que a pessoa fez.
  const sugestaoDeAnexo = sugestaoParaAnexos(anexos, idioma)
  const temAnexoPronto = sugestaoDeAnexo !== null
  // Há algo acima da caixa (chips, aviso de recusados, o passo, a localização) ou o convite.
  const temExtras = anexos.length > 0 || arrastando || mostrarEtapa || temLocalizacao

  // A sugestão digitada só existe no hero, com o campo vazio e nada correndo.
  const sugestaoVisivel = hero && rascunho === "" && !correndo && !estourou && !temAnexoPronto
  const { texto: sugestao, indice } = useSugestaoDigitada(sugestaoVisivel, sugestoes)

  function submeter() {
    const digitado = rascunho.trim()
    // Campo vazio envia a sugestão da vez — é o "Enter envia" da dica. Com
    // anexo pronto a sugestão é a dele, e vale nas DUAS variantes: quem soltou
    // um arquivo já disse o que quer, mesmo fora do hero.
    const texto = digitado || sugestaoDeAnexo || (sugestaoVisivel ? (sugestoes[indice] ?? "") : "")
    if (!texto) return
    // Com um stream em curso (ou a cota estourada) o `enviar` do hook volta em
    // silêncio: a frase digitada sumia para sempre sem nenhum sinal. Aqui o
    // envio simplesmente não acontece e o rascunho fica à vista, na mesma
    // caixa, para ir quando o stream acabar.
    if (bloqueado) return
    definirRascunho("")
    // A mensagem leva a lista do que subiu — sem ela, «analise isso» chega ao
    // assistente sem nenhum «isso». Só os PRONTOS entram, e só eles saem da
    // caixa: o que ainda sobe não estava na mensagem, e o recusado nunca teve
    // relação com ela.
    void enviar(comReferencia(texto, anexos, idioma))
    limparAnexosProntos()
    setFlash(true)
  }

  function aoTeclar(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault()
      submeter()
      return
    }
    if (e.key === "Tab" && !e.shiftKey && sugestaoVisivel) {
      // Tab aceita a sugestão em vez de sair do campo — é o que a dica promete.
      e.preventDefault()
      definirRascunho(sugestoes[indice] ?? "")
    }
  }

  function escolherChip(chip: string) {
    definirRascunho(chip)
    campoRef.current?.focus()
  }

  const placeholder = correndo
    ? t.barra.respondendo
    : sugestaoDeAnexo ?? t.barra.placeholder

  return (
    <div className="home dark home-barra pb-safe" data-variante={variante} data-saindo={saindo} data-testid="barra">
      {estourou && cota && (
        <AvisoDeCotaCheia
          cota={cota}
          plano={estado?.plano}
          assinaturasAtivas={estado?.assinaturas_ativas}
          className="mb-1.5 justify-center rounded-full px-3 py-1 text-center"
        />
      )}

      {/* Tudo o que empilha ACIMA da caixa mora nesta régua, e é a altura dela
          que a faixa recebe como folga (aoMedirExtras). O aviso de cota fica
          FORA dela de propósito — ele já tem folga própria.

          `flex flex-col gap` (não `mb` nos filhos) e `pb` quando há conteúdo:
          assim o vão até a caixa entra no `offsetHeight`. Com `mb` no último
          filho, a margem colapsava para FORA da altura medida, e a faixa subia
          ~6 px de menos — encostando de novo no "Expandir". Vazio, sem `pb`,
          mede zero. */}
      <div ref={extrasRef} className={cn("flex flex-col gap-1.5", temExtras && "pb-1.5")}>
        <AvisoDeAnexosRecusados anexos={anexos} onFechar={descartarAnexosRecusados} />

        {/* Acima da caixa, e não dentro: ela é um `rounded-full` de 44 px (56 no
            hero) e não tem onde pôr uma fileira que quebra linha. */}
        {arrastando && <ConviteDeSoltura className="justify-center" />}
        <ChipsDeAnexo anexos={anexos} onRemover={removerAnexo} className="justify-center" />
        <ChipDeLocalizacao className="justify-center" />
        {/* O passo da vez, enquanto o assistente trabalha. */}
        {mostrarEtapa && etapa && <IndicadorDeEtapa etapa={etapa} className="justify-center px-1" />}
      </div>

      <div
        className="home-barra-caixa flex items-center gap-2 rounded-full border border-border bg-background/95 pl-2.5 pr-1.5 backdrop-blur"
        data-flash={flash}
        // O realce do arraste. A área que ACEITA o arquivo é a janela inteira
        // (useArrasteDeArquivos); quem acende é só a caixa — nenhum véu cobre
        // o globo, que é a escolha desta opção.
        data-arraste={arrastando}
        onAnimationEnd={(e) => { if (e.target === e.currentTarget) setFlash(false) }}
      >
        <span className="home-barra-ico grid shrink-0 place-items-center rounded-full text-primary" aria-hidden="true">
          {correndo ? <ExecActivity size={hero ? 16 : 14} /> : <TbSparkles size={hero ? 17 : 16} />}
        </span>
        {(aoAnexar || aoPedirLocalizacao) && (
          <BotaoMais aoAnexar={aoAnexar} aoLocalizar={aoPedirLocalizacao} className="home-barra-btn rounded-full" />
        )}
        <div className="relative flex h-full min-w-0 flex-1 items-center">
          <input
            ref={campoRef}
            value={rascunho}
            onChange={(e) => definirRascunho(e.target.value)}
            onKeyDown={aoTeclar}
            onFocus={() => setFocado(true)}
            onBlur={() => setFocado(false)}
            maxLength={8000}
            disabled={estourou}
            autoComplete="off"
            placeholder={sugestaoVisivel ? "" : placeholder}
            aria-describedby={sugestaoVisivel ? "home-barra-dica" : undefined}
            className="home-barra-campo w-full min-w-0 bg-transparent text-foreground outline-none placeholder:text-muted-foreground disabled:opacity-60"
            aria-label={t.barra.rotuloDoCampo}
          />
          {sugestaoVisivel && (
            <span
              className="home-barra-sugestao pointer-events-none absolute inset-0 flex items-center overflow-hidden text-ellipsis whitespace-nowrap text-muted-foreground"
              aria-hidden="true"
              data-testid="sugestao"
            >
              {sugestao}
              <span className="home-caret" />
            </span>
          )}
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={abrir}
          className="home-barra-btn shrink-0 rounded-full text-muted-foreground"
          aria-label={t.barra.abrir}
          title={t.barra.abrirTitulo}
        >
          <TbChevronUp size={15} aria-hidden="true" />
        </Button>
        {correndo && parar ? (
          <Button
            type="button"
            variant="outline"
            size="icon"
            onClick={parar}
            className="home-barra-btn shrink-0 rounded-full"
            aria-label={t.barra.parar}
            title={t.barra.pararTitulo}
          >
            <TbPlayerStopFilled size={14} aria-hidden="true" />
          </Button>
        ) : (
          <Button
            size="icon"
            onClick={submeter}
            disabled={(!rascunho.trim() && !sugestaoVisivel && !temAnexoPronto) || bloqueado}
            // A pressão: afunda mais que o `active:scale-[0.98]` de todo botão.
            className="home-barra-btn shrink-0 rounded-full active:scale-90"
            aria-label={t.barra.enviar}
          >
            <TbArrowUp size={15} aria-hidden="true" />
          </Button>
        )}
      </div>

      {(cota != null || sugestaoVisivel) && (
        // A linha de meta sob a caixa, à direita — o lugar do indicador de
        // contexto do Claude Code, que foi a referência do dono. A dica de
        // digitação (visível só com o cursor no campo; fora dele continua no
        // DOM para o leitor de tela, que é quem não vê a frase digitada) e o
        // donut da cota dividem a mesma linha para não disputarem o canto.
        <div className="home-barra-meta flex items-center justify-end gap-3 pr-2">
          {sugestaoVisivel && (
            <p
              id="home-barra-dica"
              className={cn("text-[11px] text-muted-foreground/80", !focado && "sr-only")}
            >
              {t.barra.dica}
            </p>
          )}
          {cota != null && <UsoDaCota cota={cota} />}
        </div>
      )}

      {hero && (correndo ? (
        <p role="status" className="home-chips flex items-center justify-center gap-2 text-sm text-muted-foreground">
          {/* A marca do site pensando (a mesma do item pendente da conversa) e o
              texto com um brilho que varre — parado, o status parecia travado. */}
          <MarcaAnimada size={15} /> <span className="texto-pensando">{t.barra.trabalhando}</span>
          {parar && (
            <button
              type="button"
              onClick={parar}
              className="rounded px-1.5 py-0.5 text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring max-md:min-h-10"
            >
              {t.barra.escParaParar}
            </button>
          )}
        </p>
      ) : (
        <div className="home-chips flex flex-wrap justify-center gap-2" role="group" aria-label={t.barra.rotuloDasSugestoes}>
          {t.barra.chips.map((chip) => (
            <button
              key={chip}
              type="button"
              onClick={() => escolherChip(chip)}
              className="rounded-full border border-white/10 bg-background/60 px-3 py-1.5 text-[12.5px] text-[#cfcfcf] backdrop-blur hover:border-primary/60 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring max-md:min-h-10"
            >
              {chip}
            </button>
          ))}
        </div>
      ))}
    </div>
  )
}

/**
 * As frases do hero digitadas letra a letra (26–56 ms), lidas por 2,3 s,
 * apagadas depressa (14 ms) e trocadas pela seguinte, em ciclo. Parar e retomar
 * (a pessoa digitou e apagou) continua de onde estava. Com menos movimento, a
 * frase inteira, parada.
 */
function useSugestaoDigitada(ativa: boolean, sugestoes: readonly string[]): { texto: string; indice: number } {
  const [indice, setIndice] = useState(0)
  const [pos, setPos] = useState(0)
  const [apagando, setApagando] = useState(false)
  const reduz = usePrefereMenosMovimento()

  useEffect(() => {
    if (!ativa || reduz) return
    const alvo = sugestoes[indice] ?? ""
    let atraso: number
    let passo: () => void
    if (!apagando) {
      if (pos >= alvo.length) {
        atraso = 2300
        passo = () => setApagando(true)
      } else {
        atraso = 26 + Math.random() * 30
        passo = () => setPos((p) => p + 1)
      }
    } else if (pos === 0) {
      atraso = 420
      passo = () => {
        setApagando(false)
        setIndice((i) => (i + 1) % sugestoes.length)
      }
    } else {
      atraso = 14
      passo = () => setPos((p) => Math.max(0, p - 1))
    }
    const timer = setTimeout(passo, atraso)
    return () => clearTimeout(timer)
  }, [ativa, reduz, indice, pos, apagando, sugestoes])

  const alvo = sugestoes[indice] ?? ""
  const texto = reduz ? alvo : alvo.slice(0, pos)
  return { texto, indice }
}
