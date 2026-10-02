# Prefeitura Santo André — atributos das camadas

Geoportal: [[Geosserviços/Prefeitura Santo André/Prefeitura de Santo André — SP|Prefeitura de Santo André — SP]]

Os campos abaixo vêm de `DescribeFeatureType` (XSD), sem download de feições.

## siga (176)

### `siga:SIGA_AMB_ALTIMETRIA_NORTE_5M_S`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NUM_ALTITUDE` | `xsd:decimal` | true | 0..1 |
| `NUM_CURVA_MESTRA` | `xsd:decimal` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_AMB_ALTIMETRIA_SUL_5M`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NUM_ALTITUDE` | `xsd:decimal` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_AMB_APP_LICENC_NORTE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_AMB_APP_LICENC_SUL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_AMB_APRM_B`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `APRM_BILLI` | `xsd:string` | true | 0..1 |
| `AOD` | `xsd:string` | true | 0..1 |
| `COR_MAPA` | `xsd:string` | true | 0..1 |
| `AREA_ESPEC` | `xsd:string` | true | 0..1 |
| `TRANSP` | `xsd:decimal` | true | 0..1 |
| `SHAPE_LENG` | `xsd:decimal` | true | 0..1 |
| `SHAPE_AREA` | `xsd:decimal` | true | 0..1 |
| `URL_LINK_LEGISLAC` | `xsd:string` | true | 0..1 |

### `siga:SIGA_AMB_BACIAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | true | 0..1 |
| `NOM_BACIA` | `xsd:string` | true | 0..1 |
| `UGRHIS` | `xsd:string` | true | 0..1 |
| `NOM_MACRO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_AMB_CLASSIF_VEGETAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `CODIGO` | `xsd:decimal` | true | 0..1 |
| `CLASSIFICACAO` | `xsd:string` | true | 0..1 |
| `AREA_M2` | `xsd:string` | true | 0..1 |

### `siga:SIGA_AMB_DECLIVIDADE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:string` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOM_TIPO` | `xsd:string` | true | 0..1 |

### `siga:SIGA_AMB_GEOLOGIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOM_TIPO` | `xsd:string` | true | 0..1 |

### `siga:SIGA_AMB_GEOMORFOLOGIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOM_FORMA` | `xsd:string` | true | 0..1 |

### `siga:SIGA_AMB_HIDRO_EMPLASA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `DSC_TIPO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:decimal` | false | 1..1 |

### `siga:SIGA_AMB_MACRO_BACIAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | true | 0..1 |
| `UGRHIS` | `xsd:string` | true | 0..1 |
| `NOM_MACRO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_AMB_MASSA_DAGUA_EMPLASA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `DSC_TIPO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:decimal` | false | 1..1 |

### `siga:SIGA_AMB_PARQUES_MUNICIPAIS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOM_PARQUE` | `xsd:string` | true | 0..1 |
| `DSC_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUM_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOM_BAIRRO` | `xsd:string` | true | 0..1 |
| `NUM_TELEFONE` | `xsd:string` | true | 0..1 |
| `DSC_HORARIO` | `xsd:string` | true | 0..1 |
| `COD_SETOR` | `xsd:string` | true | 0..1 |
| `COD_QUADRA` | `xsd:string` | true | 0..1 |
| `COD_LOTE` | `xsd:string` | true | 0..1 |
| `CF_SECUNDARIA` | `xsd:string` | true | 0..1 |

### `siga:SIGA_AMB_RIOS_LICENC_NORTE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_AMB_RIOS_LICENC_SUL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_AMB_SUB_BACIAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | true | 0..1 |
| `NOM_BACIA` | `xsd:string` | true | 0..1 |
| `UGRHIS` | `xsd:string` | true | 0..1 |
| `NOM_MACRO` | `xsd:string` | true | 0..1 |
| `NOM_SUB_BACIA` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_AMB_UC_EST_ALTO_PARANAP`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | true | 0..1 |
| `NOM_UNIDADE` | `xsd:string` | true | 0..1 |
| `AREA_HA` | `xsd:decimal` | true | 0..1 |
| `DSC_LEGISLACAO` | `xsd:string` | true | 0..1 |
| `DSC_PLANO_MANEJO` | `xsd:string` | true | 0..1 |
| `LINK_LEGISLACAO` | `xsd:string` | true | 0..1 |
| `TPO_UNIDADE` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_AMB_UC_EST_BARONESA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | true | 0..1 |
| `NOM_UNIDADE` | `xsd:string` | true | 0..1 |
| `AREA_HA` | `xsd:decimal` | true | 0..1 |
| `DSC_LEGISLACAO` | `xsd:string` | true | 0..1 |
| `DSC_PLANO_MANEJO` | `xsd:string` | true | 0..1 |
| `LINK_LEGISLACAO` | `xsd:string` | true | 0..1 |
| `TPO_UNIDADE` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_AMB_UC_EST_SERRA_MAR`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | true | 0..1 |
| `NOM_UNIDADE` | `xsd:string` | true | 0..1 |
| `AREA_HA` | `xsd:decimal` | true | 0..1 |
| `DSC_LEGISLACAO` | `xsd:string` | true | 0..1 |
| `DSC_PLANO_MANEJO` | `xsd:string` | true | 0..1 |
| `LINK_LEGISLACAO` | `xsd:string` | true | 0..1 |
| `TPO_UNIDADE` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_AMB_UC_MUN_NASC_PARANAP`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | true | 0..1 |
| `NOM_UNIDADE` | `xsd:string` | true | 0..1 |
| `AREA_HA` | `xsd:decimal` | true | 0..1 |
| `DSC_LEGISLACAO` | `xsd:string` | true | 0..1 |
| `DSC_PLANO_MANEJO` | `xsd:string` | true | 0..1 |
| `LINK_LEGISLACAO` | `xsd:string` | true | 0..1 |
| `TPO_UNIDADE` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_AMB_UC_MUN_PED_ZON_INTER`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | true | 0..1 |
| `NOM_ZONEAMENTO` | `xsd:string` | true | 0..1 |
| `NOM_SUB_ZONEAMENTO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_AMB_UC_MUN_PEDROSO_AMORT`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NOM_CLASSE` | `xsd:string` | true | 0..1 |
| `DSC_DETALHAMENTO` | `xsd:string` | true | 0..1 |
| `DSC_DIRETRIZES` | `xsd:string` | true | 0..1 |
| `LINK_PLANO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_AMB_UC_MUN_PEDROSO_BACIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | true | 0..1 |
| `DSC_COMPARTIMENTO` | `xsd:string` | true | 0..1 |
| `DSC_DRENAGEM` | `xsd:string` | true | 0..1 |
| `DSC_IDENTIFICACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_AMB_UC_MUN_PEDROSO_LIM`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | true | 0..1 |
| `NOM_UNIDADE` | `xsd:string` | true | 0..1 |
| `DSC_CATEGORIA` | `xsd:string` | true | 0..1 |
| `DSC_LEGISLACAO` | `xsd:string` | true | 0..1 |
| `LINK_LEGISLACAO` | `xsd:string` | true | 0..1 |
| `DSC_PLANO_MANEJO_V1` | `xsd:string` | true | 0..1 |
| `DSC_PLANO_MANEJO_V2` | `xsd:string` | true | 0..1 |
| `LINK_SNUC` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_AMB_UGRHIS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | true | 0..1 |
| `UGRHIS` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_AS_ABRANG_ATEND_MULHER`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `BAIRROS` | `xsd:string` | true | 0..1 |
| `UNIDADE` | `xsd:string` | true | 0..1 |

### `siga:SIGA_AS_ABRANG_CRAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `UNIDADE` | `xsd:string` | true | 0..1 |
| `BAIRROS` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_AS_ABRANG_ESP_ASS_SOCIAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `UNIDADE` | `xsd:string` | true | 0..1 |
| `BAIRROS` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_AS_ABRANG_ESP_POP_RUA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `UNIDADE` | `xsd:string` | true | 0..1 |
| `BAIRROS` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_AS_ABRANG_REF_IDOSO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `UNIDADE` | `xsd:string` | true | 0..1 |
| `BAIRROS` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_AS_C_CONVIVENCIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `EMAIL` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `DESCRICAO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ABRANGENCIA` | `xsd:string` | true | 0..1 |
| `LINK_IMAGEM` | `xsd:string` | true | 0..1 |
| `COD_SETOR` | `xsd:string` | true | 0..1 |
| `COD_QUADRA` | `xsd:string` | true | 0..1 |
| `COD_LOTE` | `xsd:string` | true | 0..1 |

