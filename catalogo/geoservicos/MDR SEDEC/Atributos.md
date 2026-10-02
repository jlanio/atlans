# MDR SEDEC — atributos das camadas

Geoportal: [[Geosserviços/MDR SEDEC/Secretaria Nacional de Proteção e Defesa Civil — MDR—SEDEC|Secretaria Nacional de Proteção e Defesa Civil — MDR/SEDEC]]

Os campos abaixo vêm de `DescribeFeatureType` (XSD), sem download de feições.

## atlas (8)

### `atlas:afetados_geo_hidro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `fid` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geocodigo` | `xsd:int` | true | 0..1 |
| `afetados_geo_hidro` | `xsd:int` | true | 0..1 |

### `atlas:indicadores`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geocodigo` | `xsd:int` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `codigo` | `xsd:int` | true | 0..1 |
| `populacao` | `xsd:int` | true | 0..1 |
| `pib_2019` | `xsd:double` | true | 0..1 |
| `capacitados` | `xsd:int` | true | 0..1 |
| `entes` | `xsd:int` | true | 0..1 |
| `a_2020` | `xsd:int` | true | 0..1 |
| `a_2021` | `xsd:int` | true | 0..1 |
| `a_2022` | `xsd:int` | true | 0..1 |
| `a_2023` | `xsd:int` | true | 0..1 |
| `entes_2019` | `xsd:int` | true | 0..1 |
| `entes_2020` | `xsd:int` | true | 0..1 |
| `entes_2021` | `xsd:int` | true | 0..1 |
| `entes_2022` | `xsd:int` | true | 0..1 |
| `entes_2023` | `xsd:int` | true | 0..1 |
| `a2b1_eq` | `xsd:double` | true | 0..1 |
| `a1` | `xsd:double` | true | 0..1 |
| `a2` | `xsd:double` | true | 0..1 |
| `a3` | `xsd:double` | true | 0..1 |
| `b1` | `xsd:double` | true | 0..1 |
| `b2` | `xsd:double` | true | 0..1 |
| `b3` | `xsd:double` | true | 0..1 |
| `c1` | `xsd:double` | true | 0..1 |
| `c2` | `xsd:double` | true | 0..1 |
| `c3` | `xsd:double` | true | 0..1 |
| `c4` | `xsd:double` | true | 0..1 |
| `c5` | `xsd:double` | true | 0..1 |
| `c6` | `xsd:double` | true | 0..1 |
| `obitos` | `xsd:int` | true | 0..1 |
| `feridos` | `xsd:int` | true | 0..1 |
| `enfermos` | `xsd:int` | true | 0..1 |
| `desabrigados` | `xsd:int` | true | 0..1 |
| `desalojados` | `xsd:int` | true | 0..1 |
| `desaparecidos` | `xsd:int` | true | 0..1 |
| `outros` | `xsd:int` | true | 0..1 |
| `saude_dest` | `xsd:int` | true | 0..1 |
| `saude_danif` | `xsd:int` | true | 0..1 |
| `saude_valor` | `xsd:double` | true | 0..1 |
| `ensino_dest` | `xsd:int` | true | 0..1 |
| `ensino_danif` | `xsd:int` | true | 0..1 |
| `ensino_valor` | `xsd:double` | true | 0..1 |
| `outros_dest` | `xsd:int` | true | 0..1 |
| `outros_danif` | `xsd:int` | true | 0..1 |
| `outros_valor` | `xsd:double` | true | 0..1 |
| `comuni_dest` | `xsd:int` | true | 0..1 |
| `comuni_danif` | `xsd:int` | true | 0..1 |
| `comuni_valor` | `xsd:double` | true | 0..1 |
| `hab_dest` | `xsd:int` | true | 0..1 |
| `hab_danif` | `xsd:int` | true | 0..1 |
| `hab_valor` | `xsd:double` | true | 0..1 |
| `infra_dest` | `xsd:int` | true | 0..1 |
| `infra_danif` | `xsd:int` | true | 0..1 |
| `infra_valor` | `xsd:double` | true | 0..1 |
| `agricultura` | `xsd:double` | true | 0..1 |
| `pecuaria` | `xsd:double` | true | 0..1 |
| `industria` | `xsd:double` | true | 0..1 |
| `servicos` | `xsd:double` | true | 0..1 |
| `total_privado` | `xsd:double` | true | 0..1 |
| `saude` | `xsd:double` | true | 0..1 |
| `agua` | `xsd:double` | true | 0..1 |
| `esgoto` | `xsd:double` | true | 0..1 |
| `limpeza` | `xsd:double` | true | 0..1 |
| `pragas` | `xsd:double` | true | 0..1 |
| `energia` | `xsd:double` | true | 0..1 |
| `telecom` | `xsd:double` | true | 0..1 |
| `transportes` | `xsd:double` | true | 0..1 |
| `combustiveis` | `xsd:double` | true | 0..1 |
| `seguranca` | `xsd:double` | true | 0..1 |
| `ensino` | `xsd:double` | true | 0..1 |
| `total_publico` | `xsd:double` | true | 0..1 |
| `total_danos_materiais` | `xsd:double` | true | 0..1 |

