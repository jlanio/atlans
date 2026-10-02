"use client"

/**
 * Editor das portas de entrada de um nó de entradas dinâmicas (Script Python).
 *
 * É um CAMPO, e não um helper: o `HELPER_MAP` do node-config-form substitui o
 * formulário inteiro, e aqui o código Python precisa continuar visível ao lado
 * das portas — os nomes que se define aqui são as variáveis daquele código.
 *
 * Por que isto existe: o nome que chega ao script vem do `to_key` da aresta, e o
 * editor só preenche `to_key` quando o nó de destino declara mais de uma porta.
 * Um nó sem portas declaradas recebe as duas arestas na mesma chave e perde uma
 * — o script reclama de uma variável indefinida sem nada dizer que a outra foi
 * sobrescrita.
 */
import { useMemo } from "react"
import { TbPlus, TbTrash, TbInfoCircle, TbPlugConnected } from "react-icons/tb"

import { Input } from "@/app/components/ui/input"
import { Button } from "@/app/components/ui/button"
import { lerPortas, NOME_DE_PORTA } from "../../utils/node-ports"
import { FieldLabel } from "./field-label"
import type { FieldProps } from "./types"

/**
 * Aviso de editor de portas travado por arestas ligadas.
 *
 * Vive aqui e é usado também pelo editor de portas do sub-fluxo: o motivo do
 * bloqueio é o mesmo nos dois, e o pior desfecho também. Mudar as portas com
 * arestas ligadas as faz apontar para um ponto de conexão que deixou de
 * existir — elas somem do canvas e continuam executando, e sem linha desenhada
 * nem o botão de excluir é alcançável.
 */
export function AvisoPortasTravadas({ conexoes }: { conexoes: number }) {
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
  /** Quantas arestas chegam a este nó — o editor trava enquanto houver alguma. */
  conexoesDeEntrada?: number
}>

const PortsField = ({ field, values, setNodeField, conexoesDeEntrada = 0 }: PortsFieldProps) => {
  const portas = useMemo(() => lerPortas(values?.[field.name]), [values, field.name])
  const travado = conexoesDeEntrada > 0

  // Guardado como JSON: `setNodeField` só aceita string/number/boolean, e a
  // propriedade viaja como valor único na definition do workflow.
  const gravar = (proximo: string[]) => setNodeField(field.name, JSON.stringify(proximo))

  function adicionar() {
    let nome = "entrada"
    let n = 1
    while (portas.includes(nome)) nome = `entrada_${n++}`
    gravar([...portas, nome])
  }

  const duplicadas = useMemo(() => {
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

      {travado && <AvisoPortasTravadas conexoes={conexoesDeEntrada} />}

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
            const temEspaco = /\s/.test(porta)
            return (
              <div key={i} className="flex flex-col gap-0.5">
                <div className="flex items-center gap-1.5">
                  <Input
                    value={porta}
                    disabled={travado}
                    placeholder="ex: pontos"
                    className="h-8 font-mono text-sm"
                    onChange={e => {
                      // Sem `trim`: cortar o espaço aqui o fazia sumir enquanto
                      // a pessoa digitava, como se a tecla não funcionasse, e o
                      // aviso abaixo nunca via o valor para explicar o motivo.
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
                  // O nome vira VARIÁVEL dentro do script: espaço ou acento
                  // produziriam um SyntaxError no meio do código do usuário,
                  // longe da causa. O espaço ganha mensagem própria por ser o
                  // caso comum e o único com uma correção óbvia a sugerir.
                  <span className="text-[10px] text-destructive">
                    {temEspaco
                      ? "Espaços não são aceitos — use _ para separar palavras (ex: meus_pontos)."
                      : "Só letras, números e _ — o nome vira uma variável no script."}
                  </span>
                )}
                {duplicadas.has(porta) && (
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
