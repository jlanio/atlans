# tests/unit/test_executor_dashboard.py
"""
Painel ao vivo do executor: gate de ativacao, comutacao de logging e render.

O gate (`should_enable`) e uma funcao pura de proposito — assim a matriz de
decisao inteira e testavel sem TTY real, sem Docker e sem terminal.

A parte de logging cobre a armadilha central: o StreamHandler do console NUNCA
teve filtro, entao ele levava ao terminal tambem `websockets`, `asyncio` e
qualquer biblioteca de terceiro. Os handlers de arquivo existentes SAO filtrados
por prefixo. Trocar um pelo outro sem um handler catch-all perderia registros —
o oposto do objetivo, que e mover o log para disco, nao apaga-lo.
"""
import io
import logging

import pytest

from executor import dashboard, logging_setup


# ── Gate ─────────────────────────────────────────────────────────────────────

def _gate(env=None, *, stdout=True, stderr=True, rich=True, w=120, h=40):
    """TERM entra por default porque fora do Windows o gate exige um TERM
    utilizavel. Com o env vazio de antes, todo caso "deveria ligar" falhava em
    Linux (o CI roda Ubuntu) e — pior — os casos "nao deveria ligar" passavam
    pelo motivo errado, desligando por TERM ausente em vez da regra sob teste.
    A propria regra do TERM e coberta em test_term_ausente_ou_dumb_nao_liga.
    """
    return dashboard.should_enable(
        env={"TERM": "xterm-256color", **(env or {})},
        stdout_tty=stdout, stderr_tty=stderr,
        rich_ok=rich, largura=w, altura=h,
    )


def test_off_vence_tudo():
    """Nem TTY perfeito nem rich instalado ligam o painel contra o operador."""
    modo, _ = _gate({"EXECUTOR_DASHBOARD": "off"})
    assert modo == dashboard.MODO_OFF


@pytest.mark.parametrize("valor", ["off", "never", "0", "false", "no", "OFF"])
def test_off_aceita_sinonimos(valor):
    assert _gate({"EXECUTOR_DASHBOARD": valor})[0] == dashboard.MODO_OFF


def test_sem_rich_nao_liga_nem_forcado():
    """A biblioteca e o unico requisito que `on` nao consegue contornar."""
    assert _gate(rich=False)[0] == dashboard.MODO_OFF
    assert _gate({"EXECUTOR_DASHBOARD": "on"}, rich=False)[0] == dashboard.MODO_OFF


def test_on_ignora_a_falta_de_tty():
    """Escape hatch consciente: quem passa `on` sabe o que esta fazendo."""
    modo, _ = _gate({"EXECUTOR_DASHBOARD": "on"}, stdout=False, stderr=False)
    assert modo == dashboard.MODO_RICH


def test_stdout_tty_mas_stderr_redirecionado_nao_liga():
    """Basta um dos dois nao ser terminal — e o caso de `2> arquivo`, e o de
    quem captura so um dos canais."""
    assert _gate(stdout=True, stderr=False)[0] == dashboard.MODO_OFF
    assert _gate(stdout=False, stderr=True)[0] == dashboard.MODO_OFF


def test_sem_tty_nenhum_nao_liga():
    """Cobre Docker sem -it, systemd/journald, `| tee` e o Electron, que
    captura a saida do processo por pipe."""
    assert _gate(stdout=False, stderr=False)[0] == dashboard.MODO_OFF


def test_log_color_never_desliga():
    """docker-compose.executor.yml usa LOG_COLOR=never — o operador ja pediu
    saida sem enfeite."""
    assert _gate({"LOG_COLOR": "never"})[0] == dashboard.MODO_OFF


def test_no_color_e_ci_desligam():
    assert _gate({"NO_COLOR": "1"})[0] == dashboard.MODO_OFF
    assert _gate({"CI": "true"})[0] == dashboard.MODO_OFF


def test_terminal_pequeno_demais_nao_liga():
    """Painel cortado e pior que painel nenhum."""
    assert _gate(w=40)[0] == dashboard.MODO_OFF
    assert _gate(h=8)[0] == dashboard.MODO_OFF


def test_terminal_interativo_liga():
    assert _gate()[0] == dashboard.MODO_RICH


