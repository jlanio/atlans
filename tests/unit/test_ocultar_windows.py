# tests/unit/test_ocultar_windows.py
"""Atributo OCULTO do Windows nos arquivos internos do executor.

Os arquivos que o executor grava na pasta do usuario ja nascem com ponto no
inicio do nome (`.atlans-sync.json`, `.executor_results.sqlite`,
`.atlans-trash/`), o que basta para escondê-los no Linux e no macOS. O Explorer
do Windows ignora essa convencao: la eles apareceriam no meio dos dados do
usuario, convidando ao apagamento acidental — apagar o manifesto re-sincroniza a
pasta inteira e apagar o outbox perde resultados de jobs. Dai o
`ocultar_no_windows`.

O CI roda em Linux, entao a chamada real ao kernel32 e simulada. O que estes
testes protegem e a LOGICA (quando e com quais bits chamamos SetFileAttributesW)
e o contrato de nunca levantar — alem da FIACAO nos dois pontos que o usuario
citou: o manifesto e os arquivos SQLite.
"""
import asyncio
import types

import pytest

from executor import utils

FILE_ATTRIBUTE_HIDDEN = 0x02
FILE_ATTRIBUTE_ARCHIVE = 0x20


def _simular_windows(monkeypatch, get_retorno, registro):
    """Faz `ocultar_no_windows` crer que roda no Windows, com um kernel32 falso.

    `get_retorno` e o que o GetFileAttributesW simulado devolve; cada
    SetFileAttributesW vai para `registro` como (caminho, attrs).
    """
    import ctypes

    def _get(_p):
        return get_retorno

    def _set(p, attrs):
        registro.append((p, attrs))
        return 1

    monkeypatch.setattr(utils.os, "name", "nt")
    monkeypatch.setattr(
        ctypes, "windll",
        types.SimpleNamespace(kernel32=types.SimpleNamespace(
            GetFileAttributesW=_get, SetFileAttributesW=_set,
            GetLastError=lambda: 0,  # usado pelo log de diagnostico do helper
        )),
        raising=False,  # `windll` nao existe em Linux; criamos o atributo.
    )


# ── No-op fora do Windows ──────────────────────────────────────────────────────

def test_noop_fora_do_windows_nao_toca_no_kernel32(monkeypatch, tmp_path):
    """Em Linux/macOS o ponto ja esconde; o guard os.name deve sair ANTES de
    qualquer chamada ao kernel32.

    O teste antigo so checava `is None` — mas o helper engole AttributeError,
    entao passava mesmo se o guard fosse removido. Aqui injetamos um kernel32
    falso que REGISTRA qualquer chamada: se o guard sumir, `tocado` fica
    preenchido e o teste quebra.
    """
    import ctypes
    tocado = []

    def _registra(*a):
        tocado.append(a)
        return 0x20

    monkeypatch.setattr(utils.os, "name", "posix")
    monkeypatch.setattr(
        ctypes, "windll",
        types.SimpleNamespace(kernel32=types.SimpleNamespace(
            GetFileAttributesW=_registra, SetFileAttributesW=_registra,
            GetLastError=lambda: 0,
        )),
        raising=False,
    )

    f = tmp_path / ".atlans-sync.json"
    f.write_text("{}")
    assert utils.ocultar_no_windows(f) is None
    assert tocado == []   # o short-circuit de os.name impediu qualquer syscall


def test_nao_levanta_em_caminho_inexistente(monkeypatch):
    monkeypatch.setattr(utils.os, "name", "posix")
    assert utils.ocultar_no_windows("/nao/existe/.atlans-sync.json") is None


# ── Logica no Windows (kernel32 simulado) ───────────────────────────────────────

def test_seta_oculto_preservando_outros_atributos(monkeypatch, tmp_path):
    registro = []
    _simular_windows(monkeypatch, FILE_ATTRIBUTE_ARCHIVE, registro)

    f = tmp_path / ".atlans-sync.json"
    f.write_text("{}")
    utils.ocultar_no_windows(f)

    assert len(registro) == 1
    caminho, attrs = registro[0]
    assert caminho == str(f)
    assert attrs & FILE_ATTRIBUTE_HIDDEN      # passou a ser oculto
    assert attrs & FILE_ATTRIBUTE_ARCHIVE     # sem apagar o que ja estava la


