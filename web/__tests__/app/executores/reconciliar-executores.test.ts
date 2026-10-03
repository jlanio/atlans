import { describe, it, expect } from "vitest"
import { reconciliarExecutores } from "@/app/(dashboard)/executores/reconciliar-executores"
import type { IExecutor } from "@/service/types"

// Factory that simulates what arrives from the poll: ALWAYS new objects, as
// JSON.parse of each response produces.
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

    // Without this, ExecutorCard's React.memo misses on 100% of the 15s ticks.
    expect(segundo[0]).toBe(primeiro[0])
    expect(segundo[1]).toBe(primeiro[1])
    // Nothing changed: even the array is the same, so the derived useMemos stop there.
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

    const withNew = reconciliarExecutores(primeiro, [executor("a"), executor("b"), executor("c")])
    expect(withNew).toHaveLength(3)
    expect(withNew[0]).toBe(primeiro[0])

    const withoutB = reconciliarExecutores(withNew, [executor("a"), executor("c")])
    expect(withoutB.map(e => e.id_hash)).toEqual(["a", "c"])

    // The same pair in swapped order is a NEW list (the order is rendered),
    // but the objects are still the same ones.
    const invertida = reconciliarExecutores(withoutB, [executor("c"), executor("a")])
    expect(invertida).not.toBe(withoutB)
    expect(invertida[0]).toBe(withoutB[1])
    expect(invertida[1]).toBe(withoutB[0])
  })
})
