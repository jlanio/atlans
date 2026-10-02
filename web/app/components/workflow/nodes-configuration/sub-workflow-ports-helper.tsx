"use client"

/**
 * SubWorkflowPortsHelper — editor de portas declaradas em SubWorkflowInput
 * e SubWorkflowOutput.
 *
 * O modelo de contrato e declarativo via property `ports` (lista de strings).
 * Cada chave nesta lista vira:
 *   - uma entrada na lista de inputs/outputs do contrato (extract_contract)
 *   - uma chave que o pai precisa fornecer/recebera ao chamar este sub-fluxo
 *
 * `ports` e OPCIONAL (contrato opt-in):
 *   - vazio      -> passthrough: aceita/expoe todas as chaves
 *   - preenchido -> allowlist estrita, aplicada NOS DOIS lados. Chave que
 *                   chega fora da lista e descartada (com aviso no log).
 *
 * Cada edge que sai do SubWorkflowInput espalha o dict de entrada no seu
 * proprio destino — por isso ele pode alimentar VARIOS nodes.
 *
 * No SubWorkflowOutput as portas declaradas viram pontos de conexao: a partir
 * de duas, o editor preenche o `to_key` de cada edge com o nome da porta e cada
 * origem cai na sua chave. Sem portas, sobra um ponto anonimo e apenas UMA edge
 * e aceita — duas disputariam as mesmas chaves, e a ultima venceria.
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
  /** Arestas chegando a este nó. Só importa na saída: lá as portas são pontos
   *  de conexão, e mexer nelas com aresta ligada deixaria a aresta apontando
   *  para um ponto que não existe mais. Na entrada as portas não são handles —
   *  o nó é um gatilho e nada chega nele.
   *
   *  Sem valor padrão: um default silencioso faria o editor destravar sozinho
   *  se alguém esquecesse de ligar a contagem no formulário. */
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
  // Identificador "saudavel": comeca com letra/underscore, segue com
  // letra/digito/underscore. Evita chaves com espacos/acentos que quebram
  // ao referenciar de outros nodes.
  return /^[A-Za-z_][A-Za-z0-9_]*$/.test(key)
}


/**
 * Nome sob o qual o node SubWorkflow devolve o dict INTEIRO do sub-fluxo ao pai,
 * ao lado das chaves individuais.
 *
 * Uma porta de saída com este nome sobrescreveria o envelope: quem no pai lesse
 * `subWorkflowResult` receberia o valor daquela porta em vez do conjunto — sem
 * erro, com o dado errado. O executor recusa o fluxo; aqui o operador vê o
 * motivo enquanto digita, em vez de descobrir na hora de rodar.
 */
export const PORTA_RESERVADA = "subWorkflowResult"


/** Por que esta porta não serve — ou `null` se serve. */
export function problemaNaPorta(
  porta: string,
  variant: "input" | "output",
  duplicada: boolean,
): string | null {
  // Antes do caso geral: espaço é o erro mais comum (a pessoa escreve o nome
  // como escreveria uma frase) e o único com uma correção óbvia a sugerir.
  if (/\s/.test(porta)) {
    return "Espaços não são aceitos — use underscore para separar palavras (ex: minha_porta)."
  }
  if (porta !== "" && !isValidKey(porta)) {
    return "Use apenas letras, dígitos e underscore (começando por letra ou _)."
  }
  if (duplicada) return "Chave duplicada."
  // O node descarta toda chave começada por `__` ANTES de aplicar a allowlist
  // (são os metadados internos do executor). Uma porta assim nunca recebe nada
  // e nem entra na lista de descartes do log: some sem deixar rastro.
  if (porta.startsWith("__")) {
    return "Nomes começados por __ são reservados ao executor e nunca chegam ao pai."
  }
  // Só na saída: é o valor de retorno que colide com o envelope. Na entrada o
  // nome não chega ao pai.
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
    // Sem `trim`: cortar o espaço aqui o fazia sumir enquanto a pessoa digitava,
    // como se a tecla não funcionasse — e a validação, que já sabe recusá-lo,
    // nunca chegava a ver o valor para explicar o motivo. Guardar o que foi
    // digitado é o que permite dizer o que está errado.
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
        // Contrato é opt-in: lista vazia é modo passthrough válido, não erro.
        // O aviso anterior ("adicione ao menos uma") contradizia essa regra e
        // empurrava o operador a declarar portas em sub-fluxos de uso único.
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
