"use client";

import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/app/components/ui/dialog";
import { Button } from "@/app/components/ui/button";
import { Input } from "@/app/components/ui/input";
import { Label } from "@/app/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/app/components/ui/select";
import { TbAlertTriangle, TbInfoCircle } from "react-icons/tb";
import { GisFlowService } from "@/service/GisFlowService";
import { createToast } from "@/utils/createToast";
import { moveTargets, useWorkspace } from "@/context/WorkspaceContext";
import type { IWorkflowMoveResult, IWorkflowMoveWarning } from "@/service/types";
import { avisoDeMudancaDePolitica } from "@/app/components/workspace/politica";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workflowId: string;
  workflowName: string;
  portalAccess?: string | null;
  /** Chamado apos mover com sucesso — o pai remove o card da listagem. */
  onMoved: (result: IWorkflowMoveResult) => void;
}

function WarningList({ warnings }: { warnings: IWorkflowMoveWarning[] }) {
  return (
    <ul className="space-y-2 max-h-64 overflow-y-auto pr-1">
      {warnings.map((w, i) => (
        <li key={`${w.code}-${i}`} className="flex gap-2 text-xs">
          {w.severity === "warning" ? (
            <TbAlertTriangle className="size-4 shrink-0 mt-0.5 text-amber-500" />
          ) : (
            <TbInfoCircle className="size-4 shrink-0 mt-0.5 text-muted-foreground" />
          )}
          <span
            className={w.severity === "warning" ? "text-foreground" : "text-muted-foreground"}
          >
            {w.message}
          </span>
        </li>
      ))}
    </ul>
  );
}

