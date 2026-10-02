import { describe, it, expect, vi, beforeEach } from "vitest"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"

vi.mock("@/hooks/use-mobile", () => ({ useIsMobile: () => false }))

import PainelCamadas from "@/app/components/home/painel-camadas"
import type { MapLayer } from "@/app/components/share/MapLibreMap"

const VAZIO: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] }

const camada = (over: Partial<MapLayer> = {}): MapLayer => ({
  id: "art:a1", label: "Focos", color: "#f97316", opacity: 0.6,
  geojson: VAZIO, visible: true, geomType: "Point", ...over,
})

type Props = React.ComponentProps<typeof PainelCamadas>
function montar(props: Partial<Props> = {}): Props {
  const p: Props = {
    camadas: [], avisos: {}, carregando: {},
    onAlternar: vi.fn(), onRemover: vi.fn(), onEnquadrar: vi.fn(), onDispensarAviso: vi.fn(),
    onBaixar: vi.fn(),
    ...props,
  }
  render(<PainelCamadas {...p} />)
  return p
}

beforeEach(() => cleanup())

describe("PainelCamadas", () => {
  it("sem camadas, sem avisos e sem nada carregando: não existe", () => {
    const { container } = render(<PainelCamadas
      camadas={[]} avisos={{}}
      onAlternar={vi.fn()} onRemover={vi.fn()} onEnquadrar={vi.fn()} onDispensarAviso={vi.fn()}
      onBaixar={vi.fn()}
    />)
    expect(container.firstChild).toBeNull()
  })

  it("é uma seção nomeada por um h2 (contrato de tela da casa)", () => {
    montar({ camadas: [camada()] })
    expect(screen.getByRole("region", { name: /camadas/i })).toBeTruthy()
    expect(screen.getByRole("heading", { level: 2 })).toBeTruthy()
  })

  it("fica ABAIXO do gatilho móvel da barra lateral (z-40, nunca z-50)", () => {
    // Empatado em z-40 com o gatilho do app-header, este painel o cobria em
    // tela estreita — e ele é o único jeito de abrir a barra no telefone.
    montar({ camadas: [camada()] })
    const painel = screen.getByRole("region", { name: /camadas/i })
    expect(painel.className).toContain("z-40")
    expect(painel.className).not.toContain("z-50")
  })

  it("enquadrar fica desabilitado quando a camada não traz extensão nem feições", () => {
    montar({ camadas: [camada({ mvt: { workflowHash: "w", layerKey: "k" } })] })
    expect(screen.getByRole("button", { name: /enquadrar/i }).hasAttribute("disabled")).toBe(true)
  })

  it("enquadrar vale quando há bbox", () => {
    const p = montar({ camadas: [camada({ bbox: [-52, -12, -51, -11] })] })
    fireEvent.click(screen.getByRole("button", { name: /enquadrar/i }))
    expect(p.onEnquadrar).toHaveBeenCalledWith("art:a1")
  })

  it("o aviso diz QUAL artefato e tem como ser dispensado", () => {
    const p = montar({ avisos: { a9: { nome: "Censo 2022", motivo: "fica no executor" } } })
    expect(screen.getByText(/Censo 2022 — fica no executor/)).toBeTruthy()
    fireEvent.click(screen.getByRole("button", { name: /dispensar aviso/i }))
    expect(p.onDispensarAviso).toHaveBeenCalledWith("a9")
  })

  it("o que está sendo buscado aparece na lista", () => {
    montar({ carregando: { a7: "Buffer das escolas" } })
    expect(screen.getByText("Buffer das escolas")).toBeTruthy()
    expect(screen.getByText(/carregando/i)).toBeTruthy()
  })

  it("remover chama o callback com o id da camada", () => {
    const p = montar({ camadas: [camada()] })
    fireEvent.click(screen.getByRole("button", { name: /remover/i }))
    expect(p.onRemover).toHaveBeenCalledWith("art:a1")
  })
})

describe("PainelCamadas — baixar", () => {
  it("manda o artifact_id SEM o prefixo `art:`", () => {
    // O prefixo é do `useCamadas` (dedupe no globo); quem baixa é
    // `/artifacts/{id}/download`, que não o conhece.
    const p = montar({ camadas: [camada({ id: "art:a1", label: "Focos", baixavel: true })] })
    fireEvent.click(screen.getByRole("button", { name: /baixar focos/i }))
    expect(p.onBaixar).toHaveBeenCalledWith("a1", "Focos")
  })

  it("sem `baixavel`, o botão NEM APARECE", () => {
    // Uma camada publicada vive no globo com o conteúdo no PostGIS e pode não
    // ter arquivo no storage; um artefato marcado para ficar no executor idem.
    // Nos dois o download responderia 409/404 — botão vivo que falha é pior que
    // botão ausente.
    montar({ camadas: [camada({ baixavel: false })] })
    expect(screen.queryByRole("button", { name: /baixar/i })).toBeNull()

    cleanup()
    montar({ camadas: [camada()] })   // sem o campo: o padrão é não oferecer
    expect(screen.queryByRole("button", { name: /baixar/i })).toBeNull()
  })

  it("está na ordem de tabulação mesmo escondido: 'só no hover' não pode virar inalcançável", () => {
    // Ele é escondido por `opacity`, e só onde HÁ mouse (`@media (hover:hover)`);
    // no toque é permanente. Some da vista, nunca do teclado.
    montar({ camadas: [camada({ baixavel: true })] })
    const bt = screen.getByRole("button", { name: /baixar/i })
    expect(bt.hasAttribute("disabled")).toBe(false)
    expect(bt.getAttribute("tabindex")).toBeNull()
    expect(bt.className).toContain("max-md:opacity-100")
    expect(bt.className).toContain("group-focus-within/camada:opacity-100")
  })
})
