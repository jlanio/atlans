/**
 * Classes for the layers that float ON TOP of the editor canvas.
 *
 * Two things every overlay has to get right, and that are easy to forget
 * because the defect doesn't look like a CSS defect:
 *
 * 1. **Layer.** Nodes and edges live in `.react-flow__renderer`, which React
 *    Flow declares with `z-index: 4`. An overlay without its own z-index sits
 *    BELOW it: the node covers the button, the click goes to the node, the cursor
 *    becomes the canvas's — and none of that suggests "z-index was missing".
 *
 * 2. **Dead area.** The container's rectangle captures the whole mouse area, not
 *    only where there's a button. A column of buttons with `gap-2` swallows 8px
 *    strips; a container without a defined width swallows the whole screen width.
 *    Dragging the canvas through there gets stuck, and the click target stops
 *    being what you see.
 *
 * Careful when using: the container needs content width (`w-fit` when it isn't
 * `absolute` with a fixed position on both sides) — `pointer-events-none`
 * solves the click, but a giant rectangle still gets in the way of debugging.
 */
export const CAMADA_SOBRE_O_CANVAS =
  "pointer-events-none absolute z-10 [&>*]:pointer-events-auto"

/**
 * Overlay that only informs and never receives clicks (the loading animation).
 *
 * With no interactive children, the whole container gets out of the mouse's way —
 * it can cover the entire canvas without blocking drag or click.
 */
export const CAMADA_SO_LEITURA = "pointer-events-none absolute z-10"
