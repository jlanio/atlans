import { FieldLabel } from "./field-label"
import { Switch } from "@/app/components/ui/switch"
import type { FieldProps } from "./types"

type BooleanFieldProps = FieldProps

/**
 * A row, not a card.
 *
 * It was the ONLY field with `rounded-lg border p-3 shadow-sm` — all the others
 * are a bare label and control. In a mixed list the toggles became arbitrary
 * visual anchors: the frame suggested an importance the field doesn't have, and
 * "Publico" weighed more on screen than "Destino", which governs the whole node.
 */
const BooleanField = ({ field, values, setNodeField }: BooleanFieldProps) => (
  <div className="flex flex-row items-center justify-between gap-3">
    <FieldLabel field={field} />
    <Switch
      id={field.name}
      checked={values?.[field.name] as boolean}
      onCheckedChange={value => setNodeField(field.name, value)}
    />
  </div>
)

export default BooleanField
