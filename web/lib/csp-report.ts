/**
 * Relatos de violação da CSP, nos dois formatos que o navegador manda:
 *   - `report-uri`: um objeto `{ "csp-report": {...} }` por POST (chaves em kebab-case);
 *   - `report-to`:  uma lista `[{ type: "csp-violation", body: {...} }]` (camelCase).
 * Só o que decide a política sai daqui — o resto do relato é ruído no log.
 */
export interface ViolacaoCsp {
  documento: string;
  diretiva: string;
  bloqueado: string;
  /** `arquivo:linha` quando o navegador informa; nulo caso contrário. */
  origem: string | null;
  disposicao: string;
}

// Endpoint público: um POST forjado não pode virar um log gigante.
const TETO_POR_POST = 20;
const TETO_DO_CAMPO = 512;

function texto(v: unknown): string | null {
  return typeof v === "string" && v.length > 0 ? v.slice(0, TETO_DO_CAMPO) : null;
}

function deRelato(r: Record<string, unknown>): ViolacaoCsp | null {
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
    // A política é bloqueante: relato sem o campo (formato antigo do
    // report-uri, ou forjado) é do modo em vigor.
    disposicao: texto(r.disposition) ?? "enforce",
  };
}

export function extrairViolacoes(corpo: unknown): ViolacaoCsp[] {
  const itens: unknown[] = Array.isArray(corpo) ? corpo : [corpo];
  const saida: ViolacaoCsp[] = [];
  for (const item of itens) {
    if (saida.length >= TETO_POR_POST) break;
    if (!item || typeof item !== "object") continue;
    const o = item as Record<string, unknown>;
    const relato = o["csp-report"] ?? (o.type === "csp-violation" ? o.body : null);
    if (!relato || typeof relato !== "object") continue;
    const v = deRelato(relato as Record<string, unknown>);
    if (v) saida.push(v);
  }
  return saida;
}
