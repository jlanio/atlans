# Expressões

`{{ ... }}` e `{% ... %}` são Jinja2 em sandbox. `$Alias.campo` referencia a
saída de outro nó pelo rótulo dele, e funciona tanto sozinho quanto no meio de
um texto ou de um corpo JSON.

O contexto traz `inputs`, `nodes`, `named` (os aliases), `now()`, `uuid()` e
`env`.

A renderização desce por dicionário e lista, então funciona também dentro de
campos estruturados como o `queryParams` dos nós de banco — e ali o TIPO é
preservado quando o valor é uma expressão só: `{{ $Filtro.limite }}` com 50
entrega o inteiro 50, não `"50"`. Numa string com texto em volta
(`"limite: {{ $Filtro.limite }}"`) o resultado é sempre texto.

## Alias

O alias é o nome pelo qual um nó é referenciado. Sem `alias` explícito, o nó
responde pelo próprio `name` — daí `$Buffer.output`. Com `alias`, responde pelo
que você escolheu.

Duas armadilhas que a validação acusa:

- `invalid_alias` / `reserved_alias`: alias que não é um identificador (letras,
  dígitos e `_`, sem começar por dígito) ou que colide com uma chave fixa do
  contexto é **descartado em silêncio** pelo executor, e o nó volta a atender
  pelo `name`. A referência que você escreveu não renderiza.
- `duplicate_alias`: dois nós sob o mesmo alias. `named[alias]` guarda só o
  último que rodou; os demais ficam inacessíveis. Com alias explícito é erro;
  derivado do `name` (dois `Buffer` sem alias) só vira aviso se alguma
  expressão de fato referencia esse nome.

Dê um alias curto e distinto a todo nó que você pretende referenciar.
