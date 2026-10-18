# tests/unit/test_atribuicao_commits.py
"""
The owner's attribution rule (scripts/atribuicao_commits.py).

Every commit is the owner's: no co-author trailer naming an AI agent, no tool
footer in a commit or a PR, no agent prefix in the branch. The script is the
only place the rule lives; the `commit-msg` hook and CI's `attribution` job
both call it, and the last tests here hold those two wirings in place — a hook
that is never installed, or a job that reads the title through `${{ }}` in
`run:`, would leave the rule written down only, which is where it started.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "scripts" / "atribuicao_commits.py"

DONO = "lanio.morais@gmail.com"
AGENT_TRAILER = "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
FOOTER = "🤖 Generated with [Claude Code](https://claude.com/claude-code)"


@pytest.fixture(scope="module")
def atribuicao():
    spec = importlib.util.spec_from_file_location("atribuicao_commits", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _hook(tmp_path: Path, mensagem: str) -> subprocess.CompletedProcess:
    arquivo = tmp_path / "COMMIT_EDITMSG"
    arquivo.write_text(mensagem, encoding="utf-8")
    return subprocess.run(
        ["python", str(SCRIPT), "message", str(arquivo)], capture_output=True, text=True,
    )


# ── Commit message (the hook) ────────────────────────────────────────────────

def test_a_clean_message_passes(tmp_path):
    saida = _hook(tmp_path, "fix: keep the toasts off the field\n\nThe body explains why.\n")
    assert saida.returncode == 0, saida.stderr


def test_an_agent_co_author_trailer_fails_and_says_where(tmp_path):
    saida = _hook(tmp_path, f"chore: x\n\n{AGENT_TRAILER}\n")
    assert saida.returncode == 1
    assert "linha 3" in saida.stderr and "trailer de co-autoria de agente" in saida.stderr


def test_a_human_co_author_passes(atribuicao):
    assert atribuicao.check_message("feat: x\n\nCo-Authored-By: Maria <maria@example.com>\n") == []


@pytest.mark.parametrize("trailer", [
    "co-authored-by: GitHub Copilot <copilot@github.com>",
    "Co-Authored-By: some-app[bot] <1+some-app[bot]@users.noreply.github.com>",
    "CO-AUTHORED-BY: Devin <devin@cognition.ai>",
])
def test_other_agents_and_bots_fail_regardless_of_case(atribuicao, trailer):
    assert atribuicao.check_message(f"feat: x\n\n{trailer}\n")


@pytest.mark.parametrize("rodape", [
    FOOTER,
    "Generated with Claude Code",
    "generated with [claude](https://claude.com)",
])
def test_the_tool_footer_fails(atribuicao, rodape):
    assert atribuicao.check_message(f"feat: x\n\n{rodape}\n")


def test_a_claude_ai_code_url_fails(atribuicao):
    assert atribuicao.check_message("feat: x\n\nhttps://claude.ai/code/session_123\n")


def test_comment_lines_pass_git_removes_them(tmp_path):
    saida = _hook(tmp_path, "feat: x\n\n# Co-Authored-By: Claude\n# Please enter the commit message\n")
    assert saida.returncode == 0, saida.stderr


def test_the_diff_below_the_scissors_is_not_checked(tmp_path):
    """`git commit -v`: committing this very file must not be refused."""
    mensagem = (
        "test: x\n\n"
        "# ------------------------ >8 ------------------------\n"
        "# Do not modify or remove the line above.\n"
        f"+AGENT_TRAILER = \"{AGENT_TRAILER}\"\n"
    )
    saida = _hook(tmp_path, mensagem)
    assert saida.returncode == 0, saida.stderr


def test_every_violation_is_listed_not_only_the_first(atribuicao):
    achados = atribuicao.check_message(f"feat: x\n\nGenerated with Claude Code\n\n{AGENT_TRAILER}\n")
    assert [a.split(":")[0] for a in achados] == ["linha 3", "linha 5"], achados


# ── Branch, title and body (CI) ──────────────────────────────────────────────

def test_an_agent_branch_fails_and_the_owners_passes(atribuicao):
    assert atribuicao.check_branch("claude/x")
    assert atribuicao.check_branch("Copilot/x")
    assert atribuicao.check_branch("to/x") == []


def test_a_body_with_a_claude_ai_code_link_fails(atribuicao):
    assert atribuicao.check_pr_text("Resumo\n\nhttps://claude.ai/code/project/abc\n")


@pytest.mark.parametrize("corpo", [
    "<!-- ccr-projects-attribution -->",
    "Requested by [jlanio](https://claude.ai/user/1)",
    FOOTER,
])
def test_the_agent_interface_marks_in_the_body_fail(atribuicao, corpo):
    assert atribuicao.check_pr_text(f"Resumo\n\n{corpo}\n")


# ── Commits of the PR (CI), in a real repository ─────────────────────────────

def _git(repo: Path, *args: str) -> str:
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    identidade = ["-c", "user.name=Autor", "-c", f"user.email={DONO}"]
    return subprocess.run(
        ["git", *identidade, *args], cwd=repo, env=env, check=True, capture_output=True, text=True,
    ).stdout.strip()


def _commit(repo: Path, mensagem: str, email: str = DONO) -> None:
    # `--author`, not GIT_AUTHOR_EMAIL: some git wrappers replace the identity
    # variables, and `--author` beats them.
    _git(repo, "commit", "-q", "--allow-empty", f"--author=Autor <{email}>", "-m", mensagem)


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q", "-b", "main")
    _commit(tmp_path, "base")
    return tmp_path


def _pr(repo: Path, **extra) -> dict[str, str]:
    """The job's environment for the PR base..HEAD; BASE_SHA comes in `extra`."""
    return {
        "HEAD_SHA": _git(repo, "rev-parse", "HEAD"),
        "HEAD_REF": "to/x", "PR_TITLE": "feat: x", "PR_BODY": "", "PR_AUTHOR": "jlanio",
        **extra,
    }


