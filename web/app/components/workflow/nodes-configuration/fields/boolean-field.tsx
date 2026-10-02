import { FieldLabel } from "./field-label"
import { Switch } from "@/app/components/ui/switch"
import type { FieldProps } from "./types"

type BooleanFieldProps = FieldProps

/**
 * Linha, e nao cartao.
 *
 * Era o UNICO campo com `rounded-lg border p-3 shadow-sm` — todos os outros sao
 * rotulo e controle soltos. Numa lista mista os toggles viravam ancoras visuais
 * arbitrarias: a moldura sugeria importancia que o campo nao tem, e "Publico"
 * pesava mais na tela que "Destino", que governa o no inteiro.
 */
const BooleanField = ({ field, values, setNodeField }: BooleanFieldProps) => (
  <div className="flex flex-row items-center justify-between gap-3">
    <FieldLabel field={field} />
    <Switch
      id={field.name}
      checked={values?.[field.name] as boolean}
      onCheckedChange={value => setNodeField(field.name, value)}
    />
  </div>
)

export default BooleanField
