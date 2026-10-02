"use client"
import { useState } from "react"
import { TbDownload, TbEye, TbEyeOff, TbFocus2, TbStack2, TbTrash, TbX } from "react-icons/tb"
import { cn } from "@/lib/utils"
import { useIsMobile } from "@/hooks/use-mobile"
import type { MapLayer } from "@/app/components/share/MapLibreMap"
import type { AvisoDeCamada } from "@/app/hooks/home/useCamadas"
import { useTextos } from "./i18n"

interface Props {
  camadas: MapLayer[]
  /** artifact_id → aviso de "sem prévia". */
  avisos: Record<string, AvisoDeCamada>
  /** artifact_id → rótulo do que está sendo buscado agora. */
  carregando?: Record<string, string>
  onAlternar: (id: string) => void
  onRemover: (id: string) => void
  onEnquadrar: (id: string) => void
  onDispensarAviso: (artifactId: string) => void
  /** Baixa o arquivo de origem da camada. Recebe o `artifact_id` (sem `art:`). */
  onBaixar: (artifactId: string, nome: string) => void
}

const TITULO = "camadas-do-globo"

/**
 * A lista das camadas ativas no globo, com olho/enquadrar/remover, no canto
 * SUPERIOR ESQUERDO DA ÁREA DO GLOBO — `absolute` dentro da raiz da HomeView,
 * que já começa depois do sidebar. Fixa na viewport ela cobria a marca, o
 * "Nova conversa" e o gatilho de recolher, e ainda comia os cliques deles.
 *
 * No telefone nasce recolhida a uma faixa com a contagem: o painel do
 * assistente é opaco e vai de `top-16` até embaixo, então a lista aberta ali
 * ficava inalcançável. Recolhida, a faixa continua visível acima dele, e
 * expandir sobe por cima — que é quando a pessoa pediu para ver.
 *
 * Empilhamento da Home, de cima para baixo: gatilho móvel da barra lateral
 * (`app-header.tsx`, z-50) > este painel (z-40) > painel/barra do assistente
 * (z-30). Este painel NÃO sobe para z-50: empatado com o gatilho, ele o cobria
 * em tela estreita, e o gatilho é o único jeito de abrir a barra no telefone.
 */
