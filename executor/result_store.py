# executor/result_store.py
"""
Store persistente de resultados de jobs pendentes de envio ao servidor.

Motivação: o `_result_queue` do executor é in-memory. Se a conexão WebSocket cai
e o processo do executor reinicia (ex: docker restart, kernel OOM) antes do
`_result_sender_loop` conseguir enviar, o resultado é perdido — o workflow
fica em estado "running" indefinidamente no servidor.

Este módulo oferece uma camada SQLite leve de "outbox":
  - `put(result)`    — persiste o resultado ao produzi-lo
  - `mark_sent(id)`  — remove após o servidor confirmar o recebimento
  - `load_pending()` — no startup do executor, devolve o que nunca foi enviado

Sem dependências adicionais: usa sqlite3 da stdlib em modo WAL para
suportar writes concorrentes entre o executor e o sender_loop.

ROBUSTEZ: qualquer falha (permissão, disco cheio, SQLite corrompido)
desabilita o store silenciosamente — nunca derruba o executor. Todas as
operações viram no-op e o comportamento volta a ser "outbox em memória"
pré-refactor.
"""

import json
import logging
import os
import sqlite3
import threading
import time
from typing import Any

from executor import config
from executor.utils import ocultar_no_windows

logger = logging.getLogger(__name__)


# Nome do outbox em disco. Era `.agent_results.sqlite`, da epoca em que o
# componente se chamava "agent"; renomeado junto com o resto para "executor".
# Sem migracao de proposito: um outbox pendente e trabalho de segundos, e o
# proximo boot recria o arquivo vazio.
_DB_FILENAME = ".executor_results.sqlite"


def _default_db_path() -> str:
    """Caminho do SQLite — em ARTIFACTS_DIR para ficar colocalizado com os artifacts."""
    base = config.ARTIFACTS_DIR or os.getcwd()
    return os.path.join(base, _DB_FILENAME)


_DB_PATH = _default_db_path()

# Sufixos dos arquivos que o SQLite mantem ao lado do banco principal. -wal/-shm
# existem no modo WAL; -journal aparece quando o WAL NAO engata — ex.: o outbox
# numa pasta de rede/sincronizada sem memoria compartilhada, onde o SQLite cai
# SILENCIOSAMENTE para rollback journal e escreve .executor_results.sqlite-journal
# durante cada transacao. Ocultamos os quatro para que nenhum apareca no Explorer.
_DB_SUFIXOS = ("", "-wal", "-shm", "-journal")

# Se ja reaplicamos o hide apos a primeira escrita (ver _ocultar_arquivos_db).
_ocultado_pos_escrita: bool = False


def _ocultar_arquivos_db() -> None:
    """Aplica o atributo oculto (Windows) ao banco e seus arquivos satelite.

    No-op fora do Windows. Os -wal/-shm/-journal nascem em momentos diferentes
    (abertura do WAL, primeira escrita, fallback de rollback): ocultar um que
    ainda nao existe e inofensivo — GetFileAttributesW falha e o helper desiste.
    """
    for sufixo in _DB_SUFIXOS:
        ocultar_no_windows(_DB_PATH + sufixo)


# SQLite aceita múltiplas threads com check_same_thread=False. Usamos um
# RLock (reentrant) para serializar writes — as funções públicas pegam o
# lock e chamam _get_conn() que também precisa pegar o lock para o init
# lazy; com Lock não-reentrante isso deadlockaria no primeiro uso.
_lock = threading.RLock()
_conn: sqlite3.Connection | None = None
# Se a inicialização falhar (permissão, disco cheio, etc.), desabilita o store
# em vez de propagar — o executor continua funcionando sem persistência.
_disabled: bool = False


