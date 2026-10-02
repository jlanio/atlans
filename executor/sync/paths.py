# executor/sync/paths.py
"""
Resolucao segura de caminhos dentro do diretorio de sync.

O nome de arquivo usado como destino de download vem do servidor
(`WorkspaceFile.original_name`, originalmente digitado por um usuario no upload).
Tratar esse valor como caminho confiavel permitia escapar do sync_dir com
`../`, com um caminho absoluto (`/etc/x.geojson`, `C:\\Windows\\x.geojson`) ou
atraves de um symlink plantado dentro da pasta — virando escrita/remocao
arbitraria de arquivo no host do executor.

O servidor tambem sanitiza na ingestao, mas o executor NAO pode depender disso:
ele confia no servidor para *o que executar*, nao para *onde escrever*.
"""
import logging
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from executor.utils import ocultar_no_windows

logger = logging.getLogger("executor.sync")

# Lixeira local do sync. Uma delecao no Drive nao pode virar `unlink()` no disco
# do tecnico: nao ha lixeira do SO no caminho, nao ha re-download de recuperacao
# e um shapefile perde .shp/.dbf/.shx de uma vez. Movemos para ca em vez de
# apagar. Fica DENTRO do sync_dir para o move ser um rename no mesmo volume
# (atomico e barato), e o scanner/watcher ignoram esse nome explicitamente para
# a lixeira nao virar um loop de reupload.
TRASH_DIR_NAME = ".atlans-trash"

# Como a lixeira mora dentro do sync_dir, ela come a mesma cota do notebook de
# campo e e invisivel para o tecnico (nome com ponto no Linux/macOS e atributo
# oculto no Windows — ver `move_dataset_to_trash`; ignorada por scanner e
# watcher). Sem expurgo, uma pasta com rotatividade normal — raster diario
# substituido no Drive — enche o disco em semanas, e o unico sintoma seria o
# 'Erro ao salvar manifesto' do manifest.py.
TRASH_RETENTION_DAYS = 14
TRASH_WARN_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB acumulados → avisa o painel

# Rotulo de pasta de descarte: a chave do manifesto vira nome de diretorio, e o
# manifesto e um arquivo em disco que pode ter sido editado a mao.
_TRASH_LABEL_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


class UnsafePathError(ValueError):
    """Nome de arquivo tentou escapar do diretorio de sync."""


def safe_join(base: Path, name: str) -> Path:
    """
    Devolve `base/name` garantindo que o resultado fique DENTRO de `base`.

    Levanta UnsafePathError se `name` contiver componentes de diretorio, for
    absoluto, ou se o caminho resolvido escapar da base (inclusive via symlink).
    """
    if not name or name in (".", ".."):
        raise UnsafePathError(f"Nome de arquivo invalido: {name!r}")

    # Qualquer separador de caminho e recusado — o sync e plano por design.
    normalized = name.replace("\\", "/")
    if "/" in normalized:
        raise UnsafePathError(f"Nome de arquivo contem separador de caminho: {name!r}")

    candidate = base / normalized
    try:
        base_resolved = base.resolve()
        # strict=False: o arquivo de destino ainda nao existe no download.
        resolved = candidate.resolve(strict=False)
    except OSError as exc:
        raise UnsafePathError(f"Falha ao resolver caminho para {name!r}: {exc}") from exc

    if resolved != base_resolved and base_resolved not in resolved.parents:
        raise UnsafePathError(
            f"Caminho {name!r} escapa do diretorio de sync ({resolved} fora de {base_resolved})."
        )
    return resolved


def safe_join_or_none(base: Path, name: str, *, context: str = "") -> Path | None:
    """Variante que loga e devolve None em vez de levantar — para loops de sync."""
    try:
        return safe_join(base, name)
    except UnsafePathError as exc:
        logger.error(
            "Caminho rejeitado%s: %s",
            f" ({context})" if context else "", exc,
        )
        return None


