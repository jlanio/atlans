import { NodesDrawerState, useWorkflowCatalogStore } from "@/app/stores/workflowCatalogStore"
import { descricaoDoTipo, estiloDoTipo, nomeDoTipo } from "@/consts/NodeTypeStyles"
import { cn } from "@/lib/utils"
import IconDrawer from "./components/icon-drawer"

// Rótulo, descrição e cor saem todos de `consts/NodeTypeStyles`. Este arquivo
// mantinha uma terceira tabela própria (a segunda dentro do drawer), e ela
// discordava do canvas nos mesmos quatro tipos — e do drawer de nós em um: aqui
// "Fontes", lá "Fontes de dados".

const OptionsDrawer = () => {
  const nodesAPI = useWorkflowCatalogStore(s => s.nodesAPI)
  const setNodesDrawerState = useWorkflowCatalogStore(s => s.setNodesDrawerState)
  const uniqueType = [...new Set(nodesAPI.map(n => n.type as string))]

  function handleDrawerState(state: NodesDrawerState) {
    setNodesDrawerState(state)
  }

  return (
    <div className="p-3 grid grid-cols-2 gap-2">
      {uniqueType.map((type) => {
        const estilo = estiloDoTipo(type)
        const count = nodesAPI.filter(n => n.type === type).length

        return (
          <button
            key={type}
            onClick={() => handleDrawerState(type as NodesDrawerState)}
            className={cn(
              "group flex flex-col items-start gap-2 p-3 rounded-xl border border-border bg-card",
              "cursor-pointer text-left transition-colors duration-150",
              "hover:bg-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
            )}
          >
            {/* A faixa de cor do tipo — a mesma que marca o card no canvas —
                fica no ladrilho do ícone, e não na borda do cartão: na borda ela
                competia com o `focus-visible` e sumia no tema escuro, onde o
                `border` já é quase transparente. */}
            <div className={cn("p-2 rounded-lg", estilo.bg)}>
              <IconDrawer type={type} fontSize={16} className={estilo.icon} />
            </div>
            <div className="flex flex-col gap-0.5 w-full">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-semibold text-foreground truncate">{nomeDoTipo(type)}</span>
                <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground shrink-0 tabular-nums">
                  {count}
                </span>
              </div>
              <span className="text-[11px] text-muted-foreground leading-tight">
                {descricaoDoTipo(type)}
              </span>
            </div>
          </button>
        )
      })}
    </div>
  )
}

export default OptionsDrawer
