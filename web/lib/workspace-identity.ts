/**
 * Identidade visual determinística de workspaces.
 *
 * Objetivo: dar a cada workspace uma cor + par de iniciais consistentes,
 * SEM migration de DB nem UI de configuração. A cor é escolhida de uma
 * paleta fixa via hash do `id_hash`, então:
 *
 *   - Mesmo workspace sempre tem a mesma cor pra qualquer usuário e sessão.
 *   - Reconhecimento visual rápido (sidebar colapsada mostra só o avatar).
 *   - Ao trocar de workspace, a mudança de cor no header + toast dão
 *     feedback imediato de que o escopo mudou.
 *
 * Paleta: Tailwind `-500` de 10 cores balanceadas. Todas passam WCAG AA
 * com `text-white` — funciona em light e dark mode sem swap adicional.
 */

export interface WorkspaceIdentity {
  /** 1-2 letras maiúsculas, ex: "M", "MK", "FG" */
  initials: string
  /** Classe Tailwind pro fundo do avatar, ex: "bg-emerald-500" */
  bg: string
  /** Classe Tailwind pro texto do avatar (sempre branco) */
  fg: string
  /** Classe Tailwind pra ring de foco/hover, ex: "ring-emerald-500/40" */
  ring: string
}

// Paleta cuidada: cores -500 que contrastam bem com `text-white` tanto
// em fundo claro quanto escuro. Ordem determinística — o hash mapeia
// pra índice, então não reordenar sem plano (mudaria a cor de todos os
// workspaces existentes na próxima render).
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
 * djb2 — hash simples e rápido, espalhamento suficiente pra 10 buckets.
 * Retorna sempre um inteiro >= 0 (mask com 0x7fffffff).
 */
function djb2(str: string): number {
  let hash = 5381
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) + hash + str.charCodeAt(i)) & 0x7fffffff
  }
  return hash
}

/**
 * Extrai iniciais do nome do workspace:
 *   - Se tem 2+ palavras: 1ª letra da 1ª + 1ª letra da 2ª ("Fluxo Geo" → "FG")
 *   - Se tem 1 palavra: 2 primeiras letras ("Marketing" → "MA")
 *   - Fallback pra 1 letra se nome tem só 1 char, "?" se vazio.
 * Ignora símbolos (`-`, `_`, dígitos) na quebra por espaço.
 */
function extractInitials(name: string): string {
  const trimmed = name.trim()
  if (!trimmed) return "?"

  // Split em espaço, filtra palavras vazias
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