### `siga:SIGA_AS_CESP_ATEND_MULHER`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `EMAIL` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `DESCRICAO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `COD_SETOR` | `xsd:string` | true | 0..1 |
| `COD_QUADRA` | `xsd:string` | true | 0..1 |
| `COD_LOTE` | `xsd:string` | true | 0..1 |

### `siga:SIGA_AS_CESP_ESP_ASS_SOCIAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `EMAIL` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `DESCRICAO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `COD_SETOR` | `xsd:string` | true | 0..1 |
| `COD_QUADRA` | `xsd:string` | true | 0..1 |
| `COD_LOTE` | `xsd:string` | true | 0..1 |

### `siga:SIGA_AS_CESP_POP_RUA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `EMAIL` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `DESCRICAO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `COD_SETOR` | `xsd:string` | true | 0..1 |
| `COD_QUADRA` | `xsd:string` | true | 0..1 |
| `COD_LOTE` | `xsd:string` | true | 0..1 |

### `siga:SIGA_AS_CESP_REF_IDOSO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `EMAIL` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `DESCRICAO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `COD_SETOR` | `xsd:string` | true | 0..1 |
| `COD_QUADRA` | `xsd:string` | true | 0..1 |
| `COD_LOTE` | `xsd:string` | true | 0..1 |

### `siga:SIGA_AS_CRAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `EMAIL` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `DESCRICAO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `COD_SETOR` | `xsd:string` | true | 0..1 |
| `COD_QUADRA` | `xsd:string` | true | 0..1 |
| `COD_LOTE` | `xsd:string` | true | 0..1 |

### `siga:SIGA_AS_PROG_ATEND_PSICOSSOC`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `EMAIL` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `DESCRICAO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ABRANGENCIA` | `xsd:string` | true | 0..1 |
| `LINK_IMAGEM` | `xsd:string` | true | 0..1 |
| `COD_SETOR` | `xsd:string` | true | 0..1 |
| `COD_QUADRA` | `xsd:string` | true | 0..1 |
| `COD_LOTE` | `xsd:string` | true | 0..1 |

### `siga:SIGA_AS_SERV_ESP_ABORD_SOCIAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `EMAIL` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `DESCRICAO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ABRANGENCIA` | `xsd:string` | true | 0..1 |
| `LINK_IMAGEM` | `xsd:string` | true | 0..1 |
| `COD_SETOR` | `xsd:string` | true | 0..1 |
| `COD_QUADRA` | `xsd:string` | true | 0..1 |
| `COD_LOTE` | `xsd:string` | true | 0..1 |

### `siga:SIGA_ASO_IND_VULNERAB_SOCIAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `CODIGO_SETOR_CENSITARIO` | `xsd:string` | true | 0..1 |
| `AREA_KM2_SETOR_CENSITARIO` | `xsd:decimal` | true | 0..1 |
| `BAIRRO_AREA_CENSITARIA` | `xsd:string` | true | 0..1 |
| `IND_IVS_1_SEM_2025` | `xsd:decimal` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_CON_TUTELAR`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `EMAIL` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `DESCRICAO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `COD_SETOR` | `xsd:string` | true | 0..1 |
| `COD_QUADRA` | `xsd:string` | true | 0..1 |
| `COD_LOTE` | `xsd:string` | true | 0..1 |

### `siga:SIGA_CON_TUTELAR_ABRANGENCIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `UNIDADE` | `xsd:string` | true | 0..1 |
| `BAIRROS` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_CRA_FEIRAS_LIVRES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `DSC_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `DSC_OBSERVACAO` | `xsd:string` | true | 0..1 |
| `DSC_DIA` | `xsd:string` | true | 0..1 |
| `DSC_PERIODO` | `xsd:string` | true | 0..1 |
| `DSC_HORARIO` | `xsd:string` | true | 0..1 |
| `DSC_HORARIO_INTERDICAO` | `xsd:string` | true | 0..1 |
| `QTD_BARRACAS` | `xsd:decimal` | true | 0..1 |
| `DSC_SITE` | `xsd:string` | true | 0..1 |
| `DSC_ARQUIVO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `COD_BAIRRO` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_CUL_AUDITORIO_TEATRO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO_NOME` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `EMAIL` | `xsd:string` | true | 0..1 |
| `DESCRICAO` | `xsd:string` | true | 0..1 |
| `OBS` | `xsd:string` | true | 0..1 |
| `SITE1` | `xsd:string` | true | 0..1 |
| `SITE2` | `xsd:string` | true | 0..1 |
| `COD_SETOR` | `xsd:decimal` | true | 0..1 |
| `COD_QUADRA` | `xsd:decimal` | true | 0..1 |
| `COD_LOTE` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_CUL_BENS_REGISTRADOS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | true | 0..1 |
| `DSC_DENOMINACAO` | `xsd:string` | true | 0..1 |
| `DSC_ENDERECO` | `xsd:string` | true | 0..1 |
| `CLASS_FISCAL` | `xsd:string` | true | 0..1 |
| `DSC_INFO` | `xsd:string` | true | 0..1 |
| `DSC_LINK` | `xsd:string` | true | 0..1 |
| `DSC_TIPOLOGIA` | `xsd:string` | true | 0..1 |
| `DSC_SOLICITACAO` | `xsd:string` | true | 0..1 |
| `NUM_PROCESSO` | `xsd:string` | true | 0..1 |
| `DTA_REGISTRO` | `xsd:string` | true | 0..1 |
| `DTA_HOMOLOGACAO` | `xsd:string` | true | 0..1 |
| `NOM_ORGAO` | `xsd:string` | true | 0..1 |
| `DSC_OFICIALIZACAO` | `xsd:string` | true | 0..1 |
| `INSTITUICAO_REGISTRO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_CUL_BENS_TOMBADOS_CULT`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `DSC_DENOMINACAO` | `xsd:string` | true | 0..1 |
| `DSC_ENDERECO` | `xsd:string` | true | 0..1 |
| `NOM_BAIRRO` | `xsd:string` | true | 0..1 |
| `CLASS_FISCAL` | `xsd:string` | true | 0..1 |
| `DSC_INFORMACAO` | `xsd:string` | true | 0..1 |
| `DSC_PROPRIEDADE` | `xsd:string` | true | 0..1 |
| `DSC_USO_ATUAL` | `xsd:string` | true | 0..1 |
| `DSC_USO_ANTERIOR` | `xsd:string` | true | 0..1 |
| `DSC_SOLICITACAO` | `xsd:string` | true | 0..1 |
| `NUM_PROCESSO` | `xsd:string` | true | 0..1 |
| `DTA_TOMBO` | `xsd:string` | true | 0..1 |
| `DTA_HOMOLOG` | `xsd:string` | true | 0..1 |
| `NOM_ORGAO` | `xsd:string` | true | 0..1 |
| `DSC_OFICIALIZACAO` | `xsd:string` | true | 0..1 |
| `DSC_AREA_ENVOL` | `xsd:string` | true | 0..1 |
| `IND_ACESSO` | `xsd:string` | true | 0..1 |
| `DSC_LINK` | `xsd:string` | true | 0..1 |
| `INSTANCIA` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_CUL_BIBLIOTECA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO_NOME` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `EMAIL` | `xsd:string` | true | 0..1 |
| `DESCRICAO` | `xsd:string` | true | 0..1 |
| `OBS` | `xsd:string` | true | 0..1 |
| `SITE1` | `xsd:string` | true | 0..1 |
| `SITE2` | `xsd:string` | true | 0..1 |
| `COD_SETOR` | `xsd:string` | true | 0..1 |
| `COD_QUADRA` | `xsd:string` | true | 0..1 |
| `COD_LOTE` | `xsd:string` | true | 0..1 |

