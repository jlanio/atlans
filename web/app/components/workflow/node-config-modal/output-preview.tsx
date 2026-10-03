import { INodeContext, INodeStatusWorkFlow } from "@/context/useFlowContext"
import { STATUS_COLOR_MAP, STATUS_LABEL } from "@/consts/NodeStatusStyles"
import { TbEye } from "react-icons/tb"
import { useState } from "react"
import { useWorkflowExecutionStore } from "@/app/stores/workflowExecutionStore"
import { saidasDoNo } from "../utils/node-ports"

interface OutputPreviewProps {
  nodeFound: INodeContext
}

type OutputTab = "status" | "schema"

/**
 * Right panel — shows the selected node's output.
 * Tabs: Status (last execution) | Schema (declared fields).
 */
const OutputPreview = ({ nodeFound }: OutputPreviewProps) => {
  const statusWorkflow = useWorkflowExecutionStore(s => s.statusWorkflow)
  const [tab, setTab] = useState<OutputTab>("status")

  const nodeStatus: INodeStatusWorkFlow | undefined = statusWorkflow?.nodes?.find(
    n => n.id === nodeFound.id
  )

  // The configured outputs, not the catalog's: in the Python Script they come
  // from `output_vars`, and the panel always showed "result" even after the
  // person had renamed the script's own variables.
  const staticFields = saidasDoNo(nodeFound.data)

  const statusColorMap = STATUS_COLOR_MAP
  const statusLabel = STATUS_LABEL

  if (!nodeStatus && staticFields.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-2 p-4">
        <TbEye size={28} />
        <p className="text-xs text-center">Execute o workflow para ver a saída.</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Tabs */}
      <div className="flex gap-1 px-4 pt-2">
        <button
          onClick={() => setTab("status")}
          className={`px-2 py-1 rounded text-[11px] font-medium transition-colors ${
            tab === "status" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted"
          }`}
        >
          Status
        </button>
        <button
          onClick={() => setTab("schema")}
          className={`px-2 py-1 rounded text-[11px] font-medium transition-colors ${
            tab === "schema" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted"
          }`}
        >
          Schema
        </button>
      </div>

      {/* Content of the Status tab */}
      {tab === "status" && (
        <div className="flex flex-col gap-3 p-4 overflow-y-auto">
          {nodeStatus ? (
            <div className="flex flex-col gap-1.5 rounded-md border p-3 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-medium">Status</span>
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${statusColorMap[nodeStatus.status] ?? statusColorMap.idle}`}>
                  {statusLabel[nodeStatus.status] ?? nodeStatus.status}
                </span>
              </div>

              {nodeStatus.duration !== undefined && (
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Duração</span>
                  <span>{nodeStatus.duration.toFixed(0)}ms</span>
                </div>
              )}

              {nodeStatus.output_keys && nodeStatus.output_keys.length > 0 && (
                <div className="flex flex-col gap-1 mt-1">
                  <span className="text-muted-foreground">Saídas</span>
                  <div className="flex flex-wrap gap-1">
                    {nodeStatus.output_keys.map(key => (
                      <code key={key} className="px-1 py-0.5 rounded bg-muted text-foreground text-[10px]">{key}</code>
                    ))}
                  </div>
                </div>
              )}

              {nodeStatus.error && (
                <div className="flex flex-col gap-1 mt-1">
                  <span className="text-muted-foreground">Erro</span>
                  <p className="text-destructive break-all bg-destructive/10 rounded p-2">
                    {nodeStatus.error}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground text-center py-4">
              Nenhuma execução registrada.
            </p>
          )}
        </div>
      )}

      {/* Content of the Schema tab */}
      {tab === "schema" && (
        <div className="flex flex-col gap-2 p-4 overflow-y-auto">
          {staticFields.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-4">
              Nenhum campo de saída declarado.
            </p>
          ) : (
            <div className="flex flex-col gap-1">
              {staticFields.map((field, i) => (
                <div key={`${field.name}-${i}`} className="flex flex-col gap-0.5 rounded-md border p-2.5 text-xs">
                  <div className="flex items-center gap-2">
                    <code className="px-1 py-0.5 rounded bg-muted text-foreground text-[11px] font-mono">{field.name}</code>
                    {field.type && (
                      <span className="text-muted-foreground text-[10px]">{field.type}</span>
                    )}
                  </div>
                  {field.description && (
                    <p className="text-muted-foreground text-[10px] mt-0.5">{field.description}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default OutputPreview
