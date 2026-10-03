import { useState, useEffect } from "react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/app/components/ui/select"
import { Label } from "@/app/components/ui/label"
import { TbFileImport, TbRefresh, TbInbox } from "react-icons/tb"
import { useWorkspace } from "@/context/WorkspaceContext"
import { GisFlowService, IArtifactItem } from "@/service/GisFlowService"
import { dadoOuAviso } from "@/lib/respostas"
import type { FieldProps } from "./types"

type ArtifactFieldProps = FieldProps

/** The picker shows the most recent ones, not the whole history: downloading
 *  all of the user's artifacts just to pick one held the node modal until the
 *  complete list arrived. */
const LIMIT = 50

const ArtifactField = ({ field, values, setNodeField }: ArtifactFieldProps) => {
  const { current: workspace } = useWorkspace()
  const [items, setItems] = useState<IArtifactItem[]>([])
  const [loading, setLoading] = useState(false)
  const [truncado, setTruncated] = useState(false)
  // The list didn't arrive: the "no artifacts" notice would be a false statement.
  const [falhou, setFailed] = useState(false)

  async function fetchArtifacts() {
    if (!workspace) return
    setLoading(true)
    // The per-workspace slice is done by the SERVER: filtering on the client
    // meant downloading the artifacts of all of the user's workspaces only to
    // discard almost everything.
    const res = await GisFlowService.getArtifacts({
      workspace_id: workspace.id_hash,
      limit: LIMIT,
    })
    const dados = dadoOuAviso(res, "Erro ao carregar artefatos")
    const itens = dados?.items ?? []
    setItems(itens)
    setTruncated((dados?.total ?? 0) > itens.length)
    setFailed(dados === null)
    setLoading(false)
  }

  useEffect(() => {
    fetchArtifacts()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspace?.id_hash])

  const selected = (values?.[field.name] as string) ?? ""

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between">
        <Label htmlFor={field.name} className="flex items-center gap-1">
          <TbFileImport className="h-3.5 w-3.5" />
          {field.description ?? "Artefato"}
        </Label>
        <button
          type="button"
          onClick={fetchArtifacts}
          disabled={loading}
          className="text-muted-foreground hover:text-foreground transition-colors"
          title="Recarregar lista"
        >
          <TbRefresh className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      <Select
        value={selected || "__none__"}
        onValueChange={value => setNodeField(field.name, value === "__none__" ? "" : value)}
      >
        <SelectTrigger id={field.name} className="w-full">
          <SelectValue placeholder={loading ? "Carregando..." : "Selecione um artefato"} />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="__none__">
            <span className="text-muted-foreground">Nenhum artefato</span>
          </SelectItem>
          {items.map(art => (
            <SelectItem key={art.id_hash} value={art.id_hash}>
              <div className="flex flex-col">
                <span>{art.filename}</span>
                <span className="text-xs text-muted-foreground uppercase">
                  {art.format ?? ""}{art.workflow_name ? ` · ${art.workflow_name}` : ""}
                </span>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {truncado && !loading && (
        <p className="text-xs text-muted-foreground mt-1">
          Mostrando os {LIMIT} artefatos mais recentes deste workspace.
        </p>
      )}

      {items.length === 0 && !loading && (
        <div className="flex items-start gap-2 mt-1 px-2 py-1.5 rounded-md bg-muted/40">
          <TbInbox className="h-3.5 w-3.5 text-muted-foreground/60 shrink-0 mt-0.5" />
          <p className="text-xs text-muted-foreground">
            {falhou
              ? "Não foi possível carregar os artefatos deste workspace. Recarregue a lista para tentar de novo."
              : "Nenhum artefato neste workspace. Execute um workflow com um nó de Saída de Dados (destino Artefatos) para gerá-los."}
          </p>
        </div>
      )}
    </div>
  )
}

export default ArtifactField
