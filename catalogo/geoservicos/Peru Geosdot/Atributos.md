# Plataforma Nacional de Datos Georreferenciados — Geosdot — atributos das camadas

Geoportal: [[Geosserviços/Peru Geosdot/Plataforma Nacional de Datos Georreferenciados — Geosdot|Plataforma Nacional de Datos Georreferenciados — Geosdot]]

Campos declarados no `DescribeFeatureType`.

### `geoportal:aerodromo_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nombre` | `xsd:string` | true | 0..1 |
| `label` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `codidep` | `xsd:string` | true | 0..1 |
| `nombdep` | `xsd:string` | true | 0..1 |
| `nombprov` | `xsd:string` | true | 0..1 |
| `nombdist` | `xsd:string` | true | 0..1 |
| `escala` | `xsd:string` | true | 0..1 |
| `lat` | `xsd:string` | true | 0..1 |
| `lon` | `xsd:string` | true | 0..1 |
| `estado` | `xsd:string` | true | 0..1 |
| `administ` | `xsd:string` | true | 0..1 |
| `jerarquia` | `xsd:string` | true | 0..1 |
| `titular` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `geoportal:areas_exposicion_inundacion`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `objectid` | `xsd:long` | true | 0..1 |
| `ubi_dep` | `xsd:string` | true | 0..1 |
| `ubi_prov` | `xsd:string` | true | 0..1 |
| `ubi_dis` | `xsd:string` | true | 0..1 |
| `nom_dep` | `xsd:string` | true | 0..1 |
| `nom_prov` | `xsd:string` | true | 0..1 |
| `nom_dist` | `xsd:string` | true | 0..1 |
| `nom_lugar` | `xsd:string` | true | 0..1 |
| `nom_rio` | `xsd:string` | true | 0..1 |
| `tipo_inu2` | `xsd:string` | true | 0..1 |
| `fuente` | `xsd:string` | true | 0..1 |
| `fecha_doc` | `xsd:dateTime` | true | 0..1 |
| `des_inu` | `xsd:string` | true | 0..1 |
| `fech_inu` | `xsd:dateTime` | true | 0..1 |
| `area_inu` | `xsd:double` | true | 0..1 |
| `umbral` | `xsd:double` | true | 0..1 |
| `url` | `xsd:string` | true | 0..1 |
| `url_img` | `xsd:string` | true | 0..1 |
| `url1` | `xsd:string` | true | 0..1 |
| `url1_img` | `xsd:string` | true | 0..1 |
| `url2` | `xsd:string` | true | 0..1 |
| `url2_img` | `xsd:string` | true | 0..1 |
| `observ` | `xsd:string` | true | 0..1 |
| `fuente_log` | `xsd:string` | true | 0..1 |
| `operador` | `xsd:string` | true | 0..1 |
| `fecha_ed` | `xsd:dateTime` | true | 0..1 |
| `ubigeo` | `xsd:string` | true | 0..1 |
| `departamento` | `xsd:string` | true | 0..1 |
| `provincia` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `geoportal:areas_exposicion_movimientos_masa`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `objectid` | `xsd:long` | true | 0..1 |
| `ubi_dep` | `xsd:string` | true | 0..1 |
| `ubi_prov` | `xsd:string` | true | 0..1 |
| `ubi_dist` | `xsd:string` | true | 0..1 |
| `nom_dep` | `xsd:string` | true | 0..1 |
| `nom_prov` | `xsd:string` | true | 0..1 |
| `nom_dist` | `xsd:string` | true | 0..1 |
| `nom_lugar` | `xsd:string` | true | 0..1 |
| `tip_peligro` | `xsd:string` | true | 0..1 |
| `peligro_esp` | `xsd:string` | true | 0..1 |
| `descrip` | `xsd:string` | true | 0..1 |
| `fecha_doc` | `xsd:dateTime` | true | 0..1 |
| `fuente` | `xsd:string` | true | 0..1 |
| `fuente_log` | `xsd:string` | true | 0..1 |
| `url` | `xsd:string` | true | 0..1 |
| `url_img` | `xsd:string` | true | 0..1 |
| `fecha_ed` | `xsd:dateTime` | true | 0..1 |
| `operador` | `xsd:string` | true | 0..1 |
| `url1` | `xsd:string` | true | 0..1 |
| `url1_img` | `xsd:string` | true | 0..1 |
| `url2` | `xsd:string` | true | 0..1 |
| `url2_img` | `xsd:string` | true | 0..1 |
| `observ` | `xsd:string` | true | 0..1 |
| `oculto` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `geoportal:ccpp150_vab_callao`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `ubigeo` | `xsd:string` | true | 0..1 |
| `codcp` | `xsd:string` | true | 0..1 |
| `departamen` | `xsd:string` | true | 0..1 |
| `provincia` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:string` | true | 0..1 |
| `cen_pob` | `xsd:string` | true | 0..1 |
| `pob` | `xsd:double` | true | 0..1 |
| `viv` | `xsd:double` | true | 0..1 |
| `viv_part` | `xsd:double` | true | 0..1 |
| `viv_part_o` | `xsd:double` | true | 0..1 |
| `viv_part_1` | `xsd:double` | true | 0..1 |
| `pob_viv_pa` | `xsd:double` | true | 0..1 |
| `y` | `xsd:double` | true | 0..1 |
| `x` | `xsd:double` | true | 0..1 |
| `fuente_fin` | `xsd:string` | true | 0..1 |
| `revision` | `xsd:string` | true | 0..1 |
| `estado_coo` | `xsd:string` | true | 0..1 |
| `empate` | `xsd:string` | true | 0..1 |
| `ubigeo1` | `xsd:string` | true | 0..1 |
| `r` | `xsd:string` | true | 0..1 |
| `dfp` | `xsd:string` | true | 0..1 |
| `urb_rur` | `xsd:string` | true | 0..1 |
| `obs_u_r` | `xsd:string` | true | 0..1 |
| `idprov` | `xsd:string` | true | 0..1 |
| `capital` | `xsd:string` | true | 0..1 |
| `vab_total` | `xsd:decimal` | true | 0..1 |

### `geoportal:ccpp150_vab_lima`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `ubigeo` | `xsd:string` | true | 0..1 |
| `codcp` | `xsd:string` | true | 0..1 |
| `departamen` | `xsd:string` | true | 0..1 |
| `provincia` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:string` | true | 0..1 |
| `cen_pob` | `xsd:string` | true | 0..1 |
| `pob` | `xsd:double` | true | 0..1 |
| `viv` | `xsd:double` | true | 0..1 |
| `viv_part` | `xsd:double` | true | 0..1 |
| `viv_part_o` | `xsd:double` | true | 0..1 |
| `viv_part_1` | `xsd:double` | true | 0..1 |
| `pob_viv_pa` | `xsd:double` | true | 0..1 |
| `y` | `xsd:double` | true | 0..1 |
| `x` | `xsd:double` | true | 0..1 |
| `fuente_fin` | `xsd:string` | true | 0..1 |
| `revision` | `xsd:string` | true | 0..1 |
| `estado_coo` | `xsd:string` | true | 0..1 |
| `empate` | `xsd:string` | true | 0..1 |
| `ubigeo1` | `xsd:string` | true | 0..1 |
| `r` | `xsd:string` | true | 0..1 |
| `dfp` | `xsd:string` | true | 0..1 |
| `urb_rur` | `xsd:string` | true | 0..1 |
| `obs_u_r` | `xsd:string` | true | 0..1 |
| `idprov` | `xsd:string` | true | 0..1 |
| `capital` | `xsd:string` | true | 0..1 |
| `vab_total` | `xsd:decimal` | true | 0..1 |

