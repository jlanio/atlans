# executor/dashboard/render.py
"""
Dashboard drawing. Pure function: Snapshot in, rich renderable out.

Kept separate from the runtime on purpose — that way a synthetic Snapshot can
be rendered into a fixed-width Console inside a test, with no event loop and no
terminal.

Every non-ASCII glyph goes through the `Glyphs` object. This is not fussiness:
the legacy Windows conhost uses the ANSI code page (cp1252 in pt-BR) and raises
UnicodeEncodeError on the first '●' — the dashboard would die on the first frame.
"""
from __future__ import annotations

from dataclasses import dataclass

from typing import NamedTuple

from rich import box
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from executor.stats import Snapshot


@dataclass(frozen=True)
class Glyphs:
    conectado: str
    conectando: str
    offline: str
    terminal: str
    barra_cheia: str
    barra_vazia: str
    sobe: str
    desce: str
    elipse: str
    sep: str
    vazio: str
    caixa: box.Box


UNICODE = Glyphs(
    conectado="●", conectando="◌", offline="○", terminal="✖",
    barra_cheia="█", barra_vazia="░",
    sobe="↑", desce="↓", elipse="…", sep="·", vazio="—",
    caixa=box.ROUNDED,
)

ASCII = Glyphs(
    conectado="*", conectando="o", offline=".", terminal="x",
    barra_cheia="#", barra_vazia=".",
    sobe="^", desce="v", elipse="..", sep="-", vazio="-",
    caixa=box.ASCII,
)

# Minimum height of the alerts block (1 line + 2 borders). Always reserved:
# without it the dashboard would hide precisely what needs to be seen.
_ALERTAS_MIN = 3
# Altura minima util do bloco "em execucao": 1 job + cabecalho + 2 bordas.
_EXEC_MIN = 4

_CONN_COLOR = {
    "connected": "green", "connecting": "yellow",
    "reconnecting": "yellow", "offline": "red", "terminal": "red",
}
_CONN_LABEL = {
    "connected": "conectado",
    "connecting": "conectando",
    "reconnecting": "reconectando",
    "offline": "offline",
    "terminal": "encerrado pelo servidor",
}


def _nivel_debug() -> bool:
    """Is the root logger at DEBUG? Read on the spot, so the footer indicator
    cannot diverge from the actual logging state."""
    import logging as _logging
    return _logging.getLogger().level <= _logging.DEBUG


def _conn_symbol(estado: str, g: Glyphs) -> str:
    return {
        "connected": g.conectado,
        "connecting": g.conectando,
        "reconnecting": g.conectando,
        "terminal": g.terminal,
    }.get(estado, g.offline)


def _dur(segundos: float | None, g: Glyphs) -> str:
    """Human-readable duration. Scales the unit instead of showing '4821.3s'."""
    if segundos is None:
        return g.vazio
    s = float(segundos)
    if s < 1:
        return f"{s * 1000:.0f}ms"
    if s < 60:
        return f"{s:.1f}s"
    if s < 3600:
        return f"{int(s // 60)}m{int(s % 60):02d}s"
    h, resto = divmod(int(s), 3600)
    return f"{h}h{resto // 60:02d}m"


def _bytes(n: int | None) -> str:
    if not n:
        return "0 B"
    val = float(n)
    for unidade in ("B", "KB", "MB", "GB", "TB"):
        if val < 1024 or unidade == "TB":
            return f"{val:.0f} {unidade}" if unidade == "B" else f"{val:.1f} {unidade}"
        val /= 1024
    return f"{val:.1f} TB"


def _barra(fracao: float | None, g: Glyphs, largura: int = 10) -> Text:
    """Proportion bar colored by band: green up to 70%, yellow up to 90%, red."""
    if fracao is None:
        return Text(g.vazio, style="dim")
    f = max(0.0, min(1.0, fracao))
    cheio = int(round(f * largura))
    cor = "green" if f < 0.7 else ("yellow" if f < 0.9 else "red")
    return Text(g.barra_cheia * cheio, style=cor) + Text(g.barra_vazia * (largura - cheio), style="dim")


