# executor/config.py
"""
Configuracoes do executor carregadas via variaveis de ambiente.

Variaveis obrigatorias:
  EXECUTOR_ID                  — UUID do executor (obtido na criacao pelo admin)
  EXECUTOR_SERVER_URL          — host dos executores da instalacao (wss://...).
                                 Sem padrao: o enroll a grava no .env.

Credenciais (cert mTLS) sao persistidas em EXECUTOR_CERT_DIR (default ./certs/).
Cada executor deve fazer enrollment uma unica vez (o comando pronto sai da tela
de matricula da instalacao):
  python -m executor enroll --otp=<OTP_FORNECIDO_PELO_ADMIN> --server=https://agents.<dominio>

Variaveis opcionais:
  SERVER_SIGNING_PUBLIC_KEY    — base64 da chave publica Ed25519 do servidor.
                                 Override do operador: sem ela vale a chave
                                 fixada no enrollment (ver executor/server_key.py)
  EXECUTOR_CERT_DIR            — diretorio para cert.pem/chain.pem/ca.pem/key.pem (default: ./certs)
  EXECUTOR_PRIVATE_KEY         — base64 da chave privada X25519 (envelope encryption)
                              Se nao fornecida, lida de EXECUTOR_PRIVATE_KEY_PATH
  EXECUTOR_PRIVATE_KEY_PATH    — caminho da chave privada X25519
  EXECUTOR_VERSION             — versao do software fora da imagem Docker (padrao: "1.0.0";
                                 na imagem vale a gravada no build — executor/versao.py)
  EXECUTOR_MAX_CONCURRENT      — execucoes simultaneas (padrao: 4)
  EXECUTOR_MAX_QUEUE_SIZE      — fila local maxima (padrao: 50)
  EXECUTOR_JOB_TIMEOUT         — timeout por job em segundos (padrao: 3600)
  EXECUTOR_RECONNECT_MAX_DELAY — delay maximo de reconnect em segundos (padrao: 15)
  NONCE_CACHE_TTL           — TTL do cache anti-replay em segundos (padrao: 600)
  EXECUTOR_MAX_JOB_EXPIRY_SECONDS — teto da duracao declarada do envelope
                                 (expires_at - issued_at), padrao 900s
  EXECUTOR_CLOCK_SKEW_SECONDS  — folga de relogio na checagem de expiracao
                                 (padrao: 300s)
  EXECUTOR_MAX_CLOCK_SKEW_SECONDS — teto RIGIDO de deriva do relogio local
                                 (padrao: 900s). Acima dele todo job/comando e
                                 recusado apontando o NTP, em vez de aceito: com
                                 deriva grande a janela de aceitacao passa do TTL
                                 do cache de nonce e o anti-replay para de valer.
                                 Subir este valor exige subir NONCE_CACHE_TTL
                                 junto — ha teste do invariante.
                                 As quatro sao lidas dentro de
                                 executor/job_validator.py, junto do comentario
                                 que explica o porque de cada valor.
  EXECUTOR_HOST_ALIASES        — mapeamento de hostnames "db=localhost:5433,..."
  EXECUTOR_DASHBOARD           — auto|on|off|json (ver o bloco do painel abaixo)
  EXECUTOR_SUPERVISOR_PID      — PID de quem iniciou este processo (o app
                                 desktop). Definido pelo supervisor, nunca a
                                 mao. Liga o watchdog de executor/supervisor.py,
                                 que encerra o executor de forma ordenada se o
                                 supervisor morrer, e desliga o auto-restart
                                 interno — com supervisor, religar e trabalho
                                 dele.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

from executor._ambiente import avisar, emitir_avisos_adiados, ler_float, ler_int
from executor.versao import versao_do_executor

# Carrega .env — EXECUTOR_ENV_PATH permite ao Electron definir um path customizado.
_env_path = os.getenv("EXECUTOR_ENV_PATH") or str(Path(__file__).parent / ".env")
load_dotenv(dotenv_path=_env_path)

# Desabilita os drivers OGR VRT no GDAL ANTES de qualquer import de geopandas/
# pyogrio (o GDAL le GDAL_SKIP quando registra os drivers). Sem isto, um arquivo
# ou resposta WFS com conteudo <OGRVRTDataSource> faz o GDAL ler arquivo local
# do executor (cert mTLS, credenciais) ou fazer SSRF via /vsicurl. A leitura de
# arquivos tambem recusa VRT pelo conteudo (flow/utils/leitura_geo.py); isto e a
# defesa em profundidade que cobre ate o VRT embutido em .zip.
_gdal_skip = {s for s in os.environ.get("GDAL_SKIP", "").split(",") if s}
os.environ["GDAL_SKIP"] = ",".join(sorted(_gdal_skip | {"OGR_VRT", "VRT"}))


# Numeros do ambiente sao lidos por executor/_ambiente.py (ler_int/ler_float):
# valor invalido vira o padrao com aviso, nunca ValueError no import. Este
# modulo roda ANTES de o logging estar configurado, entao os avisos ficam
# retidos la ate configure_logging() chamar flush_startup_warnings() — o nome
# que executor/logging_setup.py importa daqui.
flush_startup_warnings = emitir_avisos_adiados


# URL do servidor. Sem padrao: um executor nunca fala com uma instalacao que
# ninguem escolheu. O enroll grava o valor no .env (ver executor/enrollment.py).
SERVER_URL: str = os.getenv("EXECUTOR_SERVER_URL", "").strip()

# Leitura TOLERANTE: abortar no import matava o processo com ValueError antes de
# main() rodar, e antes do canal com o supervisor subir — a falha chegava como
# traceback cru, sem dizer o que fazer. A exigencia mora em assert_configured(),
# chamada dentro de main() depois de o canal estar de pe.
EXECUTOR_ID:                 str = os.getenv("EXECUTOR_ID", "").strip()
SERVER_SIGNING_PUBLIC_KEY: str = os.getenv("SERVER_SIGNING_PUBLIC_KEY", "")

# ── Diretorio do cert mTLS ────────────────────────────────────────────────────
_default_cert_dir = "/data/certs" if os.path.isdir("/data") else "./certs"
EXECUTOR_CERT_DIR: str = os.getenv("EXECUTOR_CERT_DIR", _default_cert_dir)

# Paths dos arquivos individuais dentro do cert dir.
EXECUTOR_CERT_PATH:  str = str(Path(EXECUTOR_CERT_DIR) / "cert.pem")
EXECUTOR_CA_PATH:    str = str(Path(EXECUTOR_CERT_DIR) / "ca.pem")
EXECUTOR_KEY_PATH:   str = str(Path(EXECUTOR_CERT_DIR) / "key.pem")
# Chave privada X25519 para decriptar envelopes de jobs (gerada no enroll).
EXECUTOR_X25519_KEY_PATH: str = str(Path(EXECUTOR_CERT_DIR) / "x25519_key.pem")

# Retrocompat: o codigo de envelope decryption ainda le EXECUTOR_PRIVATE_KEY_PATH.
EXECUTOR_PRIVATE_KEY:      str | None = os.getenv("EXECUTOR_PRIVATE_KEY")
EXECUTOR_PRIVATE_KEY_PATH: str = os.getenv("EXECUTOR_PRIVATE_KEY_PATH", EXECUTOR_X25519_KEY_PATH)


def _cleanup_renewal_orphans() -> None:
    """
    Remove arquivos `.new` orfaos em EXECUTOR_CERT_DIR. Eles ficam quando o
    enroll ou o renewal (enrollment._persistir_bundle) escreve os `<nome>.new`
    mas o processo morre antes do `os.replace` atomico. Sem cleanup, acumulam
    para sempre. Threshold de 10 min evita corrida com um renewal em curso.
    """
    import time as _time
    cert_dir = Path(EXECUTOR_CERT_DIR)
    if not cert_dir.is_dir():
        return
    cutoff = _time.time() - 10 * 60
    for orphan in cert_dir.glob("*.new"):
        try:
            if orphan.stat().st_mtime < cutoff:
                orphan.unlink()
        except OSError:
            pass


def assert_configured() -> None:
    """
    Verifica as variaveis obrigatorias antes de iniciar.

    Antes isso era um `_require()` em tempo de import, que matava o processo
    com ValueError antes de main() rodar. Agora a checagem e explicita e
    acontece dentro de main(), depois de o canal com o supervisor subir.
    """
    if not SERVER_URL:
        raise SystemExit(
            "\n  Variavel obrigatoria nao definida: EXECUTOR_SERVER_URL\n"
            "\n  O enrollment a grava no .env:\n"
            "    python -m executor enroll --executor-id=<ID> --otp=<OTP> \\\n"
            "        --server=<URL do host dos executores>\n"
            "\n  O comando pronto, com o endereco da sua instalacao, sai da tela de\n"
            "  matricula do executor.\n"
            f"\n  (.env esperado em {_env_path})\n"
        )
    if not EXECUTOR_ID:
        # Esta e a mensagem que o usuario ve quando o executor nao consegue
        # subir. Ela precisa dizer o que FAZER, e nao so o que falta — e os dois
        # caminhos abaixo funcionam em todos os ambientes onde o executor roda.
        raise SystemExit(
            "\n  Variavel obrigatoria nao definida: EXECUTOR_ID\n"
            "\n  Enrollment (funciona em qualquer ambiente):\n"
            "    python -m executor enroll --executor-id=<ID> --otp=<OTP> \\\n"
            "        --server=" + SERVER_URL + "\n"
            "\n  Em Docker, o EXECUTOR_ID tambem precisa estar no .env montado\n"
            "  no container (env_file: em docker-compose.executor.yml).\n"
            "\n  No app desktop, o formulario de vinculo faz isso pela interface.\n"
            f"\n  (.env esperado em {_env_path})\n"
        )


def assert_enrolled() -> None:
    """
    Verifica que o executor foi enrolado antes de iniciar.
    Chamado por executor/main.py para falhar rapido com mensagem clara.
    """
    _cleanup_renewal_orphans()
    cert_path = Path(EXECUTOR_CERT_PATH)
    key_path  = Path(EXECUTOR_KEY_PATH)
    if not cert_path.exists() or not key_path.exists():
        raise SystemExit(
            "\n  Executor nao enrolado.\n"
            "  Rode: python -m executor enroll --otp=<OTP> --server=" + SERVER_URL + "\n"
            f"  (cert.pem esperado em {cert_path})\n"
        )

# Na imagem Docker vale a versao gravada no build, acima do .env (ver
# executor/versao.py); fora dela, EXECUTOR_VERSION — o desktop a define.
EXECUTOR_VERSION:            str = versao_do_executor()
_versao_no_env = (os.getenv("EXECUTOR_VERSION") or "").strip()
# O 1.0.0 e o do .env.example que toda instalacao antiga tem: nao e escolha.
if _versao_no_env and _versao_no_env not in (EXECUTOR_VERSION, "1.0.0"):
    avisar(
        "EXECUTOR_VERSION=%s ignorada: vale a versao gravada na imagem (%s).",
        _versao_no_env, EXECUTOR_VERSION,
    )
# Minimo 1 porque zero nao falha, funciona errado: executor sem worker, fila que
# nunca aceita, job que estoura na hora (ver executor/_ambiente.py::ler_int).
# Maximos sao defensivos: valores absurdos (256 workers, fila de 100k) derrubam
# o host antes de o operador perceber que digitou errado. A tela de Ajustes do
# app desktop espelha padroes e faixas destas tres em desktop/src/shared/limites.ts
# — o teste de la le ESTAS linhas e falha se os dois lados divergirem.
MAX_CONCURRENT:           int = ler_int("EXECUTOR_MAX_CONCURRENT", 4, minimo=1, maximo=256)
MAX_QUEUE_SIZE:           int = ler_int("EXECUTOR_MAX_QUEUE_SIZE", 50, minimo=1, maximo=10_000)
JOB_TIMEOUT:              int = ler_int("EXECUTOR_JOB_TIMEOUT", 3600, minimo=1)
# 15s, e nao 60s: o teto existe contra thundering herd numa queda longa, mas com
# 60s um deploy do servidor (Traefik devolvendo 404/502 por alguns segundos)
# tirava o executor do painel por ate um minuto DEPOIS de tudo ja ter voltado —
# tempo em que o dispatch roteia para outro executor ou responde "nenhum executor
# disponivel". O jitter de 50-100% ja dispersa a frota o bastante.
RECONNECT_MAX_DELAY:      int = ler_int("EXECUTOR_RECONNECT_MAX_DELAY", 15, minimo=1, maximo=3600)
NONCE_CACHE_TTL:          int = ler_int("NONCE_CACHE_TTL", 600, minimo=1)

# Workspace fixo para GeoSync (opcional — se não definido, auto-detecta do servidor)
WORKSPACE_ID:       str | None = os.getenv("EXECUTOR_WORKSPACE_ID") or None


def _parse_host_aliases(raw: str) -> dict[str, str]:
    """
    Converte EXECUTOR_HOST_ALIASES para dict {hostname_interno: host_externo_com_porta}.
    Formato: "db=localhost:5433,redis=localhost:6379"
    """
    aliases: dict[str, str] = {}
    for part in raw.split(","):
        part = part.strip()
        if "=" in part:
            internal, external = part.split("=", 1)
            aliases[internal.strip()] = external.strip()
    return aliases


HOST_ALIASES: dict[str, str] = _parse_host_aliases(os.getenv("EXECUTOR_HOST_ALIASES", ""))

# Diretório base onde o executor salva artefatos gerados pelos nós de output.
# O Electron define EXECUTOR_ARTIFACTS_DIR apontando para a pasta escolhida pelo usuário.
ARTIFACTS_DIR: str = os.getenv(
    "EXECUTOR_ARTIFACTS_DIR",
    str(Path.home() / "AtlansExecutor" / "artifacts"),
)

# ── Logging ────────────────────────────────────────────────────────────────────
# LOG_LEVEL, LOG_COLOR, LOG_FILE_AGENT e LOG_FILE_WORKFLOW nao moram aqui: quem
# as le, direto do ambiente, e o configure_logging() de executor/logging_setup.py
# — na hora de configurar, e nao no import, para nao depender da ordem de import.


def _default_log_dir() -> str:
    """`<pai de ARTIFACTS_DIR>/logs`, seguindo a convencao de ~/AtlansExecutor.

    No Docker, EXECUTOR_ARTIFACTS_DIR=/data/artifacts vira /data/logs — dentro
    do volume que ja e persistente. Se o pai for a raiz do sistema de arquivos
    (ARTIFACTS_DIR mal configurado), cai no home para nao tentar escrever em /.
    """
    pai = Path(ARTIFACTS_DIR).parent
    if pai == pai.parent:  # chegou na raiz — nao e lugar de gravar log
        return str(Path.home() / "AtlansExecutor" / "logs")
    return str(pai / "logs")


LOG_DIR: str = os.getenv("EXECUTOR_LOG_DIR") or _default_log_dir()

# ── Painel ao vivo / canal com o supervisor ──────────────────────────────────
# EXECUTOR_DASHBOARD e lida direto do ambiente pelo gate do painel
# (`should_enable_from_process` em executor/dashboard/__init__.py):
# auto  — liga o painel rich se o terminal for interativo e o `rich` existir
# on    — forca o painel rich (util para quem sabe o que esta fazendo)
# off   — nenhum dos dois; mantem o log linha a linha no console
# json  — canal NDJSON no stdout, para um supervisor (o app desktop).
#         Nunca e inferido: emitir JSON no stdout de quem esperava log humano
#         quebraria o consumidor em silencio. Ver executor/dashboard/json_runtime.py
#         para o formato dos eventos e a lista de comandos aceitos no stdin.
DASHBOARD_INTERVAL: float = ler_float("EXECUTOR_DASHBOARD_INTERVAL", 1.0, minimo=0.25)

# ── GeoSync — sincronizacao de pastas locais com o Drive do Workspace ─────────
# Pastas separadas por virgula. Vazio = sync desabilitado.
SYNC_DIRS: str = os.getenv("EXECUTOR_SYNC_DIRS", "")
# Os padroes abaixo valem quando a linha falta no .env. O .env.example — semente
# de toda instalacao nova — grava bidirectional e 10s de proposito; o app desktop
# grava o modo que a tela mostra e sempre 10s (desktop/src/shared/geosync.ts,
# com teste contra estas linhas).
SYNC_INTERVAL: int = ler_int("EXECUTOR_SYNC_INTERVAL", 30, minimo=1)  # segundos
# upload | download | bidirectional | catalog
#
# `upload` e o padrao seguro: nada que aconteca no Drive apaga ou sobrescreve
# arquivo local (ver o gate de modo em sync/manager.py::_process_drive_event).
#
# `catalog` e para dado pessoal (LGPD): o executor registra o dataset no Drive —
# nome, tipo, tamanho, CRS, bbox, contagem de feicoes — e o CONTEUDO nunca sai
# desta maquina. Os arquivos so podem ser lidos por workflows que rodem neste
# mesmo executor; o download pela plataforma nao existe.
SYNC_MODE: str = os.getenv("EXECUTOR_SYNC_MODE", "upload")
SYNC_CONFLICT_STRATEGY: str = os.getenv("EXECUTOR_SYNC_CONFLICT_STRATEGY", "remote-wins")  # local-wins | remote-wins | keep-both
SYNC_TRIGGERS: str = os.getenv("EXECUTOR_SYNC_TRIGGERS", "")
