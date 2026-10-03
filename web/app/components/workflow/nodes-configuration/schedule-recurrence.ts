// Pure logic of the schedule builder (no React), so it is testable without
// mounting a screen. The ScheduleTrigger node stores the SAME fields as always
// (`strategy`, `cron_expression`, `interval`, `unit`, `timezone`, `active`,
// `rrule_expression`) — this module only translates between those fields and a
// "frequency first" state the person understands, and computes the next runs.
//
// Mapping to what the scheduler (app/core/async_scheduler.py) can execute:
//   • Interval (every N units)       → strategy=interval (croniter not involved).
//   • Daily (every day at H:M)       → cron  "M H * * *".
//   • Every N days at H:M            → rrule "FREQ=DAILY;INTERVAL=N;BYHOUR=H;BYMINUTE=M"
//        (cron "*/N" on day-of-month RESTARTS every month — it isn't "every N days").
//   • Weekly (days at H:M)           → cron  "M H * * d,d".
//   • Monthly on day D at H:M        → cron  "M H D * *"  (months without day D are SKIPPED).
//   • Monthly on the last day        → rrule "FREQ=MONTHLY;BYMONTHDAY=-1;BYHOUR=H;BYMINUTE=M"
//        (standard cron/croniter can't express "last day").
//   • Advanced                       → raw cron or rrule, for those who know.

export type Frequencia = "intervalo" | "diario" | "semanal" | "mensal" | "avancado"
export type UnidadeIntervalo = "seconds" | "minutes" | "hours" | "days"
export type TipoAvancado = "cron" | "rrule"

export interface EstadoAgenda {
  freq: Frequencia
  intervalo: number
  unidade: UnidadeIntervalo
  hora: number        // 0-23
  minuto: number      // 0-59
  everyDays: number   // "daily": every N days (1 = every day)
  weekdays: number[]  // 0=Sunday … 6=Saturday (cron convention)
  monthDay: number    // 1-31
  monthLast: boolean
  timezone: string
  active: boolean
  advTipo: TipoAvancado
  advCron: string
  advRrule: string
}

// The default time zone is the INSTALLATION's (AGENDAMENTO_FUSO_PADRAO on the
// server), and it arrives here through the node catalog: it is the `default` of
// the ScheduleTrigger's `timezone` field (`fusoPadraoDosCampos`). That way a
// node without an explicit timezone doesn't see the preview in a different time
// zone than it would run in. This is only the fallback for when the catalog
// didn't come — the same default as a server without configuration.
export const FUSO_DE_RESERVA = "UTC"
const CRON_PADRAO = "0 9 * * *"

const DIAS_CURTOS = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"]
const DIAS_LONGOS = ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"]
// RRule BYDAY (RFC 5545): SU=Sunday … SA=Saturday, at the same index as cron.
const BYDAY = ["SU", "MO", "TU", "WE", "TH", "FR", "SA"]

// ── Field values ──────────────────────────────────────────────────────────────

type Valores = Record<string, string | number | boolean> | undefined

function texto(v: Valores, chave: string, padrao = ""): string {
  const x = v?.[chave]
  return x === undefined || x === null ? padrao : String(x)
}
function inteiro(v: Valores, chave: string, padrao: number): number {
  const n = parseInt(String(v?.[chave] ?? ""), 10)
  return Number.isFinite(n) ? n : padrao
}

function estadoInicial(fusoPadrao: string): EstadoAgenda {
  return {
    freq: "diario", intervalo: 15, unidade: "minutes", hora: 9, minuto: 0,
    everyDays: 1, weekdays: [1, 2, 3, 4, 5], monthDay: 1, monthLast: false,
    timezone: fusoPadrao, active: true, advTipo: "cron", advCron: CRON_PADRAO, advRrule: "",
  }
}

/** The installation's default time zone: the `default` of the `timezone` field in the node catalog. */
export function fusoPadraoDosCampos(campos?: { name: string; default?: unknown }[]): string {
  const padrao = campos?.find(c => c.name === "timezone")?.default
  return typeof padrao === "string" && padrao.trim() ? padrao.trim() : FUSO_DE_RESERVA
}