### `siga:SIGA_CUL_CENTRO_CULTURAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO_NOME` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `EMAIL` | `xsd:string` | true | 0..1 |
| `DESCRICAO` | `xsd:string` | true | 0..1 |
| `OBS` | `xsd:string` | true | 0..1 |
| `SITE1` | `xsd:string` | true | 0..1 |
| `SITE2` | `xsd:string` | true | 0..1 |
| `COD_SETOR` | `xsd:string` | true | 0..1 |
| `COD_QUADRA` | `xsd:string` | true | 0..1 |
| `COD_LOTE` | `xsd:string` | true | 0..1 |

### `siga:SIGA_CUL_CEU`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO_NOME` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `EMAIL` | `xsd:string` | true | 0..1 |
| `DESCRICAO` | `xsd:string` | true | 0..1 |
| `OBS` | `xsd:string` | true | 0..1 |
| `SITE1` | `xsd:string` | true | 0..1 |
| `SITE2` | `xsd:string` | true | 0..1 |
| `COD_SETOR` | `xsd:string` | true | 0..1 |
| `COD_QUADRA` | `xsd:string` | true | 0..1 |
| `COD_LOTE` | `xsd:string` | true | 0..1 |

### `siga:SIGA_CUL_EMIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO_NOME` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `EMAIL` | `xsd:string` | true | 0..1 |
| `DESCRICAO` | `xsd:string` | true | 0..1 |
| `OBS` | `xsd:string` | true | 0..1 |
| `SITE1` | `xsd:string` | true | 0..1 |
| `SITE2` | `xsd:string` | true | 0..1 |
| `COD_SETOR` | `xsd:string` | true | 0..1 |
| `COD_QUADRA` | `xsd:string` | true | 0..1 |
| `COD_LOTE` | `xsd:string` | true | 0..1 |

### `siga:SIGA_CUL_ESCOLA_LIVRE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO_NOME` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `EMAIL` | `xsd:string` | true | 0..1 |
| `DESCRICAO` | `xsd:string` | true | 0..1 |
| `OBS` | `xsd:string` | true | 0..1 |
| `SITE1` | `xsd:string` | true | 0..1 |
| `SITE2` | `xsd:string` | true | 0..1 |
| `COD_SETOR` | `xsd:string` | true | 0..1 |
| `COD_QUADRA` | `xsd:string` | true | 0..1 |
| `COD_LOTE` | `xsd:string` | true | 0..1 |

### `siga:SIGA_CUL_ESPACO_EXPOSITIVO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO_NOME` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `EMAIL` | `xsd:string` | true | 0..1 |
| `DESCRICAO` | `xsd:string` | true | 0..1 |
| `OBS` | `xsd:string` | true | 0..1 |
| `SITE1` | `xsd:string` | true | 0..1 |
| `SITE2` | `xsd:string` | true | 0..1 |
| `COD_SETOR` | `xsd:string` | true | 0..1 |
| `COD_QUADRA` | `xsd:string` | true | 0..1 |
| `COD_LOTE` | `xsd:string` | true | 0..1 |

### `siga:SIGA_CUL_TERRITORIOS_CULTURAIS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | true | 0..1 |
| `NUM_REGIAO` | `xsd:decimal` | true | 0..1 |
| `NOM_BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_DCI_ATEND_EMERGENCIAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `SITE` | `xsd:string` | true | 0..1 |
| `COD_SETOR` | `xsd:decimal` | true | 0..1 |
| `COD_QUADRA` | `xsd:decimal` | true | 0..1 |
| `COD_LOTE` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_DCI_EST_METEOROLOGICAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | true | 0..1 |
| `EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `LINK_ACESSO` | `xsd:string` | true | 0..1 |
| `COD_SETOR` | `xsd:string` | true | 0..1 |
| `COD_QUADRA` | `xsd:string` | true | 0..1 |
| `COD_LOTE` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_DCI_PLUVIOMETROS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `LINK_ACESSO` | `xsd:string` | true | 0..1 |
| `COD_SETOR` | `xsd:string` | true | 0..1 |
| `COD_QUADRA` | `xsd:string` | true | 0..1 |
| `COD_LOTE` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_DEFIS_ENTIDADES_CONVENIAD`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NOM_ENTIDADE` | `xsd:string` | true | 0..1 |
| `NUM_TELEFONE` | `xsd:string` | true | 0..1 |
| `DSC_EMAIL` | `xsd:string` | true | 0..1 |
| `DSC_SITE` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_DEFIS_EQUIPAMENTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NOM_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `DSC_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `DSC_ENDERECO` | `xsd:string` | true | 0..1 |
| `NOM_BAIRRO` | `xsd:string` | true | 0..1 |
| `NUM_TELEFONES` | `xsd:string` | true | 0..1 |
| `DSC_HORARIO_ATENDIM` | `xsd:string` | true | 0..1 |
| `DSC_EMAIL` | `xsd:string` | true | 0..1 |
| `DSC_LEGISLACAO` | `xsd:string` | true | 0..1 |
| `DSC_REQUISITOS` | `xsd:string` | true | 0..1 |
| `URL_FORM_CADASTRO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_DMV_AMIGOS_PRACA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `CODIGO` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `OBSERVACAO` | `xsd:string` | true | 0..1 |

### `siga:SIGA_DMV_SETOR_ROCAGEM`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `REGIAO` | `xsd:string` | true | 0..1 |
| `BAIRROS` | `xsd:string` | true | 0..1 |

