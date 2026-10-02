# ICMBio INDE — atributos das camadas

Geoportal: [[Geosserviços/ICMBio INDE/Instituto Chico Mendes de Conservação da Biodiversidade — ICMBio|Instituto Chico Mendes de Conservação da Biodiversidade — ICMBio]]

Os campos abaixo vêm do `DescribeFeatureType` (XSD), sem download de feições. `gml:*` geralmente identifica a geometria.

## ICMBio (85)

### `ICMBio:amazonia_2a_atualizacao`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `objectid_1` | `xsd:long` | true | 0..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `nome_area` | `xsd:string` | true | 0..1 |
| `cod_area` | `xsd:string` | true | 0..1 |
| `import_bio` | `xsd:string` | true | 0..1 |
| `prior_acao` | `xsd:string` | true | 0..1 |
| `acao_princ` | `xsd:long` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `acao_prin` | `xsd:string` | true | 0..1 |
| `acao_2` | `xsd:string` | true | 0..1 |
| `acao_3` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_le_1` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:areas_hibridas_2a_atualizacao`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `objectid_1` | `xsd:long` | true | 0..1 |
| `objectid_2` | `xsd:long` | true | 0..1 |
| `ib_pos` | `xsd:string` | true | 0..1 |
| `pa_pos` | `xsd:string` | true | 0..1 |
| `açãop_p` | `xsd:string` | true | 0..1 |
| `cod_area` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:autos_infracao_icmbio`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `vw_num_aut` | `xsd:double` | true | 0..1 |
| `numero_ai` | `xsd:string` | true | 0..1 |
| `serie` | `xsd:string` | true | 0..1 |
| `origem` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `valor_mult` | `xsd:double` | true | 0..1 |
| `embargo` | `xsd:string` | true | 0..1 |
| `apreensao` | `xsd:string` | true | 0..1 |
| `autuado` | `xsd:string` | true | 0..1 |
| `cpf_cnpj` | `xsd:string` | true | 0..1 |
| `data` | `xsd:date` | true | 0..1 |
| `ano` | `xsd:string` | true | 0..1 |
| `artigo_1` | `xsd:string` | true | 0..1 |
| `artigo_2` | `xsd:string` | true | 0..1 |
| `tipo_infra` | `xsd:string` | true | 0..1 |
| `nome_uc` | `xsd:string` | true | 0..1 |
| `cnuc` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `termos_emb` | `xsd:string` | true | 0..1 |
| `termos_apr` | `xsd:string` | true | 0..1 |
| `ordem_fisc` | `xsd:string` | true | 0..1 |
| `processo` | `xsd:string` | true | 0..1 |
| `julgamento` | `xsd:string` | true | 0..1 |
| `desc_ai_1` | `xsd:string` | true | 0..1 |
| `desc_san_1` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `ICMBio:caatinga_2a_atualizacao`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `objectid_1` | `xsd:long` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `nome_area` | `xsd:string` | true | 0..1 |
| `cod_area` | `xsd:string` | true | 0..1 |
| `import_bio` | `xsd:string` | true | 0..1 |
| `prior_acao` | `xsd:string` | true | 0..1 |
| `acao_princ` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:canie_052026_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `num_canie` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `estado` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `longitude` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:string` | true | 0..1 |
| `nvl_valida` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `ICMBio:cerrado_pantanal_2a_atualizacao`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `cod_area` | `xsd:long` | true | 0..1 |
| `import_bio` | `xsd:string` | true | 0..1 |
| `prior_acao` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `estados` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `acao2` | `xsd:string` | true | 0..1 |
| `acao1` | `xsd:string` | true | 0..1 |
| `acao3` | `xsd:string` | true | 0..1 |
| `acao4` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:compatibilidade_ivt_amazonia_062022_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `unidplane` | `xsd:string` | true | 0..1 |
| `senbioin` | `xsd:double` | true | 0..1 |
| `senbioct` | `xsd:string` | true | 0..1 |
| `impmdrod` | `xsd:double` | true | 0..1 |
| `eximprod` | `xsd:string` | true | 0..1 |
| `compatrod` | `xsd:string` | true | 0..1 |
| `impmdfer` | `xsd:double` | true | 0..1 |
| `eximpfer` | `xsd:string` | true | 0..1 |
| `compatfer` | `xsd:string` | true | 0..1 |
| `agrupcomp` | `xsd:int` | true | 0..1 |
| `grupocomp` | `xsd:string` | true | 0..1 |
| `unidcons` | `xsd:string` | true | 0..1 |
| `alvoscons` | `xsd:string` | true | 0..1 |
| `shapeleng` | `xsd:double` | true | 0..1 |
| `shapearea` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:compatibilidade_ivt_caatinga_062022_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `unidplane` | `xsd:string` | true | 0..1 |
| `senbioin` | `xsd:double` | true | 0..1 |
| `senbioct` | `xsd:string` | true | 0..1 |
| `impmdrod` | `xsd:double` | true | 0..1 |
| `eximprod` | `xsd:string` | true | 0..1 |
| `compatrod` | `xsd:string` | true | 0..1 |
| `impmdfer` | `xsd:double` | true | 0..1 |
| `eximpfer` | `xsd:string` | true | 0..1 |
| `compatfer` | `xsd:string` | true | 0..1 |
| `agrupcomp` | `xsd:int` | true | 0..1 |
| `grupocomp` | `xsd:string` | true | 0..1 |
| `unidcons` | `xsd:string` | true | 0..1 |
| `alvoscons` | `xsd:string` | true | 0..1 |
| `shapeleng` | `xsd:double` | true | 0..1 |
| `shapearea` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:compatibilidade_ivt_cerrado_062022_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `unidplane` | `xsd:string` | true | 0..1 |
| `senbioin` | `xsd:double` | true | 0..1 |
| `senbioct` | `xsd:string` | true | 0..1 |
| `impmdrod` | `xsd:double` | true | 0..1 |
| `eximprod` | `xsd:string` | true | 0..1 |
| `compatrod` | `xsd:string` | true | 0..1 |
| `impmdfer` | `xsd:double` | true | 0..1 |
| `eximpfer` | `xsd:string` | true | 0..1 |
| `compatfer` | `xsd:string` | true | 0..1 |
| `agrupcomp` | `xsd:int` | true | 0..1 |
| `grupocomp` | `xsd:string` | true | 0..1 |
| `unidcons` | `xsd:string` | true | 0..1 |
| `alvoscons` | `xsd:string` | true | 0..1 |
| `shapeleng` | `xsd:double` | true | 0..1 |
| `shapearea` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:compatibilidade_ivt_mata_atlantica_062022_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `unidplane` | `xsd:string` | true | 0..1 |
| `senbioin` | `xsd:double` | true | 0..1 |
| `senbioct` | `xsd:string` | true | 0..1 |
| `impmdrod` | `xsd:double` | true | 0..1 |
| `eximprod` | `xsd:string` | true | 0..1 |
| `compatrod` | `xsd:string` | true | 0..1 |
| `impmdfer` | `xsd:double` | true | 0..1 |
| `eximpfer` | `xsd:string` | true | 0..1 |
| `compatfer` | `xsd:string` | true | 0..1 |
| `agrupcomp` | `xsd:int` | true | 0..1 |
| `grupocomp` | `xsd:string` | true | 0..1 |
| `unidcons` | `xsd:string` | true | 0..1 |
| `alvoscons` | `xsd:string` | true | 0..1 |
| `shapeleng` | `xsd:double` | true | 0..1 |
| `shapearea` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:compatibilidade_ivt_pampa_062022_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `unidplane` | `xsd:string` | true | 0..1 |
| `senbioin` | `xsd:double` | true | 0..1 |
| `senbioct` | `xsd:string` | true | 0..1 |
| `impmdrod` | `xsd:double` | true | 0..1 |
| `eximprod` | `xsd:string` | true | 0..1 |
| `compatrod` | `xsd:string` | true | 0..1 |
| `impmdfer` | `xsd:double` | true | 0..1 |
| `eximpfer` | `xsd:string` | true | 0..1 |
| `compatfer` | `xsd:string` | true | 0..1 |
| `agrupcomp` | `xsd:int` | true | 0..1 |
| `unidcons` | `xsd:string` | true | 0..1 |
| `alvoscons` | `xsd:string` | true | 0..1 |
| `shapeleng` | `xsd:double` | true | 0..1 |
| `shapearea` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:compatibilidade_ivt_pantanal_062022_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `unidplane` | `xsd:string` | true | 0..1 |
| `senbioin` | `xsd:double` | true | 0..1 |
| `senbioct` | `xsd:string` | true | 0..1 |
| `impmdrod` | `xsd:double` | true | 0..1 |
| `eximprod` | `xsd:string` | true | 0..1 |
| `compatrod` | `xsd:string` | true | 0..1 |
| `impmdfer` | `xsd:double` | true | 0..1 |
| `eximpfer` | `xsd:string` | true | 0..1 |
| `compatfer` | `xsd:string` | true | 0..1 |
| `unidcons` | `xsd:string` | true | 0..1 |
| `alvoscons` | `xsd:string` | true | 0..1 |
| `shapeleng` | `xsd:double` | true | 0..1 |
| `shapearea` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:embargos_icmbio`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `vw_num_emb` | `xsd:double` | true | 0..1 |
| `numero_emb` | `xsd:string` | true | 0..1 |
| `serie` | `xsd:string` | true | 0..1 |
| `origem` | `xsd:string` | true | 0..1 |
| `numero_ai` | `xsd:string` | true | 0..1 |
| `cpf_cnpj` | `xsd:string` | true | 0..1 |
| `autuado` | `xsd:string` | true | 0..1 |
| `artigo_1` | `xsd:string` | true | 0..1 |
| `artigo_2` | `xsd:string` | true | 0..1 |
| `tipo_infra` | `xsd:string` | true | 0..1 |
| `nome_uc` | `xsd:string` | true | 0..1 |
| `cnuc` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `data` | `xsd:date` | true | 0..1 |
| `ano` | `xsd:string` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `julgamento` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `processo` | `xsd:string` | true | 0..1 |
| `desc_inf_1` | `xsd:string` | true | 0..1 |
| `desc_san_1` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:limiteucsfederais_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `nomeuc` | `xsd:string` | true | 0..1 |
| `cnuc` | `xsd:string` | true | 0..1 |
| `criacaoano` | `xsd:string` | true | 0..1 |
| `areahaalb` | `xsd:double` | true | 0..1 |
| `perimm` | `xsd:double` | true | 0..1 |
| `criacaoato` | `xsd:string` | true | 0..1 |
| `esferaadm` | `xsd:string` | true | 0..1 |
| `grupouc` | `xsd:string` | true | 0..1 |
| `biomas` | `xsd:string` | true | 0..1 |
| `gregional` | `xsd:string` | true | 0..1 |
| `fusoabrang` | `xsd:string` | true | 0..1 |
| `demarcacao` | `xsd:string` | true | 0..1 |
| `escalauc` | `xsd:string` | true | 0..1 |
| `bioma_pred` | `xsd:string` | true | 0..1 |
| `cat_iucn` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `categoria_` | `xsd:string` | true | 0..1 |
| `sigla_cate` | `xsd:string` | true | 0..1 |
| `dominio` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:mataatlantica_2a_atualiz`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `acaopriori` | `xsd:double` | true | 0..1 |
| `importbio_` | `xsd:string` | true | 0..1 |
| `prioridade` | `xsd:string` | true | 0..1 |
| `cod_area` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `nomeacao` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pampa_2a_atualizacao`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `cod_area` | `xsd:string` | true | 0..1 |
| `import_bio` | `xsd:string` | true | 0..1 |
| `prior_acao` | `xsd:string` | true | 0..1 |
| `acaoprinci` | `xsd:double` | true | 0..1 |
| `nome_ap` | `xsd:string` | true | 0..1 |
| `nome_acao` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cbc_polinizadores_c1_abrang_032023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cbc_polinizadores_c1_areas_estrat_102023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `cdarea` | `xsd:string` | true | 0..1 |
| `nmarea` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `grupotax` | `xsd:string` | true | 0..1 |
| `alvocons` | `xsd:string` | true | 0..1 |
| `pasei` | `xsd:string` | true | 0..1 |
| `areafin` | `xsd:string` | true | 0..1 |
| `areacria` | `xsd:string` | true | 0..1 |
| `areang` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cecav_area_abrangencia_012023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `path` | `xsd:string` | true | 0..1 |
| `pdapan cic` | `xsd:string` | true | 0..1 |
| `pdastatus` | `xsd:string` | true | 0..1 |
| `pdadata da` | `xsd:string` | true | 0..1 |
| `pdadata do` | `xsd:string` | true | 0..1 |
| `pdaportari` | `xsd:string` | true | 0..1 |
| `pdanome co` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cemave_ararinhaaz_c2_area_abrang_022023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cemave_avamazonia_c1_area_abrang_022023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cemave_avmarinhas_c1_area_abrang_022023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cemave_caatinga_c2_area_abrang_022023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cemave_caatinga_c2_area_estrat_022023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `cdarea` | `xsd:string` | true | 0..1 |
| `nmarea` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `grupotax` | `xsd:string` | true | 0..1 |
| `alvocons` | `xsd:string` | true | 0..1 |
| `pasei` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvignt` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cemave_caatinga_c3_areas_estrat_112023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `cdarea` | `xsd:string` | true | 0..1 |
| `nmarea` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `grupotax` | `xsd:string` | true | 0..1 |
| `alvocons` | `xsd:string` | true | 0..1 |
| `pasei` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cemave_cerrapanta_c1_area_abrang_022023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cemave_cerrapanta_c1_area_estrat_022023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `cdarea` | `xsd:string` | true | 0..1 |
| `nmarea` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `grupotax` | `xsd:string` | true | 0..1 |
| `alvocons` | `xsd:string` | true | 0..1 |
| `pasei` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cemave_csulinos_c2_area_abrang_022023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cemave_limicolas_c2_area_abrang_022023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cemave_limicolas_c2_area_estrat_022023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `cdarea` | `xsd:string` | true | 0..1 |
| `nmarea` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `grupotax` | `xsd:string` | true | 0..1 |
| `alvocons` | `xsd:string` | true | 0..1 |
| `pasei` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cemave_matlantica_c1_area_abrang_022023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cemave_matlantica_c1_area_estrat_022023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `cdarea` | `xsd:string` | true | 0..1 |
| `nmarea` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `grupotax` | `xsd:string` | true | 0..1 |
| `alvocons` | `xsd:string` | true | 0..1 |
| `pasei` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cemave_matlantica_c2_areas_estrat_012024_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `cdarea` | `xsd:string` | true | 0..1 |
| `nmarea` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `grupotax` | `xsd:string` | true | 0..1 |
| `alvocons` | `xsd:string` | true | 0..1 |
| `pasei` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cemave_patomergulhao_c3_abrang_012024_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cemave_planacap_c3_area_abrang_022023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cenap_ariranha_c2_abrang_012023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cenap_ariranha_c3_abrang_012024_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cenap_canideos_c1_abrang_012023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cenap_gfelinos_c1_abrang_012023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cenap_pfelinos_c2_abrang_012023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cenap_pmamifaa_c1_abrang_012024_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cenap_pmamifaa_c1_areas_estrat_012024_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `cdarea` | `xsd:string` | true | 0..1 |
| `nmarea` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `grupotax` | `xsd:string` | true | 0..1 |
| `alvocons` | `xsd:string` | true | 0..1 |
| `pasei` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cenap_pmamifaf_c1_abrang_012024_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cenap_pmamifaf_c1_areas_estrat_012024_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `cdarea` | `xsd:string` | true | 0..1 |
| `nmarea` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `grupotax` | `xsd:string` | true | 0..1 |
| `alvocons` | `xsd:string` | true | 0..1 |
| `pasei` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cenap_ung_c1_abrang_012023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cepam_pxsamazncs_c1_abrang_012023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cepsul_corais_c1_area_abrangencia_042024_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cepsul_lagoasdosul_c1_abrang_012023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cepta_altoparana_c1_abrang_032024_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cepta_baixoiguacu_c1_abrang_012023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cepta_mogi_c1_abrang_012023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cepta_paraibadosul_c2_area_estrat_022024_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `cdarea` | `xsd:string` | true | 0..1 |
| `nmarea` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `grupotax` | `xsd:string` | true | 0..1 |
| `alvocons` | `xsd:string` | true | 0..1 |
| `pasei` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cepta_paraibasul_c1_abrang_012023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cepta_paraibasul_c1_area_estrategica_082022_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `cdarea` | `xsd:string` | true | 0..1 |
| `nmarea` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `grupotax` | `xsd:string` | true | 0..1 |
| `alvocons` | `xsd:string` | true | 0..1 |
| `pasei` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cepta_paraibasul_c2_abrang_022024_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cepta_pema_c1_abrang_012023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cepta_pema_c1_area_estrategica_082022_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `cdarea` | `xsd:string` | true | 0..1 |
| `nmarea` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `grupotax` | `xsd:string` | true | 0..1 |
| `alvocons` | `xsd:string` | true | 0..1 |
| `pasei` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cepta_rivulideos_c2_abrang_012023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cepta_sfrancisco_c1_abrang_092022_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cepta_sfrancisco_c2_abrang_012023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cma_cetaceosmarinhos_c1_abrang_032023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cma_mamiferosaquaticosamazonicos_c1_abrang_032023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cma_peixeboimarinho_c1_abrang_032023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cma_toninhas_c2_abrang_032023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cpb_primamaz_c1_abrang_012023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cpb_primamazonicos_c1_areas_estrat_022023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `cdarea` | `xsd:string` | true | 0..1 |
| `nmarea` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `grupotax` | `xsd:string` | true | 0..1 |
| `alvocons` | `xsd:string` | true | 0..1 |
| `pasei` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cpb_primmtatl_c1_abrang_012023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cpb_primne_c2_abrang_012023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cpb_prine_c2_areas_estrat_022023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `cdarea` | `xsd:string` | true | 0..1 |
| `nmarea` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `grupotax` | `xsd:string` | true | 0..1 |
| `alvocons` | `xsd:string` | true | 0..1 |
| `pasei` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cpb_sauim_c2_abrang_012023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_cpb_tata_c1_abrang_012023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_icmbio_abrang_052024_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_icmbio_areas_estrat_052024_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `cdarea` | `xsd:string` | true | 0..1 |
| `nmarea` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `grupotax` | `xsd:string` | true | 0..1 |
| `alvocons` | `xsd:string` | true | 0..1 |
| `pasei` | `xsd:string` | true | 0..1 |
| `areafin` | `xsd:string` | true | 0..1 |
| `areacria` | `xsd:string` | true | 0..1 |
| `areang` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_ran_cerradoepantanal_c1_area_abrang_022023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_ran_cerradoepantanal_c1_area_estrat_022023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `cdarea` | `xsd:string` | true | 0..1 |
| `nmarea` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `grupotax` | `xsd:string` | true | 0..1 |
| `alvocons` | `xsd:string` | true | 0..1 |
| `pasei` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_ran_espinhaco_c2_area_abrang_022023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_ran_espinhaco_c2_area_estrat_022023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `cdarea` | `xsd:string` | true | 0..1 |
| `nmarea` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `grupotax` | `xsd:string` | true | 0..1 |
| `alvocons` | `xsd:string` | true | 0..1 |
| `pasei` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_ran_nordeste_c2_area_abrang_022023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_ran_nordeste_c2_area_estrat_022023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `cdarea` | `xsd:string` | true | 0..1 |
| `nmarea` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `grupotax` | `xsd:string` | true | 0..1 |
| `alvocons` | `xsd:string` | true | 0..1 |
| `pasei` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_ran_sudeste_c2_area_abrang_022023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_ran_sul_c2_area_abrang_022023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_ran_sul_c2_area_estrat_022023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `cdarea` | `xsd:string` | true | 0..1 |
| `nmarea` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `grupotax` | `xsd:string` | true | 0..1 |
| `alvocons` | `xsd:string` | true | 0..1 |
| `pasei` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_tamar_pantamar_c2_area_estrat_022023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `cdarea` | `xsd:string` | true | 0..1 |
| `nmarea` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `grupotax` | `xsd:string` | true | 0..1 |
| `alvocons` | `xsd:string` | true | 0..1 |
| `pasei` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:pan_tamar_tamar_c2_abrang_012023_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idpan` | `xsd:string` | true | 0..1 |
| `pan` | `xsd:string` | true | 0..1 |
| `centro` | `xsd:string` | true | 0..1 |
| `areaha` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fontevetor` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `nomepan` | `xsd:string` | true | 0..1 |
| `ciclo` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `datafim` | `xsd:string` | true | 0..1 |
| `portvigent` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `ICMBio:zcm_2a_atualiz`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `nome_ap` | `xsd:string` | true | 0..1 |
| `imp` | `xsd:string` | true | 0..1 |
| `prio` | `xsd:string` | true | 0..1 |
| `acprinc` | `xsd:double` | true | 0..1 |
| `ac2` | `xsd:double` | true | 0..1 |
| `ac3` | `xsd:double` | true | 0..1 |
| `acprincnom` | `xsd:string` | true | 0..1 |
| `n` | `xsd:double` | true | 0..1 |
| `id_ap` | `xsd:string` | true | 0..1 |
| `acprincdet` | `xsd:string` | true | 0..1 |
| `ac2det` | `xsd:string` | true | 0..1 |
| `ac3det` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `acaoprinc` | `xsd:string` | true | 0..1 |
| `acao2` | `xsd:string` | true | 0..1 |
| `acao3` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
