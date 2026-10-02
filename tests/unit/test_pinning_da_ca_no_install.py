# tests/unit/test_pinning_da_ca_no_install.py
"""
Pinning do root cert da CA no install.sh servido.

`STEPCA_ROOT_FINGERPRINT` era lida em `app/core/config.py` e nunca usada em
lugar nenhum do backend, enquanto `docs/mtls-bootstrap.md:77` afirmava que o
backend a usava "ao montar o install.sh". O executor sempre teve suporte a
pinning (`ATLANS_CA_SHA256`, em executor/_ca_bootstrap.py) — o que faltava era
alguem publicar o valor.

O efeito da lacuna: o `curl .../ca-bundle` do instalador era TOFU puro. Quem
conseguisse responder no lugar do servidor entregava a propria CA, e o executor
passaria a confiar em certs assinados por ela.

Tres niveis de teste, porque cada um pega uma classe diferente de erro:

  INJECAO    o servidor de fato substitui a linha do script.
  DEGRADACAO config vazia ou invalida nao pode quebrar o instalador.
  EXECUCAO   o shell gerado realmente aceita o cert certo e recusa o errado.
"""
from __future__ import annotations

import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

from app.api.routers.executores_router import (
    _LINHA_PIN_CA, _injetar_fingerprint_da_ca, _normalizar_fingerprint,
)

RAIZ = Path(__file__).resolve().parents[2]
INSTALL_SH = RAIZ / "static" / "install.sh"

FP = "a" * 64


# ── INJECAO ──────────────────────────────────────────────────────────────────

def test_a_linha_de_pinning_existe_no_script():
    """Ancora o acoplamento: o servidor substitui esta string exata."""
    assert _LINHA_PIN_CA in INSTALL_SH.read_text(encoding="utf-8"), (
        "static/install.sh perdeu a linha que o servidor substitui — o "
        "fingerprint deixaria de ser publicado, em silencio"
    )


def test_fingerprint_configurado_vira_default_no_script(monkeypatch):
    monkeypatch.setattr("app.core.config.STEPCA_ROOT_FINGERPRINT", FP)
    saida = _injetar_fingerprint_da_ca(INSTALL_SH.read_text(encoding="utf-8"))

    assert f'CA_SHA256_PIN="${{ATLANS_CA_SHA256:-{FP}}}"' in saida
    assert _LINHA_PIN_CA not in saida


def test_o_ambiente_ainda_tem_prioridade_sobre_o_injetado(monkeypatch):
    """`${ATLANS_CA_SHA256:-<fp>}` preserva o override do operador."""
    monkeypatch.setattr("app.core.config.STEPCA_ROOT_FINGERPRINT", FP)
    saida = _injetar_fingerprint_da_ca(INSTALL_SH.read_text(encoding="utf-8"))
    assert "${ATLANS_CA_SHA256:-" in saida


@pytest.mark.parametrize("bruto,esperado", [
    ("AB:CD:" + "EF" * 29 + ":01", "abcd" + "ef" * 29 + "01"),
    ("  " + "A" * 64 + "\n", "a" * 64),
])
def test_normalizacao_aceita_os_dois_formatos_de_ferramenta(bruto, esperado):
    """`step certificate fingerprint` da hex puro; `openssl` da com ':'."""
    assert _normalizar_fingerprint(bruto) == esperado


# ── DEGRADACAO ───────────────────────────────────────────────────────────────

def test_sem_configuracao_o_script_sai_intacto(monkeypatch):
    monkeypatch.setattr("app.core.config.STEPCA_ROOT_FINGERPRINT", "")
    original = INSTALL_SH.read_text(encoding="utf-8")
    assert _injetar_fingerprint_da_ca(original) == original


@pytest.mark.parametrize("invalido", ["abc", "z" * 64, "a" * 63])
def test_fingerprint_invalido_nao_e_injetado(monkeypatch, invalido):
    """Injetar lixo faria TODO instalador abortar numa comparacao impossivel."""
    monkeypatch.setattr("app.core.config.STEPCA_ROOT_FINGERPRINT", invalido)
    original = INSTALL_SH.read_text(encoding="utf-8")
    assert _injetar_fingerprint_da_ca(original) == original


def test_script_sem_a_linha_esperada_nao_quebra(monkeypatch):
    monkeypatch.setattr("app.core.config.STEPCA_ROOT_FINGERPRINT", FP)
    assert _injetar_fingerprint_da_ca("#!/bin/bash\necho oi\n") == "#!/bin/bash\necho oi\n"


