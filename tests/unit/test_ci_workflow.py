# tests/unit/test_ci_workflow.py
"""
CI has to run on EVERY pull request, whatever the target.

On 2026-09-15 a PR stacked on top of another — two PRs touching the same four
files, the second opened against the first one's branch — reached
ready-to-merge with **zero checks**. The trigger was
`pull_request: branches: [main]`, so no job was triggered; and GitHub shows a
PR without checks as `clean`, which in the list is indistinguishable from "all
green". The owner asked whether it could be merged, and the honest answer only
showed up because someone went to check.

Retargeting afterwards doesn't fix it: the base change emits `edited`, which is
not among the trigger's default actions (`opened`, `synchronize`, `reopened`).
The only way out was to push a real commit just to wake CI up.

These tests are configuration-consistency tests, in the same spirit as
`test_traefik_config.py` and `test_docs_mcp.py`: cheap in CI, and they cover a
failure no application test reaches — because the failure is the ABSENCE of
tests running.
"""
from __future__ import annotations

import re
from pathlib import Path

# Direct import, and NOT `pytest.importorskip`. PyYAML comes in via `owslib==0.35.0`,
# which is a direct, pinned dependency in `requirements.in` — the Backend job
# installs it and the test really runs. If `owslib` ever goes away, an
# `importorskip` would make this file start BEING SKIPPED silently, and the
# invariant it exists to protect would vanish without any signal. A collection
# error is noisy, and noisy is what you want when a guard stops working.
import yaml

RAIZ = Path(__file__).resolve().parents[2]
CI = RAIZ / ".github" / "workflows" / "ci.yml"
DEPENDABOT = RAIZ / ".github" / "dependabot.yml"
# `.yml` and `.yaml`: GitHub runs both. Local composite actions (there are none
# today) are included because their steps run on the same runner.
WORKFLOWS = sorted([*(RAIZ / ".github" / "workflows").glob("*.y*ml")])
LOCAL_ACTIONS = sorted([*(RAIZ / ".github").glob("actions/**/action.y*ml")])


def _triggers(caminho: Path) -> dict:
    """The `on:` section of a workflow.

    A YAML 1.1 pitfall, which PyYAML implements: unquoted `on` is read as the
    BOOLEAN `True`, not as the string `"on"`. A `carregado["on"]` would give
    `KeyError` and the test would start failing for a reason that isn't its own.
    """
    carregado = yaml.safe_load(caminho.read_text())
    return carregado.get("on") or carregado.get(True)


def test_CI_runs_on_pull_request_to_any_target():
    """The invariant that cost a PR with no checks at all.

    `pull_request:` has to exist and must **not** have `branches`. With a filter,
    a PR against any branch outside the list triggers no job and shows up
    as `clean`.
    """
    gatilhos = _triggers(CI)

    assert "pull_request" in gatilhos, "o CI deixou de rodar em pull request"
    filtro = gatilhos["pull_request"] or {}
    assert "branches" not in filtro, (
        "o gatilho de pull_request voltou a filtrar por branch: um PR aberto "
        f"contra outro alvo ficaria sem CI nenhum. Filtro encontrado: {filtro}"
    )


def test_CI_still_runs_on_push_to_main():
    """The counterpoint: removing the PR filter must not have removed push."""
    on_push = _triggers(CI)["push"]

    assert on_push["branches"] == ["main"]


def test_jobs_are_still_declared_with_the_usual_names():
    """The names the owner checks before merging.

    The assertion is EXACT equality, not substring: with `in`, renaming
    `Backend (Python)` to `Backend2 (Python)` passed — measured by mutation.
    The job name is not a detail here, it is the contract with the reviewer: this
    team's merge criterion is "the four green", checked by name in the PR's list
    — plus the dependency audit, which is informational only (see the next test).
    Renaming is legitimate; renaming without updating this test, and without
    noticing that the reviewer's habit changed along with it, is not.

    The fifth and sixth came in with the extensions (batches E1 and E2 of the
    open-source preparation): "Backend sem extensões (núcleo)" and "Frontend sem
    extensões (núcleo)" run the suites with the extensions deleted, as the free
    distribution runs them, in parallel jobs so as not to lengthen the ones above.
    Since then, "the six green".
    """
    jobs = yaml.safe_load(CI.read_text())["jobs"]
    nomes = {j.get("name", chave) for chave, j in jobs.items()}

    assert nomes == {
        "Secrets scan (detect-secrets)",
        "Backend (Python)",
        "Backend sem extensões (núcleo)",
        "Auditoria de dependências (informativa)",
        "Frontend (Next.js)",
        "Frontend sem extensões (núcleo)",
        "Desktop (typecheck + testes + lock)",
    }, f"os jobs do CI mudaram. Presentes: {sorted(nomes)}"


