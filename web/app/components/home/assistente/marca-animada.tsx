// web/app/components/home/assistente/marca-animada.tsx
//
// The site's logo, animated, without the orange background: three nodes in a
// triangle and three edges. A stroke travels each edge (n1 → n2 → n3 → n1) and
// lights the node on arrival, in a 2.4 s cycle with a light breathing of the
// whole — the approved previewer design. It is the indicator of the conversation's
// PENDING ITEM on the Home (the "Trabalhando…" of the strip and the panel, through
// the `Conversa`'s `indicador`): there, the one thinking is the site, and the
// logo is what says so. The editor keeps the `ExecActivity`.
//
// Same API as `ExecActivity` (`size`, `className`, `aria-hidden`); the animation
// lives in `globals.css` (`.home-marca-anim`), including the degradation under
// `prefers-reduced-motion`: the whole logo, still. The colors come from
// `var(--primary)` — the Home's terracotta, not a literal.

const EDGES = ["M12 4.5L19 17", "M19 17L5 17", "M5 17L12 4.5"] as const
const NODES = [
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
        {EDGES.map((d) => <path key={`trilho-${d}`} className="trilho" d={d} />)}
        {EDGES.map((d, i) => <path key={`traco-${d}`} className={`traco a${i + 1}`} d={d} />)}
        {NODES.map((no, i) => <circle key={`no-${i}`} className={`no n${i + 1}`} cx={no.cx} cy={no.cy} r={2.3} />)}
      </g>
    </svg>
  )
}