def test_o_script_continua_sintaticamente_valido_depois_da_injecao(monkeypatch):
    monkeypatch.setattr("app.core.config.STEPCA_ROOT_FINGERPRINT", FP)
    saida = _injetar_fingerprint_da_ca(INSTALL_SH.read_text(encoding="utf-8"))

    proc = subprocess.run(["bash", "-n"], input=saida, text=True, capture_output=True)
    assert proc.returncode == 0, f"install.sh injetado nao e bash valido:\n{proc.stderr}"


# ── EXECUCAO ─────────────────────────────────────────────────────────────────
#
# Recorta o bloco de verificacao do install.sh e roda de verdade, contra um
# cert gerado na hora. Sem isto, um erro de normalizacao (':' sobrando, hex
# maiusculo, `cut` no campo errado) passaria por todos os testes acima e
# quebraria todo enrollment em producao.

_BLOCO = """
set -euo pipefail
err()  { printf "ERR %s\\n" "$*" >&2; }
warn() { printf "WARN %s\\n" "$*"; }
ok()   { printf "OK %s\\n" "$*"; }
die()  { err "$*"; exit 1; }
CA_SHA256_PIN="${PIN}"
if [[ -n "$CA_SHA256_PIN" ]]; then
    _esperados=$(printf '%s' "$CA_SHA256_PIN" | tr 'A-Z' 'a-z' | tr -d ': ' | tr ',;' '\\n\\n')
    _tmp_split=$(mktemp -d)
    awk -v d="$_tmp_split" '
        /-----BEGIN( TRUSTED| X509)? CERTIFICATE-----/ { n++; f = sprintf("%s/c%03d.pem", d, n) }
        n { print > f }
    ' "$CERT"
    _blocos=$(find "$_tmp_split" -name 'c*.pem' | wc -l | tr -d '[:space:]')
    if [[ "$_blocos" -eq 0 ]]; then
        rm -rf "$_tmp_split"; die "sem cert"
    fi
    _intrusos=""
    for _bloco in "$_tmp_split"/c*.pem; do
        sed -e 's/TRUSTED CERTIFICATE/CERTIFICATE/g; s/X509 CERTIFICATE/CERTIFICATE/g' \\
            "$_bloco" > "$_bloco.norm"
        _fp=$(openssl x509 -in "$_bloco.norm" -noout -fingerprint -sha256 2>/dev/null \\
            | cut -d= -f2 | tr 'A-Z' 'a-z' | tr -d ': ' || true)
        if [[ -z "$_fp" ]] || ! printf '%s\\n' "$_esperados" | grep -qx "$_fp"; then
            _intrusos="$_intrusos ${_fp:-<bloco-ilegivel>}"
        fi
    done
    rm -rf "$_tmp_split"
    if [[ -n "$_intrusos" ]]; then
        die "MISMATCH intrusos=$_intrusos"
    fi
    ok "conferido $_blocos"
else
    warn "sem pin"
fi
"""


@pytest.fixture
def cert(tmp_path):
    """Gera um self-signed e devolve (caminho, fingerprint sha256 hex)."""
    if not shutil.which("openssl"):
        pytest.skip("openssl ausente")
    caminho = tmp_path / "root.crt"
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(tmp_path / "k.pem"), "-out", str(caminho),
         "-days", "1", "-subj", "/CN=teste"],
        check=True, capture_output=True,
    )
    saida = subprocess.run(
        ["openssl", "x509", "-in", str(caminho), "-noout", "-fingerprint", "-sha256"],
        check=True, capture_output=True, text=True,
    ).stdout
    fp = saida.split("=", 1)[1].strip().replace(":", "").lower()
    return caminho, fp


def _rodar(cert_path, pin):
    return subprocess.run(
        ["bash", "-c", textwrap.dedent(_BLOCO)],
        env={"PATH": "/usr/bin:/bin:/usr/local/bin", "CERT": str(cert_path), "PIN": pin},
        capture_output=True, text=True, timeout=60,
    )


def test_cert_correto_passa_na_verificacao(cert):
    caminho, fp = cert
    r = _rodar(caminho, fp)
    assert r.returncode == 0, r.stderr
    assert "OK conferido" in r.stdout


def test_fingerprint_com_dois_pontos_e_maiusculo_tambem_passa(cert):
    """O operador cola o que a ferramenta dele imprimiu."""
    caminho, fp = cert
    com_dois_pontos = ":".join(fp[i:i + 2] for i in range(0, len(fp), 2)).upper()
    assert _rodar(caminho, com_dois_pontos).returncode == 0


