# Image map — the `CartaImagem` node

> Contract of the output node that generates the **image map** (PNG, JPG or PDF) with the layers the workflow
> chooses. Code: `flow/nodes/outputs/carta_imagem.py` (the node) and `flow/utils/carta.py` (the
> math, pure). Tests: `tests/unit/test_carta_imagem.py`, `tests/unit/test_carta_helpers.py`,
> `tests/integration/test_carta_no_executor.py`.

## 1. What it is

A single node, an output one (`type: "output"`), with **dynamic ports**: each port is a layer of the map and
the person connects to it whatever output they want to see drawn. Whatever is not connected stays out. When it runs, the
node composes the layers with title, subtitle, legend, credits, scale bar, north arrow, coordinate
grid and basemap — each element **optional**, chosen in the configuration — and writes the
file as a **run artifact** (the same artifact list, the Home's Meu → Artefatos (Mine → Artifacts), the
download). There is no inline preview and no card on the Home: the image map is a file to download.

There is no end-of-run hook and there does not need to be one: the graph itself guarantees that the node runs
after all the layers connected to its ports.

## 2. Ports and edges — the rules that govern

The rules come from the editor (`web/app/components/workflow/utils/resolve-edge-keys.ts`, `node-ports.ts`)
and from the executor (`flow/executor/edge_resolver.py`):

| Declared ports | What the editor does | What reaches the node |
|---|---|---|
| **2 or more** | writes each edge's `to_key` with the port name; one connection point per port | `inputs[nome_da_porta]` — the port's layer; a port without a layer is skipped with a warning |
| **1 or none** | anonymous edge; the canvas blocks the second edge (`limitadoAUmaAresta`) | the previous node's dict spread out (`inputs["output"]`…): the map draws the first GeoDataFrame that arrives, with the port name (or "Camada") in the legend |

Why block the second edge with 0/1 port: two anonymous edges would spread both dicts into the
same key, the last one would win and the map would come out with a single layer — and the node has no way to notice the
loss. It is the same rule as `SubWorkflowOutput`.

The port name has to be an identifier (`NOME_DE_PORTA`: letters, numbers and `_`), which is why the
**legend label has its own field** (`rotulos`); without it, the port name with `_` turned into a space.
The order of the ports is the drawing order (the first one goes at the bottom) and the legend order.

## 3. Properties

