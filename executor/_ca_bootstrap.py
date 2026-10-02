"""
Auto-bootstrap do root cert da CA interna atlans.

Rodar `python -m executor` num ambiente novo (sem `SSL_CERT_FILE` setado
e sem `atlans-root.crt` local) hoje quebra com CERTIFICATE_VERIFY_FAILED
— o cert do host dos executores (`agents.<dominio>`) e emitido pela step-ca interna, que nao
esta no trust store do sistema. O `install.sh` do fluxo Docker resolve
isso automaticamente; este modulo faz o mesmo no fluxo Python nativo.

O trust store publicado nas env vars e um bundle COMBINADO — CAs publicas
(certifi) MAIS a CA interna —, nunca a CA interna sozinha: SSL_CERT_FILE
substitui o trust store do processo em vez de somar, e aponta-lo so para a
CA interna quebrava todo acesso HTTPS a servidor publico feito pelos nos de
workflow (WFS, WMS, APIs) com `unable to get local issuer certificate`.

Idempotente: se o cert ja existe em `<EXECUTOR_CERT_DIR>/atlans-root.crt`,
so remonta o bundle e seta as env vars. Se `SSL_CERT_FILE` ja esta setado
externamente, respeita e nao toca. Falhas de download NAO persistem nada:
o bootstrap aborta com instrucao de instalacao manual e o executor segue
o comportamento pre-existente (que provavelmente vai falhar com
CERTIFICATE_VERIFY_FAILED, dizendo ao operador exatamente o que falta).

SEGURANCA: o material baixado aqui vira ANCORA DE CONFIANCA do host —
cobre o OTP do enroll, a chave Ed25519 do cert mTLS e todo job futuro.
Por isso o download so acontece sobre TLS verificado. O unico escape
para ambientes com inspetor SSL corporativo e o pinning explicito por
fingerprint (`ATLANS_CA_SHA256`), que valida o material APOS o download.
Nunca ha um caminho "confia em qualquer coisa": um URL `http://`
(vindo de `--server=ws://...` ou de EXECUTOR_PUBLIC_SERVER_URL) tambem e
recusado, porque ali nao ha cadeia nenhuma para verificar — so o pin por
fingerprint destrava esse caso.

Zero dependencias transitivas: usa apenas stdlib. NAO importa
`executor.config` (que exige `EXECUTOR_ID` — quebraria no 1o boot antes
do enroll) nem `executor.utils.logger` (que carrega o formatter customizado
antes do env estar pronto).
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import ssl
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

_logger = logging.getLogger("executor.ca_bootstrap")


def _emit(level: str, msg: str) -> None:
    """Escreve em stderr direto — o root logger pode não ter handler ainda
    quando o bootstrap roda (antes do import de executor.main)."""
    print(f"[ca-bootstrap] {level}: {msg}", file=sys.stderr, flush=True)
    if level == "ERROR":
        _logger.error(msg)
    elif level == "WARNING":
        _logger.warning(msg)
    elif level == "INFO":
        _logger.info(msg)
    else:
        _logger.debug(msg)

_CERT_FILENAME = "atlans-root.crt"
# Trust store efetivo do processo: CAs publicas + CA interna. Derivado, nunca
# editado a mao — regravado a cada boot quando muda. Ver _ensure_combined_bundle.
_BUNDLE_FILENAME = "atlans-ca-bundle.crt"
_CA_BUNDLE_PATH = "/executores/ca-bundle"
_DOWNLOAD_TIMEOUT_SEC = 15

# Pinning opcional: SHA-256 (hex) do root cert esperado, como sai de
# `openssl x509 -in atlans-root.crt -noout -fingerprint -sha256`. Aceita com
# ou sem os `:`. Quando setado, o material baixado e validado contra ele — e
# so nesse caso a verificacao de cadeia TLS pode ser dispensada (o operador
# ja provou saber o que esperar). Sem ele, TLS verificado e a unica via.
_PIN_ENV = "ATLANS_CA_SHA256"

# O host dos executores (agents.<dominio>) usa cert da step-ca interna — o
# proprio download do CA bundle a partir dele quebraria com CERT_VERIFY_FAILED
# (circular). O install.sh contorna baixando do dominio raiz (cert publico).
# Replicamos aqui: se o server comeca com `agents.`, usamos `<dominio>` para o
# download. EXECUTOR_PUBLIC_SERVER_URL permite override manual quando a
# convencao nao aplica.
_MTLS_SUBDOMAIN_PREFIX = "agents."


def bootstrap_ca() -> None:
    """Garante um trust store que cobre a CA interna E as CAs publicas.

    Chamado como PRIMEIRA linha de `executor/__main__.main()`. Nesse
    ponto nenhum modulo do executor foi importado alem de stdlib do
    __main__ — setar env aqui e visto por todos os httpx.SSLContext
    criados nos sub-comandos (default/enroll/status).
    """
    # 1) Override explicito do operador vence — nao toca.
    if os.environ.get("SSL_CERT_FILE"):
        _emit(
            "INFO",
            f"SSL_CERT_FILE ja setado externamente: {os.environ['SSL_CERT_FILE']} "
            "— o bootstrap nao toca. Esse arquivo SUBSTITUI o trust store do processo: "
            "se ele contiver so a CA interna, os nos de workflow falham ao acessar "
            "qualquer servidor HTTPS publico.",
        )
        return

    cert_dir = Path(os.getenv("EXECUTOR_CERT_DIR") or "./certs")
    cert_path = cert_dir / _CERT_FILENAME

    # 2) Cert ja existe (Docker com install.sh, ou boot subsequente) — reusa.
    if cert_path.is_file() and cert_path.stat().st_size > 0:
        # Se o operador configurou um pin, ele vale AQUI TAMBEM, e nao so no
        # download. O arquivo mora num volume: trocar `atlans-root.crt` por
        # outro e reiniciar o container instalava a CA do atacante como ancora
        # de confianca, em silencio — o pin era verificado exatamente uma vez,
        # no primeiro boot que baixou o bundle, e nunca mais.
        #
        # Falha FECHADA: quem configurou o pin optou por ele. Uma CA rotacionada
        # com pin velho no .env para o boot, e a mensagem diz o que fazer — que
        # e o desfecho certo para um controle de confianca.
        try:
            pins = _expected_pins()
        except ValueError as exc:
            _emit("ERROR", str(exc))
            raise
        if pins:
            # Uma leitura so, e o bundle combinado e montado a partir DESTES
            # bytes. Ler o arquivo aqui e deixar `_set_env` le-lo de novo abriria
            # uma janela para trocar o conteudo entre a verificacao e o uso —
            # contra exatamente o atacante que esta checagem existe para barrar.
            material = cert_path.read_bytes()
            try:
                _assert_pinned(material, pins)
            except Exception as exc:
                _emit(
                    "ERROR",
                    f"Root cert existente em {cert_path.resolve()} NAO casa com "
                    f"{_PIN_ENV}: {exc} "
                    "Se a CA foi rotacionada, acrescente o novo fingerprint a "
                    f"{_PIN_ENV} (aceita varios, separados por virgula) ou apague "
                    "o arquivo para baixar de novo.",
                )
                raise
            _emit("INFO", f"Root cert reutilizado e conferido contra {_PIN_ENV}.")
            _set_env(cert_path, material=material)
            return
        _emit("INFO", f"Root cert reutilizado: {cert_path.resolve()}")
        _set_env(cert_path)
        return

    # 3) Cert ausente — tenta baixar.
    server_url = _resolve_server_url()
    if not server_url:
        # Sem servidor nao ha de onde baixar: nada de padrao apontando para uma
        # instalacao que ninguem escolheu. O enroll traz o --server.
        _emit(
            "WARNING",
            "Root cert da CA interna ausente e nenhum servidor configurado "
            "(EXECUTOR_SERVER_URL, --server ou EXECUTOR_PUBLIC_SERVER_URL): "
            "nada foi baixado.",
        )
        return
    bundle_url = server_url.rstrip("/") + _CA_BUNDLE_PATH

    try:
        cert_dir.mkdir(parents=True, exist_ok=True)
        _download_atomic(bundle_url, cert_path)
    except Exception as exc:
        # ABORTA sem persistir nada. Nao existe fallback sem verificacao: o
        # arquivo viraria ancora de confianca permanente do host, e um atacante
        # on-path so precisaria corromper o handshake para forcar o downgrade.
        _emit(
            "WARNING",
            f"Nao foi possivel baixar root cert de {bundle_url}: "
            f"{type(exc).__name__}: {exc}. "
            f"Nada foi gravado — instale o root cert manualmente:\n"
            f"    curl -o {cert_path} {bundle_url}\n"
            f"  (basta o arquivo no lugar; no proximo boot o bootstrap monta o trust\n"
            f"   store combinado. NAO exporte SSL_CERT_FILE apontando so para ele —\n"
            f"   isso substitui as CAs publicas e quebra os nos que acessam HTTPS.)\n"
            f"  Confira o fingerprint com o admin do Atlans:\n"
            f"    openssl x509 -in {cert_path} -noout -fingerprint -sha256\n"
            f"  Em rede com inspetor SSL corporativo, exporte {_PIN_ENV}=<sha256 esperado> "
            f"e rode de novo — o download e validado contra o fingerprint.",
        )
        return

    _set_env(cert_path)
    _emit("INFO", f"Root cert baixado em {cert_path}")


# ── Helpers ─────────────────────────────────────────────────────────────

def _set_env(cert_path: Path, material: bytes | None = None) -> None:
    """Aponta as env vars de trust store para o bundle COMBINADO (CAs publicas
    + CA interna) — nunca para o root cert interno sozinho.

    Setar SSL_CERT_FILE SUBSTITUI o trust store do processo, nao soma. Apontando
    so para a CA interna, todo HTTPS de saida para servidor publico quebrava com
    `unable to get local issuer certificate` — inclusive dentro dos nos de
    workflow (WFS/WMS via owslib+requests, GDAL/pyogrio, boto3). O executor
    contornava caso a caso no proprio codigo (`utils.build_mtls_ssl_context`,
    `enrollment._resolve_enroll_verify`), mas biblioteca de terceiro le a env var
    direto e nao tem como contornar; a correcao tem que ser aqui.

    As tres env vars cobrem stacks distintas: SSL_CERT_FILE (stdlib ssl, httpx),
    REQUESTS_CA_BUNDLE (requests/urllib3) e CURL_CA_BUNDLE (libcurl — GDAL,
    pyogrio e os drivers /vsicurl ignoram as outras duas).
    """
    p = str(_ensure_combined_bundle(cert_path, material=material))
    os.environ["SSL_CERT_FILE"] = p
    os.environ["REQUESTS_CA_BUNDLE"] = p
    os.environ["CURL_CA_BUNDLE"] = p


def _public_ca_pem() -> tuple[bytes | None, str]:
    """PEM das CAs publicas: certifi (dep do executor), senao o cafile do SO.

    `ssl.get_default_verify_paths()` honra SSL_CERT_FILE, mas aqui ele ainda nao
    foi setado por nos — `bootstrap_ca` retorna cedo quando o operador ja setou —
    entao o cafile lido e mesmo o do sistema, sem risco de auto-referencia.
    """
    try:
        import certifi  # type: ignore
        return Path(certifi.where()).read_bytes(), "certifi"
    except Exception:
        pass

    paths = ssl.get_default_verify_paths()
    for candidate in (paths.cafile, paths.openssl_cafile):
        if candidate and os.path.isfile(candidate):
            try:
                return Path(candidate).read_bytes(), candidate
            except OSError:
                continue
    return None, "none"


def _ensure_combined_bundle(root_cert: Path, material: bytes | None = None) -> Path:
    """Grava (idempotente) `<dir>/atlans-ca-bundle.crt` = CAs publicas + CA interna.

    Retorna o caminho do bundle. Em qualquer falha retorna o proprio `root_cert`:
    o executor continua falando com o host dos executores (que e o que o torna
    utilizavel), e o WARNING explica por que HTTPS publico vai falhar.

    O diretorio de certs pode estar montado read-only (o compose oferece
    `./executor-certs:/data/certs:ro`), por isso o fallback para o tmpdir — o
    bundle e derivado e so precisa sobreviver ao processo.
    """
    if material is not None:
        # Bytes JA verificados contra o pin pelo chamador. Reler o arquivo aqui
        # abriria uma janela entre a verificacao e o uso.
        internal_pem = material.strip()
    else:
        try:
            internal_pem = root_cert.read_bytes().strip()
        except OSError as exc:
            _emit("WARNING", f"Nao foi possivel ler o root cert {root_cert}: {exc}")
            return root_cert.resolve()

    public_pem, source = _public_ca_pem()
    if public_pem is None:
        _emit(
            "WARNING",
            "Nenhum bundle de CAs publicas encontrado (certifi ausente e sistema sem "
            "cafile). O trust store fica so com a CA interna, e toda conexao HTTPS para "
            "servidor publico vai falhar com 'unable to get local issuer certificate' — "
            "incluindo nos de workflow (WFS, WMS, APIs). Instale: pip install certifi",
        )
        return root_cert.resolve()

    payload = public_pem.rstrip() + b"\n" + internal_pem + b"\n"

    last_exc: OSError | None = None
    for target_dir in (root_cert.parent, Path(tempfile.gettempdir())):
        bundle = target_dir / _BUNDLE_FILENAME
        try:
            # Regrava so quando o conteudo muda (root cert renovado, certifi
            # atualizado numa nova imagem) — boot normal nao toca o disco.
            if not (bundle.is_file() and bundle.read_bytes() == payload):
                tmp = bundle.with_suffix(bundle.suffix + ".tmp")
                tmp.write_bytes(payload)
                os.replace(tmp, bundle)
                _emit("INFO", f"Trust store combinado ({source} + CA interna): {bundle}")
            return bundle.resolve()
        except OSError as exc:
            last_exc = exc

    _emit(
        "WARNING",
        f"Nao foi possivel gravar o trust store combinado ({last_exc}). Usando so a CA "
        "interna — HTTPS para servidores publicos vai falhar com 'unable to get local "
        "issuer certificate'.",
    )
    return root_cert.resolve()


def _do_env_do_executor(nome: str) -> str:
    """O valor no `executor/.env` (`_env_utils.read_env_var`, stdlib puro), sem
    as aspas que o dotenv tiraria; vazio se nao houver."""
    from executor._env_utils import read_env_var

    try:
        valor = (read_env_var(nome) or "").strip()
    except Exception:
        return ""
    if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
        valor = valor[1:-1]
    return valor


def _resolve_server_url() -> str:
    """
    Resolve o URL para download do CA bundle.

    Ordem de prioridade:
      1. EXECUTOR_PUBLIC_SERVER_URL do env — override explicito quando a
         convencao agents.<dominio> nao aplica.
      2. --server=<X> ou --server <X> no argv (preferido para enroll),
         convertido: agents.<dominio> -> <dominio>.
      3. EXECUTOR_SERVER_URL do ambiente ou, sem ele, do `executor/.env`, mesma
         conversao. O `.env` pelo motivo de `_expected_pins`: este bootstrap
         roda antes do `load_dotenv()` de `executor/config.py`, e no executor
         nativo (systemd, terminal) o servidor so existe no arquivo.
      4. Nenhum dos tres: vazio, e nada e baixado.

    Depois converte wss:// -> https:// e ws:// -> http://. Feito inline
    (sem importar `executor.utils.ws_to_http`) para nao carregar config.

    A conversao PRESERVA o `http://` de um `--server=ws://...` de proposito:
    quem decide o que fazer com ele e `_download_atomic`, que recusa baixar a
    ancora de confianca por canal nao verificado (a menos que ATLANS_CA_SHA256
    esteja setado). Reescrever para https aqui esconderia o problema atras de um
    erro de conexao confuso.
    """
    public_override = os.getenv("EXECUTOR_PUBLIC_SERVER_URL")
    if public_override:
        return public_override.replace("wss://", "https://").replace("ws://", "http://")

    from_argv = _parse_server_from_argv(sys.argv[1:])
    server = (from_argv or os.getenv("EXECUTOR_SERVER_URL") or _do_env_do_executor("EXECUTOR_SERVER_URL")).strip()
    if not server:
        return ""
    server = server.replace("wss://", "https://").replace("ws://", "http://")
    return _strip_mtls_subdomain(server)


def _strip_mtls_subdomain(url: str) -> str:
    """`https://agents.<dominio>` -> `https://<dominio>`. Se o host nao
    comeca com `agents.`, retorna igual. Preserva scheme, path, port."""
    from urllib.parse import urlsplit, urlunsplit
    parts = urlsplit(url)
    host = parts.hostname or ""
    if not host.startswith(_MTLS_SUBDOMAIN_PREFIX):
        return url
    new_host = host[len(_MTLS_SUBDOMAIN_PREFIX):]
    # Preserva porta se houver
    netloc = new_host if not parts.port else f"{new_host}:{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def _parse_server_from_argv(argv: list[str]) -> str | None:
    """Parse defensivo — nao mexe no argv, nao usa argparse (que
    consumiria args conhecidos e quebraria o dispatcher do __main__).
    Aceita as duas formas comuns: `--server=URL` e `--server URL`.
    """
    for i, arg in enumerate(argv):
        if arg.startswith("--server="):
            return arg[len("--server="):]
        if arg == "--server" and i + 1 < len(argv):
            return argv[i + 1]
    return None


def _expected_pins() -> frozenset[str]:
    """Fingerprints SHA-256 aceitos para o root cert, normalizados.

    Fontes, nesta ordem: `ATLANS_CA_SHA256` no ambiente, depois no
    `executor/.env`. O `.env` importa porque `bootstrap_ca()` e a PRIMEIRA linha
    de `executor/__main__.main()` e roda ANTES do `load_dotenv()` de
    `executor/config.py`: no compose a variavel chega pelo `env_file`, mas nos
    fluxos nativo e desktop o pin gravado pelo instalador so existe no arquivo.

    A leitura usa `_env_utils.read_env_var`, o parser de `.env` que o executor ja
    tem (stdlib puro, usado pelo enrollment). Ter um segundo parser aqui foi um
    erro: os dois divergiram na primeira revisao.

    Aceita VARIOS fingerprints separados por virgula. Sem isso, o pin estrito
    tornava impossivel uma rotacao de CA com sobreposicao — o periodo em que o
    bundle legitimamente carrega o root velho E o novo —, e o executor ficaria
    sem boot ate alguem desligar o pinning, que e o desfecho oposto ao desejado.

    Devolve frozenset vazio quando nao ha pin configurado.
    """
    from executor._env_utils import read_env_var

    # `or`, e nao `is None`: uma env var definida como VAZIA (comum em compose,
    # `ATLANS_CA_SHA256=` sem valor) sombreava o pin gravado no .env e desligava
    # o pinning sem nenhum aviso.
    bruto = os.environ.get(_PIN_ENV) or ""
    if not bruto.strip():
        try:
            bruto = read_env_var(_PIN_ENV) or ""
        except Exception:
            bruto = ""
    if not bruto.strip():
        return frozenset()

    # `export KEY=v` e comentario inline sao formas que o operador escreve a mao
    # e que o parser compartilhado nao trata; normalizar aqui evita divergir dele.
    bruto = bruto.split("#", 1)[0]
    if bruto.lstrip().startswith("export "):
        bruto = bruto.lstrip()[len("export "):]

    pins = set()
    for parte in bruto.replace(";", ",").split(","):
        raw = parte.strip().strip('"').strip("'").replace(":", "").lower()
        if not raw:
            continue
        if len(raw) != 64 or any(c not in "0123456789abcdef" for c in raw):
            raise ValueError(
                f"{_PIN_ENV} invalido: esperado SHA-256 em hex (64 chars, `:` "
                f"opcional, varios separados por virgula), recebido {len(raw)} chars."
            )
        pins.add(raw)
    return frozenset(pins)


# `CERTIFICATE` nao e o unico rotulo que o OpenSSL carrega como ancora:
# `TRUSTED CERTIFICATE` e `X509 CERTIFICATE` tambem entram em
# `load_verify_locations`. Reconhecer so o primeiro deixava a checagem de
# acrescimo ser contornada por um bloco com outro rotulo.
_PEM_CERT_RE = re.compile(
    rb"-----BEGIN (?:TRUSTED |X509 )?CERTIFICATE-----"
    rb".*?"
    rb"-----END (?:TRUSTED |X509 )?CERTIFICATE-----",
    re.DOTALL,
)


def _pem_fingerprints(payload: bytes) -> list[str]:
    """SHA-256 (hex) do DER de cada cert do bundle PEM baixado.

    O fingerprint e calculado sobre o DER, nao sobre os bytes crus do arquivo —
    e assim que `openssl x509 -fingerprint -sha256` calcula, entao o operador
    compara com o valor que o admin passou, e diferencas de whitespace/CRLF ou
    ordem dos certs no bundle nao invalidam a comparacao.
    """
    fps: list[str] = []
    for block in _PEM_CERT_RE.findall(payload):
        # `PEM_cert_to_DER_cert` so aceita o rotulo canonico. Um bloco
        # `TRUSTED CERTIFICATE` levantava e caia no `continue` — ou seja, NAO
        # era contado, que e o oposto do que a checagem de acrescimo precisa: o
        # OpenSSL carrega esse bloco como ancora de confianca do mesmo jeito.
        texto = (block.decode("ascii", errors="replace")
                 .replace("BEGIN TRUSTED CERTIFICATE", "BEGIN CERTIFICATE")
                 .replace("END TRUSTED CERTIFICATE", "END CERTIFICATE")
                 .replace("BEGIN X509 CERTIFICATE", "BEGIN CERTIFICATE")
                 .replace("END X509 CERTIFICATE", "END CERTIFICATE"))
        try:
            der = ssl.PEM_cert_to_DER_cert(texto)
        except Exception:
            # Bloco ilegivel: nao da para provar que e o cert pinado, entao
            # conta como intruso em vez de sumir da verificacao.
            fps.append("<bloco-pem-ilegivel>")
            continue
        fps.append(hashlib.sha256(der).hexdigest())
    return fps


def _assert_pinned(payload: bytes, pins: frozenset[str]) -> None:
    """Aborta se o bundle contiver QUALQUER cert fora do conjunto pinado.

    Exigir "todos batem", e nao "algum bate", e o que fecha o ataque por
    ACRESCIMO. O arquivo inteiro e concatenado as CAs publicas por
    `_ensure_combined_bundle` e o resultado vira o trust store do processo
    (SSL_CERT_FILE/REQUESTS_CA_BUNDLE/CURL_CA_BUNDLE): TODO cert dentro dele
    vira ancora de confianca, e nao so o que casa com o pin. Com a checagem
    frouxa, um bundle com [root_legitimo, ca_do_atacante] passava — o pin casava
    com o primeiro — e a segunda entrava no trust store em silencio.

    O conjunto (e nao um unico valor) e o que mantem viavel a rotacao de CA com
    sobreposicao: durante a troca, o bundle legitimo carrega os dois roots.

    Vale para os dois caminhos (download e reuso do arquivo ja em disco), porque
    os dois terminam alimentando o mesmo bundle combinado.
    """
    found = _pem_fingerprints(payload)
    if not found:
        raise ValueError(
            f"Nenhum cert PEM valido no material a conferir contra {_PIN_ENV}."
        )
    intrusos = sorted(set(found) - pins)
    if intrusos:
        raise ValueError(
            f"Root cert NAO casa com {_PIN_ENV}. Aceitos: {sorted(pins)}; "
            f"o material contem tambem {intrusos}. Possivel interceptacao, "
            "substituicao ou acrescimo de CA — nada foi gravado."
        )


def _build_download_context() -> tuple[ssl.SSLContext | None, str]:
    """SSLContext verificado para o download, na ordem:
      1. `certifi` (a lib traz um bundle de CAs publicos e ja e dep do
         executor). Resolve o gotcha do Windows onde urllib default
         nao tem trust store algum e cai em CERTIFICATE_VERIFY_FAILED.
      2. Default do sistema (`ssl.create_default_context()`). Funciona
         no Linux/macOS onde o OS mantem trust store.
    """
    try:
        import certifi  # type: ignore
        return ssl.create_default_context(cafile=certifi.where()), "certifi"
    except ImportError:
        pass
    try:
        return ssl.create_default_context(), "system"
    except Exception:
        return None, "none"


def _fetch(req: urllib.request.Request, ctx: ssl.SSLContext | None) -> bytes:
    """GET simples com timeout. `ctx=None` usa o default do urllib."""
    open_kwargs: dict = {"timeout": _DOWNLOAD_TIMEOUT_SEC}
    if ctx is not None:
        open_kwargs["context"] = ctx
    with urllib.request.urlopen(req, **open_kwargs) as resp:
        if resp.status != 200:
            raise urllib.error.HTTPError(
                req.full_url, resp.status, f"HTTP {resp.status}", resp.headers, None,
            )
        payload = resp.read()
    if not payload.strip():
        raise ValueError("Endpoint retornou payload vazio.")
    return payload


def _download_atomic(url: str, dest: Path) -> None:
    """Baixa `url` para `dest.tmp` e faz rename atomico — evita cert
    corrompido se o processo for interrompido no meio do download.

    So grava sobre TLS VERIFICADO. Nao existe fallback nao verificado: o
    arquivo resultante e a ancora de confianca do host, entao um downgrade
    acionavel por qualquer erro de handshake daria a um atacante on-path
    comprometimento persistente (OTP do enroll, chave do cert mTLS, jobs).

    Isso inclui o SCHEME: `http://` nao e um TLS que falhou, e um TLS que nunca
    existiu — o SSLContext montado abaixo seria simplesmente ignorado pelo
    urllib e o payload chegaria em texto claro. Sem pin, aborta.

    Escape unico para inspetor SSL corporativo (ou para o `http://` do on-prem):
    `ATLANS_CA_SHA256`. Com o fingerprint pinado a cadeia pode nao validar, mas o
    material baixado e conferido contra o pin ANTES de qualquer escrita —
    divergencia aborta.
    """
    from urllib.parse import urlsplit

    tmp = dest.with_suffix(dest.suffix + ".tmp")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "atlans-executor-bootstrap/1.0"},
    )

    pins = _expected_pins()

    scheme = (urlsplit(url).scheme or "").lower()
    if scheme != "https" and not pins:
        raise ValueError(
            f"Recusando baixar a ancora de confianca por '{scheme}://' ({url}). "
            "O root cert baixado vira trust store de TODA conexao TLS de saida "
            "deste host (SSL_CERT_FILE/REQUESTS_CA_BUNDLE), entao um atacante "
            "on-path so precisaria responder este GET para se tornar CA confiavel. "
            f"Use https:// no --server/EXECUTOR_PUBLIC_SERVER_URL, ou exporte "
            f"{_PIN_ENV}=<sha256 esperado> — com o pin, a integridade nao depende "
            "do canal."
        )

    ctx, ctx_source = _build_download_context()

    attempts: list[tuple[ssl.SSLContext | None, str]] = [(ctx, ctx_source)]
    if pins:
        attempts.append((ssl._create_unverified_context(), "pinned-sha256"))

    last_exc: Exception | None = None
    payload: bytes | None = None
    used_source = ctx_source
    for attempt_ctx, source in attempts:
        if source == "pinned-sha256":
            _emit(
                "WARNING",
                f"TLS verificado falhou ({type(last_exc).__name__}: {last_exc}). "
                f"Tentando de novo sem validar a cadeia porque {_PIN_ENV} esta "
                "setado — o cert baixado sera aceito somente se casar com o "
                "fingerprint pinado.",
            )
        try:
            payload = _fetch(req, attempt_ctx)
            used_source = source
            break
        except urllib.error.HTTPError:
            # Resposta do servidor (404, 500...): trocar de contexto TLS nao ajuda.
            raise
        except urllib.error.URLError as exc:
            # urllib encapsula o SSLError do handshake em URLError.reason — o
            # `except ssl.SSLError` anterior nunca casava e a segunda tentativa
            # so acontecia por acaso.
            if not isinstance(exc.reason, ssl.SSLError):
                raise  # DNS, connection refused, timeout: nao e problema de cadeia
            last_exc = exc
            continue
        except ssl.SSLError as exc:
            last_exc = exc
            continue

    if payload is None:
        raise last_exc or RuntimeError("Download do root cert falhou sem excecao registrada.")

    # Validacao ANTES de escrever: nada toca o disco se o pin divergir.
    if pins:
        _assert_pinned(payload, pins)

    tmp.write_bytes(payload)
    os.replace(tmp, dest)
    if used_source != "certifi":
        _emit("INFO", f"Root cert baixado usando SSL source={used_source}")
