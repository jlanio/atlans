# tests/unit/test_ci_workflow.py
"""
O CI tem de rodar em TODO pull request, qualquer que seja o alvo.

Em 15/09/2026 um PR empilhado sobre outro — dois PRs tocando os mesmos quatro
arquivos, o segundo aberto contra a branch do primeiro — chegou a
pronto-para-mesclar com **zero verificações**. O gatilho era
`pull_request: branches: [main]`, então nenhum job foi acionado; e o GitHub
mostra um PR sem checks como `clean`, que na lista é indistinguível de "tudo
verde". O dono perguntou se podia mesclar, e a resposta honesta só apareceu
porque alguém foi conferir.

Retargetear depois não resolve: a mudança de base emite `edited`, que não está
nas ações padrão do gatilho (`opened`, `synchronize`, `reopened`). A única
saída era empurrar um commit de verdade só para acordar o CI.

Estes testes são de coerência de configuração, no mesmo espírito de
`test_traefik_config.py` e `test_docs_mcp.py`: baratos em CI, e cobrem uma
falha que nenhum teste de aplicação alcança — porque a falha é a AUSÊNCIA de
testes rodando.
"""
from __future__ import annotations

import re
from pathlib import Path

# Import direto, e NÃO `pytest.importorskip`. PyYAML chega pelo `owslib==0.35.0`,
# que é dependência direta e pinada do `requirements.in` — o job Backend o
# instala e o teste roda de verdade. Se um dia o `owslib` sair, um
# `importorskip` faria este arquivo passar a SER PULADO em silêncio, e a
# invariante que ele existe para proteger sumiria sem sinal nenhum. Um erro de
# coleta é barulhento, e barulhento é o que se quer quando um guarda para de
# funcionar.
import yaml

RAIZ = Path(__file__).resolve().parents[2]
CI = RAIZ / ".github" / "workflows" / "ci.yml"
DEPENDABOT = RAIZ / ".github" / "dependabot.yml"
# `.yml` e `.yaml`: o GitHub roda os dois. As actions compostas locais (hoje não
# há nenhuma) entram porque os passos delas rodam no mesmo runner.
WORKFLOWS = sorted([*(RAIZ / ".github" / "workflows").glob("*.y*ml")])
ACOES_LOCAIS = sorted([*(RAIZ / ".github").glob("actions/**/action.y*ml")])


def _gatilhos(caminho: Path) -> dict:
    """A seção `on:` de um workflow.

    Cuidado do YAML 1.1, que o PyYAML implementa: `on` sem aspas é lido como o
    BOOLEANO `True`, não como a string `"on"`. Um `carregado["on"]` daria
    `KeyError` e o teste passaria a falhar por um motivo que não é o dele.
    """
    carregado = yaml.safe_load(caminho.read_text())
    return carregado.get("on") or carregado.get(True)


def test_o_CI_roda_em_pull_request_de_qualquer_alvo():
    """A invariante que custou um PR sem verificação nenhuma.

    `pull_request:` precisa existir e **não** pode ter `branches`. Com filtro,
    um PR contra qualquer branch fora da lista não aciona job nenhum e aparece
    como `clean`.
    """
    gatilhos = _gatilhos(CI)

    assert "pull_request" in gatilhos, "o CI deixou de rodar em pull request"
    filtro = gatilhos["pull_request"] or {}
    assert "branches" not in filtro, (
        "o gatilho de pull_request voltou a filtrar por branch: um PR aberto "
        f"contra outro alvo ficaria sem CI nenhum. Filtro encontrado: {filtro}"
    )


def test_o_CI_continua_rodando_no_push_da_main():
    """O contraponto: tirar o filtro do PR não pode ter tirado o push."""
    empurrao = _gatilhos(CI)["push"]

    assert empurrao["branches"] == ["main"]


