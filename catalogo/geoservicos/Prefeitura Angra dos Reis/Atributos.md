# Prefeitura Angra dos Reis — atributos das camadas

Geoportal: [[Geosserviços/Prefeitura Angra dos Reis/Prefeitura de Angra dos Reis — RJ|Prefeitura de Angra dos Reis — RJ]]

Os campos abaixo vêm de `DescribeFeatureType` (XSD), sem download de feições.

## Angra (332)

### `Angra:acesso_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:adesivo_fiscal`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `assunto` | `xsd:string` | true | 0..1 |
| `assunto_outros` | `xsd:string` | true | 0..1 |
| `autuado` | `xsd:string` | true | 0..1 |
| `bairro_id` | `xsd:long` | true | 0..1 |
| `complemento` | `xsd:string` | true | 0..1 |
| `data` | `xsd:dateTime` | true | 0..1 |
| `fiscal` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `logradouro_id` | `xsd:long` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `numero` | `xsd:string` | true | 0..1 |
| `numero_endereco` | `xsd:string` | true | 0..1 |
| `rotulo` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `fiscal_id` | `xsd:long` | true | 0..1 |
| `ano` | `xsd:int` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `Angra:aeronaves_asa_fixa_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `version` | `xsd:int` | false | 1..1 |

### `Angra:afloramento_rochoso_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |

### `Angra:afloramento_rochoso_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:ambulante`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `atividade` | `xsd:string` | false | 1..1 |
| `bairro_id` | `xsd:long` | false | 1..1 |
| `bairro_atividade_id` | `xsd:long` | false | 1..1 |
| `celular` | `xsd:int` | false | 1..1 |
| `complemento` | `xsd:string` | true | 0..1 |
| `cpf` | `xsd:int` | false | 1..1 |
| `data_nascimento` | `xsd:dateTime` | false | 1..1 |
| `email` | `xsd:string` | true | 0..1 |
| `endereco_atividade` | `xsd:string` | false | 1..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `logradouro_id` | `xsd:long` | false | 1..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | false | 1..1 |
| `numero` | `xsd:string` | false | 1..1 |
| `ponto_referencia` | `xsd:string` | false | 1..1 |
| `produto` | `xsd:string` | false | 1..1 |
| `rg` | `xsd:int` | false | 1..1 |
| `sexo` | `xsd:string` | false | 1..1 |
| `telefone` | `xsd:int` | false | 1..1 |
| `tempo_atividade_local` | `xsd:string` | false | 1..1 |
| `tipo_equipamento` | `xsd:string` | false | 1..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `Angra:apoio_campo_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `cota` | `xsd:string` | true | 0..1 |
| `hv1` | `xsd:string` | true | 0..1 |
| `cota1` | `xsd:string` | true | 0..1 |
| `hv2` | `xsd:string` | true | 0..1 |
| `cota2` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:apoio_campo_urb_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `cota` | `xsd:string` | true | 0..1 |
| `hv1` | `xsd:string` | true | 0..1 |
| `cota1` | `xsd:string` | true | 0..1 |
| `hv2` | `xsd:string` | true | 0..1 |
| `cota2` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:area_abrangencia_cras`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom_old` | `gml:GeometryPropertyType` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `Angra:area_desvalorizada_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nível_val` | `xsd:string` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |

### `Angra:area_risco`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `pluviometro_id` | `xsd:long` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `dados` | `xsd:string` | true | 0..1 |
| `bairro` | `xsd:string` | true | 0..1 |
| `bairro_id` | `xsd:long` | true | 0..1 |

### `Angra:area_urbana_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geometriaaproximada` | `xsd:string` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `Angra:areas_cerco`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `localizaca` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geom_old` | `gml:GeometryPropertyType` | true | 0..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `Angra:areas_cerco_p`

> [!warning] Schema pendente
> Este esquema ainda não foi resolvido nesta coleta. Reconsulte o endpoint antes de usar a camada.


### `Angra:areas_publicas_validadas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perim` | `xsd:double` | true | 0..1 |
| `ano_rgi` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `data_rest` | `xsd:date` | true | 0..1 |
| `rgi_n` | `xsd:long` | true | 0..1 |
| `id_bairro` | `xsd:long` | true | 0..1 |
| `cod_geo` | `xsd:string` | true | 0..1 |
| `propriet` | `xsd:string` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `areargi` | `xsd:decimal` | true | 0..1 |
| `perimrgi` | `xsd:decimal` | true | 0..1 |
| `rgi_compl` | `xsd:string` | true | 0..1 |
| `avaliacao` | `xsd:string` | true | 0..1 |
| `publica` | `xsd:string` | true | 0..1 |
| `validada` | `xsd:string` | true | 0..1 |
| `verificar` | `xsd:string` | true | 0..1 |

### `Angra:areas_publicas_validadas_new`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perim` | `xsd:double` | true | 0..1 |
| `ano_rgi` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `data_rest` | `xsd:date` | true | 0..1 |
| `rgi_n` | `xsd:long` | true | 0..1 |
| `id_bairro` | `xsd:long` | true | 0..1 |
| `cod_geo` | `xsd:string` | true | 0..1 |
| `propriet` | `xsd:string` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `areargi` | `xsd:decimal` | true | 0..1 |
| `perimrgi` | `xsd:decimal` | true | 0..1 |
| `rgi_compl` | `xsd:string` | true | 0..1 |
| `avaliacao` | `xsd:string` | true | 0..1 |
| `publica` | `xsd:string` | true | 0..1 |
| `validada` | `xsd:string` | true | 0..1 |
| `verificar` | `xsd:string` | true | 0..1 |

### `Angra:arquibancada_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `operaciona` | `xsd:string` | true | 0..1 |
| `situacaofi` | `xsd:string` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:articulacao_10000_utm`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `folha` | `xsd:string` | true | 0..1 |
| `lat_cf` | `xsd:decimal` | true | 0..1 |
| `long_cf` | `xsd:decimal` | true | 0..1 |
| `conv_merid` | `xsd:string` | true | 0..1 |
| `epsg_src` | `xsd:string` | true | 0..1 |
| `kappa` | `xsd:decimal` | true | 0..1 |
| `dec_magnet` | `xsd:string` | true | 0..1 |
| `dec_mag_da` | `xsd:string` | true | 0..1 |
| `dec_var_an` | `xsd:string` | true | 0..1 |
| `folha_mi` | `xsd:string` | true | 0..1 |
| `folha_simp` | `xsd:string` | true | 0..1 |

### `Angra:articulacao_1000_urb_utm`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `folha` | `xsd:string` | true | 0..1 |
| `lat_cf` | `xsd:decimal` | true | 0..1 |
| `long_cf` | `xsd:decimal` | true | 0..1 |
| `conv_merid` | `xsd:string` | true | 0..1 |
| `epsg_src` | `xsd:string` | true | 0..1 |
| `kappa` | `xsd:decimal` | true | 0..1 |
| `dec_magnet` | `xsd:string` | true | 0..1 |
| `dec_mag_da` | `xsd:string` | true | 0..1 |
| `dec_var_an` | `xsd:string` | true | 0..1 |
| `folha_mi` | `xsd:string` | true | 0..1 |
| `folha_simp` | `xsd:string` | true | 0..1 |

### `Angra:arvore`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `altura` | `xsd:float` | false | 1..1 |
| `area_sombreamento` | `xsd:float` | false | 1..1 |
| `arvore_proxima_edificacao` | `xsd:boolean` | true | 0..1 |
| `arvore_proxima_rede_eletrica` | `xsd:boolean` | true | 0..1 |
| `especie` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `raiz_danificando_passeio` | `xsd:boolean` | true | 0..1 |
| `geom_old` | `gml:GeometryPropertyType` | true | 0..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `Angra:arvore_isolada_urb_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:aterro_sanitario_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:aterro_sanitario_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:aterro_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:decimal` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |

### `Angra:atividade_cultural_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |

### `Angra:baia_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |

### `Angra:bairro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `codigo` | `xsd:int` | false | 1..1 |
| `nome` | `xsd:string` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `distrito_id` | `xsd:long` | true | 0..1 |

### `Angra:bairros`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:long` | true | 0..1 |
| `codigo` | `xsd:long` | true | 0..1 |

### `Angra:bairros_atendimento_cras`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `descriptio` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:string` | true | 0..1 |
| `protsocial` | `xsd:string` | true | 0..1 |
| `CRAS` | `xsd:string` | true | 0..1 |

### `Angra:bairros_cadastro_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nom_bairro` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:string` | true | 0..1 |
| `area` | `xsd:decimal` | true | 0..1 |
| `codigo` | `xsd:decimal` | true | 0..1 |

### `Angra:bairros_prefeitura`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `codigo` | `xsd:decimal` | true | 0..1 |
| `distrito` | `xsd:string` | true | 0..1 |
| `nom_bairro` | `xsd:string` | false | 1..1 |
| `top_ngeo` | `xsd:boolean` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `area` | `xsd:decimal` | true | 0..1 |

### `Angra:banco_areia_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `situacaoemagua` | `xsd:string` | true | 0..1 |
| `geometriaaproximada` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `Angra:banco_areia_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `situacaoemagua` | `xsd:string` | true | 0..1 |
| `geometriaaproximada` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `Angra:bancos_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |

### `Angra:barragem_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `matconstr` | `xsd:string` | true | 0..1 |
| `situacaofi` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:barragem_urb_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `matconstr` | `xsd:string` | true | 0..1 |
| `situacaofi` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:bem_tombado_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |

### `Angra:bloco_rocha_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | false | 1..1 |

### `Angra:bloco_rocha_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |

### `Angra:bombeiros_def_civil_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |

### `Angra:br_101_por_km`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `km` | `xsd:string` | true | 0..1 |

### `Angra:brejo_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |

### `Angra:bueiro_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:cad_saae`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `matricula` | `xsd:long` | true | 0..1 |
| `digito` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `cpf/cnpj` | `xsd:string` | true | 0..1 |
| `endereco` | `xsd:string` | true | 0..1 |
| `cep` | `xsd:string` | true | 0..1 |
| `ligacao` | `xsd:string` | true | 0..1 |
| `hidrometro` | `xsd:string` | true | 0..1 |
| `rotulo` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:string` | true | 0..1 |
| `area_bairr` | `xsd:double` | true | 0..1 |

### `Angra:cadastro_imobiliario`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `distrito` | `xsd:long` | true | 0..1 |
| `setor` | `xsd:long` | true | 0..1 |
| `quadra` | `xsd:long` | true | 0..1 |
| `lote` | `xsd:long` | true | 0..1 |
| `lote_id` | `xsd:long` | true | 0..1 |
| `unidade` | `xsd:long` | true | 0..1 |
| `bairro_id` | `xsd:long` | true | 0..1 |
| `logradouro` | `xsd:long` | true | 0..1 |
| `bairro` | `xsd:string` | true | 0..1 |
| `inscricao_` | `xsd:string` | true | 0..1 |
| `dthr_cadas` | `xsd:string` | true | 0..1 |
| `inscricaoi` | `xsd:string` | true | 0..1 |
| `imovel_exi` | `xsd:string` | true | 0..1 |
| `nome_logra` | `xsd:string` | true | 0..1 |
| `numero` | `xsd:string` | true | 0..1 |
| `complement` | `xsd:string` | true | 0..1 |
| `condominio` | `xsd:string` | true | 0..1 |
| `cep` | `xsd:string` | true | 0..1 |
| `n_hidromet` | `xsd:string` | true | 0..1 |
| `conservaca` | `xsd:string` | true | 0..1 |
| `padrao_con` | `xsd:string` | true | 0..1 |
| `patrimonio` | `xsd:string` | true | 0..1 |
| `utilizacao` | `xsd:string` | true | 0..1 |
| `sitacaouni` | `xsd:string` | true | 0..1 |
| `ocupacao` | `xsd:string` | true | 0..1 |
| `tipologiae` | `xsd:string` | true | 0..1 |
| `alinhament` | `xsd:string` | true | 0..1 |
| `piscina` | `xsd:int` | true | 0..1 |
| `situacaoed` | `xsd:string` | true | 0..1 |
| `estrutura` | `xsd:string` | true | 0..1 |
| `cobertura` | `xsd:string` | true | 0..1 |
| `paredes` | `xsd:string` | true | 0..1 |
| `esquadrias` | `xsd:string` | true | 0..1 |
| `revestimen` | `xsd:string` | true | 0..1 |
| `medidabeir` | `xsd:decimal` | true | 0..1 |
| `n_paviment` | `xsd:long` | true | 0..1 |
| `area_const` | `xsd:decimal` | true | 0..1 |
| `fracao_ide` | `xsd:decimal` | true | 0..1 |
| `proprietar` | `xsd:string` | true | 0..1 |
| `endereco_l` | `xsd:string` | true | 0..1 |
| `endereco_c` | `xsd:string` | true | 0..1 |
| `endereco_b` | `xsd:string` | true | 0..1 |
| `endereco_1` | `xsd:string` | true | 0..1 |
| `endereco_m` | `xsd:string` | true | 0..1 |
| `endereco_u` | `xsd:string` | true | 0..1 |
| `foto_facha` | `xsd:long` | true | 0..1 |
| `mes_entreg` | `xsd:string` | true | 0..1 |
| `imunidade_` | `xsd:string` | true | 0..1 |
| `inscrica_1` | `xsd:string` | true | 0..1 |

### `Angra:cadastro_morador_risco_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom_old` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `data` | `xsd:date` | true | 0..1 |
| `gps` | `xsd:int` | true | 0..1 |
| `controle` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `Angra:cais_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |

### `Angra:cais_urb_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |

### `Angra:caminho_carrocavel_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:campo_futebol_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipocampoquadra` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |
| `situacaofisica` | `xsd:string` | true | 0..1 |
| `operacional` | `xsd:string` | true | 0..1 |

### `Angra:campo_futebol_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `operaciona` | `xsd:string` | true | 0..1 |
| `situacaofi` | `xsd:string` | true | 0..1 |
| `tipocampoq` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |

### `Angra:campo_quadra_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipocampoquadra` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |
| `situacaofisica` | `xsd:string` | true | 0..1 |
| `operacional` | `xsd:string` | true | 0..1 |

### `Angra:campo_quadra_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `operaciona` | `xsd:string` | true | 0..1 |
| `situacaofi` | `xsd:string` | true | 0..1 |
| `tipocampoq` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:canal_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `situacaofi` | `xsd:string` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `matconstr` | `xsd:string` | true | 0..1 |

### `Angra:canal_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `situacaofi` | `xsd:string` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `matconstr` | `xsd:string` | true | 0..1 |

### `Angra:canal_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `matconstr` | `xsd:string` | true | 0..1 |
| `situacaofi` | `xsd:string` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |

### `Angra:canal_urb_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `matconstr` | `xsd:string` | true | 0..1 |
| `situacaofi` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |

### `Angra:caps_saude_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `endereco` | `xsd:string` | true | 0..1 |
| `bairro` | `xsd:string` | true | 0..1 |
| `telefone` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `version` | `xsd:int` | true | 0..1 |

### `Angra:captacoes`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `captacao` | `xsd:string` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `regional` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `volume` | `xsd:string` | true | 0..1 |
| `cota` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:string` | false | 1..1 |
| `lon` | `xsd:string` | false | 1..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `imagem` | `xsd:hexBinary` | true | 0..1 |

### `Angra:casa_de_maquina_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |

### `Angra:cem_saude_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `endereco` | `xsd:string` | true | 0..1 |
| `bairro` | `xsd:string` | true | 0..1 |
| `telefone` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `version` | `xsd:int` | true | 0..1 |

### `Angra:cemiterio_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:cemiterio_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:censo_ibge_2010_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cd_setor` | `xsd:string` | true | 0..1 |
| `cd_mun` | `xsd:string` | true | 0..1 |
| `nm_mun` | `xsd:string` | true | 0..1 |
| `cd_dist` | `xsd:string` | true | 0..1 |
| `nm_dist` | `xsd:string` | true | 0..1 |
| `cd_subdist` | `xsd:string` | true | 0..1 |
| `nm_subdist` | `xsd:string` | true | 0..1 |
| `cod_setor` | `xsd:string` | true | 0..1 |
| `cod_municipio` | `xsd:string` | true | 0..1 |
| `nome_do_municipio` | `xsd:string` | true | 0..1 |
| `cod_distrito` | `xsd:string` | true | 0..1 |
| `nome_do_distrito` | `xsd:string` | true | 0..1 |
| `cod_subdistrito` | `xsd:string` | true | 0..1 |
| `nome_do_subdistrito` | `xsd:string` | true | 0..1 |
| `cod_bairro` | `xsd:string` | true | 0..1 |
| `nome_do_bairro` | `xsd:string` | true | 0..1 |
| `situacao_setor` | `xsd:string` | true | 0..1 |
| `tipo_setor` | `xsd:string` | true | 0..1 |
| `domicilios` | `xsd:double` | true | 0..1 |
| `moradores` | `xsd:double` | true | 0..1 |
| `media_moradores` | `xsd:double` | true | 0..1 |
| `variancia_moradores` | `xsd:double` | true | 0..1 |
| `v005` | `xsd:double` | true | 0..1 |
| `v006` | `xsd:double` | true | 0..1 |
| `v007` | `xsd:double` | true | 0..1 |
| `v008` | `xsd:double` | true | 0..1 |
| `v009` | `xsd:double` | true | 0..1 |
| `v010` | `xsd:double` | true | 0..1 |
| `v011` | `xsd:double` | true | 0..1 |
| `v012` | `xsd:double` | true | 0..1 |

### `Angra:cerca_arame_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:cerca_arame_urb_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `tipodelimfisica` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |

### `Angra:cerca_madeira_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `tipodelimfisica` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |

### `Angra:cerca_viva_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `tipodelimfisica` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |

### `Angra:chafarizes_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |

### `Angra:ciclofaixa_urb_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |

### `Angra:ciclovia_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `situacaofi` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:clubes_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |

### `Angra:clubes_urb_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |

### `Angra:cobertura_saae_cedae`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `rotulo` | `xsd:string` | true | 0..1 |
| `area` | `xsd:decimal` | true | 0..1 |
| `esgoto` | `xsd:string` | true | 0..1 |
| `tratamento` | `xsd:string` | true | 0..1 |
| `agua_saae` | `xsd:int` | true | 0..1 |
| `agua_cedae` | `xsd:long` | true | 0..1 |
| `cedae_saae` | `xsd:int` | true | 0..1 |
| `s_cobranca` | `xsd:long` | true | 0..1 |
| `trat_part` | `xsd:decimal` | true | 0..1 |
| `empresa` | `xsd:string` | true | 0..1 |
| `version` | `xsd:int` | false | 1..1 |
| `distrito` | `xsd:string` | true | 0..1 |

### `Angra:cobertura_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipologia` | `xsd:string` | true | 0..1 |

### `Angra:col_sel_limite_bairros`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `descriptio` | `xsd:string` | true | 0..1 |
| `timestamp` | `xsd:string` | true | 0..1 |
| `begin_` | `xsd:string` | true | 0..1 |
| `end_` | `xsd:string` | true | 0..1 |
| `altitudemo` | `xsd:string` | true | 0..1 |
| `tessellate` | `xsd:long` | true | 0..1 |
| `extrude` | `xsd:long` | true | 0..1 |
| `visibility` | `xsd:long` | true | 0..1 |
| `draworder` | `xsd:long` | true | 0..1 |
| `icon` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `descri____` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:string` | true | 0..1 |
| `pop_2010` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `classes` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `Angra:col_sel_proc_residuo`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `timestamp` | `xsd:dateTime` | true | 0..1 |
| `begin` | `xsd:dateTime` | true | 0..1 |
| `end` | `xsd:dateTime` | true | 0..1 |
| `altitudemode` | `xsd:string` | true | 0..1 |
| `tessellate` | `xsd:int` | true | 0..1 |
| `extrude` | `xsd:int` | true | 0..1 |
| `visibility` | `xsd:int` | true | 0..1 |
| `draworder` | `xsd:int` | true | 0..1 |
| `icon` | `xsd:string` | true | 0..1 |
| `descri____o` | `xsd:string` | true | 0..1 |
| `endere__o` | `xsd:string` | true | 0..1 |
| `hor__rio` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `Angra:col_sel_voluntaria`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom_old` | `gml:PointPropertyType` | true | 0..1 |
| `timestamp` | `xsd:dateTime` | true | 0..1 |
| `begin` | `xsd:dateTime` | true | 0..1 |
| `end` | `xsd:dateTime` | true | 0..1 |
| `altitudemode` | `xsd:string` | true | 0..1 |
| `tessellate` | `xsd:int` | false | 1..1 |
| `extrude` | `xsd:int` | false | 1..1 |
| `visibility` | `xsd:int` | false | 1..1 |
| `draworder` | `xsd:int` | true | 0..1 |
| `icon` | `xsd:string` | true | 0..1 |
| `descri____o` | `xsd:string` | true | 0..1 |
| `endere__o` | `xsd:string` | true | 0..1 |
| `hor__rio` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `Angra:col_sel_voluntaria_itinerante`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom_old` | `gml:PointPropertyType` | true | 0..1 |
| `timestamp` | `xsd:dateTime` | true | 0..1 |
| `begin` | `xsd:dateTime` | true | 0..1 |
| `end` | `xsd:dateTime` | true | 0..1 |
| `altitudemode` | `xsd:string` | true | 0..1 |
| `tessellate` | `xsd:int` | true | 0..1 |
| `extrude` | `xsd:int` | true | 0..1 |
| `visibility` | `xsd:int` | true | 0..1 |
| `draworder` | `xsd:int` | true | 0..1 |
| `icon` | `xsd:string` | true | 0..1 |
| `descri____o` | `xsd:string` | true | 0..1 |
| `endere__o` | `xsd:string` | true | 0..1 |
| `hor__rio` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `Angra:concessionaria_servico_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |

### `Angra:consulta_apartamento`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `lote_id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `id_consulta` | `xsd:int` | true | 0..1 |
| `ci_id` | `xsd:int` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `area_construida_anuncio` | `xsd:int` | true | 0..1 |
| `area_terreno_anuncio` | `xsd:int` | true | 0..1 |
| `valor_imovel` | `xsd:int` | true | 0..1 |
| `area_terreno` | `xsd:string` | true | 0..1 |
| `area_construida` | `xsd:string` | true | 0..1 |
| `valor_construcao` | `xsd:string` | true | 0..1 |
| `valor_terreno` | `xsd:string` | true | 0..1 |
| `valor_m2_terreno` | `xsd:string` | true | 0..1 |
| `topografia` | `xsd:string` | true | 0..1 |
| `pedologia` | `xsd:string` | true | 0..1 |
| `situacaoquadra` | `xsd:string` | true | 0..1 |
| `acessopraia` | `xsd:string` | true | 0..1 |
| `acessoescadaria` | `xsd:string` | true | 0..1 |
| `ilha` | `xsd:string` | true | 0..1 |
| `limitacao` | `xsd:string` | true | 0..1 |
| `url` | `xsd:string` | true | 0..1 |
| `telefone` | `xsd:string` | true | 0..1 |
| `vaga_garagem` | `xsd:string` | true | 0..1 |
| `qtd_vaga` | `xsd:int` | true | 0..1 |
| `varanda` | `xsd:string` | true | 0..1 |
| `qtd_quarto` | `xsd:int` | true | 0..1 |
| `academia` | `xsd:string` | true | 0..1 |
| `area_lazer` | `xsd:string` | true | 0..1 |
| `area_comum` | `xsd:string` | true | 0..1 |
| `area_total_edificada` | `xsd:string` | true | 0..1 |
| `elevador` | `xsd:string` | true | 0..1 |
| `padrao_construtivo` | `xsd:string` | true | 0..1 |
| `data` | `xsd:string` | true | 0..1 |
| `geocod` | `xsd:int` | true | 0..1 |

### `Angra:consulta_imobiliaria`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `version` | `xsd:long` | false | 1..1 |
| `area_construida` | `xsd:float` | true | 0..1 |
| `area_terreno` | `xsd:float` | true | 0..1 |
| `data_consulta` | `xsd:dateTime` | true | 0..1 |
| `foto` | `xsd:hexBinary` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `nome_proprietario` | `xsd:string` | true | 0..1 |
| `telefone` | `xsd:long` | true | 0..1 |
| `valor_imovel` | `xsd:float` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `Angra:consulta_imobiliaria_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `val_imovel` | `xsd:double` | true | 0..1 |
| `val_constr` | `xsd:double` | true | 0..1 |
| `val_terren` | `xsd:double` | true | 0..1 |
| `val_m2_t` | `xsd:double` | true | 0..1 |
| `area_const` | `xsd:double` | true | 0..1 |
| `area_terre` | `xsd:double` | true | 0..1 |
| `tipo_trans` | `xsd:string` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `padrao_c` | `xsd:string` | true | 0..1 |
| `conserv` | `xsd:string` | true | 0..1 |
| `sit_terr` | `xsd:string` | true | 0..1 |
| `topografia` | `xsd:string` | true | 0..1 |
| `ocupacao` | `xsd:string` | true | 0..1 |
| `utilizacao` | `xsd:string` | true | 0..1 |
| `estrutura` | `xsd:string` | true | 0..1 |
| `parede` | `xsd:string` | true | 0..1 |
| `posicao` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | false | 1..1 |
| `1_fase` | `xsd:boolean` | true | 0..1 |

### `Angra:contencao_enconsta_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |

### `Angra:contencao_enconsta_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:contencao_encosta_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `layer` | `xsd:string` | false | 1..1 |
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:CurvePropertyType` | true | 0..1 |

### `Angra:contencao_encosta_urb_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `layer` | `xsd:string` | false | 1..1 |
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `Angra:convenio_contrato_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `referencia` | `xsd:string` | true | 0..1 |
| `objeto` | `xsd:string` | true | 0..1 |
| `endereco` | `xsd:string` | true | 0..1 |

### `Angra:corte_talude_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |

### `Angra:corte_talude_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |

### `Angra:corte_talude_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `layer` | `xsd:string` | false | 1..1 |
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `Angra:corte_talude_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |

### `Angra:corte_talude_urb_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `layer` | `xsd:string` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `Angra:costao_rochoso_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `layer` | `xsd:string` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `geometriaaproximada` | `xsd:string` | false | 1..1 |
| `id` | `xsd:int` | false | 1..1 |

### `Angra:costao_rochoso_urb_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `layer` | `xsd:string` | false | 1..1 |
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `geometriaaproximada` | `xsd:string` | false | 1..1 |

