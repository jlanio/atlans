# executor/status_cli.py
"""
`python -m executor status --json` subcommand.

Queries `GET /executores/{id}/status` and prints the result as a single JSON
object on stdout.

Exists so the desktop app can list the accessible workspaces without the Node
side reimplementing mTLS. The call requires the executor's certificate, the
internal CA's trust store and the normalization of `wss://` to `https://` — all
already solved in `executor/utils.py` and `_ca_bootstrap.py`. Duplicating that
in TypeScript would be a second authentication implementation to keep up to
date, and the first to diverge when the CA changed.

It is the same data `main.py` uses to decide the GeoSync workspace, so the app
screen shows exactly what the executor will see on the next boot.
"""
from __future__ import annotations

import json
import logging
import sys

logger = logging.getLogger(__name__)

TIMEOUT_S = 15


def _cli_main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="atlans-executor status")
    parser.add_argument(
        "--json", action="store_true",
        help="Emite um unico objeto JSON no stdout (para consumo por programa).",
    )
    args = parser.parse_args(argv)

    # With --json, stdout belongs to the JSON and nothing else.
    logging.basicConfig(
        level=logging.WARNING, format="%(levelname)s %(message)s",
        stream=sys.stderr if args.json else sys.stdout,
    )

    def _emitir(payload: dict, codigo: int) -> int:
        if args.json:
            json.dump(payload, sys.stdout, ensure_ascii=False)
            sys.stdout.write("\n")
            sys.stdout.flush()
        elif payload.get("ok"):
            for ws in payload.get("workspaces", []):
                print(f"  {ws.get('id_hash', '?')}  {ws.get('name', '')}")
        else:
            print(f"FALHA: {payload.get('erro')}", file=sys.stderr)
        return codigo

    from executor import config

    if not config.EXECUTOR_ID:
        return _emitir({"ok": False, "codigo": "config", "erro": "EXECUTOR_ID nao definido."}, 1)
    # Without a server there is no one to ask: it's configuration, not network.
    if not config.SERVER_URL:
        return _emitir({"ok": False, "codigo": "config", "erro": "EXECUTOR_SERVER_URL nao definido."}, 1)

    from pathlib import Path
    if not Path(config.EXECUTOR_CERT_PATH).exists():
        return _emitir(
            {"ok": False, "codigo": "enrollment",
             "erro": f"Certificado nao encontrado em {config.EXECUTOR_CERT_DIR}."}, 1)

    import httpx

    from executor.utils import mtls_httpx_kwargs, ws_to_http

    base_url = ws_to_http(config.SERVER_URL)
    try:
        with httpx.Client(timeout=TIMEOUT_S, follow_redirects=True,
                          **mtls_httpx_kwargs(base_url)) as cliente:
            r = cliente.get(f"{base_url}/executores/{config.EXECUTOR_ID}/status")
    except Exception as exc:
        return _emitir({"ok": False, "codigo": "rede", "erro": f"{type(exc).__name__}: {exc}"}, 1)

    if r.status_code != 200:
        # A 404 here is the same deny that drops the WebSocket connection with close
        # 4404: the executor was removed or revoked on the server.
        codigo = "revoked" if r.status_code in (401, 403, 404) else "http"
        return _emitir(
            {"ok": False, "codigo": codigo,
             "erro": f"O servidor respondeu {r.status_code}.", "status": r.status_code}, 1)

    try:
        dados = r.json()
    except Exception:
        return _emitir({"ok": False, "codigo": "resposta", "erro": "Resposta nao e JSON."}, 1)

    return _emitir({
        "ok": True,
        "executor_id": config.EXECUTOR_ID,
        "server_url": config.SERVER_URL,
        "status": dados.get("status"),
        "workspaces": dados.get("workspaces", []),
    }, 0)