### `geoportal:ccpp150_vab_total`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `ubigeo` | `xsd:string` | true | 0..1 |
| `codcp` | `xsd:string` | true | 0..1 |
| `departamen` | `xsd:string` | true | 0..1 |
| `provincia` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:string` | true | 0..1 |
| `cen_pob` | `xsd:string` | true | 0..1 |
| `pob` | `xsd:double` | true | 0..1 |
| `viv` | `xsd:double` | true | 0..1 |
| `viv_part` | `xsd:double` | true | 0..1 |
| `viv_part_o` | `xsd:double` | true | 0..1 |
| `viv_part_1` | `xsd:double` | true | 0..1 |
| `pob_viv_pa` | `xsd:double` | true | 0..1 |
| `y` | `xsd:double` | true | 0..1 |
| `x` | `xsd:double` | true | 0..1 |
| `fuente_fin` | `xsd:string` | true | 0..1 |
| `revision` | `xsd:string` | true | 0..1 |
| `estado_coo` | `xsd:string` | true | 0..1 |
| `empate` | `xsd:string` | true | 0..1 |
| `ubigeo1` | `xsd:string` | true | 0..1 |
| `r` | `xsd:string` | true | 0..1 |
| `dfp` | `xsd:string` | true | 0..1 |
| `urb_rur` | `xsd:string` | true | 0..1 |
| `obs_u_r` | `xsd:string` | true | 0..1 |
| `idprov` | `xsd:string` | true | 0..1 |
| `capital` | `xsd:string` | true | 0..1 |
| `vab_total` | `xsd:decimal` | true | 0..1 |

### `geoportal:ccpp_asentamientos_dispersos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ubigeo` | `xsd:string` | true | 0..1 |
| `codccpp` | `xsd:string` | true | 0..1 |
| `nombdep` | `xsd:string` | true | 0..1 |
| `nombprov` | `xsd:string` | true | 0..1 |
| `nombdist` | `xsd:string` | true | 0..1 |
| `cen_pob` | `xsd:string` | true | 0..1 |
| `pob` | `xsd:int` | true | 0..1 |
| `viv` | `xsd:int` | true | 0..1 |
| `viv_part` | `xsd:int` | true | 0..1 |
| `viv_part_o` | `xsd:int` | true | 0..1 |
| `viv_part_1` | `xsd:int` | true | 0..1 |
| `pob_viv_pa` | `xsd:int` | true | 0..1 |
| `y` | `xsd:decimal` | true | 0..1 |
| `x` | `xsd:decimal` | true | 0..1 |
| `fuente` | `xsd:string` | true | 0..1 |
| `revision` | `xsd:string` | true | 0..1 |
| `cap` | `xsd:string` | true | 0..1 |
| `capital` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `iddpto` | `xsd:string` | true | 0..1 |
| `idprov` | `xsd:string` | true | 0..1 |

### `geoportal:cobertura_movil_oper`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `n` | `xsd:long` | true | 0..1 |
| `ubigeo_ccp` | `xsd:string` | true | 0..1 |
| `departamen` | `xsd:string` | true | 0..1 |
| `provincia` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:string` | true | 0..1 |
| `centro_pob` | `xsd:string` | true | 0..1 |
| `y_latitud` | `xsd:decimal` | true | 0..1 |
| `x_longitud` | `xsd:string` | true | 0..1 |
| `emoperador` | `xsd:long` | true | 0..1 |
| `2g` | `xsd:long` | true | 0..1 |
| `3g` | `xsd:long` | true | 0..1 |
| `4g` | `xsd:long` | true | 0..1 |
| `5g` | `xsd:long` | true | 0..1 |
| `voz` | `xsd:long` | true | 0..1 |
| `sms` | `xsd:long` | true | 0..1 |
| `mms` | `xsd:long` | true | 0..1 |
| `hasta1mbps` | `xsd:long` | true | 0..1 |
| `masde1mbps` | `xsd:long` | true | 0..1 |
| `canteb2g` | `xsd:long` | true | 0..1 |
| `canteb3g` | `xsd:long` | true | 0..1 |
| `canteb4g` | `xsd:long` | true | 0..1 |
| `canteb5g` | `xsd:long` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |

### `geoportal:cobertura_movil_tipo`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `n` | `xsd:long` | true | 0..1 |
| `ubigeo_ccp` | `xsd:string` | true | 0..1 |
| `departamen` | `xsd:string` | true | 0..1 |
| `provincia` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:string` | true | 0..1 |
| `centro_pob` | `xsd:string` | true | 0..1 |
| `y_latitud` | `xsd:decimal` | true | 0..1 |
| `x_longitud` | `xsd:string` | true | 0..1 |
| `emoperador` | `xsd:long` | true | 0..1 |
| `2g` | `xsd:long` | true | 0..1 |
| `3g` | `xsd:long` | true | 0..1 |
| `4g` | `xsd:long` | true | 0..1 |
| `5g` | `xsd:long` | true | 0..1 |
| `voz` | `xsd:long` | true | 0..1 |
| `sms` | `xsd:long` | true | 0..1 |
| `mms` | `xsd:long` | true | 0..1 |
| `hasta1mbps` | `xsd:long` | true | 0..1 |
| `masde1mbps` | `xsd:long` | true | 0..1 |
| `canteb2g` | `xsd:long` | true | 0..1 |
| `canteb3g` | `xsd:long` | true | 0..1 |
| `canteb4g` | `xsd:long` | true | 0..1 |
| `canteb5g` | `xsd:long` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |

### `geoportal:densidad_comercio`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `gridcode` | `xsd:long` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `nivel` | `xsd:string` | true | 0..1 |
| `rango` | `xsd:string` | true | 0..1 |

### `geoportal:densidad_comercio_10km`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `gridcode` | `xsd:long` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `nivel` | `xsd:string` | true | 0..1 |
| `rango` | `xsd:string` | true | 0..1 |

### `geoportal:densidad_comercio_1km`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `gridcode` | `xsd:long` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `nivel` | `xsd:string` | true | 0..1 |
| `rango` | `xsd:string` | true | 0..1 |

### `geoportal:densidad_comercio_30km`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `gridcode` | `xsd:long` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `nivel` | `xsd:string` | true | 0..1 |
| `rango` | `xsd:string` | true | 0..1 |

### `geoportal:densidad_crecimiento_pob_ccpp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `nro` | `xsd:string` | true | 0..1 |
| `codccpp` | `xsd:string` | true | 0..1 |
| `ubigeo` | `xsd:string` | true | 0..1 |
| `dep` | `xsd:string` | true | 0..1 |
| `prov` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:string` | true | 0..1 |
| `centro_pob` | `xsd:string` | true | 0..1 |
| `pob_2007` | `xsd:string` | true | 0..1 |
| `pob_2017` | `xsd:string` | true | 0..1 |
| `tasa` | `xsd:decimal` | true | 0..1 |
| `capital` | `xsd:string` | true | 0..1 |
| `region` | `xsd:string` | true | 0..1 |
| `urb_rural` | `xsd:string` | true | 0..1 |
| `tc_catg` | `xsd:string` | true | 0..1 |

### `geoportal:densidad_crecimiento_poblacional`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `gridcode` | `xsd:long` | true | 0..1 |
| `nivel` | `xsd:string` | true | 0..1 |
| `rango` | `xsd:string` | true | 0..1 |
| `descrip` | `xsd:string` | true | 0..1 |

### `geoportal:densidad_mercado`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `gridcode` | `xsd:long` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `nivel` | `xsd:string` | true | 0..1 |
| `rango` | `xsd:string` | true | 0..1 |

### `geoportal:densidad_mercado_10km`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `gridcode` | `xsd:long` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `nivel` | `xsd:string` | true | 0..1 |
| `rango` | `xsd:string` | true | 0..1 |

### `geoportal:densidad_mercado_1km`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `gridcode` | `xsd:long` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `nivel` | `xsd:string` | true | 0..1 |
| `rango` | `xsd:string` | true | 0..1 |

### `geoportal:densidad_mercado_30km`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `gridcode` | `xsd:long` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `nivel` | `xsd:string` | true | 0..1 |
| `rango` | `xsd:string` | true | 0..1 |

### `geoportal:densidad_servicio_financiero`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `gridcode` | `xsd:long` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `rango` | `xsd:string` | true | 0..1 |
| `nivel` | `xsd:string` | true | 0..1 |

### `geoportal:densidad_servicio_financiero_10km`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `gridcode` | `xsd:long` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `rango` | `xsd:string` | true | 0..1 |
| `nivel` | `xsd:string` | true | 0..1 |

### `geoportal:densidad_servicio_financiero_2km`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `gridcode` | `xsd:long` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `rango` | `xsd:string` | true | 0..1 |
| `nivel` | `xsd:string` | true | 0..1 |

### `geoportal:densidad_servicio_financiero_30km`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `gridcode` | `xsd:long` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `rango` | `xsd:string` | true | 0..1 |
| `nivel` | `xsd:string` | true | 0..1 |

### `geoportal:densidad_viviendas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `gridcode` | `xsd:long` | true | 0..1 |
| `rango` | `xsd:string` | true | 0..1 |

### `geoportal:densidad_viviendas_12km`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `densidad` | `xsd:decimal` | true | 0..1 |
| `idcuadric` | `xsd:string` | true | 0..1 |
| `idnum` | `xsd:string` | true | 0..1 |
| `depa` | `xsd:string` | true | 0..1 |
| `idunico` | `xsd:decimal` | true | 0..1 |
| `categoria` | `xsd:decimal` | true | 0..1 |
| `disolve` | `xsd:string` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |

### `geoportal:densidad_viviendas_7km`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `densidad` | `xsd:decimal` | true | 0..1 |
| `idcuadric` | `xsd:string` | true | 0..1 |
| `idnum` | `xsd:string` | true | 0..1 |
| `depa` | `xsd:string` | true | 0..1 |
| `idunico` | `xsd:decimal` | true | 0..1 |
| `categoria` | `xsd:decimal` | true | 0..1 |
| `disolve` | `xsd:string` | true | 0..1 |