### `Angra:curva_nivel_intermediaria_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `cota` | `xsd:int` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `geometriaaproximada` | `xsd:string` | true | 0..1 |
| `depressao` | `xsd:string` | true | 0..1 |
| `tipocurvanivel` | `xsd:string` | true | 0..1 |

### `Angra:curva_nivel_intermediaria_urb_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `cota` | `xsd:long` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `depressao` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |

### `Angra:curva_nivel_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `cota` | `xsd:int` | true | 0..1 |
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `geometriaaproximada` | `xsd:string` | true | 0..1 |
| `depressao` | `xsd:string` | true | 0..1 |
| `tipocurvanivel` | `xsd:string` | true | 0..1 |

### `Angra:curva_nivel_mestra_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `cota` | `xsd:int` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `geometriaaproximada` | `xsd:string` | true | 0..1 |
| `depressao` | `xsd:string` | true | 0..1 |
| `tipocurvanivel` | `xsd:string` | true | 0..1 |

### `Angra:curva_nivel_mestra_urb_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `cota` | `xsd:long` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `depressao` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |

### `Angra:curva_nivel_urb_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:CurvePropertyType` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `cota` | `xsd:long` | true | 0..1 |
| `depressao` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |

### `Angra:dados_consulta_imobiliaria`

> [!warning] Schema pendente
> Este esquema ainda não foi resolvido nesta coleta. Reconsulte o endpoint antes de usar a camada.


### `Angra:dados_escolas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `observacoe` | `xsd:string` | true | 0..1 |
| `cod_rede_municipal` | `xsd:string` | true | 0..1 |
| `cod_inep` | `xsd:string` | true | 0..1 |
| `polo_educacional` | `xsd:string` | true | 0..1 |
| `nome_unidade` | `xsd:string` | true | 0..1 |
| `endereco` | `xsd:string` | true | 0..1 |
| `bairro` | `xsd:string` | true | 0..1 |
| `cep` | `xsd:string` | true | 0..1 |
| `email` | `xsd:string` | true | 0..1 |
| `telefone` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:string` | true | 0..1 |
| `longitude` | `xsd:string` | true | 0..1 |
| `num_salas_aula` | `xsd:string` | true | 0..1 |
| `salas_aula_usada_manha` | `xsd:string` | true | 0..1 |
| `salas_aula_usada_tarde` | `xsd:string` | true | 0..1 |
| `salas_aula_usada_noite` | `xsd:string` | true | 0..1 |
| `salas_aula_usada_integral` | `xsd:string` | true | 0..1 |
| `alunos_manha` | `xsd:string` | true | 0..1 |
| `alunos_tarde` | `xsd:string` | true | 0..1 |
| `alunos_noite` | `xsd:string` | true | 0..1 |
| `alunos_integral` | `xsd:string` | true | 0..1 |
| `alunos_total` | `xsd:string` | true | 0..1 |
| `turmas_manha` | `xsd:string` | true | 0..1 |
| `turmas_tarde` | `xsd:string` | true | 0..1 |
| `turmas_noite` | `xsd:string` | true | 0..1 |
| `turmas_integral` | `xsd:string` | true | 0..1 |
| `total_turmas` | `xsd:string` | true | 0..1 |
| `alunos_creche` | `xsd:string` | true | 0..1 |
| `alunos_pre_escola` | `xsd:string` | true | 0..1 |
| `alunos_anos_iniciais` | `xsd:string` | true | 0..1 |
| `alunos_anos_finais` | `xsd:string` | true | 0..1 |
| `alunos_eja` | `xsd:string` | true | 0..1 |
| `total_professores` | `xsd:string` | true | 0..1 |
| `total_funcionarios` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `acessibilidade` | `xsd:string` | true | 0..1 |
| `IDEB_anosFinais_2023` | `xsd:decimal` | true | 0..1 |
| `IDEB_anosIniciais_2023` | `xsd:decimal` | true | 0..1 |

### `Angra:delimitacao_fisica_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `tipodelimfisica` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:dep_abast_agua_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipodep` | `xsd:string` | true | 0..1 |

### `Angra:dep_abast_agua_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `tipodep` | `xsd:string` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `Angra:dep_abast_agua_urb_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `tipodep` | `xsd:string` | false | 1..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `Angra:dep_saneamento_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipodepgeral` | `xsd:string` | true | 0..1 |
| `tipoprodutoresiduo` | `xsd:string` | true | 0..1 |
| `tratamento` | `xsd:string` | true | 0..1 |

### `Angra:dep_saneamento_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `tipodepgeral` | `xsd:string` | false | 1..1 |
| `tipoprodutoresiduo` | `xsd:string` | false | 1..1 |
| `tratamento` | `xsd:string` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `Angra:deposito_geral_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipodepgeral` | `xsd:string` | true | 0..1 |
| `tiporesiduo` | `xsd:string` | true | 0..1 |

### `Angra:deposito_geral_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `tipodepgeral` | `xsd:string` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tiporesiduo` | `xsd:string` | true | 0..1 |

### `Angra:dique_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:dique_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:distrito`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `numero` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `Angra:distrito_sanitario`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `acid_traba` | `xsd:int` | true | 0..1 |
| `aids_notif` | `xsd:int` | true | 0..1 |
| `cobertur_1` | `xsd:int` | true | 0..1 |
| `cobertur_2` | `xsd:int` | true | 0..1 |
| `cobertur_3` | `xsd:int` | true | 0..1 |
| `cobertur_4` | `xsd:float` | true | 0..1 |
| `cobertura` | `xsd:int` | true | 0..1 |
| `d_exantem` | `xsd:int` | true | 0..1 |
| `diarreian` | `xsd:int` | true | 0..1 |
| `distritos` | `xsd:string` | true | 0..1 |
| `dst_notif` | `xsd:int` | true | 0..1 |
| `mort_acid` | `xsd:int` | true | 0..1 |
| `mort_aids` | `xsd:int` | true | 0..1 |
| `mort_diabe` | `xsd:int` | true | 0..1 |
| `mort_diver` | `xsd:int` | true | 0..1 |
| `mort_dpoc` | `xsd:int` | true | 0..1 |
| `mort_homic` | `xsd:int` | true | 0..1 |
| `mort_infan` | `xsd:float` | true | 0..1 |
| `mort_infar` | `xsd:int` | true | 0..1 |
| `mort_pneum` | `xsd:int` | true | 0..1 |
| `parto_cesa` | `xsd:int` | true | 0..1 |
| `parto_norm` | `xsd:int` | true | 0..1 |
| `sifilis_co` | `xsd:int` | true | 0..1 |
| `taxa_nasc` | `xsd:float` | true | 0..1 |

### `Angra:distritos_sanitarios_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `pop_2017` | `xsd:string` | true | 0..1 |
| `fxet_ab_01` | `xsd:string` | true | 0..1 |
| `fxet_01_04` | `xsd:string` | true | 0..1 |
| `fxet_05_09` | `xsd:string` | true | 0..1 |
| `fxet_10_14` | `xsd:string` | true | 0..1 |
| `fxet_15_19` | `xsd:string` | true | 0..1 |
| `fxet_20_29` | `xsd:string` | true | 0..1 |
| `fxet_30_39` | `xsd:string` | true | 0..1 |
| `fxet_40_49` | `xsd:string` | true | 0..1 |
| `fxet_50_59` | `xsd:string` | true | 0..1 |
| `fxet_60_69` | `xsd:string` | true | 0..1 |
| `fxet_70_79` | `xsd:string` | true | 0..1 |
| `fxet_ac_80` | `xsd:string` | true | 0..1 |
| `obito_2006` | `xsd:string` | true | 0..1 |
| `obito_2007` | `xsd:string` | true | 0..1 |
| `obito_2008` | `xsd:string` | true | 0..1 |
| `obito_2009` | `xsd:string` | true | 0..1 |
| `obito_2010` | `xsd:string` | true | 0..1 |
| `obito_2011` | `xsd:string` | true | 0..1 |
| `obito_2012` | `xsd:string` | true | 0..1 |
| `obito_2013` | `xsd:string` | true | 0..1 |
| `obito_2014` | `xsd:string` | true | 0..1 |
| `obito_2015` | `xsd:string` | true | 0..1 |
| `obito_2016` | `xsd:string` | true | 0..1 |
| `obito_2017` | `xsd:string` | true | 0..1 |
| `nasc_2006` | `xsd:string` | true | 0..1 |
| `nasc_2007` | `xsd:string` | true | 0..1 |
| `nasc_2008` | `xsd:string` | true | 0..1 |
| `nasc_2009` | `xsd:string` | true | 0..1 |
| `nasc_2010` | `xsd:string` | true | 0..1 |
| `nasc_2011` | `xsd:string` | true | 0..1 |
| `nasc_2012` | `xsd:string` | true | 0..1 |
| `nasc_2013` | `xsd:string` | true | 0..1 |
| `nasc_2014` | `xsd:string` | true | 0..1 |
| `nasc_2015` | `xsd:string` | true | 0..1 |
| `nasc_2016` | `xsd:string` | true | 0..1 |
| `nasc_2017` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | false | 1..1 |

### `Angra:economapas_unificado`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | true | 0..1 |
| `cnae_principal` | `xsd:string` | true | 0..1 |
| `razao_social` | `xsd:string` | true | 0..1 |
| `nome_fantasia` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `endereco` | `xsd:string` | true | 0..1 |
| `telefone` | `xsd:string` | true | 0..1 |
| `email` | `xsd:string` | true | 0..1 |
| `cnpj` | `xsd:long` | true | 0..1 |
| `cnae_2` | `xsd:string` | true | 0..1 |
| `nat_juridica` | `xsd:string` | true | 0..1 |
| `porte` | `xsd:string` | true | 0..1 |
| `optante_simples` | `xsd:string` | true | 0..1 |
| `socios` | `xsd:string` | true | 0..1 |
| `abertura` | `xsd:dateTime` | true | 0..1 |
| `capital_social` | `xsd:string` | true | 0..1 |
| `score_credito` | `xsd:string` | true | 0..1 |
| `score_atividade` | `xsd:string` | true | 0..1 |
| `est_faturamento_12_meses` | `xsd:string` | true | 0..1 |
| `est_funcionarios` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:decimal` | true | 0..1 |
| `longitude` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `Angra:economia`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `matricula` | `xsd:string` | false | 1..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `imagem` | `xsd:hexBinary` | true | 0..1 |
| `imobiliario_id` | `xsd:long` | true | 0..1 |

### `Angra:edificacao_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:edificacao_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:edificacao_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `pavimentos` | `xsd:long` | true | 0..1 |
| `beiral` | `xsd:string` | true | 0..1 |
| `situacaofi` | `xsd:string` | true | 0..1 |
| `tipologia` | `xsd:string` | true | 0..1 |

### `Angra:eixo_urb_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `cod_log` | `xsd:int` | true | 0..1 |
| `nome_log` | `xsd:string` | true | 0..1 |
| `bairro` | `xsd:string` | true | 0..1 |
| `tipo_log` | `xsd:int` | true | 0..1 |
| `tipo_pav` | `xsd:int` | true | 0..1 |
| `nome_log_placa` | `xsd:string` | true | 0..1 |
| `jurisdicao` | `xsd:string` | true | 0..1 |

### `Angra:elevatoria_agua`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:decimal` | false | 1..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `elev_agua` | `xsd:string` | true | 0..1 |
| `regional` | `xsd:string` | true | 0..1 |
| `bomba` | `xsd:string` | true | 0..1 |
| `vazao` | `xsd:string` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `version` | `xsd:int` | false | 1..1 |
| `imagem` | `xsd:hexBinary` | true | 0..1 |

### `Angra:elevatoria_esgoto`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `elevatoria` | `xsd:string` | true | 0..1 |
| `regional` | `xsd:string` | true | 0..1 |
| `cota_topo` | `xsd:long` | true | 0..1 |
| `cota_fundo` | `xsd:decimal` | true | 0..1 |
| `diametro` | `xsd:string` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `endereco` | `xsd:string` | true | 0..1 |
| `elev_esgoto` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `version` | `xsd:int` | false | 1..1 |
| `imagem` | `xsd:hexBinary` | true | 0..1 |

### `Angra:enseada_girassois`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |
| `Layer` | `xsd:string` | true | 0..1 |
| `PaperSpace` | `xsd:boolean` | true | 0..1 |
| `SubClasses` | `xsd:string` | true | 0..1 |
| `Linetype` | `xsd:string` | true | 0..1 |
| `EntityHandle` | `xsd:string` | true | 0..1 |
| `Text` | `xsd:string` | true | 0..1 |
| `Situação` | `xsd:string` | true | 0..1 |
| `vsefs` | `xsd:double` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |

### `Angra:enseada_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |

### `Angra:equipamento_acao_social`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `coordenador_id` | `xsd:long` | false | 1..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | false | 1..1 |
| `telefone` | `xsd:long` | true | 0..1 |
| `tipo` | `xsd:string` | false | 1..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `telefone2` | `xsd:int` | true | 0..1 |
| `rua` | `xsd:string` | true | 0..1 |
| `bairro` | `xsd:string` | true | 0..1 |
| `celular` | `xsd:long` | true | 0..1 |
| `numero` | `xsd:int` | true | 0..1 |

