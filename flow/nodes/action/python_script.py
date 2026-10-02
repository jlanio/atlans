import asyncio
import ctypes
import io
import os
import sys
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from flow.nodes.base import BaseNode
from flow.registry import register_node
from flow.utils.code_sandbox import (
    build_safe_builtins,
    validate_code_ast,
    UnsafeCodeError,
)
from flow.utils.publisher.events import publish_stdout

# Builtins seguros com __import__ customizado — gerado uma unica vez
_SAFE_BUILTINS = build_safe_builtins()

# Pool DEDICADO ao PythonScript, separado do ThreadPoolExecutor default que
# `asyncio.to_thread` usa — e que TODO no CPU-bound (spatial, to_json, conversao
# de DataFrame) compartilha. `asyncio.to_thread`/o executor NAO cancelam a
# thread: um script em `while True: pass` estoura o `wait_for` do no mas deixa a
# THREAD viva. No pool default, poucas execucoes assim esgotam os workers e
# TRAVAM os demais nos do processo — o executor ja reconhece isto ao isolar o
# plano de controle num pool proprio (ver executor/job_executor.py). Aqui o dano
# fica contido: um laco preso ocupa no maximo os workers do PythonScript, nunca
# os do resto do executor. O interrupt best-effort abaixo ainda tenta devolver o
# worker; a defesa completa (subprocesso matavel) e o follow-up registrado.
_MAX_PYTHONSCRIPT_WORKERS = min(8, (os.cpu_count() or 2) + 2)
_SCRIPT_POOL = ThreadPoolExecutor(
    max_workers=_MAX_PYTHONSCRIPT_WORKERS,
    thread_name_prefix="pythonscript",
)


class _ScriptInterrompido(BaseException):
    """Injetada na thread do script quando o tempo limite estoura.

    Subclasse de BaseException — nao de Exception — para sobreviver a um
    `except Exception` no codigo do usuario e encerrar mesmo um laco que engole
    erros comuns.
    """


def _interromper_thread(future: "Future", ident: Optional[int]) -> bool:
    """Melhor-esforco: injeta _ScriptInterrompido na thread do script no timeout.

    `asyncio.wait_for` so cancela a ESPERA; a thread do exec() segue rodando.
    Para o caso comum de laco puro-Python (`while True: x = 1`) esta injecao
    encerra a thread no proximo bytecode e devolve o worker ao pool. NAO
    interrompe codigo preso em extensao C (um numpy gigante) nem em espera de
    I/O — para esses, o worker so volta ao reiniciar o executor; a defesa
    completa (subprocesso matavel) e o follow-up registrado.

    Seguranca do alvo: `future.done()` e a chamada de injecao correm com o GIL
    RETIDO (`ctypes.pythonapi` nao o libera, e nao ha await entre elas). Se o
    future ainda nao terminou, o worker esta PROVADAMENTE dentro do nosso script
    — nunca numa proxima tarefa do pool, porque o worker so faz dequeue da
    proxima apos `set_result`, que e o que marca `done()`. Assim a interrupcao
    jamais cai numa tarefa alheia.

    Retorna True se a interrupcao foi armada para exatamente uma thread.
    """
    if ident is None or future.done():
        return False
    armadas = ctypes.pythonapi.PyThreadState_SetAsyncExc(
        ctypes.c_long(ident), ctypes.py_object(_ScriptInterrompido)
    )
    if armadas > 1:
        # Nunca deveria acontecer (o ident e unico); se acontecer, desfaz para
        # nao deixar a excecao pendente numa thread errada.
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(ident), None)
        return False
    return armadas == 1


def _descartar_future(f: "Future") -> None:
    """Consome o resultado/excecao de um future orfao (apos o timeout).

    Sem isto, a _ScriptInterrompido que a injecao poe no future viraria
    "Future exception was never retrieved" no log do executor.
    """
    try:
        if not f.cancelled():
            f.exception()
    except BaseException:
        pass