def test_os_jobs_continuam_declarados_com_os_nomes_de_sempre():
    """Os nomes que o dono confere antes de mesclar.

    A asserção é de igualdade EXATA, e não de substring: com `in`, renomear
    `Backend (Python)` para `Backend2 (Python)` passava — medido por mutação.
    Nome de job não é detalhe aqui, é o contrato com quem revisa: o critério de
    merge desta equipe é "os quatro verdes", conferido pelo nome na lista do
    PR — mais a auditoria de dependências, que só informa (ver o teste
    seguinte). Renomear é legítimo; renomear sem atualizar este teste, e sem
    reparar que o hábito de quem revisa mudou junto, não é.

    O quinto e o sexto entraram com as extensões (lotes E1 e E2 da preparação
    para software livre): "Backend sem extensões (núcleo)" e "Frontend sem
    extensões (núcleo)" rodam as suítes com as extensões apagadas, como a
    distribuição livre as roda, em jobs paralelos para não alongar os de cima.
    Desde então, "os seis verdes".
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


def test_a_auditoria_de_dependencias_so_informa():
    """Por ora ela não bloqueia: todo passo do job, fora os de preparo (checkout,
    setup-* e a instalação das ferramentas), tem `continue-on-error`, e o job
    fica verde mesmo com achado — que sai como aviso e no resumo da execução.

    A regra é por exclusão, não por nome de ferramenta: um passo novo que audite
    de outro jeito (uma action, outro scanner) também precisa declarar a chave,
    ou tornaria a auditoria bloqueante sem ninguém ter decidido. Tirar a chave
    de propósito é a decisão, e ela passa por aqui.
    """
    job = yaml.safe_load(CI.read_text())["jobs"]["audit"]
    preparo = ("actions/checkout@", "actions/setup-python@", "actions/setup-node@")
    auditorias = [
        passo for passo in job["steps"]
        if not str(passo.get("uses", "")).startswith(preparo)
        and passo.get("name") != "Instalar o pip-audit"
    ]

    assert len(auditorias) >= 4, [p.get("name") for p in auditorias]
    bloqueantes = [p.get("name") for p in auditorias if p.get("continue-on-error") is not True]
    assert bloqueantes == [], f"passos que bloqueariam o CI: {bloqueantes}"


def test_o_dependabot_segue_conservador():
    """Versão nova no máximo uma vez por mês, e só depois de 14 dias publicada
    (30 para versão maior), em todos os ecossistemas.

    É a defesa contra ataque à cadeia de suprimentos: versão maliciosa costuma
    ser descoberta e retirada em horas ou poucos dias, e quem atualiza assim que
    ela sai é quem a instala. Voltar ao semanal, encurtar a quarentena ou tirar
    um pacote dela (`cooldown.exclude`) é uma decisão, e ela passa por aqui.
    Correção de segurança não segue este arquivo (vem pelas "Dependabot
    security updates"), então não espera.
    """
    atualizacoes = yaml.safe_load(DEPENDABOT.read_text())["updates"]
    assert atualizacoes, "o dependabot.yml ficou sem configuração nenhuma"

    frouxas = []
    for u in atualizacoes:
        nome = f"{u['package-ecosystem']} {u['directory']}"
        intervalo = u["schedule"]["interval"]
        espera = u.get("cooldown") or {}
        padrao = espera.get("default-days", 0)
        if intervalo not in ("monthly", "quarterly", "semiannually", "yearly"):
            frouxas.append(f"{nome}: intervalo {intervalo}")
        if padrao < 14:
            frouxas.append(f"{nome}: quarentena de {padrao} dias")
        if espera.get("semver-major-days", padrao) < 30:
            frouxas.append(f"{nome}: quarentena de versão maior de {espera.get('semver-major-days', padrao)} dias")
        for chave in ("semver-minor-days", "semver-patch-days"):
            if chave in espera and espera[chave] < 14:
                frouxas.append(f"{nome}: {chave} = {espera[chave]}")
        if espera.get("exclude"):
            frouxas.append(f"{nome}: fora da quarentena: {espera['exclude']}")

    assert frouxas == [], frouxas

    # O Dependabot recusa o arquivo INTEIRO — e para de propor atualização em
    # todos os ecossistemas — se um deles usa chave que não aceita. Medido: para
    # actions, `semver-*-days` dá "The property ... is not supported for the
    # package ecosystem 'github-actions'".
    sem_semver = {"github-actions"}
    invalidas = [
        f"{u['package-ecosystem']} {u['directory']}: cooldown.{chave}"
        for u in atualizacoes if u["package-ecosystem"] in sem_semver
        for chave in (u.get("cooldown") or {}) if chave.startswith("semver-")
    ]
    assert invalidas == [], f"chaves que o Dependabot não aceita: {invalidas}"


def _passos(caminho: Path):
    """Todo passo de um workflow ou de uma action composta local — e todo job
    que chama um workflow reutilizável — como o GitHub os lê: pelo YAML, e não
    linha a linha (`- {uses: ...}`, recuos e aspas diferentes contam igual)."""
    doc = yaml.safe_load(caminho.read_text()) or {}
    for nome, job in (doc.get("jobs") or {}).items():
        if job.get("uses"):
            yield nome, {"uses": job["uses"]}
        for passo in job.get("steps") or []:
            yield nome, passo
    for passo in (doc.get("runs") or {}).get("steps") or []:
        yield caminho.parent.name, passo


def test_as_actions_estao_fixadas_por_sha():
    """Toda action de terceiros vai pelo SHA do commit, com a versão no
    comentário (`dono/action@<40 hex> # vX.Y.Z`).

    Uma tag (`@v4`) pode ser movida para outro código pelo dono da action — ou
    por quem roubar a conta dele. Foi o ataque ao tj-actions/changed-files, em
    mar/2025: as tags passaram a apontar para um commit que despejava os
    segredos do runner no log. Um SHA não se move. O Dependabot atualiza o SHA e
    o comentário juntos, com a mesma quarentena das outras dependências.
    """
    soltas = []
    for arquivo in [*WORKFLOWS, *ACOES_LOCAIS]:
        texto = arquivo.read_text()
        for job, passo in _passos(arquivo):
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


def test_o_CI_so_le_o_repositorio():
    """No ci.yml o token é só de leitura, no topo e em cada job; em todos os
    workflows o checkout não guarda o token no .git/config. Um script de
    instalação malicioso (npm, pip) roda dentro desses jobs: não pode encontrar
    ali credencial que escreva no repositório."""
    ci = yaml.safe_load(CI.read_text())
    assert ci.get("permissions") == {"contents": "read"}

    def so_leitura(permissoes) -> bool:
        if isinstance(permissoes, str):
            return permissoes == "read-all"
        return all(valor in ("read", "none") for valor in (permissoes or {}).values())

    com_escrita = [
        f"ci.yml:{nome}: {job['permissions']}"
        for nome, job in ci["jobs"].items()
        if "permissions" in job and not so_leitura(job["permissions"])
    ]
    assert com_escrita == [], f"job do CI pedindo mais que leitura: {com_escrita}"

    com_token = [
        f"{wf.name}:{job}"
        for wf in WORKFLOWS
        for job, passo in _passos(wf)
        if str(passo.get("uses", "")).startswith("actions/checkout@")
        and (passo.get("with") or {}).get("persist-credentials") is not False
    ]
    assert com_token == [], f"checkout guardando o token: {com_token}"


def _comandos(run: str):
    """Os comandos de um `run:` como o shell os vê: a barra no fim da linha
    junta a seguinte, comentário cai fora, e `&&`, `||`, `;`, `|` e quebra de
    linha separam um comando do outro."""
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


def test_todo_pip_install_dos_workflows_confere_hash():
    """Nenhum `pip install` do CI/CD instala sem `--require-hashes` — conferido
    comando a comando, não por linha: `pip install --upgrade pip && pip install
    --require-hashes ...` ainda deixaria o primeiro entrar sem hash. Pacote sem
    conferência, e com as dependências na versão mais nova do dia, é justamente
    a porta que os locks com hash fecharam. Vale para qualquer passo novo."""
    soltos = [
        f"{arquivo.name}:{job}: {' '.join(tokens)}"
        for arquivo in [*WORKFLOWS, *ACOES_LOCAIS]
        for job, passo in _passos(arquivo)
        for tokens in _comandos(str(passo.get("run") or ""))
        if _eh_pip_install(tokens) and "--require-hashes" not in tokens
    ]
    assert soltos == [], soltos


def test_os_hooks_do_pre_commit_usam_as_ferramentas_travadas():
    """Os hooks rodam na máquina de quem commita. Todos são `repo: local` com
    `language: system`: usam o pre-commit, o detect-secrets e os
    pre-commit-hooks do requirements-dev.txt (com hash e quarentena). Um
    repositório remoto — mesmo fixado por SHA — faz o pre-commit montar um
    ambiente próprio, resolvendo as dependências no PyPI na hora e sem hash."""
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


def test_o_release_do_desktop_remonta_o_runtime_e_isola_os_segredos():
    """O runtime Python vai, assinado, para a máquina do usuário. Ele não pode
    vir do cache do Actions (que código de qualquer job da main consegue
    envenenar) — só o tarball, que o `python:fetch` confere pelo SHA-256. E o
    token de escrita e os segredos de assinatura só entram no passo do
    electron-builder, não no build do app (tsc, esbuild, vite: terceiros)."""
    passos = [passo for _, passo in _passos(RELEASE_DESKTOP)]

    em_cache = [
        caminho
        for passo in passos
        if str(passo.get("uses", "")).startswith("actions/cache")
        for caminho in str((passo.get("with") or {}).get("path", "")).split()
    ]
    assert em_cache and all(c == "desktop/resources/.cache" for c in em_cache), em_cache

    com_segredo = [
        (passo.get("name"), str(passo.get("run")).split(" -- ")[0])
        for passo in passos
        if any("secrets." in str(valor) for valor in (passo.get("env") or {}).values())
    ]
    assert com_segredo == [("Gerar o instalador", "npm run empacotar")], com_segredo


def test_o_release_do_desktop_grava_os_enderecos_das_variaveis_do_repositorio():
    """O código não traz o servidor nem a UI de instalação nenhuma: o build os
    recebe das variáveis do repositório, e o feed do auto-update é o deste
    repositório (cada fork publica e atualiza nas próprias releases)."""
    passos = {passo.get("name"): passo for _, passo in _passos(RELEASE_DESKTOP)}

    env = passos["Compilar o app"].get("env") or {}
    assert env.get("ATLANS_DESKTOP_SERVIDOR") == "${{ vars.ATLANS_DESKTOP_SERVIDOR }}"
    assert env.get("ATLANS_DESKTOP_UI_URL") == "${{ vars.ATLANS_DESKTOP_UI_URL }}"

    # O feed vai por env, e não por `-c.publish.owner=...` na linha de comando:
    # o pwsh do runner Windows parte o argumento no primeiro ponto, e o
    # electron-builder recebia `-c` e `.publish.owner=...` (build quebrado).
    gerar = passos["Gerar o instalador"]
    assert (gerar.get("env") or {}).get("ATLANS_RELEASES_DONO") == "${{ github.repository_owner }}"
    assert (gerar.get("env") or {}).get("ATLANS_RELEASES_REPO") == "${{ github.event.repository.name }}"
    assert str(gerar.get("run")).strip() == "npm run empacotar"
    builder = (RAIZ / "desktop" / "electron-builder.yml").read_text(encoding="utf-8")
    assert re.search(r"^  owner: \$\{env\.ATLANS_RELEASES_DONO\}$", builder, re.M)
    assert re.search(r"^  repo: \$\{env\.ATLANS_RELEASES_REPO\}$", builder, re.M)