### `Angra:equipamento_parques_jardins`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `decreto` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `ponto_referencia` | `xsd:string` | true | 0..1 |
| `porcentagem_area_verde` | `xsd:decimal` | false | 1..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `Angra:equipamento_saude`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `bairro_id` | `xsd:long` | true | 0..1 |
| `diretor` | `xsd:string` | true | 0..1 |
| `endereco` | `xsd:string` | true | 0..1 |
| `especialidade` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `rotulo` | `xsd:string` | true | 0..1 |
| `telefone` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `Angra:escadaria_rampa_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:escadaria_via_urb_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |
| `layer` | `xsd:string` | true | 0..1 |

### `Angra:escolas_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |

### `Angra:escolas_publicas_privadas_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |

### `Angra:esf_saude_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `endereco` | `xsd:string` | true | 0..1 |
| `bairro` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:string` | true | 0..1 |
| `telefone` | `xsd:string` | true | 0..1 |
| `estrutura` | `xsd:string` | true | 0..1 |
| `servicos` | `xsd:string` | true | 0..1 |
| `consultorios` | `xsd:int` | true | 0..1 |
| `horario` | `xsd:string` | true | 0..1 |
| `turno` | `xsd:string` | true | 0..1 |
| `profissionais` | `xsd:string` | true | 0..1 |
| `leitos` | `xsd:int` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `version` | `xsd:int` | false | 1..1 |

### `Angra:estacionamento_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `finalidade` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:estacoes_hidrologicas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom_old` | `gml:GeometryPropertyType` | true | 0..1 |
| `tabela_original` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `version` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `Angra:estacoes_meteorologicas_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `version` | `xsd:int` | false | 1..1 |

### `Angra:estrutura_apoio_pesca`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | false | 1..1 |
| `geom_old` | `gml:GeometryPropertyType` | true | 0..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `Angra:estruturas_apoio_pesca_p`

> [!warning] Schema pendente
> Este esquema ainda não foi resolvido nesta coleta. Reconsulte o endpoint antes de usar a camada.


### `Angra:etas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `bairro_id` | `xsd:long` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `regional` | `xsd:string` | true | 0..1 |
| `tratamento` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `imagem` | `xsd:hexBinary` | true | 0..1 |

### `Angra:ete`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `atendimento` | `xsd:int` | true | 0..1 |
| `bairro_id` | `xsd:long` | true | 0..1 |
| `ete` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `populacao_atendida` | `xsd:int` | true | 0..1 |
| `regional` | `xsd:string` | true | 0..1 |
| `tratamento` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `imagem` | `xsd:hexBinary` | true | 0..1 |

### `Angra:extracao_mineral_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |

### `Angra:extracao_mineral_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:faixa_marginais_protecao`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `bairro_id` | `xsd:long` | true | 0..1 |
| `cnpj_cpf` | `xsd:string` | true | 0..1 |
| `largura` | `xsd:float` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `numero` | `xsd:string` | true | 0..1 |
| `referencia` | `xsd:string` | true | 0..1 |
| `requerente` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `Angra:farol_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |

### `Angra:favela_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `codagsn` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `cd_geocodm` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |

### `Angra:ferrovia_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `operaciona` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:ferrovia_urb_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `operaciona` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:fossa_filtro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `regional` | `xsd:string` | true | 0..1 |
| `tratamento` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `imagem` | `xsd:hexBinary` | true | 0..1 |

### `Angra:foto_360_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | true | 0..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `frame` | `xsd:string` | true | 0..1 |
| `altitude` | `xsd:decimal` | true | 0..1 |
| `azimuth` | `xsd:decimal` | true | 0..1 |
| `heading` | `xsd:decimal` | true | 0..1 |
| `latitude` | `xsd:decimal` | true | 0..1 |
| `longitude` | `xsd:decimal` | true | 0..1 |
| `nmea` | `xsd:string` | true | 0..1 |
| `numberofsa` | `xsd:decimal` | true | 0..1 |
| `pitch` | `xsd:decimal` | true | 0..1 |
| `quality` | `xsd:decimal` | true | 0..1 |
| `roll` | `xsd:decimal` | true | 0..1 |
| `stamp` | `xsd:string` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `path` | `xsd:string` | true | 0..1 |
| `link_foto` | `xsd:string` | true | 0..1 |
| `link_interno` | `xsd:string` | true | 0..1 |
| `link_externo` | `xsd:string` | true | 0..1 |

### `Angra:foto_fachada_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `imagem` | `xsd:hexBinary` | true | 0..1 |
| `mini_foto` | `xsd:hexBinary` | true | 0..1 |

### `Angra:fotos_campo`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `imagem` | `xsd:hexBinary` | false | 1..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `observacoes` | `xsd:string` | false | 1..1 |
| `tipo` | `xsd:string` | false | 1..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `Angra:galpao_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:geral_fiscalizacao_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `descriptio` | `xsd:string` | true | 0..1 |
| `nom_p_resp` | `xsd:string` | true | 0..1 |
| `cpf_resp` | `xsd:string` | true | 0..1 |
| `nom_p_co_r` | `xsd:string` | true | 0..1 |
| `cpf_c_resp` | `xsd:string` | true | 0..1 |
| `tip_interv` | `xsd:string` | true | 0..1 |
| `tip_ter_oc` | `xsd:string` | true | 0..1 |
| `mat_rgi` | `xsd:string` | true | 0..1 |
| `endereco` | `xsd:string` | true | 0..1 |
| `x_m_` | `xsd:double` | true | 0..1 |
| `y_m_` | `xsd:double` | true | 0..1 |
| `demolicao` | `xsd:string` | true | 0..1 |
| `data_demol` | `xsd:date` | true | 0..1 |
| `pi` | `xsd:string` | true | 0..1 |
| `pi_amb` | `xsd:string` | true | 0..1 |
| `proc_licen` | `xsd:string` | true | 0..1 |
| `def_notif` | `xsd:string` | true | 0..1 |
| `pror_praz` | `xsd:string` | true | 0..1 |
| `out_proc` | `xsd:string` | true | 0..1 |
| `proc_ext` | `xsd:string` | true | 0..1 |
| `of_org_ext` | `xsd:string` | true | 0..1 |
| `proc_judic` | `xsd:string` | true | 0..1 |
| `adi` | `xsd:string` | true | 0..1 |
| `ade` | `xsd:string` | true | 0..1 |
| `adn` | `xsd:string` | true | 0..1 |
| `adn_amb` | `xsd:string` | true | 0..1 |
| `notif` | `xsd:string` | true | 0..1 |
| `interd` | `xsd:string` | true | 0..1 |
| `a_inf` | `xsd:string` | true | 0..1 |
| `a_emb` | `xsd:string` | true | 0..1 |
| `ac_amb` | `xsd:string` | true | 0..1 |
| `multa` | `xsd:string` | true | 0..1 |
| `valor_mult` | `xsd:double` | true | 0..1 |
| `term_apree` | `xsd:string` | true | 0..1 |
| `descricao` | `xsd:string` | true | 0..1 |
| `fiscal` | `xsd:string` | true | 0..1 |
| `alv_const` | `xsd:string` | true | 0..1 |
| `lic_amb` | `xsd:string` | true | 0..1 |
| `habit` | `xsd:string` | true | 0..1 |
| `cer_re_amb` | `xsd:string` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `bairro` | `xsd:string` | true | 0..1 |
| `insc_mun` | `xsd:string` | true | 0..1 |

### `Angra:girassois`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |
| `Layer` | `xsd:string` | true | 0..1 |
| `PaperSpace` | `xsd:boolean` | true | 0..1 |
| `SubClasses` | `xsd:string` | true | 0..1 |
| `Linetype` | `xsd:string` | true | 0..1 |
| `EntityHandle` | `xsd:string` | true | 0..1 |
| `Text` | `xsd:string` | true | 0..1 |
| `Situação` | `xsd:string` | true | 0..1 |
| `vsefs` | `xsd:double` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |

### `Angra:heliponto`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `tabela_original` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `version` | `xsd:int` | false | 1..1 |

### `Angra:historico_geometria`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `schema` | `xsd:string` | true | 0..1 |
| `tabela` | `xsd:string` | true | 0..1 |
| `dthr` | `xsd:dateTime` | true | 0..1 |
| `operacao` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |

### `Angra:hospitais_saude_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `endereco` | `xsd:string` | true | 0..1 |
| `atendimento` | `xsd:string` | true | 0..1 |
| `telefone` | `xsd:string` | true | 0..1 |
| `especialide` | `xsd:string` | true | 0..1 |
| `especialidade` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `version` | `xsd:int` | false | 1..1 |

### `Angra:hospital_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |

### `Angra:igreja_templo_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |

### `Angra:ilha_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipoilha` | `xsd:string` | true | 0..1 |

### `Angra:ilha_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipoilha` | `xsd:string` | true | 0..1 |

### `Angra:imobiliario`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `alinhamento` | `xsd:string` | true | 0..1 |
| `area_construida` | `xsd:decimal` | true | 0..1 |
| `bairro_id` | `xsd:long` | true | 0..1 |
| `cobertura` | `xsd:string` | true | 0..1 |
| `complemento` | `xsd:string` | true | 0..1 |
| `condominio` | `xsd:string` | true | 0..1 |
| `conservacao` | `xsd:string` | true | 0..1 |
| `date_created` | `xsd:dateTime` | true | 0..1 |
| `dthr_cadastro` | `xsd:dateTime` | true | 0..1 |
| `endereco_bairro` | `xsd:string` | true | 0..1 |
| `endereco_cep` | `xsd:string` | true | 0..1 |
| `endereco_complemento` | `xsd:string` | true | 0..1 |
| `endereco_logradouro` | `xsd:string` | true | 0..1 |
| `endereco_municipio` | `xsd:string` | true | 0..1 |
| `endereco_uf` | `xsd:string` | true | 0..1 |
| `esquadrias` | `xsd:string` | true | 0..1 |
| `estrutura` | `xsd:string` | true | 0..1 |
| `foto_fachada_id` | `xsd:long` | true | 0..1 |
| `fracao_ideal` | `xsd:decimal` | true | 0..1 |
| `imunidade_isencao_iptu` | `xsd:boolean` | true | 0..1 |
| `inscricao_antiga` | `xsd:string` | true | 0..1 |
| `inscricaoimobiliario` | `xsd:long` | true | 0..1 |
| `last_updated` | `xsd:dateTime` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `lote_id` | `xsd:long` | true | 0..1 |
| `numero` | `xsd:string` | true | 0..1 |
| `numero_hidrometro` | `xsd:long` | true | 0..1 |
| `ocupacao` | `xsd:string` | true | 0..1 |
| `padrao_construtivo` | `xsd:string` | true | 0..1 |
| `paredes` | `xsd:string` | true | 0..1 |
| `patrimonio` | `xsd:string` | true | 0..1 |
| `pavimentos` | `xsd:int` | true | 0..1 |
| `piscina` | `xsd:boolean` | true | 0..1 |
| `proprietario_presente` | `xsd:string` | true | 0..1 |
| `revestimento` | `xsd:string` | true | 0..1 |
| `situacao_edificacao` | `xsd:string` | true | 0..1 |
| `situacao_unidade` | `xsd:string` | true | 0..1 |
| `tipo_lixo` | `xsd:string` | true | 0..1 |
| `tipologia_edificacao` | `xsd:string` | true | 0..1 |
| `unidade` | `xsd:int` | true | 0..1 |
| `utilizacao` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `secao_id` | `xsd:int` | true | 0..1 |
| `inscricao_topocart` | `xsd:string` | true | 0..1 |
| `medida_beiral` | `xsd:double` | true | 0..1 |
| `inscricao_cartografica` | `xsd:string` | true | 0..1 |
| `imovel_existente` | `xsd:string` | true | 0..1 |
| `dthr_atualizacao` | `xsd:dateTime` | false | 1..1 |
| `endereco_numero` | `xsd:string` | true | 0..1 |
| `area_terreno` | `xsd:double` | true | 0..1 |
| `logradouro_id` | `xsd:int` | true | 0..1 |
| `area_total_construida` | `xsd:double` | true | 0..1 |
| `area_calculada_terreno` | `xsd:decimal` | true | 0..1 |
| `area_calculada_construida` | `xsd:decimal` | true | 0..1 |
| `codigo_logradouro` | `xsd:long` | true | 0..1 |
| `trecho` | `xsd:long` | true | 0..1 |
| `tipo_utilizacao` | `xsd:string` | true | 0..1 |
| `area_construida_topocart` | `xsd:decimal` | true | 0..1 |
| `area_terreno_topocart` | `xsd:double` | true | 0..1 |
| `testada_lote_1` | `xsd:decimal` | true | 0..1 |
| `testada_lote_2` | `xsd:decimal` | true | 0..1 |
| `testada_lote_3` | `xsd:decimal` | true | 0..1 |
| `testada_lote_4` | `xsd:decimal` | true | 0..1 |
| `vut_2024` | `xsd:decimal` | true | 0..1 |
| `confirma_cancelamento` | `xsd:boolean` | true | 0..1 |
| `obs_cancelamento` | `xsd:string` | true | 0..1 |

