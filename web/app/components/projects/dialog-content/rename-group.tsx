import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { useState } from "react"
import z from "zod"

import { formCreateGroupSchema } from "./form-create-group"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/app/components/ui/form"
import { DialogClose, DialogFooter } from "@/app/components/ui/dialog"
import { Textarea } from "@/app/components/ui/textarea"
import { Input } from "@/app/components/ui/input"
import { Button } from "@/app/components/ui/button"
import { IWorkflowGroup } from "@/service/types"

interface RenameGroupProps {
  group: IWorkflowGroup
  onSubmit: (name: string, description: string | null) => Promise<void>
  onDone: () => void
}

/**
 * Renomear grupo e editar a descrição.
 *
 * O `PUT /workflow-groups/{id}` existe desde sempre e a tela nunca o usou: dava
 * para criar e excluir, e um nome errado só se corrigia recriando o grupo e
 * movendo tudo de novo.
 *
 * Mesmo schema do formulário de criação — os campos são os mesmos, e duas
 * validações separadas divergiriam na primeira mudança.
 */
const RenameGroup = ({ group, onSubmit, onDone }: RenameGroupProps) => {
  const [loading, setLoading] = useState(false)

  const form = useForm<z.infer<typeof formCreateGroupSchema>>({
    resolver: zodResolver(formCreateGroupSchema),
    defaultValues: {
      name: group.name,
      description: group.description ?? null,
      workflowId: [],
    },
  })

  async function submeter(data: z.infer<typeof formCreateGroupSchema>) {
    setLoading(true)
    await onSubmit(data.name, data.description ?? null)
    setLoading(false)
    onDone()
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(submeter)} className="flex flex-col gap-2">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Nome do grupo</FormLabel>
              <FormControl>
                <Input placeholder="Insira o nome do grupo" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Descrição</FormLabel>
              <FormControl>
                <Textarea
                  {...field}
                  placeholder="Para que serve este grupo"
                  value={field.value ?? ""}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <DialogFooter className="mt-2">
          <DialogClose asChild>
            <Button type="button" variant="outline">Cancelar</Button>
          </DialogClose>
          <Button type="submit" disabled={loading}>
            {loading ? "Salvando..." : "Salvar"}
          </Button>
        </DialogFooter>
      </form>
    </Form>
  )
}

export default RenameGroup
