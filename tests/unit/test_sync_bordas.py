# tests/unit/test_sync_bordas.py
"""
Bordas do GeoSync expostas pela auditoria das otimizacoes de desempenho.

Todas as invariantes aqui tem o mesmo desfecho quando quebradas: ARQUIVO DO
USUARIO NAO SINCRONIZADO — sem erro nenhum no log.

  A21 — o marcador da varredura completa (rede de seguranca do atalho de
        size/mtime) so pode ser carimbado DEPOIS que ela roda, e um arquivo
        ilegivel nao pode derrubar o ciclo inteiro.
  A22 — em FS de mtime grosseiro (FAT32/exFAT de pendrive), o par (size, mtime)
        so testemunha "nao mudou" se tiver sido colhido com o mtime ja fechado.
  A45 — o backoff tem de alcancar o item que foi executado, e a fila nao pode
        acumular itens equivalentes.
  A46 — relogio que anda para tras nao pode congelar um item para sempre.
  A47 — o I/O de bytes das transferencias nao espera o pool de trabalho pesado.
  A57 — gravacao de manifesto que falha mantem o manifesto sujo.
"""
import asyncio
import os
import threading
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

LOCAL_URL = "ws://localhost:8000"  # is_local_server → sem exigir cert mTLS


@pytest.fixture(autouse=True)
def _pools_limpos():
    """Os pools do GeoSync sao globais do processo: derruba-os entre testes."""
    from executor.sync import pool

    def _derrubar():
        for p in (pool._pool, pool._pool_io):
            if p is not None:
                p.shutdown(wait=False)
        pool._pool = pool._pool_io = None

    _derrubar()
    yield
    _derrubar()


def _manager(tmp_path: Path):
    from executor.sync.manager import SyncManager

    sm = SyncManager(sync_dir=str(tmp_path), workspace_id="ws-1", server_url=LOCAL_URL,
                     executor_id="ag-1", interval=1)
    sm.sync_mode = "upload"
    sm.uploader = MagicMock()
    sm.uploader.delete = AsyncMock(return_value=True)
    sm.uploader.upload = AsyncMock(return_value=None)
    sm.downloader = MagicMock()
    sm.downloader.list_remote = AsyncMock(return_value=[])
    sm.trigger._triggers = []
    return sm


def _manifesto_do_disco(scanner, stat_at=None) -> dict:
    """Manifesto sintetico que descreve a pasta como ela esta agora."""
    manifesto = {}
    for nome, ds in scanner.scan().items():
        arquivos = {}
        for fname, finfo in ds.files.items():
            entrada = finfo.to_dict()
            if stat_at is not None:
                entrada["stat_at"] = stat_at(finfo)
            arquivos[fname] = entrada
        manifesto[nome] = {"type": ds.type, "files": arquivos, "status": "synced"}
    return manifesto


# ── A21 — a rede de seguranca nao pode ser consumida sem ter rodado ───────────

def test_a21_marcador_da_varredura_completa_so_e_carimbado_se_ela_concluir(tmp_path):
    """O diff com force_hash abre TODOS os arquivos da pasta. Se ele levantar,
    o ciclo morre — e marcando antes, a passada completa ficava dada como feita
    e so voltaria 1h depois, deixando de subir a reescrita que preserva mtime."""
    sm = _manager(tmp_path)
    (tmp_path / "parcelas.geojson").write_text('{"a":1}')

    def _explode(*a, **kw):
        raise OSError("arquivo sumiu durante a varredura")

    sm.scanner.diff = _explode
    with pytest.raises(OSError):
        asyncio.run(sm._local_to_remote())

    assert sm._ultimo_hash_completo is None, \
        "a varredura completa foi consumida sem nunca ter acontecido"

    # Ciclo que conclui: agora sim o marcador vale.
    sm.scanner.diff = lambda *a, **kw: ([], [], [])
    asyncio.run(sm._local_to_remote())
    assert sm._ultimo_hash_completo is not None


def test_a21_arquivo_ilegivel_nao_derruba_o_diff_da_pasta(tmp_path, monkeypatch):
    """Um temporario que some (QGIS/ArcGIS criam e removem o tempo todo) levava
    OSError para fora do diff e matava a deteccao de mudanca da PASTA inteira."""
    from executor.sync import scanner as scanner_mod
    from executor.sync.scanner import DatasetScanner

    (tmp_path / "some.geojson").write_text('{"a":1}')
    (tmp_path / "fica.geojson").write_text('{"a":1}')
    scanner = DatasetScanner(str(tmp_path))
    manifesto = _manifesto_do_disco(scanner)

    # Os dois mudam de conteudo; so um deles fica ilegivel na hora do hash.
    for nome in ("some", "fica"):
        alvo = tmp_path / f"{nome}.geojson"
        alvo.write_text('{"a":2,"b":3}')

    real = scanner_mod._compute_md5
    monkeypatch.setattr(scanner_mod, "_compute_md5",
                        lambda p: (_ for _ in ()).throw(FileNotFoundError(p))
                        if p.name == "some.geojson" else real(p))

    _, modificados, _ = scanner.diff(scanner.scan(), manifesto, force_hash=True)
    assert modificados == ["fica"], "um arquivo ilegivel cegou a pasta inteira"


