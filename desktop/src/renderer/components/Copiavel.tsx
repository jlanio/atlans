// desktop/src/renderer/components/Copiavel.tsx
//
// Valor técnico que o usuário eventualmente precisa mandar para alguém — ID do
// executor, caminho, mensagem de erro.
//
// Existe porque o ID aparecia truncado (`7f26ceba…`) sem nenhuma forma de obter
// o valor inteiro: quem pedisse suporte teria que abrir o `.env` no Explorer.
import { useEffect, useState } from 'react'
import { cn } from '../lib/utils.js'

export function Copiavel({
  valor, rotulo, exibir, className,
}: {
  valor: string
  /** Texto do `title`. Sem ele, o próprio valor. */
  rotulo?: string
  /** O que mostrar, se diferente do valor (ex.: truncado). */
  exibir?: string
  className?: string
}) {
  const [copiado, setCopiado] = useState(false)

  // Some sozinho: um "copiado!" permanente vira ruído na tela.
  useEffect(() => {
    if (!copiado) return
    const t = setTimeout(() => setCopiado(false), 1600)
    return () => clearTimeout(t)
  }, [copiado])

  return (
    <button
      type="button"
      title={copiado ? 'Copiado' : `${rotulo ?? valor} — clique para copiar`}
      onClick={() => {
        void navigator.clipboard.writeText(valor).then(() => setCopiado(true))
      }}
      className={cn(
        'group inline-flex items-center gap-1.5 rounded font-mono text-xs text-muted-foreground',
        'transition-colors hover:text-foreground',
        className,
      )}
    >
      <span>{exibir ?? valor}</span>
      <span className={cn(
        'text-[10px] transition-opacity',
        copiado ? 'text-green-600 opacity-100 dark:text-green-400' : 'opacity-0 group-hover:opacity-60',
      )}>
        {copiado ? 'copiado' : 'copiar'}
      </span>
    </button>
  )
}
