# Instituto Geográfico Militar — IGM — IGM 1M — atributos

Geoportal: [[Geosserviços/Equador IGM 1M/Instituto Geográfico Militar — IGM — IGM 1M|Instituto Geográfico Militar — IGM — IGM 1M]]


### `igm:aeropuertos`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiPointPropertyType` |
| `objectid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcio` | `xsd:string` |
| `nam` | `xsd:string` |
| `acc` | `xsd:int` |
| `acc_desc` | `xsd:string` |
| `iko` | `xsd:string` |
| `agg` | `xsd:int` |
| `agg_desc` | `xsd:string` |
| `fuc` | `xsd:int` |
| `fuc_desc` | `xsd:string` |
| `txt` | `xsd:string` |
| `sim_prioridad` | `xsd:int` |
| `sim_escala_minima` | `xsd:int` |
| `sim_escala_maxima` | `xsd:int` |
| `aeropuertos` | `igm:aeropuertosType` |

### `igm:aeropuertos_anterior`

| Campo | Tipo |
|---|---|
| `f_code` | `xsd:string` |
| `nombre` | `xsd:string` |
| `use` | `xsd:int` |
| `uso` | `xsd:string` |
| `soc` | `xsd:string` |
| `the_geom` | `gml:PointPropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `aeropuertos_anterior` | `igm:aeropuertos_anteriorType` |

### `igm:america_del_sur_a`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `soberania` | `xsd:string` |
| `tipo` | `xsd:string` |
| `administra` | `xsd:string` |
| `pais` | `xsd:string` |
| `capital` | `xsd:string` |
| `fuente` | `xsd:string` |
| `txt` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `america_del_sur_a` | `igm:america_del_sur_aType` |

### `igm:america_sur_central_a`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `soberania` | `xsd:string` |
| `tipo` | `xsd:string` |
| `administracion` | `xsd:string` |
| `pais` | `xsd:string` |
| `capital` | `xsd:string` |
| `fuente` | `xsd:string` |
| `txt` | `xsd:string` |
| `america_sur_central_a` | `igm:america_sur_central_aType` |

### `igm:ferrocarril`

| Campo | Tipo |
|---|---|
| `f_code` | `xsd:string` |
| `exs` | `xsd:int` |
| `existencia` | `xsd:string` |
| `soc` | `xsd:string` |
| `the_geom` | `gml:CurvePropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `ferrocarril` | `igm:ferrocarrilType` |

### `igm:islas`

| Campo | Tipo |
|---|---|
| `f_code` | `xsd:string` |
| `nam` | `xsd:string` |
| `soc` | `xsd:string` |
| `the_geom` | `gml:SurfacePropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `islas` | `igm:islasType` |

### `igm:lago_laguna`

| Campo | Tipo |
|---|---|
| `f_code` | `xsd:string` |
| `nam` | `xsd:string` |
| `hyc` | `xsd:int` |
| `cat_hidro` | `xsd:string` |
| `soc` | `xsd:string` |
| `the_geom` | `gml:MultiPolygonPropertyType` |
| `na2` | `xsd:string` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `lago_laguna` | `igm:lago_lagunaType` |

### `igm:lim_costanero`

| Campo | Tipo |
|---|---|
| `f_code` | `xsd:string` |
| `descripcio` | `xsd:string` |
| `soc` | `xsd:string` |
| `the_geom` | `gml:CurvePropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `lim_costanero` | `igm:lim_costaneroType` |

### `igm:limite`

| Campo | Tipo |
|---|---|
| `fcode` | `xsd:string` |
| `descripcio` | `xsd:string` |
| `acc` | `xsd:decimal` |
| `acc_desc` | `xsd:string` |
| `bst` | `xsd:decimal` |
| `bst_desc` | `xsd:string` |
| `nm3` | `xsd:string` |
| `nm4` | `xsd:string` |
| `fuc` | `xsd:decimal` |
| `fuc_desc` | `xsd:string` |
| `rpc` | `xsd:decimal` |
| `rpc_desc` | `xsd:string` |
| `fuente` | `xsd:string` |
| `txt` | `xsd:string` |
| `shape_leng` | `xsd:decimal` |
| `the_geom` | `gml:MultiCurvePropertyType` |
| `limite` | `igm:limiteType` |

### `igm:limite_maritimo_l`