### `Angra:industria_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |

### `Angra:industrias_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |

### `Angra:jardim_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |

### `Angra:jardins_estufas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |

### `Angra:lago_lagoa_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `tipomassad` | `xsd:string` | true | 0..1 |
| `regime` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |

### `Angra:lagos_lagoas_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `tipomassad` | `xsd:string` | true | 0..1 |
| `regime` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |

### `Angra:licenciamento_2013_19`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `número` | `xsd:string` | true | 0..1 |
| `ano` | `xsd:string` | true | 0..1 |
| `processo` | `xsd:string` | true | 0..1 |
| `ano_1` | `xsd:string` | true | 0..1 |
| `favorecido` | `xsd:string` | true | 0..1 |
| `bairro` | `xsd:string` | true | 0..1 |
| `x` | `xsd:string` | true | 0..1 |
| `y` | `xsd:string` | true | 0..1 |
| `data emiss` | `xsd:string` | true | 0..1 |
| `referênci` | `xsd:string` | true | 0..1 |
| `condiciona` | `xsd:string` | true | 0..1 |
| `prazo` | `xsd:string` | true | 0..1 |
| `dias resta` | `xsd:string` | true | 0..1 |
| `situação` | `xsd:string` | true | 0..1 |
| `publicado` | `xsd:string` | true | 0..1 |
| `edição b` | `xsd:string` | true | 0..1 |
| `data` | `xsd:string` | true | 0..1 |
| `cancelada` | `xsd:string` | true | 0..1 |
| `visualizar` | `xsd:string` | true | 0..1 |
| `field_21` | `xsd:string` | true | 0..1 |
| `rótulo` | `xsd:string` | true | 0..1 |

### `Angra:limite_area_homogenea_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `id_zh` | `xsd:int` | true | 0..1 |
| `nom_bairro` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:string` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |

### `Angra:limite_municipio_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nm_municip` | `xsd:string` | true | 0..1 |
| `cd_geocmu` | `xsd:string` | true | 0..1 |

### `Angra:limite_urbano_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `Angra:linha_de_costa_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:linha_de_costa_urb_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:linha_onibus_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `descricao` | `xsd:string` | true | 0..1 |
| `codigo` | `xsd:string` | true | 0..1 |
| `origem` | `xsd:string` | true | 0..1 |
| `destino` | `xsd:string` | true | 0..1 |
| `seg_a_sex` | `xsd:string` | true | 0..1 |
| `sabado` | `xsd:string` | true | 0..1 |
| `domingo` | `xsd:string` | true | 0..1 |
| `tessellate` | `xsd:int` | true | 0..1 |
| `paradas` | `xsd:string` | true | 0..1 |
| `sab_e_dom` | `xsd:string` | true | 0..1 |
| `seg_a_sab` | `xsd:string` | true | 0..1 |
| `seg_a_dom` | `xsd:string` | true | 0..1 |
| `linha` | `xsd:string` | true | 0..1 |
| `cod_topovision` | `xsd:int` | true | 0..1 |
| `cod_linha_topovision` | `xsd:int` | true | 0..1 |

### `Angra:linha_transmissao_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `especie` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:localidades_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |

### `Angra:localidades_urb_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |

### `Angra:logradouro_atualizado_25_01_24`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_bd_geo` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `fid` | `xsd:decimal` | true | 0..1 |
| `id` | `xsd:decimal` | true | 0..1 |
| `bcl_cod` | `xsd:decimal` | true | 0..1 |
| `bcl_nome` | `xsd:string` | true | 0..1 |
| `bcl_bairro` | `xsd:string` | true | 0..1 |
| `bcl_cep` | `xsd:string` | true | 0..1 |
| `bcl_tipo` | `xsd:string` | true | 0..1 |
| `bcl_bair_1` | `xsd:string` | true | 0..1 |
| `vut` | `xsd:decimal` | true | 0..1 |
| `id_bcl` | `xsd:decimal` | true | 0..1 |
| `novo_bairr` | `xsd:string` | true | 0..1 |
| `novo_cep` | `xsd:string` | true | 0..1 |
| `novo_cod` | `xsd:decimal` | true | 0..1 |
| `novo_lei` | `xsd:string` | true | 0..1 |
| `novo_nome` | `xsd:string` | true | 0..1 |
| `novo_tipo` | `xsd:string` | true | 0..1 |
| `ant_cep` | `xsd:string` | true | 0..1 |
| `log_novo_c` | `xsd:string` | true | 0..1 |
| `cep_ligia` | `xsd:string` | true | 0..1 |
| `log_concat` | `xsd:string` | true | 0..1 |
| `comp` | `xsd:decimal` | true | 0..1 |
| `nome antig` | `xsd:string` | true | 0..1 |
| `cod_log` | `xsd:long` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `path` | `xsd:string` | true | 0..1 |

### `Angra:logradouro_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `nome_antig` | `xsd:string` | true | 0..1 |
| `num_lei` | `xsd:string` | true | 0..1 |
| `publicacao` | `xsd:string` | true | 0..1 |
| `link_bo` | `xsd:string` | true | 0..1 |
| `nom_correi` | `xsd:string` | true | 0..1 |
| `obs_nome` | `xsd:string` | true | 0..1 |
| `confronta` | `xsd:string` | true | 0..1 |
| `bairro` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:string` | true | 0..1 |
| `perimetro` | `xsd:decimal` | true | 0..1 |
| `cep_pmar` | `xsd:string` | true | 0..1 |
| `cep_correi` | `xsd:string` | true | 0..1 |
| `obs_cep` | `xsd:string` | true | 0..1 |
| `cep_raiz_p` | `xsd:string` | true | 0..1 |
| `cep_raiz_c` | `xsd:string` | true | 0..1 |
| `cod` | `xsd:long` | true | 0..1 |
| `codigo` | `xsd:string` | true | 0..1 |
| `cep_correio_numerico` | `xsd:int` | true | 0..1 |
| `nome_log_bd` | `xsd:string` | true | 0..1 |
| `logradouro_id` | `xsd:short` | true | 0..1 |

### `Angra:logradouro_l_pq_siga`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `nome_log` | `xsd:string` | true | 0..1 |

### `Angra:logradouros`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |
| `bairro_id` | `xsd:long` | true | 0..1 |
| `nome_log` | `xsd:string` | true | 0..1 |

### `Angra:lote`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | true | 0..1 |
| `acesso_escadaria` | `xsd:boolean` | true | 0..1 |
| `acesso_praia` | `xsd:boolean` | true | 0..1 |
| `area` | `xsd:decimal` | true | 0..1 |
| `area_construida` | `xsd:decimal` | true | 0..1 |
| `bairro_id` | `xsd:long` | true | 0..1 |
| `cod_lote_loteamento` | `xsd:string` | true | 0..1 |
| `cod_loteamento` | `xsd:string` | true | 0..1 |
| `cod_quadra_loteamento` | `xsd:string` | true | 0..1 |
| `ilha` | `xsd:boolean` | true | 0..1 |
| `inscricao_anterior` | `xsd:string` | true | 0..1 |
| `inscricao_topocart_old` | `xsd:string` | true | 0..1 |
| `limitacao` | `xsd:string` | true | 0..1 |
| `lote` | `xsd:int` | true | 0..1 |
| `pedologia` | `xsd:string` | false | 1..1 |
| `quadra_id` | `xsd:long` | true | 0..1 |
| `quantidade_unidades` | `xsd:int` | true | 0..1 |
| `situacao_quadra` | `xsd:string` | false | 1..1 |
| `topografia` | `xsd:string` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `inscricao_topocart` | `xsd:string` | true | 0..1 |
| `dthr_atualizacao` | `xsd:dateTime` | false | 1..1 |
| `situacao_foto` | `xsd:int` | true | 0..1 |
| `area_terreno_prefeitura` | `xsd:boolean` | true | 0..1 |
| `virtualizado` | `xsd:boolean` | true | 0..1 |
| `id_face_quadra` | `xsd:int` | true | 0..1 |
| `ilha_usar_fracao` | `xsd:boolean` | true | 0..1 |

### `Angra:lote_a_cn_angra`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_lote` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `Angra:lote_confrontantes_pq_siga`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `lote` | `xsd:int` | true | 0..1 |

### `Angra:lote_principal_pq_siga`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `lote` | `xsd:int` | true | 0..1 |

### `Angra:lotes`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |
| `distrito` | `xsd:long` | true | 0..1 |
| `setor` | `xsd:long` | true | 0..1 |
| `quadra` | `xsd:long` | true | 0..1 |
| `lote` | `xsd:string` | true | 0..1 |
| `nome_bairr` | `xsd:string` | true | 0..1 |
| `situacaoqu` | `xsd:string` | true | 0..1 |
| `topografia` | `xsd:string` | true | 0..1 |
| `pedologia` | `xsd:string` | true | 0..1 |
| `limitacao` | `xsd:string` | true | 0..1 |
| `cod_bairro` | `xsd:long` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |

### `Angra:macega_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |

### `Angra:manguezal_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |

### `Angra:Mapa_bairros_angra`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `descriptio` | `xsd:string` | true | 0..1 |
| `timestamp` | `xsd:string` | true | 0..1 |
| `begin` | `xsd:string` | true | 0..1 |
| `end` | `xsd:string` | true | 0..1 |
| `altitudemo` | `xsd:string` | true | 0..1 |
| `tessellate` | `xsd:long` | true | 0..1 |
| `extrude` | `xsd:long` | true | 0..1 |
| `visibility` | `xsd:long` | true | 0..1 |
| `draworder` | `xsd:long` | true | 0..1 |
| `icon` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `descri____` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |

### `Angra:maregrafo_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `version` | `xsd:int` | false | 1..1 |

### `Angra:marquise_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:massa_dagua_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `tipomassad` | `xsd:string` | true | 0..1 |
| `regime` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | false | 1..1 |

### `Angra:massa_dagua_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `tipomassad` | `xsd:string` | true | 0..1 |
| `regime` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |

### `Angra:microbacias`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `abrange` | `xsd:string` | true | 0..1 |
| `nome_bacia` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `Angra:monumentos_obeliscos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |

### `Angra:morro_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |

### `Angra:morro_urb_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |

### `Angra:muro_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `tipodelimfisica` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |

### `Angra:nascente_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |

### `Angra:nova_consulta_imobiliaria_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `lote_id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `id_consulta` | `xsd:int` | true | 0..1 |
| `ci_id` | `xsd:string` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `area_construida_anuncio` | `xsd:int` | true | 0..1 |
| `area_terreno_anuncio` | `xsd:int` | true | 0..1 |
| `valor_imovel` | `xsd:int` | true | 0..1 |
| `area_terreno` | `xsd:string` | true | 0..1 |
| `area_construida` | `xsd:decimal` | true | 0..1 |
| `valor_construcao` | `xsd:decimal` | true | 0..1 |
| `valor_terreno` | `xsd:decimal` | true | 0..1 |
| `valor_m2_terreno` | `xsd:decimal` | true | 0..1 |
| `vut` | `xsd:int` | true | 0..1 |
| `topografia` | `xsd:string` | true | 0..1 |
| `pedologia` | `xsd:string` | true | 0..1 |
| `situacaoquadra` | `xsd:string` | true | 0..1 |
| `acessopraia` | `xsd:string` | true | 0..1 |
| `acessoescadaria` | `xsd:string` | true | 0..1 |
| `ilha` | `xsd:string` | true | 0..1 |
| `limitacao` | `xsd:string` | true | 0..1 |
| `url` | `xsd:string` | true | 0..1 |
| `telefone` | `xsd:decimal` | true | 0..1 |
| `data` | `xsd:string` | true | 0..1 |
| `geocod` | `xsd:int` | true | 0..1 |
| `logradouro_id` | `xsd:int` | true | 0..1 |

### `Angra:nova_consulta_imobiliaria_p_vut`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `lote_id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `id_consulta` | `xsd:int` | true | 0..1 |
| `ci_id` | `xsd:string` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `area_construida_anuncio` | `xsd:int` | true | 0..1 |
| `area_terreno_anuncio` | `xsd:int` | true | 0..1 |
| `valor_imovel` | `xsd:int` | true | 0..1 |
| `area_terreno` | `xsd:string` | true | 0..1 |
| `area_construida` | `xsd:decimal` | true | 0..1 |
| `valor_construcao` | `xsd:decimal` | true | 0..1 |
| `valor_terreno` | `xsd:decimal` | true | 0..1 |
| `valor_m2_terreno` | `xsd:decimal` | true | 0..1 |
| `vut` | `xsd:int` | true | 0..1 |
| `topografia` | `xsd:string` | true | 0..1 |
| `pedologia` | `xsd:string` | true | 0..1 |
| `situacaoquadra` | `xsd:string` | true | 0..1 |
| `acessopraia` | `xsd:string` | true | 0..1 |
| `acessoescadaria` | `xsd:string` | true | 0..1 |
| `ilha` | `xsd:string` | true | 0..1 |
| `limitacao` | `xsd:string` | true | 0..1 |
| `url` | `xsd:string` | true | 0..1 |
| `telefone` | `xsd:decimal` | true | 0..1 |
| `data` | `xsd:string` | true | 0..1 |
| `geocod` | `xsd:int` | true | 0..1 |
| `logradouro_id` | `xsd:int` | true | 0..1 |

