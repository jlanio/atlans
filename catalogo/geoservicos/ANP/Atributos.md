# ANP — atributos das camadas

Geoportal: [[Geosserviços/ANP/Agência Nacional do Petróleo, Gás Natural e Biocombustíveis — ANP|Agência Nacional do Petróleo, Gás Natural e Biocombustíveis — ANP]]

Os campos abaixo vêm de `DescribeFeatureType` (XSD), sem download de feições.

## Basemap (4)

### `Basemap:Batimetria_Sirgas2000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `PROFUNDIDA` | `xsd:string` | true | 0..1 |
| `CLASSES` | `xsd:string` | true | 0..1 |

### `Basemap:Limites_America_do_Sul_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `FIPS_CNTRY` | `xsd:string` | true | 0..1 |
| `GMI_CNTRY` | `xsd:string` | true | 0..1 |
| `ISO_2DIGIT` | `xsd:string` | true | 0..1 |
| `ISO_3DIGIT` | `xsd:string` | true | 0..1 |
| `CNTRY_NAME` | `xsd:string` | true | 0..1 |
| `LONG_NAME` | `xsd:string` | true | 0..1 |
| `SOVEREIGN` | `xsd:string` | true | 0..1 |
| `POP_CNTRY` | `xsd:long` | true | 0..1 |
| `CURR_TYPE` | `xsd:string` | true | 0..1 |
| `CURR_CODE` | `xsd:string` | true | 0..1 |
| `LANDLOCKED` | `xsd:string` | true | 0..1 |
| `SQKM` | `xsd:double` | true | 0..1 |
| `SQMI` | `xsd:double` | true | 0..1 |
| `COLOR_MAP` | `xsd:string` | true | 0..1 |

### `Basemap:Limites_Estaduais`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `Id` | `xsd:int` | true | 0..1 |
| `ESTADOS` | `xsd:string` | true | 0..1 |
| `CAPITAL` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `NOME_MAIUS` | `xsd:string` | true | 0..1 |
| `REGIAO` | `xsd:string` | true | 0..1 |
| `SIGLA_REGI` | `xsd:string` | true | 0..1 |
| `POPULACAO` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:string` | true | 0..1 |
| `ILHAS` | `xsd:string` | true | 0..1 |
| `ET_ID` | `xsd:int` | true | 0..1 |

### `Basemap:Limites_Municipais`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `Id` | `xsd:int` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `AREA_INDIV` | `xsd:string` | true | 0..1 |
| `LATITUDE_S` | `xsd:string` | true | 0..1 |
| `LONGITUDE_` | `xsd:string` | true | 0..1 |
| `AREA_TOTAL` | `xsd:string` | true | 0..1 |
| `PERIMETRO_` | `xsd:string` | true | 0..1 |
| `MUNIC_MINU` | `xsd:string` | true | 0..1 |
| `MUNIC_MAIU` | `xsd:string` | true | 0..1 |
| `CAPITAL_ES` | `xsd:string` | true | 0..1 |
| `ESTADO_MAI` | `xsd:string` | true | 0..1 |
| `REGIAO` | `xsd:string` | true | 0..1 |
| `SIGLA_REGI` | `xsd:string` | true | 0..1 |
| `SEDE_MUNIC` | `xsd:int` | true | 0..1 |
| `ESTADO_MIN` | `xsd:string` | true | 0..1 |
| `GEOCODIGO_` | `xsd:string` | true | 0..1 |
| `AREA_MUNIC` | `xsd:double` | true | 0..1 |
| `DENSIDADE_` | `xsd:double` | true | 0..1 |
| `POPULACAO_` | `xsd:double` | true | 0..1 |
| `POPULACAO1` | `xsd:double` | true | 0..1 |
| `POPULACAO2` | `xsd:double` | true | 0..1 |
| `ID1` | `xsd:long` | true | 0..1 |
| `UF` | `xsd:string` | true | 0..1 |
| `ET_ID` | `xsd:int` | true | 0..1 |

## BD_ANP (71)

### `BD_ANP:BACIAS_SEDIMENTARES_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `GEOM` | `gml:GeometryPropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:decimal` | true | 0..1 |
| `SITUACAO` | `xsd:string` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `AREA` | `xsd:decimal` | true | 0..1 |

### `BD_ANP:BLCS_ARRM_CESSAO_ONEROSA1`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `NOM_CAMPO` | `xsd:string` | true | 0..1 |
| `NOM_BACIA` | `xsd:string` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `AREA` | `xsd:decimal` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:decimal` | false | 1..1 |

### `BD_ANP:BLCS_ARRM_CESSAO_ONEROSA2`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `NOM_CAMPO` | `xsd:string` | true | 0..1 |
| `NOM_BACIA` | `xsd:string` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `AREA` | `xsd:decimal` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:decimal` | false | 1..1 |

### `BD_ANP:BLCS_ARRM_OPC1`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `INDICE_BLOCO` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `SITUACAO_BLOCO` | `xsd:string` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `NOME_SETOR` | `xsd:string` | true | 0..1 |
| `AREA_ANP` | `xsd:decimal` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:decimal` | false | 1..1 |

### `BD_ANP:BLCS_ARRM_OPC2`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `INDICE_BLOCO` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `SITUACAO_BLOCO` | `xsd:string` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `NOME_SETOR` | `xsd:string` | true | 0..1 |
| `AREA_ANP` | `xsd:decimal` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:decimal` | false | 1..1 |

### `BD_ANP:BLCS_ARRM_OPC3`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `INDICE_BLOCO` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `SITUACAO_BLOCO` | `xsd:string` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `NOME_SETOR` | `xsd:string` | true | 0..1 |
| `AREA_ANP` | `xsd:decimal` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:decimal` | false | 1..1 |

### `BD_ANP:BLCS_ARRM_OPC4`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `INDICE_BLOCO` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `SITUACAO_BLOCO` | `xsd:string` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `NOME_SETOR` | `xsd:string` | true | 0..1 |
| `AREA_ANP` | `xsd:decimal` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:decimal` | false | 1..1 |

