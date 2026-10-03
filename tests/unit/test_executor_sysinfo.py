# tests/unit/test_executor_sysinfo.py
"""
Tests for `executor/sysinfo.py` — the module had none.

All the value of this file is in the invariants that the caches introduced for
performance can silently violate, because none of them produces an error:

  * the disk figure served to the panel, the desktop and `capacity` must be
    either recent or explicitly UNKNOWN — never a value from hours ago passing
    as a current reading (it is what decides the "Disco quase cheio" (disk
    almost full) alert, the only protection for a local-locality artifact);
  * a hung collection (NFS `hard`, stuck FUSE) must not block the caller, nor
    lock up every future attempt, nor leak a thread per tick;
  * a container's RAM/CPU limit CHANGES in flight (`docker update`, k8s
    in-place pod resize) and the memo must self-correct.

Time is simulated by touching the module's monotonic markers instead of
faking `time.monotonic`: the test uses real threads, and swapping the global
clock would break `threading` itself.
"""
import threading
import time

import pytest

from executor import sysinfo


GB = 1024 ** 3


class _UsoDeDisco:
    def __init__(self, livre_gb: float, total_gb: float) -> None:
        self.free = int(livre_gb * GB)
        self.total = int(total_gb * GB)
        self.used = self.total - self.free


class PsutilFalso:
    """Only what `_coletar_disco` uses. `bloqueio` simulates the hung mount."""

    def __init__(self, livre_gb: float = 100.0, total_gb: float = 500.0,
                 bloqueio: threading.Event | None = None) -> None:
        self.livre_gb = livre_gb
        self.total_gb = total_gb
        self.bloqueio = bloqueio
        self.chamadas = 0

    def disk_usage(self, path):
        self.chamadas += 1
        if self.bloqueio is not None:
            # An NFS `hard` mount that stopped responding does not return an error: it
            # simply never comes back.
            self.bloqueio.wait()
        return _UsoDeDisco(self.livre_gb, self.total_gb)


def _threads_de_disco() -> list[threading.Thread]:
    return [t for t in threading.enumerate() if t.name == "sysinfo-disco"]


def _esperar_coleta(timeout: float = 5.0) -> None:
    """Espera as threads `sysinfo-disco` pousarem."""
    for t in _threads_de_disco():
        t.join(timeout)


@pytest.fixture(autouse=True)
def _caches_limpos():
    """Isolates the module's globals between tests — see `_resetar_caches`."""
    sysinfo._resetar_caches()
    yield
    # No hung thread may survive the test: it would touch the globals in the
    # middle of the NEXT test.
    for t in _threads_de_disco():
        t.join(2.0)
    sysinfo._resetar_caches()


# ── Async collection and first reading ───────────────────────────────────────


def test_primeira_leitura_nao_bloqueia_e_o_valor_pousa_depois():
    fake = PsutilFalso(livre_gb=100.0)

    # The first call must not do disk I/O on the event loop: it returns
    # unknown and delegates to the thread.
    assert sysinfo._metricas_de_disco(fake) == {}
    _esperar_coleta()

    metricas = sysinfo._metricas_de_disco(fake)
    assert metricas["disk_free_gb"] == 100.0
    assert metricas["artifacts_disk_free_gb"] == 100.0


def test_leituras_seguintes_saem_do_cache_sem_novas_syscalls():
    fake = PsutilFalso(livre_gb=100.0)
    sysinfo._metricas_de_disco(fake)
    _esperar_coleta()
    chamadas = fake.chamadas

    for _ in range(20):
        assert sysinfo._metricas_de_disco(fake)["disk_free_gb"] == 100.0
    assert fake.chamadas == chamadas, "o TTL deixou de segurar as syscalls"


# ── A23: age ceiling ─────────────────────────────────────────────────────────


