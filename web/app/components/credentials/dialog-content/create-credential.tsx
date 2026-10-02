import { Button } from "../../ui/button"
import { DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../ui/dialog"
import { Dispatch, SetStateAction, useEffect, useRef, useState } from "react"
import { Form } from "../../ui/form"
import { useForm } from "react-hook-form"
import { formCredentialSchema } from "./form-credential"
import { zodResolver } from "@hookform/resolvers/zod"
import z from "zod"
import { GisFlowService } from "@/service/GisFlowService"
import { createToast } from "@/utils/createToast"
import { useCredentialsContext } from "@/context/useCredentialsContext"
import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore"
import NameInput from "./inputs/name-input"
import TypeInput from "./inputs/type-input"
import PropsInput from "./inputs/props-input"
import SchemaFieldsInput from "./inputs/schema-fields-input"
import MetaInputs from "./inputs/meta-inputs"
import { ICredentialTypeSchema } from "@/service/types"
import { TbLoader2, TbPlugConnected } from "react-icons/tb"
import { TestResultBanner, type TestResult } from "./test-result-banner"

interface CreateCredentialProps {
  setCreateModalState: Dispatch<SetStateAction<boolean>>
  /** Quando fornecido, restringe os tipos compatíveis com o nó em uso */
  allowedTypes?: string[]
  /** Tipo pré-selecionado (ex: ao abrir inline de um nó específico) */
  defaultType?: string
  /**
   * Valores iniciais para pré-preencher o formulário — usado ao DUPLICAR uma
   * credencial. O chamador força remontagem via `key` quando isto muda, então
   * ler no defaultValues (uma vez) basta.
   */
  initialValues?: {
    name?: string
    type?: string
    data?: Record<string, string>
    description?: string
    tags?: string[]
  }
}

const CreateCredential = ({ setCreateModalState, allowedTypes, defaultType, initialValues }: CreateCredentialProps) => {

  // Acesso OPCIONAL de propósito: este modal também é montado dentro do canvas
  // de workflow (nodes-configuration/fields/credential-field.tsx), onde não há
  // CredentialsContextProvider. Desestruturar direto aqui quebra esse caminho —
  // e nenhum teste pega, porque o modal é mockado como () => null.
  const credCtx = useCredentialsContext()
  const [credentialTypes, setCredentialTypes] = useState<ICredentialTypeSchema[]>([])
  const [typesError, setTypesError] = useState(false)
  const [isTesting, setIsTesting] = useState(false)
  const [testResult, setTestResult] = useState<TestResult | null>(null)

  useEffect(() => {
    // Sem tratamento de erro o Select de tipo ficava vazio sem explicação
    // nenhuma. O caminho equivalente no canvas já avisava com toast.
    GisFlowService.getCredentialTypes().then(res => {
      if (res?.data) {
        setCredentialTypes(res.data)
        setTypesError(false)
      } else {
        setTypesError(true)
      }
    })
  }, [])

  const form = useForm<z.infer<typeof formCredentialSchema>>({
    resolver: zodResolver(formCredentialSchema),
    defaultValues: {
      name: initialValues?.name ?? "",
      type: initialValues?.type ?? defaultType ?? "",
      data: initialValues?.data ?? {},
      description: initialValues?.description ?? "",
      tags: initialValues?.tags ?? [],
      workspace_id: undefined,
    },
  })

  const selectedType = form.watch("type")
  const activeSchema = credentialTypes.find(t => t.type === selectedType)

  // Reinicia dados ao trocar de tipo para evitar campos órfãos.
  //
  // O tipo anterior precisa vir de um ref. Antes era
  // `const previousType = form.getValues("type")` no corpo do componente —
  // recalculado a CADA render, então quando o efeito rodava o valor já era o
  // novo e `previousType !== selectedType` nunca era verdadeiro. O efeito era
  // código morto: os campos do tipo antigo seguiam em `data` e iam para a API, e
  // um "conexão OK" de outro tipo continuava na tela.
  const previousTypeRef = useRef(selectedType)
  useEffect(() => {
    if (previousTypeRef.current !== selectedType) {
      previousTypeRef.current = selectedType
      form.setValue("data", {})
      setTestResult(null)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedType])

  // O resultado do teste envelhece assim que qualquer campo muda: sem isto um
  // "conexão bem-sucedida" continuava verde depois de o usuário trocar a senha.
  //
  // A dependência é o valor SERIALIZADO, não o objeto: `form.watch` pode
  // devolver referência nova a cada render, e aí o efeito limparia o resultado
  // no render seguinte ao próprio teste — nunca daria tempo de lê-lo.
  const dataFields = form.watch("data")
  const dataSignature = JSON.stringify(dataFields ?? {})
  useEffect(() => {
    setTestResult(null)
  }, [dataSignature])

  async function handleTest() {
    const { type, data } = form.getValues()
    setIsTesting(true)
    setTestResult(null)
    const res = await GisFlowService.testCredential({ type, data })
    setIsTesting(false)
    if (res?.data) {
      setTestResult(res.data)
    } else if (res?.error) {
      setTestResult({ ok: false, message: res.error.message ?? "Erro ao testar credencial" })
    }
  }

  async function onSubmit(data: z.infer<typeof formCredentialSchema>) {
    const respCred = await GisFlowService.createCredential(data)

    if (respCred?.error)
      return createToast.error("Erro ao criar credencial!", respCred?.error.message)

    // `data` podia ser undefined num 200 sem corpo, e o concat inseria um item
    // undefined na lista. Só propaga quando há objeto de verdade.
    if (credCtx?.setCredentialsContext && respCred.data) {
      const criada = respCred.data
      credCtx.setCredentialsContext(prev => ({
        ...prev,
        credentials: prev.credentials.concat(criada)
      }))
    }

    // O canvas lê as credenciais do catálogo em memória, com TTL de 5 min.
    // Sem invalidar aqui, a credencial recém-criada em /credentials não aparecia
    // no select do nó até o TTL vencer.
    useWorkflowCatalogStore.getState().invalidarCredenciais()

    createToast.success("Credencial criada", data.name)
    form.reset()
    setCreateModalState(false)
  }

  // `isSubmitting` do react-hook-form: não era usado em nenhum lugar do repo, e
  // sem ele um duplo clique em "Criar" criava duas credenciais.
  const { isSubmitting } = form.formState
  const canTest = !!selectedType && Object.keys(dataFields ?? {}).length > 0

  return (
    <DialogContent
      // Fechar no meio do submit desmonta o componente durante o await e deixa o
      // usuário sem saber se a credencial foi criada. As três saídas precisam ser
      // cobertas — bloquear só Esc e clique-fora deixa o X como escape.
      bloqueado={isSubmitting}
    >
      <DialogHeader>
        <DialogTitle>Criar credencial</DialogTitle>
        <DialogDescription>
          Preencha os campos abaixo para criar uma credencial reutilizável nos nós do seu workflow.
        </DialogDescription>
      </DialogHeader>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-3">

          {typesError && (
            <p role="alert" className="rounded border border-destructive/20 bg-destructive/5 px-2 py-1.5 text-xs text-destructive">
              Não foi possível carregar os tipos de credencial. Feche e abra o modal para tentar de novo.
            </p>
          )}

          <NameInput form={form} />

          <TypeInput
            form={form}
            credentialTypes={credentialTypes}
            allowedTypes={allowedTypes}
          />

          {/* Campos guiados pelo schema ou editor livre como fallback */}
          {activeSchema ? (
            <SchemaFieldsInput form={form} schema={activeSchema} />
          ) : selectedType ? (
            <PropsInput form={form} />
          ) : null}

          {/* Metadados opcionais (descrição, tags, expiração, compartilhamento)
              só aparecem depois que um tipo foi escolhido — antes disso o modal
              é só nome + tipo. */}
          {selectedType && <MetaInputs form={form} />}

          <TestResultBanner result={testResult} />

          <DialogFooter className="mt-2 flex-wrap gap-2">
            <DialogClose asChild>
              <Button type="button" variant="outline" disabled={isSubmitting} className="max-md:h-10">Cancelar</Button>
            </DialogClose>
            {/* Sempre renderizado, desabilitado quando não há o que testar: antes
                ele aparecia e desaparecia conforme os campos eram preenchidos,
                deslocando os outros botões no meio da digitação e entrando/saindo
                da ordem de tabulação.
                Rótulo "Testar credencial", não "Testar conexão": o backend só
                conecta de fato em postgresql/mysql/s3 — nos outros tipos ele
                apenas valida os campos, e o botão prometia mais do que entregava. */}
            <Button
              type="button"
              variant="secondary"
              onClick={handleTest}
              disabled={isTesting || isSubmitting || !canTest}
              title={canTest ? undefined : "Preencha os campos da credencial para testar"}
              aria-busy={isTesting}
              className="gap-1 max-md:h-10"
            >
              {isTesting
                ? <TbLoader2 className="size-4 motion-safe:animate-spin" aria-hidden="true" />
                : <TbPlugConnected className="size-4" aria-hidden="true" />}
              {isTesting ? "Testando…" : "Testar credencial"}
            </Button>
            <Button type="submit" disabled={isSubmitting} className="gap-1 max-md:h-10">
              {isSubmitting && <TbLoader2 className="size-4 motion-safe:animate-spin" aria-hidden="true" />}
              {isSubmitting ? "Criando…" : "Criar"}
            </Button>
          </DialogFooter>

        </form>
      </Form>

    </DialogContent>
  )
}

export default CreateCredential