### `BD_ANP:BLCS_ARRM_OPC5`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `INDICE_BLOCO` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `SITUACAO_BLOCO` | `xsd:string` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `NOME_SETOR` | `xsd:string` | true | 0..1 |
| `AREA_ANP` | `xsd:decimal` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:decimal` | false | 1..1 |

### `BD_ANP:BLCS_ARRM_OPP1`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `NOM_CAMPO` | `xsd:string` | true | 0..1 |
| `NOM_BACIA` | `xsd:string` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `AREA` | `xsd:decimal` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:decimal` | false | 1..1 |

### `BD_ANP:BLCS_ARRM_OPP2`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `NOM_CAMPO` | `xsd:string` | true | 0..1 |
| `NOM_BACIA` | `xsd:string` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `AREA` | `xsd:decimal` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:decimal` | false | 1..1 |

### `BD_ANP:BLCS_ARRM_R10_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `NOME_SETOR` | `xsd:string` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `SITUACAO_B` | `xsd:string` | true | 0..1 |
| `NOMENCLATU` | `xsd:string` | true | 0..1 |
| `INDICE_BLO` | `xsd:decimal` | true | 0..1 |
| `AREA_BLOCO` | `xsd:double` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `BD_ANP:BLCS_ARRM_R11_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `INDICE_BLO` | `xsd:decimal` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `NOME_SETOR` | `xsd:string` | true | 0..1 |
| `NOMENCLATU` | `xsd:string` | true | 0..1 |
| `SITUACAO_B` | `xsd:string` | true | 0..1 |
| `AREA_BLOCO` | `xsd:double` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `BD_ANP:BLCS_ARRM_R12_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `NOME_SETOR` | `xsd:string` | true | 0..1 |
| `AREA_BLOCO` | `xsd:double` | true | 0..1 |
| `NOMENCLATU` | `xsd:string` | true | 0..1 |
| `SITUACAO_B` | `xsd:string` | true | 0..1 |
| `INDICE_BLO` | `xsd:decimal` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `BD_ANP:BLCS_ARRM_R13_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `NOME_SETOR` | `xsd:string` | true | 0..1 |
| `NOMENCLATU` | `xsd:string` | true | 0..1 |
| `AREA` | `xsd:double` | true | 0..1 |
| `PERIMETRO` | `xsd:double` | true | 0..1 |
| `SITUACAO_B` | `xsd:string` | true | 0..1 |
| `INDICE_BLO` | `xsd:decimal` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `BD_ANP:BLCS_ARRM_R14_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `OGR_FID` | `xsd:decimal` | true | 0..1 |
| `GEOM` | `gml:GeometryPropertyType` | true | 0..1 |
| `BACIA` | `xsd:string` | true | 0..1 |
| `SITUACAO` | `xsd:string` | true | 0..1 |
| `BLOCO` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:string` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `ARREMATADO` | `xsd:string` | true | 0..1 |

### `BD_ANP:BLCS_ARRM_R15_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `GEOM` | `gml:GeometryPropertyType` | true | 0..1 |
| `BACIA` | `xsd:string` | true | 0..1 |
| `SITUACAO` | `xsd:string` | true | 0..1 |
| `BLOCO` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:string` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `ARREMATADO` | `xsd:string` | true | 0..1 |

### `BD_ANP:BLCS_ARRM_R16_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `GEOM` | `gml:GeometryPropertyType` | true | 0..1 |
| `BACIA` | `xsd:string` | true | 0..1 |
| `SITUACAO` | `xsd:string` | true | 0..1 |
| `BLOCO` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:string` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `ARREMATADO` | `xsd:string` | true | 0..1 |

### `BD_ANP:BLCS_ARRM_R17_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `NOME` | `xsd:string` | true | 0..1 |
| `SITUACAO_BLOCO` | `xsd:string` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `NOME_SETOR` | `xsd:string` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:decimal` | false | 1..1 |

### `BD_ANP:BLCS_ARRM_R5_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `INDICE_BLOCO` | `xsd:string` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `NOME_SETOR` | `xsd:string` | true | 0..1 |
| `AREA_BLOCO` | `xsd:double` | true | 0..1 |
| `SITUACAO_BACIA` | `xsd:string` | true | 0..1 |
| `NUM_RODADA` | `xsd:decimal` | true | 0..1 |
| `COD_BLOCO` | `xsd:string` | true | 0..1 |

### `BD_ANP:BLCS_ARRM_R6_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `DIFFERENCEGEOMETRY1` | `gml:GeometryPropertyType` | true | 0..1 |
| `SITUACAO_BACIA` | `xsd:string` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `NOMENCLATURA_BLOCO` | `xsd:string` | true | 0..1 |
| `NOME_SETOR` | `xsd:string` | true | 0..1 |
| `INDICE_BLOCO` | `xsd:decimal` | true | 0..1 |
| `COD_BACIA` | `xsd:string` | true | 0..1 |
| `AREA_BLOCO_REAL` | `xsd:double` | true | 0..1 |
| `RODADA` | `xsd:double` | true | 0..1 |
| `BLOCO` | `xsd:string` | true | 0..1 |

### `BD_ANP:BLCS_ARRM_R7_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `NOMENCLATU` | `xsd:string` | true | 0..1 |
| `NOME_SETOR` | `xsd:string` | true | 0..1 |
| `INDICE_BLO` | `xsd:decimal` | true | 0..1 |
| `COD_BACIA` | `xsd:string` | true | 0..1 |
| `AREA_BLOCO` | `xsd:double` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `BD_ANP:BLCS_ARRM_R9_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `NOMENCLATU` | `xsd:string` | true | 0..1 |
| `SITUACAO_B` | `xsd:string` | true | 0..1 |
| `INDICE_BLO` | `xsd:decimal` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `NOME_SETOR` | `xsd:string` | true | 0..1 |
| `DIFFERENCEGEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `AREA_BLOCO` | `xsd:double` | true | 0..1 |

