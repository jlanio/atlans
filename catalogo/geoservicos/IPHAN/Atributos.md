# IPHAN — atributos das camadas

Geoportal: [[Geosserviços/IPHAN/Instituto do Patrimônio Histórico e Artístico Nacional — IPHAN|Instituto do Patrimônio Histórico e Artístico Nacional — IPHAN]]

Os campos abaixo vêm de `DescribeFeatureType` (XSD), sem download de feições.

## CNA (2)

### `CNA:_tmp`

> [!warning] Schema pendente
> Este esquema ainda não foi resolvido nesta coleta. Reconsulte o endpoint antes de usar a camada.


### `CNA:cnigp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `responsavel` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |

## DBGEO (4)

### `DBGEO:cim`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `sprarea` | `xsd:decimal` | true | 0..1 |
| `sprperimet` | `xsd:decimal` | true | 0..1 |
| `sprrotulo` | `xsd:string` | true | 0..1 |
| `sprnome` | `xsd:string` | true | 0..1 |
| `ind_nomenc` | `xsd:string` | true | 0..1 |
| `mi` | `xsd:string` | true | 0..1 |
| `nome_carta` | `xsd:string` | true | 0..1 |
| `tipo_carta` | `xsd:string` | true | 0..1 |
| `orgao_edit` | `xsd:string` | true | 0..1 |
| `situacao_e` | `xsd:string` | true | 0..1 |
| `ano_ultima` | `xsd:string` | true | 0..1 |
| `num_ultima` | `xsd:string` | true | 0..1 |
| `ano_impres` | `xsd:string` | true | 0..1 |
| `num_impres` | `xsd:string` | true | 0..1 |
| `metodo_pro` | `xsd:string` | true | 0..1 |
| `sistema_pr` | `xsd:string` | true | 0..1 |
| `meridiano_` | `xsd:string` | true | 0..1 |
| `latitude_o` | `xsd:string` | true | 0..1 |
| `longitude_` | `xsd:string` | true | 0..1 |
| `datum_hori` | `xsd:string` | true | 0..1 |
| `datum_vert` | `xsd:string` | true | 0..1 |
| `paralelo_p` | `xsd:string` | true | 0..1 |
| `paralelo_1` | `xsd:string` | true | 0..1 |
| `declinacao` | `xsd:string` | true | 0..1 |
| `area_carta` | `xsd:decimal` | true | 0..1 |
| `forma_disp` | `xsd:string` | true | 0..1 |

### `DBGEO:Empreendimentos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `projeto` | `xsd:string` | true | 0..1 |
| `processo` | `xsd:string` | true | 0..1 |
| `ano` | `xsd:short` | true | 0..1 |
| `id` | `xsd:int` | false | 1..1 |
| `nivel` | `xsd:short` | true | 0..1 |
| `unidade` | `xsd:string` | true | 0..1 |
| `empreendedor` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `tipo` | `xsd:int` | true | 0..1 |
| `tipo_text` | `xsd:string` | true | 0..1 |
| `tipo_in` | `xsd:int` | true | 0..1 |

### `DBGEO:Rios`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `noriocomp` | `xsd:string` | true | 0..1 |

### `DBGEO:uf`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `sprarea` | `xsd:decimal` | true | 0..1 |
| `sprperimet` | `xsd:decimal` | true | 0..1 |
| `sprrotulo` | `xsd:string` | true | 0..1 |
| `sprnome` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `cod_uf` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |

## DEPAM (3)

### `DEPAM:bem_zrp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `id_bem` | `xsd:int` | true | 0..1 |
| `identifica` | `xsd:string` | true | 0..1 |
| `co_iphan` | `xsd:string` | true | 0..1 |
| `no_logrado` | `xsd:string` | true | 0..1 |
| `nu_logrado` | `xsd:string` | true | 0..1 |
| `id_naturez` | `xsd:int` | true | 0..1 |
| `ds_naturez` | `xsd:string` | true | 0..1 |
| `codigo_iph` | `xsd:string` | true | 0..1 |
| `id_classif` | `xsd:int` | true | 0..1 |
| `ds_classif` | `xsd:string` | true | 0..1 |
| `id_tipo_be` | `xsd:int` | true | 0..1 |
| `ds_tipo_be` | `xsd:string` | true | 0..1 |
| `sg_tipo_be` | `xsd:string` | true | 0..1 |
| `sintese_be` | `xsd:string` | true | 0..1 |
| `dt_cadastr` | `xsd:date` | true | 0..1 |
| `id_proteca` | `xsd:int` | true | 0..1 |
| `id_tipo_pr` | `xsd:int` | true | 0..1 |
| `ds_tipo_pr` | `xsd:string` | true | 0..1 |
| `id_condica` | `xsd:int` | true | 0..1 |
| `ds_condica` | `xsd:string` | true | 0..1 |
| `id_zrp` | `xsd:int` | true | 0..1 |

