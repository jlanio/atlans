// desktop/src/renderer/components/Logs.tsx
//
// Painel de log com filtro, busca e exportação.
//
// As linhas vêm de duas origens que o store mistura de propósito, porque para
// quem investiga um problema elas contam a mesma história em ordem:
//
//   estruturadas — eventos `{"t":"log"}` do canal NDJSON, com nível e alias
//   brutas       — o stderr do processo (log humano formatado) e qualquer
//                  `print()` de um nó de workflow
//
// O nível só existe nas estruturadas. As brutas ficam marcadas como RAW em vez
// de terem o nível adivinhado por regex sobre a mensagem — que é exatamente o
// que apodreceu o app anterior.
import {
  memo, useDeferredValue, useEffect, useLayoutEffect, useMemo, useRef, useState,
} from 'react'
import {
  TbArrowDown, TbDownload, TbFileText, TbFolderOpen, TbSearch, TbSearchOff, TbX,
} from 'react-icons/tb'
import type { LinhaVisivel } from '../lib/useLog.js'
import { Button } from './ui/button.js'
import { Input } from './ui/input.js'
import { cn } from '../lib/utils.js'

const NIVEIS = ['ERROR', 'WARN', 'INFO', 'DEBUG', 'RAW'] as const
type Nivel = (typeof NIVEIS)[number]

/** Cor do TEXTO da mensagem. Só onde a cor carrega significado. */
const CORES: Record<string, string> = {
  ERROR: 'text-destructive',
  WARN: 'text-yellow-600 dark:text-yellow-500',
  RAW: 'text-muted-foreground',
}

/** Marcador do nível na filtragem — bolinha, para o chip não virar um bloco. */
const PONTOS: Record<Nivel, string> = {
  ERROR: 'bg-destructive',
  WARN: 'bg-yellow-500',
  INFO: 'bg-sky-500',
  DEBUG: 'bg-muted-foreground',
  RAW: 'bg-muted-foreground/50',
}

/** Faixa de fundo da linha. Só ERROR e WARN — o resto seria zebra sem sentido. */
const FUNDOS: Record<string, string> = {
  ERROR: 'bg-destructive/8',
  WARN: 'bg-yellow-500/8',
}

function hora(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString('pt-BR', { hour12: false })
}

/**
 * Destaca o termo buscado dentro da mensagem.
 *
 * Sem isto, buscar num log de mil linhas devolve trinta linhas parecidas e o
 * olho ainda precisa varrer cada uma atrás de onde deu match.
 */
function Realce({ texto, termo }: { texto: string; termo: string }) {
  if (!termo) return <>{texto}</>

  const partes: Array<{ t: string; hit: boolean }> = []
  const alvo = texto.toLowerCase()
  const busca = termo.toLowerCase()
  let i = 0
  // Varredura por índice em vez de regex: o termo é digitado pelo usuário e
  // pode conter `(`, `[`, `\` — construir um regex com ele lançaria.
  for (;;) {
    const achou = alvo.indexOf(busca, i)
    if (achou === -1) break
    if (achou > i) partes.push({ t: texto.slice(i, achou), hit: false })
    partes.push({ t: texto.slice(achou, achou + busca.length), hit: true })
    i = achou + busca.length
  }
  if (i < texto.length) partes.push({ t: texto.slice(i), hit: false })

  return (
    <>
      {partes.map((p, k) => p.hit
        ? <mark key={k} className="rounded-sm bg-primary/30 text-inherit">{p.t}</mark>
        : <span key={k}>{p.t}</span>)}
    </>
  )
}

/**
 * Quantas linhas ficam no DOM de saída.
 *
 * O buffer chega a 1000, e montar as 1000 custa caro em cada render — pior,
 * cada lote novo re-renderizava todas. Com a janela limitada e o `memo` abaixo,
 * um lote de 5 linhas monta 5 nós e deixa o resto intacto.
 *
 * O número é generoso o bastante para rolar bastante antes de precisar do
 * botão "mostrar anteriores".
 */
const JANELA = 400

