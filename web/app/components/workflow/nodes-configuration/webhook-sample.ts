/**
 * Gera um objeto de exemplo a partir do payload_schema configurado no WebhookTrigger.
 * Reutilizado pelo WebhookHelper (exemplos curl/Python/JS) e pela aba de teste.
 */

const DEFAULTS: Record<string, unknown> = {
  string:  "exemplo",
  number:  0,
  integer: 0,
  boolean: false,
  object:  {},
  array:   [],
}

export function generateSampleFromSchema(
  outputKey: string,
  payloadSchema: unknown,
): Record<string, unknown> {
  let schema = payloadSchema
  if (typeof schema === "string") {
    try { schema = JSON.parse(schema) } catch { schema = null }
  }

  const props =
    schema && typeof schema === "object"
      ? ((schema as Record<string, unknown>).properties as Record<string, { type?: string }> | undefined)
      : undefined

  const sample: Record<string, unknown> = {}
  if (props) {
    for (const [name, def] of Object.entries(props)) {
      sample[name] = DEFAULTS[def.type ?? "string"] ?? ""
    }
  }

  // Envolve em outputKey só se ele foi configurado; caso contrário, os campos
  // viram o body direto (mesma convencao que o webhook HTTP usa).
  return outputKey ? { [outputKey]: sample } : sample
}
