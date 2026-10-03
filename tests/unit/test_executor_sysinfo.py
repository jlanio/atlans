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


class _DiskUsage:
    def __init__(self, free_gb: float, total_gb: float) -> None:
        self.free = int(free_gb * GB)
        self.total = int(total_gb * GB)
        self.used = self.total - self.free


class FakePsutil:
    """Only what `_coletar_disco` uses. `bloqueio` simulates the hung mount."""

    def __init__(self, free_gb: float = 100.0, total_gb: float = 500.0,
                 bloqueio: threading.Event | None = None) -> None:
        self.free_gb = free_gb
        self.total_gb = total_gb
        self.bloqueio = bloqueio
        self.chamadas = 0

    def disk_usage(self, path):
        self.chamadas += 1
        if self.bloqueio is not None:
            # An NFS `hard` mount that stopped responding does not return an error: it
            # simply never comes back.
            self.bloqueio.wait()
        return _DiskUsage(self.free_gb, self.total_gb)


def _threads_de_disco() -> list[threading.Thread]:
    return [t for t in threading.enumerate() if t.name == "sysinfo-disco"]


def _wait_for_collection(timeout: float = 5.0) -> None:
    """Espera as threads `sysinfo-disco` pousarem."""
    for t in _threads_de_disco():
        t.join(timeout)


@pytest.fixture(autouse=True)
def _clean_caches():
    """Isolates the module's globals between tests — see `_resetar_caches`."""
    sysinfo._resetar_caches()
    yield
    # No hung thread may survive the test: it would touch the globals in the
    # middle of the NEXT test.
    for t in _threads_de_disco():
        t.join(2.0)
    sysinfo._resetar_caches()


# ── Async collection and first reading ───────────────────────────────────────


def test_first_read_does_not_block_and_the_value_lands_later():
    fake = FakePsutil(free_gb=100.0)

    # The first call must not do disk I/O on the event loop: it returns
    # unknown and delegates to the thread.
    assert sysinfo._disk_metrics(fake) == {}
    _wait_for_collection()

    metricas = sysinfo._disk_metrics(fake)
    assert metricas["disk_free_gb"] == 100.0
    assert metricas["artifacts_disk_free_gb"] == 100.0


def test_subsequent_reads_come_from_cache_without_new_syscalls():
    fake = FakePsutil(free_gb=100.0)
    sysinfo._disk_metrics(fake)
    _wait_for_collection()
    chamadas = fake.chamadas

    for _ in range(20):
        assert sysinfo._disk_metrics(fake)["disk_free_gb"] == 100.0
    assert fake.chamadas == chamadas, "o TTL deixou de segurar as syscalls"


# ── A23: age ceiling ─────────────────────────────────────────────────────────


def test_old_value_becomes_unknown_instead_of_passing_as_current_reading(caplog):
    fake = FakePsutil(free_gb=100.0)
    sysinfo._disk_metrics(fake)
    _wait_for_collection()
    assert sysinfo._disk_metrics(fake)["artifacts_disk_free_gb"] == 100.0

    # The share hung right after: the in-flight collection does not come back,
    # and the last good value ages beyond the ceiling.
    agora = time.monotonic()
    sysinfo._disk_collected_at = agora - (sysinfo.DISK_MAX_AGE_S + 1)
    sysinfo._disk_expires = 0.0
    sysinfo._disk_in_flight = 1
    sysinfo._disk_started_at = agora  # still within the deadline: nothing to fire

    with caplog.at_level("WARNING", logger="executor.sysinfo"):
        assert sysinfo._disk_metrics(fake) == {}
    assert any("obsoletas" in r.message for r in caplog.records), \
        "o painel passou a mentir sem nem registrar no log"

    sysinfo._disk_in_flight = 0  # teardown: there was no real thread


def test_value_below_the_age_ceiling_keeps_serving():
    fake = FakePsutil(free_gb=100.0)
    sysinfo._disk_metrics(fake)
    _wait_for_collection()

    # Serving stale data is acceptable; what is not is serving it forever.
    sysinfo._disk_collected_at = time.monotonic() - (sysinfo.DISK_MAX_AGE_S - 5)
    assert sysinfo._disk_metrics(fake)["disk_free_gb"] == 100.0


