"use client"

/**
 * Structured editor for the Switch node's `rules`.
 *
 * The field used to be a raw `object`: each rule was a dict typed by hand in a
 * JSON editor — `{"field":"uf","operator":"==","value":"MT","output":
 * "output_1"}` — with an operator and output easy to get wrong and no place
 * for the known columns. Here each rule is a field+operator+value+output row,
 * with selects for what is enumerable.
 *
 * The value persists as the SAME list of dicts that execute reads — a workflow
 * saved by the JSON editor opens here, and vice versa.
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

/** Mirrors `_OP_FUNCS` + the extras in switch.py — the backend is the source. */
export const SWITCH_OPERATORS = ["==", "!=", ">", "<", ">=", "<=", "contains", "starts", "ends"] as const

/** The outputs the Switch descriptor declares (outputs output_0..3).
 *  output_0 is the default/fallback output — rules normally point to 1..3. */
export const SWITCH_OUTPUTS = ["output_0", "output_1", "output_2", "output_3"] as const

/** Columns of the rules grid (header and rows): field, operator, value,
 *  output, remove. The fixed tracks fit the widest value in monospace —
 *  "contains" for the operator, "Saída padrão" for the output —, and the
 *  triggers fill the whole track (`w-full min-w-0`) instead of `w-fit`: a
 *  trigger that overflows its own track sits on top of the "Remover regra"
 *  (remove rule) button, and clicking the select's arrow deleted the rule. */
const RULE_COLUMNS = "grid-cols-[1fr_6.75rem_1fr_8.75rem_auto]"

export interface SwitchRule {
  field: string
  operator: string
  value: string
  /** "" = NO `output` in the rule: execute routes to the fallback
   *  (`rule.get("output", fallback)`). It isn't an invented state — a legacy
   *  definition without the key HAS that behavior, and normalizing it to
   *  "output_1" would change the routing on the first saved edit. */
  output: string
}

/** Reads the saved value, whether it comes as a list (ObjectField/definition) or a JSON string.
 *
 * `field`/`operator`/`value` get the SAME defaults as execute
 * (`rule.get("field","")`, `"=="`, `""`), so normalizing them doesn't change
 * behavior. `output` is the only one whose absence means something else
 * (fallback) — it stays "" and serialization omits the key. */
export function lerRegras(bruto: unknown): SwitchRule[] {
  let lista: unknown = bruto
  if (typeof bruto === "string" && bruto.trim().startsWith("[")) {
    try { lista = JSON.parse(bruto) } catch { lista = [] }
  }
  if (!Array.isArray(lista)) return []
  return lista
    .filter((r): r is Record<string, unknown> => !!r && typeof r === "object")
    .map(r => ({
      field: String(r.field ?? ""),
      operator: String(r.operator ?? "=="),
      value: String(r.value ?? ""),
      output: r.output != null ? String(r.output) : "",
    }))
}

/** What goes into the definition: the rule as execute reads it — without
 *  `output` when the rule routes to the fallback. */
export function serializarRegras(regras: SwitchRule[]): Record<string, string>[] {
  return regras.map(({ field, operator, value, output }) => ({
    field, operator, value,
    ...(output ? { output } : {}),
  }))
}

/** SelectItem value for the default output — Select doesn't accept an item with value "". */
const FALLBACK = "__fallback__"

type SwitchRulesFieldProps = FieldProps<{
  sugestoes?: string[]
  sugestoesDesatualizadas?: boolean
  sugestoesParciais?: boolean
}>

