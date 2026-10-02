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
  // Os valores são mascarados (são segredos como quaisquer outros), então precisa
  // haver como conferi-los — senão editar uma credencial deste tipo fica às
  // cegas. Mesmo mecanismo do SchemaFieldsInput.
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
            {/* Só existe quando a linha TEM duas colunas: no telefone ela
                empilha (abaixo), e o campo de chave já chega preenchido. */}
            <div className="hidden sm:grid grid-cols-2 gap-2 mb-1 mr-6">
              <Label className="text-xs">Chave</Label>
              <Label className="text-xs">Valor</Label>
            </div>

            <div className="flex flex-col gap-2">
              {props.map(([key, value], index) =>
                // Chave, valor e dois botões de ícone na mesma linha deixavam
                // ~90px por campo num telefone de 360px — e sob ponteiro grosso
                // o input usa 16px de fonte, então cabiam cinco caracteres. O
                // `sm:contents` do bloco de baixo devolve a linha única do
                // desktop, sem markup duplicado.
                <div key={key} className="flex flex-col gap-2 sm:flex-row sm:items-center">
                  <Input
                    disabled
                    aria-label={`Chave ${key}`}
                    value={key} />
                  <div className="flex items-center gap-2 sm:contents">
                    {/* type="password": este editor livre é o fallback usado quando
                        o tipo não tem schema conhecido, e os valores aqui são
                        segredos como qualquer outro. Estavam em texto claro na tela. */}
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
                    {/* Era um <FaTrash onClick>: SVG com clique não é focável, não
                        tem rótulo e não responde a teclado — ação destrutiva
                        inalcançável sem mouse. */}
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

            {/* Sem teto de 3 pares: o limite antigo impedia representar
                credenciais de tipo livre com mais campos (o fallback existe
                justamente para tipos fora do catálogo, que podem ter quantos
                campos precisarem). */}
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