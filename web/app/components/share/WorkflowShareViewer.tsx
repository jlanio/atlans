"use client";

import dynamic from "next/dynamic";
import { useRef, useState } from "react";
import {
  TbDownload, TbStack2, TbWorld, TbLock, TbLoader2,
  TbClock, TbPolygon, TbLine,
  TbCircleDot, TbMap2, TbChevronLeft, TbChevronRight,
  TbLink, TbCheck, TbFocus2,
} from "react-icons/tb";
import { useTheme } from "@/context/ThemeContext";
import { TbSun, TbMoon } from "react-icons/tb";
import { formatLocal } from "@/lib/dayjs";
import { formatarInteiro, plural } from "@/lib/formatos";
import { CartaoDeEstado } from "@/app/components/shared/estados";
import { BrandLogo } from "./BrandLogo";
import type { MapLayer, MapLibreMapHandle } from "./MapLibreMap";

const MapLibreMap = dynamic(() => import("./MapLibreMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center bg-muted">
      <div className="flex flex-col items-center gap-3">
        {/* Movimento sob motion-safe: quem pede menos animação vê o ícone parado. */}
        <TbLoader2 className="motion-safe:animate-spin text-muted-foreground size-8" aria-hidden="true" />
        <span className="text-xs text-muted-foreground">Carregando mapa…</span>
      </div>
    </div>
  ),
});

interface PublishConfig {
  title: string;
  color: string;
  opacity: number;
  description: string;
  visible_fields: string[];
}

interface PortalLayer {
  id_hash: string;
  layer_key: string;
  filename: string;
  features: number | null;
  bbox: [number, number, number, number] | null;
  geometry_type: string | null;
  /** ISO timestamp da ultima publicacao — usado como cache-buster nas URLs de tile MVT. */
  updated_at: string | null;
  publish_config: PublishConfig | null;
}

export interface PortalData {
  workflow_name: string;
  portal_access: string;
  run_date: string | null;
  layers: PortalLayer[];
}

interface LayerState extends MapLayer {
  loading: boolean;
  features?: number;
}

function GeomIcon({ type }: { type?: string }) {
  if (!type) return <TbMap2 className="size-3.5 text-muted-foreground" aria-hidden="true" />;
  if (type.includes("Polygon")) return <TbPolygon className="size-3.5 text-emerald-500" aria-hidden="true" />;
  if (type.includes("Line")) return <TbLine className="size-3.5 text-blue-500" aria-hidden="true" />;
  if (type.includes("Point")) return <TbCircleDot className="size-3.5 text-amber-500" aria-hidden="true" />;
  return <TbMap2 className="size-3.5 text-muted-foreground" aria-hidden="true" />;
}

