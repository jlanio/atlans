"use client"

/**
 * SubWorkflowPortsHelper — editor for the ports declared in SubWorkflowInput
 * and SubWorkflowOutput.
 *
 * The contract model is declarative via the `ports` property (list of strings).
 * Each key in this list becomes:
 *   - an entry in the contract's inputs/outputs list (extract_contract)
 *   - a key the parent must provide/will receive when calling this sub-workflow
 *
 * `ports` is OPTIONAL (opt-in contract):
 *   - empty      -> passthrough: accepts/exposes every key
 *   - filled     -> strict allowlist, applied on BOTH sides. A key that
 *                   arrives outside the list is dropped (with a log warning).
 *
 * Each edge leaving SubWorkflowInput spreads the input dict into its own
 * target — which is why it can feed SEVERAL nodes.
 *
 * In SubWorkflowOutput the declared ports become connection points: from two
 * on, the editor fills each edge's `to_key` with the port name and each
 * source lands in its own key. With no ports, a single anonymous point is left
 * and only ONE edge is accepted — two would compete for the same keys, and the
 * last one would win.
 */
import { useMemo } from "react"
import { Label } from "@/app/components/ui/label"
import { Input } from "@/app/components/ui/input"
import { Button } from "@/app/components/ui/button"
import { TbPlus, TbTrash, TbInfoCircle } from "react-icons/tb"
import { AvisoPortasTravadas } from "./fields/ports-field"


interface Props {
  values: Record<string, string | number | boolean | object> | undefined
  setNodeField: (field: string, value: string | number | boolean) => void
  hasUnsaved: boolean
  variant: "input" | "output"
  /** Edges arriving at this node. Only matters on the output side: there the
   *  ports are connection points, and changing them with an edge attached
   *  would leave the edge pointing at a point that no longer exists. On the
   *  input side the ports are not handles — the node is a trigger and nothing
   *  arrives at it.
   *
   *  No default value: a silent default would unlock the editor on its own if
   *  someone forgot to wire the count in the form. */
  conexoesDeEntrada: number
}


function parsePorts(raw: unknown): string[] {
  if (Array.isArray(raw)) {
    return raw.filter((x): x is string => typeof x === "string")
  }
  if (typeof raw === "string") {
    try {
      const parsed = JSON.parse(raw)
      return Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === "string") : []
    } catch {
      return []
    }
  }
  return []
}


function isValidKey(key: string): boolean {
  // "Healthy" identifier: starts with a letter/underscore, continues with
  // letter/digit/underscore. Avoids keys with spaces/accents that break
  // when referenced from other nodes.
  return /^[A-Za-z_][A-Za-z0-9_]*$/.test(key)
}


/**
 * Name under which the SubWorkflow node returns the sub-workflow's ENTIRE dict
 * to the parent, alongside the individual keys.
 *
 * An output port with this name would overwrite the envelope: whoever in the
 * parent read `subWorkflowResult` would get that port's value instead of the
 * whole set — no error, wrong data. The executor rejects the workflow; here the
 * operator sees the reason while typing, instead of finding out at run time.
 */
export const PORTA_RESERVADA = "subWorkflowResult"


/** Why this port is not valid — or `null` if it is. */
export function problemaNaPorta(
  porta: string,
  variant: "input" | "output",
  duplicada: boolean,
): string | null {
  // Before the general case: a space is the most common mistake (people write
  // the name the way they would write a sentence) and the only one with an
  // obvious fix to suggest.
  if (/\s/.test(porta)) {
    return "Espaços não são aceitos — use underscore para separar palavras (ex: minha_porta)."
  }
  if (porta !== "" && !isValidKey(porta)) {
    return "Use apenas letras, dígitos e underscore (começando por letra ou _)."
  }
  if (duplicada) return "Chave duplicada."
  // The node drops every key starting with `__` BEFORE applying the allowlist
  // (they are the executor's internal metadata). A port like that never receives
  // anything and does not even show up in the log's drop list: it vanishes
  // without a trace.
  if (porta.startsWith("__")) {
    return "Nomes começados por __ são reservados ao executor e nunca chegam ao pai."
  }
  // Output side only: it is the return value that collides with the envelope.
  // On the input side the name never reaches the parent.
  if (variant === "output" && porta === PORTA_RESERVADA) {
    return `"${PORTA_RESERVADA}" é reservado: é o nome sob o qual o pai recebe o resultado inteiro do sub-fluxo.`
  }
  return null
}