### `BD_ANP:BLCS_OFER_CESSAO_ONEROSA_LVECO1`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `NOM_CAMPO` | `xsd:string` | true | 0..1 |
| `NOM_BACIA` | `xsd:string` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `AREA` | `xsd:decimal` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:decimal` | false | 1..1 |

### `BD_ANP:BLCS_OFER_CESSAO_ONEROSA_LVECO2`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `NOM_CAMPO` | `xsd:string` | true | 0..1 |
| `NOM_BACIA` | `xsd:string` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `AREA` | `xsd:decimal` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:decimal` | false | 1..1 |

### `BD_ANP:BLCS_OFER_OPC1`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `NOME` | `xsd:string` | true | 0..1 |
| `LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `NOME_SETOR` | `xsd:string` | true | 0..1 |
| `AREA_ANP` | `xsd:decimal` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:decimal` | false | 1..1 |

### `BD_ANP:BLCS_OFER_OPC2`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `NOME` | `xsd:string` | true | 0..1 |
| `LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `NOME_SETOR` | `xsd:string` | true | 0..1 |
| `AREA_ANP` | `xsd:decimal` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:decimal` | false | 1..1 |

### `BD_ANP:BLCS_OFER_OPC3`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `NOME` | `xsd:string` | true | 0..1 |
| `LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `NOME_SETOR` | `xsd:string` | true | 0..1 |
| `AREA_ANP` | `xsd:decimal` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:decimal` | false | 1..1 |

### `BD_ANP:BLCS_OFER_OPC4`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `NOME` | `xsd:string` | true | 0..1 |
| `LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `NOME_SETOR` | `xsd:string` | true | 0..1 |
| `AREA_ANP` | `xsd:decimal` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:decimal` | false | 1..1 |

### `BD_ANP:BLCS_OFER_OPC5`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `NOME` | `xsd:string` | true | 0..1 |
| `LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `NOME_SETOR` | `xsd:string` | true | 0..1 |
| `AREA_ANP` | `xsd:decimal` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:decimal` | false | 1..1 |

### `BD_ANP:BLCS_OFER_R0`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `BACIA` | `xsd:string` | true | 0..1 |
| `COD_BLOCO` | `xsd:string` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `DIFFERENCEGEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:string` | true | 0..1 |

### `BD_ANP:BLCS_OFER_R1`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `BACIA` | `xsd:string` | true | 0..1 |
| `COD_BLOCO` | `xsd:string` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `DIFFERENCEGEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:string` | true | 0..1 |

### `BD_ANP:BLCS_OFER_R2`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `BACIA` | `xsd:string` | true | 0..1 |
| `COD_BLOCO` | `xsd:string` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `DIFFERENCEGEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:string` | true | 0..1 |

### `BD_ANP:BLCS_OFER_R3`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `BACIA` | `xsd:string` | true | 0..1 |
| `COD_BLOCO` | `xsd:string` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `DIFFERENCEGEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:string` | true | 0..1 |

### `BD_ANP:BLCS_OFER_R4`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `BACIA` | `xsd:string` | true | 0..1 |
| `COD_BLOCO` | `xsd:string` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `DIFFERENCEGEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:string` | true | 0..1 |

### `BD_ANP:BLCS_OFER_R5_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `COD_BACIA` | `xsd:string` | true | 0..1 |
| `LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `NOMENCLATU` | `xsd:string` | true | 0..1 |
| `NOME_SETOR` | `xsd:string` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `BACIA_SITU` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `INDICE_CEL` | `xsd:double` | true | 0..1 |
| `AREA_VERDA` | `xsd:double` | true | 0..1 |
| `ID` | `xsd:double` | true | 0..1 |
| `CODIGO_ANT` | `xsd:string` | true | 0..1 |
| `ID1` | `xsd:decimal` | true | 0..1 |

### `BD_ANP:BLCS_OFER_R6_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `DIFFERENCEGEOMETRY1` | `gml:GeometryPropertyType` | true | 0..1 |
| `LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `NOMENCLATURA_BLOCO` | `xsd:string` | true | 0..1 |
| `NOME_SETOR` | `xsd:string` | true | 0..1 |
| `INDICE_BLOCO` | `xsd:decimal` | true | 0..1 |
| `AREA_BLOCO` | `xsd:double` | true | 0..1 |
| `ID` | `xsd:decimal` | true | 0..1 |
| `COD_BACIA` | `xsd:string` | true | 0..1 |
| `CODIGO_ANTIGO_BLOCO` | `xsd:string` | true | 0..1 |
| `AREA_BLOCO_REAL` | `xsd:double` | true | 0..1 |

### `BD_ANP:BLOC_OFER_R10_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `DIFFERENCEGEOMETRY1` | `gml:GeometryPropertyType` | true | 0..1 |
| `NOME_SETOR` | `xsd:string` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `NOMENCLATU` | `xsd:string` | true | 0..1 |
| `INDICE_BLO` | `xsd:decimal` | true | 0..1 |
| `AREA_BLOCO` | `xsd:double` | true | 0..1 |
| `ID1` | `xsd:decimal` | true | 0..1 |

### `BD_ANP:BLOC_OFER_R11_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `INDICE_BLO` | `xsd:decimal` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `NOME_SETOR` | `xsd:string` | true | 0..1 |
| `NOMENCLATU` | `xsd:string` | true | 0..1 |
| `LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `AREA_BLOCO` | `xsd:double` | true | 0..1 |
| `ID3` | `xsd:decimal` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID1` | `xsd:decimal` | true | 0..1 |

### `BD_ANP:BLOC_OFER_R12_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `BACIA` | `xsd:string` | true | 0..1 |
| `LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `BLOCO` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:string` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `BD_ANP:BLOC_OFER_R13_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `OGR_FID` | `xsd:decimal` | true | 0..1 |
| `GEOM` | `gml:GeometryPropertyType` | true | 0..1 |
| `BACIA` | `xsd:string` | true | 0..1 |
| `LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `BLOCO` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:string` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `ARREMATADO` | `xsd:string` | true | 0..1 |

### `BD_ANP:BLOC_OFER_R14_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `OGR_FID` | `xsd:decimal` | true | 0..1 |
| `GEOM` | `gml:GeometryPropertyType` | true | 0..1 |
| `BACIA` | `xsd:string` | true | 0..1 |
| `LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `BLOCO` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:string` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `ARREMATADO` | `xsd:string` | true | 0..1 |

