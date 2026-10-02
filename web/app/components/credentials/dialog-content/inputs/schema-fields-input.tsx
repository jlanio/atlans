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
  /** Bloqueia os campos — usado no modal de editar enquanto os segredos carregam. */
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
        // `expires_at` é tratado pelo ExpiryInput universal do modal (com
        // seletor de data e conversão de fuso), não como campo de texto do
        // schema — senão apareceria duplicado nos tipos que o declaram.
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

          {/* O FormControl precisa envolver o PRÓPRIO controle, não um wrapper.
              Antes ele envolvia a <div> do grupo (e, no caso select, o Root do
              Radix, que não renderiza DOM): `id`, `aria-describedby` e
              `aria-invalid` aterravam na div, e o `htmlFor` do FormLabel apontava
              para um elemento que não era o input. Resultado: clicar no rótulo não
              focava o campo e o campo não tinha nome acessível.
              O `formItemId` é único por FormItem (useId próprio), então isso
              funciona mesmo com todos os campos compartilhando name="data". */}
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
                  // Campo numérico (ex: porta) ganha type="number" + teclado
                  // numérico no celular. Password revelado vira "text"; senão
                  // texto comum.
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
                // Sem tabIndex={-1}: o botão era inalcançável por teclado, ou seja
                // quem não usa mouse não conseguia conferir o que digitou.
                // aria-pressed comunica o estado; o rótulo diz o que a ação FAZ.
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

          {/* FormDescription, não <p> cru: é ele que carrega o `formDescriptionId`
              já referenciado no aria-describedby montado pelo FormControl. Com o
              <p> solto, a referência ARIA apontava para um id inexistente e a
              descrição não era lida. */}
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
