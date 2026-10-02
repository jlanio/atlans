// desktop/src/renderer/components/Alerta.tsx
//
// Faixa de aviso/erro — o padrão que estava resolvido dentro do App.tsx, sem
// `export`, e por isso remontado à mão no GeoSync e no Ajustes. As três cópias
// já haviam divergido em três paddings, dois radius e dois tamanhos de texto: o
// mesmo tipo de evento aparecia com peso visual diferente conforme a aba, e
// qualquer melhoria (o ícone, o `role`) teria de ser feita três vezes.
//
// Duas coisas que só existem aqui:
//
//   - ÍCONE. Antes o único traço que separava erro de aviso era o matiz da
//     borda — a 40% de alfa, sobre fundo escuro. Quem não distingue vermelho de
//     amarelo lia os dois como "uma faixa". Forma antes de cor.
//   - `role`. O alerta monta de forma assíncrona (o estado chega por IPC
//     enquanto a pessoa pode estar em qualquer aba) e é a única superfície que
//     anuncia "o executor não está rodando". Sem `role`/`aria-live`, nada é
//     anunciado: o app só muda de cor num canto que pode não estar sob o olho.
import type { ReactNode } from 'react'
import { TbAlertTriangle, TbCircleX } from 'react-icons/tb'

import { Card, CardContent } from './ui/card.js'
import { cn } from '../lib/utils.js'

const TONS = {
  erro: {
    caixa: 'border-destructive/40 bg-destructive/5',
    marca: 'text-destructive',
    Icone: TbCircleX,
  },
  aviso: {
    caixa: 'border-warning/40 bg-warning/5',
    marca: 'text-warning',
    Icone: TbAlertTriangle,
  },
} as const

export function Alerta({
  tom, titulo, remedio, bruto, denso, children,
}: {
  tom: 'erro' | 'aviso'
  titulo: ReactNode
  /** Frase acionável: o que fazer. Precede a mensagem crua. */
  remedio?: ReactNode
  /** Mensagem do sistema. Acompanha o remédio — é o que o suporte precisa ler. */
  bruto?: string | null
  /** Variante embutida numa seção, sem o peso de um cartão inteiro. */
  denso?: boolean
  children?: ReactNode
}) {
  const { caixa, marca, Icone } = TONS[tom]

  const conteudo = (
    <>
      <Icone
        size={denso ? 15 : 17}
        className={cn('mt-0.5 shrink-0', marca)}
        aria-hidden="true"
      />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <p className={cn('font-medium', denso ? 'text-xs' : 'text-sm')}>{titulo}</p>
        {(remedio || bruto) && (
          <p className={cn('text-muted-foreground select-text', denso ? 'text-xs' : 'text-sm')}>
            {remedio ?? bruto}
          </p>
        )}
        {remedio && bruto && (
          <p className="font-mono text-xs break-words text-muted-foreground select-text">{bruto}</p>
        )}
      </div>
      {children && <div className="flex shrink-0 gap-2">{children}</div>}
    </>
  )

  // `role`/`aria-live` valem nas duas formas: um erro embutido numa seção
  // continua sendo um erro que ninguém pediu para ver.
  const semantica = {
    role: tom === 'erro' ? ('alert' as const) : ('status' as const),
    'aria-live': tom === 'erro' ? ('assertive' as const) : ('polite' as const),
  }

  if (denso) {
    return (
      <div
        {...semantica}
        className={cn(
          'flex items-start gap-2 rounded-md border px-3 py-2 leading-relaxed',
          // Entra esmaecendo: a faixa aparece por conta de um evento externo,
          // e um bloco que materializa em corte seco empurra o conteúdo abaixo
          // sem que nada indique de onde veio.
          'animate-in fade-in-0 slide-in-from-top-1 duration-200',
          caixa,
        )}
      >
        {conteudo}
      </div>
    )
  }

  return (
    <Card {...semantica} className={cn('py-3 animate-in fade-in-0 slide-in-from-top-2 duration-300', caixa)}>
      <CardContent className="flex flex-wrap items-start justify-between gap-3 px-4">
        {conteudo}
      </CardContent>
    </Card>
  )
}
