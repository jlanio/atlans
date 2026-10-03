# app/services/email_transporte.py
"""
The email transport: Resend, SMTP or just the log.

Both paths that send email go through here: the server's own (verification,
password reset, alerts — `email_service.py`) and the SendEmail node's
(`internal_email_router.py`). The choice is made by EMAIL_BACKEND
(`app/core/config.py`):

  resend   the Resend API (RESEND_API_KEY)
  smtp     any SMTP server (SMTP_HOST, SMTP_PORT, SMTP_USERNAME,
           SMTP_PASSWORD, SMTP_SEGURANCA = starttls | ssl | nenhuma)
  log      nothing goes out; the caller records the email in the log

Empty = whatever is configured: Resend with the key, SMTP with the host, log
with neither — the same behavior as when there was only Resend.
`enviar` is blocking: the caller runs it in a thread (`asyncio.to_thread`).
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

# Per connection operation (connect, TLS, login, send). The SendEmail node waits
# 30 s for the whole response (`flow/nodes/outputs/send_email.py`): with 30 s
# per operation, a slow server blew the node's deadline with the email still
# going out, and the node failed with the email sent.
TEMPO_LIMITE_SMTP_S = 10

# What, in a recipient, would make it more than one: the comma separates
# addresses, `:` and `;` open and close a group, and a line break would inject a header.
_SEPARADORES = frozenset(",;:\r\n")


def endereco(destinatario: str) -> str:
    """The address of ONE recipient (`ana@x.org` or `Ana <ana@x.org>`).

    Raises ValueError if the item is not exactly one address. This is what
    enforces the SendEmail node's recipient ceiling: without it, an item with
    commas became several `RCPT TO` in SMTP, and the list of 50 counted as one.
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
    """The transport in use: the one chosen in EMAIL_BACKEND or the configured one.

    An unknown value never even gets here: `app/core/config.py` stops the API.
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
    """Is there a real transport? In `log`, no email goes out."""
    return backend() != "log"


def enviar(para: list[str], assunto: str, html: str) -> str | None:
    """Sends the email through the transport in use and returns the message id.

    Raises on any transport failure, and also in `log`: the caller decides
    what to do when there is no transport (`ativo()`).
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
    # EmailMessage rejects line breaks in headers (ValueError): a subject coming
    # from a workflow injects no header at all.
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
        # The recipients go explicitly: without `to_addrs`, smtplib takes them again
        # from the `To` header, and that is where one item becomes several.
        smtp.send_message(mensagem, to_addrs=[endereco(p) for p in para])
    return mensagem["Message-ID"]
