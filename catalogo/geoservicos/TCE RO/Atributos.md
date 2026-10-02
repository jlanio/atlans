# TCE RO — atributos das camadas

Geoportal: [[Geosserviços/TCE RO/Tribunal de Contas do Estado de Rondônia — TCE-RO|Tribunal de Contas do Estado de Rondônia — TCE-RO]]

Os campos abaixo vêm de `DescribeFeatureType` (XSD), sem download de feições.

## politico_administrativo (2)

### `politico_administrativo:ibge_limite_estadual`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cd_uf` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `nm_regiao` | `xsd:string` | true | 0..1 |
| `area_km2` | `xsd:double` | true | 0..1 |

### `politico_administrativo:ibge_limite_municipal`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cd_mun` | `xsd:string` | true | 0..1 |
| `nm_mun` | `xsd:string` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `area_km2` | `xsd:double` | true | 0..1 |

## unidades_conservacao (1)

### `unidades_conservacao:sintese_uc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nome_uc` | `xsd:string` | true | 0..1 |
| `sigla` | `xsd:string` | true | 0..1 |
| `cod_cnuc` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `cria_ano` | `xsd:string` | true | 0..1 |
| `cria_ato` | `xsd:string` | true | 0..1 |
| `outro_ato` | `xsd:string` | true | 0..1 |
| `pl_manejo` | `xsd:string` | true | 0..1 |
| `co_gestor` | `xsd:string` | true | 0..1 |
| `quali_pol` | `xsd:string` | true | 0..1 |
| `grupo` | `xsd:string` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `cat_iucn` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `qtd_incr_desmat_2008_2023` | `xsd:int` | true | 0..1 |
| `area_ha_incr_desmat_2008_2023` | `xsd:double` | true | 0..1 |
| `qtd_alerta` | `xsd:int` | true | 0..1 |
| `qtd_area_emb_sedam` | `xsd:int` | true | 0..1 |
| `qtd_area_emb_ibama` | `xsd:int` | true | 0..1 |
| `qtd_area_emb_icmbio` | `xsd:int` | true | 0..1 |
| `qtd_auto_sedam` | `xsd:int` | true | 0..1 |
| `qtd_auto_ibama` | `xsd:int` | true | 0..1 |
| `qtd_car` | `xsd:int` | true | 0..1 |
| `qtd_cert_priv_sigef` | `xsd:int` | true | 0..1 |
| `qtd_cert_pub_sigef` | `xsd:int` | true | 0..1 |
| `qtd_cert_priv_snci` | `xsd:int` | true | 0..1 |
| `qtd_cert_pub_snci` | `xsd:int` | true | 0..1 |
| `qtd_pmfs_sedam` | `xsd:int` | true | 0..1 |
| `area_ha_car` | `xsd:double` | true | 0..1 |
| `percent_area_car` | `xsd:double` | true | 0..1 |
| `area_sigef_priv` | `xsd:double` | true | 0..1 |
| `area_sigef_pub` | `xsd:double` | true | 0..1 |
| `area_snci_priv` | `xsd:double` | true | 0..1 |
| `area_snci_pub` | `xsd:double` | true | 0..1 |
| `percent_area_sigef_priv` | `xsd:double` | true | 0..1 |
| `percent_area_sigef_pub` | `xsd:double` | true | 0..1 |
| `percent_area_snci_priv` | `xsd:double` | true | 0..1 |
| `percent_area_snci_pub` | `xsd:double` | true | 0..1 |
| `data_criacao` | `xsd:date` | true | 0..1 |
| `ano_criacao` | `xsd:int` | true | 0..1 |
| `contribuicao` | `xsd:double` | true | 0..1 |
| `percent_incr_desmat_2008_2023` | `xsd:double` | true | 0..1 |
| `percent_alerta_aut` | `xsd:double` | true | 0..1 |
| `percent_2022_2021` | `xsd:double` | true | 0..1 |
| `qtd_auto_icmbio` | `xsd:int` | true | 0..1 |
| `percent_2023_2022` | `xsd:double` | true | 0..1 |
| `qtd_incr_desmat_2007` | `xsd:int` | true | 0..1 |
| `municipio_abrange` | `xsd:string` | true | 0..1 |
| `quant_turismo` | `xsd:int` | true | 0..1 |
| `quant_serviços_amb` | `xsd:int` | true | 0..1 |
| `pmfs_uc` | `xsd:string` | true | 0..1 |
| `bacias_hidro` | `xsd:string` | true | 0..1 |
| `qtd_rios` | `xsd:long` | true | 0..1 |
| `qtd_nascentes` | `xsd:long` | true | 0..1 |
| `area_ha_agro` | `xsd:double` | true | 0..1 |
| `percent_area_agro` | `xsd:double` | true | 0..1 |
| `area_desmat_2007_2023` | `xsd:double` | true | 0..1 |
| `media_desmat_2008_2023` | `xsd:double` | true | 0..1 |
| `perc_desmat_2007_2023` | `xsd:double` | true | 0..1 |
| `ranking_desmat` | `xsd:int` | true | 0..1 |
| `cicatriz_2024` | `xsd:double` | true | 0..1 |
| `co_gestor_ato` | `xsd:string` | true | 0..1 |