| Campo | Tipo |
|---|---|
| `fcode` | `xsd:string` |
| `descripcio` | `xsd:string` |
| `mnr` | `xsd:short` |
| `mnr_desc` | `xsd:string` |
| `mrr` | `xsd:short` |
| `mrr_desc` | `xsd:string` |
| `txt` | `xsd:string` |
| `shape_leng` | `xsd:decimal` |
| `the_geom` | `gml:MultiCurvePropertyType` |
| `limite_maritimo_l` | `igm:limite_maritimo_lType` |

### `igm:limite_provincial_a_2023`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `dpa_provin` | `xsd:string` |
| `dpa_despro` | `xsd:string` |
| `fcode` | `xsd:string` |
| `dpa_anio` | `xsd:string` |
| `limite_provincial_a_2023` | `igm:limite_provincial_a_2023Type` |

### `igm:limite_provincial_l_2023`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `lot` | `xsd:string` |
| `trm` | `xsd:string` |
| `fcode` | `xsd:string` |
| `not_` | `xsd:string` |
| `elt` | `xsd:string` |
| `limite_provincial_l_2023` | `igm:limite_provincial_l_2023Type` |

### `igm:mar_a`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `txt` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `mar_a` | `igm:mar_aType` |

### `igm:pista_aterrizaje_p`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiPointPropertyType` |
| `objectid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `nam` | `xsd:string` |
| `acc` | `xsd:int` |
| `acc_desc` | `xsd:string` |
| `fuc` | `xsd:int` |
| `fuc_desc` | `xsd:string` |
| `rst` | `xsd:int` |
| `rst_desc` | `xsd:string` |
| `txt` | `xsd:string` |
| `sim_prioridad` | `xsd:int` |
| `sim_escala_minima` | `xsd:int` |
| `sim_escala_maxima` | `xsd:int` |
| `pista_aterrizaje_p` | `igm:pista_aterrizaje_pType` |

### `igm:poblados`

| Campo | Tipo |
|---|---|
| `fcode` | `xsd:string` |
| `descripcio` | `xsd:string` |
| `nam` | `xsd:string` |
| `na2` | `xsd:string` |
| `ppt` | `xsd:int` |
| `ppt_desc` | `xsd:string` |
| `nute` | `xsd:string` |
| `txt` | `xsd:string` |
| `sim_prioridad` | `xsd:int` |
| `sim_escala_minima` | `xsd:int` |
| `sim_escala_maxima` | `xsd:int` |
| `the_geom` | `gml:PointPropertyType` |
| `poblados` | `igm:pobladosType` |

### `igm:poblados_tematica`

| Campo | Tipo |
|---|---|
| `fcode` | `xsd:string` |
| `descripcio` | `xsd:string` |
| `nam` | `xsd:string` |
| `na2` | `xsd:string` |
| `ppt` | `xsd:int` |
| `ppt_desc` | `xsd:string` |
| `nute` | `xsd:string` |
| `txt` | `xsd:string` |
| `sim_prioridad` | `xsd:int` |
| `sim_escala_minima` | `xsd:int` |
| `sim_escala_maxima` | `xsd:int` |
| `the_geom` | `gml:PointPropertyType` |
| `poblados_tematica` | `igm:poblados_tematicaType` |

### `igm:provincias`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:GeometryPropertyType` |
| `cod_region` | `xsd:int` |
| `region` | `xsd:string` |
| `cod_provin` | `xsd:int` |
| `provincia` | `xsd:string` |
| `capital` | `xsd:string` |
| `txt` | `xsd:string` |
| `area` | `xsd:int` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `provincias` | `igm:provinciasType` |

### `igm:represas`

| Campo | Tipo |
|---|---|
| `f_code` | `xsd:string` |
| `nam` | `xsd:string` |
| `soc` | `xsd:string` |
| `the_geom` | `gml:SurfacePropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `represas` | `igm:represasType` |

### `igm:rio_doble`

| Campo | Tipo |
|---|---|
| `f_code` | `xsd:string` |
| `nam` | `xsd:string` |
| `hyc` | `xsd:int` |
| `cat_hidro` | `xsd:string` |
| `soc` | `xsd:string` |
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `rio_doble` | `igm:rio_dobleType` |

### `igm:rio_doble_tematica`

| Campo | Tipo |
|---|---|
| `f_code` | `xsd:string` |
| `nam` | `xsd:string` |
| `hyc` | `xsd:int` |
| `cat_hidro` | `xsd:string` |
| `soc` | `xsd:string` |
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `rio_doble_tematica` | `igm:rio_doble_tematicaType` |

### `igm:rio_torrente`

| Campo | Tipo |
|---|---|
| `f_code` | `xsd:string` |
| `nam` | `xsd:string` |
| `hyc` | `xsd:int` |
| `cat_hidro` | `xsd:string` |
| `soc` | `xsd:string` |
| `the_geom` | `gml:CurvePropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `rio_torrente` | `igm:rio_torrenteType` |

