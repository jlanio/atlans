// Types shared by the node configuration field components.
// Before, each field redeclared the 3 base props — any change to one
// (adding Date to value, for example) required touching 8+ files.

import type { INodesPropertyAPI } from "@/service/types"

export type FieldValue = string | number | boolean

export interface BaseFieldProps {
  field: INodesPropertyAPI
  setNodeField: (field: string, value: FieldValue) => void
  values: Record<string, FieldValue> | undefined
}

/** Props of a specific field; inherits the 3 base fields and allows extras. */
export type FieldProps<Extra = object> = BaseFieldProps & Extra