def _get_conn() -> sqlite3.Connection | None:
    """Retorna a conexão singleton, ou None se o store foi desabilitado.

    Todo init (makedirs + connect + pragma + CREATE) é envolvido em try/except
    genérico: qualquer exceção marca o store como desabilitado em vez de subir.

    SEG: o arquivo é criado com modo 0600 (somente o owner lê/grava).
    Protege payloads persistidos contra leitura por outros processos no host.
    """
    global _conn, _disabled
    if _disabled:
        return None
    if _conn is not None:
        return _conn
    with _lock:
        if _disabled:
            return None
        if _conn is None:
            try:
                parent = os.path.dirname(_DB_PATH) or "."
                os.makedirs(parent, exist_ok=True)
                # Cria o arquivo com 0600 antes de o sqlite3 abrir — se já existe
                # com outra permissão, força o chmod pra fechar o vetor.
                if not os.path.exists(_DB_PATH):
                    fd = os.open(_DB_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    os.close(fd)
                else:
                    try:
                        os.chmod(_DB_PATH, 0o600)
                    except OSError:
                        pass  # filesystems sem suporte a chmod (Windows, etc.)
                c = sqlite3.connect(_DB_PATH, check_same_thread=False, isolation_level=None)
                # WAL: leitores não bloqueiam writers; melhor para outbox pattern.
                c.execute("PRAGMA journal_mode=WAL")
                c.execute("PRAGMA synchronous=NORMAL")
                c.execute("""
                    CREATE TABLE IF NOT EXISTS pending_results (
                        job_id     TEXT PRIMARY KEY,
                        payload    TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        attempts   INTEGER NOT NULL DEFAULT 0
                    )
                """)
                # Diário dos jobs aceitos e ainda SEM resultado (ver
                # `registrar_em_voo`). Só ids e horários: nada do payload.
                c.execute("""
                    CREATE TABLE IF NOT EXISTS jobs_em_voo (
                        job_id TEXT PRIMARY KEY,
                        estado TEXT NOT NULL,
                        desde  REAL NOT NULL
                    )
                """)
                # Oculta o outbox no Windows (no Linux/macOS o ponto ja basta).
                # Fica em ARTIFACTS_DIR (por padrao ~/AtlansExecutor/artifacts, a
                # pasta do proprio executor; o operador pode aponta-la para uma
                # pasta de dados que o usuario navega) e apaga-lo joga fora
                # resultados de jobs ainda nao confirmados pelo servidor. Ocultado
                # DEPOIS do CREATE TABLE porque so ai os -wal/-shm do modo WAL
                # existem; o SQLite reabre arquivos ocultos sem problema (winOpen
                # usa OPEN_EXISTING/OPEN_ALWAYS, nao CREATE_ALWAYS, entao nao
                # esbarra na restricao de oculto do CreateFile). O primeiro put()
                # reaplica para pegar o -wal/-journal que so surge na 1a escrita.
                _ocultar_arquivos_db()
                _conn = c
            except Exception as exc:
                _disabled = True
                logger.warning(
                    "result_store desabilitado — não foi possível inicializar SQLite em %s: %s. "
                    "Resultados não sobreviverão a crash do executor, mas a execução normal continua.",
                    _DB_PATH, exc,
                )
                return None
    return _conn


# Campos seguros para persistir no outbox — OUTPUT e STATS ficam de fora
# porque podem conter credenciais injetadas (connectionString, tokens) ou
# outputs sensíveis (GeoJSON de cliente, dados pessoais).
# O server só consome job_id/run_id/status/error para atualizar o WorkflowRun
# (a duração ele mede pelo próprio relógio) — os demais campos são enviados
# diretamente via WS quando a conexão estiver viva (não passa pelo outbox).
# `error_category` entra porque o replay precisa dela: sem a categoria, a falha
# reenviada no boot chegava ao servidor como "internal" genérico.
_SAFE_RESULT_FIELDS = {"job_id", "run_id", "status", "error", "error_category"}


def _sanitize(result: dict[str, Any]) -> dict[str, Any]:
    """Remove campos sensíveis antes de persistir em disco."""
    out = {k: v for k, v in result.items() if k in _SAFE_RESULT_FIELDS}
    # Trunca error para não inflar o arquivo se vier com stack trace gigante.
    err = out.get("error")
    if isinstance(err, str) and len(err) > 500:
        out["error"] = err[:500] + "…"
    return out


def put(result: dict[str, Any]) -> None:
    """Persiste um resultado — idempotente por job_id.

    Se o mesmo job_id já existe (ex: retry), o payload é substituído.
    Chamar ANTES de enfileirar para o sender — garante que reinício do executor
    não perde o resultado. Nunca lança: falhas apenas logam.
    """
    global _ocultado_pos_escrita
    job_id = str(result.get("job_id") or "unknown")
    try:
        # Sanitiza antes de serializar — outbox NUNCA grava output/stats em disco.
        payload = json.dumps(_sanitize(result), default=str)
    except (TypeError, ValueError) as exc:
        logger.warning("result_store.put: payload não-serializável para job '%s': %s", job_id, exc)
        return
    try:
        with _lock:
            conn = _get_conn()
            if conn is None:
                return
            # Numa transação: o resultado entra no outbox e o job sai do diário
            # juntos. Separados, uma queda entre os dois deixaria no boot um
            # "órfão" que já tem resultado — e o executor reportaria como
            # interrompido um job que terminou. BEGIN/COMMIT explícitos porque a
            # conexão é autocommit (`isolation_level=None`): nela o `with conn`
            # não abre transação nenhuma.
            conn.execute("BEGIN")
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO pending_results (job_id, payload, created_at) "
                    "VALUES (?, ?, ?)",
                    (job_id, payload, time.time()),
                )
                conn.execute("DELETE FROM jobs_em_voo WHERE job_id = ?", (job_id,))
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
            if not _ocultado_pos_escrita:
                # A 1a escrita materializa o -wal/-shm (e, no fallback sem WAL, o
                # -journal) que o CREATE TABLE — no-op quando a tabela ja existe —
                # pode nao ter criado no _get_conn. Reaplicamos UMA vez para pegar
                # esses arquivos recem-nascidos; as gravacoes seguintes nao pagam
                # a syscall.
                _ocultar_arquivos_db()
                _ocultado_pos_escrita = True
    except Exception as exc:
        # Não-fatal: store é um upgrade de robustez, não um requisito.
        logger.warning("result_store.put falhou para job '%s': %s", job_id, exc)


