# Instituto Nicaragüense de Estudios Territoriales — INETER — atributos

Geoportal: [[Geosserviços/Nicarágua INETER IDE/Instituto Nicaragüense de Estudios Territoriales — INETER|Instituto Nicaragüense de Estudios Territoriales — INETER]]


### `cite:pozos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `tipo` | `xsd:string` |
| `localizacion` | `xsd:string` |
| `propietario` | `xsd:string` |
| `codigopozo` | `xsd:string` |
| `acuifero` | `xsd:string` |
| `elevacion` | `xsd:int` |
| `profundidad` | `xsd:decimal` |
| `nea_actual` | `xsd:decimal` |
| `nea_pasado` | `xsd:decimal` |
| `nda_actual` | `xsd:decimal` |
| `nda_pasado` | `xsd:decimal` |
| `fecha_ultima` | `xsd:dateTime` |
| `pozos` | `cite:pozosType` |

### `sf:archsites`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:PointPropertyType` |
| `cat` | `xsd:long` |
| `str1` | `xsd:string` |
| `archsites` | `sf:archsitesType` |

### `sf:bugsites`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:PointPropertyType` |
| `cat` | `xsd:long` |
| `str1` | `xsd:string` |
| `bugsites` | `sf:bugsitesType` |

### `sf:restricted`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `cat` | `xsd:long` |
| `restricted` | `sf:restrictedType` |

### `sf:roads`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiCurvePropertyType` |
| `cat` | `xsd:long` |
| `label` | `xsd:string` |
| `roads` | `sf:roadsType` |

### `sf:streams`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiCurvePropertyType` |
| `cat` | `xsd:long` |
| `label` | `xsd:string` |
| `streams` | `sf:streamsType` |

### `tiger:giant_polygon`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `giant_polygon` | `tiger:giant_polygonType` |

### `tiger:poi`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:PointPropertyType` |
| `NAME` | `xsd:string` |
| `THUMBNAIL` | `xsd:string` |
| `MAINPAGE` | `xsd:string` |
| `poi` | `tiger:poiType` |

### `tiger:poly_landmarks`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `LAND` | `xsd:double` |
| `CFCC` | `xsd:string` |
| `LANAME` | `xsd:string` |
| `poly_landmarks` | `tiger:poly_landmarksType` |

### `tiger:tiger_roads`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiCurvePropertyType` |
| `CFCC` | `xsd:string` |
| `NAME` | `xsd:string` |
| `tiger_roads` | `tiger:tiger_roadsType` |

### `topp:states`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `STATE_NAME` | `xsd:string` |
| `STATE_FIPS` | `xsd:string` |
| `SUB_REGION` | `xsd:string` |
| `STATE_ABBR` | `xsd:string` |
| `LAND_KM` | `xsd:double` |
| `WATER_KM` | `xsd:double` |
| `PERSONS` | `xsd:double` |
| `FAMILIES` | `xsd:double` |
| `HOUSHOLD` | `xsd:double` |
| `MALE` | `xsd:double` |
| `FEMALE` | `xsd:double` |
| `WORKERS` | `xsd:double` |
| `DRVALONE` | `xsd:double` |
| `CARPOOL` | `xsd:double` |
| `PUBTRANS` | `xsd:double` |
| `EMPLOYED` | `xsd:double` |
| `UNEMPLOY` | `xsd:double` |
| `SERVICE` | `xsd:double` |
| `MANUAL` | `xsd:double` |
| `P_MALE` | `xsd:double` |
| `P_FEMALE` | `xsd:double` |
| `SAMP_POP` | `xsd:double` |
| `states` | `topp:statesType` |

### `topp:tasmania_cities`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiPointPropertyType` |
| `CITY_NAME` | `xsd:string` |
| `ADMIN_NAME` | `xsd:string` |
| `CNTRY_NAME` | `xsd:string` |
| `STATUS` | `xsd:string` |
| `POP_CLASS` | `xsd:string` |
| `tasmania_cities` | `topp:tasmania_citiesType` |

### `topp:tasmania_roads`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiCurvePropertyType` |
| `TYPE` | `xsd:string` |
| `tasmania_roads` | `topp:tasmania_roadsType` |

### `topp:tasmania_state_boundaries`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `STATE` | `xsd:string` |
| `COUNTRY` | `xsd:string` |
| `CURR_TYPE` | `xsd:string` |
| `CURR_CODE` | `xsd:string` |
| `tasmania_state_boundaries` | `topp:tasmania_state_boundariesType` |

### `topp:tasmania_water_bodies`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `AREA` | `xsd:long` |
| `PERIMETER` | `xsd:long` |
| `WATER_TYPE` | `xsd:string` |
| `CNTRY_NAME` | `xsd:string` |
| `CONTINENT` | `xsd:string` |
| `tasmania_water_bodies` | `topp:tasmania_water_bodiesType` |

### `ws-INETER:a_elevacion_1`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `a_elevacion_1` | `ws-INETER:a_elevacion_1Type` |

### `ws-INETER:a_elevacion_2`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fecha` | `xsd:string` |
| `area_m2` | `xsd:double` |
| `perim_km` | `xsd:double` |
| `altref` | `xsd:double` |
| `altref_50` | `xsd:double` |
| `volume_50_` | `xsd:double` |
| `sarea_50_b` | `xsd:double` |
| `volume_10b` | `xsd:double` |
| `sarea_10b` | `xsd:double` |
| `a_elevacion_2` | `ws-INETER:a_elevacion_2Type` |

### `ws-INETER:a_elevacion_3`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fecha` | `xsd:string` |
| `area_m2` | `xsd:double` |
| `perim_km` | `xsd:double` |
| `altref` | `xsd:double` |
| `altref_50` | `xsd:double` |
| `volume_50_` | `xsd:double` |
| `sarea_50_b` | `xsd:double` |
| `volume_10b` | `xsd:double` |
| `sarea_10b` | `xsd:double` |
| `layer` | `xsd:string` |
| `path` | `xsd:string` |
| `a_elevacion_3` | `ws-INETER:a_elevacion_3Type` |

### `ws-INETER:a_estructura`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `clasificac` | `xsd:string` |
| `nombres` | `xsd:string` |
| `área` | `xsd:double` |
| `a_estructura` | `ws-INETER:a_estructuraType` |

### `ws-INETER:a_geologia`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `entity` | `xsd:string` |
| `color` | `xsd:long` |
| `leyenda` | `xsd:string` |
| `depósitos` | `xsd:string` |
| `litología` | `xsd:string` |
| `granulomet` | `xsd:string` |
| `secuencia` | `xsd:string` |
| `edad` | `xsd:string` |
| `a_geologia` | `ws-INETER:a_geologiaType` |

### `ws-INETER:america`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fid_americ` | `xsd:long` |
| `objectid` | `xsd:long` |
| `pais` | `xsd:string` |
| `layer` | `xsd:string` |
| `path` | `xsd:string` |
| `shape_area` | `xsd:double` |
| `america` | `ws-INETER:americaType` |

### `ws-INETER:area_estudio`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `area_estudio` | `ws-INETER:area_estudioType` |

### `ws-INETER:baseineter`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `osm_id` | `xsd:string` |
| `osm_way_id` | `xsd:string` |
| `type` | `xsd:string` |
| `aeroway` | `xsd:string` |
| `amenity` | `xsd:string` |
| `admin_leve` | `xsd:string` |
| `barrier` | `xsd:string` |
| `boundary` | `xsd:string` |
| `building` | `xsd:string` |
| `craft` | `xsd:string` |
| `geological` | `xsd:string` |
| `historic` | `xsd:string` |
| `land_area` | `xsd:string` |
| `landuse` | `xsd:string` |
| `leisure` | `xsd:string` |
| `man_made` | `xsd:string` |
| `military` | `xsd:string` |
| `natural` | `xsd:string` |
| `office` | `xsd:string` |
| `place` | `xsd:string` |
| `shop` | `xsd:string` |
| `sport` | `xsd:string` |
| `tourism` | `xsd:string` |
| `other_tags` | `xsd:string` |
| `baseineter` | `ws-INETER:baseineterType` |

### `ws-INETER:Buffer_Camaras`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `codigo` | `xsd:string` |
| `lote` | `xsd:string` |
| `ubicacion` | `xsd:string` |
| `tipo` | `xsd:string` |
| `estado` | `xsd:string` |
| `latitud` | `xsd:decimal` |
| `longitud` | `xsd:decimal` |
| `angulovisu` | `xsd:decimal` |
| `url` | `xsd:string` |
| `direccion` | `xsd:int` |
| `tamannobf` | `xsd:decimal` |
| `tmbf` | `xsd:decimal` |
| `anchobf` | `xsd:decimal` |
| `monitorid` | `xsd:int` |
| `Buffer_Camaras` | `ws-INETER:Buffer_CamarasType` |

### `ws-INETER:Camaras_Ineter`

| Campo | Tipo |
|---|---|
| `codigo` | `xsd:string` |
| `lote` | `xsd:string` |
| `ubicacion` | `xsd:string` |
| `tipo` | `xsd:string` |
| `estado` | `xsd:string` |
| `latitud` | `xsd:decimal` |
| `longitud` | `xsd:decimal` |
| `angulovisu` | `xsd:long` |
| `url` | `xsd:string` |
| `geom` | `gml:PointPropertyType` |
| `direccion` | `xsd:int` |
| `tamannobf` | `xsd:decimal` |
| `tmbf` | `xsd:decimal` |
| `anchobf` | `xsd:float` |
| `monitorid` | `xsd:int` |
| `Camaras_Ineter` | `ws-INETER:Camaras_IneterType` |

### `ws-INETER:Delegaciones_Catastrales`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `delegacion` | `xsd:string` |
| `direccion` | `xsd:string` |
| `telefono` | `xsd:string` |
| `delegado` | `xsd:string` |
| `latitud` | `xsd:decimal` |
| `longitud` | `xsd:decimal` |
| `url` | `xsd:string` |
| `Delegaciones_Catastrales` | `ws-INETER:Delegaciones_CatastralesType` |

### `ws-INETER:deslizamientos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `N°` | `xsd:int` |
| `Coordenada X` | `xsd:double` |
| `Coordenada Y` | `xsd:double` |
| `Etiqueta` | `xsd:string` |
| `deslizamientos` | `ws-INETER:deslizamientosType` |

### `ws-INETER:Estaciones_Ineter`

| Campo | Tipo |
|---|---|
| `nombreestacion` | `xsd:string` |
| `geom` | `gml:GeometryPropertyType` |
| `codigo` | `xsd:string` |
| `latitud` | `xsd:double` |
| `longitud` | `xsd:double` |
| `tipoestacion` | `xsd:string` |
| `Estaciones_Ineter` | `ws-INETER:Estaciones_IneterType` |

### `ws-INETER:estudios_z16`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `nompdf` | `xsd:string` |
| `nomarchivo` | `xsd:string` |
| `nomestudio` | `xsd:string` |
| `anio` | `xsd:long` |
| `codigo` | `xsd:string` |
| `consultor` | `xsd:string` |
| `zonificaci` | `xsd:string` |
| `coorx` | `xsd:decimal` |
| `coory` | `xsd:decimal` |
| `longitud` | `xsd:decimal` |
| `latitud` | `xsd:decimal` |
| `reslitolog` | `xsd:string` |
| `esphrt` | `xsd:string` |
| `profhrt` | `xsd:string` |
| `esphtcp` | `xsd:string` |
| `profhtcp` | `xsd:string` |
| `descfallas` | `xsd:string` |
| `municipio` | `xsd:string` |
| `depart` | `xsd:string` |
| `fuentecoor` | `xsd:string` |
| `observacio` | `xsd:string` |
| `estudios_z16` | `ws-INETER:estudios_z16Type` |

### `ws-INETER:estudiosgeologicos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `id` | `xsd:long` |
| `nompdf` | `xsd:string` |
| `nomarchivo` | `xsd:string` |
| `nomestudio` | `xsd:string` |
| `anio` | `xsd:long` |
| `codigo` | `xsd:string` |
| `consultor` | `xsd:string` |
| `zonificaci` | `xsd:string` |
| `coorx` | `xsd:decimal` |
| `coory` | `xsd:decimal` |
| `longitud` | `xsd:decimal` |
| `latitud` | `xsd:decimal` |
| `reslitolog` | `xsd:string` |
| `esphrt` | `xsd:string` |
| `profhrt` | `xsd:string` |
| `esphtcp` | `xsd:string` |
| `profhtcp` | `xsd:string` |
| `descfallas` | `xsd:string` |
| `municipio` | `xsd:string` |
| `depart` | `xsd:string` |
| `fuentecoor` | `xsd:string` |
| `observacio` | `xsd:string` |
| `x_corr` | `xsd:double` |
| `y_corr` | `xsd:double` |
| `zona_corr` | `xsd:int` |
| `ruta` | `xsd:string` |
| `estudiosgeologicos` | `ws-INETER:estudiosgeologicosType` |

### `ws-INETER:l_estructura_1`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `id` | `xsd:int` |
| `tipo_estru` | `xsd:string` |
| `l_estructura_1` | `ws-INETER:l_estructura_1Type` |

### `ws-INETER:l_estructura_2`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `id` | `xsd:int` |
| `tipo_de_es` | `xsd:string` |
| `l_estructura_2` | `ws-INETER:l_estructura_2Type` |

### `ws-INETER:Linea_Capabase_ineter`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fid` | `xsd:long` |
| `Linea_Capabase_ineter` | `ws-INETER:Linea_Capabase_ineterType` |

### `ws-INETER:mapabase_hid`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiCurvePropertyType` |
| `entity` | `xsd:string` |
| `handle` | `xsd:string` |
| `layer` | `xsd:string` |
| `lyrfrzn` | `xsd:int` |
| `lyrlock` | `xsd:int` |
| `lyron` | `xsd:int` |
| `lyrvpfrzn` | `xsd:int` |
| `lyrhandle` | `xsd:string` |
| `color` | `xsd:int` |
| `entcolor` | `xsd:int` |
| `lyrcolor` | `xsd:int` |
| `blkcolor` | `xsd:int` |
| `linetype` | `xsd:string` |
| `entlinetyp` | `xsd:string` |
| `lyrlntype` | `xsd:string` |
| `blklinetyp` | `xsd:string` |
| `elevation` | `xsd:double` |
| `thickness` | `xsd:double` |
| `linewt` | `xsd:int` |
| `entlinewt` | `xsd:int` |
| `lyrlinewt` | `xsd:int` |
| `blklinewt` | `xsd:int` |
| `refname` | `xsd:string` |
| `ltscale` | `xsd:double` |
| `extx` | `xsd:double` |
| `exty` | `xsd:double` |
| `extz` | `xsd:double` |
| `docname` | `xsd:string` |
| `docpath` | `xsd:string` |
| `doctype` | `xsd:string` |
| `docver` | `xsd:string` |
| `mapabase_hid` | `ws-INETER:mapabase_hidType` |

### `ws-INETER:muestras`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `no.` | `xsd:long` |
| `coordenada` | `xsd:decimal` |
| `coordena_1` | `xsd:decimal` |
| `etiqueta` | `xsd:string` |
| `apodo` | `xsd:string` |
| `muestras` | `ws-INETER:muestrasType` |

### `ws-INETER:p_estructura`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `id` | `xsd:int` |
| `tipo` | `xsd:string` |
| `p_estructura` | `ws-INETER:p_estructuraType` |

### `ws-INETER:poblados`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `nombre` | `xsd:string` |
| `x_coord` | `xsd:double` |
| `y_coord` | `xsd:double` |
| `tipo` | `xsd:int` |
| `descrip` | `xsd:string` |
| `depto` | `xsd:string` |
| `municipio` | `xsd:string` |
| `crs` | `xsd:string` |
| `amenazano` | `xsd:long` |
| `amenazase` | `xsd:long` |
| `poblados` | `ws-INETER:pobladosType` |

### `ws-INETER:Red_Vial`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `Clasificacion` | `xsd:string` |
| `tipo_de_superficie` | `xsd:string` |
| `Longitud_km` | `xsd:double` |
| `Amcho_de_Rodamiento` | `xsd:double` |
| `municipio` | `xsd:string` |
| `origen` | `xsd:string` |
| `destino_` | `xsd:string` |
| `Red_Vial` | `ws-INETER:Red_VialType` |

### `ws-INETER:Red_Vialvista`

| Campo | Tipo |
|---|---|
| `Id` | `xsd:int` |
| `geom` | `gml:MultiCurvePropertyType` |
| `Clasificacion` | `xsd:string` |
| `tipo_de_superficie` | `xsd:string` |
| `Longitud_km` | `xsd:double` |
| `Amcho_de_Rodamiento` | `xsd:double` |
| `municipio` | `xsd:string` |
| `origen` | `xsd:string` |
| `destino_` | `xsd:string` |
| `Red_Vialvista` | `ws-INETER:Red_VialvistaType` |

### `ws-INETER:simbologia`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `id` | `xsd:int` |
| `simbologí` | `xsd:string` |
| `valor` | `xsd:string` |
| `value` | `xsd:string` |
| `simbologia` | `ws-INETER:simbologiaType` |

### `wsINETER-BNC:A_Aerodromo`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `caa` | `xsd:int` |
| `cod` | `xsd:int` |
| `fpt` | `xsd:int` |
| `fun` | `xsd:int` |
| `iko` | `xsd:string` |
| `nam` | `xsd:string` |
| `txt` | `xsd:string` |
| `zva` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Aerodromo` | `wsINETER-BNC:A_AerodromoType` |

### `wsINETER-BNC:A_Anteplaya`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `smc` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Anteplaya` | `wsINETER-BNC:A_AnteplayaType` |

### `wsINETER-BNC:A_Arboles_Bosque`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `dmb` | `xsd:double` |
| `dmt` | `xsd:double` |
| `iss` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `pfh` | `xsd:double` |
| `tre` | `xsd:int` |
| `txt` | `xsd:string` |
| `vsp` | `xsd:int` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `cambios` | `xsd:string` |
| `A_Arboles_Bosque` | `wsINETER-BNC:A_Arboles_BosqueType` |

### `wsINETER-BNC:A_Area_Edificada`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `bac` | `xsd:int` |
| `fuc` | `xsd:int` |
| `fun` | `xsd:int` |
| `hgt` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `ord` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Area_Edificada` | `wsINETER-BNC:A_Area_EdificadaType` |

### `wsINETER-BNC:A_Area_Fronteriza`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Area_Fronteriza` | `wsINETER-BNC:A_Area_FronterizaType` |

### `wsINETER-BNC:A_Arrozal`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `ffp` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Arrozal` | `wsINETER-BNC:A_ArrozalType` |

### `wsINETER-BNC:A_Barranco`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Barranco` | `wsINETER-BNC:A_BarrancoType` |

### `wsINETER-BNC:A_Bunker_Almacenaje`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `len` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `ppo` | `xsd:int` |
| `txt` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Bunker_Almacenaje` | `wsINETER-BNC:A_Bunker_AlmacenajeType` |

### `wsINETER-BNC:A_Campamento`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Campamento` | `wsINETER-BNC:A_CampamentoType` |

### `wsINETER-BNC:A_Campo_de_Tiro`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Campo_de_Tiro` | `wsINETER-BNC:A_Campo_de_TiroType` |

### `wsINETER-BNC:A_Canal_Navegable`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fun` | `xsd:int` |
| `hyp` | `xsd:int` |
| `lbv` | `xsd:double` |
| `loc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `nvs` | `xsd:int` |
| `rbv` | `xsd:double` |
| `txt` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Canal_Navegable` | `wsINETER-BNC:A_Canal_NavegableType` |

### `wsINETER-BNC:A_Cancha`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `cct` | `xsd:int` |
| `fun` | `xsd:int` |
| `hgt` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `ssr` | `xsd:int` |
| `txt` | `xsd:string` |
| `voi` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Cancha` | `wsINETER-BNC:A_CanchaType` |

### `wsINETER-BNC:A_Cantera`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fun` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `ppo` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Cantera` | `wsINETER-BNC:A_CanteraType` |

### `wsINETER-BNC:A_Cementerio`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `rel` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Cementerio` | `wsINETER-BNC:A_CementerioType` |

### `wsINETER-BNC:A_Central_Electrica`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `uid` | `xsd:string` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fun` | `xsd:int` |
| `hgt` | `xsd:double` |
| `len` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `pfh` | `xsd:double` |
| `ppc` | `xsd:int` |
| `smc` | `xsd:int` |
| `txt` | `xsd:string` |
| `voi` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Central_Electrica` | `wsINETER-BNC:A_Central_ElectricaType` |

### `wsINETER-BNC:A_Claros`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Claros` | `wsINETER-BNC:A_ClarosType` |

### `wsINETER-BNC:A_Cortafuegos_Area`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `len` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Cortafuegos_Area` | `wsINETER-BNC:A_Cortafuegos_AreaType` |

### `wsINETER-BNC:A_Costa`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `f_code` | `xsd:string` |
| `acc` | `xsd:int` |
| `na2` | `xsd:string` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `smc` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `A_Costa` | `wsINETER-BNC:A_CostaType` |

### `wsINETER-BNC:A_Crater_pequeno`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `hgt` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `vgt` | `xsd:int` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Crater_pequeno` | `wsINETER-BNC:A_Crater_pequenoType` |

### `wsINETER-BNC:A_Deposito_Minerales`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `hgt` | `xsd:double` |
| `len` | `xsd:double` |
| `ppo` | `xsd:int` |
| `txt` | `xsd:string` |
| `voi` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Deposito_Minerales` | `wsINETER-BNC:A_Deposito_MineralesType` |

### `wsINETER-BNC:A_Edificio`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `afc` | `xsd:int` |
| `aoo` | `xsd:double` |
| `caa` | `xsd:int` |
| `cef` | `xsd:int` |
| `cfc` | `xsd:int` |
| `cit` | `xsd:int` |
| `cus` | `xsd:int` |
| `ddc` | `xsd:int` |
| `ebt` | `xsd:int` |
| `fun` | `xsd:int` |
| `gfc` | `xsd:int` |
| `hgt` | `xsd:double` |
| `hwt` | `xsd:int` |
| `icf` | `xsd:int` |
| `mfc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `paf` | `xsd:int` |
| `ppo` | `xsd:int` |
| `psf` | `xsd:int` |
| `res` | `xsd:int` |
| `rfc` | `xsd:int` |
| `sfy` | `xsd:int` |
| `smc` | `xsd:int` |
| `suc` | `xsd:int` |
| `tfc` | `xsd:int` |
| `txt` | `xsd:string` |
| `uuc` | `xsd:int` |
| `voi` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Edificio` | `wsINETER-BNC:A_EdificioType` |

### `wsINETER-BNC:A_Establo`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fun` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Establo` | `wsINETER-BNC:A_EstabloType` |

### `wsINETER-BNC:A_Estacionamiento_Aerio`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `acs` | `xsd:int` |
| `fun` | `xsd:int` |
| `nam` | `xsd:string` |
| `rst` | `xsd:int` |
| `scb` | `xsd:int` |
| `txt` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Estacionamiento_Aerio` | `wsINETER-BNC:A_Estacionamiento_AerioType` |

### `wsINETER-BNC:A_Estanque`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fun` | `xsd:int` |
| `hyp` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Estanque` | `wsINETER-BNC:A_EstanqueType` |

### `wsINETER-BNC:A_Estanque_sedimentacion`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fun` | `xsd:int` |
| `len` | `xsd:double` |
| `txt` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Estanque_sedimentacion` | `wsINETER-BNC:A_Estanque_sedimentacionType` |

### `wsINETER-BNC:A_Evaporador`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `asc_` | `xsd:int` |
| `A_Evaporador` | `wsINETER-BNC:A_EvaporadorType` |

### `wsINETER-BNC:A_Granja_Marina`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Granja_Marina` | `wsINETER-BNC:A_Granja_MarinaType` |

### `wsINETER-BNC:A_Helipuerto`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `caa` | `xsd:int` |
| `fun` | `xsd:int` |
| `iko` | `xsd:string` |
| `nam` | `xsd:string` |
| `txt` | `xsd:string` |
| `zva` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Helipuerto` | `wsINETER-BNC:A_HelipuertoType` |

### `wsINETER-BNC:A_Isla`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Isla` | `wsINETER-BNC:A_IslaType` |

### `wsINETER-BNC:A_Laguna`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `hyp` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `scc` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Laguna` | `wsINETER-BNC:A_LagunaType` |

### `wsINETER-BNC:A_Lecho_Filtrante`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fun` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Lecho_Filtrante` | `wsINETER-BNC:A_Lecho_FiltranteType` |

### `wsINETER-BNC:A_Marisma`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `tid` | `xsd:int` |
| `txt` | `xsd:string` |
| `wle` | `xsd:int` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Marisma` | `wsINETER-BNC:A_MarismaType` |

### `wsINETER-BNC:A_Matoral_Arbustos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `dmb` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `pfh` | `xsd:double` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Matoral_Arbustos` | `wsINETER-BNC:A_Matoral_ArbustosType` |

### `wsINETER-BNC:A_Mina`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fun` | `xsd:int` |
| `min` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `ppo` | `xsd:int` |
| `sso` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Mina` | `wsINETER-BNC:A_MinaType` |

### `wsINETER-BNC:A_Muelle`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fac` | `xsd:int` |
| `len` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `pwc` | `xsd:int` |
| `txt` | `xsd:string` |
| `wid` | `xsd:double` |
| `wle` | `xsd:int` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Muelle` | `wsINETER-BNC:A_MuelleType` |

### `wsINETER-BNC:A_Pantano`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `dmt` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `pfh` | `xsd:double` |
| `tid` | `xsd:int` |
| `tre` | `xsd:int` |
| `txt` | `xsd:string` |
| `veg` | `xsd:int` |
| `vsp` | `xsd:int` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Pantano` | `wsINETER-BNC:A_PantanoType` |

### `wsINETER-BNC:A_Parque`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Parque` | `wsINETER-BNC:A_ParqueType` |

### `wsINETER-BNC:A_Parque_de_atracciones`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fun` | `xsd:int` |
| `hgt` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Parque_de_atracciones` | `wsINETER-BNC:A_Parque_de_atraccionesType` |

### `wsINETER-BNC:A_Pastizal`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `veg` | `xsd:int` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Pastizal` | `wsINETER-BNC:A_PastizalType` |

### `wsINETER-BNC:A_Pista_aterrizaje`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `acs` | `xsd:int` |
| `fun` | `xsd:int` |
| `len` | `xsd:double` |
| `nam` | `xsd:string` |
| `rst` | `xsd:int` |
| `scb` | `xsd:int` |
| `txp` | `xsd:int` |
| `txt` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Pista_aterrizaje` | `wsINETER-BNC:A_Pista_aterrizajeType` |

### `wsINETER-BNC:A_Pista_de_despegue`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `acs` | `xsd:int` |
| `aoo` | `xsd:double` |
| `caa` | `xsd:int` |
| `fun` | `xsd:int` |
| `len` | `xsd:double` |
| `nam` | `xsd:string` |
| `prm` | `xsd:int` |
| `rst` | `xsd:int` |
| `scb` | `xsd:int` |
| `txt` | `xsd:string` |
| `zva` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Pista_de_despegue` | `wsINETER-BNC:A_Pista_de_despegueType` |

### `wsINETER-BNC:A_Pista_de_frenado`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `acs` | `xsd:int` |
| `fun` | `xsd:int` |
| `len` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `rst` | `xsd:int` |
| `scb` | `xsd:int` |
| `txt` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Pista_de_frenado` | `wsINETER-BNC:A_Pista_de_frenadoType` |

### `wsINETER-BNC:A_Playa`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `smc` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Playa` | `wsINETER-BNC:A_PlayaType` |

### `wsINETER-BNC:A_Poblado`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fuc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `pfh` | `xsd:double` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Poblado` | `wsINETER-BNC:A_PobladoType` |

### `wsINETER-BNC:A_Poste_Perimetro`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `txt` | `xsd:string` |
| `wle` | `xsd:int` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Poste_Perimetro` | `wsINETER-BNC:A_Poste_PerimetroType` |

### `wsINETER-BNC:A_Presa`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `uid` | `xsd:string` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `aoo` | `xsd:double` |
| `dft` | `xsd:int` |
| `fun` | `xsd:int` |
| `hgt` | `xsd:double` |
| `len` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `smc` | `xsd:int` |
| `trs` | `xsd:int` |
| `txt` | `xsd:string` |
| `voi` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Presa` | `wsINETER-BNC:A_PresaType` |

### `wsINETER-BNC:A_Puerto`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fhc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Puerto` | `wsINETER-BNC:A_PuertoType` |

### `wsINETER-BNC:A_Rapidos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `len` | `xsd:double` |
| `lmc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Rapidos` | `wsINETER-BNC:A_RapidosType` |

### `wsINETER-BNC:A_Recinto_ferial`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Recinto_ferial` | `wsINETER-BNC:A_Recinto_ferialType` |

### `wsINETER-BNC:A_Relleno`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fic` | `xsd:int` |
| `len` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `pfh` | `xsd:double` |
| `smc` | `xsd:int` |
| `trs` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Relleno` | `wsINETER-BNC:A_RellenoType` |

### `wsINETER-BNC:A_Restos_Arqueologicos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Restos_Arqueologicos` | `wsINETER-BNC:A_Restos_ArqueologicosType` |

### `wsINETER-BNC:A_Rio`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `uid` | `xsd:string` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `cda` | `xsd:int` |
| `hyp` | `xsd:int` |
| `lbv` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `rbv` | `xsd:double` |
| `shl` | `xsd:int` |
| `shr` | `xsd:int` |
| `tid` | `xsd:int` |
| `txt` | `xsd:string` |
| `wcc` | `xsd:int` |
| `wid` | `xsd:double` |
| `wst` | `xsd:int` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `cambios` | `xsd:string` |
| `A_Rio` | `wsINETER-BNC:A_RioType` |

### `wsINETER-BNC:A_Rio_MapaBase`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `uid` | `xsd:string` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `cda` | `xsd:int` |
| `hyp` | `xsd:int` |
| `lbv` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `rbv` | `xsd:double` |
| `shl` | `xsd:int` |
| `shr` | `xsd:int` |
| `tid` | `xsd:int` |
| `txt` | `xsd:string` |
| `wcc` | `xsd:int` |
| `wid` | `xsd:double` |
| `wst` | `xsd:int` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `cambios` | `xsd:string` |
| `A_Rio_MapaBase` | `wsINETER-BNC:A_Rio_MapaBaseType` |

### `wsINETER-BNC:A_Rio_vbase`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `uid` | `xsd:string` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `cda` | `xsd:int` |
| `hyp` | `xsd:int` |
| `lbv` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `rbv` | `xsd:double` |
| `shl` | `xsd:int` |
| `shr` | `xsd:int` |
| `tid` | `xsd:int` |
| `txt` | `xsd:string` |
| `wcc` | `xsd:int` |
| `wid` | `xsd:double` |
| `wst` | `xsd:int` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `cambios` | `xsd:string` |
| `A_Rio_vbase` | `wsINETER-BNC:A_Rio_vbaseType` |

### `wsINETER-BNC:A_Ruinas`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `hgt` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Ruinas` | `wsINETER-BNC:A_RuinasType` |

### `wsINETER-BNC:A_Silo`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `awp` | `xsd:int` |
| `hgt` | `xsd:double` |
| `len` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `pfh` | `xsd:double` |
| `smc` | `xsd:int` |
| `txt` | `xsd:string` |
| `voi` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Silo` | `wsINETER-BNC:A_SiloType` |

### `wsINETER-BNC:A_Subestacion`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fun` | `xsd:int` |
| `hgt` | `xsd:double` |
| `len` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `smc` | `xsd:int` |
| `txt` | `xsd:string` |
| `voi` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Subestacion` | `wsINETER-BNC:A_SubestacionType` |

### `wsINETER-BNC:A_Tanque_Gas`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `awp` | `xsd:int` |
| `fun` | `xsd:int` |
| `hgt` | `xsd:double` |
| `len` | `xsd:double` |
| `loc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `ppo` | `xsd:int` |
| `smc` | `xsd:int` |
| `ssc` | `xsd:int` |
| `txt` | `xsd:string` |
| `voi` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Tanque_Gas` | `wsINETER-BNC:A_Tanque_GasType` |

### `wsINETER-BNC:A_Terreno_del_mismo_tipo`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `smc` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Terreno_del_mismo_tipo` | `wsINETER-BNC:A_Terreno_del_mismo_tipoType` |

### `wsINETER-BNC:A_Terreno_Pantanoso`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `boc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Terreno_Pantanoso` | `wsINETER-BNC:A_Terreno_PantanosoType` |

### `wsINETER-BNC:A_Tierra_Cultivo`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `csp` | `xsd:int` |
| `dmt` | `xsd:double` |
| `ffp` | `xsd:int` |
| `fmm` | `xsd:int` |
| `irg` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `pfh` | `xsd:double` |
| `ppo` | `xsd:int` |
| `tre` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Tierra_Cultivo` | `wsINETER-BNC:A_Tierra_CultivoType` |

### `wsINETER-BNC:A_Vertedero`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fun` | `xsd:int` |
| `hgt` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `pby` | `xsd:int` |
| `txt` | `xsd:string` |
| `voi` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Vertedero` | `wsINETER-BNC:A_VertederoType` |

### `wsINETER-BNC:A_Zona_Inundable`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `cns` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `asc_` | `xsd:int` |
| `A_Zona_Inundable` | `wsINETER-BNC:A_Zona_InundableType` |

### `wsINETER-BNC:A_Zona_Rocosa`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `hgt` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `rkf` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `A_Zona_Rocosa` | `wsINETER-BNC:A_Zona_RocosaType` |

### `wsINETER-BNC:AreaEdificada_MapaBase`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nam` | `xsd:string` |
| `AreaEdificada_MapaBase` | `wsINETER-BNC:AreaEdificada_MapaBaseType` |

### `wsINETER-BNC:L_Acequia`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `cda` | `xsd:int` |
| `hyp` | `xsd:int` |
| `lbv` | `xsd:double` |
| `rbv` | `xsd:double` |
| `txt` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Acequia` | `wsINETER-BNC:L_AcequiaType` |

### `wsINETER-BNC:L_Acueducto`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fun` | `xsd:int` |
| `loc` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Acueducto` | `wsINETER-BNC:L_AcueductoType` |

### `wsINETER-BNC:L_Arrecife`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `cod` | `xsd:int` |
| `certainty_` | `xsd:string` |
| `mcc` | `xsd:int` |
| `material_c` | `xsd:string` |
| `vrr` | `xsd:int` |
| `vertical_r` | `xsd:string` |
| `descriptio` | `xsd:string` |
| `fid_` | `xsd:int` |
| `L_Arrecife` | `wsINETER-BNC:L_ArrecifeType` |

### `wsINETER-BNC:L_Barranco`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Barranco` | `wsINETER-BNC:L_BarrancoType` |

### `wsINETER-BNC:L_Camino_Carretero`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `wd1` | `xsd:double` |
| `wtc` | `xsd:int` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `cambios` | `xsd:string` |
| `L_Camino_Carretero` | `wsINETER-BNC:L_Camino_CarreteroType` |

### `wsINETER-BNC:L_Canal_navegable`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fun` | `xsd:int` |
| `hyp` | `xsd:int` |
| `lbv` | `xsd:double` |
| `loc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `nvs` | `xsd:int` |
| `rbv` | `xsd:double` |
| `txt` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Canal_navegable` | `wsINETER-BNC:L_Canal_navegableType` |

### `wsINETER-BNC:L_Carretera_Solida`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fun` | `xsd:int` |
| `hct` | `xsd:int` |
| `loc` | `xsd:int` |
| `ltn` | `xsd:int` |
| `mes` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `rst` | `xsd:int` |
| `txt` | `xsd:string` |
| `wd1` | `xsd:double` |
| `wtc` | `xsd:int` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Carretera_Solida` | `wsINETER-BNC:L_Carretera_SolidaType` |

### `wsINETER-BNC:L_Cascada_Largo`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Cascada_Largo` | `wsINETER-BNC:L_Cascada_LargoType` |

### `wsINETER-BNC:L_Circuito_de_carreras`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Circuito_de_carreras` | `wsINETER-BNC:L_Circuito_de_carrerasType` |

### `wsINETER-BNC:L_Corte_delinear_sobre_carretera`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `pfh` | `xsd:double` |
| `smc` | `xsd:int` |
| `trs` | `xsd:int` |
| `txt` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Corte_delinear_sobre_carretera` | `wsINETER-BNC:L_Corte_delinear_sobre_carreteraType` |

### `wsINETER-BNC:L_Dique_portuario`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fun` | `xsd:int` |
| `txt` | `xsd:string` |
| `wid` | `xsd:double` |
| `wle` | `xsd:int` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Dique_portuario` | `wsINETER-BNC:L_Dique_portuarioType` |

### `wsINETER-BNC:L_Falla`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Falla` | `wsINETER-BNC:L_FallaType` |

### `wsINETER-BNC:L_Limites`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `entity` | `xsd:string` |
| `handle` | `xsd:string` |
| `layer` | `xsd:string` |
| `lyrfrzn` | `xsd:int` |
| `lyrlock` | `xsd:int` |
| `lyron` | `xsd:int` |
| `lyrvpfrzn` | `xsd:int` |
| `lyrhandle` | `xsd:string` |
| `color` | `xsd:int` |
| `entcolor` | `xsd:int` |
| `lyrcolor` | `xsd:int` |
| `blkcolor` | `xsd:int` |
| `linetype` | `xsd:string` |
| `entlinetyp` | `xsd:string` |
| `lyrlntype` | `xsd:string` |
| `blklinetyp` | `xsd:string` |
| `elevation` | `xsd:double` |
| `thickness` | `xsd:double` |
| `linewt` | `xsd:int` |
| `entlinewt` | `xsd:int` |
| `lyrlinewt` | `xsd:int` |
| `blklinewt` | `xsd:int` |
| `refname` | `xsd:string` |
| `ltscale` | `xsd:double` |
| `extx` | `xsd:double` |
| `exty` | `xsd:double` |
| `extz` | `xsd:double` |
| `docname` | `xsd:string` |
| `docpath` | `xsd:string` |
| `doctype` | `xsd:string` |
| `docver` | `xsd:string` |
| `L_Limites` | `wsINETER-BNC:L_LimitesType` |

### `wsINETER-BNC:L_Line_de_Costa`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `slt` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Line_de_Costa` | `wsINETER-BNC:L_Line_de_CostaType` |

### `wsINETER-BNC:L_Linea_Claros`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `smc` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Linea_Claros` | `wsINETER-BNC:L_Linea_ClarosType` |

### `wsINETER-BNC:L_Linea_de_Arboles`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `dmb` | `xsd:double` |
| `dmt` | `xsd:double` |
| `iss` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `pfh` | `xsd:double` |
| `tre` | `xsd:int` |
| `txt` | `xsd:string` |
| `vsp` | `xsd:int` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `cambio` | `xsd:string` |
| `L_Linea_de_Arboles` | `wsINETER-BNC:L_Linea_de_ArbolesType` |

### `wsINETER-BNC:L_Linea_de_Costa`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `na2` | `xsd:string` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Linea_de_Costa` | `wsINETER-BNC:L_Linea_de_CostaType` |

### `wsINETER-BNC:L_Linea_Electrica`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fun` | `xsd:int` |
| `hgt` | `xsd:double` |
| `kva` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `npl` | `xsd:int` |
| `owo` | `xsd:int` |
| `pfh` | `xsd:double` |
| `tst` | `xsd:int` |
| `txt` | `xsd:string` |
| `voi` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Linea_Electrica` | `wsINETER-BNC:L_Linea_ElectricaType` |

### `wsINETER-BNC:L_Muelles`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fac` | `xsd:int` |
| `len` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `pwc` | `xsd:int` |
| `txt` | `xsd:string` |
| `wid` | `xsd:double` |
| `wle` | `xsd:int` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Muelles` | `wsINETER-BNC:L_MuellesType` |

### `wsINETER-BNC:L_Muro`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fun` | `xsd:int` |
| `hgt` | `xsd:double` |
| `lnu` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `pfh` | `xsd:double` |
| `scb` | `xsd:int` |
| `txt` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Muro` | `wsINETER-BNC:L_MuroType` |

### `wsINETER-BNC:L_Muro_de_encauzamiento`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `len` | `xsd:double` |
| `txt` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Muro_de_encauzamiento` | `wsINETER-BNC:L_Muro_de_encauzamientoType` |

### `wsINETER-BNC:L_Muro_Rompeolas`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `len` | `xsd:double` |
| `txt` | `xsd:string` |
| `wid` | `xsd:double` |
| `wle` | `xsd:int` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Muro_Rompeolas` | `wsINETER-BNC:L_Muro_RompeolasType` |

### `wsINETER-BNC:L_Muro_Tapia`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `moh` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `pfh` | `xsd:double` |
| `smc` | `xsd:int` |
| `txt` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Muro_Tapia` | `wsINETER-BNC:L_Muro_TapiaType` |

### `wsINETER-BNC:L_parte_superior_de_corte`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `pfh` | `xsd:double` |
| `smc` | `xsd:int` |
| `trs` | `xsd:int` |
| `txt` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_parte_superior_de_corte` | `wsINETER-BNC:L_parte_superior_de_corteType` |

### `wsINETER-BNC:L_Precipicio`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `pfh` | `xsd:double` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Precipicio` | `wsINETER-BNC:L_PrecipicioType` |

### `wsINETER-BNC:L_Presa`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `aoo` | `xsd:double` |
| `dft` | `xsd:int` |
| `fun` | `xsd:int` |
| `hgt` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `smc` | `xsd:int` |
| `trs` | `xsd:int` |
| `txt` | `xsd:string` |
| `voi` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Presa` | `wsINETER-BNC:L_PresaType` |

### `wsINETER-BNC:L_Puente`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `bot` | `xsd:int` |
| `bsc` | `xsd:int` |
| `fun` | `xsd:int` |
| `hca` | `xsd:double` |
| `lc1` | `xsd:int` |
| `lc2` | `xsd:int` |
| `lc3` | `xsd:int` |
| `lc4` | `xsd:int` |
| `mvc` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `nos` | `xsd:int` |
| `ohb` | `xsd:double` |
| `smc` | `xsd:int` |
| `trs` | `xsd:int` |
| `txt` | `xsd:string` |
| `voi` | `xsd:string` |
| `wd1` | `xsd:double` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Puente` | `wsINETER-BNC:L_PuenteType` |

### `wsINETER-BNC:L_Rapidos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `len` | `xsd:double` |
| `lmc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Rapidos` | `wsINETER-BNC:L_RapidosType` |

### `wsINETER-BNC:L_Relleno`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fic` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `pfh` | `xsd:double` |
| `smc` | `xsd:int` |
| `trs` | `xsd:int` |
| `txt` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Relleno` | `wsINETER-BNC:L_RellenoType` |

### `wsINETER-BNC:L_Rio`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `cda` | `xsd:int` |
| `hyp` | `xsd:int` |
| `lbv` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `rbv` | `xsd:double` |
| `shl` | `xsd:int` |
| `shr` | `xsd:int` |
| `tid` | `xsd:int` |
| `txt` | `xsd:string` |
| `wcc` | `xsd:int` |
| `wid` | `xsd:double` |
| `wst` | `xsd:int` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `cambio` | `xsd:string` |
| `L_Rio` | `wsINETER-BNC:L_RioType` |

### `wsINETER-BNC:L_Sendero`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `wtc` | `xsd:int` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Sendero` | `wsINETER-BNC:L_SenderoType` |

### `wsINETER-BNC:L_Tuberia_de_Presion`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `loc` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Tuberia_de_Presion` | `wsINETER-BNC:L_Tuberia_de_PresionType` |

### `wsINETER-BNC:L_Tuberia_Pipeline`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fun` | `xsd:int` |
| `hgt` | `xsd:double` |
| `loc` | `xsd:int` |
| `owo` | `xsd:int` |
| `ppo` | `xsd:int` |
| `rta` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Tuberia_Pipeline` | `wsINETER-BNC:L_Tuberia_PipelineType` |

### `wsINETER-BNC:L_Tunel`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fun` | `xsd:int` |
| `len` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `trs` | `xsd:int` |
| `txt` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Tunel` | `wsINETER-BNC:L_TunelType` |

### `wsINETER-BNC:L_Vado`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `rst` | `xsd:int` |
| `trs` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Vado` | `wsINETER-BNC:L_VadoType` |

### `wsINETER-BNC:L_Valla`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fti` | `xsd:int` |
| `moh` | `xsd:double` |
| `pfh` | `xsd:double` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Valla` | `wsINETER-BNC:L_VallaType` |

### `wsINETER-BNC:L_Via_de_ferrocarril`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fun` | `xsd:int` |
| `gaw` | `xsd:double` |
| `loc` | `xsd:int` |
| `ltn` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `rgc` | `xsd:int` |
| `rir` | `xsd:int` |
| `rra` | `xsd:int` |
| `rrc` | `xsd:int` |
| `rta` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `L_Via_de_ferrocarril` | `wsINETER-BNC:L_Via_de_ferrocarrilType` |

### `wsINETER-BNC:Laguna_MapaBase`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nam` | `xsd:string` |
| `Laguna_MapaBase` | `wsINETER-BNC:Laguna_MapaBaseType` |

### `wsINETER-BNC:LBH140`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `uid` | `xsd:string` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `cda` | `xsd:int` |
| `hyp` | `xsd:int` |
| `lbv` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `rbv` | `xsd:double` |
| `shl` | `xsd:int` |
| `shr` | `xsd:int` |
| `tid` | `xsd:int` |
| `txt` | `xsd:string` |
| `wcc` | `xsd:int` |
| `wid` | `xsd:double` |
| `wst` | `xsd:int` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `cambio` | `xsd:string` |
| `LBH140` | `wsINETER-BNC:LBH140Type` |

### `wsINETER-BNC:LCA010_Curva_Indice`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `zv2` | `xsd:int` |
| `LCA010_Curva_Indice` | `wsINETER-BNC:LCA010_Curva_IndiceType` |

### `wsINETER-BNC:LCA010_Curva_Intermedia`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `zv2` | `xsd:int` |
| `LCA010_Curva_Intermedia` | `wsINETER-BNC:LCA010_Curva_IntermediaType` |

### `wsINETER-BNC:LCA010_Curva_Suplemetaria`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `zv2` | `xsd:int` |
| `LCA010_Curva_Suplemetaria` | `wsINETER-BNC:LCA010_Curva_SuplemetariaType` |

### `wsINETER-BNC:Limites_Departamentales_Cobertura`

| Campo | Tipo |
|---|---|
| `nombre` | `xsd:string` |
| `codigos` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `id` | `xsd:int` |
| `code_dpto` | `xsd:string` |
| `code` | `xsd:string` |
| `dpto` | `xsd:string` |
| `clase` | `xsd:string` |
| `cab_dpto` | `xsd:string` |
| `label` | `xsd:string` |
| `label_wms` | `xsd:string` |
| `m_juridico` | `xsd:string` |
| `area_km2` | `xsd:double` |
| `pob_2005` | `xsd:int` |
| `pob_2016` | `xsd:int` |
| `Limites_Departamentales_Cobertura` | `wsINETER-BNC:Limites_Departamentales_CoberturaType` |

### `wsINETER-BNC:Limites_Departamentales_Mapa_Base`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `id` | `xsd:int` |
| `code_dpto` | `xsd:string` |
| `code` | `xsd:string` |
| `dpto` | `xsd:string` |
| `clase` | `xsd:string` |
| `cab_dpto` | `xsd:string` |
| `nombre` | `xsd:string` |
| `label` | `xsd:string` |
| `label_wms` | `xsd:string` |
| `m_juridico` | `xsd:string` |
| `area_km2` | `xsd:double` |
| `pob_2005` | `xsd:int` |
| `pob_2016` | `xsd:int` |
| `Limites_Departamentales_Mapa_Base` | `wsINETER-BNC:Limites_Departamentales_Mapa_BaseType` |

### `wsINETER-BNC:MBS_lagulag`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nam` | `xsd:string` |
| `MBS_lagulag` | `wsINETER-BNC:MBS_lagulagType` |

### `wsINETER-BNC:MBS_limitnica`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `id` | `xsd:int` |
| `code_dpto` | `xsd:string` |
| `code` | `xsd:string` |
| `dpto` | `xsd:string` |
| `clase` | `xsd:string` |
| `cab_dpto` | `xsd:string` |
| `nombre` | `xsd:string` |
| `label` | `xsd:string` |
| `label_wms` | `xsd:string` |
| `m_juridico` | `xsd:string` |
| `area_km2` | `xsd:double` |
| `pob_2005` | `xsd:int` |
| `pob_2016` | `xsd:int` |
| `MBS_limitnica` | `wsINETER-BNC:MBS_limitnicaType` |

### `wsINETER-BNC:NIC_Mapabase`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `entity` | `xsd:string` |
| `handle` | `xsd:string` |
| `layer` | `xsd:string` |
| `lyrfrzn` | `xsd:int` |
| `lyrlock` | `xsd:int` |
| `lyron` | `xsd:int` |
| `lyrvpfrzn` | `xsd:int` |
| `lyrhandle` | `xsd:string` |
| `color` | `xsd:int` |
| `entcolor` | `xsd:int` |
| `lyrcolor` | `xsd:int` |
| `blkcolor` | `xsd:int` |
| `linetype` | `xsd:string` |
| `entlinetyp` | `xsd:string` |
| `lyrlntype` | `xsd:string` |
| `blklinetyp` | `xsd:string` |
| `elevation` | `xsd:double` |
| `thickness` | `xsd:double` |
| `linewt` | `xsd:int` |
| `entlinewt` | `xsd:int` |
| `lyrlinewt` | `xsd:int` |
| `blklinewt` | `xsd:int` |
| `refname` | `xsd:string` |
| `ltscale` | `xsd:double` |
| `extx` | `xsd:double` |
| `exty` | `xsd:double` |
| `extz` | `xsd:double` |
| `docname` | `xsd:string` |
| `docpath` | `xsd:string` |
| `doctype` | `xsd:string` |
| `docver` | `xsd:string` |
| `NIC_Mapabase` | `wsINETER-BNC:NIC_MapabaseType` |

### `wsINETER-BNC:P_Alcantarilla`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `txt` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Alcantarilla` | `wsINETER-BNC:P_AlcantarillaType` |

### `wsINETER-BNC:P_Antena_Parabolica`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `hgt` | `xsd:double` |
| `len` | `xsd:double` |
| `smc` | `xsd:int` |
| `txt` | `xsd:string` |
| `voi` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Antena_Parabolica` | `wsINETER-BNC:P_Antena_ParabolicaType` |

### `wsINETER-BNC:P_Arboles`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `dmb` | `xsd:double` |
| `dmt` | `xsd:double` |
| `iss` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `pfh` | `xsd:double` |
| `tre` | `xsd:int` |
| `txt` | `xsd:string` |
| `vsp` | `xsd:int` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Arboles` | `wsINETER-BNC:P_ArbolesType` |

### `wsINETER-BNC:P_Canal`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `atc` | `xsd:int` |
| `fun` | `xsd:int` |
| `len` | `xsd:double` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Canal` | `wsINETER-BNC:P_CanalType` |

### `wsINETER-BNC:P_Cantera`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `ara` | `xsd:double` |
| `fun` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `ppo` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Cantera` | `wsINETER-BNC:P_CanteraType` |

### `wsINETER-BNC:P_Cascada`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Cascada` | `wsINETER-BNC:P_CascadaType` |

### `wsINETER-BNC:P_Casco_Urbano`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `bac` | `xsd:int` |
| `fuc` | `xsd:int` |
| `fun` | `xsd:int` |
| `hgt` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `ord` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Casco_Urbano` | `wsINETER-BNC:P_Casco_UrbanoType` |

### `wsINETER-BNC:P_Cementerio`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `rel` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Cementerio` | `wsINETER-BNC:P_CementerioType` |

### `wsINETER-BNC:P_Central_Electrica`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `ara` | `xsd:double` |
| `fun` | `xsd:int` |
| `hgt` | `xsd:double` |
| `len` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `pfh` | `xsd:double` |
| `ppc` | `xsd:int` |
| `smc` | `xsd:int` |
| `txt` | `xsd:string` |
| `voi` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Central_Electrica` | `wsINETER-BNC:P_Central_ElectricaType` |

### `wsINETER-BNC:P_Choza`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `entity` | `xsd:string` |
| `handle` | `xsd:string` |
| `layer` | `xsd:string` |
| `lyrfrzn` | `xsd:int` |
| `lyrlock` | `xsd:int` |
| `lyron` | `xsd:int` |
| `lyrvpfrzn` | `xsd:int` |
| `lyrhandle` | `xsd:string` |
| `color` | `xsd:int` |
| `entcolor` | `xsd:int` |
| `lyrcolor` | `xsd:int` |
| `blkcolor` | `xsd:int` |
| `linetype` | `xsd:string` |
| `entlinetyp` | `xsd:string` |
| `lyrlntype` | `xsd:string` |
| `blklinetyp` | `xsd:string` |
| `elevation` | `xsd:double` |
| `thickness` | `xsd:double` |
| `linewt` | `xsd:int` |
| `entlinewt` | `xsd:int` |
| `lyrlinewt` | `xsd:int` |
| `blklinewt` | `xsd:int` |
| `refname` | `xsd:string` |
| `ltscale` | `xsd:double` |
| `angle` | `xsd:double` |
| `extx` | `xsd:double` |
| `exty` | `xsd:double` |
| `extz` | `xsd:double` |
| `docname` | `xsd:string` |
| `docpath` | `xsd:string` |
| `doctype` | `xsd:string` |
| `docver` | `xsd:string` |
| `scalex` | `xsd:double` |
| `scaley` | `xsd:double` |
| `scalez` | `xsd:double` |
| `P_Choza` | `wsINETER-BNC:P_ChozaType` |

### `wsINETER-BNC:P_Cisterna`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `smc` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Cisterna` | `wsINETER-BNC:P_CisternaType` |

### `wsINETER-BNC:P_Complejo_Deportivo`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `ara` | `xsd:double` |
| `fun` | `xsd:int` |
| `len` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `smc` | `xsd:int` |
| `ssc` | `xsd:int` |
| `txt` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Complejo_Deportivo` | `wsINETER-BNC:P_Complejo_DeportivoType` |

### `wsINETER-BNC:P_Deposito_de_Agua`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `awp` | `xsd:int` |
| `fun` | `xsd:int` |
| `hgt` | `xsd:double` |
| `len` | `xsd:double` |
| `smc` | `xsd:int` |
| `txt` | `xsd:string` |
| `voi` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Deposito_de_Agua` | `wsINETER-BNC:P_Deposito_de_AguaType` |

### `wsINETER-BNC:P_Deposito_de_Minerales`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `hgt` | `xsd:double` |
| `len` | `xsd:double` |
| `ppo` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Deposito_de_Minerales` | `wsINETER-BNC:P_Deposito_de_MineralesType` |

### `wsINETER-BNC:P_Edificio`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `afc` | `xsd:int` |
| `aoo` | `xsd:double` |
| `ara` | `xsd:double` |
| `caa` | `xsd:int` |
| `cef` | `xsd:int` |
| `cfc` | `xsd:int` |
| `cit` | `xsd:int` |
| `cus` | `xsd:int` |
| `ddc` | `xsd:int` |
| `ebt` | `xsd:int` |
| `fun` | `xsd:int` |
| `gfc` | `xsd:int` |
| `hgt` | `xsd:double` |
| `hwt` | `xsd:int` |
| `icf` | `xsd:int` |
| `len` | `xsd:double` |
| `mfc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `paf` | `xsd:int` |
| `ppo` | `xsd:int` |
| `psf` | `xsd:int` |
| `res` | `xsd:int` |
| `rfc` | `xsd:int` |
| `sfy` | `xsd:int` |
| `smc` | `xsd:int` |
| `suc` | `xsd:int` |
| `tfc` | `xsd:int` |
| `txt` | `xsd:string` |
| `uuc` | `xsd:int` |
| `voi` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Edificio` | `wsINETER-BNC:P_EdificioType` |

### `wsINETER-BNC:P_Elevador_de_cereales`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `hgt` | `xsd:double` |
| `len` | `xsd:double` |
| `smc` | `xsd:int` |
| `txt` | `xsd:string` |
| `voi` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Elevador_de_cereales` | `wsINETER-BNC:P_Elevador_de_cerealesType` |

### `wsINETER-BNC:P_Escape_de_humos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `awp` | `xsd:int` |
| `fun` | `xsd:int` |
| `hgt` | `xsd:double` |
| `len` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `smc` | `xsd:int` |
| `txt` | `xsd:string` |
| `voi` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Escape_de_humos` | `wsINETER-BNC:P_Escape_de_humosType` |

### `wsINETER-BNC:P_Estacion_bombeo`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fun` | `xsd:int` |
| `hgt` | `xsd:double` |
| `len` | `xsd:double` |
| `ppo` | `xsd:int` |
| `smc` | `xsd:int` |
| `txt` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Estacion_bombeo` | `wsINETER-BNC:P_Estacion_bombeoType` |

### `wsINETER-BNC:P_Estacion_generica`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fun` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Estacion_generica` | `wsINETER-BNC:P_Estacion_genericaType` |

### `wsINETER-BNC:P_Estadio`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `cct` | `xsd:int` |
| `fun` | `xsd:int` |
| `hgt` | `xsd:double` |
| `len` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `ssr` | `xsd:int` |
| `txt` | `xsd:string` |
| `voi` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Estadio` | `wsINETER-BNC:P_EstadioType` |

### `wsINETER-BNC:P_Faro`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `cos` | `xsd:int` |
| `fun` | `xsd:int` |
| `hgt` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `smc` | `xsd:int` |
| `txt` | `xsd:string` |
| `vdc` | `xsd:int` |
| `voi` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Faro` | `wsINETER-BNC:P_FaroType` |

### `wsINETER-BNC:P_Fortification`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fun` | `xsd:int` |
| `hgt` | `xsd:double` |
| `len` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `smc` | `xsd:int` |
| `txt` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Fortification` | `wsINETER-BNC:P_FortificationType` |

### `wsINETER-BNC:P_Gasometro`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `ara` | `xsd:double` |
| `awp` | `xsd:int` |
| `fun` | `xsd:int` |
| `hgt` | `xsd:double` |
| `len` | `xsd:double` |
| `loc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `ppo` | `xsd:int` |
| `smc` | `xsd:int` |
| `ssc` | `xsd:int` |
| `txt` | `xsd:string` |
| `voi` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Gasometro` | `wsINETER-BNC:P_GasometroType` |

### `wsINETER-BNC:P_Manantial`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `hyp` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `scc` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Manantial` | `wsINETER-BNC:P_ManantialType` |

### `wsINETER-BNC:P_Mina`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `ara` | `xsd:double` |
| `fun` | `xsd:int` |
| `min` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `ppo` | `xsd:int` |
| `sso` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Mina` | `wsINETER-BNC:P_MinaType` |

### `wsINETER-BNC:P_Mojon`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Mojon` | `wsINETER-BNC:P_MojonType` |

### `wsINETER-BNC:P_Molino_de_Viento`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fun` | `xsd:int` |
| `hgt` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `smc` | `xsd:int` |
| `tos` | `xsd:int` |
| `txt` | `xsd:string` |
| `voi` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Molino_de_Viento` | `wsINETER-BNC:P_Molino_de_VientoType` |

### `wsINETER-BNC:P_Monumento`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `hgt` | `xsd:double` |
| `len` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `ssc` | `xsd:int` |
| `txt` | `xsd:string` |
| `voi` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Monumento` | `wsINETER-BNC:P_MonumentoType` |

### `wsINETER-BNC:P_Navegacion_Aerea`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `awp` | `xsd:int` |
| `fun` | `xsd:int` |
| `hgt` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `prm` | `xsd:int` |
| `smc` | `xsd:int` |
| `txt` | `xsd:string` |
| `voi` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Navegacion_Aerea` | `wsINETER-BNC:P_Navegacion_AereaType` |

### `wsINETER-BNC:P_Ojo_de_Agua`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `txt` | `xsd:string` |
| `wst` | `xsd:int` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Ojo_de_Agua` | `wsINETER-BNC:P_Ojo_de_AguaType` |

### `wsINETER-BNC:P_Pista_edificios`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `caa` | `xsd:int` |
| `fun` | `xsd:int` |
| `haf` | `xsd:int` |
| `hgt` | `xsd:double` |
| `len` | `xsd:double` |
| `nam` | `xsd:string` |
| `rst` | `xsd:int` |
| `smc` | `xsd:int` |
| `txt` | `xsd:string` |
| `wid` | `xsd:double` |
| `zva` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Pista_edificios` | `wsINETER-BNC:P_Pista_edificiosType` |

### `wsINETER-BNC:P_Playa`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `smc` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Playa` | `wsINETER-BNC:P_PlayaType` |

### `wsINETER-BNC:P_Poblado`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fuc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `pfh` | `xsd:double` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Poblado` | `wsINETER-BNC:P_PobladoType` |

### `wsINETER-BNC:P_Pozo`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fun` | `xsd:int` |
| `hyp` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `ppo` | `xsd:int` |
| `scc` | `xsd:int` |
| `txt` | `xsd:string` |
| `wft` | `xsd:int` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Pozo` | `wsINETER-BNC:P_PozoType` |

### `wsINETER-BNC:P_Presa`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `aoo` | `xsd:double` |
| `dft` | `xsd:int` |
| `fun` | `xsd:int` |
| `hgt` | `xsd:double` |
| `len` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `smc` | `xsd:int` |
| `trs` | `xsd:int` |
| `txt` | `xsd:string` |
| `voi` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Presa` | `wsINETER-BNC:P_PresaType` |

### `wsINETER-BNC:P_Punto_de_control`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Punto_de_control` | `wsINETER-BNC:P_Punto_de_controlType` |

### `wsINETER-BNC:P_Rapidos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `len` | `xsd:double` |
| `lmc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Rapidos` | `wsINETER-BNC:P_RapidosType` |

### `wsINETER-BNC:P_Restos_Arqueologicos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Restos_Arqueologicos` | `wsINETER-BNC:P_Restos_ArqueologicosType` |

### `wsINETER-BNC:P_Rocas`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `len` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `smc` | `xsd:int` |
| `txt` | `xsd:string` |
| `uhs` | `xsd:int` |
| `wle` | `xsd:int` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Rocas` | `wsINETER-BNC:P_RocasType` |

### `wsINETER-BNC:P_Silo`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `awp` | `xsd:int` |
| `hgt` | `xsd:double` |
| `len` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `pfh` | `xsd:double` |
| `smc` | `xsd:int` |
| `txt` | `xsd:string` |
| `voi` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Silo` | `wsINETER-BNC:P_SiloType` |

### `wsINETER-BNC:P_Soportar_Equipos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `fun` | `xsd:int` |
| `hgt` | `xsd:double` |
| `len` | `xsd:double` |
| `smc` | `xsd:int` |
| `trs` | `xsd:int` |
| `txt` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Soportar_Equipos` | `wsINETER-BNC:P_Soportar_EquiposType` |

### `wsINETER-BNC:P_Subestacion`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `ara` | `xsd:double` |
| `fun` | `xsd:int` |
| `hgt` | `xsd:double` |
| `len` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `smc` | `xsd:int` |
| `txt` | `xsd:string` |
| `voi` | `xsd:string` |
| `wid` | `xsd:double` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Subestacion` | `wsINETER-BNC:P_SubestacionType` |

### `wsINETER-BNC:P_Torre`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `awp` | `xsd:int` |
| `hgt` | `xsd:double` |
| `len` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `smc` | `xsd:int` |
| `ttc` | `xsd:int` |
| `txt` | `xsd:string` |
| `voi` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Torre` | `wsINETER-BNC:P_TorreType` |

### `wsINETER-BNC:P_Torre_control`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `awp` | `xsd:int` |
| `fun` | `xsd:int` |
| `hgt` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `smc` | `xsd:int` |
| `trs` | `xsd:int` |
| `txt` | `xsd:string` |
| `voi` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Torre_control` | `wsINETER-BNC:P_Torre_controlType` |

### `wsINETER-BNC:P_Torre_de_Comunicacion`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `awp` | `xsd:int` |
| `fun` | `xsd:int` |
| `hgt` | `xsd:double` |
| `loc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `nst` | `xsd:int` |
| `smc` | `xsd:int` |
| `tos` | `xsd:int` |
| `txt` | `xsd:string` |
| `voi` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Torre_de_Comunicacion` | `wsINETER-BNC:P_Torre_de_ComunicacionType` |

### `wsINETER-BNC:P_Vado`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `rst` | `xsd:int` |
| `trs` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Vado` | `wsINETER-BNC:P_VadoType` |

### `wsINETER-BNC:P_Zona_Rocosa`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `hgt` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `rkf` | `xsd:int` |
| `txt` | `xsd:string` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `P_Zona_Rocosa` | `wsINETER-BNC:P_Zona_RocosaType` |

### `wsINETER-BNC:PCA030_Elevacion`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `f_code` | `xsd:string` |
| `zv2` | `xsd:int` |
| `PCA030_Elevacion` | `wsINETER-BNC:PCA030_ElevacionType` |

### `wsINETER-BNC:Rio_Monitoreo_LLuvia`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `uid` | `xsd:string` |
| `fcode` | `xsd:string` |
| `acc` | `xsd:int` |
| `cda` | `xsd:int` |
| `hyp` | `xsd:int` |
| `lbv` | `xsd:double` |
| `nam` | `xsd:string` |
| `nfi` | `xsd:string` |
| `nfn` | `xsd:string` |
| `rbv` | `xsd:double` |
| `shl` | `xsd:int` |
| `shr` | `xsd:int` |
| `tid` | `xsd:int` |
| `txt` | `xsd:string` |
| `wcc` | `xsd:int` |
| `wid` | `xsd:double` |
| `wst` | `xsd:int` |
| `ace` | `xsd:double` |
| `ace_eval` | `xsd:int` |
| `ale` | `xsd:double` |
| `ale_eval` | `xsd:int` |
| `cpyrt_note` | `xsd:string` |
| `src_date` | `xsd:string` |
| `src_info` | `xsd:string` |
| `src_name` | `xsd:int` |
| `tier_note` | `xsd:string` |
| `upd_date` | `xsd:string` |
| `upd_info` | `xsd:string` |
| `upd_name` | `xsd:int` |
| `zval_type` | `xsd:int` |
| `cambios` | `xsd:string` |
| `Rio_Monitoreo_LLuvia` | `wsINETER-BNC:Rio_Monitoreo_LLuviaType` |

### `wsINETER-DGCF:Cobertura_Catastral`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `ubicacion` | `xsd:string` |
| `territorio` | `xsd:string` |
| `etapa` | `xsd:string` |
| `zona` | `xsd:string` |
| `objectid` | `xsd:int` |
| `dpto` | `xsd:string` |
| `clase` | `xsd:string` |
| `nombre` | `xsd:string` |
| `label` | `xsd:string` |
| `zona_2` | `xsd:string` |
| `area_cober` | `xsd:double` |
| `parcelas` | `xsd:string` |
| `Cobertura_Catastral` | `wsINETER-DGCF:Cobertura_CatastralType` |

### `wsINETER-DGCF:Micro_Presas`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `dimension` | `xsd:long` |
| `label` | `xsd:string` |
| `surfacerel` | `xsd:long` |
| `numerocata` | `xsd:string` |
| `mapaparcel` | `xsd:string` |
| `beginlifes` | `xsd:string` |
| `endlifespa` | `xsd:string` |
| `isdeleted` | `xsd:long` |
| `deleteruse` | `xsd:decimal` |
| `deletionti` | `xsd:string` |
| `lastmodifi` | `xsd:string` |
| `lastmodi_1` | `xsd:decimal` |
| `creationti` | `xsd:string` |
| `creatoruse` | `xsd:decimal` |
| `spatialsou` | `xsd:decimal` |
| `polygonlev` | `xsd:decimal` |
| `quality_id` | `xsd:decimal` |
| `referencep` | `xsd:decimal` |
| `source_id` | `xsd:decimal` |
| `ni_polygon` | `xsd:decimal` |
| `nap` | `xsd:string` |
| `codigoencu` | `xsd:string` |
| `estadotran` | `xsd:long` |
| `regimenpar` | `xsd:long` |
| `zona` | `xsd:long` |
| `idmunicipi` | `xsd:decimal` |
| `edicionblo` | `xsd:long` |
| `bloqueada` | `xsd:long` |
| `usoparcela` | `xsd:long` |
| `estadosane` | `xsd:long` |
| `fechaconco` | `xsd:string` |
| `idtematica` | `xsd:decimal` |
| `tienederec` | `xsd:long` |
| `homologaci` | `xsd:long` |
| `codigosisc` | `xsd:string` |
| `homologa_1` | `xsd:long` |
| `codigosi_1` | `xsd:string` |
| `Micro_Presas` | `wsINETER-DGCF:Micro_PresasType` |

### `wsINETER-DGCF:Municipio_Parcelas`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `codigo` | `xsd:string` |
| `municipio` | `xsd:string` |
| `zona` | `xsd:string` |
| `coberturaarea` | `xsd:string` |
| `cantidadparcelas` | `xsd:string` |
| `codmunicipio` | `xsd:string` |
| `Municipio_Parcelas` | `wsINETER-DGCF:Municipio_ParcelasType` |

### `wsINETER-DGCF:nc-boaco`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `nc` | `xsd:string` |
| `mparcela` | `xsd:string` |
| `depto` | `xsd:string` |
| `municipio` | `xsd:string` |
| `polygonlev` | `xsd:string` |
| `tematica` | `xsd:string` |
| `barrio` | `xsd:string` |
| `distrito` | `xsd:string` |
| `nc-boaco` | `wsINETER-DGCF:nc-boacoType` |

### `wsINETER-DGCF:nc-carazo`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `nc` | `xsd:string` |
| `mparcela` | `xsd:string` |
| `depto` | `xsd:string` |
| `municipio` | `xsd:string` |
| `polygonlev` | `xsd:string` |
| `tematica` | `xsd:string` |
| `barrio` | `xsd:string` |
| `distrito` | `xsd:string` |
| `nc-carazo` | `wsINETER-DGCF:nc-carazoType` |

### `wsINETER-DGCF:nc-chinandega`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `nc` | `xsd:string` |
| `mparcela` | `xsd:string` |
| `depto` | `xsd:string` |
| `municipio` | `xsd:string` |
| `polygonlev` | `xsd:string` |
| `tematica` | `xsd:string` |
| `barrio` | `xsd:string` |
| `distrito` | `xsd:string` |
| `nc-chinandega` | `wsINETER-DGCF:nc-chinandegaType` |

### `wsINETER-DGCF:nc-chinandega_test`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `nc` | `xsd:string` |
| `mparcela` | `xsd:string` |
| `depto` | `xsd:string` |
| `municipio` | `xsd:string` |
| `polygonlev` | `xsd:string` |
| `tematica` | `xsd:string` |
| `barrio` | `xsd:string` |
| `distrito` | `xsd:string` |
| `nc-chinandega_test` | `wsINETER-DGCF:nc-chinandega_testType` |

### `wsINETER-DGCF:nc-chontales`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `nc` | `xsd:string` |
| `mparcela` | `xsd:string` |
| `depto` | `xsd:string` |
| `municipio` | `xsd:string` |
| `polygonlev` | `xsd:string` |
| `tematica` | `xsd:string` |
| `barrio` | `xsd:string` |
| `distrito` | `xsd:string` |
| `nc-chontales` | `wsINETER-DGCF:nc-chontalesType` |

### `wsINETER-DGCF:nc-esteli`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `nc` | `xsd:string` |
| `mparcela` | `xsd:string` |
| `depto` | `xsd:string` |
| `municipio` | `xsd:string` |
| `polygonlev` | `xsd:string` |
| `tematica` | `xsd:string` |
| `barrio` | `xsd:string` |
| `distrito` | `xsd:string` |
| `nc-esteli` | `wsINETER-DGCF:nc-esteliType` |

### `wsINETER-DGCF:nc-granada`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `nc` | `xsd:string` |
| `mparcela` | `xsd:string` |
| `depto` | `xsd:string` |
| `municipio` | `xsd:string` |
| `polygonlev` | `xsd:string` |
| `tematica` | `xsd:string` |
| `barrio` | `xsd:string` |
| `distrito` | `xsd:string` |
| `nc-granada` | `wsINETER-DGCF:nc-granadaType` |

### `wsINETER-DGCF:nc-jinotega`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `nc` | `xsd:string` |
| `mparcela` | `xsd:string` |
| `depto` | `xsd:string` |
| `municipio` | `xsd:string` |
| `polygonlev` | `xsd:string` |
| `tematica` | `xsd:string` |
| `barrio` | `xsd:string` |
| `distrito` | `xsd:string` |
| `nc-jinotega` | `wsINETER-DGCF:nc-jinotegaType` |

### `wsINETER-DGCF:nc-leon`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `nc` | `xsd:string` |
| `mparcela` | `xsd:string` |
| `depto` | `xsd:string` |
| `municipio` | `xsd:string` |
| `polygonlev` | `xsd:string` |
| `tematica` | `xsd:string` |
| `barrio` | `xsd:string` |
| `distrito` | `xsd:string` |
| `nc-leon` | `wsINETER-DGCF:nc-leonType` |

### `wsINETER-DGCF:nc-madriz`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `nc` | `xsd:string` |
| `mparcela` | `xsd:string` |
| `depto` | `xsd:string` |
| `municipio` | `xsd:string` |
| `polygonlev` | `xsd:string` |
| `tematica` | `xsd:string` |
| `barrio` | `xsd:string` |
| `distrito` | `xsd:string` |
| `nc-madriz` | `wsINETER-DGCF:nc-madrizType` |

### `wsINETER-DGCF:nc-managua`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `nc` | `xsd:string` |
| `mparcela` | `xsd:string` |
| `depto` | `xsd:string` |
| `municipio` | `xsd:string` |
| `polygonlev` | `xsd:string` |
| `tematica` | `xsd:string` |
| `barrio` | `xsd:string` |
| `distrito` | `xsd:string` |
| `nc-managua` | `wsINETER-DGCF:nc-managuaType` |

### `wsINETER-DGCF:nc-masaya`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `nc` | `xsd:string` |
| `mparcela` | `xsd:string` |
| `depto` | `xsd:string` |
| `municipio` | `xsd:string` |
| `polygonlev` | `xsd:string` |
| `tematica` | `xsd:string` |
| `barrio` | `xsd:string` |
| `distrito` | `xsd:string` |
| `nc-masaya` | `wsINETER-DGCF:nc-masayaType` |

### `wsINETER-DGCF:nc-matagalpa`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `nc` | `xsd:string` |
| `mparcela` | `xsd:string` |
| `depto` | `xsd:string` |
| `municipio` | `xsd:string` |
| `polygonlev` | `xsd:string` |
| `tematica` | `xsd:string` |
| `barrio` | `xsd:string` |
| `distrito` | `xsd:string` |
| `nc-matagalpa` | `wsINETER-DGCF:nc-matagalpaType` |

### `wsINETER-DGCF:nc-nuevasegovia`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `nc` | `xsd:string` |
| `mparcela` | `xsd:string` |
| `depto` | `xsd:string` |
| `municipio` | `xsd:string` |
| `polygonlev` | `xsd:string` |
| `tematica` | `xsd:string` |
| `barrio` | `xsd:string` |
| `distrito` | `xsd:string` |
| `nc-nuevasegovia` | `wsINETER-DGCF:nc-nuevasegoviaType` |

### `wsINETER-DGCF:nc-raccn`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `numerocata` | `xsd:string` |
| `mapaparcel` | `xsd:string` |
| `departamen` | `xsd:string` |
| `municipio` | `xsd:string` |
| `polygonlev` | `xsd:string` |
| `tematica` | `xsd:string` |
| `barrio` | `xsd:string` |
| `distrito` | `xsd:string` |
| `nc-raccn` | `wsINETER-DGCF:nc-raccnType` |

### `wsINETER-DGCF:nc-rivas`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `nc` | `xsd:string` |
| `mparcela` | `xsd:string` |
| `depto` | `xsd:string` |
| `municipio` | `xsd:string` |
| `polygonlev` | `xsd:string` |
| `tematica` | `xsd:string` |
| `barrio` | `xsd:string` |
| `distrito` | `xsd:string` |
| `nc-rivas` | `wsINETER-DGCF:nc-rivasType` |

### `wsINETER-DGCF:Parque`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `region` | `xsd:string` |
| `nom_dep` | `xsd:string` |
| `nom_mun` | `xsd:string` |
| `ubicacion` | `xsd:string` |
| `barr_comar` | `xsd:string` |
| `nom_comun` | `xsd:string` |
| `tipo` | `xsd:string` |
| `nombre` | `xsd:string` |
| `cod_equip` | `xsd:string` |
| `cod_gps` | `xsd:string` |
| `coord_x` | `xsd:double` |
| `coord_y` | `xsd:double` |
| `estado` | `xsd:string` |
| `prob_amb` | `xsd:string` |
| `cual_p_amb` | `xsd:string` |
| `prop_inv` | `xsd:string` |
| `observ` | `xsd:string` |
| `Parque` | `wsINETER-DGCF:ParqueType` |

### `wsINETER-DGCF:SIICAR_Boaco`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `IdMunicipi` | `xsd:long` |
| `Cantidad` | `xsd:string` |
| `SIICAR_Boaco` | `wsINETER-DGCF:SIICAR_BoacoType` |

### `wsINETER-DGCF:SIICAR_Carazo`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `IdMunicipi` | `xsd:long` |
| `Cantidad` | `xsd:string` |
| `SIICAR_Carazo` | `wsINETER-DGCF:SIICAR_CarazoType` |

### `wsINETER-DGCF:SIICAR_Chinandega`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `CodigoMuni` | `xsd:string` |
| `SIICAR_Chinandega` | `wsINETER-DGCF:SIICAR_ChinandegaType` |

### `wsINETER-DGCF:SIICAR_Esteli`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `dimension` | `xsd:long` |
| `label` | `xsd:string` |
| `surfaceRel` | `xsd:long` |
| `MapaParcel` | `xsd:string` |
| `endLifespa` | `xsd:string` |
| `IsDeleted` | `xsd:long` |
| `DeleterUse` | `xsd:long` |
| `DeletionTi` | `xsd:string` |
| `LastModifi` | `xsd:string` |
| `LastModi_1` | `xsd:long` |
| `CreationTi` | `xsd:string` |
| `SpatialSou` | `xsd:long` |
| `PolygonLev` | `xsd:long` |
| `quality_Id` | `xsd:long` |
| `referenceP` | `xsd:long` |
| `source_Id` | `xsd:long` |
| `NI_Polygon` | `xsd:long` |
| `NAP` | `xsd:string` |
| `CodigoEncu` | `xsd:string` |
| `EstadoTran` | `xsd:long` |
| `RegimenPar` | `xsd:long` |
| `Zona` | `xsd:long` |
| `IdMunicipi` | `xsd:long` |
| `EdicionBlo` | `xsd:long` |
| `Bloqueada` | `xsd:long` |
| `UsoParcela` | `xsd:long` |
| `SysStartTi` | `xsd:string` |
| `SysEndTime` | `xsd:string` |
| `EstadoSane` | `xsd:long` |
| `FechaConco` | `xsd:string` |
| `IdTematica` | `xsd:long` |
| `TieneDerec` | `xsd:long` |
| `Homologaci` | `xsd:long` |
| `CodigoSisc` | `xsd:string` |
| `Homologa_1` | `xsd:long` |
| `CodigoSi_1` | `xsd:string` |
| `FechaHomol` | `xsd:string` |
| `IdBarrios` | `xsd:long` |
| `Cantidad` | `xsd:string` |
| `SIICAR_Esteli` | `wsINETER-DGCF:SIICAR_EsteliType` |

### `wsINETER-DGCF:SIICAR_Granada`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `IdMunicipi` | `xsd:long` |
| `Cantidad` | `xsd:string` |
| `SIICAR_Granada` | `wsINETER-DGCF:SIICAR_GranadaType` |

### `wsINETER-DGCF:SIICAR_Jinotega`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `IdMunicipi` | `xsd:long` |
| `Cantidad` | `xsd:string` |
| `SIICAR_Jinotega` | `wsINETER-DGCF:SIICAR_JinotegaType` |

### `wsINETER-DGCF:SIICAR_Leon`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `IdMunicipi` | `xsd:long` |
| `Cantidad` | `xsd:string` |
| `SIICAR_Leon` | `wsINETER-DGCF:SIICAR_LeonType` |

### `wsINETER-DGCF:SIICAR_Madriz`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `IdMunicipi` | `xsd:long` |
| `Cantidad` | `xsd:string` |
| `SIICAR_Madriz` | `wsINETER-DGCF:SIICAR_MadrizType` |

### `wsINETER-DGCF:SIICAR_Managua`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `IdMunicipi` | `xsd:long` |
| `Cantidad` | `xsd:string` |
| `SIICAR_Managua` | `wsINETER-DGCF:SIICAR_ManaguaType` |

### `wsINETER-DGCF:SIICAR_Masaya`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `IdMunicipi` | `xsd:long` |
| `Cantidad` | `xsd:string` |
| `SIICAR_Masaya` | `wsINETER-DGCF:SIICAR_MasayaType` |

### `wsINETER-DGCF:SIICAR_Matagalpa`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `IdMunicipi` | `xsd:long` |
| `Cantidad` | `xsd:string` |
| `SIICAR_Matagalpa` | `wsINETER-DGCF:SIICAR_MatagalpaType` |

### `wsINETER-DGCF:SIICAR_NuevaSegovia`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `IdMunicipi` | `xsd:long` |
| `Cantidad` | `xsd:string` |
| `SIICAR_NuevaSegovia` | `wsINETER-DGCF:SIICAR_NuevaSegoviaType` |

### `wsINETER-DGCF:SIICAR_Rivas`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `IdMunicipi` | `xsd:long` |
| `Cantidad` | `xsd:string` |
| `SIICAR_Rivas` | `wsINETER-DGCF:SIICAR_RivasType` |

### `wsINETER-DGCF:Territorios_Indigenas_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `ubicacion` | `xsd:string` |
| `territorio` | `xsd:string` |
| `etapa` | `xsd:string` |
| `zona` | `xsd:string` |
| `Territorios_Indigenas_2022` | `wsINETER-DGCF:Territorios_Indigenas_2022Type` |

### `wsINETER-DGCF:Vinculo_Municipios_DGCF`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nv1_cod` | `xsd:string` |
| `nv3_cod` | `xsd:string` |
| `nv3_cod_in` | `xsd:string` |
| `nv3_nbre` | `xsd:string` |
| `nv3_area` | `xsd:decimal` |
| `Vinculo_Municipios_DGCF` | `wsINETER-DGCF:Vinculo_Municipios_DGCFType` |

### `wsINETER-DGCF:Zona_Catastro_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `dpto` | `xsd:string` |
| `clase` | `xsd:string` |
| `nombre` | `xsd:string` |
| `label` | `xsd:string` |
| `zona` | `xsd:string` |
| `area_cober` | `xsd:double` |
| `parcelas` | `xsd:string` |
| `Zona_Catastro_2022` | `wsINETER-DGCF:Zona_Catastro_2022Type` |

### `wsINETER-DGCF:zonas_catastro_2022-28`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `dpto` | `xsd:string` |
| `clase` | `xsd:string` |
| `nombre` | `xsd:string` |
| `label` | `xsd:string` |
| `zona` | `xsd:string` |
| `zonas_catastro_2022-28` | `wsINETER-DGCF:zonas_catastro_2022-28Type` |

### `wsINETER-DGGC:Comunidades`

| Campo | Tipo |
|---|---|
| `nombre` | `xsd:string` |
| `municipio` | `xsd:string` |
| `departamento` | `xsd:string` |
| `geom` | `gml:GeometryPropertyType` |
| `Comunidades` | `wsINETER-DGGC:ComunidadesType` |

### `wsINETER-DGGC:Comunidades_Punto`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `nombre` | `xsd:string` |
| `Comunidades_Punto` | `wsINETER-DGGC:Comunidades_PuntoType` |

### `wsINETER-DGGC:cp_BarriosComunidadesMGA`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nombre` | `xsd:string` |
| `id_barrio` | `xsd:string` |
| `vivparticu` | `xsd:long` |
| `sinenergia` | `xsd:long` |
| `sinaguapot` | `xsd:long` |
| `mayor5kmcs` | `xsd:long` |
| `poblaciont` | `xsd:long` |
| `hommayor15` | `xsd:long` |
| `hommenor15` | `xsd:long` |
| `mujmayor15` | `xsd:long` |
| `mujmenor15` | `xsd:long` |
| `nopropiate` | `xsd:long` |
| `municipio` | `xsd:string` |
| `codigo` | `xsd:string` |
| `sinluzelec` | `xsd:double` |
| `cp_BarriosComunidadesMGA` | `wsINETER-DGGC:cp_BarriosComunidadesMGAType` |

### `wsINETER-DGGC:cp_DivAdminMGA`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id_departa` | `xsd:string` |
| `id_municip` | `xsd:string` |
| `nombre` | `xsd:string` |
| `cp_DivAdminMGA` | `wsINETER-DGGC:cp_DivAdminMGAType` |

### `wsINETER-DGGC:Departamentos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `nom_departamento` | `xsd:string` |
| `Departamentos` | `wsINETER-DGGC:DepartamentosType` |

### `wsINETER-DGGC:Estaciones_Geodesicas`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `nombre` | `xsd:string` |
| `codigo` | `xsd:string` |
| `latitud` | `xsd:decimal` |
| `longitud` | `xsd:decimal` |
| `Estaciones_Geodesicas` | `wsINETER-DGGC:Estaciones_GeodesicasType` |

### `wsINETER-DGGC:Lim_Comunidades_ALLAC`

| Campo | Tipo |
|---|---|
| `nombre` | `xsd:string` |
| `municipio` | `xsd:string` |
| `departamento` | `xsd:string` |
| `geom` | `gml:GeometryPropertyType` |
| `Lim_Comunidades_ALLAC` | `wsINETER-DGGC:Lim_Comunidades_ALLACType` |

### `wsINETER-DGGC:Lim_Departamental`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nv1_cod` | `xsd:string` |
| `nv2_cod` | `xsd:string` |
| `nv2_cod_in` | `xsd:string` |
| `nv2_nbre` | `xsd:string` |
| `nv2_area` | `xsd:double` |
| `pobt_2018` | `xsd:long` |
| `pobh_2018` | `xsd:long` |
| `pobm_2018` | `xsd:long` |
| `vivt_2005` | `xsd:long` |
| `obs` | `xsd:string` |
| `Lim_Departamental` | `wsINETER-DGGC:Lim_DepartamentalType` |

### `wsINETER-DGGC:Lim_Departamental_ALLAC`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nv1_cod` | `xsd:string` |
| `nv2_cod` | `xsd:string` |
| `nv2_cod_in` | `xsd:string` |
| `nv2_nbre` | `xsd:string` |
| `nv2_area` | `xsd:double` |
| `pobt_2018` | `xsd:long` |
| `pobh_2018` | `xsd:long` |
| `pobm_2018` | `xsd:long` |
| `vivt_2005` | `xsd:long` |
| `obs` | `xsd:string` |
| `Lim_Departamental_ALLAC` | `wsINETER-DGGC:Lim_Departamental_ALLACType` |

### `wsINETER-DGGC:Lim_Departamentales_SI`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nv2_nbre` | `xsd:string` |
| `pobt_2018` | `xsd:string` |
| `nv2_area` | `xsd:string` |
| `Lim_Departamentales_SI` | `wsINETER-DGGC:Lim_Departamentales_SIType` |

### `wsINETER-DGGC:Lim_DepartamentalesR`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nv2_nbre` | `xsd:string` |
| `pobt_2018` | `xsd:string` |
| `nv2_area` | `xsd:string` |
| `Lim_DepartamentalesR` | `wsINETER-DGGC:Lim_DepartamentalesRType` |

### `wsINETER-DGGC:Lim_Municipal`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nv1_cod` | `xsd:string` |
| `nv2_cod` | `xsd:string` |
| `nv3_cod` | `xsd:string` |
| `nv3_cod_in` | `xsd:string` |
| `nv3_nbre` | `xsd:string` |
| `nv3_area` | `xsd:double` |
| `pobt_2018` | `xsd:long` |
| `pobh_2018` | `xsd:long` |
| `pobm_2018` | `xsd:long` |
| `vivt_2005` | `xsd:long` |
| `obs` | `xsd:string` |
| `Lim_Municipal` | `wsINETER-DGGC:Lim_MunicipalType` |

### `wsINETER-DGGC:Lim_Municipal_ALLAC`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nv1_cod` | `xsd:string` |
| `nv2_cod` | `xsd:string` |
| `nv3_cod` | `xsd:string` |
| `nv3_cod_in` | `xsd:string` |
| `nv3_nbre` | `xsd:string` |
| `nv3_area` | `xsd:double` |
| `pobt_2018` | `xsd:long` |
| `pobh_2018` | `xsd:long` |
| `pobm_2018` | `xsd:long` |
| `vivt_2005` | `xsd:long` |
| `obs` | `xsd:string` |
| `Lim_Municipal_ALLAC` | `wsINETER-DGGC:Lim_Municipal_ALLACType` |

### `wsINETER-DGGC:Lim_Municipales_SI`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nv3_nbre` | `xsd:string` |
| `pobt_2018` | `xsd:string` |
| `nv3_area` | `xsd:string` |
| `Lim_Municipales_SI` | `wsINETER-DGGC:Lim_Municipales_SIType` |

### `wsINETER-DGGC:Lim_MunicipalesR`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nv3_nbre` | `xsd:string` |
| `pobt_2018` | `xsd:string` |
| `nv3_area` | `xsd:string` |
| `Lim_MunicipalesR` | `wsINETER-DGGC:Lim_MunicipalesRType` |

### `wsINETER-DGGC:Lim_Nacional`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nv1_cod` | `xsd:string` |
| `nv1_nbre` | `xsd:string` |
| `nv1_area` | `xsd:double` |
| `pobt_2018` | `xsd:long` |
| `pobh_2018` | `xsd:long` |
| `pobm_2018` | `xsd:long` |
| `vivt_2005` | `xsd:long` |
| `obs` | `xsd:string` |
| `Lim_Nacional` | `wsINETER-DGGC:Lim_NacionalType` |

### `wsINETER-DGGC:Limites_Comunidades_CI`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `nombre` | `xsd:string` |
| `departamento` | `xsd:string` |
| `municipio` | `xsd:string` |
| `Limites_Comunidades_CI` | `wsINETER-DGGC:Limites_Comunidades_CIType` |

### `wsINETER-DGGC:Limites_Departamentales_CI`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nv2_nbre` | `xsd:string` |
| `pobt_2018` | `xsd:string` |
| `nv2_area` | `xsd:string` |
| `Limites_Departamentales_CI` | `wsINETER-DGGC:Limites_Departamentales_CIType` |

### `wsINETER-DGGC:Limites_Municipales_CI`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nv3_nbre` | `xsd:string` |
| `pobt_2018` | `xsd:string` |
| `nv3_area` | `xsd:string` |
| `Limites_Municipales_CI` | `wsINETER-DGGC:Limites_Municipales_CIType` |

### `wsINETER-DGGC:Limites_Municipales_CI_OS`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nv3_nbre` | `xsd:string` |
| `pobt_2018` | `xsd:string` |
| `nv3_area` | `xsd:string` |
| `Limites_Municipales_CI_OS` | `wsINETER-DGGC:Limites_Municipales_CI_OSType` |

### `wsINETER-DGGC:Limites_Municipales_Nic`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nv1_cod` | `xsd:string` |
| `nv2_cod` | `xsd:string` |
| `nv3_cod` | `xsd:string` |
| `nv3_cod_in` | `xsd:string` |
| `nv3_nbre` | `xsd:string` |
| `nv3_area` | `xsd:double` |
| `pobt_2018` | `xsd:long` |
| `pobh_2018` | `xsd:long` |
| `pobm_2018` | `xsd:long` |
| `vivt_2005` | `xsd:long` |
| `obs` | `xsd:string` |
| `Limites_Municipales_Nic` | `wsINETER-DGGC:Limites_Municipales_NicType` |

### `wsINETER-DGGC:Limites_Municipales_Viaticos`

| Campo | Tipo |
|---|---|
| `id` | `xsd:double` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `geometria` | `xsd:string` |
| `nombre` | `xsd:string` |
| `Limites_Municipales_Viaticos` | `wsINETER-DGGC:Limites_Municipales_ViaticosType` |

### `wsINETER-DGGC:limitesmuniatribushape`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nv1_cod` | `xsd:string` |
| `nv2_cod` | `xsd:string` |
| `nv3_cod` | `xsd:string` |
| `nv3_cod_in` | `xsd:string` |
| `nv3_nbre` | `xsd:string` |
| `nv3_area` | `xsd:decimal` |
| `total_pop` | `xsd:int` |
| `densi` | `xsd:decimal` |
| `g_edad_0_p` | `xsd:int` |
| `g_edad_10` | `xsd:int` |
| `g_edad_20` | `xsd:int` |
| `g_edad_30` | `xsd:int` |
| `g_edad_40` | `xsd:int` |
| `g_edad_50` | `xsd:int` |
| `g_edad_60` | `xsd:int` |
| `tot_hu` | `xsd:int` |
| `hac_cuarto` | `xsd:int` |
| `hac_dormit` | `xsd:int` |
| `h_riesg_ia` | `xsd:int` |
| `h_riesg_im` | `xsd:int` |
| `vb_acu` | `xsd:int` |
| `vc_alc` | `xsd:int` |
| `p_gru_1` | `xsd:int` |
| `p_gru_2` | `xsd:int` |
| `p_gru_3` | `xsd:int` |
| `p_gru_4` | `xsd:int` |
| `p_gru_5` | `xsd:int` |
| `p_gru_7` | `xsd:int` |
| `p_gru_8` | `xsd:int` |
| `my60uniper` | `xsd:int` |
| `my60nofam` | `xsd:int` |
| `p_disc` | `xsd:int` |
| `p_pobr` | `xsd:int` |
| `p_ingr_med` | `xsd:int` |
| `p_ingr_r` | `xsd:int` |
| `limitesmuniatribushape` | `wsINETER-DGGC:limitesmuniatribushapeType` |

### `wsINETER-DGGC:muni`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nombre` | `xsd:string` |
| `muni` | `wsINETER-DGGC:muniType` |

### `wsINETER-DGGC:Municipios`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `nom_municipio` | `xsd:string` |
| `cod_municipio` | `xsd:int` |
| `nom_departamento` | `xsd:string` |
| `area` | `xsd:decimal` |
| `Municipios` | `wsINETER-DGGC:MunicipiosType` |

### `wsINETER-DGGC:N1_Nicaragua`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `NV1_COD` | `xsd:string` |
| `NV1_NBRE` | `xsd:string` |
| `NV1_AREA` | `xsd:double` |
| `TOTAL_POP` | `xsd:long` |
| `DENSI` | `xsd:double` |
| `DENSI_R` | `xsd:long` |
| `G_EDAD_0_P` | `xsd:double` |
| `G_EDAD_10` | `xsd:double` |
| `G_EDAD_20` | `xsd:double` |
| `G_EDAD_30` | `xsd:double` |
| `G_EDAD_40` | `xsd:double` |
| `G_EDAD_50` | `xsd:double` |
| `G_EDAD_60` | `xsd:double` |
| `TOTAL_HU` | `xsd:long` |
| `HAC_CUARTO` | `xsd:double` |
| `HAC_DORMIT` | `xsd:double` |
| `H_RIESG_IA` | `xsd:double` |
| `H_RIESG_IM` | `xsd:double` |
| `VB_ACU` | `xsd:double` |
| `VC_ALC` | `xsd:double` |
| `P_GRU_1` | `xsd:double` |
| `P_GRU_2` | `xsd:double` |
| `P_GRU_3` | `xsd:double` |
| `P_GRU_4` | `xsd:double` |
| `P_GRU_5` | `xsd:double` |
| `P_GRU_7` | `xsd:double` |
| `P_GRU_8` | `xsd:double` |
| `MY60UNIPER` | `xsd:double` |
| `MY60NOFAM` | `xsd:double` |
| `P_DISC` | `xsd:double` |
| `P_POBR` | `xsd:double` |
| `P_INGR_MED` | `xsd:double` |
| `P_INGR_R` | `xsd:double` |
| `N1_Nicaragua` | `wsINETER-DGGC:N1_NicaraguaType` |

### `wsINETER-DGGC:N2_Nicaragua`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `NV1_COD` | `xsd:string` |
| `NV2_COD` | `xsd:string` |
| `NV2_COD_IN` | `xsd:string` |
| `NV2_NBRE` | `xsd:string` |
| `NV2_AREA` | `xsd:double` |
| `TOTAL_POP` | `xsd:long` |
| `DENSI` | `xsd:double` |
| `DENSI_R` | `xsd:double` |
| `G_EDAD_0_P` | `xsd:double` |
| `G_EDAD_10` | `xsd:double` |
| `G_EDAD_2` | `xsd:double` |
| `G_EDAD_30` | `xsd:double` |
| `G_EDAD_40` | `xsd:double` |
| `G_EDAD_50` | `xsd:double` |
| `G_EDAD_60` | `xsd:double` |
| `TOTAL_HU` | `xsd:long` |
| `HAC_CUARTO` | `xsd:double` |
| `HAC_DORMIT` | `xsd:double` |
| `H_RIESG_IA` | `xsd:double` |
| `H_RIESG_IM` | `xsd:double` |
| `VB_ACU` | `xsd:double` |
| `VC_ALC` | `xsd:double` |
| `P_GRU_1` | `xsd:double` |
| `P_GRU_2` | `xsd:double` |
| `P_GRU_3` | `xsd:double` |
| `P_GRU_4` | `xsd:double` |
| `P_GRU_5` | `xsd:double` |
| `P_GRU_7` | `xsd:double` |
| `P_GRU_8` | `xsd:double` |
| `MY60UNIPER` | `xsd:double` |
| `MY60NOFAM` | `xsd:double` |
| `P_DISC` | `xsd:double` |
| `P_POBR` | `xsd:double` |
| `P_INGR_MED` | `xsd:double` |
| `P_INGR_R` | `xsd:double` |
| `N2_Nicaragua` | `wsINETER-DGGC:N2_NicaraguaType` |

### `wsINETER-DGGC:N3_Nicaragua`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `NV1_COD` | `xsd:string` |
| `NV2_COD` | `xsd:string` |
| `NV3_COD` | `xsd:string` |
| `NV3_COD_IN` | `xsd:string` |
| `NV3_NBRE` | `xsd:string` |
| `NV3_AREA` | `xsd:double` |
| `TOTAL_POP` | `xsd:long` |
| `DENSI` | `xsd:double` |
| `DENSI_R` | `xsd:double` |
| `G_EDAD_0_P` | `xsd:double` |
| `G_EDAD_10` | `xsd:double` |
| `G_EDAD_20` | `xsd:double` |
| `G_EDAD_30` | `xsd:double` |
| `G_EDAD_40` | `xsd:double` |
| `G_EDAD_50` | `xsd:double` |
| `G_EDAD_60` | `xsd:double` |
| `TOTAL_HU` | `xsd:long` |
| `HAC_CUARTO` | `xsd:double` |
| `HAC_DORMIT` | `xsd:double` |
| `H_RIESG_IA` | `xsd:double` |
| `H_RIESG_IM` | `xsd:double` |
| `VB_ACU` | `xsd:double` |
| `VC_ALC` | `xsd:double` |
| `P_GRU_1` | `xsd:double` |
| `P_GRU_2` | `xsd:double` |
| `P_GRU_3` | `xsd:double` |
| `P_GRU_4` | `xsd:double` |
| `P_GRU_5` | `xsd:double` |
| `P_GRU_7` | `xsd:double` |
| `P_GRU_8` | `xsd:double` |
| `MY60UNIPER` | `xsd:double` |
| `MY60NOFAM` | `xsd:double` |
| `P_DISC` | `xsd:double` |
| `P_POBR` | `xsd:double` |
| `P_INGR_MED` | `xsd:string` |
| `P_INGR_R` | `xsd:string` |
| `N3_Nicaragua` | `wsINETER-DGGC:N3_NicaraguaType` |

### `wsINETER-DGGC:Nicaragua_Centroide`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nv1_cod` | `xsd:string` |
| `nv2_cod` | `xsd:string` |
| `nv2_cod_in` | `xsd:string` |
| `nv2_nbre` | `xsd:string` |
| `nv2_area` | `xsd:double` |
| `pobt_2018` | `xsd:long` |
| `pobh_2018` | `xsd:long` |
| `pobm_2018` | `xsd:long` |
| `vivt_2005` | `xsd:long` |
| `obs` | `xsd:string` |
| `Nicaragua_Centroide` | `wsINETER-DGGC:Nicaragua_CentroideType` |

### `wsINETER-DGGC:Nicaragua_Nivel1`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nv1_cod` | `xsd:string` |
| `nv1_nbre` | `xsd:string` |
| `nv1_area` | `xsd:double` |
| `pobt_2018` | `xsd:long` |
| `pobh_2018` | `xsd:long` |
| `pobm_2018` | `xsd:long` |
| `vivt_2005` | `xsd:long` |
| `obs` | `xsd:string` |
| `Nicaragua_Nivel1` | `wsINETER-DGGC:Nicaragua_Nivel1Type` |

### `wsINETER-DGGC:Nicaragua_Nivel2`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nv1_cod` | `xsd:string` |
| `nv2_cod` | `xsd:string` |
| `nv2_cod_in` | `xsd:string` |
| `nv2_nbre` | `xsd:string` |
| `nv2_area` | `xsd:double` |
| `pobt_2018` | `xsd:long` |
| `pobh_2018` | `xsd:long` |
| `pobm_2018` | `xsd:long` |
| `vivt_2005` | `xsd:long` |
| `obs` | `xsd:string` |
| `Nicaragua_Nivel2` | `wsINETER-DGGC:Nicaragua_Nivel2Type` |

### `wsINETER-DGGC:Nicaragua_Nivel3`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nv1_cod` | `xsd:string` |
| `nv2_cod` | `xsd:string` |
| `nv3_cod` | `xsd:string` |
| `nv3_cod_in` | `xsd:string` |
| `nv3_nbre` | `xsd:string` |
| `nv3_area` | `xsd:double` |
| `pobt_2018` | `xsd:long` |
| `pobh_2018` | `xsd:long` |
| `pobm_2018` | `xsd:long` |
| `vivt_2005` | `xsd:long` |
| `obs` | `xsd:string` |
| `Nicaragua_Nivel3` | `wsINETER-DGGC:Nicaragua_Nivel3Type` |

### `wsINETER-DGGC:Red_Altimetrica2013`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `id_mapa` | `xsd:string` |
| `norte_latitud_grad` | `xsd:int` |
| `norte_latitud_min` | `xsd:int` |
| `norte_latitud_seg` | `xsd:double` |
| `oeste_longitud_grad` | `xsd:int` |
| `oeste_longitud_min` | `xsd:int` |
| `oeste_longitud_seg` | `xsd:double` |
| `altura_elipsoidal_m` | `xsd:double` |
| `codigo` | `xsd:string` |
| `este_x` | `xsd:int` |
| `norte_y` | `xsd:int` |
| `longitud_x` | `xsd:double` |
| `latitud_y` | `xsd:double` |
| `zona_utm_estandar` | `xsd:string` |
| `Red_Altimetrica2013` | `wsINETER-DGGC:Red_Altimetrica2013Type` |

### `wsINETER-DGGC:Red_Planimetrica`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `id_mapa` | `xsd:string` |
| `norte_latitud_grad` | `xsd:int` |
| `norte_latitud_min` | `xsd:int` |
| `norte_latitud_seg` | `xsd:double` |
| `oeste_longitud_grad` | `xsd:int` |
| `oeste_longitud_min` | `xsd:int` |
| `oeste_longitud_seg` | `xsd:double` |
| `altura_elipsoidal_m` | `xsd:double` |
| `codigo` | `xsd:string` |
| `este_x` | `xsd:int` |
| `norte_y` | `xsd:int` |
| `longitud_x` | `xsd:double` |
| `latitud_y` | `xsd:double` |
| `zona_utm_estandar` | `xsd:string` |
| `Red_Planimetrica` | `wsINETER-DGGC:Red_PlanimetricaType` |

### `wsINETER-DGGC:visor_rgh_buena`

> [!warning] Schema pendente; validar antes de uso.

### `wsINETER-DGGC:vlimdepartamentales_PNRH`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nv2_nbre` | `xsd:string` |
| `pobt_2018` | `xsd:string` |
| `nv2_area` | `xsd:string` |
| `vlimdepartamentales_PNRH` | `wsINETER-DGGC:vlimdepartamentales_PNRHType` |

### `wsINETER-DGGG:Amenaza_Caida_Tefra`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `centroerup` | `xsd:int` |
| `complejoid` | `xsd:int` |
| `Amenaza_Caida_Tefra` | `wsINETER-DGGG:Amenaza_Caida_TefraType` |

### `wsINETER-DGGG:Amenaza_Centro_Eruptivo`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `centroerup` | `xsd:int` |
| `complejoid` | `xsd:int` |
| `zona` | `xsd:string` |
| `Amenaza_Centro_Eruptivo` | `wsINETER-DGGG:Amenaza_Centro_EruptivoType` |

### `wsINETER-DGGG:Amenaza_Cola_Lavas`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `centroerup` | `xsd:int` |
| `complejoid` | `xsd:int` |
| `Amenaza_Cola_Lavas` | `wsINETER-DGGG:Amenaza_Cola_LavasType` |

### `wsINETER-DGGG:Amenaza_Flujo_Lodo_Detritos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `centroerup` | `xsd:int` |
| `Amenaza_Flujo_Lodo_Detritos` | `wsINETER-DGGG:Amenaza_Flujo_Lodo_DetritosType` |

### `wsINETER-DGGG:Amenaza_Flujo_Piroclastico`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `centroerup` | `xsd:int` |
| `complejoid` | `xsd:int` |
| `Amenaza_Flujo_Piroclastico` | `wsINETER-DGGG:Amenaza_Flujo_PiroclasticoType` |

### `wsINETER-DGGG:Amenaza_Gas`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `complejoid` | `xsd:int` |
| `tipo` | `xsd:string` |
| `periodo` | `xsd:string` |
| `Amenaza_Gas` | `wsINETER-DGGG:Amenaza_GasType` |

### `wsINETER-DGGG:Amenaza_Sismica`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `gridcode` | `xsd:long` |
| `Amenaza_Sismica` | `wsINETER-DGGG:Amenaza_SismicaType` |

### `wsINETER-DGGG:Amenaza_Tsunami_Alta`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `gridcode` | `xsd:long` |
| `clases` | `xsd:string` |
| `Amenaza_Tsunami_Alta` | `wsINETER-DGGG:Amenaza_Tsunami_AltaType` |

### `wsINETER-DGGG:Amenaza_Tsunami_Baja`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `gridcode` | `xsd:long` |
| `clases` | `xsd:string` |
| `Amenaza_Tsunami_Baja` | `wsINETER-DGGG:Amenaza_Tsunami_BajaType` |

### `wsINETER-DGGG:Amenaza_Tsunami_Media`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `gridcode` | `xsd:long` |
| `clases` | `xsd:string` |
| `Amenaza_Tsunami_Media` | `wsINETER-DGGG:Amenaza_Tsunami_MediaType` |

### `wsINETER-DGGG:Amenaza_Volcanica`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `tipo` | `xsd:string` |
| `areashape` | `xsd:decimal` |
| `Amenaza_Volcanica` | `wsINETER-DGGG:Amenaza_VolcanicaType` |

### `wsINETER-DGGG:Asentamientos_Amenazados_1Hora`

| Campo | Tipo |
|---|---|
| `idah` | `xsd:int` |
| `nivelalerta` | `xsd:string` |
| `departamento` | `xsd:string` |
| `municipio` | `xsd:string` |
| `nombre` | `xsd:string` |
| `poblacion` | `xsd:double` |
| `viviendas` | `xsd:double` |
| `tiporevestimiento` | `xsd:string` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `lluvia1hr` | `xsd:double` |
| `lluvia24hr` | `xsd:double` |
| `sc_amenazantes` | `xsd:long` |
| `Asentamientos_Amenazados_1Hora` | `wsINETER-DGGG:Asentamientos_Amenazados_1HoraType` |

### `wsINETER-DGGG:asentamientos_humanos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `target_fid` | `xsd:long` |
| `cod_dpto` | `xsd:string` |
| `dpto` | `xsd:string` |
| `cod_mpio` | `xsd:string` |
| `municipio` | `xsd:string` |
| `nombre` | `xsd:string` |
| `id_unico` | `xsd:long` |
| `ha` | `xsd:double` |
| `ti_revesti` | `xsd:string` |
| `dens_vial` | `xsd:double` |
| `cant_acces` | `xsd:double` |
| `suma_long` | `xsd:double` |
| `tfuenagua` | `xsd:string` |
| `estado_v` | `xsd:string` |
| `evpeso_4_1` | `xsd:double` |
| `dvpeso_5_2` | `xsd:double` |
| `ca_peso3_3` | `xsd:double` |
| `t_peso20_p` | `xsd:double` |
| `n_de_esc` | `xsd:double` |
| `ecpeso4_1e` | `xsd:double` |
| `n_inatec` | `xsd:double` |
| `inpeso5_2e` | `xsd:double` |
| `n_univ` | `xsd:double` |
| `unpeso6_3e` | `xsd:double` |
| `nudssalu` | `xsd:double` |
| `slpeso5_1` | `xsd:double` |
| `tspeso12_2` | `xsd:double` |
| `tiudssalud` | `xsd:string` |
| `cercania` | `xsd:string` |
| `c_peso10_c` | `xsd:double` |
| `f_adtva` | `xsd:string` |
| `f_peso5_fa` | `xsd:double` |
| `categ_pobl` | `xsd:string` |
| `peso_15_p` | `xsd:double` |
| `dens_pob` | `xsd:double` |
| `peso_6_1` | `xsd:double` |
| `pobl_2022` | `xsd:double` |
| `pbporviv` | `xsd:double` |
| `no_viviend` | `xsd:double` |
| `categ_dens` | `xsd:string` |
| `tipo_const` | `xsd:string` |
| `tipo` | `xsd:string` |
| `valorfinal` | `xsd:double` |
| `prima_porc` | `xsd:double` |
| `secun_porc` | `xsd:double` |
| `terci_porc` | `xsd:double` |
| `cat_econom` | `xsd:string` |
| `urb_rur1` | `xsd:string` |
| `clasfi_ah1` | `xsd:string` |
| `territorio` | `xsd:string` |
| `asentamientos_humanos` | `wsINETER-DGGG:asentamientos_humanosType` |

### `wsINETER-DGGG:AsentamientosAmenazados`

| Campo | Tipo |
|---|---|
| `idah` | `xsd:int` |
| `nivelalerta` | `xsd:string` |
| `departamento` | `xsd:string` |
| `municipio` | `xsd:string` |
| `nombre` | `xsd:string` |
| `poblacion` | `xsd:double` |
| `viviendas` | `xsd:double` |
| `tiporevestimiento` | `xsd:string` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `lluvia24` | `xsd:double` |
| `lluvia72` | `xsd:double` |
| `sc_amenazantes` | `xsd:long` |
| `AsentamientosAmenazados` | `wsINETER-DGGG:AsentamientosAmenazadosType` |

### `wsINETER-DGGG:bufcamarasweb`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `latitud` | `xsd:decimal` |
| `longitud` | `xsd:decimal` |
| `camara` | `xsd:string` |
| `ubicacion` | `xsd:string` |
| `angulo` | `xsd:int` |
| `ancho_grad` | `xsd:long` |
| `radio_e` | `xsd:double` |
| `bufcamarasweb` | `wsINETER-DGGG:bufcamaraswebType` |

### `wsINETER-DGGG:CadenaVolcanica`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `CadenaVolcanica` | `wsINETER-DGGG:CadenaVolcanicaType` |

### `wsINETER-DGGG:Caida_Tefra`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `rangoespesorcm` | `xsd:string` |
| `centroerup` | `xsd:int` |
| `complejoid` | `xsd:int` |
| `zona` | `xsd:string` |
| `periodogeologico` | `xsd:string` |
| `Caida_Tefra` | `wsINETER-DGGG:Caida_TefraType` |

### `wsINETER-DGGG:Camaras_Volcanes`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `nombre` | `xsd:string` |
| `locacion` | `xsd:string` |
| `x` | `xsd:double` |
| `y` | `xsd:double` |
| `Camaras_Volcanes` | `wsINETER-DGGG:Camaras_VolcanesType` |

### `wsINETER-DGGG:camarasvolcanes1`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `nombre` | `xsd:string` |
| `marca` | `xsd:string` |
| `longitud` | `xsd:decimal` |
| `latitud` | `xsd:decimal` |
| `altura` | `xsd:long` |
| `departamen` | `xsd:string` |
| `municipio` | `xsd:string` |
| `observacio` | `xsd:string` |
| `camarasvolcanes1` | `wsINETER-DGGG:camarasvolcanes1Type` |

### `wsINETER-DGGG:camarasvolcanes2`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `latitud` | `xsd:double` |
| `longitud` | `xsd:double` |
| `volcan` | `xsd:string` |
| `ubicacion` | `xsd:string` |
| `camarasvolcanes2` | `wsINETER-DGGG:camarasvolcanes2Type` |

### `wsINETER-DGGG:Centro_Eruptivo`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `nombre` | `xsd:string` |
| `complejoid` | `xsd:int` |
| `codigoactividad` | `xsd:int` |
| `codigovolcan` | `xsd:int` |
| `codigoerupcion` | `xsd:int` |
| `alturacolumna` | `xsd:int` |
| `tipoamenaza` | `xsd:string` |
| `dismaxlava` | `xsd:decimal` |
| `dismaxbomb` | `xsd:decimal` |
| `dismaxceni` | `xsd:decimal` |
| `dismaxlodo` | `xsd:decimal` |
| `dismaxfluj` | `xsd:decimal` |
| `dismaxgase` | `xsd:decimal` |
| `codigocompquimico` | `xsd:int` |
| `direcionpluma` | `xsd:string` |
| `Centro_Eruptivo` | `wsINETER-DGGG:Centro_EruptivoType` |

### `wsINETER-DGGG:Concepcion_Balistico`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `tipo` | `xsd:string` |
| `areashape` | `xsd:decimal` |
| `tamannioshape` | `xsd:decimal` |
| `Concepcion_Balistico` | `wsINETER-DGGG:Concepcion_BalisticoType` |

### `wsINETER-DGGG:Concepcion_Cenizas`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `tipo` | `xsd:string` |
| `areashape` | `xsd:decimal` |
| `tamannioshape` | `xsd:decimal` |
| `Concepcion_Cenizas` | `wsINETER-DGGG:Concepcion_CenizasType` |

### `wsINETER-DGGG:Concepcion_Flujospiroclasticos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `tipo` | `xsd:string` |
| `areashape` | `xsd:decimal` |
| `tamannioshape` | `xsd:decimal` |
| `Concepcion_Flujospiroclasticos` | `wsINETER-DGGG:Concepcion_FlujospiroclasticosType` |

### `wsINETER-DGGG:Concepcion_Lahares`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `tipo` | `xsd:string` |
| `areashape` | `xsd:decimal` |
| `tamannioshape` | `xsd:decimal` |
| `Concepcion_Lahares` | `wsINETER-DGGG:Concepcion_LaharesType` |

### `wsINETER-DGGG:Concepcion_Lavas`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `tipo` | `xsd:string` |
| `areashape` | `xsd:decimal` |
| `tamannioshape` | `xsd:decimal` |
| `Concepcion_Lavas` | `wsINETER-DGGG:Concepcion_LavasType` |

### `wsINETER-DGGG:Concepcion_Rosa_Vientos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `codigo` | `xsd:string` |
| `Concepcion_Rosa_Vientos` | `wsINETER-DGGG:Concepcion_Rosa_VientosType` |

### `wsINETER-DGGG:Concepcion_Rutas_Evacuacion`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `Concepcion_Rutas_Evacuacion` | `wsINETER-DGGG:Concepcion_Rutas_EvacuacionType` |

### `wsINETER-DGGG:Concepcion_Seguridad_Refugio_Balisticos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `Concepcion_Seguridad_Refugio_Balisticos` | `wsINETER-DGGG:Concepcion_Seguridad_Refugio_BalisticosType` |

### `wsINETER-DGGG:cp_redvolcanica`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `tipo` | `xsd:string` |
| `nombre` | `xsd:string` |
| `lat_geo` | `xsd:decimal` |
| `long_geo` | `xsd:decimal` |
| `elevacion` | `xsd:decimal` |
| `elev_um` | `xsd:string` |
| `anio_erupcion` | `xsd:int` |
| `estado` | `xsd:boolean` |
| `ordenimpresion` | `xsd:short` |
| `cp_redvolcanica` | `wsINETER-DGGG:cp_redvolcanicaType` |

### `wsINETER-DGGG:Cuenca_Nivel7_Shape`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `n3` | `xsd:string` |
| `n4` | `xsd:string` |
| `n5` | `xsd:string` |
| `n6` | `xsd:string` |
| `n7` | `xsd:string` |
| `phca` | `xsd:double` |
| `code_pfafs` | `xsd:double` |
| `cuencas` | `xsd:string` |
| `area` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `Cuenca_Nivel7_Shape` | `wsINETER-DGGG:Cuenca_Nivel7_ShapeType` |

### `wsINETER-DGGG:Curvas_Nivel`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `altura` | `xsd:decimal` |
| `Curvas_Nivel` | `wsINETER-DGGG:Curvas_NivelType` |

### `wsINETER-DGGG:Deslizamiento_Nicaragua_Poligonos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fecha` | `xsd:string` |
| `autor` | `xsd:string` |
| `institucion` | `xsd:string` |
| `forma_acceso` | `xsd:string` |
| `localidad` | `xsd:string` |
| `comarca` | `xsd:string` |
| `municipio` | `xsd:string` |
| `departamento` | `xsd:string` |
| `tipo` | `xsd:string` |
| `subtipo` | `xsd:string` |
| `categoria` | `xsd:string` |
| `sec_estrat` | `xsd:string` |
| `litologia` | `xsd:string` |
| `afectacion` | `xsd:string` |
| `precipitacion` | `xsd:string` |
| `pendiente` | `xsd:string` |
| `factor_con` | `xsd:string` |
| `factor_dec` | `xsd:string` |
| `longitud_m` | `xsd:double` |
| `ancho_m` | `xsd:double` |
| `profundidad` | `xsd:double` |
| `superficie` | `xsd:double` |
| `volumen_m3` | `xsd:double` |
| `descripcion` | `xsd:string` |
| `uso_suelo` | `xsd:string` |
| `amenaza` | `xsd:string` |
| `fid_1` | `xsd:long` |
| `codigo` | `xsd:string` |
| `fid_2` | `xsd:long` |
| `fid_1_1` | `xsd:long` |
| `fid_` | `xsd:long` |
| `x` | `xsd:double` |
| `y` | `xsd:double` |
| `tiposimbol` | `xsd:string` |
| `fid_2_1` | `xsd:long` |
| `cod_bacomu` | `xsd:double` |
| `id_bacomun` | `xsd:long` |
| `comarcas` | `xsd:string` |
| `n2` | `xsd:string` |
| `nom_barrio` | `xsd:string` |
| `cod_munic` | `xsd:long` |
| `cod_depto` | `xsd:long` |
| `code` | `xsd:string` |
| `cod_barrio` | `xsd:long` |
| `contador` | `xsd:long` |
| `id_barrio` | `xsd:string` |
| `anio2` | `xsd:string` |
| `mes2` | `xsd:string` |
| `dia` | `xsd:string` |
| `contador1` | `xsd:string` |
| `distance` | `xsd:double` |
| `oid_` | `xsd:long` |
| `objectid` | `xsd:long` |
| `codinecmun` | `xsd:double` |
| `codinecdep` | `xsd:long` |
| `shape_leng` | `xsd:double` |
| `shape_le_1` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `areaaa` | `xsd:double` |
| `elaborado` | `xsd:string` |
| `Deslizamiento_Nicaragua_Poligonos` | `wsINETER-DGGG:Deslizamiento_Nicaragua_PoligonosType` |

### `wsINETER-DGGG:deslizamientos_nic_puntos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `fecha` | `xsd:string` |
| `x` | `xsd:long` |
| `y` | `xsd:long` |
| `institucion` | `xsd:string` |
| `acceso` | `xsd:string` |
| `localidad` | `xsd:string` |
| `comarca` | `xsd:string` |
| `municipio` | `xsd:string` |
| `departamento` | `xsd:string` |
| `tipo` | `xsd:string` |
| `subtipo` | `xsd:string` |
| `sec_estrat` | `xsd:string` |
| `litologia` | `xsd:string` |
| `afectacion` | `xsd:string` |
| `precipitacion` | `xsd:string` |
| `pendiente` | `xsd:string` |
| `fact_condi` | `xsd:string` |
| `fact_desen` | `xsd:string` |
| `uso_de_suelo` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `autor` | `xsd:string` |
| `objectid` | `xsd:long` |
| `id` | `xsd:double` |
| `elaborado` | `xsd:string` |
| `amenaza` | `xsd:string` |
| `ubicacion` | `xsd:string` |
| `nota` | `xsd:string` |
| `point_otro` | `xsd:string` |
| `point_ot_1` | `xsd:string` |
| `deslizamientos_nic_puntos` | `wsINETER-DGGG:deslizamientos_nic_puntosType` |

### `wsINETER-DGGG:Estaciones_Camaras`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `id` | `xsd:long` |
| `volcan` | `xsd:string` |
| `sitio` | `xsd:string` |
| `latitud` | `xsd:decimal` |
| `longitud` | `xsd:decimal` |
| `orientacio` | `xsd:string` |
| `tipo` | `xsd:string` |
| `Estaciones_Camaras` | `wsINETER-DGGG:Estaciones_CamarasType` |

### `wsINETER-DGGG:estudioszonificacion`

> [!warning] Schema pendente; validar antes de uso.

### `wsINETER-DGGG:EventosSismicos10D`

| Campo | Tipo |
|---|---|
| `id_evento` | `xsd:long` |
| `fecha_hora_local` | `xsd:dateTime` |
| `latitud` | `xsd:decimal` |
| `longitud` | `xsd:decimal` |
| `geom` | `gml:PointPropertyType` |
| `profundidad` | `xsd:decimal` |
| `magnitud` | `xsd:decimal` |
| `tipo` | `xsd:string` |
| `ubicacion_original` | `xsd:string` |
| `id_punto_referencia` | `xsd:long` |
| `punto_referencia` | `xsd:string` |
| `lat_referencia` | `xsd:decimal` |
| `lon_referencia` | `xsd:decimal` |
| `distancia_km` | `xsd:decimal` |
| `azimut` | `xsd:decimal` |
| `direccion` | `xsd:string` |
| `ubicacion` | `xsd:string` |
| `fecha_ultima_actualizacion` | `xsd:dateTime` |
| `EventosSismicos10D` | `wsINETER-DGGG:EventosSismicos10DType` |

### `wsINETER-DGGG:Fallas_Geologicas`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `clase` | `xsd:string` |
| `tamannio` | `xsd:decimal` |
| `Fallas_Geologicas` | `wsINETER-DGGG:Fallas_GeologicasType` |

### `wsINETER-DGGG:Fallas_Lineamientos_Fotogeologicos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `objectid` | `xsd:int` |
| `clase` | `xsd:string` |
| `nombre` | `xsd:string` |
| `fuente` | `xsd:string` |
| `Fallas_Lineamientos_Fotogeologicos` | `wsINETER-DGGG:Fallas_Lineamientos_FotogeologicosType` |

### `wsINETER-DGGG:Fallas_Managua_2015`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `clase` | `xsd:string` |
| `user_id` | `xsd:long` |
| `length` | `xsd:double` |
| `nombre` | `xsd:string` |
| `Fallas_Managua_2015` | `wsINETER-DGGG:Fallas_Managua_2015Type` |

### `wsINETER-DGGG:Fallas_Nacionales`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `formdeter` | `xsd:string` |
| `tipo` | `xsd:string` |
| `clase` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `Fallas_Nacionales` | `wsINETER-DGGG:Fallas_NacionalesType` |

### `wsINETER-DGGG:Fumarolas`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `centroerup` | `xsd:int` |
| `Fumarolas` | `wsINETER-DGGG:FumarolasType` |

### `wsINETER-DGGG:Geol_Apoyeque`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `color` | `xsd:int` |
| `mslink_dmr` | `xsd:long` |
| `leyenda` | `xsd:string` |
| `dep�sito` | `xsd:string` |
| `litolog�` | `xsd:string` |
| `granulomet` | `xsd:string` |
| `secuencia` | `xsd:string` |
| `edad` | `xsd:string` |
| `Geol_Apoyeque` | `wsINETER-DGGG:Geol_ApoyequeType` |

### `wsINETER-DGGG:Geol_Chinandega`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `entity` | `xsd:string` |
| `layer` | `xsd:string` |
| `level` | `xsd:long` |
| `mslink_d_1` | `xsd:long` |
| `cislo_g` | `xsd:long` |
| `popis` | `xsd:string` |
| `dep�sito` | `xsd:string` |
| `litolog�` | `xsd:string` |
| `granulomet` | `xsd:string` |
| `secuencia` | `xsd:string` |
| `edad` | `xsd:string` |
| `Geol_Chinandega` | `wsINETER-DGGG:Geol_ChinandegaType` |

### `wsINETER-DGGG:Geol_Cosiguina`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `color` | `xsd:int` |
| `mslink_dmr` | `xsd:long` |
| `leyenda` | `xsd:string` |
| `dep�sito` | `xsd:string` |
| `litolog�` | `xsd:string` |
| `granulomet` | `xsd:string` |
| `secuencia` | `xsd:string` |
| `edad` | `xsd:string` |
| `Geol_Cosiguina` | `wsINETER-DGGG:Geol_CosiguinaType` |

### `wsINETER-DGGG:Geol_Leon`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `entity` | `xsd:string` |
| `level` | `xsd:long` |
| `color` | `xsd:int` |
| `mslink_dmr` | `xsd:long` |
| `leyenda` | `xsd:string` |
| `id` | `xsd:int` |
| `dep�sitos` | `xsd:string` |
| `litolog�a` | `xsd:string` |
| `granulomet` | `xsd:string` |
| `secuencia` | `xsd:string` |
| `edad` | `xsd:string` |
| `Geol_Leon` | `wsINETER-DGGG:Geol_LeonType` |

### `wsINETER-DGGG:Geol_Masaya`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `litologia` | `xsd:string` |
| `depositos` | `xsd:string` |
| `composic` | `xsd:string` |
| `grupo` | `xsd:string` |
| `secuencia` | `xsd:string` |
| `edad` | `xsd:string` |
| `edad_hist` | `xsd:string` |
| `granulomet` | `xsd:string` |
| `fuenteinfo` | `xsd:string` |
| `Geol_Masaya` | `wsINETER-DGGG:Geol_MasayaType` |

### `wsINETER-DGGG:Geol_Momotombo`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `color` | `xsd:int` |
| `leyenda` | `xsd:string` |
| `dep�sito` | `xsd:string` |
| `litolog�` | `xsd:string` |
| `granulomet` | `xsd:string` |
| `secuencia` | `xsd:string` |
| `edad` | `xsd:string` |
| `Geol_Momotombo` | `wsINETER-DGGG:Geol_MomotomboType` |

### `wsINETER-DGGG:Geol_Ometepe`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `color` | `xsd:int` |
| `mslink_dmr` | `xsd:long` |
| `leyenda` | `xsd:string` |
| `dep�sito` | `xsd:string` |
| `litolog�` | `xsd:string` |
| `grupo` | `xsd:string` |
| `elevaci�` | `xsd:string` |
| `Geol_Ometepe` | `wsINETER-DGGG:Geol_OmetepeType` |

### `wsINETER-DGGG:Geologia_Nicaragua`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `nomencla` | `xsd:string` |
| `sistema` | `xsd:string` |
| `serie` | `xsd:string` |
| `formacion` | `xsd:string` |
| `code_geo` | `xsd:int` |
| `cod_mv` | `xsd:int` |
| `litologia` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `Geologia_Nicaragua` | `wsINETER-DGGG:Geologia_NicaraguaType` |

### `wsINETER-DGGG:Lineas_Redes_Camaras_Volcanes`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `idpg` | `xsd:long` |
| `volcan` | `xsd:string` |
| `lat_origen` | `xsd:decimal` |
| `long_orige` | `xsd:decimal` |
| `orientacio` | `xsd:string` |
| `tipo_linea` | `xsd:string` |
| `origen` | `xsd:string` |
| `destino` | `xsd:string` |
| `lat_destin` | `xsd:decimal` |
| `long_desti` | `xsd:decimal` |
| `tramo` | `xsd:string` |
| `Lineas_Redes_Camaras_Volcanes` | `wsINETER-DGGG:Lineas_Redes_Camaras_VolcanesType` |

### `wsINETER-DGGG:lluvia_sitiocriticos`

| Campo | Tipo |
|---|---|
| `id` | `xsd:long` |
| `geom` | `gml:GeometryPropertyType` |
| `origen` | `xsd:string` |
| `nivelalerta` | `xsd:string` |
| `lluvia24` | `xsd:double` |
| `lluvia72` | `xsd:double` |
| `lluvia_sitiocriticos` | `wsINETER-DGGG:lluvia_sitiocriticosType` |

### `wsINETER-DGGG:Lluviacida`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `complejoid` | `xsd:int` |
| `Lluviacida` | `wsINETER-DGGG:LluviacidaType` |

### `wsINETER-DGGG:Maderas_Deslizamientos_Amenaza_Alta`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `p_susc` | `xsd:string` |
| `geomorf` | `xsd:string` |
| `geolog` | `xsd:string` |
| `uso_suelo` | `xsd:string` |
| `pend` | `xsd:string` |
| `prof` | `xsd:string` |
| `dist` | `xsd:string` |
| `veloc` | `xsd:string` |
| `tipo` | `xsd:string` |
| `vol` | `xsd:string` |
| `area_m2` | `xsd:string` |
| `angle` | `xsd:string` |
| `amenaza` | `xsd:string` |
| `pk` | `xsd:long` |
| `Maderas_Deslizamientos_Amenaza_Alta` | `wsINETER-DGGG:Maderas_Deslizamientos_Amenaza_AltaType` |

### `wsINETER-DGGG:Maderas_Deslizamientos_Amenaza_Baja`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `p_susc` | `xsd:string` |
| `geomorf` | `xsd:string` |
| `geolog` | `xsd:string` |
| `uso_suelo` | `xsd:string` |
| `pend` | `xsd:string` |
| `prof` | `xsd:string` |
| `dist` | `xsd:string` |
| `veloc` | `xsd:string` |
| `tipo` | `xsd:string` |
| `vol` | `xsd:string` |
| `area_m2` | `xsd:string` |
| `angle` | `xsd:string` |
| `amenaza` | `xsd:string` |
| `pk` | `xsd:long` |
| `Maderas_Deslizamientos_Amenaza_Baja` | `wsINETER-DGGG:Maderas_Deslizamientos_Amenaza_BajaType` |

### `wsINETER-DGGG:Maderas_Deslizamientos_Amenaza_Media`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `p_susc` | `xsd:string` |
| `geomorf` | `xsd:string` |
| `geolog` | `xsd:string` |
| `uso_suelo` | `xsd:string` |
| `pend` | `xsd:string` |
| `prof` | `xsd:string` |
| `dist` | `xsd:string` |
| `veloc` | `xsd:string` |
| `tipo` | `xsd:string` |
| `vol` | `xsd:string` |
| `area_m2` | `xsd:string` |
| `angle` | `xsd:string` |
| `amenaza` | `xsd:string` |
| `pk` | `xsd:long` |
| `Maderas_Deslizamientos_Amenaza_Media` | `wsINETER-DGGG:Maderas_Deslizamientos_Amenaza_MediaType` |

### `wsINETER-DGGG:Maderas_Escarpe_Amenaza_Alta`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `p_susc` | `xsd:string` |
| `geomorf` | `xsd:string` |
| `geolog` | `xsd:string` |
| `uso_suelo` | `xsd:string` |
| `pend` | `xsd:string` |
| `prof` | `xsd:string` |
| `dist` | `xsd:string` |
| `veloc` | `xsd:string` |
| `tipo` | `xsd:string` |
| `vol` | `xsd:string` |
| `area_m2` | `xsd:string` |
| `angle` | `xsd:string` |
| `amenaza` | `xsd:string` |
| `pk` | `xsd:long` |
| `Maderas_Escarpe_Amenaza_Alta` | `wsINETER-DGGG:Maderas_Escarpe_Amenaza_AltaType` |

### `wsINETER-DGGG:Maderas_Escarpe_Amenaza_Baja`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `p_susc` | `xsd:string` |
| `geomorf` | `xsd:string` |
| `geolog` | `xsd:string` |
| `uso_suelo` | `xsd:string` |
| `pend` | `xsd:string` |
| `prof` | `xsd:string` |
| `dist` | `xsd:string` |
| `veloc` | `xsd:string` |
| `tipo` | `xsd:string` |
| `vol` | `xsd:string` |
| `area_m2` | `xsd:string` |
| `angle` | `xsd:string` |
| `amenaza` | `xsd:string` |
| `pk` | `xsd:long` |
| `Maderas_Escarpe_Amenaza_Baja` | `wsINETER-DGGG:Maderas_Escarpe_Amenaza_BajaType` |

### `wsINETER-DGGG:Maderas_Lahar_Arranque`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `p_susc` | `xsd:string` |
| `geomorf` | `xsd:string` |
| `geolog` | `xsd:string` |
| `uso_suelo` | `xsd:string` |
| `pend` | `xsd:string` |
| `prof` | `xsd:string` |
| `dist` | `xsd:string` |
| `veloc` | `xsd:string` |
| `tipo` | `xsd:string` |
| `vol` | `xsd:string` |
| `area_m2` | `xsd:string` |
| `angle` | `xsd:string` |
| `pk` | `xsd:long` |
| `Maderas_Lahar_Arranque` | `wsINETER-DGGG:Maderas_Lahar_ArranqueType` |

### `wsINETER-DGGG:Maderas_Lahar_Deposito_Amenaza_Alta`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `p_susc` | `xsd:string` |
| `geomorf` | `xsd:string` |
| `geolog` | `xsd:string` |
| `uso_suelo` | `xsd:string` |
| `pend` | `xsd:string` |
| `prof` | `xsd:string` |
| `dist` | `xsd:string` |
| `veloc` | `xsd:string` |
| `tipo` | `xsd:string` |
| `vol` | `xsd:string` |
| `area_m2` | `xsd:string` |
| `angle` | `xsd:string` |
| `pk` | `xsd:long` |
| `Maderas_Lahar_Deposito_Amenaza_Alta` | `wsINETER-DGGG:Maderas_Lahar_Deposito_Amenaza_AltaType` |

### `wsINETER-DGGG:Maderas_Lahar_Flujo_Escombros`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `p_susc` | `xsd:string` |
| `geomorf` | `xsd:string` |
| `geolog` | `xsd:string` |
| `uso_suelo` | `xsd:string` |
| `pend` | `xsd:string` |
| `prof` | `xsd:string` |
| `dist` | `xsd:string` |
| `veloc` | `xsd:string` |
| `tipo` | `xsd:string` |
| `vol` | `xsd:string` |
| `area_m2` | `xsd:string` |
| `angle` | `xsd:string` |
| `pk` | `xsd:long` |
| `Maderas_Lahar_Flujo_Escombros` | `wsINETER-DGGG:Maderas_Lahar_Flujo_EscombrosType` |

### `wsINETER-DGGG:Maderas_Sitios_Criticos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `lugar` | `xsd:string` |
| `tipo` | `xsd:string` |
| `no_sc` | `xsd:string` |
| `Maderas_Sitios_Criticos` | `wsINETER-DGGG:Maderas_Sitios_CriticosType` |

### `wsINETER-DGGG:Maderas_Zona_Evacuacion`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `area` | `xsd:decimal` |
| `area_km2` | `xsd:decimal` |
| `area_ha` | `xsd:decimal` |
| `Maderas_Zona_Evacuacion` | `wsINETER-DGGG:Maderas_Zona_EvacuacionType` |

### `wsINETER-DGGG:Masaya_Amencaida_Tefra_Hist`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `complejoid` | `xsd:int` |
| `Masaya_Amencaida_Tefra_Hist` | `wsINETER-DGGG:Masaya_Amencaida_Tefra_HistType` |

### `wsINETER-DGGG:Masaya_Amenza_Volcanica`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `amenaza` | `xsd:string` |
| `periodo` | `xsd:string` |
| `Masaya_Amenza_Volcanica` | `wsINETER-DGGG:Masaya_Amenza_VolcanicaType` |

### `wsINETER-DGGG:Masaya_Balistico_10km`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `generico` | `xsd:string` |
| `n_propio` | `xsd:string` |
| `latitud` | `xsd:decimal` |
| `longitud` | `xsd:decimal` |
| `municipio` | `xsd:string` |
| `nomen` | `xsd:string` |
| `msnm` | `xsd:decimal` |
| `hab` | `xsd:decimal` |
| `campo9` | `xsd:string` |
| `campo10` | `xsd:string` |
| `campo11` | `xsd:string` |
| `lat_geo` | `xsd:decimal` |
| `long_geo` | `xsd:decimal` |
| `buff_dist` | `xsd:decimal` |
| `Masaya_Balistico_10km` | `wsINETER-DGGG:Masaya_Balistico_10kmType` |

### `wsINETER-DGGG:Masaya_Calderas`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `categoria` | `xsd:string` |
| `nombre` | `xsd:string` |
| `Masaya_Calderas` | `wsINETER-DGGG:Masaya_CalderasType` |

### `wsINETER-DGGG:Masaya_Deslizamientos_Puntuales`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `x` | `xsd:decimal` |
| `y` | `xsd:decimal` |
| `altura` | `xsd:decimal` |
| `municipio` | `xsd:string` |
| `observacion` | `xsd:string` |
| `Masaya_Deslizamientos_Puntuales` | `wsINETER-DGGG:Masaya_Deslizamientos_PuntualesType` |

### `wsINETER-DGGG:Masaya_Escarpe`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `Masaya_Escarpe` | `wsINETER-DGGG:Masaya_EscarpeType` |

### `wsINETER-DGGG:Masaya_Inestabilidad_Laderas`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `shape_leng` | `xsd:decimal` |
| `shape_area` | `xsd:decimal` |
| `Masaya_Inestabilidad_Laderas` | `wsINETER-DGGG:Masaya_Inestabilidad_LaderasType` |

### `wsINETER-DGGG:Masaya_Isopaca`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `amenaza` | `xsd:string` |
| `Masaya_Isopaca` | `wsINETER-DGGG:Masaya_IsopacaType` |

### `wsINETER-DGGG:Masaya_Rutas_Evacuacion`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `fnode_` | `xsd:int` |
| `tnode_` | `xsd:int` |
| `lpoly_` | `xsd:int` |
| `rpoly_` | `xsd:int` |
| `length` | `xsd:decimal` |
| `trn_lin_` | `xsd:int` |
| `trn_lin_id` | `xsd:int` |
| `code` | `xsd:int` |
| `shape_leng` | `xsd:decimal` |
| `buffer` | `xsd:decimal` |
| `conectiv` | `xsd:string` |
| `Masaya_Rutas_Evacuacion` | `wsINETER-DGGG:Masaya_Rutas_EvacuacionType` |

### `wsINETER-DGGG:Masaya_Sitios_Concentracion`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `Masaya_Sitios_Concentracion` | `wsINETER-DGGG:Masaya_Sitios_ConcentracionType` |

### `wsINETER-DGGG:Mombacho_Debris_Avalancha`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `zona` | `xsd:string` |
| `shape_leng` | `xsd:decimal` |
| `shape_area` | `xsd:decimal` |
| `Mombacho_Debris_Avalancha` | `wsINETER-DGGG:Mombacho_Debris_AvalanchaType` |

### `wsINETER-DGGG:Mombacho_Lahar`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `zona` | `xsd:string` |
| `shape_leng` | `xsd:decimal` |
| `shape_area` | `xsd:decimal` |
| `Mombacho_Lahar` | `wsINETER-DGGG:Mombacho_LaharType` |

### `wsINETER-DGGG:Mombacho_Lahares`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `zona` | `xsd:string` |
| `shape_leng` | `xsd:decimal` |
| `shape_area` | `xsd:decimal` |
| `Mombacho_Lahares` | `wsINETER-DGGG:Mombacho_LaharesType` |

### `wsINETER-DGGG:Momotombo_Flujo`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `area_m2` | `xsd:decimal` |
| `area_km2` | `xsd:decimal` |
| `vol_m3` | `xsd:decimal` |
| `vol_km3` | `xsd:decimal` |
| `alt_pro_m` | `xsd:decimal` |
| `Momotombo_Flujo` | `wsINETER-DGGG:Momotombo_FlujoType` |

### `wsINETER-DGGG:Momotombo_Pluma`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `Momotombo_Pluma` | `wsINETER-DGGG:Momotombo_PlumaType` |

### `wsINETER-DGGG:Momotombo_Radios_Peligro`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `generico` | `xsd:string` |
| `n_propio` | `xsd:string` |
| `latitud` | `xsd:decimal` |
| `longitud` | `xsd:decimal` |
| `municipio` | `xsd:string` |
| `nomen` | `xsd:string` |
| `msnm` | `xsd:decimal` |
| `hab` | `xsd:decimal` |
| `lat_geo` | `xsd:decimal` |
| `long_geo` | `xsd:decimal` |
| `depto` | `xsd:string` |
| `buff_dist` | `xsd:decimal` |
| `shape_leng` | `xsd:decimal` |
| `shape_area` | `xsd:decimal` |
| `Momotombo_Radios_Peligro` | `wsINETER-DGGG:Momotombo_Radios_PeligroType` |

### `wsINETER-DGGG:Peligro_Volcanico_Alto`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `clase` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `peligro` | `xsd:string` |
| `Peligro_Volcanico_Alto` | `wsINETER-DGGG:Peligro_Volcanico_AltoType` |

### `wsINETER-DGGG:Peligro_Volcanico_Bajo`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `clase` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `peligro` | `xsd:string` |
| `Peligro_Volcanico_Bajo` | `wsINETER-DGGG:Peligro_Volcanico_BajoType` |

### `wsINETER-DGGG:Peligro_Volcanico_Medio`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `clase` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `peligro` | `xsd:string` |
| `Peligro_Volcanico_Medio` | `wsINETER-DGGG:Peligro_Volcanico_MedioType` |

### `wsINETER-DGGG:Placas_Tectonicas`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fid` | `xsd:string` |
| `sigla` | `xsd:string` |
| `nombre` | `xsd:string` |
| `Placas_Tectonicas` | `wsINETER-DGGG:Placas_TectonicasType` |

### `wsINETER-DGGG:Red_Estaciones_Sismicas`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `lat` | `xsd:double` |
| `long` | `xsd:double` |
| `altura` | `xsd:double` |
| `nombre` | `xsd:string` |
| `codigo` | `xsd:string` |
| `componente` | `xsd:string` |
| `pais` | `xsd:string` |
| `tipo_comp` | `xsd:string` |
| `funcion` | `xsd:double` |
| `f10` | `xsd:string` |
| `f11` | `xsd:string` |
| `f12` | `xsd:string` |
| `f13` | `xsd:string` |
| `f14` | `xsd:string` |
| `f15` | `xsd:string` |
| `f16` | `xsd:string` |
| `f17` | `xsd:string` |
| `f18` | `xsd:string` |
| `f19` | `xsd:string` |
| `f20` | `xsd:string` |
| `f21` | `xsd:string` |
| `f22` | `xsd:string` |
| `f23` | `xsd:string` |
| `f24` | `xsd:string` |
| `f25` | `xsd:string` |
| `f26` | `xsd:string` |
| `f27` | `xsd:string` |
| `f28` | `xsd:string` |
| `f29` | `xsd:string` |
| `f30` | `xsd:string` |
| `f31` | `xsd:string` |
| `Red_Estaciones_Sismicas` | `wsINETER-DGGG:Red_Estaciones_SismicasType` |

### `wsINETER-DGGG:Red_Hidrica_Shape`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiCurvePropertyType` |
| `cuenca` | `xsd:double` |
| `nombre_rio` | `xsd:string` |
| `categoria` | `xsd:string` |
| `tipo_rio` | `xsd:string` |
| `long_km` | `xsd:double` |
| `Red_Hidrica_Shape` | `wsINETER-DGGG:Red_Hidrica_ShapeType` |

### `wsINETER-DGGG:Red_Volcanica`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `tipo` | `xsd:string` |
| `nombre` | `xsd:string` |
| `lat_geo` | `xsd:decimal` |
| `long_geo` | `xsd:decimal` |
| `elevacion` | `xsd:decimal` |
| `elev_um` | `xsd:string` |
| `anio_erupcion` | `xsd:int` |
| `estado` | `xsd:boolean` |
| `ordenimpresion` | `xsd:short` |
| `Red_Volcanica` | `wsINETER-DGGG:Red_VolcanicaType` |

### `wsINETER-DGGG:Red_Volcanica_2024`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `tipo` | `xsd:string` |
| `nombre` | `xsd:string` |
| `lat_geo` | `xsd:decimal` |
| `long_geo` | `xsd:decimal` |
| `elevacion` | `xsd:decimal` |
| `elev_um` | `xsd:string` |
| `estado` | `xsd:boolean` |
| `anio_erupcion` | `xsd:string` |
| `Red_Volcanica_2024` | `wsINETER-DGGG:Red_Volcanica_2024Type` |

### `wsINETER-DGGG:redestacionessismicas-2021`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `lat` | `xsd:double` |
| `long` | `xsd:double` |
| `altura` | `xsd:double` |
| `nombre` | `xsd:string` |
| `codigo` | `xsd:string` |
| `componente` | `xsd:string` |
| `pais` | `xsd:string` |
| `tipo_comp` | `xsd:string` |
| `funcion` | `xsd:double` |
| `f10` | `xsd:string` |
| `f11` | `xsd:string` |
| `f12` | `xsd:string` |
| `f13` | `xsd:string` |
| `f14` | `xsd:string` |
| `f15` | `xsd:string` |
| `f16` | `xsd:string` |
| `f17` | `xsd:string` |
| `f18` | `xsd:string` |
| `f19` | `xsd:string` |
| `f20` | `xsd:string` |
| `f21` | `xsd:string` |
| `f22` | `xsd:string` |
| `f23` | `xsd:string` |
| `f24` | `xsd:string` |
| `f25` | `xsd:string` |
| `f26` | `xsd:string` |
| `f27` | `xsd:string` |
| `f28` | `xsd:string` |
| `f29` | `xsd:string` |
| `f30` | `xsd:string` |
| `f31` | `xsd:string` |
| `redestacionessismicas-2021` | `wsINETER-DGGG:redestacionessismicas-2021Type` |

### `wsINETER-DGGG:San_Cristobal_Lahar_dz`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `zona` | `xsd:string` |
| `shape_leng` | `xsd:decimal` |
| `shape_area` | `xsd:decimal` |
| `tipo` | `xsd:string` |
| `San_Cristobal_Lahar_dz` | `wsINETER-DGGG:San_Cristobal_Lahar_dzType` |

### `wsINETER-DGGG:San_Cristobal_Lahar_lz`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `zona` | `xsd:string` |
| `shape_leng` | `xsd:decimal` |
| `shape_area` | `xsd:decimal` |
| `tipo` | `xsd:string` |
| `San_Cristobal_Lahar_lz` | `wsINETER-DGGG:San_Cristobal_Lahar_lzType` |

### `wsINETER-DGGG:San_Cristobal_Lahar_plz`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `zona` | `xsd:string` |
| `shape_leng` | `xsd:decimal` |
| `shape_area` | `xsd:decimal` |
| `tipo` | `xsd:string` |
| `San_Cristobal_Lahar_plz` | `wsINETER-DGGG:San_Cristobal_Lahar_plzType` |

### `wsINETER-DGGG:San_Cristobal_Lahares`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `zona` | `xsd:string` |
| `shape_leng` | `xsd:decimal` |
| `shape_area` | `xsd:decimal` |
| `tipo` | `xsd:string` |
| `San_Cristobal_Lahares` | `wsINETER-DGGG:San_Cristobal_LaharesType` |

### `wsINETER-DGGG:sc_pl_bd_15022022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fecha` | `xsd:string` |
| `autor` | `xsd:string` |
| `institucio` | `xsd:string` |
| `forma_acce` | `xsd:string` |
| `localidad` | `xsd:string` |
| `comarca` | `xsd:string` |
| `municipio` | `xsd:string` |
| `departamen` | `xsd:string` |
| `tipo` | `xsd:string` |
| `subtipo` | `xsd:string` |
| `categoria` | `xsd:string` |
| `sec_estrat` | `xsd:string` |
| `litologia` | `xsd:string` |
| `afectacion` | `xsd:string` |
| `precipitac` | `xsd:string` |
| `pendiente` | `xsd:string` |
| `factor_con` | `xsd:string` |
| `factor_dec` | `xsd:string` |
| `longitud_m` | `xsd:decimal` |
| `ancho_m` | `xsd:decimal` |
| `profundida` | `xsd:decimal` |
| `superficie` | `xsd:decimal` |
| `volumen_m3` | `xsd:decimal` |
| `descripcio` | `xsd:string` |
| `uso_suelo` | `xsd:string` |
| `amenaza` | `xsd:string` |
| `codigo` | `xsd:string` |
| `x` | `xsd:decimal` |
| `y` | `xsd:decimal` |
| `tiposimbol` | `xsd:string` |
| `fid_2_1` | `xsd:decimal` |
| `cod_bacomu` | `xsd:decimal` |
| `id_bacomun` | `xsd:decimal` |
| `comarcas` | `xsd:string` |
| `n2` | `xsd:string` |
| `nom_barrio` | `xsd:string` |
| `cod_munic` | `xsd:decimal` |
| `cod_depto` | `xsd:decimal` |
| `code` | `xsd:string` |
| `cod_barrio` | `xsd:decimal` |
| `contador` | `xsd:decimal` |
| `id_barrio` | `xsd:string` |
| `año2` | `xsd:string` |
| `mes2` | `xsd:string` |
| `dia` | `xsd:string` |
| `contador1` | `xsd:string` |
| `distance` | `xsd:decimal` |
| `codinecmun` | `xsd:decimal` |
| `codinecdep` | `xsd:long` |
| `shape_leng` | `xsd:decimal` |
| `shape_le_1` | `xsd:decimal` |
| `areaaa` | `xsd:decimal` |
| `elaborado` | `xsd:string` |
| `shape_le_2` | `xsd:decimal` |
| `shape_area` | `xsd:decimal` |
| `sc_pl_bd_15022022` | `wsINETER-DGGG:sc_pl_bd_15022022Type` |

### `wsINETER-DGGG:sc_pl_mitch`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `autor` | `xsd:string` |
| `elaborado` | `xsd:string` |
| `idzonageologica` | `xsd:int` |
| `sc_pl_mitch` | `wsINETER-DGGG:sc_pl_mitchType` |

### `wsINETER-DGGG:sc_pt_15022022_pob2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `municipio` | `xsd:string` |
| `departamen` | `xsd:string` |
| `lugar` | `xsd:string` |
| `ubicaci__n` | `xsd:string` |
| `x` | `xsd:decimal` |
| `y` | `xsd:decimal` |
| `fuente` | `xsd:string` |
| `afectació` | `xsd:string` |
| `tipo` | `xsd:string` |
| `común` | `xsd:string` |
| `pob_2021` | `xsd:decimal` |
| `pob_2022` | `xsd:decimal` |
| `elaborado` | `xsd:string` |
| `amenaza` | `xsd:string` |
| `sitios_cri` | `xsd:string` |
| `sc_pt_15022022_pob2022` | `wsINETER-DGGG:sc_pt_15022022_pob2022Type` |

### `wsINETER-DGGG:sc_pt_bd_15022022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `object_id` | `xsd:long` |
| `fecha` | `xsd:string` |
| `x` | `xsd:long` |
| `y` | `xsd:long` |
| `institucio` | `xsd:string` |
| `acceso` | `xsd:string` |
| `localidad` | `xsd:string` |
| `comarca` | `xsd:string` |
| `municipio` | `xsd:string` |
| `departamen` | `xsd:string` |
| `tipo` | `xsd:string` |
| `subtipo` | `xsd:string` |
| `sec_estrat` | `xsd:string` |
| `litologia` | `xsd:string` |
| `afectacion` | `xsd:string` |
| `precipitac` | `xsd:string` |
| `pendiente` | `xsd:string` |
| `fact_condi` | `xsd:string` |
| `fact_desen` | `xsd:string` |
| `uso_de_sue` | `xsd:string` |
| `descripcio` | `xsd:string` |
| `autor` | `xsd:string` |
| `amenaza` | `xsd:string` |
| `sc_pt_bd_15022022` | `wsINETER-DGGG:sc_pt_bd_15022022Type` |

### `wsINETER-DGGG:sc_pt_devolli_2006`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `departamen` | `xsd:string` |
| `municipio` | `xsd:string` |
| `localidad` | `xsd:string` |
| `cerro` | `xsd:string` |
| `ladera` | `xsd:string` |
| `tipo_de_fe` | `xsd:string` |
| `este` | `xsd:long` |
| `norte` | `xsd:long` |
| `autor` | `xsd:string` |
| `elaborado` | `xsd:string` |
| `idzonageologica` | `xsd:int` |
| `sc_pt_devolli_2006` | `wsINETER-DGGG:sc_pt_devolli_2006Type` |

### `wsINETER-DGGG:simetcaelus`

| Campo | Tipo |
|---|---|
| `lluvia` | `xsd:double` |
| `nombreestacion` | `xsd:string` |
| `longitud` | `xsd:double` |
| `latitud` | `xsd:double` |
| `codigo` | `xsd:string` |
| `geom` | `gml:GeometryPropertyType` |
| `tipoestacion` | `xsd:string` |
| `simetcaelus` | `wsINETER-DGGG:simetcaelusType` |

### `wsINETER-DGGG:Sismografos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `descripcio` | `xsd:string` |
| `codigo` | `xsd:string` |
| `latitud` | `xsd:decimal` |
| `longitud` | `xsd:decimal` |
| `Sismografos` | `wsINETER-DGGG:SismografosType` |

### `wsINETER-DGGG:sismos`

| Campo | Tipo |
|---|---|
| `fechahorasismo` | `xsd:dateTime` |
| `latitud` | `xsd:float` |
| `longitud` | `xsd:float` |
| `profundidad` | `xsd:float` |
| `magnitud` | `xsd:float` |
| `tipomagnitud` | `xsd:string` |
| `ubicacion` | `xsd:string` |
| `geom` | `gml:GeometryPropertyType` |
| `es_ultimo` | `xsd:boolean` |
| `sismos` | `wsINETER-DGGG:sismosType` |

### `wsINETER-DGGG:sismos_prueba`

| Campo | Tipo |
|---|---|
| `fechahorasismo` | `xsd:dateTime` |
| `latitud` | `xsd:float` |
| `longitud` | `xsd:float` |
| `profundidad` | `xsd:float` |
| `magnitud` | `xsd:float` |
| `tipomagnitud` | `xsd:string` |
| `ubicacion` | `xsd:string` |
| `geom` | `gml:GeometryPropertyType` |
| `sismos_prueba` | `wsINETER-DGGG:sismos_pruebaType` |

### `wsINETER-DGGG:Sismos_Ultima_12Hora`

| Campo | Tipo |
|---|---|
| `fechahorasismo` | `xsd:dateTime` |
| `latitud` | `xsd:float` |
| `longitud` | `xsd:float` |
| `profundidad` | `xsd:float` |
| `magnitud` | `xsd:float` |
| `tipomagnitud` | `xsd:string` |
| `ubicacion` | `xsd:string` |
| `geom` | `gml:GeometryPropertyType` |
| `Sismos_Ultima_12Hora` | `wsINETER-DGGG:Sismos_Ultima_12HoraType` |

### `wsINETER-DGGG:Sismos_Ultima_24Hora`

| Campo | Tipo |
|---|---|
| `fechahorasismo` | `xsd:dateTime` |
| `latitud` | `xsd:float` |
| `longitud` | `xsd:float` |
| `profundidad` | `xsd:float` |
| `magnitud` | `xsd:float` |
| `tipomagnitud` | `xsd:string` |
| `ubicacion` | `xsd:string` |
| `geom` | `gml:GeometryPropertyType` |
| `Sismos_Ultima_24Hora` | `wsINETER-DGGG:Sismos_Ultima_24HoraType` |

### `wsINETER-DGGG:Sismos_Ultima_48Hora`

| Campo | Tipo |
|---|---|
| `fechahorasismo` | `xsd:dateTime` |
| `latitud` | `xsd:float` |
| `longitud` | `xsd:float` |
| `profundidad` | `xsd:float` |
| `magnitud` | `xsd:float` |
| `tipomagnitud` | `xsd:string` |
| `ubicacion` | `xsd:string` |
| `geom` | `gml:GeometryPropertyType` |
| `Sismos_Ultima_48Hora` | `wsINETER-DGGG:Sismos_Ultima_48HoraType` |

### `wsINETER-DGGG:Sismos_Ultima_72Hora`

| Campo | Tipo |
|---|---|
| `fechahorasismo` | `xsd:dateTime` |
| `latitud` | `xsd:float` |
| `longitud` | `xsd:float` |
| `profundidad` | `xsd:float` |
| `magnitud` | `xsd:float` |
| `tipomagnitud` | `xsd:string` |
| `ubicacion` | `xsd:string` |
| `geom` | `gml:GeometryPropertyType` |
| `Sismos_Ultima_72Hora` | `wsINETER-DGGG:Sismos_Ultima_72HoraType` |

### `wsINETER-DGGG:Sismos_Ultimas12horas_ot`

| Campo | Tipo |
|---|---|
| `fechahorasismo` | `xsd:string` |
| `fechacreacion` | `xsd:string` |
| `fechamodificacion` | `xsd:string` |
| `latitud` | `xsd:float` |
| `longitud` | `xsd:float` |
| `profundidad` | `xsd:float` |
| `magnitud` | `xsd:string` |
| `tipomagnitud` | `xsd:string` |
| `ubicacion` | `xsd:string` |
| `geom` | `gml:GeometryPropertyType` |
| `Sismos_Ultimas12horas_ot` | `wsINETER-DGGG:Sismos_Ultimas12horas_otType` |

### `wsINETER-DGGG:Sismos_Ultimos7dias_ot`

| Campo | Tipo |
|---|---|
| `fechahorasismo` | `xsd:dateTime` |
| `latitud` | `xsd:float` |
| `longitud` | `xsd:float` |
| `profundidad` | `xsd:float` |
| `magnitud` | `xsd:string` |
| `tipomagnitud` | `xsd:string` |
| `ubicacion` | `xsd:string` |
| `geom` | `gml:GeometryPropertyType` |
| `Sismos_Ultimos7dias_ot` | `wsINETER-DGGG:Sismos_Ultimos7dias_otType` |

### `wsINETER-DGGG:Sismos_Ultimos_7Dias`

| Campo | Tipo |
|---|---|
| `fechahorasismo` | `xsd:dateTime` |
| `latitud` | `xsd:float` |
| `longitud` | `xsd:float` |
| `profundidad` | `xsd:float` |
| `magnitud` | `xsd:float` |
| `tipomagnitud` | `xsd:string` |
| `ubicacion` | `xsd:string` |
| `geom` | `gml:GeometryPropertyType` |
| `Sismos_Ultimos_7Dias` | `wsINETER-DGGG:Sismos_Ultimos_7DiasType` |

### `wsINETER-DGGG:sismosultimas12horasprueba`

| Campo | Tipo |
|---|---|
| `fechahorasismo` | `xsd:string` |
| `fechacreacion` | `xsd:string` |
| `fechamodificacion` | `xsd:string` |
| `latitud` | `xsd:float` |
| `longitud` | `xsd:float` |
| `profundidad` | `xsd:float` |
| `magnitud` | `xsd:string` |
| `tipomagnitud` | `xsd:string` |
| `ubicacion` | `xsd:string` |
| `geom` | `gml:GeometryPropertyType` |
| `sismosultimas12horasprueba` | `wsINETER-DGGG:sismosultimas12horaspruebaType` |

### `wsINETER-DGGG:sismosultimos7dias`

| Campo | Tipo |
|---|---|
| `fechahorasismo` | `xsd:dateTime` |
| `latitud` | `xsd:float` |
| `longitud` | `xsd:float` |
| `profundidad` | `xsd:float` |
| `magnitud` | `xsd:float` |
| `tipomagnitud` | `xsd:string` |
| `ubicacion` | `xsd:string` |
| `geom` | `gml:GeometryPropertyType` |
| `sismosultimos7dias` | `wsINETER-DGGG:sismosultimos7diasType` |

### `wsINETER-DGGG:sismosultimos7dias2023`

| Campo | Tipo |
|---|---|
| `fechahorasismo` | `xsd:dateTime` |
| `latitud` | `xsd:float` |
| `longitud` | `xsd:float` |
| `profundidad` | `xsd:float` |
| `magnitud` | `xsd:float` |
| `tipomagnitud` | `xsd:string` |
| `ubicacion` | `xsd:string` |
| `geom` | `gml:GeometryPropertyType` |
| `sismosultimos7dias2023` | `wsINETER-DGGG:sismosultimos7dias2023Type` |

### `wsINETER-DGGG:sitiocritico_asentamiento`

| Campo | Tipo |
|---|---|
| `idah` | `xsd:int` |
| `idsc` | `xsd:long` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `departamento` | `xsd:string` |
| `municipio` | `xsd:string` |
| `nombre` | `xsd:string` |
| `tiporevestimiento` | `xsd:string` |
| `cercania` | `xsd:string` |
| `cantidadpobla` | `xsd:double` |
| `cantidadvivienda` | `xsd:double` |
| `origen` | `xsd:string` |
| `nivelalerta` | `xsd:string` |
| `lluvia24` | `xsd:double` |
| `lluvia72` | `xsd:double` |
| `sitiocritico_asentamiento` | `wsINETER-DGGG:sitiocritico_asentamientoType` |

### `wsINETER-DGGG:Sitios`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `id` | `xsd:int` |
| `nombresitio` | `xsd:string` |
| `tipo` | `xsd:string` |
| `equipo` | `xsd:string` |
| `latitud` | `xsd:double` |
| `longitud` | `xsd:double` |
| `requisitos` | `xsd:string` |
| `Sitios` | `wsINETER-DGGG:SitiosType` |

### `wsINETER-DGGG:SitiosVisual`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `id` | `xsd:int` |
| `nombresitio` | `xsd:string` |
| `tipo` | `xsd:string` |
| `equipo` | `xsd:string` |
| `latitud` | `xsd:double` |
| `longitud` | `xsd:double` |
| `requisitos` | `xsd:string` |
| `SitiosVisual` | `wsINETER-DGGG:SitiosVisualType` |

### `wsINETER-DGGG:Telica_Caida_Material`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `leyenda` | `xsd:string` |
| `Telica_Caida_Material` | `wsINETER-DGGG:Telica_Caida_MaterialType` |

### `wsINETER-DGGG:Telica_Caidam_Escoriafina`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `leyenda` | `xsd:string` |
| `Telica_Caidam_Escoriafina` | `wsINETER-DGGG:Telica_Caidam_EscoriafinaType` |

### `wsINETER-DGGG:Telica_Caidam_Escoriasup`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `leyenda` | `xsd:string` |
| `Telica_Caidam_Escoriasup` | `wsINETER-DGGG:Telica_Caidam_EscoriasupType` |

### `wsINETER-DGGG:Telica_Escarpes`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `Telica_Escarpes` | `wsINETER-DGGG:Telica_EscarpesType` |

### `wsINETER-DGGG:v_amenazado_saturacionsuelo`

> [!warning] Schema pendente; validar antes de uso.

### `wsINETER-DGGG:v_lluvia_24horas_simet_caelus`

| Campo | Tipo |
|---|---|
| `id` | `xsd:long` |
| `lluvia` | `xsd:double` |
| `nombreestacion` | `xsd:string` |
| `longitud` | `xsd:double` |
| `latitud` | `xsd:double` |
| `codigo` | `xsd:string` |
| `geom` | `gml:GeometryPropertyType` |
| `tipoestacion` | `xsd:string` |
| `v_lluvia_24horas_simet_caelus` | `wsINETER-DGGG:v_lluvia_24horas_simet_caelusType` |

### `wsINETER-DGGG:v_Sismosultimos7dias`

| Campo | Tipo |
|---|---|
| `fechahorasismo` | `xsd:dateTime` |
| `latitud` | `xsd:float` |
| `longitud` | `xsd:float` |
| `profundidad` | `xsd:float` |
| `magnitud` | `xsd:float` |
| `tipomagnitud` | `xsd:string` |
| `ubicacion` | `xsd:string` |
| `geom` | `gml:GeometryPropertyType` |
| `v_Sismosultimos7dias` | `wsINETER-DGGG:v_Sismosultimos7diasType` |

### `wsINETER-DGMT:Acumulados_lluvia_15_16`

| Campo | Tipo |
|---|---|
| `zona_climatica` | `xsd:string` |
| `order2020` | `xsd:int` |
| `departamento` | `xsd:string` |
| `municipio` | `xsd:string` |
| `estacion` | `xsd:string` |
| `longitud` | `xsd:double` |
| `latitud` | `xsd:double` |
| `altitud` | `xsd:double` |
| `acum_15_16` | `xsd:float` |
| `geom` | `gml:GeometryPropertyType` |
| `Acumulados_lluvia_15_16` | `wsINETER-DGMT:Acumulados_lluvia_15_16Type` |

### `wsINETER-DGMT:Acumulados_lluvia_16_17`

| Campo | Tipo |
|---|---|
| `zona_climatica` | `xsd:string` |
| `order2020` | `xsd:int` |
| `departamento` | `xsd:string` |
| `municipio` | `xsd:string` |
| `estacion` | `xsd:string` |
| `longitud` | `xsd:double` |
| `latitud` | `xsd:double` |
| `altitud` | `xsd:double` |
| `acum_16_17` | `xsd:float` |
| `geom` | `gml:GeometryPropertyType` |
| `Acumulados_lluvia_16_17` | `wsINETER-DGMT:Acumulados_lluvia_16_17Type` |

### `wsINETER-DGMT:Acumulados_lluvia_17_18`

| Campo | Tipo |
|---|---|
| `zona_climatica` | `xsd:string` |
| `order2020` | `xsd:int` |
| `departamento` | `xsd:string` |
| `municipio` | `xsd:string` |
| `estacion` | `xsd:string` |
| `longitud` | `xsd:double` |
| `latitud` | `xsd:double` |
| `altitud` | `xsd:double` |
| `acum_17_18` | `xsd:float` |
| `geom` | `gml:GeometryPropertyType` |
| `Acumulados_lluvia_17_18` | `wsINETER-DGMT:Acumulados_lluvia_17_18Type` |

### `wsINETER-DGMT:Acumulados_lluvia_18_19`

> [!warning] Schema pendente; validar antes de uso.

### `wsINETER-DGMT:Amenaza_Sequia`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `intervalo` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_le_1` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `Amenaza_Sequia` | `wsINETER-DGMT:Amenaza_SequiaType` |

### `wsINETER-DGMT:amenaza_sequia_abril_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `amenaza` | `xsd:string` |
| `observ` | `xsd:string` |
| `amenaza_sequia_abril_2022` | `wsINETER-DGMT:amenaza_sequia_abril_2022Type` |

### `wsINETER-DGMT:amenaza_sequia_agosto_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `amenaza` | `xsd:string` |
| `amenaza_sequia_agosto_2022` | `wsINETER-DGMT:amenaza_sequia_agosto_2022Type` |

### `wsINETER-DGMT:amenaza_sequia_anual_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `intervalo` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_le_1` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `amenaza_sequia_anual_2022` | `wsINETER-DGMT:amenaza_sequia_anual_2022Type` |

### `wsINETER-DGMT:amenaza_sequia_apante_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `amenaza` | `xsd:string` |
| `observ` | `xsd:string` |
| `amenaza_sequia_apante_2022` | `wsINETER-DGMT:amenaza_sequia_apante_2022Type` |

### `wsINETER-DGMT:amenaza_sequia_aso_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `amenaza` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `amenaza_sequia_aso_2022` | `wsINETER-DGMT:amenaza_sequia_aso_2022Type` |

### `wsINETER-DGMT:amenaza_sequia_diciembre_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `amenaza` | `xsd:string` |
| `observ` | `xsd:string` |
| `amenaza_sequia_diciembre_2022` | `wsINETER-DGMT:amenaza_sequia_diciembre_2022Type` |

### `wsINETER-DGMT:amenaza_sequia_ene_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `amenaza` | `xsd:string` |
| `observ` | `xsd:string` |
| `amenaza_sequia_ene_2022` | `wsINETER-DGMT:amenaza_sequia_ene_2022Type` |

### `wsINETER-DGMT:amenaza_sequia_feb_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `amen` | `xsd:string` |
| `observ` | `xsd:string` |
| `amenaza_sequia_feb_2022` | `wsINETER-DGMT:amenaza_sequia_feb_2022Type` |

### `wsINETER-DGMT:amenaza_sequia_julio_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `amen_julio` | `xsd:string` |
| `observ` | `xsd:string` |
| `amenaza_sequia_julio_2022` | `wsINETER-DGMT:amenaza_sequia_julio_2022Type` |

### `wsINETER-DGMT:amenaza_sequia_junio_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `jun` | `xsd:string` |
| `observ` | `xsd:string` |
| `amenaza_sequia_junio_2022` | `wsINETER-DGMT:amenaza_sequia_junio_2022Type` |

### `wsINETER-DGMT:amenaza_sequia_marzo_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `marzo` | `xsd:string` |
| `observ` | `xsd:string` |
| `amenaza_sequia_marzo_2022` | `wsINETER-DGMT:amenaza_sequia_marzo_2022Type` |

### `wsINETER-DGMT:amenaza_sequia_mayo_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `amenazas` | `xsd:string` |
| `observ` | `xsd:string` |
| `amenaza_sequia_mayo_2022` | `wsINETER-DGMT:amenaza_sequia_mayo_2022Type` |

### `wsINETER-DGMT:amenaza_sequia_mjj_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `amenaza` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `amenaza_sequia_mjj_2022` | `wsINETER-DGMT:amenaza_sequia_mjj_2022Type` |

### `wsINETER-DGMT:amenaza_sequia_mjjaso_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `amenaza` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `amenaza_sequia_mjjaso_2022` | `wsINETER-DGMT:amenaza_sequia_mjjaso_2022Type` |

### `wsINETER-DGMT:amenaza_sequia_noviembre_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `amenaza` | `xsd:string` |
| `observ` | `xsd:string` |
| `amenaza_sequia_noviembre_2022` | `wsINETER-DGMT:amenaza_sequia_noviembre_2022Type` |

### `wsINETER-DGMT:amenaza_sequia_octubre_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `amenaza` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `amenaza_sequia_octubre_2022` | `wsINETER-DGMT:amenaza_sequia_octubre_2022Type` |

### `wsINETER-DGMT:amenaza_sequia_septiembre_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `amenaza` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `amenaza_sequia_septiembre_2022` | `wsINETER-DGMT:amenaza_sequia_septiembre_2022Type` |

### `wsINETER-DGMT:Anual_Calido`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `prt2` | `xsd:string` |
| `prt` | `xsd:int` |
| `Anual_Calido` | `wsINETER-DGMT:Anual_CalidoType` |

### `wsINETER-DGMT:Anual_Confort`

> [!warning] Schema pendente; validar antes de uso.

### `wsINETER-DGMT:Anual_ETP`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `prt2` | `xsd:string` |
| `prt` | `xsd:int` |
| `Anual_ETP` | `wsINETER-DGMT:Anual_ETPType` |

### `wsINETER-DGMT:Anual_Frio`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `prt2` | `xsd:string` |
| `prt` | `xsd:int` |
| `Anual_Frio` | `wsINETER-DGMT:Anual_FrioType` |

### `wsINETER-DGMT:Catalogo_Estaciones_Caelus_2022`

| Campo | Tipo |
|---|---|
| `id` | `xsd:long` |
| `idestacionsensor` | `xsd:int` |
| `idsensor` | `xsd:int` |
| `codigoestacion` | `xsd:string` |
| `nombreestacion` | `xsd:string` |
| `nombreestacion2` | `xsd:string` |
| `longitud` | `xsd:float` |
| `latitud` | `xsd:float` |
| `point` | `gml:GeometryPropertyType` |
| `propietario` | `xsd:string` |
| `ultimatransmision` | `xsd:dateTime` |
| `Catalogo_Estaciones_Caelus_2022` | `wsINETER-DGMT:Catalogo_Estaciones_Caelus_2022Type` |

### `wsINETER-DGMT:Catalogo_Estaciones_Caelus_Activas_2022`

| Campo | Tipo |
|---|---|
| `id` | `xsd:long` |
| `geom` | `gml:GeometryPropertyType` |
| `codigoestacion` | `xsd:string` |
| `nombreestacion` | `xsd:string` |
| `longitud` | `xsd:float` |
| `latitud` | `xsd:float` |
| `propietario` | `xsd:string` |
| `ultimatransmision` | `xsd:dateTime` |
| `Catalogo_Estaciones_Caelus_Activas_2022` | `wsINETER-DGMT:Catalogo_Estaciones_Caelus_Activas_2022Type` |

### `wsINETER-DGMT:cp_vientos`

| Campo | Tipo |
|---|---|
| `nombreestacion` | `xsd:string` |
| `longitud` | `xsd:float` |
| `latitud` | `xsd:float` |
| `geom` | `gml:GeometryPropertyType` |
| `fecha` | `xsd:dateTime` |
| `velocidad` | `xsd:double` |
| `valordireccion` | `xsd:double` |
| `direccion` | `xsd:string` |
| `cp_vientos` | `wsINETER-DGMT:cp_vientosType` |

### `wsINETER-DGMT:Dipilto_Mt_Sequia`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nivel7` | `xsd:int` |
| `a1` | `xsd:double` |
| `tipoamenza` | `xsd:string` |
| `perimetro` | `xsd:double` |
| `area_ha` | `xsd:double` |
| `area_km` | `xsd:double` |
| `Dipilto_Mt_Sequia` | `wsINETER-DGMT:Dipilto_Mt_SequiaType` |

### `wsINETER-DGMT:Enso_Anualcalido_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `prt` | `xsd:string` |
| `Enso_Anualcalido_2022` | `wsINETER-DGMT:Enso_Anualcalido_2022Type` |

### `wsINETER-DGMT:Enso_Frioanual_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `prt` | `xsd:string` |
| `Enso_Frioanual_2022` | `wsINETER-DGMT:Enso_Frioanual_2022Type` |

### `wsINETER-DGMT:Enso_prt_mfrec_calido`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `prt` | `xsd:string` |
| `Enso_prt_mfrec_calido` | `wsINETER-DGMT:Enso_prt_mfrec_calidoType` |

### `wsINETER-DGMT:Enso_prt_mfrec_frio`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `prt` | `xsd:string` |
| `Enso_prt_mfrec_frio` | `wsINETER-DGMT:Enso_prt_mfrec_frioType` |

### `wsINETER-DGMT:Estaciones_Meteologicas`

| Campo | Tipo |
|---|---|
| `nombrebd` | `xsd:string` |
| `nombre` | `xsd:string` |
| `longitud` | `xsd:float` |
| `latitud` | `xsd:float` |
| `esp` | `gml:GeometryPropertyType` |
| `codigo` | `xsd:string` |
| `idpropietario` | `xsd:int` |
| `Estaciones_Meteologicas` | `wsINETER-DGMT:Estaciones_MeteologicasType` |

### `wsINETER-DGMT:Estaciones_Meteorologicas`

| Campo | Tipo |
|---|---|
| `nombrebd` | `xsd:string` |
| `nombre` | `xsd:string` |
| `longitud` | `xsd:float` |
| `latitud` | `xsd:float` |
| `esp` | `gml:GeometryPropertyType` |
| `codigo` | `xsd:string` |
| `idpropietario` | `xsd:int` |
| `Estaciones_Meteorologicas` | `wsINETER-DGMT:Estaciones_MeteorologicasType` |

### `wsINETER-DGMT:Estaciones_Principales`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `nombreesta` | `xsd:string` |
| `codigo` | `xsd:long` |
| `latitud` | `xsd:decimal` |
| `longitud` | `xsd:decimal` |
| `direccion` | `xsd:string` |
| `responsabl` | `xsd:string` |
| `telefono` | `xsd:string` |
| `celular1` | `xsd:long` |
| `celular2` | `xsd:long` |
| `Estaciones_Principales` | `wsINETER-DGMT:Estaciones_PrincipalesType` |

### `wsINETER-DGMT:Estaciones_Principales_ve`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `nombreesta` | `xsd:string` |
| `codigo` | `xsd:long` |
| `latitud` | `xsd:decimal` |
| `longitud` | `xsd:decimal` |
| `direccion` | `xsd:string` |
| `responsabl` | `xsd:string` |
| `telefono` | `xsd:string` |
| `celular1` | `xsd:long` |
| `celular2` | `xsd:long` |
| `Estaciones_Principales_ve` | `wsINETER-DGMT:Estaciones_Principales_veType` |

### `wsINETER-DGMT:Estaciones_Telemetricas`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `nombrebd` | `xsd:string` |
| `codigo` | `xsd:string` |
| `nombre` | `xsd:string` |
| `latitud` | `xsd:decimal` |
| `longitud` | `xsd:decimal` |
| `Estaciones_Telemetricas` | `wsINETER-DGMT:Estaciones_TelemetricasType` |

### `wsINETER-DGMT:Evotrans_Anual_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `prt2` | `xsd:string` |
| `prt` | `xsd:int` |
| `Evotrans_Anual_2022` | `wsINETER-DGMT:Evotrans_Anual_2022Type` |

### `wsINETER-DGMT:hr_abr_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `total2` | `xsd:string` |
| `total` | `xsd:int` |
| `hr_abr_2022` | `wsINETER-DGMT:hr_abr_2022Type` |

### `wsINETER-DGMT:hr_ago_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `total2` | `xsd:string` |
| `total` | `xsd:int` |
| `hr_ago_2022` | `wsINETER-DGMT:hr_ago_2022Type` |

### `wsINETER-DGMT:hr_dic_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `total2` | `xsd:string` |
| `total` | `xsd:int` |
| `hr_dic_2022` | `wsINETER-DGMT:hr_dic_2022Type` |

### `wsINETER-DGMT:hr_ene_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `total2` | `xsd:string` |
| `total` | `xsd:int` |
| `hr_ene_2022` | `wsINETER-DGMT:hr_ene_2022Type` |

### `wsINETER-DGMT:hr_feb_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `total2` | `xsd:string` |
| `total` | `xsd:int` |
| `hr_feb_2022` | `wsINETER-DGMT:hr_feb_2022Type` |

### `wsINETER-DGMT:hr_jul_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `total2` | `xsd:string` |
| `total` | `xsd:int` |
| `hr_jul_2022` | `wsINETER-DGMT:hr_jul_2022Type` |

### `wsINETER-DGMT:hr_jun_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `total2` | `xsd:string` |
| `total` | `xsd:int` |
| `hr_jun_2022` | `wsINETER-DGMT:hr_jun_2022Type` |

### `wsINETER-DGMT:hr_koppen_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `koppen` | `xsd:string` |
| `Clima` | `xsd:string` |
| `hr_koppen_2022` | `wsINETER-DGMT:hr_koppen_2022Type` |

### `wsINETER-DGMT:hr_mar_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `total2` | `xsd:string` |
| `total` | `xsd:int` |
| `hr_mar_2022` | `wsINETER-DGMT:hr_mar_2022Type` |

### `wsINETER-DGMT:hr_may_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `total2` | `xsd:string` |
| `total` | `xsd:int` |
| `hr_may_2022` | `wsINETER-DGMT:hr_may_2022Type` |

### `wsINETER-DGMT:hr_oct_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `total2` | `xsd:string` |
| `total` | `xsd:int` |
| `hr_oct_2022` | `wsINETER-DGMT:hr_oct_2022Type` |

### `wsINETER-DGMT:hr_sep_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `total2` | `xsd:string` |
| `total` | `xsd:int` |
| `hr_sep_2022` | `wsINETER-DGMT:hr_sep_2022Type` |

### `wsINETER-DGMT:Humedad_Relativa_Anual`

> [!warning] Schema pendente; validar antes de uso.

### `wsINETER-DGMT:Huracanes_ot`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `nombre` | `xsd:string` |
| `categoria` | `xsd:string` |
| `vientomaxknots` | `xsd:string` |
| `vientomaxmph` | `xsd:string` |
| `oceano` | `xsd:string` |
| `id` | `xsd:int` |
| `Huracanes_ot` | `wsINETER-DGMT:Huracanes_otType` |

### `wsINETER-DGMT:hurricane_Iota_lin`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `stormnum` | `xsd:decimal` |
| `stormtype` | `xsd:string` |
| `ss` | `xsd:decimal` |
| `hurricane_Iota_lin` | `wsINETER-DGMT:hurricane_Iota_linType` |

### `wsINETER-DGMT:hurricane_Iota_pts`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `stormname` | `xsd:string` |
| `dtg` | `xsd:decimal` |
| `year` | `xsd:decimal` |
| `month` | `xsd:string` |
| `day` | `xsd:decimal` |
| `hhmm` | `xsd:string` |
| `mslp` | `xsd:decimal` |
| `basin` | `xsd:string` |
| `stormnum` | `xsd:decimal` |
| `stormtype` | `xsd:string` |
| `intensity` | `xsd:decimal` |
| `ss` | `xsd:decimal` |
| `lat` | `xsd:decimal` |
| `lon` | `xsd:decimal` |
| `hurricane_Iota_pts` | `wsINETER-DGMT:hurricane_Iota_ptsType` |

### `wsINETER-DGMT:hurricane_Iota_windw`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `radii` | `xsd:decimal` |
| `stormid` | `xsd:string` |
| `basin` | `xsd:string` |
| `stormnum` | `xsd:decimal` |
| `advnum` | `xsd:string` |
| `startdtg` | `xsd:string` |
| `enddtg` | `xsd:string` |
| `hurricane_Iota_windw` | `wsINETER-DGMT:hurricane_Iota_windwType` |

### `wsINETER-DGMT:iconfort_abr_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `c_abrl` | `xsd:string` |
| `clasif` | `xsd:string` |
| `iconfort_abr_2022` | `wsINETER-DGMT:iconfort_abr_2022Type` |

### `wsINETER-DGMT:iconfort_ago_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `pla_ago` | `xsd:string` |
| `clasif` | `xsd:string` |
| `iconfort_ago_2022` | `wsINETER-DGMT:iconfort_ago_2022Type` |

### `wsINETER-DGMT:iconfort_dic_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `cclim_dic` | `xsd:string` |
| `clasif` | `xsd:string` |
| `iconfort_dic_2022` | `wsINETER-DGMT:iconfort_dic_2022Type` |

### `wsINETER-DGMT:iconfort_ene_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `confortcli` | `xsd:string` |
| `clasif` | `xsd:string` |
| `iconfort_ene_2022` | `wsINETER-DGMT:iconfort_ene_2022Type` |

### `wsINETER-DGMT:iconfort_feb_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `terjung` | `xsd:string` |
| `clasif` | `xsd:string` |
| `iconfort_feb_2022` | `wsINETER-DGMT:iconfort_feb_2022Type` |

### `wsINETER-DGMT:iconfort_jul_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `cclim_jul` | `xsd:string` |
| `clasif` | `xsd:string` |
| `iconfort_jul_2022` | `wsINETER-DGMT:iconfort_jul_2022Type` |

### `wsINETER-DGMT:iconfort_jun_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `cclimat_ju` | `xsd:string` |
| `clasif` | `xsd:string` |
| `iconfort_jun_2022` | `wsINETER-DGMT:iconfort_jun_2022Type` |

### `wsINETER-DGMT:iconfort_mar_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `con_marzo` | `xsd:string` |
| `clasif` | `xsd:string` |
| `iconfort_mar_2022` | `wsINETER-DGMT:iconfort_mar_2022Type` |

### `wsINETER-DGMT:iconfort_may_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `cclimat` | `xsd:string` |
| `clasif` | `xsd:string` |
| `iconfort_may_2022` | `wsINETER-DGMT:iconfort_may_2022Type` |

### `wsINETER-DGMT:iconfort_nov_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `cclim_nov` | `xsd:string` |
| `clasif` | `xsd:string` |
| `iconfort_nov_2022` | `wsINETER-DGMT:iconfort_nov_2022Type` |

### `wsINETER-DGMT:iconfort_oct_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `pla_ago` | `xsd:string` |
| `clasif` | `xsd:string` |
| `iconfort_oct_2022` | `wsINETER-DGMT:iconfort_oct_2022Type` |

### `wsINETER-DGMT:iconfort_sep_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `pla_ago` | `xsd:string` |
| `clasif` | `xsd:string` |
| `iconfort_sep_2022` | `wsINETER-DGMT:iconfort_sep_2022Type` |

### `wsINETER-DGMT:iconfortclim_anual_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `confortcli` | `xsd:string` |
| `clasif` | `xsd:string` |
| `iconfortclim_anual_2022` | `wsINETER-DGMT:iconfortclim_anual_2022Type` |

### `wsINETER-DGMT:Koppen_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `id` | `xsd:int` |
| `koppen` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `Koppen_2022` | `wsINETER-DGMT:Koppen_2022Type` |

### `wsINETER-DGMT:Koppen_2022-1`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `koppen` | `xsd:string` |
| `Koppen_2022-1` | `wsINETER-DGMT:Koppen_2022-1Type` |

### `wsINETER-DGMT:Lluvia_12h_managua`

| Campo | Tipo |
|---|---|
| `codigoestacion` | `xsd:int` |
| `nombreestacion` | `xsd:string` |
| `longitud` | `xsd:float` |
| `latitud` | `xsd:float` |
| `altitud` | `xsd:float` |
| `codigo` | `xsd:string` |
| `nombresensor` | `xsd:string` |
| `point` | `gml:GeometryPropertyType` |
| `lluvia` | `xsd:double` |
| `Lluvia_12h_managua` | `wsINETER-DGMT:Lluvia_12h_managuaType` |

### `wsINETER-DGMT:Lluvia_12hr`

| Campo | Tipo |
|---|---|
| `lluvia` | `xsd:double` |
| `nombreestacion` | `xsd:string` |
| `longitud` | `xsd:float` |
| `latitud` | `xsd:float` |
| `altitud` | `xsd:float` |
| `codigo` | `xsd:string` |
| `nombresensor` | `xsd:string` |
| `point` | `gml:GeometryPropertyType` |
| `Lluvia_12hr` | `wsINETER-DGMT:Lluvia_12hrType` |

### `wsINETER-DGMT:Lluvia_12hrs`

| Campo | Tipo |
|---|---|
| `lluvia` | `xsd:double` |
| `nombreestacion` | `xsd:string` |
| `longitud` | `xsd:float` |
| `latitud` | `xsd:float` |
| `altitud` | `xsd:float` |
| `codigo` | `xsd:string` |
| `nombresensor` | `xsd:string` |
| `point` | `gml:GeometryPropertyType` |
| `Lluvia_12hrs` | `wsINETER-DGMT:Lluvia_12hrsType` |

### `wsINETER-DGMT:Lluvia_24_Horas`

| Campo | Tipo |
|---|---|
| `lluvia` | `xsd:double` |
| `nombreestacion` | `xsd:string` |
| `longitud` | `xsd:double` |
| `latitud` | `xsd:double` |
| `codigo` | `xsd:int` |
| `point` | `gml:GeometryPropertyType` |
| `tipoestacion` | `xsd:string` |
| `Lluvia_24_Horas` | `wsINETER-DGMT:Lluvia_24_HorasType` |

### `wsINETER-DGMT:lluvia_24h-new`

| Campo | Tipo |
|---|---|
| `lluvia` | `xsd:double` |
| `nombreestacion` | `xsd:string` |
| `longitud` | `xsd:float` |
| `latitud` | `xsd:float` |
| `altitud` | `xsd:float` |
| `codigo` | `xsd:string` |
| `nombresensor` | `xsd:string` |
| `point` | `gml:GeometryPropertyType` |
| `lluvia_24h-new` | `wsINETER-DGMT:lluvia_24h-newType` |

### `wsINETER-DGMT:Lluvia_24h_managua`

| Campo | Tipo |
|---|---|
| `codigoestacion` | `xsd:int` |
| `nombreestacion` | `xsd:string` |
| `longitud` | `xsd:float` |
| `latitud` | `xsd:float` |
| `altitud` | `xsd:float` |
| `codigo` | `xsd:string` |
| `nombresensor` | `xsd:string` |
| `point` | `gml:GeometryPropertyType` |
| `lluvia` | `xsd:double` |
| `Lluvia_24h_managua` | `wsINETER-DGMT:Lluvia_24h_managuaType` |

### `wsINETER-DGMT:lluvia_24h_test`

| Campo | Tipo |
|---|---|
| `lluvia` | `xsd:double` |
| `nombreestacion` | `xsd:string` |
| `longitud` | `xsd:float` |
| `latitud` | `xsd:float` |
| `altitud` | `xsd:float` |
| `codigo` | `xsd:string` |
| `nombresensor` | `xsd:string` |
| `point` | `gml:GeometryPropertyType` |
| `lluvia_24h_test` | `wsINETER-DGMT:lluvia_24h_testType` |

### `wsINETER-DGMT:Lluvia_24hr`

| Campo | Tipo |
|---|---|
| `lluvia` | `xsd:double` |
| `nombreestacion` | `xsd:string` |
| `longitud` | `xsd:float` |
| `latitud` | `xsd:float` |
| `altitud` | `xsd:float` |
| `codigo` | `xsd:string` |
| `nombresensor` | `xsd:string` |
| `point` | `gml:GeometryPropertyType` |
| `Lluvia_24hr` | `wsINETER-DGMT:Lluvia_24hrType` |

### `wsINETER-DGMT:Lluvia_24hrs`

| Campo | Tipo |
|---|---|
| `lluvia` | `xsd:double` |
| `nombreestacion` | `xsd:string` |
| `longitud` | `xsd:float` |
| `latitud` | `xsd:float` |
| `altitud` | `xsd:float` |
| `codigo` | `xsd:string` |
| `nombresensor` | `xsd:string` |
| `point` | `gml:GeometryPropertyType` |
| `Lluvia_24hrs` | `wsINETER-DGMT:Lluvia_24hrsType` |

### `wsINETER-DGMT:lluvia_24hs`

| Campo | Tipo |
|---|---|
| `lluvia` | `xsd:double` |
| `nombreestacion` | `xsd:string` |
| `longitud` | `xsd:float` |
| `latitud` | `xsd:float` |
| `altitud` | `xsd:float` |
| `codigo` | `xsd:string` |
| `nombresensor` | `xsd:string` |
| `point` | `gml:GeometryPropertyType` |
| `lluvia_24hs` | `wsINETER-DGMT:lluvia_24hsType` |

### `wsINETER-DGMT:Lluvia_3h_managua`

| Campo | Tipo |
|---|---|
| `codigoestacion` | `xsd:int` |
| `nombreestacion` | `xsd:string` |
| `longitud` | `xsd:float` |
| `latitud` | `xsd:float` |
| `altitud` | `xsd:float` |
| `codigo` | `xsd:string` |
| `nombresensor` | `xsd:string` |
| `point` | `gml:GeometryPropertyType` |
| `lluvia` | `xsd:double` |
| `Lluvia_3h_managua` | `wsINETER-DGMT:Lluvia_3h_managuaType` |

### `wsINETER-DGMT:Lluvia_3hr`

| Campo | Tipo |
|---|---|
| `lluvia` | `xsd:double` |
| `nombreestacion` | `xsd:string` |
| `longitud` | `xsd:float` |
| `latitud` | `xsd:float` |
| `altitud` | `xsd:float` |
| `codigo` | `xsd:string` |
| `nombresensor` | `xsd:string` |
| `point` | `gml:GeometryPropertyType` |
| `Lluvia_3hr` | `wsINETER-DGMT:Lluvia_3hrType` |

### `wsINETER-DGMT:Lluvia_3hrs`

| Campo | Tipo |
|---|---|
| `lluvia` | `xsd:double` |
| `nombreestacion` | `xsd:string` |
| `longitud` | `xsd:float` |
| `latitud` | `xsd:float` |
| `altitud` | `xsd:float` |
| `codigo` | `xsd:string` |
| `nombresensor` | `xsd:string` |
| `point` | `gml:GeometryPropertyType` |
| `Lluvia_3hrs` | `wsINETER-DGMT:Lluvia_3hrsType` |

### `wsINETER-DGMT:lluvia_3hs`

| Campo | Tipo |
|---|---|
| `lluvia` | `xsd:double` |
| `nombreestacion` | `xsd:string` |
| `longitud` | `xsd:float` |
| `latitud` | `xsd:float` |
| `altitud` | `xsd:float` |
| `codigo` | `xsd:string` |
| `nombresensor` | `xsd:string` |
| `point` | `gml:GeometryPropertyType` |
| `lluvia_3hs` | `wsINETER-DGMT:lluvia_3hsType` |

### `wsINETER-DGMT:Lluvia_48hrs`

| Campo | Tipo |
|---|---|
| `lluvia` | `xsd:double` |
| `nombreestacion` | `xsd:string` |
| `longitud` | `xsd:float` |
| `latitud` | `xsd:float` |
| `altitud` | `xsd:float` |
| `codigo` | `xsd:string` |
| `nombresensor` | `xsd:string` |
| `point` | `gml:GeometryPropertyType` |
| `Lluvia_48hrs` | `wsINETER-DGMT:Lluvia_48hrsType` |

### `wsINETER-DGMT:Lluvia_6hrs`

| Campo | Tipo |
|---|---|
| `lluvia` | `xsd:double` |
| `nombreestacion` | `xsd:string` |
| `longitud` | `xsd:float` |
| `latitud` | `xsd:float` |
| `altitud` | `xsd:float` |
| `codigo` | `xsd:string` |
| `nombresensor` | `xsd:string` |
| `point` | `gml:GeometryPropertyType` |
| `Lluvia_6hrs` | `wsINETER-DGMT:Lluvia_6hrsType` |

### `wsINETER-DGMT:Lluvia_72hrs`

| Campo | Tipo |
|---|---|
| `lluvia` | `xsd:double` |
| `nombreestacion` | `xsd:string` |
| `longitud` | `xsd:float` |
| `latitud` | `xsd:float` |
| `altitud` | `xsd:float` |
| `codigo` | `xsd:string` |
| `nombresensor` | `xsd:string` |
| `point` | `gml:GeometryPropertyType` |
| `Lluvia_72hrs` | `wsINETER-DGMT:Lluvia_72hrsType` |

### `wsINETER-DGMT:Lluvia_Estaciones_mng8r`

| Campo | Tipo |
|---|---|
| `codigo` | `xsd:string` |
| `nombre` | `xsd:string` |
| `longitud` | `xsd:double` |
| `latitud` | `xsd:double` |
| `altitud` | `xsd:double` |
| `edicion` | `xsd:double` |
| `fechahora` | `xsd:string` |
| `geom` | `gml:GeometryPropertyType` |
| `Lluvia_Estaciones_mng8r` | `wsINETER-DGMT:Lluvia_Estaciones_mng8rType` |

### `wsINETER-DGMT:Lluvias_AmenEx_Abr_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fid_amenaz` | `xsd:int` |
| `id` | `xsd:int` |
| `amenaza` | `xsd:string` |
| `fid_union_` | `xsd:int` |
| `fid_planti` | `xsd:int` |
| `id_1` | `xsd:int` |
| `fid_plan_1` | `xsd:int` |
| `id_12` | `xsd:int` |
| `abril` | `xsd:string` |
| `Lluvias_AmenEx_Abr_2022` | `wsINETER-DGMT:Lluvias_AmenEx_Abr_2022Type` |

### `wsINETER-DGMT:Lluvias_AmenEx_Ago_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `exc_prec` | `xsd:string` |
| `Lluvias_AmenEx_Ago_2022` | `wsINETER-DGMT:Lluvias_AmenEx_Ago_2022Type` |

### `wsINETER-DGMT:Lluvias_AmenEx_Anual_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `amenaza` | `xsd:string` |
| `Lluvias_AmenEx_Anual_2022` | `wsINETER-DGMT:Lluvias_AmenEx_Anual_2022Type` |

### `wsINETER-DGMT:Lluvias_AmenEx_Dic_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `amenaza` | `xsd:string` |
| `Lluvias_AmenEx_Dic_2022` | `wsINETER-DGMT:Lluvias_AmenEx_Dic_2022Type` |

### `wsINETER-DGMT:Lluvias_AmenEx_Ene_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `ene` | `xsd:string` |
| `Lluvias_AmenEx_Ene_2022` | `wsINETER-DGMT:Lluvias_AmenEx_Ene_2022Type` |

### `wsINETER-DGMT:Lluvias_AmenEx_Feb_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `febrero` | `xsd:string` |
| `Lluvias_AmenEx_Feb_2022` | `wsINETER-DGMT:Lluvias_AmenEx_Feb_2022Type` |

### `wsINETER-DGMT:Lluvias_AmenEx_IISub_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `amenazas` | `xsd:string` |
| `Lluvias_AmenEx_IISub_2022` | `wsINETER-DGMT:Lluvias_AmenEx_IISub_2022Type` |

### `wsINETER-DGMT:Lluvias_AmenEx_ISub_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `amenaza` | `xsd:string` |
| `Lluvias_AmenEx_ISub_2022` | `wsINETER-DGMT:Lluvias_AmenEx_ISub_2022Type` |

### `wsINETER-DGMT:Lluvias_AmenEx_Jul_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `exc_lluvia` | `xsd:string` |
| `Lluvias_AmenEx_Jul_2022` | `wsINETER-DGMT:Lluvias_AmenEx_Jul_2022Type` |

### `wsINETER-DGMT:Lluvias_AmenEx_Jun_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `exc_lluvia` | `xsd:string` |
| `Lluvias_AmenEx_Jun_2022` | `wsINETER-DGMT:Lluvias_AmenEx_Jun_2022Type` |

### `wsINETER-DGMT:Lluvias_AmenEx_Mar_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `marzo` | `xsd:string` |
| `Lluvias_AmenEx_Mar_2022` | `wsINETER-DGMT:Lluvias_AmenEx_Mar_2022Type` |

### `wsINETER-DGMT:Lluvias_AmenEx_May_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `lluv_exc` | `xsd:string` |
| `Lluvias_AmenEx_May_2022` | `wsINETER-DGMT:Lluvias_AmenEx_May_2022Type` |

### `wsINETER-DGMT:Lluvias_AmenEx_Nov_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `amenaza` | `xsd:string` |
| `Lluvias_AmenEx_Nov_2022` | `wsINETER-DGMT:Lluvias_AmenEx_Nov_2022Type` |

### `wsINETER-DGMT:Lluvias_AmenEx_Oct_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `anomalias` | `xsd:string` |
| `Lluvias_AmenEx_Oct_2022` | `wsINETER-DGMT:Lluvias_AmenEx_Oct_2022Type` |

### `wsINETER-DGMT:Lluvias_AmenEx_SemAbr_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `sem_abr` | `xsd:string` |
| `Lluvias_AmenEx_SemAbr_2022` | `wsINETER-DGMT:Lluvias_AmenEx_SemAbr_2022Type` |

### `wsINETER-DGMT:Lluvias_AmenEx_SemOct_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `sem_oct` | `xsd:string` |
| `Lluvias_AmenEx_SemOct_2022` | `wsINETER-DGMT:Lluvias_AmenEx_SemOct_2022Type` |

### `wsINETER-DGMT:Lluvias_AmenEx_Sep_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `mas_lluvia` | `xsd:string` |
| `Lluvias_AmenEx_Sep_2022` | `wsINETER-DGMT:Lluvias_AmenEx_Sep_2022Type` |

### `wsINETER-DGMT:Periodo_apante`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `pol` | `xsd:string` |
| `Periodo_apante` | `wsINETER-DGMT:Periodo_apanteType` |

### `wsINETER-DGMT:Periodo_lluvioso`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `pol2` | `xsd:string` |
| `pol` | `xsd:int` |
| `Periodo_lluvioso` | `wsINETER-DGMT:Periodo_lluviosoType` |

### `wsINETER-DGMT:Periodo_seco`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `poli` | `xsd:string` |
| `Periodo_seco` | `wsINETER-DGMT:Periodo_secoType` |

### `wsINETER-DGMT:plan_hr_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `total2` | `xsd:string` |
| `total` | `xsd:int` |
| `plan_hr_2022` | `wsINETER-DGMT:plan_hr_2022Type` |

### `wsINETER-DGMT:Precipitacion_Abril_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `id` | `xsd:int` |
| `total2` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `total` | `xsd:int` |
| `Precipitacion_Abril_2022` | `wsINETER-DGMT:Precipitacion_Abril_2022Type` |

### `wsINETER-DGMT:Precipitacion_Agosto_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `id` | `xsd:int` |
| `total2` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `total` | `xsd:int` |
| `Precipitacion_Agosto_2022` | `wsINETER-DGMT:Precipitacion_Agosto_2022Type` |

### `wsINETER-DGMT:Precipitacion_Anual`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `total2` | `xsd:string` |
| `total` | `xsd:int` |
| `Precipitacion_Anual` | `wsINETER-DGMT:Precipitacion_AnualType` |

### `wsINETER-DGMT:Precipitacion_Anual_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `id` | `xsd:int` |
| `total2` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `total` | `xsd:int` |
| `Precipitacion_Anual_2022` | `wsINETER-DGMT:Precipitacion_Anual_2022Type` |

### `wsINETER-DGMT:Precipitacion_Diciembre_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `id` | `xsd:int` |
| `total2` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `total` | `xsd:int` |
| `Precipitacion_Diciembre_2022` | `wsINETER-DGMT:Precipitacion_Diciembre_2022Type` |

### `wsINETER-DGMT:Precipitacion_Enero_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `id` | `xsd:int` |
| `total2` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `total` | `xsd:int` |
| `Precipitacion_Enero_2022` | `wsINETER-DGMT:Precipitacion_Enero_2022Type` |

### `wsINETER-DGMT:Precipitacion_Febrero_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `id` | `xsd:int` |
| `total2` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `total` | `xsd:int` |
| `Precipitacion_Febrero_2022` | `wsINETER-DGMT:Precipitacion_Febrero_2022Type` |

### `wsINETER-DGMT:Precipitacion_frecuente_Nina_2012`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `prt2` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `prt` | `xsd:int` |
| `Precipitacion_frecuente_Nina_2012` | `wsINETER-DGMT:Precipitacion_frecuente_Nina_2012Type` |

### `wsINETER-DGMT:Precipitacion_Frecuente_Nino_2012`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `id` | `xsd:int` |
| `prt2` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `prt` | `xsd:int` |
| `Precipitacion_Frecuente_Nino_2012` | `wsINETER-DGMT:Precipitacion_Frecuente_Nino_2012Type` |

### `wsINETER-DGMT:Precipitacion_Julio_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `id` | `xsd:int` |
| `total2` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `total` | `xsd:int` |
| `Precipitacion_Julio_2022` | `wsINETER-DGMT:Precipitacion_Julio_2022Type` |

### `wsINETER-DGMT:Precipitacion_Junio_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `id` | `xsd:int` |
| `total2` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `total` | `xsd:int` |
| `Precipitacion_Junio_2022` | `wsINETER-DGMT:Precipitacion_Junio_2022Type` |

### `wsINETER-DGMT:Precipitacion_Lluvioso_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `id` | `xsd:int` |
| `pol_i_sub` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `Precipitacion_Lluvioso_2022` | `wsINETER-DGMT:Precipitacion_Lluvioso_2022Type` |

### `wsINETER-DGMT:Precipitacion_Marzo_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `id` | `xsd:int` |
| `total2` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `total` | `xsd:int` |
| `Precipitacion_Marzo_2022` | `wsINETER-DGMT:Precipitacion_Marzo_2022Type` |

### `wsINETER-DGMT:Precipitacion_Mayo_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `id` | `xsd:int` |
| `total2` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `total` | `xsd:int` |
| `Precipitacion_Mayo_2022` | `wsINETER-DGMT:Precipitacion_Mayo_2022Type` |

### `wsINETER-DGMT:Precipitacion_Media_Anual_Nina_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `id` | `xsd:int` |
| `prt2` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `prt` | `xsd:int` |
| `Precipitacion_Media_Anual_Nina_2022` | `wsINETER-DGMT:Precipitacion_Media_Anual_Nina_2022Type` |

### `wsINETER-DGMT:Precipitacion_Media_Anual_Nino`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `id` | `xsd:int` |
| `prt2` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `prt` | `xsd:int` |
| `Precipitacion_Media_Anual_Nino` | `wsINETER-DGMT:Precipitacion_Media_Anual_NinoType` |

### `wsINETER-DGMT:Precipitacion_Media_Apante_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `id` | `xsd:int` |
| `pol_i_sub2` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `pol_i_sub` | `xsd:int` |
| `Precipitacion_Media_Apante_2022` | `wsINETER-DGMT:Precipitacion_Media_Apante_2022Type` |

### `wsINETER-DGMT:Precipitacion_Noviembre_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `id` | `xsd:int` |
| `total2` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `total` | `xsd:int` |
| `Precipitacion_Noviembre_2022` | `wsINETER-DGMT:Precipitacion_Noviembre_2022Type` |

### `wsINETER-DGMT:Precipitacion_Octubre_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `id` | `xsd:int` |
| `total2` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `total` | `xsd:int` |
| `Precipitacion_Octubre_2022` | `wsINETER-DGMT:Precipitacion_Octubre_2022Type` |

### `wsINETER-DGMT:Precipitacion_Periodo_Sublluvioso_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `id` | `xsd:int` |
| `pol_i_sub2` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `pol_i_sub` | `xsd:int` |
| `Precipitacion_Periodo_Sublluvioso_2022` | `wsINETER-DGMT:Precipitacion_Periodo_Sublluvioso_2022Type` |

### `wsINETER-DGMT:Precipitacion_seco`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `id` | `xsd:int` |
| `pol_i_sub2` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `pol_i_sub` | `xsd:int` |
| `Precipitacion_seco` | `wsINETER-DGMT:Precipitacion_secoType` |

### `wsINETER-DGMT:Precipitacion_Segundo_Sublluvioso_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `id` | `xsd:int` |
| `pol_i_sub2` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `pol_i_sub` | `xsd:int` |
| `Precipitacion_Segundo_Sublluvioso_2022` | `wsINETER-DGMT:Precipitacion_Segundo_Sublluvioso_2022Type` |

### `wsINETER-DGMT:Precipitacion_Septiembre_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `id` | `xsd:int` |
| `total2` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `total` | `xsd:int` |
| `Precipitacion_Septiembre_2022` | `wsINETER-DGMT:Precipitacion_Septiembre_2022Type` |

### `wsINETER-DGMT:Precipitacioncaelus_Simet`

| Campo | Tipo |
|---|---|
| `codigo` | `xsd:int` |
| `nombreestacion` | `xsd:string` |
| `fuente` | `xsd:string` |
| `geom` | `gml:PointPropertyType` |
| `ultimalectura` | `xsd:dateTime` |
| `lecprecipitacion` | `xsd:float` |
| `fechaformato` | `xsd:string` |
| `horaformato` | `xsd:string` |
| `Precipitacioncaelus_Simet` | `wsINETER-DGMT:Precipitacioncaelus_SimetType` |

### `wsINETER-DGMT:Precipitacioncaelus_Simet_24h`

| Campo | Tipo |
|---|---|
| `codigo` | `xsd:int` |
| `nombreestacion` | `xsd:string` |
| `fuente` | `xsd:string` |
| `geom` | `gml:PointPropertyType` |
| `fecha` | `xsd:string` |
| `suma24h` | `xsd:float` |
| `norma` | `xsd:double` |
| `Precipitacioncaelus_Simet_24h` | `wsINETER-DGMT:Precipitacioncaelus_Simet_24hType` |

### `wsINETER-DGMT:Promedio_Dipiltopreci`

| Campo | Tipo |
|---|---|
| `codigo` | `xsd:int` |
| `nombreestacion` | `xsd:string` |
| `municipio` | `xsd:string` |
| `departamento` | `xsd:string` |
| `latitud` | `xsd:double` |
| `longitud` | `xsd:double` |
| `promediopr` | `xsd:double` |
| `geom` | `gml:PointPropertyType` |
| `Promedio_Dipiltopreci` | `wsINETER-DGMT:Promedio_DipiltopreciType` |

### `wsINETER-DGMT:Pronostico`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `radii` | `xsd:decimal` |
| `stormid` | `xsd:string` |
| `basin` | `xsd:string` |
| `stormnum` | `xsd:decimal` |
| `advnum` | `xsd:string` |
| `validtime` | `xsd:string` |
| `synoptime` | `xsd:string` |
| `timezone` | `xsd:string` |
| `tau` | `xsd:decimal` |
| `ne` | `xsd:decimal` |
| `se` | `xsd:decimal` |
| `sw` | `xsd:decimal` |
| `nw` | `xsd:decimal` |
| `Pronostico` | `wsINETER-DGMT:PronosticoType` |

### `wsINETER-DGMT:Pronostico_5day_Tipociclon_p`

| Campo | Tipo |
|---|---|
| `nombre_tormenta` | `xsd:string` |
| `basin` | `xsd:string` |
| `geom` | `gml:PointPropertyType` |
| `fecha_aviso` | `xsd:string` |
| `fecha_etiqueta` | `xsd:string` |
| `tipo_tormenta_prevista` | `xsd:string` |
| `hora_prevista_ciclon` | `xsd:int` |
| `fecha_completa` | `xsd:string` |
| `rafaga_viento` | `xsd:int` |
| `viento_maximo` | `xsd:int` |
| `tipo_ciclon` | `xsd:string` |
| `tipo_tormenta` | `xsd:string` |
| `categoria_ciclon` | `xsd:string` |
| `mas_alla_tiempo_valido` | `xsd:int` |
| `direccion_tormenta` | `xsd:int` |
| `Pronostico_5day_Tipociclon_p` | `wsINETER-DGMT:Pronostico_5day_Tipociclon_pType` |

### `wsINETER-DGMT:Pronostico_a`

| Campo | Tipo |
|---|---|
| `basin` | `xsd:string` |
| `geom` | `gml:SurfacePropertyType` |
| `nombre_tormenta` | `xsd:string` |
| `tipo_tormenta` | `xsd:string` |
| `fecha_aviso` | `xsd:string` |
| `numero_aviso` | `xsd:string` |
| `numero_cuenca` | `xsd:int` |
| `Pronostico_a` | `wsINETER-DGMT:Pronostico_aType` |

### `wsINETER-DGMT:Pronostico_l`

| Campo | Tipo |
|---|---|
| `basin` | `xsd:string` |
| `geom` | `gml:GeometryPropertyType` |
| `nombre_tormenta` | `xsd:string` |
| `tipo_tormenta` | `xsd:string` |
| `fecha_aviso` | `xsd:string` |
| `numero_aviso` | `xsd:string` |
| `numero_cuenca` | `xsd:int` |
| `Pronostico_l` | `wsINETER-DGMT:Pronostico_lType` |

### `wsINETER-DGMT:Pronostico_ps`

| Campo | Tipo |
|---|---|
| `basin` | `xsd:string` |
| `geom` | `gml:PointPropertyType` |
| `fecha_aviso` | `xsd:string` |
| `fecha_etiqueta` | `xsd:string` |
| `tipo_tormenta_prevista` | `xsd:string` |
| `hora_prevista_ciclon` | `xsd:int` |
| `fecha_completa` | `xsd:string` |
| `rafaga_viento` | `xsd:int` |
| `viento_maximo` | `xsd:int` |
| `nombre_tormenta` | `xsd:string` |
| `tipo_ciclon` | `xsd:string` |
| `tipo_tormenta` | `xsd:string` |
| `categoria_ciclon` | `xsd:string` |
| `mas_alla_tiempo_valido` | `xsd:int` |
| `direccion_tormenta` | `xsd:int` |
| `Pronostico_ps` | `wsINETER-DGMT:Pronostico_psType` |

### `wsINETER-DGMT:Pronostico_wwl`

| Campo | Tipo |
|---|---|
| `basin` | `xsd:string` |
| `geom` | `gml:GeometryPropertyType` |
| `nombre_tormenta` | `xsd:string` |
| `tipo_tormenta` | `xsd:string` |
| `fecha_aviso` | `xsd:string` |
| `numero_aviso` | `xsd:string` |
| `numero_cuenca` | `xsd:int` |
| `tcww` | `xsd:string` |
| `Pronostico_wwl` | `wsINETER-DGMT:Pronostico_wwlType` |

### `wsINETER-DGMT:pronosticoarea2025_ivan`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:SurfacePropertyType` |
| `stormname` | `xsd:string` |
| `stormtype` | `xsd:string` |
| `stormnum` | `xsd:int` |
| `fcstprd` | `xsd:int` |
| `basin` | `xsd:string` |
| `advdate` | `xsd:string` |
| `fecharegistro` | `xsd:dateTime` |
| `advisnum` | `xsd:string` |
| `pronosticoarea2025_ivan` | `wsINETER-DGMT:pronosticoarea2025_ivanType` |

### `wsINETER-DGMT:prt_max_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `prt2` | `xsd:string` |
| `prt` | `xsd:int` |
| `prt_max_2022` | `wsINETER-DGMT:prt_max_2022Type` |

### `wsINETER-DGMT:radiacionsolarcaelus`

| Campo | Tipo |
|---|---|
| `Estacion` | `xsd:string` |
| `codigo` | `xsd:string` |
| `longitud` | `xsd:float` |
| `latitud` | `xsd:float` |
| `Ultima lectura` | `xsd:dateTime` |
| `Valor` | `xsd:double` |
| `point` | `gml:GeometryPropertyType` |
| `radiacionsolarcaelus` | `wsINETER-DGMT:radiacionsolarcaelusType` |

### `wsINETER-DGMT:Regiones_Climaticas`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `adm0_cod3` | `xsd:string` |
| `adm0_nom` | `xsd:string` |
| `regiones_c` | `xsd:string` |
| `Regiones_Climaticas` | `wsINETER-DGMT:Regiones_ClimaticasType` |

### `wsINETER-DGMT:sanrafaelwgs84`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `text` | `xsd:string` |
| `codenc` | `xsd:string` |
| `perimetros` | `xsd:string` |
| `mapaparcel` | `xsd:string` |
| `bloque` | `xsd:string` |
| `lote` | `xsd:string` |
| `barrio` | `xsd:string` |
| `municipio` | `xsd:string` |
| `departamen` | `xsd:string` |
| `solicitud` | `xsd:string` |
| `colindante` | `xsd:string` |
| `sector` | `xsd:string` |
| `polig` | `xsd:string` |
| `x` | `xsd:string` |
| `y` | `xsd:string` |
| `nc` | `xsd:string` |
| `codenc_mat` | `xsd:string` |
| `nc_matriz` | `xsd:string` |
| `area` | `xsd:double` |
| `comentario` | `xsd:string` |
| `retiro` | `xsd:string` |
| `riesgo` | `xsd:string` |
| `propietari` | `xsd:string` |
| `invasion` | `xsd:string` |
| `sanrafaelwgs84` | `wsINETER-DGMT:sanrafaelwgs84Type` |

### `wsINETER-DGMT:Seg_Subperiodo_lluvioso`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `pol` | `xsd:string` |
| `Seg_Subperiodo_lluvioso` | `wsINETER-DGMT:Seg_Subperiodo_lluviosoType` |

### `wsINETER-DGMT:temp_anual_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `tmd_anual2` | `xsd:string` |
| `tmd_anual` | `xsd:int` |
| `temp_anual_2022` | `wsINETER-DGMT:temp_anual_2022Type` |

### `wsINETER-DGMT:temp_diciembre_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `tmddiciemb2` | `xsd:string` |
| `tmddiciemb` | `xsd:int` |
| `temp_diciembre_2022` | `wsINETER-DGMT:temp_diciembre_2022Type` |

### `wsINETER-DGMT:temp_maxima_anual_2022`

> [!warning] Schema pendente; validar antes de uso.

### `wsINETER-DGMT:temp_noviembre_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `tmdnoviemb2` | `xsd:string` |
| `tmdnoviemb` | `xsd:int` |
| `temp_noviembre_2022` | `wsINETER-DGMT:temp_noviembre_2022Type` |

### `wsINETER-DGMT:temp_octubre_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `tmdoctubre2` | `xsd:string` |
| `tmdoctubre` | `xsd:int` |
| `temp_octubre_2022` | `wsINETER-DGMT:temp_octubre_2022Type` |

### `wsINETER-DGMT:temp_septiembre_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `tmdseptiem2` | `xsd:string` |
| `tmdseptiem` | `xsd:int` |
| `temp_septiembre_2022` | `wsINETER-DGMT:temp_septiembre_2022Type` |

### `wsINETER-DGMT:Temperatura_Abril_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `tmdabril2` | `xsd:string` |
| `tmdabril` | `xsd:int` |
| `Temperatura_Abril_2022` | `wsINETER-DGMT:Temperatura_Abril_2022Type` |

### `wsINETER-DGMT:Temperatura_Agosto_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `tmdagosto2` | `xsd:string` |
| `tmdagosto` | `xsd:int` |
| `Temperatura_Agosto_2022` | `wsINETER-DGMT:Temperatura_Agosto_2022Type` |

### `wsINETER-DGMT:Temperatura_Anual`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `tmd_anual2` | `xsd:string` |
| `tmd_anual` | `xsd:int` |
| `Temperatura_Anual` | `wsINETER-DGMT:Temperatura_AnualType` |

### `wsINETER-DGMT:Temperatura_CaeluSimet_ot`

| Campo | Tipo |
|---|---|
| `codigo` | `xsd:int` |
| `nombrebd` | `xsd:string` |
| `geom` | `gml:GeometryPropertyType` |
| `valor` | `xsd:float` |
| `fechaformato` | `xsd:string` |
| `horaformato` | `xsd:string` |
| `Temperatura_CaeluSimet_ot` | `wsINETER-DGMT:Temperatura_CaeluSimet_otType` |

### `wsINETER-DGMT:Temperatura_Enero_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `tmdenero2` | `xsd:string` |
| `tmdenero` | `xsd:int` |
| `Temperatura_Enero_2022` | `wsINETER-DGMT:Temperatura_Enero_2022Type` |

### `wsINETER-DGMT:Temperatura_Febrero_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `tmdfeb2` | `xsd:string` |
| `tmdfeb` | `xsd:int` |
| `Temperatura_Febrero_2022` | `wsINETER-DGMT:Temperatura_Febrero_2022Type` |

### `wsINETER-DGMT:Temperatura_Julio_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `tmdjulio2` | `xsd:string` |
| `tmdjulio` | `xsd:int` |
| `Temperatura_Julio_2022` | `wsINETER-DGMT:Temperatura_Julio_2022Type` |

### `wsINETER-DGMT:Temperatura_Junio_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `tmdjunio2` | `xsd:string` |
| `tmdjunio` | `xsd:int` |
| `Temperatura_Junio_2022` | `wsINETER-DGMT:Temperatura_Junio_2022Type` |

### `wsINETER-DGMT:Temperatura_Marzo_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `tmdmarzo2` | `xsd:string` |
| `tmdmarzo` | `xsd:int` |
| `Temperatura_Marzo_2022` | `wsINETER-DGMT:Temperatura_Marzo_2022Type` |

### `wsINETER-DGMT:Temperatura_Mayo_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `tmdmayo2` | `xsd:string` |
| `tmdmayo` | `xsd:int` |
| `Temperatura_Mayo_2022` | `wsINETER-DGMT:Temperatura_Mayo_2022Type` |

### `wsINETER-DGMT:temperatura_ot`

> [!warning] Schema pendente; validar antes de uso.

### `wsINETER-DGMT:temperatura_simet_caelus`

| Campo | Tipo |
|---|---|
| `codigo` | `xsd:int` |
| `nombrebd` | `xsd:string` |
| `geom` | `gml:GeometryPropertyType` |
| `valor` | `xsd:float` |
| `fechaformato` | `xsd:string` |
| `horaformato` | `xsd:string` |
| `temperatura_simet_caelus` | `wsINETER-DGMT:temperatura_simet_caelusType` |

### `wsINETER-DGMT:temperaturacaelus`

| Campo | Tipo |
|---|---|
| `Estacion` | `xsd:string` |
| `codigo` | `xsd:string` |
| `longitud` | `xsd:float` |
| `latitud` | `xsd:float` |
| `Ultima lectura` | `xsd:dateTime` |
| `Valor` | `xsd:double` |
| `point` | `gml:GeometryPropertyType` |
| `temperaturacaelus` | `wsINETER-DGMT:temperaturacaelusType` |

### `wsINETER-DGMT:tempmaxima_anual_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `tmxanual2` | `xsd:string` |
| `tmxanual` | `xsd:int` |
| `tempmaxima_anual_2022` | `wsINETER-DGMT:tempmaxima_anual_2022Type` |

### `wsINETER-DGMT:tempminima_anual_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:int` |
| `tmnanual2` | `xsd:string` |
| `tmnanual` | `xsd:int` |
| `tempminima_anual_2022` | `wsINETER-DGMT:tempminima_anual_2022Type` |

### `wsINETER-DGMT:Total_Dipiltopreci`

| Campo | Tipo |
|---|---|
| `codigo` | `xsd:int` |
| `nombreestacion` | `xsd:string` |
| `municipio` | `xsd:string` |
| `departamento` | `xsd:string` |
| `latitud` | `xsd:double` |
| `longitud` | `xsd:double` |
| `totalpreci` | `xsd:double` |
| `geom` | `gml:PointPropertyType` |
| `Total_Dipiltopreci` | `wsINETER-DGMT:Total_DipiltopreciType` |

### `wsINETER-DGMT:Trayectoria_Dos_Dias_a`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `basin` | `xsd:string` |
| `riesgo2dia` | `xsd:string` |
| `probabilidad2dias` | `xsd:string` |
| `Trayectoria_Dos_Dias_a` | `wsINETER-DGMT:Trayectoria_Dos_Dias_aType` |

### `wsINETER-DGMT:Trayectoria_Dos_Dias_l`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `basin` | `xsd:string` |
| `riesgo2dia` | `xsd:string` |
| `probabilidad2dias` | `xsd:string` |
| `Trayectoria_Dos_Dias_l` | `wsINETER-DGMT:Trayectoria_Dos_Dias_lType` |

### `wsINETER-DGMT:Trayectoria_Dos_Dias_p`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `basin` | `xsd:string` |
| `riesgo2dia` | `xsd:string` |
| `probabilidad2dias` | `xsd:string` |
| `Trayectoria_Dos_Dias_p` | `wsINETER-DGMT:Trayectoria_Dos_Dias_pType` |

### `wsINETER-DGMT:Trayectoria_Huracanes`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `nombre` | `xsd:string` |
| `viento` | `xsd:int` |
| `presion` | `xsd:int` |
| `Trayectoria_Huracanes` | `wsINETER-DGMT:Trayectoria_HuracanesType` |

### `wsINETER-DGMT:Trayectoria_Siete_Dias_a`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `basin` | `xsd:string` |
| `riesgo7dia` | `xsd:string` |
| `probabilidad7dias` | `xsd:string` |
| `Trayectoria_Siete_Dias_a` | `wsINETER-DGMT:Trayectoria_Siete_Dias_aType` |

### `wsINETER-DGMT:Trayectoria_Siete_Dias_l`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `basin` | `xsd:string` |
| `riesgo7dia` | `xsd:string` |
| `probabilidad7dias` | `xsd:string` |
| `Trayectoria_Siete_Dias_l` | `wsINETER-DGMT:Trayectoria_Siete_Dias_lType` |

### `wsINETER-DGMT:Trayectoria_Siete_Dias_p`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `basin` | `xsd:string` |
| `riesgo7dia` | `xsd:string` |
| `probabilidad7dias` | `xsd:string` |
| `Trayectoria_Siete_Dias_p` | `wsINETER-DGMT:Trayectoria_Siete_Dias_pType` |

### `wsINETER-DGMT:Vientos_Simet_ot`

| Campo | Tipo |
|---|---|
| `codigo` | `xsd:int` |
| `nombrebd` | `xsd:string` |
| `geom` | `gml:GeometryPropertyType` |
| `velocidad` | `xsd:float` |
| `direccion` | `xsd:float` |
| `valdire` | `xsd:string` |
| `fechaformato` | `xsd:string` |
| `horaformato` | `xsd:string` |
| `Vientos_Simet_ot` | `wsINETER-DGMT:Vientos_Simet_otType` |

### `wsINETER-DGMT:vientounificada`

> [!warning] Schema pendente; validar antes de uso.

### `wsINETER-DGMT:Vista_Pronostico_AsentamientoH_Afectados`

| Campo | Tipo |
|---|---|
| `fechahora` | `xsd:string` |
| `geom` | `gml:SurfacePropertyType` |
| `departamento` | `xsd:string` |
| `municipio` | `xsd:string` |
| `nombre` | `xsd:string` |
| `cant_poblacion` | `xsd:double` |
| `cant_vivienda` | `xsd:double` |
| `tipo_revestimiento` | `xsd:string` |
| `ha` | `xsd:double` |
| `Vista_Pronostico_AsentamientoH_Afectados` | `wsINETER-DGMT:Vista_Pronostico_AsentamientoH_AfectadosType` |

### `wsINETER-DGOT:Alerta_Incendios_FW_7Dias`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `latitude` | `xsd:decimal` |
| `longitude` | `xsd:decimal` |
| `bright_ti4` | `xsd:decimal` |
| `scan` | `xsd:decimal` |
| `track` | `xsd:decimal` |
| `acq_date` | `xsd:date` |
| `acq_time` | `xsd:string` |
| `satellite` | `xsd:string` |
| `confidence` | `xsd:string` |
| `version` | `xsd:string` |
| `bright_ti5` | `xsd:decimal` |
| `frp` | `xsd:decimal` |
| `daynight` | `xsd:string` |
| `Alerta_Incendios_FW_7Dias` | `wsINETER-DGOT:Alerta_Incendios_FW_7DiasType` |

### `wsINETER-DGOT:Apante16_20`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `agrup16_20` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `Apante16_20` | `wsINETER-DGOT:Apante16_20Type` |

### `wsINETER-DGOT:Apante_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `fid_apante` | `xsd:long` |
| `capante21` | `xsd:string` |
| `ha` | `xsd:double` |
| `mz` | `xsd:double` |
| `agrupculti` | `xsd:string` |
| `rubros` | `xsd:string` |
| `destinocul` | `xsd:string` |
| `id_unico_1` | `xsd:string` |
| `depto` | `xsd:string` |
| `municipio` | `xsd:string` |
| `id_mun` | `xsd:double` |
| `id_com` | `xsd:double` |
| `area_ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `comun` | `xsd:string` |
| `fid_depart` | `xsd:long` |
| `objectid_1` | `xsd:long` |
| `clase` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_le_1` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `Apante_2022` | `wsINETER-DGOT:Apante_2022Type` |

### `wsINETER-DGOT:Areas_Protegidas`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `region` | `xsd:string` |
| `numero` | `xsd:double` |
| `categoria` | `xsd:string` |
| `decreto` | `xsd:string` |
| `año` | `xsd:int` |
| `nombre` | `xsd:string` |
| `Areas_Protegidas` | `wsINETER-DGOT:Areas_ProtegidasType` |

### `wsINETER-DGOT:Asentamientos_Casas`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `nombre` | `xsd:string` |
| `categoria` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `pbporviv` | `xsd:double` |
| `id_unico` | `xsd:long` |
| `no_viviend` | `xsd:double` |
| `buff_dist` | `xsd:double` |
| `orig_fid` | `xsd:long` |
| `Asentamientos_Casas` | `wsINETER-DGOT:Asentamientos_CasasType` |

### `wsINETER-DGOT:Asentamientos_Humanos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `target_fid` | `xsd:long` |
| `cod_dpto` | `xsd:string` |
| `dpto` | `xsd:string` |
| `cod_mpio` | `xsd:string` |
| `municipio` | `xsd:string` |
| `nombre` | `xsd:string` |
| `id_unico` | `xsd:long` |
| `ha` | `xsd:double` |
| `ti_revesti` | `xsd:string` |
| `dens_vial` | `xsd:double` |
| `cant_acces` | `xsd:double` |
| `suma_long` | `xsd:double` |
| `tfuenagua` | `xsd:string` |
| `estado_v` | `xsd:string` |
| `evpeso_4_1` | `xsd:double` |
| `dvpeso_5_2` | `xsd:double` |
| `ca_peso3_3` | `xsd:double` |
| `t_peso20_p` | `xsd:double` |
| `n_de_esc` | `xsd:double` |
| `ecpeso4_1e` | `xsd:double` |
| `n_inatec` | `xsd:double` |
| `inpeso5_2e` | `xsd:double` |
| `n_univ` | `xsd:double` |
| `unpeso6_3e` | `xsd:double` |
| `n_udssalu` | `xsd:double` |
| `slpeso5_1` | `xsd:double` |
| `tspeso12_2` | `xsd:double` |
| `tiudssalud` | `xsd:string` |
| `cercania` | `xsd:string` |
| `c_peso10_c` | `xsd:double` |
| `f_adtva` | `xsd:string` |
| `f_peso5_fa` | `xsd:double` |
| `categ_pobl` | `xsd:string` |
| `peso_15_p` | `xsd:double` |
| `dens_pob` | `xsd:double` |
| `peso_6_1` | `xsd:double` |
| `pobl_2022` | `xsd:double` |
| `pbporviv` | `xsd:double` |
| `no_viviend` | `xsd:double` |
| `categ_dens` | `xsd:string` |
| `tipo_const` | `xsd:string` |
| `tipo` | `xsd:string` |
| `valorfinal` | `xsd:double` |
| `prima_porc` | `xsd:double` |
| `secun_porc` | `xsd:double` |
| `terci_porc` | `xsd:double` |
| `cat_econom` | `xsd:string` |
| `urb_rur1` | `xsd:string` |
| `clasfi_ah1` | `xsd:string` |
| `territorio` | `xsd:string` |
| `Asentamientos_Humanos` | `wsINETER-DGOT:Asentamientos_HumanosType` |

### `wsINETER-DGOT:AsentamientosHumanos_mon`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `target_fid` | `xsd:long` |
| `cod_dpto` | `xsd:string` |
| `dpto` | `xsd:string` |
| `cod_mpio` | `xsd:string` |
| `municipio` | `xsd:string` |
| `nombre` | `xsd:string` |
| `id_unico` | `xsd:long` |
| `ha` | `xsd:double` |
| `ti_revesti` | `xsd:string` |
| `dens_vial` | `xsd:double` |
| `cant_acces` | `xsd:double` |
| `suma_long` | `xsd:double` |
| `tfuenagua` | `xsd:string` |
| `estado_v` | `xsd:string` |
| `evpeso_4_1` | `xsd:double` |
| `dvpeso_5_2` | `xsd:double` |
| `ca_peso3_3` | `xsd:double` |
| `t_peso20_p` | `xsd:double` |
| `n_de_esc` | `xsd:double` |
| `ecpeso4_1e` | `xsd:double` |
| `n_inatec` | `xsd:double` |
| `inpeso5_2e` | `xsd:double` |
| `n_univ` | `xsd:double` |
| `unpeso6_3e` | `xsd:double` |
| `n_udssalu` | `xsd:double` |
| `slpeso5_1` | `xsd:double` |
| `tspeso12_2` | `xsd:double` |
| `tiudssalud` | `xsd:string` |
| `cercania` | `xsd:string` |
| `c_peso10_c` | `xsd:double` |
| `f_adtva` | `xsd:string` |
| `f_peso5_fa` | `xsd:double` |
| `categ_pobl` | `xsd:string` |
| `peso_15_p` | `xsd:double` |
| `dens_pob` | `xsd:double` |
| `peso_6_1` | `xsd:double` |
| `pobl_2022` | `xsd:double` |
| `pbporviv` | `xsd:double` |
| `no_viviend` | `xsd:double` |
| `categ_dens` | `xsd:string` |
| `tipo_const` | `xsd:string` |
| `tipo` | `xsd:string` |
| `valorfinal` | `xsd:double` |
| `prima_porc` | `xsd:double` |
| `secun_porc` | `xsd:double` |
| `terci_porc` | `xsd:double` |
| `cat_econom` | `xsd:string` |
| `urb_rur1` | `xsd:string` |
| `clasfi_ah1` | `xsd:string` |
| `territorio` | `xsd:string` |
| `AsentamientosHumanos_mon` | `wsINETER-DGOT:AsentamientosHumanos_monType` |

### `wsINETER-DGOT:Boaco00_05`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Boaco00_05` | `wsINETER-DGOT:Boaco00_05Type` |

### `wsINETER-DGOT:Boaco00_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Boaco00_15` | `wsINETER-DGOT:Boaco00_15Type` |

### `wsINETER-DGOT:Boaco00_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Boaco00_18` | `wsINETER-DGOT:Boaco00_18Type` |

### `wsINETER-DGOT:Boaco05_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `fid` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Boaco05_10` | `wsINETER-DGOT:Boaco05_10Type` |

### `wsINETER-DGOT:Boaco05_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Boaco05_15` | `wsINETER-DGOT:Boaco05_15Type` |

### `wsINETER-DGOT:Boaco05_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Boaco05_18` | `wsINETER-DGOT:Boaco05_18Type` |

### `wsINETER-DGOT:Boaco10_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Boaco10_15` | `wsINETER-DGOT:Boaco10_15Type` |

### `wsINETER-DGOT:Boaco10_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Boaco10_18` | `wsINETER-DGOT:Boaco10_18Type` |

### `wsINETER-DGOT:Boaco15_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Boaco15_18` | `wsINETER-DGOT:Boaco15_18Type` |

### `wsINETER-DGOT:Boaco_00_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Boaco_00_10` | `wsINETER-DGOT:Boaco_00_10Type` |

### `wsINETER-DGOT:Cambio_Cobertura_2000_2005`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `Uso_2000` | `xsd:string` |
| `Uso_2005` | `xsd:string` |
| `Depart` | `xsd:string` |
| `Area Ha` | `xsd:double` |
| `Area Km2` | `xsd:double` |
| `Cambio_Cobertura_2000_2005` | `wsINETER-DGOT:Cambio_Cobertura_2000_2005Type` |

### `wsINETER-DGOT:Carazo00_05`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Carazo00_05` | `wsINETER-DGOT:Carazo00_05Type` |

### `wsINETER-DGOT:Carazo00_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Carazo00_15` | `wsINETER-DGOT:Carazo00_15Type` |

### `wsINETER-DGOT:Carazo00_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Carazo00_18` | `wsINETER-DGOT:Carazo00_18Type` |

### `wsINETER-DGOT:Carazo05_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Carazo05_10` | `wsINETER-DGOT:Carazo05_10Type` |

### `wsINETER-DGOT:Carazo05_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Carazo05_15` | `wsINETER-DGOT:Carazo05_15Type` |

### `wsINETER-DGOT:Carazo05_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Carazo05_18` | `wsINETER-DGOT:Carazo05_18Type` |

### `wsINETER-DGOT:Carazo10_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Carazo10_15` | `wsINETER-DGOT:Carazo10_15Type` |

### `wsINETER-DGOT:Carazo10_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Carazo10_18` | `wsINETER-DGOT:Carazo10_18Type` |

### `wsINETER-DGOT:Carazo15_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Carazo15_18` | `wsINETER-DGOT:Carazo15_18Type` |

### `wsINETER-DGOT:Carazo_00_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Carazo_00_10` | `wsINETER-DGOT:Carazo_00_10Type` |

### `wsINETER-DGOT:Cauces`

> [!warning] Schema pendente; validar antes de uso.

### `wsINETER-DGOT:Chinandega00_05`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Chinandega00_05` | `wsINETER-DGOT:Chinandega00_05Type` |

### `wsINETER-DGOT:Chinandega00_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Chinandega00_15` | `wsINETER-DGOT:Chinandega00_15Type` |

### `wsINETER-DGOT:Chinandega00_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Chinandega00_18` | `wsINETER-DGOT:Chinandega00_18Type` |

### `wsINETER-DGOT:Chinandega05_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Chinandega05_10` | `wsINETER-DGOT:Chinandega05_10Type` |

### `wsINETER-DGOT:Chinandega05_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Chinandega05_15` | `wsINETER-DGOT:Chinandega05_15Type` |

### `wsINETER-DGOT:Chinandega05_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Chinandega05_18` | `wsINETER-DGOT:Chinandega05_18Type` |

### `wsINETER-DGOT:Chinandega10_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Chinandega10_15` | `wsINETER-DGOT:Chinandega10_15Type` |

### `wsINETER-DGOT:Chinandega10_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Chinandega10_18` | `wsINETER-DGOT:Chinandega10_18Type` |

### `wsINETER-DGOT:Chinandega15_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Chinandega15_18` | `wsINETER-DGOT:Chinandega15_18Type` |

### `wsINETER-DGOT:Chinandega_00_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Chinandega_00_10` | `wsINETER-DGOT:Chinandega_00_10Type` |

### `wsINETER-DGOT:Chontales00_05`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Chontales00_05` | `wsINETER-DGOT:Chontales00_05Type` |

### `wsINETER-DGOT:Chontales00_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Chontales00_15` | `wsINETER-DGOT:Chontales00_15Type` |

### `wsINETER-DGOT:Chontales00_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Chontales00_18` | `wsINETER-DGOT:Chontales00_18Type` |

### `wsINETER-DGOT:Chontales05_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Chontales05_10` | `wsINETER-DGOT:Chontales05_10Type` |

### `wsINETER-DGOT:Chontales05_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Chontales05_15` | `wsINETER-DGOT:Chontales05_15Type` |

### `wsINETER-DGOT:Chontales05_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Chontales05_18` | `wsINETER-DGOT:Chontales05_18Type` |

### `wsINETER-DGOT:Chontales10_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Chontales10_15` | `wsINETER-DGOT:Chontales10_15Type` |

### `wsINETER-DGOT:Chontales10_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Chontales10_18` | `wsINETER-DGOT:Chontales10_18Type` |

### `wsINETER-DGOT:Chontales15_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Chontales15_18` | `wsINETER-DGOT:Chontales15_18Type` |

### `wsINETER-DGOT:Chontales_00_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Chontales_00_10` | `wsINETER-DGOT:Chontales_00_10Type` |

### `wsINETER-DGOT:Cobertura_uso2000`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `area` | `xsd:string` |
| `Cobertura_uso2000` | `wsINETER-DGOT:Cobertura_uso2000Type` |

### `wsINETER-DGOT:Cobertura_uso2005`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `area` | `xsd:string` |
| `Cobertura_uso2005` | `wsINETER-DGOT:Cobertura_uso2005Type` |

### `wsINETER-DGOT:Cobertura_uso2010`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `area` | `xsd:string` |
| `Cobertura_uso2010` | `wsINETER-DGOT:Cobertura_uso2010Type` |

### `wsINETER-DGOT:Cobertura_uso2015`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `area` | `xsd:string` |
| `Cobertura_uso2015` | `wsINETER-DGOT:Cobertura_uso2015Type` |

### `wsINETER-DGOT:Cobertura_uso2018`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `area` | `xsd:string` |
| `Cobertura_uso2018` | `wsINETER-DGOT:Cobertura_uso2018Type` |

### `wsINETER-DGOT:Coberturauso2000`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2000` | `wsINETER-DGOT:Coberturauso2000Type` |

### `wsINETER-DGOT:Coberturauso2000_Agua`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2000_Agua` | `wsINETER-DGOT:Coberturauso2000_AguaType` |

### `wsINETER-DGOT:Coberturauso2000_Boaco`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2000_Boaco` | `wsINETER-DGOT:Coberturauso2000_BoacoType` |

### `wsINETER-DGOT:Coberturauso2000_Carazo`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2000_Carazo` | `wsINETER-DGOT:Coberturauso2000_CarazoType` |

### `wsINETER-DGOT:Coberturauso2000_Chinandega`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2000_Chinandega` | `wsINETER-DGOT:Coberturauso2000_ChinandegaType` |

### `wsINETER-DGOT:Coberturauso2000_Chontales`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2000_Chontales` | `wsINETER-DGOT:Coberturauso2000_ChontalesType` |

### `wsINETER-DGOT:Coberturauso2000_Esteli`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2000_Esteli` | `wsINETER-DGOT:Coberturauso2000_EsteliType` |

### `wsINETER-DGOT:Coberturauso2000_Granada`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2000_Granada` | `wsINETER-DGOT:Coberturauso2000_GranadaType` |

### `wsINETER-DGOT:Coberturauso2000_Jinotega`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2000_Jinotega` | `wsINETER-DGOT:Coberturauso2000_JinotegaType` |

### `wsINETER-DGOT:Coberturauso2000_Leon`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2000_Leon` | `wsINETER-DGOT:Coberturauso2000_LeonType` |

### `wsINETER-DGOT:Coberturauso2000_Madriz`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2000_Madriz` | `wsINETER-DGOT:Coberturauso2000_MadrizType` |

### `wsINETER-DGOT:Coberturauso2000_Managua`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2000_Managua` | `wsINETER-DGOT:Coberturauso2000_ManaguaType` |

### `wsINETER-DGOT:Coberturauso2000_Masaya`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2000_Masaya` | `wsINETER-DGOT:Coberturauso2000_MasayaType` |

### `wsINETER-DGOT:Coberturauso2000_Matagalpa`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2000_Matagalpa` | `wsINETER-DGOT:Coberturauso2000_MatagalpaType` |

### `wsINETER-DGOT:Coberturauso2000_Nueva_Segovia`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2000_Nueva_Segovia` | `wsINETER-DGOT:Coberturauso2000_Nueva_SegoviaType` |

### `wsINETER-DGOT:Coberturauso2000_RACCN`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2000_RACCN` | `wsINETER-DGOT:Coberturauso2000_RACCNType` |

### `wsINETER-DGOT:Coberturauso2000_RACCS`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2000_RACCS` | `wsINETER-DGOT:Coberturauso2000_RACCSType` |

### `wsINETER-DGOT:Coberturauso2000_Rio_San_Juan`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2000_Rio_San_Juan` | `wsINETER-DGOT:Coberturauso2000_Rio_San_JuanType` |

### `wsINETER-DGOT:Coberturauso2000_Rivas`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2000_Rivas` | `wsINETER-DGOT:Coberturauso2000_RivasType` |

### `wsINETER-DGOT:Coberturauso2005`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2005` | `wsINETER-DGOT:Coberturauso2005Type` |

### `wsINETER-DGOT:Coberturauso2005_Agua`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2005_Agua` | `wsINETER-DGOT:Coberturauso2005_AguaType` |

### `wsINETER-DGOT:Coberturauso2005_Boaco`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2005_Boaco` | `wsINETER-DGOT:Coberturauso2005_BoacoType` |

### `wsINETER-DGOT:Coberturauso2005_Carazo`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2005_Carazo` | `wsINETER-DGOT:Coberturauso2005_CarazoType` |

### `wsINETER-DGOT:Coberturauso2005_Chinandega`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2005_Chinandega` | `wsINETER-DGOT:Coberturauso2005_ChinandegaType` |

### `wsINETER-DGOT:Coberturauso2005_Chontales`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2005_Chontales` | `wsINETER-DGOT:Coberturauso2005_ChontalesType` |

### `wsINETER-DGOT:Coberturauso2005_Esteli`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2005_Esteli` | `wsINETER-DGOT:Coberturauso2005_EsteliType` |

### `wsINETER-DGOT:Coberturauso2005_Granada`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2005_Granada` | `wsINETER-DGOT:Coberturauso2005_GranadaType` |

### `wsINETER-DGOT:Coberturauso2005_Jinotega`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2005_Jinotega` | `wsINETER-DGOT:Coberturauso2005_JinotegaType` |

### `wsINETER-DGOT:Coberturauso2005_Leon`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2005_Leon` | `wsINETER-DGOT:Coberturauso2005_LeonType` |

### `wsINETER-DGOT:Coberturauso2005_Madriz`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2005_Madriz` | `wsINETER-DGOT:Coberturauso2005_MadrizType` |

### `wsINETER-DGOT:Coberturauso2005_Managua`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2005_Managua` | `wsINETER-DGOT:Coberturauso2005_ManaguaType` |

### `wsINETER-DGOT:Coberturauso2005_Masaya`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2005_Masaya` | `wsINETER-DGOT:Coberturauso2005_MasayaType` |

### `wsINETER-DGOT:Coberturauso2005_Matagalpa`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2005_Matagalpa` | `wsINETER-DGOT:Coberturauso2005_MatagalpaType` |

### `wsINETER-DGOT:Coberturauso2005_Nueva_Segovia`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2005_Nueva_Segovia` | `wsINETER-DGOT:Coberturauso2005_Nueva_SegoviaType` |

### `wsINETER-DGOT:Coberturauso2005_RACCN`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2005_RACCN` | `wsINETER-DGOT:Coberturauso2005_RACCNType` |

### `wsINETER-DGOT:Coberturauso2005_RACCS`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2005_RACCS` | `wsINETER-DGOT:Coberturauso2005_RACCSType` |

### `wsINETER-DGOT:Coberturauso2005_Rio_San_Juan`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2005_Rio_San_Juan` | `wsINETER-DGOT:Coberturauso2005_Rio_San_JuanType` |

### `wsINETER-DGOT:Coberturauso2005_Rivas`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2005_Rivas` | `wsINETER-DGOT:Coberturauso2005_RivasType` |

### `wsINETER-DGOT:Coberturauso2010`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2010` | `wsINETER-DGOT:Coberturauso2010Type` |

### `wsINETER-DGOT:Coberturauso2010_Agua`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2010_Agua` | `wsINETER-DGOT:Coberturauso2010_AguaType` |

### `wsINETER-DGOT:Coberturauso2010_Boaco`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2010_Boaco` | `wsINETER-DGOT:Coberturauso2010_BoacoType` |

### `wsINETER-DGOT:Coberturauso2010_Carazo`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2010_Carazo` | `wsINETER-DGOT:Coberturauso2010_CarazoType` |

### `wsINETER-DGOT:Coberturauso2010_Chinandega`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2010_Chinandega` | `wsINETER-DGOT:Coberturauso2010_ChinandegaType` |

### `wsINETER-DGOT:Coberturauso2010_Chontales`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2010_Chontales` | `wsINETER-DGOT:Coberturauso2010_ChontalesType` |

### `wsINETER-DGOT:Coberturauso2010_Esteli`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2010_Esteli` | `wsINETER-DGOT:Coberturauso2010_EsteliType` |

### `wsINETER-DGOT:Coberturauso2010_Granada`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2010_Granada` | `wsINETER-DGOT:Coberturauso2010_GranadaType` |

### `wsINETER-DGOT:Coberturauso2010_Jinotega`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2010_Jinotega` | `wsINETER-DGOT:Coberturauso2010_JinotegaType` |

### `wsINETER-DGOT:Coberturauso2010_Leon`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2010_Leon` | `wsINETER-DGOT:Coberturauso2010_LeonType` |

### `wsINETER-DGOT:Coberturauso2010_Madriz`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2010_Madriz` | `wsINETER-DGOT:Coberturauso2010_MadrizType` |

### `wsINETER-DGOT:Coberturauso2010_Managua`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2010_Managua` | `wsINETER-DGOT:Coberturauso2010_ManaguaType` |

### `wsINETER-DGOT:Coberturauso2010_Masaya`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2010_Masaya` | `wsINETER-DGOT:Coberturauso2010_MasayaType` |

### `wsINETER-DGOT:Coberturauso2010_Matagalpa`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2010_Matagalpa` | `wsINETER-DGOT:Coberturauso2010_MatagalpaType` |

### `wsINETER-DGOT:Coberturauso2010_Nueva_Segovia`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2010_Nueva_Segovia` | `wsINETER-DGOT:Coberturauso2010_Nueva_SegoviaType` |

### `wsINETER-DGOT:Coberturauso2010_RACCN`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2010_RACCN` | `wsINETER-DGOT:Coberturauso2010_RACCNType` |

### `wsINETER-DGOT:Coberturauso2010_RACCS`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2010_RACCS` | `wsINETER-DGOT:Coberturauso2010_RACCSType` |

### `wsINETER-DGOT:Coberturauso2010_Rio_San_Juan`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2010_Rio_San_Juan` | `wsINETER-DGOT:Coberturauso2010_Rio_San_JuanType` |

### `wsINETER-DGOT:Coberturauso2010_Rivas`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2010_Rivas` | `wsINETER-DGOT:Coberturauso2010_RivasType` |

### `wsINETER-DGOT:Coberturauso2015`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2015` | `wsINETER-DGOT:Coberturauso2015Type` |

### `wsINETER-DGOT:Coberturauso2015_Agua`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2015_Agua` | `wsINETER-DGOT:Coberturauso2015_AguaType` |

### `wsINETER-DGOT:Coberturauso2015_Boaco`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2015_Boaco` | `wsINETER-DGOT:Coberturauso2015_BoacoType` |

### `wsINETER-DGOT:Coberturauso2015_Carazo`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2015_Carazo` | `wsINETER-DGOT:Coberturauso2015_CarazoType` |

### `wsINETER-DGOT:Coberturauso2015_Chinandega`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2015_Chinandega` | `wsINETER-DGOT:Coberturauso2015_ChinandegaType` |

### `wsINETER-DGOT:Coberturauso2015_Chontales`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2015_Chontales` | `wsINETER-DGOT:Coberturauso2015_ChontalesType` |

### `wsINETER-DGOT:Coberturauso2015_Esteli`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2015_Esteli` | `wsINETER-DGOT:Coberturauso2015_EsteliType` |

### `wsINETER-DGOT:Coberturauso2015_Granada`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2015_Granada` | `wsINETER-DGOT:Coberturauso2015_GranadaType` |

### `wsINETER-DGOT:Coberturauso2015_Jinotega`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2015_Jinotega` | `wsINETER-DGOT:Coberturauso2015_JinotegaType` |

### `wsINETER-DGOT:Coberturauso2015_Leon`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2015_Leon` | `wsINETER-DGOT:Coberturauso2015_LeonType` |

### `wsINETER-DGOT:Coberturauso2015_Madriz`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2015_Madriz` | `wsINETER-DGOT:Coberturauso2015_MadrizType` |

### `wsINETER-DGOT:Coberturauso2015_Managua`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2015_Managua` | `wsINETER-DGOT:Coberturauso2015_ManaguaType` |

### `wsINETER-DGOT:Coberturauso2015_Masaya`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2015_Masaya` | `wsINETER-DGOT:Coberturauso2015_MasayaType` |

### `wsINETER-DGOT:Coberturauso2015_Matagalpa`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2015_Matagalpa` | `wsINETER-DGOT:Coberturauso2015_MatagalpaType` |

### `wsINETER-DGOT:Coberturauso2015_Nueva_Segovia`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2015_Nueva_Segovia` | `wsINETER-DGOT:Coberturauso2015_Nueva_SegoviaType` |

### `wsINETER-DGOT:Coberturauso2015_RACCN`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2015_RACCN` | `wsINETER-DGOT:Coberturauso2015_RACCNType` |

### `wsINETER-DGOT:Coberturauso2015_RACCS`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2015_RACCS` | `wsINETER-DGOT:Coberturauso2015_RACCSType` |

### `wsINETER-DGOT:Coberturauso2015_Rio_San_Juan`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2015_Rio_San_Juan` | `wsINETER-DGOT:Coberturauso2015_Rio_San_JuanType` |

### `wsINETER-DGOT:Coberturauso2015_Rivas`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2015_Rivas` | `wsINETER-DGOT:Coberturauso2015_RivasType` |

### `wsINETER-DGOT:Coberturauso2018`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2018` | `wsINETER-DGOT:Coberturauso2018Type` |

### `wsINETER-DGOT:Coberturauso2018_Agua`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2018_Agua` | `wsINETER-DGOT:Coberturauso2018_AguaType` |

### `wsINETER-DGOT:Coberturauso2018_Boaco`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2018_Boaco` | `wsINETER-DGOT:Coberturauso2018_BoacoType` |

### `wsINETER-DGOT:Coberturauso2018_Carazo`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2018_Carazo` | `wsINETER-DGOT:Coberturauso2018_CarazoType` |

### `wsINETER-DGOT:Coberturauso2018_Chinandega`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2018_Chinandega` | `wsINETER-DGOT:Coberturauso2018_ChinandegaType` |

### `wsINETER-DGOT:Coberturauso2018_Chontales`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2018_Chontales` | `wsINETER-DGOT:Coberturauso2018_ChontalesType` |

### `wsINETER-DGOT:Coberturauso2018_Esteli`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2018_Esteli` | `wsINETER-DGOT:Coberturauso2018_EsteliType` |

### `wsINETER-DGOT:Coberturauso2018_Granada`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2018_Granada` | `wsINETER-DGOT:Coberturauso2018_GranadaType` |

### `wsINETER-DGOT:Coberturauso2018_Jinotega`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2018_Jinotega` | `wsINETER-DGOT:Coberturauso2018_JinotegaType` |

### `wsINETER-DGOT:Coberturauso2018_Leon`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2018_Leon` | `wsINETER-DGOT:Coberturauso2018_LeonType` |

### `wsINETER-DGOT:Coberturauso2018_Madriz`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2018_Madriz` | `wsINETER-DGOT:Coberturauso2018_MadrizType` |

### `wsINETER-DGOT:Coberturauso2018_Managua`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2018_Managua` | `wsINETER-DGOT:Coberturauso2018_ManaguaType` |

### `wsINETER-DGOT:Coberturauso2018_Masaya`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2018_Masaya` | `wsINETER-DGOT:Coberturauso2018_MasayaType` |

### `wsINETER-DGOT:Coberturauso2018_Matagalpa`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2018_Matagalpa` | `wsINETER-DGOT:Coberturauso2018_MatagalpaType` |

### `wsINETER-DGOT:Coberturauso2018_Nueva_Segovia`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2018_Nueva_Segovia` | `wsINETER-DGOT:Coberturauso2018_Nueva_SegoviaType` |

### `wsINETER-DGOT:Coberturauso2018_RACCN`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2018_RACCN` | `wsINETER-DGOT:Coberturauso2018_RACCNType` |

### `wsINETER-DGOT:Coberturauso2018_RACCS`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2018_RACCS` | `wsINETER-DGOT:Coberturauso2018_RACCSType` |

### `wsINETER-DGOT:Coberturauso2018_Rio_San_Juan`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2018_Rio_San_Juan` | `wsINETER-DGOT:Coberturauso2018_Rio_San_JuanType` |

### `wsINETER-DGOT:Coberturauso2018_Rivas`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `concept` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `area` | `xsd:string` |
| `kilometros` | `xsd:string` |
| `Coberturauso2018_Rivas` | `wsINETER-DGOT:Coberturauso2018_RivasType` |

### `wsINETER-DGOT:Coberturauso2020_Boaco`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `ha` | `xsd:double` |
| `descripcion` | `xsd:string` |
| `Coberturauso2020_Boaco` | `wsINETER-DGOT:Coberturauso2020_BoacoType` |

### `wsINETER-DGOT:Coberturauso2020_Carazo`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `ha` | `xsd:double` |
| `descripcion` | `xsd:string` |
| `Coberturauso2020_Carazo` | `wsINETER-DGOT:Coberturauso2020_CarazoType` |

### `wsINETER-DGOT:Coberturauso2020_Chinandega`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `ha` | `xsd:double` |
| `descripcion` | `xsd:string` |
| `Coberturauso2020_Chinandega` | `wsINETER-DGOT:Coberturauso2020_ChinandegaType` |

### `wsINETER-DGOT:Coberturauso2020_Chontales`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `ha` | `xsd:double` |
| `descripcion` | `xsd:string` |
| `Coberturauso2020_Chontales` | `wsINETER-DGOT:Coberturauso2020_ChontalesType` |

### `wsINETER-DGOT:Coberturauso2020_Esteli`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `ha` | `xsd:double` |
| `descripcion` | `xsd:string` |
| `Coberturauso2020_Esteli` | `wsINETER-DGOT:Coberturauso2020_EsteliType` |

### `wsINETER-DGOT:Coberturauso2020_Granada`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `ha` | `xsd:double` |
| `descripcion` | `xsd:string` |
| `Coberturauso2020_Granada` | `wsINETER-DGOT:Coberturauso2020_GranadaType` |

### `wsINETER-DGOT:Coberturauso2020_Jinotega`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `ha` | `xsd:double` |
| `descripcion` | `xsd:string` |
| `Coberturauso2020_Jinotega` | `wsINETER-DGOT:Coberturauso2020_JinotegaType` |

### `wsINETER-DGOT:Coberturauso2020_Leon`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `ha` | `xsd:double` |
| `descripcion` | `xsd:string` |
| `Coberturauso2020_Leon` | `wsINETER-DGOT:Coberturauso2020_LeonType` |

### `wsINETER-DGOT:Coberturauso2020_Madriz`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `ha` | `xsd:double` |
| `descripcion` | `xsd:string` |
| `Coberturauso2020_Madriz` | `wsINETER-DGOT:Coberturauso2020_MadrizType` |

### `wsINETER-DGOT:Coberturauso2020_Managua`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `ha` | `xsd:double` |
| `descripcion` | `xsd:string` |
| `Coberturauso2020_Managua` | `wsINETER-DGOT:Coberturauso2020_ManaguaType` |

### `wsINETER-DGOT:Coberturauso2020_Masaya`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `ha` | `xsd:double` |
| `descripcion` | `xsd:string` |
| `Coberturauso2020_Masaya` | `wsINETER-DGOT:Coberturauso2020_MasayaType` |

### `wsINETER-DGOT:Coberturauso2020_Matagalpa`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `ha` | `xsd:double` |
| `descripcion` | `xsd:string` |
| `Coberturauso2020_Matagalpa` | `wsINETER-DGOT:Coberturauso2020_MatagalpaType` |

### `wsINETER-DGOT:Coberturauso2020_NuevaSegovia`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `ha` | `xsd:double` |
| `descripcion` | `xsd:string` |
| `Coberturauso2020_NuevaSegovia` | `wsINETER-DGOT:Coberturauso2020_NuevaSegoviaType` |

### `wsINETER-DGOT:Coberturauso2020_RACCN`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `ha` | `xsd:double` |
| `descripcion` | `xsd:string` |
| `Coberturauso2020_RACCN` | `wsINETER-DGOT:Coberturauso2020_RACCNType` |

### `wsINETER-DGOT:Coberturauso2020_RACCS`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `ha` | `xsd:double` |
| `descripcion` | `xsd:string` |
| `Coberturauso2020_RACCS` | `wsINETER-DGOT:Coberturauso2020_RACCSType` |

### `wsINETER-DGOT:Coberturauso2020_RioSanJuan`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `ha` | `xsd:double` |
| `descripcion` | `xsd:string` |
| `Coberturauso2020_RioSanJuan` | `wsINETER-DGOT:Coberturauso2020_RioSanJuanType` |

### `wsINETER-DGOT:Coberturauso2020_Rivas`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `ha` | `xsd:double` |
| `descripcion` | `xsd:string` |
| `Coberturauso2020_Rivas` | `wsINETER-DGOT:Coberturauso2020_RivasType` |

### `wsINETER-DGOT:comunidades_inide`

> [!warning] Schema pendente; validar antes de uso.

### `wsINETER-DGOT:cruce_cobertura00_05_mala`

> [!warning] Schema pendente; validar antes de uso.

### `wsINETER-DGOT:Cruce_Cobertura_2000_2005`

| Campo | Tipo |
|---|---|
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:decimal` |
| `fid_cobe_1` | `xsd:decimal` |
| `usos2005` | `xsd:string` |
| `orig_fid_1` | `xsd:decimal` |
| `m2` | `xsd:decimal` |
| `ha` | `xsd:decimal` |
| `km2` | `xsd:decimal` |
| `departamento` | `xsd:string` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `Cruce_Cobertura_2000_2005` | `wsINETER-DGOT:Cruce_Cobertura_2000_2005Type` |

### `wsINETER-DGOT:Cruce_Cobertura_2000_2010`

| Campo | Tipo |
|---|---|
| `id` | `xsd:double` |
| `fid_cobert` | `xsd:decimal` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:decimal` |
| `fid_cobe_1` | `xsd:decimal` |
| `usos2010` | `xsd:string` |
| `orig_fid_1` | `xsd:decimal` |
| `m2` | `xsd:decimal` |
| `ha` | `xsd:decimal` |
| `km2` | `xsd:decimal` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamento` | `xsd:string` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `Cruce_Cobertura_2000_2010` | `wsINETER-DGOT:Cruce_Cobertura_2000_2010Type` |

### `wsINETER-DGOT:Cruce_Cobertura_2000_2015`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fid_cobert` | `xsd:long` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:long` |
| `fid_cobe_1` | `xsd:long` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:long` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamento` | `xsd:string` |
| `Cruce_Cobertura_2000_2015` | `wsINETER-DGOT:Cruce_Cobertura_2000_2015Type` |

### `wsINETER-DGOT:Cruce_Cobertura_2000_2018`

| Campo | Tipo |
|---|---|
| `id` | `xsd:double` |
| `fid_cobert` | `xsd:decimal` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:decimal` |
| `usos2018` | `xsd:string` |
| `orig_fid_1` | `xsd:decimal` |
| `m2` | `xsd:decimal` |
| `ha` | `xsd:decimal` |
| `km2` | `xsd:decimal` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamento` | `xsd:string` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `Cruce_Cobertura_2000_2018` | `wsINETER-DGOT:Cruce_Cobertura_2000_2018Type` |

### `wsINETER-DGOT:Cruce_Cobertura_2005_2010`

| Campo | Tipo |
|---|---|
| `id` | `xsd:double` |
| `fid` | `xsd:decimal` |
| `fid_cobert` | `xsd:decimal` |
| `usos2005` | `xsd:string` |
| `fid_cobe_1` | `xsd:decimal` |
| `usos2010` | `xsd:string` |
| `m2` | `xsd:decimal` |
| `ha` | `xsd:decimal` |
| `km2` | `xsd:decimal` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamento` | `xsd:string` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `Cruce_Cobertura_2005_2010` | `wsINETER-DGOT:Cruce_Cobertura_2005_2010Type` |

### `wsINETER-DGOT:Cruce_Cobertura_2005_2015`

| Campo | Tipo |
|---|---|
| `id` | `xsd:double` |
| `fid_cobert` | `xsd:decimal` |
| `usos2005` | `xsd:string` |
| `orig_fid` | `xsd:decimal` |
| `usos2015` | `xsd:string` |
| `orig_fid_1` | `xsd:decimal` |
| `m2` | `xsd:decimal` |
| `ha` | `xsd:decimal` |
| `km2` | `xsd:decimal` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamento` | `xsd:string` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `Cruce_Cobertura_2005_2015` | `wsINETER-DGOT:Cruce_Cobertura_2005_2015Type` |

### `wsINETER-DGOT:Cruce_Cobertura_2005_2018`

| Campo | Tipo |
|---|---|
| `id` | `xsd:double` |
| `fid_cobert` | `xsd:decimal` |
| `usos2005` | `xsd:string` |
| `ha` | `xsd:decimal` |
| `km2` | `xsd:decimal` |
| `usos2018` | `xsd:string` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamento` | `xsd:string` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `Cruce_Cobertura_2005_2018` | `wsINETER-DGOT:Cruce_Cobertura_2005_2018Type` |

### `wsINETER-DGOT:Cruce_Cobertura_2010_2015`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `fid_cobert` | `xsd:long` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:long` |
| `uso2015` | `xsd:string` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamento` | `xsd:string` |
| `Cruce_Cobertura_2010_2015` | `wsINETER-DGOT:Cruce_Cobertura_2010_2015Type` |

### `wsINETER-DGOT:Cruce_Cobertura_2010_2018`

| Campo | Tipo |
|---|---|
| `id` | `xsd:double` |
| `fid_cobert` | `xsd:decimal` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:decimal` |
| `km2` | `xsd:decimal` |
| `fid_cobe_1` | `xsd:decimal` |
| `uso2018` | `xsd:string` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamento` | `xsd:string` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `Cruce_Cobertura_2010_2018` | `wsINETER-DGOT:Cruce_Cobertura_2010_2018Type` |

### `wsINETER-DGOT:Cruce_Cobertura_2015_2018`

| Campo | Tipo |
|---|---|
| `id` | `xsd:double` |
| `fid_cobert` | `xsd:decimal` |
| `usos2015` | `xsd:string` |
| `ha` | `xsd:decimal` |
| `km2` | `xsd:decimal` |
| `fid_cobe_1` | `xsd:decimal` |
| `usos2018` | `xsd:string` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamento` | `xsd:string` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `Cruce_Cobertura_2015_2018` | `wsINETER-DGOT:Cruce_Cobertura_2015_2018Type` |

### `wsINETER-DGOT:CruceCobertura00_05`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `Usos2000` | `xsd:string` |
| `ORIG_FID` | `xsd:long` |
| `FID_Cobe_1` | `xsd:long` |
| `Uso2005` | `xsd:string` |
| `ORIG_FID_1` | `xsd:long` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `CruceCobertura00_05` | `wsINETER-DGOT:CruceCobertura00_05Type` |

### `wsINETER-DGOT:CuencaApanas4326`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `gridcode` | `xsd:long` |
| `AREAKM` | `xsd:double` |
| `PerimKm` | `xsd:double` |
| `LengthWate` | `xsd:double` |
| `MeanWidth` | `xsd:double` |
| `CompactFac` | `xsd:double` |
| `CirculaRat` | `xsd:double` |
| `EnlogRatio` | `xsd:double` |
| `FormFactor` | `xsd:double` |
| `HighPoint` | `xsd:double` |
| `LowPoint` | `xsd:double` |
| `ReliefKm` | `xsd:double` |
| `MeanEleva` | `xsd:double` |
| `MeanSlope` | `xsd:double` |
| `Percen_b30` | `xsd:double` |
| `MassCoeff` | `xsd:double` |
| `OroCoeff` | `xsd:double` |
| `LengthChan` | `xsd:double` |
| `ShapeW` | `xsd:double` |
| `DrainageDe` | `xsd:double` |
| `ConstChaMa` | `xsd:double` |
| `AveLes` | `xsd:double` |
| `MeltonRati` | `xsd:double` |
| `ReliefRati` | `xsd:double` |
| `Shape_Leng` | `xsd:double` |
| `Shape_Area` | `xsd:double` |
| `CuencaApanas4326` | `wsINETER-DGOT:CuencaApanas4326Type` |

### `wsINETER-DGOT:Cultivos_Agridescanso_2016`

| Campo | Tipo |
|---|---|
| `uso_2016` | `xsd:string` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `Cultivos_Agridescanso_2016` | `wsINETER-DGOT:Cultivos_Agridescanso_2016Type` |

### `wsINETER-DGOT:Cultivos_Ajonjoli_2016`

| Campo | Tipo |
|---|---|
| `uso_2016` | `xsd:string` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `Cultivos_Ajonjoli_2016` | `wsINETER-DGOT:Cultivos_Ajonjoli_2016Type` |

### `wsINETER-DGOT:Cultivos_Arrozriego_2016`

| Campo | Tipo |
|---|---|
| `uso_2016` | `xsd:string` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `Cultivos_Arrozriego_2016` | `wsINETER-DGOT:Cultivos_Arrozriego_2016Type` |

### `wsINETER-DGOT:Cultivos_Arrozsecano_2016`

| Campo | Tipo |
|---|---|
| `uso_2016` | `xsd:string` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `Cultivos_Arrozsecano_2016` | `wsINETER-DGOT:Cultivos_Arrozsecano_2016Type` |

### `wsINETER-DGOT:Cultivos_Cacao_2016`

| Campo | Tipo |
|---|---|
| `uso_2016` | `xsd:string` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `Cultivos_Cacao_2016` | `wsINETER-DGOT:Cultivos_Cacao_2016Type` |

### `wsINETER-DGOT:Cultivos_Cafesinsombra_2016`

| Campo | Tipo |
|---|---|
| `uso_2016` | `xsd:string` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `Cultivos_Cafesinsombra_2016` | `wsINETER-DGOT:Cultivos_Cafesinsombra_2016Type` |

### `wsINETER-DGOT:Cultivos_Cafesombra_2016`

| Campo | Tipo |
|---|---|
| `uso_2016` | `xsd:string` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `Cultivos_Cafesombra_2016` | `wsINETER-DGOT:Cultivos_Cafesombra_2016Type` |

### `wsINETER-DGOT:Cultivos_Canaazucar_2016`

| Campo | Tipo |
|---|---|
| `uso_2016` | `xsd:string` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `Cultivos_Canaazucar_2016` | `wsINETER-DGOT:Cultivos_Canaazucar_2016Type` |

### `wsINETER-DGOT:Cultivos_Citricos_2016`

| Campo | Tipo |
|---|---|
| `uso_2016` | `xsd:string` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `Cultivos_Citricos_2016` | `wsINETER-DGOT:Cultivos_Citricos_2016Type` |

### `wsINETER-DGOT:Cultivos_Frutales_2016`

| Campo | Tipo |
|---|---|
| `uso_2016` | `xsd:string` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `Cultivos_Frutales_2016` | `wsINETER-DGOT:Cultivos_Frutales_2016Type` |

### `wsINETER-DGOT:Cultivos_Granosbasicos_2016`

| Campo | Tipo |
|---|---|
| `uso_2016` | `xsd:string` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `Cultivos_Granosbasicos_2016` | `wsINETER-DGOT:Cultivos_Granosbasicos_2016Type` |

### `wsINETER-DGOT:Cultivos_Hortraituber_2016`

| Campo | Tipo |
|---|---|
| `uso_2016` | `xsd:string` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `Cultivos_Hortraituber_2016` | `wsINETER-DGOT:Cultivos_Hortraituber_2016Type` |

### `wsINETER-DGOT:Cultivos_Mani_2016`

| Campo | Tipo |
|---|---|
| `uso_2016` | `xsd:string` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `Cultivos_Mani_2016` | `wsINETER-DGOT:Cultivos_Mani_2016Type` |

### `wsINETER-DGOT:Cultivos_Musaceas_2016`

| Campo | Tipo |
|---|---|
| `uso_2016` | `xsd:string` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `Cultivos_Musaceas_2016` | `wsINETER-DGOT:Cultivos_Musaceas_2016Type` |

### `wsINETER-DGOT:Cultivos_Palmaaceitera_2016`

| Campo | Tipo |
|---|---|
| `uso_2016` | `xsd:string` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `Cultivos_Palmaaceitera_2016` | `wsINETER-DGOT:Cultivos_Palmaaceitera_2016Type` |

### `wsINETER-DGOT:Cultivos_Sorgoindustrial_2016`

| Campo | Tipo |
|---|---|
| `uso_2016` | `xsd:string` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `Cultivos_Sorgoindustrial_2016` | `wsINETER-DGOT:Cultivos_Sorgoindustrial_2016Type` |

### `wsINETER-DGOT:Cultivos_Tabaco_2016`

| Campo | Tipo |
|---|---|
| `uso_2016` | `xsd:string` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `Cultivos_Tabaco_2016` | `wsINETER-DGOT:Cultivos_Tabaco_2016Type` |

### `wsINETER-DGOT:Esteli00_05`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Esteli00_05` | `wsINETER-DGOT:Esteli00_05Type` |

### `wsINETER-DGOT:Esteli00_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Esteli00_15` | `wsINETER-DGOT:Esteli00_15Type` |

### `wsINETER-DGOT:Esteli00_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Esteli00_18` | `wsINETER-DGOT:Esteli00_18Type` |

### `wsINETER-DGOT:Esteli05_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Esteli05_10` | `wsINETER-DGOT:Esteli05_10Type` |

### `wsINETER-DGOT:Esteli05_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Esteli05_15` | `wsINETER-DGOT:Esteli05_15Type` |

### `wsINETER-DGOT:Esteli05_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Esteli05_18` | `wsINETER-DGOT:Esteli05_18Type` |

### `wsINETER-DGOT:Esteli10_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Esteli10_18` | `wsINETER-DGOT:Esteli10_18Type` |

### `wsINETER-DGOT:Esteli15_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Esteli15_18` | `wsINETER-DGOT:Esteli15_18Type` |

### `wsINETER-DGOT:Esteli_00_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Esteli_00_10` | `wsINETER-DGOT:Esteli_00_10Type` |

### `wsINETER-DGOT:Esteli_10_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Esteli_10_15` | `wsINETER-DGOT:Esteli_10_15Type` |

### `wsINETER-DGOT:Granada00_05`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Granada00_05` | `wsINETER-DGOT:Granada00_05Type` |

### `wsINETER-DGOT:Granada00_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Granada00_15` | `wsINETER-DGOT:Granada00_15Type` |

### `wsINETER-DGOT:Granada00_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Granada00_18` | `wsINETER-DGOT:Granada00_18Type` |

### `wsINETER-DGOT:Granada05_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Granada05_10` | `wsINETER-DGOT:Granada05_10Type` |

### `wsINETER-DGOT:Granada05_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Granada05_15` | `wsINETER-DGOT:Granada05_15Type` |

### `wsINETER-DGOT:Granada05_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Granada05_18` | `wsINETER-DGOT:Granada05_18Type` |

### `wsINETER-DGOT:Granada10_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Granada10_18` | `wsINETER-DGOT:Granada10_18Type` |

### `wsINETER-DGOT:Granada15_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Granada15_18` | `wsINETER-DGOT:Granada15_18Type` |

### `wsINETER-DGOT:Granada_00_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Granada_00_10` | `wsINETER-DGOT:Granada_00_10Type` |

### `wsINETER-DGOT:Granada_10_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Granada_10_15` | `wsINETER-DGOT:Granada_10_15Type` |

### `wsINETER-DGOT:Jinotega00_05`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Jinotega00_05` | `wsINETER-DGOT:Jinotega00_05Type` |

### `wsINETER-DGOT:Jinotega00_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Jinotega00_15` | `wsINETER-DGOT:Jinotega00_15Type` |

### `wsINETER-DGOT:Jinotega00_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Jinotega00_18` | `wsINETER-DGOT:Jinotega00_18Type` |

### `wsINETER-DGOT:Jinotega05_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Jinotega05_10` | `wsINETER-DGOT:Jinotega05_10Type` |

### `wsINETER-DGOT:Jinotega05_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Jinotega05_15` | `wsINETER-DGOT:Jinotega05_15Type` |

### `wsINETER-DGOT:Jinotega05_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Jinotega05_18` | `wsINETER-DGOT:Jinotega05_18Type` |

### `wsINETER-DGOT:Jinotega10_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Jinotega10_18` | `wsINETER-DGOT:Jinotega10_18Type` |

### `wsINETER-DGOT:Jinotega_00_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Jinotega_00_10` | `wsINETER-DGOT:Jinotega_00_10Type` |

### `wsINETER-DGOT:Jinotega_10_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Jinotega_10_15` | `wsINETER-DGOT:Jinotega_10_15Type` |

### `wsINETER-DGOT:Jinotega_15_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Jinotega_15_18` | `wsINETER-DGOT:Jinotega_15_18Type` |

### `wsINETER-DGOT:Leon00_05`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Leon00_05` | `wsINETER-DGOT:Leon00_05Type` |

### `wsINETER-DGOT:Leon00_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Leon00_15` | `wsINETER-DGOT:Leon00_15Type` |

### `wsINETER-DGOT:Leon00_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Leon00_18` | `wsINETER-DGOT:Leon00_18Type` |

### `wsINETER-DGOT:Leon05_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Leon05_10` | `wsINETER-DGOT:Leon05_10Type` |

### `wsINETER-DGOT:Leon05_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Leon05_15` | `wsINETER-DGOT:Leon05_15Type` |

### `wsINETER-DGOT:Leon05_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Leon05_18` | `wsINETER-DGOT:Leon05_18Type` |

### `wsINETER-DGOT:Leon10_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Leon10_18` | `wsINETER-DGOT:Leon10_18Type` |

### `wsINETER-DGOT:Leon15_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Leon15_18` | `wsINETER-DGOT:Leon15_18Type` |

### `wsINETER-DGOT:Leon_00_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Leon_00_10` | `wsINETER-DGOT:Leon_00_10Type` |

### `wsINETER-DGOT:Leon_10_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Leon_10_15` | `wsINETER-DGOT:Leon_10_15Type` |

### `wsINETER-DGOT:Levantamiento_Cultivos1718`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `cultivo` | `xsd:string` |
| `agcultivo` | `xsd:string` |
| `epoca` | `xsd:string` |
| `cod_pts` | `xsd:string` |
| `aã±o` | `xsd:double` |
| `Levantamiento_Cultivos1718` | `wsINETER-DGOT:Levantamiento_Cultivos1718Type` |

### `wsINETER-DGOT:Limites_Comunidades`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `id_unico` | `xsd:string` |
| `depto` | `xsd:string` |
| `municipio` | `xsd:string` |
| `id_mun` | `xsd:double` |
| `id_com` | `xsd:double` |
| `area_ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `comun` | `xsd:string` |
| `Limites_Comunidades` | `wsINETER-DGOT:Limites_ComunidadesType` |

### `wsINETER-DGOT:Limites_Comunidades2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `id_unico` | `xsd:string` |
| `depto` | `xsd:string` |
| `municipio` | `xsd:string` |
| `id_mun` | `xsd:double` |
| `id_com` | `xsd:double` |
| `area_ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `comun` | `xsd:string` |
| `Limites_Comunidades2022` | `wsINETER-DGOT:Limites_Comunidades2022Type` |

### `wsINETER-DGOT:Madriz00_05`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Madriz00_05` | `wsINETER-DGOT:Madriz00_05Type` |

### `wsINETER-DGOT:Madriz00_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Madriz00_15` | `wsINETER-DGOT:Madriz00_15Type` |

### `wsINETER-DGOT:Madriz00_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Madriz00_18` | `wsINETER-DGOT:Madriz00_18Type` |

### `wsINETER-DGOT:Madriz05_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Madriz05_10` | `wsINETER-DGOT:Madriz05_10Type` |

### `wsINETER-DGOT:Madriz05_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Madriz05_15` | `wsINETER-DGOT:Madriz05_15Type` |

### `wsINETER-DGOT:Madriz05_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Madriz05_18` | `wsINETER-DGOT:Madriz05_18Type` |

### `wsINETER-DGOT:Madriz10_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Madriz10_18` | `wsINETER-DGOT:Madriz10_18Type` |

### `wsINETER-DGOT:Madriz15_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Madriz15_18` | `wsINETER-DGOT:Madriz15_18Type` |

### `wsINETER-DGOT:Madriz_00_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Madriz_00_10` | `wsINETER-DGOT:Madriz_00_10Type` |

### `wsINETER-DGOT:Madriz_10_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Madriz_10_15` | `wsINETER-DGOT:Madriz_10_15Type` |

### `wsINETER-DGOT:Managua00_05`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Managua00_05` | `wsINETER-DGOT:Managua00_05Type` |

### `wsINETER-DGOT:Managua00_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Managua00_15` | `wsINETER-DGOT:Managua00_15Type` |

### `wsINETER-DGOT:Managua00_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Managua00_18` | `wsINETER-DGOT:Managua00_18Type` |

### `wsINETER-DGOT:Managua05_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Managua05_10` | `wsINETER-DGOT:Managua05_10Type` |

### `wsINETER-DGOT:Managua05_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Managua05_15` | `wsINETER-DGOT:Managua05_15Type` |

### `wsINETER-DGOT:Managua05_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Managua05_18` | `wsINETER-DGOT:Managua05_18Type` |

### `wsINETER-DGOT:Managua10_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Managua10_18` | `wsINETER-DGOT:Managua10_18Type` |

### `wsINETER-DGOT:Managua15_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Managua15_18` | `wsINETER-DGOT:Managua15_18Type` |

### `wsINETER-DGOT:Managua_00_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Managua_00_10` | `wsINETER-DGOT:Managua_00_10Type` |

### `wsINETER-DGOT:Managua_10_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Managua_10_15` | `wsINETER-DGOT:Managua_10_15Type` |

### `wsINETER-DGOT:Masaya00_05`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Masaya00_05` | `wsINETER-DGOT:Masaya00_05Type` |

### `wsINETER-DGOT:Masaya00_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Masaya00_15` | `wsINETER-DGOT:Masaya00_15Type` |

### `wsINETER-DGOT:Masaya00_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Masaya00_18` | `wsINETER-DGOT:Masaya00_18Type` |

### `wsINETER-DGOT:Masaya05_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Masaya05_10` | `wsINETER-DGOT:Masaya05_10Type` |

### `wsINETER-DGOT:Masaya05_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Masaya05_15` | `wsINETER-DGOT:Masaya05_15Type` |

### `wsINETER-DGOT:Masaya05_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Masaya05_18` | `wsINETER-DGOT:Masaya05_18Type` |

### `wsINETER-DGOT:Masaya10_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Masaya10_18` | `wsINETER-DGOT:Masaya10_18Type` |

### `wsINETER-DGOT:Masaya15_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Masaya15_18` | `wsINETER-DGOT:Masaya15_18Type` |

### `wsINETER-DGOT:Masaya_00_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Masaya_00_10` | `wsINETER-DGOT:Masaya_00_10Type` |

### `wsINETER-DGOT:Masaya_10_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Masaya_10_15` | `wsINETER-DGOT:Masaya_10_15Type` |

### `wsINETER-DGOT:Matagalpa00_05`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Matagalpa00_05` | `wsINETER-DGOT:Matagalpa00_05Type` |

### `wsINETER-DGOT:Matagalpa00_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Matagalpa00_15` | `wsINETER-DGOT:Matagalpa00_15Type` |

### `wsINETER-DGOT:Matagalpa00_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Matagalpa00_18` | `wsINETER-DGOT:Matagalpa00_18Type` |

### `wsINETER-DGOT:Matagalpa05_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Matagalpa05_10` | `wsINETER-DGOT:Matagalpa05_10Type` |

### `wsINETER-DGOT:Matagalpa05_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Matagalpa05_15` | `wsINETER-DGOT:Matagalpa05_15Type` |

### `wsINETER-DGOT:Matagalpa05_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Matagalpa05_18` | `wsINETER-DGOT:Matagalpa05_18Type` |

### `wsINETER-DGOT:Matagalpa10_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Matagalpa10_18` | `wsINETER-DGOT:Matagalpa10_18Type` |

### `wsINETER-DGOT:Matagalpa15_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Matagalpa15_18` | `wsINETER-DGOT:Matagalpa15_18Type` |

### `wsINETER-DGOT:Matagalpa_00_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Matagalpa_00_10` | `wsINETER-DGOT:Matagalpa_00_10Type` |

### `wsINETER-DGOT:Matagalpa_10_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Matagalpa_10_15` | `wsINETER-DGOT:Matagalpa_10_15Type` |

### `wsINETER-DGOT:Nacional_Apante1819`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `dpto` | `xsd:string` |
| `code_muni` | `xsd:string` |
| `muni` | `xsd:string` |
| `capante19` | `xsd:string` |
| `agapante19` | `xsd:string` |
| `mz` | `xsd:double` |
| `ha` | `xsd:double` |
| `Nacional_Apante1819` | `wsINETER-DGOT:Nacional_Apante1819Type` |

### `wsINETER-DGOT:Nacional_Postrera19`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `ha` | `xsd:double` |
| `mz` | `xsd:double` |
| `agpostre19` | `xsd:string` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `cpostrer19` | `xsd:string` |
| `Nacional_Postrera19` | `wsINETER-DGOT:Nacional_Postrera19Type` |

### `wsINETER-DGOT:Nacional_Primera19`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `dpto` | `xsd:string` |
| `code_muni` | `xsd:string` |
| `muni` | `xsd:string` |
| `cprimera19` | `xsd:string` |
| `agprimer19` | `xsd:string` |
| `area_ha` | `xsd:double` |
| `area_mz` | `xsd:double` |
| `Nacional_Primera19` | `wsINETER-DGOT:Nacional_Primera19Type` |

### `wsINETER-DGOT:Nuevasegovia00_05`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Nuevasegovia00_05` | `wsINETER-DGOT:Nuevasegovia00_05Type` |

### `wsINETER-DGOT:NuevaSegovia00_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `NuevaSegovia00_15` | `wsINETER-DGOT:NuevaSegovia00_15Type` |

### `wsINETER-DGOT:NuevaSegovia00_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `NuevaSegovia00_18` | `wsINETER-DGOT:NuevaSegovia00_18Type` |

### `wsINETER-DGOT:NuevaSegovia05_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `NuevaSegovia05_10` | `wsINETER-DGOT:NuevaSegovia05_10Type` |

### `wsINETER-DGOT:NuevaSegovia05_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `NuevaSegovia05_15` | `wsINETER-DGOT:NuevaSegovia05_15Type` |

### `wsINETER-DGOT:NuevaSegovia05_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `NuevaSegovia05_18` | `wsINETER-DGOT:NuevaSegovia05_18Type` |

### `wsINETER-DGOT:NuevaSegovia10_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `NuevaSegovia10_18` | `wsINETER-DGOT:NuevaSegovia10_18Type` |

### `wsINETER-DGOT:NuevaSegovia15_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `NuevaSegovia15_18` | `wsINETER-DGOT:NuevaSegovia15_18Type` |

### `wsINETER-DGOT:NuevaSegovia_00_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `NuevaSegovia_00_10` | `wsINETER-DGOT:NuevaSegovia_00_10Type` |

### `wsINETER-DGOT:NuevaSegovia_10_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `NuevaSegovia_10_15` | `wsINETER-DGOT:NuevaSegovia_10_15Type` |

### `wsINETER-DGOT:Postrera16_20`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `agrup16_20` | `xsd:string` |
| `Postrera16_20` | `wsINETER-DGOT:Postrera16_20Type` |

### `wsINETER-DGOT:Postrera_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `fid_postre` | `xsd:long` |
| `cpostre20` | `xsd:string` |
| `ha` | `xsd:double` |
| `mz` | `xsd:double` |
| `agrupculti` | `xsd:string` |
| `rubros` | `xsd:string` |
| `destinocul` | `xsd:string` |
| `id_unico_1` | `xsd:string` |
| `depto` | `xsd:string` |
| `municipio` | `xsd:string` |
| `id_mun` | `xsd:double` |
| `id_com` | `xsd:double` |
| `area_ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `comun` | `xsd:string` |
| `fid_depart` | `xsd:long` |
| `objectid_1` | `xsd:long` |
| `clase` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_le_1` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `Postrera_2022` | `wsINETER-DGOT:Postrera_2022Type` |

### `wsINETER-DGOT:Primera16_20`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `dpto` | `xsd:string` |
| `muni` | `xsd:string` |
| `agrup16_20` | `xsd:string` |
| `Primera16_20` | `wsINETER-DGOT:Primera16_20Type` |

### `wsINETER-DGOT:Primera_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `fid_primer` | `xsd:long` |
| `cprimera20` | `xsd:string` |
| `ha` | `xsd:double` |
| `mz` | `xsd:double` |
| `agrupculti` | `xsd:string` |
| `rubros` | `xsd:string` |
| `destinocul` | `xsd:string` |
| `id_unico_1` | `xsd:string` |
| `depto` | `xsd:string` |
| `municipio` | `xsd:string` |
| `id_mun` | `xsd:double` |
| `id_com` | `xsd:double` |
| `area_ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `comun` | `xsd:string` |
| `clase` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `Primera_2022` | `wsINETER-DGOT:Primera_2022Type` |

### `wsINETER-DGOT:Puntos_CalorNasa`

| Campo | Tipo |
|---|---|
| `idpuntocalor` | `xsd:int` |
| `geom` | `gml:PointPropertyType` |
| `country_id` | `xsd:string` |
| `latitude` | `xsd:double` |
| `longitude` | `xsd:double` |
| `bright_ti4` | `xsd:float` |
| `bright_ti4_c` | `xsd:float` |
| `bright_ti5` | `xsd:float` |
| `bright_ti5_c` | `xsd:float` |
| `scan` | `xsd:double` |
| `track` | `xsd:double` |
| `acq_date` | `xsd:dateTime` |
| `acq_time` | `xsd:int` |
| `satellite` | `xsd:string` |
| `instrument` | `xsd:string` |
| `confidence` | `xsd:string` |
| `version` | `xsd:string` |
| `frp` | `xsd:double` |
| `daynight` | `xsd:string` |
| `fecha` | `xsd:dateTime` |
| `departamento` | `xsd:string` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `cobertura` | `xsd:string` |
| `Puntos_CalorNasa` | `wsINETER-DGOT:Puntos_CalorNasaType` |

### `wsINETER-DGOT:puntoscalor`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `country_id` | `xsd:string` |
| `latitude` | `xsd:double` |
| `longitude` | `xsd:double` |
| `bright_ti4` | `xsd:double` |
| `scan` | `xsd:double` |
| `track` | `xsd:double` |
| `acq_date` | `xsd:dateTime` |
| `acq_time` | `xsd:int` |
| `satellite` | `xsd:string` |
| `instrument` | `xsd:string` |
| `confidence` | `xsd:string` |
| `version` | `xsd:string` |
| `bright_ti5` | `xsd:double` |
| `frp` | `xsd:double` |
| `daynight` | `xsd:string` |
| `fecha` | `xsd:dateTime` |
| `departamento` | `xsd:string` |
| `municipio` | `xsd:string` |
| `cobertura` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `bright_ti4_c` | `xsd:double` |
| `bright_ti5_c` | `xsd:double` |
| `puntoscalor` | `wsINETER-DGOT:puntoscalorType` |

### `wsINETER-DGOT:Puntoscalor_dash`

| Campo | Tipo |
|---|---|
| `idpuntocalor` | `xsd:int` |
| `geom` | `gml:PointPropertyType` |
| `latitude` | `xsd:double` |
| `longitude` | `xsd:double` |
| `bright_ti4` | `xsd:double` |
| `scan` | `xsd:double` |
| `track` | `xsd:double` |
| `acq_date` | `xsd:dateTime` |
| `acq_time` | `xsd:int` |
| `satellite` | `xsd:string` |
| `instrument` | `xsd:string` |
| `confidence` | `xsd:string` |
| `version` | `xsd:string` |
| `bright_ti5` | `xsd:double` |
| `frp` | `xsd:double` |
| `daynight` | `xsd:string` |
| `fecha` | `xsd:string` |
| `departamento` | `xsd:string` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `cobertura` | `xsd:string` |
| `bright_ti4_c` | `xsd:double` |
| `bright_ti5_c` | `xsd:double` |
| `Puntoscalor_dash` | `wsINETER-DGOT:Puntoscalor_dashType` |

### `wsINETER-DGOT:Raan00_05`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Raan00_05` | `wsINETER-DGOT:Raan00_05Type` |

### `wsINETER-DGOT:Raan_00_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Raan_00_10` | `wsINETER-DGOT:Raan_00_10Type` |

### `wsINETER-DGOT:Raas00_05`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Raas00_05` | `wsINETER-DGOT:Raas00_05Type` |

### `wsINETER-DGOT:Raas_00_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Raas_00_10` | `wsINETER-DGOT:Raas_00_10Type` |

### `wsINETER-DGOT:RACCN00_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `RACCN00_15` | `wsINETER-DGOT:RACCN00_15Type` |

### `wsINETER-DGOT:RACCN00_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `RACCN00_18` | `wsINETER-DGOT:RACCN00_18Type` |

### `wsINETER-DGOT:RACCN05_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `RACCN05_10` | `wsINETER-DGOT:RACCN05_10Type` |

### `wsINETER-DGOT:RACCN05_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `RACCN05_15` | `wsINETER-DGOT:RACCN05_15Type` |

### `wsINETER-DGOT:RACCN05_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `RACCN05_18` | `wsINETER-DGOT:RACCN05_18Type` |

### `wsINETER-DGOT:RACCN10_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `RACCN10_18` | `wsINETER-DGOT:RACCN10_18Type` |

### `wsINETER-DGOT:RACCN2015_2018`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `RACCN2015_2018` | `wsINETER-DGOT:RACCN2015_2018Type` |

### `wsINETER-DGOT:RACCN_10_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `RACCN_10_15` | `wsINETER-DGOT:RACCN_10_15Type` |

### `wsINETER-DGOT:RACCS00_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `RACCS00_15` | `wsINETER-DGOT:RACCS00_15Type` |

### `wsINETER-DGOT:RACCS00_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `RACCS00_18` | `wsINETER-DGOT:RACCS00_18Type` |

### `wsINETER-DGOT:RACCS05_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `RACCS05_10` | `wsINETER-DGOT:RACCS05_10Type` |

### `wsINETER-DGOT:RACCS05_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `RACCS05_15` | `wsINETER-DGOT:RACCS05_15Type` |

### `wsINETER-DGOT:RACCS05_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `RACCS05_18` | `wsINETER-DGOT:RACCS05_18Type` |

### `wsINETER-DGOT:RACCS10_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `RACCS10_18` | `wsINETER-DGOT:RACCS10_18Type` |

### `wsINETER-DGOT:RACCS15_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `RACCS15_18` | `wsINETER-DGOT:RACCS15_18Type` |

### `wsINETER-DGOT:RACCS_10_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `RACCS_10_15` | `wsINETER-DGOT:RACCS_10_15Type` |

### `wsINETER-DGOT:Reserva_Biosfera_OT`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `area` | `xsd:double` |
| `perimeter` | `xsd:double` |
| `nombre` | `xsd:string` |
| `categor` | `xsd:string` |
| `categoria_` | `xsd:string` |
| `decreto_cr` | `xsd:long` |
| `año_del_d` | `xsd:string` |
| `region` | `xsd:string` |
| `hectares` | `xsd:double` |
| `numero` | `xsd:double` |
| `zonas` | `xsd:string` |
| `clafic` | `xsd:string` |
| `Reserva_Biosfera_OT` | `wsINETER-DGOT:Reserva_Biosfera_OTType` |

### `wsINETER-DGOT:Rio_SanJuan15_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Rio_SanJuan15_18` | `wsINETER-DGOT:Rio_SanJuan15_18Type` |

### `wsINETER-DGOT:Riosanjuan00_05`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Riosanjuan00_05` | `wsINETER-DGOT:Riosanjuan00_05Type` |

### `wsINETER-DGOT:RioSanJuan00_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `RioSanJuan00_15` | `wsINETER-DGOT:RioSanJuan00_15Type` |

### `wsINETER-DGOT:RioSanJuan00_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `RioSanJuan00_18` | `wsINETER-DGOT:RioSanJuan00_18Type` |

### `wsINETER-DGOT:RioSanJuan05_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `RioSanJuan05_10` | `wsINETER-DGOT:RioSanJuan05_10Type` |

### `wsINETER-DGOT:RioSanJuan05_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `RioSanJuan05_15` | `wsINETER-DGOT:RioSanJuan05_15Type` |

### `wsINETER-DGOT:RioSanJuan05_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `RioSanJuan05_18` | `wsINETER-DGOT:RioSanJuan05_18Type` |

### `wsINETER-DGOT:RioSanJuan10_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `RioSanJuan10_15` | `wsINETER-DGOT:RioSanJuan10_15Type` |

### `wsINETER-DGOT:RioSanJuan10_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `RioSanJuan10_18` | `wsINETER-DGOT:RioSanJuan10_18Type` |

### `wsINETER-DGOT:Riosanjuan_00_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Riosanjuan_00_10` | `wsINETER-DGOT:Riosanjuan_00_10Type` |

### `wsINETER-DGOT:Rivas00_05`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Rivas00_05` | `wsINETER-DGOT:Rivas00_05Type` |

### `wsINETER-DGOT:Rivas00_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Rivas00_15` | `wsINETER-DGOT:Rivas00_15Type` |

### `wsINETER-DGOT:Rivas00_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Rivas00_18` | `wsINETER-DGOT:Rivas00_18Type` |

### `wsINETER-DGOT:Rivas05_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Rivas05_10` | `wsINETER-DGOT:Rivas05_10Type` |

### `wsINETER-DGOT:Rivas05_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Rivas05_15` | `wsINETER-DGOT:Rivas05_15Type` |

### `wsINETER-DGOT:Rivas05_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2005` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Rivas05_18` | `wsINETER-DGOT:Rivas05_18Type` |

### `wsINETER-DGOT:Rivas10_15`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Rivas10_15` | `wsINETER-DGOT:Rivas10_15Type` |

### `wsINETER-DGOT:Rivas10_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Rivas10_18` | `wsINETER-DGOT:Rivas10_18Type` |

### `wsINETER-DGOT:Rivas15_18`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `uso2015` | `xsd:string` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2018` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `departamen` | `xsd:string` |
| `Rivas15_18` | `wsINETER-DGOT:Rivas15_18Type` |

### `wsINETER-DGOT:Rivas_00_10`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `fid_cobert` | `xsd:double` |
| `usos2000` | `xsd:string` |
| `orig_fid` | `xsd:double` |
| `fid_cobe_1` | `xsd:double` |
| `uso2010` | `xsd:string` |
| `orig_fid_1` | `xsd:double` |
| `m2` | `xsd:double` |
| `ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `Rivas_00_10` | `wsINETER-DGOT:Rivas_00_10Type` |

### `wsINETER-DGOT:Uso2018_agua`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `ha` | `xsd:double` |
| `clase` | `xsd:string` |
| `Uso2018_agua` | `wsINETER-DGOT:Uso2018_aguaType` |

### `wsINETER-DGOT:Uso2018_bosquelatifoliadoabierto`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `ha` | `xsd:double` |
| `clase` | `xsd:string` |
| `Uso2018_bosquelatifoliadoabierto` | `wsINETER-DGOT:Uso2018_bosquelatifoliadoabiertoType` |

### `wsINETER-DGOT:Uso2018_bosquelatiforeadocerrado`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `ha` | `xsd:double` |
| `clase` | `xsd:string` |
| `Uso2018_bosquelatiforeadocerrado` | `wsINETER-DGOT:Uso2018_bosquelatiforeadocerradoType` |

### `wsINETER-DGOT:Uso2018_bosquepalma`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `ha` | `xsd:double` |
| `clase` | `xsd:string` |
| `Uso2018_bosquepalma` | `wsINETER-DGOT:Uso2018_bosquepalmaType` |

### `wsINETER-DGOT:Uso2018_bosquepinoabierto`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `ha` | `xsd:double` |
| `clase` | `xsd:string` |
| `Uso2018_bosquepinoabierto` | `wsINETER-DGOT:Uso2018_bosquepinoabiertoType` |

### `wsINETER-DGOT:Uso2018_bosquepinocerrado`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `ha` | `xsd:double` |
| `clase` | `xsd:string` |
| `Uso2018_bosquepinocerrado` | `wsINETER-DGOT:Uso2018_bosquepinocerradoType` |

### `wsINETER-DGOT:Uso2018_centropoblados`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `ha` | `xsd:double` |
| `clase` | `xsd:string` |
| `Uso2018_centropoblados` | `wsINETER-DGOT:Uso2018_centropobladosType` |

### `wsINETER-DGOT:Uso2018_cultivosanuales`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `ha` | `xsd:double` |
| `clase` | `xsd:string` |
| `Uso2018_cultivosanuales` | `wsINETER-DGOT:Uso2018_cultivosanualesType` |

### `wsINETER-DGOT:Uso2018_cultivosperennes`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `ha` | `xsd:double` |
| `clase` | `xsd:string` |
| `Uso2018_cultivosperennes` | `wsINETER-DGOT:Uso2018_cultivosperennesType` |

### `wsINETER-DGOT:Uso2018_manglar`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `ha` | `xsd:double` |
| `clase` | `xsd:string` |
| `Uso2018_manglar` | `wsINETER-DGOT:Uso2018_manglarType` |

### `wsINETER-DGOT:uso2018_pasto`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `ha` | `xsd:double` |
| `clase` | `xsd:string` |
| `uso2018_pasto` | `wsINETER-DGOT:uso2018_pastoType` |

### `wsINETER-DGOT:Uso2018_sabananatural`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `ha` | `xsd:double` |
| `clase` | `xsd:string` |
| `Uso2018_sabananatural` | `wsINETER-DGOT:Uso2018_sabananaturalType` |

### `wsINETER-DGOT:Uso2018_suselosinvegeta`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `ha` | `xsd:double` |
| `clase` | `xsd:string` |
| `Uso2018_suselosinvegeta` | `wsINETER-DGOT:Uso2018_suselosinvegetaType` |

### `wsINETER-DGOT:Uso2018_tacotal`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `ha` | `xsd:double` |
| `clase` | `xsd:string` |
| `Uso2018_tacotal` | `wsINETER-DGOT:Uso2018_tacotalType` |

### `wsINETER-DGOT:Uso2018_tierrasinundacion`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `ha` | `xsd:double` |
| `clase` | `xsd:string` |
| `Uso2018_tierrasinundacion` | `wsINETER-DGOT:Uso2018_tierrasinundacionType` |

### `wsINETER-DGOT:Uso2018_vegetacionarbustia`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `ha` | `xsd:double` |
| `clase` | `xsd:string` |
| `Uso2018_vegetacionarbustia` | `wsINETER-DGOT:Uso2018_vegetacionarbustiaType` |

### `wsINETER-DGOT:Uso2018_vegetacionherbacea`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `id` | `xsd:long` |
| `objectid` | `xsd:long` |
| `ha` | `xsd:double` |
| `clase` | `xsd:string` |
| `Uso2018_vegetacionherbacea` | `wsINETER-DGOT:Uso2018_vegetacionherbaceaType` |

### `wsINETER-DGOT:Uso_Potencial_2015`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `gridcode` | `xsd:decimal` |
| `code_upot` | `xsd:string` |
| `leye_upot` | `xsd:string` |
| `leyenda` | `xsd:string` |
| `Uso_Potencial_2015` | `wsINETER-DGOT:Uso_Potencial_2015Type` |

### `wsINETER-DGOT:Uso_Suelo2000`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `clasesipcc` | `xsd:string` |
| `Uso_Suelo2000` | `wsINETER-DGOT:Uso_Suelo2000Type` |

### `wsINETER-DGOT:Uso_Suelo2005`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `objectid_1` | `xsd:long` |
| `grid_code` | `xsd:long` |
| `clases_uso` | `xsd:string` |
| `km2_1` | `xsd:double` |
| `clave` | `xsd:string` |
| `ha` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_le_1` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `classgral` | `xsd:string` |
| `Uso_Suelo2005` | `wsINETER-DGOT:Uso_Suelo2005Type` |

### `wsINETER-DGOT:Uso_Suelo2010`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `gridcode` | `xsd:long` |
| `descrip` | `xsd:string` |
| `calsesipcc` | `xsd:string` |
| `Uso_Suelo2010` | `wsINETER-DGOT:Uso_Suelo2010Type` |

### `wsINETER-DGOT:Uso_Suelo2015`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `clase` | `xsd:string` |
| `ha` | `xsd:double` |
| `km` | `xsd:double` |
| `Uso_Suelo2015` | `wsINETER-DGOT:Uso_Suelo2015Type` |

### `wsINETER-DGOT:UsoActual2018`

| Campo | Tipo |
|---|---|
| `the_geom` | `gml:MultiSurfacePropertyType` |
| `OBJECTID` | `xsd:long` |
| `Ha` | `xsd:double` |
| `clase` | `xsd:string` |
| `UsoActual2018` | `wsINETER-DGOT:UsoActual2018Type` |

### `wsINETER-DGOT:v_adopcion`

| Campo | Tipo |
|---|---|
| `st_setsrid` | `gml:GeometryPropertyType` |
| `idadopcion` | `xsd:int` |
| `escuela` | `xsd:string` |
| `cantidadarbolesadoptados` | `xsd:int` |
| `cantidadprotagonistaninas` | `xsd:int` |
| `creadopor` | `xsd:string` |
| `direccionadopcion` | `xsd:string` |
| `codigoadopcion` | `xsd:string` |
| `fechaadopcion` | `xsd:date` |
| `semana` | `xsd:int` |
| `institucion` | `xsd:string` |
| `fechacaptura` | `xsd:dateTime` |
| `idcomunidad` | `xsd:int` |
| `cantidadprotagonistaninos` | `xsd:int` |
| `ubicacionimagen` | `xsd:string` |
| `descripcionimagen` | `xsd:string` |
| `cantidadforestal` | `xsd:int` |
| `cantidadornamental` | `xsd:int` |
| `cantidadfrutal` | `xsd:int` |
| `cantidadotrasplantas` | `xsd:int` |
| `latitud` | `xsd:decimal` |
| `longitud` | `xsd:decimal` |
| `primeraetapa` | `xsd:boolean` |
| `nombredepartamento` | `xsd:string` |
| `v_adopcion` | `wsINETER-DGOT:v_adopcionType` |

### `wsINETER-DGOT:v_capacitacion`

| Campo | Tipo |
|---|---|
| `st_setsrid` | `gml:GeometryPropertyType` |
| `idcapacitacion` | `xsd:int` |
| `fechacapacitacion` | `xsd:date` |
| `cantidadprotagonistamujeres` | `xsd:int` |
| `tematica` | `xsd:string` |
| `sitiocapacitacion` | `xsd:string` |
| `observacion` | `xsd:string` |
| `creadopor` | `xsd:string` |
| `semana` | `xsd:int` |
| `direccioncapacitacion` | `xsd:string` |
| `codigocapacitacion` | `xsd:string` |
| `fechacaptura` | `xsd:dateTime` |
| `institucion` | `xsd:string` |
| `cantidadprotagonistahombres` | `xsd:int` |
| `ubicacionimagen` | `xsd:string` |
| `descripcionimagen` | `xsd:string` |
| `latitud` | `xsd:decimal` |
| `longitud` | `xsd:decimal` |
| `primeraetapa` | `xsd:boolean` |
| `nombredepartamento` | `xsd:string` |
| `v_capacitacion` | `wsINETER-DGOT:v_capacitacionType` |

### `wsINETER-DGOT:v_entrega`

| Campo | Tipo |
|---|---|
| `st_setsrid` | `gml:GeometryPropertyType` |
| `identrega` | `xsd:int` |
| `fechaentrega` | `xsd:date` |
| `cantidadforestal` | `xsd:int` |
| `cantidadornamental` | `xsd:int` |
| `cantidadfrutal` | `xsd:int` |
| `entregadopor` | `xsd:string` |
| `recibidopor` | `xsd:string` |
| `fechacaptura` | `xsd:dateTime` |
| `creadopor` | `xsd:string` |
| `cantidadprotagonistamujeres` | `xsd:int` |
| `semana` | `xsd:int` |
| `sitioentrega` | `xsd:string` |
| `direccionentrega` | `xsd:string` |
| `codigoentrega` | `xsd:string` |
| `institucion` | `xsd:string` |
| `cantidadprotagonistahombres` | `xsd:int` |
| `ubicacionimagen` | `xsd:string` |
| `descripcionimagen` | `xsd:string` |
| `latitud` | `xsd:decimal` |
| `longitud` | `xsd:decimal` |
| `primeraetapa` | `xsd:boolean` |
| `propositoarbol` | `xsd:string` |
| `nombredepartamento` | `xsd:string` |
| `v_entrega` | `wsINETER-DGOT:v_entregaType` |

### `wsINETER-DGOT:v_plantacion`

| Campo | Tipo |
|---|---|
| `st_setsrid` | `gml:GeometryPropertyType` |
| `idjornada` | `xsd:int` |
| `fechajornada` | `xsd:date` |
| `cantidadforestal` | `xsd:int` |
| `cantidadornamental` | `xsd:int` |
| `cantidadfrutal` | `xsd:int` |
| `institucion` | `xsd:string` |
| `fechacaptura` | `xsd:dateTime` |
| `creadopor` | `xsd:string` |
| `cantidadprotagonistamujeres` | `xsd:int` |
| `semana` | `xsd:int` |
| `sitiojornada` | `xsd:string` |
| `direccionjornada` | `xsd:string` |
| `codigojornada` | `xsd:string` |
| `cantidadprotagonistahombres` | `xsd:int` |
| `ubicacionimagen` | `xsd:string` |
| `descripcionimagen` | `xsd:string` |
| `hectareaaproximada` | `xsd:decimal` |
| `latitud` | `xsd:decimal` |
| `longitud` | `xsd:decimal` |
| `primeraetapa` | `xsd:boolean` |
| `nombredepartamento` | `xsd:string` |
| `v_plantacion` | `wsINETER-DGOT:v_plantacionType` |

### `wsINETER-DGOT:v_puntoscalordash`

| Campo | Tipo |
|---|---|
| `idpuntocalor` | `xsd:int` |
| `geom` | `gml:PointPropertyType` |
| `latitude` | `xsd:double` |
| `longitude` | `xsd:double` |
| `bright_ti4` | `xsd:double` |
| `scan` | `xsd:double` |
| `track` | `xsd:double` |
| `acq_date` | `xsd:dateTime` |
| `acq_time` | `xsd:int` |
| `satellite` | `xsd:string` |
| `instrument` | `xsd:string` |
| `confidence` | `xsd:string` |
| `version` | `xsd:string` |
| `bright_ti5` | `xsd:double` |
| `frp` | `xsd:double` |
| `daynight` | `xsd:string` |
| `fecha` | `xsd:string` |
| `departamento` | `xsd:string` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `cobertura` | `xsd:string` |
| `bright_ti4_c` | `xsd:double` |
| `bright_ti5_c` | `xsd:double` |
| `v_puntoscalordash` | `wsINETER-DGOT:v_puntoscalordashType` |

### `wsINETER-DGOT:v_vivero`

| Campo | Tipo |
|---|---|
| `st_setsrid` | `gml:GeometryPropertyType` |
| `idvivero` | `xsd:int` |
| `fechacreacionvivero` | `xsd:date` |
| `cantidadforestal` | `xsd:int` |
| `cantidadornamental` | `xsd:int` |
| `cantidadhortaliza` | `xsd:int` |
| `cantidadfrutal` | `xsd:int` |
| `cantidadotrasplantas` | `xsd:int` |
| `cantidadfinalforestal` | `xsd:int` |
| `cantidadfinalornamental` | `xsd:int` |
| `cantidadfinalfrutal` | `xsd:int` |
| `area` | `xsd:decimal` |
| `responsable` | `xsd:string` |
| `tipovivero` | `xsd:string` |
| `creadopor` | `xsd:string` |
| `semana` | `xsd:int` |
| `sitiovivero` | `xsd:string` |
| `direccionvivero` | `xsd:string` |
| `codigovivero` | `xsd:string` |
| `fechacaptura` | `xsd:dateTime` |
| `institucion` | `xsd:string` |
| `ubicacionimagen` | `xsd:string` |
| `imagendescripcion` | `xsd:string` |
| `latitud` | `xsd:decimal` |
| `longitud` | `xsd:decimal` |
| `primeraetapa` | `xsd:boolean` |
| `nombredepartamento` | `xsd:string` |
| `v_vivero` | `wsINETER-DGOT:v_viveroType` |

### `wsINETER-DGRH:Acuiferos_2021`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `acuifero` | `xsd:string` |
| `redoh` | `xsd:int` |
| `z_msnm` | `xsd:int` |
| `nea_m` | `xsd:string` |
| `b_m_` | `xsd:string` |
| `t_m2_d` | `xsd:string` |
| `q_m3_d_m` | `xsd:string` |
| `s_adim` | `xsd:string` |
| `perimeter` | `xsd:double` |
| `area` | `xsd:double` |
| `leyenda` | `xsd:string` |
| `Acuiferos_2021` | `wsINETER-DGRH:Acuiferos_2021Type` |

### `wsINETER-DGRH:Acuiferos_2021-2`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `acuifero` | `xsd:string` |
| `redoh` | `xsd:int` |
| `z_msnm` | `xsd:int` |
| `nea_m` | `xsd:string` |
| `b_m_` | `xsd:string` |
| `t_m2_d` | `xsd:string` |
| `q_m3_d_m` | `xsd:string` |
| `s_adim` | `xsd:string` |
| `perimeter` | `xsd:double` |
| `area` | `xsd:double` |
| `leyenda` | `xsd:string` |
| `Acuiferos_2021-2` | `wsINETER-DGRH:Acuiferos_2021-2Type` |

### `wsINETER-DGRH:Acuiferos_Norte`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `acuifero` | `xsd:string` |
| `redoh` | `xsd:int` |
| `z_msnm` | `xsd:int` |
| `nea_m` | `xsd:string` |
| `b_m_` | `xsd:string` |
| `t_m2_d` | `xsd:string` |
| `q_m3_d_m` | `xsd:string` |
| `s_adim` | `xsd:string` |
| `perimeter` | `xsd:double` |
| `area` | `xsd:double` |
| `leyenda` | `xsd:string` |
| `max` | `xsd:string` |
| `min` | `xsd:string` |
| `prom` | `xsd:string` |
| `variacion` | `xsd:string` |
| `Acuiferos_Norte` | `wsINETER-DGRH:Acuiferos_NorteType` |

### `wsINETER-DGRH:Acuiferos_Norte-2`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `acuifero` | `xsd:string` |
| `redoh` | `xsd:int` |
| `z_msnm` | `xsd:int` |
| `nea_m` | `xsd:string` |
| `b_m_` | `xsd:string` |
| `t_m2_d` | `xsd:string` |
| `q_m3_d_m` | `xsd:string` |
| `s_adim` | `xsd:string` |
| `perimeter` | `xsd:double` |
| `area` | `xsd:double` |
| `leyenda` | `xsd:string` |
| `max` | `xsd:string` |
| `min` | `xsd:string` |
| `prom` | `xsd:string` |
| `variacion` | `xsd:string` |
| `Acuiferos_Norte-2` | `wsINETER-DGRH:Acuiferos_Norte-2Type` |

### `wsINETER-DGRH:Aforos_Ocotal`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `n` | `xsd:double` |
| `codigo` | `xsd:string` |
| `nombre` | `xsd:string` |
| `rio` | `xsd:string` |
| `tipo` | `xsd:string` |
| `longitud` | `xsd:string` |
| `latitud` | `xsd:string` |
| `longitud_x` | `xsd:double` |
| `latitud_y` | `xsd:double` |
| `long__x` | `xsd:double` |
| `lat__y` | `xsd:double` |
| `elevacion` | `xsd:double` |
| `area` | `xsd:double` |
| `n15` | `xsd:string` |
| `hoja` | `xsd:string` |
| `lugar` | `xsd:string` |
| `municipio` | `xsd:string` |
| `departamento` | `xsd:string` |
| `estado` | `xsd:string` |
| `Aforos_Ocotal` | `wsINETER-DGRH:Aforos_OcotalType` |

### `wsINETER-DGRH:Aforos_Ocotal-2`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `n` | `xsd:double` |
| `codigo` | `xsd:string` |
| `nombre` | `xsd:string` |
| `rio` | `xsd:string` |
| `tipo` | `xsd:string` |
| `longitud` | `xsd:string` |
| `latitud` | `xsd:string` |
| `longitud_x` | `xsd:double` |
| `latitud_y` | `xsd:double` |
| `long__x` | `xsd:double` |
| `lat__y` | `xsd:double` |
| `elevacion` | `xsd:double` |
| `area` | `xsd:double` |
| `n15` | `xsd:string` |
| `hoja` | `xsd:string` |
| `lugar` | `xsd:string` |
| `municipio` | `xsd:string` |
| `departamento` | `xsd:string` |
| `estado` | `xsd:string` |
| `Aforos_Ocotal-2` | `wsINETER-DGRH:Aforos_Ocotal-2Type` |

### `wsINETER-DGRH:Amenaza_Inundacion`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid_1` | `xsd:long` |
| `objectid` | `xsd:long` |
| `area` | `xsd:decimal` |
| `perimeter` | `xsd:decimal` |
| `shape_leng` | `xsd:decimal` |
| `shape_le_1` | `xsd:decimal` |
| `shape_area` | `xsd:decimal` |
| `area_km²` | `xsd:decimal` |
| `Amenaza_Inundacion` | `wsINETER-DGRH:Amenaza_InundacionType` |

### `wsINETER-DGRH:Amenaza_Inundacion-2`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid_1` | `xsd:long` |
| `objectid` | `xsd:long` |
| `area` | `xsd:decimal` |
| `perimeter` | `xsd:decimal` |
| `shape_leng` | `xsd:decimal` |
| `shape_le_1` | `xsd:decimal` |
| `shape_area` | `xsd:decimal` |
| `area_km²` | `xsd:decimal` |
| `Amenaza_Inundacion-2` | `wsINETER-DGRH:Amenaza_Inundacion-2Type` |

### `wsINETER-DGRH:Amenaza_Inundacion_Frecuente_Suelos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `inundac` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `Amenaza_Inundacion_Frecuente_Suelos` | `wsINETER-DGRH:Amenaza_Inundacion_Frecuente_SuelosType` |

### `wsINETER-DGRH:Amenaza_Inundacion_Frecuente_Suelos-2`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `inundac` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `Amenaza_Inundacion_Frecuente_Suelos-2` | `wsINETER-DGRH:Amenaza_Inundacion_Frecuente_Suelos-2Type` |

### `wsINETER-DGRH:Amenaza_Inundacion_Historica`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid_1` | `xsd:int` |
| `objectid` | `xsd:int` |
| `area` | `xsd:double` |
| `perimeter` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_le_1` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `area_km²` | `xsd:double` |
| `Amenaza_Inundacion_Historica` | `wsINETER-DGRH:Amenaza_Inundacion_HistoricaType` |

### `wsINETER-DGRH:Amenaza_Inundacion_Historica-2`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid_1` | `xsd:int` |
| `objectid` | `xsd:int` |
| `area` | `xsd:double` |
| `perimeter` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_le_1` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `area_km²` | `xsd:double` |
| `Amenaza_Inundacion_Historica-2` | `wsINETER-DGRH:Amenaza_Inundacion_Historica-2Type` |

### `wsINETER-DGRH:Amenazas_Inundacion_Ocasional_Suelos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `inundac` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `Amenazas_Inundacion_Ocasional_Suelos` | `wsINETER-DGRH:Amenazas_Inundacion_Ocasional_SuelosType` |

### `wsINETER-DGRH:Concesiones2010_2017`

> [!warning] Schema pendente; validar antes de uso.

### `wsINETER-DGRH:Cuaternario`

> [!warning] Schema pendente; validar antes de uso.

### `wsINETER-DGRH:Cuaternario_2004`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `lugar` | `xsd:string` |
| `formacion` | `xsd:string` |
| `a_km2` | `xsd:long` |
| `Cuaternario_2004` | `wsINETER-DGRH:Cuaternario_2004Type` |

### `wsINETER-DGRH:Cuenca_Nivel7`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `n3` | `xsd:string` |
| `n4` | `xsd:string` |
| `n5` | `xsd:string` |
| `n6` | `xsd:string` |
| `n7` | `xsd:string` |
| `phca` | `xsd:double` |
| `code_pfafs` | `xsd:double` |
| `cuencas` | `xsd:string` |
| `Cuenca_Nivel7` | `wsINETER-DGRH:Cuenca_Nivel7Type` |

### `wsINETER-DGRH:cuencas`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `n4` | `xsd:int` |
| `area_km2` | `xsd:double` |
| `codigo` | `xsd:int` |
| `cuencas` | `wsINETER-DGRH:cuencasType` |

### `wsINETER-DGRH:Cuencas_nivel7_2021`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `n3` | `xsd:string` |
| `n4` | `xsd:string` |
| `n5` | `xsd:string` |
| `n6` | `xsd:string` |
| `n7` | `xsd:string` |
| `phca` | `xsd:double` |
| `code_pfafs` | `xsd:double` |
| `cuencas` | `xsd:string` |
| `area` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `Cuencas_nivel7_2021` | `wsINETER-DGRH:Cuencas_nivel7_2021Type` |

### `wsINETER-DGRH:Cuerpos_Agua`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `tiposuperficie` | `xsd:string` |
| `area` | `xsd:string` |
| `Cuerpos_Agua` | `wsINETER-DGRH:Cuerpos_AguaType` |

### `wsINETER-DGRH:cuerposagua`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `nombre` | `xsd:string` |
| `tiposuperficie` | `xsd:string` |
| `area` | `xsd:decimal` |
| `cuerposagua` | `wsINETER-DGRH:cuerposaguaType` |

### `wsINETER-DGRH:Datos_Saturacion_Suelo`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `fechahora` | `xsd:dateTime` |
| `basin` | `xsd:int` |
| `map01` | `xsd:decimal` |
| `map03` | `xsd:decimal` |
| `map06` | `xsd:decimal` |
| `map24` | `xsd:decimal` |
| `gmap06` | `xsd:decimal` |
| `gmap24` | `xsd:decimal` |
| `asmu06` | `xsd:decimal` |
| `asml06` | `xsd:decimal` |
| `asmt06` | `xsd:decimal` |
| `ffg01` | `xsd:decimal` |
| `ffg03` | `xsd:decimal` |
| `ffg06` | `xsd:decimal` |
| `prevffg01` | `xsd:decimal` |
| `prevffg03` | `xsd:decimal` |
| `prevffg06` | `xsd:decimal` |
| `fmap01` | `xsd:decimal` |
| `fmap03` | `xsd:decimal` |
| `fmap06` | `xsd:decimal` |
| `ifft01` | `xsd:decimal` |
| `ifft03` | `xsd:decimal` |
| `ifft06` | `xsd:decimal` |
| `pfft01` | `xsd:decimal` |
| `pfft03` | `xsd:decimal` |
| `pfft06` | `xsd:decimal` |
| `ffft01` | `xsd:decimal` |
| `ffft03` | `xsd:decimal` |
| `ffft06` | `xsd:decimal` |
| `pet06` | `xsd:decimal` |
| `Datos_Saturacion_Suelo` | `wsINETER-DGRH:Datos_Saturacion_SueloType` |

### `wsINETER-DGRH:Delineacion_cuenca_parcoco_2020`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `n4` | `xsd:int` |
| `n5` | `xsd:int` |
| `n6` | `xsd:int` |
| `n3` | `xsd:int` |
| `nombre` | `xsd:string` |
| `área_km²` | `xsd:double` |
| `perimetro_` | `xsd:double` |
| `code_pfasf` | `xsd:int` |
| `Delineacion_cuenca_parcoco_2020` | `wsINETER-DGRH:Delineacion_cuenca_parcoco_2020Type` |

### `wsINETER-DGRH:Delineacion_cuenca_rcocoN6`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `n4` | `xsd:int` |
| `n5` | `xsd:int` |
| `n6` | `xsd:int` |
| `n3` | `xsd:int` |
| `nombre` | `xsd:string` |
| `área_km²` | `xsd:double` |
| `perimetro_` | `xsd:double` |
| `code_pfasf` | `xsd:int` |
| `Delineacion_cuenca_rcocoN6` | `wsINETER-DGRH:Delineacion_cuenca_rcocoN6Type` |

### `wsINETER-DGRH:Delineacion_cuenca_rcocoN7`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `n_3` | `xsd:double` |
| `n_4` | `xsd:double` |
| `n_5` | `xsd:int` |
| `n_6` | `xsd:double` |
| `n_7` | `xsd:double` |
| `phca` | `xsd:double` |
| `code_pfasf` | `xsd:double` |
| `area` | `xsd:double` |
| `perimetro` | `xsd:double` |
| `uh_nombre` | `xsd:string` |
| `Delineacion_cuenca_rcocoN7` | `wsINETER-DGRH:Delineacion_cuenca_rcocoN7Type` |

### `wsINETER-DGRH:Dipilto_Ana_Cafetalero`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `latitud` | `xsd:double` |
| `longitud` | `xsd:double` |
| `elevacion` | `xsd:double` |
| `comunidad` | `xsd:string` |
| `propietario` | `xsd:string` |
| `area_manz` | `xsd:double` |
| `hora_agua` | `xsd:double` |
| `cant_traba` | `xsd:int` |
| `tiemp_cost` | `xsd:double` |
| `Dipilto_Ana_Cafetalero` | `wsINETER-DGRH:Dipilto_Ana_CafetaleroType` |

### `wsINETER-DGRH:dipilto_ana_cafetalero-test`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `latitud` | `xsd:double` |
| `longitud` | `xsd:double` |
| `elevacion` | `xsd:double` |
| `comunidad` | `xsd:string` |
| `propietario` | `xsd:string` |
| `area_manz` | `xsd:double` |
| `hora_agua` | `xsd:double` |
| `cant_traba` | `xsd:int` |
| `tiemp_cost` | `xsd:double` |
| `dipilto_ana_cafetalero-test` | `wsINETER-DGRH:dipilto_ana_cafetalero-testType` |

### `wsINETER-DGRH:Dipilto_Ana_Cap`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `latitud` | `xsd:double` |
| `longitud` | `xsd:double` |
| `elevacion` | `xsd:double` |
| `nombre` | `xsd:string` |
| `fuente` | `xsd:string` |
| `Dipilto_Ana_Cap` | `wsINETER-DGRH:Dipilto_Ana_CapType` |

### `wsINETER-DGRH:Dipilto_Ana_Finca_Privada`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `latitud` | `xsd:double` |
| `longitud` | `xsd:double` |
| `elevacion` | `xsd:double` |
| `nombre` | `xsd:string` |
| `propietario` | `xsd:string` |
| `fuente` | `xsd:string` |
| `nea_m` | `xsd:double` |
| `Dipilto_Ana_Finca_Privada` | `wsINETER-DGRH:Dipilto_Ana_Finca_PrivadaType` |

### `wsINETER-DGRH:Dipilto_Ana_Fte_Agua_Cap`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `latitud` | `xsd:double` |
| `longitud` | `xsd:double` |
| `elevacion` | `xsd:double` |
| `comunidad` | `xsd:string` |
| `nombre` | `xsd:string` |
| `vivienda` | `xsd:int` |
| `vivienda2` | `xsd:int` |
| `cant_habi` | `xsd:int` |
| `Dipilto_Ana_Fte_Agua_Cap` | `wsINETER-DGRH:Dipilto_Ana_Fte_Agua_CapType` |

### `wsINETER-DGRH:Dipilto_Ana_Mon_Uscaps_Aforo`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `latitud` | `xsd:double` |
| `longitud` | `xsd:double` |
| `elevacion` | `xsd:double` |
| `comunidad` | `xsd:string` |
| `caps` | `xsd:string` |
| `sitio` | `xsd:string` |
| `q_l_s` | `xsd:double` |
| `q_mt3_dia` | `xsd:double` |
| `q_mt3_mes` | `xsd:double` |
| `q_mt3_anu` | `xsd:double` |
| `Dipilto_Ana_Mon_Uscaps_Aforo` | `wsINETER-DGRH:Dipilto_Ana_Mon_Uscaps_AforoType` |

### `wsINETER-DGRH:Dipilto_Ana_Mon_Uscaps_Cal_Agua`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `latitud` | `xsd:double` |
| `longitud` | `xsd:double` |
| `elevacion` | `xsd:double` |
| `comunidad` | `xsd:string` |
| `caps` | `xsd:string` |
| `sitio` | `xsd:string` |
| `ph` | `xsd:string` |
| `redox` | `xsd:double` |
| `c_e_us_c` | `xsd:double` |
| `std_mg_l` | `xsd:double` |
| `sal_gr_l` | `xsd:double` |
| `temperatura` | `xsd:double` |
| `Dipilto_Ana_Mon_Uscaps_Cal_Agua` | `wsINETER-DGRH:Dipilto_Ana_Mon_Uscaps_Cal_AguaType` |

### `wsINETER-DGRH:Dipilto_Ana_Mon_Usuario_Invent`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `latitud` | `xsd:double` |
| `longitud` | `xsd:double` |
| `elevacion` | `xsd:double` |
| `propietario` | `xsd:string` |
| `fuente` | `xsd:string` |
| `ph` | `xsd:string` |
| `redox` | `xsd:double` |
| `c_e_us_cm` | `xsd:double` |
| `std_mg_l` | `xsd:double` |
| `sal_gr_l` | `xsd:double` |
| `temperatura` | `xsd:double` |
| `q_l_s` | `xsd:double` |
| `q_mt3_dia` | `xsd:double` |
| `Dipilto_Ana_Mon_Usuario_Invent` | `wsINETER-DGRH:Dipilto_Ana_Mon_Usuario_InventType` |

### `wsINETER-DGRH:Dipilto_Ana_Monit_Agosto18`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `latitud` | `xsd:double` |
| `longitud` | `xsd:double` |
| `nombre` | `xsd:string` |
| `propietario` | `xsd:string` |
| `tipo_uso` | `xsd:string` |
| `cant_consum` | `xsd:double` |
| `ph` | `xsd:double` |
| `ce` | `xsd:double` |
| `t` | `xsd:double` |
| `orp` | `xsd:double` |
| `od` | `xsd:double` |
| `od1` | `xsd:double` |
| `tds` | `xsd:double` |
| `sal` | `xsd:double` |
| `Dipilto_Ana_Monit_Agosto18` | `wsINETER-DGRH:Dipilto_Ana_Monit_Agosto18Type` |

### `wsINETER-DGRH:Dipilto_Ana_Pto_Enacal`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `latitud` | `xsd:double` |
| `longitud` | `xsd:double` |
| `elevacion` | `xsd:double` |
| `fuente` | `xsd:string` |
| `tipo_fuente` | `xsd:string` |
| `Dipilto_Ana_Pto_Enacal` | `wsINETER-DGRH:Dipilto_Ana_Pto_EnacalType` |

### `wsINETER-DGRH:Dipilto_Ana_Ptos_Ineter_Pozo`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `latitud` | `xsd:double` |
| `longitud` | `xsd:double` |
| `ubicacion` | `xsd:string` |
| `Dipilto_Ana_Ptos_Ineter_Pozo` | `wsINETER-DGRH:Dipilto_Ana_Ptos_Ineter_PozoType` |

### `wsINETER-DGRH:Dipilto_Ana_Ptos_Ineter_Tsuperf`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `latitud` | `xsd:double` |
| `longitud` | `xsd:double` |
| `ubicacion` | `xsd:string` |
| `Dipilto_Ana_Ptos_Ineter_Tsuperf` | `wsINETER-DGRH:Dipilto_Ana_Ptos_Ineter_TsuperfType` |

### `wsINETER-DGRH:Dipilto_Ana_Visita1317`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `latitud` | `xsd:double` |
| `longitud` | `xsd:double` |
| `elevacion` | `xsd:double` |
| `municipio` | `xsd:string` |
| `comunidad` | `xsd:string` |
| `nombre` | `xsd:string` |
| `nombre2` | `xsd:string` |
| `fuente` | `xsd:string` |
| `uso` | `xsd:string` |
| `Dipilto_Ana_Visita1317` | `wsINETER-DGRH:Dipilto_Ana_Visita1317Type` |

### `wsINETER-DGRH:Dipilto_Bh_Area_Sitio_Aforo`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nivel7` | `xsd:int` |
| `a1` | `xsd:double` |
| `unidad_hidrica` | `xsd:string` |
| `perimetro` | `xsd:double` |
| `hectarea` | `xsd:double` |
| `Dipilto_Bh_Area_Sitio_Aforo` | `wsINETER-DGRH:Dipilto_Bh_Area_Sitio_AforoType` |

### `wsINETER-DGRH:Dipilto_Bh_Ciudad`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nombre` | `xsd:string` |
| `tipo` | `xsd:string` |
| `municipio` | `xsd:string` |
| `area` | `xsd:double` |
| `perimetro` | `xsd:double` |
| `acres` | `xsd:double` |
| `Dipilto_Bh_Ciudad` | `wsINETER-DGRH:Dipilto_Bh_CiudadType` |

### `wsINETER-DGRH:Dipilto_Bh_Linea_Curva_Dipilto`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `elevacion` | `xsd:double` |
| `Dipilto_Bh_Linea_Curva_Dipilto` | `wsINETER-DGRH:Dipilto_Bh_Linea_Curva_DipiltoType` |

### `wsINETER-DGRH:Dipilto_Bh_N7`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nivel7` | `xsd:int` |
| `a1` | `xsd:double` |
| `unidad_hidrica` | `xsd:string` |
| `perimetro` | `xsd:double` |
| `hectarea` | `xsd:double` |
| `Dipilto_Bh_N7` | `wsINETER-DGRH:Dipilto_Bh_N7Type` |

### `wsINETER-DGRH:Dipilto_Bh_Orden_Suelo_2015`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `tipo` | `xsd:string` |
| `codigo` | `xsd:string` |
| `area_km2` | `xsd:double` |
| `perimetro` | `xsd:double` |
| `Dipilto_Bh_Orden_Suelo_2015` | `wsINETER-DGRH:Dipilto_Bh_Orden_Suelo_2015Type` |

### `wsINETER-DGRH:Dipilto_Bh_Poblado`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `nombre` | `xsd:string` |
| `tipo` | `xsd:string` |
| `codigomuni` | `xsd:int` |
| `codigodept` | `xsd:int` |
| `Dipilto_Bh_Poblado` | `wsINETER-DGRH:Dipilto_Bh_PobladoType` |

### `wsINETER-DGRH:Dipilto_Bh_Poligono_Curva_Dipilto`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `area` | `xsd:double` |
| `Dipilto_Bh_Poligono_Curva_Dipilto` | `wsINETER-DGRH:Dipilto_Bh_Poligono_Curva_DipiltoType` |

### `wsINETER-DGRH:Dipilto_Bh_Red_Hidrica_Dipilto`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `nombre` | `xsd:string` |
| `categoria` | `xsd:string` |
| `longitud_km` | `xsd:double` |
| `Dipilto_Bh_Red_Hidrica_Dipilto` | `wsINETER-DGRH:Dipilto_Bh_Red_Hidrica_DipiltoType` |

### `wsINETER-DGRH:Dipilto_Bh_Rio_Principal_Dipilto`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `nombre` | `xsd:string` |
| `longitud_km` | `xsd:double` |
| `Dipilto_Bh_Rio_Principal_Dipilto` | `wsINETER-DGRH:Dipilto_Bh_Rio_Principal_DipiltoType` |

### `wsINETER-DGRH:Dipilto_Bh_Uso_Potencial_2015`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `codigo` | `xsd:string` |
| `nombre` | `xsd:string` |
| `area_km2` | `xsd:double` |
| `perimetro` | `xsd:double` |
| `Dipilto_Bh_Uso_Potencial_2015` | `wsINETER-DGRH:Dipilto_Bh_Uso_Potencial_2015Type` |

### `wsINETER-DGRH:Dipilto_Bh_Uso_Suelo_15`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nombre` | `xsd:string` |
| `area_km2` | `xsd:double` |
| `perimetro` | `xsd:double` |
| `Dipilto_Bh_Uso_Suelo_15` | `wsINETER-DGRH:Dipilto_Bh_Uso_Suelo_15Type` |

### `wsINETER-DGRH:Dipilto_Dz_Cuenca_Mod`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `tipoforma` | `xsd:string` |
| `nivel7` | `xsd:int` |
| `a1` | `xsd:double` |
| `perimetro` | `xsd:double` |
| `nombrforma` | `xsd:string` |
| `Dipilto_Dz_Cuenca_Mod` | `wsINETER-DGRH:Dipilto_Dz_Cuenca_ModType` |

### `wsINETER-DGRH:Dipilto_Dz_Derrumbe`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `municipio` | `xsd:string` |
| `descrip` | `xsd:string` |
| `Dipilto_Dz_Derrumbe` | `wsINETER-DGRH:Dipilto_Dz_DerrumbeType` |

### `wsINETER-DGRH:Dipilto_Dz_Deslizamiento`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `municipio` | `xsd:string` |
| `amenaza` | `xsd:string` |
| `sitio_critico` | `xsd:string` |
| `ubicacion` | `xsd:string` |
| `area` | `xsd:double` |
| `perimetro` | `xsd:double` |
| `acres` | `xsd:double` |
| `Dipilto_Dz_Deslizamiento` | `wsINETER-DGRH:Dipilto_Dz_DeslizamientoType` |

### `wsINETER-DGRH:Dipilto_Dz_Deslizamiento_Superficial`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `municipio` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `Dipilto_Dz_Deslizamiento_Superficial` | `wsINETER-DGRH:Dipilto_Dz_Deslizamiento_SuperficialType` |

### `wsINETER-DGRH:Dipilto_Dz_Dique`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `area_km` | `xsd:double` |
| `area_metro` | `xsd:double` |
| `Dipilto_Dz_Dique` | `wsINETER-DGRH:Dipilto_Dz_DiqueType` |

### `wsINETER-DGRH:Dipilto_Dz_Direccion_Movimiento`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `municipio` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `Dipilto_Dz_Direccion_Movimiento` | `wsINETER-DGRH:Dipilto_Dz_Direccion_MovimientoType` |

### `wsINETER-DGRH:Dipilto_Dz_Falla`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `descripcion` | `xsd:string` |
| `tipo` | `xsd:string` |
| `clase` | `xsd:string` |
| `Dipilto_Dz_Falla` | `wsINETER-DGRH:Dipilto_Dz_FallaType` |

### `wsINETER-DGRH:Dipilto_Dz_Flujo_Detritos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `municipio` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `Dipilto_Dz_Flujo_Detritos` | `wsINETER-DGRH:Dipilto_Dz_Flujo_DetritosType` |

### `wsINETER-DGRH:Dipilto_Dz_Geologia`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `tipoforma` | `xsd:string` |
| `area` | `xsd:double` |
| `perimetro` | `xsd:double` |
| `gg4` | `xsd:double` |
| `Dipilto_Dz_Geologia` | `wsINETER-DGRH:Dipilto_Dz_GeologiaType` |

### `wsINETER-DGRH:Dipilto_Dz_Manantial_Dipilto3`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `latitud` | `xsd:double` |
| `longitud` | `xsd:double` |
| `departamento` | `xsd:string` |
| `municipio` | `xsd:string` |
| `zona` | `xsd:string` |
| `barrio` | `xsd:string` |
| `nombre` | `xsd:string` |
| `tipo` | `xsd:string` |
| `tipo2` | `xsd:string` |
| `estado` | `xsd:string` |
| `problem_amb` | `xsd:string` |
| `propu_inv` | `xsd:string` |
| `prop_sist` | `xsd:string` |
| `Dipilto_Dz_Manantial_Dipilto3` | `wsINETER-DGRH:Dipilto_Dz_Manantial_Dipilto3Type` |

### `wsINETER-DGRH:Dipilto_Dz_Pozo_Manantial_Dipilto`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `latitud` | `xsd:double` |
| `longitud` | `xsd:double` |
| `ubicacion` | `xsd:string` |
| `propietario` | `xsd:string` |
| `tipo` | `xsd:string` |
| `tipo2` | `xsd:string` |
| `f11` | `xsd:string` |
| `f12` | `xsd:string` |
| `profundidad` | `xsd:double` |
| `nea_mt` | `xsd:double` |
| `nea_msnm` | `xsd:double` |
| `Dipilto_Dz_Pozo_Manantial_Dipilto` | `wsINETER-DGRH:Dipilto_Dz_Pozo_Manantial_DipiltoType` |

### `wsINETER-DGRH:Dipilto_Estacion_Cuenca`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `latitud` | `xsd:double` |
| `longitud` | `xsd:double` |
| `ubicacion` | `xsd:string` |
| `tipo` | `xsd:string` |
| `Dipilto_Estacion_Cuenca` | `wsINETER-DGRH:Dipilto_Estacion_CuencaType` |

### `wsINETER-DGRH:Dipilto_Hg_Cuenca45`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `latitud` | `xsd:double` |
| `longitud` | `xsd:double` |
| `municipio` | `xsd:string` |
| `sitio` | `xsd:string` |
| `ubicacion` | `xsd:string` |
| `tiposuelo` | `xsd:string` |
| `clase` | `xsd:string` |
| `cobertura` | `xsd:string` |
| `profun_cm` | `xsd:double` |
| `pend` | `xsd:string` |
| `vi_cal` | `xsd:double` |
| `vi_cal2` | `xsd:double` |
| `da` | `xsd:string` |
| `cc` | `xsd:string` |
| `pmp` | `xsd:string` |
| `pr_mm` | `xsd:double` |
| `fecha` | `xsd:date` |
| `Dipilto_Hg_Cuenca45` | `wsINETER-DGRH:Dipilto_Hg_Cuenca45Type` |

### `wsINETER-DGRH:Dipilto_Hg_Falla_Sanfabian`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `Dipilto_Hg_Falla_Sanfabian` | `wsINETER-DGRH:Dipilto_Hg_Falla_SanfabianType` |

### `wsINETER-DGRH:Dipilto_Hg_Hidroquimica`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `nombrhidro` | `xsd:string` |
| `perimetro` | `xsd:double` |
| `nivel7` | `xsd:int` |
| `a1` | `xsd:double` |
| `Dipilto_Hg_Hidroquimica` | `wsINETER-DGRH:Dipilto_Hg_HidroquimicaType` |

### `wsINETER-DGRH:Dipilto_Hg_Transmisividad`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `rangotrans` | `xsd:string` |
| `perimetro` | `xsd:double` |
| `nivel7` | `xsd:int` |
| `a1` | `xsd:double` |
| `Dipilto_Hg_Transmisividad` | `wsINETER-DGRH:Dipilto_Hg_TransmisividadType` |

### `wsINETER-DGRH:Dipilto_Hg_Zona_Recarga`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `zonarecarg` | `xsd:string` |
| `valorecarg` | `xsd:double` |
| `area` | `xsd:double` |
| `perimetro` | `xsd:double` |
| `nivel7` | `xsd:int` |
| `a1` | `xsd:double` |
| `Dipilto_Hg_Zona_Recarga` | `wsINETER-DGRH:Dipilto_Hg_Zona_RecargaType` |

### `wsINETER-DGRH:Esta_telemet_hsup_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `objeto` | `xsd:long` |
| `código` | `xsd:long` |
| `nombre` | `xsd:string` |
| `río` | `xsd:string` |
| `tipo` | `xsd:string` |
| `aforo` | `xsd:string` |
| `condición` | `xsd:string` |
| `observaci` | `xsd:string` |
| `ruta` | `xsd:string` |
| `municipio` | `xsd:string` |
| `x` | `xsd:double` |
| `y` | `xsd:double` |
| `Esta_telemet_hsup_2022` | `wsINETER-DGRH:Esta_telemet_hsup_2022Type` |

### `wsINETER-DGRH:Estaciones_aforos_rcoco_2020`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `n` | `xsd:double` |
| `codigo` | `xsd:string` |
| `nombre` | `xsd:string` |
| `rio` | `xsd:string` |
| `tipo` | `xsd:string` |
| `longitud` | `xsd:string` |
| `latitud` | `xsd:string` |
| `longitud_x` | `xsd:double` |
| `latitud_y` | `xsd:double` |
| `long__x` | `xsd:double` |
| `lat__y` | `xsd:double` |
| `elevación` | `xsd:double` |
| `área_de_d` | `xsd:double` |
| `n15` | `xsd:string` |
| `hoja` | `xsd:string` |
| `lugar` | `xsd:string` |
| `municipio` | `xsd:string` |
| `departamen` | `xsd:string` |
| `estado` | `xsd:string` |
| `Estaciones_aforos_rcoco_2020` | `wsINETER-DGRH:Estaciones_aforos_rcoco_2020Type` |

### `wsINETER-DGRH:Estaciones_Hidrologicas`

| Campo | Tipo |
|---|---|
| `nombrebd` | `xsd:string` |
| `nombre` | `xsd:string` |
| `longitud` | `xsd:float` |
| `latitud` | `xsd:float` |
| `esp` | `gml:GeometryPropertyType` |
| `codigo` | `xsd:string` |
| `idpropietario` | `xsd:int` |
| `Estaciones_Hidrologicas` | `wsINETER-DGRH:Estaciones_HidrologicasType` |

### `wsINETER-DGRH:Estaciones_pluviomet_rcoco_2020`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `no` | `xsd:double` |
| `nombre` | `xsd:string` |
| `codigo` | `xsd:double` |
| `periodo` | `xsd:string` |
| `long_x` | `xsd:double` |
| `lat_y` | `xsd:double` |
| `elevacion` | `xsd:string` |
| `variable` | `xsd:string` |
| `tipo` | `xsd:string` |
| `Estaciones_pluviomet_rcoco_2020` | `wsINETER-DGRH:Estaciones_pluviomet_rcoco_2020Type` |

### `wsINETER-DGRH:Estaciones_Pluviometricas_allacc`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `no` | `xsd:double` |
| `nombre` | `xsd:string` |
| `codigo` | `xsd:double` |
| `periodo` | `xsd:string` |
| `long` | `xsd:double` |
| `lat` | `xsd:double` |
| `elevacion` | `xsd:string` |
| `variable` | `xsd:string` |
| `tipo` | `xsd:string` |
| `Estaciones_Pluviometricas_allacc` | `wsINETER-DGRH:Estaciones_Pluviometricas_allaccType` |

### `wsINETER-DGRH:EstacionesHidrologicas`

| Campo | Tipo |
|---|---|
| `nombre` | `xsd:string` |
| `longitud` | `xsd:float` |
| `latitud` | `xsd:float` |
| `geom` | `gml:GeometryPropertyType` |
| `codigo` | `xsd:string` |
| `idpropietario` | `xsd:int` |
| `tipo` | `xsd:string` |
| `EstacionesHidrologicas` | `wsINETER-DGRH:EstacionesHidrologicasType` |

### `wsINETER-DGRH:inventariopozosescavados`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fid_` | `xsd:double` |
| `ac` | `xsd:double` |
| `fu` | `xsd:double` |
| `id` | `xsd:string` |
| `tipo` | `xsd:string` |
| `x` | `xsd:double` |
| `y` | `xsd:double` |
| `z_msnm_` | `xsd:string` |
| `prof__m_` | `xsd:string` |
| `nea__m_` | `xsd:string` |
| `b__m_` | `xsd:string` |
| `nea__msnm_` | `xsd:string` |
| `tb_hr_` | `xsd:string` |
| `q_m3_hr_` | `xsd:string` |
| `s_m_` | `xsd:string` |
| `q_m3_hr_m_` | `xsd:string` |
| `t_m2_d_` | `xsd:string` |
| `s` | `xsd:string` |
| `k_m_d_` | `xsd:string` |
| `q___` | `xsd:string` |
| `nd` | `xsd:string` |
| `pr` | `xsd:string` |
| `rejilla_m_` | `xsd:string` |
| `basamento_` | `xsd:string` |
| `municipio` | `xsd:string` |
| `lat` | `xsd:decimal` |
| `lo` | `xsd:decimal` |
| `inventariopozosescavados` | `wsINETER-DGRH:inventariopozosescavadosType` |

### `wsINETER-DGRH:inventariopozosperforados`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fid_` | `xsd:double` |
| `ac` | `xsd:double` |
| `fu` | `xsd:double` |
| `id` | `xsd:double` |
| `tipo` | `xsd:string` |
| `x` | `xsd:double` |
| `y` | `xsd:double` |
| `z_msnm_` | `xsd:double` |
| `prof__m_` | `xsd:double` |
| `nea__m_` | `xsd:double` |
| `b__m_` | `xsd:double` |
| `nea__msnm_` | `xsd:double` |
| `tb_hr_` | `xsd:double` |
| `q_m3_hr_` | `xsd:double` |
| `s_m_` | `xsd:double` |
| `q_m3_hr_m_` | `xsd:double` |
| `t_m2_d_` | `xsd:double` |
| `s` | `xsd:double` |
| `k_m_d_` | `xsd:double` |
| `q___` | `xsd:double` |
| `nd` | `xsd:string` |
| `pr` | `xsd:string` |
| `rejilla_m_` | `xsd:double` |
| `basamento_` | `xsd:double` |
| `municipio` | `xsd:string` |
| `datos_hid` | `xsd:string` |
| `lat` | `xsd:decimal` |
| `lo` | `xsd:decimal` |
| `inventariopozosperforados` | `wsINETER-DGRH:inventariopozosperforadosType` |

### `wsINETER-DGRH:inventariospozosmanantiales`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `fid_` | `xsd:double` |
| `ac` | `xsd:double` |
| `fu` | `xsd:double` |
| `id` | `xsd:double` |
| `tipo` | `xsd:string` |
| `x` | `xsd:double` |
| `y` | `xsd:double` |
| `z_msnm_` | `xsd:double` |
| `f8` | `xsd:string` |
| `f9` | `xsd:string` |
| `f10` | `xsd:string` |
| `lat` | `xsd:decimal` |
| `lo` | `xsd:decimal` |
| `inventariospozosmanantiales` | `wsINETER-DGRH:inventariospozosmanantialesType` |

### `wsINETER-DGRH:manantiales_2020`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `numero` | `xsd:double` |
| `tipo` | `xsd:string` |
| `x` | `xsd:double` |
| `y` | `xsd:double` |
| `z__msnm_` | `xsd:double` |
| `p_r__m_` | `xsd:double` |
| `profundida` | `xsd:double` |
| `localizaci` | `xsd:string` |
| `propietari` | `xsd:string` |
| `nombre_del` | `xsd:string` |
| `nea__m_` | `xsd:double` |
| `nd__m_` | `xsd:double` |
| `ph` | `xsd:double` |
| `ph__mv_` | `xsd:double` |
| `ce__âµs_` | `xsd:double` |
| `ce_absolut` | `xsd:double` |
| `orp__mv_` | `xsd:double` |
| `salinidad` | `xsd:double` |
| `presion_at` | `xsd:double` |
| `od____` | `xsd:double` |
| `od__ppm_` | `xsd:double` |
| `resistivid` | `xsd:double` |
| `t__â°c_` | `xsd:double` |
| `tds__ppm_` | `xsd:double` |
| `aforo` | `xsd:string` |
| `extraccion` | `xsd:double` |
| `extracci_1` | `xsd:double` |
| `tipo_de_bo` | `xsd:string` |
| `uso` | `xsd:string` |
| `numero_de` | `xsd:double` |
| `comunidad` | `xsd:string` |
| `municipio` | `xsd:string` |
| `departamen` | `xsd:string` |
| `fecha` | `xsd:string` |
| `hora` | `xsd:string` |
| `observacio` | `xsd:string` |
| `nea_msnm` | `xsd:double` |
| `prof02` | `xsd:double` |
| `manantiales_2020` | `wsINETER-DGRH:manantiales_2020Type` |

### `wsINETER-DGRH:Monitoreo_allac`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `numero` | `xsd:double` |
| `tipo` | `xsd:string` |
| `x` | `xsd:double` |
| `y` | `xsd:double` |
| `z_msnm_` | `xsd:double` |
| `p_r__m` | `xsd:double` |
| `profundidad` | `xsd:double` |
| `localizacion` | `xsd:string` |
| `propietario` | `xsd:string` |
| `nombre` | `xsd:string` |
| `nea_m` | `xsd:double` |
| `nd_m` | `xsd:double` |
| `ph` | `xsd:double` |
| `ph_mv` | `xsd:double` |
| `ce_` | `xsd:double` |
| `ce_absolut` | `xsd:double` |
| `orp_mv` | `xsd:double` |
| `salinidad` | `xsd:double` |
| `presion_at` | `xsd:double` |
| `od` | `xsd:double` |
| `od_ppm` | `xsd:double` |
| `resistivid` | `xsd:double` |
| `t` | `xsd:double` |
| `tds_ppm` | `xsd:double` |
| `aforo` | `xsd:string` |
| `extraccion` | `xsd:double` |
| `extracci_1` | `xsd:double` |
| `tipo_de_bo` | `xsd:string` |
| `uso` | `xsd:string` |
| `numero_de` | `xsd:double` |
| `comunidad` | `xsd:string` |
| `municipio` | `xsd:string` |
| `departamento` | `xsd:string` |
| `fecha` | `xsd:string` |
| `hora` | `xsd:string` |
| `observacion` | `xsd:string` |
| `nea_msnm` | `xsd:double` |
| `prof02` | `xsd:double` |
| `Monitoreo_allac` | `wsINETER-DGRH:Monitoreo_allacType` |

### `wsINETER-DGRH:Nivel_Rio`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `codigo` | `xsd:string` |
| `nombreestacion` | `xsd:string` |
| `rio` | `xsd:string` |
| `tipo` | `xsd:string` |
| `nivelrio` | `xsd:decimal` |
| `niveldesborde` | `xsd:double` |
| `fechaultimatransmision` | `xsd:dateTime` |
| `Nivel_Rio` | `wsINETER-DGRH:Nivel_RioType` |

### `wsINETER-DGRH:nucleos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `gid` | `xsd:long` |
| `cat` | `xsd:long` |
| `value` | `xsd:long` |
| `label` | `xsd:string` |
| `lat` | `xsd:decimal` |
| `lo` | `xsd:decimal` |
| `nucleos` | `wsINETER-DGRH:nucleosType` |

### `wsINETER-DGRH:Piezometria_Somoto_2020`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `zlevel` | `xsd:decimal` |
| `Piezometria_Somoto_2020` | `wsINETER-DGRH:Piezometria_Somoto_2020Type` |

### `wsINETER-DGRH:Pozo_excavados_2020`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `numero` | `xsd:decimal` |
| `tipo` | `xsd:string` |
| `x` | `xsd:decimal` |
| `y` | `xsd:decimal` |
| `z__msnm_` | `xsd:decimal` |
| `p_r__m_` | `xsd:decimal` |
| `profundida` | `xsd:decimal` |
| `localizaci` | `xsd:string` |
| `propietari` | `xsd:string` |
| `nombre_del` | `xsd:string` |
| `nea__m_` | `xsd:decimal` |
| `nd__m_` | `xsd:decimal` |
| `ph` | `xsd:decimal` |
| `ph__mv_` | `xsd:decimal` |
| `ce__âµs_` | `xsd:decimal` |
| `ce_absolut` | `xsd:decimal` |
| `orp__mv_` | `xsd:decimal` |
| `salinidad` | `xsd:decimal` |
| `presion_at` | `xsd:decimal` |
| `od____` | `xsd:decimal` |
| `od__ppm_` | `xsd:decimal` |
| `resistivid` | `xsd:decimal` |
| `t__â°c_` | `xsd:decimal` |
| `tds__ppm_` | `xsd:decimal` |
| `aforo` | `xsd:string` |
| `extraccion` | `xsd:decimal` |
| `extracci_1` | `xsd:decimal` |
| `tipo_de_bo` | `xsd:string` |
| `uso` | `xsd:string` |
| `numero_de` | `xsd:decimal` |
| `comunidad` | `xsd:string` |
| `municipio` | `xsd:string` |
| `departamen` | `xsd:string` |
| `fecha` | `xsd:string` |
| `hora` | `xsd:string` |
| `observacio` | `xsd:string` |
| `nea_msnm` | `xsd:decimal` |
| `prof02` | `xsd:decimal` |
| `Pozo_excavados_2020` | `wsINETER-DGRH:Pozo_excavados_2020Type` |

### `wsINETER-DGRH:pozo_perforado_2020`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `numero` | `xsd:decimal` |
| `tipo` | `xsd:string` |
| `x` | `xsd:decimal` |
| `y` | `xsd:decimal` |
| `z__msnm_` | `xsd:decimal` |
| `p_r__m_` | `xsd:decimal` |
| `profundida` | `xsd:decimal` |
| `localizaci` | `xsd:string` |
| `propietari` | `xsd:string` |
| `nombre_del` | `xsd:string` |
| `nea__m_` | `xsd:decimal` |
| `nd__m_` | `xsd:decimal` |
| `ph` | `xsd:decimal` |
| `ph__mv_` | `xsd:decimal` |
| `ce__âµs_` | `xsd:decimal` |
| `ce_absolut` | `xsd:decimal` |
| `orp__mv_` | `xsd:decimal` |
| `salinidad` | `xsd:decimal` |
| `presion_at` | `xsd:decimal` |
| `od____` | `xsd:decimal` |
| `od__ppm_` | `xsd:decimal` |
| `resistivid` | `xsd:decimal` |
| `t__â°c_` | `xsd:decimal` |
| `tds__ppm_` | `xsd:decimal` |
| `aforo` | `xsd:string` |
| `extraccion` | `xsd:decimal` |
| `extracci_1` | `xsd:decimal` |
| `tipo_de_bo` | `xsd:string` |
| `uso` | `xsd:string` |
| `numero_de` | `xsd:decimal` |
| `comunidad` | `xsd:string` |
| `municipio` | `xsd:string` |
| `departamen` | `xsd:string` |
| `fecha` | `xsd:string` |
| `hora` | `xsd:string` |
| `observacio` | `xsd:string` |
| `nea_msnm` | `xsd:decimal` |
| `prof02` | `xsd:decimal` |
| `pozo_perforado_2020` | `wsINETER-DGRH:pozo_perforado_2020Type` |

### `wsINETER-DGRH:Pozos_Hidraulicos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `no` | `xsd:string` |
| `x` | `xsd:double` |
| `y` | `xsd:double` |
| `long` | `xsd:double` |
| `lat` | `xsd:double` |
| `elevac_msn` | `xsd:double` |
| `fecha_a` | `xsd:double` |
| `prof_acuif` | `xsd:string` |
| `pozo_m` | `xsd:string` |
| `nea_m` | `xsd:double` |
| `acuif_espe` | `xsd:string` |
| `pozo_espes` | `xsd:string` |
| `q_m�_hr_` | `xsd:string` |
| `q_m�_h_1` | `xsd:string` |
| `s_m` | `xsd:string` |
| `q_s_m�_h` | `xsd:string` |
| `q_s_m�_1` | `xsd:string` |
| `t_m�_d__` | `xsd:string` |
| `t_m�_d_1` | `xsd:string` |
| `s` | `xsd:string` |
| `k_m_d` | `xsd:string` |
| `tipo` | `xsd:string` |
| `fuente` | `xsd:string` |
| `Pozos_Hidraulicos` | `wsINETER-DGRH:Pozos_HidraulicosType` |

### `wsINETER-DGRH:Pozos_Hidroquimicos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `codigo` | `xsd:string` |
| `localizaci` | `xsd:string` |
| `n` | `xsd:double` |
| `e` | `xsd:double` |
| `lat` | `xsd:double` |
| `long` | `xsd:double` |
| `fecha_anal` | `xsd:string` |
| `k` | `xsd:double` |
| `na` | `xsd:double` |
| `mg2` | `xsd:double` |
| `ca2` | `xsd:double` |
| `fe2` | `xsd:double` |
| `co3` | `xsd:double` |
| `hco3` | `xsd:double` |
| `cl` | `xsd:double` |
| `so4` | `xsd:double` |
| `no3` | `xsd:double` |
| `f` | `xsd:double` |
| `hidroquimi` | `xsd:string` |
| `descrip` | `xsd:string` |
| `fuente` | `xsd:string` |
| `Pozos_Hidroquimicos` | `wsINETER-DGRH:Pozos_HidroquimicosType` |

### `wsINETER-DGRH:Pozos_monitores_2021`

| Campo | Tipo |
|---|---|
| `geom` | `gml:PointPropertyType` |
| `tipo` | `xsd:string` |
| `x` | `xsd:double` |
| `y` | `xsd:double` |
| `z` | `xsd:double` |
| `localizaci` | `xsd:string` |
| `propietari` | `xsd:string` |
| `prof_m` | `xsd:double` |
| `nea__m_` | `xsd:double` |
| `nd__m_` | `xsd:double` |
| `acuifero` | `xsd:string` |
| `Pozos_monitores_2021` | `wsINETER-DGRH:Pozos_monitores_2021Type` |

### `wsINETER-DGRH:Red_hidrica_nacional_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `cuenca` | `xsd:double` |
| `nombre_rio` | `xsd:string` |
| `categoria` | `xsd:string` |
| `tipo_rio` | `xsd:string` |
| `long_km` | `xsd:double` |
| `Red_hidrica_nacional_2022` | `wsINETER-DGRH:Red_hidrica_nacional_2022Type` |

### `wsINETER-DGRH:Red_Hidrica_riococo`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `objectid` | `xsd:int` |
| `nombres` | `xsd:string` |
| `categoria` | `xsd:string` |
| `long_km` | `xsd:double` |
| `Red_Hidrica_riococo` | `wsINETER-DGRH:Red_Hidrica_riococoType` |

### `wsINETER-DGRH:Red_Hidrografica`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `nombre` | `xsd:string` |
| `Red_Hidrografica` | `wsINETER-DGRH:Red_HidrograficaType` |

### `wsINETER-DGRH:Redrenaje_parcoco_2020`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `objectid` | `xsd:long` |
| `cuenca` | `xsd:double` |
| `nombre_rio` | `xsd:string` |
| `categoria` | `xsd:string` |
| `tipo_rio` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `layer` | `xsd:string` |
| `path` | `xsd:string` |
| `Redrenaje_parcoco_2020` | `wsINETER-DGRH:Redrenaje_parcoco_2020Type` |

### `wsINETER-DGRH:Rios_princip_rcoco_2020`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `nombres` | `xsd:string` |
| `categoría` | `xsd:string` |
| `long__km` | `xsd:double` |
| `Rios_princip_rcoco_2020` | `wsINETER-DGRH:Rios_princip_rcoco_2020Type` |

### `wsINETER-DGRH:Rios_principales`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `nombre` | `xsd:string` |
| `categoria` | `xsd:string` |
| `long_km` | `xsd:double` |
| `Rios_principales` | `wsINETER-DGRH:Rios_principalesType` |

### `wsINETER-DGRH:Saturacion_Suelo_SAT`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `basin` | `xsd:int` |
| `fechahora` | `xsd:dateTime` |
| `fecha` | `xsd:date` |
| `asmu06` | `xsd:decimal` |
| `asml06` | `xsd:decimal` |
| `asmt06` | `xsd:decimal` |
| `nivelsaturacion` | `xsd:string` |
| `Saturacion_Suelo_SAT` | `wsINETER-DGRH:Saturacion_Suelo_SATType` |

### `wsINETER-DGRH:Subcuencas`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `basin` | `xsd:long` |
| `Subcuencas` | `wsINETER-DGRH:SubcuencasType` |

### `wsINETER-DGRH:Uh_coco_n7`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `n_3` | `xsd:double` |
| `n_4` | `xsd:double` |
| `n_5` | `xsd:int` |
| `n_6` | `xsd:double` |
| `n_7` | `xsd:double` |
| `phca` | `xsd:double` |
| `code_pfasf` | `xsd:double` |
| `area` | `xsd:double` |
| `perimetro` | `xsd:double` |
| `uh_nombre` | `xsd:string` |
| `Uh_coco_n7` | `wsINETER-DGRH:Uh_coco_n7Type` |

### `wsINETER-DGRH:Uh_riococo_partealta`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `n4` | `xsd:int` |
| `n5` | `xsd:int` |
| `n6` | `xsd:int` |
| `n3` | `xsd:int` |
| `nombre` | `xsd:string` |
| `area_km` | `xsd:double` |
| `perimetro` | `xsd:double` |
| `code_pfasf` | `xsd:int` |
| `Uh_riococo_partealta` | `wsINETER-DGRH:Uh_riococo_partealtaType` |

### `wsINETER-DGRH:Unidades_hidrologicas_n6`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `n4` | `xsd:int` |
| `n5` | `xsd:int` |
| `n6` | `xsd:int` |
| `n3` | `xsd:int` |
| `nombre` | `xsd:string` |
| `area_km2` | `xsd:double` |
| `perimetro` | `xsd:double` |
| `code_pfasf` | `xsd:int` |
| `Unidades_hidrologicas_n6` | `wsINETER-DGRH:Unidades_hidrologicas_n6Type` |

### `wsINETER-DGRH:UnidadGestionAguaSubterranea_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid_1` | `xsd:int` |
| `objectid` | `xsd:int` |
| `id` | `xsd:int` |
| `redoh` | `xsd:int` |
| `z_msnm` | `xsd:int` |
| `nea_m` | `xsd:string` |
| `b_m_` | `xsd:string` |
| `t_m2_d` | `xsd:string` |
| `q_m3_d_m` | `xsd:string` |
| `s_adim` | `xsd:string` |
| `nombre` | `xsd:string` |
| `codigo` | `xsd:double` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `ugas` | `xsd:string` |
| `UnidadGestionAguaSubterranea_2022` | `wsINETER-DGRH:UnidadGestionAguaSubterranea_2022Type` |

### `wsINETER-DGRH:usored2015v`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `gid` | `xsd:long` |
| `grid_code` | `xsd:long` |
| `code` | `xsd:string` |
| `codigo_ipc` | `xsd:long` |
| `uso` | `xsd:string` |
| `lat` | `xsd:decimal` |
| `lo` | `xsd:decimal` |
| `usored2015v` | `wsINETER-DGRH:usored2015vType` |

### `wsINETER-DGRH:Vertidos_2017`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `x` | `xsd:double` |
| `y` | `xsd:double` |
| `resolucion` | `xsd:string` |
| `empresa` | `xsd:string` |
| `ubicacion` | `xsd:string` |
| `ano` | `xsd:double` |
| `vigencia` | `xsd:string` |
| `cuenca` | `xsd:string` |
| `codigo` | `xsd:double` |
| `subcuenca` | `xsd:string` |
| `fecha` | `xsd:date` |
| `volumen_ma` | `xsd:double` |
| `clasificac` | `xsd:string` |
| `afluente_p` | `xsd:string` |
| `afluente_d` | `xsd:double` |
| `afluente_1` | `xsd:double` |
| `afluente_s` | `xsd:double` |
| `afluente_2` | `xsd:double` |
| `afluente_3` | `xsd:string` |
| `afluente_a` | `xsd:double` |
| `afluente_c` | `xsd:double` |
| `afluente_n` | `xsd:double` |
| `afluente_4` | `xsd:double` |
| `efluente_p` | `xsd:double` |
| `efluente_d` | `xsd:string` |
| `efluente_c` | `xsd:string` |
| `efluente_1` | `xsd:string` |
| `efluente_2` | `xsd:double` |
| `efluente_s` | `xsd:double` |
| `efluente_3` | `xsd:string` |
| `efluente_4` | `xsd:string` |
| `efluente_a` | `xsd:string` |
| `efluente_5` | `xsd:double` |
| `efluente_n` | `xsd:double` |
| `efluente_f` | `xsd:double` |
| `efluente` | `xsd:string` |
| `efluente_r` | `xsd:string` |
| `efluente_6` | `xsd:string` |
| `efluente_7` | `xsd:string` |
| `efluente_8` | `xsd:string` |
| `efluente_9` | `xsd:string` |
| `efluent_10` | `xsd:string` |
| `efluent_11` | `xsd:string` |
| `efluente_l` | `xsd:string` |
| `efluente_z` | `xsd:string` |
| `efluent_12` | `xsd:string` |
| `efluent_13` | `xsd:string` |
| `efluent_14` | `xsd:string` |
| `efluent_15` | `xsd:string` |
| `efluent_16` | `xsd:string` |
| `efluente_h` | `xsd:string` |
| `Vertidos_2017` | `wsINETER-DGRH:Vertidos_2017Type` |

### `wsINETER-EXTERNO:Densidad_Poblacional_2022`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `label` | `xsd:string` |
| `id_unico` | `xsd:string` |
| `depto` | `xsd:string` |
| `municipio` | `xsd:string` |
| `id_mun` | `xsd:double` |
| `id_com` | `xsd:double` |
| `comun` | `xsd:string` |
| `pobl_2022` | `xsd:double` |
| `densi_2022` | `xsd:double` |
| `rango_dens` | `xsd:string` |
| `densi_cara` | `xsd:string` |
| `Densidad_Poblacional_2022` | `wsINETER-EXTERNO:Densidad_Poblacional_2022Type` |

### `wsINETER-EXTERNO:Geologico_Minero_de_Nicaragua_Fallas`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `formdeter` | `xsd:string` |
| `tipo` | `xsd:string` |
| `clase` | `xsd:string` |
| `shape_leng` | `xsd:double` |
| `Geologico_Minero_de_Nicaragua_Fallas` | `wsINETER-EXTERNO:Geologico_Minero_de_Nicaragua_FallasType` |

### `wsINETER-EXTERNO:Pendiente_Terreno`

| Campo | Tipo |
|---|---|
| `id` | `xsd:int` |
| `geom` | `gml:MultiSurfacePropertyType` |
| `pendterre` | `xsd:string` |
| `Pendiente_Terreno` | `wsINETER-EXTERNO:Pendiente_TerrenoType` |

### `wsINETER-EXTERNO:PozosEnero`

| Campo | Tipo |
|---|---|
| `coordenadax` | `xsd:decimal` |
| `coordenaday` | `xsd:decimal` |
| `geom` | `gml:PointPropertyType` |
| `tipo` | `xsd:string` |
| `localizacion` | `xsd:string` |
| `propietario` | `xsd:string` |
| `codigopozo` | `xsd:string` |
| `acuifero` | `xsd:string` |
| `elevacion` | `xsd:int` |
| `profundidad` | `xsd:decimal` |
| `nea` | `xsd:decimal` |
| `nda` | `xsd:decimal` |
| `fecha` | `xsd:dateTime` |
| `mes` | `xsd:string` |
| `PozosEnero` | `wsINETER-EXTERNO:PozosEneroType` |

### `wsINETER-EXTERNO:PozosFebrero`

| Campo | Tipo |
|---|---|
| `coordenadax` | `xsd:decimal` |
| `coordenaday` | `xsd:decimal` |
| `geom` | `gml:PointPropertyType` |
| `tipo` | `xsd:string` |
| `localizacion` | `xsd:string` |
| `propietario` | `xsd:string` |
| `codigopozo` | `xsd:string` |
| `acuifero` | `xsd:string` |
| `elevacion` | `xsd:int` |
| `profundidad` | `xsd:decimal` |
| `nea` | `xsd:decimal` |
| `nda` | `xsd:decimal` |
| `fecha` | `xsd:dateTime` |
| `mes` | `xsd:string` |
| `PozosFebrero` | `wsINETER-EXTERNO:PozosFebreroType` |

### `wsINETER-EXTERNO:PozosMarzo`

| Campo | Tipo |
|---|---|
| `coordenadax` | `xsd:decimal` |
| `coordenaday` | `xsd:decimal` |
| `geom` | `gml:PointPropertyType` |
| `tipo` | `xsd:string` |
| `localizacion` | `xsd:string` |
| `propietario` | `xsd:string` |
| `codigopozo` | `xsd:string` |
| `acuifero` | `xsd:string` |
| `elevacion` | `xsd:int` |
| `profundidad` | `xsd:decimal` |
| `nea` | `xsd:decimal` |
| `nda` | `xsd:decimal` |
| `fecha` | `xsd:dateTime` |
| `mes` | `xsd:string` |
| `PozosMarzo` | `wsINETER-EXTERNO:PozosMarzoType` |

### `wsINETER-EXTERNO:Red_Hidrica_Subcuenca_Surmga_2024`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `cuenca` | `xsd:double` |
| `nombre_rio` | `xsd:string` |
| `categoria` | `xsd:string` |
| `tipo_rio` | `xsd:string` |
| `long_km` | `xsd:double` |
| `Red_Hidrica_Subcuenca_Surmga_2024` | `wsINETER-EXTERNO:Red_Hidrica_Subcuenca_Surmga_2024Type` |

### `wsINETER-EXTERNO:Unidades_Subcuenca_Surmga_2024`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `cuenca` | `xsd:string` |
| `area_km` | `xsd:double` |
| `area_mi` | `xsd:double` |
| `terr` | `xsd:string` |
| `area_feet` | `xsd:double` |
| `area_acre` | `xsd:double` |
| `objectid` | `xsd:long` |
| `shape_leng` | `xsd:double` |
| `shape_area` | `xsd:double` |
| `area` | `xsd:double` |
| `perimetro` | `xsd:double` |
| `long` | `xsd:double` |
| `Unidades_Subcuenca_Surmga_2024` | `wsINETER-EXTERNO:Unidades_Subcuenca_Surmga_2024Type` |

### `wsINETER-EXTERNO:Vulnerabilidad_Disponibilidad_Agua`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `id_unico` | `xsd:string` |
| `depto` | `xsd:string` |
| `municipio` | `xsd:string` |
| `id_mun` | `xsd:double` |
| `id_com` | `xsd:double` |
| `area_ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `comun` | `xsd:string` |
| `vuln_` | `xsd:string` |
| `Vulnerabilidad_Disponibilidad_Agua` | `wsINETER-EXTERNO:Vulnerabilidad_Disponibilidad_AguaType` |

### `wsINETER-EXTERNO:Vulnerabilidad_Exposc_Huracanes`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid_1` | `xsd:long` |
| `id_unico` | `xsd:string` |
| `depto` | `xsd:string` |
| `municipio` | `xsd:string` |
| `id_mun` | `xsd:double` |
| `id_com` | `xsd:double` |
| `area_ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `comun` | `xsd:string` |
| `nivelexp` | `xsd:string` |
| `Vulnerabilidad_Exposc_Huracanes` | `wsINETER-EXTERNO:Vulnerabilidad_Exposc_HuracanesType` |

### `wsINETER-EXTERNO:Vulnerabilidad_Exposc_Inundaciones`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `id_unico` | `xsd:string` |
| `depto` | `xsd:string` |
| `municipio` | `xsd:string` |
| `id_mun` | `xsd:double` |
| `id_com` | `xsd:double` |
| `area_ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `comun` | `xsd:string` |
| `nivel_expo` | `xsd:string` |
| `Vulnerabilidad_Exposc_Inundaciones` | `wsINETER-EXTERNO:Vulnerabilidad_Exposc_InundacionesType` |

### `wsINETER-EXTERNO:Vulnerabilidad_Exposc_Sequia_Meteorol`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:long` |
| `id_unico` | `xsd:string` |
| `depto` | `xsd:string` |
| `municipio` | `xsd:string` |
| `id_mun` | `xsd:double` |
| `id_com` | `xsd:double` |
| `area_ha` | `xsd:double` |
| `km2` | `xsd:double` |
| `comun` | `xsd:string` |
| `nivel_expo` | `xsd:string` |
| `Vulnerabilidad_Exposc_Sequia_Meteorol` | `wsINETER-EXTERNO:Vulnerabilidad_Exposc_Sequia_MeteorolType` |

### `wsINETER-GG:Amenaza_Sismica`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `pga` | `xsd:decimal` |
| `Amenaza_Sismica` | `wsINETER-GG:Amenaza_SismicaType` |

### `wsINETER-GG:Amenza_Volcanica_Masaya`

> [!warning] Schema pendente; validar antes de uso.

### `wsINETER-GG:Cenizas_Volcan_Concepcion`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `amenaza` | `xsd:string` |
| `areashape` | `xsd:decimal` |
| `tamanniosh` | `xsd:decimal` |
| `Cenizas_Volcan_Concepcion` | `wsINETER-GG:Cenizas_Volcan_ConcepcionType` |

### `wsINETER-GG:Deslizamientos_Nicaragua_Puntos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `fecha` | `xsd:string` |
| `x` | `xsd:long` |
| `y` | `xsd:long` |
| `institucion` | `xsd:string` |
| `acceso` | `xsd:string` |
| `localidad` | `xsd:string` |
| `comarca` | `xsd:string` |
| `municipio` | `xsd:string` |
| `departamento` | `xsd:string` |
| `tipo` | `xsd:string` |
| `subtipo` | `xsd:string` |
| `sec_estrat` | `xsd:string` |
| `litologia` | `xsd:string` |
| `afectacion` | `xsd:string` |
| `precipitacion` | `xsd:string` |
| `pendiente` | `xsd:string` |
| `fact_condi` | `xsd:string` |
| `fact_desen` | `xsd:string` |
| `uso_de_suelo` | `xsd:string` |
| `descripcion` | `xsd:string` |
| `autor` | `xsd:string` |
| `objectid` | `xsd:long` |
| `id` | `xsd:double` |
| `elaborado` | `xsd:string` |
| `amenaza` | `xsd:string` |
| `ubicacion` | `xsd:string` |
| `nota` | `xsd:string` |
| `point_otro` | `xsd:string` |
| `point_ot_1` | `xsd:string` |
| `Deslizamientos_Nicaragua_Puntos` | `wsINETER-GG:Deslizamientos_Nicaragua_PuntosType` |

### `wsINETER-GG:Fallas_Geologicas_Managua`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `clase` | `xsd:string` |
| `tipo` | `xsd:string` |
| `nombre` | `xsd:string` |
| `rumbo` | `xsd:string` |
| `fuente` | `xsd:string` |
| `length_m` | `xsd:double` |
| `length_km` | `xsd:double` |
| `dir_buzam` | `xsd:string` |
| `buzamiento` | `xsd:int` |
| `metodo` | `xsd:string` |
| `Fallas_Geologicas_Managua` | `wsINETER-GG:Fallas_Geologicas_ManaguaType` |

### `wsINETER-GG:Fallas_Geologicas_Matagalpa`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiCurvePropertyType` |
| `nombre` | `xsd:string` |
| `Fallas_Geologicas_Matagalpa` | `wsINETER-GG:Fallas_Geologicas_MatagalpaType` |

### `wsINETER-GG:Geologia_Peninsula_Chiltepe`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `color` | `xsd:long` |
| `mslink_dmr` | `xsd:decimal` |
| `leyenda` | `xsd:string` |
| `depositos` | `xsd:string` |
| `litologia` | `xsd:string` |
| `granulomet` | `xsd:string` |
| `secuencia` | `xsd:string` |
| `edad` | `xsd:string` |
| `cord_x` | `xsd:decimal` |
| `cord_y` | `xsd:decimal` |
| `Geologia_Peninsula_Chiltepe` | `wsINETER-GG:Geologia_Peninsula_ChiltepeType` |

### `wsINETER-GG:Lahares_Volcan_Concepcion`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:decimal` |
| `amenaza` | `xsd:string` |
| `shape_leng` | `xsd:decimal` |
| `shape_area` | `xsd:decimal` |
| `fuente` | `xsd:string` |
| `Lahares_Volcan_Concepcion` | `wsINETER-GG:Lahares_Volcan_ConcepcionType` |

### `wsINETER-GG:Lava_Concepcion`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:decimal` |
| `amenaza` | `xsd:string` |
| `shape_leng` | `xsd:decimal` |
| `shape_area` | `xsd:decimal` |
| `fuente` | `xsd:string` |
| `Lava_Concepcion` | `wsINETER-GG:Lava_ConcepcionType` |

### `wsINETER-GG:Piroclasticos_Concepcion`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:decimal` |
| `amenaza` | `xsd:string` |
| `shape_leng` | `xsd:decimal` |
| `shape_area` | `xsd:decimal` |
| `fuente` | `xsd:string` |
| `Piroclasticos_Concepcion` | `wsINETER-GG:Piroclasticos_ConcepcionType` |

### `wsINETER-GG:Proyectiles_Balisticos_Concepcion`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:decimal` |
| `amenaza` | `xsd:string` |
| `shape_leng` | `xsd:decimal` |
| `shape_area` | `xsd:decimal` |
| `fuente` | `xsd:string` |
| `Proyectiles_Balisticos_Concepcion` | `wsINETER-GG:Proyectiles_Balisticos_ConcepcionType` |

### `wsINETER-GG:Red_Estaciones_Sismicas_Nicaragua`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `lat` | `xsd:double` |
| `long` | `xsd:double` |
| `altura` | `xsd:double` |
| `nombre` | `xsd:string` |
| `codigo` | `xsd:string` |
| `componente` | `xsd:string` |
| `pais` | `xsd:string` |
| `tipo_comp` | `xsd:string` |
| `funcion` | `xsd:double` |
| `f10` | `xsd:string` |
| `f11` | `xsd:string` |
| `f12` | `xsd:string` |
| `f13` | `xsd:string` |
| `f14` | `xsd:string` |
| `f15` | `xsd:string` |
| `f16` | `xsd:string` |
| `f17` | `xsd:string` |
| `f18` | `xsd:string` |
| `f19` | `xsd:string` |
| `f20` | `xsd:string` |
| `f21` | `xsd:string` |
| `f22` | `xsd:string` |
| `f23` | `xsd:string` |
| `f24` | `xsd:string` |
| `f25` | `xsd:string` |
| `f26` | `xsd:string` |
| `f27` | `xsd:string` |
| `f28` | `xsd:string` |
| `f29` | `xsd:string` |
| `f30` | `xsd:string` |
| `f31` | `xsd:string` |
| `Red_Estaciones_Sismicas_Nicaragua` | `wsINETER-GG:Red_Estaciones_Sismicas_NicaraguaType` |

### `wsINETER-RH:INUNDACIONES`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `objectid` | `xsd:int` |
| `objectid_1` | `xsd:int` |
| `poten_inun` | `xsd:string` |
| `ubicacion` | `xsd:string` |
| `fuente` | `xsd:string` |
| `INUNDACIONES` | `wsINETER-RH:INUNDACIONESType` |

### `wsINETER-RH:Mapa_Nacional_Susceptible_Inundacion_2021`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiSurfacePropertyType` |
| `objectid` | `xsd:int` |
| `objectid_1` | `xsd:int` |
| `poten_inun` | `xsd:string` |
| `ubicacion` | `xsd:string` |
| `fuente` | `xsd:string` |
| `Mapa_Nacional_Susceptible_Inundacion_2021` | `wsINETER-RH:Mapa_Nacional_Susceptible_Inundacion_2021Type` |

### `wsINSTITUCION:Centros_Desarrollo_Infantil`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `nombre` | `xsd:string` |
| `departamento` | `xsd:string` |
| `codigo` | `xsd:long` |
| `municipio` | `xsd:string` |
| `direccion` | `xsd:string` |
| `lactante_f` | `xsd:long` |
| `lactante_m` | `xsd:long` |
| `infante_f` | `xsd:long` |
| `infante_m` | `xsd:long` |
| `i_nivel_f` | `xsd:long` |
| `i_nivel_m` | `xsd:long` |
| `ii_nivel_f` | `xsd:long` |
| `ii_nivel_m` | `xsd:long` |
| `iii_nivel_f` | `xsd:long` |
| `iii_nive_m` | `xsd:long` |
| `total_f` | `xsd:long` |
| `total_m` | `xsd:long` |
| `total` | `xsd:long` |
| `educadoras` | `xsd:long` |
| `x_utm` | `xsd:decimal` |
| `y_utm` | `xsd:decimal` |
| `anio_periodo` | `xsd:long` |
| `mes_periodo` | `xsd:long` |
| `Centros_Desarrollo_Infantil` | `wsINSTITUCION:Centros_Desarrollo_InfantilType` |

### `wsINSTITUCION:cnu-2025`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `cod` | `xsd:long` |
| `universidad` | `xsd:string` |
| `sedes` | `xsd:string` |
| `siglas` | `xsd:string` |
| `institucion` | `xsd:string` |
| `latitud` | `xsd:string` |
| `longitud` | `xsd:string` |
| `y` | `xsd:decimal` |
| `x` | `xsd:decimal` |
| `departamento` | `xsd:string` |
| `zona` | `xsd:string` |
| `direccion` | `xsd:string` |
| `correo` | `xsd:string` |
| `web` | `xsd:string` |
| `telefono` | `xsd:long` |
| `estudiante` | `xsd:string` |
| `docentes` | `xsd:long` |
| `aulas` | `xsd:string` |
| `biblioteca` | `xsd:string` |
| `laboratorios` | `xsd:string` |
| `campos_deportivos` | `xsd:long` |
| `centros_investigacion` | `xsd:long` |
| `talleres` | `xsd:long` |
| `arec` | `xsd:string` |
| `aret` | `xsd:string` |
| `cnu-2025` | `wsINSTITUCION:cnu-2025Type` |

### `wsINSTITUCION:CNU_Privadas`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `universida` | `xsd:string` |
| `latitud` | `xsd:decimal` |
| `longitud` | `xsd:string` |
| `x` | `xsd:decimal` |
| `y` | `xsd:decimal` |
| `direccion` | `xsd:string` |
| `telefono` | `xsd:string` |
| `departamen` | `xsd:string` |
| `municipio` | `xsd:string` |
| `oferta` | `xsd:string` |
| `dependenci` | `xsd:string` |
| `zona` | `xsd:string` |
| `CNU_Privadas` | `wsINSTITUCION:CNU_PrivadasType` |

### `wsINSTITUCION:CNU_Publicas`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `cod` | `xsd:string` |
| `uni` | `xsd:string` |
| `sedes` | `xsd:string` |
| `descrip` | `xsd:string` |
| `latitud` | `xsd:decimal` |
| `longitud` | `xsd:decimal` |
| `x` | `xsd:decimal` |
| `y` | `xsd:decimal` |
| `depart` | `xsd:string` |
| `zona` | `xsd:string` |
| `direcc` | `xsd:string` |
| `correo` | `xsd:string` |
| `sweb` | `xsd:string` |
| `telef` | `xsd:string` |
| `estudia` | `xsd:string` |
| `profe` | `xsd:string` |
| `aulas` | `xsd:decimal` |
| `biblio` | `xsd:decimal` |
| `labor` | `xsd:decimal` |
| `campdep` | `xsd:string` |
| `centinvest` | `xsd:decimal` |
| `talle` | `xsd:decimal` |
| `arec` | `xsd:string` |
| `aret` | `xsd:string` |
| `municipio` | `xsd:string` |
| `CNU_Publicas` | `wsINSTITUCION:CNU_PublicasType` |

### `wsINSTITUCION:Estaciones_Bomberos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `Depto` | `xsd:string` |
| `Municipio` | `xsd:string` |
| `Direccion` | `xsd:string` |
| `Institucion` | `xsd:string` |
| `Jefe` | `xsd:string` |
| `Telefono` | `xsd:string` |
| `CantidadBomberos` | `xsd:long` |
| `Autocisterna` | `xsd:long` |
| `Cisterna` | `xsd:long` |
| `Ambulancias` | `xsd:long` |
| `Rescate` | `xsd:long` |
| `Total` | `xsd:long` |
| `Estaciones_Bomberos` | `wsINSTITUCION:Estaciones_BomberosType` |

### `wsINSTITUCION:Hidrantes_Managua`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `FechaVerificacion` | `xsd:date` |
| `Hidrantes_Managua` | `wsINSTITUCION:Hidrantes_ManaguaType` |

### `wsINSTITUCION:Mined_Privados`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `codigo` | `xsd:double` |
| `municipio` | `xsd:string` |
| `localidad` | `xsd:string` |
| `zona` | `xsd:string` |
| `nombre_centro` | `xsd:string` |
| `matricula2017` | `xsd:double` |
| `año_remodelacion` | `xsd:string` |
| `monto_remodelacion` | `xsd:string` |
| `Mined_Privados` | `wsINSTITUCION:Mined_PrivadosType` |

### `wsINSTITUCION:Mined_Publicos`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `codigo` | `xsd:double` |
| `municipio` | `xsd:string` |
| `localidad` | `xsd:string` |
| `zona` | `xsd:string` |
| `nombre_centro` | `xsd:string` |
| `cantida_aulas` | `xsd:double` |
| `Matricula_2017` | `xsd:double` |
| `año_remodelacion` | `xsd:string` |
| `monto_remodelacion` | `xsd:string` |
| `Mined_Publicos` | `wsINSTITUCION:Mined_PublicosType` |

### `wsINSTITUCION:Plantas_enatrel`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `Depto` | `xsd:string` |
| `Municipio` | `xsd:string` |
| `Nombre` | `xsd:string` |
| `Direccion` | `xsd:string` |
| `TipoComustible` | `xsd:string` |
| `TotalTanquesComustible` | `xsd:long` |
| `Capacidad` | `xsd:long` |
| `Maleza300mtrs` | `xsd:string` |
| `VegetacionCercana` | `xsd:string` |
| `MateriaPrimaOtraEmpresa` | `xsd:string` |
| ` AccesibleSoloVerano` | `xsd:string` |
| `AccesibleTodoTiempo ` | `xsd:string` |
| `DistancisBomberos` | `xsd:string` |
| `AfectacionesPoblacion300M` | `xsd:string` |
| `AfectacionesInfraestructura300M` | `xsd:string` |
| `Plantas_enatrel` | `wsINSTITUCION:Plantas_enatrelType` |

### `wsINSTITUCION:Plantas_Generadoras`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `x` | `xsd:long` |
| `y` | `xsd:long` |
| `ubicacion` | `xsd:string` |
| `nombre` | `xsd:string` |
| `tipo` | `xsd:string` |
| `capacidad` | `xsd:string` |
| `anio_oper` | `xsd:long` |
| `longitud` | `xsd:double` |
| `latitud` | `xsd:double` |
| `Plantas_Generadoras` | `wsINSTITUCION:Plantas_GeneradorasType` |

### `wsINSTITUCION:Puentes`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `Km_desde_Managua` | `xsd:string` |
| `Nombre` | `xsd:string` |
| `Longitud_m` | `xsd:string` |
| `Clasificacion` | `xsd:string` |
| `Puentes` | `wsINSTITUCION:PuentesType` |

### `wsINSTITUCION:Seguridad_Social_INSS`

| Campo | Tipo |
|---|---|
| `geom` | `gml:GeometryPropertyType` |
| `nombre` | `xsd:string` |
| `cantidad_asegurados` | `xsd:decimal` |
| `cantidad_adultomayor` | `xsd:decimal` |
| `anio_periodo` | `xsd:long` |
| `mes_periodo` | `xsd:long` |
| `Seguridad_Social_INSS` | `wsINSTITUCION:Seguridad_Social_INSSType` |

### `wsINSTITUCION:v_Casas_Maternas2019`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `nombre` | `xsd:string` |
| `departamento` | `xsd:string` |
| `municipios` | `xsd:string` |
| `localidad` | `xsd:string` |
| `ubicacion` | `xsd:string` |
| `tipo_unidad` | `xsd:string` |
| `municipio_atiende` | `xsd:string` |
| `v_Casas_Maternas2019` | `wsINSTITUCION:v_Casas_Maternas2019Type` |

### `wsINSTITUCION:v_Clinicas_Medicina_Natural`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `Municipio` | `xsd:string` |
| `SILAIS` | `xsd:string` |
| `Unidad` | `xsd:string` |
| `Dirección` | `xsd:string` |
| `v_Clinicas_Medicina_Natural` | `wsINSTITUCION:v_Clinicas_Medicina_NaturalType` |

### `wsINSTITUCION:v_minsa2019`

| Campo | Tipo |
|---|---|
| `geom` | `gml:MultiPointPropertyType` |
| `nombre` | `xsd:string` |
| `departamento` | `xsd:string` |
| `municipio` | `xsd:string` |
| `municipio_atiende` | `xsd:string` |
| `localidad` | `xsd:string` |
| `ubicacion` | `xsd:string` |
| `tipo_unidad` | `xsd:string` |
| `tipo_unidad2` | `xsd:string` |
| `poblacion` | `xsd:string` |
| `medicos` | `xsd:long` |
| `enfermeras` | `xsd:long` |
| `auxiliares_enfermeria` | `xsd:long` |
| `cantidad_banios` | `xsd:long` |
| `cantidad_camillas` | `xsd:long` |
| `disponible_farmacia` | `xsd:long` |
| `disponible_lab` | `xsd:long` |
| `tanque_agua` | `xsd:string` |
| `planta_electrica` | `xsd:long` |
| `cantidad_entradas` | `xsd:long` |
| `v_minsa2019` | `wsINSTITUCION:v_minsa2019Type` |