def _kv() -> Table:
    """Two-column grid — the blocks' 'label / value' format."""
    t = Table.grid(padding=(0, 1))
    t.add_column(style="dim", no_wrap=True)
    t.add_column(no_wrap=True)
    return t


class Bloco(NamedTuple):
    """Renderable along with its height in lines.

    The height must be known BEFORE drawing: rich's `Live` rewrites N lines
    upward on every frame, and if N exceeds the terminal height the dashboard
    scrolls endlessly — it turns into continuous garbage instead of a stable
    frame. Every block uses `no_wrap` columns, so one logical line is always one
    physical line and the count adds up.
    """
    render: RenderableType
    altura: int


def _painel(corpo, titulo: str, g: Glyphs, borda: str = "dim", linhas: int = 0) -> Bloco:
    p = Panel(corpo, title=titulo, title_align="left", border_style=borda, box=g.caixa)
    return Bloco(p, linhas + 2)  # +2 for the top and bottom borders


def _curto(ident: str | None, g: Glyphs) -> str:
    if not ident:
        return g.vazio
    return ident[:8] + g.elipse


# ── Blocos ───────────────────────────────────────────────────────────────────

def _bloco_workflows(s: Snapshot, g: Glyphs) -> Panel:
    t = _kv()
    t.add_row("total", str(s.total_ok + s.total_error + s.total_cancelled))
    t.add_row("ok", Text(str(s.total_ok), style="green"))
    t.add_row("erro", Text(str(s.total_error), style="red" if s.total_error else "dim"))
    t.add_row("cancelado", Text(str(s.total_cancelled), style="dim"))

    cor = "green" if s.success_rate >= 0.95 else ("yellow" if s.success_rate >= 0.8 else "red")
    t.add_row("sucesso", Text(f"{s.success_rate * 100:.1f}%", style=cor))

    hora = str(s.last_hour_total)
    if s.last_hour_error:
        hora += f"  ({s.last_hour_error} erro)"
    t.add_row("última hora", hora)
    t.add_row("vazão", f"{s.throughput_per_min:.1f} wf/min")

    # After a 'z', "total 0" can make it look like the executor just
    # started. The title says since when the counts are valid.
    titulo = "workflows"
    if s.contando_ha_s + 1 < s.uptime_s:
        titulo += f" {g.sep} zerado há {_dur(s.contando_ha_s, g)}"
    return _painel(t, titulo, g, linhas=t.row_count)


def _bloco_tempos(s: Snapshot, g: Glyphs) -> Panel:
    t = _kv()
    t.add_row("média", _dur(s.avg_duration_s, g))
    t.add_row("p50 (1h)", _dur(s.p50_duration_s, g))
    t.add_row("p95 (1h)", _dur(s.p95_duration_s, g))

    if s.slowest:
        rid, dur = s.slowest
        t.add_row("+ lento", f"{_curto(rid, g)} {_dur(dur, g)}")
    else:
        t.add_row("+ lento", g.vazio)

    if s.last_finished:
        rid, status, dur = s.last_finished
        cor = {"ok": "green", "error": "red"}.get(status, "dim")
        t.add_row("último", Text(f"{_curto(rid, g)} {status} {_dur(dur, g)}", style=cor))
    else:
        t.add_row("último", g.vazio)

    t.add_row("uptime", _dur(s.uptime_s, g))
    return _painel(t, "tempos", g, linhas=t.row_count)


