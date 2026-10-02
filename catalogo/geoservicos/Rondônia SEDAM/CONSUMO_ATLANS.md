# Como Consumir Imagens SEDAM no Atlans

## Rondônia — Mosaicos SEDAM

### Camada de Sentinel-2 (Recomendado)

```javascript
// Node: "Fetch Imagery from Cloud Service"
// Tipo: HTTP Fetch / URL Template

const url = `https://api-geoportal.sedam.ro.gov.br/tilesapi/tiles/sentinel2/{z}/{x}/{y}`;
const bbox = [-65.5, -11.9, -59.6, -7.5]; // Rondônia
const zoom = [7, 8, 9, 10, 11, 12];

// Retorna: COG GeoTIFF (Cloud Optimized)
```

### Camada MapBiomas (Cobertura Anual)

```javascript
// Node: "Get Raster Mosaic"
// Tipo: Time Series

const url = `https://geoportal.sedam.ro.gov.br/mosaicos/mapbiomas/{year}/{z}/{x}/{y}.png`;
const years = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023];

// Classes: floresta, agricultura, pastagem, urbano, água, nuvem
```

### Camada Planet Labs (Mensal, Alta-Res)

```javascript
// Node: "Tile Layer"
// Tipo: Monthly Coverage
// ⚠️ Requer autenticação (Token Planet)

const url = `https://geoportal.sedam.ro.gov.br/mosaicos/planet/{YYYY}{MM}/{z}/{x}/{y}.png`;
const example = `https://geoportal.sedam.ro.gov.br/mosaicos/planet/202407/{z}/{x}/{y}.png`;

// Resolução: 3–5m | Cobertura 100%
```

## Acesso Programático (Python)

```python
import rasterio
from rasterio.io import MemoryFile
import requests

# COG via TilesAPI
def fetch_cog_tile(bucket, caminho, z, x, y):
    url = f"https://api-geoportal.sedam.ro.gov.br/tilesapi/tiles/{bucket}/{caminho}/{z}/{x}/{y}"
    r = requests.get(url)
    
    with MemoryFile(r.content) as memfile:
        with memfile.open() as src:
            return src.read()

# Exemplo
data = fetch_cog_tile("sentinel2", "B4", 9, 251, 413)
```

## Integração Atlans (Workflow)

**Node 1:** Bounds Rondônia (`-65.5, -11.9, -59.6, -7.5`)  
**Node 2:** Fetch Tiles (Sentinel-2 / MapBiomas)  
**Node 3:** Clip by CAR ou shapefile  
**Node 4:** Classify (NDVI, NDBI, NDMI) ou export  

## Limitações

- ⚠️ Planet Labs requer login (SEDAM)
- ⚠️ Série histórica: ~2008–2024 (gaps em satélites específicos)
- ✅ Sem limite de taxa (públicos)
- ✅ Sem download de geometria (somente raster)

**Publicado:** 2026-09-18 | Zeus
