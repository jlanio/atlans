"use client"

import { useEffect, useRef, useState } from "react"
import { TbSearch, TbSparkles, TbX } from "react-icons/tb"
import { Button } from "@/app/components/ui/button"
import { Input } from "@/app/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/app/components/ui/select"
import { cn } from "@/lib/utils"
import { formatarInteiro } from "@/lib/formatos"
import { FILTROS_DOS_CHIPS, ROTULO_DA_ORDEM, ROTULO_DO_FILTRO } from "./filtros"
import { ESTADO_PADRAO, ORDENS, filtrosAtivos, type EstadoDeProjetos, type Filtro, type Ordem } from "./projetos-url"

export interface BarraDeFiltrosProps {
  estado: EstadoDeProjetos
  /** Recebe só o que mudou; quem compõe a página funde com o resto e grava na URL. */
  onEstado: (mudanca: Partial<EstadoDeProjetos>) => void
  onLimpar: () => void
  /** Contagem de cada chip sobre a lista inteira (`contarPorFiltro`). */
  contagens: Record<Filtro, number>
  /** "Recolher todos"/"Expandir todos" só existe com grupos. */
  temGrupos: boolean
  todosRecolhidos: boolean
  onRecolherTodos: () => void
  onExpandirTodos: () => void
}

// A busca é local (a lista já está na memória), mas cada tecla gravada na
// URL é um `router.replace`; um respiro curto junta as teclas de uma palavra
// sem que a pessoa perceba a espera.
const ATRASO_DA_BUSCA_MS = 200

/**
 * Onde a barra troca de assunto: depois de "Inativos" (de estado para natureza
 * e situação) e depois de "Com portal" (o recorte por QUEM criou o fluxo, que
 * não é uma propriedade do fluxo como as outras).
 */
const SEPARADOR_DEPOIS_DE: Filtro[] = ["inativos", "portal"]

/**
 * Barra de busca, ordenação, recolher e chips (docs/specs/projects.md §3.6).
 * O arquivo não se chama `filtros.tsx` de propósito: ao lado de `filtros.ts`,
 * o mesmo `import "./filtros"` cairia no `.ts` para o tsc e o Vite e no
 * `.tsx` para o webpack do Next — e a página quebraria só no build.
 *
 * Nada aqui guarda estado de filtro: tudo sobe por `onEstado` e volta pela
 * URL. A única exceção é o texto da busca, que espera um instante parado.
 */
