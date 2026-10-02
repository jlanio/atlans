# Fontes catalogadas

O catálogo de fontes é a lista de camadas WFS que a plataforma já conhece: a
URL, a camada (`typeName`), o esquema (CRS, extensão, geometria, colunas), quem
mantém e se respondeu na última verificação. Ele existe para você NÃO adivinhar
`url`/`typeName`: uma URL inventada passa na validação (ela não toca a rede) e
só falha na execução, depois de minutos de espera e de várias voltas.

## A ordem, sempre

1. **`search_sources`** com o TEMA em 2–3 palavras — "terras indígenas",
   "focos de calor", "hidrografia", "escolas". Sem lugar nem data: a busca casa
   cada palavra (e os sinônimos dela) com instituição, título, camada,
   descrição, temas e nomes de coluna. Sem resultado, tente outra grafia
   ("queimadas" para "focos de calor") antes de qualquer outra coisa.
2. **`describe_source(id)`** e cole `node_snippet.properties` no nó `WFS`
   como estão. `schema.columns` são os nomes que um `AttributeFilter` ou uma
   expressão podem referenciar; `hints` (em `untrusted_data`) é o que quem
   registrou a fonte quer que você saiba.
3. Só se o catálogo não tiver a fonte: peça a URL a quem está usando ou
   **`probe_source(url)`** — lista as camadas — e depois
   `probe_source(url, type_name=...)` para o esquema. A sondagem não baixa
   feição nenhuma, mas fala com o servidor de fora: não é o primeiro passo.
4. **`register_source(url, type_name, title, tags, hints)`** guarda a fonte no
   workspace, para a próxima pergunta (sua ou de qualquer membro) encontrá-la
   em `search_sources`. Escreva `hints` como se fosse para você daqui a um
   mês: o filtro que funciona, a coluna de data, a unidade.

## O que os campos dizem

- `state`: `ok` respondeu na última verificação; `falhando` não (leia
  `last_error`); `nao_verificada` ainda não foi conferida — vale um
  `probe_source` antes de executar. A validação avisa `failing_source` e
  `unknown_source` sem tocar a rede.
- `priority`: 1 é a preferida entre camadas parecidas; 3 é secundária. Em
  empate, a mais usada (`uses`).
- `scope`: `platform` é o catálogo comum (o Vault de geoserviços da
  plataforma); `workspace` foi registrada por alguém do workspace.
- `node_snippet.properties.sortBy`: a coluna que permite paginar a camada no
  GeoServer; não remova. `maxFeatures` e `bbox` são seus: recorte no servidor
  sempre que a pergunta tiver um lugar.
- `cqlFilter` também é seu: o filtro por atributo roda NO SERVIDOR (ECQL do
  GeoServer), antes da paginação — só o que interessa atravessa a rede. Use os
  nomes de `schema.columns`, texto entre aspas simples: `uf_sigla = 'MT'`,
  `area_ha > 100 AND fase_ti = 'Regularizada'`, `nome LIKE 'São%'`. Com `bbox`
  preenchido, o recorte entra no filtro sozinho. Servidor que não é GeoServer
  falha com "não aplica o filtro CQL": aí deixe `cqlFilter` vazio e filtre
  depois da leitura (`AttributeFilter`).
- `schema.columns_source`: `describe_feature_type` (lido do servidor),
  `vault` (a tabela do catálogo) ou `run` (o que uma execução viu — sem tipo).

## O que NÃO fazer

- Não invente `url` nem `typeName`, nem "corrija" um nome de camada de cabeça:
  o nome inclui o prefixo do namespace (`Funai:tis_poligonais`), e a
  sondagem lista os certos.
- Não sonde o que já está catalogado: `probe_source` responde `catalog_hint`
  quando o endpoint já está no catálogo — volte a `search_sources`.
- Não use `probe_source` para "ver se a fonte está de pé" antes de cada
  execução: `state` e a verificação diária já dizem isso.

## Exemplo

Pedido: "terras indígenas de Mato Grosso no globo".

1. `search_sources(query="terras indígenas")` → `Funai:tis_poligonais`
   (FUNAI, `ok`, prioridade 1).
2. `describe_source(id)` → `node_snippet.properties` com `url`, `typeName` e
   `sortBy: "gid"`; `schema.columns` traz `uf_sigla`.
3. Nó `WFS` com essas propriedades + `cqlFilter: "uf_sigla = 'MT'"` +
   `PublishMap` — a receita 5 de `recipes`.
