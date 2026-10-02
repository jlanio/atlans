# ICA DECEA — atributos das camadas

Geoportal: [[Geosserviços/ICA DECEA/Instituto de Cartografia Aeronáutica — ICA—DECEA|Instituto de Cartografia Aeronáutica — ICA/DECEA]]

Os campos abaixo vêm de `DescribeFeatureType` (XSD), sem download de feições.

## ICA (421)

### `ICA:aga_jurisdicao`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `snippet` | `xsd:string` | true | 0..1 |

### `ICA:airport`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `id` | `xsd:string` | true | 0..1 |
| `ciad` | `xsd:string` | true | 0..1 |
| `localidade_id` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:date` | true | 0..1 |
| `fir` | `xsd:string` | true | 0..1 |
| `jurisdicao` | `xsd:string` | true | 0..1 |
| `latitude_dec` | `xsd:double` | true | 0..1 |
| `longitude_dec` | `xsd:double` | true | 0..1 |
| `latitude` | `xsd:string` | true | 0..1 |
| `longitude` | `xsd:string` | true | 0..1 |
| `elevacao` | `xsd:double` | true | 0..1 |
| `elev_uom` | `xsd:string` | true | 0..1 |
| `tipo_util` | `xsd:string` | true | 0..1 |
| `cat_sigla` | `xsd:string` | true | 0..1 |
| `opr` | `xsd:string` | true | 0..1 |
| `wh` | `xsd:string` | true | 0..1 |
| `cidade` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `utc` | `xsd:string` | true | 0..1 |
| `emenda_n` | `xsd:string` | true | 0..1 |
| `emenda` | `xsd:date` | true | 0..1 |
| `airport_pk` | `xsd:decimal` | true | 0..1 |

### `ICA:airport_heliport`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `id` | `xsd:string` | true | 0..1 |
| `ciad` | `xsd:string` | true | 0..1 |
| `localidade_id` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:date` | true | 0..1 |
| `fir` | `xsd:string` | true | 0..1 |
| `jurisdicao` | `xsd:string` | true | 0..1 |
| `latitude_dec` | `xsd:double` | true | 0..1 |
| `longitude_dec` | `xsd:double` | true | 0..1 |
| `latitude` | `xsd:string` | true | 0..1 |
| `longitude` | `xsd:string` | true | 0..1 |
| `elevacao` | `xsd:double` | true | 0..1 |
| `elev_uom` | `xsd:string` | true | 0..1 |
| `tipo_util` | `xsd:string` | true | 0..1 |
| `cat_sigla` | `xsd:string` | true | 0..1 |
| `opr` | `xsd:string` | true | 0..1 |
| `wh` | `xsd:string` | true | 0..1 |
| `cidade` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `utc` | `xsd:string` | true | 0..1 |
| `emenda_n` | `xsd:string` | true | 0..1 |
| `emenda` | `xsd:date` | true | 0..1 |
| `airport_pk` | `xsd:decimal` | true | 0..1 |

### `ICA:airspace`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `airspace_p` | `xsd:decimal` | true | 0..1 |
| `effectived` | `xsd:date` | true | 0..1 |
| `updatedt` | `xsd:date` | true | 0..1 |
| `updateoper` | `xsd:string` | true | 0..1 |
| `source` | `xsd:string` | true | 0..1 |
| `diffind` | `xsd:string` | true | 0..1 |
| `mslink` | `xsd:decimal` | true | 0..1 |
| `mapid` | `xsd:decimal` | true | 0..1 |
| `typ` | `xsd:string` | true | 0..1 |
| `ident` | `xsd:string` | true | 0..1 |
| `icaocode` | `xsd:string` | true | 0..1 |
| `address` | `xsd:string` | true | 0..1 |
| `nam` | `xsd:string` | true | 0..1 |
| `areacode` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:decimal` | true | 0..1 |
| `longitude` | `xsd:decimal` | true | 0..1 |
| `repunitspe` | `xsd:string` | true | 0..1 |
| `repunitalt` | `xsd:string` | true | 0..1 |
| `codedistve` | `xsd:string` | true | 0..1 |
| `uplimituni` | `xsd:string` | true | 0..1 |
| `codedistv1` | `xsd:string` | true | 0..1 |
| `lowerlimit` | `xsd:string` | true | 0..1 |
| `codedistv2` | `xsd:string` | true | 0..1 |
| `uomdistver` | `xsd:string` | true | 0..1 |
| `vallowerli` | `xsd:decimal` | true | 0..1 |
| `centerfea_` | `xsd:decimal` | true | 0..1 |
| `unitaddres` | `xsd:decimal` | true | 0..1 |
| `center_pk` | `xsd:decimal` | true | 0..1 |
| `txtrmk` | `xsd:string` | true | 0..1 |
| `txtborderr` | `xsd:string` | true | 0..1 |
| `cruisetabi` | `xsd:string` | true | 0..1 |
| `codewrkhr` | `xsd:string` | true | 0..1 |
| `codeclass` | `xsd:string` | true | 0..1 |
| `txtrmkwrkh` | `xsd:string` | true | 0..1 |
| `codelocind` | `xsd:string` | true | 0..1 |
| `upperlimit` | `xsd:decimal` | true | 0..1 |
| `uirupperli` | `xsd:decimal` | true | 0..1 |
| `lowerlimi1` | `xsd:decimal` | true | 0..1 |
| `valdistver` | `xsd:decimal` | true | 0..1 |
| `entryrpt` | `xsd:string` | true | 0..1 |
| `rnp` | `xsd:decimal` | true | 0..1 |
| `codeactivi` | `xsd:string` | true | 0..1 |
| `codedistv3` | `xsd:string` | true | 0..1 |
| `codemil` | `xsd:string` | true | 0..1 |
| `txtlocalty` | `xsd:string` | true | 0..1 |
| `uomdistve1` | `xsd:string` | true | 0..1 |
| `valdistve1` | `xsd:decimal` | true | 0..1 |
| `upperlower` | `xsd:string` | true | 0..1 |
| `width` | `xsd:decimal` | true | 0..1 |
| `widthuom` | `xsd:string` | true | 0..1 |
| `haccuracy` | `xsd:decimal` | true | 0..1 |
| `haccuracyu` | `xsd:string` | true | 0..1 |
| `airway_pk` | `xsd:decimal` | true | 0..1 |
| `txtrmk_loc` | `xsd:string` | true | 0..1 |
| `type_desig` | `xsd:string` | true | 0..1 |
| `relatedfir` | `xsd:string` | true | 0..1 |
| `txtrmkwrk1` | `xsd:string` | true | 0..1 |
| `classifica` | `xsd:string` | true | 0..1 |
| `classrmklo` | `xsd:string` | true | 0..1 |
| `bltype` | `xsd:string` | true | 0..1 |
| `excluir_ct` | `xsd:string` | true | 0..1 |
| `flexibleus` | `xsd:string` | true | 0..1 |
| `levl` | `xsd:string` | true | 0..1 |
| `codelocin1` | `xsd:string` | true | 0..1 |
| `txtrmkwrk2` | `xsd:string` | true | 0..1 |
| `txtrmk_lcl` | `xsd:string` | true | 0..1 |
| `emenda` | `xsd:date` | true | 0..1 |
| `emenda_futura` | `xsd:date` | true | 0..1 |

### `ICA:airway`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `airwayseg_` | `xsd:decimal` | true | 0..1 |
| `effectived` | `xsd:date` | true | 0..1 |
| `updatedt` | `xsd:date` | true | 0..1 |
| `airspace_p` | `xsd:decimal` | true | 0..1 |
| `airspace_1` | `xsd:decimal` | true | 0..1 |
| `airspace_2` | `xsd:decimal` | true | 0..1 |
| `airspace_3` | `xsd:decimal` | true | 0..1 |
| `airspace_4` | `xsd:decimal` | true | 0..1 |
| `updateoper` | `xsd:string` | true | 0..1 |
| `airway_pk` | `xsd:decimal` | true | 0..1 |
| `source` | `xsd:string` | true | 0..1 |
| `diffind` | `xsd:string` | true | 0..1 |
| `mslink` | `xsd:decimal` | true | 0..1 |
| `mapid` | `xsd:decimal` | true | 0..1 |
| `codetype` | `xsd:string` | true | 0..1 |
| `seq` | `xsd:decimal` | true | 0..1 |
| `codernp` | `xsd:decimal` | true | 0..1 |
| `levl` | `xsd:string` | true | 0..1 |
| `codeclassa` | `xsd:string` | true | 0..1 |
| `upperlimit` | `xsd:decimal` | true | 0..1 |
| `uomupperli` | `xsd:string` | true | 0..1 |
| `codedistve` | `xsd:string` | true | 0..1 |
| `lowerlimit` | `xsd:decimal` | true | 0..1 |
| `uomlowerli` | `xsd:string` | true | 0..1 |
| `codedistv1` | `xsd:string` | true | 0..1 |
| `mnmlimit` | `xsd:decimal` | true | 0..1 |
| `uommnmlimi` | `xsd:string` | true | 0..1 |
| `codedistv2` | `xsd:string` | true | 0..1 |
| `ovrdelower` | `xsd:decimal` | true | 0..1 |
| `uomlwrlmto` | `xsd:string` | true | 0..1 |
| `codedstver` | `xsd:string` | true | 0..1 |
| `fromfixdes` | `xsd:string` | true | 0..1 |
| `fromfixde1` | `xsd:string` | true | 0..1 |
| `fromfixde2` | `xsd:string` | true | 0..1 |
| `fromfixde3` | `xsd:string` | true | 0..1 |
| `tofixdesc1` | `xsd:string` | true | 0..1 |
| `tofixdesc2` | `xsd:string` | true | 0..1 |
| `tofixdesc3` | `xsd:string` | true | 0..1 |
| `tofixdesc4` | `xsd:string` | true | 0..1 |
| `rvsmstart` | `xsd:string` | true | 0..1 |
| `rvsmend` | `xsd:string` | true | 0..1 |
| `pathtype` | `xsd:string` | true | 0..1 |
| `intruetrac` | `xsd:decimal` | true | 0..1 |
| `inmagtrack` | `xsd:decimal` | true | 0..1 |
| `revtruetra` | `xsd:decimal` | true | 0..1 |
| `revmagtrac` | `xsd:decimal` | true | 0..1 |
| `routedis` | `xsd:decimal` | true | 0..1 |
| `changeover` | `xsd:decimal` | true | 0..1 |
| `uomdist` | `xsd:string` | true | 0..1 |
| `segmnt_pk` | `xsd:decimal` | true | 0..1 |
| `txtrmk` | `xsd:string` | true | 0..1 |
| `areacode` | `xsd:string` | true | 0..1 |
| `boundary` | `xsd:string` | true | 0..1 |
| `directrest` | `xsd:string` | true | 0..1 |
| `cruiseid` | `xsd:string` | true | 0..1 |
| `theta` | `xsd:decimal` | true | 0..1 |
| `rho` | `xsd:decimal` | true | 0..1 |
| `vor_pk` | `xsd:decimal` | true | 0..1 |
| `cruisedir` | `xsd:string` | true | 0..1 |
| `mnmlimitre` | `xsd:decimal` | true | 0..1 |
| `uommnmlim1` | `xsd:string` | true | 0..1 |
| `codedistv3` | `xsd:string` | true | 0..1 |
| `fixradtran` | `xsd:decimal` | true | 0..1 |
| `vor_pk2` | `xsd:decimal` | true | 0..1 |
| `totheta` | `xsd:decimal` | true | 0..1 |
| `torho` | `xsd:decimal` | true | 0..1 |
| `codedistv4` | `xsd:string` | true | 0..1 |
| `minlev` | `xsd:decimal` | true | 0..1 |
| `uomminlev` | `xsd:string` | true | 0..1 |
| `txtrmk_lcl` | `xsd:string` | true | 0..1 |
| `nonrnavusa` | `xsd:string` | true | 0..1 |
| `minobsclea` | `xsd:decimal` | true | 0..1 |
| `minobscle1` | `xsd:string` | true | 0..1 |
| `widthleft` | `xsd:decimal` | true | 0..1 |
| `widthleftu` | `xsd:string` | true | 0..1 |
| `widthright` | `xsd:decimal` | true | 0..1 |
| `widthrigh1` | `xsd:string` | true | 0..1 |
| `turndirect` | `xsd:string` | true | 0..1 |
| `signalgap` | `xsd:string` | true | 0..1 |
| `minenroute` | `xsd:decimal` | true | 0..1 |
| `minenrout1` | `xsd:string` | true | 0..1 |
| `mincrossin` | `xsd:decimal` | true | 0..1 |
| `mincrossi1` | `xsd:string` | true | 0..1 |
| `mincrossi2` | `xsd:string` | true | 0..1 |
| `maxcrossin` | `xsd:decimal` | true | 0..1 |
| `maxcrossi1` | `xsd:string` | true | 0..1 |
| `maxcrossi2` | `xsd:string` | true | 0..1 |
| `designator` | `xsd:string` | true | 0..1 |
| `to_airep_r` | `xsd:string` | true | 0..1 |
| `from_airep` | `xsd:string` | true | 0..1 |
| `bltype` | `xsd:string` | true | 0..1 |
| `airway_pk1` | `xsd:decimal` | true | 0..1 |
| `effective1` | `xsd:date` | true | 0..1 |
| `updatedt1` | `xsd:date` | true | 0..1 |
| `updateope1` | `xsd:string` | true | 0..1 |
| `source1` | `xsd:string` | true | 0..1 |
| `diffind1` | `xsd:string` | true | 0..1 |
| `mslink1` | `xsd:decimal` | true | 0..1 |
| `mapid1` | `xsd:decimal` | true | 0..1 |
| `txtdesig` | `xsd:string` | true | 0..1 |
| `txtlocdesi` | `xsd:string` | true | 0..1 |
| `txtrmk1` | `xsd:string` | true | 0..1 |
| `euindicato` | `xsd:string` | true | 0..1 |
| `txtrmk_lc1` | `xsd:string` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `flightrule` | `xsd:string` | true | 0..1 |
| `internatio` | `xsd:string` | true | 0..1 |
| `militaryus` | `xsd:string` | true | 0..1 |
| `miltraning` | `xsd:string` | true | 0..1 |
| `orgauth_pk` | `xsd:decimal` | true | 0..1 |
| `bltype1` | `xsd:string` | true | 0..1 |
| `emenda` | `xsd:date` | true | 0..1 |
| `emenda_futura` | `xsd:date` | true | 0..1 |

### `ICA:ATZ`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | false | 1..1 |
| `airspace_p` | `xsd:decimal` | true | 0..1 |
| `effectived` | `xsd:date` | true | 0..1 |
| `typ` | `xsd:string` | true | 0..1 |
| `ident` | `xsd:string` | true | 0..1 |
| `icaocode` | `xsd:string` | true | 0..1 |
| `nam` | `xsd:string` | true | 0..1 |
| `areacode` | `xsd:string` | true | 0..1 |
| `codedistve` | `xsd:string` | true | 0..1 |
| `uplimituni` | `xsd:string` | true | 0..1 |
| `codedistv1` | `xsd:string` | true | 0..1 |
| `lowerlimit` | `xsd:string` | true | 0..1 |
| `uomdistver` | `xsd:string` | true | 0..1 |
| `codewrkhr` | `xsd:string` | true | 0..1 |
| `upperlimit` | `xsd:decimal` | true | 0..1 |
| `lowerlimi1` | `xsd:decimal` | true | 0..1 |
| `entryrpt` | `xsd:string` | true | 0..1 |
| `txtlocalty` | `xsd:string` | true | 0..1 |
| `txtrmk_loc` | `xsd:string` | true | 0..1 |
| `relatedfir` | `xsd:string` | true | 0..1 |
| `classrmklo` | `xsd:string` | true | 0..1 |
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |

### `ICA:CTA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `airspace_p` | `xsd:decimal` | true | 0..1 |
| `effectived` | `xsd:date` | true | 0..1 |
| `typ` | `xsd:string` | true | 0..1 |
| `ident` | `xsd:string` | true | 0..1 |
| `icaocode` | `xsd:string` | true | 0..1 |
| `nam` | `xsd:string` | true | 0..1 |
| `areacode` | `xsd:string` | true | 0..1 |
| `codedistve` | `xsd:string` | true | 0..1 |
| `uplimituni` | `xsd:string` | true | 0..1 |
| `codedistv1` | `xsd:string` | true | 0..1 |
| `lowerlimit` | `xsd:string` | true | 0..1 |
| `uomdistver` | `xsd:string` | true | 0..1 |
| `codewrkhr` | `xsd:string` | true | 0..1 |
| `upperlimit` | `xsd:decimal` | true | 0..1 |
| `lowerlimi1` | `xsd:decimal` | true | 0..1 |
| `entryrpt` | `xsd:string` | true | 0..1 |
| `txtlocalty` | `xsd:string` | true | 0..1 |
| `txtrmk_loc` | `xsd:string` | true | 0..1 |
| `relatedfir` | `xsd:string` | true | 0..1 |
| `classrmklo` | `xsd:string` | true | 0..1 |
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |
| `emenda` | `xsd:date` | true | 0..1 |
| `emenda_futura` | `xsd:date` | true | 0..1 |

### `ICA:CTR`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `airspace_p` | `xsd:decimal` | true | 0..1 |
| `effectived` | `xsd:date` | true | 0..1 |
| `typ` | `xsd:string` | true | 0..1 |
| `ident` | `xsd:string` | true | 0..1 |
| `icaocode` | `xsd:string` | true | 0..1 |
| `nam` | `xsd:string` | true | 0..1 |
| `areacode` | `xsd:string` | true | 0..1 |
| `codedistve` | `xsd:string` | true | 0..1 |
| `uplimituni` | `xsd:string` | true | 0..1 |
| `codedistv1` | `xsd:string` | true | 0..1 |
| `lowerlimit` | `xsd:string` | true | 0..1 |
| `uomdistver` | `xsd:string` | true | 0..1 |
| `codewrkhr` | `xsd:string` | true | 0..1 |
| `upperlimit` | `xsd:decimal` | true | 0..1 |
| `lowerlimi1` | `xsd:decimal` | true | 0..1 |
| `entryrpt` | `xsd:string` | true | 0..1 |
| `txtlocalty` | `xsd:string` | true | 0..1 |
| `txtrmk_loc` | `xsd:string` | true | 0..1 |
| `relatedfir` | `xsd:string` | true | 0..1 |
| `classrmklo` | `xsd:string` | true | 0..1 |
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |
| `emenda` | `xsd:date` | true | 0..1 |
| `emenda_futura` | `xsd:date` | true | 0..1 |

