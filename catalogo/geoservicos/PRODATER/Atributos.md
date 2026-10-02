# PRODATER — atributos das camadas

Geoportal: [[Geosserviços/PRODATER/Empresa Teresinense de Processamento de Dados — PRODATER|Empresa Teresinense de Processamento de Dados — PRODATER]]

Os campos abaixo vêm de `DescribeFeatureType` (XSD), sem download de feições.

## PIPRODATER (13)

### `PIPRODATER:cbge_trecho_arruamento_2020_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `atolegal` | `xsd:string` | true | 0..1 |
| `length_otf` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `PIPRODATER:hid_banco_areia_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `tipobanco` | `xsd:string` | true | 0..1 |
| `situacaoem` | `xsd:string` | true | 0..1 |
| `materialpr` | `xsd:string` | true | 0..1 |
| `area_otf` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `PIPRODATER:hid_ilha_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `tipoelemna` | `xsd:string` | true | 0..1 |
| `tipoilha` | `xsd:string` | true | 0..1 |
| `area_otf` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `PIPRODATER:hid_massa_dagua_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `tipomassad` | `xsd:string` | true | 0..1 |
| `regime` | `xsd:string` | true | 0..1 |
| `salgada` | `xsd:string` | true | 0..1 |
| `dominialid` | `xsd:string` | true | 0..1 |
| `artificial` | `xsd:string` | true | 0..1 |
| `possuitrec` | `xsd:string` | true | 0..1 |
| `area_otf` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `PIPRODATER:hid_rocha_em_agua_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `tipoelemna` | `xsd:string` | true | 0..1 |
| `formarocha` | `xsd:string` | true | 0..1 |
| `situacaoem` | `xsd:string` | true | 0..1 |
| `alturalami` | `xsd:double` | true | 0..1 |
| `area_otf` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `PIPRODATER:hid_trecho_drenagem_l`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `tipotrecho` | `xsd:string` | true | 0..1 |
| `navegavel` | `xsd:string` | true | 0..1 |
| `larguramed` | `xsd:double` | true | 0..1 |
| `regime` | `xsd:string` | true | 0..1 |
| `encoberto` | `xsd:string` | true | 0..1 |
| `length_otf` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `PIPRODATER:lml_aglomerado_rural_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `geocodigo` | `xsd:string` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `PIPRODATER:lml_limite_municipio_a_2024`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `geocodigo` | `xsd:string` | true | 0..1 |
| `anoderefer` | `xsd:long` | true | 0..1 |
| `areaoficia` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `PIPRODATER:lml_localidades_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `PIPRODATER:lml_nucleo_urbano_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `atolegal` | `xsd:string` | true | 0..1 |
| `area_otf` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `PIPRODATER:lml_perimetro_urbano_teresina_a_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `atolegal` | `xsd:string` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `PIPRODATER:lml_territorios_semcaspi_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:double` | true | 0..1 |
| `territorio` | `xsd:string` | true | 0..1 |
| `macroterri` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `PIPRODATER:lml_zonas_urbanizacao_especifica_a`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `atolegal` | `xsd:string` | true | 0..1 |
| `area_otf` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
