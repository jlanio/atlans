# FUNAI CMR — atributos das camadas

Geoportal: [[Geosserviços/FUNAI CMR/Centro de Monitoramento Remoto da FUNAI — FUNAI—CMR|Centro de Monitoramento Remoto da FUNAI — FUNAI/CMR]]

Os campos abaixo vêm de `DescribeFeatureType` (XSD), sem download de feições.

## CMR-PUBLICO (50)

### `CMR-PUBLICO:hid_comites_de_bacias_estaduais_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nu_objectid` | `xsd:int` | true | 0..1 |
| `no_uf` | `xsd:string` | true | 0..1 |
| `sg_uf` | `xsd:string` | true | 0..1 |
| `nu_area_km2` | `xsd:double` | true | 0..1 |
| `no_cbe` | `xsd:string` | true | 0..1 |
| `cd_cbe` | `xsd:int` | true | 0..1 |
| `no_rhi` | `xsd:string` | true | 0..1 |
| `nu_cbe_ano_ref` | `xsd:double` | true | 0..1 |
| `dt_cbe_ano_ref` | `xsd:dateTime` | true | 0..1 |
| `dt_cadastro` | `xsd:dateTime` | true | 0..1 |
| `nu_piburb` | `xsd:long` | true | 0..1 |
| `nu_popurb2019` | `xsd:long` | true | 0..1 |
| `nu_poprur2019` | `xsd:long` | true | 0..1 |
| `nu_popuf` | `xsd:long` | true | 0..1 |
| `nu_pibuf` | `xsd:long` | true | 0..1 |
| `nu_area_ha` | `xsd:double` | true | 0..1 |

### `CMR-PUBLICO:hid_trecho_drenagem_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome` | `xsd:string` | true | 0..1 |
| `geometriaaproximada` | `xsd:string` | true | 0..1 |
| `tipotrechodrenagem` | `xsd:string` | true | 0..1 |
| `navegavel` | `xsd:string` | true | 0..1 |
| `larguramedia` | `xsd:float` | true | 0..1 |
| `regime` | `xsd:string` | true | 0..1 |
| `encoberto` | `xsd:string` | true | 0..1 |
| `geom` | `gml:CurvePropertyType` | true | 0..1 |

### `CMR-PUBLICO:hid_ugrh_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `no_nome` | `xsd:string` | true | 0..1 |
| `cod_ugrh` | `xsd:long` | true | 0..1 |
| `nu_area_ha` | `xsd:double` | true | 0..1 |
| `dt_cadastro` | `xsd:date` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |

### `CMR-PUBLICO:img_analise_consolidado_oneatlas_dissolvido_por_estagio_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `sg_uf` | `xsd:string` | true | 0..1 |
| `no_ti` | `xsd:string` | true | 0..1 |
| `co_funai` | `xsd:int` | true | 0..1 |
| `dt_homologada` | `xsd:string` | true | 0..1 |
| `ds_cr` | `xsd:string` | true | 0..1 |
| `nu_ano` | `xsd:int` | true | 0..1 |
| `no_estagio` | `xsd:string` | true | 0..1 |
| `no_satelites` | `xsd:string` | true | 0..1 |
| `nu_resolucoes` | `xsd:string` | true | 0..1 |
| `dt_imagens` | `xsd:string` | true | 0..1 |
| `nu_area_ha` | `xsd:decimal` | true | 0..1 |
| `nu_area_km2` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `dt_cadastro` | `xsd:dateTime` | true | 0..1 |
| `co_cr` | `xsd:long` | true | 0..1 |
| `nu_latitude` | `xsd:decimal` | true | 0..1 |
| `nu_longitude` | `xsd:decimal` | true | 0..1 |

### `CMR-PUBLICO:img_catalogo_landsat_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `image` | `xsd:string` | true | 0..1 |
| `path` | `xsd:string` | true | 0..1 |
| `url_tms` | `xsd:string` | true | 0..1 |
| `data` | `xsd:date` | true | 0..1 |
| `nuvens` | `xsd:double` | true | 0..1 |
| `quicklook` | `xsd:string` | true | 0..1 |
| `orbita` | `xsd:string` | true | 0..1 |
| `ponto` | `xsd:string` | true | 0..1 |
| `geom` | `gml:SurfacePropertyType` | false | 1..1 |
| `dt_cadastro` | `xsd:dateTime` | false | 1..1 |
| `preview` | `xsd:string` | true | 0..1 |

### `CMR-PUBLICO:img_catalogo_sentinel2_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `image` | `xsd:string` | false | 1..1 |
| `path` | `xsd:string` | false | 1..1 |
| `url_tms` | `xsd:string` | false | 1..1 |
| `utm_zone` | `xsd:int` | true | 0..1 |
| `latitude_band` | `xsd:string` | true | 0..1 |
| `grid_square` | `xsd:string` | true | 0..1 |
| `data` | `xsd:date` | false | 1..1 |
| `pr_date` | `xsd:date` | false | 1..1 |
| `cloud_cover` | `xsd:double` | true | 0..1 |
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |
| `dt_cadastro` | `xsd:dateTime` | false | 1..1 |
| `preview` | `xsd:string` | true | 0..1 |

### `CMR-PUBLICO:img_grade_landsat_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `path` | `xsd:int` | false | 1..1 |
| `row` | `xsd:int` | false | 1..1 |
| `orb_ponto` | `xsd:string` | false | 1..1 |
| `path_row` | `xsd:string` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | false | 1..1 |
| `dt_cadastro` | `xsd:dateTime` | false | 1..1 |

### `CMR-PUBLICO:img_grade_sentinel2_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ds_nome` | `xsd:string` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | false | 1..1 |
| `dt_cadastro` | `xsd:dateTime` | false | 1..1 |

