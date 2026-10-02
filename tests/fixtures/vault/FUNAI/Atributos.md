# FUNAI — atributos das camadas

Geoportal: [[Geosserviços/FUNAI/Fundação Nacional dos Povos Indígenas — FUNAI|Fundação Nacional dos Povos Indígenas — FUNAI]]

Os campos abaixo vêm de `DescribeFeatureType` (XSD), sem download de feições.

## Funai (8)

### `Funai:aldeias_pontos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `cod_aldeia` | `xsd:int` | true | 0..1 |
| `nome_aldeia` | `xsd:string` | true | 0..1 |
| `cod_ti` | `xsd:int` | true | 0..1 |
| `cod_municipio` | `xsd:int` | true | 0..1 |
| `data_cadastro` | `xsd:string` | true | 0..1 |
| `flag_ativo` | `xsd:string` | true | 0..1 |
| `nome_cr` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:PointPropertyType` | true | 0..1 |
| `nommunic` | `xsd:string` | true | 0..1 |
| `nomuf` | `xsd:string` | true | 0..1 |
| `undadm_codigo` | `xsd:long` | true | 0..1 |
| `coord_lat` | `xsd:double` | true | 0..1 |
| `coord_long` | `xsd:double` | true | 0..1 |

### `Funai:tis_amazonia_legal_poligonais`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `terrai_codigo` | `xsd:int` | true | 0..1 |
| `terrai_nome` | `xsd:string` | true | 0..1 |
| `etnia_nome` | `xsd:string` | true | 0..1 |
| `municipio_nome` | `xsd:string` | true | 0..1 |
| `uf_sigla` | `xsd:string` | true | 0..1 |
| `superficie_perimetro_ha` | `xsd:double` | true | 0..1 |
| `fase_ti` | `xsd:string` | true | 0..1 |
| `modalidade_ti` | `xsd:string` | true | 0..1 |
| `reestudo_ti` | `xsd:string` | true | 0..1 |
| `cr` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `undadm_codigo` | `xsd:long` | true | 0..1 |
| `undadm_nome` | `xsd:string` | true | 0..1 |
| `undadm_sigla` | `xsd:string` | true | 0..1 |

### `Funai:tis_cr`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `undadm_codigo` | `xsd:long` | true | 0..1 |
| `undadm_codigo_pai` | `xsd:long` | true | 0..1 |
| `undadm_sigla` | `xsd:string` | true | 0..1 |
| `undadm_nome` | `xsd:string` | true | 0..1 |
| `undadm_situacao` | `xsd:string` | true | 0..1 |
| `undadm_uf_sigla` | `xsd:string` | true | 0..1 |
| `mun_codigo_ibge` | `xsd:string` | true | 0..1 |
| `mun_nome` | `xsd:string` | true | 0..1 |
| `mun_uf_sigla` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:PointPropertyType` | true | 0..1 |

### `Funai:tis_ctl`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `undadm_codigo` | `xsd:long` | true | 0..1 |
| `undadm_codigo_pai` | `xsd:long` | true | 0..1 |
| `undadm_codigo_novo` | `xsd:long` | true | 0..1 |
| `undadm_codigo_pai_novo` | `xsd:long` | true | 0..1 |
| `undadm_sigla` | `xsd:string` | true | 0..1 |
| `undadm_nome` | `xsd:string` | true | 0..1 |
| `undadm_nome_pai` | `xsd:string` | true | 0..1 |
| `undadm_sigla_pai` | `xsd:string` | true | 0..1 |
| `undadm_situacao` | `xsd:string` | true | 0..1 |
| `undadm_logradouro` | `xsd:string` | true | 0..1 |
| `undadm_complemento` | `xsd:string` | true | 0..1 |
| `undadm_bairro` | `xsd:string` | true | 0..1 |
| `undadm_cep` | `xsd:string` | true | 0..1 |
| `undadm_email` | `xsd:string` | true | 0..1 |
| `undadm_uf_sigla` | `xsd:string` | true | 0..1 |
| `mun_codigo_ibge` | `xsd:string` | true | 0..1 |
| `muncoddv` | `xsd:int` | true | 0..1 |
| `the_geom` | `gml:PointPropertyType` | true | 0..1 |

### `Funai:tis_poligonais`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `terrai_codigo` | `xsd:int` | true | 0..1 |
| `terrai_nome` | `xsd:string` | true | 0..1 |
| `etnia_nome` | `xsd:string` | true | 0..1 |
| `municipio_nome` | `xsd:string` | true | 0..1 |
| `uf_sigla` | `xsd:string` | true | 0..1 |
| `superficie_perimetro_ha` | `xsd:double` | true | 0..1 |
| `fase_ti` | `xsd:string` | true | 0..1 |
| `modalidade_ti` | `xsd:string` | true | 0..1 |
| `reestudo_ti` | `xsd:string` | true | 0..1 |
| `cr` | `xsd:string` | true | 0..1 |
| `faixa_fronteira` | `xsd:string` | true | 0..1 |
| `undadm_codigo` | `xsd:long` | true | 0..1 |
| `undadm_nome` | `xsd:string` | true | 0..1 |
| `undadm_sigla` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `dominio_uniao` | `xsd:string` | true | 0..1 |
| `data_atualizacao` | `xsd:string` | true | 0..1 |
| `epsg` | `xsd:int` | true | 0..1 |