### `siga:SIGA_EDU_CESA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NOM_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `NUM_TELEFONE` | `xsd:string` | true | 0..1 |
| `DSC_EMAIL` | `xsd:string` | true | 0..1 |
| `SEG` | `xsd:string` | true | 0..1 |
| `TER` | `xsd:string` | true | 0..1 |
| `QUA` | `xsd:string` | true | 0..1 |
| `QUI` | `xsd:string` | true | 0..1 |
| `SEX` | `xsd:string` | true | 0..1 |
| `SAB` | `xsd:string` | true | 0..1 |
| `DOM` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_EDU_COMPLEXO_EDUCACIONAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | true | 0..1 |
| `NOM_COMPLEXO` | `xsd:string` | true | 0..1 |
| `NOM_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUM_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `COD_SETOR` | `xsd:decimal` | true | 0..1 |
| `COD_QUADRA` | `xsd:decimal` | true | 0..1 |
| `COD_LOTE` | `xsd:decimal` | true | 0..1 |
| `EQUIPAMENTOS` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_EDU_CPFP`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `EMAIL` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_EDU_CRECHE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NOM_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `NUM_TELEFONE` | `xsd:string` | true | 0..1 |
| `DSC_EMAIL` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `NUM_CAPACID_TOTAL` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_EDU_CRECHE_SUBVENCIONADA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NOM_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `NUM_TELEFONE` | `xsd:string` | true | 0..1 |
| `DSC_EMAIL` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOM_BAIRRO` | `xsd:string` | true | 0..1 |
| `NUM_CAPACID_TOTAL` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_EDU_DIRETORIA_ENSINO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NOM_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `NUM_LOGRADOURO` | `xsd:decimal` | true | 0..1 |
| `NOM_BAIRRO` | `xsd:string` | true | 0..1 |
| `NUM_TELEFONE` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_EDU_EMEI`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NOM_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `NUM_TELEFONE` | `xsd:string` | true | 0..1 |
| `DSC_EMAIL` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NUM_CAPACID_TOTAL` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_EDU_EMEIEF`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NOM_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `NUM_TELEFONE` | `xsd:string` | true | 0..1 |
| `DSC_EMAIL` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NUM_PRE_CAPACID_TOTAL` | `xsd:decimal` | true | 0..1 |
| `NUM_FUND_1_CAPAC_TOTAL` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_EDU_ENSINO_SUPERIOR`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `COD_IE` | `xsd:decimal` | true | 0..1 |
| `NOM_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `NOM_SIGLA` | `xsd:string` | true | 0..1 |
| `NOM_LOG` | `xsd:string` | true | 0..1 |
| `NUM_LOGRADOURO` | `xsd:decimal` | true | 0..1 |
| `DSC_COMPL` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `DSC_CATEGORIA` | `xsd:string` | true | 0..1 |
| `DSC_EMEC` | `xsd:string` | true | 0..1 |
| `NUM_TELEFONE` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_EDU_ESCOLA_PARQUE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NOM_EDUCACAO` | `xsd:string` | true | 0..1 |
| `DSC_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUM_LOGRADOURO` | `xsd:decimal` | true | 0..1 |
| `DSC_LOCAL` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `DSC_FUNCION_SEG` | `xsd:string` | true | 0..1 |
| `DSC_FUNCION_TER_SEX` | `xsd:string` | true | 0..1 |
| `DSC_FUNCION_SAB_DOM` | `xsd:string` | true | 0..1 |
| `COD_SETOR` | `xsd:decimal` | true | 0..1 |
| `COD_QUADRA` | `xsd:decimal` | true | 0..1 |
| `COD_LOTE` | `xsd:decimal` | true | 0..1 |
| `DSC_CLASSIF_SECUNDARIA` | `xsd:string` | true | 0..1 |
| `EQUIPAMENTOS` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_EDU_ESTADUAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NUM_CIE` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOM_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `NOM_BAIRRO` | `xsd:string` | true | 0..1 |
| `TIPO_ENSINO` | `xsd:string` | true | 0..1 |
| `NUM_TELEFONE` | `xsd:string` | true | 0..1 |

### `siga:SIGA_EDU_MUNICIPAL_EJA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOM_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `NOM_BAIRRO` | `xsd:string` | true | 0..1 |
| `NUM_TELEFONE` | `xsd:string` | true | 0..1 |
| `DSC_EMAIL` | `xsd:string` | true | 0..1 |
| `NUM_CLASSES` | `xsd:decimal` | true | 0..1 |
| `NUM_CAPACID_CLASSE` | `xsd:decimal` | true | 0..1 |
| `NUM_CAPACID_TOTAL` | `xsd:decimal` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `TIPO_ENSINO` | `xsd:string` | true | 0..1 |
| `TIPO_EQUIPAMENTO` | `xsd:string` | true | 0..1 |

### `siga:SIGA_EDU_PARTICULAR`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NOM_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `NOM_BAIRRO` | `xsd:string` | true | 0..1 |
| `TIPO_ENSINO` | `xsd:string` | true | 0..1 |
| `NUM_TELEFONE` | `xsd:string` | true | 0..1 |
| `DSC_EMAIL` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_EDU_PROJETO_ESPECIAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NOM_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `NUM_TELEFONE` | `xsd:string` | true | 0..1 |
| `DSC_EMAIL` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_EDU_SECRETARIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NOM_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `NUM_TELEFONE` | `xsd:string` | true | 0..1 |
| `DSC_EMAIL` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_ESP_CAMPOS_DISTRITAIS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `DOMINIO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `OBSERVACAO` | `xsd:string` | true | 0..1 |
| `COD_SETOR` | `xsd:string` | true | 0..1 |
| `COD_QUADRA` | `xsd:string` | true | 0..1 |
| `COD_LOTE` | `xsd:string` | true | 0..1 |
| `COD_LOGRADOURO` | `xsd:decimal` | true | 0..1 |
| `NUM_LOGRADOURO` | `xsd:decimal` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_ESP_EQUIPAMENTO_ESPORTE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `DOMINIO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `NOM_BAIRRO` | `xsd:string` | true | 0..1 |
| `NUM_TELEFONE` | `xsd:string` | true | 0..1 |
| `DSC_EMAIL` | `xsd:string` | true | 0..1 |
| `DSC_LATITUDE` | `xsd:string` | true | 0..1 |
| `DSC_LONGITUDE` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_HAB_EMPREED_HABITACIONAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `SITUACAO` | `xsd:string` | true | 0..1 |
| `TOTAL_UNID_HABITACIONAL` | `xsd:decimal` | true | 0..1 |
| `COD_BAIRRO` | `xsd:decimal` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_HAB_NUM_MAX_PAV_HIS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NUM_PAVIMENTO` | `xsd:string` | true | 0..1 |
| `URL_LEGISLACAO` | `xsd:string` | true | 0..1 |

### `siga:SIGA_LIM_BAIRROS_OFICIAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `HISTORIA` | `xsd:string` | true | 0..1 |
| `LEGISLACAO` | `xsd:string` | true | 0..1 |
| `AREA` | `xsd:decimal` | true | 0..1 |
| `CODIGO_BAIRRO` | `xsd:decimal` | true | 0..1 |
| `NUM_LEI` | `xsd:decimal` | true | 0..1 |
| `POPULACAO_2022` | `xsd:decimal` | true | 0..1 |
| `LATITUDE` | `xsd:string` | true | 0..1 |
| `LONGITUDE` | `xsd:string` | true | 0..1 |

### `siga:SIGA_LIM_BILLINGS_COTA_747`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `DSC_COMPARTIMENTO` | `xsd:string` | true | 0..1 |

### `siga:SIGA_LIM_DISTRITO_SUBDISTRITO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `COD_DISTRITO` | `xsd:string` | true | 0..1 |
| `NOM_DISTRITO` | `xsd:string` | true | 0..1 |
| `DSC_SUBDISTRITO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_LIM_MACROZONEAMENTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `LEGISLACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_LIM_MARCO_ZERO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `LATITUDE` | `xsd:string` | true | 0..1 |
| `LONGITUDE` | `xsd:string` | true | 0..1 |
| `ALTITUDE` | `xsd:string` | true | 0..1 |
| `LEGISLACAO` | `xsd:string` | true | 0..1 |
| `LINK_IMAGEM` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_LIM_MUNICIPAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `AREA` | `xsd:string` | true | 0..1 |
| `HISTORIA` | `xsd:string` | true | 0..1 |
| `LEGISLACAO` | `xsd:string` | true | 0..1 |
| `POPULACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_LIM_PARQUE_ANDREENSE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `LEGISLACAO` | `xsd:string` | true | 0..1 |
| `LINK` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_LIM_ZONEAMENTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NOM_ZONEAMENTO` | `xsd:string` | true | 0..1 |
| `DSC_MACRO` | `xsd:string` | true | 0..1 |
| `LEGISLACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_MUR_BUS_INTERMUNICIPAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:string` | true | 0..1 |
| `SENTIDO` | `xsd:string` | true | 0..1 |

### `siga:SIGA_MUR_BUS_MUNICIPAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `LINHA` | `xsd:string` | true | 0..1 |
| `SENTIDO` | `xsd:string` | true | 0..1 |
| `INTERVALO` | `xsd:decimal` | true | 0..1 |
| `PRIMEIRA_VIAGEM` | `xsd:string` | true | 0..1 |
| `ULTIMA_VIAGEM` | `xsd:string` | true | 0..1 |
| `OPERA_DIA_UTIL` | `xsd:string` | true | 0..1 |
| `OPERA_SABADO` | `xsd:string` | true | 0..1 |
| `OPERA_DOMINGO` | `xsd:string` | true | 0..1 |

