# SEDAM RO — atributos das camadas

Geoportal: [[Geosserviços/SEDAM RO/Governo de Rondônia — SEDAM|Governo de Rondônia — SEDAM]]

Os campos abaixo vêm do `DescribeFeatureType` (XSD), sem download de feições. `gml:*` geralmente identifica a geometria.

## acre (5)

### `acre:area_imovel`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `cod_tema` | `xsd:string` | true | 0..1 |
| `nom_tema` | `xsd:string` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `mod_fiscal` | `xsd:decimal` | true | 0..1 |
| `num_area` | `xsd:decimal` | true | 0..1 |
| `ind_status` | `xsd:string` | true | 0..1 |
| `ind_tipo` | `xsd:string` | true | 0..1 |
| `des_condic` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `cod_estado` | `xsd:string` | true | 0..1 |
| `dat_criaca` | `xsd:string` | true | 0..1 |
| `dat_atuali` | `xsd:string` | true | 0..1 |

### `acre:sigef_privado`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `parcela_co` | `xsd:string` | true | 0..1 |
| `rt` | `xsd:string` | true | 0..1 |
| `art` | `xsd:string` | true | 0..1 |
| `situacao_i` | `xsd:string` | true | 0..1 |
| `codigo_imo` | `xsd:string` | true | 0..1 |
| `data_submi` | `xsd:date` | true | 0..1 |
| `data_aprov` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `nome_area` | `xsd:string` | true | 0..1 |
| `registro_m` | `xsd:string` | true | 0..1 |
| `registro_d` | `xsd:date` | true | 0..1 |
| `municipio_` | `xsd:int` | true | 0..1 |
| `uf_id` | `xsd:int` | true | 0..1 |

### `acre:sigef_publico`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `parcela_co` | `xsd:string` | true | 0..1 |
| `rt` | `xsd:string` | true | 0..1 |
| `art` | `xsd:string` | true | 0..1 |
| `situacao_i` | `xsd:string` | true | 0..1 |
| `codigo_imo` | `xsd:string` | true | 0..1 |
| `data_submi` | `xsd:date` | true | 0..1 |
| `data_aprov` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `nome_area` | `xsd:string` | true | 0..1 |
| `registro_m` | `xsd:string` | true | 0..1 |
| `registro_d` | `xsd:date` | true | 0..1 |
| `municipio_` | `xsd:int` | true | 0..1 |
| `uf_id` | `xsd:int` | true | 0..1 |

### `acre:snci_privado`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `num_proces` | `xsd:string` | true | 0..1 |
| `sr` | `xsd:string` | true | 0..1 |
| `num_certif` | `xsd:string` | true | 0..1 |
| `data_certi` | `xsd:date` | true | 0..1 |
| `qtd_area_p` | `xsd:string` | true | 0..1 |
| `cod_profis` | `xsd:string` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `nome_imove` | `xsd:string` | true | 0..1 |
| `uf_municip` | `xsd:string` | true | 0..1 |

### `acre:snci_publico`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `num_proces` | `xsd:string` | true | 0..1 |
| `sr` | `xsd:string` | true | 0..1 |
| `num_certif` | `xsd:string` | true | 0..1 |
| `data_certi` | `xsd:date` | true | 0..1 |
| `qtd_area_p` | `xsd:string` | true | 0..1 |
| `cod_profis` | `xsd:string` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `nome_imove` | `xsd:string` | true | 0..1 |
| `uf_municip` | `xsd:string` | true | 0..1 |

## ana (2)

### `ana:ana_estacoes`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Altitude` | `xsd:string` | true | 0..1 |
| `Area_Drenagem` | `xsd:string` | true | 0..1 |
| `Bacia_Nome` | `xsd:string` | true | 0..1 |
| `Codigo_Adicional` | `xsd:string` | true | 0..1 |
| `Codigo_Operadora_Unidade_UF` | `xsd:string` | true | 0..1 |
| `Data_Periodo_Climatologica_Fim` | `xsd:string` | true | 0..1 |
| `Data_Periodo_Climatologica_Inicio` | `xsd:string` | true | 0..1 |
| `Data_Periodo_Desc_Liquida_Fim` | `xsd:string` | true | 0..1 |
| `Data_Periodo_Desc_liquida_Inicio` | `xsd:string` | true | 0..1 |
| `Data_Periodo_Escala_Fim` | `xsd:string` | true | 0..1 |
| `Data_Periodo_Escala_Inicio` | `xsd:string` | true | 0..1 |
| `Data_Periodo_Piezometria_Fim` | `xsd:string` | true | 0..1 |
| `Data_Periodo_Piezometria_Inicio` | `xsd:string` | true | 0..1 |
| `Data_Periodo_Pluviometro_Fim` | `xsd:string` | true | 0..1 |
| `Data_Periodo_Pluviometro_Inicio` | `xsd:string` | true | 0..1 |
| `Data_Periodo_Qual_Agua_Fim` | `xsd:string` | true | 0..1 |
| `Data_Periodo_Qual_Agua_Inicio` | `xsd:string` | true | 0..1 |
| `Data_Periodo_Registrador_Chuva_Fim` | `xsd:string` | true | 0..1 |
| `Data_Periodo_Registrador_Chuva_Inicio` | `xsd:string` | true | 0..1 |
| `Data_Periodo_Registrador_Nivel_Fim` | `xsd:string` | true | 0..1 |
| `Data_Periodo_Registrador_Nivel_Inicio` | `xsd:string` | true | 0..1 |
| `Data_Periodo_Sedimento_Inicio` | `xsd:string` | true | 0..1 |
| `Data_Periodo_Sedimento_fim` | `xsd:string` | true | 0..1 |
| `Data_Periodo_Tanque_Evapo_Fim` | `xsd:string` | true | 0..1 |
| `Data_Periodo_Tanque_Evapo_Inicio` | `xsd:string` | true | 0..1 |
| `Data_Periodo_Telemetrica_Fim` | `xsd:string` | true | 0..1 |
| `Data_Periodo_Telemetrica_Inicio` | `xsd:string` | true | 0..1 |
| `Data_Ultima_Atualizacao` | `xsd:string` | true | 0..1 |
| `Estacao_Nome` | `xsd:string` | true | 0..1 |
| `Latitude` | `xsd:string` | true | 0..1 |
| `Longitude` | `xsd:string` | true | 0..1 |
| `Municipio_Codigo` | `xsd:string` | true | 0..1 |
| `Municipio_Nome` | `xsd:string` | true | 0..1 |
| `Operadora_Codigo` | `xsd:string` | true | 0..1 |
| `Operadora_Sigla` | `xsd:string` | true | 0..1 |
| `Operadora_Sub_Unidade_UF` | `xsd:string` | true | 0..1 |
| `Operando` | `xsd:string` | true | 0..1 |
| `Responsavel_Codigo` | `xsd:string` | true | 0..1 |
| `Responsavel_Sigla` | `xsd:string` | true | 0..1 |
| `Responsavel_Unidade_UF` | `xsd:string` | true | 0..1 |
| `Rio_Codigo` | `xsd:string` | true | 0..1 |
| `Rio_Nome` | `xsd:string` | true | 0..1 |
| `Sub_Bacia_Codigo` | `xsd:string` | true | 0..1 |
| `Sub_Bacia_Nome` | `xsd:string` | true | 0..1 |
| `Tipo_Estacao` | `xsd:string` | true | 0..1 |
| `Tipo_Estacao_Climatologica` | `xsd:string` | true | 0..1 |
| `Tipo_Estacao_Desc_Liquida` | `xsd:string` | true | 0..1 |
| `Tipo_Estacao_Escala` | `xsd:string` | true | 0..1 |
| `Tipo_Estacao_Piezometria` | `xsd:string` | true | 0..1 |
| `Tipo_Estacao_Pluviometro` | `xsd:string` | true | 0..1 |
| `Tipo_Estacao_Qual_Agua` | `xsd:string` | true | 0..1 |
| `Tipo_Estacao_Registrador_Chuva` | `xsd:string` | true | 0..1 |
| `Tipo_Estacao_Registrador_Nivel` | `xsd:string` | true | 0..1 |
| `Tipo_Estacao_Sedimentos` | `xsd:string` | true | 0..1 |
| `Tipo_Estacao_Tanque_evapo` | `xsd:string` | true | 0..1 |
| `Tipo_Estacao_Telemetrica` | `xsd:string` | true | 0..1 |
| `Tipo_Rede_Basica` | `xsd:string` | true | 0..1 |
| `Tipo_Rede_Captacao` | `xsd:string` | true | 0..1 |
| `Tipo_Rede_Classe_Vazao` | `xsd:string` | true | 0..1 |
| `Tipo_Rede_Curso_Dagua` | `xsd:string` | true | 0..1 |
| `Tipo_Rede_Energetica` | `xsd:string` | true | 0..1 |
| `Tipo_Rede_Estrategica` | `xsd:string` | true | 0..1 |
| `Tipo_Rede_Navegacao` | `xsd:string` | true | 0..1 |
| `Tipo_Rede_Qual_Agua` | `xsd:string` | true | 0..1 |
| `Tipo_Rede_Sedimentos` | `xsd:string` | true | 0..1 |
| `UF_Estacao` | `xsd:string` | true | 0..1 |
| `UF_Nome_Estacao` | `xsd:string` | true | 0..1 |
| `codigobacia` | `xsd:string` | true | 0..1 |
| `codigoestacao` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:PointPropertyType` | true | 0..1 |

### `ana:pontos_captacao_agua`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `cd_massa_d` | `xsd:string` | true | 0..1 |
| `nm_massa_d` | `xsd:string` | true | 0..1 |
| `sistema` | `xsd:string` | true | 0..1 |
| `nm_captaca` | `xsd:string` | true | 0..1 |
| `nm_fantasi` | `xsd:string` | true | 0..1 |
| `tp_captaca` | `xsd:string` | true | 0..1 |
| `status_man` | `xsd:string` | true | 0..1 |
| `tp_tratame` | `xsd:string` | true | 0..1 |
| `nm_municip` | `xsd:string` | true | 0..1 |
| `geom_obs` | `xsd:string` | true | 0..1 |

## aneel (1)

### `aneel:usinas_termoeletricas_ute`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `Name` | `xsd:string` | true | 0..1 |
| `description` | `xsd:string` | true | 0..1 |
| `timestamp` | `xsd:dateTime` | true | 0..1 |
| `begin` | `xsd:dateTime` | true | 0..1 |
| `end` | `xsd:dateTime` | true | 0..1 |
| `altitudeMode` | `xsd:string` | true | 0..1 |
| `tessellate` | `xsd:int` | true | 0..1 |
| `extrude` | `xsd:int` | true | 0..1 |
| `visibility` | `xsd:int` | true | 0..1 |
| `drawOrder` | `xsd:int` | true | 0..1 |
| `icon` | `xsd:string` | true | 0..1 |

## anm (4)

### `anm:arrendamento_ro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `PROCESSO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:int` | true | 0..1 |
| `ANO` | `xsd:int` | true | 0..1 |
| `AREA_HA` | `xsd:double` | true | 0..1 |
| `ID` | `xsd:string` | true | 0..1 |
| `DSProcesso` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |
| `CD_UF` | `xsd:string` | true | 0..1 |
| `NM_UF` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `CD_REGIAO` | `xsd:string` | true | 0..1 |
| `NM_REGIAO` | `xsd:string` | true | 0..1 |
| `SIGLA_RG` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |
| `geometry` | `gml:PolygonPropertyType` | true | 0..1 |

### `anm:processos_minerarios`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
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
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |

### `anm:reservas_garimpeiras_ro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `NOME` | `xsd:string` | true | 0..1 |
| `DOCUMENTO` | `xsd:string` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |
| `CD_UF` | `xsd:string` | true | 0..1 |
| `NM_UF` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `CD_REGIAO` | `xsd:string` | true | 0..1 |
| `NM_REGIAO` | `xsd:string` | true | 0..1 |
| `SIGLA_RG` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |
| `geometry` | `gml:PolygonPropertyType` | true | 0..1 |

### `anm:vw_processos_minerarios_ro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
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
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |

## cbm (5)

### `cbm:area_atuacao_082025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `ORDEM` | `xsd:decimal` | true | 0..1 |
| `BASE DESCE` | `xsd:string` | true | 0..1 |
| `LATITUDE` | `xsd:decimal` | true | 0..1 |
| `LONGITUDE` | `xsd:decimal` | true | 0..1 |
| `id_2` | `xsd:int` | true | 0..1 |
| `fid` | `xsd:long` | true | 0..1 |
| `cd_uf` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `nm_regiao` | `xsd:string` | true | 0..1 |
| `area_km2` | `xsd:double` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |

### `cbm:areas_atuacao_destacadas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `nome_base` | `xsd:string` | true | 0..1 |
| `tipo_base` | `xsd:string` | true | 0..1 |
| `ativo` | `xsd:boolean` | true | 0..1 |
| `cd_mun` | `xsd:string` | true | 0..1 |
| `observacoes` | `xsd:string` | true | 0..1 |
| `data_criacao` | `xsd:dateTime` | true | 0..1 |
| `data_atualizacao` | `xsd:dateTime` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `atualizado_em` | `xsd:dateTime` | true | 0..1 |

### `cbm:bases_descentralizadas_082025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `ordem` | `xsd:long` | true | 0..1 |
| `base_desce` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:decimal` | true | 0..1 |
| `longitude` | `xsd:decimal` | true | 0..1 |
| `geocodigo` | `xsd:long` | true | 0..1 |

### `cbm:bases_integradas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `name` | `xsd:string` | true | 0..1 |
| `geocodigo` | `xsd:long` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |

### `cbm:quarteis`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `field_1` | `xsd:string` | true | 0..1 |
| `field_2` | `xsd:string` | true | 0..1 |
| `field_3` | `xsd:string` | true | 0..1 |
| `field_4` | `xsd:string` | true | 0..1 |
| `field_5` | `xsd:string` | true | 0..1 |
| `field_6` | `xsd:string` | true | 0..1 |
| `field_7` | `xsd:string` | true | 0..1 |

## censipam (14)

### `censipam:estrada_estadual`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `gm_layer` | `xsd:string` | true | 0..1 |
| `gm_type` | `xsd:string` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `text_1` | `xsd:string` | true | 0..1 |
| `objeid_17` | `xsd:int` | true | 0..1 |
| `objeid_14` | `xsd:int` | true | 0..1 |
| `perimetro` | `xsd:double` | true | 0..1 |
| `objeid_12` | `xsd:int` | true | 0..1 |
| `objeid_15` | `xsd:int` | true | 0..1 |
| `objeid_13` | `xsd:int` | true | 0..1 |
| `objeid_11` | `xsd:int` | true | 0..1 |

### `censipam:estrada_federal`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `gm_layer` | `xsd:string` | true | 0..1 |
| `gm_type` | `xsd:string` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `nome_rodo` | `xsd:string` | true | 0..1 |
| `objeid_28` | `xsd:int` | true | 0..1 |
| `objeid_16` | `xsd:int` | true | 0..1 |
| `perimetro` | `xsd:double` | true | 0..1 |
| `objeid_14` | `xsd:int` | true | 0..1 |
| `text_1` | `xsd:string` | true | 0..1 |
| `objeid_19` | `xsd:int` | true | 0..1 |
| `objeid_15` | `xsd:int` | true | 0..1 |
| `objeid_13` | `xsd:int` | true | 0..1 |

### `censipam:estrada_municipal`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `name` | `xsd:string` | true | 0..1 |
| `gm_layer` | `xsd:string` | true | 0..1 |
| `gm_type` | `xsd:string` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `objet_id_4` | `xsd:int` | true | 0..1 |
| `nome_rodo` | `xsd:string` | true | 0..1 |
| `objeid_31` | `xsd:int` | true | 0..1 |
| `objet_id_1` | `xsd:int` | true | 0..1 |
| `objeid_17` | `xsd:int` | true | 0..1 |
| `perimetro` | `xsd:double` | true | 0..1 |
| `objeid_15` | `xsd:int` | true | 0..1 |
| `text_1` | `xsd:string` | true | 0..1 |
| `objeid_34` | `xsd:int` | true | 0..1 |
| `objeid_18` | `xsd:int` | true | 0..1 |
| `objeid_16` | `xsd:int` | true | 0..1 |
| `length` | `xsd:string` | true | 0..1 |
| `bearing` | `xsd:string` | true | 0..1 |

### `censipam:estrada_particular`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `name` | `xsd:string` | true | 0..1 |
| `gm_layer` | `xsd:string` | true | 0..1 |
| `gm_type` | `xsd:string` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `objet_id_4` | `xsd:long` | true | 0..1 |
| `nome_rodo` | `xsd:string` | true | 0..1 |
| `objeid_31` | `xsd:long` | true | 0..1 |
| `objet_id_1` | `xsd:long` | true | 0..1 |
| `objeid_17` | `xsd:long` | true | 0..1 |
| `perimetro` | `xsd:decimal` | true | 0..1 |
| `objeid_15` | `xsd:long` | true | 0..1 |
| `text_1` | `xsd:string` | true | 0..1 |
| `objeid_34` | `xsd:long` | true | 0..1 |
| `objeid_18` | `xsd:long` | true | 0..1 |
| `objeid_16` | `xsd:long` | true | 0..1 |
| `length` | `xsd:string` | true | 0..1 |
| `bearing` | `xsd:string` | true | 0..1 |

### `censipam:focos_censipam_24h`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_censipam` | `xsd:long` | true | 0..1 |
| `bright_ti4` | `xsd:double` | true | 0..1 |
| `bright_ti5` | `xsd:double` | true | 0..1 |
| `scan` | `xsd:double` | true | 0..1 |
| `track` | `xsd:double` | true | 0..1 |
| `acq_date` | `xsd:date` | true | 0..1 |
| `acq_time` | `xsd:string` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `confidence` | `xsd:string` | true | 0..1 |
| `version` | `xsd:string` | true | 0..1 |
| `frp` | `xsd:double` | true | 0..1 |
| `daynight` | `xsd:string` | true | 0..1 |
| `dt_aquisicao` | `xsd:dateTime` | true | 0..1 |
| `satelite` | `xsd:string` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `latitude` | `xsd:double` | true | 0..1 |
| `hash` | `xsd:string` | false | 1..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `datetime` | `xsd:dateTime` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `month` | `xsd:int` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `nome_dist` | `xsd:string` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `terra_indigena_nome` | `xsd:string` | true | 0..1 |

### `censipam:focos_censipam_30d`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_censipam` | `xsd:long` | true | 0..1 |
| `bright_ti4` | `xsd:double` | true | 0..1 |
| `bright_ti5` | `xsd:double` | true | 0..1 |
| `scan` | `xsd:double` | true | 0..1 |
| `track` | `xsd:double` | true | 0..1 |
| `acq_date` | `xsd:date` | true | 0..1 |
| `acq_time` | `xsd:string` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `confidence` | `xsd:string` | true | 0..1 |
| `version` | `xsd:string` | true | 0..1 |
| `frp` | `xsd:double` | true | 0..1 |
| `daynight` | `xsd:string` | true | 0..1 |
| `dt_aquisicao` | `xsd:dateTime` | true | 0..1 |
| `satelite` | `xsd:string` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `latitude` | `xsd:double` | true | 0..1 |
| `hash` | `xsd:string` | false | 1..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `datetime` | `xsd:dateTime` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `month` | `xsd:int` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `nome_dist` | `xsd:string` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `terra_indigena_nome` | `xsd:string` | true | 0..1 |

### `censipam:focos_censipam_7d`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_censipam` | `xsd:long` | true | 0..1 |
| `bright_ti4` | `xsd:double` | true | 0..1 |
| `bright_ti5` | `xsd:double` | true | 0..1 |
| `scan` | `xsd:double` | true | 0..1 |
| `track` | `xsd:double` | true | 0..1 |
| `acq_date` | `xsd:date` | true | 0..1 |
| `acq_time` | `xsd:string` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `confidence` | `xsd:string` | true | 0..1 |
| `version` | `xsd:string` | true | 0..1 |
| `frp` | `xsd:double` | true | 0..1 |
| `daynight` | `xsd:string` | true | 0..1 |
| `dt_aquisicao` | `xsd:dateTime` | true | 0..1 |
| `satelite` | `xsd:string` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `latitude` | `xsd:double` | true | 0..1 |
| `hash` | `xsd:string` | false | 1..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `datetime` | `xsd:dateTime` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `month` | `xsd:int` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `nome_dist` | `xsd:string` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `terra_indigena_nome` | `xsd:string` | true | 0..1 |

### `censipam:focos_censipam_hoje`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_censipam` | `xsd:long` | true | 0..1 |
| `bright_ti4` | `xsd:double` | true | 0..1 |
| `bright_ti5` | `xsd:double` | true | 0..1 |
| `scan` | `xsd:double` | true | 0..1 |
| `track` | `xsd:double` | true | 0..1 |
| `acq_date` | `xsd:date` | true | 0..1 |
| `acq_time` | `xsd:string` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `confidence` | `xsd:string` | true | 0..1 |
| `version` | `xsd:string` | true | 0..1 |
| `frp` | `xsd:double` | true | 0..1 |
| `daynight` | `xsd:string` | true | 0..1 |
| `dt_aquisicao` | `xsd:dateTime` | true | 0..1 |
| `satelite` | `xsd:string` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `latitude` | `xsd:double` | true | 0..1 |
| `hash` | `xsd:string` | false | 1..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `datetime` | `xsd:dateTime` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `month` | `xsd:int` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `nome_dist` | `xsd:string` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `terra_indigena_nome` | `xsd:string` | true | 0..1 |

### `censipam:tb_evento_fogo_ro_2020_2023`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `id_status_` | `xsd:long` | true | 0..1 |
| `dt_minima` | `xsd:string` | true | 0..1 |
| `dt_maxima` | `xsd:string` | true | 0..1 |
| `status_vis` | `xsd:string` | true | 0..1 |
| `prioridade` | `xsd:string` | true | 0..1 |
| `persistenc` | `xsd:long` | true | 0..1 |
| `indice_per` | `xsd:string` | true | 0..1 |
| `qtd_detecc` | `xsd:long` | true | 0..1 |
| `area_km2` | `xsd:decimal` | true | 0..1 |
| `is_recorre` | `xsd:int` | true | 0..1 |
| `dt_ultima_` | `xsd:string` | true | 0..1 |
| `id_tipo_fo` | `xsd:long` | true | 0..1 |
| `dt_criacao` | `xsd:string` | true | 0..1 |
| `cd_uf` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `nm_regiao` | `xsd:string` | true | 0..1 |
| `area_km2_2` | `xsd:double` | true | 0..1 |
| `ano` | `xsd:long` | true | 0..1 |

### `censipam:tb_evento_fogo_ro_2024`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `id_status_evento` | `xsd:int` | true | 0..1 |
| `dt_minima` | `xsd:dateTime` | true | 0..1 |
| `dt_maxima` | `xsd:dateTime` | true | 0..1 |
| `status_visita` | `xsd:string` | true | 0..1 |
| `prioridade_evento` | `xsd:string` | true | 0..1 |
| `persistencia_dias` | `xsd:int` | true | 0..1 |
| `indice_persistencia_normalizada` | `xsd:string` | true | 0..1 |
| `qtd_deteccoes` | `xsd:int` | true | 0..1 |
| `area_km2` | `xsd:double` | true | 0..1 |
| `is_recorrente` | `xsd:boolean` | true | 0..1 |
| `dt_ultima_visao` | `xsd:dateTime` | true | 0..1 |
| `id_tipo_fogo` | `xsd:int` | true | 0..1 |
| `dt_criacao` | `xsd:dateTime` | true | 0..1 |
| `dt_insercao` | `xsd:dateTime` | true | 0..1 |
| `ano` | `xsd:int` | true | 0..1 |
| `CD_UF` | `xsd:string` | true | 0..1 |
| `NM_UF` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `NM_REGIAO` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |

### `censipam:trecho_rodoviario_edgv`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `gid` | `xsd:decimal` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `sigla` | `xsd:string` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `jurisidica` | `xsd:string` | true | 0..1 |
| `administra` | `xsd:string` | true | 0..1 |
| `concession` | `xsd:string` | true | 0..1 |
| `revestimen` | `xsd:string` | true | 0..1 |
| `operaciona` | `xsd:string` | true | 0..1 |
| `situacaofi` | `xsd:string` | true | 0..1 |
| `canteirodi` | `xsd:string` | true | 0..1 |
| `nrpista` | `xsd:int` | true | 0..1 |
| `nrfaixa` | `xsd:int` | true | 0..1 |
| `trafego` | `xsd:string` | true | 0..1 |
| `tipopavime` | `xsd:string` | true | 0..1 |
| `tipovia` | `xsd:string` | true | 0..1 |
| `codtrechor` | `xsd:string` | true | 0..1 |
| `limitevelo` | `xsd:decimal` | true | 0..1 |
| `trechoempe` | `xsd:string` | true | 0..1 |
| `acostament` | `xsd:string` | true | 0..1 |

### `censipam:vw_trecho_rodoviario_estadual`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `sigla` | `xsd:string` | true | 0..1 |
| `jurisidica` | `xsd:string` | true | 0..1 |
| `administra` | `xsd:string` | true | 0..1 |
| `concession` | `xsd:string` | true | 0..1 |
| `revestimen` | `xsd:string` | true | 0..1 |
| `operaciona` | `xsd:string` | true | 0..1 |
| `situacaofi` | `xsd:string` | true | 0..1 |
| `canteirodi` | `xsd:string` | true | 0..1 |
| `nrpista` | `xsd:int` | true | 0..1 |
| `nrfaixa` | `xsd:int` | true | 0..1 |
| `trafego` | `xsd:string` | true | 0..1 |
| `tipopavime` | `xsd:string` | true | 0..1 |
| `tipovia` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |

### `censipam:vw_trecho_rodoviario_federal`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `sigla` | `xsd:string` | true | 0..1 |
| `jurisidica` | `xsd:string` | true | 0..1 |
| `administra` | `xsd:string` | true | 0..1 |
| `concession` | `xsd:string` | true | 0..1 |
| `revestimen` | `xsd:string` | true | 0..1 |
| `operaciona` | `xsd:string` | true | 0..1 |
| `situacaofi` | `xsd:string` | true | 0..1 |
| `canteirodi` | `xsd:string` | true | 0..1 |
| `nrpista` | `xsd:int` | true | 0..1 |
| `nrfaixa` | `xsd:int` | true | 0..1 |
| `trafego` | `xsd:string` | true | 0..1 |
| `tipopavime` | `xsd:string` | true | 0..1 |
| `tipovia` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |

### `censipam:vw_trecho_rodoviario_municipal`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `sigla` | `xsd:string` | true | 0..1 |
| `jurisidica` | `xsd:string` | true | 0..1 |
| `administra` | `xsd:string` | true | 0..1 |
| `concession` | `xsd:string` | true | 0..1 |
| `revestimen` | `xsd:string` | true | 0..1 |
| `operaciona` | `xsd:string` | true | 0..1 |
| `situacaofi` | `xsd:string` | true | 0..1 |
| `canteirodi` | `xsd:string` | true | 0..1 |
| `nrpista` | `xsd:int` | true | 0..1 |
| `nrfaixa` | `xsd:int` | true | 0..1 |
| `trafego` | `xsd:string` | true | 0..1 |
| `tipopavime` | `xsd:string` | true | 0..1 |
| `tipovia` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |

## cfp (3)

### `cfp:vw_ati_auf_publico`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `CAR` | `xsd:string` | true | 0..1 |
| `AUTOR.` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `INICIO` | `xsd:date` | true | 0..1 |
| `FIM` | `xsd:date` | true | 0..1 |
| `MUNICIPIO` | `xsd:string` | true | 0..1 |
| `ERGAS` | `xsd:string` | true | 0..1 |
| `ANO` | `xsd:long` | true | 0..1 |

### `cfp:vw_ati_auf_validos_publico`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `CAR` | `xsd:string` | true | 0..1 |
| `AUTOR.` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `INICIO` | `xsd:date` | true | 0..1 |
| `FIM` | `xsd:date` | true | 0..1 |
| `MUNICIPIO` | `xsd:string` | true | 0..1 |
| `ERGAS` | `xsd:string` | true | 0..1 |
| `ANO` | `xsd:long` | true | 0..1 |

### `cfp:vw_limpeza_pastagem_externo`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `ano` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |

## coai (1)

### `coai:vw_coai_areas_embargadas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `infracao` | `xsd:string` | true | 0..1 |

## codef (10)

### `codef:vw_areas_codef_asv`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `projeto_de` | `xsd:string` | true | 0..1 |
| `car` | `xsd:string` | true | 0..1 |

### `codef:vw_areas_codef_cai`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `projeto_de` | `xsd:string` | true | 0..1 |
| `car` | `xsd:string` | true | 0..1 |

### `codef:vw_areas_codef_crv`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `projeto_de` | `xsd:string` | true | 0..1 |
| `car` | `xsd:string` | true | 0..1 |

### `codef:vw_areas_codef_lapr`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `projeto_de` | `xsd:string` | true | 0..1 |
| `car` | `xsd:string` | true | 0..1 |

### `codef:vw_areas_codef_lc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `projeto_de` | `xsd:string` | true | 0..1 |
| `car` | `xsd:string` | true | 0..1 |

### `codef:vw_areas_codef_pef`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `projeto_de` | `xsd:string` | true | 0..1 |
| `car` | `xsd:string` | true | 0..1 |

### `codef:vw_areas_codef_pmfs`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `projeto_de` | `xsd:string` | true | 0..1 |
| `car` | `xsd:string` | true | 0..1 |

### `codef:vw_codef_apat_publico`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `car` | `xsd:string` | true | 0..1 |

### `codef:vw_codef_aumpf_publico`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `projeto_de` | `xsd:string` | true | 0..1 |
| `car` | `xsd:string` | true | 0..1 |

### `codef:vw_codef_reposicao_florestal_publico`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `car` | `xsd:string` | true | 0..1 |

## cogeo (49)

### `cogeo:Aptidao_agricula_categorizado_ro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `codigo` | `xsd:string` | true | 0..1 |
| `color` | `xsd:string` | true | 0..1 |
| `aptagr#` | `xsd:int` | true | 0..1 |
| `aptagr_id` | `xsd:int` | true | 0..1 |
| `terrain` | `xsd:string` | true | 0..1 |
| `categoriza` | `xsd:string` | true | 0..1 |
| `subgrupo` | `xsd:string` | true | 0..1 |

### `cogeo:areas_agricultaveis_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `dn` | `xsd:int` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |

### `cogeo:base_sicar_Area_Consol`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `cod_tema` | `xsd:string` | true | 0..1 |
| `nom_tema` | `xsd:string` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `num_area` | `xsd:decimal` | true | 0..1 |
| `ind_status` | `xsd:string` | true | 0..1 |
| `des_condic` | `xsd:string` | true | 0..1 |

### `cogeo:base_sicar_area_pousio`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `cod_tema` | `xsd:string` | true | 0..1 |
| `nom_tema` | `xsd:string` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `num_area` | `xsd:decimal` | true | 0..1 |
| `ind_status` | `xsd:string` | true | 0..1 |
| `des_condic` | `xsd:string` | true | 0..1 |