### `BD_ANP:BLOC_OFER_R15_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `GEOM` | `gml:SurfacePropertyType` | true | 0..1 |
| `BACIA` | `xsd:string` | true | 0..1 |
| `LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `BLOCO` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:string` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `ARREMATADO` | `xsd:string` | true | 0..1 |

### `BD_ANP:BLOC_OFER_R16_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `GEOM` | `gml:SurfacePropertyType` | true | 0..1 |
| `BACIA` | `xsd:string` | true | 0..1 |
| `LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `BLOCO` | `xsd:string` | true | 0..1 |
| `SETOR` | `xsd:string` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `ARREMATADO` | `xsd:string` | true | 0..1 |

### `BD_ANP:BLOC_OFER_R17_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `OGR_FID` | `xsd:decimal` | true | 0..1 |
| `GEOM` | `gml:GeometryPropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:decimal` | true | 0..1 |
| `LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `INDICE_BLO` | `xsd:decimal` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `NOMENCLATU` | `xsd:string` | true | 0..1 |
| `NOME_SETOR` | `xsd:string` | true | 0..1 |
| `AREA_ANP` | `xsd:decimal` | true | 0..1 |

### `BD_ANP:BLOC_OFER_R7_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `NOMENCLATU` | `xsd:string` | true | 0..1 |
| `NOME_SETOR` | `xsd:string` | true | 0..1 |
| `INDICE_BLO` | `xsd:decimal` | true | 0..1 |
| `AREA_BLOCO` | `xsd:double` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID1` | `xsd:decimal` | true | 0..1 |

### `BD_ANP:BLOC_OFER_R9_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `NOMENCLATU` | `xsd:string` | true | 0..1 |
| `LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `INDICE_BLO` | `xsd:decimal` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `NOME_SETOR` | `xsd:string` | true | 0..1 |
| `DIFFERENCEGEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID4` | `xsd:decimal` | true | 0..1 |
| `AREA_BLOCO` | `xsd:double` | true | 0..1 |

### `BD_ANP:Blocos_Arrematados_Partilha_1`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome` | `xsd:string` | true | 0..1 |
| `cod_bloco` | `xsd:string` | true | 0..1 |
| `rodada` | `xsd:string` | true | 0..1 |
| `nome_bacia` | `xsd:string` | true | 0..1 |
| `setor` | `xsd:string` | true | 0..1 |
| `GEOM` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:decimal` | true | 0..1 |

### `BD_ANP:Blocos_Arrematados_Partilha_2`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome` | `xsd:string` | true | 0..1 |
| `cod_bloco` | `xsd:string` | true | 0..1 |
| `rodada` | `xsd:string` | true | 0..1 |
| `nome_bacia` | `xsd:string` | true | 0..1 |
| `setor` | `xsd:string` | true | 0..1 |
| `GEOM` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:decimal` | true | 0..1 |

### `BD_ANP:Blocos_Arrematados_Partilha_3`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome` | `xsd:string` | true | 0..1 |
| `cod_bloco` | `xsd:string` | true | 0..1 |
| `rodada` | `xsd:string` | true | 0..1 |
| `nome_bacia` | `xsd:string` | true | 0..1 |
| `setor` | `xsd:string` | true | 0..1 |
| `GEOM` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:decimal` | true | 0..1 |

### `BD_ANP:Blocos_Arrematados_Partilha_4`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome` | `xsd:string` | true | 0..1 |
| `cod_bloco` | `xsd:string` | true | 0..1 |
| `rodada` | `xsd:string` | true | 0..1 |
| `nome_bacia` | `xsd:string` | true | 0..1 |
| `setor` | `xsd:string` | true | 0..1 |
| `GEOM` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:decimal` | true | 0..1 |

### `BD_ANP:Blocos_Arrematados_Partilha_5`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome` | `xsd:string` | true | 0..1 |
| `cod_bloco` | `xsd:string` | true | 0..1 |
| `rodada` | `xsd:string` | true | 0..1 |
| `nome_bacia` | `xsd:string` | true | 0..1 |
| `setor` | `xsd:string` | true | 0..1 |
| `GEOM` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:decimal` | true | 0..1 |

### `BD_ANP:Blocos_Arrematados_Partilha_6`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nome` | `xsd:string` | true | 0..1 |
| `cod_bloco` | `xsd:string` | true | 0..1 |
| `rodada` | `xsd:string` | true | 0..1 |
| `nome_bacia` | `xsd:string` | true | 0..1 |
| `setor` | `xsd:string` | true | 0..1 |
| `GEOM` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:decimal` | true | 0..1 |

### `BD_ANP:Blocos_Arrematados_R0`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `BACIA` | `xsd:string` | true | 0..1 |
| `COD_BLOCO` | `xsd:string` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `DIFFERENCEGEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:string` | true | 0..1 |

### `BD_ANP:Blocos_Arrematados_R1`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `BACIA` | `xsd:string` | true | 0..1 |
| `COD_BLOCO` | `xsd:string` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `DIFFERENCEGEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:string` | true | 0..1 |

### `BD_ANP:Blocos_Arrematados_R2`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `BACIA` | `xsd:string` | true | 0..1 |
| `COD_BLOCO` | `xsd:string` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `DIFFERENCEGEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:string` | true | 0..1 |

### `BD_ANP:Blocos_Arrematados_R3`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `BACIA` | `xsd:string` | true | 0..1 |
| `COD_BLOCO` | `xsd:string` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `DIFFERENCEGEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:string` | true | 0..1 |

### `BD_ANP:Blocos_Arrematados_R4`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `BACIA` | `xsd:string` | true | 0..1 |
| `COD_BLOCO` | `xsd:string` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `DIFFERENCEGEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:string` | true | 0..1 |

### `BD_ANP:BLOCOS_EXPLORATORIOS_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `COD_BLOCO` | `xsd:string` | true | 0..1 |
| `COD_FASE_C` | `xsd:string` | true | 0..1 |
| `DAT_ASSINA` | `xsd:string` | true | 0..1 |
| `DAT_TERMIN` | `xsd:string` | true | 0..1 |
| `NOM_BACIA` | `xsd:string` | true | 0..1 |
| `NOM_BLOCO` | `xsd:string` | true | 0..1 |
| `NOM_FANTAS` | `xsd:string` | true | 0..1 |
| `NUM_CONTRA` | `xsd:string` | true | 0..1 |
| `NUM_DESCOB` | `xsd:double` | true | 0..1 |
| `OPERADOR_C` | `xsd:string` | true | 0..1 |
| `RODADA` | `xsd:string` | true | 0..1 |
| `AREA_TOTAL` | `xsd:double` | true | 0..1 |
| `AMBIENTE` | `xsd:string` | true | 0..1 |
| `BLOCOS` | `xsd:string` | true | 0..1 |

