# Carta imagem — o nó `CartaImagem`

> Contrato do nó de saída que gera a **carta imagem** (PNG, JPG ou PDF) com as camadas que o fluxo
> escolher. Código: `flow/nodes/outputs/carta_imagem.py` (o nó) e `flow/utils/carta.py` (a
> matemática, pura). Testes: `tests/unit/test_carta_imagem.py`, `tests/unit/test_carta_helpers.py`,
> `tests/integration/test_carta_no_executor.py`.

## 1. O que é

Um nó só, de saída (`type: "output"`), com **portas dinâmicas**: cada porta é uma camada da carta e
a pessoa liga a ela a saída que quiser ver desenhada. O que não está ligado fica de fora. Ao rodar, o
nó compõe as camadas com título, subtítulo, legenda, créditos, escala gráfica, seta de norte, grade
de coordenadas e fundo de mapa — cada elemento **opcional**, escolhido na configuração — e grava o
arquivo como um **artefato da execução** (a mesma lista de artefatos, o Meu → Artefatos da Home, o
download). Não há prévia inline nem cartão na Home: a carta é um arquivo para baixar.

Não existe gancho de fim de run e não precisa existir: o próprio grafo garante que o nó roda
depois de todas as camadas ligadas às suas portas.

## 2. Portas e arestas — as regras que mandam

As regras vêm do editor (`web/app/components/workflow/utils/resolve-edge-keys.ts`, `node-ports.ts`)
e do executor (`flow/executor/edge_resolver.py`):

| Portas declaradas | O que o editor faz | O que chega ao nó |
|---|---|---|
| **2 ou mais** | grava o `to_key` de cada aresta com o nome da porta; um ponto de conexão por porta | `inputs[nome_da_porta]` — a camada da porta; porta sem camada é pulada com aviso |
| **1 ou nenhuma** | aresta anônima; o canvas barra a segunda aresta (`limitadoAUmaAresta`) | o dict do nó anterior espalhado (`inputs["output"]`…): a carta desenha o primeiro GeoDataFrame que chegar, com o nome da porta (ou "Camada") na legenda |

Por que barrar a segunda aresta com 0/1 porta: duas arestas anônimas espalhariam os dois dicts na
mesma chave, a última venceria e a carta sairia com uma camada só — e o nó não tem como perceber a
perda. É a mesma regra do `SubWorkflowOutput`.

O nome da porta tem de ser identificador (`NOME_DE_PORTA`: letras, números e `_`), por isso o
**rótulo da legenda tem campo próprio** (`rotulos`); sem ele, o nome da porta com `_` virando espaço.
A ordem das portas é a ordem de desenho (a primeira fica por baixo) e a ordem da legenda.

## 3. Propriedades

| Nome | Tipo | Padrão | Notas |
|---|---|---|---|
| `ports` | `ports` | `[]` | uma porta por camada |
| `titulo` | string | `Carta` | também dá o nome do arquivo (`slugify(titulo).ext`) |
| `subtitulo`, `creditos` | string | vazio | opcionais; a atribuição do fundo entra sozinha nos créditos |
| `formato` | select | `png` | `png`, `jpg` (qualidade 90), `pdf` (vetorial nas geometrias) |
| `tamanho` | select | `a4-paisagem` | A4/A3, paisagem/retrato (ISO 216) |
| `dpi` | integer | 150 | 72 a 300; **teto de 30 Mpx** por página (A3 a 300 dpi passa) |
| `rotulos` | keyvalue | `{}` | porta → rótulo na legenda |
| `cores` | keyvalue | `{}` | porta → `#RRGGBB`; vazio = paleta de 8 cores; cor inválida é erro |
| `opacidade` | number | 0.7 | 0–1, para todas as camadas |
| `legenda`, `escala`, `norte` | boolean | `true` | |
| `grade` | boolean | `false` | linhas e rótulos de coordenadas nas bordas |
| `fundo` | select | `nenhum` | `hibrido` / `satelite` / `ruas` (os da instalação, `MAPA_*`), `personalizado` |
| `fundo_url` | string | vazio | template com `{z}`, `{x}` e `{y}`; só com `fundo = personalizado` |
| `crs` | string | `auto` | ver §4 |
| `credential_id` | credential | vazio | token Bearer do download; sem ele o artefato é público; some com localidade `executor` |
| `localidade` | select | `herdar` | `herdar` / `executor` — como todo nó que grava artefato |