### `siga:SIGA_MUR_CONTAG_VEICULAR`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `POSTOS` | `xsd:string` | true | 0..1 |
| `LOCAL` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `TOTAL_AUTOMOVEL` | `xsd:decimal` | true | 0..1 |
| `TOTAL_MOTOS` | `xsd:decimal` | true | 0..1 |
| `TOTAL_CAMINHOES` | `xsd:decimal` | true | 0..1 |
| `TOTAL_BICICLETA` | `xsd:decimal` | true | 0..1 |
| `TOTAL` | `xsd:decimal` | true | 0..1 |
| `PERIODO` | `xsd:string` | true | 0..1 |
| `LINK_PLANILHA` | `xsd:string` | true | 0..1 |
| `TOTAL_ONIBUS` | `xsd:decimal` | true | 0..1 |
| `DATA_ATUALIZACAO` | `xsd:string` | true | 0..1 |

### `siga:SIGA_MUR_CORREDOR_METROP_ABD`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `SENTIDO` | `xsd:string` | true | 0..1 |
| `NUMERO_LINHAS` | `xsd:string` | true | 0..1 |
| `NOME_LINHAS` | `xsd:string` | true | 0..1 |
| `LINK_SITE` | `xsd:string` | true | 0..1 |
| `LINK_SITE_MAPA` | `xsd:string` | true | 0..1 |

### `siga:SIGA_MUR_CORREDORES_TRANSP`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOM_TRECHO` | `xsd:string` | true | 0..1 |
| `NUM_EXTENSAO` | `xsd:decimal` | true | 0..1 |
| `DSC_TIPO` | `xsd:string` | true | 0..1 |
| `DSC_VELOCIDADE` | `xsd:string` | true | 0..1 |
| `DSC_COMPARTILHA` | `xsd:string` | true | 0..1 |
| `DSC_FUNC_SEMANA` | `xsd:string` | true | 0..1 |
| `DSC_FUNC_SABADO` | `xsd:string` | true | 0..1 |

### `siga:SIGA_MUR_FERROVIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOM_FERROVIA` | `xsd:string` | true | 0..1 |
| `NOM_SIGLA` | `xsd:string` | true | 0..1 |
| `NOM_LINHA` | `xsd:string` | true | 0..1 |

### `siga:SIGA_MUR_FERROVIA_ESTACOES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NOM_FERROVIA` | `xsd:string` | true | 0..1 |
| `NOM_ESTACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_MUR_LINHA_TURQUESA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NOM_LINHA` | `xsd:string` | true | 0..1 |
| `NUM_LINHA` | `xsd:decimal` | true | 0..1 |
| `NOM_EMPRESA` | `xsd:string` | true | 0..1 |
| `DSC_LINK` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_MUR_LINHA_TURQUESA_ESTAC`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NOM_ESTACAO` | `xsd:string` | true | 0..1 |
| `DSC_SENTIDO` | `xsd:string` | true | 0..1 |
| `DSC_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUM_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `DTA_CRIACAO` | `xsd:dateTime` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_MUR_PASV`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `DSC_LEGISLACAO` | `xsd:string` | true | 0..1 |
| `DSC_LINK` | `xsd:string` | true | 0..1 |
| `DSC_FAIXA` | `xsd:string` | true | 0..1 |

### `siga:SIGA_MUR_PONTO_RECARGA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOM_PONTO` | `xsd:string` | true | 0..1 |
| `DSC_ENDERECO` | `xsd:string` | true | 0..1 |
| `NUM_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `DSC_FUNCIONAMENTO` | `xsd:string` | true | 0..1 |

### `siga:SIGA_MUR_PTO_BUS_INTERMUNICIP`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `LINHAS` | `xsd:string` | true | 0..1 |
| `LINHAS_INTERMUNIC` | `xsd:string` | true | 0..1 |
| `LINHAS_MUNIC` | `xsd:string` | true | 0..1 |

### `siga:SIGA_MUR_PTO_BUS_MUNICIPAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `LINHAS` | `xsd:string` | true | 0..1 |
| `LINHAS_MUNIC` | `xsd:string` | true | 0..1 |
| `LINHAS_INTERMUNIC` | `xsd:string` | true | 0..1 |

### `siga:SIGA_MUR_PTO_TAXI`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `PONTO` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |

### `siga:SIGA_MUR_RADARES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `DSC_TIPO` | `xsd:string` | true | 0..1 |
| `DSC_ESPECIE` | `xsd:string` | true | 0..1 |
| `MAX_KM_HORA` | `xsd:string` | true | 0..1 |
| `NUM_REG_IMMETRO` | `xsd:string` | true | 0..1 |
| `NUM_SERIE_FABR` | `xsd:string` | true | 0..1 |
| `DSC_LOCAL` | `xsd:string` | true | 0..1 |
| `IND_SITUACAO` | `xsd:string` | true | 0..1 |
| `DTA_INSTALACAO` | `xsd:dateTime` | true | 0..1 |
| `DSC_SENTIDO` | `xsd:string` | true | 0..1 |
| `DSC_LATITUDE` | `xsd:string` | true | 0..1 |
| `DSC_LONGITUDE` | `xsd:string` | true | 0..1 |
| `DSC_SITE` | `xsd:string` | true | 0..1 |
| `NUM_INTERNO` | `xsd:decimal` | true | 0..1 |
| `DSC_TPO_CAMERA` | `xsd:string` | true | 0..1 |
| `DSC_MARCA` | `xsd:string` | true | 0..1 |
| `DSC_MODELO` | `xsd:string` | true | 0..1 |
| `DSC_TPO_FISCALIZACAO` | `xsd:string` | true | 0..1 |
| `DSC_ABRANGENCIA` | `xsd:string` | true | 0..1 |

### `siga:SIGA_MUR_SEMAFORO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NUM_CRUZAMENTO` | `xsd:string` | true | 0..1 |
| `NUM_CONTROLADOR` | `xsd:string` | true | 0..1 |
| `MANUTENCAO_SEMAFORO` | `xsd:string` | true | 0..1 |
| `MANUTENCAO_CONTROLADOR` | `xsd:string` | true | 0..1 |
| `CONTROLE_PROGRAMACAO` | `xsd:string` | true | 0..1 |
| `CONTROLE_CENTRAL` | `xsd:string` | true | 0..1 |
| `TEMPO_REAL` | `xsd:string` | true | 0..1 |
| `TIPO_CONTROLADOR` | `xsd:string` | true | 0..1 |
| `ENDERECO1` | `xsd:string` | true | 0..1 |
| `ENDERECO2` | `xsd:string` | true | 0..1 |
| `LAMPADA` | `xsd:string` | true | 0..1 |
| `FOCO_VEICULAR` | `xsd:string` | true | 0..1 |
| `FOCO_PEDESTRE` | `xsd:string` | true | 0..1 |
| `ROTA` | `xsd:string` | true | 0..1 |
| `SINCRONISMO` | `xsd:string` | true | 0..1 |
| `IND_INTELIGENTE` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_MUR_SIS_CICLOVIARIO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `DSC_LOCAL` | `xsd:string` | true | 0..1 |

### `siga:SIGA_MUR_TERMINAIS_BUS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `LINHAS_MUNICIPAIS` | `xsd:string` | true | 0..1 |
| `LINHAS_INTERMUNICIPAIS` | `xsd:string` | true | 0..1 |

### `siga:SIGA_MUR_TRAVESSIAS_ELEVADAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `DSC_ENDERECO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_MUR_TROLEBUS_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:string` | true | 0..1 |
| `SENTIDO` | `xsd:string` | true | 0..1 |