def test_valor_velho_vira_desconhecido_em_vez_de_passar_por_leitura_corrente(caplog):
    fake = PsutilFalso(livre_gb=100.0)
    sysinfo._metricas_de_disco(fake)
    _esperar_coleta()
    assert sysinfo._metricas_de_disco(fake)["artifacts_disk_free_gb"] == 100.0

    # The share hung right after: the in-flight collection does not come back,
    # and the last good value ages beyond the ceiling.
    agora = time.monotonic()
    sysinfo._disco_coletado_em = agora - (sysinfo.IDADE_MAXIMA_DISCO_S + 1)
    sysinfo._disco_expira = 0.0
    sysinfo._disco_em_voo = 1
    sysinfo._disco_iniciou_em = agora  # still within the deadline: nothing to fire

    with caplog.at_level("WARNING", logger="executor.sysinfo"):
        assert sysinfo._metricas_de_disco(fake) == {}
    assert any("obsoletas" in r.message for r in caplog.records), \
        "o painel passou a mentir sem nem registrar no log"

    sysinfo._disco_em_voo = 0  # teardown: there was no real thread


def test_valor_abaixo_do_teto_de_idade_continua_servindo():
    fake = PsutilFalso(livre_gb=100.0)
    sysinfo._metricas_de_disco(fake)
    _esperar_coleta()

    # Serving stale data is acceptable; what is not is serving it forever.
    sysinfo._disco_coletado_em = time.monotonic() - (sysinfo.IDADE_MAXIMA_DISCO_S - 5)
    assert sysinfo._metricas_de_disco(fake)["disk_free_gb"] == 100.0


def test_aviso_de_obsoleto_nao_se_repete_a_cada_tick(caplog):
    fake = PsutilFalso(livre_gb=100.0)
    sysinfo._metricas_de_disco(fake)
    _esperar_coleta()
    sysinfo._disco_coletado_em = time.monotonic() - (sysinfo.IDADE_MAXIMA_DISCO_S + 1)
    sysinfo._disco_em_voo = 1
    sysinfo._disco_iniciou_em = time.monotonic()

    with caplog.at_level("WARNING", logger="executor.sysinfo"):
        for _ in range(10):
            sysinfo._metricas_de_disco(fake)
    obsoletos = [r for r in caplog.records if "obsoletas" in r.message]
    assert len(obsoletos) == 1, "o aviso é avaliado a 1 Hz; não pode inundar o log"

    sysinfo._disco_em_voo = 0


# ── A23: coleta pendurada ────────────────────────────────────────────────────


def test_coleta_pendurada_nao_bloqueia_o_chamador():
    bloqueio = threading.Event()
    fake = PsutilFalso(livre_gb=100.0, bloqueio=bloqueio)
    try:
        t0 = time.monotonic()
        assert sysinfo._metricas_de_disco(fake) == {}
        assert time.monotonic() - t0 < 1.0, "o event loop esperou pelo mount pendurado"
        assert sysinfo._disco_em_voo == 1
    finally:
        bloqueio.set()
        _esperar_coleta()


def test_coleta_pendurada_nao_trava_as_tentativas_futuras_para_sempre():
    bloqueio = threading.Event()
    fake = PsutilFalso(livre_gb=100.0, bloqueio=bloqueio)
    try:
        sysinfo._metricas_de_disco(fake)
        assert sysinfo._disco_em_voo == 1

        # Within the deadline: no new thread, even with the TTL expired.
        sysinfo._disco_expira = 0.0
        sysinfo._metricas_de_disco(fake)
        assert sysinfo._disco_em_voo == 1

        # Past the deadline, the collection is considered hung and a new one is
        # allowed — without this, `_disco_em_voo` would be a permanent lock and
        # the frozen value would never be replaced again.
        sysinfo._disco_iniciou_em = time.monotonic() - sysinfo.TIMEOUT_COLETA_DISCO_S - 1
        sysinfo._disco_expira = 0.0
        sysinfo._metricas_de_disco(fake)
        assert sysinfo._disco_em_voo == 2
    finally:
        bloqueio.set()
        _esperar_coleta()


def test_mount_pendurado_nao_vaza_uma_thread_por_tick():
    bloqueio = threading.Event()
    fake = PsutilFalso(livre_gb=100.0, bloqueio=bloqueio)
    try:
        for _ in range(30):
            # The most hostile scenario possible: deadline always blown and TTL always
            # expired. Only the ceiling can hold it.
            sysinfo._disco_iniciou_em = time.monotonic() - sysinfo.TIMEOUT_COLETA_DISCO_S - 1
            sysinfo._disco_expira = 0.0
            assert sysinfo._metricas_de_disco(fake) == {}
        assert sysinfo._disco_em_voo == sysinfo.MAX_COLETAS_DISCO_EM_VOO
        assert len(_threads_de_disco()) <= sysinfo.MAX_COLETAS_DISCO_EM_VOO
    finally:
        bloqueio.set()
        _esperar_coleta()


