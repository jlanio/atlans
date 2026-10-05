"""
app/cli.py
Atlans administrative CLI. Invocation:
    docker compose exec api-prod python -m app.cli <comando> [args]

Available commands:
    create-admin   Creates the first admin user (idempotent).
    executor-local Creates the dev executor and leaves its enrollment request in
                   a folder (development only; see app/services/executor_local_service.py).
    migrar-nos     Rewrites saved workflows with old node names (dry run
                   by default; writes with --aplicar). See app/services/nos_renomeados.py.
"""
from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import re
import sys

# Maintenance commands scan entire tables (`migrar-nos` does a LIKE on the
# text of every workflow and every version): the API's query deadline (60 s,
# app/core/config.py) would cut them off midway. In this process, no deadline — unless
# the operator sets one. Before any import of app.core.
for _env_var in ("DB_STATEMENT_TIMEOUT", "DB_COMMAND_TIMEOUT"):
    os.environ[_env_var] = os.environ.get(_env_var) or "0"


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


async def _create_admin(email: str, password: str, username: str | None) -> int:
    # Lazy imports — so `python -m app.cli --help` does not require a loaded .env.
    from sqlalchemy import select
    from app.core.db import get_session_async
    from app.core.utils.jwt_utils import hash_password
    from app.models.user import User
    from app.models.workspace import Workspace

    if not _EMAIL_RE.match(email):
        print(f"Email invalido: {email}", file=sys.stderr)
        return 2
    if len(password) < 12:
        print("Senha precisa ter pelo menos 12 caracteres.", file=sys.stderr)
        return 2

    derived_username = username or email.split("@", 1)[0]

    async with get_session_async() as db:
        # Idempotent: if an admin with this email already exists, just report it.
        existing = (
            await db.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if existing is not None:
            if existing.role == "admin" and existing.status == "active":
                print(f"Admin com email {email} ja existe (id_hash={existing.id_hash}).")
                return 0
            # User exists but is not admin/active — promote.
            existing.role = "admin"
            existing.status = "active"
            existing.email_verified = True
            existing.hashed_password = hash_password(password)
            await db.commit()
            print(f"Usuario {email} promovido a admin (id_hash={existing.id_hash}).")
            return 0

        user = User(
            username=derived_username,
            email=email,
            hashed_password=hash_password(password),
            role="admin",
            status="active",
            email_verified=True,
        )
        db.add(user)
        await db.flush()

        # Workspace padrao para o admin novo.
        ws = Workspace(
            name=f"Workspace de {user.username}",
            description="Workspace padrao do admin",
            owner_id=user.id_hash,
            is_default=True,
        )
        db.add(ws)
        await db.commit()

        print(f"Admin criado: {email} (id_hash={user.id_hash}).")
        return 0


def _cmd_create_admin(args: argparse.Namespace) -> int:
    email = args.email or input("Email do admin: ").strip()
    password = args.password
    if not password:
        password = getpass.getpass("Senha (>=12 chars): ")
        confirm = getpass.getpass("Confirme a senha: ")
        if password != confirm:
            print("Senhas nao conferem.", file=sys.stderr)
            return 2
    return asyncio.run(_create_admin(email=email, password=password, username=args.username))


async def _migrate_nodes(aplicar: bool) -> int:
    from app.core.db import get_session_async
    from app.services.nos_renomeados import migrate_nodes, disabled_old_names

    async with get_session_async() as db:
        desabilitados = await disabled_old_names(db)
        relatorio = await migrate_nodes(db, aplicar=aplicar)
    if not relatorio:
        print("Nenhuma definicao usa nome antigo de no. Nada a fazer.")
        return 0
    for item in relatorio:
        trocas = ", ".join(f"{antigo} -> {novo} (no {nid})" for nid, antigo, novo in item["trocas"])
        onde = (
            f"workflow {item['workflow']} ({item['nome']})" if item["tipo"] == "workflow"
            else f"versao {item['versao']} do workflow {item['workflow']}"
        )
        print(f"{onde}: {trocas}")
        if item.get("revisar"):
            print(
                f"  REVISAR a mao: no(s) {', '.join(item['revisar'])} ainda citam "
                "drive_file_id (hoje file_id) numa forma que o comando nao reescreve."
            )
    for nome in desabilitados:
        print(
            f"ATENCAO: o admin desabilitou '{nome}'. Depois da migracao esses fluxos rodam "
            "como o no novo, que esta habilitado — desabilite-o em /admin se ainda for a intencao."
        )
    if aplicar:
        print(f"{len(relatorio)} definicao(oes) migrada(s).")
    else:
        # The rewrite is in place: "restore version" does not undo it (the versions
        # are migrated too). The backup is the way back.
        print(
            f"{len(relatorio)} definicao(oes) a migrar. Antes de rodar com --aplicar, guarde as "
            "tabelas (no host, com o DATABASE_URL do .env): "
            "U=$(printf %s \"$DATABASE_URL\" | sed -e 's/+asyncpg//' -e 's/?.*//'); "
            "pg_dump \"$U\" -t workflows -t workflow_versions -F c -f fluxos-antes-de-migrar-nos.dump"
        )
    return 0


def _cmd_migrate_nodes(args: argparse.Namespace) -> int:
    return asyncio.run(_migrate_nodes(aplicar=args.aplicar))


def _cmd_executor_local(args: argparse.Namespace) -> int:
    from pathlib import Path
    from app.services import executor_local_service as local

    pasta = Path(args.dir)
    if args.watch:
        try:
            asyncio.run(local.vigiar(pasta, intervalo=args.interval))
        except KeyboardInterrupt:
            pass
        return 0
    try:
        situacao = asyncio.run(local.provisionar(pasta))
    except Exception as exc:  # noqa: BLE001 — one line instead of a traceback
        print(local.explicar_erro(exc), file=sys.stderr)
        return 1
    print(local.MENSAGENS[situacao])
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli", description="CLI administrativo do Atlans.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_admin = sub.add_parser("create-admin", help="Cria (ou promove) um usuario admin.")
    p_admin.add_argument("--email", help="Email do admin. Se omitido, pergunta interativamente.")
    p_admin.add_argument("--password", help="Senha do admin. Se omitido, pergunta interativamente.")
    p_admin.add_argument("--username", help="Username opcional. Default: parte antes do @ do email.")
    p_admin.set_defaults(func=_cmd_create_admin)

    p_local = sub.add_parser(
        "executor-local",
        help="[Dev] Cria o executor local e grava o pedido de cadastro dele na pasta.",
    )
    p_local.add_argument("--dir", required=True, help="Pasta compartilhada com o container do executor.")
    p_local.add_argument(
        "--watch", action="store_true",
        help="Repete a verificacao para sempre (o container executor-local-init do compose).",
    )
    p_local.add_argument("--interval", type=float, default=15.0, help="Segundos entre verificacoes (com --watch).")
    p_local.set_defaults(func=_cmd_executor_local)

    p_nodes = sub.add_parser(
        "migrar-nos",
        help="Reescreve fluxos salvos que usam nomes antigos de nos (DriveTrigger, ArtifactOutput).",
    )
    p_nodes.add_argument(
        "--aplicar", action="store_true",
        help="Grava as mudancas. Sem ele, so lista o que mudaria.",
    )
    p_nodes.set_defaults(func=_cmd_migrate_nodes)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
