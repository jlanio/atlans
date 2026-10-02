# U.S. Census Bureau — TIGERweb

- **Mantenedor:** U.S. Census Bureau
- **Finalidade:** Malha censitária dos EUA: estados, condados, lugares, hidrografia, áreas legislativas e escolares.
- **Tipo de serviço:** ArcGIS Server (REST) — **não expõe WFS**.
- **Catálogo REST:** <https://tigerweb.geo.census.gov/arcgis/rest/services>
- **Serviços inventariados:** 170
- **Camadas inventariadas:** 4144
- **Última coleta de metadados:** 2026-09-17

> [!warning] Como consumir no Atlans
> Estes serviços **não respondem a WFS** (o pedido `WFSServer` devolve HTTP 400). Use o nó `HttpRequest` com `f=geojson` na URL da camada, e passe o corpo adiante com `from_key:"body"`. O nó `WFS` do Atlans não serve aqui. Formato de consulta declarado: `geoJSON`.

## Navegação

- [[Geosserviços/EUA TIGERweb/Camadas|Camadas]]