def test_cert_errado_aborta_a_instalacao(cert):
    """A propriedade central: CA trocada nao passa."""
    caminho, _ = cert
    r = _rodar(caminho, "b" * 64)
    assert r.returncode != 0
    assert "MISMATCH" in r.stderr


def test_sem_pin_o_instalador_avisa_e_segue(cert):
    """Comportamento antigo preservado para servidor sem a variavel."""
    caminho, _ = cert
    r = _rodar(caminho, "")
    assert r.returncode == 0
    assert "WARN sem pin" in r.stdout


# ── PERSISTENCIA ─────────────────────────────────────────────────────────────
#
# Onde o pin de fato passa a valer a cada boot.
#
# `_ca_bootstrap.bootstrap_ca()` retorna cedo quando `SSL_CERT_FILE` ja esta
# setado — e o container de enrollment o seta, apontando para o cert que o shell
# ja verificou. Logo o `-e ATLANS_CA_SHA256` daquele comando e inerte, e a
# verificacao "a cada boot" so existe se o valor chegar ao servico de longa
# duracao, que NAO seta SSL_CERT_FILE. O caminho para isso e o `executor/.env`.

def _bloco_de_persistencia() -> str:
    """O trecho do install.sh que grava o pin em executor/.env.

    Delimitado por marcadores estaveis em vez de fatiar por offset: a versao
    anterior pegava os 600 caracteres anteriores a uma string e quebrou assim
    que um comentario foi acrescentado acima dela.
    """
    fonte = INSTALL_SH.read_text(encoding="utf-8")
    inicio = fonte.index("Persiste o fingerprint no .env")
    fim = fonte.index("chmod 660 executor/.env", inicio)
    return fonte[inicio:fim]


def test_o_instalador_grava_o_pin_no_env_do_executor():
    bloco = _bloco_de_persistencia()
    assert "ATLANS_CA_SHA256=" in bloco, (
        "o instalador nao persiste o pin em executor/.env — sem isso o servico "
        "de longa duracao nunca reconfere a CA"
    )
    # A gravacao tem de ser condicional: sem pin publicado, nada a escrever.
    assert 'if [[ -n "$CA_SHA256_PIN" ]]' in bloco, (
        "a gravacao no .env precisa ser condicional ao pin existir"
    )


def test_o_pin_gravado_e_normalizado():
    """O .env e lido por `_expected_pins()`, que espera hex minusculo."""
    bloco = _bloco_de_persistencia()
    assert "tr 'A-Z' 'a-z'" in bloco and "tr -d ': '" in bloco, (
        "o valor gravado no .env precisa da mesma normalizacao da comparacao"
    )


def test_gravar_duas_vezes_nao_duplica_a_chave():
    """Rodar o instalador de novo (--force) nao pode deixar duas linhas."""
    bloco = _bloco_de_persistencia()
    assert "grep -qE '^[[:space:]]*(export[[:space:]]+)?ATLANS_CA_SHA256='" in bloco, (
        "sem checar a existencia (inclusive com `export`), um segundo run "
        "acrescenta uma linha duplicada"
    )


def test_a_doc_nao_promete_verificacao_no_container_de_enrollment():
    """A doc ja afirmou uma camada que nao roda; nao pode voltar a afirmar."""
    doc = (RAIZ / "docs" / "mtls-bootstrap.md").read_text(encoding="utf-8")
    assert "SSL_CERT_FILE" in doc, (
        "a doc precisa explicar por que o container de enrollment nao reverifica"
    )
    assert "bootstrap_ca()" in doc


# ── REUSO ────────────────────────────────────────────────────────────────────
#
# O pin tem de valer no caminho de REUSO, e nao so no download.
#
# `bootstrap_ca()` reusa `atlans-root.crt` quando ele ja existe no cert_dir —
# que e um volume. O pin so era conferido dentro de `_download_atomic`, entao a
# verificacao acontecia UMA vez, no primeiro boot que baixou o bundle. Trocar o
# arquivo no volume e reiniciar instalava a CA do atacante como ancora de
# confianca, sem nenhum aviso.

_TRUST_VARS = ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE", "ATLANS_CA_SHA256")


@pytest.fixture(autouse=True)
def _trust_env_limpo():
    """Isola as env vars de trust store, na entrada E na saida.

    monkeypatch nao basta: `_set_env` escreve em os.environ direto, e
    `monkeypatch.delenv(..., raising=False)` nao registra nada quando a chave
    esta ausente — as tres vars vazariam para os testes seguintes apontando para
    um bundle em tmp_path ja apagado. Mesmo motivo (e mesma forma) da fixture
    autouse de tests/unit/test_ca_bundle_trust_store.py.
    """
    import os as _os
    antes = {v: _os.environ.get(v) for v in _TRUST_VARS}
    for v in _TRUST_VARS:
        _os.environ.pop(v, None)
    yield
    for v, valor in antes.items():
        if valor is None:
            _os.environ.pop(v, None)
        else:
            _os.environ[v] = valor