### `atlas:obitos_geo_hidro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `fid` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geocodigo` | `xsd:int` | true | 0..1 |
| `obitos_geo_hidro` | `xsd:int` | true | 0..1 |

### `atlas:pop_r3_geo_hidro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `fid` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geocodigo` | `xsd:int` | true | 0..1 |
| `pop_r3_geo_hidro` | `xsd:int` | true | 0..1 |

### `atlas:pop_r4_geo_hidro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `fid` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geocodigo` | `xsd:int` | true | 0..1 |
| `pop_r4_geo_hidro` | `xsd:int` | true | 0..1 |

### `atlas:pop_total_r3_r4_geo_hidro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `fid` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geocodigo` | `xsd:int` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `pop_total_risco_geo_hidro` | `xsd:int` | true | 0..1 |

### `atlas:reconhecimentos_geo-hidro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `fid` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geocodigo` | `xsd:int` | true | 0..1 |
| `rec_geo_hidro` | `xsd:int` | true | 0..1 |

### `atlas:total_de_reconhecimentos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `fid` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geocodigo` | `xsd:int` | true | 0..1 |
| `reconhecimentos` | `xsd:int` | true | 0..1 |

## s2id (6)

### `s2id:municipios_semiarido`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `CD_GEO` | `xsd:int` | true | 0..1 |
| `NM_MUNICIPIO` | `xsd:string` | true | 0..1 |
| `MP_GEORREFERENCIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `s2id:Portal_OCP_Mapa2_Mun_Sem_seca_e_est_rec_vigente`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `CD_GEO` | `xsd:int` | true | 0..1 |
| `NM_MUNICIPIO` | `xsd:string` | true | 0..1 |
| `SG_UF` | `xsd:string` | true | 0..1 |
| `DT_OCORRENCIA` | `xsd:dateTime` | true | 0..1 |
| `TIPO_COBRADE` | `xsd:string` | true | 0..1 |
| `DS_COBRADE` | `xsd:string` | true | 0..1 |
| `NOME_DECRETO` | `xsd:string` | true | 0..1 |
| `NUMERO_DECRETO` | `xsd:string` | true | 0..1 |
| `DT_ENVIO_DECRETO` | `xsd:dateTime` | true | 0..1 |
| `DT_VIG` | `xsd:dateTime` | true | 0..1 |
| `NOME_PORTARIA` | `xsd:string` | true | 0..1 |
| `DT_DOU` | `xsd:dateTime` | true | 0..1 |
| `NR_DOU` | `xsd:string` | true | 0..1 |
| `MP_GEORREFERENCIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `s2id:Portal_OCP_Mapa3_timeline_rec`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `CD_GEO` | `xsd:decimal` | true | 0..1 |
| `ID_MUNICIPIO` | `xsd:decimal` | true | 0..1 |
| `NM_MUNICIPIO` | `xsd:string` | true | 0..1 |
| `SG_UF` | `xsd:string` | true | 0..1 |
| `TIPO_COBRADE` | `xsd:string` | true | 0..1 |
| `NUMERO_DECRETO` | `xsd:string` | true | 0..1 |
| `DT_ENVIO_DECRETO` | `xsd:dateTime` | true | 0..1 |
| `DT_VIG` | `xsd:dateTime` | true | 0..1 |
| `DT_DOU` | `xsd:dateTime` | true | 0..1 |
| `NR_DOU` | `xsd:string` | true | 0..1 |
| `MP_GEORREFERENCIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `s2id:vw_ponto_teste_setor`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distancia_metros` | `xsd:double` | true | 0..1 |
| `cd_setor` | `xsd:long` | true | 0..1 |
| `nm_mun_s` | `xsd:string` | true | 0..1 |
| `nm_bairro` | `xsd:string` | true | 0..1 |
| `id_ponto_proximo` | `xsd:int` | true | 0..1 |
| `nome_ponto_proximo` | `xsd:string` | true | 0..1 |
| `alerta_30m` | `xsd:string` | true | 0..1 |