### `ICA:CV_REA_BR_COMPLETO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `fca` | `xsd:string` | true | 0..1 |
| `ats` | `xsd:string` | true | 0..1 |
| `semi_largura` | `xsd:double` | true | 0..1 |
| `rumoa_to_b` | `xsd:int` | true | 0..1 |
| `rumob_to_a` | `xsd:int` | true | 0..1 |
| `altmax` | `xsd:int` | true | 0..1 |
| `altmin` | `xsd:int` | true | 0..1 |
| `altcomp` | `xsd:int` | true | 0..1 |
| `altmaxa_to_b` | `xsd:int` | true | 0..1 |
| `altmina_to_b` | `xsd:int` | true | 0..1 |
| `altmaxb_to_a` | `xsd:int` | true | 0..1 |
| `altminb_to_a` | `xsd:int` | true | 0..1 |
| `altcompa_to_b` | `xsd:int` | true | 0..1 |
| `altcompb_to_a` | `xsd:int` | true | 0..1 |
| `fixo_a_lat` | `xsd:double` | true | 0..1 |
| `fixo_a_lon` | `xsd:double` | true | 0..1 |
| `fixo_b_lat` | `xsd:double` | true | 0..1 |
| `fixo_b_lon` | `xsd:double` | true | 0..1 |
| `eixokey` | `xsd:string` | true | 0..1 |
| `fixo_a_nome` | `xsd:string` | true | 0..1 |
| `fixo_b_nome` | `xsd:string` | true | 0..1 |
| `carta_nome` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:dateTime` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |

### `ICA:CV_REA_PI_PARINTINS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `fca` | `xsd:string` | true | 0..1 |
| `ats` | `xsd:string` | true | 0..1 |
| `semi_largura` | `xsd:double` | true | 0..1 |
| `rumoa_to_b` | `xsd:int` | true | 0..1 |
| `rumob_to_a` | `xsd:int` | true | 0..1 |
| `altmax` | `xsd:int` | true | 0..1 |
| `altmin` | `xsd:int` | true | 0..1 |
| `altcomp` | `xsd:int` | true | 0..1 |
| `altmaxa_to_b` | `xsd:int` | true | 0..1 |
| `altmina_to_b` | `xsd:int` | true | 0..1 |
| `altmaxb_to_a` | `xsd:int` | true | 0..1 |
| `altminb_to_a` | `xsd:int` | true | 0..1 |
| `altcompa_to_b` | `xsd:int` | true | 0..1 |
| `altcompb_to_a` | `xsd:int` | true | 0..1 |
| `fixo_a_lat` | `xsd:double` | true | 0..1 |
| `fixo_a_lon` | `xsd:double` | true | 0..1 |
| `fixo_b_lat` | `xsd:double` | true | 0..1 |
| `fixo_b_lon` | `xsd:double` | true | 0..1 |
| `eixokey` | `xsd:string` | true | 0..1 |
| `fixo_a_nome` | `xsd:string` | true | 0..1 |
| `fixo_b_nome` | `xsd:string` | true | 0..1 |
| `carta_nome` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:dateTime` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |

### `ICA:CV_REA_WA_TABATINGA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `fca` | `xsd:string` | true | 0..1 |
| `ats` | `xsd:string` | true | 0..1 |
| `semi_largura` | `xsd:double` | true | 0..1 |
| `rumoa_to_b` | `xsd:int` | true | 0..1 |
| `rumob_to_a` | `xsd:int` | true | 0..1 |
| `altmax` | `xsd:int` | true | 0..1 |
| `altmin` | `xsd:int` | true | 0..1 |
| `altcomp` | `xsd:int` | true | 0..1 |
| `altmaxa_to_b` | `xsd:int` | true | 0..1 |
| `altmina_to_b` | `xsd:int` | true | 0..1 |
| `altmaxb_to_a` | `xsd:int` | true | 0..1 |
| `altminb_to_a` | `xsd:int` | true | 0..1 |
| `altcompa_to_b` | `xsd:int` | true | 0..1 |
| `altcompb_to_a` | `xsd:int` | true | 0..1 |
| `fixo_a_lat` | `xsd:double` | true | 0..1 |
| `fixo_a_lon` | `xsd:double` | true | 0..1 |
| `fixo_b_lat` | `xsd:double` | true | 0..1 |
| `fixo_b_lon` | `xsd:double` | true | 0..1 |
| `eixokey` | `xsd:string` | true | 0..1 |
| `fixo_a_nome` | `xsd:string` | true | 0..1 |
| `fixo_b_nome` | `xsd:string` | true | 0..1 |
| `carta_nome` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:dateTime` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |

### `ICA:CV_REA_WB_BELEM`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `fca` | `xsd:string` | true | 0..1 |
| `ats` | `xsd:string` | true | 0..1 |
| `semi_largura` | `xsd:double` | true | 0..1 |
| `rumoa_to_b` | `xsd:int` | true | 0..1 |
| `rumob_to_a` | `xsd:int` | true | 0..1 |
| `altmax` | `xsd:int` | true | 0..1 |
| `altmin` | `xsd:int` | true | 0..1 |
| `altcomp` | `xsd:int` | true | 0..1 |
| `altmaxa_to_b` | `xsd:int` | true | 0..1 |
| `altmina_to_b` | `xsd:int` | true | 0..1 |
| `altmaxb_to_a` | `xsd:int` | true | 0..1 |
| `altminb_to_a` | `xsd:int` | true | 0..1 |
| `altcompa_to_b` | `xsd:int` | true | 0..1 |
| `altcompb_to_a` | `xsd:int` | true | 0..1 |
| `fixo_a_lat` | `xsd:double` | true | 0..1 |
| `fixo_a_lon` | `xsd:double` | true | 0..1 |
| `fixo_b_lat` | `xsd:double` | true | 0..1 |
| `fixo_b_lon` | `xsd:double` | true | 0..1 |
| `eixokey` | `xsd:string` | true | 0..1 |
| `fixo_a_nome` | `xsd:string` | true | 0..1 |
| `fixo_b_nome` | `xsd:string` | true | 0..1 |
| `carta_nome` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:dateTime` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |

### `ICA:CV_REA_WF_RECIFE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `fca` | `xsd:string` | true | 0..1 |
| `ats` | `xsd:string` | true | 0..1 |
| `semi_largura` | `xsd:double` | true | 0..1 |
| `rumoa_to_b` | `xsd:int` | true | 0..1 |
| `rumob_to_a` | `xsd:int` | true | 0..1 |
| `altmax` | `xsd:int` | true | 0..1 |
| `altmin` | `xsd:int` | true | 0..1 |
| `altcomp` | `xsd:int` | true | 0..1 |
| `altmaxa_to_b` | `xsd:int` | true | 0..1 |
| `altmina_to_b` | `xsd:int` | true | 0..1 |
| `altmaxb_to_a` | `xsd:int` | true | 0..1 |
| `altminb_to_a` | `xsd:int` | true | 0..1 |
| `altcompa_to_b` | `xsd:int` | true | 0..1 |
| `altcompb_to_a` | `xsd:int` | true | 0..1 |
| `fixo_a_lat` | `xsd:double` | true | 0..1 |
| `fixo_a_lon` | `xsd:double` | true | 0..1 |
| `fixo_b_lat` | `xsd:double` | true | 0..1 |
| `fixo_b_lon` | `xsd:double` | true | 0..1 |
| `eixokey` | `xsd:string` | true | 0..1 |
| `fixo_a_nome` | `xsd:string` | true | 0..1 |
| `fixo_b_nome` | `xsd:string` | true | 0..1 |
| `carta_nome` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:dateTime` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |

### `ICA:CV_REA_WG_CAMPO_GRANDE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `fca` | `xsd:string` | true | 0..1 |
| `ats` | `xsd:string` | true | 0..1 |
| `semi_largura` | `xsd:double` | true | 0..1 |
| `rumoa_to_b` | `xsd:int` | true | 0..1 |
| `rumob_to_a` | `xsd:int` | true | 0..1 |
| `altmax` | `xsd:int` | true | 0..1 |
| `altmin` | `xsd:int` | true | 0..1 |
| `altcomp` | `xsd:int` | true | 0..1 |
| `altmaxa_to_b` | `xsd:int` | true | 0..1 |
| `altmina_to_b` | `xsd:int` | true | 0..1 |
| `altmaxb_to_a` | `xsd:int` | true | 0..1 |
| `altminb_to_a` | `xsd:int` | true | 0..1 |
| `altcompa_to_b` | `xsd:int` | true | 0..1 |
| `altcompb_to_a` | `xsd:int` | true | 0..1 |
| `fixo_a_lat` | `xsd:double` | true | 0..1 |
| `fixo_a_lon` | `xsd:double` | true | 0..1 |
| `fixo_b_lat` | `xsd:double` | true | 0..1 |
| `fixo_b_lon` | `xsd:double` | true | 0..1 |
| `eixokey` | `xsd:string` | true | 0..1 |
| `fixo_a_nome` | `xsd:string` | true | 0..1 |
| `fixo_b_nome` | `xsd:string` | true | 0..1 |
| `carta_nome` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:dateTime` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |

### `ICA:CV_REA_WJ1_RIO_DE_JANEIRO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `fca` | `xsd:string` | true | 0..1 |
| `ats` | `xsd:string` | true | 0..1 |
| `semi_largura` | `xsd:double` | true | 0..1 |
| `rumoa_to_b` | `xsd:int` | true | 0..1 |
| `rumob_to_a` | `xsd:int` | true | 0..1 |
| `altmax` | `xsd:int` | true | 0..1 |
| `altmin` | `xsd:int` | true | 0..1 |
| `altcomp` | `xsd:int` | true | 0..1 |
| `altmaxa_to_b` | `xsd:int` | true | 0..1 |
| `altmina_to_b` | `xsd:int` | true | 0..1 |
| `altmaxb_to_a` | `xsd:int` | true | 0..1 |
| `altminb_to_a` | `xsd:int` | true | 0..1 |
| `altcompa_to_b` | `xsd:int` | true | 0..1 |
| `altcompb_to_a` | `xsd:int` | true | 0..1 |
| `fixo_a_lat` | `xsd:double` | true | 0..1 |
| `fixo_a_lon` | `xsd:double` | true | 0..1 |
| `fixo_b_lat` | `xsd:double` | true | 0..1 |
| `fixo_b_lon` | `xsd:double` | true | 0..1 |
| `eixokey` | `xsd:string` | true | 0..1 |
| `fixo_a_nome` | `xsd:string` | true | 0..1 |
| `fixo_b_nome` | `xsd:string` | true | 0..1 |
| `carta_nome` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:dateTime` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |

### `ICA:CV_REA_WK_PORTO_SEGURO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `fca` | `xsd:string` | true | 0..1 |
| `ats` | `xsd:string` | true | 0..1 |
| `semi_largura` | `xsd:double` | true | 0..1 |
| `rumoa_to_b` | `xsd:int` | true | 0..1 |
| `rumob_to_a` | `xsd:int` | true | 0..1 |
| `altmax` | `xsd:int` | true | 0..1 |
| `altmin` | `xsd:int` | true | 0..1 |
| `altcomp` | `xsd:int` | true | 0..1 |
| `altmaxa_to_b` | `xsd:int` | true | 0..1 |
| `altmina_to_b` | `xsd:int` | true | 0..1 |
| `altmaxb_to_a` | `xsd:int` | true | 0..1 |
| `altminb_to_a` | `xsd:int` | true | 0..1 |
| `altcompa_to_b` | `xsd:int` | true | 0..1 |
| `altcompb_to_a` | `xsd:int` | true | 0..1 |
| `fixo_a_lat` | `xsd:double` | true | 0..1 |
| `fixo_a_lon` | `xsd:double` | true | 0..1 |
| `fixo_b_lat` | `xsd:double` | true | 0..1 |
| `fixo_b_lon` | `xsd:double` | true | 0..1 |
| `eixokey` | `xsd:string` | true | 0..1 |
| `fixo_a_nome` | `xsd:string` | true | 0..1 |
| `fixo_b_nome` | `xsd:string` | true | 0..1 |
| `carta_nome` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:dateTime` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |

### `ICA:CV_REA_WN_MANAUS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `fca` | `xsd:string` | true | 0..1 |
| `ats` | `xsd:string` | true | 0..1 |
| `semi_largura` | `xsd:double` | true | 0..1 |
| `rumoa_to_b` | `xsd:int` | true | 0..1 |
| `rumob_to_a` | `xsd:int` | true | 0..1 |
| `altmax` | `xsd:int` | true | 0..1 |
| `altmin` | `xsd:int` | true | 0..1 |
| `altcomp` | `xsd:int` | true | 0..1 |
| `altmaxa_to_b` | `xsd:int` | true | 0..1 |
| `altmina_to_b` | `xsd:int` | true | 0..1 |
| `altmaxb_to_a` | `xsd:int` | true | 0..1 |
| `altminb_to_a` | `xsd:int` | true | 0..1 |
| `altcompa_to_b` | `xsd:int` | true | 0..1 |
| `altcompb_to_a` | `xsd:int` | true | 0..1 |
| `fixo_a_lat` | `xsd:double` | true | 0..1 |
| `fixo_a_lon` | `xsd:double` | true | 0..1 |
| `fixo_b_lat` | `xsd:double` | true | 0..1 |
| `fixo_b_lon` | `xsd:double` | true | 0..1 |
| `eixokey` | `xsd:string` | true | 0..1 |
| `fixo_a_nome` | `xsd:string` | true | 0..1 |
| `fixo_b_nome` | `xsd:string` | true | 0..1 |
| `carta_nome` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:dateTime` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |

### `ICA:CV_REA_WP1_PORTO_ALEGRE`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `fca` | `xsd:string` | true | 0..1 |
| `ats` | `xsd:string` | true | 0..1 |
| `semi_largura` | `xsd:double` | true | 0..1 |
| `rumoa_to_b` | `xsd:int` | true | 0..1 |
| `rumob_to_a` | `xsd:int` | true | 0..1 |
| `altmax` | `xsd:int` | true | 0..1 |
| `altmin` | `xsd:int` | true | 0..1 |
| `altcomp` | `xsd:int` | true | 0..1 |
| `altmaxa_to_b` | `xsd:int` | true | 0..1 |
| `altmina_to_b` | `xsd:int` | true | 0..1 |
| `altmaxb_to_a` | `xsd:int` | true | 0..1 |
| `altminb_to_a` | `xsd:int` | true | 0..1 |
| `altcompa_to_b` | `xsd:int` | true | 0..1 |
| `altcompb_to_a` | `xsd:int` | true | 0..1 |
| `fixo_a_lat` | `xsd:double` | true | 0..1 |
| `fixo_a_lon` | `xsd:double` | true | 0..1 |
| `fixo_b_lat` | `xsd:double` | true | 0..1 |
| `fixo_b_lon` | `xsd:double` | true | 0..1 |
| `eixokey` | `xsd:string` | true | 0..1 |
| `fixo_a_nome` | `xsd:string` | true | 0..1 |
| `fixo_b_nome` | `xsd:string` | true | 0..1 |
| `carta_nome` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:dateTime` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |

### `ICA:CV_REA_WR_BRASILIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `fca` | `xsd:string` | true | 0..1 |
| `ats` | `xsd:string` | true | 0..1 |
| `semi_largura` | `xsd:double` | true | 0..1 |
| `rumoa_to_b` | `xsd:int` | true | 0..1 |
| `rumob_to_a` | `xsd:int` | true | 0..1 |
| `altmax` | `xsd:int` | true | 0..1 |
| `altmin` | `xsd:int` | true | 0..1 |
| `altcomp` | `xsd:int` | true | 0..1 |
| `altmaxa_to_b` | `xsd:int` | true | 0..1 |
| `altmina_to_b` | `xsd:int` | true | 0..1 |
| `altmaxb_to_a` | `xsd:int` | true | 0..1 |
| `altminb_to_a` | `xsd:int` | true | 0..1 |
| `altcompa_to_b` | `xsd:int` | true | 0..1 |
| `altcompb_to_a` | `xsd:int` | true | 0..1 |
| `fixo_a_lat` | `xsd:double` | true | 0..1 |
| `fixo_a_lon` | `xsd:double` | true | 0..1 |
| `fixo_b_lat` | `xsd:double` | true | 0..1 |
| `fixo_b_lon` | `xsd:double` | true | 0..1 |
| `eixokey` | `xsd:string` | true | 0..1 |
| `fixo_a_nome` | `xsd:string` | true | 0..1 |
| `fixo_b_nome` | `xsd:string` | true | 0..1 |
| `carta_nome` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:dateTime` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |

### `ICA:CV_REA_WS_SAO_LUIS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `fca` | `xsd:string` | true | 0..1 |
| `ats` | `xsd:string` | true | 0..1 |
| `semi_largura` | `xsd:double` | true | 0..1 |
| `rumoa_to_b` | `xsd:int` | true | 0..1 |
| `rumob_to_a` | `xsd:int` | true | 0..1 |
| `altmax` | `xsd:int` | true | 0..1 |
| `altmin` | `xsd:int` | true | 0..1 |
| `altcomp` | `xsd:int` | true | 0..1 |
| `altmaxa_to_b` | `xsd:int` | true | 0..1 |
| `altmina_to_b` | `xsd:int` | true | 0..1 |
| `altmaxb_to_a` | `xsd:int` | true | 0..1 |
| `altminb_to_a` | `xsd:int` | true | 0..1 |
| `altcompa_to_b` | `xsd:int` | true | 0..1 |
| `altcompb_to_a` | `xsd:int` | true | 0..1 |
| `fixo_a_lat` | `xsd:double` | true | 0..1 |
| `fixo_a_lon` | `xsd:double` | true | 0..1 |
| `fixo_b_lat` | `xsd:double` | true | 0..1 |
| `fixo_b_lon` | `xsd:double` | true | 0..1 |
| `eixokey` | `xsd:string` | true | 0..1 |
| `fixo_a_nome` | `xsd:string` | true | 0..1 |
| `fixo_b_nome` | `xsd:string` | true | 0..1 |
| `carta_nome` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:dateTime` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |

### `ICA:CV_REA_WX_SANTAREM`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `fca` | `xsd:string` | true | 0..1 |
| `ats` | `xsd:string` | true | 0..1 |
| `semi_largura` | `xsd:double` | true | 0..1 |
| `rumoa_to_b` | `xsd:int` | true | 0..1 |
| `rumob_to_a` | `xsd:int` | true | 0..1 |
| `altmax` | `xsd:int` | true | 0..1 |
| `altmin` | `xsd:int` | true | 0..1 |
| `altcomp` | `xsd:int` | true | 0..1 |
| `altmaxa_to_b` | `xsd:int` | true | 0..1 |
| `altmina_to_b` | `xsd:int` | true | 0..1 |
| `altmaxb_to_a` | `xsd:int` | true | 0..1 |
| `altminb_to_a` | `xsd:int` | true | 0..1 |
| `altcompa_to_b` | `xsd:int` | true | 0..1 |
| `altcompb_to_a` | `xsd:int` | true | 0..1 |
| `fixo_a_lat` | `xsd:double` | true | 0..1 |
| `fixo_a_lon` | `xsd:double` | true | 0..1 |
| `fixo_b_lat` | `xsd:double` | true | 0..1 |
| `fixo_b_lon` | `xsd:double` | true | 0..1 |
| `eixokey` | `xsd:string` | true | 0..1 |
| `fixo_a_nome` | `xsd:string` | true | 0..1 |
| `fixo_b_nome` | `xsd:string` | true | 0..1 |
| `carta_nome` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:dateTime` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |

### `ICA:CV_REA_WY_CUIABA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `fca` | `xsd:string` | true | 0..1 |
| `ats` | `xsd:string` | true | 0..1 |
| `semi_largura` | `xsd:double` | true | 0..1 |
| `rumoa_to_b` | `xsd:int` | true | 0..1 |
| `rumob_to_a` | `xsd:int` | true | 0..1 |
| `altmax` | `xsd:int` | true | 0..1 |
| `altmin` | `xsd:int` | true | 0..1 |
| `altcomp` | `xsd:int` | true | 0..1 |
| `altmaxa_to_b` | `xsd:int` | true | 0..1 |
| `altmina_to_b` | `xsd:int` | true | 0..1 |
| `altmaxb_to_a` | `xsd:int` | true | 0..1 |
| `altminb_to_a` | `xsd:int` | true | 0..1 |
| `altcompa_to_b` | `xsd:int` | true | 0..1 |
| `altcompb_to_a` | `xsd:int` | true | 0..1 |
| `fixo_a_lat` | `xsd:double` | true | 0..1 |
| `fixo_a_lon` | `xsd:double` | true | 0..1 |
| `fixo_b_lat` | `xsd:double` | true | 0..1 |
| `fixo_b_lon` | `xsd:double` | true | 0..1 |
| `eixokey` | `xsd:string` | true | 0..1 |
| `fixo_a_nome` | `xsd:string` | true | 0..1 |
| `fixo_b_nome` | `xsd:string` | true | 0..1 |
| `carta_nome` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:dateTime` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |

### `ICA:CV_REA_WZ_FORTALEZA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `fca` | `xsd:string` | true | 0..1 |
| `ats` | `xsd:string` | true | 0..1 |
| `semi_largura` | `xsd:double` | true | 0..1 |
| `rumoa_to_b` | `xsd:int` | true | 0..1 |
| `rumob_to_a` | `xsd:int` | true | 0..1 |
| `altmax` | `xsd:int` | true | 0..1 |
| `altmin` | `xsd:int` | true | 0..1 |
| `altcomp` | `xsd:int` | true | 0..1 |
| `altmaxa_to_b` | `xsd:int` | true | 0..1 |
| `altmina_to_b` | `xsd:int` | true | 0..1 |
| `altmaxb_to_a` | `xsd:int` | true | 0..1 |
| `altminb_to_a` | `xsd:int` | true | 0..1 |
| `altcompa_to_b` | `xsd:int` | true | 0..1 |
| `altcompb_to_a` | `xsd:int` | true | 0..1 |
| `fixo_a_lat` | `xsd:double` | true | 0..1 |
| `fixo_a_lon` | `xsd:double` | true | 0..1 |
| `fixo_b_lat` | `xsd:double` | true | 0..1 |
| `fixo_b_lon` | `xsd:double` | true | 0..1 |
| `eixokey` | `xsd:string` | true | 0..1 |
| `fixo_a_nome` | `xsd:string` | true | 0..1 |
| `fixo_b_nome` | `xsd:string` | true | 0..1 |
| `carta_nome` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:dateTime` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |

### `ICA:CV_REA_XF_FLORIANOPOLIS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `fca` | `xsd:string` | true | 0..1 |
| `ats` | `xsd:string` | true | 0..1 |
| `semi_largura` | `xsd:double` | true | 0..1 |
| `rumoa_to_b` | `xsd:int` | true | 0..1 |
| `rumob_to_a` | `xsd:int` | true | 0..1 |
| `altmax` | `xsd:int` | true | 0..1 |
| `altmin` | `xsd:int` | true | 0..1 |
| `altcomp` | `xsd:int` | true | 0..1 |
| `altmaxa_to_b` | `xsd:int` | true | 0..1 |
| `altmina_to_b` | `xsd:int` | true | 0..1 |
| `altmaxb_to_a` | `xsd:int` | true | 0..1 |
| `altminb_to_a` | `xsd:int` | true | 0..1 |
| `altcompa_to_b` | `xsd:int` | true | 0..1 |
| `altcompb_to_a` | `xsd:int` | true | 0..1 |
| `fixo_a_lat` | `xsd:double` | true | 0..1 |
| `fixo_a_lon` | `xsd:double` | true | 0..1 |
| `fixo_b_lat` | `xsd:double` | true | 0..1 |
| `fixo_b_lon` | `xsd:double` | true | 0..1 |
| `eixokey` | `xsd:string` | true | 0..1 |
| `fixo_a_nome` | `xsd:string` | true | 0..1 |
| `fixo_b_nome` | `xsd:string` | true | 0..1 |
| `carta_nome` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:dateTime` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |

### `ICA:CV_REA_XK_MACAPA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `fca` | `xsd:string` | true | 0..1 |
| `ats` | `xsd:string` | true | 0..1 |
| `semi_largura` | `xsd:double` | true | 0..1 |
| `rumoa_to_b` | `xsd:int` | true | 0..1 |
| `rumob_to_a` | `xsd:int` | true | 0..1 |
| `altmax` | `xsd:int` | true | 0..1 |
| `altmin` | `xsd:int` | true | 0..1 |
| `altcomp` | `xsd:int` | true | 0..1 |
| `altmaxa_to_b` | `xsd:int` | true | 0..1 |
| `altmina_to_b` | `xsd:int` | true | 0..1 |
| `altmaxb_to_a` | `xsd:int` | true | 0..1 |
| `altminb_to_a` | `xsd:int` | true | 0..1 |
| `altcompa_to_b` | `xsd:int` | true | 0..1 |
| `altcompb_to_a` | `xsd:int` | true | 0..1 |
| `fixo_a_lat` | `xsd:double` | true | 0..1 |
| `fixo_a_lon` | `xsd:double` | true | 0..1 |
| `fixo_b_lat` | `xsd:double` | true | 0..1 |
| `fixo_b_lon` | `xsd:double` | true | 0..1 |
| `eixokey` | `xsd:string` | true | 0..1 |
| `fixo_a_nome` | `xsd:string` | true | 0..1 |
| `fixo_b_nome` | `xsd:string` | true | 0..1 |
| `carta_nome` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:dateTime` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |

### `ICA:CV_REA_XN_ANAPOLIS`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `fca` | `xsd:string` | true | 0..1 |
| `ats` | `xsd:string` | true | 0..1 |
| `semi_largura` | `xsd:double` | true | 0..1 |
| `rumoa_to_b` | `xsd:int` | true | 0..1 |
| `rumob_to_a` | `xsd:int` | true | 0..1 |
| `altmax` | `xsd:int` | true | 0..1 |
| `altmin` | `xsd:int` | true | 0..1 |
| `altcomp` | `xsd:int` | true | 0..1 |
| `altmaxa_to_b` | `xsd:int` | true | 0..1 |
| `altmina_to_b` | `xsd:int` | true | 0..1 |
| `altmaxb_to_a` | `xsd:int` | true | 0..1 |
| `altminb_to_a` | `xsd:int` | true | 0..1 |
| `altcompa_to_b` | `xsd:int` | true | 0..1 |
| `altcompb_to_a` | `xsd:int` | true | 0..1 |
| `fixo_a_lat` | `xsd:double` | true | 0..1 |
| `fixo_a_lon` | `xsd:double` | true | 0..1 |
| `fixo_b_lat` | `xsd:double` | true | 0..1 |
| `fixo_b_lon` | `xsd:double` | true | 0..1 |
| `eixokey` | `xsd:string` | true | 0..1 |
| `fixo_a_nome` | `xsd:string` | true | 0..1 |
| `fixo_b_nome` | `xsd:string` | true | 0..1 |
| `carta_nome` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:dateTime` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |

### `ICA:CV_REA_XO_LONDRINA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `fca` | `xsd:string` | true | 0..1 |
| `ats` | `xsd:string` | true | 0..1 |
| `semi_largura` | `xsd:double` | true | 0..1 |
| `rumoa_to_b` | `xsd:int` | true | 0..1 |
| `rumob_to_a` | `xsd:int` | true | 0..1 |
| `altmax` | `xsd:int` | true | 0..1 |
| `altmin` | `xsd:int` | true | 0..1 |
| `altcomp` | `xsd:int` | true | 0..1 |
| `altmaxa_to_b` | `xsd:int` | true | 0..1 |
| `altmina_to_b` | `xsd:int` | true | 0..1 |
| `altmaxb_to_a` | `xsd:int` | true | 0..1 |
| `altminb_to_a` | `xsd:int` | true | 0..1 |
| `altcompa_to_b` | `xsd:int` | true | 0..1 |
| `altcompb_to_a` | `xsd:int` | true | 0..1 |
| `fixo_a_lat` | `xsd:double` | true | 0..1 |
| `fixo_a_lon` | `xsd:double` | true | 0..1 |
| `fixo_b_lat` | `xsd:double` | true | 0..1 |
| `fixo_b_lon` | `xsd:double` | true | 0..1 |
| `eixokey` | `xsd:string` | true | 0..1 |
| `fixo_a_nome` | `xsd:string` | true | 0..1 |
| `fixo_b_nome` | `xsd:string` | true | 0..1 |
| `carta_nome` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:dateTime` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |

### `ICA:CV_REA_XP1_SAO_PAULO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `fca` | `xsd:string` | true | 0..1 |
| `ats` | `xsd:string` | true | 0..1 |
| `semi_largura` | `xsd:double` | true | 0..1 |
| `rumoa_to_b` | `xsd:int` | true | 0..1 |
| `rumob_to_a` | `xsd:int` | true | 0..1 |
| `altmax` | `xsd:int` | true | 0..1 |
| `altmin` | `xsd:int` | true | 0..1 |
| `altcomp` | `xsd:int` | true | 0..1 |
| `altmaxa_to_b` | `xsd:int` | true | 0..1 |
| `altmina_to_b` | `xsd:int` | true | 0..1 |
| `altmaxb_to_a` | `xsd:int` | true | 0..1 |
| `altminb_to_a` | `xsd:int` | true | 0..1 |
| `altcompa_to_b` | `xsd:int` | true | 0..1 |
| `altcompb_to_a` | `xsd:int` | true | 0..1 |
| `fixo_a_lat` | `xsd:double` | true | 0..1 |
| `fixo_a_lon` | `xsd:double` | true | 0..1 |
| `fixo_b_lat` | `xsd:double` | true | 0..1 |
| `fixo_b_lon` | `xsd:double` | true | 0..1 |
| `eixokey` | `xsd:string` | true | 0..1 |
| `fixo_a_nome` | `xsd:string` | true | 0..1 |
| `fixo_b_nome` | `xsd:string` | true | 0..1 |
| `carta_nome` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:dateTime` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |

### `ICA:CV_REA_XQ_RIBEIRAO_PRETO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `fca` | `xsd:string` | true | 0..1 |
| `ats` | `xsd:string` | true | 0..1 |
| `semi_largura` | `xsd:double` | true | 0..1 |
| `rumoa_to_b` | `xsd:int` | true | 0..1 |
| `rumob_to_a` | `xsd:int` | true | 0..1 |
| `altmax` | `xsd:int` | true | 0..1 |
| `altmin` | `xsd:int` | true | 0..1 |
| `altcomp` | `xsd:int` | true | 0..1 |
| `altmaxa_to_b` | `xsd:int` | true | 0..1 |
| `altmina_to_b` | `xsd:int` | true | 0..1 |
| `altmaxb_to_a` | `xsd:int` | true | 0..1 |
| `altminb_to_a` | `xsd:int` | true | 0..1 |
| `altcompa_to_b` | `xsd:int` | true | 0..1 |
| `altcompb_to_a` | `xsd:int` | true | 0..1 |
| `fixo_a_lat` | `xsd:double` | true | 0..1 |
| `fixo_a_lon` | `xsd:double` | true | 0..1 |
| `fixo_b_lat` | `xsd:double` | true | 0..1 |
| `fixo_b_lon` | `xsd:double` | true | 0..1 |
| `eixokey` | `xsd:string` | true | 0..1 |
| `fixo_a_nome` | `xsd:string` | true | 0..1 |
| `fixo_b_nome` | `xsd:string` | true | 0..1 |
| `carta_nome` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:dateTime` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |

### `ICA:CV_REA_XR_VITORIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `fca` | `xsd:string` | true | 0..1 |
| `ats` | `xsd:string` | true | 0..1 |
| `semi_largura` | `xsd:double` | true | 0..1 |
| `rumoa_to_b` | `xsd:int` | true | 0..1 |
| `rumob_to_a` | `xsd:int` | true | 0..1 |
| `altmax` | `xsd:int` | true | 0..1 |
| `altmin` | `xsd:int` | true | 0..1 |
| `altcomp` | `xsd:int` | true | 0..1 |
| `altmaxa_to_b` | `xsd:int` | true | 0..1 |
| `altmina_to_b` | `xsd:int` | true | 0..1 |
| `altmaxb_to_a` | `xsd:int` | true | 0..1 |
| `altminb_to_a` | `xsd:int` | true | 0..1 |
| `altcompa_to_b` | `xsd:int` | true | 0..1 |
| `altcompb_to_a` | `xsd:int` | true | 0..1 |
| `fixo_a_lat` | `xsd:double` | true | 0..1 |
| `fixo_a_lon` | `xsd:double` | true | 0..1 |
| `fixo_b_lat` | `xsd:double` | true | 0..1 |
| `fixo_b_lon` | `xsd:double` | true | 0..1 |
| `eixokey` | `xsd:string` | true | 0..1 |
| `fixo_a_nome` | `xsd:string` | true | 0..1 |
| `fixo_b_nome` | `xsd:string` | true | 0..1 |
| `carta_nome` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:dateTime` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |

### `ICA:CV_REA_XS_SALVADOR`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `fca` | `xsd:string` | true | 0..1 |
| `ats` | `xsd:string` | true | 0..1 |
| `semi_largura` | `xsd:double` | true | 0..1 |
| `rumoa_to_b` | `xsd:int` | true | 0..1 |
| `rumob_to_a` | `xsd:int` | true | 0..1 |
| `altmax` | `xsd:int` | true | 0..1 |
| `altmin` | `xsd:int` | true | 0..1 |
| `altcomp` | `xsd:int` | true | 0..1 |
| `altmaxa_to_b` | `xsd:int` | true | 0..1 |
| `altmina_to_b` | `xsd:int` | true | 0..1 |
| `altmaxb_to_a` | `xsd:int` | true | 0..1 |
| `altminb_to_a` | `xsd:int` | true | 0..1 |
| `altcompa_to_b` | `xsd:int` | true | 0..1 |
| `altcompb_to_a` | `xsd:int` | true | 0..1 |
| `fixo_a_lat` | `xsd:double` | true | 0..1 |
| `fixo_a_lon` | `xsd:double` | true | 0..1 |
| `fixo_b_lat` | `xsd:double` | true | 0..1 |
| `fixo_b_lon` | `xsd:double` | true | 0..1 |
| `eixokey` | `xsd:string` | true | 0..1 |
| `fixo_a_nome` | `xsd:string` | true | 0..1 |
| `fixo_b_nome` | `xsd:string` | true | 0..1 |
| `carta_nome` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:dateTime` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |

### `ICA:CV_REA_XT_NATAL`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `fca` | `xsd:string` | true | 0..1 |
| `ats` | `xsd:string` | true | 0..1 |
| `semi_largura` | `xsd:double` | true | 0..1 |
| `rumoa_to_b` | `xsd:int` | true | 0..1 |
| `rumob_to_a` | `xsd:int` | true | 0..1 |
| `altmax` | `xsd:int` | true | 0..1 |
| `altmin` | `xsd:int` | true | 0..1 |
| `altcomp` | `xsd:int` | true | 0..1 |
| `altmaxa_to_b` | `xsd:int` | true | 0..1 |
| `altmina_to_b` | `xsd:int` | true | 0..1 |
| `altmaxb_to_a` | `xsd:int` | true | 0..1 |
| `altminb_to_a` | `xsd:int` | true | 0..1 |
| `altcompa_to_b` | `xsd:int` | true | 0..1 |
| `altcompb_to_a` | `xsd:int` | true | 0..1 |
| `fixo_a_lat` | `xsd:double` | true | 0..1 |
| `fixo_a_lon` | `xsd:double` | true | 0..1 |
| `fixo_b_lat` | `xsd:double` | true | 0..1 |
| `fixo_b_lon` | `xsd:double` | true | 0..1 |
| `eixokey` | `xsd:string` | true | 0..1 |
| `fixo_a_nome` | `xsd:string` | true | 0..1 |
| `fixo_b_nome` | `xsd:string` | true | 0..1 |
| `carta_nome` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:dateTime` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |

### `ICA:CV_REH_BR_COMPLETO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `fca` | `xsd:string` | true | 0..1 |
| `ats` | `xsd:string` | true | 0..1 |
| `semi_largura` | `xsd:double` | true | 0..1 |
| `rumoa_to_b` | `xsd:int` | true | 0..1 |
| `rumob_to_a` | `xsd:int` | true | 0..1 |
| `altmax` | `xsd:int` | true | 0..1 |
| `altmin` | `xsd:int` | true | 0..1 |
| `altcomp` | `xsd:int` | true | 0..1 |
| `altmaxa_to_b` | `xsd:int` | true | 0..1 |
| `altmina_to_b` | `xsd:int` | true | 0..1 |
| `altmaxb_to_a` | `xsd:int` | true | 0..1 |
| `altminb_to_a` | `xsd:int` | true | 0..1 |
| `altcompa_to_b` | `xsd:int` | true | 0..1 |
| `altcompb_to_a` | `xsd:int` | true | 0..1 |
| `fixo_a_lat` | `xsd:double` | true | 0..1 |
| `fixo_a_lon` | `xsd:double` | true | 0..1 |
| `fixo_b_lat` | `xsd:double` | true | 0..1 |
| `fixo_b_lon` | `xsd:double` | true | 0..1 |
| `eixokey` | `xsd:string` | true | 0..1 |
| `fixo_a_nome` | `xsd:string` | true | 0..1 |
| `fixo_b_nome` | `xsd:string` | true | 0..1 |
| `carta_nome` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:dateTime` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |

### `ICA:CV_REH_WJ2_RIO_DE_JANEIRO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `fca` | `xsd:string` | true | 0..1 |
| `ats` | `xsd:string` | true | 0..1 |
| `semi_largura` | `xsd:double` | true | 0..1 |
| `rumoa_to_b` | `xsd:int` | true | 0..1 |
| `rumob_to_a` | `xsd:int` | true | 0..1 |
| `altmax` | `xsd:int` | true | 0..1 |
| `altmin` | `xsd:int` | true | 0..1 |
| `altcomp` | `xsd:int` | true | 0..1 |
| `altmaxa_to_b` | `xsd:int` | true | 0..1 |
| `altmina_to_b` | `xsd:int` | true | 0..1 |
| `altmaxb_to_a` | `xsd:int` | true | 0..1 |
| `altminb_to_a` | `xsd:int` | true | 0..1 |
| `altcompa_to_b` | `xsd:int` | true | 0..1 |
| `altcompb_to_a` | `xsd:int` | true | 0..1 |
| `fixo_a_lat` | `xsd:double` | true | 0..1 |
| `fixo_a_lon` | `xsd:double` | true | 0..1 |
| `fixo_b_lat` | `xsd:double` | true | 0..1 |
| `fixo_b_lon` | `xsd:double` | true | 0..1 |
| `eixokey` | `xsd:string` | true | 0..1 |
| `fixo_a_nome` | `xsd:string` | true | 0..1 |
| `fixo_b_nome` | `xsd:string` | true | 0..1 |
| `carta_nome` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:dateTime` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |

### `ICA:CV_REH_XP_SAO_PAULO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `fca` | `xsd:string` | true | 0..1 |
| `ats` | `xsd:string` | true | 0..1 |
| `semi_largura` | `xsd:double` | true | 0..1 |
| `rumoa_to_b` | `xsd:int` | true | 0..1 |
| `rumob_to_a` | `xsd:int` | true | 0..1 |
| `altmax` | `xsd:int` | true | 0..1 |
| `altmin` | `xsd:int` | true | 0..1 |
| `altcomp` | `xsd:int` | true | 0..1 |
| `altmaxa_to_b` | `xsd:int` | true | 0..1 |
| `altmina_to_b` | `xsd:int` | true | 0..1 |
| `altmaxb_to_a` | `xsd:int` | true | 0..1 |
| `altminb_to_a` | `xsd:int` | true | 0..1 |
| `altcompa_to_b` | `xsd:int` | true | 0..1 |
| `altcompb_to_a` | `xsd:int` | true | 0..1 |
| `fixo_a_lat` | `xsd:double` | true | 0..1 |
| `fixo_a_lon` | `xsd:double` | true | 0..1 |
| `fixo_b_lat` | `xsd:double` | true | 0..1 |
| `fixo_b_lon` | `xsd:double` | true | 0..1 |
| `eixokey` | `xsd:string` | true | 0..1 |
| `fixo_a_nome` | `xsd:string` | true | 0..1 |
| `fixo_b_nome` | `xsd:string` | true | 0..1 |
| `carta_nome` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:dateTime` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |

### `ICA:CV_REH_XR_VITORIA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | false | 1..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `trecho` | `xsd:int` | true | 0..1 |
| `classe` | `xsd:string` | true | 0..1 |
| `fca` | `xsd:string` | true | 0..1 |
| `ats` | `xsd:string` | true | 0..1 |
| `semi_largura` | `xsd:double` | true | 0..1 |
| `rumoa_to_b` | `xsd:int` | true | 0..1 |
| `rumob_to_a` | `xsd:int` | true | 0..1 |
| `altmax` | `xsd:int` | true | 0..1 |
| `altmin` | `xsd:int` | true | 0..1 |
| `altcomp` | `xsd:int` | true | 0..1 |
| `altmaxa_to_b` | `xsd:int` | true | 0..1 |
| `altmina_to_b` | `xsd:int` | true | 0..1 |
| `altmaxb_to_a` | `xsd:int` | true | 0..1 |
| `altminb_to_a` | `xsd:int` | true | 0..1 |
| `altcompa_to_b` | `xsd:int` | true | 0..1 |
| `altcompb_to_a` | `xsd:int` | true | 0..1 |
| `fixo_a_lat` | `xsd:double` | true | 0..1 |
| `fixo_a_lon` | `xsd:double` | true | 0..1 |
| `fixo_b_lat` | `xsd:double` | true | 0..1 |
| `fixo_b_lon` | `xsd:double` | true | 0..1 |
| `eixokey` | `xsd:string` | true | 0..1 |
| `fixo_a_nome` | `xsd:string` | true | 0..1 |
| `fixo_b_nome` | `xsd:string` | true | 0..1 |
| `carta_nome` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:dateTime` | true | 0..1 |
| `identificador` | `xsd:string` | true | 0..1 |

### `ICA:dme`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `dme_pk` | `xsd:decimal` | true | 0..1 |
| `effectived` | `xsd:date` | true | 0..1 |
| `valchannel` | `xsd:decimal` | true | 0..1 |
| `codeid` | `xsd:string` | true | 0..1 |
| `geolat` | `xsd:decimal` | true | 0..1 |
| `geolong` | `xsd:decimal` | true | 0..1 |
| `codetype` | `xsd:string` | true | 0..1 |
| `valghostfr` | `xsd:decimal` | true | 0..1 |
| `uomghostfr` | `xsd:string` | true | 0..1 |
| `valdisplac` | `xsd:decimal` | true | 0..1 |
| `uomdisplac` | `xsd:string` | true | 0..1 |
| `txtname` | `xsd:string` | true | 0..1 |
| `codeem` | `xsd:string` | true | 0..1 |
| `codedatum` | `xsd:string` | true | 0..1 |
| `valgeoaccu` | `xsd:decimal` | true | 0..1 |
| `uomgeoaccu` | `xsd:string` | true | 0..1 |
| `valelev` | `xsd:decimal` | true | 0..1 |
| `valelevacc` | `xsd:decimal` | true | 0..1 |
| `valgeoidun` | `xsd:decimal` | true | 0..1 |
| `valcrc` | `xsd:string` | true | 0..1 |
| `txtverdatu` | `xsd:string` | true | 0..1 |
| `codeworkhr` | `xsd:string` | true | 0..1 |
| `orgauth_pk` | `xsd:decimal` | true | 0..1 |
| `txtrmkwork` | `xsd:string` | true | 0..1 |
| `txtrmk` | `xsd:string` | true | 0..1 |
| `areacode` | `xsd:string` | true | 0..1 |
| `airspace_p` | `xsd:decimal` | true | 0..1 |
| `airspace_1` | `xsd:decimal` | true | 0..1 |
| `icaocode` | `xsd:string` | true | 0..1 |
| `class3` | `xsd:string` | true | 0..1 |
| `class5` | `xsd:string` | true | 0..1 |
| `facchar5` | `xsd:string` | true | 0..1 |
| `codechanne` | `xsd:string` | true | 0..1 |
| `valdeclina` | `xsd:decimal` | true | 0..1 |
| `elevationu` | `xsd:string` | true | 0..1 |
| `vertaccuom` | `xsd:string` | true | 0..1 |
| `geoidundul` | `xsd:string` | true | 0..1 |
| `mobile` | `xsd:string` | true | 0..1 |
| `magneticva` | `xsd:decimal` | true | 0..1 |
| `magvaracc` | `xsd:decimal` | true | 0..1 |
| `datemagvar` | `xsd:date` | true | 0..1 |
| `flightchec` | `xsd:string` | true | 0..1 |
| `txtrmk_lcl` | `xsd:string` | true | 0..1 |
| `bltype` | `xsd:string` | true | 0..1 |
| `purpose` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `emenda` | `xsd:date` | true | 0..1 |
| `emenda_futura` | `xsd:date` | true | 0..1 |
| `latitude_gms` | `xsd:string` | true | 0..1 |
| `longitude_gms` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |

### `ICA:eac_d`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `pk` | `xsd:decimal` | true | 0..1 |
| `efetivacao` | `xsd:date` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `id` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `uom_ulimit` | `xsd:string` | true | 0..1 |
| `uom_llimit` | `xsd:string` | true | 0..1 |
| `upperlimit` | `xsd:decimal` | true | 0..1 |
| `lowerlimit` | `xsd:decimal` | true | 0..1 |
| `perigo` | `xsd:string` | true | 0..1 |
| `observacao` | `xsd:string` | true | 0..1 |
| `designador` | `xsd:string` | true | 0..1 |
| `fir` | `xsd:string` | true | 0..1 |
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |

### `ICA:eac_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `pk` | `xsd:decimal` | true | 0..1 |
| `efetivacao` | `xsd:date` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `id` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `uom_ulimit` | `xsd:string` | true | 0..1 |
| `uom_llimit` | `xsd:string` | true | 0..1 |
| `upperlimit` | `xsd:decimal` | true | 0..1 |
| `lowerlimit` | `xsd:decimal` | true | 0..1 |
| `perigo` | `xsd:string` | true | 0..1 |
| `observacao` | `xsd:string` | true | 0..1 |
| `designador` | `xsd:string` | true | 0..1 |
| `fir` | `xsd:string` | true | 0..1 |
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |

### `ICA:eac_r`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `pk` | `xsd:decimal` | true | 0..1 |
| `efetivacao` | `xsd:date` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `id` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `uom_ulimit` | `xsd:string` | true | 0..1 |
| `uom_llimit` | `xsd:string` | true | 0..1 |
| `upperlimit` | `xsd:decimal` | true | 0..1 |
| `lowerlimit` | `xsd:decimal` | true | 0..1 |
| `perigo` | `xsd:string` | true | 0..1 |
| `observacao` | `xsd:string` | true | 0..1 |
| `designador` | `xsd:string` | true | 0..1 |
| `fir` | `xsd:string` | true | 0..1 |
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |

### `ICA:fir`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `airspace_p` | `xsd:decimal` | true | 0..1 |
| `effectived` | `xsd:date` | true | 0..1 |
| `typ` | `xsd:string` | true | 0..1 |
| `ident` | `xsd:string` | true | 0..1 |
| `icaocode` | `xsd:string` | true | 0..1 |
| `nam` | `xsd:string` | true | 0..1 |
| `areacode` | `xsd:string` | true | 0..1 |
| `codedistve` | `xsd:string` | true | 0..1 |
| `uplimituni` | `xsd:string` | true | 0..1 |
| `codedistv1` | `xsd:string` | true | 0..1 |
| `lowerlimit` | `xsd:string` | true | 0..1 |
| `uomdistver` | `xsd:string` | true | 0..1 |
| `codewrkhr` | `xsd:string` | true | 0..1 |
| `upperlimit` | `xsd:decimal` | true | 0..1 |
| `lowerlimi1` | `xsd:decimal` | true | 0..1 |
| `entryrpt` | `xsd:string` | true | 0..1 |
| `txtlocalty` | `xsd:string` | true | 0..1 |
| `txtrmk_loc` | `xsd:string` | true | 0..1 |
| `classrmklo` | `xsd:string` | true | 0..1 |
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |
| `emenda` | `xsd:date` | true | 0..1 |
| `emenda_futura` | `xsd:date` | true | 0..1 |

### `ICA:fis`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:long` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `codewrkhr` | `xsd:string` | true | 0..1 |
| `airspace_p` | `xsd:int` | true | 0..1 |
| `typ` | `xsd:string` | true | 0..1 |
| `ident` | `xsd:string` | true | 0..1 |
| `icaocode` | `xsd:string` | true | 0..1 |
| `nam` | `xsd:string` | true | 0..1 |
| `areacode` | `xsd:string` | true | 0..1 |
| `codedistve` | `xsd:string` | true | 0..1 |
| `uomdistver` | `xsd:string` | true | 0..1 |
| `entryrpt` | `xsd:string` | true | 0..1 |
| `txtlocalty` | `xsd:string` | true | 0..1 |
| `relatedfir` | `xsd:string` | true | 0..1 |
| `classrmklo` | `xsd:string` | true | 0..1 |
| `txtrmk_loc` | `xsd:string` | true | 0..1 |
| `uplimituni` | `xsd:string` | true | 0..1 |
| `lowerlimit` | `xsd:string` | true | 0..1 |
| `lowerlimi1` | `xsd:int` | true | 0..1 |
| `upperlimit` | `xsd:int` | true | 0..1 |
| `codedistv1` | `xsd:string` | true | 0..1 |
| `effectived` | `xsd:date` | true | 0..1 |
| `emenda` | `xsd:date` | true | 0..1 |
| `emenda_futura` | `xsd:date` | true | 0..1 |

### `ICA:fiz`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `airspace_p` | `xsd:decimal` | true | 0..1 |
| `effectived` | `xsd:date` | true | 0..1 |
| `typ` | `xsd:string` | true | 0..1 |
| `ident` | `xsd:string` | true | 0..1 |
| `icaocode` | `xsd:string` | true | 0..1 |
| `nam` | `xsd:string` | true | 0..1 |
| `areacode` | `xsd:string` | true | 0..1 |
| `codedistve` | `xsd:string` | true | 0..1 |
| `uplimituni` | `xsd:string` | true | 0..1 |
| `codedistv1` | `xsd:string` | true | 0..1 |
| `lowerlimit` | `xsd:string` | true | 0..1 |
| `uomdistver` | `xsd:string` | true | 0..1 |
| `codewrkhr` | `xsd:string` | true | 0..1 |
| `upperlimit` | `xsd:decimal` | true | 0..1 |
| `lowerlimi1` | `xsd:decimal` | true | 0..1 |
| `entryrpt` | `xsd:string` | true | 0..1 |
| `txtlocalty` | `xsd:string` | true | 0..1 |
| `txtrmk_loc` | `xsd:string` | true | 0..1 |
| `relatedfir` | `xsd:string` | true | 0..1 |
| `classrmklo` | `xsd:string` | true | 0..1 |
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |
| `emenda` | `xsd:date` | true | 0..1 |
| `emenda_futura` | `xsd:date` | true | 0..1 |

### `ICA:heliport`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `id` | `xsd:string` | true | 0..1 |
| `ciad` | `xsd:string` | true | 0..1 |
| `localidade_id` | `xsd:string` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `efetivacao` | `xsd:date` | true | 0..1 |
| `fir` | `xsd:string` | true | 0..1 |
| `jurisdicao` | `xsd:string` | true | 0..1 |
| `latitude_dec` | `xsd:double` | true | 0..1 |
| `longitude_dec` | `xsd:double` | true | 0..1 |
| `latitude` | `xsd:string` | true | 0..1 |
| `longitude` | `xsd:string` | true | 0..1 |
| `elevacao` | `xsd:double` | true | 0..1 |
| `elev_uom` | `xsd:string` | true | 0..1 |
| `tipo_util` | `xsd:string` | true | 0..1 |
| `cat_sigla` | `xsd:string` | true | 0..1 |
| `opr` | `xsd:string` | true | 0..1 |
| `wh` | `xsd:string` | true | 0..1 |
| `cidade` | `xsd:string` | true | 0..1 |
| `uf` | `xsd:string` | true | 0..1 |
| `utc` | `xsd:string` | true | 0..1 |
| `emenda_n` | `xsd:string` | true | 0..1 |
| `emenda` | `xsd:date` | true | 0..1 |
| `airport_pk` | `xsd:decimal` | true | 0..1 |

### `ICA:MAP_ARC_OTHER`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `airspace_p` | `xsd:decimal` | true | 0..1 |
| `effectived` | `xsd:date` | true | 0..1 |
| `typ` | `xsd:string` | true | 0..1 |
| `ident` | `xsd:string` | true | 0..1 |
| `icaocode` | `xsd:string` | true | 0..1 |
| `nam` | `xsd:string` | true | 0..1 |
| `areacode` | `xsd:string` | true | 0..1 |
| `codedistve` | `xsd:string` | true | 0..1 |
| `uplimituni` | `xsd:string` | true | 0..1 |
| `codedistv1` | `xsd:string` | true | 0..1 |
| `lowerlimit` | `xsd:string` | true | 0..1 |
| `uomdistver` | `xsd:string` | true | 0..1 |
| `codewrkhr` | `xsd:string` | true | 0..1 |
| `upperlimit` | `xsd:decimal` | true | 0..1 |
| `lowerlimi1` | `xsd:decimal` | true | 0..1 |
| `entryrpt` | `xsd:string` | true | 0..1 |
| `txtlocalty` | `xsd:string` | true | 0..1 |
| `txtrmk_loc` | `xsd:string` | true | 0..1 |
| `relatedfir` | `xsd:string` | true | 0..1 |
| `classrmklo` | `xsd:string` | true | 0..1 |
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |

### `ICA:MAP_ENRCH_OTHER`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `airspace_p` | `xsd:decimal` | true | 0..1 |
| `effectived` | `xsd:date` | true | 0..1 |
| `typ` | `xsd:string` | true | 0..1 |
| `ident` | `xsd:string` | true | 0..1 |
| `icaocode` | `xsd:string` | true | 0..1 |
| `nam` | `xsd:string` | true | 0..1 |
| `areacode` | `xsd:string` | true | 0..1 |
| `codedistve` | `xsd:string` | true | 0..1 |
| `uplimituni` | `xsd:string` | true | 0..1 |
| `codedistv1` | `xsd:string` | true | 0..1 |
| `lowerlimit` | `xsd:string` | true | 0..1 |
| `uomdistver` | `xsd:string` | true | 0..1 |
| `codewrkhr` | `xsd:string` | true | 0..1 |
| `upperlimit` | `xsd:decimal` | true | 0..1 |
| `lowerlimi1` | `xsd:decimal` | true | 0..1 |
| `entryrpt` | `xsd:string` | true | 0..1 |
| `txtlocalty` | `xsd:string` | true | 0..1 |
| `txtrmk_loc` | `xsd:string` | true | 0..1 |
| `relatedfir` | `xsd:string` | true | 0..1 |
| `classrmklo` | `xsd:string` | true | 0..1 |
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |

### `ICA:MAP_ENRCL_OTHER`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `airspace_p` | `xsd:decimal` | true | 0..1 |
| `effectived` | `xsd:date` | true | 0..1 |
| `typ` | `xsd:string` | true | 0..1 |
| `ident` | `xsd:string` | true | 0..1 |
| `icaocode` | `xsd:string` | true | 0..1 |
| `nam` | `xsd:string` | true | 0..1 |
| `areacode` | `xsd:string` | true | 0..1 |
| `codedistve` | `xsd:string` | true | 0..1 |
| `uplimituni` | `xsd:string` | true | 0..1 |
| `codedistv1` | `xsd:string` | true | 0..1 |
| `lowerlimit` | `xsd:string` | true | 0..1 |
| `uomdistver` | `xsd:string` | true | 0..1 |
| `codewrkhr` | `xsd:string` | true | 0..1 |
| `upperlimit` | `xsd:decimal` | true | 0..1 |
| `lowerlimi1` | `xsd:decimal` | true | 0..1 |
| `entryrpt` | `xsd:string` | true | 0..1 |
| `txtlocalty` | `xsd:string` | true | 0..1 |
| `txtrmk_loc` | `xsd:string` | true | 0..1 |
| `relatedfir` | `xsd:string` | true | 0..1 |
| `classrmklo` | `xsd:string` | true | 0..1 |
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |

### `ICA:navaids`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `navaids_pk` | `xsd:decimal` | true | 0..1 |
| `effectived` | `xsd:date` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `designator` | `xsd:string` | true | 0..1 |
| `flightchec` | `xsd:string` | true | 0..1 |
| `purpose` | `xsd:string` | true | 0..1 |
| `signalperf` | `xsd:string` | true | 0..1 |
| `coursequal` | `xsd:string` | true | 0..1 |
| `integrityl` | `xsd:string` | true | 0..1 |
| `elevation` | `xsd:decimal` | true | 0..1 |
| `elevationu` | `xsd:string` | true | 0..1 |
| `geoidundul` | `xsd:decimal` | true | 0..1 |
| `geoidundu1` | `xsd:string` | true | 0..1 |
| `verticalda` | `xsd:string` | true | 0..1 |
| `verticalac` | `xsd:decimal` | true | 0..1 |
| `vertaccuom` | `xsd:string` | true | 0..1 |
| `haccuracy` | `xsd:decimal` | true | 0..1 |
| `haccuracyu` | `xsd:string` | true | 0..1 |
| `txtrmk` | `xsd:string` | true | 0..1 |
| `airport_pk` | `xsd:decimal` | true | 0..1 |
| `rwydirecti` | `xsd:decimal` | true | 0..1 |
| `tlof_pk` | `xsd:decimal` | true | 0..1 |
| `latitude` | `xsd:decimal` | true | 0..1 |
| `longitude` | `xsd:decimal` | true | 0..1 |
| `bltype` | `xsd:string` | true | 0..1 |
| `codedatum` | `xsd:string` | true | 0..1 |
| `originalla` | `xsd:decimal` | true | 0..1 |
| `originallo` | `xsd:decimal` | true | 0..1 |
| `originalsr` | `xsd:string` | true | 0..1 |
| `originalel` | `xsd:decimal` | true | 0..1 |
| `originale1` | `xsd:string` | true | 0..1 |
| `geoidrefsy` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `emenda` | `xsd:date` | true | 0..1 |
| `emenda_futura` | `xsd:date` | true | 0..1 |
| `latitude_gms` | `xsd:string` | true | 0..1 |
| `longitude_gms` | `xsd:string` | true | 0..1 |

### `ICA:ndb`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `ndb_pk` | `xsd:decimal` | true | 0..1 |
| `effectived` | `xsd:date` | true | 0..1 |
| `codeid` | `xsd:string` | true | 0..1 |
| `geolat` | `xsd:decimal` | true | 0..1 |
| `geolong` | `xsd:decimal` | true | 0..1 |
| `txtname` | `xsd:string` | true | 0..1 |
| `valfreq` | `xsd:decimal` | true | 0..1 |
| `uomfreq` | `xsd:string` | true | 0..1 |
| `codeclass` | `xsd:string` | true | 0..1 |
| `codepsnils` | `xsd:string` | true | 0..1 |
| `valmagvar` | `xsd:decimal` | true | 0..1 |
| `datemagvar` | `xsd:date` | true | 0..1 |
| `codeem` | `xsd:string` | true | 0..1 |
| `codedatum` | `xsd:string` | true | 0..1 |
| `valgeoaccu` | `xsd:decimal` | true | 0..1 |
| `uomgeoaccu` | `xsd:string` | true | 0..1 |
| `valelev` | `xsd:decimal` | true | 0..1 |
| `valelevacc` | `xsd:decimal` | true | 0..1 |
| `valgeoidun` | `xsd:decimal` | true | 0..1 |
| `valcrc` | `xsd:string` | true | 0..1 |
| `txtverdatu` | `xsd:string` | true | 0..1 |
| `codeworkhr` | `xsd:string` | true | 0..1 |
| `txtrmkwork` | `xsd:string` | true | 0..1 |
| `txtrmk` | `xsd:string` | true | 0..1 |
| `areacode` | `xsd:string` | true | 0..1 |
| `icaocode` | `xsd:string` | true | 0..1 |
| `airspace_p` | `xsd:decimal` | true | 0..1 |
| `airspace_1` | `xsd:decimal` | true | 0..1 |
| `orgauth_pk` | `xsd:decimal` | true | 0..1 |
| `dme_pk` | `xsd:decimal` | true | 0..1 |
| `class1` | `xsd:string` | true | 0..1 |
| `class3` | `xsd:string` | true | 0..1 |
| `class4` | `xsd:string` | true | 0..1 |
| `class5` | `xsd:string` | true | 0..1 |
| `facchar3` | `xsd:string` | true | 0..1 |
| `facchar4` | `xsd:string` | true | 0..1 |
| `facchar5` | `xsd:decimal` | true | 0..1 |
| `valdeclina` | `xsd:decimal` | true | 0..1 |
| `txtrmk_lcl` | `xsd:string` | true | 0..1 |
| `facchar2` | `xsd:string` | true | 0..1 |
| `elevationu` | `xsd:string` | true | 0..1 |
| `vertaccuom` | `xsd:string` | true | 0..1 |
| `geoidundul` | `xsd:string` | true | 0..1 |
| `emissionba` | `xsd:string` | true | 0..1 |
| `mobile` | `xsd:string` | true | 0..1 |
| `magvaracc` | `xsd:decimal` | true | 0..1 |
| `flightchec` | `xsd:string` | true | 0..1 |
| `txtrmkwor1` | `xsd:string` | true | 0..1 |
| `bltype` | `xsd:string` | true | 0..1 |
| `rotaer_rmk` | `xsd:string` | true | 0..1 |
| `rwyremark` | `xsd:string` | true | 0..1 |
| `purpose` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `emenda` | `xsd:date` | true | 0..1 |
| `emenda_futura` | `xsd:date` | true | 0..1 |
| `latitude_gms` | `xsd:string` | true | 0..1 |
| `longitude_gms` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |

### `ICA:opea`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:string` | true | 0..1 |
| `aixm_code` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `altitude_topo` | `xsd:double` | true | 0..1 |
| `altitude_base` | `xsd:double` | true | 0..1 |
| `altura` | `xsd:double` | true | 0..1 |
| `iluminado` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `ads_impactados` | `xsd:string` | true | 0..1 |
| `data_atualizacao` | `xsd:date` | true | 0..1 |