def test_the_dependency_audit_only_reports():
    """For now it doesn't block: every step of the job, except the setup ones
    (checkout, setup-* and the tools installation), has `continue-on-error`, and
    the job stays green even with a finding — which comes out as a warning and in
    the run summary.

    The rule is by exclusion, not by tool name: a new step that audits another
    way (an action, another scanner) also has to declare the key, or it would
    make the audit blocking without anyone having decided. Removing the key on
    purpose is the decision, and it goes through here.
    """
    job = yaml.safe_load(CI.read_text())["jobs"]["audit"]
    setup_steps = ("actions/checkout@", "actions/setup-python@", "actions/setup-node@")
    audits = [
        passo for passo in job["steps"]
        if not str(passo.get("uses", "")).startswith(setup_steps)
        and passo.get("name") != "Instalar o pip-audit"
    ]

    assert len(audits) >= 4, [p.get("name") for p in audits]
    blocking = [p.get("name") for p in audits if p.get("continue-on-error") is not True]
    assert blocking == [], f"passos que bloqueariam o CI: {blocking}"


def test_dependabot_stays_conservative():
    """A new version at most once a month, and only after 14 days published
    (30 for a major version), in every ecosystem.

    It is the defense against supply-chain attacks: a malicious version is usually
    discovered and pulled within hours or a few days, and whoever updates as soon
    as it comes out is who installs it. Going back to weekly, shortening the
    quarantine or taking a package out of it (`cooldown.exclude`) is a decision,
    and it goes through here. Security fixes don't follow this file (they come via
    "Dependabot security updates"), so they don't wait.
    """
    updates = yaml.safe_load(DEPENDABOT.read_text())["updates"]
    assert updates, "o dependabot.yml ficou sem configuração nenhuma"

    loose = []
    for u in updates:
        nome = f"{u['package-ecosystem']} {u['directory']}"
        intervalo = u["schedule"]["interval"]
        espera = u.get("cooldown") or {}
        padrao = espera.get("default-days", 0)
        if intervalo not in ("monthly", "quarterly", "semiannually", "yearly"):
            loose.append(f"{nome}: intervalo {intervalo}")
        if padrao < 14:
            loose.append(f"{nome}: quarentena de {padrao} dias")
        if espera.get("semver-major-days", padrao) < 30:
            loose.append(f"{nome}: quarentena de versão maior de {espera.get('semver-major-days', padrao)} dias")
        for chave in ("semver-minor-days", "semver-patch-days"):
            if chave in espera and espera[chave] < 14:
                loose.append(f"{nome}: {chave} = {espera[chave]}")
        if espera.get("exclude"):
            loose.append(f"{nome}: fora da quarentena: {espera['exclude']}")

    assert loose == [], loose

    # Dependabot rejects the WHOLE file — and stops proposing updates in every
    # ecosystem — if one of them uses a key it doesn't accept. Measured: for
    # actions, `semver-*-days` gives "The property ... is not supported for the
    # package ecosystem 'github-actions'".
    without_semver = {"github-actions"}
    invalidas = [
        f"{u['package-ecosystem']} {u['directory']}: cooldown.{chave}"
        for u in updates if u["package-ecosystem"] in without_semver
        for chave in (u.get("cooldown") or {}) if chave.startswith("semver-")
    ]
    assert invalidas == [], f"chaves que o Dependabot não aceita: {invalidas}"


def _steps(caminho: Path):
    """Every step of a workflow or of a local composite action — and every job
    that calls a reusable workflow — as GitHub reads them: through the YAML, not
    line by line (`- {uses: ...}`, different indentation and quotes count the same)."""
    doc = yaml.safe_load(caminho.read_text()) or {}
    for nome, job in (doc.get("jobs") or {}).items():
        if job.get("uses"):
            yield nome, {"uses": job["uses"]}
        for passo in job.get("steps") or []:
            yield nome, passo
    for passo in (doc.get("runs") or {}).get("steps") or []:
        yield caminho.parent.name, passo


