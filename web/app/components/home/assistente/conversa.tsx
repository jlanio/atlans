"use client"

// web/app/components/home/assistente/conversa.tsx
//
// A conversa desenhada: turnos de quem pergunta, turnos do assistente.
//
// O turno do assistente é uma LINHA DO TEMPO (`assistente-quadros.ts`), e não
// blocos de texto separados dos passos. É a escolha que dá espaço ao modelo
// para EXPLICAR o que fez entre uma ferramenta e a próxima — que é o que
// impede alguém de aplicar um fluxo sem entender, e a razão pela qual a gaveta
// lateral venceu a barra de comando.
//
// A MESMA Conversa serve de LEGENDA na Home (`compacta`, a faixa acima da
// barra): a pergunta numa linha, e de cada resposta só o que ficou — o último
// texto, cortado em 4 linhas, os erros e os cartões — mais o que está vivo (o
// passo em curso). O processo (raciocínio, passos concluídos, textos
// anteriores) não entra: uma legenda que mostrasse tudo encheria a faixa até o
// teto e voltaria a rolar; ele fica a um "Expandir", no painel.

import { useCallback, useEffect, useRef } from "react"
import { TbAlertTriangle, TbChevronRight, TbSparkles } from "react-icons/tb"

import { cn } from "@/lib/utils"
import ExecActivity from "@/app/components/shared/exec-activity"
import type { BlocoDoAssistente, TurnoDoAssistente, PropostaDeFluxo } from "@/app/components/home/assistente/quadros"
import Passo from "./passo"
import type { ErroDoAssistente } from "@/app/components/home/assistente/quadros"
import type { Idioma } from "@/lib/idioma"
import { textosDe, useIdiomaDaTela, useTextos } from "../i18n"

/**
 * O texto de um erro na tela. Em português é a mensagem do servidor COMO VEIO
 * (a de sempre). Em inglês e espanhol, um código conhecido vira a frase do
 * dicionário — a mensagem do servidor é em português; um código novo ainda
 * aparece como veio, que é melhor que nada.
 */
export function textoDoErro(erro: ErroDoAssistente, idioma: Idioma): { message: string; hint?: string } {
  if (idioma === "pt-BR") return { message: erro.message, hint: erro.hint }
  const erros = textosDe(idioma).assistente.erros
  if (!Object.hasOwn(erros, erro.code)) return { message: erro.message, hint: erro.hint }
  const conhecido = erros[erro.code]
  return { message: conhecido.message(erro.teto ?? null), hint: conhecido.hint || undefined }
}

/** O que a `Conversa` sabe de um bloco além dele mesmo, para quem renderiza os `extras`. */
export interface ContextoDoBloco {
  /** O bloco está no ÚLTIMO turno da lista — o único onde uma oferta ainda vale. */
  ultimoTurno: boolean
}

/** O indicador de atividade do item pendente: um SVG que aceita `size` (o `ExecActivity`; a marca da Home). */
export type IndicadorDeAtividade = React.ComponentType<{ size?: number; className?: string }>

interface Props {
  turnos: TurnoDoAssistente[]
  correndo: boolean
  // Opcional: só a gaveta do editor sabe desenhar uma proposta no canvas —
  // ela injeta o cartão por aqui. A Home não passa (a superfície HOME não
  // emite `proposta`) e usa `extras` para os blocos que só ela tem.
  proposta?: (proposta: PropostaDeFluxo) => React.ReactNode
  /**
   * Renderiza os blocos que esta Conversa não conhece (`fluxo`/`camada`/
   * `confirmacao`/`respostas_rapidas` do assistente da Home). Sem ele, um bloco
   * desconhecido some. O editor não passa — e nunca emite esses tipos. O
   * `contexto` diz se o bloco está no ÚLTIMO turno: é o que deixa as respostas
   * rápidas valerem só para aquela vez.
   */
  extras?: (bloco: BlocoDoAssistente, contexto: ContextoDoBloco) => React.ReactNode
  /**
   * Como a superfície se chama no anúncio para leitor de tela. O editor é o
   * "assistente"; na Home a mesma conversa é o "assistente", e anunciar o nome
   * errado é anunciar uma tela que não existe ali.
   */
  nome?: string
  /**
   * O convite da conversa vazia. O padrão fala do editor (descrever um fluxo,
   * aplicar no canvas); a Home, que não tem canvas, passa o dela.
   */
  vazio?: React.ReactNode
  /**
   * A vista de LEGENDA da Home (a faixa colada à barra): a pergunta numa linha
   * ("Você · …", truncada, o texto inteiro no `title`), e de cada resposta só o
   * que ficou — o último texto, cortado em 4 linhas, os erros e os cartões dos
   * `extras` — mais o que está vivo enquanto o turno corre (o "Trabalhando…" ou o
   * passo em curso). Raciocínio, passos concluídos e textos anteriores ficam
   * para o painel. O editor e o painel não passam: a conversa inteira, como
   * sempre.
   */
  compacta?: boolean
  /**
   * O indicador de atividade do item pendente (o "Trabalhando…" do turno sem bloco
   * e o raciocínio vivo). O padrão é o `ExecActivity` do editor — um vocabulário
   * de "ocupado" só, o mesmo do nó em execução. A Home passa a marca animada
   * (`assistente/marca-animada.tsx`): ali quem pensa é o site.
   */
  indicador?: IndicadorDeAtividade
  /**
   * Um cursor piscando no fim do parágrafo que está sendo escrito (o último
   * grupo do turno em curso), como o da sugestão digitada da Home. Opt-in da
   * Home (`.home-caret` mora no CSS dela); o editor não passa e fica igual.
   */
  cursorAoEscrever?: boolean
}

