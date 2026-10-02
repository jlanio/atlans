# Sistema de Información Territorial — SIT La Paz (Bolívia) — atributos das camadas

Geoportal: [[Geosserviços/Bolivia SIT La Paz/Sistema de Información Territorial — SIT La Paz (Bolívia)|Sistema de Información Territorial — SIT La Paz (Bolívia)]]

Campos declarados no `DescribeFeatureType`.

### `sit:actividadesEconomicasEBA`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `idae` | `xsd:int` | true | 0..1 |
| `actividaddesarrollada` | `xsd:string` | true | 0..1 |
| `denominacion` | `xsd:string` | true | 0..1 |
| `nit_ci` | `xsd:string` | true | 0..1 |
| `estado` | `xsd:string` | true | 0..1 |
| `direccion` | `xsd:string` | true | 0..1 |
| `latitud` | `xsd:double` | true | 0..1 |
| `longitud` | `xsd:double` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:agenciascooperacion`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Telefono` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:string` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:agenciasviajes`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `Tipo` | `xsd:string` | true | 0..1 |
| `ActividadEconomica` | `xsd:string` | true | 0..1 |
| `MacroDistrito` | `xsd:string` | true | 0..1 |
| `DistritoChar` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:AlumbradoPublico`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Codigo_pi` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Distrito` | `xsd:int` | true | 0..1 |
| `Propietari` | `xsd:string` | true | 0..1 |
| `Tipo_poste` | `xsd:string` | true | 0..1 |
| `Tipo_lampa` | `xsd:string` | true | 0..1 |
| `Potencia` | `xsd:int` | true | 0..1 |
| `Macrodistr` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:ap_municipales2018`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `fid` | `xsd:long` | true | 0..1 |
| `fid_ap_tod` | `xsd:int` | true | 0..1 |
| `superfic2` | `xsd:double` | true | 0..1 |
| `normativa` | `xsd:string` | true | 0..1 |
| `fid_ap_mun` | `xsd:int` | true | 0..1 |
| `fid_anexos` | `xsd:int` | true | 0..1 |
| `nombre` | `xsd:string` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `auto_id` | `xsd:string` | true | 0..1 |
| `rrr` | `xsd:string` | true | 0..1 |
| `normativa1` | `xsd:string` | true | 0..1 |
| `superficie1` | `xsd:double` | true | 0..1 |
| `superficie` | `xsd:double` | true | 0..1 |

### `sit:ap_nacional`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |
| `fid` | `xsd:long` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `codigo` | `xsd:double` | true | 0..1 |
| `nombre` | `xsd:string` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `base_legal` | `xsd:string` | true | 0..1 |
| `hectareas` | `xsd:double` | true | 0..1 |

### `sit:ap_sector_chucura`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |
| `fid` | `xsd:long` | true | 0..1 |

### `sit:areas_protegidas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `ley_nac` | `xsd:string` | true | 0..1 |
| `dec_sup` | `xsd:string` | true | 0..1 |
| `res_pref` | `xsd:string` | true | 0..1 |
| `ley_mun` | `xsd:string` | true | 0..1 |
| `ord_mun` | `xsd:string` | true | 0..1 |
| `res_mun` | `xsd:string` | true | 0..1 |
| `cat` | `xsd:string` | true | 0..1 |
| `área_ha` | `xsd:double` | true | 0..1 |
| `num` | `xsd:string` | true | 0..1 |
| `tipo_area` | `xsd:string` | true | 0..1 |
| `desc_cat` | `xsd:string` | true | 0..1 |

### `sit:arqueo_muyaltasensibilidad`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `fid` | `xsd:long` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |

### `sit:arqueologico_areas_interes_2026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |
| `area` | `xsd:double` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `CONTROL` | `xsd:string` | true | 0..1 |

### `sit:arqueologico_sitios_2026`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `LAYER` | `xsd:string` | true | 0..1 |
| `ESTE` | `xsd:int` | true | 0..1 |
| `NORTE` | `xsd:int` | true | 0..1 |
| `DENSIDAD` | `xsd:string` | true | 0..1 |
| `UBICACION` | `xsd:string` | true | 0..1 |
| `PESO` | `xsd:int` | true | 0..1 |
| `path` | `xsd:string` | true | 0..1 |

### `sit:bancos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nombre` | `xsd:string` | true | 0..1 |
| `tipoPuntoAtencion` | `xsd:string` | true | 0..1 |
| `nombrePuntoAtencion` | `xsd:string` | true | 0..1 |
| `direccion` | `xsd:string` | true | 0..1 |
| `telefono` | `xsd:string` | true | 0..1 |
| `telefonoEmergencia` | `xsd:string` | true | 0..1 |
| `servicio` | `xsd:string` | true | 0..1 |
| `horarios` | `xsd:string` | true | 0..1 |
| `nroIdentif` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `sit:bibliotecas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:bicicleteada`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:CurvePropertyType` | true | 0..1 |
| `nombre` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `distanc_km` | `xsd:long` | true | 0..1 |

### `sit:cajeros_atm`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nombre` | `xsd:string` | true | 0..1 |
| `tipoPuntoAtencion` | `xsd:string` | true | 0..1 |
| `nombrePuntoAtencion` | `xsd:string` | true | 0..1 |
| `direccion` | `xsd:string` | true | 0..1 |
| `telefonoEmergencia` | `xsd:string` | true | 0..1 |
| `servicio` | `xsd:string` | true | 0..1 |
| `horarios` | `xsd:string` | true | 0..1 |
| `nroIdentif` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `sit:camarasseguridad`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Ubicacion` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `Macro` | `xsd:string` | true | 0..1 |
| `idPropietario` | `xsd:int` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:camposdeportivos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Administracion` | `xsd:string` | true | 0..1 |
| `IdTipo` | `xsd:int` | true | 0..1 |
| `Tipo` | `xsd:string` | true | 0..1 |
| `Macrodistrito` | `xsd:string` | true | 0..1 |
| `CodDistrito` | `xsd:string` | true | 0..1 |
| `IdCategoria` | `xsd:int` | true | 0..1 |
| `Categoria` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `Codigo` | `xsd:short` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:cementerios`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `IdTipo` | `xsd:int` | true | 0..1 |
| `Tipo` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:centrosdesarrollosocial`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Descripcion` | `xsd:string` | true | 0..1 |
| `IdTipo` | `xsd:int` | true | 0..1 |
| `Tipo` | `xsd:string` | true | 0..1 |
| `Vocacion` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:centrosinfantiles`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `macro` | `xsd:string` | true | 0..1 |
| `Convenio` | `xsd:string` | true | 0..1 |
| `IdTipo` | `xsd:int` | true | 0..1 |
| `Tipo` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:centrosreligiosos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Tipo` | `xsd:string` | true | 0..1 |
| `Shape` | `gml:PointPropertyType` | true | 0..1 |

### `sit:CentrosVacunacion`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `lugar` | `xsd:string` | true | 0..1 |
| `diasatenci` | `xsd:string` | true | 0..1 |
| `horario` | `xsd:string` | true | 0..1 |
| `findeseman` | `xsd:string` | true | 0..1 |

### `sit:cines`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:clustersfinancieros`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `OficinaCentral` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `IdTipo` | `xsd:int` | true | 0..1 |
| `Tipo` | `xsd:string` | true | 0..1 |
| `Sucursales` | `xsd:string` | true | 0..1 |
| `LaPaz` | `xsd:boolean` | true | 0..1 |
| `Cochabamba` | `xsd:boolean` | true | 0..1 |
| `SantaCruz` | `xsd:boolean` | true | 0..1 |
| `Chuquisaca` | `xsd:boolean` | true | 0..1 |
| `Oruro` | `xsd:boolean` | true | 0..1 |
| `Potosi` | `xsd:boolean` | true | 0..1 |
| `Beni` | `xsd:boolean` | true | 0..1 |
| `Pando` | `xsd:boolean` | true | 0..1 |
| `Tarija` | `xsd:boolean` | true | 0..1 |
| `CuotaMercado` | `xsd:double` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:computopresi2020`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ogr_geometry` | `gml:SurfacePropertyType` | true | 0..1 |
| `c_ut` | `xsd:string` | true | 0..1 |
| `provincia` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `departamen` | `xsd:string` | true | 0..1 |
| `CREEMOS` | `xsd:double` | true | 0..1 |
| `MAS_IPSP` | `xsd:double` | true | 0..1 |
| `FPV` | `xsd:double` | true | 0..1 |
| `PAN_BOL` | `xsd:double` | true | 0..1 |
| `CC` | `xsd:double` | true | 0..1 |
| `VOTO_VALIDO` | `xsd:double` | true | 0..1 |