### `siga:SIGA_MUR_TROLEBUS_LINHA_PARADA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `PARADA` | `xsd:string` | true | 0..1 |
| `NUMERO_LINHAS` | `xsd:string` | true | 0..1 |
| `LINHAS` | `xsd:string` | true | 0..1 |
| `LINK_SITE` | `xsd:string` | true | 0..1 |
| `SENTIDO` | `xsd:string` | true | 0..1 |
| `CODIGO` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_NIS_ESCOLA_OURO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `DSC_LOCAL` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `NOM_BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_PLA_BANCA_JORNAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NOM_PONTO` | `xsd:string` | true | 0..1 |
| `DSC_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUM_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOM_BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_PLA_EIV`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `COD_SETOR` | `xsd:decimal` | true | 0..1 |
| `COD_QUADRA` | `xsd:decimal` | true | 0..1 |
| `COD_LOTE` | `xsd:decimal` | true | 0..1 |
| `DTA_PROTOCOLO` | `xsd:dateTime` | true | 0..1 |
| `DSC_INTERESSADO` | `xsd:string` | true | 0..1 |
| `TPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOM_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUM_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOM_BAIRRO` | `xsd:string` | true | 0..1 |
| `DSC_USO` | `xsd:string` | true | 0..1 |
| `DSC_ATIVIDADE` | `xsd:string` | true | 0..1 |
| `DSC_TIPOLOGIA` | `xsd:string` | true | 0..1 |
| `DSC_STATUS` | `xsd:string` | true | 0..1 |
| `NUM_AREA_LOTE` | `xsd:string` | true | 0..1 |
| `NUM_AREA_CONSTRUIDA` | `xsd:string` | true | 0..1 |
| `NUM_PAVIMENTO` | `xsd:string` | true | 0..1 |
| `NUM_PROCESSO` | `xsd:decimal` | true | 0..1 |
| `NUM_ANO_PROCESSO` | `xsd:decimal` | true | 0..1 |
| `NUM_UNIDADE` | `xsd:string` | true | 0..1 |
| `NUM_VAGA` | `xsd:string` | true | 0..1 |
| `DSC_PARECER` | `xsd:string` | true | 0..1 |
| `URL_EIV` | `xsd:string` | true | 0..1 |
| `URL_RIT` | `xsd:string` | true | 0..1 |
| `DSC_CLASS_FISCAL_SEC` | `xsd:string` | true | 0..1 |

### `siga:SIGA_PLA_LEG_EIXO_TAMANDUATEI`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `LEGISLACAO` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `LINK` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_PLA_LEG_SETOR_TAMANDUATEI`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NOM_SETOR` | `xsd:string` | true | 0..1 |
| `NOM_SUBSETOR` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_PLA_LEGIS_ZEIP_PARANAP`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `NOM_SETOR` | `xsd:string` | true | 0..1 |
| `NUM_AREA` | `xsd:decimal` | true | 0..1 |
| `NUM_PERIMETRO` | `xsd:decimal` | true | 0..1 |
| `DSC_LEGISLACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `LEGISLACAO` | `xsd:string` | true | 0..1 |

### `siga:SIGA_PLA_LEGISLACAO_ZEBT`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `LEGISLACAO` | `xsd:string` | true | 0..1 |

### `siga:SIGA_PLA_LEGISLACAO_ZEIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `LEGISLACAO` | `xsd:string` | true | 0..1 |

### `siga:SIGA_PLA_LEGISLACAO_ZEIC`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `LEGISLACAO` | `xsd:string` | true | 0..1 |

### `siga:SIGA_PLA_LEGISLACAO_ZEIP`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `LEGISLACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NUM_LEGISLACAO` | `xsd:string` | true | 0..1 |

### `siga:SIGA_PLA_LEGISLACAO_ZEIS_A`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `CODIGO` | `xsd:decimal` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `LEGISLACAO` | `xsd:string` | true | 0..1 |
| `DSC_OBS` | `xsd:string` | true | 0..1 |
| `DSC_CF` | `xsd:string` | true | 0..1 |
| `LINK_LEGISLACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_PLA_LEGISLACAO_ZEIS_B_C_D`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | true | 0..1 |
| `CODIGO` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `LEGISLACAO` | `xsd:string` | true | 0..1 |
| `LINK_LEGISLACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_PLA_METAS_2021_24_ASSOC_SEPE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `META` | `xsd:string` | true | 0..1 |
| `PROJETO` | `xsd:string` | true | 0..1 |
| `SECRETARIA` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `VALOR_PREVISTO` | `xsd:string` | true | 0..1 |
| `ODS_RELACIONADA` | `xsd:string` | true | 0..1 |
| `STATUS` | `xsd:string` | true | 0..1 |
| `LINK_PLANO` | `xsd:string` | true | 0..1 |

### `siga:SIGA_PLA_METAS_2021_24_LINEAR_SMSU`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `META` | `xsd:decimal` | true | 0..1 |
| `SECRETARIA` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `ODS_RELACIONADA` | `xsd:string` | true | 0..1 |
| `VALOR_PREVISTO` | `xsd:decimal` | true | 0..1 |
| `STATUS` | `xsd:string` | true | 0..1 |
| `LINK_PLANO` | `xsd:string` | true | 0..1 |
| `PROJETO` | `xsd:string` | true | 0..1 |
| `VALOR_BAIRRO` | `xsd:decimal` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:string` | true | 0..1 |
| `BAIRROS` | `xsd:string` | true | 0..1 |

### `siga:SIGA_PLA_OUTOR_2010_2015`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `COD_SETOR` | `xsd:decimal` | true | 0..1 |
| `COD_QUADRA` | `xsd:decimal` | true | 0..1 |
| `COD_LOTE` | `xsd:decimal` | true | 0..1 |
| `DSC_INTERESSADO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `NOM_BAIRRO` | `xsd:string` | true | 0..1 |
| `DSC_USO` | `xsd:string` | true | 0..1 |
| `DSC_ATIVIDADE` | `xsd:string` | true | 0..1 |
| `DSC_TIPOLOGIA` | `xsd:string` | true | 0..1 |
| `NUM_COEF_APROV_BAS` | `xsd:decimal` | true | 0..1 |
| `NUM_COEF_APROV_SOL` | `xsd:decimal` | true | 0..1 |
| `DSC_STATUS` | `xsd:string` | true | 0..1 |
| `NUM_CARACTERIZACAO` | `xsd:string` | true | 0..1 |
| `NUM_PROCESSO` | `xsd:decimal` | true | 0..1 |
| `NUM_ANO_PROCESSO` | `xsd:decimal` | true | 0..1 |
| `NUM_AREA_LOTE` | `xsd:decimal` | true | 0..1 |
| `NUM_UNIDADE` | `xsd:decimal` | true | 0..1 |
| `NUM_VAGA` | `xsd:decimal` | true | 0..1 |
| `DTA_PROTOCOLO` | `xsd:dateTime` | true | 0..1 |

### `siga:SIGA_PLA_OUTOR_2016_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `COD_SETOR` | `xsd:decimal` | true | 0..1 |
| `COD_QUADRA` | `xsd:decimal` | true | 0..1 |
| `COD_LOTE` | `xsd:decimal` | true | 0..1 |
| `DSC_INTERESSADO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `NOM_BAIRRO` | `xsd:string` | true | 0..1 |
| `DSC_USO` | `xsd:string` | true | 0..1 |
| `DSC_ATIVIDADE` | `xsd:string` | true | 0..1 |
| `DSC_TIPOLOGIA` | `xsd:string` | true | 0..1 |
| `NUM_COEF_APROV_BAS` | `xsd:string` | true | 0..1 |
| `NUM_COEF_APROV_SOL` | `xsd:string` | true | 0..1 |
| `DSC_STATUS` | `xsd:string` | true | 0..1 |
| `NUM_CARACTERIZACAO` | `xsd:string` | true | 0..1 |
| `NUM_PROCESSO` | `xsd:decimal` | true | 0..1 |
| `NUM_ANO_PROCESSO` | `xsd:decimal` | true | 0..1 |
| `NUM_AREA_LOTE` | `xsd:decimal` | true | 0..1 |
| `NUM_UNIDADE` | `xsd:decimal` | true | 0..1 |
| `NUM_VAGA` | `xsd:decimal` | true | 0..1 |
| `DTA_PROTOCOLO` | `xsd:dateTime` | true | 0..1 |

### `siga:SIGA_PLA_PADROES_OCUPACAO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `FINALIDADE` | `xsd:string` | true | 0..1 |
| `PLANEJAMENTO` | `xsd:string` | true | 0..1 |
| `VALOR` | `xsd:string` | true | 0..1 |
| `TIPOLOGIA` | `xsd:string` | true | 0..1 |
| `DESCRICAO1` | `xsd:string` | true | 0..1 |
| `DESCRICAO2` | `xsd:string` | true | 0..1 |
| `LEGENDA` | `xsd:string` | true | 0..1 |