export default function PainelCamadas({
  camadas, avisos, carregando = {}, onAlternar, onRemover, onEnquadrar, onDispensarAviso, onBaixar,
}: Props) {
  const t = useTextos().casca.camadas
  const isMobile = useIsMobile()
  const [expandidoManual, setExpandidoManual] = useState<boolean | null>(null)

  const semPrevia = Object.entries(avisos)
  const buscando = Object.entries(carregando)
  const total = camadas.length + buscando.length
  if (total === 0 && semPrevia.length === 0) return null

  const expandido = expandidoManual ?? !isMobile

  return (
    <section
      aria-labelledby={TITULO}
      className="home dark absolute left-6 top-6 z-40 w-64 max-w-[calc(100%-3rem)] overflow-hidden rounded-xl border border-border bg-background/95 pl-safe shadow-2xl backdrop-blur"
    >
      <h2 id={TITULO}>
        <button
          type="button"
          onClick={() => setExpandidoManual(!expandido)}
          aria-expanded={expandido}
          className="flex w-full items-center gap-1.5 border-b border-border px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wide text-muted-foreground transition-colors hover:text-foreground max-md:py-3"
        >
          <TbStack2 size={13} aria-hidden="true" /> {t.titulo}
          {total > 0 && <span className="ml-auto tabular-nums">{total}</span>}
        </button>
      </h2>

      {expandido && (
        <ul className="max-h-[40vh] overflow-y-auto p-1.5">
          {camadas.map((c) => {
            // Camada MVT sem bbox útil: a geometria vem dos tiles e o
            // `fitToLayer` não tem por onde calcular o enquadramento. O botão
            // vivo que não faz nada é pior do que o botão desabilitado.
            const podeEnquadrar = !!c.bbox || (c.geojson?.features?.length ?? 0) > 0
            return (
              <li key={c.id} className="group/camada flex items-center gap-1.5 rounded-md px-1.5 py-1 hover:bg-accent/50 max-md:gap-2">
                <span
                  className="size-2.5 shrink-0 rounded-sm"
                  style={{ backgroundColor: c.color, opacity: c.visible ? 1 : 0.35 }}
                  aria-hidden="true"
                />
                <span className={cn("min-w-0 flex-1 truncate text-xs", !c.visible && "text-muted-foreground line-through")}>
                  {c.label}
                </span>
                {/* Só quando o servidor disse que o arquivo existe para baixar
                    (`baixavel`): uma camada publicada aparece no globo com o
                    conteúdo no PostGIS e pode não ter arquivo no storage — ali
                    o download responderia 409/404, e botão vivo que falha é
                    pior que botão ausente. */}
                {c.baixavel && (
                  <BotaoIcone
                    label={t.baixar(c.label)}
                    onClick={() => onBaixar(idDoArtefato(c.id), c.label)}
                    soNoHover
                  >
                    <TbDownload size={14} />
                  </BotaoIcone>
                )}
                <BotaoIcone
                  label={t.enquadrar(c.label)}
                  onClick={() => onEnquadrar(c.id)}
                  desabilitado={!podeEnquadrar}
                  titulo={podeEnquadrar ? undefined : t.semExtensao}
                >
                  <TbFocus2 size={14} />
                </BotaoIcone>
                <BotaoIcone label={c.visible ? t.ocultar(c.label) : t.mostrar(c.label)} onClick={() => onAlternar(c.id)}>
                  {c.visible ? <TbEye size={14} /> : <TbEyeOff size={14} />}
                </BotaoIcone>
                <BotaoIcone label={t.remover(c.label)} onClick={() => onRemover(c.id)} destaque>
                  <TbTrash size={14} />
                </BotaoIcone>
              </li>
            )
          })}

          {/* Entre o clique e a camada nascer podiam passar segundos sem nada
              na tela — a pessoa clicava de novo e baixava o arquivo duas vezes. */}
          {buscando.map(([id, nome]) => (
            <li key={`carregando-${id}`} className="flex items-center gap-1.5 px-1.5 py-1 text-xs text-muted-foreground" aria-busy="true">
              <span className="size-2.5 shrink-0 animate-pulse rounded-sm bg-muted-foreground/40" aria-hidden="true" />
              <span className="min-w-0 flex-1 truncate">{nome}</span>
              <span className="shrink-0 text-[11px] italic">{t.carregando}</span>
            </li>
          ))}

          {semPrevia.length > 0 && (
            <li>
              <ul role="status">
                {semPrevia.map(([id, aviso]) => (
                  <li key={id} className="flex items-start gap-1.5 px-1.5 py-1 text-[11px] text-muted-foreground max-md:gap-2">
                    <span className="min-w-0 flex-1 break-words italic">
                      {aviso.nome ? `${aviso.nome} — ` : t.semPrevia}{aviso.motivo}
                    </span>
                    <BotaoIcone label={t.dispensarAviso(aviso.nome ?? null)} onClick={() => onDispensarAviso(id)}>
                      <TbX size={13} />
                    </BotaoIcone>
                  </li>
                ))}
              </ul>
            </li>
          )}
        </ul>
      )}
    </section>
  )
}

/** `art:<artifact_id>` → `<artifact_id>`. O prefixo é do `useCamadas`. */
export function idDoArtefato(idDaCamada: string): string {
  return idDaCamada.startsWith("art:") ? idDaCamada.slice(4) : idDaCamada
}

function BotaoIcone({
  label, onClick, destaque, desabilitado, soNoHover, titulo, children,
}: {
  label: string
  onClick: () => void
  destaque?: boolean
  desabilitado?: boolean
  /** Aparece ao passar o mouse na linha (ou ao receber foco). Ver abaixo. */
  soNoHover?: boolean
  titulo?: string
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={desabilitado}
      aria-label={label}
      title={titulo ?? label}
      className={cn(
        "flex size-6 shrink-0 items-center justify-center rounded text-muted-foreground transition-colors hover:bg-accent hover:text-foreground max-md:size-10",
        destaque && "hover:text-destructive",
        desabilitado && "cursor-not-allowed opacity-40 hover:bg-transparent hover:text-muted-foreground",
        soNoHover && [
          // `opacity`, e não `hidden`: a largura fica reservada, então a linha
          // não se reorganiza (e o nome não re-corta) quando o mouse entra.
          //
          // Três guardas para que "só no hover" não vire "inalcançável":
          // `@media (hover:hover)` restringe o esconderijo a quem TEM mouse —
          // no toque o botão é permanente, porque lá não existe hover; o foco
          // do teclado o revela (ele nunca sai da ordem de tabulação); e
          // `group-focus-within` cobre o foco chegando por outro botão da mesma
          // linha. Sem isto a ação existiria só para quem usa mouse.
          "max-md:opacity-100",
          "[@media(hover:hover)]:opacity-0",
          "[@media(hover:hover)]:group-hover/camada:opacity-100",
          "[@media(hover:hover)]:group-focus-within/camada:opacity-100",
          "[@media(hover:hover)]:focus-visible:opacity-100",
        ],
      )}
    >
      {children}
    </button>
  )
}