def test_the_actions_are_pinned_by_sha():
    """Every third-party action goes by commit SHA, with the version in the
    comment (`dono/action@<40 hex> # vX.Y.Z`).

    A tag (`@v4`) can be moved to other code by the action's owner — or by
    whoever steals their account. That was the attack on tj-actions/changed-files,
    in Mar/2025: the tags started pointing to a commit that dumped the runner's
    secrets into the log. A SHA doesn't move. Dependabot updates the SHA and the
    comment together, with the same quarantine as the other dependencies.
    """
    soltas = []
    for arquivo in [*WORKFLOWS, *LOCAL_ACTIONS]:
        texto = arquivo.read_text()
        for job, passo in _steps(arquivo):
            uses = str(passo.get("uses") or "")
            if not uses or uses.startswith("./"):
                continue
            if uses.startswith("docker://"):
                if not re.search(r"@sha256:[0-9a-f]{64}$", uses):
                    soltas.append(f"{arquivo.name}:{job}: {uses} (imagem sem digest)")
            elif not re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", uses):
                soltas.append(f"{arquivo.name}:{job}: {uses}")
            elif not re.search(re.escape(uses) + r"""["']?\s*#\s*v\d+(\.\d+)*\b""", texto):
                soltas.append(f"{arquivo.name}:{job}: {uses} (sem o comentário `# vX.Y.Z`)")
    assert soltas == [], soltas


def test_CI_only_reads_the_repository():
    """In ci.yml the token is read-only, at the top and in each job; in every
    workflow the checkout doesn't keep the token in .git/config. A malicious
    install script (npm, pip) runs inside these jobs: it must not find there a
    credential that can write to the repository."""
    ci = yaml.safe_load(CI.read_text())
    assert ci.get("permissions") == {"contents": "read"}

    def read_only(permissions) -> bool:
        if isinstance(permissions, str):
            return permissions == "read-all"
        return all(valor in ("read", "none") for valor in (permissions or {}).values())

    with_write = [
        f"ci.yml:{nome}: {job['permissions']}"
        for nome, job in ci["jobs"].items()
        if "permissions" in job and not read_only(job["permissions"])
    ]
    assert with_write == [], f"job do CI pedindo mais que leitura: {with_write}"

    with_token = [
        f"{wf.name}:{job}"
        for wf in WORKFLOWS
        for job, passo in _steps(wf)
        if str(passo.get("uses", "")).startswith("actions/checkout@")
        and (passo.get("with") or {}).get("persist-credentials") is not False
    ]
    assert with_token == [], f"checkout guardando o token: {with_token}"


def _commands(run: str):
    """The commands of a `run:` as the shell sees them: a backslash at the end of the
    line joins the next one, comments drop out, and `&&`, `||`, `;`, `|` and line
    breaks separate one command from another."""
    texto = re.sub(r"\\\n", " ", run)
    texto = "\n".join(re.sub(r"(^|\s)#.*$", r"\1", linha) for linha in texto.splitlines())
    for comando in re.split(r"&&|\|\||[;|\n]", texto):
        if comando.strip():
            yield comando.split()


def _eh_pip_install(tokens: list[str]) -> bool:
    """`pip install`, `pip3.12 install`, `python -m pip install`,
    `pip --opção install`, `uv pip install`..."""
    return any(
        re.fullmatch(r"(?:.*/)?pip[\d.]*", token) and "install" in tokens[i + 1 :]
        for i, token in enumerate(tokens)
    )


def test_every_pip_install_in_workflows_checks_hash():
    """No CI/CD `pip install` installs without `--require-hashes` — checked
    command by command, not by line: `pip install --upgrade pip && pip install
    --require-hashes ...` would still let the first one in without a hash. An
    unchecked package, with dependencies at the day's newest version, is precisely
    the door the hashed lockfiles closed. Applies to any new step."""
    soltos = [
        f"{arquivo.name}:{job}: {' '.join(tokens)}"
        for arquivo in [*WORKFLOWS, *LOCAL_ACTIONS]
        for job, passo in _steps(arquivo)
        for tokens in _commands(str(passo.get("run") or ""))
        if _eh_pip_install(tokens) and "--require-hashes" not in tokens
    ]
    assert soltos == [], soltos