### `CMR-PUBLICO:instrumento_gestao`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `no_ti` | `xsd:string` | true | 0..1 |
| `no_grupo_etnico` | `xsd:string` | true | 0..1 |
| `ds_fase_ti` | `xsd:string` | true | 0..1 |
| `ds_modalidade` | `xsd:string` | true | 0..1 |
| `ds_reestudo_ti` | `xsd:string` | true | 0..1 |
| `co_cr` | `xsd:long` | true | 0..1 |
| `ds_cr` | `xsd:string` | true | 0..1 |
| `no_municipio` | `xsd:string` | true | 0..1 |
| `sg_uf` | `xsd:string` | true | 0..1 |
| `nu_area_ha` | `xsd:double` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `dt_cadastro` | `xsd:dateTime` | true | 0..1 |
| `st_faixa_fronteira` | `xsd:string` | true | 0..1 |
| `dt_em_estudo` | `xsd:date` | true | 0..1 |
| `ds_portaria_em_estudo` | `xsd:string` | true | 0..1 |
| `dt_delimitada` | `xsd:date` | true | 0..1 |
| `ds_despacho_delimitada` | `xsd:string` | true | 0..1 |
| `dt_declarada` | `xsd:date` | true | 0..1 |
| `ds_portaria_declarada` | `xsd:string` | true | 0..1 |
| `dt_homologada` | `xsd:date` | true | 0..1 |
| `ds_decreto_homologada` | `xsd:string` | true | 0..1 |
| `dt_regularizada` | `xsd:date` | true | 0..1 |
| `ds_matricula_regularizada` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_em_estudo` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_delimitada` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_declarada` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_homologada` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_regularizada` | `xsd:string` | true | 0..1 |
| `possui_ig` | `xsd:boolean` | true | 0..1 |
| `ranking` | `xsd:long` | true | 0..1 |

### `CMR-PUBLICO:lim_amazonia_legal_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | false | 1..1 |
| `dt_cadastro` | `xsd:dateTime` | false | 1..1 |

### `CMR-PUBLICO:lim_assentamento_rural_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `cd_sipra` | `xsd:string` | true | 0..1 |
| `sg_modalidade` | `xsd:string` | true | 0..1 |
| `no_projeto` | `xsd:string` | true | 0..1 |
| `nu_fase` | `xsd:int` | true | 0..1 |
| `nu_capacidade` | `xsd:int` | true | 0..1 |
| `nu_beneficio` | `xsd:int` | true | 0..1 |
| `sg_uf` | `xsd:string` | true | 0..1 |
| `no_municipio` | `xsd:string` | true | 0..1 |
| `dt_criacao` | `xsd:date` | true | 0..1 |
| `nu_ano_criacao` | `xsd:short` | true | 0..1 |
| `nu_area_ref_incra` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `dt_cadastro` | `xsd:dateTime` | false | 1..1 |
| `ds_forma_obtencao` | `xsd:string` | true | 0..1 |
| `dt_obtencao` | `xsd:date` | true | 0..1 |
| `no_sr` | `xsd:string` | true | 0..1 |
| `ds_assentamento` | `xsd:string` | true | 0..1 |
| `nu_area_ha` | `xsd:double` | true | 0..1 |

### `CMR-PUBLICO:lim_assentamento_rural_ti_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `cd_sipra` | `xsd:string` | true | 0..1 |
| `sg_modalidade` | `xsd:string` | true | 0..1 |
| `no_projeto` | `xsd:string` | true | 0..1 |
| `nu_fase` | `xsd:int` | true | 0..1 |
| `nu_capacidade` | `xsd:int` | true | 0..1 |
| `nu_beneficio` | `xsd:int` | true | 0..1 |
| `sg_uf` | `xsd:string` | true | 0..1 |
| `no_municipio` | `xsd:string` | true | 0..1 |
| `dt_criacao` | `xsd:date` | true | 0..1 |
| `nu_ano_criacao` | `xsd:short` | true | 0..1 |
| `nu_area_ref_incra` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `dt_cadastro` | `xsd:dateTime` | true | 0..1 |
| `ds_forma_obtencao` | `xsd:string` | true | 0..1 |
| `dt_obtencao` | `xsd:date` | true | 0..1 |
| `no_sr` | `xsd:string` | true | 0..1 |
| `ds_assentamento` | `xsd:string` | true | 0..1 |
| `nu_area_ha` | `xsd:double` | true | 0..1 |
| `ds_cr` | `xsd:string` | true | 0..1 |
| `co_funai` | `xsd:int` | true | 0..1 |
| `no_ti` | `xsd:string` | true | 0..1 |
| `co_cr` | `xsd:long` | true | 0..1 |

### `CMR-PUBLICO:lim_buffer_10km_recorte_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nu_buffer_distancia` | `xsd:decimal` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | false | 1..1 |
| `dt_cadastro` | `xsd:dateTime` | false | 1..1 |