### `igm:rio_torrente_tematica`

| Campo | Tipo |
|---|---|
| `f_code` | `xsd:string` |
| `nam` | `xsd:string` |
| `hyc` | `xsd:int` |
| `cat_hidro` | `xsd:string` |
| `soc` | `xsd:string` |
| `the_geom` | `gml:CurvePropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `rio_torrente_tematica` | `igm:rio_torrente_tematicaType` |

### `igm:rodera_l_ojo`

| Campo | Tipo |
|---|---|
| `fcode` | `xsd:string` |
| `descripcio` | `xsd:string` |
| `typ` | `xsd:int` |
| `typ_desc` | `xsd:string` |
| `rst` | `xsd:int` |
| `rst_desc` | `xsd:string` |
| `hct` | `xsd:int` |
| `hct_desc` | `xsd:string` |
| `rdt` | `xsd:int` |
| `rdt_desc` | `xsd:string` |
| `wtc` | `xsd:int` |
| `wtc_desc` | `xsd:string` |
| `ltn` | `xsd:decimal` |
| `tuc` | `xsd:int` |
| `tuc_desc` | `xsd:string` |
| `txt` | `xsd:string` |
| `shape_leng` | `xsd:decimal` |
| `sim_prioridad` | `xsd:int` |
| `sim_escala_minima` | `xsd:int` |
| `sim_escala_maxima` | `xsd:int` |
| `the_geom` | `gml:MultiCurvePropertyType` |
| `rodera_l_ojo` | `igm:rodera_l_ojoType` |

### `igm:rodera_l_tematica`

| Campo | Tipo |
|---|---|
| `fcode` | `xsd:string` |
| `descripcio` | `xsd:string` |
| `typ` | `xsd:int` |
| `typ_desc` | `xsd:string` |
| `rst` | `xsd:int` |
| `rst_desc` | `xsd:string` |
| `hct` | `xsd:int` |
| `hct_desc` | `xsd:string` |
| `rdt` | `xsd:int` |
| `rdt_desc` | `xsd:string` |
| `wtc` | `xsd:int` |
| `wtc_desc` | `xsd:string` |
| `ltn` | `xsd:decimal` |
| `tuc` | `xsd:int` |
| `tuc_desc` | `xsd:string` |
| `txt` | `xsd:string` |
| `shape_leng` | `xsd:decimal` |
| `sim_prioridad` | `xsd:int` |
| `sim_escala_minima` | `xsd:int` |
| `sim_escala_maxima` | `xsd:int` |
| `the_geom` | `gml:MultiCurvePropertyType` |
| `rodera_l_tematica` | `igm:rodera_l_tematicaType` |

### `igm:sendero_l_OJO`

| Campo | Tipo |
|---|---|
| `fcode` | `xsd:string` |
| `descripcio` | `xsd:string` |
| `coe` | `xsd:int` |
| `coe_desc` | `xsd:string` |
| `wtc` | `xsd:int` |
| `wtc_desc` | `xsd:string` |
| `txt` | `xsd:string` |
| `shape_leng` | `xsd:decimal` |
| `sim_prioridad` | `xsd:int` |
| `sim_escala_minima` | `xsd:int` |
| `sim_escala_maxima` | `xsd:int` |
| `the_geom` | `gml:MultiCurvePropertyType` |
| `sendero_l_OJO` | `igm:sendero_l_OJOType` |

### `igm:sendero_l_tematica`

| Campo | Tipo |
|---|---|
| `fcode` | `xsd:string` |
| `descripcio` | `xsd:string` |
| `coe` | `xsd:int` |
| `coe_desc` | `xsd:string` |
| `wtc` | `xsd:int` |
| `wtc_desc` | `xsd:string` |
| `txt` | `xsd:string` |
| `shape_leng` | `xsd:decimal` |
| `sim_prioridad` | `xsd:int` |
| `sim_escala_minima` | `xsd:int` |
| `sim_escala_maxima` | `xsd:int` |
| `the_geom` | `gml:MultiCurvePropertyType` |
| `sendero_l_tematica` | `igm:sendero_l_tematicaType` |

### `igm:vias`

| Campo | Tipo |
|---|---|
| `fcode` | `xsd:string` |
| `descripcio` | `xsd:string` |
| `nam` | `xsd:string` |
| `na2` | `xsd:string` |
| `acc` | `xsd:int` |
| `acc_desc` | `xsd:string` |
| `rst` | `xsd:int` |
| `rst_desc` | `xsd:string` |
| `typ` | `xsd:int` |
| `typ_desc` | `xsd:string` |
| `hct` | `xsd:int` |
| `hct_desc` | `xsd:string` |
| `wtc` | `xsd:int` |
| `wtc_desc` | `xsd:string` |
| `loc` | `xsd:int` |
| `loc_desc` | `xsd:string` |
| `ltn` | `xsd:decimal` |
| `mes` | `xsd:decimal` |
| `tuc` | `xsd:int` |
| `tuc_desc` | `xsd:string` |
| `txt` | `xsd:string` |
| `rtn` | `xsd:string` |
| `rn2` | `xsd:string` |
| `sim_prioridad` | `xsd:int` |
| `sim_escala_minima` | `xsd:int` |
| `sim_escala_maxima` | `xsd:int` |
| `shape_leng` | `xsd:decimal` |
| `the_geom` | `gml:MultiCurvePropertyType` |
| `vias` | `igm:viasType` |

### `igm:vias_tematica_atrac_cult_nat_l`

| Campo | Tipo |
|---|---|
| `fcode` | `xsd:string` |
| `descripcio` | `xsd:string` |
| `nam` | `xsd:string` |
| `na2` | `xsd:string` |
| `acc` | `xsd:int` |
| `acc_desc` | `xsd:string` |
| `rst` | `xsd:int` |
| `rst_desc` | `xsd:string` |
| `typ` | `xsd:int` |
| `typ_desc` | `xsd:string` |
| `hct` | `xsd:int` |
| `hct_desc` | `xsd:string` |
| `wtc` | `xsd:int` |
| `wtc_desc` | `xsd:string` |
| `loc` | `xsd:int` |
| `loc_desc` | `xsd:string` |
| `ltn` | `xsd:decimal` |
| `mes` | `xsd:decimal` |
| `tuc` | `xsd:int` |
| `tuc_desc` | `xsd:string` |
| `txt` | `xsd:string` |
| `rtn` | `xsd:string` |
| `rn2` | `xsd:string` |
| `sim_prioridad` | `xsd:int` |
| `sim_escala_minima` | `xsd:int` |
| `sim_escala_maxima` | `xsd:int` |
| `shape_leng` | `xsd:decimal` |
| `the_geom` | `gml:MultiCurvePropertyType` |
| `vias_tematica_atrac_cult_nat_l` | `igm:vias_tematica_atrac_cult_nat_lType` |

### `igm:zona_edificada_a`

| Campo | Tipo |
|---|---|
| `fcode` | `xsd:string` |
| `descripcio` | `xsd:string` |
| `nam` | `xsd:string` |
| `na2` | `xsd:string` |
| `acc` | `xsd:int` |
| `acc_desc` | `xsd:string` |
| `nute` | `xsd:string` |
| `txt` | `xsd:string` |
| `shape_leng` | `xsd:decimal` |
| `shape_area` | `xsd:decimal` |
| `sim_prioridad` | `xsd:int` |
| `sim_escala_minima` | `xsd:int` |
| `sim_escala_maxima` | `xsd:int` |
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `zona_edificada_a` | `igm:zona_edificada_aType` |

### `igm:zona_edificada_a_republica_ecuador`

| Campo | Tipo |
|---|---|
| `fcode` | `xsd:string` |
| `descripcio` | `xsd:string` |
| `nam` | `xsd:string` |
| `na2` | `xsd:string` |
| `acc` | `xsd:int` |
| `acc_desc` | `xsd:string` |
| `nute` | `xsd:string` |
| `txt` | `xsd:string` |
| `shape_leng` | `xsd:decimal` |
| `shape_area` | `xsd:decimal` |
| `sim_prioridad` | `xsd:int` |
| `sim_escala_minima` | `xsd:int` |
| `sim_escala_maxima` | `xsd:int` |
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `zona_edificada_a_republica_ecuador` | `igm:zona_edificada_a_republica_ecuadorType` |

### `igm:zona_edificada_a_tematica`

| Campo | Tipo |
|---|---|
| `fcode` | `xsd:string` |
| `descripcio` | `xsd:string` |
| `nam` | `xsd:string` |
| `na2` | `xsd:string` |
| `acc` | `xsd:int` |
| `acc_desc` | `xsd:string` |
| `nute` | `xsd:string` |
| `txt` | `xsd:string` |
| `shape_leng` | `xsd:decimal` |
| `shape_area` | `xsd:decimal` |
| `sim_prioridad` | `xsd:int` |
| `sim_escala_minima` | `xsd:int` |
| `sim_escala_maxima` | `xsd:int` |
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `zona_edificada_a_tematica` | `igm:zona_edificada_a_tematicaType` |

### `nacional_2024:acantilado_l_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `nam` | `xsd:string` |
| `txt` | `xsd:string` |
| `the_geom` | `gml:CurvePropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `acantilado_l_2024` | `nacional_2024:acantilado_l_2024Type` |

### `nacional_2024:aeropuerto_p_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `nam` | `xsd:string` |
| `acc_desc` | `xsd:string` |
| `iko` | `xsd:string` |
| `agg_desc` | `xsd:string` |
| `fuc_desc` | `xsd:string` |
| `txt` | `xsd:string` |
| `the_geom` | `gml:PointPropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `aeropuerto_p_2024` | `nacional_2024:aeropuerto_p_2024Type` |

### `nacional_2024:america_del_sur_a_2024`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `soberania` | `xsd:string` |
| `tipo` | `xsd:string` |
| `administra` | `xsd:string` |
| `pais` | `xsd:string` |
| `capital` | `xsd:string` |
| `fuente` | `xsd:string` |
| `txt` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `america_del_sur_a_2024` | `nacional_2024:america_del_sur_a_2024Type` |

### `nacional_2024:area_plataforma_continental_l_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `NATION` | `xsd:string` |
| `INFORM` | `xsd:string` |
| `NINFOM` | `xsd:string` |
| `NTXTDS` | `xsd:string` |
| `SCAMAX` | `xsd:string` |
| `SCAMIN` | `xsd:string` |
| `TXTDSC` | `xsd:string` |
| `RECDAT` | `xsd:string` |
| `RECIND` | `xsd:string` |
| `SORDAT` | `xsd:string` |
| `SORIND` | `xsd:string` |
| `the_geom` | `gml:CurvePropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `area_plataforma_continental_l_2024` | `nacional_2024:area_plataforma_continental_l_2024Type` |

### `nacional_2024:curva_nivel_l_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `hqc_desc` | `xsd:string` |
| `ela_desc` | `xsd:string` |
| `crv` | `xsd:double` |
| `txt` | `xsd:string` |
| `the_geom` | `gml:CurvePropertyType` |
| `curva_nivel_l_2024` | `nacional_2024:curva_nivel_l_2024Type` |

