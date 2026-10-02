# Ministerio del Ambiente del Perú — Geoservidor MINAM

- **Mantenedor:** MINAM (Perú)
- **Finalidade:** Ordenamiento territorial, áreas naturales protegidas, bosques, hidrografía e información ambiental del Perú.
- **Tipo de serviço:** ArcGIS Server (REST).
- **Catálogo REST:** <https://geoservidorperu.minam.gob.pe/arcgis/rest/services>
- **Serviços inventariados:** 261
- **Camadas inventariadas:** 4555
- **WFS também disponível:** sim — este ArcGIS expõe WFS. Verificado em `https://geoservidorperu.minam.gob.pe/arcgis/services/ServicioBase/MapServer/WFSServer` (18 camadas do serviço `ServicioBase`). Quando a camada existir nesse serviço, prefira o nó `WFS` do Atlans; nas demais, use `HttpRequest` com `f=geojson`.
- **Última coleta de metadados:** 2026-09-17

> [!warning] Como consumir no Atlans
> Para as camadas sem WFS, use o nó `HttpRequest` com `f=geojson` na URL da camada e leve a saída adiante com `from_key:"body"`.

## Navegação

- [[Geosserviços/Peru MINAM Geoservidor/Camadas|Camadas]]
