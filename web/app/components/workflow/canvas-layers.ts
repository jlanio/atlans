/**
 * Classes das camadas que flutuam SOBRE o canvas do editor.
 *
 * Dois acertos que todo overlay precisa fazer, e que são fáceis de esquecer
 * porque o defeito não parece um defeito de CSS:
 *
 * 1. **Camada.** Nós e arestas vivem no `.react-flow__renderer`, que o React
 *    Flow declara com `z-index: 4`. Um overlay sem z-index próprio fica ABAIXO
 *    dele: o nó cobre o botão, o clique vai para o nó, o cursor vira o do
 *    canvas — e nada disso sugere "faltou z-index".
 *
 * 2. **Área morta.** O retângulo do contêiner captura o mouse inteiro, não só
 *    onde há botão. Uma coluna de botões com `gap-2` engole faixas de 8px; um
 *    contêiner sem largura definida engole a largura toda da tela. Arrastar o
 *    canvas por ali trava, e o alvo do clique deixa de ser o que se vê.
 *
 * Cuidado ao usar: o contêiner precisa ter largura de conteúdo (`w-fit` quando
 * não for `absolute` com posição fixa nos dois lados) — `pointer-events-none`
 * resolve o clique, mas um retângulo gigante ainda atrapalha a depuração.
 */
export const CAMADA_SOBRE_O_CANVAS =
  "pointer-events-none absolute z-10 [&>*]:pointer-events-auto"

/**
 * Overlay que só informa e nunca recebe clique (a animação de carga).
 *
 * Sem filhos interativos, o contêiner inteiro sai do caminho do mouse — pode
 * cobrir o canvas todo sem travar arraste nem clique.
 */
export const CAMADA_SO_LEITURA = "pointer-events-none absolute z-10"
