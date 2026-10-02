"use client"

import { useState } from "react"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/app/components/ui/sheet"
import {
  TbBraces,
  TbVariable,
  TbClock,
  TbFilter,
  TbArrowsShuffle,
  TbCode,
  TbCheck,
  TbCopy,
  TbChevronDown,
  TbInfoCircle,
  TbBulb,
} from "react-icons/tb"

// ── Botao copiar ────────────────────────────────────────────────────────────

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  function copy() {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    })
  }

  return (
    <button
      onClick={copy}
      title="Copiar"
      className="p-0.5 rounded hover:bg-white/10 transition-colors text-muted-foreground hover:text-foreground"
    >
      {copied
        ? <TbCheck className="h-3 w-3 text-green-500" />
        : <TbCopy className="h-3 w-3" />}
    </button>
  )
}

function CodeExample({ code, label }: { code: string; label?: string }) {
  return (
    <div className="relative group">
      {label && (
        <p className="text-[10px] text-muted-foreground/70 mb-0.5 pl-0.5">{label}</p>
      )}
      <pre className="bg-zinc-950/80 dark:bg-zinc-950/60 rounded-md px-3 py-2 text-[11px] font-mono leading-relaxed overflow-x-auto whitespace-pre text-emerald-400/90">
        {code}
      </pre>
      {/* `coarse:`: no telefone não há hover, e copiar o bloco era impossível. */}
      <div className="absolute top-1 right-1 opacity-0 coarse:opacity-70 group-hover:opacity-100 transition-opacity">
        <CopyButton text={code} />
      </div>
    </div>
  )
}

// ── Callout informativo ─────────────────────────────────────────────────────

function Callout({ children, variant = "info" }: { children: React.ReactNode; variant?: "info" | "tip" }) {
  const styles = {
    info: "bg-blue-500/8 border-blue-500/20 text-blue-200/70",
    tip:  "bg-amber-500/8 border-amber-500/20 text-amber-200/70",
  }
  const Icon = variant === "tip" ? TbBulb : TbInfoCircle
  return (
    <div className={`rounded-lg border px-3 py-2.5 flex gap-2 items-start ${styles[variant]}`}>
      <Icon className="h-3.5 w-3.5 shrink-0 mt-0.5" />
      <p className="text-[11px] leading-relaxed">{children}</p>
    </div>
  )
}

// ── Badge de variavel ───────────────────────────────────────────────────────

function VarBadge({ name, desc, color = "zinc" }: { name: string; desc: string; color?: "zinc" | "green" | "blue" | "amber" | "purple" }) {
  const colors: Record<string, string> = {
    zinc:   "bg-zinc-500/10 border-zinc-500/20 text-zinc-400",
    green:  "bg-emerald-500/10 border-emerald-500/20 text-emerald-400",
    blue:   "bg-blue-500/10 border-blue-500/20 text-blue-400",
    amber:  "bg-amber-500/10 border-amber-500/20 text-amber-400",
    purple: "bg-purple-500/10 border-purple-500/20 text-purple-400",
  }
  return (
    <div className="flex items-center gap-2 py-1">
      <code className={`px-2 py-0.5 rounded-md border font-mono text-[11px] shrink-0 ${colors[color]}`}>
        {name}
      </code>
      <span className="text-[11px] text-muted-foreground">{desc}</span>
    </div>
  )
}

// ── Secao colapsavel ────────────────────────────────────────────────────────

