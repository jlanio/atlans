# executor/sync/scanner.py
"""
DatasetScanner — agrupa arquivos locais em datasets espaciais.
Trata Shapefile como pacote logico (shp+dbf+shx+prj+cpg).
"""
import hashlib
import logging
import time
from pathlib import Path

from executor.sync.paths import TRASH_DIR_NAME

logger = logging.getLogger("executor.sync")

# Extensoes de componentes de Shapefile
_SHP_EXTENSIONS = {".shp", ".dbf", ".shx", ".prj", ".cpg", ".sbn", ".sbx", ".fbn", ".fbx", ".ain", ".aih", ".ixs", ".mxs", ".atx", ".qpj"}
_SHP_REQUIRED = {".shp", ".dbf", ".shx"}

# Extensoes suportadas para sync (arquivos unicos)
_SINGLE_FILE_EXTENSIONS = {
    ".geojson", ".json", ".gpkg", ".kml", ".kmz",
    ".tiff", ".tif", ".csv", ".xlsx",
    ".zip", ".gml", ".fgb", ".parquet",
}

# Tudo que o sync reconhece
SUPPORTED_EXTENSIONS = _SINGLE_FILE_EXTENSIONS | _SHP_EXTENSIONS

# Arquivos/pastas ignorados
_IGNORE_NAMES = {".atlans-sync.json", ".DS_Store", "Thumbs.db", "__pycache__", ".git", TRASH_DIR_NAME}


class Dataset:
    """Representa um dataset espacial (pode ser 1 arquivo ou bundle Shapefile)."""

    def __init__(self, name: str, dataset_type: str):
        self.name = name
        self.type = dataset_type  # "shapefile" | "geojson" | "gpkg" | "csv" | "tiff" | etc
        self.files: dict[str, FileInfo] = {}  # filename → FileInfo
        self.is_complete = True

    def add_file(self, file_info: "FileInfo"):
        self.files[file_info.filename] = file_info

    @property
    def total_size(self) -> int:
        return sum(f.size for f in self.files.values())

    @property
    def primary_path(self) -> Path | None:
        """Retorna o path do arquivo principal (ex: .shp para Shapefile, .geojson para GeoJSON)."""
        if self.type == "shapefile":
            for f in self.files.values():
                if f.path.suffix.lower() == ".shp":
                    return f.path
        elif self.files:
            return next(iter(self.files.values())).path
        return None

    def file_hashes(self) -> dict[str, str]:
        return {name: f.md5 for name, f in self.files.items()}


class FileInfo:
    """Informacoes de um arquivo individual."""

    def __init__(self, path: Path):
        st = path.stat()  # um stat so: o segundo era I/O puro em vao
        self.path = path
        self.filename = path.name
        self.extension = path.suffix.lower()
        self.size = st.st_size
        self.mtime = st.st_mtime
        # Quando este stat foi tirado. E o que torna o par (size, mtime) uma
        # TESTEMUNHA confiavel de "nao mudou" — ver `_testemunho_confiavel`.
        self.stat_at = time.time()
        self._md5: str | None = None

    @property
    def md5(self) -> str:
        if self._md5 is None:
            self._md5 = _compute_md5(self.path)
        return self._md5

    def semear_md5(self, valor: str) -> None:
        """Adota o MD5 que o manifesto ja guardava para este arquivo.

        So e chamado quando (size, mtime) batem com o manifesto — isto e, quando
        o diff ja concluiu que o arquivo nao mudou. Sem isso, `_dataset_md5()`
        la na frente releria do disco o que acabamos de decidir nao reler.
        """
        self._md5 = valor

    def to_dict(self) -> dict:
        return {
            "md5": self.md5,
            "size": self.size,
            "mtime": self.mtime,
            "stat_at": self.stat_at,
        }


