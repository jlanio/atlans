/**
 * Tabela que vira ficha empilhada no telefone.
 *
 * O que existia antes era `overflow-x-auto` com `min-w-[N]`: nada ficava
 * inalcançável — o `overflow-x: clip` do body CORTARIA sem isso —, mas ler o
 * status ou a data de uma execução exigia arrastar a tabela de lado, uma linha
 * de cada vez, e as últimas colunas viviam fora de vista.
 *
 * Aqui a linha deixa de ser linha abaixo de `md`: vira uma faixa `flex-wrap` de
 * fatos, na mesma ordem das colunas. Sete colunas viram três ou quatro linhas de
 * texto que cabem em 360px sem rolagem nenhuma.
 *
 * A escolha central é o `max-md:`: TODAS as classes daqui só existem abaixo do
 * breakpoint, então de `md` para cima a tabela é exatamente a de antes — nenhum
 * `<td>` precisa ser editado, e não há risco de regressão no desktop. O reset de
 * padding vive no seletor `[&>td]` da linha (especificidade 0,1,1) justamente
 * para vencer o `px-4 py-2.5` de cada célula sem tocá-las.
 *
 * Uso:
 *
 *   <table className="w-full md:min-w-[720px]">   // o min-w só onde há colunas
 *     <thead className={CABECALHO_DE_COLUNAS}>    // rótulo sem coluna é ruído
 *     <tr className={LINHA_EMPILHADA}>
 *       <td className={cn(DESTAQUE_DA_FICHA, "…")}>   // opcional: linha própria
 *
 * `DESTAQUE_DA_FICHA` na célula que identifica o registro (o nome, o id) dá à
 * ficha um título: sem ela as sete fatias entram todas no mesmo parágrafo e não
 * há por onde começar a ler.
 */

/** `<thead>`: some onde não há colunas para rotular. */
export const CABECALHO_DE_COLUNAS = "max-md:hidden"

/** `<tr>` de dados. */
export const LINHA_EMPILHADA =
  "max-md:flex max-md:flex-wrap max-md:items-center max-md:gap-x-3 max-md:gap-y-1 " +
  "max-md:px-3 max-md:py-3 max-md:[&>td]:p-0"

/** `<td>` que ocupa a primeira linha da ficha sozinho. */
export const DESTAQUE_DA_FICHA = "max-md:basis-full"

/**
 * `<td>` numérico que leva o próprio rótulo na ficha. Sem a coluna acima, "0"
 * pode ser falhas ou cache hits, e "1,2 GB" pode ser Drive, artefatos ou total —
 * o rótulo é o que separa um dado de um número solto. Some em `md`, onde o
 * cabeçalho volta a dizer a mesma coisa.
 *
 *   <td data-rotulo="Falhas" className={cn(CELULA_COM_ROTULO, "…")}>
 */
export const CELULA_COM_ROTULO =
  "max-md:before:content-[attr(data-rotulo)] max-md:before:mr-1 " +
  "max-md:before:text-muted-foreground max-md:before:font-normal"

/**
 * `<tr>` de conteúdo expandido (a linha de erro que abre sob a execução, com
 * `colSpan`): não é uma ficha, é um bloco — `flex-wrap` a espremeria em fatias.
 */
export const LINHA_EXPANDIDA = "max-md:block"
