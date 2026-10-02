# ANATEL — atributos das camadas

Geoportal: [[Geosserviços/ANATEL/Agência Nacional de Telecomunicações — ANATEL|Agência Nacional de Telecomunicações — ANATEL]]

Os campos abaixo vêm de `DescribeFeatureType` (XSD), sem download de feições.

## ANATEL (18)

### `ANATEL:anatel_anuf`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `anuf` | `xsd:string` | true | 0..1 |
| `estado` | `xsd:string` | true | 0..1 |
| `regiao` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ANATEL:municipios`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:double` | true | 0..1 |
| `cd_geocodm` | `xsd:string` | true | 0..1 |
| `nm_municip` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |

### `ANATEL:Servico248GeracaoTV`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_plano_basico` | `xsd:int` | true | 0..1 |
| `numfistel` | `xsd:string` | true | 0..1 |
| `est_geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nomefase` | `xsd:string` | true | 0..1 |
| `siglauf` | `xsd:string` | true | 0..1 |
| `nomemunicipio` | `xsd:string` | true | 0..1 |
| `nomeentidade` | `xsd:string` | true | 0..1 |
| `numservico` | `xsd:string` | true | 0..1 |
| `servico` | `xsd:string` | true | 0..1 |
| `codcanal` | `xsd:string` | true | 0..1 |
| `medlatitudedecimal` | `xsd:double` | true | 0..1 |
| `medlongitudedecimal` | `xsd:double` | true | 0..1 |
| `mederpmax` | `xsd:double` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `metadado` | `xsd:string` | true | 0..1 |

### `ANATEL:tb_localidades_anatel`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `codmunicipio` | `xsd:string` | true | 0..1 |
| `geocodmunicipio` | `xsd:string` | true | 0..1 |
| `nomemunicipio` | `xsd:string` | true | 0..1 |
| `siglauf` | `xsd:string` | true | 0..1 |
| `sedemunicipio` | `xsd:boolean` | true | 0..1 |
| `nomelocalidade` | `xsd:string` | true | 0..1 |
| `siglacnl` | `xsd:string` | true | 0..1 |
| `codigocnl` | `xsd:string` | true | 0..1 |
| `codareatarifacao` | `xsd:string` | true | 0..1 |
| `atendidostfc` | `xsd:boolean` | true | 0..1 |
| `dataatendimento` | `xsd:date` | true | 0..1 |
| `numcodigonacional` | `xsd:string` | true | 0..1 |
| `medlatitude` | `xsd:string` | true | 0..1 |
| `medlongitude` | `xsd:string` | true | 0..1 |
| `siglahemisferio` | `xsd:string` | true | 0..1 |
| `medlatitudedecimal` | `xsd:double` | true | 0..1 |
| `medlongitudedecimal` | `xsd:double` | true | 0..1 |
| `qtdpopulacao` | `xsd:int` | true | 0..1 |
| `qtdpopulacaourbana` | `xsd:int` | true | 0..1 |
| `est_geom` | `gml:PointPropertyType` | true | 0..1 |
| `dt_cadastro` | `xsd:dateTime` | false | 1..1 |

### `ANATEL:TUP`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `est_geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `id_tup` | `xsd:int` | true | 0..1 |
| `idttup` | `xsd:int` | true | 0..1 |
| `concessionaria` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `numero` | `xsd:string` | true | 0..1 |
| `dtativacao` | `xsd:string` | true | 0..1 |
| `dataultimacomunicacao` | `xsd:string` | true | 0..1 |
| `siglauf` | `xsd:string` | true | 0..1 |
| `nomemunicipio` | `xsd:string` | true | 0..1 |
| `localidade` | `xsd:string` | true | 0..1 |
| `bairro` | `xsd:string` | true | 0..1 |
| `logradouro` | `xsd:string` | true | 0..1 |
| `complemento` | `xsd:string` | true | 0..1 |
| `cep` | `xsd:string` | true | 0..1 |
| `deficientecadeirante` | `xsd:string` | true | 0..1 |
| `deficienteaudio` | `xsd:string` | true | 0..1 |
| `vintequatrohoras` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `metadado` | `xsd:string` | true | 0..1 |

