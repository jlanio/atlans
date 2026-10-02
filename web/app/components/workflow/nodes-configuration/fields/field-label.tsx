// Rotulo de campo de configuracao de no, com a ajuda embutida.
//
// Este arquivo ja existia para centralizar o `<p className="text-xs
// text-muted-foreground">` repetido em string-field, numeric-field,
// boolean-field e companhia — mas so o numeric-field chegou a adota-lo, e os
// outros seguiram montando o proprio paragrafo. Agora ele e o unico caminho, e
// mudou de forma: a descricao deixou de ser paragrafo e virou tooltip.
//
// Por que: sao 182 descricoes no catalogo, mediana de 53 caracteres mas com
// picos de 210. Num no de 7 campos — e os que se configura mais tem de 6 a 10 —
// o texto auxiliar ocupava mais espaco que os proprios controles, e o painel
// virava parede cinza. Como tooltip, a explicacao continua inteira e a um hover
// de distancia, e o painel volta a ser uma lista de campos.
import { TbHelpCircle } from "react-icons/tb"

import { Label } from "@/app/components/ui/label"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/app/components/ui/tooltip"
import { INodesPropertyAPI } from "@/service/types"

interface AjudaProps {
  texto: string
  /** Para o nome acessivel do gatilho — "Ajuda: Nome do arquivo". */
  rotulo: string
}

/**
 * O gatilho e um `<button>`, e nao um `<span>`: assim o Radix lhe da foco e o
 * texto fica alcancavel pelo teclado. Trocar paragrafo por tooltip nao pode
 * custar o acesso de quem nao usa mouse — antes o texto era lido por todos e
 * ocupava espaco de todos; agora e o inverso, sem tirar de ninguem.
 */
export const AjudaDoCampo = ({ texto, rotulo }: AjudaProps) => (
  // `delayDuration` acima de zero (o default do nosso Tooltip) porque os icones
  // ficam na coluna dos rotulos, bem no caminho do mouse descendo o formulario:
  // com abertura instantanea, atravessar o painel dispara um tooltip atras do
  // outro. 300ms e curto para quem mira e suficiente para quem so passa.
  <Tooltip delayDuration={300}>
    <TooltipTrigger
      type="button"
      aria-label={`Ajuda: ${rotulo}`}
      // O anel de foco e explicito: `outline-none` sozinho apagaria o unico
      // sinal de onde o teclado esta, e a mudanca de cor (muted → foreground)
      // e fraca demais para servir de indicador.
      className="text-muted-foreground/70 hover:text-foreground shrink-0 rounded-sm transition-colors outline-none focus-visible:ring-[2px] focus-visible:ring-ring/60"
    >
      <TbHelpCircle size={14} />
    </TooltipTrigger>
    {/* Largura maxima porque ha descricoes de 200+ caracteres: sem teto, o
        tooltip vira uma linha unica atravessando a tela. */}
    <TooltipContent side="top" align="start" className="max-w-[320px] text-xs leading-relaxed">
      {texto}
    </TooltipContent>
  </Tooltip>
)

interface FieldLabelProps {
  field: INodesPropertyAPI
  /**
   * Elemento que o rotulo rotula. `null` para os campos cujo controle e de
   * terceiros e nao aceita `id` — Monaco no `code`/`sql`, JsonEditor no
   * `object`. Um `<label for>` apontando para id inexistente e uma associacao
   * quebrada: o leitor de tela anuncia um rotulo orfao e o clique nao faz nada.
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
        {/* O execute() recusa este campo vazio (schema `required`). Sinalização,
            não bloqueio: a validação dura continua no backend. */}
        {field.required && <span aria-label="obrigatório" className="text-destructive ml-0.5">*</span>}
      </Label>
      {field.description && <AjudaDoCampo texto={field.description} rotulo={texto} />}
    </div>
  )
}
