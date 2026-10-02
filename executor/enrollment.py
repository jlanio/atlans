# executor/enrollment.py
"""
Modulo de enrollment do executor via Bootstrap OTP + mTLS.

Fluxo:
  1. Operador roda `python -m executor enroll --otp=... --server=https://...`
  2. Executor gera keypair Ed25519 (cert) + X25519 (envelope encryption de jobs)
  3. Monta CSR com CN=executor-pending
  4. POST /executores/enroll com Authorization: Bearer {otp}
  5. Servidor consome OTP, valida CSR, pede a step-ca para assinar, devolve cert
  6. Executor valida o bundle e troca cert.pem, chain.pem, ca.pem, key.pem e
     x25519_key.pem em CERT_DIR (0o600) via .new + os.replace —
     `_persistir_bundle`, o mesmo caminho do renewal (executor/renewal.py)
  7. Zera o OTP da memoria
"""
from __future__ import annotations

import json
import logging
import os
import platform
import socket
import sys
from pathlib import Path

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.x509.oid import NameOID

from executor.versao import versao_do_executor

logger = logging.getLogger(__name__)


# ── Constantes de filename ────────────────────────────────────────────────────

CERT_FILE  = "cert.pem"
CHAIN_FILE = "chain.pem"
CA_FILE    = "ca.pem"
KEY_FILE   = "key.pem"          # chave privada Ed25519 (cert mTLS)
X25519_KEY_FILE = "x25519_key.pem"  # chave privada X25519 (envelope decrypt)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _ws_to_http(server_url: str) -> str:
    """Converte wss://... -> https://... (e ws:// -> http://)."""
    if server_url.startswith("wss://"):
        return "https://" + server_url[len("wss://"):]
    if server_url.startswith("ws://"):
        return "http://" + server_url[len("ws://"):]
    return server_url


def _find_internal_root_cert(cert_dir: Path) -> Path | None:
    """Localiza o root cert da CA interna, na ordem de precedencia real.

    O quickstart/Docker grava o cert FORA do cert_dir (ex: /atlans-root.crt) e
    aponta SSL_CERT_FILE para la; o _ca_bootstrap respeita esse env e retorna
    cedo. Procurar apenas em `cert_dir` fazia o enroll ignorar exatamente o
    cert que o bootstrap tinha acabado de honrar, caindo no bundle publico —
    que nao contem a CA interna do host dos executores.
    """
    candidatos = [cert_dir / "atlans-root.crt"]
    for env in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
        valor = os.environ.get(env)
        if valor:
            candidatos.append(Path(valor))

    for c in candidatos:
        try:
            if c.is_file() and c.stat().st_size > 0:
                return c
        except OSError:
            continue
    return None


def _resolve_enroll_verify(cert_dir: Path):
    """Contexto TLS para o POST /executores/enroll.

    Combina o trust store padrao (certifi/sistema) COM a CA interna, em vez de
    escolher um ou outro:
      - so a CA interna quebraria um servidor com cert publico (ex: o dominio raiz
        atras do Cloudflare);
      - so o certifi quebra o host dos executores, cujo cert vem da step-ca.
    Mesmo padrao de `executor/utils.py::build_mtls_ssl_context`, usado depois
    do enroll.

    Retorna `(verify, descricao_para_log)`. `verify` e um SSLContext quando ha
    CA interna; senao um path/bool aceito pelo httpx. Passar explicitamente
    evita o gotcha de bibliotecas que usam truststore e ignoram SSL_CERT_FILE.
    """
    root = _find_internal_root_cert(cert_dir)
    if root is not None:
        import ssl
        ctx = ssl.create_default_context()
        try:
            # create_default_context() honra SSL_CERT_FILE — que o quickstart
            # aponta para a CA interna, SUBSTITUINDO o trust store publico em vez
            # de somar a ele. Recarregamos o bundle publico explicitamente para
            # que as CAs do sistema sobrevivam (senao um endpoint publico atras
            # do Cloudflare quebraria no mesmo contexto).
            try:
                import certifi  # type: ignore
                ctx.load_verify_locations(cafile=certifi.where())
            except ImportError:
                ctx.load_default_certs()
            ctx.load_verify_locations(cafile=str(root))
            return ctx, f"sistema + CA interna ({root})"
        except Exception as exc:
            logger.warning("Root cert '%s' invalido (%s) — seguindo sem ele.", root, exc)

    try:
        import certifi  # type: ignore
        return certifi.where(), f"certifi ({certifi.where()})"
    except ImportError:
        return True, "trust store do sistema"


