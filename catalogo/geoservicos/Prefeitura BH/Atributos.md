# Prefeitura BH — atributos das camadas

Geoportal: [[Geosserviços/Prefeitura BH/Prefeitura de Belo Horizonte — MG|Prefeitura de Belo Horizonte — MG]]

Os campos abaixo vêm de `DescribeFeatureType` (XSD), sem download de feições.

## ide_bhgeo (354)

### `ide_bhgeo:ACADEMIA_CEU_ABERTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQ_ESP` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `NOME_POPULAR` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `REF_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `GESTOR_EQUIP_ESPORT` | `xsd:string` | true | 0..1 |
| `STATUS` | `xsd:string` | true | 0..1 |
| `CODIGO` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:ACADEMIA_CIDADE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQ_SAUDE` | `xsd:decimal` | false | 1..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `SIGLA_CATEGORIA` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `LOGRADOURO` | `xsd:string` | false | 1..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | false | 1..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:ADE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ADE` | `xsd:decimal` | false | 1..1 |
| `NOME_ADE` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:ADE_11181`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ADE` | `xsd:decimal` | false | 1..1 |
| `NOME_ADE` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:ADE_INTERESSE_AMBIENTAL_11181`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ADE_INTERESSE_AMBIENTAL` | `xsd:decimal` | false | 1..1 |
| `NOME_TIPO_ADE_INTERESSE_AMB` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:ADE_SETORES_11181`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_SETOR_ADE` | `xsd:decimal` | false | 1..1 |
| `NOME_SETOR_ADE` | `xsd:string` | true | 0..1 |
| `DESC_USO_SETOR_ADE` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:AEIS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_AEIS` | `xsd:decimal` | false | 1..1 |
| `REF_LEGAL` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:AEIS_INTERESSE_AMBIENTAL_11181`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_AEIS_INTERESSE_AMBIENTAL` | `xsd:decimal` | false | 1..1 |
| `NOME_AEIS_INTERESSE_AMBIENT` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:AIP_PB_COMAER`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_AIP_BH_COMAER` | `xsd:decimal` | false | 1..1 |
| `AREA_INTERESSE_PUBLICO_BH` | `xsd:string` | false | 1..1 |
| `COTA_MAXIMA_AIP_BH` | `xsd:double` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:ALAGAMENTO_AREA_PRIORITARIA_SBN`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_AREAS_PRIORITARIAS_SBN_2022` | `xsd:decimal` | false | 1..1 |
| `AREA_M2` | `xsd:double` | true | 0..1 |
| `EXP_ALAG` | `xsd:double` | true | 0..1 |
| `EXP_DESL` | `xsd:double` | true | 0..1 |
| `EXP_INUN` | `xsd:double` | true | 0..1 |
| `EXP_ONDA` | `xsd:double` | true | 0..1 |
| `VUL_ALAG` | `xsd:double` | true | 0..1 |
| `VUL_DESL` | `xsd:double` | true | 0..1 |
| `VUL_INUN` | `xsd:double` | true | 0..1 |
| `VUL_ONDA` | `xsd:double` | true | 0..1 |
| `AC_ALAG` | `xsd:double` | true | 0..1 |
| `AC_DESL` | `xsd:double` | true | 0..1 |
| `AC_INUN` | `xsd:double` | true | 0..1 |
| `AC_ONDA` | `xsd:double` | true | 0..1 |
| `CON_AMB` | `xsd:double` | true | 0..1 |
| `CON_ANT` | `xsd:double` | true | 0..1 |
| `CON_TOT` | `xsd:double` | true | 0..1 |
| `SBN_ALAG` | `xsd:double` | true | 0..1 |
| `SBN_DESL` | `xsd:double` | true | 0..1 |
| `SBN_INUN` | `xsd:double` | true | 0..1 |
| `SBN_ONDA` | `xsd:double` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:ALIMENTACAO_ESCOLAR`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIP_SEG_ALIM_NUTRI` | `xsd:decimal` | false | 1..1 |
| `NOME_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `REFERENCIA` | `xsd:string` | true | 0..1 |
| `DIA_HORARIO` | `xsd:string` | true | 0..1 |
| `CONTATO` | `xsd:string` | true | 0..1 |
| `INFORMACOES_ADICIONAIS` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `NUMERO_BARRACAS` | `xsd:decimal` | true | 0..1 |
| `PRODUTOS_COMERCIALIZADOS` | `xsd:string` | true | 0..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:ALIMENTACAO_SOCIOASSISTENCIAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIP_SEG_ALIM_NUTRI` | `xsd:decimal` | false | 1..1 |
| `NOME_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `REFERENCIA` | `xsd:string` | true | 0..1 |
| `DIA_HORARIO` | `xsd:string` | true | 0..1 |
| `CONTATO` | `xsd:string` | true | 0..1 |
| `INFORMACOES_ADICIONAIS` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `NUMERO_BARRACAS` | `xsd:decimal` | true | 0..1 |
| `PRODUTOS_COMERCIALIZADOS` | `xsd:string` | true | 0..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:ALVARA_LOCALIZACAO_FUNCIONAMENTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ALF_PUBLICA` | `xsd:decimal` | false | 1..1 |
| `NUMERO_ALVARA` | `xsd:string` | true | 0..1 |
| `SITUACAO_ALVARA` | `xsd:string` | true | 0..1 |
| `DATA_CONCESSAO_ALVARA` | `xsd:string` | true | 0..1 |
| `DATA_VALIDADE` | `xsd:string` | true | 0..1 |
| `TIPO_DOCUMENTO` | `xsd:string` | true | 0..1 |
| `NOME_RAZAO_SOCIAL` | `xsd:string` | true | 0..1 |
| `CNPJ` | `xsd:string` | true | 0..1 |
| `INDICE_CADASTRAL_IPTU` | `xsd:string` | true | 0..1 |
| `AREA_UTILIZADA` | `xsd:decimal` | true | 0..1 |
| `CNAE_ATIV_EXERCIDA_LOCAL` | `xsd:string` | true | 0..1 |
| `CNAE_ATIV_NAO_EXERCIDA_LOCAL` | `xsd:string` | true | 0..1 |
| `ATIVIDADE_AUXILIAR` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TIPO_ACESSO_ENDR_PRINCIPAL` | `xsd:string` | true | 0..1 |
| `ENDERECO_SECUNDARIO` | `xsd:string` | true | 0..1 |
| `LINK_SIATU_ALF` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `DESCRICAO_CODIGO_AMBIENTAL` | `xsd:string` | true | 0..1 |
| `SUBCATEGORIA` | `xsd:string` | true | 0..1 |
| `TIPOLOGIA` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:AMBULANTES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ATVECON` | `xsd:decimal` | false | 1..1 |
| `CNAE_PRINCIPAL` | `xsd:string` | true | 0..1 |
| `DESCRICAO_CNAE` | `xsd:string` | true | 0..1 |
| `CNAE` | `xsd:string` | true | 0..1 |
| `NATUREZA_JURIDICA` | `xsd:string` | true | 0..1 |
| `PORTE_EMPRESA` | `xsd:string` | true | 0..1 |
| `AREA_UTILIZADA` | `xsd:string` | true | 0..1 |
| `IND_SIMPLES` | `xsd:string` | true | 0..1 |
| `IND_MEI` | `xsd:string` | true | 0..1 |
| `TIPO_UNIDADE` | `xsd:string` | true | 0..1 |
| `FORMA_ATUACAO` | `xsd:string` | true | 0..1 |
| `DESC_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `NOME_FANTASIA` | `xsd:string` | true | 0..1 |
| `CNPJ` | `xsd:string` | true | 0..1 |
| `DATA_INICIO_ATIVIDADE` | `xsd:string` | true | 0..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |
| `INSCRICAO_MUNICIPAL` | `xsd:string` | true | 0..1 |
| `IND_POSSUI_ALVARA` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:ANTENA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ANTENA` | `xsd:decimal` | false | 1..1 |
| `DESCRICAO_ETR` | `xsd:string` | true | 0..1 |
| `TIPO_SISTEMA_ETR` | `xsd:string` | true | 0..1 |
| `TIPO_FUNCAO_ETR` | `xsd:string` | true | 0..1 |
| `CODIGO_ETR` | `xsd:string` | true | 0..1 |
| `NUMERO_LICENCA` | `xsd:string` | true | 0..1 |
| `DATA_CONCESSAO` | `xsd:string` | true | 0..1 |
| `DATA_VALIDADE` | `xsd:string` | true | 0..1 |
| `OUTRAS_LICENCAS` | `xsd:string` | true | 0..1 |
| `CODIGO_SITAR` | `xsd:string` | true | 0..1 |
| `TECNOLOGIA` | `xsd:string` | true | 0..1 |
| `SITUACAO` | `xsd:string` | true | 0..1 |
| `FREQUENCIA` | `xsd:string` | true | 0..1 |
| `OBSERVACOES` | `xsd:string` | true | 0..1 |
| `DETENTORA` | `xsd:string` | true | 0..1 |
| `PRESTADORA` | `xsd:string` | true | 0..1 |
| `NUM_SETORES` | `xsd:decimal` | true | 0..1 |
| `AZIMUTE1` | `xsd:double` | true | 0..1 |
| `AZIMUTE2` | `xsd:double` | true | 0..1 |
| `AZIMUTE3` | `xsd:double` | true | 0..1 |
| `ALTURA` | `xsd:double` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:AREA_ABRANGENCIA_SAUDE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_AREA_ABRANGENCIA_SAUDE` | `xsd:decimal` | false | 1..1 |
| `COD_SMSA` | `xsd:string` | true | 0..1 |
| `NOME_AREA_ABRANGENCIA` | `xsd:string` | false | 1..1 |
| `DISTRITO_SANITARIO` | `xsd:string` | false | 1..1 |
| `NOME_CENTRO_SAUDE` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO_CS` | `xsd:string` | false | 1..1 |
| `NOME_LOGRADOURO_CS` | `xsd:string` | false | 1..1 |
| `NUMERO_IMOVEL_CS` | `xsd:decimal` | false | 1..1 |
| `NOME_BAIRRO_POPULAR_CS` | `xsd:string` | false | 1..1 |
| `TELEFONE_CENTRO_SAUDE` | `xsd:string` | true | 0..1 |
| `DATA_ULTIMA_ATUALIZACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:AREA_ESCAPE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_AREA_ESCAPE` | `xsd:decimal` | false | 1..1 |
| `TIPO_ELEMENTO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:AREA_PONDERACAO_CENSO_2010`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_AP_SC_2010` | `xsd:decimal` | false | 1..1 |
| `COD_AREA_POND_CENSO_2010` | `xsd:string` | false | 1..1 |
| `NOME_AREA_POND_CENSO_2010` | `xsd:string` | false | 1..1 |
| `TOTAL_SETORES_AGREGADOR` | `xsd:decimal` | true | 0..1 |
| `QTDE_PESSOAS_UNIVERSO` | `xsd:decimal` | false | 1..1 |
| `QTDE_DOMICILIOS_UNIVERSO` | `xsd:decimal` | false | 1..1 |
| `QTDE_PESSOAS_AMOSTRA` | `xsd:decimal` | false | 1..1 |
| `QTDE_DOMICILIOS_AMOSTRA` | `xsd:decimal` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:AREA_PRESERVACAO_PERMANENTE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_APP` | `xsd:decimal` | false | 1..1 |
| `CLASSIFICACAO_APP` | `xsd:string` | false | 1..1 |
| `ORIGEM` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:AREA_PROTECAO_CULTURAL_CDPCM-BH`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_AREA_PROTECAO_CULTURAL` | `xsd:decimal` | false | 1..1 |
| `DESC_TIPO_AREA_PROTECAO` | `xsd:string` | true | 0..1 |
| `NOME_AREA_PROTECAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:AREA_PROTECAO_CULTURAL_IEPHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_AREA_PROTECAO_CULTURAL` | `xsd:decimal` | false | 1..1 |
| `DESC_TIPO_AREA_PROTECAO` | `xsd:string` | true | 0..1 |
| `NOME_AREA_PROTECAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:AREA_PROTECAO_CULTURAL_IPHAN`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_AREA_PROTECAO_CULTURAL` | `xsd:decimal` | false | 1..1 |
| `DESC_TIPO_AREA_PROTECAO` | `xsd:string` | true | 0..1 |
| `NOME_AREA_PROTECAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:AREA_PUBLICA_WIFI`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIP_HOTSPOT` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `CODIGO_PROJETO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:AREA_RISCO_ASSOCIADO_ESCAVACOES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ARG` | `xsd:decimal` | false | 1..1 |
| `RISCO_GEOLOGICO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:AREA_RISCO_CONTAMINACAO_LENCOL_FREATICO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ARG` | `xsd:decimal` | false | 1..1 |
| `RISCO_GEOLOGICO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:AREA_RISCO_EROSAO_ASSOREAMENTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ARG` | `xsd:decimal` | false | 1..1 |
| `RISCO_GEOLOGICO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:AREA_RISCO_ESCORREGAMENTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ARG` | `xsd:decimal` | false | 1..1 |
| `RISCO_GEOLOGICO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:AREA_RISCO_INUNDACAO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ARG` | `xsd:decimal` | false | 1..1 |
| `RISCO_GEOLOGICO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:AREAS_CONTAMINADAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_AREA_CONTAMINADA` | `xsd:decimal` | false | 1..1 |
| `RAZAO_SOCIAL` | `xsd:string` | true | 0..1 |
| `NOME_FANTASIA` | `xsd:string` | true | 0..1 |
| `CNPJ` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `NOME_CIRCUNSCRICAO_HIDROGRAFICA` | `xsd:string` | false | 1..1 |
| `AREA_DESCOMISSIONADA` | `xsd:string` | true | 0..1 |
| `DESC_CATEGORIA_USO_DECLARADO` | `xsd:string` | true | 0..1 |
| `DESC_FASE_LIVRE_CONTAMINACAO` | `xsd:string` | true | 0..1 |
| `SIGLA_ETAPA_GERENCIAMENTO` | `xsd:string` | false | 1..1 |
| `DESC_ETAPA_GERENCIAMENTO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:ARTICULACAO_1`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ARTICULACAO_1` | `xsd:decimal` | false | 1..1 |
| `NUM_QUADRICULA` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:ARTICULACAO_1942`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ARTICUL_1942` | `xsd:decimal` | false | 1..1 |
| `NUM_FOLHA` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:ARTICULACAO_1953`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ARTICUL_1953` | `xsd:decimal` | false | 1..1 |
| `NUM_FOLHA` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:ARTICULACAO_2`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ARTICUL2` | `xsd:decimal` | false | 1..1 |
| `NOARQXWD` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:ARTICULACAO_400`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ARTICULACAO_400` | `xsd:decimal` | false | 1..1 |
| `COD_QUADRICULA` | `xsd:string` | true | 0..1 |
| `COD_REGIONAL` | `xsd:string` | true | 0..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:SurfacePropertyType` | true | 0..1 |
| `COD_SMSA` | `xsd:string` | true | 0..1 |
| `NOME_AREA_ABRANGENCIA` | `xsd:string` | true | 0..1 |
| `REGIONAL_REF_CENTROIDE` | `xsd:string` | true | 0..1 |
| `LATITUDE_CENTROIDE` | `xsd:string` | true | 0..1 |
| `LONGITUDE_CENTROIDE` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:ARTICULACAO_5`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ARTICULACAO_5` | `xsd:decimal` | false | 1..1 |
| `NUM_QUADRICULA` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:ATIVIDADE_ECONOMICA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ATIV_ECON_ESTABELECIMENTO` | `xsd:decimal` | false | 1..1 |
| `CNAE_PRINCIPAL` | `xsd:string` | true | 0..1 |
| `DESCRICAO_CNAE_PRINCIPAL` | `xsd:string` | true | 0..1 |
| `CNAE` | `xsd:string` | true | 0..1 |
| `DATA_INICIO_ATIVIDADE` | `xsd:string` | true | 0..1 |
| `NATUREZA_JURIDICA` | `xsd:string` | true | 0..1 |
| `PORTE_EMPRESA` | `xsd:string` | true | 0..1 |
| `AREA_UTILIZADA` | `xsd:string` | true | 0..1 |
| `IND_SIMPLES` | `xsd:string` | true | 0..1 |
| `IND_MEI` | `xsd:string` | true | 0..1 |
| `IND_POSSUI_ALVARA` | `xsd:string` | true | 0..1 |
| `TIPO_UNIDADE` | `xsd:string` | true | 0..1 |
| `FORMA_ATUACAO` | `xsd:string` | true | 0..1 |
| `DESC_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `NOME_FANTASIA` | `xsd:string` | true | 0..1 |
| `CNPJ` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:ATIVIDADE_ECONOMICAS_AUTONOMOS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `COD_INSCRICAO_MUNICIPAL` | `xsd:string` | false | 1..1 |
| `AREA_UTILIZADA` | `xsd:decimal` | true | 0..1 |
| `AREA_SUJEITA_TFS` | `xsd:decimal` | true | 0..1 |
| `CODIGO_CBO` | `xsd:string` | true | 0..1 |
| `DESCRICAO_CBO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `DATA_INICIO_ATIVIDADE` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:ATRATIVO_TURISTICO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ATRATIVO_TURISTICO` | `xsd:decimal` | false | 1..1 |
| `DESCRICAO` | `xsd:string` | true | 0..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `LINK_SITE_REDE_SOCIAL` | `xsd:string` | true | 0..1 |
| `REF_LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:BACIA_HIDROGRAFICA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_BHID` | `xsd:decimal` | false | 1..1 |
| `COD_BACIA` | `xsd:decimal` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `AREA_M2` | `xsd:decimal` | true | 0..1 |
| `PERIMETRO_M` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:BACIA_HIDROGRAFICA_ELEMENTAR`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_BHIDEL` | `xsd:decimal` | false | 1..1 |
| `CODIGO_BHIDEL` | `xsd:string` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `AREA_M2` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:BAIRRO_OFICIAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_BAC` | `xsd:decimal` | false | 1..1 |
| `CODIGO` | `xsd:decimal` | false | 1..1 |
| `TIPO` | `xsd:string` | false | 1..1 |
| `NOME` | `xsd:string` | false | 1..1 |
| `AREA_KM2` | `xsd:decimal` | true | 0..1 |
| `PERIMETR_M` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:BAIRRO_POPULAR`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID` | `xsd:decimal` | false | 1..1 |
| `CODIGO` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | false | 1..1 |
| `AREA_KM2` | `xsd:decimal` | true | 0..1 |
| `PERIMETR_M` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:BANCO_ALIMENTOS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIP_SEG_ALIM_NUTRI` | `xsd:decimal` | false | 1..1 |
| `NOME_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `REFERENCIA` | `xsd:string` | true | 0..1 |
| `DIA_HORARIO` | `xsd:string` | true | 0..1 |
| `CONTATO` | `xsd:string` | true | 0..1 |
| `INFORMACOES_ADICIONAIS` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `NUMERO_BARRACAS` | `xsd:decimal` | true | 0..1 |
| `PRODUTOS_COMERCIALIZADOS` | `xsd:string` | true | 0..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:BANHEIRO_PUBLICO_AUTOLIMPANTE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_BANHEIRO_PUBLICO` | `xsd:decimal` | false | 1..1 |
| `REGIONAL` | `xsd:string` | true | 0..1 |
| `HORARIO_FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `DATA_INICIO_OPERACAO` | `xsd:string` | true | 0..1 |
| `DIMENSAO_HORIZONTAL` | `xsd:decimal` | true | 0..1 |
| `DIMENSAO_VERTICAL` | `xsd:decimal` | true | 0..1 |
| `AREA` | `xsd:decimal` | true | 0..1 |
| `TIPO_LOCAL` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `REFERENCIA_LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:BARES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ATVECON` | `xsd:decimal` | false | 1..1 |
| `CNAE_PRINCIPAL` | `xsd:string` | true | 0..1 |
| `DESCRICAO_CNAE` | `xsd:string` | true | 0..1 |
| `CNAE` | `xsd:string` | true | 0..1 |
| `NATUREZA_JURIDICA` | `xsd:string` | true | 0..1 |
| `PORTE_EMPRESA` | `xsd:string` | true | 0..1 |
| `AREA_UTILIZADA` | `xsd:string` | true | 0..1 |
| `IND_SIMPLES` | `xsd:string` | true | 0..1 |
| `IND_MEI` | `xsd:string` | true | 0..1 |
| `TIPO_UNIDADE` | `xsd:string` | true | 0..1 |
| `FORMA_ATUACAO` | `xsd:string` | true | 0..1 |
| `DESC_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `NOME_FANTASIA` | `xsd:string` | true | 0..1 |
| `CNPJ` | `xsd:string` | true | 0..1 |
| `DATA_INICIO_ATIVIDADE` | `xsd:string` | true | 0..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |
| `INSCRICAO_MUNICIPAL` | `xsd:string` | true | 0..1 |
| `IND_POSSUI_ALVARA` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:BEM_CULTURAL_IEPHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_BEM_CULTURAL` | `xsd:decimal` | false | 1..1 |
| `NOME_BEM_CULTURAL` | `xsd:string` | true | 0..1 |
| `DESC_TIPO_GRAU_PROTECAO` | `xsd:string` | true | 0..1 |
| `TIPO_BEM_CULTURAL` | `xsd:string` | true | 0..1 |
| `IND_TOMBAMENTO_ESTADUAL` | `xsd:string` | true | 0..1 |
| `IND_TOMBAMENTO_FEDERAL` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:BEM_CULTURAL_IMATERIAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_BEM_CULTURAL_IMATERIAL` | `xsd:decimal` | false | 1..1 |
| `NOME_BEM_CULTURAL_IMATERIAL` | `xsd:string` | true | 0..1 |
| `DESC_TIPO_GRAU_PROTECAO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:BEM_CULTURAL_IMOVEL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_BEM_CULTURAL_IMOVEL` | `xsd:decimal` | false | 1..1 |
| `NOME_BEM_CULTURAL_IMOVEL` | `xsd:string` | true | 0..1 |
| `DESC_TIPO_GRAU_PROTECAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:BEM_CULTURAL_INTEGRADO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_BEM_CULTURAL_INTEGRADO` | `xsd:decimal` | false | 1..1 |
| `NOME_BEM_CULTURAL_INTEGRADO` | `xsd:string` | true | 0..1 |
| `DESC_TIPO_GRAU_PROTECAO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:BEM_CULTURAL_IPHAN`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_BEM_CULTURAL` | `xsd:decimal` | false | 1..1 |
| `NOME_BEM_CULTURAL` | `xsd:string` | true | 0..1 |
| `DESC_TIPO_GRAU_PROTECAO` | `xsd:string` | true | 0..1 |
| `TIPO_BEM_CULTURAL` | `xsd:string` | true | 0..1 |
| `IND_TOMBAMENTO_ESTADUAL` | `xsd:string` | true | 0..1 |
| `IND_TOMBAMENTO_FEDERAL` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:BEM_CULTURAL_MOVEL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_BEM_CULTURAL_MOVEL` | `xsd:decimal` | false | 1..1 |
| `NOME_BEM_CULTURAL_MOVEL` | `xsd:string` | true | 0..1 |
| `DESC_TIPO_GRAU_PROTECAO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:BEM_CULTURAL_NATURAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_BEM_CULTURAL_NATURAL` | `xsd:decimal` | false | 1..1 |
| `NOME_BEM_CULTURAL_NATURAL` | `xsd:string` | true | 0..1 |
| `DESC_TIPO_GRAU_PROTECAO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:BEM_CULTURAL_URBANISTICO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_BEM_CULTURAL_URBANISTICO` | `xsd:decimal` | false | 1..1 |
| `NOME_BEM_CULTURAL_URBANISTICO` | `xsd:string` | true | 0..1 |
| `DESC_TIPO_GRAU_PROTECAO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiGeometryPropertyType` | true | 0..1 |

### `ide_bhgeo:BH_RESOLVE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_REFERENCIA_LOCALIZACAO` | `xsd:decimal` | false | 1..1 |
| `NOME_REFERENCIA_LOCALIZACAO` | `xsd:string` | false | 1..1 |
| `ID_CATEGORIA_REFERENCIA_LOC` | `xsd:decimal` | false | 1..1 |
| `TIPO_REFERENCIA_LOCALIZACAO` | `xsd:string` | false | 1..1 |
| `ID_ENDERECO_PBH` | `xsd:decimal` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `CONTATO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:BH_RESOLVE_VELHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_REFERENCIA_LOCALIZACAO` | `xsd:decimal` | false | 1..1 |
| `NOME_REFERENCIA_LOCALIZACAO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:BREJO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_BRJ` | `xsd:decimal` | false | 1..1 |
| `CODIGO_FLORESTAL` | `xsd:string` | true | 0..1 |
| `APP` | `xsd:decimal` | true | 0..1 |
| `GENESE` | `xsd:string` | true | 0..1 |
| `TEMPORALIDADE` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:CA_BASICO_11181`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_CA_BASICO` | `xsd:decimal` | false | 1..1 |
| `CA_BASICO` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:CADASTRO_ENGENHO_PUBLICIDADE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_CADEP` | `xsd:decimal` | false | 1..1 |
| `CNPJ` | `xsd:string` | true | 0..1 |
| `INSCRICAO_MUNICIPAL` | `xsd:string` | true | 0..1 |
| `NUMERO_CADEP` | `xsd:string` | true | 0..1 |
| `ENDERECO_INSTALACAO` | `xsd:string` | true | 0..1 |
| `DATA_INSTALACAO` | `xsd:date` | true | 0..1 |
| `FORMA_VEICULACAO` | `xsd:string` | true | 0..1 |
| `TIPO_ILUMINACAO` | `xsd:string` | true | 0..1 |
| `TIPO_MOVIMENTO` | `xsd:string` | true | 0..1 |
| `TIPO_MENSAGEM` | `xsd:string` | true | 0..1 |
| `AREA_TRIBUTADA` | `xsd:decimal` | true | 0..1 |
| `NUMERO_LICENCA` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:CADASTRO_IMOBILIARIO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `INDICE_CADASTRAL` | `xsd:string` | false | 1..1 |
| `NULOTCTM` | `xsd:string` | true | 0..1 |
| `ZONEAMENTO_PVIPTU` | `xsd:string` | true | 0..1 |
| `FREQUENCIA_COLETA` | `xsd:string` | true | 0..1 |
| `IND_MEIO_FIO` | `xsd:string` | true | 0..1 |
| `IND_PAVIMENTACAO` | `xsd:string` | true | 0..1 |
| `IND_ARBORIZACAO` | `xsd:string` | true | 0..1 |
| `IND_GALERIA_PLUVIAL` | `xsd:string` | true | 0..1 |
| `IND_ILUMINACAO_PUBLICA` | `xsd:string` | true | 0..1 |
| `IND_REDE_ESGOTO` | `xsd:string` | true | 0..1 |
| `IND_REDE_AGUA` | `xsd:string` | true | 0..1 |
| `IND_REDE_TELEFONICA` | `xsd:string` | true | 0..1 |
| `AREA_TERRENO` | `xsd:decimal` | true | 0..1 |
| `AREA_CONSTRUCAO` | `xsd:decimal` | true | 0..1 |
| `TIPO_CONSTRUTIVO` | `xsd:string` | true | 0..1 |
| `TIPO_OCUPACAO` | `xsd:string` | true | 0..1 |
| `PADRAO_ACABAMENTO` | `xsd:string` | true | 0..1 |
| `QUANTIDADE_ECONOMIAS` | `xsd:decimal` | true | 0..1 |
| `FRACAO_IDEAL` | `xsd:decimal` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `CEP` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO_ENDERECO` | `xsd:string` | true | 0..1 |
| `ZONA_HOMOGENEA` | `xsd:string` | true | 0..1 |
| `TIPOLOGIA` | `xsd:string` | true | 0..1 |
| `CIB` | `xsd:string` | true | 0..1 |
| `ANO_CONSTRUCAO` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:CAMPO_FUTEBOL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQ_ESP` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `NOME_POPULAR` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `REF_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `GESTOR_EQUIP_ESPORT` | `xsd:string` | true | 0..1 |
| `STATUS` | `xsd:string` | true | 0..1 |
| `CODIGO` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:CANTEIRO_CENTRAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_CCTRL` | `xsd:decimal` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:CAPELA_VELORIO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_UNIDADE` | `xsd:decimal` | false | 1..1 |
| `NOME_UNIDADE` | `xsd:string` | false | 1..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `TELEFONE_PRINCIPAL` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:CASA_ACOLHIMENTO_LGBT`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIPAMENTO_CIDADANIA` | `xsd:decimal` | false | 1..1 |
| `NOME_EQUIPAMENTO_CIDADANIA` | `xsd:string` | false | 1..1 |
| `DESC_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `LETRA_IMOVEL` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `DESCRICAO_CATEGORIA` | `xsd:string` | true | 0..1 |
| `DIAS_FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `HORARIO_FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:CEMITERIO_PARTICULAR`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_CEMITERIO_PARTICULAR` | `xsd:decimal` | false | 1..1 |
| `NOME_CEMITERIO_PARTICULAR` | `xsd:string` | false | 1..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `LOGRADOURO` | `xsd:string` | false | 1..1 |
| `NUMERO` | `xsd:decimal` | false | 1..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:CEMITERIO_PUBLICO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_UNIDADE` | `xsd:decimal` | false | 1..1 |
| `NOME_UNIDADE` | `xsd:string` | false | 1..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `TELEFONE_PRINCIPAL` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:CENTRAL_ABASTECIMENTO_CAFA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIP_SEG_ALIM_NUTRI` | `xsd:decimal` | false | 1..1 |
| `NOME_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `REFERENCIA` | `xsd:string` | true | 0..1 |
| `DIA_HORARIO` | `xsd:string` | true | 0..1 |
| `CONTATO` | `xsd:string` | true | 0..1 |
| `INFORMACOES_ADICIONAIS` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `NUMERO_BARRACAS` | `xsd:decimal` | true | 0..1 |
| `PRODUTOS_COMERCIALIZADOS` | `xsd:string` | true | 0..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:CENTRALIDADE_LOCAL_11181`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_CENTRALIDADE_LOCAL` | `xsd:decimal` | false | 1..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:CENTRO_ATENDIMENTO_TURISTA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_CENTRO_ATENDIMENTO_TURISTA` | `xsd:decimal` | false | 1..1 |
| `NOME_CENTRO_ATEND_TURISTA` | `xsd:string` | false | 1..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `LETRA_IMOVEL` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `PORTAL_BELO_HORIZONTE` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | false | 1..1 |