### `s2id:vw_setor_ponto_teste`

> [!warning] Schema pendente
> Este esquema ainda não foi resolvido nesta coleta. Reconsulte o endpoint antes de usar a camada.


### `s2id:vw_setores_guara`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_exclusivo` | `xsd:int` | true | 0..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `cd_setor` | `xsd:long` | true | 0..1 |
| `cd_setor_n` | `xsd:long` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `cd_sit` | `xsd:int` | true | 0..1 |
| `cd_tipo` | `xsd:string` | true | 0..1 |
| `cd_regiao` | `xsd:int` | true | 0..1 |
| `nm_regiao` | `xsd:string` | true | 0..1 |
| `cd_uf` | `xsd:int` | true | 0..1 |
| `nm_uf_s` | `xsd:string` | true | 0..1 |
| `cd_mun_s` | `xsd:int` | true | 0..1 |
| `nm_mun_s` | `xsd:string` | true | 0..1 |
| `cd_dist` | `xsd:long` | true | 0..1 |
| `nm_dist` | `xsd:string` | true | 0..1 |
| `cd_subdist` | `xsd:long` | true | 0..1 |
| `nm_subdist` | `xsd:string` | true | 0..1 |
| `cd_bairro` | `xsd:string` | true | 0..1 |
| `nm_bairro` | `xsd:string` | true | 0..1 |
| `cd_nu` | `xsd:long` | true | 0..1 |
| `nm_nu` | `xsd:string` | true | 0..1 |
| `cd_fcu` | `xsd:long` | true | 0..1 |
| `nm_fcu` | `xsd:string` | true | 0..1 |
| `cd_aglom` | `xsd:long` | true | 0..1 |
| `nm_aglom` | `xsd:string` | true | 0..1 |
| `cd_rgint` | `xsd:int` | true | 0..1 |
| `nm_rgint` | `xsd:string` | true | 0..1 |
| `cd_rgi` | `xsd:int` | true | 0..1 |
| `nm_rgi` | `xsd:string` | true | 0..1 |
| `cd_concurb` | `xsd:long` | true | 0..1 |
| `nm_concurb` | `xsd:string` | true | 0..1 |
| `area_km2` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

## s2id4.0 (8)