/**
 * Uma linha do log.
 *
 * `memo` + chave `seq` é o que faz a lista parar de se reconstruir inteira: o
 * objeto da linha nunca é mutado (o main o cria uma vez e o entrega num lote
 * só), então as props de uma linha antiga são idênticas entre renders e o React
 * pula o trabalho.
 *
 * A chave é `seq`, e NÃO o índice: o buffer é aparado pelo início, e com índice
 * toda linha mudaria de chave a cada descarte — invalidando a memoização
 * exatamente quando ela mais importa, com o log cheio.
 */
const LinhaDeLog = memo(function LinhaDeLog({
  linha, termo,
}: {
  linha: LinhaVisivel
  termo: string
}) {
  return (
    <div className={cn('flex gap-3 px-3 py-0.5 hover:bg-muted/40', FUNDOS[linha.level])}>
      <span className="shrink-0 text-muted-foreground/70 tabular-nums">{hora(linha.ts)}</span>
      {/* Largura fixa para as mensagens ficarem numa coluna só: com largura
          automática, cada alias diferente desalinhava tudo. */}
      <span className="w-12 shrink-0 truncate text-muted-foreground" title={linha.alias}>
        {linha.alias}
      </span>
      <span className={cn('min-w-0 whitespace-pre-wrap break-words', CORES[linha.level])}>
        <Realce texto={linha.msg} termo={termo} />
      </span>
    </div>
  )
})

/**
 * Painel de log.
 *
 * Vive SEMPRE em janela própria, aberta pelo botão da barra de rodapé — ler log
 * é quase sempre comparar com outra coisa, e uma aba obriga a escolher entre as
 * duas. Por isso não há mais o modo "embutido" nem o botão de destacar: a tela
 * ocupa a janela inteira, que é a única forma em que ela existe.
 */
