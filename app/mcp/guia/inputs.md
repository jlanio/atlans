# Parâmetros de execução (`inputs`)

`inputs` é o dicionário que quem dispara o fluxo passa na hora de executar. O
contrato desses valores é o `params_schema` do workflow — um campo do
workflow, **não** da definição.

## Formato do `params_schema`

```json
{
  "bairro":  { "type": "string",  "description": "Bairro alvo", "required": true },
  "minima":  { "type": "number",  "default": 500 },
  "enviar":  { "type": "boolean", "default": false },
  "filtros": { "type": "object",  "description": "Objeto livre repassado ao filtro" }
}
```

Um dicionário `{nome: {type, description?, default?, required?}}`, com
`type ∈ {string, number, boolean, object}`. Qualquer outra forma conta como
**sem contrato**: não é erro, mas os `inputs` passam sem validação nenhuma e a
resposta traz o aviso correspondente em `hints`.

## Como os valores chegam aos nós

Três caminhos, conforme o gatilho:

- **`{{ inputs.nome }}` em nó de gatilho.** Dentro de um nó `type: "trigger"`,
  `inputs` são os parâmetros de execução. Nos demais nós, `inputs` é o que
  chegou pelas ARESTAS — a mesma palavra, dois significados. Referência a
  parâmetro do usuário fora de um trigger não resolve para o que você espera.
- **`payloadField` do `WebhookTrigger`.** Com `payloadField` vazio, o corpo do
  webhook JÁ É o `inputs`. Com `payloadField: "dados"`, o corpo é lido de
  `inputs["dados"]`. `payload_schema` valida esse corpo no despacho, e é
  independente do `params_schema`.
- **`ports` do `SubWorkflowInput`.** Num fluxo chamado como sub-fluxo, as
  chaves declaradas em `ports` são o contrato de entrada: o pai as preenche
  pelo `inputsMapping` do nó `SubWorkflow`, e cada porta vira uma saída
  nomeada do trigger (a aresta que sai leva `from_key` com o nome da porta).
  Chave fora da lista é descartada.

## Coerção na execução

Ao executar, cada valor declarado passa por uma regra fixa:

1. Declarado, ausente e `required` sem `default` → erro
   `inputs.<nome> obrigatório`. Ausente com `default` → o default é usado.
2. A coerção só acontece **a partir de string** (é o que um formulário ou uma
   linha de comando entrega):
   - `number`: `int` quando o texto é só dígitos (com sinal), senão `float`.
     String vazia é erro, não zero. `bool` não conta como `number`.
   - `boolean`: `true/false/1/0/yes/no/sim/não`.
   - `string`: aceita texto; `int`, `float` e `bool` viram texto; dict e list
     são erro.
   - `object`: aceita dict ou list; string é decodificada como JSON e precisa
     dar dict ou list.
3. Chave **não declarada** passa intacta e é listada em `hints` — é assim que
   um payload de webhook mais rico que o `params_schema` continua chegando.
4. Os erros vêm agregados: `{errors: [{path, message}, ...]}`, todos de uma vez.

## `suggested_params_schema`

A validação devolve um `report.suggested_params_schema` heurístico, montado a
partir das referências `inputs.<nome>` encontradas em nós de gatilho e das
`ports` de um `SubWorkflowInput`. Cada entrada sai como
`{"type": "string", "required": true}` — o tipo é um chute pela origem, não uma
leitura do valor.

Use-o como rascunho: revise tipo, `default` e `required` antes de gravar em
`params_schema`. Quando ele vem não-vazio, `report.hints` diz exatamente isso.
