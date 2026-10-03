import { useState } from "react"
import { UseFormReturn } from "react-hook-form"
import z from "zod"
import { formCredentialSchema } from "../form-credential"
import { Label } from "@/app/components/ui/label"
import { Input } from "@/app/components/ui/input"
import { Textarea } from "@/app/components/ui/textarea"
import { Badge } from "@/app/components/ui/badge"
import { Switch } from "@/app/components/ui/switch"
import { Separator } from "@/app/components/ui/separator"
import { Button } from "@/app/components/ui/button"
import { TbX, TbAlertTriangle } from "react-icons/tb"
import { useWorkspace } from "@/context/WorkspaceContext"
import { dayjs, fromBackend } from "@/lib/dayjs"

// Types whose secret the node forwards (Authorization, the authkey key, the
// WFS Basic). Whoever can USE the credential in a node controls the destination
// URL and can therefore EXTRACT the secret by pointing at their own server —
// the SSRF guard only blocks internal targets. Hence, for these types "share for
// use" amounts to "entrust the secret". DATABASE credentials do not have that
// problem (the destination is embedded in the DSN, not an author parameter).
const TOKEN_TYPES = ["http_bearer", "http_basic", "wfs", "geoserver_authkey"]

interface MetaInputsProps {
  form: UseFormReturn<z.infer<typeof formCredentialSchema>>
  /** Locks everything — used in edit while the secrets load. */
  disabled?: boolean
}

const MAX_TAGS = 10

/**
 * OPTIONAL fields of a credential: description, tags, expiration and sharing
 * with the workspace. Shared between create and edit.
 *
 * `expires_at` lives inside `data` (data.expires_at) — same convention as the
 * backend, which reads it from there and is where the resolver applies the
 * expiration. The others are top-level form fields (they become their own columns).
 */
const MetaInputs = ({ form, disabled }: MetaInputsProps) => {
  const { current } = useWorkspace()
  const [tagBuffer, setTagBuffer] = useState("")

  const description = form.watch("description") ?? ""
  const tags = form.watch("tags") ?? []
  const data = form.watch("data") ?? {}
  const workspaceId = form.watch("workspace_id")
  const isTokenType = TOKEN_TYPES.includes(form.watch("type"))

  // ── expiration ──────────────────────────────────────────────────────────
  // ISO (UTC) stored in data.expires_at ⇄ local value of the <input datetime-local>.
  const expiryLocal = fromBackend(data.expires_at)?.format("YYYY-MM-DDTHH:mm") ?? ""

  function setExpiry(localValue: string) {
    const next = { ...data }
    if (!localValue) {
      delete next.expires_at
    } else {
      // The input delivers LOCAL time; we store it in UTC (with Z) to match what
      // the backend expects and the resolver compares.
      next.expires_at = dayjs(localValue).toISOString()
    }
    form.setValue("data", next, { shouldDirty: true })
  }

  // ── tags ────────────────────────────────────────────────────────────────
  function addTag(raw: string) {
    const t = raw.trim()
    if (!t) return
    if (tags.includes(t) || tags.length >= MAX_TAGS) {
      setTagBuffer("")
      return
    }
    form.setValue("tags", [...tags, t], { shouldDirty: true })
    setTagBuffer("")
  }

  function removeTag(t: string) {
    form.setValue("tags", tags.filter(x => x !== t), { shouldDirty: true })
  }

  // ── compartilhamento ──────────────────────────────────────────────────────
  function toggleShare(on: boolean) {
    // string = shares with the current workspace; null = removes (the backend's
    // PATCH semantics: null clears, undefined would leave it untouched).
    form.setValue("workspace_id", on && current?.id_hash ? current.id_hash : null, { shouldDirty: true })
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <Separator className="flex-1" />
        <span className="text-[11px] uppercase tracking-wide text-muted-foreground">Opcional</span>
        <Separator className="flex-1" />
      </div>

      {/* Description */}
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="cred-description">Descrição</Label>
        <Textarea
          id="cred-description"
          placeholder="Para que serve esta credencial? (visível só para quem pode vê-la)"
          value={description}
          maxLength={200}
          rows={2}
          disabled={disabled}
          onChange={e => form.setValue("description", e.target.value, { shouldDirty: true })}
        />
      </div>

      {/* Tags */}
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="cred-tags">Tags</Label>
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {tags.map(t => (
              <Badge key={t} variant="secondary" className="gap-1 pr-1">
                <span className="max-w-[10rem] truncate">{t}</span>
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => removeTag(t)}
                  aria-label={`Remover tag ${t}`}
                  className="rounded-full p-0.5 hover:bg-background/60 disabled:opacity-50"
                >
                  <TbX className="size-3" aria-hidden="true" />
                </button>
              </Badge>
            ))}
          </div>
        )}
        <Input
          id="cred-tags"
          placeholder={tags.length >= MAX_TAGS ? `Máximo de ${MAX_TAGS} tags` : "Digite e pressione Enter"}
          value={tagBuffer}
          disabled={disabled || tags.length >= MAX_TAGS}
          onChange={e => setTagBuffer(e.target.value)}
          onKeyDown={e => {
            if (e.key === "Enter" || e.key === ",") {
              e.preventDefault()
              addTag(tagBuffer)
            } else if (e.key === "Backspace" && !tagBuffer && tags.length) {
              removeTag(tags[tags.length - 1])
            }
          }}
          onBlur={() => addTag(tagBuffer)}
        />
      </div>

      {/* Expiration */}
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="cred-expiry">Expiração</Label>
        <div className="flex items-center gap-2">
          <Input
            id="cred-expiry"
            type="datetime-local"
            className="flex-1"
            value={expiryLocal}
            disabled={disabled}
            onChange={e => setExpiry(e.target.value)}
          />
          {expiryLocal && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={disabled}
              onClick={() => setExpiry("")}
              className="shrink-0"
            >
              Limpar
            </Button>
          )}
        </div>
        <p className="text-xs text-muted-foreground">
          Após esta data a credencial deixa de ser usada nas execuções. Deixe vazio para não expirar.
        </p>
      </div>

      {/* Sharing with the workspace */}
      {current?.id_hash && (
        <div className="flex flex-col gap-2 rounded-md border px-3 py-2">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <Label htmlFor="cred-share" className="cursor-pointer">
                Compartilhar com o workspace
              </Label>
              <p className="text-xs text-muted-foreground truncate">
                «{current.name}» — membros poderão usá-la nos workflows.
              </p>
            </div>
            <Switch
              id="cred-share"
              checked={!!workspaceId}
              disabled={disabled}
              onCheckedChange={toggleShare}
              aria-label="Compartilhar credencial com o workspace atual"
            />
          </div>

          {/* Honest warning for token types: "use" ≡ "able to extract". It is not
              an error alert (it does not use role=alert), it is trust guidance. */}
          {isTokenType && (
            <p className="flex items-start gap-1.5 text-xs text-amber-700 dark:text-amber-400">
              <TbAlertTriangle className="mt-px size-3.5 shrink-0" aria-hidden="true" />
              <span>
                Este é um segredo do tipo <strong>token</strong>: quem puder usá-la
                consegue, na prática, extrair o token (basta usá-la num nó de
                requisição apontado para um servidor próprio). Compartilhe apenas
                com quem você confiaria o segredo em si.
              </span>
            </p>
          )}
        </div>
      )}
    </div>
  )
}

export default MetaInputs
