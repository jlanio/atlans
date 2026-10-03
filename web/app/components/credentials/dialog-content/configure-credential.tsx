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
  // Loading state of the secrets. Until it finishes, the form stays locked —
  // see the comment on the effect below, it is the most delicate point of
  // this modal.
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
        // Without the catalog there is no schema, so the form falls back to the free
        // editor — with masked values, no field labels and no explanation. Warning
        // is the minimum; create-credential already did it and this one did not.
        setTypesError(true)
      }
      setTypesLoaded(true)
    })
  }, [])

  // Fetches the decrypted data to pre-populate the edit form.
  //
  // DANGER this lock prevents: the backend does `self.data = {...}` in
  // encrypt_and_store — it REPLACES the whole blob, without merging. And it only
  // skips re-encryption when `data` is empty (`if update_data.data:`). So a
  // PARTIAL `data` is the destructive case: if this fetch failed (or the user
  // typed before it came back) and they saved, all the other secrets would be
  // erased — and `_build_postgres_dsn` fills in what is missing with defaults,
  // producing `postgresql://:@localhost:5432/`. A plausible, broken credential
  // that only fails when the workflow runs.
  //
  // Hence: fields disabled until `ready`, and on `error` Save stays locked
  // instead of writing over it.
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

  // The test result goes stale on every field change — this modal had no reset
  // at all, so testing and then changing the password left the green on screen.
  // The dependency is the serialized value, not the object: `form.watch` may
  // return a new reference per render, and then the result would be cleared on
  // the render right after the test itself.
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
    // The old guard (`!credentialFound`) failed silently: clicking Save
    // simply did nothing if the credential was not in the context.
    if (!configureCredentialId) return
    if (secretsState !== "ready") {
      return createToast.error(
        "Não é possível salvar",
        "Os dados da credencial não foram carregados. Feche e abra o modal novamente.",
      )
    }

    // Sends only what the backend accepts (name/type/data). The previous
    // `{...credentialFound}` dragged id/expires_at into the PUT and, worse,
    // injected `data` — plaintext secrets — into the listing objects, which are
    // typed without that field.
    const respCred = await GisFlowService.updateCredential(configureCredentialId, data)

    if (respCred?.error)
      return createToast.error("Erro ao atualizar credencial!", respCred?.error.message)

    // Updates the list AFTER the response. Before it was optimistic with no
    // rollback: on error the toast came out and the listing kept showing the
    // value the backend refused.
    setCredentialsContext(prev => ({
      ...prev,
      credentials: prev.credentials.map(credential =>
        credential.id === configureCredentialId
          ? { ...credential, name: data.name, type: data.type }
          : credential
      )
    }))

    // The canvas keeps the credential list in memory for 5 min; without
    // invalidating, the node would keep showing the credential's old name until
    // the TTL expired.
    useWorkflowCatalogStore.getState().invalidarCredenciais()

    createToast.success("Credencial atualizada", data.name)
    setConfigureCredentialId(undefined)
  }

  const { isSubmitting } = form.formState
  const fieldsLocked = secretsState !== "ready" || isSubmitting
  const canTest = !!selectedType && Object.keys(dataFields ?? {}).length > 0 && secretsState === "ready"

  return (
    <DialogContent
      bloqueado={isSubmitting}
    >
      <DialogHeader>
        {/* `pr-8` and `break-words`: the name comes from the user, and a long name
            ran under the close X — or overflowed the side on the phone,
            where the dialog is 328px wide. */}
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

          {/* Schema-driven fields or the free editor as a fallback.
              `typesLoaded` in the gate avoids the flash: the type already comes
              filled in the defaults, so before the catalog arrived `activeSchema`
              was undefined and fell into PropsInput — which renders the values
              WITHOUT type="password", exposing the secrets in plain text for an
              instant. */}
          {secretsState === "loading" || !typesLoaded ? (
            <div className="flex flex-col gap-2" aria-busy="true">
              <Skeleton className="h-9 w-full rounded-md" />
              <Skeleton className="h-9 w-full rounded-md" />
              <Skeleton className="h-9 w-2/3 rounded-md" />
              <span className="sr-only">Carregando dados da credencial…</span>
            </div>
          ) : activeSchema ? (
            <SchemaFieldsInput form={form} schema={activeSchema} disabled={fieldsLocked} />
          ) : selectedType ? (
            <PropsInput form={form} />
          ) : null}

          {/* Optional metadata — only after the secrets load, and locked along
              with the rest in the meantime. */}
          {secretsState === "ready" && <MetaInputs form={form} disabled={fieldsLocked} />}

          <TestResultBanner result={testResult} />

          <DialogFooter className="mt-2 flex-wrap gap-2">
            <DialogClose asChild>
              <Button type="button" variant="outline" disabled={isSubmitting} className="max-md:h-10">Cancelar</Button>
            </DialogClose>
            <Button
              type="button"
              variant="secondary"
              onClick={handleTest}
              disabled={isTesting || fieldsLocked || !canTest}
              title={canTest ? undefined : "Preencha os campos da credencial para testar"}
              aria-busy={isTesting}
              className="gap-1 max-md:h-10"
            >
              {isTesting
                ? <TbLoader2 className="size-4 motion-safe:animate-spin" aria-hidden="true" />
                : <TbPlugConnected className="size-4" aria-hidden="true" />}
              {isTesting ? "Testando…" : "Testar credencial"}
            </Button>
            <Button type="submit" disabled={fieldsLocked} className="gap-1 max-md:h-10">
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
