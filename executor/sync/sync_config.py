# executor/sync/sync_config.py
"""
SyncConfig — configuracao de sync seletivo.
Controla quais datasets remotos devem ser baixados no modo bidirecional.

Este modulo tambem concentra os parametros de RITMO do GeoSync (concorrencia,
piso entre ciclos, tamanho do pool de threads). Eles moram aqui e nao em
executor/config.py porque so o subsistema de sync os le — e porque mexer neles
sem entender o ciclo de varredura e a forma mais rapida de por o disco em 100%.
"""
import fnmatch
import json
import logging
from pathlib import Path

from executor._ambiente import ler_int
from executor.utils import ocultar_no_windows

logger = logging.getLogger("executor.sync")

_CONFIG_FILE = ".atlans-sync-config.json"


# Os parametros abaixo passam pela mesma leitura tolerante do resto do
# executor (executor/_ambiente.py::ler_int): valor fora de faixa e erro de
# digitacao, nao intencao — `SYNC_CONCURRENCY=0` deixaria a pasta sem nenhum
# upload e o sintoma ("nada sobe") nao apontaria para o .env.

# Transferencias simultaneas por pasta (upload ou download). O teto e baixo de
# proposito: em link de campo, concorrencia alta piora o tempo total e ainda
# arrisca estourar o timeout de 300s do PUT/GET.
SYNC_CONCURRENCY: int = ler_int("EXECUTOR_SYNC_CONCURRENCY", 3, 1, 16)

# Piso de tempo entre dois ciclos disparados pelo WATCHER. Sem ele, copiar um
# arquivo grande para a pasta fazia o executor varrer+hashear tudo a cada ~2s,
# em ciclos encostados, disputando I/O com a propria copia.
SYNC_MIN_CYCLE: int = ler_int("EXECUTOR_SYNC_MIN_CYCLE", 5, 0, 3600)

# Debounce de CICLO (nao de caminho): depois de acordar, o ciclo so comeca
# quando a pasta ficar este tanto de tempo sem nenhum evento novo — e a
# "estabilizacao" do arquivo que esta sendo copiado.
SYNC_QUIET_PERIOD: int = ler_int("EXECUTOR_SYNC_QUIET_PERIOD", 3, 0, 600)

# Teto da espera por estabilizacao: uma copia de horas nao pode adiar o ciclo
# para sempre.
SYNC_MAX_QUIET_WAIT: int = ler_int("EXECUTOR_SYNC_MAX_QUIET_WAIT", 120, 1, 3600)

# Rede de seguranca do atalho (size, mtime) do diff: de tempos em tempos o ciclo
# rehasheia tudo, para pegar a reescrita rara que preserva o mtime (copia com
# `-p`, por exemplo).
SYNC_FULL_HASH_INTERVAL: int = ler_int("EXECUTOR_SYNC_FULL_HASH_INTERVAL", 3600, 60, 86400)

# Threads do pool de trabalho PESADO do GeoSync — zip, validate, metadados,
# MD5, varredura (ver executor/sync/pool.py). Pequeno de proposito: e trabalho
# CPU-bound e nao pode competir com os nos dos workflows.
SYNC_THREADS: int = ler_int("EXECUTOR_SYNC_THREADS", 2, 1, 8)

# Threads do pool de I/O de BYTES das transferencias (chunks do PUT/GET). E
# separado do de cima porque as duas cargas nao se parecem: cada chamada aqui e
# curta (1 MB de read/write) mas precisa de vazao continua, e no mesmo pool de 2
# threads um `_write_zip` de bundle de GB segurava TODAS as transferencias em voo
# por minutos — socket parado o tempo todo, o que convida o MinIO a derrubar a
# conexao por ociosidade e joga o upload na fila de retry.
SYNC_IO_THREADS: int = ler_int("EXECUTOR_SYNC_IO_THREADS", 8, 1, 32)

# Intervalo minimo entre gravacoes do manifesto durante um lote de uploads.
SYNC_FLUSH_INTERVAL: int = ler_int("EXECUTOR_SYNC_FLUSH_INTERVAL", 5, 0, 300)


class SyncConfig:
    """
    Gerencia filtros de sync seletivo, lidos do arquivo local
    .atlans-sync-config.json da pasta sincronizada.

    Havia uma segunda fonte, a config remota (GET /drive/executor-sync-config),
    mas nada no servidor a escrevia: o GET devolvia sempre o padrão. A rota e a
    busca saíram; executores antigos que ainda a chamam recebem um erro HTTP
    (405: o caminho casa com o `DELETE /drive/{id_hash}`) e seguem com a
    config local, como já faziam quando a busca falhava.
    """

    def __init__(self, sync_dir: str | Path):
        self.sync_dir = Path(sync_dir)

        # Filtros
        self.include_patterns: list[str] = []   # ex: ["*.geojson", "parcelas_*"]
        self.exclude_patterns: list[str] = []   # ex: ["temp_*", "backup_*"]
        self.enabled_remote_ids: set[str] | None = None  # None = todos

        self._load_local()

    def _load_local(self):
        config_path = self.sync_dir / _CONFIG_FILE
        if not config_path.exists():
            return

        # Dotfile de config na pasta do usuario: no Windows o ponto nao esconde,
        # entao garantimos o atributo oculto sempre que o encontramos. Nao somos
        # nos que o criamos (vem do usuario ou do push remoto), por isso e aqui,
        # na leitura, e nao numa gravacao.
        ocultar_no_windows(config_path)

        try:
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)
            self.include_patterns = data.get("include", [])
            self.exclude_patterns = data.get("exclude", [])
            ids = data.get("enabled_ids")
            self.enabled_remote_ids = set(ids) if ids is not None else None
            logger.info("SyncConfig carregado: include=%s, exclude=%s, ids=%s",
                        self.include_patterns, self.exclude_patterns,
                        len(self.enabled_remote_ids) if self.enabled_remote_ids is not None else "todos")
        except Exception as exc:
            logger.warning("Erro ao ler %s: %s", _CONFIG_FILE, exc)

    def should_download(self, original_name: str, id_hash: str) -> bool:
        """Verifica se um arquivo remoto deve ser baixado."""
        # Se IDs especificos configurados, verificar
        if self.enabled_remote_ids is not None:
            if id_hash not in self.enabled_remote_ids:
                return False

        # Se exclude patterns, verificar
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(original_name, pattern):
                return False

        # Se include patterns, deve casar com pelo menos um
        if self.include_patterns:
            return any(fnmatch.fnmatch(original_name, p) for p in self.include_patterns)

        return True