def test_disparo_empurra_o_vencimento_para_nao_abrir_thread_por_tick():
    bloqueio = threading.Event()
    fake = PsutilFalso(livre_gb=100.0, bloqueio=bloqueio)
    try:
        sysinfo._metricas_de_disco(fake)
        # If the expiration were only pushed at the end of the collection, a
        # collection that never finishes would leave `_disco_expira` in the past forever.
        assert sysinfo._disco_expira >= time.monotonic() + sysinfo.TIMEOUT_COLETA_DISCO_S - 1
    finally:
        bloqueio.set()
        _esperar_coleta()


def test_falha_na_coleta_sai_no_log_e_mantem_o_valor_anterior(caplog, monkeypatch):
    fake = PsutilFalso(livre_gb=100.0)
    sysinfo._metricas_de_disco(fake)
    _esperar_coleta()

    def explode(_mod):
        raise OSError("unidade de rede sumiu")

    monkeypatch.setattr(sysinfo, "_coletar_disco", explode)
    with caplog.at_level("WARNING", logger="executor.sysinfo"):
        sysinfo._refrescar_disco(fake)

    # An inaccessible artifacts folder was completely silent (logger.debug).
    assert any("Falha ao coletar metricas de disco" in r.message for r in caplog.records)
    assert sysinfo._metricas_de_disco(fake)["disk_free_gb"] == 100.0
    assert sysinfo._disco_em_voo == 0, "a vaga precisa voltar mesmo na falha"


# ── A48: adaptive TTL near the end of the disk ───────────────────────────────


def test_ttl_longo_quando_ha_folga():
    assert sysinfo._ttl_do_valor({}) == sysinfo.TTL_DISCO_S
    assert sysinfo._ttl_do_valor(
        {"disk_free_gb": 200.0, "artifacts_disk_free_gb": 80.0}
    ) == sysinfo.TTL_DISCO_S


def test_ttl_curto_quando_o_disco_dos_artefatos_esta_apertado():
    # 3 GB free: a GIS node writing a raster consumes that in seconds, and the
    # "Disco quase cheio" (disk almost full) toast must arrive BEFORE the write fails.
    assert sysinfo._ttl_do_valor(
        {"disk_free_gb": 200.0, "artifacts_disk_free_gb": 3.0}
    ) == sysinfo.TTL_DISCO_APERTADO_S


def test_disco_apertado_encurta_o_vencimento_de_verdade():
    fake = PsutilFalso(livre_gb=3.0, total_gb=500.0)
    sysinfo._metricas_de_disco(fake)
    _esperar_coleta()

    restante = sysinfo._disco_expira - time.monotonic()
    assert restante <= sysinfo.TTL_DISCO_APERTADO_S + 0.5
    assert restante < sysinfo.TTL_DISCO_S


def test_folga_mantem_o_ttl_longo_de_verdade():
    fake = PsutilFalso(livre_gb=200.0, total_gb=500.0)
    sysinfo._metricas_de_disco(fake)
    _esperar_coleta()

    restante = sysinfo._disco_expira - time.monotonic()
    assert restante > sysinfo.TTL_DISCO_S - 5, \
        "o TTL longo é o que tira o I/O de disco do caminho de 1 Hz"


# ── A58: limites de cgroup mudam em voo ──────────────────────────────────────


def test_limite_de_ram_do_container_e_relido_apos_o_ttl(monkeypatch):
    monkeypatch.setattr(sysinfo, "_EH_LINUX", True)
    arquivos = {"/sys/fs/cgroup/memory.max": 4 * GB}
    monkeypatch.setattr(sysinfo, "_read_cgroup_value", lambda p: arquivos.get(p))

    assert sysinfo._get_cgroup_ram_total() == 4 * GB

    # `docker update --memory=16g` reescreve memory.max sem recriar o container.
    arquivos["/sys/fs/cgroup/memory.max"] = 16 * GB
    assert sysinfo._get_cgroup_ram_total() == 4 * GB, "o memo curto deve valer"

    sysinfo._cache_ram_total_em -= sysinfo.TTL_CGROUP_S + 1
    assert sysinfo._get_cgroup_ram_total() == 16 * GB, \
        "o memo permanente prendia ram_available_gb em 0.0 para sempre"