def test_term_ausente_ou_dumb_nao_liga(monkeypatch):
    """Cron, systemd sem tty e imagens minimas caem aqui. A regra so vale fora do
    Windows, onde TERM nao e o sinal de terminal utilizavel — por isso o
    `os.name` e forcado, em vez de pular o teste no ambiente de quem desenvolve."""
    monkeypatch.setattr(dashboard.os, "name", "posix")
    base = dict(stdout_tty=True, stderr_tty=True, rich_ok=True, largura=120, altura=40)

    assert dashboard.should_enable(env={}, **base)[0] == dashboard.MODO_OFF
    assert dashboard.should_enable(env={"TERM": "dumb"}, **base)[0] == dashboard.MODO_OFF
    assert dashboard.should_enable(env={"TERM": "xterm"}, **base)[0] == dashboard.MODO_RICH


@pytest.mark.parametrize("caso", [
    {"env": {"EXECUTOR_DASHBOARD": "off"}},
    {"rich": False},
    {"stdout": False},
    {"env": {"LOG_COLOR": "never"}},
    {"w": 30},
])
def test_motivo_sempre_preenchido_quando_nao_liga(caso):
    """O motivo vai para o log de boot: um painel que nao aparece sem
    explicacao vira ticket de suporte."""
    modo, motivo = _gate(**caso)
    assert modo == dashboard.MODO_OFF
    assert motivo and isinstance(motivo, str)


def test_gate_do_processo_devolve_modo_e_motivo():
    modo, motivo = dashboard.should_enable_from_process()
    assert modo in (dashboard.MODO_RICH, dashboard.MODO_JSON, dashboard.MODO_OFF)
    assert motivo


# ── Modo JSON ────────────────────────────────────────────────────────────────
# O canal NDJSON e para consumidor que e um programa (o app desktop), nao para o
# terminal. Por isso ele ignora todas as condicoes que existem para proteger a
# tela — e por isso ele nunca e inferido.

@pytest.mark.parametrize("valor", ["json", "ndjson", "ipc", "JSON", " json "])
def test_json_aceita_sinonimos(valor):
    assert _gate({"EXECUTOR_DASHBOARD": valor})[0] == dashboard.MODO_JSON


@pytest.mark.parametrize("caso", [
    {"stdout": False, "stderr": False},   # pipe do supervisor — o caso normal
    {"rich": False},                      # nao desenha nada, nao precisa de rich
    {"w": 20, "h": 5},                    # nao ha tela para caber
    {"env": {"LOG_COLOR": "never", "NO_COLOR": "1", "CI": "true"}},
])
def test_json_ignora_as_condicoes_de_tela(caso):
    """Todas essas regras existem para nao estragar um terminal. Com um programa
    do outro lado do pipe, nenhuma se aplica — e o modo JSON e exatamente o
    cenario em que stdout NAO e um TTY."""
    env = {"EXECUTOR_DASHBOARD": "json", **caso.pop("env", {})}
    assert _gate(env, **caso)[0] == dashboard.MODO_JSON


def test_json_nunca_e_inferido():
    """Um terminal perfeito continua rendendo `rich`, e um ambiente sem TTY
    continua rendendo `off`. Emitir NDJSON no stdout de quem esperava log humano
    quebraria o consumidor em silencio — quem quer o canal, pede."""
    assert _gate()[0] == dashboard.MODO_RICH
    assert _gate(stdout=False, stderr=False)[0] == dashboard.MODO_OFF


def test_off_vence_json_apenas_se_pedido_explicitamente():
    """`off` e `json` sao valores diferentes da MESMA variavel; quem escreveu
    `off` desligou tudo, inclusive o canal."""
    assert _gate({"EXECUTOR_DASHBOARD": "off"})[0] == dashboard.MODO_OFF


# ── Comutacao de logging ─────────────────────────────────────────────────────

@pytest.fixture
def logging_limpo():
    """Isola o root logger — os testes mexem em handlers globais. E a fábrica
    de LogRecord: `configure_logging()` instala nela a redação de segredos, que
    valeria para o resto da sessão de testes."""
    from flow.utils import redacao_log

    root = logging.getLogger()
    originais = list(root.handlers)
    nivel = root.level
    fabrica, instalada = logging.getLogRecordFactory(), redacao_log._instalada
    estado = (logging_setup._console, logging_setup._detached_console,
              logging_setup._catch_all, logging_setup._agent_file,
              logging_setup._agent_file_path, logging_setup._configurado)
    yield root
    root.handlers[:] = originais
    root.setLevel(nivel)
    logging.setLogRecordFactory(fabrica)
    redacao_log._instalada = instalada
    (logging_setup._console, logging_setup._detached_console,
     logging_setup._catch_all, logging_setup._agent_file,
     logging_setup._agent_file_path, logging_setup._configurado) = estado


