"use client"

// Diálogo «Novo token» em 2 passos.
//
// Passo 1 é o formulário (nome, escopos, workspaces, validade). Passo 2 mostra
// o segredo — a ÚNICA vez que ele aparece — e os snippets para conectar um
// agente. Os snippets nunca embutem o segredo real: levam `${ATLANS_TOKEN}`,
// para que copiar um comando e colar num chat ou num README não vaze o token.

import { useEffect, useMemo, useRef, useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import {
  TbAlertTriangle, TbCheck, TbClockBolt, TbCopy, TbEye, TbFolder, TbLoader2,
  TbPencil, TbPlayerPlay, TbUpload,
} from "react-icons/tb"
import type { IconType } from "react-icons"
import { GisFlowService } from "@/service/GisFlowService"
import type { ApiTokenCreate, ApiTokenCreated, ApiTokenExpiresInDays, ApiTokenScope, IWorkspace } from "@/service/types"
import { createToast } from "@/utils/createToast"
import { getExternalApiUrl } from "@/utils/env"
import { cn } from "@/lib/utils"
import { dayjs } from "@/lib/dayjs"
import { Button } from "@/app/components/ui/button"
import { Checkbox } from "@/app/components/ui/checkbox"
import {
  DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/app/components/ui/dialog"
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/app/components/ui/form"
import { Input } from "@/app/components/ui/input"
import { Label } from "@/app/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/app/components/ui/select"
import {
  ESCOPOS, ESCOPOS_SOMENTE_LEITURA, ESCOPO_DESCRICOES, ESCOPO_ROTULOS, ordenarEscopos,
} from "../escopo-rotulos"

// ── Constantes ───────────────────────────────────────────────────────────────

// O MCP é o desta instalação, no caminho /mcp da API: em produção, o proxy
// reverso o entrega no próprio host do site; no desenvolvimento, a API responde
// na porta dela (NEXT_PUBLIC_API_PORT), e o `next dev` não repassa /mcp.
// getExternalApiUrl() cobre os dois. Os snippets levam URL_DO_MCP no lugar do
// endereço, e a tela o troca por este; docs/mcp.md traz os mesmos snippets com
// um domínio de exemplo.
export const URL_DO_MCP = "{URL_DO_MCP}"

export function urlDoMcp(): string {
  return `${getExternalApiUrl()}/mcp`
}

export function snippetCom(snippet: string, url: string): string {
  return snippet.replaceAll(URL_DO_MCP, url)
}

// Caminho do documento que descreve escopos, limites e erros do servidor.
// Texto, não link: o documento mora com o código, não nesta instalação.
export const DOCS_MCP = "docs/mcp.md"

const VALIDADES: readonly ApiTokenExpiresInDays[] = [30, 90, 180, 365]
const VALIDADE_PADRAO: ApiTokenExpiresInDays = 90

function rotuloDeValidade(dias: ApiTokenExpiresInDays): string {
  return dias === 365 ? "1 ano" : `${dias} dias`
}

const ESCOPO_ICONES: Record<ApiTokenScope, IconType> = {
  "workflows:read":  TbEye,
  "workflows:write": TbPencil,
  "runs:execute":    TbPlayerPlay,
  "triggers:manage": TbClockBolt,
  "drive:read":      TbFolder,
  "drive:write":     TbUpload,
}

type Cliente = "claude" | "mcp-json" | "mcp-remote"

// Strings entre aspas simples de propósito: `${ATLANS_TOKEN}` é texto literal
// para o shell/JSON do usuário, não interpolação nossa.
export const CLIENTES: { id: Cliente; rotulo: string; snippet: string; nota: string }[] = [
  {
    id: "claude",
    rotulo: "Claude Code",
    snippet: 'claude mcp add --transport http atlans {URL_DO_MCP} --header "Authorization: Bearer ${ATLANS_TOKEN}"',
    nota: 'Troque ${ATLANS_TOKEN} pelo segredo acima — ou exporte a variável antes de rodar.',
  },
  {
    id: "mcp-json",
    rotulo: "Cursor, VS Code e Windsurf",
    snippet: JSON.stringify(
      { mcpServers: { atlans: { url: URL_DO_MCP, headers: { Authorization: "Bearer ${ATLANS_TOKEN}" } } } },
      null,
      2,
    ),
    nota: 'Cole no mcp.json do cliente e troque ${ATLANS_TOKEN} pelo segredo acima.',
  },
  {
    id: "mcp-remote",
    rotulo: "mcp-remote",
    snippet: 'npx mcp-remote {URL_DO_MCP} --header "Authorization:${AUTH_HEADER}"',
    nota: 'Defina AUTH_HEADER="Bearer …" no ambiente, com o segredo no lugar das reticências.',
  },
]

// ── Formulário ───────────────────────────────────────────────────────────────

const schema = z
  .object({
    name: z
      .string()
      .trim()
      .min(1, "O nome do token é obrigatório")
      .max(80, "O nome do token não pode ter mais de 80 caracteres"),
    scopes: z.array(z.enum(ESCOPOS)).min(1, "Escolha pelo menos um escopo"),
    all_workspaces: z.boolean(),
    workspace_ids: z.array(z.string()),
    expires_in_days: z.union([z.literal(30), z.literal(90), z.literal(180), z.literal(365)]),
  })
  .refine(v => v.all_workspaces || v.workspace_ids.length > 0, {
    message: "Escolha pelo menos um workspace — ou marque «Todos os workspaces»",
    path: ["workspace_ids"],
  })

type FormValues = z.infer<typeof schema>

function alternar<T>(lista: readonly T[], item: T): T[] {
  return lista.includes(item) ? lista.filter(x => x !== item) : [...lista, item]
}

/**
 * Copiar para a área de transferência com o «Copiado» de 2 s. O timer é limpo
 * ao rearmar e no unmount: fechar o diálogo antes dos 2 s não pode disparar um
 * setState em componente desmontado. Sem `navigator.clipboard` (http simples,
 * iframe sem permissão) a falha vira uma mensagem — o texto continua
 * selecionável para copiar à mão.
 */
function useCopiar() {
  const [copiado, setCopiado] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  useEffect(() => () => clearTimeout(timer.current), [])

  async function copiar(texto: string) {
    setErro(null)
    try {
      if (typeof navigator === "undefined" || !navigator.clipboard?.writeText) {
        throw new Error("Área de transferência indisponível")
      }
      await navigator.clipboard.writeText(texto)
      setCopiado(true)
      clearTimeout(timer.current)
      timer.current = setTimeout(() => setCopiado(false), 2000)
    } catch {
      setCopiado(false)
      setErro("Não foi possível copiar automaticamente — selecione o texto e copie manualmente.")
    }
  }

  return { copiado, erro, copiar }
}

interface CreateTokenProps {
  /** Workspaces do usuário — a lista de caixas do passo 1. */
  workspaces: IWorkspace[]
  /** Chamado assim que o POST responde: a lista já recebe o token, mesmo que
   *  o usuário saia do passo 2 pelo X ou pelo Esc. */
  onCreated: (token: ApiTokenCreated) => void
  /** «Concluir» do passo 2 — quem monta o diálogo fecha e desmonta. */
  onClose: () => void
}

const CreateToken = ({ workspaces, onCreated, onClose }: CreateTokenProps) => {
  const [criado, setCriado] = useState<ApiTokenCreated | null>(null)
  const [cliente, setCliente] = useState<Cliente>("claude")
  const segredo = useCopiar()
  const comando = useCopiar()

  const idsAtuais = useMemo(() => workspaces.map(w => w.id_hash), [workspaces])

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: "",
      scopes: [],
      all_workspaces: false,
      workspace_ids: idsAtuais,
      expires_in_days: VALIDADE_PADRAO,
    },
  })

  // A lista de workspaces pode chegar depois de o diálogo abrir. Enquanto o
  // usuário não mexeu nas caixas, «todos marcados» continua sendo o padrão.
  useEffect(() => {
    if (!form.getFieldState("workspace_ids").isDirty) {
      form.setValue("workspace_ids", idsAtuais)
    }
  }, [idsAtuais, form])

  const todos = form.watch("all_workspaces")
  const validade = form.watch("expires_in_days")
  const { isSubmitting } = form.formState

  async function onSubmit(valores: FormValues) {
    const payload: ApiTokenCreate = {
      name: valores.name,
      scopes: ordenarEscopos(valores.scopes),
      workspace_ids: valores.all_workspaces ? null : valores.workspace_ids,
      expires_in_days: valores.expires_in_days,
    }
    const res = await GisFlowService.createApiToken(payload)
    // 422 (validação) e 409 (teto de 20 ativos) chegam com a mensagem do
    // backend; o diálogo fica aberto para o usuário corrigir.
    if (res.error || !res.data) {
      createToast.error("Não foi possível criar o token", res.error?.message)
      return
    }
    setCriado(res.data)
    onCreated(res.data)
    createToast.success("Token criado", res.data.name)
  }

  const clienteAtual = CLIENTES.find(c => c.id === cliente) ?? CLIENTES[0]
  const snippetAtual = snippetCom(clienteAtual.snippet, urlDoMcp())

  return (
    <DialogContent
      // Fechar no meio do submit desmonta o componente durante o await e deixa
      // o usuário sem saber se o token foi criado. As três saídas (Esc,
      // clique-fora e o X) precisam ser cobertas. No passo 2 o clique-fora
      // também fica travado: um clique acidental apagaria o segredo que só
      // aparece uma vez — Esc e o X continuam sendo saídas deliberadas.
      bloqueado={isSubmitting}
      // Com o token na tela, o clique fora não fecha: o segredo aparece uma vez só.
      onInteractOutside={e => { if (criado) e.preventDefault() }}
    >
      <DialogHeader className="pr-6">
        <DialogTitle>{criado ? "Token criado" : "Novo token de acesso"}</DialogTitle>
        <DialogDescription>
          {criado
            ? "Copie o segredo agora e conecte o seu agente."
            : "O token faz em seu nome o que a sua conta já pode fazer — nunca mais que isso. Dê só o que o agente precisa."}
        </DialogDescription>
      </DialogHeader>

      {criado ? (
        // `min-w-0`: filho do grid do DialogContent. Sem isto, o segredo (uma
        // palavra longa) forçaria a largura do grid acima do `max-w-lg`.
        <div className="flex min-w-0 flex-col gap-4 motion-safe:animate-in motion-safe:fade-in-0 motion-safe:duration-200">
          <div className="flex flex-col gap-2">
            <p className="text-sm font-medium text-foreground">Seu token</p>
            <div className="flex items-start gap-2">
              {/* `select-all`: um clique seleciona o segredo inteiro para quem
                  prefere Ctrl+C; `break-all` porque é uma palavra só. */}
              <code
                tabIndex={0}
                aria-label="Segredo do token"
                className="min-w-0 flex-1 select-all whitespace-pre-wrap break-all rounded-lg border border-border bg-muted/60 px-3 py-2.5 font-mono text-xs leading-relaxed outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
              >
                {criado.token}
              </code>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => segredo.copiar(criado.token)}
                className="shrink-0 gap-1.5 max-md:h-10"
              >
                {segredo.copiado
                  ? <TbCheck className="size-4 text-green-500" aria-hidden="true" />
                  : <TbCopy className="size-4" aria-hidden="true" />}
                {segredo.copiado ? "Copiado" : "Copiar"}
              </Button>
            </div>
            {segredo.erro && (
              <p role="alert" className="text-xs text-destructive">{segredo.erro}</p>
            )}
            <p
              role="status"
              className="flex items-start gap-2 rounded-md border border-amber-500/30 bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:bg-amber-500/10 dark:text-amber-400"
            >
              <TbAlertTriangle size={14} className="mt-px shrink-0" aria-hidden="true" />
              <span>Este segredo não será mostrado de novo. Guarde-o agora.</span>
            </p>
          </div>

          <section aria-labelledby="tk-conectar-titulo" className="flex min-w-0 flex-col gap-2">
            <h3 id="tk-conectar-titulo" className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              Conectar seu agente
            </h3>
            {/* Toggle canônico do contrato §1: grupo com aria-pressed, ativo em
                bg-accent, inativo em muted. */}
            <div
              role="group"
              aria-label="Cliente MCP"
              className="inline-flex h-8 w-full overflow-hidden rounded-md border bg-card max-md:h-10 sm:w-auto"
            >
              {CLIENTES.map(c => (
                <button
                  key={c.id}
                  type="button"
                  aria-pressed={cliente === c.id}
                  onClick={() => setCliente(c.id)}
                  className={cn(
                    "flex-1 border-l px-3 text-xs font-medium outline-none transition-colors first:border-l-0 sm:flex-none",
                    "focus-visible:z-10 focus-visible:ring-[3px] focus-visible:ring-ring/50",
                    cliente === c.id ? "bg-accent text-foreground" : "text-muted-foreground hover:bg-accent/60",
                  )}
                >
                  {c.rotulo}
                </button>
              ))}
            </div>
            <div className="flex items-start gap-2">
              <pre className="min-w-0 flex-1 whitespace-pre-wrap break-all rounded-lg border border-border bg-muted/60 px-3 py-2.5 font-mono text-[11px] leading-relaxed">
                {snippetAtual}
              </pre>
              <Button
                type="button"
                size="icon"
                variant="outline"
                onClick={() => comando.copiar(snippetAtual)}
                title="Copiar comando"
                aria-label="Copiar comando"
                className="shrink-0 max-md:size-10"
              >
                {comando.copiado
                  ? <TbCheck className="text-green-500" aria-hidden="true" />
                  : <TbCopy aria-hidden="true" />}
              </Button>
            </div>
            {comando.erro && (
              <p role="alert" className="text-xs text-destructive">{comando.erro}</p>
            )}
            <p className="text-xs text-muted-foreground">{clienteAtual.nota}</p>
            <p className="text-xs text-muted-foreground/80">
              Conecte pelo comando acima. Limites e detalhes em <code className="font-mono">{DOCS_MCP}</code>.
            </p>
          </section>

          <DialogFooter className="border-t border-border pt-4">
            <Button type="button" onClick={onClose} className="max-md:h-10">Concluir</Button>
          </DialogFooter>
        </div>
      ) : (
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="flex min-w-0 flex-col gap-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Nome</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="ex.: agente de relatórios"
                      maxLength={80}
                      autoComplete="off"
                      disabled={isSubmitting}
                      className="max-md:h-10"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="scopes"
              render={({ field }) => (
                <FormItem>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span id="tk-escopos-rotulo" className="text-sm font-medium text-foreground">Escopos</span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      disabled={isSubmitting}
                      onClick={() => field.onChange([...ESCOPOS_SOMENTE_LEITURA])}
                      className="h-7 px-2 text-xs max-md:h-10"
                    >
                      Somente leitura
                    </Button>
                  </div>
                  <div
                    role="group"
                    aria-labelledby="tk-escopos-rotulo"
                    className="grid grid-cols-1 gap-2 sm:grid-cols-2"
                  >
                    {ESCOPOS.map(escopo => (
                      <EscopoCard
                        key={escopo}
                        escopo={escopo}
                        ativo={field.value.includes(escopo)}
                        disabled={isSubmitting}
                        onToggle={() => field.onChange(alternar(field.value, escopo))}
                      />
                    ))}
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="workspace_ids"
              render={({ field }) => (
                <FormItem>
                  <span className="text-sm font-medium text-foreground">Workspaces</span>
                  <div className="flex flex-col gap-2.5 rounded-md border px-3 py-2.5">
                    <div className="flex items-start gap-2">
                      <Checkbox
                        id="tk-todos-workspaces"
                        checked={todos}
                        disabled={isSubmitting}
                        onCheckedChange={v => form.setValue("all_workspaces", v === true, { shouldDirty: true, shouldValidate: form.formState.isSubmitted })}
                        className="mt-0.5"
                      />
                      <Label htmlFor="tk-todos-workspaces" className="cursor-pointer leading-snug">
                        Todos os workspaces, inclusive os que eu entrar depois
                      </Label>
                    </div>
                    {workspaces.length > 0 ? (
                      <ul
                        aria-label="Workspaces do token"
                        className={cn("flex flex-col gap-1.5 border-t border-border/60 pt-2.5 transition-opacity", todos && "opacity-50")}
                      >
                        {workspaces.map(w => (
                          <li key={w.id_hash} className="flex items-center gap-2">
                            <Checkbox
                              id={`tk-ws-${w.id_hash}`}
                              checked={field.value.includes(w.id_hash)}
                              disabled={todos || isSubmitting}
                              onCheckedChange={v => {
                                const proximo = v === true
                                  ? [...field.value, w.id_hash]
                                  : field.value.filter(id => id !== w.id_hash)
                                form.setValue("workspace_ids", proximo, { shouldDirty: true, shouldValidate: form.formState.isSubmitted })
                              }}
                            />
                            <Label htmlFor={`tk-ws-${w.id_hash}`} className="cursor-pointer max-md:min-h-10">
                              {w.name}
                            </Label>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="border-t border-border/60 pt-2.5 text-xs text-muted-foreground">
                        Nenhum workspace carregado. Marque «Todos os workspaces» para seguir.
                      </p>
                    )}
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="expires_in_days"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Validade</FormLabel>
                  <Select
                    value={String(field.value)}
                    disabled={isSubmitting}
                    onValueChange={v => field.onChange(Number(v) as ApiTokenExpiresInDays)}
                  >
                    <FormControl>
                      <SelectTrigger className="w-full max-md:h-10" aria-label="Validade do token">
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {VALIDADES.map(d => (
                        <SelectItem key={d} value={String(d)}>{rotuloDeValidade(d)}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs tabular-nums text-muted-foreground">
                    Expira em {dayjs().add(validade, "day").format("DD/MM/YYYY")}. Depois disso, crie outro token.
                  </p>
                </FormItem>
              )}
            />

            <DialogFooter className="mt-1 flex-wrap gap-2">
              <DialogClose asChild>
                <Button type="button" variant="outline" disabled={isSubmitting} className="max-md:h-10">Cancelar</Button>
              </DialogClose>
              <Button type="submit" disabled={isSubmitting} className="gap-1 max-md:h-10">
                {isSubmitting && <TbLoader2 className="size-4 motion-safe:animate-spin" aria-hidden="true" />}
                {isSubmitting ? "Criando…" : "Criar token"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      )}
    </DialogContent>
  )
}

/**
 * Cartão de escopo: um botão `aria-pressed` (multi-seleção — cada escopo liga
 * e desliga por si), na mesma moldura do `SelectCard` dos executores, mais o
 * check que diz «este está marcado» quando há vários ligados.
 */
function EscopoCard({ escopo, ativo, disabled, onToggle }: {
  escopo: ApiTokenScope
  ativo: boolean
  disabled?: boolean
  onToggle: () => void
}) {
  const Icone = ESCOPO_ICONES[escopo]
  return (
    <button
      type="button"
      aria-pressed={ativo}
      disabled={disabled}
      onClick={onToggle}
      className={cn(
        "flex items-start gap-2.5 rounded-lg border px-3 py-2.5 text-left outline-none transition-colors max-md:min-h-10",
        "focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:opacity-50",
        ativo ? "border-primary bg-primary/10" : "border-border bg-transparent hover:border-primary/40 hover:bg-muted/40",
      )}
    >
      <span className={cn(
        "flex size-7 shrink-0 items-center justify-center rounded-md border bg-background text-base",
        ativo ? "border-primary/30 text-primary" : "border-border text-muted-foreground",
      )}>
        <Icone aria-hidden="true" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-center justify-between gap-1.5 text-sm font-semibold text-foreground">
          {ESCOPO_ROTULOS[escopo]}
          {ativo && <TbCheck className="size-4 shrink-0 text-primary" aria-hidden="true" />}
        </span>
        <span className="mt-0.5 block text-xs leading-snug text-muted-foreground">{ESCOPO_DESCRICOES[escopo]}</span>
      </span>
    </button>
  )
}

export default CreateToken