### `CMR-PUBLICO:lim_cnuc_2024_02_estadual_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `fid` | `xsd:int` | true | 0..1 |
| `gml_id` | `xsd:string` | true | 0..1 |
| `uc_id` | `xsd:string` | true | 0..1 |
| `cd_cnuc` | `xsd:string` | true | 0..1 |
| `wdpa_pid` | `xsd:string` | true | 0..1 |
| `nome_uc` | `xsd:string` | true | 0..1 |
| `cria_ano` | `xsd:string` | true | 0..1 |
| `cria_ato` | `xsd:string` | true | 0..1 |
| `outro_ato` | `xsd:string` | true | 0..1 |
| `pl_manejo` | `xsd:string` | true | 0..1 |
| `co_gestor` | `xsd:string` | true | 0..1 |
| `quali_pol` | `xsd:string` | true | 0..1 |
| `ppgr` | `xsd:string` | true | 0..1 |
| `ha_total` | `xsd:string` | true | 0..1 |
| `ha_ato` | `xsd:string` | true | 0..1 |
| `esfera` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `org_gestor` | `xsd:string` | true | 0..1 |
| `grupo` | `xsd:string` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `cat_iucn` | `xsd:string` | true | 0..1 |
| `amazonia` | `xsd:string` | true | 0..1 |
| `caatinga` | `xsd:string` | true | 0..1 |
| `cerrado` | `xsd:string` | true | 0..1 |
| `matlantica` | `xsd:string` | true | 0..1 |
| `pampa` | `xsd:string` | true | 0..1 |
| `pantanal` | `xsd:string` | true | 0..1 |
| `marinho` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `limite` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `nomeabrev` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `CMR-PUBLICO:lim_cnuc_2024_02_estadual_ti_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `fid` | `xsd:int` | true | 0..1 |
| `gml_id` | `xsd:string` | true | 0..1 |
| `uc_id` | `xsd:string` | true | 0..1 |
| `cd_cnuc` | `xsd:string` | true | 0..1 |
| `wdpa_pid` | `xsd:string` | true | 0..1 |
| `nome_uc` | `xsd:string` | true | 0..1 |
| `cria_ano` | `xsd:string` | true | 0..1 |
| `cria_ato` | `xsd:string` | true | 0..1 |
| `outro_ato` | `xsd:string` | true | 0..1 |
| `pl_manejo` | `xsd:string` | true | 0..1 |
| `co_gestor` | `xsd:string` | true | 0..1 |
| `quali_pol` | `xsd:string` | true | 0..1 |
| `ppgr` | `xsd:string` | true | 0..1 |
| `ha_total` | `xsd:string` | true | 0..1 |
| `ha_ato` | `xsd:string` | true | 0..1 |
| `esfera` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `org_gestor` | `xsd:string` | true | 0..1 |
| `grupo` | `xsd:string` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `cat_iucn` | `xsd:string` | true | 0..1 |
| `amazonia` | `xsd:string` | true | 0..1 |
| `caatinga` | `xsd:string` | true | 0..1 |
| `cerrado` | `xsd:string` | true | 0..1 |
| `matlantica` | `xsd:string` | true | 0..1 |
| `pampa` | `xsd:string` | true | 0..1 |
| `pantanal` | `xsd:string` | true | 0..1 |
| `marinho` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `limite` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `nomeabrev` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `ds_cr` | `xsd:string` | true | 0..1 |
| `co_funai` | `xsd:int` | true | 0..1 |
| `no_ti` | `xsd:string` | true | 0..1 |
| `co_cr` | `xsd:long` | true | 0..1 |

### `CMR-PUBLICO:lim_fronteira_uf_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `cd_uf` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `cd_regia` | `xsd:string` | true | 0..1 |
| `nm_regia` | `xsd:string` | true | 0..1 |
| `sigla_rg` | `xsd:string` | true | 0..1 |
| `area_tot` | `xsd:double` | true | 0..1 |
| `area_int` | `xsd:double` | true | 0..1 |
| `porc_int` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `CMR-PUBLICO:lim_municipio_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nu_uf_geocodigo` | `xsd:int` | false | 1..1 |
| `no_municipio` | `xsd:string` | false | 1..1 |
| `no_abreviado` | `xsd:string` | true | 0..1 |
| `nu_geocodigo` | `xsd:int` | false | 1..1 |
| `nu_ano_referencia` | `xsd:short` | true | 0..1 |
| `nu_area_km2` | `xsd:double` | true | 0..1 |
| `nu_area_ha` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | false | 1..1 |
| `dt_cadastro` | `xsd:dateTime` | false | 1..1 |
| `sg_uf` | `xsd:string` | true | 0..1 |

### `CMR-PUBLICO:lim_prodes_biomas_x_terra_indigena_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `co_funai` | `xsd:int` | true | 0..1 |
| `no_ti` | `xsd:string` | true | 0..1 |
| `co_cr` | `xsd:long` | true | 0..1 |
| `id_ti` | `xsd:string` | true | 0..1 |
| `ds_cr` | `xsd:string` | true | 0..1 |
| `id_cr` | `xsd:string` | true | 0..1 |
| `no_classe` | `xsd:string` | true | 0..1 |
| `sg_uf` | `xsd:string` | true | 0..1 |
| `nu_ano` | `xsd:int` | true | 0..1 |
| `nu_orbita` | `xsd:string` | true | 0..1 |
| `nu_ponto` | `xsd:string` | true | 0..1 |
| `dt_imagem` | `xsd:date` | true | 0..1 |
| `nu_area_km2` | `xsd:decimal` | true | 0..1 |
| `nu_area_ha` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `CMR-PUBLICO:lim_quilombolas_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `co_sr` | `xsd:string` | true | 0..1 |
| `nu_processo` | `xsd:string` | true | 0..1 |
| `no_comunidade` | `xsd:string` | true | 0..1 |
| `no_municipio` | `xsd:string` | true | 0..1 |
| `sg_uf` | `xsd:string` | true | 0..1 |
| `dt_publica` | `xsd:date` | true | 0..1 |
| `dt_public1` | `xsd:date` | true | 0..1 |
| `nu_familia` | `xsd:int` | true | 0..1 |
| `dt_titulo` | `xsd:date` | true | 0..1 |
| `nu_area_ha` | `xsd:double` | true | 0..1 |
| `no_responsavel` | `xsd:string` | true | 0..1 |
| `no_esfera` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `dt_cadastro` | `xsd:dateTime` | false | 1..1 |
| `cd_quilomb` | `xsd:int` | true | 0..1 |
| `cd_sipra` | `xsd:string` | true | 0..1 |
| `ds_descricao` | `xsd:string` | true | 0..1 |
| `st_titulad` | `xsd:string` | true | 0..1 |
| `dt_decreto` | `xsd:date` | true | 0..1 |
| `tp_levanta` | `xsd:string` | true | 0..1 |
| `nr_escalao` | `xsd:string` | true | 0..1 |
| `ds_fase` | `xsd:string` | true | 0..1 |

### `CMR-PUBLICO:lim_quilombolas_ti_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `co_sr` | `xsd:string` | true | 0..1 |
| `nu_processo` | `xsd:string` | true | 0..1 |
| `no_comunidade` | `xsd:string` | true | 0..1 |
| `no_municipio` | `xsd:string` | true | 0..1 |
| `sg_uf` | `xsd:string` | true | 0..1 |
| `dt_publica` | `xsd:date` | true | 0..1 |
| `dt_public1` | `xsd:date` | true | 0..1 |
| `nu_familia` | `xsd:int` | true | 0..1 |
| `dt_titulo` | `xsd:date` | true | 0..1 |
| `nu_area_ha` | `xsd:double` | true | 0..1 |
| `no_responsavel` | `xsd:string` | true | 0..1 |
| `no_esfera` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `dt_cadastro` | `xsd:dateTime` | true | 0..1 |
| `cd_quilomb` | `xsd:int` | true | 0..1 |
| `cd_sipra` | `xsd:string` | true | 0..1 |
| `ds_descricao` | `xsd:string` | true | 0..1 |
| `st_titulad` | `xsd:string` | true | 0..1 |
| `dt_decreto` | `xsd:date` | true | 0..1 |
| `tp_levanta` | `xsd:string` | true | 0..1 |
| `nr_escalao` | `xsd:string` | true | 0..1 |
| `ds_fase` | `xsd:string` | true | 0..1 |
| `ds_cr` | `xsd:string` | true | 0..1 |
| `co_funai` | `xsd:int` | true | 0..1 |
| `no_ti` | `xsd:string` | true | 0..1 |
| `co_cr` | `xsd:long` | true | 0..1 |

