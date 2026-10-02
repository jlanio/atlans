import { describe, it, expect } from "vitest"
import { reconciliarExecutores } from "@/app/(dashboard)/executores/reconciliar-executores"
import type { IExecutor } from "@/service/types"

// Fábrica que simula o que chega do poll: objetos SEMPRE novos, como o
// JSON.parse de cada resposta produz.
function executor(id: string, extra: Partial<IExecutor> = {}): IExecutor {
  return {
    id_hash:             id,
    name:                `Executor ${id}`,
    description:         null,
    status:              "active",
    executor_type:       "default",
    is_default:          true,
    capabilities:        ["gis"],
    max_concurrent_jobs: 2,
    max_queue_size:      10,
    executor_version:    "2.4.0",
    last_seen_at:        "2026-08-28T12:00:00",
    created_at:          "2026-01-01T00:00:00",
    created_by:          "user-1",
    online:              true,
    capacity:            null,
    connected_at:        "2026-08-28T11:00:00",
    system_info:         null,
    ...extra,
  }
}

describe("reconciliarExecutores", () => {
  it("preserva a identidade dos objetos que não mudaram entre dois ticks", () => {
    const primeiro = [executor("a"), executor("b")]
    const segundo  = reconciliarExecutores(primeiro, [executor("a"), executor("b")])

    // Sem isto o React.memo do ExecutorCard erra em 100% dos ticks de 15s.
    expect(segundo[0]).toBe(primeiro[0])
    expect(segundo[1]).toBe(primeiro[1])
    // Nada mudou: até o array é o mesmo, para os useMemo derivados pararem ali.
    expect(segundo).toBe(primeiro)
  })

  it("troca só o objeto do executor que mudou de fato", () => {
    const primeiro = [executor("a"), executor("b")]
    const segundo  = reconciliarExecutores(primeiro, [
      executor("a"),
      executor("b", { online: false }),
    ])

    expect(segundo).not.toBe(primeiro)
    expect(segundo[0]).toBe(primeiro[0])
    expect(segundo[1]).not.toBe(primeiro[1])
    expect(segundo[1].online).toBe(false)
  })

  it("acompanha entrada, saída e reordenação da lista", () => {
    const primeiro = [executor("a"), executor("b")]

    const comNovo = reconciliarExecutores(primeiro, [executor("a"), executor("b"), executor("c")])
    expect(comNovo).toHaveLength(3)
    expect(comNovo[0]).toBe(primeiro[0])

    const semB = reconciliarExecutores(comNovo, [executor("a"), executor("c")])
    expect(semB.map(e => e.id_hash)).toEqual(["a", "c"])

    // Mesma dupla em ordem trocada é uma lista NOVA (a ordem é renderizada),
    // mas os objetos continuam sendo os mesmos.
    const invertida = reconciliarExecutores(semB, [executor("c"), executor("a")])
    expect(invertida).not.toBe(semB)
    expect(invertida[0]).toBe(semB[1])
    expect(invertida[1]).toBe(semB[0])
  })
})
