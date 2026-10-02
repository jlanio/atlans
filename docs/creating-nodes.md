# Como Criar um Novo Nó

Este guia explica passo a passo como adicionar um novo nó ao motor de workflows do Atlans.

## Sumário

- [Conceitos Fundamentais](#conceitos-fundamentais)
- [Passo 1 — Escolha a categoria](#passo-1--escolha-a-categoria)
- [Passo 2 — Crie o arquivo do nó](#passo-2--crie-o-arquivo-do-nó)
- [Passo 3 — Implemente `description()`](#passo-3--implemente-description)
- [Passo 4 — Implemente `execute()` (ou `execute_sync()`)](#passo-4--implemente-execute-ou-execute_sync)
- [Passo 5 — Registro automático](#passo-5--registro-automático)
- [Passo 6 — Verifique no editor](#passo-6--verifique-no-editor)
- [Referência: BaseNode](#referência-basenode)
- [Referência: Tipos de propriedades](#referência-tipos-de-propriedades)
- [Exemplos comentados](#exemplos-comentados)
- [Checklist final](#checklist-final)

---

## Conceitos Fundamentais

Um **nó** é uma unidade atômica de processamento dentro de um workflow DAG. Cada nó:

- Recebe um dicionário `inputs` com as saídas dos nós anteriores
- Tem parâmetros configuráveis pelo usuário (acessados via `self.get_param()` / `self.parameters`)
- Retorna um dicionário `outputs` que alimenta os nós seguintes

```
      [Nó A]
         │ output "output" ──(aresta: from_key/to_key)──▶
         ▼
      [Nó B]  ← inputs = {"output": GeoDataFrame}
         │ output "output" ──▶
         ▼
      [Nó C]
```

> **Como o dado atravessa a aresta.** As chaves que chegam em `inputs` são definidas **na
> própria aresta** (`from_key`/`to_key`, escolhidas no canvas), não por parâmetros do nó. Um
> nó novo deve **ler/escrever chaves de saída fixas** (por convenção, `output`) e declará-las
> em `outputs`; quem conecta escolhe a porta no editor. O antigo padrão de parâmetros
> `inputKey`/`outputKey` foi **aposentado** — nenhum nó do repositório o usa e o runtime não
> o interpreta mais (ver `docs/specs/edge-data-contract.md`). Não crie parâmetros
> `inputKey`/`outputKey`: eles seriam simplesmente descartados.

---

## Passo 1 — Escolha a categoria

Coloque o arquivo do nó na categoria semanticamente correta:

| Pasta | Quando usar | Nós existentes (referência) |
|-------|-------------|----------------------------|
| `flow/nodes/action/` | Transformações de atributos, requisições HTTP, geocodificação, scripts | `SetFields`, `Sort`, `RemoveDuplicates`, `HttpRequest`, `GeocodeNode`, `PythonScript` |
| `flow/nodes/spatial/` | Operações geométricas (buffer, clip, dissolve, join espacial…) | `Buffer`, `Clip`, `Dissolve`, `SpatialJoin`, `CentroidNode`, `UnionNode`, `Simplify`, … |
| `flow/nodes/datasource/` | Leitura de dados (banco, arquivos, WFS, APIs) | `DatabaseSpatialQuery`, `ReadGeoJSON`, `ReadShapefile`, `WFS`, `DataInput`, … |
| `flow/nodes/outputs/` | Escrita de resultados (arquivos, banco, S3, webhook, e-mail) | `SaveGeoJSON`, `SaveToPostGIS`, `SaveToS3`, `SendEmail`, `SendWebhook` |
| `flow/nodes/control/` | Controle de fluxo (condicional, loop, merge, sub-workflow, roteamento) | `Conditional`, `Switch`, `Merge`, `Loop`, `JinjaBranch`, `SubWorkflow` |
| `flow/nodes/trigger/` | Gatilhos de execução (agendamento, webhook, arquivo) | `ScheduleTrigger`, `WebhookTrigger`, `FileTrigger`, `GeofenceTrigger` |

> Observação: o `type` da categoria (usado em `description()`) é **singular** — para a pasta
> `outputs/` o `type` é `"output"`. Note também que o `name` de registro de alguns nós carrega
> o sufixo `Node` (`GeocodeNode`, `CentroidNode`, `UnionNode`, `SimplifyNode`), enquanto outros
> não (`Buffer`, `Clip`). O `name` é livre — só precisa ser único (ver Passo 3).

---

## Passo 2 — Crie o arquivo do nó

**Não existe um `_template.py`.** Crie o arquivo do zero, ou copie um nó existente próximo do
que você precisa e adapte:

```bash
# Do zero:
touch flow/nodes/spatial/meu_no.py

# Ou copiando um nó simples como ponto de partida:
cp flow/nodes/spatial/simplify.py flow/nodes/spatial/meu_no.py
```

O nome do arquivo deve ser `snake_case`. O nome da classe pode ser `PascalCase`.

Esqueleto mínimo:

```python
import asyncio
from typing import Any, Dict

from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger

logger = get_logger(__name__)


@register_node
class MeuNo(BaseNode):
    @classmethod
    def description(cls) -> Dict[str, Any]:
        ...

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        ...
```

---

## Passo 3 — Implemente `description()`

O método `description()` é um `classmethod` que retorna os metadados do nó. Esses metadados
são usados pelo:
- **Registry** — para identificar e instanciar o nó pelo campo `name`
- **Editor visual** — para gerar o formulário de configuração automaticamente
- **API `/nodes/`** — para listar os nós disponíveis
- **Simulação de schema (`validate_service`, tool `validate_workflow` do MCP)** — via `outputs`/`dynamic_output`

```python
@classmethod
def description(cls) -> Dict[str, Any]:
    return {
        # Identificador único no registro — sem espaços, sem acentos.
        # É a CHAVE do registro (flow/registry.py) e é salvo na definition do
        # workflow no campo "name" do nó. A fábrica instancia o nó procurando
        # node_def["name"] no NODE_REGISTRY (flow/factory.py). NÃO MUDE após o
        # nó estar em uso em produção — crie um nó novo se precisar mudar.
        "name": "MeuNo",

        # Nome exibido no editor visual para o usuário
        "alias": "Meu Nó",

        # Descrição completa — aparece como tooltip/ajuda no editor
        "description": "Realiza X operação sobre Y dados, retornando Z resultado.",

        # CATEGORIA do nó (define ícone/cor no editor e é usada no filtro do grafo).
        # NÃO é o identificador — o identificador é "name" acima.
        # Valores: "trigger" | "action" | "spatial" | "datasource" | "output" | "control"
        "type": "spatial",

        # Parâmetros configuráveis pelo usuário
        "properties": [
            {
                "name": "distance",         # chave do parâmetro em self.parameters
                "label": "Distância",       # rótulo exibido no editor (opcional, recomendado)
                "type": "number",           # ver tabela de tipos abaixo
                "default": 100,             # default aplicado por self.validate()
                "description": "Distância do buffer em unidades do CRS.",
            },
        ],

        # Campos de saída — a FONTE ÚNICA do contrato de saída: as chaves do
        # dict que execute() devolve, com tipo. Usados pelo editor (painel de
        # schema, seletor de porta, autocomplete), pela simulação/preview e
        # pela detecção de "schema drift" no executor.
        #   - `port: True` marca um campo com ponto de conexão próprio no
        #     canvas (2+ deles ⇒ handles nomeados; nenhum ⇒ saída anônima).
        #   - Nós de RAMO (Conditional e afins) declaram `"branches": True`:
        #     os pontos de saída são true/false e roteiam a execução.
        "outputs": [
            {"name": "output", "type": "geodataframe",
             "description": "GeoDataFrame com o resultado."},
        ],
    }
```

### Campos de propriedade especiais

Além de `name`/`type`/`default`/`description`, uma propriedade pode ter:

```python
# Lista de opções (renderiza um select). Use type "select"; cada opção é um
# objeto {value, label}. self.validate() valida o valor contra os "value".
{
    "name": "crs",
    "label": "CRS de saída",
    "type": "select",
    "default": "EPSG:4326",
    "description": "Sistema de referência de coordenadas.",
    "options": [
        {"value": "EPSG:4326",  "label": "WGS 84 (4326)"},
        {"value": "EPSG:31983", "label": "SIRGAS 2000 / UTM 23S (31983)"},
    ],
},

# Exibição condicional: só mostra o campo quando outro parâmetro tem certo valor.
{
    "name": "fieldName",
    "label": "Campo",
    "type": "string",
    "default": "",
    "description": "Nome do campo a avaliar.",
    "visibleWhen": {"field": "metric", "in": ["field"]},
},
```

### Nós que exigem credencial

Há dois padrões em uso, ambos válidos:

```python
# (a) Nós de banco (DatabaseSpatialQuery, SaveToPostGIS): sinalizam com
#     requires_credential + um parâmetro credential_id (string). O SERVIDOR
#     resolve a credencial e injeta a connectionString decifrada (ver Passo 4).
"requires_credential": True,
# ... em properties:
{"name": "credential_id",     "type": "string", "default": "", "description": "UUID da credencial."},
{"name": "connectionString",  "type": "string", "default": "", "description": "DSN (injetada automaticamente)."},

# (b) Seletor de credencial no editor: propriedade do tipo "credential" com
#     credential_types (PLURAL, lista) filtrando os tipos compatíveis
#     (ex.: HttpRequest, SaveToS3, SaveGeoJSON com webhook opcional).
{
    "name": "credential_id",
    "type": "credential",
    "credential_types": ["http_bearer", "http_basic"],
    "default": "",
    "description": "Credencial de autenticação.",
},
```

### Saída dinâmica (`dynamic_output` + `simulate`)

Se o nó gera saídas que dependem dos parâmetros/entrada (ex.: `Switch` com N baldes,
`DatabaseSpatialQuery` cujo schema vem do SQL), marque `"dynamic_output": True` e,
opcionalmente, implemente um `classmethod async simulate(cls, parameters, simulated_inputs)`
que devolve a lista de schema. É isso que a validação (`validate_service`) usa para prever o schema
sem executar (ver `flow/nodes/datasource/database_spatial_query.py::simulate`); a resposta marca
esses nós com `schema_source: "simulated"`. Sem `simulate`, o nó `dynamic_output` **não some**
da resposta: o validate deriva as saídas do próprio payload — `output_vars` (PythonScript),
`rules[].output` + `fallback_output` (Switch), `ports` (`outputs_from_ports`,
`SubWorkflowInput`) — ou, na falta deles, dos `outputs` do catálogo, e marca
`schema_source: "declared"`. É uma
aproximação pela declaração: implementar `simulate()` continua sendo o que dá o schema real.

---

## Passo 4 — Implemente `execute()` (ou `execute_sync()`)

A lógica do nó vive em `execute()` (assíncrono) OU em `execute_sync()` (síncrono, para nós
CPU-bound). Escolha um:

- **`execute_sync(self, inputs)`** — para nós **CPU-bound** (pandas/GeoPandas/Shapely, Jinja
  linha a linha). A classe base despacha o corpo síncrono para um pool de threads dedicado
  automaticamente — você **não** precisa de `asyncio.to_thread`. É a forma recomendada pela
  `BaseNode` para trabalho pesado de CPU (ex.: `flow/nodes/action/field_transformer.py`).
- **`async def execute(self, inputs)`** — quando o nó **aguarda I/O assíncrono** de verdade
  (`asyncpg`, `httpx` com `await`). Nesse caso, mande o trabalho **bloqueante** (parsing,
  cálculos GeoPandas) para dentro de `asyncio.to_thread()` para não travar o event loop. É o
  padrão da maioria dos nós existentes (ex.: `buffer.py`, `simplify.py`).

Regras obrigatórias em qualquer um dos dois:

1. **Chame `self.validate()` na primeira linha** — aplica os defaults declarados e coage os
   tipos (`number`→float, `integer`→int, `select` validado contra as opções). Praticamente
   todos os nós fazem isso.
2. Acesse parâmetros via `self.get_param()` / `self.parameters` (nunca `self.properties` —
   esse atributo levanta erro de propósito).
3. Obtenha a entrada com `self.get_first_gdf(inputs)` (primeiro GeoDataFrame) ou
   `self.get_input_gdf(inputs, key)` (chave específica).
4. Retorne um `dict` de saídas com chaves fixas (ex.: `{"output": gdf}`).
5. **Idempotência:** o executor pode chamar `execute()` mais de uma vez em caso de retry
   (ver `retry_count`/`retry_delay_s` na referência). Evite efeitos colaterais não repetíveis
   ou torne-os idempotentes.

Exemplo (nó de I/O ou misto — `async execute` + `to_thread` para o trecho pesado):

```python
async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
    # 1. Defaults + validação de tipos
    self.validate()

    # 2. Parâmetros (já coagidos por self.validate())
    distance = self.get_param_float("distance", 100.0)

    # 3. Entrada — primeiro GeoDataFrame disponível
    gdf = self.get_first_gdf(inputs)

    # 4. Trabalho bloqueante numa thread separada (não trava o event loop)
    def _apply_buffer(df):
        return df.copy().assign(geometry=df.geometry.buffer(distance))

    result = await asyncio.to_thread(_apply_buffer, gdf)

    # 5. Log de resumo
    logger.info("%s: buffer de %.1f aplicado em %d feições.",
                self.__class__.__name__, distance, len(result))

    # 6. Retorne com chave de saída fixa
    return {"output": result}
```

Mesma lógica como nó **CPU-bound** (sem `async`, sem `to_thread` — a base cuida da thread):

```python
def execute_sync(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
    self.validate()
    distance = self.get_param_float("distance", 100.0)
    gdf = self.get_first_gdf(inputs)
    result = gdf.copy().assign(geometry=gdf.geometry.buffer(distance))
    return {"output": result}
```

### Lidando com credenciais

O **servidor** (não o executor) resolve a credencial e injeta o valor decifrado nos
parâmetros do nó antes da execução (ver `app/services/credential_resolver.py`). Para os tipos
de banco, o valor chega no parâmetro **`connectionString`** (camelCase); para HTTP, chega em
`http_auth`.

```python
async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
    self.validate()
    # A connectionString decifrada foi injetada pelo servidor a partir de credential_id.
    conn_str = self.get_param("connectionString")   # NÃO "connection_string"
    if not conn_str:
        raise ValueError("Credencial não resolvida: 'connectionString' vazia.")

    def _query(cs):
        import geopandas as gpd
        return gpd.read_postgis("SELECT * FROM tabela", cs, geom_col="geom")

    result = await asyncio.to_thread(_query, conn_str)
    return {"output": result}
```

> Nós de banco costumam usar o helper `flow/utils/credencial.py::obter_conexao(self.parameters)`,
> que lê e valida `parameters["connectionString"]`.

### Publicando saída no terminal de logs do usuário

Os atributos injetados pelo executor permitem publicar eventos. O publisher é uma instância
de `WorkflowEventPublisher` (classe abstrata, método **síncrono** `publish_event(...)`) — não
existe `RedisPublisher` nem um método `publish()`. Para enviar linhas ao terminal do usuário
(equivalente a `print()`), use o helper de módulo `publish_stdout`, exatamente como faz o
`PythonScript` (`flow/nodes/action/python_script.py`):

```python
from flow.utils.publisher.events import publish_stdout

# self._publisher pode ser None fora do contexto de execução — o helper trata isso.
publish_stdout(self._publisher, self._task_id, self.node_id,
               [f"Processando {len(gdf)} feições..."])
```

Para uma mensagem simples de log (sem terminal do usuário), prefira `self.log("...")` ou o
`logger` de módulo.

---

## Passo 5 — Registro automático

O `registry.py` descobre seu nó automaticamente ao importar o módulo. Basta adicionar o
decorator `@register_node` à classe:

```python
from flow.registry import register_node
from flow.nodes.base import BaseNode

@register_node   # ← Isso é tudo que é necessário para o registro
class MeuNo(BaseNode):
    ...
```

> O `registry.py` usa `pkgutil.walk_packages` para importar todos os módulos em `flow/nodes/`
> recursivamente. Não é necessário editar nenhum outro arquivo. O decorator valida que a
> classe herda de `BaseNode` e que o `name` de `description()` é único (nomes duplicados
> levantam erro no boot).

**Importante:** o valor `"name"` em `description()` é o identificador permanente. A fábrica
instancia o nó procurando `node_def["name"]` no registro (`flow/factory.py`). Uma vez que
workflows em produção usem esse nome, **não o altere** — crie um nó novo se precisar mudar o
comportamento.

Se renomear for inevitável, é no MESMO commit: uma entrada em `NOMES_ANTIGOS`
(`flow/nodes/contrato.py`, nome antigo → novo), o mapeamento das propriedades que mudaram em
`app/services/nos_renomeados.py` e, no deploy, `python -m app.cli migrar-nos --aplicar`. Foi
por faltar isso que a renomeação de 27/07 (`DriveTrigger` → `DataInput`, `ArtifactOutput` →
`DataOutput`) deixou fluxos salvos falhando todo dia com "Node 'DriveTrigger' não encontrado".
Com a entrada no mapa, o lint e a fábrica também passam a dizer para onde o nó foi.

---

## Passo 6 — Verifique no editor

1. Reinicie o worker e a API:
   ```bash
   docker compose restart api worker
   ```

2. Acesse `http://localhost:8000/docs` → `GET /nodes/` → verifique se seu nó aparece na lista

3. Acesse `http://localhost:3000` → abra um workflow → na paleta de nós (drawer) → seu nó
   deve aparecer na categoria correta

4. Arraste o nó para o canvas, configure os parâmetros e execute um workflow de teste

---

## Referência: BaseNode

Métodos e atributos disponíveis para todos os nós (`flow/nodes/base.py`):

### Ciclo de vida

| Método | Descrição |
|--------|-----------|
| `description()` (classmethod, abstrato) | Metadados do nó (obrigatório) |
| `async execute(self, inputs)` | Lógica principal (assíncrona). Default: despacha `execute_sync` para o pool de threads |
| `execute_sync(self, inputs)` | Corpo síncrono para nós CPU-bound (implemente este OU sobrescreva `execute`) |
| `async setup(self)` | Hook opcional chamado ANTES de `execute()` |
| `async teardown(self)` | Hook opcional chamado APÓS `execute()` (inclusive em erro) |
| `validate(self)` | Aplica defaults de `description()['properties']` e coage tipos. Chame no início de `execute()` |

### Acesso a parâmetros

| Método | Descrição |
|--------|-----------|
| `self.get_param(name, default)` | Retorna parâmetro como está |
| `self.get_param_float(name, default)` | Converte para `float`, lança `ValueError` se inválido |
| `self.get_param_int(name, default)` | Converte para `int` (via `int(float(...))`) |
| `self.get_param_bool(name, default)` | Converte para `bool` (aceita `True`/`"true"`/`"1"`/`"yes"`/`"sim"`) |
| `self.get_retry_params()` | Retorna `(retry_count, retry_delay_s)` (defaults `0`, `5.0`) |

### Acesso a inputs

| Método | Descrição |
|--------|-----------|
| `self.get_input_gdf(inputs, key)` | GeoDataFrame pela chave. Lança `ValueError` se ausente/vazio, `TypeError` se não for GeoDataFrame |
| `self.get_first_gdf(inputs)` | Primeiro GeoDataFrame não-vazio. Avisa se houver mais de um candidato distinto; lança `ValueError` se nenhum |

### Atributos injetados pelo executor

| Atributo | Tipo | Descrição |
|----------|------|-----------|
| `self.node_id` | `str` | Identificador do nó no workflow |
| `self.parameters` | `dict` | Parâmetros configurados pelo usuário |
| `self.context` | `dict` | Contexto compartilhado com o executor (ex.: `_subflow_ancestors`) |
| `self._publisher` | `WorkflowEventPublisher \| None` | Publicador de eventos (pode ser `None` fora do contexto de execução) |
| `self._task_id` | `str \| None` | ID da run/tarefa atual |
| `self._workspace_id` | `str \| None` | ID do workspace (isolamento multi-tenant) |
| `self._workflow_hash` | `str \| None` | Hash do workflow (state cross-run) |
| `self._debug_mode` | `bool` | `True` se o workflow está em modo debug |

Helpers de contexto: `self.require_execution_context()` (garante `_workspace_id`/`_task_id`) e
`self.derive_label(...)` (resolve o `label` de nós de saída).

### Retentativas (retry)

O executor lê `retry_count` e `retry_delay_s` dos parâmetros do nó (defaults `0` e `5.0`s) e
reexecuta `execute()` em caso de exceção. Esses são parâmetros de **plataforma** — não precisam
ser declarados em `properties`, e não são reportados como "descartados". Como `execute()` pode
rodar mais de uma vez, mantenha-o **idempotente**.

### Logging

```python
# Opção 1: logger de módulo (recomendado)
from flow.utils.logger import get_logger
logger = get_logger(__name__)
logger.info("Mensagem")

# Opção 2: helper de instância (sem import)
self.log("Mensagem")
```

---

## Referência: Tipos de propriedades

| `type` | Renderização no editor | Observação |
|--------|----------------------|------------|
| `"string"` | Input de texto | Padrão para a maioria dos parâmetros |
| `"number"` | Input numérico | `self.validate()` já coage para `float`; leia com `get_param_float()` |
| `"integer"` | Input numérico inteiro | `self.validate()` coage para `int`; leia com `get_param_int()` |
| `"boolean"` | Checkbox | Use `get_param_bool()` para leitura segura |
| `"select"` | Dropdown | Requer `options: [{"value":…, "label":…}]`; `self.validate()` valida o valor |
| `"object"` | Editor JSON | Aceita `dict` ou `list` (JSON serializado é decodificado) |
| `"code"` | Editor Monaco (Python) | Para nós que recebem código como parâmetro (ex.: `PythonScript`) |
| `"credential"` | Select de credenciais | Requer `credential_types` (lista) para filtrar por tipo compatível |
| `"ports"` | Editor de portas de entrada | Só com `"dynamic_inputs": True`; grava uma lista de nomes (identificadores). Com 2+ portas o editor grava o `to_key` de cada aresta; com 0/1 a aresta é anônima (ex.: `PythonScript`, `CartaImagem`). Leia com `_parse_ports()` |
| `"keyvalue"` | Pares chave → valor | Lista rasa de duas colunas (ex.: cabeçalhos do `HttpRequest`, cores por porta do `CartaImagem`). Chega como `dict` (ou JSON em string num fluxo antigo): leia com um parser tolerante |

> Em `outputs[].type`, o `type` descreve o **tipo do dado de saída** (ex.:
> `"geodataframe"`, `"any"`, `"number"`, `"boolean"`), não um widget de UI.

> **Jinja em valores de string:** propriedades `"string"`/`"object"` podem conter expressões
> Jinja2 (`{{ row.campo }}`, `{{ env.VARIAVEL }}`). O nó `SetFields`
> (`flow/nodes/action/field_transformer.py`) usa isso para transformações por linha, com um
> `jinja2.sandbox.SandboxedEnvironment` (ambiente **sandboxed**, não `jinja2.Environment` cru).

---

## Exemplos comentados

### Nó de operação espacial simples (CPU-bound via `async execute` + `to_thread`)

```python
# flow/nodes/spatial/simplify_geometry.py
import asyncio
import geopandas as gpd
from typing import Any, Dict

from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger

logger = get_logger(__name__)


@register_node
class SimplifyGeometry(BaseNode):
    """Remove vértices desnecessários preservando a topologia."""

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            "name": "SimplifyGeometry",
            "alias": "Simplificar Geometria",
            "description": "Simplifica geometrias reduzindo o número de vértices.",
            "type": "spatial",
            "properties": [
                {
                    "name": "tolerance",
                    "label": "Tolerância",
                    "type": "number",
                    "default": 1.0,
                    "description": "Tolerância na unidade do CRS. Valores maiores = mais simplificação.",
                },
                {
                    "name": "preserveTopology",
                    "label": "Preservar topologia",
                    "type": "boolean",
                    "default": True,
                    "description": "Se ativado, preserva a topologia durante a simplificação.",
                },
            ],
            "outputs": [
                {"name": "output", "type": "geodataframe",
                 "description": "GeoDataFrame com geometrias simplificadas."},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()

        tolerance = self.get_param_float("tolerance", 1.0)
        preserve_topology = self.get_param_bool("preserveTopology", True)

        # Entrada: primeiro GeoDataFrame disponível (a porta é escolhida na aresta)
        gdf = self.get_first_gdf(inputs)

        def _simplify(df: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
            result = df.copy()
            result[result.geometry.name] = df.geometry.simplify(
                tolerance, preserve_topology=preserve_topology
            )
            return result

        result = await asyncio.to_thread(_simplify, gdf)

        logger.info("%s: tolerância=%.2f aplicada em %d feições.",
                    self.__class__.__name__, tolerance, len(result))

        # Chave de saída FIXA (declarada em outputs)
        return {"output": result}
```

### Nó que consome uma API externa (I/O assíncrono real)

```python
# flow/nodes/datasource/fetch_geojson_url.py
import asyncio
import io
import httpx
from typing import Any, Dict

from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger

logger = get_logger(__name__)


@register_node
class FetchGeoJsonUrl(BaseNode):
    """Baixa um GeoJSON de uma URL e o disponibiliza como GeoDataFrame."""

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            "name": "FetchGeoJsonUrl",
            "alias": "Buscar GeoJSON por URL",
            "description": "Faz download de um GeoJSON público e o converte em GeoDataFrame.",
            "type": "datasource",
            "properties": [
                {
                    "name": "url",
                    "label": "URL",
                    "type": "string",
                    "default": "",
                    "description": "URL pública do arquivo GeoJSON.",
                },
            ],
            "outputs": [
                {"name": "output", "type": "geodataframe",
                 "description": "GeoDataFrame carregado da URL."},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        import geopandas as gpd

        self.validate()
        url = self.get_param("url", "")
        if not url:
            raise ValueError("O parâmetro 'url' é obrigatório.")

        # Download assíncrono — httpx já é async, não usa asyncio.to_thread
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()

        # Parsing bloqueante — executa em thread
        def _parse(content: bytes):
            return gpd.read_file(io.BytesIO(content))

        gdf = await asyncio.to_thread(_parse, response.content)

        logger.info("%s: %d feições carregadas de %s.",
                    self.__class__.__name__, len(gdf), url)
        return {"output": gdf}
```

---

## Helpers de configuração — o critério

O formulário do editor é GERADO do schema (`node-config-form.tsx`): campos,
rótulos, tooltip de ajuda (`description`), asterisco de obrigatório
(`required`), exemplo no input (`placeholder`), visibilidade condicional
(`visibleWhen`), sugestões de coluna (`suggest_columns`) e opções (`options`).

**Um componente específico de nó (helper) só existe quando há COMPORTAMENTO
que o schema não expressa** — sondagem de serviço (WFS GetCapabilities),
teste de webhook, contrato assíncrono de sub-fluxo, editor de recorrência.
Nunca para layout: cor, agrupamento, texto explicativo e exemplo pertencem ao
schema, onde o MCP e a validação também os enxergam. O FileTriggerHelper —
dois inputs decorados — é o contraexemplo que morreu nesta regra.

## Checklist final

Antes de submeter o PR com o novo nó, confirme:

- [ ] Arquivo na pasta de categoria correta
- [ ] Classe decorada com `@register_node`
- [ ] `description()` tem `name` único (sem espaços, único em todo o projeto)
- [ ] `outputs` declarado (campos de saída tipados), `type` de categoria correto
- [ ] `self.validate()` chamado no início de `execute()`/`execute_sync()`
- [ ] Parâmetros acessados via `self.get_param()` (nunca `self.properties`)
- [ ] Inputs acessados via `self.get_first_gdf()` / `self.get_input_gdf()` (sem parâmetros `inputKey`/`outputKey`)
- [ ] Nós CPU-bound usam `execute_sync` OU `asyncio.to_thread` dentro de `async execute`
- [ ] I/O assíncrono (`httpx`/`asyncpg`) com `await`, sem `to_thread`
- [ ] `execute()` idempotente (pode ser reexecutado por retry)
- [ ] Chaves de saída FIXAS (ex.: `{"output": ...}`)
- [ ] Erros levantados com `raise ValueError(mensagem clara)`
- [ ] Logger configurado com `logger = get_logger(__name__)`
- [ ] Comentários e strings em português do Brasil
- [ ] Testado localmente: nó aparece em `GET /nodes/` e no editor visual