export default function SubWorkflowPortsHelper({
  values, setNodeField, variant, conexoesDeEntrada,
}: Props) {
  const ports = useMemo(() => parsePorts(values?.ports), [values?.ports])

  const isInput = variant === "input"
  const travado = !isInput && conexoesDeEntrada > 0
  const label = isInput ? "Portas de entrada" : "Portas de saída"
  const placeholder = isInput ? "ex: geometry" : "ex: result_geometry"
  const helpText = isInput
    ? "Cada porta é uma chave que o workflow chamador (pai) pode fornecer. Chaves fora desta lista não chegam ao sub-fluxo."
    : "Cada porta é uma chave devolvida ao workflow chamador (pai). A partir de duas, cada uma vira um ponto de conexão próprio e recebe a sua origem."

  function commit(next: string[]) {
    setNodeField("ports", JSON.stringify(next))
  }

  function addPort() {
    const base = "porta"
    let candidate = base
    let n = 1
    while (ports.includes(candidate)) {
      candidate = `${base}_${n++}`
    }
    commit([...ports, candidate])
  }

  function renamePort(index: number, newName: string) {
    // No `trim`: cutting the space here made it vanish while the person typed,
    // as if the key did not work — and the validation, which already knows to
    // reject it, never got to see the value to explain why. Keeping what was
    // typed is what makes it possible to say what is wrong.
    const next = ports.slice()
    next[index] = newName
    commit(next)
  }

  function removePort(index: number) {
    const next = ports.slice()
    next.splice(index, 1)
    commit(next)
  }

  const duplicates = useMemo(() => {
    const seen = new Set<string>()
    const dup = new Set<string>()
    for (const p of ports) {
      if (seen.has(p)) dup.add(p)
      else seen.add(p)
    }
    return dup
  }, [ports])

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <Label className="text-xs">{label}</Label>
        <Button
          variant="outline" size="sm" className="h-7 text-[11px]"
          onClick={addPort} disabled={travado}
        >
          <TbPlus className="mr-1" /> Adicionar porta
        </Button>
      </div>

      <p className="text-[11px] text-muted-foreground">{helpText}</p>

      {travado && <AvisoPortasTravadas conexoes={conexoesDeEntrada} />}

      {ports.length === 0 ? (
        // The contract is opt-in: an empty list is a valid passthrough mode, not an
        // error. The previous warning ("adicione ao menos uma", add at least
        // one) contradicted that rule and pushed the operator into declaring
        // ports in single-use sub-workflows.
        <div className="rounded-md border border-border bg-muted/30 p-2.5 text-xs flex items-start gap-2">
          <TbInfoCircle className="text-muted-foreground shrink-0 mt-0.5" />
          <span>
            Sem portas declaradas —{" "}
            <strong className="text-foreground">
              {isInput ? "aceita todas as chaves enviadas pelo pai" : "devolve todas as chaves recebidas"}
            </strong>
            . Declare portas para fixar a interface quando o sub-fluxo for reutilizado
            por vários workflows.
          </span>
        </div>
      ) : (
        <div className="rounded-md border border-border overflow-hidden">
          <table className="w-full text-xs">
            <thead className="bg-muted/40">
              <tr>
                <th className="text-left px-2 py-1.5 font-medium text-muted-foreground w-8">#</th>
                <th className="text-left px-2 py-1.5 font-medium text-muted-foreground">Nome da chave</th>
                <th className="px-2 py-1.5 w-8" />
              </tr>
            </thead>
            <tbody>
              {ports.map((port, i) => {
                const problema = problemaNaPorta(port, variant, duplicates.has(port))
                return (
                  <tr key={i} className="border-t border-border">
                    <td className="px-2 py-1.5 text-muted-foreground">{i + 1}</td>
                    <td className="px-2 py-1.5">
                      <Input
                        value={port}
                        onChange={(e) => renamePort(i, e.target.value)}
                        placeholder={placeholder}
                        disabled={travado}
                        className={`h-7 text-xs font-mono ${
                          problema ? "border-destructive focus-visible:ring-destructive" : ""
                        }`}
                      />
                      {problema && (
                        <p className="text-[10px] text-destructive mt-0.5">{problema}</p>
                      )}
                    </td>
                    <td className="px-2 py-1.5">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 text-muted-foreground hover:text-destructive"
                        onClick={() => removePort(i)}
                        disabled={travado}
                        title="Remover porta"
                      >
                        <TbTrash className="text-xs" />
                      </Button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="rounded-md border border-border bg-muted/30 p-2.5 text-[11px] text-muted-foreground">
        {isInput ? (
          <>
            <strong>Roteamento interno:</strong> conecte este node a <em>quantos</em> nodes
            precisar — cada conexão entrega o mesmo dict de entrada ao seu destino, com
            todas as chaves declaradas juntas.
          </>
        ) : (
          <>
            <strong>Roteamento interno:</strong> com <em>duas ou mais</em> portas, cada
            uma é um ponto de conexão separado — ligue um node em cada e o valor de
            cada origem vai para a sua chave. Sem portas declaradas, o node aceita
            <em>uma</em> conexão só e devolve tudo que chegar: duas arestas
            disputariam as mesmas chaves e a última venceria.
          </>
        )}
      </div>
    </div>
  )
}