def test_the_owners_commits_pass(atribuicao, repo):
    base = _git(repo, "rev-parse", "HEAD")
    _commit(repo, "feat: x")
    _commit(repo, "fix: y", email="10765588+jlanio@users.noreply.github.com")
    assert atribuicao.check_pr(_pr(repo, BASE_SHA=base), cwd=repo) == []


def test_an_author_outside_the_list_fails(atribuicao, repo):
    base = _git(repo, "rev-parse", "HEAD")
    _commit(repo, "feat: x", email="agente@example.com")
    achados = atribuicao.check_pr(_pr(repo, BASE_SHA=base), cwd=repo)
    assert len(achados) == 1 and "agente@example.com" in achados[0], achados


def test_a_merge_commit_is_checked_too(atribuicao, repo):
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", "-b", "lado")
    _commit(repo, "feat: lado")
    _git(repo, "checkout", "-q", "main")
    _commit(repo, "feat: main")
    _git(repo, "merge", "-q", "--no-ff", "lado", "-m", f"Merge lado\n\n{AGENT_TRAILER}")
    achados = atribuicao.check_pr(_pr(repo, BASE_SHA=base), cwd=repo)
    assert len(achados) == 1 and "trailer" in achados[0], achados


def test_the_cli_lists_branch_title_and_commit_together(repo):
    base = _git(repo, "rev-parse", "HEAD")
    _commit(repo, f"chore: x\n\n{AGENT_TRAILER}")
    env = {**os.environ, **_pr(repo, BASE_SHA=base, HEAD_REF="claude/x", PR_TITLE=FOOTER)}
    env.pop("GITHUB_ACTIONS", None)
    saida = subprocess.run(
        ["python", str(SCRIPT), "pr"], cwd=repo, env=env, capture_output=True, text=True,
    )
    assert saida.returncode == 1
    for trecho in ("trailer de co-autoria", "branch claude/x", "título do PR"):
        assert trecho in saida.stderr, saida.stderr


def test_dependabots_body_is_third_party_content(atribuicao, repo):
    """The Vitest changelog in PR #5 mentions Claude; the title is still checked."""
    base = _git(repo, "rev-parse", "HEAD")
    _commit(repo, "chore(deps): bump vitest", email="49699333+dependabot[bot]@users.noreply.github.com")
    corpo = "Release notes\n\n- Fixes found with Claude Opus. Generated with Claude Code\n"
    env = _pr(repo, BASE_SHA=base, HEAD_REF="dependabot/npm/vitest", PR_BODY=corpo, PR_AUTHOR="dependabot[bot]")
    assert atribuicao.check_pr(env, cwd=repo) == []
    assert atribuicao.check_pr({**env, "PR_AUTHOR": "jlanio"}, cwd=repo)


# ── The wirings ──────────────────────────────────────────────────────────────

def test_pre_commit_install_also_installs_the_commit_msg_hook():
    config = yaml.safe_load((RAIZ / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    assert "commit-msg" in config["default_install_hook_types"]

    hooks = {h["id"]: h for repo in config["repos"] for h in repo["hooks"]}
    assert hooks["no-agent-attribution"]["stages"] == ["commit-msg"]
    assert hooks["no-agent-attribution"]["entry"] == "python scripts/atribuicao_commits.py message"
    # Without `stages`, a hook also runs on the commit message.
    sem_estagio = [i for i, h in hooks.items() if i != "no-agent-attribution" and "commit-msg" in h.get("stages", ["commit-msg"])]
    assert sem_estagio == [], sem_estagio


def test_the_ci_job_reads_the_pr_through_env_only():
    job = yaml.safe_load((RAIZ / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))["jobs"]["attribution"]
    assert job["if"] == "github.event_name == 'pull_request'"

    checkout, *_, verificacao = job["steps"]
    assert checkout["with"]["fetch-depth"] == 0
    assert verificacao["run"] == "python scripts/atribuicao_commits.py pr"
    assert {"BASE_SHA", "HEAD_SHA", "HEAD_REF", "PR_TITLE", "PR_BODY", "PR_AUTHOR"} <= set(verificacao["env"])
    interpolados = [p.get("name") for p in job["steps"] if "${{" in str(p.get("run", ""))]
    assert interpolados == [], f"entrada do PR interpolada em run: {interpolados}"
