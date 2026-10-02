// desktop/src/renderer/components/MetricCard.tsx
//
// Variante de Card para KPI, seguindo .interface-design/system.md:
// header `flex-row items-center justify-between pb-2`, valor `text-2xl font-bold`
// (a unica exceção aceita ao "nao usar font-bold").
//
// O ícone entra num quadrado de fundo tênue, à direita. Ele não decora: quatro
// cartões com a mesma tipografia e nenhuma marca visual obrigam a LER cada
// título para achar o que se procura, e o Painel é justamente a tela que se
// consulta de relance.
// NOTA DE PADRÃO — `CardHeader` é GRID, não flex.
//
// O primitivo (portado do web) declara `grid auto-rows-min grid-rows-[auto_auto]`.
// Um `flex-row` acrescentado por className não faz nada ali: `flex-direction`
// não se aplica a um contêiner de grade, e `justify-between` passa a alinhar
// dentro da célula, não entre irmãos. O efeito era silencioso e visível — cada
// filho caía numa LINHA própria, esticado na largura toda.
//
// A forma certa é a que o próprio primitivo oferece: o que vai à direita entra
// em `CardAction` (o header tem `has-data-[slot=card-action]:grid-cols-[1fr_auto]`),
// e o que acompanha o título à esquerda entra DENTRO de `CardTitle`.
import type { ComponentType } from 'react'
import { Card, CardAction, CardContent, CardHeader, CardTitle } from './ui/card.js'
import { cn } from '../lib/utils.js'

/** Cor do valor. Só onde o número carrega julgamento — o resto fica neutro. */
const TONS = {
  atencao: 'text-warning',
  erro: 'text-destructive',
  ativo: 'text-primary',
} as const

export function MetricCard({
  titulo, valor, rodape, icone: Icone, tom,
}: {
  titulo: string
  valor: string
  rodape?: string
  /**
   * O COMPONENTE do ícone, não um elemento pronto — o tamanho é decidido aqui,
   * e um `size` embutido na chamada tiraria essa liberdade do cartão.
   */
  icone?: ComponentType<{ size?: number; className?: string }>
  tom?: keyof typeof TONS
}) {
  return (
    <Card className="gap-0 py-4 transition-colors hover:border-primary/30">
      {/* Ver a NOTA DE PADRÃO no topo: o ícone vai em `CardAction`, que é o
          slot que o header reserva à direita. Com `flex-row` ele caía numa
          linha própria, ABAIXO do título e alinhado à esquerda — o oposto do
          que o comentário deste arquivo descreve. */}
      <CardHeader className="items-center gap-2 px-4 pb-2">
        <CardTitle className="truncate text-xs font-medium text-muted-foreground">
          {titulo}
        </CardTitle>
        {Icone && (
          <CardAction className={cn(
            'flex size-7 shrink-0 items-center justify-center rounded-md transition-colors',
            tom ? 'bg-current/10' : 'bg-muted',
            tom ? TONS[tom] : 'text-muted-foreground',
          )}>
            <Icone size={15} />
          </CardAction>
        )}
      </CardHeader>
      <CardContent className="px-4">
        {/* `tabular-nums` evita o valor "dançar" a cada tick de 1s quando os
            dígitos trocam de largura. */}
        <div className={cn('text-2xl font-bold tabular-nums', tom && TONS[tom])}>{valor}</div>
        {rodape && <p className="mt-0.5 truncate text-xs text-muted-foreground">{rodape}</p>}
      </CardContent>
    </Card>
  )
}