def mark_sent(job_id: str) -> None:
    """Remove o resultado da store após envio bem-sucedido ao servidor."""
    if not job_id:
        return
    try:
        with _lock:
            conn = _get_conn()
            if conn is None:
                return
            conn.execute(
                "DELETE FROM pending_results WHERE job_id = ?",
                (str(job_id),),
            )
    except Exception as exc:
        logger.warning("result_store.mark_sent falhou para job '%s': %s", job_id, exc)


def increment_attempts(job_id: str) -> None:
    """Incrementa o contador de tentativas — útil para logs/telemetria."""
    if not job_id:
        return
    try:
        with _lock:
            conn = _get_conn()
            if conn is None:
                return
            conn.execute(
                "UPDATE pending_results SET attempts = attempts + 1 WHERE job_id = ?",
                (str(job_id),),
            )
    except Exception as exc:
        logger.debug("result_store.increment_attempts: %s", exc)


def load_pending() -> list[dict]:
    """Retorna todos os resultados pendentes, mais antigos primeiro.

    Chamar no startup do executor para drenar e reenfileirar o que não foi
    enviado antes da queda anterior. Nunca lança: falhas retornam [].
    """
    try:
        with _lock:
            conn = _get_conn()
            if conn is None:
                return []
            rows = conn.execute(
                "SELECT payload FROM pending_results ORDER BY created_at ASC"
            ).fetchall()
    except Exception as exc:
        logger.warning("result_store.load_pending falhou: %s", exc)
        return []

    out: list[dict] = []
    for (payload,) in rows:
        try:
            out.append(json.loads(payload))
        except json.JSONDecodeError as exc:
            logger.warning("result_store: payload corrompido, pulando: %s", exc)
    return out


