# tests/unit/test_traefik_config.py
"""
A Traefik router must not reference a middleware that does not exist.

In a real installation, the `api-mcp` router declared `rate-mcp@file` and
Traefik could not see that middleware — it was in the host's file, but the
container read an orphan inode (the update deleted the file before copying the
new one, and a single-file bind mount pins the inode). Traefik silently drops a
router whose middleware does not resolve: `/mcp` started falling into the
Next.js catch-all and returning HTML to an MCP client, with no symptom at all on
the other routes.

The mount is now a directory and the provider has `watch`, which fixes the
DELIVERY of the file. What these tests cover is the other half: the INTEGRITY
of the references. A misspelled name in a label would still take down the
whole route in production, and the only place it showed up was the Traefik
log — which nobody reads before a deploy goes wrong.

The first attempt at a fix added a second lesson: the directory ended up in
`traefik/dynamic/`, which is tidy in the repository and does not work in the
installation — `traefik/` is the internal CA's folder, belonging to the
operator, and whoever updates the code may not be able to write to it; the
update died with `Permission denied` before starting any container. That is
why there is also a test about WHERE the directory lives.

These are consistency tests across configuration files, in the same spirit as
`test_docs_mcp.py`: cheap in CI, and they cover failures that no application
test reaches.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[2]
COMPOSE = RAIZ / "docker-compose.yml"
DINAMICO = RAIZ / "traefik-dynamic" / "dynamic.yml"

# `traefik.http.routers.<router>.middlewares=a@file,b@file`
_MIDDLEWARES_DA_LABEL = re.compile(
    r"traefik\.http\.routers\.(?P<router>[\w-]+)\.middlewares=(?P<lista>[^\"']+)"
)


def _texto(caminho: Path) -> str:
    return caminho.read_text(encoding="utf-8")


# Middleware name: a key indented 4 spaces, right below `  middlewares:`.
# Read with a regex, not with PyYAML, on purpose: PyYAML is not in
# `requirements.in` (it only arrives transitively), and an `importorskip`
# would make this whole file silently VANISH from CI — the same kind of
# silent failure it exists to catch.
_INICIO_DOS_MIDDLEWARES = re.compile(r"^  middlewares:\s*$", re.M)
_NOME_DO_MIDDLEWARE = re.compile(r"^    ([A-Za-z][\w-]*):\s*$", re.M)
_FIM_DO_BLOCO = re.compile(r"^(?:\S|  [A-Za-z])", re.M)


def _middlewares_definidos() -> set[str]:
    """The names the file provider publishes as `<nome>@file`."""
    texto = _texto(DINAMICO)
    inicio = _INICIO_DOS_MIDDLEWARES.search(texto)
    assert inicio, "bloco `http.middlewares` nao encontrado em dynamic.yml"
    resto = texto[inicio.end() :]
    fim = _FIM_DO_BLOCO.search(resto)
    bloco = resto[: fim.start()] if fim else resto
    return set(_NOME_DO_MIDDLEWARE.findall(bloco))


def test_a_leitura_do_arquivo_dinamico_enxerga_os_middlewares():
    """If the parsing breaks, the integrity test would pass vacuously."""
    definidos = _middlewares_definidos()
    assert len(definidos) >= 4, f"leitura suspeita de dynamic.yml: {sorted(definidos)}"
    # The ones the MCP router uses (one variant per edge) — if they vanish from here, the route goes down.
    assert {"rate-mcp-borda-aberta", "rate-mcp-cloudflare-only", "strip-executor-cert-header"} <= definidos


def test_o_rate_limit_conta_pelo_ip_do_cliente_em_cada_borda():
    """Without a CDN, `ipStrategy.depth: 1` is NOT "per IP": Traefik strips the
    X-Forwarded-For of anyone not in trustedIPs before the middlewares and only
    appends the client IP after them, so the limit's source was empty and all
    clients fell into a single bucket (reproduced on Traefik v3.6: one client
    exhausted the bucket and the others got a 429 on their first request).
    That is why each limit of the public routers has one variant per edge,
    chosen by the same BORDA_MIDDLEWARE as the labels; and /internal, which the
    executors reach directly in any installation, counts per connection."""
    middlewares = yaml.safe_load(_texto(DINAMICO))["http"]["middlewares"]
    assert "sourceCriterion" not in middlewares["rate-internal"]["rateLimit"]
    for limite in ("rate-mcp", "rate-download"):
        aberta = middlewares[f"{limite}-borda-aberta"]["rateLimit"]
        cloudflare = middlewares[f"{limite}-cloudflare-only"]["rateLimit"]
        assert "sourceCriterion" not in aberta, f"{limite}-borda-aberta conta pela conexao"
        assert cloudflare["sourceCriterion"]["ipStrategy"]["depth"] == 1
        # The same quota in both: the edge changes the source, not the limit.
        assert {k: v for k, v in aberta.items()} == {k: v for k, v in cloudflare.items() if k != "sourceCriterion"}
    compose = _texto(COMPOSE)
    for limite in ("rate-mcp", "rate-download"):
        assert f"{limite}-${{BORDA_MIDDLEWARE:-borda-aberta}}@file" in compose, f"a label do {limite} nao segue a borda"
        assert f",{limite}@file" not in compose, f"a label antiga do {limite} voltou"


_VARIAVEL = re.compile(r"\$\{(?P<nome>[A-Z_][A-Z0-9_]*)(?::-(?P<padrao>[^}]*))?\}")


def _resolver(texto: str, ambiente: dict[str, str] | None = None) -> str:
    """Interpolates `${VAR:-padrao}` like compose: the environment value or the default."""
    ambiente = ambiente or {}
    return _VARIAVEL.sub(lambda m: ambiente.get(m.group("nome"), m.group("padrao") or ""), texto)


def _referencias_por_router(ambiente: dict[str, str] | None = None) -> dict[str, list[str]]:
    """`{router: [middleware, ...]}` read from the compose labels, already interpolated."""
    referencias: dict[str, list[str]] = {}
    for achado in _MIDDLEWARES_DA_LABEL.finditer(_resolver(_texto(COMPOSE), ambiente)):
        nomes = [n.strip() for n in achado.group("lista").split(",") if n.strip()]
        referencias.setdefault(achado.group("router"), []).extend(nomes)
    return referencias


def test_ha_routers_com_middleware_para_conferir():
    """If the regex stops matching, the tests below would pass vacuously."""
    referencias = _referencias_por_router()
    assert referencias, "nenhuma label de middleware encontrada no docker-compose.yml"
    assert "api-mcp" in referencias, "o router do servidor MCP sumiu do compose"


# The edge of the public routers changes with the .env: no CDN (the default)
# and behind Cloudflare. Each one's middleware has to exist in the dynamic file.
_BORDAS = {
    "sem CDN": {},
    "Cloudflare": {"BORDA_MIDDLEWARE": "cloudflare-only"},
}


@pytest.mark.parametrize("borda", sorted(_BORDAS))
def test_todo_middleware_referenciado_existe_no_arquivo_dinamico(borda):
    """The test that would have prevented the incident.

    It applies to all routers at once: any new label that invents a name — or
    gets one letter wrong — fails here, and not in production by returning the
    wrong page.
    """
    definidos = _middlewares_definidos()
    faltando: list[str] = []
    for router, nomes in sorted(_referencias_por_router(_BORDAS[borda]).items()):
        for nome in nomes:
            # Only the file provider is checked here: a middleware without a
            # suffix, or with `@docker`, comes from another source and has another rule.
            if not nome.endswith("@file"):
                continue
            if nome[: -len("@file")] not in definidos:
                faltando.append(f"{router} -> {nome}")
    assert not faltando, (
        "middleware referenciado que o provider de arquivo nao define: "
        + "; ".join(faltando)
        + f" (definidos: {sorted(definidos)})"
    )


def test_o_compose_monta_o_diretorio_e_nao_o_arquivo_solto():
    """Going back to the single-file mount reopens the inode pitfall."""
    compose = _texto(COMPOSE)
    assert "./traefik-dynamic:/etc/traefik/dynamic:ro" in compose
    assert "--providers.file.directory=/etc/traefik/dynamic" in compose
    # Sem `watch`, mudar o arquivo volta a exigir recriar o container.
    assert "--providers.file.watch=true" in compose
    # The old mount must not come back alongside the new one.
    assert "/etc/traefik/dynamic.yml" not in compose
    assert "--providers.file.filename=" not in compose


def test_o_diretorio_dinamico_fica_na_raiz_e_fora_de_traefik():
    """The INSTALLATION side: `traefik/` belongs to the operator, and the update does not write there.

    The first version of this fix put the directory in `traefik/dynamic/`, which
    is tidy in the repository and does not work in the installation: `traefik/`
    is the internal CA's folder, belonging to the operator (created for
    `atlans-ca`), and whoever updates the code may not be able to write to it —
    the update died with
    `mkdir: cannot create directory: Permission denied` before even starting
    any container. Nothing in the repository gave this away — `traefik/` is not
    even tracked in git —, so the invariant is written down here.
    """
    assert DINAMICO.exists(), f"{DINAMICO} nao existe"
    assert DINAMICO.parent.parent == RAIZ, "o diretorio dinamico saiu da raiz do projeto"
    assert not (RAIZ / "traefik" / "dynamic").exists(), (
        "o diretorio voltou para dentro de traefik/, onde o usuario do deploy nao escreve"
    )
    # The compose file has to agree with the location.
    assert "./traefik/dynamic" not in _texto(COMPOSE)


# ── The edge middleware goes in front of every public router ───────────────
#
# Behind Cloudflare (BORDA_MIDDLEWARE=cloudflare-only), the executors' host is
# DNS-only (mTLS does not pass through Cloudflare) and publishes the origin IP —
# and it is the SAME Traefik that serves the public host. Without
# `cloudflare-only@file` IN FRONT of each router of the public hosts,
# `curl --resolve <host>:443:<ip>` talks to Next.js and the API bypassing
# Cloudflare: no WAF and no edge rate limit. Confirmed in production before
# these tests existed. A new router without the label would silently reopen the
# door — that is why the rule is "every router", not a fixed list of names. The
# hosts come from the .env (PUBLIC_HOST, S3_HOST, AGENTS_HOST); so does the
# edge (BORDA_MIDDLEWARE).

# `traefik.http.routers.<router>.rule=Host(`...`) && ...`
_REGRA_DA_LABEL = re.compile(
    r"traefik\.http\.routers\.(?P<router>[\w-]+)\.rule=(?P<regra>[^\"']+)"
)
_HOSTS_PROXIED = ("Host(`${PUBLIC_HOST:-localhost}`)", "Host(`${S3_HOST:-s3.localhost}`)")
_HOST_DOS_EXECUTORES = "Host(`${AGENTS_HOST:-agents.localhost}`)"
_LISTA = "${BORDA_MIDDLEWARE:-borda-aberta}@file"


def _referencias_cruas() -> dict[str, list[str]]:
    """The references as written in the compose file, without interpolation."""
    referencias: dict[str, list[str]] = {}
    for achado in _MIDDLEWARES_DA_LABEL.finditer(_texto(COMPOSE)):
        nomes = [n.strip() for n in achado.group("lista").split(",") if n.strip()]
        referencias.setdefault(achado.group("router"), []).extend(nomes)
    return referencias


def _regras_por_router() -> dict[str, str]:
    return {
        achado.group("router"): achado.group("regra")
        for achado in _REGRA_DA_LABEL.finditer(_texto(COMPOSE))
    }


def test_ha_routers_proxied_e_de_executores_para_conferir():
    """If the rules regex stops matching, the two tests below would pass vacuously."""
    regras = _regras_por_router()
    proxied = {r for r, g in regras.items() if any(h in g for h in _HOSTS_PROXIED)}
    executores = {r for r, g in regras.items() if _HOST_DOS_EXECUTORES in g}
    assert {"web-prod", "api-mcp", "minio-s3"} <= proxied, sorted(proxied)
    assert {"executores-ws", "executores-enroll"} <= executores, sorted(executores)


def test_todo_router_publico_leva_a_borda_na_frente():
    """First position, not "somewhere": whatever comes before it runs for
    anyone — a rate limit in front, for example, would still spend the bucket
    of a forged IP."""
    regras = _regras_por_router()
    referencias = _referencias_cruas()
    sem_lista = [
        r for r, g in sorted(regras.items())
        if any(h in g for h in _HOSTS_PROXIED)
        and (referencias.get(r) or [""])[0] != _LISTA
    ]
    assert not sem_lista, (
        f"router de host proxied sem `{_LISTA}` na primeira posicao: " + ", ".join(sem_lista)
    )


def test_os_routers_dos_executores_nao_levam_a_lista_da_cloudflare():
    """Executors connect from any network — the list would lock them out."""
    regras = _regras_por_router()
    referencias = _referencias_cruas()
    com_lista = [
        r for r, g in sorted(regras.items())
        if _HOST_DOS_EXECUTORES in g
        and ({_LISTA, "cloudflare-only@file"} & set(referencias.get(r, [])))
    ]
    assert not com_lista, "router de executor com a borda: " + ", ".join(com_lista)


def test_toda_regra_de_host_vem_do_env():
    """No installation host hard-coded in the rules: only the three from the .env."""
    for router, regra in sorted(_regras_por_router().items()):
        hosts = re.findall(r"Host\(`([^`]*)`\)", regra)
        assert hosts, f"{router} sem Host() na regra"
        for host in hosts:
            assert re.fullmatch(r"\$\{(PUBLIC_HOST|AGENTS_HOST|S3_HOST):-[a-z0-9.-]+\}", host), (
                f"{router}: host fixo na regra ({host})"
            )


def test_o_compose_nao_traz_o_dominio_nem_o_registry_de_uma_instalacao():
    compose = _texto(COMPOSE)
    assert not re.search(r"ghcr\.io/[a-z0-9-]+/atlans-", compose)


# The `- x.x.x.x/nn` items of the `cloudflare-only:` block, which runs until the
# next 4-space key (the next middleware).
_CIDR = re.compile(r"^\s+-\s+([0-9a-fA-F.:]+/\d+)\s*$", re.M)


def _faixas_da_lista() -> set[str]:
    texto = _texto(DINAMICO)
    marca = "    cloudflare-only:\n"
    resto = texto[texto.index(marca) + len(marca):]
    fim = _NOME_DO_MIDDLEWARE.search(resto)
    bloco = resto[: fim.start()] if fim else resto
    return set(_CIDR.findall(bloco))


def test_as_faixas_da_cloudflare_sao_as_mesmas_nos_tres_lugares():
    """The list lives in three files, and a divergence opens or closes the wrong door.

    One range too few in the allowlist is a 403 for some of the users
    (Cloudflare arrives through several); one too many is a hole. The backend
    (CLOUDFLARE_RANGES, which finds the real IP in X-Forwarded-For) and the
    entrypoints' `trustedIPs` have to agree with it. `trustedIPs` comes from the
    .env (BORDA_FAIXAS_CONFIAVEIS); the value for Cloudflare is the one in the
    .env.example sample, IPv4 only, which is how Cloudflare reaches the origin.
    """
    from app.core.trusted_proxy import CLOUDFLARE_RANGES

    faixas = _faixas_da_lista()
    assert len(faixas) >= 20, f"leitura suspeita da allowlist: {sorted(faixas)}"
    assert faixas == set(CLOUDFLARE_RANGES.split(","))
    exemplo = re.search(r"^#BORDA_FAIXAS_CONFIAVEIS=(\S+)$", _texto(RAIZ / ".env.example"), re.M)
    assert exemplo, "o exemplo da Cloudflare sumiu do .env.example"
    assert set(exemplo.group(1).split(",")) == {f for f in faixas if ":" not in f}


def test_sem_cdn_o_traefik_nao_confia_em_ninguem_alem_do_loopback():
    """The trustedIPs default: without a CDN, Traefik is the edge and rewrites the XFF."""
    compose = _texto(COMPOSE)
    for entrypoint in ("web", "websecure"):
        achado = re.search(
            rf"entrypoints\.{entrypoint}\.forwardedHeaders\.trustedIPs=([^\"]+)", compose
        )
        assert achado, f"trustedIPs do entrypoint {entrypoint} sumiu do compose"
        assert achado.group(1) == "${BORDA_FAIXAS_CONFIAVEIS:-127.0.0.1/32}", entrypoint


def test_a_borda_aberta_aceita_qualquer_ip():
    texto = _texto(DINAMICO)
    marca = "    borda-aberta:\n"
    resto = texto[texto.index(marca) + len(marca):]
    fim = _NOME_DO_MIDDLEWARE.search(resto)
    bloco = resto[: fim.start()] if fim else resto
    assert set(_CIDR.findall(bloco)) == {"0.0.0.0/0", "::/0"}


def test_o_cert_dos_executores_tem_nome_fixo_e_o_legado_segue_ate_a_troca():
    """bootstrap-stepca.sh writes agents.crt; the old name stays only during the transition."""
    dinamico = _texto(DINAMICO)
    assert "certFile: /etc/ssl/atlans-ca/agents.crt" in dinamico
    assert "keyFile:  /etc/ssl/atlans-ca/agents.key" in dinamico
    bootstrap = _texto(RAIZ / "scripts" / "bootstrap-stepca.sh")
    assert 'CRT_PATH="traefik/atlans-ca/agents.crt"' in bootstrap
    assert 'KEY_PATH="traefik/atlans-ca/agents.key"' in bootstrap