### `ide_bhgeo:CENTRO_DIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_REDE_SOCIOASSISTENCIAL` | `xsd:decimal` | false | 1..1 |
| `ID_ENTIDADE` | `xsd:decimal` | false | 1..1 |
| `NOME_ENTIDADE` | `xsd:string` | true | 0..1 |
| `DESC_CATEGORIA` | `xsd:string` | true | 0..1 |
| `SIGLA_CATEGORIA` | `xsd:string` | true | 0..1 |
| `TIPO_EXECUCAO` | `xsd:string` | true | 0..1 |
| `NOME_SERVICO` | `xsd:string` | true | 0..1 |
| `NIVEL_PROTECAO` | `xsd:string` | true | 0..1 |
| `SIGLA_PROTECAO` | `xsd:string` | true | 0..1 |
| `PUBLICO_USUARIO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:CENTRO_ESPECIALIZADO_ATENDIMENTO_MULHER`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIPAMENTO_CIDADANIA` | `xsd:decimal` | false | 1..1 |
| `NOME_EQUIPAMENTO_CIDADANIA` | `xsd:string` | false | 1..1 |
| `DESC_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `LETRA_IMOVEL` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `DESCRICAO_CATEGORIA` | `xsd:string` | true | 0..1 |
| `DIAS_FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `HORARIO_FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:CENTRO_POP`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_REDE_SOCIOASSISTENCIAL` | `xsd:decimal` | false | 1..1 |
| `ID_ENTIDADE` | `xsd:decimal` | false | 1..1 |
| `NOME_ENTIDADE` | `xsd:string` | true | 0..1 |
| `DESC_CATEGORIA` | `xsd:string` | true | 0..1 |
| `SIGLA_CATEGORIA` | `xsd:string` | true | 0..1 |
| `TIPO_EXECUCAO` | `xsd:string` | true | 0..1 |
| `NOME_SERVICO` | `xsd:string` | true | 0..1 |
| `NIVEL_PROTECAO` | `xsd:string` | true | 0..1 |
| `SIGLA_PROTECAO` | `xsd:string` | true | 0..1 |
| `PUBLICO_USUARIO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:CENTRO_REFERENCIA_JUVENTUDES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIPAMENTO_CIDADANIA` | `xsd:decimal` | false | 1..1 |
| `NOME_EQUIPAMENTO_CIDADANIA` | `xsd:string` | false | 1..1 |
| `DESC_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `LETRA_IMOVEL` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `DESCRICAO_CATEGORIA` | `xsd:string` | true | 0..1 |
| `DIAS_FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `HORARIO_FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:CENTRO_REFERENCIA_LGBT`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIPAMENTO_CIDADANIA` | `xsd:decimal` | false | 1..1 |
| `NOME_EQUIPAMENTO_CIDADANIA` | `xsd:string` | false | 1..1 |
| `DESC_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `LETRA_IMOVEL` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `DESCRICAO_CATEGORIA` | `xsd:string` | true | 0..1 |
| `DIAS_FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `HORARIO_FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:CENTRO_REFERENCIA_PESSOA_IDOSA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIPAMENTO_CIDADANIA` | `xsd:decimal` | false | 1..1 |
| `NOME_EQUIPAMENTO_CIDADANIA` | `xsd:string` | false | 1..1 |
| `DESC_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `LETRA_IMOVEL` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `DESCRICAO_CATEGORIA` | `xsd:string` | true | 0..1 |
| `DIAS_FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `HORARIO_FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:CENTRO_REFERENCIA_SEGURANCA_ALIMENTAR_NUTRI`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIP_SEG_ALIM_NUTRI` | `xsd:decimal` | false | 1..1 |
| `NOME_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `REFERENCIA` | `xsd:string` | true | 0..1 |
| `DIA_HORARIO` | `xsd:string` | true | 0..1 |
| `CONTATO` | `xsd:string` | true | 0..1 |
| `INFORMACOES_ADICIONAIS` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `NUMERO_BARRACAS` | `xsd:decimal` | true | 0..1 |
| `PRODUTOS_COMERCIALIZADOS` | `xsd:string` | true | 0..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:CENTRO_SAUDE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQ_SAUDE` | `xsd:decimal` | false | 1..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `SIGLA_CATEGORIA` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `LOGRADOURO` | `xsd:string` | false | 1..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | false | 1..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:CENTROS_ESPECIALIDADES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQ_SAUDE` | `xsd:decimal` | false | 1..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `SIGLA_CATEGORIA` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `LOGRADOURO` | `xsd:string` | false | 1..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | false | 1..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:CIRCULACAO_VIARIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_TCV` | `xsd:decimal` | false | 1..1 |
| `TIPO_TRECHO_CIRCULACAO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `COD_LOGRADOURO` | `xsd:decimal` | true | 0..1 |
| `ID_NO_CIRC_INICIAL` | `xsd:decimal` | true | 0..1 |
| `ID_NO_CIRC_FINAL` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:CIRCUNSCRICAO_CARTORIAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_CIRCUNSCRICAO_CARTORIAL` | `xsd:decimal` | false | 1..1 |
| `CODIGO_CIRCUNSCRICAO_CARTORIAL` | `xsd:decimal` | false | 1..1 |
| `DESC_CIRCUNSCRICAO_CARTORIAL` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:CLASSIFICACAO_CALCADA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_CLASSIFICACAO_CALCADA` | `xsd:decimal` | false | 1..1 |
| `CLASSIFICACAO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:CLASSIFICACAO_VIARIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_HV` | `xsd:decimal` | false | 1..1 |
| `ID_TRECHO` | `xsd:decimal` | false | 1..1 |
| `TPLOG` | `xsd:string` | true | 0..1 |
| `NOLOG` | `xsd:string` | true | 0..1 |
| `SITUACAO` | `xsd:string` | true | 0..1 |
| `DESC_CLASSIF_VIARIA` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:CLASSIFICACAO_VIARIA_11181`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_CLASSIFICACAO_VIARIA` | `xsd:decimal` | false | 1..1 |
| `TP_LOG` | `xsd:string` | true | 0..1 |
| `NO_LOG` | `xsd:string` | true | 0..1 |
| `CLASSIFICACAO_VIARIA` | `xsd:string` | true | 0..1 |
| `SUBDIVISAO_CLASSF_VIARIA` | `xsd:string` | true | 0..1 |
| `AFASTAMENTO_FRONTAL` | `xsd:string` | true | 0..1 |
| `TIPO_LARGURA_VIA` | `xsd:string` | true | 0..1 |
| `DESCRICAO_TIPO_LARGURA` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:COEF_CN_CENARIO_2021`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_COEF_CN_CENARIO_2021` | `xsd:decimal` | false | 1..1 |
| `SUBBACIA` | `xsd:decimal` | false | 1..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `AREA_M2` | `xsd:decimal` | true | 0..1 |
| `COEFICIENTE_CN_2021` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:COEF_CN_CENARIO_LEI11181`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_COEF_CN_CENARIO_LEI11181` | `xsd:decimal` | false | 1..1 |
| `SUBBACIA` | `xsd:decimal` | false | 1..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `AREA_M2` | `xsd:decimal` | true | 0..1 |
| `CNPD_LEI11181` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:COEF_ESCOAMENTO_SUPERFICIAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_COEF_ESCOAMENTO_SUPERFICIAL` | `xsd:decimal` | false | 1..1 |
| `COEFICIENTE_ESCOAMENTO` | `xsd:decimal` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:COLETA_RESIDUOS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_CR` | `xsd:decimal` | false | 1..1 |
| `ID_TRECHO` | `xsd:decimal` | true | 0..1 |
| `NOME_DISTRITO_COLETA` | `xsd:string` | true | 0..1 |
| `PROGRAMACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `TURNO` | `xsd:string` | true | 0..1 |
| `NUM_QUADRA` | `xsd:string` | true | 0..1 |
| `ID_DISTRITO_COLETA` | `xsd:decimal` | true | 0..1 |

### `ide_bhgeo:COLETA_SELETIVA_PORTA_PORTA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_COLETA_SELETIVA_PORTA_PORTA` | `xsd:decimal` | false | 1..1 |
| `ID_BASE_TRECHO` | `xsd:decimal` | true | 0..1 |
| `PROGRAMACAO` | `xsd:string` | true | 0..1 |
| `TURNO` | `xsd:string` | true | 0..1 |
| `NOME_DISTRITO` | `xsd:string` | true | 0..1 |
| `COOPERATIVA_RESPONSAVEL` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:COMERCIO_EQUIPAMENTO_INFORMATICA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ATVECON` | `xsd:decimal` | false | 1..1 |
| `CNAE_PRINCIPAL` | `xsd:string` | true | 0..1 |
| `DESCRICAO_CNAE` | `xsd:string` | true | 0..1 |
| `CNAE` | `xsd:string` | true | 0..1 |
| `NATUREZA_JURIDICA` | `xsd:string` | true | 0..1 |
| `PORTE_EMPRESA` | `xsd:string` | true | 0..1 |
| `AREA_UTILIZADA` | `xsd:string` | true | 0..1 |
| `IND_SIMPLES` | `xsd:string` | true | 0..1 |
| `IND_MEI` | `xsd:string` | true | 0..1 |
| `TIPO_UNIDADE` | `xsd:string` | true | 0..1 |
| `FORMA_ATUACAO` | `xsd:string` | true | 0..1 |
| `DESC_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `NOME_FANTASIA` | `xsd:string` | true | 0..1 |
| `CNPJ` | `xsd:string` | true | 0..1 |
| `DATA_INICIO_ATIVIDADE` | `xsd:string` | true | 0..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |
| `INSCRICAO_MUNICIPAL` | `xsd:string` | true | 0..1 |
| `IND_POSSUI_ALVARA` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:COMUNIDADE_QUILOMBOLA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_COMUNIDADE_QUILOMBOLA` | `xsd:decimal` | false | 1..1 |
| `NOME_COMUNIDADE` | `xsd:string` | false | 1..1 |
| `AREA_INCRA` | `xsd:decimal` | true | 0..1 |
| `PERIMETRO_INCRA` | `xsd:decimal` | true | 0..1 |
| `NUM_PROCESSO_INCRA` | `xsd:string` | true | 0..1 |
| `NUM_PROCESSO_FCP` | `xsd:string` | true | 0..1 |
| `SITUACAO` | `xsd:string` | true | 0..1 |
| `OBSERVACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:SurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:CONEXAO_FUNDO_VALE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_CONEXAO_FUNDO_VALE` | `xsd:decimal` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:CONEXAO_VERDE_11181`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_CONEXAO_VERDE` | `xsd:decimal` | false | 1..1 |
| `TP_LOGRAD` | `xsd:string` | false | 1..1 |
| `LOGRADOURO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:CONJUNTO_HABITACIONAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_CHB` | `xsd:decimal` | false | 1..1 |
| `NOME_CONJUNTO_HABITACIONAL` | `xsd:string` | false | 1..1 |
| `DESC_AGRUPAMENTO` | `xsd:string` | true | 0..1 |
| `STATUS_CONSTRUCAO` | `xsd:string` | true | 0..1 |
| `STATUS_REGULARIZACAO` | `xsd:string` | true | 0..1 |
| `NUM_UNID_INICIAR` | `xsd:decimal` | true | 0..1 |
| `NUM_UNID_ANDAMENTO` | `xsd:decimal` | true | 0..1 |
| `NUM_UNID_CONCLUSAO` | `xsd:decimal` | true | 0..1 |
| `DESC_PROGRAMA` | `xsd:string` | true | 0..1 |
| `DESC_FONTE_RECURSO` | `xsd:string` | true | 0..1 |
| `ANO_PREVISAO_CONCLUSAO` | `xsd:string` | true | 0..1 |
| `ANO_PRIMEIRA_ENTREGA_UH` | `xsd:string` | true | 0..1 |
| `ANO_ULTIMA_ENTREGA_UH` | `xsd:string` | true | 0..1 |
| `DESC_FAIXA_RENDA` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:CONSELHO_TUTELAR`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIPAMENTO_CIDADANIA` | `xsd:decimal` | false | 1..1 |
| `NOME_EQUIPAMENTO_CIDADANIA` | `xsd:string` | false | 1..1 |
| `DESC_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `LETRA_IMOVEL` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `DESCRICAO_CATEGORIA` | `xsd:string` | true | 0..1 |
| `DIAS_FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `HORARIO_FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:CORREDOR_ECOLOGICO_SERRA_CURRAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_COR_ECO_ESPI_SERRA_CURRAL` | `xsd:decimal` | false | 1..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `DESC_CATEGORIA` | `xsd:string` | true | 0..1 |
| `UCA_ORIGEM` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `LEGISLACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:CORREDOR_ECOLOGICO_SERRA_CURRAL_VELHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_UCA` | `xsd:decimal` | false | 1..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `DESC_CATEGORIA` | `xsd:string` | true | 0..1 |
| `COMPETENCIA` | `xsd:string` | false | 1..1 |
| `NOME` | `xsd:string` | false | 1..1 |
| `TIPO_USO` | `xsd:string` | true | 0..1 |
| `LEGISLACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:COZINHA_SOLIDARIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIP_SEG_ALIM_NUTRI` | `xsd:decimal` | false | 1..1 |
| `NOME_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `REFERENCIA` | `xsd:string` | true | 0..1 |
| `DIA_HORARIO` | `xsd:string` | true | 0..1 |
| `CONTATO` | `xsd:string` | true | 0..1 |
| `INFORMACOES_ADICIONAIS` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `NUMERO_BARRACAS` | `xsd:decimal` | true | 0..1 |
| `PRODUTOS_COMERCIALIZADOS` | `xsd:string` | true | 0..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:CRECHES_CONVENIADAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIP_EDUCACAO` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `DEPENDENCIA_ADM` | `xsd:string` | true | 0..1 |
| `CODIGO_INEP` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `REGIONAL` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:CURSO_DAGUA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_CURDG` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `CODIGO_FLORESTAL` | `xsd:string` | true | 0..1 |
| `TIPO_CANAL` | `xsd:string` | false | 1..1 |
| `APP` | `xsd:decimal` | true | 0..1 |
| `CLASSIF_HIDROLOGICA` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `TEMPORALIDADE` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:CURVA_DE_NIVEL_5M`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_CN5M` | `xsd:decimal` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | false | 1..1 |
| `COTA` | `xsd:decimal` | false | 1..1 |