### `geoportal:evaluacion_riesgos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id_documen` | `xsd:decimal` | true | 0..1 |
| `nombre` | `xsd:string` | true | 0..1 |
| `tipo_docum` | `xsd:string` | true | 0..1 |
| `anio` | `xsd:double` | true | 0..1 |
| `ciudad` | `xsd:string` | true | 0..1 |
| `editorial` | `xsd:string` | true | 0..1 |
| `descripcio` | `xsd:string` | true | 0..1 |
| `keywords` | `xsd:string` | true | 0..1 |
| `ambito` | `xsd:string` | true | 0..1 |
| `autor_corp` | `xsd:string` | true | 0..1 |
| `url` | `xsd:string` | true | 0..1 |
| `tiene_imag` | `xsd:double` | true | 0..1 |
| `tiene_docu` | `xsd:double` | true | 0..1 |
| `updated_at` | `xsd:string` | true | 0..1 |
| `autor_co_1` | `xsd:string` | true | 0..1 |
| `estado` | `xsd:string` | true | 0..1 |
| `created_at` | `xsd:string` | true | 0..1 |
| `pma` | `xsd:decimal` | true | 0..1 |
| `pa` | `xsd:decimal` | true | 0..1 |
| `vma` | `xsd:decimal` | true | 0..1 |
| `va` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `geoportal:flujo_est_1000_3500`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `salen` | `xsd:string` | true | 0..1 |
| `dep_salen` | `xsd:string` | true | 0..1 |
| `prov_salen` | `xsd:string` | true | 0..1 |
| `dist_salen` | `xsd:string` | true | 0..1 |
| `entran` | `xsd:string` | true | 0..1 |
| `dep_entran` | `xsd:string` | true | 0..1 |
| `prov_entra` | `xsd:string` | true | 0..1 |
| `dist_entra` | `xsd:string` | true | 0..1 |
| `x_salen` | `xsd:decimal` | true | 0..1 |
| `y_salen` | `xsd:decimal` | true | 0..1 |
| `valor` | `xsd:long` | true | 0..1 |
| `hubname` | `xsd:string` | true | 0..1 |
| `hubdist` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `geoportal:flujo_est_100_1000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `salen` | `xsd:string` | true | 0..1 |
| `dep_salen` | `xsd:string` | true | 0..1 |
| `prov_salen` | `xsd:string` | true | 0..1 |
| `dist_salen` | `xsd:string` | true | 0..1 |
| `entran` | `xsd:string` | true | 0..1 |
| `dep_entran` | `xsd:string` | true | 0..1 |
| `prov_entra` | `xsd:string` | true | 0..1 |
| `dist_entra` | `xsd:string` | true | 0..1 |
| `x_salen` | `xsd:decimal` | true | 0..1 |
| `y_salen` | `xsd:decimal` | true | 0..1 |
| `valor` | `xsd:long` | true | 0..1 |
| `hubname` | `xsd:string` | true | 0..1 |
| `hubdist` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `geoportal:flujo_est_13000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `salen` | `xsd:string` | true | 0..1 |
| `dep_salen` | `xsd:string` | true | 0..1 |
| `prov_salen` | `xsd:string` | true | 0..1 |
| `dist_salen` | `xsd:string` | true | 0..1 |
| `entran` | `xsd:string` | true | 0..1 |
| `dep_entran` | `xsd:string` | true | 0..1 |
| `prov_entra` | `xsd:string` | true | 0..1 |
| `dist_entra` | `xsd:string` | true | 0..1 |
| `x_salen` | `xsd:decimal` | true | 0..1 |
| `y_salen` | `xsd:decimal` | true | 0..1 |
| `valor` | `xsd:long` | true | 0..1 |
| `hubname` | `xsd:string` | true | 0..1 |
| `hubdist` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `geoportal:flujo_est_3500_7000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `salen` | `xsd:string` | true | 0..1 |
| `dep_salen` | `xsd:string` | true | 0..1 |
| `prov_salen` | `xsd:string` | true | 0..1 |
| `dist_salen` | `xsd:string` | true | 0..1 |
| `entran` | `xsd:string` | true | 0..1 |
| `dep_entran` | `xsd:string` | true | 0..1 |
| `prov_entra` | `xsd:string` | true | 0..1 |
| `dist_entra` | `xsd:string` | true | 0..1 |
| `x_salen` | `xsd:decimal` | true | 0..1 |
| `y_salen` | `xsd:decimal` | true | 0..1 |
| `valor` | `xsd:long` | true | 0..1 |
| `hubname` | `xsd:string` | true | 0..1 |
| `hubdist` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `geoportal:flujo_est_7000_13000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `salen` | `xsd:string` | true | 0..1 |
| `dep_salen` | `xsd:string` | true | 0..1 |
| `prov_salen` | `xsd:string` | true | 0..1 |
| `dist_salen` | `xsd:string` | true | 0..1 |
| `entran` | `xsd:string` | true | 0..1 |
| `dep_entran` | `xsd:string` | true | 0..1 |
| `prov_entra` | `xsd:string` | true | 0..1 |
| `dist_entra` | `xsd:string` | true | 0..1 |
| `x_salen` | `xsd:decimal` | true | 0..1 |
| `y_salen` | `xsd:decimal` | true | 0..1 |
| `valor` | `xsd:long` | true | 0..1 |
| `hubname` | `xsd:string` | true | 0..1 |
| `hubdist` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `geoportal:flujo_trb_10000_25000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `salen` | `xsd:string` | true | 0..1 |
| `dep_salen` | `xsd:string` | true | 0..1 |
| `prov_salen` | `xsd:string` | true | 0..1 |
| `dist_salen` | `xsd:string` | true | 0..1 |
| `entran` | `xsd:string` | true | 0..1 |
| `dep_entran` | `xsd:string` | true | 0..1 |
| `prov_entra` | `xsd:string` | true | 0..1 |
| `dist_entra` | `xsd:string` | true | 0..1 |
| `x_salen` | `xsd:decimal` | true | 0..1 |
| `y_salen` | `xsd:decimal` | true | 0..1 |
| `valor` | `xsd:long` | true | 0..1 |
| `hubname` | `xsd:string` | true | 0..1 |
| `hubdist` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `geoportal:flujo_trb_100_1500`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `salen` | `xsd:string` | true | 0..1 |
| `dep_salen` | `xsd:string` | true | 0..1 |
| `prov_salen` | `xsd:string` | true | 0..1 |
| `dist_salen` | `xsd:string` | true | 0..1 |
| `entran` | `xsd:string` | true | 0..1 |
| `dep_entran` | `xsd:string` | true | 0..1 |
| `prov_entra` | `xsd:string` | true | 0..1 |
| `dist_entra` | `xsd:string` | true | 0..1 |
| `x_salen` | `xsd:decimal` | true | 0..1 |
| `y_salen` | `xsd:decimal` | true | 0..1 |
| `valor` | `xsd:long` | true | 0..1 |
| `hubname` | `xsd:string` | true | 0..1 |
| `hubdist` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `geoportal:flujo_trb_1500_5000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `salen` | `xsd:string` | true | 0..1 |
| `dep_salen` | `xsd:string` | true | 0..1 |
| `prov_salen` | `xsd:string` | true | 0..1 |
| `dist_salen` | `xsd:string` | true | 0..1 |
| `entran` | `xsd:string` | true | 0..1 |
| `dep_entran` | `xsd:string` | true | 0..1 |
| `prov_entra` | `xsd:string` | true | 0..1 |
| `dist_entra` | `xsd:string` | true | 0..1 |
| `x_salen` | `xsd:decimal` | true | 0..1 |
| `y_salen` | `xsd:decimal` | true | 0..1 |
| `valor` | `xsd:long` | true | 0..1 |
| `hubname` | `xsd:string` | true | 0..1 |
| `hubdist` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `geoportal:flujo_trb_25000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `salen` | `xsd:string` | true | 0..1 |
| `dep_salen` | `xsd:string` | true | 0..1 |
| `prov_salen` | `xsd:string` | true | 0..1 |
| `dist_salen` | `xsd:string` | true | 0..1 |
| `entran` | `xsd:string` | true | 0..1 |
| `dep_entran` | `xsd:string` | true | 0..1 |
| `prov_entra` | `xsd:string` | true | 0..1 |
| `dist_entra` | `xsd:string` | true | 0..1 |
| `x_salen` | `xsd:decimal` | true | 0..1 |
| `y_salen` | `xsd:decimal` | true | 0..1 |
| `valor` | `xsd:long` | true | 0..1 |
| `hubname` | `xsd:string` | true | 0..1 |
| `hubdist` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `geoportal:flujo_trb_5000_10000`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `salen` | `xsd:string` | true | 0..1 |
| `dep_salen` | `xsd:string` | true | 0..1 |
| `prov_salen` | `xsd:string` | true | 0..1 |
| `dist_salen` | `xsd:string` | true | 0..1 |
| `entran` | `xsd:string` | true | 0..1 |
| `dep_entran` | `xsd:string` | true | 0..1 |
| `prov_entra` | `xsd:string` | true | 0..1 |
| `dist_entra` | `xsd:string` | true | 0..1 |
| `x_salen` | `xsd:decimal` | true | 0..1 |
| `y_salen` | `xsd:decimal` | true | 0..1 |
| `valor` | `xsd:long` | true | 0..1 |
| `hubname` | `xsd:string` | true | 0..1 |
| `hubdist` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `geoportal:instituciones_prestadoras_servicios_salud`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `cod_unic_e` | `xsd:string` | true | 0..1 |
| `cod_tipo_e` | `xsd:string` | true | 0..1 |
| `des_tipo_e` | `xsd:string` | true | 0..1 |
| `cod_clas_e` | `xsd:string` | true | 0..1 |
| `des_clas_e` | `xsd:string` | true | 0..1 |
| `nom_esta` | `xsd:string` | true | 0..1 |
| `cod_inst_d` | `xsd:string` | true | 0..1 |
| `des_inst_d` | `xsd:string` | true | 0..1 |
| `dir_esta` | `xsd:string` | true | 0..1 |
| `cod_ubig_e` | `xsd:string` | true | 0..1 |
| `nombdep` | `xsd:string` | true | 0..1 |
| `nombprov` | `xsd:string` | true | 0..1 |
| `nombdist` | `xsd:string` | true | 0..1 |
| `num_tele` | `xsd:string` | true | 0..1 |
| `fec_inic_o` | `xsd:date` | true | 0..1 |
| `cod_cate` | `xsd:string` | true | 0..1 |
| `doc_cate` | `xsd:string` | true | 0..1 |
| `des_hora_e` | `xsd:string` | true | 0..1 |
| `cod_cond_e` | `xsd:string` | true | 0..1 |
| `val_lati` | `xsd:decimal` | true | 0..1 |
| `val_long` | `xsd:decimal` | true | 0..1 |
| `cod_auto_s` | `xsd:string` | true | 0..1 |
| `des_auto_s` | `xsd:string` | true | 0..1 |
| `cod_reds` | `xsd:string` | true | 0..1 |
| `des_reds` | `xsd:string` | true | 0..1 |
| `cod_micr_r` | `xsd:string` | true | 0..1 |
| `des_micr_r` | `xsd:string` | true | 0..1 |
| `cod_nruc` | `xsd:decimal` | true | 0..1 |
| `nom_repr_l` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `geoportal:inventario_inundaciones`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `paraje` | `xsd:string` | true | 0..1 |
| `superficie` | `xsd:double` | true | 0..1 |
| `familias_e` | `xsd:double` | true | 0..1 |
| `infraestru` | `xsd:string` | true | 0..1 |
| `nomb_rio_q` | `xsd:string` | true | 0..1 |
| `vivendas_e` | `xsd:string` | true | 0..1 |
| `fecha_act` | `xsd:dateTime` | true | 0..1 |
| `fecha_doc` | `xsd:dateTime` | true | 0..1 |
| `operador` | `xsd:string` | true | 0..1 |
| `tip_peligr` | `xsd:string` | true | 0..1 |
| `medid_prev` | `xsd:string` | true | 0..1 |
| `descrip` | `xsd:string` | true | 0..1 |
| `observ` | `xsd:string` | true | 0..1 |
| `fecha_actu` | `xsd:string` | true | 0..1 |
| `id_entidad` | `xsd:long` | true | 0..1 |
| `id_documento` | `xsd:long` | true | 0..1 |
| `url_documento` | `xsd:string` | true | 0..1 |
| `url_imagen` | `xsd:string` | true | 0..1 |
| `nombre_entidad` | `xsd:string` | true | 0..1 |
| `ubigeo` | `xsd:string` | true | 0..1 |
| `departamento` | `xsd:string` | true | 0..1 |
| `provincia` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `geoportal:inventario_movimientos_masa`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `muestra` | `xsd:string` | true | 0..1 |
| `proyecto` | `xsd:string` | true | 0..1 |
| `proyecto_c` | `xsd:string` | true | 0..1 |
| `norte` | `xsd:decimal` | true | 0..1 |
| `este` | `xsd:decimal` | true | 0..1 |
| `longitud` | `xsd:decimal` | true | 0..1 |
| `latitud` | `xsd:decimal` | true | 0..1 |
| `nombdep` | `xsd:string` | true | 0..1 |
| `nombprov` | `xsd:string` | true | 0..1 |
| `ubigeo` | `xsd:string` | true | 0..1 |
| `paraje` | `xsd:string` | true | 0..1 |
| `tipo_pelig` | `xsd:string` | true | 0..1 |
| `peligro_es` | `xsd:string` | true | 0..1 |
| `pendiente` | `xsd:string` | true | 0..1 |
| `medidas_pr` | `xsd:string` | true | 0..1 |
| `recomendac` | `xsd:string` | true | 0..1 |
| `danhos` | `xsd:string` | true | 0..1 |
| `zona` | `xsd:decimal` | true | 0..1 |
| `observ` | `xsd:string` | true | 0..1 |
| `fecha_act` | `xsd:string` | true | 0..1 |
| `reclasif` | `xsd:string` | true | 0..1 |
| `fuente` | `xsd:string` | true | 0..1 |
| `fuente_log` | `xsd:string` | true | 0..1 |
| `url` | `xsd:string` | true | 0..1 |
| `url_img` | `xsd:string` | true | 0..1 |
| `id_entidad` | `xsd:decimal` | true | 0..1 |
| `id_documen` | `xsd:decimal` | true | 0..1 |
| `id_docum_1` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `geoportal:locales_educativos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `CODLOCAL` | `xsd:string` | true | 0..1 |
| `SERVICIOS` | `xsd:string` | true | 0..1 |
| `DIR_CEN` | `xsd:string` | true | 0..1 |
| `LOCALIDAD` | `xsd:string` | true | 0..1 |
| `CODCP_INEI` | `xsd:string` | true | 0..1 |
| `CODCCPP` | `xsd:string` | true | 0..1 |
| `CEN_POB` | `xsd:string` | true | 0..1 |
| `D_DPTO` | `xsd:string` | true | 0..1 |
| `D_PROV` | `xsd:string` | true | 0..1 |
| `D_DIST` | `xsd:string` | true | 0..1 |
| `DAREACENSO` | `xsd:string` | true | 0..1 |
| `NLAT_IE` | `xsd:decimal` | true | 0..1 |
| `NLONG_IE` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `geoportal:puntos_criticos_inundaciones`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `objectid_12` | `xsd:long` | true | 0..1 |
| `ubi_dpto` | `xsd:string` | true | 0..1 |
| `ubi_prov` | `xsd:string` | true | 0..1 |
| `ubi_dist` | `xsd:string` | true | 0..1 |
| `nom_cuenca` | `xsd:string` | true | 0..1 |
| `nom_dpto` | `xsd:string` | true | 0..1 |
| `nom_prov` | `xsd:string` | true | 0..1 |
| `nom_dist` | `xsd:string` | true | 0..1 |
| `paraje` | `xsd:string` | true | 0..1 |
| `nomb_rio_q` | `xsd:string` | true | 0..1 |
| `fuente` | `xsd:string` | true | 0..1 |
| `fecha_doc` | `xsd:dateTime` | true | 0..1 |
| `familias_e` | `xsd:double` | true | 0..1 |
| `vivendas_e` | `xsd:string` | true | 0..1 |
| `superficie` | `xsd:double` | true | 0..1 |
| `infraestru` | `xsd:string` | true | 0..1 |
| `tip_peligr` | `xsd:string` | true | 0..1 |
| `descrip` | `xsd:string` | true | 0..1 |
| `medid_prev` | `xsd:string` | true | 0..1 |
| `tipo_punto` | `xsd:string` | true | 0..1 |
| `este_i` | `xsd:string` | true | 0..1 |
| `norte_i` | `xsd:string` | true | 0..1 |
| `este_f` | `xsd:double` | true | 0..1 |
| `norte_f` | `xsd:double` | true | 0..1 |
| `fecha_actu` | `xsd:string` | true | 0..1 |
| `url` | `xsd:string` | true | 0..1 |
| `url_img` | `xsd:string` | true | 0..1 |
| `url1` | `xsd:string` | true | 0..1 |
| `url1_img` | `xsd:string` | true | 0..1 |
| `url2` | `xsd:string` | true | 0..1 |
| `url2_img` | `xsd:string` | true | 0..1 |
| `url3` | `xsd:string` | true | 0..1 |
| `url3_img` | `xsd:string` | true | 0..1 |
| `fecha_act` | `xsd:dateTime` | true | 0..1 |
| `ficha_tecnica` | `xsd:string` | true | 0..1 |
| `fuente_log` | `xsd:string` | true | 0..1 |
| `operador` | `xsd:string` | true | 0..1 |
| `observ` | `xsd:string` | true | 0..1 |
| `oculto` | `xsd:string` | true | 0..1 |
| `n_peligro` | `xsd:string` | true | 0..1 |
| `tipo_ficha` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `geoportal:red_vial_departamental_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nombdep` | `xsd:string` | true | 0..1 |
| `nombprov` | `xsd:string` | true | 0..1 |
| `trayectori` | `xsd:string` | true | 0..1 |
| `iddpto` | `xsd:string` | true | 0..1 |
| `jerarq` | `xsd:string` | true | 0..1 |
| `estado` | `xsd:string` | true | 0..1 |
| `codruta` | `xsd:string` | true | 0..1 |
| `superfic` | `xsd:int` | true | 0..1 |
| `longitud` | `xsd:decimal` | true | 0..1 |
| `estado_l` | `xsd:string` | true | 0..1 |
| `superfic_l` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `geoportal:red_vial_nacional_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `inicio` | `xsd:decimal` | true | 0..1 |
| `fin` | `xsd:decimal` | true | 0..1 |
| `trayectori` | `xsd:string` | true | 0..1 |
| `nrocarril` | `xsd:int` | true | 0..1 |
| `ejeclas` | `xsd:string` | true | 0..1 |
| `iddpto` | `xsd:string` | true | 0..1 |
| `nombdep` | `xsd:string` | true | 0..1 |
| `codruta` | `xsd:string` | true | 0..1 |
| `jerarq` | `xsd:string` | true | 0..1 |
| `superfic` | `xsd:int` | true | 0..1 |
| `longitud` | `xsd:decimal` | true | 0..1 |
| `codconces` | `xsd:string` | true | 0..1 |
| `codclog` | `xsd:string` | true | 0..1 |
| `superfic_l` | `xsd:string` | true | 0..1 |
| `codclog_l` | `xsd:string` | true | 0..1 |
| `estado` | `xsd:int` | true | 0..1 |
| `estado_l` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `geoportal:red_vial_vecinal_2022`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nombdep` | `xsd:string` | true | 0..1 |
| `nombprov` | `xsd:string` | true | 0..1 |
| `iddpto` | `xsd:string` | true | 0..1 |
| `jerarq` | `xsd:string` | true | 0..1 |
| `trayectori` | `xsd:string` | true | 0..1 |
| `estado` | `xsd:string` | true | 0..1 |
| `codruta` | `xsd:string` | true | 0..1 |
| `superfic` | `xsd:int` | true | 0..1 |
| `longitud` | `xsd:decimal` | true | 0..1 |
| `estado_l` | `xsd:string` | true | 0..1 |
| `superfic_l` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `geoportal:servicios_educativos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `CODINST` | `xsd:string` | true | 0..1 |
| `CEN_EDU` | `xsd:string` | true | 0..1 |
| `D_DREUGEL` | `xsd:string` | true | 0..1 |
| `D_GESTION` | `xsd:string` | true | 0..1 |
| `D_GES_DEP` | `xsd:string` | true | 0..1 |
| `D_FORMA` | `xsd:string` | true | 0..1 |
| `COD_MOD` | `xsd:string` | true | 0..1 |
| `ANEXO` | `xsd:string` | true | 0..1 |
| `D_NIV_MOD` | `xsd:string` | true | 0..1 |
| `D_COD_CAR` | `xsd:string` | true | 0..1 |
| `D_TIPSSEXO` | `xsd:string` | true | 0..1 |
| `D_TIPOPROG` | `xsd:string` | true | 0..1 |
| `D_COD_TUR` | `xsd:string` | true | 0..1 |
| `NLAT_IE` | `xsd:decimal` | true | 0..1 |
| `NLONG_IE` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `geoportal:tiempo_deplazamiento_capital_cercano`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `dn` | `xsd:string` | true | 0..1 |
| `cat_tiempo` | `xsd:string` | true | 0..1 |
| `fid` | `xsd:decimal` | true | 0..1 |
| `capa` | `xsd:string` | true | 0..1 |
| `direccion` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `geoportal:tramos_criticos_inundaciones`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `objectid` | `xsd:int` | true | 0..1 |
| `cod_tc` | `xsd:string` | true | 0..1 |
| `ubi_dpto` | `xsd:string` | true | 0..1 |
| `ubi_prov` | `xsd:string` | true | 0..1 |
| `ubi_dist` | `xsd:string` | true | 0..1 |
| `aaa` | `xsd:string` | true | 0..1 |
| `ala` | `xsd:string` | true | 0..1 |
| `nom_cuenca` | `xsd:string` | true | 0..1 |
| `nom_rio_q` | `xsd:string` | true | 0..1 |
| `nom_dpto` | `xsd:string` | true | 0..1 |
| `nom_prov` | `xsd:string` | true | 0..1 |
| `nom_dist` | `xsd:string` | true | 0..1 |
| `paraje` | `xsd:string` | true | 0..1 |
| `c_este_i` | `xsd:string` | true | 0..1 |
| `c_este_f` | `xsd:string` | true | 0..1 |
| `c_norte_i` | `xsd:string` | true | 0..1 |
| `c_norte_f` | `xsd:string` | true | 0..1 |
| `zona` | `xsd:string` | true | 0..1 |
| `tip_peligr` | `xsd:string` | true | 0..1 |
| `n_peligro` | `xsd:string` | true | 0..1 |
| `medid_prev` | `xsd:string` | true | 0..1 |
| `medid_tipo` | `xsd:string` | true | 0..1 |
| `presupuest` | `xsd:double` | true | 0..1 |
| `e_iiee` | `xsd:string` | true | 0..1 |
| `e_eess` | `xsd:string` | true | 0..1 |
| `e_via_km` | `xsd:string` | true | 0..1 |
| `e_habitant` | `xsd:string` | true | 0..1 |
| `e_vivienda` | `xsd:string` | true | 0..1 |
| `e_area_cul` | `xsd:double` | true | 0..1 |
| `e_otros_in` | `xsd:string` | true | 0..1 |
| `af_familia` | `xsd:string` | true | 0..1 |
| `af_viviend` | `xsd:string` | true | 0..1 |
| `af_area_cu` | `xsd:double` | true | 0..1 |
| `af_otros_i` | `xsd:string` | true | 0..1 |
| `af_iiee` | `xsd:string` | true | 0..1 |
| `af_eess` | `xsd:string` | true | 0..1 |
| `af_via_km` | `xsd:string` | true | 0..1 |
| `fuente` | `xsd:string` | true | 0..1 |
| `fuente_log` | `xsd:string` | true | 0..1 |
| `periodo` | `xsd:string` | true | 0..1 |
| `fecha_doc` | `xsd:dateTime` | true | 0..1 |
| `url` | `xsd:string` | true | 0..1 |
| `url_img` | `xsd:string` | true | 0..1 |
| `url1` | `xsd:string` | true | 0..1 |
| `url1_img` | `xsd:string` | true | 0..1 |
| `url2` | `xsd:string` | true | 0..1 |
| `url2_img` | `xsd:string` | true | 0..1 |
| `url3` | `xsd:string` | true | 0..1 |
| `url3_img` | `xsd:string` | true | 0..1 |
| `operador` | `xsd:string` | true | 0..1 |
| `fecha_ed` | `xsd:dateTime` | true | 0..1 |
| `descrip` | `xsd:string` | true | 0..1 |
| `observ` | `xsd:string` | true | 0..1 |
| `oculto` | `xsd:string` | true | 0..1 |
| `objectid_1` | `xsd:int` | true | 0..1 |
| `tipo_ficha` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `geoportal:v_capitales`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `ubigeo` | `xsd:string` | true | 0..1 |
| `nombdep` | `xsd:string` | true | 0..1 |
| `nombprov` | `xsd:string` | true | 0..1 |
| `nombdist` | `xsd:string` | true | 0..1 |
| `codccpp` | `xsd:string` | true | 0..1 |
| `cen_pob` | `xsd:string` | true | 0..1 |
| `pob` | `xsd:int` | true | 0..1 |
| `capital` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `geoportal:v_departamentos_2023`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `iddpto` | `xsd:string` | true | 0..1 |
| `nombdep` | `xsd:string` | true | 0..1 |
| `capital` | `xsd:string` | true | 0..1 |
| `tipo_norma` | `xsd:string` | true | 0..1 |
| `numero` | `xsd:string` | true | 0..1 |
| `fecha` | `xsd:date` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `geoportal:v_distritos_2023`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `ubigeo` | `xsd:string` | true | 0..1 |
| `nombdep` | `xsd:string` | true | 0..1 |
| `nombprov` | `xsd:string` | true | 0..1 |
| `nombdist` | `xsd:string` | true | 0..1 |
| `capital` | `xsd:string` | true | 0..1 |
| `region_nat` | `xsd:string` | true | 0..1 |
| `tipo_norma` | `xsd:string` | true | 0..1 |
| `numero` | `xsd:string` | true | 0..1 |
| `fecha_fin` | `xsd:date` | true | 0..1 |
| `comentarios` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `geoportal:v_provincias_2023`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gid` | `xsd:int` | true | 0..1 |
| `iddpto` | `xsd:string` | true | 0..1 |
| `nombdep` | `xsd:string` | true | 0..1 |
| `idprov` | `xsd:string` | true | 0..1 |
| `nombprov` | `xsd:string` | true | 0..1 |
| `capital` | `xsd:string` | true | 0..1 |
| `tipo_norma` | `xsd:string` | true | 0..1 |
| `numero` | `xsd:string` | true | 0..1 |
| `fecha` | `xsd:date` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `geoportal:zonas_criticas_movimientos_masa`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `objectid_12` | `xsd:long` | true | 0..1 |
| `objectid_1` | `xsd:long` | true | 0..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `n` | `xsd:double` | true | 0..1 |
| `nom_dep` | `xsd:string` | true | 0..1 |
| `nom_prov` | `xsd:string` | true | 0..1 |
| `nom_dist` | `xsd:string` | true | 0..1 |
| `nom_lugar` | `xsd:string` | true | 0..1 |
| `x` | `xsd:double` | true | 0..1 |
| `y` | `xsd:double` | true | 0..1 |
| `zona` | `xsd:double` | true | 0..1 |
| `tipo_pel` | `xsd:string` | true | 0..1 |
| `e_expuesto` | `xsd:string` | true | 0..1 |
| `recomend` | `xsd:string` | true | 0..1 |
| `fuente` | `xsd:string` | true | 0..1 |
| `fuente_log` | `xsd:string` | true | 0..1 |
| `observ` | `xsd:string` | true | 0..1 |
| `fecha_doc` | `xsd:dateTime` | true | 0..1 |
| `fecha_ed` | `xsd:dateTime` | true | 0..1 |
| `url` | `xsd:string` | true | 0..1 |
| `url_img` | `xsd:string` | true | 0..1 |
| `operador` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `geoportal:zonas_riesgos_no_mitigable`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `objectid` | `xsd:long` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |
| `ubi_dep` | `xsd:string` | true | 0..1 |
| `ubi_prov` | `xsd:string` | true | 0..1 |
| `ubi_dist` | `xsd:string` | true | 0..1 |
| `nom_dep` | `xsd:string` | true | 0..1 |
| `nom_prov` | `xsd:string` | true | 0..1 |
| `nom_dist` | `xsd:string` | true | 0..1 |
| `fuente` | `xsd:string` | true | 0..1 |
| `fecha_doc` | `xsd:dateTime` | true | 0..1 |
| `nom_predio` | `xsd:string` | true | 0..1 |
| `bdcenepred_informacion_compleme` | `xsd:double` | true | 0..1 |
| `part_regis` | `xsd:string` | true | 0..1 |
| `of_regist` | `xsd:string` | true | 0..1 |
| `fuente_log` | `xsd:string` | true | 0..1 |
| `fecha_act` | `xsd:dateTime` | true | 0..1 |
| `url` | `xsd:string` | true | 0..1 |
| `url_img` | `xsd:string` | true | 0..1 |
| `descrip` | `xsd:string` | true | 0..1 |
| `observ` | `xsd:string` | true | 0..1 |
| `operador` | `xsd:string` | true | 0..1 |
| `url1` | `xsd:string` | true | 0..1 |
| `url_img1` | `xsd:string` | true | 0..1 |
| `condicion` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
