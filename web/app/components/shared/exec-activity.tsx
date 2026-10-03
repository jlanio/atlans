/**
 * Activity indicator for the node being executed — four bars oscillating out
 * of phase.
 *
 * It replaced the spinning spinner (`TbLoader`/`TbLoader2`). Rotation is the
 * universal "please wait" glyph, and what this badge needs to say is something
 * else: that there is work HAPPENING in there. Out-of-phase oscillation reads as
 * activity — processing, computing — rather than waiting.
 *
 * A local SVG and not a `react-icons` icon: no Tabler glyph has this shape, and
 * the animation needs to hit each bar with its own delay, which requires
 * controlling the inner elements. The animation itself lives in `globals.css`
 * (`.exec-activity`), alongside the other execution states — including the
 * degradation under `prefers-reduced-motion`.
 */
const ExecActivity = ({ size = 14, className }: { size?: number; className?: string }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    className={className ? `exec-activity ${className}` : "exec-activity"}
    aria-hidden="true"
    focusable="false"
  >
    <g fill="currentColor">
      <rect x="3"    y="5" width="3.4" height="14" rx="1.7" />
      <rect x="8.3"  y="5" width="3.4" height="14" rx="1.7" />
      <rect x="13.6" y="5" width="3.4" height="14" rx="1.7" />
      <rect x="18.9" y="5" width="3.4" height="14" rx="1.7" />
    </g>
  </svg>
)

export default ExecActivity