def test_pre_commit_hooks_use_the_pinned_tools():
    """The hooks run on the committer's machine. All of them are `repo: local` with
    `language: system`: they use pre-commit, detect-secrets and the
    pre-commit-hooks from requirements-dev.txt (with hashes and quarantine). A
    remote repository — even pinned by SHA — makes pre-commit build its own
    environment, resolving the dependencies from PyPI on the spot and without hashes."""
    config = yaml.safe_load((RAIZ / ".pre-commit-config.yaml").read_text())
    fora = []
    for repo in config["repos"]:
        if repo["repo"] == "meta":
            continue
        if repo["repo"] != "local":
            fora.append(f"repositório remoto: {repo['repo']}")
            continue
        for hook in repo["hooks"]:
            if hook.get("language") not in ("system", "pygrep", "fail"):
                fora.append(f"{hook['id']}: language {hook.get('language')} (monta ambiente próprio)")
            if hook.get("additional_dependencies"):
                fora.append(f"{hook['id']}: additional_dependencies sem trava")
    assert fora == [], fora

    lock_dev = (RAIZ / "requirements-dev.txt").read_text()
    for pacote in ("pre-commit", "detect-secrets", "pre-commit-hooks"):
        assert re.search(rf"^{pacote}==\S+ \\$", lock_dev, re.M), f"{pacote} fora do requirements-dev.txt"


RELEASE_DESKTOP = RAIZ / ".github" / "workflows" / "desktop-windows.yml"


def test_desktop_release_rebuilds_the_runtime_and_isolates_the_secrets():
    """The Python runtime goes, signed, to the user's machine. It must not come
    from the Actions cache (which code from any job on main can poison) — only
    the tarball, which `python:fetch` checks by SHA-256. And the write token and
    the signing secrets only get into the electron-builder step, not into the app
    build (tsc, esbuild, vite: third parties)."""
    passos = [passo for _, passo in _steps(RELEASE_DESKTOP)]

    em_cache = [
        caminho
        for passo in passos
        if str(passo.get("uses", "")).startswith("actions/cache")
        for caminho in str((passo.get("with") or {}).get("path", "")).split()
    ]
    assert em_cache and all(c == "desktop/resources/.cache" for c in em_cache), em_cache

    with_secret = [
        (passo.get("name"), str(passo.get("run")).split(" -- ")[0])
        for passo in passos
        if any("secrets." in str(valor) for valor in (passo.get("env") or {}).values())
    ]
    assert with_secret == [("Gerar o instalador", "npm run empacotar")], with_secret


def test_desktop_release_writes_the_urls_from_repository_variables():
    """The code carries neither the server nor the UI of any installation: the build
    receives them from the repository variables, and the auto-update feed is this
    repository's (each fork publishes and updates in its own releases)."""
    passos = {passo.get("name"): passo for _, passo in _steps(RELEASE_DESKTOP)}

    env = passos["Compilar o app"].get("env") or {}
    assert env.get("ATLANS_DESKTOP_SERVIDOR") == "${{ vars.ATLANS_DESKTOP_SERVIDOR }}"
    assert env.get("ATLANS_DESKTOP_UI_URL") == "${{ vars.ATLANS_DESKTOP_UI_URL }}"

    # The feed goes via env, not via `-c.publish.owner=...` on the command line:
    # the Windows runner's pwsh splits the argument at the first dot, and
    # electron-builder received `-c` and `.publish.owner=...` (broken build).
    gerar = passos["Gerar o instalador"]
    assert (gerar.get("env") or {}).get("ATLANS_RELEASES_DONO") == "${{ github.repository_owner }}"
    assert (gerar.get("env") or {}).get("ATLANS_RELEASES_REPO") == "${{ github.event.repository.name }}"
    assert str(gerar.get("run")).strip() == "npm run empacotar"
    builder = (RAIZ / "desktop" / "electron-builder.yml").read_text(encoding="utf-8")
    assert re.search(r"^  owner: \$\{env\.ATLANS_RELEASES_DONO\}$", builder, re.M)
    assert re.search(r"^  repo: \$\{env\.ATLANS_RELEASES_REPO\}$", builder, re.M)