def test_nao_reaplica_se_ja_oculto(monkeypatch, tmp_path):
    registro = []
    _simular_windows(monkeypatch, FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_ARCHIVE, registro)

    utils.ocultar_no_windows(tmp_path / "x")
    assert registro == []                     # ja oculto → nenhum SetFileAttributes


@pytest.mark.parametrize("invalido", [-1, 0xFFFFFFFF])
def test_bail_quando_get_file_attributes_falha(monkeypatch, tmp_path, invalido):
    registro = []
    _simular_windows(monkeypatch, invalido, registro)

    utils.ocultar_no_windows(tmp_path / "sumido")
    assert registro == []                     # Get falhou → nao tenta setar nada


def test_nunca_levanta_mesmo_com_set_quebrado(monkeypatch, tmp_path):
    import ctypes

    def _get(_p):
        return FILE_ATTRIBUTE_ARCHIVE

    def _set(_p, _a):
        raise OSError("acesso negado")

    monkeypatch.setattr(utils.os, "name", "nt")
    monkeypatch.setattr(
        ctypes, "windll",
        types.SimpleNamespace(kernel32=types.SimpleNamespace(
            GetFileAttributesW=_get, SetFileAttributesW=_set,
        )),
        raising=False,
    )

    # Best-effort por contrato: jamais propaga para quem acabou de gravar.
    assert utils.ocultar_no_windows(tmp_path / "x") is None


# ── Fiacao: o manifesto e o outbox realmente chamam o helper ────────────────────

def test_manifesto_e_ocultado_apos_cada_gravacao(monkeypatch, tmp_path):
    """O `.atlans-sync.json` — o exemplo que o usuario citou — e ocultado ao salvar.

    Reaplicado a cada gravacao de proposito: no Windows o os.replace faz o
    manifesto herdar os atributos do `.tmp` visivel, entao um unico hide na
    criacao nao sobreviveria ao primeiro flush.
    """
    from executor.sync import manifest as manifest_mod

    chamadas = []
    monkeypatch.setattr(manifest_mod, "ocultar_no_windows", lambda p: chamadas.append(str(p)))

    m = manifest_mod.SyncManifest(str(tmp_path), "ws-1", "exec-1")
    m.set_dataset("parcelas", {"type": "geojson"})
    asyncio.run(m.flush())
    m.set_dataset("lotes", {"type": "geojson"})
    asyncio.run(m.flush())  # segunda gravacao tem de reaplicar

    alvo = str(tmp_path / ".atlans-sync.json")
    assert (tmp_path / ".atlans-sync.json").exists()
    assert chamadas.count(alvo) == 2


def test_outbox_sqlite_wal_e_journal_sao_ocultados(monkeypatch, tmp_path):
    """Os 'arquivos sqlite' (.sqlite, -wal, -shm, -journal) citados pelo usuario.

    -journal entra porque, quando o WAL nao engata (ex.: share de rede), o SQLite
    cai silenciosamente para rollback journal e escreve um .sqlite-journal visivel.
    """
    from executor import result_store

    db = tmp_path / ".executor_results.sqlite"
    monkeypatch.setattr(result_store, "_DB_PATH", str(db))
    monkeypatch.setattr(result_store, "_conn", None)
    monkeypatch.setattr(result_store, "_disabled", False)
    monkeypatch.setattr(result_store, "_ocultado_pos_escrita", False)

    ocultos = []
    monkeypatch.setattr(result_store, "ocultar_no_windows", lambda p: ocultos.append(p))

    try:
        # A conexao e criada lazy no primeiro put → dispara o ocultar.
        result_store.put({"job_id": "j1", "status": "success"})
        for sufixo in ("", "-wal", "-shm", "-journal"):
            assert str(db) + sufixo in ocultos
    finally:
        result_store.close()


def test_outbox_real_segue_operavel_apos_ocultar(monkeypatch, tmp_path):
    """Com o helper REAL (no-op em Linux), o db e criado, ocultado e permanece
    gravavel: valida a premissa de result_store (ocultar depois do CREATE/escrita
    nao quebra o SQLite), alem do ciclo put/count/mark_sent/load_pending."""
    from executor import result_store

    db = tmp_path / ".executor_results.sqlite"
    monkeypatch.setattr(result_store, "_DB_PATH", str(db))
    monkeypatch.setattr(result_store, "_conn", None)
    monkeypatch.setattr(result_store, "_disabled", False)
    monkeypatch.setattr(result_store, "_ocultado_pos_escrita", False)
    # NAO mocka ocultar_no_windows: em Linux ele e no-op, mas exercita o caminho real.

    try:
        result_store.put({"job_id": "j1", "status": "success"})
        result_store.put({"job_id": "j2", "status": "error"})
        assert db.exists()
        assert result_store.count_pending() == 2
        result_store.mark_sent("j1")
        assert result_store.count_pending() == 1
        assert [p["job_id"] for p in result_store.load_pending()] == ["j2"]
    finally:
        result_store.close()