### `cogeo:base_sicar_hidrografia`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `cod_tema` | `xsd:string` | true | 0..1 |
| `nom_tema` | `xsd:string` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `ind_status` | `xsd:string` | true | 0..1 |
| `des_condic` | `xsd:string` | true | 0..1 |

### `cogeo:base_sicar_RL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `cod_tema` | `xsd:string` | true | 0..1 |
| `nom_tema` | `xsd:string` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `num_area` | `xsd:decimal` | true | 0..1 |
| `ind_status` | `xsd:string` | true | 0..1 |
| `des_condic` | `xsd:string` | true | 0..1 |

### `cogeo:base_sicar_servidao_adm`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `cod_tema` | `xsd:string` | true | 0..1 |
| `nom_tema` | `xsd:string` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `num_area` | `xsd:decimal` | true | 0..1 |
| `ind_status` | `xsd:string` | true | 0..1 |
| `des_condic` | `xsd:string` | true | 0..1 |

### `cogeo:base_sicar_uso_restrito`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `cod_tema` | `xsd:string` | true | 0..1 |
| `nom_tema` | `xsd:string` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `num_area` | `xsd:decimal` | true | 0..1 |
| `ind_status` | `xsd:string` | true | 0..1 |
| `des_condic` | `xsd:string` | true | 0..1 |

### `cogeo:base_sicar_veget_nativa`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `cod_tema` | `xsd:string` | true | 0..1 |
| `nom_tema` | `xsd:string` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `num_area` | `xsd:decimal` | true | 0..1 |
| `ind_status` | `xsd:string` | true | 0..1 |
| `des_condic` | `xsd:string` | true | 0..1 |

### `cogeo:bases_cbm`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `tipo_base` | `xsd:string` | false | 1..1 |
| `nome_base` | `xsd:string` | true | 0..1 |
| `ativo` | `xsd:boolean` | false | 1..1 |
| `area_atuacao` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `ponto_referencia` | `gml:PointPropertyType` | true | 0..1 |
| `latitude` | `xsd:decimal` | true | 0..1 |
| `longitude` | `xsd:decimal` | true | 0..1 |
| `geocodigo` | `xsd:long` | true | 0..1 |
| `nome_municipio` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `observacoes` | `xsd:string` | true | 0..1 |
| `data_criacao` | `xsd:dateTime` | true | 0..1 |
| `data_atualizacao` | `xsd:dateTime` | true | 0..1 |

### `cogeo:basesCBM`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `tipo_base` | `xsd:string` | false | 1..1 |
| `nome_base` | `xsd:string` | true | 0..1 |
| `ativo` | `xsd:boolean` | false | 1..1 |
| `area_atuacao` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `ponto_referencia` | `gml:PointPropertyType` | true | 0..1 |
| `latitude` | `xsd:decimal` | true | 0..1 |
| `longitude` | `xsd:decimal` | true | 0..1 |
| `geocodigo` | `xsd:long` | true | 0..1 |
| `nome_municipio` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `observacoes` | `xsd:string` | true | 0..1 |
| `data_criacao` | `xsd:dateTime` | true | 0..1 |
| `data_atualizacao` | `xsd:dateTime` | true | 0..1 |

### `cogeo:CENAS_LANDSAT5_RO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `cena` | `xsd:string` | true | 0..1 |

### `cogeo:deter_public_ro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `FID` | `xsd:string` | true | 0..1 |
| `CLASSNAME` | `xsd:string` | true | 0..1 |
| `QUADRANT` | `xsd:string` | true | 0..1 |
| `PATH_ROW` | `xsd:string` | true | 0..1 |
| `VIEW_DATE` | `xsd:string` | true | 0..1 |
| `SENSOR` | `xsd:string` | true | 0..1 |
| `SATELLITE` | `xsd:string` | true | 0..1 |
| `AREAUCKM` | `xsd:double` | true | 0..1 |
| `UC` | `xsd:string` | true | 0..1 |
| `AREAMUNKM` | `xsd:double` | true | 0..1 |
| `MUNICIPALI` | `xsd:string` | true | 0..1 |
| `GEOCODIBGE` | `xsd:string` | true | 0..1 |
| `UF` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `ano` | `xsd:int` | true | 0..1 |
| `mes/ano` | `xsd:string` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `lat` | `xsd:double` | true | 0..1 |
| `long` | `xsd:double` | true | 0..1 |
| `lat_dms` | `xsd:string` | true | 0..1 |
| `long_dms` | `xsd:string` | true | 0..1 |

### `cogeo:DIAGNOSTICOS_LIXAO_RO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `data` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:decimal` | true | 0..1 |
| `longitude` | `xsd:decimal` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `uso_lixao` | `xsd:string` | true | 0..1 |
| `destinorsu` | `xsd:string` | true | 0..1 |
| `temcatador` | `xsd:string` | true | 0..1 |

### `cogeo:divisao_municipal_bolivia`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `capital` | `xsd:string` | true | 0..1 |
| `objectid_1` | `xsd:long` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `pais_pcode` | `xsd:string` | true | 0..1 |
| `departamento` | `xsd:string` | true | 0..1 |
| `departamento_pcode` | `xsd:string` | true | 0..1 |
| `provincia` | `xsd:string` | true | 0..1 |
| `provincia_pcode` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `municipio_pcode` | `xsd:string` | true | 0..1 |
| `w` | `xsd:long` | true | 0..1 |

### `cogeo:fabdem_curvas_de_nivel_10m_ro_31980`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `elevation` | `xsd:int` | true | 0..1 |

### `cogeo:fabdem_curvas_de_nivel_20m_ro_31980`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `elevation` | `xsd:int` | true | 0..1 |

### `cogeo:fabdem_curvas_de_nivel_40m_ro_31980`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `elevation` | `xsd:int` | true | 0..1 |

### `cogeo:focos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:string` | false | 1..1 |
| `hash` | `xsd:string` | false | 1..1 |
| `latitude` | `xsd:double` | false | 1..1 |
| `longitude` | `xsd:double` | false | 1..1 |
| `geometry` | `gml:GeometryPropertyType` | false | 1..1 |
| `bright_ti4` | `xsd:double` | true | 0..1 |
| `bright_ti5` | `xsd:double` | true | 0..1 |
| `scan` | `xsd:double` | true | 0..1 |
| `track` | `xsd:double` | true | 0..1 |
| `frp` | `xsd:double` | true | 0..1 |
| `acq_date` | `xsd:string` | false | 1..1 |
| `acq_time` | `xsd:long` | false | 1..1 |
| `datetime` | `xsd:dateTime` | false | 1..1 |
| `daynight` | `xsd:string` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `instrument` | `xsd:string` | true | 0..1 |
| `confidence` | `xsd:string` | true | 0..1 |
| `version` | `xsd:string` | true | 0..1 |
| `sat` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `terra_indigena_nome` | `xsd:string` | true | 0..1 |
| `nome_car` | `xsd:string` | true | 0..1 |
| `nome_dist` | `xsd:string` | true | 0..1 |
| `created_at` | `xsd:dateTime` | true | 0..1 |
| `updated_at` | `xsd:dateTime` | true | 0..1 |
| `qntd_notificacoes` | `xsd:int` | true | 0..1 |

### `cogeo:focos_cluster`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:string` | false | 1..1 |
| `geom` | `gml:GeometryPropertyType` | false | 1..1 |
| `focos_id` | `xsd:string` | false | 1..1 |
| `frp_total` | `xsd:double` | true | 0..1 |
| `frp_medio` | `xsd:double` | true | 0..1 |
| `frp_maximo` | `xsd:double` | true | 0..1 |
| `qntd_dias` | `xsd:int` | true | 0..1 |
| `area_em_km` | `xsd:double` | true | 0..1 |
| `area_em_ha` | `xsd:double` | true | 0..1 |
| `velocidade_propagacao_km_h` | `xsd:double` | true | 0..1 |
| `velocidade_propagacao_ha_h` | `xsd:double` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `observacao` | `xsd:string` | true | 0..1 |
| `verificado` | `xsd:boolean` | true | 0..1 |
| `risco_car` | `xsd:double` | true | 0..1 |
| `risco_ti` | `xsd:double` | true | 0..1 |
| `risco_uc` | `xsd:double` | true | 0..1 |
| `risco` | `xsd:double` | true | 0..1 |
| `probabilidade` | `xsd:string` | true | 0..1 |
| `qntd_notificacoes` | `xsd:int` | true | 0..1 |
| `qntd_horas` | `xsd:int` | true | 0..1 |
| `qntd_focos` | `xsd:int` | true | 0..1 |
| `data_inicio` | `xsd:dateTime` | true | 0..1 |
| `data_fim` | `xsd:dateTime` | true | 0..1 |
| `confiabilidade` | `xsd:double` | true | 0..1 |
| `ativo` | `xsd:boolean` | true | 0..1 |
| `data_atualizado` | `xsd:dateTime` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `historico_focos` | `xsd:string` | true | 0..1 |

### `cogeo:focos_cluster_noaa20`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:string` | false | 1..1 |
| `geom` | `gml:GeometryPropertyType` | false | 1..1 |
| `focos_id` | `xsd:string` | false | 1..1 |
| `frp_total` | `xsd:double` | true | 0..1 |
| `frp_medio` | `xsd:double` | true | 0..1 |
| `frp_maximo` | `xsd:double` | true | 0..1 |
| `qntd_dias` | `xsd:int` | true | 0..1 |
| `qntd_horas` | `xsd:int` | true | 0..1 |
| `data_inicio` | `xsd:dateTime` | true | 0..1 |
| `data_fim` | `xsd:dateTime` | true | 0..1 |
| `area_em_km` | `xsd:double` | true | 0..1 |
| `area_em_ha` | `xsd:double` | true | 0..1 |
| `velocidade_propagacao_km_h` | `xsd:double` | true | 0..1 |
| `velocidade_propagacao_ha_h` | `xsd:double` | true | 0..1 |
| `qntd_focos` | `xsd:int` | true | 0..1 |
| `risco_car` | `xsd:double` | true | 0..1 |
| `risco_ti` | `xsd:double` | true | 0..1 |
| `risco_uc` | `xsd:double` | true | 0..1 |
| `risco` | `xsd:double` | true | 0..1 |
| `confiabilidade` | `xsd:double` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `probabilidade` | `xsd:string` | true | 0..1 |
| `ativo` | `xsd:boolean` | true | 0..1 |
| `verificado` | `xsd:boolean` | true | 0..1 |
| `qntd_notificacoes` | `xsd:int` | true | 0..1 |
| `observacao` | `xsd:string` | true | 0..1 |
| `data_atualizado` | `xsd:dateTime` | true | 0..1 |
| `created_at` | `xsd:dateTime` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `historico_focos` | `xsd:string` | true | 0..1 |

### `cogeo:focos_unificados`

> [!warning] Schema unresolved
> O XSD não foi resolvido nesta coleta. Reconsulte o endpoint antes de usar a camada.


### `cogeo:GRADES_CBERS4A_MUX`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `path` | `xsd:long` | true | 0..1 |
| `row` | `xsd:long` | true | 0..1 |
| `path_row` | `xsd:string` | true | 0..1 |

### `cogeo:grades_cena_data_landsat5_2008`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `name` | `xsd:string` | true | 0..1 |
| `cena` | `xsd:string` | true | 0..1 |

### `cogeo:igarapes_micro_bacia_arara`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `NAME` | `xsd:string` | true | 0..1 |
| `LAYER` | `xsd:string` | true | 0..1 |
| `KML_STYLE` | `xsd:string` | true | 0..1 |
| `KML_FOLDER` | `xsd:string` | true | 0..1 |
| `tessellate` | `xsd:int` | true | 0..1 |

### `cogeo:limite_micro_bacia_arara`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `GM_TYPE` | `xsd:string` | true | 0..1 |
| `GM_LAYER` | `xsd:string` | true | 0..1 |
| `CLASSNAME` | `xsd:string` | true | 0..1 |
| `QUADRANT` | `xsd:string` | true | 0..1 |
| `PATH_ROW` | `xsd:string` | true | 0..1 |
| `VIEW_DATE` | `xsd:string` | true | 0..1 |
| `SENSOR` | `xsd:string` | true | 0..1 |
| `SATELLITE` | `xsd:string` | true | 0..1 |
| `AREAUCKM` | `xsd:string` | true | 0..1 |
| `UC` | `xsd:string` | true | 0..1 |
| `AREAMUNKM` | `xsd:string` | true | 0..1 |
| `MUNICIPALI` | `xsd:string` | true | 0..1 |
| `UF` | `xsd:string` | true | 0..1 |
| `AREA2` | `xsd:string` | true | 0..1 |
| `ANO` | `xsd:string` | true | 0..1 |
| `MES_ANO` | `xsd:string` | true | 0..1 |
| `CLOSED` | `xsd:string` | true | 0..1 |
| `BORDER_STY` | `xsd:string` | true | 0..1 |
| `BORDER_COL` | `xsd:string` | true | 0..1 |
| `BORDER_WID` | `xsd:int` | true | 0..1 |
| `FILL_STYLE` | `xsd:string` | true | 0..1 |
| `PERÍMETRO` | `xsd:string` | true | 0..1 |
| `ENCLOSED_A` | `xsd:string` | true | 0..1 |
| `LAYER` | `xsd:string` | true | 0..1 |
| `TRACE_FLOW` | `xsd:string` | true | 0..1 |
| `ELEVATION` | `xsd:double` | true | 0..1 |
| `BORDER_ST1` | `xsd:string` | true | 0..1 |
| `FILL_COLOR` | `xsd:string` | true | 0..1 |
| `FILL_ALPHA` | `xsd:int` | true | 0..1 |
| `KML_STYLE` | `xsd:string` | true | 0..1 |

### `cogeo:massas_daguas_arara`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `LAYER` | `xsd:string` | true | 0..1 |
| `KML_STYLE` | `xsd:string` | true | 0..1 |
| `KML_FOLDER` | `xsd:string` | true | 0..1 |

### `cogeo:ordem_cluster`

> [!warning] Schema unresolved
> O XSD não foi resolvido nesta coleta. Reconsulte o endpoint antes de usar a camada.


### `cogeo:ordem_formas_cluster`

> [!warning] Schema unresolved
> O XSD não foi resolvido nesta coleta. Reconsulte o endpoint antes de usar a camada.


### `cogeo:ordem_uniao_cluster_geral`

> [!warning] Schema unresolved
> O XSD não foi resolvido nesta coleta. Reconsulte o endpoint antes de usar a camada.


### `cogeo:pedologia`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `id1` | `xsd:long` | true | 0..1 |
| `cd_fcim` | `xsd:string` | true | 0..1 |
| `nom_unidad` | `xsd:string` | true | 0..1 |
| `cod_simbol` | `xsd:string` | true | 0..1 |
| `val_ncompo` | `xsd:decimal` | true | 0..1 |
| `legenda` | `xsd:string` | true | 0..1 |
| `ordem` | `xsd:string` | true | 0..1 |
| `subordem` | `xsd:string` | true | 0..1 |
| `grande_gru` | `xsd:string` | true | 0..1 |
| `subgrupos` | `xsd:string` | true | 0..1 |
| `textura` | `xsd:string` | true | 0..1 |
| `horizonte` | `xsd:string` | true | 0..1 |
| `erosao` | `xsd:string` | true | 0..1 |
| `pedregosid` | `xsd:string` | true | 0..1 |
| `rochosidad` | `xsd:string` | true | 0..1 |
| `relevo` | `xsd:string` | true | 0..1 |
| `componente` | `xsd:string` | true | 0..1 |
| `component1` | `xsd:string` | true | 0..1 |
| `component2` | `xsd:string` | true | 0..1 |
| `component3` | `xsd:string` | true | 0..1 |
| `inclu_p1` | `xsd:string` | true | 0..1 |
| `inclu_p2` | `xsd:string` | true | 0..1 |
| `inclu_p3` | `xsd:string` | true | 0..1 |
| `leg_ordem` | `xsd:string` | true | 0..1 |
| `legenda_2` | `xsd:string` | true | 0..1 |
| `cd_ord_id` | `xsd:decimal` | true | 0..1 |
| `cd_leg2_id` | `xsd:decimal` | true | 0..1 |
| `geocodigo` | `xsd:string` | true | 0..1 |
| `ar_poli_km` | `xsd:decimal` | true | 0..1 |

### `cogeo:planafloro_isoietas_precipitacao`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `map_name` | `xsd:string` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `isoba_cu_` | `xsd:long` | true | 0..1 |
| `isoba_cu_i` | `xsd:long` | true | 0..1 |
| `range_code` | `xsd:long` | true | 0..1 |
| `range` | `xsd:long` | true | 0..1 |
| `symbol` | `xsd:int` | true | 0..1 |
| `closed` | `xsd:string` | true | 0..1 |
| `border_sty` | `xsd:string` | true | 0..1 |
| `border_col` | `xsd:string` | true | 0..1 |
| `border_wid` | `xsd:int` | true | 0..1 |
| `fill_style` | `xsd:string` | true | 0..1 |
| `fill_color` | `xsd:string` | true | 0..1 |

### `cogeo:reserva_legal_ro_19112024.shp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `cod_tema` | `xsd:string` | true | 0..1 |
| `nom_tema` | `xsd:string` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `num_area` | `xsd:decimal` | true | 0..1 |
| `ind_status` | `xsd:string` | true | 0..1 |
| `des_condic` | `xsd:string` | true | 0..1 |

### `cogeo:rios_bacias_arara`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `kml_style` | `xsd:string` | true | 0..1 |
| `kml_folder` | `xsd:string` | true | 0..1 |

### `cogeo:rios_e_barragens_arara`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `NAME` | `xsd:string` | true | 0..1 |
| `LAYER` | `xsd:string` | true | 0..1 |
| `KML_STYLE` | `xsd:string` | true | 0..1 |
| `KML_FOLDER` | `xsd:string` | true | 0..1 |
| `tessellate` | `xsd:int` | true | 0..1 |

### `cogeo:RO_tanques_piscic`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `area_ha` | `xsd:decimal` | true | 0..1 |
| `cd_mun` | `xsd:string` | true | 0..1 |
| `nm_mun` | `xsd:string` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `area_km2` | `xsd:decimal` | true | 0..1 |

### `cogeo:vegetacao`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `id1` | `xsd:long` | true | 0..1 |
| `cd_fcim` | `xsd:string` | true | 0..1 |
| `leg_carga` | `xsd:string` | true | 0..1 |
| `cd_fito` | `xsd:string` | true | 0..1 |
| `cd_leg_2` | `xsd:string` | true | 0..1 |
| `clas_domi` | `xsd:string` | true | 0..1 |
| `leg_uveg` | `xsd:string` | true | 0..1 |
| `nm_uveg` | `xsd:string` | true | 0..1 |
| `leg_uantr` | `xsd:string` | true | 0..1 |
| `nm_uantr` | `xsd:string` | true | 0..1 |
| `leg_contat` | `xsd:string` | true | 0..1 |
| `nm_contat` | `xsd:string` | true | 0..1 |
| `veg_pretet` | `xsd:string` | true | 0..1 |
| `nm_pretet` | `xsd:string` | true | 0..1 |
| `leg_sec1` | `xsd:string` | true | 0..1 |
| `nm_sec1` | `xsd:string` | true | 0..1 |
| `leg_sec2` | `xsd:string` | true | 0..1 |
| `nm_sec2` | `xsd:string` | true | 0..1 |
| `leg_sup` | `xsd:string` | true | 0..1 |
| `legenda_1` | `xsd:string` | true | 0..1 |
| `legenda_2` | `xsd:string` | true | 0..1 |
| `legenda` | `xsd:string` | true | 0..1 |
| `leg1_id` | `xsd:decimal` | true | 0..1 |
| `leg2_id` | `xsd:decimal` | true | 0..1 |
| `geocodigo` | `xsd:string` | true | 0..1 |
| `ar_poli_km` | `xsd:decimal` | true | 0..1 |

### `cogeo:ventos_RO`

> [!warning] Schema unresolved
> O XSD não foi resolvido nesta coleta. Reconsulte o endpoint antes de usar a camada.


### `cogeo:ventos_rondonia`

> [!warning] Schema unresolved
> O XSD não foi resolvido nesta coleta. Reconsulte o endpoint antes de usar a camada.


### `cogeo:vw_GRADES_LANDSAT`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `name` | `xsd:string` | true | 0..1 |

### `cogeo:vw_GRADES_SENTINEL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `name` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `cogeo:vw_GRADES_SPOT_100000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `dia` | `xsd:double` | true | 0..1 |
| `mês` | `xsd:double` | true | 0..1 |
| `ano` | `xsd:double` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `map_name` | `xsd:string` | true | 0..1 |
| `map_number` | `xsd:string` | true | 0..1 |

### `cogeo:vw_GRADES_SPOT_25000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `satelite` | `xsd:long` | true | 0..1 |
| `mi` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `ano` | `xsd:int` | true | 0..1 |
| `articulaca` | `xsd:string` | true | 0..1 |
| `data_passa` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `ano_passag` | `xsd:string` | true | 0..1 |
| `ativo` | `xsd:int` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `cogeo:vw_ordem_uniao_cluster_geral`

> [!warning] Schema unresolved
> O XSD não foi resolvido nesta coleta. Reconsulte o endpoint antes de usar a camada.


### `cogeo:vw_pontos_solar`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `cogeo:vw_ti_areas_protegidas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nome_usual` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `dominio` | `xsd:string` | true | 0..1 |
| `gerencia` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `area_km2` | `xsd:double` | true | 0..1 |

### `cogeo:vw_uc_estadual`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nome_usual` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `dominio` | `xsd:string` | true | 0..1 |
| `gerencia` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `area_km2` | `xsd:double` | true | 0..1 |

### `cogeo:vw_uc_municipal`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nome_usual` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `dominio` | `xsd:string` | true | 0..1 |
| `gerencia` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `area_km2` | `xsd:double` | true | 0..1 |

### `cogeo:ZSEE_2Aprox_2005_312_SIRGAS2000_4674`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `SPRAREA` | `xsd:double` | true | 0..1 |
| `SPRPERIMET` | `xsd:double` | true | 0..1 |
| `SPRROTULO` | `xsd:string` | true | 0..1 |
| `SPRNOME` | `xsd:string` | true | 0..1 |
| `SPRAREA_1` | `xsd:double` | true | 0..1 |
| `SPRPERIM_1` | `xsd:double` | true | 0..1 |
| `SPRROTUL_1` | `xsd:string` | true | 0..1 |
| `SPRNOME_1` | `xsd:string` | true | 0..1 |
| `SUBZONA` | `xsd:string` | true | 0..1 |
| `CATEGORI` | `xsd:string` | true | 0..1 |
| `CLASSE` | `xsd:string` | true | 0..1 |
| `GERENCIA` | `xsd:string` | true | 0..1 |
| `NOME1` | `xsd:string` | true | 0..1 |

## colmam (1)

### `colmam:vw_piscicultura`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `endereco` | `xsd:string` | true | 0..1 |
| `numero_lo` | `xsd:string` | false | 1..1 |
| `dt_validad` | `xsd:string` | true | 0..1 |
| `atividade` | `xsd:string` | true | 0..1 |

## comrar (36)

### `comrar:car_fitofisionomia`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `objectid` | `xsd:decimal` | true | 0..1 |
| `feature_id` | `xsd:decimal` | true | 0..1 |
| `leg_carga` | `xsd:string` | true | 0..1 |
| `leg_uveg` | `xsd:string` | true | 0..1 |
| `leg_uantr` | `xsd:string` | true | 0..1 |
| `leg_contat` | `xsd:string` | true | 0..1 |
| `veg_preter` | `xsd:string` | true | 0..1 |
| `leg_sec1` | `xsd:string` | true | 0..1 |
| `leg_sec2` | `xsd:string` | true | 0..1 |
| `leg_sec3` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |
| `shape_area` | `xsd:decimal` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `tipologia` | `xsd:string` | true | 0..1 |
| `preterito` | `xsd:string` | true | 0..1 |
| `cerrado` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `fitoecolog` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `comrar:reserva_legal_aprovada`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_registro_rl` | `xsd:string` | true | 0..1 |
| `numero_do_registro_rl` | `xsd:string` | true | 0..1 |
| `data_de_cadastro_da_rl` | `xsd:date` | true | 0..1 |
| `codigo_do_imovel` | `xsd:string` | true | 0..1 |
| `nome_do_imovel` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `area` | `xsd:decimal` | true | 0..1 |

### `comrar:reserva_legal_total`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nom_imovel` | `xsd:string` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `nom_condicao_inscricao` | `xsd:string` | true | 0..1 |
| `atualizado_em` | `xsd:date` | true | 0..1 |
| `area` | `xsd:decimal` | true | 0..1 |

### `comrar:sicar_imoveis_ac`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:string` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `status_imovel` | `xsd:string` | true | 0..1 |
| `dat_criacao` | `xsd:dateTime` | true | 0..1 |
| `data_atualizacao` | `xsd:dateTime` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `condicao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `cod_municipio_ibge` | `xsd:int` | true | 0..1 |
| `m_fiscal` | `xsd:double` | true | 0..1 |
| `tipo_imovel` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `comrar:sicar_imoveis_am`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:string` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `status_imovel` | `xsd:string` | true | 0..1 |
| `dat_criacao` | `xsd:dateTime` | true | 0..1 |
| `data_atualizacao` | `xsd:dateTime` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `condicao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `cod_municipio_ibge` | `xsd:int` | true | 0..1 |
| `m_fiscal` | `xsd:double` | true | 0..1 |
| `tipo_imovel` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `comrar:sicar_imoveis_mt`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:string` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `status_imovel` | `xsd:string` | true | 0..1 |
| `dat_criacao` | `xsd:dateTime` | true | 0..1 |
| `data_atualizacao` | `xsd:dateTime` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `condicao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `cod_municipio_ibge` | `xsd:int` | true | 0..1 |
| `m_fiscal` | `xsd:double` | true | 0..1 |
| `tipo_imovel` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `comrar:vw_car_analisado_area_consolidada`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `recibo` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:string` | true | 0..1 |
| `dt_finalizacao` | `xsd:date` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `comrar:vw_car_app_a_recuperar_aprovada`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `recibo` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:string` | true | 0..1 |
| `dt_finalizacao` | `xsd:date` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nom_condicao_inscricao` | `xsd:string` | true | 0..1 |

### `comrar:vw_car_app_a_recuperar_declarado`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `recibo` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:string` | true | 0..1 |
| `dt_finalizacao` | `xsd:date` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `comrar:vw_car_app_nascentes_olhos_dagua_perenes_declarado`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `recibo` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:string` | true | 0..1 |
| `dt_finalizacao` | `xsd:date` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nom_condicao_inscricao` | `xsd:string` | true | 0..1 |

### `comrar:vw_car_app_reservatorio_energia_ate_24_08_2001_aprovado`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `recibo` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:string` | true | 0..1 |
| `dt_finalizacao` | `xsd:date` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nom_condicao_inscricao` | `xsd:string` | true | 0..1 |

### `comrar:vw_car_app_reservatorio_energia_ate_24_08_2001_declarado`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `recibo` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:string` | true | 0..1 |
| `dt_finalizacao` | `xsd:date` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nom_condicao_inscricao` | `xsd:string` | true | 0..1 |

### `comrar:vw_car_app_segundo_art_61A_aprovado`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `recibo` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:string` | true | 0..1 |
| `dt_finalizacao` | `xsd:date` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nom_condicao_inscricao` | `xsd:string` | true | 0..1 |

### `comrar:vw_car_app_segundo_art_61A_declarada`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `recibo` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:string` | true | 0..1 |
| `dt_finalizacao` | `xsd:date` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nom_condicao_inscricao` | `xsd:string` | true | 0..1 |

### `comrar:vw_car_app_total_declarado`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `recibo` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:string` | true | 0..1 |
| `dt_finalizacao` | `xsd:date` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nom_condicao_inscricao` | `xsd:string` | true | 0..1 |

### `comrar:vw_car_aprovada_apps_lagos_lagoas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `recibo` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:string` | true | 0..1 |
| `dt_finalizacao` | `xsd:date` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nom_condicao_inscricao` | `xsd:string` | true | 0..1 |

### `comrar:vw_car_area_app_total_aprovada`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `recibo` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:string` | true | 0..1 |
| `dt_finalizacao` | `xsd:date` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nom_condicao_inscricao` | `xsd:string` | true | 0..1 |

### `comrar:vw_car_area_consolidada_aprovada`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `recibo` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:string` | true | 0..1 |
| `dt_finalizacao` | `xsd:date` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `comrar:vw_car_area_total_imovel_aprovado_publico`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `seq` | `xsd:long` | true | 0..1 |
| `idt_imovel` | `xsd:long` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `nom_imovel` | `xsd:string` | true | 0..1 |
| `num_area_imovel` | `xsd:decimal` | true | 0..1 |
| `num_modulo_fiscal` | `xsd:decimal` | true | 0..1 |
| `idt_municipio` | `xsd:int` | true | 0..1 |
| `nom_municipio` | `xsd:string` | true | 0..1 |
| `ind_status_imovel` | `xsd:string` | true | 0..1 |
| `dat_protocolo` | `xsd:string` | true | 0..1 |
| `ind_tipo_imovel` | `xsd:string` | true | 0..1 |
| `des_acesso` | `xsd:string` | true | 0..1 |
| `id_situacao` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `idt_condicao_inscricao` | `xsd:int` | true | 0..1 |
| `condicao_inscricao_imovel` | `xsd:string` | true | 0..1 |
| `cod_condicao` | `xsd:string` | true | 0..1 |
| `id_documento` | `xsd:string` | true | 0..1 |
| `nome_documento` | `xsd:string` | true | 0..1 |
| `id_tipo_documento` | `xsd:string` | true | 0..1 |
| `tipo_documento` | `xsd:string` | true | 0..1 |
| `tipo_classificacao` | `xsd:string` | true | 0..1 |
| `nome_classificacao` | `xsd:string` | true | 0..1 |
| `des_condicao` | `xsd:string` | true | 0..1 |
| `condicao_analise` | `xsd:string` | true | 0..1 |
| `data_criacao` | `xsd:dateTime` | true | 0..1 |
| `data_atualizacao` | `xsd:dateTime` | true | 0..1 |
| `qtd_retificacoes` | `xsd:int` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `area_uc_fed_ha` | `xsd:decimal` | true | 0..1 |
| `perc_uc_fed` | `xsd:decimal` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `area_uc_est_ha` | `xsd:decimal` | true | 0..1 |
| `perc_uc_est` | `xsd:decimal` | true | 0..1 |
| `nom_uc_mun` | `xsd:string` | true | 0..1 |
| `area_uc_mun_ha` | `xsd:decimal` | true | 0..1 |
| `perc_uc_mun` | `xsd:decimal` | true | 0..1 |
| `nome_terraindigena` | `xsd:string` | true | 0..1 |
| `area_ti_ha` | `xsd:decimal` | true | 0..1 |
| `perc_ti` | `xsd:decimal` | true | 0..1 |
| `area_com_restricao` | `xsd:string` | true | 0..1 |
| `data_notificacao` | `xsd:date` | true | 0..1 |
| `situacao_area_protegida` | `xsd:string` | true | 0..1 |
| `nome_area_quilombola` | `xsd:string` | true | 0..1 |
| `area_quilombola_ha` | `xsd:decimal` | true | 0..1 |
| `perc_quilombola` | `xsd:decimal` | true | 0..1 |
| `cod_sipra_assent_nc` | `xsd:string` | true | 0..1 |
| `area_assent_nc_ha` | `xsd:decimal` | true | 0..1 |
| `perc_assent_nc` | `xsd:decimal` | true | 0..1 |
| `nome_usina_sae` | `xsd:string` | true | 0..1 |
| `area_usina_sae_ha` | `xsd:decimal` | true | 0..1 |
| `perc_usina_sae` | `xsd:decimal` | true | 0..1 |
| `tem_sobreposicao_car` | `xsd:string` | true | 0..1 |
| `eh_interestadual` | `xsd:string` | true | 0..1 |
| `nm_distrit_distrital` | `xsd:string` | true | 0..1 |
| `nm_municip_distrital` | `xsd:string` | true | 0..1 |
| `area_distrital_ha` | `xsd:decimal` | true | 0..1 |
| `perc_distrital` | `xsd:decimal` | true | 0..1 |

