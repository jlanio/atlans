import { describe, it, expect } from "vitest";
import { extrairViolacoes } from "@/lib/csp-report";

describe("extrairViolacoes", () => {
  it("lê o formato do report-uri (um objeto, kebab-case)", () => {
    const [v] = extrairViolacoes({
      "csp-report": {
        "document-uri": "https://atlans.example.org/login",
        "effective-directive": "script-src",
        "blocked-uri": "https://evil.example/x.js",
        "source-file": "https://atlans.example.org/_next/static/chunks/a.js",
        "line-number": 12,
        disposition: "report",
      },
    });
    expect(v).toEqual({
      documento: "https://atlans.example.org/login",
      diretiva: "script-src",
      bloqueado: "https://evil.example/x.js",
      origem: "https://atlans.example.org/_next/static/chunks/a.js:12",
      disposicao: "report",
    });
  });

  it("lê o formato do report-to (lista, camelCase) e ignora outros tipos", () => {
    const vs = extrairViolacoes([
      {
        type: "csp-violation",
        body: {
          documentURL: "https://atlans.example.org/",
          effectiveDirective: "img-src",
          blockedURL: "https://tile.example/1.png",
          disposition: "report",
        },
      },
      { type: "deprecation", body: { id: "x" } },
    ]);
    expect(vs).toHaveLength(1);
    expect(vs[0].diretiva).toBe("img-src");
    expect(vs[0].origem).toBeNull();
  });

  it("cai na violated-directive quando não há effective-directive", () => {
    const [v] = extrairViolacoes({ "csp-report": { "violated-directive": "frame-src 'none'" } });
    expect(v.diretiva).toBe("frame-src 'none'");
    expect(v.documento).toBe("");
  });

  it("ignora lixo sem quebrar", () => {
    expect(extrairViolacoes(null)).toEqual([]);
    expect(extrairViolacoes("texto")).toEqual([]);
    expect(extrairViolacoes([1, "a", { "csp-report": "x" }])).toEqual([]);
    // no directive, nothing to decide
    expect(extrairViolacoes({ "csp-report": { "blocked-uri": "x" } })).toEqual([]);
  });

  it("trunca campos longos e limita a quantidade por POST", () => {
    const item = { type: "csp-violation", body: { effectiveDirective: "x".repeat(2000) } };
    const vs = extrairViolacoes(Array.from({ length: 50 }, () => item));
    expect(vs).toHaveLength(20);
    expect(vs[0].diretiva).toHaveLength(512);
  });
});