/** Translates the fields stored on the node into the builder state. */
export function lerEstado(valores: Valores, fusoPadrao: string = FUSO_DE_RESERVA): EstadoAgenda {
  const e = estadoInicial(fusoPadrao)
  e.timezone = texto(valores, "timezone", fusoPadrao) || fusoPadrao
  // `Boolean("false")` is true — explicitly coerces strings/0 (legacy data).
  const a = valores?.active
  e.active = !(a === false || a === "false" || a === 0 || a === "0")
  e.intervalo = Math.max(1, inteiro(valores, "interval", 15))
  const unidade = texto(valores, "unit", "minutes")
  e.unidade = (["seconds", "minutes", "hours", "days"].includes(unidade) ? unidade : "minutes") as UnidadeIntervalo
  e.advCron = texto(valores, "cron_expression", CRON_PADRAO) || CRON_PADRAO
  e.advRrule = texto(valores, "rrule_expression", "")

  const strategy = texto(valores, "strategy", "cron") || "cron"

  if (strategy === "interval") {
    e.freq = "intervalo"
    return e
  }
  if (strategy === "rrule") {
    // The saved strategy is rrule: the advanced mode's type MUST be "rrule".
    // Without this, an rrule that matches a simple mode (e.g. "every 3 days")
    // loads with advTipo="cron" (the estadoInicial default). Opening "Avançado"
    // (Advanced) the person lands on the cron tab — not on the rrule that was
    // saved — and a "Salvar" from there writes strategy=cron with CRON_PADRAO,
    // silently erasing the rrule.
    e.advTipo = "rrule"
    return aplicarRrule(e, e.advRrule)
  }
  // strategy === "cron" (or absent): tries to map to a builder mode.
  return aplicarCron(e, e.advCron)
}

function aplicarCron(e: EstadoAgenda, expr: string): EstadoAgenda {
  const p = String(expr || "").trim().split(/\s+/)
  const avancado = (): EstadoAgenda => ({ ...e, freq: "avancado", advTipo: "cron", advCron: expr })
  if (p.length !== 5) return avancado()
  const [min, hora, dom, mes, dow] = p
  const m = /^\d+$/.test(min) ? +min : null
  const h = /^\d+$/.test(hora) ? +hora : null
  // Fixed minute and hour are the basis of every calendar mode.
  if (m === null || h === null || m > 59 || h > 23 || mes !== "*") return avancado()

  // Daily: "M H * * *"
  if (dom === "*" && dow === "*") return { ...e, freq: "diario", everyDays: 1, hora: h, minuto: m }
  // Weekly: "M H * * d,d" (day-of-week only)
  if (dom === "*" && dow !== "*") {
    const dias = expandirDow(dow)
    return dias ? { ...e, freq: "semanal", weekdays: dias, hora: h, minuto: m } : avancado()
  }
  // Monthly: "M H D * *" (day-of-month only)
  if (dow === "*" && /^\d+$/.test(dom)) {
    const d = +dom
    if (d >= 1 && d <= 31) return { ...e, freq: "mensal", monthDay: d, monthLast: false, hora: h, minuto: m }
  }
  return avancado()
}

/** Expande "1-5" / "2,4" / "1" em [1..5] / [2,4] / [1]; null se tiver algo fora disso. */
function expandirDow(dow: string): number[] | null {
  const out: number[] = []
  for (const parte of dow.split(",")) {
    const faixa = /^(\d)-(\d)$/.exec(parte)
    if (faixa) {
      const de = +faixa[1], ate = +faixa[2]
      if (de > ate || de > 7 || ate > 7) return null   // croniter aceita 0-7 (7=domingo)
      for (let x = de; x <= ate; x++) out.push(x % 7)
    } else if (/^\d$/.test(parte)) {
      const n = +parte
      if (n > 7) return null                            // 8/9 are invalid for croniter → falls into advanced
      out.push(n % 7)
    } else {
      return null
    }
  }
  const unicos = Array.from(new Set(out)).sort((a, b) => a - b)
  return unicos.length ? unicos : null
}

