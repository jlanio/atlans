import { INodeContext } from "@/context/useFlowContext"
import React, { useMemo } from "react"
import dynamic from "next/dynamic"

// Fields reused from the legacy panel
import CredentialField from "../nodes-configuration/fields/credential-field"
import StringField from "../nodes-configuration/fields/string-field"
import PayloadSchemaEditor from "../nodes-configuration/fields/payload-schema-editor"
import NumericField from "../nodes-configuration/fields/numeric-field"
import BooleanField from "../nodes-configuration/fields/boolean-field"
import SqlField from "../nodes-configuration/fields/sql-field"
import CodeField from "../nodes-configuration/fields/code-field"
import DriveField from "../nodes-configuration/fields/drive-field"
import ArtifactField from "../nodes-configuration/fields/artifact-field"
import SelectField from "../nodes-configuration/fields/select-field"
import PortsField from "../nodes-configuration/fields/ports-field"
import ChipsField from "../nodes-configuration/fields/chips-field"
import KeyValueField from "../nodes-configuration/fields/key-value-field"
import SortByField from "../nodes-configuration/fields/sort-by-field"
import SwitchRulesField from "../nodes-configuration/fields/switch-rules-field"
import { NO_SUGGESTION, sugestaoParaNo } from "../utils/colunas-conhecidas"
import { saidasDoNo } from "../utils/node-ports"
import { useKnownColumnsStore } from "@/app/stores/knownColumnsStore"
import WFSHelper from "../nodes-configuration/wfs-helper"
import NodeOperationHelper from "../nodes-configuration/node-operation-helper"
import ScheduleTriggerHelper from "../nodes-configuration/schedule-trigger-helper"
import SetFieldsHelper from "../nodes-configuration/set-fields-helper"
import SubWorkflowHelper from "../nodes-configuration/sub-workflow-helper"
import SubWorkflowPortsHelper from "../nodes-configuration/sub-workflow-ports-helper"
import { INodePortAPI, INodesPropertyAPI } from "@/service/types"
import { useEdges } from "@xyflow/react"

// The object editor drags json-edit-react (~54 KB minified) along, and most
// nodes don't have a single field of type `object`. Loaded on demand, it even
// leaves the modal's chunk.
const ObjectField = dynamic(() => import("../nodes-configuration/fields/object-field"), {
  ssr: false,
  loading: () => <div className="h-24 rounded-sm border bg-muted/40 animate-pulse" />,
})

interface NodeConfigFormProps {
  nodeFound: INodeContext
  values: Record<string, string | number | boolean> | undefined
  setNodeField: (field: string, value: string | number | boolean) => void
  saveNodeConfig: () => void
  nodeName: string
  requiresCredential: boolean
  workflowId?: string
}

/** What every specialized helper receives. */
interface HelperProps {
  values: NodeConfigFormProps["values"]
  setNodeField: NodeConfigFormProps["setNodeField"]
  saveNodeConfig: NodeConfigFormProps["saveNodeConfig"]
  hasUnsaved: boolean
  workflowId?: string
  // SubWorkflowHelper uses it to find out, from the edges arriving at this node,
  // which input keys actually exist — instead of the operator typing them.
  nodeId?: string
  // The node's fields in the server catalog, with the installation's `default`s
  // (ScheduleTrigger takes the default time zone from here).
  campos?: INodesPropertyAPI[]
  // The SubWorkflowOutput port editor locks while there is a connected
  // edge: there the ports are connection points, and changing them would leave
  // the edges pointing at a point that no longer exists.
  //
  // REQUIRED on purpose: with an optional value, forgetting to pass it here
  // would silently unlock the editor — and the defect would only show up as an
  // edge gone from someone's canvas. This way, forgetting doesn't compile.
  conexoesDeEntrada: number
  // Known columns from the upstream nodes, for the helpers whose fields ask for
  // a column name (the whole of SetFields is that). Without passing through
  // here, the "redefinir campos" (redefine fields) node was the only one in the
  // workflow that never saw a suggestion — the helper replaces the field
  // renderer, where the hint originates.
  //
  // REQUIRED for the same reason as the field above: if optional, a new helper
  // would forget to receive them and the absence would become "suggestions
  // don't work on this node" — indistinguishable, to the user, from the defect
  // that motivated all this.
  sugestoesDeColunas: string[]
  sugestoesDesatualizadas: boolean
  sugestoesParciais: boolean
}

