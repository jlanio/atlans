# executor/sync/ignore.py
"""
IgnoreFilter — filtra arquivos/pastas baseado em .atlans-ignore (sintaxe gitignore).
"""
import logging
from pathlib import Path

import pathspec

from executor.utils import ocultar_no_windows

logger = logging.getLogger("executor.sync")

_IGNORE_FILENAME = ".atlans-ignore"


class IgnoreFilter:
    """Carrega e aplica padroes de exclusao do .atlans-ignore."""

    def __init__(self, sync_dir: str | Path):
        self.sync_dir = Path(sync_dir)
        self._spec: pathspec.PathSpec | None = None
        self._mtime: float = 0
        self._load()

    def _load(self):
        ignore_path = self.sync_dir / _IGNORE_FILENAME
        if not ignore_path.exists():
            self._spec = None
            self._mtime = 0
            return

        # Dotfile de config na pasta do usuario: no Windows o ponto nao esconde,
        # entao garantimos o atributo oculto sempre que o encontramos — mesmo
        # tratamento do .atlans-sync-config.json (ver sync_config._load_local).
        ocultar_no_windows(ignore_path)

        try:
            mtime = ignore_path.stat().st_mtime
            with open(ignore_path, encoding="utf-8") as f:
                lines = f.readlines()
            self._spec = pathspec.PathSpec.from_lines("gitwildmatch", lines)
            self._mtime = mtime
            logger.info("Carregado %s (%d regras).", _IGNORE_FILENAME, len(lines))
        except Exception as exc:
            logger.warning("Erro ao ler %s: %s", _IGNORE_FILENAME, exc)
            self._spec = None

    def reload(self):
        """Recarrega o arquivo se foi modificado."""
        ignore_path = self.sync_dir / _IGNORE_FILENAME
        if not ignore_path.exists():
            if self._spec is not None:
                self._spec = None
                self._mtime = 0
                logger.info("%s removido — filtros desativados.", _IGNORE_FILENAME)
            return

        try:
            current_mtime = ignore_path.stat().st_mtime
        except OSError:
            return

        if current_mtime != self._mtime:
            self._load()

    def should_ignore(self, path: str | Path) -> bool:
        """Retorna True se o path deve ser ignorado pelo sync."""
        if self._spec is None:
            return False
        try:
            rel = Path(path).relative_to(self.sync_dir)
        except ValueError:
            return False
        return self._spec.match_file(str(rel))