### `siga:SIGA_PLA_RESTR_ADICIONAIS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `LEGISLACAO` | `xsd:string` | true | 0..1 |
| `LIM_GAB` | `xsd:string` | true | 0..1 |
| `URL_LEGIS` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `siga:SIGA_PLA_USO_SOLO_MZU_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |

### `siga:SIGA_PRACA_ATEND_EQUIPAMEN`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `CEP` | `xsd:string` | true | 0..1 |
| `TELEFONE0800` | `xsd:string` | true | 0..1 |
| `FONE_FACIL` | `xsd:string` | true | 0..1 |
| `HORARIO_ATENDIMENTO` | `xsd:string` | true | 0..1 |
| `LINK_PORTAL_SERVICO_CIDADAO` | `xsd:string` | true | 0..1 |
| `LINK_GUIA_SERVICO` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `COD_SETOR` | `xsd:string` | true | 0..1 |
| `COD_QUADRA` | `xsd:string` | true | 0..1 |
| `COD_LOTE` | `xsd:string` | true | 0..1 |

### `siga:SIGA_SAU_ATENCAO_DOMICILIAR`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `GESTAO` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `FLUXO_CLIENTELA` | `xsd:string` | true | 0..1 |
| `RAMAL` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `QUADRA` | `xsd:decimal` | true | 0..1 |
| `LOTE` | `xsd:decimal` | true | 0..1 |
| `COD_LOGRADOURO` | `xsd:decimal` | true | 0..1 |
| `NUM_LOGRADOURO` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_SAU_CAPS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `GESTAO` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `FLUXO_CLIENTELA` | `xsd:string` | true | 0..1 |
| `RAMAL` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `QUADRA` | `xsd:decimal` | true | 0..1 |
| `LOTE` | `xsd:decimal` | true | 0..1 |
| `COD_LOGRADOURO` | `xsd:decimal` | true | 0..1 |
| `NUM_LOGRADOURO` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_SAU_CEN_ESPECIALIDADE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `GESTAO` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `FLUXO_CLIENTELA` | `xsd:string` | true | 0..1 |
| `RAMAL` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `QUADRA` | `xsd:decimal` | true | 0..1 |
| `LOTE` | `xsd:decimal` | true | 0..1 |
| `COD_LOGRADOURO` | `xsd:decimal` | true | 0..1 |
| `NUM_LOGRADOURO` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_SAU_CEN_HOSPITALAR`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `GESTAO` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `FLUXO_CLIENTELA` | `xsd:string` | true | 0..1 |
| `TOTAL_LEITOS_INTERNACAO` | `xsd:decimal` | true | 0..1 |
| `TOTAL_LEITOS_UTI` | `xsd:decimal` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `QUADRA` | `xsd:decimal` | true | 0..1 |
| `LOTE` | `xsd:decimal` | true | 0..1 |
| `COD_LOGRADOURO` | `xsd:decimal` | true | 0..1 |
| `NUM_LOGRADOURO` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_SAU_CLIN_ESPECIALIZADA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `GESTAO` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `FLUXO_CLIENTELA` | `xsd:string` | true | 0..1 |
| `RAMAL` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `QUADRA` | `xsd:decimal` | true | 0..1 |
| `LOTE` | `xsd:decimal` | true | 0..1 |
| `COD_LOGRADOURO` | `xsd:decimal` | true | 0..1 |
| `NUM_LOGRADOURO` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_SAU_ESPECIALIDADE_ASSIST`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `GESTAO` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `FLUXO_CLIENTELA` | `xsd:string` | true | 0..1 |
| `RAMAL` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `QUADRA` | `xsd:decimal` | true | 0..1 |
| `LOTE` | `xsd:decimal` | true | 0..1 |
| `COD_LOGRADOURO` | `xsd:decimal` | true | 0..1 |
| `NUM_LOGRADOURO` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_SAU_HOSP_ESTADUAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `ATENDIMENTO` | `xsd:string` | true | 0..1 |
| `SITE` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `QUADRA` | `xsd:decimal` | true | 0..1 |
| `LOTE` | `xsd:decimal` | true | 0..1 |
| `COD_LOGRADOURO` | `xsd:decimal` | true | 0..1 |
| `NUM_LOGRADOURO` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_SAU_HOSP_MULHER`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `GESTAO` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `FLUXO_CLIENTELA` | `xsd:string` | true | 0..1 |
| `TOTAL_LEITOS_INTERNACAO` | `xsd:decimal` | true | 0..1 |
| `TOTAL_LEITOS_UTI` | `xsd:decimal` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `QUADRA` | `xsd:decimal` | true | 0..1 |
| `LOTE` | `xsd:decimal` | true | 0..1 |
| `COD_LOGRADOURO` | `xsd:decimal` | true | 0..1 |
| `NUM_LOGRADOURO` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_SAU_HOSP_PARTICULAR`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `ATENDIMENTO` | `xsd:string` | true | 0..1 |
| `SITE` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `QUADRA` | `xsd:decimal` | true | 0..1 |
| `LOTE` | `xsd:decimal` | true | 0..1 |
| `COD_LOGRADOURO` | `xsd:decimal` | true | 0..1 |
| `NUM_LOGRADOURO` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_SAU_NUPE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `GESTAO` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `FLUXO_CLIENTELA` | `xsd:string` | true | 0..1 |
| `RAMAL` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `QUADRA` | `xsd:decimal` | true | 0..1 |
| `LOTE` | `xsd:decimal` | true | 0..1 |
| `COD_LOGRADOURO` | `xsd:decimal` | true | 0..1 |
| `NUM_LOGRADOURO` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_SAU_PS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `GESTAO` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `FLUXO_CLIENTELA` | `xsd:string` | true | 0..1 |
| `TOTAL_LEITOS_INTERNACAO` | `xsd:decimal` | true | 0..1 |
| `TOTAL_LEITOS_UTI` | `xsd:decimal` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `QUADRA` | `xsd:decimal` | true | 0..1 |
| `LOTE` | `xsd:decimal` | true | 0..1 |
| `COD_LOGRADOURO` | `xsd:decimal` | true | 0..1 |
| `NUM_LOGRADOURO` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_SAU_TERRITORIOS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOM_TERRITORIO` | `xsd:string` | true | 0..1 |
| `NOM_UBS_VINCULADAS` | `xsd:string` | true | 0..1 |

### `siga:SIGA_SAU_UNID_BASICA_SAUDE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `GESTAO` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `FLUXO_CLIENTELA` | `xsd:string` | true | 0..1 |
| `RAMAL` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:string` | true | 0..1 |
| `QUADRA` | `xsd:string` | true | 0..1 |
| `LOTE` | `xsd:string` | true | 0..1 |
| `COD_LOGRADOURO` | `xsd:decimal` | true | 0..1 |
| `NUM_LOGRADOURO` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_SAU_UPA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `GESTAO` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `FLUXO_CLIENTELA` | `xsd:string` | true | 0..1 |
| `TOTAL_LEITOS_INTERNACAO` | `xsd:decimal` | true | 0..1 |
| `TOTAL_LEITOS_UTI` | `xsd:decimal` | true | 0..1 |
| `DSC_OBS_LEITO_UTI` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `QUADRA` | `xsd:decimal` | true | 0..1 |
| `LOTE` | `xsd:decimal` | true | 0..1 |
| `COD_LOGRADOURO` | `xsd:decimal` | true | 0..1 |
| `NUM_LOGRADOURO` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_SEG_BOMBEIRO_AGRUPAM`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `DSC_ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONES` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `SITE` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `QUADRA` | `xsd:decimal` | true | 0..1 |
| `LOTE` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_SEG_BOMBEIRO_HIDRANTE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ESTACAO` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `FORMULARIO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `HISTORICO` | `xsd:string` | true | 0..1 |

