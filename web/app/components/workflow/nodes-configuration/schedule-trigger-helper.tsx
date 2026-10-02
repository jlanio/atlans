"use client"
import { useEffect, useMemo, useRef, useState } from "react"
import {
  TbAlertTriangle, TbCalendarMonth, TbCalendarRepeat, TbCalendarWeek, TbClock, TbRepeat,
} from "react-icons/tb"
import { Label } from "@/app/components/ui/label"
import { Input } from "@/app/components/ui/input"
import { Switch } from "@/app/components/ui/switch"
import { Separator } from "@/app/components/ui/separator"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/app/components/ui/select"
import { cn } from "@/lib/utils"
import {
  type EstadoAgenda, type Frequencia, type UnidadeIntervalo,
  descrever, fusoPadraoDosCampos, gerarCampos, lerEstado, NOME_DIA_CURTO, NOME_DIA_LONGO,
  opcoesDeFuso, proximasExecucoes, resumoSalvo, validarAvancado,
} from "./schedule-recurrence"
import type { INodesPropertyAPI } from "@/service/types"

interface Props {
  values: Record<string, string | number | boolean> | undefined
  setNodeField: (field: string, value: string | number | boolean) => void
  hasUnsaved: boolean
  /** Id do nó — re-inicializa o construtor ao trocar de nó. */
  nodeId?: string
  /**
   * Os campos do nó no catálogo do servidor. O `default` do `timezone` é o fuso
   * padrão da instalação (AGENDAMENTO_FUSO_PADRAO): é ele que vale para um nó
   * sem fuso, e não um fixo aqui.
   */
  campos?: INodesPropertyAPI[]
}

const UNIDADES: { value: UnidadeIntervalo; label: string }[] = [
  { value: "seconds", label: "segundos" },
  { value: "minutes", label: "minutos" },
  { value: "hours",   label: "horas" },
  { value: "days",    label: "dias" },
]

const FREQS: { value: Frequencia; label: string; icon: typeof TbClock }[] = [
  { value: "intervalo", label: "Intervalo",    icon: TbRepeat },
  { value: "diario",    label: "Diariamente",  icon: TbClock },
  { value: "semanal",   label: "Semanalmente", icon: TbCalendarWeek },
  { value: "mensal",    label: "Mensalmente",  icon: TbCalendarMonth },
  { value: "avancado",  label: "Avançado",     icon: TbCalendarRepeat },
]

const pad = (n: number) => String(n).padStart(2, "0")

