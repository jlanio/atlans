"use client"

import React from "react"
import { CardDescription, CardTitle } from "@/app/components/ui/card"

interface EntityCardProps {
  title: string
  description?: string | null
  onClick?: () => void
  actions?: React.ReactNode
  /** Selo colado ao título — para o que o item É, e não para o que se faz com
   *  ele. Ações ficam em `actions`, do outro lado do card. */
  badge?: React.ReactNode
  leading?: React.ReactNode
  /** Linha(s) de apoio abaixo da descrição — chips, contagens, datas. Fica na
   *  coluna do texto (quebra linha, não trunca), ao contrário de `actions`,
   *  que é `shrink-0` e espremeria o título se levasse muitos selos. */
  meta?: React.ReactNode
  onTitleDoubleClick?: (e: React.MouseEvent) => void
}

export function EntityCard({ title, description, onClick, actions, badge, leading, meta, onTitleDoubleClick }: EntityCardProps) {
  return (
    // Entrada por CSS (tw-animate-css), como no PageRoot: tira o framer-motion
    // do chunk da rota de Credenciais. O `exit` era código morto — não há
    // AnimatePresence em volta desta lista para animar a saída.
    <div
      onClick={onClick}
      // Empilha no telefone. `actions` costuma trazer dois ou três selos além
      // do menu, e com tudo na mesma linha o conjunto era `shrink-0` enquanto
      // o título encolhia: em 360px sobravam poucas dezenas de pixels para o
      // nome do item — justamente o que distingue um card do outro.
      className="animate-in fade-in slide-in-from-bottom-1 duration-200 flex flex-col sm:flex-row w-full justify-between px-3 py-3.5 rounded-lg cursor-pointer gap-2 sm:gap-0 transition-[transform,box-shadow,background-color] hover:bg-accent/40 hover:shadow-md hover:-translate-y-[1px] active:translate-y-0 border bg-card text-card-foreground shadow-xs"
    >
      <div className="flex flex-row min-w-0 flex-1">
        {leading && (
          <div className="flex items-center pr-2" onClick={e => e.stopPropagation()}>
            {leading}
          </div>
        )}

        <div className="flex flex-col justify-center gap-0.5 flex-1 min-w-0 px-2">
          {/* truncate: o container já é min-w-0, mas sem isto o título longo
              quebrava em várias linhas e a altura do card destoava do skeleton. */}
          {/* O título trunca; o selo não. Sem `min-w-0` no título a flex box
              se recusa a encolhê-lo e o selo é empurrado para fora do card. */}
          <div className="flex items-center gap-1.5 min-w-0">
            <CardTitle
              className="text-sm font-medium truncate min-w-0"
              title={title}
              onDoubleClick={onTitleDoubleClick ? e => { e.stopPropagation(); onTitleDoubleClick(e) } : undefined}
            >{title}</CardTitle>
            {badge}
          </div>
          {description && <CardDescription className="text-xs truncate">{description}</CardDescription>}
          {meta && <div className="min-w-0">{meta}</div>}
        </div>
      </div>

      {/* gap-2, não gap-4: o espaço entre badges e menu era maior que o espaço
          ENTRE os cards (gap-3), invertendo a hierarquia visual.
          `pl-10` no telefone alinha os selos com o texto, e não com a borda do
          card, deixando claro que pertencem ao item de cima. */}
      {actions && (
        <div
          className="flex items-center gap-2 shrink-0 flex-wrap pl-10 sm:pl-0"
          onClick={e => e.stopPropagation()}
        >
          {actions}
        </div>
      )}
    </div>
  )
}
