import { INodeContext, INodeStatusWorkFlow } from "@/context/useFlowContext"
import { STATUS_COLOR_MAP, STATUS_LABEL } from "@/consts/NodeStatusStyles"
import { TbPinFilled } from "react-icons/tb"
import { useMemo, useState } from "react"
import { useParams } from "next/navigation"
import { useWorkflowExecutionStore } from "@/app/stores/workflowExecutionStore"
import { useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore"
import { useNodeSamplesStore } from "@/app/stores/nodeSamplesStore"
import { resolveNodeAlias } from "../utils/node-alias"
import { saidasDoNo } from "../utils/node-ports"
import {
  AbasDeChave, FilhosDaChave, SeletorDeVisao, SeloAnterior, SemAmostra, VisaoDaSaida, useVisaoLembrada,
} from "./data-view"

interface OutputPreviewProps {
  nodeFound: INodeContext
}

/**
 * Right panel — what this node produced (docs/specs/node-data-panels.md §6.3).
 *
 * The same three views as the input panel, over this node's own sample:
 * Schema (keys, columns, example values), Tabela and JSON. Status, duration,
 * error and the pin state stay at the top.
 */
const OutputPreview = ({ nodeFound }: OutputPreviewProps) => {
  const workflowId = useParams<{ id?: string }>()?.id
  const statusWorkflow = useWorkflowExecutionStore(s => s.statusWorkflow)
  const registro = useNodeSamplesStore(s => (workflowId && s.workflowId === workflowId ? s.byNode[nodeFound.id] : undefined))
  const desligado = useNodeSamplesStore(s => !!workflowId && s.workflowId === workflowId && s.disabledByAdmin)
  const pin = useWorkflowCatalogStore(s => s.pinnedNodes.find(p => p.node_id === nodeFound.id))
  const fixado = !!pin && !pin.expired
  const [visao, setVisao] = useVisaoLembrada("saidas", !!registro)

  const nodeStatus: INodeStatusWorkFlow | undefined = statusWorkflow?.nodes?.find(
    n => n.id === nodeFound.id
  )

  // The configured outputs, not the catalog's: in the Python Script they come
  // from `output_vars`, and the panel always showed "result" even after the
  // person had renamed the script's own variables.
  // Memoized: a new array on every render made the `chaves` memo below useless.
  const staticFields = useMemo(() => saidasDoNo(nodeFound.data), [nodeFound.data])
  const alias = resolveNodeAlias(nodeFound.data ?? {}) || nodeFound.id.slice(0, 8)

  const chaves = useMemo(() => {
    const keys = new Set<string>()
    nodeStatus?.output_keys?.forEach(k => keys.add(k))
    Object.keys(registro?.sample.outputs ?? {}).forEach(k => keys.add(k))
    staticFields.forEach(f => keys.add(f.name))
    return [...keys]
  }, [nodeStatus?.output_keys, registro, staticFields])

  const [chave, setChave] = useState<string | null>(null)
  const chaveAtual = chave && chaves.includes(chave) ? chave : (chaves.find(k => registro?.sample.outputs[k]) ?? chaves[0])
  const saidaAtual = chaveAtual ? registro?.sample.outputs[chaveAtual] : undefined
  const motivoVazio = desligado ? "desligado" : (nodeStatus && nodeStatus.status !== "idle") ? "sem-amostra" : "nao-executado"
  const tipoDeclarado = new Map(staticFields.map(f => [f.name, f]))

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="flex flex-col gap-2 border-b px-3 pb-2 pt-1">
        <div className="flex items-center gap-2">
          <span className="min-w-0 flex-1 truncate text-xs font-semibold">{alias}</span>
          <SeletorDeVisao visao={visao} onChange={setVisao} />
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {nodeStatus && (
            <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${STATUS_COLOR_MAP[nodeStatus.status] ?? STATUS_COLOR_MAP.idle}`}>
              {STATUS_LABEL[nodeStatus.status] ?? nodeStatus.status}
              {nodeStatus.duration !== undefined && ` · ${nodeStatus.duration.toFixed(0)}ms`}
            </span>
          )}
          {nodeStatus?.cache_hit && (
            <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">do cache</span>
          )}
          {fixado && (
            <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-1.5 py-0.5 text-[10px] text-amber-600 dark:text-amber-400"
                  title="As próximas execuções reaproveitam esta saída em vez de rodar o nó">
              <TbPinFilled size={10} /> dados fixados
            </span>
          )}
          {registro?.stale && <SeloAnterior />}
        </div>
        {visao !== "schema" && chaveAtual && <AbasDeChave chaves={chaves} atual={chaveAtual} onChange={setChave} />}
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-3">
        {nodeStatus?.error && (
          <p className="text-[11px] text-destructive break-all bg-destructive/10 rounded p-2">{nodeStatus.error}</p>
        )}

        {visao === "schema" ? (
          chaves.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-4">Nenhum campo de saída declarado.</p>
          ) : (
            <div className="flex flex-col gap-1.5 text-xs">
              {chaves.map(key => {
                const saida = registro?.sample.outputs[key]
                const declarado = tipoDeclarado.get(key)
                const tipo = saida?.kind === "table"
                  ? `tabela · ${saida.rows_total.toLocaleString("pt-BR")} linhas`
                  : saida?.kind === "json" ? "objeto" : declarado?.type
                return (
                  <div key={key} className="flex flex-col gap-0.5">
                    <div className="rounded bg-muted/60 px-1.5 py-1">
                      <code className="font-mono text-[11px] font-medium text-primary">{key}</code>
                      {tipo && <span className="ml-1.5 text-[9px] text-muted-foreground">{tipo}</span>}
                      {!saida && declarado?.description && (
                        <p className="mt-0.5 text-[10px] text-muted-foreground">{declarado.description}</p>
                      )}
                    </div>
                    {/* Not draggable: this node's own outputs are not inputs of its fields. */}
                    <FilhosDaChave saida={saida} colunasConhecidas={nodeStatus?.output_columns?.[key]} arrastavel={false} />
                  </div>
                )
              })}
              {!registro && (
                <p className="mt-1 text-[10px] text-muted-foreground">
                  {desligado
                    ? "Amostras de dados desligadas pelo administrador."
                    : "Execute o fluxo para ver as colunas e um valor de exemplo de cada saída."}
                </p>
              )}
            </div>
          )
        ) : saidaAtual ? (
          <VisaoDaSaida saida={saidaAtual} visao={visao} onVerJson={() => setVisao("json")} />
        ) : (
          <SemAmostra motivo={motivoVazio} deQuem="deste nó" />
        )}
      </div>
    </div>
  )
}

export default OutputPreview
