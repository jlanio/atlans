# Atlans — Design System

Extracted from the existing components in `web/app/components/`.
Framework: Tailwind CSS v4 + shadcn/ui + Radix primitives.

---

## Spacing

Base unit: **4px** (Tailwind rem/4 system)

| Token     | Value | Main use                             |
|-----------|-------|--------------------------------------|
| `gap-0.5` | 2px   | Between icon and inline text         |
| `gap-1`   | 4px   | Compact items                        |
| `gap-1.5` | 6px   | Card header rows, sheet header       |
| `gap-2`   | 8px   | Footer buttons, dialog header/desc   |
| `gap-4`   | 16px  | Sections inside card/dialog/sheet    |
| `gap-6`   | 24px  | Page sections (PageRoot)             |

| Context        | Horizontal | Vertical   |
|----------------|------------|------------|
| Page (PageRoot)| `px-8`(32) | `py-8`(32) |
| Card content   | `px-6`(24) | `py-5`(20) |
| Dialog content | `p-6` (24) | `p-6` (24) |
| Sheet header   | `p-4` (16) | `p-4` (16) |
| EntityCard     | `px-3`(12) | `py-3.5`(14) |
| Table cell     | `px-4-6`   | `py-2-2.5` |

**Rule:** Spacing must sit on the 4px grid. Tolerated exceptions: `py-3.5`(14px) in EntityCard, `py-0.5`(2px) in badges.

---

## Radius

Base CSS variable: `--radius: 0.5rem` (8px)

| Token        | Value | Calculation              | Use                          |
|--------------|-------|--------------------------|------------------------------|
| `rounded-sm` | 4px   | `var(--radius) - 4px`    | Select items, separators     |
| `rounded-md` | 6px   | `var(--radius) - 2px`    | Button, Input, Select, Skeleton |
| `rounded-lg` | 8px   | `var(--radius)`          | Card, Dialog, EntityCard     |
| `rounded-xl` | 12px  | `var(--radius) + 4px`    | Larger containers            |
| `rounded-full`| pill | —                        | Badge, StatusBadge, Avatar   |

**Rule:** Do not use arbitrary radius values (`rounded-[Xpx]`). Use only the tokens above.

---

## Depth (Elevation)

Strategy: **Borders-first** with minimal shadows for elevation.

| Level     | Style                  | Components                 |
|-----------|------------------------|----------------------------|
| Level 0   | no border/shadow       | Backgrounds, content areas |
| Level 1   | `border` + `shadow-xs` | Card, EntityCard           |
| Level 2   | `border` + `shadow-md` | Select popover, Dropdown   |
| Level 3   | `border` + `shadow-lg` | Dialog, Sheet              |

**Rules:**
- Ring shadows (`ring-[3px]`, `0 0 0 Xpx`) are allowed for focus states.
- `shadow-xl` and `shadow-2xl` are not used — avoid them.
- Overlays use `bg-black/50`.

---

## Colors

OKLCH token system via CSS custom properties. Two themes: light and dark.

### Semantic tokens

| Token                  | Light (oklch)              | Dark (oklch)               |
|------------------------|----------------------------|----------------------------|
| `--background`         | `0.985 0.003 75`           | `0.188 0.008 55`           |
| `--foreground`         | `0.18 0.02 65`             | `0.93 0.004 70`            |
| `--primary`            | `0.57 0.17 43` (terracotta)| `0.68 0.16 44`             |
| `--primary-foreground` | `1 0 0` (white)            | `0.99 0 0`                 |
| `--secondary`          | `0.96 0.006 72`            | `0.285 0.008 55`           |
| `--muted`              | `0.96 0.006 72`            | `0.270 0.008 55`           |
| `--muted-foreground`   | `0.50 0.03 68`             | `0.60 0.008 60`            |
| `--accent`             | `0.95 0.008 70`            | `0.270 0.008 55`           |
| `--destructive`        | `0.577 0.245 27.325`       | `0.65 0.21 22`             |
| `--card`               | `1 0 0`                    | `0.215 0.008 55`           |
| `--border`             | `0.90 0.012 70`            | `1 0 0 / 9%`               |

### Status colors (hardcoded in StatusBadge)

| Status    | Background      | Text            |
|-----------|-----------------|-----------------|
| success   | `bg-green-100`  | `text-green-700` |
| failed    | `bg-red-100`    | `text-red-700`   |
| error     | `bg-red-100`    | `text-red-700`   |
| running   | `bg-blue-100`   | `text-blue-700`  |
| pending   | `bg-yellow-100` | `text-yellow-700`|
| cached    | `bg-purple-100` | `text-purple-700`|
| cancelled | `bg-amber-100`  | `text-amber-700` |
| fallback  | `bg-muted`      | `text-muted-foreground` |