def count_pending() -> int:
    """Quantos resultados aguardam envio. Nunca lança: falhas retornam 0.

    Existe para o painel, que precisa do número a cada poucos segundos e não
    pode usar `load_pending()` — aquele desserializa todos os payloads, o que a
    1 Hz seria desperdício puro.
    """
    try:
        with _lock:
            conn = _get_conn()
            if conn is None:
                return 0
            row = conn.execute("SELECT COUNT(*) FROM pending_results").fetchone()
            return int(row[0]) if row else 0
    except Exception as exc:
        logger.debug("result_store.count_pending: %s", exc)
        return 0


def job_ids_pendentes() -> list[str] | None:
    """Ids com resultado ainda não confirmado pelo servidor. Nunca lança.

    Entra no inventário que o executor manda ao servidor: um job cujo resultado
    está aqui terminou, e o servidor não pode fechar o run como perdido só
    porque ele saiu da fila de execução.

    None quando o outbox existe mas não pôde ser lido (`database is locked`,
    I/O — plausível no desktop, com a pasta sincronizada ou sob antivírus).
    Devolver [] nesse caso afirmaria "nada pendente" e o servidor fecharia como
    perdidos runs cujo resultado está aqui. Outbox desabilitado é [] mesmo: não
    há nada persistido, e a fila em memória é contada por quem chama.
    """
    try:
        with _lock:
            conn = _get_conn()
            if conn is None:
                return []
            rows = conn.execute("SELECT job_id FROM pending_results").fetchall()
        return [r[0] for r in rows]
    except Exception as exc:
        logger.warning("Outbox ilegível ao listar os resultados pendentes: %s", exc)
        return None


# ── Diário dos jobs em voo ────────────────────────────────────────────────────
# Um job aceito entra aqui e só sai quando o resultado dele entra no outbox
# (`put` apaga a linha na mesma transação). O que sobrar no boot é de um
# processo que morreu sem produzir resultado — falta de memória, kill, queda da
# máquina — e vira falha com a causa provável em vez de um run preso em
# "Em andamento" no servidor. Caso real: um executor morto pelo OOM do cgroup
# voltou 6 s depois e ninguém fechou a execução que ele rodava.

ESTADO_NA_FILA = "fila"
ESTADO_EXECUTANDO = "executando"


def registrar_em_voo(job_id: str) -> None:
    """Anota um job aceito na fila local. Nunca lança."""
    if not job_id:
        return
    try:
        with _lock:
            conn = _get_conn()
            if conn is None:
                return
            conn.execute(
                "INSERT OR REPLACE INTO jobs_em_voo (job_id, estado, desde) VALUES (?, ?, ?)",
                (str(job_id), ESTADO_NA_FILA, time.time()),
            )
    except Exception as exc:
        logger.debug("result_store.registrar_em_voo: %s", exc)


def marcar_executando(job_id: str) -> None:
    """O job saiu da fila e começou a rodar. Nunca lança."""
    if not job_id:
        return
    try:
        with _lock:
            conn = _get_conn()
            if conn is None:
                return
            conn.execute(
                "UPDATE jobs_em_voo SET estado = ?, desde = ? WHERE job_id = ?",
                (ESTADO_EXECUTANDO, time.time(), str(job_id)),
            )
    except Exception as exc:
        logger.debug("result_store.marcar_executando: %s", exc)


