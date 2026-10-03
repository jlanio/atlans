/**
 * Builds a sample object from the payload_schema configured on the WebhookTrigger.
 * Reused by WebhookHelper (curl/Python/JS examples) and by the test tab.
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

  // Wraps in outputKey only if it was configured; otherwise the fields
  // become the body directly (same convention the HTTP webhook uses).
  return outputKey ? { [outputKey]: sample } : sample
}
