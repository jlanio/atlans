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
    # 1a coisa: garante SSL_CERT_FILE apontando pra CA interna. Idempotente,
    # silencioso em falha, respeita override do operador. Precisa vir ANTES
    # dos imports dos sub-comandos — httpx cria SSLContext no import.
    from executor._ca_bootstrap import bootstrap_ca
    bootstrap_ca()

    argv = sys.argv[1:]

    if argv and argv[0] == "enroll":
        from executor.enrollment import _cli_main
        sys.exit(_cli_main(argv[1:]))

    if argv and argv[0] == "status":
        from executor.status_cli import _cli_main as _status_main
        sys.exit(_status_main(argv[1:]))

    # Subcomando desconhecido: recusa em vez de cair no default.
    #
    # Sem esta guarda, `python -m executor setup` — que existiu ate pouco tempo
    # e ainda esta na memoria de quem usava — INICIAVA o executor em silencio.
    # Um comando que faz algo diferente do que foi pedido, sem avisar, e pior
    # que um comando que falha.
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
        # Espelha o `finally` de executor/main.py: se o painel estiver no ar,
        # o terminal precisa voltar ao normal por qualquer caminho de saida.
        from executor import dashboard
        dashboard.emergency_stop()


if __name__ == "__main__":
    main()