### `ide_bhgeo:CURVA_NIVEL_SEGMENTADA_1M`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_CURVA_SEC_SEGMENTADA` | `xsd:decimal` | false | 1..1 |
| `ID_CURVA_SEC` | `xsd:decimal` | false | 1..1 |
| `COTA_CURVA_NIVEL` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:CurvePropertyType` | true | 0..1 |

### `ide_bhgeo:DECLIV_TRECHO_LOGRAD_SEG_2015`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_DECLIV_TRECHO_SEG_OAE_2015` | `xsd:decimal` | false | 1..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `DECLIVIDADE_PERCENTUAL` | `xsd:decimal` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:DECLIV_TRECHO_LOGRAD_SEG_2015_ACESS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_DECLIV_TRECHO_SEG_OAE_2015` | `xsd:decimal` | false | 1..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `DECLIVIDADE_PERCENTUAL` | `xsd:decimal` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:DECLIV_TRECHO_LOGRADOURO_2007`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_DECLIV_TRECHO_UFMG_2007` | `xsd:decimal` | false | 1..1 |
| `ID_TRECHO` | `xsd:decimal` | true | 0..1 |
| `COMPRIMENTO` | `xsd:double` | true | 0..1 |
| `LARGURA` | `xsd:double` | true | 0..1 |
| `DECLIVIDADE_MINIMA` | `xsd:double` | true | 0..1 |
| `DECLIVIDADE_MEDIA` | `xsd:double` | true | 0..1 |
| `DECLIVIDADE_MAXIMA` | `xsd:double` | true | 0..1 |
| `COTA_MINIMA` | `xsd:double` | true | 0..1 |
| `COTA_MEDIA` | `xsd:double` | true | 0..1 |
| `COTA_MAXIMA` | `xsd:double` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:DECLIVIDADE_TRECHO_LOGRADOURO_2015`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_DECLIV_TRECHO_ESTATIST_2015` | `xsd:decimal` | false | 1..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `QTDE_SEGMENTOS` | `xsd:decimal` | true | 0..1 |
| `DECLIVIDADE_MINIMA` | `xsd:decimal` | true | 0..1 |
| `DECLIVIDADE_MAXIMA` | `xsd:decimal` | true | 0..1 |
| `DECLIVIDADE_MEDIA` | `xsd:decimal` | true | 0..1 |
| `MEDIANA` | `xsd:decimal` | true | 0..1 |
| `DESVIO_PADRAO` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:DENSIDADE_DOMICILIO_POR_BAIRRO_2010`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_POP_DMC` | `xsd:decimal` | false | 1..1 |
| `NUM_BAIRRO` | `xsd:decimal` | true | 0..1 |
| `NOME_BAIRRO` | `xsd:string` | true | 0..1 |
| `POPULACAO` | `xsd:decimal` | true | 0..1 |
| `DOMICILIO` | `xsd:decimal` | true | 0..1 |
| `HAB_DOM` | `xsd:decimal` | true | 0..1 |
| `HAB_KM2` | `xsd:decimal` | true | 0..1 |
| `AREA_KM2` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `QTDE_DOMIC_KM2` | `xsd:decimal` | true | 0..1 |

### `ide_bhgeo:DENSIDADE_DOMICILIO_POR_BAIRRO_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_POP_DOMIC_BAIRRO_2022` | `xsd:decimal` | false | 1..1 |
| `NUM_BAIRRO` | `xsd:decimal` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `AREA_KM` | `xsd:decimal` | true | 0..1 |
| `POPULACAO` | `xsd:decimal` | true | 0..1 |
| `DOMICILIOS` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `DENSIDADE_DEMOGRAFICA` | `xsd:decimal` | true | 0..1 |
| `QTDE_DOMIC_KM2` | `xsd:decimal` | true | 0..1 |

### `ide_bhgeo:DENSIDADE_DOMICILIO_POR_REGONAL_2010`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_REGIONAL` | `xsd:decimal` | false | 1..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |
| `QTDE_POPULACAO` | `xsd:decimal` | true | 0..1 |
| `QTDE_DOMICILIO` | `xsd:decimal` | true | 0..1 |
| `QTDE_HAB_DOM` | `xsd:decimal` | true | 0..1 |
| `QTDE_HAB_KM2` | `xsd:decimal` | true | 0..1 |
| `AREA_KM2` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `QTDE_DOMIC_KM2` | `xsd:decimal` | true | 0..1 |

### `ide_bhgeo:DENSIDADE_DOMICILIO_POR_REGONAL_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_POP_DOMIC_REGIONAL_2022` | `xsd:decimal` | false | 1..1 |
| `COD_REGIONAL` | `xsd:decimal` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `SIGLA` | `xsd:string` | true | 0..1 |
| `AREA_KM` | `xsd:decimal` | true | 0..1 |
| `POPULACAO` | `xsd:decimal` | true | 0..1 |
| `DOMICILIOS` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `DENSIDADE_DEMOGRAFICA` | `xsd:decimal` | true | 0..1 |
| `QTDE_DOMIC_KM2` | `xsd:decimal` | true | 0..1 |

### `ide_bhgeo:DENSIDADE_POPULACIONAL_BAIRRO_2010`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_POP_DMC` | `xsd:decimal` | false | 1..1 |
| `NUM_BAIRRO` | `xsd:decimal` | true | 0..1 |
| `NOME_BAIRRO` | `xsd:string` | true | 0..1 |
| `POPULACAO` | `xsd:decimal` | true | 0..1 |
| `DOMICILIO` | `xsd:decimal` | true | 0..1 |
| `HAB_DOM` | `xsd:decimal` | true | 0..1 |
| `HAB_KM2` | `xsd:decimal` | true | 0..1 |
| `AREA_KM2` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `QTDE_DOMIC_KM2` | `xsd:decimal` | true | 0..1 |

### `ide_bhgeo:DENSIDADE_POPULACIONAL_BAIRRO_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_POP_DOMIC_BAIRRO_2022` | `xsd:decimal` | false | 1..1 |
| `NUM_BAIRRO` | `xsd:decimal` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `AREA_KM` | `xsd:decimal` | true | 0..1 |
| `POPULACAO` | `xsd:decimal` | true | 0..1 |
| `DOMICILIOS` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `DENSIDADE_DEMOGRAFICA` | `xsd:decimal` | true | 0..1 |
| `QTDE_DOMIC_KM2` | `xsd:decimal` | true | 0..1 |

### `ide_bhgeo:DENSIDADE_POPULACIONAL_REGIONAL_2010`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_REGIONAL` | `xsd:decimal` | false | 1..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |
| `QTDE_POPULACAO` | `xsd:decimal` | true | 0..1 |
| `QTDE_DOMICILIO` | `xsd:decimal` | true | 0..1 |
| `QTDE_HAB_DOM` | `xsd:decimal` | true | 0..1 |
| `QTDE_HAB_KM2` | `xsd:decimal` | true | 0..1 |
| `AREA_KM2` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `QTDE_DOMIC_KM2` | `xsd:decimal` | true | 0..1 |

### `ide_bhgeo:DENSIDADE_POPULACIONAL_REGIONAL_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_POP_DOMIC_REGIONAL_2022` | `xsd:decimal` | false | 1..1 |
| `COD_REGIONAL` | `xsd:decimal` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `SIGLA` | `xsd:string` | true | 0..1 |
| `AREA_KM` | `xsd:decimal` | true | 0..1 |
| `POPULACAO` | `xsd:decimal` | true | 0..1 |
| `DOMICILIOS` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `DENSIDADE_DEMOGRAFICA` | `xsd:decimal` | true | 0..1 |
| `QTDE_DOMIC_KM2` | `xsd:decimal` | true | 0..1 |

### `ide_bhgeo:DESLIZAMENTO_TERRA_AREA_PRIORITARIA_SBN`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_AREAS_PRIORITARIAS_SBN_2022` | `xsd:decimal` | false | 1..1 |
| `AREA_M2` | `xsd:double` | true | 0..1 |
| `EXP_ALAG` | `xsd:double` | true | 0..1 |
| `EXP_DESL` | `xsd:double` | true | 0..1 |
| `EXP_INUN` | `xsd:double` | true | 0..1 |
| `EXP_ONDA` | `xsd:double` | true | 0..1 |
| `VUL_ALAG` | `xsd:double` | true | 0..1 |
| `VUL_DESL` | `xsd:double` | true | 0..1 |
| `VUL_INUN` | `xsd:double` | true | 0..1 |
| `VUL_ONDA` | `xsd:double` | true | 0..1 |
| `AC_ALAG` | `xsd:double` | true | 0..1 |
| `AC_DESL` | `xsd:double` | true | 0..1 |
| `AC_INUN` | `xsd:double` | true | 0..1 |
| `AC_ONDA` | `xsd:double` | true | 0..1 |
| `CON_AMB` | `xsd:double` | true | 0..1 |
| `CON_ANT` | `xsd:double` | true | 0..1 |
| `CON_TOT` | `xsd:double` | true | 0..1 |
| `SBN_ALAG` | `xsd:double` | true | 0..1 |
| `SBN_DESL` | `xsd:double` | true | 0..1 |
| `SBN_INUN` | `xsd:double` | true | 0..1 |
| `SBN_ONDA` | `xsd:double` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:DESTAQUE_CIRCULACAO_VIARIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_TCV` | `xsd:decimal` | false | 1..1 |
| `TIPO_TRECHO_CIRCULACAO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `COD_LOGRADOURO` | `xsd:decimal` | true | 0..1 |
| `ID_NO_CIRC_INICIAL` | `xsd:decimal` | true | 0..1 |
| `ID_NO_CIRC_FINAL` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:DIRETRIZ_ALTIMETRIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_DIRETRIZ_PROTECAO` | `xsd:decimal` | false | 1..1 |
| `DESC_TIPO_DIRETRIZ_PROTECAO` | `xsd:string` | true | 0..1 |
| `DESC_DIRETRIZ_PROTECAO` | `xsd:string` | true | 0..1 |
| `VALOR_REFERENCIA` | `xsd:double` | true | 0..1 |
| `NUM_LOTE_CTM` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:DIRETRIZ_PROTECAO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_DIRETRIZ_PROTECAO` | `xsd:decimal` | false | 1..1 |
| `DESC_TIPO_DIRETRIZ_PROTECAO` | `xsd:string` | true | 0..1 |
| `DESC_DIRETRIZ_PROTECAO` | `xsd:string` | true | 0..1 |
| `VALOR_REFERENCIA` | `xsd:double` | true | 0..1 |
| `NUM_LOTE_CTM` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:DISTRITO_MUNICIPAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_DISTRITO_MUNICIPAL` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `LEGISLACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:DISTRITO_SANITARIO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_DISTRITO_SANITARIO` | `xsd:decimal` | false | 1..1 |
| `NOME_DISTRITO_SANITARIO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:DIVISA_FISICA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `TIPO_DIVISA` | `xsd:string` | false | 1..1 |
| `ID_DVF` | `xsd:decimal` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:DOACAO_EQUIPAMENTO_ELETRONICO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_POSTO_DOACAO` | `xsd:decimal` | false | 1..1 |
| `NOME_POSTO_DOACAO` | `xsd:string` | true | 0..1 |
| `DESCRICAO_POSTO_DOACAO` | `xsd:string` | true | 0..1 |
| `TIPO_POSTO_DOACAO` | `xsd:string` | false | 1..1 |
| `TIPO_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `REGIONAL` | `xsd:string` | true | 0..1 |
| `OBSERVACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:EDIFICACAO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EDIF` | `xsd:decimal` | false | 1..1 |
| `AREA` | `xsd:decimal` | false | 1..1 |
| `COTA_MAX_MDE` | `xsd:decimal` | true | 0..1 |
| `COTA_MAX_MDT` | `xsd:decimal` | true | 0..1 |
| `COTA_MIN_MDE` | `xsd:decimal` | true | 0..1 |
| `COTA_MIN_MDT` | `xsd:decimal` | true | 0..1 |
| `DESVIO_PADRAO_MDE` | `xsd:decimal` | true | 0..1 |
| `DESVIO_PADRAO_MDT` | `xsd:decimal` | true | 0..1 |
| `ID_LOTE_CTM` | `xsd:decimal` | true | 0..1 |
| `MEDIA_MDE` | `xsd:decimal` | true | 0..1 |
| `MEDIA_MDT` | `xsd:decimal` | true | 0..1 |
| `MODA_MDE` | `xsd:decimal` | true | 0..1 |
| `MODA_MDT` | `xsd:decimal` | true | 0..1 |
| `ALT_EST_MAXMDE_MINMDT` | `xsd:decimal` | true | 0..1 |
| `ALT_EST_MODAMDE_MINMDT` | `xsd:decimal` | true | 0..1 |
| `OBSERVACAO_MAXMDE_MINMDT` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `OBSERVACAO_MODAMDE_MINMDT` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:EDIFICACAO_DESTAQUE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EDIFICACAO` | `xsd:decimal` | false | 1..1 |
| `GEOMETRIA` | `gml:GeometryPropertyType` | true | 0..1 |

### `ide_bhgeo:EMPREENDIMENTOS_SUDECAP`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_AREA_EMPREENDIMENTO` | `xsd:decimal` | false | 1..1 |
| `NUMERO_PO` | `xsd:decimal` | false | 1..1 |
| `NOME_PO` | `xsd:string` | true | 0..1 |
| `REGIONAL` | `xsd:string` | true | 0..1 |
| `TEMATICA` | `xsd:string` | true | 0..1 |
| `STATUS` | `xsd:string` | true | 0..1 |
| `ORCAMENTO_PARTICIPATIVO` | `xsd:string` | true | 0..1 |
| `EMPRESA_RESPONSAVEL` | `xsd:string` | true | 0..1 |
| `GRUPO` | `xsd:string` | true | 0..1 |
| `PLANEJAMENTO_OBRA` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:EMPRESA_PEQUENO_PORTE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ATIV_ECON_ESTABELECIMENTO` | `xsd:decimal` | false | 1..1 |
| `CNAE_PRINCIPAL` | `xsd:string` | true | 0..1 |
| `DESCRICAO_CNAE_PRINCIPAL` | `xsd:string` | true | 0..1 |
| `CNAE` | `xsd:string` | true | 0..1 |
| `DATA_INICIO_ATIVIDADE` | `xsd:string` | true | 0..1 |
| `NATUREZA_JURIDICA` | `xsd:string` | true | 0..1 |
| `PORTE_EMPRESA` | `xsd:string` | true | 0..1 |
| `AREA_UTILIZADA` | `xsd:string` | true | 0..1 |
| `IND_SIMPLES` | `xsd:string` | true | 0..1 |
| `IND_MEI` | `xsd:string` | true | 0..1 |
| `IND_POSSUI_ALVARA` | `xsd:string` | true | 0..1 |
| `TIPO_UNIDADE` | `xsd:string` | true | 0..1 |
| `FORMA_ATUACAO` | `xsd:string` | true | 0..1 |
| `DESC_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `NOME_FANTASIA` | `xsd:string` | true | 0..1 |
| `CNPJ` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:EMPRESAS_OUTROS_PORTES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ATIV_ECON_ESTABELECIMENTO` | `xsd:decimal` | false | 1..1 |
| `CNAE_PRINCIPAL` | `xsd:string` | true | 0..1 |
| `DESCRICAO_CNAE_PRINCIPAL` | `xsd:string` | true | 0..1 |
| `CNAE` | `xsd:string` | true | 0..1 |
| `DATA_INICIO_ATIVIDADE` | `xsd:string` | true | 0..1 |
| `NATUREZA_JURIDICA` | `xsd:string` | true | 0..1 |
| `PORTE_EMPRESA` | `xsd:string` | true | 0..1 |
| `AREA_UTILIZADA` | `xsd:string` | true | 0..1 |
| `IND_SIMPLES` | `xsd:string` | true | 0..1 |
| `IND_MEI` | `xsd:string` | true | 0..1 |
| `IND_POSSUI_ALVARA` | `xsd:string` | true | 0..1 |
| `TIPO_UNIDADE` | `xsd:string` | true | 0..1 |
| `FORMA_ATUACAO` | `xsd:string` | true | 0..1 |
| `DESC_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `NOME_FANTASIA` | `xsd:string` | true | 0..1 |
| `CNPJ` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:ENDERECO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `IDEND` | `xsd:string` | true | 0..1 |
| `ID_EDC` | `xsd:decimal` | false | 1..1 |
| `ID_LOGRADOURO` | `xsd:decimal` | false | 1..1 |
| `SIGLA_TIPO_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `DESC_TIPO_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `NOME_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | false | 1..1 |
| `LETRA_IMOVEL` | `xsd:string` | true | 0..1 |
| `ID_BAIRRO_POPULAR` | `xsd:decimal` | true | 0..1 |
| `NUM_BAIRRO_POPULAR` | `xsd:decimal` | false | 1..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | false | 1..1 |
| `ID_BAIRRO_OFICIAL` | `xsd:decimal` | true | 0..1 |
| `NUM_BAIRRO_OFICIAL` | `xsd:decimal` | false | 1..1 |
| `TIPO_BAIRRO_OFICIAL` | `xsd:string` | false | 1..1 |
| `NOME_BAIRRO_OFICIAL` | `xsd:string` | false | 1..1 |
| `ID_REGIONAL` | `xsd:decimal` | true | 0..1 |
| `NOME_REGIONAL` | `xsd:string` | false | 1..1 |
| `CEP` | `xsd:decimal` | true | 0..1 |
| `EXISTENCIA_NUM_LOCAL` | `xsd:string` | true | 0..1 |
| `SITUACAO_PBH` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:ENSINO_SUPERIOR`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ATIV_ECON_ESTABELECIMENTO` | `xsd:decimal` | false | 1..1 |
| `CNAE_PRINCIPAL` | `xsd:string` | true | 0..1 |
| `DESCRICAO_CNAE_PRINCIPAL` | `xsd:string` | true | 0..1 |
| `CNAE` | `xsd:string` | true | 0..1 |
| `DATA_INICIO_ATIVIDADE` | `xsd:string` | true | 0..1 |
| `NATUREZA_JURIDICA` | `xsd:string` | true | 0..1 |
| `PORTE_EMPRESA` | `xsd:string` | true | 0..1 |
| `AREA_UTILIZADA` | `xsd:string` | true | 0..1 |
| `IND_SIMPLES` | `xsd:string` | true | 0..1 |
| `IND_MEI` | `xsd:string` | true | 0..1 |
| `IND_POSSUI_ALVARA` | `xsd:string` | true | 0..1 |
| `TIPO_UNIDADE` | `xsd:string` | true | 0..1 |
| `FORMA_ATUACAO` | `xsd:string` | true | 0..1 |
| `DESC_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `NOME_FANTASIA` | `xsd:string` | true | 0..1 |
| `CNPJ` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:EQUIP_CEVAE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIP_SEG_ALIM_NUTRI` | `xsd:decimal` | false | 1..1 |
| `NOME_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `REFERENCIA` | `xsd:string` | true | 0..1 |
| `DIA_HORARIO` | `xsd:string` | true | 0..1 |
| `CONTATO` | `xsd:string` | true | 0..1 |
| `INFORMACOES_ADICIONAIS` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `NUMERO_BARRACAS` | `xsd:decimal` | true | 0..1 |
| `PRODUTOS_COMERCIALIZADOS` | `xsd:string` | true | 0..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:EQUIP_EDUCACAO_AMBIENTAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIP_EDUCACAO_AMBIENTAL` | `xsd:decimal` | false | 1..1 |
| `TIPO_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `NOME_EQUIPAMENTO` | `xsd:string` | false | 1..1 |
| `LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |
| `IND_ATIVO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | false | 1..1 |