def _generate_keypairs() -> tuple[Ed25519PrivateKey, X25519PrivateKey]:
    """Gera (chave Ed25519 para cert mTLS, chave X25519 para envelope encryption)."""
    return Ed25519PrivateKey.generate(), X25519PrivateKey.generate()


def _build_csr(ed_key: Ed25519PrivateKey, cn: str) -> bytes:
    """
    Monta CSR Ed25519 em PEM. O CN deve ser `executor-{id}` — a step-ca exige
    que o CN do CSR case com o `sub` do OTT (one-time token) que o backend
    gera com `sub=executor-{executor_id}`. Sem isso, step-ca rejeita com 403.
    """
    builder = x509.CertificateSigningRequestBuilder().subject_name(
        x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    )
    csr = builder.sign(ed_key, algorithm=None)  # Ed25519 nao usa hash separado
    return csr.public_bytes(serialization.Encoding.PEM)


def _write_pem(path: Path, content: bytes, mode: int = 0o600) -> None:
    """Escreve PEM com permissoes restritas. Em Windows os.chmod() e no-op mas o NTFS ACL ja restringe."""
    path.write_bytes(content)
    try:
        os.chmod(path, mode)
    except (OSError, NotImplementedError):
        pass  # Windows


def _pem_privado(chave: Ed25519PrivateKey | X25519PrivateKey) -> bytes:
    """Chave privada em PEM PKCS8 sem cifra — o formato de key.pem e x25519_key.pem."""
    return chave.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


def _validate_bundle(bundle: dict, new_key: Ed25519PrivateKey) -> str | None:
    """
    Valida o bundle devolvido pelo /enroll ou pelo /renew-cert ANTES de tocar
    em qualquer arquivo. Retorna None se OK, ou a mensagem do motivo da recusa.

    POR QUE: o renewal fazia `_write_pem(..., bundle.get("ca_pem", "").encode())`
    seguido de `os.replace`. Um `ca_pem` vazio (o servidor ja devolveu "" com
    apenas um WARNING quando o root cert sumia) sobrescrevia o ca.pem BOM por um
    arquivo vazio. A partir dai TODO connect estourava
    X509 NO_CERTIFICATE_OR_CRL_FOUND — inclusive o proprio renewal, que precisa
    do ca.pem para falar com o servidor. O executor ficava offline em backoff
    eterno, sem conseguir se autocorrigir. Um renewal que falha e recuperavel;
    um renewal que corrompe as credenciais, nao. O enroll gravava direto e
    ficou com o mesmo buraco por mais tempo: num RE-enroll, o ca.pem bom virava
    o vazio do servidor.
    """
    # Obrigatorios: sem cert_pem nao ha identidade, e sem ca_pem nao ha trust
    # anchor — este ultimo e exatamente o campo cujo vazio causava o dano.
    #
    # chain_pem NAO entra aqui de proposito. O servidor o preenche com
    # `body.get("ca") or ""` (executor_enrollment_service.sign_csr_via_stepca):
    # vazio e um valor que ele emite legitimamente, e o enroll sempre gravou
    # esse vazio sem reclamar. Exigi-lo aqui deixaria o validador MAIS RIGIDO
    # que o emissor, e a consequencia seria pior que o bug original: o renewal
    # falharia em todo ciclo, silenciosamente, ate o cert expirar e o executor
    # morrer de vez. Chain ausente nao corrompe nada — quem ancora a confianca
    # e o ca_pem.
    for field in ("cert_pem", "ca_pem"):
        value = bundle.get(field)
        if not isinstance(value, str) or not value.strip():
            return f"campo '{field}' ausente ou vazio na resposta do servidor"

    chain_pem = bundle.get("chain_pem")
    if chain_pem is not None and not isinstance(chain_pem, str):
        return "campo 'chain_pem' com tipo invalido na resposta do servidor"

    try:
        cert = x509.load_pem_x509_certificate(bundle["cert_pem"].encode())
    except Exception as exc:
        return f"'cert_pem' nao e um certificado PEM valido: {exc}"

    try:
        ca_certs = x509.load_pem_x509_certificates(bundle["ca_pem"].encode())
    except Exception as exc:
        return f"'ca_pem' nao e um PEM de certificados valido: {exc}"
    if not ca_certs:
        return "'ca_pem' nao contem nenhum certificado"

    # chain_pem so precisa ser PARSEAVEL quando vem preenchido.
    if chain_pem and chain_pem.strip():
        try:
            x509.load_pem_x509_certificates(chain_pem.encode())
        except Exception as exc:
            return f"'chain_pem' nao e um PEM de certificados valido: {exc}"

    # O cert emitido tem que ser da chave que acabamos de gerar — se o servidor
    # devolvesse (por bug ou cache) o cert antigo, o par cert/key ficaria
    # inconsistente e o mTLS quebraria com a mesma cara de "offline eterno".
    issued_pub = cert.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    expected_pub = new_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    if issued_pub != expected_pub:
        return "'cert_pem' nao corresponde a chave privada gerada para este pedido"

    return None


def _persistir_bundle(
    cert_dir: Path,
    bundle: dict,
    chave_ed: Ed25519PrivateKey,
    chave_x: X25519PrivateKey | None = None,
) -> str | None:
    """
    Valida o bundle e troca os arquivos de identidade — o caminho unico do
    enroll e do renewal. Retorna None se gravou, ou o motivo da recusa; na
    recusa NENHUM arquivo foi tocado.

    Tudo vai primeiro para `<nome>.new` e so depois, com todos escritos, cada
    um substitui o original com os.replace (atomico por arquivo). Uma falha de
    escrita no meio (disco cheio) apaga os .new e propaga o erro sem ter trocado
    nada. Os .new que um crash deixar para tras sao limpos no boot
    (executor/config.py::_cleanup_renewal_orphans).

    `chave_x` (a X25519 do envelope) so vem no enroll: o renewal troca o cert
    mTLS, e a chave publica X25519 continua a registrada no servidor.
    """
    problema = _validate_bundle(bundle, chave_ed)
    if problema:
        return problema

    conteudos = [
        (CERT_FILE, bundle["cert_pem"].encode()),
        # chain_pem e opcional (ver _validate_bundle): ausente ou null vira vazio.
        (CHAIN_FILE, (bundle.get("chain_pem") or "").encode()),
        (CA_FILE, bundle["ca_pem"].encode()),
        (KEY_FILE, _pem_privado(chave_ed)),
    ]
    if chave_x is not None:
        conteudos.append((X25519_KEY_FILE, _pem_privado(chave_x)))

    novos = [(cert_dir / (nome + ".new"), cert_dir / nome, dados) for nome, dados in conteudos]
    try:
        for temporario, _final, dados in novos:
            _write_pem(temporario, dados)
    except OSError:
        for temporario, _final, _dados in novos:
            try:
                temporario.unlink(missing_ok=True)
            except OSError:
                pass
        raise
    for temporario, final, _dados in novos:
        os.replace(temporario, final)
    return None


