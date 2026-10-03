"use client"

import React from "react"
import { CardDescription, CardTitle } from "@/app/components/ui/card"

interface EntityCardProps {
  title: string
  description?: string | null
  onClick?: () => void
  actions?: React.ReactNode
  /** Badge attached to the title — for what the item IS, not for what you do
   *  with it. Actions go in `actions`, on the other side of the card. */
  badge?: React.ReactNode
  leading?: React.ReactNode
  /** Supporting line(s) below the description — chips, counts, dates. Stays in
   *  the text column (wraps, doesn't truncate), unlike `actions`, which is
   *  `shrink-0` and would squeeze the title if it carried many badges. */
  meta?: React.ReactNode
  onTitleDoubleClick?: (e: React.MouseEvent) => void
}

export function EntityCard({ title, description, onClick, actions, badge, leading, meta, onTitleDoubleClick }: EntityCardProps) {
  return (
    // Entrance via CSS (tw-animate-css), as in PageRoot: takes framer-motion
    // out of the Credentials route chunk. The `exit` was dead code — there is
    // no AnimatePresence around this list to animate the exit.
    <div
      onClick={onClick}
      // Stacks on the phone. `actions` usually carries two or three badges besides
      // the menu, and with everything on the same line the group was `shrink-0`
      // while the title shrank: at 360px only a few dozen pixels were left for
      // the item name — precisely what tells one card from another.
      className="animate-in fade-in slide-in-from-bottom-1 duration-200 flex flex-col sm:flex-row w-full justify-between px-3 py-3.5 rounded-lg cursor-pointer gap-2 sm:gap-0 transition-[transform,box-shadow,background-color] hover:bg-accent/40 hover:shadow-md hover:-translate-y-[1px] active:translate-y-0 border bg-card text-card-foreground shadow-xs"
    >
      <div className="flex flex-row min-w-0 flex-1">
        {leading && (
          <div className="flex items-center pr-2" onClick={e => e.stopPropagation()}>
            {leading}
          </div>
        )}

        <div className="flex flex-col justify-center gap-0.5 flex-1 min-w-0 px-2">
          {/* truncate: the container is already min-w-0, but without this a long title
              wrapped onto several lines and the card height clashed with the skeleton. */}
          {/* The title truncates; the badge doesn't. Without `min-w-0` on the title the
              flex box refuses to shrink it and the badge is pushed out of the card. */}
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

      {/* gap-2, not gap-4: the space between badges and menu was larger than the space
          BETWEEN the cards (gap-3), inverting the visual hierarchy.
          `pl-10` on the phone aligns the badges with the text, not with the card
          edge, making it clear they belong to the item above. */}
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
