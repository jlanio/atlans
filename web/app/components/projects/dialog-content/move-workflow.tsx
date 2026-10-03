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
  /** Called after a successful move — the parent removes the card from the listing. */
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
  // Post-move report: the dialog becomes a reading screen instead of closing,
  // because warning afterwards only works if the user actually reads the
  // warning. While it is set, it rules the body — the two states are exclusive.
  const [report, setReport] = useState<IWorkflowMoveResult | null>(null);
  // Different execution policy between source and destination: the workflow
  // starts following the destination's, and whoever moves from an Isolated
  // workspace to the pool needs to know the data changes executor.
  const [policyNotice, setPolicyNotice] = useState<string | null>(null);
  const sourceId = current?.id_hash ?? null;

  // Same list the menu uses to decide whether to offer the action; that is why
  // the dialog never opens without an eligible destination.
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
      // The preview is informational: if it fails, the move stays available — the
      // definitive report comes back in the POST response itself.
      setPreview(res?.error ? null : res.data ?? null);
    });
    return () => {
      cancelado = true;
    };
  }, [target, workflowId]);

  useEffect(() => {
    // Clear BEFORE fetching: the previous destination's warning must not stay on
    // screen while the new destination's loads.
    setPolicyNotice(null);
    if (!target || !sourceId) return;
    let cancelado = false;
    Promise.all([
      GisFlowService.getWorkspacePolicy(sourceId),
      GisFlowService.getWorkspacePolicy(target),
    ]).then(([origem, destino]) => {
      if (cancelado) return;
      // Informational: if one of the reads fails, there is no warning — the move goes on.
      setPolicyNotice(avisoDeMudancaDePolitica(
        origem?.error ? null : origem?.data ?? null,
        destino?.error ? null : destino?.data ?? null,
      ));
    });
    return () => {
      cancelado = true;
    };
  }, [target, sourceId]);

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

    const targetName = destinos.find((w) => w.id_hash === target)?.name ?? "outro workspace";
    onMoved(res.data);

    if (res.data.warnings.length > 0) {
      setReport(res.data);
      createToast.info(`Workflow movido para ${targetName}`, "Revise os avisos.");
      return;
    }
    createToast.success(`Workflow movido para ${targetName}`);
    onOpenChange(false);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-md"
        // Closing in the middle of the move leaves the user not knowing whether it
        // happened — and the impact report only appears afterwards. The three
        // exits: Esc, click-outside and the X.
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
                  {policyNotice && (
                    <li className="font-medium text-amber-700 dark:text-amber-400">{policyNotice}</li>
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
              {/* Never disabled because of the warnings: the decision to move
                  anyway is the user's, and the report already explained the cost. */}
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