### `nacional_2024:embalse_a_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `nam` | `xsd:string` |
| `hyp_desc` | `xsd:string` |
| `txt` | `xsd:string` |
| `the_geom` | `gml:SurfacePropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `embalse_a_2024` | `nacional_2024:embalse_a_2024Type` |

### `nacional_2024:faro_p_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `nam` | `xsd:string` |
| `txt` | `xsd:string` |
| `the_geom` | `gml:PointPropertyType` |
| `faro_p_2024` | `nacional_2024:faro_p_2024Type` |

### `nacional_2024:ferrocarril_l_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `nam` | `xsd:string` |
| `acc_desc` | `xsd:string` |
| `coe_desc` | `xsd:string` |
| `fco_desc` | `xsd:string` |
| `loc_desc` | `xsd:string` |
| `ltn` | `xsd:int` |
| `rgc_desc` | `xsd:string` |
| `rra_desc` | `xsd:string` |
| `rrc_desc` | `xsd:string` |
| `txt` | `xsd:string` |
| `the_geom` | `gml:CurvePropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `ferrocarril_l_2024` | `nacional_2024:ferrocarril_l_2024Type` |

### `nacional_2024:frontera_internacional_maritima_l_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `nam` | `xsd:string` |
| `txt` | `xsd:string` |
| `the_geom` | `gml:CurvePropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `frontera_internacional_maritima_l_2024` | `nacional_2024:frontera_internacional_maritima_l_2024Type` |

### `nacional_2024:hito_p_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `CATCTR_desc` | `xsd:string` |
| `DATEND` | `xsd:string` |
| `DATSTA` | `xsd:string` |
| `ELEVAT` | `xsd:string` |
| `NOBJNM` | `xsd:string` |
| `OBJNAM` | `xsd:string` |
| `VERACC` | `xsd:string` |
| `VERDAT_desc` | `xsd:string` |
| `INFORM` | `xsd:string` |
| `NINFOM` | `xsd:string` |
| `NTXTDS` | `xsd:string` |
| `PICREP` | `xsd:string` |
| `SCAMAX` | `xsd:string` |
| `SCAMIN` | `xsd:string` |
| `TXTDSC` | `xsd:string` |
| `RECDAT` | `xsd:string` |
| `RECIND` | `xsd:string` |
| `SORDAT` | `xsd:string` |
| `SORIND` | `xsd:string` |
| `nam` | `xsd:string` |
| `na2` | `xsd:string` |
| `txt` | `xsd:string` |
| `nfi` | `xsd:string` |
| `DPA_DESPRO` | `xsd:string` |
| `flv_desc` | `xsd:string` |
| `ncm` | `xsd:string` |
| `the_geom` | `gml:GeometryPropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `hito_p_2024` | `nacional_2024:hito_p_2024Type` |

### `nacional_2024:isla_a_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `nam` | `xsd:string` |
| `na2` | `xsd:string` |
| `txt` | `xsd:string` |
| `the_geom` | `gml:SurfacePropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `isla_a_2024` | `nacional_2024:isla_a_2024Type` |

### `nacional_2024:lago_laguna_a_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `nam` | `xsd:string` |
| `na2` | `xsd:string` |
| `hyp_desc` | `xsd:string` |
| `scc_desc` | `xsd:string` |
| `txt` | `xsd:string` |
| `the_geom` | `gml:SurfacePropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `lago_laguna_a_2024` | `nacional_2024:lago_laguna_a_2024Type` |

### `nacional_2024:limite_administrativo_l_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `acc_desc` | `xsd:string` |
| `bst_desc` | `xsd:string` |
| `nm3` | `xsd:string` |
| `nm4` | `xsd:string` |
| `fuc_desc` | `xsd:string` |
| `rpc_desc` | `xsd:string` |
| `fuente` | `xsd:string` |
| `txt` | `xsd:string` |
| `the_geom` | `gml:CurvePropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `limite_administrativo_l_2024` | `nacional_2024:limite_administrativo_l_2024Type` |

### `nacional_2024:limite_nieve_a_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `txt` | `xsd:string` |
| `the_geom` | `gml:SurfacePropertyType` |
| `limite_nieve_a_2024` | `nacional_2024:limite_nieve_a_2024Type` |