def _pin_server_signing_key(cert_dir: Path, key_b64: str | None) -> str | None:
    """Fixa a chave de assinatura do servidor entregue no bundle do enroll/renew.

    Nao desfaz o enrollment em caso de problema: o cert mTLS ja foi emitido e
    persistido, e reverter isso queimaria o OTP a toa. Mas DIVERGENCIA (a chave
    fixada e outra) nao pode virar so uma linha de log: `pin_key` grava um
    marcador de conflito que faz o proximo boot parar, e aqui devolvemos a
    mensagem para o CLI terminar com falha em vez de imprimir "concluido com
    sucesso". Antes, o comando saia com 0 e o executor subia rejeitando 100% dos
    jobs por assinatura invalida, sem nada ligando os dois fatos.

    Retorna a mensagem de divergencia (fatal para o CLI) ou None.
    """
    from executor.server_key import ServerKeyError, ServerKeyPersistError, pin_key

    if not key_b64:
        logger.warning(
            "Servidor nao devolveu 'server_signing_public_key' no bundle "
            "(EXECUTOR_SIGNING_KEY provavelmente nao configurada no servidor). "
            "O executor tentara fixa-la no primeiro boot."
        )
        return None
    try:
        pin_key(cert_dir, key_b64, source="bundle do enrollment")
    except ServerKeyPersistError as exc:
        # Nao e divergencia: o cert_dir e que nao aceitou a escrita. O boot
        # recorre ao TOFU e segue — nao vale reprovar o enroll por isso.
        logger.error("Nao foi possivel gravar o pin da chave de assinatura: %s", exc)
        return None
    except ServerKeyError as exc:
        logger.error("Nao foi possivel fixar a chave de assinatura do servidor: %s", exc)
        return str(exc)
    return None


def _persist_agent_config_to_env(
    executor_id: str,
    server_url: str | None = None,
    env_path: Path | None = None,
) -> None:
    """
    Semeia o `.env` a partir do `.env.example` (se vazio) e grava EXECUTOR_ID +
    EXECUTOR_SERVER_URL. Tambem remove envs legados que confundem o executor apos
    a migracao mTLS.

    O seed garante que variaveis criticas (EXECUTOR_SERVER_URL, LOG_LEVEL, etc.)
    fiquem populadas desde o primeiro boot — sem isso, o executor caia em
    fallback hardcoded (`wss://localhost`) e o upload falhava com
    `Connection refused`.

    Erros de IO viram WARNING — o enrollment ja persistiu o cert, e a falta
    do EXECUTOR_ID em .env nao impede o operador de adicionar manualmente.
    """
    from executor._env_utils import (
        normalize_server_url_to_ws,
        persist_env_var,
        read_env_var,
        remove_env_var,
        seed_env_from_example,
    )

    # 1. Semeia .env a partir do .env.example (se ainda nao tem config).
    seed_env_from_example(env_path=env_path)

    # 2. Limpa envs legados (idempotente):
    # - EXECUTOR_API_KEY: nao usado mais apos mTLS, fica residual em .envs antigos.
    # - EXECUTOR_PRIVATE_KEY_PATH apontando para path legacy: causava o executor gerar
    #   chave nova em ./agent_key.pem em vez de usar a do enroll em x25519_key.pem.
    remove_env_var("EXECUTOR_API_KEY", env_path)
    legacy_key_path = read_env_var("EXECUTOR_PRIVATE_KEY_PATH", env_path)
    if legacy_key_path and legacy_key_path.strip() in ("./agent_key.pem", "/data/agent_key.pem"):
        remove_env_var("EXECUTOR_PRIVATE_KEY_PATH", env_path)

    # 3. Atualiza EXECUTOR_ID com o valor do enrollment.
    persist_env_var(
        "EXECUTOR_ID",
        executor_id,
        env_path=env_path,
        file_header="# Gerado por `python -m executor enroll`\n",
    )

    # 4. Sobrescreve EXECUTOR_SERVER_URL se o operador passou --server diferente
    # do default do example. Permite deploys staging/dev sem editar .env manual.
    # Normaliza para wss:// porque o executor abre WebSocket — gravar https:// no
    # .env quebra o connect com "scheme isn't ws or wss".
    if server_url:
        persist_env_var(
            "EXECUTOR_SERVER_URL",
            normalize_server_url_to_ws(server_url),
            env_path=env_path,
        )


# ── API publica ────────────────────────────────────────────────────────────────