@pytest.fixture
def cert_dir(tmp_path, monkeypatch):
    """Simula o volume do executor, com um root cert ja instalado."""
    if not shutil.which("openssl"):
        pytest.skip("openssl ausente")
    d = tmp_path / "certs"
    d.mkdir()
    caminho = d / "atlans-root.crt"
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(tmp_path / "k.pem"), "-out", str(caminho),
         "-days", "1", "-subj", "/CN=atlans-teste"],
        check=True, capture_output=True,
    )
    saida = subprocess.run(
        ["openssl", "x509", "-in", str(caminho), "-noout", "-fingerprint", "-sha256"],
        check=True, capture_output=True, text=True,
    ).stdout
    fp = saida.split("=", 1)[1].strip().replace(":", "").lower()

    monkeypatch.setenv("EXECUTOR_CERT_DIR", str(d))
    # `_expected_pin` cai no `.env` quando a env var nao existe; aponta para um
    # arquivo vazio para o teste controlar as duas fontes.
    (tmp_path / "vazio.env").write_text("", encoding="utf-8")
    monkeypatch.setenv("EXECUTOR_ENV_PATH", str(tmp_path / "vazio.env"))
    return caminho, fp


def test_reuso_com_pin_correto_segue_normalmente(cert_dir, monkeypatch):
    from executor import _ca_bootstrap

    caminho, fp = cert_dir
    monkeypatch.setenv("ATLANS_CA_SHA256", fp)

    _ca_bootstrap.bootstrap_ca()

    import os
    assert os.environ.get("SSL_CERT_FILE"), "o trust store deveria ter sido montado"


def test_cert_TROCADO_no_volume_para_o_boot(cert_dir, monkeypatch):
    """A regressao de seguranca: swap do arquivo + restart nao pode passar."""
    from executor import _ca_bootstrap

    caminho, fp = cert_dir
    # O pin continua sendo o do cert legitimo...
    monkeypatch.setenv("ATLANS_CA_SHA256", fp)
    # ...mas alguem trocou o arquivo no volume.
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(caminho.parent / "atacante.key"), "-out", str(caminho),
         "-days", "1", "-subj", "/CN=atacante"],
        check=True, capture_output=True,
    )

    with pytest.raises(Exception) as exc:
        _ca_bootstrap.bootstrap_ca()
    assert "ATLANS_CA_SHA256" in str(exc.value) or "casa" in str(exc.value).lower()


def test_sem_pin_o_reuso_continua_como_antes(cert_dir, monkeypatch):
    """Quem nao configurou pinning nao pode ter o boot quebrado por isto."""
    from executor import _ca_bootstrap

    monkeypatch.delenv("ATLANS_CA_SHA256", raising=False)
    _ca_bootstrap.bootstrap_ca()

    import os
    assert os.environ.get("SSL_CERT_FILE")


def test_ACRESCIMO_de_CA_ao_bundle_tambem_e_barrado(cert_dir, monkeypatch):
    """O furo que "algum cert casa" deixava passar.

    `_set_env` concatena o arquivo inteiro as CAs publicas e publica o resultado
    em SSL_CERT_FILE/REQUESTS_CA_BUNDLE/CURL_CA_BUNDLE — TODO cert dentro dele
    vira ancora de confianca. Com a checagem frouxa, um atacante nao precisava
    SUBSTITUIR o root: bastava ACRESCENTAR a propria CA ao arquivo. O pin casava
    com o cert legitimo, a verificacao passava, e a CA extra entrava no trust
    store em silencio.
    """
    from executor import _ca_bootstrap

    caminho, fp = cert_dir
    monkeypatch.setenv("ATLANS_CA_SHA256", fp)

    # Root legitimo PRESERVADO; a CA do atacante vem depois, no mesmo arquivo.
    intruso = caminho.parent / "intruso.crt"
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(caminho.parent / "intruso.key"), "-out", str(intruso),
         "-days", "1", "-subj", "/CN=atacante"],
        check=True, capture_output=True,
    )
    caminho.write_bytes(caminho.read_bytes() + b"\n" + intruso.read_bytes())

    with pytest.raises(Exception) as exc:
        _ca_bootstrap.bootstrap_ca()
    assert "acrescimo" in str(exc.value).lower() or "encontrado" in str(exc.value).lower()


