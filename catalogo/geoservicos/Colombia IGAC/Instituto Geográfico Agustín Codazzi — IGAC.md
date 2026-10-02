# Instituto Geográfico Agustín Codazzi — IGAC

- **Mantenedor:** IGAC (Colômbia)
- **Finalidade:** Cadastro, cartografia, geodésia, limites, agrologia, cobertura e uso da terra, ordenamento territorial e dados de referência da Colômbia.
- **Tipo de serviço:** ArcGIS Server (REST). **494 dos 1269 serviços abertos também expõem WFS.**
- **Catálogo REST:** <https://mapas.igac.gov.co/server/rest/services>
- **Serviços inventariados:** 1471
- **Serviços abertos com geoJSON:** 1269
- **Camadas inventariadas:** 18422
- **Camadas também acessíveis via WFS:** 6969 (em 494 serviços)
- **Serviços com erro/transitoriedade na coleta:** 60
- **Última coleta de metadados:** 2026-09-17

> [!tip] Como consumir no Atlans
> Para serviços marcados **WFS**, prefira o nó `WFS`: `https://mapas.igac.gov.co/server/services/<serviço>/MapServer/WFSServer`. Nos demais, use `HttpRequest` no endpoint da camada com `query`, `f=geojson`, paginação (`resultOffset`/`resultRecordCount`) e `from_key:"body"`. Cada serviço informa `maxRecordCount`; não presuma que todos aceitam o mesmo tamanho de página.

> [!warning] Acesso restrito ou instável
> Cinco pastas exigem token: `cartografia_tableros`, `minasyenergia`, `nombresgeograficos`, `poblacion` e `seguridad`. Elas não foram inventariadas como públicas. Outros 60 serviços falharam durante a coleta e devem ser retestados antes de uso.

## Navegação

- [[Geosserviços/Colombia IGAC/Camadas|Camadas]]
- [[Geosserviços/Colombia IGAC/Atributos|Atributos]]
