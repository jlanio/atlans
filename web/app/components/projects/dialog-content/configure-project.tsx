"use client"
import { Button } from "../../ui/button"
import { DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../ui/dialog"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "../../ui/form"
import { useForm } from "react-hook-form"
import { formConfigureProjectSchema } from "./form-configure-project"
import { zodResolver } from "@hookform/resolvers/zod"
import z from "zod"
import { Input } from "../../ui/input"
import { Textarea } from "../../ui/textarea"
import { GisFlowService } from "@/service/GisFlowService"
import { createToast } from "@/utils/createToast"
import type { IWorkflow } from "@/service/types"

interface ConfigureProjectProps {
  workflow: IWorkflow
  /** Optimistic update in the parent's list (name and description), before the PUT. */
  onSaved: (workflow: IWorkflow) => void
  /** Closes the dialog after the PUT succeeds. */
  onDone: () => void
}

// Takes the workflow by prop, not through a page context: the list lives
// in the Projects data hook, and a second place holding "the projects"
// would diverge from it on the first optimistic mutation.
const ConfigureProject = ({ workflow, onSaved, onDone }: ConfigureProjectProps) => {
  const form = useForm<z.infer<typeof formConfigureProjectSchema>>({
    resolver: zodResolver(formConfigureProjectSchema),
    defaultValues: {
      name: workflow.name,
      description: workflow.description ?? "",
    },
  })

  async function onSubmit(data: z.infer<typeof formConfigureProjectSchema>) {
    onSaved({
      ...workflow,
      name: data.name,
      description: data.description ?? "",
    })

    // Only the fields this form edits. The object spread above serves the
    // local state; sending it whole to the API resent fields the client
    // must not set (workspace_id, created_by_id, timestamps) — and the backend
    // now answers 422 to an unknown field (WorkflowUpdate uses extra="forbid").
    const respFlow = await GisFlowService.updateWorkflowById(workflow.id_hash, {
      name: data.name,
      description: data.description ?? "",
    })

    if (respFlow?.error)
      return createToast.error("Erro ao atualizar workflow!", respFlow?.error.message)

    onDone()
  }

  return (
    <DialogContent>
      <DialogHeader>
        <DialogTitle>Configurar projeto &quot;{workflow.name}&quot;</DialogTitle>
        <DialogDescription>
          Altere as configurações do seu projeto.
        </DialogDescription>
      </DialogHeader>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-3">
          <FormField
            control={form.control}
            name="name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Nome do projeto</FormLabel>
                <FormControl>
                  <Input placeholder="Insira o nome do projeto" {...field} />
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
                  <Textarea placeholder="Insira a descrição do projeto" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <DialogFooter className="mt-2">
            <DialogClose asChild>
              <Button type="button" variant="outline">Cancelar</Button>
            </DialogClose>
            <Button type="submit">Salvar</Button>
          </DialogFooter>
        </form>
      </Form>
    </DialogContent>
  )
}

export default ConfigureProject