def test_pin_vindo_do_env_file_e_respeitado(cert_dir, monkeypatch, tmp_path):
    """`bootstrap_ca` roda ANTES do load_dotenv de executor/config.py.

    No compose a variavel chega pelo `env_file` do container e isso nao aparece;
    nos fluxos nativo e desktop, o pin que o instalador grava em `executor/.env`
    ficava invisivel — o bootstrap caia no ramo "sem pin" e nao conferia nada,
    contra o que a doc promete.
    """
    from executor import _ca_bootstrap

    caminho, fp = cert_dir
    monkeypatch.delenv("ATLANS_CA_SHA256", raising=False)
    env = tmp_path / "com-pin.env"
    env.write_text(f"# comentario\nOUTRA=coisa\nATLANS_CA_SHA256={fp}\n", encoding="utf-8")
    monkeypatch.setenv("EXECUTOR_ENV_PATH", str(env))

    assert _ca_bootstrap._expected_pins() == frozenset({fp})

    # E o pin do .env de fato barra um cert trocado.
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(caminho.parent / "outro.key"), "-out", str(caminho),
         "-days", "1", "-subj", "/CN=outro"],
        check=True, capture_output=True,
    )
    with pytest.raises(Exception):
        _ca_bootstrap.bootstrap_ca()


def test_ambiente_tem_prioridade_sobre_o_env_file(cert_dir, monkeypatch, tmp_path):
    from executor import _ca_bootstrap

    env = tmp_path / "com-pin.env"
    env.write_text("ATLANS_CA_SHA256=" + "b" * 64 + "\n", encoding="utf-8")
    monkeypatch.setenv("EXECUTOR_ENV_PATH", str(env))
    monkeypatch.setenv("ATLANS_CA_SHA256", "a" * 64)

    assert _ca_bootstrap._expected_pins() == frozenset({"a" * 64})


def test_emit_de_ERROR_chega_ao_logger(caplog):
    """A mensagem de pin divergente caia em `debug` e sumia do log persistido."""
    import logging
    from executor import _ca_bootstrap

    with caplog.at_level(logging.ERROR, logger="executor.ca_bootstrap"):
        _ca_bootstrap._emit("ERROR", "pin divergente de teste")

    assert any(r.levelno == logging.ERROR for r in caplog.records), (
        "_emit('ERROR') precisa chegar ao logger como ERROR"
    )


def test_multiplos_pins_permitem_rotacao_com_sobreposicao(cert_dir, monkeypatch, tmp_path):
    """O pin estrito nao pode impedir a troca de CA.

    Durante a rotacao o bundle legitimamente carrega o root velho E o novo. Com
    um pin unico e a checagem "todos batem", o executor ficaria sem boot ate
    alguem DESLIGAR o pinning — o desfecho oposto ao pretendido.
    """
    from executor import _ca_bootstrap

    caminho, fp_velho = cert_dir

    novo = caminho.parent / "novo.crt"
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(caminho.parent / "novo.key"), "-out", str(novo),
         "-days", "1", "-subj", "/CN=atlans-novo"],
        check=True, capture_output=True,
    )
    fp_novo = subprocess.run(
        ["openssl", "x509", "-in", str(novo), "-noout", "-fingerprint", "-sha256"],
        check=True, capture_output=True, text=True,
    ).stdout.split("=", 1)[1].strip().replace(":", "").lower()

    # Bundle de sobreposicao: os dois roots.
    caminho.write_bytes(caminho.read_bytes() + b"\n" + novo.read_bytes())
    monkeypatch.setenv("ATLANS_CA_SHA256", f"{fp_velho},{fp_novo}")

    _ca_bootstrap.bootstrap_ca()  # nao levanta

    import os
    assert os.environ.get("SSL_CERT_FILE")


def test_rotulo_TRUSTED_CERTIFICATE_tambem_e_contado(cert_dir, monkeypatch):
    """`CERTIFICATE` nao e o unico rotulo que o OpenSSL carrega como ancora.

    Reconhecer so ele deixava a checagem de acrescimo ser contornada trocando o
    rotulo do bloco intruso.
    """
    from executor import _ca_bootstrap

    caminho, fp = cert_dir
    monkeypatch.setenv("ATLANS_CA_SHA256", fp)

    intruso = caminho.parent / "intruso.crt"
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(caminho.parent / "i.key"), "-out", str(intruso),
         "-days", "1", "-subj", "/CN=atacante"],
        check=True, capture_output=True,
    )
    disfarcado = intruso.read_bytes() \
        .replace(b"BEGIN CERTIFICATE", b"BEGIN TRUSTED CERTIFICATE") \
        .replace(b"END CERTIFICATE", b"END TRUSTED CERTIFICATE")
    caminho.write_bytes(caminho.read_bytes() + b"\n" + disfarcado)

    with pytest.raises(Exception):
        _ca_bootstrap.bootstrap_ca()


