"use client"

// web/app/components/home/assistente/pilha.tsx
//
// A conversa AO CENTRO: uma FAIXA colada à barra, a legenda do globo. Mostra só
// a última troca — a pergunta numa linha e, da resposta, o que ficou (o último
// texto cortado em 4 linhas, os erros, os cartões) e o que está vivo (o passo
// em curso) —, para ocupar pouco da tela e deixar o globo à vista. Nada rola
// nem desliza: o texto só troca, com um fade de entrada (`.home-pilha` em
// globals.css). É a MESMA conversa do painel lateral — os mesmos turnos, a
// mesma `Conversa` (em `compacta`), os mesmos cartões (`useExtrasDoAssistente`)
// — recortada aos últimos itens. Quem quer ler tudo (raciocínio, passos,
// textos inteiros) expande para a lateral, pelo botão, pelo chevron da barra
// ou por Ctrl+I; o painel tem o campo próprio e "Recolher" traz a conversa de
// volta para cá. Um modelo, duas vistas; nada é duplicado.

import { TbArrowsMaximize } from "react-icons/tb"

import Conversa from "@/app/components/home/assistente/conversa"
import type { TurnoDoAssistente } from "@/app/components/home/assistente/quadros"
import { useHomeStore } from "@/app/stores/homeStore"
import { useExtrasDoAssistente, type Confirmar, type Enviar } from "./extras"
import MarcaAnimada from "./marca-animada"
import { useTextos } from "../i18n"

/** Quantos turnos ficam ao centro: a última troca (a pergunta e a resposta). */
export const ITENS_AO_CENTRO = 2

interface Props {
  turnos: TurnoDoAssistente[]
  correndo: boolean
  confirmar: Confirmar
  /** As respostas rápidas enviam por aqui — o mesmo `enviar` da barra. */
  enviar: Enviar
  /** O painel abriu e a faixa está saindo: desliza para a direita e apaga, sem cliques. */
  saindo?: boolean
  /** A barra está com o pill de cota estourada acima da caixa: a faixa sobe a
   *  altura dele, senão o pill (z-30) pinta por cima do rodapé daqui (z-25). */
  comAvisoDeCota?: boolean
  /** A altura, em px, do que a barra empilha acima da caixa (chips de anexo,
   *  convite, aviso de recusados). Mesma razão do `comAvisoDeCota`, só que
   *  medida em vez de fixa, porque estes crescem e quebram linha. */
  folgaExtras?: number
}

export default function Pilha({
  turnos, correndo, confirmar, enviar, saindo = false, comAvisoDeCota = false, folgaExtras = 0,
}: Props) {
  const abrir = useHomeStore((s) => s.abrirPainel)
  const extras = useExtrasDoAssistente({ confirmar, correndo, enviar })
  const t = useTextos().assistente

  if (turnos.length === 0) return null

  const ultimos = turnos.slice(-ITENS_AO_CENTRO)
  const ocultos = turnos.length - ultimos.length

  return (
    <section
      aria-label={t.pilha.rotulo}
      className="home dark home-pilha flex flex-col gap-1.5"
      style={{ "--folga-extras": `${folgaExtras}px` } as React.CSSProperties}
      data-saindo={saindo}
      data-aviso-de-cota={comAvisoDeCota}
      data-testid="pilha"
    >
      {/* O teto de altura (CSS) é só segurança: com a pergunta numa linha e a
          resposta em 4, a faixa cabe; a `Conversa` só rola se os cartões
          passarem dele. */}
      <div className="home-pilha-itens flex min-h-0 flex-col">
        <Conversa
          turnos={ultimos}
          correndo={correndo}
          extras={extras}
          nome={t.nome}
          compacta
          indicador={MarcaAnimada}
          cursorAoEscrever
        />
      </div>
      {/* O rodapé vem DEPOIS dos itens, colado à barra: o contador à esquerda,
          a saída para a lateral à direita. */}
      <div className="flex min-h-[18px] items-center justify-end gap-3 text-[11.5px] text-muted-foreground">
        {ocultos > 0 && (
          <span className="mr-auto">
            {t.pilha.anteriores(ocultos)}
          </span>
        )}
        <button
          type="button"
          onClick={abrir}
          className="inline-flex items-center gap-1 rounded px-1 py-0.5 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring max-md:min-h-10"
          title={t.pilha.expandirTitulo}
        >
          <TbArrowsMaximize size={12} aria-hidden="true" /> {t.pilha.expandir}
        </button>
      </div>
    </section>
  )
}
