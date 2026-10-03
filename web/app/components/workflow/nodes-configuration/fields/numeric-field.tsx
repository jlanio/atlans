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
          const n = Number(e.target.value)
          setNodeField(field.name, isInt ? Math.round(n) : n)
        }}
        value={`${values?.[field.name] ?? ""}`}
      />
    </div>
  )
}

export default NumericField
