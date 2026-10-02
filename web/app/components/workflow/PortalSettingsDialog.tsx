"use client";

import { useState, useRef } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
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
import { TbX, TbLink, TbCheck, TbExternalLink } from "react-icons/tb";
import { GisFlowService } from "@/service/GisFlowService";
import { createToast } from "@/utils/createToast";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workflowId: string;
  workflowName: string;
  initialAccess: "disabled" | "public" | "private";
  initialSharedWith: string[] | null;
  onSaved: (access: "disabled" | "public" | "private", sharedWith: string[] | null) => void;
}

export default function PortalSettingsDialog({
  open,
  onOpenChange,
  workflowId,
  workflowName,
  initialAccess,
  initialSharedWith,
  onSaved,
}: Props) {
  const [access, setAccess] = useState<"disabled" | "public" | "private">(initialAccess);
  const [sharedWith, setSharedWith] = useState<string[]>(initialSharedWith ?? []);
  const [tagInput, setTagInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const shareUrl =
    access !== "disabled"
      ? `${typeof window !== "undefined" ? window.location.origin : ""}/share/${workflowId}`
      : null;

  function addTag(value: string) {
    const trimmed = value.trim();
    if (!trimmed || sharedWith.includes(trimmed)) return;
    setSharedWith((prev) => [...prev, trimmed]);
    setTagInput("");
  }

  function removeTag(tag: string) {
    setSharedWith((prev) => prev.filter((t) => t !== tag));
  }

  async function handleSave() {
    setSaving(true);
    const result = await GisFlowService.updatePortalSettings(workflowId, {
      portal_access: access,
      portal_shared_with: access === "private" ? sharedWith : null,
    });
    setSaving(false);
    if (result?.error) {
      createToast.error("Erro ao salvar configuracoes do portal", result.error.message);
      return;
    }
    onSaved(access, access === "private" ? sharedWith : null);
    createToast.success(
      access === "disabled"
        ? "Portal desativado."
        : access === "public"
        ? "Portal publico ativado."
        : "Portal privado configurado."
    );
    onOpenChange(false);
  }

  async function handleCopyLink() {
    if (!shareUrl) return;
    await navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Portal publico</DialogTitle>
          <DialogDescription>
            Configure o acesso ao portal de mapas do workflow{" "}
            <span className="font-medium text-foreground">{workflowName}</span>.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label>Acesso ao portal</Label>
            <Select
              value={access}
              onValueChange={(v) => setAccess(v as "disabled" | "public" | "private")}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="disabled">Desativado</SelectItem>
                <SelectItem value="public">Publico — qualquer pessoa com o link</SelectItem>
                <SelectItem value="private">Privado — somente usuarios listados</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {access === "private" && (
            <div className="space-y-1.5">
              <Label>Usuarios com acesso</Label>
              <p className="text-xs text-muted-foreground">
                Digite o e-mail ou username e pressione Enter para adicionar.
              </p>
              <div className="flex gap-2">
                <Input
                  ref={inputRef}
                  placeholder="email@exemplo.com ou username"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      addTag(tagInput);
                    }
                  }}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => addTag(tagInput)}
                >
                  Adicionar
                </Button>
              </div>
              {sharedWith.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {sharedWith.map((tag) => (
                    <span
                      key={tag}
                      className="flex items-center gap-1 bg-secondary text-secondary-foreground text-xs rounded px-2 py-0.5"
                    >
                      {tag}
                      <button
                        onClick={() => removeTag(tag)}
                        className="hover:text-destructive transition-colors"
                        aria-label={`Remover ${tag}`}
                      >
                        <TbX className="size-3" />
                      </button>
                    </span>
                  ))}
                </div>
              )}
              {sharedWith.length === 0 && (
                <p className="text-xs text-muted-foreground italic">
                  Nenhum usuario adicionado ainda.
                </p>
              )}
            </div>
          )}

          {shareUrl && (
            <div className="space-y-1.5">
              <Label>Link do portal</Label>
              <div className="flex gap-2">
                <Input
                  readOnly
                  value={shareUrl}
                  className="text-xs text-muted-foreground"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleCopyLink}
                  title="Copiar link"
                >
                  {copied ? <TbCheck className="size-4 text-green-500" /> : <TbLink className="size-4" />}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => window.open(shareUrl, "_blank")}
                  title="Abrir portal"
                >
                  <TbExternalLink className="size-4" />
                </Button>
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? "Salvando..." : "Salvar"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