def _preparar(root, tmp_path, monkeypatch, *, log_file_agent=None):
    """Simula o estado pos-configure_logging() com um console e um arquivo."""
    root.handlers[:] = []
    console = logging.StreamHandler(io.StringIO())
    root.addHandler(console)
    root.setLevel(logging.INFO)

    logging_setup._console = console
    logging_setup._detached_console = None
    logging_setup._catch_all = None
    logging_setup._agent_file = None
    logging_setup._agent_file_path = None

    destino = str(tmp_path / "logs" / "executor.log")
    monkeypatch.setattr(logging_setup, "resolve_agent_log_path", lambda: destino)
    return console, destino


def test_modo_painel_captura_logger_de_terceiro(logging_limpo, tmp_path, monkeypatch):
    """O teste central: o handler que substitui o console nao pode ter filtro.

    Os handlers de arquivo existentes so aceitam `executor`/`httpx` e
    `flow`/`node`/`app` — nenhum deles cobre `websockets`, que hoje aparece no
    terminal. Com um handler filtrado no lugar do console, esse log sumiria.
    """
    _, destino = _preparar(logging_limpo, tmp_path, monkeypatch)

    logging_setup.switch_to_dashboard_mode()
    logging.getLogger("websockets.client").warning("conexao caiu")
    logging.getLogger("executor.job_queue").info("job enfileirado")
    for h in logging_limpo.handlers:
        h.flush()

    conteudo = open(destino, encoding="utf-8").read()
    assert "conexao caiu" in conteudo
    assert "job enfileirado" in conteudo


def test_modo_painel_tira_o_console_do_root(logging_limpo, tmp_path, monkeypatch):
    console, _ = _preparar(logging_limpo, tmp_path, monkeypatch)
    logging_setup.switch_to_dashboard_mode()
    assert console not in logging_limpo.handlers


def test_restore_devolve_o_mesmo_handler(logging_limpo, tmp_path, monkeypatch):
    console, _ = _preparar(logging_limpo, tmp_path, monkeypatch)
    logging_setup.switch_to_dashboard_mode()
    logging_setup.restore_console_mode()
    assert console in logging_limpo.handlers


def test_restore_e_idempotente(logging_limpo, tmp_path, monkeypatch):
    """emergency_stop pode ser chamado por varios caminhos de saida (atexit,
    KeyboardInterrupt, execve) — duplicar o console dobraria cada linha."""
    console, _ = _preparar(logging_limpo, tmp_path, monkeypatch)
    logging_setup.switch_to_dashboard_mode()
    logging_setup.restore_console_mode()
    logging_setup.restore_console_mode()
    logging_setup.restore_console_mode()
    assert logging_limpo.handlers.count(console) == 1


def test_arquivo_continua_gravando_depois_do_restore(logging_limpo, tmp_path, monkeypatch):
    """Fechar o painel nao pode parar o log em arquivo: o processo segue vivo."""
    _, destino = _preparar(logging_limpo, tmp_path, monkeypatch)
    logging_setup.switch_to_dashboard_mode()
    logging_setup.restore_console_mode()

    logging.getLogger("executor").info("depois do painel")
    for h in logging_limpo.handlers:
        h.flush()
    assert "depois do painel" in open(destino, encoding="utf-8").read()


def test_handler_filtrado_do_mesmo_arquivo_e_removido(logging_limpo, tmp_path, monkeypatch):
    """Se LOG_FILE_AGENT ja apontava para este arquivo, manter os dois
    handlers duplicaria cada linha de `executor.*` dentro dele."""
    _, destino = _preparar(logging_limpo, tmp_path, monkeypatch)

    antigo = logging_setup._rotating(destino)
    antigo.addFilter(logging_setup._PrefixFilter("executor"))
    logging_limpo.addHandler(antigo)
    logging_setup._agent_file = antigo
    logging_setup._agent_file_path = destino

    logging_setup.switch_to_dashboard_mode()
    assert antigo not in logging_limpo.handlers

    logging.getLogger("executor").info("linha unica")
    for h in logging_limpo.handlers:
        h.flush()
    assert open(destino, encoding="utf-8").read().count("linha unica") == 1


def test_diretorio_invalido_levanta_e_preserva_o_console(logging_limpo, tmp_path, monkeypatch):
    """A regra: o painel so liga se o arquivo abrir. Trocar o log do console
    por um arquivo que nao existe seria apagar o log, nao move-lo."""
    console, _ = _preparar(logging_limpo, tmp_path, monkeypatch)

    def _explode(_path):
        raise OSError("permissao negada")

    monkeypatch.setattr(logging_setup, "_rotating", _explode)

    with pytest.raises(logging_setup.LoggingSetupError):
        logging_setup.switch_to_dashboard_mode()
    assert console in logging_limpo.handlers


