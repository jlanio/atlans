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
  /** artifact_id → "no preview" notice. */
  avisos: Record<string, AvisoDeCamada>
  /** artifact_id → label of what is being fetched right now. */
  carregando?: Record<string, string>
  onAlternar: (id: string) => void
  onRemover: (id: string) => void
  onEnquadrar: (id: string) => void
  onDispensarAviso: (artifactId: string) => void
  /** Downloads the layer's source file. Takes the `artifact_id` (without `art:`). */
  onBaixar: (artifactId: string, nome: string) => void
}

const TITULO = "camadas-do-globo"

/**
 * The list of layers active on the globe, with eye/zoom-to/remove, in the
 * TOP LEFT CORNER OF THE GLOBE AREA — `absolute` inside the HomeView root,
 * which already starts after the sidebar. Fixed to the viewport it covered the
 * logo, the "Nova conversa" (new conversation) button and the collapse trigger,
 * and also swallowed their clicks.
 *
 * On the phone it starts collapsed to a strip with the count: the assistant
 * panel is opaque and runs from `top-16` to the bottom, so the open list there
 * was unreachable. Collapsed, the strip stays visible above it, and expanding
 * goes over it — which is when the person asked to see it.
 *
 * Home stacking, from top to bottom: mobile sidebar trigger
 * (`app-header.tsx`, z-50) > this panel (z-40) > assistant panel/bar
 * (z-30). This panel does NOT go up to z-50: tied with the trigger, it covered
 * it on narrow screens, and the trigger is the only way to open the bar on the
 * phone.
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
            // MVT layer with no useful bbox: the geometry comes from the tiles and
            // `fitToLayer` has no way to compute the framing. A live button
            // that does nothing is worse than a disabled button.
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
                {/* Only when the server said the file exists to download
                    (`baixavel`): a published layer appears on the globe with
                    its content in PostGIS and may have no file in storage —
                    there the download would answer 409/404, and a live button
                    that fails is worse than a missing button. */}
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

          {/* Between the click and the layer appearing, seconds could pass with nothing
              on screen — the person clicked again and downloaded the file twice. */}
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

/** `art:<artifact_id>` → `<artifact_id>`. The prefix comes from `useCamadas`. */
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
  /** Appears when hovering the row (or on receiving focus). See below. */
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
          // `opacity`, not `hidden`: the width stays reserved, so the row
          // does not reflow (and the name does not re-truncate) when the mouse enters.
          //
          // Three guards so that "hover only" does not become "unreachable":
          // `@media (hover:hover)` limits the hiding to those who HAVE a mouse —
          // on touch the button is permanent, because there is no hover there;
          // keyboard focus reveals it (it never leaves the tab order); and
          // `group-focus-within` covers focus arriving through another button on
          // the same row. Without this the action would exist only for mouse users.
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
