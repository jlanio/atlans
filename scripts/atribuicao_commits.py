#!/usr/bin/env python3
"""scripts/atribuicao_commits.py — the owner's attribution rule, as a check.

Every commit in this repository is the owner's: no co-author trailer naming an
AI agent, no tool footer in commits or PRs, no agent prefix in the branch. The
rule was written down only; this script makes it fail on its own. It is the one
place the rule lives, used by the two entry points:

- the `no-agent-attribution` hook (.pre-commit-config.yaml, `commit-msg`
  stage), which checks the message being committed:

      python scripts/atribuicao_commits.py message .git/COMMIT_EDITMSG

- the `attribution` job in CI (.github/workflows/ci.yml, pull requests only),
  the safety net for whoever did not install the hook. It reads from the
  environment, never from the command line (title and body are untrusted
  input): BASE_SHA and HEAD_SHA (every commit in BASE_SHA..HEAD_SHA, merges
  included), HEAD_REF, PR_TITLE, PR_BODY and PR_AUTHOR:

      python scripts/atribuicao_commits.py pr

Every comparison ignores case. Exits with 1 listing every violation, not only
the first; 0 when everything passes. Standard library only.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# A `Co-Authored-By:` trailer naming any of these is an agent, not a person.
AGENT_TERMS = (
    "claude", "anthropic", "paperclip", "copilot", "codex", "openai",
    "chatgpt", "gemini", "cursor", "devin", "[bot]", "noreply@anthropic.com",
)

# The tool footers and links, in commit messages and in the PR alike.
FOOTER_RULES = (
    (re.compile(r"generated\s+with\s*\[?\s*claude", re.I), "rodapé de ferramenta"),
    (re.compile(r"🤖\s*generated", re.I), "rodapé de ferramenta (emoji de robô)"),
    (re.compile(r"claude\.ai/code", re.I), "link de sessão web do agente"),
)

# Only in the PR's title and body: what the agent's web interface leaves there.
# The rule names are reported, and none of them matches a rule: pasting the
# job's log into a PR body must not break the job.
PR_RULES = (
    (re.compile(r"ccr-projects-attribution", re.I), "marcador oculto de atribuição do agente"),
    (re.compile(r"requested\s+by.*claude\.ai", re.I), "Requested by com link do agente"),
)

TRAILER = re.compile(r"^\s*co-authored-by\s*:", re.I)

# `git commit -v` appends the diff below this line, and git drops it along with
# the comments. Without stopping here, committing a test that quotes a trailer
# would block the commit.
SCISSORS = "# ------------------------ >8 ------------------------"

ALLOWED_AUTHOR_EMAILS = (
    "lanio.morais@gmail.com",
    # Commits made through GitHub's web interface.
    "10765588+jlanio@users.noreply.github.com",
    # Dependabot's PRs must not break.
    "49699333+dependabot[bot]@users.noreply.github.com",
)

AGENT_BRANCH_PREFIXES = ("claude/", "copilot/", "codex/", "cursor/", "agent/", "devin/")

DEPENDABOT = "dependabot[bot]"


def _trailer_violation(linha: str) -> str | None:
    if TRAILER.match(linha):
        baixa = linha.lower()
        termo = next((t for t in AGENT_TERMS if t in baixa), None)
        if termo:
            return f"trailer de co-autoria de agente ({termo})"
    return None


def _line_violations(linha: str, regras) -> list[str]:
    return [nome for padrao, nome in regras if padrao.search(linha)]


def check_message(texto: str, *, strip_comments: bool = False) -> list[str]:
    """The violations in a commit message, one per offending line and rule."""
    achados = []
    for numero, linha in enumerate(texto.splitlines(), 1):
        if strip_comments:
            if linha.startswith(SCISSORS):
                break
            if linha.startswith("#"):
                continue
        regras = [_trailer_violation(linha), *_line_violations(linha, FOOTER_RULES)]
        achados += [f"linha {numero}: {regra}: {linha.strip()}" for regra in regras if regra]
    return achados


def check_pr_text(texto: str) -> list[str]:
    """The violations in a PR's title or body: footers, links and markers."""
    return [
        f"linha {numero}: {regra}"
        for numero, linha in enumerate(texto.splitlines(), 1)
        for regra in _line_violations(linha, FOOTER_RULES + PR_RULES)
    ]


def check_branch(ref: str) -> list[str]:
    prefixo = next((p for p in AGENT_BRANCH_PREFIXES if ref.lower().startswith(p)), None)
    return [f"branch {ref}: prefixo de agente ({prefixo})"] if prefixo else []


def check_author_email(email: str) -> list[str]:
    if email.strip().lower() in ALLOWED_AUTHOR_EMAILS:
        return []
    return [f"e-mail do autor fora da lista: {email}"]


def _git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True, encoding="utf-8",
    ).stdout


def check_commits(base: str, head: str, *, cwd: Path | None = None) -> list[str]:
    """Author e-mail and message of every commit in base..head, merges included.

    The committer's e-mail is not checked: merging through GitHub's web
    interface uses GitHub's own committer.
    """
    achados = []
    for sha in _git("rev-list", f"{base}..{head}", cwd=cwd).split():
        email, _, mensagem = _git("show", "-s", "--format=%ae%x00%B", sha, cwd=cwd).partition("\0")
        curto = sha[:12]
        achados += [f"commit {curto}: {v}" for v in check_author_email(email)]
        achados += [f"commit {curto}: {v}" for v in check_message(mensagem)]
    return achados


def check_pr(env: dict[str, str], *, cwd: Path | None = None) -> list[str]:
    faltando = [nome for nome in ("BASE_SHA", "HEAD_SHA", "HEAD_REF") if not env.get(nome)]
    if faltando:
        return [f"variáveis de ambiente ausentes: {', '.join(faltando)}"]
    achados = check_commits(env["BASE_SHA"], env["HEAD_SHA"], cwd=cwd)
    achados += check_branch(env["HEAD_REF"])
    achados += [f"título do PR: {v}" for v in check_pr_text(env.get("PR_TITLE", ""))]
    # Dependabot's body is third-party content: the Vitest changelog in PR #5
    # mentions "Claude Opus".
    if env.get("PR_AUTHOR", "").lower() != DEPENDABOT:
        achados += [f"corpo do PR: {v}" for v in check_pr_text(env.get("PR_BODY", ""))]
    return achados


def _report(achados: list[str]) -> int:
    if not achados:
        return 0
    anotar = os.environ.get("GITHUB_ACTIONS") == "true"
    print("Atribuição fora da regra do proprietário (CONTRIBUTING, \"6. Pre-commit hooks\"):", file=sys.stderr)
    for achado in achados:
        print(f"::error::{achado}" if anotar else f"  - {achado}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    modos = parser.add_subparsers(dest="modo", required=True)
    mensagem = modos.add_parser("message", help="checa um arquivo de mensagem de commit (hook commit-msg)")
    mensagem.add_argument("arquivo", type=Path)
    modos.add_parser("pr", help="checa commits, branch, título e corpo do PR (CI)")
    args = parser.parse_args(argv)

    if args.modo == "message":
        texto = args.arquivo.read_text(encoding="utf-8", errors="replace")
        return _report(check_message(texto, strip_comments=True))
    return _report(check_pr(dict(os.environ)))


if __name__ == "__main__":
    sys.exit(main())