def _bloco_recursos(s: Snapshot, g: Glyphs) -> Panel:
    t = _kv()

    if s.proc_cpu_pct is None:
        t.add_row("CPU exec", g.vazio)
    else:
        nucleos = f" de {s.cpu_cores:g}" if s.cpu_cores else ""
        t.add_row("CPU exec", Text.assemble(
            f"{s.proc_cpu_pct:5.1f}%{nucleos}  ", _barra((s.proc_cpu_pct_norm or 0) / 100, g),
        ))

    if s.proc_rss_mb is None:
        t.add_row("RAM exec", g.vazio)
    else:
        threads = f" {g.sep} {s.proc_threads} threads" if s.proc_threads else ""
        t.add_row("RAM exec", f"{s.proc_rss_mb:.0f} MB{threads}")

    # "free > total" really happens inside a container: if memory.max
    # exists but memory.current does not, the total comes from the cgroup and the
    # available amount falls back to the HOST's psutil. Showing "34 / 16 GB"
    # would be worse than omitting the total.
    if s.ram_available_gb is not None and s.ram_total_gb and s.ram_available_gb <= s.ram_total_gb:
        t.add_row("RAM livre", Text.assemble(
            f"{s.ram_available_gb:.1f} / {s.ram_total_gb:.1f} GB  ",
            _barra(1 - (s.ram_available_gb / s.ram_total_gb), g),
        ))
    elif s.ram_available_gb is not None:
        t.add_row("RAM livre", f"{s.ram_available_gb:.1f} GB")

    if s.disk_free_gb is not None and s.disk_total_gb:
        t.add_row("Disco", Text.assemble(
            f"{s.disk_free_gb:.0f} / {s.disk_total_gb:.0f} GB  ",
            _barra(1 - (s.disk_free_gb / s.disk_total_gb), g),
        ))
    elif s.disk_free_gb is not None:
        t.add_row("Disco", f"{s.disk_free_gb:.0f} GB livres")

    if s.wf_cpu_peak_pct is not None or s.wf_mem_peak_mb is not None:
        pico = []
        if s.wf_cpu_peak_pct is not None:
            pico.append(f"cpu {s.wf_cpu_peak_pct:.0f}%")
        if s.wf_mem_peak_mb is not None:
            pico.append(f"mem {s.wf_mem_peak_mb:.0f} MB")
        t.add_row("pico nos wf", f" {g.sep} ".join(pico))

    if s.nodes_executed_total:
        falhas = f" {g.sep} {s.nodes_failed_total} falha(s)" if s.nodes_failed_total else ""
        t.add_row("nós", f"{s.nodes_executed_total}{falhas}")

    return _painel(t, "recursos", g, linhas=t.row_count)


def _bloco_fila(s: Snapshot, g: Glyphs) -> Panel:
    t = _kv()

    slots = s.running_count / s.max_concurrent if s.max_concurrent else None
    t.add_row("slots", Text.assemble(f"{s.running_count} / {s.max_concurrent}  ", _barra(slots, g, 8)))

    fila = s.queued / s.max_queue if s.max_queue else None
    t.add_row("fila", Text.assemble(f"{s.queued} / {s.max_queue}  ", _barra(fila, g, 8)))

    if s.outbox_pending:
        t.add_row("outbox", Text(f"{s.outbox_pending} pendente(s)", style="yellow"))

    if s.heartbeat_age_s is None:
        t.add_row("heartbeat", g.vazio)
    else:
        # Sent every 30s (connection._HEARTBEAT_INTERVAL); the server gives up at
        # 90s. Going well past that is the first sign of a silently dead session.
        estilo = "dim" if s.heartbeat_age_s < 45 else ("yellow" if s.heartbeat_age_s < 90 else "red")
        t.add_row("heartbeat", Text(_dur(s.heartbeat_age_s, g), style=estilo))

    reconex = str(s.reconnects)
    if s.next_retry_in_s:
        reconex += f" {g.sep} retry em {_dur(s.next_retry_in_s, g)}"
    t.add_row("reconexões", reconex)

    return _painel(t, "fila & conexão", g, linhas=t.row_count)