export default function Conversa({
  turnos, correndo, proposta, extras,
  nome = "assistente", vazio, compacta = false,
  indicador: Indicador = ExecActivity, cursorAoEscrever = false,
}: Props) {
  const t = useTextos().assistente.conversa
  const fimRef = useRef<HTMLDivElement>(null)
  const grudadoRef = useRef(true)

  // Rola só quando já se estava no fim. Quem subiu para reler uma explicação
  // não deve ser arrastado de volta a cada delta de texto.
  useEffect(() => {
    if (grudadoRef.current) fimRef.current?.scrollIntoView({ block: "end" })
  }, [turnos])

  function aoRolar(e: React.UIEvent<HTMLDivElement>) {
    const el = e.currentTarget
    grudadoRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 48
  }

  // Abrir um `<details>` aumenta o `scrollHeight` SEM disparar evento `scroll`
  // — crescimento de conteudo nao dispara. Entao o `grudadoRef` fica preso no
  // ultimo valor lido, quase sempre `true`, e o proximo delta arrasta de volta
  // para o fim: o clique de quem so queria ler o raciocinio e desfeito sozinho.
  // Quem abre um bloco ANTIGO desgruda; quem abre o que esta sendo escrito
  // continua acompanhando, que e o que se quer nos dois casos.
  const desgrudar = useCallback(() => { grudadoRef.current = false }, [])

  const idDoUltimo = turnos[turnos.length - 1]?.id

  return (
    // `min-h-0` NAO e detalhe: sem ele o layout quebra conforme a conversa
    // cresce. Filho de flex nasce com `min-height: auto`, entao `flex-1` +
    // `overflow-y-auto` nao encolhe abaixo do conteudo — a lista empurra o
    // formulario de enviar para fora da gaveta em vez de rolar. O sintoma
    // aparece so depois de alguns turnos, que e o que o torna dificil de achar.
    // `min-w-0` pelo mesmo motivo no outro eixo, com a gaveta em 300px.
    //
    // E este container existe SEMPRE, inclusive com a conversa vazia. Antes o
    // estado vazio era um retorno antecipado, irmao do formulario e sem rolagem
    // nenhuma: com a gaveta ganhando teto de altura, ~300px de convite mais o
    // cabecalho e o formulario nao cabem num viewport curto (telefone deitado,
    // janela baixa) e o campo de enviar sairia da tela sem nada para rolar —
    // justamente em `/workflow/create`, onde a gaveta nasce aberta.
    <div
      // A legenda não tem padding próprio: a faixa (`.home-pilha`) já o dá.
      className={cn("nowheel min-h-0 min-w-0 flex-1 overflow-y-auto", !compacta && "px-3 py-3")}
      onScroll={aoRolar}
      aria-busy={correndo}
    >
      {/* O anúncio para leitor de tela é GROSSO, e a lista NÃO é `aria-live`.
          O texto do modelo chega em dezenas de deltas que se acumulam no mesmo
          parágrafo; uma região viva ali reanunciaria a resposta inteira a cada
          pedaço, e a pessoa não ouviria o fim de frase nenhuma. */}
      <p className="sr-only" role="status">
        {correndo ? t.respondendo(nome) : ""}
      </p>

      {turnos.length === 0 ? (vazio ?? <Vazio />) : (
        <>
          <ol className={cn("flex min-w-0 flex-col", compacta ? "gap-1.5" : "gap-4")}>
            {turnos.map(turno => (
              <li key={turno.id}>
                {turno.papel === "user" ? <Pergunta texto={turno.texto ?? ""} compacta={compacta} /> : (
                  <Resposta
                    turno={turno}
                    proposta={proposta}
                    extras={extras}
                    compacta={compacta}
                    // O turno do modelo que esta correndo e, por construcao, o
                    // ULTIMO da lista. Nao ha estado novo aqui.
                    pensando={correndo && turno.id === idDoUltimo}
                    ultimoTurno={turno.id === idDoUltimo}
                    Indicador={Indicador}
                    cursorAoEscrever={cursorAoEscrever}
                    onDesgrudar={desgrudar}
                  />
                )}
              </li>
            ))}
          </ol>
          <div ref={fimRef} />
        </>
      )}
    </div>
  )
}

