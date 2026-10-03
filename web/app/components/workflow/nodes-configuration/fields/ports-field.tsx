"use client"

/**
 * Editor for the input ports of a node with dynamic inputs (Python Script).
 *
 * It is a FIELD, not a helper: node-config-form's `HELPER_MAP` replaces the
 * whole form, and here the Python code needs to stay visible next to the ports
 * — the names defined here are the variables of that code.
 *
 * Why this exists: the name that reaches the script comes from the edge's
 * `to_key`, and the editor only fills `to_key` when the target node declares
 * more than one port. A node without declared ports receives both edges on the
 * same key and loses one — the script complains about an undefined variable
 * without anything saying the other one was overwritten.
 */
import { useMemo } from "react"
import { TbPlus, TbTrash, TbInfoCircle, TbPlugConnected } from "react-icons/tb"

import { Input } from "@/app/components/ui/input"
import { Button } from "@/app/components/ui/button"
import { lerPortas, NOME_DE_PORTA } from "../../utils/node-ports"
import { FieldLabel } from "./field-label"
import type { FieldProps } from "./types"

/**
 * Notice for a port editor locked by connected edges.
 *
 * It lives here and is also used by the sub-workflow port editor: the reason
 * for the lock is the same in both, and so is the worst outcome. Changing the
 * ports with connected edges makes them point to a connection point that no
 * longer exists — they vanish from the canvas and keep executing, and with no
 * line drawn not even the delete button is reachable.
 */
export function LockedPortsNotice({ conexoes }: { conexoes: number }) {
  return (
    <p className="flex items-start gap-2 rounded-md border border-yellow-500/40 bg-yellow-500/5 px-3 py-2 text-xs leading-relaxed text-muted-foreground">
      <TbPlugConnected size={14} className="mt-px shrink-0 text-yellow-500" />
      <span>
        {conexoes === 1 ? "Há 1 conexão" : `Há ${conexoes} conexões`}{" "}
        chegando a este nó. Desconecte antes de mudar as portas — senão as
        ligações existentes ficariam apontando para portas que não existem mais.
      </span>
    </p>
  )
}

type PortsFieldProps = FieldProps<{
  /** How many edges arrive at this node — the editor locks while there is any. */
  conexoesDeEntrada?: number
}>

const PortsField = ({ field, values, setNodeField, conexoesDeEntrada = 0 }: PortsFieldProps) => {
  const portas = useMemo(() => lerPortas(values?.[field.name]), [values, field.name])
  const travado = conexoesDeEntrada > 0

  // Stored as JSON: `setNodeField` only accepts string/number/boolean, and the
  // property travels as a single value in the workflow definition.
  const gravar = (proximo: string[]) => setNodeField(field.name, JSON.stringify(proximo))

  function adicionar() {
    let nome = "entrada"
    let n = 1
    while (portas.includes(nome)) nome = `entrada_${n++}`
    gravar([...portas, nome])
  }

  const duplicates = useMemo(() => {
    const vistas = new Set<string>()
    const dup = new Set<string>()
    for (const p of portas) (vistas.has(p) ? dup : vistas).add(p)
    return dup
  }, [portas])

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <FieldLabel field={field} htmlFor={null} />
        <Button
          type="button" size="sm" variant="outline" className="h-7 gap-1 text-xs"
          onClick={adicionar} disabled={travado}
        >
          <TbPlus size={13} /> Adicionar
        </Button>
      </div>

      {travado && <LockedPortsNotice conexoes={conexoesDeEntrada} />}

      {portas.length === 0 ? (
        <p className="flex items-start gap-2 text-xs leading-relaxed text-muted-foreground">
          <TbInfoCircle size={14} className="mt-px shrink-0" />
          <span>
            Sem portas, o nó aceita uma conexão e a variável recebe o nome da
            saída do nó anterior. Defina <strong className="font-medium text-foreground">duas ou mais</strong>{" "}
            para receber entradas separadas, cada uma com o nome que você der.
          </span>
        </p>
      ) : (
        <div className="flex flex-col gap-1.5">
          {portas.map((porta, i) => {
            const invalida = porta !== "" && !NOME_DE_PORTA.test(porta)
            const hasSpace = /\s/.test(porta)
            return (
              <div key={i} className="flex flex-col gap-0.5">
                <div className="flex items-center gap-1.5">
                  <Input
                    value={porta}
                    disabled={travado}
                    placeholder="ex: pontos"
                    className="h-8 font-mono text-sm"
                    onChange={e => {
                      // No `trim`: cutting the space here made it vanish while
                      // the person typed, as if the key didn't work, and the
                      // warning below never saw the value to explain why.
                      const proximo = portas.slice()
                      proximo[i] = e.target.value
                      gravar(proximo)
                    }}
                  />
                  <Button
                    type="button" size="icon" variant="ghost" disabled={travado}
                    className="h-8 w-8 shrink-0 text-muted-foreground hover:text-destructive"
                    title="Remover esta porta"
                    onClick={() => gravar(portas.filter((_, j) => j !== i))}
                  >
                    <TbTrash size={14} />
                  </Button>
                </div>
                {invalida && (
                  // The name becomes a VARIABLE inside the script: a space or an
                  // accent would produce a SyntaxError in the middle of the
                  // user's code, far from the cause. The space gets its own
                  // message for being the common case and the only one with an
                  // obvious fix to suggest.
                  <span className="text-[10px] text-destructive">
                    {hasSpace
                      ? "Espaços não são aceitos — use _ para separar palavras (ex: meus_pontos)."
                      : "Só letras, números e _ — o nome vira uma variável no script."}
                  </span>
                )}
                {duplicates.has(porta) && (
                  <span className="text-[10px] text-destructive">
                    Nome repetido: uma das entradas sobrescreveria a outra.
                  </span>
                )}
              </div>
            )
          })}
          {portas.length === 1 && (
            <span className="text-[10px] text-muted-foreground">
              Com uma porta só, nomear não muda nada — o ponto de conexão segue
              único e sem nome.
            </span>
          )}
        </div>
      )}
    </div>
  )
}

export default PortsField