def _motivo_da_recusa(resp) -> str:
    """O motivo que o servidor deu, no formato em que ele responde.

    Os handlers do servidor devolvem `message` (e não `detail`, o campo cru do
    FastAPI), e o 422 de validação lista os campos recusados em `details`. Lia
    só o `detail`: toda recusa saía com o motivo em branco.
    """
    try:
        corpo = resp.json()
    except Exception:
        return resp.text[:200]
    if not isinstance(corpo, dict):
        return str(corpo)[:200]
    motivo = str(corpo.get("message") or corpo.get("detail") or "")
    campos = [
        f"{'.'.join(str(p) for p in (e.get('loc') or [])[1:])}: {e.get('msg', '')}"
        for e in (corpo.get("details") or []) if isinstance(e, dict)
    ]
    if campos:
        motivo = f"{motivo} ({'; '.join(campos)})" if motivo else "; ".join(campos)
    return motivo[:300]


def enroll(
    server_url: str,
    otp: str,
    executor_id: str,
    cert_dir: str | Path,
    env_path: str | Path | None = None,
) -> dict:
    """
    Executa o enrollment completo: gera keypairs, manda CSR, recebe cert, persiste.

    O `executor_id` deve ser o id_hash do executor (fornecido pelo admin na UI).
    Ele e usado como CN do CSR — step-ca exige que case com o `sub` do OTT.

    `env_path` define onde o EXECUTOR_ID e o EXECUTOR_SERVER_URL sao gravados.
    Sem ele cai no default de `_env_utils` (o `.env` dentro do pacote), que e o
    lugar errado quando quem chama e o app desktop — la a config vive em
    `%APPDATA%\\AtlasExecutor\\config\\.env`.

    Lanca RuntimeError se servidor recusar ou step-ca indisponivel.
    Retorna dict com metadata do cert emitido (serial, fingerprint, expires_at).
    """
    cert_dir = Path(cert_dir)
    cert_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(cert_dir, 0o700)
    except (OSError, NotImplementedError):
        pass

    if not executor_id or not executor_id.strip():
        raise RuntimeError("executor_id e obrigatorio (recebido pelo admin no momento da criacao do executor).")

    logger.info("Gerando keypairs locais...")
    ed_key, x_key = _generate_keypairs()
    csr_pem = _build_csr(ed_key, cn=f"executor-{executor_id}").decode()

    x25519_pub_pem = x_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    body = {
        "csr_pem":        csr_pem,
        "public_key_pem": x25519_pub_pem,
        "hostname":       socket.gethostname()[:255],
        # A mesma do handshake (executor/versao.py): a do build na imagem Docker,
        # a do app no desktop.
        "executor_version":  versao_do_executor(),
        "os":             f"{platform.system()} {platform.release()}"[:64],
    }

    http_base = _ws_to_http(server_url).rstrip("/")
    url = f"{http_base}/executores/enroll"

    # `--server=ws://...` vira http:// e o `verify` abaixo passa a ser decorativo:
    # o OTP viaja em texto claro no header Authorization e qualquer on-path pode
    # consumi-lo para se enrolar como este executor. Nao bloqueamos (on-prem sem
    # TLS e uma escolha deliberada do operador), mas nao pode ser silencioso.
    if not http_base.lower().startswith("https://"):
        logger.warning(
            "Enroll indo por canal NAO CIFRADO (%s): o OTP trafega em texto claro e "
            "o certificado emitido nao tem mais garantia que a rede. Use https:// / "
            "wss:// em qualquer ambiente que nao seja um laboratorio isolado.",
            http_base,
        )

    verify_path, verify_desc = _resolve_enroll_verify(cert_dir)
    logger.info("Enviando CSR para %s (verify=%s)", url, verify_desc)
    try:
        resp = httpx.post(
            url,
            json=body,
            headers={"Authorization": f"Bearer {otp}"},
            timeout=30,
            verify=verify_path,
        )
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Falha de rede no enrollment: {exc}") from exc
    finally:
        # Zera o OTP da memoria assim que possivel.
        otp = None  # noqa: F841

    if resp.status_code != 200 and resp.status_code != 201:
        raise RuntimeError(
            f"Servidor recusou enrollment (status {resp.status_code}): {_motivo_da_recusa(resp)}"
        )

    bundle = resp.json()

    # Persiste cert + chain + CA + chaves privadas pelo mesmo caminho do
    # renewal: valida antes e troca via .new + os.replace. Gravar direto, como
    # antes, aceitava um ca_pem vazio e — num RE-enroll — sobrescrevia o ca.pem
    # bom, deixando o executor sem trust anchor.
    problema = _persistir_bundle(cert_dir, bundle, ed_key, x_key)
    if problema:
        raise RuntimeError(
            f"Servidor devolveu um bundle invalido no enrollment ({problema}). "
            "Nenhum arquivo foi alterado. O OTP ja foi consumido: depois de "
            "corrigir o servidor, gere outro."
        )

    # Fixa a chave de assinatura Ed25519 do servidor que veio no bundle. Este e o
    # momento certo: o bundle ja foi autenticado pelo OTP, entao nao ha janela de
    # "confia na primeira resposta". Sem isto o executor cairia no TOFU do boot
    # (ver executor/server_key.py), que e a brecha que o achado S8 aponta.
    signing_key_conflict = _pin_server_signing_key(
        cert_dir, bundle.get("server_signing_public_key")
    )

    # Semeia executor/.env a partir do .env.example, grava EXECUTOR_ID e atualiza
    # EXECUTOR_SERVER_URL com o valor que o operador passou no --server. Garante
    # que variaveis criticas (LOG_LEVEL, EXECUTOR_SYNC_*, etc.) ja venham populadas.
    _persist_agent_config_to_env(
        executor_id, server_url=server_url,
        env_path=Path(env_path) if env_path else None,
    )

    logger.info(
        "Enrollment OK. Cert serial=%s expira=%s",
        bundle["serial"], bundle["expires_at"],
    )

    return {
        "serial":      bundle["serial"],
        "fingerprint": bundle["fingerprint"],
        "issued_at":   bundle["issued_at"],
        "expires_at":  bundle["expires_at"],
        # Presente (mensagem) quando a chave de assinatura do servidor divergiu da
        # fixada. O cert e valido, mas o executor NAO vai subir ate o operador
        # resolver o conflito — o CLI precisa dizer isso em vez de "sucesso".
        "signing_key_conflict": signing_key_conflict,
    }