| Name | Type | Default | Notes |
|---|---|---|---|
| `ports` | `ports` | `[]` | one port per layer |
| `titulo` | string | `Carta` | also gives the file name (`slugify(titulo).ext`) |
| `subtitulo`, `creditos` | string | empty | optional; the basemap attribution goes into the credits on its own |
| `formato` | select | `png` | `png`, `jpg` (quality 90), `pdf` (vector for the geometries) |
| `tamanho` | select | `a4-paisagem` | A4/A3, landscape/portrait (ISO 216) |
| `dpi` | integer | 150 | 72 to 300; **ceiling of 30 Mpx** per page (A3 at 300 dpi passes) |
| `rotulos` | keyvalue | `{}` | port → label in the legend |
| `cores` | keyvalue | `{}` | port → `#RRGGBB`; empty = 8-color palette; an invalid color is an error |
| `opacidade` | number | 0.7 | 0–1, for all layers |
| `legenda`, `escala`, `norte` | boolean | `true` | |
| `grade` | boolean | `false` | coordinate lines and labels on the edges |
| `fundo` | select | `nenhum` | `hibrido` / `satelite` / `ruas` (the installation's, `MAPA_*`), `personalizado` |
| `fundo_url` | string | empty | template with `{z}`, `{x}` and `{y}`; only with `fundo = personalizado` |
| `crs` | string | `auto` | see §4 |
| `credential_id` | credential | empty | Bearer token for the download; without it the artifact is public; disappears with `executor` locality |
| `localidade` | select | `herdar` | `herdar` / `executor` — like every node that writes an artifact |

`validate_node_parameters` coerces types but does not apply minimum/maximum: dpi, size and the pixel ceiling
are checked in `execute`. `keyvalue` and `ports` arrive as an object or as JSON in a string (an old saved
workflow) — the parsers are tolerant.

## 4. The image map's CRS

| `crs` | `fundo` | Result |
|---|---|---|
| any | ≠ `nenhum` | **EPSG:3857** always — the tiles are Web Mercator and the basemap is not reprojected |
| `auto` | `nenhum` | the **local UTM** estimated from the center of the extent of all layers (`estimate_utm_crs`); an extent above ~6° of longitude gets a distortion warning; with no UTM zone (polar regions) it falls back to 3857 with a warning |
| `EPSG:xxxx` / WKT | `nenhum` | the requested CRS; invalid text is an error |

The order matters: a layer **without a CRS is treated as EPSG:4326 before** any reprojection (a
`set_crs` with the map's CRS would label degrees as meters).

The **scale bar only exists in a projected CRS** (`is_projected`); in degrees it is skipped with a warning
in the log. In 3857 the length is corrected by cos(central latitude) — the bar measures the real distance
on the ground, not the distance on the plane. Round lengths: 1, 2 or 5 × 10ⁿ meters, about one fifth
of the map's width.

The **grid**: in 3857 the lines are round longitudes/latitudes (the conversion is exact: x depends only
on lon, y only on lat); in UTM, round multiples of meters; in degrees, degrees.

## 5. Page and composition

The frame is fixed and the extent grows to its proportion (it never crops): map on the left; right-hand
column with the legend (it only exists with a legend; without it the map takes the page); title and subtitle at the
top; credits and the date + CRS in the footer; north arrow and scale inside the map (top right
and bottom left corners). Extent = union of the layers + 5 % margin; a single point gets 500 m
(or 0.01°) per side.

The drawing uses matplotlib's object-oriented API (`Figure` + `FigureCanvasAgg`) in a thread,
with `matplotlib.use("Agg")` before any plot (`gdf.plot` imports pyplot internally and the
backend is resolved in the thread; on the desktop Tk is pruned from the runtime). Geometries are simplified to
1 px before drawing; above 200 thousand features the log warns and the PDF comes out rasterized.

matplotlib is imported **only at drawing time** — `flow/` is imported by the API and by the catalog
tests. On an old executor, without the library, the node fails with "A carta imagem precisa do
matplotlib no executor: atualize…" (The image map needs matplotlib on the executor: update…). The font cache goes to `artifacts_root()/.mpl`.

## 6. Basemap (tiles)

- The named basemaps are the installation's, the same ones as the web map (`web/lib/fundos-do-mapa.ts`):
  `MAPA_HIBRIDO_URL`, `MAPA_SATELITE_URL` and `MAPA_RUAS_URL` (with the `_CREDITO` ones), in the
  API environment. The code ships no satellite at all; the streets, without configuration, are `tile.openstreetmap.org`.
  The executor does not have this configuration: the server injects it into the node when dispatching
  (`fundo_da_instalacao`, `app/services/fundos_do_mapa.py`), and without it the executor's environment applies.
  The injection writes to both forms of the node's properties and always replaces whatever comes in the workflow.
  Without the hybrid, the satellite applies, as on the web. A named basemap without configuration fails saying
  which variable is missing. `personalizado` requires `{z}`, `{x}` and `{y}`.
- An executor of this version with an earlier server does not receive the basemap (the old server does not
  inject it), and the map says so, instead of saying that the installation does not have it. That is why the server
  is updated before the executors and the desktop app.
- Zoom: the lowest one at which the map's width in tile pixels reaches the page width; ceiling of
  **256 tiles** (the zoom goes down until it fits — it never fails because of size) and maximum zoom 19.
- Each tile goes through **`safe_httpx_request`** (pins the IP, blocks redirects, limits the body to 2 MB),
  as in the HTTP nodes: a template written in the workflow cannot reach the internal network or the cloud
  metadata (`validate_url_ssrf`). Two connections at a time, User-Agent `Atlans/carta (+<site da instalação>)`
  (`flow/utils/identidade.py`),
  two retries only on transport error/502/503/504; 4xx is a definitive error.
- Attribution: `© OpenStreetMap contributors` (ODbL — mandatory) or the basemap's `MAPA_*_CREDITO`
  go into the credits on their own. The OSM usage policy asks for light and identified use; the basemap is
  optional and off by default.
- The executor needs internet at run time; without it the image map fails (the basemap was requested).

## 7. The artifact

`persistir_artefato(localidade, content, filename, content_type, …)` — the same path as the other
output nodes: MinIO through a pre-signed URL (with the right `Content-Type`: `image/png`, `image/jpeg`,
`application/pdf`) or the executor's disk with "manter apenas no executor" (keep only on the executor). The server records the raw
`format` (`png`/`jpg`/`pdf`); the download forces `attachment`.

The node returns the **flat** keys declared in `outputs` (`artifact_filename`,
`artifact_s3_key`, `format`, `size_bytes`, `camadas`, `largura_px`, `altura_px`) plus `__artifact__`
— the executor compares the top-level keys with the declared ones and lights up the drift warning in the panel when
they do not match.

**Two nodes with the same title in the same run** would write the same S3 key and the server would deduplicate
silently: the node registers the file name in the run's `context` and the second one fails asking for different
titles (the same node on retry is not a collision).

## 8. Where the image map appears

- `/artifacts` (format badge with an image/PDF icon) and Meu → Artefatos (Mine → Artifacts) on the Home (icon by
  extension; the row is inert, with the reason "carta imagem: sem prévia no globo — baixe o arquivo" (image map: no
  preview on the globe — download the file)).
- The run panel shows the node's output keys, as for every node; it does not list artifacts
  (for any format) — follow-up.
- The Home assistant only emits `camada` for GeoJSON; an image map generated by an assistant workflow
  stays in the artifact list — follow-up.

## 9. Dependency

`matplotlib==3.10.9` in `requirements.txt` and `executor/requirements-full.txt` (the desktop uses the
executor's lock). CI, images and the desktop runtime run Python 3.12; matplotlib's 3.10.x line
brings pillow, contourpy, cycler, fonttools, kiwisolver and pyparsing. Agg and PDF backends
built in and the DejaVu font in the package — no system cairo/freetype.

The desktop lock is generated by `npm run python:lock` with a `python.exe`; with no Windows at hand, the
same resolution comes out of pip on any platform:

```bash
python -m pip install --dry-run --ignore-installed --only-binary=:all: \
  --platform win_amd64 --python-version 3.10 --implementation cp --abi cp310 \
  --report /tmp/report.json -c desktop/requirements.lock.txt -r executor/requirements-full.txt
# the {name==version} set of the report's "install" has to be IDENTICAL to the lock's lines;
# the CI `desktop` job (windows-latest, `python:lock:check`) is the final judge.
```

Executors only get the node when they update the image (Docker) or the desktop app.
