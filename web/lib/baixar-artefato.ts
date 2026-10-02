// web/lib/baixar-artefato.ts
//
// BAIXAR UM ARTEFATO, em um lugar só. Três telas precisam disto (a tabela de
// Artefatos do app, a lista de Artefatos da Home e o painel de camadas do
// globo), e o caminho certo não é óbvio: `GET /artifacts/{id}/download` NÃO
// devolve o arquivo — devolve `{download_url, filename}` em JSON, com a URL
// pré-assinada do MinIO. Navegar até o endpoint da plataforma numa aba nova
// abre esse JSON na cara da pessoa; quem baixa é a URL pré-assinada, que já
// carrega o `Content-Disposition: attachment` na assinatura.
//
// Duas razões para passar pelo serviço em vez de abrir o endpoint direto:
//
// 1. O interceptor anexa o JWT. Navegação de topo não leva Bearer, então um
//    artefato `protected` regrediria para 401.
// 2. A URL pré-assinada é aberta em aba nova SEM puxar o arquivo para um blob
//    em memória — o `revokeObjectURL` síncrono abortava downloads grandes no
//    Firefox e no Safari.
//
// O fetch da URL pré-assinada não passa pelo interceptor, e é de propósito: ela
// aponta para o MinIO, e mandar o token da plataforma para outra origem seria
// vazá-lo.

import { GisFlowService } from "@/service/GisFlowService"

/** As frases do erro. Padrão: o português da tabela de Artefatos; a Home traduzida passa as dela. */
export interface TextosDoDownload {
  noExecutor: string
  tenteDeNovo: string
}

export const TEXTOS_DO_DOWNLOAD_PT: TextosDoDownload = {
  noExecutor: "Este arquivo permanece no executor e não pode ser baixado daqui.",
  tenteDeNovo: "Tente de novo.",
}

/**
 * Resolve a URL pré-assinada e abre o download. Devolve a mensagem do erro
 * quando não deu — quem chama decide como mostrar (toast, aviso inline) —, e
 * `null` quando deu certo. A mensagem do SERVIDOR, quando vem, passa como veio.
 */
export async function baixarArtefato(
  idHash: string,
  textos: TextosDoDownload = TEXTOS_DO_DOWNLOAD_PT,
): Promise<string | null> {
  const res = await GisFlowService.getArtifactDownload(idHash)
  if (!res.success || !res.data?.download_url) {
    // 409 é a política, não uma falha: o arquivo ficou no executor por marcação
    // `keepLocal` e o servidor não pode buscá-lo. Vale uma frase própria — "não
    // foi possível baixar" mandaria a pessoa tentar de novo para sempre.
    if (res.status === 409) return textos.noExecutor
    return res.error?.message ?? textos.tenteDeNovo
  }
  window.open(res.data.download_url, "_blank")
  return null
}
