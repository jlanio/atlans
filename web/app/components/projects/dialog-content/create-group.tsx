import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import z from "zod"
import { formCreateGroupSchema } from "./form-create-group"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/app/components/ui/form"
import { DialogClose, DialogFooter } from "@/app/components/ui/dialog"
import { Textarea } from "@/app/components/ui/textarea"
import { Input } from "@/app/components/ui/input"
import { Button } from "@/app/components/ui/button"
import { GisFlowService } from "@/service/GisFlowService"
import { useWorkspace } from "@/context/WorkspaceContext"
import { IWorkflowGroup } from "@/service/types"
import { useState } from "react"
import { createToast } from "@/utils/createToast"

interface CreateGroupProps {
  onSuccess?: (group: IWorkflowGroup) => void
}

const CreateGroup = ({ onSuccess }: CreateGroupProps) => {

  const { current: currentWorkspace } = useWorkspace()
  const [loading, setLoading] = useState(false)

  const form = useForm<z.infer<typeof formCreateGroupSchema>>({
    resolver: zodResolver(formCreateGroupSchema),
    defaultValues: {
      name: "",
      description: null,
      workflowId: []
    },
  })

  async function onSubmit(data: z.infer<typeof formCreateGroupSchema>) {
    setLoading(true)
    const result = await GisFlowService.createWorkflowGroup({
      name: data.name,
      description: data.description,
      workspace_id: currentWorkspace?.id_hash,
      workflow_ids: data.workflowId,
    })
    setLoading(false)

    if (result?.error) {
      createToast.error("Erro ao criar grupo", result.error.message)
      return
    }

    if (result?.data) {
      createToast.success("Grupo criado!", `"${result.data.name}" criado com sucesso.`)
      form.reset()
      onSuccess?.(result.data)
    }
  }

  return (
    <div>
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-2" >
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
                <FormLabel>Descricao</FormLabel>
                <FormControl>
                  <Textarea
                    {...field}
                    placeholder="Insira a descricao do grupo"
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
              {loading ? "Criando..." : "Criar"}
            </Button>
          </DialogFooter>

        </form>

      </Form>
    </div>
  )
}

export default CreateGroup
