import { UseFormReturn } from "react-hook-form"
import z from "zod"
import { formCredentialSchema } from "../form-credential"
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/app/components/ui/form"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/app/components/ui/select"
import { ICredentialTypeSchema } from "@/service/types"

interface TypeInputProps {
  form: UseFormReturn<z.infer<typeof formCredentialSchema>>
  credentialTypes: ICredentialTypeSchema[]
  /** Restricts the selection to a single type (e.g. when creating inline from a specific node) */
  allowedTypes?: string[]
  /** When true, shows the type as read-only — it cannot be changed while editing */
  disabled?: boolean
}

const TypeInput = ({ form, credentialTypes, allowedTypes, disabled }: TypeInputProps) => {
  const options = allowedTypes
    ? credentialTypes.filter(t => allowedTypes.includes(t.type))
    : credentialTypes

  const currentType = form.watch("type")
  const currentLabel = credentialTypes.find(t => t.type === currentType)?.label ?? currentType

  if (disabled) {
    return (
      <div className="flex flex-col gap-1.5">
        <span className="text-sm font-medium">Tipo</span>
        <div className="flex items-center gap-2 h-9 rounded-md border border-input bg-muted/50 px-3 text-sm text-muted-foreground">
          {currentLabel}
        </div>
        <p className="text-xs text-muted-foreground">O tipo não pode ser alterado após a criação.</p>
      </div>
    )
  }

  return (
    <FormField
      control={form.control}
      name="type"
      render={({ field }) => (
        <FormItem className="w-full">
          <FormLabel>Tipo</FormLabel>
          <Select onValueChange={field.onChange} value={field.value}>
            <FormControl>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Selecione um tipo" />
              </SelectTrigger>
            </FormControl>
            <SelectContent>
              {options.map(t => (
                <SelectItem key={t.type} value={t.type}>
                  <div className="flex flex-col">
                    <span>{t.label}</span>
                    <span className="text-xs text-muted-foreground">{t.description}</span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <FormMessage />
        </FormItem>
      )}
    />
  )
}

export default TypeInput
