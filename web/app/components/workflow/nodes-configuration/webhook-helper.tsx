"use client"
import { useState } from "react"
import { TbCopy, TbCheck, TbBrandPython, TbBrandJavascript, TbTerminal2 } from "react-icons/tb"
import { getExternalApiUrl } from "@/utils/env"
import { generateSampleFromSchema } from "./webhook-sample"

type Tab = "curl" | "python" | "js"

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
      className="p-1 rounded hover:bg-white/10 transition-colors text-muted-foreground hover:text-foreground"
    >
      {copied ? <TbCheck className="h-3.5 w-3.5 text-green-500" /> : <TbCopy className="h-3.5 w-3.5" />}
    </button>
  )
}

function CodeBlock({ code }: { code: string }) {
  return (
    <div className="relative group">
      <pre className="bg-muted rounded-md p-3 text-[11px] font-mono leading-relaxed overflow-x-auto whitespace-pre text-foreground/80">
        {code}
      </pre>
      {/* `coarse:`: no telefone não há hover, e copiar o bloco era impossível. */}
      <div className="absolute top-1.5 right-1.5 opacity-0 coarse:opacity-70 group-hover:opacity-100 transition-opacity">
        <CopyButton text={code} />
      </div>
    </div>
  )
}

/** Converte objeto JS para representação de dict Python (aspas simples). */
function toPythonDict(obj: unknown, indent = 0): string {
  if (obj === null || obj === undefined) return "None"
  if (typeof obj === "boolean") return obj ? "True" : "False"
  if (typeof obj === "number") return String(obj)
  if (typeof obj === "string") return `"${obj}"`
  if (Array.isArray(obj)) {
    if (obj.length === 0) return "[]"
    const items = obj.map(v => toPythonDict(v, indent + 4))
    const pad = " ".repeat(indent + 4)
    return `[\n${items.map(i => `${pad}${i}`).join(",\n")}\n${" ".repeat(indent)}]`
  }
  if (typeof obj === "object") {
    const entries = Object.entries(obj as Record<string, unknown>)
    if (entries.length === 0) return "{}"
    const pad = " ".repeat(indent + 4)
    const lines = entries.map(([k, v]) => `${pad}"${k}": ${toPythonDict(v, indent + 4)}`)
    return `{\n${lines.join(",\n")}\n${" ".repeat(indent)}}`
  }
  return String(obj)
}

interface Props {
  workflowId: string | undefined
  outputKey: string
  hasSecret?: boolean
  payloadSchema?: unknown
}

export default function WebhookHelper({ workflowId, outputKey, hasSecret, payloadSchema }: Props) {
  const [tab, setTab] = useState<Tab>("curl")

  if (!workflowId) return null

  const webhookUrl = `${getExternalApiUrl()}/webhook/execute/${workflowId}`
  const sample = generateSampleFromSchema(outputKey, payloadSchema)
  const sampleJson = JSON.stringify(sample)
  const sampleJsonPretty = JSON.stringify(sample, null, 2)
  const samplePython = toPythonDict(sample)

  const secretHeader = hasSecret ? " \\\n  -H \"Authorization: Bearer <seu-token>\"" : ""
  const secretHeaderPy = hasSecret ? "\n    headers={\"Authorization\": \"Bearer <seu-token>\"}," : ""
  const secretHeaderJs = hasSecret ? "\n    \"Authorization\": \"Bearer <seu-token>\"," : ""

  const curlCode = `curl -X POST "${webhookUrl}" \\
  -H "Content-Type: application/json"${secretHeader} \\
  -d '${sampleJson}'`

  const pythonCode = `import httpx

response = httpx.post(
    "${webhookUrl}",${secretHeaderPy}
    json=${samplePython},
)
task_id = response.json()["task_id"]
print(f"Task iniciada: {task_id}")`

  const jsCode = `const response = await fetch("${webhookUrl}", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",${secretHeaderJs}
  },
  body: JSON.stringify(${sampleJsonPretty.split("\n").map((l, i) => i === 0 ? l : "  " + l).join("\n")}),
});
const { task_id } = await response.json();
console.log("Task iniciada:", task_id);`

  const TABS: { id: Tab; label: string; icon: React.ElementType }[] = [
    { id: "curl",   label: "cURL",       icon: TbTerminal2 },
    { id: "python", label: "Python",     icon: TbBrandPython },
    { id: "js",     label: "JavaScript", icon: TbBrandJavascript },
  ]

  const code = tab === "curl" ? curlCode : tab === "python" ? pythonCode : jsCode

  return (
    <div className="flex flex-col gap-3 px-1 mt-1">
      {/* Título */}
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
        Como acionar via API
      </p>

      {/* URL do endpoint */}
      <div>
        <p className="text-[11px] text-muted-foreground mb-1">Endpoint</p>
        <div className="flex items-center gap-1 bg-muted rounded-md px-2 py-1.5">
          <span className="text-[10px] font-mono font-medium text-primary bg-primary/10 rounded px-1 py-0.5 shrink-0">
            POST
          </span>
          <span className="text-[11px] font-mono text-foreground/80 truncate flex-1" title={webhookUrl}>
            {webhookUrl}
          </span>
          <CopyButton text={webhookUrl} />
        </div>
      </div>

      {/* Autenticação */}
      {hasSecret && (
        <div className="flex items-start gap-2 bg-amber-500/8 border border-amber-500/20 rounded-md px-2.5 py-2">
          <span className="text-amber-500 text-[10px] font-bold mt-0.5 shrink-0">🔒</span>
          <p className="text-[11px] text-foreground/70 leading-relaxed">
            Este webhook exige autenticação. Inclua o header{" "}
            <span className="font-mono bg-muted px-1 rounded text-foreground/90">Authorization: Bearer &lt;seu-token&gt;</span>{" "}
            em todas as requisições.
          </p>
        </div>
      )}

      {/* Resposta */}
      <div>
        <p className="text-[11px] text-muted-foreground mb-1">Resposta (202 Accepted)</p>
        <CodeBlock code={`{ "task_id": "uuid-da-task" }`} />
      </div>

      {/* Payload de exemplo */}
      <div>
        <p className="text-[11px] text-muted-foreground mb-1">Estrutura do body</p>
        <CodeBlock code={sampleJsonPretty} />
      </div>

      {/* Abas de código */}
      <div>
        <div className="flex gap-1 mb-2">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium transition-colors ${
                tab === id
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              }`}
            >
              <Icon className="h-3 w-3" />
              {label}
            </button>
          ))}
        </div>
        <CodeBlock code={code} />
      </div>

      {/* Nota sobre task_id */}
      <p className="text-[11px] text-muted-foreground leading-relaxed">
        O <span className="font-mono bg-muted px-1 rounded">task_id</span> retornado pode ser usado para
        acompanhar a execução em tempo real via WebSocket{" "}
        <span className="font-mono bg-muted px-1 rounded">ws://…/ws/workflow/{"{"}{`task_id`}{"}"}</span>.
      </p>
    </div>
  )
}