def _bloco_execucao(s: Snapshot, g: Glyphs, compacto: bool, maximo: int) -> Bloco:
    t = Table(box=None, expand=True, pad_edge=False, show_edge=False)
    # Fixed widths on the short columns: without them `expand` splits the
    # leftover evenly and the 9-char run_id gets a third of the line.
    t.add_column("run", style="cyan", no_wrap=True, width=12)
    t.add_column("nó atual", overflow="ellipsis", no_wrap=True, ratio=1)
    t.add_column("há", justify="right", no_wrap=True, width=8)
    if not compacto:
        t.add_column("nós", justify="right", no_wrap=True, width=7)

    mostrados = list(s.running)[:maximo]
    for job in mostrados:
        no = job.node or Text("(iniciando)", style="dim")
        linha = [_curto(job.run_id or job.job_id, g), no, _dur(job.elapsed_s, g)]
        if not compacto:
            linha.append(f"{job.nodes_done}/{job.nodes_total or '?'}")
        t.add_row(*linha)

    ocultos = len(s.running) - len(mostrados)
    titulo = f"em execução ({len(s.running)})"
    if ocultos > 0:
        # Truncar em silencio faria o painel mentir sobre quantos jobs rodam.
        titulo += f" {g.sep} +{ocultos} sem espaço"
    return _painel(t, titulo, g, linhas=t.row_count + 1)  # +1 for the table header


def _bloco_geosync(s: Snapshot, g: Glyphs) -> Bloco:
    t = _kv()
    t.add_row(f"{g.sobe} enviado", f"{s.sync_files_up} arq {g.sep} {_bytes(s.sync_bytes_up)}")
    t.add_row(f"{g.desce} baixado", f"{s.sync_files_down} arq {g.sep} {_bytes(s.sync_bytes_down)}")
    if s.sync_errors or s.sync_conflicts:
        t.add_row("problemas", Text(
            f"{s.sync_errors} erro(s) {g.sep} {s.sync_conflicts} conflito(s)", style="yellow",
        ))
    if s.sync_current:
        t.add_row("agora", Text(s.sync_current, style="cyan"))

    pastas = ", ".join(s.sync_dirs)
    return _painel(t, f"geosync {g.sep} {pastas}" if pastas else "geosync", g,
                   linhas=t.row_count)


def _bloco_alertas(s: Snapshot, g: Glyphs, linhas: int) -> Bloco:
    if not s.log_tail:
        return _painel(Text("sem avisos", style="dim"), "alertas", g, linhas=1)

    t = Table.grid(padding=(0, 1))
    t.add_column(style="dim", no_wrap=True)
    t.add_column(no_wrap=True)
    t.add_column(style="dim", no_wrap=True)
    # no_wrap is mandatory: a long message wrapped into 3 physical lines and
    # the computed height did not match the drawn one — the Live scrolling again.
    t.add_column(overflow="ellipsis", no_wrap=True)
    for linha in list(s.log_tail)[-linhas:]:
        cor = "red" if linha.level in ("ERROR", "CRIT") else "yellow"
        t.add_row(linha.ts, Text(linha.level, style=cor), linha.alias, linha.msg)

    resumo = ""
    if s.log_warn_count or s.log_error_count:
        resumo = f" {g.sep} 1h: {s.log_error_count} erro, {s.log_warn_count} aviso"
    return _painel(t, f"alertas{resumo}", g,
                   borda="yellow" if s.log_error_count else "dim",
                   linhas=t.row_count)


