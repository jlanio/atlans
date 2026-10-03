import { UseFormReturn } from "react-hook-form"
import z from "zod"
import { formCredentialSchema } from "../form-credential"
import { FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/app/components/ui/form"
import { FormControl } from "@/app/components/ui/form"
import { Input } from "@/app/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/app/components/ui/select"
import { ICredentialFieldSchema, ICredentialTypeSchema } from "@/service/types"
import { useState } from "react"
import { FaEye, FaEyeSlash } from "react-icons/fa"
import { Button } from "@/app/components/ui/button"

interface SchemaFieldsInputProps {
  form: UseFormReturn<z.infer<typeof formCredentialSchema>>
  schema: ICredentialTypeSchema
  /** Locks the fields — used in the edit modal while the secrets load. */
  disabled?: boolean
}

const SchemaFieldsInput = ({ form, schema, disabled }: SchemaFieldsInputProps) => {
  const [revealed, setRevealed] = useState<Record<string, boolean>>({})

  function toggleReveal(key: string) {
    setRevealed(prev => ({ ...prev, [key]: !prev[key] }))
  }

  return (
    <div className="flex flex-col gap-3">
      {schema.fields
        // `expires_at` is handled by the modal's universal ExpiryInput (with a
        // date picker and time-zone conversion), not as a schema text field —
        // otherwise it would appear twice in the types that declare it.
        .filter(field => field.key !== "expires_at")
        .map(field => (
          <SchemaField
            key={field.key}
            field={field}
            form={form}
            disabled={disabled}
            revealed={!!revealed[field.key]}
            onToggleReveal={() => toggleReveal(field.key)}
          />
        ))}
    </div>
  )
}

interface SchemaFieldProps {
  field: ICredentialFieldSchema
  form: UseFormReturn<z.infer<typeof formCredentialSchema>>
  revealed: boolean
  onToggleReveal: () => void
  disabled?: boolean
}

const SchemaField = ({ field, form, revealed, onToggleReveal, disabled }: SchemaFieldProps) => {
  const isPassword = field.type === "password"
  const isSelect = field.type === "select"
  const isNumber = field.type === "number"

  const currentData = form.watch("data")

  function handleChange(value: string) {
    form.setValue("data", { ...currentData, [field.key]: value })
  }

  const currentValue = currentData?.[field.key] ?? field.default ?? ""

  return (
    <FormField
      control={form.control}
      name="data"
      render={() => (
        <FormItem className="w-full">
          <FormLabel>
            {field.label}
            {!field.required && (
              <span className="ml-1 text-xs text-muted-foreground">(opcional)</span>
            )}
          </FormLabel>

          {/* FormControl has to wrap the control ITSELF, not a wrapper.
              Before, it wrapped the group's <div> (and, in the select case, Radix's
              Root, which renders no DOM): `id`, `aria-describedby` and
              `aria-invalid` landed on the div, and FormLabel's `htmlFor` pointed
              to an element that was not the input. Result: clicking the label did
              not focus the field and the field had no accessible name.
              `formItemId` is unique per FormItem (its own useId), so this
              works even with all fields sharing name="data". */}
          {isSelect ? (
            <Select value={currentValue} onValueChange={handleChange} disabled={disabled}>
              <FormControl>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder={`Selecione ${field.label}`} />
                </SelectTrigger>
              </FormControl>
              <SelectContent>
                {(field.options ?? []).map(opt => (
                  <SelectItem key={opt} value={opt}>{opt}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <div className="flex items-center gap-1">
              <FormControl>
                <Input
                  // A numeric field (e.g. port) gets type="number" + a numeric
                  // keyboard on mobile. A revealed password becomes "text";
                  // otherwise plain text.
                  type={isPassword && !revealed ? "password" : isNumber ? "number" : "text"}
                  inputMode={isNumber ? "numeric" : undefined}
                  placeholder={field.placeholder ?? ""}
                  value={currentValue}
                  onChange={e => handleChange(e.target.value)}
                  autoComplete={isPassword ? "new-password" : "off"}
                  disabled={disabled}
                />
              </FormControl>
              {isPassword && (
                // No tabIndex={-1}: the button was unreachable by keyboard, that is,
                // those who do not use a mouse could not check what they typed.
                // aria-pressed conveys the state; the label says what the action DOES.
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="size-9 shrink-0"
                  onClick={onToggleReveal}
                  disabled={disabled}
                  aria-label={revealed ? `Ocultar ${field.label}` : `Mostrar ${field.label}`}
                  aria-pressed={revealed}
                  title={revealed ? "Ocultar" : "Mostrar"}
                >
                  {revealed
                    ? <FaEyeSlash className="size-4" aria-hidden="true" />
                    : <FaEye className="size-4" aria-hidden="true" />}
                </Button>
              )}
            </div>
          )}

          {/* FormDescription, not a raw <p>: it is what carries the `formDescriptionId`
              already referenced in the aria-describedby built by FormControl. With
              a loose <p>, the ARIA reference pointed to a nonexistent id and the
              description was not read. */}
          {field.description && (
            <FormDescription className="text-xs">{field.description}</FormDescription>
          )}

          <FormMessage />
        </FormItem>
      )}
    />
  )
}

export default SchemaFieldsInput