def test_log_level_do_env_e_lido_no_configure_e_nao_no_import(logging_limpo, monkeypatch):
    """`logging_setup` nao pode ler as variaveis no import: quem coloca o
    conteudo do `.env` no ambiente e o `load_dotenv()` de `config.py`, que roda
    depois. Lendo no import, `LOG_LEVEL=DEBUG` no .env era ignorado em silencio
    sempre que a ordem de import mudasse."""
    logging_limpo.handlers[:] = []
    logging_setup._configurado = False
    logging_setup._console = None
    logging_setup._detached_console = None

    # Simula o load_dotenv() acontecendo DEPOIS do import do modulo.
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_COLOR", "never")
    logging_setup.configure_logging()

    assert logging_limpo.level == logging.DEBUG
    formatter = logging_setup._console.formatter
    assert formatter._color is False, "LOG_COLOR=never do .env foi ignorado"


def test_alias_reusa_a_taxonomia_do_console():
    """O rodape do painel mostra a mesma coluna de subsistema do log."""
    assert logging_setup.alias_for("executor.connection").strip() == "CONN"
    assert logging_setup.alias_for("executor.sync.uploader").strip() == "SYNC"
    assert logging_setup.alias_for("flow.executor.core").strip() == "FLOW"
    assert len(logging_setup.alias_for("desconhecido.qualquer")) == 6


# ── Avisos de config antes dos handlers ──────────────────────────────────────

def test_avisos_do_import_de_config_sao_emitidos_no_flush(caplog, monkeypatch):
    """config.py e importado antes de existir handler algum. Antes esses
    avisos caiam no logging.lastResort (stderr cru) — com o painel no ar,
    virariam lixo por cima do desenho. A fila mora em executor/_ambiente.py;
    o estado dela e isolado aqui porque outro teste pode ja ter feito o flush."""
    from executor import _ambiente, config

    monkeypatch.setattr(_ambiente, "_AVISOS_ADIADOS", [])
    monkeypatch.setattr(_ambiente, "_logging_pronto", False)
    _ambiente.avisar("%s invalido — usando %d.", "EXECUTOR_MAX_CONCURRENT", 4)
    assert not caplog.records

    with caplog.at_level(logging.WARNING):
        config.flush_startup_warnings()

    assert any("EXECUTOR_MAX_CONCURRENT invalido" in r.getMessage() for r in caplog.records)
    assert _ambiente._AVISOS_ADIADOS == []


# ── Render ───────────────────────────────────────────────────────────────────

def _snapshot_sintetico():
    from executor.stats import ExecutorStats

    relogio = [1000.0]
    st = ExecutorStats(executor_id="a1b2c3d4-5e6f", version="1.0.0",
                       server_url="wss://agents.atlans.example.org",
                       clock=lambda: relogio[0])
    st.system = {"hostname": "geo-01", "container": True, "cpu_cores": 8,
                 "ram_total_gb": 16.0, "disk_total_gb": 930.0}
    st.sync_dirs = ("/data/sync",)
    st.on_connected()

    st.on_job_started("j1", run_id="run-antigo")
    st.on_job_finished("j1", "ok", 12.5)
    st.on_job_started("j2", run_id="run-vivo")
    st.on_event({"run_id": "run-vivo", "node": "n1", "status": "started",
                 "extra": {"node_name": "buffer_1", "nodes_total": 9}})
    st.on_event({"type": "sync_event", "event": "file_uploaded",
                 "dataset": "municipios", "timestamp": 1.0, "total_bytes": 5_000_000})
    st.on_log_record(
        logging.LogRecord("executor.connection", logging.ERROR, "", 0,
                          "Falha de rede. Reconectando...", (), None),
        "CONN  ", "ERROR",
    )
    relogio[0] += 30
    return st.snapshot(
        capacity={"queued": 3, "running": 1, "max_concurrent": 4, "max_queue": 50},
        recursos={"ram_available_gb": 6.1, "disk_free_gb": 221.0},
        processo={"cpu_pct": 47.2, "cpu_pct_norm": 5.9, "rss_mb": 812.0,
                  "threads": 34, "cpu_cores": 8},
    )