### `sit:contenedoresbasura`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Codigo` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `macro` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `otb` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:creditobisa_lineas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `desc_cod_da` | `xsd:decimal` | true | 0..1 |
| `nombre_da` | `xsd:string` | false | 1..1 |
| `desc_cod_ue` | `xsd:decimal` | true | 0..1 |
| `nombre_ue` | `xsd:string` | false | 1..1 |
| `cod_poa` | `xsd:decimal` | false | 1..1 |
| `desc_poa` | `xsd:string` | true | 0..1 |
| `cod_programa` | `xsd:string` | true | 0..1 |
| `cod_proyecto` | `xsd:string` | true | 0..1 |
| `cod_actividad` | `xsd:string` | true | 0..1 |
| `pres_vigente` | `xsd:double` | true | 0..1 |
| `cod_zona` | `xsd:string` | true | 0..1 |
| `nombre_zona` | `xsd:string` | false | 1..1 |
| `cod_distrito` | `xsd:string` | true | 0..1 |
| `cod_macro` | `xsd:string` | true | 0..1 |
| `cod_geom` | `xsd:decimal` | false | 1..1 |
| `cod_eje` | `xsd:string` | true | 0..1 |
| `eje` | `xsd:string` | true | 0..1 |
| `cod_sub_eje` | `xsd:string` | true | 0..1 |
| `sub_eje` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `sit:creditobisa_poligonos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `desc_cod_da` | `xsd:decimal` | true | 0..1 |
| `nombre_da` | `xsd:string` | false | 1..1 |
| `desc_cod_ue` | `xsd:decimal` | true | 0..1 |
| `nombre_ue` | `xsd:string` | false | 1..1 |
| `cod_poa` | `xsd:decimal` | false | 1..1 |
| `desc_poa` | `xsd:string` | true | 0..1 |
| `cod_programa` | `xsd:string` | true | 0..1 |
| `cod_proyecto` | `xsd:string` | true | 0..1 |
| `cod_actividad` | `xsd:string` | true | 0..1 |
| `pres_vigente` | `xsd:double` | true | 0..1 |
| `cod_zona` | `xsd:string` | true | 0..1 |
| `nombre_zona` | `xsd:string` | false | 1..1 |
| `cod_distrito` | `xsd:string` | true | 0..1 |
| `cod_macro` | `xsd:string` | true | 0..1 |
| `cod_geom` | `xsd:decimal` | false | 1..1 |
| `cod_eje` | `xsd:string` | true | 0..1 |
| `eje` | `xsd:string` | true | 0..1 |
| `cod_sub_eje` | `xsd:string` | true | 0..1 |
| `sub_eje` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `sit:creditobisa_puntos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `desc_cod_da` | `xsd:decimal` | true | 0..1 |
| `nombre_da` | `xsd:string` | false | 1..1 |
| `desc_cod_ue` | `xsd:decimal` | true | 0..1 |
| `nombre_ue` | `xsd:string` | false | 1..1 |
| `cod_poa` | `xsd:decimal` | false | 1..1 |
| `desc_poa` | `xsd:string` | true | 0..1 |
| `cod_programa` | `xsd:string` | true | 0..1 |
| `cod_proyecto` | `xsd:string` | true | 0..1 |
| `cod_actividad` | `xsd:string` | true | 0..1 |
| `pres_vigente` | `xsd:double` | true | 0..1 |
| `cod_zona` | `xsd:string` | true | 0..1 |
| `nombre_zona` | `xsd:string` | false | 1..1 |
| `cod_distrito` | `xsd:string` | true | 0..1 |
| `cod_macro` | `xsd:string` | true | 0..1 |
| `cod_geom` | `xsd:decimal` | false | 1..1 |
| `cod_eje` | `xsd:string` | true | 0..1 |
| `eje` | `xsd:string` | true | 0..1 |
| `cod_sub_eje` | `xsd:string` | true | 0..1 |
| `sub_eje` | `xsd:string` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |

### `sit:distribucionoxigeno`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `nombre` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `direccion` | `xsd:string` | true | 0..1 |
| `whatsapp` | `xsd:string` | true | 0..1 |
| `telefono` | `xsd:string` | true | 0..1 |

### `sit:distritos2016`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `tipo` | `xsd:string` | true | 0..1 |
| `coddistrito` | `xsd:decimal` | true | 0..1 |
| `macrodistrito` | `xsd:string` | true | 0..1 |
| `subalcaldia` | `xsd:string` | true | 0..1 |
| `codmacro` | `xsd:decimal` | true | 0..1 |
| `wkb_geometry` | `gml:SurfacePropertyType` | true | 0..1 |

### `sit:distritos_nrocasos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |
| `CodDistrito` | `xsd:string` | true | 0..1 |
| `CodMacro` | `xsd:int` | true | 0..1 |
| `Macrodistrito` | `xsd:string` | true | 0..1 |
| `SubAlcaldia` | `xsd:string` | true | 0..1 |
| `POSITIVO` | `xsd:int` | true | 0..1 |
| `RECUPERADO` | `xsd:int` | true | 0..1 |
| `FALLECIDO` | `xsd:int` | true | 0..1 |
| `TOTAL` | `xsd:int` | true | 0..1 |

### `sit:edificios`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `OBJECTID_1` | `xsd:int` | true | 0..1 |
| `OBJECTID` | `xsd:int` | true | 0..1 |
| `LAYER` | `xsd:string` | true | 0..1 |
| `Nombre` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:educacion_smecc`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `Telefono` | `xsd:string` | true | 0..1 |
| `MacroDistrito` | `xsd:string` | true | 0..1 |
| `Codigo` | `xsd:string` | true | 0..1 |
| `Turno` | `xsd:string` | true | 0..1 |
| `Nivel` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:educacionprivada`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `CodMacro` | `xsd:short` | true | 0..1 |
| `CodDistrito` | `xsd:short` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |
| `IdTipo` | `xsd:int` | true | 0..1 |
| `Nombreback` | `xsd:string` | true | 0..1 |

### `sit:educacionpublica`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `codigoSIE` | `xsd:string` | true | 0..1 |
| `ue1` | `xsd:string` | true | 0..1 |
| `ue2` | `xsd:string` | true | 0..1 |
| `ue3` | `xsd:string` | true | 0..1 |
| `ue4` | `xsd:string` | true | 0..1 |
| `ue5` | `xsd:string` | true | 0..1 |
| `Nombre` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `CodMacro` | `xsd:short` | true | 0..1 |
| `CodDistrito` | `xsd:short` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `IdTipo` | `xsd:int` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:educacionsuperior`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Telefono` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:string` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:embajadas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Telefono` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:string` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:entidadesfinancieras`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `IdTipoEntidad` | `xsd:int` | true | 0..1 |
| `Entidad` | `xsd:string` | true | 0..1 |
| `IdTipoOficina` | `xsd:int` | true | 0..1 |
| `tipo_ofi` | `xsd:string` | true | 0..1 |
| `NombreOficina` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `Telefono` | `xsd:string` | true | 0..1 |
| `latitud` | `xsd:decimal` | true | 0..1 |
| `longitud` | `xsd:decimal` | true | 0..1 |
| `enlace` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:equipamientoareas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `ogc_fid` | `xsd:long` | true | 0..1 |
| `nombre` | `xsd:string` | true | 0..1 |
| `linaje` | `xsd:string` | true | 0..1 |
| `nombre_esc` | `xsd:string` | true | 0..1 |
| `codusu` | `xsd:string` | true | 0..1 |
| `tipologia` | `xsd:string` | true | 0..1 |
| `descripcio` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `om` | `xsd:string` | true | 0..1 |
| `tipo_2` | `xsd:string` | true | 0..1 |

### `sit:equipHampaturi`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `nombre` | `xsd:string` | true | 0..1 |
| `tipo_equip` | `xsd:string` | true | 0..1 |
| `nom_comuni` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `observacio` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |

### `sit:equipZongo`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `nombre` | `xsd:string` | true | 0..1 |
| `tipo_equip` | `xsd:string` | true | 0..1 |
| `nom_comuni` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `observacio` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |

### `sit:estacionesservicio`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Shape` | `gml:PointPropertyType` | true | 0..1 |
| `CodMacro` | `xsd:string` | true | 0..1 |
| `CodDistrito` | `xsd:string` | true | 0..1 |
| `Macrodistrito` | `xsd:string` | true | 0..1 |