def _cabecalho(s: Snapshot, g: Glyphs) -> Bloco:
    # no_wrap on both lines: on a narrow terminal the header wrapped into 3
    # lines and the declared height (4) did not match the drawn one — the Live
    # started scrolling because of a single extra line.
    linha1 = Text.assemble(
        (f"Atlans Executor v{s.version}", "bold"),
        (f"  {g.sep}  ", "dim"),
        (_curto(s.executor_id, g), "cyan"),
        (f"  {g.sep}  ", "dim"),
        (s.server_url, "dim"),
        overflow="ellipsis", no_wrap=True,
    )

    detalhes = [str(s.system.get("hostname") or g.vazio)]
    if s.system.get("container"):
        detalhes.append("container")
    if s.cpu_cores:
        detalhes.append(f"{s.cpu_cores:g} núcleos")

    estado = Text.assemble(
        (f"{_conn_symbol(s.conn_state, g)} {_CONN_LABEL.get(s.conn_state, s.conn_state)}",
         _CONN_COLOR.get(s.conn_state, "red")),
    )
    if s.conn_state == "connected" and s.conn_since_s is not None:
        estado.append(f" há {_dur(s.conn_since_s, g)}", style="dim")

    linha2 = Text.assemble((f" {g.sep} ".join(detalhes), "dim"), ("    ", ""), estado,
                           overflow="ellipsis", no_wrap=True)
    return Bloco(Panel(Group(linha1, linha2), border_style="cyan", box=g.caixa), 4)


# Shortcuts in the footer's priority order: when width runs short, the ones at
# the end go first. `l` is the one the user looks for most (back to the usual
# log) and `?` always stays, because it is how the rest is discovered.
ATALHOS = (
    ("l", "log/painel"),
    ("a", "alertas"),
    ("d", "debug"),
    ("r", "reconecta"),
    ("z", "zera"),
    ("p", "pausa"),
    ("?", "ajuda"),
    ("q", "encerra"),
)
_ATALHOS_ESSENCIAIS = ("l", "?", "q")

AJUDA = (
    ("l  ou  Tab", "alterna entre o painel e o log linha a linha"),
    ("a", "abre a lista completa de alertas"),
    ("d", "liga/desliga o log DEBUG (sem reiniciar)"),
    ("r", "força a reconexão agora, sem esperar o backoff"),
    ("z", "zera os contadores da sessão"),
    ("p", "pausa/retoma a atualização do painel"),
    ("?  ou  h", "mostra/esconde esta ajuda"),
    ("q", "encerra o executor (shutdown gracioso)"),
    ("Ctrl+C", "encerra o executor"),
)


def _rodape(log_path: str, largura: int, atalhos: bool, pausado: bool,
            debug: bool) -> Text:
    """Log path, status indicators and shortcut bar, on a single line.

    The footer cannot wrap into two: the dashboard height counts 1 line for
    it, and one more would make the `Live` scroll. When width runs short, the
    parts go in this order: the log path, then the least-used shortcuts.
    """
    marcas: list[tuple[str, str]] = []
    if debug:
        # Bem visivel: DEBUG multiplica o volume do arquivo, e esquecer ligado
        # enche o disco em silencio.
        marcas.append(("  [DEBUG]", "yellow bold"))
    if pausado:
        marcas.append(("  [PAUSADO]", "yellow bold"))
    custo_marcas = sum(len(t) for t, _ in marcas)

    if not atalhos:
        partes = [("log: ", "dim"), (log_path, "dim cyan"), *marcas]
        dica = "   EXECUTOR_DASHBOARD=off desliga o painel"
        if len("log: ") + len(log_path) + custo_marcas + len(dica) <= largura:
            partes.append((dica, "dim"))
        return Text.assemble(*partes, overflow="ellipsis", no_wrap=True)

    def montar(teclas) -> tuple[list[tuple[str, str]], int]:
        barra: list[tuple[str, str]] = []
        for tecla, rotulo in teclas:
            barra.append((f"  {tecla}", "bold"))
            barra.append((f" {rotulo}", "dim"))
        return barra, sum(len(t) for t, _ in barra)

    # Keeps removing shortcuts from the end until the bar fits with the shortened path.
    mostrados = list(ATALHOS)
    while True:
        barra, custo = montar(mostrados)
        folga = largura - len("log: ") - custo_marcas - custo
        if folga >= 10 or len(mostrados) <= len(_ATALHOS_ESSENCIAIS):
            break
        # Removes the last non-essential one.
        for i in range(len(mostrados) - 1, -1, -1):
            if mostrados[i][0] not in _ATALHOS_ESSENCIAIS:
                mostrados.pop(i)
                break
        else:
            break

    if folga < 6:
        partes = list(marcas)
    elif len(log_path) > folga:
        partes = [("log: ", "dim"), ("…" + log_path[-(folga - 1):], "dim cyan"), *marcas]
    else:
        partes = [("log: ", "dim"), (log_path, "dim cyan"), *marcas]

    partes.extend(barra)
    return Text.assemble(*partes, overflow="ellipsis", no_wrap=True)