def is_inside(base: Path, path: Path) -> bool:
    """
    Confirma que `path`, JA RESOLVIDO (symlinks seguidos), fica dentro de `base`.

    Usado na contencao do UPLOAD: o download sempre passou por `safe_join`, mas
    o upload nao tinha contencao nenhuma — um symlink plantado na pasta de sync
    (`ln -s /opt/atlans/executor/certs/client.key pontos.csv`) publicava um
    arquivo de fora no Drive do workspace. Exige que o arquivo exista
    (strict=True): so subimos o que conseguimos resolver de fato.

    ESCOPO: isto e contencao de CAMINHO, nao de proveniencia de conteudo. Um
    hardlink continua passando (`resolve()` nao o desfaz e `is_symlink()` e
    False), e nao ha contencao possivel contra isso — quem consegue criar o
    hardlink ja consegue copiar o arquivo para dentro da pasta, o que publicaria
    exatamente os mesmos bytes. O que garantimos e que o executor so le bytes de
    dentro do sync_dir.
    """
    try:
        resolved = path.resolve(strict=True)
        base_resolved = base.resolve()
    except OSError:
        return False
    return resolved == base_resolved or base_resolved in resolved.parents


def _trash_label(ds_name: str) -> str:
    label = _TRASH_LABEL_UNSAFE.sub("_", ds_name).strip("._")
    return (label or "dataset")[:60]


def move_dataset_to_trash(sync_dir: Path, ds_name: str, files: Iterable[Path]) -> list[Path]:
    """
    Move os arquivos de UM dataset para `<sync_dir>/.atlans-trash/<ds>_<stamp>/`,
    preservando os nomes originais. Devolve a lista dos que NAO puderam ser
    movidos (vazia = descarte completo).

    O descarte e por DATASET, nao por arquivo, porque um shapefile so e
    utilizavel se .shp/.dbf/.shx compartilham o mesmo stem — e era justamente
    "um shapefile perde .shp/.dbf/.shx de uma vez" a razao de existir da lixeira.
    Carimbar cada arquivo individualmente quebrava o bundle de duas formas: o
    stamp tem granularidade de segundo (um laco sobre componentes de centenas de
    MB atravessa a virada) e o contador anti-colisao era independente por
    arquivo. Uma subpasta por descarte resolve stem, colisao e ainda da ao
    expurgo por idade uma unidade natural.
    """
    alvos = [p for p in files]
    if not alvos:
        return []

    trash = sync_dir / TRASH_DIR_NAME
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    label = _trash_label(ds_name)
    try:
        trash.mkdir(parents=True, exist_ok=True)
        # No Windows o ponto no nome nao esconde a pasta; sem o atributo oculto
        # a lixeira apareceria no meio dos dados do usuario. Reaplicado a cada
        # descarte porque mkdir(exist_ok=True) nao devolve se a pasta ja existia,
        # e ocultar uma pasta ja oculta e no-op.
        ocultar_no_windows(trash)
        dest_dir = trash / f"{label}_{stamp}"
        counter = 1
        while dest_dir.exists():
            dest_dir = trash / f"{label}_{stamp}_{counter}"
            counter += 1
        dest_dir.mkdir()
    except OSError as exc:
        logger.error("Falha ao criar a pasta de lixeira de '%s': %s", ds_name, exc)
        return alvos

    falhos: list[Path] = []
    for path in alvos:
        try:
            path.replace(dest_dir / path.name)
        except OSError as exc:
            logger.error("Falha ao mover '%s' para a lixeira: %s", path.name, exc)
            falhos.append(path)
    return falhos


def _size_of(path: Path) -> int:
    if path.is_dir():
        total = 0
        for sub in path.rglob("*"):
            try:
                if sub.is_file():
                    total += sub.stat().st_size
            except OSError:
                continue
        return total
    try:
        return path.stat().st_size
    except OSError:
        return 0


def purge_trash(sync_dir: Path, max_age_days: int = TRASH_RETENTION_DAYS) -> tuple[int, int]:
    """
    Remove descartes com mais de `max_age_days` dias. Sincrono (I/O de disco):
    o chamador roda em thread. Devolve (descartes_removidos, bytes_restantes).
    """
    trash = sync_dir / TRASH_DIR_NAME
    if not trash.is_dir():
        return 0, 0

    limite = time.time() - max_age_days * 86400
    removidos = 0
    restantes = 0
    for item in trash.iterdir():
        try:
            if item.stat().st_mtime < limite:
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink(missing_ok=True)
                removidos += 1
                continue
            restantes += _size_of(item)
        except OSError as exc:
            logger.debug("Lixeira: '%s' nao pode ser inspecionado (%s).", item.name, exc)
    return removidos, restantes
