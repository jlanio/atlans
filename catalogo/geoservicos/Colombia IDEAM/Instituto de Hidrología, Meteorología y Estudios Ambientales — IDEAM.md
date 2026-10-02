# Instituto de Hidrología, Meteorología y Estudios Ambientales — IDEAM

- **Mantenedor:** IDEAM (Colômbia)
- **Finalidade:** Clima, recursos hídricos, cobertura da terra, ecossistemas, degradação de solos, riscos e vulnerabilidade ambiental da Colômbia.
- **Tipo de serviço:** ArcGIS Server (REST). **64 dos 90 serviços também expõem WFS.**
- **Catálogo REST:** <https://visualizador.ideam.gov.co/gisserver/rest/services>
- **Serviços inventariados:** 90 (todos com geoJSON)
- **Camadas inventariadas:** 927
- **Camadas também acessíveis via WFS:** 731 (em 64 serviços)
- **Última coleta de metadados:** 2026-09-17

> [!tip] Como consumir no Atlans
> **Prefira o nó `WFS`** quando o serviço tiver WFS — ele é a entrada vetorial nativa do Atlans. O endpoint é `https://visualizador.ideam.gov.co/gisserver/services/<serviço>/MapServer/WFSServer`. Para os serviços sem WFS, use `HttpRequest` com `f=geojson` e `from_key:"body"`.

## Navegação

- [[Geosserviços/Colombia IDEAM/Camadas|Camadas]]
