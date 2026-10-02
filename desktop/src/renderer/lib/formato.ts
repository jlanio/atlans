// desktop/src/renderer/lib/formato.ts
//
// Formatação de números para as telas — um lugar só.
//
// A duração vivia copiada no Painel (App.tsx) e na lista de Execuções, e as
// cópias divergiram: o Painel corrigiu o arredondamento e a lista continuou
// mostrando "60.0s" e "59m 60s".

/** Duração em segundos, como se lê num relógio: `12.3s`, `4m 5s`, `2h 10m`. */
export function duracao(s: number | null | undefined): string {
  if (s == null) return '—'
  // Arredonda ANTES de decidir a faixa. Fazendo depois, 59.97s caía em `< 60`
  // e o toFixed(1) imprimia "60.0s"; e 3599.7s virava "59m 60s" — dois valores
  // que não existem no relógio, num painel que se olha de relance.
  const decimos = Math.round(s * 10) / 10
  if (decimos < 60) return `${decimos.toFixed(1)}s`
  const totalSeg = Math.round(s)
  const m = Math.floor(totalSeg / 60)
  return m < 60
    ? `${m}m ${totalSeg % 60}s`
    : `${Math.floor(m / 60)}h ${m % 60}m`
}
