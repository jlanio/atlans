"use client"

// Trocar o modelo do assistente.
//
// O núcleo é o seletor: o modelo em uso, o catálogo do provedor e o salvar.
// Uma extensão (`web/extensoes`) pode envolvê-lo com o que a troca muda nela —
// uma de planos pagos, por exemplo, soma a cota de cada plano e a conta do
// custo e da margem com o modelo escolhido. Sem extensão, é só o seletor.

import { Suspense, useEffect, useMemo, useState, type ReactNode } from "react"
import { TbAlertTriangle, TbCheck, TbSearch } from "react-icons/tb"
import { EXTENSOES, LimiteDaExtensao } from "@/extensoes"
import { GisFlowService } from "@/service/GisFlowService"
import type { IPainelDoModelo, IModeloDoCatalogo } from "@/service/types"
import { createToast } from "@/utils/createToast"
import { cn } from "@/lib/utils"
import { Button } from "@/app/components/ui/button"
import { Input } from "@/app/components/ui/input"
import { formatarDolar } from "@/lib/formatos"

interface Props {
  painel: IPainelDoModelo
  onTrocado: () => void
}

export function ModeloDoAssistente({ painel, onTrocado }: Props) {
  const [escolhido, setEscolhido] = useState<string>(painel.atual.modelo)
  const [filtro, setFiltro] = useState("")
  // Uma gravação em curso — a do modelo, aqui, ou a de uma extensão. Um estado
  // só, para os botões das duas esperarem juntos.
  const [salvando, setSalvando] = useState(false)

  // A carga nova do pai é a verdade: depois de salvar, o modelo escolhido tem
  // de acompanhar, senão o botão continua oferecendo salvar o que já está lá.
  useEffect(() => { setEscolhido(painel.atual.modelo) }, [painel.atual.modelo])

  const catalogo = useMemo(() => {
    const busca = filtro.trim().toLowerCase()
    if (!busca) return painel.catalogo
    return painel.catalogo.filter(m => `${m.id} ${m.nome}`.toLowerCase().includes(busca))
  }, [painel.catalogo, filtro])

  async function salvar(modelo: string | null) {
    setSalvando(true)
    const res = await GisFlowService.trocarModelo(modelo)
    setSalvando(false)
    if (res.error) {
      createToast.error("Não foi possível trocar o modelo", res.error.message)
      return
    }
    createToast.success(
      modelo ? "Modelo trocado" : "De volta ao padrão do ambiente",
      "Vale da próxima conversa em diante; as que estão em curso terminam no modelo em que começaram.",
    )
    onTrocado()
  }

  // ── Escolher ───────────────────────────────────────────────────────────────
  const seletor = painel.catalogo.length > 0 && (
    <div className="flex flex-col gap-1.5">
      <label htmlFor="modelo-busca" className="text-xs font-medium">Trocar para</label>
      <div className="relative">
        <TbSearch size={14} aria-hidden="true" className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <Input
          id="modelo-busca"
          value={filtro}
          onChange={e => setFiltro(e.target.value)}
          placeholder="filtrar por nome ou fornecedor…"
          className="h-9 pl-8 text-[13px]"
          autoComplete="off"
        />
      </div>
      <ul role="listbox" aria-label="Modelos disponíveis" className="max-h-48 overflow-y-auto rounded-md border">
        {catalogo.length === 0 ? (
          <li className="px-3 py-3 text-xs text-muted-foreground">
            Nenhum modelo com «{filtro}». A lista vem do provedor.
          </li>
        ) : catalogo.map(m => (
          <li key={m.id}>
            <button
              type="button"
              role="option"
              aria-selected={m.id === escolhido}
              onClick={() => setEscolhido(m.id)}
              className={cn(
                "flex w-full flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5 border-b px-3 py-2 text-left text-xs last:border-b-0 hover:bg-muted",
                m.id === escolhido && "bg-primary/10 shadow-[inset_2px_0_0_var(--primary)]",
              )}
            >
              <span className="font-mono">
                {m.id}
                {m.id === painel.atual.modelo && <span className="text-muted-foreground"> · em uso</span>}
              </span>
              <span className="tabular-nums whitespace-nowrap text-muted-foreground">
                {precoDoModelo(m)}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )

  // Cada extensão envolve o que veio antes dela: a primeira envolve o seletor.
  // Se um envoltório falha (um defeito dele, ou o pedaço sob demanda que não
  // chegou), fica o que ele envolvia: o seletor e o «Voltar ao padrão» são a
  // saída de emergência desta tela, e não podem cair junto.
  const corpo = EXTENSOES.reduce<ReactNode>((filho, extensao) => {
    const Envoltorio = extensao.painelDoModelo?.Envoltorio
    if (!Envoltorio) return filho
    return (
      <LimiteDaExtensao key={extensao.nome} nome={extensao.nome} reserva={filho}>
        <Envoltorio
          painel={painel}
          escolhido={escolhido}
          ocupado={salvando}
          aoOcupar={setSalvando}
          aoTrocar={onTrocado}
        >
          {filho}
        </Envoltorio>
      </LimiteDaExtensao>
    )
  }, seletor)

  return (
    <div className="flex flex-col gap-4">
      {/* ── O que está em uso ───────────────────────────────────────────── */}
      <p className="flex flex-wrap items-baseline gap-2 text-sm">
        Em uso agora: <b className="font-mono text-[13px]">{painel.atual.modelo}</b>
        <span className="rounded-full border bg-muted px-2 py-px text-[10.5px] text-muted-foreground">
          {painel.atual.origem === "ambiente"
            ? "do ambiente · ASSISTENTE_MODELO"
            : `definido aqui${painel.atual.definido_por ? ` · por ${painel.atual.definido_por}` : ""}`}
        </span>
      </p>

      {painel.catalogo_indisponivel && (
        <p role="status" className="flex items-start gap-2 rounded-md border border-border bg-muted px-3 py-2 text-xs text-muted-foreground">
          <TbAlertTriangle size={14} className="mt-px shrink-0" aria-hidden="true" />
          {/* Provedor fora do ar não derruba a tela: o admin ainda precisa ver
              o que está em uso e poder voltar ao padrão. */}
          <span>
            Não foi possível ler o catálogo do provedor
            {painel.catalogo_indisponivel === "sem_credencial"
              ? " — não há credencial configurada nesta instalação."
              : ` (${painel.catalogo_indisponivel}).`}
            {" "}Você ainda pode voltar ao padrão do ambiente.
          </span>
        </p>
      )}

      {/* Um envoltório pode chegar sob demanda (`lazy`): enquanto ele carrega,
          o seletor aparece sozinho. */}
      <Suspense fallback={seletor}>{corpo}</Suspense>

      {/* ── Salvar ───────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-end gap-2 border-t pt-3">
        <span className="mr-auto text-[11px] text-muted-foreground">
          {escolhido === painel.atual.modelo
            ? "Nenhuma mudança: este já é o modelo em uso."
            : `Vai passar para ${escolhido} na próxima conversa de cada pessoa.`}
        </span>
        {painel.atual.origem === "banco" && (
          <Button variant="outline" size="sm" disabled={salvando} onClick={() => salvar(null)}>
            Voltar ao padrão do ambiente
          </Button>
        )}
        <Button
          size="sm"
          disabled={salvando || escolhido === painel.atual.modelo}
          onClick={() => salvar(escolhido)}
        >
          <TbCheck size={14} aria-hidden="true" />
          Salvar modelo
        </Button>
      </div>
    </div>
  )
}

function precoDoModelo(m: IModeloDoCatalogo): string {
  if (m.entrada_por_milhao == null || m.saida_por_milhao == null) return "preço não informado"
  return `${formatarDolar(m.entrada_por_milhao)} ent · ${formatarDolar(m.saida_por_milhao)} saí / M`
}
