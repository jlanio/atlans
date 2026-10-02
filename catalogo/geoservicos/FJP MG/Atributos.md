# FJP MG — atributos das camadas

Geoportal: [[Geosserviços/FJP MG/Infraestrutura Estadual de Dados Espaciais — Fundação João Pinheiro|Infraestrutura Estadual de Dados Espaciais — Fundação João Pinheiro]]

Os campos abaixo vêm de `DescribeFeatureType` (XSD), sem download de feições.

## BASE_DA_DIVISÃO_TERRITORIAL.Distritos (1)

### `BASE_DA_DIVISÃO_TERRITORIAL.Distritos:mg_distritos_fjp_pl_ago_2026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `GEOCODIGO` | `xsd:string` | true | 0..1 |
| `ANODEREFER` | `xsd:string` | true | 0..1 |
| `LEICRIACAO` | `xsd:string` | true | 0..1 |
| `AREA` | `xsd:double` | true | 0..1 |
| `MUNICIPIO` | `xsd:string` | true | 0..1 |
| `GEOCODIGOM` | `xsd:string` | true | 0..1 |
| `DATAIOMG` | `xsd:string` | true | 0..1 |
| `LEGENDA` | `xsd:string` | true | 0..1 |

## BASE_DA_DIVISÃO_TERRITORIAL.Limites_Distritais (1)

### `BASE_DA_DIVISÃO_TERRITORIAL.Limites_Distritais:mg_distritos_fjp_ln_ago_2026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `GEOCODIGO` | `xsd:string` | true | 0..1 |
| `ANODEREFER` | `xsd:string` | true | 0..1 |
| `LEICRIACAO` | `xsd:string` | true | 0..1 |
| `AREA` | `xsd:double` | true | 0..1 |
| `MUNICIPIO` | `xsd:string` | true | 0..1 |
| `GEOCODIGOM` | `xsd:string` | true | 0..1 |
| `DATAIOMG` | `xsd:string` | true | 0..1 |
| `LEGENDA` | `xsd:string` | true | 0..1 |

## BASE_DA_DIVISÃO_TERRITORIAL.Limites_Estaduais (1)

### `BASE_DA_DIVISÃO_TERRITORIAL.Limites_Estaduais:mg_limite_estadual_fjp_pl_jan_2026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `ANODEREFER` | `xsd:double` | true | 0..1 |
| `AREA` | `xsd:double` | true | 0..1 |

## BASE_DA_DIVISÃO_TERRITORIAL.Limites_Municipais (1)

### `BASE_DA_DIVISÃO_TERRITORIAL.Limites_Municipais:mg_municipios_fjp_ln_jul_2026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `GEOCODIGO` | `xsd:string` | true | 0..1 |
| `ANODEREFER` | `xsd:string` | true | 0..1 |
| `LEICRIACAO` | `xsd:string` | true | 0..1 |
| `AREA` | `xsd:decimal` | true | 0..1 |
| `MUNORGC1` | `xsd:string` | true | 0..1 |
| `MUNORIG1` | `xsd:string` | true | 0..1 |
| `MUNORGC2` | `xsd:string` | true | 0..1 |
| `MUNORIG2` | `xsd:string` | true | 0..1 |
| `ADPATRIO` | `xsd:string` | true | 0..1 |
| `DENOMANT` | `xsd:string` | true | 0..1 |
| `LEGEND` | `xsd:string` | true | 0..1 |

## BASE_DA_DIVISÃO_TERRITORIAL.Municipios (1)

### `BASE_DA_DIVISÃO_TERRITORIAL.Municipios:mg_municipios_fjp_pl_set_2026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `GEOCODIGO` | `xsd:string` | true | 0..1 |
| `ANODEREFER` | `xsd:string` | true | 0..1 |
| `LEICRIACAO` | `xsd:string` | true | 0..1 |
| `AREA` | `xsd:double` | true | 0..1 |
| `MUNORGC1` | `xsd:string` | true | 0..1 |
| `MUNORIG1` | `xsd:string` | true | 0..1 |
| `MUNORGC2` | `xsd:string` | true | 0..1 |
| `MUNORIG2` | `xsd:string` | true | 0..1 |
| `ADPATRIO` | `xsd:string` | true | 0..1 |
| `DENOMANT` | `xsd:string` | true | 0..1 |
| `LEGENDA` | `xsd:string` | true | 0..1 |

## BASE_DA_DIVISÃO_TERRITORIAL.Vilas (1)

### `BASE_DA_DIVISÃO_TERRITORIAL.Vilas:mg_vilas_fjp_pt_jul_2026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `GEOCODIGO` | `xsd:string` | true | 0..1 |
| `LAT` | `xsd:decimal` | true | 0..1 |
| `LONG` | `xsd:decimal` | true | 0..1 |
| `MUNICIPIO` | `xsd:string` | true | 0..1 |
| `GEOCODIGOM` | `xsd:string` | true | 0..1 |
| `LEGEND` | `xsd:string` | true | 0..1 |

## DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Base_de_Dados_Geografica_da_Distribuidora_BDGD (10)

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Base_de_Dados_Geografica_da_Distribuidora_BDGD:mg_aproveitamentos_hidreletricos_aneel_pt_dez_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome` | `xsd:string` | true | 0..1 |
| `proprietar` | `xsd:string` | true | 0..1 |
| `cnpj` | `xsd:string` | true | 0..1 |
| `ceg` | `xsd:string` | true | 0..1 |
| `munic_cf` | `xsd:string` | true | 0..1 |
| `uf_cf` | `xsd:string` | true | 0..1 |
| `munic_1` | `xsd:string` | true | 0..1 |
| `uf_1` | `xsd:string` | true | 0..1 |
| `munic_2` | `xsd:string` | true | 0..1 |
| `uf_2` | `xsd:string` | true | 0..1 |
| `rio` | `xsd:string` | true | 0..1 |
| `cod_bac` | `xsd:decimal` | true | 0..1 |
| `cod_sbac` | `xsd:decimal` | true | 0..1 |
| `dsp_inv` | `xsd:string` | true | 0..1 |
| `ato_legal` | `xsd:string` | true | 0..1 |
| `proc_aneel` | `xsd:string` | true | 0..1 |
| `lat_eixo_g` | `xsd:string` | true | 0..1 |
| `long_eixo_` | `xsd:string` | true | 0..1 |
| `lat_cf_gms` | `xsd:string` | true | 0..1 |
| `long_cf_gm` | `xsd:string` | true | 0..1 |
| `pot_kw` | `xsd:decimal` | true | 0..1 |
| `n_unid_ger` | `xsd:int` | true | 0..1 |
| `pot_uni_ge` | `xsd:decimal` | true | 0..1 |
| `fator_pot` | `xsd:decimal` | true | 0..1 |
| `pot_por_tu` | `xsd:decimal` | true | 0..1 |
| `eng_min` | `xsd:decimal` | true | 0..1 |
| `tipo_turb` | `xsd:string` | true | 0..1 |
| `rend_nom_t` | `xsd:decimal` | true | 0..1 |
| `rend_nom_g` | `xsd:decimal` | true | 0..1 |
| `tx_eq_inds` | `xsd:decimal` | true | 0..1 |
| `inds_prog` | `xsd:decimal` | true | 0..1 |
| `perd_hid_n` | `xsd:decimal` | true | 0..1 |
| `na_max_max` | `xsd:decimal` | true | 0..1 |
| `na_max_mon` | `xsd:decimal` | true | 0..1 |
| `na_min_mon` | `xsd:decimal` | true | 0..1 |
| `na_nor_jus` | `xsd:decimal` | true | 0..1 |
| `area_na_ma` | `xsd:decimal` | true | 0..1 |
| `area_na_mi` | `xsd:decimal` | true | 0..1 |
| `area_dren` | `xsd:decimal` | true | 0..1 |
| `vol_na_max` | `xsd:decimal` | true | 0..1 |
| `vol_na_min` | `xsd:decimal` | true | 0..1 |
| `qd_bruta_n` | `xsd:decimal` | true | 0..1 |
| `perdas_ele` | `xsd:decimal` | true | 0..1 |
| `cons_inter` | `xsd:decimal` | true | 0..1 |
| `vazao_rem` | `xsd:decimal` | true | 0..1 |
| `vazao_uso_` | `xsd:decimal` | true | 0..1 |
| `vazao_proj` | `xsd:decimal` | true | 0..1 |
| `serie_vaza` | `xsd:string` | true | 0..1 |
| `tabela_ser` | `xsd:string` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `data_atual` | `xsd:date` | true | 0..1 |
| `inic_oper` | `xsd:date` | true | 0..1 |
| `pot_fisc_k` | `xsd:decimal` | true | 0..1 |
| `cod_uph` | `xsd:decimal` | true | 0..1 |
| `id_empreen` | `xsd:decimal` | true | 0..1 |
| `lat_eixo_d` | `xsd:decimal` | true | 0..1 |
| `long_eixo1` | `xsd:decimal` | true | 0..1 |
| `tipo_ahe` | `xsd:string` | true | 0..1 |
| `reg_mens` | `xsd:string` | true | 0..1 |
| `rn_696_15` | `xsd:string` | true | 0..1 |
| `fase` | `xsd:string` | true | 0..1 |
| `versao_atu` | `xsd:string` | true | 0..1 |
| `legend` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Base_de_Dados_Geografica_da_Distribuidora_BDGD:mg_centrais_geradoras_hidreletricas_aneel_pt_dez_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome` | `xsd:string` | true | 0..1 |
| `proprietar` | `xsd:string` | true | 0..1 |
| `cnpj` | `xsd:string` | true | 0..1 |
| `ceg` | `xsd:string` | true | 0..1 |
| `munic_cf` | `xsd:string` | true | 0..1 |
| `uf_cf` | `xsd:string` | true | 0..1 |
| `munic_1` | `xsd:string` | true | 0..1 |
| `uf_1` | `xsd:string` | true | 0..1 |
| `munic_2` | `xsd:string` | true | 0..1 |
| `uf_2` | `xsd:string` | true | 0..1 |
| `rio` | `xsd:string` | true | 0..1 |
| `cod_bac` | `xsd:decimal` | true | 0..1 |
| `cod_sbac` | `xsd:decimal` | true | 0..1 |
| `dsp_inv` | `xsd:string` | true | 0..1 |
| `ato_legal` | `xsd:string` | true | 0..1 |
| `proc_aneel` | `xsd:string` | true | 0..1 |
| `lat_eixo_g` | `xsd:string` | true | 0..1 |
| `long_eixo_` | `xsd:string` | true | 0..1 |
| `lat_cf_gms` | `xsd:string` | true | 0..1 |
| `long_cf_gm` | `xsd:string` | true | 0..1 |
| `pot_kw` | `xsd:decimal` | true | 0..1 |
| `n_unid_ger` | `xsd:int` | true | 0..1 |
| `pot_uni_ge` | `xsd:decimal` | true | 0..1 |
| `fator_pot` | `xsd:decimal` | true | 0..1 |
| `pot_por_tu` | `xsd:decimal` | true | 0..1 |
| `eng_min` | `xsd:decimal` | true | 0..1 |
| `tipo_turb` | `xsd:string` | true | 0..1 |
| `rend_nom_t` | `xsd:decimal` | true | 0..1 |
| `rend_nom_g` | `xsd:decimal` | true | 0..1 |
| `tx_eq_inds` | `xsd:decimal` | true | 0..1 |
| `inds_prog` | `xsd:decimal` | true | 0..1 |
| `perd_hid_n` | `xsd:decimal` | true | 0..1 |
| `na_max_max` | `xsd:decimal` | true | 0..1 |
| `na_max_mon` | `xsd:decimal` | true | 0..1 |
| `na_min_mon` | `xsd:decimal` | true | 0..1 |
| `na_nor_jus` | `xsd:decimal` | true | 0..1 |
| `area_na_ma` | `xsd:decimal` | true | 0..1 |
| `area_na_mi` | `xsd:decimal` | true | 0..1 |
| `area_dren` | `xsd:decimal` | true | 0..1 |
| `vol_na_max` | `xsd:decimal` | true | 0..1 |
| `vol_na_min` | `xsd:decimal` | true | 0..1 |
| `qd_bruta_n` | `xsd:decimal` | true | 0..1 |
| `perdas_ele` | `xsd:decimal` | true | 0..1 |
| `cons_inter` | `xsd:decimal` | true | 0..1 |
| `vazao_rem` | `xsd:decimal` | true | 0..1 |
| `vazao_uso_` | `xsd:decimal` | true | 0..1 |
| `vazao_proj` | `xsd:decimal` | true | 0..1 |
| `serie_vaza` | `xsd:string` | true | 0..1 |
| `tabela_ser` | `xsd:string` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `data_atual` | `xsd:date` | true | 0..1 |
| `inic_oper` | `xsd:date` | true | 0..1 |
| `pot_fisc_k` | `xsd:decimal` | true | 0..1 |
| `cod_uph` | `xsd:decimal` | true | 0..1 |
| `id_empreen` | `xsd:decimal` | true | 0..1 |
| `lat_eixo_d` | `xsd:decimal` | true | 0..1 |
| `long_eixo1` | `xsd:decimal` | true | 0..1 |
| `tipo_ahe` | `xsd:string` | true | 0..1 |
| `reg_mens` | `xsd:string` | true | 0..1 |
| `rn_696_15` | `xsd:string` | true | 0..1 |
| `fase` | `xsd:string` | true | 0..1 |
| `versao_atu` | `xsd:string` | true | 0..1 |
| `legend` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Base_de_Dados_Geografica_da_Distribuidora_BDGD:mg_distribuidoras_energia_aneel_pl_dez_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nm_municip` | `xsd:string` | true | 0..1 |
| `cd_geocmu` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `nm_estado` | `xsd:string` | true | 0..1 |
| `sigla_auto` | `xsd:string` | true | 0..1 |
| `pop_2010` | `xsd:decimal` | true | 0..1 |
| `estpop_201` | `xsd:decimal` | true | 0..1 |
| `area_ibge_` | `xsd:decimal` | true | 0..1 |
| `tipo_2` | `xsd:string` | true | 0..1 |
| `dist_2` | `xsd:int` | true | 0..1 |
| `sigla_2` | `xsd:string` | true | 0..1 |
| `tipo_3` | `xsd:string` | true | 0..1 |
| `dist_3` | `xsd:int` | true | 0..1 |
| `sigla_3` | `xsd:string` | true | 0..1 |
| `nuc_1` | `xsd:decimal` | true | 0..1 |
| `nuc_2` | `xsd:decimal` | true | 0..1 |
| `nuc_3` | `xsd:decimal` | true | 0..1 |
| `dist_autor` | `xsd:decimal` | true | 0..1 |
| `tipo_1` | `xsd:string` | true | 0..1 |
| `dist_1` | `xsd:int` | true | 0..1 |
| `sigla_1` | `xsd:string` | true | 0..1 |
| `pop_1` | `xsd:decimal` | true | 0..1 |
| `pop_2` | `xsd:decimal` | true | 0..1 |
| `pop_3` | `xsd:decimal` | true | 0..1 |
| `outras_dis` | `xsd:string` | true | 0..1 |
| `nuc_outras` | `xsd:decimal` | true | 0..1 |
| `pop_outras` | `xsd:decimal` | true | 0..1 |
| `nuc` | `xsd:decimal` | true | 0..1 |
| `shape_star` | `xsd:decimal` | true | 0..1 |
| `shape_stle` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Base_de_Dados_Geografica_da_Distribuidora_BDGD:mg_linhas_transmissao_aneel_ln_dez_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome` | `xsd:string` | true | 0..1 |
| `concession` | `xsd:string` | true | 0..1 |
| `tensao` | `xsd:decimal` | true | 0..1 |
| `extensao` | `xsd:decimal` | true | 0..1 |
| `ano_opera` | `xsd:int` | true | 0..1 |
| `created_us` | `xsd:string` | true | 0..1 |
| `created_da` | `xsd:date` | true | 0..1 |
| `last_edite` | `xsd:string` | true | 0..1 |
| `last_edi_1` | `xsd:date` | true | 0..1 |
| `shape_stle` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Base_de_Dados_Geografica_da_Distribuidora_BDGD:mg_pequenas_centrais_hidreletricas_aneel_pt_dez_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome` | `xsd:string` | true | 0..1 |
| `proprietar` | `xsd:string` | true | 0..1 |
| `cnpj` | `xsd:string` | true | 0..1 |
| `ceg` | `xsd:string` | true | 0..1 |
| `munic_cf` | `xsd:string` | true | 0..1 |
| `uf_cf` | `xsd:string` | true | 0..1 |
| `munic_1` | `xsd:string` | true | 0..1 |
| `uf_1` | `xsd:string` | true | 0..1 |
| `munic_2` | `xsd:string` | true | 0..1 |
| `uf_2` | `xsd:string` | true | 0..1 |
| `rio` | `xsd:string` | true | 0..1 |
| `cod_bac` | `xsd:decimal` | true | 0..1 |
| `cod_sbac` | `xsd:decimal` | true | 0..1 |
| `dsp_inv` | `xsd:string` | true | 0..1 |
| `ato_legal` | `xsd:string` | true | 0..1 |
| `proc_aneel` | `xsd:string` | true | 0..1 |
| `lat_eixo_g` | `xsd:string` | true | 0..1 |
| `long_eixo_` | `xsd:string` | true | 0..1 |
| `lat_cf_gms` | `xsd:string` | true | 0..1 |
| `long_cf_gm` | `xsd:string` | true | 0..1 |
| `pot_kw` | `xsd:decimal` | true | 0..1 |
| `n_unid_ger` | `xsd:int` | true | 0..1 |
| `pot_uni_ge` | `xsd:decimal` | true | 0..1 |
| `fator_pot` | `xsd:decimal` | true | 0..1 |
| `pot_por_tu` | `xsd:decimal` | true | 0..1 |
| `eng_min` | `xsd:decimal` | true | 0..1 |
| `tipo_turb` | `xsd:string` | true | 0..1 |
| `rend_nom_t` | `xsd:decimal` | true | 0..1 |
| `rend_nom_g` | `xsd:decimal` | true | 0..1 |
| `tx_eq_inds` | `xsd:decimal` | true | 0..1 |
| `inds_prog` | `xsd:decimal` | true | 0..1 |
| `perd_hid_n` | `xsd:decimal` | true | 0..1 |
| `na_max_max` | `xsd:decimal` | true | 0..1 |
| `na_max_mon` | `xsd:decimal` | true | 0..1 |
| `na_min_mon` | `xsd:decimal` | true | 0..1 |
| `na_nor_jus` | `xsd:decimal` | true | 0..1 |
| `area_na_ma` | `xsd:decimal` | true | 0..1 |
| `area_na_mi` | `xsd:decimal` | true | 0..1 |
| `area_dren` | `xsd:decimal` | true | 0..1 |
| `vol_na_max` | `xsd:decimal` | true | 0..1 |
| `vol_na_min` | `xsd:decimal` | true | 0..1 |
| `qd_bruta_n` | `xsd:decimal` | true | 0..1 |
| `perdas_ele` | `xsd:decimal` | true | 0..1 |
| `cons_inter` | `xsd:decimal` | true | 0..1 |
| `vazao_rem` | `xsd:decimal` | true | 0..1 |
| `vazao_uso_` | `xsd:decimal` | true | 0..1 |
| `vazao_proj` | `xsd:decimal` | true | 0..1 |
| `serie_vaza` | `xsd:string` | true | 0..1 |
| `tabela_ser` | `xsd:string` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `data_atual` | `xsd:date` | true | 0..1 |
| `inic_oper` | `xsd:date` | true | 0..1 |
| `pot_fisc_k` | `xsd:decimal` | true | 0..1 |
| `cod_uph` | `xsd:decimal` | true | 0..1 |
| `id_empreen` | `xsd:decimal` | true | 0..1 |
| `lat_eixo_d` | `xsd:decimal` | true | 0..1 |
| `long_eixo1` | `xsd:decimal` | true | 0..1 |
| `tipo_ahe` | `xsd:string` | true | 0..1 |
| `reg_mens` | `xsd:string` | true | 0..1 |
| `rn_696_15` | `xsd:string` | true | 0..1 |
| `fase` | `xsd:string` | true | 0..1 |
| `versao_atu` | `xsd:string` | true | 0..1 |
| `legend` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Base_de_Dados_Geografica_da_Distribuidora_BDGD:mg_ponto_notaveis_aneel_pt_dez_2020_gdb`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `COD_ID` | `xsd:string` | true | 0..1 |
| `DIST` | `xsd:int` | true | 0..1 |
| `TIP_PN` | `xsd:string` | true | 0..1 |
| `POS` | `xsd:string` | true | 0..1 |
| `ESTR` | `xsd:string` | true | 0..1 |
| `MAT` | `xsd:string` | true | 0..1 |
| `ESF` | `xsd:string` | true | 0..1 |
| `ALT` | `xsd:string` | true | 0..1 |
| `CONJ` | `xsd:int` | true | 0..1 |
| `MUN` | `xsd:string` | true | 0..1 |
| `ODI` | `xsd:string` | true | 0..1 |
| `TI` | `xsd:string` | true | 0..1 |
| `CM` | `xsd:string` | true | 0..1 |
| `TUC` | `xsd:string` | true | 0..1 |
| `A1` | `xsd:string` | true | 0..1 |
| `A2` | `xsd:string` | true | 0..1 |
| `A3` | `xsd:string` | true | 0..1 |
| `A4` | `xsd:string` | true | 0..1 |
| `A5` | `xsd:string` | true | 0..1 |
| `A6` | `xsd:string` | true | 0..1 |
| `SITCONT` | `xsd:string` | true | 0..1 |
| `DESCR` | `xsd:string` | true | 0..1 |
| `ARE_LOC` | `xsd:string` | true | 0..1 |
| `DETAILS` | `xsd:string` | true | 0..1 |
| `LEGEND` | `xsd:string` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Base_de_Dados_Geografica_da_Distribuidora_BDGD:mg_usinas_eolicas_aneel_pt_dez_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome` | `xsd:string` | true | 0..1 |
| `codmun` | `xsd:decimal` | true | 0..1 |
| `munic1` | `xsd:string` | true | 0..1 |
| `uf1` | `xsd:string` | true | 0..1 |
| `proc_aneel` | `xsd:string` | true | 0..1 |
| `ato_legal` | `xsd:string` | true | 0..1 |
| `p_out_kw` | `xsd:decimal` | true | 0..1 |
| `p_fisc_kw` | `xsd:decimal` | true | 0..1 |
| `proprietar` | `xsd:string` | true | 0..1 |
| `caminhofot` | `xsd:string` | true | 0..1 |
| `caminhocon` | `xsd:string` | true | 0..1 |
| `data_atual` | `xsd:date` | true | 0..1 |
| `eol_versao` | `xsd:decimal` | true | 0..1 |
| `dro_id_scg` | `xsd:decimal` | true | 0..1 |
| `long_gms` | `xsd:string` | true | 0..1 |
| `lat_gms` | `xsd:string` | true | 0..1 |
| `nomes_eol_` | `xsd:string` | true | 0..1 |
| `dro_data` | `xsd:date` | true | 0..1 |
| `id_lt` | `xsd:decimal` | true | 0..1 |
| `id_se` | `xsd:decimal` | true | 0..1 |
| `id_est` | `xsd:string` | true | 0..1 |
| `dro_dt_vig` | `xsd:date` | true | 0..1 |
| `ceg` | `xsd:string` | true | 0..1 |
| `id_empreen` | `xsd:decimal` | true | 0..1 |
| `lat_dec` | `xsd:decimal` | true | 0..1 |
| `long_dec` | `xsd:decimal` | true | 0..1 |
| `qtd_aeg` | `xsd:decimal` | true | 0..1 |
| `inicio_ope` | `xsd:date` | true | 0..1 |
| `fase` | `xsd:string` | true | 0..1 |
| `validacao` | `xsd:string` | true | 0..1 |
| `fuso` | `xsd:string` | true | 0..1 |
| `datum_emp` | `xsd:string` | true | 0..1 |
| `tipo_exp` | `xsd:string` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `legend` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Base_de_Dados_Geografica_da_Distribuidora_BDGD:mg_usinas_fotovoltaicas_aneel_pt_dez_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome` | `xsd:string` | true | 0..1 |
| `proprietar` | `xsd:string` | true | 0..1 |
| `cnpj` | `xsd:string` | true | 0..1 |
| `ceg` | `xsd:string` | true | 0..1 |
| `munic` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `ato_legal` | `xsd:string` | true | 0..1 |
| `proc_aneel` | `xsd:string` | true | 0..1 |
| `pot_kw` | `xsd:decimal` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `data_atual` | `xsd:date` | true | 0..1 |
| `inic_oper` | `xsd:date` | true | 0..1 |
| `pot_fisc_k` | `xsd:decimal` | true | 0..1 |
| `codmun` | `xsd:decimal` | true | 0..1 |
| `lat_gms` | `xsd:string` | true | 0..1 |
| `long_gms` | `xsd:string` | true | 0..1 |
| `id_empreen` | `xsd:decimal` | true | 0..1 |
| `lat_dec` | `xsd:decimal` | true | 0..1 |
| `long_dec` | `xsd:decimal` | true | 0..1 |
| `estagio_ge` | `xsd:string` | true | 0..1 |
| `combustive` | `xsd:string` | true | 0..1 |
| `datum` | `xsd:string` | true | 0..1 |
| `tipo_explo` | `xsd:string` | true | 0..1 |
| `fase_usina` | `xsd:string` | true | 0..1 |
| `classe_com` | `xsd:string` | true | 0..1 |
| `fonte_comb` | `xsd:string` | true | 0..1 |
| `oper_com` | `xsd:string` | true | 0..1 |
| `legend` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Base_de_Dados_Geografica_da_Distribuidora_BDGD:mg_usinas_hidreletricas_aneel_pt_dez_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome` | `xsd:string` | true | 0..1 |
| `proprietar` | `xsd:string` | true | 0..1 |
| `cnpj` | `xsd:string` | true | 0..1 |
| `ceg` | `xsd:string` | true | 0..1 |
| `munic_cf` | `xsd:string` | true | 0..1 |
| `uf_cf` | `xsd:string` | true | 0..1 |
| `munic_1` | `xsd:string` | true | 0..1 |
| `uf_1` | `xsd:string` | true | 0..1 |
| `munic_2` | `xsd:string` | true | 0..1 |
| `uf_2` | `xsd:string` | true | 0..1 |
| `rio` | `xsd:string` | true | 0..1 |
| `cod_bac` | `xsd:decimal` | true | 0..1 |
| `cod_sbac` | `xsd:decimal` | true | 0..1 |
| `dsp_inv` | `xsd:string` | true | 0..1 |
| `ato_legal` | `xsd:string` | true | 0..1 |
| `proc_aneel` | `xsd:string` | true | 0..1 |
| `lat_eixo_g` | `xsd:string` | true | 0..1 |
| `long_eixo_` | `xsd:string` | true | 0..1 |
| `lat_cf_gms` | `xsd:string` | true | 0..1 |
| `long_cf_gm` | `xsd:string` | true | 0..1 |
| `pot_kw` | `xsd:decimal` | true | 0..1 |
| `n_unid_ger` | `xsd:int` | true | 0..1 |
| `pot_uni_ge` | `xsd:decimal` | true | 0..1 |
| `fator_pot` | `xsd:decimal` | true | 0..1 |
| `pot_por_tu` | `xsd:decimal` | true | 0..1 |
| `eng_min` | `xsd:decimal` | true | 0..1 |
| `tipo_turb` | `xsd:string` | true | 0..1 |
| `rend_nom_t` | `xsd:decimal` | true | 0..1 |
| `rend_nom_g` | `xsd:decimal` | true | 0..1 |
| `tx_eq_inds` | `xsd:decimal` | true | 0..1 |
| `inds_prog` | `xsd:decimal` | true | 0..1 |
| `perd_hid_n` | `xsd:decimal` | true | 0..1 |
| `na_max_max` | `xsd:decimal` | true | 0..1 |
| `na_max_mon` | `xsd:decimal` | true | 0..1 |
| `na_min_mon` | `xsd:decimal` | true | 0..1 |
| `na_nor_jus` | `xsd:decimal` | true | 0..1 |
| `area_na_ma` | `xsd:decimal` | true | 0..1 |
| `area_na_mi` | `xsd:decimal` | true | 0..1 |
| `area_dren` | `xsd:decimal` | true | 0..1 |
| `vol_na_max` | `xsd:decimal` | true | 0..1 |
| `vol_na_min` | `xsd:decimal` | true | 0..1 |
| `qd_bruta_n` | `xsd:decimal` | true | 0..1 |
| `perdas_ele` | `xsd:decimal` | true | 0..1 |
| `cons_inter` | `xsd:decimal` | true | 0..1 |
| `vazao_rem` | `xsd:decimal` | true | 0..1 |
| `vazao_uso_` | `xsd:decimal` | true | 0..1 |
| `vazao_proj` | `xsd:decimal` | true | 0..1 |
| `serie_vaza` | `xsd:string` | true | 0..1 |
| `tabela_ser` | `xsd:string` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `data_atual` | `xsd:date` | true | 0..1 |
| `inic_oper` | `xsd:date` | true | 0..1 |
| `pot_fisc_k` | `xsd:decimal` | true | 0..1 |
| `cod_uph` | `xsd:decimal` | true | 0..1 |
| `id_empreen` | `xsd:decimal` | true | 0..1 |
| `lat_eixo_d` | `xsd:decimal` | true | 0..1 |
| `long_eixo1` | `xsd:decimal` | true | 0..1 |
| `tipo_ahe` | `xsd:string` | true | 0..1 |
| `reg_mens` | `xsd:string` | true | 0..1 |
| `rn_696_15` | `xsd:string` | true | 0..1 |
| `fase` | `xsd:string` | true | 0..1 |
| `versao_atu` | `xsd:string` | true | 0..1 |
| `legend` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Base_de_Dados_Geografica_da_Distribuidora_BDGD:mg_usinas_termeletricas_aneel_pt_dez_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome` | `xsd:string` | true | 0..1 |
| `proprietar` | `xsd:string` | true | 0..1 |
| `cnpj` | `xsd:string` | true | 0..1 |
| `ceg` | `xsd:string` | true | 0..1 |
| `munic` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `ato_legal` | `xsd:string` | true | 0..1 |
| `proc_aneel` | `xsd:string` | true | 0..1 |
| `pot_kw` | `xsd:decimal` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `data_atual` | `xsd:date` | true | 0..1 |
| `inic_oper` | `xsd:date` | true | 0..1 |
| `pot_fisc_k` | `xsd:decimal` | true | 0..1 |
| `codmun` | `xsd:decimal` | true | 0..1 |
| `lat_gms` | `xsd:string` | true | 0..1 |
| `long_gms` | `xsd:string` | true | 0..1 |
| `id_empreen` | `xsd:decimal` | true | 0..1 |
| `lat_dec` | `xsd:decimal` | true | 0..1 |
| `long_dec` | `xsd:decimal` | true | 0..1 |
| `estagio_ge` | `xsd:string` | true | 0..1 |
| `combustive` | `xsd:string` | true | 0..1 |
| `datum` | `xsd:string` | true | 0..1 |
| `tipo_explo` | `xsd:string` | true | 0..1 |
| `fase_usina` | `xsd:string` | true | 0..1 |
| `classe_com` | `xsd:string` | true | 0..1 |
| `fonte_comb` | `xsd:string` | true | 0..1 |
| `oper_com` | `xsd:string` | true | 0..1 |
| `legend` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

## DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Clima (2)

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Clima:mg_classificacao_koppen_jan_2017`

> [!warning] Schema pendente
> Este esquema ainda não foi resolvido nesta coleta. Reconsulte o endpoint antes de usar a camada.


### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Clima:mg_estacoes_inmet_pt_mai_2024`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `estacao` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `altitude` | `xsd:double` | true | 0..1 |
| `inicio_op` | `xsd:date` | true | 0..1 |

## DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Defesa_Civil (7)

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Defesa_Civil:mg_barragens_rejeitos_residuos_cedec_pt_jun_2024`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `REF` | `xsd:int` | true | 0..1 |
| `FID_1` | `xsd:double` | true | 0..1 |
| `Barragens` | `xsd:string` | true | 0..1 |
| `Municipio` | `xsd:string` | true | 0..1 |
| `Org_Est` | `xsd:string` | true | 0..1 |
| `Org_Fed` | `xsd:string` | true | 0..1 |
| `Finalidade` | `xsd:string` | true | 0..1 |
| `Categoria` | `xsd:string` | true | 0..1 |
| `Pot_Dano` | `xsd:string` | true | 0..1 |
| `Empresa` | `xsd:string` | true | 0..1 |
| `Codigo_Ba` | `xsd:double` | true | 0..1 |
| `Possui_PAE` | `xsd:string` | true | 0..1 |
| `Possui_Pla` | `xsd:string` | true | 0..1 |
| `Data_da_Ú` | `xsd:date` | true | 0..1 |
| `Barragem_A` | `xsd:string` | true | 0..1 |
| `T_Material` | `xsd:string` | true | 0..1 |
| `Uso_Comple` | `xsd:string` | true | 0..1 |
| `Cl_Barrage` | `xsd:string` | true | 0..1 |
| `Curso_Dagu` | `xsd:string` | true | 0..1 |
| `Reg_Hidro` | `xsd:string` | true | 0..1 |
| `Bacia` | `xsd:string` | true | 0..1 |
| `Data_da__1` | `xsd:date` | true | 0..1 |
| `Tipo_da_Ú` | `xsd:string` | true | 0..1 |
| `Fase_da_Vi` | `xsd:string` | true | 0..1 |
| `Fase_da__1` | `xsd:string` | true | 0..1 |
| `Latitude` | `xsd:double` | true | 0..1 |
| `Longitude` | `xsd:double` | true | 0..1 |
| `Completude` | `xsd:string` | true | 0..1 |
| `Data` | `xsd:date` | true | 0..1 |
| `Legend` | `xsd:string` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Defesa_Civil:mg_municipios_compdec_cedec_pl_jun_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `CD_MUN` | `xsd:string` | true | 0..1 |
| `NM_MUN` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `DESC_` | `xsd:string` | true | 0..1 |
| `ÓRGÃO` | `xsd:string` | true | 0..1 |
| `AREA_KM²` | `xsd:double` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Defesa_Civil:mg_municipios_operacao_pipa_cedec_pl_jun_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `CD_MUN` | `xsd:string` | true | 0..1 |
| `Item` | `xsd:double` | true | 0..1 |
| `Nome` | `xsd:string` | true | 0..1 |
| `Município` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `Descriçã` | `xsd:string` | true | 0..1 |
| `AREA_Km²` | `xsd:double` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Defesa_Civil:mg_municipios_pad_cedec_pl_jun_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `REF` | `xsd:int` | true | 0..1 |
| `FID_1` | `xsd:double` | true | 0..1 |
| `CD_MUN` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `ÓRGÃO` | `xsd:string` | true | 0..1 |
| `DESC_` | `xsd:string` | true | 0..1 |
| `NM_MUN` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `AREA_KM²` | `xsd:double` | true | 0..1 |
| `Penden` | `xsd:string` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Defesa_Civil:mg_municipios_plancon_cedec_pl_jun_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `CD_MUN` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `DESC_` | `xsd:string` | true | 0..1 |
| `ÓRGÃO` | `xsd:string` | true | 0..1 |
| `NM_MUN` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `AREA_KM²` | `xsd:double` | true | 0..1 |
| `Plancon` | `xsd:string` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Defesa_Civil:mg_municipios_programa_captacao_cedec_pl_jun_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `CD_MUN` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |
| `ÓRGÃO` | `xsd:string` | true | 0..1 |
| `NOME_DO_PR` | `xsd:string` | true | 0..1 |
| `MUNICIPIO` | `xsd:string` | true | 0..1 |
| `COMUNIDADE` | `xsd:string` | true | 0..1 |
| `DESC_` | `xsd:string` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Defesa_Civil:mg_redecs_cedec_pl_jun_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `CD_MUN` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |
| `REDEC` | `xsd:string` | true | 0..1 |
| `QtdEv_Extr` | `xsd:long` | true | 0..1 |
| `REDEC_NUM` | `xsd:long` | true | 0..1 |

## DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Desenvolvimento_Social (2)

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Desenvolvimento_Social:mg_cras_sedese_pt_05_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `Sigla` | `xsd:string` | true | 0..1 |
| `Nome` | `xsd:string` | true | 0..1 |
| `Entidade` | `xsd:string` | true | 0..1 |
| `Município` | `xsd:string` | true | 0..1 |
| `Rua` | `xsd:string` | true | 0..1 |
| `Nº` | `xsd:double` | true | 0..1 |
| `Bairro` | `xsd:string` | true | 0..1 |
| `CEP` | `xsd:double` | true | 0..1 |
| `UF` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Desenvolvimento_Social:mg_creas_sedese_pt_05_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `Sigla` | `xsd:string` | true | 0..1 |
| `Nome` | `xsd:string` | true | 0..1 |
| `Órgão` | `xsd:string` | true | 0..1 |
| `Município` | `xsd:string` | true | 0..1 |
| `Rua` | `xsd:string` | true | 0..1 |
| `Nº` | `xsd:double` | true | 0..1 |
| `Bairro` | `xsd:string` | true | 0..1 |
| `CEP` | `xsd:string` | true | 0..1 |
| `UF` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |

## DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Desmatamento (1)

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Desmatamento:mg_area_acu_sup_veg_nat_biomas_prodes_pl_jun_set_2000_2016`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `main_class` | `xsd:string` | true | 0..1 |
| `image_date` | `xsd:date` | true | 0..1 |
| `area_km` | `xsd:double` | true | 0..1 |
| `source` | `xsd:string` | true | 0..1 |
| `sensor` | `xsd:string` | true | 0..1 |
| `year` | `xsd:long` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |

## DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Economia (3)

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Economia:mg_municipios_agroexportadores_fjp_pl_abr_2026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `GEOCODIGO` | `xsd:string` | true | 0..1 |
| `MUNICIPIO` | `xsd:string` | true | 0..1 |
| `AREA_KM` | `xsd:decimal` | true | 0..1 |
| `INSUMO` | `xsd:string` | true | 0..1 |
| `US_million` | `xsd:decimal` | true | 0..1 |
| `US_MI` | `xsd:string` | true | 0..1 |
| `ANO_BASE` | `xsd:decimal` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Economia:mg_processos_minerarios_amn_pl_abr_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `PROCESSO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:int` | true | 0..1 |
| `ANO` | `xsd:int` | true | 0..1 |
| `AREA_HA` | `xsd:double` | true | 0..1 |
| `ID` | `xsd:string` | true | 0..1 |
| `FASE` | `xsd:string` | true | 0..1 |
| `ULT_EVENTO` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `SUBS` | `xsd:string` | true | 0..1 |
| `USO` | `xsd:string` | true | 0..1 |
| `UF` | `xsd:string` | true | 0..1 |
| `DSProcesso` | `xsd:string` | true | 0..1 |
| `DECADA` | `xsd:string` | true | 0..1 |
| `REGIME` | `xsd:string` | true | 0..1 |
| `SUBS_AGRUP` | `xsd:string` | true | 0..1 |
| `SUBCLASSE` | `xsd:string` | true | 0..1 |
| `CLASSE` | `xsd:string` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Economia:mg_terra_rara_codemge_pt_mai_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `TOPONÍMIA` | `xsd:string` | true | 0..1 |
| `MUNICÍPIO` | `xsd:string` | true | 0..1 |
| `STATUS_ECO` | `xsd:string` | true | 0..1 |
| `SITUAÇÃO` | `xsd:string` | true | 0..1 |
| `LATITUDE` | `xsd:double` | true | 0..1 |
| `LONGITUDE` | `xsd:double` | true | 0..1 |
| `LEGENDA` | `xsd:string` | true | 0..1 |

## DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Educação (2)

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Educação:mg_escola_inep_pt_mai_2026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `REST` | `xsd:string` | true | 0..1 |
| `ESCOLA` | `xsd:string` | true | 0..1 |
| `COD_INEP` | `xsd:long` | true | 0..1 |
| `UF` | `xsd:string` | true | 0..1 |
| `MUN` | `xsd:string` | true | 0..1 |
| `LOCAL_` | `xsd:string` | true | 0..1 |
| `TIPO_LOC` | `xsd:string` | true | 0..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `END_` | `xsd:string` | true | 0..1 |
| `CEP` | `xsd:string` | true | 0..1 |
| `TEL` | `xsd:string` | true | 0..1 |
| `DEP_ADM` | `xsd:string` | true | 0..1 |
| `CAT_PRIV` | `xsd:string` | true | 0..1 |
| `CONV_PUB` | `xsd:string` | true | 0..1 |
| `REG_EDUC` | `xsd:string` | true | 0..1 |
| `PORT` | `xsd:string` | true | 0..1 |
| `MOD_ENSINO` | `xsd:string` | true | 0..1 |
| `OF_EDUC` | `xsd:string` | true | 0..1 |
| `LAT` | `xsd:double` | true | 0..1 |
| `LONG_` | `xsd:double` | true | 0..1 |
| `LEGEND` | `xsd:string` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Educação:mg_escolas_tecnicas_mec_pt_mai_2026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `UNIDADE` | `xsd:string` | true | 0..1 |
| `REDE` | `xsd:string` | true | 0..1 |
| `LAT` | `xsd:string` | true | 0..1 |
| `LONG` | `xsd:string` | true | 0..1 |
| `Y` | `xsd:double` | true | 0..1 |
| `X` | `xsd:double` | true | 0..1 |

## DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Hidrografia (5)

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Hidrografia:mg_bacia_hidrografica_ana_pl_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `codogootto` | `xsd:long` | true | 0..1 |
| `nivelotto` | `xsd:string` | true | 0..1 |
| `nomeabrev` | `xsd:string` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Hidrografia:mg_hidrografia_ana_ln_mar_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `fid_1` | `xsd:double` | true | 0..1 |
| `drn_pk` | `xsd:long` | true | 0..1 |
| `cotrecho` | `xsd:long` | true | 0..1 |
| `noorigem` | `xsd:long` | true | 0..1 |
| `nodestino` | `xsd:long` | true | 0..1 |
| `cocursodag` | `xsd:string` | true | 0..1 |
| `cobacia` | `xsd:string` | true | 0..1 |
| `nucomptrec` | `xsd:double` | true | 0..1 |
| `nudistbact` | `xsd:double` | true | 0..1 |
| `nudistcdag` | `xsd:double` | true | 0..1 |
| `nuareacont` | `xsd:double` | true | 0..1 |
| `nuareamont` | `xsd:double` | true | 0..1 |
| `nogenerico` | `xsd:string` | true | 0..1 |
| `noligacao` | `xsd:string` | true | 0..1 |
| `noespecif` | `xsd:string` | true | 0..1 |
| `noriocomp` | `xsd:string` | true | 0..1 |
| `nooriginal` | `xsd:string` | true | 0..1 |
| `cocdadesag` | `xsd:string` | true | 0..1 |
| `nutrjus` | `xsd:long` | true | 0..1 |
| `nudistbacc` | `xsd:double` | true | 0..1 |
| `nuareabacc` | `xsd:double` | true | 0..1 |
| `nuordemcda` | `xsd:long` | true | 0..1 |
| `nucompcda` | `xsd:double` | true | 0..1 |
| `nunivotto` | `xsd:long` | true | 0..1 |
| `nunivotcda` | `xsd:long` | true | 0..1 |
| `nustrahler` | `xsd:long` | true | 0..1 |
| `dedominial` | `xsd:string` | true | 0..1 |
| `dsversao` | `xsd:string` | true | 0..1 |
| `legend` | `xsd:string` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Hidrografia:mg_ish_ana_pl_dez_2035`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `ace_cd` | `xsd:string` | true | 0..1 |
| `ire_cs_amb` | `xsd:double` | true | 0..1 |
| `ire_cs_hum` | `xsd:double` | true | 0..1 |
| `ire_cs_eco` | `xsd:double` | true | 0..1 |
| `ire_cs_res` | `xsd:double` | true | 0..1 |
| `ire_cs_ish` | `xsd:double` | true | 0..1 |
| `ish_bra_gr` | `xsd:string` | true | 0..1 |
| `gr_ish_amb` | `xsd:string` | true | 0..1 |
| `gr_ish_hum` | `xsd:string` | true | 0..1 |
| `gr_ish_eco` | `xsd:string` | true | 0..1 |
| `gr_ish_res` | `xsd:string` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Hidrografia:mg_massa_dagua_ana_igam_pl_set_2021`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:double` | true | 0..1 |
| `objectid` | `xsd:decimal` | true | 0..1 |
| `fid_geoft_` | `xsd:decimal` | true | 0..1 |
| `__gid` | `xsd:decimal` | true | 0..1 |
| `esp_cd` | `xsd:decimal` | true | 0..1 |
| `cod_snisb` | `xsd:decimal` | true | 0..1 |
| `cod_sar` | `xsd:decimal` | true | 0..1 |
| `nmoriginal` | `xsd:string` | true | 0..1 |
| `nmalternat` | `xsd:string` | true | 0..1 |
| `nmgenerico` | `xsd:string` | true | 0..1 |
| `nmligacao` | `xsd:string` | true | 0..1 |
| `nmespecifi` | `xsd:string` | true | 0..1 |
| `detipomass` | `xsd:string` | true | 0..1 |
| `dedominial` | `xsd:string` | true | 0..1 |
| `dedominio` | `xsd:string` | true | 0..1 |
| `defiscaliz` | `xsd:string` | true | 0..1 |
| `nmemp` | `xsd:string` | true | 0..1 |
| `fonmemp` | `xsd:string` | true | 0..1 |
| `dtreserv` | `xsd:string` | true | 0..1 |
| `fodtreserv` | `xsd:string` | true | 0..1 |
| `nuvolumhm3` | `xsd:decimal` | true | 0..1 |
| `fonuvolume` | `xsd:string` | true | 0..1 |
| `nuperimkm` | `xsd:decimal` | true | 0..1 |
| `nuareakm2` | `xsd:decimal` | true | 0..1 |
| `nuareaha` | `xsd:decimal` | true | 0..1 |
| `nucompgeom` | `xsd:decimal` | true | 0..1 |
| `usoprinc` | `xsd:string` | true | 0..1 |
| `fousoprinc` | `xsd:string` | true | 0..1 |
| `detipoapr` | `xsd:string` | true | 0..1 |
| `detipomda` | `xsd:string` | true | 0..1 |
| `salinidade` | `xsd:string` | true | 0..1 |
| `regime` | `xsd:string` | true | 0..1 |
| `nmriocomp` | `xsd:string` | true | 0..1 |
| `nmufe` | `xsd:string` | true | 0..1 |
| `nmmun` | `xsd:string` | true | 0..1 |
| `defonte` | `xsd:string` | true | 0..1 |
| `desatelite` | `xsd:string` | true | 0..1 |
| `deversao` | `xsd:string` | true | 0..1 |
| `deobs` | `xsd:string` | true | 0..1 |
| `nuvzreg` | `xsd:decimal` | true | 0..1 |
| `nuvzlago` | `xsd:decimal` | true | 0..1 |
| `nuvzdeflu` | `xsd:decimal` | true | 0..1 |
| `cdtipooper` | `xsd:decimal` | true | 0..1 |
| `detipooper` | `xsd:string` | true | 0..1 |
| `fovzlago` | `xsd:string` | true | 0..1 |
| `fovzdeflu` | `xsd:string` | true | 0..1 |
| `fovzreg` | `xsd:string` | true | 0..1 |
| `cobarprin` | `xsd:decimal` | true | 0..1 |
| `cotrecho` | `xsd:decimal` | true | 0..1 |
| `nuvzrecebe` | `xsd:decimal` | true | 0..1 |
| `nuvztransf` | `xsd:decimal` | true | 0..1 |
| `deobsvazao` | `xsd:string` | true | 0..1 |
| `cocda2013` | `xsd:string` | true | 0..1 |
| `cocda2017` | `xsd:string` | true | 0..1 |
| `fid_c1104_` | `xsd:decimal` | true | 0..1 |
| `hidro` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Hidrografia:mg_reservatorio_hidrico_ana_jan_2021`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome` | `xsd:string` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `namaximoma` | `xsd:double` | true | 0..1 |
| `usoprincip` | `xsd:string` | true | 0..1 |
| `volumeutil` | `xsd:double` | true | 0..1 |
| `namaximoop` | `xsd:double` | true | 0..1 |
| `nomeabrev` | `xsd:string` | true | 0..1 |
| `hidro` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

## DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Limites (19)

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Limites:mg_area_administracao_fazendaria_fjp_pl_mar_2026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `CODAF` | `xsd:double` | true | 0..1 |
| `R_AF` | `xsd:string` | true | 0..1 |
| `DESC_` | `xsd:string` | true | 0..1 |
| `AREA_KM²` | `xsd:double` | true | 0..1 |
| `LEGEND` | `xsd:string` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Limites:mg_area_batalhao_fjp_pl_mar_2026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `P_BATALHAO` | `xsd:string` | true | 0..1 |
| `DESC_` | `xsd:string` | true | 0..1 |
| `AREA_KM²` | `xsd:double` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Limites:mg_area_camarca_fjp_pl_mar_2026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `P_CODCOM` | `xsd:double` | true | 0..1 |
| `P_COMARCA` | `xsd:string` | true | 0..1 |
| `DESC_` | `xsd:string` | true | 0..1 |
| `AREA_KM²` | `xsd:double` | true | 0..1 |
| `LEGEND` | `xsd:string` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Limites:mg_area_delegacia_fjp_pl_mar_2026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `P_DELEGACI` | `xsd:string` | true | 0..1 |
| `DESC_` | `xsd:string` | true | 0..1 |
| `AREA_KM²` | `xsd:double` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Limites:mg_area_macrorregiao_saude_fjp_pl_mar_2026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `S_CODMACRO` | `xsd:double` | true | 0..1 |
| `S_MACRO` | `xsd:string` | true | 0..1 |
| `DESC_` | `xsd:string` | true | 0..1 |
| `AREA_KM²` | `xsd:double` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Limites:mg_area_microrregiao_saude_fjp_pl_mar_2026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `S_CODMICRO` | `xsd:double` | true | 0..1 |
| `S_MICRO` | `xsd:string` | true | 0..1 |
| `DESC_` | `xsd:string` | true | 0..1 |
| `AREA_KM¹` | `xsd:double` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Limites:mg_area_regiao_planejamento_fjp_pl_mar_2026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `CODPLAN` | `xsd:double` | true | 0..1 |
| `REG_PLAN` | `xsd:string` | true | 0..1 |
| `DESC_` | `xsd:string` | true | 0..1 |
| `AREA_MK²` | `xsd:double` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Limites:mg_area_risp_fjp_pl_mar_2026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `RISP` | `xsd:string` | true | 0..1 |
| `DESC_` | `xsd:string` | true | 0..1 |
| `AREA_KM²` | `xsd:double` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Limites:mg_area_territorio_desenvolvimento_fjp_pl_mar_2026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `CODTERRIT` | `xsd:double` | true | 0..1 |
| `TERRITORIO` | `xsd:string` | true | 0..1 |
| `DESC_` | `xsd:string` | true | 0..1 |
| `AREA_MK²` | `xsd:double` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Limites:mg_area_uso_comunitario_incra_pl_dez_2010`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `auc_cd` | `xsd:decimal` | true | 0..1 |
| `auc_tau_cd` | `xsd:decimal` | true | 0..1 |
| `auc_nm` | `xsd:string` | true | 0..1 |
| `auc_gm_are` | `xsd:decimal` | true | 0..1 |
| `auc_gm_per` | `xsd:decimal` | true | 0..1 |
| `auc_gm_pol` | `xsd:string` | true | 0..1 |
| `incra` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Limites:mg_areas_quilombolas_incra_pl_dez_2010`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cd_quilomb` | `xsd:decimal` | true | 0..1 |
| `cd_sr` | `xsd:string` | true | 0..1 |
| `nr_process` | `xsd:string` | true | 0..1 |
| `nm_comunid` | `xsd:string` | true | 0..1 |
| `nm_municip` | `xsd:string` | true | 0..1 |
| `cd_uf` | `xsd:string` | true | 0..1 |
| `dt_publica` | `xsd:string` | true | 0..1 |
| `dt_public1` | `xsd:string` | true | 0..1 |
| `nr_familia` | `xsd:int` | true | 0..1 |
| `dt_titulac` | `xsd:string` | true | 0..1 |
| `nr_area_ha` | `xsd:decimal` | true | 0..1 |
| `nr_perimet` | `xsd:decimal` | true | 0..1 |
| `cd_sipra` | `xsd:string` | true | 0..1 |
| `ob_descric` | `xsd:string` | true | 0..1 |
| `st_titulad` | `xsd:string` | true | 0..1 |
| `dt_decreto` | `xsd:string` | true | 0..1 |
| `tp_levanta` | `xsd:string` | true | 0..1 |
| `nr_escalao` | `xsd:string` | true | 0..1 |
| `area_calc_` | `xsd:decimal` | true | 0..1 |
| `perimetro_` | `xsd:decimal` | true | 0..1 |
| `esfera` | `xsd:string` | true | 0..1 |
| `fase` | `xsd:string` | true | 0..1 |
| `responsave` | `xsd:string` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Limites:mg_areas_urbanas_populacao_ibge_pl_abr_2021`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `CD_SETOR` | `xsd:string` | true | 0..1 |
| `CD_SIT` | `xsd:string` | true | 0..1 |
| `NM_SIT` | `xsd:string` | true | 0..1 |
| `CD_UF` | `xsd:string` | true | 0..1 |
| `NM_UF` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `CD_MUN` | `xsd:string` | true | 0..1 |
| `NM_MUN` | `xsd:string` | true | 0..1 |
| `CD_DIST` | `xsd:string` | true | 0..1 |
| `NM_DIST` | `xsd:string` | true | 0..1 |
| `CD_SUBDIST` | `xsd:string` | true | 0..1 |
| `NM_SUBDIST` | `xsd:string` | true | 0..1 |
| `v0001` | `xsd:long` | true | 0..1 |
| `v0002` | `xsd:long` | true | 0..1 |
| `v0003` | `xsd:long` | true | 0..1 |
| `v0004` | `xsd:long` | true | 0..1 |
| `v0005` | `xsd:double` | true | 0..1 |
| `v0006` | `xsd:double` | true | 0..1 |
| `v0007` | `xsd:long` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Limites:mg_crg_lotes_der_pl_jun_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `ID` | `xsd:int` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:long` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `AREA_M2` | `xsd:double` | true | 0..1 |
| `Regional` | `xsd:string` | true | 0..1 |
| `RG` | `xsd:string` | true | 0..1 |
| `DECS` | `xsd:string` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Limites:mg_mesorregiao_ibge_pl_mar_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cd_meso` | `xsd:string` | true | 0..1 |
| `nm_meso` | `xsd:string` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `area_km2` | `xsd:double` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Limites:mg_microrregiao_ibge_pl_mar_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cd_micro` | `xsd:string` | true | 0..1 |
| `nm_micro` | `xsd:string` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `area_km2` | `xsd:double` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Limites:mg_regiao_geografica_imediata_ibge_pl_mar_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cd_rgi` | `xsd:string` | true | 0..1 |
| `nm_rgi` | `xsd:string` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `area_km2` | `xsd:double` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Limites:mg_regiao_geografica_intermediaria_ibge_pl_mar_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cd_rgint` | `xsd:string` | true | 0..1 |
| `nm_rgint` | `xsd:string` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `area_km2` | `xsd:double` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Limites:mg_setores_censitarios_ibge_pl_abr_2021`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cd_setor` | `xsd:string` | true | 0..1 |
| `cd_sit` | `xsd:string` | true | 0..1 |
| `nm_sit` | `xsd:string` | true | 0..1 |
| `cd_uf` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `cd_mun` | `xsd:string` | true | 0..1 |
| `nm_mun` | `xsd:string` | true | 0..1 |
| `cd_dist` | `xsd:string` | true | 0..1 |
| `nm_dist` | `xsd:string` | true | 0..1 |
| `cd_subdist` | `xsd:string` | true | 0..1 |
| `nm_subdist` | `xsd:string` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Limites:mg_terra_indigena_funai_pl_fev_2023`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `__gid` | `xsd:int` | true | 0..1 |
| `terrai_cod` | `xsd:int` | true | 0..1 |
| `terrai_nom` | `xsd:string` | true | 0..1 |
| `etnia_nome` | `xsd:string` | true | 0..1 |
| `municipio_` | `xsd:string` | true | 0..1 |
| `uf_sigla` | `xsd:string` | true | 0..1 |
| `superficie` | `xsd:decimal` | true | 0..1 |
| `fase_ti` | `xsd:string` | true | 0..1 |
| `modalidade` | `xsd:string` | true | 0..1 |
| `reestudo_t` | `xsd:string` | true | 0..1 |
| `cr` | `xsd:string` | true | 0..1 |
| `faixa_fron` | `xsd:string` | true | 0..1 |
| `undadm_cod` | `xsd:decimal` | true | 0..1 |
| `undadm_nom` | `xsd:string` | true | 0..1 |
| `undadm_sig` | `xsd:string` | true | 0..1 |
| `dominio_un` | `xsd:string` | true | 0..1 |
| `data_atual` | `xsd:string` | true | 0..1 |
| `epsg` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

## DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Localidades (1)

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Localidades:mg_cidade_fjp_pt_ago_2017`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome` | `xsd:string` | true | 0..1 |
| `geocodigo` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:double` | true | 0..1 |
| `long` | `xsd:double` | true | 0..1 |
| `nomecarta` | `xsd:string` | true | 0..1 |
| `escalacart` | `xsd:int` | true | 0..1 |
| `fuso` | `xsd:string` | true | 0..1 |
| `meridcentr` | `xsd:string` | true | 0..1 |
| `cidade` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

## DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Meio_Ambiente (5)

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Meio_Ambiente:mg_biomas_prodes_brasil_pl_dez_2021`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `cd_bioma` | `xsd:double` | true | 0..1 |
| `area_km` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Meio_Ambiente:mg_cobertura_uso_da_terra_ibge_pl_dez_2000_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `class` | `xsd:string` | true | 0..1 |
| `Area_ha` | `xsd:double` | true | 0..1 |
| `USO2000` | `xsd:double` | true | 0..1 |
| `USO2010` | `xsd:double` | true | 0..1 |
| `USO2012` | `xsd:double` | true | 0..1 |
| `USO2014` | `xsd:double` | true | 0..1 |
| `USO2016` | `xsd:double` | true | 0..1 |
| `USO2018` | `xsd:double` | true | 0..1 |
| `USO2020` | `xsd:double` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Meio_Ambiente:mg_inventario_florestal_ief_pl_jul_2009`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `class_name` | `xsd:string` | true | 0..1 |
| `class_id` | `xsd:long` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Meio_Ambiente:mg_reg_fito_ibge_pl_mar_2026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `cd_fito` | `xsd:string` | true | 0..1 |
| `legenda_1` | `xsd:string` | true | 0..1 |
| `area_km2` | `xsd:double` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Meio_Ambiente:mg_uso_cobertura_mapbiomas_colecao_10_pl_dez_2024`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `gridcode` | `xsd:int` | true | 0..1 |
| `Code_ID` | `xsd:double` | true | 0..1 |
| `Colecao_10` | `xsd:string` | true | 0..1 |
| `Collection_10` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |
| `Area_Total` | `xsd:double` | true | 0..1 |
| `Area_km²` | `xsd:double` | true | 0..1 |
| `Percentual` | `xsd:double` | true | 0..1 |

## DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Políticas_Públicas (2)

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Políticas_Públicas:mg_cidades_futuro_sede_pl_jun_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `code_muni` | `xsd:string` | true | 0..1 |
| `name_muni` | `xsd:string` | true | 0..1 |
| `cod_estado` | `xsd:double` | true | 0..1 |
| `sigla` | `xsd:string` | true | 0..1 |
| `estado` | `xsd:string` | true | 0..1 |
| `cod_regiao` | `xsd:double` | true | 0..1 |
| `name_regia` | `xsd:string` | true | 0..1 |
| `cid_do_fut` | `xsd:string` | true | 0..1 |
| `reurb` | `xsd:string` | true | 0..1 |
| `reurb_resp` | `xsd:string` | true | 0..1 |
| `mat_MLPC` | `xsd:string` | true | 0..1 |
| `MLPC` | `xsd:string` | true | 0..1 |
| `list_APL` | `xsd:string` | true | 0..1 |
| `APL` | `xsd:string` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Políticas_Públicas:mg_minas_reurb_sede_pl_jun_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `code_muni` | `xsd:string` | true | 0..1 |
| `name_muni` | `xsd:string` | true | 0..1 |
| `cod_estado` | `xsd:double` | true | 0..1 |
| `sigla` | `xsd:string` | true | 0..1 |
| `estado` | `xsd:string` | true | 0..1 |
| `cod_regiao` | `xsd:double` | true | 0..1 |
| `name_regia` | `xsd:string` | true | 0..1 |
| `cid_do_fut` | `xsd:string` | true | 0..1 |
| `reurb` | `xsd:string` | true | 0..1 |
| `reurb_resp` | `xsd:string` | true | 0..1 |
| `mat_MLPC` | `xsd:string` | true | 0..1 |
| `MLPC` | `xsd:string` | true | 0..1 |
| `list_APL` | `xsd:string` | true | 0..1 |
| `APL` | `xsd:string` | true | 0..1 |

## DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Regiao_Metropolitana_de_Belo_Horizonte (11)

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Regiao_Metropolitana_de_Belo_Horizonte:mg_linhas_onibus_metropolitanas_armbh_ln_out_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `nome linha` | `xsd:string` | true | 0..1 |
| `cod linha` | `xsd:string` | true | 0..1 |
| `cod delega` | `xsd:decimal` | true | 0..1 |
| `operadora` | `xsd:string` | true | 0..1 |
| `numero rit` | `xsd:decimal` | true | 0..1 |
| `indicacao` | `xsd:string` | true | 0..1 |
| `sistema` | `xsd:string` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Regiao_Metropolitana_de_Belo_Horizonte:mg_linhas_onibus_municipais_armbh_ln_out_2017`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `linha` | `xsd:string` | true | 0..1 |
| `cod_sublin` | `xsd:string` | true | 0..1 |
| `nome linha` | `xsd:string` | true | 0..1 |
| `nome area` | `xsd:string` | true | 0..1 |
| `operador` | `xsd:string` | true | 0..1 |
| `sistema` | `xsd:string` | true | 0..1 |
| `sentidolin` | `xsd:string` | true | 0..1 |
| `extensao` | `xsd:decimal` | true | 0..1 |
| `gestor` | `xsd:string` | true | 0..1 |
| `cod linha` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Regiao_Metropolitana_de_Belo_Horizonte:mg_proj_infra_transp_rmbh_ferroanel_armbh_ln_out_2017`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `pavimento` | `xsd:string` | true | 0..1 |
| `extenso` | `xsd:decimal` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `data` | `xsd:decimal` | true | 0..1 |
| `projeto` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Regiao_Metropolitana_de_Belo_Horizonte:mg_rmbh_metro_armbh_ln_out_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `cod linha` | `xsd:int` | true | 0..1 |
| `cod sublin` | `xsd:int` | true | 0..1 |
| `linha` | `xsd:string` | true | 0..1 |
| `nome linha` | `xsd:string` | true | 0..1 |
| `sent linha` | `xsd:string` | true | 0..1 |
| `extensao` | `xsd:decimal` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `gestor` | `xsd:string` | true | 0..1 |
| `operador` | `xsd:string` | true | 0..1 |
| `sistema` | `xsd:string` | true | 0..1 |
| `metro` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Regiao_Metropolitana_de_Belo_Horizonte:mg_rmbh_plan_mob_pl_out_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome` | `xsd:string` | true | 0..1 |
| `existencia` | `xsd:string` | true | 0..1 |
| `ano` | `xsd:string` | true | 0..1 |
| `intr_legal` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Regiao_Metropolitana_de_Belo_Horizonte:mg_rmbh_plano_diretor_pl_out_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome` | `xsd:string` | true | 0..1 |
| `versao_pd` | `xsd:string` | true | 0..1 |
| `ano_pd` | `xsd:int` | true | 0..1 |
| `lei_pd` | `xsd:string` | true | 0..1 |
| `lei_parcel` | `xsd:string` | true | 0..1 |
| `zim` | `xsd:string` | true | 0..1 |
| `lei_criaca` | `xsd:string` | true | 0..1 |
| `situa_pd` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Regiao_Metropolitana_de_Belo_Horizonte:mg_rmbh_sistema_viario_armbh_ln_out_2017`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `jurisidica` | `xsd:string` | true | 0..1 |
| `pavimento` | `xsd:string` | true | 0..1 |
| `hier_legal` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `nome_via` | `xsd:string` | true | 0..1 |
| `sis_viario` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Regiao_Metropolitana_de_Belo_Horizonte:mg_rmbh_snt_pl_out_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome` | `xsd:string` | true | 0..1 |
| `integracao` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Regiao_Metropolitana_de_Belo_Horizonte:mg_rmbh_terminais_metro_armbh_pt_out_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome_linha` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `terminal` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:decimal` | true | 0..1 |
| `lon` | `xsd:decimal` | true | 0..1 |
| `data` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Regiao_Metropolitana_de_Belo_Horizonte:mg_rodoviarias_armbh_pt_out_2017`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `municipio` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:decimal` | true | 0..1 |
| `lon` | `xsd:decimal` | true | 0..1 |
| `data` | `xsd:int` | true | 0..1 |
| `rodo` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Regiao_Metropolitana_de_Belo_Horizonte:mg_terminais_brt_armbh_pt_out_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `municipio` | `xsd:string` | true | 0..1 |
| `data` | `xsd:int` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `nome_siste` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:decimal` | true | 0..1 |
| `lat` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

## DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Relevo (5)

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Relevo:mg_marco_fjp_pt_nov_2014`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `codmarco` | `xsd:string` | true | 0..1 |
| `tipomarco` | `xsd:string` | true | 0..1 |
| `anoimp` | `xsd:string` | true | 0..1 |
| `mesimp` | `xsd:string` | true | 0..1 |
| `descricao1` | `xsd:string` | true | 0..1 |
| `descricao2` | `xsd:string` | true | 0..1 |
| `sistgeod` | `xsd:string` | true | 0..1 |
| `mc` | `xsd:string` | true | 0..1 |
| `fuso` | `xsd:string` | true | 0..1 |
| `latgeod` | `xsd:string` | true | 0..1 |
| `longgeod` | `xsd:string` | true | 0..1 |
| `latutm` | `xsd:double` | true | 0..1 |
| `longutm` | `xsd:double` | true | 0..1 |
| `altitude` | `xsd:double` | true | 0..1 |
| `muni1` | `xsd:string` | true | 0..1 |
| `muni2` | `xsd:string` | true | 0..1 |
| `muni3` | `xsd:string` | true | 0..1 |
| `muni_confr` | `xsd:string` | true | 0..1 |
| `uf_c` | `xsd:string` | true | 0..1 |
| `marcoref` | `xsd:string` | true | 0..1 |
| `solicitant` | `xsd:string` | true | 0..1 |
| `latgeodsir` | `xsd:string` | true | 0..1 |
| `longgeodsi` | `xsd:string` | true | 0..1 |
| `latutmsirg` | `xsd:double` | true | 0..1 |
| `longutmsir` | `xsd:double` | true | 0..1 |
| `latdecsirg` | `xsd:double` | true | 0..1 |
| `longdecsir` | `xsd:double` | true | 0..1 |
| `legend` | `xsd:string` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Relevo:mg_pico_fjp_pt_jan_2021`