### `CMR-PUBLICO:lim_semiarido_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | false | 1..1 |
| `nu_area_km2` | `xsd:double` | true | 0..1 |
| `nu_area_ha` | `xsd:double` | true | 0..1 |
| `dt_cadastro` | `xsd:dateTime` | false | 1..1 |

### `CMR-PUBLICO:lim_sigmine_ti_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `id_sigmine` | `xsd:string` | true | 0..1 |
| `no_processo` | `xsd:string` | true | 0..1 |
| `nu_numero` | `xsd:string` | true | 0..1 |
| `nu_ano` | `xsd:int` | true | 0..1 |
| `nu_area_ha` | `xsd:double` | true | 0..1 |
| `no_fase` | `xsd:string` | true | 0..1 |
| `no_ult_evento` | `xsd:string` | true | 0..1 |
| `no_nome` | `xsd:string` | true | 0..1 |
| `no_subs` | `xsd:string` | true | 0..1 |
| `no_uso` | `xsd:string` | true | 0..1 |
| `sg_uf` | `xsd:string` | true | 0..1 |
| `dt_cadastro` | `xsd:dateTime` | true | 0..1 |
| `no_ti` | `xsd:string` | true | 0..1 |
| `co_funai` | `xsd:int` | true | 0..1 |
| `ds_cr` | `xsd:string` | true | 0..1 |
| `co_cr` | `xsd:long` | true | 0..1 |

### `CMR-PUBLICO:lim_terra_indigena_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `no_ti` | `xsd:string` | false | 1..1 |
| `no_grupo_etnico` | `xsd:string` | true | 0..1 |
| `ds_fase_ti` | `xsd:string` | true | 0..1 |
| `ds_modalidade` | `xsd:string` | true | 0..1 |
| `ds_reestudo_ti` | `xsd:string` | true | 0..1 |
| `ds_cr` | `xsd:string` | true | 0..1 |
| `no_municipio` | `xsd:string` | true | 0..1 |
| `sg_uf` | `xsd:string` | true | 0..1 |
| `co_funai` | `xsd:int` | false | 1..1 |
| `nu_area_ha` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | false | 1..1 |
| `dt_cadastro` | `xsd:dateTime` | false | 1..1 |
| `st_faixa_fronteira` | `xsd:string` | true | 0..1 |
| `dt_em_estudo` | `xsd:date` | true | 0..1 |
| `ds_portaria_em_estudo` | `xsd:string` | true | 0..1 |
| `dt_delimitada` | `xsd:date` | true | 0..1 |
| `ds_despacho_delimitada` | `xsd:string` | true | 0..1 |
| `dt_declarada` | `xsd:date` | true | 0..1 |
| `ds_portaria_declarada` | `xsd:string` | true | 0..1 |
| `dt_homologada` | `xsd:date` | true | 0..1 |
| `ds_decreto_homologada` | `xsd:string` | true | 0..1 |
| `dt_regularizada` | `xsd:date` | true | 0..1 |
| `ds_matricula_regularizada` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_em_estudo` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_delimitada` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_declarada` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_homologada` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_regularizada` | `xsd:string` | true | 0..1 |
| `co_cr` | `xsd:long` | true | 0..1 |
| `possui_ig` | `xsd:boolean` | true | 0..1 |
| `ranking` | `xsd:long` | true | 0..1 |
| `dt_insercao_ti` | `xsd:date` | true | 0..1 |
| `dt_dou` | `xsd:date` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `ano_base` | `xsd:int` | true | 0..1 |

### `CMR-PUBLICO:lim_terra_indigena_at`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `no_ti` | `xsd:string` | false | 1..1 |
| `no_grupo_etnico` | `xsd:string` | true | 0..1 |
| `ds_fase_ti` | `xsd:string` | true | 0..1 |
| `ds_modalidade` | `xsd:string` | true | 0..1 |
| `ds_reestudo_ti` | `xsd:string` | true | 0..1 |
| `ds_cr` | `xsd:string` | true | 0..1 |
| `no_municipio` | `xsd:string` | true | 0..1 |
| `sg_uf` | `xsd:string` | true | 0..1 |
| `co_funai` | `xsd:int` | false | 1..1 |
| `nu_area_ha` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | false | 1..1 |
| `dt_cadastro` | `xsd:dateTime` | false | 1..1 |
| `st_faixa_fronteira` | `xsd:string` | true | 0..1 |
| `dt_em_estudo` | `xsd:date` | true | 0..1 |
| `ds_portaria_em_estudo` | `xsd:string` | true | 0..1 |
| `dt_delimitada` | `xsd:date` | true | 0..1 |
| `ds_despacho_delimitada` | `xsd:string` | true | 0..1 |
| `dt_declarada` | `xsd:date` | true | 0..1 |
| `ds_portaria_declarada` | `xsd:string` | true | 0..1 |
| `dt_homologada` | `xsd:date` | true | 0..1 |
| `ds_decreto_homologada` | `xsd:string` | true | 0..1 |
| `dt_regularizada` | `xsd:date` | true | 0..1 |
| `ds_matricula_regularizada` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_em_estudo` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_delimitada` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_declarada` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_homologada` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_regularizada` | `xsd:string` | true | 0..1 |
| `co_cr` | `xsd:long` | true | 0..1 |
| `possui_ig` | `xsd:boolean` | true | 0..1 |
| `ranking` | `xsd:long` | true | 0..1 |
| `dt_insercao_ti` | `xsd:date` | true | 0..1 |
| `dt_dou` | `xsd:date` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `ano_base` | `xsd:int` | true | 0..1 |

