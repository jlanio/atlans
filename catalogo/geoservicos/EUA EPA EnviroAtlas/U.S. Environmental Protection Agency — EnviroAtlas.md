# U.S. Environmental Protection Agency — EnviroAtlas

- **Mantenedor:** U.S. Environmental Protection Agency
- **Finalidade:** Serviços ecossistêmicos, cobertura do solo, bacias e indicadores ambientais dos EUA.
- **Tipo de serviço:** ArcGIS Server (REST) — **não expõe WFS**.
- **Catálogo REST:** <https://enviroatlas.epa.gov/arcgis/rest/services>
- **Serviços inventariados:** 45
- **Camadas inventariadas:** 256
- **Última coleta de metadados:** 2026-09-17

> [!warning] Como consumir no Atlans
> Estes serviços **não respondem a WFS** (o pedido `WFSServer` devolve HTTP 400). Use o nó `HttpRequest` com `f=geojson` na URL da camada, e passe o corpo adiante com `from_key:"body"`. O nó `WFS` do Atlans não serve aqui. Formato de consulta declarado: `geoJSON`.

## Navegação

- [[Geosserviços/EUA EPA EnviroAtlas/Camadas|Camadas]]
