"use client"

import { useState } from "react"
import { Input } from "@/app/components/ui/input"
import { Button } from "@/app/components/ui/button"
import { TbPlus, TbTrash } from "react-icons/tb"
import { FieldLabel } from "./field-label"
import type { FieldProps } from "./types"

/**
 * Editor de pares chave/valor — cabeçalhos HTTP, query string e afins.
 *
 * O `ObjectField` (editor de árvore JSON) continua certo para estruturas
 * aninhadas, mas cabeçalho não é estrutura: é uma lista rasa de duas colunas.
 * Naquele editor, escrever `Content-Type: application/json` custa navegar uma
 * árvore, escolher o tipo do valor e confirmar — para um dado que o usuário já
 * sabe digitar de cor. Aqui são dois campos e um botão.
 *
 * O valor persistido continua sendo o MESMO objeto de antes; muda só a forma de
 * editá-lo. Trocar o tipo do campo no schema não migra nada e não invalida
 * workflow salvo.
 */

type KeyValueFieldProps = FieldProps

/** Aceita objeto ou string JSON — o valor salvo pode vir das duas formas. */
function paraObjeto(bruto: unknown): Record<string, string> {
  if (bruto && typeof bruto === "object") return bruto as Record<string, string>
  if (typeof bruto === "string" && bruto.trim()) {
    try {
      const lido = JSON.parse(bruto)
      if (lido && typeof lido === "object") return lido as Record<string, string>
    } catch { /* string inválida vira objeto vazio, como no editor antigo */ }
  }
  return {}
}

/** Pares na ordem em que estão no objeto salvo, com o valor sempre string. */
function paraPares(objeto: Record<string, string>): [string, string][] {
  return Object.entries(objeto).map(([k, v]) => [k, String(v ?? "")])
}

const KeyValueField = ({ field, values, setNodeField }: KeyValueFieldProps) => {

  const objeto = paraObjeto(values?.[field.name])
  const assinatura = JSON.stringify(objeto)

  // As linhas vivem em ESTADO LOCAL, e não derivadas do objeto salvo.
  //
  // O objeto não admite chave vazia — e é justamente uma linha de chave vazia
  // que uma linha recém-criada é. Enquanto a lista era recalculada do valor
  // salvo, o `Adicionar` gravava a linha em branco, a gravação a descartava, o
  // componente re-renderizava a partir do valor salvo e a linha não aparecia:
  // o botão simplesmente não fazia nada, e `headers` e `params` do HttpRequest
  // eram impreenchíveis pela interface. Pelo mesmo motivo, limpar o nome para
  // renomear um cabeçalho apagava a linha inteira no meio da edição.
  const [pares, setPares] = useState<[string, string][]>(() => paraPares(objeto))

  // Semente: a última forma do objeto que ESTE componente conhece. O caminho é
  // controlado (o modal devolve o que gravamos, sem estado próprio), então sem
  // essa marca toda tecla digitada voltaria como "mudou de fora" e derrubaria a
  // linha sem nome que o usuário está preenchendo. Quando a diferença é real —
  // outro nó selecionado, valor reposto de fora — as linhas são resemeadas.
  const [semente, setSemente] = useState(assinatura)
  if (assinatura !== semente) {
    setSemente(assinatura)
    setPares(paraPares(objeto))
  }

  function gravar(novosPares: [string, string][]) {
    setPares(novosPares)
    const saida: Record<string, string> = {}
    for (const [chave, valor] of novosPares) {
      const limpa = chave.trim()
      // Linha sem nome fica na tela, mas não vira cabeçalho: o valor que sai do
      // componente continua sendo só o que dá para enviar.
      if (limpa) saida[limpa] = valor
    }
    setSemente(JSON.stringify(saida))
    setNodeField(field.name, saida as unknown as string)
  }

  function alterar(indice: number, coluna: 0 | 1, texto: string) {
    const copia = pares.map(p => [...p] as [string, string])
    copia[indice][coluna] = texto
    gravar(copia)
  }

  function remover(indice: number) {
    gravar(pares.filter((_, i) => i !== indice))
  }

  function adicionar() {
    gravar([...pares, ["", ""]])
  }

  return (
    <div>
      <FieldLabel field={field} htmlFor={null} />

      <div className="flex flex-col gap-1.5">
        {pares.length === 0 && (
          <p className="text-xs text-muted-foreground py-1">
            Nenhum item. Use o botão abaixo para adicionar.
          </p>
        )}

        {pares.map(([chave, valor], i) => (
          <div key={i} className="flex items-center gap-1.5">
            <Input
              value={chave}
              onChange={e => alterar(i, 0, e.target.value)}
              placeholder="Nome"
              className="h-8 text-xs font-mono flex-1 min-w-0"
              aria-label={`Nome do item ${i + 1}`}
            />
            <Input
              value={String(valor ?? "")}
              onChange={e => alterar(i, 1, e.target.value)}
              placeholder="Valor"
              className="h-8 text-xs font-mono flex-1 min-w-0"
              aria-label={`Valor do item ${i + 1}`}
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => remover(i)}
              className="h-8 w-8 shrink-0 text-muted-foreground hover:text-destructive"
              aria-label={`Remover item ${i + 1}`}
            >
              <TbTrash size={14} />
            </Button>
          </div>
        ))}

        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={adicionar}
          className="h-8 gap-1.5 self-start"
        >
          <TbPlus size={14} />
          Adicionar
        </Button>
      </div>
    </div>
  )
}

export default KeyValueField
