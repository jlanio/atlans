# tests/unit/test_executor_dashboard.py
"""
Executor live panel: activation gate, logging switching and rendering.

The gate (`should_enable`) is a pure function on purpose — that way the whole
decision matrix is testable without a real TTY, without Docker and without a
terminal.

The logging part covers the central pitfall: the console StreamHandler NEVER
had a filter, so it also sent `websockets`, `asyncio` and any third-party
library to the terminal. The existing file handlers ARE filtered by prefix.
Swapping one for the other without a catch-all handler would lose records —
the opposite of the goal, which is to move the log to disk, not delete it.
"""
import io
import logging

import pytest

from executor import dashboard, logging_setup


# ── Gate ─────────────────────────────────────────────────────────────────────

def _gate(env=None, *, stdout=True, stderr=True, rich=True, w=120, h=40):
    """TERM is included by default because outside Windows the gate requires a
    usable TERM. With the empty env from before, every "should enable" case
    failed on Linux (the CI runs Ubuntu) and — worse — the "should not enable"
    cases passed for the wrong reason, disabling due to a missing TERM instead
    of the rule under test. The TERM rule itself is covered in
    test_term_ausente_ou_dumb_nao_liga.
    """
    return dashboard.should_enable(
        env={"TERM": "xterm-256color", **(env or {})},
        stdout_tty=stdout, stderr_tty=stderr,
        rich_ok=rich, largura=w, altura=h,
    )


def test_off_vence_tudo():
    """Neither a perfect TTY nor rich installed turn the panel on against the operator."""
    modo, _ = _gate({"EXECUTOR_DASHBOARD": "off"})
    assert modo == dashboard.MODO_OFF


@pytest.mark.parametrize("valor", ["off", "never", "0", "false", "no", "OFF"])
def test_off_aceita_sinonimos(valor):
    assert _gate({"EXECUTOR_DASHBOARD": valor})[0] == dashboard.MODO_OFF


def test_sem_rich_nao_liga_nem_forcado():
    """The library is the only requirement that `on` cannot bypass."""
    assert _gate(rich=False)[0] == dashboard.MODO_OFF
    assert _gate({"EXECUTOR_DASHBOARD": "on"}, rich=False)[0] == dashboard.MODO_OFF


def test_on_ignora_a_falta_de_tty():
    """Deliberate escape hatch: whoever passes `on` knows what they are doing."""
    modo, _ = _gate({"EXECUTOR_DASHBOARD": "on"}, stdout=False, stderr=False)
    assert modo == dashboard.MODO_RICH


def test_stdout_tty_mas_stderr_redirecionado_nao_liga():
    """It is enough for one of the two not to be a terminal — that is the case of
    `2> arquivo`, and of whoever captures only one of the channels."""
    assert _gate(stdout=True, stderr=False)[0] == dashboard.MODO_OFF
    assert _gate(stdout=False, stderr=True)[0] == dashboard.MODO_OFF


def test_sem_tty_nenhum_nao_liga():
    """Covers Docker without -it, systemd/journald, `| tee` and Electron, which
    captures the process output through a pipe."""
    assert _gate(stdout=False, stderr=False)[0] == dashboard.MODO_OFF


def test_log_color_never_desliga():
    """docker-compose.executor.yml uses LOG_COLOR=never — the operator already
    asked for unadorned output."""
    assert _gate({"LOG_COLOR": "never"})[0] == dashboard.MODO_OFF


def test_no_color_e_ci_desligam():
    assert _gate({"NO_COLOR": "1"})[0] == dashboard.MODO_OFF
    assert _gate({"CI": "true"})[0] == dashboard.MODO_OFF


def test_terminal_pequeno_demais_nao_liga():
    """A clipped panel is worse than no panel."""
    assert _gate(w=40)[0] == dashboard.MODO_OFF
    assert _gate(h=8)[0] == dashboard.MODO_OFF


