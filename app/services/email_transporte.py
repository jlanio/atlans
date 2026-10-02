# app/services/email_transporte.py
"""
O transporte dos e-mails: Resend, SMTP ou só o log.

Os dois caminhos que mandam e-mail passam por aqui: os do próprio servidor
(verificação, redefinição de senha, alertas — `email_service.py`) e o do nó
SendEmail (`internal_email_router.py`). Quem escolhe é EMAIL_BACKEND
(`app/core/config.py`):

  resend   a API da Resend (RESEND_API_KEY)
  smtp     qualquer servidor SMTP (SMTP_HOST, SMTP_PORT, SMTP_USERNAME,
           SMTP_PASSWORD, SMTP_SEGURANCA = starttls | ssl | nenhuma)
  log      nada sai; quem chama registra o e-mail no log

Vazio = o que estiver configurado: Resend com a chave, SMTP com o host, log
sem nenhum dos dois — o mesmo comportamento de quando só havia a Resend.
`enviar` é bloqueante: quem chama roda em thread (`asyncio.to_thread`).
"""
from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate, getaddresses, make_msgid, parseaddr

from app.core import config
from app.core.utils.logger import get_logger

logger = get_logger(__name__)

BACKENDS = ("resend", "smtp", "log")

# Por operação da conexão (conectar, TLS, login, envio). O nó SendEmail espera
# 30 s pela resposta inteira (`flow/nodes/outputs/send_email.py`): com 30 s
# por operação, um servidor lento estourava o prazo do nó com o e-mail ainda
# saindo, e o nó falhava com o e-mail enviado.
TEMPO_LIMITE_SMTP_S = 10

# O que, num destinatário, faria dele mais de um: a vírgula separa endereços,
# `:` e `;` abrem e fecham um grupo, e a quebra de linha injetaria cabeçalho.
_SEPARADORES = frozenset(",;:\r\n")


def endereco(destinatario: str) -> str:
    """O endereço de UM destinatário (`ana@x.org` ou `Ana <ana@x.org>`).

    Levanta ValueError se o item não for exatamente um endereço. É o que faz
    valer o teto de destinatários do nó SendEmail: sem isto, um item com
    vírgulas virava vários `RCPT TO` no SMTP, e a lista de 50 contava um.
    """
    item = destinatario.strip()
    if not item or any(c in _SEPARADORES for c in item):
        raise ValueError(f"Destinatário inválido: {destinatario!r} (um endereço por item).")
    pares = getaddresses([item])
    _, puro = pares[0] if len(pares) == 1 else ("", "")
    local, arroba, dominio = puro.rpartition("@")
    if not (arroba and local and dominio) or any(c.isspace() for c in puro):
        raise ValueError(f"Destinatário inválido: {destinatario!r} (um endereço por item).")
    return puro


def backend() -> str:
    """O transporte em uso: o escolhido em EMAIL_BACKEND ou o configurado.

    Um valor desconhecido nem chega aqui: `app/core/config.py` para a API.
    """
    escolhido = config.EMAIL_BACKEND
    if escolhido in BACKENDS:
        return escolhido
    if config.RESEND_API_KEY:
        return "resend"
    if config.SMTP_HOST:
        return "smtp"
    return "log"


def ativo() -> bool:
    """Há um transporte de verdade? Em `log`, nenhum e-mail sai."""
    return backend() != "log"


def enviar(para: list[str], assunto: str, html: str) -> str | None:
    """Envia o e-mail pelo transporte em uso e devolve o id da mensagem.

    Levanta em qualquer falha do transporte, e também em `log`: quem chama
    decide o que fazer quando não há transporte (`ativo()`).
    """
    qual = backend()
    for destinatario in para:
        endereco(destinatario)
    if qual == "resend":
        return _enviar_resend(para, assunto, html)
    if qual == "smtp":
        return _enviar_smtp(para, assunto, html)
    raise RuntimeError("Nenhum transporte de e-mail configurado (EMAIL_BACKEND, RESEND_API_KEY ou SMTP_HOST).")


def _enviar_resend(para: list[str], assunto: str, html: str) -> str | None:
    import resend

    resend.api_key = config.RESEND_API_KEY
    resultado = resend.Emails.send({
        "from": config.EMAIL_FROM,
        "to": para,
        "subject": assunto,
        "html": html,
    })
    return resultado.get("id") if isinstance(resultado, dict) else None


def _enviar_smtp(para: list[str], assunto: str, html: str) -> str | None:
    # EmailMessage recusa quebra de linha em cabeçalho (ValueError): um assunto
    # vindo de workflow não injeta cabeçalho nenhum.
    mensagem = EmailMessage()
    mensagem["From"] = config.EMAIL_FROM
    mensagem["To"] = ", ".join(para)
    mensagem["Subject"] = assunto
    mensagem["Date"] = formatdate(localtime=False)
    dominio = parseaddr(config.EMAIL_FROM)[1].rpartition("@")[2] or None
    mensagem["Message-ID"] = make_msgid(domain=dominio)
    mensagem.set_content(html, subtype="html")

    contexto = ssl.create_default_context()
    if config.SMTP_SEGURANCA == "ssl":
        conexao = smtplib.SMTP_SSL(
            config.SMTP_HOST, config.SMTP_PORT, context=contexto, timeout=TEMPO_LIMITE_SMTP_S,
        )
    else:
        conexao = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=TEMPO_LIMITE_SMTP_S)
    with conexao as smtp:
        if config.SMTP_SEGURANCA == "starttls":
            smtp.starttls(context=contexto)
        if config.SMTP_USERNAME:
            smtp.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
        # Os destinatários vão explícitos: sem `to_addrs`, o smtplib os tira de
        # novo do cabeçalho `To`, e é ali que um item vira vários.
        smtp.send_message(mensagem, to_addrs=[endereco(p) for p in para])
    return mensagem["Message-ID"]
