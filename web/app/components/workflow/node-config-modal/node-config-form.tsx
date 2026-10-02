import { INodeContext } from "@/context/useFlowContext"
import React, { useMemo } from "react"
import dynamic from "next/dynamic"

// Campos reutilizados do painel legado
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
import { SEM_SUGESTAO, sugestaoParaNo } from "../utils/colunas-conhecidas"
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

// O editor de objeto arrasta o json-edit-react (~54 KB minificado) junto, e a
// maioria dos nós não tem um único campo do tipo `object`. Carregado sob demanda
// ele sai até do chunk do modal.
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

/** O que todo helper especializado recebe. */
interface HelperProps {
  values: NodeConfigFormProps["values"]
  setNodeField: NodeConfigFormProps["setNodeField"]
  saveNodeConfig: NodeConfigFormProps["saveNodeConfig"]
  hasUnsaved: boolean
  workflowId?: string
  // SubWorkflowHelper usa para descobrir, pelas arestas que chegam neste nó,
  // quais chaves de input existem de fato — em vez de o operador digitá-las.
  nodeId?: string
  // Os campos do nó no catálogo do servidor, com os `default` da instalação (o
  // ScheduleTrigger tira daqui o fuso padrão).
  campos?: INodesPropertyAPI[]
  // O editor de portas do SubWorkflowOutput trava enquanto houver aresta
  // ligada: lá as portas são pontos de conexão, e mudá-las deixaria as
  // arestas apontando para um ponto que não existe mais.
  //
  // OBRIGATÓRIO de propósito: com valor opcional, esquecer de passar aqui
  // destravaria o editor em silêncio — e o defeito só apareceria como aresta
  // sumida no canvas de alguém. Assim, esquecer não compila.
  conexoesDeEntrada: number
  // Colunas conhecidas dos nós anteriores, para os helpers cujos campos pedem
  // nome de coluna (o SetFields inteiro é isso). Sem passar por aqui, o nó
  // "redefinir campos" era o único do fluxo que nunca via uma sugestão — o
  // helper substitui o renderizador de campos, onde a dica nasce.
  //
  // OBRIGATÓRIAS pela mesma razão do campo acima: opcional, um helper novo
  // esqueceria de recebê-las e a ausência viraria "a sugestão não funciona
  // neste nó" — indistinguível, para quem usa, do defeito que motivou tudo.
  sugestoesDeColunas: string[]
  sugestoesDesatualizadas: boolean
  sugestoesParciais: boolean
}

// Os dois editores de porta são o MESMO componente com uma variante fixa, e por
// isso precisam de um nome próprio aqui em cima.
//
// Como wrappers inline dentro do formulário, eram uma função nova a cada render:
// o tipo do elemento mudava de identidade, o React desmontava e remontava a
// subárvore inteira, e o campo de texto — recriado do zero — perdia o foco a
// cada tecla. Digitar o nome de uma porta só era possível uma letra por vez,
// clicando de volta no campo entre elas.
const SubWorkflowInputPorts = (props: HelperProps) => (
  <SubWorkflowPortsHelper {...props} variant="input" />
)
const SubWorkflowOutputPorts = (props: HelperProps) => (
  <SubWorkflowPortsHelper {...props} variant="output" />
)

/** Helpers que substituem a renderização padrão dos campos, por tipo de nó.
 *
 * No escopo do módulo: recriar o mapa a cada render remontaria o helper montado,
 * perdendo foco e estado interno dele. */
const HELPER_MAP: Record<string, React.ComponentType<HelperProps>> = {
  ScheduleTrigger: ScheduleTriggerHelper,
  SetFields: SetFieldsHelper,
  SubWorkflow: SubWorkflowHelper,
  SubWorkflowInput: SubWorkflowInputPorts,
  SubWorkflowOutput: SubWorkflowOutputPorts,
}