### `nacional_2024:limite_provincial_l_2024`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `lot` | `xsd:string` |
| `trm` | `xsd:string` |
| `fcode` | `xsd:string` |
| `not_` | `xsd:string` |
| `elt` | `xsd:string` |
| `limite_provincial_l_2024` | `nacional_2024:limite_provincial_l_2024Type` |

### `nacional_2024:linea_base_l_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `NATION` | `xsd:string` |
| `INFORM` | `xsd:string` |
| `NINFOM` | `xsd:string` |
| `NTXTDS` | `xsd:string` |
| `SCAMAX` | `xsd:string` |
| `SCAMIN` | `xsd:string` |
| `TXTDSC` | `xsd:string` |
| `RECDAT` | `xsd:string` |
| `RECIND` | `xsd:string` |
| `SORDAT` | `xsd:string` |
| `SORIND` | `xsd:string` |
| `the_geom` | `gml:CurvePropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `linea_base_l_2024` | `nacional_2024:linea_base_l_2024Type` |

### `nacional_2024:linea_costa_l_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `acc_desc` | `xsd:string` |
| `vdc_desc` | `xsd:string` |
| `txt` | `xsd:string` |
| `the_geom` | `gml:CurvePropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `linea_costa_l_2024` | `nacional_2024:linea_costa_l_2024Type` |

### `nacional_2024:mar_territorial_a_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `NATION` | `xsd:string` |
| `INFORM` | `xsd:string` |
| `RESTRN_desc` | `xsd:string` |
| `NINFOM` | `xsd:string` |
| `NTXTDS` | `xsd:string` |
| `SCAMAX` | `xsd:string` |
| `SCAMIN` | `xsd:string` |
| `TXTDSC` | `xsd:string` |
| `RECDAT` | `xsd:string` |
| `RECIND` | `xsd:string` |
| `SORDAT` | `xsd:string` |
| `SORIND` | `xsd:string` |
| `the_geom` | `gml:SurfacePropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `mar_territorial_a_2024` | `nacional_2024:mar_territorial_a_2024Type` |

### `nacional_2024:nombre_geografico_l`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `nam` | `xsd:string` |
| `gaz` | `xsd:int` |
| `gaz_desc` | `xsd:string` |
| `fna` | `xsd:string` |
| `txt` | `xsd:string` |
| `simb_prioridad` | `xsd:int` |
| `the_geom` | `gml:CurvePropertyType` |
| `nombre_geografico_l` | `nacional_2024:nombre_geografico_lType` |

### `nacional_2024:nombre_geografico_p_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `nam` | `xsd:string` |
| `gaz_desc` | `xsd:string` |
| `fna` | `xsd:string` |
| `txt` | `xsd:string` |
| `the_geom` | `gml:PointPropertyType` |
| `simb_prioridad` | `xsd:int` |
| `nombre_geografico_p_2024` | `nacional_2024:nombre_geografico_p_2024Type` |