function aplicarRrule(e: EstadoAgenda, expr: string): EstadoAgenda {
  const partes: Record<string, string> = {}
  String(expr || "").replace(/^RRULE:/i, "").split(";").forEach(kv => {
    const i = kv.indexOf("=")
    if (i > 0) partes[kv.slice(0, i).trim().toUpperCase()] = kv.slice(i + 1).trim()
  })
  const avancado = (): EstadoAgenda => ({ ...e, freq: "avancado", advTipo: "rrule", advRrule: expr })
  const freq = (partes.FREQ || "").toUpperCase()
  const h = /^\d+$/.test(partes.BYHOUR || "") ? +partes.BYHOUR : null
  const m = /^\d+$/.test(partes.BYMINUTE || "") ? +partes.BYMINUTE : null
  if (h === null || m === null || h > 23 || m > 59) return avancado()

  if (freq === "DAILY") {
    const n = Math.max(1, /^\d+$/.test(partes.INTERVAL || "") ? +partes.INTERVAL : 1)
    // Only recognizes the shape the builder generates (no extra BYDAY/BYMONTHDAY).
    if (partes.BYDAY || partes.BYMONTHDAY) return avancado()
    return { ...e, freq: "diario", everyDays: n, hora: h, minuto: m }
  }
  if (freq === "WEEKLY") {
    if (partes.INTERVAL && +partes.INTERVAL !== 1) return avancado()
    const dias = (partes.BYDAY || "").split(",").map(d => BYDAY.indexOf(d.trim().toUpperCase())).filter(i => i >= 0)
    if (!dias.length) return avancado()
    return { ...e, freq: "semanal", weekdays: Array.from(new Set(dias)).sort((a, b) => a - b), hora: h, minuto: m }
  }
  if (freq === "MONTHLY") {
    if (partes.INTERVAL && +partes.INTERVAL !== 1) return avancado()
    const bmd = (partes.BYMONTHDAY || "").trim()
    if (bmd === "-1") return { ...e, freq: "mensal", monthLast: true, hora: h, minuto: m }
    if (/^\d+$/.test(bmd) && +bmd >= 1 && +bmd <= 31) return { ...e, freq: "mensal", monthDay: +bmd, monthLast: false, hora: h, minuto: m }
  }
  return avancado()
}

// ── Estado → campos gravados ──────────────────────────────────────────────────

export interface CamposAgenda {
  strategy: "cron" | "interval" | "rrule"
  cron_expression: string
  interval: number
  unit: UnidadeIntervalo
  rrule_expression: string
  timezone: string
  active: boolean
}

const hhmm = (e: EstadoAgenda) => ({ m: clamp(e.minuto, 0, 59), h: clamp(e.hora, 0, 23) })
function clamp(n: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, Math.round(Number.isFinite(n) ? n : min)))
}

/** Produces the COMPLETE, canonical set of fields to persist for the state. */
export function gerarCampos(e: EstadoAgenda): CamposAgenda {
  const base: CamposAgenda = {
    strategy: "cron", cron_expression: "", interval: Math.max(1, e.intervalo),
    unit: e.unidade, rrule_expression: "", timezone: e.timezone || FUSO_DE_RESERVA, active: e.active,
  }
  const { m, h } = hhmm(e)

  if (e.freq === "intervalo") {
    return { ...base, strategy: "interval" }
  }
  if (e.freq === "diario") {
    if (e.everyDays <= 1) return { ...base, strategy: "cron", cron_expression: `${m} ${h} * * *` }
    return { ...base, strategy: "rrule", rrule_expression: `FREQ=DAILY;INTERVAL=${Math.max(2, Math.round(e.everyDays))};BYHOUR=${h};BYMINUTE=${m};BYSECOND=0` }
  }
  if (e.freq === "semanal") {
    const dias = (e.weekdays.length ? Array.from(new Set(e.weekdays)).sort((a, b) => a - b) : [1]).join(",")
    return { ...base, strategy: "cron", cron_expression: `${m} ${h} * * ${dias}` }
  }
  if (e.freq === "mensal") {
    if (e.monthLast) return { ...base, strategy: "rrule", rrule_expression: `FREQ=MONTHLY;BYMONTHDAY=-1;BYHOUR=${h};BYMINUTE=${m};BYSECOND=0` }
    return { ...base, strategy: "cron", cron_expression: `${m} ${h} ${clamp(e.monthDay, 1, 31)} * *` }
  }
  // advanced
  if (e.advTipo === "rrule") return { ...base, strategy: "rrule", rrule_expression: e.advRrule }
  return { ...base, strategy: "cron", cron_expression: e.advCron }
}

