"use client"

// web/app/components/home/assistente/etapa.tsx
//
// O passo ATUAL da resposta, mostrado na barra do rodapé enquanto o assistente
// trabalha.
//
// **Por que existe.** A barra desce ao rodapé assim que a pessoa envia — antes
// do primeiro token de texto (ver o hero na HomeView). Durante o raciocínio e
// as chamadas de ferramenta (catálogo, WFS), que podem levar segundos, a barra
// ficaria sem dizer nada. Este indicador conta o que está acontecendo AGORA:
// "Pensando…", ou o rótulo da ferramenta em curso ("Consultando o guia · edges").
// A faixa (a `Pilha`) mostra a linha do tempo inteira; a barra mostra só o passo
// da vez, pertinho de onde a pessoa escreve.
//
// Os rótulos são os MESMOS do painel (`assistente/rotulos.ts` e `Passo`): o nome
// cru da ferramenta nunca vai para a tela.

import MarcaAnimada from "./marca-animada"
import { detalheDaChamada, rotuloDaFerramenta } from "@/app/components/home/assistente/rotulos"
import type { TurnoDoAssistente } from "@/app/components/home/assistente/quadros"
import { cn } from "@/lib/utils"
import { IDIOMA_PADRAO, type Idioma } from "@/lib/idioma"
import { textosDe } from "../i18n"

export interface Etapa {
  tipo: "pensando" | "ferramenta"
  rotulo: string
  detalhe?: string
}

/**
 * O passo atual, a partir dos turnos e do `correndo`.
 *
 * - Parado (`!correndo`) ou sem turno do assistente → `null`.
 * - Turno ainda sem bloco, último bloco de raciocínio, ou ferramenta já
 *   CONCLUÍDA (o modelo está digerindo o resultado) → "Pensando".
 * - Ferramenta EM CURSO → o rótulo dela, com o detalhe da chamada.
 * - Já escrevendo a resposta (último bloco de texto/cartão) → `null`: o texto
 *   aparece na faixa, e um "passo" ali seria ruído.
 */
export function etapaDaConversa(
  turnos: TurnoDoAssistente[],
  correndo: boolean,
  idioma: Idioma = IDIOMA_PADRAO,
): Etapa | null {
  if (!correndo) return null
  let ultimo: TurnoDoAssistente | undefined
  for (let i = turnos.length - 1; i >= 0; i--) {
    if (turnos[i].papel === "assistant") { ultimo = turnos[i]; break }
  }
  if (!ultimo) return null

  const bloco = ultimo.blocos[ultimo.blocos.length - 1]
  if (bloco?.tipo === "ferramenta" && bloco.estado === "correndo") {
    const detalhe = detalheDaChamada(bloco.argumentos)
    return { tipo: "ferramenta", rotulo: rotuloDaFerramenta(bloco.nome, idioma), detalhe: detalhe ?? undefined }
  }
  if (!bloco || bloco.tipo === "pensando" || bloco.tipo === "ferramenta") {
    return { tipo: "pensando", rotulo: textosDe(idioma).assistente.etapa.pensando }
  }
  return null
}

/** A linha do passo: a marca do site animada + o rótulo (o "…" varre no pensar). */
export function IndicadorDeEtapa({ etapa, className }: { etapa: Etapa; className?: string }) {
  return (
    <p
      role="status"
      aria-live="polite"
      data-testid="etapa-da-barra"
      className={cn("flex items-center gap-2 text-[12px] text-muted-foreground", className)}
    >
      <MarcaAnimada size={13} />
      {etapa.tipo === "pensando" ? (
        <span className="texto-pensando">{etapa.rotulo}…</span>
      ) : (
        <span className="min-w-0 truncate">
          {etapa.rotulo}
          {etapa.detalhe ? <span className="text-muted-foreground/70"> · {etapa.detalhe}</span> : null}
        </span>
      )}
    </p>
  )
}