### `ICA:rotas_diretas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `airspace_p` | `xsd:decimal` | true | 0..1 |
| `ident` | `xsd:string` | true | 0..1 |
| `uplimituni` | `xsd:string` | true | 0..1 |
| `lowerlimit` | `xsd:string` | true | 0..1 |
| `txtrmk` | `xsd:string` | true | 0..1 |
| `codewrkhr` | `xsd:string` | true | 0..1 |
| `codeclass` | `xsd:string` | true | 0..1 |
| `upperlimit` | `xsd:decimal` | true | 0..1 |
| `lowerlimi1` | `xsd:decimal` | true | 0..1 |
| `txtlocalty` | `xsd:string` | true | 0..1 |

### `ICA:runway`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `runway_pk` | `xsd:decimal` | true | 0..1 |
| `effectived` | `xsd:date` | true | 0..1 |
| `airport_pk` | `xsd:decimal` | true | 0..1 |
| `ident` | `xsd:string` | true | 0..1 |
| `runwayleng` | `xsd:decimal` | true | 0..1 |
| `width` | `xsd:decimal` | true | 0..1 |
| `codecondsf` | `xsd:string` | true | 0..1 |
| `surface` | `xsd:string` | true | 0..1 |
| `rwydesc` | `xsd:string` | true | 0..1 |
| `rwystrengt` | `xsd:string` | true | 0..1 |
| `descrstren` | `xsd:string` | true | 0..1 |
| `lenstrip` | `xsd:decimal` | true | 0..1 |
| `widstrip` | `xsd:decimal` | true | 0..1 |
| `lenoffset` | `xsd:decimal` | true | 0..1 |
| `widoffset` | `xsd:decimal` | true | 0..1 |
| `codests` | `xsd:string` | true | 0..1 |
| `txtprofile` | `xsd:string` | true | 0..1 |
| `txtmarking` | `xsd:string` | true | 0..1 |
| `txtrmk` | `xsd:string` | true | 0..1 |
| `txtrmk_lcl` | `xsd:string` | true | 0..1 |
| `rwydesc_lc` | `xsd:string` | true | 0..1 |
| `txtprofil1` | `xsd:string` | true | 0..1 |
| `txtmarkin1` | `xsd:string` | true | 0..1 |
| `valcrc` | `xsd:string` | true | 0..1 |
| `auwweight` | `xsd:decimal` | true | 0..1 |
| `codepcnmax` | `xsd:string` | true | 0..1 |
| `lcnclass` | `xsd:decimal` | true | 0..1 |
| `pcnclass` | `xsd:decimal` | true | 0..1 |
| `pcnevalmet` | `xsd:string` | true | 0..1 |
| `pcnnote` | `xsd:string` | true | 0..1 |
| `pcnpavemen` | `xsd:string` | true | 0..1 |
| `pcnpaveme1` | `xsd:string` | true | 0..1 |
| `preparatio` | `xsd:string` | true | 0..1 |
| `siwltirepr` | `xsd:decimal` | true | 0..1 |
| `siwlweight` | `xsd:decimal` | true | 0..1 |
| `uomauwweig` | `xsd:string` | true | 0..1 |
| `uomsiwltir` | `xsd:string` | true | 0..1 |
| `uomsiwlwei` | `xsd:string` | true | 0..1 |
| `valpcnmaxt` | `xsd:decimal` | true | 0..1 |
| `lengthoffs` | `xsd:string` | true | 0..1 |
| `lengthstri` | `xsd:string` | true | 0..1 |
| `nominallen` | `xsd:string` | true | 0..1 |
| `lengthaccu` | `xsd:decimal` | true | 0..1 |
| `widthoffse` | `xsd:string` | true | 0..1 |
| `widthstrip` | `xsd:string` | true | 0..1 |
| `nominalwid` | `xsd:string` | true | 0..1 |
| `widthaccur` | `xsd:decimal` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `abandoned` | `xsd:string` | true | 0..1 |
| `widthshoul` | `xsd:decimal` | true | 0..1 |
| `widthshou1` | `xsd:string` | true | 0..1 |
| `light_desc` | `xsd:string` | true | 0..1 |
| `bltype` | `xsd:string` | true | 0..1 |
| `lengthacc1` | `xsd:string` | true | 0..1 |
| `widthaccu1` | `xsd:string` | true | 0..1 |
| `codenumber` | `xsd:string` | true | 0..1 |
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |
| `emenda` | `xsd:date` | true | 0..1 |
| `emenda_futura` | `xsd:date` | true | 0..1 |

### `ICA:runway_v2`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `runway_pk` | `xsd:decimal` | true | 0..1 |
| `effectived` | `xsd:date` | true | 0..1 |
| `airport_pk` | `xsd:decimal` | true | 0..1 |
| `ident` | `xsd:string` | true | 0..1 |
| `runwayleng` | `xsd:decimal` | true | 0..1 |
| `width` | `xsd:decimal` | true | 0..1 |
| `codecondsf` | `xsd:string` | true | 0..1 |
| `surface` | `xsd:string` | true | 0..1 |
| `rwydesc` | `xsd:string` | true | 0..1 |
| `rwystrengt` | `xsd:string` | true | 0..1 |
| `descrstren` | `xsd:string` | true | 0..1 |
| `lenstrip` | `xsd:decimal` | true | 0..1 |
| `widstrip` | `xsd:decimal` | true | 0..1 |
| `lenoffset` | `xsd:decimal` | true | 0..1 |
| `widoffset` | `xsd:decimal` | true | 0..1 |
| `codests` | `xsd:string` | true | 0..1 |
| `txtprofile` | `xsd:string` | true | 0..1 |
| `txtmarking` | `xsd:string` | true | 0..1 |
| `txtrmk` | `xsd:string` | true | 0..1 |
| `txtrmk_lcl` | `xsd:string` | true | 0..1 |
| `rwydesc_lc` | `xsd:string` | true | 0..1 |
| `txtprofil1` | `xsd:string` | true | 0..1 |
| `txtmarkin1` | `xsd:string` | true | 0..1 |
| `valcrc` | `xsd:string` | true | 0..1 |
| `auwweight` | `xsd:decimal` | true | 0..1 |
| `codepcnmax` | `xsd:string` | true | 0..1 |
| `lcnclass` | `xsd:decimal` | true | 0..1 |
| `pcnclass` | `xsd:decimal` | true | 0..1 |
| `pcnevalmet` | `xsd:string` | true | 0..1 |
| `pcnnote` | `xsd:string` | true | 0..1 |
| `pcnpavemen` | `xsd:string` | true | 0..1 |
| `pcnpaveme1` | `xsd:string` | true | 0..1 |
| `preparatio` | `xsd:string` | true | 0..1 |
| `siwltirepr` | `xsd:decimal` | true | 0..1 |
| `siwlweight` | `xsd:decimal` | true | 0..1 |
| `uomauwweig` | `xsd:string` | true | 0..1 |
| `uomsiwltir` | `xsd:string` | true | 0..1 |
| `uomsiwlwei` | `xsd:string` | true | 0..1 |
| `valpcnmaxt` | `xsd:decimal` | true | 0..1 |
| `lengthoffs` | `xsd:string` | true | 0..1 |
| `lengthstri` | `xsd:string` | true | 0..1 |
| `nominallen` | `xsd:string` | true | 0..1 |
| `lengthaccu` | `xsd:decimal` | true | 0..1 |
| `widthoffse` | `xsd:string` | true | 0..1 |
| `widthstrip` | `xsd:string` | true | 0..1 |
| `nominalwid` | `xsd:string` | true | 0..1 |
| `widthaccur` | `xsd:decimal` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `abandoned` | `xsd:string` | true | 0..1 |
| `widthshoul` | `xsd:decimal` | true | 0..1 |
| `widthshou1` | `xsd:string` | true | 0..1 |
| `light_desc` | `xsd:string` | true | 0..1 |
| `bltype` | `xsd:string` | true | 0..1 |
| `lengthacc1` | `xsd:string` | true | 0..1 |
| `widthaccu1` | `xsd:string` | true | 0..1 |
| `codenumber` | `xsd:string` | true | 0..1 |
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |
| `emenda` | `xsd:date` | true | 0..1 |
| `emenda_futura` | `xsd:date` | true | 0..1 |

### `ICA:rwydirection`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `fid` | `xsd:int` | true | 0..1 |
| `gid` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `rwydirecti` | `xsd:decimal` | true | 0..1 |
| `effectived` | `xsd:date` | true | 0..1 |
| `runway_pk` | `xsd:decimal` | true | 0..1 |
| `rwyendid` | `xsd:string` | true | 0..1 |
| `truebrg` | `xsd:decimal` | true | 0..1 |
| `truebrgsrc` | `xsd:string` | true | 0..1 |
| `magbrg` | `xsd:decimal` | true | 0..1 |
| `threshlat` | `xsd:decimal` | true | 0..1 |
| `threshlon` | `xsd:decimal` | true | 0..1 |
| `codedatum` | `xsd:string` | true | 0..1 |
| `valgeoaccu` | `xsd:decimal` | true | 0..1 |
| `uomgeoaccu` | `xsd:string` | true | 0..1 |
| `elevaccura` | `xsd:decimal` | true | 0..1 |
| `geoidundul` | `xsd:decimal` | true | 0..1 |
| `uomdistver` | `xsd:string` | true | 0..1 |
| `valcrc` | `xsd:string` | true | 0..1 |
| `verdatum` | `xsd:string` | true | 0..1 |
| `gradient` | `xsd:decimal` | true | 0..1 |
| `tdzelevloc` | `xsd:string` | true | 0..1 |
| `tdzelev` | `xsd:decimal` | true | 0..1 |
| `threshelev` | `xsd:decimal` | true | 0..1 |
| `elevtdzacc` | `xsd:decimal` | true | 0..1 |
| `tch` | `xsd:decimal` | true | 0..1 |
| `vasis` | `xsd:string` | true | 0..1 |
| `vasisangle` | `xsd:decimal` | true | 0..1 |
| `durtax` | `xsd:decimal` | true | 0..1 |
| `descrpsnva` | `xsd:string` | true | 0..1 |
| `meht` | `xsd:decimal` | true | 0..1 |
| `uommeht` | `xsd:string` | true | 0..1 |
| `descrarstd` | `xsd:string` | true | 0..1 |
| `descrrvr` | `xsd:string` | true | 0..1 |
| `vfrpattern` | `xsd:string` | true | 0..1 |
| `txtrmk` | `xsd:string` | true | 0..1 |
| `uomtch` | `xsd:string` | true | 0..1 |
| `descrpsnv1` | `xsd:string` | true | 0..1 |
| `txtrmk_lcl` | `xsd:string` | true | 0..1 |
| `codeportab` | `xsd:string` | true | 0..1 |
| `codepsnvas` | `xsd:string` | true | 0..1 |
| `noboxvasis` | `xsd:decimal` | true | 0..1 |
| `elevtdzac1` | `xsd:string` | true | 0..1 |
| `elevationt` | `xsd:string` | true | 0..1 |
| `truebearin` | `xsd:decimal` | true | 0..1 |
| `slopetdz` | `xsd:decimal` | true | 0..1 |
| `apprmarkin` | `xsd:string` | true | 0..1 |
| `apprmarki1` | `xsd:string` | true | 0..1 |
| `classlight` | `xsd:string` | true | 0..1 |
| `precapproc` | `xsd:string` | true | 0..1 |
| `rwyelement` | `xsd:decimal` | true | 0..1 |
| `rmk_light_` | `xsd:string` | true | 0..1 |
| `rmk_light1` | `xsd:string` | true | 0..1 |
| `light_desc` | `xsd:string` | true | 0..1 |
| `gradientrm` | `xsd:string` | true | 0..1 |
| `bltype` | `xsd:string` | true | 0..1 |
| `geoiduom` | `xsd:string` | true | 0..1 |
| `vertaccuom` | `xsd:string` | true | 0..1 |
| `originalla` | `xsd:decimal` | true | 0..1 |
| `originallo` | `xsd:decimal` | true | 0..1 |
| `originalsr` | `xsd:string` | true | 0..1 |
| `originalel` | `xsd:decimal` | true | 0..1 |
| `originale1` | `xsd:string` | true | 0..1 |
| `geoidrefsy` | `xsd:string` | true | 0..1 |
| `emergencyl` | `xsd:string` | true | 0..1 |
| `codeintst` | `xsd:string` | true | 0..1 |
| `codecolour` | `xsd:string` | true | 0..1 |
| `emenda` | `xsd:date` | true | 0..1 |
| `emenda_futura` | `xsd:date` | true | 0..1 |

