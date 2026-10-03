/**
 * Deterministic visual identity for workspaces.
 *
 * Goal: give each workspace a consistent color + pair of initials, WITHOUT a
 * DB migration or a configuration UI. The color is picked from a fixed
 * palette via a hash of `id_hash`, so:
 *
 *   - The same workspace always has the same color for any user and session.
 *   - Fast visual recognition (the collapsed sidebar shows only the avatar).
 *   - When switching workspace, the color change in the header + the toast
 *     give immediate feedback that the scope changed.
 *
 * Palette: Tailwind `-500` of 10 balanced colors. All pass WCAG AA
 * with `text-white` — works in light and dark mode with no extra swap.
 */

export interface WorkspaceIdentity {
  /** 1-2 uppercase letters, e.g. "M", "MK", "FG" */
  initials: string
  /** Classe Tailwind pro fundo do avatar, ex: "bg-emerald-500" */
  bg: string
  /** Tailwind class for the avatar's text (always white) */
  fg: string
  /** Classe Tailwind pra ring de foco/hover, ex: "ring-emerald-500/40" */
  ring: string
}

// Curated palette: -500 colors that contrast well with `text-white` on both
// light and dark backgrounds. Deterministic order — the hash maps to an
// index, so do not reorder without a plan (it would change the color of every
// existing workspace on the next render).
const PALETTE: ReadonlyArray<Pick<WorkspaceIdentity, "bg" | "ring">> = [
  { bg: "bg-emerald-500", ring: "ring-emerald-500/40" },
  { bg: "bg-blue-500",    ring: "ring-blue-500/40"    },
  { bg: "bg-violet-500",  ring: "ring-violet-500/40"  },
  { bg: "bg-pink-500",    ring: "ring-pink-500/40"    },
  { bg: "bg-amber-500",   ring: "ring-amber-500/40"   },
  { bg: "bg-cyan-500",    ring: "ring-cyan-500/40"    },
  { bg: "bg-rose-500",    ring: "ring-rose-500/40"    },
  { bg: "bg-indigo-500",  ring: "ring-indigo-500/40"  },
  { bg: "bg-lime-500",    ring: "ring-lime-500/40"    },
  { bg: "bg-orange-500",  ring: "ring-orange-500/40"  },
]

/**
 * djb2 — a simple, fast hash, with enough spread for 10 buckets.
 * Always returns an integer >= 0 (masked with 0x7fffffff).
 */
function djb2(str: string): number {
  let hash = 5381
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) + hash + str.charCodeAt(i)) & 0x7fffffff
  }
  return hash
}

/**
 * Extracts initials from the workspace name:
 *   - With 2+ words: 1st letter of the 1st + 1st letter of the 2nd ("Fluxo Geo" → "FG")
 *   - With 1 word: the first 2 letters ("Marketing" → "MA")
 *   - Falls back to 1 letter if the name has only 1 char, "?" if empty.
 * Ignores symbols (`-`, `_`, digits) when splitting on spaces.
 */
function extractInitials(name: string): string {
  const trimmed = name.trim()
  if (!trimmed) return "?"

  // Split on spaces, filter out empty words
  const words = trimmed.split(/\s+/).filter(Boolean)

  if (words.length >= 2) {
    const first = words[0][0] ?? ""
    const second = words[1][0] ?? ""
    return (first + second).toUpperCase()
  }

  const w = words[0] ?? ""
  return (w.length >= 2 ? w.slice(0, 2) : w).toUpperCase()
}

export function getWorkspaceIdentity(workspace: {
  id_hash: string
  name: string
}): WorkspaceIdentity {
  const idx = djb2(workspace.id_hash) % PALETTE.length
  const { bg, ring } = PALETTE[idx]
  return {
    initials: extractInitials(workspace.name),
    bg,
    fg: "text-white",
    ring,
  }
}