### `BD_ANP:CAMPOS_PRODUCAO_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `NUM_RODADA` | `xsd:string` | true | 0..1 |
| `NOM_CAMPO` | `xsd:string` | true | 0..1 |
| `AREA` | `xsd:decimal` | true | 0..1 |
| `OPERADOR_C` | `xsd:string` | true | 0..1 |
| `NUM_CONTRA` | `xsd:string` | true | 0..1 |
| `DAT_ASSINA` | `xsd:string` | true | 0..1 |
| `DAT_TERMIN` | `xsd:string` | true | 0..1 |
| `NOM_BACIA` | `xsd:string` | true | 0..1 |
| `COD_CAMPO` | `xsd:decimal` | true | 0..1 |
| `SIG_CAMPO` | `xsd:string` | true | 0..1 |
| `DAT_DESCOB` | `xsd:string` | true | 0..1 |
| `DAT_INICIO` | `xsd:string` | true | 0..1 |
| `ETAPA` | `xsd:string` | true | 0..1 |
| `MED_LAMINA` | `xsd:decimal` | true | 0..1 |
| `FLUIDO_PRI` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:decimal` | true | 0..1 |
| `AMBIENTE` | `xsd:string` | true | 0..1 |

### `BD_ANP:DADOS_TECNICOS_NAO_SISMICOS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | true | 0..1 |
| `N_AUTORIZA` | `xsd:string` | true | 0..1 |
| `OPERADORA` | `xsd:string` | true | 0..1 |
| `COD` | `xsd:string` | true | 0..1 |
| `EAD` | `xsd:string` | true | 0..1 |
| `TECNOLOGIA` | `xsd:string` | true | 0..1 |
| `CONF` | `xsd:string` | true | 0..1 |
| `LEVANT` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |

### `BD_ANP:DADOS_TECNICOS_SISMICA_2D`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `VOLUME` | `xsd:decimal` | true | 0..1 |
| `PROJETO` | `xsd:string` | true | 0..1 |
| `COD` | `xsd:string` | true | 0..1 |
| `TIPO_PROC` | `xsd:string` | true | 0..1 |
| `CONF` | `xsd:string` | true | 0..1 |
| `LEVANT` | `xsd:string` | true | 0..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `TIPO_LEVAN` | `xsd:string` | true | 0..1 |
| `TECNOLOGIA` | `xsd:string` | true | 0..1 |
| `AUTORIZ` | `xsd:string` | true | 0..1 |
| `INICIO` | `xsd:string` | true | 0..1 |
| `TERM_REAL` | `xsd:string` | true | 0..1 |
| `PUB_EM` | `xsd:string` | true | 0..1 |
| `ATO_NORM` | `xsd:string` | true | 0..1 |
| `BLOCO` | `xsd:string` | true | 0..1 |
| `CAMPO` | `xsd:string` | true | 0..1 |
| `EAD` | `xsd:string` | true | 0..1 |
| `OPERADORA` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:decimal` | true | 0..1 |

### `BD_ANP:DADOS_TECNICOS_SISMICA_3D`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `VOLUME` | `xsd:decimal` | true | 0..1 |
| `PROJETO` | `xsd:string` | true | 0..1 |
| `COD` | `xsd:string` | true | 0..1 |
| `TIPO_PROC` | `xsd:string` | true | 0..1 |
| `CONF` | `xsd:string` | true | 0..1 |
| `LEVANT` | `xsd:string` | true | 0..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `TIPO_LEVAN` | `xsd:string` | true | 0..1 |
| `TECNOLOGIA` | `xsd:string` | true | 0..1 |
| `AUTORIZ` | `xsd:string` | true | 0..1 |
| `INICIO` | `xsd:string` | true | 0..1 |
| `TERM_REAL` | `xsd:string` | true | 0..1 |
| `PUB_EM` | `xsd:string` | true | 0..1 |
| `ATO_NORM` | `xsd:string` | true | 0..1 |
| `BLOCO` | `xsd:string` | true | 0..1 |
| `CAMPO` | `xsd:string` | true | 0..1 |
| `EAD` | `xsd:string` | true | 0..1 |
| `OPERADORA` | `xsd:string` | true | 0..1 |
| `GEOMETRY` | `gml:GeometryPropertyType` | true | 0..1 |
| `ID` | `xsd:decimal` | true | 0..1 |

### `BD_ANP:GASODUTOS_TRANSPORTE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `GEOM` | `gml:GeometryPropertyType` | true | 0..1 |
| `DUTO` | `xsd:string` | true | 0..1 |
| `TRECHO` | `xsd:string` | true | 0..1 |
| `DIAM_POL` | `xsd:string` | true | 0..1 |
| `EXTENS_KM` | `xsd:string` | true | 0..1 |
| `INST_ORIGEM` | `xsd:string` | true | 0..1 |
| `INST_DEST` | `xsd:string` | true | 0..1 |
| `MUN_ORIG` | `xsd:string` | true | 0..1 |
| `MUN_DEST` | `xsd:string` | true | 0..1 |
| `PROPRIET` | `xsd:string` | true | 0..1 |
| `OPERADOR` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `FLUIDO` | `xsd:string` | true | 0..1 |

