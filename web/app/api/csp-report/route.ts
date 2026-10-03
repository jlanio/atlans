import { NextResponse } from "next/server";
import { extrairViolacoes } from "@/lib/csp-report";

// Collector for Content-Security-Policy reports (next.config.ts). The browser
// makes the POST without session or CSRF, which is why the route stays outside
// the middleware matcher. It only logs — with a size ceiling, because anyone can
// call it.
//
// 256 KB and not 16: via `report-to`, Chrome groups up to a minute of reports
// into a single POST, and each report repeats the whole policy (~900 bytes).
// With 16 KB, a page with more than ~18 blocks in a minute lost the whole batch
// to a 413 — precisely the case where the log matters most. The volume in the
// log stays limited by `extrairViolacoes` (20 lines per POST).
const TETO_BYTES = 256 * 1024;

/** The body as text, or `null` if it exceeds the ceiling.
 *
 *  Read as a stream, counting bytes: without `Content-Length` (chunked body),
 *  the earlier `req.text()` kept the WHOLE body in memory before any check —
 *  100 MB in an anonymous POST added ~330 MB to the process. */
async function lerComTeto(req: Request): Promise<string | null> {
  if (!req.body) return "";
  const leitor = req.body.getReader();
  const pedacos: Uint8Array[] = [];
  let total = 0;
  for (;;) {
    const { done, value } = await leitor.read();
    if (done) break;
    total += value.byteLength;
    if (total > TETO_BYTES) {
      await leitor.cancel();
      return null;
    }
    pedacos.push(value);
  }
  return Buffer.concat(pedacos).toString("utf8");
}

export async function POST(req: Request) {
  if (Number(req.headers.get("content-length") ?? 0) > TETO_BYTES) {
    return new NextResponse(null, { status: 413 });
  }
  const bruto = await lerComTeto(req);
  if (bruto === null) return new NextResponse(null, { status: 413 });

  let corpo: unknown;
  try {
    corpo = JSON.parse(bruto);
  } catch {
    return new NextResponse(null, { status: 400 });
  }
  for (const violacao of extrairViolacoes(corpo)) {
    console.warn("[csp-report]", JSON.stringify(violacao));
  }
  return new NextResponse(null, { status: 204 });
}