// The two port editors are the SAME component with a fixed variant, and that
// is why they need a name of their own up here.
//
// As inline wrappers inside the form, they were a new function on every render:
// the element type changed identity, React unmounted and remounted the whole
// subtree, and the text field — recreated from scratch — lost focus on every
// keystroke. Typing a port name was only possible one letter at a time,
// clicking back into the field between them.
const SubWorkflowInputPorts = (props: HelperProps) => (
  <SubWorkflowPortsHelper {...props} variant="input" />
)
const SubWorkflowOutputPorts = (props: HelperProps) => (
  <SubWorkflowPortsHelper {...props} variant="output" />
)

/** Helpers that replace the default field rendering, by node type.
 *
 * At module scope: recreating the map on every render would remount the mounted
 * helper, losing its focus and internal state. */
const HELPER_MAP: Record<string, React.ComponentType<HelperProps>> = {
  ScheduleTrigger: ScheduleTriggerHelper,
  SetFields: SetFieldsHelper,
  SubWorkflow: SubWorkflowHelper,
  SubWorkflowInput: SubWorkflowInputPorts,
  SubWorkflowOutput: SubWorkflowOutputPorts,
}

/**
 * Central panel of the modal — renders the node's configuration fields.
 * Reuses exactly the same field components as the legacy panel.
 */