def test_pin_com_comentario_inline_nao_derruba_o_boot(cert_dir, monkeypatch, tmp_path):
    """`.env` escrito a mao costuma ter comentario na mesma linha."""
    from executor import _ca_bootstrap

    caminho, fp = cert_dir
    monkeypatch.delenv("ATLANS_CA_SHA256", raising=False)
    env = tmp_path / "com-comentario.env"
    env.write_text(f"export ATLANS_CA_SHA256={fp}  # root de producao\n", encoding="utf-8")
    monkeypatch.setenv("EXECUTOR_ENV_PATH", str(env))

    assert _ca_bootstrap._expected_pins() == frozenset({fp})


def test_a_fixture_de_isolamento_nao_apaga_a_env_do_desenvolvedor(monkeypatch):
    """Regressao da ordem de fixtures.

    Pedida por `cert_dir`, `_trust_env_limpo` era criada DEPOIS do monkeypatch e
    restaurava ANTES do teardown dele — e o monkeypatch, que registrou "ausente"
    para uma var que a fixture ja havia removido, apagava o valor real em
    seguida. Autouse inverte a ordem.
    """
    import os
    assert os.environ.get("SSL_CERT_FILE") is None, (
        "a fixture autouse deveria ter limpado a var para este teste"
    )


def test_instalador_recusa_bundle_com_CA_ACRESCENTADA(cert, tmp_path):
    """O mesmo furo do lado do executor, agora no shell.

    `openssl x509 -in <arquivo>` le so o PRIMEIRO bloco PEM. O arquivo inteiro
    vira trust store, entao [root_legitimo, ca_do_atacante] passava na
    conferencia da instalacao — e virava o SSL_CERT_FILE do container de
    enrollment, que carrega o OTP e gera a chave do cert mTLS.
    """
    caminho, fp = cert
    intruso = tmp_path / "intruso.crt"
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(tmp_path / "i.key"), "-out", str(intruso),
         "-days", "1", "-subj", "/CN=atacante"],
        check=True, capture_output=True,
    )
    juntos = tmp_path / "juntos.crt"
    juntos.write_bytes(caminho.read_bytes() + b"\n" + intruso.read_bytes())

    r = _rodar(juntos, fp)
    assert r.returncode != 0, "bundle com CA acrescentada nao pode passar"
    assert "MISMATCH" in r.stderr


def test_instalador_aceita_bundle_de_rotacao_com_dois_pins(cert, tmp_path):
    caminho, fp = cert
    novo = tmp_path / "novo.crt"
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(tmp_path / "n.key"), "-out", str(novo),
         "-days", "1", "-subj", "/CN=atlans-novo"],
        check=True, capture_output=True,
    )
    fp_novo = subprocess.run(
        ["openssl", "x509", "-in", str(novo), "-noout", "-fingerprint", "-sha256"],
        check=True, capture_output=True, text=True,
    ).stdout.split("=", 1)[1].strip().replace(":", "").lower()

    juntos = tmp_path / "juntos.crt"
    juntos.write_bytes(caminho.read_bytes() + b"\n" + novo.read_bytes())

    r = _rodar(juntos, f"{fp},{fp_novo}")
    assert r.returncode == 0, r.stderr
    assert "OK conferido 2" in r.stdout


def test_instalador_conta_bloco_com_rotulo_TRUSTED(cert, tmp_path):
    caminho, fp = cert
    intruso = tmp_path / "i.crt"
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(tmp_path / "i2.key"), "-out", str(intruso),
         "-days", "1", "-subj", "/CN=atacante"],
        check=True, capture_output=True,
    )
    disfarcado = intruso.read_bytes() \
        .replace(b"BEGIN CERTIFICATE", b"BEGIN TRUSTED CERTIFICATE") \
        .replace(b"END CERTIFICATE", b"END TRUSTED CERTIFICATE")
    juntos = tmp_path / "juntos.crt"
    juntos.write_bytes(caminho.read_bytes() + b"\n" + disfarcado)

    assert _rodar(juntos, fp).returncode != 0


# ── Bordas encontradas na quinta revisao ─────────────────────────────────────

