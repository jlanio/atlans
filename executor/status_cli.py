# executor/status_cli.py
"""
Subcomando `python -m executor status --json`.

Consulta `GET /executores/{id}/status` e imprime o resultado como um unico
objeto JSON no stdout.

Existe para o app desktop poder listar os workspaces acessiveis sem que o lado
Node reimplemente mTLS. A chamada exige o certificado do executor, o trust store
da CA interna e a normalizacao de `wss://` para `https://` — tudo ja resolvido
em `executor/utils.py` e `_ca_bootstrap.py`. Duplicar isso em TypeScript seria
uma segunda implementacao de autenticacao para manter em dia, e a primeira a
divergir quando a CA mudasse.

E o mesmo dado que `main.py` usa para decidir o workspace do GeoSync, entao a
tela do app mostra exatamente o que o executor vai enxergar no proximo boot.
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

    # Com --json o stdout e do JSON e de mais nada.
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
    # Sem servidor nao ha a quem perguntar: e configuracao, e nao rede.
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
        # 404 aqui e o mesmo deny que derruba a conexao WebSocket com close 4404:
        # o executor foi removido ou revogado no servidor.
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