Each pair above always comes with its `dark:` variant in the code (e.g. `dark:bg-green-500/15 dark:text-green-400`, `cancelled` → `dark:bg-amber-500/15 dark:text-amber-400`); the table lists only the light tone. Source: `StatusBadge.tsx`.

### Execution on the canvas (`--exec-*`)

Single source of the execution state, consumed by the node's card **and** by the edge leaving it. Before, each one carried its own hex, the two disagreed (`unknown` left the card amber and the edge gray) and neither switched with the theme.

| Token           | Light (oklch)      | Dark (oklch)      | Use                        |
|-----------------|--------------------|-------------------|----------------------------|
| `--exec-idle`   | `0.62 0.020 68`    | `0.56 0.015 62`   | neutral; losing branch     |
| `--exec-running`| `0.58 0.160 254`   | `0.70 0.145 250`  | node in `started`          |
| `--exec-success`| `0.62 0.145 152`   | `0.74 0.150 152`  | `completed`; `true` branch |
| `--exec-error`  | `0.575 0.205 27`   | `0.68 0.190 24`   | `failed`; `false` branch   |
| `--exec-unknown`| `0.70 0.140 72`    | `0.80 0.140 76`   | `unknown`                  |
| `--exec-cache`  | `0.74 0.150 88`    | `0.85 0.140 90`   | `cache_hit` badge          |

Available as utilities (`text-exec-running`, `bg-exec-error/10`) via `@theme inline`. `--exec-halo-near` / `--exec-halo-far` calibrate the halo intensity per theme.

**Canvas rules:**
- The state ring lives in `.exec-card::after` (`outline`), **never** in `ring-*`. `ring-*`, `shadow-sm` and glow keyframes compete for the same `box-shadow` property, and a keyframe replaces the whole declaration — that is what was erasing the selection ring during the pulse.
- The halo lives in `.exec-card::before` and animates only `opacity`/`transform` (compositor). Animating blur or spread repaints the shadow on every frame, on every active node.
- States are also distinguished by **shape**, not only by hue: `unknown` and "pending" use a dashed ring, because at 0.42 zoom two ambers become the same blot.

### Chart colors

`chart-1` to `chart-5` defined in `globals.css`. Use them via the `--chart-N` tokens.

**Rules:**
- Always use semantic tokens (`text-foreground`, `bg-primary`, etc.) — never raw colors (`text-gray-900`) for general content.
- Status colors (green/red/blue/yellow/purple-100/700) are the accepted exception for status indicators in `StatusBadge`. On the workflow canvas use the `--exec-*` tokens.
- `text-[10px]` in the trend badges is the only size exception outside the grid.

---

## Typography

Fonts: Inter (body; `--font-sans`, via next/font in `app/layout.tsx` → `--font-inter`) / the system monospace stack (code/IDs; `--font-mono`: SF Mono, Consolas, Liberation Mono…). Inter loads weights 400–700; the system mono only has 400 and 700, so `font-medium` in `font-mono` comes out regular.

| Level           | Classes                               | Use                              |
|-----------------|---------------------------------------|----------------------------------|
| Page title      | `text-2xl font-semibold`              | Page h1                          |
| Section title   | `text-base font-medium` or `font-semibold` | Section CardTitle           |
| Body            | `text-sm`                             | General text, labels, inputs    |
| Description     | `text-sm text-muted-foreground`       | CardDescription, DialogDescription |
| Meta            | `text-xs text-muted-foreground`       | Timestamps, IDs, stats          |
| Micro           | `text-[10px]`                         | Trend badges (exception)        |
| Mono            | `font-mono text-xs`                   | Run IDs, hashes                 |

**Rules:**
- `font-semibold` for Card/Dialog titles.
- `font-medium` for labels, badges, list items.
- Do not use `font-bold` outside highlighted numeric values (`text-2xl font-bold` in MetricCard).

---

## Patterns

### Button

Defined in `ui/button.tsx` via CVA.

| Size      | Height | Padding          | Radius      |
|-----------|--------|------------------|-------------|
| `default` | h-9    | `px-4 py-2`      | `rounded-md`|
| `sm`      | h-8    | `px-3`           | `rounded-md`|
| `lg`      | h-10   | `px-6`           | `rounded-md`|
| `icon`    | size-9 | —                | `rounded-md`|