### `sit:estacionesteleferico`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Estacion` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Shape` | `gml:PointPropertyType` | true | 0..1 |
| `Nombre` | `xsd:string` | true | 0..1 |

### `sit:farmacias`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `Ciudad` | `xsd:string` | true | 0..1 |
| `Telefono` | `xsd:string` | true | 0..1 |
| `Celular` | `xsd:string` | true | 0..1 |
| `PaginaWeb` | `xsd:string` | true | 0..1 |
| `Codigo` | `xsd:short` | true | 0..1 |
| `Email` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:farmacias_smde`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `Tipo` | `xsd:string` | true | 0..1 |
| `ActividadEconomica` | `xsd:string` | true | 0..1 |
| `MacroDistrito` | `xsd:string` | true | 0..1 |
| `DistritoVarchar` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:hidrantes`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Codigo` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:hoteleshostales`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `Tipo` | `xsd:string` | true | 0..1 |
| `ActividadEconomica` | `xsd:string` | true | 0..1 |
| `MacroDistrito` | `xsd:string` | true | 0..1 |
| `DistritoVarchar` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:institucional`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `nombre` | `xsd:string` | true | 0..1 |
| `alias` | `xsd:string` | true | 0..1 |
| `fuente` | `xsd:string` | true | 0..1 |
| `zonaref` | `xsd:string` | true | 0..1 |
| `tipo_desc` | `xsd:string` | true | 0..1 |
| `subtipo_de` | `xsd:string` | true | 0..1 |
| `direccion` | `xsd:string` | true | 0..1 |

### `sit:laboratorioscovid`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `nro` | `xsd:long` | true | 0..1 |
| `nombre` | `xsd:string` | true | 0..1 |
| `direccion` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `watsapp` | `xsd:string` | true | 0..1 |
| `telefono` | `xsd:string` | true | 0..1 |
| `zona` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:long` | true | 0..1 |
| `fechaactua` | `xsd:date` | true | 0..1 |
| `observacio` | `xsd:string` | true | 0..1 |

### `sit:lineasteleferico`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Shape` | `gml:CurvePropertyType` | true | 0..1 |
| `Color` | `xsd:string` | true | 0..1 |

### `sit:lusu_arqueologico`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `sit:lusu_conjuntospat`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `entity` | `xsd:string` | true | 0..1 |
| `conjunto` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `wkb_geometry` | `gml:SurfacePropertyType` | true | 0..1 |

### `sit:lusu_ejeteleferico`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `entity` | `xsd:string` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `elevation` | `xsd:decimal` | true | 0..1 |
| `thickness` | `xsd:decimal` | true | 0..1 |
| `color` | `xsd:decimal` | true | 0..1 |
| `wkb_geometry` | `gml:CurvePropertyType` | true | 0..1 |
| `linea` | `xsd:string` | true | 0..1 |

### `sit:lusu_pem`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `uspa_fina` | `xsd:string` | true | 0..1 |
| `codusu` | `xsd:string` | true | 0..1 |
| `disuspa` | `xsd:decimal` | true | 0..1 |
| `distrito` | `xsd:decimal` | true | 0..1 |
| `cod_sifca` | `xsd:string` | true | 0..1 |
| `sup` | `xsd:decimal` | true | 0..1 |
| `wkb_geometry` | `gml:SurfacePropertyType` | true | 0..1 |
| `idpe` | `xsd:int` | true | 0..1 |

### `sit:lusu_prediospat`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `cod_sifca` | `xsd:string` | true | 0..1 |
| `numerrya` | `xsd:string` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `instlegal` | `xsd:string` | true | 0..1 |
| `anio` | `xsd:string` | true | 0..1 |
| `conjunto` | `xsd:string` | true | 0..1 |
| `inslegal` | `xsd:string` | true | 0..1 |
| `nume` | `xsd:decimal` | true | 0..1 |
| `observacio` | `xsd:string` | true | 0..1 |
| `id_predio` | `xsd:string` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `sit:lusu_restriccionpem`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `idcartilla` | `xsd:decimal` | true | 0..1 |
| `mirador` | `xsd:string` | true | 0..1 |
| `wkb_geometry` | `gml:SurfacePropertyType` | true | 0..1 |

### `sit:lusu_restricciontelef`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nombre` | `xsd:string` | true | 0..1 |
| `wkb_geometry` | `gml:SurfacePropertyType` | true | 0..1 |
| `consolidado` | `xsd:boolean` | true | 0..1 |

### `sit:lusu_restriccrespre`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `distancia` | `xsd:string` | true | 0..1 |
| `altura` | `xsd:decimal` | true | 0..1 |
| `wkb_geometry` | `gml:SurfacePropertyType` | true | 0..1 |
| `idcartilla` | `xsd:int` | true | 0..1 |

### `sit:lusu_teleferico2`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `layer` | `xsd:string` | true | 0..1 |
| `linea` | `xsd:string` | true | 0..1 |
| `wkb_geometry` | `gml:CurvePropertyType` | true | 0..1 |

### `sit:lusu_vigente`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `edificable` | `xsd:string` | true | 0..1 |
| `ususuelo` | `xsd:string` | true | 0..1 |
| `uspa_fina` | `xsd:string` | true | 0..1 |
| `lusu` | `xsd:string` | true | 0..1 |
| `codusu` | `xsd:string` | true | 0..1 |
| `dis2013` | `xsd:decimal` | true | 0..1 |
| `distriuspa` | `xsd:decimal` | true | 0..1 |
| `sup_` | `xsd:decimal` | true | 0..1 |
| `layer__` | `xsd:string` | true | 0..1 |
| `norplavi` | `xsd:string` | true | 0..1 |
| `norlusu` | `xsd:string` | true | 0..1 |
| `norhist` | `xsd:string` | true | 0..1 |
| `ba_carto` | `xsd:string` | true | 0..1 |
| `tipoinst` | `xsd:string` | true | 0..1 |
| `nombre` | `xsd:string` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `idpep` | `xsd:int` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:macrodistritos_nrocasos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |
| `cod_macro` | `xsd:int` | true | 0..1 |
| `macro_ante` | `xsd:string` | true | 0..1 |
| `POSITIVO` | `xsd:int` | true | 0..1 |
| `RECUPERADO` | `xsd:int` | true | 0..1 |
| `FALLECIDO` | `xsd:int` | true | 0..1 |
| `TOTAL` | `xsd:int` | true | 0..1 |

### `sit:manzanas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `distcat` | `xsd:int` | true | 0..1 |
| `manzana` | `xsd:int` | true | 0..1 |
| `ddmm` | `xsd:string` | true | 0..1 |
| `servicios` | `xsd:string` | true | 0..1 |
| `linaje` | `xsd:string` | true | 0..1 |
| `macrodistrito` | `xsd:int` | true | 0..1 |
| `distritomcpal` | `xsd:int` | true | 0..1 |
| `deslinde_ine` | `xsd:int` | true | 0..1 |
| `tipo` | `xsd:int` | true | 0..1 |
| `ajuste` | `xsd:int` | true | 0..1 |
| `shape_length` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `sit:medioscomunicacion`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `Telefono` | `xsd:string` | true | 0..1 |
| `IdTipo` | `xsd:int` | true | 0..1 |
| `Tipo` | `xsd:string` | true | 0..1 |
| `PaginaWeb` | `xsd:string` | true | 0..1 |
| `Macrodistrito` | `xsd:string` | true | 0..1 |
| `idMacrodistrito` | `xsd:int` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:mercados`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `Macrodistrito` | `xsd:string` | true | 0..1 |
| `CodMacro` | `xsd:string` | true | 0..1 |
| `CodDistrito` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:mercadosmoviles`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nombre` | `xsd:string` | true | 0..1 |
| `direccion` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `macro_ante` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `zona` | `xsd:string` | true | 0..1 |
| `fecha_prop` | `xsd:date` | true | 0..1 |
| `fecha_crea` | `xsd:date` | true | 0..1 |
| `afiche` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:mgr_brigadas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `departamen` | `xsd:string` | true | 0..1 |
| `municipio` | `xsd:string` | true | 0..1 |
| `codigo_mz` | `xsd:string` | true | 0..1 |
| `nro_vivien` | `xsd:decimal` | true | 0..1 |
| `cod_dis` | `xsd:string` | true | 0..1 |
| `cod_gral` | `xsd:string` | true | 0..1 |
| `ras_br` | `xsd:string` | true | 0..1 |
| `pob2020` | `xsd:decimal` | true | 0..1 |

### `sit:mgr_distritos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `CodDistrito` | `xsd:string` | true | 0..1 |
| `CodMacro` | `xsd:int` | true | 0..1 |
| `Macrodistrito` | `xsd:string` | true | 0..1 |
| `SubAlcaldia` | `xsd:string` | true | 0..1 |
| `asintomatico` | `xsd:int` | true | 0..1 |
| `leve` | `xsd:int` | true | 0..1 |
| `moderado` | `xsd:int` | true | 0..1 |
| `critico` | `xsd:int` | true | 0..1 |
| `total_clasif` | `xsd:int` | true | 0..1 |
| `hombre` | `xsd:int` | true | 0..1 |
| `mujer` | `xsd:int` | true | 0..1 |
| `total_pers` | `xsd:int` | true | 0..1 |
| `prueba_rap` | `xsd:string` | true | 0..1 |
| `nro_pruebarap_si` | `xsd:int` | true | 0..1 |
| `negativo` | `xsd:int` | true | 0..1 |
| `positivo` | `xsd:int` | true | 0..1 |
| `nro_kit_de_tra` | `xsd:int` | true | 0..1 |
| `hogares_encuestados` | `xsd:int` | true | 0..1 |
| `hombres_ho` | `xsd:decimal` | true | 0..1 |
| `mujeres_ho` | `xsd:decimal` | true | 0..1 |
| `total_hoga` | `xsd:decimal` | true | 0..1 |
| `entrevista_si` | `xsd:int` | true | 0..1 |
| `porc_aceptacion` | `xsd:decimal` | true | 0..1 |
| `continua_enf` | `xsd:decimal` | true | 0..1 |
| `recuperado` | `xsd:decimal` | true | 0..1 |
| `fallecidos` | `xsd:decimal` | true | 0..1 |
| `total_covid` | `xsd:decimal` | true | 0..1 |
| `nro_viviendas` | `xsd:decimal` | true | 0..1 |
| `poblacion_ine` | `xsd:decimal` | true | 0..1 |

