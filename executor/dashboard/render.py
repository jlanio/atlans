# executor/dashboard/render.py
"""
Desenho do painel. Funcao pura: Snapshot entra, renderavel do rich sai.

Separado do runtime de proposito — assim da para renderizar um Snapshot
sintetico num Console de largura fixa dentro de um teste, sem event loop e sem
terminal.

Todo glifo nao-ASCII passa pelo objeto `Glyphs`. Nao e preciosismo: o conhost
legado do Windows usa a code page ANSI (cp1252 em pt-BR) e levanta
UnicodeEncodeError no primeiro '●' — o painel morreria no primeiro quadro.
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

# Altura minima do bloco de alertas (1 linha + 2 bordas). Reservada sempre: sem
# ela o painel esconderia justamente o que precisa ser visto.
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
    """O root logger esta em DEBUG? Lido na hora, para o indicador do rodape
    nao poder divergir do estado real do logging."""
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
    """Duracao legivel. Escala a unidade em vez de mostrar '4821.3s'."""
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
    """Barra de proporcao colorida por faixa: verde ate 70%, amarelo ate 90%, vermelho."""
    if fracao is None:
        return Text(g.vazio, style="dim")
    f = max(0.0, min(1.0, fracao))
    cheio = int(round(f * largura))
    cor = "green" if f < 0.7 else ("yellow" if f < 0.9 else "red")
    return Text(g.barra_cheia * cheio, style=cor) + Text(g.barra_vazia * (largura - cheio), style="dim")


def _kv() -> Table:
    """Grade de duas colunas — o formato 'rotulo / valor' dos blocos."""
    t = Table.grid(padding=(0, 1))
    t.add_column(style="dim", no_wrap=True)
    t.add_column(no_wrap=True)
    return t


class Bloco(NamedTuple):
    """Renderavel com a sua altura em linhas.

    A altura tem que ser conhecida ANTES de desenhar: o `Live` do rich reescreve
    N linhas para cima a cada quadro, e se N passar da altura do terminal o
    painel rola sem parar — vira lixo continuo em vez de um quadro estavel.
    Todo bloco usa colunas `no_wrap`, entao uma linha logica e sempre uma linha
    fisica e a contagem fecha.
    """
    render: RenderableType
    altura: int


def _painel(corpo, titulo: str, g: Glyphs, borda: str = "dim", linhas: int = 0) -> Bloco:
    p = Panel(corpo, title=titulo, title_align="left", border_style=borda, box=g.caixa)
    return Bloco(p, linhas + 2)  # +2 das bordas superior e inferior


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

    # Depois de um 'z', "total 0" pode fazer parecer que o executor acabou de
    # subir. O titulo diz desde quando as contagens valem.
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

    # "livre > total" acontece de verdade dentro de container: se memory.max
    # existe mas memory.current nao, o total vem do cgroup e o disponivel cai
    # no psutil do HOST. Mostrar "34 / 16 GB" seria pior que omitir o total.
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
        # Sai a cada 30s (connection._HEARTBEAT_INTERVAL); o servidor desiste aos
        # 90s. Passar muito disso e o primeiro sinal de sessao morta sem aviso.
        estilo = "dim" if s.heartbeat_age_s < 45 else ("yellow" if s.heartbeat_age_s < 90 else "red")
        t.add_row("heartbeat", Text(_dur(s.heartbeat_age_s, g), style=estilo))

    reconex = str(s.reconnects)
    if s.next_retry_in_s:
        reconex += f" {g.sep} retry em {_dur(s.next_retry_in_s, g)}"
    t.add_row("reconexões", reconex)

    return _painel(t, "fila & conexão", g, linhas=t.row_count)


def _bloco_execucao(s: Snapshot, g: Glyphs, compacto: bool, maximo: int) -> Bloco:
    t = Table(box=None, expand=True, pad_edge=False, show_edge=False)
    # Larguras fixas nas colunas curtas: sem elas o `expand` reparte a sobra
    # igualmente e o run_id de 9 chars ganha um terco da linha.
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
    return _painel(t, titulo, g, linhas=t.row_count + 1)  # +1 do cabecalho da tabela


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
    # no_wrap obrigatorio: uma mensagem longa quebrava em 3 linhas fisicas e a
    # altura calculada nao batia com a desenhada — de novo o Live rolando.
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
    # no_wrap nas duas linhas: em terminal estreito o cabecalho quebrava em 3
    # linhas e a altura declarada (4) nao batia com a desenhada — o Live
    # passava a rolar por causa de uma unica linha a mais.
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


# Atalhos na ordem de prioridade do rodape: quando falta largura, os do fim
# saem primeiro. `l` e o que o usuario mais procura (voltar ao log de sempre) e
# `?` sempre fica, porque e por ele que se descobre o resto.
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
    """Caminho do log, indicadores de estado e barra de atalhos, numa linha so.

    O rodape nao pode quebrar em duas: a altura do painel conta 1 linha para
    ele, e uma a mais faria o `Live` rolar. Quando falta largura, as partes
    saem nesta ordem: caminho do log, depois os atalhos menos usados.
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

    # Vai tirando atalhos do fim ate a barra caber com o caminho encurtado.
    mostrados = list(ATALHOS)
    while True:
        barra, custo = montar(mostrados)
        folga = largura - len("log: ") - custo_marcas - custo
        if folga >= 10 or len(mostrados) <= len(_ATALHOS_ESSENCIAIS):
            break
        # Remove o ultimo nao-essencial.
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
    """Lista de atalhos, mostrada no lugar do corpo enquanto `?` estiver ativo."""
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
    """Distribui colunas de blocos lado a lado; a altura e a da coluna mais alta."""
    grade = Table.grid(expand=True)
    for _ in colunas:
        grade.add_column(ratio=1)
    empilhadas = [_empilhar(c) for c in colunas]
    grade.add_row(*[e.render for e in empilhadas])
    return Bloco(grade, max(e.altura for e in empilhadas))


