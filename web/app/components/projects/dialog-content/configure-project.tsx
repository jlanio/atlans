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
  /** Atualização otimista na lista do pai (nome e descrição), antes do PUT. */
  onSaved: (workflow: IWorkflow) => void
  /** Fecha o diálogo depois de o PUT dar certo. */
  onDone: () => void
}

// Recebe o workflow por prop, e não por um contexto de página: a lista vive
// no hook de dados de Projetos, e um segundo lugar guardando "os projetos"
// divergiria dela na primeira mutação otimista.
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

    // Só os campos que este formulário edita. O objeto espalhado acima serve ao
    // estado local; mandá-lo inteiro para a API reenviava campos que o cliente
    // não deve definir (workspace_id, created_by_id, timestamps) — e o backend
    // agora responde 422 a campo desconhecido (WorkflowUpdate usa extra="forbid").
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