### `DEPAM:zrp_especial`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `id_zrp` | `xsd:int` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |

### `DEPAM:zrp_padronizada`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `id_bem` | `xsd:int` | true | 0..1 |
| `identifica` | `xsd:string` | true | 0..1 |
| `co_iphan` | `xsd:string` | true | 0..1 |
| `no_logrado` | `xsd:string` | true | 0..1 |
| `nu_logrado` | `xsd:string` | true | 0..1 |
| `id_naturez` | `xsd:int` | true | 0..1 |
| `ds_naturez` | `xsd:string` | true | 0..1 |
| `codigo_iph` | `xsd:string` | true | 0..1 |
| `id_classif` | `xsd:int` | true | 0..1 |
| `ds_classif` | `xsd:string` | true | 0..1 |
| `id_tipo_be` | `xsd:int` | true | 0..1 |
| `ds_tipo_be` | `xsd:string` | true | 0..1 |
| `sg_tipo_be` | `xsd:string` | true | 0..1 |
| `sintese_be` | `xsd:string` | true | 0..1 |
| `dt_cadastr` | `xsd:date` | true | 0..1 |
| `id_proteca` | `xsd:int` | true | 0..1 |
| `id_tipo_pr` | `xsd:int` | true | 0..1 |
| `ds_tipo_pr` | `xsd:string` | true | 0..1 |
| `id_condica` | `xsd:int` | true | 0..1 |
| `ds_condica` | `xsd:string` | true | 0..1 |
| `zrp_raio_m` | `xsd:decimal` | true | 0..1 |

## fca (5)

### `fca:ada_saip_teste`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `esfera_licenciamento_ambiental` | `xsd:string` | true | 0..1 |
| `item` | `xsd:int` | true | 0..1 |
| `tipo_empreendimento` | `xsd:string` | true | 0..1 |
| `nivel_patrimonio_arqueologico` | `xsd:short` | true | 0..1 |
| `area_ada_ha` | `xsd:double` | true | 0..1 |
| `bens_tombados_valorados` | `xsd:string` | true | 0..1 |
| `bens_registrados` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `data_protocolo` | `xsd:date` | true | 0..1 |
| `data_tre` | `xsd:date` | true | 0..1 |
| `processo` | `xsd:string` | true | 0..1 |
| `ano` | `xsd:short` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `situacao_empreendimento` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `id_saip` | `xsd:string` | true | 0..1 |
| `nome_empreendimento` | `xsd:string` | true | 0..1 |
| `rol_art_4` | `xsd:string` | true | 0..1 |

### `fca:aid_saip`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `nome_empreendimento` | `xsd:string` | true | 0..1 |
| `esfera_licenciamento_ambiental` | `xsd:string` | true | 0..1 |
| `item` | `xsd:int` | true | 0..1 |
| `tipo_empreendimento` | `xsd:string` | true | 0..1 |
| `nivel_patrimonio_arqueologico` | `xsd:short` | true | 0..1 |
| `area_aid_ha` | `xsd:double` | true | 0..1 |
| `bens_tombados_valorados` | `xsd:string` | true | 0..1 |
| `bens_registrados` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `processo` | `xsd:string` | true | 0..1 |
| `ano` | `xsd:short` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `situacao_empreendimento` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `id_saip` | `xsd:string` | true | 0..1 |
| `rol_art_4` | `xsd:string` | true | 0..1 |

### `fca:fca`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `projeto` | `xsd:string` | true | 0..1 |
| `processo` | `xsd:string` | true | 0..1 |
| `ano` | `xsd:short` | true | 0..1 |
| `id` | `xsd:int` | false | 1..1 |
| `data_entrada` | `xsd:date` | true | 0..1 |
| `data_analise` | `xsd:date` | true | 0..1 |
| `nivel` | `xsd:short` | true | 0..1 |
| `unidade` | `xsd:string` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `empreendedor` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `tipo` | `xsd:int` | true | 0..1 |
| `tipo_in` | `xsd:int` | true | 0..1 |
| `es_material` | `xsd:boolean` | true | 0..1 |
| `es_imaterial` | `xsd:boolean` | true | 0..1 |