### `ide_bhgeo:EQUIP_ESPORTIVO_ESPECIALIZADO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQ_ESP` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `NOME_POPULAR` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `REF_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `GESTOR_EQUIP_ESPORT` | `xsd:string` | true | 0..1 |
| `STATUS` | `xsd:string` | true | 0..1 |
| `CODIGO` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:EQUIP_HAB_CREAR`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQ_CREAR` | `xsd:decimal` | false | 1..1 |
| `CATEGORIA` | `xsd:string` | false | 1..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:string` | false | 1..1 |
| `LETRA_IMOVEL` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | false | 1..1 |
| `COMPL_ENDERECO` | `xsd:string` | true | 0..1 |
| `ORGAO_RESPONSAVEL` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | false | 1..1 |

### `ide_bhgeo:EQUIP_PUBLICO_WIFI`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIP_HOTSPOT` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `CODIGO_PROJETO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:EQUIPAMENTO_CIDADANIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIPAMENTO_CIDADANIA` | `xsd:decimal` | false | 1..1 |
| `NOME_EQUIPAMENTO_CIDADANIA` | `xsd:string` | false | 1..1 |
| `DESC_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `LETRA_IMOVEL` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `DESCRICAO_CATEGORIA` | `xsd:string` | true | 0..1 |
| `DIAS_FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `HORARIO_FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:EQUIPAMENTO_CRAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_REDE_SOCIOASSISTENCIAL` | `xsd:decimal` | false | 1..1 |
| `ID_ENTIDADE` | `xsd:decimal` | false | 1..1 |
| `NOME_ENTIDADE` | `xsd:string` | true | 0..1 |
| `DESC_CATEGORIA` | `xsd:string` | true | 0..1 |
| `SIGLA_CATEGORIA` | `xsd:string` | true | 0..1 |
| `TIPO_EXECUCAO` | `xsd:string` | true | 0..1 |
| `NOME_SERVICO` | `xsd:string` | true | 0..1 |
| `NIVEL_PROTECAO` | `xsd:string` | true | 0..1 |
| `SIGLA_PROTECAO` | `xsd:string` | true | 0..1 |
| `PUBLICO_USUARIO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:EQUIPAMENTO_CREAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_REDE_SOCIOASSISTENCIAL` | `xsd:decimal` | false | 1..1 |
| `ID_ENTIDADE` | `xsd:decimal` | false | 1..1 |
| `NOME_ENTIDADE` | `xsd:string` | true | 0..1 |
| `DESC_CATEGORIA` | `xsd:string` | true | 0..1 |
| `SIGLA_CATEGORIA` | `xsd:string` | true | 0..1 |
| `TIPO_EXECUCAO` | `xsd:string` | true | 0..1 |
| `NOME_SERVICO` | `xsd:string` | true | 0..1 |
| `NIVEL_PROTECAO` | `xsd:string` | true | 0..1 |
| `SIGLA_PROTECAO` | `xsd:string` | true | 0..1 |
| `PUBLICO_USUARIO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:EQUIPAMENTOS_CULTURAIS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQ_CT` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | false | 1..1 |
| `TIPO` | `xsd:string` | false | 1..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `HORARIO_FUNCIONAMENTO` | `xsd:string` | false | 1..1 |
| `REDE_SOCIAL` | `xsd:string` | true | 0..1 |
| `LINK_PORTAL_PBH` | `xsd:string` | true | 0..1 |
| `LINK_BH_FAZ_CULTURA` | `xsd:string` | true | 0..1 |
| `EMAIL` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:ESCOLAS_ESTADUAIS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIP_EDUCACAO` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `DEPENDENCIA_ADM` | `xsd:string` | true | 0..1 |
| `CODIGO_INEP` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `REGIONAL` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:ESCOLAS_FEDERAIS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIP_EDUCACAO` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `DEPENDENCIA_ADM` | `xsd:string` | true | 0..1 |
| `CODIGO_INEP` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `REGIONAL` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:ESCOLAS_MUNICIPAIS_EDUCACAO_INFANTIL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIP_EDUCACAO` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `DEPENDENCIA_ADM` | `xsd:string` | true | 0..1 |
| `CODIGO_INEP` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `REGIONAL` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:ESCOLAS_MUNICIPAIS_ENSINO_FUNDAMENTAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIP_EDUCACAO` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `DEPENDENCIA_ADM` | `xsd:string` | true | 0..1 |
| `CODIGO_INEP` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `REGIONAL` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:ESCOLAS_PARTICULARES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIP_EDUCACAO` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `DEPENDENCIA_ADM` | `xsd:string` | true | 0..1 |
| `CODIGO_INEP` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `REGIONAL` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:ESPACO_OPERACIONAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ESPACO_OPERACIONAL` | `xsd:decimal` | false | 1..1 |
| `NUMERO_PROTOCOLO` | `xsd:string` | false | 1..1 |
| `DATA_EMISSAO_AUTORIZACAO` | `xsd:date` | true | 0..1 |
| `NUMERO_AUTORIZACAO` | `xsd:string` | true | 0..1 |
| `SITUACAO_AUTORIZACAO` | `xsd:string` | true | 0..1 |
| `LINK_AUTORIZACAO` | `xsd:string` | true | 0..1 |
| `INIC_FUNC_DIA_UTIL` | `xsd:string` | true | 0..1 |
| `FIM_FUNC_DIA_UTIL` | `xsd:string` | true | 0..1 |
| `INIC_FUNC_FIM_SEMAN_FERIADO` | `xsd:string` | true | 0..1 |
| `FIM_FUNC_FIM_SEMAN_FERIADO` | `xsd:string` | true | 0..1 |
| `QTD_MESA_APROVADA` | `xsd:decimal` | true | 0..1 |
| `QTD_CADEIRA_APROVADA` | `xsd:decimal` | true | 0..1 |
| `REFERENCIA_LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `OBSERVACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:ESTACAO_HIDROMETEOROLOGICA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ESTACAO_HIDROMETEOROLOGICA` | `xsd:decimal` | false | 1..1 |
| `CODIGO` | `xsd:string` | true | 0..1 |
| `NOME_BACIA_HIDROGRAFICA` | `xsd:string` | true | 0..1 |
| `ALTITUDE` | `xsd:decimal` | true | 0..1 |
| `TIPO_ESTACAO` | `xsd:string` | true | 0..1 |
| `REFERENCIA_LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:ESTACAO_METRO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ESTMT` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `QTDE_VIAGEM_DIA_UTIL` | `xsd:decimal` | true | 0..1 |
| `LINHA_METRO_ESTACAO` | `xsd:string` | true | 0..1 |
| `CODIGO` | `xsd:string` | true | 0..1 |
| `SITUACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:ESTACAO_ONIBUS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ESTPB` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `CORREDOR_MOVE` | `xsd:string` | true | 0..1 |
| `EIXO_MOVE` | `xsd:string` | true | 0..1 |
| `SISTEMA_TRONCAL` | `xsd:string` | true | 0..1 |
| `INTEGRACAO_FISICA_METRO` | `xsd:string` | true | 0..1 |
| `SITUACAO` | `xsd:string` | true | 0..1 |
| `GESTOR` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:ESTACAO_TRANSPORTE_PUBLICO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_REFERENCIA_LOCALIZACAO` | `xsd:decimal` | false | 1..1 |
| `NOME_REFERENCIA_LOCALIZACAO` | `xsd:string` | false | 1..1 |
| `ID_CATEGORIA_REFERENCIA_LOC` | `xsd:decimal` | false | 1..1 |
| `TIPO_REFERENCIA_LOCALIZACAO` | `xsd:string` | false | 1..1 |
| `ID_ENDERECO_PBH` | `xsd:decimal` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `CONTATO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:ESTACIONAMENTO_IDOSO_PERMANENCIA_LIVRE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EDESP` | `xsd:decimal` | false | 1..1 |
| `TIPO_ESTACIONAMENTO` | `xsd:string` | true | 0..1 |
| `DESTINACAO_ESPECIFICA` | `xsd:string` | true | 0..1 |
| `DIA_REGRA_OPERACAO` | `xsd:string` | true | 0..1 |
| `PERIODO_VALIDO_REGRA_OPERACAO` | `xsd:string` | true | 0..1 |
| `NUMERO_VAGAS_FISICAS` | `xsd:decimal` | true | 0..1 |
| `NUMERO_VAGAS_ROTATIVAS` | `xsd:decimal` | true | 0..1 |
| `TEMPO_PERMANENCIA` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `REFERENCIA_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:ESTACIONAMENTO_ROTATIVO_IDOSO_PARQUE_MANGABEIRAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EDESP` | `xsd:decimal` | false | 1..1 |
| `TIPO_ESTACIONAMENTO` | `xsd:string` | true | 0..1 |
| `DESTINACAO_ESPECIFICA` | `xsd:string` | true | 0..1 |
| `DIA_REGRA_OPERACAO` | `xsd:string` | true | 0..1 |
| `PERIODO_VALIDO_REGRA_OPERACAO` | `xsd:string` | true | 0..1 |
| `NUMERO_VAGAS_FISICAS` | `xsd:decimal` | true | 0..1 |
| `NUMERO_VAGAS_ROTATIVAS` | `xsd:decimal` | true | 0..1 |
| `TEMPO_PERMANENCIA` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `REFERENCIA_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:ESTACIONAMENTO_ROTATIVO_IDOSO_SABADO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EDESP` | `xsd:decimal` | false | 1..1 |
| `TIPO_ESTACIONAMENTO` | `xsd:string` | true | 0..1 |
| `DESTINACAO_ESPECIFICA` | `xsd:string` | true | 0..1 |
| `DIA_REGRA_OPERACAO` | `xsd:string` | true | 0..1 |
| `PERIODO_VALIDO_REGRA_OPERACAO` | `xsd:string` | true | 0..1 |
| `NUMERO_VAGAS_FISICAS` | `xsd:decimal` | true | 0..1 |
| `NUMERO_VAGAS_ROTATIVAS` | `xsd:decimal` | true | 0..1 |
| `TEMPO_PERMANENCIA` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `REFERENCIA_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:ESTACIONAMENTO_ROTATIVO_IDOSO_SEGUNDA_SEXTA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EDESP` | `xsd:decimal` | false | 1..1 |
| `TIPO_ESTACIONAMENTO` | `xsd:string` | true | 0..1 |
| `DESTINACAO_ESPECIFICA` | `xsd:string` | true | 0..1 |
| `DIA_REGRA_OPERACAO` | `xsd:string` | true | 0..1 |
| `PERIODO_VALIDO_REGRA_OPERACAO` | `xsd:string` | true | 0..1 |
| `NUMERO_VAGAS_FISICAS` | `xsd:decimal` | true | 0..1 |
| `NUMERO_VAGAS_ROTATIVAS` | `xsd:decimal` | true | 0..1 |
| `TEMPO_PERMANENCIA` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `REFERENCIA_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:ESTACIONAMENTO_ROTATIVO_MOTOFRETE_SABADO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EDESP` | `xsd:decimal` | false | 1..1 |
| `TIPO_ESTACIONAMENTO` | `xsd:string` | true | 0..1 |
| `DESTINACAO_ESPECIFICA` | `xsd:string` | true | 0..1 |
| `DIA_REGRA_OPERACAO` | `xsd:string` | true | 0..1 |
| `PERIODO_VALIDO_REGRA_OPERACAO` | `xsd:string` | true | 0..1 |
| `NUMERO_VAGAS_FISICAS` | `xsd:decimal` | true | 0..1 |
| `NUMERO_VAGAS_ROTATIVAS` | `xsd:decimal` | true | 0..1 |
| `TEMPO_PERMANENCIA` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `REFERENCIA_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:ESTACIONAMENTO_ROTATIVO_MOTOFRETE_SEGUNDA_SEXTA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EDESP` | `xsd:decimal` | false | 1..1 |
| `TIPO_ESTACIONAMENTO` | `xsd:string` | true | 0..1 |
| `DESTINACAO_ESPECIFICA` | `xsd:string` | true | 0..1 |
| `DIA_REGRA_OPERACAO` | `xsd:string` | true | 0..1 |
| `PERIODO_VALIDO_REGRA_OPERACAO` | `xsd:string` | true | 0..1 |
| `NUMERO_VAGAS_FISICAS` | `xsd:decimal` | true | 0..1 |
| `NUMERO_VAGAS_ROTATIVAS` | `xsd:decimal` | true | 0..1 |
| `TEMPO_PERMANENCIA` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `REFERENCIA_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:ESTACIONAMENTO_ROTATIVO_PARQUE_MANGABEIRAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ESTACIONAMENTO` | `xsd:decimal` | false | 1..1 |
| `NUMERO_VAGAS_FISICAS` | `xsd:decimal` | true | 0..1 |
| `NUMERO_VAGAS_ROTATIVAS` | `xsd:decimal` | true | 0..1 |
| `TEMPO_PERMANENCIA` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `REFERENCIA_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `PERIODO_VALIDO_REGRA_OPERACAO` | `xsd:string` | true | 0..1 |
| `DIA_REGRA_OPERACAO` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:ESTACIONAMENTO_ROTATIVO_SABADO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ESTACIONAMENTO` | `xsd:decimal` | false | 1..1 |
| `NUMERO_VAGAS_FISICAS` | `xsd:decimal` | true | 0..1 |
| `NUMERO_VAGAS_ROTATIVAS` | `xsd:decimal` | true | 0..1 |
| `TEMPO_PERMANENCIA` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `REFERENCIA_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `PERIODO_VALIDO_REGRA_OPERACAO` | `xsd:string` | true | 0..1 |
| `DIA_REGRA_OPERACAO` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:ESTACIONAMENTO_ROTATIVO_SEGUNDA_SEXTA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ESTACIONAMENTO` | `xsd:decimal` | false | 1..1 |
| `NUMERO_VAGAS_FISICAS` | `xsd:decimal` | true | 0..1 |
| `NUMERO_VAGAS_ROTATIVAS` | `xsd:decimal` | true | 0..1 |
| `TEMPO_PERMANENCIA` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `REFERENCIA_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `PERIODO_VALIDO_REGRA_OPERACAO` | `xsd:string` | true | 0..1 |
| `DIA_REGRA_OPERACAO` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:FABRICACAO_EQUIPAMENTO_INFORMATICA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ATVECON` | `xsd:decimal` | false | 1..1 |
| `CNAE_PRINCIPAL` | `xsd:string` | true | 0..1 |
| `DESCRICAO_CNAE` | `xsd:string` | true | 0..1 |
| `CNAE` | `xsd:string` | true | 0..1 |
| `NATUREZA_JURIDICA` | `xsd:string` | true | 0..1 |
| `PORTE_EMPRESA` | `xsd:string` | true | 0..1 |
| `AREA_UTILIZADA` | `xsd:string` | true | 0..1 |
| `IND_SIMPLES` | `xsd:string` | true | 0..1 |
| `IND_MEI` | `xsd:string` | true | 0..1 |
| `TIPO_UNIDADE` | `xsd:string` | true | 0..1 |
| `FORMA_ATUACAO` | `xsd:string` | true | 0..1 |
| `DESC_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `NOME_FANTASIA` | `xsd:string` | true | 0..1 |
| `CNPJ` | `xsd:string` | true | 0..1 |
| `DATA_INICIO_ATIVIDADE` | `xsd:string` | true | 0..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |
| `INSCRICAO_MUNICIPAL` | `xsd:string` | true | 0..1 |
| `IND_POSSUI_ALVARA` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:FAIXA_RODAGEM_RODOVIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_FX_ROD` | `xsd:decimal` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:FEIRA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIP_SEG_ALIM_NUTRI` | `xsd:decimal` | false | 1..1 |
| `NOME_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `REFERENCIA` | `xsd:string` | true | 0..1 |
| `DIA_HORARIO` | `xsd:string` | true | 0..1 |
| `CONTATO` | `xsd:string` | true | 0..1 |
| `INFORMACOES_ADICIONAIS` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `NUMERO_BARRACAS` | `xsd:decimal` | true | 0..1 |
| `PRODUTOS_COMERCIALIZADOS` | `xsd:string` | true | 0..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:FEIRA_AFONSO_PENA_BARRACA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_FEIRA_AFONSO_PENA_BARRACA` | `xsd:decimal` | false | 1..1 |
| `CODIGO_VAGA` | `xsd:string` | false | 1..1 |
| `NOME_FANTASIA` | `xsd:string` | false | 1..1 |
| `NOME_FEIRANTE` | `xsd:string` | false | 1..1 |
| `NOME_PREPOSTO` | `xsd:string` | true | 0..1 |
| `NOME_SETOR` | `xsd:string` | false | 1..1 |
| `PRODUTOS` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:FEIRA_AFONSO_PENA_SETOR`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_FEIRA_AFONSO_PENA_SETOR` | `xsd:decimal` | false | 1..1 |
| `DESCRICAO_CATEGORIA_SETOR` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:FERROVIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_FRV` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `DESTINACAO` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | false | 1..1 |

### `ide_bhgeo:FISCALIZACAO_ELETRONICA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_FISCALIZACAO_ELETRONICA` | `xsd:decimal` | false | 1..1 |
| `DESC_LOC_CONTROLADOR_TRANSITO` | `xsd:string` | true | 0..1 |
| `DESC_TIPO_CONTROLADOR_TRANSITO` | `xsd:string` | false | 1..1 |
| `VELOCIDADE_REGULAMENTAR` | `xsd:decimal` | false | 1..1 |
| `SENTIDO` | `xsd:string` | false | 1..1 |
| `SENTIDO_FISCALIZADO` | `xsd:string` | true | 0..1 |
| `NUM_SERIE_ATUAL` | `xsd:decimal` | true | 0..1 |
| `COD_SECUNDARIA` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:GALPAO_RECICLAGEM`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_GALPAO_RECICLAGEM` | `xsd:decimal` | false | 1..1 |
| `NOME_GALPAO_RECICLAGEM` | `xsd:string` | false | 1..1 |
| `NOME_ASSOCIACAO_COOPERATIVA` | `xsd:string` | false | 1..1 |
| `TIPO_RESIDUOS` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUM_IMOVEL` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `HORARIO_FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `ENDERECO_ELETRONICO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | false | 1..1 |

### `ide_bhgeo:GEOLOGIA_BASICA_ATIVIDADE_MINERARIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_GEOLOGIA_BASICA_1995_PT` | `xsd:decimal` | false | 1..1 |
| `TEMA` | `xsd:string` | true | 0..1 |
| `DESC_ITEM` | `xsd:string` | true | 0..1 |
| `AZIMUTE_DIRECAO` | `xsd:decimal` | true | 0..1 |
| `AZIMUTE_MERGULHO` | `xsd:decimal` | true | 0..1 |
| `ANGULO_MERGULHO` | `xsd:decimal` | true | 0..1 |
| `MATERIAL_EXTRAIDO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiPointPropertyType` | true | 0..1 |

### `ide_bhgeo:GEOLOGIA_BASICA_CONTATO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_GEOLOGIA_BASICA_1995_LN` | `xsd:decimal` | false | 1..1 |
| `TEMA` | `xsd:string` | true | 0..1 |
| `DESC_ITEM` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:GEOLOGIA_BASICA_DIQUE_CLASTICO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_GEOLOGIA_BASICA_1995_LN` | `xsd:decimal` | false | 1..1 |
| `TEMA` | `xsd:string` | true | 0..1 |
| `DESC_ITEM` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:GEOLOGIA_BASICA_FALHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_GEOLOGIA_BASICA_1995_LN` | `xsd:decimal` | false | 1..1 |
| `TEMA` | `xsd:string` | true | 0..1 |
| `DESC_ITEM` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:GEOLOGIA_BASICA_FOTOLINEAMENTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_GEOLOGIA_BASICA_1995_LN` | `xsd:decimal` | false | 1..1 |
| `TEMA` | `xsd:string` | true | 0..1 |
| `DESC_ITEM` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:GEOLOGIA_BASICA_LIMITE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_GEOLOGIA_BASICA_1995_PL` | `xsd:decimal` | false | 1..1 |
| `TEMA` | `xsd:string` | true | 0..1 |
| `DESC_ITEM` | `xsd:string` | true | 0..1 |
| `SIGLA_UNIDADE` | `xsd:string` | true | 0..1 |
| `DESC_SIGLA_UNIDADE` | `xsd:string` | true | 0..1 |
| `HIERARQUIA` | `xsd:string` | true | 0..1 |
| `CLASSIF_UNIDADE` | `xsd:string` | true | 0..1 |
| `EON_IDADE_MAXIMA` | `xsd:string` | true | 0..1 |
| `ERA_IDADE_MAXIMA` | `xsd:string` | true | 0..1 |
| `DESC_UNIDADE` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:GEOLOGIA_BASICA_LITOTIPO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_GEOLOGIA_BASICA_1995_PL` | `xsd:decimal` | false | 1..1 |
| `TEMA` | `xsd:string` | true | 0..1 |
| `DESC_ITEM` | `xsd:string` | true | 0..1 |
| `SIGLA_UNIDADE` | `xsd:string` | true | 0..1 |
| `DESC_SIGLA_UNIDADE` | `xsd:string` | true | 0..1 |
| `HIERARQUIA` | `xsd:string` | true | 0..1 |
| `CLASSIF_UNIDADE` | `xsd:string` | true | 0..1 |
| `EON_IDADE_MAXIMA` | `xsd:string` | true | 0..1 |
| `ERA_IDADE_MAXIMA` | `xsd:string` | true | 0..1 |
| `DESC_UNIDADE` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:GEOLOGIA_BASICA_LITOTIPO_OCORRENCIA_PONTUAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_GEOLOGIA_BASICA_1995_PT` | `xsd:decimal` | false | 1..1 |
| `TEMA` | `xsd:string` | true | 0..1 |
| `DESC_ITEM` | `xsd:string` | true | 0..1 |
| `AZIMUTE_DIRECAO` | `xsd:decimal` | true | 0..1 |
| `AZIMUTE_MERGULHO` | `xsd:decimal` | true | 0..1 |
| `ANGULO_MERGULHO` | `xsd:decimal` | true | 0..1 |
| `MATERIAL_EXTRAIDO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiPointPropertyType` | true | 0..1 |

### `ide_bhgeo:GEOLOGIA_BASICA_MEDIDA_ESTRUTURAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_GEOLOGIA_BASICA_1995_PT` | `xsd:decimal` | false | 1..1 |
| `TEMA` | `xsd:string` | true | 0..1 |
| `DESC_ITEM` | `xsd:string` | true | 0..1 |
| `AZIMUTE_DIRECAO` | `xsd:decimal` | true | 0..1 |
| `AZIMUTE_MERGULHO` | `xsd:decimal` | true | 0..1 |
| `ANGULO_MERGULHO` | `xsd:decimal` | true | 0..1 |
| `MATERIAL_EXTRAIDO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiPointPropertyType` | true | 0..1 |

### `ide_bhgeo:GEOLOGIA_BASICA_TRACADO_PERFIL_GEOLOGICO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_GEOLOGIA_BASICA_1995_LN` | `xsd:decimal` | false | 1..1 |
| `TEMA` | `xsd:string` | true | 0..1 |
| `DESC_ITEM` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:GEOLOGIA_BASICA_ZONA_CISALHAMENTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_GEOLOGIA_BASICA_1995_PT` | `xsd:decimal` | false | 1..1 |
| `TEMA` | `xsd:string` | true | 0..1 |
| `DESC_ITEM` | `xsd:string` | true | 0..1 |
| `AZIMUTE_DIRECAO` | `xsd:decimal` | true | 0..1 |
| `AZIMUTE_MERGULHO` | `xsd:decimal` | true | 0..1 |
| `ANGULO_MERGULHO` | `xsd:decimal` | true | 0..1 |
| `MATERIAL_EXTRAIDO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiPointPropertyType` | true | 0..1 |