def test_terminal_interativo_liga():
    assert _gate()[0] == dashboard.MODO_RICH


def test_term_ausente_ou_dumb_nao_liga(monkeypatch):
    """Cron, systemd without a tty and minimal images end up here. The rule only
    applies outside Windows, where TERM is not the sign of a usable terminal —
    that is why `os.name` is forced, instead of skipping the test in the
    developer's environment."""
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
    """The reason goes to the boot log: a panel that does not show up without
    explanation becomes a support ticket."""
    modo, motivo = _gate(**caso)
    assert modo == dashboard.MODO_OFF
    assert motivo and isinstance(motivo, str)


def test_gate_do_processo_devolve_modo_e_motivo():
    modo, motivo = dashboard.should_enable_from_process()
    assert modo in (dashboard.MODO_RICH, dashboard.MODO_JSON, dashboard.MODO_OFF)
    assert motivo


# ── JSON mode ────────────────────────────────────────────────────────────────
# The NDJSON channel is for a consumer that is a program (the desktop app), not
# for the terminal. That is why it ignores every condition that exists to
# protect the screen — and that is why it is never inferred.

@pytest.mark.parametrize("valor", ["json", "ndjson", "ipc", "JSON", " json "])
def test_json_aceita_sinonimos(valor):
    assert _gate({"EXECUTOR_DASHBOARD": valor})[0] == dashboard.MODO_JSON


@pytest.mark.parametrize("caso", [
    {"stdout": False, "stderr": False},   # pipe do supervisor — o caso normal
    {"rich": False},                      # draws nothing, does not need rich
    {"w": 20, "h": 5},                    # there is no screen to fit
    {"env": {"LOG_COLOR": "never", "NO_COLOR": "1", "CI": "true"}},
])
def test_json_ignora_as_condicoes_de_tela(caso):
    """All these rules exist so as not to mess up a terminal. With a program on
    the other side of the pipe, none of them applies — and JSON mode is exactly
    the scenario in which stdout is NOT a TTY."""
    env = {"EXECUTOR_DASHBOARD": "json", **caso.pop("env", {})}
    assert _gate(env, **caso)[0] == dashboard.MODO_JSON


def test_json_nunca_e_inferido():
    """A perfect terminal still yields `rich`, and an environment without a TTY
    still yields `off`. Emitting NDJSON on the stdout of someone expecting a
    human log would silently break the consumer — whoever wants the channel
    asks for it."""
    assert _gate()[0] == dashboard.MODO_RICH
    assert _gate(stdout=False, stderr=False)[0] == dashboard.MODO_OFF


def test_off_vence_json_apenas_se_pedido_explicitamente():
    """`off` and `json` are different values of the SAME variable; whoever wrote
    `off` turned everything off, including the channel."""
    assert _gate({"EXECUTOR_DASHBOARD": "off"})[0] == dashboard.MODO_OFF


# ── Logging switching ────────────────────────────────────────────────────────