### `ICA:SBAN_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `perimeter` | `xsd:string` | true | 0..1 |
| `enclosed_a` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBAN_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `layer` | `xsd:string` | true | 0..1 |
| `elevation` | `xsd:double` | true | 0..1 |
| `map_name` | `xsd:string` | true | 0..1 |
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `line_style` | `xsd:string` | true | 0..1 |
| `line_color` | `xsd:string` | true | 0..1 |
| `line_width` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBAN_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBAN_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBAN_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `layer` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBAN_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBAN_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBAN_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBAR_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBAR_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBAR_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `making` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBAR_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBAR_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBAR_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBAR_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `making` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBAR_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBBE_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `LAYER` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBBE_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBBE_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBBE_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBBE_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `OBJECTID` | `xsd:double` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBBE_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBBE_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBBE_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBBR_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `idosbt` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hsttderv` | `xsd:string` | true | 0..1 |
| `hbias` | `xsd:double` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vsttderv` | `xsd:string` | true | 0..1 |
| `vbias` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `revtime` | `xsd:date` | true | 0..1 |
| `efstdate` | `xsd:date` | true | 0..1 |
| `efsttime` | `xsd:date` | true | 0..1 |
| `efendate` | `xsd:date` | true | 0..1 |
| `efentime` | `xsd:date` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |
| `integridad` | `xsd:string` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `uu_id` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBBR_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `objectid` | `xsd:int` | true | 0..1 |
| `idosbt` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hsttderv` | `xsd:string` | true | 0..1 |
| `hbias` | `xsd:double` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vsttderv` | `xsd:string` | true | 0..1 |
| `vbias` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `revtime` | `xsd:date` | true | 0..1 |
| `efstdate` | `xsd:date` | true | 0..1 |
| `efsttime` | `xsd:date` | true | 0..1 |
| `efendate` | `xsd:date` | true | 0..1 |
| `efentime` | `xsd:date` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |
| `shape_area` | `xsd:decimal` | true | 0..1 |
| `integridad` | `xsd:string` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `uu_id` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBBR_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `objectid` | `xsd:int` | true | 0..1 |
| `idosbt` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hsttderv` | `xsd:string` | true | 0..1 |
| `hbias` | `xsd:double` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vsttderv` | `xsd:string` | true | 0..1 |
| `vbias` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `revtime` | `xsd:date` | true | 0..1 |
| `efstdate` | `xsd:date` | true | 0..1 |
| `efsttime` | `xsd:date` | true | 0..1 |
| `efendate` | `xsd:date` | true | 0..1 |
| `efentime` | `xsd:date` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `integridad` | `xsd:string` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `uu_id` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBBR_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `objectid` | `xsd:int` | true | 0..1 |
| `idosbt` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `source` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hsttderv` | `xsd:string` | true | 0..1 |
| `hbias` | `xsd:double` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vsttderv` | `xsd:string` | true | 0..1 |
| `vbias` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `integr` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `revtime` | `xsd:date` | true | 0..1 |
| `efstdate` | `xsd:date` | true | 0..1 |
| `efsttime` | `xsd:date` | true | 0..1 |
| `efendate` | `xsd:date` | true | 0..1 |
| `efentime` | `xsd:date` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBBR_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `objectid` | `xsd:int` | true | 0..1 |
| `idosbt` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `source` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hsttderv` | `xsd:string` | true | 0..1 |
| `hbias` | `xsd:double` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vsttderv` | `xsd:string` | true | 0..1 |
| `vbias` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `integr` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `revtime` | `xsd:date` | true | 0..1 |
| `efstdate` | `xsd:date` | true | 0..1 |
| `efsttime` | `xsd:date` | true | 0..1 |
| `efendate` | `xsd:date` | true | 0..1 |
| `efentime` | `xsd:date` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |
| `shape_area` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBBR_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `objectid` | `xsd:int` | true | 0..1 |
| `idosbt` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `source` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hsttderv` | `xsd:string` | true | 0..1 |
| `hbias` | `xsd:double` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vsttderv` | `xsd:string` | true | 0..1 |
| `vbias` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `integr` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `revtime` | `xsd:date` | true | 0..1 |
| `efstdate` | `xsd:date` | true | 0..1 |
| `efsttime` | `xsd:date` | true | 0..1 |
| `efendate` | `xsd:date` | true | 0..1 |
| `efentime` | `xsd:date` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBBR_GAB_CONS_1`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elevation` | `xsd:decimal` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBBV_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBBV_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBBV_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBBV_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBBV_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBBV_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBBV_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBBV_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBCB_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `LAYER` | `xsd:string` | true | 0..1 |
| `GM_TYPE` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBCB_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBCB_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBCB_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `featype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:double` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBCB_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `LAYER` | `xsd:string` | true | 0..1 |
| `GM_TYPE` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBCB_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `obsttype` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBCB_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBCB_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `featype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:double` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBCF_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBCF_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `feattype` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hsttderv` | `xsd:string` | true | 0..1 |
| `hbias` | `xsd:double` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vsttderv` | `xsd:string` | true | 0..1 |
| `vbias` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `revtime` | `xsd:date` | true | 0..1 |
| `efstdate` | `xsd:date` | true | 0..1 |
| `efsttime` | `xsd:date` | true | 0..1 |
| `efendate` | `xsd:date` | true | 0..1 |
| `efentime` | `xsd:date` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |
| `source` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uu_id` | `xsd:string` | true | 0..1 |
| `shape_le_1` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBCF_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `feattype` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hsttderv` | `xsd:string` | true | 0..1 |
| `hbias` | `xsd:double` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vsttderv` | `xsd:string` | true | 0..1 |
| `vbias` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `revtime` | `xsd:date` | true | 0..1 |
| `efstdate` | `xsd:date` | true | 0..1 |
| `efsttime` | `xsd:date` | true | 0..1 |
| `efendate` | `xsd:date` | true | 0..1 |
| `efentime` | `xsd:date` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uu_id` | `xsd:string` | true | 0..1 |
| `shape_le_1` | `xsd:decimal` | true | 0..1 |
| `shape_area` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBCF_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `feattype` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hsttderv` | `xsd:string` | true | 0..1 |
| `hbias` | `xsd:double` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vsttderv` | `xsd:string` | true | 0..1 |
| `vbias` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `revtime` | `xsd:date` | true | 0..1 |
| `efstdate` | `xsd:date` | true | 0..1 |
| `efsttime` | `xsd:date` | true | 0..1 |
| `efendate` | `xsd:date` | true | 0..1 |
| `efentime` | `xsd:date` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uu_id` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBCF_GAB_CONS_1`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `fid_` | `xsd:decimal` | true | 0..1 |
| `entity` | `xsd:string` | true | 0..1 |
| `level` | `xsd:decimal` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `color` | `xsd:int` | true | 0..1 |
| `linetype` | `xsd:string` | true | 0..1 |
| `elevation` | `xsd:decimal` | true | 0..1 |
| `linewt` | `xsd:int` | true | 0..1 |
| `refname` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBCG_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `LAYER` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBCG_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBCG_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBCG_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBCG_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `GM_LAYER` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBCG_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBCG_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBCG_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBCR_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBCR_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBCR_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `making` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBCR_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBCR_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBCR_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBCR_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `making` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBCR_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBCT_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBCT_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBCT_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBCT_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBCT_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `layer` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBCT_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBCT_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBCT_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBCT_GAB_CONS_1`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `fid_` | `xsd:int` | true | 0..1 |
| `entity` | `xsd:string` | true | 0..1 |
| `level` | `xsd:int` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `color` | `xsd:short` | true | 0..1 |
| `linetype` | `xsd:string` | true | 0..1 |
| `elevation` | `xsd:decimal` | true | 0..1 |
| `linewt` | `xsd:short` | true | 0..1 |
| `refname` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBCT_GAB_CONS_2`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `fid_` | `xsd:int` | true | 0..1 |
| `entity` | `xsd:string` | true | 0..1 |
| `level` | `xsd:int` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `color` | `xsd:short` | true | 0..1 |
| `linetype` | `xsd:string` | true | 0..1 |
| `elevation` | `xsd:decimal` | true | 0..1 |
| `linewt` | `xsd:short` | true | 0..1 |
| `refname` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBCZ_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBCZ_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBCZ_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `making` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBCZ_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBCZ_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBCZ_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBCZ_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `making` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBCZ_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBEG_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBEG_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBEG_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `making` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBEG_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBEG_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBEG_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBEG_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `making` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBEG_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBFI_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Layer` | `xsd:string` | true | 0..1 |
| `Areakm2` | `xsd:double` | true | 0..1 |
| `PerimKm` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBFI_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBFI_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBFI_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBFI_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Layer` | `xsd:string` | true | 0..1 |
| `AreaKm2` | `xsd:double` | true | 0..1 |
| `PerimKm` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBFI_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `OBJECTID` | `xsd:double` | true | 0..1 |
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBFI_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBFI_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ELEVATION` | `xsd:double` | true | 0..1 |
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBFL_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `layer` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBFL_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBFL_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBFL_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBFL_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `layer` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBFL_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `z_max` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBFL_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBFL_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `radius` | `xsd:double` | true | 0..1 |
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBFZ_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBFZ_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBFZ_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `making` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBFZ_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBFZ_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBFZ_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBFZ_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `making` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBFZ_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBGL_A2_LIMITES_1`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBGL_A2_LIMITES_2`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBGL_GAB_CONS_1`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `fid_` | `xsd:decimal` | true | 0..1 |
| `entity` | `xsd:string` | true | 0..1 |
| `level` | `xsd:decimal` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `color` | `xsd:int` | true | 0..1 |
| `linetype` | `xsd:string` | true | 0..1 |
| `elevation` | `xsd:decimal` | true | 0..1 |
| `linewt` | `xsd:int` | true | 0..1 |
| `refname` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBGL_GAB_CONS_2`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `fid_` | `xsd:decimal` | true | 0..1 |
| `entity` | `xsd:string` | true | 0..1 |
| `level` | `xsd:decimal` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `color` | `xsd:int` | true | 0..1 |
| `linetype` | `xsd:string` | true | 0..1 |
| `elevation` | `xsd:decimal` | true | 0..1 |
| `linewt` | `xsd:int` | true | 0..1 |
| `refname` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBGO_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `layer` | `xsd:string` | true | 0..1 |
| `perimeter` | `xsd:string` | true | 0..1 |
| `enclosed_a` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBGO_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBGO_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBGO_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBGO_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `layer` | `xsd:string` | true | 0..1 |
| `gm_type` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBGO_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBGO_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBGO_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gm_layer` | `xsd:string` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `elevation` | `xsd:double` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBGR_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBGR_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBGR_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBGR_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBGR_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `layer` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBGR_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBGR_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBGR_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBGR_GAB_CONS_1`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `fid_` | `xsd:int` | true | 0..1 |
| `entity` | `xsd:string` | true | 0..1 |
| `level` | `xsd:int` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `color` | `xsd:short` | true | 0..1 |
| `linetype` | `xsd:string` | true | 0..1 |
| `elevation` | `xsd:decimal` | true | 0..1 |
| `linewt` | `xsd:short` | true | 0..1 |
| `refname` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBGR_GAB_CONS_2`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `fid_` | `xsd:int` | true | 0..1 |
| `entity` | `xsd:string` | true | 0..1 |
| `level` | `xsd:int` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `color` | `xsd:short` | true | 0..1 |
| `linetype` | `xsd:string` | true | 0..1 |
| `elevation` | `xsd:decimal` | true | 0..1 |
| `linewt` | `xsd:short` | true | 0..1 |
| `refname` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBJP_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `LAYER` | `xsd:string` | true | 0..1 |
| `ELEVATION` | `xsd:double` | true | 0..1 |
| `FILENAME` | `xsd:string` | true | 0..1 |
| `DESCRIPTIO` | `xsd:string` | true | 0..1 |
| `UPPER_LE_X` | `xsd:double` | true | 0..1 |
| `UPPER_LE_Y` | `xsd:double` | true | 0..1 |
| `LOWER_RI_X` | `xsd:double` | true | 0..1 |
| `LOWER_RI_Y` | `xsd:double` | true | 0..1 |
| `WEST_LONGI` | `xsd:double` | true | 0..1 |
| `NORTH_LATI` | `xsd:double` | true | 0..1 |
| `EAST_LONGI` | `xsd:double` | true | 0..1 |
| `SOUTH_LATI` | `xsd:double` | true | 0..1 |
| `UL_CORNER_` | `xsd:double` | true | 0..1 |
| `UL_CORNER1` | `xsd:double` | true | 0..1 |
| `UR_CORNER_` | `xsd:double` | true | 0..1 |
| `UR_CORNER1` | `xsd:double` | true | 0..1 |
| `LR_CORNER_` | `xsd:double` | true | 0..1 |
| `LR_CORNER1` | `xsd:double` | true | 0..1 |
| `LL_CORNER_` | `xsd:double` | true | 0..1 |
| `LL_CORNER1` | `xsd:double` | true | 0..1 |
| `PROJ_DESC` | `xsd:string` | true | 0..1 |
| `PROJ_DATUM` | `xsd:string` | true | 0..1 |
| `PROJ_UNITS` | `xsd:string` | true | 0..1 |
| `EPSG_CODE` | `xsd:string` | true | 0..1 |
| `COVERED_AR` | `xsd:string` | true | 0..1 |
| `LOAD_TIME` | `xsd:string` | true | 0..1 |
| `GDAL_NO_DA` | `xsd:double` | true | 0..1 |
| `NUM_COLUMN` | `xsd:double` | true | 0..1 |
| `NUM_ROWS` | `xsd:double` | true | 0..1 |
| `NUM_BANDS` | `xsd:double` | true | 0..1 |
| `PIXEL_WIDT` | `xsd:string` | true | 0..1 |
| `PIXEL_HEIG` | `xsd:string` | true | 0..1 |
| `MIN_ELEVAT` | `xsd:string` | true | 0..1 |
| `MAX_ELEVAT` | `xsd:string` | true | 0..1 |
| `ELEVATION_` | `xsd:string` | true | 0..1 |
| `BIT_DEPTH` | `xsd:double` | true | 0..1 |
| `SAMPLE_TYP` | `xsd:string` | true | 0..1 |
| `PCS_CITATI` | `xsd:string` | true | 0..1 |
| `GT_CITATIO` | `xsd:string` | true | 0..1 |
| `PHOTOMETRI` | `xsd:string` | true | 0..1 |
| `BIT_DEPTH1` | `xsd:double` | true | 0..1 |
| `SAMPLE_FOR` | `xsd:string` | true | 0..1 |
| `ROWS_PER_S` | `xsd:double` | true | 0..1 |
| `COMPRESSIO` | `xsd:string` | true | 0..1 |
| `PIXEL_SCAL` | `xsd:string` | true | 0..1 |
| `TIEPOINTS` | `xsd:string` | true | 0..1 |
| `MODEL_TYPE` | `xsd:string` | true | 0..1 |
| `RASTER_TYP` | `xsd:string` | true | 0..1 |
| `VERT_DATUM` | `xsd:string` | true | 0..1 |
| `CLOSED` | `xsd:string` | true | 0..1 |
| `BORDER_STY` | `xsd:string` | true | 0..1 |
| `BORDER_COL` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBJP_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `topo` | `xsd:double` | true | 0..1 |
| `chao` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBJP_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBJP_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBJP_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `FID_` | `xsd:double` | true | 0..1 |
| `Entity` | `xsd:string` | true | 0..1 |
| `Layer` | `xsd:string` | true | 0..1 |
| `Color` | `xsd:double` | true | 0..1 |
| `Linetype` | `xsd:string` | true | 0..1 |
| `Elevation` | `xsd:double` | true | 0..1 |
| `LineWt` | `xsd:double` | true | 0..1 |
| `RefName` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBJP_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `topo` | `xsd:double` | true | 0..1 |
| `chao` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBJP_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `TOCA` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBJP_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBJV_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBJV_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBJV_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBJV_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBJV_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBJV_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBJV_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBJV_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBKP_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `LAYER` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBKP_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBKP_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBKP_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBKP_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `FID_` | `xsd:double` | true | 0..1 |
| `Entity` | `xsd:string` | true | 0..1 |
| `Layer` | `xsd:string` | true | 0..1 |
| `Color` | `xsd:double` | true | 0..1 |
| `Linetype` | `xsd:string` | true | 0..1 |
| `Elevation` | `xsd:double` | true | 0..1 |
| `LineWt` | `xsd:double` | true | 0..1 |
| `RefName` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBKP_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBKP_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBKP_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBMG_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `LAYER` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBMG_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBMG_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBMG_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBMG_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Layer` | `xsd:string` | true | 0..1 |
| `Elevation` | `xsd:double` | true | 0..1 |
| `AREA` | `xsd:double` | true | 0..1 |
| `Perimetro` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBMG_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBMG_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBMG_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBMN_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBMN_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBMN_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBMN_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBMN_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBMN_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBMN_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBMN_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBMO_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBMO_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBMO_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `making` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBMO_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBMO_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBMO_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBMO_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `making` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBMO_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBMQ_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Layer` | `xsd:string` | true | 0..1 |
| `Perim_km` | `xsd:double` | true | 0..1 |
| `Area_km2` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBMQ_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBMQ_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBMQ_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBMQ_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Layer` | `xsd:string` | true | 0..1 |
| `Perim_km` | `xsd:double` | true | 0..1 |
| `Area_km2` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBMQ_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBMQ_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBMQ_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBNF_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `layer` | `xsd:string` | true | 0..1 |
| `gm_type` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBNF_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radiusd` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:double` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBNF_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBNF_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:double` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBNF_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `layer` | `xsd:string` | true | 0..1 |
| `gm_type` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBNF_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:double` | true | 0..1 |
| `id_eng` | `xsd:double` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBNF_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:long` | true | 0..1 |
| `vconf` | `xsd:long` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBNF_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:double` | true | 0..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `fid_1` | `xsd:long` | true | 0..1 |
| `id_eng` | `xsd:double` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBNT_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBNT_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBNT_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `making` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBNT_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBNT_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBNT_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBNT_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `making` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBNT_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBPA_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBPA_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBPA_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBPA_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBPA_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `layer` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBPA_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBPA_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBPA_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBPA_GAB_CONS_1`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `fid_` | `xsd:int` | true | 0..1 |
| `entity` | `xsd:string` | true | 0..1 |
| `level` | `xsd:int` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `color` | `xsd:short` | true | 0..1 |
| `linetype` | `xsd:string` | true | 0..1 |
| `elevation` | `xsd:decimal` | true | 0..1 |
| `linewt` | `xsd:short` | true | 0..1 |
| `refname` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBPJ_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `RefName` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBPJ_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBPJ_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBPJ_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBPJ_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `LAYER` | `xsd:string` | true | 0..1 |
| `GM_TYPE` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBPJ_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBPJ_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBPJ_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBPP_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBPP_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBPP_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBPP_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBPP_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Shape_Area` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBPP_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBPP_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBPP_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBPS_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBPS_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBPS_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `making` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBPS_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBPS_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBPS_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBPS_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `making` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBPS_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBPV_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBPV_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBPV_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `making` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBPV_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBPV_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBPV_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBPV_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `making` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBPV_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBRB_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBRB_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBRB_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `making` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBRB_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBRB_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `layer` | `xsd:string` | true | 0..1 |
| `SHAPE_Area` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBRB_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBRB_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `making` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBRB_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBRF_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBRF_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBRF_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBRF_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBRF_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `layer` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBRF_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBRF_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBRF_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBRF_GAB_CONS_1`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `fid_` | `xsd:int` | true | 0..1 |
| `entity` | `xsd:string` | true | 0..1 |
| `level` | `xsd:int` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `color` | `xsd:short` | true | 0..1 |
| `linetype` | `xsd:string` | true | 0..1 |
| `elevation` | `xsd:decimal` | true | 0..1 |
| `linewt` | `xsd:short` | true | 0..1 |
| `refname` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBRJ_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBRJ_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `idosbt` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hsttderv` | `xsd:string` | true | 0..1 |
| `hbias` | `xsd:double` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vsttderv` | `xsd:string` | true | 0..1 |
| `vbias` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `revtime` | `xsd:date` | true | 0..1 |
| `efstdate` | `xsd:date` | true | 0..1 |
| `efsttime` | `xsd:date` | true | 0..1 |
| `efendate` | `xsd:date` | true | 0..1 |
| `efentime` | `xsd:date` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |
| `source` | `xsd:decimal` | true | 0..1 |
| `integr` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBRJ_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `idosbt` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hsttderv` | `xsd:string` | true | 0..1 |
| `hbias` | `xsd:double` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vsttderv` | `xsd:string` | true | 0..1 |
| `vbias` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `revtime` | `xsd:date` | true | 0..1 |
| `efstdate` | `xsd:date` | true | 0..1 |
| `efsttime` | `xsd:date` | true | 0..1 |
| `efendate` | `xsd:date` | true | 0..1 |
| `efentime` | `xsd:date` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `source` | `xsd:double` | true | 0..1 |
| `integr` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBRJ_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `idosbt` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hsttderv` | `xsd:string` | true | 0..1 |
| `hbias` | `xsd:double` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vsttderv` | `xsd:string` | true | 0..1 |
| `vbias` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `revtime` | `xsd:date` | true | 0..1 |
| `efstdate` | `xsd:date` | true | 0..1 |
| `efsttime` | `xsd:date` | true | 0..1 |
| `efendate` | `xsd:date` | true | 0..1 |
| `efentime` | `xsd:date` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |
| `source` | `xsd:decimal` | true | 0..1 |
| `integr` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBRJ_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `objectid` | `xsd:int` | true | 0..1 |
| `idosbt` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hsttderv` | `xsd:string` | true | 0..1 |
| `hbias` | `xsd:double` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vsttderv` | `xsd:string` | true | 0..1 |
| `vbias` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `revtime` | `xsd:date` | true | 0..1 |
| `efstdate` | `xsd:date` | true | 0..1 |
| `efsttime` | `xsd:date` | true | 0..1 |
| `efendate` | `xsd:date` | true | 0..1 |
| `efentime` | `xsd:date` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `source` | `xsd:decimal` | true | 0..1 |
| `integr` | `xsd:decimal` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBRJ_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `objectid` | `xsd:int` | true | 0..1 |
| `idosbt` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hsttderv` | `xsd:string` | true | 0..1 |
| `hbias` | `xsd:double` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vsttderv` | `xsd:string` | true | 0..1 |
| `vbias` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `revtime` | `xsd:date` | true | 0..1 |
| `efstdate` | `xsd:date` | true | 0..1 |
| `efsttime` | `xsd:date` | true | 0..1 |
| `efendate` | `xsd:date` | true | 0..1 |
| `efentime` | `xsd:date` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `source` | `xsd:decimal` | true | 0..1 |
| `integridad` | `xsd:decimal` | true | 0..1 |
| `shape_leng` | `xsd:decimal` | true | 0..1 |
| `shape_area` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBRJ_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `objectid` | `xsd:int` | true | 0..1 |
| `idosbt` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hsttderv` | `xsd:string` | true | 0..1 |
| `hbias` | `xsd:double` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vsttderv` | `xsd:string` | true | 0..1 |
| `vbias` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `revtime` | `xsd:date` | true | 0..1 |
| `efstdate` | `xsd:date` | true | 0..1 |
| `efsttime` | `xsd:date` | true | 0..1 |
| `efendate` | `xsd:date` | true | 0..1 |
| `efentime` | `xsd:date` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `source` | `xsd:decimal` | true | 0..1 |
| `integr` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBRJ_GAB_CONS_1`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `fid_` | `xsd:decimal` | true | 0..1 |
| `entity` | `xsd:string` | true | 0..1 |
| `level` | `xsd:decimal` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `color` | `xsd:int` | true | 0..1 |
| `linetype` | `xsd:string` | true | 0..1 |
| `elevation` | `xsd:decimal` | true | 0..1 |
| `linewt` | `xsd:int` | true | 0..1 |
| `refname` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBRJ_GAB_CONS_2`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `fid_` | `xsd:decimal` | true | 0..1 |
| `entity` | `xsd:string` | true | 0..1 |
| `level` | `xsd:decimal` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `color` | `xsd:int` | true | 0..1 |
| `linetype` | `xsd:string` | true | 0..1 |
| `elevation` | `xsd:decimal` | true | 0..1 |
| `linewt` | `xsd:int` | true | 0..1 |
| `refname` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBSG_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBSG_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBSG_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBSG_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBSG_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBSG_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBSG_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBSG_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBSJ_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBSJ_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBSJ_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_OBST` | `xsd:string` | true | 0..1 |
| `FEATTYPE` | `xsd:double` | true | 0..1 |
| `OBSTYPE` | `xsd:double` | true | 0..1 |
| `ELEV` | `xsd:double` | true | 0..1 |
| `REVDATE` | `xsd:string` | true | 0..1 |
| `STATUS` | `xsd:double` | true | 0..1 |
| `LIGHTING` | `xsd:double` | true | 0..1 |
| `MARKING` | `xsd:double` | true | 0..1 |
| `EXTENT` | `xsd:string` | true | 0..1 |
| `ID_SOURCE` | `xsd:string` | true | 0..1 |
| `HACC` | `xsd:double` | true | 0..1 |
| `HCONF` | `xsd:double` | true | 0..1 |
| `HREFSYS` | `xsd:string` | true | 0..1 |
| `VACC` | `xsd:double` | true | 0..1 |
| `VCONF` | `xsd:double` | true | 0..1 |
| `VRES` | `xsd:double` | true | 0..1 |
| `VREFSYS` | `xsd:string` | true | 0..1 |
| `INTEGR` | `xsd:double` | true | 0..1 |
| `UOM` | `xsd:string` | true | 0..1 |
| `HSTNDDEV` | `xsd:double` | true | 0..1 |
| `VSTNDDEV` | `xsd:double` | true | 0..1 |
| `STTDERV` | `xsd:double` | true | 0..1 |
| `HRES` | `xsd:double` | true | 0..1 |
| `HEIGHT` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBSJ_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_OBST` | `xsd:string` | true | 0..1 |
| `FEATTYPE` | `xsd:double` | true | 0..1 |
| `OBSTYPE` | `xsd:double` | true | 0..1 |
| `ELEV` | `xsd:double` | true | 0..1 |
| `RADIUS` | `xsd:double` | true | 0..1 |
| `REVDATE` | `xsd:string` | true | 0..1 |
| `STATUS` | `xsd:double` | true | 0..1 |
| `LIGHTING` | `xsd:double` | true | 0..1 |
| `MARKING` | `xsd:double` | true | 0..1 |
| `EXTENT` | `xsd:string` | true | 0..1 |
| `ID_SOURCE` | `xsd:string` | true | 0..1 |
| `HACC` | `xsd:double` | true | 0..1 |
| `HCONF` | `xsd:double` | true | 0..1 |
| `HRES` | `xsd:double` | true | 0..1 |
| `HREFSYS` | `xsd:string` | true | 0..1 |
| `VACC` | `xsd:double` | true | 0..1 |
| `VCONF` | `xsd:double` | true | 0..1 |
| `VRES` | `xsd:double` | true | 0..1 |
| `VREFSYS` | `xsd:string` | true | 0..1 |
| `INTEGR` | `xsd:double` | true | 0..1 |
| `UOM` | `xsd:string` | true | 0..1 |
| `HSTNDDEV` | `xsd:double` | true | 0..1 |
| `VSTNDDEV` | `xsd:double` | true | 0..1 |
| `STTDERV` | `xsd:double` | true | 0..1 |
| `HEIGHT` | `xsd:double` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBSJ_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Layer` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBSJ_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBSJ_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_OBST` | `xsd:string` | true | 0..1 |
| `FEATTYPE` | `xsd:double` | true | 0..1 |
| `OBSTYPE` | `xsd:double` | true | 0..1 |
| `ELEV` | `xsd:double` | true | 0..1 |
| `REVDATE` | `xsd:string` | true | 0..1 |
| `STATUS` | `xsd:double` | true | 0..1 |
| `LIGHTING` | `xsd:double` | true | 0..1 |
| `MARKING` | `xsd:double` | true | 0..1 |
| `EXTENT` | `xsd:string` | true | 0..1 |
| `ID_SOURCE` | `xsd:string` | true | 0..1 |
| `HACC` | `xsd:double` | true | 0..1 |
| `HCONF` | `xsd:double` | true | 0..1 |
| `HREFSYS` | `xsd:string` | true | 0..1 |
| `VACC` | `xsd:double` | true | 0..1 |
| `VCONF` | `xsd:double` | true | 0..1 |
| `VRES` | `xsd:double` | true | 0..1 |
| `VREFSYS` | `xsd:string` | true | 0..1 |
| `INTEGR` | `xsd:double` | true | 0..1 |
| `UOM` | `xsd:string` | true | 0..1 |
| `HSTNDDEV` | `xsd:double` | true | 0..1 |
| `VSTNDDEV` | `xsd:double` | true | 0..1 |
| `STTDERV` | `xsd:double` | true | 0..1 |
| `HRES` | `xsd:double` | true | 0..1 |
| `HEIGHT` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBSJ_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ID_OBST` | `xsd:string` | true | 0..1 |
| `FEATTYPE` | `xsd:double` | true | 0..1 |
| `OBSTYPE` | `xsd:double` | true | 0..1 |
| `ELEV` | `xsd:double` | true | 0..1 |
| `RADIUS` | `xsd:double` | true | 0..1 |
| `REVDATE` | `xsd:string` | true | 0..1 |
| `STATUS` | `xsd:double` | true | 0..1 |
| `LIGHTING` | `xsd:double` | true | 0..1 |
| `MARKING` | `xsd:double` | true | 0..1 |
| `EXTENT` | `xsd:string` | true | 0..1 |
| `ID_SOURCE` | `xsd:string` | true | 0..1 |
| `HACC` | `xsd:double` | true | 0..1 |
| `HCONF` | `xsd:double` | true | 0..1 |
| `HRES` | `xsd:double` | true | 0..1 |
| `HREFSYS` | `xsd:string` | true | 0..1 |
| `VACC` | `xsd:double` | true | 0..1 |
| `VCONF` | `xsd:double` | true | 0..1 |
| `VRES` | `xsd:double` | true | 0..1 |
| `VREFSYS` | `xsd:string` | true | 0..1 |
| `INTEGR` | `xsd:double` | true | 0..1 |
| `UOM` | `xsd:string` | true | 0..1 |
| `HSTNDDEV` | `xsd:double` | true | 0..1 |
| `VSTNDDEV` | `xsd:double` | true | 0..1 |
| `STTDERV` | `xsd:double` | true | 0..1 |
| `HEIGHT` | `xsd:double` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBSL_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `LAYER` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBSL_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBSL_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBSL_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBSL_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBSL_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `OBJECTID` | `xsd:double` | true | 0..1 |
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBSL_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBSL_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBSM_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBSM_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `SHAPE_Leng` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBSM_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `making` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBSM_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBSM_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Name` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBSM_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `SHAPE_Leng` | `xsd:double` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBSM_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `making` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBSM_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBSN_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ELEVATION` | `xsd:double` | true | 0..1 |
| `LAYER` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBSN_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBSN_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `making` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBSN_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBSN_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |
| `Layer` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBSN_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBSN_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Shape_Leng` | `xsd:double` | true | 0..1 |
| `Shape_Area` | `xsd:double` | true | 0..1 |
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `making` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBSN_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBSP_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBSP_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBSP_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBSP_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBSP_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `layer` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBSP_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBSP_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBSP_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBSP_GAB_CONS_1`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `fid_` | `xsd:int` | true | 0..1 |
| `entity` | `xsd:string` | true | 0..1 |
| `level` | `xsd:int` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `color` | `xsd:short` | true | 0..1 |
| `linetype` | `xsd:string` | true | 0..1 |
| `elevation` | `xsd:decimal` | true | 0..1 |
| `linewt` | `xsd:short` | true | 0..1 |
| `refname` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBSP_GAB_CONS_2`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `fid_` | `xsd:int` | true | 0..1 |
| `entity` | `xsd:string` | true | 0..1 |
| `level` | `xsd:int` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `color` | `xsd:short` | true | 0..1 |
| `linetype` | `xsd:string` | true | 0..1 |
| `elevation` | `xsd:decimal` | true | 0..1 |
| `linewt` | `xsd:short` | true | 0..1 |
| `refname` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBSV_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBSV_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBSV_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBSV_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBSV_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `layer` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBSV_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBSV_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBSV_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `elev` | `xsd:decimal` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `feattypety` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:decimal` | true | 0..1 |
| `hconf` | `xsd:string` | true | 0..1 |
| `height` | `xsd:decimal` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `hres` | `xsd:decimal` | true | 0..1 |
| `hstnddev` | `xsd:decimal` | true | 0..1 |
| `id_obstacu` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `radius` | `xsd:decimal` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:decimal` | true | 0..1 |
| `vconf` | `xsd:string` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `vres` | `xsd:decimal` | true | 0..1 |
| `vstnddev` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBSV_GAB_CONS_1`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `fid_` | `xsd:int` | true | 0..1 |
| `entity` | `xsd:string` | true | 0..1 |
| `level` | `xsd:int` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `color` | `xsd:short` | true | 0..1 |
| `linetype` | `xsd:string` | true | 0..1 |
| `elevation` | `xsd:decimal` | true | 0..1 |
| `linewt` | `xsd:short` | true | 0..1 |
| `refname` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBSV_GAB_CONS_2`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `fid_` | `xsd:int` | true | 0..1 |
| `entity` | `xsd:string` | true | 0..1 |
| `level` | `xsd:int` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `color` | `xsd:short` | true | 0..1 |
| `linetype` | `xsd:string` | true | 0..1 |
| `elevation` | `xsd:decimal` | true | 0..1 |
| `linewt` | `xsd:short` | true | 0..1 |
| `refname` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBTT_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBTT_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `obstype` | `xsd:string` | true | 0..1 |
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBTT_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `obstype` | `xsd:string` | true | 0..1 |
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBTT_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `obstype` | `xsd:string` | true | 0..1 |
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBTT_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:int` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBTT_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:string` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBTT_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `obstype` | `xsd:string` | true | 0..1 |
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBTT_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `obstype` | `xsd:string` | true | 0..1 |
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBVT_A2_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `FID_` | `xsd:double` | true | 0..1 |
| `Entity` | `xsd:string` | true | 0..1 |
| `Layer` | `xsd:string` | true | 0..1 |
| `Color` | `xsd:double` | true | 0..1 |
| `Linetype` | `xsd:string` | true | 0..1 |
| `Elevation` | `xsd:double` | true | 0..1 |
| `LineWt` | `xsd:double` | true | 0..1 |
| `RefName` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBVT_A2_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBVT_A2_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBVT_A2_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SBVT_A3_LIMITES`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `FID_` | `xsd:double` | true | 0..1 |
| `Entity` | `xsd:string` | true | 0..1 |
| `Layer` | `xsd:string` | true | 0..1 |
| `Color` | `xsd:double` | true | 0..1 |
| `Linetype` | `xsd:string` | true | 0..1 |
| `Elevation` | `xsd:double` | true | 0..1 |
| `LineWt` | `xsd:double` | true | 0..1 |
| `RefName` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBVT_A3_LINHA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `ICA:SBVT_A3_POLIGONO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `ICA:SBVT_A3_PONTO`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_obst` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `obstype` | `xsd:string` | true | 0..1 |
| `elev` | `xsd:double` | true | 0..1 |
| `height` | `xsd:double` | true | 0..1 |
| `radius` | `xsd:double` | true | 0..1 |
| `revdate` | `xsd:date` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `lighting` | `xsd:string` | true | 0..1 |
| `marking` | `xsd:string` | true | 0..1 |
| `extent` | `xsd:string` | true | 0..1 |
| `id_source` | `xsd:string` | true | 0..1 |
| `hacc` | `xsd:double` | true | 0..1 |
| `hconf` | `xsd:double` | true | 0..1 |
| `hres` | `xsd:double` | true | 0..1 |
| `hrefsys` | `xsd:string` | true | 0..1 |
| `vacc` | `xsd:double` | true | 0..1 |
| `vconf` | `xsd:double` | true | 0..1 |
| `vres` | `xsd:double` | true | 0..1 |
| `vrefsys` | `xsd:string` | true | 0..1 |
| `integr` | `xsd:string` | true | 0..1 |
| `uom` | `xsd:string` | true | 0..1 |
| `hstnddev` | `xsd:double` | true | 0..1 |
| `vstnddev` | `xsd:double` | true | 0..1 |
| `sttderv` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `ICA:SETOR_FIR`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `airspace_p` | `xsd:decimal` | true | 0..1 |
| `effectived` | `xsd:date` | true | 0..1 |
| `typ` | `xsd:string` | true | 0..1 |
| `ident` | `xsd:string` | true | 0..1 |
| `icaocode` | `xsd:string` | true | 0..1 |
| `nam` | `xsd:string` | true | 0..1 |
| `areacode` | `xsd:string` | true | 0..1 |
| `codedistve` | `xsd:string` | true | 0..1 |
| `uplimituni` | `xsd:string` | true | 0..1 |
| `codedistv1` | `xsd:string` | true | 0..1 |
| `lowerlimit` | `xsd:string` | true | 0..1 |
| `uomdistver` | `xsd:string` | true | 0..1 |
| `codewrkhr` | `xsd:string` | true | 0..1 |
| `upperlimit` | `xsd:decimal` | true | 0..1 |
| `lowerlimi1` | `xsd:decimal` | true | 0..1 |
| `entryrpt` | `xsd:string` | true | 0..1 |
| `txtlocalty` | `xsd:string` | true | 0..1 |
| `txtrmk_loc` | `xsd:string` | true | 0..1 |
| `relatedfir` | `xsd:string` | true | 0..1 |
| `classrmklo` | `xsd:string` | true | 0..1 |
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |
| `emenda` | `xsd:date` | true | 0..1 |
| `emenda_futura` | `xsd:date` | true | 0..1 |

### `ICA:setores_tma`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `airspace_p` | `xsd:decimal` | true | 0..1 |
| `effectived` | `xsd:date` | true | 0..1 |
| `typ` | `xsd:string` | true | 0..1 |
| `ident` | `xsd:string` | true | 0..1 |
| `icaocode` | `xsd:string` | true | 0..1 |
| `nam` | `xsd:string` | true | 0..1 |
| `areacode` | `xsd:string` | true | 0..1 |
| `codedistve` | `xsd:string` | true | 0..1 |
| `uplimituni` | `xsd:string` | true | 0..1 |
| `codedistv1` | `xsd:string` | true | 0..1 |
| `lowerlimit` | `xsd:string` | true | 0..1 |
| `uomdistver` | `xsd:string` | true | 0..1 |
| `codewrkhr` | `xsd:string` | true | 0..1 |
| `upperlimit` | `xsd:decimal` | true | 0..1 |
| `lowerlimi1` | `xsd:decimal` | true | 0..1 |
| `entryrpt` | `xsd:string` | true | 0..1 |
| `txtlocalty` | `xsd:string` | true | 0..1 |
| `txtrmk_loc` | `xsd:string` | true | 0..1 |
| `relatedfir` | `xsd:string` | true | 0..1 |
| `classrmklo` | `xsd:string` | true | 0..1 |
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |
| `emenda` | `xsd:date` | true | 0..1 |
| `emenda_futura` | `xsd:date` | true | 0..1 |

### `ICA:TMA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | false | 1..1 |
| `airspace_p` | `xsd:decimal` | true | 0..1 |
| `effectived` | `xsd:date` | true | 0..1 |
| `typ` | `xsd:string` | true | 0..1 |
| `ident` | `xsd:string` | true | 0..1 |
| `icaocode` | `xsd:string` | true | 0..1 |
| `nam` | `xsd:string` | true | 0..1 |
| `areacode` | `xsd:string` | true | 0..1 |
| `codedistve` | `xsd:string` | true | 0..1 |
| `uplimituni` | `xsd:string` | true | 0..1 |
| `codedistv1` | `xsd:string` | true | 0..1 |
| `lowerlimit` | `xsd:string` | true | 0..1 |
| `uomdistver` | `xsd:string` | true | 0..1 |
| `codewrkhr` | `xsd:string` | true | 0..1 |
| `upperlimit` | `xsd:decimal` | true | 0..1 |
| `lowerlimi1` | `xsd:decimal` | true | 0..1 |
| `entryrpt` | `xsd:string` | true | 0..1 |
| `txtlocalty` | `xsd:string` | true | 0..1 |
| `txtrmk_loc` | `xsd:string` | true | 0..1 |
| `relatedfir` | `xsd:string` | true | 0..1 |
| `classrmklo` | `xsd:string` | true | 0..1 |
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |
| `emenda` | `xsd:date` | false | 1..1 |
| `emenda_futura` | `xsd:date` | false | 1..1 |