### `BD_ANP:Pocos_Confidenciais`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `POCO` | `xsd:string` | true | 0..1 |
| `CADASTRO` | `xsd:string` | true | 0..1 |
| `OPERADOR` | `xsd:string` | true | 0..1 |
| `POCO_OPERA` | `xsd:string` | true | 0..1 |
| `ESTADO` | `xsd:string` | true | 0..1 |
| `BACIA` | `xsd:string` | true | 0..1 |
| `BLOCO` | `xsd:string` | true | 0..1 |
| `SIG_CAMPO` | `xsd:string` | true | 0..1 |
| `CAMPO` | `xsd:string` | true | 0..1 |
| `TERRA_MAR` | `xsd:string` | true | 0..1 |
| `POS_ANP` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `RECLASSIFI` | `xsd:string` | true | 0..1 |
| `SITUACAO` | `xsd:string` | true | 0..1 |
| `INICIO` | `xsd:string` | true | 0..1 |
| `TERMINO` | `xsd:string` | true | 0..1 |
| `CONCLUSAO` | `xsd:string` | true | 0..1 |
| `TITULARIDA` | `xsd:string` | true | 0..1 |
| `LAT_4C` | `xsd:string` | true | 0..1 |
| `LONG_4C` | `xsd:string` | true | 0..1 |
| `LAT_DD` | `xsd:decimal` | true | 0..1 |
| `LONG_DD` | `xsd:decimal` | true | 0..1 |
| `DATUM_HORI` | `xsd:string` | true | 0..1 |
| `TIPO_COORD` | `xsd:string` | true | 0..1 |
| `DIRECAO` | `xsd:string` | true | 0..1 |
| `PROF_VERT` | `xsd:string` | true | 0..1 |
| `PROF_SOND` | `xsd:decimal` | true | 0..1 |
| `PROF_MEDID` | `xsd:string` | true | 0..1 |
| `REF_PROFUN` | `xsd:string` | true | 0..1 |
| `MESA_ROTAT` | `xsd:decimal` | true | 0..1 |
| `COTA_ALTIM` | `xsd:string` | true | 0..1 |
| `LAMINA_DAG` | `xsd:string` | true | 0..1 |
| `DATUM_VERT` | `xsd:string` | true | 0..1 |
| `UNI_ESTRAT` | `xsd:string` | true | 0..1 |
| `GEO_GRUP_F` | `xsd:string` | true | 0..1 |
| `GEO_FORM_F` | `xsd:string` | true | 0..1 |
| `GEO_MEMB_F` | `xsd:string` | true | 0..1 |
| `CDPE` | `xsd:string` | true | 0..1 |
| `AGP` | `xsd:string` | true | 0..1 |
| `PC` | `xsd:string` | true | 0..1 |
| `PAG` | `xsd:string` | true | 0..1 |
| `P_CONVEN` | `xsd:string` | true | 0..1 |
| `DUR_PERFUR` | `xsd:string` | true | 0..1 |
| `P_DIGITAIS` | `xsd:string` | true | 0..1 |
| `P_PROCESS` | `xsd:string` | true | 0..1 |
| `P_ESPEC` | `xsd:string` | true | 0..1 |
| `A_LATERAL` | `xsd:string` | true | 0..1 |
| `SISMICA` | `xsd:string` | true | 0..1 |
| `TEMPO_PROF` | `xsd:string` | true | 0..1 |
| `DADOS_DIRE` | `xsd:string` | true | 0..1 |
| `TESTE_CABO` | `xsd:string` | true | 0..1 |
| `TESTE_FORM` | `xsd:string` | true | 0..1 |
| `CANHONEIO` | `xsd:string` | true | 0..1 |
| `TESTEMUNHO` | `xsd:string` | true | 0..1 |
| `GEOQUIMICA` | `xsd:string` | true | 0..1 |
| `SIG_SONDA` | `xsd:string` | true | 0..1 |
| `NOME_SONDA` | `xsd:string` | true | 0..1 |
| `AT_PRESAL` | `xsd:string` | true | 0..1 |
| `GEOM` | `gml:GeometryPropertyType` | true | 0..1 |
| `OGR_FID` | `xsd:decimal` | true | 0..1 |

