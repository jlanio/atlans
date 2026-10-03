// Label for a node configuration field, with the built-in help.
//
// This file already existed to centralize the `<p className="text-xs
// text-muted-foreground">` repeated in string-field, numeric-field,
// boolean-field and company — but only numeric-field ever adopted it, and the
// others kept building their own paragraph. Now it is the only path, and it
// changed shape: the description stopped being a paragraph and became a tooltip.
//
// Why: there are 182 descriptions in the catalog, median of 53 characters but
// with peaks of 210. In a 7-field node — and the most configured ones have 6 to
// 10 — the helper text took more space than the controls themselves, and the
// panel became a gray wall. As a tooltip, the explanation stays whole and one
// hover away, and the panel is a list of fields again.
import { TbHelpCircle } from "react-icons/tb"

import { Label } from "@/app/components/ui/label"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/app/components/ui/tooltip"
import { INodesPropertyAPI } from "@/service/types"

interface AjudaProps {
  texto: string
  /** For the trigger's accessible name — "Ajuda: Nome do arquivo". */
  rotulo: string
}

/**
 * The trigger is a `<button>`, not a `<span>`: that way Radix gives it focus and
 * the text is reachable by keyboard. Swapping a paragraph for a tooltip must not
 * cost access to those who don't use a mouse — before, the text was read by
 * everyone and took space from everyone; now it is the reverse, without taking
 * from anyone.
 */
export const AjudaDoCampo = ({ texto, rotulo }: AjudaProps) => (
  // `delayDuration` above zero (our Tooltip's default) because the icons sit in
  // the label column, right in the path of the mouse going down the form: with
  // instant opening, crossing the panel fires one tooltip after another. 300ms
  // is short for someone aiming and enough for someone just passing by.
  <Tooltip delayDuration={300}>
    <TooltipTrigger
      type="button"
      aria-label={`Ajuda: ${rotulo}`}
      // The focus ring is explicit: `outline-none` alone would erase the only
      // sign of where the keyboard is, and the color change (muted → foreground)
      // is too weak to serve as an indicator.
      className="text-muted-foreground/70 hover:text-foreground shrink-0 rounded-sm transition-colors outline-none focus-visible:ring-[2px] focus-visible:ring-ring/60"
    >
      <TbHelpCircle size={14} />
    </TooltipTrigger>
    {/* Max width because there are 200+ character descriptions: without a ceiling,
        the tooltip becomes a single line across the screen. */}
    <TooltipContent side="top" align="start" className="max-w-[320px] text-xs leading-relaxed">
      {texto}
    </TooltipContent>
  </Tooltip>
)

interface FieldLabelProps {
  field: INodesPropertyAPI
  /**
   * Element the label labels. `null` for fields whose control is third-party
   * and doesn't accept an `id` — Monaco in `code`/`sql`, JsonEditor in
   * `object`. A `<label for>` pointing at a nonexistent id is a broken
   * association: the screen reader announces an orphan label and clicking does nothing.
   */
  htmlFor?: string | null
}

export const FieldLabel = ({ field, htmlFor }: FieldLabelProps) => {
  const texto = field.label ?? field.name
  const alvo = htmlFor === undefined ? field.name : htmlFor
  return (
    <div className="flex items-center gap-1.5">
      <Label htmlFor={alvo ?? undefined}>
        {texto}
        {/* execute() rejects this field when empty (schema `required`). A signal,
            not a block: the hard validation stays in the backend. */}
        {field.required && <span aria-label="obrigatório" className="text-destructive ml-0.5">*</span>}
      </Label>
      {field.description && <AjudaDoCampo texto={field.description} rotulo={texto} />}
    </div>
  )
}