export default function MoveWorkflowDialog({
  open,
  onOpenChange,
  workflowId,
  workflowName,
  portalAccess,
  onMoved,
}: Props) {
  const { workspaces, current } = useWorkspace();
  const [target, setTarget] = useState("");
  const [name, setName] = useState("");
  const [preview, setPreview] = useState<IWorkflowMoveResult | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [saving, setSaving] = useState(false);
  // Relatorio pos-move: o dialogo vira uma tela de leitura em vez de fechar,
  // porque avisar depois so funciona se o usuario chegar a ler o aviso. Enquanto
  // preenchido, e ele que manda no corpo — os dois estados sao exclusivos.
  const [report, setReport] = useState<IWorkflowMoveResult | null>(null);
  // Politica de execucao diferente entre origem e destino: o workflow passa a
  // seguir a do destino, e quem move de um workspace Isolado para o pool
  // precisa saber que os dados mudam de executor.
  const [avisoPolitica, setAvisoPolitica] = useState<string | null>(null);
  const origemId = current?.id_hash ?? null;

  // Mesma lista que o menu usa para decidir se oferece a acao; por isso o
  // dialogo nunca abre sem destino elegivel.
  const destinos = moveTargets(workspaces, current?.id_hash);

  useEffect(() => {
    if (!open) {
      setTarget("");
      setName("");
      setPreview(null);
      setReport(null);
    }
  }, [open]);

  useEffect(() => {
    if (!target) {
      setPreview(null);
      return;
    }
    let cancelado = false;
    setLoadingPreview(true);
    GisFlowService.previewMoveWorkflow(workflowId, target).then((res) => {
      if (cancelado) return;
      setLoadingPreview(false);
      // Preview e informativo: se falhar, o move segue disponivel — o relatorio
      // definitivo volta na propria resposta do POST.
      setPreview(res?.error ? null : res.data ?? null);
    });
    return () => {
      cancelado = true;
    };
  }, [target, workflowId]);

  useEffect(() => {
    // Limpa ANTES de buscar: o aviso do destino anterior nao pode ficar na
    // tela enquanto o do novo destino carrega.
    setAvisoPolitica(null);
    if (!target || !origemId) return;
    let cancelado = false;
    Promise.all([
      GisFlowService.getWorkspacePolicy(origemId),
      GisFlowService.getWorkspacePolicy(target),
    ]).then(([origem, destino]) => {
      if (cancelado) return;
      // Informativo: se uma das leituras falhar, nao ha aviso — o move segue.
      setAvisoPolitica(avisoDeMudancaDePolitica(
        origem?.error ? null : origem?.data ?? null,
        destino?.error ? null : destino?.data ?? null,
      ));
    });
    return () => {
      cancelado = true;
    };
  }, [target, origemId]);

  async function handleMove() {
    if (!target) return;
    setSaving(true);
    const res = await GisFlowService.moveWorkflowToWorkspace(
      workflowId,
      target,
      name.trim() || undefined,
    );
    setSaving(false);

    if (res?.error || !res.data) {
      createToast.error("Erro ao mover workflow", res?.error?.message);
      return;
    }

    const nomeDestino = destinos.find((w) => w.id_hash === target)?.name ?? "outro workspace";
    onMoved(res.data);

    if (res.data.warnings.length > 0) {
      setReport(res.data);
      createToast.info(`Workflow movido para ${nomeDestino}`, "Revise os avisos.");
      return;
    }
    createToast.success(`Workflow movido para ${nomeDestino}`);
    onOpenChange(false);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-md"
        // Fechar no meio do move deixa o usuario sem saber se ele aconteceu —
        // e o relatorio de impacto so aparece depois. As tres saidas: Esc,
        // clique-fora e o X.
        bloqueado={saving}
      >
        <DialogHeader>
          <DialogTitle>{report ? "Workflow movido" : "Mover para workspace"}</DialogTitle>
          <DialogDescription>
            {report ? (
              <>
                O workflow foi movido como{" "}
                <span className="font-medium text-foreground">{report.name}</span>. Estes
                pontos precisam da sua atencao:
              </>
            ) : (
              <>
                Move{" "}
                <span className="font-medium text-foreground">{workflowName}</span> para
                outro workspace. O historico de execucoes, artefatos e metricas permanece
                no workspace atual.
              </>
            )}
          </DialogDescription>
        </DialogHeader>

        {report ? (
          <>
            <WarningList warnings={report.warnings} />
            <DialogFooter>
              <Button onClick={() => onOpenChange(false)}>Entendi</Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <div className="space-y-4">
              <div className="space-y-1.5">
                <Label>Workspace de destino</Label>
                <Select value={target} onValueChange={setTarget}>
                  <SelectTrigger>
                    <SelectValue placeholder="Selecione o destino" />
                  </SelectTrigger>
                  <SelectContent>
                    {destinos.map((w) => (
                      <SelectItem key={w.id_hash} value={w.id_hash}>
                        {w.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <Label>Novo nome (opcional)</Label>
                <Input
                  placeholder={workflowName}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Se ja houver um workflow com o mesmo nome no destino, um sufixo e
                  adicionado automaticamente.
                </p>
              </div>

              <div className="rounded border border-border bg-muted/40 p-3 space-y-1">
                <p className="text-xs font-medium">O que muda ao mover</p>
                <ul className="text-xs text-muted-foreground list-disc pl-4 space-y-0.5">
                  <li>O agendamento chega desligado no destino.</li>
                  <li>
                    O portal volta a &quot;desativado&quot;
                    {portalAccess && portalAccess !== "disabled"
                      ? " — os links ja compartilhados deixarao de funcionar."
                      : "."}
                  </li>
                  <li>O workflow sai do grupo atual e os dados fixados sao removidos.</li>
                  {avisoPolitica && (
                    <li className="font-medium text-amber-700 dark:text-amber-400">{avisoPolitica}</li>
                  )}
                </ul>
              </div>

              {loadingPreview && (
                <p className="text-xs text-muted-foreground">Verificando impactos...</p>
              )}

              {preview && preview.warnings.length > 0 && (
                <div className="space-y-1.5">
                  <Label>Impactos identificados</Label>
                  <WarningList warnings={preview.warnings} />
                </div>
              )}

              {preview && preview.warnings.length === 0 && (
                <p className="text-xs text-muted-foreground">
                  Nenhum impacto adicional identificado neste destino.
                </p>
              )}
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
                Cancelar
              </Button>
              {/* Nunca desabilitado por causa dos avisos: a decisao de mover
                  mesmo assim e do usuario, e o relatorio ja explicou o custo. */}
              <Button onClick={handleMove} disabled={!target || saving}>
                {saving ? "Movendo..." : "Mover"}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