def carregar_em_voo() -> list[dict]:
    """Jobs do diário que NÃO têm resultado no outbox — os órfãos do processo
    anterior, mais antigos primeiro. Nunca lança: falhas retornam [].

    O `NOT IN` é defesa em profundidade: `put` já apaga a linha na mesma
    transação, mas um banco herdado de uma versão sem essa transação não pode
    fazer um job concluído ser reportado como interrompido.
    """
    try:
        with _lock:
            conn = _get_conn()
            if conn is None:
                return []
            rows = conn.execute(
                "SELECT job_id, estado, desde FROM jobs_em_voo "
                "WHERE job_id NOT IN (SELECT job_id FROM pending_results) "
                "ORDER BY desde ASC"
            ).fetchall()
            conn.execute(
                "DELETE FROM jobs_em_voo WHERE job_id IN (SELECT job_id FROM pending_results)"
            )
    except Exception as exc:
        logger.warning("result_store.carregar_em_voo falhou: %s", exc)
        return []
    return [{"job_id": r[0], "estado": r[1], "desde": r[2]} for r in rows]


# ── Posse do diário ───────────────────────────────────────────────────────────
# Arquivo ao lado do outbox, travado pela vida do processo — ver
# `tomar_posse_do_diario`.
_trava_do_diario = None
_esperando_posse = False
_lock_da_posse = threading.Lock()
_INTERVALO_DE_POSSE_S = 5.0


def _tentar_travar() -> str:
    """'travou', 'ocupada' (outro processo vivo a segura) ou 'sem_suporte'."""
    global _trava_do_diario
    with _lock_da_posse:
        if _trava_do_diario is not None:
            return "travou"
        caminho = _DB_PATH + ".dono"
        try:
            os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
            arquivo = open(caminho, "a+b")
        except OSError as exc:
            logger.debug("Trava do diário indisponível (%s): %s", caminho, exc)
            return "sem_suporte"
        try:
            if os.name == "nt":
                import msvcrt
                arquivo.seek(0)
                msvcrt.locking(arquivo.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(arquivo.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, PermissionError):
            arquivo.close()
            return "ocupada"
        except OSError as exc:
            arquivo.close()
            logger.debug("Trava do diário sem suporte aqui (%s): %s", caminho, exc)
            return "sem_suporte"
        _trava_do_diario = arquivo
    ocultar_no_windows(caminho)
    return "travou"


def _esperar_posse() -> None:
    global _esperando_posse
    try:
        while (resultado := _tentar_travar()) == "ocupada":
            time.sleep(_INTERVALO_DE_POSSE_S)
        if resultado == "travou":
            logger.info("Diário de jobs: posse assumida (o processo anterior saiu).")
    finally:
        _esperando_posse = False


def tomar_posse_do_diario() -> bool:
    """Trava exclusiva do diário para este processo. False se OUTRO processo vivo
    a segura.

    No desktop, o app morto à força deixa o Python filho drenando (até 150 s), e
    a reabertura sobe um segundo processo com o mesmo outbox: os jobs no diário
    são daquele processo, que ainda os está terminando — convertê-los em falha
    faria o resultado verdadeiro dele ser recusado. O sistema operacional solta
    a trava quando o processo morre, de qualquer jeito que morra.

    Sem a trava agora, este processo segue tentando em segundo plano: quando o
    outro sair, ele vira o dono — senão um TERCEIRO que subisse depois pegaria a
    trava livre e converteria os jobs vivos DESTE.

    Sem como travar (plataforma ou sistema de arquivos sem suporte) devolve True:
    o comportamento de antes.
    """
    global _esperando_posse
    if _tentar_travar() != "ocupada":
        return True
    with _lock_da_posse:
        if not _esperando_posse:
            _esperando_posse = True
            threading.Thread(target=_esperar_posse, name="posse-do-diario", daemon=True).start()
    return False


def close() -> None:
    """Fecha a conexão SQLite. Chamar no shutdown do executor."""
    global _conn, _ocultado_pos_escrita
    with _lock:
        if _conn is not None:
            try:
                _conn.close()
            except Exception:
                pass
            _conn = None
        # Re-arma a reocultacao pos-escrita: um reconnect recria os arquivos WAL
        # e precisa escondê-los de novo na primeira gravacao seguinte.
        _ocultado_pos_escrita = False