@pytest.mark.parametrize("largura,ascii_only", [(120, False), (80, False), (100, True)])
def test_render_nao_estoura_e_mostra_o_essencial(largura, ascii_only):
    pytest.importorskip("rich")
    from rich.console import Console
    from executor.dashboard import render

    buf = io.StringIO()
    Console(file=buf, width=largura, height=44, force_terminal=False,
            legacy_windows=False).print(
        render.build(_snapshot_sintetico(), largura=largura, altura=44,
                     log_path="/tmp/executor.log", ascii_only=ascii_only)
    )
    saida = buf.getvalue()

    assert "Atlans Executor v1.0.0" in saida
    assert "buffer_1" in saida            # nó em execução
    assert "Falha de rede" in saida       # alerta visível
    assert "/tmp/executor.log" in saida   # onde achar o log completo
    # Nenhuma linha pode estourar a largura — painel cortado engana o operador.
    assert max(len(linha) for linha in saida.splitlines()) <= largura


def _render_kw(snap, largura, altura, **kw):
    from rich.console import Console
    from executor.dashboard import render

    buf = io.StringIO()
    Console(file=buf, width=largura, height=altura, force_terminal=False,
            legacy_windows=False).print(
        render.build(snap, largura=largura, altura=altura,
                     log_path="/home/usuario/AtlansExecutor/logs/executor.log", **kw)
    )
    return buf.getvalue()


def _render(snap, largura, altura, ascii_only=False):
    return _render_kw(snap, largura, altura, ascii_only=ascii_only)


@pytest.mark.parametrize("largura,altura", [
    (200, 60), (160, 50), (140, 40), (132, 30), (120, 40), (120, 30),
    (120, 24), (120, 20), (120, 16), (110, 26), (100, 24), (90, 34),
    (80, 40), (80, 24), (80, 16), (72, 20), (64, 14), (60, 12),
])
def test_painel_nunca_estoura_o_terminal(largura, altura):
    """O `Live` repinta reescrevendo N linhas para cima. Se o renderavel for
    mais alto que o terminal, ele rola sem parar e o painel vira lixo continuo.

    A versao anterior decidia por limiares (`if altura >= 22`) sem medir nada:
    em 80x24 — um terminal absolutamente comum — o painel tinha 44 linhas.
    """
    pytest.importorskip("rich")
    saida = _render(_snapshot_sintetico(), largura, altura)
    linhas = saida.rstrip("\n").splitlines()
    assert len(linhas) <= altura, (
        f"painel com {len(linhas)} linhas num terminal de {altura}"
    )
    assert max((len(linha) for linha in linhas), default=0) <= largura


def test_painel_apertado_mantem_os_alertas():
    """Quando falta espaco, o que some sao 'em execucao' e geosync — nunca os
    alertas. Sem eles o painel esconde justamente o que precisa ser visto."""
    pytest.importorskip("rich")
    saida = _render(_snapshot_sintetico(), 120, 18)
    assert "alertas" in saida
    assert "Falha de rede" in saida


def test_painel_avisa_quando_corta_jobs_da_lista():
    """Truncar em silencio faria o painel mentir sobre quantos jobs rodam."""
    pytest.importorskip("rich")
    from executor.stats import ExecutorStats

    rel = [1000.0]
    st = ExecutorStats(version="1.0.0", clock=lambda: rel[0])
    for i in range(12):
        st.on_job_started(f"j{i}", run_id=f"run{i}")
        st.on_event({"run_id": f"run{i}", "node": "n", "status": "started",
                     "extra": {"node_name": "buffer", "nodes_total": 9}})
    rel[0] += 10
    snap = st.snapshot(capacity={"running": 12, "max_concurrent": 12,
                                 "queued": 0, "max_queue": 50},
                       recursos={}, processo={})
    # Em 120x30 cabem 4 dos 12 jobs — o titulo tem de dizer que 8 ficaram fora.
    apertado = _render(snap, 120, 30)
    assert "em execução (12)" in apertado
    assert "sem espaço" in apertado

    # Com altura de sobra os 12 aparecem e o aviso some.
    folgado = _render(snap, 120, 44)
    assert "em execução (12)" in folgado
    assert "sem espaço" not in folgado


# ── Atalhos de teclado ───────────────────────────────────────────────────────

@pytest.mark.parametrize("largura", [60, 72, 80, 100, 120, 160, 200])
@pytest.mark.parametrize("pausado", [False, True])
def test_rodape_com_atalhos_cabe_numa_linha(largura, pausado):
    """A altura do painel conta 1 linha para o rodape. Se a barra de atalhos o
    fizesse quebrar em duas, o `Live` voltaria a rolar."""
    pytest.importorskip("rich")
    from rich.console import Console
    from executor.dashboard import render

    buf = io.StringIO()
    Console(file=buf, width=largura, force_terminal=False, legacy_windows=False).print(
        render._rodape("/home/usuario/com/caminho/bem/longo/AtlansExecutor/logs/executor.log",
                       largura, atalhos=True, pausado=pausado, debug=False)
    )
    assert len(buf.getvalue().rstrip("\n").splitlines()) == 1