### `fca:fca_se`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `projeto` | `xsd:string` | true | 0..1 |
| `processo` | `xsd:string` | true | 0..1 |
| `ano` | `xsd:short` | true | 0..1 |
| `homologado` | `xsd:string` | true | 0..1 |
| `id` | `xsd:int` | false | 1..1 |
| `data_entrada` | `xsd:date` | true | 0..1 |
| `data_analise` | `xsd:date` | true | 0..1 |
| `nivel` | `xsd:short` | true | 0..1 |
| `unidade` | `xsd:string` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `empreendedor` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `tipo` | `xsd:int` | true | 0..1 |
| `tipo_in` | `xsd:int` | true | 0..1 |
| `es_material` | `xsd:boolean` | true | 0..1 |
| `es_imaterial` | `xsd:boolean` | true | 0..1 |

### `fca:fca_tipos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_tipo` | `xsd:int` | false | 1..1 |
| `tipo` | `xsd:string` | true | 0..1 |

## Nimuendaju (9)

### `Nimuendaju:tb_familia_linguistica`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_familia_linguistica` | `xsd:int` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `descricao` | `xsd:string` | true | 0..1 |

### `Nimuendaju:tb_quadrante`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_quadrante` | `xsd:int` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |

### `Nimuendaju:tb_referencia_bibliografica_nimuendaju`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_referencia` | `xsd:int` | false | 1..1 |
| `autoria` | `xsd:string` | true | 0..1 |
| `titulo` | `xsd:string` | true | 0..1 |
| `outros_titulos` | `xsd:string` | true | 0..1 |
| `ano` | `xsd:int` | true | 0..1 |
| `referencia_completa` | `xsd:string` | true | 0..1 |
| `link` | `xsd:string` | true | 0..1 |
| `observacao` | `xsd:string` | true | 0..1 |

### `Nimuendaju:tb_tipo_sede`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_tipo_sede` | `xsd:int` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `descricao` | `xsd:string` | true | 0..1 |

### `Nimuendaju:tb_tipo_tribo`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_tipo_tribo` | `xsd:int` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `descricao` | `xsd:string` | true | 0..1 |

### `Nimuendaju:tb_tribo_quadrante`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_tribo_quadrante` | `xsd:int` | false | 1..1 |
| `id_tribo` | `xsd:int` | false | 1..1 |
| `id_quadrante` | `xsd:int` | false | 1..1 |

### `Nimuendaju:tb_tribo_referencia`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_tribo_referencia` | `xsd:int` | false | 1..1 |
| `id_tribo` | `xsd:int` | false | 1..1 |
| `id_referencia` | `xsd:int` | false | 1..1 |

### `Nimuendaju:tg_tribo`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_tribo` | `xsd:int` | false | 1..1 |
| `ponto` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `outros_nomes` | `xsd:string` | true | 0..1 |
| `descricao_local` | `xsd:string` | true | 0..1 |
| `datacao_inicial` | `xsd:int` | true | 0..1 |
| `id_tipo_tribo` | `xsd:int` | false | 1..1 |
| `id_tipo_sede` | `xsd:int` | false | 1..1 |
| `id_familia_linguistica` | `xsd:int` | false | 1..1 |
| `datacao_final` | `xsd:int` | true | 0..1 |

### `Nimuendaju:tg_tribo_view`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ponto` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `id_tribo` | `xsd:int` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `outros_nomes` | `xsd:string` | true | 0..1 |
| `descricao_local` | `xsd:string` | true | 0..1 |
| `datacao_inicial` | `xsd:int` | true | 0..1 |
| `datacao_final` | `xsd:int` | true | 0..1 |
| `id_tipo_tribo` | `xsd:int` | false | 1..1 |
| `tipo_tribo` | `xsd:string` | true | 0..1 |
| `id_tipo_sede` | `xsd:int` | false | 1..1 |
| `tipo_sede` | `xsd:string` | true | 0..1 |
| `id_familia_linguistica` | `xsd:int` | false | 1..1 |
| `familia` | `xsd:string` | true | 0..1 |

## SICG (11)

