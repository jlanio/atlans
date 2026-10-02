# Como o dado anda pelas arestas

O executor decide o que o nó filho recebe com três casos, nesta ordem:

| Aresta | O que o nó filho recebe |
|---|---|
| com `from_key` | `{to_key ou from_key: pai["from_key"]}` |
| só `to_key` | `{to_key: primeiro valor do pai}` |
| sem nenhum dos dois | TODAS as saídas do pai, com os nomes originais |

`from_key` é a chave de SAÍDA do pai — os nomes vêm das portas declaradas do
nó (`describe_node` lista em `outputs`). `to_key` é o nome com
que o valor chega no `inputs` do filho.

## Quando nomear

Se o filho aceita várias entradas distintas (um `SpatialJoin` com camada A e
camada B, um `SubWorkflowOutput` com várias portas), `to_key` é **obrigatório**
— sem ele as duas arestas espalham e a segunda sobrescreve a primeira, em
silêncio. Se o filho só consome um dado, pode deixar as duas em branco.

## `from_key` inexistente não derruba a run

Em produção o executor é tolerante de propósito: um `from_key` sem
correspondência **omite** a porta (uma saída opcional ou um pai pulado não
podem derrubar um fluxo legítimo). O resultado é o pior tipo de defeito — o
fluxo termina verde com o dado errado.

Por isso a checagem é ESTÁTICA. `validate_workflow` compara cada `from_key`
com as saídas declaradas da origem e devolve:

- `edge_from_key_unknown` (**erro**): o `from_key` não é saída declarada do nó
  de origem. Fiação defasada — quase sempre um nome de porta antigo.
- `edge_spread_ambiguous` (**aviso**): aresta sem `from_key` nem `to_key`
  saindo de um nó com várias saídas. Funciona, mas o que chega ao filho
  depende da ordem das chaves do pai. Nomeie.

Origem que não declara saída nenhuma não gera diagnóstico: não há com o que
comparar.

## Bifurcação

Aresta que sai de um nó de controle carrega `condition: true` ou
`condition: false`, e o executor só ativa as que casam com o `branch` do nó. O
ramo perdedor é marcado como pulado e não executa.

```json
[
  { "source": "cond1", "target": "envia",   "condition": true,  "source_handle": "true"  },
  { "source": "cond1", "target": "arquiva", "condition": false, "source_handle": "false" }
]
```

`source_handle: "true"|"false"` acompanha, e é o que o editor usa para ancorar
a aresta visualmente. Sem ele a aresta some do canvas ao reabrir — grave os
dois.

Nós que bifurcam: `Conditional`, `JinjaBranch`, `ChangeDetector`. O `Switch`
roteia por porta nomeada (`from_key: "output_0"`), não por `condition`.

Uma aresta de bifurcação **não** leva `from_key`. O filho recebe o dict inteiro
do pai — o dado com o nome original, mais `branch`, `value` e `result`.

## Aresta solta

Aresta cuja ponta não existe entre os nós é ignorada pelo executor sem dizer
nada; a validação a acusa como aviso `orphan_edge`. Nó sem caminho a partir de
um gatilho fica fora da simulação e do run: `unreachable_node`. Os dois são
avisos, mas quase sempre significam fiação que você achou que tinha feito.