function Pergunta({ texto, compacta }: { texto: string; compacta: boolean }) {
  const t = useTextos().assistente.conversa
  if (compacta) {
    // Uma linha: "Você · pergunta", truncada, com o texto inteiro no `title`.
    // A pergunta fica num `<span>` próprio, e não solta ao lado de "Você": é
    // ela que o leitor de tela lê e que quem procura a frase encontra.
    return (
      <p className="truncate text-xs text-muted-foreground" title={texto}>
        <span className="text-primary">{t.voce}</span> · <span>{texto}</span>
      </p>
    )
  }
  return (
    <p className="ml-auto w-fit max-w-[85%] whitespace-pre-wrap break-words rounded-lg rounded-br-sm bg-primary/10 px-3 py-2 text-sm text-foreground">
      {texto}
    </p>
  )
}

function Resposta({
  turno,
  proposta,
  extras,
  pensando,
  compacta,
  ultimoTurno,
  Indicador,
  cursorAoEscrever,
  onDesgrudar,
}: {
  turno: TurnoDoAssistente
  proposta?: (proposta: PropostaDeFluxo) => React.ReactNode
  extras?: (bloco: BlocoDoAssistente, contexto: ContextoDoBloco) => React.ReactNode
  /** Este turno e o que esta sendo escrito agora. */
  pensando: boolean
  compacta: boolean
  /** Este turno e o ultimo da lista (os `extras` sabem: uma oferta so vale nele). */
  ultimoTurno: boolean
  Indicador: IndicadorDeAtividade
  cursorAoEscrever: boolean
  onDesgrudar: () => void
}) {
  if (!turno.blocos.length) return <Pensando Indicador={Indicador} />

  // Os passos consecutivos viram uma lista só: cinco `<ul>` de um item cada
  // desenhavam cinco blocos soltos onde há uma sequência.
  const grupos: BlocoDoAssistente[][] = []
  for (const bloco of turno.blocos) {
    const ultimo = grupos[grupos.length - 1]
    if (bloco.tipo === "ferramenta" && ultimo?.[0]?.tipo === "ferramenta") ultimo.push(bloco)
    else grupos.push([bloco])
  }

  // Na legenda (`compacta`) entra só o que FICOU — o último texto, os erros e
  // os cartões — e o que está VIVO: o último grupo enquanto o turno corre (o
  // "Trabalhando…" ou o passo em curso). Raciocínio e passos concluídos, e os
  // textos anteriores ao último, ficam para o painel. O índice guardado é o
  // ORIGINAL (a `key` e o `pensandoAgora` dependem dele): o filtro não pode
  // deslocar dono.
  const ultimoTexto = grupos.map((g) => g[0].tipo).lastIndexOf("texto")
  const vivo = grupos.length - 1
  const visiveis = grupos
    .map((grupo, i) => ({ grupo, i }))
    .filter(({ grupo, i }) => {
      if (!compacta) return true
      const tipo = grupo[0].tipo
      if (tipo === "texto") return i === ultimoTexto
      if (tipo === "pensando" || tipo === "ferramenta") return pensando && i === vivo
      return true // `erro` e os cartões da Home; `proposta` não chega à Home
    })

  return (
    <div className="flex min-w-0 flex-col gap-2">
      {visiveis.map(({ grupo, i }) => (
        <Grupo
          key={i}
          grupo={grupo}
          proposta={proposta}
          extras={extras}
          // O `key={i}` e seguro porque os indices sao APPEND-ONLY: `acumular`
          // substitui o ultimo bloco ou anexa, `mapearFerramenta` substitui no
          // lugar, e todo o resto anexa. Nenhum grupo desloca no meio, entao um
          // <details> aberto nao salta de dono durante o stream. Se algum
          // quadro novo passar a inserir bloco no MEIO, isto deixa de valer.
          pensandoAgora={pensando && i === vivo}
          compacta={compacta}
          ultimoTurno={ultimoTurno}
          Indicador={Indicador}
          cursorAoEscrever={cursorAoEscrever}
          onDesgrudar={onDesgrudar}
        />
      ))}
    </div>
  )
}