### `CMR-PUBLICO:lim_unidade_conservacao_federal_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `no_uc` | `xsd:string` | true | 0..1 |
| `sg_uc` | `xsd:string` | true | 0..1 |
| `no_unidade` | `xsd:string` | true | 0..1 |
| `co_cnuc` | `xsd:short` | true | 0..1 |
| `ds_link_icmbio` | `xsd:string` | true | 0..1 |
| `no_classificacao` | `xsd:string` | true | 0..1 |
| `sg_grupo` | `xsd:string` | true | 0..1 |
| `nu_ano_criacao` | `xsd:short` | true | 0..1 |
| `ds_ato_legalizacao` | `xsd:string` | true | 0..1 |
| `ds_historico` | `xsd:string` | true | 0..1 |
| `no_coordenacao` | `xsd:string` | true | 0..1 |
| `ds_fuso_abrangente` | `xsd:string` | true | 0..1 |
| `nu_perimetro` | `xsd:double` | true | 0..1 |
| `nu_hectare` | `xsd:double` | true | 0..1 |
| `ds_especie` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | false | 1..1 |
| `dt_cadastro` | `xsd:dateTime` | false | 1..1 |
| `no_administracao` | `xsd:string` | true | 0..1 |
| `sg_uf` | `xsd:string` | true | 0..1 |
| `no_municipios` | `xsd:string` | true | 0..1 |
| `no_biomaibge` | `xsd:string` | true | 0..1 |
| `no_biomacrl` | `xsd:string` | true | 0..1 |
| `nu_uorg` | `xsd:int` | true | 0..1 |
| `no_nome` | `xsd:string` | true | 0..1 |

### `CMR-PUBLICO:lim_unidade_conservacao_federal_a_ti_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `no_uc` | `xsd:string` | true | 0..1 |
| `sg_uc` | `xsd:string` | true | 0..1 |
| `no_unidade` | `xsd:string` | true | 0..1 |
| `co_cnuc` | `xsd:short` | true | 0..1 |
| `ds_link_icmbio` | `xsd:string` | true | 0..1 |
| `no_classificacao` | `xsd:string` | true | 0..1 |
| `sg_grupo` | `xsd:string` | true | 0..1 |
| `nu_ano_criacao` | `xsd:short` | true | 0..1 |
| `ds_ato_legalizacao` | `xsd:string` | true | 0..1 |
| `ds_historico` | `xsd:string` | true | 0..1 |
| `no_coordenacao` | `xsd:string` | true | 0..1 |
| `ds_fuso_abrangente` | `xsd:string` | true | 0..1 |
| `nu_perimetro` | `xsd:double` | true | 0..1 |
| `nu_hectare` | `xsd:double` | true | 0..1 |
| `ds_especie` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `dt_cadastro` | `xsd:dateTime` | true | 0..1 |
| `no_administracao` | `xsd:string` | true | 0..1 |
| `sg_uf` | `xsd:string` | true | 0..1 |
| `no_municipios` | `xsd:string` | true | 0..1 |
| `no_biomaibge` | `xsd:string` | true | 0..1 |
| `no_biomacrl` | `xsd:string` | true | 0..1 |
| `nu_uorg` | `xsd:int` | true | 0..1 |
| `no_nome` | `xsd:string` | true | 0..1 |
| `ds_cr` | `xsd:string` | true | 0..1 |
| `co_funai` | `xsd:int` | true | 0..1 |
| `no_ti` | `xsd:string` | true | 0..1 |
| `co_cr` | `xsd:long` | true | 0..1 |

### `CMR-PUBLICO:lim_unidade_federacao_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `sg_uf` | `xsd:string` | false | 1..1 |
| `no_uf` | `xsd:string` | false | 1..1 |
| `no_abreviado` | `xsd:string` | true | 0..1 |
| `nu_geocodigo` | `xsd:int` | false | 1..1 |
| `nu_ano_referencia` | `xsd:short` | true | 0..1 |
| `nu_area_km2` | `xsd:double` | true | 0..1 |
| `nu_area_ha` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | false | 1..1 |
| `dt_cadastro` | `xsd:dateTime` | false | 1..1 |

### `CMR-PUBLICO:loc_coordenacao_regional_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `co_cr` | `xsd:long` | false | 1..1 |
| `no_cr` | `xsd:string` | false | 1..1 |
| `no_abreviado` | `xsd:string` | true | 0..1 |
| `sg_cr` | `xsd:string` | true | 0..1 |
| `st_situacao` | `xsd:string` | true | 0..1 |
| `ds_email` | `xsd:string` | true | 0..1 |
| `no_regiao` | `xsd:string` | true | 0..1 |
| `no_municipio` | `xsd:string` | true | 0..1 |
| `no_uf` | `xsd:string` | true | 0..1 |
| `sg_uf` | `xsd:string` | true | 0..1 |
| `ds_telefone` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | false | 1..1 |
| `dt_cadastro` | `xsd:dateTime` | false | 1..1 |

### `CMR-PUBLICO:loc_coordenacao_regional_ti_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `co_cr` | `xsd:long` | true | 0..1 |
| `no_cr` | `xsd:string` | true | 0..1 |
| `no_abreviado` | `xsd:string` | true | 0..1 |
| `sg_cr` | `xsd:string` | true | 0..1 |
| `st_situacao` | `xsd:string` | true | 0..1 |
| `ds_email` | `xsd:string` | true | 0..1 |
| `no_regiao` | `xsd:string` | true | 0..1 |
| `no_municipio` | `xsd:string` | true | 0..1 |
| `no_uf` | `xsd:string` | true | 0..1 |
| `sg_uf` | `xsd:string` | true | 0..1 |
| `ds_telefone` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `dt_cadastro` | `xsd:dateTime` | true | 0..1 |
| `ds_cr` | `xsd:string` | true | 0..1 |
| `co_funai` | `xsd:int` | true | 0..1 |
| `no_ti` | `xsd:string` | true | 0..1 |

