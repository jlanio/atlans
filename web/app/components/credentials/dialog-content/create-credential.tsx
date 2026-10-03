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
  /** When provided, restricts the types compatible with the node in use */
  allowedTypes?: string[]
  /** Pre-selected type (e.g. when opening inline from a specific node) */
  defaultType?: string
  /**
   * Initial values to pre-fill the form — used when DUPLICATING a credential.
   * The caller forces a remount via `key` when this changes, so reading it in
   * defaultValues (once) is enough.
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

  // OPTIONAL access on purpose: this modal is also mounted inside the workflow
  // canvas (nodes-configuration/fields/credential-field.tsx), where there is no
  // CredentialsContextProvider. Destructuring directly here breaks that path —
  // and no test catches it, because the modal is mocked as () => null.
  const credCtx = useCredentialsContext()
  const [credentialTypes, setCredentialTypes] = useState<ICredentialTypeSchema[]>([])
  const [typesError, setTypesError] = useState(false)
  const [isTesting, setIsTesting] = useState(false)
  const [testResult, setTestResult] = useState<TestResult | null>(null)

  useEffect(() => {
    // Without error handling the type Select stayed empty with no explanation
    // at all. The equivalent path in the canvas already warned with a toast.
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

  // Resets the data on type change to avoid orphaned fields.
  //
  // The previous type has to come from a ref. Before it was
  // `const previousType = form.getValues("type")` in the component body —
  // recomputed on EVERY render, so when the effect ran the value was already the
  // new one and `previousType !== selectedType` was never true. The effect was
  // dead code: the old type's fields stayed in `data` and went to the API, and
  // a "conexão OK" from another type stayed on screen.
  const previousTypeRef = useRef(selectedType)
  useEffect(() => {
    if (previousTypeRef.current !== selectedType) {
      previousTypeRef.current = selectedType
      form.setValue("data", {})
      setTestResult(null)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedType])

  // The test result goes stale as soon as any field changes: without this a
  // "conexão bem-sucedida" stayed green after the user changed the password.
  //
  // The dependency is the SERIALIZED value, not the object: `form.watch` may
  // return a new reference on every render, and then the effect would clear the
  // result on the render right after the test itself — there would never be time
  // to read it.
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

    // `data` could be undefined on a 200 without a body, and the concat inserted an
    // undefined item into the list. Only propagates when there is a real object.
    if (credCtx?.setCredentialsContext && respCred.data) {
      const criada = respCred.data
      credCtx.setCredentialsContext(prev => ({
        ...prev,
        credentials: prev.credentials.concat(criada)
      }))
    }

    // The canvas reads credentials from the in-memory catalog, with a 5 min TTL.
    // Without invalidating here, the credential just created in /credentials did
    // not show up in the node's select until the TTL expired.
    useWorkflowCatalogStore.getState().invalidarCredenciais()

    createToast.success("Credencial criada", data.name)
    form.reset()
    setCreateModalState(false)
  }

  // react-hook-form's `isSubmitting`: it was not used anywhere in the repo, and
  // without it a double click on "Criar" created two credentials.
  const { isSubmitting } = form.formState
  const canTest = !!selectedType && Object.keys(dataFields ?? {}).length > 0

  return (
    <DialogContent
      // Closing mid-submit unmounts the component during the await and leaves the
      // user not knowing whether the credential was created. All three exits need
      // to be covered — blocking only Esc and click-outside leaves the X as an escape.
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

          {/* Schema-driven fields or the free editor as a fallback */}
          {activeSchema ? (
            <SchemaFieldsInput form={form} schema={activeSchema} />
          ) : selectedType ? (
            <PropsInput form={form} />
          ) : null}

          {/* Optional metadata (description, tags, expiration, sharing) only
              appears after a type has been chosen — before that the modal is
              just name + type. */}
          {selectedType && <MetaInputs form={form} />}

          <TestResultBanner result={testResult} />

          <DialogFooter className="mt-2 flex-wrap gap-2">
            <DialogClose asChild>
              <Button type="button" variant="outline" disabled={isSubmitting} className="max-md:h-10">Cancelar</Button>
            </DialogClose>
            {/* Always rendered, disabled when there is nothing to test: before, it
                appeared and disappeared as the fields were filled in,
                shifting the other buttons mid-typing and entering/leaving
                the tab order.
                Label "Testar credencial", not "Testar conexão": the backend only
                actually connects for postgresql/mysql/s3 — for the other types it
                only validates the fields, and the button promised more than it delivered. */}
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
