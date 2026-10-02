"use client"

// A casca padronizada de cada seção da página de Configurações (contrato §2).

// ── Casca de seção (contrato §2) ─────────────────────────────────────────────

/**
 * Casca padronizada da seção: `<section aria-labelledby>` com a moldura do
 * contrato (borda + `bg-card` + `shadow-xs`), cabeçalho `px-4 pt-4 pb-1` com o
 * `<h2>` e a linha de apoio, e o corpo em `px-4 pb-4`. Substitui o `SettingCard`
 * (Card + CardHeader + Separator do shadcn), que trazia sombra e separador que
 * não são do padrão. `aria-busy` marca a seção enquanto a fonte dela carrega.
 */
export function SecaoDeConfiguracao({
  id, titulo, apoio, carregando, children,
}: {
  id: string
  titulo: string
  apoio: string
  carregando?: boolean
  children: React.ReactNode
}) {
  return (
    <section
      aria-labelledby={`${id}-titulo`}
      aria-busy={carregando || undefined}
      className="flex min-w-0 flex-col rounded-lg border bg-card shadow-xs"
    >
      <div className="px-4 pt-4 pb-1">
        <h2 id={`${id}-titulo`} className="text-sm font-semibold">{titulo}</h2>
        <p className="text-xs text-muted-foreground">{apoio}</p>
      </div>
      <div className="px-4 pb-4">{children}</div>
    </section>
  )
}
