# Expressions

`{{ ... }}` and `{% ... %}` are sandboxed Jinja2. `$Alias.campo` references the
output of another node by its label, and it works both on its own and in the middle of
a text or a JSON body.

The context provides `inputs`, `nodes`, `named` (the aliases), `now()`, `uuid()` and
`env`.

Rendering descends through dicts and lists, so it also works inside
structured fields such as the `queryParams` of database nodes — and there the TYPE is
preserved when the value is a single expression: `{{ $Filtro.limite }}` with 50
yields the integer 50, not `"50"`. In a string with text around it
(`"limite: {{ $Filtro.limite }}"`) the result is always text.

## Alias

The alias is the name by which a node is referenced. Without an explicit `alias`, the node
answers to its own `name` — hence `$Buffer.output`. With `alias`, it answers to
what you chose.

Two pitfalls that validation reports:

- `invalid_alias` / `reserved_alias`: an alias that is not an identifier (letters,
  digits and `_`, not starting with a digit) or that collides with a fixed key of the
  context is **silently discarded** by the executor, and the node goes back to answering
  to its `name`. The reference you wrote does not render.
- `duplicate_alias`: two nodes under the same alias. `named[alias]` keeps only the
  last one that ran; the others become inaccessible. With an explicit alias it is an error;
  derived from the `name` (two `Buffer` nodes without an alias) it only becomes a warning if some
  expression actually references that name.

Give a short, distinct alias to every node you intend to reference.
