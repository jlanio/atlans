import { FieldLabel } from "./field-label"
import { githubDarkTheme, JsonEditor } from "json-edit-react"
import type { FieldProps } from "./types"

type ObjectFieldProps = FieldProps

const ObjectField = ({ field, values, setNodeField }: ObjectFieldProps) => {

  return (
    <div>
      {/* `htmlFor={null}`: o JsonEditor e de terceiros e nao expoe id. */}
      <FieldLabel field={field} htmlFor={null} />
      <JsonEditor
        data={
          typeof values?.[field.name] === "object" ?
            values?.[field.name] ?? ""
            :
            JSON.parse(values?.[field.name] as string || "{}")
        }
        indent={1}
        theme={githubDarkTheme}
        className="border !rounded-sm"
        enableClipboard={false}
        showCollectionCount={false}
        rootName="json"
        setData={value => {
          setNodeField(field.name, value as string)
        }}
      />
    </div>
  )
}

export default ObjectField