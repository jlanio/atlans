import { NextResponse } from "next/server";
import { extrairViolacoes } from "@/lib/csp-report";

// Coletor dos relatos da Content-Security-Policy (next.config.ts). O navegador
// faz o POST sem sessão nem CSRF, por isso a rota fica fora do matcher do
// middleware. Só loga — com teto de tamanho, porque qualquer um pode chamar.
//
// 256 KB e não 16: pelo `report-to`, o Chrome junta os relatos de até um
// minuto num POST só, e cada relato repete a política inteira (~900 bytes).
// Com 16 KB, uma página com mais de ~18 bloqueios num minuto perdia o lote
// inteiro num 413 — justo o caso em que o log mais importa. O volume no log
// segue limitado por `extrairViolacoes` (20 linhas por POST).
const TETO_BYTES = 256 * 1024;

/** O corpo como texto, ou `null` se passar do teto.
 *
 *  Lido em fluxo, contando bytes: sem `Content-Length` (corpo chunked), o
 *  `req.text()` de antes guardava o corpo INTEIRO na memória antes de qualquer
 *  checagem — 100 MB num POST anônimo somavam ~330 MB ao processo. */
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
