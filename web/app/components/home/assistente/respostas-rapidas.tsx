"use client"

// web/app/components/home/assistente/respostas-rapidas.tsx
//
// The quick replies: up to three short continuations the assistant offers below
// the answer (`sugerir_respostas`, on the server) that the person picks with a
// click. Same language as the hero chips (`barra.tsx`), with ONE behavioral
// difference: the hero ones FILL the field; these SEND. What decides whether
// they appear is `useExtrasDoAssistente` (only on the last turn, outside the
// stream) — this is only the drawing and the click.

import { useTextos } from "../i18n"

interface Props {
  opcoes: string[]
  onEscolher: (opcao: string) => void
}

export default function RespostasRapidas({ opcoes, onEscolher }: Props) {
  const t = useTextos().assistente
  return (
    <div role="group" aria-label={t.respostasRapidas} className="flex flex-wrap gap-2 pt-0.5">
      {opcoes.map((opcao) => (
        <button
          key={opcao}
          type="button"
          onClick={() => onEscolher(opcao)}
          className="rounded-full border border-white/10 bg-background/60 px-3 py-1.5 text-[12.5px] text-[#cfcfcf] backdrop-blur hover:border-primary/60 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring max-md:min-h-10"
        >
          {opcao}
        </button>
      ))}
    </div>
  )
}