### `sit:mgr_macrodistrito`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `cod_macro` | `xsd:int` | true | 0..1 |
| `macro_ante` | `xsd:string` | true | 0..1 |
| `asintomatico` | `xsd:int` | true | 0..1 |
| `leve` | `xsd:int` | true | 0..1 |
| `moderado` | `xsd:int` | true | 0..1 |
| `critico` | `xsd:int` | true | 0..1 |
| `total_clasif` | `xsd:int` | true | 0..1 |
| `hombre` | `xsd:int` | true | 0..1 |
| `mujer` | `xsd:int` | true | 0..1 |
| `total_pers` | `xsd:int` | true | 0..1 |
| `prueba_rap` | `xsd:string` | true | 0..1 |
| `nro_pruebarap_si` | `xsd:int` | true | 0..1 |
| `negativo` | `xsd:int` | true | 0..1 |
| `positivo` | `xsd:int` | true | 0..1 |
| `nro_kit_de_tra` | `xsd:int` | true | 0..1 |
| `hogares_encuestados` | `xsd:int` | true | 0..1 |
| `hombres_ho` | `xsd:decimal` | true | 0..1 |
| `mujeres_ho` | `xsd:decimal` | true | 0..1 |
| `total_hoga` | `xsd:decimal` | true | 0..1 |
| `entrevista_si` | `xsd:int` | true | 0..1 |
| `porc_aceptacion` | `xsd:decimal` | true | 0..1 |
| `continua_enf` | `xsd:decimal` | true | 0..1 |
| `recuperado` | `xsd:decimal` | true | 0..1 |
| `fallecidos` | `xsd:decimal` | true | 0..1 |
| `total_covid` | `xsd:decimal` | true | 0..1 |
| `nro_viviendas` | `xsd:decimal` | true | 0..1 |
| `poblacion_ine` | `xsd:decimal` | true | 0..1 |

### `sit:mgr_puntosencuentro`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `cod` | `xsd:decimal` | true | 0..1 |
| `x` | `xsd:decimal` | true | 0..1 |
| `y` | `xsd:decimal` | true | 0..1 |
| `cod_1` | `xsd:decimal` | true | 0..1 |
| `ubicacion` | `xsd:string` | true | 0..1 |
| `infraestru` | `xsd:string` | true | 0..1 |
| `observacio` | `xsd:string` | true | 0..1 |
| `brigadas_a` | `xsd:string` | true | 0..1 |
| `cantidad_d` | `xsd:decimal` | true | 0..1 |
| `personas_b` | `xsd:decimal` | true | 0..1 |
| `total_pers` | `xsd:decimal` | true | 0..1 |
| `encargado` | `xsd:string` | true | 0..1 |
| `ci` | `xsd:string` | true | 0..1 |
| `celular` | `xsd:decimal` | true | 0..1 |
| `macro_ante` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:decimal` | true | 0..1 |

### `sit:mgr_resumen_mlp`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `municipio` | `xsd:string` | false | 1..1 |
| `fecha_actual` | `xsd:dateTime` | false | 1..1 |
| `asintomatico` | `xsd:int` | true | 0..1 |
| `leve` | `xsd:int` | true | 0..1 |
| `moderado` | `xsd:int` | true | 0..1 |
| `critico` | `xsd:int` | true | 0..1 |
| `total_clasif` | `xsd:int` | true | 0..1 |
| `hombre` | `xsd:int` | true | 0..1 |
| `mujer` | `xsd:int` | true | 0..1 |
| `total_pers` | `xsd:int` | true | 0..1 |
| `nro_pruebarap_si` | `xsd:int` | true | 0..1 |
| `negativo` | `xsd:int` | true | 0..1 |
| `positivo` | `xsd:int` | true | 0..1 |
| `nro_kit_de_tra` | `xsd:int` | true | 0..1 |
| `hogares_encuestados` | `xsd:int` | true | 0..1 |
| `hombres_ho` | `xsd:decimal` | true | 0..1 |
| `mujeres_ho` | `xsd:decimal` | true | 0..1 |
| `total_hoga` | `xsd:decimal` | true | 0..1 |
| `entrevista_si` | `xsd:int` | true | 0..1 |
| `porc_aceptacion` | `xsd:decimal` | true | 0..1 |
| `continua_enf` | `xsd:decimal` | true | 0..1 |
| `recuperado` | `xsd:decimal` | true | 0..1 |
| `fallecidos` | `xsd:decimal` | true | 0..1 |
| `total_covid` | `xsd:decimal` | true | 0..1 |
| `nro_viviendas` | `xsd:decimal` | true | 0..1 |
| `poblacion_ine` | `xsd:decimal` | true | 0..1 |

### `sit:mgr_resumen_mlp_fechas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `municipio` | `xsd:string` | false | 1..1 |
| `fecha_actual` | `xsd:dateTime` | false | 1..1 |
| `asintomatico` | `xsd:int` | true | 0..1 |
| `leve` | `xsd:int` | true | 0..1 |
| `moderado` | `xsd:int` | true | 0..1 |
| `critico` | `xsd:int` | true | 0..1 |
| `total_clasif` | `xsd:int` | true | 0..1 |
| `hombre` | `xsd:int` | true | 0..1 |
| `mujer` | `xsd:int` | true | 0..1 |
| `total_pers` | `xsd:int` | true | 0..1 |
| `nro_pruebarap_si` | `xsd:int` | true | 0..1 |
| `negativo` | `xsd:int` | true | 0..1 |
| `positivo` | `xsd:int` | true | 0..1 |
| `nro_kit_de_tra` | `xsd:int` | true | 0..1 |
| `hogares_encuestados` | `xsd:int` | true | 0..1 |
| `hombres_ho` | `xsd:decimal` | true | 0..1 |
| `mujeres_ho` | `xsd:decimal` | true | 0..1 |
| `total_hoga` | `xsd:decimal` | true | 0..1 |
| `entrevista_si` | `xsd:int` | true | 0..1 |
| `porc_aceptacion` | `xsd:decimal` | true | 0..1 |
| `continua_enf` | `xsd:decimal` | true | 0..1 |
| `recuperado` | `xsd:decimal` | true | 0..1 |
| `fallecidos` | `xsd:decimal` | true | 0..1 |
| `total_covid` | `xsd:decimal` | true | 0..1 |
| `nro_viviendas` | `xsd:decimal` | true | 0..1 |
| `poblacion_ine` | `xsd:decimal` | true | 0..1 |
| `fecha_creacion` | `xsd:string` | true | 0..1 |

