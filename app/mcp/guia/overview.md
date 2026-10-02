# O formato da definição

Um workflow é um grafo: `nodes` que fazem alguma coisa e `edges` que levam o
dado de um para o outro. O que está aqui foi lido do executor e dos schemas do
servidor, não de documentação. Onde há uma armadilha, ela vem com o motivo.

```json
{
  "nodes": [
    { "id": "n1", "name": "DatabaseSpatialQuery", "type": "datasource",
      "properties": { "query": "SELECT ...", "credential_id": "uuid" },
      "position": { "x": 0, "y": 0 } }
  ],
  "edges": [
    { "source": "n1", "target": "n2", "from_key": "output", "to_key": "camada" }
  ],
  "viewport": { "x": 0, "y": 0, "zoom": 1 }
}
```

- `id` é livre, só precisa ser único dentro do fluxo. Dois nós com o mesmo id
  não são um aviso: o executor montaria `{id: nó}` e o último venceria, então a
  validação recusa a definição inteira (`duplicate_node_id`).
- `name` tem de bater EXATAMENTE com o `name` do catálogo (`search_nodes`).
  Nome errado é recusado com o código `unknown_node` — junto com todo o resto
  que estiver errado, num relatório só.
- `type` é o grupo do nó no catálogo (`trigger`, `datasource`, `spatial`,
  `control`, `action`, `output`). Copie o que `describe_node` devolve: é por
  ele que o servidor sabe quais nós leem parâmetros de execução (ver `inputs`).
- `position` não afeta a execução, mas sem ela os nós empilham no canto do
  editor. Use um grid: 320 px na horizontal, 180 na vertical.

## O relatório vem inteiro, de uma vez

`validate_workflow` roda um lint estático antes de simular, e ele é
CUMULATIVO: um nome errado não interrompe a checagem dos outros nós. O que
volta é `report.errors[]` e `report.warnings[]`, cada item com
`{code, severity, node_id, edge, message}`.

Cinco códigos derrubam a definição (a tool devolve o erro `validation` com o
`report` junto, e nada é gravado):

| `code` | O que é |
|---|---|
| `unknown_node` | `name` que não existe no catálogo |
| `duplicate_node_id` | dois nós com o mesmo `id` |
| `cycle` | o grafo volta sobre si mesmo |
| `invalid_credential_id` | `credential_id` que não é UUID |
| `construction_error` | o executor não conseguiu montar o fluxo |

Os demais códigos (alias inválido, propriedade não declarada, aresta órfã, nó
inalcançável, `from_key` desconhecido) vêm como erro ou aviso no mesmo
relatório, sem impedir a leitura do resto. `report.ok` é `false` sempre que há
qualquer erro; aviso não derruba.

Corrija tudo o que o relatório apontou e valide de novo — não uma coisa por
rodada.

## `properties` × `parameters`

A definição gravada usa **`properties`**. As tools aceitam os dois nomes como
sinônimos (em conflito, `parameters` vence), e gravam sempre `properties`.
Escreva `properties` e não pense mais nisso.

## Só o que está declarado sobrevive

`BaseNode.validate()` RECONSTRÓI os parâmetros do nó a partir das propriedades
declaradas no catálogo e **descarta toda chave que não esteja lá**. Uma
propriedade inventada não vira erro de execução: ela desaparece, e o nó roda
com o default.

Consequência prática: confira o nome de cada propriedade com
`describe_node` antes de escrever — o `name` aceita uma lista (até 8 por
chamada), então peça as fichas de todos os nós do fluxo numa chamada só. Um `timeOut` no lugar de `timeout` é
silenciosamente ignorado — na validação isso aparece como o aviso
`undeclared_property`, que é fácil de ler e fácil de ignorar. Não ignore.