### `ide_bhgeo:GINASIO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQ_ESP` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `NOME_POPULAR` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `REF_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `GESTOR_EQUIP_ESPORT` | `xsd:string` | true | 0..1 |
| `STATUS` | `xsd:string` | true | 0..1 |
| `CODIGO` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:HELIPONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_HLPT` | `xsd:decimal` | false | 1..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:HOSPITAIS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQ_SAUDE` | `xsd:decimal` | false | 1..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `SIGLA_CATEGORIA` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `LOGRADOURO` | `xsd:string` | false | 1..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | false | 1..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:ILUM_PUBLICA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_BASE_TRECHO` | `xsd:decimal` | true | 0..1 |
| `ID_BASE_IP` | `xsd:decimal` | false | 1..1 |
| `IND_IP` | `xsd:string` | true | 0..1 |
| `LARG_INICIO` | `xsd:double` | true | 0..1 |
| `LARG_FINAL` | `xsd:double` | true | 0..1 |
| `LADO_IP` | `xsd:string` | true | 0..1 |
| `DATA` | `xsd:date` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:INDICE_QUALIDADE_NASCENTES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_INDICE_QUALIDADE_NASCENTES` | `xsd:decimal` | false | 1..1 |
| `ID_NASC` | `xsd:decimal` | false | 1..1 |
| `LOCAL_REFERENCIA` | `xsd:string` | true | 0..1 |
| `QUALIDADE_CODIGO_FLORESTAL` | `xsd:decimal` | true | 0..1 |
| `PESO_CODIGO_FLORESTAL` | `xsd:decimal` | true | 0..1 |
| `QUALIDADE_ASPECTO` | `xsd:decimal` | true | 0..1 |
| `PESO_ASPECTO` | `xsd:decimal` | true | 0..1 |
| `QUALIDADE_LOCAL` | `xsd:decimal` | true | 0..1 |
| `PESO_LOCAL` | `xsd:decimal` | true | 0..1 |
| `QUALIDADE_CONDICAO` | `xsd:decimal` | true | 0..1 |
| `PESO_CONDICAO` | `xsd:decimal` | true | 0..1 |
| `IQ_NASC` | `xsd:decimal` | false | 1..1 |
| `AVALIACAO_QUALIDADE` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:INUNDACAO_AREA_PRIORITARIA_SBN`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_AREAS_PRIORITARIAS_SBN_2022` | `xsd:decimal` | false | 1..1 |
| `AREA_M2` | `xsd:double` | true | 0..1 |
| `EXP_ALAG` | `xsd:double` | true | 0..1 |
| `EXP_DESL` | `xsd:double` | true | 0..1 |
| `EXP_INUN` | `xsd:double` | true | 0..1 |
| `EXP_ONDA` | `xsd:double` | true | 0..1 |
| `VUL_ALAG` | `xsd:double` | true | 0..1 |
| `VUL_DESL` | `xsd:double` | true | 0..1 |
| `VUL_INUN` | `xsd:double` | true | 0..1 |
| `VUL_ONDA` | `xsd:double` | true | 0..1 |
| `AC_ALAG` | `xsd:double` | true | 0..1 |
| `AC_DESL` | `xsd:double` | true | 0..1 |
| `AC_INUN` | `xsd:double` | true | 0..1 |
| `AC_ONDA` | `xsd:double` | true | 0..1 |
| `CON_AMB` | `xsd:double` | true | 0..1 |
| `CON_ANT` | `xsd:double` | true | 0..1 |
| `CON_TOT` | `xsd:double` | true | 0..1 |
| `SBN_ALAG` | `xsd:double` | true | 0..1 |
| `SBN_DESL` | `xsd:double` | true | 0..1 |
| `SBN_INUN` | `xsd:double` | true | 0..1 |
| `SBN_ONDA` | `xsd:double` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:ISA_BACIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ISA_BACIA` | `xsd:decimal` | false | 1..1 |
| `COD_BACIA` | `xsd:decimal` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `AREA_BACIA` | `xsd:decimal` | true | 0..1 |
| `POPULACAO_BACIA` | `xsd:decimal` | true | 0..1 |
| `DENSIDADE_BACIA` | `xsd:decimal` | true | 0..1 |
| `IAB` | `xsd:decimal` | true | 0..1 |
| `POPULACAO_SEM_REDE_COLETORA` | `xsd:decimal` | true | 0..1 |
| `POPULACAO_COM_REDE_COLETORA` | `xsd:decimal` | true | 0..1 |
| `ICE` | `xsd:decimal` | true | 0..1 |
| `POPULACAO_SEM_INTERCEPTACAO` | `xsd:decimal` | true | 0..1 |
| `POPULACAO_COM_INTERCEPTACAO` | `xsd:decimal` | true | 0..1 |
| `IIE` | `xsd:decimal` | true | 0..1 |
| `IES` | `xsd:decimal` | true | 0..1 |
| `POPULACAO_CF` | `xsd:decimal` | true | 0..1 |
| `POPULACAO_SEM_COLETA_LIXO_CF` | `xsd:decimal` | true | 0..1 |
| `POPULACAO_COM_COLETA_LIXO_CF` | `xsd:decimal` | true | 0..1 |
| `ICL_CF` | `xsd:decimal` | true | 0..1 |
| `POPULACAO_SEM_COLETA_LIXO_VF` | `xsd:decimal` | true | 0..1 |
| `POPULACAO_COM_COLETA_LIXO_VF` | `xsd:decimal` | true | 0..1 |
| `ICL_VF` | `xsd:decimal` | true | 0..1 |
| `POPULACAO_SEM_COLETA_LIXO_CFVF` | `xsd:decimal` | true | 0..1 |
| `POPULACAO_COM_COLETA_LIXO_CFVF` | `xsd:decimal` | true | 0..1 |
| `ICL` | `xsd:decimal` | true | 0..1 |
| `POPULACAO_MANCHA_INUNDACAO` | `xsd:decimal` | true | 0..1 |
| `IDR` | `xsd:decimal` | true | 0..1 |
| `ISA` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:ISA_SUB_BACIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ISA_SUB_BACIA` | `xsd:decimal` | false | 1..1 |
| `COD_SUB_BACIA` | `xsd:string` | true | 0..1 |
| `NOME_SUB_BACIA` | `xsd:string` | true | 0..1 |
| `AREA_SUB_BACIA` | `xsd:decimal` | true | 0..1 |
| `POPULACAO_SUB_BACIA` | `xsd:decimal` | true | 0..1 |
| `DENSIDADE_SUB_BACIA` | `xsd:decimal` | true | 0..1 |
| `IAB_SUB_BACIA` | `xsd:decimal` | true | 0..1 |
| `POPULACAO_SEM_REDE_COLETORA` | `xsd:decimal` | true | 0..1 |
| `POPULACAO_COM_REDE_COLETORA` | `xsd:decimal` | true | 0..1 |
| `ICE_SUB_BACIA` | `xsd:decimal` | true | 0..1 |
| `POPULACAO_SEM_INTERCEPTACAO` | `xsd:decimal` | true | 0..1 |
| `POPULACAO_COM_INTERCEPTACAO` | `xsd:decimal` | true | 0..1 |
| `IIE_SUB_BACIA` | `xsd:decimal` | true | 0..1 |
| `IES_SUB_BACIA` | `xsd:decimal` | true | 0..1 |
| `POPULACAO_CF` | `xsd:decimal` | true | 0..1 |
| `POPULACAO_SEM_COLETA_LIXO_CF` | `xsd:decimal` | true | 0..1 |
| `POPULACAO_COM_COLETA_LIXO_CF` | `xsd:decimal` | true | 0..1 |
| `ICL_CF_SUB_BACIA` | `xsd:decimal` | true | 0..1 |
| `POPULACAO_SEM_COLETA_LIXO_VF` | `xsd:decimal` | true | 0..1 |
| `POPULACAO_COM_COLETA_LIXO_VF` | `xsd:decimal` | true | 0..1 |
| `ICL_VF_SUB_BACIA` | `xsd:decimal` | true | 0..1 |
| `POPULACAO_SEM_COLETA_LIXO_CFVF` | `xsd:decimal` | true | 0..1 |
| `POPULACAO_COM_COLETA_LIXO_CFVF` | `xsd:decimal` | true | 0..1 |
| `ICL_SUB_BACIA` | `xsd:decimal` | true | 0..1 |
| `POPULACAO_MANCHA_INUNDACAO` | `xsd:decimal` | true | 0..1 |
| `IDR_SUB_BACIA` | `xsd:decimal` | true | 0..1 |
| `ISA_SUB_BACIA` | `xsd:decimal` | true | 0..1 |
| `ID_ISA_BACIA` | `xsd:decimal` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:ITINERARIO_TRANSPORTE_COLETIVO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ITINERARIO_TRANSP_COLETIVO` | `xsd:decimal` | false | 1..1 |
| `CODIGO_LINHA` | `xsd:string` | true | 0..1 |
| `NUMERO_SUBLINHA` | `xsd:decimal` | true | 0..1 |
| `NUMERO_PC` | `xsd:decimal` | true | 0..1 |
| `TIPO_TRANSPORTE` | `xsd:string` | true | 0..1 |
| `EXTENSAO_TOTAL_ITINERARIO` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:CurvePropertyType` | true | 0..1 |

### `ide_bhgeo:IVS_INDICE_VULNERAB_SAUDE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_IVS` | `xsd:decimal` | false | 1..1 |
| `POPULACAO_TOTAL` | `xsd:decimal` | true | 0..1 |
| `POPFEM` | `xsd:decimal` | false | 1..1 |
| `POPMASC` | `xsd:decimal` | false | 1..1 |
| `IVS_2012` | `xsd:string` | false | 1..1 |
| `COD_SETOR_CENSITARIO_SAUDE` | `xsd:string` | true | 0..1 |
| `ID_SETOR_CENSITARIO_2010` | `xsd:decimal` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:JARDIM_CHUVA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_JARDIM_CHUVA` | `xsd:decimal` | false | 1..1 |
| `AREA_INTERNA` | `xsd:double` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `NOME_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `NUMERO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `REGIONAL` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:JURISDICAO_ESCOLAR_EDUCACAO_INFANTIL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_JURCR` | `xsd:decimal` | false | 1..1 |
| `COD_JURISDICAO` | `xsd:string` | true | 0..1 |
| `REGIONAL` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:JURISDICAO_ESCOLAR_EF`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_JUREF` | `xsd:decimal` | false | 1..1 |
| `COD_JURISDICAO` | `xsd:string` | true | 0..1 |
| `REGIONAL` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:LAGOA_PAMPULHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_RPSA` | `xsd:decimal` | false | 1..1 |
| `CODIGO_FLORESTAL` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:LANCHONETES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ATVECON` | `xsd:decimal` | false | 1..1 |
| `CNAE_PRINCIPAL` | `xsd:string` | true | 0..1 |
| `DESCRICAO_CNAE` | `xsd:string` | true | 0..1 |
| `CNAE` | `xsd:string` | true | 0..1 |
| `NATUREZA_JURIDICA` | `xsd:string` | true | 0..1 |
| `PORTE_EMPRESA` | `xsd:string` | true | 0..1 |
| `AREA_UTILIZADA` | `xsd:string` | true | 0..1 |
| `IND_SIMPLES` | `xsd:string` | true | 0..1 |
| `IND_MEI` | `xsd:string` | true | 0..1 |
| `TIPO_UNIDADE` | `xsd:string` | true | 0..1 |
| `FORMA_ATUACAO` | `xsd:string` | true | 0..1 |
| `DESC_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `NOME_FANTASIA` | `xsd:string` | true | 0..1 |
| `CNPJ` | `xsd:string` | true | 0..1 |
| `DATA_INICIO_ATIVIDADE` | `xsd:string` | true | 0..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |
| `INSCRICAO_MUNICIPAL` | `xsd:string` | true | 0..1 |
| `IND_POSSUI_ALVARA` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:LIMITE_AREA_PLANEJADA_1895`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_LIMITE_AREA_PLANEJADA_1895` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:LIMITE_MUNICIPIO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_LM` | `xsd:decimal` | false | 1..1 |
| `AREA_KM2` | `xsd:decimal` | true | 0..1 |
| `PERIMETR_M` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:LINHA_METRO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_MTR` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:LINHA_TRANSMISSAO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_LT` | `xsd:decimal` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:LOCAL_ENTREGA_VOLUNTARIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_LEV` | `xsd:decimal` | false | 1..1 |
| `NOME_LEV` | `xsd:string` | false | 1..1 |
| `TIPO_MATERIAL_COLETADO` | `xsd:string` | true | 0..1 |
| `HORARIO_FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `LETRA_IMOVEL` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `REGIONAL` | `xsd:string` | true | 0..1 |
| `REF_LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:LOGRADOURO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_LOGRADOURO` | `xsd:decimal` | false | 1..1 |
| `COD_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `NOME_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `LARGURA_MEDIA` | `xsd:decimal` | true | 0..1 |
| `COMPRIMENTO_LOGRADOURO` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:LOGRADOURO_DESTAQUE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_LOGRADOURO_DESTAQUE` | `xsd:decimal` | false | 1..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `CODIGO` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:CurvePropertyType` | true | 0..1 |

### `ide_bhgeo:LOGRADOURO_OBRA_DE_ARTE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_OBRART` | `xsd:decimal` | false | 1..1 |
| `TIPO_OBRA_DE_ARTE` | `xsd:string` | true | 0..1 |
| `DENOMINACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:LOTE_APROVADO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_LCP` | `xsd:decimal` | false | 1..1 |
| `ZONA_FISCAL` | `xsd:string` | true | 0..1 |
| `QUARTEIRAO` | `xsd:string` | true | 0..1 |
| `LOTE` | `xsd:string` | true | 0..1 |
| `PLANTA_CP` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:LOTE_CTM`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_LT` | `xsd:decimal` | false | 1..1 |
| `NULOTCTM` | `xsd:string` | false | 1..1 |
| `ID_QUADRA_CTM` | `xsd:decimal` | false | 1..1 |
| `AREA_M2` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:MANCHA_URBANA_1918`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EMURB` | `xsd:decimal` | false | 1..1 |
| `ANO_MANCHA_URBANA` | `xsd:decimal` | false | 1..1 |
| `AREA_KM2` | `xsd:decimal` | false | 1..1 |
| `FONTE` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `CRIADOR` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:MANCHA_URBANA_1935`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EMURB` | `xsd:decimal` | false | 1..1 |
| `ANO_MANCHA_URBANA` | `xsd:decimal` | false | 1..1 |
| `AREA_KM2` | `xsd:decimal` | false | 1..1 |
| `FONTE` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `CRIADOR` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:MANCHA_URBANA_1950`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EMURB` | `xsd:decimal` | false | 1..1 |
| `ANO_MANCHA_URBANA` | `xsd:decimal` | false | 1..1 |
| `AREA_KM2` | `xsd:decimal` | false | 1..1 |
| `FONTE` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `CRIADOR` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:MANCHA_URBANA_1977`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EMURB` | `xsd:decimal` | false | 1..1 |
| `ANO_MANCHA_URBANA` | `xsd:decimal` | false | 1..1 |
| `AREA_KM2` | `xsd:decimal` | false | 1..1 |
| `FONTE` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `CRIADOR` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:MANCHA_URBANA_1999`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EMURB` | `xsd:decimal` | false | 1..1 |
| `ANO_MANCHA_URBANA` | `xsd:decimal` | false | 1..1 |
| `AREA_KM2` | `xsd:decimal` | false | 1..1 |
| `FONTE` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `CRIADOR` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:MANCHA_URBANA_2007`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EMURB` | `xsd:decimal` | false | 1..1 |
| `ANO_MANCHA_URBANA` | `xsd:decimal` | false | 1..1 |
| `AREA_KM2` | `xsd:decimal` | false | 1..1 |
| `FONTE` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `CRIADOR` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:MANCHA_URBANA_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EMURB` | `xsd:decimal` | false | 1..1 |
| `ANO_MANCHA_URBANA` | `xsd:decimal` | false | 1..1 |
| `AREA_KM2` | `xsd:decimal` | false | 1..1 |
| `FONTE` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `CRIADOR` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:MEIO_FIO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_BASE_MF` | `xsd:decimal` | false | 1..1 |
| `ID_BASE_TRECHO` | `xsd:decimal` | true | 0..1 |
| `IND_MF` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:MEIO_FIO_QUADRA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_MFQ` | `xsd:decimal` | false | 1..1 |
| `IND_MEIO_FIO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | false | 1..1 |

### `ide_bhgeo:MEIO_FIO_QUADRA_DESTAQUE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_MFQ` | `xsd:decimal` | false | 1..1 |
| `IND_MEIO_FIO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | false | 1..1 |

### `ide_bhgeo:MERCADO_MUNICIPAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIP_SEG_ALIM_NUTRI` | `xsd:decimal` | false | 1..1 |
| `NOME_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `REFERENCIA` | `xsd:string` | true | 0..1 |
| `DIA_HORARIO` | `xsd:string` | true | 0..1 |
| `CONTATO` | `xsd:string` | true | 0..1 |
| `INFORMACOES_ADICIONAIS` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `NUMERO_BARRACAS` | `xsd:decimal` | true | 0..1 |
| `PRODUTOS_COMERCIALIZADOS` | `xsd:string` | true | 0..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:MICRO_EMPRESA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ATIV_ECON_ESTABELECIMENTO` | `xsd:decimal` | false | 1..1 |
| `CNAE_PRINCIPAL` | `xsd:string` | true | 0..1 |
| `DESCRICAO_CNAE_PRINCIPAL` | `xsd:string` | true | 0..1 |
| `CNAE` | `xsd:string` | true | 0..1 |
| `DATA_INICIO_ATIVIDADE` | `xsd:string` | true | 0..1 |
| `NATUREZA_JURIDICA` | `xsd:string` | true | 0..1 |
| `PORTE_EMPRESA` | `xsd:string` | true | 0..1 |
| `AREA_UTILIZADA` | `xsd:string` | true | 0..1 |
| `IND_SIMPLES` | `xsd:string` | true | 0..1 |
| `IND_MEI` | `xsd:string` | true | 0..1 |
| `IND_POSSUI_ALVARA` | `xsd:string` | true | 0..1 |
| `TIPO_UNIDADE` | `xsd:string` | true | 0..1 |
| `FORMA_ATUACAO` | `xsd:string` | true | 0..1 |
| `DESC_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `NOME_FANTASIA` | `xsd:string` | true | 0..1 |
| `CNPJ` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:MUNICIPIO_RMBH`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_MRMBH` | `xsd:decimal` | false | 1..1 |
| `NOME_MUNICIPIO` | `xsd:string` | false | 1..1 |
| `LEI_CRIACAO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:NASCENTE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_NASCENTE` | `xsd:decimal` | false | 1..1 |
| `CODIGO_FLORESTAL` | `xsd:string` | true | 0..1 |
| `APP` | `xsd:decimal` | true | 0..1 |
| `GENESE` | `xsd:string` | true | 0..1 |
| `TEMPORALIDADE` | `xsd:string` | true | 0..1 |
| `FORMA` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:NO_CIRCULACAO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_NTCV` | `xsd:decimal` | false | 1..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:OBRAS_SUDECAP`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_AREA_EMPREENDIMENTO` | `xsd:decimal` | false | 1..1 |
| `NUMERO_PO` | `xsd:decimal` | false | 1..1 |
| `NOME_PO` | `xsd:string` | true | 0..1 |
| `REGIONAL` | `xsd:string` | true | 0..1 |
| `TEMATICA` | `xsd:string` | true | 0..1 |
| `STATUS` | `xsd:string` | true | 0..1 |
| `ORCAMENTO_PARTICIPATIVO` | `xsd:string` | true | 0..1 |
| `EMPRESA_RESPONSAVEL` | `xsd:string` | true | 0..1 |
| `GRUPO` | `xsd:string` | true | 0..1 |
| `PLANEJAMENTO_OBRA` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:OCORRENCIA_SINISTRO_TRANSITO_COM_VITIMA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_SINISTRO_TRANSITO` | `xsd:decimal` | false | 1..1 |
| `NUMERO_BOLETIM` | `xsd:string` | true | 0..1 |
| `DATA_HORA_BOLETIM` | `xsd:dateTime` | false | 1..1 |
| `DESCRICAO_TIPO_ACIDENTE` | `xsd:string` | true | 0..1 |
| `DESCRICAO_REGIONAL` | `xsd:string` | true | 0..1 |
| `INDICADOR_FATALIDADE` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:OCUPACAO_LOTEAMENTO_IRREGULAR`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_OCUPACAO_LOTEAM_IRREG` | `xsd:decimal` | false | 1..1 |
| `NOME_LOCALIDADE` | `xsd:string` | false | 1..1 |
| `APELIDO_LOCALIDADE` | `xsd:string` | true | 0..1 |
| `PLANO_URBANISTICO` | `xsd:string` | true | 0..1 |
| `REGIONAL` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:OLEI`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_OLEI` | `xsd:decimal` | false | 1..1 |
| `NOME_EMPREENDIMENTO` | `xsd:string` | true | 0..1 |
| `COD_REQUERIMENTO_OLEI` | `xsd:string` | true | 0..1 |
| `TIPO_OLEI` | `xsd:string` | true | 0..1 |
| `TIPOLOGIA_ENQUADRAMENTO` | `xsd:string` | true | 0..1 |
| `ETAPA_LICENCA` | `xsd:string` | true | 0..1 |
| `DATA_EMISSAO` | `xsd:string` | true | 0..1 |
| `DATA_VALIDADE` | `xsd:string` | true | 0..1 |
| `DATA_ATENDIMENTO_BH_DIGITAL` | `xsd:string` | true | 0..1 |
| `PROCESSO_BHDIGITAL` | `xsd:string` | true | 0..1 |
| `DADOS_LICENCA_DEFERIMENTO` | `xsd:string` | true | 0..1 |
| `DATA_CONCLUSAO_PROCESSO_LICENCIAMENTO` | `xsd:string` | true | 0..1 |
| `DSC_SITUACAO_REQUERIMENTO_OLEI` | `xsd:string` | true | 0..1 |
| `INDICE_CADASTRAL` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:ONDAS_CALOR_AREA_PRIORITARIA_SBN`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_AREAS_PRIORITARIAS_SBN_2022` | `xsd:decimal` | false | 1..1 |
| `AREA_M2` | `xsd:double` | true | 0..1 |
| `EXP_ALAG` | `xsd:double` | true | 0..1 |
| `EXP_DESL` | `xsd:double` | true | 0..1 |
| `EXP_INUN` | `xsd:double` | true | 0..1 |
| `EXP_ONDA` | `xsd:double` | true | 0..1 |
| `VUL_ALAG` | `xsd:double` | true | 0..1 |
| `VUL_DESL` | `xsd:double` | true | 0..1 |
| `VUL_INUN` | `xsd:double` | true | 0..1 |
| `VUL_ONDA` | `xsd:double` | true | 0..1 |
| `AC_ALAG` | `xsd:double` | true | 0..1 |
| `AC_DESL` | `xsd:double` | true | 0..1 |
| `AC_INUN` | `xsd:double` | true | 0..1 |
| `AC_ONDA` | `xsd:double` | true | 0..1 |
| `CON_AMB` | `xsd:double` | true | 0..1 |
| `CON_ANT` | `xsd:double` | true | 0..1 |
| `CON_TOT` | `xsd:double` | true | 0..1 |
| `SBN_ALAG` | `xsd:double` | true | 0..1 |
| `SBN_DESL` | `xsd:double` | true | 0..1 |
| `SBN_INUN` | `xsd:double` | true | 0..1 |
| `SBN_ONDA` | `xsd:double` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:OPERACAO_URBANA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_OPU` | `xsd:decimal` | false | 1..1 |
| `TIPO` | `xsd:string` | false | 1..1 |
| `NOME` | `xsd:string` | false | 1..1 |
| `VALIDADE` | `xsd:date` | true | 0..1 |
| `SITUACAO` | `xsd:string` | false | 1..1 |
| `SUBDIVISAO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:OPERACAO_URBANA_11181`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_OPERACAO_URBANA` | `xsd:decimal` | false | 1..1 |
| `TIPO` | `xsd:string` | false | 1..1 |
| `NOME` | `xsd:string` | false | 1..1 |
| `SITUACAO` | `xsd:string` | true | 0..1 |
| `VALIDADE` | `xsd:date` | true | 0..1 |
| `SUBDIVISAO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:OPERACAO_URBANA_TRANS_11181`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_OPERACAO_URBANA_TRANS_11181` | `xsd:decimal` | false | 1..1 |
| `TIPO` | `xsd:string` | false | 1..1 |
| `NOME` | `xsd:string` | false | 1..1 |
| `SUBDIVISAO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:PARQUE_LAGOA_PAMPULHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_UNIDADE_FPMZB` | `xsd:decimal` | false | 1..1 |
| `NOME_UNIDADE_FPMZB` | `xsd:string` | false | 1..1 |
| `IND_ABERTO_PUBLICO` | `xsd:string` | true | 0..1 |
| `LEGISLACAO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE_PRINCIPAL` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:PARQUES_MUNICIPAIS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_UNIDADE_FPMZB` | `xsd:decimal` | false | 1..1 |
| `NOME_UNIDADE_FPMZB` | `xsd:string` | false | 1..1 |
| `IND_ABERTO_PUBLICO` | `xsd:string` | true | 0..1 |
| `LEGISLACAO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE_PRINCIPAL` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:PAVIMENTACAO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_PAV` | `xsd:decimal` | false | 1..1 |
| `ID_BASE_TRECHO` | `xsd:decimal` | true | 0..1 |
| `LARG_INICIO` | `xsd:double` | true | 0..1 |
| `LARG_FINAL` | `xsd:double` | true | 0..1 |
| `IND_PAV` | `xsd:string` | true | 0..1 |
| `LADO_PAV` | `xsd:string` | true | 0..1 |
| `TP_PAV` | `xsd:string` | true | 0..1 |
| `DATA` | `xsd:date` | true | 0..1 |
| `ID_LOGRADOURO` | `xsd:decimal` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:PER_USO_REGRA_ESPEC_AREA_7166`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_AREA_PERMIS_USO_RE_7166` | `xsd:decimal` | false | 1..1 |
| `TIPO_PERMISSIVIDADE` | `xsd:string` | true | 0..1 |
| `DESCRICAO_TIPO_PERMISSIVIDADE` | `xsd:string` | true | 0..1 |
| `TIPO_AREA` | `xsd:string` | true | 0..1 |
| `DESCRICAO_AREA` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:PERM_USO_LOTES_BELVII_11181`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_PERM_USO_LOTES_BELVII_11181` | `xsd:decimal` | false | 1..1 |
| `SIGLA_PERMISSIVIDADE_ESPEC` | `xsd:string` | false | 1..1 |
| `DESC_PERMISSIVIDADE_ESPEC` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:PERMISSIV_ESPEC_TRECHO_7166`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_TRECHO_PERMISSIV_ESPEC_7166` | `xsd:decimal` | false | 1..1 |
| `TIPO_PERMISSIVIDADE` | `xsd:string` | true | 0..1 |
| `DESCRICAO_TIPO_PERMISSIVIDADE` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:PERMISSIV_REGRA_GERAL_7166`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_PERMIS_USO_RG_7166` | `xsd:decimal` | false | 1..1 |
| `TIPO_LOGRAD` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `DESCRICAO_PERMISSIVIDADE` | `xsd:string` | true | 0..1 |
| `SIGLA_TIPO_PERMISSIVIDADE` | `xsd:string` | true | 0..1 |
| `ID_TIPO_PERMISSIVIDADE_GERAL` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:PERMISSIV_USO_REG_ESP_11181`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_PERMISSIVIDADE_REGRA_ESPEC` | `xsd:decimal` | false | 1..1 |
| `TPLOG` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `DESC_PERMISSIVIDADE_ESPEC` | `xsd:string` | true | 0..1 |
| `SIGLA_PERMISSIVIDADE_ESPEC` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:PERMISSIV_USO_REG_GERAL_11181`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_CLASSIF_VIA_PERMISSIVIDADE` | `xsd:decimal` | false | 1..1 |
| `TPLOG` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `DESCRICAO_PERMISSIVIDADE` | `xsd:string` | true | 0..1 |
| `SIGLA_TIPO_PERMISSIVIDADE` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:PISTA_AEROPORTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_PAERO` | `xsd:decimal` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:PISTA_SKATE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQ_ESP` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `NOME_POPULAR` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `REF_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `GESTOR_EQUIP_ESPORT` | `xsd:string` | true | 0..1 |
| `STATUS` | `xsd:string` | true | 0..1 |
| `CODIGO` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:PLANTA_APROVADA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_PCP` | `xsd:decimal` | false | 1..1 |
| `COD_PLANTA_CP` | `xsd:string` | false | 1..1 |
| `ZONA_FISCAL` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:PLANTA_PARTICULAR`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_PLANTA_PARTICULAR` | `xsd:decimal` | false | 1..1 |
| `NOME_BAIRRO_PLANTA` | `xsd:string` | true | 0..1 |
| `REGIONAL` | `xsd:string` | true | 0..1 |
| `NUMERO_PLANTA` | `xsd:string` | true | 0..1 |
| `NUM_PLANTA_ANTERIOR` | `xsd:string` | true | 0..1 |
| `NOME_REFERENCIA` | `xsd:string` | true | 0..1 |
| `PLANTA_PARTICULAR` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:PONTO_ALTIMETRICO_MUNICIPIO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_PONTO_ALTIMETRICO` | `xsd:decimal` | false | 1..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |
| `COTA_M` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:PONTO_ALTIMETRICO_REGIONAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_PONTO_ALTIMETRICO` | `xsd:decimal` | false | 1..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |
| `COTA_M` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:PONTO_INCLUSAO_DIGITAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_CENTRO_INCLUSAO_DIGITAL` | `xsd:decimal` | false | 1..1 |
| `NOME_CENTRO_INCLUSAO_DIGITAL` | `xsd:string` | false | 1..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `DESC_GRUPO_USUARIO` | `xsd:string` | true | 0..1 |
| `QUANTIDADE_COMPUTADOR` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | false | 1..1 |

