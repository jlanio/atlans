# SEPLAN TO — atributos das camadas

Geoportal: [[Geosserviços/SEPLAN TO/Secretaria do Planejamento e Orçamento do Tocantins — SEPLAN|Secretaria do Planejamento e Orçamento do Tocantins — SEPLAN]]

Os campos abaixo vêm de `DescribeFeatureType` (XSD), sem download de feições.

## base_cartografica_sudeste_tocantins (12)

### `base_cartografica_sudeste_tocantins:aerodromo_st`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `nm_municip` | `xsd:string` | true | 0..1 |
| `tipoaero` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `largura_m` | `xsd:double` | true | 0..1 |
| `num_pista` | `xsd:int` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `altitude` | `xsd:double` | true | 0..1 |
| `extensao` | `xsd:double` | true | 0..1 |
| `cod_uso` | `xsd:string` | true | 0..1 |
| `pavimento` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `cod_icao` | `xsd:string` | true | 0..1 |
| `geocodigo` | `xsd:int` | true | 0..1 |

### `base_cartografica_sudeste_tocantins:areaestudopoligon`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_cartografica_sudeste_tocantins:areaumida_pol50`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geometriaa` | `xsd:int` | true | 0..1 |
| `tipoareaum` | `xsd:string` | true | 0..1 |
| `nomeabrev` | `xsd:string` | true | 0..1 |
| `gcod` | `xsd:int` | true | 0..1 |
| `clei` | `xsd:int` | true | 0..1 |
| `tipoarea_1` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_cartografica_sudeste_tocantins:assentamentoincrapoligono`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `gid0` | `xsd:string` | true | 0..1 |
| `nome_pro2` | `xsd:string` | true | 0..1 |
| `municipi3` | `xsd:string` | true | 0..1 |
| `area_hec4` | `xsd:string` | true | 0..1 |
| `capacida5` | `xsd:string` | true | 0..1 |
| `num_fami6` | `xsd:string` | true | 0..1 |
| `data_de_8` | `xsd:string` | true | 0..1 |
| `forma_ob9` | `xsd:string` | true | 0..1 |
| `data_obt10` | `xsd:string` | true | 0..1 |
| `area_cal11` | `xsd:string` | true | 0..1 |
| `descrica13` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_cartografica_sudeste_tocantins:estacaofluvioanaponto`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `descriptio` | `xsd:string` | true | 0..1 |

### `base_cartografica_sudeste_tocantins:hidrografialinha50`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geometriaa` | `xsd:int` | true | 0..1 |
| `coincideco` | `xsd:string` | true | 0..1 |
| `dentrodepo` | `xsd:int` | true | 0..1 |
| `compartilh` | `xsd:int` | true | 0..1 |
| `eixoprinci` | `xsd:int` | true | 0..1 |
| `navegabili` | `xsd:string` | true | 0..1 |
| `caladomax` | `xsd:double` | true | 0..1 |
| `regime` | `xsd:string` | true | 0..1 |
| `larguramed` | `xsd:double` | true | 0..1 |
| `velocidade` | `xsd:double` | true | 0..1 |
| `profundida` | `xsd:double` | true | 0..1 |
| `nomeabrev` | `xsd:string` | true | 0..1 |
| `gcod` | `xsd:int` | true | 0..1 |
| `clei` | `xsd:int` | true | 0..1 |
| `nome_2` | `xsd:string` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `f100_toc_5` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |

### `base_cartografica_sudeste_tocantins:ilhapoligono50`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geometriaa` | `xsd:int` | true | 0..1 |
| `tipoilha` | `xsd:string` | true | 0..1 |
| `nomeabrev` | `xsd:string` | true | 0..1 |
| `gcod` | `xsd:int` | true | 0..1 |
| `clei` | `xsd:int` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_cartografica_sudeste_tocantins:localidades_st`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `nm_nome` | `xsd:string` | true | 0..1 |
| `geocodigo` | `xsd:string` | true | 0..1 |
| `cd_classe_` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `populacao2` | `xsd:int` | true | 0..1 |
| `md_latitud` | `xsd:double` | true | 0..1 |
| `md_longitu` | `xsd:double` | true | 0..1 |
| `data_alter` | `xsd:string` | true | 0..1 |
| `metodo_alt` | `xsd:string` | true | 0..1 |
| `fonte_info` | `xsd:string` | true | 0..1 |
| `gmrotation` | `xsd:double` | true | 0..1 |

### `base_cartografica_sudeste_tocantins:massaaguapoligono50`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geometriaa` | `xsd:int` | true | 0..1 |
| `tipomassad` | `xsd:string` | true | 0..1 |
| `regime` | `xsd:string` | true | 0..1 |
| `salinidade` | `xsd:string` | true | 0..1 |
| `nomeabrev` | `xsd:string` | true | 0..1 |
| `gcod` | `xsd:int` | true | 0..1 |
| `clei` | `xsd:int` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_cartografica_sudeste_tocantins:nascenteponto50`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geometriaa` | `xsd:int` | true | 0..1 |
| `nascente` | `xsd:string` | true | 0..1 |
| `nomeabrev` | `xsd:string` | true | 0..1 |
| `gcod` | `xsd:int` | true | 0..1 |
| `clei` | `xsd:int` | true | 0..1 |

### `base_cartografica_sudeste_tocantins:territorioquilombolaincra`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nr_proce2` | `xsd:string` | true | 0..1 |
| `nm_comun3` | `xsd:string` | true | 0..1 |
| `nm_munic4` | `xsd:string` | true | 0..1 |
| `nr_famil8` | `xsd:string` | true | 0..1 |
| `area_cal10` | `xsd:string` | true | 0..1 |
| `responsa12` | `xsd:string` | true | 0..1 |
| `esfera13` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_cartografica_sudeste_tocantins:trechomassaaguapoligono50`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geometriaa` | `xsd:int` | true | 0..1 |
| `tipotrecho` | `xsd:string` | true | 0..1 |
| `regime` | `xsd:string` | true | 0..1 |
| `salinidade` | `xsd:string` | true | 0..1 |
| `nomeabrev` | `xsd:string` | true | 0..1 |
| `gcod` | `xsd:int` | true | 0..1 |
| `clei` | `xsd:int` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

## base_digital_continua (115)

### `base_digital_continua:aeroportos_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_sistema` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `cd_cat_aer` | `xsd:int` | true | 0..1 |
| `cd_util_ae` | `xsd:int` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:areas_humidas_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hidrogr` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `tip_hidrog` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fonte_inf_` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `nm_rio_ass` | `xsd:string` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:areas_humidas_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hidrogr` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `tip_hidrog` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fonte_inf_` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `nm_rio_ass` | `xsd:string` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:areas_humidas_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hidrogr` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `tip_hidrog` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fonte_inf_` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `nm_rio_ass` | `xsd:string` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:areas_lazer_pontos_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_obra` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_lazer` | `xsd:int` | true | 0..1 |
| `angulo` | `xsd:int` | true | 0..1 |

### `base_digital_continua:areas_lazer_pontos_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_obra` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_lazer` | `xsd:int` | true | 0..1 |
| `angulo` | `xsd:int` | true | 0..1 |

### `base_digital_continua:areas_lazer_pontos_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_obra` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_lazer` | `xsd:int` | true | 0..1 |
| `angulo` | `xsd:int` | true | 0..1 |

### `base_digital_continua:bacias_hidrograficas_poligonos_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `fon_inf_al` | `xsd:string` | true | 0..1 |
| `tip_limite` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:bacias_hidrograficas_poligonos_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `fon_inf_al` | `xsd:string` | true | 0..1 |
| `tip_limite` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:bacias_hidrograficas_poligonos_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `fon_inf_al` | `xsd:string` | true | 0..1 |
| `tip_limite` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:barragem_represa_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_obra` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `cd_tip_bar` | `xsd:int` | true | 0..1 |
| `nm_localiz` | `xsd:string` | true | 0..1 |
| `nm_rio_ass` | `xsd:string` | true | 0..1 |
| `data_licen` | `xsd:date` | true | 0..1 |
| `data_lic_1` | `xsd:date` | true | 0..1 |
| `data_lic_2` | `xsd:date` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:barragem_represa_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_obra` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `cd_tip_bar` | `xsd:int` | true | 0..1 |
| `nm_localiz` | `xsd:string` | true | 0..1 |
| `nm_rio_ass` | `xsd:string` | true | 0..1 |
| `data_licen` | `xsd:date` | true | 0..1 |
| `data_lic_1` | `xsd:date` | true | 0..1 |
| `data_lic_2` | `xsd:date` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:barragem_represa_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_obra` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `cd_tip_bar` | `xsd:int` | true | 0..1 |
| `nm_localiz` | `xsd:string` | true | 0..1 |
| `nm_rio_ass` | `xsd:string` | true | 0..1 |
| `data_licen` | `xsd:date` | true | 0..1 |
| `data_lic_1` | `xsd:date` | true | 0..1 |
| `data_lic_2` | `xsd:date` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:campo_pouso_poligonos_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_sistema` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `nm_mun_ass` | `xsd:string` | true | 0..1 |
| `cd_tip_pis` | `xsd:int` | true | 0..1 |
| `cd_util_ae` | `xsd:int` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:campo_pouso_poligonos_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_sistema` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `nm_mun_ass` | `xsd:string` | true | 0..1 |
| `cd_tip_pis` | `xsd:int` | true | 0..1 |
| `cd_util_ae` | `xsd:int` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:campo_pouso_pontos_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_sistema` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `cd_util_ae` | `xsd:int` | true | 0..1 |
| `tip_campo` | `xsd:int` | true | 0..1 |
| `angulo` | `xsd:int` | true | 0..1 |

### `base_digital_continua:campo_pouso_pontos_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_sistema` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `cd_util_ae` | `xsd:int` | true | 0..1 |
| `tip_campo` | `xsd:int` | true | 0..1 |
| `angulo` | `xsd:int` | true | 0..1 |

### `base_digital_continua:campo_pouso_pontos_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_sistema` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `cd_util_ae` | `xsd:int` | true | 0..1 |
| `tip_campo` | `xsd:int` | true | 0..1 |
| `angulo` | `xsd:int` | true | 0..1 |

### `base_digital_continua:cercas_muros_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `tip_edific` | `xsd:int` | true | 0..1 |
| `cd_alinham` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:cercas_muros_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `tip_edific` | `xsd:int` | true | 0..1 |
| `cd_alinham` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:cercas_muros_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `tip_edific` | `xsd:int` | true | 0..1 |
| `cd_alinham` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:cursos_agua_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hidrogr` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `tip_hidrog` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `cd_tip_ele` | `xsd:int` | true | 0..1 |
| `cd_fluxo` | `xsd:int` | true | 0..1 |
| `cd_navegab` | `xsd:int` | true | 0..1 |
| `cd_cla_dna` | `xsd:int` | true | 0..1 |
| `nm_rio_ass` | `xsd:string` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:cursos_agua_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hidrogr` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `tip_hidrog` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `cd_tip_ele` | `xsd:int` | true | 0..1 |
| `cd_fluxo` | `xsd:int` | true | 0..1 |
| `cd_navegab` | `xsd:int` | true | 0..1 |
| `cd_cla_dna` | `xsd:int` | true | 0..1 |
| `nm_rio_ass` | `xsd:string` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:cursos_agua_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hidrogr` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `tip_hidrog` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `cd_tip_ele` | `xsd:int` | true | 0..1 |
| `cd_fluxo` | `xsd:int` | true | 0..1 |
| `cd_navegab` | `xsd:int` | true | 0..1 |
| `cd_cla_dna` | `xsd:int` | true | 0..1 |
| `nm_rio_ass` | `xsd:string` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:curvas_de_nivel_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hipsogr` | `xsd:int` | true | 0..1 |
| `cota` | `xsd:int` | true | 0..1 |
| `tip_hipsog` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_ateraca` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:curvas_de_nivel_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hipsogr` | `xsd:int` | true | 0..1 |
| `cota` | `xsd:int` | true | 0..1 |
| `tip_hipsog` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_ateraca` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:curvas_de_nivel_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hipsogr` | `xsd:int` | true | 0..1 |
| `cota` | `xsd:int` | true | 0..1 |
| `tip_hipsog` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_ateraca` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:desmatamento_1000_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cla_2002` | `xsd:string` | true | 0..1 |
| `cla_2000` | `xsd:string` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:desmatamento_100_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cla_2002` | `xsd:string` | true | 0..1 |
| `cla_2000` | `xsd:string` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:desmatamento_250_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cla_2002` | `xsd:string` | true | 0..1 |
| `cla_2000` | `xsd:string` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:desmatamento_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `leg_100` | `xsd:string` | true | 0..1 |
| `vegetacao` | `xsd:string` | true | 0..1 |
| `descricao` | `xsd:string` | true | 0..1 |
| `regioes_f` | `xsd:string` | true | 0..1 |
| `classes_1` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `area_km2` | `xsd:double` | true | 0..1 |
| `area_m2` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:desmatamento_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `leg_1000` | `xsd:string` | true | 0..1 |
| `vegetacao` | `xsd:string` | true | 0..1 |
| `descricao_` | `xsd:string` | true | 0..1 |
| `regioes_fi` | `xsd:string` | true | 0..1 |
| `classes_1` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `area_km2` | `xsd:double` | true | 0..1 |
| `area_m2` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:desmatamento_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `leg_250` | `xsd:string` | true | 0..1 |
| `vegetacao` | `xsd:string` | true | 0..1 |
| `descricao_` | `xsd:string` | true | 0..1 |
| `regioes_fi` | `xsd:string` | true | 0..1 |
| `classes_1` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `area_km2` | `xsd:double` | true | 0..1 |
| `area_m2` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:edificacoes_grandes_bdc_`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_obra` | `xsd:int` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_edific` | `xsd:int` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:edificacoes_grandes_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_obra` | `xsd:int` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_edific` | `xsd:int` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:edificacoes_pontos_bdc_`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_obra` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_edific` | `xsd:int` | true | 0..1 |
| `angulo` | `xsd:int` | true | 0..1 |

### `base_digital_continua:edificacoes_pontos_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `cd_obra` | `xsd:double` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `fon_inf_al` | `xsd:double` | true | 0..1 |
| `met_altera` | `xsd:double` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_edific` | `xsd:double` | true | 0..1 |
| `angulo` | `xsd:double` | true | 0..1 |

### `base_digital_continua:edificacoes_pontos_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_obra` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_edific` | `xsd:int` | true | 0..1 |
| `angulo` | `xsd:int` | true | 0..1 |

### `base_digital_continua:estacao_geradora_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_obra` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_estaca` | `xsd:int` | true | 0..1 |

### `base_digital_continua:estacao_geradora_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_obra` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_estaca` | `xsd:int` | true | 0..1 |

### `base_digital_continua:estacao_geradora_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_obra` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_estaca` | `xsd:int` | true | 0..1 |

### `base_digital_continua:ferrovia_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_sistema` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `cd_sit_fer` | `xsd:int` | true | 0..1 |
| `cd_org_man` | `xsd:int` | true | 0..1 |
| `cd_tip_bit` | `xsd:int` | true | 0..1 |
| `cd_con_fer` | `xsd:int` | true | 0..1 |
| `cd_tip_lin` | `xsd:int` | true | 0..1 |
| `cd_adminis` | `xsd:int` | true | 0..1 |
| `tip_ferrov` | `xsd:int` | true | 0..1 |
| `cd_alinham` | `xsd:int` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:hidrografia_balsas_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_sistema` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_estrut` | `xsd:int` | true | 0..1 |
| `nm_rio_ass` | `xsd:string` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:hidrografia_balsas_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_sistema` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_estrut` | `xsd:int` | true | 0..1 |
| `nm_rio_ass` | `xsd:string` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:hidrografia_balsas_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_sistema` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_estrut` | `xsd:int` | true | 0..1 |
| `nm_rio_ass` | `xsd:string` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:hidrografia_ilhas_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hidrogr` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `tip_hidrog` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `nm_rio_ass` | `xsd:string` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:hidrografia_ilhas_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hidrogr` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `tip_hidrog` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `nm_rio_ass` | `xsd:string` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:hidrografia_ilhas_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hidrogr` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `tip_hidrog` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `nm_rio_ass` | `xsd:string` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:hidrografia_pontos_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hidrogr` | `xsd:int` | true | 0..1 |
| `tip_hidrog` | `xsd:int` | true | 0..1 |
| `angulo` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `nm_rio_ass` | `xsd:string` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |

### `base_digital_continua:hidrografia_pontos_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hidrogr` | `xsd:int` | true | 0..1 |
| `tip_hidrog` | `xsd:int` | true | 0..1 |
| `angulo` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `nm_rio_ass` | `xsd:string` | true | 0..1 |
| `nm_identic` | `xsd:string` | true | 0..1 |

### `base_digital_continua:hipsografia_banco_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hipsogr` | `xsd:int` | true | 0..1 |
| `tip_hipsog` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `cd_condica` | `xsd:int` | true | 0..1 |
| `nm_banco` | `xsd:string` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:hipsografia_banco_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hipsogr` | `xsd:int` | true | 0..1 |
| `tip_hipsog` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `cd_condica` | `xsd:int` | true | 0..1 |
| `nm_banco` | `xsd:string` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:hipsografia_banco_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hipsogr` | `xsd:int` | true | 0..1 |
| `tip_hipsog` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `cd_condica` | `xsd:int` | true | 0..1 |
| `nm_banco` | `xsd:string` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:hipsografia_escarpa_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hipsogr` | `xsd:int` | true | 0..1 |
| `tip_hipsog` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `nm_escarpa` | `xsd:string` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:hipsografia_escarpa_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hipsogr` | `xsd:int` | true | 0..1 |
| `tip_hipsog` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `nm_escarpa` | `xsd:string` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:hipsografia_escarpa_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hipsogr` | `xsd:int` | true | 0..1 |
| `tip_hipsog` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `nm_escarpa` | `xsd:string` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:hipsografia_linha_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hipsogr` | `xsd:int` | true | 0..1 |
| `tip_hipsog` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:hipsografia_linha_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hipsogr` | `xsd:int` | true | 0..1 |
| `tip_hipsog` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:hipsografia_linha_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hipsogr` | `xsd:int` | true | 0..1 |
| `tip_hipsog` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:hipsografia_ponto_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hipsogr` | `xsd:int` | true | 0..1 |
| `tip_hipsog` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |

### `base_digital_continua:hipsografia_ponto_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hipsogr` | `xsd:int` | true | 0..1 |
| `tip_hipsog` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |

### `base_digital_continua:hipsografia_ponto_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hipsogr` | `xsd:int` | true | 0..1 |
| `tip_hipsog` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |

### `base_digital_continua:jazida_linhas_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_obra` | `xsd:int` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_jazime` | `xsd:int` | true | 0..1 |
| `cd_con_exp` | `xsd:int` | true | 0..1 |
| `cd_tip_poc` | `xsd:int` | true | 0..1 |
| `cd_tip_ext` | `xsd:int` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:jazida_linhas_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_obra` | `xsd:int` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_jazime` | `xsd:int` | true | 0..1 |
| `cd_con_exp` | `xsd:int` | true | 0..1 |
| `cd_tip_poc` | `xsd:int` | true | 0..1 |
| `cd_tip_ext` | `xsd:int` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:jazida_linhas_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_obra` | `xsd:int` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_jazime` | `xsd:int` | true | 0..1 |
| `cd_con_exp` | `xsd:int` | true | 0..1 |
| `cd_tip_poc` | `xsd:int` | true | 0..1 |
| `cd_tip_ext` | `xsd:int` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:jazida_poligonos_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_obra` | `xsd:int` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_jazime` | `xsd:int` | true | 0..1 |
| `cd_con_exp` | `xsd:int` | true | 0..1 |
| `cd_tip_poc` | `xsd:int` | true | 0..1 |
| `cd_tip_ext` | `xsd:int` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:jazida_poligonos_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_obra` | `xsd:int` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_jazime` | `xsd:int` | true | 0..1 |
| `cd_con_exp` | `xsd:int` | true | 0..1 |
| `cd_tip_poc` | `xsd:int` | true | 0..1 |
| `cd_tip_ext` | `xsd:int` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:jazida_poligonos_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_obra` | `xsd:int` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_jazime` | `xsd:int` | true | 0..1 |
| `cd_con_exp` | `xsd:int` | true | 0..1 |
| `cd_tip_poc` | `xsd:int` | true | 0..1 |
| `cd_tip_ext` | `xsd:int` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:jazida_pontos_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_obra` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_jazime` | `xsd:int` | true | 0..1 |

### `base_digital_continua:jazida_pontos_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_obra` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_jazime` | `xsd:int` | true | 0..1 |

### `base_digital_continua:jazida_pontos_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_obra` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_jazime` | `xsd:int` | true | 0..1 |

### `base_digital_continua:limite_estadual_poligono_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `fon_inf_al` | `xsd:string` | true | 0..1 |
| `tip_limite` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:limites_municipais_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `fon_inf_al` | `xsd:string` | true | 0..1 |
| `tip_limite` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:linha_transmissao_energia_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_obra` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_linha_` | `xsd:int` | true | 0..1 |
| `cd_tensao` | `xsd:int` | true | 0..1 |
| `cd_tip_com` | `xsd:int` | true | 0..1 |
| `cd_alinham` | `xsd:int` | true | 0..1 |
| `cd_situaca` | `xsd:int` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:linha_transmissao_energia_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_obra` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_linha_` | `xsd:int` | true | 0..1 |
| `cd_tensao` | `xsd:int` | true | 0..1 |
| `cd_tip_com` | `xsd:int` | true | 0..1 |
| `cd_alinham` | `xsd:int` | true | 0..1 |
| `cd_situaca` | `xsd:int` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:linha_transmissao_energia_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_obra` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_linha_` | `xsd:int` | true | 0..1 |
| `cd_tensao` | `xsd:int` | true | 0..1 |
| `cd_tip_com` | `xsd:int` | true | 0..1 |
| `cd_alinham` | `xsd:int` | true | 0..1 |
| `cd_situaca` | `xsd:int` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:localidades_poligono_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_localid` | `xsd:int` | true | 0..1 |
| `nm_localid` | `xsd:string` | true | 0..1 |
| `tip_locali` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `nm_loc_ass` | `xsd:string` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:localidades_ponto_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_localid` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `tip_locali` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `nm_loc_ass` | `xsd:string` | true | 0..1 |

### `base_digital_continua:marco_1000_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_limite` | `xsd:int` | true | 0..1 |
| `tip_limite` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `nm_marco` | `xsd:string` | true | 0..1 |
| `nro_marco` | `xsd:int` | true | 0..1 |

### `base_digital_continua:marco_100_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `cd_limite` | `xsd:double` | true | 0..1 |
| `tip_limite` | `xsd:double` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:double` | true | 0..1 |
| `fon_inf_al` | `xsd:double` | true | 0..1 |
| `nm_marco` | `xsd:string` | true | 0..1 |
| `nro_marco` | `xsd:double` | true | 0..1 |

### `base_digital_continua:marco_250_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_limite` | `xsd:int` | true | 0..1 |
| `tip_limite` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `nm_marco` | `xsd:string` | true | 0..1 |
| `nro_marco` | `xsd:int` | true | 0..1 |

### `base_digital_continua:massa_agua_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hidrogr` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `tip_hidrog` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `cd_classif` | `xsd:int` | true | 0..1 |
| `cd_fluxo` | `xsd:int` | true | 0..1 |
| `cd_navegab` | `xsd:int` | true | 0..1 |
| `nm_rio_ass` | `xsd:string` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:massa_agua_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hidrogr` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `tip_hidrog` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `cd_classif` | `xsd:int` | true | 0..1 |
| `cd_fluxo` | `xsd:int` | true | 0..1 |
| `cd_navegab` | `xsd:int` | true | 0..1 |
| `nm_rio_ass` | `xsd:string` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:massa_agua_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hidrogr` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `tip_hidrog` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `cd_classif` | `xsd:int` | true | 0..1 |
| `cd_fluxo` | `xsd:int` | true | 0..1 |
| `cd_navegab` | `xsd:int` | true | 0..1 |
| `nm_rio_ass` | `xsd:string` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:pistas_aeroporto_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_sistema` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `nm_mun_ass` | `xsd:string` | true | 0..1 |
| `cd_tip_pis` | `xsd:int` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:pistas_aeroporto_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_sistema` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `nm_mun_ass` | `xsd:string` | true | 0..1 |
| `cd_tip_pis` | `xsd:int` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:pontes_pontos_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_sistema` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `nm_aci_atr` | `xsd:string` | true | 0..1 |
| `nm_via_ass` | `xsd:string` | true | 0..1 |
| `cd_tip_pon` | `xsd:int` | true | 0..1 |
| `cd_tip_via` | `xsd:int` | true | 0..1 |
| `cd_tip_aci` | `xsd:int` | true | 0..1 |
| `nr_angulo` | `xsd:int` | true | 0..1 |

### `base_digital_continua:pontes_pontos_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_sistema` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `nm_aci_atr` | `xsd:string` | true | 0..1 |
| `nm_via_ass` | `xsd:string` | true | 0..1 |
| `cd_tip_pon` | `xsd:int` | true | 0..1 |
| `cd_tip_via` | `xsd:int` | true | 0..1 |
| `cd_tip_aci` | `xsd:int` | true | 0..1 |
| `nr_angulo` | `xsd:int` | true | 0..1 |

### `base_digital_continua:pontes_pontos_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_sistema` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `cd_localiz` | `xsd:int` | true | 0..1 |

### `base_digital_continua:ponto_fiscal_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_sistema` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `nm_cidade` | `xsd:string` | true | 0..1 |
| `nm_posto` | `xsd:string` | true | 0..1 |
| `tip_posto` | `xsd:int` | true | 0..1 |

### `base_digital_continua:ponto_fiscal_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_sistema` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `nm_cidade` | `xsd:string` | true | 0..1 |
| `nm_posto` | `xsd:string` | true | 0..1 |
| `tip_posto` | `xsd:int` | true | 0..1 |

### `base_digital_continua:ponto_fiscal_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_sistema` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `nm_cidade` | `xsd:string` | true | 0..1 |
| `nm_posto` | `xsd:string` | true | 0..1 |
| `tip_posto` | `xsd:int` | true | 0..1 |

### `base_digital_continua:ponto_passagem_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_sistema` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `cd_tip_aci` | `xsd:int` | true | 0..1 |
| `cd_tip_pas` | `xsd:int` | true | 0..1 |
| `angulo` | `xsd:int` | true | 0..1 |

### `base_digital_continua:ponto_passagem_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_sistema` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `cd_tip_aci` | `xsd:int` | true | 0..1 |
| `cd_tip_pas` | `xsd:int` | true | 0..1 |
| `angulo` | `xsd:int` | true | 0..1 |

### `base_digital_continua:ponto_passagem_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_sistema` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `cd_tip_aci` | `xsd:int` | true | 0..1 |
| `cd_tip_pas` | `xsd:int` | true | 0..1 |
| `angulo` | `xsd:int` | true | 0..1 |

### `base_digital_continua:ponto_referencia_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_ponto` | `xsd:int` | true | 0..1 |
| `tip_ponto` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `nr_cota` | `xsd:int` | true | 0..1 |

### `base_digital_continua:ponto_referencia_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_ponto` | `xsd:int` | true | 0..1 |
| `tip_ponto` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `nr_cota` | `xsd:int` | true | 0..1 |

### `base_digital_continua:ponto_referencia_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_ponto` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `tip_ponto` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `nr_cota` | `xsd:int` | true | 0..1 |

### `base_digital_continua:pontos_cotados_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hipsogr` | `xsd:int` | true | 0..1 |
| `cota` | `xsd:int` | true | 0..1 |
| `tip_pon_co` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `cd_tip_cot` | `xsd:int` | true | 0..1 |

### `base_digital_continua:pontos_cotados_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hipsogr` | `xsd:int` | true | 0..1 |
| `cota` | `xsd:int` | true | 0..1 |
| `tip_pon_co` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `cd_tip_cot` | `xsd:int` | true | 0..1 |

### `base_digital_continua:pontos_cotados_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_hipsogr` | `xsd:int` | true | 0..1 |
| `cota` | `xsd:int` | true | 0..1 |
| `tip_pon_co` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `cd_tip_cot` | `xsd:int` | true | 0..1 |

### `base_digital_continua:prefixo_rodovias_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_sistema` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_prefix` | `xsd:int` | true | 0..1 |
| `angulo` | `xsd:int` | true | 0..1 |

### `base_digital_continua:prefixo_rodovias_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_sistema` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_prefix` | `xsd:int` | true | 0..1 |
| `angulo` | `xsd:int` | true | 0..1 |

### `base_digital_continua:terras_indigenas_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_limite` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `tip_limite` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:terras_indigenas_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_limite` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `tip_limite` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:terras_indigenas_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_limite` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `tip_limite` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:torres_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_obra` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_torre` | `xsd:int` | true | 0..1 |
| `nr_altura` | `xsd:double` | true | 0..1 |

### `base_digital_continua:torres_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_obra` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_torre` | `xsd:int` | true | 0..1 |
| `nr_altura` | `xsd:double` | true | 0..1 |

### `base_digital_continua:torres_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_obra` | `xsd:int` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `tip_torre` | `xsd:int` | true | 0..1 |
| `nr_altura` | `xsd:double` | true | 0..1 |

### `base_digital_continua:tunel_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_sistema` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `nm_aci_atr` | `xsd:string` | true | 0..1 |
| `nm_via_ass` | `xsd:string` | true | 0..1 |
| `cd_tip_via` | `xsd:int` | true | 0..1 |
| `cd_tip_aci` | `xsd:int` | true | 0..1 |
| `angulo` | `xsd:int` | true | 0..1 |

### `base_digital_continua:tunel_bdc_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_sistema` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `nm_aci_atr` | `xsd:string` | true | 0..1 |
| `nm_via_ass` | `xsd:string` | true | 0..1 |
| `cd_tip_via` | `xsd:int` | true | 0..1 |
| `cd_tip_aci` | `xsd:int` | true | 0..1 |
| `angulo` | `xsd:int` | true | 0..1 |

### `base_digital_continua:tunel_bdc_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `cd_sistema` | `xsd:int` | true | 0..1 |
| `dt_aquisic` | `xsd:date` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `dt_alterac` | `xsd:date` | true | 0..1 |
| `met_altera` | `xsd:int` | true | 0..1 |
| `fon_inf_al` | `xsd:int` | true | 0..1 |
| `fl_ind_nom` | `xsd:string` | true | 0..1 |
| `nm_aci_atr` | `xsd:string` | true | 0..1 |
| `nm_via_ass` | `xsd:string` | true | 0..1 |
| `cd_tip_via` | `xsd:int` | true | 0..1 |
| `cd_tip_aci` | `xsd:int` | true | 0..1 |
| `angulo` | `xsd:int` | true | 0..1 |

### `base_digital_continua:uso_da_terr_250_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `oid_` | `xsd:int` | true | 0..1 |
| `leg_250` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `area_m2` | `xsd:double` | true | 0..1 |
| `area_km2` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:uso_da_terra_1000_bdc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `oid_` | `xsd:int` | true | 0..1 |
| `leg_1000` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `area_m2` | `xsd:double` | true | 0..1 |
| `area_km2` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_digital_continua:uso_da_terra_100_bdc_`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `oid_` | `xsd:int` | true | 0..1 |
| `leg_100` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `area_m2` | `xsd:double` | true | 0..1 |
| `area_km2` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

## base_referencia_palmas (20)

### `base_referencia_palmas:sigp_areas_especiais_brp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid_1` | `xsd:double` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `unidades` | `xsd:string` | true | 0..1 |
| `dominio` | `xsd:string` | true | 0..1 |
| `fund_legal` | `xsd:string` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_le_1` | `xsd:double` | true | 0..1 |

### `base_referencia_palmas:sigp_borda_chapada_brp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `classes` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_referencia_palmas:sigp_cabeceira_brp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid_1` | `xsd:double` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `app` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `ex` | `xsd:string` | true | 0..1 |

### `base_referencia_palmas:sigp_curso_agua_brp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_le_1` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_referencia_palmas:sigp_curso_hidrico_brp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid_1` | `xsd:double` | true | 0..1 |
| `objectid_2` | `xsd:double` | true | 0..1 |
| `id` | `xsd:double` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `app` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `acres` | `xsd:double` | true | 0..1 |
| `hectares` | `xsd:double` | true | 0..1 |
| `shape_le_1` | `xsd:double` | true | 0..1 |
| `shape_le_2` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_referencia_palmas:sigp_curva_nivel_brp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `contour` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `tip_hipsog` | `xsd:string` | true | 0..1 |
| `shape_le_1` | `xsd:double` | true | 0..1 |

### `base_referencia_palmas:sigp_declividade_brp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `classes` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_referencia_palmas:sigp_edificacoes_brp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `id` | `xsd:double` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_referencia_palmas:sigp_espelho_agua_brp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `id` | `xsd:double` | true | 0..1 |
| `descr` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `acres` | `xsd:double` | true | 0..1 |
| `hectares` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_referencia_palmas:sigp_hidrografia_brp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid_1` | `xsd:double` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `cd_hidrogr` | `xsd:double` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `tip_hidrog` | `xsd:double` | true | 0..1 |
| `cd_fluxo` | `xsd:double` | true | 0..1 |
| `nm_rio_ass` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `app` | `xsd:string` | true | 0..1 |
| `codigo` | `xsd:double` | true | 0..1 |
| `largura` | `xsd:double` | true | 0..1 |
| `shape_le_1` | `xsd:double` | true | 0..1 |
| `shape_le_2` | `xsd:double` | true | 0..1 |

### `base_referencia_palmas:sigp_limite_municipal_brp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `left_fid` | `xsd:double` | true | 0..1 |
| `right_fid` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |

### `base_referencia_palmas:sigp_linha_pontes_brp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `id` | `xsd:double` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `lado` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |

### `base_referencia_palmas:sigp_mancha_urbana_brp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `id` | `xsd:double` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_referencia_palmas:sigp_rodovias_brp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid_1` | `xsd:double` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `nm_mun` | `xsd:string` | true | 0..1 |
| `juris` | `xsd:string` | true | 0..1 |
| `ext_km` | `xsd:double` | true | 0..1 |
| `base_2011` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `nm_via_1` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_le_1` | `xsd:double` | true | 0..1 |

### `base_referencia_palmas:sigp_rppn_brp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid_1` | `xsd:double` | true | 0..1 |
| `fid_rppn_p` | `xsd:double` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `nomerppn` | `xsd:string` | true | 0..1 |
| `dominio` | `xsd:string` | true | 0..1 |
| `ano` | `xsd:double` | true | 0..1 |
| `data_val` | `xsd:string` | true | 0..1 |
| `anos_cert` | `xsd:string` | true | 0..1 |
| `qualidade` | `xsd:double` | true | 0..1 |
| `baselegal` | `xsd:string` | true | 0..1 |
| `nomeimovel` | `xsd:string` | true | 0..1 |
| `codrural` | `xsd:string` | true | 0..1 |
| `comarca` | `xsd:string` | true | 0..1 |
| `proprietar` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `cep` | `xsd:string` | true | 0..1 |
| `complement` | `xsd:string` | true | 0..1 |
| `matricula` | `xsd:string` | true | 0..1 |
| `arearppn` | `xsd:double` | true | 0..1 |
| `areaprop` | `xsd:double` | true | 0..1 |
| `datacriaca` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_le_1` | `xsd:double` | true | 0..1 |
| `shape_le_2` | `xsd:double` | true | 0..1 |

### `base_referencia_palmas:sigp_topo_morro_brp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_referencia_palmas:sigp_unidade_conservacao_brp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `unidades` | `xsd:string` | true | 0..1 |
| `dominio` | `xsd:string` | true | 0..1 |
| `fund_legal` | `xsd:string` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_referencia_palmas:sigp_unidades_conservacao_municipal_brp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `id` | `xsd:double` | true | 0..1 |
| `uc_pd` | `xsd:string` | true | 0..1 |
| `nenhum` | `xsd:double` | true | 0..1 |
| `area_ha_1` | `xsd:double` | true | 0..1 |
| `area_m` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_referencia_palmas:sigp_vias_interurbanas_brp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid_1` | `xsd:double` | true | 0..1 |
| `objectid_2` | `xsd:double` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `nm_mun` | `xsd:string` | true | 0..1 |
| `juris` | `xsd:string` | true | 0..1 |
| `ext_km` | `xsd:double` | true | 0..1 |
| `base_2011` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_le_1` | `xsd:double` | true | 0..1 |

### `base_referencia_palmas:sigp_vias_urbanas_brp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid_1` | `xsd:double` | true | 0..1 |
| `objectid_2` | `xsd:double` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `nm_mun` | `xsd:string` | true | 0..1 |
| `juris` | `xsd:string` | true | 0..1 |
| `ext_km` | `xsd:double` | true | 0..1 |
| `base_2011` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_le_1` | `xsd:double` | true | 0..1 |

## base_tematica_norte_tocantins (26)

### `base_tematica_norte_tocantins:abacaxi_nt`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `abacaxi_` | `xsd:double` | true | 0..1 |
| `abacaxi_id` | `xsd:double` | true | 0..1 |
| `sprclasse` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_norte_tocantins:acai_nt`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `acai_` | `xsd:double` | true | 0..1 |
| `acai_id` | `xsd:double` | true | 0..1 |
| `sprclasse` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_norte_tocantins:aptidao`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `apt_` | `xsd:double` | true | 0..1 |
| `apt_id` | `xsd:double` | true | 0..1 |
| `aptidao` | `xsd:string` | true | 0..1 |
| `simbolos` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_norte_tocantins:arroz_medio_nt_`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `am_` | `xsd:double` | true | 0..1 |
| `am_id` | `xsd:double` | true | 0..1 |
| `sprclasse` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `inicio` | `xsd:date` | true | 0..1 |
| `fim` | `xsd:date` | true | 0..1 |

### `base_tematica_norte_tocantins:arroz_precoce_nt`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `ap_` | `xsd:double` | true | 0..1 |
| `ap_id` | `xsd:double` | true | 0..1 |
| `sprclasse` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `inicio` | `xsd:date` | true | 0..1 |
| `fim` | `xsd:date` | true | 0..1 |

### `base_tematica_norte_tocantins:banana_nt`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `banana_` | `xsd:double` | true | 0..1 |
| `banana_id` | `xsd:double` | true | 0..1 |
| `sprclasse` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_norte_tocantins:caju_nt`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `caju_` | `xsd:double` | true | 0..1 |
| `caju_id` | `xsd:double` | true | 0..1 |
| `sprclasse` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_norte_tocantins:cobertura_e_uso_terra`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `uso_` | `xsd:double` | true | 0..1 |
| `uso_id` | `xsd:double` | true | 0..1 |
| `nivel_i` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_norte_tocantins:cupuacu`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `cupuacu_` | `xsd:double` | true | 0..1 |
| `cupuacu_id` | `xsd:double` | true | 0..1 |
| `sprclasse` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_norte_tocantins:feijao_caupi_nt`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `ca_` | `xsd:double` | true | 0..1 |
| `ca_id` | `xsd:double` | true | 0..1 |
| `sprclasse` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `inicio` | `xsd:date` | true | 0..1 |
| `fim` | `xsd:date` | true | 0..1 |

### `base_tematica_norte_tocantins:feijao_precoce_nt`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `fp_` | `xsd:double` | true | 0..1 |
| `fp_id` | `xsd:double` | true | 0..1 |
| `sprclasse` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `inicio` | `xsd:date` | true | 0..1 |
| `fim` | `xsd:date` | true | 0..1 |

### `base_tematica_norte_tocantins:feijao_tardio_nt`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `ft_` | `xsd:double` | true | 0..1 |
| `ft_id` | `xsd:double` | true | 0..1 |
| `sprclasse` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `inicio` | `xsd:date` | true | 0..1 |
| `fim` | `xsd:date` | true | 0..1 |

### `base_tematica_norte_tocantins:geologia`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `geog_` | `xsd:double` | true | 0..1 |
| `geog_id` | `xsd:double` | true | 0..1 |
| `classes` | `xsd:string` | true | 0..1 |
| `vul_geo` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_norte_tocantins:geomorfologia`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `dissec` | `xsd:string` | true | 0..1 |
| `uni_geom` | `xsd:string` | true | 0..1 |
| `vul_geom` | `xsd:double` | true | 0..1 |
| `layout` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_norte_tocantins:girassol_nt`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `gi_` | `xsd:double` | true | 0..1 |
| `gi_id` | `xsd:double` | true | 0..1 |
| `sprclasse` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `inicio` | `xsd:date` | true | 0..1 |
| `fim` | `xsd:date` | true | 0..1 |

### `base_tematica_norte_tocantins:manga_nt`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `manga_` | `xsd:double` | true | 0..1 |
| `manga_id` | `xsd:double` | true | 0..1 |
| `sprclasse` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_norte_tocantins:milho_nt`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `mm_` | `xsd:double` | true | 0..1 |
| `mm_id` | `xsd:double` | true | 0..1 |
| `sprclasse` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `inicio` | `xsd:date` | true | 0..1 |
| `fim` | `xsd:date` | true | 0..1 |

### `base_tematica_norte_tocantins:murici_nt`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `murici_` | `xsd:double` | true | 0..1 |
| `murici_id` | `xsd:double` | true | 0..1 |
| `sprclasse` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_norte_tocantins:plano_uso_vegetacao_nt`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `utbun_` | `xsd:double` | true | 0..1 |
| `utbun_id` | `xsd:double` | true | 0..1 |
| `puveg1` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `hectares` | `xsd:double` | true | 0..1 |

### `base_tematica_norte_tocantins:regioes_fitoecologicas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `r_ft_ct` | `xsd:string` | true | 0..1 |
| `form_domin` | `xsd:string` | true | 0..1 |
| `form_assoc` | `xsd:string` | true | 0..1 |

### `base_tematica_norte_tocantins:soja_precoce_nt`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `sp_` | `xsd:double` | true | 0..1 |
| `sp_id` | `xsd:double` | true | 0..1 |
| `sprclasse` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `inicio` | `xsd:date` | true | 0..1 |
| `fim` | `xsd:date` | true | 0..1 |

### `base_tematica_norte_tocantins:soja_tardio_nt`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `st_` | `xsd:double` | true | 0..1 |
| `st_id` | `xsd:double` | true | 0..1 |
| `sprclasse` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `inicio` | `xsd:date` | true | 0..1 |
| `fim` | `xsd:date` | true | 0..1 |

### `base_tematica_norte_tocantins:solos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `solog_` | `xsd:double` | true | 0..1 |
| `solog_i` | `xsd:double` | true | 0..1 |
| `solos` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_norte_tocantins:unidades_territoriais_basicas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `utbg_` | `xsd:double` | true | 0..1 |
| `utbg_id` | `xsd:double` | true | 0..1 |
| `zonas` | `xsd:string` | true | 0..1 |
| `z2` | `xsd:double` | true | 0..1 |
| `clamb` | `xsd:string` | true | 0..1 |
| `so` | `xsd:string` | true | 0..1 |
| `apt` | `xsd:string` | true | 0..1 |
| `vulnb` | `xsd:string` | true | 0..1 |
| `cbus` | `xsd:string` | true | 0..1 |
| `plus` | `xsd:string` | true | 0..1 |
| `unid` | `xsd:double` | true | 0..1 |
| `frut` | `xsd:string` | true | 0..1 |
| `uso_veg` | `xsd:string` | true | 0..1 |
| `amb_fito` | `xsd:string` | true | 0..1 |
| `puva` | `xsd:string` | true | 0..1 |
| `puveg1` | `xsd:string` | true | 0..1 |
| `agri` | `xsd:string` | true | 0..1 |
| `fruti` | `xsd:string` | true | 0..1 |
| `agpec` | `xsd:string` | true | 0..1 |
| `zona1` | `xsd:string` | true | 0..1 |
| `cobuso` | `xsd:string` | true | 0..1 |
| `geologia` | `xsd:string` | true | 0..1 |
| `geomorfo` | `xsd:string` | true | 0..1 |
| `solos` | `xsd:string` | true | 0..1 |
| `precipit` | `xsd:double` | true | 0..1 |
| `disseca` | `xsd:string` | true | 0..1 |
| `vul_uso` | `xsd:double` | true | 0..1 |
| `vul_geo` | `xsd:double` | true | 0..1 |
| `vul_geom` | `xsd:double` | true | 0..1 |
| `vul_solo` | `xsd:double` | true | 0..1 |
| `vul_preci` | `xsd:double` | true | 0..1 |
| `vul_final` | `xsd:double` | true | 0..1 |
| `vulnerabi` | `xsd:string` | true | 0..1 |
| `num_aptdao` | `xsd:double` | true | 0..1 |
| `num_cobuso` | `xsd:double` | true | 0..1 |
| `num_geolo` | `xsd:double` | true | 0..1 |
| `num_unigeo` | `xsd:double` | true | 0..1 |
| `num_solo` | `xsd:double` | true | 0..1 |
| `num_dissic` | `xsd:double` | true | 0..1 |
| `num_zona_f` | `xsd:double` | true | 0..1 |
| `zona_resum` | `xsd:string` | true | 0..1 |
| `cobambi` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_norte_tocantins:vulnerabilidade_paisagens_nt`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `vuln_` | `xsd:double` | true | 0..1 |
| `vuln_id` | `xsd:double` | true | 0..1 |
| `vulnera` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_norte_tocantins:zoneamento_ecolog_econ_nt`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `zonas_resu` | `xsd:string` | true | 0..1 |
| `cnt_zonas_` | `xsd:double` | true | 0..1 |

## base_tematica_palmas (7)

### `base_tematica_palmas:cob_uso_100mil_btp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `leg_100` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_le_1` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_palmas:cob_uso_2011_final_btp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `legenda` | `xsd:string` | true | 0..1 |
| `leg_25` | `xsd:string` | true | 0..1 |
| `leg_50` | `xsd:string` | true | 0..1 |
| `leg_100` | `xsd:string` | true | 0..1 |
| `leg_250` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_palmas:cob_uso_250mil_btp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `leg_250` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_le_1` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_palmas:cob_uso_50mil_btp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `leg_50` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_le_1` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_palmas:sigp_bacias_btp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid_1` | `xsd:double` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `bacia` | `xsd:string` | true | 0..1 |
| `cod_bacia` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_le_1` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_palmas:sigp_pontos_referencia_btp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `id` | `xsd:double` | true | 0..1 |
| `descricao` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |

### `base_tematica_palmas:sigp_sub_bacias_btp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid_1` | `xsd:double` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `subbacia` | `xsd:string` | true | 0..1 |
| `bacia` | `xsd:string` | true | 0..1 |
| `cod_bacias` | `xsd:double` | true | 0..1 |
| `cod_subbac` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `acres` | `xsd:double` | true | 0..1 |
| `hectares` | `xsd:double` | true | 0..1 |
| `shape_le_1` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

## base_tematica_sudeste_tocantins (29)

### `base_tematica_sudeste_tocantins:adequacao_uso`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `join_obj` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `aptidao_1` | `xsd:string` | true | 0..1 |
| `apt_ind` | `xsd:string` | true | 0..1 |
| `subtipos_f` | `xsd:string` | true | 0..1 |
| `nivel_iii` | `xsd:string` | true | 0..1 |
| `clas_vulne` | `xsd:string` | true | 0..1 |
| `adeq_uso` | `xsd:string` | true | 0..1 |
| `nivel_i` | `xsd:string` | true | 0..1 |
| `ade_uso` | `xsd:string` | true | 0..1 |

### `base_tematica_sudeste_tocantins:aptidao_agricola_st`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `leg_apt` | `xsd:string` | true | 0..1 |
| `desc_apt` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `leg_mapa` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_sudeste_tocantins:areaminerae_st`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_sudeste_tocantins:articulacao_100mil_st`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `oid_` | `xsd:double` | true | 0..1 |
| `id` | `xsd:double` | true | 0..1 |
| `ind_nomenc` | `xsd:string` | true | 0..1 |
| `mi` | `xsd:string` | true | 0..1 |
| `nome_carta` | `xsd:string` | true | 0..1 |
| `orgao` | `xsd:string` | true | 0..1 |
| `escal_plot` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `faixa` | `xsd:string` | true | 0..1 |
| `shape_le_1` | `xsd:double` | true | 0..1 |
| `sub_faixa` | `xsd:string` | true | 0..1 |
| `shape_le_2` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_sudeste_tocantins:articulacao_100mil_st_especial`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid_2` | `xsd:double` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `oid_` | `xsd:double` | true | 0..1 |
| `id` | `xsd:double` | true | 0..1 |
| `ind_nomenc` | `xsd:string` | true | 0..1 |
| `mi` | `xsd:string` | true | 0..1 |
| `nome_carta` | `xsd:string` | true | 0..1 |
| `orgao` | `xsd:string` | true | 0..1 |
| `escal_plot` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `faixa` | `xsd:string` | true | 0..1 |
| `shape_le_1` | `xsd:double` | true | 0..1 |
| `sub_faixa` | `xsd:string` | true | 0..1 |
| `shape_le_2` | `xsd:double` | true | 0..1 |
| `alteradas` | `xsd:string` | true | 0..1 |
| `shape_le_3` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_sudeste_tocantins:articulacao_50mil_st`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `carta` | `xsd:string` | true | 0..1 |
| `fuso` | `xsd:string` | true | 0..1 |
| `faixa` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `folha_100m` | `xsd:string` | true | 0..1 |
| `mi_100mil` | `xsd:string` | true | 0..1 |
| `folha_50mi` | `xsd:string` | true | 0..1 |
| `mi_50mil` | `xsd:string` | true | 0..1 |
| `escal_plot` | `xsd:double` | true | 0..1 |
| `shape_le_1` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_sudeste_tocantins:articulacao_50mil_st_especial`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid_2` | `xsd:double` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `carta` | `xsd:string` | true | 0..1 |
| `fuso` | `xsd:string` | true | 0..1 |
| `faixa` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `escal_plot` | `xsd:double` | true | 0..1 |
| `shape_le_1` | `xsd:double` | true | 0..1 |
| `folha_100m` | `xsd:string` | true | 0..1 |
| `mi_100mil` | `xsd:string` | true | 0..1 |
| `folha_50mi` | `xsd:string` | true | 0..1 |
| `mi_50mil` | `xsd:string` | true | 0..1 |
| `alteradas` | `xsd:string` | true | 0..1 |
| `shape_le_2` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_sudeste_tocantins:caverna_ponto_st`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `cod_canie_` | `xsd:string` | true | 0..1 |
| `fid__n_9_0` | `xsd:int` | true | 0..1 |
| `caverna_c_` | `xsd:string` | true | 0..1 |
| `latitude_n` | `xsd:double` | true | 0..1 |
| `longitude_` | `xsd:double` | true | 0..1 |
| `altitude_n` | `xsd:int` | true | 0..1 |
| `compila_c_` | `xsd:string` | true | 0..1 |
| `uf_c_254` | `xsd:string` | true | 0..1 |
| `munic_pio_` | `xsd:string` | true | 0..1 |
| `codigo_ibg` | `xsd:int` | true | 0..1 |
| `em_uc_c_25` | `xsd:string` | true | 0..1 |
| `em_uc_trab` | `xsd:string` | true | 0..1 |
| `uc_federal` | `xsd:string` | true | 0..1 |
| `nome_uc_c_` | `xsd:string` | true | 0..1 |
| `pi_ou_us_c` | `xsd:string` | true | 0..1 |
| `ano_base_c` | `xsd:string` | true | 0..1 |
| `valida_c_2` | `xsd:string` | true | 0..1 |
| `litologia_` | `xsd:string` | true | 0..1 |
| `bioma_c_25` | `xsd:string` | true | 0..1 |

### `base_tematica_sudeste_tocantins:cob_uso_st`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nivel_i_cb` | `xsd:string` | true | 0..1 |
| `nivel_ii_c` | `xsd:string` | true | 0..1 |
| `nivel_iii_` | `xsd:string` | true | 0..1 |
| `assoc_cb` | `xsd:string` | true | 0..1 |
| `sigla_100` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_sudeste_tocantins:cobusorse_pol50_`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nivel_i_cb` | `xsd:string` | true | 0..1 |
| `nivel_ii_c` | `xsd:string` | true | 0..1 |
| `nivel_iii_` | `xsd:string` | true | 0..1 |
| `assoc_cb` | `xsd:string` | true | 0..1 |
| `leg_sim_cb` | `xsd:string` | true | 0..1 |
| `leg_fim_cb` | `xsd:string` | true | 0..1 |
| `sigla_100` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_sudeste_tocantins:escassezhidrica_clima_pol50_st`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `esc_hidric` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_sudeste_tocantins:escassezhidricarse_pol50_gcs`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `pot_cav` | `xsd:string` | true | 0..1 |
| `calcario` | `xsd:string` | true | 0..1 |
| `aquifero` | `xsd:string` | true | 0..1 |
| `modelado` | `xsd:string` | true | 0..1 |
| `decliv` | `xsd:string` | true | 0..1 |
| `unidades_g` | `xsd:string` | true | 0..1 |
| `simb_rel` | `xsd:string` | true | 0..1 |
| `desc_rel` | `xsd:string` | true | 0..1 |
| `ampl_rel` | `xsd:string` | true | 0..1 |
| `ordens` | `xsd:string` | true | 0..1 |
| `subordens` | `xsd:string` | true | 0..1 |
| `simb_solo` | `xsd:string` | true | 0..1 |
| `desc_solo` | `xsd:string` | true | 0..1 |
| `zae_to` | `xsd:string` | true | 0..1 |
| `leg_apt` | `xsd:string` | true | 0..1 |
| `desc_apt` | `xsd:string` | true | 0..1 |
| `siamb_f` | `xsd:string` | true | 0..1 |
| `regiao_f` | `xsd:string` | true | 0..1 |
| `formacao_f` | `xsd:string` | true | 0..1 |
| `subtipo_f` | `xsd:string` | true | 0..1 |
| `leg_sim_f` | `xsd:string` | true | 0..1 |
| `assoc_f` | `xsd:string` | true | 0..1 |
| `leg_fim_f` | `xsd:string` | true | 0..1 |
| `nivel_i_cb` | `xsd:string` | true | 0..1 |
| `nivel_ii_c` | `xsd:string` | true | 0..1 |
| `nivel_iii_` | `xsd:string` | true | 0..1 |
| `assoc_cb` | `xsd:string` | true | 0..1 |
| `leg_sim_cb` | `xsd:string` | true | 0..1 |
| `leg_fim_cb` | `xsd:string` | true | 0..1 |
| `up` | `xsd:string` | true | 0..1 |
| `pcp_anual` | `xsd:string` | true | 0..1 |
| `pcp_chuv` | `xsd:string` | true | 0..1 |
| `pcp_seco` | `xsd:string` | true | 0..1 |
| `tmed_anual` | `xsd:string` | true | 0..1 |
| `tmed_chuv` | `xsd:string` | true | 0..1 |
| `tmed_seco` | `xsd:string` | true | 0..1 |
| `ur_anual` | `xsd:string` | true | 0..1 |
| `ur_chuv` | `xsd:string` | true | 0..1 |
| `ur_seco` | `xsd:string` | true | 0..1 |
| `eto_anual` | `xsd:string` | true | 0..1 |
| `eto_chuv` | `xsd:string` | true | 0..1 |
| `eto_seco` | `xsd:string` | true | 0..1 |
| `dh_anual` | `xsd:string` | true | 0..1 |
| `unep_anual` | `xsd:string` | true | 0..1 |
| `ih_anual` | `xsd:string` | true | 0..1 |
| `iu_anual` | `xsd:string` | true | 0..1 |
| `varclim_eh` | `xsd:double` | true | 0..1 |
| `dh_datual` | `xsd:double` | true | 0..1 |
| `dh_2022` | `xsd:double` | true | 0..1 |
| `dh_2027` | `xsd:double` | true | 0..1 |
| `dh_2037` | `xsd:double` | true | 0..1 |
| `dh_req90` | `xsd:double` | true | 0..1 |
| `dh_dq90` | `xsd:double` | true | 0..1 |
| `dh_d75q90` | `xsd:double` | true | 0..1 |
| `peh_id` | `xsd:double` | true | 0..1 |
| `peh_class` | `xsd:string` | true | 0..1 |
| `vi_apl` | `xsd:double` | true | 0..1 |
| `vi_geo` | `xsd:double` | true | 0..1 |
| `vi_geom` | `xsd:double` | true | 0..1 |
| `vi_decl` | `xsd:double` | true | 0..1 |
| `vi_geom_me` | `xsd:double` | true | 0..1 |
| `vi_solo` | `xsd:double` | true | 0..1 |
| `vi_clim` | `xsd:double` | true | 0..1 |
| `vi_cbuso` | `xsd:double` | true | 0..1 |
| `vi_final` | `xsd:double` | true | 0..1 |
| `clas_vulne` | `xsd:string` | true | 0..1 |
| `dominios_n` | `xsd:string` | true | 0..1 |
| `sigla_lito` | `xsd:string` | true | 0..1 |
| `desc_lito_` | `xsd:string` | true | 0..1 |
| `leg_lito_1` | `xsd:string` | true | 0..1 |
| `dominio_za` | `xsd:string` | true | 0..1 |
| `regiao_zae` | `xsd:string` | true | 0..1 |
| `setor_zae` | `xsd:string` | true | 0..1 |
| `unidade_za` | `xsd:string` | true | 0..1 |
| `adq_uso` | `xsd:string` | true | 0..1 |
| `sig_adq_us` | `xsd:string` | true | 0..1 |
| `ubc_` | `xsd:string` | true | 0..1 |
| `sisnat` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_sudeste_tocantins:estruturas_geologia_linha250_st`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `estrutura` | `xsd:string` | true | 0..1 |
| `nmestrutur` | `xsd:string` | true | 0..1 |
| `sentido_de` | `xsd:string` | true | 0..1 |
| `ang_norte` | `xsd:int` | true | 0..1 |
| `mergulho` | `xsd:int` | true | 0..1 |
| `desloc` | `xsd:int` | true | 0..1 |
| `idade_desl` | `xsd:int` | true | 0..1 |
| `sentido` | `xsd:string` | true | 0..1 |
| `evento_oro` | `xsd:string` | true | 0..1 |
| `regime_tec` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `rumo` | `xsd:string` | true | 0..1 |
| `origem` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |

### `base_tematica_sudeste_tocantins:geologia_st`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `pot_cav` | `xsd:string` | true | 0..1 |
| `calcario` | `xsd:string` | true | 0..1 |
| `aquifero` | `xsd:string` | true | 0..1 |
| `dominios_n` | `xsd:string` | true | 0..1 |
| `leg_rgb` | `xsd:string` | true | 0..1 |
| `unidade` | `xsd:string` | true | 0..1 |
| `leg_und` | `xsd:string` | true | 0..1 |
| `eon` | `xsd:string` | true | 0..1 |
| `era` | `xsd:string` | true | 0..1 |
| `periodo` | `xsd:string` | true | 0..1 |
| `epoca` | `xsd:string` | true | 0..1 |
| `idade_max` | `xsd:string` | true | 0..1 |
| `litologia` | `xsd:string` | true | 0..1 |
| `prov_hidro` | `xsd:string` | true | 0..1 |
| `dom_hidrog` | `xsd:string` | true | 0..1 |
| `subdm_hidr` | `xsd:string` | true | 0..1 |
| `sigl_subdo` | `xsd:string` | true | 0..1 |
| `pot_aquif` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_sudeste_tocantins:geomorfologia_tematica_se`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `modelado` | `xsd:string` | true | 0..1 |
| `decliv` | `xsd:string` | true | 0..1 |
| `unidades_g` | `xsd:string` | true | 0..1 |
| `simb_rel` | `xsd:string` | true | 0..1 |
| `desc_rel` | `xsd:string` | true | 0..1 |
| `ampl_rel` | `xsd:string` | true | 0..1 |
| `vi_apl` | `xsd:double` | true | 0..1 |
| `vi_geom` | `xsd:double` | true | 0..1 |
| `vi_decl` | `xsd:double` | true | 0..1 |
| `vi_geom_me` | `xsd:double` | true | 0..1 |
| `dominios_n` | `xsd:string` | true | 0..1 |
| `dom_morfes` | `xsd:string` | true | 0..1 |
| `sigla_un` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_sudeste_tocantins:hidrogeologia_st_`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `pot_cav` | `xsd:string` | true | 0..1 |
| `calcario` | `xsd:string` | true | 0..1 |
| `aquifero` | `xsd:string` | true | 0..1 |
| `dominios_n` | `xsd:string` | true | 0..1 |
| `leg_rgb` | `xsd:string` | true | 0..1 |
| `unidade` | `xsd:string` | true | 0..1 |
| `leg_und` | `xsd:string` | true | 0..1 |
| `eon` | `xsd:string` | true | 0..1 |
| `era` | `xsd:string` | true | 0..1 |
| `periodo` | `xsd:string` | true | 0..1 |
| `epoca` | `xsd:string` | true | 0..1 |
| `idade_max` | `xsd:string` | true | 0..1 |
| `litologia` | `xsd:string` | true | 0..1 |
| `prov_hidro` | `xsd:string` | true | 0..1 |
| `dom_hidrog` | `xsd:string` | true | 0..1 |
| `subdm_hidr` | `xsd:string` | true | 0..1 |
| `sigl_subdo` | `xsd:string` | true | 0..1 |
| `pot_aquif` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_sudeste_tocantins:pedologia_st`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `ordens` | `xsd:string` | true | 0..1 |
| `subordens` | `xsd:string` | true | 0..1 |
| `simb_solo` | `xsd:string` | true | 0..1 |
| `desc_solo` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_le_1` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `simb_100` | `xsd:string` | true | 0..1 |

### `base_tematica_sudeste_tocantins:pocoprofundo_ponto100_st`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `ponto` | `xsd:double` | true | 0..1 |
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `latitude_d` | `xsd:double` | true | 0..1 |
| `longitude_` | `xsd:double` | true | 0..1 |
| `utme` | `xsd:double` | true | 0..1 |
| `utmn` | `xsd:double` | true | 0..1 |
| `cota` | `xsd:double` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `prof_m_` | `xsd:double` | true | 0..1 |
| `vazao_esta` | `xsd:double` | true | 0..1 |
| `ne` | `xsd:double` | true | 0..1 |
| `nd` | `xsd:double` | true | 0..1 |
| `vazao_espe` | `xsd:double` | true | 0..1 |
| `carga_hidr` | `xsd:double` | true | 0..1 |
| `ce` | `xsd:string` | true | 0..1 |
| `odor` | `xsd:string` | true | 0..1 |
| `t_c` | `xsd:string` | true | 0..1 |
| `cor` | `xsd:string` | true | 0..1 |
| `ph` | `xsd:string` | true | 0..1 |
| `solidos_su` | `xsd:string` | true | 0..1 |
| `turbidez` | `xsd:string` | true | 0..1 |
| `natureza` | `xsd:string` | true | 0..1 |
| `aquifero` | `xsd:string` | true | 0..1 |
| `nome_unida` | `xsd:string` | true | 0..1 |
| `subgrupo_f` | `xsd:string` | true | 0..1 |
| `condicao` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `bacia` | `xsd:string` | true | 0..1 |
| `subbacia` | `xsd:string` | true | 0..1 |
| `uso_agua` | `xsd:string` | true | 0..1 |
| `tipo_capta` | `xsd:string` | true | 0..1 |
| `nivel_agua` | `xsd:string` | true | 0..1 |
| `vazao` | `xsd:string` | true | 0..1 |
| `tipo_teste` | `xsd:string` | true | 0..1 |
| `tipo_bomba` | `xsd:string` | true | 0..1 |
| `data_anali` | `xsd:string` | true | 0..1 |
| `surgencia` | `xsd:string` | true | 0..1 |
| `data_colet` | `xsd:string` | true | 0..1 |
| `data_insta` | `xsd:string` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `f44` | `xsd:string` | true | 0..1 |

### `base_tematica_sudeste_tocantins:potencial_caverna_st`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `metodologi` | `xsd:string` | true | 0..1 |
| `grau_de_po` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_le_1` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_sudeste_tocantins:projetobarraginhasponto_st`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `cidade` | `xsd:string` | true | 0..1 |
| `fuso` | `xsd:int` | true | 0..1 |
| `x` | `xsd:int` | true | 0..1 |
| `y` | `xsd:int` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `bacia_hidr` | `xsd:string` | true | 0..1 |
| `peh` | `xsd:int` | true | 0..1 |
| `vulnera` | `xsd:string` | true | 0..1 |
| `mcp` | `xsd:string` | true | 0..1 |
| `uso` | `xsd:string` | true | 0..1 |
| `app` | `xsd:string` | true | 0..1 |

### `base_tematica_sudeste_tocantins:regiaofitoecologica_pol50_st`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `regioes` | `xsd:string` | true | 0..1 |
| `formacoes` | `xsd:string` | true | 0..1 |
| `subtipos_f` | `xsd:string` | true | 0..1 |
| `leg_simple` | `xsd:string` | true | 0..1 |
| `asso_cont` | `xsd:string` | true | 0..1 |
| `leg_final` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_sudeste_tocantins:titulominerariopol100_gcs_st`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `processo` | `xsd:string` | true | 0..1 |
| `id` | `xsd:string` | true | 0..1 |
| `numero` | `xsd:int` | true | 0..1 |
| `ano` | `xsd:int` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `fase` | `xsd:string` | true | 0..1 |
| `ult_evento` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `subs` | `xsd:string` | true | 0..1 |
| `uso` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_sudeste_tocantins:turismo_st`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `descricao` | `xsd:string` | true | 0..1 |

### `base_tematica_sudeste_tocantins:ubc_pol50_mi_completo_4674`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nm_lit` | `xsd:string` | true | 0..1 |
| `desc_lit` | `xsd:string` | true | 0..1 |
| `nm_rel` | `xsd:string` | true | 0..1 |
| `desc_rel` | `xsd:string` | true | 0..1 |
| `sigla_sol` | `xsd:string` | true | 0..1 |
| `nm_sol` | `xsd:string` | true | 0..1 |
| `desc_sol` | `xsd:string` | true | 0..1 |
| `nm_cli` | `xsd:string` | true | 0..1 |
| `desc_cli` | `xsd:string` | true | 0..1 |
| `nm_pot` | `xsd:string` | true | 0..1 |
| `desc_pot` | `xsd:string` | true | 0..1 |
| `ubc` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `ubc_num` | `xsd:double` | true | 0..1 |

### `base_tematica_sudeste_tocantins:unidades_de_paisagem_st`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nm_lit` | `xsd:string` | true | 0..1 |
| `desc_lit` | `xsd:string` | true | 0..1 |
| `nm_rel` | `xsd:string` | true | 0..1 |
| `desc_rel` | `xsd:string` | true | 0..1 |
| `sigla_sol` | `xsd:string` | true | 0..1 |
| `nm_sol` | `xsd:string` | true | 0..1 |
| `desc_sol` | `xsd:string` | true | 0..1 |
| `nm_cli` | `xsd:string` | true | 0..1 |
| `desc_cli` | `xsd:string` | true | 0..1 |
| `nm_pot` | `xsd:string` | true | 0..1 |
| `desc_pot` | `xsd:string` | true | 0..1 |
| `ubc` | `xsd:string` | true | 0..1 |
| `leg_simple` | `xsd:string` | true | 0..1 |
| `assoc_cont` | `xsd:string` | true | 0..1 |
| `regioes` | `xsd:string` | true | 0..1 |
| `formacoes` | `xsd:string` | true | 0..1 |
| `subtipos_f` | `xsd:string` | true | 0..1 |
| `leg_final` | `xsd:string` | true | 0..1 |
| `nivel_i` | `xsd:string` | true | 0..1 |
| `nivel_ii` | `xsd:string` | true | 0..1 |
| `nivel_iii` | `xsd:string` | true | 0..1 |
| `assoc` | `xsd:string` | true | 0..1 |
| `leg_uso_si` | `xsd:string` | true | 0..1 |
| `leg_uso_fi` | `xsd:string` | true | 0..1 |
| `cobuso` | `xsd:string` | true | 0..1 |
| `up` | `xsd:string` | true | 0..1 |
| `orig_fid` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_sudeste_tocantins:up_pol50_norte`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `ubc` | `xsd:string` | true | 0..1 |
| `cobuso_leg` | `xsd:string` | true | 0..1 |
| `up` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_sudeste_tocantins:up_pol50_sul`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nm_lit` | `xsd:string` | true | 0..1 |
| `desc_lit` | `xsd:string` | true | 0..1 |
| `nm_rel` | `xsd:string` | true | 0..1 |
| `desc_rel` | `xsd:string` | true | 0..1 |
| `sigla_sol` | `xsd:string` | true | 0..1 |
| `nm_sol` | `xsd:string` | true | 0..1 |
| `desc_sol` | `xsd:string` | true | 0..1 |
| `nm_cli` | `xsd:string` | true | 0..1 |
| `desc_cli` | `xsd:string` | true | 0..1 |
| `nm_pot` | `xsd:string` | true | 0..1 |
| `desc_pot` | `xsd:string` | true | 0..1 |
| `ubc` | `xsd:string` | true | 0..1 |
| `leg_simple` | `xsd:string` | true | 0..1 |
| `assoc_cont` | `xsd:string` | true | 0..1 |
| `regioes` | `xsd:string` | true | 0..1 |
| `formacoes` | `xsd:string` | true | 0..1 |
| `subtipos_f` | `xsd:string` | true | 0..1 |
| `leg_final` | `xsd:string` | true | 0..1 |
| `nivel_i` | `xsd:string` | true | 0..1 |
| `nivel_ii` | `xsd:string` | true | 0..1 |
| `nivel_iii` | `xsd:string` | true | 0..1 |
| `assoc` | `xsd:string` | true | 0..1 |
| `leg_uso_si` | `xsd:string` | true | 0..1 |
| `leg_uso_fi` | `xsd:string` | true | 0..1 |
| `cobuso` | `xsd:string` | true | 0..1 |
| `up` | `xsd:string` | true | 0..1 |
| `orig_fid` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_sudeste_tocantins:vereda_st`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geometriaa` | `xsd:int` | true | 0..1 |
| `clei` | `xsd:int` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_sudeste_tocantins:vulnerabilidade_st`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `vi_apl` | `xsd:double` | true | 0..1 |
| `vi_geo` | `xsd:double` | true | 0..1 |
| `vi_geom` | `xsd:double` | true | 0..1 |
| `vi_decl` | `xsd:double` | true | 0..1 |
| `vi_geom_me` | `xsd:double` | true | 0..1 |
| `vi_solo` | `xsd:double` | true | 0..1 |
| `vi_clim` | `xsd:double` | true | 0..1 |
| `vi_cbuso` | `xsd:double` | true | 0..1 |
| `vi_final` | `xsd:double` | true | 0..1 |
| `clas_vulne` | `xsd:string` | true | 0..1 |
| `vi_fin_arr` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

## base_tematica_tocantins (66)

### `base_tematica_tocantins:atrativos_turistico_cientifico_2012`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `id` | `xsd:decimal` | true | 0..1 |

### `base_tematica_tocantins:bacias_hidro_2000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `fid_` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `a172bac_` | `xsd:double` | true | 0..1 |
| `a172bac_id` | `xsd:double` | true | 0..1 |
| `classes` | `xsd:string` | true | 0..1 |
| `a173bac_` | `xsd:double` | true | 0..1 |
| `a173bac_id` | `xsd:double` | true | 0..1 |
| `a199bac_` | `xsd:double` | true | 0..1 |
| `a199bac_id` | `xsd:double` | true | 0..1 |
| `a200bac_` | `xsd:double` | true | 0..1 |
| `a200bac_id` | `xsd:double` | true | 0..1 |
| `a226bac_` | `xsd:double` | true | 0..1 |
| `a226bac_id` | `xsd:double` | true | 0..1 |
| `a227bac_` | `xsd:double` | true | 0..1 |
| `a227bac_id` | `xsd:double` | true | 0..1 |
| `a278bac_` | `xsd:double` | true | 0..1 |
| `a278bac_id` | `xsd:double` | true | 0..1 |
| `a279bac_` | `xsd:double` | true | 0..1 |
| `a279bac_id` | `xsd:double` | true | 0..1 |
| `a303bac_` | `xsd:double` | true | 0..1 |
| `a303bac_id` | `xsd:double` | true | 0..1 |
| `a304bac_` | `xsd:double` | true | 0..1 |
| `a304bac_id` | `xsd:double` | true | 0..1 |
| `a305bac_` | `xsd:double` | true | 0..1 |
| `a305bac_id` | `xsd:double` | true | 0..1 |
| `a306bac_` | `xsd:double` | true | 0..1 |
| `a306bac_id` | `xsd:double` | true | 0..1 |
| `a323bac_` | `xsd:double` | true | 0..1 |
| `a323bac_id` | `xsd:double` | true | 0..1 |
| `a324bac_` | `xsd:double` | true | 0..1 |
| `a324bac_id` | `xsd:double` | true | 0..1 |
| `a325bac_` | `xsd:double` | true | 0..1 |
| `a325bac_id` | `xsd:double` | true | 0..1 |
| `a326bac_` | `xsd:double` | true | 0..1 |
| `a326bac_id` | `xsd:double` | true | 0..1 |
| `a343bac_` | `xsd:double` | true | 0..1 |
| `a343bac_id` | `xsd:double` | true | 0..1 |
| `a344bac_` | `xsd:double` | true | 0..1 |
| `a344bac_id` | `xsd:double` | true | 0..1 |
| `a345bac_` | `xsd:double` | true | 0..1 |
| `a345bac_id` | `xsd:double` | true | 0..1 |
| `a346bac_` | `xsd:double` | true | 0..1 |
| `a346bac_id` | `xsd:double` | true | 0..1 |
| `a362bac_` | `xsd:double` | true | 0..1 |
| `a362bac_id` | `xsd:double` | true | 0..1 |
| `ae01bac_` | `xsd:double` | true | 0..1 |
| `ae01bac_id` | `xsd:double` | true | 0..1 |
| `ae23bac_` | `xsd:double` | true | 0..1 |
| `ae23bac_id` | `xsd:double` | true | 0..1 |
| `ae45bac_` | `xsd:double` | true | 0..1 |
| `ae45bac_id` | `xsd:double` | true | 0..1 |
| `ae61bac_` | `xsd:double` | true | 0..1 |
| `ae61bac_id` | `xsd:double` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `path` | `xsd:string` | true | 0..1 |

### `base_tematica_tocantins:bacias_hidrograficas_2012`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `bacia` | `xsd:string` | true | 0..1 |
| `sistema` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |
| `shape_area` | `xsd:decimal` | true | 0..1 |
| `area_km` | `xsd:decimal` | true | 0..1 |

### `base_tematica_tocantins:cena_cbers`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `orbita_pon` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_tocantins:cenlandsat`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `orbita` | `xsd:string` | true | 0..1 |
| `ponto` | `xsd:string` | true | 0..1 |
| `orbpto` | `xsd:string` | true | 0..1 |
| `reg` | `xsd:double` | true | 0..1 |
| `tocantins` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_tocantins:cobertura_e_uso_1996`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `fid_` | `xsd:double` | true | 0..1 |
| `area` | `xsd:decimal` | true | 0..1 |
| `perimeter` | `xsd:decimal` | true | 0..1 |
| `a172uso_` | `xsd:double` | true | 0..1 |
| `a172uso_id` | `xsd:double` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `a173uso_` | `xsd:double` | true | 0..1 |
| `a173uso_id` | `xsd:double` | true | 0..1 |
| `a199uso_` | `xsd:double` | true | 0..1 |
| `a199uso_id` | `xsd:double` | true | 0..1 |
| `a200uso_` | `xsd:decimal` | true | 0..1 |
| `a200uso_id` | `xsd:decimal` | true | 0..1 |
| `a226uso_` | `xsd:double` | true | 0..1 |
| `a226uso_id` | `xsd:double` | true | 0..1 |
| `a227uso_` | `xsd:double` | true | 0..1 |
| `a227uso_id` | `xsd:double` | true | 0..1 |
| `a253auso_` | `xsd:double` | true | 0..1 |
| `a253auso_i` | `xsd:double` | true | 0..1 |
| `a253buso_` | `xsd:double` | true | 0..1 |
| `a253buso_i` | `xsd:double` | true | 0..1 |
| `a254auso_` | `xsd:double` | true | 0..1 |
| `a254auso_i` | `xsd:double` | true | 0..1 |
| `a254buso_` | `xsd:double` | true | 0..1 |
| `a254buso_i` | `xsd:double` | true | 0..1 |
| `a278uso_` | `xsd:double` | true | 0..1 |
| `a278uso_id` | `xsd:double` | true | 0..1 |
| `a279auso_` | `xsd:double` | true | 0..1 |
| `a279auso_i` | `xsd:double` | true | 0..1 |
| `a279buso_` | `xsd:double` | true | 0..1 |
| `a279buso_i` | `xsd:double` | true | 0..1 |
| `a280auso_` | `xsd:double` | true | 0..1 |
| `a280auso_i` | `xsd:double` | true | 0..1 |
| `a280buso_` | `xsd:double` | true | 0..1 |
| `a280buso_i` | `xsd:double` | true | 0..1 |
| `a303uso_` | `xsd:double` | true | 0..1 |
| `a303uso_id` | `xsd:double` | true | 0..1 |
| `a304auso_` | `xsd:double` | true | 0..1 |
| `a304auso_i` | `xsd:double` | true | 0..1 |
| `a304buso_` | `xsd:double` | true | 0..1 |
| `a304buso_i` | `xsd:double` | true | 0..1 |
| `a305uso_` | `xsd:decimal` | true | 0..1 |
| `a305uso_id` | `xsd:decimal` | true | 0..1 |
| `a306uso_` | `xsd:double` | true | 0..1 |
| `a306uso_id` | `xsd:double` | true | 0..1 |
| `a323uso_` | `xsd:double` | true | 0..1 |
| `a323uso_id` | `xsd:double` | true | 0..1 |
| `a324uso_` | `xsd:double` | true | 0..1 |
| `a324uso_id` | `xsd:double` | true | 0..1 |
| `a325uso_` | `xsd:double` | true | 0..1 |
| `a325uso_id` | `xsd:double` | true | 0..1 |
| `a326uso_` | `xsd:double` | true | 0..1 |
| `a326uso_id` | `xsd:double` | true | 0..1 |
| `a343uso_` | `xsd:double` | true | 0..1 |
| `a343uso_id` | `xsd:double` | true | 0..1 |
| `a344auso_` | `xsd:double` | true | 0..1 |
| `a344auso_i` | `xsd:double` | true | 0..1 |
| `a344buso_` | `xsd:double` | true | 0..1 |
| `a344buso_i` | `xsd:double` | true | 0..1 |
| `a345auso_` | `xsd:double` | true | 0..1 |
| `a345auso_i` | `xsd:double` | true | 0..1 |
| `a345buso_` | `xsd:double` | true | 0..1 |
| `a345buso_i` | `xsd:double` | true | 0..1 |
| `a346uso_` | `xsd:double` | true | 0..1 |
| `a346uso_id` | `xsd:double` | true | 0..1 |
| `a361uso_` | `xsd:double` | true | 0..1 |
| `a361uso_id` | `xsd:double` | true | 0..1 |
| `a362uso_` | `xsd:double` | true | 0..1 |
| `a362uso_id` | `xsd:double` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `path` | `xsd:string` | true | 0..1 |

### `base_tematica_tocantins:cobertura_uso_1990`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nm_tipo` | `xsd:string` | true | 0..1 |
| `cd_tipo` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `km` | `xsd:double` | true | 0..1 |

### `base_tematica_tocantins:cobertura_uso_2002`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `oid_` | `xsd:double` | true | 0..1 |
| `leg_100` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `area_m2` | `xsd:double` | true | 0..1 |
| `area_km2` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_len` | `xsd:double` | true | 0..1 |

### `base_tematica_tocantins:cobertura_uso_2004`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `fid_limite` | `xsd:double` | true | 0..1 |
| `cod_ibge` | `xsd:double` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `region` | `xsd:string` | true | 0..1 |
| `nume_cid` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `fid_marco_` | `xsd:double` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `area_m` | `xsd:double` | true | 0..1 |
| `area_km` | `xsd:double` | true | 0..1 |

### `base_tematica_tocantins:cobertura_uso_2007_1`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nm_tipo` | `xsd:string` | true | 0..1 |
| `cd_tipo` | `xsd:string` | true | 0..1 |
| `area_km2` | `xsd:double` | true | 0..1 |

### `base_tematica_tocantins:cobertura_uso_solo_2000_2`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `nm_tipo` | `xsd:string` | true | 0..1 |
| `cd_tipo` | `xsd:string` | true | 0..1 |

### `base_tematica_tocantins:cobertura_uso_solo_2003`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `leg_100` | `xsd:string` | true | 0..1 |
| `leg_250` | `xsd:string` | true | 0..1 |
| `leg_1000` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `area_m` | `xsd:double` | true | 0..1 |
| `area_km` | `xsd:double` | true | 0..1 |
| `classeb` | `xsd:string` | true | 0..1 |
| `fuso` | `xsd:string` | true | 0..1 |
| `divmcp00_` | `xsd:double` | true | 0..1 |
| `divmcp00_i` | `xsd:double` | true | 0..1 |
| `cod_ibge` | `xsd:double` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `region` | `xsd:string` | true | 0..1 |
| `num_cid` | `xsd:double` | true | 0..1 |
| `nume_cid` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `marco_1` | `xsd:string` | true | 0..1 |
| `x_coord` | `xsd:double` | true | 0..1 |
| `y_coord` | `xsd:double` | true | 0..1 |

### `base_tematica_tocantins:cobertura_usosolo_2005`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nm_tipo_20` | `xsd:string` | true | 0..1 |
| `cd_tipo_20` | `xsd:string` | true | 0..1 |

### `base_tematica_tocantins:compartimentacao_geoambiental_2012`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `regioes` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |
| `shape_area` | `xsd:decimal` | true | 0..1 |
| `class_num` | `xsd:string` | true | 0..1 |

### `base_tematica_tocantins:declividade_2012`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `classes_d` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |
| `shape_area` | `xsd:decimal` | true | 0..1 |

### `base_tematica_tocantins:erodibilidade`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `classes` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_tocantins:ferrovia_patios_2019`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `nm_nome` | `xsd:string` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |

### `base_tematica_tocantins:ferrovias_2019`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `nomen` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |

### `base_tematica_tocantins:fitoecologico_1`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `leg_simple` | `xsd:string` | true | 0..1 |
| `assoc_cont` | `xsd:string` | true | 0..1 |
| `regioes` | `xsd:string` | true | 0..1 |
| `formacoes` | `xsd:string` | true | 0..1 |
| `subtipos_f` | `xsd:string` | true | 0..1 |
| `leg_final` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_tocantins:floresta_amazonica`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `carga` | `xsd:string` | true | 0..1 |
| `contato` | `xsd:string` | true | 0..1 |
| `preterita` | `xsd:string` | true | 0..1 |
| `sec1` | `xsd:string` | true | 0..1 |
| `sec2` | `xsd:string` | true | 0..1 |
| `sec3` | `xsd:string` | true | 0..1 |
| `uantr` | `xsd:string` | true | 0..1 |
| `uveg` | `xsd:string` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `super_` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `sintese` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |

### `base_tematica_tocantins:formas_relevo`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `classes` | `xsd:string` | true | 0..1 |

### `base_tematica_tocantins:geoformologia_amz`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cd_legenda` | `xsd:string` | true | 0..1 |
| `cd_unid_ge` | `xsd:double` | true | 0..1 |
| `cd_simb_ca` | `xsd:string` | true | 0..1 |
| `cd_naturez` | `xsd:string` | true | 0..1 |
| `cd_forma_m` | `xsd:string` | true | 0..1 |
| `cd_caract_` | `xsd:string` | true | 0..1 |
| `cd_densida` | `xsd:string` | true | 0..1 |
| `cd_aprofun` | `xsd:string` | true | 0..1 |
| `cd_nivel_a` | `xsd:string` | true | 0..1 |
| `feature_id` | `xsd:double` | true | 0..1 |
| `id_regi_ge` | `xsd:double` | true | 0..1 |
| `nm_unid_ge` | `xsd:string` | true | 0..1 |
| `sg_regiao_` | `xsd:string` | true | 0..1 |
| `md_altimet` | `xsd:double` | true | 0..1 |
| `md_altim_1` | `xsd:double` | true | 0..1 |
| `cd_morfoge` | `xsd:string` | true | 0..1 |
| `ds_padrao_` | `xsd:string` | true | 0..1 |
| `ds_process` | `xsd:string` | true | 0..1 |
| `ds_caract_` | `xsd:string` | true | 0..1 |
| `ds_caract1` | `xsd:string` | true | 0..1 |
| `ds_contato` | `xsd:string` | true | 0..1 |
| `id_dom_mor` | `xsd:double` | true | 0..1 |
| `nm_regi_go` | `xsd:string` | true | 0..1 |
| `ds_caract2` | `xsd:string` | true | 0..1 |
| `nm_dom_mor` | `xsd:string` | true | 0..1 |
| `ds_caract3` | `xsd:string` | true | 0..1 |
| `cd_natur_1` | `xsd:string` | true | 0..1 |
| `cd_categ_m` | `xsd:string` | true | 0..1 |
| `cd_forma_1` | `xsd:string` | true | 0..1 |
| `cd_caract1` | `xsd:string` | true | 0..1 |
| `ds_categ_m` | `xsd:string` | true | 0..1 |
| `ds_ocor_ca` | `xsd:string` | true | 0..1 |

### `base_tematica_tocantins:geologia_afloramentos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiPointPropertyType` | true | 0..1 |
| `id_complet` | `xsd:string` | true | 0..1 |
| `cd_estado` | `xsd:string` | true | 0..1 |
| `cd_municip` | `xsd:string` | true | 0..1 |
| `feature_id` | `xsd:double` | true | 0..1 |

### `base_tematica_tocantins:geologia_ambientes_2012`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `amb_final` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |
| `shape_area` | `xsd:decimal` | true | 0..1 |

### `base_tematica_tocantins:geologia_amz`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cd_legenda` | `xsd:string` | true | 0..1 |
| `id_unid_ge` | `xsd:double` | true | 0..1 |
| `id_poli_po` | `xsd:string` | true | 0..1 |
| `cd_letra_s` | `xsd:string` | true | 0..1 |
| `nm_litolog` | `xsd:string` | true | 0..1 |
| `nm_litol_1` | `xsd:string` | true | 0..1 |
| `nm_litol_2` | `xsd:string` | true | 0..1 |
| `nm_litol_3` | `xsd:string` | true | 0..1 |
| `cd_poli_di` | `xsd:string` | true | 0..1 |
| `feature_id` | `xsd:double` | true | 0..1 |
| `cd_letra_1` | `xsd:string` | true | 0..1 |
| `nm_unid_ge` | `xsd:string` | true | 0..1 |
| `nm_unid__1` | `xsd:string` | true | 0..1 |
| `cd_tipo_un` | `xsd:string` | true | 0..1 |
| `nm_tempo_g` | `xsd:string` | true | 0..1 |
| `nm_tempo_1` | `xsd:string` | true | 0..1 |
| `cd_tipo_de` | `xsd:string` | true | 0..1 |
| `cd_tipo__1` | `xsd:string` | true | 0..1 |
| `cd_tipo__2` | `xsd:string` | true | 0..1 |
| `cd_tipo__3` | `xsd:string` | true | 0..1 |
| `cd_obtenca` | `xsd:string` | true | 0..1 |
| `cd_caract_` | `xsd:string` | true | 0..1 |
| `cd_unid_id` | `xsd:string` | true | 0..1 |
| `vl_idade_i` | `xsd:double` | true | 0..1 |
| `vl_erro_id` | `xsd:double` | true | 0..1 |
| `vl_idade_f` | `xsd:double` | true | 0..1 |
| `vl_erro__1` | `xsd:double` | true | 0..1 |
| `vl_idade_1` | `xsd:double` | true | 0..1 |
| `vl_err_ida` | `xsd:double` | true | 0..1 |
| `vl_idade_2` | `xsd:double` | true | 0..1 |
| `vl_err_i_1` | `xsd:double` | true | 0..1 |
| `vl_idade_3` | `xsd:double` | true | 0..1 |
| `vl_err_i_2` | `xsd:double` | true | 0..1 |
| `vl_idade_4` | `xsd:double` | true | 0..1 |
| `vl_err_i_3` | `xsd:double` | true | 0..1 |
| `cd_unid_ge` | `xsd:string` | true | 0..1 |
| `md_espessu` | `xsd:double` | true | 0..1 |
| `md_espes_1` | `xsd:double` | true | 0..1 |
| `cd_prov_es` | `xsd:string` | true | 0..1 |
| `cd_prov__1` | `xsd:string` | true | 0..1 |
| `cd_prov__2` | `xsd:string` | true | 0..1 |
| `cd_prov__3` | `xsd:string` | true | 0..1 |
| `id_deforma` | `xsd:string` | true | 0..1 |
| `id_defor_1` | `xsd:string` | true | 0..1 |
| `id_defor_2` | `xsd:string` | true | 0..1 |
| `id_defor_3` | `xsd:string` | true | 0..1 |
| `id_defor_4` | `xsd:string` | true | 0..1 |
| `ds_localid` | `xsd:string` | true | 0..1 |
| `ds_resumo_` | `xsd:string` | true | 0..1 |
| `ds_resumid` | `xsd:string` | true | 0..1 |

### `base_tematica_tocantins:geologia_ano_2000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `fid_` | `xsd:double` | true | 0..1 |
| `area` | `xsd:decimal` | true | 0..1 |
| `perimeter` | `xsd:decimal` | true | 0..1 |
| `a172geol_` | `xsd:double` | true | 0..1 |
| `a172geol_i` | `xsd:double` | true | 0..1 |
| `classes` | `xsd:string` | true | 0..1 |
| `a173geol_` | `xsd:double` | true | 0..1 |
| `a173geol_i` | `xsd:double` | true | 0..1 |
| `a199geol_` | `xsd:double` | true | 0..1 |
| `a199geol_i` | `xsd:double` | true | 0..1 |
| `a200geol_` | `xsd:decimal` | true | 0..1 |
| `a200geol_i` | `xsd:decimal` | true | 0..1 |
| `a226geol_` | `xsd:double` | true | 0..1 |
| `a226geol_i` | `xsd:double` | true | 0..1 |
| `a227geol_` | `xsd:double` | true | 0..1 |
| `a227geol_i` | `xsd:double` | true | 0..1 |
| `a278geol_` | `xsd:double` | true | 0..1 |
| `a278geol_i` | `xsd:double` | true | 0..1 |
| `a279geol_` | `xsd:double` | true | 0..1 |
| `a279geol_i` | `xsd:double` | true | 0..1 |
| `a303geol_` | `xsd:double` | true | 0..1 |
| `a303geol_i` | `xsd:double` | true | 0..1 |
| `a304geol_` | `xsd:double` | true | 0..1 |
| `a304geol_i` | `xsd:double` | true | 0..1 |
| `a305geol_` | `xsd:double` | true | 0..1 |
| `a305geol_i` | `xsd:double` | true | 0..1 |
| `a306geol_` | `xsd:double` | true | 0..1 |
| `a306geol_i` | `xsd:double` | true | 0..1 |
| `a323geol_` | `xsd:double` | true | 0..1 |
| `a323geol_i` | `xsd:double` | true | 0..1 |
| `a324geol_` | `xsd:double` | true | 0..1 |
| `a324geol_i` | `xsd:double` | true | 0..1 |
| `a325geol_` | `xsd:double` | true | 0..1 |
| `a325geol_i` | `xsd:double` | true | 0..1 |
| `a326geol_` | `xsd:double` | true | 0..1 |
| `a326geol_i` | `xsd:double` | true | 0..1 |
| `a343geol_` | `xsd:double` | true | 0..1 |
| `a343geol_i` | `xsd:double` | true | 0..1 |
| `a344geol_` | `xsd:double` | true | 0..1 |
| `a344geol_i` | `xsd:double` | true | 0..1 |
| `a345geol_` | `xsd:double` | true | 0..1 |
| `a345geol_i` | `xsd:double` | true | 0..1 |
| `geo_` | `xsd:double` | true | 0..1 |
| `geo_id` | `xsd:double` | true | 0..1 |
| `a362geol_` | `xsd:double` | true | 0..1 |
| `a362geol_i` | `xsd:double` | true | 0..1 |
| `ae01geol_` | `xsd:double` | true | 0..1 |
| `ae01geol_i` | `xsd:double` | true | 0..1 |
| `ae23geol_` | `xsd:double` | true | 0..1 |
| `ae23geol_i` | `xsd:double` | true | 0..1 |
| `ae45geol_` | `xsd:double` | true | 0..1 |
| `ae45geol_i` | `xsd:double` | true | 0..1 |
| `ae61geol_` | `xsd:double` | true | 0..1 |
| `ae61geol_i` | `xsd:double` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `path` | `xsd:string` | true | 0..1 |

### `base_tematica_tocantins:geologia_dobra`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `cd_represe` | `xsd:string` | true | 0..1 |
| `cd_tipo_do` | `xsd:string` | true | 0..1 |
| `cd_repre_1` | `xsd:string` | true | 0..1 |
| `cd_caract_` | `xsd:string` | true | 0..1 |
| `cd_repre_2` | `xsd:string` | true | 0..1 |
| `cd_caract1` | `xsd:string` | true | 0..1 |
| `cd_forma_o` | `xsd:string` | true | 0..1 |
| `feature_id` | `xsd:double` | true | 0..1 |

### `base_tematica_tocantins:geologia_estruturas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiPointPropertyType` | true | 0..1 |
| `cd_tipo` | `xsd:string` | true | 0..1 |
| `cd_caract_` | `xsd:string` | true | 0..1 |
| `cd_inclina` | `xsd:string` | true | 0..1 |
| `ds_valor_d` | `xsd:string` | true | 0..1 |
| `ds_valor_m` | `xsd:string` | true | 0..1 |
| `feature_id` | `xsd:double` | true | 0..1 |

### `base_tematica_tocantins:geologia_falha_sipam`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `nm_falha` | `xsd:string` | true | 0..1 |
| `cd_mergulh` | `xsd:string` | true | 0..1 |
| `cd_caiment` | `xsd:string` | true | 0..1 |
| `cd_forma_o` | `xsd:string` | true | 0..1 |
| `cd_sentido` | `xsd:string` | true | 0..1 |
| `feature_id` | `xsd:double` | true | 0..1 |

### `base_tematica_tocantins:geologia_fratura`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `nm_fratura` | `xsd:string` | true | 0..1 |
| `cd_represe` | `xsd:string` | true | 0..1 |
| `cd_mergulh` | `xsd:string` | true | 0..1 |
| `cd_forma_o` | `xsd:string` | true | 0..1 |
| `ds_rocha` | `xsd:string` | true | 0..1 |
| `id_unid_ge` | `xsd:double` | true | 0..1 |
| `feature_id` | `xsd:double` | true | 0..1 |

### `base_tematica_tocantins:geomorfologia_dominios_2012`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nm_dom_mor` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |
| `shape_area` | `xsd:decimal` | true | 0..1 |

### `base_tematica_tocantins:geomorfologia_unidades_2012`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cd_unid_ge` | `xsd:decimal` | true | 0..1 |
| `nm_unid_ge` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |
| `shape_area` | `xsd:decimal` | true | 0..1 |

### `base_tematica_tocantins:geracao_de_energia`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:decimal` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `proprietar` | `xsd:string` | true | 0..1 |
| `cnpj` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:decimal` | true | 0..1 |
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
| `lat_eixo_d` | `xsd:decimal` | true | 0..1 |
| `long_eixo1` | `xsd:decimal` | true | 0..1 |
| `pot_kw` | `xsd:decimal` | true | 0..1 |
| `n_unid_ger` | `xsd:decimal` | true | 0..1 |
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
| `regul_men` | `xsd:decimal` | true | 0..1 |
| `qd_bruta_n` | `xsd:decimal` | true | 0..1 |
| `perdas_ele` | `xsd:decimal` | true | 0..1 |
| `cons_inter` | `xsd:decimal` | true | 0..1 |
| `vazao_rem` | `xsd:decimal` | true | 0..1 |
| `vazao_uso` | `xsd:decimal` | true | 0..1 |
| `vazao_proj` | `xsd:decimal` | true | 0..1 |
| `serie_vaza` | `xsd:string` | true | 0..1 |
| `tabela_ser` | `xsd:string` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `data_atual` | `xsd:date` | true | 0..1 |
| `ren_696_15` | `xsd:string` | true | 0..1 |
| `inic_oper` | `xsd:date` | true | 0..1 |
| `pot_fisc_k` | `xsd:decimal` | true | 0..1 |
| `destino_en` | `xsd:decimal` | true | 0..1 |
| `codmun` | `xsd:decimal` | true | 0..1 |
| `tipo_comb` | `xsd:string` | true | 0..1 |
| `clas_comb` | `xsd:string` | true | 0..1 |
| `destino_1` | `xsd:string` | true | 0..1 |
| `cod_uph` | `xsd:decimal` | true | 0..1 |
| `id_empreen` | `xsd:decimal` | true | 0..1 |
| `regulariza` | `xsd:string` | true | 0..1 |
| `estagio_1` | `xsd:string` | true | 0..1 |
| `tipo_1` | `xsd:string` | true | 0..1 |
| `versao` | `xsd:decimal` | true | 0..1 |
| `arquivo` | `xsd:string` | true | 0..1 |

### `base_tematica_tocantins:hidrogeologia_2012`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:decimal` | true | 0..1 |
| `dominio` | `xsd:string` | true | 0..1 |
| `sub_domini` | `xsd:string` | true | 0..1 |
| `fav_hidrol` | `xsd:string` | true | 0..1 |
| `sigla` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |
| `shape_area` | `xsd:decimal` | true | 0..1 |

### `base_tematica_tocantins:index_100`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `index100_` | `xsd:double` | true | 0..1 |
| `index100_i` | `xsd:double` | true | 0..1 |
| `mpindice_` | `xsd:double` | true | 0..1 |
| `mpindice_i` | `xsd:double` | true | 0..1 |
| `tile_name` | `xsd:string` | true | 0..1 |
| `ibge_dsg` | `xsd:string` | true | 0..1 |
| `test` | `xsd:string` | true | 0..1 |

### `base_tematica_tocantins:index_250`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `area` | `xsd:decimal` | true | 0..1 |
| `perimeter` | `xsd:decimal` | true | 0..1 |
| `index250_` | `xsd:double` | true | 0..1 |
| `index250_i` | `xsd:double` | true | 0..1 |
| `tile_name` | `xsd:string` | true | 0..1 |
| `mir` | `xsd:double` | true | 0..1 |

### `base_tematica_tocantins:index_500`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `area` | `xsd:decimal` | true | 0..1 |
| `perimeter` | `xsd:decimal` | true | 0..1 |
| `index500_` | `xsd:double` | true | 0..1 |
| `index500_i` | `xsd:double` | true | 0..1 |
| `folhas500` | `xsd:string` | true | 0..1 |

### `base_tematica_tocantins:LimiteEstadual_AGM_TO_2022_A`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `color` | `xsd:int` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_tocantins:LimiteMunicipal_AGM_TO_2022_A`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `color` | `xsd:int` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_tocantins:LimiteMunicipal_AGM_TO_2022_L`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `tip_limite` | `xsd:long` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |

### `base_tematica_tocantins:localidade_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `ct_localid` | `xsd:string` | true | 0..1 |
| `cd_mun` | `xsd:string` | true | 0..1 |
| `nm_mun` | `xsd:string` | true | 0..1 |
| `cd_rgint` | `xsd:string` | true | 0..1 |
| `nm_rgint` | `xsd:string` | true | 0..1 |
| `cd_rgi` | `xsd:string` | true | 0..1 |
| `nm_rgi` | `xsd:string` | true | 0..1 |
| `cd_localid` | `xsd:string` | true | 0..1 |
| `nm_localid` | `xsd:string` | true | 0..1 |
| `lat_locali` | `xsd:double` | true | 0..1 |
| `long_local` | `xsd:double` | true | 0..1 |
| `wkb_geometry` | `gml:MultiPointPropertyType` | true | 0..1 |
| `modified_by` | `xsd:string` | true | 0..1 |
| `last_modification` | `xsd:date` | true | 0..1 |

### `base_tematica_tocantins:macrorregiao_regiao_2024`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `id` | `xsd:int` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `Macrorregiao` | `xsd:string` | true | 0..1 |
| `Regiao` | `xsd:string` | true | 0..1 |

### `base_tematica_tocantins:ocorrencias_minerais_2012`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `classes` | `xsd:string` | true | 0..1 |
| `subminerai` | `xsd:string` | true | 0..1 |
| `at` | `xsd:double` | true | 0..1 |
| `siglas` | `xsd:string` | true | 0..1 |
| `class_subc` | `xsd:string` | true | 0..1 |

### `base_tematica_tocantins:pedologia_2012`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `eb_nivel_1` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |
| `shape_area` | `xsd:decimal` | true | 0..1 |
| `area_km` | `xsd:decimal` | true | 0..1 |

### `base_tematica_tocantins:pedologia_sipam`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `feature_id` | `xsd:double` | true | 0..1 |
| `cd_legenda` | `xsd:string` | true | 0..1 |
| `cd_letra_s` | `xsd:string` | true | 0..1 |
| `cd_tipo_un` | `xsd:string` | true | 0..1 |
| `qt_compone` | `xsd:double` | true | 0..1 |
| `cd_classe_` | `xsd:string` | true | 0..1 |
| `or_relativ` | `xsd:double` | true | 0..1 |
| `or_grupame` | `xsd:string` | true | 0..1 |
| `cd_tipo_co` | `xsd:string` | true | 0..1 |
| `cd_classe1` | `xsd:string` | true | 0..1 |
| `qt_fertili` | `xsd:double` | true | 0..1 |
| `qt_argila` | `xsd:double` | true | 0..1 |
| `qt_hor_sup` | `xsd:double` | true | 0..1 |
| `qt_carater` | `xsd:double` | true | 0..1 |
| `qt_classe_` | `xsd:double` | true | 0..1 |
| `qt_relevo` | `xsd:double` | true | 0..1 |
| `cd_ativ_ar` | `xsd:string` | true | 0..1 |
| `cd_ativ__1` | `xsd:string` | true | 0..1 |
| `cd_ativ__2` | `xsd:string` | true | 0..1 |
| `cd_fertili` | `xsd:string` | true | 0..1 |
| `cd_ferti_1` | `xsd:string` | true | 0..1 |
| `cd_ferti_2` | `xsd:string` | true | 0..1 |
| `cd_horiz_s` | `xsd:string` | true | 0..1 |
| `cd_horiz_1` | `xsd:string` | true | 0..1 |
| `cd_horiz_2` | `xsd:string` | true | 0..1 |
| `cd_relevo_` | `xsd:string` | true | 0..1 |
| `cd_relevo1` | `xsd:string` | true | 0..1 |
| `cd_relevo2` | `xsd:string` | true | 0..1 |
| `cd_relevo3` | `xsd:string` | true | 0..1 |
| `cd_relevo4` | `xsd:string` | true | 0..1 |
| `cd_textura` | `xsd:string` | true | 0..1 |
| `cd_pre_cas` | `xsd:string` | true | 0..1 |
| `cd_pre_c_1` | `xsd:string` | true | 0..1 |
| `cd_conecto` | `xsd:string` | true | 0..1 |
| `cd_textu_1` | `xsd:string` | true | 0..1 |
| `cd_pre_c_2` | `xsd:string` | true | 0..1 |
| `cd_pre_c_3` | `xsd:string` | true | 0..1 |
| `cd_textu_2` | `xsd:string` | true | 0..1 |
| `cd_pre_c_4` | `xsd:string` | true | 0..1 |
| `cd_pre_c_5` | `xsd:string` | true | 0..1 |
| `cd_conec_1` | `xsd:string` | true | 0..1 |
| `cd_textu_3` | `xsd:string` | true | 0..1 |
| `cd_pre_c_6` | `xsd:string` | true | 0..1 |
| `cd_pre_c_7` | `xsd:string` | true | 0..1 |
| `cd_textu_4` | `xsd:string` | true | 0..1 |
| `cd_pre_c_8` | `xsd:string` | true | 0..1 |
| `cd_pre_c_9` | `xsd:string` | true | 0..1 |
| `cd_conec_2` | `xsd:string` | true | 0..1 |
| `cd_textu_5` | `xsd:string` | true | 0..1 |
| `cd_pre__10` | `xsd:string` | true | 0..1 |
| `cd_pre__11` | `xsd:string` | true | 0..1 |
| `cd_textu_6` | `xsd:string` | true | 0..1 |
| `cd_pre__12` | `xsd:string` | true | 0..1 |
| `cd_pre__13` | `xsd:string` | true | 0..1 |
| `cd_conec_3` | `xsd:string` | true | 0..1 |
| `cd_textu_7` | `xsd:string` | true | 0..1 |
| `cd_pre__14` | `xsd:string` | true | 0..1 |
| `cd_pre__15` | `xsd:string` | true | 0..1 |
| `nm_classe_` | `xsd:string` | true | 0..1 |
| `nm_carater` | `xsd:string` | true | 0..1 |
| `nm_carat_1` | `xsd:string` | true | 0..1 |
| `nm_carat_2` | `xsd:string` | true | 0..1 |
| `nm_carat_3` | `xsd:string` | true | 0..1 |
| `nm_carat_4` | `xsd:string` | true | 0..1 |

### `base_tematica_tocantins:plano_diretor_palmas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `palmas` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_tocantins:plano_uso_potencial_vegetacao`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `fid_plano_` | `xsd:decimal` | true | 0..1 |
| `fid_plano1` | `xsd:decimal` | true | 0..1 |
| `veg_uso` | `xsd:string` | true | 0..1 |
| `id` | `xsd:decimal` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |
| `shape_area` | `xsd:decimal` | true | 0..1 |
| `descricao` | `xsd:string` | true | 0..1 |

### `base_tematica_tocantins:potencialidade_uso_terra_2012`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `classes` | `xsd:string` | true | 0..1 |
| `dominios` | `xsd:string` | true | 0..1 |
| `regioes` | `xsd:string` | true | 0..1 |
| `newclass` | `xsd:string` | true | 0..1 |
| `prim_ind` | `xsd:string` | true | 0..1 |
| `segu_ind` | `xsd:string` | true | 0..1 |
| `setores` | `xsd:string` | true | 0..1 |
| `units_num` | `xsd:string` | true | 0..1 |
| `geologia` | `xsd:string` | true | 0..1 |
| `mat_origem` | `xsd:string` | true | 0..1 |
| `mecanizaca` | `xsd:string` | true | 0..1 |
| `proc_domin` | `xsd:string` | true | 0..1 |
| `efeitos_do` | `xsd:string` | true | 0..1 |
| `pedogenese` | `xsd:string` | true | 0..1 |
| `bal_m_p` | `xsd:string` | true | 0..1 |
| `horiz_tipo` | `xsd:string` | true | 0..1 |
| `horiz_def` | `xsd:string` | true | 0..1 |
| `v_` | `xsd:string` | true | 0..1 |
| `m_` | `xsd:string` | true | 0..1 |
| `c_` | `xsd:string` | true | 0..1 |
| `estrut_pri` | `xsd:string` | true | 0..1 |
| `text_geral` | `xsd:string` | true | 0..1 |
| `consist_um` | `xsd:string` | true | 0..1 |
| `silte_argi` | `xsd:string` | true | 0..1 |
| `fe203` | `xsd:string` | true | 0..1 |
| `prof_efet` | `xsd:string` | true | 0..1 |
| `erodibil` | `xsd:string` | true | 0..1 |
| `fator_limi` | `xsd:string` | true | 0..1 |
| `unidades` | `xsd:string` | true | 0..1 |
| `pot_res` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |
| `shape_area` | `xsd:decimal` | true | 0..1 |

### `base_tematica_tocantins:precipit_media_anual_zae`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `classes` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `modified_by` | `xsd:string` | true | 0..1 |
| `last_modification` | `xsd:date` | true | 0..1 |

### `base_tematica_tocantins:prectanual_1m_gcs_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `min` | `xsd:string` | true | 0..1 |
| `max` | `xsd:string` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `modified_by` | `xsd:string` | true | 0..1 |
| `last_modification` | `xsd:date` | true | 0..1 |

### `base_tematica_tocantins:prectanual_1m_gcs_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `valor` | `xsd:double` | true | 0..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `modified_by` | `xsd:string` | true | 0..1 |
| `last_modification` | `xsd:date` | true | 0..1 |

### `base_tematica_tocantins:regionalizacao_climatica_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `modified_by` | `xsd:string` | true | 0..1 |
| `last_modification` | `xsd:date` | true | 0..1 |

### `base_tematica_tocantins:rodovia_2024`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `extlay` | `xsd:double` | true | 0..1 |
| `class2024` | `xsd:string` | true | 0..1 |
| `juris2024` | `xsd:string` | true | 0..1 |
| `nome2024` | `xsd:string` | true | 0..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `modified_by` | `xsd:string` | true | 0..1 |
| `last_modification` | `xsd:date` | true | 0..1 |

### `base_tematica_tocantins:sedes`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:decimal` | true | 0..1 |
| `cidades` | `xsd:string` | true | 0..1 |
| `pop_2007` | `xsd:decimal` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `vinculo` | `xsd:string` | true | 0..1 |
| `utr` | `xsd:string` | true | 0..1 |
| `pop_2009` | `xsd:decimal` | true | 0..1 |
| `pop_2008` | `xsd:decimal` | true | 0..1 |
| `cod_ibge` | `xsd:decimal` | true | 0..1 |
| `pop_2011` | `xsd:decimal` | true | 0..1 |
| `ppa_2020_2` | `xsd:string` | true | 0..1 |
| `categoria` | `xsd:decimal` | true | 0..1 |

### `base_tematica_tocantins:sistemas_hidrograficos_2012`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `grande_bac` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |
| `shape_area` | `xsd:decimal` | true | 0..1 |

### `base_tematica_tocantins:solos_2000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `fid_` | `xsd:double` | true | 0..1 |
| `area` | `xsd:decimal` | true | 0..1 |
| `perimeter` | `xsd:decimal` | true | 0..1 |
| `a172ped_` | `xsd:double` | true | 0..1 |
| `a172ped_id` | `xsd:double` | true | 0..1 |
| `classes` | `xsd:string` | true | 0..1 |
| `a173ped_` | `xsd:double` | true | 0..1 |
| `a173ped_id` | `xsd:double` | true | 0..1 |
| `a199ped_` | `xsd:double` | true | 0..1 |
| `a199ped_id` | `xsd:double` | true | 0..1 |
| `a200ped_` | `xsd:decimal` | true | 0..1 |
| `a200ped_id` | `xsd:decimal` | true | 0..1 |
| `fid_1` | `xsd:double` | true | 0..1 |
| `a226ped_` | `xsd:double` | true | 0..1 |
| `a226ped_id` | `xsd:double` | true | 0..1 |
| `a227ped_` | `xsd:double` | true | 0..1 |
| `a227ped_id` | `xsd:double` | true | 0..1 |
| `a278ped_` | `xsd:double` | true | 0..1 |
| `a278ped_id` | `xsd:double` | true | 0..1 |
| `a279ped_` | `xsd:double` | true | 0..1 |
| `a279ped_id` | `xsd:double` | true | 0..1 |
| `a303ped_` | `xsd:double` | true | 0..1 |
| `a303ped_id` | `xsd:double` | true | 0..1 |
| `a304ped_` | `xsd:double` | true | 0..1 |
| `a304ped_id` | `xsd:double` | true | 0..1 |
| `a305ped_` | `xsd:double` | true | 0..1 |
| `a305ped_id` | `xsd:double` | true | 0..1 |
| `a306ped_` | `xsd:double` | true | 0..1 |
| `a306ped_id` | `xsd:double` | true | 0..1 |
| `a323ped_` | `xsd:double` | true | 0..1 |
| `a323ped_id` | `xsd:double` | true | 0..1 |
| `a324ped_` | `xsd:double` | true | 0..1 |
| `a324ped_id` | `xsd:double` | true | 0..1 |
| `a325ped_` | `xsd:double` | true | 0..1 |
| `a325ped_id` | `xsd:double` | true | 0..1 |
| `a326ped_` | `xsd:double` | true | 0..1 |
| `a326ped_id` | `xsd:double` | true | 0..1 |
| `a343ped_` | `xsd:double` | true | 0..1 |
| `a343ped_id` | `xsd:double` | true | 0..1 |
| `a344ped_` | `xsd:double` | true | 0..1 |
| `a344ped_id` | `xsd:double` | true | 0..1 |
| `a345ped_` | `xsd:double` | true | 0..1 |
| `a345ped_id` | `xsd:double` | true | 0..1 |
| `a346ped_` | `xsd:double` | true | 0..1 |
| `a346ped_id` | `xsd:double` | true | 0..1 |
| `a362ped_` | `xsd:double` | true | 0..1 |
| `a362ped_id` | `xsd:double` | true | 0..1 |
| `ae01ped_` | `xsd:double` | true | 0..1 |
| `ae01ped_id` | `xsd:double` | true | 0..1 |
| `ae23ped_` | `xsd:double` | true | 0..1 |
| `ae23ped_id` | `xsd:double` | true | 0..1 |
| `ae45ped_` | `xsd:double` | true | 0..1 |
| `ae45ped_id` | `xsd:double` | true | 0..1 |
| `ae61ped_` | `xsd:double` | true | 0..1 |
| `ae61ped_id` | `xsd:double` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `path` | `xsd:string` | true | 0..1 |

### `base_tematica_tocantins:subbacias_hidrograficas_2012`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `grande_bac` | `xsd:string` | true | 0..1 |
| `bacia` | `xsd:string` | true | 0..1 |
| `sub_bacia` | `xsd:string` | true | 0..1 |
| `distance` | `xsd:decimal` | true | 0..1 |
| `sistema` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |
| `shape_area` | `xsd:decimal` | true | 0..1 |

### `base_tematica_tocantins:temperatura_media_2000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `classes` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `base_tematica_tocantins:temperatura_media_anual_zae`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `classes` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `modified_by` | `xsd:string` | true | 0..1 |
| `last_modification` | `xsd:date` | true | 0..1 |

### `base_tematica_tocantins:terras_indigenas_2019`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:decimal` | true | 0..1 |
| `gid` | `xsd:string` | true | 0..1 |
| `codarea` | `xsd:string` | true | 0..1 |
| `sigla` | `xsd:string` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `rev` | `xsd:string` | true | 0..1 |
| `em_revisa` | `xsd:string` | true | 0..1 |
| `codareare` | `xsd:string` | true | 0..1 |
| `adr_antig` | `xsd:string` | true | 0..1 |
| `populacao` | `xsd:string` | true | 0..1 |
| `grupos` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `etapa` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `titulo` | `xsd:string` | true | 0..1 |
| `documento` | `xsd:string` | true | 0..1 |
| `perimetro` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:string` | true | 0..1 |
| `datadoc` | `xsd:string` | true | 0..1 |
| `extenso` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `cdoc` | `xsd:string` | true | 0..1 |
| `codti` | `xsd:string` | true | 0..1 |
| `nome_area` | `xsd:string` | true | 0..1 |
| `nome_ti` | `xsd:string` | true | 0..1 |
| `coor_reg` | `xsd:string` | true | 0..1 |
| `area_ha_of` | `xsd:decimal` | true | 0..1 |
| `sobreposic` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |
| `shape_area` | `xsd:decimal` | true | 0..1 |

### `base_tematica_tocantins:tmedmanual_1m_gcs_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `valor` | `xsd:long` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `modified_by` | `xsd:string` | true | 0..1 |
| `last_modification` | `xsd:date` | true | 0..1 |

### `base_tematica_tocantins:uhe_lajeado_nivel_maximo_sirgas2000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `fid_` | `xsd:long` | true | 0..1 |
| `entity` | `xsd:string` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `modified_by` | `xsd:string` | true | 0..1 |
| `last_modification` | `xsd:date` | true | 0..1 |

### `base_tematica_tocantins:veg_sec_amz`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `carga` | `xsd:string` | true | 0..1 |
| `contato` | `xsd:string` | true | 0..1 |
| `preterita` | `xsd:string` | true | 0..1 |
| `sec1` | `xsd:string` | true | 0..1 |
| `sec2` | `xsd:string` | true | 0..1 |
| `sec3` | `xsd:string` | true | 0..1 |
| `uantr` | `xsd:string` | true | 0..1 |
| `uveg` | `xsd:string` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `super_` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `sintese` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |

### `base_tematica_tocantins:vegetacao_amz_`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `carga` | `xsd:string` | true | 0..1 |
| `contato` | `xsd:string` | true | 0..1 |
| `preterita` | `xsd:string` | true | 0..1 |
| `sec1` | `xsd:string` | true | 0..1 |
| `sec2` | `xsd:string` | true | 0..1 |
| `sec3` | `xsd:string` | true | 0..1 |
| `uantr` | `xsd:string` | true | 0..1 |
| `uveg` | `xsd:string` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `super_` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `sintese` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |

### `base_tematica_tocantins:vegetacao_potencial`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `fid_` | `xsd:double` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `a172veg_` | `xsd:double` | true | 0..1 |
| `a172veg_id` | `xsd:double` | true | 0..1 |
| `classes` | `xsd:string` | true | 0..1 |
| `a173veg_` | `xsd:double` | true | 0..1 |
| `a173veg_id` | `xsd:double` | true | 0..1 |
| `a199veg_` | `xsd:double` | true | 0..1 |
| `a199veg_id` | `xsd:double` | true | 0..1 |
| `a200veg_` | `xsd:double` | true | 0..1 |
| `a200veg_id` | `xsd:double` | true | 0..1 |
| `a226veg_` | `xsd:double` | true | 0..1 |
| `a226veg_id` | `xsd:double` | true | 0..1 |
| `a227veg_` | `xsd:double` | true | 0..1 |
| `a227veg_id` | `xsd:double` | true | 0..1 |
| `a278veg_` | `xsd:double` | true | 0..1 |
| `a278veg_id` | `xsd:double` | true | 0..1 |
| `a279veg_` | `xsd:double` | true | 0..1 |
| `a279veg_id` | `xsd:double` | true | 0..1 |
| `a303veg_` | `xsd:double` | true | 0..1 |
| `a303veg_id` | `xsd:double` | true | 0..1 |
| `a304veg_` | `xsd:double` | true | 0..1 |
| `a304veg_id` | `xsd:double` | true | 0..1 |
| `a305veg_` | `xsd:double` | true | 0..1 |
| `a305veg_id` | `xsd:double` | true | 0..1 |
| `a306veg_` | `xsd:double` | true | 0..1 |
| `a306veg_id` | `xsd:double` | true | 0..1 |
| `a323veg_` | `xsd:double` | true | 0..1 |
| `a323veg_id` | `xsd:double` | true | 0..1 |
| `a324veg_` | `xsd:double` | true | 0..1 |
| `a324veg_id` | `xsd:double` | true | 0..1 |
| `a325veg_` | `xsd:double` | true | 0..1 |
| `a325veg_id` | `xsd:double` | true | 0..1 |
| `a326veg_` | `xsd:double` | true | 0..1 |
| `a326veg_id` | `xsd:double` | true | 0..1 |
| `a343veg_` | `xsd:double` | true | 0..1 |
| `a343veg_id` | `xsd:double` | true | 0..1 |
| `a344veg_` | `xsd:double` | true | 0..1 |
| `a344veg_id` | `xsd:double` | true | 0..1 |
| `a345veg_` | `xsd:double` | true | 0..1 |
| `a345veg_id` | `xsd:double` | true | 0..1 |
| `a346veg_` | `xsd:double` | true | 0..1 |
| `a346veg_id` | `xsd:double` | true | 0..1 |
| `a362veg_` | `xsd:double` | true | 0..1 |
| `a362veg_id` | `xsd:double` | true | 0..1 |
| `ae01veg_` | `xsd:double` | true | 0..1 |
| `ae01veg_id` | `xsd:double` | true | 0..1 |
| `ae23veg_` | `xsd:double` | true | 0..1 |
| `ae23veg_id` | `xsd:double` | true | 0..1 |
| `ae45veg_` | `xsd:double` | true | 0..1 |
| `ae45veg_id` | `xsd:double` | true | 0..1 |
| `ae61veg_` | `xsd:double` | true | 0..1 |
| `ae61veg_id` | `xsd:double` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `path` | `xsd:string` | true | 0..1 |

### `base_tematica_tocantins:zoneamento_agroecologico_zae`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `fid_` | `xsd:int` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `alv_zae_` | `xsd:int` | true | 0..1 |
| `alv_zae_id` | `xsd:int` | true | 0..1 |
| `classes` | `xsd:string` | true | 0..1 |
| `imp_zae_` | `xsd:double` | true | 0..1 |
| `imp_zae_id` | `xsd:double` | true | 0..1 |
| `jal_zae_` | `xsd:double` | true | 0..1 |
| `jal_zae_id` | `xsd:double` | true | 0..1 |
| `liz_zae_` | `xsd:double` | true | 0..1 |
| `liz_zae_id` | `xsd:double` | true | 0..1 |
| `mar_zae_` | `xsd:double` | true | 0..1 |
| `mar_zae_id` | `xsd:double` | true | 0..1 |
| `mir_zae_` | `xsd:double` | true | 0..1 |
| `mir_zae_id` | `xsd:double` | true | 0..1 |
| `pal_zae_` | `xsd:double` | true | 0..1 |
| `pal_zae_id` | `xsd:double` | true | 0..1 |
| `par_sed_` | `xsd:double` | true | 0..1 |
| `par_sed_id` | `xsd:double` | true | 0..1 |
| `sed_` | `xsd:int` | true | 0..1 |
| `sed_id` | `xsd:int` | true | 0..1 |
| `xam_zae_` | `xsd:double` | true | 0..1 |
| `xam_zae_id` | `xsd:double` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `path` | `xsd:string` | true | 0..1 |

## cartas_climaticas (890)

### `cartas_climaticas:DChv1990_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv1990_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv1991_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv1991_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv1992_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv1992_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv1993_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv1993_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv1994_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv1994_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv1995_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv1995_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv1996_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv1996_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv1997_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv1997_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv1998_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv1998_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv1999_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv1999_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2000_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2000_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2001_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2001_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2002_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2002_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2003_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2003_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2004_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2004_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2005_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2005_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2006_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2006_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2007_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2007_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2008_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2008_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2009_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2009_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2010_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2010_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2011_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2011_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2012_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2012_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2013_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2013_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2014_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2014_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2015_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2015_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2016_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2016_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2017_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2017_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2018_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2018_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2019_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChv2019_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChvM01_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChvM01_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChvM02_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChvM02_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChvM03_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChvM03_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChvM04_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChvM04_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChvM05_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChvM05_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChvM06_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChvM06_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChvM07_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChvM07_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChvM08_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChvM08_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChvM09_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChvM09_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChvM10_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChvM10_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChvM11_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChvM11_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChvM12_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChvM12_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChvTAnual_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DChvTAnual_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DHidAnual_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID_1` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DHidM01_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DHidM02_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DHidM03_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DHidM04_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DHidM05_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DHidM06_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DHidM07_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DHidM08_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DHidM09_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DHidM10_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DHidM11_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:DHidM12_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EHidAnual_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID_1` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EHidM01_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID_1` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EHidM02_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID_1` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EHidM03_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID_1` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EHidM04_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID_1` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EHidM05_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID_1` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EHidM06_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID_1` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EHidM07_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID_1` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EHidM08_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID_1` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EHidM09_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID_1` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EHidM10_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID_1` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EHidM11_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID_1` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EHidM12_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID_1` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRMM01_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRMM01_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRMM02_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRMM02_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRMM03_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRMM03_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRMM04_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRMM04_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRMM05_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRMM05_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRMM06_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRMM06_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRMM07_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRMM07_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRMM08_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRMM08_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRMM09_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRMM09_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRMM10_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRMM10_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRMM11_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRMM11_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRMM12_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRMM12_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRT2007_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRT2007_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRT2008_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRT2008_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRT2009_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRT2009_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRT2010_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRT2010_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRT2011_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRT2011_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRT2012_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRT2013_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRT2013_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRT2014_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRT2014_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRT2015_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRT2015_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRT2016_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRT2016_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRT2017_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRT2017_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRT2018_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRT2018_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRT2019_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRT2019_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRTAnual_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EtoRTAnual_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapMM01_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapMM01_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapMM02_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapMM02_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapMM03_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapMM03_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapMM04_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapMM04_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapMM05_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapMM05_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapMM06_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapMM06_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapMM07_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapMM07_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapMM08_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapMM08_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapMM09_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapMM09_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapMM10_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapMM10_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapMM11_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapMM11_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapMM12_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapMM12_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT1990_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT1990_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT1991_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT1991_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT1992_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT1992_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT1993_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT1993_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT1994_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT1994_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT1995_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT1995_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT1996_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT1996_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT1997_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT1997_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT1998_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT1998_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT1999_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT1999_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2000_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2000_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2001_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2001_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2002_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2002_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2003_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2003_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2004_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2004_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2005_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2005_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2006_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2006_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2007_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2007_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2008_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2008_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2009_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2009_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2010_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2010_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2011_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2011_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2012_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2012_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2013_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2013_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2014_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2014_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2015_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2015_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2016_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2016_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2017_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapT2017_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapTAnual_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:EvapTAnual_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:IHid_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslMM01_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslMM01_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslMM02_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslMM02_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslMM03_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslMM03_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslMM04_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslMM04_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslMM05_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslMM05_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslMM06_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslMM06_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslMM07_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslMM07_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslMM08_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslMM08_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslMM09_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslMM09_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslMM10_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslMM10_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslMM11_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslMM11_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslMM12_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslMM12_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT1990_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT1990_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT1991_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT1991_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT1992_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT1992_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT1993_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT1993_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT1994_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT1994_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT1995_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT1995_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT1996_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT1996_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT1997_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT1997_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT1998_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT1998_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT1999_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT1999_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2000_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2000_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2001_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2001_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2002_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2002_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2003_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2003_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2004_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2004_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2005_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2005_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2006_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2006_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2007_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2007_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2008_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2008_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2009_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2009_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2010_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2010_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2011_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2011_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2012_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2012_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2013_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2013_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2014_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2014_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2015_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2015_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2016_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2016_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2017_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2017_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2018_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2018_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2019_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslT2019_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslTAnual_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:InslTAnual_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:ISec_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl1990_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl1990_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl1991_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl1991_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl1992_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl1992_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl1993_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl1993_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl1994_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl1994_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl1995_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl1995_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl1996_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl1996_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl1997_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl1997_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl1998_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl1998_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl1999_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl1999_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2000_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2000_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2001_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2001_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2002_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2002_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2003_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2003_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2004_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2004_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2005_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2005_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2006_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2006_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2007_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2007_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2008_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2008_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2009_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2009_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2010_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2010_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2011_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2011_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2012_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2012_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2013_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2013_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2014_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2014_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2015_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2015_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2016_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2016_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2017_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2017_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2018_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2018_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2019_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Nebl2019_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:NeblM01_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:NeblM01_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:NeblM02_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:NeblM02_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:NeblM03_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:NeblM03_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:NeblM04_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:NeblM04_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:NeblM05_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:NeblM05_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:NeblM06_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:NeblM06_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:NeblM07_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:NeblM07_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:NeblM08_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:NeblM08_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:NeblM09_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:NeblM09_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:NeblM10_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:NeblM10_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:NeblM11_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:NeblM11_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:NeblM12_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:NeblM12_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:NeblMAnual_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:NeblMAnual_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn1990a1991_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn1990a1991_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn1991a1992_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn1991a1992_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn1992a1993_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn1992a1993_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn1993a1994_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn1993a1994_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn1994a1995_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn1994a1995_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn1995a1996_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn1995a1996_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn1996a1997_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn1996a1997_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn1997a1998_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn1997a1998_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn1998a1999_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn1998a1999_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn1999a2000_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn1999a2000_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2000a2001_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2000a2001_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2001a2002_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2001a2002_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2002a2003_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2002a2003_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2003a2004_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2003a2004_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2004a2005_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2004a2005_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2005a2006_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2005a2006_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2006a2007_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2006a2007_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2007a2008_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2007a2008_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2008a2009_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2008a2009_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2009a2010_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2009a2010_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2010a2011_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2010a2011_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2011a2012_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2011a2012_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2012a2013_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2012a2013_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2013a2014_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2013a2014_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2014a2015_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2014a2015_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2015a2016_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2015a2016_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2016a2017_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2016a2017_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2017a2018_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2017a2018_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2018a2019_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrn2018a2019_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrnMAnual_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `ContourMin` | `xsd:double` | true | 0..1 |
| `ContourMax` | `xsd:double` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:OVrnMAnual_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv1990a1991_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv1990a1991_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv1991a1992_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv1991a1992_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv1992a1993_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv1992a1993_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv1993a1994_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv1993a1994_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv1994a1995_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv1994a1995_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv1995a1996_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv1995a1996_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv1996a1997_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv1996a1997_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv1997a1998_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv1997a1998_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv1998a1999_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv1998a1999_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv1999a2000_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv1999a2000_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2000a2001_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2000a2001_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2001a2002_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2001a2002_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2002a2003_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2002a2003_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2003a2004_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2003a2004_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2004a2005_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2004a2005_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2005a2006_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2005a2006_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2006a2007_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2006a2007_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2007a2008_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2007a2008_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2008a2009_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2008a2009_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2009a2010_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2009a2010_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2010a2011_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2010a2011_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2011a2012_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2011a2012_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2012a2013_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2012a2013_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2013a2014_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2013a2014_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2014a2015_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2014a2015_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2015a2016_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2015a2016_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2016a2017_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2016a2017_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2017a2018_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2017a2018_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2018a2019_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChv2018a2019_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChvMAnual_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PChvMAnual_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecMM01_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecMM01_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecMM02_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecMM02_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecMM03_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecMM03_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecMM04_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecMM04_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecMM05_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecMM05_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecMM06_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecMM06_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecMM07_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecMM07_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecMM08_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecMM08_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecMM09_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecMM09_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecMM10_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecMM10_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecMM11_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecMM11_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecMM12_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecMM12_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT1990_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT1990_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT1991_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT1991_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT1992_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT1992_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT1993_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT1993_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT1994_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT1994_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT1995_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT1995_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT1996_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT1996_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT1997_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT1997_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT1998_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT1998_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT1999_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT1999_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2000_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2000_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2001_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2001_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2002_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2002_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2003_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2003_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2004_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2004_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2005_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2005_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2006_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2006_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2007_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2007_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2008_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2008_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2009_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2009_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2010_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2010_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2011_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2011_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2012_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2012_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2013_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2014_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2014_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2015_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2015_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2016_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2016_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2017_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2017_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2018_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2018_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2019_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecT2019_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecTAnual_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:PrecTAnual_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RClm_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RClmK_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `KOPPEN` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RClmS_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSG2007_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSG2007_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSG2008_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSG2008_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSG2009_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSG2009_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSG2010_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSG2010_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSG2011_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSG2011_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSG2012_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSG2012_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSG2013_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSG2013_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSG2014_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSG2014_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSG2015_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSG2015_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSG2016_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSG2016_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSG2017_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSG2017_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSG2018_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSG2018_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSGM01_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSGM01_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSGM02_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSGM02_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSGM03_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSGM03_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSGM04_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSGM04_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSGM05_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSGM05_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSGM06_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSGM06_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSGM07_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSGM07_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSGM08_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSGM08_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSGM09_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSGM09_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSGM10_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSGM10_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSGM11_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSGM11_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSGM12_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSGM12_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSGMAnual_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:RdSGMAnual_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax1990_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax1991_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax1992_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax1993_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax1994_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax1995_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax1996_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax1997_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax1998_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax1999_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax2000_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax2001_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax2002_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax2003_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax2004_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax2005_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax2006_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax2007_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax2008_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax2009_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax2010_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax2011_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax2012_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax2013_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax2014_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax2015_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax2016_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax2017_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax2018_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMax2019_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMaxM01_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMaxM02_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMaxM03_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMaxM04_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMaxM05_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMaxM06_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMaxM07_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMaxM08_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMaxM09_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMaxM10_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMaxM11_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMaxM12_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMaxMAnual_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed1990_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed1991_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed1992_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed1993_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed1994_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed1995_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed1996_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed1997_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed1998_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed1999_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed2000_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed2001_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed2002_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed2003_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed2004_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed2005_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed2006_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed2007_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed2008_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed2009_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed2010_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed2011_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed2012_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed2013_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed2014_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed2015_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed2016_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed2017_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed2018_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMed2019_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMedM01_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMedM02_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMedM03_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMedM04_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMedM05_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMedM06_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMedM07_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMedM08_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMedM09_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMedM10_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMedM11_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMedM12_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMedMAnual_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin1990_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin1991_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin1992_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin1993_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin1994_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin1995_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin1996_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin1997_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin1998_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin1999_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin2000_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin2001_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin2003_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin2004_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin2005_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin2006_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin2007_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin2008_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin2009_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin2010_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin2011_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin2012_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin2013_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin2014_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin2015_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin2016_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin2017_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin2018_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMin2019_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMinM01_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMinM02_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMinM03_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMinM04_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMinM05_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMinM06_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMinM07_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMinM08_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMinM09_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMinM10_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMinM11_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMinM12_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:TMinMAnual_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:int` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid1990_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid1990_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid1991_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid1991_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid1992_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid1992_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid1993_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid1993_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid1994_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid1994_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid1995_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid1995_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid1996_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid1996_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid1997_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid1997_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid1998_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid1998_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid1999_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2000_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2000_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2001_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2001_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2002_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2002_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2003_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2003_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2004_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2004_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2005_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2005_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2006_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2006_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2007_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2007_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2008_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2008_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2009_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2009_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2010_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2010_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2011_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2011_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2012_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2012_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2013_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2013_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2014_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2014_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2015_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2015_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2016_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2016_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2017_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2017_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2018_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2018_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2019_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:Umid2019_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:UmidM01_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:UmidM01_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:UmidM02_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:UmidM02_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:UmidM03_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:UmidM03_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:UmidM04_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:UmidM04_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:UmidM05_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:UmidM05_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:UmidM06_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:UmidM06_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:UmidM07_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:UmidM07_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:UmidM08_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:UmidM08_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:UmidM09_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:UmidM09_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:UmidM10_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:UmidM10_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:UmidM11_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:UmidM11_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:UmidM12_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:UmidM12_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:UmidMAnual_1M_GCS_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Min` | `xsd:string` | true | 0..1 |
| `Max` | `xsd:string` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cartas_climaticas:UmidMAnual_1M_GCS_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Valor` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |

## estatistica (71)

### `estatistica:acidentes_com_animais_peconhentos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `serp_2007` | `xsd:long` | true | 0..1 |
| `aran_2007` | `xsd:long` | true | 0..1 |
| `escor_2007` | `xsd:long` | true | 0..1 |
| `lagar_2007` | `xsd:long` | true | 0..1 |
| `abel_2007` | `xsd:long` | true | 0..1 |
| `otros_2007` | `xsd:long` | true | 0..1 |
| `serp_2008` | `xsd:long` | true | 0..1 |
| `aran_2008` | `xsd:long` | true | 0..1 |
| `escor_2008` | `xsd:long` | true | 0..1 |
| `lagar_2008` | `xsd:long` | true | 0..1 |
| `abel_2008` | `xsd:long` | true | 0..1 |
| `otros_2008` | `xsd:long` | true | 0..1 |
| `serp_2009` | `xsd:long` | true | 0..1 |
| `aran_2009` | `xsd:long` | true | 0..1 |
| `escor_2009` | `xsd:long` | true | 0..1 |
| `lagar_2009` | `xsd:long` | true | 0..1 |
| `abel_2009` | `xsd:long` | true | 0..1 |
| `otros_2009` | `xsd:long` | true | 0..1 |
| `serp_2010` | `xsd:long` | true | 0..1 |
| `aran_2010` | `xsd:long` | true | 0..1 |
| `escor_2010` | `xsd:long` | true | 0..1 |
| `lagar_2010` | `xsd:long` | true | 0..1 |
| `abel_2010` | `xsd:long` | true | 0..1 |
| `otros_2010` | `xsd:long` | true | 0..1 |
| `serp_2011` | `xsd:long` | true | 0..1 |
| `aran_2011` | `xsd:long` | true | 0..1 |
| `escor_2011` | `xsd:long` | true | 0..1 |
| `lagar_2011` | `xsd:long` | true | 0..1 |
| `abel_2011` | `xsd:long` | true | 0..1 |
| `otros_2011` | `xsd:long` | true | 0..1 |
| `serp_2012` | `xsd:long` | true | 0..1 |
| `aran_2012` | `xsd:long` | true | 0..1 |
| `escor_2012` | `xsd:long` | true | 0..1 |
| `lagar_2012` | `xsd:long` | true | 0..1 |
| `abel_2012` | `xsd:long` | true | 0..1 |
| `otros_2012` | `xsd:long` | true | 0..1 |
| `serp_2013` | `xsd:long` | true | 0..1 |
| `aran_2013` | `xsd:long` | true | 0..1 |
| `escor_2013` | `xsd:long` | true | 0..1 |
| `lagar_2013` | `xsd:long` | true | 0..1 |
| `abel_2013` | `xsd:long` | true | 0..1 |
| `otros_2013` | `xsd:long` | true | 0..1 |
| `serp_2014` | `xsd:long` | true | 0..1 |
| `aran_2014` | `xsd:long` | true | 0..1 |
| `escor_2014` | `xsd:long` | true | 0..1 |
| `lagar_2014` | `xsd:long` | true | 0..1 |
| `abel_2014` | `xsd:long` | true | 0..1 |
| `otros_2014` | `xsd:long` | true | 0..1 |
| `serp_2015` | `xsd:long` | true | 0..1 |
| `aran_2015` | `xsd:long` | true | 0..1 |
| `escor_2015` | `xsd:long` | true | 0..1 |
| `lagar_2015` | `xsd:long` | true | 0..1 |
| `abel_2015` | `xsd:long` | true | 0..1 |
| `otros_2015` | `xsd:long` | true | 0..1 |
| `serp_2016` | `xsd:long` | true | 0..1 |
| `aran_2016` | `xsd:long` | true | 0..1 |
| `escor_2016` | `xsd:long` | true | 0..1 |
| `lagar_2016` | `xsd:long` | true | 0..1 |
| `abel_2016` | `xsd:long` | true | 0..1 |
| `otros_2016` | `xsd:long` | true | 0..1 |
| `serp_2017` | `xsd:long` | true | 0..1 |
| `aran_2017` | `xsd:long` | true | 0..1 |
| `escor_2017` | `xsd:long` | true | 0..1 |
| `lagar_2017` | `xsd:long` | true | 0..1 |
| `abel_2017` | `xsd:long` | true | 0..1 |
| `otros_2017` | `xsd:long` | true | 0..1 |
| `serp_2018` | `xsd:long` | true | 0..1 |
| `aran_2018` | `xsd:long` | true | 0..1 |
| `escor_2018` | `xsd:long` | true | 0..1 |
| `lagar_2018` | `xsd:long` | true | 0..1 |
| `abel_2018` | `xsd:long` | true | 0..1 |
| `otros_2018` | `xsd:long` | true | 0..1 |
| `serp_2019` | `xsd:long` | true | 0..1 |
| `aran_2019` | `xsd:long` | true | 0..1 |
| `escor_2019` | `xsd:long` | true | 0..1 |
| `lagar_2019` | `xsd:long` | true | 0..1 |
| `abel_2019` | `xsd:long` | true | 0..1 |
| `otros_2019` | `xsd:long` | true | 0..1 |

### `estatistica:alho`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `area_1989` | `xsd:double` | true | 0..1 |
| `area_1990` | `xsd:double` | true | 0..1 |
| `area_1991` | `xsd:double` | true | 0..1 |
| `area_1992` | `xsd:double` | true | 0..1 |
| `area_1993` | `xsd:double` | true | 0..1 |
| `area_1994` | `xsd:double` | true | 0..1 |
| `area_1995` | `xsd:double` | true | 0..1 |
| `area_1996` | `xsd:double` | true | 0..1 |
| `area_1997` | `xsd:double` | true | 0..1 |
| `area_1998` | `xsd:double` | true | 0..1 |
| `area_1999` | `xsd:double` | true | 0..1 |
| `area_2000` | `xsd:double` | true | 0..1 |
| `area_2001` | `xsd:double` | true | 0..1 |
| `area_2002` | `xsd:double` | true | 0..1 |
| `area_2003` | `xsd:double` | true | 0..1 |
| `area_2004` | `xsd:double` | true | 0..1 |
| `area_2005` | `xsd:double` | true | 0..1 |
| `area_2006` | `xsd:double` | true | 0..1 |
| `area_2007` | `xsd:double` | true | 0..1 |
| `area_2008` | `xsd:double` | true | 0..1 |
| `area_2009` | `xsd:double` | true | 0..1 |
| `area_2010` | `xsd:double` | true | 0..1 |
| `area_2011` | `xsd:double` | true | 0..1 |
| `area_2012` | `xsd:double` | true | 0..1 |
| `area_2013` | `xsd:double` | true | 0..1 |
| `area_2014` | `xsd:double` | true | 0..1 |
| `area_2015` | `xsd:double` | true | 0..1 |
| `area_2016` | `xsd:double` | true | 0..1 |
| `area_2017` | `xsd:double` | true | 0..1 |
| `area_2018` | `xsd:double` | true | 0..1 |
| `colhi_1989` | `xsd:double` | true | 0..1 |
| `colhi_1990` | `xsd:double` | true | 0..1 |
| `colhi_1991` | `xsd:double` | true | 0..1 |
| `colhi_1992` | `xsd:double` | true | 0..1 |
| `colhi_1993` | `xsd:double` | true | 0..1 |
| `colhi_1994` | `xsd:double` | true | 0..1 |
| `colhi_1995` | `xsd:double` | true | 0..1 |
| `colhi_1996` | `xsd:double` | true | 0..1 |
| `colhi_1997` | `xsd:double` | true | 0..1 |
| `colhi_1998` | `xsd:double` | true | 0..1 |
| `colhi_1999` | `xsd:double` | true | 0..1 |
| `colhi_2000` | `xsd:double` | true | 0..1 |
| `colhi_2001` | `xsd:double` | true | 0..1 |
| `colhi_2002` | `xsd:double` | true | 0..1 |
| `colhi_2003` | `xsd:double` | true | 0..1 |
| `colhi_2004` | `xsd:double` | true | 0..1 |
| `colhi_2005` | `xsd:double` | true | 0..1 |
| `colhi_2006` | `xsd:double` | true | 0..1 |
| `colhi_2007` | `xsd:double` | true | 0..1 |
| `colhi_2008` | `xsd:double` | true | 0..1 |
| `colhi_2009` | `xsd:double` | true | 0..1 |
| `colhi_2010` | `xsd:double` | true | 0..1 |
| `colhi_2011` | `xsd:double` | true | 0..1 |
| `colhi_2012` | `xsd:double` | true | 0..1 |
| `colhi_2013` | `xsd:double` | true | 0..1 |
| `colhi_2014` | `xsd:double` | true | 0..1 |
| `colhi_2015` | `xsd:double` | true | 0..1 |
| `colhi_2016` | `xsd:double` | true | 0..1 |
| `colhi_2017` | `xsd:double` | true | 0..1 |
| `colhi_2018` | `xsd:double` | true | 0..1 |
| `produ_1989` | `xsd:double` | true | 0..1 |
| `produ_1990` | `xsd:double` | true | 0..1 |
| `produ_1991` | `xsd:double` | true | 0..1 |
| `produ_1992` | `xsd:double` | true | 0..1 |
| `produ_1993` | `xsd:double` | true | 0..1 |
| `produ_1994` | `xsd:double` | true | 0..1 |
| `produ_1995` | `xsd:double` | true | 0..1 |
| `produ_1996` | `xsd:double` | true | 0..1 |
| `produ_1997` | `xsd:double` | true | 0..1 |
| `produ_1998` | `xsd:double` | true | 0..1 |
| `produ_1999` | `xsd:double` | true | 0..1 |
| `produ_2000` | `xsd:double` | true | 0..1 |
| `produ_2001` | `xsd:double` | true | 0..1 |
| `produ_2002` | `xsd:double` | true | 0..1 |
| `produ_2003` | `xsd:double` | true | 0..1 |
| `produ_2004` | `xsd:double` | true | 0..1 |
| `produ_2005` | `xsd:double` | true | 0..1 |
| `produ_2006` | `xsd:double` | true | 0..1 |
| `produ_2007` | `xsd:double` | true | 0..1 |
| `produ_2008` | `xsd:double` | true | 0..1 |
| `produ_2009` | `xsd:double` | true | 0..1 |
| `produ_2010` | `xsd:double` | true | 0..1 |
| `produ_2011` | `xsd:double` | true | 0..1 |
| `produ_2012` | `xsd:double` | true | 0..1 |
| `produ_2013` | `xsd:double` | true | 0..1 |
| `produ_2014` | `xsd:double` | true | 0..1 |
| `produ_2015` | `xsd:double` | true | 0..1 |
| `produ_2016` | `xsd:double` | true | 0..1 |
| `produ_2017` | `xsd:double` | true | 0..1 |
| `produ_2018` | `xsd:double` | true | 0..1 |
| `rendi_1989` | `xsd:double` | true | 0..1 |
| `rendi_1990` | `xsd:double` | true | 0..1 |
| `rendi_1991` | `xsd:double` | true | 0..1 |
| `rendi_1992` | `xsd:double` | true | 0..1 |
| `rendi_1993` | `xsd:double` | true | 0..1 |
| `rendi_1994` | `xsd:double` | true | 0..1 |
| `rendi_1995` | `xsd:double` | true | 0..1 |
| `rendi_1996` | `xsd:double` | true | 0..1 |
| `rendi_1997` | `xsd:double` | true | 0..1 |
| `rendi_1998` | `xsd:double` | true | 0..1 |
| `rendi_1999` | `xsd:double` | true | 0..1 |
| `rendi_2000` | `xsd:double` | true | 0..1 |
| `rendi_2001` | `xsd:double` | true | 0..1 |
| `rendi_2002` | `xsd:double` | true | 0..1 |
| `rendi_2003` | `xsd:double` | true | 0..1 |
| `rendi_2004` | `xsd:double` | true | 0..1 |
| `rendi_2005` | `xsd:double` | true | 0..1 |
| `rendi_2006` | `xsd:double` | true | 0..1 |
| `rendi_2007` | `xsd:double` | true | 0..1 |
| `rendi_2008` | `xsd:double` | true | 0..1 |
| `rendi_2009` | `xsd:double` | true | 0..1 |
| `rendi_2010` | `xsd:double` | true | 0..1 |
| `rendi_2011` | `xsd:double` | true | 0..1 |
| `rendi_2012` | `xsd:double` | true | 0..1 |
| `rendi_2013` | `xsd:double` | true | 0..1 |
| `rendi_2014` | `xsd:double` | true | 0..1 |
| `rendi_2015` | `xsd:double` | true | 0..1 |
| `rendi_2016` | `xsd:double` | true | 0..1 |
| `rendi_2017` | `xsd:double` | true | 0..1 |
| `rendi_2018` | `xsd:double` | true | 0..1 |

### `estatistica:aquicultura_2013_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `pr_2013_1` | `xsd:long` | true | 0..1 |
| `pr_2013_2` | `xsd:double` | true | 0..1 |
| `pr_2013_3` | `xsd:long` | true | 0..1 |
| `pr_2013_4` | `xsd:double` | true | 0..1 |
| `pr_2013_5` | `xsd:double` | true | 0..1 |
| `pr_2013_6` | `xsd:double` | true | 0..1 |
| `pr_2013_7` | `xsd:double` | true | 0..1 |
| `pr_2013_8` | `xsd:double` | true | 0..1 |
| `pr_2013_9` | `xsd:double` | true | 0..1 |
| `pr_2013_10` | `xsd:double` | true | 0..1 |
| `pr_2013_11` | `xsd:long` | true | 0..1 |
| `pr_2013_12` | `xsd:double` | true | 0..1 |
| `pr_2013_13` | `xsd:string` | true | 0..1 |
| `pr_2013_14` | `xsd:double` | true | 0..1 |
| `pr_2013_15` | `xsd:double` | true | 0..1 |
| `pr_2013_16` | `xsd:long` | true | 0..1 |
| `pr_2013_17` | `xsd:double` | true | 0..1 |
| `pr_2013_18` | `xsd:double` | true | 0..1 |
| `pr_2013_19` | `xsd:double` | true | 0..1 |
| `pr_2013_20` | `xsd:long` | true | 0..1 |
| `pr_2013_21` | `xsd:long` | true | 0..1 |
| `pr_2013_22` | `xsd:long` | true | 0..1 |
| `pr_2013_23` | `xsd:long` | true | 0..1 |
| `pr_2014_1` | `xsd:long` | true | 0..1 |
| `pr_2014_2` | `xsd:double` | true | 0..1 |
| `pr_2014_3` | `xsd:long` | true | 0..1 |
| `pr_2014_4` | `xsd:double` | true | 0..1 |
| `pr_2014_5` | `xsd:double` | true | 0..1 |
| `pr_2014_6` | `xsd:double` | true | 0..1 |
| `pr_2014_7` | `xsd:double` | true | 0..1 |
| `pr_2014_8` | `xsd:double` | true | 0..1 |
| `pr_2014_9` | `xsd:double` | true | 0..1 |
| `pr_2014_10` | `xsd:double` | true | 0..1 |
| `pr_2014_11` | `xsd:double` | true | 0..1 |
| `pr_2014_12` | `xsd:double` | true | 0..1 |
| `pr_2014_13` | `xsd:string` | true | 0..1 |
| `pr_2014_14` | `xsd:double` | true | 0..1 |
| `pr_2014_15` | `xsd:double` | true | 0..1 |
| `pr_2014_16` | `xsd:long` | true | 0..1 |
| `pr_2014_17` | `xsd:double` | true | 0..1 |
| `pr_2014_18` | `xsd:double` | true | 0..1 |
| `pr_2014_19` | `xsd:double` | true | 0..1 |
| `pr_2014_20` | `xsd:long` | true | 0..1 |
| `pr_2014_21` | `xsd:long` | true | 0..1 |
| `pr_2014_22` | `xsd:long` | true | 0..1 |
| `pr_2014_23` | `xsd:long` | true | 0..1 |
| `pr_2015_1` | `xsd:long` | true | 0..1 |
| `pr_2015_2` | `xsd:double` | true | 0..1 |
| `pr_2015_3` | `xsd:long` | true | 0..1 |
| `pr_2015_4` | `xsd:double` | true | 0..1 |
| `pr_2015_5` | `xsd:double` | true | 0..1 |
| `pr_2015_6` | `xsd:double` | true | 0..1 |
| `pr_2015_7` | `xsd:double` | true | 0..1 |
| `pr_2015_8` | `xsd:double` | true | 0..1 |
| `pr_2015_9` | `xsd:double` | true | 0..1 |
| `pr_2015_10` | `xsd:double` | true | 0..1 |
| `pr_2015_11` | `xsd:double` | true | 0..1 |
| `pr_2015_12` | `xsd:double` | true | 0..1 |
| `pr_2015_13` | `xsd:string` | true | 0..1 |
| `pr_2015_14` | `xsd:double` | true | 0..1 |
| `pr_2015_15` | `xsd:double` | true | 0..1 |
| `pr_2015_16` | `xsd:long` | true | 0..1 |
| `pr_2015_17` | `xsd:double` | true | 0..1 |
| `pr_2015_18` | `xsd:long` | true | 0..1 |
| `pr_2015_19` | `xsd:double` | true | 0..1 |
| `pr_2015_20` | `xsd:long` | true | 0..1 |
| `pr_2015_21` | `xsd:long` | true | 0..1 |
| `pr_2015_22` | `xsd:long` | true | 0..1 |
| `pr_2015_23` | `xsd:long` | true | 0..1 |
| `pr_2016_1` | `xsd:long` | true | 0..1 |
| `pr_2016_2` | `xsd:double` | true | 0..1 |
| `pr_2016_3` | `xsd:long` | true | 0..1 |
| `pr_2016_4` | `xsd:double` | true | 0..1 |
| `pr_2016_5` | `xsd:double` | true | 0..1 |
| `pr_2016_6` | `xsd:double` | true | 0..1 |
| `pr_2016_7` | `xsd:double` | true | 0..1 |
| `pr_2016_8` | `xsd:double` | true | 0..1 |
| `pr_2016_9` | `xsd:double` | true | 0..1 |
| `pr_2016_10` | `xsd:double` | true | 0..1 |
| `pr_2016_11` | `xsd:double` | true | 0..1 |
| `pr_2016_12` | `xsd:double` | true | 0..1 |
| `pr_2016_13` | `xsd:string` | true | 0..1 |
| `pr_2016_14` | `xsd:double` | true | 0..1 |
| `pr_2016_15` | `xsd:double` | true | 0..1 |
| `pr_2016_16` | `xsd:long` | true | 0..1 |
| `pr_2016_17` | `xsd:double` | true | 0..1 |
| `pr_2016_18` | `xsd:long` | true | 0..1 |
| `pr_2016_19` | `xsd:double` | true | 0..1 |
| `pr_2016_20` | `xsd:long` | true | 0..1 |
| `pr_2016_21` | `xsd:long` | true | 0..1 |
| `pr_2016_22` | `xsd:long` | true | 0..1 |
| `pr_2016_23` | `xsd:long` | true | 0..1 |
| `pr_2017_1` | `xsd:long` | true | 0..1 |
| `pr_2017_2` | `xsd:double` | true | 0..1 |
| `pr_2017_3` | `xsd:long` | true | 0..1 |
| `pr_2017_4` | `xsd:double` | true | 0..1 |
| `pr_2017_5` | `xsd:double` | true | 0..1 |
| `pr_2017_6` | `xsd:double` | true | 0..1 |
| `pr_2017_7` | `xsd:double` | true | 0..1 |
| `pr_2017_8` | `xsd:double` | true | 0..1 |
| `pr_2017_9` | `xsd:double` | true | 0..1 |
| `pr_2017_10` | `xsd:double` | true | 0..1 |
| `pr_2017_11` | `xsd:double` | true | 0..1 |
| `pr_2017_12` | `xsd:double` | true | 0..1 |
| `pr_2017_13` | `xsd:string` | true | 0..1 |
| `pr_2017_14` | `xsd:double` | true | 0..1 |
| `pr_2017_15` | `xsd:double` | true | 0..1 |
| `pr_2017_16` | `xsd:long` | true | 0..1 |
| `pr_2017_17` | `xsd:double` | true | 0..1 |
| `pr_2017_18` | `xsd:double` | true | 0..1 |
| `pr_2017_19` | `xsd:double` | true | 0..1 |
| `pr_2017_20` | `xsd:long` | true | 0..1 |
| `pr_2017_21` | `xsd:long` | true | 0..1 |
| `pr_2017_22` | `xsd:long` | true | 0..1 |
| `pr_2017_23` | `xsd:long` | true | 0..1 |
| `pr_2018_1` | `xsd:long` | true | 0..1 |
| `pr_2018_2` | `xsd:double` | true | 0..1 |
| `pr_2018_3` | `xsd:long` | true | 0..1 |
| `pr_2018_4` | `xsd:double` | true | 0..1 |
| `pr_2018_5` | `xsd:long` | true | 0..1 |
| `pr_2018_6` | `xsd:double` | true | 0..1 |
| `pr_2018_7` | `xsd:double` | true | 0..1 |
| `pr_2018_8` | `xsd:double` | true | 0..1 |
| `pr_2018_9` | `xsd:double` | true | 0..1 |
| `pr_2018_10` | `xsd:double` | true | 0..1 |
| `pr_2018_11` | `xsd:double` | true | 0..1 |
| `pr_2018_12` | `xsd:double` | true | 0..1 |
| `pr_2018_13` | `xsd:string` | true | 0..1 |
| `pr_2018_14` | `xsd:double` | true | 0..1 |
| `pr_2018_15` | `xsd:double` | true | 0..1 |
| `pr_2018_16` | `xsd:long` | true | 0..1 |
| `pr_2018_17` | `xsd:double` | true | 0..1 |
| `pr_2018_18` | `xsd:double` | true | 0..1 |
| `pr_2018_19` | `xsd:double` | true | 0..1 |
| `pr_2018_20` | `xsd:long` | true | 0..1 |
| `pr_2018_21` | `xsd:long` | true | 0..1 |
| `pr_2018_22` | `xsd:long` | true | 0..1 |
| `pr_2018_23` | `xsd:long` | true | 0..1 |
| `val_2013_1` | `xsd:long` | true | 0..1 |
| `val_2013_2` | `xsd:long` | true | 0..1 |
| `val_2013_3` | `xsd:long` | true | 0..1 |
| `val_2013_4` | `xsd:long` | true | 0..1 |
| `val_2013_5` | `xsd:long` | true | 0..1 |
| `val_2013_6` | `xsd:double` | true | 0..1 |
| `val_2013_7` | `xsd:double` | true | 0..1 |
| `val_2013_8` | `xsd:long` | true | 0..1 |
| `val_2013_9` | `xsd:double` | true | 0..1 |
| `val_2013_` | `xsd:long` | true | 0..1 |
| `val_201_1` | `xsd:long` | true | 0..1 |
| `val_201_2` | `xsd:long` | true | 0..1 |
| `val_201_3` | `xsd:double` | true | 0..1 |
| `val_201_4` | `xsd:long` | true | 0..1 |
| `val_201_5` | `xsd:long` | true | 0..1 |
| `val_201_6` | `xsd:long` | true | 0..1 |
| `val_201_7` | `xsd:long` | true | 0..1 |
| `val_201_8` | `xsd:long` | true | 0..1 |
| `val_201_9` | `xsd:long` | true | 0..1 |
| `val_20110` | `xsd:long` | true | 0..1 |
| `val_20111` | `xsd:long` | true | 0..1 |
| `val_20112` | `xsd:long` | true | 0..1 |
| `val_20113` | `xsd:long` | true | 0..1 |
| `val_2014_1` | `xsd:long` | true | 0..1 |
| `val_2014_2` | `xsd:long` | true | 0..1 |
| `val_2014_3` | `xsd:long` | true | 0..1 |
| `val_2014_4` | `xsd:long` | true | 0..1 |
| `val_2014_5` | `xsd:long` | true | 0..1 |
| `val_2014_6` | `xsd:double` | true | 0..1 |
| `val_2014_7` | `xsd:double` | true | 0..1 |
| `val_2014_8` | `xsd:double` | true | 0..1 |
| `val_2014_9` | `xsd:double` | true | 0..1 |
| `val_2014_` | `xsd:long` | true | 0..1 |
| `val_20114` | `xsd:double` | true | 0..1 |
| `val_20115` | `xsd:double` | true | 0..1 |
| `val_20116` | `xsd:double` | true | 0..1 |
| `val_20117` | `xsd:long` | true | 0..1 |
| `val_20118` | `xsd:long` | true | 0..1 |
| `val_20119` | `xsd:long` | true | 0..1 |
| `val_20120` | `xsd:long` | true | 0..1 |
| `val_20121` | `xsd:long` | true | 0..1 |
| `val_20122` | `xsd:double` | true | 0..1 |
| `val_20123` | `xsd:long` | true | 0..1 |
| `val_20124` | `xsd:long` | true | 0..1 |
| `val_20125` | `xsd:long` | true | 0..1 |
| `val_20126` | `xsd:long` | true | 0..1 |
| `val_2015_1` | `xsd:long` | true | 0..1 |
| `val_2015_2` | `xsd:long` | true | 0..1 |
| `val_2015_3` | `xsd:long` | true | 0..1 |
| `val_2015_4` | `xsd:long` | true | 0..1 |
| `val_2015_5` | `xsd:long` | true | 0..1 |
| `val_2015_6` | `xsd:double` | true | 0..1 |
| `val_2015_7` | `xsd:double` | true | 0..1 |
| `val_2015_8` | `xsd:long` | true | 0..1 |
| `val_2015_9` | `xsd:double` | true | 0..1 |
| `val_2015_` | `xsd:long` | true | 0..1 |
| `val_20127` | `xsd:double` | true | 0..1 |
| `val_20128` | `xsd:double` | true | 0..1 |
| `val_20129` | `xsd:double` | true | 0..1 |
| `val_20130` | `xsd:long` | true | 0..1 |
| `val_20131` | `xsd:long` | true | 0..1 |
| `val_20132` | `xsd:long` | true | 0..1 |
| `val_20133` | `xsd:long` | true | 0..1 |
| `val_20134` | `xsd:long` | true | 0..1 |
| `val_20135` | `xsd:double` | true | 0..1 |
| `val_20136` | `xsd:long` | true | 0..1 |
| `val_20137` | `xsd:long` | true | 0..1 |
| `val_20138` | `xsd:long` | true | 0..1 |
| `val_20139` | `xsd:long` | true | 0..1 |
| `val_2016_1` | `xsd:long` | true | 0..1 |
| `val_2016_2` | `xsd:long` | true | 0..1 |
| `val_2016_3` | `xsd:long` | true | 0..1 |
| `val_2016_4` | `xsd:long` | true | 0..1 |
| `val_2016_5` | `xsd:long` | true | 0..1 |
| `val_2016_6` | `xsd:double` | true | 0..1 |
| `val_2016_7` | `xsd:double` | true | 0..1 |
| `val_2016_8` | `xsd:long` | true | 0..1 |
| `val_2016_9` | `xsd:double` | true | 0..1 |
| `val_2016_` | `xsd:long` | true | 0..1 |
| `val_20140` | `xsd:double` | true | 0..1 |
| `val_20141` | `xsd:double` | true | 0..1 |
| `val_20142` | `xsd:double` | true | 0..1 |
| `val_20143` | `xsd:long` | true | 0..1 |
| `val_20144` | `xsd:long` | true | 0..1 |
| `val_20145` | `xsd:long` | true | 0..1 |
| `val_20146` | `xsd:long` | true | 0..1 |
| `val_20147` | `xsd:long` | true | 0..1 |
| `val_20148` | `xsd:double` | true | 0..1 |
| `val_20149` | `xsd:long` | true | 0..1 |
| `val_20150` | `xsd:long` | true | 0..1 |
| `val_20151` | `xsd:long` | true | 0..1 |
| `val_20152` | `xsd:long` | true | 0..1 |
| `val_2017_1` | `xsd:long` | true | 0..1 |
| `val_2017_2` | `xsd:long` | true | 0..1 |
| `val_2017_3` | `xsd:long` | true | 0..1 |
| `val_2017_4` | `xsd:long` | true | 0..1 |
| `val_2017_5` | `xsd:long` | true | 0..1 |
| `val_2017_6` | `xsd:double` | true | 0..1 |
| `val_2017_7` | `xsd:double` | true | 0..1 |
| `val_2017_8` | `xsd:double` | true | 0..1 |
| `val_2017_9` | `xsd:double` | true | 0..1 |
| `val_2017_` | `xsd:long` | true | 0..1 |
| `val_20153` | `xsd:double` | true | 0..1 |
| `val_20154` | `xsd:double` | true | 0..1 |
| `val_20155` | `xsd:double` | true | 0..1 |
| `val_20156` | `xsd:long` | true | 0..1 |
| `val_20157` | `xsd:long` | true | 0..1 |
| `val_20158` | `xsd:long` | true | 0..1 |
| `val_20159` | `xsd:long` | true | 0..1 |
| `val_20160` | `xsd:long` | true | 0..1 |
| `val_20161` | `xsd:double` | true | 0..1 |
| `val_20162` | `xsd:long` | true | 0..1 |
| `val_20163` | `xsd:long` | true | 0..1 |
| `val_20164` | `xsd:long` | true | 0..1 |
| `val_20165` | `xsd:long` | true | 0..1 |
| `val_2018_1` | `xsd:long` | true | 0..1 |
| `val_2018_2` | `xsd:long` | true | 0..1 |
| `val_2018_3` | `xsd:long` | true | 0..1 |
| `val_2018_4` | `xsd:long` | true | 0..1 |
| `val_2018_5` | `xsd:long` | true | 0..1 |
| `val_2018_6` | `xsd:double` | true | 0..1 |
| `val_2018_7` | `xsd:long` | true | 0..1 |
| `val_2018_8` | `xsd:double` | true | 0..1 |
| `val_2018_9` | `xsd:double` | true | 0..1 |
| `val_2018_` | `xsd:long` | true | 0..1 |
| `val_20166` | `xsd:double` | true | 0..1 |
| `val_20167` | `xsd:double` | true | 0..1 |
| `val_20168` | `xsd:double` | true | 0..1 |
| `val_20169` | `xsd:long` | true | 0..1 |
| `val_20170` | `xsd:long` | true | 0..1 |
| `val_20171` | `xsd:long` | true | 0..1 |
| `val_20172` | `xsd:long` | true | 0..1 |
| `val_20173` | `xsd:long` | true | 0..1 |
| `val_20174` | `xsd:double` | true | 0..1 |
| `val_20175` | `xsd:long` | true | 0..1 |
| `val_20176` | `xsd:long` | true | 0..1 |
| `val_20177` | `xsd:long` | true | 0..1 |
| `val_20178` | `xsd:long` | true | 0..1 |

### `estatistica:bovino1989_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `bovin_1989` | `xsd:double` | true | 0..1 |
| `bovin_1990` | `xsd:double` | true | 0..1 |
| `bovin_1991` | `xsd:double` | true | 0..1 |
| `bovin_1992` | `xsd:double` | true | 0..1 |
| `bovin_1993` | `xsd:double` | true | 0..1 |
| `bovin_1994` | `xsd:double` | true | 0..1 |
| `bovin_1995` | `xsd:double` | true | 0..1 |
| `bovin_1996` | `xsd:double` | true | 0..1 |
| `bovin_1997` | `xsd:double` | true | 0..1 |
| `bovin_1998` | `xsd:double` | true | 0..1 |
| `bovin_1999` | `xsd:double` | true | 0..1 |
| `bovin_2000` | `xsd:double` | true | 0..1 |
| `bovin_2001` | `xsd:double` | true | 0..1 |
| `bovin_2002` | `xsd:double` | true | 0..1 |
| `bovin_2003` | `xsd:double` | true | 0..1 |
| `bovin_2004` | `xsd:double` | true | 0..1 |
| `bovin_2005` | `xsd:double` | true | 0..1 |
| `bovin_2006` | `xsd:double` | true | 0..1 |
| `bovin_2007` | `xsd:double` | true | 0..1 |
| `bovin_2008` | `xsd:double` | true | 0..1 |
| `bovin_2009` | `xsd:double` | true | 0..1 |
| `bovin_2010` | `xsd:double` | true | 0..1 |
| `bovin_2011` | `xsd:double` | true | 0..1 |
| `bovin_2012` | `xsd:double` | true | 0..1 |
| `bovin_2013` | `xsd:double` | true | 0..1 |
| `bovin_2014` | `xsd:double` | true | 0..1 |
| `bovin_2015` | `xsd:double` | true | 0..1 |
| `bovin_2016` | `xsd:double` | true | 0..1 |
| `bovin_2017` | `xsd:double` | true | 0..1 |
| `bovin_2018` | `xsd:double` | true | 0..1 |

### `estatistica:bubalinos1989_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `bubal_1989` | `xsd:double` | true | 0..1 |
| `bubal_1990` | `xsd:double` | true | 0..1 |
| `bubal_1991` | `xsd:double` | true | 0..1 |
| `bubal_1992` | `xsd:double` | true | 0..1 |
| `bubal_1993` | `xsd:double` | true | 0..1 |
| `bubal_1994` | `xsd:double` | true | 0..1 |
| `bubal_1995` | `xsd:double` | true | 0..1 |
| `bubal_1996` | `xsd:double` | true | 0..1 |
| `bubal_1997` | `xsd:double` | true | 0..1 |
| `bubal_1998` | `xsd:double` | true | 0..1 |
| `bubal_1999` | `xsd:double` | true | 0..1 |
| `bubal_2000` | `xsd:double` | true | 0..1 |
| `bubal_2001` | `xsd:double` | true | 0..1 |
| `bubal_2002` | `xsd:double` | true | 0..1 |
| `bubal_2003` | `xsd:double` | true | 0..1 |
| `bubal_2004` | `xsd:double` | true | 0..1 |
| `bubal_2005` | `xsd:double` | true | 0..1 |
| `bubal_2006` | `xsd:double` | true | 0..1 |
| `bubal_2007` | `xsd:double` | true | 0..1 |
| `bubal_2008` | `xsd:double` | true | 0..1 |
| `bubal_2009` | `xsd:double` | true | 0..1 |
| `bubal_2010` | `xsd:double` | true | 0..1 |
| `bubal_2011` | `xsd:double` | true | 0..1 |
| `bubal_2012` | `xsd:double` | true | 0..1 |
| `bubal_2013` | `xsd:double` | true | 0..1 |
| `bubal_2014` | `xsd:double` | true | 0..1 |
| `bubal_2015` | `xsd:double` | true | 0..1 |
| `bubal_2016` | `xsd:double` | true | 0..1 |
| `bubal_2017` | `xsd:double` | true | 0..1 |
| `bubal_2018` | `xsd:double` | true | 0..1 |

### `estatistica:caprino1989_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `capri_1989` | `xsd:double` | true | 0..1 |
| `capri_1990` | `xsd:double` | true | 0..1 |
| `capri_1991` | `xsd:double` | true | 0..1 |
| `capri_1992` | `xsd:double` | true | 0..1 |
| `capri_1993` | `xsd:double` | true | 0..1 |
| `capri_1994` | `xsd:double` | true | 0..1 |
| `capri_1995` | `xsd:double` | true | 0..1 |
| `capri_1996` | `xsd:double` | true | 0..1 |
| `capri_1997` | `xsd:double` | true | 0..1 |
| `capri_1998` | `xsd:double` | true | 0..1 |
| `capri_1999` | `xsd:double` | true | 0..1 |
| `capri_2000` | `xsd:double` | true | 0..1 |
| `capri_2001` | `xsd:double` | true | 0..1 |
| `capri_2002` | `xsd:double` | true | 0..1 |
| `capri_2003` | `xsd:double` | true | 0..1 |
| `capri_2004` | `xsd:double` | true | 0..1 |
| `capri_2005` | `xsd:double` | true | 0..1 |
| `capri_2006` | `xsd:double` | true | 0..1 |
| `capri_2007` | `xsd:double` | true | 0..1 |
| `capri_2008` | `xsd:double` | true | 0..1 |
| `capri_2009` | `xsd:double` | true | 0..1 |
| `capri_2010` | `xsd:double` | true | 0..1 |
| `capri_2011` | `xsd:double` | true | 0..1 |
| `capri_2012` | `xsd:double` | true | 0..1 |
| `capri_2013` | `xsd:double` | true | 0..1 |
| `capri_2014` | `xsd:double` | true | 0..1 |
| `capri_2015` | `xsd:double` | true | 0..1 |
| `capri_2016` | `xsd:double` | true | 0..1 |
| `capri_2017` | `xsd:double` | true | 0..1 |
| `capri_2018` | `xsd:double` | true | 0..1 |

### `estatistica:codorna`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `nume_cid` | `xsd:string` | true | 0..1 |
| `pgai` | `xsd:string` | true | 0..1 |
| `tipo_cidd` | `xsd:string` | true | 0..1 |
| `regiao_num` | `xsd:string` | true | 0..1 |
| `territ_cid` | `xsd:string` | true | 0..1 |
| `utr` | `xsd:string` | true | 0..1 |
| `criacao` | `xsd:string` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `pop_1996` | `xsd:double` | true | 0..1 |
| `pop_2000` | `xsd:double` | true | 0..1 |
| `pop_2007` | `xsd:double` | true | 0..1 |
| `pop_2008` | `xsd:double` | true | 0..1 |
| `pop_2009` | `xsd:double` | true | 0..1 |
| `assoc_mun` | `xsd:string` | true | 0..1 |
| `reg_pm` | `xsd:string` | true | 0..1 |
| `art_pm` | `xsd:string` | true | 0..1 |
| `region_ibg` | `xsd:string` | true | 0..1 |
| `cod_region` | `xsd:double` | true | 0..1 |
| `pop_2010` | `xsd:double` | true | 0..1 |
| `ppa_2012_2` | `xsd:string` | true | 0..1 |
| `number` | `xsd:double` | true | 0..1 |
| `regionaliz` | `xsd:string` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `reg_tur` | `xsd:string` | true | 0..1 |
| `nova_regio` | `xsd:string` | true | 0..1 |
| `nova_reg_o` | `xsd:string` | true | 0..1 |
| `codor_1989` | `xsd:double` | true | 0..1 |
| `codor_1990` | `xsd:double` | true | 0..1 |
| `codor_1991` | `xsd:double` | true | 0..1 |
| `codor_1992` | `xsd:double` | true | 0..1 |
| `codor_1993` | `xsd:double` | true | 0..1 |
| `codor_1994` | `xsd:double` | true | 0..1 |
| `codor_1995` | `xsd:double` | true | 0..1 |
| `codor_1996` | `xsd:double` | true | 0..1 |
| `codor_1997` | `xsd:double` | true | 0..1 |
| `codor_1998` | `xsd:double` | true | 0..1 |
| `codor_1999` | `xsd:double` | true | 0..1 |
| `codor_2000` | `xsd:double` | true | 0..1 |
| `codor_2001` | `xsd:double` | true | 0..1 |
| `codor_2002` | `xsd:double` | true | 0..1 |
| `codor_2003` | `xsd:double` | true | 0..1 |
| `codor_2004` | `xsd:double` | true | 0..1 |
| `codor_2005` | `xsd:double` | true | 0..1 |
| `codor_2006` | `xsd:double` | true | 0..1 |
| `codor_2007` | `xsd:double` | true | 0..1 |
| `codor_2008` | `xsd:double` | true | 0..1 |
| `codor_2009` | `xsd:double` | true | 0..1 |
| `codor_2010` | `xsd:double` | true | 0..1 |
| `codor_2011` | `xsd:double` | true | 0..1 |
| `codor_2012` | `xsd:double` | true | 0..1 |
| `codor_2013` | `xsd:double` | true | 0..1 |
| `codor_2014` | `xsd:double` | true | 0..1 |
| `codor_2015` | `xsd:double` | true | 0..1 |
| `codor_2016` | `xsd:double` | true | 0..1 |
| `codor_2017` | `xsd:double` | true | 0..1 |
| `codor_2018` | `xsd:double` | true | 0..1 |

### `estatistica:coeficiente_deteccao_anual_hanseniase`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `hans_2017` | `xsd:long` | true | 0..1 |
| `hans_2007` | `xsd:double` | true | 0..1 |
| `hans_2008` | `xsd:double` | true | 0..1 |
| `hans_2009` | `xsd:double` | true | 0..1 |
| `hans_2010` | `xsd:double` | true | 0..1 |
| `hans_2011` | `xsd:double` | true | 0..1 |
| `hans_2012` | `xsd:double` | true | 0..1 |
| `hans_2013` | `xsd:double` | true | 0..1 |
| `hans_2014` | `xsd:double` | true | 0..1 |
| `hans_2015` | `xsd:double` | true | 0..1 |
| `hans_2016` | `xsd:double` | true | 0..1 |

### `estatistica:docentes_separados_2014`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `cod_ibge_1` | `xsd:long` | true | 0..1 |
| `color` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:int` | true | 0..1 |
| `last_modification_1` | `xsd:date` | true | 0..1 |
| `modified_by_1` | `xsd:string` | true | 0..1 |
| `ndc_est_ru` | `xsd:long` | true | 0..1 |
| `ndc_est_ur` | `xsd:long` | true | 0..1 |
| `ndc_mun_ru` | `xsd:long` | true | 0..1 |
| `ndc_mun_u` | `xsd:long` | true | 0..1 |
| `ndc_mun_ur` | `xsd:long` | true | 0..1 |
| `ndc_pa_ru` | `xsd:long` | true | 0..1 |
| `ndc_pa_ur` | `xsd:long` | true | 0..1 |
| `nde_e_ru` | `xsd:long` | true | 0..1 |
| `nde_e_ur` | `xsd:long` | true | 0..1 |
| `nde_m_ur` | `xsd:long` | true | 0..1 |
| `nde_pa_ur` | `xsd:long` | true | 0..1 |
| `ndeja_e_r` | `xsd:long` | true | 0..1 |
| `ndeja_e_ru` | `xsd:long` | true | 0..1 |
| `ndeja_e_u` | `xsd:long` | true | 0..1 |
| `ndeja_e_ur` | `xsd:long` | true | 0..1 |
| `ndeja_m_ru` | `xsd:long` | true | 0..1 |
| `ndeja_m_u` | `xsd:long` | true | 0..1 |
| `ndeja_m_ur` | `xsd:long` | true | 0..1 |
| `ndeja_p_ru` | `xsd:long` | true | 0..1 |
| `ndeja_p_u` | `xsd:long` | true | 0..1 |
| `ndeja_p_ur` | `xsd:long` | true | 0..1 |
| `ndeja_ur_f` | `xsd:long` | true | 0..1 |
| `ndf_es_ru` | `xsd:long` | true | 0..1 |
| `ndf_es_ur` | `xsd:long` | true | 0..1 |
| `ndf_mun_ru` | `xsd:long` | true | 0..1 |
| `ndf_mun_ur` | `xsd:long` | true | 0..1 |
| `ndf_pa_ru` | `xsd:long` | true | 0..1 |
| `ndf_pa_ur` | `xsd:long` | true | 0..1 |
| `ndm_es_ru` | `xsd:long` | true | 0..1 |
| `ndm_es_ur` | `xsd:long` | true | 0..1 |
| `ndm_mun_ru` | `xsd:long` | true | 0..1 |
| `ndm_mun_ur` | `xsd:long` | true | 0..1 |
| `ndm_pa_ru` | `xsd:long` | true | 0..1 |
| `ndm_pa_ur` | `xsd:long` | true | 0..1 |
| `ndm_ru_fe` | `xsd:long` | true | 0..1 |
| `ndm_ur_fe` | `xsd:long` | true | 0..1 |
| `ndp_es_ru` | `xsd:long` | true | 0..1 |
| `ndp_es_u` | `xsd:long` | true | 0..1 |
| `ndp_es_ur` | `xsd:long` | true | 0..1 |
| `ndp_mun_ru` | `xsd:long` | true | 0..1 |
| `ndp_pa_r` | `xsd:long` | true | 0..1 |
| `ndp_pa_ru` | `xsd:long` | true | 0..1 |
| `ndp_pa_u` | `xsd:long` | true | 0..1 |
| `ndp_pa_ur` | `xsd:long` | true | 0..1 |
| `ndp_ru_fe` | `xsd:long` | true | 0..1 |
| `ndp_ur_fe` | `xsd:long` | true | 0..1 |

### `estatistica:docentes_separados_por_categoria_2012`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `cod_ibge_1` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `es_ru_en` | `xsd:int` | true | 0..1 |
| `es_ru_to` | `xsd:int` | true | 0..1 |
| `es_ru_tot` | `xsd:int` | true | 0..1 |
| `es_ur_en` | `xsd:int` | true | 0..1 |
| `es_ur_er` | `xsd:int` | true | 0..1 |
| `es_ur_to` | `xsd:int` | true | 0..1 |
| `es_ur_tot` | `xsd:int` | true | 0..1 |
| `est_ru_en` | `xsd:int` | true | 0..1 |
| `est_ru_pr` | `xsd:int` | true | 0..1 |
| `est_ur_en` | `xsd:int` | true | 0..1 |
| `est_urb_pr` | `xsd:int` | true | 0..1 |
| `fe_ru_ed` | `xsd:int` | true | 0..1 |
| `fe_ru_en` | `xsd:int` | true | 0..1 |
| `fe_ru_tot` | `xsd:int` | true | 0..1 |
| `fe_ur_ed` | `xsd:int` | true | 0..1 |
| `fe_ur_en` | `xsd:int` | true | 0..1 |
| `fe_ur_tot` | `xsd:int` | true | 0..1 |
| `mu_ru_en` | `xsd:int` | true | 0..1 |
| `mun_ru_en` | `xsd:int` | true | 0..1 |
| `mun_ru_pr` | `xsd:int` | true | 0..1 |
| `mun_ru_to` | `xsd:int` | true | 0..1 |
| `mun_ru_tot` | `xsd:int` | true | 0..1 |
| `mun_ur_en` | `xsd:int` | true | 0..1 |
| `mun_ur_to` | `xsd:int` | true | 0..1 |
| `mun_ur_tot` | `xsd:int` | true | 0..1 |
| `mun_urb_pr` | `xsd:int` | true | 0..1 |
| `pri_ru_e` | `xsd:int` | true | 0..1 |
| `pri_ru_ed` | `xsd:int` | true | 0..1 |
| `pri_ru_en` | `xsd:int` | true | 0..1 |
| `pri_ru_tot` | `xsd:int` | true | 0..1 |
| `pri_ur` | `xsd:string` | true | 0..1 |
| `pri_ur_ed` | `xsd:int` | true | 0..1 |
| `pri_ur_en` | `xsd:int` | true | 0..1 |
| `pri_ur_pr` | `xsd:int` | true | 0..1 |
| `pri_ur_to` | `xsd:int` | true | 0..1 |
| `pri_ur_tot` | `xsd:int` | true | 0..1 |

### `estatistica:docentes_separados_por_categoria_2015`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `cod_ibge_1` | `xsd:long` | true | 0..1 |
| `color` | `xsd:long` | true | 0..1 |
| `last_modification` | `xsd:date` | true | 0..1 |
| `modified_by` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `d_eja_es` | `xsd:long` | true | 0..1 |
| `d_eja_fe` | `xsd:long` | true | 0..1 |
| `d_eja_mu` | `xsd:long` | true | 0..1 |
| `d_eja_pa` | `xsd:long` | true | 0..1 |
| `d_es_es` | `xsd:long` | true | 0..1 |
| `d_es_fe` | `xsd:long` | true | 0..1 |
| `d_es_mu` | `xsd:long` | true | 0..1 |
| `d_es_pa` | `xsd:long` | true | 0..1 |
| `do_cre_es` | `xsd:long` | true | 0..1 |
| `do_cre_mu` | `xsd:long` | true | 0..1 |
| `do_cre_pa` | `xsd:long` | true | 0..1 |
| `do_fu_es` | `xsd:long` | true | 0..1 |
| `do_fu_mu` | `xsd:long` | true | 0..1 |
| `do_fu_pa` | `xsd:long` | true | 0..1 |
| `do_me_es` | `xsd:long` | true | 0..1 |
| `do_me_fe` | `xsd:long` | true | 0..1 |
| `do_me_mu` | `xsd:long` | true | 0..1 |
| `do_me_pa` | `xsd:long` | true | 0..1 |
| `do_pre_es` | `xsd:long` | true | 0..1 |
| `do_pre_mu` | `xsd:long` | true | 0..1 |
| `do_pre_pa` | `xsd:long` | true | 0..1 |
| `do_pro_es` | `xsd:long` | true | 0..1 |
| `do_pro_fe` | `xsd:long` | true | 0..1 |
| `do_pro_mu` | `xsd:long` | true | 0..1 |
| `do_pro_pa` | `xsd:long` | true | 0..1 |

### `estatistica:equinos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `nume_cid` | `xsd:string` | true | 0..1 |
| `pgai` | `xsd:string` | true | 0..1 |
| `tipo_cidd` | `xsd:string` | true | 0..1 |
| `regiao_num` | `xsd:string` | true | 0..1 |
| `territ_cid` | `xsd:string` | true | 0..1 |
| `utr` | `xsd:string` | true | 0..1 |
| `criacao` | `xsd:string` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `pop_1996` | `xsd:double` | true | 0..1 |
| `pop_2000` | `xsd:double` | true | 0..1 |
| `pop_2007` | `xsd:double` | true | 0..1 |
| `pop_2008` | `xsd:double` | true | 0..1 |
| `pop_2009` | `xsd:double` | true | 0..1 |
| `assoc_mun` | `xsd:string` | true | 0..1 |
| `reg_pm` | `xsd:string` | true | 0..1 |
| `art_pm` | `xsd:string` | true | 0..1 |
| `region_ibg` | `xsd:string` | true | 0..1 |
| `cod_region` | `xsd:double` | true | 0..1 |
| `pop_2010` | `xsd:double` | true | 0..1 |
| `ppa_2012_2` | `xsd:string` | true | 0..1 |
| `number` | `xsd:double` | true | 0..1 |
| `regionaliz` | `xsd:string` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `reg_tur` | `xsd:string` | true | 0..1 |
| `nova_regio` | `xsd:string` | true | 0..1 |
| `nova_reg_o` | `xsd:string` | true | 0..1 |
| `municipios` | `xsd:string` | true | 0..1 |
| `equin1989` | `xsd:double` | true | 0..1 |
| `equin1990` | `xsd:double` | true | 0..1 |
| `equin1991` | `xsd:double` | true | 0..1 |
| `equin1992` | `xsd:double` | true | 0..1 |
| `equin1993` | `xsd:double` | true | 0..1 |
| `equin1994` | `xsd:double` | true | 0..1 |
| `equin1995` | `xsd:double` | true | 0..1 |
| `equin1996` | `xsd:double` | true | 0..1 |
| `equin1997` | `xsd:double` | true | 0..1 |
| `equin1998` | `xsd:double` | true | 0..1 |
| `equin1999` | `xsd:double` | true | 0..1 |
| `equin2000` | `xsd:double` | true | 0..1 |
| `equin2001` | `xsd:double` | true | 0..1 |
| `equin2002` | `xsd:double` | true | 0..1 |
| `equin2003` | `xsd:double` | true | 0..1 |
| `equin2004` | `xsd:double` | true | 0..1 |
| `equin2005` | `xsd:double` | true | 0..1 |
| `equin2006` | `xsd:double` | true | 0..1 |
| `equin2007` | `xsd:double` | true | 0..1 |
| `equin2008` | `xsd:double` | true | 0..1 |
| `equin2009` | `xsd:double` | true | 0..1 |
| `equin2010` | `xsd:double` | true | 0..1 |
| `equin2011` | `xsd:double` | true | 0..1 |
| `equin2012` | `xsd:double` | true | 0..1 |
| `equin2013` | `xsd:double` | true | 0..1 |
| `equin2014` | `xsd:double` | true | 0..1 |
| `equin2015` | `xsd:double` | true | 0..1 |
| `equin2016` | `xsd:double` | true | 0..1 |
| `equin2017` | `xsd:double` | true | 0..1 |
| `equin2018` | `xsd:double` | true | 0..1 |

### `estatistica:estabelecimentos_2012`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `mun_ur_pre` | `xsd:int` | true | 0..1 |
| `mun_ru_pre` | `xsd:int` | true | 0..1 |
| `pri_ur_pre` | `xsd:int` | true | 0..1 |
| `es_ur` | `xsd:int` | true | 0..1 |
| `es_ru` | `xsd:int` | true | 0..1 |
| `mun_ur` | `xsd:int` | true | 0..1 |
| `mun_r` | `xsd:int` | true | 0..1 |
| `pri_ur` | `xsd:int` | true | 0..1 |
| `pri_ru` | `xsd:int` | true | 0..1 |
| `fed` | `xsd:string` | true | 0..1 |
| `fed_ru` | `xsd:int` | true | 0..1 |
| `est` | `xsd:string` | true | 0..1 |
| `est_re` | `xsd:int` | true | 0..1 |
| `mun_ru` | `xsd:int` | true | 0..1 |
| `pri_urbano` | `xsd:int` | true | 0..1 |
| `pri_rural` | `xsd:int` | true | 0..1 |
| `fed_ur` | `xsd:int` | true | 0..1 |
| `fed_r` | `xsd:int` | true | 0..1 |
| `est_u` | `xsd:int` | true | 0..1 |
| `pri_rl` | `xsd:int` | true | 0..1 |
| `pri` | `xsd:string` | true | 0..1 |
| `fed_u` | `xsd:int` | true | 0..1 |
| `fed_rural` | `xsd:int` | true | 0..1 |
| `est_ur` | `xsd:int` | true | 0..1 |
| `est_ru` | `xsd:int` | true | 0..1 |
| `mun_u` | `xsd:int` | true | 0..1 |
| `mun` | `xsd:string` | true | 0..1 |
| `pri_u` | `xsd:int` | true | 0..1 |
| `pri_r` | `xsd:int` | true | 0..1 |
| `es_ur_tot` | `xsd:int` | true | 0..1 |
| `es_ru_tot` | `xsd:int` | true | 0..1 |
| `mun_ur_tot` | `xsd:int` | true | 0..1 |
| `mun_ru_tot` | `xsd:int` | true | 0..1 |
| `pri_ur_tot` | `xsd:int` | true | 0..1 |

### `estatistica:estabelecimentos_2014`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `nepe_mur` | `xsd:int` | true | 0..1 |
| `nepe_mru` | `xsd:int` | true | 0..1 |
| `nepe_pur` | `xsd:int` | true | 0..1 |
| `nepe_pru` | `xsd:int` | true | 0..1 |
| `neef_eur` | `xsd:int` | true | 0..1 |
| `neef_eru` | `xsd:int` | true | 0..1 |
| `neef_mur` | `xsd:int` | true | 0..1 |
| `neef_mru` | `xsd:int` | true | 0..1 |
| `neef_pur` | `xsd:int` | true | 0..1 |
| `neef_pru` | `xsd:int` | true | 0..1 |
| `neem_urf` | `xsd:int` | true | 0..1 |
| `neem_ruf` | `xsd:int` | true | 0..1 |
| `neem_eur` | `xsd:int` | true | 0..1 |
| `neem_eru` | `xsd:int` | true | 0..1 |
| `neem_mru` | `xsd:int` | true | 0..1 |
| `neem_pur` | `xsd:int` | true | 0..1 |
| `neem_pru` | `xsd:int` | true | 0..1 |
| `neep_urf` | `xsd:int` | true | 0..1 |
| `neep_ruf` | `xsd:int` | true | 0..1 |
| `neep_m_eur` | `xsd:int` | true | 0..1 |
| `neep_pur` | `xsd:int` | true | 0..1 |
| `neep_pru` | `xsd:int` | true | 0..1 |
| `neeef_eur` | `xsd:int` | true | 0..1 |
| `neeef_eru` | `xsd:int` | true | 0..1 |
| `neeef_mur` | `xsd:int` | true | 0..1 |
| `neeef_mru` | `xsd:int` | true | 0..1 |
| `neeef_pur` | `xsd:int` | true | 0..1 |
| `neeef_pru` | `xsd:int` | true | 0..1 |
| `neeem_urf` | `xsd:int` | true | 0..1 |
| `neeem_eur` | `xsd:int` | true | 0..1 |
| `neeem_eru` | `xsd:int` | true | 0..1 |
| `neeem_mur` | `xsd:int` | true | 0..1 |
| `neeem_pur` | `xsd:int` | true | 0..1 |
| `neeem_pru` | `xsd:int` | true | 0..1 |
| `neee_fru` | `xsd:int` | true | 0..1 |
| `neee_eur` | `xsd:int` | true | 0..1 |
| `neee_eru` | `xsd:int` | true | 0..1 |
| `neee_mur` | `xsd:int` | true | 0..1 |
| `neee_pur` | `xsd:int` | true | 0..1 |

### `estatistica:estabelecimentos_2015`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `eec_e` | `xsd:int` | true | 0..1 |
| `eec_m` | `xsd:int` | true | 0..1 |
| `eec_p` | `xsd:int` | true | 0..1 |
| `eepe_e` | `xsd:int` | true | 0..1 |
| `eepe_m` | `xsd:int` | true | 0..1 |
| `eepe_p` | `xsd:int` | true | 0..1 |
| `eef_e` | `xsd:int` | true | 0..1 |
| `eef_m` | `xsd:int` | true | 0..1 |
| `eef_p` | `xsd:int` | true | 0..1 |
| `eem_f` | `xsd:int` | true | 0..1 |
| `eem_e` | `xsd:int` | true | 0..1 |
| `eem_m` | `xsd:int` | true | 0..1 |
| `eem_p` | `xsd:int` | true | 0..1 |
| `eep_f` | `xsd:int` | true | 0..1 |
| `eep_e` | `xsd:int` | true | 0..1 |
| `eep_m` | `xsd:int` | true | 0..1 |
| `eep_p` | `xsd:int` | true | 0..1 |
| `ee_eja_fe` | `xsd:int` | true | 0..1 |
| `ee_eja_es` | `xsd:int` | true | 0..1 |
| `ee_eja_mu` | `xsd:int` | true | 0..1 |
| `ee_eja_pa` | `xsd:int` | true | 0..1 |
| `eee_fe` | `xsd:int` | true | 0..1 |
| `eee_es` | `xsd:int` | true | 0..1 |
| `eee_mu` | `xsd:int` | true | 0..1 |
| `eee_pa` | `xsd:int` | true | 0..1 |

### `estatistica:estimativa_populacao`

> [!warning] Schema pendente
> Este esquema ainda não foi resolvido nesta coleta. Reconsulte o endpoint antes de usar a camada.


### `estatistica:galinaceo1`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `galin_1989` | `xsd:long` | true | 0..1 |
| `galin_1990` | `xsd:long` | true | 0..1 |
| `galin_1991` | `xsd:long` | true | 0..1 |
| `galin_1992` | `xsd:long` | true | 0..1 |
| `galin_1993` | `xsd:long` | true | 0..1 |
| `galin_1994` | `xsd:long` | true | 0..1 |
| `galin_1996` | `xsd:long` | true | 0..1 |
| `galin_1997` | `xsd:long` | true | 0..1 |
| `galin_1998` | `xsd:long` | true | 0..1 |
| `galin_1999` | `xsd:long` | true | 0..1 |
| `galin_2000` | `xsd:long` | true | 0..1 |
| `galin_2001` | `xsd:long` | true | 0..1 |
| `galin_2002` | `xsd:long` | true | 0..1 |
| `galin_2003` | `xsd:long` | true | 0..1 |
| `galin_2004` | `xsd:long` | true | 0..1 |
| `galin_2005` | `xsd:long` | true | 0..1 |
| `galin_2006` | `xsd:long` | true | 0..1 |
| `galin_2007` | `xsd:long` | true | 0..1 |
| `galin_2008` | `xsd:long` | true | 0..1 |
| `galin_2009` | `xsd:long` | true | 0..1 |
| `galin_2010` | `xsd:long` | true | 0..1 |
| `galin_2011` | `xsd:long` | true | 0..1 |
| `galin_2012` | `xsd:long` | true | 0..1 |
| `galin_2013` | `xsd:long` | true | 0..1 |
| `galin_2014` | `xsd:long` | true | 0..1 |
| `galin_2015` | `xsd:long` | true | 0..1 |
| `galin_2016` | `xsd:long` | true | 0..1 |
| `galin_2017` | `xsd:long` | true | 0..1 |
| `galin_2018` | `xsd:long` | true | 0..1 |
| `galin_1995` | `xsd:long` | true | 0..1 |

### `estatistica:imunizacao_em_menores`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `bcg_n_2013` | `xsd:double` | true | 0..1 |
| `bcg_c_2013` | `xsd:double` | true | 0..1 |
| `dtp_n_2013` | `xsd:double` | true | 0..1 |
| `dtp_c_2013` | `xsd:double` | true | 0..1 |
| `pol_n_2013` | `xsd:double` | true | 0..1 |
| `pol_c_2013` | `xsd:double` | true | 0..1 |
| `feb_n_2013` | `xsd:double` | true | 0..1 |
| `feb_c_2013` | `xsd:double` | true | 0..1 |
| `bcg_n_2014` | `xsd:double` | true | 0..1 |
| `bcg_c_2014` | `xsd:double` | true | 0..1 |
| `bcg_n_2015` | `xsd:double` | true | 0..1 |
| `bcg_c_2015` | `xsd:double` | true | 0..1 |
| `dtp_n_2014` | `xsd:double` | true | 0..1 |
| `dtp_c_2014` | `xsd:double` | true | 0..1 |
| `dtp_n_2015` | `xsd:double` | true | 0..1 |
| `dtp_c_2015` | `xsd:double` | true | 0..1 |
| `pol_n_2014` | `xsd:double` | true | 0..1 |
| `pol_c_2014` | `xsd:double` | true | 0..1 |
| `pol_n_2015` | `xsd:double` | true | 0..1 |
| `pol_c_2015` | `xsd:double` | true | 0..1 |
| `feb_n_2014` | `xsd:double` | true | 0..1 |
| `feb_c_2014` | `xsd:double` | true | 0..1 |
| `feb_n_2015` | `xsd:double` | true | 0..1 |
| `feb_c_2015` | `xsd:double` | true | 0..1 |

### `estatistica:indice_2013`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `ideb_ai_e` | `xsd:double` | true | 0..1 |
| `ideb_ai_m` | `xsd:double` | true | 0..1 |
| `ideb_ai_p` | `xsd:double` | true | 0..1 |
| `ideb_af_e` | `xsd:double` | true | 0..1 |
| `ideb_af_m` | `xsd:double` | true | 0..1 |
| `ideb_af_p` | `xsd:double` | true | 0..1 |

### `estatistica:indice_2015`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `ideb_ai_e` | `xsd:double` | true | 0..1 |
| `ideb_ai_m` | `xsd:double` | true | 0..1 |
| `ideb_ai_p` | `xsd:double` | true | 0..1 |
| `ideb_af_e` | `xsd:double` | true | 0..1 |
| `ideb_af_m` | `xsd:double` | true | 0..1 |
| `ideb_af_p` | `xsd:double` | true | 0..1 |

### `estatistica:inidce_2009`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `ideb_ai_e` | `xsd:double` | true | 0..1 |
| `ideb_ai_m` | `xsd:double` | true | 0..1 |
| `ideb_ai_p` | `xsd:double` | true | 0..1 |
| `ideb_af_e` | `xsd:double` | true | 0..1 |
| `ideb_af_m` | `xsd:double` | true | 0..1 |
| `adeb_af_p` | `xsd:double` | true | 0..1 |

### `estatistica:inidce_2011`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `ideb_ai_e` | `xsd:long` | true | 0..1 |
| `ideb_ai_m` | `xsd:double` | true | 0..1 |
| `ideb_ai_p` | `xsd:double` | true | 0..1 |
| `ideb_af_e` | `xsd:double` | true | 0..1 |
| `ideb_af_m` | `xsd:long` | true | 0..1 |
| `ideb_af_p` | `xsd:double` | true | 0..1 |

### `estatistica:lavoura_permanente_abacate_1989a2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `nume_cid` | `xsd:string` | true | 0..1 |
| `pgai` | `xsd:string` | true | 0..1 |
| `tipo_cidd` | `xsd:string` | true | 0..1 |
| `regiao_num` | `xsd:string` | true | 0..1 |
| `territ_cid` | `xsd:string` | true | 0..1 |
| `utr` | `xsd:string` | true | 0..1 |
| `criacao` | `xsd:string` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `pop_1996` | `xsd:double` | true | 0..1 |
| `pop_2000` | `xsd:double` | true | 0..1 |
| `pop_2007` | `xsd:double` | true | 0..1 |
| `pop_2008` | `xsd:double` | true | 0..1 |
| `pop_2009` | `xsd:double` | true | 0..1 |
| `assoc_mun` | `xsd:string` | true | 0..1 |
| `reg_pm` | `xsd:string` | true | 0..1 |
| `art_pm` | `xsd:string` | true | 0..1 |
| `region_ibg` | `xsd:string` | true | 0..1 |
| `cod_region` | `xsd:double` | true | 0..1 |
| `pop_2010` | `xsd:double` | true | 0..1 |
| `ppa_2012_2` | `xsd:string` | true | 0..1 |
| `number` | `xsd:double` | true | 0..1 |
| `regionaliz` | `xsd:string` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `reg_tur` | `xsd:string` | true | 0..1 |
| `nova_regio` | `xsd:string` | true | 0..1 |
| `nova_reg_o` | `xsd:string` | true | 0..1 |
| `cultura` | `xsd:string` | true | 0..1 |
| `plant_1989` | `xsd:double` | true | 0..1 |
| `plant_1990` | `xsd:double` | true | 0..1 |
| `plant_1991` | `xsd:double` | true | 0..1 |
| `plant_1992` | `xsd:double` | true | 0..1 |
| `plant_1993` | `xsd:double` | true | 0..1 |
| `plant_1994` | `xsd:double` | true | 0..1 |
| `plant_1995` | `xsd:double` | true | 0..1 |
| `plant_1996` | `xsd:double` | true | 0..1 |
| `plant_1997` | `xsd:double` | true | 0..1 |
| `plant_1998` | `xsd:double` | true | 0..1 |
| `plant_1999` | `xsd:double` | true | 0..1 |
| `plant_2000` | `xsd:double` | true | 0..1 |
| `plant_2001` | `xsd:double` | true | 0..1 |
| `plant_2002` | `xsd:double` | true | 0..1 |
| `plant_2003` | `xsd:double` | true | 0..1 |
| `plant_2004` | `xsd:double` | true | 0..1 |
| `plant_2005` | `xsd:double` | true | 0..1 |
| `plant_2006` | `xsd:double` | true | 0..1 |
| `plant_2007` | `xsd:double` | true | 0..1 |
| `plant_2008` | `xsd:double` | true | 0..1 |
| `plant_2009` | `xsd:double` | true | 0..1 |
| `plant_2010` | `xsd:double` | true | 0..1 |
| `plant_2011` | `xsd:double` | true | 0..1 |
| `plant_2012` | `xsd:double` | true | 0..1 |
| `plant_2013` | `xsd:double` | true | 0..1 |
| `plant_2014` | `xsd:double` | true | 0..1 |
| `plant_2015` | `xsd:double` | true | 0..1 |
| `plant_2016` | `xsd:double` | true | 0..1 |
| `plant_2017` | `xsd:double` | true | 0..1 |
| `plant_2018` | `xsd:double` | true | 0..1 |
| `colhi_1989` | `xsd:double` | true | 0..1 |
| `colhi_1990` | `xsd:double` | true | 0..1 |
| `colhi_1991` | `xsd:double` | true | 0..1 |
| `colhi_1992` | `xsd:double` | true | 0..1 |
| `colhi_1993` | `xsd:double` | true | 0..1 |
| `colhi_1994` | `xsd:double` | true | 0..1 |
| `colhi_1995` | `xsd:double` | true | 0..1 |
| `colhi_1996` | `xsd:double` | true | 0..1 |
| `colhi_1997` | `xsd:double` | true | 0..1 |
| `colhi_1998` | `xsd:double` | true | 0..1 |
| `colhi_1999` | `xsd:double` | true | 0..1 |
| `colhi_2000` | `xsd:double` | true | 0..1 |
| `colhi_2001` | `xsd:double` | true | 0..1 |
| `colhi_2002` | `xsd:double` | true | 0..1 |
| `colhi_2003` | `xsd:double` | true | 0..1 |
| `colhi_2004` | `xsd:double` | true | 0..1 |
| `colhi_2005` | `xsd:double` | true | 0..1 |
| `colhi_2006` | `xsd:double` | true | 0..1 |
| `colhi_2007` | `xsd:double` | true | 0..1 |
| `colhi_2008` | `xsd:double` | true | 0..1 |
| `colhi_2009` | `xsd:double` | true | 0..1 |
| `colhi_2010` | `xsd:double` | true | 0..1 |
| `colhi_2011` | `xsd:double` | true | 0..1 |
| `colhi_2012` | `xsd:double` | true | 0..1 |
| `colhi_2013` | `xsd:double` | true | 0..1 |
| `colhi_2014` | `xsd:double` | true | 0..1 |
| `colhi_2015` | `xsd:double` | true | 0..1 |
| `colhi_2016` | `xsd:double` | true | 0..1 |
| `colhi_2017` | `xsd:double` | true | 0..1 |
| `colhi_2018` | `xsd:double` | true | 0..1 |
| `produ_1989` | `xsd:double` | true | 0..1 |
| `produ_1990` | `xsd:double` | true | 0..1 |
| `produ_1991` | `xsd:double` | true | 0..1 |
| `produ_1992` | `xsd:double` | true | 0..1 |
| `produ_1993` | `xsd:double` | true | 0..1 |
| `produ_1994` | `xsd:double` | true | 0..1 |
| `produ_1995` | `xsd:double` | true | 0..1 |
| `produ_1996` | `xsd:double` | true | 0..1 |
| `produ_1997` | `xsd:double` | true | 0..1 |
| `produ_1998` | `xsd:double` | true | 0..1 |
| `produ_1999` | `xsd:double` | true | 0..1 |
| `produ_2000` | `xsd:double` | true | 0..1 |
| `produ_2001` | `xsd:double` | true | 0..1 |
| `produ_2002` | `xsd:double` | true | 0..1 |
| `produ_2003` | `xsd:double` | true | 0..1 |
| `produ_2004` | `xsd:double` | true | 0..1 |
| `produ_2005` | `xsd:double` | true | 0..1 |
| `produ_2006` | `xsd:double` | true | 0..1 |
| `produ_2007` | `xsd:double` | true | 0..1 |
| `produ_2008` | `xsd:double` | true | 0..1 |
| `produ_2009` | `xsd:double` | true | 0..1 |
| `produ_2010` | `xsd:double` | true | 0..1 |
| `produ_2011` | `xsd:double` | true | 0..1 |
| `produ_2012` | `xsd:double` | true | 0..1 |
| `produ_2013` | `xsd:double` | true | 0..1 |
| `produ_2014` | `xsd:double` | true | 0..1 |
| `produ_2015` | `xsd:double` | true | 0..1 |
| `produ_2016` | `xsd:double` | true | 0..1 |
| `produ_2017` | `xsd:double` | true | 0..1 |
| `produ_2018` | `xsd:double` | true | 0..1 |
| `rendi_1989` | `xsd:double` | true | 0..1 |
| `rendi_1990` | `xsd:double` | true | 0..1 |
| `rendi_1991` | `xsd:double` | true | 0..1 |
| `rendi_1992` | `xsd:double` | true | 0..1 |
| `rendi_1993` | `xsd:double` | true | 0..1 |
| `rendi_1994` | `xsd:double` | true | 0..1 |
| `rendi_1995` | `xsd:double` | true | 0..1 |
| `rendi_1996` | `xsd:double` | true | 0..1 |
| `rendi_1997` | `xsd:double` | true | 0..1 |
| `rendi_1998` | `xsd:double` | true | 0..1 |
| `rendi_1999` | `xsd:double` | true | 0..1 |
| `rendi_2000` | `xsd:double` | true | 0..1 |
| `rendi_2001` | `xsd:double` | true | 0..1 |
| `rendi_2002` | `xsd:double` | true | 0..1 |
| `rendi_2003` | `xsd:double` | true | 0..1 |
| `rendi_2004` | `xsd:double` | true | 0..1 |
| `rendi_2005` | `xsd:double` | true | 0..1 |
| `rendi_2006` | `xsd:double` | true | 0..1 |
| `rendi_2007` | `xsd:double` | true | 0..1 |
| `rendi_2008` | `xsd:double` | true | 0..1 |
| `rendi_2009` | `xsd:double` | true | 0..1 |
| `rendi_2010` | `xsd:double` | true | 0..1 |
| `rendi_2011` | `xsd:double` | true | 0..1 |
| `rendi_2012` | `xsd:double` | true | 0..1 |
| `rendi_2013` | `xsd:double` | true | 0..1 |
| `rendi_2014` | `xsd:double` | true | 0..1 |
| `rendi_2015` | `xsd:double` | true | 0..1 |
| `rendi_2016` | `xsd:double` | true | 0..1 |
| `rendi_2017` | `xsd:double` | true | 0..1 |
| `rendi_2018` | `xsd:double` | true | 0..1 |

### `estatistica:lavoura_permanente_banana_1989a2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `nume_cid` | `xsd:string` | true | 0..1 |
| `pgai` | `xsd:string` | true | 0..1 |
| `tipo_cidd` | `xsd:string` | true | 0..1 |
| `regiao_num` | `xsd:string` | true | 0..1 |
| `territ_cid` | `xsd:string` | true | 0..1 |
| `utr` | `xsd:string` | true | 0..1 |
| `criacao` | `xsd:string` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `pop_1996` | `xsd:double` | true | 0..1 |
| `pop_2000` | `xsd:double` | true | 0..1 |
| `pop_2007` | `xsd:double` | true | 0..1 |
| `pop_2008` | `xsd:double` | true | 0..1 |
| `pop_2009` | `xsd:double` | true | 0..1 |
| `assoc_mun` | `xsd:string` | true | 0..1 |
| `reg_pm` | `xsd:string` | true | 0..1 |
| `art_pm` | `xsd:string` | true | 0..1 |
| `region_ibg` | `xsd:string` | true | 0..1 |
| `cod_region` | `xsd:double` | true | 0..1 |
| `pop_2010` | `xsd:double` | true | 0..1 |
| `ppa_2012_2` | `xsd:string` | true | 0..1 |
| `number` | `xsd:double` | true | 0..1 |
| `regionaliz` | `xsd:string` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `reg_tur` | `xsd:string` | true | 0..1 |
| `nova_regio` | `xsd:string` | true | 0..1 |
| `nova_reg_o` | `xsd:string` | true | 0..1 |
| `cultura` | `xsd:string` | true | 0..1 |
| `area_1989` | `xsd:double` | true | 0..1 |
| `area_1990` | `xsd:double` | true | 0..1 |
| `area_1991` | `xsd:double` | true | 0..1 |
| `area_1992` | `xsd:double` | true | 0..1 |
| `area_1993` | `xsd:double` | true | 0..1 |
| `area_1994` | `xsd:double` | true | 0..1 |
| `area_1995` | `xsd:double` | true | 0..1 |
| `area_1996` | `xsd:double` | true | 0..1 |
| `area_1997` | `xsd:double` | true | 0..1 |
| `area_1998` | `xsd:double` | true | 0..1 |
| `area_1999` | `xsd:double` | true | 0..1 |
| `area_2000` | `xsd:double` | true | 0..1 |
| `area_2001` | `xsd:double` | true | 0..1 |
| `area_2002` | `xsd:double` | true | 0..1 |
| `area_2003` | `xsd:double` | true | 0..1 |
| `area_2004` | `xsd:double` | true | 0..1 |
| `area_2005` | `xsd:double` | true | 0..1 |
| `area_2006` | `xsd:double` | true | 0..1 |
| `area_2007` | `xsd:double` | true | 0..1 |
| `area_2008` | `xsd:double` | true | 0..1 |
| `area_2009` | `xsd:double` | true | 0..1 |
| `area_2010` | `xsd:double` | true | 0..1 |
| `area_2011` | `xsd:double` | true | 0..1 |
| `area_2012` | `xsd:double` | true | 0..1 |
| `area_2013` | `xsd:double` | true | 0..1 |
| `area_2014` | `xsd:double` | true | 0..1 |
| `area_2015` | `xsd:double` | true | 0..1 |
| `area_2016` | `xsd:double` | true | 0..1 |
| `area_2017` | `xsd:double` | true | 0..1 |
| `area_2018` | `xsd:double` | true | 0..1 |
| `colhi_1989` | `xsd:double` | true | 0..1 |
| `colhi_1990` | `xsd:double` | true | 0..1 |
| `colhi_1991` | `xsd:double` | true | 0..1 |
| `colhi_1992` | `xsd:double` | true | 0..1 |
| `colhi_1993` | `xsd:double` | true | 0..1 |
| `colhi_1994` | `xsd:double` | true | 0..1 |
| `colhi_1995` | `xsd:double` | true | 0..1 |
| `colhi_1996` | `xsd:double` | true | 0..1 |
| `colhi_1997` | `xsd:double` | true | 0..1 |
| `colhi_1998` | `xsd:double` | true | 0..1 |
| `colhi_1999` | `xsd:double` | true | 0..1 |
| `colhi_2000` | `xsd:double` | true | 0..1 |
| `colhi_2001` | `xsd:double` | true | 0..1 |
| `colhi_2002` | `xsd:double` | true | 0..1 |
| `colhi_2003` | `xsd:double` | true | 0..1 |
| `colhi_2004` | `xsd:double` | true | 0..1 |
| `colhi_2005` | `xsd:double` | true | 0..1 |
| `colhi_2006` | `xsd:double` | true | 0..1 |
| `colhi_2007` | `xsd:double` | true | 0..1 |
| `colhi_2008` | `xsd:double` | true | 0..1 |
| `colhi_2009` | `xsd:double` | true | 0..1 |
| `colhi_2010` | `xsd:double` | true | 0..1 |
| `colhi_2011` | `xsd:double` | true | 0..1 |
| `colhi_2012` | `xsd:double` | true | 0..1 |
| `colhi_2013` | `xsd:double` | true | 0..1 |
| `colhi_2014` | `xsd:double` | true | 0..1 |
| `colhi_2015` | `xsd:double` | true | 0..1 |
| `colhi_2016` | `xsd:double` | true | 0..1 |
| `colhi_2017` | `xsd:double` | true | 0..1 |
| `colhi_2018` | `xsd:double` | true | 0..1 |
| `produ_1989` | `xsd:double` | true | 0..1 |
| `produ_1990` | `xsd:double` | true | 0..1 |
| `produ_1991` | `xsd:double` | true | 0..1 |
| `produ_1992` | `xsd:double` | true | 0..1 |
| `produ_1993` | `xsd:double` | true | 0..1 |
| `produ_1994` | `xsd:double` | true | 0..1 |
| `produ_1995` | `xsd:double` | true | 0..1 |
| `produ_1996` | `xsd:double` | true | 0..1 |
| `produ_1997` | `xsd:double` | true | 0..1 |
| `produ_1998` | `xsd:double` | true | 0..1 |
| `produ_1999` | `xsd:double` | true | 0..1 |
| `produ_2000` | `xsd:double` | true | 0..1 |
| `produ_2001` | `xsd:double` | true | 0..1 |
| `produ_2002` | `xsd:double` | true | 0..1 |
| `produ_2003` | `xsd:double` | true | 0..1 |
| `produ_2004` | `xsd:double` | true | 0..1 |
| `produ_2005` | `xsd:double` | true | 0..1 |
| `produ_2006` | `xsd:double` | true | 0..1 |
| `produ_2007` | `xsd:double` | true | 0..1 |
| `produ_2008` | `xsd:double` | true | 0..1 |
| `produ_2009` | `xsd:double` | true | 0..1 |
| `produ_2010` | `xsd:double` | true | 0..1 |
| `produ_2011` | `xsd:double` | true | 0..1 |
| `produ_2012` | `xsd:double` | true | 0..1 |
| `produ_2013` | `xsd:double` | true | 0..1 |
| `produ_2014` | `xsd:double` | true | 0..1 |
| `produ_2015` | `xsd:double` | true | 0..1 |
| `produ_2016` | `xsd:double` | true | 0..1 |
| `produ_2017` | `xsd:double` | true | 0..1 |
| `produ_2018` | `xsd:double` | true | 0..1 |
| `rendi_1989` | `xsd:double` | true | 0..1 |
| `rendi_1990` | `xsd:double` | true | 0..1 |
| `rendi_1991` | `xsd:double` | true | 0..1 |
| `rendi_1992` | `xsd:double` | true | 0..1 |
| `rendi_1993` | `xsd:double` | true | 0..1 |
| `rendi_1994` | `xsd:double` | true | 0..1 |
| `rendi_1995` | `xsd:double` | true | 0..1 |
| `rendi_1996` | `xsd:double` | true | 0..1 |
| `rendi_1997` | `xsd:double` | true | 0..1 |
| `rendi_1998` | `xsd:double` | true | 0..1 |
| `rendi_1999` | `xsd:double` | true | 0..1 |
| `rendi_2000` | `xsd:double` | true | 0..1 |
| `rendi_2001` | `xsd:double` | true | 0..1 |
| `rendi_2002` | `xsd:double` | true | 0..1 |
| `rendi_2003` | `xsd:double` | true | 0..1 |
| `rendi_2004` | `xsd:double` | true | 0..1 |
| `rendi_2005` | `xsd:double` | true | 0..1 |
| `rendi_2006` | `xsd:double` | true | 0..1 |
| `rendi_2007` | `xsd:double` | true | 0..1 |
| `rendi_2008` | `xsd:double` | true | 0..1 |
| `rendi_2009` | `xsd:double` | true | 0..1 |
| `rendi_2010` | `xsd:double` | true | 0..1 |
| `rendi_2011` | `xsd:double` | true | 0..1 |
| `rendi_2012` | `xsd:double` | true | 0..1 |
| `rendi_2013` | `xsd:double` | true | 0..1 |
| `rendi_2014` | `xsd:double` | true | 0..1 |
| `rendi_2015` | `xsd:double` | true | 0..1 |
| `rendi_2016` | `xsd:double` | true | 0..1 |
| `rendi_2017` | `xsd:double` | true | 0..1 |
| `rendi_2018` | `xsd:double` | true | 0..1 |

### `estatistica:lavoura_permanente_coco_da_baia_1996a2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `nume_cid` | `xsd:string` | true | 0..1 |
| `pgai` | `xsd:string` | true | 0..1 |
| `tipo_cidd` | `xsd:string` | true | 0..1 |
| `regiao_num` | `xsd:string` | true | 0..1 |
| `territ_cid` | `xsd:string` | true | 0..1 |
| `utr` | `xsd:string` | true | 0..1 |
| `criacao` | `xsd:string` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `pop_1996` | `xsd:double` | true | 0..1 |
| `pop_2000` | `xsd:double` | true | 0..1 |
| `pop_2007` | `xsd:double` | true | 0..1 |
| `pop_2008` | `xsd:double` | true | 0..1 |
| `pop_2009` | `xsd:double` | true | 0..1 |
| `assoc_mun` | `xsd:string` | true | 0..1 |
| `reg_pm` | `xsd:string` | true | 0..1 |
| `art_pm` | `xsd:string` | true | 0..1 |
| `region_ibg` | `xsd:string` | true | 0..1 |
| `cod_region` | `xsd:double` | true | 0..1 |
| `pop_2010` | `xsd:double` | true | 0..1 |
| `ppa_2012_2` | `xsd:string` | true | 0..1 |
| `number` | `xsd:double` | true | 0..1 |
| `regionaliz` | `xsd:string` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `reg_tur` | `xsd:string` | true | 0..1 |
| `nova_regio` | `xsd:string` | true | 0..1 |
| `nova_reg_o` | `xsd:string` | true | 0..1 |
| `cultura` | `xsd:string` | true | 0..1 |
| `plant_1996` | `xsd:double` | true | 0..1 |
| `plant_1997` | `xsd:double` | true | 0..1 |
| `plant_1998` | `xsd:double` | true | 0..1 |
| `plant_1999` | `xsd:double` | true | 0..1 |
| `plant_2000` | `xsd:double` | true | 0..1 |
| `plant_2001` | `xsd:double` | true | 0..1 |
| `plant_2002` | `xsd:double` | true | 0..1 |
| `plant_2003` | `xsd:double` | true | 0..1 |
| `plant_2004` | `xsd:double` | true | 0..1 |
| `plant_2005` | `xsd:double` | true | 0..1 |
| `plant_2006` | `xsd:double` | true | 0..1 |
| `plant_2007` | `xsd:double` | true | 0..1 |
| `plant_2008` | `xsd:double` | true | 0..1 |
| `plant_2009` | `xsd:double` | true | 0..1 |
| `plant_2010` | `xsd:double` | true | 0..1 |
| `plant_2011` | `xsd:double` | true | 0..1 |
| `plant_2012` | `xsd:double` | true | 0..1 |
| `plant_2013` | `xsd:double` | true | 0..1 |
| `plant_2014` | `xsd:double` | true | 0..1 |
| `plant_2015` | `xsd:double` | true | 0..1 |
| `plant_2016` | `xsd:double` | true | 0..1 |
| `plant_2017` | `xsd:double` | true | 0..1 |
| `plant_2018` | `xsd:double` | true | 0..1 |
| `colh_1996` | `xsd:double` | true | 0..1 |
| `colh_1997` | `xsd:double` | true | 0..1 |
| `colh_1998` | `xsd:double` | true | 0..1 |
| `colh_1999` | `xsd:double` | true | 0..1 |
| `colh_2000` | `xsd:double` | true | 0..1 |
| `colh_2001` | `xsd:double` | true | 0..1 |
| `colh_2002` | `xsd:double` | true | 0..1 |
| `colh_2003` | `xsd:double` | true | 0..1 |
| `colh_2004` | `xsd:double` | true | 0..1 |
| `colh_2005` | `xsd:double` | true | 0..1 |
| `colh_2006` | `xsd:double` | true | 0..1 |
| `colh_2007` | `xsd:double` | true | 0..1 |
| `colh_2008` | `xsd:double` | true | 0..1 |
| `colh_2009` | `xsd:double` | true | 0..1 |
| `colh_2010` | `xsd:double` | true | 0..1 |
| `colh_2011` | `xsd:double` | true | 0..1 |
| `colh_2012` | `xsd:double` | true | 0..1 |
| `colh_2013` | `xsd:double` | true | 0..1 |
| `colh_2014` | `xsd:double` | true | 0..1 |
| `colh_2015` | `xsd:double` | true | 0..1 |
| `colh_2016` | `xsd:double` | true | 0..1 |
| `colh_2017` | `xsd:double` | true | 0..1 |
| `colh_2018` | `xsd:double` | true | 0..1 |
| `prod_1996` | `xsd:double` | true | 0..1 |
| `prod_1997` | `xsd:double` | true | 0..1 |
| `prod_1998` | `xsd:double` | true | 0..1 |
| `prod_1999` | `xsd:double` | true | 0..1 |
| `prod_2000` | `xsd:double` | true | 0..1 |
| `prod_2001` | `xsd:double` | true | 0..1 |
| `prod_2002` | `xsd:double` | true | 0..1 |
| `prod_2003` | `xsd:double` | true | 0..1 |
| `prod_2004` | `xsd:double` | true | 0..1 |
| `prod_2005` | `xsd:double` | true | 0..1 |
| `prod_2006` | `xsd:double` | true | 0..1 |
| `prod_2007` | `xsd:double` | true | 0..1 |
| `prod_2008` | `xsd:double` | true | 0..1 |
| `prod_2009` | `xsd:double` | true | 0..1 |
| `prod_2010` | `xsd:double` | true | 0..1 |
| `prod_2011` | `xsd:double` | true | 0..1 |
| `prod_2012` | `xsd:double` | true | 0..1 |
| `prod_2013` | `xsd:double` | true | 0..1 |
| `prod_2014` | `xsd:double` | true | 0..1 |
| `prod_2015` | `xsd:double` | true | 0..1 |
| `prod_2016` | `xsd:double` | true | 0..1 |
| `prod_2017` | `xsd:double` | true | 0..1 |
| `prod_2018` | `xsd:double` | true | 0..1 |
| `rend_1996` | `xsd:double` | true | 0..1 |
| `rend_1997` | `xsd:double` | true | 0..1 |
| `rend_1998` | `xsd:double` | true | 0..1 |
| `rend_1999` | `xsd:double` | true | 0..1 |
| `rend_2000` | `xsd:double` | true | 0..1 |
| `rend_2001` | `xsd:double` | true | 0..1 |
| `rend_2002` | `xsd:double` | true | 0..1 |
| `rend_2003` | `xsd:double` | true | 0..1 |
| `rend_2004` | `xsd:double` | true | 0..1 |
| `rend_2005` | `xsd:double` | true | 0..1 |
| `rend_2006` | `xsd:double` | true | 0..1 |
| `rend_2007` | `xsd:double` | true | 0..1 |
| `rend_2008` | `xsd:double` | true | 0..1 |
| `rend_2009` | `xsd:double` | true | 0..1 |
| `rend_2010` | `xsd:double` | true | 0..1 |
| `rend_2011` | `xsd:double` | true | 0..1 |
| `rend_2012` | `xsd:double` | true | 0..1 |
| `rend_2013` | `xsd:double` | true | 0..1 |
| `rend_2014` | `xsd:double` | true | 0..1 |
| `rend_2015` | `xsd:double` | true | 0..1 |
| `rend_2016` | `xsd:double` | true | 0..1 |
| `rend_2017` | `xsd:double` | true | 0..1 |
| `rend_2018` | `xsd:double` | true | 0..1 |
| `valor_1996` | `xsd:double` | true | 0..1 |
| `valor_1997` | `xsd:double` | true | 0..1 |
| `valor_1998` | `xsd:double` | true | 0..1 |
| `valor_1999` | `xsd:double` | true | 0..1 |
| `valor_2000` | `xsd:double` | true | 0..1 |
| `valor_2001` | `xsd:double` | true | 0..1 |
| `valor_2002` | `xsd:double` | true | 0..1 |
| `valor_2003` | `xsd:double` | true | 0..1 |
| `valor_2004` | `xsd:double` | true | 0..1 |
| `valor_2005` | `xsd:double` | true | 0..1 |
| `valor_2006` | `xsd:double` | true | 0..1 |
| `valor_2007` | `xsd:double` | true | 0..1 |
| `valor_2008` | `xsd:double` | true | 0..1 |
| `valor_2009` | `xsd:double` | true | 0..1 |
| `valor_2010` | `xsd:double` | true | 0..1 |
| `valor_2011` | `xsd:double` | true | 0..1 |
| `valor_2012` | `xsd:double` | true | 0..1 |
| `valor_2013` | `xsd:double` | true | 0..1 |
| `valor_2014` | `xsd:double` | true | 0..1 |
| `valor_2015` | `xsd:double` | true | 0..1 |
| `valor_2016` | `xsd:double` | true | 0..1 |
| `valor_2017` | `xsd:double` | true | 0..1 |
| `valor_2018` | `xsd:double` | true | 0..1 |

### `estatistica:lavoura_permanente_laranja_1989a2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `cultura` | `xsd:string` | true | 0..1 |
| `area_1989` | `xsd:double` | true | 0..1 |
| `area_1990` | `xsd:double` | true | 0..1 |
| `area_1991` | `xsd:double` | true | 0..1 |
| `area_1992` | `xsd:double` | true | 0..1 |
| `area_1993` | `xsd:double` | true | 0..1 |
| `area_1994` | `xsd:double` | true | 0..1 |
| `area_1995` | `xsd:double` | true | 0..1 |
| `area_1996` | `xsd:double` | true | 0..1 |
| `area_1997` | `xsd:double` | true | 0..1 |
| `area_1998` | `xsd:double` | true | 0..1 |
| `area_1999` | `xsd:double` | true | 0..1 |
| `area_2000` | `xsd:double` | true | 0..1 |
| `area_2001` | `xsd:double` | true | 0..1 |
| `area_2002` | `xsd:double` | true | 0..1 |
| `area_2003` | `xsd:double` | true | 0..1 |
| `area_2004` | `xsd:double` | true | 0..1 |
| `area_2005` | `xsd:double` | true | 0..1 |
| `area_2006` | `xsd:double` | true | 0..1 |
| `area_2007` | `xsd:double` | true | 0..1 |
| `area_2008` | `xsd:double` | true | 0..1 |
| `area_2009` | `xsd:double` | true | 0..1 |
| `area_2010` | `xsd:double` | true | 0..1 |
| `area_2011` | `xsd:double` | true | 0..1 |
| `area_2012` | `xsd:double` | true | 0..1 |
| `area_2013` | `xsd:double` | true | 0..1 |
| `area_2014` | `xsd:double` | true | 0..1 |
| `area_2015` | `xsd:double` | true | 0..1 |
| `area_2016` | `xsd:double` | true | 0..1 |
| `area_2017` | `xsd:double` | true | 0..1 |
| `area_2018` | `xsd:double` | true | 0..1 |
| `colhi_1989` | `xsd:double` | true | 0..1 |
| `colhi_1990` | `xsd:double` | true | 0..1 |
| `colhi_1991` | `xsd:double` | true | 0..1 |
| `colhi_1992` | `xsd:double` | true | 0..1 |
| `colhi_1993` | `xsd:double` | true | 0..1 |
| `colhi_1994` | `xsd:double` | true | 0..1 |
| `colhi_1995` | `xsd:double` | true | 0..1 |
| `colhi_1996` | `xsd:double` | true | 0..1 |
| `colhi_1997` | `xsd:double` | true | 0..1 |
| `colhi_1998` | `xsd:double` | true | 0..1 |
| `colhi_1999` | `xsd:double` | true | 0..1 |
| `colhi_2000` | `xsd:double` | true | 0..1 |
| `colhi_2001` | `xsd:double` | true | 0..1 |
| `colhi_2002` | `xsd:double` | true | 0..1 |
| `colhi_2003` | `xsd:double` | true | 0..1 |
| `colhi_2004` | `xsd:double` | true | 0..1 |
| `colhi_2005` | `xsd:double` | true | 0..1 |
| `colhi_2006` | `xsd:double` | true | 0..1 |
| `colhi_2007` | `xsd:double` | true | 0..1 |
| `colhi_2008` | `xsd:double` | true | 0..1 |
| `colhi_2009` | `xsd:double` | true | 0..1 |
| `colhi_2010` | `xsd:double` | true | 0..1 |
| `colhi_2011` | `xsd:double` | true | 0..1 |
| `colhi_2012` | `xsd:double` | true | 0..1 |
| `colhi_2013` | `xsd:double` | true | 0..1 |
| `colhi_2014` | `xsd:double` | true | 0..1 |
| `colhi_2015` | `xsd:double` | true | 0..1 |
| `colhi_2016` | `xsd:double` | true | 0..1 |
| `colhi_2017` | `xsd:double` | true | 0..1 |
| `colhi_2018` | `xsd:double` | true | 0..1 |
| `prod_1989` | `xsd:double` | true | 0..1 |
| `prod_1990` | `xsd:double` | true | 0..1 |
| `prod_1991` | `xsd:double` | true | 0..1 |
| `prod_1992` | `xsd:double` | true | 0..1 |
| `prod_1993` | `xsd:double` | true | 0..1 |
| `prod_1994` | `xsd:double` | true | 0..1 |
| `prod_1995` | `xsd:double` | true | 0..1 |
| `prod_1996` | `xsd:double` | true | 0..1 |
| `prod_1997` | `xsd:double` | true | 0..1 |
| `prod_1998` | `xsd:double` | true | 0..1 |
| `prod_1999` | `xsd:double` | true | 0..1 |
| `prod_2000` | `xsd:double` | true | 0..1 |
| `prod_2001` | `xsd:double` | true | 0..1 |
| `prod_2002` | `xsd:double` | true | 0..1 |
| `prod_2003` | `xsd:double` | true | 0..1 |
| `prod_2004` | `xsd:double` | true | 0..1 |
| `prod_2005` | `xsd:double` | true | 0..1 |
| `prod_2006` | `xsd:double` | true | 0..1 |
| `prod_2007` | `xsd:double` | true | 0..1 |
| `prod_2008` | `xsd:double` | true | 0..1 |
| `prod_2009` | `xsd:double` | true | 0..1 |
| `prod_2010` | `xsd:double` | true | 0..1 |
| `prod_2011` | `xsd:double` | true | 0..1 |
| `prod_2012` | `xsd:double` | true | 0..1 |
| `prod_2013` | `xsd:double` | true | 0..1 |
| `prod_2014` | `xsd:double` | true | 0..1 |
| `prod_2015` | `xsd:double` | true | 0..1 |
| `prod_2016` | `xsd:double` | true | 0..1 |
| `prod_2017` | `xsd:double` | true | 0..1 |
| `prod_2018` | `xsd:double` | true | 0..1 |
| `rend_1989` | `xsd:double` | true | 0..1 |
| `rend_1990` | `xsd:double` | true | 0..1 |
| `rend_1991` | `xsd:double` | true | 0..1 |
| `rend_1992` | `xsd:double` | true | 0..1 |
| `rend_1993` | `xsd:double` | true | 0..1 |
| `rend_1994` | `xsd:double` | true | 0..1 |
| `rend_1995` | `xsd:double` | true | 0..1 |
| `rend_1996` | `xsd:double` | true | 0..1 |
| `rend_1997` | `xsd:double` | true | 0..1 |
| `rend_1998` | `xsd:double` | true | 0..1 |
| `rend_1999` | `xsd:double` | true | 0..1 |
| `rend_2000` | `xsd:double` | true | 0..1 |
| `rend_2001` | `xsd:double` | true | 0..1 |
| `rend_2002` | `xsd:double` | true | 0..1 |
| `rend_2003` | `xsd:double` | true | 0..1 |
| `rend_2004` | `xsd:double` | true | 0..1 |
| `rend_2005` | `xsd:double` | true | 0..1 |
| `rend_2006` | `xsd:double` | true | 0..1 |
| `rend_2007` | `xsd:double` | true | 0..1 |
| `rend_2008` | `xsd:double` | true | 0..1 |
| `rend_2009` | `xsd:double` | true | 0..1 |
| `rend_2010` | `xsd:double` | true | 0..1 |
| `rend_2011` | `xsd:double` | true | 0..1 |
| `rend_2012` | `xsd:double` | true | 0..1 |
| `rend_2013` | `xsd:double` | true | 0..1 |
| `rend_2014` | `xsd:double` | true | 0..1 |
| `rend_2015` | `xsd:double` | true | 0..1 |
| `rend_2016` | `xsd:double` | true | 0..1 |
| `rend_2017` | `xsd:double` | true | 0..1 |
| `rend_2018` | `xsd:double` | true | 0..1 |
| `valor_1989` | `xsd:double` | true | 0..1 |
| `valor_1990` | `xsd:double` | true | 0..1 |
| `valor_1991` | `xsd:double` | true | 0..1 |
| `valor_1992` | `xsd:double` | true | 0..1 |
| `valor_1993` | `xsd:double` | true | 0..1 |
| `valor_1994` | `xsd:double` | true | 0..1 |
| `valor_1995` | `xsd:double` | true | 0..1 |
| `valor_1996` | `xsd:double` | true | 0..1 |
| `valor_1997` | `xsd:double` | true | 0..1 |
| `valor_1998` | `xsd:double` | true | 0..1 |
| `valor_1999` | `xsd:double` | true | 0..1 |
| `valor_2000` | `xsd:double` | true | 0..1 |
| `valor_2001` | `xsd:double` | true | 0..1 |
| `valor_2002` | `xsd:double` | true | 0..1 |
| `valor_2003` | `xsd:double` | true | 0..1 |
| `valor_2004` | `xsd:double` | true | 0..1 |
| `valor_2005` | `xsd:double` | true | 0..1 |
| `valor_2006` | `xsd:double` | true | 0..1 |
| `valor_2007` | `xsd:double` | true | 0..1 |
| `valor_2008` | `xsd:double` | true | 0..1 |
| `valor_2009` | `xsd:double` | true | 0..1 |
| `valor_2010` | `xsd:double` | true | 0..1 |
| `valor_2011` | `xsd:double` | true | 0..1 |
| `valor_2012` | `xsd:double` | true | 0..1 |
| `valor_2013` | `xsd:double` | true | 0..1 |
| `valor_2014` | `xsd:double` | true | 0..1 |
| `valor_2015` | `xsd:double` | true | 0..1 |
| `valor_2016` | `xsd:double` | true | 0..1 |
| `valor_2017` | `xsd:double` | true | 0..1 |
| `valor_2018` | `xsd:double` | true | 0..1 |

### `estatistica:lavoura_permanente_manga_1994a2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `cultura` | `xsd:string` | true | 0..1 |
| `area_1994` | `xsd:double` | true | 0..1 |
| `area_1995` | `xsd:double` | true | 0..1 |
| `area_1996` | `xsd:double` | true | 0..1 |
| `area_1997` | `xsd:double` | true | 0..1 |
| `area_1998` | `xsd:double` | true | 0..1 |
| `area_1999` | `xsd:double` | true | 0..1 |
| `area_2000` | `xsd:double` | true | 0..1 |
| `area_2001` | `xsd:double` | true | 0..1 |
| `area_2002` | `xsd:double` | true | 0..1 |
| `area_2003` | `xsd:double` | true | 0..1 |
| `area_2004` | `xsd:double` | true | 0..1 |
| `area_2005` | `xsd:double` | true | 0..1 |
| `area_2006` | `xsd:double` | true | 0..1 |
| `area_2007` | `xsd:double` | true | 0..1 |
| `area_2008` | `xsd:double` | true | 0..1 |
| `area_2009` | `xsd:double` | true | 0..1 |
| `area_2010` | `xsd:double` | true | 0..1 |
| `area_2011` | `xsd:double` | true | 0..1 |
| `area_2012` | `xsd:double` | true | 0..1 |
| `area_2013` | `xsd:double` | true | 0..1 |
| `area_2014` | `xsd:double` | true | 0..1 |
| `area_2015` | `xsd:double` | true | 0..1 |
| `area_2016` | `xsd:double` | true | 0..1 |
| `area_2017` | `xsd:double` | true | 0..1 |
| `area_2018` | `xsd:double` | true | 0..1 |
| `colhi_1994` | `xsd:double` | true | 0..1 |
| `colhi_1995` | `xsd:double` | true | 0..1 |
| `colhi_1996` | `xsd:double` | true | 0..1 |
| `colhi_1997` | `xsd:double` | true | 0..1 |
| `colhi_1998` | `xsd:double` | true | 0..1 |
| `colhi_1999` | `xsd:double` | true | 0..1 |
| `colhi_2000` | `xsd:double` | true | 0..1 |
| `colhi_2001` | `xsd:double` | true | 0..1 |
| `colhi_2002` | `xsd:double` | true | 0..1 |
| `colhi_2003` | `xsd:double` | true | 0..1 |
| `colhi_2004` | `xsd:double` | true | 0..1 |
| `colhi_2005` | `xsd:double` | true | 0..1 |
| `colhi_2006` | `xsd:double` | true | 0..1 |
| `colhi_2007` | `xsd:double` | true | 0..1 |
| `colhi_2008` | `xsd:double` | true | 0..1 |
| `colhi_2009` | `xsd:double` | true | 0..1 |
| `colhi_2010` | `xsd:double` | true | 0..1 |
| `colhi_2011` | `xsd:double` | true | 0..1 |
| `colhi_2012` | `xsd:double` | true | 0..1 |
| `colhi_2013` | `xsd:double` | true | 0..1 |
| `colhi_2014` | `xsd:double` | true | 0..1 |
| `colhi_2015` | `xsd:double` | true | 0..1 |
| `colhi_2016` | `xsd:double` | true | 0..1 |
| `colhi_2017` | `xsd:double` | true | 0..1 |
| `colhi_2018` | `xsd:double` | true | 0..1 |
| `prod_1994` | `xsd:double` | true | 0..1 |
| `prod_1995` | `xsd:double` | true | 0..1 |
| `prod_1996` | `xsd:double` | true | 0..1 |
| `prod_1997` | `xsd:double` | true | 0..1 |
| `prod_1998` | `xsd:double` | true | 0..1 |
| `prod_1999` | `xsd:double` | true | 0..1 |
| `prod_2000` | `xsd:double` | true | 0..1 |
| `prod_2001` | `xsd:double` | true | 0..1 |
| `prod_2002` | `xsd:double` | true | 0..1 |
| `prod_2003` | `xsd:double` | true | 0..1 |
| `prod_2004` | `xsd:double` | true | 0..1 |
| `prod_2005` | `xsd:double` | true | 0..1 |
| `prod_2006` | `xsd:double` | true | 0..1 |
| `prod_2007` | `xsd:double` | true | 0..1 |
| `prod_2008` | `xsd:double` | true | 0..1 |
| `prod_2009` | `xsd:double` | true | 0..1 |
| `prod_2010` | `xsd:double` | true | 0..1 |
| `prod_2011` | `xsd:double` | true | 0..1 |
| `prod_2012` | `xsd:double` | true | 0..1 |
| `prod_2013` | `xsd:double` | true | 0..1 |
| `prod_2014` | `xsd:double` | true | 0..1 |
| `prod_2015` | `xsd:double` | true | 0..1 |
| `prod_2016` | `xsd:double` | true | 0..1 |
| `prod_2017` | `xsd:double` | true | 0..1 |
| `prod_2018` | `xsd:double` | true | 0..1 |
| `rend_1994` | `xsd:double` | true | 0..1 |
| `rend_1995` | `xsd:double` | true | 0..1 |
| `rend_1996` | `xsd:double` | true | 0..1 |
| `rend_1997` | `xsd:double` | true | 0..1 |
| `rend_1998` | `xsd:double` | true | 0..1 |
| `rend_1999` | `xsd:double` | true | 0..1 |
| `rend_2000` | `xsd:double` | true | 0..1 |
| `rend_2001` | `xsd:double` | true | 0..1 |
| `rend_2002` | `xsd:double` | true | 0..1 |
| `rend_2003` | `xsd:double` | true | 0..1 |
| `rend_2004` | `xsd:double` | true | 0..1 |
| `rend_2005` | `xsd:double` | true | 0..1 |
| `rend_2006` | `xsd:double` | true | 0..1 |
| `rend_2007` | `xsd:double` | true | 0..1 |
| `rend_2008` | `xsd:double` | true | 0..1 |
| `rend_2009` | `xsd:double` | true | 0..1 |
| `rend_2010` | `xsd:double` | true | 0..1 |
| `rend_2011` | `xsd:double` | true | 0..1 |
| `rend_2012` | `xsd:double` | true | 0..1 |
| `rend_2013` | `xsd:double` | true | 0..1 |
| `rend_2014` | `xsd:double` | true | 0..1 |
| `rend_2015` | `xsd:double` | true | 0..1 |
| `rend_2016` | `xsd:double` | true | 0..1 |
| `rend_2017` | `xsd:double` | true | 0..1 |
| `rend_2018` | `xsd:double` | true | 0..1 |
| `valor_1994` | `xsd:double` | true | 0..1 |
| `valor_1995` | `xsd:double` | true | 0..1 |
| `valor_1996` | `xsd:double` | true | 0..1 |
| `valor_1997` | `xsd:double` | true | 0..1 |
| `valor_1998` | `xsd:double` | true | 0..1 |
| `valor_1999` | `xsd:double` | true | 0..1 |
| `valor_2000` | `xsd:double` | true | 0..1 |
| `valor_2001` | `xsd:double` | true | 0..1 |
| `valor_2002` | `xsd:double` | true | 0..1 |
| `valor_2003` | `xsd:double` | true | 0..1 |
| `valor_2004` | `xsd:double` | true | 0..1 |
| `valor_2005` | `xsd:double` | true | 0..1 |
| `valor_2006` | `xsd:double` | true | 0..1 |
| `valor_2007` | `xsd:double` | true | 0..1 |
| `valor_2008` | `xsd:double` | true | 0..1 |
| `valor_2009` | `xsd:double` | true | 0..1 |
| `valor_2010` | `xsd:double` | true | 0..1 |
| `valor_2011` | `xsd:double` | true | 0..1 |
| `valor_2012` | `xsd:double` | true | 0..1 |
| `valor_2013` | `xsd:double` | true | 0..1 |
| `valor_2014` | `xsd:double` | true | 0..1 |
| `valor_2015` | `xsd:double` | true | 0..1 |
| `valor_2016` | `xsd:double` | true | 0..1 |
| `valor_2017` | `xsd:double` | true | 0..1 |
| `valor_2018` | `xsd:double` | true | 0..1 |

### `estatistica:lavoura_permanente_maracuja_1989a2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `cultura` | `xsd:string` | true | 0..1 |
| `area_1989` | `xsd:double` | true | 0..1 |
| `area_1990` | `xsd:double` | true | 0..1 |
| `area_1991` | `xsd:double` | true | 0..1 |
| `area_1992` | `xsd:double` | true | 0..1 |
| `area_1993` | `xsd:double` | true | 0..1 |
| `area_1994` | `xsd:double` | true | 0..1 |
| `area_1995` | `xsd:double` | true | 0..1 |
| `area_1996` | `xsd:double` | true | 0..1 |
| `area_1997` | `xsd:double` | true | 0..1 |
| `area_1998` | `xsd:double` | true | 0..1 |
| `area_1999` | `xsd:double` | true | 0..1 |
| `area_2000` | `xsd:double` | true | 0..1 |
| `area_2001` | `xsd:double` | true | 0..1 |
| `area_2002` | `xsd:double` | true | 0..1 |
| `area_2003` | `xsd:double` | true | 0..1 |
| `area_2004` | `xsd:double` | true | 0..1 |
| `area_2005` | `xsd:double` | true | 0..1 |
| `area_2006` | `xsd:double` | true | 0..1 |
| `area_2007` | `xsd:double` | true | 0..1 |
| `area_2008` | `xsd:double` | true | 0..1 |
| `area_2009` | `xsd:double` | true | 0..1 |
| `area_2010` | `xsd:double` | true | 0..1 |
| `area_2011` | `xsd:double` | true | 0..1 |
| `area_2012` | `xsd:double` | true | 0..1 |
| `area_2013` | `xsd:double` | true | 0..1 |
| `area_2014` | `xsd:double` | true | 0..1 |
| `area_2015` | `xsd:double` | true | 0..1 |
| `area_2016` | `xsd:double` | true | 0..1 |
| `area_2017` | `xsd:double` | true | 0..1 |
| `area_2018` | `xsd:double` | true | 0..1 |
| `colhi_1989` | `xsd:double` | true | 0..1 |
| `colhi_1990` | `xsd:double` | true | 0..1 |
| `colhi_1991` | `xsd:double` | true | 0..1 |
| `colhi_1992` | `xsd:double` | true | 0..1 |
| `colhi_1993` | `xsd:double` | true | 0..1 |
| `colhi_1994` | `xsd:double` | true | 0..1 |
| `colhi_1995` | `xsd:double` | true | 0..1 |
| `colhi_1996` | `xsd:double` | true | 0..1 |
| `colhi_1997` | `xsd:double` | true | 0..1 |
| `colhi_1998` | `xsd:double` | true | 0..1 |
| `colhi_1999` | `xsd:double` | true | 0..1 |
| `colhi_2000` | `xsd:double` | true | 0..1 |
| `colhi_2001` | `xsd:double` | true | 0..1 |
| `colhi_2002` | `xsd:double` | true | 0..1 |
| `colhi_2003` | `xsd:double` | true | 0..1 |
| `colhi_2004` | `xsd:double` | true | 0..1 |
| `colhi_2005` | `xsd:double` | true | 0..1 |
| `colhi_2006` | `xsd:double` | true | 0..1 |
| `colhi_2007` | `xsd:double` | true | 0..1 |
| `colhi_2008` | `xsd:double` | true | 0..1 |
| `colhi_2009` | `xsd:double` | true | 0..1 |
| `colhi_2010` | `xsd:double` | true | 0..1 |
| `colhi_2011` | `xsd:double` | true | 0..1 |
| `colhi_2012` | `xsd:double` | true | 0..1 |
| `colhi_2013` | `xsd:double` | true | 0..1 |
| `colhi_2014` | `xsd:double` | true | 0..1 |
| `colhi_2015` | `xsd:double` | true | 0..1 |
| `colhi_2016` | `xsd:double` | true | 0..1 |
| `colhi_2017` | `xsd:double` | true | 0..1 |
| `colhi_2018` | `xsd:double` | true | 0..1 |
| `produ_1989` | `xsd:double` | true | 0..1 |
| `produ_1990` | `xsd:double` | true | 0..1 |
| `produ_1991` | `xsd:double` | true | 0..1 |
| `produ_1992` | `xsd:double` | true | 0..1 |
| `produ_1993` | `xsd:double` | true | 0..1 |
| `produ_1994` | `xsd:double` | true | 0..1 |
| `produ_1995` | `xsd:double` | true | 0..1 |
| `produ_1996` | `xsd:double` | true | 0..1 |
| `produ_1997` | `xsd:double` | true | 0..1 |
| `produ_1998` | `xsd:double` | true | 0..1 |
| `produ_1999` | `xsd:double` | true | 0..1 |
| `produ_2000` | `xsd:double` | true | 0..1 |
| `produ_2001` | `xsd:double` | true | 0..1 |
| `produ_2002` | `xsd:double` | true | 0..1 |
| `produ_2003` | `xsd:double` | true | 0..1 |
| `produ_2004` | `xsd:double` | true | 0..1 |
| `produ_2005` | `xsd:double` | true | 0..1 |
| `produ_2006` | `xsd:double` | true | 0..1 |
| `produ_2007` | `xsd:double` | true | 0..1 |
| `produ_2008` | `xsd:double` | true | 0..1 |
| `produ_2009` | `xsd:double` | true | 0..1 |
| `produ_2010` | `xsd:double` | true | 0..1 |
| `produ_2011` | `xsd:double` | true | 0..1 |
| `produ_2012` | `xsd:double` | true | 0..1 |
| `produ_2013` | `xsd:double` | true | 0..1 |
| `produ_2014` | `xsd:double` | true | 0..1 |
| `produ_2015` | `xsd:double` | true | 0..1 |
| `produ_2016` | `xsd:double` | true | 0..1 |
| `produ_2017` | `xsd:double` | true | 0..1 |
| `produ_2018` | `xsd:double` | true | 0..1 |
| `rendi_1989` | `xsd:double` | true | 0..1 |
| `rendi_1990` | `xsd:double` | true | 0..1 |
| `rendi_1991` | `xsd:double` | true | 0..1 |
| `rendi_1992` | `xsd:double` | true | 0..1 |
| `rendi_1993` | `xsd:double` | true | 0..1 |
| `rendi_1994` | `xsd:double` | true | 0..1 |
| `rendi_1995` | `xsd:double` | true | 0..1 |
| `rendi_1996` | `xsd:double` | true | 0..1 |
| `rendi_1997` | `xsd:double` | true | 0..1 |
| `rendi_1998` | `xsd:double` | true | 0..1 |
| `rendi_1999` | `xsd:double` | true | 0..1 |
| `rendi_2000` | `xsd:double` | true | 0..1 |
| `rendi_2001` | `xsd:double` | true | 0..1 |
| `rendi_2002` | `xsd:double` | true | 0..1 |
| `rendi_2003` | `xsd:double` | true | 0..1 |
| `rendi_2004` | `xsd:double` | true | 0..1 |
| `rendi_2005` | `xsd:double` | true | 0..1 |
| `rendi_2006` | `xsd:double` | true | 0..1 |
| `rendi_2007` | `xsd:double` | true | 0..1 |
| `rendi_2008` | `xsd:double` | true | 0..1 |
| `rendi_2009` | `xsd:double` | true | 0..1 |
| `rendi_2010` | `xsd:double` | true | 0..1 |
| `rendi_2011` | `xsd:double` | true | 0..1 |
| `rendi_2012` | `xsd:double` | true | 0..1 |
| `rendi_2013` | `xsd:double` | true | 0..1 |
| `rendi_2014` | `xsd:double` | true | 0..1 |
| `rendi_2015` | `xsd:double` | true | 0..1 |
| `rendi_2016` | `xsd:double` | true | 0..1 |
| `rendi_2017` | `xsd:double` | true | 0..1 |
| `rendi_2018` | `xsd:double` | true | 0..1 |
| `valor_1989` | `xsd:double` | true | 0..1 |
| `valor_1990` | `xsd:double` | true | 0..1 |
| `valor_1991` | `xsd:double` | true | 0..1 |
| `valor_1992` | `xsd:double` | true | 0..1 |
| `valor_1993` | `xsd:double` | true | 0..1 |
| `valor_1994` | `xsd:double` | true | 0..1 |
| `valor_1995` | `xsd:double` | true | 0..1 |
| `valor_1996` | `xsd:double` | true | 0..1 |
| `valor_1997` | `xsd:double` | true | 0..1 |
| `valor_1998` | `xsd:double` | true | 0..1 |
| `valor_1999` | `xsd:double` | true | 0..1 |
| `valor_2000` | `xsd:double` | true | 0..1 |
| `valor_2001` | `xsd:double` | true | 0..1 |
| `valor_2002` | `xsd:double` | true | 0..1 |
| `valor_2003` | `xsd:double` | true | 0..1 |
| `valor_2004` | `xsd:double` | true | 0..1 |
| `valor_2005` | `xsd:double` | true | 0..1 |
| `valor_2006` | `xsd:double` | true | 0..1 |
| `valor_2007` | `xsd:double` | true | 0..1 |
| `valor_2008` | `xsd:double` | true | 0..1 |
| `valor_2009` | `xsd:double` | true | 0..1 |
| `valor_2010` | `xsd:double` | true | 0..1 |
| `valor_2011` | `xsd:double` | true | 0..1 |
| `valor_2012` | `xsd:double` | true | 0..1 |
| `valor_2013` | `xsd:double` | true | 0..1 |
| `valor_2014` | `xsd:double` | true | 0..1 |
| `valor_2015` | `xsd:double` | true | 0..1 |
| `valor_2016` | `xsd:double` | true | 0..1 |
| `valor_2017` | `xsd:double` | true | 0..1 |
| `valor_2018` | `xsd:double` | true | 0..1 |

### `estatistica:lavoura_temporaria_abacaxi_1989_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `nume_cid` | `xsd:string` | true | 0..1 |
| `pgai` | `xsd:string` | true | 0..1 |
| `tipo_cidd` | `xsd:string` | true | 0..1 |
| `regiao_num` | `xsd:string` | true | 0..1 |
| `territ_cid` | `xsd:string` | true | 0..1 |
| `utr` | `xsd:string` | true | 0..1 |
| `criacao` | `xsd:string` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `pop_1996` | `xsd:double` | true | 0..1 |
| `pop_2000` | `xsd:double` | true | 0..1 |
| `pop_2007` | `xsd:double` | true | 0..1 |
| `pop_2008` | `xsd:double` | true | 0..1 |
| `pop_2009` | `xsd:double` | true | 0..1 |
| `assoc_mun` | `xsd:string` | true | 0..1 |
| `reg_pm` | `xsd:string` | true | 0..1 |
| `art_pm` | `xsd:string` | true | 0..1 |
| `region_ibg` | `xsd:string` | true | 0..1 |
| `cod_region` | `xsd:double` | true | 0..1 |
| `pop_2010` | `xsd:double` | true | 0..1 |
| `ppa_2012_2` | `xsd:string` | true | 0..1 |
| `number` | `xsd:double` | true | 0..1 |
| `regionaliz` | `xsd:string` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `reg_tur` | `xsd:string` | true | 0..1 |
| `nova_regio` | `xsd:string` | true | 0..1 |
| `nova_reg_o` | `xsd:string` | true | 0..1 |
| `cultura` | `xsd:string` | true | 0..1 |
| `area_1989` | `xsd:double` | true | 0..1 |
| `area_1990` | `xsd:double` | true | 0..1 |
| `area_1991` | `xsd:double` | true | 0..1 |
| `area_1992` | `xsd:double` | true | 0..1 |
| `area_1993` | `xsd:double` | true | 0..1 |
| `area_1994` | `xsd:double` | true | 0..1 |
| `area_1995` | `xsd:double` | true | 0..1 |
| `area_1996` | `xsd:double` | true | 0..1 |
| `area_1997` | `xsd:double` | true | 0..1 |
| `area_1998` | `xsd:double` | true | 0..1 |
| `area_1999` | `xsd:double` | true | 0..1 |
| `area_2000` | `xsd:double` | true | 0..1 |
| `area_2001` | `xsd:double` | true | 0..1 |
| `area_2002` | `xsd:double` | true | 0..1 |
| `area_2003` | `xsd:double` | true | 0..1 |
| `area_2004` | `xsd:double` | true | 0..1 |
| `area_2005` | `xsd:double` | true | 0..1 |
| `area_2006` | `xsd:double` | true | 0..1 |
| `area_2007` | `xsd:double` | true | 0..1 |
| `area_2008` | `xsd:double` | true | 0..1 |
| `area_2009` | `xsd:double` | true | 0..1 |
| `area_2010` | `xsd:double` | true | 0..1 |
| `area_2011` | `xsd:double` | true | 0..1 |
| `area_2012` | `xsd:double` | true | 0..1 |
| `area_2013` | `xsd:double` | true | 0..1 |
| `area_2014` | `xsd:double` | true | 0..1 |
| `area_2015` | `xsd:double` | true | 0..1 |
| `area_2016` | `xsd:double` | true | 0..1 |
| `area_2017` | `xsd:double` | true | 0..1 |
| `area_2018` | `xsd:double` | true | 0..1 |
| `area_2019` | `xsd:double` | true | 0..1 |
| `colhi_1989` | `xsd:double` | true | 0..1 |
| `colhi_1990` | `xsd:double` | true | 0..1 |
| `colhi_1991` | `xsd:double` | true | 0..1 |
| `colhi_1992` | `xsd:double` | true | 0..1 |
| `colhi_1993` | `xsd:double` | true | 0..1 |
| `colhi_1994` | `xsd:double` | true | 0..1 |
| `colhi_1995` | `xsd:double` | true | 0..1 |
| `colhi_1996` | `xsd:double` | true | 0..1 |
| `colhi_1997` | `xsd:double` | true | 0..1 |
| `colhi_1998` | `xsd:double` | true | 0..1 |
| `colhi_1999` | `xsd:double` | true | 0..1 |
| `colhi_2000` | `xsd:double` | true | 0..1 |
| `colhi_2001` | `xsd:double` | true | 0..1 |
| `colhi_2002` | `xsd:double` | true | 0..1 |
| `colhi_2003` | `xsd:double` | true | 0..1 |
| `colhi_2004` | `xsd:double` | true | 0..1 |
| `colhi_2005` | `xsd:double` | true | 0..1 |
| `colhi_2006` | `xsd:double` | true | 0..1 |
| `colhi_2007` | `xsd:double` | true | 0..1 |
| `colhi_2008` | `xsd:double` | true | 0..1 |
| `colhi_2009` | `xsd:double` | true | 0..1 |
| `colhi_2010` | `xsd:double` | true | 0..1 |
| `colhi_2011` | `xsd:double` | true | 0..1 |
| `colhi_2012` | `xsd:double` | true | 0..1 |
| `colhi_2013` | `xsd:double` | true | 0..1 |
| `colhi_2014` | `xsd:double` | true | 0..1 |
| `colhi_2015` | `xsd:double` | true | 0..1 |
| `colhi_2016` | `xsd:double` | true | 0..1 |
| `colhi_2017` | `xsd:double` | true | 0..1 |
| `colhi_2018` | `xsd:double` | true | 0..1 |
| `produ_1989` | `xsd:double` | true | 0..1 |
| `produ_1990` | `xsd:double` | true | 0..1 |
| `produ_1991` | `xsd:double` | true | 0..1 |
| `produ_1992` | `xsd:double` | true | 0..1 |
| `produ_1993` | `xsd:double` | true | 0..1 |
| `produ_1994` | `xsd:double` | true | 0..1 |
| `produ_1995` | `xsd:double` | true | 0..1 |
| `produ_1996` | `xsd:double` | true | 0..1 |
| `produ_1997` | `xsd:double` | true | 0..1 |
| `produ_1998` | `xsd:double` | true | 0..1 |
| `produ_1999` | `xsd:double` | true | 0..1 |
| `produ_2000` | `xsd:double` | true | 0..1 |
| `produ_2001` | `xsd:double` | true | 0..1 |
| `produ_2002` | `xsd:double` | true | 0..1 |
| `produ_2003` | `xsd:double` | true | 0..1 |
| `produ_2004` | `xsd:double` | true | 0..1 |
| `produ_2005` | `xsd:double` | true | 0..1 |
| `produ_2006` | `xsd:double` | true | 0..1 |
| `produ_2007` | `xsd:double` | true | 0..1 |
| `produ_2008` | `xsd:double` | true | 0..1 |
| `produ_2009` | `xsd:double` | true | 0..1 |
| `produ_2010` | `xsd:double` | true | 0..1 |
| `produ_2011` | `xsd:double` | true | 0..1 |
| `produ_2012` | `xsd:double` | true | 0..1 |
| `produ_2013` | `xsd:double` | true | 0..1 |
| `produ_2014` | `xsd:double` | true | 0..1 |
| `produ_2015` | `xsd:double` | true | 0..1 |
| `produ_2016` | `xsd:double` | true | 0..1 |
| `produ_2017` | `xsd:double` | true | 0..1 |
| `produ_2018` | `xsd:double` | true | 0..1 |
| `rendi_1989` | `xsd:double` | true | 0..1 |
| `rendi_1990` | `xsd:double` | true | 0..1 |
| `rendi_1991` | `xsd:double` | true | 0..1 |
| `rendi_1992` | `xsd:double` | true | 0..1 |
| `rendi_1993` | `xsd:double` | true | 0..1 |
| `rendi_1994` | `xsd:double` | true | 0..1 |
| `rendi_1995` | `xsd:double` | true | 0..1 |
| `rendi_1996` | `xsd:double` | true | 0..1 |
| `rendi_1997` | `xsd:double` | true | 0..1 |
| `rendi_1998` | `xsd:double` | true | 0..1 |
| `rendi_1999` | `xsd:double` | true | 0..1 |
| `rendi_2000` | `xsd:double` | true | 0..1 |
| `rendi_2001` | `xsd:double` | true | 0..1 |
| `rendi_2002` | `xsd:double` | true | 0..1 |
| `rendi_2003` | `xsd:double` | true | 0..1 |
| `rendi_2004` | `xsd:double` | true | 0..1 |
| `rendi_2005` | `xsd:double` | true | 0..1 |
| `rendi_2006` | `xsd:double` | true | 0..1 |
| `rendi_2007` | `xsd:double` | true | 0..1 |
| `rendi_2008` | `xsd:double` | true | 0..1 |
| `rendi_2009` | `xsd:double` | true | 0..1 |
| `rendi_2010` | `xsd:double` | true | 0..1 |
| `rendi_2011` | `xsd:double` | true | 0..1 |
| `rendi_2012` | `xsd:double` | true | 0..1 |
| `rendi_2013` | `xsd:double` | true | 0..1 |
| `rendi_2014` | `xsd:double` | true | 0..1 |
| `rendi_2015` | `xsd:double` | true | 0..1 |
| `rendi_2016` | `xsd:double` | true | 0..1 |
| `rendi_2017` | `xsd:double` | true | 0..1 |
| `rendi_2018` | `xsd:double` | true | 0..1 |

### `estatistica:lavoura_temporaria_algodao_1989_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `nume_cid` | `xsd:string` | true | 0..1 |
| `pgai` | `xsd:string` | true | 0..1 |
| `tipo_cidd` | `xsd:string` | true | 0..1 |
| `regiao_num` | `xsd:string` | true | 0..1 |
| `territ_cid` | `xsd:string` | true | 0..1 |
| `utr` | `xsd:string` | true | 0..1 |
| `criacao` | `xsd:string` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `pop_1996` | `xsd:double` | true | 0..1 |
| `pop_2000` | `xsd:double` | true | 0..1 |
| `pop_2007` | `xsd:double` | true | 0..1 |
| `pop_2008` | `xsd:double` | true | 0..1 |
| `pop_2009` | `xsd:double` | true | 0..1 |
| `assoc_mun` | `xsd:string` | true | 0..1 |
| `reg_pm` | `xsd:string` | true | 0..1 |
| `art_pm` | `xsd:string` | true | 0..1 |
| `region_ibg` | `xsd:string` | true | 0..1 |
| `cod_region` | `xsd:double` | true | 0..1 |
| `pop_2010` | `xsd:double` | true | 0..1 |
| `ppa_2012_2` | `xsd:string` | true | 0..1 |
| `number` | `xsd:double` | true | 0..1 |
| `regionaliz` | `xsd:string` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `reg_tur` | `xsd:string` | true | 0..1 |
| `nova_regio` | `xsd:string` | true | 0..1 |
| `nova_reg_o` | `xsd:string` | true | 0..1 |
| `cultura` | `xsd:string` | true | 0..1 |
| `area_1989` | `xsd:double` | true | 0..1 |
| `area_1990` | `xsd:double` | true | 0..1 |
| `area_1991` | `xsd:double` | true | 0..1 |
| `area_1992` | `xsd:double` | true | 0..1 |
| `area_1993` | `xsd:double` | true | 0..1 |
| `area_1994` | `xsd:double` | true | 0..1 |
| `area_1995` | `xsd:double` | true | 0..1 |
| `area_1996` | `xsd:double` | true | 0..1 |
| `area_1997` | `xsd:double` | true | 0..1 |
| `area_1998` | `xsd:double` | true | 0..1 |
| `area_1999` | `xsd:double` | true | 0..1 |
| `area_2000` | `xsd:double` | true | 0..1 |
| `area_2001` | `xsd:double` | true | 0..1 |
| `area_2002` | `xsd:double` | true | 0..1 |
| `area_2003` | `xsd:double` | true | 0..1 |
| `area_2004` | `xsd:double` | true | 0..1 |
| `area_2005` | `xsd:double` | true | 0..1 |
| `area_2006` | `xsd:double` | true | 0..1 |
| `area_2007` | `xsd:double` | true | 0..1 |
| `area_2008` | `xsd:double` | true | 0..1 |
| `area_2009` | `xsd:double` | true | 0..1 |
| `area_2010` | `xsd:double` | true | 0..1 |
| `area_2011` | `xsd:double` | true | 0..1 |
| `area_2012` | `xsd:double` | true | 0..1 |
| `area_2013` | `xsd:double` | true | 0..1 |
| `area_2014` | `xsd:double` | true | 0..1 |
| `area_2015` | `xsd:double` | true | 0..1 |
| `area_2016` | `xsd:double` | true | 0..1 |
| `area_2017` | `xsd:double` | true | 0..1 |
| `area_2018` | `xsd:double` | true | 0..1 |
| `colhi_1989` | `xsd:double` | true | 0..1 |
| `colhi_1990` | `xsd:double` | true | 0..1 |
| `colhi_1991` | `xsd:double` | true | 0..1 |
| `colhi_1992` | `xsd:double` | true | 0..1 |
| `colhi_1993` | `xsd:double` | true | 0..1 |
| `colhi_1994` | `xsd:double` | true | 0..1 |
| `colhi_1995` | `xsd:double` | true | 0..1 |
| `colhi_1996` | `xsd:double` | true | 0..1 |
| `colhi_1997` | `xsd:double` | true | 0..1 |
| `colhi_1998` | `xsd:double` | true | 0..1 |
| `colhi_1999` | `xsd:double` | true | 0..1 |
| `colhi_2000` | `xsd:double` | true | 0..1 |
| `colhi_2001` | `xsd:double` | true | 0..1 |
| `colhi_2002` | `xsd:double` | true | 0..1 |
| `colhi_2003` | `xsd:double` | true | 0..1 |
| `colhi_2004` | `xsd:double` | true | 0..1 |
| `colhi_2005` | `xsd:double` | true | 0..1 |
| `colhi_2006` | `xsd:double` | true | 0..1 |
| `colhi_2007` | `xsd:double` | true | 0..1 |
| `colhi_2008` | `xsd:double` | true | 0..1 |
| `colhi_2009` | `xsd:double` | true | 0..1 |
| `colhi_2010` | `xsd:double` | true | 0..1 |
| `colhi_2011` | `xsd:double` | true | 0..1 |
| `colhi_2012` | `xsd:double` | true | 0..1 |
| `colhi_2013` | `xsd:double` | true | 0..1 |
| `colhi_2014` | `xsd:double` | true | 0..1 |
| `colhi_2015` | `xsd:double` | true | 0..1 |
| `colhi_2016` | `xsd:double` | true | 0..1 |
| `colhi_2017` | `xsd:double` | true | 0..1 |
| `colhi_2018` | `xsd:double` | true | 0..1 |
| `produ_1989` | `xsd:double` | true | 0..1 |
| `produ_1990` | `xsd:double` | true | 0..1 |
| `produ_1991` | `xsd:double` | true | 0..1 |
| `produ_1992` | `xsd:double` | true | 0..1 |
| `produ_1993` | `xsd:double` | true | 0..1 |
| `produ_1994` | `xsd:double` | true | 0..1 |
| `produ_1995` | `xsd:double` | true | 0..1 |
| `produ_1996` | `xsd:double` | true | 0..1 |
| `produ_1997` | `xsd:double` | true | 0..1 |
| `produ_1998` | `xsd:double` | true | 0..1 |
| `produ_1999` | `xsd:double` | true | 0..1 |
| `produ_2000` | `xsd:double` | true | 0..1 |
| `produ_2001` | `xsd:double` | true | 0..1 |
| `produ_2002` | `xsd:double` | true | 0..1 |
| `produ_2003` | `xsd:double` | true | 0..1 |
| `produ_2004` | `xsd:double` | true | 0..1 |
| `produ_2005` | `xsd:double` | true | 0..1 |
| `produ_2006` | `xsd:double` | true | 0..1 |
| `produ_2007` | `xsd:double` | true | 0..1 |
| `produ_2008` | `xsd:double` | true | 0..1 |
| `produ_2009` | `xsd:double` | true | 0..1 |
| `produ_2010` | `xsd:double` | true | 0..1 |
| `produ_2011` | `xsd:double` | true | 0..1 |
| `produ_2012` | `xsd:double` | true | 0..1 |
| `produ_2013` | `xsd:double` | true | 0..1 |
| `produ_2014` | `xsd:double` | true | 0..1 |
| `produ_2015` | `xsd:double` | true | 0..1 |
| `produ_2016` | `xsd:double` | true | 0..1 |
| `produ_2017` | `xsd:double` | true | 0..1 |
| `produ_2018` | `xsd:double` | true | 0..1 |
| `rendi_1989` | `xsd:double` | true | 0..1 |
| `rendi_1990` | `xsd:double` | true | 0..1 |
| `rendi_1991` | `xsd:double` | true | 0..1 |
| `rendi_1992` | `xsd:double` | true | 0..1 |
| `rendi_1993` | `xsd:double` | true | 0..1 |
| `rendi_1994` | `xsd:double` | true | 0..1 |
| `rendi_1995` | `xsd:double` | true | 0..1 |
| `rendi_1996` | `xsd:double` | true | 0..1 |
| `rendi_1997` | `xsd:double` | true | 0..1 |
| `rendi_1998` | `xsd:double` | true | 0..1 |
| `rendi_1999` | `xsd:double` | true | 0..1 |
| `rendi_2000` | `xsd:double` | true | 0..1 |
| `rendi_2001` | `xsd:double` | true | 0..1 |
| `rendi_2002` | `xsd:double` | true | 0..1 |
| `rendi_2003` | `xsd:double` | true | 0..1 |
| `rendi_2004` | `xsd:double` | true | 0..1 |
| `rendi_2005` | `xsd:double` | true | 0..1 |
| `rendi_2006` | `xsd:double` | true | 0..1 |
| `rendi_2007` | `xsd:double` | true | 0..1 |
| `rendi_2008` | `xsd:double` | true | 0..1 |
| `rendi_2009` | `xsd:double` | true | 0..1 |
| `rendi_2010` | `xsd:double` | true | 0..1 |
| `rendi_2011` | `xsd:double` | true | 0..1 |
| `rendi_2012` | `xsd:double` | true | 0..1 |
| `rendi_2013` | `xsd:double` | true | 0..1 |
| `rendi_2014` | `xsd:double` | true | 0..1 |
| `rendi_2015` | `xsd:double` | true | 0..1 |
| `rendi_2016` | `xsd:double` | true | 0..1 |
| `rendi_2017` | `xsd:double` | true | 0..1 |
| `rendi_2018` | `xsd:double` | true | 0..1 |

### `estatistica:lavoura_temporaria_amendoim_1989_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `nume_cid` | `xsd:string` | true | 0..1 |
| `pgai` | `xsd:string` | true | 0..1 |
| `tipo_cidd` | `xsd:string` | true | 0..1 |
| `regiao_num` | `xsd:string` | true | 0..1 |
| `territ_cid` | `xsd:string` | true | 0..1 |
| `utr` | `xsd:string` | true | 0..1 |
| `criacao` | `xsd:string` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `pop_1996` | `xsd:double` | true | 0..1 |
| `pop_2000` | `xsd:double` | true | 0..1 |
| `pop_2007` | `xsd:double` | true | 0..1 |
| `pop_2008` | `xsd:double` | true | 0..1 |
| `pop_2009` | `xsd:double` | true | 0..1 |
| `assoc_mun` | `xsd:string` | true | 0..1 |
| `reg_pm` | `xsd:string` | true | 0..1 |
| `art_pm` | `xsd:string` | true | 0..1 |
| `region_ibg` | `xsd:string` | true | 0..1 |
| `cod_region` | `xsd:double` | true | 0..1 |
| `pop_2010` | `xsd:double` | true | 0..1 |
| `ppa_2012_2` | `xsd:string` | true | 0..1 |
| `number` | `xsd:double` | true | 0..1 |
| `regionaliz` | `xsd:string` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `reg_tur` | `xsd:string` | true | 0..1 |
| `nova_regio` | `xsd:string` | true | 0..1 |
| `nova_reg_o` | `xsd:string` | true | 0..1 |
| `cultura` | `xsd:string` | true | 0..1 |
| `area_1989` | `xsd:double` | true | 0..1 |
| `area_1990` | `xsd:double` | true | 0..1 |
| `area_1991` | `xsd:double` | true | 0..1 |
| `area_1992` | `xsd:double` | true | 0..1 |
| `area_1993` | `xsd:double` | true | 0..1 |
| `area_1994` | `xsd:double` | true | 0..1 |
| `area_1995` | `xsd:double` | true | 0..1 |
| `area_1996` | `xsd:double` | true | 0..1 |
| `area_1997` | `xsd:double` | true | 0..1 |
| `area_1998` | `xsd:double` | true | 0..1 |
| `area_1999` | `xsd:double` | true | 0..1 |
| `area_2000` | `xsd:double` | true | 0..1 |
| `area_2001` | `xsd:double` | true | 0..1 |
| `area_2002` | `xsd:double` | true | 0..1 |
| `area_2003` | `xsd:double` | true | 0..1 |
| `area_2004` | `xsd:double` | true | 0..1 |
| `area_2005` | `xsd:double` | true | 0..1 |
| `area_2006` | `xsd:double` | true | 0..1 |
| `area_2007` | `xsd:double` | true | 0..1 |
| `area_2008` | `xsd:double` | true | 0..1 |
| `area_2009` | `xsd:double` | true | 0..1 |
| `area_2010` | `xsd:double` | true | 0..1 |
| `area_2011` | `xsd:double` | true | 0..1 |
| `area_2012` | `xsd:double` | true | 0..1 |
| `area_2013` | `xsd:double` | true | 0..1 |
| `area_2014` | `xsd:double` | true | 0..1 |
| `area_2015` | `xsd:double` | true | 0..1 |
| `area_2016` | `xsd:double` | true | 0..1 |
| `area_2017` | `xsd:double` | true | 0..1 |
| `area_2018` | `xsd:double` | true | 0..1 |
| `colh_1989` | `xsd:double` | true | 0..1 |
| `colh_1990` | `xsd:double` | true | 0..1 |
| `colh_1991` | `xsd:double` | true | 0..1 |
| `colh_1992` | `xsd:double` | true | 0..1 |
| `colh_1993` | `xsd:double` | true | 0..1 |
| `colh_1994` | `xsd:double` | true | 0..1 |
| `colh_1995` | `xsd:double` | true | 0..1 |
| `colh_1996` | `xsd:double` | true | 0..1 |
| `colh_1997` | `xsd:double` | true | 0..1 |
| `colh_1998` | `xsd:double` | true | 0..1 |
| `colh_1999` | `xsd:double` | true | 0..1 |
| `colh_2000` | `xsd:double` | true | 0..1 |
| `colh_2001` | `xsd:double` | true | 0..1 |
| `colh_2002` | `xsd:double` | true | 0..1 |
| `colh_2003` | `xsd:double` | true | 0..1 |
| `colh_2004` | `xsd:double` | true | 0..1 |
| `colh_2005` | `xsd:double` | true | 0..1 |
| `colh_2006` | `xsd:double` | true | 0..1 |
| `colh_2007` | `xsd:double` | true | 0..1 |
| `colh_2008` | `xsd:double` | true | 0..1 |
| `colh_2009` | `xsd:double` | true | 0..1 |
| `colh_2010` | `xsd:double` | true | 0..1 |
| `colh_2011` | `xsd:double` | true | 0..1 |
| `colh_2012` | `xsd:double` | true | 0..1 |
| `colh_2013` | `xsd:double` | true | 0..1 |
| `colh_2014` | `xsd:double` | true | 0..1 |
| `colh_2015` | `xsd:double` | true | 0..1 |
| `colh_2016` | `xsd:double` | true | 0..1 |
| `colh_2017` | `xsd:double` | true | 0..1 |
| `colh_2018` | `xsd:double` | true | 0..1 |
| `prod_1989` | `xsd:double` | true | 0..1 |
| `prod_1990` | `xsd:double` | true | 0..1 |
| `prod_1991` | `xsd:double` | true | 0..1 |
| `prod_1992` | `xsd:double` | true | 0..1 |
| `prod_1993` | `xsd:double` | true | 0..1 |
| `prod_1994` | `xsd:double` | true | 0..1 |
| `prod_1995` | `xsd:double` | true | 0..1 |
| `prod_1996` | `xsd:double` | true | 0..1 |
| `prod_1997` | `xsd:double` | true | 0..1 |
| `prod_1998` | `xsd:double` | true | 0..1 |
| `prod_1999` | `xsd:double` | true | 0..1 |
| `prod_2000` | `xsd:double` | true | 0..1 |
| `prod_2001` | `xsd:double` | true | 0..1 |
| `prod_2002` | `xsd:double` | true | 0..1 |
| `prod_2003` | `xsd:double` | true | 0..1 |
| `prod_2004` | `xsd:double` | true | 0..1 |
| `prod_2005` | `xsd:double` | true | 0..1 |
| `prod_2006` | `xsd:double` | true | 0..1 |
| `prod_2007` | `xsd:double` | true | 0..1 |
| `prod_2008` | `xsd:double` | true | 0..1 |
| `prod_2009` | `xsd:double` | true | 0..1 |
| `prod_2010` | `xsd:double` | true | 0..1 |
| `prod_2011` | `xsd:double` | true | 0..1 |
| `prod_2012` | `xsd:double` | true | 0..1 |
| `prod_2013` | `xsd:double` | true | 0..1 |
| `prod_2014` | `xsd:double` | true | 0..1 |
| `prod_2015` | `xsd:double` | true | 0..1 |
| `prod_2016` | `xsd:double` | true | 0..1 |
| `prod_2017` | `xsd:double` | true | 0..1 |
| `prod_2018` | `xsd:double` | true | 0..1 |
| `rend_1989` | `xsd:double` | true | 0..1 |
| `rend_1990` | `xsd:double` | true | 0..1 |
| `rend_1991` | `xsd:double` | true | 0..1 |
| `rend_1992` | `xsd:double` | true | 0..1 |
| `rend_1993` | `xsd:double` | true | 0..1 |
| `rend_1994` | `xsd:double` | true | 0..1 |
| `rend_1995` | `xsd:double` | true | 0..1 |
| `rend_1996` | `xsd:double` | true | 0..1 |
| `rend_1997` | `xsd:double` | true | 0..1 |
| `rend_1998` | `xsd:double` | true | 0..1 |
| `rend_1999` | `xsd:double` | true | 0..1 |
| `rend_2000` | `xsd:double` | true | 0..1 |
| `rend_2001` | `xsd:double` | true | 0..1 |
| `rend_2002` | `xsd:double` | true | 0..1 |
| `rend_2003` | `xsd:double` | true | 0..1 |
| `rend_2004` | `xsd:double` | true | 0..1 |
| `rend_2005` | `xsd:double` | true | 0..1 |
| `rend_2006` | `xsd:double` | true | 0..1 |
| `rend_2007` | `xsd:double` | true | 0..1 |
| `rend_2008` | `xsd:double` | true | 0..1 |
| `rend_2009` | `xsd:double` | true | 0..1 |
| `rend_2010` | `xsd:double` | true | 0..1 |
| `rend_2011` | `xsd:double` | true | 0..1 |
| `rend_2012` | `xsd:double` | true | 0..1 |
| `rend_2013` | `xsd:double` | true | 0..1 |
| `rend_2014` | `xsd:double` | true | 0..1 |
| `rend_2015` | `xsd:double` | true | 0..1 |
| `rend_2016` | `xsd:double` | true | 0..1 |
| `rend_2017` | `xsd:double` | true | 0..1 |
| `rend_2018` | `xsd:double` | true | 0..1 |

### `estatistica:lavoura_temporaria_arroz_1989_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `nume_cid` | `xsd:string` | true | 0..1 |
| `pgai` | `xsd:string` | true | 0..1 |
| `tipo_cidd` | `xsd:string` | true | 0..1 |
| `regiao_num` | `xsd:string` | true | 0..1 |
| `territ_cid` | `xsd:string` | true | 0..1 |
| `utr` | `xsd:string` | true | 0..1 |
| `criacao` | `xsd:string` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `pop_1996` | `xsd:double` | true | 0..1 |
| `pop_2000` | `xsd:double` | true | 0..1 |
| `pop_2007` | `xsd:double` | true | 0..1 |
| `pop_2008` | `xsd:double` | true | 0..1 |
| `pop_2009` | `xsd:double` | true | 0..1 |
| `assoc_mun` | `xsd:string` | true | 0..1 |
| `reg_pm` | `xsd:string` | true | 0..1 |
| `art_pm` | `xsd:string` | true | 0..1 |
| `region_ibg` | `xsd:string` | true | 0..1 |
| `cod_region` | `xsd:double` | true | 0..1 |
| `pop_2010` | `xsd:double` | true | 0..1 |
| `ppa_2012_2` | `xsd:string` | true | 0..1 |
| `number` | `xsd:double` | true | 0..1 |
| `regionaliz` | `xsd:string` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `reg_tur` | `xsd:string` | true | 0..1 |
| `nova_regio` | `xsd:string` | true | 0..1 |
| `nova_reg_o` | `xsd:string` | true | 0..1 |
| `cultura` | `xsd:string` | true | 0..1 |
| `area_1989` | `xsd:double` | true | 0..1 |
| `area_1990` | `xsd:double` | true | 0..1 |
| `area_1991` | `xsd:double` | true | 0..1 |
| `area_1992` | `xsd:double` | true | 0..1 |
| `area_1993` | `xsd:double` | true | 0..1 |
| `area_1994` | `xsd:double` | true | 0..1 |
| `area_1995` | `xsd:double` | true | 0..1 |
| `area_1996` | `xsd:double` | true | 0..1 |
| `area_1997` | `xsd:double` | true | 0..1 |
| `area_1998` | `xsd:double` | true | 0..1 |
| `area_1999` | `xsd:double` | true | 0..1 |
| `area_2000` | `xsd:double` | true | 0..1 |
| `area_2001` | `xsd:double` | true | 0..1 |
| `area_2002` | `xsd:double` | true | 0..1 |
| `area_2003` | `xsd:double` | true | 0..1 |
| `area_2004` | `xsd:double` | true | 0..1 |
| `area_2005` | `xsd:double` | true | 0..1 |
| `area_2006` | `xsd:double` | true | 0..1 |
| `area_2007` | `xsd:double` | true | 0..1 |
| `area_2008` | `xsd:double` | true | 0..1 |
| `area_2009` | `xsd:double` | true | 0..1 |
| `area_2010` | `xsd:double` | true | 0..1 |
| `area_2011` | `xsd:double` | true | 0..1 |
| `area_2012` | `xsd:double` | true | 0..1 |
| `area_2013` | `xsd:double` | true | 0..1 |
| `area_2014` | `xsd:double` | true | 0..1 |
| `area_2015` | `xsd:double` | true | 0..1 |
| `area_2016` | `xsd:double` | true | 0..1 |
| `area_2017` | `xsd:double` | true | 0..1 |
| `area_2018` | `xsd:double` | true | 0..1 |
| `colh_1989` | `xsd:string` | true | 0..1 |
| `colh_1990` | `xsd:double` | true | 0..1 |
| `colh_1991` | `xsd:double` | true | 0..1 |
| `colh_1992` | `xsd:double` | true | 0..1 |
| `colh_1993` | `xsd:double` | true | 0..1 |
| `colh_1994` | `xsd:double` | true | 0..1 |
| `colh_1995` | `xsd:double` | true | 0..1 |
| `colh_1996` | `xsd:double` | true | 0..1 |
| `colh_1997` | `xsd:double` | true | 0..1 |
| `colh_1998` | `xsd:double` | true | 0..1 |
| `colh_1999` | `xsd:double` | true | 0..1 |
| `colh_2000` | `xsd:double` | true | 0..1 |
| `colh_2001` | `xsd:double` | true | 0..1 |
| `colh_2002` | `xsd:double` | true | 0..1 |
| `colh_2003` | `xsd:double` | true | 0..1 |
| `colh_2004` | `xsd:double` | true | 0..1 |
| `colh_2005` | `xsd:double` | true | 0..1 |
| `colh_2006` | `xsd:double` | true | 0..1 |
| `colh_2007` | `xsd:double` | true | 0..1 |
| `colh_2008` | `xsd:double` | true | 0..1 |
| `colh_2009` | `xsd:double` | true | 0..1 |
| `colh_2010` | `xsd:double` | true | 0..1 |
| `colh_2011` | `xsd:double` | true | 0..1 |
| `prod_1989` | `xsd:double` | true | 0..1 |
| `prod_1990` | `xsd:double` | true | 0..1 |
| `prod_1991` | `xsd:double` | true | 0..1 |
| `prod_1992` | `xsd:double` | true | 0..1 |
| `prod_1993` | `xsd:double` | true | 0..1 |
| `prod_1994` | `xsd:double` | true | 0..1 |
| `prod_1995` | `xsd:double` | true | 0..1 |
| `prod_1996` | `xsd:double` | true | 0..1 |
| `prod_1997` | `xsd:double` | true | 0..1 |
| `prod_1998` | `xsd:double` | true | 0..1 |
| `prod_1999` | `xsd:double` | true | 0..1 |
| `prod_2000` | `xsd:double` | true | 0..1 |
| `prod_2001` | `xsd:double` | true | 0..1 |
| `prod_2002` | `xsd:double` | true | 0..1 |
| `prod_2003` | `xsd:double` | true | 0..1 |
| `prod_2004` | `xsd:double` | true | 0..1 |
| `prod_2005` | `xsd:double` | true | 0..1 |
| `prod_2006` | `xsd:double` | true | 0..1 |
| `prod_2007` | `xsd:double` | true | 0..1 |
| `prod_2008` | `xsd:double` | true | 0..1 |
| `prod_2009` | `xsd:double` | true | 0..1 |
| `prod_2010` | `xsd:double` | true | 0..1 |
| `prod_2011` | `xsd:double` | true | 0..1 |
| `prod_2012` | `xsd:double` | true | 0..1 |
| `prod_2013` | `xsd:double` | true | 0..1 |
| `prod_2014` | `xsd:double` | true | 0..1 |
| `prod_2015` | `xsd:double` | true | 0..1 |
| `prod_2016` | `xsd:double` | true | 0..1 |
| `prod_2017` | `xsd:double` | true | 0..1 |
| `prod_2018` | `xsd:double` | true | 0..1 |
| `rend_1989` | `xsd:double` | true | 0..1 |
| `rend_1990` | `xsd:double` | true | 0..1 |
| `rend_1991` | `xsd:double` | true | 0..1 |
| `rend_1992` | `xsd:double` | true | 0..1 |
| `rend_1993` | `xsd:double` | true | 0..1 |
| `rend_1994` | `xsd:double` | true | 0..1 |
| `rend_1995` | `xsd:double` | true | 0..1 |
| `rend_1996` | `xsd:double` | true | 0..1 |
| `rend_1997` | `xsd:double` | true | 0..1 |
| `rend_1998` | `xsd:double` | true | 0..1 |
| `rend_1999` | `xsd:double` | true | 0..1 |
| `rend_2000` | `xsd:double` | true | 0..1 |
| `rend_2001` | `xsd:double` | true | 0..1 |
| `rend_2002` | `xsd:double` | true | 0..1 |
| `rend_2003` | `xsd:double` | true | 0..1 |
| `rend_2004` | `xsd:double` | true | 0..1 |
| `rend_2005` | `xsd:double` | true | 0..1 |
| `rend_2006` | `xsd:double` | true | 0..1 |
| `rend_2007` | `xsd:double` | true | 0..1 |
| `rend_2008` | `xsd:double` | true | 0..1 |
| `rend_2009` | `xsd:double` | true | 0..1 |
| `rend_2010` | `xsd:double` | true | 0..1 |
| `rend_2011` | `xsd:double` | true | 0..1 |
| `rend_2012` | `xsd:double` | true | 0..1 |
| `rend_2013` | `xsd:double` | true | 0..1 |
| `rend_2014` | `xsd:double` | true | 0..1 |
| `rend_2015` | `xsd:double` | true | 0..1 |
| `rend_2016` | `xsd:double` | true | 0..1 |
| `rend_2017` | `xsd:double` | true | 0..1 |
| `rend_2018` | `xsd:double` | true | 0..1 |

### `estatistica:lavoura_temporaria_cana_de_acucar_1989_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `nume_cid` | `xsd:string` | true | 0..1 |
| `pgai` | `xsd:string` | true | 0..1 |
| `tipo_cidd` | `xsd:string` | true | 0..1 |
| `regiao_num` | `xsd:string` | true | 0..1 |
| `territ_cid` | `xsd:string` | true | 0..1 |
| `utr` | `xsd:string` | true | 0..1 |
| `criacao` | `xsd:string` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `pop_1996` | `xsd:double` | true | 0..1 |
| `pop_2000` | `xsd:double` | true | 0..1 |
| `pop_2007` | `xsd:double` | true | 0..1 |
| `pop_2008` | `xsd:double` | true | 0..1 |
| `pop_2009` | `xsd:double` | true | 0..1 |
| `assoc_mun` | `xsd:string` | true | 0..1 |
| `reg_pm` | `xsd:string` | true | 0..1 |
| `art_pm` | `xsd:string` | true | 0..1 |
| `region_ibg` | `xsd:string` | true | 0..1 |
| `cod_region` | `xsd:double` | true | 0..1 |
| `pop_2010` | `xsd:double` | true | 0..1 |
| `ppa_2012_2` | `xsd:string` | true | 0..1 |
| `number` | `xsd:double` | true | 0..1 |
| `regionaliz` | `xsd:string` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `reg_tur` | `xsd:string` | true | 0..1 |
| `nova_regio` | `xsd:string` | true | 0..1 |
| `nova_reg_o` | `xsd:string` | true | 0..1 |
| `cultura` | `xsd:string` | true | 0..1 |
| `area_1989` | `xsd:double` | true | 0..1 |
| `area_1990` | `xsd:double` | true | 0..1 |
| `area_1991` | `xsd:double` | true | 0..1 |
| `area_1992` | `xsd:double` | true | 0..1 |
| `area_1993` | `xsd:double` | true | 0..1 |
| `area_1994` | `xsd:double` | true | 0..1 |
| `area_1995` | `xsd:double` | true | 0..1 |
| `area_1996` | `xsd:double` | true | 0..1 |
| `area_1997` | `xsd:double` | true | 0..1 |
| `area_1998` | `xsd:double` | true | 0..1 |
| `area_1999` | `xsd:double` | true | 0..1 |
| `area_2000` | `xsd:double` | true | 0..1 |
| `area_2001` | `xsd:double` | true | 0..1 |
| `area_2002` | `xsd:double` | true | 0..1 |
| `area_2003` | `xsd:double` | true | 0..1 |
| `area_2004` | `xsd:double` | true | 0..1 |
| `area_2005` | `xsd:double` | true | 0..1 |
| `area_2006` | `xsd:double` | true | 0..1 |
| `area_2007` | `xsd:double` | true | 0..1 |
| `area_2008` | `xsd:double` | true | 0..1 |
| `area_2009` | `xsd:double` | true | 0..1 |
| `area_2010` | `xsd:double` | true | 0..1 |
| `area_2011` | `xsd:double` | true | 0..1 |
| `area_2012` | `xsd:double` | true | 0..1 |
| `area_2013` | `xsd:double` | true | 0..1 |
| `area_2014` | `xsd:double` | true | 0..1 |
| `area_2015` | `xsd:double` | true | 0..1 |
| `area_2016` | `xsd:double` | true | 0..1 |
| `area_2017` | `xsd:double` | true | 0..1 |
| `area_2018` | `xsd:double` | true | 0..1 |
| `colh_1989` | `xsd:double` | true | 0..1 |
| `colh_1990` | `xsd:double` | true | 0..1 |
| `colh_1991` | `xsd:double` | true | 0..1 |
| `colh_1992` | `xsd:double` | true | 0..1 |
| `colh_1993` | `xsd:double` | true | 0..1 |
| `colh_1994` | `xsd:double` | true | 0..1 |
| `colh_1995` | `xsd:double` | true | 0..1 |
| `colh_1996` | `xsd:double` | true | 0..1 |
| `colh_1997` | `xsd:double` | true | 0..1 |
| `colh_1998` | `xsd:double` | true | 0..1 |
| `colh_1999` | `xsd:double` | true | 0..1 |
| `colh_2000` | `xsd:double` | true | 0..1 |
| `colh_2001` | `xsd:double` | true | 0..1 |
| `colh_2002` | `xsd:double` | true | 0..1 |
| `colh_2003` | `xsd:double` | true | 0..1 |
| `colh_2004` | `xsd:double` | true | 0..1 |
| `colh_2005` | `xsd:double` | true | 0..1 |
| `colh_2006` | `xsd:double` | true | 0..1 |
| `colh_2007` | `xsd:double` | true | 0..1 |
| `colh_2008` | `xsd:double` | true | 0..1 |
| `colh_2009` | `xsd:double` | true | 0..1 |
| `colh_2010` | `xsd:double` | true | 0..1 |
| `colh_2011` | `xsd:double` | true | 0..1 |
| `colh_2012` | `xsd:double` | true | 0..1 |
| `colh_2013` | `xsd:double` | true | 0..1 |
| `colh_2014` | `xsd:double` | true | 0..1 |
| `colh_2015` | `xsd:double` | true | 0..1 |
| `colh_2016` | `xsd:double` | true | 0..1 |
| `colh_2017` | `xsd:double` | true | 0..1 |
| `colh_2018` | `xsd:double` | true | 0..1 |
| `prod_1989` | `xsd:double` | true | 0..1 |
| `prod_1990` | `xsd:double` | true | 0..1 |
| `prod_1991` | `xsd:double` | true | 0..1 |
| `prod_1992` | `xsd:double` | true | 0..1 |
| `prod_1993` | `xsd:double` | true | 0..1 |
| `prod_1994` | `xsd:double` | true | 0..1 |
| `prod_1995` | `xsd:double` | true | 0..1 |
| `prod_1996` | `xsd:double` | true | 0..1 |
| `prod_1997` | `xsd:double` | true | 0..1 |
| `prod_1998` | `xsd:double` | true | 0..1 |
| `prod_1999` | `xsd:double` | true | 0..1 |
| `prod_2000` | `xsd:double` | true | 0..1 |
| `prod_2001` | `xsd:double` | true | 0..1 |
| `prod_2002` | `xsd:double` | true | 0..1 |
| `prod_2003` | `xsd:double` | true | 0..1 |
| `prod_2004` | `xsd:double` | true | 0..1 |
| `prod_2005` | `xsd:double` | true | 0..1 |
| `prod_2006` | `xsd:double` | true | 0..1 |
| `prod_2007` | `xsd:double` | true | 0..1 |
| `prod_2008` | `xsd:double` | true | 0..1 |
| `prod_2009` | `xsd:double` | true | 0..1 |
| `prod_2010` | `xsd:double` | true | 0..1 |
| `prod_2011` | `xsd:double` | true | 0..1 |
| `prod_2012` | `xsd:double` | true | 0..1 |
| `prod_2013` | `xsd:double` | true | 0..1 |
| `prod_2014` | `xsd:double` | true | 0..1 |
| `prod_2015` | `xsd:double` | true | 0..1 |
| `prod_2016` | `xsd:double` | true | 0..1 |
| `prod_2017` | `xsd:double` | true | 0..1 |
| `prod_2018` | `xsd:double` | true | 0..1 |
| `rend_1989` | `xsd:double` | true | 0..1 |
| `rend_1990` | `xsd:double` | true | 0..1 |
| `rend_1991` | `xsd:double` | true | 0..1 |
| `rend_1992` | `xsd:double` | true | 0..1 |
| `rend_1993` | `xsd:double` | true | 0..1 |
| `rend_1994` | `xsd:double` | true | 0..1 |
| `rend_1995` | `xsd:double` | true | 0..1 |
| `rend_1996` | `xsd:double` | true | 0..1 |
| `rend_1997` | `xsd:double` | true | 0..1 |
| `rend_1998` | `xsd:double` | true | 0..1 |
| `rend_1999` | `xsd:double` | true | 0..1 |
| `rend_2000` | `xsd:double` | true | 0..1 |
| `rend_2001` | `xsd:double` | true | 0..1 |
| `rend_2002` | `xsd:double` | true | 0..1 |
| `rend_2003` | `xsd:double` | true | 0..1 |
| `rend_2004` | `xsd:double` | true | 0..1 |
| `rend_2005` | `xsd:double` | true | 0..1 |
| `rend_2006` | `xsd:double` | true | 0..1 |
| `rend_2007` | `xsd:double` | true | 0..1 |
| `rend_2008` | `xsd:double` | true | 0..1 |
| `rend_2009` | `xsd:double` | true | 0..1 |
| `rend_2010` | `xsd:double` | true | 0..1 |
| `rend_2011` | `xsd:double` | true | 0..1 |
| `rend_2012` | `xsd:double` | true | 0..1 |
| `rend_2013` | `xsd:double` | true | 0..1 |
| `rend_2014` | `xsd:double` | true | 0..1 |
| `rend_2015` | `xsd:double` | true | 0..1 |
| `rend_2016` | `xsd:double` | true | 0..1 |
| `rend_2017` | `xsd:double` | true | 0..1 |
| `rend_2018` | `xsd:double` | true | 0..1 |

### `estatistica:lavoura_temporaria_feijao_1989_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `nume_cid` | `xsd:string` | true | 0..1 |
| `pgai` | `xsd:string` | true | 0..1 |
| `tipo_cidd` | `xsd:string` | true | 0..1 |
| `regiao_num` | `xsd:string` | true | 0..1 |
| `territ_cid` | `xsd:string` | true | 0..1 |
| `utr` | `xsd:string` | true | 0..1 |
| `criacao` | `xsd:string` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `pop_1996` | `xsd:double` | true | 0..1 |
| `pop_2000` | `xsd:double` | true | 0..1 |
| `pop_2007` | `xsd:double` | true | 0..1 |
| `pop_2008` | `xsd:double` | true | 0..1 |
| `pop_2009` | `xsd:double` | true | 0..1 |
| `assoc_mun` | `xsd:string` | true | 0..1 |
| `reg_pm` | `xsd:string` | true | 0..1 |
| `art_pm` | `xsd:string` | true | 0..1 |
| `region_ibg` | `xsd:string` | true | 0..1 |
| `cod_region` | `xsd:double` | true | 0..1 |
| `pop_2010` | `xsd:double` | true | 0..1 |
| `ppa_2012_2` | `xsd:string` | true | 0..1 |
| `number` | `xsd:double` | true | 0..1 |
| `regionaliz` | `xsd:string` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `reg_tur` | `xsd:string` | true | 0..1 |
| `nova_regio` | `xsd:string` | true | 0..1 |
| `nova_reg_o` | `xsd:string` | true | 0..1 |
| `cultura` | `xsd:string` | true | 0..1 |
| `area_1989` | `xsd:double` | true | 0..1 |
| `area_1990` | `xsd:double` | true | 0..1 |
| `area_1991` | `xsd:double` | true | 0..1 |
| `area_1992` | `xsd:double` | true | 0..1 |
| `area_1993` | `xsd:double` | true | 0..1 |
| `area_1994` | `xsd:double` | true | 0..1 |
| `area_1995` | `xsd:double` | true | 0..1 |
| `area_1996` | `xsd:double` | true | 0..1 |
| `area_1997` | `xsd:double` | true | 0..1 |
| `area_1998` | `xsd:double` | true | 0..1 |
| `area_1999` | `xsd:double` | true | 0..1 |
| `area_2000` | `xsd:double` | true | 0..1 |
| `area_2001` | `xsd:double` | true | 0..1 |
| `area_2002` | `xsd:double` | true | 0..1 |
| `area_2003` | `xsd:double` | true | 0..1 |
| `area_2004` | `xsd:double` | true | 0..1 |
| `area_2005` | `xsd:double` | true | 0..1 |
| `area_2006` | `xsd:double` | true | 0..1 |
| `area_2007` | `xsd:double` | true | 0..1 |
| `area_2008` | `xsd:double` | true | 0..1 |
| `area_2009` | `xsd:double` | true | 0..1 |
| `area_2010` | `xsd:double` | true | 0..1 |
| `area_2011` | `xsd:double` | true | 0..1 |
| `area_2012` | `xsd:double` | true | 0..1 |
| `area_2013` | `xsd:double` | true | 0..1 |
| `area_2014` | `xsd:double` | true | 0..1 |
| `area_2015` | `xsd:double` | true | 0..1 |
| `area_2016` | `xsd:double` | true | 0..1 |
| `area_2017` | `xsd:double` | true | 0..1 |
| `area_2018` | `xsd:double` | true | 0..1 |
| `colh_1989` | `xsd:double` | true | 0..1 |
| `colh_1990` | `xsd:double` | true | 0..1 |
| `colh_1991` | `xsd:double` | true | 0..1 |
| `colh_1992` | `xsd:double` | true | 0..1 |
| `colh_1993` | `xsd:double` | true | 0..1 |
| `colh_1994` | `xsd:double` | true | 0..1 |
| `colh_1995` | `xsd:double` | true | 0..1 |
| `colh_1996` | `xsd:double` | true | 0..1 |
| `colh_1997` | `xsd:double` | true | 0..1 |
| `colh_1998` | `xsd:double` | true | 0..1 |
| `colh_1999` | `xsd:double` | true | 0..1 |
| `colh_2000` | `xsd:double` | true | 0..1 |
| `colh_2001` | `xsd:double` | true | 0..1 |
| `colh_2002` | `xsd:double` | true | 0..1 |
| `colh_2003` | `xsd:double` | true | 0..1 |
| `colh_2004` | `xsd:double` | true | 0..1 |
| `colh_2005` | `xsd:double` | true | 0..1 |
| `colh_2006` | `xsd:double` | true | 0..1 |
| `colh_2007` | `xsd:double` | true | 0..1 |
| `colh_2008` | `xsd:double` | true | 0..1 |
| `colh_2009` | `xsd:double` | true | 0..1 |
| `colh_2010` | `xsd:double` | true | 0..1 |
| `colh_2011` | `xsd:double` | true | 0..1 |
| `colh_2012` | `xsd:double` | true | 0..1 |
| `colh_2013` | `xsd:double` | true | 0..1 |
| `colh_2014` | `xsd:double` | true | 0..1 |
| `colh_2015` | `xsd:double` | true | 0..1 |
| `colh_2016` | `xsd:double` | true | 0..1 |
| `colh_2017` | `xsd:double` | true | 0..1 |
| `colh_2018` | `xsd:double` | true | 0..1 |
| `prod_1989` | `xsd:double` | true | 0..1 |
| `prod_1990` | `xsd:double` | true | 0..1 |
| `prod_1991` | `xsd:double` | true | 0..1 |
| `prod_1992` | `xsd:double` | true | 0..1 |
| `prod_1993` | `xsd:double` | true | 0..1 |
| `prod_1994` | `xsd:double` | true | 0..1 |
| `prod_1995` | `xsd:double` | true | 0..1 |
| `prod_1996` | `xsd:double` | true | 0..1 |
| `prod_1997` | `xsd:double` | true | 0..1 |
| `prod_1998` | `xsd:double` | true | 0..1 |
| `prod_1999` | `xsd:double` | true | 0..1 |
| `prod_2000` | `xsd:double` | true | 0..1 |
| `prod_2001` | `xsd:double` | true | 0..1 |
| `prod_2002` | `xsd:double` | true | 0..1 |
| `prod_2003` | `xsd:double` | true | 0..1 |
| `prod_2004` | `xsd:double` | true | 0..1 |
| `prod_2005` | `xsd:double` | true | 0..1 |
| `prod_2006` | `xsd:double` | true | 0..1 |
| `prod_2007` | `xsd:double` | true | 0..1 |
| `prod_2008` | `xsd:double` | true | 0..1 |
| `prod_2009` | `xsd:double` | true | 0..1 |
| `prod_2010` | `xsd:double` | true | 0..1 |
| `prod_2011` | `xsd:double` | true | 0..1 |
| `prod_2012` | `xsd:double` | true | 0..1 |
| `prod_2013` | `xsd:double` | true | 0..1 |
| `prod_2014` | `xsd:double` | true | 0..1 |
| `prod_2015` | `xsd:double` | true | 0..1 |
| `prod_2016` | `xsd:double` | true | 0..1 |
| `prod_2017` | `xsd:double` | true | 0..1 |
| `prod_2018` | `xsd:double` | true | 0..1 |
| `rend_1989` | `xsd:double` | true | 0..1 |
| `rend_1990` | `xsd:double` | true | 0..1 |
| `rend_1991` | `xsd:double` | true | 0..1 |
| `rend_1992` | `xsd:double` | true | 0..1 |
| `rend_1993` | `xsd:double` | true | 0..1 |
| `rend_1994` | `xsd:double` | true | 0..1 |
| `rend_1995` | `xsd:double` | true | 0..1 |
| `rend_1996` | `xsd:double` | true | 0..1 |
| `rend_1997` | `xsd:double` | true | 0..1 |
| `rend_1998` | `xsd:double` | true | 0..1 |
| `rend_1999` | `xsd:double` | true | 0..1 |
| `rend_2000` | `xsd:double` | true | 0..1 |
| `rend_2001` | `xsd:double` | true | 0..1 |
| `rend_2002` | `xsd:double` | true | 0..1 |
| `rend_2003` | `xsd:double` | true | 0..1 |
| `rend_2004` | `xsd:double` | true | 0..1 |
| `rend_2005` | `xsd:double` | true | 0..1 |
| `rend_2006` | `xsd:double` | true | 0..1 |
| `rend_2007` | `xsd:double` | true | 0..1 |
| `rend_2008` | `xsd:double` | true | 0..1 |
| `rend_2009` | `xsd:double` | true | 0..1 |
| `rend_2010` | `xsd:double` | true | 0..1 |
| `rend_2011` | `xsd:double` | true | 0..1 |
| `rend_2012` | `xsd:double` | true | 0..1 |
| `rend_2013` | `xsd:double` | true | 0..1 |
| `rend_2014` | `xsd:double` | true | 0..1 |
| `rend_2015` | `xsd:double` | true | 0..1 |
| `rend_2016` | `xsd:double` | true | 0..1 |
| `rend_2017` | `xsd:double` | true | 0..1 |
| `rend_2018` | `xsd:double` | true | 0..1 |

### `estatistica:lavoura_temporaria_mandioca_1989_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `nume_cid` | `xsd:string` | true | 0..1 |
| `pgai` | `xsd:string` | true | 0..1 |
| `tipo_cidd` | `xsd:string` | true | 0..1 |
| `regiao_num` | `xsd:string` | true | 0..1 |
| `territ_cid` | `xsd:string` | true | 0..1 |
| `utr` | `xsd:string` | true | 0..1 |
| `criacao` | `xsd:string` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `pop_1996` | `xsd:double` | true | 0..1 |
| `pop_2000` | `xsd:double` | true | 0..1 |
| `pop_2007` | `xsd:double` | true | 0..1 |
| `pop_2008` | `xsd:double` | true | 0..1 |
| `pop_2009` | `xsd:double` | true | 0..1 |
| `assoc_mun` | `xsd:string` | true | 0..1 |
| `reg_pm` | `xsd:string` | true | 0..1 |
| `art_pm` | `xsd:string` | true | 0..1 |
| `region_ibg` | `xsd:string` | true | 0..1 |
| `cod_region` | `xsd:double` | true | 0..1 |
| `pop_2010` | `xsd:double` | true | 0..1 |
| `ppa_2012_2` | `xsd:string` | true | 0..1 |
| `number` | `xsd:double` | true | 0..1 |
| `regionaliz` | `xsd:string` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `reg_tur` | `xsd:string` | true | 0..1 |
| `nova_regio` | `xsd:string` | true | 0..1 |
| `nova_reg_o` | `xsd:string` | true | 0..1 |
| `cultura` | `xsd:string` | true | 0..1 |
| `area_1989` | `xsd:double` | true | 0..1 |
| `area_1990` | `xsd:double` | true | 0..1 |
| `area_1991` | `xsd:double` | true | 0..1 |
| `area_1992` | `xsd:double` | true | 0..1 |
| `area_1993` | `xsd:double` | true | 0..1 |
| `area_1994` | `xsd:double` | true | 0..1 |
| `area_1995` | `xsd:double` | true | 0..1 |
| `area_1996` | `xsd:double` | true | 0..1 |
| `area_1997` | `xsd:double` | true | 0..1 |
| `area_1998` | `xsd:double` | true | 0..1 |
| `area_1999` | `xsd:double` | true | 0..1 |
| `area_2000` | `xsd:double` | true | 0..1 |
| `area_2001` | `xsd:double` | true | 0..1 |
| `area_2002` | `xsd:double` | true | 0..1 |
| `area_2003` | `xsd:double` | true | 0..1 |
| `area_2004` | `xsd:double` | true | 0..1 |
| `area_2005` | `xsd:double` | true | 0..1 |
| `area_2006` | `xsd:double` | true | 0..1 |
| `area_2007` | `xsd:double` | true | 0..1 |
| `area_2008` | `xsd:double` | true | 0..1 |
| `area_2009` | `xsd:double` | true | 0..1 |
| `area_2010` | `xsd:double` | true | 0..1 |
| `area_2011` | `xsd:double` | true | 0..1 |
| `area_2012` | `xsd:double` | true | 0..1 |
| `area_2013` | `xsd:double` | true | 0..1 |
| `area_2014` | `xsd:double` | true | 0..1 |
| `area_2015` | `xsd:double` | true | 0..1 |
| `area_2016` | `xsd:double` | true | 0..1 |
| `area_2017` | `xsd:double` | true | 0..1 |
| `area_2018` | `xsd:double` | true | 0..1 |
| `colh_1989` | `xsd:double` | true | 0..1 |
| `colh_1990` | `xsd:double` | true | 0..1 |
| `colh_1991` | `xsd:double` | true | 0..1 |
| `colh_1992` | `xsd:double` | true | 0..1 |
| `colh_1993` | `xsd:double` | true | 0..1 |
| `colh_1994` | `xsd:double` | true | 0..1 |
| `colh_1995` | `xsd:double` | true | 0..1 |
| `colh_1996` | `xsd:double` | true | 0..1 |
| `colh_1997` | `xsd:double` | true | 0..1 |
| `colh_1998` | `xsd:double` | true | 0..1 |
| `colh_1999` | `xsd:double` | true | 0..1 |
| `colh_2000` | `xsd:double` | true | 0..1 |
| `colh_2001` | `xsd:double` | true | 0..1 |
| `colh_2002` | `xsd:double` | true | 0..1 |
| `colh_2003` | `xsd:double` | true | 0..1 |
| `colh_2004` | `xsd:double` | true | 0..1 |
| `colh_2005` | `xsd:double` | true | 0..1 |
| `colh_2006` | `xsd:double` | true | 0..1 |
| `colh_2007` | `xsd:double` | true | 0..1 |
| `colh_2008` | `xsd:double` | true | 0..1 |
| `colh_2009` | `xsd:double` | true | 0..1 |
| `colh_2010` | `xsd:double` | true | 0..1 |
| `colh_2011` | `xsd:double` | true | 0..1 |
| `colh_2012` | `xsd:double` | true | 0..1 |
| `colh_2013` | `xsd:double` | true | 0..1 |
| `colh_2014` | `xsd:double` | true | 0..1 |
| `colh_2015` | `xsd:double` | true | 0..1 |
| `colh_2016` | `xsd:double` | true | 0..1 |
| `colh_2017` | `xsd:double` | true | 0..1 |
| `colh_2018` | `xsd:double` | true | 0..1 |
| `prod_1989` | `xsd:double` | true | 0..1 |
| `prod_1990` | `xsd:double` | true | 0..1 |
| `prod_1991` | `xsd:double` | true | 0..1 |
| `prod_1992` | `xsd:double` | true | 0..1 |
| `prod_1993` | `xsd:double` | true | 0..1 |
| `prod_1994` | `xsd:double` | true | 0..1 |
| `prod_1995` | `xsd:double` | true | 0..1 |
| `prod_1996` | `xsd:double` | true | 0..1 |
| `prod_1997` | `xsd:double` | true | 0..1 |
| `prod_1998` | `xsd:double` | true | 0..1 |
| `prod_1999` | `xsd:double` | true | 0..1 |
| `prod_2000` | `xsd:double` | true | 0..1 |
| `prod_2001` | `xsd:double` | true | 0..1 |
| `prod_2002` | `xsd:double` | true | 0..1 |
| `prod_2003` | `xsd:double` | true | 0..1 |
| `prod_2004` | `xsd:double` | true | 0..1 |
| `prod_2005` | `xsd:double` | true | 0..1 |
| `prod_2006` | `xsd:double` | true | 0..1 |
| `prod_2007` | `xsd:double` | true | 0..1 |
| `prod_2008` | `xsd:double` | true | 0..1 |
| `prod_2009` | `xsd:double` | true | 0..1 |
| `prod_2010` | `xsd:double` | true | 0..1 |
| `prod_2011` | `xsd:double` | true | 0..1 |
| `prod_2012` | `xsd:double` | true | 0..1 |
| `prod_2013` | `xsd:double` | true | 0..1 |
| `prod_2014` | `xsd:double` | true | 0..1 |
| `prod_2015` | `xsd:double` | true | 0..1 |
| `prod_2016` | `xsd:double` | true | 0..1 |
| `prod_2017` | `xsd:double` | true | 0..1 |
| `prod_2018` | `xsd:double` | true | 0..1 |
| `rend_1989` | `xsd:double` | true | 0..1 |
| `rend_1990` | `xsd:double` | true | 0..1 |
| `rend_1991` | `xsd:double` | true | 0..1 |
| `rend_1992` | `xsd:double` | true | 0..1 |
| `rend_1993` | `xsd:double` | true | 0..1 |
| `rend_1994` | `xsd:double` | true | 0..1 |
| `rend_1995` | `xsd:double` | true | 0..1 |
| `rend_1996` | `xsd:double` | true | 0..1 |
| `rend_1997` | `xsd:double` | true | 0..1 |
| `rend_1998` | `xsd:double` | true | 0..1 |
| `rend_1999` | `xsd:double` | true | 0..1 |
| `rend_2000` | `xsd:double` | true | 0..1 |
| `rend_2001` | `xsd:double` | true | 0..1 |
| `rend_2002` | `xsd:double` | true | 0..1 |
| `rend_2003` | `xsd:double` | true | 0..1 |
| `rend_2004` | `xsd:double` | true | 0..1 |
| `rend_2005` | `xsd:double` | true | 0..1 |
| `rend_2006` | `xsd:double` | true | 0..1 |
| `rend_2007` | `xsd:double` | true | 0..1 |
| `rend_2008` | `xsd:double` | true | 0..1 |
| `rend_2009` | `xsd:double` | true | 0..1 |
| `rend_2010` | `xsd:double` | true | 0..1 |
| `rend_2011` | `xsd:double` | true | 0..1 |
| `rend_2012` | `xsd:double` | true | 0..1 |
| `rend_2013` | `xsd:double` | true | 0..1 |
| `rend_2014` | `xsd:double` | true | 0..1 |
| `rend_2015` | `xsd:double` | true | 0..1 |
| `rend_2016` | `xsd:double` | true | 0..1 |
| `rend_2017` | `xsd:double` | true | 0..1 |
| `rend_2018` | `xsd:double` | true | 0..1 |

### `estatistica:lavoura_temporaria_melancia_1989_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `nume_cid` | `xsd:string` | true | 0..1 |
| `pgai` | `xsd:string` | true | 0..1 |
| `tipo_cidd` | `xsd:string` | true | 0..1 |
| `regiao_num` | `xsd:string` | true | 0..1 |
| `territ_cid` | `xsd:string` | true | 0..1 |
| `utr` | `xsd:string` | true | 0..1 |
| `criacao` | `xsd:string` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `pop_1996` | `xsd:double` | true | 0..1 |
| `pop_2000` | `xsd:double` | true | 0..1 |
| `pop_2007` | `xsd:double` | true | 0..1 |
| `pop_2008` | `xsd:double` | true | 0..1 |
| `pop_2009` | `xsd:double` | true | 0..1 |
| `assoc_mun` | `xsd:string` | true | 0..1 |
| `reg_pm` | `xsd:string` | true | 0..1 |
| `art_pm` | `xsd:string` | true | 0..1 |
| `region_ibg` | `xsd:string` | true | 0..1 |
| `cod_region` | `xsd:double` | true | 0..1 |
| `pop_2010` | `xsd:double` | true | 0..1 |
| `ppa_2012_2` | `xsd:string` | true | 0..1 |
| `number` | `xsd:double` | true | 0..1 |
| `regionaliz` | `xsd:string` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `reg_tur` | `xsd:string` | true | 0..1 |
| `nova_regio` | `xsd:string` | true | 0..1 |
| `nova_reg_o` | `xsd:string` | true | 0..1 |
| `cultura` | `xsd:string` | true | 0..1 |
| `area_1989` | `xsd:double` | true | 0..1 |
| `area_1990` | `xsd:double` | true | 0..1 |
| `area_1991` | `xsd:double` | true | 0..1 |
| `area_1992` | `xsd:double` | true | 0..1 |
| `area_1993` | `xsd:double` | true | 0..1 |
| `area_1994` | `xsd:double` | true | 0..1 |
| `area_1995` | `xsd:double` | true | 0..1 |
| `area_1996` | `xsd:double` | true | 0..1 |
| `area_1997` | `xsd:double` | true | 0..1 |
| `area_1998` | `xsd:double` | true | 0..1 |
| `area_1999` | `xsd:double` | true | 0..1 |
| `area_2000` | `xsd:double` | true | 0..1 |
| `area_2001` | `xsd:double` | true | 0..1 |
| `area_2002` | `xsd:double` | true | 0..1 |
| `area_2003` | `xsd:double` | true | 0..1 |
| `area_2004` | `xsd:double` | true | 0..1 |
| `area_2005` | `xsd:double` | true | 0..1 |
| `area_2006` | `xsd:double` | true | 0..1 |
| `area_2007` | `xsd:double` | true | 0..1 |
| `area_2008` | `xsd:double` | true | 0..1 |
| `area_2009` | `xsd:double` | true | 0..1 |
| `area_2010` | `xsd:double` | true | 0..1 |
| `area_2011` | `xsd:double` | true | 0..1 |
| `area_2012` | `xsd:double` | true | 0..1 |
| `area_2013` | `xsd:double` | true | 0..1 |
| `area_2014` | `xsd:double` | true | 0..1 |
| `area_2015` | `xsd:double` | true | 0..1 |
| `area_2016` | `xsd:double` | true | 0..1 |
| `area_2017` | `xsd:double` | true | 0..1 |
| `area_2018` | `xsd:double` | true | 0..1 |
| `colh_1989` | `xsd:double` | true | 0..1 |
| `colh_1990` | `xsd:double` | true | 0..1 |
| `colh_1991` | `xsd:double` | true | 0..1 |
| `colh_1992` | `xsd:double` | true | 0..1 |
| `colh_1993` | `xsd:double` | true | 0..1 |
| `colh_1994` | `xsd:double` | true | 0..1 |
| `colh_1995` | `xsd:double` | true | 0..1 |
| `colh_1996` | `xsd:double` | true | 0..1 |
| `colh_1997` | `xsd:double` | true | 0..1 |
| `colh_1998` | `xsd:double` | true | 0..1 |
| `colh_1999` | `xsd:double` | true | 0..1 |
| `colh_2000` | `xsd:double` | true | 0..1 |
| `colh_2001` | `xsd:double` | true | 0..1 |
| `colh_2002` | `xsd:double` | true | 0..1 |
| `colh_2003` | `xsd:double` | true | 0..1 |
| `colh_2004` | `xsd:double` | true | 0..1 |
| `colh_2005` | `xsd:double` | true | 0..1 |
| `colh_2006` | `xsd:double` | true | 0..1 |
| `colh_2007` | `xsd:double` | true | 0..1 |
| `colh_2008` | `xsd:double` | true | 0..1 |
| `colh_2009` | `xsd:double` | true | 0..1 |
| `colh_2010` | `xsd:double` | true | 0..1 |
| `colh_2011` | `xsd:double` | true | 0..1 |
| `colh_2012` | `xsd:double` | true | 0..1 |
| `colh_2013` | `xsd:double` | true | 0..1 |
| `colh_2014` | `xsd:double` | true | 0..1 |
| `colh_2015` | `xsd:double` | true | 0..1 |
| `colh_2016` | `xsd:double` | true | 0..1 |
| `colh_2017` | `xsd:double` | true | 0..1 |
| `colh_2018` | `xsd:double` | true | 0..1 |
| `prod_1989` | `xsd:double` | true | 0..1 |
| `prod_1990` | `xsd:double` | true | 0..1 |
| `prod_1991` | `xsd:double` | true | 0..1 |
| `prod_1992` | `xsd:double` | true | 0..1 |
| `prod_1993` | `xsd:double` | true | 0..1 |
| `prod_1994` | `xsd:double` | true | 0..1 |
| `prod_1995` | `xsd:double` | true | 0..1 |
| `prod_1996` | `xsd:double` | true | 0..1 |
| `prod_1997` | `xsd:double` | true | 0..1 |
| `prod_1998` | `xsd:double` | true | 0..1 |
| `prod_1999` | `xsd:double` | true | 0..1 |
| `prod_2000` | `xsd:double` | true | 0..1 |
| `prod_2001` | `xsd:double` | true | 0..1 |
| `prod_2002` | `xsd:double` | true | 0..1 |
| `prod_2003` | `xsd:double` | true | 0..1 |
| `prod_2004` | `xsd:double` | true | 0..1 |
| `prod_2005` | `xsd:double` | true | 0..1 |
| `prod_2006` | `xsd:double` | true | 0..1 |
| `prod_2007` | `xsd:double` | true | 0..1 |
| `prod_2008` | `xsd:double` | true | 0..1 |
| `prod_2009` | `xsd:double` | true | 0..1 |
| `prod_2010` | `xsd:double` | true | 0..1 |
| `prod_2011` | `xsd:double` | true | 0..1 |
| `prod_2012` | `xsd:double` | true | 0..1 |
| `prod_2013` | `xsd:double` | true | 0..1 |
| `prod_2014` | `xsd:double` | true | 0..1 |
| `prod_2015` | `xsd:double` | true | 0..1 |
| `prod_2016` | `xsd:double` | true | 0..1 |
| `prod_2017` | `xsd:double` | true | 0..1 |
| `prod_2018` | `xsd:double` | true | 0..1 |

### `estatistica:lavoura_temporaria_melao_1989_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `nume_cid` | `xsd:string` | true | 0..1 |
| `pgai` | `xsd:string` | true | 0..1 |
| `tipo_cidd` | `xsd:string` | true | 0..1 |
| `regiao_num` | `xsd:string` | true | 0..1 |
| `territ_cid` | `xsd:string` | true | 0..1 |
| `utr` | `xsd:string` | true | 0..1 |
| `criacao` | `xsd:string` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `pop_1996` | `xsd:double` | true | 0..1 |
| `pop_2000` | `xsd:double` | true | 0..1 |
| `pop_2007` | `xsd:double` | true | 0..1 |
| `pop_2008` | `xsd:double` | true | 0..1 |
| `pop_2009` | `xsd:double` | true | 0..1 |
| `assoc_mun` | `xsd:string` | true | 0..1 |
| `reg_pm` | `xsd:string` | true | 0..1 |
| `art_pm` | `xsd:string` | true | 0..1 |
| `region_ibg` | `xsd:string` | true | 0..1 |
| `cod_region` | `xsd:double` | true | 0..1 |
| `pop_2010` | `xsd:double` | true | 0..1 |
| `ppa_2012_2` | `xsd:string` | true | 0..1 |
| `number` | `xsd:double` | true | 0..1 |
| `regionaliz` | `xsd:string` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `reg_tur` | `xsd:string` | true | 0..1 |
| `nova_regio` | `xsd:string` | true | 0..1 |
| `nova_reg_o` | `xsd:string` | true | 0..1 |
| `cultura` | `xsd:string` | true | 0..1 |
| `area_1989` | `xsd:double` | true | 0..1 |
| `area_1990` | `xsd:double` | true | 0..1 |
| `area_1991` | `xsd:double` | true | 0..1 |
| `area_1992` | `xsd:double` | true | 0..1 |
| `area_1993` | `xsd:double` | true | 0..1 |
| `area_1994` | `xsd:double` | true | 0..1 |
| `area_1995` | `xsd:double` | true | 0..1 |
| `area_1996` | `xsd:double` | true | 0..1 |
| `area_1997` | `xsd:double` | true | 0..1 |
| `area_1998` | `xsd:double` | true | 0..1 |
| `area_1999` | `xsd:double` | true | 0..1 |
| `area_2000` | `xsd:double` | true | 0..1 |
| `area_2001` | `xsd:double` | true | 0..1 |
| `area_2002` | `xsd:double` | true | 0..1 |
| `area_2003` | `xsd:double` | true | 0..1 |
| `area_2004` | `xsd:double` | true | 0..1 |
| `area_2005` | `xsd:double` | true | 0..1 |
| `area_2006` | `xsd:double` | true | 0..1 |
| `area_2007` | `xsd:double` | true | 0..1 |
| `area_2008` | `xsd:double` | true | 0..1 |
| `area_2009` | `xsd:double` | true | 0..1 |
| `area_2010` | `xsd:double` | true | 0..1 |
| `area_2011` | `xsd:double` | true | 0..1 |
| `area_2012` | `xsd:double` | true | 0..1 |
| `area_2013` | `xsd:double` | true | 0..1 |
| `area_2014` | `xsd:double` | true | 0..1 |
| `area_2015` | `xsd:double` | true | 0..1 |
| `area_2016` | `xsd:double` | true | 0..1 |
| `area_2017` | `xsd:double` | true | 0..1 |
| `area_2018` | `xsd:double` | true | 0..1 |
| `colh_1989` | `xsd:double` | true | 0..1 |
| `colh_1990` | `xsd:double` | true | 0..1 |
| `colh_1991` | `xsd:double` | true | 0..1 |
| `colh_1992` | `xsd:double` | true | 0..1 |
| `colh_1993` | `xsd:double` | true | 0..1 |
| `colh_1994` | `xsd:double` | true | 0..1 |
| `colh_1995` | `xsd:double` | true | 0..1 |
| `colh_1996` | `xsd:double` | true | 0..1 |
| `colh_1997` | `xsd:double` | true | 0..1 |
| `colh_1998` | `xsd:double` | true | 0..1 |
| `colh_1999` | `xsd:double` | true | 0..1 |
| `colh_2000` | `xsd:double` | true | 0..1 |
| `colh_2001` | `xsd:double` | true | 0..1 |
| `colh_2002` | `xsd:double` | true | 0..1 |
| `colh_2003` | `xsd:double` | true | 0..1 |
| `colh_2004` | `xsd:double` | true | 0..1 |
| `colh_2005` | `xsd:double` | true | 0..1 |
| `colh_2006` | `xsd:double` | true | 0..1 |
| `colh_2007` | `xsd:double` | true | 0..1 |
| `colh_2008` | `xsd:double` | true | 0..1 |
| `colh_2009` | `xsd:double` | true | 0..1 |
| `colh_2010` | `xsd:double` | true | 0..1 |
| `colh_2011` | `xsd:double` | true | 0..1 |
| `colh_2012` | `xsd:double` | true | 0..1 |
| `colh_2013` | `xsd:double` | true | 0..1 |
| `colh_2014` | `xsd:double` | true | 0..1 |
| `colh_2015` | `xsd:double` | true | 0..1 |
| `colh_2016` | `xsd:double` | true | 0..1 |
| `colh_2017` | `xsd:double` | true | 0..1 |
| `colh_2018` | `xsd:double` | true | 0..1 |
| `prod_1989` | `xsd:double` | true | 0..1 |
| `prod_1990` | `xsd:double` | true | 0..1 |
| `prod_1991` | `xsd:double` | true | 0..1 |
| `prod_1992` | `xsd:double` | true | 0..1 |
| `prod_1993` | `xsd:double` | true | 0..1 |
| `prod_1994` | `xsd:double` | true | 0..1 |
| `prod_1995` | `xsd:double` | true | 0..1 |
| `prod_1996` | `xsd:double` | true | 0..1 |
| `prod_1997` | `xsd:double` | true | 0..1 |
| `prod_1998` | `xsd:double` | true | 0..1 |
| `prod_1999` | `xsd:double` | true | 0..1 |
| `prod_2000` | `xsd:double` | true | 0..1 |
| `prod_2001` | `xsd:double` | true | 0..1 |
| `prod_2002` | `xsd:double` | true | 0..1 |
| `prod_2003` | `xsd:double` | true | 0..1 |
| `prod_2004` | `xsd:double` | true | 0..1 |
| `prod_2005` | `xsd:double` | true | 0..1 |
| `prod_2006` | `xsd:double` | true | 0..1 |
| `prod_2007` | `xsd:double` | true | 0..1 |
| `prod_2008` | `xsd:double` | true | 0..1 |
| `prod_2009` | `xsd:double` | true | 0..1 |
| `prod_2010` | `xsd:double` | true | 0..1 |
| `prod_2011` | `xsd:double` | true | 0..1 |
| `prod_2012` | `xsd:double` | true | 0..1 |
| `prod_2013` | `xsd:double` | true | 0..1 |
| `prod_2014` | `xsd:double` | true | 0..1 |
| `prod_2015` | `xsd:double` | true | 0..1 |
| `prod_2016` | `xsd:double` | true | 0..1 |
| `prod_2017` | `xsd:double` | true | 0..1 |
| `prod_2018` | `xsd:double` | true | 0..1 |
| `rend_1989` | `xsd:double` | true | 0..1 |
| `rend_1990` | `xsd:double` | true | 0..1 |
| `rend_1991` | `xsd:double` | true | 0..1 |
| `rend_1992` | `xsd:double` | true | 0..1 |
| `rend_1993` | `xsd:double` | true | 0..1 |
| `rend_1994` | `xsd:double` | true | 0..1 |
| `rend_1995` | `xsd:double` | true | 0..1 |
| `rend_1996` | `xsd:double` | true | 0..1 |
| `rend_1997` | `xsd:double` | true | 0..1 |
| `rend_1998` | `xsd:double` | true | 0..1 |
| `rend_1999` | `xsd:double` | true | 0..1 |
| `rend_2000` | `xsd:double` | true | 0..1 |
| `rend_2001` | `xsd:double` | true | 0..1 |
| `rend_2002` | `xsd:double` | true | 0..1 |
| `rend_2003` | `xsd:double` | true | 0..1 |
| `rend_2004` | `xsd:double` | true | 0..1 |
| `rend_2005` | `xsd:double` | true | 0..1 |
| `rend_2006` | `xsd:double` | true | 0..1 |
| `rend_2007` | `xsd:double` | true | 0..1 |
| `rend_2008` | `xsd:double` | true | 0..1 |
| `rend_2009` | `xsd:double` | true | 0..1 |
| `rend_2010` | `xsd:double` | true | 0..1 |
| `rend_2011` | `xsd:double` | true | 0..1 |
| `rend_2012` | `xsd:double` | true | 0..1 |
| `rend_2013` | `xsd:double` | true | 0..1 |
| `rend_2014` | `xsd:double` | true | 0..1 |
| `rend_2015` | `xsd:double` | true | 0..1 |
| `rend_2016` | `xsd:double` | true | 0..1 |
| `rend_2017` | `xsd:double` | true | 0..1 |
| `rend_2018` | `xsd:double` | true | 0..1 |

### `estatistica:lavoura_temporaria_milho_1989_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `nume_cid` | `xsd:string` | true | 0..1 |
| `pgai` | `xsd:string` | true | 0..1 |
| `tipo_cidd` | `xsd:string` | true | 0..1 |
| `regiao_num` | `xsd:string` | true | 0..1 |
| `territ_cid` | `xsd:string` | true | 0..1 |
| `utr` | `xsd:string` | true | 0..1 |
| `criacao` | `xsd:string` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `pop_1996` | `xsd:double` | true | 0..1 |
| `pop_2000` | `xsd:double` | true | 0..1 |
| `pop_2007` | `xsd:double` | true | 0..1 |
| `pop_2008` | `xsd:double` | true | 0..1 |
| `pop_2009` | `xsd:double` | true | 0..1 |
| `assoc_mun` | `xsd:string` | true | 0..1 |
| `reg_pm` | `xsd:string` | true | 0..1 |
| `art_pm` | `xsd:string` | true | 0..1 |
| `region_ibg` | `xsd:string` | true | 0..1 |
| `cod_region` | `xsd:double` | true | 0..1 |
| `pop_2010` | `xsd:double` | true | 0..1 |
| `ppa_2012_2` | `xsd:string` | true | 0..1 |
| `number` | `xsd:double` | true | 0..1 |
| `regionaliz` | `xsd:string` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `reg_tur` | `xsd:string` | true | 0..1 |
| `nova_regio` | `xsd:string` | true | 0..1 |
| `nova_reg_o` | `xsd:string` | true | 0..1 |
| `cultura` | `xsd:string` | true | 0..1 |
| `area_1989` | `xsd:double` | true | 0..1 |
| `area_1990` | `xsd:double` | true | 0..1 |
| `area_1991` | `xsd:double` | true | 0..1 |
| `area_1992` | `xsd:double` | true | 0..1 |
| `area_1993` | `xsd:double` | true | 0..1 |
| `area_1994` | `xsd:double` | true | 0..1 |
| `area_1995` | `xsd:double` | true | 0..1 |
| `area_1996` | `xsd:double` | true | 0..1 |
| `area_1997` | `xsd:double` | true | 0..1 |
| `area_1998` | `xsd:double` | true | 0..1 |
| `area_1999` | `xsd:double` | true | 0..1 |
| `area_2000` | `xsd:double` | true | 0..1 |
| `area_2001` | `xsd:double` | true | 0..1 |
| `area_2002` | `xsd:double` | true | 0..1 |
| `area_2003` | `xsd:double` | true | 0..1 |
| `area_2004` | `xsd:double` | true | 0..1 |
| `area_2005` | `xsd:double` | true | 0..1 |
| `area_2006` | `xsd:double` | true | 0..1 |
| `area_2007` | `xsd:double` | true | 0..1 |
| `area_2008` | `xsd:double` | true | 0..1 |
| `area_2009` | `xsd:double` | true | 0..1 |
| `area_2010` | `xsd:double` | true | 0..1 |
| `area_2011` | `xsd:double` | true | 0..1 |
| `area_2012` | `xsd:double` | true | 0..1 |
| `area_2013` | `xsd:double` | true | 0..1 |
| `area_2014` | `xsd:double` | true | 0..1 |
| `area_2015` | `xsd:double` | true | 0..1 |
| `area_2016` | `xsd:double` | true | 0..1 |
| `area_2017` | `xsd:double` | true | 0..1 |
| `area_2018` | `xsd:double` | true | 0..1 |
| `colh_1989` | `xsd:double` | true | 0..1 |
| `colh_1990` | `xsd:double` | true | 0..1 |
| `colh_1991` | `xsd:double` | true | 0..1 |
| `colh_1992` | `xsd:double` | true | 0..1 |
| `colh_1993` | `xsd:double` | true | 0..1 |
| `colh_1994` | `xsd:double` | true | 0..1 |
| `colh_1995` | `xsd:double` | true | 0..1 |
| `colh_1996` | `xsd:double` | true | 0..1 |
| `colh_1997` | `xsd:double` | true | 0..1 |
| `colh_1998` | `xsd:double` | true | 0..1 |
| `colh_1999` | `xsd:double` | true | 0..1 |
| `colh_2000` | `xsd:double` | true | 0..1 |
| `colh_2001` | `xsd:double` | true | 0..1 |
| `colh_2002` | `xsd:double` | true | 0..1 |
| `colh_2003` | `xsd:double` | true | 0..1 |
| `colh_2004` | `xsd:double` | true | 0..1 |
| `colh_2005` | `xsd:double` | true | 0..1 |
| `colh_2006` | `xsd:double` | true | 0..1 |
| `colh_2007` | `xsd:double` | true | 0..1 |
| `colh_2008` | `xsd:double` | true | 0..1 |
| `colh_2009` | `xsd:double` | true | 0..1 |
| `colh_2010` | `xsd:double` | true | 0..1 |
| `colh_2011` | `xsd:double` | true | 0..1 |
| `colh_2012` | `xsd:double` | true | 0..1 |
| `colh_2013` | `xsd:double` | true | 0..1 |
| `colh_2014` | `xsd:double` | true | 0..1 |
| `colh_2015` | `xsd:double` | true | 0..1 |
| `colh_2016` | `xsd:double` | true | 0..1 |
| `colh_2017` | `xsd:double` | true | 0..1 |
| `colh_2018` | `xsd:double` | true | 0..1 |
| `prod_1989` | `xsd:double` | true | 0..1 |
| `prod_1990` | `xsd:double` | true | 0..1 |
| `prod_1991` | `xsd:double` | true | 0..1 |
| `prod_1992` | `xsd:double` | true | 0..1 |
| `prod_1993` | `xsd:double` | true | 0..1 |
| `prod_1994` | `xsd:double` | true | 0..1 |
| `prod_1995` | `xsd:double` | true | 0..1 |
| `prod_1996` | `xsd:double` | true | 0..1 |
| `prod_1997` | `xsd:double` | true | 0..1 |
| `prod_1998` | `xsd:double` | true | 0..1 |
| `prod_1999` | `xsd:double` | true | 0..1 |
| `prod_2000` | `xsd:double` | true | 0..1 |
| `prod_2001` | `xsd:double` | true | 0..1 |
| `prod_2002` | `xsd:double` | true | 0..1 |
| `prod_2003` | `xsd:double` | true | 0..1 |
| `prod_2004` | `xsd:double` | true | 0..1 |
| `prod_2005` | `xsd:double` | true | 0..1 |
| `prod_2006` | `xsd:double` | true | 0..1 |
| `prod_2007` | `xsd:double` | true | 0..1 |
| `prod_2008` | `xsd:double` | true | 0..1 |
| `prod_2009` | `xsd:double` | true | 0..1 |
| `prod_2010` | `xsd:double` | true | 0..1 |
| `prod_2011` | `xsd:double` | true | 0..1 |
| `prod_2012` | `xsd:double` | true | 0..1 |
| `prod_2013` | `xsd:double` | true | 0..1 |
| `prod_2014` | `xsd:double` | true | 0..1 |
| `prod_2015` | `xsd:double` | true | 0..1 |
| `prod_2016` | `xsd:double` | true | 0..1 |
| `prod_2017` | `xsd:double` | true | 0..1 |
| `prod_2018` | `xsd:double` | true | 0..1 |
| `rend_1989` | `xsd:double` | true | 0..1 |
| `rend_1990` | `xsd:double` | true | 0..1 |
| `rend_1991` | `xsd:double` | true | 0..1 |
| `rend_1992` | `xsd:double` | true | 0..1 |
| `rend_1993` | `xsd:double` | true | 0..1 |
| `rend_1994` | `xsd:double` | true | 0..1 |
| `rend_1995` | `xsd:double` | true | 0..1 |
| `rend_1996` | `xsd:double` | true | 0..1 |
| `rend_1997` | `xsd:double` | true | 0..1 |
| `rend_1998` | `xsd:double` | true | 0..1 |
| `rend_1999` | `xsd:double` | true | 0..1 |
| `rend_2000` | `xsd:double` | true | 0..1 |
| `rend_2001` | `xsd:double` | true | 0..1 |
| `rend_2002` | `xsd:double` | true | 0..1 |
| `rend_2003` | `xsd:double` | true | 0..1 |
| `rend_2004` | `xsd:double` | true | 0..1 |
| `rend_2005` | `xsd:double` | true | 0..1 |
| `rend_2006` | `xsd:double` | true | 0..1 |
| `rend_2007` | `xsd:double` | true | 0..1 |
| `rend_2008` | `xsd:double` | true | 0..1 |
| `rend_2009` | `xsd:double` | true | 0..1 |
| `rend_2010` | `xsd:double` | true | 0..1 |
| `rend_2011` | `xsd:double` | true | 0..1 |
| `rend_2012` | `xsd:double` | true | 0..1 |
| `rend_2013` | `xsd:double` | true | 0..1 |
| `rend_2014` | `xsd:double` | true | 0..1 |
| `rend_2015` | `xsd:double` | true | 0..1 |
| `rend_2016` | `xsd:double` | true | 0..1 |
| `rend_2017` | `xsd:double` | true | 0..1 |
| `rend_2018` | `xsd:double` | true | 0..1 |

### `estatistica:lavoura_temporaria_soja_1989_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `nume_cid` | `xsd:string` | true | 0..1 |
| `pgai` | `xsd:string` | true | 0..1 |
| `tipo_cidd` | `xsd:string` | true | 0..1 |
| `regiao_num` | `xsd:string` | true | 0..1 |
| `territ_cid` | `xsd:string` | true | 0..1 |
| `utr` | `xsd:string` | true | 0..1 |
| `criacao` | `xsd:string` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `pop_1996` | `xsd:double` | true | 0..1 |
| `pop_2000` | `xsd:double` | true | 0..1 |
| `pop_2007` | `xsd:double` | true | 0..1 |
| `pop_2008` | `xsd:double` | true | 0..1 |
| `pop_2009` | `xsd:double` | true | 0..1 |
| `assoc_mun` | `xsd:string` | true | 0..1 |
| `reg_pm` | `xsd:string` | true | 0..1 |
| `art_pm` | `xsd:string` | true | 0..1 |
| `region_ibg` | `xsd:string` | true | 0..1 |
| `cod_region` | `xsd:double` | true | 0..1 |
| `pop_2010` | `xsd:double` | true | 0..1 |
| `ppa_2012_2` | `xsd:string` | true | 0..1 |
| `number` | `xsd:double` | true | 0..1 |
| `regionaliz` | `xsd:string` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `reg_tur` | `xsd:string` | true | 0..1 |
| `nova_regio` | `xsd:string` | true | 0..1 |
| `nova_reg_o` | `xsd:string` | true | 0..1 |
| `cultura` | `xsd:string` | true | 0..1 |
| `area_1989` | `xsd:double` | true | 0..1 |
| `area_1990` | `xsd:double` | true | 0..1 |
| `area_1991` | `xsd:double` | true | 0..1 |
| `area_1992` | `xsd:double` | true | 0..1 |
| `area_1993` | `xsd:double` | true | 0..1 |
| `area_1994` | `xsd:double` | true | 0..1 |
| `area_1995` | `xsd:double` | true | 0..1 |
| `area_1996` | `xsd:double` | true | 0..1 |
| `area_1997` | `xsd:double` | true | 0..1 |
| `area_1998` | `xsd:double` | true | 0..1 |
| `area_1999` | `xsd:double` | true | 0..1 |
| `area_2000` | `xsd:double` | true | 0..1 |
| `area_2001` | `xsd:double` | true | 0..1 |
| `area_2002` | `xsd:double` | true | 0..1 |
| `area_2003` | `xsd:double` | true | 0..1 |
| `area_2004` | `xsd:double` | true | 0..1 |
| `area_2005` | `xsd:double` | true | 0..1 |
| `area_2006` | `xsd:double` | true | 0..1 |
| `area_2007` | `xsd:double` | true | 0..1 |
| `area_2008` | `xsd:double` | true | 0..1 |
| `area_2009` | `xsd:double` | true | 0..1 |
| `area_2010` | `xsd:double` | true | 0..1 |
| `area_2011` | `xsd:double` | true | 0..1 |
| `area_2012` | `xsd:double` | true | 0..1 |
| `area_2013` | `xsd:double` | true | 0..1 |
| `area_2014` | `xsd:double` | true | 0..1 |
| `area_2015` | `xsd:double` | true | 0..1 |
| `area_2016` | `xsd:double` | true | 0..1 |
| `area_2017` | `xsd:double` | true | 0..1 |
| `area_2018` | `xsd:double` | true | 0..1 |
| `colh_1989` | `xsd:double` | true | 0..1 |
| `colh_1990` | `xsd:double` | true | 0..1 |
| `colh_1991` | `xsd:double` | true | 0..1 |
| `colh_1992` | `xsd:double` | true | 0..1 |
| `colh_1993` | `xsd:double` | true | 0..1 |
| `colh_1994` | `xsd:double` | true | 0..1 |
| `colh_1995` | `xsd:double` | true | 0..1 |
| `colh_1996` | `xsd:double` | true | 0..1 |
| `colh_1997` | `xsd:double` | true | 0..1 |
| `colh_1998` | `xsd:double` | true | 0..1 |
| `colh_1999` | `xsd:double` | true | 0..1 |
| `colh_2000` | `xsd:double` | true | 0..1 |
| `colh_2001` | `xsd:double` | true | 0..1 |
| `colh_2002` | `xsd:double` | true | 0..1 |
| `colh_2003` | `xsd:double` | true | 0..1 |
| `colh_2004` | `xsd:double` | true | 0..1 |
| `colh_2005` | `xsd:double` | true | 0..1 |
| `colh_2006` | `xsd:double` | true | 0..1 |
| `colh_2007` | `xsd:double` | true | 0..1 |
| `colh_2008` | `xsd:double` | true | 0..1 |
| `colh_2009` | `xsd:double` | true | 0..1 |
| `colh_2010` | `xsd:double` | true | 0..1 |
| `colh_2011` | `xsd:double` | true | 0..1 |
| `colh_2012` | `xsd:double` | true | 0..1 |
| `colh_2013` | `xsd:double` | true | 0..1 |
| `colh_2014` | `xsd:double` | true | 0..1 |
| `colh_2015` | `xsd:double` | true | 0..1 |
| `colh_2016` | `xsd:double` | true | 0..1 |
| `colh_2017` | `xsd:double` | true | 0..1 |
| `colh_2018` | `xsd:double` | true | 0..1 |
| `prod_1989` | `xsd:double` | true | 0..1 |
| `prod_1990` | `xsd:double` | true | 0..1 |
| `prod_1991` | `xsd:double` | true | 0..1 |
| `prod_1992` | `xsd:double` | true | 0..1 |
| `prod_1993` | `xsd:double` | true | 0..1 |
| `prod_1994` | `xsd:double` | true | 0..1 |
| `prod_1995` | `xsd:double` | true | 0..1 |
| `prod_1996` | `xsd:double` | true | 0..1 |
| `prod_1997` | `xsd:double` | true | 0..1 |
| `prod_1998` | `xsd:double` | true | 0..1 |
| `prod_1999` | `xsd:double` | true | 0..1 |
| `prod_2000` | `xsd:double` | true | 0..1 |
| `prod_2001` | `xsd:double` | true | 0..1 |
| `prod_2002` | `xsd:double` | true | 0..1 |
| `prod_2003` | `xsd:double` | true | 0..1 |
| `prod_2004` | `xsd:double` | true | 0..1 |
| `prod_2005` | `xsd:double` | true | 0..1 |
| `prod_2006` | `xsd:double` | true | 0..1 |
| `prod_2007` | `xsd:double` | true | 0..1 |
| `prod_2008` | `xsd:double` | true | 0..1 |
| `prod_2009` | `xsd:double` | true | 0..1 |
| `prod_2010` | `xsd:double` | true | 0..1 |
| `prod_2011` | `xsd:double` | true | 0..1 |
| `prod_2012` | `xsd:double` | true | 0..1 |
| `prod_2013` | `xsd:double` | true | 0..1 |
| `prod_2014` | `xsd:double` | true | 0..1 |
| `prod_2015` | `xsd:double` | true | 0..1 |
| `prod_2016` | `xsd:double` | true | 0..1 |
| `prod_2017` | `xsd:double` | true | 0..1 |
| `prod_2018` | `xsd:double` | true | 0..1 |
| `rend_1989` | `xsd:double` | true | 0..1 |
| `rend_1990` | `xsd:double` | true | 0..1 |
| `rend_1991` | `xsd:double` | true | 0..1 |
| `rend_1992` | `xsd:double` | true | 0..1 |
| `rend_1993` | `xsd:double` | true | 0..1 |
| `rend_1994` | `xsd:double` | true | 0..1 |
| `rend_1995` | `xsd:double` | true | 0..1 |
| `rend_1996` | `xsd:double` | true | 0..1 |
| `rend_1997` | `xsd:double` | true | 0..1 |
| `rend_1998` | `xsd:double` | true | 0..1 |
| `rend_1999` | `xsd:double` | true | 0..1 |
| `rend_2000` | `xsd:double` | true | 0..1 |
| `rend_2001` | `xsd:double` | true | 0..1 |
| `rend_2002` | `xsd:double` | true | 0..1 |
| `rend_2003` | `xsd:double` | true | 0..1 |
| `rend_2004` | `xsd:double` | true | 0..1 |
| `rend_2005` | `xsd:double` | true | 0..1 |
| `rend_2006` | `xsd:double` | true | 0..1 |
| `rend_2007` | `xsd:double` | true | 0..1 |
| `rend_2008` | `xsd:double` | true | 0..1 |
| `rend_2009` | `xsd:double` | true | 0..1 |
| `rend_2010` | `xsd:double` | true | 0..1 |
| `rend_2011` | `xsd:double` | true | 0..1 |
| `rend_2012` | `xsd:double` | true | 0..1 |
| `rend_2013` | `xsd:double` | true | 0..1 |
| `rend_2014` | `xsd:double` | true | 0..1 |
| `rend_2015` | `xsd:double` | true | 0..1 |
| `rend_2016` | `xsd:double` | true | 0..1 |
| `rend_2017` | `xsd:double` | true | 0..1 |
| `rend_2018` | `xsd:double` | true | 0..1 |

### `estatistica:lavoura_temporaria_sorgo_1989_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `nume_cid` | `xsd:string` | true | 0..1 |
| `pgai` | `xsd:string` | true | 0..1 |
| `tipo_cidd` | `xsd:string` | true | 0..1 |
| `regiao_num` | `xsd:string` | true | 0..1 |
| `territ_cid` | `xsd:string` | true | 0..1 |
| `utr` | `xsd:string` | true | 0..1 |
| `criacao` | `xsd:string` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `pop_1996` | `xsd:double` | true | 0..1 |
| `pop_2000` | `xsd:double` | true | 0..1 |
| `pop_2007` | `xsd:double` | true | 0..1 |
| `pop_2008` | `xsd:double` | true | 0..1 |
| `pop_2009` | `xsd:double` | true | 0..1 |
| `assoc_mun` | `xsd:string` | true | 0..1 |
| `reg_pm` | `xsd:string` | true | 0..1 |
| `art_pm` | `xsd:string` | true | 0..1 |
| `region_ibg` | `xsd:string` | true | 0..1 |
| `cod_region` | `xsd:double` | true | 0..1 |
| `pop_2010` | `xsd:double` | true | 0..1 |
| `ppa_2012_2` | `xsd:string` | true | 0..1 |
| `number` | `xsd:double` | true | 0..1 |
| `regionaliz` | `xsd:string` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `reg_tur` | `xsd:string` | true | 0..1 |
| `nova_regio` | `xsd:string` | true | 0..1 |
| `nova_reg_o` | `xsd:string` | true | 0..1 |
| `cultura` | `xsd:string` | true | 0..1 |
| `area_1989` | `xsd:double` | true | 0..1 |
| `area_1990` | `xsd:double` | true | 0..1 |
| `area_1991` | `xsd:double` | true | 0..1 |
| `area_1992` | `xsd:double` | true | 0..1 |
| `area_1993` | `xsd:double` | true | 0..1 |
| `area_1994` | `xsd:double` | true | 0..1 |
| `area_1995` | `xsd:double` | true | 0..1 |
| `area_1996` | `xsd:double` | true | 0..1 |
| `area_1997` | `xsd:double` | true | 0..1 |
| `area_1998` | `xsd:double` | true | 0..1 |
| `area_1999` | `xsd:double` | true | 0..1 |
| `area_2000` | `xsd:double` | true | 0..1 |
| `area_2001` | `xsd:double` | true | 0..1 |
| `area_2002` | `xsd:double` | true | 0..1 |
| `area_2003` | `xsd:double` | true | 0..1 |
| `area_2004` | `xsd:double` | true | 0..1 |
| `area_2005` | `xsd:double` | true | 0..1 |
| `area_2006` | `xsd:double` | true | 0..1 |
| `area_2007` | `xsd:double` | true | 0..1 |
| `area_2008` | `xsd:double` | true | 0..1 |
| `area_2009` | `xsd:double` | true | 0..1 |
| `area_2010` | `xsd:double` | true | 0..1 |
| `area_2011` | `xsd:double` | true | 0..1 |
| `area_2012` | `xsd:double` | true | 0..1 |
| `area_2013` | `xsd:double` | true | 0..1 |
| `area_2014` | `xsd:double` | true | 0..1 |
| `area_2015` | `xsd:double` | true | 0..1 |
| `area_2016` | `xsd:double` | true | 0..1 |
| `area_2017` | `xsd:double` | true | 0..1 |
| `area_2018` | `xsd:double` | true | 0..1 |
| `colh_1989` | `xsd:double` | true | 0..1 |
| `colh_1990` | `xsd:double` | true | 0..1 |
| `colh_1991` | `xsd:double` | true | 0..1 |
| `colh_1992` | `xsd:double` | true | 0..1 |
| `colh_1993` | `xsd:double` | true | 0..1 |
| `colh_1994` | `xsd:double` | true | 0..1 |
| `colh_1995` | `xsd:double` | true | 0..1 |
| `colh_1996` | `xsd:double` | true | 0..1 |
| `colh_1997` | `xsd:double` | true | 0..1 |
| `colh_1998` | `xsd:double` | true | 0..1 |
| `colh_1999` | `xsd:double` | true | 0..1 |
| `colh_2000` | `xsd:double` | true | 0..1 |
| `colh_2001` | `xsd:double` | true | 0..1 |
| `colh_2002` | `xsd:double` | true | 0..1 |
| `colh_2003` | `xsd:double` | true | 0..1 |
| `colh_2004` | `xsd:double` | true | 0..1 |
| `colh_2005` | `xsd:double` | true | 0..1 |
| `colh_2006` | `xsd:double` | true | 0..1 |
| `colh_2007` | `xsd:double` | true | 0..1 |
| `colh_2008` | `xsd:double` | true | 0..1 |
| `colh_2009` | `xsd:double` | true | 0..1 |
| `colh_2010` | `xsd:double` | true | 0..1 |
| `colh_2011` | `xsd:double` | true | 0..1 |
| `colh_2012` | `xsd:double` | true | 0..1 |
| `colh_2013` | `xsd:double` | true | 0..1 |
| `colh_2014` | `xsd:double` | true | 0..1 |
| `colh_2015` | `xsd:double` | true | 0..1 |
| `colh_2016` | `xsd:double` | true | 0..1 |
| `colh_2017` | `xsd:double` | true | 0..1 |
| `colh_2018` | `xsd:double` | true | 0..1 |
| `prod_1989` | `xsd:double` | true | 0..1 |
| `prod_1990` | `xsd:double` | true | 0..1 |
| `prod_1991` | `xsd:double` | true | 0..1 |
| `prod_1992` | `xsd:double` | true | 0..1 |
| `prod_1993` | `xsd:double` | true | 0..1 |
| `prod_1994` | `xsd:double` | true | 0..1 |
| `prod_1995` | `xsd:double` | true | 0..1 |
| `prod_1996` | `xsd:double` | true | 0..1 |
| `prod_1997` | `xsd:double` | true | 0..1 |
| `prod_1998` | `xsd:double` | true | 0..1 |
| `prod_1999` | `xsd:double` | true | 0..1 |
| `prod_2000` | `xsd:double` | true | 0..1 |
| `prod_2001` | `xsd:double` | true | 0..1 |
| `prod_2002` | `xsd:double` | true | 0..1 |
| `prod_2003` | `xsd:double` | true | 0..1 |
| `prod_2004` | `xsd:double` | true | 0..1 |
| `prod_2005` | `xsd:double` | true | 0..1 |
| `prod_2006` | `xsd:double` | true | 0..1 |
| `prod_2007` | `xsd:double` | true | 0..1 |
| `prod_2008` | `xsd:double` | true | 0..1 |
| `prod_2009` | `xsd:double` | true | 0..1 |
| `prod_2010` | `xsd:double` | true | 0..1 |
| `prod_2011` | `xsd:double` | true | 0..1 |
| `prod_2012` | `xsd:double` | true | 0..1 |
| `prod_2013` | `xsd:double` | true | 0..1 |
| `prod_2014` | `xsd:double` | true | 0..1 |
| `prod_2015` | `xsd:double` | true | 0..1 |
| `prod_2016` | `xsd:double` | true | 0..1 |
| `prod_2017` | `xsd:double` | true | 0..1 |
| `prod_2018` | `xsd:double` | true | 0..1 |
| `rend_1989` | `xsd:double` | true | 0..1 |
| `rend_1990` | `xsd:double` | true | 0..1 |
| `rend_1991` | `xsd:double` | true | 0..1 |
| `rend_1992` | `xsd:double` | true | 0..1 |
| `rend_1993` | `xsd:double` | true | 0..1 |
| `rend_1994` | `xsd:double` | true | 0..1 |
| `rend_1995` | `xsd:double` | true | 0..1 |
| `rend_1996` | `xsd:double` | true | 0..1 |
| `rend_1997` | `xsd:double` | true | 0..1 |
| `rend_1998` | `xsd:double` | true | 0..1 |
| `rend_1999` | `xsd:double` | true | 0..1 |
| `rend_2000` | `xsd:double` | true | 0..1 |
| `rend_2001` | `xsd:double` | true | 0..1 |
| `rend_2002` | `xsd:double` | true | 0..1 |
| `rend_2003` | `xsd:double` | true | 0..1 |
| `rend_2004` | `xsd:double` | true | 0..1 |
| `rend_2005` | `xsd:double` | true | 0..1 |
| `rend_2006` | `xsd:double` | true | 0..1 |
| `rend_2007` | `xsd:double` | true | 0..1 |
| `rend_2008` | `xsd:double` | true | 0..1 |
| `rend_2009` | `xsd:double` | true | 0..1 |
| `rend_2010` | `xsd:double` | true | 0..1 |
| `rend_2011` | `xsd:double` | true | 0..1 |
| `rend_2012` | `xsd:double` | true | 0..1 |
| `rend_2013` | `xsd:double` | true | 0..1 |
| `rend_2014` | `xsd:double` | true | 0..1 |
| `rend_2015` | `xsd:double` | true | 0..1 |
| `rend_2016` | `xsd:double` | true | 0..1 |
| `rend_2017` | `xsd:double` | true | 0..1 |
| `rend_2018` | `xsd:double` | true | 0..1 |

### `estatistica:lavoura_temporaria_tomate_1989_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `nume_cid` | `xsd:string` | true | 0..1 |
| `pgai` | `xsd:string` | true | 0..1 |
| `tipo_cidd` | `xsd:string` | true | 0..1 |
| `regiao_num` | `xsd:string` | true | 0..1 |
| `territ_cid` | `xsd:string` | true | 0..1 |
| `utr` | `xsd:string` | true | 0..1 |
| `criacao` | `xsd:string` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `pop_1996` | `xsd:double` | true | 0..1 |
| `pop_2000` | `xsd:double` | true | 0..1 |
| `pop_2007` | `xsd:double` | true | 0..1 |
| `pop_2008` | `xsd:double` | true | 0..1 |
| `pop_2009` | `xsd:double` | true | 0..1 |
| `assoc_mun` | `xsd:string` | true | 0..1 |
| `reg_pm` | `xsd:string` | true | 0..1 |
| `art_pm` | `xsd:string` | true | 0..1 |
| `region_ibg` | `xsd:string` | true | 0..1 |
| `cod_region` | `xsd:double` | true | 0..1 |
| `pop_2010` | `xsd:double` | true | 0..1 |
| `ppa_2012_2` | `xsd:string` | true | 0..1 |
| `number` | `xsd:double` | true | 0..1 |
| `regionaliz` | `xsd:string` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `reg_tur` | `xsd:string` | true | 0..1 |
| `nova_regio` | `xsd:string` | true | 0..1 |
| `nova_reg_o` | `xsd:string` | true | 0..1 |
| `cultura` | `xsd:string` | true | 0..1 |
| `area_1989` | `xsd:double` | true | 0..1 |
| `area_1990` | `xsd:double` | true | 0..1 |
| `area_1991` | `xsd:double` | true | 0..1 |
| `area_1992` | `xsd:double` | true | 0..1 |
| `area_1993` | `xsd:double` | true | 0..1 |
| `area_1994` | `xsd:double` | true | 0..1 |
| `area_1995` | `xsd:double` | true | 0..1 |
| `area_1996` | `xsd:double` | true | 0..1 |
| `area_1997` | `xsd:double` | true | 0..1 |
| `area_1998` | `xsd:double` | true | 0..1 |
| `area_1999` | `xsd:double` | true | 0..1 |
| `area_2000` | `xsd:double` | true | 0..1 |
| `area_2001` | `xsd:double` | true | 0..1 |
| `area_2002` | `xsd:double` | true | 0..1 |
| `area_2003` | `xsd:double` | true | 0..1 |
| `area_2004` | `xsd:double` | true | 0..1 |
| `area_2005` | `xsd:double` | true | 0..1 |
| `area_2006` | `xsd:double` | true | 0..1 |
| `area_2007` | `xsd:double` | true | 0..1 |
| `area_2008` | `xsd:double` | true | 0..1 |
| `area_2009` | `xsd:double` | true | 0..1 |
| `area_2010` | `xsd:double` | true | 0..1 |
| `area_2011` | `xsd:double` | true | 0..1 |
| `area_2012` | `xsd:double` | true | 0..1 |
| `area_2013` | `xsd:double` | true | 0..1 |
| `area_2014` | `xsd:double` | true | 0..1 |
| `area_2015` | `xsd:double` | true | 0..1 |
| `area_2016` | `xsd:double` | true | 0..1 |
| `area_2017` | `xsd:double` | true | 0..1 |
| `area_2018` | `xsd:double` | true | 0..1 |
| `colh_1989` | `xsd:double` | true | 0..1 |
| `colh_1990` | `xsd:double` | true | 0..1 |
| `colh_1991` | `xsd:double` | true | 0..1 |
| `colh_1992` | `xsd:double` | true | 0..1 |
| `colh_1993` | `xsd:double` | true | 0..1 |
| `colh_1994` | `xsd:double` | true | 0..1 |
| `colh_1995` | `xsd:double` | true | 0..1 |
| `colh_1996` | `xsd:double` | true | 0..1 |
| `colh_1997` | `xsd:double` | true | 0..1 |
| `colh_1998` | `xsd:double` | true | 0..1 |
| `colh_1999` | `xsd:double` | true | 0..1 |
| `colh_2000` | `xsd:double` | true | 0..1 |
| `colh_2001` | `xsd:double` | true | 0..1 |
| `colh_2002` | `xsd:double` | true | 0..1 |
| `colh_2003` | `xsd:double` | true | 0..1 |
| `colh_2004` | `xsd:double` | true | 0..1 |
| `colh_2005` | `xsd:double` | true | 0..1 |
| `colh_2006` | `xsd:double` | true | 0..1 |
| `colh_2007` | `xsd:double` | true | 0..1 |
| `colh_2008` | `xsd:double` | true | 0..1 |
| `colh_2009` | `xsd:double` | true | 0..1 |
| `colh_2010` | `xsd:double` | true | 0..1 |
| `colh_2011` | `xsd:double` | true | 0..1 |
| `colh_2012` | `xsd:double` | true | 0..1 |
| `colh_2013` | `xsd:double` | true | 0..1 |
| `colh_2014` | `xsd:double` | true | 0..1 |
| `colh_2015` | `xsd:double` | true | 0..1 |
| `colh_2016` | `xsd:double` | true | 0..1 |
| `colh_2017` | `xsd:double` | true | 0..1 |
| `colh_2018` | `xsd:double` | true | 0..1 |
| `prod_1989` | `xsd:double` | true | 0..1 |
| `prod_1990` | `xsd:double` | true | 0..1 |
| `prod_1991` | `xsd:double` | true | 0..1 |
| `prod_1992` | `xsd:double` | true | 0..1 |
| `prod_1993` | `xsd:double` | true | 0..1 |
| `prod_1994` | `xsd:double` | true | 0..1 |
| `prod_1995` | `xsd:double` | true | 0..1 |
| `prod_1996` | `xsd:double` | true | 0..1 |
| `prod_1997` | `xsd:double` | true | 0..1 |
| `prod_1998` | `xsd:double` | true | 0..1 |
| `prod_1999` | `xsd:double` | true | 0..1 |
| `prod_2000` | `xsd:double` | true | 0..1 |
| `prod_2001` | `xsd:double` | true | 0..1 |
| `prod_2002` | `xsd:double` | true | 0..1 |
| `prod_2003` | `xsd:double` | true | 0..1 |
| `prod_2004` | `xsd:double` | true | 0..1 |
| `prod_2005` | `xsd:double` | true | 0..1 |
| `prod_2006` | `xsd:double` | true | 0..1 |
| `prod_2007` | `xsd:double` | true | 0..1 |
| `prod_2008` | `xsd:double` | true | 0..1 |
| `prod_2009` | `xsd:double` | true | 0..1 |
| `prod_2010` | `xsd:double` | true | 0..1 |
| `prod_2011` | `xsd:double` | true | 0..1 |
| `prod_2012` | `xsd:double` | true | 0..1 |
| `prod_2013` | `xsd:double` | true | 0..1 |
| `prod_2014` | `xsd:double` | true | 0..1 |
| `prod_2015` | `xsd:double` | true | 0..1 |
| `prod_2016` | `xsd:double` | true | 0..1 |
| `prod_2017` | `xsd:double` | true | 0..1 |
| `prod_2018` | `xsd:double` | true | 0..1 |
| `rend_1989` | `xsd:double` | true | 0..1 |
| `rend_1990` | `xsd:double` | true | 0..1 |
| `rend_1991` | `xsd:double` | true | 0..1 |
| `rend_1992` | `xsd:double` | true | 0..1 |
| `rend_1993` | `xsd:double` | true | 0..1 |
| `rend_1994` | `xsd:double` | true | 0..1 |
| `rend_1995` | `xsd:double` | true | 0..1 |
| `rend_1996` | `xsd:double` | true | 0..1 |
| `rend_1997` | `xsd:double` | true | 0..1 |
| `rend_1998` | `xsd:double` | true | 0..1 |
| `rend_1999` | `xsd:double` | true | 0..1 |
| `rend_2000` | `xsd:double` | true | 0..1 |
| `rend_2001` | `xsd:double` | true | 0..1 |
| `rend_2002` | `xsd:double` | true | 0..1 |
| `rend_2003` | `xsd:double` | true | 0..1 |
| `rend_2004` | `xsd:double` | true | 0..1 |
| `rend_2005` | `xsd:double` | true | 0..1 |
| `rend_2006` | `xsd:double` | true | 0..1 |
| `rend_2007` | `xsd:double` | true | 0..1 |
| `rend_2008` | `xsd:double` | true | 0..1 |
| `rend_2009` | `xsd:double` | true | 0..1 |
| `rend_2010` | `xsd:double` | true | 0..1 |
| `rend_2011` | `xsd:double` | true | 0..1 |
| `rend_2012` | `xsd:double` | true | 0..1 |
| `rend_2013` | `xsd:double` | true | 0..1 |
| `rend_2014` | `xsd:double` | true | 0..1 |
| `rend_2015` | `xsd:double` | true | 0..1 |
| `rend_2016` | `xsd:double` | true | 0..1 |
| `rend_2017` | `xsd:double` | true | 0..1 |
| `rend_2018` | `xsd:double` | true | 0..1 |

### `estatistica:leishmaniose_visceral`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `visce_2007` | `xsd:long` | true | 0..1 |
| `tegum_2007` | `xsd:long` | true | 0..1 |
| `visce_2008` | `xsd:long` | true | 0..1 |
| `tegum_2008` | `xsd:long` | true | 0..1 |
| `visce_2009` | `xsd:long` | true | 0..1 |
| `tegum_2009` | `xsd:long` | true | 0..1 |
| `visce_2010` | `xsd:long` | true | 0..1 |
| `tegum_2010` | `xsd:long` | true | 0..1 |
| `visce_2011` | `xsd:long` | true | 0..1 |
| `tegum_2011` | `xsd:long` | true | 0..1 |
| `visce_2012` | `xsd:long` | true | 0..1 |
| `tegum_2012` | `xsd:long` | true | 0..1 |
| `visce_2013` | `xsd:long` | true | 0..1 |
| `tegum_2013` | `xsd:long` | true | 0..1 |
| `visce_2014` | `xsd:long` | true | 0..1 |
| `tegum_2014` | `xsd:long` | true | 0..1 |
| `visce_2015` | `xsd:long` | true | 0..1 |
| `tegum_2015` | `xsd:long` | true | 0..1 |
| `visce_2016` | `xsd:long` | true | 0..1 |
| `tegum_2016` | `xsd:long` | true | 0..1 |
| `visce_2017` | `xsd:long` | true | 0..1 |
| `tegum_2017` | `xsd:long` | true | 0..1 |
| `visce_2018` | `xsd:long` | true | 0..1 |
| `tegum_2018` | `xsd:long` | true | 0..1 |

### `estatistica:leite1`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `leite_1989` | `xsd:long` | true | 0..1 |
| `leite_1990` | `xsd:long` | true | 0..1 |
| `leite_1991` | `xsd:long` | true | 0..1 |
| `leite_1992` | `xsd:long` | true | 0..1 |
| `leite_1993` | `xsd:long` | true | 0..1 |
| `leite_1994` | `xsd:long` | true | 0..1 |
| `leite_1995` | `xsd:long` | true | 0..1 |
| `leite_1996` | `xsd:long` | true | 0..1 |
| `leite_1997` | `xsd:long` | true | 0..1 |
| `leite_1998` | `xsd:long` | true | 0..1 |
| `leite_1999` | `xsd:long` | true | 0..1 |
| `leite_2000` | `xsd:long` | true | 0..1 |
| `leite_2001` | `xsd:long` | true | 0..1 |
| `leite_2002` | `xsd:long` | true | 0..1 |
| `leite_2003` | `xsd:long` | true | 0..1 |
| `leite_2004` | `xsd:long` | true | 0..1 |
| `leite_2005` | `xsd:long` | true | 0..1 |
| `leite_2006` | `xsd:long` | true | 0..1 |
| `leite_2007` | `xsd:long` | true | 0..1 |
| `leite_2008` | `xsd:long` | true | 0..1 |
| `leite_2009` | `xsd:long` | true | 0..1 |
| `leite_2010` | `xsd:long` | true | 0..1 |
| `leite_2011` | `xsd:long` | true | 0..1 |
| `leite_2012` | `xsd:long` | true | 0..1 |
| `leite_2013` | `xsd:long` | true | 0..1 |
| `leite_2014` | `xsd:long` | true | 0..1 |
| `leite_2015` | `xsd:long` | true | 0..1 |
| `leite_2016` | `xsd:long` | true | 0..1 |
| `leite_2017` | `xsd:long` | true | 0..1 |
| `leite_2018` | `xsd:long` | true | 0..1 |

### `estatistica:matriculas_2012`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `mpre_mur` | `xsd:int` | true | 0..1 |
| `mpe_mru` | `xsd:int` | true | 0..1 |
| `mpe_pur` | `xsd:int` | true | 0..1 |
| `mur_ef` | `xsd:int` | true | 0..1 |
| `mru_ef` | `xsd:int` | true | 0..1 |
| `pur_ef` | `xsd:int` | true | 0..1 |
| `pru_ef` | `xsd:int` | true | 0..1 |
| `mru_em` | `xsd:int` | true | 0..1 |
| `pur_em` | `xsd:int` | true | 0..1 |
| `pru_em` | `xsd:int` | true | 0..1 |
| `ep_pur` | `xsd:int` | true | 0..1 |
| `ep_pru` | `xsd:int` | true | 0..1 |
| `mur_te` | `xsd:int` | true | 0..1 |
| `mru_te` | `xsd:int` | true | 0..1 |
| `pur_te` | `xsd:int` | true | 0..1 |
| `pru_te` | `xsd:int` | true | 0..1 |
| `mur_tee` | `xsd:int` | true | 0..1 |
| `mru_tee` | `xsd:int` | true | 0..1 |
| `pur_tee` | `xsd:int` | true | 0..1 |

### `estatistica:matriculas_2014`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nmc_mru` | `xsd:int` | true | 0..1 |
| `nmc_mur` | `xsd:int` | true | 0..1 |
| `nmc_pru` | `xsd:int` | true | 0..1 |
| `nmc_pur` | `xsd:int` | true | 0..1 |
| `nmee_eur` | `xsd:int` | true | 0..1 |
| `nmee_mur` | `xsd:int` | true | 0..1 |
| `nmee_pur` | `xsd:int` | true | 0..1 |
| `nmee_ru` | `xsd:int` | true | 0..1 |
| `nmeef_eru` | `xsd:int` | true | 0..1 |
| `nmeef_eur` | `xsd:int` | true | 0..1 |
| `nmeef_mru` | `xsd:int` | true | 0..1 |
| `nmeef_pur` | `xsd:int` | true | 0..1 |
| `nmeem_eru` | `xsd:int` | true | 0..1 |
| `nmeem_eur` | `xsd:int` | true | 0..1 |
| `nmeem_fur` | `xsd:int` | true | 0..1 |
| `nmeem_mur` | `xsd:int` | true | 0..1 |
| `nmeem_pru` | `xsd:int` | true | 0..1 |
| `nmeem_pur` | `xsd:int` | true | 0..1 |
| `nmef_eru` | `xsd:int` | true | 0..1 |
| `nmef_eur` | `xsd:int` | true | 0..1 |
| `nmef_mru` | `xsd:int` | true | 0..1 |
| `nmef_mu` | `xsd:int` | true | 0..1 |
| `nmef_mur` | `xsd:int` | true | 0..1 |
| `nmef_pru` | `xsd:int` | true | 0..1 |
| `nmef_pur` | `xsd:int` | true | 0..1 |
| `nmem_eru` | `xsd:int` | true | 0..1 |
| `nmem_eur` | `xsd:int` | true | 0..1 |
| `nmem_mru` | `xsd:int` | true | 0..1 |
| `nmem_pru` | `xsd:int` | true | 0..1 |
| `nmem_pur` | `xsd:int` | true | 0..1 |
| `nmem_ruf` | `xsd:int` | true | 0..1 |
| `nmem_urf` | `xsd:int` | true | 0..1 |
| `nmep_eur` | `xsd:int` | true | 0..1 |
| `nmep_fru` | `xsd:int` | true | 0..1 |
| `nmep_fur` | `xsd:int` | true | 0..1 |
| `nmep_pru` | `xsd:int` | true | 0..1 |
| `nmep_pur` | `xsd:int` | true | 0..1 |
| `nmpe_mru` | `xsd:int` | true | 0..1 |
| `nmpe_mur` | `xsd:int` | true | 0..1 |
| `nmpe_pru` | `xsd:int` | true | 0..1 |
| `nmpe_pur` | `xsd:int` | true | 0..1 |

### `estatistica:matriculas_2015`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `mec_e` | `xsd:int` | true | 0..1 |
| `mec_m` | `xsd:int` | true | 0..1 |
| `mec_p` | `xsd:int` | true | 0..1 |
| `me_pe_e` | `xsd:int` | true | 0..1 |
| `me_pe_m` | `xsd:int` | true | 0..1 |
| `me_pe_p` | `xsd:int` | true | 0..1 |
| `mef_e` | `xsd:int` | true | 0..1 |
| `mef_m` | `xsd:int` | true | 0..1 |
| `mef_p` | `xsd:int` | true | 0..1 |
| `me_mf` | `xsd:int` | true | 0..1 |
| `me_m` | `xsd:int` | true | 0..1 |
| `me_mm` | `xsd:int` | true | 0..1 |
| `me_mp` | `xsd:int` | true | 0..1 |
| `mep_f` | `xsd:int` | true | 0..1 |
| `mep_e` | `xsd:int` | true | 0..1 |
| `mep_mu` | `xsd:int` | true | 0..1 |
| `mep_p` | `xsd:int` | true | 0..1 |
| `mee_f` | `xsd:int` | true | 0..1 |
| `mee_es` | `xsd:int` | true | 0..1 |
| `mee_mu` | `xsd:int` | true | 0..1 |
| `mee_p` | `xsd:int` | true | 0..1 |
| `mee_fe` | `xsd:int` | true | 0..1 |
| `mee_e` | `xsd:int` | true | 0..1 |
| `mee_m` | `xsd:int` | true | 0..1 |
| `mee_par` | `xsd:int` | true | 0..1 |

### `estatistica:mel_de_abelha_1989_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `miel1989` | `xsd:long` | true | 0..1 |
| `miel1990` | `xsd:long` | true | 0..1 |
| `miel1991` | `xsd:long` | true | 0..1 |
| `miel1992` | `xsd:long` | true | 0..1 |
| `miel1993` | `xsd:long` | true | 0..1 |
| `miel1994` | `xsd:long` | true | 0..1 |
| `miel1995` | `xsd:long` | true | 0..1 |
| `miel1996` | `xsd:long` | true | 0..1 |
| `miel1997` | `xsd:long` | true | 0..1 |
| `miel1998` | `xsd:long` | true | 0..1 |
| `miel1999` | `xsd:long` | true | 0..1 |
| `miel2000` | `xsd:long` | true | 0..1 |
| `miel2001` | `xsd:long` | true | 0..1 |
| `miel2002` | `xsd:long` | true | 0..1 |
| `miel2003` | `xsd:long` | true | 0..1 |
| `miel2004` | `xsd:long` | true | 0..1 |
| `miel2005` | `xsd:long` | true | 0..1 |
| `miel2006` | `xsd:long` | true | 0..1 |
| `miel2007` | `xsd:long` | true | 0..1 |
| `miel2008` | `xsd:long` | true | 0..1 |
| `miel2009` | `xsd:long` | true | 0..1 |
| `miel2010` | `xsd:long` | true | 0..1 |
| `miel2011` | `xsd:long` | true | 0..1 |
| `miel2012` | `xsd:long` | true | 0..1 |
| `miel2013` | `xsd:long` | true | 0..1 |
| `miel2014` | `xsd:long` | true | 0..1 |
| `miel2015` | `xsd:long` | true | 0..1 |
| `miel2016` | `xsd:long` | true | 0..1 |
| `miel2017` | `xsd:long` | true | 0..1 |
| `miel2018` | `xsd:long` | true | 0..1 |

### `estatistica:numero_casos_dengue`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `dengue_07` | `xsd:long` | true | 0..1 |
| `dengue_08` | `xsd:long` | true | 0..1 |
| `dengue_09` | `xsd:long` | true | 0..1 |
| `dengue_10` | `xsd:long` | true | 0..1 |
| `dengue_11` | `xsd:long` | true | 0..1 |
| `dengue_12` | `xsd:long` | true | 0..1 |
| `dengue_13` | `xsd:long` | true | 0..1 |
| `dengue_14` | `xsd:long` | true | 0..1 |
| `dengue_15` | `xsd:long` | true | 0..1 |
| `dengue_16` | `xsd:long` | true | 0..1 |

### `estatistica:numero_de_casos_confirmados_de_meningite_2007_a_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `casos_2007` | `xsd:long` | true | 0..1 |
| `casos_2008` | `xsd:long` | true | 0..1 |
| `casos_2009` | `xsd:long` | true | 0..1 |
| `casos_2010` | `xsd:long` | true | 0..1 |
| `casos_2011` | `xsd:long` | true | 0..1 |
| `casos_2012` | `xsd:long` | true | 0..1 |
| `casos_2013` | `xsd:long` | true | 0..1 |
| `casos_2014` | `xsd:long` | true | 0..1 |
| `casos_2015` | `xsd:long` | true | 0..1 |
| `casos_2016` | `xsd:long` | true | 0..1 |
| `casos_2017` | `xsd:long` | true | 0..1 |
| `casos_2018` | `xsd:long` | true | 0..1 |

### `estatistica:numero_de_leitos_de_internacao_hospitalar`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `sus_2006` | `xsd:long` | true | 0..1 |
| `priv_2006` | `xsd:long` | true | 0..1 |
| `sus_2007` | `xsd:long` | true | 0..1 |
| `priv_2007` | `xsd:long` | true | 0..1 |
| `sus_2008` | `xsd:long` | true | 0..1 |
| `priv_2008` | `xsd:long` | true | 0..1 |
| `sus_2009` | `xsd:long` | true | 0..1 |
| `priv_2009` | `xsd:long` | true | 0..1 |
| `sus_2010` | `xsd:long` | true | 0..1 |
| `priv_2010` | `xsd:long` | true | 0..1 |
| `sus_2011` | `xsd:long` | true | 0..1 |
| `priv_2011` | `xsd:long` | true | 0..1 |
| `sus_2012` | `xsd:long` | true | 0..1 |
| `priv_2012` | `xsd:long` | true | 0..1 |
| `sus_2013` | `xsd:long` | true | 0..1 |
| `priv_2013` | `xsd:long` | true | 0..1 |
| `sus_2014` | `xsd:long` | true | 0..1 |
| `priv_2014` | `xsd:long` | true | 0..1 |
| `sus_2015` | `xsd:long` | true | 0..1 |
| `priv_2015` | `xsd:long` | true | 0..1 |
| `sus_2016` | `xsd:long` | true | 0..1 |
| `priv_2016` | `xsd:long` | true | 0..1 |
| `sus_2017` | `xsd:long` | true | 0..1 |
| `priv_2017` | `xsd:long` | true | 0..1 |
| `sus_2018` | `xsd:long` | true | 0..1 |
| `priv_2018` | `xsd:long` | true | 0..1 |
| `sus_2019` | `xsd:long` | true | 0..1 |
| `priv_2019` | `xsd:long` | true | 0..1 |

### `estatistica:numero_de_profissionais_de_saude`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `anes_2008` | `xsd:long` | true | 0..1 |
| `cirur_2008` | `xsd:long` | true | 0..1 |
| `clini_2008` | `xsd:long` | true | 0..1 |
| `ginec_2008` | `xsd:long` | true | 0..1 |
| `famil_2008` | `xsd:long` | true | 0..1 |
| `pedi_2008` | `xsd:long` | true | 0..1 |
| `psiq_2008` | `xsd:long` | true | 0..1 |
| `radio_2008` | `xsd:long` | true | 0..1 |
| `sanit_2008` | `xsd:long` | true | 0..1 |
| `outro_2008` | `xsd:long` | true | 0..1 |
| `denti_2008` | `xsd:long` | true | 0..1 |
| `enfer_2008` | `xsd:long` | true | 0..1 |
| `fisio_2008` | `xsd:long` | true | 0..1 |
| `fono_2008` | `xsd:long` | true | 0..1 |
| `nutri_2008` | `xsd:long` | true | 0..1 |
| `farma_2008` | `xsd:long` | true | 0..1 |
| `assis_2008` | `xsd:long` | true | 0..1 |
| `psico_2008` | `xsd:long` | true | 0..1 |
| `auxil_2008` | `xsd:long` | true | 0..1 |
| `tecni_2008` | `xsd:long` | true | 0..1 |
| `anes_2009` | `xsd:long` | true | 0..1 |
| `cirur_2009` | `xsd:long` | true | 0..1 |
| `clini_2009` | `xsd:long` | true | 0..1 |
| `ginec_2009` | `xsd:long` | true | 0..1 |
| `famil_2009` | `xsd:long` | true | 0..1 |
| `pedi_2009` | `xsd:long` | true | 0..1 |
| `psiq_2009` | `xsd:long` | true | 0..1 |
| `radio_2009` | `xsd:long` | true | 0..1 |
| `sanit_2009` | `xsd:long` | true | 0..1 |
| `outro_2009` | `xsd:long` | true | 0..1 |
| `denti_2009` | `xsd:long` | true | 0..1 |
| `enfer_2009` | `xsd:long` | true | 0..1 |
| `fisio_2009` | `xsd:long` | true | 0..1 |
| `fono_2009` | `xsd:long` | true | 0..1 |
| `nutri_2009` | `xsd:long` | true | 0..1 |
| `farma_2009` | `xsd:long` | true | 0..1 |
| `assis_2009` | `xsd:long` | true | 0..1 |
| `psico_2009` | `xsd:long` | true | 0..1 |
| `auxil_2009` | `xsd:long` | true | 0..1 |
| `tecni_2009` | `xsd:long` | true | 0..1 |
| `anes_2010` | `xsd:long` | true | 0..1 |
| `cirur_2010` | `xsd:long` | true | 0..1 |
| `clini_2010` | `xsd:long` | true | 0..1 |
| `ginec_2010` | `xsd:long` | true | 0..1 |
| `famil_2010` | `xsd:long` | true | 0..1 |
| `pedi_2010` | `xsd:long` | true | 0..1 |
| `psiq_2010` | `xsd:long` | true | 0..1 |
| `radio_2010` | `xsd:long` | true | 0..1 |
| `sanit_2010` | `xsd:long` | true | 0..1 |
| `outro_2010` | `xsd:long` | true | 0..1 |
| `denti_2010` | `xsd:long` | true | 0..1 |
| `enfer_2010` | `xsd:long` | true | 0..1 |
| `fisio_2010` | `xsd:long` | true | 0..1 |
| `fono_2010` | `xsd:long` | true | 0..1 |
| `nutri_2010` | `xsd:long` | true | 0..1 |
| `farma_2010` | `xsd:long` | true | 0..1 |
| `assis_2010` | `xsd:long` | true | 0..1 |
| `psico_2010` | `xsd:long` | true | 0..1 |
| `auxil_2010` | `xsd:long` | true | 0..1 |
| `tecni_2010` | `xsd:long` | true | 0..1 |
| `anes_2011` | `xsd:long` | true | 0..1 |
| `cirur_2011` | `xsd:long` | true | 0..1 |
| `clini_2011` | `xsd:long` | true | 0..1 |
| `ginec_2011` | `xsd:long` | true | 0..1 |
| `famil_2011` | `xsd:long` | true | 0..1 |
| `pedi_2011` | `xsd:long` | true | 0..1 |
| `psiq_2011` | `xsd:long` | true | 0..1 |
| `radio_2011` | `xsd:long` | true | 0..1 |
| `sanit_2011` | `xsd:long` | true | 0..1 |
| `outro_2011` | `xsd:long` | true | 0..1 |
| `denti_2011` | `xsd:long` | true | 0..1 |
| `enfer_2011` | `xsd:long` | true | 0..1 |
| `fisio_2011` | `xsd:long` | true | 0..1 |
| `fono_2011` | `xsd:long` | true | 0..1 |
| `nutri_2011` | `xsd:long` | true | 0..1 |
| `farma_2011` | `xsd:long` | true | 0..1 |
| `assis_2011` | `xsd:long` | true | 0..1 |
| `psico_2011` | `xsd:long` | true | 0..1 |
| `auxil_2011` | `xsd:long` | true | 0..1 |
| `tecni_2011` | `xsd:long` | true | 0..1 |
| `anes_2012` | `xsd:long` | true | 0..1 |
| `cirur_2012` | `xsd:long` | true | 0..1 |
| `clini_2012` | `xsd:long` | true | 0..1 |
| `ginec_2012` | `xsd:long` | true | 0..1 |
| `famil_2012` | `xsd:long` | true | 0..1 |
| `pedi_2012` | `xsd:long` | true | 0..1 |
| `psiq_2012` | `xsd:long` | true | 0..1 |
| `radio_2012` | `xsd:long` | true | 0..1 |
| `outro_2012` | `xsd:long` | true | 0..1 |
| `denti_2012` | `xsd:long` | true | 0..1 |
| `enfer_2012` | `xsd:long` | true | 0..1 |
| `fisio_2012` | `xsd:long` | true | 0..1 |
| `fono_2012` | `xsd:long` | true | 0..1 |
| `nutri_2012` | `xsd:long` | true | 0..1 |
| `farma_2012` | `xsd:long` | true | 0..1 |
| `assis_2012` | `xsd:long` | true | 0..1 |
| `psico_2012` | `xsd:long` | true | 0..1 |
| `auxil_2012` | `xsd:long` | true | 0..1 |
| `tecni_2012` | `xsd:long` | true | 0..1 |
| `anes_2013` | `xsd:long` | true | 0..1 |
| `cirur_2013` | `xsd:long` | true | 0..1 |
| `clini_2013` | `xsd:long` | true | 0..1 |
| `ginec_2013` | `xsd:long` | true | 0..1 |
| `famil_2013` | `xsd:long` | true | 0..1 |
| `pedi_2013` | `xsd:long` | true | 0..1 |
| `psiq_2013` | `xsd:long` | true | 0..1 |
| `radio_2013` | `xsd:long` | true | 0..1 |
| `outro_2013` | `xsd:long` | true | 0..1 |
| `denti_2013` | `xsd:long` | true | 0..1 |
| `enfer_2013` | `xsd:long` | true | 0..1 |
| `fisio_2013` | `xsd:long` | true | 0..1 |
| `fono_2013` | `xsd:long` | true | 0..1 |
| `nutri_2013` | `xsd:long` | true | 0..1 |
| `farma_2013` | `xsd:long` | true | 0..1 |
| `assis_2013` | `xsd:long` | true | 0..1 |
| `psico_2013` | `xsd:long` | true | 0..1 |
| `auxil_2013` | `xsd:long` | true | 0..1 |
| `tecni_2013` | `xsd:long` | true | 0..1 |
| `anes_2014` | `xsd:long` | true | 0..1 |
| `cirur_2014` | `xsd:long` | true | 0..1 |
| `clini_2014` | `xsd:long` | true | 0..1 |
| `ginec_2014` | `xsd:long` | true | 0..1 |
| `famil_2014` | `xsd:long` | true | 0..1 |
| `pedi_2014` | `xsd:long` | true | 0..1 |
| `psiq_2014` | `xsd:long` | true | 0..1 |
| `radio_2014` | `xsd:long` | true | 0..1 |
| `outro_2014` | `xsd:long` | true | 0..1 |
| `denti_2014` | `xsd:long` | true | 0..1 |
| `enfer_2014` | `xsd:long` | true | 0..1 |
| `fisio_2014` | `xsd:long` | true | 0..1 |
| `fono_2014` | `xsd:long` | true | 0..1 |
| `nutri_2014` | `xsd:long` | true | 0..1 |
| `farma_2014` | `xsd:long` | true | 0..1 |
| `assis_2014` | `xsd:long` | true | 0..1 |
| `psico_2014` | `xsd:long` | true | 0..1 |
| `auxil_2014` | `xsd:long` | true | 0..1 |
| `tecni_2014` | `xsd:long` | true | 0..1 |
| `anes_2015` | `xsd:long` | true | 0..1 |
| `cirur_2015` | `xsd:long` | true | 0..1 |
| `clini_2015` | `xsd:long` | true | 0..1 |
| `ginec_2015` | `xsd:long` | true | 0..1 |
| `famil_2015` | `xsd:long` | true | 0..1 |
| `pedi_2015` | `xsd:long` | true | 0..1 |
| `psiq_2015` | `xsd:long` | true | 0..1 |
| `radio_2015` | `xsd:long` | true | 0..1 |
| `outro_2015` | `xsd:long` | true | 0..1 |
| `denti_2015` | `xsd:long` | true | 0..1 |
| `enfer_2015` | `xsd:long` | true | 0..1 |
| `fisio_2015` | `xsd:long` | true | 0..1 |
| `fono_2015` | `xsd:long` | true | 0..1 |
| `nutri_2015` | `xsd:long` | true | 0..1 |
| `farma_2015` | `xsd:long` | true | 0..1 |
| `assis_2015` | `xsd:long` | true | 0..1 |
| `psico_2015` | `xsd:long` | true | 0..1 |
| `auxil_2015` | `xsd:long` | true | 0..1 |
| `tecni_2015` | `xsd:long` | true | 0..1 |
| `anes_2016` | `xsd:long` | true | 0..1 |
| `cirur_2016` | `xsd:long` | true | 0..1 |
| `clini_2016` | `xsd:long` | true | 0..1 |
| `ginec_2016` | `xsd:long` | true | 0..1 |
| `famil_2016` | `xsd:long` | true | 0..1 |
| `pedi_2016` | `xsd:long` | true | 0..1 |
| `psiq_2016` | `xsd:long` | true | 0..1 |
| `radio_2016` | `xsd:long` | true | 0..1 |
| `outro_2016` | `xsd:long` | true | 0..1 |
| `denti_2016` | `xsd:long` | true | 0..1 |
| `enfer_2016` | `xsd:long` | true | 0..1 |
| `fisio_2016` | `xsd:long` | true | 0..1 |
| `fono_2016` | `xsd:long` | true | 0..1 |
| `nutri_2016` | `xsd:long` | true | 0..1 |
| `farma_2016` | `xsd:long` | true | 0..1 |
| `assis_2016` | `xsd:long` | true | 0..1 |
| `psico_2016` | `xsd:long` | true | 0..1 |
| `auxil_2016` | `xsd:long` | true | 0..1 |
| `tecni_2016` | `xsd:long` | true | 0..1 |
| `anes_2017` | `xsd:long` | true | 0..1 |
| `cirur_2017` | `xsd:long` | true | 0..1 |
| `clini_2017` | `xsd:long` | true | 0..1 |
| `ginec_2017` | `xsd:long` | true | 0..1 |
| `famil_2017` | `xsd:long` | true | 0..1 |
| `pedi_2017` | `xsd:long` | true | 0..1 |
| `psiq_2017` | `xsd:long` | true | 0..1 |
| `radio_2017` | `xsd:long` | true | 0..1 |
| `outro_2017` | `xsd:long` | true | 0..1 |
| `denti_2017` | `xsd:long` | true | 0..1 |
| `enfer_2017` | `xsd:long` | true | 0..1 |
| `fisio_2017` | `xsd:long` | true | 0..1 |
| `fono_2017` | `xsd:long` | true | 0..1 |
| `nutri_2017` | `xsd:long` | true | 0..1 |
| `farma_2017` | `xsd:long` | true | 0..1 |
| `assis_2017` | `xsd:long` | true | 0..1 |
| `psico_2017` | `xsd:long` | true | 0..1 |
| `auxil_2017` | `xsd:long` | true | 0..1 |
| `tecni_2017` | `xsd:long` | true | 0..1 |
| `anes_2018` | `xsd:long` | true | 0..1 |
| `cirur_2018` | `xsd:long` | true | 0..1 |
| `clini_2018` | `xsd:long` | true | 0..1 |
| `ginec_2018` | `xsd:long` | true | 0..1 |
| `famil_2018` | `xsd:long` | true | 0..1 |
| `pedi_2018` | `xsd:long` | true | 0..1 |
| `psiq_2018` | `xsd:long` | true | 0..1 |
| `radio_2018` | `xsd:long` | true | 0..1 |
| `outro_2018` | `xsd:long` | true | 0..1 |
| `denti_2018` | `xsd:long` | true | 0..1 |
| `enfer_2018` | `xsd:long` | true | 0..1 |
| `fisio_2018` | `xsd:long` | true | 0..1 |
| `fono_2018` | `xsd:long` | true | 0..1 |
| `nutri_2018` | `xsd:long` | true | 0..1 |
| `farma_2018` | `xsd:long` | true | 0..1 |
| `assis_2018` | `xsd:long` | true | 0..1 |
| `psico_2018` | `xsd:long` | true | 0..1 |
| `auxil_2018` | `xsd:long` | true | 0..1 |
| `tecni_2018` | `xsd:long` | true | 0..1 |
| `anes_2019` | `xsd:long` | true | 0..1 |
| `cirur_2019` | `xsd:long` | true | 0..1 |
| `clini_2019` | `xsd:long` | true | 0..1 |
| `ginec_2019` | `xsd:long` | true | 0..1 |
| `famil_2019` | `xsd:long` | true | 0..1 |
| `pedi_2019` | `xsd:long` | true | 0..1 |
| `psiq_2019` | `xsd:long` | true | 0..1 |
| `radio_2019` | `xsd:long` | true | 0..1 |
| `outro_2019` | `xsd:long` | true | 0..1 |
| `denti_2019` | `xsd:long` | true | 0..1 |
| `enfer_2019` | `xsd:long` | true | 0..1 |
| `fisio_2019` | `xsd:long` | true | 0..1 |
| `fono_2019` | `xsd:long` | true | 0..1 |
| `nutri_2019` | `xsd:long` | true | 0..1 |
| `farma_2019` | `xsd:long` | true | 0..1 |
| `assis_2019` | `xsd:long` | true | 0..1 |
| `psico_2019` | `xsd:long` | true | 0..1 |
| `auxil_2019` | `xsd:long` | true | 0..1 |
| `tecni_2019` | `xsd:long` | true | 0..1 |

### `estatistica:numero_estabelecimentos_saude`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `basic_2009` | `xsd:long` | true | 0..1 |
| `ambu_2009` | `xsd:long` | true | 0..1 |
| `consu_2009` | `xsd:long` | true | 0..1 |
| `hosp_2009` | `xsd:long` | true | 0..1 |
| `poli_2009` | `xsd:long` | true | 0..1 |
| `posto_2009` | `xsd:long` | true | 0..1 |
| `apoio_2009` | `xsd:long` | true | 0..1 |
| `vigil_2009` | `xsd:long` | true | 0..1 |
| `basic_2010` | `xsd:long` | true | 0..1 |
| `ambu_2010` | `xsd:long` | true | 0..1 |
| `consu_2010` | `xsd:long` | true | 0..1 |
| `hosp_2010` | `xsd:long` | true | 0..1 |
| `poli_2010` | `xsd:long` | true | 0..1 |
| `posto_2010` | `xsd:long` | true | 0..1 |
| `apoio_2010` | `xsd:long` | true | 0..1 |
| `vigil_2010` | `xsd:long` | true | 0..1 |
| `basic_2011` | `xsd:long` | true | 0..1 |
| `ambu_2011` | `xsd:long` | true | 0..1 |
| `consu_2011` | `xsd:long` | true | 0..1 |
| `hosp_2011` | `xsd:long` | true | 0..1 |
| `poli_2011` | `xsd:long` | true | 0..1 |
| `posto_2011` | `xsd:long` | true | 0..1 |
| `apoio_2011` | `xsd:long` | true | 0..1 |
| `vigil_2011` | `xsd:long` | true | 0..1 |
| `basic_2012` | `xsd:long` | true | 0..1 |
| `ambu_2012` | `xsd:long` | true | 0..1 |
| `consu_2012` | `xsd:long` | true | 0..1 |
| `hosp_2012` | `xsd:long` | true | 0..1 |
| `poli_2012` | `xsd:long` | true | 0..1 |
| `posto_2012` | `xsd:long` | true | 0..1 |
| `apoio_2012` | `xsd:long` | true | 0..1 |
| `vigil_2012` | `xsd:long` | true | 0..1 |
| `basic_2013` | `xsd:long` | true | 0..1 |
| `ambu_2013` | `xsd:long` | true | 0..1 |
| `consu_2013` | `xsd:long` | true | 0..1 |
| `hosp_2013` | `xsd:long` | true | 0..1 |
| `poli_2013` | `xsd:long` | true | 0..1 |
| `posto_2013` | `xsd:long` | true | 0..1 |
| `apoio_2013` | `xsd:long` | true | 0..1 |
| `vigil_2013` | `xsd:long` | true | 0..1 |
| `basic_2014` | `xsd:long` | true | 0..1 |
| `ambu_2014` | `xsd:long` | true | 0..1 |
| `consu_2014` | `xsd:long` | true | 0..1 |
| `hosp_2014` | `xsd:long` | true | 0..1 |
| `poli_2014` | `xsd:long` | true | 0..1 |
| `posto_2014` | `xsd:long` | true | 0..1 |
| `apoio_2014` | `xsd:long` | true | 0..1 |
| `vigil_2014` | `xsd:long` | true | 0..1 |
| `basic_2015` | `xsd:long` | true | 0..1 |
| `ambu_2015` | `xsd:long` | true | 0..1 |
| `consu_2015` | `xsd:long` | true | 0..1 |
| `hosp_2015` | `xsd:long` | true | 0..1 |
| `poli_2015` | `xsd:long` | true | 0..1 |
| `posto_2015` | `xsd:long` | true | 0..1 |
| `apoio_2015` | `xsd:long` | true | 0..1 |
| `vigil_2015` | `xsd:long` | true | 0..1 |
| `basic_2016` | `xsd:long` | true | 0..1 |
| `ambu_2016` | `xsd:long` | true | 0..1 |
| `consu_2016` | `xsd:long` | true | 0..1 |
| `hosp_2016` | `xsd:long` | true | 0..1 |
| `poli_2016` | `xsd:long` | true | 0..1 |
| `apoio_2016` | `xsd:long` | true | 0..1 |
| `vigil_2016` | `xsd:long` | true | 0..1 |
| `basic_2017` | `xsd:long` | true | 0..1 |
| `ambu_2017` | `xsd:long` | true | 0..1 |
| `consu_2017` | `xsd:long` | true | 0..1 |
| `hosp_2017` | `xsd:long` | true | 0..1 |
| `poli_2017` | `xsd:long` | true | 0..1 |
| `posto_2017` | `xsd:long` | true | 0..1 |
| `apoio_2017` | `xsd:long` | true | 0..1 |
| `vigil_2017` | `xsd:long` | true | 0..1 |
| `basic_2018` | `xsd:long` | true | 0..1 |
| `ambu_2018` | `xsd:long` | true | 0..1 |
| `consu_2018` | `xsd:long` | true | 0..1 |
| `hosp_2018` | `xsd:long` | true | 0..1 |
| `poli_2018` | `xsd:long` | true | 0..1 |
| `posto_2018` | `xsd:long` | true | 0..1 |
| `apoio_2018` | `xsd:long` | true | 0..1 |
| `vigil_2018` | `xsd:long` | true | 0..1 |
| `basic_2019` | `xsd:long` | true | 0..1 |
| `ambu_2019` | `xsd:long` | true | 0..1 |
| `consu_2019` | `xsd:long` | true | 0..1 |
| `hosp_2019` | `xsd:long` | true | 0..1 |
| `poli_2019` | `xsd:long` | true | 0..1 |
| `posto_2019` | `xsd:long` | true | 0..1 |
| `apoio_2019` | `xsd:long` | true | 0..1 |
| `vigil_2019` | `xsd:long` | true | 0..1 |
| `posto_2016` | `xsd:long` | true | 0..1 |

### `estatistica:numero_nascidos_vivos_por_sexo_faixa_etaria_de_mae_2009_a_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `h15_2009` | `xsd:long` | true | 0..1 |
| `m15_2009` | `xsd:long` | true | 0..1 |
| `h1519_2009` | `xsd:long` | true | 0..1 |
| `m1519_2009` | `xsd:long` | true | 0..1 |
| `h2024_2009` | `xsd:long` | true | 0..1 |
| `m2024_2009` | `xsd:long` | true | 0..1 |
| `h2529_2009` | `xsd:long` | true | 0..1 |
| `m2529_2009` | `xsd:long` | true | 0..1 |
| `h3034_2009` | `xsd:long` | true | 0..1 |
| `m3034_2009` | `xsd:long` | true | 0..1 |
| `h3539_2009` | `xsd:long` | true | 0..1 |
| `m3539_2009` | `xsd:long` | true | 0..1 |
| `h4044_2009` | `xsd:long` | true | 0..1 |
| `m4044_2009` | `xsd:long` | true | 0..1 |
| `h4549_2009` | `xsd:long` | true | 0..1 |
| `m4549_2009` | `xsd:long` | true | 0..1 |
| `h50_2009` | `xsd:long` | true | 0..1 |
| `m50_2009` | `xsd:long` | true | 0..1 |
| `h_ign_2009` | `xsd:long` | true | 0..1 |
| `m_ign_2009` | `xsd:long` | true | 0..1 |
| `h15_2010` | `xsd:long` | true | 0..1 |
| `m15_2010` | `xsd:long` | true | 0..1 |
| `h1519_2010` | `xsd:long` | true | 0..1 |
| `m1519_2010` | `xsd:long` | true | 0..1 |
| `h2024_2010` | `xsd:long` | true | 0..1 |
| `m2024_2010` | `xsd:long` | true | 0..1 |
| `h2529_2010` | `xsd:long` | true | 0..1 |
| `m2529_2010` | `xsd:long` | true | 0..1 |
| `h3034_2010` | `xsd:long` | true | 0..1 |
| `m3034_2010` | `xsd:long` | true | 0..1 |
| `h3539_2010` | `xsd:long` | true | 0..1 |
| `m3539_2010` | `xsd:long` | true | 0..1 |
| `h4044_2010` | `xsd:long` | true | 0..1 |
| `m4044_2010` | `xsd:long` | true | 0..1 |
| `h4549_2010` | `xsd:long` | true | 0..1 |
| `m4549_2010` | `xsd:long` | true | 0..1 |
| `h50_2010` | `xsd:long` | true | 0..1 |
| `m50_2010` | `xsd:long` | true | 0..1 |
| `h_ign_2010` | `xsd:long` | true | 0..1 |
| `m_ign_2010` | `xsd:long` | true | 0..1 |
| `h15_2011` | `xsd:long` | true | 0..1 |
| `m15_2011` | `xsd:long` | true | 0..1 |
| `h1519_2011` | `xsd:long` | true | 0..1 |
| `m1519_2011` | `xsd:long` | true | 0..1 |
| `h2024_2011` | `xsd:long` | true | 0..1 |
| `m2024_2011` | `xsd:long` | true | 0..1 |
| `h2529_2011` | `xsd:long` | true | 0..1 |
| `m2529_2011` | `xsd:long` | true | 0..1 |
| `h3034_2011` | `xsd:long` | true | 0..1 |
| `m3034_2011` | `xsd:long` | true | 0..1 |
| `h3539_2011` | `xsd:long` | true | 0..1 |
| `m3539_2011` | `xsd:long` | true | 0..1 |
| `h4044_2011` | `xsd:long` | true | 0..1 |
| `m4044_2011` | `xsd:long` | true | 0..1 |
| `h4549_2011` | `xsd:long` | true | 0..1 |
| `m4549_2011` | `xsd:long` | true | 0..1 |
| `h50_2011` | `xsd:long` | true | 0..1 |
| `m50_2011` | `xsd:long` | true | 0..1 |
| `h_ign_2011` | `xsd:long` | true | 0..1 |
| `m_ign_2011` | `xsd:long` | true | 0..1 |
| `h15_2012` | `xsd:long` | true | 0..1 |
| `m15_2012` | `xsd:long` | true | 0..1 |
| `h1519_2012` | `xsd:long` | true | 0..1 |
| `m1519_2012` | `xsd:long` | true | 0..1 |
| `h2024_2012` | `xsd:long` | true | 0..1 |
| `m2024_2012` | `xsd:long` | true | 0..1 |
| `h2529_2012` | `xsd:long` | true | 0..1 |
| `m2529_2012` | `xsd:long` | true | 0..1 |
| `h3034_2012` | `xsd:long` | true | 0..1 |
| `m3034_2012` | `xsd:long` | true | 0..1 |
| `h3539_2012` | `xsd:long` | true | 0..1 |
| `m3539_2012` | `xsd:long` | true | 0..1 |
| `h4044_2012` | `xsd:long` | true | 0..1 |
| `m4044_2012` | `xsd:long` | true | 0..1 |
| `h4549_2012` | `xsd:long` | true | 0..1 |
| `m4549_2012` | `xsd:long` | true | 0..1 |
| `h50_2012` | `xsd:long` | true | 0..1 |
| `m50_2012` | `xsd:long` | true | 0..1 |
| `h_ign_2012` | `xsd:long` | true | 0..1 |
| `m_ign_2012` | `xsd:long` | true | 0..1 |
| `h15_2013` | `xsd:long` | true | 0..1 |
| `m15_2013` | `xsd:long` | true | 0..1 |
| `h1519_2013` | `xsd:long` | true | 0..1 |
| `m1519_2013` | `xsd:long` | true | 0..1 |
| `h2024_2013` | `xsd:long` | true | 0..1 |
| `m2024_2013` | `xsd:long` | true | 0..1 |
| `h2529_2013` | `xsd:long` | true | 0..1 |
| `m2529_2013` | `xsd:long` | true | 0..1 |
| `h3034_2013` | `xsd:long` | true | 0..1 |
| `m3034_2013` | `xsd:long` | true | 0..1 |
| `h3539_2013` | `xsd:long` | true | 0..1 |
| `m3539_2013` | `xsd:long` | true | 0..1 |
| `h4044_2013` | `xsd:long` | true | 0..1 |
| `m4044_2013` | `xsd:long` | true | 0..1 |
| `h4549_2013` | `xsd:long` | true | 0..1 |
| `m4549_2013` | `xsd:long` | true | 0..1 |
| `h50_2013` | `xsd:long` | true | 0..1 |
| `m50_2013` | `xsd:long` | true | 0..1 |
| `h_ign_2013` | `xsd:long` | true | 0..1 |
| `m_ign_2013` | `xsd:long` | true | 0..1 |
| `h15_2014` | `xsd:long` | true | 0..1 |
| `m15_2014` | `xsd:long` | true | 0..1 |
| `h1519_2014` | `xsd:long` | true | 0..1 |
| `m1519_2014` | `xsd:long` | true | 0..1 |
| `h2024_2014` | `xsd:long` | true | 0..1 |
| `m2024_2014` | `xsd:long` | true | 0..1 |
| `h2529_2014` | `xsd:long` | true | 0..1 |
| `m2529_2014` | `xsd:long` | true | 0..1 |
| `h3034_2014` | `xsd:long` | true | 0..1 |
| `m3034_2014` | `xsd:long` | true | 0..1 |
| `h3539_2014` | `xsd:long` | true | 0..1 |
| `m3539_2014` | `xsd:long` | true | 0..1 |
| `h4044_2014` | `xsd:long` | true | 0..1 |
| `m4044_2014` | `xsd:long` | true | 0..1 |
| `h4549_2014` | `xsd:long` | true | 0..1 |
| `m4549_2014` | `xsd:long` | true | 0..1 |
| `h50_2014` | `xsd:long` | true | 0..1 |
| `m50_2014` | `xsd:long` | true | 0..1 |
| `h_ign_2014` | `xsd:long` | true | 0..1 |
| `m_ign_2014` | `xsd:long` | true | 0..1 |
| `h15_2015` | `xsd:long` | true | 0..1 |
| `m15_2015` | `xsd:long` | true | 0..1 |
| `h1519_2015` | `xsd:long` | true | 0..1 |
| `m1519_2015` | `xsd:long` | true | 0..1 |
| `h2024_2015` | `xsd:long` | true | 0..1 |
| `m2024_2015` | `xsd:long` | true | 0..1 |
| `h2529_2015` | `xsd:long` | true | 0..1 |
| `m2529_2015` | `xsd:long` | true | 0..1 |
| `h3034_2015` | `xsd:long` | true | 0..1 |
| `m3034_2015` | `xsd:long` | true | 0..1 |
| `h3539_2015` | `xsd:long` | true | 0..1 |
| `m3539_2015` | `xsd:long` | true | 0..1 |
| `h4044_2015` | `xsd:long` | true | 0..1 |
| `m4044_2015` | `xsd:long` | true | 0..1 |
| `h4549_2015` | `xsd:long` | true | 0..1 |
| `m4549_2015` | `xsd:long` | true | 0..1 |
| `h50_2015` | `xsd:long` | true | 0..1 |
| `m50_2015` | `xsd:long` | true | 0..1 |
| `h_ign_2015` | `xsd:long` | true | 0..1 |
| `m_ign_2015` | `xsd:long` | true | 0..1 |
| `h15_2016` | `xsd:long` | true | 0..1 |
| `m15_2016` | `xsd:long` | true | 0..1 |
| `h1519_2016` | `xsd:long` | true | 0..1 |
| `m1519_2016` | `xsd:long` | true | 0..1 |
| `h2024_2016` | `xsd:long` | true | 0..1 |
| `m2024_2016` | `xsd:long` | true | 0..1 |
| `h2529_2016` | `xsd:long` | true | 0..1 |
| `m2529_2016` | `xsd:long` | true | 0..1 |
| `h3034_2016` | `xsd:long` | true | 0..1 |
| `m3034_2016` | `xsd:long` | true | 0..1 |
| `h3539_2016` | `xsd:long` | true | 0..1 |
| `m3539_2016` | `xsd:long` | true | 0..1 |
| `h4044_2016` | `xsd:long` | true | 0..1 |
| `m4044_2016` | `xsd:long` | true | 0..1 |
| `h4549_2016` | `xsd:long` | true | 0..1 |
| `m4549_2016` | `xsd:long` | true | 0..1 |
| `h50_2016` | `xsd:long` | true | 0..1 |
| `m50_2016` | `xsd:long` | true | 0..1 |
| `h_ign_2016` | `xsd:long` | true | 0..1 |
| `m_ign_2016` | `xsd:long` | true | 0..1 |
| `h15_2017` | `xsd:long` | true | 0..1 |
| `m15_2017` | `xsd:long` | true | 0..1 |
| `h1519_2017` | `xsd:long` | true | 0..1 |
| `m1519_2017` | `xsd:long` | true | 0..1 |
| `h2024_2017` | `xsd:long` | true | 0..1 |
| `m2024_2017` | `xsd:long` | true | 0..1 |
| `h2529_2017` | `xsd:long` | true | 0..1 |
| `m2529_2017` | `xsd:long` | true | 0..1 |
| `h3034_2017` | `xsd:long` | true | 0..1 |
| `m3034_2017` | `xsd:long` | true | 0..1 |
| `h3539_2017` | `xsd:long` | true | 0..1 |
| `m3539_2017` | `xsd:long` | true | 0..1 |
| `h4044_2017` | `xsd:long` | true | 0..1 |
| `m4044_2017` | `xsd:long` | true | 0..1 |
| `h4549_2017` | `xsd:long` | true | 0..1 |
| `m4549_2017` | `xsd:long` | true | 0..1 |
| `h50_2017` | `xsd:long` | true | 0..1 |
| `m50_2017` | `xsd:long` | true | 0..1 |
| `h_ign_2017` | `xsd:long` | true | 0..1 |
| `m_ign_2017` | `xsd:long` | true | 0..1 |
| `h15_2018` | `xsd:long` | true | 0..1 |
| `m15_2018` | `xsd:long` | true | 0..1 |
| `h1519_2018` | `xsd:long` | true | 0..1 |
| `m1519_2018` | `xsd:long` | true | 0..1 |
| `h2024_2018` | `xsd:long` | true | 0..1 |
| `m2024_2018` | `xsd:long` | true | 0..1 |
| `h2529_2018` | `xsd:long` | true | 0..1 |
| `m2529_2018` | `xsd:long` | true | 0..1 |
| `h3034_2018` | `xsd:long` | true | 0..1 |
| `m3034_2018` | `xsd:long` | true | 0..1 |
| `h3539_2018` | `xsd:long` | true | 0..1 |
| `m3539_2018` | `xsd:long` | true | 0..1 |
| `h4044_2018` | `xsd:long` | true | 0..1 |
| `m4044_2018` | `xsd:long` | true | 0..1 |
| `h4549_2018` | `xsd:long` | true | 0..1 |
| `m4549_2018` | `xsd:long` | true | 0..1 |
| `h50_2018` | `xsd:long` | true | 0..1 |
| `m50_2018` | `xsd:long` | true | 0..1 |
| `h_ign_2018` | `xsd:long` | true | 0..1 |
| `m_ign_2018` | `xsd:long` | true | 0..1 |

### `estatistica:numero_obitos_por_faixa_etaria_2009_a_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `de1_2009` | `xsd:long` | true | 0..1 |
| `de1a14_09` | `xsd:long` | true | 0..1 |
| `de15a19_09` | `xsd:long` | true | 0..1 |
| `de20a24_09` | `xsd:long` | true | 0..1 |
| `de25a29_09` | `xsd:long` | true | 0..1 |
| `de30a34_09` | `xsd:long` | true | 0..1 |
| `de35a39_20` | `xsd:long` | true | 0..1 |
| `de40a44_09` | `xsd:long` | true | 0..1 |
| `de45a49_09` | `xsd:long` | true | 0..1 |
| `de50a54_09` | `xsd:long` | true | 0..1 |
| `de55a59_09` | `xsd:long` | true | 0..1 |
| `de60a64_09` | `xsd:long` | true | 0..1 |
| `de65a69_20` | `xsd:long` | true | 0..1 |
| `de70a74_09` | `xsd:long` | true | 0..1 |
| `de75a79_09` | `xsd:long` | true | 0..1 |
| `de80a84_09` | `xsd:long` | true | 0..1 |
| `de85a89_09` | `xsd:long` | true | 0..1 |
| `de90a94_09` | `xsd:long` | true | 0..1 |
| `de95a99_09` | `xsd:long` | true | 0..1 |
| `de100_09` | `xsd:long` | true | 0..1 |
| `ign_2009` | `xsd:long` | true | 0..1 |
| `de1_2010` | `xsd:long` | true | 0..1 |
| `de1a14_10` | `xsd:long` | true | 0..1 |
| `de15a19_10` | `xsd:long` | true | 0..1 |
| `de20a24_10` | `xsd:long` | true | 0..1 |
| `de25a29_10` | `xsd:long` | true | 0..1 |
| `de30a34_10` | `xsd:long` | true | 0..1 |
| `de35a39__1` | `xsd:long` | true | 0..1 |
| `de40a44_10` | `xsd:long` | true | 0..1 |
| `de45a49_10` | `xsd:long` | true | 0..1 |
| `de50a54_10` | `xsd:long` | true | 0..1 |
| `de55a59_10` | `xsd:long` | true | 0..1 |
| `de60a64_10` | `xsd:long` | true | 0..1 |
| `de65a69_10` | `xsd:long` | true | 0..1 |
| `de70a74_10` | `xsd:long` | true | 0..1 |
| `de75a79_10` | `xsd:long` | true | 0..1 |
| `de80a84_10` | `xsd:long` | true | 0..1 |
| `de85a89_10` | `xsd:long` | true | 0..1 |
| `de90a94_10` | `xsd:long` | true | 0..1 |
| `de95a99_10` | `xsd:long` | true | 0..1 |
| `de100_10` | `xsd:long` | true | 0..1 |
| `ign_2010` | `xsd:long` | true | 0..1 |
| `de1_2011` | `xsd:long` | true | 0..1 |
| `de1a14_11` | `xsd:long` | true | 0..1 |
| `de15a19_11` | `xsd:long` | true | 0..1 |
| `de20a24_11` | `xsd:long` | true | 0..1 |
| `de25a29_11` | `xsd:long` | true | 0..1 |
| `de30a34_11` | `xsd:long` | true | 0..1 |
| `de35a39_11` | `xsd:long` | true | 0..1 |
| `de40a44_11` | `xsd:long` | true | 0..1 |
| `de45a49_11` | `xsd:long` | true | 0..1 |
| `de50a54_11` | `xsd:long` | true | 0..1 |
| `de55a59_11` | `xsd:long` | true | 0..1 |
| `de60a64_11` | `xsd:long` | true | 0..1 |
| `de65a69_11` | `xsd:long` | true | 0..1 |
| `de70a74_11` | `xsd:long` | true | 0..1 |
| `de75a79_11` | `xsd:long` | true | 0..1 |
| `de80a84_11` | `xsd:long` | true | 0..1 |
| `de85a89_11` | `xsd:long` | true | 0..1 |
| `de90a94_11` | `xsd:long` | true | 0..1 |
| `de95a99_11` | `xsd:long` | true | 0..1 |
| `de100_11` | `xsd:long` | true | 0..1 |
| `ign_2011` | `xsd:long` | true | 0..1 |
| `de1_2012` | `xsd:long` | true | 0..1 |
| `de1a14_12` | `xsd:long` | true | 0..1 |
| `de15a19_12` | `xsd:long` | true | 0..1 |
| `de20a24_12` | `xsd:long` | true | 0..1 |
| `de25a29_12` | `xsd:long` | true | 0..1 |
| `de30a34_12` | `xsd:long` | true | 0..1 |
| `de35a39_12` | `xsd:long` | true | 0..1 |
| `de40a44_12` | `xsd:long` | true | 0..1 |
| `de45a49_12` | `xsd:long` | true | 0..1 |
| `de50a54_12` | `xsd:long` | true | 0..1 |
| `de55a59_12` | `xsd:long` | true | 0..1 |
| `de60a64_12` | `xsd:long` | true | 0..1 |
| `de65a69_12` | `xsd:long` | true | 0..1 |
| `de70a74_12` | `xsd:long` | true | 0..1 |
| `de75a79_12` | `xsd:long` | true | 0..1 |
| `de80a84_12` | `xsd:long` | true | 0..1 |
| `de85a89_12` | `xsd:long` | true | 0..1 |
| `de90a94_12` | `xsd:long` | true | 0..1 |
| `de95a99_12` | `xsd:long` | true | 0..1 |
| `de100_12` | `xsd:long` | true | 0..1 |
| `ign_2012` | `xsd:long` | true | 0..1 |
| `de1_13` | `xsd:long` | true | 0..1 |
| `de1a14_13` | `xsd:long` | true | 0..1 |
| `de15a19_13` | `xsd:long` | true | 0..1 |
| `de20a24_13` | `xsd:long` | true | 0..1 |
| `de25a29_13` | `xsd:long` | true | 0..1 |
| `de30a34_13` | `xsd:long` | true | 0..1 |
| `de35a39_13` | `xsd:long` | true | 0..1 |
| `de40a44_13` | `xsd:long` | true | 0..1 |
| `de45a49_13` | `xsd:long` | true | 0..1 |
| `de50a54_13` | `xsd:long` | true | 0..1 |
| `de55a59_13` | `xsd:long` | true | 0..1 |
| `de60a64_13` | `xsd:long` | true | 0..1 |
| `de65a69_13` | `xsd:long` | true | 0..1 |
| `de70a74_13` | `xsd:long` | true | 0..1 |
| `de75a79_13` | `xsd:long` | true | 0..1 |
| `de80a84_13` | `xsd:long` | true | 0..1 |
| `de85a89_13` | `xsd:long` | true | 0..1 |
| `de90a94_13` | `xsd:long` | true | 0..1 |
| `de95a99_13` | `xsd:long` | true | 0..1 |
| `de100_13` | `xsd:long` | true | 0..1 |
| `ign_13` | `xsd:long` | true | 0..1 |
| `de1_14` | `xsd:long` | true | 0..1 |
| `de1a14_14` | `xsd:long` | true | 0..1 |
| `de15a19_14` | `xsd:long` | true | 0..1 |
| `de20a24_14` | `xsd:long` | true | 0..1 |
| `de25a29_14` | `xsd:long` | true | 0..1 |
| `de30a34_14` | `xsd:long` | true | 0..1 |
| `de35a39_14` | `xsd:long` | true | 0..1 |
| `de40a44_14` | `xsd:long` | true | 0..1 |
| `de45a49_14` | `xsd:long` | true | 0..1 |
| `de50a54_14` | `xsd:long` | true | 0..1 |
| `de55a59_14` | `xsd:long` | true | 0..1 |
| `de60a64_14` | `xsd:long` | true | 0..1 |
| `de65a69_14` | `xsd:long` | true | 0..1 |
| `de70a74_14` | `xsd:long` | true | 0..1 |
| `de75a79_14` | `xsd:long` | true | 0..1 |
| `de80a84_14` | `xsd:long` | true | 0..1 |
| `de85a89_14` | `xsd:long` | true | 0..1 |
| `de90a94_14` | `xsd:long` | true | 0..1 |
| `de95a99_14` | `xsd:long` | true | 0..1 |
| `de100_14` | `xsd:long` | true | 0..1 |
| `ign_14` | `xsd:long` | true | 0..1 |
| `de1_15` | `xsd:long` | true | 0..1 |
| `de1a14_15` | `xsd:long` | true | 0..1 |
| `de15a19_15` | `xsd:long` | true | 0..1 |
| `de20a24_15` | `xsd:long` | true | 0..1 |
| `de25a29_15` | `xsd:long` | true | 0..1 |
| `de30a34_15` | `xsd:long` | true | 0..1 |
| `de35a39_15` | `xsd:long` | true | 0..1 |
| `de40a44_15` | `xsd:long` | true | 0..1 |
| `de45a49_15` | `xsd:long` | true | 0..1 |
| `de50a54_15` | `xsd:long` | true | 0..1 |
| `de55a59_15` | `xsd:long` | true | 0..1 |
| `de60a64_15` | `xsd:long` | true | 0..1 |
| `de65a69_15` | `xsd:long` | true | 0..1 |
| `de70a74_15` | `xsd:long` | true | 0..1 |
| `de75a79_15` | `xsd:long` | true | 0..1 |
| `de80a84_15` | `xsd:long` | true | 0..1 |
| `de85a89_15` | `xsd:long` | true | 0..1 |
| `de90a94_15` | `xsd:long` | true | 0..1 |
| `de95a99_15` | `xsd:long` | true | 0..1 |
| `de100_15` | `xsd:long` | true | 0..1 |
| `ign_2015` | `xsd:long` | true | 0..1 |
| `de1_16` | `xsd:long` | true | 0..1 |
| `de1a14_16` | `xsd:long` | true | 0..1 |
| `de15a19_16` | `xsd:long` | true | 0..1 |
| `de20a24_16` | `xsd:long` | true | 0..1 |
| `de25a29_16` | `xsd:long` | true | 0..1 |
| `de30a34_16` | `xsd:long` | true | 0..1 |
| `de35a39_16` | `xsd:long` | true | 0..1 |
| `de40a44_16` | `xsd:long` | true | 0..1 |
| `de45a49_16` | `xsd:long` | true | 0..1 |
| `de50a54_16` | `xsd:long` | true | 0..1 |
| `de55a59_16` | `xsd:long` | true | 0..1 |
| `de60a64_16` | `xsd:long` | true | 0..1 |
| `de65a69_16` | `xsd:long` | true | 0..1 |
| `de70a74_16` | `xsd:long` | true | 0..1 |
| `de75a79_16` | `xsd:long` | true | 0..1 |
| `de80a84_16` | `xsd:long` | true | 0..1 |
| `de85a89_16` | `xsd:long` | true | 0..1 |
| `de90a94_16` | `xsd:long` | true | 0..1 |
| `de95a99_16` | `xsd:long` | true | 0..1 |
| `de100_16` | `xsd:long` | true | 0..1 |
| `ign_16` | `xsd:long` | true | 0..1 |
| `de1_2017` | `xsd:long` | true | 0..1 |
| `de1a14_17` | `xsd:long` | true | 0..1 |
| `de15a19_17` | `xsd:long` | true | 0..1 |
| `de20a24_17` | `xsd:long` | true | 0..1 |
| `de25a29_17` | `xsd:long` | true | 0..1 |
| `de30a34_17` | `xsd:long` | true | 0..1 |
| `de35a39_17` | `xsd:long` | true | 0..1 |
| `de40a44_17` | `xsd:long` | true | 0..1 |
| `de45a49_17` | `xsd:long` | true | 0..1 |
| `de50a54_17` | `xsd:long` | true | 0..1 |
| `de55a59_17` | `xsd:long` | true | 0..1 |
| `de60a64_17` | `xsd:long` | true | 0..1 |
| `de65a69_17` | `xsd:long` | true | 0..1 |
| `de70a74_17` | `xsd:long` | true | 0..1 |
| `de75a79_17` | `xsd:long` | true | 0..1 |
| `de80a84_17` | `xsd:long` | true | 0..1 |
| `de85a89_17` | `xsd:long` | true | 0..1 |
| `de90a94_17` | `xsd:long` | true | 0..1 |
| `de95a99_17` | `xsd:long` | true | 0..1 |
| `de100_17` | `xsd:long` | true | 0..1 |
| `ign_17` | `xsd:long` | true | 0..1 |
| `de1_18` | `xsd:long` | true | 0..1 |
| `de1a14_18` | `xsd:long` | true | 0..1 |
| `de15a19_18` | `xsd:long` | true | 0..1 |
| `de20a24_18` | `xsd:long` | true | 0..1 |
| `de25a29_18` | `xsd:long` | true | 0..1 |
| `de30a34_18` | `xsd:long` | true | 0..1 |
| `de35a39_18` | `xsd:long` | true | 0..1 |
| `de40a44_18` | `xsd:long` | true | 0..1 |
| `de45a49_18` | `xsd:long` | true | 0..1 |
| `de50a54_18` | `xsd:long` | true | 0..1 |
| `de55a59_18` | `xsd:long` | true | 0..1 |
| `de60a64_18` | `xsd:long` | true | 0..1 |
| `de65a69_18` | `xsd:long` | true | 0..1 |
| `de70a74_18` | `xsd:long` | true | 0..1 |
| `de75a79_18` | `xsd:long` | true | 0..1 |
| `de80a84_18` | `xsd:long` | true | 0..1 |
| `de85a89_18` | `xsd:long` | true | 0..1 |
| `de90a94_18` | `xsd:long` | true | 0..1 |
| `de95a99_18` | `xsd:long` | true | 0..1 |
| `de100_18` | `xsd:long` | true | 0..1 |
| `ign_18` | `xsd:long` | true | 0..1 |

### `estatistica:obitos_por_causa_morte_2009_2010_2013_2014_2015`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `infec_2009` | `xsd:long` | true | 0..1 |
| `neopl_2009` | `xsd:long` | true | 0..1 |
| `endoc_2009` | `xsd:long` | true | 0..1 |
| `circu_2009` | `xsd:long` | true | 0..1 |
| `respi_2009` | `xsd:long` | true | 0..1 |
| `diges_2009` | `xsd:long` | true | 0..1 |
| `perin_2009` | `xsd:long` | true | 0..1 |
| `no_cl_2009` | `xsd:long` | true | 0..1 |
| `c_ext_2009` | `xsd:long` | true | 0..1 |
| `outra_2009` | `xsd:long` | true | 0..1 |
| `infec_2010` | `xsd:long` | true | 0..1 |
| `neopl_2010` | `xsd:long` | true | 0..1 |
| `endoc_2010` | `xsd:long` | true | 0..1 |
| `circu_2010` | `xsd:long` | true | 0..1 |
| `respi_2010` | `xsd:long` | true | 0..1 |
| `diges_2010` | `xsd:long` | true | 0..1 |
| `perin_2010` | `xsd:long` | true | 0..1 |
| `no_cl_2010` | `xsd:long` | true | 0..1 |
| `c_ext_2010` | `xsd:long` | true | 0..1 |
| `outra_2010` | `xsd:long` | true | 0..1 |
| `infec_2013` | `xsd:long` | true | 0..1 |
| `neopl_2013` | `xsd:long` | true | 0..1 |
| `endoc_2013` | `xsd:long` | true | 0..1 |
| `circu_2013` | `xsd:long` | true | 0..1 |
| `respi_2013` | `xsd:long` | true | 0..1 |
| `diges_2013` | `xsd:long` | true | 0..1 |
| `perin_2013` | `xsd:long` | true | 0..1 |
| `no_cl_2013` | `xsd:long` | true | 0..1 |
| `c_ext_2013` | `xsd:long` | true | 0..1 |
| `outra_2013` | `xsd:long` | true | 0..1 |
| `infec_2014` | `xsd:long` | true | 0..1 |
| `neopl_2014` | `xsd:long` | true | 0..1 |
| `endoc_2014` | `xsd:long` | true | 0..1 |
| `circu_2014` | `xsd:long` | true | 0..1 |
| `respi_2014` | `xsd:long` | true | 0..1 |
| `diges_2014` | `xsd:long` | true | 0..1 |
| `perin_2014` | `xsd:long` | true | 0..1 |
| `no_cl_2014` | `xsd:long` | true | 0..1 |
| `c_ext_2014` | `xsd:long` | true | 0..1 |
| `outra_2014` | `xsd:long` | true | 0..1 |
| `infec_2015` | `xsd:long` | true | 0..1 |
| `neopl_2015` | `xsd:long` | true | 0..1 |
| `endoc_2015` | `xsd:long` | true | 0..1 |
| `circu_2015` | `xsd:long` | true | 0..1 |
| `respi_2015` | `xsd:long` | true | 0..1 |
| `diges_2015` | `xsd:long` | true | 0..1 |
| `perin_2015` | `xsd:long` | true | 0..1 |
| `no_cl_2015` | `xsd:long` | true | 0..1 |
| `c_ext_2015` | `xsd:long` | true | 0..1 |
| `outra_2015` | `xsd:long` | true | 0..1 |

### `estatistica:ovino`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `ovino_1989` | `xsd:long` | true | 0..1 |
| `ovino_1990` | `xsd:long` | true | 0..1 |
| `ovino_1991` | `xsd:long` | true | 0..1 |
| `ovino_1992` | `xsd:long` | true | 0..1 |
| `ovino_1993` | `xsd:long` | true | 0..1 |
| `ovino_1994` | `xsd:long` | true | 0..1 |
| `ovino_1995` | `xsd:long` | true | 0..1 |
| `ovino_1996` | `xsd:long` | true | 0..1 |
| `ovino_1997` | `xsd:long` | true | 0..1 |
| `ovino_1998` | `xsd:long` | true | 0..1 |
| `ovino_1999` | `xsd:long` | true | 0..1 |
| `ovino_2000` | `xsd:long` | true | 0..1 |
| `ovino_2001` | `xsd:long` | true | 0..1 |
| `ovino_2002` | `xsd:long` | true | 0..1 |
| `ovino_2003` | `xsd:long` | true | 0..1 |
| `ovino_2004` | `xsd:long` | true | 0..1 |
| `ovino_2005` | `xsd:long` | true | 0..1 |
| `ovino_2006` | `xsd:long` | true | 0..1 |
| `ovino_2007` | `xsd:long` | true | 0..1 |
| `ovino_2008` | `xsd:long` | true | 0..1 |
| `ovino_2009` | `xsd:long` | true | 0..1 |
| `ovino_2010` | `xsd:long` | true | 0..1 |
| `ovino_2011` | `xsd:long` | true | 0..1 |
| `ovino_2012` | `xsd:long` | true | 0..1 |
| `ovino_2013` | `xsd:long` | true | 0..1 |
| `ovino_2014` | `xsd:long` | true | 0..1 |
| `ovino_2015` | `xsd:long` | true | 0..1 |
| `ovino_2016` | `xsd:long` | true | 0..1 |
| `ovino_2017` | `xsd:long` | true | 0..1 |
| `ovino_2018` | `xsd:long` | true | 0..1 |

### `estatistica:ovos_galinha_1989_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `ovogal1989` | `xsd:long` | true | 0..1 |
| `ovogal1990` | `xsd:long` | true | 0..1 |
| `ovogal1991` | `xsd:long` | true | 0..1 |
| `ovogal1992` | `xsd:long` | true | 0..1 |
| `ovogal1993` | `xsd:long` | true | 0..1 |
| `ovogal1994` | `xsd:long` | true | 0..1 |
| `ovogal1995` | `xsd:long` | true | 0..1 |
| `ovogal1996` | `xsd:long` | true | 0..1 |
| `ovogal1997` | `xsd:long` | true | 0..1 |
| `ovogal1998` | `xsd:long` | true | 0..1 |
| `ovogal1999` | `xsd:long` | true | 0..1 |
| `ovogal2000` | `xsd:long` | true | 0..1 |
| `ovogal2001` | `xsd:long` | true | 0..1 |
| `ovogal2002` | `xsd:long` | true | 0..1 |
| `ovogal2003` | `xsd:long` | true | 0..1 |
| `ovogal2004` | `xsd:long` | true | 0..1 |
| `ovogal2005` | `xsd:long` | true | 0..1 |
| `ovogal2006` | `xsd:long` | true | 0..1 |
| `ovogal2007` | `xsd:long` | true | 0..1 |
| `ovogal2008` | `xsd:long` | true | 0..1 |
| `ovogal2009` | `xsd:long` | true | 0..1 |
| `ovogal2010` | `xsd:long` | true | 0..1 |
| `ovogal2011` | `xsd:long` | true | 0..1 |
| `ovogal2012` | `xsd:long` | true | 0..1 |
| `ovogal2013` | `xsd:long` | true | 0..1 |
| `ovogal2014` | `xsd:long` | true | 0..1 |
| `ovogal2015` | `xsd:long` | true | 0..1 |
| `ovogal2016` | `xsd:long` | true | 0..1 |
| `ovogal2017` | `xsd:long` | true | 0..1 |
| `ovogal2018` | `xsd:long` | true | 0..1 |

### `estatistica:pib_e_pib_por_capita`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `nume_cid` | `xsd:string` | true | 0..1 |
| `pgai` | `xsd:string` | true | 0..1 |
| `tipo_cidd` | `xsd:string` | true | 0..1 |
| `regiao_num` | `xsd:string` | true | 0..1 |
| `territ_cid` | `xsd:string` | true | 0..1 |
| `utr` | `xsd:string` | true | 0..1 |
| `criacao` | `xsd:string` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `pop_1996` | `xsd:double` | true | 0..1 |
| `pop_2000` | `xsd:double` | true | 0..1 |
| `pop_2007` | `xsd:double` | true | 0..1 |
| `pop_2008` | `xsd:double` | true | 0..1 |
| `pop_2009` | `xsd:double` | true | 0..1 |
| `assoc_mun` | `xsd:string` | true | 0..1 |
| `reg_pm` | `xsd:string` | true | 0..1 |
| `art_pm` | `xsd:string` | true | 0..1 |
| `region_ibg` | `xsd:string` | true | 0..1 |
| `cod_region` | `xsd:double` | true | 0..1 |
| `pop_2010` | `xsd:double` | true | 0..1 |
| `ppa_2012_2` | `xsd:string` | true | 0..1 |
| `number` | `xsd:double` | true | 0..1 |
| `regionaliz` | `xsd:string` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `reg_tur` | `xsd:string` | true | 0..1 |
| `nova_regio` | `xsd:string` | true | 0..1 |
| `nova_reg_o` | `xsd:string` | true | 0..1 |
| `munic` | `xsd:string` | true | 0..1 |
| `pib10_1000` | `xsd:double` | true | 0..1 |
| `pib11_1000` | `xsd:double` | true | 0..1 |
| `pib12_1000` | `xsd:double` | true | 0..1 |
| `pib13_1000` | `xsd:double` | true | 0..1 |
| `pib14_1000` | `xsd:double` | true | 0..1 |
| `pib15_1000` | `xsd:double` | true | 0..1 |
| `pib16_1000` | `xsd:double` | true | 0..1 |
| `pcap_2010` | `xsd:double` | true | 0..1 |
| `pcap_2011` | `xsd:double` | true | 0..1 |
| `pcap_2012` | `xsd:double` | true | 0..1 |
| `pcap_2013` | `xsd:double` | true | 0..1 |
| `pcap_2014` | `xsd:double` | true | 0..1 |
| `pcap_2015` | `xsd:double` | true | 0..1 |
| `pcap_2016` | `xsd:double` | true | 0..1 |

### `estatistica:popul_resid_cor_raca_sexo_situacao`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `nume_cid` | `xsd:string` | true | 0..1 |
| `pgai` | `xsd:string` | true | 0..1 |
| `tipo_cidd` | `xsd:string` | true | 0..1 |
| `regiao_num` | `xsd:string` | true | 0..1 |
| `territ_cid` | `xsd:string` | true | 0..1 |
| `utr` | `xsd:string` | true | 0..1 |
| `criacao` | `xsd:string` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `pop_1996` | `xsd:double` | true | 0..1 |
| `pop_2000` | `xsd:double` | true | 0..1 |
| `pop_2007` | `xsd:double` | true | 0..1 |
| `pop_2008` | `xsd:double` | true | 0..1 |
| `pop_2009` | `xsd:double` | true | 0..1 |
| `assoc_mun` | `xsd:string` | true | 0..1 |
| `reg_pm` | `xsd:string` | true | 0..1 |
| `art_pm` | `xsd:string` | true | 0..1 |
| `region_ibg` | `xsd:string` | true | 0..1 |
| `cod_region` | `xsd:double` | true | 0..1 |
| `pop_2010` | `xsd:double` | true | 0..1 |
| `ppa_2012_2` | `xsd:string` | true | 0..1 |
| `number` | `xsd:double` | true | 0..1 |
| `regionaliz` | `xsd:string` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `reg_tur` | `xsd:string` | true | 0..1 |
| `nova_regio` | `xsd:string` | true | 0..1 |
| `nova_reg_o` | `xsd:string` | true | 0..1 |
| `muncipio` | `xsd:string` | true | 0..1 |
| `grup_idade` | `xsd:string` | true | 0..1 |
| `total_2000` | `xsd:double` | true | 0..1 |
| `tot_hom_00` | `xsd:double` | true | 0..1 |
| `tot_mul_00` | `xsd:double` | true | 0..1 |
| `urb_tot_00` | `xsd:double` | true | 0..1 |
| `urb_hom_00` | `xsd:double` | true | 0..1 |
| `urb_mul_00` | `xsd:double` | true | 0..1 |
| `rur_tot_00` | `xsd:double` | true | 0..1 |
| `rur_hom_00` | `xsd:double` | true | 0..1 |
| `rur_mul_00` | `xsd:double` | true | 0..1 |
| `total_2010` | `xsd:double` | true | 0..1 |
| `tot_hom_10` | `xsd:double` | true | 0..1 |
| `tot_mul_10` | `xsd:double` | true | 0..1 |
| `urb_tot_10` | `xsd:double` | true | 0..1 |
| `urb_hom_10` | `xsd:double` | true | 0..1 |
| `urb_mul_10` | `xsd:double` | true | 0..1 |
| `rur_tot_10` | `xsd:double` | true | 0..1 |
| `rur_hom_10` | `xsd:double` | true | 0..1 |
| `rur_mul_10` | `xsd:double` | true | 0..1 |

### `estatistica:popul_resid_por_situacao_do_domicilio_e_sexo_2010`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `nume_cid` | `xsd:string` | true | 0..1 |
| `pgai` | `xsd:string` | true | 0..1 |
| `tipo_cidd` | `xsd:string` | true | 0..1 |
| `regiao_num` | `xsd:string` | true | 0..1 |
| `territ_cid` | `xsd:string` | true | 0..1 |
| `utr` | `xsd:string` | true | 0..1 |
| `criacao` | `xsd:string` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `pop_1996` | `xsd:double` | true | 0..1 |
| `pop_2000` | `xsd:double` | true | 0..1 |
| `pop_2007` | `xsd:double` | true | 0..1 |
| `pop_2008` | `xsd:double` | true | 0..1 |
| `pop_2009` | `xsd:double` | true | 0..1 |
| `assoc_mun` | `xsd:string` | true | 0..1 |
| `reg_pm` | `xsd:string` | true | 0..1 |
| `art_pm` | `xsd:string` | true | 0..1 |
| `region_ibg` | `xsd:string` | true | 0..1 |
| `cod_region` | `xsd:double` | true | 0..1 |
| `pop_2010` | `xsd:double` | true | 0..1 |
| `ppa_2012_2` | `xsd:string` | true | 0..1 |
| `number` | `xsd:double` | true | 0..1 |
| `regionaliz` | `xsd:string` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `reg_tur` | `xsd:string` | true | 0..1 |
| `nova_regio` | `xsd:string` | true | 0..1 |
| `nova_reg_o` | `xsd:string` | true | 0..1 |
| `tot_p_res` | `xsd:double` | true | 0..1 |
| `hom_tot` | `xsd:double` | true | 0..1 |
| `mulh_tot` | `xsd:double` | true | 0..1 |
| `tot_urb` | `xsd:double` | true | 0..1 |
| `hom_urb` | `xsd:double` | true | 0..1 |
| `mulh_urb` | `xsd:double` | true | 0..1 |
| `tot_rur` | `xsd:double` | true | 0..1 |
| `hom_rur` | `xsd:double` | true | 0..1 |
| `mulh_rur` | `xsd:double` | true | 0..1 |

### `estatistica:populacao_censitaria_municip_1991_2000_2010`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `nume_cid` | `xsd:string` | true | 0..1 |
| `pgai` | `xsd:string` | true | 0..1 |
| `tipo_cidd` | `xsd:string` | true | 0..1 |
| `regiao_num` | `xsd:string` | true | 0..1 |
| `territ_cid` | `xsd:string` | true | 0..1 |
| `utr` | `xsd:string` | true | 0..1 |
| `criacao` | `xsd:string` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `pop_1996` | `xsd:double` | true | 0..1 |
| `pop_2000` | `xsd:double` | true | 0..1 |
| `pop_2007` | `xsd:double` | true | 0..1 |
| `pop_2008` | `xsd:double` | true | 0..1 |
| `pop_2009` | `xsd:double` | true | 0..1 |
| `assoc_mun` | `xsd:string` | true | 0..1 |
| `reg_pm` | `xsd:string` | true | 0..1 |
| `art_pm` | `xsd:string` | true | 0..1 |
| `region_ibg` | `xsd:string` | true | 0..1 |
| `cod_region` | `xsd:double` | true | 0..1 |
| `pop_2010` | `xsd:double` | true | 0..1 |
| `ppa_2012_2` | `xsd:string` | true | 0..1 |
| `number` | `xsd:double` | true | 0..1 |
| `regionaliz` | `xsd:string` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `reg_tur` | `xsd:string` | true | 0..1 |
| `nova_regio` | `xsd:string` | true | 0..1 |
| `nova_reg_o` | `xsd:string` | true | 0..1 |
| `pop_1991` | `xsd:double` | true | 0..1 |
| `pop_2000_1` | `xsd:double` | true | 0..1 |
| `pop_2010_1` | `xsd:double` | true | 0..1 |
| `max_pop` | `xsd:int` | true | 0..1 |

### `estatistica:suino1989_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `suino_1989` | `xsd:long` | true | 0..1 |
| `suino_1990` | `xsd:long` | true | 0..1 |
| `suino_1991` | `xsd:long` | true | 0..1 |
| `suino_1992` | `xsd:long` | true | 0..1 |
| `suino_1993` | `xsd:long` | true | 0..1 |
| `suino_1994` | `xsd:long` | true | 0..1 |
| `suino_1995` | `xsd:long` | true | 0..1 |
| `suino_1996` | `xsd:long` | true | 0..1 |
| `suino_1997` | `xsd:long` | true | 0..1 |
| `suino_1998` | `xsd:long` | true | 0..1 |
| `suino_1999` | `xsd:long` | true | 0..1 |
| `suino_2000` | `xsd:long` | true | 0..1 |
| `suino_2001` | `xsd:long` | true | 0..1 |
| `suino_2002` | `xsd:long` | true | 0..1 |
| `suino_2003` | `xsd:long` | true | 0..1 |
| `suino_2004` | `xsd:long` | true | 0..1 |
| `suino_2005` | `xsd:long` | true | 0..1 |
| `suino_2006` | `xsd:long` | true | 0..1 |
| `suino_2007` | `xsd:long` | true | 0..1 |
| `suino_2008` | `xsd:long` | true | 0..1 |
| `suino_2009` | `xsd:long` | true | 0..1 |
| `suino_2010` | `xsd:long` | true | 0..1 |
| `suino_2011` | `xsd:long` | true | 0..1 |
| `suino_2012` | `xsd:long` | true | 0..1 |
| `suino_2013` | `xsd:long` | true | 0..1 |
| `suino_2014` | `xsd:long` | true | 0..1 |
| `suino_2015` | `xsd:long` | true | 0..1 |
| `suino_2016` | `xsd:long` | true | 0..1 |
| `suino_2017` | `xsd:long` | true | 0..1 |
| `suino_2018` | `xsd:long` | true | 0..1 |

### `estatistica:taxa_abandono_2013`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `ta_ef_eur` | `xsd:double` | true | 0..1 |
| `ta_ef_eru` | `xsd:double` | true | 0..1 |
| `ta_ef_mur` | `xsd:double` | true | 0..1 |
| `ta_ef_mru` | `xsd:double` | true | 0..1 |
| `ta_ef_pur` | `xsd:double` | true | 0..1 |
| `ta_ef_pru` | `xsd:double` | true | 0..1 |
| `ta_em_eur` | `xsd:double` | true | 0..1 |
| `ta_em_eru` | `xsd:double` | true | 0..1 |
| `ta_em_mru` | `xsd:double` | true | 0..1 |
| `ta_em_pur` | `xsd:double` | true | 0..1 |
| `ta_em_fur` | `xsd:double` | true | 0..1 |
| `ta_em_fru` | `xsd:long` | true | 0..1 |

### `estatistica:taxa_abandono_2015`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `ta_ef_eur` | `xsd:double` | true | 0..1 |
| `ta_ef_eru` | `xsd:double` | true | 0..1 |
| `ta_ef_mur` | `xsd:double` | true | 0..1 |
| `ta_ef_mru` | `xsd:double` | true | 0..1 |
| `ta_ef_pur` | `xsd:double` | true | 0..1 |
| `ta_em_eur` | `xsd:double` | true | 0..1 |
| `ta_em_eru` | `xsd:double` | true | 0..1 |
| `ta_em_mru` | `xsd:double` | true | 0..1 |
| `ta_em_pur` | `xsd:double` | true | 0..1 |
| `ta_em_fur` | `xsd:double` | true | 0..1 |
| `ta_em_fru` | `xsd:double` | true | 0..1 |

### `estatistica:taxa_aprovacao_2013`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `ta_ef_eur` | `xsd:double` | true | 0..1 |
| `ta_ef_eru` | `xsd:double` | true | 0..1 |
| `ta_ef_mur` | `xsd:double` | true | 0..1 |
| `ta_ef_mru` | `xsd:double` | true | 0..1 |
| `ta_ef_pur` | `xsd:double` | true | 0..1 |
| `ta_ef_pru` | `xsd:double` | true | 0..1 |
| `ta_em_eur` | `xsd:double` | true | 0..1 |
| `ta_em_eru` | `xsd:double` | true | 0..1 |
| `ta_em_mru` | `xsd:double` | true | 0..1 |
| `ta_em_pur` | `xsd:double` | true | 0..1 |
| `ta_me_pru` | `xsd:double` | true | 0..1 |
| `ta_em_fur` | `xsd:double` | true | 0..1 |
| `ta_em_fru` | `xsd:double` | true | 0..1 |

### `estatistica:taxa_de_aprovacao_2015`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `cod_ibge_1` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `abe` | `xsd:double` | true | 0..1 |
| `ta_ef_eru` | `xsd:double` | true | 0..1 |
| `ta_ef_eur` | `xsd:double` | true | 0..1 |
| `ta_ef_mru` | `xsd:double` | true | 0..1 |
| `ta_ef_mur` | `xsd:double` | true | 0..1 |
| `ta_ef_pru` | `xsd:double` | true | 0..1 |
| `ta_ef_pur` | `xsd:double` | true | 0..1 |
| `ta_em_eru` | `xsd:double` | true | 0..1 |
| `ta_em_eur` | `xsd:double` | true | 0..1 |
| `ta_em_fru` | `xsd:double` | true | 0..1 |
| `ta_em_fur` | `xsd:double` | true | 0..1 |
| `ta_em_mru` | `xsd:double` | true | 0..1 |
| `ta_em_pur` | `xsd:double` | true | 0..1 |

### `estatistica:taxa_de_distorcao_2013`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge_1_1` | `xsd:long` | true | 0..1 |
| `nome_1` | `xsd:string` | true | 0..1 |
| `ti_snf_eur` | `xsd:double` | true | 0..1 |
| `ti_stf_eru` | `xsd:long` | true | 0..1 |
| `ti_stf_mru` | `xsd:long` | true | 0..1 |
| `ti_stf_mur` | `xsd:double` | true | 0..1 |
| `ti_stf_pru` | `xsd:long` | true | 0..1 |
| `ti_stf_pur` | `xsd:long` | true | 0..1 |
| `ti_stm_eru` | `xsd:long` | true | 0..1 |
| `ti_stm_eur` | `xsd:double` | true | 0..1 |
| `ti_stm_fru` | `xsd:long` | true | 0..1 |
| `ti_stm_fur` | `xsd:long` | true | 0..1 |
| `ti_stm_mru` | `xsd:long` | true | 0..1 |
| `ti_stm_pru` | `xsd:long` | true | 0..1 |
| `ti_stm_pur` | `xsd:long` | true | 0..1 |

### `estatistica:taxa_de_distorcao_2015`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `ti_sf_eur` | `xsd:double` | true | 0..1 |
| `ti_stf_eru` | `xsd:long` | true | 0..1 |
| `ti_stf_mur` | `xsd:long` | true | 0..1 |
| `ti_stf_mru` | `xsd:long` | true | 0..1 |
| `ti_stf_pur` | `xsd:long` | true | 0..1 |
| `ti_stf_pru` | `xsd:long` | true | 0..1 |
| `ti_stm_eur` | `xsd:double` | true | 0..1 |
| `ti_stm_eru` | `xsd:long` | true | 0..1 |
| `ti_stm_mru` | `xsd:long` | true | 0..1 |
| `ti_stm_pur` | `xsd:long` | true | 0..1 |
| `ti_stm_pru` | `xsd:long` | true | 0..1 |
| `ti_stm_fur` | `xsd:long` | true | 0..1 |
| `ti_stm_fru` | `xsd:long` | true | 0..1 |

### `estatistica:taxa_de_mortalidade_infantil_2008_a_2015`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `m_inf_2008` | `xsd:double` | true | 0..1 |
| `m_inf_2009` | `xsd:long` | true | 0..1 |
| `m_inf_2010` | `xsd:long` | true | 0..1 |
| `m_inf_2011` | `xsd:long` | true | 0..1 |
| `m_inf_2012` | `xsd:long` | true | 0..1 |
| `m_inf_2013` | `xsd:long` | true | 0..1 |
| `m_inf_2014` | `xsd:double` | true | 0..1 |
| `m_inf_2015` | `xsd:long` | true | 0..1 |

### `estatistica:taxa_de_reprovacao_2013`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tr_efu_eur` | `xsd:double` | true | 0..1 |
| `tr_efu_eru` | `xsd:double` | true | 0..1 |
| `tr_efu_mur` | `xsd:double` | true | 0..1 |
| `tr_efu_mru` | `xsd:double` | true | 0..1 |
| `tr_efu_pur` | `xsd:double` | true | 0..1 |
| `tr_efu_pru` | `xsd:double` | true | 0..1 |
| `tr_eme_eur` | `xsd:double` | true | 0..1 |
| `tr_eme_eru` | `xsd:double` | true | 0..1 |
| `tr_eme_mru` | `xsd:long` | true | 0..1 |
| `tr_eme_pur` | `xsd:double` | true | 0..1 |
| `tr_eme_pru` | `xsd:double` | true | 0..1 |
| `tr_eme_fur` | `xsd:double` | true | 0..1 |
| `tr_eme_fru` | `xsd:double` | true | 0..1 |

### `estatistica:taxa_de_reprovacao_2015`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tr_efu_eur` | `xsd:double` | true | 0..1 |
| `tr_efu_eru` | `xsd:double` | true | 0..1 |
| `tr_efu_mur` | `xsd:double` | true | 0..1 |
| `tr_efu_mru` | `xsd:double` | true | 0..1 |
| `tr_efu_pur` | `xsd:double` | true | 0..1 |
| `tr_efu_pru` | `xsd:double` | true | 0..1 |

## hidrogeologico (14)

### `hidrogeologico:AreaEstudo_A`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `NM_IDENTIF` | `xsd:string` | true | 0..1 |
| `Area` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `hidrogeologico:CobUso_2015_A`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Leg_Simple` | `xsd:string` | true | 0..1 |
| `Uso_2015` | `xsd:string` | true | 0..1 |
| `Cob_Uso` | `xsd:string` | true | 0..1 |
| `F2015_Resum` | `xsd:string` | true | 0..1 |
| `SHAPE_Length` | `xsd:double` | true | 0..1 |
| `SHAPE_Area` | `xsd:double` | true | 0..1 |

### `hidrogeologico:Fitoecologico_A`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Assoc_Cont` | `xsd:string` | true | 0..1 |
| `Leg_Final` | `xsd:string` | true | 0..1 |
| `Leg_Simple` | `xsd:string` | true | 0..1 |
| `Regioes` | `xsd:string` | true | 0..1 |
| `Formacoes` | `xsd:string` | true | 0..1 |
| `Subtipos_F` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `hidrogeologico:Geologia_A`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `NOME_UNIDA` | `xsd:string` | true | 0..1 |
| `SIGLA_UNID` | `xsd:string` | true | 0..1 |
| `HIERARQUIA` | `xsd:string` | true | 0..1 |
| `IDADE_MAX` | `xsd:double` | true | 0..1 |
| `ERRO_MAX` | `xsd:double` | true | 0..1 |
| `EON_ID_MAX` | `xsd:string` | true | 0..1 |
| `ERA_MAXIMA` | `xsd:string` | true | 0..1 |
| `PERIOD_MAX` | `xsd:string` | true | 0..1 |
| `EPOCA_MAX` | `xsd:string` | true | 0..1 |
| `MET_ID_MAX` | `xsd:string` | true | 0..1 |
| `MET_DAT_MA` | `xsd:string` | true | 0..1 |
| `QLD_ID_MAX` | `xsd:string` | true | 0..1 |
| `IDADE_MIN` | `xsd:double` | true | 0..1 |
| `ERRO_MIN` | `xsd:double` | true | 0..1 |
| `EON_ID_MIN` | `xsd:string` | true | 0..1 |
| `ERA_MINIMA` | `xsd:string` | true | 0..1 |
| `PERIODO_MI` | `xsd:string` | true | 0..1 |
| `EPOCA_MIN` | `xsd:string` | true | 0..1 |
| `MET_ID_MIN` | `xsd:string` | true | 0..1 |
| `MET_DAT_MI` | `xsd:string` | true | 0..1 |
| `QLD_ID_MIN` | `xsd:string` | true | 0..1 |
| `AMBSED` | `xsd:string` | true | 0..1 |
| `SISTSED` | `xsd:string` | true | 0..1 |
| `TIPO_DEP` | `xsd:string` | true | 0..1 |
| `ASSOC_MAGM` | `xsd:string` | true | 0..1 |
| `NIVEL_CRUS` | `xsd:string` | true | 0..1 |
| `TEXT_IGNEA` | `xsd:string` | true | 0..1 |
| `FONTE_MAGM` | `xsd:string` | true | 0..1 |
| `MORFOLOGIA` | `xsd:string` | true | 0..1 |
| `AMB_TECTO` | `xsd:string` | true | 0..1 |
| `METAMORF` | `xsd:string` | true | 0..1 |
| `TRAJET_PT` | `xsd:string` | true | 0..1 |
| `LITOTIPO1` | `xsd:string` | true | 0..1 |
| `LITOTIPO2` | `xsd:string` | true | 0..1 |
| `CLASSE_RX1` | `xsd:string` | true | 0..1 |
| `CLASSE_RX2` | `xsd:string` | true | 0..1 |
| `SUBCLA_RX1` | `xsd:string` | true | 0..1 |
| `SUBCLA_RX2` | `xsd:string` | true | 0..1 |
| `Leg` | `xsd:string` | true | 0..1 |
| `RGB` | `xsd:string` | true | 0..1 |
| `Dominio` | `xsd:string` | true | 0..1 |
| `Legenda` | `xsd:string` | true | 0..1 |
| `SHAPE_Length` | `xsd:double` | true | 0..1 |
| `SHAPE_Area` | `xsd:double` | true | 0..1 |

### `hidrogeologico:Geomofologia_A`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `CD_UNID_GE` | `xsd:double` | true | 0..1 |
| `NM_UNID_GE` | `xsd:string` | true | 0..1 |
| `Dominios` | `xsd:string` | true | 0..1 |
| `SHAPE_Length` | `xsd:double` | true | 0..1 |
| `SHAPE_Area` | `xsd:double` | true | 0..1 |

### `hidrogeologico:Pedologia_A`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID_1` | `xsd:long` | true | 0..1 |
| `OBJECTID` | `xsd:int` | true | 0..1 |
| `legenda` | `xsd:string` | true | 0..1 |
| `CD_FCIM` | `xsd:string` | true | 0..1 |
| `NOM_UNIDAD` | `xsd:string` | true | 0..1 |
| `COD_SIMBOL` | `xsd:string` | true | 0..1 |
| `VAL_NCOMPO` | `xsd:double` | true | 0..1 |
| `LEGENDA_1` | `xsd:string` | true | 0..1 |
| `ORDEM` | `xsd:string` | true | 0..1 |
| `SUBORDEM` | `xsd:string` | true | 0..1 |
| `GRANDE_GRU` | `xsd:string` | true | 0..1 |
| `SUBGRUPOS` | `xsd:string` | true | 0..1 |
| `TEXTURA` | `xsd:string` | true | 0..1 |
| `HORIZONTE` | `xsd:string` | true | 0..1 |
| `EROSAO` | `xsd:string` | true | 0..1 |
| `PEDREGOSID` | `xsd:string` | true | 0..1 |
| `ROCHOSIDAD` | `xsd:string` | true | 0..1 |
| `RELEVO` | `xsd:string` | true | 0..1 |
| `COMPONENTE` | `xsd:string` | true | 0..1 |
| `COMPONENT1` | `xsd:string` | true | 0..1 |
| `COMPONENT2` | `xsd:string` | true | 0..1 |
| `COMPONENT3` | `xsd:string` | true | 0..1 |
| `INCLU_P1` | `xsd:string` | true | 0..1 |
| `INCLU_P2` | `xsd:string` | true | 0..1 |
| `INCLU_P3` | `xsd:string` | true | 0..1 |
| `MD_AR_POLI` | `xsd:double` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `hidrogeologico:Pocos_STD_PH`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Ordem` | `xsd:string` | true | 0..1 |
| `Fic_cpo` | `xsd:int` | true | 0..1 |
| `Munic` | `xsd:string` | true | 0..1 |
| `Fuso` | `xsd:string` | true | 0..1 |
| `Coord_X` | `xsd:int` | true | 0..1 |
| `Coord_y` | `xsd:int` | true | 0..1 |
| `Geologica` | `xsd:string` | true | 0..1 |
| `Aquifero` | `xsd:string` | true | 0..1 |
| `Situacao` | `xsd:string` | true | 0..1 |
| `CondElet` | `xsd:int` | true | 0..1 |
| `SolTotal` | `xsd:int` | true | 0..1 |
| `pH` | `xsd:double` | true | 0..1 |
| `SistAquif` | `xsd:string` | true | 0..1 |

### `hidrogeologico:PocosPotenciometria`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Numero` | `xsd:double` | true | 0..1 |
| `Poco` | `xsd:string` | true | 0..1 |
| `Fic_cpo` | `xsd:double` | true | 0..1 |
| `Munic` | `xsd:string` | true | 0..1 |
| `Fuso` | `xsd:double` | true | 0..1 |
| `Coord_X` | `xsd:double` | true | 0..1 |
| `Coord_Y` | `xsd:double` | true | 0..1 |
| `Aquifero` | `xsd:string` | true | 0..1 |
| `Situacao` | `xsd:string` | true | 0..1 |
| `Profundi` | `xsd:double` | true | 0..1 |
| `CotaBoca` | `xsd:double` | true | 0..1 |
| `NivEstat` | `xsd:double` | true | 0..1 |
| `CotaSup` | `xsd:double` | true | 0..1 |

### `hidrogeologico:PocosVulnerabilidade`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Ordem` | `xsd:string` | true | 0..1 |
| `Munic` | `xsd:string` | true | 0..1 |
| `Fuso` | `xsd:string` | true | 0..1 |
| `Coord_X` | `xsd:double` | true | 0..1 |
| `Coord_Y` | `xsd:double` | true | 0..1 |
| `Aquifero` | `xsd:string` | true | 0..1 |
| `Vulnerab` | `xsd:double` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |

### `hidrogeologico:Potenciometria`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Id` | `xsd:int` | true | 0..1 |
| `gridcode` | `xsd:int` | true | 0..1 |
| `Cota` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `hidrogeologico:STD_Fissural`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID_1` | `xsd:long` | true | 0..1 |
| `OBJECTID` | `xsd:double` | true | 0..1 |
| `Classes` | `xsd:int` | true | 0..1 |
| `Value_Min` | `xsd:double` | true | 0..1 |
| `Value_Max` | `xsd:double` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `hidrogeologico:STD_Poroso`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID_1` | `xsd:long` | true | 0..1 |
| `OBJECTID` | `xsd:double` | true | 0..1 |
| `Classes` | `xsd:int` | true | 0..1 |
| `Value_Min` | `xsd:double` | true | 0..1 |
| `Value_Max` | `xsd:double` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `hidrogeologico:Vunerabilidade`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `gridcode` | `xsd:int` | true | 0..1 |
| `Classe` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `hidrogeologico:ZonasHidrogeologico`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `NOME_UNIDA` | `xsd:string` | true | 0..1 |
| `SIGLA_UNID` | `xsd:string` | true | 0..1 |
| `Leg` | `xsd:string` | true | 0..1 |
| `Dominio` | `xsd:string` | true | 0..1 |
| `Zonas` | `xsd:string` | true | 0..1 |
| `Shape_Length` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

## preview (3)

### `preview:preview_line`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_proyect` | `xsd:double` | true | 0..1 |
| `nb_proyect` | `xsd:string` | true | 0..1 |
| `descrip` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `preview:preview_point`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_proyect` | `xsd:decimal` | true | 0..1 |
| `nb_proyect` | `xsd:string` | true | 0..1 |
| `descrip` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `preview:preview_polygon`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_proyect` | `xsd:string` | true | 0..1 |
| `nb_proyect` | `xsd:string` | true | 0..1 |
| `descrip` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

## zoneamento_ecologico_economico (14)

### `zoneamento_ecologico_economico:cenario_atual_`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geocodigo` | `xsd:double` | true | 0..1 |
| `area_mun` | `xsd:double` | true | 0..1 |
| `area_m_km` | `xsd:double` | true | 0..1 |
| `cla_fxl_at` | `xsd:double` | true | 0..1 |
| `sin_fluxos` | `xsd:double` | true | 0..1 |
| `cen_at` | `xsd:double` | true | 0..1 |
| `i_cen_at` | `xsd:string` | true | 0..1 |
| `cla_cen_at` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_le_1` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `zoneamento_ecologico_economico:cobertura_uso_2015_zoneamento`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `classe_200` | `xsd:string` | true | 0..1 |
| `uso_2007` | `xsd:string` | true | 0..1 |
| `classe_201` | `xsd:string` | true | 0..1 |
| `uso_2015` | `xsd:string` | true | 0..1 |
| `resul_acre` | `xsd:string` | true | 0..1 |
| `resul_desc` | `xsd:string` | true | 0..1 |
| `result_man` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_le_1` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `zoneamento_ecologico_economico:localidades_consulta_publica_zoneamento_`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `nm_tip_loc` | `xsd:string` | true | 0..1 |
| `oficinas` | `xsd:double` | true | 0..1 |

### `zoneamento_ecologico_economico:localidades_oficinas_zoneamento_`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `nm_tip_loc` | `xsd:string` | true | 0..1 |
| `oficinas` | `xsd:double` | true | 0..1 |

### `zoneamento_ecologico_economico:municipios_consulta_publica_zoneamento_`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `nm_tip_loc` | `xsd:string` | true | 0..1 |
| `convidados` | `xsd:double` | true | 0..1 |
| `mob_presen` | `xsd:string` | true | 0..1 |
| `presentes` | `xsd:double` | true | 0..1 |

### `zoneamento_ecologico_economico:municipios_oficinas_zoneamento_`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `nm_identif` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `nm_tip_loc` | `xsd:string` | true | 0..1 |
| `convidados` | `xsd:double` | true | 0..1 |
| `mob_presen` | `xsd:string` | true | 0..1 |
| `presentes` | `xsd:double` | true | 0..1 |

### `zoneamento_ecologico_economico:nivel_macro_zoneamento`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `macro` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `zoneamento_ecologico_economico:pontos_campo_biotico_zoneamento_`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `data` | `xsd:date` | true | 0..1 |
| `longitud` | `xsd:double` | true | 0..1 |
| `latitude` | `xsd:double` | true | 0..1 |
| `relevo` | `xsd:string` | true | 0..1 |
| `solos` | `xsd:string` | true | 0..1 |
| `paisagem_f` | `xsd:string` | true | 0..1 |
| `paisagem_t` | `xsd:string` | true | 0..1 |
| `paisagem_c` | `xsd:string` | true | 0..1 |
| `uso_pastag` | `xsd:string` | true | 0..1 |
| `uso_agricu` | `xsd:string` | true | 0..1 |
| `uso_reflor` | `xsd:string` | true | 0..1 |
| `uso_minera` | `xsd:string` | true | 0..1 |
| `tip_vegeta` | `xsd:string` | true | 0..1 |
| `conserv_fl` | `xsd:string` | true | 0..1 |
| `conserv_ce` | `xsd:string` | true | 0..1 |
| `observacao` | `xsd:string` | true | 0..1 |
| `foto1` | `xsd:string` | true | 0..1 |
| `foto2` | `xsd:string` | true | 0..1 |
| `foto3` | `xsd:string` | true | 0..1 |
| `foto4` | `xsd:string` | true | 0..1 |
| `foto5` | `xsd:string` | true | 0..1 |
| `foto6` | `xsd:string` | true | 0..1 |
| `ponto` | `xsd:string` | true | 0..1 |

### `zoneamento_ecologico_economico:pontos_coleta_zoneamento_4674`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `x` | `xsd:double` | true | 0..1 |
| `y` | `xsd:double` | true | 0..1 |
| `descricao` | `xsd:string` | true | 0..1 |
| `globalid` | `xsd:string` | true | 0..1 |
| `aflorament` | `xsd:string` | true | 0..1 |
| `depositos` | `xsd:string` | true | 0..1 |
| `lineamento` | `xsd:string` | true | 0..1 |
| `pedregoso` | `xsd:string` | true | 0..1 |
| `relevo` | `xsd:string` | true | 0..1 |
| `ambiente` | `xsd:string` | true | 0..1 |
| `tipo_de_va` | `xsd:string` | true | 0..1 |
| `cota` | `xsd:double` | true | 0..1 |
| `solo_expos` | `xsd:string` | true | 0..1 |
| `rocha_ou_c` | `xsd:string` | true | 0..1 |
| `apar_geral` | `xsd:string` | true | 0..1 |
| `alt_perf_m` | `xsd:string` | true | 0..1 |
| `esp_hor_a` | `xsd:string` | true | 0..1 |
| `cor_hori_a` | `xsd:string` | true | 0..1 |
| `cor_hori_b` | `xsd:string` | true | 0..1 |
| `text_hor_a` | `xsd:string` | true | 0..1 |
| `text_hor_b` | `xsd:string` | true | 0..1 |
| `area_alaga` | `xsd:string` | true | 0..1 |
| `larg_canal` | `xsd:string` | true | 0..1 |
| `apare_agua` | `xsd:string` | true | 0..1 |
| `canal_fluv` | `xsd:string` | true | 0..1 |
| `leito_fluv` | `xsd:string` | true | 0..1 |
| `tip_de_val` | `xsd:string` | true | 0..1 |
| `plan_d_inu` | `xsd:string` | true | 0..1 |
| `pocos` | `xsd:string` | true | 0..1 |
| `uso_do_sol` | `xsd:string` | true | 0..1 |
| `eros_marg` | `xsd:string` | true | 0..1 |
| `seco_umido` | `xsd:string` | true | 0..1 |
| `equipe` | `xsd:string` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |

### `zoneamento_ecologico_economico:rotas_campo_antropico_zoneamento_`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `equip_resp` | `xsd:string` | true | 0..1 |
| `dia` | `xsd:string` | true | 0..1 |
| `temp_trajt` | `xsd:string` | true | 0..1 |
| `dist_km_` | `xsd:double` | true | 0..1 |
| `origem` | `xsd:string` | true | 0..1 |
| `destino` | `xsd:string` | true | 0..1 |
| `rteir_simp` | `xsd:string` | true | 0..1 |
| `ordem` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |

### `zoneamento_ecologico_economico:servicos_ecossistemicos_4674`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `serv_ecos` | `xsd:string` | true | 0..1 |
| `shape_le_1` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `zoneamento_ecologico_economico:unidades_paisagem_zoneamento_`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `fid_nivel_` | `xsd:double` | true | 0..1 |
| `niveli` | `xsd:string` | true | 0..1 |
| `nivelii` | `xsd:string` | true | 0..1 |
| `niveliii` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `zoneamento_ecologico_economico:vulnerabilidade_zoneamento_`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `niveli` | `xsd:string` | true | 0..1 |
| `nivelii` | `xsd:string` | true | 0..1 |
| `niveliii` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `class_vul_` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_le_1` | `xsd:double` | true | 0..1 |
| `shape_le_2` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `zoneamento_ecologico_economico:zoneamento_to`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `OBJECTID` | `xsd:long` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nm_zona` | `xsd:string` | true | 0..1 |
| `zona_sigla` | `xsd:string` | true | 0..1 |
| `zona` | `xsd:string` | true | 0..1 |
| `area_gis_ha` | `xsd:double` | true | 0..1 |
| `SHAPE_Length` | `xsd:double` | true | 0..1 |
| `SHAPE_Area` | `xsd:double` | true | 0..1 |
