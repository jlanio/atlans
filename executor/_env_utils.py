# executor/_env_utils.py
"""
Manipulacao idempotente do executor/.env.

Compartilhado entre `executor.enrollment` (persist EXECUTOR_ID depois do enroll)
e pelo app desktop (gravar config sem destruir envs custom).

Algoritmo:
  - Le linhas com splitlines (preserva comentarios, ordem, linhas vazias).
  - Encontra a primeira linha com `KEY=...` (ignorando comentarios e indentacao).
  - Se existe com mesmo valor: no-op.
  - Se existe com valor diferente: atualiza in-place (mesma posicao).
  - Se nao existe: adiciona ao final.
  - Se o arquivo nao existe: cria com header minimal.

Erros de IO sao loggados como WARNING — nunca levantados — para nao bloquear
flows criticos (ex.: enrollment ja persistiu o cert).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def _sem_export(linha: str) -> str:
    """Remove o prefixo `export ` de uma linha de .env, se houver.

    Ponto unico de proposito: quando so `read_env_var` tolerava `export KEY=`,
    `remove_env_var` deixava de casar a mesma linha que o read reportava — a
    migracao de variavel legada (enrollment.py) virava no-op silencioso, e uma
    linha `export KEY=antigo` convivia com um `KEY=novo` acrescentado depois,
    com o read devolvendo o antigo (primeira ocorrencia vence).
    """
    despido = linha.lstrip()
    if despido.startswith("export "):
        return despido[len("export "):].lstrip()
    return despido


def default_env_path() -> Path:
    """Path padrao do executor/.env, respeitando EXECUTOR_ENV_PATH se setado."""
    from_env = os.getenv("EXECUTOR_ENV_PATH")
    if from_env:
        return Path(from_env)
    # Sobe um nivel a partir deste arquivo (executor/) e usa .env no mesmo dir
    return Path(__file__).parent / ".env"


def persist_env_var(
    key: str,
    value: str,
    env_path: Path | str | None = None,
    file_header: str | None = None,
) -> None:
    """
    Idempotente. Atualiza/adiciona uma variavel de ambiente em `env_path`.

    Args:
        key:        nome da env var (ex.: "EXECUTOR_ID")
        value:      valor (string; sera escrita como `KEY=value` literalmente)
        env_path:   caminho do .env. Se None, usa `default_env_path()`.
        file_header: header opcional para o arquivo se ele for criado do zero
                    (ex.: "# Gerado por executor enroll\n"). Ignorado se ja existe.
    """
    env_path = Path(env_path) if env_path else default_env_path()
    target_line = f"{key}={value}"

    try:
        if env_path.exists():
            lines = env_path.read_text(encoding="utf-8").splitlines()
            for i, line in enumerate(lines):
                # Ignora linhas comentadas e linhas com chaves diferentes
                if line.lstrip().startswith("#") or not line.strip():
                    continue
                # Mesma normalizacao de read/remove: sem ela, um
                # `export KEY=antigo` nao era reconhecido e o persist ACRESCENTAVA
                # `KEY=novo`, deixando as duas linhas — com o read devolvendo a
                # primeira, isto e, a antiga.
                stripped = _sem_export(line)
                if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
                    # Preserva o `export ` que estava na linha: num .env que e
                    # `source`ado — o motivo de alguem escrever `export` —,
                    # troca-lo pela forma nua faria a variavel deixar de chegar
                    # aos processos filhos.
                    prefixo = "export " if line.lstrip().startswith("export ") else ""
                    nova = f"{prefixo}{target_line}"
                    if line == nova:
                        return  # ja igual
                    lines[i] = nova
                    break
            else:
                lines.append(target_line)
            env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        else:
            env_path.parent.mkdir(parents=True, exist_ok=True)
            header = file_header or "# Gerado automaticamente.\n"
            env_path.write_text(f"{header}{target_line}\n", encoding="utf-8")
        logger.info("%s persistido em %s", key, env_path)
    except OSError as exc:
        logger.warning(
            "Nao foi possivel persistir %s em %s: %s. Adicione manualmente: %s",
            key, env_path, exc, target_line,
        )


def remove_env_var(key: str, env_path: Path | str | None = None) -> bool:
    """
    Remove a linha `KEY=...` do .env, se existir. Retorna True se removeu algo.
    Util para limpeza de envs legados (EXECUTOR_API_KEY, EXECUTOR_PRIVATE_KEY_PATH apontando
    para path antigo, etc.) durante migracao.
    """
    env_path = Path(env_path) if env_path else default_env_path()
    if not env_path.exists():
        return False

    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
        kept = []
        removed = False
        for line in lines:
            stripped = _sem_export(line)
            if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
                removed = True
                continue
            kept.append(line)
        if removed:
            env_path.write_text("\n".join(kept) + "\n", encoding="utf-8")
            logger.info("%s removido de %s", key, env_path)
        return removed
    except OSError as exc:
        logger.warning("Nao foi possivel remover %s de %s: %s", key, env_path, exc)
        return False


def normalize_server_url_to_ws(server_url: str) -> str:
    """
    Normaliza a URL do servidor para o scheme WebSocket (`wss://` ou `ws://`).

    O executor abre conexao WebSocket — gravar `https://` em EXECUTOR_SERVER_URL
    quebra o connect com `scheme isn't ws or wss` da lib `websockets`.
    Aceita https/http/wss/ws na entrada; retorna sempre wss/ws.

    Funcoes que recebem `--server=URL` do operador devem chamar isso antes
    de persistir no .env. Os call sites que fazem HTTP (POST /enroll, etc.)
    devem usar `_ws_to_http` para o caminho inverso.
    """
    s = server_url.strip()
    if s.startswith("https://"):
        return "wss://" + s[len("https://"):]
    if s.startswith("http://"):
        return "ws://" + s[len("http://"):]
    # Ja em wss/ws, ou outro scheme — devolve sem mudar.
    return s


def seed_env_from_example(
    env_path: Path | str | None = None,
    example_path: Path | str | None = None,
) -> bool:
    """
    Semeia `env_path` com o conteudo de `example_path` quando ainda nao foi
    configurado.

    Idempotente: se `env_path` ja tem conteudo nao-vazio (linhas com `KEY=valor`
    fora de comentarios), no-op. Se nao existe ou esta vazio/so com comentarios,
    copia o example. E o ponto unico do enroll — manual, do quickstart ou do app
    desktop — para garantir que toda variavel critica (EXECUTOR_SERVER_URL,
    LOG_LEVEL, etc.) tenha valor desde o primeiro boot.

    Returns:
        True se o arquivo foi semeado nesta chamada, False se ja estava OK.
    """
    env_path = Path(env_path) if env_path else default_env_path()
    if example_path is None:
        # O example vive ao lado do CODIGO, nao ao lado do `.env`.
        #
        # Antes o default era `env_path.parent / ".env.example"`, o que so
        # funciona quando o `.env` mora dentro do pacote. Com EXECUTOR_ENV_PATH
        # apontando para outro lugar — `%APPDATA%\AtlasExecutor\config\.env` no
        # app desktop — o example nao existia la e o seed virava no-op
        # silencioso: o `.env` nascia sem EXECUTOR_SYNC_* nem LOG_*,
        # exatamente o cenario que o docstring acima diz querer evitar.
        example_path = Path(__file__).parent / ".env.example"
    else:
        example_path = Path(example_path)

    if not example_path.exists():
        logger.debug(".env.example nao encontrado em %s — pulando seed.", example_path)
        return False

    # Considera o .env "ja configurado" se tem ao menos uma linha nao-comentada
    # com `KEY=...`. Evita sobrescrever arquivo customizado pelo operador.
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                stripped = line.lstrip()
                if not stripped or stripped.startswith("#"):
                    continue
                if "=" in stripped:
                    return False  # ja tem config — preserva
        except OSError as exc:
            logger.warning("Falha ao ler %s para verificar seed: %s", env_path, exc)
            return False

    try:
        env_path.parent.mkdir(parents=True, exist_ok=True)
        env_path.write_text(
            example_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        logger.info(".env semeado a partir de %s", example_path.name)
        return True
    except OSError as exc:
        logger.warning(
            "Nao foi possivel semear %s a partir de %s: %s",
            env_path, example_path, exc,
        )
        return False


def read_env_var(key: str, env_path: Path | str | None = None) -> str | None:
    """Le o valor atual de uma env var do arquivo (sem aplicar no os.environ)."""
    env_path = Path(env_path) if env_path else default_env_path()
    if not env_path.exists():
        return None

    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.lstrip()
            if stripped.startswith("#") or not stripped:
                continue
            stripped = _sem_export(stripped)
            if stripped.startswith(f"{key}="):
                return stripped[len(key) + 1:]
            if stripped.startswith(f"{key} ="):
                return stripped[len(key) + 2:].lstrip()
        return None
    except OSError:
        return None