class DatasetScanner:
    """Escaneia uma pasta e agrupa arquivos em datasets espaciais."""

    def __init__(self, sync_dir: str, ignore_filter=None):
        self.sync_dir = Path(sync_dir)
        self._ignore = ignore_filter

    def scan(self) -> dict[str, Dataset]:
        """Retorna dict nome → Dataset com todos os datasets encontrados."""
        datasets: dict[str, Dataset] = {}
        shp_groups: dict[str, list[FileInfo]] = {}  # stem → arquivos

        for file_path in self.sync_dir.iterdir():
            # Symlinks NUNCA entram no sync. O upload nao tem `safe_join` como o
            # download tem, entao um link plantado na pasta (ex:
            # 'pontos.csv' → /opt/atlans/executor/certs/client.key) publicaria um
            # arquivo de fora no Drive do workspace — o validador nem abre .csv/
            # .xlsx e o bundle de shapefile e zipado sem checagem de conteudo.
            # Isto fecha o ESCAPE DE CAMINHO, nao a proveniencia do conteudo: um
            # hardlink continua invisivel aqui (is_symlink() e False) e nenhuma
            # checagem de caminho o pegaria — quem consegue linkar ja consegue
            # copiar os mesmos bytes para dentro da pasta.
            if file_path.is_symlink():
                logger.warning("Symlink '%s' ignorado pelo sync (aponta para fora do controle da pasta).",
                               file_path.name)
                continue
            if not file_path.is_file():
                continue
            if file_path.name in _IGNORE_NAMES or file_path.name.startswith("."):
                continue
            if self._ignore and self._ignore.should_ignore(file_path):
                continue

            ext = file_path.suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            # O QGIS (e afins) cria e remove temporarios o tempo todo: o arquivo
            # pode sumir entre o iterdir() e o stat() do FileInfo. Isso e normal,
            # nao um erro de sync — pula em vez de derrubar o scan inteiro.
            try:
                info = FileInfo(file_path)
            except OSError as exc:
                logger.debug("Arquivo '%s' indisponivel durante o scan (%s) — ignorado.", file_path.name, exc)
                continue

            if ext in _SHP_EXTENSIONS:
                # Agrupa por stem (nome sem extensao)
                stem = file_path.stem.lower()
                shp_groups.setdefault(stem, []).append(info)
            elif ext in _SINGLE_FILE_EXTENSIONS:
                # Dataset de arquivo unico
                ds_name = file_path.stem.lower()
                ds_type = ext.lstrip(".")
                if ds_type in ("tiff", "tif"):
                    ds_type = "raster"
                elif ds_type in ("csv", "xlsx"):
                    ds_type = "tabular"
                ds = Dataset(ds_name, ds_type)
                ds.add_file(info)
                datasets[ds_name] = ds

        # Processa grupos de Shapefile
        for stem, files in shp_groups.items():
            ds = Dataset(stem, "shapefile")
            extensions_found = set()
            for f in files:
                ds.add_file(f)
                extensions_found.add(f.extension)

            # Verifica completude (minimo: .shp + .dbf + .shx)
            ds.is_complete = _SHP_REQUIRED.issubset(extensions_found)
            if not ds.is_complete:
                missing = _SHP_REQUIRED - extensions_found
                logger.warning("Shapefile '%s' incompleto — faltam: %s", stem, missing)

            datasets[stem] = ds

        return datasets

    def diff(self, current: dict[str, Dataset], manifest_datasets: dict,
             force_hash: bool = False) -> tuple[list, list, list]:
        """
        Compara estado atual com manifesto.
        Retorna (novos, modificados, removidos) como listas de nomes de datasets.

        Para os datasets presentes dos DOIS lados, o veredito sai de (size,
        mtime) — que o manifesto ja guardava e o `scan()` acabou de ler no
        `stat()`. Antes o diff pedia o MD5 de tudo a cada ciclo (30s por
        padrao): numa pasta de campo com rasters, o disco ficava em 100% de
        leitura permanentemente sem NENHUM arquivo ter mudado.

        `force_hash=True` ignora o atalho e rehasheia tudo — e a rede de
        seguranca contra a reescrita que preserva o mtime (copia com `-p`),
        usada no boot e de hora em hora pelo ciclo.
        """
        new_datasets = []
        modified_datasets = []
        removed_datasets = []

        current_names = set(current.keys())
        manifest_names = set(manifest_datasets.keys())

        # Novos
        for name in current_names - manifest_names:
            ds = current[name]
            if ds.type == "shapefile" and not ds.is_complete:
                continue  # Nao sincroniza shapefile incompleto
            new_datasets.append(name)

        # Removidos
        for name in manifest_names - current_names:
            removed_datasets.append(name)

        # Modificados
        for name in current_names & manifest_names:
            ds = current[name]
            manifest_ds = manifest_datasets[name]
            manifest_files = manifest_ds.get("files", {})

            if not force_hash and _metadados_inalterados(ds, manifest_files):
                continue  # atalho barato: nem abriu o arquivo

            # Aqui o hash e obrigatorio: (size, mtime) divergiram e e ele que
            # separa uma edicao de verdade de um `touch` — sem esta confirmacao
            # abrir o arquivo no QGIS ja bastaria para re-enviar tudo.
            current_hashes = _hashes_atuais(ds)
            if current_hashes is None:
                continue
            manifest_hashes = {fname: info.get("md5") for fname, info in manifest_files.items()}

            if current_hashes != manifest_hashes:
                modified_datasets.append(name)
            else:
                _renovar_testemunho(ds, manifest_files)

        return new_datasets, modified_datasets, removed_datasets


# Pior granularidade de mtime que aparece em campo: FAT32/exFAT de pendrive e
# HD externo gravam o horario de modificacao em passos de 2 segundos.
_GRANULARIDADE_MTIME_S = 2.0


