# Rondônia — SEDAM Geoportal

**Instituição:** Secretaria de Estado do Desenvolvimento Ambiental (SEDAM) | Governo do Estado de Rondônia

**Website:** https://geoportal.sedam.ro.gov.br/

**Coordenadoria de Geociências (Cogeo)**

## Tipo de Serviço

- ✅ **WFS 2.0** (features vetoriais)
- ✅ **WMS 1.1/1.3** (mapas)
- ✅ **Tile API (COG)** — Cloud Optimized GeoTIFF via Minio
- ✅ **Imagery — Satélite** (mosaicos mensais/anuais)
- ✅ **Data Discovery** — Landsat, Sentinel-2, CBERS, Planet, Amazonia-1, SPOT

## Endpoints

| Serviço | URL | Versão | Status |
|---------|-----|--------|--------|
| WFS/WMS (GeoServer) | `https://geoportal.sedam.ro.gov.br/geoserver/ows` | 2.0/1.3 | ✅ Ativo |
| Tiles API (COG) | `https://api-geoportal.sedam.ro.gov.br/tilesapi/tiles/{bucket}/{caminho}/{z}/{x}/{y}` | COG | ✅ Ativo |
| Imagery (XYZ) | `https://api-geoportal.sedam.ro.gov.br/services/{camada}/tiles/{z}/{x}/{y}.png` | XYZ | ✅ Ativo |
| Mosaicos Satélite | `https://geoportal.sedam.ro.gov.br/mosaicos/{satelite}/{camada}/{z}/{x}/{y}.png` | PNG | ✅ Ativo |

## Camadas (Principais Temas)

### Vetoriais (WFS)
- Áreas Embargadas
- Unidades de Conservação Estaduais
- Limite de Rondônia
- Cadastro Ambiental Rural (CAR)
- Hidografia, hidrologia
- Topografia (topodata)

### Raster — Mosaicos de Satélite

**Planet Labs** (mensal)
- Cobertura Rondônia
- Resolução: ~3-5m
- Período: 2020–2024 (ongoing)
- Zoom: 7–17

**Sentinel-2 (ESA)**
- Mosaicos mensais
- Resolução: 10m (B2/B3/B4/B8)
- Período: 2015–2024
- Zoom: 7–17

**CBERS-4A (Satélite sino-brasileiro)**
- Composições: MUX (20m), WPM (8m)
- Período: 2019–2020
- Exemplo: `/mosaicos/cbers4a/mux/072020/`

**Amazonia-1 (INPE)**
- Período: 2021–2024
- Zoom: 7–17

**SPOT (Histórico)**
- 2008 (ortofoto)
- Resolução: ~2.5m

**MapBiomas**
- Cobertura e uso do solo (anual)
- Classes: floresta, agricultura, pastagem, urbano, etc.
- Período: 1985–2023

## Autenticação

- ✅ **Público** para visualização web
- ⚠️ **Autenticação requerida** para:
  - Download direto de mosaicos
  - Análise de série temporal
  - Exportação de mapas
  - Dados de satélite Planet (acesso restrito)

## Zoom Efetivo

- **Mínimo:** 7
- **Máximo:** 17 (depende do mosaico)

## Referências

- [[Geosserviços/Brasil/INDE|Catálogo Brasil — INDE]]
- [[Geosserviços/Índice|Índice de Geoportais]]
- Documentação oficial: https://geoportal.sedam.ro.gov.br/documentacao/docs/geoservicos

**Catalogado:** 2026-09-18 | Zeus