### `sit:mgr_zonas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `macrodistrito` | `xsd:string` | true | 0..1 |
| `zona` | `xsd:string` | true | 0..1 |
| `codigozona` | `xsd:int` | true | 0..1 |
| `macro` | `xsd:int` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `asintomatico` | `xsd:int` | true | 0..1 |
| `leve` | `xsd:int` | true | 0..1 |
| `moderado` | `xsd:int` | true | 0..1 |
| `critico` | `xsd:int` | true | 0..1 |
| `total_clasif` | `xsd:int` | true | 0..1 |
| `hombre` | `xsd:int` | true | 0..1 |
| `mujer` | `xsd:int` | true | 0..1 |
| `total_pers` | `xsd:int` | true | 0..1 |
| `prueba_rap` | `xsd:string` | true | 0..1 |
| `nro_pruebarap_si` | `xsd:int` | true | 0..1 |
| `negativo` | `xsd:int` | true | 0..1 |
| `positivo` | `xsd:int` | true | 0..1 |
| `nro_kit_de_tra` | `xsd:int` | true | 0..1 |
| `hogares_encuestados` | `xsd:int` | true | 0..1 |
| `hombres_ho` | `xsd:decimal` | true | 0..1 |
| `mujeres_ho` | `xsd:decimal` | true | 0..1 |
| `total_hoga` | `xsd:decimal` | true | 0..1 |
| `entrevista_si` | `xsd:int` | true | 0..1 |
| `porc_aceptacion` | `xsd:decimal` | true | 0..1 |
| `continua_enf` | `xsd:decimal` | true | 0..1 |
| `recuperado` | `xsd:decimal` | true | 0..1 |
| `fallecidos` | `xsd:decimal` | true | 0..1 |
| `total_covid` | `xsd:decimal` | true | 0..1 |
| `nro_viviendas` | `xsd:decimal` | true | 0..1 |
| `poblacion_ine` | `xsd:decimal` | true | 0..1 |

### `sit:miradores`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `Tipo` | `xsd:string` | true | 0..1 |
| `CodMacro` | `xsd:short` | true | 0..1 |
| `CodDistrito` | `xsd:short` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:modulospoliciales`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `Tipo` | `xsd:string` | true | 0..1 |
| `IdTipo` | `xsd:int` | true | 0..1 |
| `Macrodistrito` | `xsd:string` | true | 0..1 |
| `CodDistrito` | `xsd:short` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:museos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:numeropuertas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `cod_sifca` | `xsd:string` | true | 0..1 |
| `num_puerta` | `xsd:string` | true | 0..1 |
| `fuente` | `xsd:string` | true | 0..1 |
| `n_inmueble` | `xsd:int` | true | 0..1 |
| `tipo_via` | `xsd:string` | true | 0..1 |
| `nombre_via` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `otb` | `xsd:string` | true | 0..1 |
| `zona` | `xsd:string` | true | 0..1 |

### `sit:nv_poligonos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |
| `AREA` | `xsd:double` | true | 0..1 |
| `DWGNAME` | `xsd:string` | true | 0..1 |
| `LAYER` | `xsd:string` | true | 0..1 |
| `NOMBRE` | `xsd:string` | true | 0..1 |
| `IDENTIFICACION` | `xsd:string` | true | 0..1 |
| `Manzana` | `xsd:string` | true | 0..1 |
| `Lote` | `xsd:string` | true | 0..1 |
| `ACTO_ADMINISTRATIVO` | `xsd:string` | true | 0..1 |
| `FECHA_ACTUALIZACION` | `xsd:date` | true | 0..1 |
| `SUP_LOTE` | `xsd:float` | true | 0..1 |
| `SUP` | `xsd:float` | true | 0..1 |

### `sit:otbdpe`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nom_otb` | `xsd:string` | true | 0..1 |
| `sub_alcald` | `xsd:string` | true | 0..1 |
| `estado` | `xsd:string` | true | 0..1 |
| `numero` | `xsd:double` | true | 0..1 |
| `distrito` | `xsd:double` | true | 0..1 |
| `codigo` | `xsd:string` | true | 0..1 |
| `area_m2` | `xsd:double` | true | 0..1 |
| `area_has` | `xsd:double` | true | 0..1 |
| `area_km2` | `xsd:double` | true | 0..1 |
| `shape_length` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |

### `sit:otbrural`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `objectid` | `xsd:decimal` | true | 0..1 |
| `nombre` | `xsd:string` | true | 0..1 |
| `sa` | `xsd:string` | true | 0..1 |
| `estado` | `xsd:string` | true | 0..1 |
| `autoidenti` | `xsd:string` | true | 0..1 |
| `central` | `xsd:string` | true | 0..1 |
| `sub_centra` | `xsd:string` | true | 0..1 |
| `area_m2` | `xsd:decimal` | true | 0..1 |
| `area_has` | `xsd:decimal` | true | 0..1 |
| `area_km2` | `xsd:decimal` | true | 0..1 |
| `recorr` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:decimal` | true | 0..1 |
| `ate` | `xsd:string` | true | 0..1 |
| `wkb_geometry` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `sit:otbs_poa`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nombre` | `xsd:string` | true | 0..1 |
| `estado` | `xsd:string` | true | 0..1 |
| `ob_poa2020` | `xsd:string` | true | 0..1 |
| `cod_macro` | `xsd:string` | true | 0..1 |
| `cod_distrito` | `xsd:string` | true | 0..1 |
| `cod_zona` | `xsd:string` | true | 0..1 |
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `sit:oxigenoterapia`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `nombre` | `xsd:string` | true | 0..1 |
| `dias_atenc` | `xsd:string` | true | 0..1 |
| `horario` | `xsd:string` | true | 0..1 |
| `telefono` | `xsd:string` | true | 0..1 |

### `sit:paradaspumakatari`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Direccion` | `xsd:string` | true | 0..1 |
| `Ruta` | `xsd:string` | true | 0..1 |
| `Shape` | `gml:PointPropertyType` | true | 0..1 |

### `sit:paradaspumakatari2021`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Id` | `xsd:int` | true | 0..1 |
| `Ruta` | `xsd:string` | true | 0..1 |
| `Shape` | `gml:PointPropertyType` | true | 0..1 |
| `Name` | `xsd:string` | true | 0..1 |
| `sentido` | `xsd:string` | true | 0..1 |
| `numero_rut` | `xsd:int` | true | 0..1 |

### `sit:patrimonio_estilocartilla`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `estilo` | `xsd:string` | true | 0..1 |
| `codigoscat` | `xsd:string` | true | 0..1 |
| `cartilla` | `xsd:string` | true | 0..1 |

### `sit:permisosconstruccion`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `NumeroTramite` | `xsd:decimal` | true | 0..1 |
| `idPCTramite` | `xsd:decimal` | false | 1..1 |
| `descripcion` | `xsd:string` | true | 0..1 |
| `idTipoTramite` | `xsd:decimal` | true | 0..1 |
| `fechaRegistro` | `xsd:dateTime` | true | 0..1 |
| `Solicitante` | `xsd:string` | true | 0..1 |
| `arquitectoNombre` | `xsd:string` | true | 0..1 |
| `arquitectoRegistroNacionalCAB` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `idProyectoDesarrollo` | `xsd:decimal` | true | 0..1 |
| `idTipoObra` | `xsd:decimal` | true | 0..1 |
| `TipoProyecto` | `xsd:string` | true | 0..1 |
| `TipoObra` | `xsd:string` | true | 0..1 |
| `Resultado` | `xsd:string` | true | 0..1 |
| `EstadoTramite` | `xsd:string` | true | 0..1 |
| `idInsDocumento` | `xsd:decimal` | true | 0..1 |
| `nombreArchivo` | `xsd:string` | true | 0..1 |
| `FechaRegistroArch` | `xsd:dateTime` | true | 0..1 |
| `codigoCatastral` | `xsd:string` | true | 0..1 |
| `fechaAprobacion` | `xsd:dateTime` | true | 0..1 |
| `macroDistrito` | `xsd:string` | true | 0..1 |
| `distritoMunicipal` | `xsd:decimal` | true | 0..1 |
| `cantidadPisos` | `xsd:decimal` | true | 0..1 |
| `superficieLegal` | `xsd:double` | true | 0..1 |
| `nombreEdificio` | `xsd:string` | true | 0..1 |
| `SuperficieConstruida` | `xsd:decimal` | true | 0..1 |
| `fechaEntrega` | `xsd:dateTime` | true | 0..1 |
| `superficieUtil` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `sit:pl_lineas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `DWGNAME` | `xsd:string` | true | 0..1 |
| `LAYER` | `xsd:string` | true | 0..1 |
| `ACTO_ADMINISTRATIVO` | `xsd:string` | true | 0..1 |
| `FECHA_ACTUALIZACION` | `xsd:date` | true | 0..1 |

### `sit:pl_poligonos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |
| `AREA` | `xsd:decimal` | true | 0..1 |
| `DWGNAME` | `xsd:string` | true | 0..1 |
| `LAYER` | `xsd:string` | true | 0..1 |
| `NOMBRE` | `xsd:string` | true | 0..1 |
| `SUP` | `xsd:double` | true | 0..1 |
| `IDENTIFICACION` | `xsd:string` | true | 0..1 |
| `SUP_LOTE` | `xsd:double` | true | 0..1 |
| `Manzana` | `xsd:string` | true | 0..1 |
| `Lote` | `xsd:string` | true | 0..1 |
| `ACTO ADMINISTRATIVO` | `xsd:string` | true | 0..1 |
| `FECHA_ACTUALIZACION` | `xsd:date` | true | 0..1 |
| `OBS_LEGAL` | `xsd:string` | true | 0..1 |
| `OBS_TECNICA` | `xsd:string` | true | 0..1 |