### `s2id4.0:mv_municipios_brazil`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `cd_mun` | `xsd:long` | false | 1..1 |
| `nm_mun` | `xsd:string` | false | 1..1 |
| `cd_uf` | `xsd:int` | false | 1..1 |
| `sigla_uf` | `xsd:string` | false | 1..1 |
| `nm_uf` | `xsd:string` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `s2id4.0:mv_setores_trabalho`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_exclusivo` | `xsd:int` | true | 0..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `cd_setor` | `xsd:long` | true | 0..1 |
| `cd_setor_n` | `xsd:long` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `cd_sit` | `xsd:int` | true | 0..1 |
| `cd_tipo` | `xsd:string` | true | 0..1 |
| `cd_regiao` | `xsd:int` | true | 0..1 |
| `nm_regiao` | `xsd:string` | true | 0..1 |
| `cd_uf` | `xsd:int` | true | 0..1 |
| `nm_uf_s` | `xsd:string` | true | 0..1 |
| `cd_mun_s` | `xsd:int` | true | 0..1 |
| `nm_mun_s` | `xsd:string` | true | 0..1 |
| `cd_dist` | `xsd:long` | true | 0..1 |
| `nm_dist` | `xsd:string` | true | 0..1 |
| `cd_subdist` | `xsd:long` | true | 0..1 |
| `nm_subdist` | `xsd:string` | true | 0..1 |
| `cd_bairro` | `xsd:string` | true | 0..1 |
| `nm_bairro` | `xsd:string` | true | 0..1 |
| `cd_nu` | `xsd:long` | true | 0..1 |
| `nm_nu` | `xsd:string` | true | 0..1 |
| `cd_fcu` | `xsd:long` | true | 0..1 |
| `nm_fcu` | `xsd:string` | true | 0..1 |
| `cd_aglom` | `xsd:long` | true | 0..1 |
| `nm_aglom` | `xsd:string` | true | 0..1 |
| `cd_rgint` | `xsd:int` | true | 0..1 |
| `nm_rgint` | `xsd:string` | true | 0..1 |
| `cd_rgi` | `xsd:int` | true | 0..1 |
| `nm_rgi` | `xsd:string` | true | 0..1 |
| `cd_concurb` | `xsd:long` | true | 0..1 |
| `nm_concurb` | `xsd:string` | true | 0..1 |
| `area_km2` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `s2id4.0:vw_alertas_cemaden_vigente`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:string` | true | 0..1 |
| `id_alerta` | `xsd:int` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |
| `id_evento` | `xsd:long` | true | 0..1 |
| `cd_municipio_ibge` | `xsd:long` | true | 0..1 |
| `nivel_descricao` | `xsd:string` | true | 0..1 |
| `nivel_cor` | `xsd:string` | true | 0..1 |
| `data_inicio` | `xsd:dateTime` | true | 0..1 |
| `data_expiracao` | `xsd:dateTime` | true | 0..1 |
| `is_vigente` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `s2id4.0:vw_alertas_cemaden_vigente_centroid`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:string` | true | 0..1 |
| `id_alerta` | `xsd:int` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |
| `identificador_base` | `xsd:string` | true | 0..1 |
| `versao` | `xsd:int` | true | 0..1 |
| `id_evento` | `xsd:long` | true | 0..1 |
| `nivel_descricao` | `xsd:string` | true | 0..1 |
| `nivel_cor` | `xsd:string` | true | 0..1 |
| `data_inicio` | `xsd:dateTime` | true | 0..1 |
| `data_expiracao` | `xsd:dateTime` | true | 0..1 |
| `status_codigo` | `xsd:int` | true | 0..1 |
| `status_descricao` | `xsd:string` | true | 0..1 |
| `cd_municipio_ibge` | `xsd:long` | true | 0..1 |
| `is_vigente` | `xsd:string` | true | 0..1 |
| `cemaden_centroid` | `gml:PointPropertyType` | true | 0..1 |

### `s2id4.0:vw_alertas_inmet_pontos_uf`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_ponto` | `xsd:int` | true | 0..1 |
| `id_alerta` | `xsd:int` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |
| `identificador_base` | `xsd:string` | true | 0..1 |
| `versao` | `xsd:int` | true | 0..1 |
| `cd_uf` | `xsd:int` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `nivel_descricao` | `xsd:string` | true | 0..1 |
| `nivel_cor` | `xsd:string` | true | 0..1 |
| `prioridade` | `xsd:int` | true | 0..1 |
| `total_alertas` | `xsd:long` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `s2id4.0:vw_alertas_inmet_vigente`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `instituicao_sigla` | `xsd:string` | true | 0..1 |
| `id_alerta` | `xsd:int` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |
| `identificador_base` | `xsd:string` | true | 0..1 |
| `versao` | `xsd:int` | true | 0..1 |
| `categoria_nome` | `xsd:string` | true | 0..1 |
| `certeza_nivel` | `xsd:string` | true | 0..1 |
| `nivel_descricao` | `xsd:string` | true | 0..1 |
| `nivel_cor` | `xsd:string` | true | 0..1 |
| `prioridade` | `xsd:int` | true | 0..1 |
| `severidade_nome` | `xsd:string` | true | 0..1 |
| `severidade_info` | `xsd:string` | true | 0..1 |
| `desastre_titulo` | `xsd:string` | true | 0..1 |
| `desastre_codigo` | `xsd:string` | true | 0..1 |
| `data_inicio` | `xsd:dateTime` | true | 0..1 |
| `data_expiracao` | `xsd:dateTime` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `status_codigo` | `xsd:int` | true | 0..1 |
| `id_evento` | `xsd:long` | true | 0..1 |

