/**
 * Table that turns into a stacked card on the phone.
 *
 * What existed before was `overflow-x-auto` with `min-w-[N]`: nothing was
 * unreachable — the body's `overflow-x: clip` WOULD CLIP without it —, but
 * reading a run's status or date required dragging the table sideways, one row
 * at a time, and the last columns lived out of view.
 *
 * Here the row stops being a row below `md`: it becomes a `flex-wrap` strip of
 * facts, in the same order as the columns. Seven columns become three or four
 * lines of text that fit in 360px with no scrolling at all.
 *
 * The central choice is `max-md:`: ALL the classes here exist only below the
 * breakpoint, so from `md` up the table is exactly what it was — no `<td>`
 * needs editing, and there is no risk of regression on desktop. The padding
 * reset lives in the row's `[&>td]` selector (specificity 0,1,1) precisely to
 * beat each cell's `px-4 py-2.5` without touching them.
 *
 * Usage:
 *
 *   <table className="w-full md:min-w-[720px]">   // min-w only where there are columns
 *     <thead className={CABECALHO_DE_COLUNAS}>    // a label without a column is noise
 *     <tr className={LINHA_EMPILHADA}>
 *       <td className={cn(DESTAQUE_DA_FICHA, "…")}>   // optional: a line of its own
 *
 * `DESTAQUE_DA_FICHA` on the cell that identifies the record (the name, the id)
 * gives the card a title: without it the seven slices all go into the same
 * paragraph and there is nowhere to start reading.
 */

/** `<thead>`: disappears where there are no columns to label. */
export const CABECALHO_DE_COLUNAS = "max-md:hidden"

/** Data `<tr>`. */
export const LINHA_EMPILHADA =
  "max-md:flex max-md:flex-wrap max-md:items-center max-md:gap-x-3 max-md:gap-y-1 " +
  "max-md:px-3 max-md:py-3 max-md:[&>td]:p-0"

/** `<td>` that takes the card's first line by itself. */
export const DESTAQUE_DA_FICHA = "max-md:basis-full"

/**
 * Numeric `<td>` that carries its own label in the card. Without the column
 * above, "0" could be failures or cache hits, and "1,2 GB" could be Drive,
 * artifacts or total — the label is what separates a data point from a loose
 * number. It disappears at `md`, where the header says the same thing again.
 *
 *   <td data-rotulo="Falhas" className={cn(CELULA_COM_ROTULO, "…")}>
 */
export const CELULA_COM_ROTULO =
  "max-md:before:content-[attr(data-rotulo)] max-md:before:mr-1 " +
  "max-md:before:text-muted-foreground max-md:before:font-normal"

/**
 * `<tr>` of expanded content (the error row that opens under the run, with
 * `colSpan`): it isn't a card, it's a block — `flex-wrap` would squeeze it into
 * slices.
 */
export const LINHA_EXPANDIDA = "max-md:block"
