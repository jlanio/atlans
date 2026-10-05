"""
scripts/executor-local/iniciar.py

Entrypoint of the dev executor (docker-compose.yml, profile executor-local).
Runs in the executor image, as the image's user, and ends by exec-ing
`python -m executor`, the same process an installed executor runs.

What it does before that, in order:

1. Trust. Downloads the internal CA's root (`/executores/ca-bundle`, the public
   endpoint install.sh uses), through traefik-dev's internal HTTP entrypoint,
   into the cert dir as `atlans-root.crt`, where executor/_ca_bootstrap.py
   looks for it. Downloaded on every start, so a recreated CA does not leave a
   stale root behind. The executor never mounts the step-ca volume: it holds
   the CA's private keys, and the executor runs workflow code.

2. MinIO. The API signs upload and download URLs with MINIO_EXTERNAL_ENDPOINT,
   `http://localhost:9000` in dev: right for the browser, but inside this
   container localhost is the container. A small forwarder makes that address
   reach MinIO, through traefik-dev's TCP entrypoint (this container's network
   has only traefik-dev). The signature covers the Host header, which the
   client still sends as localhost:9000, so MinIO accepts it unchanged.

3. Enrollment. executor-local-init (app/services/executor_local_service.py)
   leaves `pedido.json` in the shared folder with the executor id and an OTP.
   This runs `python -m executor enroll` with it through traefik-dev, records
   `cadastrado.json` and deletes the request. With a certificate for the
   executor recorded there, it starts the executor; without one, it waits for
   the next request.

Development only.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

PASTA = Path(os.environ.get("EXECUTOR_LOCAL_PASTA", "/data/matricula"))
CERTS = Path(os.environ.get("EXECUTOR_CERT_DIR", "/data/certs"))
ENV_PATH = Path(os.environ.get("EXECUTOR_ENV_PATH", "/data/executor.env"))
SERVIDOR = os.environ.get("EXECUTOR_SERVER_URL", "wss://agents.localhost")
CA_URL = os.environ.get("EXECUTOR_LOCAL_CA_URL", "http://agents.localhost/executores/ca-bundle")
MINIO = os.environ.get("EXECUTOR_LOCAL_MINIO", "traefik-dev:9000")

PEDIDO = PASTA / "pedido.json"
CADASTRADO = PASTA / "cadastrado.json"


def log(mensagem: str) -> None:
    print(f"[executor-local] {mensagem}", flush=True)


def ler_json(caminho: Path) -> dict:
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return dados if isinstance(dados, dict) else {}


def gravar(caminho: Path, conteudo: bytes, modo: int = 0o600) -> None:
    fd, tmp = tempfile.mkstemp(dir=caminho.parent, prefix=f".{caminho.name}.")
    with os.fdopen(fd, "wb") as f:
        f.write(conteudo)
    os.chmod(tmp, modo)
    os.replace(tmp, caminho)


# ── 1. Trust ──────────────────────────────────────────────────────────────────

def baixar_ca() -> None:
    destino = CERTS / "atlans-root.crt"
    avisou = False
    while True:
        try:
            with urllib.request.urlopen(CA_URL, timeout=10) as resp:
                pem = resp.read()
            if b"BEGIN CERTIFICATE" in pem:
                gravar(destino, pem, 0o644)
                log("CA interna baixada da API.")
                return
            motivo = "resposta sem certificado"
        except (urllib.error.URLError, OSError, ValueError) as exc:
            motivo = str(getattr(exc, "reason", exc))
        if not avisou:
            log(f"aguardando {CA_URL} para baixar a CA interna ({motivo})...")
            avisou = True
        time.sleep(5)


# ── 2. MinIO ──────────────────────────────────────────────────────────────────

def _endereco_local_do_minio() -> int | None:
    """The port to forward when MINIO_EXTERNAL_ENDPOINT points at this machine."""
    valor = os.environ.get("MINIO_EXTERNAL_ENDPOINT", "http://localhost:9000").strip()
    if "://" not in valor:
        valor = "//" + valor
    partes = urlsplit(valor)
    if partes.hostname not in ("localhost", "127.0.0.1", "::1"):
        return None
    return partes.port or (443 if partes.scheme == "https" else 80)


async def _encaminhar(porta: int, destino_host: str, destino_porta: int) -> None:
    async def _copiar(leitor: asyncio.StreamReader, escritor: asyncio.StreamWriter) -> None:
        try:
            while dados := await leitor.read(65536):
                escritor.write(dados)
                await escritor.drain()
        except (ConnectionError, OSError):
            pass
        finally:
            escritor.close()

    async def _atender(leitor: asyncio.StreamReader, escritor: asyncio.StreamWriter) -> None:
        try:
            r2, w2 = await asyncio.open_connection(destino_host, destino_porta)
        except OSError:
            escritor.close()
            return
        await asyncio.gather(_copiar(leitor, w2), _copiar(r2, escritor))

    servidores = []
    for host in ("127.0.0.1", "::1"):
        try:
            servidores.append(await asyncio.start_server(_atender, host, porta))
        except OSError:
            pass  # no IPv6 loopback in this container
    await asyncio.gather(*(s.serve_forever() for s in servidores))


def iniciar_encaminhador() -> None:
    porta = _endereco_local_do_minio()
    if porta is None:
        return
    # A separate process: it has to outlive the exec into the executor below.
    subprocess.Popen([sys.executable, __file__, "--encaminhar", str(porta)])
    log(f"localhost:{porta} encaminhado para {MINIO} (URLs assinadas do MinIO).")


# ── 3. Enrollment ─────────────────────────────────────────────────────────────

def id_no_env() -> str:
    """EXECUTOR_ID as enroll wrote it to the executor's .env."""
    try:
        linhas = ENV_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    for linha in linhas:
        if linha.startswith("EXECUTOR_ID="):
            return linha.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def cadastrar(pedido: dict) -> bool:
    https = "https://" + SERVIDOR.split("://", 1)[-1]
    resultado = subprocess.run(
        [sys.executable, "-m", "executor", "enroll",
         "--executor-id", pedido["executor_id"], "--otp-stdin",
         "--server", https, "--cert-dir", str(CERTS)],
        input=pedido["otp"] + "\n", text=True,
    )
    return resultado.returncode == 0


