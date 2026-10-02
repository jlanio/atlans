# Brasil — Serviços de Imagens (Amazônia + Centro-Oeste)

**Escopo expandido:** Catálogo de **WCS, Imagery REST, Tile APIs** e **Satélites Públicos** para Amazônia e Centro-Oeste.

---

## Estrutura Regional

### Amazônia (5 Estados)

#### Amazonas
- **SEMA SMART System** — Monitoramento de biodiversidade (12 UC estaduais, expansão para 42)
- **Dados INPE** — Landsat/Sentinel via Brazil Data Cube

#### Pará ⭐ (Tier-1)
- **SeloVerde Platform** (UFMG + SEMAS-PA + ITERPA)
  - WCS: SIMLAM-PA (`https://monitoramento.semas.pa.gov.br`)
  - Imagery: **Planet Scope** (3m, diário, 130+ satélites)
  - Cobertura: 230.000+ propriedades rurais (CAR)
  - Camadas: Desmatamento 2008+, MapBiomas 2008, Hidrologia, APP
  - **Status:** ✅ Ativo e bem-financiado (UFMG + WCS Brasil)

- **SEMAS-PA Dashboard**
  - WCS: Sim (SIMLAM-PA integrado)
  - Alerta: Desmatamento, degradação, queimadas
  - Frequência: Diária
  - Status: ✅ Ativo

#### Acre
- **IMAC SCCON Platform** (`https://sccon.acre.gov.br`)
  - Imagery: Landsat (histórico 1988-2024) + Sentinel-2
  - WCS: Parcial (via SIPAM)
  - Integração: SINAFLOR + AUTEX (autorizações florestais)
  - Status: ✅ Ativo

### Centro-Oeste (2 Estados)

#### Mato Grosso ⭐⭐ (Tier-1 Premium)
- **SEMA-MT GeoPortal + SIMLAM** (`https://geoportal.sema.mt.gov.br`)
  - **WCS:** Sim, operacional
  - **Imagery:** Planet Scope (3-5m, diário), Landsat, MODIS
  - **Resolução:** 3-30m
  - **Camadas:**
    - CAR (Cadastro Ambiental Rural)
    - Cobertura vegetal
    - AUTEX/AEF (autorizações florestais)
    - UC estaduais e federais
    - Terras indígenas
    - Desmatamento (alerta em tempo real)
  - **Dashboard:** Análise de dinâmica de mudanças, relatórios por município
  - **Status:** ✅ Ativo, robusto, financiado
  - **Responsável:** SEMA/MT + ICV (Simex monitoring)

- **SEMA-MT SCCON (Vegetation Monitoring)**
  - **Imagery:** Planet constellation (130+ satélites)
  - **Alerta:** Semanal
  - **Período:** Desde 2019
  - **Financiamento:** REM Program (Alemanha + UK via FUNBIO)
  - **Status:** ✅ Ativo

#### Mato Grosso do Sul
- **SEMADESC MS em Mapas** (`https://www.semadesc.ms.gov.br/informativo/ms-em-mapas/`)
  - Imagery: Sentinel-2 (parcial processada)
  - Camadas: CAR, limite municipal, infraestrutura, setores produtivos
  - Status: ✅ Ativo (foco socioeconômico)

---

## Recursos Cross-State (Amazônia + Centro-Oeste)

### INPE — Brazil Data Cube 🌍
- **URL:** `https://data.inpe.br/bdc`
- **Tipo:** WCS + STAC
- **Cobertura:** Brasil completo (Amazônia + Centro-Oeste)
- **Imagery:**
  - Sentinel-2 (10m, 10 dias)
  - Landsat-8/9 (30m, 8 dias)
  - CBERS-4A (MUX 20m, WPM 8m)
  - Amazonia-1 (22m)
- **Endpoints:**
  - WCS: `https://data.inpe.br/bdc/geoserver/mosaics/ows`
  - STAC: `https://data.inpe.br/bdc/stac`
- **Status:** ✅ Ativo

### SIPAM — Sistema de Proteção da Amazônia 🛰️
- **URL:** `https://panorama.sipam.gov.br/geonetwork/`
- **Tipo:** CSW Metadata Discovery
- **Cobertura:** Amazônia Legal (9 estados)
- **Imagery:** Landsat histórico (1988-2024), Carta-Imagem
- **Acesso:** Público
- **Status:** ✅ Ativo

### MapBiomas — Série Temporal 📊
- **URL:** `https://mapbiomas.org/`
- **Tipo:** Time Series Imagery (Landsat + Sentinel-2)
- **Período:** 1985-2023 (anual)
- **Resolução:** 30m
- **Camadas:** Floresta, Agricultura, Pastagem, Urbano, Água, Nuvem
- **Acesso:** Público + STAC
- **Status:** ✅ Ativo

### MapBiomas Alerta 🚨
- **URL:** `https://alerta.mapbiomas.org/`
- **Tipo:** Deforestation + Vegetation Change Alerts (Sentinel-2)
- **Resolução:** Alta (10m)
- **Frequência:** Mensal
- **Cobertura:** Brasil completo
- **Status:** ✅ Ativo desde 2019

---

## Resumo de Cobertura

| Métrica | Valor |
|---------|-------|
| **Estados catalogados** | 5 (Amazonas, Pará, Acre, MT, MS) |
| **Geoportais Tier-1** | 3 (Pará SeloVerde, SEMA-MT, SEMA-RO) |
| **Fontes de satélite** | 8 (Planet, Sentinel, Landsat, CBERS, Amazonia-1, MODIS, MapBiomas) |
| **Resolução média** | 3-30m |
| **Frequência atualização** | Diária a Mensal |
| **Área total coberta** | ~4,7 milhões km² |
| **WCS operacional** | ✅ Pará, Mato Grosso, Rondônia |

---

## Consumo no Atlans

**Recomendação:** Priorizar **Pará SeloVerde** e **SEMA-MT** para WCS + Imagery.

```
Node 1: Fetch WCS (SIMLAM-PA ou SIMLAM-MT)
  └─ Endpoint: https://monitoramento.semas.pa.gov.br/wcs
  
Node 2: Tile API (Planet Scope)
  └─ Template: https://api-geoportal.sedam.ro.gov.br/services/{layer}/{z}/{x}/{y}.png
  
Node 3: Time Series (MapBiomas)
  └─ STAC: https://mapbiomas.org/download
  
Node 4: Clip + Classify (NDVI, NDBI)
  └─ Output: GeoTIFF ou COG
```

---

## Referências

- [[Geosserviços/Índice|Catálogo de Geoportais — Américas]]
- [[Geosserviços/Brasil/INDE|INDE — Brasil Vetorial]]
- [[Geosserviços/Rondônia SEDAM|Rondônia — SEDAM Imagery]]

**Catalogado:** 2026-09-18 | Zeus