### `comrar:vw_car_area_total_imovel_declarada_publico`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `seq` | `xsd:long` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `nom_imovel` | `xsd:string` | true | 0..1 |
| `num_area_imovel` | `xsd:decimal` | true | 0..1 |
| `num_modulo_fiscal` | `xsd:decimal` | true | 0..1 |
| `idt_municipio` | `xsd:int` | true | 0..1 |
| `nom_municipio` | `xsd:string` | true | 0..1 |
| `ind_status_imovel` | `xsd:string` | true | 0..1 |
| `dat_protocolo` | `xsd:string` | true | 0..1 |
| `ind_tipo_imovel` | `xsd:string` | true | 0..1 |
| `des_acesso` | `xsd:string` | true | 0..1 |
| `id_situacao` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `idt_condicao_inscricao` | `xsd:int` | true | 0..1 |
| `condicao_inscricao_imovel` | `xsd:string` | true | 0..1 |
| `cod_condicao` | `xsd:string` | true | 0..1 |
| `id_documento` | `xsd:string` | true | 0..1 |
| `nome_documento` | `xsd:string` | true | 0..1 |
| `id_tipo_documento` | `xsd:string` | true | 0..1 |
| `tipo_documento` | `xsd:string` | true | 0..1 |
| `tipo_classificacao` | `xsd:string` | true | 0..1 |
| `nome_classificacao` | `xsd:string` | true | 0..1 |
| `des_condicao` | `xsd:string` | true | 0..1 |
| `condicao_analise` | `xsd:string` | true | 0..1 |
| `data_criacao` | `xsd:dateTime` | true | 0..1 |
| `data_atualizacao` | `xsd:dateTime` | true | 0..1 |
| `qtd_retificacoes` | `xsd:int` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `area_uc_fed_ha` | `xsd:decimal` | true | 0..1 |
| `perc_uc_fed` | `xsd:decimal` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `area_uc_est_ha` | `xsd:decimal` | true | 0..1 |
| `perc_uc_est` | `xsd:decimal` | true | 0..1 |
| `nom_uc_mun` | `xsd:string` | true | 0..1 |
| `area_uc_mun_ha` | `xsd:decimal` | true | 0..1 |
| `perc_uc_mun` | `xsd:decimal` | true | 0..1 |
| `nome_terraindigena` | `xsd:string` | true | 0..1 |
| `area_ti_ha` | `xsd:decimal` | true | 0..1 |
| `perc_ti` | `xsd:decimal` | true | 0..1 |
| `area_com_restricao` | `xsd:string` | true | 0..1 |
| `data_notificacao` | `xsd:date` | true | 0..1 |
| `situacao_area_protegida` | `xsd:string` | true | 0..1 |
| `nome_area_quilombola` | `xsd:string` | true | 0..1 |
| `area_quilombola_ha` | `xsd:decimal` | true | 0..1 |
| `perc_quilombola` | `xsd:decimal` | true | 0..1 |
| `cod_sipra_assent_nc` | `xsd:string` | true | 0..1 |
| `area_assent_nc_ha` | `xsd:decimal` | true | 0..1 |
| `perc_assent_nc` | `xsd:decimal` | true | 0..1 |
| `nome_usina_sae` | `xsd:string` | true | 0..1 |
| `area_usina_sae_ha` | `xsd:decimal` | true | 0..1 |
| `perc_usina_sae` | `xsd:decimal` | true | 0..1 |
| `tem_sobreposicao_car` | `xsd:string` | true | 0..1 |
| `eh_interestadual` | `xsd:string` | true | 0..1 |
| `nm_distrit_distrital` | `xsd:string` | true | 0..1 |
| `nm_municip_distrital` | `xsd:string` | true | 0..1 |
| `area_distrital_ha` | `xsd:decimal` | true | 0..1 |
| `perc_distrital` | `xsd:decimal` | true | 0..1 |

### `comrar:vw_car_declarada_apps_lagos_lagoas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `recibo` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:string` | true | 0..1 |
| `dt_finalizacao` | `xsd:date` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nom_condicao_inscricao` | `xsd:string` | true | 0..1 |

### `comrar:vw_car_hidrografia_aprovada`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `recibo` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:string` | true | 0..1 |
| `dt_finalizacao` | `xsd:date` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nom_condicao_inscricao` | `xsd:string` | true | 0..1 |

### `comrar:vw_car_hidrografia_aprovada_cursos_dagua`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `recibo` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:string` | true | 0..1 |
| `dt_finalizacao` | `xsd:date` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nom_condicao_inscricao` | `xsd:string` | true | 0..1 |

### `comrar:vw_car_hidrografia_aprovada_lagos_lagoas_naturais`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `recibo` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:string` | true | 0..1 |
| `dt_finalizacao` | `xsd:date` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nom_condicao_inscricao` | `xsd:string` | true | 0..1 |

### `comrar:vw_car_hidrografia_aprovada_reservatorio_artificial_decorrente_barramentos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `recibo` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:string` | true | 0..1 |
| `dt_finalizacao` | `xsd:date` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nom_condicao_inscricao` | `xsd:string` | true | 0..1 |

### `comrar:vw_car_hidrografia_declarada`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `recibo` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:string` | true | 0..1 |
| `dt_finalizacao` | `xsd:date` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nom_condicao_inscricao` | `xsd:string` | true | 0..1 |

### `comrar:vw_car_hidrografia_declarada_cursos_dagua`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `recibo` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:string` | true | 0..1 |
| `dt_finalizacao` | `xsd:date` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nom_condicao_inscricao` | `xsd:string` | true | 0..1 |

### `comrar:vw_car_hidrografia_declarada_lagos_lagoas_naturais`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `recibo` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:string` | true | 0..1 |
| `dt_finalizacao` | `xsd:date` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nom_condicao_inscricao` | `xsd:string` | true | 0..1 |

### `comrar:vw_car_hidrografia_declarada_reservatorio_artificial_decorrente_barramentos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `recibo` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:string` | true | 0..1 |
| `dt_finalizacao` | `xsd:date` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nom_condicao_inscricao` | `xsd:string` | true | 0..1 |

### `comrar:vw_car_remanescente_de_vegetacao_nativa`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `recibo` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:string` | true | 0..1 |
| `dt_finalizacao` | `xsd:date` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nom_condicao_inscricao` | `xsd:string` | true | 0..1 |

### `comrar:vw_car_remanescente_de_vegetacao_nativa_aprovada`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `recibo` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:string` | true | 0..1 |
| `dt_finalizacao` | `xsd:date` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `comrar:vw_car_servidao_administrativa_aprovada`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `recibo` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:string` | true | 0..1 |
| `dt_finalizacao` | `xsd:date` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `comrar:vw_car_servidao_administrativa_declarada`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `recibo` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:string` | true | 0..1 |
| `dt_finalizacao` | `xsd:date` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `comrar:vw_car_servidao_ambiental_aprovada`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `recibo` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:string` | true | 0..1 |
| `dt_finalizacao` | `xsd:date` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `comrar:vw_car_servidao_ambiental_declarada`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `recibo` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:string` | true | 0..1 |
| `dt_finalizacao` | `xsd:date` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `comrar:vw_comrar_passivo_ambiental`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:decimal` | true | 0..1 |
| `nom_municipio` | `xsd:string` | true | 0..1 |
| `cod_controle` | `xsd:string` | true | 0..1 |
| `dt_emissao` | `xsd:date` | true | 0..1 |
| `dt_finalizacao` | `xsd:date` | true | 0..1 |
| `nm_tipo_area_regularidade_imovel` | `xsd:string` | true | 0..1 |
| `nm_tema_analise` | `xsd:string` | true | 0..1 |
| `des_condicao` | `xsd:string` | true | 0..1 |
| `num_area_passivo` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `ordem` | `xsd:decimal` | true | 0..1 |

## copam (3)

### `copam:embargos_ativos_mv_public`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `id` | `xsd:string` | true | 0..1 |
| `origem` | `xsd:string` | true | 0..1 |
| `id_cadast` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `data` | `xsd:string` | true | 0..1 |
| `coord_pree` | `xsd:string` | true | 0..1 |
| `num_aut` | `xsd:string` | true | 0..1 |
| `num_embarg` | `xsd:string` | true | 0..1 |
| `coord_centro` | `xsd:string` | true | 0..1 |
| `coord_1` | `xsd:string` | true | 0..1 |
| `id_sedam` | `xsd:string` | true | 0..1 |
| `coord_2` | `xsd:string` | true | 0..1 |
| `coord_3` | `xsd:string` | true | 0..1 |
| `coord_4` | `xsd:string` | true | 0..1 |
| `enqua_boa` | `xsd:string` | true | 0..1 |
| `num_bo_boa` | `xsd:string` | true | 0..1 |
| `enquad_aut` | `xsd:string` | true | 0..1 |
| `car` | `xsd:string` | true | 0..1 |
| `link` | `xsd:string` | true | 0..1 |
| `valor_da_multa` | `xsd:string` | true | 0..1 |
| `id_bpa` | `xsd:string` | true | 0..1 |
| `proc_sei` | `xsd:string` | true | 0..1 |
| `assunto` | `xsd:string` | true | 0..1 |
| `ano` | `xsd:int` | true | 0..1 |
| `data_inser` | `xsd:date` | true | 0..1 |
| `tipo_embar` | `xsd:string` | true | 0..1 |
| `descric` | `xsd:string` | true | 0..1 |
| `descric1` | `xsd:string` | true | 0..1 |
| `termo_emba` | `xsd:string` | true | 0..1 |
| `embargo_tipo` | `xsd:string` | true | 0..1 |

### `copam:vw_area_copam_autuadas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |

### `copam:vw_desembargos_sedam`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `tipo_embar` | `xsd:string` | true | 0..1 |
| `ano` | `xsd:int` | true | 0..1 |
| `coord_cent` | `xsd:string` | true | 0..1 |
| `municip` | `xsd:string` | true | 0..1 |

## coreh (17)

### `coreh:bacias_ro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `fid` | `xsd:long` | true | 0..1 |
| `id_bacia_h` | `xsd:long` | true | 0..1 |
| `codigo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `grandeza` | `xsd:string` | true | 0..1 |
| `area_decla` | `xsd:double` | true | 0..1 |
| `area_calcu` | `xsd:double` | true | 0..1 |

### `coreh:comite_bacias`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `uhe_nome` | `xsd:string` | true | 0..1 |
| `cbh_anoref` | `xsd:long` | true | 0..1 |
| `uf_sigla` | `xsd:string` | true | 0..1 |
| `uf_areakm2` | `xsd:decimal` | true | 0..1 |
| `uf_pop` | `xsd:decimal` | true | 0..1 |
| `cbh_popurb` | `xsd:long` | true | 0..1 |
| `cbh_poprur` | `xsd:long` | true | 0..1 |
| `cbh_poptot` | `xsd:long` | true | 0..1 |
| `cbh_pibagr` | `xsd:decimal` | true | 0..1 |
| `cbh_pibind` | `xsd:decimal` | true | 0..1 |
| `cbh_pibser` | `xsd:decimal` | true | 0..1 |
| `cbh_pibadm` | `xsd:decimal` | true | 0..1 |
| `cbh_pibimp` | `xsd:decimal` | true | 0..1 |
| `cbh_pibhab` | `xsd:decimal` | true | 0..1 |
| `cbh_pibtot` | `xsd:decimal` | true | 0..1 |
| `cbh_pibpop` | `xsd:decimal` | true | 0..1 |
| `cbh_pibp_1` | `xsd:decimal` | true | 0..1 |
| `cbh_agncag` | `xsd:string` | true | 0..1 |
| `cbh_idh` | `xsd:decimal` | true | 0..1 |
| `cbh_riopri` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |
| `shape_area` | `xsd:decimal` | true | 0..1 |

### `coreh:CURSO_DE_AGUA_1_100000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id_curso_d` | `xsd:decimal` | true | 0..1 |
| `codigo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `regime` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:decimal` | true | 0..1 |
| `origem` | `xsd:string` | true | 0..1 |
| `data` | `xsd:string` | true | 0..1 |
| `projeto` | `xsd:string` | true | 0..1 |
| `info` | `xsd:string` | true | 0..1 |
| `controle` | `xsd:string` | true | 0..1 |
| `geometry2_` | `xsd:string` | true | 0..1 |

### `coreh:hidrografia_fbds_ro_25082025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `idrio` | `xsd:long` | true | 0..1 |
| `rio_nome` | `xsd:string` | true | 0..1 |
| `dist_m` | `xsd:decimal` | true | 0..1 |
| `dist_km` | `xsd:decimal` | true | 0..1 |
| `nm_bacia` | `xsd:string` | true | 0..1 |
| `temtoponim` | `xsd:string` | true | 0..1 |
| `nextdown` | `xsd:long` | true | 0..1 |

### `coreh:micro_bacias_ro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `gm_type` | `xsd:string` | true | 0..1 |
| `map_name` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `closed` | `xsd:string` | true | 0..1 |
| `border_sty` | `xsd:string` | true | 0..1 |
| `border_col` | `xsd:string` | true | 0..1 |
| `border_wid` | `xsd:int` | true | 0..1 |
| `fill_style` | `xsd:string` | true | 0..1 |
| `fill_color` | `xsd:string` | true | 0..1 |
| `fill_alpha` | `xsd:int` | true | 0..1 |

### `coreh:Microbacia_Rio_Boa_Vista_Area_de_Contribuicao_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `gm_type` | `xsd:string` | true | 0..1 |
| `map_name` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `closed` | `xsd:string` | true | 0..1 |
| `border_sty` | `xsd:string` | true | 0..1 |
| `border_col` | `xsd:string` | true | 0..1 |
| `border_wid` | `xsd:int` | true | 0..1 |
| `fill_style` | `xsd:string` | true | 0..1 |
| `fill_color` | `xsd:string` | true | 0..1 |
| `fill_alpha` | `xsd:int` | true | 0..1 |
| `bacia` | `xsd:string` | true | 0..1 |
| `cod` | `xsd:long` | true | 0..1 |
| `nm_micro` | `xsd:string` | true | 0..1 |

### `coreh:Microbacia_Rio_Boa_Vista_Drenagem_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `idrio` | `xsd:long` | true | 0..1 |
| `rio_nome` | `xsd:string` | true | 0..1 |
| `dist_m` | `xsd:decimal` | true | 0..1 |
| `dist_km` | `xsd:decimal` | true | 0..1 |
| `nm_bacia` | `xsd:string` | true | 0..1 |
| `nextdown` | `xsd:long` | true | 0..1 |
| `PILOTO` | `xsd:string` | true | 0..1 |
| `ORDEM` | `xsd:long` | true | 0..1 |

### `coreh:Microbacia_Rio_Cornelio_Area_de_Contribuicao_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `gm_type` | `xsd:string` | true | 0..1 |
| `map_name` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `closed` | `xsd:string` | true | 0..1 |
| `border_sty` | `xsd:string` | true | 0..1 |
| `border_col` | `xsd:string` | true | 0..1 |
| `border_wid` | `xsd:int` | true | 0..1 |
| `fill_style` | `xsd:string` | true | 0..1 |
| `fill_color` | `xsd:string` | true | 0..1 |
| `fill_alpha` | `xsd:int` | true | 0..1 |
| `bacia` | `xsd:string` | true | 0..1 |
| `cod` | `xsd:long` | true | 0..1 |
| `nm_micro` | `xsd:string` | true | 0..1 |

### `coreh:Microbacia_Rio_Cornelio_Drenagem_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `idrio` | `xsd:long` | true | 0..1 |
| `rio_nome` | `xsd:string` | true | 0..1 |
| `dist_m` | `xsd:decimal` | true | 0..1 |
| `dist_km` | `xsd:decimal` | true | 0..1 |
| `nm_bacia` | `xsd:string` | true | 0..1 |
| `nextdown` | `xsd:long` | true | 0..1 |
| `PILOTO` | `xsd:string` | true | 0..1 |
| `ORDEM` | `xsd:long` | true | 0..1 |

### `coreh:Microbacia_Rio_Pregao_Area_de_Contribuicao_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `gm_type` | `xsd:string` | true | 0..1 |
| `map_name` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `closed` | `xsd:string` | true | 0..1 |
| `border_sty` | `xsd:string` | true | 0..1 |
| `border_col` | `xsd:string` | true | 0..1 |
| `border_wid` | `xsd:int` | true | 0..1 |
| `fill_style` | `xsd:string` | true | 0..1 |
| `fill_color` | `xsd:string` | true | 0..1 |
| `fill_alpha` | `xsd:int` | true | 0..1 |
| `bacia` | `xsd:string` | true | 0..1 |
| `cod` | `xsd:long` | true | 0..1 |
| `nm_micro` | `xsd:string` | true | 0..1 |

### `coreh:Microbacia_Rio_Pregao_Drenagem_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `idrio` | `xsd:long` | true | 0..1 |
| `rio_nome` | `xsd:string` | true | 0..1 |
| `dist_m` | `xsd:decimal` | true | 0..1 |
| `dist_km` | `xsd:decimal` | true | 0..1 |
| `nm_bacia` | `xsd:string` | true | 0..1 |
| `nextdown` | `xsd:long` | true | 0..1 |
| `PILOTO` | `xsd:string` | true | 0..1 |
| `ORDEM` | `xsd:long` | true | 0..1 |

### `coreh:Microbacia_Rio_Sao_Domingos_Area_de_Contribuicao_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `gm_type` | `xsd:string` | true | 0..1 |
| `map_name` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `closed` | `xsd:string` | true | 0..1 |
| `border_sty` | `xsd:string` | true | 0..1 |
| `border_col` | `xsd:string` | true | 0..1 |
| `border_wid` | `xsd:int` | true | 0..1 |
| `fill_style` | `xsd:string` | true | 0..1 |
| `fill_color` | `xsd:string` | true | 0..1 |
| `fill_alpha` | `xsd:int` | true | 0..1 |
| `bacia` | `xsd:string` | true | 0..1 |
| `cod` | `xsd:long` | true | 0..1 |
| `nm_micro` | `xsd:string` | true | 0..1 |

### `coreh:Microbacia_Rio_Sao_Domingos_Drenagem_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `idrio` | `xsd:long` | true | 0..1 |
| `rio_nome` | `xsd:string` | true | 0..1 |
| `dist_m` | `xsd:decimal` | true | 0..1 |
| `dist_km` | `xsd:decimal` | true | 0..1 |
| `nm_bacia` | `xsd:string` | true | 0..1 |
| `nextdown` | `xsd:long` | true | 0..1 |
| `PILOTO` | `xsd:string` | true | 0..1 |
| `ORDEM` | `xsd:long` | true | 0..1 |

### `coreh:pontos_outorga_agua_geral`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `Nº` | `xsd:long` | true | 0..1 |
| `Nome da Ba` | `xsd:string` | true | 0..1 |
| `Municipio` | `xsd:string` | true | 0..1 |
| `UF` | `xsd:string` | true | 0..1 |
| `uso` | `xsd:string` | true | 0..1 |
| `Cat_Risco` | `xsd:string` | true | 0..1 |
| `Dano_Poten` | `xsd:string` | true | 0..1 |
| `Nível_Per` | `xsd:string` | true | 0..1 |
| `Volume Hm3` | `xsd:string` | true | 0..1 |
| `Latitude` | `xsd:string` | true | 0..1 |
| `Longitude` | `xsd:string` | true | 0..1 |
| `Situação` | `xsd:string` | true | 0..1 |
| `Data_Emiss` | `xsd:string` | true | 0..1 |
| `Altura` | `xsd:double` | true | 0..1 |
| `Ano` | `xsd:int` | true | 0..1 |

### `coreh:sub_bacias_ro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `fid` | `xsd:long` | true | 0..1 |
| `id_sub_bac` | `xsd:long` | true | 0..1 |
| `codigo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `grandeza` | `xsd:string` | true | 0..1 |
| `area_decla` | `xsd:double` | true | 0..1 |
| `area_calcu` | `xsd:double` | true | 0..1 |

### `coreh:unidade_hidrografica_de_gestao`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `fid` | `xsd:long` | true | 0..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `id_bacia_h` | `xsd:double` | true | 0..1 |
| `codigo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `grandeza` | `xsd:string` | true | 0..1 |
| `area_decla` | `xsd:double` | true | 0..1 |
| `area_calcu` | `xsd:double` | true | 0..1 |
| `escala` | `xsd:double` | true | 0..1 |
| `origem` | `xsd:string` | true | 0..1 |
| `data` | `xsd:date` | true | 0..1 |
| `projeto` | `xsd:string` | true | 0..1 |
| `info` | `xsd:string` | true | 0..1 |
| `controle` | `xsd:string` | true | 0..1 |
| `geometry1_` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `cod_uhg` | `xsd:string` | true | 0..1 |
| `total_2016` | `xsd:double` | true | 0..1 |
| `total_2021` | `xsd:double` | true | 0..1 |
| `total_2026` | `xsd:double` | true | 0..1 |
| `total_2036` | `xsd:double` | true | 0..1 |

### `coreh:vw_pontos_outorgas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `id` | `xsd:int` | false | 1..1 |
| `INT_CD_CNARH40` | `xsd:string` | true | 0..1 |
| `INT_TIN_DS` | `xsd:string` | true | 0..1 |
| `INT_TIN_CD` | `xsd:string` | true | 0..1 |
| `INT_TSU_DS` | `xsd:string` | true | 0..1 |
| `INT_TSU_CD` | `xsd:string` | true | 0..1 |
| `INT_TCH_CD` | `xsd:string` | true | 0..1 |
| `INT_TCH_DS` | `xsd:string` | true | 0..1 |
| `INT_TSI_DS` | `xsd:string` | true | 0..1 |
| `INT_TSI_CD` | `xsd:string` | true | 0..1 |
| `INT_TOD_DS` | `xsd:string` | true | 0..1 |
| `INT_TDM_DS` | `xsd:string` | true | 0..1 |
| `INT_NU_CNARH` | `xsd:string` | true | 0..1 |
| `INT_NU_SIAGAS` | `xsd:string` | true | 0..1 |
| `INT_NU_LATITUDE` | `xsd:string` | true | 0..1 |
| `INT_NU_LONGITUDE` | `xsd:string` | true | 0..1 |
| `ING_NU_IBGEMUNICIPIO` | `xsd:string` | true | 0..1 |
| `ING_SG_UFMUNICIPIO` | `xsd:string` | true | 0..1 |
| `ING_NM_MUNICIPIO` | `xsd:string` | true | 0..1 |
| `INT_NM_CORPOHIDRICO` | `xsd:string` | true | 0..1 |
| `INT_NM_CORPOHIDRICOALTERADO` | `xsd:string` | true | 0..1 |
| `INT_DS_ORGAO` | `xsd:string` | true | 0..1 |
| `INT_DT_REGISTRO` | `xsd:string` | true | 0..1 |

## cprm (26)

### `cprm:Area`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `CD_UF` | `xsd:string` | true | 0..1 |
| `NM_UF` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `NM_REGIAO` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cprm:bacias_hidrograficas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `UHE_NM` | `xsd:string` | true | 0..1 |
| `UHE_AN_REF` | `xsd:int` | true | 0..1 |
| `UHE_FONTE` | `xsd:string` | true | 0..1 |
| `UHE_NM_RHI` | `xsd:string` | true | 0..1 |
| `UF` | `xsd:string` | true | 0..1 |
| `Area` | `xsd:double` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cprm:candeias_risco`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `munic` | `xsd:string` | true | 0..1 |
| `local` | `xsd:string` | true | 0..1 |
| `data_setor` | `xsd:date` | true | 0..1 |
| `num_setor` | `xsd:string` | true | 0..1 |
| `tipolo_g1` | `xsd:string` | true | 0..1 |
| `tipolo_e1` | `xsd:string` | true | 0..1 |
| `cobrade_01` | `xsd:string` | true | 0..1 |
| `tipolo_g2` | `xsd:string` | true | 0..1 |
| `tipolo_e2` | `xsd:string` | true | 0..1 |
| `cobrade_02` | `xsd:string` | true | 0..1 |
| `tipolo_g3` | `xsd:string` | true | 0..1 |
| `tipolo_e3` | `xsd:string` | true | 0..1 |
| `cobrade_03` | `xsd:string` | true | 0..1 |
| `tipolo_g4` | `xsd:string` | true | 0..1 |
| `tipolo_e4` | `xsd:string` | true | 0..1 |
| `cobrade_04` | `xsd:string` | true | 0..1 |
| `tipolo_g5` | `xsd:string` | true | 0..1 |
| `tipolo_e5` | `xsd:string` | true | 0..1 |
| `cobrade_05` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `descricao` | `xsd:string` | true | 0..1 |
| `num_edif` | `xsd:double` | true | 0..1 |
| `num_pess` | `xsd:double` | true | 0..1 |
| `obs_ocup` | `xsd:string` | true | 0..1 |
| `grau_vulne` | `xsd:string` | true | 0..1 |
| `grau_risco` | `xsd:string` | true | 0..1 |
| `sug_interv` | `xsd:string` | true | 0..1 |
| `orgao_exec` | `xsd:string` | true | 0..1 |
| `projeto` | `xsd:string` | true | 0..1 |
| `utme` | `xsd:double` | true | 0..1 |
| `utmn` | `xsd:double` | true | 0..1 |
| `zona` | `xsd:string` | true | 0..1 |

### `cprm:Capacidade_de_Infiltracao_dos_Solos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `CAP_INF` | `xsd:string` | true | 0..1 |
| `infiltraca` | `xsd:string` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cprm:Capital`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `OBJECTID_1` | `xsd:long` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `ID_MANCHA_` | `xsd:double` | true | 0..1 |
| `CODIGO` | `xsd:string` | true | 0..1 |
| `LOCALIDADE` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `AREA_CALCU` | `xsd:string` | true | 0..1 |
| `ESCALA` | `xsd:double` | true | 0..1 |
| `ORIGEM` | `xsd:string` | true | 0..1 |
| `DATA` | `xsd:date` | true | 0..1 |
| `PROJETO` | `xsd:string` | true | 0..1 |
| `INFO` | `xsd:string` | true | 0..1 |
| `CONTROLE` | `xsd:string` | true | 0..1 |
| `GEOMETRY1_` | `xsd:string` | true | 0..1 |
| `USO` | `xsd:string` | true | 0..1 |
| `ORIG_FID` | `xsd:long` | true | 0..1 |

### `cprm:Cidade`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `ID_MANCHA_` | `xsd:double` | true | 0..1 |
| `CODIGO` | `xsd:string` | true | 0..1 |
| `LOCALIDADE` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `AREA_CALCU` | `xsd:string` | true | 0..1 |
| `ESCALA` | `xsd:double` | true | 0..1 |
| `ORIGEM` | `xsd:string` | true | 0..1 |
| `DATA` | `xsd:date` | true | 0..1 |
| `PROJETO` | `xsd:string` | true | 0..1 |
| `INFO` | `xsd:string` | true | 0..1 |
| `CONTROLE` | `xsd:string` | true | 0..1 |
| `GEOMETRY1_` | `xsd:string` | true | 0..1 |
| `USO` | `xsd:string` | true | 0..1 |
| `ORIG_FID` | `xsd:long` | true | 0..1 |

### `cprm:Classe_de_Relevo`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `OBJECTID_1` | `xsd:long` | true | 0..1 |
| `Relevo` | `xsd:string` | true | 0..1 |
| `Relevo_2` | `xsd:string` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cprm:Compartimentação_de_Relevo`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `OBJECTID_1` | `xsd:long` | true | 0..1 |
| `compartime` | `xsd:string` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cprm:Curso_de_Agua`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `GEOMETRIAA` | `xsd:string` | true | 0..1 |
| `TIPOTRECHO` | `xsd:string` | true | 0..1 |
| `NAVEGAVEL` | `xsd:string` | true | 0..1 |
| `LARGURAMED` | `xsd:double` | true | 0..1 |
| `REGIME` | `xsd:string` | true | 0..1 |
| `ENCOBERTO` | `xsd:string` | true | 0..1 |
| `USO` | `xsd:string` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |

### `cprm:Densidade_de_Pocos_Cadastrados`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `OBJECTID_1` | `xsd:long` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |
| `Sum` | `xsd:long` | true | 0..1 |

### `cprm:Dominio_Hidrolitologico`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |
| `D_HL_AFL` | `xsd:string` | true | 0..1 |

### `cprm:Estimativa_Volumes_Anuais_Explotados`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `OBJECTID_1` | `xsd:long` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |
| `Vol_An_m3` | `xsd:string` | true | 0..1 |

### `cprm:Hidrogeologia`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `SIGLA_UNID` | `xsd:string` | true | 0..1 |
| `NOME_UNIDA` | `xsd:string` | true | 0..1 |
| `LITOTIPO1` | `xsd:string` | true | 0..1 |
| `LITOTIPO2` | `xsd:string` | true | 0..1 |
| `SGL_UE_AFL` | `xsd:string` | true | 0..1 |
| `SGL_UE_SUB` | `xsd:string` | true | 0..1 |
| `NOM_UE_AFL` | `xsd:string` | true | 0..1 |
| `NOM_UE_SUB` | `xsd:string` | true | 0..1 |
| `L_UE_AFL` | `xsd:string` | true | 0..1 |
| `L_UE_SUB` | `xsd:string` | true | 0..1 |
| `E_UE_AFL` | `xsd:string` | true | 0..1 |
| `E_UE_SUB` | `xsd:string` | true | 0..1 |
| `U_HL_AFL` | `xsd:string` | true | 0..1 |
| `U_HL_SUB` | `xsd:string` | true | 0..1 |
| `E_INT` | `xsd:string` | true | 0..1 |
| `GRAU_FRAT` | `xsd:string` | true | 0..1 |
| `Q_HE_AFL` | `xsd:string` | true | 0..1 |
| `Q_HE_SUB` | `xsd:string` | true | 0..1 |
| `Qs_HE_AFL` | `xsd:string` | true | 0..1 |
| `Qs_HE_SUB` | `xsd:string` | true | 0..1 |
| `T_HE_AFL` | `xsd:string` | true | 0..1 |
| `T_HE_SUB` | `xsd:string` | true | 0..1 |
| `K_HE_AFL` | `xsd:string` | true | 0..1 |
| `K_HE_SUB` | `xsd:string` | true | 0..1 |
| `PE_HE_AFL` | `xsd:string` | true | 0..1 |
| `PE_HE_SUB` | `xsd:string` | true | 0..1 |
| `S_HE_SUB` | `xsd:string` | true | 0..1 |
| `PROD_HE_AF` | `xsd:string` | true | 0..1 |
| `PROD_HE_SU` | `xsd:string` | true | 0..1 |
| `CS_HE_AFL` | `xsd:string` | true | 0..1 |
| `CS_HE_SUB` | `xsd:string` | true | 0..1 |
| `U_HE_AFL` | `xsd:string` | true | 0..1 |
| `U_HE_SUB` | `xsd:string` | true | 0..1 |
| `ESTRAT` | `xsd:string` | true | 0..1 |
| `REPR_MAP` | `xsd:string` | true | 0..1 |
| `CLS_STYLE` | `xsd:string` | true | 0..1 |
| `ROTULO` | `xsd:string` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cprm:Hidrogeologia_Contato`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |

### `cprm:Isoietas_PMA_1977_2006`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `OBJECTID_1` | `xsd:long` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `ID` | `xsd:long` | true | 0..1 |
| `CONTOUR` | `xsd:double` | true | 0..1 |
| `OBS` | `xsd:long` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Shape_Le_1` | `xsd:double` | true | 0..1 |

### `cprm:Limite_Interestadual`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |

### `cprm:Limite_Internacional`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |

### `cprm:Massa_de_Agua`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `CODIGO` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `REGIME` | `xsd:string` | true | 0..1 |
| `ESCALA` | `xsd:double` | true | 0..1 |
| `ORIGEM` | `xsd:string` | true | 0..1 |
| `DATA` | `xsd:date` | true | 0..1 |
| `PROJETO` | `xsd:string` | true | 0..1 |
| `INFO` | `xsd:string` | true | 0..1 |
| `CONTROLE` | `xsd:string` | true | 0..1 |
| `GEOMETRY2_` | `xsd:string` | true | 0..1 |
| `LABEL` | `xsd:string` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `cprm:Massa_de_Agua_outline`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `OBJECTID_1` | `xsd:long` | true | 0..1 |
| `FID_Export` | `xsd:long` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `CODIGO` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `REGIME` | `xsd:string` | true | 0..1 |
| `ESCALA` | `xsd:double` | true | 0..1 |
| `ORIGEM` | `xsd:string` | true | 0..1 |
| `DATA` | `xsd:date` | true | 0..1 |
| `PROJETO` | `xsd:string` | true | 0..1 |
| `INFO` | `xsd:string` | true | 0..1 |
| `CONTROLE` | `xsd:string` | true | 0..1 |
| `GEOMETRY2_` | `xsd:string` | true | 0..1 |
| `LABEL` | `xsd:string` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Shape_Le_1` | `xsd:double` | true | 0..1 |

### `cprm:Pocos_representativos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `SIAGAS` | `xsd:double` | true | 0..1 |
| `UF` | `xsd:string` | true | 0..1 |
| `MUNICIPIO` | `xsd:string` | true | 0..1 |
| `LAT` | `xsd:double` | true | 0..1 |
| `LOG` | `xsd:double` | true | 0..1 |
| `AQUIF_CAP` | `xsd:string` | true | 0..1 |
| `SIGLA` | `xsd:string` | true | 0..1 |
| `ESP_AQUIF_` | `xsd:double` | true | 0..1 |
| `Q_m3_h` | `xsd:double` | true | 0..1 |
| `q_m3_h_m` | `xsd:double` | true | 0..1 |
| `NE_m` | `xsd:double` | true | 0..1 |
| `ND_m` | `xsd:double` | true | 0..1 |
| `PROF_m` | `xsd:double` | true | 0..1 |
| `T_m2_s` | `xsd:string` | true | 0..1 |
| `K_m_s` | `xsd:string` | true | 0..1 |
| `CE_µS_cm` | `xsd:double` | true | 0..1 |
| `HE_REPR` | `xsd:string` | true | 0..1 |
| `ROTULO` | `xsd:string` | true | 0..1 |

### `cprm:Pocos_rimas_siagas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `ponto` | `xsd:long` | true | 0..1 |
| `localizaca` | `xsd:string` | true | 0..1 |
| `data_insta` | `xsd:string` | true | 0..1 |
| `cota_terre` | `xsd:double` | true | 0..1 |
| `latitude` | `xsd:string` | true | 0..1 |
| `longitude` | `xsd:long` | true | 0..1 |
| `latitude_d` | `xsd:double` | true | 0..1 |
| `longitude_` | `xsd:double` | true | 0..1 |
| `utme` | `xsd:double` | true | 0..1 |
| `utmn` | `xsd:double` | true | 0..1 |
| `bacia` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `natureza` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `subbacia` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `uso_agua` | `xsd:string` | true | 0..1 |
| `data_perfu` | `xsd:string` | true | 0..1 |
| `metodo_per` | `xsd:string` | true | 0..1 |
| `perfurador` | `xsd:string` | true | 0..1 |
| `diametro_b` | `xsd:string` | true | 0..1 |
| `topo` | `xsd:double` | true | 0..1 |
| `base` | `xsd:double` | true | 0..1 |
| `tipo_penet` | `xsd:string` | true | 0..1 |
| `condicao` | `xsd:string` | true | 0..1 |
| `tipo_capta` | `xsd:string` | true | 0..1 |
| `data_medic` | `xsd:string` | true | 0..1 |
| `nivel_agua` | `xsd:string` | true | 0..1 |
| `vazao` | `xsd:string` | true | 0..1 |
| `nivel_bomb` | `xsd:string` | true | 0..1 |
| `profundida` | `xsd:string` | true | 0..1 |
| `profundi_1` | `xsd:double` | true | 0..1 |
| `tipo_forma` | `xsd:string` | true | 0..1 |
| `data_teste` | `xsd:string` | true | 0..1 |
| `tipo_teste` | `xsd:string` | true | 0..1 |
| `metodo_int` | `xsd:string` | true | 0..1 |
| `surgencia` | `xsd:string` | true | 0..1 |
| `unidade_de` | `xsd:string` | true | 0..1 |
| `nivel_dina` | `xsd:string` | true | 0..1 |
| `nivel_esta` | `xsd:double` | true | 0..1 |
| `vazao_espe` | `xsd:double` | true | 0..1 |
| `coeficient` | `xsd:string` | true | 0..1 |
| `vazao_livr` | `xsd:string` | true | 0..1 |
| `permeabili` | `xsd:string` | true | 0..1 |
| `transmissi` | `xsd:double` | true | 0..1 |
| `vazao_esta` | `xsd:double` | true | 0..1 |
| `tipo_bomba` | `xsd:string` | true | 0..1 |
| `data_anali` | `xsd:string` | true | 0..1 |
| `data_colet` | `xsd:string` | true | 0..1 |
| `cor` | `xsd:double` | true | 0..1 |
| `odor` | `xsd:string` | true | 0..1 |
| `sabor` | `xsd:string` | true | 0..1 |
| `temperatur` | `xsd:double` | true | 0..1 |
| `turbidez` | `xsd:double` | true | 0..1 |
| `solidos_se` | `xsd:string` | true | 0..1 |
| `solidos_su` | `xsd:string` | true | 0..1 |
| `aspecto_na` | `xsd:string` | true | 0..1 |
| `Uso_Simp` | `xsd:string` | true | 0..1 |
| `condutivid` | `xsd:double` | true | 0..1 |

### `cprm:Potenciometria_Parecis`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `VAL_POTENC` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `INTERVALO` | `xsd:string` | true | 0..1 |
| `LOCAL_` | `xsd:string` | true | 0..1 |
| `SERIE_H` | `xsd:string` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |

### `cprm:Rodovia`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `JURISDICAO` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `USO` | `xsd:string` | true | 0..1 |
| `REVESTIMEN` | `xsd:string` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |

### `cprm:rondonia_estrutura`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `nome_estru` | `xsd:string` | true | 0..1 |
| `ang_norte` | `xsd:int` | true | 0..1 |
| `mergulho` | `xsd:int` | true | 0..1 |
| `sentido` | `xsd:string` | true | 0..1 |
| `tipo_estru` | `xsd:string` | true | 0..1 |
| `rumo` | `xsd:string` | true | 0..1 |

### `cprm:rondonia_lito`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `cod_uni_es` | `xsd:long` | true | 0..1 |
| `sigla_unid` | `xsd:string` | true | 0..1 |
| `siglas_ant` | `xsd:string` | true | 0..1 |
| `nome_unida` | `xsd:string` | true | 0..1 |
| `hierarquia` | `xsd:string` | true | 0..1 |
| `idade_max` | `xsd:string` | true | 0..1 |
| `erro_max` | `xsd:string` | true | 0..1 |
| `eon_idad_m` | `xsd:string` | true | 0..1 |
| `era_maxima` | `xsd:string` | true | 0..1 |
| `periodo_ma` | `xsd:string` | true | 0..1 |
| `epoca_max` | `xsd:string` | true | 0..1 |
| `sistema_ge` | `xsd:string` | true | 0..1 |
| `metodo_geo` | `xsd:string` | true | 0..1 |
| `qlde_infer` | `xsd:string` | true | 0..1 |
| `idade_min` | `xsd:string` | true | 0..1 |
| `erro_min` | `xsd:string` | true | 0..1 |
| `eon_idad_1` | `xsd:string` | true | 0..1 |
| `era_minima` | `xsd:string` | true | 0..1 |
| `periodo_mi` | `xsd:string` | true | 0..1 |
| `epoca_min` | `xsd:string` | true | 0..1 |
| `sistema__1` | `xsd:string` | true | 0..1 |
| `metodo_g_1` | `xsd:string` | true | 0..1 |
| `qlde_inf_1` | `xsd:string` | true | 0..1 |
| `ambsedimen` | `xsd:string` | true | 0..1 |
| `sistsedime` | `xsd:string` | true | 0..1 |
| `tipo_depos` | `xsd:string` | true | 0..1 |
| `assoc_magm` | `xsd:string` | true | 0..1 |
| `nivel_crus` | `xsd:string` | true | 0..1 |
| `textura_ig` | `xsd:string` | true | 0..1 |
| `fonte_magm` | `xsd:string` | true | 0..1 |
| `morfologia` | `xsd:string` | true | 0..1 |
| `ambiente_t` | `xsd:string` | true | 0..1 |
| `metamorfis` | `xsd:string` | true | 0..1 |
| `metodo_g_2` | `xsd:string` | true | 0..1 |
| `temp_pico` | `xsd:long` | true | 0..1 |
| `erro_temp_` | `xsd:long` | true | 0..1 |
| `pressao_pi` | `xsd:long` | true | 0..1 |
| `erro_press` | `xsd:long` | true | 0..1 |
| `tipo_baric` | `xsd:string` | true | 0..1 |
| `trajetoria` | `xsd:string` | true | 0..1 |
| `litotipo1` | `xsd:string` | true | 0..1 |
| `litotipo2` | `xsd:string` | true | 0..1 |
| `classe_roc` | `xsd:string` | true | 0..1 |
| `classe_r_1` | `xsd:string` | true | 0..1 |
| `bb_subclas` | `xsd:string` | true | 0..1 |
| `bb_subcl_1` | `xsd:string` | true | 0..1 |

### `cprm:rondonia_recmin_mapa`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `projeto` | `xsd:string` | true | 0..1 |
| `toponimia` | `xsd:string` | true | 0..1 |
| `numero_cam` | `xsd:string` | true | 0..1 |
| `substancia` | `xsd:string` | true | 0..1 |
| `substanc_1` | `xsd:string` | true | 0..1 |
| `abrev` | `xsd:string` | true | 0..1 |
| `importanci` | `xsd:string` | true | 0..1 |
| `status_eco` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:double` | true | 0..1 |
| `long_` | `xsd:double` | true | 0..1 |
| `codigo_fol` | `xsd:string` | true | 0..1 |
| `folha` | `xsd:string` | true | 0..1 |
| `datum` | `xsd:string` | true | 0..1 |
| `metodo_geo` | `xsd:string` | true | 0..1 |
| `erro_assoc` | `xsd:string` | true | 0..1 |
| `data_alt` | `xsd:string` | true | 0..1 |
| `classes_ut` | `xsd:string` | true | 0..1 |
| `classe_gen` | `xsd:string` | true | 0..1 |
| `modelo` | `xsd:string` | true | 0..1 |
| `assoc_geoq` | `xsd:string` | true | 0..1 |
| `tipologia` | `xsd:string` | true | 0..1 |
| `rocha_enca` | `xsd:string` | true | 0..1 |
| `rocha_hosp` | `xsd:string` | true | 0..1 |
| `mineralogi` | `xsd:string` | true | 0..1 |
| `unid_rec_m` | `xsd:string` | true | 0..1 |
| `unid_rec_i` | `xsd:string` | true | 0..1 |
| `producao_h` | `xsd:string` | true | 0..1 |
| `recurso_to` | `xsd:string` | true | 0..1 |
| `textura` | `xsd:string` | true | 0..1 |
| `unidade_li` | `xsd:string` | true | 0..1 |
| `sureg` | `xsd:string` | true | 0..1 |
| `referencia` | `xsd:string` | true | 0..1 |
| `fonte_info` | `xsd:string` | true | 0..1 |
| `referenc_1` | `xsd:string` | true | 0..1 |
| `reserva_pr` | `xsd:string` | true | 0..1 |
| `unid_res_p` | `xsd:string` | true | 0..1 |
| `reserva__1` | `xsd:string` | true | 0..1 |
| `unid_res_1` | `xsd:string` | true | 0..1 |
| `morfologia` | `xsd:string` | true | 0..1 |
| `tonelagem` | `xsd:string` | true | 0..1 |
| `observacao` | `xsd:string` | true | 0..1 |
| `outras_obs` | `xsd:string` | true | 0..1 |
| `precisao` | `xsd:double` | true | 0..1 |
| `situacao_m` | `xsd:string` | true | 0..1 |
| `provincia` | `xsd:string` | true | 0..1 |
| `geologo` | `xsd:string` | true | 0..1 |
| `rese_indi` | `xsd:string` | true | 0..1 |
| `rese_infe` | `xsd:string` | true | 0..1 |
| `rese_medi` | `xsd:string` | true | 0..1 |
| `problema` | `xsd:string` | true | 0..1 |
| `tipos_alte` | `xsd:string` | true | 0..1 |
| `id_afloram` | `xsd:long` | true | 0..1 |
| `origem` | `xsd:string` | true | 0..1 |
| `data_cadas` | `xsd:date` | true | 0..1 |
| `tipo_aflor` | `xsd:string` | true | 0..1 |
| `descricao` | `xsd:string` | true | 0..1 |
| `id_ocorren` | `xsd:long` | true | 0..1 |
| `localizaca` | `xsd:string` | true | 0..1 |
| `motivo_ina` | `xsd:string` | true | 0..1 |
| `tamanho` | `xsd:string` | true | 0..1 |
| `amostrado` | `xsd:string` | true | 0..1 |
| `altitude_m` | `xsd:double` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `cobertura_` | `xsd:string` | true | 0..1 |
| `forma` | `xsd:string` | true | 0..1 |
| `int_quim_m` | `xsd:string` | true | 0..1 |
| `num_recmin` | `xsd:string` | true | 0..1 |

## cuc (3)

### `cuc:limites_ucs_estaduais`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `fid` | `xsd:decimal` | true | 0..1 |
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

### `cuc:unidades_conservacao_municipal_ro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `cd_mun` | `xsd:string` | true | 0..1 |
| `nm_mun` | `xsd:string` | true | 0..1 |
| `nome_usual` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `dominio` | `xsd:string` | true | 0..1 |
| `sigla` | `xsd:string` | true | 0..1 |
| `gerencia` | `xsd:string` | true | 0..1 |
| `area-ha` | `xsd:decimal` | true | 0..1 |
| `ato de criação` | `xsd:string` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `grupo_snuc` | `xsd:string` | true | 0..1 |
| `outros_atos_legais` | `xsd:string` | true | 0..1 |
| `codigo_cnuc` | `xsd:string` | true | 0..1 |

### `cuc:zona_amortecimento_uc_estadual`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `cd_uf` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `nm_regiao` | `xsd:string` | true | 0..1 |
| `fid` | `xsd:decimal` | true | 0..1 |
| `id_area_po` | `xsd:decimal` | true | 0..1 |
| `nome_usual` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `dominio` | `xsd:string` | true | 0..1 |
| `portaria` | `xsd:string` | true | 0..1 |
| `tamanho` | `xsd:string` | true | 0..1 |

## der (3)

### `der:estradas_nao_pavimentadas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `Name` | `xsd:string` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `FID` | `xsd:string` | true | 0..1 |
| `COBERTURA` | `xsd:string` | true | 0..1 |
| `RO` | `xsd:string` | true | 0..1 |
| `EXTENSAO` | `xsd:string` | true | 0..1 |
| `SRE` | `xsd:string` | true | 0..1 |
| `RODOVIA` | `xsd:string` | true | 0..1 |
| `EXT_INICIO` | `xsd:string` | true | 0..1 |
| `EXT_FIM` | `xsd:string` | true | 0..1 |
| `TRECHO_INI` | `xsd:string` | true | 0..1 |
| `TRECHO_FIM` | `xsd:string` | true | 0..1 |
| `MUNICIPIO` | `xsd:string` | true | 0..1 |
| `JURISDICAO` | `xsd:string` | true | 0..1 |
| `COINC_1` | `xsd:string` | true | 0..1 |
| `SUPERPOSTA` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `SRE_ANTIGO` | `xsd:string` | true | 0..1 |
| `LOTE_TP` | `xsd:string` | true | 0..1 |
| `ROD_NOVA` | `xsd:string` | true | 0..1 |
| `PISTA_DUPL` | `xsd:string` | true | 0..1 |
| `IDENT_TREC` | `xsd:string` | true | 0..1 |
| `CLAS_FUNCI` | `xsd:string` | true | 0..1 |
| `TIPO_REVES` | `xsd:string` | true | 0..1 |
| `LOTE_MAN` | `xsd:string` | true | 0..1 |
| `LOTES_RR` | `xsd:string` | true | 0..1 |

### `der:estradas_pavimentadas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `Name` | `xsd:string` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `FID` | `xsd:string` | true | 0..1 |
| `COBERTURA` | `xsd:string` | true | 0..1 |
| `RO` | `xsd:string` | true | 0..1 |
| `EXTENSAO` | `xsd:string` | true | 0..1 |
| `SRE` | `xsd:string` | true | 0..1 |
| `RODOVIA` | `xsd:string` | true | 0..1 |
| `EXT_INICIO` | `xsd:string` | true | 0..1 |
| `EXT_FIM` | `xsd:string` | true | 0..1 |
| `TRECHO_INI` | `xsd:string` | true | 0..1 |
| `TRECHO_FIM` | `xsd:string` | true | 0..1 |
| `MUNICIPIO` | `xsd:string` | true | 0..1 |
| `JURISDICAO` | `xsd:string` | true | 0..1 |
| `COINC_1` | `xsd:string` | true | 0..1 |
| `SUPERPOSTA` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `SRE_ANTIGO` | `xsd:string` | true | 0..1 |
| `LOTE_TP` | `xsd:string` | true | 0..1 |
| `ROD_NOVA` | `xsd:string` | true | 0..1 |
| `PISTA_DUPL` | `xsd:string` | true | 0..1 |
| `IDENT_TREC` | `xsd:string` | true | 0..1 |
| `CLAS_FUNCI` | `xsd:string` | true | 0..1 |
| `TIPO_REVES` | `xsd:string` | true | 0..1 |
| `LOTE_MAN` | `xsd:string` | true | 0..1 |
| `LOTES_RR` | `xsd:string` | true | 0..1 |

### `der:estradas_planejadas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `fid` | `xsd:double` | true | 0..1 |
| `Name` | `xsd:string` | true | 0..1 |
| `COBERTURA` | `xsd:string` | true | 0..1 |
| `RO` | `xsd:string` | true | 0..1 |
| `EXTENSAO` | `xsd:string` | true | 0..1 |
| `SRE` | `xsd:string` | true | 0..1 |
| `RODOVIA` | `xsd:string` | true | 0..1 |
| `EXT_INICIO` | `xsd:string` | true | 0..1 |
| `EXT_FIM` | `xsd:string` | true | 0..1 |
| `TRECHO_INI` | `xsd:string` | true | 0..1 |
| `TRECHO_FIM` | `xsd:string` | true | 0..1 |
| `MUNICIPIO` | `xsd:string` | true | 0..1 |
| `JURISDICAO` | `xsd:string` | true | 0..1 |
| `COINC_1` | `xsd:string` | true | 0..1 |
| `SUPERPOSTA` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `SRE_ANTIGO` | `xsd:string` | true | 0..1 |
| `LOTE_TP` | `xsd:string` | true | 0..1 |
| `ROD_NOVA` | `xsd:string` | true | 0..1 |
| `PISTA_DUPL` | `xsd:string` | true | 0..1 |
| `IDENT_TREC` | `xsd:string` | true | 0..1 |
| `CLAS_FUNCI` | `xsd:string` | true | 0..1 |
| `TIPO_REVES` | `xsd:string` | true | 0..1 |
| `LOTE_MAN` | `xsd:string` | true | 0..1 |
| `LOTES_RR` | `xsd:string` | true | 0..1 |

## emater (1)

### `emater:pontos_sedes_ro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `name` | `xsd:string` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `gm_type` | `xsd:string` | true | 0..1 |
| `elevation` | `xsd:int` | true | 0..1 |

## ergas (2)

### `ergas:ergas_poligonos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `descr` | `xsd:string` | true | 0..1 |

### `ergas:localizacao_ergas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `erga` | `xsd:string` | true | 0..1 |
| `gerente` | `xsd:string` | true | 0..1 |
| `endereço` | `xsd:string` | true | 0..1 |
| `contatos` | `xsd:string` | true | 0..1 |
| `instagram` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:decimal` | true | 0..1 |
| `long` | `xsd:decimal` | true | 0..1 |

## fabdem (1)

### `fabdem:fabdem_tiles_v1`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `file_name` | `xsd:string` | true | 0..1 |
| `zipfile_name_link` | `xsd:string` | true | 0..1 |
| `link` | `xsd:string` | true | 0..1 |

## fbds (8)

### `fbds:app_nascentes`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `geocodigo` | `xsd:decimal` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `cd_uf` | `xsd:decimal` | true | 0..1 |
| `hidro` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:decimal` | true | 0..1 |

### `fbds:app_rios_e_igarapes`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `geocodigo` | `xsd:decimal` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `cd_uf` | `xsd:string` | true | 0..1 |
| `hidro` | `xsd:string` | true | 0..1 |
| `app_m` | `xsd:long` | true | 0..1 |
| `area_ha` | `xsd:decimal` | true | 0..1 |

### `fbds:massas_dagua`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `geocodigo` | `xsd:decimal` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `cd_uf` | `xsd:string` | true | 0..1 |
| `hidro` | `xsd:string` | true | 0..1 |
| `natureza` | `xsd:string` | true | 0..1 |
| `rio` | `xsd:string` | true | 0..1 |
| `setor` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:decimal` | true | 0..1 |

### `fbds:nascentes`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `geocodigo` | `xsd:decimal` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `cd_uf` | `xsd:decimal` | true | 0..1 |
| `hidro` | `xsd:string` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `path` | `xsd:string` | true | 0..1 |

### `fbds:rios_duplos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `geocodigo` | `xsd:decimal` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `cd_uf` | `xsd:decimal` | true | 0..1 |
| `hidro` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:decimal` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `path` | `xsd:string` | true | 0..1 |

### `fbds:rios_e_igarapes`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `geocodigo` | `xsd:decimal` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `cd_uf` | `xsd:decimal` | true | 0..1 |
| `hidro` | `xsd:string` | true | 0..1 |
| `comp_km` | `xsd:decimal` | true | 0..1 |

### `fbds:rios_e_igarapes_bacia_rio_machado`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `fid` | `xsd:decimal` | true | 0..1 |
| `idrio` | `xsd:decimal` | true | 0..1 |
| `rio_nome` | `xsd:string` | true | 0..1 |
| `nm_bacia` | `xsd:string` | true | 0..1 |
| `temtoponim` | `xsd:string` | true | 0..1 |
| `dist_m` | `xsd:decimal` | true | 0..1 |
| `dist_km` | `xsd:decimal` | true | 0..1 |

### `fbds:uso_solo`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `geocodigo` | `xsd:decimal` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `cd_uf` | `xsd:decimal` | true | 0..1 |
| `classe_uso` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:decimal` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |

## funai (2)

### `funai:aldeias_pontos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `cod_aldeia` | `xsd:long` | true | 0..1 |
| `nome_aldeia` | `xsd:string` | true | 0..1 |
| `cod_ti` | `xsd:long` | true | 0..1 |
| `cod_municipio` | `xsd:long` | true | 0..1 |
| `data_cadastro` | `xsd:string` | true | 0..1 |
| `flag_ativo` | `xsd:string` | true | 0..1 |
| `nome_cr` | `xsd:string` | true | 0..1 |
| `nommunic` | `xsd:string` | true | 0..1 |
| `nomuf` | `xsd:string` | true | 0..1 |
| `undadm_codigo` | `xsd:double` | true | 0..1 |
| `coord_lat` | `xsd:double` | true | 0..1 |
| `coord_long` | `xsd:double` | true | 0..1 |
| `geometry` | `gml:PointPropertyType` | true | 0..1 |

### `funai:tis_poligonais`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geometry` | `gml:PolygonPropertyType` | true | 0..1 |
| `Name` | `xsd:string` | true | 0..1 |
| `description` | `xsd:string` | true | 0..1 |
| `timestamp` | `xsd:dateTime` | true | 0..1 |
| `begin` | `xsd:dateTime` | true | 0..1 |
| `end` | `xsd:dateTime` | true | 0..1 |
| `altitudeMode` | `xsd:string` | true | 0..1 |
| `tessellate` | `xsd:int` | true | 0..1 |
| `extrude` | `xsd:int` | true | 0..1 |
| `visibility` | `xsd:int` | true | 0..1 |
| `drawOrder` | `xsd:int` | true | 0..1 |
| `icon` | `xsd:string` | true | 0..1 |
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
| `undadm_codigo` | `xsd:string` | true | 0..1 |
| `undadm_nome` | `xsd:string` | true | 0..1 |
| `undadm_sigla` | `xsd:string` | true | 0..1 |
| `dominio_uniao` | `xsd:string` | true | 0..1 |
| `data_atualizacao` | `xsd:string` | true | 0..1 |
| `epsg` | `xsd:int` | true | 0..1 |

## ibama (5)

### `ibama:auto_ibama`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `objectid` | `xsd:long` | true | 0..1 |
| `rid` | `xsd:string` | true | 0..1 |
| `seq_auto_i` | `xsd:string` | true | 0..1 |
| `des_status` | `xsd:string` | true | 0..1 |
| `ds_sit_aut` | `xsd:string` | true | 0..1 |
| `sit_cancel` | `xsd:string` | true | 0..1 |
| `num_auto_i` | `xsd:string` | true | 0..1 |
| `ser_auto_i` | `xsd:string` | true | 0..1 |
| `cd_origina` | `xsd:string` | true | 0..1 |
| `tipo_auto` | `xsd:string` | true | 0..1 |
| `tipo_multa` | `xsd:string` | true | 0..1 |
| `val_auto_i` | `xsd:double` | true | 0..1 |
| `fundamenta` | `xsd:string` | true | 0..1 |
| `patrimonio` | `xsd:string` | true | 0..1 |
| `gravidade_` | `xsd:string` | true | 0..1 |
| `cd_nivel_g` | `xsd:string` | true | 0..1 |
| `motivacao_` | `xsd:string` | true | 0..1 |
| `efeito_mei` | `xsd:string` | true | 0..1 |
| `efeito_sau` | `xsd:string` | true | 0..1 |
| `passivel_r` | `xsd:string` | true | 0..1 |
| `unid_arrec` | `xsd:string` | true | 0..1 |
| `des_auto_i` | `xsd:string` | true | 0..1 |
| `dat_hora_a` | `xsd:string` | true | 0..1 |
| `forma_entr` | `xsd:string` | true | 0..1 |
| `dat_cienci` | `xsd:string` | true | 0..1 |
| `dt_fato_in` | `xsd:dateTime` | true | 0..1 |
| `dt_inicio_` | `xsd:dateTime` | true | 0..1 |
| `dt_fim_ato` | `xsd:dateTime` | true | 0..1 |
| `cod_munici` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `num_proces` | `xsd:string` | true | 0..1 |
| `cod_infrac` | `xsd:string` | true | 0..1 |
| `des_infrac` | `xsd:string` | true | 0..1 |
| `tipo_infra` | `xsd:string` | true | 0..1 |
| `des_receit` | `xsd:string` | true | 0..1 |
| `num_pessoa` | `xsd:string` | true | 0..1 |
| `nome_infra` | `xsd:string` | true | 0..1 |
| `cpf_cnpj_i` | `xsd:string` | true | 0..1 |
| `qt_area` | `xsd:double` | true | 0..1 |
| `infracao_a` | `xsd:string` | true | 0..1 |
| `des_outros` | `xsd:string` | true | 0..1 |
| `classifica` | `xsd:string` | true | 0..1 |
| `num_longit` | `xsd:double` | true | 0..1 |
| `num_latitu` | `xsd:double` | true | 0..1 |
| `des_local_` | `xsd:string` | true | 0..1 |
| `unidade_co` | `xsd:string` | true | 0..1 |
| `ds_biomas_` | `xsd:string` | true | 0..1 |
| `seq_notifi` | `xsd:string` | true | 0..1 |
| `seq_acao_f` | `xsd:string` | true | 0..1 |
| `cd_acao_fi` | `xsd:string` | true | 0..1 |
| `unid_contr` | `xsd:string` | true | 0..1 |
| `tipo_acao` | `xsd:string` | true | 0..1 |
| `operacao` | `xsd:string` | true | 0..1 |
| `denuncia_s` | `xsd:string` | true | 0..1 |
| `seq_ordem_` | `xsd:string` | true | 0..1 |
| `ordem_fisc` | `xsd:string` | true | 0..1 |
| `unid_orden` | `xsd:string` | true | 0..1 |
| `seq_solici` | `xsd:string` | true | 0..1 |
| `solicitaca` | `xsd:string` | true | 0..1 |
| `operacao_s` | `xsd:string` | true | 0..1 |
| `dt_lancame` | `xsd:dateTime` | true | 0..1 |
| `dt_ult_alt` | `xsd:dateTime` | true | 0..1 |
| `tp_ult_alt` | `xsd:string` | true | 0..1 |
| `justificat` | `xsd:string` | true | 0..1 |
| `dt_ult_a00` | `xsd:dateTime` | true | 0..1 |
| `tp_origem_` | `xsd:string` | true | 0..1 |
| `dt_atualiz` | `xsd:dateTime` | true | 0..1 |
| `geometry` | `gml:PointPropertyType` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |

### `ibama:embargos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `origem_geo` | `xsd:string` | true | 0..1 |
| `seq_tad` | `xsd:long` | true | 0..1 |
| `num_tad` | `xsd:string` | true | 0..1 |
| `serie_tad` | `xsd:string` | true | 0..1 |
| `cod_uf` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `cod_munici` | `xsd:long` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `nome_imove` | `xsd:string` | true | 0..1 |
| `des_locali` | `xsd:string` | true | 0..1 |
| `nome_embar` | `xsd:string` | true | 0..1 |
| `cpf_cnpj_e` | `xsd:string` | true | 0..1 |
| `sit_desmat` | `xsd:string` | true | 0..1 |
| `tipo_area` | `xsd:string` | true | 0..1 |
| `num_auto_i` | `xsd:string` | true | 0..1 |
| `serie_auto` | `xsd:string` | true | 0..1 |
| `cod_tipo_b` | `xsd:string` | true | 0..1 |
| `des_tipo_b` | `xsd:string` | true | 0..1 |
| `operacao` | `xsd:string` | true | 0..1 |
| `unid_contr` | `xsd:string` | true | 0..1 |
| `ordem_fisc` | `xsd:string` | true | 0..1 |
| `cd_acao_fi` | `xsd:string` | true | 0..1 |
| `num_proces` | `xsd:string` | true | 0..1 |
| `des_tad` | `xsd:string` | true | 0..1 |
| `des_infrac` | `xsd:string` | true | 0..1 |
| `num_longit` | `xsd:string` | true | 0..1 |
| `num_latitu` | `xsd:string` | true | 0..1 |
| `dat_embarg` | `xsd:dateTime` | true | 0..1 |
| `dat_impres` | `xsd:dateTime` | true | 0..1 |
| `dat_ult_al` | `xsd:dateTime` | true | 0..1 |
| `num_long_1` | `xsd:double` | true | 0..1 |
| `num_lati_1` | `xsd:double` | true | 0..1 |
| `qtd_area_d` | `xsd:double` | true | 0..1 |
| `qtd_area_e` | `xsd:double` | true | 0..1 |
| `dat_ult__1` | `xsd:dateTime` | true | 0..1 |
| `st_area_sh` | `xsd:double` | true | 0..1 |
| `st_perimet` | `xsd:double` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `nome_uf` | `xsd:string` | true | 0..1 |
| `nome_regiao` | `xsd:string` | true | 0..1 |
| `nome_pais` | `xsd:string` | true | 0..1 |

### `ibama:sinaflor_proj_externo`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `GmlID` | `xsd:string` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `objectid_origem` | `xsd:int` | true | 0..1 |
| `origem` | `xsd:string` | true | 0..1 |
| `nu_recibo` | `xsd:string` | true | 0..1 |
| `nu_autorizacao` | `xsd:string` | true | 0..1 |
| `tipo_emp` | `xsd:string` | true | 0..1 |
| `nm_orgao` | `xsd:string` | true | 0..1 |
| `nm_empreendimento` | `xsd:string` | true | 0..1 |
| `nu_art` | `xsd:string` | true | 0..1 |
| `tipo_atividade` | `xsd:string` | true | 0..1 |
| `nm_detentor` | `xsd:string` | true | 0..1 |
| `nu_cpf_cnpj` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `dt_valid_inicio` | `xsd:string` | true | 0..1 |
| `dt_valid_fim` | `xsd:string` | true | 0..1 |
| `status_autorizacao` | `xsd:string` | true | 0..1 |
| `nu_car_imovel` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `area_pamgia_ha` | `xsd:double` | true | 0..1 |
| `bioma_pamgia` | `xsd:string` | true | 0..1 |
| `nm_uc_fed` | `xsd:string` | true | 0..1 |
| `presen_uc_fed` | `xsd:string` | true | 0..1 |
| `nm_uc_est` | `xsd:string` | true | 0..1 |
| `presen_uc_est` | `xsd:string` | true | 0..1 |
| `nm_ti` | `xsd:string` | true | 0..1 |
| `presen_ti` | `xsd:string` | true | 0..1 |
| `geom` | `xsd:string` | true | 0..1 |
| `dt_atualizacao` | `xsd:string` | true | 0..1 |
| `st_area_shape_` | `xsd:double` | true | 0..1 |
| `st_perimeter_shape_` | `xsd:double` | true | 0..1 |
| `geometry` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `nome_uf` | `xsd:string` | true | 0..1 |
| `nome_regiao` | `xsd:string` | true | 0..1 |
| `nome_pais` | `xsd:string` | true | 0..1 |

### `ibama:vw_auto_infracao`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `municipio` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `des_auto_i` | `xsd:string` | true | 0..1 |
| `dat_hora_a` | `xsd:string` | true | 0..1 |
| `des_status` | `xsd:string` | true | 0..1 |
| `tipo_auto` | `xsd:string` | true | 0..1 |
| `motivacao_` | `xsd:string` | true | 0..1 |
| `unid_arrec` | `xsd:string` | true | 0..1 |
| `des_infrac` | `xsd:string` | true | 0..1 |
| `tipo_infra` | `xsd:string` | true | 0..1 |
| `infracao_a` | `xsd:string` | true | 0..1 |
| `classifica` | `xsd:string` | true | 0..1 |
| `unid_contr` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |

### `ibama:vw_embargo`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `uf` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `serie_auto` | `xsd:string` | true | 0..1 |
| `cod_tipo_b` | `xsd:string` | true | 0..1 |
| `des_tipo_b` | `xsd:string` | true | 0..1 |
| `unid_contr` | `xsd:string` | true | 0..1 |
| `des_tad` | `xsd:string` | true | 0..1 |
| `des_infrac` | `xsd:string` | true | 0..1 |
| `dat_embarg` | `xsd:dateTime` | true | 0..1 |
| `dat_impres` | `xsd:dateTime` | true | 0..1 |
| `dat_ult_al` | `xsd:dateTime` | true | 0..1 |
| `st_area_sh` | `xsd:double` | true | 0..1 |
| `st_perimet` | `xsd:double` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |

## ibge (85)

### `ibge:ac_municipios_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_MUN` | `xsd:string` | true | 0..1 |
| `NM_MUN` | `xsd:string` | true | 0..1 |
| `CD_RGI` | `xsd:string` | true | 0..1 |
| `NM_RGI` | `xsd:string` | true | 0..1 |
| `CD_RGINT` | `xsd:string` | true | 0..1 |
| `NM_RGINT` | `xsd:string` | true | 0..1 |
| `CD_UF` | `xsd:string` | true | 0..1 |
| `NM_UF` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `CD_REGIAO` | `xsd:string` | true | 0..1 |
| `NM_REGIAO` | `xsd:string` | true | 0..1 |
| `SIGLA_RG` | `xsd:string` | true | 0..1 |
| `CD_CONCURB` | `xsd:string` | true | 0..1 |
| `NM_CONCURB` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |

### `ibge:ac_rg_imediatas_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_RGI` | `xsd:string` | true | 0..1 |
| `NM_RGI` | `xsd:string` | true | 0..1 |
| `CD_RGINT` | `xsd:string` | true | 0..1 |
| `NM_RGINT` | `xsd:string` | true | 0..1 |
| `CD_UF` | `xsd:string` | true | 0..1 |
| `NM_UF` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `CD_REGIAO` | `xsd:string` | true | 0..1 |
| `NM_REGIAO` | `xsd:string` | true | 0..1 |
| `SIGLA_RG` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |

### `ibge:ac_rg_intermediarias_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_RGINT` | `xsd:string` | true | 0..1 |
| `NM_RGINT` | `xsd:string` | true | 0..1 |
| `CD_UF` | `xsd:string` | true | 0..1 |
| `NM_UF` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `CD_REGIAO` | `xsd:string` | true | 0..1 |
| `NM_REGIAO` | `xsd:string` | true | 0..1 |
| `SIGLA_RG` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |

### `ibge:ac_uf_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_UF` | `xsd:string` | true | 0..1 |
| `NM_UF` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `CD_REGIAO` | `xsd:string` | true | 0..1 |
| `NM_REGIAO` | `xsd:string` | true | 0..1 |
| `SIGLA_RG` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |

### `ibge:america_do_sul`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `GM_LAYER` | `xsd:string` | true | 0..1 |
| `MAP_NAME` | `xsd:string` | true | 0..1 |
| `LAYER` | `xsd:string` | true | 0..1 |
| `FIPS_CNTRY` | `xsd:string` | true | 0..1 |
| `GMI_CNTRY` | `xsd:string` | true | 0..1 |
| `ISO_2DIGIT` | `xsd:string` | true | 0..1 |
| `ISO_3DIGIT` | `xsd:string` | true | 0..1 |
| `CNTRY_NAME` | `xsd:string` | true | 0..1 |
| `LONG_NAME` | `xsd:string` | true | 0..1 |
| `SOVEREIGN` | `xsd:string` | true | 0..1 |
| `POP_CNTRY` | `xsd:int` | true | 0..1 |
| `CURR_TYPE` | `xsd:string` | true | 0..1 |
| `CURR_CODE` | `xsd:string` | true | 0..1 |
| `LANDLOCKED` | `xsd:string` | true | 0..1 |
| `SQKM` | `xsd:double` | true | 0..1 |
| `SQMI` | `xsd:double` | true | 0..1 |
| `COLOR_MAP` | `xsd:int` | true | 0..1 |
| `CLOSED` | `xsd:string` | true | 0..1 |
| `BORDER_STY` | `xsd:string` | true | 0..1 |
| `BORDER_COL` | `xsd:string` | true | 0..1 |
| `BORDER_WID` | `xsd:int` | true | 0..1 |
| `FILL_STYLE` | `xsd:string` | true | 0..1 |
| `FILL_COLOR` | `xsd:string` | true | 0..1 |

### `ibge:areas_urbanas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `GM_LAYER` | `xsd:string` | true | 0..1 |
| `GM_TYPE` | `xsd:string` | true | 0..1 |
| `LAYER` | `xsd:string` | true | 0..1 |
| `AREA` | `xsd:double` | true | 0..1 |
| `PERIMETER` | `xsd:double` | true | 0..1 |
| `MANCHA_URB` | `xsd:int` | true | 0..1 |
| `MANCHA_UR1` | `xsd:int` | true | 0..1 |
| `ID_MANCHA_` | `xsd:int` | true | 0..1 |
| `CODIGO` | `xsd:string` | true | 0..1 |
| `LOCALIDADE` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `AREA_CALCU` | `xsd:string` | true | 0..1 |
| `ESCALA` | `xsd:double` | true | 0..1 |
| `ORIGEM` | `xsd:int` | true | 0..1 |
| `DATA` | `xsd:string` | true | 0..1 |
| `PROJETO` | `xsd:int` | true | 0..1 |
| `INFO` | `xsd:int` | true | 0..1 |
| `CONTROLE` | `xsd:int` | true | 0..1 |
| `GEOMETRY1_` | `xsd:string` | true | 0..1 |

### `ibge:bairros_br_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `cd_regiao` | `xsd:string` | true | 0..1 |
| `nm_regiao` | `xsd:string` | true | 0..1 |
| `cd_uf` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `cd_mun` | `xsd:string` | true | 0..1 |
| `nm_mun` | `xsd:string` | true | 0..1 |
| `cd_dist` | `xsd:string` | true | 0..1 |
| `nm_dist` | `xsd:string` | true | 0..1 |
| `cd_subdist` | `xsd:string` | true | 0..1 |
| `nm_subdist` | `xsd:string` | true | 0..1 |
| `cd_bairro` | `xsd:string` | true | 0..1 |
| `nm_bairro` | `xsd:string` | true | 0..1 |
| `cd_rgint` | `xsd:string` | true | 0..1 |
| `nm_rgint` | `xsd:string` | true | 0..1 |
| `cd_rgi` | `xsd:string` | true | 0..1 |
| `nm_rgi` | `xsd:string` | true | 0..1 |
| `cd_concurb` | `xsd:string` | true | 0..1 |
| `nm_concurb` | `xsd:string` | true | 0..1 |

### `ibge:bioma_ro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `fid` | `xsd:long` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `cd_bioma` | `xsd:int` | true | 0..1 |

### `ibge:divisao_distrital_ro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `fid` | `xsd:long` | true | 0..1 |
| `gm_layer` | `xsd:string` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nm_distrit` | `xsd:string` | true | 0..1 |
| `nm_municip` | `xsd:string` | true | 0..1 |
| `cd_geocmu` | `xsd:string` | true | 0..1 |

### `ibge:domicilios_ac`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `COD_UF` | `xsd:long` | true | 0..1 |
| `COD_MUN` | `xsd:long` | true | 0..1 |
| `COD_ESPECI` | `xsd:long` | true | 0..1 |
| `LATITUDE` | `xsd:decimal` | true | 0..1 |
| `LONGITUDE` | `xsd:decimal` | true | 0..1 |
| `NV_GEO_COO` | `xsd:long` | true | 0..1 |

### `ibge:domicilios_am`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `cod_uf` | `xsd:double` | true | 0..1 |
| `cod_mun` | `xsd:double` | true | 0..1 |
| `cod_especi` | `xsd:double` | true | 0..1 |
| `latitude` | `xsd:decimal` | true | 0..1 |
| `longitude` | `xsd:decimal` | true | 0..1 |
| `nv_geo_coo` | `xsd:double` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ibge:domicilios_ro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `COD_UF` | `xsd:long` | true | 0..1 |
| `COD_MUN` | `xsd:long` | true | 0..1 |
| `COD_ESPECI` | `xsd:long` | true | 0..1 |
| `LATITUDE` | `xsd:decimal` | true | 0..1 |
| `LONGITUDE` | `xsd:decimal` | true | 0..1 |
| `NV_GEO_COO` | `xsd:long` | true | 0..1 |

### `ibge:faixa_de_fronteira_por_uf_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `cd_uf` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `nm_regiao` | `xsd:string` | true | 0..1 |
| `area_km2` | `xsd:double` | true | 0..1 |
| `area_int` | `xsd:double` | true | 0..1 |
| `porc_int` | `xsd:double` | true | 0..1 |

### `ibge:fitofisonomia`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id1` | `xsd:long` | true | 0..1 |
| `cd_fcim` | `xsd:string` | true | 0..1 |
| `leg_carga` | `xsd:string` | true | 0..1 |
| `cd_fito` | `xsd:string` | true | 0..1 |
| `cd_leg_2` | `xsd:string` | true | 0..1 |
| `clas_domi` | `xsd:string` | true | 0..1 |
| `leg_uveg` | `xsd:string` | true | 0..1 |
| `nm_uveg` | `xsd:string` | true | 0..1 |
| `leg_uantr` | `xsd:string` | true | 0..1 |
| `nm_uantr` | `xsd:string` | true | 0..1 |
| `leg_contat` | `xsd:string` | true | 0..1 |
| `nm_contat` | `xsd:string` | true | 0..1 |
| `veg_pretet` | `xsd:string` | true | 0..1 |
| `nm_pretet` | `xsd:string` | true | 0..1 |
| `leg_sec1` | `xsd:string` | true | 0..1 |
| `nm_sec1` | `xsd:string` | true | 0..1 |
| `leg_sec2` | `xsd:string` | true | 0..1 |
| `nm_sec2` | `xsd:string` | true | 0..1 |
| `leg_sup` | `xsd:string` | true | 0..1 |
| `legenda_1` | `xsd:string` | true | 0..1 |
| `legenda_2` | `xsd:string` | true | 0..1 |
| `legenda` | `xsd:string` | true | 0..1 |
| `leg1_id` | `xsd:decimal` | true | 0..1 |
| `leg2_id` | `xsd:decimal` | true | 0..1 |
| `geocodigo` | `xsd:string` | true | 0..1 |
| `ar_poli_km` | `xsd:decimal` | true | 0..1 |
| `fid` | `xsd:decimal` | true | 0..1 |
| `cd_uf` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `nm_regiao` | `xsd:string` | true | 0..1 |

### `ibge:geomorfologia_311102024`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `id1` | `xsd:long` | true | 0..1 |
| `cd_fcim` | `xsd:string` | true | 0..1 |
| `leg_carga` | `xsd:string` | true | 0..1 |
| `nm_dominio` | `xsd:string` | true | 0..1 |
| `nm_regiao` | `xsd:string` | true | 0..1 |
| `id_unidade` | `xsd:long` | true | 0..1 |
| `nm_unidade` | `xsd:string` | true | 0..1 |
| `letra_simb` | `xsd:string` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `natureza` | `xsd:string` | true | 0..1 |
| `caract` | `xsd:string` | true | 0..1 |
| `forma` | `xsd:string` | true | 0..1 |
| `dens_dren` | `xsd:string` | true | 0..1 |
| `aprof_inci` | `xsd:string` | true | 0..1 |
| `niv_alt` | `xsd:string` | true | 0..1 |
| `leg_sup` | `xsd:string` | true | 0..1 |
| `cd_leg_sup` | `xsd:string` | true | 0..1 |
| `legenda` | `xsd:string` | true | 0..1 |
| `compartime` | `xsd:string` | true | 0..1 |
| `cd_comp_id` | `xsd:decimal` | true | 0..1 |
| `cd_dominio` | `xsd:decimal` | true | 0..1 |
| `cd_unid_id` | `xsd:decimal` | true | 0..1 |
| `cod_otto` | `xsd:string` | true | 0..1 |
| `ar_poli_km` | `xsd:decimal` | true | 0..1 |
| `fid` | `xsd:decimal` | true | 0..1 |
| `cd_uf` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `nm_regiao_` | `xsd:string` | true | 0..1 |

### `ibge:limite_regioes_administrativas_ro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `fid` | `xsd:long` | true | 0..1 |
| `setores_ro` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `município` | `xsd:string` | true | 0..1 |
| `região` | `xsd:string` | true | 0..1 |

### `ibge:municipios_da_faixa_de_fronteira_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `cd_mun` | `xsd:string` | true | 0..1 |
| `nm_regiao` | `xsd:string` | true | 0..1 |
| `cd_uf` | `xsd:long` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `nm_mun` | `xsd:string` | true | 0..1 |
| `area_tot` | `xsd:decimal` | true | 0..1 |
| `area_int` | `xsd:decimal` | true | 0..1 |
| `porc_int` | `xsd:decimal` | true | 0..1 |
| `cid_gemea` | `xsd:string` | true | 0..1 |

### `ibge:pedologia31102024`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `id1` | `xsd:long` | true | 0..1 |
| `cd_fcim` | `xsd:string` | true | 0..1 |
| `nom_unidad` | `xsd:string` | true | 0..1 |
| `cod_simbol` | `xsd:string` | true | 0..1 |
| `val_ncompo` | `xsd:decimal` | true | 0..1 |
| `legenda` | `xsd:string` | true | 0..1 |
| `ordem` | `xsd:string` | true | 0..1 |
| `subordem` | `xsd:string` | true | 0..1 |
| `grande_gru` | `xsd:string` | true | 0..1 |
| `subgrupos` | `xsd:string` | true | 0..1 |
| `textura` | `xsd:string` | true | 0..1 |
| `horizonte` | `xsd:string` | true | 0..1 |
| `erosao` | `xsd:string` | true | 0..1 |
| `pedregosid` | `xsd:string` | true | 0..1 |
| `rochosidad` | `xsd:string` | true | 0..1 |
| `relevo` | `xsd:string` | true | 0..1 |
| `componente` | `xsd:string` | true | 0..1 |
| `component1` | `xsd:string` | true | 0..1 |
| `component2` | `xsd:string` | true | 0..1 |
| `component3` | `xsd:string` | true | 0..1 |
| `inclu_p1` | `xsd:string` | true | 0..1 |
| `inclu_p2` | `xsd:string` | true | 0..1 |
| `inclu_p3` | `xsd:string` | true | 0..1 |
| `leg_ordem` | `xsd:string` | true | 0..1 |
| `legenda_2` | `xsd:string` | true | 0..1 |
| `cd_ord_id` | `xsd:decimal` | true | 0..1 |
| `cd_leg2_id` | `xsd:decimal` | true | 0..1 |
| `cod_otto` | `xsd:string` | true | 0..1 |
| `ar_poli_km` | `xsd:decimal` | true | 0..1 |
| `fid` | `xsd:decimal` | true | 0..1 |
| `cd_uf` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `nm_regiao` | `xsd:string` | true | 0..1 |

### `ibge:ro_bairros_cd2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `cd_regiao` | `xsd:string` | true | 0..1 |
| `nm_regiao` | `xsd:string` | true | 0..1 |
| `cd_uf` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `cd_mun` | `xsd:string` | true | 0..1 |
| `nm_mun` | `xsd:string` | true | 0..1 |
| `cd_dist` | `xsd:string` | true | 0..1 |
| `nm_dist` | `xsd:string` | true | 0..1 |
| `cd_subdist` | `xsd:string` | true | 0..1 |
| `nm_subdist` | `xsd:string` | true | 0..1 |
| `cd_bairro` | `xsd:string` | true | 0..1 |
| `nm_bairro` | `xsd:string` | true | 0..1 |
| `cd_rgint` | `xsd:string` | true | 0..1 |
| `nm_rgint` | `xsd:string` | true | 0..1 |
| `cd_rgi` | `xsd:string` | true | 0..1 |
| `nm_rgi` | `xsd:string` | true | 0..1 |
| `cd_concurb` | `xsd:string` | true | 0..1 |
| `nm_concurb` | `xsd:string` | true | 0..1 |

### `ibge:ro_distritos_cd2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `cd_regiao` | `xsd:string` | true | 0..1 |
| `nm_regiao` | `xsd:string` | true | 0..1 |
| `cd_uf` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `cd_mun` | `xsd:string` | true | 0..1 |
| `nm_mun` | `xsd:string` | true | 0..1 |
| `cd_dist` | `xsd:string` | true | 0..1 |
| `nm_dist` | `xsd:string` | true | 0..1 |
| `cd_rgint` | `xsd:string` | true | 0..1 |
| `nm_rgint` | `xsd:string` | true | 0..1 |
| `cd_rgi` | `xsd:string` | true | 0..1 |
| `nm_rgi` | `xsd:string` | true | 0..1 |
| `cd_concurb` | `xsd:string` | true | 0..1 |
| `nm_concurb` | `xsd:string` | true | 0..1 |

### `ibge:ro_divisao_distrital_2023`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `cd_regiao` | `xsd:string` | true | 0..1 |
| `nm_regiao` | `xsd:string` | true | 0..1 |
| `cd_uf` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `cd_mun` | `xsd:string` | true | 0..1 |
| `nm_mun` | `xsd:string` | true | 0..1 |
| `cd_dist` | `xsd:string` | true | 0..1 |
| `nm_dist` | `xsd:string` | true | 0..1 |
| `cd_rgint` | `xsd:string` | true | 0..1 |
| `nm_rgint` | `xsd:string` | true | 0..1 |
| `cd_rgi` | `xsd:string` | true | 0..1 |
| `nm_rgi` | `xsd:string` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `ibge:ro_mesorregioes_2000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `MSLINK` | `xsd:long` | true | 0..1 |
| `CODIGO` | `xsd:string` | true | 0..1 |
| `AREA_1` | `xsd:double` | true | 0..1 |
| `PERIMETRO_` | `xsd:double` | true | 0..1 |
| `GEOCODIGO` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `AREA_TOT_G` | `xsd:double` | true | 0..1 |
| `RESERVADO` | `xsd:boolean` | true | 0..1 |

### `ibge:ro_mesorregioes_2014`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `NM_MESO` | `xsd:string` | true | 0..1 |
| `CD_GEOCME` | `xsd:string` | true | 0..1 |

### `ibge:ro_mesorregioes_2015`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `NM_MESO` | `xsd:string` | true | 0..1 |
| `CD_GEOCME` | `xsd:string` | true | 0..1 |

### `ibge:ro_mesorregioes_2016`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `NM_MESO` | `xsd:string` | true | 0..1 |
| `CD_GEOCME` | `xsd:string` | true | 0..1 |

### `ibge:ro_mesorregioes_2017`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `NM_MESO` | `xsd:string` | true | 0..1 |
| `CD_GEOCME` | `xsd:string` | true | 0..1 |

### `ibge:ro_mesorregioes_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `NM_MESO` | `xsd:string` | true | 0..1 |
| `CD_GEOCME` | `xsd:string` | true | 0..1 |

### `ibge:ro_mesorregioes_2019`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_MESO` | `xsd:string` | true | 0..1 |
| `NM_MESO` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |

### `ibge:ro_mesorregioes_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_MESO` | `xsd:string` | true | 0..1 |
| `NM_MESO` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |

### `ibge:ro_mesorregioes_2021`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_MESO` | `xsd:string` | true | 0..1 |
| `NM_MESO` | `xsd:string` | true | 0..1 |
| `SIGLA` | `xsd:string` | true | 0..1 |

### `ibge:ro_mesorregioes_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_MESO` | `xsd:string` | true | 0..1 |
| `NM_MESO` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |

### `ibge:ro_microrregioes_2000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `MSLINK` | `xsd:long` | true | 0..1 |
| `CODIGO` | `xsd:string` | true | 0..1 |
| `AREA_1` | `xsd:double` | true | 0..1 |
| `PERIMETRO_` | `xsd:double` | true | 0..1 |
| `GEOCODIGO` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `AREA_TOT_G` | `xsd:double` | true | 0..1 |
| `RESERVADO` | `xsd:boolean` | true | 0..1 |

### `ibge:ro_microrregioes_2014`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `NM_MICRO` | `xsd:string` | true | 0..1 |
| `CD_GEOCMI` | `xsd:string` | true | 0..1 |

### `ibge:ro_microrregioes_2015`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `NM_MICRO` | `xsd:string` | true | 0..1 |
| `CD_GEOCMI` | `xsd:string` | true | 0..1 |

### `ibge:ro_microrregioes_2016`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `NM_MICRO` | `xsd:string` | true | 0..1 |
| `CD_GEOCMI` | `xsd:string` | true | 0..1 |

### `ibge:ro_microrregioes_2017`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `NM_MICRO` | `xsd:string` | true | 0..1 |
| `CD_GEOCMI` | `xsd:string` | true | 0..1 |

### `ibge:ro_microrregioes_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `NM_MICRO` | `xsd:string` | true | 0..1 |
| `CD_GEOCMI` | `xsd:string` | true | 0..1 |

### `ibge:ro_microrregioes_2019`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_MICRO` | `xsd:string` | true | 0..1 |
| `NM_MICRO` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |

### `ibge:ro_microrregioes_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_MICRO` | `xsd:string` | true | 0..1 |
| `NM_MICRO` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |

### `ibge:ro_microrregioes_2021`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_MICRO` | `xsd:string` | true | 0..1 |
| `NM_MICRO` | `xsd:string` | true | 0..1 |
| `SIGLA` | `xsd:string` | true | 0..1 |

### `ibge:ro_microrregioes_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_MICRO` | `xsd:string` | true | 0..1 |
| `NM_MICRO` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |

### `ibge:ro_municipios_2000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `MSLINK` | `xsd:long` | true | 0..1 |
| `CODIGO` | `xsd:string` | true | 0..1 |
| `AREA_1` | `xsd:double` | true | 0..1 |
| `PERIMETRO_` | `xsd:double` | true | 0..1 |
| `GEOCODIGO` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `SEDE` | `xsd:boolean` | true | 0..1 |
| `LATITUDESE` | `xsd:double` | true | 0..1 |
| `LONGITUDES` | `xsd:double` | true | 0..1 |
| `AREA_TOT_G` | `xsd:double` | true | 0..1 |
| `RESERVADO` | `xsd:boolean` | true | 0..1 |

### `ibge:ro_municipios_2014`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `NM_MUNICIP` | `xsd:string` | true | 0..1 |
| `CD_GEOCMU` | `xsd:string` | true | 0..1 |

### `ibge:ro_municipios_2015`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `NM_MUNICIP` | `xsd:string` | true | 0..1 |
| `CD_GEOCMU` | `xsd:string` | true | 0..1 |

### `ibge:ro_municipios_2016`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `NM_MUNICIP` | `xsd:string` | true | 0..1 |
| `CD_GEOCMU` | `xsd:string` | true | 0..1 |

### `ibge:ro_municipios_2017`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `NM_MUNICIP` | `xsd:string` | true | 0..1 |
| `CD_GEOCMU` | `xsd:string` | true | 0..1 |

### `ibge:ro_municipios_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `NM_MUNICIP` | `xsd:string` | true | 0..1 |
| `CD_GEOCMU` | `xsd:string` | true | 0..1 |

### `ibge:ro_municipios_2019`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_MUN` | `xsd:string` | true | 0..1 |
| `NM_MUN` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |

### `ibge:ro_municipios_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_MUN` | `xsd:string` | true | 0..1 |
| `NM_MUN` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |

### `ibge:ro_municipios_2021`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_MUN` | `xsd:string` | true | 0..1 |
| `NM_MUN` | `xsd:string` | true | 0..1 |
| `SIGLA` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:decimal` | true | 0..1 |

### `ibge:ro_municipios_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_MUN` | `xsd:string` | true | 0..1 |
| `NM_MUN` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |

### `ibge:ro_municipios_2023`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_MUN` | `xsd:string` | true | 0..1 |
| `NM_MUN` | `xsd:string` | true | 0..1 |
| `CD_RGI` | `xsd:string` | true | 0..1 |
| `NM_RGI` | `xsd:string` | true | 0..1 |
| `CD_RGINT` | `xsd:string` | true | 0..1 |
| `NM_RGINT` | `xsd:string` | true | 0..1 |
| `CD_UF` | `xsd:string` | true | 0..1 |
| `NM_UF` | `xsd:string` | true | 0..1 |
| `CD_REGIAO` | `xsd:string` | true | 0..1 |
| `NM_REGIAO` | `xsd:string` | true | 0..1 |
| `CD_CONCURB` | `xsd:string` | true | 0..1 |
| `NM_CONCURB` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |

### `ibge:ro_municipios_2024`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_MUN` | `xsd:string` | true | 0..1 |
| `NM_MUN` | `xsd:string` | true | 0..1 |
| `CD_RGI` | `xsd:string` | true | 0..1 |
| `NM_RGI` | `xsd:string` | true | 0..1 |
| `CD_RGINT` | `xsd:string` | true | 0..1 |
| `NM_RGINT` | `xsd:string` | true | 0..1 |
| `CD_UF` | `xsd:string` | true | 0..1 |
| `NM_UF` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `CD_REGIA` | `xsd:string` | true | 0..1 |
| `NM_REGIA` | `xsd:string` | true | 0..1 |
| `SIGLA_RG` | `xsd:string` | true | 0..1 |
| `CD_CONCU` | `xsd:string` | true | 0..1 |
| `NM_CONCU` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |

### `ibge:ro_municipios_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_MUN` | `xsd:string` | true | 0..1 |
| `NM_MUN` | `xsd:string` | true | 0..1 |
| `CD_RGI` | `xsd:string` | true | 0..1 |
| `NM_RGI` | `xsd:string` | true | 0..1 |
| `CD_RGINT` | `xsd:string` | true | 0..1 |
| `NM_RGINT` | `xsd:string` | true | 0..1 |
| `CD_UF` | `xsd:string` | true | 0..1 |
| `NM_UF` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `CD_REGIAO` | `xsd:string` | true | 0..1 |
| `NM_REGIAO` | `xsd:string` | true | 0..1 |
| `SIGLA_RG` | `xsd:string` | true | 0..1 |
| `CD_CONCURB` | `xsd:string` | true | 0..1 |
| `NM_CONCURB` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |

### `ibge:ro_regioes_imediatas_2019`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_RGI` | `xsd:string` | true | 0..1 |
| `NM_RGI` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |

### `ibge:ro_regioes_imediatas_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_RGI` | `xsd:string` | true | 0..1 |
| `NM_RGI` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |

### `ibge:ro_regioes_imediatas_2021`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_RGI` | `xsd:string` | true | 0..1 |
| `NM_RGI` | `xsd:string` | true | 0..1 |
| `SIGLA` | `xsd:string` | true | 0..1 |

### `ibge:ro_regioes_imediatas_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `cd_rgi` | `xsd:string` | true | 0..1 |
| `nm_rgi` | `xsd:string` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `area_km2` | `xsd:double` | true | 0..1 |

### `ibge:ro_regioes_imediatas_2023`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_RGI` | `xsd:string` | true | 0..1 |
| `NM_RGI` | `xsd:string` | true | 0..1 |
| `CD_UF` | `xsd:string` | true | 0..1 |
| `NM_UF` | `xsd:string` | true | 0..1 |
| `CD_REGIAO` | `xsd:string` | true | 0..1 |
| `NM_REGIAO` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |

### `ibge:ro_regioes_imediatas_2024`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_RGI` | `xsd:string` | true | 0..1 |
| `NM_RGI` | `xsd:string` | true | 0..1 |
| `CD_RGINT` | `xsd:string` | true | 0..1 |
| `NM_RGINT` | `xsd:string` | true | 0..1 |
| `CD_UF` | `xsd:string` | true | 0..1 |
| `NM_UF` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `CD_REGIA` | `xsd:string` | true | 0..1 |
| `NM_REGIA` | `xsd:string` | true | 0..1 |
| `SIGLA_RG` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |

### `ibge:ro_regioes_imediatas_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_RGI` | `xsd:string` | true | 0..1 |
| `NM_RGI` | `xsd:string` | true | 0..1 |
| `CD_RGINT` | `xsd:string` | true | 0..1 |
| `NM_RGINT` | `xsd:string` | true | 0..1 |
| `CD_UF` | `xsd:string` | true | 0..1 |
| `NM_UF` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `CD_REGIAO` | `xsd:string` | true | 0..1 |
| `NM_REGIAO` | `xsd:string` | true | 0..1 |
| `SIGLA_RG` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |

### `ibge:ro_regioes_intermediarias_2019`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_RGINT` | `xsd:string` | true | 0..1 |
| `NM_RGINT` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |

### `ibge:ro_regioes_intermediarias_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_RGINT` | `xsd:string` | true | 0..1 |
| `NM_RGINT` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |

### `ibge:ro_regioes_intermediarias_2021`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_RGINT` | `xsd:string` | true | 0..1 |
| `NM_RGINT` | `xsd:string` | true | 0..1 |
| `SIGLA` | `xsd:string` | true | 0..1 |

### `ibge:ro_regioes_intermediarias_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `cd_rgint` | `xsd:string` | true | 0..1 |
| `nm_rgint` | `xsd:string` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `area_km2` | `xsd:double` | true | 0..1 |

### `ibge:ro_regioes_intermediarias_2023`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_RGINT` | `xsd:string` | true | 0..1 |
| `NM_RGINT` | `xsd:string` | true | 0..1 |
| `CD_UF` | `xsd:string` | true | 0..1 |
| `NM_UF` | `xsd:string` | true | 0..1 |
| `CD_REGIAO` | `xsd:string` | true | 0..1 |
| `NM_REGIAO` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |

### `ibge:ro_regioes_intermediarias_2024`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_RGINT` | `xsd:string` | true | 0..1 |
| `NM_RGINT` | `xsd:string` | true | 0..1 |
| `CD_UF` | `xsd:string` | true | 0..1 |
| `NM_UF` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `CD_REGIA` | `xsd:string` | true | 0..1 |
| `NM_REGIA` | `xsd:string` | true | 0..1 |
| `SIGLA_RG` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |

### `ibge:ro_regioes_intermediarias_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_RGINT` | `xsd:string` | true | 0..1 |
| `NM_RGINT` | `xsd:string` | true | 0..1 |
| `CD_UF` | `xsd:string` | true | 0..1 |
| `NM_UF` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `CD_REGIAO` | `xsd:string` | true | 0..1 |
| `NM_REGIAO` | `xsd:string` | true | 0..1 |
| `SIGLA_RG` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |

### `ibge:ro_setores_cd2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `cd_setor` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `cd_sit` | `xsd:string` | true | 0..1 |
| `cd_tipo` | `xsd:string` | true | 0..1 |
| `area_km2` | `xsd:decimal` | true | 0..1 |
| `cd_regiao` | `xsd:string` | true | 0..1 |
| `nm_regiao` | `xsd:string` | true | 0..1 |
| `cd_uf` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `cd_mun` | `xsd:string` | true | 0..1 |
| `nm_mun` | `xsd:string` | true | 0..1 |
| `cd_dist` | `xsd:string` | true | 0..1 |
| `nm_dist` | `xsd:string` | true | 0..1 |
| `cd_subdist` | `xsd:string` | true | 0..1 |
| `nm_subdist` | `xsd:string` | true | 0..1 |
| `cd_bairro` | `xsd:string` | true | 0..1 |
| `nm_bairro` | `xsd:string` | true | 0..1 |
| `cd_nu` | `xsd:string` | true | 0..1 |
| `nm_nu` | `xsd:string` | true | 0..1 |
| `cd_fcu` | `xsd:string` | true | 0..1 |
| `nm_fcu` | `xsd:string` | true | 0..1 |
| `cd_aglom` | `xsd:string` | true | 0..1 |
| `nm_aglom` | `xsd:string` | true | 0..1 |
| `cd_rgint` | `xsd:string` | true | 0..1 |
| `nm_rgint` | `xsd:string` | true | 0..1 |
| `cd_rgi` | `xsd:string` | true | 0..1 |
| `nm_rgi` | `xsd:string` | true | 0..1 |
| `cd_concurb` | `xsd:string` | true | 0..1 |
| `nm_concurb` | `xsd:string` | true | 0..1 |

### `ibge:ro_subdistritos_cd2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `cd_regiao` | `xsd:string` | true | 0..1 |
| `nm_regiao` | `xsd:string` | true | 0..1 |
| `cd_uf` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `cd_mun` | `xsd:string` | true | 0..1 |
| `nm_mun` | `xsd:string` | true | 0..1 |
| `cd_dist` | `xsd:string` | true | 0..1 |
| `nm_dist` | `xsd:string` | true | 0..1 |
| `cd_subdist` | `xsd:string` | true | 0..1 |
| `nm_subdist` | `xsd:string` | true | 0..1 |
| `cd_rgint` | `xsd:string` | true | 0..1 |
| `nm_rgint` | `xsd:string` | true | 0..1 |
| `cd_rgi` | `xsd:string` | true | 0..1 |
| `nm_rgi` | `xsd:string` | true | 0..1 |
| `cd_concurb` | `xsd:string` | true | 0..1 |
| `nm_concurb` | `xsd:string` | true | 0..1 |
| `sigla` | `xsd:string` | true | 0..1 |

### `ibge:ro_uf_2000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `MSLINK` | `xsd:long` | true | 0..1 |
| `CODIGO` | `xsd:string` | true | 0..1 |
| `AREA_1` | `xsd:double` | true | 0..1 |
| `PERIMETRO_` | `xsd:double` | true | 0..1 |
| `GEOCODIGO` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `AREA_TOT_G` | `xsd:double` | true | 0..1 |
| `RESERVADO` | `xsd:boolean` | true | 0..1 |

### `ibge:ro_uf_2014`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `NM_ESTADO` | `xsd:string` | true | 0..1 |
| `NM_REGIAO` | `xsd:string` | true | 0..1 |
| `CD_GEOCUF` | `xsd:string` | true | 0..1 |

### `ibge:ro_uf_2015`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `NM_ESTADO` | `xsd:string` | true | 0..1 |
| `NM_REGIAO` | `xsd:string` | true | 0..1 |
| `CD_GEOCUF` | `xsd:string` | true | 0..1 |

### `ibge:ro_uf_2016`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `NM_ESTADO` | `xsd:string` | true | 0..1 |
| `NM_REGIAO` | `xsd:string` | true | 0..1 |
| `CD_GEOCUF` | `xsd:string` | true | 0..1 |

### `ibge:ro_uf_2017`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `NM_ESTADO` | `xsd:string` | true | 0..1 |
| `NM_REGIAO` | `xsd:string` | true | 0..1 |
| `CD_GEOCUF` | `xsd:string` | true | 0..1 |

### `ibge:ro_uf_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `NM_ESTADO` | `xsd:string` | true | 0..1 |
| `NM_REGIAO` | `xsd:string` | true | 0..1 |
| `CD_GEOCUF` | `xsd:string` | true | 0..1 |

### `ibge:ro_uf_2019`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_UF` | `xsd:string` | true | 0..1 |
| `NM_UF` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `NM_REGIAO` | `xsd:string` | true | 0..1 |

### `ibge:ro_uf_2021`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_UF` | `xsd:string` | true | 0..1 |
| `NM_UF` | `xsd:string` | true | 0..1 |
| `SIGLA` | `xsd:string` | true | 0..1 |
| `NM_REGIAO` | `xsd:string` | true | 0..1 |

### `ibge:ro_uf_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_UF` | `xsd:string` | true | 0..1 |
| `NM_UF` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `NM_REGIAO` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |

### `ibge:ro_uf_2023`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_UF` | `xsd:string` | true | 0..1 |
| `NM_UF` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `CD_REGIAO` | `xsd:string` | true | 0..1 |
| `NM_REGIAO` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |

### `ibge:ro_uf_2024`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_UF` | `xsd:string` | true | 0..1 |
| `NM_UF` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `CD_REGIA` | `xsd:string` | true | 0..1 |
| `NM_REGIA` | `xsd:string` | true | 0..1 |
| `SIGLA_RG` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |

### `ibge:ro_uf_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `CD_UF` | `xsd:string` | true | 0..1 |
| `NM_UF` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `CD_REGIAO` | `xsd:string` | true | 0..1 |
| `NM_REGIAO` | `xsd:string` | true | 0..1 |
| `SIGLA_RG` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:double` | true | 0..1 |

### `ibge:sedes_municipios_faixa_de_fronteira_cidades_gemeas_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `nm_regiao` | `xsd:string` | true | 0..1 |
| `cd_uf` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `cd_mun` | `xsd:string` | true | 0..1 |
| `nm_mun` | `xsd:string` | true | 0..1 |
| `lat_sede` | `xsd:decimal` | true | 0..1 |
| `lng_sede` | `xsd:decimal` | true | 0..1 |
| `cid_gemea` | `xsd:string` | true | 0..1 |
| `faixa_sede` | `xsd:string` | true | 0..1 |

### `ibge:territorio_cidadania`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `cd_mun` | `xsd:string` | true | 0..1 |
| `nm_mun` | `xsd:string` | true | 0..1 |
| `cd_rgi` | `xsd:string` | true | 0..1 |
| `nm_rgi` | `xsd:string` | true | 0..1 |
| `cd_rgint` | `xsd:string` | true | 0..1 |
| `nm_rgint` | `xsd:string` | true | 0..1 |
| `cd_uf` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `cd_regiao` | `xsd:string` | true | 0..1 |
| `nm_regiao` | `xsd:string` | true | 0..1 |
| `cd_concurb` | `xsd:string` | true | 0..1 |
| `nm_concurb` | `xsd:string` | true | 0..1 |
| `area_km2` | `xsd:decimal` | true | 0..1 |
| `TERRITORIO` | `xsd:string` | true | 0..1 |

### `ibge:trajetos_dos_recenseadores_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |

## icmbio (4)

### `icmbio:embargos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | true | 0..1 |
| `vw_num_emb` | `xsd:int` | true | 0..1 |
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
| `data` | `xsd:dateTime` | true | 0..1 |
| `ano` | `xsd:string` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `julgamento` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `processo` | `xsd:string` | true | 0..1 |
| `desc_inf_1` | `xsd:string` | true | 0..1 |
| `desc_san_1` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |

### `icmbio:limites_ucs_federais`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `ogc_fid` | `xsd:short` | true | 0..1 |
| `nomeuc` | `xsd:string` | true | 0..1 |
| `cnuc` | `xsd:string` | true | 0..1 |
| `criacaoano` | `xsd:string` | true | 0..1 |
| `areahaalb` | `xsd:decimal` | true | 0..1 |
| `perimm` | `xsd:decimal` | true | 0..1 |
| `criacaoato` | `xsd:string` | true | 0..1 |
| `esferaadm` | `xsd:string` | true | 0..1 |
| `siglacateg` | `xsd:string` | true | 0..1 |
| `grupouc` | `xsd:string` | true | 0..1 |
| `ufabrang` | `xsd:string` | true | 0..1 |
| `biomaibge` | `xsd:string` | true | 0..1 |
| `biomacrl` | `xsd:string` | true | 0..1 |
| `gregional` | `xsd:string` | true | 0..1 |
| `fusoabrang` | `xsd:string` | true | 0..1 |
| `abrev` | `xsd:string` | true | 0..1 |
| `escalauc` | `xsd:string` | true | 0..1 |
| `demarcacao` | `xsd:string` | true | 0..1 |

### `icmbio:rppn`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `imovelid` | `xsd:int` | true | 0..1 |
| `name` | `xsd:string` | true | 0..1 |
| `areaimovel` | `xsd:string` | true | 0..1 |
| `arearppn` | `xsd:double` | true | 0..1 |
| `nameimovel` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `qual_lim` | `xsd:string` | true | 0..1 |

### `icmbio:vw_autos_de_infracao`

> [!warning] Schema unresolved
> O XSD não foi resolvido nesta coleta. Reconsulte o endpoint antes de usar a camada.


## incra (11)

### `incra:areas_de_quilombolas_ro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geometry` | `gml:PolygonPropertyType` | true | 0..1 |
| `cd_quilomb` | `xsd:double` | true | 0..1 |
| `cd_sr` | `xsd:string` | true | 0..1 |
| `nr_process` | `xsd:string` | true | 0..1 |
| `nm_comunid` | `xsd:string` | true | 0..1 |
| `nm_municip` | `xsd:string` | true | 0..1 |
| `cd_uf` | `xsd:string` | true | 0..1 |
| `dt_publica` | `xsd:string` | true | 0..1 |
| `dt_public1` | `xsd:string` | true | 0..1 |
| `nr_familia` | `xsd:double` | true | 0..1 |
| `dt_titulac` | `xsd:string` | true | 0..1 |
| `nr_area_ha` | `xsd:double` | true | 0..1 |
| `nr_perimet` | `xsd:double` | true | 0..1 |
| `cd_sipra` | `xsd:string` | true | 0..1 |
| `ob_descric` | `xsd:string` | true | 0..1 |
| `st_titulad` | `xsd:string` | true | 0..1 |
| `dt_decreto` | `xsd:string` | true | 0..1 |
| `tp_levanta` | `xsd:string` | true | 0..1 |
| `nr_escalao` | `xsd:string` | true | 0..1 |
| `area_calc_` | `xsd:double` | true | 0..1 |
| `perimetro_` | `xsd:double` | true | 0..1 |
| `esfera` | `xsd:string` | true | 0..1 |
| `fase` | `xsd:string` | true | 0..1 |
| `responsave` | `xsd:string` | true | 0..1 |

### `incra:assentamento_federal_ro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `cd_sipra` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `nome_proje` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `area_hecta` | `xsd:string` | true | 0..1 |
| `capacidade` | `xsd:long` | true | 0..1 |
| `num_famili` | `xsd:long` | true | 0..1 |
| `fase` | `xsd:long` | true | 0..1 |
| `data_de_cr` | `xsd:string` | true | 0..1 |
| `forma_obte` | `xsd:string` | true | 0..1 |
| `data_obten` | `xsd:string` | true | 0..1 |
| `area_calc_` | `xsd:double` | true | 0..1 |
| `sr` | `xsd:string` | true | 0..1 |
| `descricao_` | `xsd:string` | true | 0..1 |

### `incra:fundiaria_siglo_publico`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `nome_do_lo` | `xsd:string` | true | 0..1 |
| `setor` | `xsd:decimal` | true | 0..1 |
| `nome_setor` | `xsd:string` | true | 0..1 |
| `gleba` | `xsd:string` | true | 0..1 |
| `nome_do_im` | `xsd:string` | true | 0..1 |
| `propriedad` | `xsd:string` | true | 0..1 |
| `nome_proje` | `xsd:string` | true | 0..1 |
| `adequacao_` | `xsd:decimal` | true | 0..1 |

### `incra:glebas_federais`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `gid` | `xsd:long` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `matricula` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `sr` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `consulta` | `xsd:string` | true | 0..1 |
| `assent_pre` | `xsd:long` | true | 0..1 |
| `ano_assent` | `xsd:decimal` | true | 0..1 |
| `data_dou` | `xsd:date` | true | 0..1 |
| `area_ha` | `xsd:decimal` | true | 0..1 |
| `data_certi` | `xsd:string` | true | 0..1 |
| `num_certif` | `xsd:string` | true | 0..1 |
| `mat_recons` | `xsd:string` | true | 0..1 |

### `incra:imovel_certificado_snci_privado_ro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `num_proces` | `xsd:string` | true | 0..1 |
| `sr` | `xsd:string` | true | 0..1 |
| `num_certif` | `xsd:string` | true | 0..1 |
| `data_certi` | `xsd:string` | true | 0..1 |
| `qtd_area_p` | `xsd:string` | true | 0..1 |
| `cod_profis` | `xsd:string` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `nome_imove` | `xsd:string` | true | 0..1 |
| `uf_municip` | `xsd:string` | true | 0..1 |

### `incra:imovel_certificado_snci_publico_ro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `num_proces` | `xsd:string` | true | 0..1 |
| `sr` | `xsd:string` | true | 0..1 |
| `num_certif` | `xsd:string` | true | 0..1 |
| `data_certi` | `xsd:string` | true | 0..1 |
| `qtd_area_p` | `xsd:string` | true | 0..1 |
| `cod_profis` | `xsd:string` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `nome_imove` | `xsd:string` | true | 0..1 |
| `uf_municip` | `xsd:string` | true | 0..1 |

### `incra:parcelas_geo_regularizacao_ro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |
| `parcela_codigo` | `xsd:string` | true | 0..1 |
| `orgao_publico` | `xsd:string` | true | 0..1 |
| `licitacao` | `xsd:string` | true | 0..1 |
| `modalidade` | `xsd:string` | true | 0..1 |
| `contrato` | `xsd:string` | true | 0..1 |
| `rt` | `xsd:string` | true | 0..1 |
| `art` | `xsd:string` | true | 0..1 |
| `situacao_informada` | `xsd:string` | true | 0..1 |
| `natureza` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `data_submissao` | `xsd:string` | true | 0..1 |
| `migrada` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |
| `municipio_id` | `xsd:long` | true | 0..1 |
| `uf_id` | `xsd:long` | true | 0..1 |
| `codigo_imovel` | `xsd:double` | true | 0..1 |
| `nome_area` | `xsd:string` | true | 0..1 |
| `municipio_nome` | `xsd:string` | true | 0..1 |
| `uf_sigla` | `xsd:string` | true | 0..1 |

### `incra:projetos_de_assentamento_consolidados`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `ID1` | `xsd:long` | true | 0..1 |
| `Cod_Sipra` | `xsd:string` | true | 0..1 |
| `Denominaca` | `xsd:string` | true | 0..1 |
| `Familias_A` | `xsd:int` | true | 0..1 |
| `Capacidade` | `xsd:int` | true | 0..1 |
| `Area_de_Cr` | `xsd:decimal` | true | 0..1 |
| `Perimetro_` | `xsd:decimal` | true | 0..1 |
| `Area_Demar` | `xsd:decimal` | true | 0..1 |
| `Perimetr_1` | `xsd:decimal` | true | 0..1 |
| `RT_da_Dema` | `xsd:string` | true | 0..1 |
| `Fase` | `xsd:int` | true | 0..1 |
| `Ato_Tipo` | `xsd:string` | true | 0..1 |
| `Num_do_Ato` | `xsd:int` | true | 0..1 |
| `Data_Criac` | `xsd:date` | true | 0..1 |
| `Forma_da_O` | `xsd:string` | true | 0..1 |
| `Demarcado_` | `xsd:string` | true | 0..1 |
| `Demarcad_1` | `xsd:string` | true | 0..1 |
| `Demarcad_2` | `xsd:string` | true | 0..1 |
| `Instituica` | `xsd:string` | true | 0..1 |
| `Responsave` | `xsd:string` | true | 0..1 |
| `Data_Prime` | `xsd:date` | true | 0..1 |
| `Responsa_1` | `xsd:string` | true | 0..1 |
| `Data_Ultim` | `xsd:date` | true | 0..1 |
| `Municipio_` | `xsd:string` | true | 0..1 |
| `UF` | `xsd:string` | true | 0..1 |
| `Lat_GWS` | `xsd:string` | true | 0..1 |
| `Long_GWS` | `xsd:string` | true | 0..1 |
| `Obs` | `xsd:string` | true | 0..1 |

### `incra:projetos_de_assentamento_nao_consolidados`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `ID1` | `xsd:long` | true | 0..1 |
| `Cod_Sipra` | `xsd:string` | true | 0..1 |
| `Denominaca` | `xsd:string` | true | 0..1 |
| `Familias_A` | `xsd:int` | true | 0..1 |
| `Capacidade` | `xsd:int` | true | 0..1 |
| `Area_de_Cr` | `xsd:decimal` | true | 0..1 |
| `Perimetro_` | `xsd:decimal` | true | 0..1 |
| `Area_Demar` | `xsd:decimal` | true | 0..1 |
| `Perimetr_1` | `xsd:decimal` | true | 0..1 |
| `RT_da_Dema` | `xsd:string` | true | 0..1 |
| `Fase` | `xsd:int` | true | 0..1 |
| `Ato_Tipo` | `xsd:string` | true | 0..1 |
| `Num_do_Ato` | `xsd:int` | true | 0..1 |
| `Data_Criac` | `xsd:date` | true | 0..1 |
| `Forma_da_O` | `xsd:string` | true | 0..1 |
| `Demarcado_` | `xsd:string` | true | 0..1 |
| `Demarcad_1` | `xsd:string` | true | 0..1 |
| `Demarcad_2` | `xsd:string` | true | 0..1 |
| `Instituica` | `xsd:string` | true | 0..1 |
| `Responsave` | `xsd:string` | true | 0..1 |
| `Data_Prime` | `xsd:date` | true | 0..1 |
| `Responsa_1` | `xsd:string` | true | 0..1 |
| `Data_Ultim` | `xsd:date` | true | 0..1 |
| `Municipio_` | `xsd:string` | true | 0..1 |
| `UF` | `xsd:string` | true | 0..1 |
| `Lat_GWS` | `xsd:string` | true | 0..1 |
| `Long_GWS` | `xsd:string` | true | 0..1 |
| `Obs` | `xsd:string` | true | 0..1 |

### `incra:sigef_privado_ro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geometry` | `gml:PolygonPropertyType` | true | 0..1 |
| `rt` | `xsd:string` | true | 0..1 |
| `art` | `xsd:string` | true | 0..1 |
| `situacao_i` | `xsd:string` | true | 0..1 |
| `codigo_imo` | `xsd:string` | true | 0..1 |
| `data_submi` | `xsd:string` | true | 0..1 |
| `data_aprov` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `nome_area` | `xsd:string` | true | 0..1 |
| `registro_m` | `xsd:string` | true | 0..1 |
| `registro_d` | `xsd:string` | true | 0..1 |
| `municipio_` | `xsd:long` | true | 0..1 |
| `uf_id` | `xsd:long` | true | 0..1 |
| `municipio_nome` | `xsd:string` | true | 0..1 |
| `uf_sigla` | `xsd:string` | true | 0..1 |

### `incra:sigef_publico_ro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geometry` | `gml:PolygonPropertyType` | true | 0..1 |
| `rt` | `xsd:string` | true | 0..1 |
| `art` | `xsd:string` | true | 0..1 |
| `situacao_i` | `xsd:string` | true | 0..1 |
| `codigo_imo` | `xsd:string` | true | 0..1 |
| `data_submi` | `xsd:string` | true | 0..1 |
| `data_aprov` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `nome_area` | `xsd:string` | true | 0..1 |
| `registro_m` | `xsd:string` | true | 0..1 |
| `registro_d` | `xsd:string` | true | 0..1 |
| `municipio_` | `xsd:long` | true | 0..1 |
| `uf_id` | `xsd:long` | true | 0..1 |
| `municipio_nome` | `xsd:string` | true | 0..1 |
| `uf_sigla` | `xsd:string` | true | 0..1 |

## inpe (11)

### `inpe:deter_public_ro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `CLASSNAME` | `xsd:string` | true | 0..1 |
| `QUADRANT` | `xsd:string` | true | 0..1 |
| `PATH_ROW` | `xsd:string` | true | 0..1 |
| `VIEW_DATE` | `xsd:dateTime` | true | 0..1 |
| `SENSOR` | `xsd:string` | true | 0..1 |
| `SATELLITE` | `xsd:string` | true | 0..1 |
| `AREAUCKM` | `xsd:double` | true | 0..1 |
| `UC` | `xsd:string` | true | 0..1 |
| `AREAMUNKM` | `xsd:double` | true | 0..1 |
| `MUNICIPALI` | `xsd:string` | true | 0..1 |
| `GEOCODIBGE` | `xsd:string` | true | 0..1 |
| `UF` | `xsd:string` | true | 0..1 |
| `ano` | `xsd:int` | true | 0..1 |
| `mes/ano` | `xsd:string` | true | 0..1 |

### `inpe:deter_public_ro_2023`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `CLASSNAME` | `xsd:string` | true | 0..1 |
| `QUADRANT` | `xsd:string` | true | 0..1 |
| `PATH_ROW` | `xsd:string` | true | 0..1 |
| `VIEW_DATE` | `xsd:dateTime` | true | 0..1 |
| `SENSOR` | `xsd:string` | true | 0..1 |
| `SATELLITE` | `xsd:string` | true | 0..1 |
| `AREAUCKM` | `xsd:double` | true | 0..1 |
| `UC` | `xsd:string` | true | 0..1 |
| `AREAMUNKM` | `xsd:double` | true | 0..1 |
| `MUNICIPALI` | `xsd:string` | true | 0..1 |
| `GEOCODIBGE` | `xsd:string` | true | 0..1 |
| `UF` | `xsd:string` | true | 0..1 |
| `ano` | `xsd:int` | true | 0..1 |
| `mes/ano` | `xsd:string` | true | 0..1 |

### `inpe:deter_public_ro_2024`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `CLASSNAME` | `xsd:string` | true | 0..1 |
| `QUADRANT` | `xsd:string` | true | 0..1 |
| `PATH_ROW` | `xsd:string` | true | 0..1 |
| `VIEW_DATE` | `xsd:dateTime` | true | 0..1 |
| `SENSOR` | `xsd:string` | true | 0..1 |
| `SATELLITE` | `xsd:string` | true | 0..1 |
| `AREAUCKM` | `xsd:double` | true | 0..1 |
| `UC` | `xsd:string` | true | 0..1 |
| `AREAMUNKM` | `xsd:double` | true | 0..1 |
| `MUNICIPALI` | `xsd:string` | true | 0..1 |
| `GEOCODIBGE` | `xsd:string` | true | 0..1 |
| `UF` | `xsd:string` | true | 0..1 |
| `ano` | `xsd:int` | true | 0..1 |
| `mes/ano` | `xsd:string` | true | 0..1 |

### `inpe:mosaico_amazonia1_wfi_2021`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `index` | `xsd:string` | true | 0..1 |
| `datetime` | `xsd:string` | true | 0..1 |
| `path` | `xsd:long` | true | 0..1 |
| `row` | `xsd:long` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `sensor` | `xsd:string` | true | 0..1 |
| `cloud_cove` | `xsd:decimal` | true | 0..1 |

### `inpe:mosaico_cbers4a_mux_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `index` | `xsd:string` | true | 0..1 |
| `datetime` | `xsd:string` | true | 0..1 |
| `path` | `xsd:long` | true | 0..1 |
| `row` | `xsd:long` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `sensor` | `xsd:string` | true | 0..1 |
| `cloud_cove` | `xsd:decimal` | true | 0..1 |

### `inpe:mosaico_cbers4a_wpm_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `index` | `xsd:string` | true | 0..1 |
| `datetime` | `xsd:string` | true | 0..1 |
| `path` | `xsd:long` | true | 0..1 |
| `row` | `xsd:long` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `sensor` | `xsd:string` | true | 0..1 |
| `cloud_cove` | `xsd:decimal` | true | 0..1 |

### `inpe:PRODES_1988_2007_RO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `fid` | `xsd:long` | true | 0..1 |
| `origin_id` | `xsd:double` | true | 0..1 |
| `state` | `xsd:string` | true | 0..1 |
| `path_row` | `xsd:string` | true | 0..1 |
| `main_class` | `xsd:string` | true | 0..1 |
| `class_name` | `xsd:string` | true | 0..1 |
| `def_cloud` | `xsd:double` | true | 0..1 |
| `julian_day` | `xsd:double` | true | 0..1 |
| `image_date` | `xsd:string` | true | 0..1 |
| `year` | `xsd:double` | true | 0..1 |
| `area_km` | `xsd:double` | true | 0..1 |
| `scene_id` | `xsd:double` | true | 0..1 |
| `source` | `xsd:string` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `sensor` | `xsd:string` | true | 0..1 |

### `inpe:PRODES_2008_2023_RO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `fid` | `xsd:long` | true | 0..1 |
| `state` | `xsd:string` | true | 0..1 |
| `path_row` | `xsd:string` | true | 0..1 |
| `main_class` | `xsd:string` | true | 0..1 |
| `class_name` | `xsd:string` | true | 0..1 |
| `sub_class` | `xsd:string` | true | 0..1 |
| `def_cloud` | `xsd:double` | true | 0..1 |
| `julian_day` | `xsd:int` | true | 0..1 |
| `image_date` | `xsd:date` | true | 0..1 |
| `year` | `xsd:double` | true | 0..1 |
| `area_km` | `xsd:double` | true | 0..1 |
| `scene_id` | `xsd:int` | true | 0..1 |
| `source` | `xsd:string` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `sensor` | `xsd:string` | true | 0..1 |
| `uuid` | `xsd:string` | true | 0..1 |

