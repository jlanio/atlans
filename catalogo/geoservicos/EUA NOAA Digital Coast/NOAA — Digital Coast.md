# NOAA — Digital Coast

- **Mantenedor:** NOAA — Office for Coastal Management
- **Finalidade:** Zona costeira dos EUA: cadastro marinho, cobertura do solo costeira, elevação e áreas submersas.
- **Tipo de serviço:** ArcGIS Server (REST) — **não expõe WFS**.
- **Catálogo REST:** <https://coast.noaa.gov/arcgis/rest/services>
- **Serviços inventariados:** 240
- **Camadas inventariadas:** 981
- **Última coleta de metadados:** 2026-09-17

> [!warning] Como consumir no Atlans
> Estes serviços **não respondem a WFS** (o pedido `WFSServer` devolve HTTP 400). Use o nó `HttpRequest` com `f=geojson` na URL da camada, e passe o corpo adiante com `from_key:"body"`. O nó `WFS` do Atlans não serve aqui. Formato de consulta declarado: `geoJSON`.

## Navegação

- [[Geosserviços/EUA NOAA Digital Coast/Camadas|Camadas]]