### `CMR-PUBLICO:loc_indigenas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `cd_munic` | `xsd:int` | true | 0..1 |
| `nm_munic` | `xsd:string` | true | 0..1 |
| `id_li` | `xsd:int` | true | 0..1 |
| `cd_li` | `xsd:int` | true | 0..1 |
| `ocorrencia` | `xsd:int` | true | 0..1 |
| `nm_li` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `ti_funai` | `xsd:string` | true | 0..1 |
| `nm_ti` | `xsd:string` | true | 0..1 |
| `fase` | `xsd:string` | true | 0..1 |
| `c_cr_funai` | `xsd:string` | true | 0..1 |
| `n_cr_funai` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `CMR-PUBLICO:loc_sede_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geometriaa` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geocodigo` | `xsd:int` | true | 0..1 |
| `dt_cadastro` | `xsd:dateTime` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `CMR-PUBLICO:loc_terra_indigena_estudo_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `co_funai` | `xsd:int` | false | 1..1 |
| `no_ti` | `xsd:string` | false | 1..1 |
| `no_grupo_etnico` | `xsd:string` | true | 0..1 |
| `ds_fase_ti` | `xsd:string` | true | 0..1 |
| `ds_modalidade` | `xsd:string` | true | 0..1 |
| `ds_reestudo_ti` | `xsd:string` | true | 0..1 |
| `no_municipio` | `xsd:string` | true | 0..1 |
| `sg_uf` | `xsd:string` | true | 0..1 |
| `st_faixa_fronteira` | `xsd:string` | true | 0..1 |
| `dt_em_estudo` | `xsd:date` | true | 0..1 |
| `ds_portaria_em_estudo` | `xsd:string` | true | 0..1 |
| `dt_delimitada` | `xsd:date` | true | 0..1 |
| `ds_despacho_delimitada` | `xsd:string` | true | 0..1 |
| `dt_declarada` | `xsd:date` | true | 0..1 |
| `ds_portaria_declarada` | `xsd:string` | true | 0..1 |
| `dt_homologada` | `xsd:date` | true | 0..1 |
| `ds_decreto_homologada` | `xsd:string` | true | 0..1 |
| `dt_regularizada` | `xsd:date` | true | 0..1 |
| `ds_matricula_regularizada` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_em_estudo` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_delimitada` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_declarada` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_homologada` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_regularizada` | `xsd:string` | true | 0..1 |
| `nu_area_ha` | `xsd:double` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | false | 1..1 |
| `dt_cadastro` | `xsd:dateTime` | false | 1..1 |

### `CMR-PUBLICO:met_risco_fogo_previsao_1dia_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nu_risco_fogo` | `xsd:int` | true | 0..1 |
| `nu_area_ha` | `xsd:double` | true | 0..1 |
| `dt_cadastro` | `xsd:date` | true | 0..1 |

### `CMR-PUBLICO:met_risco_fogo_previsao_2dias_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nu_risco_fogo` | `xsd:int` | true | 0..1 |
| `nu_area_ha` | `xsd:double` | true | 0..1 |
| `dt_cadastro` | `xsd:date` | true | 0..1 |

### `CMR-PUBLICO:tra_trecho_rodoviario_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nu_br` | `xsd:short` | false | 1..1 |
| `sg_uf` | `xsd:string` | false | 1..1 |
| `co_rodovia` | `xsd:string` | false | 1..1 |
| `no_inicio_rodovia` | `xsd:string` | false | 1..1 |
| `no_fim_rodovia` | `xsd:string` | false | 1..1 |
| `nu_km_inicial` | `xsd:double` | false | 1..1 |
| `nu_km_final` | `xsd:double` | false | 1..1 |
| `nu_km_extensao` | `xsd:double` | false | 1..1 |
| `ds_situacao` | `xsd:string` | false | 1..1 |
| `ds_concessao` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | false | 1..1 |
| `dt_cadastro` | `xsd:dateTime` | false | 1..1 |
| `id_trecho` | `xsd:long` | true | 0..1 |
| `no_br` | `xsd:string` | true | 0..1 |
| `nm_tipo_trecho` | `xsd:string` | true | 0..1 |
| `sg_tipo_trecho` | `xsd:string` | true | 0..1 |
| `ds_coincidente` | `xsd:string` | true | 0..1 |
| `sg_superficie_federal` | `xsd:string` | true | 0..1 |
| `ds_obra` | `xsd:string` | true | 0..1 |
| `no_unidade_local` | `xsd:string` | true | 0..1 |
| `ds_ato_legal` | `xsd:string` | true | 0..1 |
| `no_estadual_coincidente` | `xsd:string` | true | 0..1 |
| `no_superficie_estadual_coincidente` | `xsd:string` | true | 0..1 |
| `ds_jurisdicao` | `xsd:string` | true | 0..1 |
| `ds_superficie_federal` | `xsd:string` | true | 0..1 |
| `ds_legenda` | `xsd:string` | true | 0..1 |
| `sg_legenda` | `xsd:string` | true | 0..1 |

### `CMR-PUBLICO:veg_biomas_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `no_bioma` | `xsd:string` | false | 1..1 |
| `nu_area_km2` | `xsd:double` | true | 0..1 |
| `nu_area_ha` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | false | 1..1 |
| `dt_cadastro` | `xsd:dateTime` | false | 1..1 |

### `CMR-PUBLICO:vw_img_grade_landsat_ti_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `path` | `xsd:int` | true | 0..1 |
| `row` | `xsd:int` | true | 0..1 |
| `orb_ponto` | `xsd:string` | true | 0..1 |
| `path_row` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `dt_cadastro` | `xsd:dateTime` | true | 0..1 |
| `co_cr` | `xsd:long` | true | 0..1 |
| `ds_cr` | `xsd:string` | true | 0..1 |
| `co_funai` | `xsd:int` | true | 0..1 |
| `no_ti` | `xsd:string` | true | 0..1 |

### `CMR-PUBLICO:vw_img_grade_sentinel2_a_ti_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `ds_nome` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `dt_cadastro` | `xsd:dateTime` | true | 0..1 |
| `co_cr` | `xsd:long` | true | 0..1 |
| `ds_cr` | `xsd:string` | true | 0..1 |
| `co_funai` | `xsd:int` | true | 0..1 |
| `no_ti` | `xsd:string` | true | 0..1 |