### `Angra:oceano_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome` | `xsd:string` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `id` | `xsd:int` | false | 1..1 |

### `Angra:oceano_urb_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome` | `xsd:string` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `id` | `xsd:int` | false | 1..1 |

### `Angra:ocorrencias`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `qt.` | `xsd:string` | true | 0..1 |
| `ro` | `xsd:string` | true | 0..1 |
| `bairro` | `xsd:string` | true | 0..1 |
| `endereço` | `xsd:string` | true | 0..1 |
| `solicitant` | `xsd:string` | true | 0..1 |
| `data` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:string` | true | 0..1 |
| `longitude` | `xsd:string` | true | 0..1 |
| `24 horas` | `xsd:string` | true | 0..1 |
| `motivo` | `xsd:string` | true | 0..1 |
| `técnico` | `xsd:string` | true | 0..1 |
| `observaç�` | `xsd:string` | true | 0..1 |
| `risco` | `xsd:string` | true | 0..1 |
| `estação` | `xsd:string` | true | 0..1 |

### `Angra:outras_entidades_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |

### `Angra:outras_entidades_publicas_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |

### `Angra:palmeira_urb_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:parada_onibus_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `descricao` | `xsd:string` | true | 0..1 |
| `linha` | `xsd:string` | true | 0..1 |
| `bairro` | `xsd:string` | true | 0..1 |
| `referencia` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:string` | true | 0..1 |
| `via` | `xsd:string` | true | 0..1 |
| `codigo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `cod_topovision` | `xsd:int` | true | 0..1 |

### `Angra:parada_onibus_urb_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `bairro` | `xsd:string` | true | 0..1 |
| `abrigo` | `xsd:string` | true | 0..1 |

### `Angra:parque_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |

### `Angra:parque_natural_centro`

> [!warning] Schema pendente
> Este esquema ainda não foi resolvido nesta coleta. Reconsulte o endpoint antes de usar a camada.


### `Angra:parque_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |

### `Angra:passagem_elevada_viaduto_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `modaluso` | `xsd:string` | true | 0..1 |
| `matconstr` | `xsd:string` | true | 0..1 |
| `operaciona` | `xsd:string` | true | 0..1 |
| `situacaofi` | `xsd:string` | true | 0..1 |
| `tipopavime` | `xsd:string` | true | 0..1 |
| `tipopassag` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:passarela_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `situacaofi` | `xsd:string` | true | 0..1 |
| `tipotraves` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:pasto_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |

### `Angra:pesca_artesanal`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `geom_old` | `gml:GeometryPropertyType` | true | 0..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `Angra:pesca_artesanal_p`

> [!warning] Schema pendente
> Este esquema ainda não foi resolvido nesta coleta. Reconsulte o endpoint antes de usar a camada.


### `Angra:piamb2010_19`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `ano` | `xsd:long` | true | 0..1 |
| `piamb` | `xsd:string` | true | 0..1 |
| `auto` | `xsd:string` | true | 0..1 |
| `fiscal` | `xsd:string` | true | 0..1 |
| `data` | `xsd:string` | true | 0..1 |
| `autuado` | `xsd:string` | true | 0..1 |
| `assunto` | `xsd:string` | true | 0..1 |
| `endereço` | `xsd:string` | true | 0..1 |
| `bairro` | `xsd:string` | true | 0..1 |
| `coord_x` | `xsd:decimal` | true | 0..1 |
| `coord_y` | `xsd:decimal` | true | 0..1 |
| `c` | `xsd:string` | true | 0..1 |
| `n` | `xsd:string` | true | 0..1 |
| `e` | `xsd:string` | true | 0..1 |
| `inti` | `xsd:string` | true | 0..1 |
| `interd` | `xsd:string` | true | 0..1 |
| `prz` | `xsd:string` | true | 0..1 |
| `venc_a` | `xsd:string` | true | 0..1 |
| `r_t` | `xsd:string` | true | 0..1 |
| `a_inf` | `xsd:string` | true | 0..1 |
| `venc_i` | `xsd:string` | true | 0..1 |
| `valor` | `xsd:string` | true | 0..1 |
| `pag` | `xsd:string` | true | 0..1 |

### `Angra:pier_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:piscina_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `situacaofi` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:pista_ponto_pouso_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipopista` | `xsd:string` | true | 0..1 |
| `revestimen` | `xsd:string` | true | 0..1 |
| `situacaofi` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |

### `Angra:pista_ponto_pouso_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipopista` | `xsd:string` | true | 0..1 |
| `revestimen` | `xsd:string` | true | 0..1 |
| `situacaofi` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |

### `Angra:plataforma_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:pluviometro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `bairro_id` | `xsd:long` | true | 0..1 |
| `cep` | `xsd:int` | true | 0..1 |
| `ddd_contato` | `xsd:int` | true | 0..1 |
| `email_contato` | `xsd:string` | true | 0..1 |
| `fone_contato` | `xsd:int` | true | 0..1 |
| `id_datalogger` | `xsd:string` | true | 0..1 |
| `instalado` | `xsd:boolean` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `local` | `xsd:string` | true | 0..1 |
| `logradouro_id` | `xsd:long` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `nome_contato` | `xsd:string` | true | 0..1 |
| `numero_endereco` | `xsd:string` | true | 0..1 |
| `numero_pluviometro` | `xsd:int` | false | 1..1 |
| `observacoes` | `xsd:string` | true | 0..1 |
| `orgao_responsavel` | `xsd:string` | true | 0..1 |
| `patrimonio` | `xsd:int` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nome_pluviometro` | `xsd:string` | true | 0..1 |

### `Angra:pluviometros_unificados`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `tabela_original` | `xsd:string` | true | 0..1 |

### `Angra:poco_artesiano`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `poco` | `xsd:string` | true | 0..1 |
| `regional` | `xsd:string` | true | 0..1 |
| `bomba` | `xsd:string` | true | 0..1 |
| `profundidade` | `xsd:long` | true | 0..1 |
| `vazao_m` | `xsd:decimal` | true | 0..1 |
| `vazao_l` | `xsd:decimal` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `version` | `xsd:int` | false | 1..1 |
| `imagem` | `xsd:hexBinary` | true | 0..1 |

### `Angra:pontal_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |

### `Angra:pontal_urb_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |

### `Angra:ponte_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipoponte` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |
| `matconstr` | `xsd:string` | true | 0..1 |

### `Angra:ponte_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `matconstr` | `xsd:string` | true | 0..1 |
| `tipoponte` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:ponto_cotado_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geometriaaproximada` | `xsd:string` | true | 0..1 |
| `cota` | `xsd:float` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `Angra:ponto_cotado_urb_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geometriaaproximada` | `xsd:string` | true | 0..1 |
| `cota` | `xsd:float` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `Angra:pontos_notaveis_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |

### `Angra:pontos_notaveis_urb_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | false | 1..1 |

### `Angra:poste_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `tipoposte` | `xsd:string` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:praca_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `local` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:praia_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:praia_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |

### `Angra:praia_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:processo_interno_urb`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `adesivo_embargo` | `xsd:string` | true | 0..1 |
| `adesivo_interdicao` | `xsd:string` | true | 0..1 |
| `adesivo_notificacao` | `xsd:string` | true | 0..1 |
| `adesivo_notificacao_ambiental` | `xsd:string` | true | 0..1 |
| `alvara_construcao` | `xsd:string` | true | 0..1 |
| `auto_constacacao_ambiental` | `xsd:string` | true | 0..1 |
| `auto_embargo` | `xsd:string` | true | 0..1 |
| `auto_infracao` | `xsd:string` | true | 0..1 |
| `bairro_id` | `xsd:long` | true | 0..1 |
| `certidao_regularidade_ambiental` | `xsd:string` | true | 0..1 |
| `complemento` | `xsd:string` | true | 0..1 |
| `cpf_cnpj_co_responsavel` | `xsd:string` | true | 0..1 |
| `cpf_cnpj_responsavel` | `xsd:string` | true | 0..1 |
| `data_demolicao` | `xsd:dateTime` | true | 0..1 |
| `defesa_notificacao` | `xsd:string` | true | 0..1 |
| `demolido` | `xsd:string` | true | 0..1 |
| `descricao` | `xsd:string` | true | 0..1 |
| `descricao_outros` | `xsd:string` | true | 0..1 |
| `fiscal` | `xsd:string` | true | 0..1 |
| `habitese` | `xsd:string` | true | 0..1 |
| `interd` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `licenciamento_ambiental` | `xsd:string` | true | 0..1 |
| `logradouro_id` | `xsd:long` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `matricula_rg` | `xsd:string` | true | 0..1 |
| `multa` | `xsd:string` | true | 0..1 |
| `nome_co_responsavel` | `xsd:string` | true | 0..1 |
| `nome_responsavel` | `xsd:string` | true | 0..1 |
| `notificacao` | `xsd:string` | true | 0..1 |
| `numero` | `xsd:string` | true | 0..1 |
| `numero_pi` | `xsd:string` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `oficio_orgao_externo` | `xsd:string` | true | 0..1 |
| `outro_processo` | `xsd:string` | true | 0..1 |
| `pi_amb_id` | `xsd:long` | true | 0..1 |
| `processo_externo` | `xsd:string` | true | 0..1 |
| `processo_judicial` | `xsd:string` | true | 0..1 |
| `processo_licenciamento` | `xsd:string` | true | 0..1 |
| `pror_prazo` | `xsd:string` | true | 0..1 |
| `termo_apreensao` | `xsd:string` | true | 0..1 |
| `tipo_intervencao` | `xsd:string` | true | 0..1 |
| `valor_multa` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `Angra:processos_silo`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `numero_requerimento` | `xsd:string` | true | 0..1 |
| `numero_protocolo_requerimento` | `xsd:string` | true | 0..1 |
| `protocolo_vinculado` | `xsd:string` | true | 0..1 |
| `area_terreno_obra` | `xsd:string` | true | 0..1 |
| `tipo_imovel` | `xsd:string` | true | 0..1 |
| `uso_imovel` | `xsd:string` | true | 0..1 |
| `logradouro_imovel` | `xsd:string` | true | 0..1 |
| `numero_imovel` | `xsd:string` | true | 0..1 |
| `complemento_imovel` | `xsd:string` | true | 0..1 |
| `cep_imovel` | `xsd:string` | true | 0..1 |
| `bairro_imovel` | `xsd:string` | true | 0..1 |
| `referencia` | `xsd:string` | true | 0..1 |
| `inscricao_imovel_iptu` | `xsd:string` | true | 0..1 |
| `art_obra` | `xsd:string` | true | 0..1 |
| `rrt_obra` | `xsd:string` | true | 0..1 |
| `coordenadas_localização_mapa` | `xsd:string` | true | 0..1 |
| `data_finalização` | `xsd:string` | true | 0..1 |
| `data_envio` | `xsd:string` | true | 0..1 |
| `proprietarias_nome` | `xsd:string` | true | 0..1 |
| `proprietarios_cpf_cnpj` | `xsd:string` | true | 0..1 |
| `resp_tecnicos_nome` | `xsd:string` | true | 0..1 |
| `resp_tecnicos_cpf_cnpj` | `xsd:string` | true | 0..1 |
| `resp_tecnicos_cau_crea` | `xsd:string` | true | 0..1 |
| `autores_projeto_nome` | `xsd:string` | true | 0..1 |
| `autores_projeto_cpf_cnpj` | `xsd:string` | true | 0..1 |
| `autores_projeto_cau_crea` | `xsd:string` | true | 0..1 |
| `y` | `xsd:string` | true | 0..1 |
| `x` | `xsd:string` | true | 0..1 |

### `Angra:produtores_origem_animal`

> [!warning] Schema pendente
> Este esquema ainda não foi resolvido nesta coleta. Reconsulte o endpoint antes de usar a camada.


### `Angra:produtores_origem_animal_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom_old` | `gml:PointPropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `version` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `Angra:produtores_rurais`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `version` | `xsd:int` | true | 0..1 |
| `lat` | `xsd:double` | true | 0..1 |
| `lon` | `xsd:double` | true | 0..1 |
| `geom_old` | `gml:PointPropertyType` | true | 0..1 |
| `descriptio` | `xsd:string` | true | 0..1 |
| `mandioca` | `xsd:string` | true | 0..1 |
| `banana` | `xsd:string` | true | 0..1 |
| `milho` | `xsd:string` | true | 0..1 |
| `palmito` | `xsd:string` | true | 0..1 |
| `bovinos` | `xsd:string` | true | 0..1 |
| `aves` | `xsd:string` | true | 0..1 |
| `coco` | `xsd:string` | true | 0..1 |
| `leite` | `xsd:string` | true | 0..1 |
| `piscicult` | `xsd:string` | true | 0..1 |
| `queijo` | `xsd:string` | true | 0..1 |
| `frut nativ` | `xsd:string` | true | 0..1 |
| `frut. out` | `xsd:string` | true | 0..1 |
| `cana` | `xsd:string` | true | 0..1 |
| `feijão` | `xsd:string` | true | 0..1 |
| `pupunha` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `out. criac` | `xsd:string` | true | 0..1 |
| `olericola` | `xsd:string` | true | 0..1 |
| `suino` | `xsd:string` | true | 0..1 |
| `cafe` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `Angra:produtores_rurais_p`