### `nacional_2024:ORGANIZACION_TERRITORIAL_PROVINCIAL`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `dpa_provin` | `xsd:string` |
| `dpa_despro` | `xsd:string` |
| `fcode` | `xsd:string` |
| `dpa_anio` | `xsd:string` |
| `ORGANIZACION_TERRITORIAL_PROVINCIAL` | `nacional_2024:ORGANIZACION_TERRITORIAL_PROVINCIALType` |

### `nacional_2024:pista_aterrizaje_p_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `nam` | `xsd:string` |
| `acc_desc` | `xsd:string` |
| `fuc_desc` | `xsd:string` |
| `rst_desc` | `xsd:string` |
| `txt` | `xsd:string` |
| `the_geom` | `gml:PointPropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `pista_aterrizaje_p_2024` | `nacional_2024:pista_aterrizaje_p_2024Type` |

### `nacional_2024:poblado_p_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `nam` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `na2` | `xsd:string` |
| `ppt_desc` | `xsd:string` |
| `nute` | `xsd:string` |
| `txt` | `xsd:string` |
| `the_geom` | `gml:PointPropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `adu_desc` | `xsd:string` |
| `poblado_p_2024` | `nacional_2024:poblado_p_2024Type` |

### `nacional_2024:puente_l_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `nam` | `xsd:string` |
| `na2` | `xsd:string` |
| `acc_desc` | `xsd:string` |
| `bsc_desc` | `xsd:string` |
| `ltn` | `xsd:int` |
| `typ_desc` | `xsd:string` |
| `tuc_desc` | `xsd:string` |
| `txt` | `xsd:string` |
| `the_geom` | `gml:CurvePropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `puente_l_2024` | `nacional_2024:puente_l_2024Type` |

### `nacional_2024:puerto_p_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `nam` | `xsd:string` |
| `wpi` | `xsd:string` |
| `txt` | `xsd:string` |
| `the_geom` | `gml:PointPropertyType` |
| `puerto_p_2024` | `nacional_2024:puerto_p_2024Type` |