function Grupo({
  grupo,
  proposta,
  extras,
  pensandoAgora,
  compacta,
  ultimoTurno,
  Indicador,
  cursorAoEscrever,
  onDesgrudar,
}: {
  grupo: BlocoDoAssistente[]
  proposta?: (proposta: PropostaDeFluxo) => React.ReactNode
  extras?: (bloco: BlocoDoAssistente, contexto: ContextoDoBloco) => React.ReactNode
  /** Este e o ultimo grupo de um turno em andamento — ou seja, o vivo. */
  pensandoAgora: boolean
  compacta: boolean
  ultimoTurno: boolean
  Indicador: IndicadorDeAtividade
  cursorAoEscrever: boolean
  onDesgrudar: () => void
}) {
  const primeiro = grupo[0]
  const idioma = useIdiomaDaTela()
  const t = textosDe(idioma).assistente.conversa

  if (primeiro.tipo === "ferramenta") {
    // Na legenda, só o passo em curso: os anteriores do grupo já terminaram.
    const passos = compacta ? grupo.slice(-1) : grupo
    return (
      <ul className="rounded-md border border-dashed bg-muted/30 px-2.5 py-1">
        {passos.map((b, i) => (
          b.tipo === "ferramenta" ? <Passo key={`${b.id}-${i}`} bloco={b} /> : null
        ))}
      </ul>
    )
  }

  if (primeiro.tipo === "pensando") {
    // RECOLHIDO por padrao, e nao mais sempre aberto.
    //
    // O texto vem em INGLES e nao ha como pedir outro idioma: com
    // `display: "summarized"` o pensamento cru nunca volta, e o resumo e
    // gerado por um passo separado que nao obedece o "Responda sempre em
    // {ASSISTENTE_IDIOMA}" do system prompt (`app/services/assistente/editor_service.py`).
    // Traduzir custaria outra chamada ao modelo por bloco e mataria justamente
    // o streaming. Entao: enquanto o modelo pensa fica so a animacao, e o texto
    // continua a um clique — no DOM, achavel por Ctrl+F e por leitor de tela.
    //
    // `<details>` nativo e nao `useState`: o estado aberto mora no DOM, entao
    // os turnos serem reconstruidos a cada delta nao o fecha; e `<summary>` ja
    // e focavel e ja anuncia recolhido/expandido sem `aria-expanded`. Molde
    // copiado de `components/executores/dialogs.tsx`.
    return (
      <details
        className="group rounded-md border-l-2 border-primary/40 bg-muted/20 py-1.5 pl-2.5 pr-2"
        onToggle={pensandoAgora ? undefined : onDesgrudar}
      >
        <summary className="flex cursor-pointer list-none items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground/80 transition-colors hover:text-muted-foreground [&::-webkit-details-marker]:hidden">
          {pensandoAgora ? (
            <>
              <Indicador size={12} />
              {/* O rótulo ganha o brilho que varre (o sistema do "Trabalhando…"
                  da barra) e as reticências são DIGITADAS pelo ::after do
                  .tic-pensando — vida no indicador sem expor o raciocínio, que
                  continua recolhido (e em inglês) de propósito. O "…" real fica
                  no sr-only: o leitor de tela e os testes leem "Trabalhando…",
                  enquanto o olho vê os pontos aparecerem um a um. */}
              <span className="texto-pensando">
                {t.trabalhando}
                <span className="tic-pensando" aria-hidden="true" />
                <span className="sr-only">…</span>
              </span>
            </>
          ) : t.raciocinio}
          <TbChevronRight
            size={12}
            className="ml-auto shrink-0 transition-transform group-open:rotate-90"
            aria-hidden="true"
          />
        </summary>
        {/* `lang="en"`: o conteudo E ingles, comprovadamente, e sem isto o
            leitor de tela o soletra com fonetica portuguesa. */}
        <p lang="en" className="mt-1 whitespace-pre-wrap break-words text-xs leading-relaxed text-muted-foreground">
          {primeiro.texto}
        </p>
      </details>
    )
  }

  if (primeiro.tipo === "texto") {
    return (
      // Na legenda a resposta corta em 4 linhas; o texto inteiro fica no painel.
      // O cursor só no parágrafo VIVO: some quando uma ferramenta o segue ou o
      // turno acaba.
      <p className={cn("whitespace-pre-wrap break-words text-sm leading-relaxed text-foreground", compacta && "line-clamp-4")}>
        {primeiro.texto}
        {cursorAoEscrever && pensandoAgora && <span className="home-caret" aria-hidden="true" />}
      </p>
    )
  }

  if (primeiro.tipo === "proposta") {
    // Só a gaveta injeta o cartão; sem o slot (a Home) o bloco não se desenha.
    return proposta ? <>{proposta(primeiro.proposta)}</> : null
  }

  if (primeiro.tipo === "erro") {
    const erro = textoDoErro(primeiro.erro, idioma)
    return (
      <p
        role="alert"
        className="flex items-start gap-2 rounded-md border border-destructive/20 bg-destructive/10 px-2.5 py-2 text-xs text-destructive"
      >
        <TbAlertTriangle size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
        <span className="min-w-0">
          {erro.message}
          {erro.hint && (
            <span className="block text-destructive/80">{erro.hint}</span>
          )}
        </span>
      </p>
    )
  }

  // Blocos que esta Conversa não conhece (fluxo/camada/confirmação/respostas
  // rápidas da Home). O editor não passa `extras` e nunca emite esses tipos →
  // some, como antes. O contexto diz se o bloco está no último turno.
  return <>{extras?.(primeiro, { ultimoTurno })}</>
}

