/**
 * CSP violation reports, in the two formats the browser sends:
 *   - `report-uri`: one `{ "csp-report": {...} }` object per POST (kebab-case keys);
 *   - `report-to`:  a list `[{ type: "csp-violation", body: {...} }]` (camelCase).
 * Only what decides the policy comes out of here — the rest of the report is log noise.
 */
export interface CspViolation {
  documento: string;
  diretiva: string;
  bloqueado: string;
  /** `file:line` when the browser provides it; null otherwise. */
  origem: string | null;
  disposicao: string;
}

// Public endpoint: a forged POST must not turn into a giant log.
const PER_POST_CEILING = 20;
const FIELD_CEILING = 512;

function texto(v: unknown): string | null {
  return typeof v === "string" && v.length > 0 ? v.slice(0, FIELD_CEILING) : null;
}

function fromReport(r: Record<string, unknown>): CspViolation | null {
  const diretiva = texto(
    r["effective-directive"] ?? r.effectiveDirective ?? r["violated-directive"] ?? r.violatedDirective,
  );
  if (!diretiva) return null;
  const arquivo = texto(r["source-file"] ?? r.sourceFile);
  const linha = r["line-number"] ?? r.lineNumber;
  return {
    documento: texto(r["document-uri"] ?? r.documentURL) ?? "",
    diretiva,
    bloqueado: texto(r["blocked-uri"] ?? r.blockedURL) ?? "",
    origem: arquivo ? (typeof linha === "number" ? `${arquivo}:${linha}` : arquivo) : null,
    // The policy is blocking: a report without the field (old report-uri
    // format, or forged) belongs to the mode in force.
    disposicao: texto(r.disposition) ?? "enforce",
  };
}

export function extrairViolacoes(corpo: unknown): CspViolation[] {
  const itens: unknown[] = Array.isArray(corpo) ? corpo : [corpo];
  const saida: CspViolation[] = [];
  for (const item of itens) {
    if (saida.length >= PER_POST_CEILING) break;
    if (!item || typeof item !== "object") continue;
    const o = item as Record<string, unknown>;
    const relato = o["csp-report"] ?? (o.type === "csp-violation" ? o.body : null);
    if (!relato || typeof relato !== "object") continue;
    const v = fromReport(relato as Record<string, unknown>);
    if (v) saida.push(v);
  }
  return saida;
}