### `sit:pl_texto`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `LAYER` | `xsd:string` | true | 0..1 |
| `DWGNAME` | `xsd:string` | true | 0..1 |
| `TEXT_SIZE` | `xsd:decimal` | true | 0..1 |
| `TEXT_ANGLE` | `xsd:decimal` | true | 0..1 |
| `ROTATION` | `xsd:decimal` | true | 0..1 |
| `TEXTSTRING` | `xsd:string` | true | 0..1 |
| `ACTO ADMINISTRATIVO` | `xsd:string` | true | 0..1 |
| `FECHA_ACTUALIZACION` | `xsd:date` | true | 0..1 |

### `sit:plataformassitram`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Telefono` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `IdTipoPlataforma` | `xsd:int` | true | 0..1 |
| `Servicio` | `xsd:string` | true | 0..1 |
| `HorarioAtencion` | `xsd:string` | true | 0..1 |
| `Dependencias` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:plazasparques`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `IdTipo` | `xsd:int` | true | 0..1 |
| `Tipo` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:plazasparques_sit`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `OBJECTID_1` | `xsd:int` | true | 0..1 |
| `Nombre` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `OBJECTID` | `xsd:int` | true | 0..1 |
| `Layer` | `xsd:string` | true | 0..1 |
| `IdTipo` | `xsd:int` | true | 0..1 |
| `Jerarquia` | `xsd:short` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:publicidadurbana`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `idContribuyente` | `xsd:int` | true | 0..1 |
| `clase` | `xsd:string` | true | 0..1 |
| `PMC` | `xsd:string` | true | 0..1 |
| `Nit` | `xsd:int` | true | 0..1 |
| `NombreContribuyente` | `xsd:string` | true | 0..1 |
| `CI` | `xsd:int` | true | 0..1 |
| `exp` | `xsd:string` | true | 0..1 |
| `IdPub` | `xsd:int` | true | 0..1 |
| `Ubicacion` | `xsd:string` | false | 1..1 |
| `descripcionPublicidad` | `xsd:string` | true | 0..1 |
| `sup` | `xsd:double` | true | 0..1 |
| `caras` | `xsd:int` | true | 0..1 |
| `caras1` | `xsd:int` | true | 0..1 |
| `zona` | `xsd:string` | true | 0..1 |
| `inicio` | `xsd:string` | true | 0..1 |
| `fin` | `xsd:string` | true | 0..1 |
| `Observacion` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:puentes`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `nombre` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `subalcaldi` | `xsd:string` | true | 0..1 |
| `zona` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:decimal` | true | 0..1 |
| `pnt_fec_se` | `xsd:string` | true | 0..1 |
| `estructura` | `xsd:string` | true | 0..1 |
| `pnt_cruza` | `xsd:string` | true | 0..1 |
| `categoria` | `xsd:decimal` | true | 0..1 |
| `macrodistr` | `xsd:string` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:puntosdiapeaton`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `nombr_ruta` | `xsd:string` | true | 0..1 |
| `nomb_punto` | `xsd:string` | true | 0..1 |
| `descripcio` | `xsd:string` | true | 0..1 |

### `sit:puntosverdes`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `Este` | `xsd:string` | true | 0..1 |
| `Sur` | `xsd:string` | true | 0..1 |
| `Tipo` | `xsd:string` | true | 0..1 |
| `TipoActividad` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:redistritacion`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Tipo` | `xsd:string` | true | 0..1 |
| `CodDistrito` | `xsd:string` | true | 0..1 |
| `Macrodistrito` | `xsd:string` | true | 0..1 |
| `SubAlcaldia` | `xsd:string` | true | 0..1 |
| `CodigoM` | `xsd:string` | true | 0..1 |
| `CodMacro` | `xsd:int` | true | 0..1 |
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |

### `sit:reporteCasosRed114`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `nro_caso` | `xsd:int` | true | 0..1 |
| `institucion` | `xsd:string` | true | 0..1 |
| `tipo_caso` | `xsd:string` | true | 0..1 |
| `cat_riesgo` | `xsd:string` | true | 0..1 |
| `fecha_registro` | `xsd:dateTime` | true | 0..1 |
| `fecha_registro_1` | `xsd:dateTime` | true | 0..1 |
| `derivacion` | `xsd:string` | true | 0..1 |
| `nom_vecino` | `xsd:string` | true | 0..1 |
| `telefono_1` | `xsd:string` | true | 0..1 |
| `telefono_2` | `xsd:string` | true | 0..1 |
| `estado` | `xsd:string` | true | 0..1 |
| `macrodistrito` | `xsd:int` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `zona` | `xsd:string` | true | 0..1 |
| `direccion` | `xsd:string` | true | 0..1 |
| `referencia_1` | `xsd:string` | true | 0..1 |
| `referencia_2` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:restaurantes`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `razonSocial` | `xsd:string` | true | 0..1 |
| `actividad` | `xsd:string` | true | 0..1 |
| `descGrupo` | `xsd:string` | true | 0..1 |
| `direccion` | `xsd:string` | true | 0..1 |
| `calleav` | `xsd:string` | true | 0..1 |
| `entreCalles` | `xsd:string` | true | 0..1 |
| `edificio` | `xsd:string` | true | 0..1 |
| `telefono` | `xsd:string` | true | 0..1 |
| `categoria` | `xsd:string` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `sit:riesgo_riesgos2025opt`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `id` | `xsd:long` | true | 0..1 |
| `gridcode` | `xsd:decimal` | true | 0..1 |
| `grado` | `xsd:string` | true | 0..1 |

### `sit:riosrural`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `sde_sde_rios_r_entity` | `xsd:string` | true | 0..1 |
| `level_` | `xsd:double` | true | 0..1 |
| `color` | `xsd:int` | true | 0..1 |
| `nobre_de_r` | `xsd:string` | true | 0..1 |
| `clasificac` | `xsd:string` | true | 0..1 |
| `distritos` | `xsd:string` | true | 0..1 |
| `longitud_d` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_length` | `xsd:double` | true | 0..1 |

### `sit:riosurbano`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `objectid` | `xsd:long` | true | 0..1 |
| `nombre` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |

### `sit:rutas_recoleccion_basura_atencion`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `OBJECTID` | `xsd:long` | true | 0..1 |
| `end_` | `xsd:date` | true | 0..1 |
| `Tipo_reg` | `xsd:string` | true | 0..1 |
| `latitude` | `xsd:double` | true | 0..1 |
| `longitude` | `xsd:double` | true | 0..1 |
| `altitude` | `xsd:double` | true | 0..1 |
| `precision_` | `xsd:double` | true | 0..1 |
| `Foto_ini` | `xsd:string` | true | 0..1 |
| `ini_URL` | `xsd:string` | true | 0..1 |
| `Foto_des` | `xsd:string` | true | 0..1 |
| `des_URL` | `xsd:string` | true | 0..1 |
| `Obser` | `xsd:string` | true | 0..1 |
| `fuente` | `xsd:string` | true | 0..1 |
| `estado` | `xsd:string` | true | 0..1 |
| `F_id` | `xsd:double` | true | 0..1 |

### `sit:rutas_recoleccion_basura_lpl`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `descripcio` | `xsd:string` | true | 0..1 |
| `turno` | `xsd:string` | true | 0..1 |
| `empresa` | `xsd:string` | true | 0..1 |