def _testemunho_confiavel(gravado: dict) -> bool:
    """O par (size, mtime) gravado consegue TESTEMUNHAR que o arquivo nao mudou?

    So consegue se, no instante em que foi coletado, o mtime do arquivo ja
    estivesse "fechado". Num FS de mtime grosseiro (FAT32/exFAT: 2s), uma
    gravacao feita logo APOS o nosso stat cai no MESMO balde de mtime — e como o
    registro DBF tem largura fixa, editar um atributo de shapefile no QGIS
    reescreve so o .dbf sem mudar o tamanho. Resultado: size e mtime identicos
    para todos os componentes, o atalho conclui "inalterado" e o arquivo do
    usuario NUNCA sobe (a varredura completa horaria era a unica rede).

    Duas saidas:
      * mtime com parte fracionaria → o FS tem resolucao sub-segundo e a janela
        de colisao e de milissegundos; nao existe na pratica;
      * senao, exige-se que o stat tenha sido tirado ao menos uma granularidade
        DEPOIS do mtime — dai qualquer gravacao posterior a ele cai
        obrigatoriamente num balde diferente e o atalho volta a ser seguro.

    Entrada sem `stat_at` (manifesto gravado antes deste campo) nao tem como
    provar nada: rehasheia uma vez e o `_renovar_testemunho` a reancora.
    """
    mtime = gravado["mtime"]
    if mtime % 1:
        return True
    stat_at = gravado.get("stat_at")
    if stat_at is None:
        return False
    return (stat_at - mtime) >= _GRANULARIDADE_MTIME_S


def _metadados_inalterados(ds: Dataset, manifest_files: dict) -> bool:
    """(size, mtime) de TODOS os arquivos batem com o manifesto?

    Tudo-ou-nada de proposito: semear o MD5 de parte dos arquivos e hashear o
    resto produziria um hash combinado meio velho, que acabaria gravado no
    manifesto como se fosse o estado atual do disco.
    """
    if set(ds.files) != set(manifest_files):
        return False

    for fname, finfo in ds.files.items():
        gravado = manifest_files[fname]
        if not isinstance(gravado, dict):
            return False
        md5_gravado = gravado.get("md5")
        # Manifesto antigo (ou entrada gravada sem stat) nao tem com o que
        # comparar — cai no hash.
        if not md5_gravado or gravado.get("size") is None or gravado.get("mtime") is None:
            return False
        if finfo.size != gravado["size"] or finfo.mtime != gravado["mtime"]:
            return False
        if not _testemunho_confiavel(gravado):
            return False

    for fname, finfo in ds.files.items():
        finfo.semear_md5(manifest_files[fname]["md5"])
    return True


def _renovar_testemunho(ds: Dataset, manifest_files: dict) -> None:
    """Reancora (size, mtime, stat_at) depois de o HASH confirmar que o conteudo
    e o mesmo.

    Sem isto, um `touch` — ou uma entrada gravada por versao antiga, sem
    `stat_at`, ou colhida cedo demais num pendrive — condenava o dataset a ser
    rehasheado a cada ciclo: nada muda, nada e enviado e, portanto, ninguem
    regrava a entrada do manifesto. Aqui a mutacao e no dict vivo do manifesto;
    o flush do fim do ciclo a persiste. Se ela se perder, o unico custo e mais
    um hash no ciclo seguinte.
    """
    for fname, finfo in ds.files.items():
        gravado = manifest_files.get(fname)
        if isinstance(gravado, dict):
            gravado["size"] = finfo.size
            gravado["mtime"] = finfo.mtime
            gravado["stat_at"] = finfo.stat_at


def entrada_de_manifesto(path: Path, md5: str) -> dict:
    """Entrada de 'files' para um arquivo que NOS acabamos de gravar (download).

    Passa pelo `FileInfo` para que o formato do testemunho (size/mtime/stat_at)
    tenha um lugar so: montado a mao em cada ponto de download, bastava esquecer
    o `stat_at` para o dataset ser rehasheado todo ciclo.
    """
    info = FileInfo(path)
    info.semear_md5(md5)
    return info.to_dict()


def _hashes_atuais(ds: Dataset) -> dict[str, str] | None:
    """MD5 de todos os arquivos do dataset, ou None se algum nao pode ser lido.

    O `scan()` ja trata o temporario que some entre o `iterdir` e o `stat`; aqui
    a janela e bem maior, porque o hash ABRE todos os arquivos — e na varredura
    completa horaria isso e a pasta inteira. Um unico arquivo que suma (QGIS/
    ArcGIS criam e removem temporarios o tempo todo) ou que esteja travado
    derrubava o ciclo com OSError, e com ele a deteccao de mudanca da pasta
    toda. Sem conseguir ler, nao ha veredito seguro a dar: o dataset fica para o
    proximo ciclo, quando o scan ja vera a pasta como ela ficou.
    """
    try:
        return ds.file_hashes()
    except OSError as exc:
        logger.info("Dataset '%s' nao pode ser lido agora (%s) — veredito adiado "
                    "para o proximo ciclo.", ds.name, exc)
        return None


# Chunk de leitura do MD5. 8 KB pagava uma chamada de leitura a cada 8 KB de
# raster; o uploader ja lia em 1 MB.
_CHUNK = 1024 * 1024


def _compute_md5(path: Path) -> str:
    """Calcula MD5 de um arquivo."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()