/**
 * Painel central do modal — renderiza os campos de configuração do nó.
 * Reutiliza exatamente os mesmos componentes de campo do painel legado.
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

  // Quantas arestas chegam a este nó. O editor de portas trava enquanto houver
  // alguma: mudar as portas com ligações feitas as deixaria apontando para um
  // ponto de conexão inexistente, e elas somem do canvas sem como apagar.
  const edges = useEdges()
  const conexoesDeEntrada = edges.filter(e => e.target === nodeFound?.id).length

  // Colunas conhecidas dos nós ANTERIORES a este — de um run desta sessão ou
  // re-hidratadas do último run persistido. Vira sugestão nos campos que pedem
  // nome de coluna — antes a única forma de saber o que chega aqui era
  // executar o fluxo, olhar o resultado e voltar.
  //
  // FOTOGRAFIA, não assinatura. A store troca o Map a cada lote de eventos,
  // então assinar re-renderizaria o formulário inteiro — com Monaco e todos os
  // campos — a cada evento de nó enquanto uma execução acontece com este
  // diálogo aberto. E não há o que ganhar: o botão de executar fica atrás do
  // overlay, então não se dispara um run daqui; o que vale é o estado do
  // momento em que o diálogo abriu.
  const colunasSugeridas = useMemo(() => {
    if (!nodeFound?.id) return SEM_SUGESTAO
    return sugestaoParaNo(edges, useKnownColumnsStore.getState().porNo, nodeFound.id)
    // `edges` entra porque religar o nó muda de onde as colunas vêm.
  }, [edges, nodeFound?.id])

  /** Colunas a oferecer neste campo, conforme o lado que ele declara. */
  function sugerirColunas(field: INodesPropertyAPI): string[] {
    const de = field.suggest_columns
    if (!de) return []
    return de === "*" ? colunasSugeridas.todas : (colunasSugeridas.porPorta[de] ?? [])
  }

  const hasUnsaved = JSON.stringify(nodeFound?.data.properties) !== JSON.stringify(values)

  // Visibilidade condicional declarativa: um campo com `visibleWhen` só aparece
  // quando o valor atual do campo referenciado está em `in`. Lista → AND.
  const isFieldVisible = (field: INodesPropertyAPI): boolean => {
    const vw = field.visibleWhen
    if (!vw) return true
    const rules = Array.isArray(vw) ? vw : [vw]
    return rules.every(r => r.in.includes(values?.[r.field] as string | number | boolean))
  }

  // Nó sem campos — mostra apenas o helper de operação
  if (nodeFound?.data.fields.length === 0) {
    return (
      <div className="overflow-y-auto flex-1 p-4">
        <NodeOperationHelper
          name={nodeFound.data.name}
          alias={nodeFound.data.alias as string}
          description={nodeFound.data.description}
          type={nodeFound.data.type as string}
          inputs={(nodeFound.data.inputs ?? []) as INodePortAPI[]}
          // Os CAMPOS de saída (saidasDoNo), não os handles: um nó linear tem
          // ponto de conexão anônimo (outputs = []) mas continua entregando
          // `output` — e é isso que este painel existe para dizer.
          outputs={saidasDoNo(nodeFound.data)}
        />
      </div>
    )
  }

  // Nó com helper especializado (ScheduleTrigger, SetFields, etc.)
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
          sugestoesDeColunas={colunasSugeridas.todas}
          sugestoesDesatualizadas={colunasSugeridas.desatualizadas}
          sugestoesParciais={colunasSugeridas.parciais}
        />
      </div>
    )
  }

  // Renderização padrão dos campos
  return (
    // `gap-4`, e nao `gap-3`: sem os paragrafos de descricao (agora tooltip no
    // rotulo) as linhas encurtaram e ficaram todas com a mesma altura, entao a
    // separacao entre campos passou a ser o unico ritmo da lista.
    <div className="flex flex-col gap-4 p-4 overflow-y-auto flex-1">
      {/* Helper WFS: discovery de camadas com dropdown */}
      {nodeName === "WFS" && (
        <WFSHelper values={values} setNodeField={setNodeField} workflowId={workflowId} />
      )}

      {nodeFound?.data.fields.map(field => {
        const fieldProps = { field, setNodeField, values }
        const key = `${nodeFound.id}-${field.name}`

        // Visibilidade condicional declarativa (substitui as regras hardcoded de
        // Conditional/Response, agora expressas via `visibleWhen` no schema do nó).
        // Avaliado ANTES dos casos especiais para valer inclusive p/ credential_id
        // (ex.: DataOutput oculta a credencial quando o artefato é público).
        if (!isFieldVisible(field)) return null

        // Campos especiais
        if (field.name === "credential_id")
          return <CredentialField key={key} {...fieldProps} nodeFound={nodeFound} required={requiresCredential} />
        // Campos preenchidos pelo SERVIDOR, nunca pela pessoa: o alias, a DSN
        // resolvida da credencial e a autenticacao HTTP/S3 resolvida. A checagem e
        // pelo NOME e nao pelo tipo — `http_auth` e `object`, e a condicao antiga
        // (`type === "string"`) o teria deixado passar, desenhando um editor de
        // JSON vazio chamado "Autenticacao resolvida" no meio do formulario.
        if (["alias", "credential_id", "connectionString", "http_auth", "s3_auth", "fundo_da_instalacao"].includes(field.name))
          return null

        // queryParams é renderizado pelo SqlField (inputs nomeados) — pular aqui
        const hasSqlSibling = nodeFound.data.fields.some(f => f.type === "sql")
        if (field.name === "queryParams" && hasSqlSibling) return null

        // url e typeName do WFS são gerenciados pelo WFSHelper — pular aqui
        const isWFS = nodeName === "WFS"
        if (isWFS && (field.name === "url" || field.name === "typeName")) return null

        // Campos por tipo
        switch (field.type) {
          case "string":  return <StringField key={key} {...fieldProps} nodeFound={nodeFound} sugestoes={sugerirColunas(field)} sugestoesDesatualizadas={colunasSugeridas.desatualizadas} sugestoesParciais={colunasSugeridas.parciais} />
          case "number":  return <NumericField key={key} {...fieldProps} variant="number" />
          case "integer": return <NumericField key={key} {...fieldProps} variant="integer" />
          case "boolean": return <BooleanField key={key} {...fieldProps} />
          case "code":    return <CodeField key={key} {...fieldProps} nodeFound={nodeFound} />
          case "sql":     return <SqlField key={key} {...fieldProps} paramsFieldName="queryParams" />
          case "drive":   return <DriveField key={key} {...fieldProps} />
          case "artifact": return <ArtifactField key={key} {...fieldProps} />
          case "select":  return <SelectField key={key} {...fieldProps} />
          case "ports":   return <PortsField key={key} {...fieldProps} conexoesDeEntrada={conexoesDeEntrada} />
          case "chips":   return <ChipsField key={key} {...fieldProps} sugestoes={sugerirColunas(field)} sugestoesDesatualizadas={colunasSugeridas.desatualizadas} sugestoesParciais={colunasSugeridas.parciais} />
          case "keyvalue": return <KeyValueField key={key} {...fieldProps} />
          case "object":
            // Editores dedicados no lugar do JSON cru — mesmo despacho por
            // nome do payload_schema. O formato persistido não muda: gravam a
            // MESMA lista que o execute lê, então fluxos salvos abrem aqui e
            // os daqui rodam em executor antigo.
            if (nodeName === "Sort" && field.name === "sort_by")
              return <SortByField key={key} {...fieldProps} sugestoes={sugerirColunas(field)} sugestoesDesatualizadas={colunasSugeridas.desatualizadas} sugestoesParciais={colunasSugeridas.parciais} />
            if (nodeName === "Switch" && field.name === "rules")
              return <SwitchRulesField key={key} {...fieldProps} sugestoes={sugerirColunas(field)} sugestoesDesatualizadas={colunasSugeridas.desatualizadas} sugestoesParciais={colunasSugeridas.parciais} />
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