def test_rodape_sacrifica_o_caminho_antes_dos_atalhos():
    """Saber qual tecla apertar importa mais que ler o caminho inteiro — que
    tambem aparece na linha impressa quando o painel liga."""
    pytest.importorskip("rich")
    from rich.console import Console
    from executor.dashboard import render

    buf = io.StringIO()
    Console(file=buf, width=70, force_terminal=False, legacy_windows=False).print(
        render._rodape("/um/caminho/absurdamente/longo/AtlansExecutor/logs/executor.log",
                       70, atalhos=True, pausado=False, debug=False)
    )
    saida = buf.getvalue()
    assert "log/painel" in saida and "q encerra" in saida


def test_rodape_sem_teclado_explica_como_desligar():
    pytest.importorskip("rich")
    from rich.console import Console
    from executor.dashboard import render

    buf = io.StringIO()
    Console(file=buf, width=120, force_terminal=False, legacy_windows=False).print(
        render._rodape("/tmp/x.log", 120, atalhos=False, pausado=False, debug=False)
    )
    assert "EXECUTOR_DASHBOARD=off" in buf.getvalue()


def test_ajuda_substitui_o_corpo_e_mantem_cabecalho_e_rodape():
    pytest.importorskip("rich")
    saida = _render_kw(_snapshot_sintetico(), 110, 34, atalhos=True, overlay="ajuda")
    assert "atalhos" in saida
    assert "alterna entre o painel e o log" in saida
    assert "Atlans Executor" in saida       # cabecalho fica
    assert "log/painel" in saida            # rodape fica
    assert "workflows" not in saida         # corpo deu lugar a ajuda


def test_teclado_indisponivel_sem_tty(monkeypatch):
    """stdin redirecionado (`< /dev/null`, pipe, supervisor) — o painel continua
    funcionando, so sem atalhos."""
    from executor.dashboard import keys

    class _FakeStdin:
        def isatty(self):
            return False

    monkeypatch.setattr(keys.sys, "stdin", _FakeStdin())
    assert keys.teclado_disponivel() is False


@pytest.mark.asyncio
async def test_leitor_de_teclas_nao_sobe_sem_terminal(monkeypatch):
    from executor.dashboard import keys

    monkeypatch.setattr(keys, "teclado_disponivel", lambda: False)
    assert keys.LeitorDeTeclas(lambda t: None).start() is False


@pytest.mark.asyncio
async def test_leitor_entrega_as_teclas_no_event_loop(monkeypatch):
    """A thread le bloqueando e entrega por `call_soon_threadsafe`. Se a entrega
    nao passasse pelo loop, o callback mexeria no estado do painel de outra
    thread, no meio de um render."""
    import asyncio as aio
    import queue as _queue
    from executor.dashboard import keys

    pendentes = _queue.Queue()
    for t in ("l", "p", "q"):
        pendentes.put(t)

    recebidas: list[tuple[str, int]] = []
    principal = __import__("threading").get_ident()
    tudo = aio.Event()

    def registrar(tecla: str) -> None:
        recebidas.append((tecla, __import__("threading").get_ident()))
        if len(recebidas) == 3:
            tudo.set()

    leitor = keys.LeitorDeTeclas(registrar)
    monkeypatch.setattr(keys, "teclado_disponivel", lambda: True)
    monkeypatch.setattr(leitor, "_preparar_terminal", lambda: None)
    monkeypatch.setattr(leitor, "_ler_uma", lambda: pendentes.get())

    assert leitor.start() is True
    try:
        await aio.wait_for(tudo.wait(), timeout=5)
    finally:
        leitor.stop()

    assert [t for t, _ in recebidas] == ["l", "p", "q"]
    assert all(ident == principal for _, ident in recebidas), \
        "callback rodou fora do event loop"


def test_restaurar_terminal_e_idempotente():
    """A restauracao e chamada de tres lugares (stop, finally da thread,
    atexit). Um terminal deixado em cbreak para de ecoar o que o usuario
    digita — o shell parece travado."""
    from executor.dashboard import keys

    keys._restaurar_terminal()
    keys._restaurar_terminal()  # sem estado guardado, nao pode levantar