`validate_node_parameters` coage tipos mas não aplica mínimo/máximo: dpi, tamanho e o teto de pixels
são conferidos no `execute`. `keyvalue` e `ports` chegam como objeto ou JSON em string (fluxo salvo
antigo) — os parsers são tolerantes.

## 4. CRS da carta

| `crs` | `fundo` | Resultado |
|---|---|---|
| qualquer | ≠ `nenhum` | **EPSG:3857** sempre — os tiles são Web Mercator e o fundo não é reprojetado |
| `auto` | `nenhum` | o **UTM local** estimado pelo centro da extensão de todas as camadas (`estimate_utm_crs`); extensão acima de ~6° de longitude ganha aviso de distorção; sem zona UTM (regiões polares) cai em 3857 com aviso |
| `EPSG:xxxx` / WKT | `nenhum` | o CRS pedido; texto inválido é erro |

A ordem importa: camada **sem CRS é tratada como EPSG:4326 antes** de qualquer reprojeção (um
`set_crs` com o CRS da carta rotularia graus como metros).

A **escala gráfica só existe em CRS projetado** (`is_projected`); em graus ela é pulada com aviso
no log. Em 3857 o comprimento é corrigido por cos(latitude central) — a barra mede a distância real
no chão, não a distância no plano. Comprimentos redondos: 1, 2 ou 5 × 10ⁿ metros, cerca de um quinto
da largura do mapa.

A **grade**: em 3857 as linhas são de longitude/latitude redondas (a conversão é exata: x só depende
de lon, y só de lat); em UTM, múltiplos redondos de metros; em graus, graus.

## 5. Página e composição

A moldura é fixa e a extensão cresce até a proporção dela (nunca corta): mapa à esquerda; coluna da
direita com a legenda (só existe com legenda; sem ela o mapa toma a página); título e subtítulo no
topo; créditos e a data + CRS no rodapé; seta de norte e escala dentro do mapa (canto superior
direito e inferior esquerdo). Extensão = união das camadas + 5 % de folga; um ponto só ganha 500 m
(ou 0,01°) de lado.

O desenho usa a API orientada a objeto do matplotlib (`Figure` + `FigureCanvasAgg`) numa thread,
com `matplotlib.use("Agg")` antes de qualquer plot (o `gdf.plot` importa o pyplot por dentro e o
backend se resolve na thread; no desktop o Tk é podado do runtime). Geometrias são simplificadas a
1 px antes de desenhar; acima de 200 mil feições o log avisa e o PDF sai rasterizado.

O matplotlib é importado **só na hora de desenhar** — `flow/` é importado pela API e pelos testes de
catálogo. Num executor antigo, sem a biblioteca, o nó falha com "A carta imagem precisa do
matplotlib no executor: atualize…". O cache de fontes vai para `artifacts_root()/.mpl`.

## 6. Fundo de mapa (tiles)

- Os fundos com nome são os da instalação, os mesmos do mapa web (`web/lib/fundos-do-mapa.ts`):
  `MAPA_HIBRIDO_URL`, `MAPA_SATELITE_URL` e `MAPA_RUAS_URL` (com os `_CREDITO`), no ambiente da
  API. O código não traz satélite nenhum; as ruas, sem configuração, são `tile.openstreetmap.org`.
  O executor não tem essa configuração: o servidor a injeta no nó ao despachar
  (`fundo_da_instalacao`, `app/services/fundos_do_mapa.py`), e sem ela vale o ambiente do executor.
  A injeção escreve nas duas formas de propriedades do nó e sempre substitui o que vier no fluxo.
  Sem o híbrido, vale o satélite, como no web. Um fundo com nome sem configuração falha dizendo
  qual variável falta. `personalizado` exige `{z}`, `{x}` e `{y}`.
