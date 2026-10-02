import { useState, useEffect } from "react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/app/components/ui/select"
import { Label } from "@/app/components/ui/label"
import { Button } from "@/app/components/ui/button"
import { Dialog } from "@/app/components/ui/dialog"
import { INodeContext } from "@/context/useFlowContext"
import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore"
import { INodesPropertyAPI } from "@/service/types"
import { TbAlertCircle, TbLock, TbPlus } from "react-icons/tb"
import { GisFlowService } from "@/service/GisFlowService"
import CreateCredential from "@/app/components/credentials/dialog-content/create-credential"
import { ICredentialTypeSchema } from "@/service/types"
import { useWorkspace } from "@/context/WorkspaceContext"
import { dadoOuAviso } from "@/lib/respostas"
import type { FieldProps } from "./types"

type CredentialFieldProps = FieldProps<{
  nodeFound: INodeContext
  /** Quando true, bloqueia o botão Aplicar enquanto nenhuma credencial estiver selecionada */
  required?: boolean
}>

const CredentialField = ({ nodeFound, field, values, setNodeField, required = false }: CredentialFieldProps) => {

  const credentials = useWorkflowCatalogStore(s => s.credentials)
  const setCredentials = useWorkflowCatalogStore(s => s.setCredentials)
  // Editor ou superior edita credenciais; viewer só lê. Não é "dono" —
  // o nome anterior (isOwner) descrevia uma regra que não existe.
  const { canEdit } = useWorkspace()
  const [createOpen, setCreateOpen] = useState(false)
  const [credentialTypes, setCredentialTypes] = useState<ICredentialTypeSchema[]>([])

  useEffect(() => {
    GisFlowService.getCredentialTypes().then(res => {
      const tipos = dadoOuAviso(res, "Erro ao carregar tipos de credenciais")
      if (tipos) setCredentialTypes(tipos)
    })
  }, [])

  async function handleAfterCreate() {
    setCreateOpen(false)
    const lista = dadoOuAviso(await GisFlowService.getCredentials(), "Erro ao recarregar credenciais")
    if (lista) setCredentials(lista)
  }

  const nodeCategory = nodeFound.data.type as string

  // Tipos definidos diretamente na propriedade têm prioridade sobre os tipos do nó
  const allowedByProperty: string[] | undefined = (field as INodesPropertyAPI).credential_types

  const compatibleTypes = allowedByProperty
    ? allowedByProperty
    : credentialTypes.filter(t => t.node_types.includes(nodeCategory)).map(t => t.type)

  const filtered = compatibleTypes.length === 0
    ? credentials
    : credentials.filter(c => compatibleTypes.includes(c.type))

  function getCredentialLabel(credType: string) {
    return credentialTypes.find(t => t.type === credType)?.label ?? credType
  }

  const selectedId = values?.[field.name] as string ?? ""
  const isMissingRequired = required && !selectedId

  // A lista vem de GET /credentials/, que o backend filtra por owner_id: a
  // credencial de outro membro do workspace NUNCA aparece aqui. Sem tratar
  // isso, o Select não acha item para o value e cai no placeholder — o campo
  // parece vazio embora o nó esteja configurado e executando.
  const selectedCredential = credentials.find(c => c.id === selectedId)
  const isForeign = !!selectedId && !selectedCredential
  // Mesmo sintoma, outra causa: a credencial é do usuário, mas o tipo não é
  // aceito por este nó, então ficou fora de `filtered`. Aqui o nome pode ser
  // mostrado, já que pertence a quem está vendo.
  const isIncompatible = !!selectedCredential && !filtered.some(c => c.id === selectedId)

  // Viewer — estado somente leitura
  if (!canEdit) {
    return (
      <div className="flex flex-col gap-2">
        <Label>Credencial</Label>
        <div className="flex items-center gap-2 rounded-md border border-dashed px-3 py-2 text-sm text-muted-foreground bg-muted/40">
          <TbLock className="shrink-0 h-4 w-4" />
          {selectedCredential ? (
            <div className="flex flex-col min-w-0">
              <span className="font-medium text-foreground truncate">{selectedCredential.name}</span>
              <span className="text-xs">{getCredentialLabel(selectedCredential.type)}</span>
            </div>
          ) : isForeign ? (
            // Antes caía em "Edição Indisponível", que sugere nó sem credencial.
            <span className="text-foreground">Credencial de outro usuário</span>
          ) : (
            <span className="italic">Nenhuma credencial configurada</span>
          )}
        </div>
        <p className="text-xs text-muted-foreground">
          Seu papel neste workspace não permite editar credenciais.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1">
          <Label htmlFor={field.name}>Credencial</Label>
          {required && (
            <span className="text-destructive text-xs font-medium">*obrigatório</span>
          )}
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-6 px-2 text-xs gap-1"
          onClick={() => setCreateOpen(true)}
        >
          <TbPlus className="h-3 w-3" />
          Nova credencial
        </Button>
      </div>

      <Select
        value={selectedId || "__none__"}
        onValueChange={value => setNodeField(field.name, value === "__none__" ? "" : value)}
      >
        <SelectTrigger
          id={field.name}
          disabled={filtered.length === 0 && required}
          className={`w-full ${isMissingRequired ? "border-destructive" : ""}`}
        >
          <SelectValue placeholder="Escolha a credencial" />
        </SelectTrigger>
        <SelectContent>
          {!required && (
            <SelectItem value="__none__">
              <span className="text-muted-foreground">Sem credencial (público)</span>
            </SelectItem>
          )}

          {/* Itens sintéticos: sem um SelectItem com este value, o Radix não
              tem o que casar e exibe o placeholder — o campo pareceria vazio. */}
          {isForeign && (
            <SelectItem value={selectedId}>
              <div className="flex items-center gap-1.5">
                <TbLock className="h-3 w-3 shrink-0" />
                <span>Credencial de outro usuário</span>
              </div>
            </SelectItem>
          )}
          {isIncompatible && selectedCredential && (
            <SelectItem value={selectedId}>
              <div className="flex flex-col">
                <span>{selectedCredential.name}</span>
                <span className="text-xs text-destructive">
                  {getCredentialLabel(selectedCredential.type)} — tipo não aceito por este nó
                </span>
              </div>
            </SelectItem>
          )}

          {filtered.map(credential => (
            <SelectItem key={credential.id} value={credential.id}>
              <div className="flex flex-col">
                <span>{credential.name}</span>
                <span className="text-xs text-muted-foreground">{getCredentialLabel(credential.type)}</span>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {isForeign && (
        <p className="text-xs text-muted-foreground">
          Configurada por quem criou o nó. O workflow tem uma única definição —
          escolher a sua substitui para todos os membros.
        </p>
      )}

      {isIncompatible && (
        <p className="flex items-center gap-1 text-xs text-destructive">
          <TbAlertCircle className="h-3 w-3" />
          Esta credencial não é de um tipo aceito por este nó
        </p>
      )}

      {isMissingRequired && (
        <p className="flex items-center gap-1 text-xs text-destructive">
          <TbAlertCircle className="h-3 w-3" />
          Este nó requer uma credencial para executar
        </p>
      )}

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <CreateCredential
          setCreateModalState={handleAfterCreate}
          allowedTypes={compatibleTypes.length > 0 ? compatibleTypes : undefined}
        />
      </Dialog>
    </div>
  )
}

export default CredentialField