> [!warning] Schema pendente
> Este esquema ainda não foi resolvido nesta coleta. Reconsulte o endpoint antes de usar a camada.


### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Relevo:mg_pico_ibge_pt_jun_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `pico` | `xsd:string` | true | 0..1 |
| `desc_` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:double` | true | 0..1 |
| `long` | `xsd:double` | true | 0..1 |
| `cota` | `xsd:double` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Relevo:mg_ponto_cotado_ibge_pt_mar_2010`

> [!warning] Schema pendente
> Este esquema ainda não foi resolvido nesta coleta. Reconsulte o endpoint antes de usar a camada.


### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Relevo:mg_solos_ufv_pl_dez_2010_v2`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `unidade` | `xsd:string` | true | 0..1 |
| `first_leva` | `xsd:short` | true | 0..1 |
| `first_base` | `xsd:short` | true | 0..1 |
| `legenda` | `xsd:string` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

## DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Sistema_de_Transporte (14)

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Sistema_de_Transporte:mg_balancas_der_pt_jun_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `URG` | `xsd:string` | true | 0..1 |
| `Municipio` | `xsd:string` | true | 0..1 |
| `Rodovia` | `xsd:string` | true | 0..1 |
| `Km` | `xsd:string` | true | 0..1 |
| `Coord_Y` | `xsd:double` | true | 0..1 |
| `Coord_X` | `xsd:double` | true | 0..1 |
| `Tipo_de_Op` | `xsd:string` | true | 0..1 |
| `Tipo_de_Eq` | `xsd:string` | true | 0..1 |
| `Status` | `xsd:string` | true | 0..1 |
| `Responsave` | `xsd:string` | true | 0..1 |
| `CD_MUN` | `xsd:decimal` | true | 0..1 |
| `NM_MUN` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |
| `Nível` | `xsd:string` | true | 0..1 |
| `Município` | `xsd:string` | true | 0..1 |
| `nm_meso` | `xsd:string` | true | 0..1 |
| `cd_geocme` | `xsd:decimal` | true | 0..1 |
| `Nº_URG` | `xsd:long` | true | 0..1 |
| `URG_2` | `xsd:string` | true | 0..1 |
| `Regional` | `xsd:string` | true | 0..1 |
| `Pop_2022` | `xsd:long` | true | 0..1 |
| `Pop_Est_20` | `xsd:long` | true | 0..1 |
| `Taxa_Cresc` | `xsd:double` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Sistema_de_Transporte:mg_complexo_aeroportuario_anac_pt_jan_2021`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome` | `xsd:string` | true | 0..1 |
| `indicador` | `xsd:string` | true | 0..1 |
| `siglaaero` | `xsd:string` | true | 0..1 |
| `tipocompla` | `xsd:string` | true | 0..1 |
| `classifica` | `xsd:string` | true | 0..1 |
| `latoficial` | `xsd:decimal` | true | 0..1 |
| `longoficia` | `xsd:decimal` | true | 0..1 |
| `altitude` | `xsd:double` | true | 0..1 |
| `nomeabrev` | `xsd:string` | true | 0..1 |
| `igamunicip` | `xsd:string` | true | 0..1 |
| `igadistrit` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Sistema_de_Transporte:mg_ferrovias_cprm_ln_dez_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `NOMEABREV` | `xsd:string` | true | 0..1 |
| `GEOMETRIAA` | `xsd:string` | true | 0..1 |
| `CODTRECHOF` | `xsd:string` | true | 0..1 |
| `POSICAOREL` | `xsd:string` | true | 0..1 |
| `TIPOTRECHO` | `xsd:string` | true | 0..1 |
| `BITOLA` | `xsd:string` | true | 0..1 |
| `ELETRIFICA` | `xsd:string` | true | 0..1 |
| `NRLINHAS` | `xsd:string` | true | 0..1 |
| `EMARRUAMEN` | `xsd:string` | true | 0..1 |
| `JURISDICAO` | `xsd:string` | true | 0..1 |
| `ADMINISTRA` | `xsd:string` | true | 0..1 |
| `CONCESSION` | `xsd:string` | true | 0..1 |
| `OPERACIONA` | `xsd:string` | true | 0..1 |
| `CARGASUPOR` | `xsd:double` | true | 0..1 |
| `SITUACAOFI` | `xsd:string` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Sistema_de_Transporte:mg_passagem_elevada_viaduto_der_pt_2011`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome` | `xsd:string` | true | 0..1 |
| `tipo_passa` | `xsd:string` | true | 0..1 |
| `modal_uso` | `xsd:string` | true | 0..1 |
| `matconstr` | `xsd:string` | true | 0..1 |
| `extensao` | `xsd:double` | true | 0..1 |
| `rodovia` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Sistema_de_Transporte:mg_pista_ponto_pouso_anac_pt_jan_2021`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `iganome` | `xsd:string` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `tipopista` | `xsd:string` | true | 0..1 |
| `usopista` | `xsd:string` | true | 0..1 |
| `revestimen` | `xsd:string` | true | 0..1 |
| `homologaca` | `xsd:string` | true | 0..1 |
| `operaciona` | `xsd:string` | true | 0..1 |
| `situacaofi` | `xsd:string` | true | 0..1 |
| `largura` | `xsd:double` | true | 0..1 |
| `extensao` | `xsd:int` | true | 0..1 |
| `nomeabrev` | `xsd:string` | true | 0..1 |
| `igamunicip` | `xsd:string` | true | 0..1 |
| `igadistrit` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Sistema_de_Transporte:mg_ponte_der_pt_jun_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `idCad` | `xsd:string` | true | 0..1 |
| `codUrg` | `xsd:double` | true | 0..1 |
| `sremg` | `xsd:string` | true | 0..1 |
| `descInicio` | `xsd:string` | true | 0..1 |
| `descFim` | `xsd:string` | true | 0..1 |
| `tipoOAE` | `xsd:string` | true | 0..1 |
| `responsabi` | `xsd:string` | true | 0..1 |
| `extensao` | `xsd:double` | true | 0..1 |
| `largura` | `xsd:double` | true | 0..1 |
| `tipoEstrut` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `RODOVIA` | `xsd:string` | true | 0..1 |
| `KM_INICIAL` | `xsd:string` | true | 0..1 |
| `MUNICIPIO` | `xsd:string` | true | 0..1 |
| `CURSO_DAGU` | `xsd:string` | true | 0..1 |
| `x` | `xsd:double` | true | 0..1 |
| `y` | `xsd:double` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Sistema_de_Transporte:mg_pontos_carregamentos_der_pt_jun_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `desc_` | `xsd:string` | true | 0..1 |
| `X` | `xsd:string` | true | 0..1 |
| `Y` | `xsd:string` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Sistema_de_Transporte:mg_radares_der_pt_jun_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `URG` | `xsd:long` | true | 0..1 |
| `Rodovia` | `xsd:string` | true | 0..1 |
| `Km` | `xsd:double` | true | 0..1 |
| `Município` | `xsd:string` | true | 0..1 |
| `Local` | `xsd:string` | true | 0..1 |
| `Latitude` | `xsd:double` | true | 0..1 |
| `Longitude` | `xsd:double` | true | 0..1 |
| `Lote` | `xsd:long` | true | 0..1 |
| `Faixas` | `xsd:string` | true | 0..1 |
| `Tipo` | `xsd:string` | true | 0..1 |
| `Velocidade` | `xsd:string` | true | 0..1 |
| `Energia` | `xsd:string` | true | 0..1 |
| `Status` | `xsd:string` | true | 0..1 |
| `Observaçd` | `xsd:string` | true | 0..1 |
| `Data_Iníc` | `xsd:string` | true | 0..1 |
| `Data_In�` | `xsd:string` | true | 0..1 |
| `Responsáv` | `xsd:string` | true | 0..1 |
| `Respons�` | `xsd:string` | true | 0..1 |
| `Estudo_Té` | `xsd:string` | true | 0..1 |
| `Nº_de_sé` | `xsd:string` | true | 0..1 |
| `Data_da_ú` | `xsd:string` | true | 0..1 |
| `Vencimento` | `xsd:string` | true | 0..1 |
| `fid_1` | `xsd:decimal` | true | 0..1 |
| `Name` | `xsd:string` | true | 0..1 |
| `descriptio` | `xsd:string` | true | 0..1 |
| `timestamp` | `xsd:string` | true | 0..1 |
| `begin` | `xsd:string` | true | 0..1 |
| `end` | `xsd:string` | true | 0..1 |
| `altitudeMo` | `xsd:string` | true | 0..1 |
| `tessellate` | `xsd:decimal` | true | 0..1 |
| `extrude` | `xsd:decimal` | true | 0..1 |
| `visibility` | `xsd:decimal` | true | 0..1 |
| `drawOrder` | `xsd:string` | true | 0..1 |
| `icon` | `xsd:string` | true | 0..1 |
| `CDEXPORTAC` | `xsd:string` | true | 0..1 |
| `ANO` | `xsd:decimal` | true | 0..1 |
| `ROD` | `xsd:string` | true | 0..1 |
| `SREMG` | `xsd:string` | true | 0..1 |
| `CDTRECHO` | `xsd:string` | true | 0..1 |
| `DESCINI` | `xsd:string` | true | 0..1 |
| `DESFIM` | `xsd:string` | true | 0..1 |
| `KMINI` | `xsd:double` | true | 0..1 |
| `KMFIM` | `xsd:double` | true | 0..1 |
| `KMEXT` | `xsd:double` | true | 0..1 |
| `MKINI` | `xsd:string` | true | 0..1 |
| `MKFIM` | `xsd:string` | true | 0..1 |
| `RESP` | `xsd:string` | true | 0..1 |
| `CRGRRG` | `xsd:string` | true | 0..1 |
| `CRGRESP` | `xsd:string` | true | 0..1 |
| `CARAC` | `xsd:string` | true | 0..1 |
| `SITFIS` | `xsd:string` | true | 0..1 |
| `JURIS` | `xsd:string` | true | 0..1 |
| `CIDE` | `xsd:string` | true | 0..1 |
| `CONSR` | `xsd:string` | true | 0..1 |
| `POSI` | `xsd:string` | true | 0..1 |
| `COIN1` | `xsd:string` | true | 0..1 |
| `COIN2` | `xsd:string` | true | 0..1 |
| `COIN3` | `xsd:string` | true | 0..1 |
| `COIN4` | `xsd:string` | true | 0..1 |
| `SREMGANT` | `xsd:string` | true | 0..1 |
| `TRECHOOBS` | `xsd:string` | true | 0..1 |
| `CLASSFUNC` | `xsd:string` | true | 0..1 |
| `DENNOM` | `xsd:string` | true | 0..1 |
| `DENDEC` | `xsd:string` | true | 0..1 |
| `DENDAT` | `xsd:string` | true | 0..1 |
| `RMBH` | `xsd:string` | true | 0..1 |
| `REGPLAN` | `xsd:string` | true | 0..1 |
| `CONVNUM` | `xsd:string` | true | 0..1 |
| `CONVPUB` | `xsd:string` | true | 0..1 |
| `CONVINI` | `xsd:string` | true | 0..1 |
| `CONVFIM` | `xsd:string` | true | 0..1 |
| `CONVOBS` | `xsd:string` | true | 0..1 |
| `VMDPASS` | `xsd:decimal` | true | 0..1 |
| `VMDCOLE` | `xsd:decimal` | true | 0..1 |
| `VMDLEVE` | `xsd:decimal` | true | 0..1 |
| `VMDMED` | `xsd:decimal` | true | 0..1 |
| `VMDPESA` | `xsd:decimal` | true | 0..1 |
| `VMDTOT` | `xsd:decimal` | true | 0..1 |
| `SENTTRAF` | `xsd:string` | true | 0..1 |
| `INATIVO` | `xsd:string` | true | 0..1 |
| `OFICIAL` | `xsd:string` | true | 0..1 |
| `NUKMINICIA` | `xsd:double` | true | 0..1 |
| `NUKMFINALG` | `xsd:double` | true | 0..1 |
| `Resp_class` | `xsd:string` | true | 0..1 |
| `URG_2` | `xsd:long` | true | 0..1 |
| `Fonte` | `xsd:string` | true | 0..1 |
| `Moto` | `xsd:long` | true | 0..1 |
| `Passeio___` | `xsd:long` | true | 0..1 |
| `Onibus_fro` | `xsd:long` | true | 0..1 |
| `Leve_frota` | `xsd:long` | true | 0..1 |
| `Media_frot` | `xsd:long` | true | 0..1 |
| `Articulado` | `xsd:long` | true | 0..1 |
| `VMDAT` | `xsd:long` | true | 0..1 |
| `fid_2` | `xsd:decimal` | true | 0..1 |
| `CD_MUN` | `xsd:decimal` | true | 0..1 |
| `NM_MUN` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |
| `Nível` | `xsd:string` | true | 0..1 |
| `Municíp_1` | `xsd:string` | true | 0..1 |
| `nm_meso` | `xsd:string` | true | 0..1 |
| `cd_geocme` | `xsd:decimal` | true | 0..1 |
| `Pop_2022` | `xsd:long` | true | 0..1 |
| `Pop_Est_20` | `xsd:long` | true | 0..1 |
| `Taxa_Cresc` | `xsd:double` | true | 0..1 |
| `Regional` | `xsd:string` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Sistema_de_Transporte:mg_risco_atropelamento_fauna_der_ln_jun_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `Rodovia` | `xsd:string` | true | 0..1 |
| `Lat__Inici` | `xsd:double` | true | 0..1 |
| `Long__Inic` | `xsd:double` | true | 0..1 |
| `Lat__Final` | `xsd:double` | true | 0..1 |
| `Long__Fina` | `xsd:double` | true | 0..1 |
| `Ranking` | `xsd:double` | true | 0..1 |
| `perccentil` | `xsd:long` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Sistema_de_Transporte:mg_rodovias_cprm_ln_dez_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `GEOMETRIAA` | `xsd:string` | true | 0..1 |
| `CODTRECHOR` | `xsd:string` | true | 0..1 |
| `TIPOTRECHO` | `xsd:string` | true | 0..1 |
| `JURISDICAO` | `xsd:string` | true | 0..1 |
| `ADMINISTRA` | `xsd:string` | true | 0..1 |
| `CONCESSION` | `xsd:string` | true | 0..1 |
| `REVESTIMEN` | `xsd:string` | true | 0..1 |
| `OPERACIONA` | `xsd:string` | true | 0..1 |
| `SITUACAOFI` | `xsd:string` | true | 0..1 |
| `NRPISTAS` | `xsd:double` | true | 0..1 |
| `NRFAIXAS` | `xsd:double` | true | 0..1 |
| `TRAFEGO` | `xsd:string` | true | 0..1 |
| `CANTEIRODI` | `xsd:string` | true | 0..1 |
| `CAPACCARGA` | `xsd:double` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Sistema_de_Transporte:mg_rodovias_der_ln_set_2019`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `SIGLA_RODO` | `xsd:string` | true | 0..1 |
| `RESPONSAVE` | `xsd:string` | true | 0..1 |
| `SITUACAO_F` | `xsd:string` | true | 0..1 |
| `JURISDICAO` | `xsd:string` | true | 0..1 |
| `CLASSE_FUN` | `xsd:string` | true | 0..1 |
| `SENTIDO_TR` | `xsd:string` | true | 0..1 |
| `rod` | `xsd:string` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Sistema_de_Transporte:mg_trecho_ferroviario_der_ln_set_2021`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `GEOMETRIAA` | `xsd:string` | true | 0..1 |
| `CODTRECHOF` | `xsd:string` | true | 0..1 |
| `POSICAOREL` | `xsd:string` | true | 0..1 |
| `TIPOTRECHO` | `xsd:string` | true | 0..1 |
| `BITOLA` | `xsd:string` | true | 0..1 |
| `ELETRIFICA` | `xsd:string` | true | 0..1 |
| `NRLINHAS` | `xsd:string` | true | 0..1 |
| `EMARRUAMEN` | `xsd:string` | true | 0..1 |
| `JURISDIшE` | `xsd:string` | true | 0..1 |
| `ADMINISTRA` | `xsd:string` | true | 0..1 |
| `CONCESSION` | `xsd:string` | true | 0..1 |
| `OPERACIONA` | `xsd:string` | true | 0..1 |
| `SITUACAOFI` | `xsd:string` | true | 0..1 |
| `CARGASUPOR` | `xsd:double` | true | 0..1 |
| `NOMEABREV` | `xsd:string` | true | 0..1 |
| `IGANOMETRE` | `xsd:string` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Sistema_de_Transporte:mg_trecho_rodoviario_ibge_ln_jun_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `ROD_KM_INI` | `xsd:double` | true | 0..1 |
| `ROD_KM_FIN` | `xsd:double` | true | 0..1 |
| `ROD_KM_EXT` | `xsd:double` | true | 0..1 |
| `SNV_ROD_CO` | `xsd:string` | true | 0..1 |
| `UF_SIGLA` | `xsd:string` | true | 0..1 |
| `ROD_ADM_NO` | `xsd:string` | true | 0..1 |
| `ROD_CODIGO` | `xsd:string` | true | 0..1 |
| `SNV_ROD_SU` | `xsd:string` | true | 0..1 |
| `ROD_CON_DE` | `xsd:string` | true | 0..1 |
| `ROD_FON_DE` | `xsd:string` | true | 0..1 |
| `br` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Sistema_de_Transporte:mg_vias_osm_ln_abr_2024`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `osm_id` | `xsd:string` | true | 0..1 |
| `ref` | `xsd:string` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `oneway` | `xsd:int` | true | 0..1 |
| `bridge` | `xsd:int` | true | 0..1 |
| `tunnel` | `xsd:int` | true | 0..1 |
| `maxspeed` | `xsd:int` | true | 0..1 |
| `extensao_m` | `xsd:double` | true | 0..1 |
| `legend` | `xsd:string` | true | 0..1 |

## DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Áreas_Protegidas (5)

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Áreas_Protegidas:mg_area_protecao_especial_ief_pl_jul_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nome_uc` | `xsd:string` | true | 0..1 |
| `sigla` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `ato_legal` | `xsd:string` | true | 0..1 |
| `area_ofic` | `xsd:double` | true | 0..1 |
| `area_geo` | `xsd:double` | true | 0..1 |
| `municipios` | `xsd:string` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `administra` | `xsd:string` | true | 0..1 |
| `reg_ief` | `xsd:string` | true | 0..1 |
| `id_uc_` | `xsd:string` | true | 0..1 |
| `v_atual_` | `xsd:string` | true | 0..1 |
| `uc_tipo` | `xsd:string` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Áreas_Protegidas:mg_reserva_particular_patrimonio_natural_ief_icmbio_pl_dez_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome_uc` | `xsd:string` | true | 0..1 |
| `sigla` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `ato_legal` | `xsd:string` | true | 0..1 |
| `area_ofic` | `xsd:double` | true | 0..1 |
| `area_geo` | `xsd:double` | true | 0..1 |
| `municipios` | `xsd:string` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `administra` | `xsd:string` | true | 0..1 |
| `reg_ief` | `xsd:string` | true | 0..1 |
| `id_uc_` | `xsd:string` | true | 0..1 |
| `v_atual_` | `xsd:string` | true | 0..1 |
| `uc_tipo` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Áreas_Protegidas:mg_unidade_conservacao_estadual_ief_icmbio_pl_jan_2021`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nome_uc` | `xsd:string` | true | 0..1 |
| `sigla` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `ato_legal` | `xsd:string` | true | 0..1 |
| `area_ofic` | `xsd:double` | true | 0..1 |
| `area_geo` | `xsd:double` | true | 0..1 |
| `municipios` | `xsd:string` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `administra` | `xsd:string` | true | 0..1 |
| `reg_ief` | `xsd:string` | true | 0..1 |
| `id_uc_` | `xsd:string` | true | 0..1 |
| `v_atual_` | `xsd:string` | true | 0..1 |
| `uc_tipo` | `xsd:string` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Áreas_Protegidas:mg_unidade_conservacao_federal_ief_icmbio_pl_jul_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome_uc` | `xsd:string` | true | 0..1 |
| `sigla` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `ato_legal` | `xsd:string` | true | 0..1 |
| `area_ofic` | `xsd:double` | true | 0..1 |
| `area_geo` | `xsd:double` | true | 0..1 |
| `municipios` | `xsd:string` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `administra` | `xsd:string` | true | 0..1 |
| `reg_ief` | `xsd:string` | true | 0..1 |
| `id_uc_` | `xsd:string` | true | 0..1 |
| `v_atual_` | `xsd:string` | true | 0..1 |
| `uc_tipo` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `DADOS_GEOESPACIAIS_DE_MINAS_GERAIS.Áreas_Protegidas:mg_unidade_conservacao_municipal_ief_icmbio_pl_dez_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome_uc` | `xsd:string` | true | 0..1 |
| `sigla` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `ato_legal` | `xsd:string` | true | 0..1 |
| `area_ofic` | `xsd:double` | true | 0..1 |
| `area_geo` | `xsd:double` | true | 0..1 |
| `municipios` | `xsd:string` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `administra` | `xsd:string` | true | 0..1 |
| `reg_ief` | `xsd:string` | true | 0..1 |
| `id_uc_` | `xsd:string` | true | 0..1 |
| `v_atual_` | `xsd:string` | true | 0..1 |
| `uc_tipo` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

## ORTOFOTOS_e_MDT_RMBH_2014_a_2019.Mosaico_Ortofotos_RMBH (1)

### `ORTOFOTOS_e_MDT_RMBH_2014_a_2019.Mosaico_Ortofotos_RMBH:mg_art_mun_hiparc_fototerra_pl_2019`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `CONTRATO` | `xsd:string` | true | 0..1 |
| `MUN_CONT` | `xsd:string` | true | 0..1 |
| `ACERVO` | `xsd:string` | true | 0..1 |
| `ART` | `xsd:string` | true | 0..1 |
| `MUNICIPIO` | `xsd:string` | true | 0..1 |