### `ide_bhgeo:PONTO_ONIBUS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_PONTO_ONIBUS_LINHA` | `xsd:decimal` | false | 1..1 |
| `COD_LINHA` | `xsd:string` | true | 0..1 |
| `NOME_LINHA` | `xsd:string` | true | 0..1 |
| `NOME_SUB_LINHA` | `xsd:string` | true | 0..1 |
| `ORIGEM` | `xsd:string` | true | 0..1 |
| `IDENTIFICADOR_PONTO_ONIBUS` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:PONTO_VERDE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_LEV` | `xsd:decimal` | false | 1..1 |
| `NOME_LEV` | `xsd:string` | false | 1..1 |
| `TIPO_MATERIAL_COLETADO` | `xsd:string` | true | 0..1 |
| `HORARIO_FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `LETRA_IMOVEL` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `REGIONAL` | `xsd:string` | true | 0..1 |
| `REF_LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:PONTOS_DE_CULTURA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_PONTO_CULTURAL` | `xsd:decimal` | false | 1..1 |
| `NOME_PONTO_CULTURAL` | `xsd:string` | true | 0..1 |
| `DATA_CERTIFICACAO` | `xsd:date` | true | 0..1 |
| `REDE_SOCIAL` | `xsd:string` | true | 0..1 |
| `AREA_ATUACAO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:PONTOS_REDE_TRIANGULACAO_1895`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_PTS_REDE_TRIANGULACAO_1895` | `xsd:decimal` | false | 1..1 |
| `NOME_MARCO` | `xsd:string` | true | 0..1 |
| `ALTITUDE` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:POP_DOMIC_BAIRRO_2010`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_POP_DMC` | `xsd:decimal` | false | 1..1 |
| `NUM_BAIRRO` | `xsd:decimal` | true | 0..1 |
| `NOME_BAIRRO` | `xsd:string` | true | 0..1 |
| `POPULACAO` | `xsd:decimal` | true | 0..1 |
| `DOMICILIO` | `xsd:decimal` | true | 0..1 |
| `HAB_DOM` | `xsd:decimal` | true | 0..1 |
| `HAB_KM2` | `xsd:decimal` | true | 0..1 |
| `AREA_KM2` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `QTDE_DOMIC_KM2` | `xsd:decimal` | true | 0..1 |

### `ide_bhgeo:POP_DOMIC_BAIRRO_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_POP_DOMIC_BAIRRO_2022` | `xsd:decimal` | false | 1..1 |
| `NUM_BAIRRO` | `xsd:decimal` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `AREA_KM` | `xsd:decimal` | true | 0..1 |
| `POPULACAO` | `xsd:decimal` | true | 0..1 |
| `DOMICILIOS` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `DENSIDADE_DEMOGRAFICA` | `xsd:decimal` | true | 0..1 |
| `QTDE_DOMIC_KM2` | `xsd:decimal` | true | 0..1 |

### `ide_bhgeo:POP_DOMIC_REGIONAL_2010`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_REGIONAL` | `xsd:decimal` | false | 1..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |
| `QTDE_POPULACAO` | `xsd:decimal` | true | 0..1 |
| `QTDE_DOMICILIO` | `xsd:decimal` | true | 0..1 |
| `QTDE_HAB_DOM` | `xsd:decimal` | true | 0..1 |
| `QTDE_HAB_KM2` | `xsd:decimal` | true | 0..1 |
| `AREA_KM2` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `QTDE_DOMIC_KM2` | `xsd:decimal` | true | 0..1 |

### `ide_bhgeo:POP_DOMIC_REGIONAL_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_POP_DOMIC_REGIONAL_2022` | `xsd:decimal` | false | 1..1 |
| `COD_REGIONAL` | `xsd:decimal` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `SIGLA` | `xsd:string` | true | 0..1 |
| `AREA_KM` | `xsd:decimal` | true | 0..1 |
| `POPULACAO` | `xsd:decimal` | true | 0..1 |
| `DOMICILIOS` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `DENSIDADE_DEMOGRAFICA` | `xsd:decimal` | true | 0..1 |
| `QTDE_DOMIC_KM2` | `xsd:decimal` | true | 0..1 |

### `ide_bhgeo:POSTE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_POSTE_ILUMINACAO` | `xsd:decimal` | false | 1..1 |
| `ILUMINACAO_PUBLICA` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:POSTO_VENDA_ROTATIVO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_POSTO_VENDA_ROTATIVO` | `xsd:decimal` | false | 1..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | false | 1..1 |

### `ide_bhgeo:PRACA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_PRC` | `xsd:decimal` | false | 1..1 |
| `ID_LOGRADOURO` | `xsd:decimal` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `NOME_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:PREFEITURA_BELO_HORIZONTE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_REFERENCIA_LOCALIZACAO` | `xsd:decimal` | false | 1..1 |
| `NOME_REFERENCIA_LOCALIZACAO` | `xsd:string` | false | 1..1 |
| `ID_CATEGORIA_REFERENCIA_LOC` | `xsd:decimal` | false | 1..1 |
| `TIPO_REFERENCIA_LOCALIZACAO` | `xsd:string` | false | 1..1 |
| `ID_ENDERECO_PBH` | `xsd:decimal` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `CONTATO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:PRESTACAO_SERVICOS_INFORMACAO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ATVECON` | `xsd:decimal` | false | 1..1 |
| `CNAE_PRINCIPAL` | `xsd:string` | true | 0..1 |
| `DESCRICAO_CNAE` | `xsd:string` | true | 0..1 |
| `CNAE` | `xsd:string` | true | 0..1 |
| `NATUREZA_JURIDICA` | `xsd:string` | true | 0..1 |
| `PORTE_EMPRESA` | `xsd:string` | true | 0..1 |
| `AREA_UTILIZADA` | `xsd:string` | true | 0..1 |
| `IND_SIMPLES` | `xsd:string` | true | 0..1 |
| `IND_MEI` | `xsd:string` | true | 0..1 |
| `TIPO_UNIDADE` | `xsd:string` | true | 0..1 |
| `FORMA_ATUACAO` | `xsd:string` | true | 0..1 |
| `DESC_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `NOME_FANTASIA` | `xsd:string` | true | 0..1 |
| `CNPJ` | `xsd:string` | true | 0..1 |
| `DATA_INICIO_ATIVIDADE` | `xsd:string` | true | 0..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |
| `INSCRICAO_MUNICIPAL` | `xsd:string` | true | 0..1 |
| `IND_POSSUI_ALVARA` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:PROGRAMA_ABASTECER`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIP_SEG_ALIM_NUTRI` | `xsd:decimal` | false | 1..1 |
| `NOME_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `REFERENCIA` | `xsd:string` | true | 0..1 |
| `DIA_HORARIO` | `xsd:string` | true | 0..1 |
| `CONTATO` | `xsd:string` | true | 0..1 |
| `INFORMACOES_ADICIONAIS` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `NUMERO_BARRACAS` | `xsd:decimal` | true | 0..1 |
| `PRODUTOS_COMERCIALIZADOS` | `xsd:string` | true | 0..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:PROGRAMA_ADORO_BH_AREA_ADOTADA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_PROGRAMA_ADORO_BH` | `xsd:decimal` | false | 1..1 |
| `DESC_TIPO_AREA_PUBLICA` | `xsd:string` | true | 0..1 |
| `SITUACAO` | `xsd:string` | true | 0..1 |
| `AREA` | `xsd:decimal` | true | 0..1 |
| `NUM_PROCESSO` | `xsd:string` | true | 0..1 |
| `NOME_ADOTANTE` | `xsd:string` | true | 0..1 |
| `DATA_PUBLICACAO` | `xsd:string` | true | 0..1 |
| `DATA_INICIO_VIGENCIA` | `xsd:string` | true | 0..1 |
| `DATA_FIM_VIGENCIA` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO_PRINCIPAL` | `xsd:string` | true | 0..1 |
| `LOGRADOURO_PRINCIPAL` | `xsd:string` | true | 0..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |
| `REFERENCIA_LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:PROGRAMA_ADORO_BH_AREA_ADOTAVEL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_PROGRAMA_ADORO_BH` | `xsd:decimal` | false | 1..1 |
| `DESC_TIPO_AREA_PUBLICA` | `xsd:string` | true | 0..1 |
| `SITUACAO` | `xsd:string` | true | 0..1 |
| `AREA` | `xsd:decimal` | true | 0..1 |
| `NUM_PROCESSO` | `xsd:string` | true | 0..1 |
| `NOME_ADOTANTE` | `xsd:string` | true | 0..1 |
| `DATA_PUBLICACAO` | `xsd:string` | true | 0..1 |
| `DATA_INICIO_VIGENCIA` | `xsd:string` | true | 0..1 |
| `DATA_FIM_VIGENCIA` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO_PRINCIPAL` | `xsd:string` | true | 0..1 |
| `LOGRADOURO_PRINCIPAL` | `xsd:string` | true | 0..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |
| `REFERENCIA_LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:PROGRAMA_ADOTE_JARDIM_CHUVA_AREA_ADOTADA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_PROGRAMA_ADOTE_JARDIM_CHUVA` | `xsd:decimal` | false | 1..1 |
| `AREA_INTERNA` | `xsd:double` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `NOME_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `NUMERO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `REGIONAL` | `xsd:string` | false | 1..1 |
| `PERMITE_ADOCAO` | `xsd:string` | true | 0..1 |
| `DISPONIBILIDADE` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:PROGRAMA_ADOTE_JARDIM_CHUVA_AREA_DISPONIVEL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_PROGRAMA_ADOTE_JARDIM_CHUVA` | `xsd:decimal` | false | 1..1 |
| `AREA_INTERNA` | `xsd:double` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `NOME_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `NUMERO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `REGIONAL` | `xsd:string` | false | 1..1 |
| `PERMITE_ADOCAO` | `xsd:string` | true | 0..1 |
| `DISPONIBILIDADE` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:PROGRAMA_ESPACO_CIDADANIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIPAMENTO_CIDADANIA` | `xsd:decimal` | false | 1..1 |
| `NOME_EQUIPAMENTO_CIDADANIA` | `xsd:string` | false | 1..1 |
| `DESC_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `LETRA_IMOVEL` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO` | `xsd:string` | true | 0..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `DESCRICAO_CATEGORIA` | `xsd:string` | true | 0..1 |
| `DIAS_FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `HORARIO_FUNCIONAMENTO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:PROGRAMA_QUALIF_CENTRALIDADE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_PROGRAMA_QUALIF_CENTRALIDADE` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | false | 1..1 |
| `SITUACAO` | `xsd:string` | false | 1..1 |
| `TIPO_ACAO` | `xsd:string` | true | 0..1 |
| `ESCOPO_COOPERACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:SurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:PROGRAMA_VILA_MAIS_CONECTADA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_WPID` | `xsd:decimal` | false | 1..1 |
| `SIGLA_AP` | `xsd:string` | false | 1..1 |
| `LOCAL_INSTALACAO` | `xsd:string` | false | 1..1 |
| `NOME_BAIRRO` | `xsd:string` | false | 1..1 |
| `EQUIPAMENTO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | false | 1..1 |