Variants: `default`, `destructive`, `outline`, `secondary`, `ghost`, `link`.

**Rule:** Do not create ad-hoc buttons with `<button className="...">`. Always use the component's `<Button>`.

### Card

Defined in `ui/card.tsx`.

- Container: `rounded-lg border shadow-xs bg-card text-card-foreground`
- Vertical gap: `gap-4` between sections
- Header/Content/Footer: `px-6`
- Card vertical padding: `py-5`

**EntityCard** (compact variant for lists):
- `px-3 py-3.5 rounded-lg gap-0`
- Title: `text-sm font-medium`
- Description: `text-xs`

**MetricCard** (variant for KPIs):
- Uses the standard Card
- Header: `flex-row items-center justify-between pb-2`
- Value: `text-2xl font-bold`

### Input

Defined in `ui/input.tsx`.

- Height: `h-9` (36px)
- Padding: `px-3 py-1`
- Radius: `rounded-md`
- Border: `border border-input`
- Focus: `focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]`

### Badge

Defined in `ui/badge.tsx`.

- Shape: `rounded-full`
- Padding: `px-2.5 py-0.5`
- Text: `text-xs font-semibold`
- Border: `border` (transparent for filled variants)

**StatusBadge** (variant for execution status):
- Same shape as Badge but with hardcoded colors per status
- Includes an inline icon (TbCheck, TbX)

### Dialog

Defined in `ui/dialog.tsx`.

- Max width: `sm:max-w-lg`
- Padding: `p-6`
- Radius: `rounded-lg`
- Depth: `border shadow-lg`
- Gap: `gap-4` between header/content/footer
- Overlay: `bg-black/50`

### Sheet

Defined in `ui/sheet.tsx`.

- Default side: `right`
- Max width: `sm:max-w-sm`
- Depth: `shadow-lg` + side border
- Header/Footer: `p-4`
- Gap: `gap-4`

---

## Layout

### Page container (PageRoot)

```
<main className="flex justify-center w-full px-safe">
  <div className="flex flex-col gap-4 px-4 py-6 sm:gap-6 sm:px-8 sm:py-8 max-w-6xl w-full animate-in fade-in slide-in-from-bottom-2 duration-350 ease-out">
```

### Grid patterns

| Context           | Mobile          | Desktop              |
|-------------------|-----------------|----------------------|
| Indicators/stat   | `grid-cols-2`   | `lg:grid-cols-4`     |
| Content/side      | `grid-cols-1`   | `lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]` |
| Cards/rows        | `sm:grid-cols-2`| `xl:grid-cols-3`     |
| Gaps              | `gap-3`/`gap-4` | `gap-3`/`gap-4`      |

### Column rail (dense listing)

A grid of fixed columns — the rail of `/executores` — does not survive the
phone: the columns add up to ~360px before the name, and the body's `overflow-x: clip`
**cuts off** the excess instead of scrolling, taking the actions column with it.

A pattern in three bands, with ONE grid declaration shared by the header and the
rows:

| Band    | Shape                                                              |
|---------|--------------------------------------------------------------------|
| `< md`  | two lines per item; column header `hidden`; the metadata block becomes a `flex-wrap` line |
| `md`    | lean rail — the columns that only qualify (type, version) go away  |
| `lg`    | full rail                                                          |

**Rules:**
- The same markup serves both shapes: the metadata block uses `md:contents`,
  so from `md` up it disappears from the layout and its children become cells again.