function Section({
  icon,
  title,
  badge,
  defaultOpen = false,
  children,
}: {
  icon: React.ReactNode
  title: string
  badge?: string
  defaultOpen?: boolean
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className="border border-border/60 rounded-xl overflow-hidden bg-card/50">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2.5 px-3.5 py-3 text-left hover:bg-muted/30 transition-colors"
      >
        <span className="text-muted-foreground">{icon}</span>
        <span className="text-[13px] font-medium flex-1">{title}</span>
        {badge && (
          <span className="text-[9px] font-medium px-1.5 py-0.5 rounded-full bg-primary/10 text-primary">
            {badge}
          </span>
        )}
        <TbChevronDown
          className={`h-4 w-4 text-muted-foreground transition-transform duration-200 ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <div className="px-3.5 pb-4 flex flex-col gap-3 border-t border-border/40 pt-3">
          {children}
        </div>
      )}
    </div>
  )
}

// ── Tabela de filtros ───────────────────────────────────────────────────────

function FilterRow({ filter, desc }: { filter: string; desc: string }) {
  return (
    <div className="flex items-center gap-2 py-0.5">
      <code className="px-2 py-0.5 rounded-md border border-purple-500/20 bg-purple-500/10 text-purple-400 font-mono text-[10px] shrink-0 min-w-[90px]">
        {filter}
      </code>
      <span className="text-[10px] text-muted-foreground">{desc}</span>
    </div>
  )
}

// ── Componente principal ────────────────────────────────────────────────────

interface JinjaExpressionGuideProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export default function JinjaExpressionGuide({ open, onOpenChange }: JinjaExpressionGuideProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      {/* 440px fixos passavam da tela inteira de um telefone, e o Sheet do
          Radix não encolhe sozinho — o conteúdo saía pela borda direita. */}
      <SheetContent side="right" className="w-full sm:w-[440px] sm:max-w-[440px] overflow-y-auto bg-background/95 backdrop-blur-sm !z-[70]">
        <SheetHeader className="pb-1">
          <SheetTitle className="flex items-center gap-2.5 text-base">
            <div className="flex items-center justify-center h-7 w-7 rounded-lg bg-primary/10">
              <TbBraces className="h-4 w-4 text-primary" />
            </div>
            Guia de Expressoes
          </SheetTitle>
          <SheetDescription className="text-xs leading-relaxed">
            Use <code className="px-1.5 py-0.5 bg-emerald-500/10 border border-emerald-500/20 rounded-md font-mono text-emerald-500 text-[11px]">$Alias</code> e
            expressoes Jinja2 para parametros dinamicos.
          </SheetDescription>
        </SheetHeader>

        <div className="flex flex-col gap-2.5 px-4 pb-6">

          {/* ── Aliases ────────────────────────────────────────────────── */}
          <Section
            icon={<TbArrowsShuffle className="h-4 w-4" />}
            title="Referencias entre nos"
            badge="$Alias"
            defaultOpen
          >
            <p className="text-xs text-muted-foreground leading-relaxed">
              Use <code className="px-1.5 py-0.5 bg-emerald-500/10 border border-emerald-500/20 rounded-md font-mono text-emerald-400 text-[11px]">$NomeDoNo</code> para
              acessar a saida de outro no. Funciona sozinho ou dentro de {"{{ }}"}.
            </p>

            <div className="flex flex-col gap-1.5">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">Uso direto</p>
              <CodeExample code="$Buffer" />
              <CodeExample code="$Buffer.output" />
              <CodeExample code="$DatabaseQuery.output.area" />
            </div>

            <div className="flex flex-col gap-1.5">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">Dentro de Jinja2</p>
              <CodeExample code={'{{ $MeuNo.output }}'} />
              <CodeExample code={'{{ $MeuNo.output | upper }}'} />
              <CodeExample code={"SELECT * FROM t WHERE id = '{{ $Query.id }}'"} />
            </div>

            <Callout variant="tip">
              <strong>Dica:</strong> O alias padrao e o nome do no (ex: Buffer, DatabaseQuery).
              Renomeie no campo de titulo. Nomes reservados
              (<code className="text-[10px] font-mono">inputs</code>, <code className="text-[10px] font-mono">env</code>, <code className="text-[10px] font-mono">now</code>, <code className="text-[10px] font-mono">uuid</code>, <code className="text-[10px] font-mono">nodes</code>) nao podem ser usados.
            </Callout>
          </Section>

          {/* ── Sintaxe Jinja ──────────────────────────────────────────── */}
          <Section
            icon={<TbBraces className="h-4 w-4" />}
            title="Sintaxe Jinja2"
            badge="{{ }}"
          >
            <p className="text-xs text-muted-foreground leading-relaxed">
              Todo campo de texto aceita expressoes entre <code className="px-1 py-0.5 bg-muted rounded-md font-mono text-[11px]">{"{{ }}"}</code>.
            </p>

            <div className="flex flex-col gap-1.5">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">Expressoes</p>
              <CodeExample code={'{{ inputs.nome }}'} label="Acesso a entrada" />
              <CodeExample code={'{{ inputs.area * 1.5 }}'} label="Calculo" />
              <CodeExample code={'{{ $Consulta.output | length }}'} label="Alias + filtro" />
            </div>

            <div className="flex flex-col gap-1.5">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">Condicionais</p>
              <CodeExample code={'{{ inputs.valor if inputs.valor > 0 else "N/A" }}'} />
              <CodeExample code={'{% if inputs.tipo == "urbano" %}sim{% else %}nao{% endif %}'} />
            </div>

            <div className="flex flex-col gap-1.5">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">Operadores</p>
              <div className="grid grid-cols-2 gap-1.5 text-[11px]">
                <code className="px-2 py-1.5 bg-muted/60 rounded-md font-mono text-center">==  !=  &gt;  &lt;  &gt;=  &lt;=</code>
                <span className="text-muted-foreground py-1.5 text-[10px]">Comparacao</span>
                <code className="px-2 py-1.5 bg-muted/60 rounded-md font-mono text-center">and  or  not</code>
                <span className="text-muted-foreground py-1.5 text-[10px]">Logicos</span>
                <code className="px-2 py-1.5 bg-muted/60 rounded-md font-mono text-center">+  -  *  /  //  %</code>
                <span className="text-muted-foreground py-1.5 text-[10px]">Aritmeticos</span>
                <code className="px-2 py-1.5 bg-muted/60 rounded-md font-mono text-center">is none  is not none</code>
                <span className="text-muted-foreground py-1.5 text-[10px]">Teste de nulo</span>
              </div>
            </div>
          </Section>

          {/* ── Variaveis disponiveis ──────────────────────────────────── */}
          <Section
            icon={<TbVariable className="h-4 w-4" />}
            title="Variaveis disponiveis"
          >
            <div className="flex flex-col gap-0.5">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60 mb-1">Em qualquer no</p>
              <VarBadge name="inputs"  desc="Dados recebidos pelo no" color="blue" />
              <VarBadge name="$Alias"  desc="Saida de qualquer no por alias" color="green" />
              <VarBadge name="env"     desc="Variaveis de ambiente seguras" color="amber" />
              <VarBadge name="nodes"   desc="Saidas por ID (avancado)" color="zinc" />
            </div>

            <div className="flex flex-col gap-0.5">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60 mb-1">JinjaBranch</p>
              <VarBadge name="value"  desc="Primeiro valor dos inputs (atalho)" color="purple" />
            </div>

            <div className="flex flex-col gap-1">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60 mb-1">SetFields (por linha)</p>
              <VarBadge name="row"  desc="Linha atual do GeoDataFrame (dict)" color="purple" />
              <CodeExample code={'{{ row.area / 1000000 }}'} label="Area em km2" />
              <CodeExample code={'{{ row.nome | upper }}_{{ row.id }}'} label="Concatenar campos" />
            </div>
          </Section>

          {/* ── Funcoes globais ─────────────────────────────────────────── */}
          <Section
            icon={<TbClock className="h-4 w-4" />}
            title="Funcoes globais"
          >
            <div className="flex flex-col gap-3">
              <div>
                <VarBadge name="now()" desc="Data/hora UTC" color="amber" />
                <div className="flex flex-col gap-1 mt-1 ml-1">
                  <CodeExample code={'{{ now() }}'} label="Padrao ISO" />
                  <CodeExample code={'{{ now("%d/%m/%Y") }}'} label="Formato BR" />
                  <CodeExample code={'{{ now("%Y%m%d_%H%M") }}'} label="Para nome de arquivo" />
                </div>
              </div>

              <div>
                <VarBadge name="uuid()" desc="UUID4 aleatorio" color="amber" />
                <div className="ml-1 mt-1">
                  <CodeExample code={'{{ uuid() }}'} />
                </div>
              </div>

              <div>
                <VarBadge name="env" desc="Variaveis de ambiente" color="amber" />
                <div className="ml-1 mt-1">
                  <CodeExample code={'{{ env.TZ }}'} />
                </div>
                <Callout variant="info">
                  Apenas variaveis seguras sao expostas (TZ, NODE_ENV, LANG).
                  Admins podem expor mais via <code className="text-[10px] font-mono">EXPOSED_ENV_VARS</code>.
                </Callout>
              </div>
            </div>
          </Section>

          {/* ── Filtros ────────────────────────────────────────────────── */}
          <Section
            icon={<TbFilter className="h-4 w-4" />}
            title="Filtros comuns"
            badge="| filtro"
          >
            <p className="text-xs text-muted-foreground leading-relaxed">
              Transformam valores com <code className="px-1.5 py-0.5 bg-purple-500/10 border border-purple-500/20 rounded-md font-mono text-purple-400 text-[11px]">valor | filtro</code>.
            </p>

            <div className="flex flex-col gap-0.5">
              <FilterRow filter="upper"          desc="Texto em maiusculas" />
              <FilterRow filter="lower"          desc="Texto em minusculas" />
              <FilterRow filter="title"          desc="Primeira letra maiuscula" />
              <FilterRow filter="trim"           desc="Remove espacos" />
              <FilterRow filter="length"         desc="Tamanho da lista/string" />
              <FilterRow filter={'default("x")'} desc="Valor padrao se vazio" />
              <FilterRow filter="round(2)"       desc="Arredonda decimal" />
              <FilterRow filter="int"            desc="Converte para inteiro" />
              <FilterRow filter="float"          desc="Converte para decimal" />
              <FilterRow filter={'join(",")'}    desc="Une lista em string" />
              <FilterRow filter={'replace(a,b)'} desc="Substitui texto" />
              <FilterRow filter="first / last"   desc="Primeiro / ultimo item" />
            </div>

            <div className="flex flex-col gap-1 mt-1">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">Exemplos</p>
              <CodeExample code={'{{ inputs.nome | upper }}'} />
              <CodeExample code={'{{ $Consulta.output | round(2) }}'} />
              <CodeExample code={'{{ inputs.tags | join(", ") }}'} />
              <CodeExample code={'{{ inputs.valor | default(0) }}'} />
            </div>
          </Section>

          {/* ── Exemplos praticos ──────────────────────────────────────── */}
          <Section
            icon={<TbCode className="h-4 w-4" />}
            title="Exemplos praticos"
          >
            <div className="flex flex-col gap-3">
              <CodeExample
                label="Nome de arquivo dinamico"
                code={'resultado_{{ now("%Y%m%d_%H%M") }}_{{ uuid() }}.geojson'}
              />

              <CodeExample
                label="Query SQL com alias"
                code={"SELECT * FROM tabela\nWHERE geom && ST_MakeEnvelope(\n  {{ $BBox.minx }}, {{ $BBox.miny }},\n  {{ $BBox.maxx }}, {{ $BBox.maxy }}, 4326\n)"}
              />

              <CodeExample
                label="Alias direto (substitui campo inteiro)"
                code={'$Consulta.output'}
              />

              <CodeExample
                label="Alias com filtro + texto"
                code={'{{ $Consulta.output | length }} registros encontrados'}
              />

              <CodeExample
                label="Condicional no JinjaBranch"
                code={'{{ inputs.count > 10 and inputs.status == "ativo" }}'}
              />

              <CodeExample
                label="Valor com fallback"
                code={'{{ inputs.nome | default("sem_nome") }}'}
              />
            </div>
          </Section>

        </div>
      </SheetContent>
    </Sheet>
  )
}