### `siga:SIGA_SEG_CIDADA_DEPARTAMENTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `DSC_ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `DESCRICAO` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `QUADRA` | `xsd:decimal` | true | 0..1 |
| `LOTE` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_SEG_GCM_CORREGEDORIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `CORREGEDOR` | `xsd:string` | true | 0..1 |
| `DSC_ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `QUADRA` | `xsd:decimal` | true | 0..1 |
| `LOTE` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_SEG_GCM_DESTACAMENTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `INSPETOR_CHEFE` | `xsd:string` | true | 0..1 |
| `DSC_ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `QUADRA` | `xsd:decimal` | true | 0..1 |
| `LOTE` | `xsd:decimal` | true | 0..1 |
| `DSC_EMAIL` | `xsd:string` | true | 0..1 |

### `siga:SIGA_SEG_GCM_INSPETORIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `INSPETOR_CHEFE` | `xsd:string` | true | 0..1 |
| `DSC_EMAIL` | `xsd:string` | true | 0..1 |
| `DSC_ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |

### `siga:SIGA_SEG_GCM_SEG_PATRIMONIAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `DSC_ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `QUADRA` | `xsd:decimal` | true | 0..1 |
| `LOTE` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_SEG_PCIENT_IML`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `DSC_ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `LINK` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `QUADRA` | `xsd:decimal` | true | 0..1 |
| `LOTE` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_SEG_PCIENT_INT_CRIMINAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `DSC_ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `LINK` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `QUADRA` | `xsd:decimal` | true | 0..1 |
| `LOTE` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_SEG_PCIENT_SUPERINTENDEN`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `DSC_ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `LINK` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `QUADRA` | `xsd:decimal` | true | 0..1 |
| `LOTE` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_SEG_PCIVIL_CENTRO_DETENC`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `DSC_ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `SITE` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `QUADRA` | `xsd:decimal` | true | 0..1 |
| `LOTE` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_SEG_PCIVIL_DELEGACIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `DELEGADO_TITULAR` | `xsd:string` | true | 0..1 |
| `DSC_ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `QUADRA` | `xsd:decimal` | true | 0..1 |
| `LOTE` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_SEG_PFEDERAL_POSTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `DSC_ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `SITE` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `QUADRA` | `xsd:decimal` | true | 0..1 |
| `LOTE` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_SEG_PM_BATALHAO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `COMANDO` | `xsd:string` | true | 0..1 |
| `COMANDANTE` | `xsd:string` | true | 0..1 |
| `DSC_ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `SITE` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `QUADRA` | `xsd:decimal` | true | 0..1 |
| `LOTE` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_SEG_PM_COMANDO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `COMANDANTE` | `xsd:string` | true | 0..1 |
| `DSC_ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `SITE` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `QUADRA` | `xsd:decimal` | true | 0..1 |
| `LOTE` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_SEG_PM_COMPANHIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `BATALHAO` | `xsd:string` | true | 0..1 |
| `COMANDANTE` | `xsd:string` | true | 0..1 |
| `DSC_ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `QUADRA` | `xsd:decimal` | true | 0..1 |
| `LOTE` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_SEG_PM_RODOVIARIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `DSC_ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `QUADRA` | `xsd:decimal` | true | 0..1 |
| `LOTE` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_SEM_AREA_CONTAMINADA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `COD_SETOR` | `xsd:decimal` | false | 1..1 |
| `COD_QUADRA` | `xsd:decimal` | false | 1..1 |
| `COD_LOTE` | `xsd:decimal` | false | 1..1 |
| `DSC_FONTE_LOTE_CONTAMINADO` | `xsd:string` | false | 1..1 |
| `DSC_SITUACAO_LOTE_CONTAMINADO` | `xsd:string` | false | 1..1 |
| `DSC_DOCUMENTO` | `xsd:string` | false | 1..1 |
| `DSC_LINK_SITE` | `xsd:string` | true | 0..1 |
| `NOM_BAIRRO_OFICIAL` | `xsd:string` | true | 0..1 |

### `siga:SIGA_SEM_ESTACOES_COLETA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `HORARIO` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `RESTRICAO` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:decimal` | true | 0..1 |
| `QUADRA` | `xsd:decimal` | true | 0..1 |
| `LOTE` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_SEM_PISCINAO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `ATENDE` | `xsd:string` | true | 0..1 |
| `CAPACIDADE` | `xsd:string` | true | 0..1 |
| `UNIDADE` | `xsd:string` | true | 0..1 |
| `ANO_OPERACAO` | `xsd:string` | true | 0..1 |

### `siga:SIGA_SEM_PISCININHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `ATENDE` | `xsd:string` | true | 0..1 |
| `CAPACIDADE` | `xsd:string` | true | 0..1 |

### `siga:SIGA_SEM_SETOR_COL_RED_SECOS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `SETOR` | `xsd:string` | true | 0..1 |
| `DIA` | `xsd:string` | true | 0..1 |
| `HORARIO` | `xsd:string` | true | 0..1 |
| `BAIRROS` | `xsd:string` | true | 0..1 |

### `siga:SIGA_SEM_SETOR_COL_RES_UMIDO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `SETOR` | `xsd:string` | true | 0..1 |
| `DIA` | `xsd:string` | true | 0..1 |
| `HORARIO` | `xsd:string` | true | 0..1 |
| `BAIRROS` | `xsd:string` | true | 0..1 |

### `siga:SIGA_SFU_CEMITERIO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `NOME_POPULAR` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `HORARIO` | `xsd:string` | true | 0..1 |
| `EMAIL` | `xsd:string` | true | 0..1 |

### `siga:SIGA_TOTAL_EQUIP_BAIRRO_INVEST`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `COD_BAIRRO` | `xsd:decimal` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `POPULACAO_2022` | `xsd:decimal` | true | 0..1 |
| `AREA` | `xsd:decimal` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `QTD_CULTURA` | `xsd:decimal` | true | 0..1 |
| `QTD_EDUCACAO` | `xsd:decimal` | true | 0..1 |
| `QTD_SAUDE` | `xsd:decimal` | true | 0..1 |
| `QTD_FEIRAS` | `xsd:decimal` | true | 0..1 |
| `QTD_SHOPPINGS` | `xsd:decimal` | true | 0..1 |
| `QTD_MARCAS` | `xsd:decimal` | true | 0..1 |

### `siga:SIGA_TUR_ARTE_ARQUITETURA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `LINK` | `xsd:string` | true | 0..1 |

### `siga:SIGA_TUR_CIRC_HOTEL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `LINK` | `xsd:string` | true | 0..1 |

### `siga:SIGA_TUR_CIRC_INDUSTRIA_INOVAC`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `LINK` | `xsd:string` | true | 0..1 |

### `siga:SIGA_TUR_CIRC_PARANAPIACABA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `LINK` | `xsd:string` | true | 0..1 |

### `siga:SIGA_TUR_CIRC_PARQUE_LAZER`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `LINK` | `xsd:string` | true | 0..1 |

### `siga:SIGA_TUR_CIRC_PEDAGOG_CIENTIF`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `LINK` | `xsd:string` | true | 0..1 |

### `siga:SIGA_TUR_CITY_TOUR_HISTORICO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `LINK` | `xsd:string` | true | 0..1 |

### `siga:SIGA_TUR_COMPRA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `LINK` | `xsd:string` | true | 0..1 |

### `siga:SIGA_TUR_HIST_CULTURAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `LINK` | `xsd:string` | true | 0..1 |
