"use client"

// web/app/components/home/assistente/respostas-rapidas.tsx
//
// As respostas rápidas: até três continuações curtas que o assistente oferece
// sob a resposta (`sugerir_respostas`, no servidor) e que a pessoa escolhe com
// um clique. Mesma linguagem dos chips do hero (`barra.tsx`), com UMA diferença
// de comportamento: os do hero PREENCHEM o campo; estes ENVIAM. Quem decide se
// eles aparecem é o `useExtrasDoAssistente` (só no último turno, fora do
// stream) — aqui é só o desenho e o clique.

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
