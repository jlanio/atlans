import { UseFormReturn } from "react-hook-form"
import z from "zod"
import { formCredentialSchema } from "../form-credential"
import { FormField, FormItem, FormLabel, FormMessage } from "@/app/components/ui/form"
import { useState } from "react"
import { Input } from "@/app/components/ui/input"
import { Label } from "@/app/components/ui/label"
import { FaEye, FaEyeSlash, FaTrash } from "react-icons/fa"
import { createToast } from "@/utils/createToast"
import { Button } from "@/app/components/ui/button"

interface PropsInputProps {
  form: UseFormReturn<z.infer<typeof formCredentialSchema>>
}

const initialValue = {
  key: "",
  value: ""
}

const PropsInput = ({ form }: PropsInputProps) => {

  const currentData = form.watch("data")
  const props = Object.entries(currentData ?? {})
  const [createProps, setCreateProp] = useState<{ key: string, value: string }>(initialValue)
  // The values are masked (they are secrets like any others), so there has to
  // be a way to check them — otherwise editing a credential of this type is done
  // blind. Same mechanism as SchemaFieldsInput.
  const [revealed, setRevealed] = useState<Record<string, boolean>>({})

  function updateProp(index: number, newValue: string) {
    const entries = [...props]
    const [k] = entries[index]
    form.setValue("data", {
      ...currentData,
      [k]: newValue
    })
  }

  function createNewProp() {

    if (createProps.key === "" || createProps.value === "")
      return

    if (createProps.key in (currentData ?? {})) {
      createToast.error("A chave já existe", `A chave '${createProps.key}' já foi adicionada`)
      return setCreateProp(initialValue)
    }

    form.setValue("data", {
      ...currentData,
      [createProps.key]: createProps.value
    })

    setCreateProp(initialValue)

  }

  function deleteProp(keyToDelete: string) {
    const newData = { ...currentData }
    delete newData[keyToDelete]
    form.setValue("data", newData)
  }

  return (
    <FormField
      control={form.control}
      name="data"
      render={() => (
        <FormItem className="w-full">

          <FormLabel>Props</FormLabel>

          <div>
            {/* Only exists when the row HAS two columns: on the phone it
                stacks (below), and the key field already comes filled in. */}
            <div className="hidden sm:grid grid-cols-2 gap-2 mb-1 mr-6">
              <Label className="text-xs">Chave</Label>
              <Label className="text-xs">Valor</Label>
            </div>

            <div className="flex flex-col gap-2">
              {props.map(([key, value], index) =>
                // Key, value and two icon buttons on the same row left
                // ~90px per field on a 360px phone — and under a coarse pointer
                // the input uses a 16px font, so five characters fit. The
                // `sm:contents` of the block below restores the desktop's
                // single row, without duplicated markup.
                <div key={key} className="flex flex-col gap-2 sm:flex-row sm:items-center">
                  <Input
                    disabled
                    aria-label={`Chave ${key}`}
                    value={key} />
                  <div className="flex items-center gap-2 sm:contents">
                    {/* type="password": this free editor is the fallback used when
                        the type has no known schema, and the values here are
                        secrets like any other. They were in plain text on screen. */}
                    <Input
                      type={revealed[key] ? "text" : "password"}
                      autoComplete="new-password"
                      aria-label={`Valor de ${key}`}
                      onChange={e => updateProp(index, e.target.value)}
                      value={value} />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="size-9 shrink-0"
                      onClick={() => setRevealed(prev => ({ ...prev, [key]: !prev[key] }))}
                      aria-label={revealed[key] ? `Ocultar valor de ${key}` : `Mostrar valor de ${key}`}
                      aria-pressed={!!revealed[key]}
                      title={revealed[key] ? "Ocultar" : "Mostrar"}
                    >
                      {revealed[key]
                        ? <FaEyeSlash className="size-4" aria-hidden="true" />
                        : <FaEye className="size-4" aria-hidden="true" />}
                    </Button>
                    {/* It was a <FaTrash onClick>: an SVG with a click is not focusable,
                        has no label and does not respond to the keyboard — a
                        destructive action unreachable without a mouse. */}
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="size-9 shrink-0 text-accent-foreground hover:text-destructive"
                      onClick={() => deleteProp(key)}
                      aria-label={`Remover a propriedade ${key}`}
                      title="Remover"
                    >
                      <FaTrash className="size-3.5" aria-hidden="true" />
                    </Button>
                  </div>
                </div>
              )}
            </div>

            {/* No ceiling of 3 pairs: the old limit prevented representing
                free-type credentials with more fields (the fallback exists
                precisely for types outside the catalog, which may have as many
                fields as they need). */}
            <div className="flex flex-col gap-2 mt-2 sm:flex-row sm:items-center sm:mr-[20px]">
              <Input
                placeholder="Insira uma chave"
                onBlur={createNewProp}
                onChange={e => setCreateProp(prev => ({
                  ...prev,
                  key: e.target.value
                }))}
                value={createProps.key ?? ""}
              />
              <Input
                placeholder="Insira um valor"
                onBlur={createNewProp}
                onChange={e => setCreateProp(prev => ({
                  ...prev,
                  value: e.target.value
                }))}
                value={createProps.value ?? ""}
              />
            </div>
          </div>

          <FormMessage />
        </FormItem>
      )}
    />
  )
}

export default PropsInput