// ── Frase em pt-BR ────────────────────────────────────────────────────────────

const UNIDADE_TXT: Record<UnidadeIntervalo, [string, string]> = {
  seconds: ["segundo", "segundos"], minutes: ["minuto", "minutos"],
  hours: ["hora", "horas"], days: ["dia", "dias"],
}
const hhmmStr = (e: EstadoAgenda) => `${String(clamp(e.hora, 0, 23)).padStart(2, "0")}:${String(clamp(e.minuto, 0, 59)).padStart(2, "0")}`

export function descrever(e: EstadoAgenda): string {
  const hora = hhmmStr(e)
  if (e.freq === "intervalo") {
    const n = Math.max(1, e.intervalo), par = UNIDADE_TXT[e.unidade]
    return `A cada ${n} ${n === 1 ? par[0] : par[1]}`
  }
  if (e.freq === "diario") return e.everyDays <= 1 ? `Todos os dias às ${hora}` : `A cada ${e.everyDays} dias às ${hora}`
  if (e.freq === "semanal") {
    const ds = Array.from(new Set(e.weekdays)).sort((a, b) => a - b)
    if (!ds.length) return "Escolha ao menos um dia da semana"
    if (ds.length === 7) return `Todos os dias às ${hora}`
    if (ds.join() === "1,2,3,4,5") return `De segunda a sexta às ${hora}`
    if (ds.join() === "0,6") return `Sábado e domingo às ${hora}`
    return `Toda ${ds.map(d => DIAS_CURTOS[d]).join(", ")} às ${hora}`
  }
  if (e.freq === "mensal") return e.monthLast ? `No último dia do mês às ${hora}` : `Todo dia ${e.monthDay} às ${hora}`
  // advanced
  if (e.advTipo === "rrule") return e.advRrule ? "Regra RRule personalizada" : "Defina a expressão RRule"
  return descreverCron(e.advCron)
}

/** Best-effort description of a raw cron (advanced mode). */
export function descreverCron(expr: string): string {
  const p = String(expr || "").trim().split(/\s+/)
  if (p.length !== 5) return "Expressão inválida (5 campos: min hora dia mês dia-semana)"
  const [min, hora, dom, mes, dow] = p
  if (expr.trim() === "* * * * *") return "A cada minuto"
  const passo = /^\*\/(\d+)$/.exec(min)
  if (passo && hora === "*" && dom === "*" && mes === "*" && dow === "*")
    return `A cada ${passo[1]} minuto${passo[1] === "1" ? "" : "s"}`
  const m = /^\d+$/.test(min) ? +min : null
  const h = /^\d+$/.test(hora) ? +hora : null
  if (m === null || h === null) return `Personalizado: ${expr}`
  const hhmmTxt = `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`
  if (dom === "*" && mes === "*" && dow === "*") return `Diariamente às ${hhmmTxt}`
  if (dom === "*" && mes === "*" && dow !== "*") {
    const dias = expandirDow(dow)
    if (dias) return `${dias.map(d => DIAS_CURTOS[d]).join(", ")} às ${hhmmTxt}`
  }
  if (/^\d+$/.test(dom) && mes === "*" && dow === "*") return `Todo dia ${dom} às ${hhmmTxt}`
  return `Personalizado: ${expr}`
}

/**
 * Validation error for ADVANCED mode (null = ok). Light on purpose — mirrors
 * what the scheduler would reject (cron ≠ 5 fields; empty rrule/without FREQ)
 * so the client doesn't write an expression that would silently erase the schedule.
 */
export function validarAvancado(e: EstadoAgenda): string | null {
  if (e.freq !== "avancado") return null
  if (e.advTipo === "cron") {
    const p = String(e.advCron || "").trim().split(/\s+/).filter(Boolean)
    if (p.length !== 5) return "A expressão cron precisa ter 5 campos: minuto hora dia mês dia-semana."
    return null
  }
  const r = String(e.advRrule || "").trim()
  if (!r) return "Informe a expressão RRule."
  if (!/FREQ=/i.test(r)) return "A RRule precisa conter FREQ= (RFC 5545)."
  return null
}