const SwitchRulesField = ({ field, values, setNodeField, sugestoes = [], sugestoesDesatualizadas = false, sugestoesParciais = false }: SwitchRulesFieldProps) => {
  const regras = lerRegras(values?.[field.name])

  // The REAL list, not a JSON string — same cast as SetFieldsHelper. Serializes
  // by execute's contract: a fallback rule goes WITHOUT the `output` key.
  const gravar = (next: SwitchRule[]) =>
    setNodeField(field.name, serializarRegras(next) as unknown as string)

  const editar = (idx: number, mudanca: Partial<SwitchRule>) =>
    gravar(regras.map((r, i) => (i === idx ? { ...r, ...mudanca } : r)))

  const newRule = (fieldName = ""): SwitchRule =>
    ({ field: fieldName, operator: "==", value: "", output: "output_1" })

  // Click on a suggestion: fills the first rule without a field or opens a
  // new one — never replaces what has already been typed. The SAME column can
  // govern several rules (uf == MT → 1, uf == GO → 2), so here the list isn't
  // filtered by what is already in use.
  function escolher(nome: string) {
    const vazia = regras.findIndex(r => r.field.trim() === "")
    if (vazia >= 0) editar(vazia, { field: nome })
    else gravar([...regras, newRule(nome)])
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <FieldLabel field={field} />
        <Button
          size="icon" variant="ghost" className="h-6 w-6"
          aria-label="Adicionar regra"
          onClick={() => gravar([...regras, newRule()])}
        >
          <TbPlus className="h-3.5 w-3.5" />
        </Button>
      </div>

      {regras.length === 0 ? (
        <p className="text-[11px] text-muted-foreground italic px-1">
          Nenhuma regra: tudo cai na saída padrão. Clique em + para adicionar.
        </p>
      ) : (
        <div className="flex flex-col gap-1.5">
          <div className={`grid ${RULE_COLUMNS} gap-1.5 px-1`}>
            <span className="text-[10px] font-medium text-muted-foreground">Campo</span>
            <span className="text-[10px] font-medium text-muted-foreground">Operador</span>
            <span className="text-[10px] font-medium text-muted-foreground">Valor</span>
            <span className="text-[10px] font-medium text-muted-foreground">Saída</span>
            <span />
          </div>

          {regras.map((regra, idx) => (
            <div key={idx} className={`grid ${RULE_COLUMNS} gap-1.5 items-center`}>
              <Input
                value={regra.field}
                placeholder="coluna"
                className="h-7 text-xs font-mono"
                onChange={e => editar(idx, { field: e.target.value })}
              />
              <Select value={regra.operator} onValueChange={v => editar(idx, { operator: v })}>
                <SelectTrigger className="h-7 w-full min-w-0 text-xs font-mono">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {/* Operator outside the vocabulary (hand-edited definition):
                      it becomes an item so the value shows and survives editing —
                      a mute Select would erase the choice on the first save. */}
                  {!SWITCH_OPERATORS.includes(regra.operator as never) && (
                    <SelectItem value={regra.operator} className="font-mono text-xs">{regra.operator}</SelectItem>
                  )}
                  {SWITCH_OPERATORS.map(op => (
                    <SelectItem key={op} value={op} className="font-mono text-xs">{op}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Input
                value={regra.value}
                placeholder="valor"
                className="h-7 text-xs font-mono"
                onChange={e => editar(idx, { value: e.target.value })}
              />
              <Select
                value={regra.output || FALLBACK}
                onValueChange={v => editar(idx, { output: v === FALLBACK ? "" : v })}
              >
                <SelectTrigger className="h-7 w-full min-w-0 text-xs font-mono">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {/* A rule without `output` routes to the default output AND ends
                      evaluation — it is a legitimate state of a legacy definition,
                      not a hole to fill. */}
                  <SelectItem value={FALLBACK} className="text-xs">Saída padrão</SelectItem>
                  {regra.output !== "" && !SWITCH_OUTPUTS.includes(regra.output as never) && (
                    <SelectItem value={regra.output} className="font-mono text-xs">{regra.output}</SelectItem>
                  )}
                  {SWITCH_OUTPUTS.map(saida => (
                    <SelectItem key={saida} value={saida} className="font-mono text-xs">{saida}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                size="icon" variant="ghost"
                className="h-7 w-7 text-muted-foreground hover:text-destructive"
                aria-label={`Remover regra ${idx + 1}`}
                onClick={() => gravar(regras.filter((_, i) => i !== idx))}
              >
                <TbTrash className="h-3.5 w-3.5" />
              </Button>
            </div>
          ))}
        </div>
      )}

      <ColumnSuggestions
        nomes={sugestoes}
        onEscolher={escolher}
        totalConhecido={sugestoes.length}
        desatualizadas={sugestoesDesatualizadas}
        parciais={sugestoesParciais}
      />
    </div>
  )
}

export default SwitchRulesField