### `SICG:bem_poligono`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `poligono` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `id_bem` | `xsd:int` | false | 1..1 |
| `identificacao_bem` | `xsd:string` | false | 1..1 |
| `co_iphan` | `xsd:string` | false | 1..1 |
| `no_logradouro` | `xsd:string` | true | 0..1 |
| `nu_logradouro` | `xsd:string` | true | 0..1 |
| `id_natureza` | `xsd:int` | false | 1..1 |
| `ds_natureza` | `xsd:string` | false | 1..1 |
| `codigo_iphan` | `xsd:string` | false | 1..1 |
| `id_classificacao` | `xsd:int` | false | 1..1 |
| `ds_classificacao` | `xsd:string` | false | 1..1 |
| `id_tipo_bem` | `xsd:int` | false | 1..1 |
| `ds_tipo_bem` | `xsd:string` | false | 1..1 |
| `sg_tipo_bem` | `xsd:string` | false | 1..1 |
| `sintese_bem` | `xsd:string` | true | 0..1 |
| `dt_cadastro` | `xsd:date` | true | 0..1 |

### `SICG:Bem_Protecao`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ponto` | `gml:PointPropertyType` | true | 0..1 |
| `id_bem` | `xsd:int` | false | 1..1 |
| `identificacao_bem` | `xsd:string` | false | 1..1 |
| `co_iphan` | `xsd:string` | false | 1..1 |
| `no_logradouro` | `xsd:string` | true | 0..1 |
| `nu_logradouro` | `xsd:string` | true | 0..1 |
| `id_natureza` | `xsd:int` | false | 1..1 |
| `ds_natureza` | `xsd:string` | false | 1..1 |
| `codigo_iphan` | `xsd:string` | false | 1..1 |
| `id_classificacao` | `xsd:int` | false | 1..1 |
| `ds_classificacao` | `xsd:string` | false | 1..1 |
| `id_tipo_bem` | `xsd:int` | false | 1..1 |
| `ds_tipo_bem` | `xsd:string` | false | 1..1 |
| `sg_tipo_bem` | `xsd:string` | false | 1..1 |
| `id_protecao_bem` | `xsd:int` | false | 1..1 |
| `id_tipo_protecao` | `xsd:int` | false | 1..1 |
| `ds_tipo_protecao` | `xsd:string` | false | 1..1 |
| `id_condicao_protecao` | `xsd:int` | false | 1..1 |
| `ds_condicao_protecao` | `xsd:string` | false | 1..1 |
| `sintese_bem` | `xsd:string` | true | 0..1 |
| `dt_cadastro` | `xsd:date` | true | 0..1 |

### `SICG:ctx_imediato`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_contexto_imediato` | `xsd:int` | false | 1..1 |
| `id_contexto_geral` | `xsd:int` | false | 1..1 |
| `objeto_analise` | `xsd:string` | false | 1..1 |
| `sintese_historica` | `xsd:string` | true | 0..1 |
| `aspecto_geografico` | `xsd:string` | true | 0..1 |
| `aspecto_economico` | `xsd:string` | true | 0..1 |
| `aspecto_social` | `xsd:string` | true | 0..1 |
| `morfologia_paisagem` | `xsd:string` | true | 0..1 |
| `caract_imp_bem_macro` | `xsd:string` | true | 0..1 |
| `caract_imp_bem_meso` | `xsd:string` | true | 0..1 |
| `caract_imp_bem_micro` | `xsd:string` | true | 0..1 |
| `analise_espec_bem_conj` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:SurfacePropertyType` | true | 0..1 |

### `SICG:municipio`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_uf` | `xsd:int` | true | 0..1 |
| `cod_md` | `xsd:string` | true | 0..1 |
| `geometriaaproximada` | `xsd:boolean` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geocodigo` | `xsd:string` | false | 1..1 |
| `data_alteracao` | `xsd:string` | true | 0..1 |
| `metodo_alteracao` | `xsd:string` | true | 0..1 |
| `fonte_info_alter` | `xsd:string` | true | 0..1 |
| `anodereferencia` | `xsd:int` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `SICG:sitios`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ponto` | `gml:PointPropertyType` | true | 0..1 |
| `id_bem` | `xsd:int` | false | 1..1 |
| `identificacao_bem` | `xsd:string` | false | 1..1 |
| `co_iphan` | `xsd:string` | false | 1..1 |
| `no_logradouro` | `xsd:string` | true | 0..1 |
| `nu_logradouro` | `xsd:string` | true | 0..1 |
| `id_natureza` | `xsd:int` | false | 1..1 |
| `ds_natureza` | `xsd:string` | false | 1..1 |
| `codigo_iphan` | `xsd:string` | false | 1..1 |
| `id_classificacao` | `xsd:int` | false | 1..1 |
| `ds_classificacao` | `xsd:string` | false | 1..1 |
| `id_tipo_bem` | `xsd:int` | false | 1..1 |
| `ds_tipo_bem` | `xsd:string` | false | 1..1 |
| `sg_tipo_bem` | `xsd:string` | false | 1..1 |
| `sintese_bem` | `xsd:string` | true | 0..1 |
| `dt_cadastro` | `xsd:date` | true | 0..1 |

