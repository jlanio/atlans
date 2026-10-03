# executor/__main__.py
"""
Entry point para `python -m executor`.

Sub-comandos:
  python -m executor                    → inicia o executor (requer enrollment previo)
  python -m executor enroll --otp=... --server=https://... [--cert-dir=./certs]
  python -m executor status [--json]    → consulta o servidor (workspaces acessiveis)
"""
import asyncio
import sys

_SUBCOMANDOS = ("enroll", "status")


def main():
    # First thing: make sure SSL_CERT_FILE points to the internal CA. Idempotent,
    # silent on failure, respects the operator's override. Must come BEFORE
    # the subcommand imports — httpx creates the SSLContext at import time.
    from executor._ca_bootstrap import bootstrap_ca
    bootstrap_ca()

    argv = sys.argv[1:]

    if argv and argv[0] == "enroll":
        from executor.enrollment import _cli_main
        sys.exit(_cli_main(argv[1:]))

    if argv and argv[0] == "status":
        from executor.status_cli import _cli_main as _status_main
        sys.exit(_status_main(argv[1:]))

    # Unknown subcommand: refuse instead of falling through to the default.
    #
    # Without this guard, `python -m executor setup` — which existed until recently
    # and is still in the memory of those who used it — STARTED the executor silently.
    # A command that does something other than what was asked, without warning, is
    # worse than a command that fails.
    if argv and not argv[0].startswith("-"):
        conhecidos = ", ".join(_SUBCOMANDOS)
        print(f"Subcomando desconhecido: {argv[0]!r}", file=sys.stderr)
        print(f"Disponiveis: {conhecidos}", file=sys.stderr)
        sys.exit(2)

    # Default: inicia o executor
    from executor.main import main as agent_main
    try:
        asyncio.run(agent_main())
    except KeyboardInterrupt:
        pass
    finally:
        # Mirrors the `finally` in executor/main.py: if the panel is up, the
        # terminal must be restored to normal on every exit path.
        from executor import dashboard
        dashboard.emergency_stop()


if __name__ == "__main__":
    main()