### `BD_ANP:Pocos_Publicos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `POCO` | `xsd:string` | true | 0..1 |
| `CADASTRO` | `xsd:string` | true | 0..1 |
| `OPERADOR` | `xsd:string` | true | 0..1 |
| `POCO_OPERA` | `xsd:string` | true | 0..1 |
| `ESTADO` | `xsd:string` | true | 0..1 |
| `BACIA` | `xsd:string` | true | 0..1 |
| `BLOCO` | `xsd:string` | true | 0..1 |
| `SIG_CAMPO` | `xsd:string` | true | 0..1 |
| `CAMPO` | `xsd:string` | true | 0..1 |
| `TERRA_MAR` | `xsd:string` | true | 0..1 |
| `POS_ANP` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `RECLASSIFI` | `xsd:string` | true | 0..1 |
| `SITUACAO` | `xsd:string` | true | 0..1 |
| `INICIO` | `xsd:string` | true | 0..1 |
| `TERMINO` | `xsd:string` | true | 0..1 |
| `CONCLUSAO` | `xsd:string` | true | 0..1 |
| `TITULARIDA` | `xsd:string` | true | 0..1 |
| `LAT_4C` | `xsd:string` | true | 0..1 |
| `LONG_4C` | `xsd:string` | true | 0..1 |
| `LAT_DD` | `xsd:decimal` | true | 0..1 |
| `LONG_DD` | `xsd:decimal` | true | 0..1 |
| `DATUM_HORI` | `xsd:string` | true | 0..1 |
| `TIPO_COORD` | `xsd:string` | true | 0..1 |
| `DIRECAO` | `xsd:string` | true | 0..1 |
| `PROF_VERT` | `xsd:string` | true | 0..1 |
| `PROF_SOND` | `xsd:decimal` | true | 0..1 |
| `PROF_MEDID` | `xsd:string` | true | 0..1 |
| `REF_PROFUN` | `xsd:string` | true | 0..1 |
| `MESA_ROTAT` | `xsd:decimal` | true | 0..1 |
| `COTA_ALTIM` | `xsd:string` | true | 0..1 |
| `LAMINA_DAG` | `xsd:string` | true | 0..1 |
| `DATUM_VERT` | `xsd:string` | true | 0..1 |
| `UNI_ESTRAT` | `xsd:string` | true | 0..1 |
| `GEO_GRUP_F` | `xsd:string` | true | 0..1 |
| `GEO_FORM_F` | `xsd:string` | true | 0..1 |
| `GEO_MEMB_F` | `xsd:string` | true | 0..1 |
| `CDPE` | `xsd:string` | true | 0..1 |
| `AGP` | `xsd:string` | true | 0..1 |
| `PC` | `xsd:string` | true | 0..1 |
| `PAG` | `xsd:string` | true | 0..1 |
| `P_CONVEN` | `xsd:string` | true | 0..1 |
| `DUR_PERFUR` | `xsd:string` | true | 0..1 |
| `P_DIGITAIS` | `xsd:string` | true | 0..1 |
| `P_PROCESS` | `xsd:string` | true | 0..1 |
| `P_ESPEC` | `xsd:string` | true | 0..1 |
| `A_LATERAL` | `xsd:string` | true | 0..1 |
| `SISMICA` | `xsd:string` | true | 0..1 |
| `TEMPO_PROF` | `xsd:string` | true | 0..1 |
| `DADOS_DIRE` | `xsd:string` | true | 0..1 |
| `TESTE_CABO` | `xsd:string` | true | 0..1 |
| `TESTE_FORM` | `xsd:string` | true | 0..1 |
| `CANHONEIO` | `xsd:string` | true | 0..1 |
| `TESTEMUNHO` | `xsd:string` | true | 0..1 |
| `GEOQUIMICA` | `xsd:string` | true | 0..1 |
| `SIG_SONDA` | `xsd:string` | true | 0..1 |
| `NOME_SONDA` | `xsd:string` | true | 0..1 |
| `AT_PRESAL` | `xsd:string` | true | 0..1 |
| `GEOM` | `gml:GeometryPropertyType` | true | 0..1 |
| `OGR_FID` | `xsd:decimal` | true | 0..1 |

### `BD_ANP:POCOS_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `OGR_FID` | `xsd:decimal` | true | 0..1 |
| `GEOM` | `gml:GeometryPropertyType` | true | 0..1 |
| `POCO` | `xsd:string` | true | 0..1 |
| `CADASTRO` | `xsd:string` | true | 0..1 |
| `OPERADOR` | `xsd:string` | true | 0..1 |
| `POCO_OPERA` | `xsd:string` | true | 0..1 |
| `ESTADO` | `xsd:string` | true | 0..1 |
| `BACIA` | `xsd:string` | true | 0..1 |
| `BLOCO` | `xsd:string` | true | 0..1 |
| `SIG_CAMPO` | `xsd:string` | true | 0..1 |
| `CAMPO` | `xsd:string` | true | 0..1 |
| `TERRA_MAR` | `xsd:string` | true | 0..1 |
| `POS_ANP` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `RECLASSIFI` | `xsd:string` | true | 0..1 |
| `SITUACAO` | `xsd:string` | true | 0..1 |
| `INICIO` | `xsd:string` | true | 0..1 |
| `TERMINO` | `xsd:string` | true | 0..1 |
| `CONCLUSAO` | `xsd:string` | true | 0..1 |
| `TITULARIDA` | `xsd:string` | true | 0..1 |
| `DATUM_HORI` | `xsd:string` | true | 0..1 |
| `TIPO_COORD` | `xsd:string` | true | 0..1 |
| `DIRECAO` | `xsd:string` | true | 0..1 |
| `PROF_VERT` | `xsd:string` | true | 0..1 |
| `PROF_SOND` | `xsd:decimal` | true | 0..1 |
| `PROF_MEDID` | `xsd:string` | true | 0..1 |
| `REF_PROFUN` | `xsd:string` | true | 0..1 |
| `MESA_ROTAT` | `xsd:decimal` | true | 0..1 |
| `COTA_ALTIM` | `xsd:string` | true | 0..1 |
| `LAMINA_DAG` | `xsd:string` | true | 0..1 |
| `DATUM_VERT` | `xsd:string` | true | 0..1 |
| `UNI_ESTRAT` | `xsd:string` | true | 0..1 |
| `GEO_GRUP_F` | `xsd:string` | true | 0..1 |
| `GEO_FORM_F` | `xsd:string` | true | 0..1 |
| `GEO_MEMB_F` | `xsd:string` | true | 0..1 |
| `CDPE` | `xsd:string` | true | 0..1 |
| `AGP` | `xsd:string` | true | 0..1 |
| `PC` | `xsd:string` | true | 0..1 |
| `PAG` | `xsd:string` | true | 0..1 |
| `P_CONVEN` | `xsd:string` | true | 0..1 |
| `DUR_PERFUR` | `xsd:string` | true | 0..1 |
| `P_DIGITAIS` | `xsd:string` | true | 0..1 |
| `P_PROCESS` | `xsd:string` | true | 0..1 |
| `P_ESPEC` | `xsd:string` | true | 0..1 |
| `A_LATERAL` | `xsd:string` | true | 0..1 |
| `SISMICA` | `xsd:string` | true | 0..1 |
| `TEMPO_PROF` | `xsd:string` | true | 0..1 |
| `DADOS_DIRE` | `xsd:string` | true | 0..1 |
| `TESTE_CABO` | `xsd:string` | true | 0..1 |
| `TESTE_FORM` | `xsd:string` | true | 0..1 |
| `CANHONEIO` | `xsd:string` | true | 0..1 |
| `TESTEMUNHO` | `xsd:string` | true | 0..1 |
| `GEOQUIMICA` | `xsd:string` | true | 0..1 |
| `SIG_SONDA` | `xsd:string` | true | 0..1 |
| `NOME_SONDA` | `xsd:string` | true | 0..1 |
| `AT_PRESAL` | `xsd:string` | true | 0..1 |