- A cell that only exists in the full rail: `md:hidden lg:block` (or
  `lg:inline-flex`, depending on the element's display).
- The "no value" dash (`—`) is a **column marker**: hide it where there is no
  column, otherwise it becomes a stray symbol in the stacked layout.

### Stacked table (`<table>` on the phone)

`overflow-x-auto` + `min-w-[N]` keeps the table reachable, but reading the status of
a run then requires dragging the list sideways. The repo's pattern is
`app/components/shared/tabela-empilhada.ts`: below `md` the `<tr>` stops being a
row and becomes a `flex-wrap` band of facts, in the same order as the columns.

| Constant               | Where               | What it does                                |
|------------------------|---------------------|---------------------------------------------|
| `COLUMN_HEADER` | `<thead>`           | disappears where there are no columns        |
| `STACKED_ROW`      | data `<tr>`         | becomes a card; zeroes the cells' padding    |
| `CARD_HIGHLIGHT`    | identifying `<td>`  | takes the first line by itself               |
| `LABELED_CELL`    | numeric `<td>`      | carries its label along (`data-rotulo`)      |
| `EXPANDED_ROW`      | `<tr>` with `colSpan` | block, not card                            |

**Rules:**
- All the classes are `max-md:`. From `md` up the table is the same as before —
  no `<td>` needs editing, and there is no way to regress the desktop.
- The table's `min-w-[N]` becomes `md:min-w-[N]`: without columns there is nothing to
  force.
- A number without a column is a stray number: `0` could be failures or cache hits, `1,2 GB`
  could be Drive or total. Those get `data-rotulo`.

### Touch (`coarse:`)

Variant declared in `globals.css` as `@media (pointer: coarse)`. It is about the
POINTER, not the width: a 1280px tablet with touch needs the rule and a
narrow laptop does not.

**Rule:** everything that only appears under `hover:` (the arrow that says the row leads
somewhere, the copy button of a code block) needs a
`coarse:opacity-*` — on the phone `hover:` never happens, and the affordance
simply does not exist.

### Sidebar

- Background: `bg-sidebar` (dedicated token, darker than card)
- Content area: `bg-card`
- Drawer (workflow): `min-w-[26rem] w-[26rem] bg-card`

---

## Animations

| Name               | Duration | Easing          | Use                     |
|--------------------|----------|-----------------|-------------------------|
| `animate-in`       | default  | ease            | Dialog/Sheet/Select open |
| `fade-in-0`        | default  | ease            | Overlays, popovers      |
| `zoom-in-95`       | default  | ease            | Dialog/Tooltip scale-in |
| `slide-in-from-*`  | default  | ease            | Sheet/Select direction  |
| `theme-appear`     | 400ms    | ease-in-out     | Theme toggle            |
| `animate-pulse`    | default  | —               | Skeleton loading        |
| `animate-spin`     | default  | linear          | Loading spinner         |

### Workflow canvas

All in `.exec-card::before` (halo), except where noted. See "Execution on the canvas" under Colors.

| Name                | Duration | Easing                       | State                       |
|---------------------|---------|------------------------------|-----------------------------|
| `exec-breathe`      | 2.4s    | `cubic-bezier(.45,0,.55,1)` ∞ | `started` — breathing      |
| `exec-settle`       | 620ms   | `cubic-bezier(.22,1,.36,1)`  | `completed` — the light settles |
| `exec-alert`        | 760ms   | `cubic-bezier(.22,1,.36,1)`  | `failed` — entrance, then stops |
| `exec-idle-breathe` | 2.8s    | `ease-in-out` ∞              | pending, run underway       |
| `exec-arrive`       | 2.4s    | `cubic-bezier(.22,1,.36,1)`  | newly added node            |
| `edge-flow-fast`    | 420ms   | `linear` ∞                   | active edge — fine layer    |
| `edge-flow-slow`    | 1.5s    | `linear` ∞                   | active edge — coarse layer  |
| `edge-glow-pulse`   | 1.6s    | `ease-in-out` ∞              | glow under the active edge  |
| `edge-flow-hint`    | 1.05s   | `linear` ∞                   | edge under the cursor       |
| `exec-activity-wave`| 1s      | `ease-in-out` ∞              | badge of the running node   |

**Rules:**
- Sheet uses `duration-300` (close) / `duration-500` (open). Dialog uses `duration-200`.
- `failed` does **not** animate in a loop. A still red ring is already loud; what needs to draw attention is the entrance. Several nodes blinking out of phase made the canvas illegible, and the problems panel already chases the user.
- The active edge uses **two** streams of dots in parallax (`fast` fine and quick, `slow` coarse and spaced out) plus the pulsing glow. A single stream of identical dots reads as a dotted line sliding; two of different caliber read as traffic.
- Hover on an idle edge uses `edge-flow-hint` — **one** stream and no glow. That is what separates "direction on demand" from "live edge", now that the active one has gained density.
- The running node's badge uses `ExecActivity` (oscillating bars), **not** a spinning spinner: rotation is the universal glyph for "please wait", and what the badge needs to say is that there is work happening.
- Every canvas animation degrades under `prefers-reduced-motion: reduce` to the **informative frame**, never to nothing: each state must remain distinguishable without motion.

---

## Focus & Accessibility

- Focus ring: `focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:border-ring`
- Invalid state: `aria-invalid:ring-destructive/20 aria-invalid:border-destructive`
- Disabled: `disabled:pointer-events-none disabled:opacity-50`
- Screen reader: `<span className="sr-only">` for close buttons
- SVGs: `[&_svg]:pointer-events-none [&_svg]:shrink-0`