### `ide_bhgeo:PROJ_VIARIO_PRIOR_11181`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `NOME_VIURBS` | `xsd:string` | true | 0..1 |
| `ID_PROJ_VIARIO_PRIOR` | `xsd:decimal` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:PROJETO_EDIFICACAO_LICENCIADO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_PROJETO_EDIFICACOES` | `xsd:decimal` | false | 1..1 |
| `NUMERO_PROCESSO` | `xsd:string` | true | 0..1 |
| `NUM_REQUERIMENTO` | `xsd:string` | true | 0..1 |
| `SITUACAO_REQUERIMENTO` | `xsd:string` | true | 0..1 |
| `TITULO_PROJETO` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `SITUACAO_PROJETO` | `xsd:string` | true | 0..1 |
| `NUM_ULTIMO_ALVARA` | `xsd:string` | true | 0..1 |
| `DT_EMISSAO_ALVARA_CONSTRUCAO` | `xsd:date` | true | 0..1 |
| `DT_CONCESSAO_ULTIMO_ALVARA` | `xsd:date` | true | 0..1 |
| `DT_VALIDADE_ULTIMO_ALVARA` | `xsd:date` | true | 0..1 |
| `DATA_COMUNICADO_INICIO_OBRA` | `xsd:date` | true | 0..1 |
| `DATA_ULTIMA_BAIXA` | `xsd:date` | true | 0..1 |
| `TIPO_ULTIMA_BAIXA` | `xsd:string` | true | 0..1 |
| `ENDERECO` | `xsd:string` | true | 0..1 |
| `LOTE_PROJETO` | `xsd:string` | true | 0..1 |
| `USO_GERAL` | `xsd:string` | true | 0..1 |
| `QTD_UND_RESIDENCIAL` | `xsd:decimal` | true | 0..1 |
| `QTD_UND_NAO_RESIDENCIAL` | `xsd:decimal` | true | 0..1 |
| `AREA_CONSTRUIDA` | `xsd:double` | true | 0..1 |
| `TIPO_APROVACAO` | `xsd:string` | true | 0..1 |
| `DATA_APROVACAO` | `xsd:string` | true | 0..1 |
| `AREA_LIQUIDA` | `xsd:double` | true | 0..1 |
| `QTDE_PAVIMENTOS` | `xsd:decimal` | true | 0..1 |
| `LINK_SIATU_EDIFICACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:PROJETO_VIARIO_PRIORITARIO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_PVP` | `xsd:decimal` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:PROPOSTA_OUS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_PROPOSTA_OUS` | `xsd:decimal` | false | 1..1 |
| `NOME_OUS` | `xsd:string` | false | 1..1 |
| `PROTOCOLO_PBH` | `xsd:string` | false | 1..1 |
| `DESC_SITUACAO` | `xsd:string` | true | 0..1 |
| `LEI` | `xsd:string` | true | 0..1 |
| `DATA_VALIDADE_OPERACAO` | `xsd:string` | true | 0..1 |
| `PROJETO_LEI` | `xsd:string` | true | 0..1 |
| `DATA_ULTIMA_AUDIENCIA_PUBLIC` | `xsd:string` | true | 0..1 |
| `EMPREENDIMENTO` | `xsd:string` | true | 0..1 |
| `USO_EMPREENDIMENTO` | `xsd:string` | true | 0..1 |
| `DESC_PERIMETRO` | `xsd:string` | true | 0..1 |
| `DESC_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `LETRA_IMOVEL` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `NUM_LOTE` | `xsd:string` | true | 0..1 |
| `NUM_QUARTEIRAO_CP` | `xsd:string` | true | 0..1 |
| `NUM_ZONA_FISCAL` | `xsd:string` | true | 0..1 |
| `RESPONSAVEL_LEGAL` | `xsd:string` | true | 0..1 |
| `RESPONSAVEL_PROJETO` | `xsd:string` | true | 0..1 |
| `RESPONSAVEL_ESTUDO` | `xsd:string` | true | 0..1 |
| `DATA_PROTOCOLO` | `xsd:string` | true | 0..1 |
| `INTERESSE_PUBLICO` | `xsd:string` | true | 0..1 |
| `INTERESSE_PARCEIRO` | `xsd:string` | true | 0..1 |
| `VALOR_CONTRAPARTIDA` | `xsd:decimal` | true | 0..1 |
| `INTERVENCAO_CONTRAPARTIDA` | `xsd:string` | true | 0..1 |
| `MEDIDAS_QUALIFICACAO` | `xsd:string` | true | 0..1 |
| `OBSERVACAO` | `xsd:string` | true | 0..1 |
| `DATA_CONCLUSAO_INTERVENCAO` | `xsd:string` | true | 0..1 |
| `JUSTIFICATIVA_INDEFERIMENTO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `SITUACAO_CONTRAPARTIDA` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:QUADRA_CEMITERIO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_QUADRA_CEMITERIO` | `xsd:decimal` | false | 1..1 |
| `NUM_QUADRA_CEMITERIO` | `xsd:string` | false | 1..1 |
| `NOME_CEMITERIO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiGeometryPropertyType` | true | 0..1 |

### `ide_bhgeo:QUADRA_CTM`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_QDR` | `xsd:decimal` | false | 1..1 |
| `CODIGO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:QUADRA_ESPORTIVA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQ_ESP` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `NOME_POPULAR` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `REF_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `GESTOR_EQUIP_ESPORT` | `xsd:string` | true | 0..1 |
| `STATUS` | `xsd:string` | true | 0..1 |
| `CODIGO` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:QUADRA_VIARIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_QUADRA_VIARIA` | `xsd:decimal` | false | 1..1 |
| `IND_NIVEL_SOLO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:RADIACAO_ELETROMAG_ANTENA_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_RADIACAO_ELETROMAG_ANTENA` | `xsd:decimal` | false | 1..1 |
| `DATA_MEDICAO` | `xsd:string` | true | 0..1 |
| `HORA_MEDICAO` | `xsd:string` | true | 0..1 |
| `ANO_MEDICAO` | `xsd:string` | true | 0..1 |
| `VALOR_MEDIO` | `xsd:double` | true | 0..1 |
| `VALOR_MAXIMO` | `xsd:double` | true | 0..1 |
| `VALOR_LIMITE` | `xsd:double` | true | 0..1 |
| `VALOR_PERCENTUAL` | `xsd:decimal` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `LOGRADOURO` | `xsd:string` | false | 1..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | false | 1..1 |
| `BAIRRO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:RADIACAO_ELETROMAG_ANTENA_2019`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_RADIACAO_ELETROMAG_ANTENA` | `xsd:decimal` | false | 1..1 |
| `DATA_MEDICAO` | `xsd:string` | true | 0..1 |
| `HORA_MEDICAO` | `xsd:string` | true | 0..1 |
| `ANO_MEDICAO` | `xsd:string` | true | 0..1 |
| `VALOR_MEDIO` | `xsd:double` | true | 0..1 |
| `VALOR_MAXIMO` | `xsd:double` | true | 0..1 |
| `VALOR_LIMITE` | `xsd:double` | true | 0..1 |
| `VALOR_PERCENTUAL` | `xsd:decimal` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `LOGRADOURO` | `xsd:string` | false | 1..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | false | 1..1 |
| `BAIRRO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:RADIACAO_ELETROMAG_ANTENA_2021`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_RADIACAO_ELETROMAG_ANTENA` | `xsd:decimal` | false | 1..1 |
| `DATA_MEDICAO` | `xsd:string` | true | 0..1 |
| `HORA_MEDICAO` | `xsd:string` | true | 0..1 |
| `ANO_MEDICAO` | `xsd:string` | true | 0..1 |
| `VALOR_MEDIO` | `xsd:double` | true | 0..1 |
| `VALOR_MAXIMO` | `xsd:double` | true | 0..1 |
| `VALOR_LIMITE` | `xsd:double` | true | 0..1 |
| `VALOR_PERCENTUAL` | `xsd:decimal` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `LOGRADOURO` | `xsd:string` | false | 1..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | false | 1..1 |
| `BAIRRO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:RADIACAO_ELETROMAG_ANTENA_2025`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_RADIACAO_ELETROMAG_ANTENA` | `xsd:decimal` | false | 1..1 |
| `DATA_MEDICAO` | `xsd:string` | true | 0..1 |
| `HORA_MEDICAO` | `xsd:string` | true | 0..1 |
| `ANO_MEDICAO` | `xsd:string` | true | 0..1 |
| `VALOR_MEDIO` | `xsd:double` | true | 0..1 |
| `VALOR_MAXIMO` | `xsd:double` | true | 0..1 |
| `VALOR_LIMITE` | `xsd:double` | true | 0..1 |
| `VALOR_PERCENTUAL` | `xsd:decimal` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `LOGRADOURO` | `xsd:string` | false | 1..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | false | 1..1 |
| `BAIRRO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:RECUO_ALINHAMENTO_11181`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_RECUO_ALINHAMENTO` | `xsd:decimal` | false | 1..1 |
| `TPLOG` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LARGURA_FINAL_TRECHO` | `xsd:decimal` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:REDE_AGUA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_BASE_TRECHO` | `xsd:decimal` | true | 0..1 |
| `ID_RDAGU` | `xsd:decimal` | false | 1..1 |
| `LARG_INICIO` | `xsd:double` | true | 0..1 |
| `LARG_FINAL` | `xsd:double` | true | 0..1 |
| `LADO_RDAGU` | `xsd:string` | true | 0..1 |
| `IND_RDAGU` | `xsd:string` | true | 0..1 |
| `DATA` | `xsd:date` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:REDE_CICLOVIARIA_ANEXOIX`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_REDE_CICLOVIARIA_ANEXOIX` | `xsd:decimal` | false | 1..1 |
| `DESCRICAO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:REDE_ELETRICA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_BASE_TRECHO` | `xsd:decimal` | true | 0..1 |
| `ID_BASE_RE` | `xsd:decimal` | false | 1..1 |
| `IND_RE` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:REDE_ESGOTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_BASE_TRECHO` | `xsd:decimal` | true | 0..1 |
| `ID_RDESG` | `xsd:decimal` | false | 1..1 |
| `LARG_INICIO` | `xsd:double` | true | 0..1 |
| `LARG_FINAL` | `xsd:double` | true | 0..1 |
| `LADO_RDESG` | `xsd:string` | true | 0..1 |
| `IND_RDESG` | `xsd:string` | true | 0..1 |
| `DATA` | `xsd:date` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:REDE_EST_TRANSP_COLETIVO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_REDE_ESTR_TRAN_COLETIVO` | `xsd:decimal` | false | 1..1 |
| `DESCRICAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:REDE_MICRODRENAGEM`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_REDE_MICRODRENAGEM` | `xsd:decimal` | false | 1..1 |
| `MATERIAL` | `xsd:string` | true | 0..1 |
| `DIAMETRO` | `xsd:string` | true | 0..1 |
| `ALTURA` | `xsd:decimal` | true | 0..1 |
| `LARGURA` | `xsd:decimal` | true | 0..1 |
| `COMPRIMENTO` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:REDE_MUNIC_REFERENCIA_CADASTRAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_MARCG` | `xsd:decimal` | false | 1..1 |
| `NOME_MARCO_GEODESICO` | `xsd:string` | false | 1..1 |
| `EXECUCAO` | `xsd:string` | true | 0..1 |
| `DATA_ULTIMA_VISITA` | `xsd:string` | true | 0..1 |
| `MONOGRAFIA` | `xsd:string` | true | 0..1 |
| `UTM_NORTE` | `xsd:decimal` | true | 0..1 |
| `UTM_ESTE` | `xsd:decimal` | true | 0..1 |
| `ALTITUDE_GEO` | `xsd:decimal` | true | 0..1 |
| `SIST_REF_GEODESICO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | false | 1..1 |

### `ide_bhgeo:REDE_PRIORIZACAO_ONIBUS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_REDE_PRIORIZACAO_ONIBUS` | `xsd:decimal` | false | 1..1 |
| `SITUACAO` | `xsd:string` | false | 1..1 |
| `INFRAESTRUTURA_PREDOMINANTE` | `xsd:string` | true | 0..1 |
| `INFRA_DETALHADA_SENTIDO` | `xsd:string` | true | 0..1 |
| `ANO_IMPLANT_INFRA_ATUAL` | `xsd:decimal` | true | 0..1 |
| `POSICIONAMENTO_VIA` | `xsd:string` | true | 0..1 |
| `SISTEMA_BRT` | `xsd:string` | true | 0..1 |
| `NOME_ROTA` | `xsd:string` | true | 0..1 |
| `EXTENSAO_TRECHO` | `xsd:decimal` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRAD_INICIAL` | `xsd:string` | true | 0..1 |
| `LOGRAD_FINAL` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:REDE_PROTECAO_ESPECIAL_ALTA_COMPLEXIDADE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_REDE_SOCIOASSISTENCIAL` | `xsd:decimal` | false | 1..1 |
| `ID_ENTIDADE` | `xsd:decimal` | false | 1..1 |
| `NOME_ENTIDADE` | `xsd:string` | true | 0..1 |
| `DESC_CATEGORIA` | `xsd:string` | true | 0..1 |
| `SIGLA_CATEGORIA` | `xsd:string` | true | 0..1 |
| `TIPO_EXECUCAO` | `xsd:string` | true | 0..1 |
| `NOME_SERVICO` | `xsd:string` | true | 0..1 |
| `NIVEL_PROTECAO` | `xsd:string` | true | 0..1 |
| `SIGLA_PROTECAO` | `xsd:string` | true | 0..1 |
| `PUBLICO_USUARIO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:REDE_PROTECAO_ESPECIAL_MEDIA_COMPLEXIDADE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_REDE_SOCIOASSISTENCIAL` | `xsd:decimal` | false | 1..1 |
| `ID_ENTIDADE` | `xsd:decimal` | false | 1..1 |
| `NOME_ENTIDADE` | `xsd:string` | true | 0..1 |
| `DESC_CATEGORIA` | `xsd:string` | true | 0..1 |
| `SIGLA_CATEGORIA` | `xsd:string` | true | 0..1 |
| `TIPO_EXECUCAO` | `xsd:string` | true | 0..1 |
| `NOME_SERVICO` | `xsd:string` | true | 0..1 |
| `NIVEL_PROTECAO` | `xsd:string` | true | 0..1 |
| `SIGLA_PROTECAO` | `xsd:string` | true | 0..1 |
| `PUBLICO_USUARIO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:REDE_PROTECAO_SOCIAL_BASICA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_REDE_SOCIOASSISTENCIAL` | `xsd:decimal` | false | 1..1 |
| `ID_ENTIDADE` | `xsd:decimal` | false | 1..1 |
| `NOME_ENTIDADE` | `xsd:string` | true | 0..1 |
| `DESC_CATEGORIA` | `xsd:string` | true | 0..1 |
| `SIGLA_CATEGORIA` | `xsd:string` | true | 0..1 |
| `TIPO_EXECUCAO` | `xsd:string` | true | 0..1 |
| `NOME_SERVICO` | `xsd:string` | true | 0..1 |
| `NIVEL_PROTECAO` | `xsd:string` | true | 0..1 |
| `SIGLA_PROTECAO` | `xsd:string` | true | 0..1 |
| `PUBLICO_USUARIO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:REDE_TELEFONICA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_BASE_TRECHO` | `xsd:decimal` | true | 0..1 |
| `ID_BASE_RT` | `xsd:decimal` | false | 1..1 |
| `IND_RT` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:REDE_TRIANGULACAO_1895`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_REDE_TRIANGULACAO_1895` | `xsd:decimal` | false | 1..1 |
| `POLIGONAL` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:REDUTOR_VELOCIDADE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_REDUTOR_VELOCIDADE` | `xsd:decimal` | false | 1..1 |
| `NUM_PROJETO_OPERACIONAL` | `xsd:string` | true | 0..1 |
| `ENDERECO_REFERENCIA` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `REFERENCIA_LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `DATA_IMPLANTACAO` | `xsd:date` | true | 0..1 |
| `DATA_ULTIMA_MANUTENCAO` | `xsd:date` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:REFERENCIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_REF` | `xsd:decimal` | false | 1..1 |
| `TIPO_REF` | `xsd:string` | true | 0..1 |
| `NOME_OFICIAL` | `xsd:string` | true | 0..1 |
| `NOME_POPULAR` | `xsd:string` | true | 0..1 |
| `INFO_COMPLEMENTAR` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:REGIONAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_REG` | `xsd:decimal` | false | 1..1 |
| `COD_REG` | `xsd:decimal` | false | 1..1 |
| `SIGLA` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | false | 1..1 |
| `AREA_KM2` | `xsd:decimal` | true | 0..1 |
| `PERIMETR_M` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:REGIONAL_OBRA_MB`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_REG` | `xsd:decimal` | false | 1..1 |
| `COD_REG` | `xsd:decimal` | false | 1..1 |
| `SIGLA` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | false | 1..1 |
| `AREA_KM2` | `xsd:decimal` | true | 0..1 |
| `PERIMETR_M` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:REGIONAL_OBRA_TEMATICO_MB`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_REG` | `xsd:decimal` | false | 1..1 |
| `COD_REG` | `xsd:decimal` | false | 1..1 |
| `SIGLA` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | false | 1..1 |
| `AREA_KM2` | `xsd:decimal` | true | 0..1 |
| `PERIMETR_M` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:REPARACAO_MANUTENCAO_EQUIPAMENTOS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ATVECON` | `xsd:decimal` | false | 1..1 |
| `CNAE_PRINCIPAL` | `xsd:string` | true | 0..1 |
| `DESCRICAO_CNAE` | `xsd:string` | true | 0..1 |
| `CNAE` | `xsd:string` | true | 0..1 |
| `NATUREZA_JURIDICA` | `xsd:string` | true | 0..1 |
| `PORTE_EMPRESA` | `xsd:string` | true | 0..1 |
| `AREA_UTILIZADA` | `xsd:string` | true | 0..1 |
| `IND_SIMPLES` | `xsd:string` | true | 0..1 |
| `IND_MEI` | `xsd:string` | true | 0..1 |
| `TIPO_UNIDADE` | `xsd:string` | true | 0..1 |
| `FORMA_ATUACAO` | `xsd:string` | true | 0..1 |
| `DESC_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `NOME_FANTASIA` | `xsd:string` | true | 0..1 |
| `CNPJ` | `xsd:string` | true | 0..1 |
| `DATA_INICIO_ATIVIDADE` | `xsd:string` | true | 0..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |
| `INSCRICAO_MUNICIPAL` | `xsd:string` | true | 0..1 |
| `IND_POSSUI_ALVARA` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:REPRESA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_RPSA` | `xsd:decimal` | false | 1..1 |
| `CODIGO_FLORESTAL` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:RESTAURANTE_POPULAR`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIP_SEG_ALIM_NUTRI` | `xsd:decimal` | false | 1..1 |
| `NOME_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `REFERENCIA` | `xsd:string` | true | 0..1 |
| `DIA_HORARIO` | `xsd:string` | true | 0..1 |
| `CONTATO` | `xsd:string` | true | 0..1 |
| `INFORMACOES_ADICIONAIS` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `NUMERO_BARRACAS` | `xsd:decimal` | true | 0..1 |
| `PRODUTOS_COMERCIALIZADOS` | `xsd:string` | true | 0..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:RESTAURANTES_E_SIMILARES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ATVECON` | `xsd:decimal` | false | 1..1 |
| `CNAE_PRINCIPAL` | `xsd:string` | true | 0..1 |
| `DESCRICAO_CNAE` | `xsd:string` | true | 0..1 |
| `CNAE` | `xsd:string` | true | 0..1 |
| `NATUREZA_JURIDICA` | `xsd:string` | true | 0..1 |
| `PORTE_EMPRESA` | `xsd:string` | true | 0..1 |
| `AREA_UTILIZADA` | `xsd:string` | true | 0..1 |
| `IND_SIMPLES` | `xsd:string` | true | 0..1 |
| `IND_MEI` | `xsd:string` | true | 0..1 |
| `TIPO_UNIDADE` | `xsd:string` | true | 0..1 |
| `FORMA_ATUACAO` | `xsd:string` | true | 0..1 |
| `DESC_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `NOME_FANTASIA` | `xsd:string` | true | 0..1 |
| `CNPJ` | `xsd:string` | true | 0..1 |
| `DATA_INICIO_ATIVIDADE` | `xsd:string` | true | 0..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |
| `INSCRICAO_MUNICIPAL` | `xsd:string` | true | 0..1 |
| `IND_POSSUI_ALVARA` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:RESTRICAO_VOO_DRONE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_RESTRICAO_VOO_DRONE` | `xsd:decimal` | false | 1..1 |
| `DESC_RESTRICAO_VOO` | `xsd:string` | true | 0..1 |
| `ALTURA_LIMITE_VOO` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `COD_RESTRICAO_VOO` | `xsd:decimal` | true | 0..1 |

### `ide_bhgeo:ROTA_CICLOVIARIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ROTA_CICLOVIARIA` | `xsd:decimal` | false | 1..1 |
| `ID_TRECHO` | `xsd:decimal` | true | 0..1 |
| `NOME_LOGRAD` | `xsd:string` | true | 0..1 |
| `ANO_MES_IMPLANTACAO` | `xsd:string` | true | 0..1 |
| `TIPO_ROTA_CICLOVIARIA` | `xsd:string` | true | 0..1 |
| `POSICIONAMENTO` | `xsd:string` | true | 0..1 |
| `EXTENSAO_CICLOVIA` | `xsd:double` | true | 0..1 |
| `SITUACAO_ROTA` | `xsd:string` | true | 0..1 |
| `SENTIDO_CIRCULACAO` | `xsd:string` | true | 0..1 |
| `LARGURA_MIN` | `xsd:decimal` | true | 0..1 |
| `TIPO_SEGREGADOR` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:ROTULO_LOGRADOURO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_LOGRADOURO` | `xsd:decimal` | false | 1..1 |
| `COD_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `NOME_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `LARGURA_MEDIA` | `xsd:decimal` | true | 0..1 |
| `COMPRIMENTO_LOGRADOURO` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:SAUDE_MENTAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQ_SAUDE` | `xsd:decimal` | false | 1..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `SIGLA_CATEGORIA` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `LOGRADOURO` | `xsd:string` | false | 1..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | false | 1..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:SEDE_REGIONAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_REFERENCIA_LOCALIZACAO` | `xsd:decimal` | false | 1..1 |
| `NOME_REFERENCIA_LOCALIZACAO` | `xsd:string` | false | 1..1 |
| `ID_CATEGORIA_REFERENCIA_LOC` | `xsd:decimal` | false | 1..1 |
| `TIPO_REFERENCIA_LOCALIZACAO` | `xsd:string` | false | 1..1 |
| `ID_ENDERECO_PBH` | `xsd:decimal` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `CONTATO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:SEDE_REGIONAL_VELHA`

> [!warning] Schema pendente
> Este esquema ainda não foi resolvido nesta coleta. Reconsulte o endpoint antes de usar a camada.


### `ide_bhgeo:SERVICOS_DISTRITAIS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQ_SAUDE` | `xsd:decimal` | false | 1..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `SIGLA_CATEGORIA` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `LOGRADOURO` | `xsd:string` | false | 1..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | false | 1..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:SERVICOS_TECNOLOGIA_INFORMACAO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ATVECON` | `xsd:decimal` | false | 1..1 |
| `CNAE_PRINCIPAL` | `xsd:string` | true | 0..1 |
| `DESCRICAO_CNAE` | `xsd:string` | true | 0..1 |
| `CNAE` | `xsd:string` | true | 0..1 |
| `NATUREZA_JURIDICA` | `xsd:string` | true | 0..1 |
| `PORTE_EMPRESA` | `xsd:string` | true | 0..1 |
| `AREA_UTILIZADA` | `xsd:string` | true | 0..1 |
| `IND_SIMPLES` | `xsd:string` | true | 0..1 |
| `IND_MEI` | `xsd:string` | true | 0..1 |
| `TIPO_UNIDADE` | `xsd:string` | true | 0..1 |
| `FORMA_ATUACAO` | `xsd:string` | true | 0..1 |
| `DESC_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:string` | true | 0..1 |
| `COMPLEMENTO` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `NOME_FANTASIA` | `xsd:string` | true | 0..1 |
| `CNPJ` | `xsd:string` | true | 0..1 |
| `DATA_INICIO_ATIVIDADE` | `xsd:string` | true | 0..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |
| `INSCRICAO_MUNICIPAL` | `xsd:string` | true | 0..1 |
| `IND_POSSUI_ALVARA` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:SETOR_CENSITARIO_2010`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_CS_2010` | `xsd:decimal` | false | 1..1 |
| `COD_GEOCODI` | `xsd:string` | false | 1..1 |
| `QT_PESSOAS_RES_DOMC` | `xsd:decimal` | true | 0..1 |
| `QT_POP_FEM` | `xsd:decimal` | true | 0..1 |
| `QT_POP_MASC` | `xsd:decimal` | true | 0..1 |
| `QT_POP_0_4` | `xsd:decimal` | true | 0..1 |
| `QT_POP_5_9` | `xsd:decimal` | true | 0..1 |
| `QT_POP_10_14` | `xsd:decimal` | true | 0..1 |
| `QT_POP_15_19` | `xsd:decimal` | true | 0..1 |
| `QT_POP_20_24` | `xsd:decimal` | true | 0..1 |
| `QT_POP_25_29` | `xsd:decimal` | true | 0..1 |
| `QT_POP_30_34` | `xsd:decimal` | true | 0..1 |
| `QT_POP_35_39` | `xsd:decimal` | true | 0..1 |
| `QT_POP_40_44` | `xsd:decimal` | true | 0..1 |
| `QT_POP_45_49` | `xsd:decimal` | true | 0..1 |
| `QT_POP_50_54` | `xsd:decimal` | true | 0..1 |
| `QT_POP_55_59` | `xsd:decimal` | true | 0..1 |
| `QT_POP_60_64` | `xsd:decimal` | true | 0..1 |
| `QT_POP_65_69` | `xsd:decimal` | true | 0..1 |
| `QT_POP_70_74` | `xsd:decimal` | true | 0..1 |
| `QT_POP_75_79` | `xsd:decimal` | true | 0..1 |
| `QT_POP_80_MAIS` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:SETOR_CENSITARIO_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_SETOR_CENSITARIO_2022` | `xsd:decimal` | false | 1..1 |
| `COD_SETOR` | `xsd:string` | true | 0..1 |
| `TIPO_SITUACAO_DENS_OCUPACAO` | `xsd:string` | true | 0..1 |
| `NOME_SUBDISTRITO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `REGIONAL_CONSIDERADA_SETOR` | `xsd:string` | true | 0..1 |
| `TGC_CONSIDERADA_SETOR` | `xsd:string` | true | 0..1 |
| `BAIRRO_CONSIDERADO_SETOR` | `xsd:string` | true | 0..1 |
| `QT_TOT_PESSOAS_RES_DOMC` | `xsd:decimal` | true | 0..1 |
| `QT_TOT_DOMC_OCUP` | `xsd:decimal` | true | 0..1 |

### `ide_bhgeo:SINALIZACAO_SEMAFORICA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_SINALIZACAO_SEMAFORICA` | `xsd:decimal` | false | 1..1 |
| `COD_SINALIZACAO_SEMAFORICA` | `xsd:string` | false | 1..1 |
| `NOME` | `xsd:string` | false | 1..1 |
| `TP_TRAVESSIA_PEDESTRE` | `xsd:string` | true | 0..1 |
| `BOTOEIRA` | `xsd:string` | true | 0..1 |
| `BOTOEIRA_SONORA` | `xsd:string` | true | 0..1 |
| `LACO_DETECTOR_VEICULAR` | `xsd:string` | true | 0..1 |
| `QTD_TR_C_FOCO` | `xsd:decimal` | false | 1..1 |
| `QTD_TR_S_FOCO` | `xsd:decimal` | false | 1..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | false | 1..1 |

### `ide_bhgeo:SONDAGEM_GEOTECNICA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_SONDAGEM_GEOTECNICA` | `xsd:decimal` | false | 1..1 |
| `COD_RELATORIO` | `xsd:string` | false | 1..1 |
| `NOME_EMPREENDIMENTO` | `xsd:string` | false | 1..1 |
| `CODIGO_FURO_SONDAGEM` | `xsd:string` | false | 1..1 |
| `TIPO_FURO_SONDAGEM` | `xsd:string` | true | 0..1 |
| `CAMPANHA` | `xsd:string` | true | 0..1 |
| `RELATORIO_SONDAGEM` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | false | 1..1 |

