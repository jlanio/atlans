"use client"

import { Handle, HandleProps, Position } from "@xyflow/react"
import { HTMLAttributes } from "react"
import { cn } from "@/lib/utils"
import { corDoTom, tomDoHandle } from "../../utils/exec-colors"

/**
 * Porta de um nó do canvas — o ponto de onde a aresta sai e onde ela chega.
 *
 * Nasceu de dois arquivos gêmeos de 17 linhas (`source.tsx` e `target.tsx`) que
 * divergiam justamente onde não deviam: a saída era um círculo de 6px e a
 * entrada um retângulo de 8×12, sem intenção declarada em lugar nenhum, e ambos
 * cravavam `!bg-white` — no tema escuro a porta virava o elemento de maior
 * contraste do canvas, mais forte que o título do nó.
 *
 * Aqui a forma diz a DIREÇÃO (saída é pino cheio, entrada é soquete vazado), o
 * traço diz o ESTADO (livre é tracejado) e a cor vem do mesmo vocabulário de
 * execução da aresta. As regras visuais moram em `globals.css`, sob
 * `.react-flow__handle.rf-handle`: é preciso especificidade maior que a do
 * próprio React Flow, e resolver isso com `!important` em classe utilitária era
 * o que impedia o chamador de sobrescrever qualquer coisa.
 */

export type DirecaoDaPorta = "saida" | "entrada"

interface PortaProps
  extends Omit<HandleProps, "type" | "position">,
    Omit<HTMLAttributes<HTMLDivElement>, "id"> {
  direcao: DirecaoDaPorta
  /** Porta sem aresta ligada.
   *
   *  Quem carregava essa informação era só o stub "+" ao lado, que o LOD esconde
   *  no zoom afastado — a informação sumia junto. */
  livre?: boolean
}

const Porta = ({ direcao, livre, className, style, ...props }: PortaProps) => {
  const saida = direcao === "saida"
  // `true`/`false` do Conditional nascem verde/vermelho e ASSIM FICAM: a porta
  // diz qual ramo ela é, e a aresta diz o que aconteceu com ele. Ver o
  // comentário de `--rf-handle-tom` em globals.css para o porquê de a porta não
  // acompanhar o status do nó.
  //
  // Só na SAÍDA: o mapa descreve ramos de roteamento, que são saídas do
  // Conditional. Aplicado à entrada, um nó de portas dinâmicas com uma entrada
  // chamada `true` ganharia um soquete verde anunciando um ramo que não existe.
  const ramo = saida ? tomDoHandle(props.id) : undefined

  return (
    <Handle
      {...props}
      type={saida ? "source" : "target"}
      position={saida ? Position.Right : Position.Left}
      data-livre={livre ? "true" : "false"}
      style={{
        ...(ramo ? ({ "--rf-handle-ramo": corDoTom(ramo) } as React.CSSProperties) : null),
        ...style,
      }}
      className={cn(
        // `z-10` vem dos dois arquivos que este substituiu, e não é decorativo:
        // `.exec-card` é `isolate`, e o `::after` que desenha o anel de execução
        // é gerado por último — em `z-index: auto` ele pinta POR CIMA das
        // portas, cortando cada uma ao meio durante um run.
        "rf-handle z-10",
        saida ? "rf-handle-saida" : "rf-handle-entrada",
        className,
      )}
    />
  )
}

/** Saída do nó — pino cheio, à direita. */
export const HandleSource = (props: Omit<PortaProps, "direcao">) => (
  <Porta {...props} direcao="saida" />
)

/** Entrada do nó — soquete vazado, à esquerda. */
export const HandleTarget = (props: Omit<PortaProps, "direcao">) => (
  <Porta {...props} direcao="entrada" />
)