def _runtime_de_teste(tmp_path, ao_sair=None):
    from executor.dashboard.runtime import DashboardRuntime
    from executor.stats import ExecutorStats

    class _Fila:
        def qsize(self):
            return 0

    stats = ExecutorStats(executor_id="deadbeef", version="1.0.0", server_url="ws://x")
    stats.system = {"hostname": "t", "cpu_cores": 4, "ram_total_gb": 8.0,
                    "disk_total_gb": 100.0}
    return DashboardRuntime(
        stats,
        capacity_source=lambda: {"queued": 0, "running": 0,
                                 "max_concurrent": 4, "max_queue": 50},
        result_queue=_Fila(), intervalo=0.05,
        log_path=str(tmp_path / "executor.log"), ao_sair=ao_sair,
    )


@pytest.mark.asyncio
async def test_tecla_l_alterna_painel_e_log(logging_limpo, tmp_path, monkeypatch):
    """O que o usuario pediu: voltar ao log de sempre sem reiniciar o executor.

    No modo log o console recebe de novo; no modo painel, nao. O arquivo grava
    nos dois — alternar nunca pode custar registro.
    """
    pytest.importorskip("rich")
    from executor.dashboard.runtime import MODO_LOG, MODO_PAINEL

    console, destino = _preparar(logging_limpo, tmp_path, monkeypatch)
    logging_setup.ensure_file_mirror()

    dash = _runtime_de_teste(tmp_path)
    monkeypatch.setattr(dash._teclas, "start", lambda: False)  # sem thread real
    await dash.start()
    try:
        assert dash.modo == MODO_PAINEL
        assert console not in logging_limpo.handlers
        logging.getLogger("executor").info("no painel")

        dash._tecla("l")
        assert dash.modo == MODO_LOG
        assert console in logging_limpo.handlers
        logging.getLogger("executor").info("no log")

        dash._tecla("l")
        assert dash.modo == MODO_PAINEL
        assert console not in logging_limpo.handlers
        logging.getLogger("executor").info("no painel de novo")
    finally:
        await dash.stop()

    for h in logging_limpo.handlers:
        h.flush()
    arquivo = open(destino, encoding="utf-8").read()
    assert all(m in arquivo for m in ("no painel", "no log", "no painel de novo"))
    assert console in logging_limpo.handlers, "console tem de voltar no stop"


@pytest.mark.asyncio
async def test_tecla_q_dispara_o_shutdown(logging_limpo, tmp_path, monkeypatch):
    """'q' entra pelo mesmo caminho de um SIGTERM. Vale ainda mais no Windows,
    onde `add_signal_handler` nao registra nada e o Ctrl+C pode matar o
    processo antes de qualquer `finally`."""
    pytest.importorskip("rich")
    _preparar(logging_limpo, tmp_path, monkeypatch)
    logging_setup.ensure_file_mirror()

    chamou: list[bool] = []
    dash = _runtime_de_teste(tmp_path, ao_sair=lambda: chamou.append(True))
    monkeypatch.setattr(dash._teclas, "start", lambda: False)
    await dash.start()
    try:
        dash._tecla("q")
        assert chamou == [True]
    finally:
        await dash.stop()


@pytest.mark.asyncio
async def test_tecla_d_alterna_o_nivel_de_log(logging_limpo, tmp_path, monkeypatch):
    """Diagnosticar um erro exigia parar o executor, editar LOG_LEVEL no .env e
    subir de novo — perdendo o estado que se queria investigar."""
    pytest.importorskip("rich")
    _preparar(logging_limpo, tmp_path, monkeypatch)
    logging_setup.ensure_file_mirror()
    logging_limpo.setLevel(logging.INFO)
    logging_setup._nivel_base = None

    dash = _runtime_de_teste(tmp_path)
    monkeypatch.setattr(dash._teclas, "start", lambda: False)
    await dash.start()
    try:
        dash._tecla("d")
        assert logging_limpo.level == logging.DEBUG
        # httpx em DEBUG despeja cada frame HTTP e afoga o resto.
        assert logging.getLogger("httpx").level == logging.INFO

        dash._tecla("d")
        assert logging_limpo.level == logging.INFO
        assert logging.getLogger("httpx").level == logging.WARNING
    finally:
        await dash.stop()


