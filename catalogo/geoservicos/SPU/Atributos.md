# SPU — atributos das camadas

Geoportal: [[Geosserviços/SPU/Secretaria de Patrimônio da União — SPU|Secretaria de Patrimônio da União — SPU]]

Os campos abaixo vêm de `DescribeFeatureType` (XSD), sem download de feições.

## SPU (18)

### `SPU:destinacao_aguas_publicas_jul2026_inde`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idgeometri` | `xsd:string` | true | 0..1 |
| `ripimovel` | `xsd:string` | true | 0..1 |
| `riputiliza` | `xsd:string` | true | 0..1 |
| `areaaproxi` | `xsd:double` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `geocodigo` | `xsd:long` | true | 0..1 |
| `finalidade` | `xsd:string` | true | 0..1 |
| `instrument` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:date` | true | 0..1 |
| `ano` | `xsd:long` | true | 0..1 |
| `nivelpreci` | `xsd:string` | true | 0..1 |
| `idprodutoc` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `SPU:disponibilidade_aguas_publicas_mai2026_inde_010626`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idgeometri` | `xsd:double` | true | 0..1 |
| `pa` | `xsd:string` | true | 0..1 |
| `numerocert` | `xsd:string` | true | 0..1 |
| `dataemissa` | `xsd:date` | true | 0..1 |
| `dataencerr` | `xsd:date` | true | 0..1 |
| `interessad` | `xsd:string` | true | 0..1 |
| `geocodigo` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `espelhodag` | `xsd:string` | true | 0..1 |
| `nivelpreci` | `xsd:string` | true | 0..1 |
| `idprodutoc` | `xsd:long` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `SPU:faixa_seguranca_08072026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idgeometri` | `xsd:double` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipofaixas` | `xsd:string` | true | 0..1 |
| `nivelpreci` | `xsd:string` | true | 0..1 |
| `idprodutoc` | `xsd:long` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `SPU:linha_costa_08072026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idgeometri` | `xsd:double` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `nivelpreci` | `xsd:string` | true | 0..1 |
| `idprodutoc` | `xsd:long` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `escalanume` | `xsd:string` | true | 0..1 |
| `dataultima` | `xsd:date` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `SPU:qualificageo_2026_ago_787174_rips_painel_brasil_filtro_sigilo`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:double` | true | 0..1 |
| `ripspunet` | `xsd:string` | true | 0..1 |
| `ripimovel` | `xsd:string` | true | 0..1 |
| `riputiliza` | `xsd:string` | true | 0..1 |
| `classeimov` | `xsd:string` | true | 0..1 |
| `conceituac` | `xsd:string` | true | 0..1 |
| `tipoimovel` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `bairro` | `xsd:string` | true | 0..1 |
| `endereco` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:string` | true | 0..1 |
| `longitude` | `xsd:string` | true | 0..1 |
| `nivelpreci` | `xsd:string` | true | 0..1 |
| `proprietar` | `xsd:string` | true | 0..1 |
| `datacadast` | `xsd:string` | true | 0..1 |
| `datainicio` | `xsd:string` | true | 0..1 |
| `regimeutil` | `xsd:string` | true | 0..1 |
| `areaterren` | `xsd:string` | true | 0..1 |
| `areauniaou` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `SPU:trecho_tagp_08072026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `idgeometri` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `pa` | `xsd:double` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `geocodigo` | `xsd:long` | true | 0..1 |
| `datapublic` | `xsd:string` | true | 0..1 |
| `areaaproxi` | `xsd:double` | true | 0..1 |
| `nivelpreci` | `xsd:string` | true | 0..1 |
| `idprodutoc` | `xsd:long` | true | 0..1 |
| `tipopoligo` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `SPU:vw_app_espelho_dagua_federal_a_03092026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `nivelpreci` | `xsd:string` | true | 0..1 |
| `idprodutoc` | `xsd:long` | true | 0..1 |
| `escalanume` | `xsd:string` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `areaaproxi` | `xsd:double` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `geocodigo` | `xsd:long` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `pa` | `xsd:string` | true | 0..1 |
| `tipoespelh` | `xsd:string` | true | 0..1 |
| `numerorela` | `xsd:long` | true | 0..1 |
| `datarelato` | `xsd:date` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `termoincor` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `SPU:vw_app_ilha_federal_a_03092026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `nivelpreci` | `xsd:string` | true | 0..1 |
| `idprodutoc` | `xsd:long` | true | 0..1 |
| `escalanume` | `xsd:string` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `areaaproxi` | `xsd:double` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `geocodigo` | `xsd:long` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `pa` | `xsd:string` | true | 0..1 |
| `tipoilhafe` | `xsd:string` | true | 0..1 |
| `numerorela` | `xsd:long` | true | 0..1 |
| `datarelato` | `xsd:date` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `termoincor` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `SPU:vw_app_manguezal_federal_a_03092026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `nivelpreci` | `xsd:string` | true | 0..1 |
| `idprodutoc` | `xsd:long` | true | 0..1 |
| `escalanume` | `xsd:string` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `areaaproxi` | `xsd:double` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `geocodigo` | `xsd:long` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `pa` | `xsd:string` | true | 0..1 |
| `numerorela` | `xsd:long` | true | 0..1 |
| `datarelato` | `xsd:date` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `termoincor` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `SPU:vw_app_praia_federal_a_03092026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `nivelpreci` | `xsd:string` | true | 0..1 |
| `idprodutoc` | `xsd:long` | true | 0..1 |
| `escalanume` | `xsd:string` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `areaaproxi` | `xsd:double` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `geocodigo` | `xsd:long` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `pa` | `xsd:string` | true | 0..1 |
| `tipopraiaf` | `xsd:string` | true | 0..1 |
| `numerorela` | `xsd:long` | true | 0..1 |
| `datarelato` | `xsd:date` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `termoincor` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `SPU:vw_app_trecho_terreno_acrescido_marginal_a_03092026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `nivelpreci` | `xsd:string` | true | 0..1 |
| `idprodutoc` | `xsd:long` | true | 0..1 |
| `escalanume` | `xsd:string` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `areaaproxi` | `xsd:double` | true | 0..1 |
| `pa` | `xsd:string` | true | 0..1 |
| `etapademar` | `xsd:string` | true | 0..1 |
| `situacaotr` | `xsd:string` | true | 0..1 |
| `nometrecho` | `xsd:string` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `datadeterm` | `xsd:date` | true | 0..1 |
| `dataaprova` | `xsd:date` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `SPU:vw_app_trecho_terreno_acrescido_marinha_a_03092026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `nivelpreci` | `xsd:string` | true | 0..1 |
| `idprodutoc` | `xsd:long` | true | 0..1 |
| `escalanume` | `xsd:string` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `areaaproxi` | `xsd:double` | true | 0..1 |
| `pa` | `xsd:string` | true | 0..1 |
| `etapademar` | `xsd:string` | true | 0..1 |
| `situacaotr` | `xsd:string` | true | 0..1 |
| `nometrecho` | `xsd:string` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `datadeterm` | `xsd:date` | true | 0..1 |
| `dataaprova` | `xsd:date` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `SPU:vw_app_trecho_terreno_marginal_a_03092026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `nivelpreci` | `xsd:string` | true | 0..1 |
| `idprodutoc` | `xsd:long` | true | 0..1 |
| `escalanume` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `areaaproxi` | `xsd:double` | true | 0..1 |
| `pa` | `xsd:string` | true | 0..1 |
| `etapademar` | `xsd:string` | true | 0..1 |
| `situacaotr` | `xsd:string` | true | 0..1 |
| `nometrecho` | `xsd:string` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `datadeterm` | `xsd:date` | true | 0..1 |
| `dataaprova` | `xsd:date` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `SPU:vw_app_trecho_terreno_marinha_a_03092026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `nivelpreci` | `xsd:string` | true | 0..1 |
| `idprodutoc` | `xsd:long` | true | 0..1 |
| `escalanume` | `xsd:string` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `areaaproxi` | `xsd:double` | true | 0..1 |
| `pa` | `xsd:string` | true | 0..1 |
| `etapademar` | `xsd:string` | true | 0..1 |
| `situacaotr` | `xsd:string` | true | 0..1 |
| `nometrecho` | `xsd:string` | true | 0..1 |
| `areaoficia` | `xsd:double` | true | 0..1 |
| `datadeterm` | `xsd:date` | true | 0..1 |
| `dataaprova` | `xsd:date` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `SPU:vw_lpp_trecho_lltm_l_03092026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `nivelpreci` | `xsd:string` | true | 0..1 |
| `idprodutoc` | `xsd:long` | true | 0..1 |
| `escalanume` | `xsd:string` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `pa` | `xsd:string` | true | 0..1 |
| `etapademar` | `xsd:string` | true | 0..1 |
| `situacaotr` | `xsd:string` | true | 0..1 |
| `nometrecho` | `xsd:string` | true | 0..1 |
| `nomerio` | `xsd:string` | true | 0..1 |
| `extensaoap` | `xsd:double` | true | 0..1 |
| `normarefer` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `datadeterm` | `xsd:date` | true | 0..1 |
| `dataaprova` | `xsd:date` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `SPU:vw_lpp_trecho_lmeo_l_03092026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `nivelpreci` | `xsd:string` | true | 0..1 |
| `idprodutoc` | `xsd:long` | true | 0..1 |
| `escalanume` | `xsd:string` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `pa` | `xsd:string` | true | 0..1 |
| `etapademar` | `xsd:string` | true | 0..1 |
| `situacaotr` | `xsd:string` | true | 0..1 |
| `nometrecho` | `xsd:string` | true | 0..1 |
| `nomerio` | `xsd:string` | true | 0..1 |
| `extensaoap` | `xsd:double` | true | 0..1 |
| `normarefer` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `datadeterm` | `xsd:date` | true | 0..1 |
| `dataaprova` | `xsd:date` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `SPU:vw_lpp_trecho_lpm_l_03092026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `nivelpreci` | `xsd:string` | true | 0..1 |
| `idprodutoc` | `xsd:long` | true | 0..1 |
| `escalanume` | `xsd:string` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `pa` | `xsd:string` | true | 0..1 |
| `etapademar` | `xsd:string` | true | 0..1 |
| `situacaotr` | `xsd:string` | true | 0..1 |
| `nometrecho` | `xsd:string` | true | 0..1 |
| `extensaoap` | `xsd:double` | true | 0..1 |
| `normarefer` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `datadeterm` | `xsd:date` | true | 0..1 |
| `dataaprova` | `xsd:date` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `SPU:vw_lpp_trecho_ltm_l_03092026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogc_fid` | `xsd:int` | false | 1..1 |
| `id` | `xsd:long` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `nivelpreci` | `xsd:string` | true | 0..1 |
| `idprodutoc` | `xsd:long` | true | 0..1 |
| `escalanume` | `xsd:string` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `pa` | `xsd:string` | true | 0..1 |
| `etapademar` | `xsd:string` | true | 0..1 |
| `situacaotr` | `xsd:string` | true | 0..1 |
| `nometrecho` | `xsd:string` | true | 0..1 |
| `extensaoap` | `xsd:double` | true | 0..1 |
| `normarefer` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `datadeterm` | `xsd:date` | true | 0..1 |
| `dataaprova` | `xsd:date` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
