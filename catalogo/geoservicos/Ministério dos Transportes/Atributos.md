# Ministério dos Transportes — atributos das camadas

Geoportal: [[Geosserviços/Ministério dos Transportes/Ministério dos Transportes — MTR|Ministério dos Transportes — MTR]]

Os campos abaixo vêm de `DescribeFeatureType` (XSD), sem download de feições.

## MInfra (10)

### `MInfra:Aeródromos civis privados`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `codigo_aoc` | `xsd:string` | true | 0..1 |
| `ciad` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `longitude` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:string` | true | 0..1 |
| `altitude` | `xsd:string` | true | 0..1 |
| `oper_diurn` | `xsd:string` | true | 0..1 |
| `oper_notur` | `xsd:string` | true | 0..1 |
| `designacao` | `xsd:string` | true | 0..1 |
| `compriment` | `xsd:long` | true | 0..1 |
| `largura_pi` | `xsd:long` | true | 0..1 |
| `resistenci` | `xsd:string` | true | 0..1 |
| `superficie` | `xsd:string` | true | 0..1 |
| `designacao2` | `xsd:string` | true | 0..1 |
| `compriment2` | `xsd:long` | true | 0..1 |
| `largura_pi2` | `xsd:long` | true | 0..1 |
| `resistenci2` | `xsd:string` | true | 0..1 |
| `superficie2` | `xsd:string` | true | 0..1 |
| `validade_r` | `xsd:string` | true | 0..1 |
| `portaria_r` | `xsd:string` | true | 0..1 |
| `link_porta` | `xsd:string` | true | 0..1 |
| `lat_geo` | `xsd:string` | true | 0..1 |
| `long_geo` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MInfra:Aeródromos civis públicos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `codigo_oac` | `xsd:string` | true | 0..1 |
| `ciad` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:string` | true | 0..1 |
| `longitude` | `xsd:string` | true | 0..1 |
| `altitude` | `xsd:string` | true | 0..1 |
| `operacao` | `xsd:string` | true | 0..1 |
| `designacao` | `xsd:string` | true | 0..1 |
| `compriment` | `xsd:string` | true | 0..1 |
| `largura_pi` | `xsd:string` | true | 0..1 |
| `resisten_p` | `xsd:string` | true | 0..1 |
| `superficie` | `xsd:string` | true | 0..1 |
| `designacao2` | `xsd:string` | true | 0..1 |
| `compriment2` | `xsd:string` | true | 0..1 |
| `largura_pi2` | `xsd:string` | true | 0..1 |
| `resisten_p2` | `xsd:string` | true | 0..1 |
| `superficie2` | `xsd:string` | true | 0..1 |
| `designacao3` | `xsd:string` | true | 0..1 |
| `compriment3` | `xsd:string` | true | 0..1 |
| `largura_pi3` | `xsd:string` | true | 0..1 |
| `resisten_p3` | `xsd:string` | true | 0..1 |
| `superficie3` | `xsd:string` | true | 0..1 |
| `heli_ramp` | `xsd:string` | true | 0..1 |
| `heli_forma` | `xsd:string` | true | 0..1 |
| `heli_dimen` | `xsd:string` | true | 0..1 |
| `heli_resis` | `xsd:string` | true | 0..1 |
| `heli_super` | `xsd:string` | true | 0..1 |
| `p1` | `xsd:string` | true | 0..1 |
| `p2` | `xsd:string` | true | 0..1 |
| `p3` | `xsd:string` | true | 0..1 |
| `p4` | `xsd:string` | true | 0..1 |
| `portarias` | `xsd:string` | true | 0..1 |
| `atos_norma` | `xsd:string` | true | 0..1 |
| `atos_norma2` | `xsd:string` | true | 0..1 |
| `atos_norma3` | `xsd:string` | true | 0..1 |
| `portaria_a` | `xsd:string` | true | 0..1 |
| `portaria_n` | `xsd:string` | true | 0..1 |
| `portaria_n2` | `xsd:string` | true | 0..1 |
| `aeronave_c` | `xsd:string` | true | 0..1 |
| `tipo_de_ap` | `xsd:string` | true | 0..1 |
| `frequencia` | `xsd:string` | true | 0..1 |
| `r1` | `xsd:string` | true | 0..1 |
| `r2` | `xsd:string` | true | 0..1 |
| `referencia` | `xsd:string` | true | 0..1 |
| `restricao` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `r1_medidas` | `xsd:string` | true | 0..1 |
| `referencia2` | `xsd:string` | true | 0..1 |
| `sit_amazon` | `xsd:string` | true | 0..1 |
| `observacoe` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MInfra:estaleiros_minfra`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `objectid_1` | `xsd:long` | true | 0..1 |
| `idi_tuaria` | `xsd:long` | true | 0..1 |
| `cdi_tuaria` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `cdbigrama` | `xsd:string` | true | 0..1 |
| `cdtrigrama` | `xsd:string` | true | 0..1 |
| `cdterminal` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `gestao` | `xsd:string` | true | 0..1 |
| `modalidade` | `xsd:string` | true | 0..1 |
| `companhia` | `xsd:string` | true | 0..1 |
| `cnpj` | `xsd:string` | true | 0..1 |
| `legislacao` | `xsd:string` | true | 0..1 |
| `pro_didade` | `xsd:double` | true | 0..1 |
| `endereco` | `xsd:string` | true | 0..1 |
| `com_emento` | `xsd:string` | true | 0..1 |
| `numero` | `xsd:long` | true | 0..1 |
| `bairro` | `xsd:string` | true | 0..1 |
| `cep` | `xsd:string` | true | 0..1 |
| `idcidade` | `xsd:string` | true | 0..1 |
| `cidade` | `xsd:string` | true | 0..1 |
| `idestado` | `xsd:string` | true | 0..1 |
| `estado` | `xsd:string` | true | 0..1 |
| `idr_rafica` | `xsd:long` | true | 0..1 |
| `reg_rafica` | `xsd:string` | true | 0..1 |
| `loc_izacao` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:string` | true | 0..1 |
| `longitude` | `xsd:string` | true | 0..1 |
| `observacao` | `xsd:string` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MInfra:Ferrovias`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `tip_situac` | `xsd:string` | true | 0..1 |
| `bitola` | `xsd:string` | true | 0..1 |
| `sigla` | `xsd:string` | true | 0..1 |
| `sigla_coin` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `st_length_` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `MInfra:linhas_de_travesssia`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `idl_vessia` | `xsd:double` | true | 0..1 |
| `idantaq` | `xsd:double` | true | 0..1 |
| `nom_vessia` | `xsd:string` | true | 0..1 |
| `idm_origem` | `xsd:string` | true | 0..1 |
| `mun_origem` | `xsd:string` | true | 0..1 |
| `est_origem` | `xsd:string` | true | 0..1 |
| `idm_estino` | `xsd:string` | true | 0..1 |
| `mun_estino` | `xsd:string` | true | 0..1 |
| `est_estino` | `xsd:string` | true | 0..1 |
| `cod_origem` | `xsd:string` | true | 0..1 |
| `pai_origem` | `xsd:string` | true | 0..1 |
| `cod_estino` | `xsd:string` | true | 0..1 |
| `pai_estino` | `xsd:string` | true | 0..1 |
| `sit_cional` | `xsd:string` | true | 0..1 |
| `aut_izacao` | `xsd:string` | true | 0..1 |
| `percurso` | `xsd:string` | true | 0..1 |
| `edorigem` | `xsd:string` | true | 0..1 |
| `eddestino` | `xsd:string` | true | 0..1 |
| `idrio` | `xsd:double` | true | 0..1 |
| `nome_rio` | `xsd:string` | true | 0..1 |
| `orig_lat` | `xsd:string` | true | 0..1 |
| `orig_long` | `xsd:string` | true | 0..1 |
| `dest_lat` | `xsd:string` | true | 0..1 |
| `dest_long` | `xsd:string` | true | 0..1 |
| `idseq` | `xsd:double` | true | 0..1 |
| `id_gan` | `xsd:long` | true | 0..1 |
| `operadores` | `xsd:long` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `MInfra:poligonal_portos_publicos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `tetulodado` | `xsd:string` | true | 0..1 |
| `tipodedata` | `xsd:string` | true | 0..1 |
| `datadodado` | `xsd:string` | true | 0..1 |
| `resumodado` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `atualizcao` | `xsd:string` | true | 0..1 |
| `idioma` | `xsd:string` | true | 0..1 |
| `institucao` | `xsd:string` | true | 0..1 |
| `organizcao` | `xsd:string` | true | 0..1 |
| `funcao` | `xsd:string` | true | 0..1 |
| `nomearquiv` | `xsd:string` | true | 0..1 |
| `tags` | `xsd:string` | true | 0..1 |
| `tipodado` | `xsd:string` | true | 0..1 |
| `denomscala` | `xsd:string` | true | 0..1 |
| `datum` | `xsd:string` | true | 0..1 |
| `st_area_sh` | `xsd:double` | true | 0..1 |
| `st_length_` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `MInfra:Portos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idi_tuaria` | `xsd:long` | true | 0..1 |
| `idseq` | `xsd:long` | true | 0..1 |
| `cdi_tuaria` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `cdbigrama` | `xsd:string` | true | 0..1 |
| `cdtrigrama` | `xsd:string` | true | 0..1 |
| `cdterminal` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `gestao` | `xsd:string` | true | 0..1 |
| `modalidade` | `xsd:string` | true | 0..1 |
| `companhia` | `xsd:string` | true | 0..1 |
| `cnpj` | `xsd:string` | true | 0..1 |
| `legislacao` | `xsd:string` | true | 0..1 |
| `pro_didade` | `xsd:double` | true | 0..1 |
| `endereco` | `xsd:string` | true | 0..1 |
| `com_emento` | `xsd:string` | true | 0..1 |
| `numero` | `xsd:long` | true | 0..1 |
| `bairro` | `xsd:string` | true | 0..1 |
| `cep` | `xsd:string` | true | 0..1 |
| `idcidade` | `xsd:string` | true | 0..1 |
| `cidade` | `xsd:string` | true | 0..1 |
| `idestado` | `xsd:string` | true | 0..1 |
| `estado` | `xsd:string` | true | 0..1 |
| `idr_rafica` | `xsd:long` | true | 0..1 |
| `reg_rafica` | `xsd:string` | true | 0..1 |
| `loc_izacao` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:string` | true | 0..1 |
| `longitude` | `xsd:string` | true | 0..1 |
| `observacao` | `xsd:string` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `cdc_troide` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MInfra:Rodovias Federais`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id_trecho_` | `xsd:long` | true | 0..1 |
| `vl_br` | `xsd:string` | true | 0..1 |
| `sg_uf` | `xsd:string` | true | 0..1 |
| `nm_tipo_tr` | `xsd:string` | true | 0..1 |
| `sg_tipo_tr` | `xsd:string` | true | 0..1 |
| `desc_coinc` | `xsd:string` | true | 0..1 |
| `vl_codigo` | `xsd:string` | true | 0..1 |
| `ds_local_i` | `xsd:string` | true | 0..1 |
| `ds_local_f` | `xsd:string` | true | 0..1 |
| `vl_km_inic` | `xsd:double` | true | 0..1 |
| `vl_km_fina` | `xsd:double` | true | 0..1 |
| `vl_extensa` | `xsd:double` | true | 0..1 |
| `ds_sup_fed` | `xsd:string` | true | 0..1 |
| `ds_obra` | `xsd:string` | true | 0..1 |
| `ul` | `xsd:string` | true | 0..1 |
| `ds_coinc` | `xsd:string` | true | 0..1 |
| `ds_tipo_ad` | `xsd:string` | true | 0..1 |
| `ds_ato_leg` | `xsd:string` | true | 0..1 |
| `est_coinc` | `xsd:string` | true | 0..1 |
| `sup_est_co` | `xsd:string` | true | 0..1 |
| `ds_jurisdi` | `xsd:string` | true | 0..1 |
| `ds_superfi` | `xsd:string` | true | 0..1 |
| `ds_legenda` | `xsd:string` | true | 0..1 |
| `sg_legenda` | `xsd:string` | true | 0..1 |
| `leg_multim` | `xsd:string` | true | 0..1 |
| `versao_snv` | `xsd:string` | true | 0..1 |
| `id_versao` | `xsd:long` | true | 0..1 |
| `marcador` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `MInfra:transporte_aquaviario`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idhidrovia` | `xsd:long` | true | 0..1 |
| `idseq` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `navegacao` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `vel_cional` | `xsd:double` | true | 0..1 |
| `extensao` | `xsd:double` | true | 0..1 |
| `tempo` | `xsd:string` | true | 0..1 |
| `cla_icacao` | `xsd:string` | true | 0..1 |
| `nome_rio` | `xsd:string` | true | 0..1 |
| `nom_eclusa` | `xsd:string` | true | 0..1 |
| `jurisdicao` | `xsd:string` | true | 0..1 |
| `reg_rafica` | `xsd:string` | true | 0..1 |
| `pro_de_min` | `xsd:double` | true | 0..1 |
| `pro_de_max` | `xsd:double` | true | 0..1 |
| `dominio` | `xsd:string` | true | 0..1 |
| `observacao` | `xsd:string` | true | 0..1 |
| `snv` | `xsd:string` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `idm_origem` | `xsd:string` | true | 0..1 |
| `mun_origem` | `xsd:string` | true | 0..1 |
| `est_origem` | `xsd:string` | true | 0..1 |
| `idm_estino` | `xsd:string` | true | 0..1 |
| `mun_estino` | `xsd:string` | true | 0..1 |
| `est_estino` | `xsd:string` | true | 0..1 |
| `idantaq` | `xsd:long` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `MInfra:viaseconomicamentenavegadas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idhidrovia` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `navegacao` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `vel_cional` | `xsd:double` | true | 0..1 |
| `extensao` | `xsd:double` | true | 0..1 |
| `tempo` | `xsd:string` | true | 0..1 |
| `cla_icacao` | `xsd:string` | true | 0..1 |
| `nome_rio` | `xsd:string` | true | 0..1 |
| `nom_eclusa` | `xsd:string` | true | 0..1 |
| `jurisdicao` | `xsd:string` | true | 0..1 |
| `reg_rafica` | `xsd:string` | true | 0..1 |
| `pro_de_min` | `xsd:double` | true | 0..1 |
| `pro_de_max` | `xsd:double` | true | 0..1 |
| `dominio` | `xsd:string` | true | 0..1 |
| `observacao` | `xsd:string` | true | 0..1 |
| `snv` | `xsd:string` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `idm_origem` | `xsd:string` | true | 0..1 |
| `mun_origem` | `xsd:string` | true | 0..1 |
| `est_origem` | `xsd:string` | true | 0..1 |
| `idm_estino` | `xsd:string` | true | 0..1 |
| `mun_estino` | `xsd:string` | true | 0..1 |
| `est_estino` | `xsd:string` | true | 0..1 |
| `idantaq` | `xsd:long` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