### `sit:rutas_recoleccion_basura_selec`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `descripcio` | `xsd:string` | true | 0..1 |
| `turno` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `dis_km` | `xsd:double` | true | 0..1 |
| `empresa` | `xsd:string` | true | 0..1 |
| `codi` | `xsd:string` | true | 0..1 |
| `ruta` | `xsd:string` | true | 0..1 |
| `procedenci` | `xsd:double` | true | 0..1 |
| `enero` | `xsd:double` | true | 0..1 |
| `febrero` | `xsd:double` | true | 0..1 |
| `marzo` | `xsd:double` | true | 0..1 |
| `abril` | `xsd:double` | true | 0..1 |
| `mayo` | `xsd:double` | true | 0..1 |
| `junio` | `xsd:double` | true | 0..1 |
| `julio` | `xsd:double` | true | 0..1 |
| `agosto` | `xsd:double` | true | 0..1 |
| `septiembre` | `xsd:double` | true | 0..1 |
| `octubre` | `xsd:double` | true | 0..1 |
| `noviembre` | `xsd:double` | true | 0..1 |
| `diciembre` | `xsd:double` | true | 0..1 |
| `prom_kg_` | `xsd:double` | true | 0..1 |
| `total__kg_` | `xsd:double` | true | 0..1 |
| `total__tn_` | `xsd:double` | true | 0..1 |

### `sit:rutasfumigacion`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:CurvePropertyType` | true | 0..1 |
| `total_long` | `xsd:double` | true | 0..1 |

### `sit:rutaspeaton`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:CurvePropertyType` | true | 0..1 |
| `nombr_ruta` | `xsd:string` | true | 0..1 |
| `descripcio` | `xsd:string` | true | 0..1 |
| `distanc_km` | `xsd:double` | true | 0..1 |

### `sit:rutaspumakatari`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Id` | `xsd:int` | true | 0..1 |
| `RUTA` | `xsd:string` | true | 0..1 |
| `Shape` | `gml:CurvePropertyType` | true | 0..1 |

### `sit:rutaspumakatari2021`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Id` | `xsd:int` | true | 0..1 |
| `Name` | `xsd:string` | true | 0..1 |
| `Shape` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `sentido` | `xsd:string` | true | 0..1 |
| `numero_rut` | `xsd:int` | true | 0..1 |
| `Ruta` | `xsd:string` | true | 0..1 |
| `Año_Inagur` | `xsd:long` | true | 0..1 |

### `sit:salud`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `IdFuente` | `xsd:int` | true | 0..1 |
| `Fuente` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `IdTipo` | `xsd:int` | true | 0..1 |
| `Tipo` | `xsd:string` | true | 0..1 |
| `IdSector` | `xsd:int` | true | 0..1 |
| `Sector` | `xsd:string` | true | 0..1 |
| `IdNivel` | `xsd:int` | true | 0..1 |
| `Nivel` | `xsd:string` | true | 0..1 |
| `Red` | `xsd:string` | true | 0..1 |
| `TipoAtencion` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:saludsiis`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Codigo` | `xsd:string` | true | 0..1 |
| `Nombre` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `IdTipo` | `xsd:int` | true | 0..1 |
| `IdSector` | `xsd:int` | true | 0..1 |
| `IdNivel` | `xsd:int` | true | 0..1 |
| `Red` | `xsd:string` | true | 0..1 |
| `TipoAtencion` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:sedes_establsalud`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `codsnis` | `xsd:int` | true | 0..1 |
| `nombr_snis` | `xsd:string` | true | 0..1 |
| `niveles` | `xsd:string` | true | 0..1 |
| `ambitogeo` | `xsd:string` | true | 0..1 |
| `nivel` | `xsd:int` | true | 0..1 |

### `sit:sedes_redsalud`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `codredsal` | `xsd:string` | true | 0..1 |
| `nombrered` | `xsd:string` | true | 0..1 |
| `coddepto` | `xsd:string` | true | 0..1 |
| `nomdepto` | `xsd:string` | true | 0..1 |

### `sit:sedes_redsalud2016`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `descriptio` | `xsd:string` | true | 0..1 |
| `codredsal` | `xsd:string` | true | 0..1 |
| `nombrered` | `xsd:string` | true | 0..1 |
| `coddepto` | `xsd:string` | true | 0..1 |
| `nomdepto` | `xsd:string` | true | 0..1 |

### `sit:servicioshigienicos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:sim_proyectos2023_puntos2`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `cod_geom` | `xsd:long` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `desc_cod_da` | `xsd:long` | true | 0..1 |
| `nombre_da` | `xsd:string` | true | 0..1 |
| `desc_cod_ue` | `xsd:long` | true | 0..1 |
| `nombre_ue` | `xsd:string` | true | 0..1 |
| `cod_poa` | `xsd:long` | true | 0..1 |
| `desc_poa` | `xsd:string` | true | 0..1 |
| `cod_programa` | `xsd:string` | true | 0..1 |
| `cod_proyecto` | `xsd:string` | true | 0..1 |
| `cod_actividad` | `xsd:string` | true | 0..1 |
| `pres_vigente` | `xsd:double` | true | 0..1 |
| `cod_zona` | `xsd:string` | true | 0..1 |
| `nombre_zona` | `xsd:string` | true | 0..1 |
| `cod_distrito` | `xsd:string` | true | 0..1 |
| `cod_macro` | `xsd:string` | true | 0..1 |
| `cod_eje` | `xsd:string` | true | 0..1 |
| `eje` | `xsd:string` | true | 0..1 |
| `cod_sub_eje` | `xsd:string` | true | 0..1 |
| `sub_eje` | `xsd:string` | true | 0..1 |
| `prioridad_fac` | `xsd:string` | true | 0..1 |
| `prioridadoperacion` | `xsd:string` | true | 0..1 |

### `sit:sim_proyectos_p`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `cod_geom` | `xsd:long` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `desc_cod_da` | `xsd:long` | true | 0..1 |
| `nombre_da` | `xsd:string` | true | 0..1 |
| `desc_cod_ue` | `xsd:long` | true | 0..1 |
| `nombre_ue` | `xsd:string` | true | 0..1 |
| `cod_poa` | `xsd:long` | true | 0..1 |
| `desc_poa` | `xsd:string` | true | 0..1 |
| `cod_programa` | `xsd:string` | true | 0..1 |
| `cod_proyecto` | `xsd:string` | true | 0..1 |
| `cod_actividad` | `xsd:string` | true | 0..1 |
| `nombre_zona` | `xsd:string` | true | 0..1 |
| `cod_distrito` | `xsd:string` | true | 0..1 |
| `cod_macro` | `xsd:string` | true | 0..1 |
| `cod_eje` | `xsd:string` | true | 0..1 |
| `eje` | `xsd:string` | true | 0..1 |
| `cod_sub_eje` | `xsd:string` | true | 0..1 |
| `sub_eje` | `xsd:string` | true | 0..1 |
| `prioridad_fac` | `xsd:string` | true | 0..1 |
| `prioridadoperacion` | `xsd:string` | true | 0..1 |
| `gestion` | `xsd:double` | true | 0..1 |

### `sit:sim_proyectos_puntos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | true | 0..1 |
| `cod_geom` | `xsd:long` | true | 0..1 |
| `geom` | `gml:GeometryPropertyType` | true | 0..1 |
| `desc_cod_da` | `xsd:long` | true | 0..1 |
| `nombre_da` | `xsd:string` | true | 0..1 |
| `desc_cod_ue` | `xsd:long` | true | 0..1 |
| `nombre_ue` | `xsd:string` | true | 0..1 |
| `cod_poa` | `xsd:long` | true | 0..1 |
| `desc_poa` | `xsd:string` | true | 0..1 |
| `cod_programa` | `xsd:string` | true | 0..1 |
| `cod_proyecto` | `xsd:string` | true | 0..1 |
| `cod_actividad` | `xsd:string` | true | 0..1 |
| `pres_vigente` | `xsd:double` | true | 0..1 |
| `cod_zona` | `xsd:string` | true | 0..1 |
| `nombre_zona` | `xsd:string` | true | 0..1 |
| `cod_distrito` | `xsd:string` | true | 0..1 |
| `cod_macro` | `xsd:string` | true | 0..1 |
| `cod_eje` | `xsd:string` | true | 0..1 |
| `eje` | `xsd:string` | true | 0..1 |
| `cod_sub_eje` | `xsd:string` | true | 0..1 |
| `sub_eje` | `xsd:string` | true | 0..1 |
| `prioridad_fac` | `xsd:string` | true | 0..1 |
| `prioridadoperacion` | `xsd:string` | true | 0..1 |
| `gestion` | `xsd:double` | true | 0..1 |

