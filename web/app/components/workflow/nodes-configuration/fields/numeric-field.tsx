import { FieldLabel } from "./field-label"
import { Input } from "@/app/components/ui/input"
import type { FieldProps } from "./types"

type NumericFieldProps = FieldProps<{
  /** "integer" arredonda + step=1; "number" aceita decimais. */
  variant?: "number" | "integer"
}>

/**
 * Unified numeric field (replaces number-field and integer-field).
 * The "integer" variant rounds in onChange and uses a visual step=1; "number"
 * lets the user type decimals freely.
 */
const NumericField = ({ field, values, setNodeField, variant = "number" }: NumericFieldProps) => {
  const isInt = variant === "integer"
  return (
    <div className="flex flex-col gap-1">
      <FieldLabel field={field} />
      <Input
        placeholder={field.placeholder}
        id={field.name}
        type="number"
        step={isInt ? 1 : undefined}
        onChange={e => {
          // An emptied input means "not filled in", not zero: `Number("")` is 0,
          // so clearing an optional field (limit, timeout, tolerance) stored a
          // silent 0 and the input snapped back to "0". It is stored as "" —
          // the executor's parameter validation reads "" in a numeric field as
          // "use the declared default" (flow/utils/parameter_validation.py),
          // which is also what the drawer seeds unset fields with. A browser
          // also reports "" while the typed text is not a number yet ("-" on
          // the way to "-5"), and "" leaves that text alone where 0 replaced it.
          if (e.target.value === "") {
            setNodeField(field.name, "")
            return
          }
          const n = Number(e.target.value)
          setNodeField(field.name, isInt ? Math.round(n) : n)
        }}
        value={`${values?.[field.name] ?? ""}`}
      />
    </div>
  )
}

export default NumericField