def test_bloco_ilegivel_vira_intruso_e_nao_mata_o_script(cert, tmp_path):
    """Sob `set -euo pipefail`, o openssl falhando abortava o script AQUI.

    O ramo de intruso — e com ele o `rm -f` do bundle — nunca rodava: o arquivo
    do atacante ficava em disco e o instalador morria com "Falha na etapa:
    cabundle", sem dizer por que.
    """
    caminho, fp = cert
    quebrado = tmp_path / "quebrado.crt"
    quebrado.write_bytes(
        caminho.read_bytes()
        + b"\n-----BEGIN CERTIFICATE-----\nnao-e-base64-valido\n-----END CERTIFICATE-----\n"
    )

    r = _rodar(quebrado, fp)
    assert r.returncode != 0
    assert "MISMATCH" in r.stderr, (
        f"esperado o ramo de intruso, veio: {r.stderr[:200]!r}"
    )


def test_contagem_de_blocos_sem_padding():
    """`wc -l` do BSD/macOS pad com espacos — o instalador ja mira macOS.

    Rodar o bloco real nao testa nada aqui: o GNU `wc` do Linux nao pad, entao a
    asserção passaria com ou sem o `tr` que ela diz proteger. O teste simula a
    saida do BSD (`       2`) e verifica que a normalizacao a limpa.
    """
    r = subprocess.run(
        ["bash", "-c", "_b=$(printf '       2\n' | tr -d '[:space:]'); printf 'conferido %s' \"$_b\""],
        capture_output=True, text=True, timeout=30,
    )
    assert r.stdout == "conferido 2", repr(r.stdout)

    # E o install.sh entregue de fato usa a normalizacao.
    fonte = INSTALL_SH.read_text(encoding="utf-8")
    assert "wc -l | tr -d '[:space:]'" in fonte


def test_servidor_injeta_valor_multi_pin(monkeypatch):
    """A doc prescreve `<fp_antigo>,<fp_novo>` na rotacao.

    A validacao de tamanho rejeitava o valor inteiro (129 chars) e o script saia
    SEM pinning — TOFU puro exatamente na janela em que a CA esta trocando.
    """
    dois = f"{'a' * 64},{'b' * 64}"
    monkeypatch.setattr("app.core.config.STEPCA_ROOT_FINGERPRINT", dois)
    saida = _injetar_fingerprint_da_ca(INSTALL_SH.read_text(encoding="utf-8"))
    assert f'CA_SHA256_PIN="${{ATLANS_CA_SHA256:-{dois}}}"' in saida


def test_multi_pin_com_uma_entrada_invalida_e_recusado(monkeypatch):
    monkeypatch.setattr(
        "app.core.config.STEPCA_ROOT_FINGERPRINT", f"{'a' * 64},nao-e-hex",
    )
    original = INSTALL_SH.read_text(encoding="utf-8")
    assert _injetar_fingerprint_da_ca(original) == original


def test_normalizacao_de_multi_pin():
    assert _normalizar_fingerprint(f"AB:{'CD' * 31}:EF, {'a' * 64}") == \
        f"ab{'cd' * 31}ef,{'a' * 64}"


def test_env_var_VAZIA_nao_sombreia_o_pin_do_env_file(cert_dir, monkeypatch, tmp_path):
    """`ATLANS_CA_SHA256=` sem valor e comum em compose.

    Com `if bruto is None`, ela sombreava o pin do .env e desligava o pinning
    sem nenhum aviso.
    """
    from executor import _ca_bootstrap

    _, fp = cert_dir
    monkeypatch.setenv("ATLANS_CA_SHA256", "")
    env = tmp_path / "com-pin.env"
    env.write_text(f"ATLANS_CA_SHA256={fp}\n", encoding="utf-8")
    monkeypatch.setenv("EXECUTOR_ENV_PATH", str(env))

    assert _ca_bootstrap._expected_pins() == frozenset({fp})


def test_remove_env_var_casa_a_MESMA_linha_que_read_env_var(tmp_path):
    """A tolerancia a `export` tinha sido posta so no read.

    `remove_env_var` deixava de casar a linha que o read reportava, e a migracao
    de variavel legada (enrollment.py) virava no-op silencioso.
    """
    from executor import _env_utils

    env = tmp_path / ".env"
    env.write_text("export LEGADO=valor\nOUTRA=x\n", encoding="utf-8")

    assert _env_utils.read_env_var("LEGADO", env) == "valor"
    assert _env_utils.remove_env_var("LEGADO", env) is True
    assert _env_utils.read_env_var("LEGADO", env) is None