@pytest.mark.asyncio
async def test_tecla_r_interrompe_o_backoff(logging_limpo, tmp_path, monkeypatch):
    """Quando a rede volta, o executor pode estar num backoff de ate 60s."""
    pytest.importorskip("rich")
    _preparar(logging_limpo, tmp_path, monkeypatch)
    logging_setup.ensure_file_mirror()

    pedidos: list[bool] = []
    dash = _runtime_de_teste(tmp_path)
    dash._ao_reconectar = lambda: (pedidos.append(True), True)[1]
    monkeypatch.setattr(dash._teclas, "start", lambda: False)
    await dash.start()
    try:
        dash._tecla("r")
        assert pedidos == [True]
    finally:
        await dash.stop()


@pytest.mark.asyncio
async def test_tecla_z_zera_os_contadores(logging_limpo, tmp_path, monkeypatch):
    pytest.importorskip("rich")
    _preparar(logging_limpo, tmp_path, monkeypatch)
    logging_setup.ensure_file_mirror()

    dash = _runtime_de_teste(tmp_path)
    monkeypatch.setattr(dash._teclas, "start", lambda: False)
    await dash.start()
    try:
        dash._stats.on_job_started("j", run_id="j")
        dash._stats.on_job_finished("j", "ok", 5.0)
        assert dash._stats.snapshot(capacity={}, recursos={}, processo={}).total_ok == 1

        dash._tecla("z")
        assert dash._stats.snapshot(capacity={}, recursos={}, processo={}).total_ok == 0
    finally:
        await dash.stop()


@pytest.mark.asyncio
async def test_tecla_a_abre_o_historico_de_alertas(logging_limpo, tmp_path, monkeypatch):
    """O buffer guarda 200 linhas mas o rodape mostra 6 — 194 ficam invisiveis."""
    pytest.importorskip("rich")
    _preparar(logging_limpo, tmp_path, monkeypatch)
    logging_setup.ensure_file_mirror()

    dash = _runtime_de_teste(tmp_path)
    monkeypatch.setattr(dash._teclas, "start", lambda: False)
    await dash.start()
    try:
        dash._tecla("a")
        assert dash._overlay == "alertas"
        dash._tecla("a")
        assert dash._overlay is None

        # Um overlay substitui o outro, em vez de empilhar.
        dash._tecla("a")
        dash._tecla("?")
        assert dash._overlay == "ajuda"
    finally:
        await dash.stop()


@pytest.mark.asyncio
async def test_teclas_p_e_interrogacao(logging_limpo, tmp_path, monkeypatch):
    pytest.importorskip("rich")
    _preparar(logging_limpo, tmp_path, monkeypatch)
    logging_setup.ensure_file_mirror()

    dash = _runtime_de_teste(tmp_path)
    monkeypatch.setattr(dash._teclas, "start", lambda: False)
    await dash.start()
    try:
        dash._tecla("p")
        assert dash._pausado is True
        dash._tecla("p")
        assert dash._pausado is False

        dash._tecla("?")
        assert dash._overlay == "ajuda"
        dash._tecla("h")
        assert dash._overlay is None

        # Tecla desconhecida nao pode mudar nada nem levantar.
        dash._tecla("")
        assert dash._pausado is False and dash._overlay is None
    finally:
        await dash.stop()


def test_render_omite_o_total_quando_a_ram_livre_e_maior():
    """Acontece de verdade em container: se memory.max existe mas
    memory.current nao, o total vem do cgroup e o disponivel cai no psutil do
    HOST. Mostrar '34 / 16 GB' seria pior que omitir o total."""
    pytest.importorskip("rich")
    from rich.console import Console
    from executor.dashboard import render
    from dataclasses import replace

    snap = replace(_snapshot_sintetico(), ram_available_gb=34.0, ram_total_gb=16.0)
    buf = io.StringIO()
    Console(file=buf, width=120, height=44, force_terminal=False,
            legacy_windows=False).print(
        render.build(snap, largura=120, altura=44, log_path="/tmp/x.log")
    )
    saida = buf.getvalue()
    assert "34.0 GB" in saida
    assert "34.0 / 16.0" not in saida


def test_render_ascii_nao_usa_caractere_fora_do_cp1252():
    """O conhost legado do Windows usa a code page ANSI e levanta
    UnicodeEncodeError no primeiro '●' — o painel morreria no 1o quadro."""
    pytest.importorskip("rich")
    from rich.console import Console
    from executor.dashboard import render

    buf = io.StringIO()
    Console(file=buf, width=100, height=44, force_terminal=False,
            legacy_windows=False).print(
        render.build(_snapshot_sintetico(), largura=100, altura=44,
                     log_path="/tmp/executor.log", ascii_only=True)
    )
    # errors='strict': qualquer glifo fora da code page levanta aqui.
    buf.getvalue().encode("cp1252")