### `CMR-PUBLICO:vw_lim_imovel_certificado_privado_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `co_imovel` | `xsd:string` | true | 0..1 |
| `nu_processo` | `xsd:string` | true | 0..1 |
| `co_sr` | `xsd:string` | true | 0..1 |
| `nu_certificado` | `xsd:string` | true | 0..1 |
| `dt_certificado` | `xsd:dateTime` | true | 0..1 |
| `nu_area_ha` | `xsd:double` | true | 0..1 |
| `co_profissional` | `xsd:string` | true | 0..1 |
| `dt_cadastro` | `xsd:dateTime` | true | 0..1 |
| `no_imovel` | `xsd:string` | true | 0..1 |
| `sg_uf` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `CMR-PUBLICO:vw_lim_imovel_certificado_privado_ti_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `co_imovel` | `xsd:string` | true | 0..1 |
| `nu_processo` | `xsd:string` | true | 0..1 |
| `co_sr` | `xsd:string` | true | 0..1 |
| `nu_certificado` | `xsd:string` | true | 0..1 |
| `dt_certificado` | `xsd:dateTime` | true | 0..1 |
| `nu_area_ha` | `xsd:double` | true | 0..1 |
| `co_profissional` | `xsd:string` | true | 0..1 |
| `dt_cadastro` | `xsd:dateTime` | true | 0..1 |
| `no_imovel` | `xsd:string` | true | 0..1 |
| `sg_uf` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `ds_cr` | `xsd:string` | true | 0..1 |
| `co_funai` | `xsd:int` | true | 0..1 |
| `no_ti` | `xsd:string` | true | 0..1 |

### `CMR-PUBLICO:vw_lim_imovel_certificado_publico_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `no_imovel` | `xsd:string` | true | 0..1 |
| `nu_processo` | `xsd:string` | true | 0..1 |
| `co_sr` | `xsd:string` | true | 0..1 |
| `sg_uf` | `xsd:string` | true | 0..1 |
| `co_profissional` | `xsd:string` | true | 0..1 |
| `nu_certificado` | `xsd:string` | true | 0..1 |
| `dt_certificado` | `xsd:dateTime` | true | 0..1 |
| `nu_area_ha` | `xsd:double` | true | 0..1 |
| `dt_cadastro` | `xsd:dateTime` | true | 0..1 |
| `co_imovel` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `CMR-PUBLICO:vw_lim_imovel_certificado_publico_a_ti_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `no_imovel` | `xsd:string` | true | 0..1 |
| `nu_processo` | `xsd:string` | true | 0..1 |
| `co_sr` | `xsd:string` | true | 0..1 |
| `sg_uf` | `xsd:string` | true | 0..1 |
| `co_profissional` | `xsd:string` | true | 0..1 |
| `nu_certificado` | `xsd:string` | true | 0..1 |
| `dt_certificado` | `xsd:dateTime` | true | 0..1 |
| `nu_area_ha` | `xsd:double` | true | 0..1 |
| `dt_cadastro` | `xsd:dateTime` | true | 0..1 |
| `co_imovel` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `ds_cr` | `xsd:string` | true | 0..1 |
| `co_funai` | `xsd:int` | true | 0..1 |
| `no_ti` | `xsd:string` | true | 0..1 |
| `co_cr` | `xsd:long` | true | 0..1 |

### `CMR-PUBLICO:vw_lim_imovel_certificado_sigef_privado_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `co_parcela` | `xsd:string` | true | 0..1 |
| `no_rt` | `xsd:string` | true | 0..1 |
| `co_art` | `xsd:string` | true | 0..1 |
| `ds_situacao` | `xsd:string` | true | 0..1 |
| `co_imovel` | `xsd:long` | true | 0..1 |
| `dt_submissao` | `xsd:date` | true | 0..1 |
| `dt_aprovacao` | `xsd:date` | true | 0..1 |
| `ds_status` | `xsd:string` | true | 0..1 |
| `no_area` | `xsd:string` | true | 0..1 |
| `ds_registro_m` | `xsd:string` | true | 0..1 |
| `ds_registro_d` | `xsd:string` | true | 0..1 |
| `cd_municipio` | `xsd:long` | true | 0..1 |
| `cd_uf` | `xsd:int` | true | 0..1 |
| `dt_cadastro` | `xsd:date` | true | 0..1 |

### `CMR-PUBLICO:vw_lim_imovel_certificado_sigef_privado_ti_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `co_parcela` | `xsd:string` | true | 0..1 |
| `no_rt` | `xsd:string` | true | 0..1 |
| `co_art` | `xsd:string` | true | 0..1 |
| `ds_situacao` | `xsd:string` | true | 0..1 |
| `co_imovel` | `xsd:long` | true | 0..1 |
| `dt_submissao` | `xsd:date` | true | 0..1 |
| `dt_aprovacao` | `xsd:date` | true | 0..1 |
| `ds_status` | `xsd:string` | true | 0..1 |
| `no_area` | `xsd:string` | true | 0..1 |
| `ds_registro_m` | `xsd:string` | true | 0..1 |
| `ds_registro_d` | `xsd:string` | true | 0..1 |
| `cd_municipio` | `xsd:long` | true | 0..1 |
| `cd_uf` | `xsd:int` | true | 0..1 |
| `dt_cadastro` | `xsd:date` | true | 0..1 |
| `ds_cr` | `xsd:string` | true | 0..1 |
| `co_funai` | `xsd:int` | true | 0..1 |
| `no_ti` | `xsd:string` | true | 0..1 |

### `CMR-PUBLICO:vw_lim_imovel_certificado_sigef_publico_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `co_parcela` | `xsd:string` | true | 0..1 |
| `no_rt` | `xsd:string` | true | 0..1 |
| `co_art` | `xsd:string` | true | 0..1 |
| `ds_situacao` | `xsd:string` | true | 0..1 |
| `co_imovel` | `xsd:long` | true | 0..1 |
| `dt_submissao` | `xsd:date` | true | 0..1 |
| `dt_aprovacao` | `xsd:date` | true | 0..1 |
| `ds_status` | `xsd:string` | true | 0..1 |
| `no_area` | `xsd:string` | true | 0..1 |
| `ds_registro_m` | `xsd:string` | true | 0..1 |
| `ds_registro_d` | `xsd:string` | true | 0..1 |
| `cd_municipio` | `xsd:long` | true | 0..1 |
| `cd_uf` | `xsd:int` | true | 0..1 |
| `dt_cadastro` | `xsd:date` | true | 0..1 |

### `CMR-PUBLICO:vw_lim_imovel_certificado_sigef_publico_ti_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `co_parcela` | `xsd:string` | true | 0..1 |
| `no_rt` | `xsd:string` | true | 0..1 |
| `co_art` | `xsd:string` | true | 0..1 |
| `ds_situacao` | `xsd:string` | true | 0..1 |
| `co_imovel` | `xsd:long` | true | 0..1 |
| `dt_submissao` | `xsd:date` | true | 0..1 |
| `dt_aprovacao` | `xsd:date` | true | 0..1 |
| `ds_status` | `xsd:string` | true | 0..1 |
| `no_area` | `xsd:string` | true | 0..1 |
| `ds_registro_m` | `xsd:string` | true | 0..1 |
| `ds_registro_d` | `xsd:string` | true | 0..1 |
| `cd_municipio` | `xsd:long` | true | 0..1 |
| `cd_uf` | `xsd:int` | true | 0..1 |
| `dt_cadastro` | `xsd:date` | true | 0..1 |
| `ds_cr` | `xsd:string` | true | 0..1 |
| `co_funai` | `xsd:int` | true | 0..1 |
| `no_ti` | `xsd:string` | true | 0..1 |