### `BD_ANP:POLIGONO_PRESAL_PLSIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `OGR_FID` | `xsd:decimal` | true | 0..1 |
| `GEOM` | `gml:GeometryPropertyType` | true | 0..1 |

### `BD_ANP:REFINARIAS_SIRGAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `GEOM` | `gml:GeometryPropertyType` | true | 0..1 |
| `SIGLA` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `MUNICIPIO` | `xsd:string` | true | 0..1 |
| `UF` | `xsd:string` | true | 0..1 |
| `AUT_OP` | `xsd:string` | true | 0..1 |
| `FONTE` | `xsd:string` | true | 0..1 |
| `LAT` | `xsd:string` | true | 0..1 |
| `LONG` | `xsd:string` | true | 0..1 |
| `PAC_DIESEL` | `xsd:string` | true | 0..1 |
| `PAC_CONV` | `xsd:string` | true | 0..1 |
| `PAC_GASOLINA` | `xsd:string` | true | 0..1 |
| `PAC_HBIO` | `xsd:string` | true | 0..1 |
| `CAPAC_BPD` | `xsd:decimal` | true | 0..1 |
| `EMPRESA` | `xsd:string` | true | 0..1 |
| `CAPAC_M3` | `xsd:decimal` | true | 0..1 |

### `BD_ANP:Terminais_GNL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `NOME` | `xsd:string` | true | 0..1 |
| `RAZAO_SOCI` | `xsd:string` | true | 0..1 |
| `AUTORIZACA` | `xsd:string` | true | 0..1 |
| `SITUACAO_A` | `xsd:string` | true | 0..1 |
| `MUNICIPIO` | `xsd:string` | true | 0..1 |
| `UF` | `xsd:string` | true | 0..1 |
| `CAPACIDADE` | `xsd:decimal` | true | 0..1 |
| `GEOM` | `gml:GeometryPropertyType` | true | 0..1 |
| `OGR_FID` | `xsd:decimal` | true | 0..1 |

### `BD_ANP:TERMINAIS_LIQ`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `OGR_FID` | `xsd:decimal` | true | 0..1 |
| `GEOM` | `gml:GeometryPropertyType` | true | 0..1 |
| `SIMP` | `xsd:decimal` | true | 0..1 |
| `RAZAO_SOCI` | `xsd:string` | true | 0..1 |
| `AUTORIZACA` | `xsd:string` | true | 0..1 |
| `SITUACAO_A` | `xsd:string` | true | 0..1 |
| `MUNICIPIO` | `xsd:string` | true | 0..1 |
| `UF` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |

### `BD_ANP:UPGN`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `NOME` | `xsd:string` | true | 0..1 |
| `MUNICIPIO` | `xsd:string` | true | 0..1 |
| `ESTADO` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `TITULARIDA` | `xsd:string` | true | 0..1 |
| `FONTE` | `xsd:string` | true | 0..1 |
| `GEOM` | `gml:GeometryPropertyType` | true | 0..1 |
| `OGR_FID` | `xsd:decimal` | true | 0..1 |

## oracleworskspace (1)

### `oracleworskspace:brasil`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:int` | true | 0..1 |
| `Id` | `xsd:int` | true | 0..1 |
| `ESTADOS` | `xsd:string` | true | 0..1 |
| `CAPITAL` | `xsd:string` | true | 0..1 |
| `SIGLA_UF` | `xsd:string` | true | 0..1 |
| `NOME_MAIUS` | `xsd:string` | true | 0..1 |
| `REGIAO` | `xsd:string` | true | 0..1 |
| `SIGLA_REGI` | `xsd:string` | true | 0..1 |
| `POPULACAO` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:string` | true | 0..1 |
| `ILHAS` | `xsd:string` | true | 0..1 |
| `ET_ID` | `xsd:int` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |

## SFI (1)

### `SFI:Postos_Combustivel`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `Identificador` | `xsd:string` | true | 0..1 |
| `Tipo_de_instalacao` | `xsd:string` | true | 0..1 |
| `CNPJ_CPF` | `xsd:string` | true | 0..1 |
| `Razao_Social` | `xsd:string` | true | 0..1 |
| `Nome` | `xsd:string` | true | 0..1 |
| `Nome_Reduzido` | `xsd:string` | true | 0..1 |
| `Telefone` | `xsd:string` | true | 0..1 |
| `E_mail` | `xsd:string` | true | 0..1 |
| `Endereco` | `xsd:string` | true | 0..1 |
| `Numero` | `xsd:string` | true | 0..1 |
| `Complemento` | `xsd:string` | true | 0..1 |
| `Bairro` | `xsd:string` | true | 0..1 |
| `Municipio` | `xsd:string` | true | 0..1 |
| `UF` | `xsd:string` | true | 0..1 |
| `CEP` | `xsd:string` | true | 0..1 |
| `Situacao_Atual` | `xsd:string` | true | 0..1 |
| `PRC_Tipo` | `xsd:string` | true | 0..1 |
| `PRC_Distribuidora` | `xsd:string` | true | 0..1 |
| `GLP_Classe_de_Armazenamento` | `xsd:string` | true | 0..1 |
| `GLP_Distribuidora` | `xsd:string` | true | 0..1 |
| `Geo_Latitude` | `xsd:string` | true | 0..1 |
| `Geo_Longitude` | `xsd:string` | true | 0..1 |
| `Geo_Latitude_ANP4C` | `xsd:string` | true | 0..1 |
| `Geo_Longitude_ANP4C` | `xsd:string` | true | 0..1 |
| `Geo_EPSG` | `xsd:string` | true | 0..1 |
| `Geo_SRC` | `xsd:string` | true | 0..1 |
| `Geo_Data_de_Obtencao` | `xsd:string` | true | 0..1 |
| `Geo_Origem_da_Informacao` | `xsd:string` | true | 0..1 |
| `Geo_Situacao_Constatada` | `xsd:string` | true | 0..1 |
