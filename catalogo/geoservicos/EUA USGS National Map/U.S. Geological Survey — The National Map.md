# U.S. Geological Survey — The National Map

- **Mantenedor:** U.S. Geological Survey
- **Finalidade:** Base cartográfica nacional dos EUA: limites administrativos, transporte, estruturas, relevo e toponímia.
- **Tipo de serviço:** ArcGIS Server (REST) — **não expõe WFS**.
- **Catálogo REST:** <https://carto.nationalmap.gov/arcgis/rest/services>
- **Serviços inventariados:** 7
- **Camadas inventariadas:** 229
- **Última coleta de metadados:** 2026-09-17

> [!warning] Como consumir no Atlans
> Estes serviços **não respondem a WFS** (o pedido `WFSServer` devolve HTTP 400). Use o nó `HttpRequest` com `f=geojson` na URL da camada, e passe o corpo adiante com `from_key:"body"`. O nó `WFS` do Atlans não serve aqui. Formato de consulta declarado: `geoJSON`.

## Navegação

- [[Geosserviços/EUA USGS National Map/Camadas|Camadas]]