export function Logs({ linhas, pastaDeLogs }: {
  linhas: LinhaVisivel[]
  /** Pasta dos arquivos de log — habilita o atalho no rodapé. */
  pastaDeLogs?: string
}) {
  const [busca, setBusca] = useState('')
  const [ocultos, setOcultos] = useState<Set<Nivel>>(new Set())
  const [exportado, setExportado] = useState<string | null>(null)
  const areaRef = useRef<HTMLDivElement>(null)
  // Rolagem automática só enquanto o usuário está no fim. Rolar sempre
  // arrancaria a tela de quem subiu para ler uma linha antiga — e linha nova
  // chega a cada segundo.
  const [seguindo, setSeguindo] = useState(true)
  const [limite, setLimite] = useState(JANELA)
  // Posição guardada antes de crescer a janela — ver `mostrarAnteriores`.
  const ancora = useRef<{ altura: number; topo: number } | null>(null)

  const contagem = useMemo(() => {
    const c: Record<string, number> = {}
    for (const l of linhas) c[l.level] = (c[l.level] ?? 0) + 1
    return c
  }, [linhas])

  /**
   * O termo que o FILTRO usa — atrasado de propósito.
   *
   * `busca` pinta a letra na tela; `termo` só alcança um render depois, e é ele
   * que refiltra o buffer e remonta a lista. Sem essa separação, cada tecla
   * fazia as duas coisas na mesma renderização e a letra só aparecia depois do
   * filtro terminar.
   */
  const termo = useDeferredValue(busca.trim().toLowerCase())

  const visiveis = useMemo(() => (
    // `l.busca` já vem em minúsculas (ver useLog.ts): antes eram duas alocações
    // de string por linha, 2000 por tecla digitada.
    linhas.filter((l) => {
      if (ocultos.has(l.level as Nivel)) return false
      return !termo || l.busca.includes(termo)
    })
  ), [linhas, termo, ocultos])

  // O recorte que vai ao DOM. Memoizado para o efeito de rolagem ter uma
  // dependência estável: solto, o `slice` devolvia um array novo a cada render
  // e o efeito forçava layout mesmo quando a lista não tinha mudado.
  const recorte = useMemo(
    () => (visiveis.length > limite ? visiveis.slice(-limite) : visiveis),
    [visiveis, limite],
  )

  /**
   * Cresce a janela renderizada, sem mover o que a pessoa está lendo.
   *
   * As linhas entram ACIMA da posição atual, o que empurra todo o conteúdo para
   * baixo. Sem compensar, clicar em "mostrar anteriores" faz a tela saltar e a
   * linha que se estava lendo desaparece — o oposto do que o botão promete.
   */
  function mostrarAnteriores() {
    const el = areaRef.current
    if (el) ancora.current = { altura: el.scrollHeight, topo: el.scrollTop }
    setLimite((n) => n + JANELA)
  }

  // `useLayoutEffect` e não `useEffect`: rolar depois da pintura produz um
  // salto visível a cada linha nova.
  //
  // COM lista de dependências: sem ela o efeito rodava depois de TODA
  // renderização — inclusive as que só mudaram o texto do campo de busca — e
  // cada passada lia `scrollHeight`, que força o layout na hora.
  useLayoutEffect(() => {
    const el = areaRef.current
    if (!el) return

    if (ancora.current) {
      // Restaura pela DIFERENÇA de altura: é exatamente o quanto o conteúdo
      // desceu ao ganhar linhas no topo.
      el.scrollTop = ancora.current.topo + (el.scrollHeight - ancora.current.altura)
      ancora.current = null
      return
    }
    if (seguindo) el.scrollTop = el.scrollHeight
  }, [recorte, seguindo])

  // Um filtro novo muda o conteúdo inteiro; voltar ao fim é o que o usuário
  // espera de "aplicar filtro". A janela volta ao tamanho padrão junto: o
  // recorte anterior era sobre outro conjunto de linhas.
  //
  // Depende de `termo`, e não de `busca`: é a filtragem que muda o conteúdo, e
  // ela chega um render depois da tecla.
  useEffect(() => { setSeguindo(true); setLimite(JANELA) }, [termo, ocultos])

  function aoRolar() {
    const el = areaRef.current
    if (!el) return
    // 24px de tolerância: exigir o fim exato faz a rolagem por roda, que anda
    // em passos, desligar o acompanhamento sem o usuário ter pedido.
    setSeguindo(el.scrollHeight - el.scrollTop - el.clientHeight < 24)
  }

  function alternar(n: Nivel) {
    const novo = new Set(ocultos)
    if (novo.has(n)) novo.delete(n)
    else novo.add(n)
    setOcultos(novo)
  }

  async function exportar() {
    // Exporta o que está VISÍVEL, não tudo: quem filtrou para isolar um
    // problema quer mandar aquilo, não 1000 linhas de ruído em volta.
    const texto = visiveis
      .map((l) => `${hora(l.ts)} ${l.level.padEnd(5)} ${l.alias.padEnd(6)} ${l.msg}`)
      .join('\n')
    const caminho = await window.atlas.exportarLog(texto)
    if (caminho) setExportado(caminho)
  }

  const filtrando = Boolean(termo) || ocultos.size > 0

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      {/* ── Barra de ferramentas ────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative flex h-9 min-w-56 flex-1 items-center">
          <TbSearch size={15} className="pointer-events-none absolute left-3 text-muted-foreground" />
          <Input
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Buscar no log…"
            spellCheck={false}
            aria-label="Buscar no log"
            className="h-full pr-8 pl-9 select-text"
          />
          {busca && (
            <button type="button" onClick={() => setBusca('')} aria-label="Limpar busca"
                    className="absolute right-2 rounded-sm p-1 text-muted-foreground outline-none transition-colors hover:text-foreground focus-visible:ring-ring/50 focus-visible:ring-2 animate-in fade-in-0 zoom-in-75 duration-150">
              <TbX size={14} />
            </button>
          )}
        </div>

        <Button variant="outline" size="sm" disabled={visiveis.length === 0} onClick={exportar}
                title="Salva TODAS as linhas que passam pelo filtro atual — não só as visíveis na janela">
          <TbDownload size={15} /> Exportar
        </Button>
      </div>

      {/* Chips de nível numa linha própria: junto da busca eles quebravam para
          a linha de baixo em janela estreita e o alinhamento desmontava. */}
      <div className="flex flex-wrap items-center gap-1.5">
        {NIVEIS.map((n) => {
          const escondido = ocultos.has(n)
          const total = contagem[n] ?? 0
          return (
            <button
              key={n}
              type="button"
              aria-pressed={!escondido}
              onClick={() => alternar(n)}
              title={escondido ? `Mostrar ${n}` : `Ocultar ${n}`}
              className={cn(
                'flex items-center gap-1.5 rounded-full border py-1 pr-2.5 pl-2 text-[11px] font-medium outline-none',
                'transition-colors focus-visible:ring-ring/50 focus-visible:ring-2',
                escondido
                  ? 'border-input text-muted-foreground/60 hover:text-muted-foreground'
                  : 'border-transparent bg-muted text-foreground',
              )}
            >
              <span className={cn(
                'size-1.5 shrink-0 rounded-full transition-opacity',
                PONTOS[n], escondido && 'opacity-30',
              )} />
              <span className="font-mono">{n}</span>
              <span className={cn('tabular-nums', escondido ? 'opacity-60' : 'text-muted-foreground')}>
                {total}
              </span>
            </button>
          )
        })}

        {filtrando && (
          <button
            type="button"
            onClick={() => { setBusca(''); setOcultos(new Set()) }}
            className="ml-1 text-[11px] text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
          >
            limpar filtros
          </button>
        )}
      </div>

      {exportado && (
        <p className="text-xs text-muted-foreground">
          Salvo em <span className="font-mono select-text">{exportado}</span>
        </p>
      )}

      {/* ── Área de log ─────────────────────────────────────────────── */}
      <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border bg-card">
        {visiveis.length === 0 ? (
          <div className="flex flex-col items-center gap-2 px-6 py-12 text-center">
            {linhas.length === 0
              ? <TbFileText size={26} className="text-muted-foreground/50" />
              : <TbSearchOff size={26} className="text-muted-foreground/50" />}
            <p className="text-sm text-muted-foreground">
              {linhas.length === 0
                ? 'Sem registros ainda. As linhas aparecem aqui assim que o executor iniciar.'
                : `Nenhuma das ${linhas.length} linhas em memória corresponde ao filtro.`}
            </p>
          </div>
        ) : (
          <div
            ref={areaRef}
            onScroll={aoRolar}
            // `log` traz a tipografia do painel — ver a regra em index.css.
            className="log flex min-h-0 flex-1 flex-col overflow-y-auto py-1.5 font-mono select-text"
          >
            {visiveis.length > limite && (
              <button
                type="button"
                onClick={mostrarAnteriores}
                className="mx-3 mb-1 rounded-md border border-dashed py-1 text-[11px] text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground"
              >
                mostrar {Math.min(JANELA, visiveis.length - limite)} linha(s) anterior(es)
                {' · '}{visiveis.length - limite} acima
              </button>
            )}
            {recorte.map((l) => (
              <LinhaDeLog key={l.seq} linha={l} termo={termo} />
            ))}
          </div>
        )}

        {/* Flutua SOBRE a área, e não abaixo dela: o botão só existe quando o
            usuário rolou para cima, e é ali que o olho dele está. */}
        {!seguindo && visiveis.length > 0 && (
          <button
            type="button"
            onClick={() => setSeguindo(true)}
            className="absolute right-4 bottom-3 flex items-center gap-1.5 rounded-full border bg-popover px-3 py-1.5 text-xs font-medium shadow-md transition-colors hover:bg-accent"
          >
            <TbArrowDown size={13} /> Acompanhar o fim
          </button>
        )}
      </div>

      {/* Rodapé discreto: quantas linhas há aqui, e onde está o resto.
          A menção anterior mandava procurar "em Ajustes" — que agora é OUTRA
          janela. Mandar alguém trocar de janela para achar um caminho, quando
          o botão cabe aqui, é instrução no lugar de ação. */}
      <p className="flex flex-wrap items-center gap-x-1.5 text-xs text-muted-foreground">
        <span>
          {visiveis.length === linhas.length
            ? `${linhas.length} linha(s) em memória`
            : `${visiveis.length} de ${linhas.length} linha(s) em memória`}
          {' · '}o registro completo fica em arquivo
        </span>
        {pastaDeLogs && (
          <button type="button" onClick={() => window.atlas.abrirCaminho(pastaDeLogs)}
                  title={`Abrir no Explorer: ${pastaDeLogs}`}
                  className="inline-flex items-center gap-1 underline-offset-4 hover:text-foreground hover:underline">
            <TbFolderOpen size={13} /> abrir pasta
          </button>
        )}
      </p>
    </div>
  )
}
