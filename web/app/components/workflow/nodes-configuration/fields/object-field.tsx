import { FieldLabel } from "./field-label"
import { JsonEditor } from "json-edit-react"
// json-edit-react 2 moved the ready-made themes to their own package.
import { githubDarkTheme } from "@json-edit-react/themes"
import type { FieldProps } from "./types"

type ObjectFieldProps = FieldProps

const ObjectField = ({ field, values, setNodeField }: ObjectFieldProps) => {

  return (
    <div>
      {/* `htmlFor={null}`: JsonEditor is third-party and doesn't expose an id. */}
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
        showClipboardButton={false}
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