def _arranjar_corpo(blocos: list[Bloco], largura: int, orcamento: int) -> Bloco:
    """Escolhe o arranjo mais baixo que a largura comporta e que cabe no orcamento.

    Tenta, em ordem, 4 colunas / 2x2 / 1 coluna — cada um so se a largura der
    espaco util a cada bloco. Se nenhum couber, descarta blocos do fim da lista
    (que vem ordenada por prioridade) ate caber.
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
        restantes.pop()  # sai o de menor prioridade e tenta de novo

    return Bloco(Text(""), 0)


def build(s: Snapshot, *, largura: int, altura: int, log_path: str,
          ascii_only: bool = False, atalhos: bool = False,
          pausado: bool = False, overlay: str | None = None) -> RenderableType:
    """Monta o painel dentro do orcamento de linhas do terminal.

    O `Live` do rich repinta reescrevendo N linhas para cima. Se o renderavel
    for mais alto que o terminal, ele rola sem parar e o painel vira lixo — por
    isso cada bloco declara a sua altura e a montagem respeita o orcamento, em
    vez de adivinhar por limiares.

    Prioridade quando falta espaco: cabecalho e rodape sempre; alertas nunca
    somem (sem eles o painel esconde justamente o que precisa ser visto);
    "em execucao" e geosync entram se sobrar; e os blocos do corpo caem na
    ordem inversa da prioridade (recursos primeiro, workflows por ultimo).
    """
    g = ASCII if ascii_only else UNICODE
    compacto = largura < 110

    cabecalho = _cabecalho(s, g)
    # `_nivel_debug` sai do proprio logging: assim o indicador nao pode
    # divergir do estado real, mesmo se o toggle for chamado de outro lugar.
    rodape = _rodape(log_path, largura, atalhos, pausado, _nivel_debug())

    # Uma linha de alerta e o minimo inegociavel: e o que impede o painel de
    # esconder um executor em loop de reconexao atras de contadores bonitos.
    orcamento = altura - cabecalho.altura - 1  # -1 do rodape
    if orcamento < 3:
        # Terminal baixo demais ate para o minimo — so cabecalho e rodape.
        return Group(cabecalho.render, rodape)

    # Os overlays entram no LUGAR do corpo, e nao por cima: sobrepor de verdade
    # exigiria o buffer alternativo do terminal (`screen=True`), que apaga todo
    # o scrollback do boot — caro demais para uma tela auxiliar.
    if overlay == "ajuda":
        bloco = _overlay_ajuda(g)
        if bloco.altura <= orcamento:
            return Group(cabecalho.render, bloco.render, rodape)
    elif overlay == "alertas":
        bloco = _overlay_alertas(s, g, linhas=max(1, orcamento - 2))
        if bloco.altura <= orcamento:
            return Group(cabecalho.render, bloco.render, rodape)

    # Ordem = prioridade. "Esta saudavel?" e "esta saturado?" vem antes de
    # "quanto consome?".
    corpo_blocos = [
        _bloco_workflows(s, g),
        _bloco_fila(s, g),
        _bloco_tempos(s, g),
        _bloco_recursos(s, g),
    ]
    corpo = _arranjar_corpo(corpo_blocos, largura, orcamento - 3)

    partes: list[Bloco] = [corpo] if corpo.altura else []
    sobra = orcamento - corpo.altura

    # `_ALERTAS_MIN` fica reservado o tempo todo: os blocos opcionais so entram
    # com o que sobrar depois disso.
    if s.running and sobra >= _ALERTAS_MIN + _EXEC_MIN:
        # O bloco custa `mostrados + 3` (cabecalho da tabela + 2 bordas), entao o
        # teto de jobs e `sobra - _ALERTAS_MIN - 3`. Errar essa conta pelo lado
        # otimista fazia o bloco nunca caber e sumir do painel sem aviso.
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