export default function WorkflowShareViewer({ data, workflowHash }: { data: PortalData; workflowHash?: string }) {
  const { theme, setTheme } = useTheme();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [copied, setCopied] = useState(false);
  const mapRef = useRef<MapLibreMapHandle>(null);

  const [layers, setLayers] = useState<LayerState[]>(() =>
    data.layers.map((l) => ({
      id: l.id_hash,
      label: l.publish_config?.title ?? l.filename,
      color: l.publish_config?.color ?? "#3b82f6",
      opacity: l.publish_config?.opacity ?? 0.5,
      geojson: { type: "FeatureCollection", features: [] } as GeoJSON.FeatureCollection,
      visible: true,
      loading: false,
      features: l.features ?? undefined,
      geomType: l.geometry_type ?? undefined,
      bbox: l.bbox ?? undefined,
    }))
  );

  const toggleLayer = (id: string) => {
    setLayers((prev) =>
      prev.map((l) => (l.id === id ? { ...l, visible: !l.visible } : l))
    );
  };

  const updateOpacity = (id: string, opacity: number) => {
    setLayers((prev) =>
      prev.map((l) => (l.id === id ? { ...l, opacity } : l))
    );
  };

  const handleCopyLink = async () => {
    await navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const runDateFormatted = formatLocal(data.run_date, "DD/MM/YYYY HH:mm:ss")
  const runDateLabel = runDateFormatted === "—" ? null : runDateFormatted

  // Classe comum dos botões-ícone do cabeçalho: anel de foco padrão (§5) e alvo
  // de 40px no telefone (size-10/p-2.5), reduzindo no desktop.
  const botaoHeader =
    "flex items-center justify-center rounded-lg p-2.5 sm:p-1.5 max-md:size-10 text-muted-foreground transition-colors outline-none hover:bg-accent focus-visible:ring-[3px] focus-visible:ring-ring/50";

  return (
    <div className="flex flex-col h-screen bg-background text-foreground">
      {/* ── Header ─────────────────────────────────────────────────── */}
      <header className="flex items-center justify-between px-4 py-2.5 border-b border-border/60 shrink-0 backdrop-blur-sm bg-background/95">
        <div className="flex items-center gap-3 min-w-0">
          <BrandLogo size="sm" />

          <span className="w-px h-4 bg-border/60" aria-hidden="true" />

          <span className="font-medium text-sm truncate max-w-[200px] sm:max-w-xs">
            {data.workflow_name}
          </span>

          {data.portal_access === "private" ? (
            <span className="flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
              <TbLock className="size-2.5" aria-hidden="true" /> Privado
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
              <TbWorld className="size-2.5" aria-hidden="true" /> Público
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {runDateLabel && (
            <span className="items-center gap-1 text-[11px] tabular-nums text-muted-foreground hidden sm:flex">
              <TbClock className="size-3" aria-hidden="true" />
              {runDateLabel}
            </span>
          )}
          <button
            type="button"
            onClick={handleCopyLink}
            className={botaoHeader}
            aria-label="Copiar link"
            title="Copiar link do portal"
          >
            {copied
              ? <TbCheck className="size-4 text-green-500" aria-hidden="true" />
              : <TbLink className="size-4" aria-hidden="true" />
            }
          </button>
          <button
            type="button"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className={botaoHeader}
            aria-label={theme === "dark" ? "Usar tema claro" : "Usar tema escuro"}
          >
            {theme === "dark" ? <TbSun className="size-4" aria-hidden="true" /> : <TbMoon className="size-4" aria-hidden="true" />}
          </button>
        </div>
      </header>

      {/* ── Body ───────────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden relative">

        {/* Toggle sidebar — visível em todos os tamanhos */}
        <button
          type="button"
          onClick={() => setSidebarOpen(!sidebarOpen)}
          // No telefone este é o único controle que abre a lista de camadas, e
          // a 28px ficava bem abaixo do alvo de toque de 44px.
          className="absolute top-3 z-20 p-3 sm:p-1.5 rounded-lg bg-background/90 backdrop-blur-sm border border-border/60 shadow-xs transition-all outline-none hover:bg-accent focus-visible:ring-[3px] focus-visible:ring-ring/50"
          style={{ left: sidebarOpen ? "16.5rem" : "0.75rem" }}
          aria-label={sidebarOpen ? "Recolher camadas" : "Mostrar camadas"}
          aria-expanded={sidebarOpen}
        >
          {sidebarOpen
            ? <TbChevronLeft className="size-4" aria-hidden="true" />
            : <TbChevronRight className="size-4" aria-hidden="true" />}
        </button>

        {/* ── Sidebar ──────────────────────────────────────────────── */}
        <aside
          className={`
            ${sidebarOpen ? "w-64 translate-x-0" : "w-0 -translate-x-full"}
            shrink-0 border-r border-border/60 flex flex-col overflow-hidden
            transition-all duration-300 ease-in-out
            absolute sm:relative z-10 h-full bg-background
          `}
        >
          <div className="px-4 py-3 border-b border-border/40">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                <TbStack2 className="size-3.5" aria-hidden="true" />
                Camadas
              </div>
              <span className="text-[10px] tabular-nums text-muted-foreground bg-muted px-1.5 py-0.5 rounded-full">
                {formatarInteiro(layers.length)}
              </span>
            </div>
          </div>

          {layers.length === 0 ? (
            // Vazio canônico (§3.3), adaptado à largura da lateral.
            <section
              aria-labelledby="camadas-vazio-titulo"
              className="flex-1 flex flex-col items-center justify-center gap-3 px-6 py-14 text-center"
            >
              <div className="rounded-full bg-muted/60 p-5">
                <TbMap2 className="size-7 text-muted-foreground/50" aria-hidden="true" />
              </div>
              <div className="flex flex-col gap-1.5">
                <p id="camadas-vazio-titulo" className="text-base font-semibold text-foreground">Nenhuma camada</p>
                <p className="text-sm text-muted-foreground">
                  Execute o workflow com um nó PublishMap para ver dados aqui.
                </p>
              </div>
            </section>
          ) : (
            <ul className="flex-1 overflow-y-auto p-2 space-y-1">
              {layers.map((layer, i) => {
                const cfg = data.layers[i]?.publish_config;
                return (
                  <li
                    key={layer.id}
                    className={`rounded-lg p-2.5 space-y-2 transition-colors duration-150 ${
                      layer.visible ? "bg-accent/50" : "bg-transparent opacity-60"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => toggleLayer(layer.id)}
                        className="flex items-center gap-2 flex-1 min-w-0 text-left group rounded-md outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
                        title={layer.visible ? "Ocultar camada" : "Mostrar camada"}
                        aria-pressed={layer.visible}
                      >
                        <span
                          className="w-3 h-3 rounded shrink-0 border-2 transition-colors duration-150"
                          style={{
                            backgroundColor: layer.visible ? layer.color : "transparent",
                            borderColor: layer.color,
                          }}
                          aria-hidden="true"
                        />
                        <span className="text-[13px] font-medium truncate group-hover:text-foreground transition-colors">
                          {layer.label}
                        </span>
                      </button>

                      {/* Spinner de carregamento */}
                      {layer.loading ? (
                        <TbLoader2 className="size-3.5 motion-safe:animate-spin text-muted-foreground shrink-0" aria-hidden="true" />
                      ) : (
                        /* Botão zoom para camada */
                        <button
                          type="button"
                          onClick={() => mapRef.current?.fitToLayer(layer.id)}
                          title="Zoom para esta camada"
                          aria-label={`Zoom para «${layer.label}»`}
                          className="p-1 max-md:p-2.5 rounded outline-none transition-colors shrink-0 text-muted-foreground hover:bg-accent hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50"
                        >
                          <TbFocus2 className="size-3.5" aria-hidden="true" />
                        </button>
                      )}

                      <GeomIcon type={layer.geomType} />
                    </div>

                    {layer.visible && (
                      <div className="pl-5 space-y-1.5">
                        {cfg?.description && (
                          <p className="text-[11px] text-muted-foreground leading-snug">{cfg.description}</p>
                        )}

                        {layer.features != null && (
                          <span className="inline-flex items-center text-[10px] tabular-nums text-muted-foreground bg-muted/80 px-1.5 py-0.5 rounded">
                            {plural(layer.features, "feição", "feições")}
                          </span>
                        )}

                        <div className="flex items-center gap-2">
                          <label htmlFor={`opacidade-${layer.id}`} className="text-[10px] text-muted-foreground w-12">Opacidade</label>
                          <input
                            id={`opacidade-${layer.id}`}
                            type="range"
                            min="0"
                            max="1"
                            step="0.05"
                            value={layer.opacity}
                            onChange={(e) => updateOpacity(layer.id, parseFloat(e.target.value))}
                            onWheel={(e) => e.stopPropagation()}
                            className="flex-1 h-1 cursor-pointer outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 rounded-full"
                            style={{ accentColor: layer.color }}
                            aria-label={`Opacidade de «${layer.label}»`}
                          />
                          <span className="text-[10px] tabular-nums text-muted-foreground w-6 text-right">
                            {Math.round(layer.opacity * 100)}%
                          </span>
                        </div>

                        <a
                          href={`/terra/artifacts/${layer.id}/download`}
                          download
                          className="inline-flex items-center gap-1 text-[11px] text-primary rounded-sm outline-none transition-colors hover:text-primary/80 hover:underline underline-offset-2 focus-visible:ring-[3px] focus-visible:ring-ring/50 max-md:min-h-10"
                        >
                          <TbDownload className="size-3" aria-hidden="true" />
                          Baixar GeoJSON
                        </a>
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </aside>

        {/* ── Mapa ─────────────────────────────────────────────────── */}
        <main className="flex-1 overflow-hidden">
          {layers.length === 0 ? (
            // Vazio canônico (§3.3): sem camadas publicadas não há o que desenhar.
            <div className="w-full h-full flex items-center justify-center bg-muted p-6">
              <section aria-labelledby="mapa-vazio-titulo">
                <CartaoDeEstado
                  icone={TbMap2}
                  tamanho="amplo"
                  titulo="Nenhum dado disponível"
                  descricao="Execute o workflow com um nó PublishMap para ver dados aqui."
                  tituloId="mapa-vazio-titulo"
                />
              </section>
            </div>
          ) : (
            <MapLibreMap
              ref={mapRef}
              layers={layers}
              useMvt={true}
              workflowHash={workflowHash}
              isDark={theme === "dark"}
              tileLayerKeys={Object.fromEntries(
                data.layers.map((l) => [l.id_hash, l.layer_key ?? l.filename.replace(/\.geojson$/, "")])
              )}
              tileLayerVersions={Object.fromEntries(
                data.layers.map((l) => [l.id_hash, l.updated_at ?? ""])
              )}
              visibleFields={Object.fromEntries(
                data.layers.map((l) => [l.id_hash, l.publish_config?.visible_fields ?? []])
              )}
            />
          )}
        </main>
      </div>
    </div>
  );
}
