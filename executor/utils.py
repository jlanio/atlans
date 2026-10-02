# executor/utils.py
"""Funcoes utilitarias compartilhadas pelo executor."""
import logging
import os

# `is_local_server` vive no flow/ (presente nas imagens da API e do executor):
# o `get_agent_http_config` dos nos precisa da MESMA regra e nao pode importar
# o executor na imagem da API. Reexportada aqui para os callers do executor.
from flow.utils.executor_http import is_local_server

logger = logging.getLogger(__name__)


def ocultar_no_windows(caminho) -> None:
    """Marca um arquivo/pasta como OCULTO no Windows (FILE_ATTRIBUTE_HIDDEN).

    Os arquivos internos do executor ja nascem com ponto no inicio do nome
    (`.atlans-sync.json`, `.executor_results.sqlite`, `.atlans-trash/`), o que
    basta para escondê-los no Linux e no macOS. O Explorer do Windows, porém,
    IGNORA essa convencao: la esses arquivos aparecem como qualquer outro, no
    meio dos dados do usuario, convidando ao apagamento acidental. E apagar nao
    e inofensivo — sumir com o manifesto re-sincroniza a pasta inteira, e perder
    o outbox SQLite joga fora resultados de jobs ainda nao confirmados pelo
    servidor. O atributo oculto do NTFS e o que de fato tira esses arquivos da
    frente no unico SO onde o ponto nao resolve.

    No-op fora do Windows (o ponto ja cuida disso) e totalmente best-effort:
    qualquer falha — arquivo recem-removido, volume sem suporte a atributos,
    permissao — e engolida. Ocultar e conveniencia, nunca pode derrubar o fluxo
    que acabou de gravar o arquivo.

    Aceita str ou os.PathLike.
    """
    # TODO(windows): o comportamento desta funcao e dos pontos que dependem dela
    # foi verificado por DOCUMENTACAO/analise da Win32, nao num Windows real — o
    # CI roda so em Linux, onde tudo aqui e no-op. Tres premissas ficam sem teste
    # de ponta a ponta:
    #   1. os.replace (MoveFileEx) NAO falha ao sobrescrever um destino oculto,
    #      entao o manifesto (sync/manifest.py) continua persistindo apos o 1o
    #      hide. So o CreateFile CREATE_ALWAYS barra em arquivo oculto, e o fluxo
    #      .tmp + os.replace o contorna.
    #   2. O SQLite reabre um .sqlite oculto (result_store.py) via OPEN_EXISTING/
    #      OPEN_ALWAYS, sem ACCESS_DENIED.
    #   3. SetFileAttributesW de fato esconde no Explorer (e caminhos > MAX_PATH
    #      sem long-path habilitado caem no bail silencioso — ver o log de debug).
    # Fechar o gap: um smoke test marcado @pytest.mark.skipif(sys.platform !=
    # 'win32') que crie, oculte e reescreva manifesto+outbox num runner Windows.
    if os.name != "nt":
        return
    try:
        import ctypes

        FILE_ATTRIBUTE_HIDDEN = 0x02
        # GetFileAttributesW devolve 0xFFFFFFFF em erro; com o restype padrao do
        # ctypes (c_int) isso chega como -1. Tratamos as duas formas.
        INVALIDO = (-1, 0xFFFFFFFF)

        alvo = str(caminho)
        # ctypes converte `str` para wchar_t* automaticamente nas funcoes `...W`.
        atuais = ctypes.windll.kernel32.GetFileAttributesW(alvo)
        if atuais in INVALIDO:
            # Arquivo inexistente, sem acesso, ou caminho acima de MAX_PATH sem
            # long-path habilitado. Segue best-effort; so registramos em debug
            # porque, sem isto, esse modo de falha e impossivel de diagnosticar.
            logger.debug("ocultar_no_windows: GetFileAttributesW invalido para %s (err=%s)",
                         alvo, ctypes.windll.kernel32.GetLastError())
            return
        # OR com os atributos atuais para nao apagar um READONLY/SYSTEM que ja
        # estivesse la. Se o bit de oculto ja esta setado, nem toca no arquivo.
        if not (atuais & FILE_ATTRIBUTE_HIDDEN):
            if not ctypes.windll.kernel32.SetFileAttributesW(alvo, atuais | FILE_ATTRIBUTE_HIDDEN):
                logger.debug("ocultar_no_windows: SetFileAttributesW falhou para %s (err=%s)",
                             alvo, ctypes.windll.kernel32.GetLastError())
    except Exception:
        # Best-effort por contrato: ver a docstring.
        pass


