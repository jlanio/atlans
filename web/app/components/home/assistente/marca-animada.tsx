// web/app/components/home/assistente/marca-animada.tsx
//
// A marca do site, animada, sem o fundo laranja: três nós num triângulo e três
// arestas. Um traço percorre cada aresta (n1 → n2 → n3 → n1) e acende o nó ao
// chegar, num ciclo de 2,4 s com uma respiração leve do conjunto — o desenho do
// previewer aprovado. É o indicador do ITEM PENDENTE da conversa na Home (o
// "Trabalhando…" da faixa e do painel, pelo `indicador` da `Conversa`): ali quem
// pensa é o site, e a marca é o que diz isso. O editor fica com o `ExecActivity`.
//
// Mesma API do `ExecActivity` (`size`, `className`, `aria-hidden`); a animação
// mora em `globals.css` (`.home-marca-anim`), inclusive a degradação sob
// `prefers-reduced-motion`: a marca inteira, parada. As cores vêm de
// `var(--primary)` — a terracota da Home, não um literal.

const ARESTAS = ["M12 4.5L19 17", "M19 17L5 17", "M5 17L12 4.5"] as const
const NOS = [
  { cx: 12, cy: 4.5 },
  { cx: 19, cy: 17 },
  { cx: 5, cy: 17 },
] as const

export default function MarcaAnimada({ size = 14, className }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      className={className ? `home-marca-anim ${className}` : "home-marca-anim"}
      aria-hidden="true"
      focusable="false"
    >
      <g className="respira">
        {ARESTAS.map((d) => <path key={`trilho-${d}`} className="trilho" d={d} />)}
        {ARESTAS.map((d, i) => <path key={`traco-${d}`} className={`traco a${i + 1}`} d={d} />)}
        {NOS.map((no, i) => <circle key={`no-${i}`} className={`no n${i + 1}`} cx={no.cx} cy={no.cy} r={2.3} />)}
      </g>
    </svg>
  )
}