def _overlay_ajuda(g: Glyphs) -> Bloco:
    """Shortcut list, shown in place of the body while `?` is active."""
    t = Table.grid(padding=(0, 2))
    t.add_column(style="bold", no_wrap=True)
    t.add_column(no_wrap=True, overflow="ellipsis")
    for tecla, descricao in AJUDA:
        t.add_row(tecla, descricao)
    return _painel(t, "atalhos", g, borda="cyan", linhas=t.row_count)


def _overlay_alertas(s: Snapshot, g: Glyphs, linhas: int) -> Bloco:
    """Historico completo de alertas — o rodape so cabe 6, o buffer guarda 200."""
    if not s.log_tail:
        return _painel(Text("nenhum aviso ou erro registrado", style="dim"),
                       "alertas (histórico)", g, borda="cyan", linhas=1)

    t = Table.grid(padding=(0, 1))
    t.add_column(style="dim", no_wrap=True)
    t.add_column(no_wrap=True)
    t.add_column(style="dim", no_wrap=True)
    t.add_column(overflow="ellipsis", no_wrap=True)
    recentes = list(s.log_tail)[-linhas:]
    for linha in recentes:
        cor = "red" if linha.level in ("ERROR", "CRIT") else "yellow"
        t.add_row(linha.ts, Text(linha.level, style=cor), linha.alias, linha.msg)

    ocultos = len(s.log_tail) - len(recentes)
    titulo = f"alertas {g.sep} {len(s.log_tail)} guardado(s)"
    if ocultos:
        titulo += f", {ocultos} acima da tela"
    return _painel(t, titulo, g, borda="cyan", linhas=t.row_count)


def _empilhar(blocos: list[Bloco]) -> Bloco:
    """Empilha blocos numa coluna; a altura e a soma."""
    grade = Table.grid(expand=True)
    grade.add_column()
    for b in blocos:
        grade.add_row(b.render)
    return Bloco(grade, sum(b.altura for b in blocos))


def _lado_a_lado(colunas: list[list[Bloco]]) -> Bloco:
    """Lays out columns of blocks side by side; the height is the tallest column's."""
    grade = Table.grid(expand=True)
    for _ in colunas:
        grade.add_column(ratio=1)
    empilhadas = [_empilhar(c) for c in colunas]
    grade.add_row(*[e.render for e in empilhadas])
    return Bloco(grade, max(e.altura for e in empilhadas))


def _arranjar_corpo(blocos: list[Bloco], largura: int, orcamento: int) -> Bloco:
    """Picks the shortest arrangement the width allows that fits in the budget.

    Tries, in order, 4 columns / 2x2 / 1 column — each only if the width gives
    every block usable space. If none fits, drops blocks from the end of the
    list (which comes sorted by priority) until it fits.
    """
    def arranjos(bs: list[Bloco]) -> list[Bloco]:
        saida = []
        if largura >= 132 and len(bs) >= 2:
            saida.append(_lado_a_lado([[b] for b in bs]))
        if largura >= 96 and len(bs) >= 2:
            meio = (len(bs) + 1) // 2
            saida.append(_lado_a_lado([bs[:meio], bs[meio:]]))
        saida.append(_empilhar(bs))
        return saida

    restantes = list(blocos)
    while restantes:
        cabem = [a for a in arranjos(restantes) if a.altura <= orcamento]
        if cabem:
            return min(cabem, key=lambda a: a.altura)
        restantes.pop()  # drop the lowest-priority one and try again

    return Bloco(Text(""), 0)