# ── A22 — testemunho (size, mtime) em FS de mtime grosseiro ──────────────────

def test_a22_edicao_no_mesmo_balde_de_mtime_do_pendrive_e_detectada(tmp_path):
    """FAT32/exFAT gravam mtime em passos de 2s. Editar um atributo no QGIS
    reescreve so o .dbf, que tem registro de largura fixa: mesmo tamanho. Se a
    gravacao cair no mesmo balde do stat que gerou o manifesto, size e mtime
    ficam identicos e o atalho conclui 'inalterado' — o arquivo nunca sobe."""
    from executor.sync.scanner import DatasetScanner

    alvo = tmp_path / "parcelas.geojson"
    alvo.write_text('{"a":1}')
    t = float(int(time.time()) - 600)     # mtime INTEIRO, como num FAT32
    os.utime(alvo, (t, t))

    scanner = DatasetScanner(str(tmp_path))
    # Testemunho colhido meio segundo depois do mtime: dentro do balde de 2s.
    manifesto = _manifesto_do_disco(scanner, stat_at=lambda f: t + 0.5)

    alvo.write_text('{"a":2}')            # mesmo tamanho...
    os.utime(alvo, (t, t))                # ...e mesmo mtime (balde de 2s)

    _, modificados, _ = scanner.diff(scanner.scan(), manifesto)
    assert modificados == ["parcelas"], "edicao invisivel para (size, mtime) nao subiu"


def test_a22_testemunho_maduro_preserva_o_atalho(tmp_path, monkeypatch):
    """O ganho continua de pe: com o mtime ja fechado quando o stat foi tirado,
    nenhuma gravacao posterior cabe no mesmo balde — e o ciclo nao abre nada."""
    from executor.sync import scanner as scanner_mod
    from executor.sync.scanner import DatasetScanner

    alvo = tmp_path / "parcelas.geojson"
    alvo.write_text('{"a":1}')
    t = float(int(time.time()) - 600)
    os.utime(alvo, (t, t))

    scanner = DatasetScanner(str(tmp_path))
    manifesto = _manifesto_do_disco(scanner, stat_at=lambda f: t + 30)

    monkeypatch.setattr(scanner_mod, "_compute_md5",
                        lambda p: pytest.fail(f"o diff releu {p.name} sem necessidade"))
    assert scanner.diff(scanner.scan(), manifesto) == ([], [], [])


def test_a22_testemunho_e_reancorado_apos_o_hash_confirmar(tmp_path, monkeypatch):
    """Entrada sem `stat_at` (manifesto de versao anterior) ou colhida cedo
    demais precisa se curar: senao o dataset e rehasheado a cada ciclo para
    sempre — nada muda, nada sobe, e portanto ninguem regrava o manifesto."""
    from executor.sync import scanner as scanner_mod
    from executor.sync.scanner import DatasetScanner

    alvo = tmp_path / "parcelas.geojson"
    alvo.write_text('{"a":1}')
    t = float(int(time.time()) - 600)
    os.utime(alvo, (t, t))

    scanner = DatasetScanner(str(tmp_path))
    manifesto = _manifesto_do_disco(scanner)
    del manifesto["parcelas"]["files"]["parcelas.geojson"]["stat_at"]

    leituras = {"n": 0}
    real = scanner_mod._compute_md5
    monkeypatch.setattr(scanner_mod, "_compute_md5",
                        lambda p: (leituras.__setitem__("n", leituras["n"] + 1), real(p))[1])

    assert scanner.diff(scanner.scan(), manifesto) == ([], [], [])
    assert leituras["n"] == 1, "entrada sem testemunho tem de cair no hash"
    assert scanner.diff(scanner.scan(), manifesto) == ([], [], [])
    assert leituras["n"] == 1, "o testemunho nao foi reancorado: rehashearia para sempre"


# ── A45 — backoff tem de alcancar o item executado ───────────────────────────

def _manifesto(tmp_path):
    from executor.sync.manifest import SyncManifest
    return SyncManifest(str(tmp_path), "ws-1", "ag-1")


def test_a45_todos_os_itens_executados_recebem_agendamento(tmp_path):
    """Casando so pelo nome e dando break, o backoff ia sempre para o PRIMEIRO
    homonimo: os demais retentavam a cada ciclo, cada tentativa pagando
    validate + metadados + MD5 do dataset inteiro."""
    from executor.sync.queue import SyncQueue

    m = _manifesto(tmp_path)
    m.enqueue("upload", "parcelas")
    # Fila herdada de antes da deduplicacao — o cenario que a auditoria descreve.
    m._data["pending_queue"].append(dict(m._data["pending_queue"][0]))

    async def _falha(item):
        return False

    asyncio.run(SyncQueue(m, _falha).process_pending())

    agora = time.time()
    assert len(m.pending_items()) == 2
    for item in m.pending_items():
        assert item["retries"] == 1
        assert item["next_attempt_at"] > agora, "item executado ficou sem backoff"