/** Summary of what will be saved (shown in "ver o que será salvo"). */
export function resumoSalvo(e: EstadoAgenda): string {
  const c = gerarCampos(e)
  if (c.strategy === "interval") return `intervalo: ${c.interval} (${c.unit})`
  if (c.strategy === "rrule") return `rrule: ${c.rrule_expression}`
  return `cron: ${c.cron_expression}`
}

// ── Next runs (same semantics as async_scheduler) ─────────────────────────────

interface ParteFuso { y: number; mo: number; d: number; h: number; mi: number; wd: number }

function partesNoFuso(date: Date, tz: string): ParteFuso {
  const f = new Intl.DateTimeFormat("en-CA", {
    timeZone: tz, hour12: false, year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", weekday: "short",
  })
  const p: Record<string, string> = {}
  for (const x of f.formatToParts(date)) p[x.type] = x.value
  const wd = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].indexOf(p.weekday)
  return { y: +p.year, mo: +p.month, d: +p.day, h: +(p.hour === "24" ? "0" : p.hour), mi: +p.minute, wd }
}

/** UTC instant matching the "wall clock" time (y-mo-d h:mi) in the time zone. */
function utcDaParede(y: number, mo: number, d: number, h: number, mi: number, tz: string): Date {
  let ts = Date.UTC(y, mo - 1, d, h, mi, 0)
  for (let i = 0; i < 3; i++) {
    const p = partesNoFuso(new Date(ts), tz)
    const visto = Date.UTC(p.y, p.mo - 1, p.d, p.h, p.mi, 0)
    const querido = Date.UTC(y, mo - 1, d, h, mi, 0)
    if (visto === querido) break
    ts += querido - visto
  }
  return new Date(ts)
}

function ultimoDiaDoMes(y: number, mo1: number): number {
  return new Date(Date.UTC(y, mo1, 0)).getUTCDate() // mo1 = month 1-12
}

/**
 * Next `count` runs starting from `agora` (default: new Date()), in the state's
 * time zone. Returns null when the preview isn't possible (advanced without a
 * recognized shape). Mirrors what async_scheduler would compute.
 */
export function proximasExecucoes(e: EstadoAgenda, count = 5, agora: Date = new Date()): Date[] | null {
  const out: Date[] = []
  const tz = e.timezone || FUSO_DE_RESERVA
  const { m, h } = hhmm(e)

  if (e.freq === "intervalo") {
    const seg = Math.max(1, e.intervalo) * ({ seconds: 1, minutes: 60, hours: 3600, days: 86400 }[e.unidade])
    for (let i = 1; i <= count; i++) out.push(new Date(agora.getTime() + i * seg * 1000))
    return out
  }

  if (e.freq === "avancado") {
    if (e.advTipo === "rrule") return null       // raw rrule: no local forecast
    return proximasDeCron(e.advCron, tz, count, agora)
  }

  if (e.freq === "mensal") {
    const base = partesNoFuso(agora, tz)
    for (let k = 0; out.length < count && k < 120; k++) {
      let ano = base.y, mesIdx = base.mo - 1 + k
      ano += Math.floor(mesIdx / 12); mesIdx = ((mesIdx % 12) + 12) % 12
      const ult = ultimoDiaDoMes(ano, mesIdx + 1)
      let dia: number
      if (e.monthLast) dia = ult
      else { if (e.monthDay > ult) continue; dia = e.monthDay }   // month without day D → SKIP
      const q = utcDaParede(ano, mesIdx + 1, dia, h, m, tz)
      if (q.getTime() > agora.getTime()) out.push(q)
    }
    return out
  }

  // daily / weekly: scans day by day in the time zone's calendar.
  const t0 = partesNoFuso(agora, tz)
  const ancora = Date.UTC(t0.y, t0.mo - 1, t0.d)
  const nDias = e.freq === "diario" ? Math.max(1, e.everyDays) : 1
  const dias = e.freq === "semanal" ? Array.from(new Set(e.weekdays)) : null
  if (dias && !dias.length) return []
  // Ceiling adapted to the cadence: "every N days" with a large N needs to scan
  // further ahead to find `count` runs.
  const teto = Math.max(1200, (count + 1) * nDias)
  for (let k = 0; out.length < count && k < teto; k++) {
    const cd = new Date(ancora + k * 86400000)
    const y = cd.getUTCFullYear(), mo = cd.getUTCMonth() + 1, d = cd.getUTCDate(), wd = cd.getUTCDay()
    const ok = e.freq === "diario" ? (k % nDias === 0) : dias!.indexOf(wd) !== -1
    if (!ok) continue
    const q = utcDaParede(y, mo, d, h, m, tz)
    if (q.getTime() > agora.getTime()) out.push(q)
  }
  return out
}

