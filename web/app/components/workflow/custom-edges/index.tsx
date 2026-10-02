"use client"

import { useWorkflowExecutionStore } from "@/app/stores/workflowExecutionStore";
import { useTools } from "@/app/hooks/workflow/useTools";
import { cn } from "@/lib/utils";
import { EdgeProps, EdgeLabelRenderer, useStoreApi, getSmoothStepPath } from "@xyflow/react"
import { MdDelete } from "react-icons/md"
import { useState } from "react"
import { getLaneOffset } from "../utils/edge-bundling"
import { getCandidateKeys, sourceHandleDaChave } from "../utils/resolve-edge-keys"
import { corDoTom, tomDaAresta } from "../utils/exec-colors"
import { useSubflowReadOnly, useSubflowStatus } from "../subflow-viewer/scope"

// Handles de roteamento do Conditional. Só decide se o badge vira seletor de
// chave — a COR vem de `tomDaAresta`, que já conhece esses mesmos handles.
const HANDLE_DE_RAMO = new Set(["true", "false"])

const CustomEdge = ({
  id,
  source,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourceHandleId,
  sourcePosition,
  targetPosition,
  data,
}: EdgeProps) => {
  const [hovered, setHovered] = useState(false)
  const [editando, setEditando] = useState(false)
  const store = useStoreApi()
  const { toolState, handleToolState } = useTools()
  // Preenchidos só quando a aresta está sendo desenhada dentro do visualizador
  // de sub-fluxo — ver subflow-viewer/scope. Custo zero no editor: `useContext`
  // sem provider devolve o default literal e nunca re-renderiza.
  const noVisualizador = useSubflowReadOnly()
  const subflowStatus = useSubflowStatus()
  // Seletores escalares por id: assinar `statusWorkflow` (objeto novo a cada
  // mensagem do WS) re-renderizava TODAS as arestas visíveis, e cada uma ainda
  // reconstruía o próprio Map sobre a lista inteira de nós.
  const statusCanvas = useWorkflowExecutionStore(s => s.statusById.get(source)?.status)
  const emRamoPerdedor = useWorkflowExecutionStore(s => !!s.losingEdgeIds?.has(id))

  // Mesma regra do card (ver icon-root): dentro do visualizador o estado vem do
  // escopo. `statusById` só conhece os nós do canvas do editor — os ids do filho
  // chegam prefixados e não casam com nenhum, então a aresta do sub-fluxo lia o
  // status do nó do PAI que por acaso tivesse o mesmo id local.
  const sourceStatus = subflowStatus ? subflowStatus.get(source)?.status : statusCanvas
  // `losingEdgeIds` é calculado sobre as arestas do canvas do editor e não
  // conhece o grafo do filho — aplicá-lo aqui dentro tracejaria arestas por
  // coincidência de id.
  const isLosing = !noVisualizador && emRamoPerdedor

  // Faixa própria quando há mais de uma aresta ligando o mesmo par de nós.
  // `getState()` em vez de `useEdges()` de propósito: não cria uma subscription
  // por aresta, e o EdgeRenderer já re-renderiza este componente quando o array
  // de arestas muda.
  const lane = getLaneOffset(store.getState().edges, id)

  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    borderRadius: 10,
    centerX: (sourceX + targetX) / 2 + lane,
  })

  const handleKey = sourceHandleId ?? ""

  const color = corDoTom(tomDaAresta(sourceStatus, handleKey, isLosing))

  // Hover e execução deixam de compartilhar o mesmo efeito. Antes, passar o
  // mouse numa aresta PARADA durante um run a fazia parecer viva — o canal mais
  // forte do canvas ("dado passando") disparado por um gesto de leitura.
  const arestaAtiva = sourceStatus === "started" && !isLosing
  // Ramo rejeitado recua por tracejado + neutro + um pouco de opacidade. A
  // opacidade PROFUNDA continua reservada ao realce de caminho: os dois canais
  // se multiplicam, e exagerar aqui apagaria de vez uma aresta rejeitada que
  // esteja dentro do caminho em foco.
  const edgeOpacity = isLosing ? 0.45 : 0.85

  const label = (data?.from_key as string) ?? (handleKey || null)
  const isToolOpen = toolState !== "disable"

  // Saídas de dado do nó de origem. Só vale trocar quando há mais de uma — com
  // uma só não há escolha, e handles de roteamento (true/false) definem o ramo,
  // não o dado.
  // Sem useMemo de propósito: as deps seriam [store, source], que nunca mudam,
  // e a lista congelaria. Nós de porta dinâmica (SubWorkflow) alteram as saídas
  // depois do mount, e o seletor passaria a oferecer portas que não existem
  // mais. `getState()` não cria subscription e a chamada é O(portas).
  const candidatos = getCandidateKeys(
    store.getState().nodeLookup.get(source)?.data as Parameters<typeof getCandidateKeys>[0],
  )
  const podeTrocar = candidatos.length > 1 && !HANDLE_DE_RAMO.has(handleKey)

  const escolherChave = (nome: string) => {
    const atual = store.getState().edgeLookup.get(id)
    if (!atual) return
    // F9: em nó multi-saída a invariante é sourceHandle == from_key; trocar só o
    // from_key deixava source_handle (porta antiga) e from_key (porta nova) em
    // desacordo, e resolveSourceHandle (edge-persistence) reancorava a linha na
    // porta ANTIGA após reload.
    //
    // Mas só é porta REAL o que o nó desenha como handle — e isso é `outputs`
    // com 2+ saídas, nunca um campo sem `port`. Sincronizar o sourceHandle com
    // um campo sem ponto de conexão (que o seletor oferece via getCandidateKeys)
    // apontava a linha para um handle inexistente e o React Flow parava de
    // desenhá-la: a aresta SUMIA ao escolher a chave. `sourceHandleDaChave`
    // devolve `undefined` quando não há o que mexer; senão o handle nomeado ou
    // `null` (anônimo, que ainda limpa um handle fantasma já gravado).
    const saidas = (store.getState().nodeLookup.get(source)?.data as { outputs?: Array<{ name?: string }> } | undefined)?.outputs
    const novoHandle = sourceHandleDaChave(saidas, nome)
    // Emite como EdgeChange em vez de setEdges direto: é o que faz a troca
    // passar por `handleEdgesChange` no canvas e entrar no histórico de
    // undo/redo. Com setEdges, a alteração era persistida (o autosave observa
    // `edges`) mas Ctrl+Z não a desfazia.
    store.getState().triggerEdgeChanges([{
      id,
      type: "replace",
      item: {
        ...atual,
        sourceHandle: novoHandle === undefined ? atual.sourceHandle : novoHandle,
        data: { ...atual.data, from_key: nome },
      },
    }])
    setEditando(false)
  }

  return (
    <>
      <g style={{ "--exec-color": color } as React.CSSProperties}>
        {/* Brilho sob a linha ativa. Um traço largo e translúcido, e não um
            `filter: blur()`: filtro SVG por aresta é caro e cria surface
            própria. Vem PRIMEIRO porque no SVG quem é desenhado antes fica
            atrás. */}
        {arestaAtiva && (
          <path
            data-role="edge-glow"
            d={edgePath}
            fill="none"
            stroke="var(--exec-color)"
            strokeWidth={7}
            strokeLinecap="round"
            className="edge-glow-pulse"
            style={{ pointerEvents: "none" }}
          />
        )}

        {/* Aresta principal — losing branch ganha dash pattern explícito em
            vez de só opacidade, deixando claro que o ramo foi rejeitado em
            vez de parecer "ainda não executada". */}
        <path
          data-role="edge-path"
          d={edgePath}
          fill="none"
          stroke="var(--exec-color)"
          strokeWidth={hovered ? 2.5 : 1.5}
          strokeOpacity={edgeOpacity}
          strokeLinecap="round"
          strokeDasharray={isLosing ? "3 5" : undefined}
        />

        {/* Fluxo — traços marchando no sentido do dado.

            Ativa: duas correntes em paralaxe. Uma corrente só lê como um
            tracejado escorregando; duas de calibre e velocidade diferentes
            leem como tráfego. Os dasharray fecham exatamente o período do
            keyframe correspondente (3+8=11, 9+20=29), senão o laço salta.

            Sob o cursor: UMA corrente e sem brilho. Nítida o bastante para
            ensinar a direção, sem se passar por uma aresta viva. */}
        {arestaAtiva ? (
          <>
            <path
              data-role="edge-flow"
              d={edgePath}
              fill="none"
              stroke="var(--exec-color)"
              strokeWidth={1.4}
              strokeLinecap="round"
              strokeDasharray="3 8"
              className="edge-flow-fast"
              style={{ pointerEvents: "none" }}
            />
            <path
              data-role="edge-flow"
              d={edgePath}
              fill="none"
              stroke="var(--exec-color)"
              strokeWidth={2.6}
              strokeLinecap="round"
              strokeDasharray="9 20"
              className="edge-flow-slow"
              style={{ pointerEvents: "none" }}
            />
          </>
        ) : hovered && (
          <path
            data-role="edge-flow"
            d={edgePath}
            fill="none"
            stroke="var(--exec-color)"
            strokeWidth={2.4}
            strokeLinecap="round"
            strokeDasharray="6 12"
            className="edge-flow-hint"
            style={{ pointerEvents: "none" }}
          />
        )}

        {/* Área invisível de hover (para facilitar o clique/hover) */}
        <path
          d={edgePath}
          fill="none"
          stroke="transparent"
          strokeWidth={32}
          onMouseEnter={() => { setHovered(true); handleToolState("onFocus") }}
          onMouseLeave={() => { setHovered(false); handleToolState("leave") }}
          style={{ pointerEvents: "stroke", cursor: "pointer" }}
        />
      </g>

      <EdgeLabelRenderer>
        {/* Badge com o label (from_key ou true/false) — ponto médio da aresta.
            Com mais de um candidato ele vira botão: era o único jeito de
            corrigir a chave depois, já que antes escolher errado obrigava a
            apagar a aresta e refazer a conexão. No hover sobe uma linha para
            dar lugar ao botão de deletar, em vez de sumir. */}
        {(label || podeTrocar) && (
          <div
            data-edge-id={id}
            data-role="edge-label"
            className={cn(
              "absolute z-[20] transition-transform duration-150",
              podeTrocar ? "pointer-events-auto" : "pointer-events-none",
            )}
            style={{
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`
                + (isToolOpen ? " translateY(-16px)" : ""),
              // `EdgeLabelRenderer` é um portal: este div não está dentro do
              // <g> da aresta e não herdaria a variável de lá.
              "--exec-color": color,
            } as React.CSSProperties}
            onMouseEnter={() => { setHovered(true); handleToolState("onFocus") }}
            onMouseLeave={() => { setHovered(false); handleToolState("leave") }}
          >
            {podeTrocar ? (
              <button
                type="button"
                title="Trocar a saída que passa por esta aresta"
                onClick={() => setEditando(v => !v)}
                className="text-[10px] font-mono px-1 rounded cursor-pointer hover:brightness-125"
                // `color-mix` e não sufixo de alpha em hex: a cor agora é um
                // token (`var(--exec-*)`), e concatenar "22" nele não é cor.
                style={{
                  background: "color-mix(in oklch, var(--exec-color) 12%, transparent)",
                  color: "var(--exec-color)",
                  border: "1px solid color-mix(in oklch, var(--exec-color) 32%, transparent)",
                }}
              >
                {label || "escolher"} ▾
              </button>
            ) : (
              <span
                className="text-[10px] font-mono px-1 rounded"
                style={{
                  background: "color-mix(in oklch, var(--exec-color) 12%, transparent)",
                  color: "var(--exec-color)",
                  border: "1px solid color-mix(in oklch, var(--exec-color) 32%, transparent)",
                }}
              >
                {label}
              </span>
            )}

            {editando && (
              <div
                className="absolute left-1/2 top-full mt-1 -translate-x-1/2 z-[30] min-w-36
                           rounded-md border border-border bg-popover shadow-md overflow-hidden"
                onMouseLeave={() => setEditando(false)}
              >
                {candidatos.map(porta => (
                  <button
                    key={porta.name}
                    type="button"
                    onClick={() => escolherChave(porta.name)}
                    className={cn(
                      "block w-full text-left px-2 py-1 text-[11px] font-mono transition-colors",
                      porta.name === data?.from_key
                        ? "bg-accent text-accent-foreground"
                        : "hover:bg-accent/50",
                    )}
                  >
                    {porta.name}
                    {porta.description && (
                      <span className="block text-[9px] text-muted-foreground font-sans truncate">
                        {porta.description}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Botão de deletar — visível ao hover/ferramenta ativa */}
        <div
          data-edge-id={id}
          data-role="edge-delete"
          onMouseEnter={() => { setHovered(true); handleToolState("onFocus") }}
          onMouseLeave={() => { setHovered(false); handleToolState("leave") }}
          className={cn(
            "absolute transition-opacity duration-200",
            isToolOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
          )}
          style={{
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            pointerEvents: "all",
          }}
        >
          <button
            // Mesmo motivo da troca de chave: `setEdges` direto não gera
            // EdgeChange, então apagar uma aresta pelo botão nunca entrou no
            // histórico e Ctrl+Z não a trazia de volta.
            onClick={() => store.getState().triggerEdgeChanges([{ id, type: "remove" }])}
            className="group !pointer-events-auto bg-background/80 border border-border rounded-full p-0.5 shadow-sm hover:border-destructive transition-colors cursor-pointer"
          >
            <MdDelete size={13} className="group-hover:text-destructive text-muted-foreground transition-colors" />
          </button>
        </div>
      </EdgeLabelRenderer>
    </>
  )
}

export default CustomEdge