### `SICG:sitios_pol`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `poligono` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `id_bem` | `xsd:int` | false | 1..1 |
| `identificacao_bem` | `xsd:string` | false | 1..1 |
| `co_iphan` | `xsd:string` | false | 1..1 |
| `no_logradouro` | `xsd:string` | true | 0..1 |
| `nu_logradouro` | `xsd:string` | true | 0..1 |
| `id_natureza` | `xsd:int` | false | 1..1 |
| `ds_natureza` | `xsd:string` | false | 1..1 |
| `codigo_iphan` | `xsd:string` | false | 1..1 |
| `id_classificacao` | `xsd:int` | false | 1..1 |
| `ds_classificacao` | `xsd:string` | false | 1..1 |
| `id_tipo_bem` | `xsd:int` | false | 1..1 |
| `ds_tipo_bem` | `xsd:string` | false | 1..1 |
| `sg_tipo_bem` | `xsd:string` | false | 1..1 |
| `sintese_bem` | `xsd:string` | true | 0..1 |
| `dt_cadastro` | `xsd:date` | true | 0..1 |

### `SICG:tg_acao`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_acao` | `xsd:int` | false | 1..1 |
| `id_situacao_acao` | `xsd:int` | false | 1..1 |
| `id_instrumento` | `xsd:int` | false | 1..1 |
| `tp_acao` | `xsd:int` | false | 1..1 |
| `no_acao` | `xsd:string` | false | 1..1 |
| `ds_acao` | `xsd:string` | false | 1..1 |
| `no_bem_inventariado` | `xsd:int` | true | 0..1 |
| `localizacao_especifica` | `xsd:string` | true | 0..1 |
| `dia_inicio_acao` | `xsd:string` | true | 0..1 |
| `mes_inicio_acao` | `xsd:string` | true | 0..1 |
| `ano_inicio_acao` | `xsd:string` | true | 0..1 |
| `dia_conclusao_acao` | `xsd:string` | true | 0..1 |
| `mes_conclusao_acao` | `xsd:string` | true | 0..1 |
| `ano_conclusao_acao` | `xsd:string` | true | 0..1 |
| `dia_inicio_lev_prelim` | `xsd:string` | true | 0..1 |
| `mes_inicio_lev_prelim` | `xsd:string` | true | 0..1 |
| `ano_inicio_lev_prelim` | `xsd:string` | true | 0..1 |
| `dia_fim_lev_prelim` | `xsd:string` | true | 0..1 |
| `mes_fim_lev_prelim` | `xsd:string` | true | 0..1 |
| `ano_fim_lev_prelim` | `xsd:string` | true | 0..1 |
| `dia_inicio_identif` | `xsd:string` | true | 0..1 |
| `mes_inicio_identif` | `xsd:string` | true | 0..1 |
| `ano_inicio_identif` | `xsd:string` | true | 0..1 |
| `dia_fim_identif` | `xsd:string` | true | 0..1 |
| `mes_fim_identif` | `xsd:string` | true | 0..1 |
| `ano_fim_identif` | `xsd:string` | true | 0..1 |
| `dia_inicio_doc` | `xsd:string` | true | 0..1 |
| `mes_inicio_doc` | `xsd:string` | true | 0..1 |
| `ano_inicio_doc` | `xsd:string` | true | 0..1 |
| `dia_fim_doc` | `xsd:string` | true | 0..1 |
| `mes_fim_doc` | `xsd:string` | true | 0..1 |
| `ano_fim_doc` | `xsd:string` | true | 0..1 |
| `dia_inicio_anal_prel` | `xsd:string` | true | 0..1 |
| `mes_inicio_anal_prel` | `xsd:string` | true | 0..1 |
| `ano_inicio_anal_prel` | `xsd:string` | true | 0..1 |
| `dia_fim_anal_prel` | `xsd:string` | true | 0..1 |
| `mes_fim_anal_prel` | `xsd:string` | true | 0..1 |
| `ano_fim_anal_prel` | `xsd:string` | true | 0..1 |
| `dia_inicio_instr_tec` | `xsd:string` | true | 0..1 |
| `mes_inicio_instr_tec` | `xsd:string` | true | 0..1 |
| `ano_inicio_instr_tec` | `xsd:string` | true | 0..1 |
| `dia_fim_instr_tec` | `xsd:string` | true | 0..1 |
| `mes_fim_instr_tec` | `xsd:string` | true | 0..1 |
| `ano_fim_instr_tec` | `xsd:string` | true | 0..1 |
| `dia_inicio_anal_final` | `xsd:string` | true | 0..1 |
| `mes_inicio_anal_final` | `xsd:string` | true | 0..1 |
| `ano_inicio_anal_final` | `xsd:string` | true | 0..1 |
| `dia_fim_anal_final` | `xsd:string` | true | 0..1 |
| `mes_fim_anal_final` | `xsd:string` | true | 0..1 |
| `ano_fim_anal_final` | `xsd:string` | true | 0..1 |
| `geometria_ponto` | `gml:PointPropertyType` | false | 1..1 |
| `geometria_poligono` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `ativo` | `xsd:boolean` | false | 1..1 |