### `sit:sitiosturisticos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `IdCategoria` | `xsd:short` | true | 0..1 |
| `Categoria` | `xsd:string` | true | 0..1 |
| `Nombre` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Cod_UGT` | `xsd:string` | true | 0..1 |
| `Telefono` | `xsd:string` | true | 0..1 |
| `Contacto` | `xsd:string` | true | 0..1 |
| `Correo` | `xsd:string` | true | 0..1 |
| `Legalidad` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:smc_arqueologico`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `area` | `xsd:decimal` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |

### `sit:supermercados`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `Nombre` | `xsd:string` | true | 0..1 |
| `Direccion` | `xsd:string` | true | 0..1 |
| `Zona` | `xsd:string` | true | 0..1 |
| `Tipo` | `xsd:string` | true | 0..1 |
| `ActividadEconomica` | `xsd:string` | true | 0..1 |
| `MacroDistrito` | `xsd:string` | true | 0..1 |
| `DistritoVarchar` | `xsd:string` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `owner` | `xsd:string` | true | 0..1 |
| `usuario` | `xsd:string` | true | 0..1 |
| `fechaActual` | `xsd:dateTime` | true | 0..1 |
| `observaciones` | `xsd:string` | true | 0..1 |

### `sit:toponimia`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `wkb_geometry` | `gml:PointPropertyType` | true | 0..1 |
| `layer` | `xsd:string` | true | 0..1 |
| `rango` | `xsd:int` | true | 0..1 |
| `nombre` | `xsd:string` | true | 0..1 |
| `gdbsnomb` | `xsd:string` | true | 0..1 |

### `sit:toponimia2`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `tipo` | `xsd:int` | true | 0..1 |
| `sub_tipo` | `xsd:int` | true | 0..1 |
| `nombre` | `xsd:string` | true | 0..1 |
| `alias` | `xsd:string` | true | 0..1 |
| `fuente` | `xsd:string` | true | 0..1 |
| `categoria` | `xsd:int` | true | 0..1 |
| `zonaref` | `xsd:string` | true | 0..1 |
| `tipo_desc` | `xsd:string` | true | 0..1 |
| `subtipo_desc` | `xsd:string` | true | 0..1 |

### `sit:tramitesterritoriales`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `idPCTramite` | `xsd:decimal` | false | 1..1 |
| `descripcion` | `xsd:string` | true | 0..1 |
| `idTipoTramite` | `xsd:decimal` | true | 0..1 |
| `fechaRegistro` | `xsd:dateTime` | true | 0..1 |
| `Solicitante` | `xsd:string` | true | 0..1 |
| `arquitectoNombre` | `xsd:string` | true | 0..1 |
| `arquitectoRegistroNacionalCAB` | `xsd:string` | true | 0..1 |
| `nroInmueble` | `xsd:string` | true | 0..1 |
| `idProyectoDesarrollo` | `xsd:decimal` | true | 0..1 |
| `idTipoObra` | `xsd:decimal` | true | 0..1 |
| `TipoProyecto` | `xsd:string` | true | 0..1 |
| `TipoObra` | `xsd:string` | true | 0..1 |
| `NumeroTramite` | `xsd:decimal` | true | 0..1 |
| `Resultado` | `xsd:string` | true | 0..1 |
| `EstadoTramite` | `xsd:string` | true | 0..1 |
| `idInsDocumento` | `xsd:decimal` | true | 0..1 |
| `nombreArchivo` | `xsd:string` | true | 0..1 |
| `FechaRegistroArch` | `xsd:dateTime` | true | 0..1 |
| `codigoCatastral` | `xsd:string` | true | 0..1 |
| `fechaAprobacion` | `xsd:dateTime` | true | 0..1 |
| `macroDistrito` | `xsd:string` | true | 0..1 |
| `distritoMunicipal` | `xsd:decimal` | true | 0..1 |
| `cantidadPisos` | `xsd:decimal` | true | 0..1 |
| `superficieLegal` | `xsd:double` | true | 0..1 |
| `nombreEdificio` | `xsd:string` | true | 0..1 |
| `SuperficieConstruida` | `xsd:decimal` | true | 0..1 |
| `geom` | `gml:PointPropertyType` | true | 0..1 |

### `sit:ubicacionvias2`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:PointPropertyType` | true | 0..1 |
| `objectid` | `xsd:int` | true | 0..1 |
| `featureid` | `xsd:int` | true | 0..1 |
| `TextString` | `xsd:string` | true | 0..1 |
| `nombalfa` | `xsd:string` | true | 0..1 |
| `alias` | `xsd:string` | true | 0..1 |
| `zona` | `xsd:string` | true | 0..1 |
| `tipovia` | `xsd:string` | true | 0..1 |
| `om` | `xsd:string` | true | 0..1 |
| `descripcion` | `xsd:string` | true | 0..1 |

### `sit:vias`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `gdbsanvi` | `xsd:decimal` | true | 0..1 |
| `codifica` | `xsd:string` | true | 0..1 |
| `gdbsnovi` | `xsd:string` | true | 0..1 |
| `cod_mat` | `xsd:string` | true | 0..1 |
| `gdbstivi` | `xsd:decimal` | true | 0..1 |
| `om` | `xsd:string` | true | 0..1 |
| `ruteo` | `xsd:string` | true | 0..1 |
| `fecha` | `xsd:string` | true | 0..1 |
| `gestion` | `xsd:decimal` | true | 0..1 |
| `reg_histor` | `xsd:string` | true | 0..1 |
| `longitud` | `xsd:decimal` | true | 0..1 |
| `novisible` | `xsd:decimal` | true | 0..1 |
| `cod_usuari` | `xsd:decimal` | true | 0..1 |
| `via_tipo` | `xsd:decimal` | true | 0..1 |
| `acopiar` | `xsd:decimal` | true | 0..1 |
| `via_materi` | `xsd:decimal` | true | 0..1 |
| `distrito` | `xsd:decimal` | true | 0..1 |
| `macro` | `xsd:string` | true | 0..1 |
| `jerarquia` | `xsd:decimal` | true | 0..1 |
| `nombalfa` | `xsd:string` | true | 0..1 |
| `alias` | `xsd:string` | true | 0..1 |
| `zonaref` | `xsd:string` | true | 0..1 |
| `idtmp` | `xsd:decimal` | true | 0..1 |
| `cuadrante` | `xsd:string` | true | 0..1 |
| `cod_via` | `xsd:decimal` | true | 0..1 |
| `wkb_geometry` | `gml:MultiCurvePropertyType` | true | 0..1 |
| `novi_alias` | `xsd:string` | true | 0..1 |

### `sit:zonas_nrocasos`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:SurfacePropertyType` | true | 0..1 |
| `macrodistrito` | `xsd:string` | true | 0..1 |
| `zona` | `xsd:string` | true | 0..1 |
| `codigozona` | `xsd:int` | true | 0..1 |
| `macro` | `xsd:int` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
| `POSITIVO` | `xsd:int` | true | 0..1 |
| `RECUPERADO` | `xsd:int` | true | 0..1 |
| `FALLECIDO` | `xsd:int` | true | 0..1 |
| `TOTAL` | `xsd:int` | true | 0..1 |

### `sit:zonas_seguras_ae`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |
| `nombre` | `xsd:string` | true | 0..1 |

### `sit:zonasgu2016`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `zonaref` | `xsd:string` | true | 0..1 |
| `macrodistrito` | `xsd:string` | true | 0..1 |
| `zona` | `xsd:string` | true | 0..1 |
| `wkb_geometry` | `gml:SurfacePropertyType` | true | 0..1 |
| `subalcaldia` | `xsd:string` | true | 0..1 |
| `codigozona` | `xsd:int` | true | 0..1 |
| `macro` | `xsd:int` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |

### `sit:zonasgu2016_label`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `geom` | `gml:MultiPointPropertyType` | true | 0..1 |
| `nombre` | `xsd:string` | true | 0..1 |

### `sit:zonasref`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `zonaref` | `xsd:string` | true | 0..1 |
| `macrodistrito` | `xsd:string` | true | 0..1 |
| `zona` | `xsd:string` | true | 0..1 |
| `wkb_geometry` | `gml:SurfacePropertyType` | true | 0..1 |
| `subalcaldia` | `xsd:string` | true | 0..1 |
| `codigozona` | `xsd:int` | true | 0..1 |
| `macro` | `xsd:int` | true | 0..1 |
| `distrito` | `xsd:int` | true | 0..1 |