> [!warning] Schema pendente
> Este esquema ainda não foi resolvido nesta coleta. Reconsulte o endpoint antes de usar a camada.


### `Angra:quadra`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `bairro_id` | `xsd:long` | true | 0..1 |
| `quadra` | `xsd:int` | true | 0..1 |
| `setor_id` | `xsd:long` | true | 0..1 |
| `total_lotes` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `inscricao_topocart` | `xsd:string` | true | 0..1 |
| `dthr_atualizacao` | `xsd:dateTime` | false | 1..1 |
| `quadra_atual` | `xsd:int` | true | 0..1 |

### `Angra:quadra_esporte_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipocampoquadra` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |
| `situacaofisica` | `xsd:string` | true | 0..1 |
| `operacional` | `xsd:string` | true | 0..1 |

### `Angra:quadra_esporte_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipocampoquadra` | `xsd:string` | true | 0..1 |
| `id` | `xsd:string` | true | 0..1 |
| `situacaofisica` | `xsd:string` | true | 0..1 |
| `operacional` | `xsd:long` | true | 0..1 |

### `Angra:quadra_pq_visual_siga`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `quadra` | `xsd:int` | true | 0..1 |

### `Angra:radar_meteorologico_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `version` | `xsd:int` | false | 1..1 |

### `Angra:rampa`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |

### `Angra:rede_agua`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:decimal` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `diametro` | `xsd:string` | true | 0..1 |
| `material` | `xsd:string` | true | 0..1 |
| `extensao` | `xsd:decimal` | true | 0..1 |
| `profundidade` | `xsd:decimal` | true | 0..1 |
| `localizacao` | `xsd:string` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `version` | `xsd:int` | false | 1..1 |

### `Angra:rede_geodesica_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `este` | `xsd:string` | true | 0..1 |
| `sigmae` | `xsd:string` | true | 0..1 |
| `norte` | `xsd:string` | true | 0..1 |
| `sigman` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:string` | true | 0..1 |
| `longitude` | `xsd:string` | true | 0..1 |
| `alt_geomet` | `xsd:string` | true | 0..1 |
| `sigmah` | `xsd:string` | true | 0..1 |
| `alt_ortome` | `xsd:string` | true | 0..1 |

### `Angra:renda_ibge_2010_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cd_geocodi` | `xsd:string` | true | 0..1 |
| `cod_setor` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `cod_municipio` | `xsd:string` | true | 0..1 |
| `nome_do_municipio` | `xsd:string` | true | 0..1 |
| `cod_distrito` | `xsd:string` | true | 0..1 |
| `nome_do_distrito` | `xsd:string` | true | 0..1 |
| `cod_subdistrito` | `xsd:string` | true | 0..1 |
| `nome_do_subdistrito` | `xsd:string` | true | 0..1 |
| `cod_bairro` | `xsd:string` | true | 0..1 |
| `nome_do_bairro` | `xsd:string` | true | 0..1 |
| `domicilios` | `xsd:double` | true | 0..1 |
| `moradores` | `xsd:double` | true | 0..1 |
| `media_moradores` | `xsd:double` | true | 0..1 |
| `variancia_moradores` | `xsd:double` | true | 0..1 |
| `situacao_setor` | `xsd:string` | true | 0..1 |
| `tipo_setor` | `xsd:string` | true | 0..1 |
| `rendimento_mensal` | `xsd:double` | true | 0..1 |
| `varianca_rendimento` | `xsd:double` | true | 0..1 |

### `Angra:reservatorio`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `regional` | `xsd:string` | true | 0..1 |
| `cota` | `xsd:long` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `volume` | `xsd:long` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `reservatorio` | `xsd:string` | true | 0..1 |
| `version` | `xsd:int` | false | 1..1 |
| `imagem` | `xsd:hexBinary` | true | 0..1 |

### `Angra:restinga_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |

### `Angra:rio_intermitente_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `tipotrecho` | `xsd:string` | true | 0..1 |
| `encoberto` | `xsd:string` | true | 0..1 |
| `regime` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |

### `Angra:rio_perene_i`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `tipotrecho` | `xsd:string` | true | 0..1 |
| `encoberto` | `xsd:string` | true | 0..1 |
| `regime` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |

### `Angra:rio_perene_ii`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipomassad` | `xsd:string` | true | 0..1 |
| `tipotrecho` | `xsd:string` | true | 0..1 |
| `regime` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |

### `Angra:rio_perene_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `tipotrecho` | `xsd:string` | true | 0..1 |
| `encoberto` | `xsd:string` | true | 0..1 |
| `regime` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |

### `Angra:risco_coppe`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `fid_area_u` | `xsd:int` | true | 0..1 |
| `fid_setore` | `xsd:int` | true | 0..1 |
| `geo_codigo` | `xsd:string` | true | 0..1 |
| `fid_area_1` | `xsd:int` | true | 0..1 |
| `legenda_1` | `xsd:string` | true | 0..1 |
| `area_urb` | `xsd:string` | true | 0..1 |
| `area_urb10` | `xsd:double` | true | 0..1 |
| `domicilios` | `xsd:int` | true | 0..1 |
| `pessoas` | `xsd:string` | true | 0..1 |
| `area_setor` | `xsd:double` | true | 0..1 |
| `area_sc10` | `xsd:double` | true | 0..1 |
| `dom_10` | `xsd:string` | true | 0..1 |
| `pess_10` | `xsd:double` | true | 0..1 |
| `dens_pop10` | `xsd:double` | true | 0..1 |
| `c_denpop10` | `xsd:string` | true | 0..1 |
| `fid_suscet` | `xsd:int` | true | 0..1 |
| `susc` | `xsd:string` | true | 0..1 |
| `area_risco` | `xsd:double` | true | 0..1 |
| `pop_risco` | `xsd:double` | true | 0..1 |
| `dom_risco` | `xsd:string` | true | 0..1 |
| `susc_final` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `domicilio` | `xsd:string` | true | 0..1 |
| `ar_urb_10` | `xsd:string` | true | 0..1 |
| `pessoas_10` | `xsd:string` | true | 0..1 |
| `sc_10_ha` | `xsd:double` | true | 0..1 |
| `dens_pop` | `xsd:double` | true | 0..1 |
| `pop_risc` | `xsd:int` | true | 0..1 |
| `area_risc` | `xsd:double` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `join_code` | `xsd:int` | true | 0..1 |
| `id_1` | `xsd:long` | true | 0..1 |
| `cd_geocodi` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nm_bairro` | `xsd:string` | true | 0..1 |
| `n_pessoas` | `xsd:double` | true | 0..1 |
| `n_domic` | `xsd:double` | true | 0..1 |
| `pess_dom` | `xsd:double` | true | 0..1 |
| `ha_urb_set` | `xsd:double` | true | 0..1 |
| `haurbset10` | `xsd:double` | true | 0..1 |
| `urb10_urb` | `xsd:double` | true | 0..1 |
| `clasdenpop` | `xsd:string` | true | 0..1 |
| `ha_risco` | `xsd:double` | true | 0..1 |
| `riscourb10` | `xsd:double` | true | 0..1 |
| `pop_urb10` | `xsd:double` | true | 0..1 |
| `dom_urb10` | `xsd:double` | true | 0..1 |
| `risco` | `xsd:string` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `path` | `xsd:string` | true | 0..1 |

### `Angra:risco_cprm_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `descriptio` | `xsd:string` | true | 0..1 |
| `name_2` | `xsd:string` | true | 0..1 |
| `descript_2` | `xsd:string` | true | 0..1 |

### `Angra:risco_drm`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `Unidade` | `xsd:string` | true | 0..1 |
| `Sigla` | `xsd:string` | true | 0..1 |
| `Area_km2` | `xsd:double` | true | 0..1 |
| `Forma` | `xsd:string` | true | 0..1 |
| `Decliv` | `xsd:string` | true | 0..1 |
| `Potencial` | `xsd:string` | true | 0..1 |

### `Angra:ruina_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `layer` | `xsd:string` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `Angra:secao`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `bairro_id` | `xsd:long` | true | 0..1 |
| `cep` | `xsd:int` | true | 0..1 |
| `codigo` | `xsd:int` | true | 0..1 |
| `coleta_lixo` | `xsd:boolean` | false | 1..1 |
| `comprimento` | `xsd:decimal` | true | 0..1 |
| `frequencia_coleta` | `xsd:int` | true | 0..1 |
| `iluminacao` | `xsd:boolean` | false | 1..1 |
| `largura_fim` | `xsd:decimal` | true | 0..1 |
| `largura_inicio` | `xsd:decimal` | true | 0..1 |
| `largura_meio` | `xsd:decimal` | true | 0..1 |
| `limpeza` | `xsd:boolean` | false | 1..1 |
| `logradouro_id` | `xsd:long` | false | 1..1 |
| `pavimento` | `xsd:string` | true | 0..1 |
| `setor_id` | `xsd:long` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `vut_antigo` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `largura_media` | `xsd:decimal` | true | 0..1 |
| `dthr_atualizacao` | `xsd:dateTime` | false | 1..1 |
| `id_lei` | `xsd:short` | true | 0..1 |
| `conferido` | `xsd:short` | true | 0..1 |
| `vut_2024` | `xsd:decimal` | true | 0..1 |
| `tipo_old` | `xsd:string` | true | 0..1 |
| `trecho_tributario` | `xsd:int` | true | 0..1 |
| `logradouro_id_old` | `xsd:long` | true | 0..1 |

### `Angra:sensores_de_umidade_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `version` | `xsd:int` | false | 1..1 |

### `Angra:sepulcrario`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `endereco` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `Angra:serra_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |

### `Angra:serra_urb_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |

### `Angra:setor`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `numero` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `distrito_id` | `xsd:int` | true | 0..1 |
| `inscricao_topocart` | `xsd:string` | true | 0..1 |

### `Angra:sirene`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom_old` | `gml:GeometryPropertyType` | true | 0..1 |
| `tabela_original` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `version` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `Angra:spa_saude_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `endereco` | `xsd:string` | true | 0..1 |
| `bairro` | `xsd:string` | true | 0..1 |
| `telefone` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `version` | `xsd:int` | false | 1..1 |

### `Angra:subestacao_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:subestacao_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |

### `Angra:sumidouro_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `tiposumvert` | `xsd:string` | false | 1..1 |
| `geometriaaproximada` | `xsd:string` | false | 1..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `Angra:tampao`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `diametro` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `imagem` | `xsd:hexBinary` | true | 0..1 |
| `version` | `xsd:int` | true | 0..1 |

### `Angra:tb_bcl_l_angra`

> [!warning] Schema pendente
> Este esquema ainda não foi resolvido nesta coleta. Reconsulte o endpoint antes de usar a camada.


### `Angra:tb_edificacao_a_angra_cadastro`

> [!warning] Schema pendente
> Este esquema ainda não foi resolvido nesta coleta. Reconsulte o endpoint antes de usar a camada.


### `Angra:tb_quadra_a_angra_cadastro`

> [!warning] Schema pendente
> Este esquema ainda não foi resolvido nesta coleta. Reconsulte o endpoint antes de usar a camada.


### `Angra:terreno_erodido_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |

### `Angra:terreno_erodido_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:terreno_exposto_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |

### `Angra:terreno_exposto_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `layer` | `xsd:string` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `Angra:topo_morro_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `Angra:torre_comunic_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:torre_comunicacao_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:torre_energia_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | false | 1..1 |

### `Angra:torre_energia_urb_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:torres_comunicacao_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |

### `Angra:travessia_pedrestre_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `situacaofi` | `xsd:string` | true | 0..1 |
| `tipotraves` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:trecho_arruamento_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `revestimen` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:trecho_arruamento_interno_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:trecho_arruamento_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `nome_log` | `xsd:string` | true | 0..1 |
| `tipo_log` | `xsd:string` | true | 0..1 |
| `tipo_pav` | `xsd:string` | true | 0..1 |
| `nome_log_p` | `xsd:string` | true | 0..1 |
| `jurisdicao` | `xsd:string` | true | 0..1 |

### `Angra:trecho_arruamento_urb_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |

### `Angra:trecho_drenagem_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `tipotrecho` | `xsd:string` | true | 0..1 |
| `encoberto` | `xsd:string` | true | 0..1 |
| `regime` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:trecho_drenagem_urb_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `tipotrecho` | `xsd:string` | true | 0..1 |
| `encoberto` | `xsd:string` | true | 0..1 |
| `regime` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:trecho_energia_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `especie` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:trecho_massa_dagua_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipomassad` | `xsd:string` | true | 0..1 |
| `tipotrecho` | `xsd:string` | true | 0..1 |
| `regime` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |

### `Angra:trecho_massa_dagua_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipomassad` | `xsd:string` | true | 0..1 |
| `tipotrecho` | `xsd:string` | true | 0..1 |
| `regime` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:treinam_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `nome_prop` | `xsd:string` | true | 0..1 |

### `Angra:tubulacao_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `layer` | `xsd:string` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `Angra:tunel_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:uni_cons_area_preservacao_ambiental`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom_old` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `descriptio` | `xsd:string` | true | 0..1 |
| `timestamp` | `xsd:string` | true | 0..1 |
| `begin` | `xsd:string` | true | 0..1 |
| `end` | `xsd:string` | true | 0..1 |
| `altitudemo` | `xsd:string` | true | 0..1 |
| `tessellate` | `xsd:long` | true | 0..1 |
| `extrude` | `xsd:long` | true | 0..1 |
| `visibility` | `xsd:long` | true | 0..1 |
| `draworder` | `xsd:long` | true | 0..1 |
| `icon` | `xsd:string` | true | 0..1 |
| `descri____` | `xsd:string` | true | 0..1 |
| `nome_uc` | `xsd:string` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `esfera` | `xsd:string` | true | 0..1 |
| `ano_cria` | `xsd:string` | true | 0..1 |
| `ato_legal` | `xsd:string` | true | 0..1 |
| `nome_org` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `Angra:uni_cons_area_relevante_int_eco_cataguases`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom_old` | `gml:SurfacePropertyType` | true | 0..1 |
| `timestamp` | `xsd:dateTime` | true | 0..1 |
| `begin` | `xsd:dateTime` | true | 0..1 |
| `end` | `xsd:dateTime` | true | 0..1 |
| `altitudemode` | `xsd:string` | true | 0..1 |
| `tessellate` | `xsd:int` | true | 0..1 |
| `extrude` | `xsd:int` | true | 0..1 |
| `visibility` | `xsd:int` | true | 0..1 |
| `draworder` | `xsd:int` | true | 0..1 |
| `icon` | `xsd:string` | true | 0..1 |
| `descri____o` | `xsd:string` | true | 0..1 |
| `nome_uc` | `xsd:string` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `esfera` | `xsd:string` | true | 0..1 |
| `ano_cria` | `xsd:string` | true | 0..1 |
| `ato_legal` | `xsd:string` | true | 0..1 |
| `nome_org` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `Angra:uni_cons_est_ecologica_tamoios`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom_old` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `timestamp` | `xsd:dateTime` | true | 0..1 |
| `begin` | `xsd:dateTime` | true | 0..1 |
| `end` | `xsd:dateTime` | true | 0..1 |
| `altitudemode` | `xsd:string` | true | 0..1 |
| `tessellate` | `xsd:int` | true | 0..1 |
| `extrude` | `xsd:int` | true | 0..1 |
| `visibility` | `xsd:int` | true | 0..1 |
| `draworder` | `xsd:int` | true | 0..1 |
| `icon` | `xsd:string` | true | 0..1 |
| `descri____o` | `xsd:string` | true | 0..1 |
| `nome_uc` | `xsd:string` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `esfera` | `xsd:string` | true | 0..1 |
| `ano_cria` | `xsd:string` | true | 0..1 |
| `ato_legal` | `xsd:string` | true | 0..1 |
| `nome_org` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `Angra:uni_cons_limite_municipal`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `timestamp` | `xsd:dateTime` | true | 0..1 |
| `begin` | `xsd:dateTime` | true | 0..1 |
| `end` | `xsd:dateTime` | true | 0..1 |
| `altitudemode` | `xsd:string` | true | 0..1 |
| `tessellate` | `xsd:int` | true | 0..1 |
| `extrude` | `xsd:int` | true | 0..1 |
| `visibility` | `xsd:int` | true | 0..1 |
| `draworder` | `xsd:int` | true | 0..1 |
| `icon` | `xsd:string` | true | 0..1 |
| `descri____o` | `xsd:string` | true | 0..1 |
| `cd_geocodm` | `xsd:string` | true | 0..1 |
| `nm_municip` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `geom_old` | `gml:GeometryPropertyType` | true | 0..1 |
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |

### `Angra:uni_cons_parques_ambientais`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom_old` | `gml:SurfacePropertyType` | true | 0..1 |
| `timestamp` | `xsd:dateTime` | true | 0..1 |
| `begin` | `xsd:dateTime` | true | 0..1 |
| `end` | `xsd:dateTime` | true | 0..1 |
| `altitudemode` | `xsd:string` | true | 0..1 |
| `tessellate` | `xsd:int` | true | 0..1 |
| `extrude` | `xsd:int` | true | 0..1 |
| `visibility` | `xsd:int` | true | 0..1 |
| `draworder` | `xsd:int` | true | 0..1 |
| `icon` | `xsd:string` | true | 0..1 |
| `descri____o` | `xsd:string` | true | 0..1 |
| `nome_uc` | `xsd:string` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `esfera` | `xsd:string` | true | 0..1 |
| `ano_cria` | `xsd:string` | true | 0..1 |
| `ato_legal` | `xsd:string` | true | 0..1 |
| `nome_org` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `Angra:uni_cons_reservas_ambientais`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom_old` | `gml:SurfacePropertyType` | true | 0..1 |
| `timestamp` | `xsd:dateTime` | true | 0..1 |
| `begin` | `xsd:dateTime` | true | 0..1 |
| `end` | `xsd:dateTime` | true | 0..1 |
| `altitudemode` | `xsd:string` | true | 0..1 |
| `tessellate` | `xsd:int` | true | 0..1 |
| `extrude` | `xsd:int` | true | 0..1 |
| `visibility` | `xsd:int` | true | 0..1 |
| `draworder` | `xsd:int` | true | 0..1 |
| `icon` | `xsd:string` | true | 0..1 |
| `descri____o` | `xsd:string` | true | 0..1 |
| `nome_uc` | `xsd:string` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `esfera` | `xsd:string` | true | 0..1 |
| `ano_cria` | `xsd:string` | true | 0..1 |
| `ato_legal` | `xsd:string` | true | 0..1 |
| `nome_org` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `Angra:unidade_new`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `Angra:unidades`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `lote_id` | `xsd:long` | true | 0..1 |
| `logradouro` | `xsd:long` | true | 0..1 |
| `bairro` | `xsd:string` | true | 0..1 |
| `nome_logra` | `xsd:string` | true | 0..1 |
| `numero` | `xsd:string` | true | 0..1 |
| `complement` | `xsd:string` | true | 0..1 |
| `condominio` | `xsd:string` | true | 0..1 |
| `utilizacao` | `xsd:string` | true | 0..1 |
| `sitacaouni` | `xsd:string` | true | 0..1 |
| `ocupacao` | `xsd:string` | true | 0..1 |
| `situacaoed` | `xsd:string` | true | 0..1 |
| `revestimen` | `xsd:string` | true | 0..1 |

### `Angra:unidades_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |
| `lote_id` | `xsd:long` | true | 0..1 |
| `logradouro` | `xsd:long` | true | 0..1 |
| `bairro` | `xsd:string` | true | 0..1 |
| `nome_logra` | `xsd:string` | true | 0..1 |
| `numero` | `xsd:string` | true | 0..1 |
| `complement` | `xsd:string` | true | 0..1 |
| `condominio` | `xsd:string` | true | 0..1 |
| `utilizacao` | `xsd:string` | true | 0..1 |
| `sitacaouni` | `xsd:string` | true | 0..1 |
| `ocupacao` | `xsd:string` | true | 0..1 |
| `situacaoed` | `xsd:string` | true | 0..1 |
| `revestimen` | `xsd:string` | true | 0..1 |

### `Angra:usuario_assistencia_social`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `codigo_familia` | `xsd:long` | false | 1..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `Angra:vaga_estacionamento`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `idoso` | `xsd:boolean` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `pdc` | `xsd:boolean` | true | 0..1 |
| `tipo` | `xsd:string` | false | 1..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `Angra:vagas_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `vaga` | `xsd:string` | true | 0..1 |
| `logradouro` | `xsd:string` | true | 0..1 |
| `numero` | `xsd:string` | true | 0..1 |
| `bairro` | `xsd:string` | true | 0..1 |
| `referencia` | `xsd:string` | true | 0..1 |

### `Angra:vala_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `situacaofi` | `xsd:string` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:vala_urb_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `situacaofi` | `xsd:string` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:valvula`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `descricao` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `imagem` | `xsd:hexBinary` | true | 0..1 |

### `Angra:vegetacao_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | false | 1..1 |

### `Angra:vegetacao_cultivada_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |

### `Angra:vegetacao_rasteira_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |

### `Angra:vegetacao_urb_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |

### `Angra:vw_foto_fachada`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `id_lote` | `xsd:int` | true | 0..1 |

### `Angra:vw_foto_fachada_unidade`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `foto_fachada_id` | `xsd:long` | true | 0..1 |
| `bairro` | `xsd:string` | true | 0..1 |
| `numero` | `xsd:string` | true | 0..1 |
| `complemento` | `xsd:string` | true | 0..1 |
| `cep` | `xsd:string` | true | 0..1 |
| `imagem` | `xsd:hexBinary` | true | 0..1 |

### `Angra:vw_foto_fachada_unidade_new`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `id_id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `foto_fachada_id` | `xsd:long` | true | 0..1 |
| `bairro` | `xsd:string` | true | 0..1 |
| `numero` | `xsd:string` | true | 0..1 |
| `complemento` | `xsd:string` | true | 0..1 |
| `cep` | `xsd:string` | true | 0..1 |
| `foto2` | `xsd:string` | true | 0..1 |
| `link` | `xsd:string` | true | 0..1 |

### `Angra:vw_secao_logradouro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `logradouro_id` | `xsd:long` | true | 0..1 |
| `codigo_logradouro` | `xsd:int` | true | 0..1 |
| `nome_logradouro` | `xsd:string` | true | 0..1 |

### `Angra:zon_apatamoios_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `bases` | `xsd:string` | true | 0..1 |
| `nome_ilha` | `xsd:string` | true | 0..1 |
| `zonaapa` | `xsd:string` | true | 0..1 |
| `subzonaapa` | `xsd:string` | true | 0..1 |
| `praia` | `xsd:string` | true | 0..1 |
| `alteracoes` | `xsd:string` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `porc` | `xsd:double` | true | 0..1 |

### `Angra:zoneamento_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:string` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `Name` | `xsd:string` | true | 0..1 |
| `descriptio` | `xsd:string` | true | 0..1 |
| `timestamp` | `xsd:string` | true | 0..1 |
| `begin` | `xsd:string` | true | 0..1 |
| `end` | `xsd:string` | true | 0..1 |
| `altitudeMo` | `xsd:string` | true | 0..1 |
| `tessellate` | `xsd:long` | true | 0..1 |
| `extrude` | `xsd:long` | true | 0..1 |
| `visibility` | `xsd:long` | true | 0..1 |
| `drawOrder` | `xsd:long` | true | 0..1 |
| `icon` | `xsd:string` | true | 0..1 |
| `ZONA` | `xsd:string` | true | 0..1 |
| `MACROZONEA` | `xsd:string` | true | 0..1 |
| `UT` | `xsd:string` | true | 0..1 |
| `COAP` | `xsd:string` | true | 0..1 |
| `TO` | `xsd:string` | true | 0..1 |
| `TP` | `xsd:string` | true | 0..1 |
| `PEUC` | `xsd:string` | true | 0..1 |
| `OODC_OGDC` | `xsd:string` | true | 0..1 |
| `TDC` | `xsd:string` | true | 0..1 |
| `CAM` | `xsd:string` | true | 0..1 |
| `AME_SEM` | `xsd:string` | true | 0..1 |
| `AME_COM` | `xsd:string` | true | 0..1 |
| `GBE` | `xsd:string` | true | 0..1 |
| `GME` | `xsd:string` | true | 0..1 |
| `AML` | `xsd:string` | true | 0..1 |
| `TML` | `xsd:string` | true | 0..1 |
| `CT` | `xsd:string` | true | 0..1 |

### `Angra:zoneamento_municipal`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `version` | `xsd:long` | false | 1..1 |
| `afastamento_frontal` | `xsd:string` | true | 0..1 |
| `altura_maxima` | `xsd:decimal` | false | 1..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `coeficiente_aprovado` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `legislacao` | `xsd:string` | true | 0..1 |
| `link_lei` | `xsd:string` | true | 0..1 |
| `local` | `xsd:string` | true | 0..1 |
| `localizacao` | `xsd:string` | true | 0..1 |
| `maximo_pavimentos` | `xsd:int` | false | 1..1 |
| `observacao` | `xsd:string` | true | 0..1 |
| `parcelamento` | `xsd:string` | true | 0..1 |
| `ponto_inicial` | `xsd:string` | true | 0..1 |
| `publicacao` | `xsd:string` | true | 0..1 |
| `taxa_ocupacao` | `xsd:string` | true | 0..1 |
| `unidade_te` | `xsd:string` | true | 0..1 |
| `usos` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `Angra:zpe_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `zpe` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |

### `Angra:zpe_usina_nuclear_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `timestamp` | `xsd:dateTime` | true | 0..1 |
| `begin` | `xsd:dateTime` | true | 0..1 |
| `end` | `xsd:dateTime` | true | 0..1 |
| `altitudemode` | `xsd:string` | true | 0..1 |
| `tessellate` | `xsd:int` | true | 0..1 |
| `extrude` | `xsd:int` | true | 0..1 |
| `visibility` | `xsd:int` | true | 0..1 |
| `draworder` | `xsd:int` | true | 0..1 |
| `icon` | `xsd:string` | true | 0..1 |
| `snippet` | `xsd:string` | true | 0..1 |
