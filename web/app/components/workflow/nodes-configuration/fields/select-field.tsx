import { FieldLabel } from "./field-label"
import type { FieldProps } from "./types"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/app/components/ui/select"

type SelectFieldProps = FieldProps

const SelectField = ({ field, values, setNodeField }: SelectFieldProps) => {
  const current = (values?.[field.name] as string) || (field.default as string) || ""

  return (
    <div>
      <FieldLabel field={field} />
      <Select
        value={current}
        onValueChange={value => setNodeField(field.name, value)}
      >
        <SelectTrigger id={field.name} className="mt-1">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {(field.options || []).map(opt => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

export default SelectField
