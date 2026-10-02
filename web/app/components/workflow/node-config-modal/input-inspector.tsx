import { INodeContext } from "@/context/useFlowContext"
import { STATUS_COLOR_MAP, STATUS_LABEL } from "@/consts/NodeStatusStyles"
import { useEdges, useNodes } from "@xyflow/react"
import { TbInbox, TbCopy, TbGripVertical } from "react-icons/tb"
import { useCallback, useMemo, useState } from "react"
import { cn } from "@/lib/utils"
import { useWorkflowExecutionStore } from "@/app/stores/workflowExecutionStore"
import { resolveNodeAlias } from "../utils/node-alias"
import { saidasDoNo } from "../utils/node-ports"

interface InputInspectorProps {
  nodeFound: INodeContext
}

/**
 * Painel esquerdo — mostra dados de entrada do nó selecionado.
 * Output keys dos nós pais são arrastáveis (drag) para campos do form.
 * Ao soltar num campo de texto, insere a expressão Jinja {{ Alias.key }}.
 */
type InputTab = "campos" | "schema"

const InputInspector = ({ nodeFound }: InputInspectorProps) => {
  const edges = useEdges()
  const allNodes = useNodes<INodeContext>()
  const statusWorkflow = useWorkflowExecutionStore(s => s.statusWorkflow)
  const [tab, setTab] = useState<InputTab>("campos")

  const parentEdges = useMemo(() => edges.filter(e => e.target === nodeFound.id), [edges, nodeFound.id])

  const isPythonNode = nodeFound.data?.name === "PythonScript"

  // Portas declaradas por ESTE nó. Num nó de entradas dinâmicas elas são as que
  // a pessoa configurou, e é por elas que a variável do script se chama.
  const portasDeclaradas = ((nodeFound.data?.inputs ?? []) as { name: string }[]).map(p => p.name)

  // PERF: memoiza lookup de pais — evita recalcular O(n) a cada drag no canvas
  const parentInfos = useMemo(() => {
    // Deduplica: um pai pode ter múltiplas edges conectadas (ex: output + metadata)
    const seenIds = new Set<string>()
    const parentNodeIds = parentEdges.map(e => e.source).filter(id => {
      if (seenIds.has(id)) return false
      seenIds.add(id)
      return true
    })
    return parentNodeIds.map(id => {
      const node = allNodes.find(n => n.id === id)
      const status = statusWorkflow?.nodes?.find(n => n.id === id)
      // Mesma regra do executor (flow/executor/core.py::_resolve_alias), em
      // utils/node-alias — o painel gera expressões que o usuário arrasta para
      // o campo, então o alias daqui tem de ser o registrado no contexto.
      const alias = resolveNodeAlias(node?.data ?? {}) || id.slice(0, 8)
      const staticFields: string[] = saidasDoNo(node?.data).map(f => f.name)
      // Todas as edges deste pai → quais chaves estão de fato conectadas
      const connectedEdges = parentEdges.filter(e => e.source === id)
      const connectedKeys = new Set<string>(
        connectedEdges.flatMap(e => {
          const fk = e.data?.from_key as string | undefined
          return fk ? [fk] : []
        })
      )
      return { id, node, status, alias, staticFields, connectedEdges, connectedKeys }
    }).filter(p => p.node !== undefined)
  }, [parentEdges, allNodes, statusWorkflow?.nodes])

  const statusColorMap = STATUS_COLOR_MAP
  const statusLabel = STATUS_LABEL

  const copyToClipboard = useCallback((text: string) => {
    navigator.clipboard.writeText(text)
  }, [])

  // Inicia drag com a expressão Jinja como texto
  const handleDragStart = useCallback((e: React.DragEvent, expression: string) => {
    e.dataTransfer.setData("text/plain", expression)
    e.dataTransfer.effectAllowed = "copy"
  }, [])

  // Coleta schema do nó pai para a aba Schema. Mescla:
  //   - os campos declarados no catálogo (nome + tipo + descrição)
  //   - output_keys observado em runtime (marca como "dinâmico" se não declarado)
  // Sem o merge, schema do nó sem campos declarados fica vazio mesmo que o
  // run real tenha entregado keys.
  const parentStaticOutputs = parentInfos.flatMap(({ alias, node, status }) => {
    const declared = saidasDoNo(node?.data).map(f => ({
      alias, name: f.name, type: f.type, description: f.description, dynamic: false,
    }))
    const declaredNames = new Set(declared.map(d => d.name))
    const runtimeOnly = (status?.output_keys ?? [])
      .filter(k => !declaredNames.has(k))
      .map(name => ({ alias, name, type: undefined, description: "Observado em runtime (não declarado no schema do nó)", dynamic: true }))
    return [...declared, ...runtimeOnly]
  })

  if (parentInfos.length === 0) {
    return (
      <div className="flex flex-col h-full gap-3 p-4">
        <div className="flex flex-col items-center justify-center gap-2 py-6 text-muted-foreground">
          <TbInbox size={28} />
          <p className="text-xs text-center">Nenhuma entrada conectada a este nó.</p>
        </div>

        {/* As portas que o nó DECLARA, mesmo sem nada ligado. Sem isto, quem
            acabou de configurá-las não tinha onde conferir os nomes — e são
            eles que viram as variáveis do script. */}
        {portasDeclaradas.length > 0 && (
          <div className="flex flex-col gap-1.5">
            <span className="text-[10px] text-muted-foreground uppercase tracking-wide">
              Entradas deste nó
            </span>
            {portasDeclaradas.map(porta => (
              <div key={porta} className="flex items-center gap-1.5 rounded-md border border-dashed px-2 py-1.5">
                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-muted-foreground/40"
                      title="Ainda sem conexão" />
                <code className="flex-1 font-mono text-[11px] text-foreground">{porta}</code>
              </div>
            ))}
            <p className="text-[10px] leading-relaxed text-muted-foreground">
              {isPythonNode
                ? "Cada uma vira uma variável com este nome dentro do script, quando algo for ligado nela."
                : "Ligue um nó a cada uma para que este receba os dados."}
            </p>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Tabs */}
      <div className="flex gap-1 px-4 pt-2">
        <button
          onClick={() => setTab("campos")}
          className={`px-2 py-1 rounded text-[11px] font-medium transition-colors ${
            tab === "campos" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted"
          }`}
        >
          Campos
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

      {/* Conteúdo da aba Campos */}
      {tab === "campos" && (
        <div className="flex flex-col gap-3 p-4">
          {parentInfos.map(({ id, status, alias, staticFields, connectedKeys, connectedEdges }) => {
            // Combina: status real > campos declarados > connectedKeys > fallback "output"
            const keys = new Set<string>()
            if (status?.output_keys) status.output_keys.forEach(k => keys.add(k))
            if (staticFields.length > 0) staticFields.forEach(k => keys.add(k))
            connectedKeys.forEach(k => keys.add(k))
            if (keys.size === 0) keys.add("output")
            const outputKeys = Array.from(keys)

            // O nome de chegada segue a mesma regra do executor
            // (`inputs[to_key if to_key else from_key]`). Antes o painel usava
            // sempre a chave do PAI — certo enquanto não havia portas nomeadas,
            // e mentira depois: mandava usar `output` quando a variável se
            // chamava `pontos`.
            //
            // Uma linha por ARESTA, e não por chave do pai: o mesmo pai pode
            // alimentar DUAS portas diferentes deste nó, e aí as duas arestas
            // carregam o mesmo `from_key`. Listando por chave, a segunda porta
            // ficava invisível — justamente no cenário que as portas criaram.
            const linhas = outputKeys.flatMap(key => {
              const daChave = connectedEdges.filter(e => (e.data?.from_key as string | undefined) === key)
              // Aresta sem `from_key` atende a qualquer chave (o executor espalha
              // todas as saídas do pai), mas o `to_key` dela, se houver, continua
              // sendo o nome de chegada.
              const semChave = connectedEdges.filter(e => !e.data?.from_key)
              const arestas = daChave.length ? daChave : semChave
              if (!arestas.length) return [{ key, variavel: key, linhaId: key }]
              return arestas.map(e => ({
                key,
                variavel: (e.data?.to_key as string | undefined) || key,
                linhaId: `${key}:${e.id}`,
              }))
            })

            return (
              <div key={id} className="flex flex-col gap-1.5 rounded-md border p-3 text-xs">
                {/* Header: alias + status */}
                <div className="flex items-center justify-between">
                  <span className="font-semibold truncate max-w-[160px]">{alias}</span>
                  {status && (
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${statusColorMap[status.status] ?? statusColorMap.idle}`}>
                      {statusLabel[status.status] ?? status.status}
                    </span>
                  )}
                </div>

                {status?.duration !== undefined && (
                  <span className="text-muted-foreground text-[10px]">
                    {status.duration.toFixed(0)}ms
                  </span>
                )}

                {/* Aviso de schema drift: backend detectou divergencia entre
                    os campos declarados no catálogo e o output real do nó. */}
                {status?.schema_drift && (status.schema_drift.missing.length > 0 || status.schema_drift.extra.length > 0) && (
                  <div className="text-[10px] text-yellow-700 bg-yellow-500/10 border border-yellow-500/30 rounded px-1.5 py-1 mt-1">
                    <span className="font-semibold">Schema divergente:</span>
                    {status.schema_drift.missing.length > 0 && (
                      <span className="ml-1">faltando {status.schema_drift.missing.join(", ")}</span>
                    )}
                    {status.schema_drift.extra.length > 0 && (
                      <span className="ml-1">extra {status.schema_drift.extra.join(", ")}</span>
                    )}
                  </div>
                )}

                {/* Output keys */}
                <div className="flex flex-col gap-1 mt-1">
                  <span className="text-[10px] text-muted-foreground uppercase tracking-wide">Saídas</span>
                  {linhas.map(({ key, variavel, linhaId }) => {
                    // Regra de visibilidade:
                    // - connectedKeys.size > 0 → edge com from_key explícito: só a chave
                    //   conectada é marcada como "fiada" (ponto verde + arrastável).
                    // - connectedKeys.size === 0 → edge sem from_key (auto-connect de nó
                    //   sem campos declarados): o executor espalha todos os outputs
                    //   do pai no namespace, portanto todas as chaves são acessíveis —
                    //   isWired = true para todas evita falsos negativos.
                    // - Chave observada em runtime via status.output_keys também conta
                    //   como wired: o executor entregou esse dado mesmo que a edge tenha
                    //   from_key específico em outra chave (espalhamento dinamico).
                    const isWired = (
                      connectedKeys.size === 0 ||
                      connectedKeys.has(key) ||
                      (status?.output_keys?.includes(key) ?? false)
                    )
                    // Para o Script Python o que se digita é a VARIÁVEL, então
                    // tem de ser o nome de chegada. Para os demais a expressão
                    // Jinja navega pela saída do pai, e a chave é a dele.
                    const expression = isPythonNode ? variavel : `{{ ${alias}.${key} }}`
                    return (
                      <div
                        key={linhaId}
                        draggable={isWired}
                        onDragStart={isWired ? (e) => handleDragStart(e, expression) : undefined}
                        title={isWired ? undefined : "Não conectado — adicione uma edge para usar esta chave"}
                        className={cn(
                          "flex items-center gap-1 group rounded px-1.5 py-1 transition-colors",
                          isWired
                            ? "cursor-grab active:cursor-grabbing hover:bg-muted"
                            : "opacity-40 cursor-default"
                        )}
                      >
                        {isWired
                          ? <TbGripVertical className="h-3 w-3 shrink-0 text-muted-foreground/50 group-hover:text-muted-foreground" />
                          : <span className="h-3 w-3 shrink-0" />
                        }
                        <code className="flex-1 text-[11px] font-mono text-foreground">
                          {key}
                          {variavel !== key && (
                            // A porta é o nome que importa para quem escreve o
                            // script; a chave do pai fica como procedência.
                            <span className="ml-1 text-muted-foreground">
                              &rarr; <span className="text-foreground">{variavel}</span>
                            </span>
                          )}
                        </code>
                        {isWired && (
                          <>
                            <span className="w-1.5 h-1.5 rounded-full bg-green-500 shrink-0" title="Conectado" />
                            <button
                              onClick={() => copyToClipboard(expression)}
                              // `coarse:`: sem hover o botão de copiar a expressão
                              // simplesmente não existia no telefone.
                              className="opacity-0 coarse:opacity-70 group-hover:opacity-100 transition-opacity ml-1"
                              title={`Copiar: ${expression}`}
                            >
                              <TbCopy className="h-3 w-3 text-muted-foreground hover:text-foreground" />
                            </button>
                          </>
                        )}
                      </div>
                    )
                  })}
                </div>

                {status?.error && (
                  <p className="text-destructive break-all text-[10px] mt-1">{status.error}</p>
                )}
              </div>
            )
          })}

          {(() => {
            const ligadas = new Set(
              parentEdges.map(e => (e.data?.to_key as string | undefined)).filter(Boolean) as string[],
            )
            const pendentes = portasDeclaradas.filter(p => !ligadas.has(p))
            if (!pendentes.length) return null
            // Com uma porta ligada e outra não, a lista de pais mostra só a
            // primeira — e a que falta ficava invisível justamente para quem
            // ainda precisa ligá-la.
            return (
              <div className="flex flex-col gap-1.5">
                <span className="text-[10px] text-muted-foreground uppercase tracking-wide">
                  Aguardando conexão
                </span>
                {pendentes.map(porta => (
                  <div key={porta} className="flex items-center gap-1.5 rounded-md border border-dashed px-2 py-1.5">
                    <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-muted-foreground/40" />
                    <code className="flex-1 font-mono text-[11px] text-muted-foreground">{porta}</code>
                  </div>
                ))}
              </div>
            )
          })()}

          <p className="text-[10px] text-muted-foreground mt-2">
            {isPythonNode
              ? <>Arraste ou clique em <TbCopy className="inline h-3 w-3" /> para copiar o nome da variável Python.</>
              : <>Arraste uma saída para um campo ou clique em <TbCopy className="inline h-3 w-3" /> para copiar a expressão Jinja.</>
            }
          </p>
        </div>
      )}

      {/* Conteúdo da aba Schema — campos estáticos dos nós pais */}
      {tab === "schema" && (
        <div className="flex flex-col gap-2 p-4">
          {parentStaticOutputs.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-4">
              Nenhum campo estático declarado nos nós de entrada.
            </p>
          ) : (
            <div className="flex flex-col gap-1">
              {parentStaticOutputs.map((field, i) => (
                <div key={`${field.alias}-${field.name}-${i}`} className="flex flex-col gap-0.5 rounded-md border p-2.5 text-xs">
                  <span className="text-[10px] text-muted-foreground/70 font-medium truncate">{field.alias}</span>
                  <div className="flex items-center gap-2">
                    <code className="px-1 py-0.5 rounded bg-muted text-foreground text-[11px] font-mono">{field.name}</code>
                    {field.type && (
                      <span className="text-muted-foreground text-[10px]">{field.type}</span>
                    )}
                    {field.dynamic && (
                      <span className="text-[9px] px-1 py-0.5 rounded bg-yellow-500/10 text-yellow-600 border border-yellow-500/30">
                        runtime
                      </span>
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

export default InputInspector