# Janela de agregação do stdout. Um node_event POR LINHA de print() enchia a
# fila de 500 slots do executor — compartilhada por TODOS os jobs e pelo GeoSync
# — e estourava o rate limit de 200 eventos/s do servidor: um
# `for i in range(50000): print(i)` derrubava a telemetria dos outros workflows
# junto. Com lote de 200 ms / 200 linhas o volume cai de 2 a 3 ordens de grandeza
# e o "tempo real" percebido continua o mesmo.
_STDOUT_FLUSH_SECONDS = 0.2
_STDOUT_FLUSH_LINES = 200
# Orçamento de BYTES do lote — e ele fecha ANTES do teto de linhas.
# Contar só linhas era insuficiente: um node_event acima de 64 KB
# (TETO_NODE_EVENT_BYTES em flow/utils/publisher/reducao.py, a regra única do
# executor e do servidor) é reduzido, e das linhas só sobra o prefixo que cabe —
# o painel perdia o lote INTEIRO, em silêncio, sempre que as linhas eram longas
# (`for r in gdf.itertuples(): print(r)`, `print(json.dumps(feature))`).
# 24 KB deixa folga confortável para o overhead de JSON e para escapes (uma
# linha com acentos/aspas pode quase dobrar de tamanho ao ser serializada).
_STDOUT_FLUSH_BYTES = 24 * 1024
# Teto de UMA linha. Acima disso ela sozinha estouraria o frame e levaria junto
# as linhas legítimas do mesmo lote (um `print(gdf.to_json())` de 70 KB matava
# as outras 199). Truncada individualmente, com marcação explícita — nunca em
# silêncio.
_STDOUT_MAX_LINE_CHARS = 8 * 1024
# Teto por execução de nó. Passado ele, o script continua rodando (e o log local
# continua completo), mas o painel recebe um aviso único em vez de um dilúvio.
_STDOUT_MAX_LINES = 5_000