# ── CLI entry point ────────────────────────────────────────────────────────────


def _cli_main(argv: list[str]) -> int:
    """
    Subcomando `python -m executor enroll`:
      python -m executor enroll --otp=<otp> --server=https://agents.<dominio> \\
          [--executor-id=<id>] [--cert-dir=./certs]

    Se `--executor-id` nao for passado, le de EXECUTOR_ID env (carregado de executor/.env
    quando rodando via docker compose, ou exportado no shell quando local).
    """
    import argparse
    parser = argparse.ArgumentParser(prog="atlans-executor enroll")
    parser.add_argument(
        "--executor-id", default=None,
        help="ID do executor (id_hash). Default: env EXECUTOR_ID (de executor/.env)",
    )
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--otp", help="OTP fornecido pelo admin (~43 chars)")
    grupo.add_argument(
        "--otp-stdin", action="store_true",
        help="Le o OTP da primeira linha do stdin. Preferivel a --otp: a linha "
             "de comando de um processo e legivel por qualquer outro processo "
             "do mesmo usuario.",
    )
    parser.add_argument("--server", required=True, help="URL do servidor (https:// ou wss://)")
    parser.add_argument("--cert-dir", default="./certs", help="Diretorio para salvar cert + chave (default: ./certs)")
    parser.add_argument(
        "--json", action="store_true",
        help="Emite um unico objeto JSON no stdout, em vez do relatorio humano. "
             "Para quem chama o enrollment de outro programa (o app desktop).",
    )
    args = parser.parse_args(argv)

    # Com --json o stdout e do JSON e de mais nada; o log vai para o stderr,
    # senao a primeira linha INFO do logging quebraria o parse de quem chamou.
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stderr if args.json else sys.stdout,
    )

    def _falhar(mensagem: str, *, codigo: str = "erro") -> int:
        if args.json:
            json.dump({"ok": False, "codigo": codigo, "erro": mensagem}, sys.stdout)
            sys.stdout.write("\n")
            sys.stdout.flush()
        else:
            print(f"FALHA: {mensagem}", file=sys.stderr)
        return 1

    otp = args.otp
    if args.otp_stdin:
        otp = sys.stdin.readline().strip()
        if not otp:
            return _falhar("nenhum OTP recebido no stdin.", codigo="otp_ausente")

    # Carrega executor/.env (no-op se env_file ja foi aplicado pelo docker compose).
    try:
        from dotenv import load_dotenv as _load_dotenv
        _env_path = os.getenv("EXECUTOR_ENV_PATH") or str(Path(__file__).parent / ".env")
        _load_dotenv(dotenv_path=_env_path, override=False)
    except ImportError:
        pass  # python-dotenv ausente: depende do shell ja ter as envs

    # Resolve executor_id: flag CLI > env var > erro claro.
    executor_id = (args.executor_id or os.getenv("EXECUTOR_ID") or "").strip()
    if not executor_id:
        return _falhar(
            "EXECUTOR_ID nao definido. Configure no .env ou passe --executor-id=<id>.",
            codigo="executor_id_ausente",
        )

    _env_path = os.getenv("EXECUTOR_ENV_PATH") or str(Path(__file__).parent / ".env")

    try:
        info = enroll(args.server, otp, executor_id, args.cert_dir, env_path=_env_path)
    except RuntimeError as exc:
        return _falhar(str(exc), codigo="enroll_recusado")

    # Cert emitido, mas a chave de assinatura do servidor nao bate com a fixada:
    # o executor nao sobe assim (ver executor/server_key.py). Sair com 0 aqui
    # mandava o operador rodar `docker compose up` e descobrir o problema so pelo
    # sintoma "online mas nada roda".
    if info.get("signing_key_conflict"):
        if args.json:
            json.dump({
                "ok": False, "codigo": "signing_key_conflict",
                "erro": info["signing_key_conflict"],
                "cert_dir": str(Path(args.cert_dir).resolve()),
            }, sys.stdout)
            sys.stdout.write("\n")
            sys.stdout.flush()
            return 1
        print(file=sys.stderr)
        print("  Cert emitido, MAS O ENROLLMENT NAO ESTA UTILIZAVEL.", file=sys.stderr)
        print(f"  Certs em: {Path(args.cert_dir).resolve()}", file=sys.stderr)
        print(file=sys.stderr)
        print(f"  {info['signing_key_conflict']}", file=sys.stderr)
        return 1

    if args.json:
        json.dump({
            "ok": True,
            "executor_id": executor_id,
            "serial": info.get("serial"),
            "fingerprint": info.get("fingerprint"),
            "expires_at": info.get("expires_at"),
            "cert_dir": str(Path(args.cert_dir).resolve()),
            "env_path": _env_path,
        }, sys.stdout)
        sys.stdout.write("\n")
        sys.stdout.flush()
        return 0

    print()
    print("  Enrollment concluido com sucesso.")
    print(f"  Serial:     {info['serial']}")
    print(f"  Valido ate: {info['expires_at']}")
    print(f"  Certs em:   {Path(args.cert_dir).resolve()}")
    print(f"  EXECUTOR_ID gravado em: {_env_path}")
    # No quickstart (install.sh) o bash continua e roda `docker compose up -d`
    # logo apos. Omitir o "python -m executor" evita instrucao conflitante.
    if not os.getenv("ATLANS_QUICKSTART"):
        print()
        print("  Inicie o executor com:")
        print("    python -m executor")
    return 0


if __name__ == "__main__":
    sys.exit(_cli_main(sys.argv[1:]))