def principal() -> None:
    PASTA.mkdir(parents=True, exist_ok=True)
    CERTS.mkdir(parents=True, exist_ok=True)
    os.chmod(CERTS, 0o700)

    baixar_ca()
    iniciar_encaminhador()

    falhas = 0
    avisou = False
    while True:
        pedido = ler_json(PEDIDO)
        if pedido.get("executor_id") and pedido.get("otp"):
            log(f"cadastrando o executor {pedido['executor_id']}...")
            if cadastrar(pedido):
                gravar(CADASTRADO, json.dumps({"executor_id": pedido["executor_id"]}).encode())
                PEDIDO.unlink(missing_ok=True)
                log("cadastro concluido.")
                falhas = 0
            else:
                # The OTP may have been burnt: ask for another, and back off so a
                # broken setup does not hit the enrollment rate limit (10/hour).
                PEDIDO.unlink(missing_ok=True)
                falhas += 1
                espera = min(300, 15 * 2 ** (falhas - 1))
                log(f"o cadastro falhou; novo pedido em instantes, nova tentativa em {espera}s.")
                time.sleep(espera)
                continue

        cadastrado = ler_json(CADASTRADO)
        executor_id = cadastrado.get("executor_id")
        if executor_id and (CERTS / "cert.pem").is_file() and id_no_env() == executor_id:
            log(f"iniciando o executor {executor_id}.")
            os.execvp(sys.executable, [sys.executable, "-m", "executor"])

        # Nobody holds a certificate here: forget the record, so that
        # executor-local-init asks for a new enrollment.
        CADASTRADO.unlink(missing_ok=True)
        if not avisou:
            log("aguardando o pedido de cadastro do executor-local-init...")
            avisou = True
        time.sleep(3)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--encaminhar":
        host, _, porta = MINIO.rpartition(":")
        asyncio.run(_encaminhar(int(sys.argv[2]), host or "traefik-dev", int(porta or 9000)))
    else:
        principal()