@pytest.fixture
def logging_limpo():
    """Isolates the root logger — the tests touch global handlers. And the
    LogRecord factory: `configure_logging()` installs secret redaction in it,
    which would apply to the rest of the test session."""
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
    """The central test: the handler replacing the console must have no filter.

    The existing file handlers only accept `executor`/`httpx` and
    `flow`/`node`/`app` — none of them covers `websockets`, which shows up in
    the terminal today. With a filtered handler in place of the console, that
    log would vanish.
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
    """emergency_stop can be called by several exit paths (atexit,
    KeyboardInterrupt, execve) — duplicating the console would double every line."""
    console, _ = _preparar(logging_limpo, tmp_path, monkeypatch)
    logging_setup.switch_to_dashboard_mode()
    logging_setup.restore_console_mode()
    logging_setup.restore_console_mode()
    logging_setup.restore_console_mode()
    assert logging_limpo.handlers.count(console) == 1


def test_arquivo_continua_gravando_depois_do_restore(logging_limpo, tmp_path, monkeypatch):
    """Closing the panel must not stop the file log: the process stays alive."""
    _, destino = _preparar(logging_limpo, tmp_path, monkeypatch)
    logging_setup.switch_to_dashboard_mode()
    logging_setup.restore_console_mode()

    logging.getLogger("executor").info("depois do painel")
    for h in logging_limpo.handlers:
        h.flush()
    assert "depois do painel" in open(destino, encoding="utf-8").read()


def test_handler_filtrado_do_mesmo_arquivo_e_removido(logging_limpo, tmp_path, monkeypatch):
    """If LOG_FILE_AGENT already pointed to this file, keeping both handlers
    would duplicate every `executor.*` line inside it."""
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
    """The rule: the panel only turns on if the file opens. Swapping the console
    log for a file that does not exist would be deleting the log, not moving it."""
    console, _ = _preparar(logging_limpo, tmp_path, monkeypatch)

    def _explode(_path):
        raise OSError("permissao negada")

    monkeypatch.setattr(logging_setup, "_rotating", _explode)

    with pytest.raises(logging_setup.LoggingSetupError):
        logging_setup.switch_to_dashboard_mode()
    assert console in logging_limpo.handlers


def test_log_level_do_env_e_lido_no_configure_e_nao_no_import(logging_limpo, monkeypatch):
    """`logging_setup` must not read the variables at import: what puts the
    contents of `.env` into the environment is `load_dotenv()` in `config.py`,
    which runs later. Reading at import, `LOG_LEVEL=DEBUG` in the .env was
    silently ignored whenever the import order changed."""
    logging_limpo.handlers[:] = []
    logging_setup._configurado = False
    logging_setup._console = None
    logging_setup._detached_console = None

    # Simulates load_dotenv() happening AFTER the module import.
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_COLOR", "never")
    logging_setup.configure_logging()

    assert logging_limpo.level == logging.DEBUG
    formatter = logging_setup._console.formatter
    assert formatter._color is False, "LOG_COLOR=never do .env foi ignorado"


def test_alias_reusa_a_taxonomia_do_console():
    """The panel footer shows the same subsystem column as the log."""
    assert logging_setup.alias_for("executor.connection").strip() == "CONN"
    assert logging_setup.alias_for("executor.sync.uploader").strip() == "SYNC"
    assert logging_setup.alias_for("flow.executor.core").strip() == "FLOW"
    assert len(logging_setup.alias_for("desconhecido.qualquer")) == 6


# ── Config warnings before the handlers ──────────────────────────────────────

def test_avisos_do_import_de_config_sao_emitidos_no_flush(caplog, monkeypatch):
    """config.py is imported before any handler exists. Before, these warnings
    fell into logging.lastResort (raw stderr) — with the panel up, they would
    become garbage on top of the drawing. The queue lives in
    executor/_ambiente.py; its state is isolated here because another test may
    already have done the flush."""
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
    assert "buffer_1" in saida            # node running
    assert "Falha de rede" in saida       # visible alert
    assert "/tmp/executor.log" in saida   # where to find the full log
    # No line may exceed the width — a clipped panel misleads the operator.
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
    """`Live` repaints by rewriting N lines upward. If the renderable is taller
    than the terminal, it scrolls nonstop and the panel becomes continuous garbage.

    The previous version decided by thresholds (`if altura >= 22`) without
    measuring anything: at 80x24 — an entirely common terminal — the panel had
    44 lines.
    """
    pytest.importorskip("rich")
    saida = _render(_snapshot_sintetico(), largura, altura)
    linhas = saida.rstrip("\n").splitlines()
    assert len(linhas) <= altura, (
        f"painel com {len(linhas)} linhas num terminal de {altura}"
    )
    assert max((len(linha) for linha in linhas), default=0) <= largura


def test_painel_apertado_mantem_os_alertas():
    """When space runs out, what goes away is 'em execucao' (running) and geosync
    — never the alerts. Without them the panel hides precisely what needs to be seen."""
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
    # At 120x30, 4 of the 12 jobs fit — the title must say that 8 were left out.
    apertado = _render(snap, 120, 30)
    assert "em execução (12)" in apertado
    assert "sem espaço" in apertado

    # With height to spare, all 12 show up and the notice goes away.
    folgado = _render(snap, 120, 44)
    assert "em execução (12)" in folgado
    assert "sem espaço" not in folgado


# ── Keyboard shortcuts ───────────────────────────────────────────────────────

@pytest.mark.parametrize("largura", [60, 72, 80, 100, 120, 160, 200])
@pytest.mark.parametrize("pausado", [False, True])
def test_rodape_com_atalhos_cabe_numa_linha(largura, pausado):
    """The panel height counts 1 line for the footer. If the shortcut bar made it
    wrap into two, `Live` would start scrolling again."""
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
    """Knowing which key to press matters more than reading the whole path —
    which also appears in the line printed when the panel turns on."""
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
    assert "Atlans Executor" in saida       # header stays
    assert "log/painel" in saida            # footer stays
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
    """The thread reads blocking and delivers via `call_soon_threadsafe`. If the
    delivery did not go through the loop, the callback would touch the panel
    state from another thread, in the middle of a render."""
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
    """The restoration is called from three places (stop, the thread's finally,
    atexit). A terminal left in cbreak stops echoing what the user types —
    the shell looks frozen."""
    from executor.dashboard import keys

    keys._restaurar_terminal()
    keys._restaurar_terminal()  # with no saved state, must not raise


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
    """What the user asked for: go back to the usual log without restarting the executor.

    In log mode the console receives again; in panel mode, it does not. The
    file writes in both — toggling must never cost a record.
    """
    pytest.importorskip("rich")
    from executor.dashboard.runtime import MODO_LOG, MODO_PAINEL

    console, destino = _preparar(logging_limpo, tmp_path, monkeypatch)
    logging_setup.ensure_file_mirror()

    dash = _runtime_de_teste(tmp_path)
    monkeypatch.setattr(dash._teclas, "start", lambda: False)  # no real thread
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
    """'q' goes through the same path as a SIGTERM. It matters even more on
    Windows, where `add_signal_handler` registers nothing and Ctrl+C can kill
    the process before any `finally`."""
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
    """Diagnosing an error required stopping the executor, editing LOG_LEVEL in
    the .env and starting it again — losing the state one wanted to investigate."""
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
    """When the network comes back, the executor may be in a backoff of up to 60s."""
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
    """The buffer keeps 200 lines but the footer shows 6 — 194 stay invisible."""
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

        # One overlay replaces the other, instead of stacking.
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

        # An unknown key must not change anything or raise.
        dash._tecla("")
        assert dash._pausado is False and dash._overlay is None
    finally:
        await dash.stop()


def test_render_omite_o_total_quando_a_ram_livre_e_maior():
    """It really happens in a container: if memory.max exists but memory.current
    does not, the total comes from the cgroup and the available amount falls
    back to the HOST's psutil. Showing '34 / 16 GB' would be worse than omitting
    the total."""
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
    """The legacy Windows conhost uses the ANSI code page and raises
    UnicodeEncodeError on the first '●' — the panel would die on the 1st frame."""
    pytest.importorskip("rich")
    from rich.console import Console
    from executor.dashboard import render

    buf = io.StringIO()
    Console(file=buf, width=100, height=44, force_terminal=False,
            legacy_windows=False).print(
        render.build(_snapshot_sintetico(), largura=100, altura=44,
                     log_path="/tmp/executor.log", ascii_only=True)
    )
    # errors='strict': any glyph outside the code page raises here.
    buf.getvalue().encode("cp1252")