### `inpe:prodes_public_ro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `fid` | `xsd:int` | true | 0..1 |
| `state` | `xsd:string` | true | 0..1 |
| `path_row` | `xsd:string` | true | 0..1 |
| `main_class` | `xsd:string` | true | 0..1 |
| `class_name` | `xsd:string` | true | 0..1 |
| `sub_class` | `xsd:string` | true | 0..1 |
| `def_cloud` | `xsd:double` | true | 0..1 |
| `julian_day` | `xsd:int` | true | 0..1 |
| `image_date` | `xsd:dateTime` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `area_km` | `xsd:double` | true | 0..1 |
| `scene_id` | `xsd:double` | true | 0..1 |
| `source` | `xsd:string` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `sensor` | `xsd:string` | true | 0..1 |
| `uuid` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `ano` | `xsd:long` | true | 0..1 |
| `nm_distrito` | `xsd:string` | true | 0..1 |
| `nm_municipio` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:decimal` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `area_uc_fed_ha` | `xsd:decimal` | true | 0..1 |
| `perc_uc_fed` | `xsd:decimal` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `area_uc_est_ha` | `xsd:decimal` | true | 0..1 |
| `perc_uc_est` | `xsd:decimal` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `area_uc_mun_ha` | `xsd:decimal` | true | 0..1 |
| `perc_uc_mun` | `xsd:decimal` | true | 0..1 |
| `nome_terra_indigena` | `xsd:string` | true | 0..1 |
| `area_ti_ha` | `xsd:decimal` | true | 0..1 |
| `perc_ti` | `xsd:decimal` | true | 0..1 |
| `nome_quilombola` | `xsd:string` | true | 0..1 |
| `area_quilombola_ha` | `xsd:decimal` | true | 0..1 |
| `perc_quilombola` | `xsd:decimal` | true | 0..1 |
| `situacao_area_protegida` | `xsd:string` | true | 0..1 |

### `inpe:prodes_public_ro_2024`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `fid` | `xsd:int` | true | 0..1 |
| `state` | `xsd:string` | true | 0..1 |
| `path_row` | `xsd:string` | true | 0..1 |
| `main_class` | `xsd:string` | true | 0..1 |
| `class_name` | `xsd:string` | true | 0..1 |
| `sub_class` | `xsd:string` | true | 0..1 |
| `def_cloud` | `xsd:double` | true | 0..1 |
| `julian_day` | `xsd:int` | true | 0..1 |
| `image_date` | `xsd:dateTime` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `area_km` | `xsd:double` | true | 0..1 |
| `scene_id` | `xsd:double` | true | 0..1 |
| `source` | `xsd:string` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `sensor` | `xsd:string` | true | 0..1 |
| `uuid` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `ano` | `xsd:long` | true | 0..1 |
| `nm_distrito` | `xsd:string` | true | 0..1 |
| `nm_municipio` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:decimal` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `area_uc_fed_ha` | `xsd:decimal` | true | 0..1 |
| `perc_uc_fed` | `xsd:decimal` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `area_uc_est_ha` | `xsd:decimal` | true | 0..1 |
| `perc_uc_est` | `xsd:decimal` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `area_uc_mun_ha` | `xsd:decimal` | true | 0..1 |
| `perc_uc_mun` | `xsd:decimal` | true | 0..1 |
| `nome_terra_indigena` | `xsd:string` | true | 0..1 |
| `area_ti_ha` | `xsd:decimal` | true | 0..1 |
| `perc_ti` | `xsd:decimal` | true | 0..1 |
| `nome_quilombola` | `xsd:string` | true | 0..1 |
| `area_quilombola_ha` | `xsd:decimal` | true | 0..1 |
| `perc_quilombola` | `xsd:decimal` | true | 0..1 |
| `situacao_area_protegida` | `xsd:string` | true | 0..1 |

### `inpe:prodes_public_ro_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `fid` | `xsd:int` | true | 0..1 |
| `state` | `xsd:string` | true | 0..1 |
| `path_row` | `xsd:string` | true | 0..1 |
| `main_class` | `xsd:string` | true | 0..1 |
| `class_name` | `xsd:string` | true | 0..1 |
| `sub_class` | `xsd:string` | true | 0..1 |
| `def_cloud` | `xsd:double` | true | 0..1 |
| `julian_day` | `xsd:int` | true | 0..1 |
| `image_date` | `xsd:dateTime` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `area_km` | `xsd:double` | true | 0..1 |
| `scene_id` | `xsd:double` | true | 0..1 |
| `source` | `xsd:string` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `sensor` | `xsd:string` | true | 0..1 |
| `uuid` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `ano` | `xsd:long` | true | 0..1 |
| `nm_distrito` | `xsd:string` | true | 0..1 |
| `nm_municipio` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:decimal` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `area_uc_fed_ha` | `xsd:decimal` | true | 0..1 |
| `perc_uc_fed` | `xsd:decimal` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `area_uc_est_ha` | `xsd:decimal` | true | 0..1 |
| `perc_uc_est` | `xsd:decimal` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `area_uc_mun_ha` | `xsd:decimal` | true | 0..1 |
| `perc_uc_mun` | `xsd:decimal` | true | 0..1 |
| `nome_terra_indigena` | `xsd:string` | true | 0..1 |
| `area_ti_ha` | `xsd:decimal` | true | 0..1 |
| `perc_ti` | `xsd:decimal` | true | 0..1 |
| `nome_quilombola` | `xsd:string` | true | 0..1 |
| `area_quilombola_ha` | `xsd:decimal` | true | 0..1 |
| `perc_quilombola` | `xsd:decimal` | true | 0..1 |
| `situacao_area_protegida` | `xsd:string` | true | 0..1 |

## iphan (2)

### `iphan:inst_guarda_pesquisa`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `responsavel` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:MultiPointPropertyType` | true | 0..1 |

### `iphan:sitios`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:string` | true | 0..1 |
| `id_bem` | `xsd:int` | true | 0..1 |
| `identificacao_bem` | `xsd:string` | true | 0..1 |
| `co_iphan` | `xsd:string` | true | 0..1 |
| `no_logradouro` | `xsd:string` | true | 0..1 |
| `nu_logradouro` | `xsd:string` | true | 0..1 |
| `id_natureza` | `xsd:int` | true | 0..1 |
| `ds_natureza` | `xsd:string` | true | 0..1 |
| `codigo_iphan` | `xsd:string` | true | 0..1 |
| `id_classificacao` | `xsd:int` | true | 0..1 |
| `ds_classificacao` | `xsd:string` | true | 0..1 |
| `id_tipo_bem` | `xsd:int` | true | 0..1 |
| `ds_tipo_bem` | `xsd:string` | true | 0..1 |
| `sg_tipo_bem` | `xsd:string` | true | 0..1 |
| `sintese_bem` | `xsd:string` | true | 0..1 |
| `dt_cadastro` | `xsd:dateTime` | true | 0..1 |
| `geometry` | `gml:PointPropertyType` | true | 0..1 |

## mapbiomas (1)

### `mapbiomas:alertas_mapbiomas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `CODEALERTA` | `xsd:long` | true | 0..1 |
| `FONTE` | `xsd:string` | true | 0..1 |
| `BIOMA` | `xsd:string` | true | 0..1 |
| `ESTADO` | `xsd:string` | true | 0..1 |
| `MUNICIPIO` | `xsd:string` | true | 0..1 |
| `AREAHA` | `xsd:double` | true | 0..1 |
| `ANODETEC` | `xsd:double` | true | 0..1 |
| `DATADETEC` | `xsd:string` | true | 0..1 |
| `DTIMGANT` | `xsd:string` | true | 0..1 |
| `DTIMGDEP` | `xsd:string` | true | 0..1 |
| `DTPUBLI` | `xsd:string` | true | 0..1 |
| `VPRESSAO` | `xsd:string` | true | 0..1 |

## nasa (23)

### `nasa:focos_aqua_10d`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `bright_ti4` | `xsd:double` | true | 0..1 |
| `scan` | `xsd:double` | true | 0..1 |
| `track` | `xsd:double` | true | 0..1 |
| `acq_date` | `xsd:date` | true | 0..1 |
| `acq_time` | `xsd:long` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `instrument` | `xsd:string` | true | 0..1 |
| `confidence` | `xsd:string` | true | 0..1 |
| `version` | `xsd:string` | true | 0..1 |
| `bright_ti5` | `xsd:double` | true | 0..1 |
| `frp` | `xsd:double` | true | 0..1 |
| `daynight` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `datetime` | `xsd:dateTime` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `terra_indigena_nome` | `xsd:string` | true | 0..1 |
| `nome_dist` | `xsd:string` | true | 0..1 |
| `hash` | `xsd:string` | false | 1..1 |
| `id` | `xsd:string` | false | 1..1 |
| `brightness` | `xsd:string` | true | 0..1 |
| `bright_t31` | `xsd:string` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `coordenadas` | `xsd:string` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `month` | `xsd:int` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |

### `nasa:focos_aqua_24h`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `bright_ti4` | `xsd:double` | true | 0..1 |
| `scan` | `xsd:double` | true | 0..1 |
| `track` | `xsd:double` | true | 0..1 |
| `acq_date` | `xsd:date` | true | 0..1 |
| `acq_time` | `xsd:long` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `instrument` | `xsd:string` | true | 0..1 |
| `confidence` | `xsd:string` | true | 0..1 |
| `version` | `xsd:string` | true | 0..1 |
| `bright_ti5` | `xsd:double` | true | 0..1 |
| `frp` | `xsd:double` | true | 0..1 |
| `daynight` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `datetime` | `xsd:dateTime` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `terra_indigena_nome` | `xsd:string` | true | 0..1 |
| `nome_dist` | `xsd:string` | true | 0..1 |
| `hash` | `xsd:string` | false | 1..1 |
| `id` | `xsd:string` | false | 1..1 |
| `brightness` | `xsd:string` | true | 0..1 |
| `bright_t31` | `xsd:string` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `coordenadas` | `xsd:string` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `month` | `xsd:int` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |

### `nasa:focos_aqua_30d`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `bright_ti4` | `xsd:double` | true | 0..1 |
| `scan` | `xsd:double` | true | 0..1 |
| `track` | `xsd:double` | true | 0..1 |
| `acq_date` | `xsd:date` | true | 0..1 |
| `acq_time` | `xsd:long` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `instrument` | `xsd:string` | true | 0..1 |
| `confidence` | `xsd:string` | true | 0..1 |
| `version` | `xsd:string` | true | 0..1 |
| `bright_ti5` | `xsd:double` | true | 0..1 |
| `frp` | `xsd:double` | true | 0..1 |
| `daynight` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `datetime` | `xsd:dateTime` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `terra_indigena_nome` | `xsd:string` | true | 0..1 |
| `nome_dist` | `xsd:string` | true | 0..1 |
| `hash` | `xsd:string` | false | 1..1 |
| `id` | `xsd:string` | false | 1..1 |
| `brightness` | `xsd:string` | true | 0..1 |
| `bright_t31` | `xsd:string` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `coordenadas` | `xsd:string` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `month` | `xsd:int` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |

### `nasa:focos_aqua_7d`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `bright_ti4` | `xsd:double` | true | 0..1 |
| `scan` | `xsd:double` | true | 0..1 |
| `track` | `xsd:double` | true | 0..1 |
| `acq_date` | `xsd:date` | true | 0..1 |
| `acq_time` | `xsd:long` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `instrument` | `xsd:string` | true | 0..1 |
| `confidence` | `xsd:string` | true | 0..1 |
| `version` | `xsd:string` | true | 0..1 |
| `bright_ti5` | `xsd:double` | true | 0..1 |
| `frp` | `xsd:double` | true | 0..1 |
| `daynight` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `datetime` | `xsd:dateTime` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `terra_indigena_nome` | `xsd:string` | true | 0..1 |
| `nome_dist` | `xsd:string` | true | 0..1 |
| `hash` | `xsd:string` | false | 1..1 |
| `id` | `xsd:string` | false | 1..1 |
| `brightness` | `xsd:string` | true | 0..1 |
| `bright_t31` | `xsd:string` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `coordenadas` | `xsd:string` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `month` | `xsd:int` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |

### `nasa:focos_aqua_hoje`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `bright_ti4` | `xsd:double` | true | 0..1 |
| `scan` | `xsd:double` | true | 0..1 |
| `track` | `xsd:double` | true | 0..1 |
| `acq_date` | `xsd:date` | true | 0..1 |
| `acq_time` | `xsd:long` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `instrument` | `xsd:string` | true | 0..1 |
| `confidence` | `xsd:string` | true | 0..1 |
| `version` | `xsd:string` | true | 0..1 |
| `bright_ti5` | `xsd:double` | true | 0..1 |
| `frp` | `xsd:double` | true | 0..1 |
| `daynight` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `datetime` | `xsd:dateTime` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `terra_indigena_nome` | `xsd:string` | true | 0..1 |
| `nome_dist` | `xsd:string` | true | 0..1 |
| `hash` | `xsd:string` | false | 1..1 |
| `id` | `xsd:string` | false | 1..1 |
| `brightness` | `xsd:string` | true | 0..1 |
| `bright_t31` | `xsd:string` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `coordenadas` | `xsd:string` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `month` | `xsd:int` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |

### `nasa:focos_noaa20_10d`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `bright_ti4` | `xsd:double` | true | 0..1 |
| `scan` | `xsd:double` | true | 0..1 |
| `track` | `xsd:double` | true | 0..1 |
| `acq_date` | `xsd:date` | true | 0..1 |
| `acq_time` | `xsd:long` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `instrument` | `xsd:string` | true | 0..1 |
| `confidence` | `xsd:string` | true | 0..1 |
| `version` | `xsd:string` | true | 0..1 |
| `bright_ti5` | `xsd:double` | true | 0..1 |
| `frp` | `xsd:double` | true | 0..1 |
| `daynight` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `datetime` | `xsd:dateTime` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `terra_indigena_nome` | `xsd:string` | true | 0..1 |
| `nome_dist` | `xsd:string` | true | 0..1 |
| `hash` | `xsd:string` | false | 1..1 |
| `id` | `xsd:string` | false | 1..1 |
| `brightness` | `xsd:string` | true | 0..1 |
| `bright_t31` | `xsd:string` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `coordenadas` | `xsd:string` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `month` | `xsd:int` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |

### `nasa:focos_noaa20_24h`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `bright_ti4` | `xsd:double` | true | 0..1 |
| `scan` | `xsd:double` | true | 0..1 |
| `track` | `xsd:double` | true | 0..1 |
| `acq_date` | `xsd:date` | true | 0..1 |
| `acq_time` | `xsd:long` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `instrument` | `xsd:string` | true | 0..1 |
| `confidence` | `xsd:string` | true | 0..1 |
| `version` | `xsd:string` | true | 0..1 |
| `bright_ti5` | `xsd:double` | true | 0..1 |
| `frp` | `xsd:double` | true | 0..1 |
| `daynight` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `datetime` | `xsd:dateTime` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `terra_indigena_nome` | `xsd:string` | true | 0..1 |
| `nome_dist` | `xsd:string` | true | 0..1 |
| `hash` | `xsd:string` | false | 1..1 |
| `id` | `xsd:string` | false | 1..1 |
| `brightness` | `xsd:string` | true | 0..1 |
| `bright_t31` | `xsd:string` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `coordenadas` | `xsd:string` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `month` | `xsd:int` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |

### `nasa:focos_noaa20_30d`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `bright_ti4` | `xsd:double` | true | 0..1 |
| `scan` | `xsd:double` | true | 0..1 |
| `track` | `xsd:double` | true | 0..1 |
| `acq_date` | `xsd:date` | true | 0..1 |
| `acq_time` | `xsd:long` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `instrument` | `xsd:string` | true | 0..1 |
| `confidence` | `xsd:string` | true | 0..1 |
| `version` | `xsd:string` | true | 0..1 |
| `bright_ti5` | `xsd:double` | true | 0..1 |
| `frp` | `xsd:double` | true | 0..1 |
| `daynight` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `datetime` | `xsd:dateTime` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `terra_indigena_nome` | `xsd:string` | true | 0..1 |
| `nome_dist` | `xsd:string` | true | 0..1 |
| `hash` | `xsd:string` | false | 1..1 |
| `brightness` | `xsd:string` | true | 0..1 |
| `bright_t31` | `xsd:string` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `coordenadas` | `xsd:string` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `month` | `xsd:int` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |

### `nasa:focos_noaa20_7d`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `bright_ti4` | `xsd:double` | true | 0..1 |
| `scan` | `xsd:double` | true | 0..1 |
| `track` | `xsd:double` | true | 0..1 |
| `acq_date` | `xsd:date` | true | 0..1 |
| `acq_time` | `xsd:long` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `instrument` | `xsd:string` | true | 0..1 |
| `confidence` | `xsd:string` | true | 0..1 |
| `version` | `xsd:string` | true | 0..1 |
| `bright_ti5` | `xsd:double` | true | 0..1 |
| `frp` | `xsd:double` | true | 0..1 |
| `daynight` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `datetime` | `xsd:dateTime` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `terra_indigena_nome` | `xsd:string` | true | 0..1 |
| `nome_dist` | `xsd:string` | true | 0..1 |
| `hash` | `xsd:string` | false | 1..1 |
| `brightness` | `xsd:string` | true | 0..1 |
| `bright_t31` | `xsd:string` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `coordenadas` | `xsd:string` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `month` | `xsd:int` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |

### `nasa:focos_noaa20_hoje`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `bright_ti4` | `xsd:double` | true | 0..1 |
| `scan` | `xsd:double` | true | 0..1 |
| `track` | `xsd:double` | true | 0..1 |
| `acq_date` | `xsd:date` | true | 0..1 |
| `acq_time` | `xsd:long` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `instrument` | `xsd:string` | true | 0..1 |
| `confidence` | `xsd:string` | true | 0..1 |
| `version` | `xsd:string` | true | 0..1 |
| `bright_ti5` | `xsd:double` | true | 0..1 |
| `frp` | `xsd:double` | true | 0..1 |
| `daynight` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `datetime` | `xsd:dateTime` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `terra_indigena_nome` | `xsd:string` | true | 0..1 |
| `nome_dist` | `xsd:string` | true | 0..1 |
| `hash` | `xsd:string` | false | 1..1 |
| `brightness` | `xsd:string` | true | 0..1 |
| `bright_t31` | `xsd:string` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `coordenadas` | `xsd:string` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `month` | `xsd:int` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |

### `nasa:focos_noaa21_10d`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `bright_ti4` | `xsd:double` | true | 0..1 |
| `scan` | `xsd:double` | true | 0..1 |
| `track` | `xsd:double` | true | 0..1 |
| `acq_date` | `xsd:date` | true | 0..1 |
| `acq_time` | `xsd:long` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `instrument` | `xsd:string` | true | 0..1 |
| `confidence` | `xsd:string` | true | 0..1 |
| `version` | `xsd:string` | true | 0..1 |
| `bright_ti5` | `xsd:double` | true | 0..1 |
| `frp` | `xsd:double` | true | 0..1 |
| `daynight` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `datetime` | `xsd:dateTime` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `terra_indigena_nome` | `xsd:string` | true | 0..1 |
| `nome_dist` | `xsd:string` | true | 0..1 |
| `hash` | `xsd:string` | false | 1..1 |
| `brightness` | `xsd:string` | true | 0..1 |
| `bright_t31` | `xsd:string` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `coordenadas` | `xsd:string` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `month` | `xsd:int` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |

### `nasa:focos_noaa21_24h`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `bright_ti4` | `xsd:double` | true | 0..1 |
| `scan` | `xsd:double` | true | 0..1 |
| `track` | `xsd:double` | true | 0..1 |
| `acq_date` | `xsd:date` | true | 0..1 |
| `acq_time` | `xsd:long` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `instrument` | `xsd:string` | true | 0..1 |
| `confidence` | `xsd:string` | true | 0..1 |
| `version` | `xsd:string` | true | 0..1 |
| `bright_ti5` | `xsd:double` | true | 0..1 |
| `frp` | `xsd:double` | true | 0..1 |
| `daynight` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `datetime` | `xsd:dateTime` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `terra_indigena_nome` | `xsd:string` | true | 0..1 |
| `nome_dist` | `xsd:string` | true | 0..1 |
| `hash` | `xsd:string` | false | 1..1 |
| `brightness` | `xsd:string` | true | 0..1 |
| `bright_t31` | `xsd:string` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `coordenadas` | `xsd:string` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `month` | `xsd:int` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |

### `nasa:focos_noaa21_30d`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `bright_ti4` | `xsd:double` | true | 0..1 |
| `scan` | `xsd:double` | true | 0..1 |
| `track` | `xsd:double` | true | 0..1 |
| `acq_date` | `xsd:date` | true | 0..1 |
| `acq_time` | `xsd:long` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `instrument` | `xsd:string` | true | 0..1 |
| `confidence` | `xsd:string` | true | 0..1 |
| `version` | `xsd:string` | true | 0..1 |
| `bright_ti5` | `xsd:double` | true | 0..1 |
| `frp` | `xsd:double` | true | 0..1 |
| `daynight` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `datetime` | `xsd:dateTime` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `terra_indigena_nome` | `xsd:string` | true | 0..1 |
| `nome_dist` | `xsd:string` | true | 0..1 |
| `hash` | `xsd:string` | false | 1..1 |
| `brightness` | `xsd:string` | true | 0..1 |
| `bright_t31` | `xsd:string` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `coordenadas` | `xsd:string` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `month` | `xsd:int` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |

### `nasa:focos_noaa21_7d`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `bright_ti4` | `xsd:double` | true | 0..1 |
| `scan` | `xsd:double` | true | 0..1 |
| `track` | `xsd:double` | true | 0..1 |
| `acq_date` | `xsd:date` | true | 0..1 |
| `acq_time` | `xsd:long` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `instrument` | `xsd:string` | true | 0..1 |
| `confidence` | `xsd:string` | true | 0..1 |
| `version` | `xsd:string` | true | 0..1 |
| `bright_ti5` | `xsd:double` | true | 0..1 |
| `frp` | `xsd:double` | true | 0..1 |
| `daynight` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `datetime` | `xsd:dateTime` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `terra_indigena_nome` | `xsd:string` | true | 0..1 |
| `nome_dist` | `xsd:string` | true | 0..1 |
| `hash` | `xsd:string` | false | 1..1 |
| `brightness` | `xsd:string` | true | 0..1 |
| `bright_t31` | `xsd:string` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `coordenadas` | `xsd:string` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `month` | `xsd:int` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |

### `nasa:focos_noaa21_hoje`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `bright_ti4` | `xsd:double` | true | 0..1 |
| `scan` | `xsd:double` | true | 0..1 |
| `track` | `xsd:double` | true | 0..1 |
| `acq_date` | `xsd:date` | true | 0..1 |
| `acq_time` | `xsd:long` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `instrument` | `xsd:string` | true | 0..1 |
| `confidence` | `xsd:string` | true | 0..1 |
| `version` | `xsd:string` | true | 0..1 |
| `bright_ti5` | `xsd:double` | true | 0..1 |
| `frp` | `xsd:double` | true | 0..1 |
| `daynight` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `datetime` | `xsd:dateTime` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `terra_indigena_nome` | `xsd:string` | true | 0..1 |
| `nome_dist` | `xsd:string` | true | 0..1 |
| `hash` | `xsd:string` | false | 1..1 |
| `id` | `xsd:string` | false | 1..1 |
| `brightness` | `xsd:string` | true | 0..1 |
| `bright_t31` | `xsd:string` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `coordenadas` | `xsd:string` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `month` | `xsd:int` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |

### `nasa:focos_snpp_10d`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `bright_ti4` | `xsd:double` | true | 0..1 |
| `scan` | `xsd:double` | true | 0..1 |
| `track` | `xsd:double` | true | 0..1 |
| `acq_date` | `xsd:date` | true | 0..1 |
| `acq_time` | `xsd:long` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `instrument` | `xsd:string` | true | 0..1 |
| `confidence` | `xsd:string` | true | 0..1 |
| `version` | `xsd:string` | true | 0..1 |
| `bright_ti5` | `xsd:double` | true | 0..1 |
| `frp` | `xsd:double` | true | 0..1 |
| `daynight` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `datetime` | `xsd:dateTime` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `terra_indigena_nome` | `xsd:string` | true | 0..1 |
| `nome_dist` | `xsd:string` | true | 0..1 |
| `hash` | `xsd:string` | false | 1..1 |
| `brightness` | `xsd:string` | true | 0..1 |
| `bright_t31` | `xsd:string` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `coordenadas` | `xsd:string` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `month` | `xsd:int` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |

### `nasa:focos_snpp_24h`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `bright_ti4` | `xsd:double` | true | 0..1 |
| `scan` | `xsd:double` | true | 0..1 |
| `track` | `xsd:double` | true | 0..1 |
| `acq_date` | `xsd:date` | true | 0..1 |
| `acq_time` | `xsd:long` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `instrument` | `xsd:string` | true | 0..1 |
| `confidence` | `xsd:string` | true | 0..1 |
| `version` | `xsd:string` | true | 0..1 |
| `bright_ti5` | `xsd:double` | true | 0..1 |
| `frp` | `xsd:double` | true | 0..1 |
| `daynight` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `datetime` | `xsd:dateTime` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `terra_indigena_nome` | `xsd:string` | true | 0..1 |
| `nome_dist` | `xsd:string` | true | 0..1 |
| `hash` | `xsd:string` | false | 1..1 |
| `brightness` | `xsd:string` | true | 0..1 |
| `bright_t31` | `xsd:string` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `coordenadas` | `xsd:string` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `month` | `xsd:int` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |

### `nasa:focos_snpp_30d`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `bright_ti4` | `xsd:double` | true | 0..1 |
| `scan` | `xsd:double` | true | 0..1 |
| `track` | `xsd:double` | true | 0..1 |
| `acq_date` | `xsd:date` | true | 0..1 |
| `acq_time` | `xsd:long` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `instrument` | `xsd:string` | true | 0..1 |
| `confidence` | `xsd:string` | true | 0..1 |
| `version` | `xsd:string` | true | 0..1 |
| `bright_ti5` | `xsd:double` | true | 0..1 |
| `frp` | `xsd:double` | true | 0..1 |
| `daynight` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `datetime` | `xsd:dateTime` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `terra_indigena_nome` | `xsd:string` | true | 0..1 |
| `nome_dist` | `xsd:string` | true | 0..1 |
| `hash` | `xsd:string` | false | 1..1 |
| `id` | `xsd:string` | false | 1..1 |
| `brightness` | `xsd:string` | true | 0..1 |
| `bright_t31` | `xsd:string` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `coordenadas` | `xsd:string` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `month` | `xsd:int` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |

### `nasa:focos_snpp_7d`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `bright_ti4` | `xsd:double` | true | 0..1 |
| `scan` | `xsd:double` | true | 0..1 |
| `track` | `xsd:double` | true | 0..1 |
| `acq_date` | `xsd:date` | true | 0..1 |
| `acq_time` | `xsd:long` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `instrument` | `xsd:string` | true | 0..1 |
| `confidence` | `xsd:string` | true | 0..1 |
| `version` | `xsd:string` | true | 0..1 |
| `bright_ti5` | `xsd:double` | true | 0..1 |
| `frp` | `xsd:double` | true | 0..1 |
| `daynight` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `datetime` | `xsd:dateTime` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `terra_indigena_nome` | `xsd:string` | true | 0..1 |
| `nome_dist` | `xsd:string` | true | 0..1 |
| `hash` | `xsd:string` | false | 1..1 |
| `brightness` | `xsd:string` | true | 0..1 |
| `bright_t31` | `xsd:string` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `coordenadas` | `xsd:string` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `month` | `xsd:int` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |

### `nasa:focos_snpp_hoje`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `bright_ti4` | `xsd:double` | true | 0..1 |
| `scan` | `xsd:double` | true | 0..1 |
| `track` | `xsd:double` | true | 0..1 |
| `acq_date` | `xsd:date` | true | 0..1 |
| `acq_time` | `xsd:long` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `instrument` | `xsd:string` | true | 0..1 |
| `confidence` | `xsd:string` | true | 0..1 |
| `version` | `xsd:string` | true | 0..1 |
| `bright_ti5` | `xsd:double` | true | 0..1 |
| `frp` | `xsd:double` | true | 0..1 |
| `daynight` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `datetime` | `xsd:dateTime` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `terra_indigena_nome` | `xsd:string` | true | 0..1 |
| `nome_dist` | `xsd:string` | true | 0..1 |
| `hash` | `xsd:string` | false | 1..1 |
| `brightness` | `xsd:string` | true | 0..1 |
| `bright_t31` | `xsd:string` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `coordenadas` | `xsd:string` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `month` | `xsd:int` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |

### `nasa:tb_focos_noaa20`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `bright_ti4` | `xsd:double` | true | 0..1 |
| `scan` | `xsd:double` | true | 0..1 |
| `track` | `xsd:double` | true | 0..1 |
| `acq_date` | `xsd:date` | true | 0..1 |
| `acq_time` | `xsd:long` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `instrument` | `xsd:string` | true | 0..1 |
| `confidence` | `xsd:string` | true | 0..1 |
| `version` | `xsd:string` | true | 0..1 |
| `bright_ti5` | `xsd:double` | true | 0..1 |
| `frp` | `xsd:double` | true | 0..1 |
| `daynight` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:PointPropertyType` | true | 0..1 |
| `datetime` | `xsd:dateTime` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `terra_indigena_nome` | `xsd:string` | true | 0..1 |
| `nome_dist` | `xsd:string` | true | 0..1 |
| `hash` | `xsd:string` | false | 1..1 |
| `brightness` | `xsd:string` | true | 0..1 |
| `bright_t31` | `xsd:string` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `coordenadas` | `xsd:string` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `month` | `xsd:int` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |

### `nasa:tb_focos_noaa21`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `bright_ti4` | `xsd:double` | true | 0..1 |
| `scan` | `xsd:double` | true | 0..1 |
| `track` | `xsd:double` | true | 0..1 |
| `acq_date` | `xsd:date` | true | 0..1 |
| `acq_time` | `xsd:long` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `instrument` | `xsd:string` | true | 0..1 |
| `confidence` | `xsd:string` | true | 0..1 |
| `version` | `xsd:string` | true | 0..1 |
| `bright_ti5` | `xsd:double` | true | 0..1 |
| `frp` | `xsd:double` | true | 0..1 |
| `daynight` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:PointPropertyType` | true | 0..1 |
| `datetime` | `xsd:dateTime` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `terra_indigena_nome` | `xsd:string` | true | 0..1 |
| `nome_dist` | `xsd:string` | true | 0..1 |
| `hash` | `xsd:string` | false | 1..1 |
| `brightness` | `xsd:string` | true | 0..1 |
| `bright_t31` | `xsd:string` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `coordenadas` | `xsd:string` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `month` | `xsd:int` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |

### `nasa:tb_focos_snpp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `bright_ti4` | `xsd:double` | true | 0..1 |
| `scan` | `xsd:double` | true | 0..1 |
| `track` | `xsd:double` | true | 0..1 |
| `acq_date` | `xsd:date` | true | 0..1 |
| `acq_time` | `xsd:long` | true | 0..1 |
| `satellite` | `xsd:string` | true | 0..1 |
| `instrument` | `xsd:string` | true | 0..1 |
| `confidence` | `xsd:string` | true | 0..1 |
| `version` | `xsd:string` | true | 0..1 |
| `bright_ti5` | `xsd:double` | true | 0..1 |
| `frp` | `xsd:double` | true | 0..1 |
| `daynight` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |
| `datetime` | `xsd:dateTime` | true | 0..1 |
| `sigla_uf` | `xsd:string` | true | 0..1 |
| `pais` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `nome_mun` | `xsd:string` | true | 0..1 |
| `nome_uc_fed` | `xsd:string` | true | 0..1 |
| `nome_uc_est` | `xsd:string` | true | 0..1 |
| `nome_uc_mun` | `xsd:string` | true | 0..1 |
| `terra_indigena_nome` | `xsd:string` | true | 0..1 |
| `nome_dist` | `xsd:string` | true | 0..1 |
| `hash` | `xsd:string` | false | 1..1 |
| `brightness` | `xsd:string` | true | 0..1 |
| `bright_t31` | `xsd:string` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `coordenadas` | `xsd:string` | true | 0..1 |
| `year` | `xsd:int` | true | 0..1 |
| `month` | `xsd:int` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |

## noaa (4)

### `noaa:vw_leitura_estacoes`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | false | 1..1 |
| `nome_estacao` | `xsd:string` | true | 0..1 |
| `horario_leitura` | `xsd:dateTime` | false | 1..1 |
| `horario_leitura_fmt` | `xsd:string` | true | 0..1 |
| `tensao_bateria` | `xsd:string` | true | 0..1 |
| `temperatura_ar` | `xsd:string` | true | 0..1 |
| `umidade_relativa` | `xsd:string` | true | 0..1 |
| `pressao_atmosferica` | `xsd:string` | true | 0..1 |
| `radiacao_solar` | `xsd:string` | true | 0..1 |
| `direcao_vento` | `xsd:string` | true | 0..1 |
| `velocidade_vento` | `xsd:string` | true | 0..1 |
| `precipitacao` | `xsd:string` | true | 0..1 |
| `pcd_tombo` | `xsd:string` | true | 0..1 |
| `nm_mun` | `xsd:string` | true | 0..1 |
| `nm_dist` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:decimal` | true | 0..1 |
| `longitude` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `noaa:vw_leitura_estacoes_10d`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome_distrito` | `xsd:string` | true | 0..1 |
| `horario_leitura` | `xsd:dateTime` | false | 1..1 |
| `horario_leitura_fmt` | `xsd:string` | true | 0..1 |
| `tensao_bateria` | `xsd:string` | true | 0..1 |
| `temperatura_ar` | `xsd:string` | true | 0..1 |
| `umidade_relativa` | `xsd:string` | true | 0..1 |
| `pressao_atmosferica` | `xsd:string` | true | 0..1 |
| `radiacao_solar` | `xsd:string` | true | 0..1 |
| `direcao_vento` | `xsd:string` | true | 0..1 |
| `velocidade_vento` | `xsd:string` | true | 0..1 |
| `precipitacao` | `xsd:string` | true | 0..1 |
| `pcd_tombo` | `xsd:string` | true | 0..1 |
| `nm_mun` | `xsd:string` | true | 0..1 |
| `nm_dist` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:decimal` | true | 0..1 |
| `longitude` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `noaa:vw_leitura_estacoes_1d`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome_distrito` | `xsd:string` | true | 0..1 |
| `horario_leitura` | `xsd:dateTime` | false | 1..1 |
| `horario_leitura_fmt` | `xsd:string` | true | 0..1 |
| `tensao_bateria` | `xsd:string` | true | 0..1 |
| `temperatura_ar` | `xsd:string` | true | 0..1 |
| `umidade_relativa` | `xsd:string` | true | 0..1 |
| `pressao_atmosferica` | `xsd:string` | true | 0..1 |
| `radiacao_solar` | `xsd:string` | true | 0..1 |
| `direcao_vento` | `xsd:string` | true | 0..1 |
| `velocidade_vento` | `xsd:string` | true | 0..1 |
| `precipitacao` | `xsd:string` | true | 0..1 |
| `pcd_tombo` | `xsd:string` | true | 0..1 |
| `nm_mun` | `xsd:string` | true | 0..1 |
| `nm_dist` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:decimal` | true | 0..1 |
| `longitude` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `noaa:vw_leitura_estacoes_7d`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome_distrito` | `xsd:string` | true | 0..1 |
| `horario_leitura` | `xsd:dateTime` | false | 1..1 |
| `horario_leitura_fmt` | `xsd:string` | true | 0..1 |
| `tensao_bateria` | `xsd:string` | true | 0..1 |
| `temperatura_ar` | `xsd:string` | true | 0..1 |
| `umidade_relativa` | `xsd:string` | true | 0..1 |
| `pressao_atmosferica` | `xsd:string` | true | 0..1 |
| `radiacao_solar` | `xsd:string` | true | 0..1 |
| `direcao_vento` | `xsd:string` | true | 0..1 |
| `velocidade_vento` | `xsd:string` | true | 0..1 |
| `precipitacao` | `xsd:string` | true | 0..1 |
| `pcd_tombo` | `xsd:string` | true | 0..1 |
| `nm_mun` | `xsd:string` | true | 0..1 |
| `nm_dist` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:decimal` | true | 0..1 |
| `longitude` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

## openstreetmap (15)

### `openstreetmap:areas_naturais`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `osm_id` | `xsd:string` | true | 0..1 |
| `code` | `xsd:int` | true | 0..1 |
| `fclass` | `xsd:string` | true | 0..1 |
| `name` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:PointPropertyType` | true | 0..1 |

### `openstreetmap:cursos_agua`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `osm_id` | `xsd:string` | true | 0..1 |
| `code` | `xsd:int` | true | 0..1 |
| `fclass` | `xsd:string` | true | 0..1 |
| `width` | `xsd:int` | true | 0..1 |
| `name` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |

### `openstreetmap:ferrovias`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `osm_id` | `xsd:string` | true | 0..1 |
| `code` | `xsd:int` | true | 0..1 |
| `fclass` | `xsd:string` | true | 0..1 |
| `name` | `xsd:string` | true | 0..1 |
| `layer` | `xsd:long` | true | 0..1 |
| `bridge` | `xsd:string` | true | 0..1 |
| `tunnel` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:LineStringPropertyType` | true | 0..1 |

### `openstreetmap:linhas_transmissao`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `osm_id` | `xsd:string` | true | 0..1 |
| `name` | `xsd:string` | true | 0..1 |
| `highway` | `xsd:string` | true | 0..1 |
| `waterway` | `xsd:string` | true | 0..1 |
| `aerialway` | `xsd:string` | true | 0..1 |
| `barrier` | `xsd:string` | true | 0..1 |
| `man_made` | `xsd:string` | true | 0..1 |
| `railway` | `xsd:string` | true | 0..1 |
| `z_order` | `xsd:int` | true | 0..1 |
| `other_tags` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |

### `openstreetmap:localidades`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `osm_id` | `xsd:string` | true | 0..1 |
| `code` | `xsd:int` | true | 0..1 |
| `fclass` | `xsd:string` | true | 0..1 |
| `population` | `xsd:long` | true | 0..1 |
| `name` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:PointPropertyType` | true | 0..1 |

### `openstreetmap:lugares_culto`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `osm_id` | `xsd:string` | true | 0..1 |
| `code` | `xsd:int` | true | 0..1 |
| `fclass` | `xsd:string` | true | 0..1 |
| `name` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:PointPropertyType` | true | 0..1 |

### `openstreetmap:pontos_interesse`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `osm_id` | `xsd:string` | true | 0..1 |
| `code` | `xsd:int` | true | 0..1 |
| `fclass` | `xsd:string` | true | 0..1 |
| `name` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:PointPropertyType` | true | 0..1 |

### `openstreetmap:rodovias_ac`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `osm_id` | `xsd:string` | true | 0..1 |
| `code` | `xsd:int` | true | 0..1 |
| `fclass` | `xsd:string` | true | 0..1 |
| `name` | `xsd:string` | true | 0..1 |
| `ref` | `xsd:string` | true | 0..1 |
| `oneway` | `xsd:string` | true | 0..1 |
| `maxspeed` | `xsd:int` | true | 0..1 |
| `layer` | `xsd:long` | true | 0..1 |
| `bridge` | `xsd:string` | true | 0..1 |
| `tunnel` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |

### `openstreetmap:rodovias_am`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `osm_id` | `xsd:string` | true | 0..1 |
| `code` | `xsd:int` | true | 0..1 |
| `fclass` | `xsd:string` | true | 0..1 |
| `name` | `xsd:string` | true | 0..1 |
| `ref` | `xsd:string` | true | 0..1 |
| `oneway` | `xsd:string` | true | 0..1 |
| `maxspeed` | `xsd:int` | true | 0..1 |
| `layer` | `xsd:long` | true | 0..1 |
| `bridge` | `xsd:string` | true | 0..1 |
| `tunnel` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |

### `openstreetmap:rodovias_bolivia`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `osm_id` | `xsd:string` | true | 0..1 |
| `code` | `xsd:int` | true | 0..1 |
| `fclass` | `xsd:string` | true | 0..1 |
| `name` | `xsd:string` | true | 0..1 |
| `ref` | `xsd:string` | true | 0..1 |
| `oneway` | `xsd:string` | true | 0..1 |
| `maxspeed` | `xsd:int` | true | 0..1 |
| `layer` | `xsd:long` | true | 0..1 |
| `bridge` | `xsd:string` | true | 0..1 |
| `tunnel` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |

### `openstreetmap:rodovias_mt`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `osm_id` | `xsd:string` | true | 0..1 |
| `code` | `xsd:int` | true | 0..1 |
| `fclass` | `xsd:string` | true | 0..1 |
| `name` | `xsd:string` | true | 0..1 |
| `ref` | `xsd:string` | true | 0..1 |
| `oneway` | `xsd:string` | true | 0..1 |
| `maxspeed` | `xsd:int` | true | 0..1 |
| `layer` | `xsd:long` | true | 0..1 |
| `bridge` | `xsd:string` | true | 0..1 |
| `tunnel` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |

### `openstreetmap:rodovias_ro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `osm_id` | `xsd:string` | true | 0..1 |
| `code` | `xsd:int` | true | 0..1 |
| `fclass` | `xsd:string` | true | 0..1 |
| `name` | `xsd:string` | true | 0..1 |
| `ref` | `xsd:string` | true | 0..1 |
| `oneway` | `xsd:string` | true | 0..1 |
| `maxspeed` | `xsd:int` | true | 0..1 |
| `layer` | `xsd:long` | true | 0..1 |
| `bridge` | `xsd:string` | true | 0..1 |
| `tunnel` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:GeometryPropertyType` | true | 0..1 |

### `openstreetmap:torres_energia`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `osm_id` | `xsd:string` | true | 0..1 |
| `name` | `xsd:string` | true | 0..1 |
| `barrier` | `xsd:string` | true | 0..1 |
| `highway` | `xsd:string` | true | 0..1 |
| `ref` | `xsd:string` | true | 0..1 |
| `address` | `xsd:string` | true | 0..1 |
| `is_in` | `xsd:string` | true | 0..1 |
| `place` | `xsd:string` | true | 0..1 |
| `man_made` | `xsd:string` | true | 0..1 |
| `other_tags` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:PointPropertyType` | true | 0..1 |

### `openstreetmap:trafego`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `osm_id` | `xsd:string` | true | 0..1 |
| `code` | `xsd:int` | true | 0..1 |
| `fclass` | `xsd:string` | true | 0..1 |
| `name` | `xsd:string` | true | 0..1 |
| `calming` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:PointPropertyType` | true | 0..1 |

### `openstreetmap:transporte`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `osm_id` | `xsd:string` | true | 0..1 |
| `code` | `xsd:int` | true | 0..1 |
| `fclass` | `xsd:string` | true | 0..1 |
| `name` | `xsd:string` | true | 0..1 |
| `geometry` | `gml:PointPropertyType` | true | 0..1 |

## pra (19)

### `pra:area_regularidade_imovel`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `sei` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:long` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `nom_municipio` | `xsd:string` | true | 0..1 |
| `cod_controle` | `xsd:string` | true | 0..1 |
| `dt_emissao` | `xsd:dateTime` | true | 0..1 |
| `dt_finalizacao` | `xsd:dateTime` | true | 0..1 |
| `nm_tipo_area_regularidade_imovel` | `xsd:string` | true | 0..1 |
| `nm_tema_analise` | `xsd:string` | true | 0..1 |
| `des_condicao` | `xsd:string` | true | 0..1 |
| `num_area_passivo` | `xsd:double` | true | 0..1 |

### `pra:pra_geometrias`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `sei` | `xsd:string` | true | 0..1 |
| `recibo` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |

### `pra:vw_pra`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `sei` | `xsd:string` | true | 0..1 |
| `tipo_termo` | `xsd:int` | true | 0..1 |
| `num_termo` | `xsd:string` | true | 0..1 |
| `dt_compromisso` | `xsd:date` | true | 0..1 |
| `ano_termo` | `xsd:string` | true | 0..1 |
| `cod_controle` | `xsd:string` | true | 0..1 |
| `dt_emissao` | `xsd:dateTime` | true | 0..1 |
| `dt_finalizacao` | `xsd:dateTime` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `nom_imovel` | `xsd:string` | true | 0..1 |
| `nom_municipio` | `xsd:string` | true | 0..1 |
| `num_area_imovel` | `xsd:double` | true | 0..1 |
| `num_modulo_fiscal` | `xsd:double` | true | 0..1 |
| `nu_registro_rl` | `xsd:string` | true | 0..1 |
| `nu_rl_minima_exigida_lei` | `xsd:double` | true | 0..1 |
| `nu_rl_registrada` | `xsd:double` | true | 0..1 |
| `nu_rl_excedente_passivo` | `xsd:double` | true | 0..1 |
| `num_area_consolidada` | `xsd:double` | true | 0..1 |
| `num_remanescente_vegetacao` | `xsd:double` | true | 0..1 |
| `num_area_preservacao_permanente` | `xsd:double` | true | 0..1 |
| `num_reserva_legal_recompor` | `xsd:double` | true | 0..1 |
| `num_reserva_legal_compensar` | `xsd:double` | true | 0..1 |
| `num_area_preservacao_permanente_recompor` | `xsd:double` | true | 0..1 |
| `num_area_uso_restrito_recompor` | `xsd:double` | true | 0..1 |
| `dt_criacao` | `xsd:dateTime` | true | 0..1 |
| `dt_atualizacao` | `xsd:dateTime` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:long` | true | 0..1 |
| `extrato` | `xsd:string` | true | 0..1 |
| `dt_publicacao` | `xsd:date` | true | 0..1 |
| `pra_modalidade` | `xsd:string` | true | 0..1 |
| `des_estado_civil` | `xsd:string` | true | 0..1 |

### `pra:vw_pra_geom_app_lagos_lagoas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `sei` | `xsd:string` | true | 0..1 |
| `recibo` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |

### `pra:vw_pra_geom_app_total`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `sei` | `xsd:string` | true | 0..1 |
| `recibo` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |

### `pra:vw_pra_geom_area_consolidada`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `sei` | `xsd:string` | true | 0..1 |
| `recibo` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |

### `pra:vw_pra_geom_area_reserva_legal`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `sei` | `xsd:string` | true | 0..1 |
| `recibo` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |

### `pra:vw_pra_geom_area_servidao`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `sei` | `xsd:string` | true | 0..1 |
| `recibo` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |

### `pra:vw_pra_geom_curso_dagua`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `sei` | `xsd:string` | true | 0..1 |
| `recibo` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |

### `pra:vw_pra_geom_curso_dagua_10a50m`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `sei` | `xsd:string` | true | 0..1 |
| `recibo` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |

### `pra:vw_pra_geom_curso_dagua_200a600m`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `sei` | `xsd:string` | true | 0..1 |
| `recibo` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |

### `pra:vw_pra_geom_curso_dagua_50a200m`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `sei` | `xsd:string` | true | 0..1 |
| `recibo` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |

### `pra:vw_pra_geom_curso_dagua_acima_600m`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `sei` | `xsd:string` | true | 0..1 |
| `recibo` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |

### `pra:vw_pra_geom_curso_dagua_ate_10m`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `sei` | `xsd:string` | true | 0..1 |
| `recibo` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |

### `pra:vw_pra_geom_remanescente_vegetacao`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `sei` | `xsd:string` | true | 0..1 |
| `recibo` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |

### `pra:vw_pra_geom_reservatorio_artificial`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `sei` | `xsd:string` | true | 0..1 |
| `recibo` | `xsd:string` | true | 0..1 |
| `area` | `xsd:string` | true | 0..1 |
| `tema` | `xsd:string` | true | 0..1 |

### `pra:vw_pra_imovel_area_preservacao_permanente`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `sei` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:long` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `nom_municipio` | `xsd:string` | true | 0..1 |
| `cod_controle` | `xsd:string` | true | 0..1 |
| `dt_emissao` | `xsd:dateTime` | true | 0..1 |
| `dt_finalizacao` | `xsd:dateTime` | true | 0..1 |
| `nm_tipo_area_regularidade_imovel` | `xsd:string` | true | 0..1 |
| `nm_tema_analise` | `xsd:string` | true | 0..1 |
| `des_condicao` | `xsd:string` | true | 0..1 |
| `num_area_passivo` | `xsd:double` | true | 0..1 |

### `pra:vw_pra_imovel_areas_fora_app`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `sei` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:long` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `nom_municipio` | `xsd:string` | true | 0..1 |
| `cod_controle` | `xsd:string` | true | 0..1 |
| `dt_emissao` | `xsd:dateTime` | true | 0..1 |
| `dt_finalizacao` | `xsd:dateTime` | true | 0..1 |
| `nm_tipo_area_regularidade_imovel` | `xsd:string` | true | 0..1 |
| `nm_tema_analise` | `xsd:string` | true | 0..1 |
| `des_condicao` | `xsd:string` | true | 0..1 |
| `num_area_passivo` | `xsd:double` | true | 0..1 |

### `pra:vw_pra_imovel_reserva_legal`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `sei` | `xsd:string` | true | 0..1 |
| `idt_imovel` | `xsd:long` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `nom_municipio` | `xsd:string` | true | 0..1 |
| `cod_controle` | `xsd:string` | true | 0..1 |
| `dt_emissao` | `xsd:dateTime` | true | 0..1 |
| `dt_finalizacao` | `xsd:dateTime` | true | 0..1 |
| `nm_tipo_area_regularidade_imovel` | `xsd:string` | true | 0..1 |
| `nm_tema_analise` | `xsd:string` | true | 0..1 |
| `des_condicao` | `xsd:string` | true | 0..1 |
| `num_area_passivo` | `xsd:double` | true | 0..1 |

## prefeitura_pvh (3)

### `prefeitura_pvh:ba_localidades_pvh`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `potenciali` | `xsd:string` | true | 0..1 |
| `acoes_prev` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:decimal` | true | 0..1 |
| `longitude` | `xsd:decimal` | true | 0..1 |

### `prefeitura_pvh:ba_localizacao_distritos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `descriptio` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |

### `prefeitura_pvh:bc_lote_geoportal_05072024`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `inscricao_` | `xsd:string` | true | 0..1 |
| `zona` | `xsd:string` | true | 0..1 |
| `setor` | `xsd:string` | true | 0..1 |
| `quadra` | `xsd:string` | true | 0..1 |
| `lote` | `xsd:string` | true | 0..1 |
| `bairro` | `xsd:string` | true | 0..1 |
| `zoneamento` | `xsd:string` | true | 0..1 |
| `area_m2` | `xsd:decimal` | true | 0..1 |

## protege (2)

### `protege:poluicao_distrito_diario`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `data_ref` | `xsd:date` | false | 1..1 |
| `cd_dist` | `xsd:string` | false | 1..1 |
| `nm_dist` | `xsd:string` | false | 1..1 |
| `cd_mun_pai` | `xsd:string` | true | 0..1 |
| `pm25_med` | `xsd:double` | true | 0..1 |
| `pm25_max` | `xsd:double` | true | 0..1 |
| `pm25_avg` | `xsd:double` | true | 0..1 |
| `pm25_p95` | `xsd:double` | true | 0..1 |
| `pm10_med` | `xsd:double` | true | 0..1 |
| `pm10_max` | `xsd:double` | true | 0..1 |
| `pm10_avg` | `xsd:double` | true | 0..1 |
| `pm10_p95` | `xsd:double` | true | 0..1 |
| `classe_conama` | `xsd:short` | true | 0..1 |
| `iqa` | `xsd:int` | true | 0..1 |
| `iqa_categoria` | `xsd:short` | true | 0..1 |
| `iqa_poluente` | `xsd:string` | true | 0..1 |
| `aod` | `xsd:double` | true | 0..1 |
| `n_pixels` | `xsd:int` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `atualizado_em` | `xsd:dateTime` | false | 1..1 |
| `geom` | `gml:MultiPolygonPropertyType` | false | 1..1 |

### `protege:poluicao_municipio_diario`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `data_ref` | `xsd:date` | false | 1..1 |
| `cd_mun` | `xsd:string` | false | 1..1 |
| `nm_mun` | `xsd:string` | false | 1..1 |
| `pm25_med` | `xsd:double` | true | 0..1 |
| `pm25_max` | `xsd:double` | true | 0..1 |
| `pm25_avg` | `xsd:double` | true | 0..1 |
| `pm25_p95` | `xsd:double` | true | 0..1 |
| `pm10_med` | `xsd:double` | true | 0..1 |
| `pm10_max` | `xsd:double` | true | 0..1 |
| `pm10_avg` | `xsd:double` | true | 0..1 |
| `pm10_p95` | `xsd:double` | true | 0..1 |
| `classe_conama` | `xsd:short` | true | 0..1 |
| `iqa` | `xsd:int` | true | 0..1 |
| `iqa_categoria` | `xsd:short` | true | 0..1 |
| `iqa_poluente` | `xsd:string` | true | 0..1 |
| `aod` | `xsd:double` | true | 0..1 |
| `n_pixels` | `xsd:int` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `atualizado_em` | `xsd:dateTime` | false | 1..1 |
| `geom` | `gml:MultiPolygonPropertyType` | false | 1..1 |

## sae (7)

### `sae:app_rev_sae_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `Cod_Imovel` | `xsd:string` | true | 0..1 |
| `hectares` | `xsd:decimal` | true | 0..1 |
| `Shape_Leng` | `xsd:decimal` | true | 0..1 |
| `Shape_Area` | `xsd:decimal` | true | 0..1 |

### `sae:app_uhe_sa_225_parte2`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `hectares` | `xsd:double` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `sae:app_uhe_sae_2025_PARTE1`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `hectares` | `xsd:double` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `sae:area_bloqueada_sae_10_2021_epsg4674`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |
| `AREA_BLOQ` | `xsd:double` | true | 0..1 |

### `sae:cota_71.30_aeromapa`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `Id` | `xsd:int` | true | 0..1 |
| `Hectares` | `xsd:double` | true | 0..1 |
| `Perimetro` | `xsd:double` | true | 0..1 |

### `sae:perimetral_usinas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `seq` | `xsd:decimal` | true | 0..1 |
| `idt_imovel` | `xsd:decimal` | true | 0..1 |
| `cod_imovel` | `xsd:string` | true | 0..1 |
| `nom_imovel` | `xsd:string` | true | 0..1 |
| `num_area_i` | `xsd:double` | true | 0..1 |
| `num_modulo` | `xsd:double` | true | 0..1 |
| `idt_munici` | `xsd:long` | true | 0..1 |
| `nom_munici` | `xsd:string` | true | 0..1 |
| `ind_status` | `xsd:string` | true | 0..1 |
| `dat_protoc` | `xsd:string` | true | 0..1 |
| `ind_tipo_i` | `xsd:string` | true | 0..1 |
| `des_acesso` | `xsd:string` | true | 0..1 |
| `id_situaca` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `idt_condic` | `xsd:long` | true | 0..1 |
| `condicao_i` | `xsd:string` | true | 0..1 |
| `cod_condic` | `xsd:string` | true | 0..1 |
| `cpf_cnpj` | `xsd:string` | true | 0..1 |
| `nome_compl` | `xsd:string` | true | 0..1 |
| `data_nasci` | `xsd:string` | true | 0..1 |
| `id_documen` | `xsd:string` | true | 0..1 |
| `nome_docum` | `xsd:string` | true | 0..1 |
| `id_tipo_do` | `xsd:string` | true | 0..1 |
| `tipo_docum` | `xsd:string` | true | 0..1 |
| `tipo_class` | `xsd:string` | true | 0..1 |
| `nome_class` | `xsd:string` | true | 0..1 |
| `des_condic` | `xsd:string` | true | 0..1 |

### `sae:REMANSO_7130_2023`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `fid_1` | `xsd:double` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `hectares` | `xsd:double` | true | 0..1 |
| `perimeter` | `xsd:double` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

## samuel (6)

### `samuel:area_declarada_utilidade_publica`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `LAYER` | `xsd:string` | true | 0..1 |
| `ELEVATION` | `xsd:int` | true | 0..1 |
| `Item` | `xsd:string` | true | 0..1 |
| `Nomenclatu` | `xsd:string` | true | 0..1 |
| `COTA` | `xsd:double` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `AREA_HA` | `xsd:string` | true | 0..1 |

### `samuel:area_total_vinculada_concessao`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `LAYER` | `xsd:string` | true | 0..1 |
| `ELEVATION` | `xsd:int` | true | 0..1 |
| `Item` | `xsd:string` | true | 0..1 |
| `Nomenclatu` | `xsd:string` | true | 0..1 |
| `COTA` | `xsd:double` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `AREA_HA` | `xsd:string` | true | 0..1 |

### `samuel:barramento`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `LAYER` | `xsd:string` | true | 0..1 |
| `ELEVATION` | `xsd:double` | true | 0..1 |
| `Item` | `xsd:string` | true | 0..1 |
| `Nomenclatu` | `xsd:string` | true | 0..1 |
| `COTA` | `xsd:double` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `AREA_HA` | `xsd:string` | true | 0..1 |

### `samuel:faixa_seguranca_barragem`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiLineStringPropertyType` | true | 0..1 |
| `LAYER` | `xsd:string` | true | 0..1 |
| `ELEVATION` | `xsd:int` | true | 0..1 |
| `Name` | `xsd:string` | true | 0..1 |

### `samuel:reservatorio_maximo_maximorum`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `LAYER` | `xsd:string` | true | 0..1 |
| `ELEVATION` | `xsd:int` | true | 0..1 |
| `Item` | `xsd:string` | true | 0..1 |
| `Nomenclatu` | `xsd:string` | true | 0..1 |
| `COTA` | `xsd:double` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `AREA_HA` | `xsd:string` | true | 0..1 |

### `samuel:reservatorio_operacional_normal`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `LAYER` | `xsd:string` | true | 0..1 |
| `ELEVATION` | `xsd:int` | true | 0..1 |
| `Item` | `xsd:string` | true | 0..1 |
| `Nomenclatu` | `xsd:string` | true | 0..1 |
| `COTA` | `xsd:double` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `AREA_HA` | `xsd:string` | true | 0..1 |

## sfb (7)

### `sfb:CNFP_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `orgao` | `xsd:string` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `estagio` | `xsd:string` | true | 0..1 |
| `governo` | `xsd:string` | true | 0..1 |
| `codigo` | `xsd:string` | true | 0..1 |
| `ano` | `xsd:long` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `protecao` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `comunitari` | `xsd:string` | true | 0..1 |
| `atolegal` | `xsd:string` | true | 0..1 |
| `anocriacao` | `xsd:long` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `observacao` | `xsd:string` | true | 0..1 |
| `sobreposic` | `xsd:string` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:long` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `sfb:CNFP_2022_RO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `governo` | `xsd:string` | true | 0..1 |
| `orgao` | `xsd:string` | true | 0..1 |
| `sobreposic` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `atolegal` | `xsd:string` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `codigo` | `xsd:string` | true | 0..1 |
| `ano` | `xsd:decimal` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `protecao` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `comunitari` | `xsd:string` | true | 0..1 |
| `anocriacao` | `xsd:decimal` | true | 0..1 |
| `observacao` | `xsd:string` | true | 0..1 |
| `objectid` | `xsd:decimal` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |
| `shape_area` | `xsd:decimal` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `estagio` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:decimal` | true | 0..1 |

### `sfb:CNFP_2024_RO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `protecao` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `governo` | `xsd:string` | true | 0..1 |
| `comunitari` | `xsd:string` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `orgao` | `xsd:string` | true | 0..1 |
| `sobreposic` | `xsd:string` | true | 0..1 |
| `atolegal` | `xsd:string` | true | 0..1 |
| `anocriacao` | `xsd:string` | true | 0..1 |
| `estagio` | `xsd:string` | true | 0..1 |
| `codigo` | `xsd:string` | true | 0..1 |
| `observacao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `geocodigo` | `xsd:long` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |

### `sfb:CNFP_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `protecao` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `governo` | `xsd:string` | true | 0..1 |
| `comunitari` | `xsd:string` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `orgao` | `xsd:string` | true | 0..1 |
| `sobreposic` | `xsd:string` | true | 0..1 |
| `atolegal` | `xsd:string` | true | 0..1 |
| `anocriacao` | `xsd:string` | true | 0..1 |
| `estagio` | `xsd:string` | true | 0..1 |
| `codigo` | `xsd:string` | true | 0..1 |
| `observacao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `geocodigo` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |

### `sfb:vw_cnfp_ro_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `orgao` | `xsd:string` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `estagio` | `xsd:string` | true | 0..1 |
| `governo` | `xsd:string` | true | 0..1 |
| `codigo` | `xsd:string` | true | 0..1 |
| `ano` | `xsd:long` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `protecao` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `comunitari` | `xsd:string` | true | 0..1 |
| `atolegal` | `xsd:string` | true | 0..1 |
| `anocriacao` | `xsd:long` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `observacao` | `xsd:string` | true | 0..1 |
| `sobreposic` | `xsd:string` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:long` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

### `sfb:vw_cnfp_ro_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `protecao` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `governo` | `xsd:string` | true | 0..1 |
| `comunitari` | `xsd:string` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `orgao` | `xsd:string` | true | 0..1 |
| `sobreposic` | `xsd:string` | true | 0..1 |
| `atolegal` | `xsd:string` | true | 0..1 |
| `anocriacao` | `xsd:string` | true | 0..1 |
| `estagio` | `xsd:string` | true | 0..1 |
| `codigo` | `xsd:string` | true | 0..1 |
| `observacao` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `geocodigo` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:double` | true | 0..1 |

### `sfb:vw_florestas_publicas_2022_ro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `governo` | `xsd:string` | true | 0..1 |
| `orgao` | `xsd:string` | true | 0..1 |
| `sobreposic` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `atolegal` | `xsd:string` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `ano` | `xsd:decimal` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `protecao` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `comunitari` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |
| `shape_area` | `xsd:decimal` | true | 0..1 |
| `bioma` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:decimal` | true | 0..1 |

## worldview (1)

### `worldview:metadata_strips`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPolygonPropertyType` | true | 0..1 |
| `catalog_id` | `xsd:string` | true | 0..1 |
| `acq_date` | `xsd:string` | true | 0..1 |
| `sensor` | `xsd:string` | true | 0..1 |
| `off_nadir` | `xsd:double` | true | 0..1 |
| `sun_elev` | `xsd:double` | true | 0..1 |
| `native_res` | `xsd:double` | true | 0..1 |
| `accuracy` | `xsd:double` | true | 0..1 |
| `proc_notes` | `xsd:string` | true | 0..1 |
| `area_ha` | `xsd:decimal` | true | 0..1 |
