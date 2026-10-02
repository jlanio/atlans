/**
 * Agendamento — o fuso padrão é o da instalação, e o seletor oferece todos.
 *
 * Antes, a tela tinha um fuso padrão fixo (UTC-4) e só nove fusos
 * do Brasil mais UTC: um nó sem fuso via a prévia num fuso diferente do que o
 * servidor de outra instalação usaria, e quem estava fora do Brasil não achava o
 * seu. Agora o padrão vem do catálogo de nós (o `default` do campo `timezone`,
 * que o servidor lê de AGENDAMENTO_FUSO_PADRAO), e a lista é a IANA inteira.
 */
import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"
import { ReactFlowProvider } from "@xyflow/react"
import NodeConfigForm from "@/app/components/workflow/node-config-modal/node-config-form"
import ScheduleTriggerHelper from "@/app/components/workflow/nodes-configuration/schedule-trigger-helper"
import type { INodeContext } from "@/context/useFlowContext"
import {
  deslocamentoDoFuso, FUSO_DE_RESERVA, fusoPadraoDosCampos, lerEstado, opcoesDeFuso,
} from "@/app/components/workflow/nodes-configuration/schedule-recurrence"
import type { INodesPropertyAPI } from "@/service/types"

vi.mock("@monaco-editor/react", () => ({
  default: () => <div data-testid="monaco" />,
  Editor: () => <div data-testid="monaco" />,
  useMonaco: () => null,
  loader: { config: () => {} },
}))

afterEach(cleanup)

const campoFuso = (padrao: string) => ({ name: "timezone", type: "string", default: padrao }) as INodesPropertyAPI

describe("o fuso padrão da instalação", () => {
  it("vem do default do campo timezone no catálogo", () => {
    expect(fusoPadraoDosCampos([campoFuso("Europe/Lisbon")])).toBe("Europe/Lisbon")
  })

  it("sem catálogo (ou sem o campo), a reserva é UTC — o padrão do servidor sem configuração", () => {
    expect(FUSO_DE_RESERVA).toBe("UTC")
    expect(fusoPadraoDosCampos(undefined)).toBe("UTC")
    expect(fusoPadraoDosCampos([{ name: "cron_expression", default: "0 9 * * *" } as INodesPropertyAPI])).toBe("UTC")
    expect(fusoPadraoDosCampos([campoFuso("  ")])).toBe("UTC")
  })

  it("um nó sem fuso (ou com fuso vazio) lê o padrão da instalação", () => {
    expect(lerEstado(undefined, "Europe/Lisbon").timezone).toBe("Europe/Lisbon")
    expect(lerEstado({ timezone: "" }, "Europe/Lisbon").timezone).toBe("Europe/Lisbon")
    // Um fuso gravado vence o padrão.
    expect(lerEstado({ timezone: "Asia/Tokyo" }, "Europe/Lisbon").timezone).toBe("Asia/Tokyo")
  })

  it("o helper usa o padrão do catálogo e não grava nada só por abrir", () => {
    const setNodeField = vi.fn()
    render(
      <ScheduleTriggerHelper
        values={{ strategy: "cron", cron_expression: "0 9 * * *", timezone: "", active: true }}
        setNodeField={setNodeField} hasUnsaved={false} nodeId="n1" campos={[campoFuso("Europe/Lisbon")]}
      />,
    )
    expect(screen.getAllByText(/Europe\/Lisbon|Europe Lisbon/).length).toBeGreaterThan(0)
    expect(setNodeField).not.toHaveBeenCalled()
  })
})

describe("o formulário do nó", () => {
  it("entrega ao helper os campos do catálogo, de onde sai o fuso padrão", () => {
    // Achado da revisão: tirar `campos` do formulário não quebrava nenhum
    // teste — e o helper cairia em UTC numa instalação de outro fuso.
    const no = {
      id: "agenda-1",
      position: { x: 0, y: 0 },
      data: {
        name: "ScheduleTrigger",
        alias: "Agendamento",
        description: "",
        type: "trigger",
        properties: { strategy: "cron", cron_expression: "0 9 * * *", active: true },
        fields: [
          { name: "cron_expression", type: "string", default: "0 9 * * *" },
          campoFuso("Europe/Lisbon"),
        ],
        inputs: [],
        outputs: [],
      },
    } as unknown as INodeContext
    render(
      <ReactFlowProvider>
        <NodeConfigForm
          nodeFound={no}
          values={{ strategy: "cron", cron_expression: "0 9 * * *", active: true }}
          setNodeField={() => {}}
          saveNodeConfig={() => {}}
          nodeName="ScheduleTrigger"
          requiresCredential={false}
        />
      </ReactFlowProvider>,
    )
    expect(screen.getAllByText(/Europe\/Lisbon|Europe Lisbon/).length).toBeGreaterThan(0)
  })
})

describe("a lista de fusos", () => {
  const AGORA = new Date("2026-01-15T12:00:00Z")

  it("traz UTC primeiro e os fusos IANA do mundo todo, com o deslocamento", () => {
    const opcoes = opcoesDeFuso(undefined, AGORA)
    expect(opcoes[0]).toEqual({ value: "UTC", label: "UTC" })
    const valores = opcoes.map(o => o.value)
    for (const zona of ["America/Sao_Paulo", "Europe/Lisbon", "Asia/Tokyo", "Pacific/Auckland"]) {
      expect(valores).toContain(zona)
    }
    expect(opcoes.length).toBeGreaterThan(300)
    expect(opcoes.find(o => o.value === "America/Sao_Paulo")?.label).toBe("America/Sao Paulo (UTC−3)")
    // O ICU chama a Índia de `Asia/Calcutta` (o nome canônico dele); versões
    // novas podem trazer `Asia/Kolkata`. O servidor aceita os dois.
    const india = opcoes.find(o => o.value === "Asia/Kolkata" || o.value === "Asia/Calcutta")
    expect(india?.label).toMatch(/\(UTC\+5:30\)$/)
  })

  it("um nome antigo gravado no nó continua no seletor", () => {
    const valores = opcoesDeFuso("America/Buenos_Aires", AGORA).map(o => o.value)
    expect(valores).toContain("America/Buenos_Aires")
  })

  it("o deslocamento de um fuso inválido é nulo, e não um erro", () => {
    expect(deslocamentoDoFuso("Marte/Olympus", AGORA)).toBeNull()
    expect(deslocamentoDoFuso("UTC", AGORA)).toBe("UTC")
  })
})