### `nacional_2024:punto_acotado_p_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `acc_desc` | `xsd:string` |
| `ela_desc` | `xsd:string` |
| `zvh` | `xsd:double` |
| `txt` | `xsd:string` |
| `the_geom` | `gml:PointPropertyType` |
| `punto_acotado_p_2024` | `nacional_2024:punto_acotado_p_2024Type` |

### `nacional_2024:punto_desvanecido_p_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `wcc_desc` | `xsd:string` |
| `txt` | `xsd:string` |
| `the_geom` | `gml:PointPropertyType` |
| `punto_desvanecido_p_2024` | `nacional_2024:punto_desvanecido_p_2024Type` |

### `nacional_2024:rio_a_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `nam` | `xsd:string` |
| `na2` | `xsd:string` |
| `acc_desc` | `xsd:string` |
| `hyp_desc` | `xsd:string` |
| `txt` | `xsd:string` |
| `the_geom` | `gml:SurfacePropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `rio_a_2024` | `nacional_2024:rio_a_2024Type` |

### `nacional_2024:rio_l_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `nam` | `xsd:string` |
| `na2` | `xsd:string` |
| `acc_desc` | `xsd:string` |
| `hyp_desc` | `xsd:string` |
| `txt` | `xsd:string` |
| `the_geom` | `gml:CurvePropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `rio_l_2024` | `nacional_2024:rio_l_2024Type` |

### `nacional_2024:roca_p_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `nam` | `xsd:string` |
| `acc_desc` | `xsd:string` |
| `mcc_desc` | `xsd:string` |
| `wle_desc` | `xsd:string` |
| `txt` | `xsd:string` |
| `the_geom` | `gml:PointPropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `roca_p_2024` | `nacional_2024:roca_p_2024Type` |

### `nacional_2024:rodera_l_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `typ_desc` | `xsd:string` |
| `rst_desc` | `xsd:string` |
| `hct_desc` | `xsd:string` |
| `wtc_desc` | `xsd:string` |
| `ltn` | `xsd:int` |
| `tuc_desc` | `xsd:string` |
| `txt` | `xsd:string` |
| `the_geom` | `gml:CurvePropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `rodera_l_2024` | `nacional_2024:rodera_l_2024Type` |

### `nacional_2024:sendero_l_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `coe_desc` | `xsd:string` |
| `wtc_desc` | `xsd:string` |
| `txt` | `xsd:string` |
| `the_geom` | `gml:CurvePropertyType` |
| `sendero_l_2024` | `nacional_2024:sendero_l_2024Type` |