### `ide_bhgeo:SUBBACIA_HIDROGRAFICA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_SUBBAC` | `xsd:decimal` | false | 1..1 |
| `SUBBACIA` | `xsd:string` | true | 0..1 |
| `COD_BACIA` | `xsd:string` | true | 0..1 |
| `NOME_BACIA` | `xsd:string` | true | 0..1 |
| `AREA_M2` | `xsd:decimal` | true | 0..1 |
| `PERIMETRO_M` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:SUBESTACAO_ENERGIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_SUBESTACAO` | `xsd:decimal` | false | 1..1 |
| `GEOMETRIA` | `gml:SurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:SUBESTACAO_ENERGIA_MB`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_SUBESTACAO` | `xsd:decimal` | false | 1..1 |
| `GEOMETRIA` | `gml:SurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:SUBESTACOES_REFERENCIA_LOCALIZACAO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_REFERENCIA_LOCALIZACAO` | `xsd:decimal` | false | 1..1 |
| `NOME_REFERENCIA_LOCALIZACAO` | `xsd:string` | false | 1..1 |
| `ID_CATEGORIA_REFERENCIA_LOC` | `xsd:decimal` | false | 1..1 |
| `TIPO_REFERENCIA_LOCALIZACAO` | `xsd:string` | false | 1..1 |
| `ID_ENDERECO_PBH` | `xsd:decimal` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO` | `xsd:decimal` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `CONTATO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:TAXA_PERMEABILIDADE_11181`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_PERMEABILIDADE_SOLO` | `xsd:decimal` | false | 1..1 |
| `TAXA_PERMEABILIDADE` | `xsd:decimal` | true | 0..1 |
| `MENSAGEM_PERM` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:TERRITORIO_CRAS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_TERRITORIO_PROTECAO` | `xsd:decimal` | false | 1..1 |
| `TIPO_TERRITORIO` | `xsd:string` | true | 0..1 |
| `NOME_TERRITORIO_PROTECAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:TERRITORIO_FISCALIZACAO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_TFIS` | `xsd:decimal` | false | 1..1 |
| `SIGLA_TFIS` | `xsd:string` | true | 0..1 |
| `DESCRICAO_TFIS` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:TERRITORIO_GESTAO_COMPART`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_TGC` | `xsd:decimal` | false | 1..1 |
| `IDENT_TERRITORIO_GEST_COMPART` | `xsd:string` | false | 1..1 |
| `DESC_TERRITORIO_GEST_COMPART` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:TERRITORIO_PROTECAO_SOCIOASSISTENCIAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_TERRITORIO_PROTECAO` | `xsd:decimal` | false | 1..1 |
| `TIPO_TERRITORIO` | `xsd:string` | true | 0..1 |
| `NOME_TERRITORIO_PROTECAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:TIPOLOGIA_USO_OCUPACAO_LOTE_2011`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_TP_USO_OCP` | `xsd:decimal` | false | 1..1 |
| `NULOTCTM` | `xsd:string` | true | 0..1 |
| `TIPOLOGIA_USO` | `xsd:string` | true | 0..1 |
| `TIPOLOGIA_OCUPACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:TIPOLOGIA_USO_OCUPACAO_LOTE_2017`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_TP_USO_OCP` | `xsd:decimal` | false | 1..1 |
| `NULOTCTM` | `xsd:string` | true | 0..1 |
| `TIPOLOGIA_USO` | `xsd:string` | true | 0..1 |
| `TIPOLOGIA_OCUPACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:TIPOLOGIA_USO_OCUPACAO_LOTE_2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_TP_USO_OCP` | `xsd:decimal` | false | 1..1 |
| `NULOTCTM` | `xsd:string` | true | 0..1 |
| `TIPOLOGIA_USO` | `xsd:string` | true | 0..1 |
| `TIPOLOGIA_OCUPACAO` | `xsd:string` | true | 0..1 |
| `MORFOLOGIA` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:TIPOLOGIA_USO_OCUPACAO_LOTE_2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_TP_USO_OCP` | `xsd:decimal` | false | 1..1 |
| `NULOTCTM` | `xsd:string` | true | 0..1 |
| `TIPOLOGIA_USO` | `xsd:string` | true | 0..1 |
| `TIPOLOGIA_OCUPACAO` | `xsd:string` | true | 0..1 |
| `MORFOLOGIA` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:TIPOLOGIA_USO_OCUPACAO_LOTE_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_TP_USO_OCP` | `xsd:decimal` | false | 1..1 |
| `NULOTCTM` | `xsd:string` | true | 0..1 |
| `TIPOLOGIA_USO` | `xsd:string` | true | 0..1 |
| `TIPOLOGIA_OCUPACAO` | `xsd:string` | true | 0..1 |
| `MORFOLOGIA` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:TORRE_TRANSMISSAO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_TORRE_TRANSMISSAO` | `xsd:decimal` | false | 1..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:TRECHO_CIRC_VIARIA_DESTAQUE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_TRECHO_CIRC_VIARIA_DESTAQUE` | `xsd:decimal` | false | 1..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `NOME_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `CODIGO` | `xsd:decimal` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:TRECHO_LOGRADOURO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_TRECHO_LOGRADOURO` | `xsd:decimal` | false | 1..1 |
| `ID_BASE_TRECHO` | `xsd:decimal` | false | 1..1 |
| `ID_LOGRADOURO` | `xsd:decimal` | false | 1..1 |
| `SIGLA_TIPO_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `DESC_SIGLA_TIPO_LOGRAD` | `xsd:string` | false | 1..1 |
| `NOME_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `COMPRIMENTO` | `xsd:decimal` | true | 0..1 |
| `LARGURA` | `xsd:double` | false | 1..1 |
| `SITUACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ide_bhgeo:TREVO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_TRV` | `xsd:decimal` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:TREVO_MB`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_TRV` | `xsd:decimal` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:UNID_CONSERV_AMBIENTAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_UCA` | `xsd:decimal` | false | 1..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `DESC_CATEGORIA` | `xsd:string` | true | 0..1 |
| `COMPETENCIA` | `xsd:string` | false | 1..1 |
| `NOME` | `xsd:string` | false | 1..1 |
| `TIPO_USO` | `xsd:string` | true | 0..1 |
| `LEGISLACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:UNID_PLANEJAMENTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_UNID_PLANEJAMENTO` | `xsd:decimal` | false | 1..1 |
| `COD_UNID_PLANEJAMENTO` | `xsd:decimal` | false | 1..1 |
| `NOME_UNID_PLANEJAMENTO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:UNIDADE_ILUMINACAO_PUBLICA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_UNIDADE_ILUMINACAO_PUBLICA` | `xsd:decimal` | false | 1..1 |
| `NUMERO_IDENTIFICACAO` | `xsd:string` | true | 0..1 |
| `ILUMINACAO_DESTAQUE` | `xsd:string` | true | 0..1 |
| `OBJETO_ILUMINADO` | `xsd:string` | true | 0..1 |
| `PONTO_MODERNIZADO_LED` | `xsd:string` | true | 0..1 |
| `TELEGESTAO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `REGIONAL` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:UNIDADE_PRODUTIVA_COLETIVA_COMUNITARIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIP_SEG_ALIM_NUTRI_UPCC` | `xsd:decimal` | false | 1..1 |
| `NOME_EQUIPAMENTO` | `xsd:string` | false | 1..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `COMPOSTAGEM` | `xsd:string` | false | 1..1 |
| `COMERCIALIZACAO` | `xsd:string` | false | 1..1 |
| `ANO_CADASTRO` | `xsd:decimal` | false | 1..1 |
| `TIPO_PRODUCAO` | `xsd:string` | true | 0..1 |
| `CONTATO` | `xsd:string` | true | 0..1 |
| `QTDE_AGRICULTOR` | `xsd:decimal` | true | 0..1 |
| `DATA_ATUALIZACAO_CADASTRO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:UNIDADE_PRODUTIVA_INSTITUCIONAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIP_SEG_ALIM_NUTRI` | `xsd:decimal` | false | 1..1 |
| `NOME_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `REFERENCIA` | `xsd:string` | true | 0..1 |
| `DIA_HORARIO` | `xsd:string` | true | 0..1 |
| `CONTATO` | `xsd:string` | true | 0..1 |
| `INFORMACOES_ADICIONAIS` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `NUMERO_BARRACAS` | `xsd:decimal` | true | 0..1 |
| `PRODUTOS_COMERCIALIZADOS` | `xsd:string` | true | 0..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:UNIDADE_PRODUTIVA_INSTITUCIONAL_ESCOLAR`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIP_SEG_ALIM_NUTRI` | `xsd:decimal` | false | 1..1 |
| `NOME_EQUIPAMENTO` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NOME_LOGRADOURO` | `xsd:string` | true | 0..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | true | 0..1 |
| `BAIRRO` | `xsd:string` | true | 0..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `TIPO` | `xsd:string` | true | 0..1 |
| `REFERENCIA` | `xsd:string` | true | 0..1 |
| `DIA_HORARIO` | `xsd:string` | true | 0..1 |
| `CONTATO` | `xsd:string` | true | 0..1 |
| `INFORMACOES_ADICIONAIS` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
| `NUMERO_BARRACAS` | `xsd:decimal` | true | 0..1 |
| `PRODUTOS_COMERCIALIZADOS` | `xsd:string` | true | 0..1 |
| `NOME_REGIONAL` | `xsd:string` | true | 0..1 |

### `ide_bhgeo:UNIDADE_PRONTO_ATENDIMENTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQ_SAUDE` | `xsd:decimal` | false | 1..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `SIGLA_CATEGORIA` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `LOGRADOURO` | `xsd:string` | false | 1..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | false | 1..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:URPV`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_URPV` | `xsd:decimal` | false | 1..1 |
| `NOME_URPV` | `xsd:string` | false | 1..1 |
| `TIPO_MATERIAL_COLETADO` | `xsd:string` | true | 0..1 |
| `HORARIO_FUNCIONAMENTO` | `xsd:string` | false | 1..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `NOME_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | false | 1..1 |
| `LETRA_IMOVEL` | `xsd:string` | true | 0..1 |
| `BAIRRO` | `xsd:string` | false | 1..1 |
| `REGIONAL` | `xsd:string` | false | 1..1 |
| `REF_LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `ENDERECO_ELETRONICO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | false | 1..1 |

### `ide_bhgeo:USUARIOS_DIA_UTIL_DESTINO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_MATRIZ_OD_DESTINO` | `xsd:decimal` | false | 1..1 |
| `COD_HEX_H3` | `xsd:string` | true | 0..1 |
| `DOMINGO_TIPICO` | `xsd:decimal` | true | 0..1 |
| `SABADO_TIPICO` | `xsd:decimal` | true | 0..1 |
| `DIA_UTIL_TIPICO` | `xsd:decimal` | true | 0..1 |
| `DATA_REFERENCIA` | `xsd:string` | true | 0..1 |
| `DATA_ATUALIZACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:USUARIOS_DIA_UTIL_ORIGEM`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_MATRIZ_OD_ORIGEM` | `xsd:decimal` | false | 1..1 |
| `COD_HEX_H3` | `xsd:string` | true | 0..1 |
| `DOMINGO_TIPICO` | `xsd:decimal` | true | 0..1 |
| `SABADO_TIPICO` | `xsd:decimal` | true | 0..1 |
| `DIA_UTIL_TIPICO` | `xsd:decimal` | true | 0..1 |
| `DATA_REFERENCIA` | `xsd:string` | true | 0..1 |
| `DATA_ATUALIZACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:USUARIOS_DOMINGO_DESTINO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_MATRIZ_OD_DESTINO` | `xsd:decimal` | false | 1..1 |
| `COD_HEX_H3` | `xsd:string` | true | 0..1 |
| `DOMINGO_TIPICO` | `xsd:decimal` | true | 0..1 |
| `SABADO_TIPICO` | `xsd:decimal` | true | 0..1 |
| `DIA_UTIL_TIPICO` | `xsd:decimal` | true | 0..1 |
| `DATA_REFERENCIA` | `xsd:string` | true | 0..1 |
| `DATA_ATUALIZACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:USUARIOS_DOMINGO_ORIGEM`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_MATRIZ_OD_ORIGEM` | `xsd:decimal` | false | 1..1 |
| `COD_HEX_H3` | `xsd:string` | true | 0..1 |
| `DOMINGO_TIPICO` | `xsd:decimal` | true | 0..1 |
| `SABADO_TIPICO` | `xsd:decimal` | true | 0..1 |
| `DIA_UTIL_TIPICO` | `xsd:decimal` | true | 0..1 |
| `DATA_REFERENCIA` | `xsd:string` | true | 0..1 |
| `DATA_ATUALIZACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:USUARIOS_SABADO_DESTINO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_MATRIZ_OD_DESTINO` | `xsd:decimal` | false | 1..1 |
| `COD_HEX_H3` | `xsd:string` | true | 0..1 |
| `DOMINGO_TIPICO` | `xsd:decimal` | true | 0..1 |
| `SABADO_TIPICO` | `xsd:decimal` | true | 0..1 |
| `DIA_UTIL_TIPICO` | `xsd:decimal` | true | 0..1 |
| `DATA_REFERENCIA` | `xsd:string` | true | 0..1 |
| `DATA_ATUALIZACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:USUARIOS_SABADO_ORIGEM`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_MATRIZ_OD_ORIGEM` | `xsd:decimal` | false | 1..1 |
| `COD_HEX_H3` | `xsd:string` | true | 0..1 |
| `DOMINGO_TIPICO` | `xsd:decimal` | true | 0..1 |
| `SABADO_TIPICO` | `xsd:decimal` | true | 0..1 |
| `DIA_UTIL_TIPICO` | `xsd:decimal` | true | 0..1 |
| `DATA_REFERENCIA` | `xsd:string` | true | 0..1 |
| `DATA_ATUALIZACAO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:VARANDA_URBANA_PARKLET`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_PARKLET_VARANDA_URBANA` | `xsd:decimal` | false | 1..1 |
| `TERMO_COOPERACAO` | `xsd:decimal` | false | 1..1 |
| `PROTOCOLO_BH_DIGITAL` | `xsd:string` | false | 1..1 |
| `MANTENEDOR_PARKLET` | `xsd:string` | false | 1..1 |
| `IND_BAR_RESTAURANTE` | `xsd:string` | false | 1..1 |
| `DT_SOLIC_ANALISE_LOCALIZACAO` | `xsd:date` | true | 0..1 |
| `DT_CONCL_ANALISE_LOCALIZACAO` | `xsd:date` | true | 0..1 |
| `SITUACAO_ANALISE_LOCALIZACAO` | `xsd:string` | false | 1..1 |
| `SITUACAO_ANALISE_PROJETO` | `xsd:string` | false | 1..1 |
| `DT_EMISSAO_TERMO_PROVISORIO` | `xsd:date` | true | 0..1 |
| `DT_EMISSAO_TERMO_DEFINITIVO` | `xsd:date` | true | 0..1 |
| `SITUACAO_SOLICIT_TERMO_COOP` | `xsd:string` | false | 1..1 |
| `SITUACAO_IMPLANTACAO_PARKLET` | `xsd:string` | false | 1..1 |
| `SITUACAO_MATERIAL_RENOVACAO` | `xsd:string` | false | 1..1 |
| `SITUACAO_TERMO_COOPERACAO` | `xsd:string` | false | 1..1 |
| `DT_RENOVACAO_TERMO_DEFINITIVO` | `xsd:date` | true | 0..1 |
| `DT_PROX_RENOV_TERMO_DEFINITIVO` | `xsd:date` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `LOGRADOURO` | `xsd:string` | false | 1..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | false | 1..1 |
| `BAIRRO` | `xsd:string` | false | 1..1 |
| `COMPRIMENTO_PARKLET` | `xsd:decimal` | true | 0..1 |
| `LARGURA_PARKLET` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:VIA_CEMITERIO_PUBLICO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_LOGRADOURO_CEMITERIO` | `xsd:decimal` | false | 1..1 |
| `NOME_LOGRADOURO_CEMITERIO` | `xsd:string` | true | 0..1 |
| `NOME_CEMITERIO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiGeometryPropertyType` | true | 0..1 |

### `ide_bhgeo:VILA_FAVELA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_VILA_FAVELA` | `xsd:decimal` | false | 1..1 |
| `NOME_LOCALIDADE` | `xsd:string` | false | 1..1 |
| `APELIDO_LOCALIDADE` | `xsd:string` | true | 0..1 |
| `DESC_LOCALIDADE` | `xsd:string` | false | 1..1 |
| `QTDE_DOMICILIO` | `xsd:decimal` | false | 1..1 |
| `FONTE_DOMICILIO` | `xsd:string` | false | 1..1 |
| `DATA_QTDE_DOMICILIO` | `xsd:string` | true | 0..1 |
| `QTDE_ESTABELECIMENTO` | `xsd:decimal` | true | 0..1 |
| `FONTE_ESTABELECIMENTO` | `xsd:string` | false | 1..1 |
| `DATA_QTDE_ESTABELECIMENTO` | `xsd:string` | true | 0..1 |
| `QTDE_POPULACAO_EXISTENTE` | `xsd:decimal` | false | 1..1 |
| `FONTE_POPULACAO_EXISTENTE` | `xsd:string` | false | 1..1 |
| `DATA_INFO_POP_EXISTENTE` | `xsd:string` | true | 0..1 |
| `PLANO_URBANISTICO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:VIST_OBRA_LOGRAD_LICEN`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_VIST_OBRA_LOGRAD_LICEN` | `xsd:decimal` | false | 1..1 |
| `DATA_VISTORIA` | `xsd:string` | true | 0..1 |
| `IND_REVESTIMENTO_PASSEIO` | `xsd:string` | true | 0..1 |
| `IND_PAVIMENTACAO` | `xsd:string` | true | 0..1 |
| `NOME_VISTORIADOR` | `xsd:string` | true | 0..1 |
| `OBSERVACAO` | `xsd:string` | true | 0..1 |
| `TIPO_VISTORIA` | `xsd:string` | true | 0..1 |
| `ALVARA` | `xsd:string` | true | 0..1 |
| `DESCRICAO_IRREGULARIDADE` | `xsd:string` | true | 0..1 |
| `TIPO_REVESTIMENTO_PASSEIO` | `xsd:string` | true | 0..1 |
| `TIPO_REVESTIMENTO_VIA` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:WIFI_HIPERCENTRO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQUIP_HOTSPOT` | `xsd:decimal` | false | 1..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `LOCALIZACAO` | `xsd:string` | true | 0..1 |
| `CODIGO_PROJETO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |

### `ide_bhgeo:ZON_GEOTECNICO_COMPL_LITOGENET`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ZON_GEOTECNICO_COMPL_LITOG` | `xsd:decimal` | false | 1..1 |
| `NUM_COMPLEXO_LITOGENETICO` | `xsd:decimal` | true | 0..1 |
| `SIGLA_COMPLEXO_LITOGENETICO` | `xsd:string` | true | 0..1 |
| `DESC_COMPLEXO_LITOGENETICO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:ZON_GEOTECNICO_PL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ZON_GEOTECNICO_PL` | `xsd:decimal` | false | 1..1 |
| `NUM_COMPLEXO_LITOGENETICO` | `xsd:decimal` | true | 0..1 |
| `SIGLA_COMPLEXO_LITOGENETICO` | `xsd:string` | true | 0..1 |
| `DESC_COMPLEXO_LITOGENETICO` | `xsd:string` | true | 0..1 |
| `NUM_ZONA_LITOLOGICA` | `xsd:decimal` | true | 0..1 |
| `SIGLA_ZONA_LITOLOGICA` | `xsd:string` | true | 0..1 |
| `DESC_ZONA_LITOLOGICA` | `xsd:string` | true | 0..1 |
| `NUM_ZONA_GEOTECNICA` | `xsd:decimal` | true | 0..1 |
| `SIGLA_ZONA_GEOTECNICA` | `xsd:string` | true | 0..1 |
| `DESC_ZONA_GEOTECNICA` | `xsd:string` | true | 0..1 |
| `PREV_COMPORTAMENTO_FUNDACOES` | `xsd:string` | true | 0..1 |
| `PREV_COMPORTAMENTO_TALUDES` | `xsd:string` | true | 0..1 |
| `PREV_COMPORT_TRABALHABILIDADE` | `xsd:string` | true | 0..1 |
| `PREV_COMPORT_OBS_COMPLEMENT` | `xsd:string` | true | 0..1 |
| `URL_CROQUIS_ZONA_GEOTECNICA` | `xsd:string` | true | 0..1 |
| `NOME_IMAGEM_CROQUIS_ZONA_GEOT` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:ZON_GEOTECNICO_PT`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ZON_GEOTECNICO_PT` | `xsd:decimal` | false | 1..1 |
| `NUM_COMPLEXO_LITOGENETICO` | `xsd:decimal` | true | 0..1 |
| `SIGLA_COMPLEXO_LITOGENETICO` | `xsd:string` | true | 0..1 |
| `DESC_COMPLEXO_LITOGENETICO` | `xsd:string` | true | 0..1 |
| `NUM_ZONA_LITOLOGICA` | `xsd:decimal` | true | 0..1 |
| `SIGLA_ZONA_LITOLOGICA` | `xsd:string` | true | 0..1 |
| `DESC_ZONA_LITOLOGICA` | `xsd:string` | true | 0..1 |
| `NUM_ZONA_GEOTECNICA` | `xsd:decimal` | true | 0..1 |
| `SIGLA_ZONA_GEOTECNICA` | `xsd:string` | true | 0..1 |
| `DESC_ZONA_GEOTECNICA` | `xsd:string` | true | 0..1 |
| `PREV_COMPORTAMENTO_FUNDACOES` | `xsd:string` | true | 0..1 |
| `PREV_COMPORTAMENTO_TALUDES` | `xsd:string` | true | 0..1 |
| `PREV_COMPORT_TRABALHABILIDADE` | `xsd:string` | true | 0..1 |
| `PREV_COMPORT_OBS_COMPLEMENT` | `xsd:string` | true | 0..1 |
| `URL_CROQUIS_ZONA_GEOTECNICA` | `xsd:string` | true | 0..1 |
| `NOME_IMAGEM_CROQUIS_ZONA_GEOT` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiPointPropertyType` | true | 0..1 |

### `ide_bhgeo:ZON_GEOTECNICO_ZONA_LITOLOGICA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ZON_GEOTECNICO_ZONA_LITOLOG` | `xsd:decimal` | false | 1..1 |
| `NUM_COMPLEXO_LITOGENETICO` | `xsd:decimal` | true | 0..1 |
| `SIGLA_COMPLEXO_LITOGENETICO` | `xsd:string` | true | 0..1 |
| `DESC_COMPLEXO_LITOGENETICO` | `xsd:string` | true | 0..1 |
| `NUM_ZONA_LITOLOGICA` | `xsd:decimal` | true | 0..1 |
| `SIGLA_ZONA_LITOLOGICA` | `xsd:string` | true | 0..1 |
| `DESC_ZONA_LITOLOGICA` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:ZONA_CULTURAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ZONA_CULTURAL` | `xsd:decimal` | false | 1..1 |
| `NOME_ZONA_CULTURAL` | `xsd:string` | true | 0..1 |
| `NUM_DECRETO_CRIACAO` | `xsd:string` | true | 0..1 |
| `NUM_DECRETO_ATUALIZACAO` | `xsd:string` | true | 0..1 |
| `AREA_KM2` | `xsd:decimal` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:ZONA_HOMOGENEA_IPTU`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ZONA_HOMOGENEA` | `xsd:decimal` | false | 1..1 |
| `CODIGO_ZH` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:ZONA_RUIDO_AERONAUTICA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ZONA_RUIDO_AERO` | `xsd:decimal` | false | 1..1 |
| `DESCRICAO_ZONA_RUIDO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | false | 1..1 |

### `ide_bhgeo:ZONEAMENTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ZT` | `xsd:decimal` | false | 1..1 |
| `SIGLA_ZONEAMENTO` | `xsd:string` | true | 0..1 |
| `DESC_ZONEAMENTO` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:ZONEAMENTO_11181`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_ZONEAMENTO` | `xsd:decimal` | false | 1..1 |
| `DESC_TIPO_ZONEAMENTO` | `xsd:string` | false | 1..1 |
| `SIGLA_TIPO_ZONEAMENTO` | `xsd:string` | false | 1..1 |
| `GEOMETRIA` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ide_bhgeo:ZOONOSES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_EQ_SAUDE` | `xsd:decimal` | false | 1..1 |
| `CATEGORIA` | `xsd:string` | true | 0..1 |
| `SIGLA_CATEGORIA` | `xsd:string` | true | 0..1 |
| `NOME` | `xsd:string` | true | 0..1 |
| `TIPO_LOGRADOURO` | `xsd:string` | false | 1..1 |
| `LOGRADOURO` | `xsd:string` | false | 1..1 |
| `NUMERO_IMOVEL` | `xsd:decimal` | false | 1..1 |
| `TELEFONE` | `xsd:string` | true | 0..1 |
| `NOME_BAIRRO_POPULAR` | `xsd:string` | true | 0..1 |
| `GEOMETRIA` | `gml:PointPropertyType` | true | 0..1 |