### `ICA:vor`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `vor_pk` | `xsd:decimal` | true | 0..1 |
| `effectived` | `xsd:date` | true | 0..1 |
| `airspace_p` | `xsd:decimal` | true | 0..1 |
| `airspace_1` | `xsd:decimal` | true | 0..1 |
| `ident` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:decimal` | true | 0..1 |
| `longitude` | `xsd:decimal` | true | 0..1 |
| `areacode` | `xsd:string` | true | 0..1 |
| `icaocode` | `xsd:string` | true | 0..1 |
| `txtname` | `xsd:string` | true | 0..1 |
| `magvariati` | `xsd:decimal` | true | 0..1 |
| `magvardate` | `xsd:date` | true | 0..1 |
| `elevation` | `xsd:decimal` | true | 0..1 |
| `elevaccura` | `xsd:decimal` | true | 0..1 |
| `frequency` | `xsd:decimal` | true | 0..1 |
| `class3` | `xsd:string` | true | 0..1 |
| `class4` | `xsd:string` | true | 0..1 |
| `class5` | `xsd:string` | true | 0..1 |
| `facchar1` | `xsd:string` | true | 0..1 |
| `facchar2` | `xsd:string` | true | 0..1 |
| `freqprotdi` | `xsd:decimal` | true | 0..1 |
| `frequnits` | `xsd:string` | true | 0..1 |
| `fom` | `xsd:string` | true | 0..1 |
| `vortype` | `xsd:string` | true | 0..1 |
| `codeem` | `xsd:string` | true | 0..1 |
| `codedatum` | `xsd:string` | true | 0..1 |
| `valgeoaccu` | `xsd:decimal` | true | 0..1 |
| `uomgeoaccu` | `xsd:string` | true | 0..1 |
| `geoundulat` | `xsd:decimal` | true | 0..1 |
| `valcrc` | `xsd:string` | true | 0..1 |
| `verdatum` | `xsd:string` | true | 0..1 |
| `codewrkhr` | `xsd:string` | true | 0..1 |
| `txtrmkwrkh` | `xsd:string` | true | 0..1 |
| `txtrmk` | `xsd:string` | true | 0..1 |
| `orgauth_pk` | `xsd:decimal` | true | 0..1 |
| `antennahei` | `xsd:decimal` | true | 0..1 |
| `power` | `xsd:decimal` | true | 0..1 |
| `ndb_pk` | `xsd:decimal` | true | 0..1 |
| `valdeclina` | `xsd:decimal` | true | 0..1 |
| `magtrueind` | `xsd:string` | true | 0..1 |
| `txtrmk_lcl` | `xsd:string` | true | 0..1 |
| `txtrmk_cov` | `xsd:string` | true | 0..1 |
| `vertaccuom` | `xsd:string` | true | 0..1 |
| `elevationu` | `xsd:string` | true | 0..1 |
| `geoidundul` | `xsd:string` | true | 0..1 |
| `mobile` | `xsd:string` | true | 0..1 |
| `magvaracc` | `xsd:decimal` | true | 0..1 |
| `flightchec` | `xsd:string` | true | 0..1 |
| `txtrmk_co1` | `xsd:string` | true | 0..1 |
| `bltype` | `xsd:string` | true | 0..1 |
| `rotaer_rmk` | `xsd:string` | true | 0..1 |
| `rwyremark` | `xsd:string` | true | 0..1 |
| `purpose` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `emenda` | `xsd:date` | true | 0..1 |
| `emenda_futura` | `xsd:date` | true | 0..1 |
| `latitude_gms` | `xsd:string` | true | 0..1 |
| `longitude_gms` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |

### `ICA:vw_aerovia_alta`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `airwayseg_` | `xsd:decimal` | true | 0..1 |
| `effectived` | `xsd:date` | true | 0..1 |
| `updatedt` | `xsd:date` | true | 0..1 |
| `airspace_p` | `xsd:decimal` | true | 0..1 |
| `airspace_1` | `xsd:decimal` | true | 0..1 |
| `airspace_2` | `xsd:decimal` | true | 0..1 |
| `airspace_3` | `xsd:decimal` | true | 0..1 |
| `airspace_4` | `xsd:decimal` | true | 0..1 |
| `updateoper` | `xsd:string` | true | 0..1 |
| `airway_pk` | `xsd:decimal` | true | 0..1 |
| `source` | `xsd:string` | true | 0..1 |
| `diffind` | `xsd:string` | true | 0..1 |
| `mslink` | `xsd:decimal` | true | 0..1 |
| `mapid` | `xsd:decimal` | true | 0..1 |
| `codetype` | `xsd:string` | true | 0..1 |
| `seq` | `xsd:decimal` | true | 0..1 |
| `codernp` | `xsd:decimal` | true | 0..1 |
| `levl` | `xsd:string` | true | 0..1 |
| `codeclassa` | `xsd:string` | true | 0..1 |
| `upperlimit` | `xsd:decimal` | true | 0..1 |
| `uomupperli` | `xsd:string` | true | 0..1 |
| `codedistve` | `xsd:string` | true | 0..1 |
| `lowerlimit` | `xsd:decimal` | true | 0..1 |
| `uomlowerli` | `xsd:string` | true | 0..1 |
| `codedistv1` | `xsd:string` | true | 0..1 |
| `mnmlimit` | `xsd:decimal` | true | 0..1 |
| `uommnmlimi` | `xsd:string` | true | 0..1 |
| `codedistv2` | `xsd:string` | true | 0..1 |
| `ovrdelower` | `xsd:decimal` | true | 0..1 |
| `uomlwrlmto` | `xsd:string` | true | 0..1 |
| `codedstver` | `xsd:string` | true | 0..1 |
| `fromfixdes` | `xsd:string` | true | 0..1 |
| `fromfixde1` | `xsd:string` | true | 0..1 |
| `fromfixde2` | `xsd:string` | true | 0..1 |
| `fromfixde3` | `xsd:string` | true | 0..1 |
| `tofixdesc1` | `xsd:string` | true | 0..1 |
| `tofixdesc2` | `xsd:string` | true | 0..1 |
| `tofixdesc3` | `xsd:string` | true | 0..1 |
| `tofixdesc4` | `xsd:string` | true | 0..1 |
| `rvsmstart` | `xsd:string` | true | 0..1 |
| `rvsmend` | `xsd:string` | true | 0..1 |
| `pathtype` | `xsd:string` | true | 0..1 |
| `intruetrac` | `xsd:decimal` | true | 0..1 |
| `inmagtrack` | `xsd:decimal` | true | 0..1 |
| `revtruetra` | `xsd:decimal` | true | 0..1 |
| `revmagtrac` | `xsd:decimal` | true | 0..1 |
| `routedis` | `xsd:decimal` | true | 0..1 |
| `changeover` | `xsd:decimal` | true | 0..1 |
| `uomdist` | `xsd:string` | true | 0..1 |
| `segmnt_pk` | `xsd:decimal` | true | 0..1 |
| `txtrmk` | `xsd:string` | true | 0..1 |
| `areacode` | `xsd:string` | true | 0..1 |
| `boundary` | `xsd:string` | true | 0..1 |
| `directrest` | `xsd:string` | true | 0..1 |
| `cruiseid` | `xsd:string` | true | 0..1 |
| `theta` | `xsd:decimal` | true | 0..1 |
| `rho` | `xsd:decimal` | true | 0..1 |
| `vor_pk` | `xsd:decimal` | true | 0..1 |
| `cruisedir` | `xsd:string` | true | 0..1 |
| `mnmlimitre` | `xsd:decimal` | true | 0..1 |
| `uommnmlim1` | `xsd:string` | true | 0..1 |
| `codedistv3` | `xsd:string` | true | 0..1 |
| `fixradtran` | `xsd:decimal` | true | 0..1 |
| `vor_pk2` | `xsd:decimal` | true | 0..1 |
| `totheta` | `xsd:decimal` | true | 0..1 |
| `torho` | `xsd:decimal` | true | 0..1 |
| `codedistv4` | `xsd:string` | true | 0..1 |
| `minlev` | `xsd:decimal` | true | 0..1 |
| `uomminlev` | `xsd:string` | true | 0..1 |
| `txtrmk_lcl` | `xsd:string` | true | 0..1 |
| `nonrnavusa` | `xsd:string` | true | 0..1 |
| `minobsclea` | `xsd:decimal` | true | 0..1 |
| `minobscle1` | `xsd:string` | true | 0..1 |
| `widthleft` | `xsd:decimal` | true | 0..1 |
| `widthleftu` | `xsd:string` | true | 0..1 |
| `widthright` | `xsd:decimal` | true | 0..1 |
| `widthrigh1` | `xsd:string` | true | 0..1 |
| `turndirect` | `xsd:string` | true | 0..1 |
| `signalgap` | `xsd:string` | true | 0..1 |
| `minenroute` | `xsd:decimal` | true | 0..1 |
| `minenrout1` | `xsd:string` | true | 0..1 |
| `mincrossin` | `xsd:decimal` | true | 0..1 |
| `mincrossi1` | `xsd:string` | true | 0..1 |
| `mincrossi2` | `xsd:string` | true | 0..1 |
| `maxcrossin` | `xsd:decimal` | true | 0..1 |
| `maxcrossi1` | `xsd:string` | true | 0..1 |
| `maxcrossi2` | `xsd:string` | true | 0..1 |
| `designator` | `xsd:string` | true | 0..1 |
| `to_airep_r` | `xsd:string` | true | 0..1 |
| `from_airep` | `xsd:string` | true | 0..1 |
| `bltype` | `xsd:string` | true | 0..1 |
| `airway_pk1` | `xsd:decimal` | true | 0..1 |
| `effective1` | `xsd:date` | true | 0..1 |
| `updatedt1` | `xsd:date` | true | 0..1 |
| `updateope1` | `xsd:string` | true | 0..1 |
| `source1` | `xsd:string` | true | 0..1 |
| `diffind1` | `xsd:string` | true | 0..1 |
| `mslink1` | `xsd:decimal` | true | 0..1 |
| `mapid1` | `xsd:decimal` | true | 0..1 |
| `txtdesig` | `xsd:string` | true | 0..1 |
| `txtlocdesi` | `xsd:string` | true | 0..1 |
| `txtrmk1` | `xsd:string` | true | 0..1 |
| `euindicato` | `xsd:string` | true | 0..1 |
| `txtrmk_lc1` | `xsd:string` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `flightrule` | `xsd:string` | true | 0..1 |
| `internatio` | `xsd:string` | true | 0..1 |
| `militaryus` | `xsd:string` | true | 0..1 |
| `miltraning` | `xsd:string` | true | 0..1 |
| `orgauth_pk` | `xsd:decimal` | true | 0..1 |
| `bltype1` | `xsd:string` | true | 0..1 |
| `emenda` | `xsd:date` | true | 0..1 |
| `emenda_futura` | `xsd:date` | true | 0..1 |

### `ICA:vw_aerovia_alta_v2`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `geom` | `gml:CurvePropertyType` | true | 0..1 |
| `airwayseg_pk` | `xsd:decimal` | true | 0..1 |
| `effectived` | `xsd:date` | true | 0..1 |
| `airway_pk` | `xsd:decimal` | true | 0..1 |
| `code_type` | `xsd:string` | true | 0..1 |
| `sequence` | `xsd:decimal` | true | 0..1 |
| `level` | `xsd:string` | true | 0..1 |
| `upper_limit` | `xsd:decimal` | true | 0..1 |
| `uom_upper_limit` | `xsd:string` | true | 0..1 |
| `code_vertical_distance_upper` | `xsd:string` | true | 0..1 |
| `lower_limit` | `xsd:decimal` | true | 0..1 |
| `uom_lower_limit` | `xsd:string` | true | 0..1 |
| `code_vertical_distance_lower` | `xsd:string` | true | 0..1 |
| `initial_true_track` | `xsd:decimal` | true | 0..1 |
| `initial_magnetic_track` | `xsd:decimal` | true | 0..1 |
| `reverse_true_track` | `xsd:decimal` | true | 0..1 |
| `reverse_magnetic_track` | `xsd:decimal` | true | 0..1 |
| `segmnt_pk` | `xsd:decimal` | true | 0..1 |
| `text_remark` | `xsd:string` | true | 0..1 |
| `minimumn_level` | `xsd:decimal` | true | 0..1 |
| `uom_minimumn_level` | `xsd:string` | true | 0..1 |
| `code_vertical_distance_minimumn_level` | `xsd:string` | true | 0..1 |
| `text_remark_local_language` | `xsd:string` | true | 0..1 |
| `to_airep_report` | `xsd:string` | true | 0..1 |
| `from_airep_report` | `xsd:string` | true | 0..1 |
| `text_designator` | `xsd:string` | true | 0..1 |
| `area_designator` | `xsd:string` | true | 0..1 |
| `airway_text_remark` | `xsd:string` | true | 0..1 |
| `airway_text_remark_local_language` | `xsd:string` | true | 0..1 |
| `direction` | `xsd:string` | true | 0..1 |
| `segment_length` | `xsd:double` | true | 0..1 |
| `segment_length_uom` | `xsd:string` | true | 0..1 |
| `from_fix_fea` | `xsd:int` | true | 0..1 |
| `from_fix_pk` | `xsd:int` | true | 0..1 |
| `to_fix_fea` | `xsd:int` | true | 0..1 |
| `to_fix_pk` | `xsd:int` | true | 0..1 |
| `from_fix_type` | `xsd:string` | true | 0..1 |
| `from_fix_ident` | `xsd:string` | true | 0..1 |
| `to_fix_type` | `xsd:string` | true | 0..1 |
| `to_fix_ident` | `xsd:string` | true | 0..1 |
| `emenda` | `xsd:date` | true | 0..1 |
| `emenda_futura` | `xsd:date` | true | 0..1 |

### `ICA:vw_aerovia_baixa`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `airwayseg_` | `xsd:decimal` | true | 0..1 |
| `effectived` | `xsd:date` | true | 0..1 |
| `updatedt` | `xsd:date` | true | 0..1 |
| `airspace_p` | `xsd:decimal` | true | 0..1 |
| `airspace_1` | `xsd:decimal` | true | 0..1 |
| `airspace_2` | `xsd:decimal` | true | 0..1 |
| `airspace_3` | `xsd:decimal` | true | 0..1 |
| `airspace_4` | `xsd:decimal` | true | 0..1 |
| `updateoper` | `xsd:string` | true | 0..1 |
| `airway_pk` | `xsd:decimal` | true | 0..1 |
| `source` | `xsd:string` | true | 0..1 |
| `diffind` | `xsd:string` | true | 0..1 |
| `mslink` | `xsd:decimal` | true | 0..1 |
| `mapid` | `xsd:decimal` | true | 0..1 |
| `codetype` | `xsd:string` | true | 0..1 |
| `seq` | `xsd:decimal` | true | 0..1 |
| `codernp` | `xsd:decimal` | true | 0..1 |
| `levl` | `xsd:string` | true | 0..1 |
| `codeclassa` | `xsd:string` | true | 0..1 |
| `upperlimit` | `xsd:decimal` | true | 0..1 |
| `uomupperli` | `xsd:string` | true | 0..1 |
| `codedistve` | `xsd:string` | true | 0..1 |
| `lowerlimit` | `xsd:decimal` | true | 0..1 |
| `uomlowerli` | `xsd:string` | true | 0..1 |
| `codedistv1` | `xsd:string` | true | 0..1 |
| `mnmlimit` | `xsd:decimal` | true | 0..1 |
| `uommnmlimi` | `xsd:string` | true | 0..1 |
| `codedistv2` | `xsd:string` | true | 0..1 |
| `ovrdelower` | `xsd:decimal` | true | 0..1 |
| `uomlwrlmto` | `xsd:string` | true | 0..1 |
| `codedstver` | `xsd:string` | true | 0..1 |
| `fromfixdes` | `xsd:string` | true | 0..1 |
| `fromfixde1` | `xsd:string` | true | 0..1 |
| `fromfixde2` | `xsd:string` | true | 0..1 |
| `fromfixde3` | `xsd:string` | true | 0..1 |
| `tofixdesc1` | `xsd:string` | true | 0..1 |
| `tofixdesc2` | `xsd:string` | true | 0..1 |
| `tofixdesc3` | `xsd:string` | true | 0..1 |
| `tofixdesc4` | `xsd:string` | true | 0..1 |
| `rvsmstart` | `xsd:string` | true | 0..1 |
| `rvsmend` | `xsd:string` | true | 0..1 |
| `pathtype` | `xsd:string` | true | 0..1 |
| `intruetrac` | `xsd:decimal` | true | 0..1 |
| `inmagtrack` | `xsd:decimal` | true | 0..1 |
| `revtruetra` | `xsd:decimal` | true | 0..1 |
| `revmagtrac` | `xsd:decimal` | true | 0..1 |
| `routedis` | `xsd:decimal` | true | 0..1 |
| `changeover` | `xsd:decimal` | true | 0..1 |
| `uomdist` | `xsd:string` | true | 0..1 |
| `segmnt_pk` | `xsd:decimal` | true | 0..1 |
| `txtrmk` | `xsd:string` | true | 0..1 |
| `areacode` | `xsd:string` | true | 0..1 |
| `boundary` | `xsd:string` | true | 0..1 |
| `directrest` | `xsd:string` | true | 0..1 |
| `cruiseid` | `xsd:string` | true | 0..1 |
| `theta` | `xsd:decimal` | true | 0..1 |
| `rho` | `xsd:decimal` | true | 0..1 |
| `vor_pk` | `xsd:decimal` | true | 0..1 |
| `cruisedir` | `xsd:string` | true | 0..1 |
| `mnmlimitre` | `xsd:decimal` | true | 0..1 |
| `uommnmlim1` | `xsd:string` | true | 0..1 |
| `codedistv3` | `xsd:string` | true | 0..1 |
| `fixradtran` | `xsd:decimal` | true | 0..1 |
| `vor_pk2` | `xsd:decimal` | true | 0..1 |
| `totheta` | `xsd:decimal` | true | 0..1 |
| `torho` | `xsd:decimal` | true | 0..1 |
| `codedistv4` | `xsd:string` | true | 0..1 |
| `minlev` | `xsd:decimal` | true | 0..1 |
| `uomminlev` | `xsd:string` | true | 0..1 |
| `txtrmk_lcl` | `xsd:string` | true | 0..1 |
| `nonrnavusa` | `xsd:string` | true | 0..1 |
| `minobsclea` | `xsd:decimal` | true | 0..1 |
| `minobscle1` | `xsd:string` | true | 0..1 |
| `widthleft` | `xsd:decimal` | true | 0..1 |
| `widthleftu` | `xsd:string` | true | 0..1 |
| `widthright` | `xsd:decimal` | true | 0..1 |
| `widthrigh1` | `xsd:string` | true | 0..1 |
| `turndirect` | `xsd:string` | true | 0..1 |
| `signalgap` | `xsd:string` | true | 0..1 |
| `minenroute` | `xsd:decimal` | true | 0..1 |
| `minenrout1` | `xsd:string` | true | 0..1 |
| `mincrossin` | `xsd:decimal` | true | 0..1 |
| `mincrossi1` | `xsd:string` | true | 0..1 |
| `mincrossi2` | `xsd:string` | true | 0..1 |
| `maxcrossin` | `xsd:decimal` | true | 0..1 |
| `maxcrossi1` | `xsd:string` | true | 0..1 |
| `maxcrossi2` | `xsd:string` | true | 0..1 |
| `designator` | `xsd:string` | true | 0..1 |
| `to_airep_r` | `xsd:string` | true | 0..1 |
| `from_airep` | `xsd:string` | true | 0..1 |
| `bltype` | `xsd:string` | true | 0..1 |
| `airway_pk1` | `xsd:decimal` | true | 0..1 |
| `effective1` | `xsd:date` | true | 0..1 |
| `updatedt1` | `xsd:date` | true | 0..1 |
| `updateope1` | `xsd:string` | true | 0..1 |
| `source1` | `xsd:string` | true | 0..1 |
| `diffind1` | `xsd:string` | true | 0..1 |
| `mslink1` | `xsd:decimal` | true | 0..1 |
| `mapid1` | `xsd:decimal` | true | 0..1 |
| `txtdesig` | `xsd:string` | true | 0..1 |
| `txtlocdesi` | `xsd:string` | true | 0..1 |
| `txtrmk1` | `xsd:string` | true | 0..1 |
| `euindicato` | `xsd:string` | true | 0..1 |
| `txtrmk_lc1` | `xsd:string` | true | 0..1 |
| `type` | `xsd:string` | true | 0..1 |
| `flightrule` | `xsd:string` | true | 0..1 |
| `internatio` | `xsd:string` | true | 0..1 |
| `militaryus` | `xsd:string` | true | 0..1 |
| `miltraning` | `xsd:string` | true | 0..1 |
| `orgauth_pk` | `xsd:decimal` | true | 0..1 |
| `bltype1` | `xsd:string` | true | 0..1 |
| `emenda` | `xsd:date` | true | 0..1 |
| `emenda_futura` | `xsd:date` | true | 0..1 |

### `ICA:vw_aerovia_baixa_v2`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `geom` | `gml:CurvePropertyType` | true | 0..1 |
| `airwayseg_pk` | `xsd:decimal` | true | 0..1 |
| `effectived` | `xsd:date` | true | 0..1 |
| `airway_pk` | `xsd:decimal` | true | 0..1 |
| `code_type` | `xsd:string` | true | 0..1 |
| `sequence` | `xsd:decimal` | true | 0..1 |
| `level` | `xsd:string` | true | 0..1 |
| `upper_limit` | `xsd:decimal` | true | 0..1 |
| `uom_upper_limit` | `xsd:string` | true | 0..1 |
| `code_vertical_distance_upper` | `xsd:string` | true | 0..1 |
| `lower_limit` | `xsd:decimal` | true | 0..1 |
| `uom_lower_limit` | `xsd:string` | true | 0..1 |
| `code_vertical_distance_lower` | `xsd:string` | true | 0..1 |
| `initial_true_track` | `xsd:decimal` | true | 0..1 |
| `initial_magnetic_track` | `xsd:decimal` | true | 0..1 |
| `reverse_true_track` | `xsd:decimal` | true | 0..1 |
| `reverse_magnetic_track` | `xsd:decimal` | true | 0..1 |
| `segmnt_pk` | `xsd:decimal` | true | 0..1 |
| `text_remark` | `xsd:string` | true | 0..1 |
| `minimumn_level` | `xsd:decimal` | true | 0..1 |
| `uom_minimumn_level` | `xsd:string` | true | 0..1 |
| `code_vertical_distance_minimumn_level` | `xsd:string` | true | 0..1 |
| `text_remark_local_language` | `xsd:string` | true | 0..1 |
| `to_airep_report` | `xsd:string` | true | 0..1 |
| `from_airep_report` | `xsd:string` | true | 0..1 |
| `text_designator` | `xsd:string` | true | 0..1 |
| `area_designator` | `xsd:string` | true | 0..1 |
| `airway_text_remark` | `xsd:string` | true | 0..1 |
| `airway_text_remark_local_language` | `xsd:string` | true | 0..1 |
| `direction` | `xsd:string` | true | 0..1 |
| `segment_length` | `xsd:double` | true | 0..1 |
| `segment_length_uom` | `xsd:string` | true | 0..1 |
| `from_fix_fea` | `xsd:int` | true | 0..1 |
| `from_fix_pk` | `xsd:int` | true | 0..1 |
| `to_fix_fea` | `xsd:int` | true | 0..1 |
| `to_fix_pk` | `xsd:int` | true | 0..1 |
| `from_fix_type` | `xsd:string` | true | 0..1 |
| `from_fix_ident` | `xsd:string` | true | 0..1 |
| `to_fix_type` | `xsd:string` | true | 0..1 |
| `to_fix_ident` | `xsd:string` | true | 0..1 |
| `emenda` | `xsd:date` | true | 0..1 |
| `emenda_futura` | `xsd:date` | true | 0..1 |

### `ICA:vw_busca_feature_name`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:string` | true | 0..1 |
| `feattype` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `ICA:waypoint`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `waypoint_p` | `xsd:decimal` | true | 0..1 |
| `effectived` | `xsd:date` | true | 0..1 |
| `airspace_p` | `xsd:decimal` | true | 0..1 |
| `airspace_1` | `xsd:decimal` | true | 0..1 |
| `assocpoint` | `xsd:decimal` | true | 0..1 |
| `assocpoin1` | `xsd:decimal` | true | 0..1 |
| `ident` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:decimal` | true | 0..1 |
| `longitude` | `xsd:decimal` | true | 0..1 |
| `codetype` | `xsd:string` | true | 0..1 |
| `typ1` | `xsd:string` | true | 0..1 |
| `typ2` | `xsd:string` | true | 0..1 |
| `typ3` | `xsd:string` | true | 0..1 |
| `usage1` | `xsd:string` | true | 0..1 |
| `usage2` | `xsd:string` | true | 0..1 |
| `areacode` | `xsd:string` | true | 0..1 |
| `icaocode` | `xsd:string` | true | 0..1 |
| `nam` | `xsd:string` | true | 0..1 |
| `magvariati` | `xsd:decimal` | true | 0..1 |
| `nameind1` | `xsd:string` | true | 0..1 |
| `nameind2` | `xsd:string` | true | 0..1 |
| `magvardate` | `xsd:date` | true | 0..1 |
| `codedatum` | `xsd:string` | true | 0..1 |
| `valgeoaccu` | `xsd:decimal` | true | 0..1 |
| `uomgeoaccu` | `xsd:string` | true | 0..1 |
| `valcrc` | `xsd:string` | true | 0..1 |
| `txtrmk` | `xsd:string` | true | 0..1 |
| `txtrmk_lcl` | `xsd:string` | true | 0..1 |
| `bltype` | `xsd:string` | true | 0..1 |
| `rpt_role` | `xsd:string` | true | 0..1 |
| `rpt_priorf` | `xsd:decimal` | true | 0..1 |
| `rpt_prior1` | `xsd:string` | true | 0..1 |
| `rpt_postfi` | `xsd:decimal` | true | 0..1 |
| `rpt_postf1` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `emenda` | `xsd:date` | true | 0..1 |
| `emenda_futura` | `xsd:date` | true | 0..1 |
| `latitude_gms` | `xsd:string` | true | 0..1 |
| `longitude_gms` | `xsd:string` | true | 0..1 |

### `ICA:waypoint_aisweb`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `pk` | `xsd:decimal` | true | 0..1 |
| `efetivação` | `xsd:date` | true | 0..1 |
| `ident` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:decimal` | true | 0..1 |
| `latitude_gms` | `xsd:string` | true | 0..1 |
| `longitude` | `xsd:decimal` | true | 0..1 |
| `longitude_gms` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `varmag` | `xsd:decimal` | true | 0..1 |
| `datavarmag` | `xsd:date` | true | 0..1 |
| `emenda` | `xsd:date` | true | 0..1 |
| `emenda_futura` | `xsd:date` | true | 0..1 |
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |

### `ICA:zida`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `gm_layer` | `xsd:string` | true | 0..1 |
| `map_name` | `xsd:string` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `id_pais` | `xsd:int` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `nomeabrev` | `xsd:string` | true | 0..1 |
| `geometriaa` | `xsd:string` | true | 0..1 |
| `sigla` | `xsd:string` | true | 0..1 |
| `codiso3166` | `xsd:string` | true | 0..1 |
| `closed` | `xsd:string` | true | 0..1 |
| `border_sty` | `xsd:string` | true | 0..1 |
| `border_col` | `xsd:string` | true | 0..1 |
| `border_wid` | `xsd:short` | true | 0..1 |
| `fill_style` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