### `nacional_2024:tuberia_l_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `acc_desc` | `xsd:string` |
| `loc_desc` | `xsd:string` |
| `ppo_desc` | `xsd:string` |
| `fco_desc` | `xsd:string` |
| `txt` | `xsd:string` |
| `the_geom` | `gml:CurvePropertyType` |
| `tuberia_l_2024` | `nacional_2024:tuberia_l_2024Type` |

### `nacional_2024:via_ruta_l_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `nam` | `xsd:string` |
| `na2` | `xsd:string` |
| `acc_desc` | `xsd:string` |
| `rst_desc` | `xsd:string` |
| `typ_desc` | `xsd:string` |
| `hct_desc` | `xsd:string` |
| `wtc_desc` | `xsd:string` |
| `loc_desc` | `xsd:string` |
| `ltn` | `xsd:int` |
| `mes_desc` | `xsd:string` |
| `tuc_desc` | `xsd:string` |
| `txt` | `xsd:string` |
| `the_geom` | `gml:CurvePropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `subtipo_desc` | `xsd:string` |
| `via_ruta_l_2024` | `nacional_2024:via_ruta_l_2024Type` |

### `nacional_2024:zona_contigua_a_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `DATEND` | `xsd:string` |
| `DATSTA` | `xsd:string` |
| `NATION` | `xsd:string` |
| `STATUS_desc` | `xsd:string` |
| `INFORM` | `xsd:string` |
| `NINFOM` | `xsd:string` |
| `NTXTDS` | `xsd:string` |
| `SCAMAX` | `xsd:string` |
| `SCAMIN` | `xsd:string` |
| `TXTDSC` | `xsd:string` |
| `RECDAT` | `xsd:string` |
| `RECIND` | `xsd:string` |
| `SORDAT` | `xsd:string` |
| `SORIND` | `xsd:string` |
| `the_geom` | `gml:GeometryPropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `zona_contigua_a_2024` | `nacional_2024:zona_contigua_a_2024Type` |

### `nacional_2024:zona_economica_exclusiva_a_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `NATION` | `xsd:string` |
| `INFORM` | `xsd:string` |
| `NINFOM` | `xsd:string` |
| `NTXTDS` | `xsd:string` |
| `SCAMAX` | `xsd:string` |
| `SCAMIN` | `xsd:string` |
| `TXTDSC` | `xsd:string` |
| `RECDAT` | `xsd:string` |
| `RECIND` | `xsd:string` |
| `SORDAT` | `xsd:string` |
| `SORIND` | `xsd:string` |
| `the_geom` | `gml:SurfacePropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `zona_economica_exclusiva_a_2024` | `nacional_2024:zona_economica_exclusiva_a_2024Type` |

### `nacional_2024:zona_edificada_a_2024`

| Campo | Tipo |
|---|---|
| `gid` | `xsd:int` |
| `fcode` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `nam` | `xsd:string` |
| `na2` | `xsd:string` |
| `acc_desc` | `xsd:string` |
| `nute` | `xsd:string` |
| `txt` | `xsd:string` |
| `the_geom` | `gml:SurfacePropertyType` |
| `simb_prioridad` | `xsd:int` |
| `simb_escala_min` | `xsd:int` |
| `simb_escala_max` | `xsd:int` |
| `adu_desc` | `xsd:string` |
| `zona_edificada_a_2024` | `nacional_2024:zona_edificada_a_2024Type` |