export default function ScheduleTriggerHelper({ values, setNodeField, hasUnsaved, nodeId, campos }: Props) {
  const fusoPadrao = fusoPadraoDosCampos(campos)
  const [e, setE] = useState<EstadoAgenda>(() => lerEstado(values, fusoPadrao))
  const eRef = useRef(e)
  eRef.current = e

  // Sincroniza o estado local com os valores salvos. Necessário porque o modal
  // MONTA este helper com `values=undefined` e só popula os valores num efeito
  // seguinte (mesmo nodeId), e também reaproveita o componente ao trocar de nó.
  // Sem isto, abrir um nó salvo mostraria os padrões e a edição gravaria por
  // cima da regra real. A comparação é canônica (via gerarCampos) para NÃO
  // re-inicializar no eco das próprias gravações nem por cron equivalente.
  useEffect(() => {
    const alvo = lerEstado(values, fusoPadrao)
    if (JSON.stringify(gerarCampos(alvo)) !== JSON.stringify(gerarCampos(eRef.current))) {
      setE(alvo)
    }
  }, [values, nodeId, fusoPadrao])

  /** Grava só os campos que MUDARAM de fato. Evita canonicalizar um cron
   * equivalente ('00 09' -> '0 9') e fazer o backend (que compara por string)
   * apagar e recriar o schedule à toa — o que pularia a ocorrência do dia. */
  function escrever(campos: Record<string, string | number | boolean>) {
    for (const k of Object.keys(campos)) {
      const v = campos[k]
      if (String(v) !== String(values?.[k] ?? "")) setNodeField(k, v)
    }
  }

  /** Muda um campo que DEFINE a recorrência e regrava a expressão (diff-only). */
  function atualizar(patch: Partial<EstadoAgenda>) {
    const ne = { ...e, ...patch }
    setE(ne)
    const campos: Record<string, string | number | boolean> = { ...gerarCampos(ne) }
    // Expressão avançada inválida: NÃO toca em strategy nem em nenhuma das
    // expressões — senão gravaríamos strategy=cron/rrule + a expressão vazia
    // da outra aba, apagando o agendamento válido anterior. Só timezone/active/
    // interval/unit podem mudar; o schedule salvo fica intacto de fato.
    if (ne.freq === "avancado" && validarAvancado(ne)) {
      delete campos.strategy
      delete campos.cron_expression
      delete campos.rrule_expression
    }
    escrever(campos)
  }

  /** Fuso e "ativo" não mexem na expressão — gravam só o próprio campo, para
   * não regravar (e churnar) o cron/rrule. */
  function setFuso(v: string) {
    setE(p => ({ ...p, timezone: v }))
    if (String(v) !== String(values?.timezone ?? "")) setNodeField("timezone", v)
  }
  function setAtivo(v: boolean) {
    setE(p => ({ ...p, active: v }))
    if (String(v) !== String(values?.active ?? "")) setNodeField("active", v)
  }

  const horaStr = `${pad(e.hora)}:${pad(e.minuto)}`
  function setHora(hhmm: string) {
    const [h, m] = hhmm.split(":").map(Number)
    if (Number.isFinite(h) && Number.isFinite(m)) atualizar({ hora: h, minuto: m })
  }
  function toggleDia(d: number) {
    const tem = e.weekdays.includes(d)
    if (tem && e.weekdays.length === 1) return // nunca deixa sem nenhum dia
    atualizar({ weekdays: tem ? e.weekdays.filter(x => x !== d) : [...e.weekdays, d] })
  }

  const frase = descrever(e)
  const erroAvancado = validarAvancado(e)
  const runs = useMemo(() => proximasExecucoes(e, 5), [e])
  // Todos os fusos IANA (mais o atual, se for um nome antigo). A lista muda só
  // com o fuso escolhido: montá-la custa ~400 formatações de deslocamento.
  const fusos = useMemo(() => opcoesDeFuso(e.timezone), [e.timezone])
  const tzLabel = (fusos.find(t => t.value === e.timezone) || { label: e.timezone }).label
  const fmt = useMemo(() => {
    try {
      return new Intl.DateTimeFormat("pt-BR", {
        timeZone: e.timezone, weekday: "short", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
      })
    } catch { return new Intl.DateTimeFormat("pt-BR", { weekday: "short", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) }
  }, [e.timezone])

  // Guardas honestas, derivadas do que o agendador realmente faz.
  const aviso = avisoDe(e)

  return (
    <div className="flex flex-col gap-4 mt-1 px-1 pb-4">
      {/* Frequência */}
      <div className="flex flex-col gap-1.5">
        <Label>Repetir</Label>
        <div role="group" aria-label="Frequência" className="flex flex-wrap gap-1.5">
          {FREQS.map(f => {
            const Icon = f.icon, ativo = e.freq === f.value
            return (
              <button
                key={f.value} type="button" aria-pressed={ativo}
                onClick={() => atualizar({ freq: f.value })}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-medium transition-colors outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 max-md:min-h-9",
                  ativo
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border text-muted-foreground hover:text-foreground hover:border-foreground/30",
                )}
              >
                <Icon className="size-3.5" aria-hidden="true" /> {f.label}
              </button>
            )
          })}
        </div>
      </div>

      <Separator />

      {/* ── Intervalo ─────────────────────────────────────────────────────── */}
      {e.freq === "intervalo" && (
        <div className="flex items-end gap-2">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="intervalo">A cada</Label>
            <Input
              id="intervalo" type="number" min={1} value={e.intervalo}
              onChange={ev => atualizar({ intervalo: Math.max(1, parseInt(ev.target.value) || 1) })}
              className="w-24 tabular-nums"
            />
          </div>
          <div className="flex flex-col gap-1.5 flex-1">
            <Label>Unidade</Label>
            <Select value={e.unidade} onValueChange={v => atualizar({ unidade: v as UnidadeIntervalo })}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {UNIDADES.map(u => <SelectItem key={u.value} value={u.value}>{u.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </div>
      )}

      {/* ── Diariamente ───────────────────────────────────────────────────── */}
      {e.freq === "diario" && (
        <div className="flex items-end gap-2">
          <div className="flex flex-col gap-1.5 flex-1">
            <Label htmlFor="hora-d">Horário</Label>
            <Input id="hora-d" type="time" value={horaStr} onChange={ev => setHora(ev.target.value)} />
          </div>
          <div className="flex flex-col gap-1.5 w-36">
            <Label htmlFor="everydays">Repetir a cada</Label>
            <div className="flex items-center gap-1.5">
              <Input
                id="everydays" type="number" min={1} max={365} value={e.everyDays}
                onChange={ev => atualizar({ everyDays: Math.min(365, Math.max(1, parseInt(ev.target.value) || 1)) })}
                className="w-16 tabular-nums"
              />
              <span className="text-sm text-muted-foreground">dia(s)</span>
            </div>
          </div>
        </div>
      )}

      {/* ── Semanalmente ──────────────────────────────────────────────────── */}
      {e.freq === "semanal" && (
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <Label>Dias da semana</Label>
            <div className="flex flex-wrap gap-1.5">
              {NOME_DIA_CURTO.map((nome, i) => {
                const ativo = e.weekdays.includes(i)
                return (
                  <button
                    key={i} type="button" aria-pressed={ativo} aria-label={NOME_DIA_LONGO[i]}
                    onClick={() => toggleDia(i)}
                    className={cn(
                      "grid size-9 place-items-center rounded-full border text-xs font-semibold transition-colors outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50",
                      ativo
                        ? "border-primary bg-primary/15 text-primary"
                        : "border-border text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {nome.charAt(0).toUpperCase()}
                  </button>
                )
              })}
            </div>
            <div className="flex flex-wrap gap-1.5 mt-0.5">
              {[
                { l: "Seg a sex", v: [1, 2, 3, 4, 5] },
                { l: "Fim de semana", v: [0, 6] },
                { l: "Todos", v: [0, 1, 2, 3, 4, 5, 6] },
              ].map(q => (
                <button
                  key={q.l} type="button" onClick={() => atualizar({ weekdays: q.v })}
                  className="rounded-full border border-border px-2.5 py-0.5 text-[11px] text-muted-foreground hover:text-foreground hover:border-foreground/30 outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
                >
                  {q.l}
                </button>
              ))}
            </div>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="hora-s">Horário</Label>
            <Input id="hora-s" type="time" value={horaStr} onChange={ev => setHora(ev.target.value)} />
          </div>
        </div>
      )}

      {/* ── Mensalmente ───────────────────────────────────────────────────── */}
      {e.freq === "mensal" && (
        <div className="flex flex-col gap-3">
          <div className="flex items-end gap-2">
            <div className="flex flex-col gap-1.5 flex-1">
              <Label>No dia</Label>
              <Select
                value={e.monthLast ? "last" : String(e.monthDay)}
                onValueChange={v => v === "last" ? atualizar({ monthLast: true }) : atualizar({ monthLast: false, monthDay: +v })}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="last">Último dia</SelectItem>
                  {Array.from({ length: 31 }, (_, i) => i + 1).map(d => (
                    <SelectItem key={d} value={String(d)}>Dia {d}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-1.5 w-36">
              <Label htmlFor="hora-m">Horário</Label>
              <Input id="hora-m" type="time" value={horaStr} onChange={ev => setHora(ev.target.value)} />
            </div>
          </div>
        </div>
      )}

      {/* ── Avançado ──────────────────────────────────────────────────────── */}
      {e.freq === "avancado" && (
        <div className="flex flex-col gap-2">
          <div className="flex gap-1.5">
            {(["cron", "rrule"] as const).map(t => (
              <button
                key={t} type="button" aria-pressed={e.advTipo === t}
                onClick={() => atualizar({ advTipo: t })}
                className={cn(
                  "rounded-md border px-2.5 py-1 text-xs font-medium outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50",
                  e.advTipo === t ? "border-border bg-accent text-accent-foreground" : "border-border text-muted-foreground hover:text-foreground",
                )}
              >
                {t === "cron" ? "Cron" : "RRule"}
              </button>
            ))}
          </div>
          {e.advTipo === "cron" ? (
            <div className="flex flex-col gap-1.5">
              <Input
                value={e.advCron} onChange={ev => atualizar({ advCron: ev.target.value })}
                placeholder="0 9 * * *" className="font-mono text-sm"
                aria-label="Expressão cron"
              />
              <p className="text-[11px] text-muted-foreground">
                Formato: <span className="font-mono">minuto hora dia mês dia-semana</span>
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-1.5">
              <textarea
                value={e.advRrule} onChange={ev => atualizar({ advRrule: ev.target.value })}
                placeholder="FREQ=WEEKLY;BYDAY=MO,WE,FR;BYHOUR=9;BYMINUTE=0" rows={3}
                aria-label="Expressão RRule"
                className="flex min-h-[72px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
              />
              <p className="text-[11px] text-muted-foreground">RRule (RFC 5545) — para recorrências que o cron não expressa.</p>
            </div>
          )}
          {erroAvancado && (
            <p className="flex items-start gap-1.5 text-xs text-destructive">
              <TbAlertTriangle className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
              {erroAvancado} Enquanto estiver assim, o agendamento anterior é mantido.
            </p>
          )}
        </div>
      )}

      {/* Fuso horário */}
      <div className="flex flex-col gap-1.5">
        <Label>Fuso horário</Label>
        <Select value={e.timezone} onValueChange={setFuso}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            {fusos.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {/* Ativo */}
      <div className="flex flex-row items-center justify-between rounded-lg border p-3">
        <div>
          <Label className="text-sm font-medium">Agendamento ativo</Label>
          <p className="text-xs text-muted-foreground mt-0.5">Inativo, o workflow não roda sozinho.</p>
        </div>
        <Switch checked={e.active} onCheckedChange={setAtivo} aria-label="Agendamento ativo" />
      </div>

      {/* Aviso */}
      {aviso && (
        <div className="flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-foreground">
          <TbAlertTriangle className="mt-0.5 size-3.5 shrink-0 text-amber-600 dark:text-amber-400" aria-hidden="true" />
          <span>{aviso}</span>
        </div>
      )}

      {/* Prévia */}
      <div className="rounded-lg border overflow-hidden">
        <div className="flex items-start gap-2 bg-muted px-3 py-2.5">
          <TbClock className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
          <div className="min-w-0">
            <p className="text-sm font-semibold text-balance">{frase}</p>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Fuso: {tzLabel}{!e.active && <span className="ml-1 text-amber-600 dark:text-amber-400">· inativo</span>}
            </p>
          </div>
        </div>
        <ul className="p-1.5" aria-label="Próximas execuções">
          {runs === null ? (
            <li className="px-2 py-1.5 text-xs text-muted-foreground">Prévia indisponível para esta expressão.</li>
          ) : runs.length === 0 ? (
            <li className="px-2 py-1.5 text-xs text-muted-foreground">Nenhuma execução futura com esta regra.</li>
          ) : (
            runs.map((d, i) => (
              <li key={i} className={cn("flex items-center gap-2 rounded-md px-2 py-1.5 text-xs", i === 0 && "bg-primary/5")}>
                <span className={cn("size-1.5 rounded-full bg-primary", i !== 0 && "opacity-40")} aria-hidden="true" />
                <span className="tabular-nums">{capitalizar(fmt.format(d))}</span>
                <span className="ml-auto tabular-nums text-muted-foreground">{relativo(d)}</span>
              </li>
            ))
          )}
        </ul>
        <details className="border-t">
          <summary className="cursor-pointer list-none px-3 py-2 text-[11px] text-muted-foreground hover:text-foreground">
            Ver o que será salvo
          </summary>
          <div className="px-3 pb-2.5">
            <code className="block overflow-x-auto whitespace-nowrap rounded-md bg-muted px-2.5 py-1.5 font-mono text-[11px]">
              {resumoSalvo(e)}
            </code>
          </div>
        </details>
      </div>

      {hasUnsaved && <p className="self-end text-xs text-amber-600 dark:text-amber-400">Alterações não salvas</p>}
    </div>
  )
}

function avisoDe(e: EstadoAgenda): string | null {
  if (e.freq === "intervalo") {
    const seg = e.intervalo * ({ seconds: 1, minutes: 60, hours: 3600, days: 86400 }[e.unidade])
    if (seg < 30) return "O agendador verifica a cada ~30 s; intervalos menores rodam no máximo a cada ~30 s."
    if (seg < 300) return "Cadência curta: isso gera muitas execuções por dia."
  }
  if (e.freq === "mensal" && !e.monthLast && e.monthDay > 28)
    return `Meses sem o dia ${e.monthDay} são pulados (ex.: fevereiro). Para rodar todo mês, use “Último dia”.`
  return null
}

function capitalizar(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1)
}

function relativo(d: Date): string {
  const ms = d.getTime() - Date.now()
  const min = Math.round(ms / 60000)
  if (min < 1) return "agora"
  if (min < 60) return `em ${min} min`
  const hrs = Math.round(min / 60)
  if (hrs < 48) return `em ${hrs} h`
  const dias = Math.round(hrs / 24)
  return `em ${dias} dias`
}