def test_stale_warning_does_not_repeat_every_tick(caplog):
    fake = FakePsutil(free_gb=100.0)
    sysinfo._disk_metrics(fake)
    _wait_for_collection()
    sysinfo._disk_collected_at = time.monotonic() - (sysinfo.DISK_MAX_AGE_S + 1)
    sysinfo._disk_in_flight = 1
    sysinfo._disk_started_at = time.monotonic()

    with caplog.at_level("WARNING", logger="executor.sysinfo"):
        for _ in range(10):
            sysinfo._disk_metrics(fake)
    stale_records = [r for r in caplog.records if "obsoletas" in r.message]
    assert len(stale_records) == 1, "o aviso é avaliado a 1 Hz; não pode inundar o log"

    sysinfo._disk_in_flight = 0


# ── A23: coleta pendurada ────────────────────────────────────────────────────


def test_hung_collection_does_not_block_the_caller():
    bloqueio = threading.Event()
    fake = FakePsutil(free_gb=100.0, bloqueio=bloqueio)
    try:
        t0 = time.monotonic()
        assert sysinfo._disk_metrics(fake) == {}
        assert time.monotonic() - t0 < 1.0, "o event loop esperou pelo mount pendurado"
        assert sysinfo._disk_in_flight == 1
    finally:
        bloqueio.set()
        _wait_for_collection()


def test_hung_collection_does_not_lock_future_attempts_forever():
    bloqueio = threading.Event()
    fake = FakePsutil(free_gb=100.0, bloqueio=bloqueio)
    try:
        sysinfo._disk_metrics(fake)
        assert sysinfo._disk_in_flight == 1

        # Within the deadline: no new thread, even with the TTL expired.
        sysinfo._disk_expires = 0.0
        sysinfo._disk_metrics(fake)
        assert sysinfo._disk_in_flight == 1

        # Past the deadline, the collection is considered hung and a new one is
        # allowed — without this, `_disk_in_flight` would be a permanent lock and
        # the frozen value would never be replaced again.
        sysinfo._disk_started_at = time.monotonic() - sysinfo.DISK_COLLECTION_TIMEOUT_S - 1
        sysinfo._disk_expires = 0.0
        sysinfo._disk_metrics(fake)
        assert sysinfo._disk_in_flight == 2
    finally:
        bloqueio.set()
        _wait_for_collection()


def test_hung_mount_does_not_leak_a_thread_per_tick():
    bloqueio = threading.Event()
    fake = FakePsutil(free_gb=100.0, bloqueio=bloqueio)
    try:
        for _ in range(30):
            # The most hostile scenario possible: deadline always blown and TTL always
            # expired. Only the ceiling can hold it.
            sysinfo._disk_started_at = time.monotonic() - sysinfo.DISK_COLLECTION_TIMEOUT_S - 1
            sysinfo._disk_expires = 0.0
            assert sysinfo._disk_metrics(fake) == {}
        assert sysinfo._disk_in_flight == sysinfo.MAX_DISK_COLLECTIONS_IN_FLIGHT
        assert len(_threads_de_disco()) <= sysinfo.MAX_DISK_COLLECTIONS_IN_FLIGHT
    finally:
        bloqueio.set()
        _wait_for_collection()


def test_trigger_pushes_the_expiry_to_avoid_a_thread_per_tick():
    bloqueio = threading.Event()
    fake = FakePsutil(free_gb=100.0, bloqueio=bloqueio)
    try:
        sysinfo._disk_metrics(fake)
        # If the expiration were only pushed at the end of the collection, a
        # collection that never finishes would leave `_disk_expires` in the past forever.
        assert sysinfo._disk_expires >= time.monotonic() + sysinfo.DISK_COLLECTION_TIMEOUT_S - 1
    finally:
        bloqueio.set()
        _wait_for_collection()


def test_collection_failure_is_logged_and_keeps_the_previous_value(caplog, monkeypatch):
    fake = FakePsutil(free_gb=100.0)
    sysinfo._disk_metrics(fake)
    _wait_for_collection()

    def explode(_mod):
        raise OSError("unidade de rede sumiu")

    monkeypatch.setattr(sysinfo, "_coletar_disco", explode)
    with caplog.at_level("WARNING", logger="executor.sysinfo"):
        sysinfo._refresh_disk(fake)

    # An inaccessible artifacts folder was completely silent (logger.debug).
    assert any("Falha ao coletar metricas de disco" in r.message for r in caplog.records)
    assert sysinfo._disk_metrics(fake)["disk_free_gb"] == 100.0
    assert sysinfo._disk_in_flight == 0, "a vaga precisa voltar mesmo na falha"


# ── A48: adaptive TTL near the end of the disk ───────────────────────────────