def build(s: Snapshot, *, largura: int, altura: int, log_path: str,
          ascii_only: bool = False, atalhos: bool = False,
          pausado: bool = False, overlay: str | None = None) -> RenderableType:
    """Builds the dashboard within the terminal's line budget.

    rich's `Live` repaints by rewriting N lines upward. If the renderable is
    taller than the terminal, it scrolls endlessly and the dashboard turns into
    garbage — that is why each block declares its height and the layout respects
    the budget, instead of guessing with thresholds.

    Priority when space runs short: header and footer always; alerts never
    disappear (without them the dashboard hides precisely what needs to be seen);
    "running" and geosync go in if there is room left; and the body blocks drop
    in reverse priority order (resources first, workflows last).
    """
    g = ASCII if ascii_only else UNICODE
    compacto = largura < 110

    cabecalho = _cabecalho(s, g)
    # `_nivel_debug` comes from logging itself: that way the indicator cannot
    # diverge from the actual state, even if the toggle is called from elsewhere.
    rodape = _rodape(log_path, largura, atalhos, pausado, _nivel_debug())

    # One alert line is the non-negotiable minimum: it is what keeps the dashboard
    # from hiding an executor stuck in a reconnect loop behind pretty counters.
    orcamento = altura - cabecalho.altura - 1  # -1 for the footer
    if orcamento < 3:
        # Terminal baixo demais ate para o minimo — so cabecalho e rodape.
        return Group(cabecalho.render, rodape)

    # Overlays go in PLACE of the body, not on top of it: truly overlaying
    # would require the terminal's alternate buffer (`screen=True`), which wipes
    # all the boot scrollback — too costly for an auxiliary screen.
    if overlay == "ajuda":
        bloco = _overlay_ajuda(g)
        if bloco.altura <= orcamento:
            return Group(cabecalho.render, bloco.render, rodape)
    elif overlay == "alertas":
        bloco = _overlay_alertas(s, g, linhas=max(1, orcamento - 2))
        if bloco.altura <= orcamento:
            return Group(cabecalho.render, bloco.render, rodape)

    # Order = priority. "Is it healthy?" and "is it saturated?" come before
    # "how much does it consume?".
    corpo_blocos = [
        _bloco_workflows(s, g),
        _bloco_fila(s, g),
        _bloco_tempos(s, g),
        _bloco_recursos(s, g),
    ]
    corpo = _arranjar_corpo(corpo_blocos, largura, orcamento - 3)

    partes: list[Bloco] = [corpo] if corpo.altura else []
    sobra = orcamento - corpo.altura

    # `_ALERTAS_MIN` stays reserved at all times: the optional blocks only get
    # whatever is left after that.
    if s.running and sobra >= _ALERTAS_MIN + _EXEC_MIN:
        # The block costs `mostrados + 3` (table header + 2 borders), so the
        # job ceiling is `sobra - _ALERTAS_MIN - 3`. Getting this math wrong on
        # the optimistic side made the block never fit and vanish from the
        # dashboard without warning.
        cabem = sobra - _ALERTAS_MIN - 3
        exec_bloco = _bloco_execucao(s, g, compacto, maximo=max(1, cabem))
        if exec_bloco.altura <= sobra - _ALERTAS_MIN:
            partes.append(exec_bloco)
            sobra -= exec_bloco.altura

    if s.sync_dirs:
        sync_bloco = _bloco_geosync(s, g)
        if sync_bloco.altura <= sobra - _ALERTAS_MIN:
            partes.append(sync_bloco)
            sobra -= sync_bloco.altura

    partes.append(_bloco_alertas(s, g, linhas=max(1, min(6, sobra - 2))))

    return Group(cabecalho.render, *[p.render for p in partes], rodape)