### `s2id4.0:vw_alertas_inmet_vigente_centroid`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | true | 0..1 |
| `instituicao_sigla` | `xsd:string` | true | 0..1 |
| `id_alerta` | `xsd:int` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |
| `identificador_base` | `xsd:string` | true | 0..1 |
| `versao` | `xsd:int` | true | 0..1 |
| `categoria_nome` | `xsd:string` | true | 0..1 |
| `certeza_nivel` | `xsd:string` | true | 0..1 |
| `nivel_descricao` | `xsd:string` | true | 0..1 |
| `nivel_cor` | `xsd:string` | true | 0..1 |
| `prioridade` | `xsd:int` | true | 0..1 |
| `severidade_nome` | `xsd:string` | true | 0..1 |
| `severidade_info` | `xsd:string` | true | 0..1 |
| `desastre_titulo` | `xsd:string` | true | 0..1 |
| `desastre_codigo` | `xsd:string` | true | 0..1 |
| `data_inicio` | `xsd:dateTime` | true | 0..1 |
| `data_expiracao` | `xsd:dateTime` | true | 0..1 |
| `status_codigo` | `xsd:int` | true | 0..1 |
| `geom_poligono` | `gml:GeometryPropertyType` | true | 0..1 |
| `cor_ponto` | `xsd:string` | true | 0..1 |
| `inmet_centroid` | `gml:GeometryPropertyType` | true | 0..1 |
| `id_evento` | `xsd:long` | true | 0..1 |

### `s2id4.0:vw_alertas_sgb_vigente`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:string` | true | 0..1 |
| `id_estacao` | `xsd:long` | true | 0..1 |
| `sigla_pm` | `xsd:string` | true | 0..1 |
| `nome_estacao` | `xsd:string` | true | 0..1 |
| `id_bacia` | `xsd:long` | true | 0..1 |
| `nome_bacia` | `xsd:string` | true | 0..1 |
| `bacia` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:decimal` | true | 0..1 |
| `longitude` | `xsd:decimal` | true | 0..1 |
| `id_monitoramento` | `xsd:long` | true | 0..1 |
| `id_status` | `xsd:long` | true | 0..1 |
| `status_estacao` | `xsd:string` | true | 0..1 |
| `cor_estacao` | `xsd:string` | true | 0..1 |
| `gravidade_estacao` | `xsd:int` | true | 0..1 |
| `cota` | `xsd:decimal` | true | 0..1 |
| `data_leitura` | `xsd:dateTime` | true | 0..1 |
| `id_alerta` | `xsd:int` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |
| `identificador_base` | `xsd:string` | true | 0..1 |
| `versao` | `xsd:int` | true | 0..1 |
| `possui_alerta` | `xsd:boolean` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