### `SICG:tg_bem_classificacao`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ponto` | `gml:PointPropertyType` | true | 0..1 |
| `id_bem` | `xsd:int` | false | 1..1 |
| `identificacao_bem` | `xsd:string` | false | 1..1 |
| `co_iphan` | `xsd:string` | false | 1..1 |
| `no_logradouro` | `xsd:string` | true | 0..1 |
| `nu_logradouro` | `xsd:string` | true | 0..1 |
| `id_natureza` | `xsd:int` | false | 1..1 |
| `ds_natureza` | `xsd:string` | false | 1..1 |
| `codigo_iphan` | `xsd:string` | false | 1..1 |
| `id_classificacao` | `xsd:int` | false | 1..1 |
| `ds_classificacao` | `xsd:string` | false | 1..1 |
| `id_tipo_bem` | `xsd:int` | false | 1..1 |
| `ds_tipo_bem` | `xsd:string` | false | 1..1 |
| `sg_tipo_bem` | `xsd:string` | false | 1..1 |
| `sintese_bem` | `xsd:string` | true | 0..1 |
| `dt_cadastro` | `xsd:date` | true | 0..1 |

### `SICG:tg_bem_imaterial`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_bem_imaterial` | `xsd:int` | false | 1..1 |
| `id_abrangencia_bem_imat` | `xsd:int` | false | 1..1 |
| `st_registrado` | `xsd:boolean` | true | 0..1 |
| `st_identificado` | `xsd:boolean` | true | 0..1 |
| `no_bem_imaterial` | `xsd:string` | false | 1..1 |
| `ds_bem_imaterial` | `xsd:string` | false | 1..1 |
| `categoria` | `xsd:int` | false | 1..1 |
| `dt_identificacao` | `xsd:date` | true | 0..1 |
| `dt_registro` | `xsd:date` | true | 0..1 |
| `localizacao_especifica` | `xsd:string` | true | 0..1 |
| `outra_denominacao` | `xsd:string` | true | 0..1 |
| `geometria_ponto` | `gml:PointPropertyType` | false | 1..1 |
| `geometria_poligono` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `ativo` | `xsd:boolean` | false | 1..1 |
| `usuario_cadastro` | `xsd:string` | true | 0..1 |
| `integracao_licen_ambient` | `xsd:boolean` | false | 1..1 |

### `SICG:tg_hidrografia`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:decimal` | true | 0..1 |
| `__gid` | `xsd:decimal` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `codigo` | `xsd:decimal` | true | 0..1 |
| `id` | `xsd:decimal` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `SICG:tg_pre_setor`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_pre_setor` | `xsd:int` | false | 1..1 |
| `id_pre_setor_pai` | `xsd:int` | true | 0..1 |
| `id_protecao_bem` | `xsd:int` | false | 1..1 |
| `caracterizacao` | `xsd:string` | true | 0..1 |
| `orientacao_preserv_bem` | `xsd:string` | true | 0..1 |
| `st_entorno` | `xsd:boolean` | false | 1..1 |
| `st_protegido` | `xsd:boolean` | false | 1..1 |
| `st_setor` | `xsd:boolean` | false | 1..1 |
| `no_setor` | `xsd:string` | true | 0..1 |
| `normativa` | `xsd:string` | true | 0..1 |
| `permissa` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