/** Preview for a raw cron — only the shapes with a fixed minute and hour. */
function proximasDeCron(expr: string, tz: string, count: number, agora: Date): Date[] | null {
  const p = String(expr || "").trim().split(/\s+/)
  if (p.length !== 5) return null
  const [min, hora, dom, mes, dow] = p
  const m = /^\d+$/.test(min) ? +min : null
  const h = /^\d+$/.test(hora) ? +hora : null
  if (m === null || h === null || mes !== "*") return null
  const diasSemana = dow === "*" ? null : expandirDow(dow)
  if (dow !== "*" && !diasSemana) return null
  const diaMes = dom === "*" ? null : (/^\d+$/.test(dom) ? +dom : null)
  if (dom !== "*" && diaMes === null) return null
  if (diaMes !== null && diasSemana) return null   // a combination we don't generate

  const out: Date[] = []
  const t0 = partesNoFuso(agora, tz)
  const ancora = Date.UTC(t0.y, t0.mo - 1, t0.d)
  for (let k = 0; out.length < count && k < 1200; k++) {
    const cd = new Date(ancora + k * 86400000)
    const y = cd.getUTCFullYear(), mo = cd.getUTCMonth() + 1, d = cd.getUTCDate(), wd = cd.getUTCDay()
    const ok = diaMes !== null ? d === diaMes : (diasSemana ? diasSemana.indexOf(wd) !== -1 : true)
    if (!ok) continue
    const q = utcDaParede(y, mo, d, h, m, tz)
    if (q.getTime() > agora.getTime()) out.push(q)
  }
  return out
}

// ── Labels for the UI ─────────────────────────────────────────────────────────

export const NOME_DIA_CURTO = DIAS_CURTOS
export const NOME_DIA_LONGO = DIAS_LONGOS

// ── Fusos IANA ────────────────────────────────────────────────────────────────

/** "UTC−3", "UTC+5:30", "UTC" — the time zone's offset at `agora`. */
export function deslocamentoDoFuso(zona: string, agora: Date = new Date()): string | null {
  try {
    const parte = new Intl.DateTimeFormat("en-US", { timeZone: zona, timeZoneName: "shortOffset" })
      .formatToParts(agora).find(p => p.type === "timeZoneName")?.value
    if (!parte) return null
    const desloc = parte.replace(/^GMT/, "")
    return !desloc || desloc === "+0" ? "UTC" : `UTC${desloc.replace("-", "−")}`
  } catch {
    return null
  }
}

/**
 * The time zones the picker offers: every IANA zone the browser knows, plus UTC
 * and the current value — which may be an old name (`America/Buenos_Aires`)
 * saved earlier and that, outside the list, would vanish from the picker.
 * Alphabetical order, UTC first.
 */
export function opcoesDeFuso(atual?: string, agora: Date = new Date()): { value: string; label: string }[] {
  let zonas: string[] = []
  try {
    zonas = Intl.supportedValuesOf("timeZone")
  } catch { /* old browser: keeps only UTC and the current one */ }
  const todas = Array.from(new Set([...zonas, ...(atual ? [atual] : [])].filter(z => z !== "UTC"))).sort()
  return ["UTC", ...todas].map(zona => {
    const desloc = deslocamentoDoFuso(zona, agora)
    const nome = zona.replaceAll("_", " ")
    return { value: zona, label: desloc && desloc !== nome ? `${nome} (${desloc})` : nome }
  })
}
