# SQL

Os nós `DatabaseQuery` e `DatabaseSpatialQuery` recebem a consulta em `query` e
os valores em `queryParams`. A credencial entra por `credential_id` — nunca a
string de conexão (ver o tópico `credentials`).

```json
{ "id": "n1", "name": "DatabaseSpatialQuery", "type": "datasource",
  "properties": {
    "credential_id": "3f2a7c18-5b90-4c2e-9a44-1d6f8e2b7c05",
    "query": "SELECT id, nome, geom FROM lotes WHERE bairro = :bairro AND area > :minima",
    "queryParams": { "bairro": "{{ inputs.bairro }}", "minima": 500 },
    "geometryColumn": "geom",
    "crs": "EPSG:4326"
  } }
```

`:placeholder` é o caminho seguro: o valor vira bind, não texto concatenado.
Interpolar com Jinja direto no SQL também funciona, mas monta a query por
concatenação — prefira o bind.

`:nome` dentro de string ou de comentário SQL **não** é tratado como
placeholder, então `WHERE obs = 'as :10 horas'` não vira parâmetro nenhum.

`queryParams` é renderizado com Jinja antes do bind e preserva o TIPO quando o
valor é uma expressão só: `{{ inputs.minima }}` com 500 entrega o inteiro 500.

Duas notas de operação:

- `timeout` (segundos) existe nos dois nós e vale a pena ajustar em consulta
  pesada; o default é 120.
- O `DatabaseSpatialQuery` declara saída dinâmica E implementa simulação: ele
  **conecta ao banco da credencial durante a validação** para descobrir as
  colunas. Não escreve nada, mas abre conexão — é por isso que a credencial
  compartilhada só entra no escopo da validação a partir do papel `operator`.