class _LoggingStream(io.TextIOBase):
    """
    Stream que intercepta chamadas de print() e as redireciona para o logger
    do nó e para o publisher, fazendo-as aparecer no terminal da UI.
    Processa linha a linha para respeitar o comportamento padrão de print().

    As linhas são AGRUPADAS antes de virar evento: `publish_fn` recebe uma lista
    de linhas, não uma linha. O lote fecha por BYTES (_STDOUT_FLUSH_BYTES), por
    contagem (_STDOUT_FLUSH_LINES) ou por tempo (_STDOUT_FLUSH_SECONDS), o que
    vier primeiro — nessa ordem de prioridade, porque só o critério de bytes
    impede o evento de passar do teto de 64 KB e ser reduzido aos campos de
    controle no caminho (perda TOTAL do lote, sem aviso). O flush por tempo roda
    num `threading.Timer` porque o script do usuário é dono da thread: sem ele,
    um script que imprime e depois calcula por 10 s só entregaria as linhas no
    fim do nó.
    """

    def __init__(
        self,
        log_fn: Callable[[str], None],
        publish_fn: Callable[[List[str]], None] | None = None,
    ) -> None:
        self._log_fn = log_fn
        self._publish_fn = publish_fn
        self._partial = ""
        # O buffer é tocado pela thread do script E pela thread do timer.
        self._lock = threading.Lock()
        self._buffer: List[str] = []
        # Bytes de texto já acumulados no lote atual (ver _STDOUT_FLUSH_BYTES).
        self._bytes_lote = 0
        self._timer: threading.Timer | None = None
        self._publicadas = 0
        self._truncado = False

    # ── Buffer ───────────────────────────────────────────────────────────────

    @staticmethod
    def _cortar_linha(line: str) -> str:
        """Trunca uma linha isolada grande demais para caber num frame.

        Sem isto um único `print()` de um GeoJSON leva o lote inteiro consigo:
        o evento passa dos 64 KB e chega ao painel sem `extra` nenhum. A marca
        é explícita porque truncar em silêncio faria a saída parecer completa.
        """
        if len(line) <= _STDOUT_MAX_LINE_CHARS:
            return line
        return (
            line[:_STDOUT_MAX_LINE_CHARS]
            + f"…[linha truncada: {len(line)} caracteres; completa no log do executor]"
        )

    def _emit(self, line: str) -> None:
        self._log_fn(line)
        if self._publish_fn is None:
            return
        # O log local (acima) recebe a linha INTEIRA; só o que vai para o painel
        # é cortado.
        linha = self._cortar_linha(line)
        with self._lock:
            self._buffer.append(linha)
            self._bytes_lote += len(linha)
            # Bytes primeiro: é o critério que evita o descarte total do lote.
            cheio = (
                self._bytes_lote >= _STDOUT_FLUSH_BYTES
                or len(self._buffer) >= _STDOUT_FLUSH_LINES
            )
            if not cheio and self._timer is None:
                self._timer = threading.Timer(_STDOUT_FLUSH_SECONDS, self._flush_lote)
                self._timer.daemon = True
                self._timer.start()
        if cheio:
            self._flush_lote()

    def _flush_lote(self) -> None:
        """Fecha o lote atual e publica. Chamado pela thread do script ou pelo timer.

        Publica DENTRO do lock: são duas threads produzindo lotes (a do script,
        quando enche, e a do timer, quando o tempo fecha) e publicar fora dele
        deixaria as linhas chegarem trocadas no painel. O custo é irrelevante —
        publicar é um `call_soon_threadsafe`, não uma ida à rede.
        """
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            if not self._buffer:
                return
            lote = self._buffer
            self._buffer = []
            self._bytes_lote = 0
            restante = _STDOUT_MAX_LINES - self._publicadas
            if restante <= 0:
                if self._truncado:
                    return
                self._truncado = True
                lote = [self._aviso_de_truncagem()]
            elif len(lote) > restante:
                self._truncado = True
                lote = lote[:restante] + [self._aviso_de_truncagem()]
                self._publicadas = _STDOUT_MAX_LINES
            else:
                self._publicadas += len(lote)
            self._publish_fn(lote)  # type: ignore[misc]

    @staticmethod
    def _aviso_de_truncagem() -> str:
        return (
            f"[saída truncada: o nó passou de {_STDOUT_MAX_LINES} linhas impressas; "
            "o restante continua apenas no log do executor]"
        )

    # ── io.TextIOBase ────────────────────────────────────────────────────────

    def write(self, text: str) -> int:
        self._partial += text
        while "\n" in self._partial:
            line, self._partial = self._partial.split("\n", 1)
            if line:  # ignora linhas vazias geradas pelo \n final do print()
                self._emit(line)
        return len(text)

    def flush(self) -> None:
        # Emite conteúdo parcial que não terminou com \n
        if self._partial.strip():
            self._emit(self._partial)
        self._partial = ""
        self._flush_lote()


def _run_script(
    code: str,
    namespace: Dict[str, Any],
    log_fn: Callable[[str], None],
    publish_fn: Callable[[List[str]], None] | None = None,
) -> None:
    """
    Executa o script Python no namespace fornecido com builtins restritos.
    Redireciona stdout para que print() apareça no terminal da UI em tempo real.
    """
    stream = _LoggingStream(log_fn, publish_fn)
    old_stdout = sys.stdout
    try:
        sys.stdout = stream  # type: ignore[assignment]
        namespace["__builtins__"] = _SAFE_BUILTINS
        exec(compile(code, "<PythonScript>", "exec"), namespace)  # noqa: S102
    finally:
        # Restaura o stdout ANTES do flush: se a interrupcao assincrona do
        # timeout (_ScriptInterrompido) cair neste finally, o stdout global ja
        # voltou ao normal — nunca fica preso no stream morto do no. O flush
        # opera sobre o proprio `stream`, nao sobre sys.stdout, entao a ordem
        # nao muda o que e publicado; no maximo o ultimo lote se perde se a
        # thread for morta no meio, o que e aceitavel (o no ja falhou).
        sys.stdout = old_stdout
        # O flush final é obrigatório: sem ele o último lote (e a linha sem \n)
        # morreriam junto com a thread do script.
        stream.flush()


