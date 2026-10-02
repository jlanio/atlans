"use client"

import { useState } from "react"
import { TbAlertTriangle, TbLock } from "react-icons/tb"
import { Badge } from "@/app/components/ui/badge"
import { Button } from "@/app/components/ui/button"
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/app/components/ui/dialog"
import { Switch } from "@/app/components/ui/switch"
import { GisFlowService } from "@/service/GisFlowService"
import type { IWorkspacePolicyAdmin } from "@/service/types"
import { createToast } from "@/utils/createToast"
import { cn } from "@/lib/utils"
import { classeDoModo, rotuloDoModo } from "@/app/components/workspace/politica"
import {
  CABECALHO_DE_COLUNAS, CELULA_COM_ROTULO, DESTAQUE_DA_FICHA, LINHA_EMPILHADA,
} from "@/app/components/shared/tabela-empilhada"

/** Sob piso e sem executor principal: nada roda até o dono incluir um. */
export function semOndeRodar(ws: IWorkspacePolicyAdmin): boolean {
  return ws.isolation_floor === "no_pool" && ws.primary_count === 0
}

/**
 * Piso de isolamento, por workspace (spec §4.5): só o administrador da
 * plataforma escreve. `no_pool` proíbe o pool compartilhado — o último recurso
 * do dono é forçado a "Falhar" e ele não consegue afrouxar.
 *
 * Exigir pede confirmação: muda o que roda onde, e pode deixar um workspace
 * sem executor nenhum. Liberar não: só devolve a escolha ao dono.
 */
export function IsolationFloorSection({ items, onChanged }: {
  items: IWorkspacePolicyAdmin[]
  onChanged: () => void
}) {
  const [confirmar, setConfirmar] = useState<IWorkspacePolicyAdmin | null>(null)
  const [salvando, setSalvando] = useState<string | null>(null)

  async function aplicar(ws: IWorkspacePolicyAdmin, floor: "none" | "no_pool") {
    setConfirmar(null)
    setSalvando(ws.id_hash)
    const res = await GisFlowService.setWorkspaceIsolationFloor(ws.id_hash, floor)
    setSalvando(null)
    if (res.error) {
      createToast.error("Erro ao alterar o piso", res.error.message)
      return
    }
    if (floor === "no_pool") {
      createToast.success(
        `«${ws.name}» passa a exigir isolamento.`
        + (res.data?.terminal_forced_to_fail
          ? " O último recurso foi travado em Falhar e os donos foram avisados por e-mail."
          : ""),
      )
    } else {
      createToast.success(`«${ws.name}» volta a poder usar o pool como último recurso.`)
    }
    onChanged()
  }

  function alternar(ws: IWorkspacePolicyAdmin, exigir: boolean) {
    if (exigir) { setConfirmar(ws); return }
    aplicar(ws, "none")
  }

  if (items.length === 0) {
    return <p className="text-xs text-muted-foreground">Nenhum workspace.</p>
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-lg border border-border overflow-x-auto">
        <table className="w-full text-xs md:min-w-[560px]">
          <thead className={CABECALHO_DE_COLUNAS}>
            <tr className="bg-muted/50 border-b border-border">
              <th className="text-left px-3 py-2 font-medium text-muted-foreground">Workspace</th>
              <th className="text-left px-3 py-2 font-medium text-muted-foreground">Política</th>
              <th className="text-right px-3 py-2 font-medium text-muted-foreground">Exigir isolamento</th>
            </tr>
          </thead>
          <tbody>
            {items.map(ws => {
              const sobPiso = ws.isolation_floor === "no_pool"
              const alerta = semOndeRodar(ws)
              return (
                <tr key={ws.id_hash} className={`border-b border-border last:border-b-0 ${LINHA_EMPILHADA}`}>
                  <td className={`px-3 py-2 ${DESTAQUE_DA_FICHA}`}>
                    <div className="flex items-center gap-1.5 font-medium text-foreground">
                      {ws.name}
                      {ws.is_default && <Badge variant="secondary" className="px-1 py-0 text-[9px]">padrão</Badge>}
                    </div>
                    <div className="text-muted-foreground">{ws.owner_username ?? "(sem dono)"}</div>
                  </td>
                  <td data-rotulo="política" className={`px-3 py-2 ${CELULA_COM_ROTULO}`}>
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                      <Badge
                        variant="outline"
                        className={cn("gap-1 px-1.5 py-0 text-[10px]", classeDoModo(ws.mode))}
                      >
                        {sobPiso && <TbLock size={10} aria-hidden="true" />}
                        {rotuloDoModo(ws.mode)}
                      </Badge>
                      <span className="tabular-nums text-muted-foreground">
                        {ws.primary_count} {ws.primary_count === 1 ? "principal" : "principais"}
                        {ws.fallback_count > 0 && ` · ${ws.fallback_count} reserva`}
                      </span>
                      {alerta && (
                        <span className="flex items-center gap-1 font-medium text-amber-700 dark:text-amber-400">
                          <TbAlertTriangle size={12} aria-hidden="true" />
                          sem executor principal: nada roda
                        </span>
                      )}
                    </div>
                  </td>
                  <td data-rotulo="exigir isolamento" className={`px-3 py-2 text-right ${CELULA_COM_ROTULO}`}>
                    <Switch
                      checked={sobPiso}
                      disabled={salvando === ws.id_hash}
                      onCheckedChange={v => alternar(ws, v)}
                      aria-label={`Exigir isolamento de ${ws.name}`}
                    />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <Dialog open={confirmar !== null} onOpenChange={o => { if (!o) setConfirmar(null) }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Exigir isolamento de «{confirmar?.name}»?</DialogTitle>
            <DialogDescription>
              Este workspace nunca mais usará o pool compartilhado: o último recurso do dono fica
              travado em «Falhar a execução».
              {confirmar?.effective_terminal === "pool" && (
                <> Hoje ele usa o pool como último recurso — isso deixa de valer e os donos são
                avisados por e-mail.</>
              )}
              {confirmar && confirmar.primary_count === 0 && (
                <> Como não há executor principal, <span className="font-medium text-foreground">nada
                roda</span> neste workspace até o dono incluir um executor dedicado.</>
              )}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmar(null)}>Cancelar</Button>
            <Button onClick={() => confirmar && aplicar(confirmar, "no_pool")}>Exigir isolamento</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