### `CMR-PUBLICO:vw_lim_terra_indigena_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `no_ti` | `xsd:string` | true | 0..1 |
| `no_grupo_etnico` | `xsd:string` | true | 0..1 |
| `ds_fase_ti` | `xsd:string` | true | 0..1 |
| `ds_modalidade` | `xsd:string` | true | 0..1 |
| `ds_reestudo_ti` | `xsd:string` | true | 0..1 |
| `ds_cr` | `xsd:string` | true | 0..1 |
| `no_municipio` | `xsd:string` | true | 0..1 |
| `sg_uf` | `xsd:string` | true | 0..1 |
| `co_funai` | `xsd:int` | true | 0..1 |
| `nu_area_ha` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `dt_cadastro` | `xsd:dateTime` | true | 0..1 |
| `st_faixa_fronteira` | `xsd:string` | true | 0..1 |
| `dt_em_estudo` | `xsd:date` | true | 0..1 |
| `ds_portaria_em_estudo` | `xsd:string` | true | 0..1 |
| `dt_delimitada` | `xsd:date` | true | 0..1 |
| `ds_despacho_delimitada` | `xsd:string` | true | 0..1 |
| `dt_declarada` | `xsd:date` | true | 0..1 |
| `ds_portaria_declarada` | `xsd:string` | true | 0..1 |
| `dt_homologada` | `xsd:date` | true | 0..1 |
| `ds_decreto_homologada` | `xsd:string` | true | 0..1 |
| `dt_regularizada` | `xsd:date` | true | 0..1 |
| `ds_matricula_regularizada` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_em_estudo` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_delimitada` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_declarada` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_homologada` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_regularizada` | `xsd:string` | true | 0..1 |
| `co_cr` | `xsd:long` | true | 0..1 |
| `possui_ig` | `xsd:boolean` | true | 0..1 |
| `ranking` | `xsd:long` | true | 0..1 |

### `CMR-PUBLICO:vw_lim_terra_indigena_possui_ig`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `no_ti` | `xsd:string` | true | 0..1 |
| `no_grupo_etnico` | `xsd:string` | true | 0..1 |
| `ds_fase_ti` | `xsd:string` | true | 0..1 |
| `ds_modalidade` | `xsd:string` | true | 0..1 |
| `ds_reestudo_ti` | `xsd:string` | true | 0..1 |
| `co_cr` | `xsd:long` | true | 0..1 |
| `ds_cr` | `xsd:string` | true | 0..1 |
| `no_municipio` | `xsd:string` | true | 0..1 |
| `sg_uf` | `xsd:string` | true | 0..1 |
| `co_funai` | `xsd:int` | true | 0..1 |
| `nu_area_ha` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `dt_cadastro` | `xsd:dateTime` | true | 0..1 |
| `st_faixa_fronteira` | `xsd:string` | true | 0..1 |
| `dt_em_estudo` | `xsd:date` | true | 0..1 |
| `ds_portaria_em_estudo` | `xsd:string` | true | 0..1 |
| `dt_delimitada` | `xsd:date` | true | 0..1 |
| `ds_despacho_delimitada` | `xsd:string` | true | 0..1 |
| `dt_declarada` | `xsd:date` | true | 0..1 |
| `ds_portaria_declarada` | `xsd:string` | true | 0..1 |
| `dt_homologada` | `xsd:date` | true | 0..1 |
| `ds_decreto_homologada` | `xsd:string` | true | 0..1 |
| `dt_regularizada` | `xsd:date` | true | 0..1 |
| `ds_matricula_regularizada` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_em_estudo` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_delimitada` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_declarada` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_homologada` | `xsd:string` | true | 0..1 |
| `ds_doc_resumo_regularizada` | `xsd:string` | true | 0..1 |
| `possui_ig` | `xsd:boolean` | true | 0..1 |
| `ranking` | `xsd:long` | true | 0..1 |

### `CMR-PUBLICO:vw_prodes_com_terra_indigena_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `co_funai` | `xsd:int` | true | 0..1 |
| `no_ti` | `xsd:string` | true | 0..1 |
| `co_cr` | `xsd:long` | true | 0..1 |
| `id_ti` | `xsd:string` | true | 0..1 |
| `ds_cr` | `xsd:string` | true | 0..1 |
| `id_cr` | `xsd:string` | true | 0..1 |
| `no_classe` | `xsd:string` | true | 0..1 |
| `sg_uf` | `xsd:string` | true | 0..1 |
| `nu_ano` | `xsd:short` | true | 0..1 |
| `nu_orbita` | `xsd:string` | true | 0..1 |
| `nu_ponto` | `xsd:string` | true | 0..1 |
| `dt_imagem` | `xsd:date` | true | 0..1 |
| `nu_area_km2` | `xsd:double` | true | 0..1 |
| `nu_area_ha` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `CMR-PUBLICO:vwm_heatmap_ti_cr_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `co_funai` | `xsd:int` | true | 0..1 |
| `no_ti` | `xsd:string` | true | 0..1 |
| `co_cr` | `xsd:long` | true | 0..1 |
| `ds_cr` | `xsd:string` | true | 0..1 |
| `ti_nu_area_ha` | `xsd:double` | true | 0..1 |
| `no_ciclo` | `xsd:string` | true | 0..1 |
| `no_estagio` | `xsd:string` | true | 0..1 |
| `no_imagem` | `xsd:string` | true | 0..1 |
| `dt_imagem` | `xsd:date` | true | 0..1 |
| `nu_orbita` | `xsd:string` | true | 0..1 |
| `nu_ponto` | `xsd:string` | true | 0..1 |
| `dt_t_zero` | `xsd:date` | true | 0..1 |
| `dt_t_um` | `xsd:date` | true | 0..1 |
| `nu_area_km2` | `xsd:decimal` | true | 0..1 |
| `nu_area_ha` | `xsd:decimal` | true | 0..1 |
| `nu_latitude` | `xsd:double` | true | 0..1 |
| `nu_longitude` | `xsd:double` | true | 0..1 |
| `dt_cadastro` | `xsd:date` | true | 0..1 |
| `no_municipio` | `xsd:string` | true | 0..1 |
| `sg_uf` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