/**
 * O turno que ainda nao produziu bloco nenhum.
 *
 * No editor o indicador e o `ExecActivity` — as quatro barras oscilando fora de
 * fase que o nó em execucao ja usa. Nao e so economia de codigo: o docstring
 * dele registra POR QUE aquela forma foi escolhida (rotacao e o glifo de
 * "aguarde"; a oscilacao diz que ha trabalho ACONTECENDO), e e exatamente isso
 * que a gaveta precisa dizer enquanto o modelo monta; uma segunda animacao de
 * "ocupado" no editor seria um segundo vocabulario para a mesma ideia. A Home
 * passa outro pelo `indicador` da Conversa: a marca animada do site — ali quem
 * pensa e o site, e a marca e o que diz isso.
 *
 * O que havia aqui antes eram tres pontos com `animate-pulse` e atraso de
 * 150ms. O ciclo do `animate-pulse` e de 2s, entao 150ms sao 7,5% de fase: os
 * tres piscavam praticamente JUNTOS, e o que se lia era um bloco piscando, nao
 * uma onda. O `exec-activity` cicla em 1s com passos de 0,14s — 14% de fase, a
 * onda que se queria. E ele ja degrada sob `prefers-reduced-motion`, congelando
 * as barras em alturas diferentes em vez de sumir.
 *
 * Cabe dentro de um `<summary>` porque `<svg>` e *phrasing content*; o `<p>`
 * daqui nao caberia, e o `role="status"` dele tampouco — um por bloco de
 * raciocinio seria a regiao viva que o comentario do `<ol>` acima recusa.
 */
function Pensando({ Indicador }: { Indicador: IndicadorDeAtividade }) {
  const t = useTextos().assistente.barra
  return (
    <p className="flex items-center gap-1.5 text-xs text-muted-foreground" role="status">
      <Indicador size={13} />
      <span className="texto-pensando">{t.trabalhando}</span>
    </p>
  )
}

function Vazio() {
  return (
    // `min-h-full` e nao `flex-1`: o pai agora e o container de rolagem, e nao
    // mais a coluna da gaveta. Resolve contra a content box dele — a altura
    // menos o `py-3` —, entao centraliza quando ha espaco e ROLA quando nao ha.
    <div className="flex min-h-full flex-col items-center justify-center gap-3 px-6 py-10 text-center">
      <span className="rounded-full bg-muted/60 p-4" aria-hidden="true">
        <TbSparkles size={22} className="text-muted-foreground/50" />
      </span>
      <p className="text-sm font-semibold text-foreground">Descreva o fluxo que você quer</p>
      <p className="text-xs leading-relaxed text-muted-foreground">
        Diga de onde vêm os dados, o que fazer com eles e onde entregar. O assistente monta,
        valida e mostra — aplicar no canvas é você quem decide.
      </p>
      <p className="rounded-md bg-muted/50 px-2.5 py-2 text-left text-xs italic text-muted-foreground">
        «lê municipios.shp do Drive, faz buffer de 500 m, dissolve por UF e publica no portal»
      </p>
    </div>
  )
}