export function BarraDeFiltros({
  estado, onEstado, onLimpar, contagens, temGrupos, todosRecolhidos, onRecolherTodos, onExpandirTodos,
}: BarraDeFiltrosProps) {
  const ativos = filtrosAtivos(estado)
  // `pausado` e `nunca` chegam pela faixa de atenção e não têm chip fixo: um
  // chip provisório, já marcado, mostra o recorte em vigor — senão a faixa
  // some (quando o número zera) e a lista fica filtrada sem nada dizer por quê.
  const filtroSemChip = FILTROS_DOS_CHIPS.includes(estado.filtro) ? null : estado.filtro

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <Busca valor={estado.q} onValor={q => onEstado({ q })} />
        <Select value={estado.ordem} onValueChange={v => onEstado({ ordem: v as Ordem })}>
          <SelectTrigger size="sm" aria-label="Ordenar" className="max-md:h-10">
            <span className="text-muted-foreground">Ordenar:</span>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {ORDENS.map(o => (
              <SelectItem key={o} value={o}>{ROTULO_DA_ORDEM[o]}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        {temGrupos && (
          <Button
            variant="ghost"
            size="sm"
            onClick={todosRecolhidos ? onExpandirTodos : onRecolherTodos}
            className="max-md:h-10"
          >
            {todosRecolhidos ? "Expandir todos" : "Recolher todos"}
          </Button>
        )}
      </div>

      <div className="flex items-center gap-2">
        {/* No telefone os chips rolam na horizontal em vez de quebrar em três
            linhas; no desktop quebram, porque há largura. */}
        <div
          role="group"
          aria-label="Filtros"
          className="flex min-w-0 items-center gap-1.5 max-md:overflow-x-auto max-md:pb-1 md:flex-wrap"
        >
          {FILTROS_DOS_CHIPS.map(f => (
            <span key={f} className="contents">
              <Chip
                filtro={f}
                ativo={estado.filtro === f}
                n={contagens[f]}
                onClick={() => onEstado({ filtro: estado.filtro === f && f !== ESTADO_PADRAO.filtro ? ESTADO_PADRAO.filtro : f })}
              />
              {SEPARADOR_DEPOIS_DE.includes(f) && <span aria-hidden="true" className="mx-0.5 h-4 w-px shrink-0 bg-border" />}
            </span>
          ))}
          {filtroSemChip && (
            <Chip filtro={filtroSemChip} ativo n={contagens[filtroSemChip]} onClick={() => onEstado({ filtro: ESTADO_PADRAO.filtro })} />
          )}
        </div>
        {ativos > 0 && (
          <button
            type="button"
            onClick={onLimpar}
            className="inline-flex h-8 shrink-0 items-center gap-1 rounded-md px-1.5 text-xs font-medium text-primary outline-none hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50 max-md:h-10"
          >
            <TbX size={12} aria-hidden="true" /> Limpar filtros
          </button>
        )}
      </div>
    </div>
  )
}

function Chip({ filtro, ativo, n, onClick }: { filtro: Filtro; ativo: boolean; n: number | undefined; onClick: () => void }) {
  return (
    <button
      type="button"
      aria-pressed={ativo}
      onClick={onClick}
      className={cn(
        "inline-flex h-8 shrink-0 items-center gap-1.5 rounded-full border px-3 text-xs font-medium whitespace-nowrap transition-colors outline-none max-md:h-10",
        "focus-visible:ring-[3px] focus-visible:ring-ring/50",
        ativo
          ? "border-primary bg-primary/10 text-foreground"
          : "border-border bg-card text-muted-foreground hover:border-foreground/30 hover:text-foreground",
      )}
    >
      {/* A faísca do chip é a mesma do selo da linha: quem vê uma reconhece a
          outra sem ler o rótulo. */}
      {filtro === "assistente" && <TbSparkles size={13} aria-hidden="true" className="text-primary" />}
      {ROTULO_DO_FILTRO[filtro]}
      {n != null && <b className="font-semibold text-foreground tabular-nums">{formatarInteiro(n)}</b>}
    </button>
  )
}

function Busca({ valor, onValor }: { valor: string; onValor: (q: string) => void }) {
  const [texto, setTexto] = useState(valor)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  // O que este campo já emitiu: quando a URL muda por fora (Limpar filtros,
  // link novo), o campo acompanha; quando a URL só ecoa o que ele mandou, não
  // há nada a fazer — e sobrescrever aqui apagaria o que a pessoa digitou
  // entre o respiro e a resposta do router.
  const emitido = useRef(valor)

  useEffect(() => {
    // A URL guarda o texto sem espaços nas pontas: "bacia " volta como
    // "bacia". Comparar o emitido também sem eles é o que impede o eco da
    // URL de apagar o espaço que a pessoa acabou de digitar.
    if (valor !== emitido.current.trim()) {
      emitido.current = valor
      setTexto(valor)
    }
  }, [valor])

  useEffect(() => () => { if (timer.current) clearTimeout(timer.current) }, [])

  function aoDigitar(q: string) {
    setTexto(q)
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => {
      emitido.current = q
      onValor(q)
    }, ATRASO_DA_BUSCA_MS)
  }

  return (
    <div className="relative max-md:w-full md:w-72">
      <TbSearch size={14} aria-hidden="true" className="pointer-events-none absolute top-1/2 left-2.5 -translate-y-1/2 text-muted-foreground" />
      <Input
        type="search"
        role="searchbox"
        aria-label="Buscar workflow ou grupo"
        placeholder="Buscar workflow ou grupo…"
        value={texto}
        onChange={e => aoDigitar(e.target.value)}
        // 16px no telefone: abaixo disso o iOS dá zoom ao focar o campo.
        className="h-8 pl-8 text-base max-md:h-10 md:text-xs"
      />
    </div>
  )
}
