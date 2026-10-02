# Catálogo de fontes de dados (geosserviços)

`catalogo/geoservicos/` é a semente de fontes que acompanha o repositório, um
vault de notas Markdown: uma pasta por instituição, com a nota da instituição, a
lista de camadas e os atributos de cada camada. A API importa esta pasta na subida e transforma cada
camada WFS numa **fonte de dados** da plataforma (tabela `fontes_de_dados`), que
o assistente consulta ANTES de prospectar qualquer dado externo — ver
`docs/fontes.md`.

Nada aqui é lido pela interface: o catálogo alimenta as tools MCP
`search_sources` / `describe_source` e os avisos da validação.

## De onde vem o conteúdo

Os nomes, títulos, descrições e esquemas de atributos das camadas são os que
cada serviço publica no `GetCapabilities` e no `DescribeFeatureType`, colhidos
na data de cada nota. Esse conteúdo é de cada instituição e segue os termos do
serviço de origem (muitos são dados abertos governamentais; confira os termos
antes de republicar um recorte). O que é do Atlans: a organização em notas, as
finalidades, os sinônimos e as dicas de uso.

## O que a pasta contém

```
catalogo/
  README.md                     ← este arquivo
  geoservicos/
    _sinonimos.md               ← opcional: sinônimos para a busca (raiz)
    <Instituição>/
      <Nome — SIGLA>.md         ← a nota da instituição (ou nota-base.md)
      Camadas.md                ← as camadas por grupo
      Atributos.md              ← os atributos de cada camada
```

Só as subpastas de primeiro nível são lidas; arquivos soltos na raiz (índices,
relatórios) são ignorados — exceto `_sinonimos.md`. Os nomes ficam em NFC.

## O formato de hoje (gerado pelo script do Vault)

**Nota da instituição** — o nome vem do `# título`; os campos são bullets
`- **Campo:** valor`:

```markdown
# Fundação Nacional dos Povos Indígenas — FUNAI

- **Mantenedor:** Funai
- **Finalidade:** Terras indígenas, aldeias e coordenações regionais.
- **Endpoint WFS:** <https://geoserver.funai.gov.br/geoserver/ows>
- **GetCapabilities:** <https://geoserver.funai.gov.br/geoserver/ows?service=WFS&request=GetCapabilities>
- **Versão usada para os schemas:** WFS 2.0.0
- **Última coleta de metadados:** 2026-09-17
- **Camadas inventariadas:** 12

Parágrafo livre sobre o serviço.

> [!tip] Como consumir no Atlans
> Nó WFS → url = endpoint acima, typeName = a camada.
```

- `Endpoint WFS` é **obrigatório**: sem ele a pasta é ignorada com o motivo
  `sem_endpoint_wfs` (é o que acontece hoje com as pastas ArcGIS REST e com os
  placeholders "(Metadados em validação)" — ficam para uma fase futura).
- `Versão usada para os schemas`: `WFS 2.0.0` (padrão) ou `WFS 1.0.0` (IBGE).
- URL com usuário e senha embutidos é recusada (`url_com_credencial`).
- `Finalidade` vira a descrição das camadas; o parágrafo livre e o callout
  viram as `dicas`.

**`Camadas.md`** — grupos `## Grupo (n)` e bullets `` - `ns:camada` — Título ``:

```markdown
## Funai (12)
- `Funai:tis_poligonais` — Terras indígenas (poligonais)
- `Funai:aldeias_pontos` — Aldeias (pontos)
```

**`Atributos.md`** — `### `ns:camada`` seguido da tabela
`| Campo | Tipo XSD | Nulo | Ocorrência |`. A linha cujo tipo é
`gml:<Geometria>PropertyType` define a coluna e o tipo de geometria. A primeira
coluna entre `gid, fid, id, objectid, ogc_fid` vira o `sortBy` sugerido (o
GeoServer exige um SORTBY para paginar camada sem chave primária).

## Extensões opcionais (retrocompatíveis)

O formato de hoje já é importável. O que limita a BUSCA é o título da camada:
`BC100_AC_2023_Barragem_P` não diz "barragem" para quem procura "represa", e
nada diz o país, a UF ou qual das 40 camadas parecidas é a preferida. Três
acréscimos, todos nativos do Obsidian, que o importador já lê:

1. **Frontmatter YAML na nota da instituição** (as "Propriedades" do Obsidian).
   Os campos do corpo continuam valendo; o frontmatter só torna explícito o que
   a busca precisa:

   ```yaml
   ---
   sigla: FUNAI
   pais: BR
   uf:                # "MT" quando a instituição é estadual/municipal
   endpoint_wfs: https://geoserver.funai.gov.br/geoserver/ows
   versao_wfs: "2.0.0"
   temas: [terras indígenas, povos indígenas, territórios]
   prioridade: 1      # 1 preferida · 2 normal · 3 secundária
   coletada_em: 2026-09-17
   ---
   ```

2. **Tags inline nas camadas** (`Camadas.md`), no fim da linha, para o que o
   título não diz. Saem do título e entram nos temas; `#preferida` marca
   prioridade 1 e `#secundaria` prioridade 3:

   ```markdown
   - `Funai:tis_poligonais` — Terras indígenas (poligonais) #terras-indígenas #polígono #br #preferida
   ```

   Não precisa marcar tudo: marcar as 200–300 camadas que importam (focos de
   calor, TIs, UCs, municípios, hidrografia, CAR, escolas) já muda a busca.

3. **`_sinonimos.md` na raiz** — uma tabela `| termo | sinônimos |` (ou bullets
   `- termo: a, b`). A busca expande a consulta com ela, além dos sinônimos
   padrão do serviço:

   ```markdown
   | termo | sinônimos |
   |---|---|
   | focos de calor | queimadas, incêndio, hotspot, fogo |
   | terra indígena | TI, indígena, aldeia |
   ```

## Como o servidor usa a pasta

- Na subida da API, `importar_catalogo_no_arranque()` (`app/core/fontes_catalogo.py`)
  lê `FONTES_CATALOGO_DIR` (padrão: esta pasta) e importa cada camada como fonte
  `vault` da plataforma. É idempotente: cada registro tem um hash; pasta igual à
  da última subida custa uma consulta e zero escritas. Camada que sumiu da pasta
  é marcada como removida (soft delete). Só um worker importa (lock Redis).
- Em seguida, e depois a cada `FONTES_VERIFICACAO_INTERVAL` segundos (padrão
  1 dia; 0 desliga), UM GetCapabilities por URL distinta marca as camadas
  daquela URL como `ok` ou `falhando` e preenche CRS e bbox.
- O parser é `app/services/fontes_vault.py`; a importação e a busca,
  `app/services/fontes_service.py`. As fixtures de teste em
  `tests/fixtures/vault/` são recortes reais desta pasta.

## Como atualizar

1. Exporte o Vault (a pasta `Geosserviços/`) e substitua o conteúdo de
   `catalogo/geoservicos/` — sem os arquivos soltos da raiz, exceto `_sinonimos.md`.
2. Confira localmente:

   ```bash
   python -c "from app.services import fontes_vault as v; r=list(v.ler_pasta('catalogo/geoservicos')); print(len(r))"
   pytest tests/unit/test_fontes_vault.py tests/unit/test_fontes_service.py -q
   ```

3. Abra um PR. A pasta está fora do `detect-secrets` e do limite de tamanho de
   arquivo do pre-commit (o `Atributos.md` do IBGE tem 4 MB).