### `ANATEL:vw_competicao`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nm_municip` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `hhi_dth_mmds` | `xsd:double` | true | 0..1 |
| `metadado` | `xsd:string` | true | 0..1 |

### `ANATEL:vw_competicao_scm`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nm_municip` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `ds_hhi_scm` | `xsd:double` | true | 0..1 |
| `metadado` | `xsd:string` | true | 0..1 |

### `ANATEL:vw_competicao_seac`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nm_municip` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `ds_hhi_seac` | `xsd:double` | true | 0..1 |
| `metadado` | `xsd:string` | true | 0..1 |

### `ANATEL:vw_competicao_transporte`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nm_municip` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `ds_transporte` | `xsd:int` | true | 0..1 |
| `metadado` | `xsd:string` | true | 0..1 |

### `ANATEL:vw_competicao_tvc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nm_municip` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `ds_hhi_tvc` | `xsd:double` | true | 0..1 |
| `metadado` | `xsd:string` | true | 0..1 |

### `ANATEL:vw_fm`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_plano_basico` | `xsd:int` | true | 0..1 |
| `numfistel` | `xsd:string` | true | 0..1 |
| `est_geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nomefase` | `xsd:string` | true | 0..1 |
| `siglauf` | `xsd:string` | true | 0..1 |
| `nomemunicipio` | `xsd:string` | true | 0..1 |
| `nomeentidade` | `xsd:string` | true | 0..1 |
| `numservico` | `xsd:string` | true | 0..1 |
| `codcanal` | `xsd:string` | true | 0..1 |
| `frequencia` | `xsd:double` | true | 0..1 |
| `medlatitudedecimal` | `xsd:double` | true | 0..1 |
| `medlongitudedecimal` | `xsd:double` | true | 0..1 |
| `potenciafm` | `xsd:double` | true | 0..1 |
| `classefm` | `xsd:string` | true | 0..1 |
| `metadado` | `xsd:string` | true | 0..1 |

### `ANATEL:vw_oc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_plano_basico` | `xsd:int` | true | 0..1 |
| `numfistel` | `xsd:string` | true | 0..1 |
| `est_geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nomefase` | `xsd:string` | true | 0..1 |
| `siglauf` | `xsd:string` | true | 0..1 |
| `nomemunicipio` | `xsd:string` | true | 0..1 |
| `nomeentidade` | `xsd:string` | true | 0..1 |
| `numservico` | `xsd:string` | true | 0..1 |
| `medlatitudedecimal` | `xsd:double` | true | 0..1 |
| `medlongitudedecimal` | `xsd:double` | true | 0..1 |
| `frequencia` | `xsd:double` | true | 0..1 |
| `potenciaoc` | `xsd:double` | true | 0..1 |
| `metadado` | `xsd:string` | true | 0..1 |

### `ANATEL:vw_om`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_plano_basico` | `xsd:int` | true | 0..1 |
| `numfistel` | `xsd:string` | true | 0..1 |
| `est_geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nomefase` | `xsd:string` | true | 0..1 |
| `siglauf` | `xsd:string` | true | 0..1 |
| `nomemunicipio` | `xsd:string` | true | 0..1 |
| `nomeentidade` | `xsd:string` | true | 0..1 |
| `numservico` | `xsd:string` | true | 0..1 |
| `medlatitudedecimal` | `xsd:double` | true | 0..1 |
| `medlongitudedecimal` | `xsd:double` | true | 0..1 |
| `frequencia` | `xsd:double` | true | 0..1 |
| `potenciadiurnaomot` | `xsd:double` | true | 0..1 |
| `potencianoturnaomot` | `xsd:double` | true | 0..1 |
| `classeomot` | `xsd:string` | true | 0..1 |
| `metadado` | `xsd:string` | true | 0..1 |