def ws_to_http(ws_url: str) -> str:
    """Converte URL WebSocket para HTTP/HTTPS. Ex: wss://agents.<dominio> -> https://agents.<dominio>"""
    return ws_url.replace("wss://", "https://").replace("ws://", "http://")


def build_mtls_ssl_context():
    """
    Constroi SSLContext com cert + key do executor (mTLS) e CA interna ADICIONADA
    ao trust store padrao do sistema.

    Antes era `create_default_context(cafile=ca.pem)` que SUBSTITUI o trust
    store do sistema pelo ca.pem — o executor so confiava na CA interna e
    quebrava ao falar com endpoints publicos (ex: o S3 publico atras de um CDN)
    no mesmo SSLContext, com erro `unable to get local issuer certificate`.

    Agora: trust store padrao (CAs publicas via certifi/sistema) + ca.pem
    como CA adicional. O mesmo context funciona para:
      - o host dos executores (assinado pela CA interna)
      - o S3 publico / qualquer endpoint com cert publico (CDN/LE)
      - envio do cert mTLS do executor quando o server pedir (Traefik)

    GOTCHA: `create_default_context()` honra SSL_CERT_FILE, que SUBSTITUI o trust
    store padrao em vez de somar. Hoje o _ca_bootstrap ja exporta um bundle
    combinado (certifi + CA interna), mas um operador pode apontar a variavel
    para um arquivo so com a CA interna — e ai o mesmo context usado como
    `verify` em httpx.put para MinIO/Drive/APIs externas quebraria com "unable
    to get local issuer certificate". Carregar certifi explicitamente antes do
    ca.pem torna este context independente do que veio no ambiente — mesmo
    tratamento de `executor/enrollment.py::_resolve_enroll_verify`.

    Levanta FileNotFoundError se o executor nao foi enrolado.
    """
    import ssl
    from executor import config as _agent_config
    ctx = ssl.create_default_context()
    try:
        import certifi  # type: ignore
        ctx.load_verify_locations(cafile=certifi.where())
    except ImportError:
        # Sem certifi, recorre ao trust store do SO (que o SSL_CERT_FILE do
        # bootstrap tambem mascara, mas load_default_certs le do sistema).
        ctx.load_default_certs()
    ctx.load_verify_locations(cafile=_agent_config.EXECUTOR_CA_PATH)
    ctx.load_cert_chain(
        certfile=_agent_config.EXECUTOR_CERT_PATH,
        keyfile=_agent_config.EXECUTOR_KEY_PATH,
    )
    return ctx


def mtls_httpx_kwargs(url: str) -> dict:
    """
    Retorna kwargs para httpx.AsyncClient/Client (verify=..., cert=...) que
    aplicam mTLS quando apropriado. Util para sync/uploader, sync/downloader, etc.
    """
    if is_local_server(url):
        return {"verify": False}
    return {"verify": build_mtls_ssl_context()}


def classify_dataset_type(dataset_type: str) -> str:
    """Classifica tipo de dataset: raster, tabular ou vector."""
    if dataset_type in ("raster", "tiff", "tif"):
        return "raster"
    if dataset_type in ("csv", "xlsx", "tabular"):
        return "tabular"
    return "vector"