def test_a45_enfileirar_de_novo_nao_duplica_nem_zera_o_backoff(tmp_path):
    """Cada falha de upload deixa a entrada sem 'files', o diff do ciclo
    seguinte reenfileira, e a fila crescia um item por ciclo."""
    m = _manifesto(tmp_path)
    m.enqueue("upload", "parcelas")
    m.pending_items()[0]["next_attempt_at"] = 12345.0
    m.pending_items()[0]["retries"] = 3

    m.enqueue("upload", "parcelas")

    assert len(m.pending_items()) == 1
    assert m.pending_items()[0]["retries"] == 3
    assert m.pending_items()[0]["next_attempt_at"] == 12345.0

    m.enqueue("delete", "parcelas", {"remote_id_hash": "abc"})
    assert len(m.pending_items()) == 2, "acoes diferentes sao operacoes diferentes"


# ── A46 — relogio de parede nao pode congelar a fila ─────────────────────────

def test_a46_relogio_que_volta_no_tempo_nao_congela_o_descarte(tmp_path):
    """Notebook de campo que boota adiantado e depois e corrigido pelo NTP: o
    agendamento gravado no manifesto vira um futuro que nunca chega. Para
    'discard' nao ha outro motor — o arquivo que o Drive mandou apagar ficaria
    no disco do tecnico para sempre, sem nenhum erro no log."""
    from executor.sync.queue import SyncQueue

    m = _manifesto(tmp_path)
    m.enqueue("discard", "parcelas")
    m.pending_items()[0]["next_attempt_at"] = time.time() + 86400  # relogio adiantado

    executados = []

    async def _executa(item):
        executados.append(item["dataset"])
        return True

    asyncio.run(SyncQueue(m, _executa).process_pending())
    assert executados == ["parcelas"]


def test_a46_agendamento_legitimo_continua_sendo_respeitado(tmp_path):
    """O saneamento nao pode virar 'ignore o backoff'."""
    from executor.sync.queue import SyncQueue, _MAX_BACKOFF

    m = _manifesto(tmp_path)
    m.enqueue("upload", "parcelas")
    m.pending_items()[0]["next_attempt_at"] = time.time() + _MAX_BACKOFF - 5

    async def _nunca(item):
        raise AssertionError("item ainda nao venceu")

    asyncio.run(SyncQueue(m, _nunca).process_pending())


# ── A47 — transferencias nao esperam o pool de trabalho pesado ───────────────

def test_a47_io_de_transferencia_tem_pool_proprio():
    """Com tudo no mesmo pool de 2 threads, dois `_write_zip`/`extract_metadata`
    pesados paravam TODAS as transferencias em voo por minutos: o socket do
    PUT/GET ficava sem dados e o MinIO derrubava a conexao por ociosidade."""
    from executor.sync import pool
    from executor.sync.sync_config import SYNC_THREADS

    async def cenario():
        travar = threading.Event()
        pesadas = [asyncio.create_task(pool.em_thread(travar.wait, 10))
                   for _ in range(SYNC_THREADS)]
        await asyncio.sleep(0.2)  # todas as threads pesadas ocupadas
        try:
            assert await asyncio.wait_for(pool.em_thread_io(lambda: "ok"), timeout=5) == "ok"
        finally:
            travar.set()
            await asyncio.gather(*pesadas)

    asyncio.run(cenario())


# ── A57 — gravacao que falha mantem o manifesto sujo ─────────────────────────

def test_a57_flush_que_falha_nao_da_o_estado_como_salvo(tmp_path):
    """Disco cheio: o estado de N datasets recem-sincronizados ficava so em
    memoria com o manifesto marcado como limpo. Um kill nessa janela re-enviava
    tudo e deixava copias orfas no Drive com o mesmo original_name."""
    m = _manifesto(tmp_path)
    m.set_dataset("parcelas", {"type": "geojson"})

    m._escrever = lambda conteudo: False          # OSError engolido la dentro
    asyncio.run(m.flush())
    assert m._sujo, "manifesto dado como salvo sem ter chegado ao disco"

    gravados = []
    m._escrever = lambda conteudo: (gravados.append(conteudo), True)[1]
    asyncio.run(m.flush())
    assert gravados and "parcelas" in gravados[0]
    assert not m._sujo


def test_a57_mutacao_durante_a_gravacao_continua_pendente(tmp_path):
    """A gravacao roda fora do loop: o que muda no meio dela nao entrou no
    snapshot e nao pode ser dado como salvo."""
    m = _manifesto(tmp_path)
    m.set_dataset("a", {"type": "geojson"})

    liberar = threading.Event()

    def _escrever_lento(conteudo):
        liberar.wait(5)
        return True

    m._escrever = _escrever_lento

    async def cenario():
        tarefa = asyncio.create_task(m.flush())
        await asyncio.sleep(0.2)              # a gravacao ja comecou
        m.set_dataset("b", {"type": "geojson"})
        liberar.set()
        await tarefa

    asyncio.run(cenario())
    assert m._sujo, "a mutacao feita durante a gravacao foi dada como salva"
