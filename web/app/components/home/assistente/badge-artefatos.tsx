"use client"
import { TbAlertTriangle, TbMap2 } from "react-icons/tb"
import { derivarCamadas } from "@/app/components/home/camadas"
import { useHomeStore } from "@/app/stores/homeStore"
import type { TurnoDoAssistente } from "@/app/components/home/assistente/quadros"
import { useTextos } from "../i18n"

/**
 * Os artefatos que ESTA conversa produziu, numa faixa fixa no topo do painel.
 * Clicar põe o artefato no globo — nada aqui navega para fora da Home.
 *
 * Esta faixa mostrava os FLUXOS do assistente e abria `/workflow/{id}` (a antiga
 * decisão 4). O dono a substituiu: a Home é a única página de quem não
 * administra o sistema, e o que vale ser alcançável daqui é o RESULTADO, não a
 * máquina que o produziu. O fluxo continua em Projetos, com o interruptor
 * "mostrar os do assistente" ligado, para quem chegar lá.
 *
 * **Não duplica o que já existe** — são três recortes diferentes:
 *
 * - `CartaoCamada`, inline na conversa: o momento "a camada entrou no globo".
 *   Rola junto com a conversa e sai de vista.
 * - esta faixa: o índice do que a conversa TODA produziu. Fica fixa entre o
 *   cabeçalho e o rolo, então sobrevive à rolagem.
 * - `PainelCamadas`, no canto do globo: o que está no globo AGORA, com olho,
 *   remover e enquadrar.
 */
export default function BadgeArtefatos({ turnos }: { turnos: TurnoDoAssistente[] }) {
  const pedirCamada = useHomeStore((s) => s.pedirCamada)
  const t = useTextos().assistente.camada
  const camadas = derivarCamadas(turnos)
  if (camadas.length === 0) return null

  return (
    <div className="flex flex-wrap gap-1.5 border-b border-border px-3 py-2">
      {camadas.map((c) => {
        const nome = c.nome?.trim() || t.artefato
        const comum = "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] max-md:min-h-10 max-md:px-3 max-md:text-xs"

        // Sem prévia não há o que pôr no globo: fica `<span>`, não `<button>`.
        // Um botão sem ação promete um clique que não acontece, e o leitor de
        // tela ainda o anunciaria como acionável — a mesma razão que tirou o
        // `<button>` da linha de Agendamentos.
        if (!c.available) {
          return (
            <span
              key={c.artifact_id}
              title={c.hint ?? t.semPrevia}
              className={`${comum} border-dashed border-border bg-muted/20 text-muted-foreground/70`}
            >
              <TbAlertTriangle size={12} className="shrink-0" aria-hidden="true" />
              <span className="max-w-[10rem] truncate">{nome}</span>
            </span>
          )
        }

        return (
          <button
            key={c.artifact_id}
            type="button"
            // A fila do `homeStore` é o mesmo canal que a lista de Artefatos
            // usa: quem chama `useCamadas.adicionar` é o `HomeView`, que a
            // drena. `adicionar` já deduplica, então re-clicar é inofensivo.
            onClick={() => pedirCamada(c.artifact_id, c.nome)}
            title={t.mostrarNoGlobo(nome)}
            className={`${comum} border-border bg-muted/40 text-muted-foreground transition-colors hover:border-muted-foreground/40 hover:text-foreground`}
          >
            <TbMap2 size={12} className="shrink-0 text-primary" aria-hidden="true" />
            <span className="max-w-[10rem] truncate">{nome}</span>
          </button>
        )
      })}
    </div>
  )
}
