# MTUR — atributos das camadas

Geoportal: [[Geosserviços/MTUR/Ministério do Turismo — MTUR|Ministério do Turismo — MTUR]]

Os campos abaixo vêm de `DescribeFeatureType` (XSD), sem download de feições.

## MTU (67)

### `MTU:apoio_nautico_estruturas_se`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `cod_ibge` | `xsd:double` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `acesso` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:apoio_nautico_estruturas_sul`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `cod_ibge` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `acesso` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:area_estudo_pem_se`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `MTU:area_piloto_pem_sul`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `MTU:ataque_tubarao_se`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `ano` | `xsd:string` | true | 0..1 |
| `x` | `xsd:string` | true | 0..1 |
| `y` | `xsd:string` | true | 0..1 |
| `gravidade` | `xsd:string` | true | 0..1 |
| `spp` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fonte_1` | `xsd:string` | true | 0..1 |
| `fonte_2` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:ataque_tubarao_sul`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `ano` | `xsd:long` | true | 0..1 |
| `x` | `xsd:double` | true | 0..1 |
| `y` | `xsd:double` | true | 0..1 |
| `gravidade` | `xsd:string` | true | 0..1 |
| `spp` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `fonte_1` | `xsd:string` | true | 0..1 |
| `fonte_2` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:atividades_esportivas_se`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `fid` | `xsd:double` | true | 0..1 |
| `dn` | `xsd:long` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `MTU:atividades_esportivas_sul`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `fid` | `xsd:double` | true | 0..1 |
| `dn` | `xsd:long` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `MTU:est_kde_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `dn` | `xsd:int` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `MTU:est_kde_2018_lin`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `dn` | `xsd:int` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `MTU:est_kde_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `dn` | `xsd:int` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `MTU:est_kde_2022_lin`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `dn` | `xsd:int` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `MTU:eventos_nauticos_se_pol`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `MTU:eventos_nauticos_se_pto`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `regime` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `cod_ibge` | `xsd:double` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:eventos_nauticos_sul`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `regime` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `entidade` | `xsd:string` | true | 0..1 |
| `site` | `xsd:string` | true | 0..1 |
| `local` | `xsd:string` | true | 0..1 |
| `percurso` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:eventos_nauticos_trajetos_se`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `regime` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `MTU:eventos_nauticos_trajetos_sul`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:int` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `regime` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `MTU:fundeadores_cruzeiros_se`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `objectid_1` | `xsd:long` | true | 0..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |
| `lat_bin` | `xsd:double` | true | 0..1 |
| `lon_bin` | `xsd:double` | true | 0..1 |
| `total_vess` | `xsd:long` | true | 0..1 |
| `mean_vesse` | `xsd:double` | true | 0..1 |
| `sd_vessels` | `xsd:double` | true | 0..1 |
| `hours` | `xsd:double` | true | 0..1 |
| `mean_hours` | `xsd:double` | true | 0..1 |
| `sd_hours` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `MTU:fundeadouros_cruzeiros_sul`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |
| `lat_bin` | `xsd:double` | true | 0..1 |
| `lon_bin` | `xsd:double` | true | 0..1 |
| `total_vess` | `xsd:long` | true | 0..1 |
| `mean_vesse` | `xsd:double` | true | 0..1 |
| `sd_vessels` | `xsd:double` | true | 0..1 |
| `hours` | `xsd:double` | true | 0..1 |
| `mean_hours` | `xsd:double` | true | 0..1 |
| `sd_hours` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `MTU:fundeadouros_se`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `MTU:fundeadouros_sul`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `MTU:ind_massa_sal_kde_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `dn` | `xsd:int` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `MTU:ind_massa_sal_kde_2018_lin`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `dn` | `xsd:int` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `MTU:ind_massa_sal_kde_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `dn` | `xsd:int` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `MTU:ind_massa_sal_kde_2022_lin`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `dn` | `xsd:int` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `MTU:linha_costa_carta_sao_santos_campos_espsanto`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `tt` | `xsd:long` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `MTU:linha_costa_carta_sao_santos_pelotas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `isl` | `xsd:double` | true | 0..1 |
| `segmento` | `xsd:string` | true | 0..1 |
| `oid_` | `xsd:long` | true | 0..1 |
| `area_est` | `xsd:string` | true | 0..1 |
| `denom_mapa` | `xsd:string` | true | 0..1 |
| `denom_loca` | `xsd:string` | true | 0..1 |
| `data_levan` | `xsd:date` | true | 0..1 |
| `horario` | `xsd:string` | true | 0..1 |
| `observ` | `xsd:string` | true | 0..1 |
| `ext_seg` | `xsd:string` | true | 0..1 |
| `preamar` | `xsd:string` | true | 0..1 |
| `zona_surf` | `xsd:string` | true | 0..1 |
| `transp_lit` | `xsd:string` | true | 0..1 |
| `est_refer` | `xsd:string` | true | 0..1 |
| `tipo_lit` | `xsd:string` | true | 0..1 |
| `l_praia` | `xsd:string` | true | 0..1 |
| `h_berma` | `xsd:string` | true | 0..1 |
| `dec_face` | `xsd:string` | true | 0..1 |
| `comp_oleo` | `xsd:string` | true | 0..1 |
| `risco_amb` | `xsd:string` | true | 0..1 |
| `risco_soc` | `xsd:string` | true | 0..1 |
| `asp_operac` | `xsd:string` | true | 0..1 |
| `comentario` | `xsd:string` | true | 0..1 |
| `habitat` | `xsd:string` | true | 0..1 |
| `arrebentac` | `xsd:string` | true | 0..1 |
| `h_onda` | `xsd:string` | true | 0..1 |
| `dec_praia` | `xsd:string` | true | 0..1 |
| `banc_areia` | `xsd:string` | true | 0..1 |
| `subs_rocha` | `xsd:string` | true | 0..1 |
| `subs_sed` | `xsd:string` | true | 0..1 |
| `subs_rocho` | `xsd:string` | true | 0..1 |
| `vegetacao` | `xsd:string` | true | 0..1 |
| `pos_estr` | `xsd:string` | true | 0..1 |
| `mat_estr` | `xsd:string` | true | 0..1 |
| `est_feicao` | `xsd:string` | true | 0..1 |
| `est_vegeta` | `xsd:string` | true | 0..1 |
| `residuos` | `xsd:string` | true | 0..1 |
| `baixamar` | `xsd:string` | true | 0..1 |
| `armadilhas` | `xsd:string` | true | 0..1 |
| `limpeza` | `xsd:string` | true | 0..1 |
| `exposicao` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `fid_tatica` | `xsd:long` | true | 0..1 |
| `fid_pel1_t` | `xsd:long` | true | 0..1 |
| `carta` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `isl2` | `xsd:string` | true | 0..1 |
| `shape_le_1` | `xsd:double` | true | 0..1 |
| `dissolve` | `xsd:int` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `MTU:mergulho_se`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `prof` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:mergulho_sul`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `lat` | `xsd:double` | true | 0..1 |
| `long` | `xsd:double` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `prof` | `xsd:long` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:monitoramento_baln_se`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `praia` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `cod_ibge` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:monitoramento_baln_sul`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `y` | `xsd:string` | true | 0..1 |
| `x` | `xsd:string` | true | 0..1 |
| `praia` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `cod_ibge` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:naufragios_hist_se`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `y` | `xsd:string` | true | 0..1 |
| `x` | `xsd:string` | true | 0..1 |
| `n_ordem` | `xsd:string` | true | 0..1 |
| `nome_embar` | `xsd:string` | true | 0..1 |
| `classe_emb` | `xsd:string` | true | 0..1 |
| `tipo_embar` | `xsd:string` | true | 0..1 |
| `causa_nauf` | `xsd:string` | true | 0..1 |
| `posicao_em` | `xsd:string` | true | 0..1 |
| `bandeira` | `xsd:string` | true | 0..1 |
| `data_naufr` | `xsd:long` | true | 0..1 |
| `fontes` | `xsd:string` | true | 0..1 |
| `inf_comple` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:naufragios_hist_sul`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `y` | `xsd:string` | true | 0..1 |
| `x` | `xsd:string` | true | 0..1 |
| `n_ordem` | `xsd:string` | true | 0..1 |
| `nome_embar` | `xsd:string` | true | 0..1 |
| `classe_emb` | `xsd:string` | true | 0..1 |
| `tipo_embar` | `xsd:string` | true | 0..1 |
| `causa_nauf` | `xsd:string` | true | 0..1 |
| `posicao_em` | `xsd:string` | true | 0..1 |
| `bandeira` | `xsd:string` | true | 0..1 |
| `data_naufr` | `xsd:double` | true | 0..1 |
| `fontes` | `xsd:string` | true | 0..1 |
| `inf_comple` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:observacao_fauna_se`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:int` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `organismo` | `xsd:string` | true | 0..1 |
| `regime` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:observacao_fauna_sul`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `organismos` | `xsd:string` | true | 0..1 |
| `regime` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:operadoras_mergulho_se`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `y` | `xsd:double` | true | 0..1 |
| `x` | `xsd:double` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `endereço` | `xsd:string` | true | 0..1 |
| `telefone` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `url` | `xsd:string` | true | 0..1 |
| `serviços` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:operadoras_mergulho_sul`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `fid` | `xsd:double` | true | 0..1 |
| `y` | `xsd:double` | true | 0..1 |
| `x` | `xsd:double` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `endereco` | `xsd:string` | true | 0..1 |
| `telefone` | `xsd:double` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `url` | `xsd:string` | true | 0..1 |
| `servicos` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:patrimonio_historico_cultural_marinho_se`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id_bem` | `xsd:long` | true | 0..1 |
| `identifica` | `xsd:string` | true | 0..1 |
| `co_iphan` | `xsd:string` | true | 0..1 |
| `no_logrado` | `xsd:string` | true | 0..1 |
| `nu_logrado` | `xsd:string` | true | 0..1 |
| `id_naturez` | `xsd:long` | true | 0..1 |
| `ds_naturez` | `xsd:string` | true | 0..1 |
| `codigo_iph` | `xsd:string` | true | 0..1 |
| `id_classif` | `xsd:long` | true | 0..1 |
| `ds_classif` | `xsd:string` | true | 0..1 |
| `id_tipo_be` | `xsd:long` | true | 0..1 |
| `ds_tipo_be` | `xsd:string` | true | 0..1 |
| `sg_tipo_be` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:patrimonio_historico_cultural_marinho_se_pol`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id_bem_ima` | `xsd:string` | true | 0..1 |
| `no_bem_ima` | `xsd:string` | true | 0..1 |
| `ds_bem_ima` | `xsd:string` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `localizaca` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `MTU:patrimonio_historico_cultural_marinho_sul`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `classifica` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `endereço` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `visitacao` | `xsd:string` | true | 0..1 |
| `telefone` | `xsd:double` | true | 0..1 |
| `url` | `xsd:string` | true | 0..1 |
| `tombamento` | `xsd:string` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:patrimonio_historico_cultural_marinho_sul_pol`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:int` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `classifica` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `visitacao` | `xsd:string` | true | 0..1 |
| `telefone` | `xsd:long` | true | 0..1 |
| `url` | `xsd:string` | true | 0..1 |
| `tombamento` | `xsd:string` | true | 0..1 |
| `endereco` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `MTU:portos_se`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idi_tuaria` | `xsd:double` | true | 0..1 |
| `idseq` | `xsd:double` | true | 0..1 |
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
| `numero` | `xsd:double` | true | 0..1 |
| `bairro` | `xsd:string` | true | 0..1 |
| `cep` | `xsd:string` | true | 0..1 |
| `idcidade` | `xsd:string` | true | 0..1 |
| `cidade` | `xsd:string` | true | 0..1 |
| `idestado` | `xsd:string` | true | 0..1 |
| `estado` | `xsd:string` | true | 0..1 |
| `idr_rafica` | `xsd:double` | true | 0..1 |
| `reg_rafica` | `xsd:string` | true | 0..1 |
| `loc_izacao` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:string` | true | 0..1 |
| `longitude` | `xsd:string` | true | 0..1 |
| `observacao` | `xsd:string` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `cdc_troide` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:portos_sul`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idi_tuaria` | `xsd:double` | true | 0..1 |
| `idseq` | `xsd:double` | true | 0..1 |
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
| `numero` | `xsd:double` | true | 0..1 |
| `bairro` | `xsd:string` | true | 0..1 |
| `cep` | `xsd:string` | true | 0..1 |
| `idcidade` | `xsd:string` | true | 0..1 |
| `cidade` | `xsd:string` | true | 0..1 |
| `idestado` | `xsd:string` | true | 0..1 |
| `estado` | `xsd:string` | true | 0..1 |
| `idr_rafica` | `xsd:double` | true | 0..1 |
| `reg_rafica` | `xsd:string` | true | 0..1 |
| `loc_izacao` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:string` | true | 0..1 |
| `longitude` | `xsd:string` | true | 0..1 |
| `observacao` | `xsd:string` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `cdc_troide` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:rais_estabelecimentos_2018_ponto`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `y` | `xsd:double` | true | 0..1 |
| `x` | `xsd:double` | true | 0..1 |
| `cep_estab` | `xsd:long` | true | 0..1 |
| `cnae_95` | `xsd:long` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `munic` | `xsd:string` | true | 0..1 |
| `nat_jur` | `xsd:long` | true | 0..1 |
| `qt_vincu` | `xsd:long` | true | 0..1 |
| `tam_estab` | `xsd:long` | true | 0..1 |
| `tipo_estab` | `xsd:long` | true | 0..1 |
| `ibge_subc` | `xsd:long` | true | 0..1 |
| `cnae_2.0_c` | `xsd:long` | true | 0..1 |
| `subclasse` | `xsd:long` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:rais_estabelecimentos_2022_ponto`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `y` | `xsd:double` | true | 0..1 |
| `x` | `xsd:double` | true | 0..1 |
| `cep_estab` | `xsd:string` | true | 0..1 |
| `cnae_95` | `xsd:long` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `munic` | `xsd:string` | true | 0..1 |
| `nat_jur` | `xsd:long` | true | 0..1 |
| `qt_vincu` | `xsd:long` | true | 0..1 |
| `tam_estab` | `xsd:long` | true | 0..1 |
| `tipo_estab` | `xsd:long` | true | 0..1 |
| `ibge_subc` | `xsd:long` | true | 0..1 |
| `cnae_2.0_c` | `xsd:long` | true | 0..1 |
| `subclasse` | `xsd:long` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:rais_ind_vinculos_2018_se_kernel_lin`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `dn` | `xsd:long` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `MTU:rais_indicadores_2018_ponto`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `y` | `xsd:string` | true | 0..1 |
| `x` | `xsd:string` | true | 0..1 |
| `cep_estab` | `xsd:string` | true | 0..1 |
| `cnae_95` | `xsd:string` | true | 0..1 |
| `cod_ibge` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `munic` | `xsd:string` | true | 0..1 |
| `nat_jur` | `xsd:string` | true | 0..1 |
| `qt_vincu` | `xsd:string` | true | 0..1 |
| `tam_estab` | `xsd:string` | true | 0..1 |
| `tipo_estab` | `xsd:string` | true | 0..1 |
| `ibge_subc` | `xsd:string` | true | 0..1 |
| `cnae_2.0_c` | `xsd:string` | true | 0..1 |
| `subclasse` | `xsd:string` | true | 0..1 |
| `massa_sal` | `xsd:double` | true | 0..1 |
| `media_sal` | `xsd:double` | true | 0..1 |
| `maior_sal` | `xsd:double` | true | 0..1 |
| `menor_sal` | `xsd:double` | true | 0..1 |
| `media_idad` | `xsd:long` | true | 0..1 |
| `media_sm` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:rais_indicadores_2022_ponto`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `y` | `xsd:double` | true | 0..1 |
| `x` | `xsd:double` | true | 0..1 |
| `cep_estab` | `xsd:string` | true | 0..1 |
| `cnae_95` | `xsd:long` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `munic` | `xsd:string` | true | 0..1 |
| `nat_jur` | `xsd:long` | true | 0..1 |
| `qt_vincu` | `xsd:long` | true | 0..1 |
| `tam_estab` | `xsd:long` | true | 0..1 |
| `tipo_estab` | `xsd:long` | true | 0..1 |
| `ibge_subc` | `xsd:long` | true | 0..1 |
| `cnae_2.0_c` | `xsd:long` | true | 0..1 |
| `subclasse` | `xsd:long` | true | 0..1 |
| `massa_sal` | `xsd:string` | true | 0..1 |
| `media_sal` | `xsd:double` | true | 0..1 |
| `maior_sal` | `xsd:double` | true | 0..1 |
| `menor_sal` | `xsd:double` | true | 0..1 |
| `media_idad` | `xsd:double` | true | 0..1 |
| `media_sm` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:recifes_artificiais_pol`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `finalidade` | `xsd:string` | true | 0..1 |
| `instalacao` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `MTU:recifes_artificiais_se_pnt`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `finalidade` | `xsd:string` | true | 0..1 |
| `instalacao` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:recifes_artificiais_se_pol`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `finalidade` | `xsd:string` | true | 0..1 |
| `instalacao` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `MTU:rotas_cabotagem_se`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `idhidrovia` | `xsd:double` | true | 0..1 |
| `idseq` | `xsd:double` | true | 0..1 |
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
| `idantaq` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `MTU:rotas_cabotagem_sul`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idhidrovia` | `xsd:double` | true | 0..1 |
| `idseq` | `xsd:double` | true | 0..1 |
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
| `idantaq` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `MTU:rotas_cruzeiros_se`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |
| `lat_bin` | `xsd:double` | true | 0..1 |
| `lon_bin` | `xsd:double` | true | 0..1 |
| `total_vess` | `xsd:long` | true | 0..1 |
| `mean_vesse` | `xsd:double` | true | 0..1 |
| `sd_vessels` | `xsd:double` | true | 0..1 |
| `hours` | `xsd:double` | true | 0..1 |
| `mean_hours` | `xsd:double` | true | 0..1 |
| `sd_hours` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `MTU:rotas_cruzeiros_sul`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `lat_bin` | `xsd:double` | true | 0..1 |
| `lon_bin` | `xsd:double` | true | 0..1 |
| `total_vess` | `xsd:long` | true | 0..1 |
| `mean_vesse` | `xsd:double` | true | 0..1 |
| `sd_vessels` | `xsd:double` | true | 0..1 |
| `hours` | `xsd:double` | true | 0..1 |
| `mean_hours` | `xsd:double` | true | 0..1 |
| `sd_hours` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `MTU:salva_vidas_se`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `praia` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `cod_ibge` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:salva_vidas_sul`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `praia` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `cod_ibge` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:sitios_arqueologicos_se`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id_bem` | `xsd:long` | true | 0..1 |
| `identifica` | `xsd:string` | true | 0..1 |
| `co_iphan` | `xsd:string` | true | 0..1 |
| `no_logrado` | `xsd:string` | true | 0..1 |
| `nu_logrado` | `xsd:string` | true | 0..1 |
| `id_naturez` | `xsd:long` | true | 0..1 |
| `ds_naturez` | `xsd:string` | true | 0..1 |
| `codigo_iph` | `xsd:string` | true | 0..1 |
| `id_classif` | `xsd:long` | true | 0..1 |
| `ds_classif` | `xsd:string` | true | 0..1 |
| `id_tipo_be` | `xsd:long` | true | 0..1 |
| `ds_tipo_be` | `xsd:string` | true | 0..1 |
| `sg_tipo_be` | `xsd:string` | true | 0..1 |
| `sintese_be` | `xsd:string` | true | 0..1 |
| `dt_cadastr` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:sitios_arqueologicos_sul`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `endereco` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `visitacao` | `xsd:string` | true | 0..1 |
| `telefone` | `xsd:double` | true | 0..1 |
| `url` | `xsd:string` | true | 0..1 |
| `id_bem` | `xsd:long` | true | 0..1 |
| `co_iphan` | `xsd:string` | true | 0..1 |
| `id_naturez` | `xsd:long` | true | 0..1 |
| `ds_naturez` | `xsd:string` | true | 0..1 |
| `codigo_iph` | `xsd:string` | true | 0..1 |
| `id_classif` | `xsd:long` | true | 0..1 |
| `ds_classif` | `xsd:string` | true | 0..1 |
| `id_tipo_be` | `xsd:long` | true | 0..1 |
| `ds_tipo_be` | `xsd:string` | true | 0..1 |
| `sg_tipo_be` | `xsd:string` | true | 0..1 |
| `sintese_be` | `xsd:string` | true | 0..1 |
| `dt_cadastr` | `xsd:string` | true | 0..1 |
| `zona` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:turismo_nautico_recreio_sul`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `cod_ibge` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `descricao` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:turismo_nautico_se`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `endereco` | `xsd:string` | true | 0..1 |
| `telefone` | `xsd:string` | true | 0..1 |
| `url` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `cod_ibge` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `acesso` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `joina` | `xsd:int` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:turismo_praia_se`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `cod_ibge` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `salvavidas` | `xsd:string` | true | 0..1 |
| `baln` | `xsd:string` | true | 0..1 |
| `uso` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `MTU:turismo_praia_sul`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `salvavidas` | `xsd:int` | true | 0..1 |
| `baln` | `xsd:int` | true | 0..1 |
| `uso` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `MTU:vista_panoramica_interesse_se`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `dn` | `xsd:int` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `MTU:vista_panoramica_interesse_sul`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `dn` | `xsd:int` | true | 0..1 |
| `valor` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `MTU:vista_panoramica_se`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `tp_areaest` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `MTU:vista_panoramica_sul`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `cod_ibge` | `xsd:long` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |
