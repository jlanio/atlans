import { Button } from "../../ui/button"
import { DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../ui/dialog"
import { Dispatch, SetStateAction, useEffect, useState } from "react"
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
import SchemaFieldsInput from "./inputs/schema-fields-input"
import PropsInput from "./inputs/props-input"
import MetaInputs from "./inputs/meta-inputs"
import { ICredentialTypeSchema } from "@/service/types"
import { TbAlertTriangle, TbLoader2, TbPlugConnected } from "react-icons/tb"
import { TestResultBanner, type TestResult } from "./test-result-banner"
import { Skeleton } from "../../ui/skeleton"

interface ConfigureCredentialProps {
  configureCredentialId: string | undefined
  setConfigureCredentialId: Dispatch<SetStateAction<string | undefined>>
}

const ConfigureCredential = ({ configureCredentialId, setConfigureCredentialId }: ConfigureCredentialProps) => {

  const { credentials, setCredentialsContext } = useCredentialsContext()
  const credentialFound = credentials.find(credential => credential.id === configureCredentialId)

  const [credentialTypes, setCredentialTypes] = useState<ICredentialTypeSchema[]>([])
  const [typesLoaded, setTypesLoaded] = useState(false)
  const [typesError, setTypesError] = useState(false)
  const [isTesting, setIsTesting] = useState(false)
  const [testResult, setTestResult] = useState<TestResult | null>(null)
  // Estado do carregamento dos segredos. Enquanto não terminar, o formulário
  // fica bloqueado — ver o comentário do efeito abaixo, é o ponto mais delicado
  // deste modal.
  const [secretsState, setSecretsState] = useState<"loading" | "ready" | "error">("loading")

  const form = useForm<z.infer<typeof formCredentialSchema>>({
    resolver: zodResolver(formCredentialSchema),
    defaultValues: {
      name: credentialFound?.name ?? "",
      type: credentialFound?.type ?? "",
      data: {},
      description: credentialFound?.description ?? "",
      tags: credentialFound?.tags ?? [],
      workspace_id: credentialFound?.workspace_id ?? null,
    },
  })

  useEffect(() => {
    GisFlowService.getCredentialTypes().then(res => {
      if (res?.data) {
        setCredentialTypes(res.data)
      } else {
        // Sem o catálogo não há schema, então o formulário cai no editor livre —
        // com os valores mascarados, sem rótulos de campo e sem explicação. Avisar
        // é o mínimo; o create-credential já fazia isso e este ficou sem.
        setTypesError(true)
      }
      setTypesLoaded(true)
    })
  }, [])

  // Busca os dados descriptografados para pré-popular o formulário de edição.
  //
  // PERIGO que este bloqueio evita: o backend faz `self.data = {...}` no
  // encrypt_and_store — SUBSTITUI o blob inteiro, sem merge. E só pula a
  // re-encriptação quando `data` é vazio (`if update_data.data:`). Então um
  // `data` PARCIAL é o caso destrutivo: se esta busca falhasse (ou o usuário
  // digitasse antes de ela voltar) e ele salvasse, todos os outros segredos
  // seriam apagados — e `_build_postgres_dsn` preenche o que falta com defaults,
  // produzindo `postgresql://:@localhost:5432/`. Uma credencial plausível e
  // quebrada, que só falha na execução do workflow.
  //
  // Por isso: campos desabilitados até `ready`, e em `error` o Salvar fica
  // bloqueado em vez de gravar por cima.
  useEffect(() => {
    if (!configureCredentialId) return
    let ativo = true
    setSecretsState("loading")
    GisFlowService.getCredentialData(configureCredentialId).then(res => {
      if (!ativo) return
      if (res?.data) {
        form.reset({
          name: res.data.name,
          type: res.data.type,
          data: res.data.data ?? {},
          description: res.data.description ?? "",
          tags: res.data.tags ?? [],
          workspace_id: res.data.workspace_id ?? null,
        })
        setSecretsState("ready")
      } else {
        setSecretsState("error")
      }
    })
    return () => { ativo = false }
  }, [configureCredentialId, form])

  const selectedType = form.watch("type")
  const activeSchema = credentialTypes.find(t => t.type === selectedType)

  // Resultado do teste envelhece a cada mudança de campo — neste modal não havia
  // reset nenhum, então testar e depois trocar a senha deixava o verde na tela.
  // A dependência é o valor serializado, não o objeto: `form.watch` pode devolver
  // referência nova por render, e aí o resultado seria limpo no render seguinte
  // ao próprio teste.
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
    // O guard antigo (`!credentialFound`) falhava em silêncio: clicar em Salvar
    // simplesmente não fazia nada se a credencial não estivesse no contexto.
    if (!configureCredentialId) return
    if (secretsState !== "ready") {
      return createToast.error(
        "Não é possível salvar",
        "Os dados da credencial não foram carregados. Feche e abra o modal novamente.",
      )
    }

    // Envia só o que o backend aceita (name/type/data). O `{...credentialFound}`
    // anterior arrastava id/expires_at no PUT e, pior, injetava `data` — segredos
    // em claro — nos objetos da listagem, que é tipada sem esse campo.
    const respCred = await GisFlowService.updateCredential(configureCredentialId, data)

    if (respCred?.error)
      return createToast.error("Erro ao atualizar credencial!", respCred?.error.message)

    // Atualiza a lista DEPOIS da resposta. Antes era otimista e sem rollback:
    // em erro saía o toast e a listagem seguia exibindo o valor que o backend
    // recusou.
    setCredentialsContext(prev => ({
      ...prev,
      credentials: prev.credentials.map(credential =>
        credential.id === configureCredentialId
          ? { ...credential, name: data.name, type: data.type }
          : credential
      )
    }))

    // O canvas guarda a lista de credenciais em memória por 5 min; sem invalidar,
    // o nó continuaria mostrando o nome antigo da credencial até o TTL vencer.
    useWorkflowCatalogStore.getState().invalidarCredenciais()

    createToast.success("Credencial atualizada", data.name)
    setConfigureCredentialId(undefined)
  }

  const { isSubmitting } = form.formState
  const camposBloqueados = secretsState !== "ready" || isSubmitting
  const canTest = !!selectedType && Object.keys(dataFields ?? {}).length > 0 && secretsState === "ready"

  return (
    <DialogContent
      bloqueado={isSubmitting}
    >
      <DialogHeader>
        {/* `pr-8` e `break-words`: o nome vem do usuário, e um nome longo
            passava por baixo do X de fechar — ou vazava a lateral no telefone,
            onde o diálogo tem 328px. */}
        <DialogTitle className="pr-8 break-words">Configurar credencial «{credentialFound?.name}»</DialogTitle>
        <DialogDescription>
          Altere as configurações da sua credencial.
        </DialogDescription>
      </DialogHeader>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-3">

          {typesError && (
            <p role="alert" className="rounded border border-destructive/20 bg-destructive/5 px-2 py-1.5 text-xs text-destructive">
              Não foi possível carregar os tipos de credencial. Os campos aparecem
              como pares chave/valor genéricos. Feche e abra o modal para tentar de novo.
            </p>
          )}

          {secretsState === "error" && (
            <p role="alert" className="flex items-start gap-1.5 rounded border border-destructive/20 bg-destructive/5 px-2 py-1.5 text-xs text-destructive">
              <TbAlertTriangle className="mt-px size-3.5 shrink-0" aria-hidden="true" />
              <span className="min-w-0">
                Não foi possível carregar os dados desta credencial. Salvar está bloqueado
                para não sobrescrever os valores existentes. Feche e abra o modal novamente.
              </span>
            </p>
          )}

          <NameInput form={form} />

          <TypeInput form={form} credentialTypes={credentialTypes} disabled />

          {/* Campos guiados pelo schema ou editor livre como fallback.
              `typesLoaded` no gate evita o piscar: o tipo já vem preenchido nos
              defaults, então antes do catálogo chegar `activeSchema` era undefined
              e caía no PropsInput — que renderiza os valores SEM type="password",
              expondo os segredos em texto claro por um instante. */}
          {secretsState === "loading" || !typesLoaded ? (
            <div className="flex flex-col gap-2" aria-busy="true">
              <Skeleton className="h-9 w-full rounded-md" />
              <Skeleton className="h-9 w-full rounded-md" />
              <Skeleton className="h-9 w-2/3 rounded-md" />
              <span className="sr-only">Carregando dados da credencial…</span>
            </div>
          ) : activeSchema ? (
            <SchemaFieldsInput form={form} schema={activeSchema} disabled={camposBloqueados} />
          ) : selectedType ? (
            <PropsInput form={form} />
          ) : null}

          {/* Metadados opcionais — só depois que os segredos carregam, e
              bloqueados junto com o resto enquanto isso. */}
          {secretsState === "ready" && <MetaInputs form={form} disabled={camposBloqueados} />}

          <TestResultBanner result={testResult} />

          <DialogFooter className="mt-2 flex-wrap gap-2">
            <DialogClose asChild>
              <Button type="button" variant="outline" disabled={isSubmitting} className="max-md:h-10">Cancelar</Button>
            </DialogClose>
            <Button
              type="button"
              variant="secondary"
              onClick={handleTest}
              disabled={isTesting || camposBloqueados || !canTest}
              title={canTest ? undefined : "Preencha os campos da credencial para testar"}
              aria-busy={isTesting}
              className="gap-1 max-md:h-10"
            >
              {isTesting
                ? <TbLoader2 className="size-4 motion-safe:animate-spin" aria-hidden="true" />
                : <TbPlugConnected className="size-4" aria-hidden="true" />}
              {isTesting ? "Testando…" : "Testar credencial"}
            </Button>
            <Button type="submit" disabled={camposBloqueados} className="gap-1 max-md:h-10">
              {isSubmitting && <TbLoader2 className="size-4 motion-safe:animate-spin" aria-hidden="true" />}
              {isSubmitting ? "Salvando…" : "Salvar"}
            </Button>
          </DialogFooter>

        </form>
      </Form>

    </DialogContent>
  )
}

export default ConfigureCredential