def test_ram_disponivel_acompanha_o_limite_reduzido(monkeypatch):
    monkeypatch.setattr(sysinfo, "_EH_LINUX", True)
    arquivos = {"/sys/fs/cgroup/memory.max": 4 * GB,
                "/sys/fs/cgroup/memory.current": 1 * GB}
    monkeypatch.setattr(sysinfo, "_read_cgroup_value", lambda p: arquivos.get(p))

    assert sysinfo._get_cgroup_ram_available() == 3 * GB

    # `docker update --memory=2g`: the real headroom drops to 1 GB. With a
    # permanent memo the executor would announce 3 GB that do not exist.
    arquivos["/sys/fs/cgroup/memory.max"] = 2 * GB
    sysinfo._cache_ram_total_em -= sysinfo.TTL_CGROUP_S + 1
    assert sysinfo._get_cgroup_ram_available() == 1 * GB


def test_cota_de_cpu_do_container_e_relida_apos_o_ttl(monkeypatch):
    monkeypatch.setattr(sysinfo, "_EH_LINUX", True)
    cota = {"valor": 2.0}
    monkeypatch.setattr(sysinfo, "_ler_cgroup_cpu_cores", lambda: cota["valor"])

    assert sysinfo._get_cgroup_cpu_cores() == 2.0
    cota["valor"] = 8.0  # docker update --cpus=8
    assert sysinfo._get_cgroup_cpu_cores() == 2.0

    sysinfo._cache_cpu_cores_em -= sysinfo.TTL_CGROUP_S + 1
    assert sysinfo._get_cgroup_cpu_cores() == 8.0, \
        "cpu_pct_norm ficaria normalizado pela cota antiga para sempre"


def test_o_memo_de_cgroup_evita_reler_a_cada_tick(monkeypatch):
    monkeypatch.setattr(sysinfo, "_EH_LINUX", True)
    leituras = []
    monkeypatch.setattr(sysinfo, "_read_cgroup_value",
                        lambda p: leituras.append(p) or (4 * GB))

    for _ in range(60):
        sysinfo._get_cgroup_ram_total()
    assert len(leituras) == 1, "o objetivo da otimização (cortar open() por tick) se perdeu"


def test_fora_do_linux_nao_toca_no_sysfs(monkeypatch):
    """This case IS immutable, and it is what generated FileNotFoundError every second."""
    monkeypatch.setattr(sysinfo, "_EH_LINUX", False)

    def nao_deveria(*_a, **_k):
        raise AssertionError("leu /sys/fs/cgroup fora do Linux")

    monkeypatch.setattr(sysinfo, "_read_cgroup_value", nao_deveria)
    monkeypatch.setattr(sysinfo, "_ler_cgroup_cpu_cores", nao_deveria)

    assert sysinfo._get_cgroup_ram_total() is None
    assert sysinfo._get_cgroup_cpu_cores() is None
    assert sysinfo._get_cgroup_ram_available() is None


# ── Reset hook ───────────────────────────────────────────────────────────────


def test_resetar_caches_zera_todo_o_estado(monkeypatch):
    monkeypatch.setattr(sysinfo, "_EH_LINUX", True)
    monkeypatch.setattr(sysinfo, "_read_cgroup_value", lambda p: 4 * GB)
    sysinfo._get_cgroup_ram_total()
    fake = PsutilFalso(livre_gb=100.0)
    sysinfo._metricas_de_disco(fake)
    _esperar_coleta()

    sysinfo._resetar_caches()

    assert sysinfo._disco_valor == {}
    assert sysinfo._disco_em_voo == 0
    assert sysinfo._disco_expira == 0.0
    assert sysinfo._cache_ram_total is None
    assert sysinfo._cache_ram_total_em == sysinfo._SEM_LEITURA
    assert sysinfo._cache_cpu_cores_em == sysinfo._SEM_LEITURA