def test_persist_env_var_atualiza_linha_com_export(tmp_path):
    """Sem isto o persist ACRESCENTAVA uma segunda linha, e o read (primeira
    ocorrencia vence) continuava devolvendo o valor antigo."""
    from executor import _env_utils

    env = tmp_path / ".env"
    env.write_text("export CHAVE=antigo\n", encoding="utf-8")

    _env_utils.persist_env_var("CHAVE", "novo", env)

    conteudo = env.read_text(encoding="utf-8")
    assert conteudo.count("CHAVE") == 1, f"linha duplicada: {conteudo!r}"
    assert _env_utils.read_env_var("CHAVE", env) == "novo"


def test_o_bloco_executavel_do_teste_nao_divergiu_do_install_sh():
    """`_BLOCO` e uma COPIA do trecho de verificacao do install.sh.

    A copia existe para poder rodar o shell de verdade contra certs reais — o
    que ja pegou tres bugs que nenhum teste de string pegaria. O preco e a
    sincronia, e ela ja quebrou uma vez: o `|| true` foi para o install.sh e nao
    para a copia, e o teste do bloco ilegivel passou a exercitar a versao antiga.

    Este teste trava os pontos que importam. Nao compara caractere a caractere:
    o `_BLOCO` e propositalmente reduzido (sem `rm -f`, sem mensagens longas).
    """
    fonte = INSTALL_SH.read_text(encoding="utf-8")
    for marca in (
        "|| true",                                   # bloco ilegivel nao mata o script
        "tr -d '[:space:]'",                         # wc -l do BSD
        "tr ',;' '\\n\\n'",                          # multi-pin
        "BEGIN( TRUSTED| X509)? CERTIFICATE",        # rotulos alternativos no awk
        "s/TRUSTED CERTIFICATE/CERTIFICATE/g",       # normalizacao antes do openssl
        "grep -qx",                                  # casamento exato do fingerprint
    ):
        assert marca in fonte, f"install.sh perdeu: {marca!r}"
        assert marca in _BLOCO, (
            f"_BLOCO divergiu do install.sh — falta {marca!r}. "
            "O teste passaria exercitando um shell que nao e o entregue."
        )


def test_instalador_ATUALIZA_linha_com_export_em_vez_de_duplicar(tmp_path):
    """A rotacao de CA passava a recusar o boot logo apos o instalador rodar.

    O escritor de .env do install.sh so casava `^ATLANS_CA_SHA256=`. Com uma
    linha `export ATLANS_CA_SHA256=<antigo>`, ele ACRESCENTAVA o novo valor em
    vez de substituir — e `read_env_var` devolve a PRIMEIRA ocorrencia, entao o
    executor continuava pinando a CA velha.
    """
    env = tmp_path / ".env"
    env.write_text("export ATLANS_CA_SHA256=" + "a" * 64 + "\nOUTRA=x\n", encoding="utf-8")
    novo = "b" * 64

    trecho = r'''
set -euo pipefail
_pin_normalizado="$NOVO"
cd "$DIR"
if grep -qE '^[[:space:]]*(export[[:space:]]+)?ATLANS_CA_SHA256=' .env 2>/dev/null; then
    sed -i.bak -E "s|^([[:space:]]*(export[[:space:]]+)?)ATLANS_CA_SHA256=.*|\1ATLANS_CA_SHA256=${_pin_normalizado}|" .env
    rm -f .env.bak
else
    printf 'ATLANS_CA_SHA256=%s\n' "$_pin_normalizado" >> .env
fi
'''
    r = subprocess.run(
        ["bash", "-c", trecho],
        env={"PATH": "/usr/bin:/bin", "DIR": str(tmp_path), "NOVO": novo},
        capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0, r.stderr

    conteudo = env.read_text(encoding="utf-8")
    assert conteudo.count("ATLANS_CA_SHA256") == 1, f"linha duplicada: {conteudo!r}"
    assert "export ATLANS_CA_SHA256=" + novo in conteudo, (
        f"o `export` tem de ser preservado: {conteudo!r}"
    )

    from executor import _env_utils
    assert _env_utils.read_env_var("ATLANS_CA_SHA256", env) == novo


def test_persist_env_var_preserva_o_export(tmp_path):
    """Num .env `source`ado, perder o `export` faz a variavel parar de chegar
    aos processos filhos."""
    from executor import _env_utils

    env = tmp_path / ".env"
    env.write_text("export CHAVE=antigo\n", encoding="utf-8")

    _env_utils.persist_env_var("CHAVE", "novo", env)

    conteudo = env.read_text(encoding="utf-8")
    assert conteudo.strip() == "export CHAVE=novo", repr(conteudo)