const NodeConfigForm = ({
  nodeFound,
  values,
  setNodeField,
  saveNodeConfig,
  nodeName,
  requiresCredential,
  workflowId,
}: NodeConfigFormProps) => {

  // How many edges arrive at this node. The port editor locks while there is
  // any: changing the ports with connections made would leave them pointing at
  // a nonexistent connection point, and they vanish from the canvas with no way
  // to delete them.
  const edges = useEdges()
  const conexoesDeEntrada = edges.filter(e => e.target === nodeFound?.id).length

  // Known columns of the nodes UPSTREAM of this one — from a run in this session
  // or re-hydrated from the last persisted run. They become suggestions in the
  // fields that ask for a column name — before, the only way to know what
  // arrives here was to run the workflow, look at the result and come back.
  //
  // A SNAPSHOT, not a subscription. The store swaps the Map on every batch of
  // events, so subscribing would re-render the whole form — with Monaco and
  // every field — on each node event while an execution happens with this
  // dialog open. And there is nothing to gain: the run button sits behind the
  // overlay, so no run is fired from here; what matters is the state at the
  // moment the dialog opened.
  const suggestedColumns = useMemo(() => {
    if (!nodeFound?.id) return NO_SUGGESTION
    return sugestaoParaNo(edges, useKnownColumnsStore.getState().porNo, nodeFound.id)
    // `edges` is included because rewiring the node changes where the columns come from.
  }, [edges, nodeFound?.id])

  /** Columns to offer in this field, according to the side it declares. */
  function suggestColumns(field: INodesPropertyAPI): string[] {
    const de = field.suggest_columns
    if (!de) return []
    return de === "*" ? suggestedColumns.todas : (suggestedColumns.porPorta[de] ?? [])
  }

  const hasUnsaved = JSON.stringify(nodeFound?.data.properties) !== JSON.stringify(values)

  // Declarative conditional visibility: a field with `visibleWhen` only appears
  // when the referenced field's current value is in `in`. List → AND.
  const isFieldVisible = (field: INodesPropertyAPI): boolean => {
    const vw = field.visibleWhen
    if (!vw) return true
    const rules = Array.isArray(vw) ? vw : [vw]
    return rules.every(r => r.in.includes(values?.[r.field] as string | number | boolean))
  }

  // Node without fields — shows only the operation helper
  if (nodeFound?.data.fields.length === 0) {
    return (
      <div className="overflow-y-auto flex-1 p-4">
        <NodeOperationHelper
          name={nodeFound.data.name}
          alias={nodeFound.data.alias as string}
          description={nodeFound.data.description}
          type={nodeFound.data.type as string}
          inputs={(nodeFound.data.inputs ?? []) as INodePortAPI[]}
          // The output FIELDS (saidasDoNo), not the handles: a linear node has an
          // anonymous connection point (outputs = []) but still delivers
          // `output` — and that is what this panel exists to say.
          outputs={saidasDoNo(nodeFound.data)}
        />
      </div>
    )
  }

  // Node with a specialized helper (ScheduleTrigger, SetFields, etc.)
  if (HELPER_MAP[nodeName]) {
    const Helper = HELPER_MAP[nodeName]
    return (
      <div className="overflow-y-auto flex-1 p-4">
        <Helper
          values={values}
          setNodeField={setNodeField}
          saveNodeConfig={saveNodeConfig}
          hasUnsaved={hasUnsaved}
          workflowId={workflowId}
          nodeId={nodeFound?.id}
          campos={nodeFound?.data?.fields}
          conexoesDeEntrada={conexoesDeEntrada}
          sugestoesDeColunas={suggestedColumns.todas}
          sugestoesDesatualizadas={suggestedColumns.desatualizadas}
          sugestoesParciais={suggestedColumns.parciais}
        />
      </div>
    )
  }

  // Default field rendering
  return (
    // `gap-4`, not `gap-3`: without the description paragraphs (now a tooltip on
    // the label) the rows got shorter and all the same height, so the spacing
    // between fields became the list's only rhythm.
    <div className="flex flex-col gap-4 p-4 overflow-y-auto flex-1">
      {/* WFS helper: layer discovery with a dropdown */}
      {nodeName === "WFS" && (
        <WFSHelper values={values} setNodeField={setNodeField} workflowId={workflowId} />
      )}

      {nodeFound?.data.fields.map(field => {
        const fieldProps = { field, setNodeField, values }
        const key = `${nodeFound.id}-${field.name}`

        // Declarative conditional visibility (replaces the hardcoded rules of
        // Conditional/Response, now expressed via `visibleWhen` in the node schema).
        // Evaluated BEFORE the special cases so it applies even to credential_id
        // (e.g. DataOutput hides the credential when the artifact is public).
        if (!isFieldVisible(field)) return null

        // Campos especiais
        if (field.name === "credential_id")
          return <CredentialField key={key} {...fieldProps} nodeFound={nodeFound} required={requiresCredential} />
        // Fields filled by the SERVER, never by the person: the alias, the DSN
        // resolved from the credential and the resolved HTTP/S3 authentication.
        // The check is by NAME, not by type — `http_auth` is `object`, and the old
        // condition (`type === "string"`) would have let it through, drawing an
        // empty JSON editor called "Autenticacao resolvida" in the middle of the form.
        if (["alias", "credential_id", "connectionString", "http_auth", "s3_auth", "fundo_da_instalacao"].includes(field.name))
          return null

        // queryParams is rendered by SqlField (named inputs) — skip here
        const hasSqlSibling = nodeFound.data.fields.some(f => f.type === "sql")
        if (field.name === "queryParams" && hasSqlSibling) return null

        // The WFS url and typeName are managed by WFSHelper — skip here
        const isWFS = nodeName === "WFS"
        if (isWFS && (field.name === "url" || field.name === "typeName")) return null

        // Fields by type
        switch (field.type) {
          case "string":  return <StringField key={key} {...fieldProps} nodeFound={nodeFound} sugestoes={suggestColumns(field)} sugestoesDesatualizadas={suggestedColumns.desatualizadas} sugestoesParciais={suggestedColumns.parciais} />
          case "number":  return <NumericField key={key} {...fieldProps} variant="number" />
          case "integer": return <NumericField key={key} {...fieldProps} variant="integer" />
          case "boolean": return <BooleanField key={key} {...fieldProps} />
          case "code":    return <CodeField key={key} {...fieldProps} nodeFound={nodeFound} />
          case "sql":     return <SqlField key={key} {...fieldProps} paramsFieldName="queryParams" />
          case "drive":   return <DriveField key={key} {...fieldProps} />
          case "artifact": return <ArtifactField key={key} {...fieldProps} />
          case "select":  return <SelectField key={key} {...fieldProps} />
          case "ports":   return <PortsField key={key} {...fieldProps} conexoesDeEntrada={conexoesDeEntrada} />
          case "chips":   return <ChipsField key={key} {...fieldProps} sugestoes={suggestColumns(field)} sugestoesDesatualizadas={suggestedColumns.desatualizadas} sugestoesParciais={suggestedColumns.parciais} />
          case "keyvalue": return <KeyValueField key={key} {...fieldProps} />
          case "object":
            // Dedicated editors instead of raw JSON — same dispatch by
            // payload_schema name. The persisted format doesn't change: they
            // write the SAME list that execute reads, so saved workflows open
            // here and the ones made here run on an old executor.
            if (nodeName === "Sort" && field.name === "sort_by")
              return <SortByField key={key} {...fieldProps} sugestoes={suggestColumns(field)} sugestoesDesatualizadas={suggestedColumns.desatualizadas} sugestoesParciais={suggestedColumns.parciais} />
            if (nodeName === "Switch" && field.name === "rules")
              return <SwitchRulesField key={key} {...fieldProps} sugestoes={suggestColumns(field)} sugestoesDesatualizadas={suggestedColumns.desatualizadas} sugestoesParciais={suggestedColumns.parciais} />
            return field.name === "payload_schema"
              ? <PayloadSchemaEditor key={key} {...fieldProps} />
              : <ObjectField key={key} {...fieldProps} />
          default: return null
        }
      })}
    </div>
  )
}

export default NodeConfigForm