### `ANATEL:vw_ot`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_plano_basico` | `xsd:int` | true | 0..1 |
| `numfistel` | `xsd:string` | true | 0..1 |
| `est_geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nomefase` | `xsd:string` | true | 0..1 |
| `siglauf` | `xsd:string` | true | 0..1 |
| `nomemunicipio` | `xsd:string` | true | 0..1 |
| `nomeentidade` | `xsd:string` | true | 0..1 |
| `numservico` | `xsd:string` | true | 0..1 |
| `medlatitudedecimal` | `xsd:double` | true | 0..1 |
| `medlongitudedecimal` | `xsd:double` | true | 0..1 |
| `frequencia` | `xsd:double` | true | 0..1 |
| `potencia` | `xsd:string` | true | 0..1 |
| `classeomot` | `xsd:string` | true | 0..1 |
| `metadado` | `xsd:string` | true | 0..1 |

### `ANATEL:vw_radcom`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nm_municip` | `xsd:string` | true | 0..1 |
| `nm_uf` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `id_plano_basico` | `xsd:int` | true | 0..1 |
| `numservico` | `xsd:string` | true | 0..1 |
| `codcanal` | `xsd:string` | true | 0..1 |
| `frequencia` | `xsd:double` | true | 0..1 |
| `metadado` | `xsd:string` | true | 0..1 |

### `ANATEL:vw_rtv`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_plano_basico` | `xsd:int` | true | 0..1 |
| `numfistel` | `xsd:string` | true | 0..1 |
| `indcarater` | `xsd:string` | true | 0..1 |
| `nomecarater` | `xsd:string` | true | 0..1 |
| `est_geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nomefase` | `xsd:string` | true | 0..1 |
| `siglauf` | `xsd:string` | true | 0..1 |
| `nomemunicipio` | `xsd:string` | true | 0..1 |
| `nomeentidade` | `xsd:string` | true | 0..1 |
| `numservico` | `xsd:string` | true | 0..1 |
| `codcanal` | `xsd:string` | true | 0..1 |
| `medlatitudedecimal` | `xsd:double` | true | 0..1 |
| `medlongitudedecimal` | `xsd:double` | true | 0..1 |
| `mederpmax` | `xsd:double` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `metadado` | `xsd:string` | true | 0..1 |

### `ANATEL:vw_tva`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_plano_basico` | `xsd:int` | true | 0..1 |
| `numfistel` | `xsd:string` | true | 0..1 |
| `est_geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nomefase` | `xsd:string` | true | 0..1 |
| `siglauf` | `xsd:string` | true | 0..1 |
| `nomemunicipio` | `xsd:string` | true | 0..1 |
| `nomeentidade` | `xsd:string` | true | 0..1 |
| `numservico` | `xsd:string` | true | 0..1 |
| `codcanal` | `xsd:string` | true | 0..1 |
| `medlatitudedecimal` | `xsd:double` | true | 0..1 |
| `medlongitudedecimal` | `xsd:double` | true | 0..1 |
| `mederpmax` | `xsd:double` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `metadado` | `xsd:string` | true | 0..1 |

### `ANATEL:vw_tvd`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_plano_basico` | `xsd:int` | true | 0..1 |
| `numfistel` | `xsd:string` | true | 0..1 |
| `est_geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `nomefase` | `xsd:string` | true | 0..1 |
| `siglauf` | `xsd:string` | true | 0..1 |
| `nomemunicipio` | `xsd:string` | true | 0..1 |
| `nomeentidade` | `xsd:string` | true | 0..1 |
| `numservico` | `xsd:string` | true | 0..1 |
| `servico` | `xsd:string` | true | 0..1 |
| `codcanal` | `xsd:string` | true | 0..1 |
| `medlatitudedecimal` | `xsd:double` | true | 0..1 |
| `medlongitudedecimal` | `xsd:double` | true | 0..1 |
| `mederpmax` | `xsd:double` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `metadado` | `xsd:string` | true | 0..1 |
