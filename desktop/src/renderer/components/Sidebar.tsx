// desktop/src/renderer/components/Sidebar.tsx
//
// Navegação lateral — mesmo esqueleto do Atlans Studio, para quem usa os dois
// reconhecer de imediato.
//
// Além de navegar, a barra carrega o controle de ciclo de vida do executor —
// um alvo grande, no mesmo lugar em qualquer aba. O ESTADO (conectado, parado)
// não está aqui: ele é chrome da janela e vive na StatusBar do rodapé, onde a
// largura não é disputada com a navegação.
import { useEffect, useState, type ReactNode } from 'react'
import {
  TbActivity, TbAdjustments, TbCloudDataConnection, TbHandStop, TbLayoutDashboard,
  TbLoader2, TbPlayerPlayFilled, TbPlayerStopFilled,
} from 'react-icons/tb'
import type { EstadoApp } from '../../main/state/store.js'
import { Button } from './ui/button.js'
import { cn } from '../lib/utils.js'

/**
 * As telas do app.
 *
 * Sem 'logs': o log não é mais uma aba. Ele abre em JANELA PRÓPRIA pelo botão da
 * barra de rodapé, que é como ele se usa — acompanhado ao lado de outra coisa,
 * e não visitado no lugar dela.
 */
export type Aba = 'painel' | 'execucoes' | 'geosync' | 'ajustes'

const ITENS: Array<{ id: Aba; rotulo: string; icone: ReactNode }> = [
  { id: 'painel', rotulo: 'Painel', icone: <TbLayoutDashboard size={17} /> },
  { id: 'execucoes', rotulo: 'Execuções', icone: <TbActivity size={17} /> },
  { id: 'geosync', rotulo: 'GeoSync', icone: <TbCloudDataConnection size={17} /> },
  { id: 'ajustes', rotulo: 'Ajustes', icone: <TbAdjustments size={17} /> },
]

/**
 * Quanto tempo o botão "Forçar parada" fica inerte depois de aparecer.
 *
 * Meio segundo é o intervalo padrão de duplo clique do Windows: acima disso o
 * clique já não é acidental, e abaixo o botão destrutivo herdaria o segundo
 * clique de quem só quis parar.
 */
const MS_ATE_LIBERAR_FORCAR = 500

/**
 * O controle de ciclo de vida — um botão só, que muda de papel com o estado.
 *
 * Dois botões lado a lado (um "Iniciar" e um "Parar", um deles sempre
 * desabilitado) obrigariam a ler os dois para descobrir qual está ativo. Aqui
 * há sempre UMA ação possível, e o ícone diz qual antes do texto ser lido:
 * triângulo para partir, quadrado para parar, mão para forçar.
 *
 * Nos estados de transição o ícone vira um spinner — é o que separa "está
 * demorando" de "o clique não pegou", e sem ele a única pista seria o botão
 * apagado.
 *
 * Não há mais um "ocupado" GLOBAL: as três ações voltam na hora pelo IPC, e quem
 * conta o andamento é o PRÓPRIO estado (o botão vira "Encerrando…", depois
 * "Forçar parada"). O flag antigo ficava preso à promessa de `parar`, que só
 * resolvia no fim da drenagem — e desabilitava até o botão de forçar, que é a
 * saída da espera. O que ficou é local a cada botão, abaixo.
 */
function ControleExecutor({
  estado, aoIniciar, aoParar, aoForcar,
}: {
  estado: EstadoApp
  aoIniciar: () => void
  aoParar: () => void
  aoForcar: () => void
}) {
  // `w-full` + `justify-start`: alinhar os ícones à esquerda deixa a coluna do
  // botão em linha com os ícones da navegação acima.
  const comum = 'w-full justify-start gap-2 font-medium'
  const fase = estado.supervisor

  // Feedback imediato do clique em "Parar".
  //
  // O IPC volta na hora, mas o estado `draining` só chega ~100 ms depois
  // (coalescência do store + IPC + render). Nesse vão o botão ainda dizia
  // "Parar" e continuava clicável: o segundo clique de um duplo clique entrava
  // e pedia uma SEGUNDA parada. Este flag desabilita SÓ este botão — nunca o
  // "Forçar", que aparece em seguida.
  const [paradaPedida, setParadaPedida] = useState(false)
  useEffect(() => {
    // Saiu de `running`/`starting`: o pedido chegou e o botão já é outro.
    if (fase !== 'running' && fase !== 'starting') setParadaPedida(false)
  }, [fase])

  // "Forçar parada" nasce inerte por meio segundo.
  //
  // Ele ocupa a MESMA posição na tela que o "Parar" que acabou de sumir; sem
  // este intervalo, o segundo clique de um duplo clique cairia nele e mataria
  // as execuções em andamento a frio, sem ninguém ter pedido isso.
  const [forcarLiberado, setForcarLiberado] = useState(false)
  useEffect(() => {
    if (fase !== 'draining') {
      setForcarLiberado(false)
      return
    }
    const t = setTimeout(() => setForcarLiberado(true), MS_ATE_LIBERAR_FORCAR)
    return () => clearTimeout(t)
  }, [fase])

  function pedirParada() {
    setParadaPedida(true)
    aoParar()
  }

  switch (fase) {
    // Drenando: insistir em "Parar" não faria nada. A saída é forçar, e ela
    // precisa parecer perigosa — a espera pode chegar a 150s, mas cortá-la
    // mata execuções em andamento.
    case 'draining':
      return (
        <Button size="sm" variant="destructive" className={comum}
                onClick={aoForcar} disabled={!forcarLiberado}
                title="Encerra agora, interrompendo as execuções em andamento">
          <TbHandStop size={15} /> Forçar parada
        </Button>
      )

    case 'restarting':
      return (
        <Button size="sm" variant="outline" className={comum} disabled>
          <TbLoader2 size={15} className="animate-spin" /> Reiniciando…
        </Button>
      )

    // Ainda subindo, mas clicável de propósito: um boot travado precisa de
    // saída, e desabilitar o botão deixaria o usuário sem nenhuma.
    case 'starting':
      return (
        <Button size="sm" variant="outline" className={comum}
                onClick={pedirParada} disabled={paradaPedida}
                title="Cancela a inicialização">
          <TbLoader2 size={15} className="animate-spin" />
          {paradaPedida ? 'Parando…' : 'Iniciando…'}
        </Button>
      )

    case 'running':
      return paradaPedida ? (
        <Button size="sm" variant="outline" className={comum} disabled>
          <TbLoader2 size={15} className="animate-spin" /> Parando…
        </Button>
      ) : (
        <Button size="sm" variant="outline" className={comum}
                onClick={pedirParada}
                title="Encerra depois que as execuções em andamento terminarem">
          <TbPlayerStopFilled size={15} className="text-destructive" />
          Parar
        </Button>
      )

    // `stopped` e `failed`: a ação é a mesma, e é a única de destaque no app —
    // fica no `default` do botão, na cor primária.
    default:
      return (
        <Button size="sm" className={comum} onClick={aoIniciar}>
          <TbPlayerPlayFilled size={15} />
          Iniciar executor
        </Button>
      )
  }
}

