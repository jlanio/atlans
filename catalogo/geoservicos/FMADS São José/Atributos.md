# FMADS São José — atributos das camadas

Geoportal: [[Geosserviços/FMADS São José/Fundação Municipal do Meio Ambiente de São José — FMADS (SC)|Fundação Municipal do Meio Ambiente de São José — FMADS (SC)]]

Os campos abaixo vêm de `DescribeFeatureType` (XSD), sem download de feições.

## SCSJFMADS (3)

### `SCSJFMADS:app_cursohidrico`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `fid` | `xsd:double` | true | 0..1 |
| `objectid` | `xsd:double` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `buffer` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `SCSJFMADS:hidrografia_sds`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `fid` | `xsd:double` | true | 0..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `geometriaa` | `xsd:long` | true | 0..1 |
| `coincideco` | `xsd:long` | true | 0..1 |
| `dentrodepo` | `xsd:long` | true | 0..1 |
| `compartilh` | `xsd:long` | true | 0..1 |
| `caladomax` | `xsd:double` | true | 0..1 |
| `regime` | `xsd:long` | true | 0..1 |
| `larguramed` | `xsd:double` | true | 0..1 |
| `velocidade` | `xsd:double` | true | 0..1 |
| `profundida` | `xsd:double` | true | 0..1 |
| `nomeabrev` | `xsd:string` | true | 0..1 |
| `id_trecho_` | `xsd:long` | true | 0..1 |
| `eixoprinci` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `navegabili` | `xsd:long` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `temnome` | `xsd:long` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `SCSJFMADS:lotes_geomais`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `fid` | `xsd:double` | true | 0..1 |
| `id_lote` | `xsd:long` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `insc` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
