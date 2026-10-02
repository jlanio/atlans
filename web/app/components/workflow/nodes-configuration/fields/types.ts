// Tipos compartilhados pelos componentes de campo da configuração de nó.
// Antes cada field redeclarava as 3 props base — qualquer mudança em uma
// (adicionar Date no value, por ex.) exigia tocar 8+ arquivos.

import type { INodesPropertyAPI } from "@/service/types"

export type FieldValue = string | number | boolean

export interface BaseFieldProps {
  field: INodesPropertyAPI
  setNodeField: (field: string, value: FieldValue) => void
  values: Record<string, FieldValue> | undefined
}

/** Props de field específico, herda os 3 campos base e permite extras. */
export type FieldProps<Extra = object> = BaseFieldProps & Extra
