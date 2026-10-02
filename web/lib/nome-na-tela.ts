// web/lib/nome-na-tela.ts
//
// O nome que a tela mostra: o wordmark da barra lateral, o cabeçalho da tela
// de entrada e o título da aba.
//
// O código mostra «Atlans», o nome do projeto. A forma com o domínio é a
// instalação do titular, e é marca dele (TRADEMARKS.md):
// quem distribui uma versão modificada ou a oferece como serviço troca o
// nome. Por isso ele é da INSTALAÇÃO, não do código: vem de NOME_NA_TELA no
// ambiente do servidor web, lida pelo layout raiz a cada pedido e passada ao
// cliente por contexto (`app/components/share/nome-na-tela.tsx`), como o link
// do código-fonte e os fundos de mapa. NEXT_PUBLIC_* não serviria: gravaria o
// valor no build, e a imagem do web é a mesma para toda instalação.

export const NOME_PADRAO = "Atlans"

/** NOME_NA_TELA limpo, ou «Atlans» quando vazia, longa demais ou com caractere estranho. */
export function lerNomeNaTelaDoAmbiente(env: Record<string, string | undefined>): string {
  const nome = (env.NOME_NA_TELA ?? "").replace(/\s+/g, " ").trim()
  if (!nome || nome.length > 40 || /[\p{C}<>]/u.test(nome)) return NOME_PADRAO
  return nome
}
