/**
 * Port de `app/core/utils/allowlist.py` — mantenha os dois em sincronia.
 *
 * Existe para que a tela de notificações mostre o efeito de uma allowlist
 * ENQUANTO ela é editada, antes de salvar. Sem isso o usuário só descobriria
 * quais workflows passou a bloquear depois de gravar — e a coluna já falha em
 * silêncio o suficiente.
 *
 * O backend continua sendo a autoridade: o que esta função calcula é um preview,
 * reconciliado pela resposta do PUT. `web/__tests__/lib/hostname-allowlist.test.ts`
 * espelha os casos do Python; se as regras lá mudarem, ele quebra aqui.
 */

/**
 * Padrões aceitos:
 *   - "exemplo.com"   → match exato
 *   - "*.exemplo.com" → qualquer subdomínio (a.exemplo.com, foo.bar.exemplo.com)
 *                       mas NÃO o domínio nu (exemplo.com)
 *
 * Comparação case-insensitive.
 */
export function hostnameMatchesAllowlist(hostname: string, allowlist: string[]): boolean {
  const host = (hostname ?? "").toLowerCase().trim()
  if (!host) return false

  for (const raw of allowlist ?? []) {
    const pattern = (raw ?? "").toLowerCase().trim()
    if (!pattern) continue

    if (pattern.startsWith("*.")) {
      const suffix = pattern.slice(1) // ".exemplo.com"
      // `host !== suffix.slice(1)` é o que exclui o domínio nu: "*.exemplo.com"
      // cobre os subdomínios, não "exemplo.com".
      if (host.endsWith(suffix) && host !== suffix.slice(1)) return true
    } else if (host === pattern) {
      return true
    }
  }
  return false
}

/**
 * Um host é permitido quando a allowlist está vazia.
 *
 * Espelha o `if allowlist:` do consumer: sem lista não há política adicional, e
 * tudo que passa na verificação de SSRF é aceito. É a semântica invertida da
 * coluna — aplicar `hostnameMatchesAllowlist` direto marcaria tudo como
 * bloqueado no estado em que hoje tudo passa.
 */
export function isHostAllowed(hostname: string, allowlist: string[]): boolean {
  if (!allowlist || allowlist.length === 0) return true
  return hostnameMatchesAllowlist(hostname, allowlist)
}

/**
 * Valida um padrão antes de virar chip, com as mesmas regras de
 * `_normalize_allowlist` no backend. Devolve a mensagem de erro, ou null.
 *
 * Duplicar a validação aqui é o que permite errar barato: colar a URL inteira é
 * o engano óbvio, e descobri-lo só no 400 do servidor custa um round-trip.
 */
export function validateAllowlistPattern(raw: string): string | null {
  const pattern = (raw ?? "").trim().toLowerCase()
  if (!pattern) return "Informe um host."

  if (pattern.includes("://") || pattern.includes("/") || pattern.includes("@") || pattern.includes(":")) {
    return "Informe apenas o host, sem protocolo, porta ou caminho (ex.: exemplo.com)."
  }
  if (pattern.includes("*") && !pattern.startsWith("*.")) {
    return "O curinga só vale no formato *.exemplo.com (subdomínios)."
  }
  if (pattern.startsWith("*.") && !pattern.slice(2).includes(".")) {
    return "Informe o domínio completo após o curinga (ex.: *.exemplo.com)."
  }
  if (!pattern.startsWith("*.") && !pattern.includes(".")) {
    return "Não parece um hostname válido (ex.: exemplo.com)."
  }
  return null
}