### `Funai:tis_poligonais_portarias`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `terrai_codigo` | `xsd:int` | true | 0..1 |
| `terrai_nome` | `xsd:string` | true | 0..1 |
| `etnia_nome` | `xsd:string` | true | 0..1 |
| `municipio_nome` | `xsd:string` | true | 0..1 |
| `uf_sigla` | `xsd:string` | true | 0..1 |
| `superficie_perimetro_ha` | `xsd:double` | true | 0..1 |
| `fase_ti` | `xsd:string` | true | 0..1 |
| `modalidade_ti` | `xsd:string` | true | 0..1 |
| `reestudo_ti` | `xsd:string` | true | 0..1 |
| `cr` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `faixa_fronteira` | `xsd:string` | true | 0..1 |
| `data_em_estudo` | `xsd:date` | true | 0..1 |
| `tit_em_estudo` | `xsd:string` | true | 0..1 |
| `data_delimitada` | `xsd:date` | true | 0..1 |
| `tit_delimitada` | `xsd:string` | true | 0..1 |
| `data_declarada` | `xsd:date` | true | 0..1 |
| `tit_declarada` | `xsd:string` | true | 0..1 |
| `data_homologada` | `xsd:date` | true | 0..1 |
| `tit_homologada` | `xsd:string` | true | 0..1 |
| `data_regularizada` | `xsd:date` | true | 0..1 |
| `tit_regularizada` | `xsd:string` | true | 0..1 |
| `res_em_estudo` | `xsd:string` | true | 0..1 |
| `res_delimitada` | `xsd:string` | true | 0..1 |
| `res_declarada` | `xsd:string` | true | 0..1 |
| `res_homologada` | `xsd:string` | true | 0..1 |
| `res_regularizada` | `xsd:string` | true | 0..1 |
| `undadm_codigo` | `xsd:long` | true | 0..1 |
| `undadm_nome` | `xsd:string` | true | 0..1 |
| `undadm_sigla` | `xsd:string` | true | 0..1 |

### `Funai:tis_pontos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |
| `terrai_nome` | `xsd:string` | true | 0..1 |
| `etnia_nome` | `xsd:string` | true | 0..1 |
| `municipio_nome` | `xsd:string` | true | 0..1 |
| `uf_sigla` | `xsd:string` | true | 0..1 |
| `superficie_perimetro_ha` | `xsd:double` | true | 0..1 |
| `fase_ti` | `xsd:string` | true | 0..1 |
| `modalidade_ti` | `xsd:string` | true | 0..1 |
| `reestudo_ti` | `xsd:string` | true | 0..1 |
| `superficie_ti` | `xsd:string` | true | 0..1 |
| `terrai_codigo` | `xsd:int` | true | 0..1 |
| `the_geom` | `gml:PointPropertyType` | true | 0..1 |
| `undadm_codigo` | `xsd:long` | true | 0..1 |
| `undadm_nome` | `xsd:string` | true | 0..1 |
| `undadm_sigla` | `xsd:string` | true | 0..1 |

### `Funai:tis_pontos_portarias`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `terrai_nome` | `xsd:string` | true | 0..1 |
| `etnia_nome` | `xsd:string` | true | 0..1 |
| `municipio_nome` | `xsd:string` | true | 0..1 |
| `uf_sigla` | `xsd:string` | true | 0..1 |
| `superficie_perimetro_ha` | `xsd:double` | true | 0..1 |
| `fase_ti` | `xsd:string` | true | 0..1 |
| `modalidade_ti` | `xsd:string` | true | 0..1 |
| `reestudo_ti` | `xsd:string` | true | 0..1 |
| `superficie_ti` | `xsd:string` | true | 0..1 |
| `terrai_codigo` | `xsd:int` | true | 0..1 |
| `the_geom` | `gml:PointPropertyType` | true | 0..1 |
| `faixa_fronteira` | `xsd:string` | true | 0..1 |
| `data_em_estudo` | `xsd:date` | true | 0..1 |
| `tit_em_estudo` | `xsd:string` | true | 0..1 |
| `data_delimitada` | `xsd:date` | true | 0..1 |
| `tit_delimitada` | `xsd:string` | true | 0..1 |
| `data_declarada` | `xsd:date` | true | 0..1 |
| `tit_declarada` | `xsd:string` | true | 0..1 |
| `data_homologada` | `xsd:date` | true | 0..1 |
| `tit_homologada` | `xsd:string` | true | 0..1 |
| `data_regularizada` | `xsd:date` | true | 0..1 |
| `tit_regularizada` | `xsd:string` | true | 0..1 |
| `res_em_estudo` | `xsd:string` | true | 0..1 |
| `res_delimitada` | `xsd:string` | true | 0..1 |
| `res_declarada` | `xsd:string` | true | 0..1 |
| `res_homologada` | `xsd:string` | true | 0..1 |
| `res_regularizada` | `xsd:string` | true | 0..1 |
| `undadm_codigo` | `xsd:long` | true | 0..1 |
| `undadm_nome` | `xsd:string` | true | 0..1 |
| `undadm_sigla` | `xsd:string` | true | 0..1 |
