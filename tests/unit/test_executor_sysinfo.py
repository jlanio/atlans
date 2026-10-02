# tests/unit/test_executor_sysinfo.py
"""
Testes de `executor/sysinfo.py` — o módulo não tinha nenhum.

Todo o valor deste arquivo está nas invariantes que os caches introduzidos por
desempenho podem violar em silêncio, porque nenhuma delas produz erro:

  * o número de disco servido ao painel, ao desktop e ao `capacity` precisa ser
    ou recente ou explicitamente DESCONHECIDO — nunca um valor de horas atrás
    passando por leitura corrente (é ele que decide o alerta "Disco quase
    cheio", a única proteção de um artefato de localidade local);
  * uma coleta pendurada (NFS `hard`, FUSE travado) não pode bloquear o
    chamador, nem travar toda tentativa futura, nem vazar uma thread por tick;
  * o limite de RAM/CPU de um container MUDA em voo (`docker update`, in-place
    pod resize do k8s) e o memo precisa se autocorrigir.

O tempo é simulado mexendo nos marcadores monotônicos do módulo em vez de
falsear `time.monotonic`: o teste usa threads de verdade, e trocar o relógio
global quebraria o próprio `threading`.
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
    """Só o que `_coletar_disco` usa. `bloqueio` simula o mount pendurado."""

    def __init__(self, livre_gb: float = 100.0, total_gb: float = 500.0,
                 bloqueio: threading.Event | None = None) -> None:
        self.livre_gb = livre_gb
        self.total_gb = total_gb
        self.bloqueio = bloqueio
        self.chamadas = 0

    def disk_usage(self, path):
        self.chamadas += 1
        if self.bloqueio is not None:
            # Um NFS `hard` mount que parou de responder não devolve erro: ele
            # simplesmente não volta.
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
    """Isola os globais do módulo entre testes — ver `_resetar_caches`."""
    sysinfo._resetar_caches()
    yield
    # Nenhuma thread pendurada pode sobreviver ao teste: ela mexeria nos globais
    # no meio do teste SEGUINTE.
    for t in _threads_de_disco():
        t.join(2.0)
    sysinfo._resetar_caches()


# ── Coleta assíncrona e primeira leitura ─────────────────────────────────────


def test_primeira_leitura_nao_bloqueia_e_o_valor_pousa_depois():
    fake = PsutilFalso(livre_gb=100.0)

    # A primeira chamada não pode fazer I/O de disco no event loop: devolve
    # desconhecido e delega para a thread.
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


# ── A23: teto de idade ───────────────────────────────────────────────────────


def test_valor_velho_vira_desconhecido_em_vez_de_passar_por_leitura_corrente(caplog):
    fake = PsutilFalso(livre_gb=100.0)
    sysinfo._metricas_de_disco(fake)
    _esperar_coleta()
    assert sysinfo._metricas_de_disco(fake)["artifacts_disk_free_gb"] == 100.0

    # O share pendurou logo depois: a coleta em voo não volta, e o último valor
    # bom envelhece além do teto.
    agora = time.monotonic()
    sysinfo._disco_coletado_em = agora - (sysinfo.IDADE_MAXIMA_DISCO_S + 1)
    sysinfo._disco_expira = 0.0
    sysinfo._disco_em_voo = 1
    sysinfo._disco_iniciou_em = agora  # ainda dentro do prazo: nada a disparar

    with caplog.at_level("WARNING", logger="executor.sysinfo"):
        assert sysinfo._metricas_de_disco(fake) == {}
    assert any("obsoletas" in r.message for r in caplog.records), \
        "o painel passou a mentir sem nem registrar no log"

    sysinfo._disco_em_voo = 0  # teardown: não havia thread de verdade


def test_valor_abaixo_do_teto_de_idade_continua_servindo():
    fake = PsutilFalso(livre_gb=100.0)
    sysinfo._metricas_de_disco(fake)
    _esperar_coleta()

    # Servir dado velho é aceitável; o que não pode é servi-lo para sempre.
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

        # Dentro do prazo: nenhuma thread nova, mesmo com o TTL vencido.
        sysinfo._disco_expira = 0.0
        sysinfo._metricas_de_disco(fake)
        assert sysinfo._disco_em_voo == 1

        # Passado o prazo, a coleta é dada por pendurada e uma nova é permitida
        # — sem isto, `_disco_em_voo` seria um cadeado permanente e o valor
        # congelado nunca mais seria substituído.
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
            # Cenário mais hostil possível: prazo sempre estourado e TTL sempre
            # vencido. Só o teto pode segurar.
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
        # Se o vencimento só fosse empurrado no fim da coleta, uma coleta que
        # nunca termina deixaria `_disco_expira` no passado para sempre.
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

    # Uma pasta de artefatos inacessível era totalmente silenciosa (logger.debug).
    assert any("Falha ao coletar metricas de disco" in r.message for r in caplog.records)
    assert sysinfo._metricas_de_disco(fake)["disk_free_gb"] == 100.0
    assert sysinfo._disco_em_voo == 0, "a vaga precisa voltar mesmo na falha"


# ── A48: TTL adaptativo perto do fim do disco ────────────────────────────────


def test_ttl_longo_quando_ha_folga():
    assert sysinfo._ttl_do_valor({}) == sysinfo.TTL_DISCO_S
    assert sysinfo._ttl_do_valor(
        {"disk_free_gb": 200.0, "artifacts_disk_free_gb": 80.0}
    ) == sysinfo.TTL_DISCO_S


def test_ttl_curto_quando_o_disco_dos_artefatos_esta_apertado():
    # 3 GB livres: um nó GIS gravando um raster consome isso em segundos, e o
    # toast "Disco quase cheio" precisa chegar ANTES da falha de gravação.
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

    # `docker update --memory=2g`: a folga real cai para 1 GB. Com o memo
    # permanente o executor anunciaria 3 GB que não existem.
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
    """Este caso SIM é imutável, e é o que gerava FileNotFoundError por segundo."""
    monkeypatch.setattr(sysinfo, "_EH_LINUX", False)

    def nao_deveria(*_a, **_k):
        raise AssertionError("leu /sys/fs/cgroup fora do Linux")

    monkeypatch.setattr(sysinfo, "_read_cgroup_value", nao_deveria)
    monkeypatch.setattr(sysinfo, "_ler_cgroup_cpu_cores", nao_deveria)

    assert sysinfo._get_cgroup_ram_total() is None
    assert sysinfo._get_cgroup_cpu_cores() is None
    assert sysinfo._get_cgroup_ram_available() is None


# ── Hook de reset ────────────────────────────────────────────────────────────


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
