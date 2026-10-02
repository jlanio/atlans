import { FieldLabel } from "./field-label"
import { Input } from "@/app/components/ui/input"
import { INodeContext } from "@/context/useFlowContext"
import ExpressionInput from "./expression-input"
import { useCallback, useState } from "react"
import type { FieldProps } from "./types"

type StringFieldProps = FieldProps<{
  nodeFound?: INodeContext
  /** Nomes de coluna vistos na última execução do nó anterior. Oferecidos
   *  abaixo do campo — clicar preenche. É dica, não validação: o fluxo pode ter
   *  mudado desde então, e escrever um nome fora da lista continua valendo. */
  sugestoes?: string[]
  /** true quando as sugestões vieram da re-hidratação de um run PERSISTIDO
   *  (não desta sessão): o rótulo troca para avisar que a lista pode ter
   *  mudado — afirmar "última execução" com dado antigo seria mentir. */
  sugestoesDesatualizadas?: boolean
  /** true quando o stat de origem veio truncado — o rótulo avisa "lista
   *  parcial" em vez de afirmar completude. */
  sugestoesParciais?: boolean
}>

const StringField = ({ field, values, setNodeField, nodeFound, sugestoes = [], sugestoesDesatualizadas = false, sugestoesParciais = false }: StringFieldProps) => {
  const currentValue = `${values?.[field.name] ?? ""}`
  const [dragOver, setDragOver] = useState(false)

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const text = e.dataTransfer.getData("text/plain")
    if (text) {
      // Concatena expressão ao valor atual (ou substitui se vazio)
      const newValue = currentValue ? `${currentValue} ${text}` : text
      setNodeField(field.name, newValue)
    }
  }, [currentValue, field.name, setNodeField])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = "copy"
    setDragOver(true)
  }, [])

  return (
    <div
      className={`flex flex-col gap-1 rounded transition-colors ${dragOver ? "bg-blue-50 dark:bg-blue-950 ring-2 ring-blue-400" : ""}`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={() => setDragOver(false)}
    >
      <FieldLabel field={field} />
      {nodeFound ? (
        // Sem `placeholder={field.description}`: era a MESMA frase que aparecia
        // no paragrafo abaixo, entao a descricao inteira era exibida duas vezes.
        // Placeholder deve ser um exemplo de valor, nao a documentacao do campo.
        <ExpressionInput
          id={field.name}
          value={currentValue}
          onChange={v => setNodeField(field.name, v)}
          nodeFound={nodeFound}
          placeholder={field.placeholder}
        />
      ) : (
        <Input
          id={field.name}
          onChange={e => setNodeField(field.name, e.target.value)}
          value={currentValue}
          placeholder={field.placeholder}
        />
      )}

      {sugestoes.length > 0 && (
        <div className="flex flex-wrap items-center gap-1">
          <span className="text-[11px] text-muted-foreground">
            {sugestoesDesatualizadas
              ? "Vistas em execução anterior (podem ter mudado)"
              : "Vistas na última execução"}
            {sugestoesParciais && " (lista parcial)"}:
          </span>
          {sugestoes.map(nome => (
            <button
              key={nome}
              type="button"
              onClick={() => setNodeField(field.name, nome)}
              className={`rounded border px-1.5 py-px font-mono text-[11px] transition-colors ${
                currentValue === nome
                  ? "border-primary/60 bg-primary/10 text-foreground"
                  : "border-dashed border-border text-muted-foreground hover:border-primary/50 hover:text-foreground"
              }`}
            >
              {nome}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default StringField
