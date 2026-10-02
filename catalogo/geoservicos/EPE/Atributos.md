# EPE — atributos das camadas

Geoportal: [[Geosserviços/EPE/Empresa de Pesquisa Energética — EPE|Empresa de Pesquisa Energética — EPE]]

Os campos abaixo vêm de `DescribeFeatureType` (XSD), sem download de feições.

## EPE (7)

### `EPE:Bacia Efetiva Probabilística 2023`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `situacao` | `xsd:string` | true | 0..1 |
| `bacia` | `xsd:string` | true | 0..1 |
| `bef_prob` | `xsd:double` | true | 0..1 |
| `rgb` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `EPE:bacsedimen`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `objectid` | `xsd:long` | true | 0..1 |
| `situacao` | `xsd:string` | true | 0..1 |
| `bacia` | `xsd:string` | true | 0..1 |
| `area_km2` | `xsd:double` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `EPE:embasam`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `objectid` | `xsd:long` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `EPE:IA Armazenamento C 2023`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ipa_armazc` | `xsd:int` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `EPE:IPA Total 2023`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `ipa_total` | `xsd:int` | true | 0..1 |
| `rgb` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `shape_area` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiSurfacePropertyType` | true | 0..1 |

### `EPE:Linhas de Distribuição de Energia Elétrica Submarinas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `cod_id` | `xsd:string` | true | 0..1 |
| `pn_con_1` | `xsd:string` | true | 0..1 |
| `pn_con_2` | `xsd:string` | true | 0..1 |
| `ctat` | `xsd:string` | true | 0..1 |
| `ct_cod_op` | `xsd:string` | true | 0..1 |
| `conj` | `xsd:long` | true | 0..1 |
| `are_loc` | `xsd:string` | true | 0..1 |
| `dist` | `xsd:long` | true | 0..1 |
| `pac_1` | `xsd:string` | true | 0..1 |
| `pac_2` | `xsd:string` | true | 0..1 |
| `fas_con` | `xsd:string` | true | 0..1 |
| `tip_inst` | `xsd:string` | true | 0..1 |
| `tip_cnd` | `xsd:string` | true | 0..1 |
| `pos` | `xsd:string` | true | 0..1 |
| `odi` | `xsd:string` | true | 0..1 |
| `ti` | `xsd:string` | true | 0..1 |
| `cm` | `xsd:string` | true | 0..1 |
| `sitcont` | `xsd:string` | true | 0..1 |
| `comp` | `xsd:double` | true | 0..1 |
| `descr` | `xsd:string` | true | 0..1 |
| `uni_tr_mt` | `xsd:string` | true | 0..1 |
| `ctmt` | `xsd:string` | true | 0..1 |
| `uni_tr_at` | `xsd:string` | true | 0..1 |
| `sub` | `xsd:string` | true | 0..1 |
| `shape_leng` | `xsd:double` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |

### `EPE:Linhas de Transmissão de Energia Elétrica Submarinas`

| Campo | Tipo XSD | Nulo | Ocorrência |
|---|---|---:|---|
| `id` | `xsd:long` | true | 0..1 |
| `nome` | `xsd:string` | true | 0..1 |
| `fonte` | `xsd:string` | true | 0..1 |
| `ano_planej` | `xsd:double` | true | 0..1 |
| `ano_opera` | `xsd:double` | true | 0..1 |
| `status` | `xsd:string` | true | 0..1 |
| `n_circuito` | `xsd:double` | true | 0..1 |
| `tipo_circ` | `xsd:string` | true | 0..1 |
| `tipo` | `xsd:string` | true | 0..1 |
| `tipo_rede` | `xsd:string` | true | 0..1 |
| `concession` | `xsd:string` | true | 0..1 |
| `obs` | `xsd:string` | true | 0..1 |
| `r1` | `xsd:string` | true | 0..1 |
| `nt` | `xsd:string` | true | 0..1 |
| `cod_item` | `xsd:string` | true | 0..1 |
| `cod_empre` | `xsd:string` | true | 0..1 |
| `status_tra` | `xsd:string` | true | 0..1 |
| `tens_statu` | `xsd:string` | true | 0..1 |
| `tensao` | `xsd:double` | true | 0..1 |
| `extensao` | `xsd:double` | true | 0..1 |
| `tracadorea` | `xsd:string` | true | 0..1 |
| `pde2029` | `xsd:string` | true | 0..1 |
| `pde2030` | `xsd:string` | true | 0..1 |
| `id_ons` | `xsd:string` | true | 0..1 |
| `sentidons` | `xsd:string` | true | 0..1 |
| `the_geom` | `gml:MultiCurvePropertyType` | true | 0..1 |