def test_long_ttl_when_there_is_headroom():
    assert sysinfo._value_ttl({}) == sysinfo.TTL_DISCO_S
    assert sysinfo._value_ttl(
        {"disk_free_gb": 200.0, "artifacts_disk_free_gb": 80.0}
    ) == sysinfo.TTL_DISCO_S


def test_short_ttl_when_the_artifacts_disk_is_tight():
    # 3 GB free: a GIS node writing a raster consumes that in seconds, and the
    # "Disco quase cheio" (disk almost full) toast must arrive BEFORE the write fails.
    assert sysinfo._value_ttl(
        {"disk_free_gb": 200.0, "artifacts_disk_free_gb": 3.0}
    ) == sysinfo.DISK_LOW_TTL_S


def test_tight_disk_really_shortens_the_expiry():
    fake = FakePsutil(free_gb=3.0, total_gb=500.0)
    sysinfo._disk_metrics(fake)
    _wait_for_collection()

    restante = sysinfo._disk_expires - time.monotonic()
    assert restante <= sysinfo.DISK_LOW_TTL_S + 0.5
    assert restante < sysinfo.TTL_DISCO_S


def test_headroom_really_keeps_the_long_ttl():
    fake = FakePsutil(free_gb=200.0, total_gb=500.0)
    sysinfo._disk_metrics(fake)
    _wait_for_collection()

    restante = sysinfo._disk_expires - time.monotonic()
    assert restante > sysinfo.TTL_DISCO_S - 5, \
        "o TTL longo é o que tira o I/O de disco do caminho de 1 Hz"


# ── A58: limites de cgroup mudam em voo ──────────────────────────────────────


def test_container_ram_limit_is_reread_after_the_ttl(monkeypatch):
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


def test_available_ram_follows_the_reduced_limit(monkeypatch):
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


def test_container_cpu_quota_is_reread_after_the_ttl(monkeypatch):
    monkeypatch.setattr(sysinfo, "_EH_LINUX", True)
    cota = {"valor": 2.0}
    monkeypatch.setattr(sysinfo, "_ler_cgroup_cpu_cores", lambda: cota["valor"])

    assert sysinfo._get_cgroup_cpu_cores() == 2.0
    cota["valor"] = 8.0  # docker update --cpus=8
    assert sysinfo._get_cgroup_cpu_cores() == 2.0

    sysinfo._cached_cpu_cores_at -= sysinfo.TTL_CGROUP_S + 1
    assert sysinfo._get_cgroup_cpu_cores() == 8.0, \
        "cpu_pct_norm ficaria normalizado pela cota antiga para sempre"


def test_cgroup_memo_avoids_rereading_every_tick(monkeypatch):
    monkeypatch.setattr(sysinfo, "_EH_LINUX", True)
    leituras = []
    monkeypatch.setattr(sysinfo, "_read_cgroup_value",
                        lambda p: leituras.append(p) or (4 * GB))

    for _ in range(60):
        sysinfo._get_cgroup_ram_total()
    assert len(leituras) == 1, "o objetivo da otimização (cortar open() por tick) se perdeu"


def test_outside_linux_does_not_touch_sysfs(monkeypatch):
    """This case IS immutable, and it is what generated FileNotFoundError every second."""
    monkeypatch.setattr(sysinfo, "_EH_LINUX", False)

    def should_not_happen(*_a, **_k):
        raise AssertionError("leu /sys/fs/cgroup fora do Linux")

    monkeypatch.setattr(sysinfo, "_read_cgroup_value", should_not_happen)
    monkeypatch.setattr(sysinfo, "_ler_cgroup_cpu_cores", should_not_happen)

    assert sysinfo._get_cgroup_ram_total() is None
    assert sysinfo._get_cgroup_cpu_cores() is None
    assert sysinfo._get_cgroup_ram_available() is None


# ── Reset hook ───────────────────────────────────────────────────────────────


def test_reset_caches_clears_all_state(monkeypatch):
    monkeypatch.setattr(sysinfo, "_EH_LINUX", True)
    monkeypatch.setattr(sysinfo, "_read_cgroup_value", lambda p: 4 * GB)
    sysinfo._get_cgroup_ram_total()
    fake = FakePsutil(free_gb=100.0)
    sysinfo._disk_metrics(fake)
    _wait_for_collection()

    sysinfo._resetar_caches()

    assert sysinfo._disk_value == {}
    assert sysinfo._disk_in_flight == 0
    assert sysinfo._disk_expires == 0.0
    assert sysinfo._cache_ram_total is None
    assert sysinfo._cache_ram_total_em == sysinfo._NEVER_READ
    assert sysinfo._cached_cpu_cores_at == sysinfo._NEVER_READ
