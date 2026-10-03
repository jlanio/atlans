"use client"

/**
 * Structured editor for the Sort (Ordenar) node's `sort_by`.
 *
 * The field used to be a raw `object`: the person typed
 * `[{"field":"area","direction":"desc"}]` into a JSON editor — hostile even
 * without suggestions, and with no place to offer the known columns. Here each
 * criterion is a field+direction row, with the last execution's columns one
 * click away.
 *
 * It is a FIELD, not a helper: the node's sibling fields stay visible
 * alongside (the same reason recorded in the chips-field header).
 *
 * The value persists as the SAME `[{field, direction}]` list the backend's
 * execute already reads — no new format: a workflow saved by the JSON editor
 * opens here, and one saved here runs on an old executor.
 */
import { Button } from "@/app/components/ui/button"
import { Input } from "@/app/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/app/components/ui/select"
import { TbPlus, TbTrash } from "react-icons/tb"

import { FieldLabel } from "./field-label"
import ColumnSuggestions from "./sugestoes-de-colunas"
import type { FieldProps } from "./types"

export interface SortCriterion {
  field: string
  direction: "asc" | "desc"
}

/** Reads the saved value, whether it comes as a list (ObjectField/definition) or a JSON string. */
export function lerCriterios(bruto: unknown): SortCriterion[] {
  let lista: unknown = bruto
  if (typeof bruto === "string" && bruto.trim().startsWith("[")) {
    try { lista = JSON.parse(bruto) } catch { lista = [] }
  }
  if (!Array.isArray(lista)) return []
  return lista
    .filter((c): c is Record<string, unknown> => !!c && typeof c === "object")
    .map(c => ({
      field: String(c.field ?? ""),
      direction: String(c.direction ?? "asc").toLowerCase() === "desc" ? "desc" as const : "asc" as const,
    }))
}

type SortByFieldProps = FieldProps<{
  sugestoes?: string[]
  sugestoesDesatualizadas?: boolean
  sugestoesParciais?: boolean
}>

const SortByField = ({ field, values, setNodeField, sugestoes = [], sugestoesDesatualizadas = false, sugestoesParciais = false }: SortByFieldProps) => {
  const criteria = lerCriterios(values?.[field.name])

  // The REAL list, not a JSON string: it is what execute reads today — and the
  // cast is the same as in SetFieldsHelper, because `setNodeField` only types scalars.
  const gravar = (next: SortCriterion[]) =>
    setNodeField(field.name, next as unknown as string)

  const editar = (idx: number, mudanca: Partial<SortCriterion>) =>
    gravar(criteria.map((c, i) => (i === idx ? { ...c, ...mudanca } : c)))

  // Click on a suggestion: fills the first empty row or opens a new one —
  // never replaces what has already been typed.
  function escolher(nome: string) {
    const vazia = criteria.findIndex(c => c.field.trim() === "")
    if (vazia >= 0) editar(vazia, { field: nome })
    else gravar([...criteria, { field: nome, direction: "asc" }])
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <FieldLabel field={field} />
        <Button
          size="icon" variant="ghost" className="h-6 w-6"
          aria-label="Adicionar critério"
          onClick={() => gravar([...criteria, { field: "", direction: "asc" }])}
        >
          <TbPlus className="h-3.5 w-3.5" />
        </Button>
      </div>

      {criteria.length === 0 ? (
        <p className="text-[11px] text-muted-foreground italic px-1">
          Nenhum critério. Clique em + (ou numa coluna abaixo) para adicionar.
        </p>
      ) : (
        <div className="flex flex-col gap-1.5">
          {criteria.map((criterion, idx) => (
            <div key={idx} className="grid grid-cols-[1fr_7.5rem_auto] gap-1.5 items-center">
              <Input
                value={criterion.field}
                placeholder="nome_da_coluna"
                className="h-7 text-xs font-mono"
                onChange={e => editar(idx, { field: e.target.value })}
              />
              <Select
                value={criterion.direction}
                onValueChange={v => editar(idx, { direction: v as SortCriterion["direction"] })}
              >
                <SelectTrigger className="h-7 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="asc">Crescente</SelectItem>
                  <SelectItem value="desc">Decrescente</SelectItem>
                </SelectContent>
              </Select>
              <Button
                size="icon" variant="ghost"
                className="h-7 w-7 text-muted-foreground hover:text-destructive"
                aria-label={`Remover critério ${idx + 1}`}
                onClick={() => gravar(criteria.filter((_, i) => i !== idx))}
              >
                <TbTrash className="h-3.5 w-3.5" />
              </Button>
            </div>
          ))}
        </div>
      )}

      <ColumnSuggestions
        nomes={sugestoes.filter(s => !criteria.some(c => c.field === s))}
        onEscolher={escolher}
        totalConhecido={sugestoes.length}
        desatualizadas={sugestoesDesatualizadas}
        parciais={sugestoesParciais}
      />
    </div>
  )
}

export default SortByField