@register_node
class PythonScript(BaseNode):
    """
    Executa um trecho de código Python para transformar ou processar dados.

    Todos os inputs conectados ficam disponíveis como variáveis no escopo do
    script (pelo nome da porta de entrada, conforme definido na edge).

    Bibliotecas disponíveis por padrão: pd, gpd, np, shapely.

    As variáveis listadas em `output_vars` são lidas do namespace ao final da
    execução e retornadas como outputs nomeados.

    Exemplo de script (supondo uma porta de entrada chamada `camadas`):
        gdf = camadas.copy()
        gdf["area_ha"] = gdf.geometry.area / 10_000
        gdf = gdf[gdf["area_ha"] > 5]
        result = gdf
    """

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            "name": "PythonScript",
            "alias": "Script Python",
            "description": (
                "Executa código Python para transformar tabelas ou GeoDataFrames. "
                "Inputs disponíveis como variáveis; defina as variáveis de saída em output_vars."
            ),
            "type": "action",
            "properties": [
                {
                    "name": "code",
                    "label": "Código Python",
                    "type": "code",
                    "default": "# Inputs disponíveis pelo nome da porta de entrada (ex: minha_camada, dados)\n# Bibliotecas: pd, gpd, np, shapely\n\n# result = minha_camada  # substitua pelo nome da sua porta de entrada\nresult = None\n",
                    "description": "Script Python a executar",
                },
                {
                    "name": "output_vars",
                    "label": "Variável de saída",
                    "type": "string",
                    "default": "result",
                    "description": "Variáveis de saída separadas por vírgula (ex: result_a, result_b)",
                },
                {
                    "name": "ports",
                    "label": "Portas de entrada",
                    "type": "ports",
                    "default": [],
                    "description": (
                        "Nome de cada entrada. Vazio: o nó aceita uma conexão e a "
                        "variável recebe o nome da saída do nó anterior. Com DUAS ou "
                        "mais, cada porta vira um ponto de conexão próprio e o nome "
                        "que você der é o nome da variável no script."
                    ),
                },
                {
                    "name": "timeout",
                    "label": "Tempo limite (s)",
                    "type": "integer",
                    "default": 30,
                    "description": "Tempo máximo de execução em segundos",
                },
            ],
            # Entradas DECLARADAS PELO USUARIO, via a propriedade `ports`.
            #
            # Sem isto o no nao consegue receber duas entradas distintas: o nome da
            # variavel vem do `to_key` da aresta, o editor so preenche `to_key`
            # quando o destino declara mais de uma porta, e sem ele o executor cai
            # no `from_key` — que e "output" em praticamente todo no. As duas
            # arestas escrevem na mesma chave e a segunda sobrescreve a primeira.
            #
            # Vazio por padrao: no existente continua com uma porta anonima e as
            # arestas de hoje seguem funcionando exatamente como funcionam.
            "dynamic_inputs": True,
            # Outputs dinamicos — definidos pelo usuario via output_vars
            "dynamic_output": True,
            "outputs": [
                {"name": "result", "type": "any", "description": "Saída padrão do script (tipo depende do código executado)"},
            ],
        }

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()

        code: str = self.parameters.get("code", "")
        output_vars_raw: str = self.parameters.get("output_vars", "result")
        timeout: int = self.get_param_int("timeout", 30)

        if not code.strip():
            raise ValueError("O campo 'code' não pode estar vazio.")

        # ── Validação de segurança (AST) ────────────────────────────
        # Rejeita imports não permitidos e acessos a atributos perigosos
        # ANTES de compilar/executar qualquer código.
        try:
            validate_code_ast(code)
        except UnsafeCodeError as exc:
            raise ValueError(f"Código bloqueado por segurança: {exc}") from exc

        # Nomes das variáveis de saída
        output_var_names: List[str] = [
            v.strip() for v in output_vars_raw.split(",") if v.strip()
        ]
        if not output_var_names:
            raise ValueError("'output_vars' deve conter ao menos um nome de variável.")

        # Monta namespace com inputs nomeados + bibliotecas
        namespace: Dict[str, Any] = {
            "pd": pd,
            "gpd": gpd,
            "np": np,
            "shapely": shapely,
        }

        # Injeta inputs pelo nome real da porta (to_key/from_key definido na edge)
        for key, value in inputs.items():
            namespace[key] = value

        # Constrói callback que publica print() no terminal da UI via Redis
        publisher = self._publisher
        task_id = self._task_id
        node_id = self.node_id

        def _publish_print(linhas: List[str]) -> None:
            """Publica um LOTE de linhas de print() como um evento kind=stdout."""
            publish_stdout(publisher, task_id, node_id, linhas)

        # Executa o script no pool DEDICADO do PythonScript, com tempo limite.
        # self.log é passado como callback para o logger Python;
        # _publish_print roteia print() para o terminal da UI via WebSocket.
        #
        # A thread do script NAO e cancelavel: no timeout nao ha como para-la.
        # Por isso (a) rodamos no _SCRIPT_POOL, que isola o dano de um laco preso
        # dos demais nos, e (b) capturamos o ident da thread para injetar
        # _ScriptInterrompido e tentar devolver o worker ao pool.
        loop = asyncio.get_running_loop()
        estado_thread: Dict[str, int] = {}

        def _executar_script() -> None:
            estado_thread["ident"] = threading.get_ident()
            stdout_antes = sys.stdout
            try:
                _run_script(code, namespace, self.log, _publish_print)
            finally:
                # Rede de seguranca: se _ScriptInterrompido cair no finally de
                # _run_script antes de restaurar o stdout, aqui ele volta. Neste
                # ponto a excecao assincrona ja foi consumida (dispara uma unica
                # vez), entao este finally roda inteiro, sem risco de nova
                # interrupcao — o stdout global nunca fica preso no stream do no.
                if sys.stdout is not stdout_antes:
                    sys.stdout = stdout_antes

        future = loop.run_in_executor(_SCRIPT_POOL, _executar_script)
        # NAO usar asyncio.wait_for: no timeout ele tenta CANCELAR o future e,
        # como a thread do executor ja esta rodando (nao cancelavel), ESPERA a
        # thread terminar — que num `while True` nunca acontece, anulando o
        # proprio timeout. asyncio.wait apenas OBSERVA: no prazo o future fica em
        # `pendentes` e nos o tratamos sem cancelar.
        _, pendentes = await asyncio.wait({future}, timeout=float(timeout))
        if pendentes:
            # add_done_callback so aqui: apenas o caminho orfao (thread ainda
            # viva) precisa descartar a excecao — no caminho normal o
            # future.exception() abaixo ja a consome.
            future.add_done_callback(_descartar_future)
            liberou = _interromper_thread(future, estado_thread.get("ident"))
            self.log(
                "Tempo limite excedido. "
                + (
                    "Thread do script interrompida; worker devolvido ao pool."
                    if liberou
                    else "A thread pode seguir presa (codigo em extensao C ou I/O); "
                    "o worker so volta ao reiniciar o executor."
                )
            )
            raise TimeoutError(
                f"Execução do script excedeu o limite de {timeout} segundos."
            )

        # Concluido dentro do prazo — propaga um erro do script como antes.
        exc = future.exception()
        if exc is not None:
            _libs = {"pd", "gpd", "np", "shapely"}
            available = [k for k in namespace if not k.startswith("__") and k not in _libs]
            hint = f" Inputs disponíveis no namespace: {available}." if available else " Nenhum input foi conectado a este nó."
            raise RuntimeError(f"Erro ao executar script Python: {exc}.{hint}") from exc

        # Coleta variáveis de saída do namespace
        result: Dict[str, Any] = {}
        for var in output_var_names:
            if var not in namespace:
                _libs = {"pd", "gpd", "np", "shapely"}
                available = [k for k in namespace if not k.startswith("__") and k not in _libs]
                hint = f" Variáveis disponíveis: {available}." if available else ""
                raise KeyError(
                    f"Variável de saída '{var}' não foi definida no script.{hint}"
                )
            result[var] = namespace[var]

        return result