export function Sidebar({
  aba, aoTrocar, pendencias, estado, aoIniciar, aoParar, aoForcar,
}: {
  aba: Aba
  aoTrocar: (a: Aba) => void
  /** Telas com alterações não salvas — ganham um ponto na navegação. */
  pendencias?: Partial<Record<Aba, boolean>>
  estado: EstadoApp
  aoIniciar: () => void
  aoParar: () => void
  aoForcar: () => void
}) {

  return (
    <aside className="flex w-48 shrink-0 flex-col border-r border-sidebar-border bg-sidebar">
      <nav aria-label="Seções do aplicativo" className="flex flex-1 flex-col gap-0.5 p-2">
        {ITENS.map((item) => {
          const ativo = aba === item.id
          const emExecucao = estado.snapshot?.running_count ?? 0
          return (
          <button
            key={item.id}
            type="button"
            onClick={() => aoTrocar(item.id)}
            // `aria-current="page"` é o que diz "você está aqui" a quem não vê
            // o realce; o `focus-visible` é a receita do system.md (Focus &
            // Accessibility) — esta navegação é a ÚNICA rota de teclado do app,
            // e sem anel de foco quem tabula não sabe onde está.
            aria-current={ativo ? 'page' : undefined}
            className={cn(
              'flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm outline-none',
              'transition-all active:scale-[0.98]',
              'focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]',
              ativo
                ? 'bg-sidebar-accent font-medium text-sidebar-foreground'
                : 'text-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground',
            )}
          >
            {/* `transition-colors` no ícone também: sem ele o fundo transicionava
                e o glifo saltava de cinza para laranja no mesmo quadro. */}
            <span className={cn('shrink-0 transition-colors', ativo && 'text-primary')}>
              {item.icone}
            </span>
            <span className="flex-1 text-left">{item.rotulo}</span>

            {/* Contadores só onde há algo a notar — um "0" em toda linha não
                informa e polui. */}
            {item.id === 'execucoes' && emExecucao > 0 && (
              <span
                className="rounded-full bg-blue-500/20 px-1.5 text-[10px] font-semibold text-blue-400 tabular-nums animate-in fade-in-0 zoom-in-95 duration-200"
                title={`${emExecucao} ${emExecucao === 1 ? 'execução em andamento' : 'execuções em andamento'}`}
              >
                {emExecucao}
              </span>
            )}

            {/* Alterações não salvas nesta tela.
                Um ponto, e não um texto: a navegação tem 192px e o recado é
                binário. A cor é a primária, e não a de erro — não há nada
                errado, só trabalho por concluir.

                `title` mais `sr-only`: o alvo tem 6px e o `title` sozinho é um
                recado que só existe para quem acerta o ponteiro nele. */}
            {pendencias?.[item.id] && (
              <span
                className="size-1.5 shrink-0 rounded-full bg-primary animate-in fade-in-0 zoom-in-50 duration-200"
                title="Alterações não salvas"
              >
                <span className="sr-only">Alterações não salvas</span>
              </span>
            )}
          </button>
          )
        })}
      </nav>

      {/* ── Rodapé: estado e ação ─────────────────────────────────────────
          Fica na barra, e não no cabeçalho de uma aba, para continuar visível
          enquanto o usuário lê o log ou mexe nos ajustes. */}
      <div className="border-t border-sidebar-border p-2">
        <ControleExecutor
          estado={estado}
          aoIniciar={aoIniciar} aoParar={aoParar} aoForcar={aoForcar}
        />
      </div>
    </aside>
  )
}
