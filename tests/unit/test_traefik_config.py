# tests/unit/test_traefik_config.py
"""
Um router do Traefik nao pode referenciar middleware que nao existe.

Numa instalacao real, o router `api-mcp` declarava `rate-mcp@file` e o Traefik
nao enxergava esse middleware — ele estava no arquivo do host, mas o container
lia um inode orfao (a atualizacao apagava o arquivo antes de copiar o novo, e
bind mount de arquivo unico prende o inode). Traefik descarta em silencio um
router cujo middleware nao resolve: `/mcp` passou a cair no catch-all do
Next.js e devolver HTML a um cliente MCP, sem sintoma nenhum nas outras rotas.

O mount agora e de diretorio e o provider tem `watch`, o que conserta a
ENTREGA do arquivo. O que esses testes cobrem e a outra metade: a INTEGRIDADE
das referencias. Um nome digitado errado numa label continuaria derrubando a
rota inteira em producao, e o unico lugar onde isso aparecia era o log do
Traefik — que ninguem le antes de um deploy dar errado.

A primeira tentativa de conserto acrescentou uma segunda licao: o diretorio
foi parar em `traefik/dynamic/`, que e arrumado no repositorio e nao serve na
instalacao — `traefik/` e a pasta da CA interna, de quem opera, e quem atualiza
o codigo pode nao escrever nela; a atualizacao morreu com
`Permission denied` antes de subir container nenhum. Por isso ha tambem um
teste sobre ONDE o diretorio fica.

Sao testes de coerencia entre arquivos de configuracao, no mesmo espirito de
`test_docs_mcp.py`: baratos em CI, e cobrem falhas que nenhum teste de
aplicacao alcanca.
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


# Nome de middleware: chave com 4 espacos de recuo, logo abaixo de
# `  middlewares:`. Lido com regex, e nao com PyYAML, de proposito: PyYAML nao
# esta no `requirements.in` (chega so por transitividade), e um
# `importorskip` faria este arquivo inteiro SUMIR do CI em silencio — o mesmo
# tipo de falha muda que ele existe para pegar.
_INICIO_DOS_MIDDLEWARES = re.compile(r"^  middlewares:\s*$", re.M)
_NOME_DO_MIDDLEWARE = re.compile(r"^    ([A-Za-z][\w-]*):\s*$", re.M)
_FIM_DO_BLOCO = re.compile(r"^(?:\S|  [A-Za-z])", re.M)


def _middlewares_definidos() -> set[str]:
    """Os nomes que o provider de arquivo publica como `<nome>@file`."""
    texto = _texto(DINAMICO)
    inicio = _INICIO_DOS_MIDDLEWARES.search(texto)
    assert inicio, "bloco `http.middlewares` nao encontrado em dynamic.yml"
    resto = texto[inicio.end() :]
    fim = _FIM_DO_BLOCO.search(resto)
    bloco = resto[: fim.start()] if fim else resto
    return set(_NOME_DO_MIDDLEWARE.findall(bloco))


def test_a_leitura_do_arquivo_dinamico_enxerga_os_middlewares():
    """Se a leitura quebrar, o teste de integridade passaria vazio."""
    definidos = _middlewares_definidos()
    assert len(definidos) >= 4, f"leitura suspeita de dynamic.yml: {sorted(definidos)}"
    # Os que o router do MCP usa (uma variante por borda) — se sumirem daqui, a rota cai.
    assert {"rate-mcp-borda-aberta", "rate-mcp-cloudflare-only", "strip-executor-cert-header"} <= definidos


def test_o_rate_limit_conta_pelo_ip_do_cliente_em_cada_borda():
    """Sem CDN, `ipStrategy.depth: 1` NAO e "por IP": o Traefik apaga o
    X-Forwarded-For de quem nao esta em trustedIPs antes dos middlewares e so
    anexa o IP do cliente depois deles, entao a fonte do limite ficava vazia e
    todos os clientes caiam num balde so (reproduzido no Traefik v3.6: um
    cliente esgotava o balde e os outros recebiam 429 no primeiro pedido).
    Por isso cada limite dos routers publicos tem uma variante por borda,
    escolhida pela mesma BORDA_MIDDLEWARE das labels; e o /internal, que os
    executores alcancam direto em qualquer instalacao, conta pela conexao."""
    middlewares = yaml.safe_load(_texto(DINAMICO))["http"]["middlewares"]
    assert "sourceCriterion" not in middlewares["rate-internal"]["rateLimit"]
    for limite in ("rate-mcp", "rate-download"):
        aberta = middlewares[f"{limite}-borda-aberta"]["rateLimit"]
        cloudflare = middlewares[f"{limite}-cloudflare-only"]["rateLimit"]
        assert "sourceCriterion" not in aberta, f"{limite}-borda-aberta conta pela conexao"
        assert cloudflare["sourceCriterion"]["ipStrategy"]["depth"] == 1
        # A mesma cota nas duas: a borda muda a fonte, nao o limite.
        assert {k: v for k, v in aberta.items()} == {k: v for k, v in cloudflare.items() if k != "sourceCriterion"}
    compose = _texto(COMPOSE)
    for limite in ("rate-mcp", "rate-download"):
        assert f"{limite}-${{BORDA_MIDDLEWARE:-borda-aberta}}@file" in compose, f"a label do {limite} nao segue a borda"
        assert f",{limite}@file" not in compose, f"a label antiga do {limite} voltou"


_VARIAVEL = re.compile(r"\$\{(?P<nome>[A-Z_][A-Z0-9_]*)(?::-(?P<padrao>[^}]*))?\}")


def _resolver(texto: str, ambiente: dict[str, str] | None = None) -> str:
    """Interpola `${VAR:-padrao}` como o compose: o valor do ambiente ou o padrao."""
    ambiente = ambiente or {}
    return _VARIAVEL.sub(lambda m: ambiente.get(m.group("nome"), m.group("padrao") or ""), texto)


def _referencias_por_router(ambiente: dict[str, str] | None = None) -> dict[str, list[str]]:
    """`{router: [middleware, ...]}` lido das labels do compose, ja interpolado."""
    referencias: dict[str, list[str]] = {}
    for achado in _MIDDLEWARES_DA_LABEL.finditer(_resolver(_texto(COMPOSE), ambiente)):
        nomes = [n.strip() for n in achado.group("lista").split(",") if n.strip()]
        referencias.setdefault(achado.group("router"), []).extend(nomes)
    return referencias


def test_ha_routers_com_middleware_para_conferir():
    """Se a regex parar de casar, os testes abaixo passariam vazios."""
    referencias = _referencias_por_router()
    assert referencias, "nenhuma label de middleware encontrada no docker-compose.yml"
    assert "api-mcp" in referencias, "o router do servidor MCP sumiu do compose"


# A borda dos routers publicos muda com o .env: sem CDN (o padrao) e atras da
# Cloudflare. O middleware de cada uma tem de existir no arquivo dinamico.
_BORDAS = {
    "sem CDN": {},
    "Cloudflare": {"BORDA_MIDDLEWARE": "cloudflare-only"},
}


@pytest.mark.parametrize("borda", sorted(_BORDAS))
def test_todo_middleware_referenciado_existe_no_arquivo_dinamico(borda):
    """O teste que teria evitado o incidente.

    Vale para todos os routers de uma vez: qualquer label nova que invente um
    nome — ou erre uma letra — reprova aqui, e nao em producao devolvendo a
    pagina errada.
    """
    definidos = _middlewares_definidos()
    faltando: list[str] = []
    for router, nomes in sorted(_referencias_por_router(_BORDAS[borda]).items()):
        for nome in nomes:
            # Só o provider de arquivo é conferido aqui: um middleware sem
            # sufixo, ou com `@docker`, vem de outra fonte e tem outra regra.
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
    """Voltar ao mount de arquivo unico reabre a armadilha do inode."""
    compose = _texto(COMPOSE)
    assert "./traefik-dynamic:/etc/traefik/dynamic:ro" in compose
    assert "--providers.file.directory=/etc/traefik/dynamic" in compose
    # Sem `watch`, mudar o arquivo volta a exigir recriar o container.
    assert "--providers.file.watch=true" in compose
    # O mount antigo nao pode voltar junto com o novo.
    assert "/etc/traefik/dynamic.yml" not in compose
    assert "--providers.file.filename=" not in compose


def test_o_diretorio_dinamico_fica_na_raiz_e_fora_de_traefik():
    """O lado da INSTALACAO: `traefik/` e de quem opera, e a atualizacao nao escreve la.

    A primeira versao deste conserto pos o diretorio em `traefik/dynamic/`, que
    e arrumado no repositorio e nao serve na instalacao: `traefik/` e a pasta da
    CA interna, de quem opera (criada para o `atlans-ca`), e quem atualiza o
    codigo pode nao escrever nela — a atualizacao morreu com
    `mkdir: cannot create directory: Permission denied` antes mesmo de subir
    qualquer container. Nada no repositorio denunciava isso — `traefik/` nem e
    rastreado no git —, entao a invariante fica escrita aqui.
    """
    assert DINAMICO.exists(), f"{DINAMICO} nao existe"
    assert DINAMICO.parent.parent == RAIZ, "o diretorio dinamico saiu da raiz do projeto"
    assert not (RAIZ / "traefik" / "dynamic").exists(), (
        "o diretorio voltou para dentro de traefik/, onde o usuario do deploy nao escreve"
    )
    # O compose tem de concordar com o lugar.
    assert "./traefik/dynamic" not in _texto(COMPOSE)


# ── O middleware de borda vai na frente de todo router publico ─────────────
#
# Atras da Cloudflare (BORDA_MIDDLEWARE=cloudflare-only), o host dos executores
# e DNS-only (o mTLS nao atravessa a Cloudflare) e publica o IP do origin — e e
# o MESMO Traefik que serve o host publico. Sem `cloudflare-only@file` NA FRENTE
# de cada router dos hosts publicos, `curl --resolve <host>:443:<ip>` fala com o
# Next.js e a API por fora da Cloudflare: sem WAF nem rate limit da borda.
# Confirmado em producao antes destes testes existirem. Um router novo sem a
# label reabriria a porta em silencio — por isso a regra e "todo router", e nao
# uma lista fixa de nomes. Os hosts vem do .env (PUBLIC_HOST, S3_HOST,
# AGENTS_HOST); a borda tambem (BORDA_MIDDLEWARE).

# `traefik.http.routers.<router>.rule=Host(`...`) && ...`
_REGRA_DA_LABEL = re.compile(
    r"traefik\.http\.routers\.(?P<router>[\w-]+)\.rule=(?P<regra>[^\"']+)"
)
_HOSTS_PROXIED = ("Host(`${PUBLIC_HOST:-localhost}`)", "Host(`${S3_HOST:-s3.localhost}`)")
_HOST_DOS_EXECUTORES = "Host(`${AGENTS_HOST:-agents.localhost}`)"
_LISTA = "${BORDA_MIDDLEWARE:-borda-aberta}@file"


def _referencias_cruas() -> dict[str, list[str]]:
    """As referencias como estao escritas no compose, sem interpolar."""
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
    """Se a regex das regras parar de casar, os dois testes abaixo passariam vazios."""
    regras = _regras_por_router()
    proxied = {r for r, g in regras.items() if any(h in g for h in _HOSTS_PROXIED)}
    executores = {r for r, g in regras.items() if _HOST_DOS_EXECUTORES in g}
    assert {"web-prod", "api-mcp", "minio-s3"} <= proxied, sorted(proxied)
    assert {"executores-ws", "executores-enroll"} <= executores, sorted(executores)


def test_todo_router_publico_leva_a_borda_na_frente():
    """Primeira posicao, nao "em algum lugar": o que vem antes dela roda para
    qualquer um — um rate limit na frente, por exemplo, ainda gastaria o balde
    de um IP forjado."""
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
    """Executores conectam de qualquer rede — a lista os trancaria fora."""
    regras = _regras_por_router()
    referencias = _referencias_cruas()
    com_lista = [
        r for r, g in sorted(regras.items())
        if _HOST_DOS_EXECUTORES in g
        and ({_LISTA, "cloudflare-only@file"} & set(referencias.get(r, [])))
    ]
    assert not com_lista, "router de executor com a borda: " + ", ".join(com_lista)


def test_toda_regra_de_host_vem_do_env():
    """Nenhum host de instalacao fixo nas regras: so os tres do .env."""
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


# Itens `- x.x.x.x/nn` do bloco `cloudflare-only:`, que vai ate a proxima chave
# de 4 espacos (o proximo middleware).
_CIDR = re.compile(r"^\s+-\s+([0-9a-fA-F.:]+/\d+)\s*$", re.M)


def _faixas_da_lista() -> set[str]:
    texto = _texto(DINAMICO)
    marca = "    cloudflare-only:\n"
    resto = texto[texto.index(marca) + len(marca):]
    fim = _NOME_DO_MIDDLEWARE.search(resto)
    bloco = resto[: fim.start()] if fim else resto
    return set(_CIDR.findall(bloco))


def test_as_faixas_da_cloudflare_sao_as_mesmas_nos_tres_lugares():
    """A lista vive em tres arquivos, e divergir abre ou fecha a porta errada.

    Uma faixa a menos na allowlist e 403 para parte dos usuarios (a Cloudflare
    chega por varias); uma a mais e um buraco. O backend (CLOUDFLARE_RANGES,
    que acha o IP real no X-Forwarded-For) e o `trustedIPs` dos entrypoints
    tem de concordar com ela. O `trustedIPs` vem do .env
    (BORDA_FAIXAS_CONFIAVEIS); o valor para a Cloudflare e o do exemplo do
    .env.example, so IPv4, que e por onde a Cloudflare alcanca o origin.
    """
    from app.core.trusted_proxy import CLOUDFLARE_RANGES

    faixas = _faixas_da_lista()
    assert len(faixas) >= 20, f"leitura suspeita da allowlist: {sorted(faixas)}"
    assert faixas == set(CLOUDFLARE_RANGES.split(","))
    exemplo = re.search(r"^#BORDA_FAIXAS_CONFIAVEIS=(\S+)$", _texto(RAIZ / ".env.example"), re.M)
    assert exemplo, "o exemplo da Cloudflare sumiu do .env.example"
    assert set(exemplo.group(1).split(",")) == {f for f in faixas if ":" not in f}


def test_sem_cdn_o_traefik_nao_confia_em_ninguem_alem_do_loopback():
    """O padrao do trustedIPs: sem CDN, o Traefik e a borda e reescreve o XFF."""
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
    """O bootstrap-stepca.sh grava agents.crt; o nome antigo fica so na transicao."""
    dinamico = _texto(DINAMICO)
    assert "certFile: /etc/ssl/atlans-ca/agents.crt" in dinamico
    assert "keyFile:  /etc/ssl/atlans-ca/agents.key" in dinamico
    bootstrap = _texto(RAIZ / "scripts" / "bootstrap-stepca.sh")
    assert 'CRT_PATH="traefik/atlans-ca/agents.crt"' in bootstrap
    assert 'KEY_PATH="traefik/atlans-ca/agents.key"' in bootstrap