def test_lixeira_e_ocultada_ao_criar(monkeypatch, tmp_path):
    from executor.sync import paths as paths_mod

    ocultos = []
    monkeypatch.setattr(paths_mod, "ocultar_no_windows", lambda p: ocultos.append(str(p)))

    origem = tmp_path / "parcelas.geojson"
    origem.write_bytes(b"{}")
    paths_mod.move_dataset_to_trash(tmp_path, "parcelas", [origem])

    assert str(tmp_path / paths_mod.TRASH_DIR_NAME) in ocultos


def test_sync_config_oculta_dotfile_de_config(monkeypatch, tmp_path):
    """Fiacao do 4o ponto: .atlans-sync-config.json e ocultado ao ser lido."""
    from executor.sync import sync_config as sc

    chamadas = []
    monkeypatch.setattr(sc, "ocultar_no_windows", lambda p: chamadas.append(str(p)))

    alvo = tmp_path / ".atlans-sync-config.json"
    alvo.write_text('{"include": ["*.geojson"]}', encoding="utf-8")
    sc.SyncConfig(tmp_path)   # __init__ chama _load_local

    assert str(alvo) in chamadas


def test_sync_config_nao_oculta_quando_ausente(monkeypatch, tmp_path):
    """Sem o arquivo, o early-return impede a chamada (nao oculta caminho inexistente)."""
    from executor.sync import sync_config as sc

    chamadas = []
    monkeypatch.setattr(sc, "ocultar_no_windows", lambda p: chamadas.append(str(p)))
    sc.SyncConfig(tmp_path)
    assert chamadas == []


def test_ignore_oculta_dotfile_de_config(monkeypatch, tmp_path):
    """Consistencia: .atlans-ignore recebe o mesmo tratamento do sync-config."""
    from executor.sync import ignore as ig

    chamadas = []
    monkeypatch.setattr(ig, "ocultar_no_windows", lambda p: chamadas.append(str(p)))

    alvo = tmp_path / ".atlans-ignore"
    alvo.write_text("*.tmp\n", encoding="utf-8")
    ig.IgnoreFilter(tmp_path)   # __init__ chama _load

    assert str(alvo) in chamadas


def test_ignore_nao_oculta_quando_ausente(monkeypatch, tmp_path):
    from executor.sync import ignore as ig

    chamadas = []
    monkeypatch.setattr(ig, "ocultar_no_windows", lambda p: chamadas.append(str(p)))
    ig.IgnoreFilter(tmp_path)
    assert chamadas == []


def test_manifesto_sobrevive_a_os_replace_que_falha(monkeypatch, tmp_path):
    """Contrato do caminho de erro do os.replace (ex.: destino bloqueado no Windows).

    O risco mais grave levantado na revisao: se o os.replace atomico falhasse
    sobre o manifesto, o executor nao podia corromper nem travar. Como em Linux o
    replace sempre funciona, simulamos a falha. Esperado: _escrever devolve False,
    flush() NAO marca como persistido, o manifesto continua 'sujo' para o proximo
    flush tentar de novo, nada e gravado e o `.tmp` e limpo.
    """
    from executor.sync import manifest as manifest_mod

    m = manifest_mod.SyncManifest(str(tmp_path), "ws-1", "exec-1")
    m.set_dataset("parcelas", {"type": "geojson"})

    def _replace_bloqueado(*_a, **_k):
        raise PermissionError("[WinError 5] Access is denied")

    monkeypatch.setattr(manifest_mod.os, "replace", _replace_bloqueado)

    asyncio.run(m.flush())  # nao deve levantar

    assert m._sujo is True                                    # pendente p/ retry
    assert not (tmp_path / ".atlans-sync.json").exists()      # nada persistido
    assert not (tmp_path / ".atlans-sync.json.tmp").exists()  # .tmp limpo
