// web/lib/catalogo.ts
//
// O catálogo de fontes em NÚMEROS e em NOMES, para a vitrine que a Home mostra
// a quem ainda não entrou (o grupo "No catálogo" do `HomeSidebar`).
//
// Por que constante, e não um GET: a casca anônima da Home não faz requisição
// NENHUMA — é a decisão que faz o grupo "Meu" nem montar sem sessão
// (`home-sidebar.tsx`), e um `/fontes/resumo` aqui a desfaria por um número que
// muda a cada semente nova. Os valores saem de `catalogo/geoservicos/`, a mesma
// pasta que a API importa no arranque (`app/core/fontes_catalogo.py`).
//
// Quem impede que envelheçam é `tests/unit/test_vitrine_do_catalogo.py`: ele
// recalcula tudo a partir da pasta e falha DIZENDO o número novo. Trocar a
// semente e esquecer deste arquivo quebra o teste — que é exatamente o ponto.
// Se um dia a vitrine precisar do número do banco (fontes aprendidas, fontes de
// workspace), o caminho é o servidor passar por prop, nunca o cliente buscar.

/**
 * Uma base citada pela vitrine: o `rotulo` é o que a pessoa lê; a `pasta` é o
 * que PROVA que ela existe — o nome (ou o prefixo do nome) da pasta em
 * `catalogo/geoservicos/`. Os países são prefixo: "Bolívia" aparece na barra,
 * mas a pasta é `Bolivia INRA`, sem acento. O teste usa este campo para conferir
 * que nenhum nome aqui virou ficção.
 */
export interface BaseCitada {
  rotulo: string
  pasta: string
}

/**
 * O tamanho do catálogo. `paises` conta o Brasil mais os 10 de fora — e "países"
 * é aproximação deliberada: a Guiana Francesa é território francês, e o rótulo
 * na barra não cabe "países e territórios".
 */
export const CATALOGO = {
  camadas: 25_492,
  instituicoes: 76,
  paises: 11,
} as const

/** A primeira fita: os órgãos federais mais reconhecíveis. */
export const ORGAOS_FEDERAIS: readonly BaseCitada[] = [
  { rotulo: "IBGE", pasta: "IBGE" },
  { rotulo: "IBAMA", pasta: "IBAMA" },
  { rotulo: "FUNAI", pasta: "FUNAI" },
  { rotulo: "ICMBio", pasta: "ICMBio INDE" },
  { rotulo: "ANA", pasta: "ANA" },
  { rotulo: "Embrapa", pasta: "Embrapa" },
  { rotulo: "Marinha", pasta: "Marinha DHN" },
  { rotulo: "IPHAN", pasta: "IPHAN" },
]

/**
 * A segunda fita: estados e agências. Ela existe para desfazer a impressão de
 * que o catálogo é só federal — INEA e Sisema sozinhos são 22% das camadas.
 */
export const ORGAOS_REGIONAIS: readonly BaseCitada[] = [
  { rotulo: "INEA (RJ)", pasta: "INEA RJ" },
  { rotulo: "Sisema (MG)", pasta: "Sisema MG" },
  { rotulo: "SEPLAN (TO)", pasta: "SEPLAN TO" },
  { rotulo: "GEOBASES (ES)", pasta: "GEOBASES ES" },
  { rotulo: "ANP", pasta: "ANP" },
  { rotulo: "ANM", pasta: "ANM" },
  { rotulo: "MAPA", pasta: "MAPA" },
  { rotulo: "SFB", pasta: "SFB" },
]

/**
 * A terceira fita: tudo o que há fora do Brasil, na ordem do PESO no catálogo
 * (Nicarágua e Equador juntos são mais que os outros oito somados). São os dez
 * completos de propósito: escolher seis dava uma lista arbitrária, e o Chile —
 * uma camada só, a rede ferroviária — some de qualquer recorte honesto por
 * tamanho, mas é verdade que está lá.
 */
export const PAISES: readonly BaseCitada[] = [
  { rotulo: "Equador", pasta: "Equador" },
  { rotulo: "Nicarágua", pasta: "Nicarágua" },
  { rotulo: "Guiana Francesa", pasta: "Guiana Francesa" },
  { rotulo: "Argentina", pasta: "Argentina" },
  { rotulo: "Bolívia", pasta: "Bolivia" },
  { rotulo: "México", pasta: "México" },
  { rotulo: "Canadá", pasta: "Canadá" },
  { rotulo: "Uruguai", pasta: "Uruguai" },
  { rotulo: "Peru", pasta: "Peru" },
  { rotulo: "Chile", pasta: "Chile" },
]
