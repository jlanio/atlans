# Run parameters (`inputs`)

`inputs` is the dictionary that whoever triggers the workflow passes at execution time. The
contract for these values is the workflow's `params_schema` — a field of the
workflow, **not** of the definition.

## Format of `params_schema`

```json
{
  "bairro":  { "type": "string",  "description": "Bairro alvo", "required": true },
  "minima":  { "type": "number",  "default": 500 },
  "enviar":  { "type": "boolean", "default": false },
  "filtros": { "type": "object",  "description": "Objeto livre repassado ao filtro" }
}
```

A dictionary `{nome: {type, description?, default?, required?}}`, with
`type ∈ {string, number, boolean, object}`. Any other shape counts as
**no contract**: it is not an error, but the `inputs` pass with no validation at all and the
response carries the corresponding warning in `hints`.

## How the values reach the nodes

Three paths, depending on the trigger:

- **`{{ inputs.nome }}` in a trigger node.** Inside a `type: "trigger"` node,
  `inputs` are the run parameters. In all other nodes, `inputs` is what
  arrived through the EDGES — the same word, two meanings. A reference to a
  user parameter outside a trigger does not resolve to what you expect.
- **`payloadField` of the `WebhookTrigger`.** With an empty `payloadField`, the
  webhook body IS the `inputs`. With `payloadField: "dados"`, the body is read from
  `inputs["dados"]`. `payload_schema` validates that body at dispatch, and is
  independent of `params_schema`.
- **`ports` of the `SubWorkflowInput`.** In a workflow called as a sub-workflow, the
  keys declared in `ports` are the input contract: the parent fills them
  through the `inputsMapping` of the `SubWorkflow` node, and each port becomes a named
  output of the trigger (the outgoing edge carries `from_key` with the port name).
  A key not in the list is discarded.

## Coercion at execution

On execution, each declared value goes through a fixed rule:

1. Declared, absent and `required` without a `default` → error
   `inputs.<nome> obrigatório`. Absent with a `default` → the default is used.
2. Coercion only happens **from a string** (which is what a form or a
   command line delivers):
   - `number`: `int` when the text is digits only (with a sign), otherwise `float`.
     An empty string is an error, not zero. `bool` does not count as `number`.
   - `boolean`: `true/false/1/0/yes/no/sim/não`.
   - `string`: accepts text; `int`, `float` and `bool` become text; dict and list
     are an error.
   - `object`: accepts dict or list; a string is decoded as JSON and must
     yield a dict or list.
3. An **undeclared** key passes through intact and is listed in `hints` — that is how
   a webhook payload richer than the `params_schema` keeps arriving.
4. The errors come aggregated: `{errors: [{path, message}, ...]}`, all at once.

## `suggested_params_schema`

Validation returns a heuristic `report.suggested_params_schema`, built
from the `inputs.<nome>` references found in trigger nodes and from the
`ports` of a `SubWorkflowInput`. Each entry comes out as
`{"type": "string", "required": true}` — the type is a guess based on the origin, not a
reading of the value.

Use it as a draft: review type, `default` and `required` before saving to
`params_schema`. When it comes back non-empty, `report.hints` says exactly that.
