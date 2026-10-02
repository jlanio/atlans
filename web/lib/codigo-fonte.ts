// web/lib/codigo-fonte.ts
//
// O link para o código-fonte da versão que roda nesta instalação.
//
// A AGPL (seção 13 da LICENSE) pede que quem usa a instalação pela rede possa
// obter o código-fonte dela — o oficial, ou o fork de quem a modificou. O
// endereço é da INSTALAÇÃO, não do código: vem de CODIGO_FONTE_URL no
// ambiente do servidor web, lida pelo layout raiz a cada pedido e passada ao
// cliente por contexto (`app/components/share/codigo-fonte.tsx`), como os
// fundos de mapa. NEXT_PUBLIC_* não serviria: gravaria o valor no build, e a
// imagem do web é a mesma para toda instalação.
//
// Sem a variável, nenhum link aparece: o código não traz endereço nenhum.

/** A URL de CODIGO_FONTE_URL, ou null quando vazia ou sem esquema http(s). */
export function lerCodigoFonteDoAmbiente(env: Record<string, string | undefined>): string | null {
  const url = (env.CODIGO_FONTE_URL ?? "").trim()
  return /^https?:\/\/\S+$/i.test(url) ? url : null
}