- Um executor desta versão com um servidor anterior não recebe o fundo (o servidor antigo não o
  injeta), e a carta diz isso, em vez de dizer que a instalação não o tem. Por isso o servidor
  é atualizado antes dos executores e do app desktop.
- Zoom: o menor em que a largura do mapa em pixels de tile alcança a largura da página; teto de
  **256 tiles** (o zoom desce até caber — nunca falha por tamanho) e zoom máximo 19.
- Cada tile passa por **`safe_httpx_request`** (pina o IP, bloqueia redirect, limita o corpo a 2 MB),
  como nos nós de HTTP: um template escrito no fluxo não alcança a rede interna nem os metadados da
  nuvem (`validate_url_ssrf`). Duas conexões por vez, User-Agent `Atlans/carta (+<site da instalação>)`
  (`flow/utils/identidade.py`),
  duas novas tentativas só em erro de transporte/502/503/504; 4xx é erro definitivo.
- Atribuição: `© OpenStreetMap contributors` (ODbL — obrigatória) ou o `MAPA_*_CREDITO` do fundo
  entram nos créditos sozinhos. A política de uso do OSM pede uso leve e identificado; o fundo é
  opcional e desligado por padrão.
- O executor precisa de internet na hora do run; sem ela a carta falha (o fundo foi pedido).

## 7. O artefato

`persistir_artefato(localidade, content, filename, content_type, …)` — o mesmo caminho dos outros
nós de saída: MinIO por URL pré-assinada (com o `Content-Type` certo: `image/png`, `image/jpeg`,
`application/pdf`) ou disco do executor com "manter apenas no executor". O servidor grava `format`
cru (`png`/`jpg`/`pdf`); o download força `attachment`.

O nó devolve as chaves **planas** declaradas em `outputs` (`artifact_filename`,
`artifact_s3_key`, `format`, `size_bytes`, `camadas`, `largura_px`, `altura_px`) mais `__artifact__`
— o executor compara as chaves de topo com as declaradas e acende o aviso de drift no painel quando
não casam.

**Dois nós com o mesmo título no mesmo run** gravariam a mesma chave S3 e o servidor deduplicaria em
silêncio: o nó registra o nome do arquivo no `context` do run e o segundo falha pedindo títulos
diferentes (o mesmo nó em retry não é colisão).

## 8. Onde a carta aparece

- `/artifacts` (badge de formato com ícone de imagem/PDF) e Meu → Artefatos na Home (ícone por
  extensão; a linha é inerte, com o motivo "carta imagem: sem prévia no globo — baixe o arquivo").
- O painel de execução mostra as chaves de saída do nó, como para todo nó; não lista artefatos
  (para formato nenhum) — follow-up.
- O assistente da Home só emite `camada` para GeoJSON; uma carta gerada por um fluxo do assistente
  fica na lista de artefatos — follow-up.

## 9. Dependência

`matplotlib==3.10.9` em `requirements.txt` e `executor/requirements-full.txt` (o desktop usa o
lock do executor). CI, imagens e o runtime do desktop rodam Python 3.12; a linha 3.10.x do
matplotlib traz pillow, contourpy, cycler, fonttools, kiwisolver e pyparsing. Backends Agg
e PDF embutidos e a fonte DejaVu no pacote — nada de cairo/freetype de sistema.

O lock do desktop é gerado por `npm run python:lock` com um `python.exe`; sem Windows à mão, a
mesma resolução sai do pip de qualquer plataforma:

```bash
python -m pip install --dry-run --ignore-installed --only-binary=:all: \
  --platform win_amd64 --python-version 3.10 --implementation cp --abi cp310 \
  --report /tmp/report.json -c desktop/requirements.lock.txt -r executor/requirements-full.txt
# o conjunto {name==version} do "install" do relatório tem de ser IDÊNTICO às linhas do lock;
# o job `desktop` do CI (windows-latest, `python:lock:check`) é o juiz final.
```

Executores só ganham o nó ao atualizar a imagem (Docker) ou o app desktop.
