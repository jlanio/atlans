# tests/unit/test_admin_assistente_router.py
"""`/admin/assistente/modelo` — changing the model with the catalog up front.

What these tests pin down:

1. **Admin only.** The whole router is under `require_admin`.
2. **A provider that is down does not take down the screen.** Without a
   catalog, the admin still needs to see what is in use and be able to go
   back to the default.
3. **An invalid id is a 400 right away**, not an error on every user's next
   conversation.
4. **The model is probed before saving**, and "back to default" never is.
5. **An extension adds fields to the panel** (a plans extension adds the quota
   and the cost, with tests in its folder) and receives the URL parameters
   the core does not read.
"""
from unittest.mock import patch

import pytest
import pytest_asyncio

from app.core.config import ASSISTENTE_MODELO
from app.services import openrouter
from tests.unit._painel_do_modelo import CATALOGO, api_com_banco, com_catalogo

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def api(client, mock_current_user):
    async with api_com_banco(client, mock_current_user) as par:
        yield par


async def test_usuario_comum_nao_entra(client, mock_current_user):
    mock_current_user.role = "user"
    r = await client.get("/admin/assistente/modelo")
    assert r.status_code in (401, 403)


async def test_provedor_fora_do_ar_nao_derruba_a_tela(api):
    """Without a catalog the admin still needs to see what is in use and be able
    to go back to the default — answering 500 here would lock the only exit."""
    client, _ = api
    with com_catalogo(erro=openrouter.ErroDoOpenRouter("fora do ar", status=503)):
        r = await client.get("/admin/assistente/modelo")

    assert r.status_code == 200
    corpo = r.json()
    assert corpo["catalogo"] == []
    assert corpo["catalogo_indisponivel"] == "ErroDoOpenRouter"
    assert corpo["atual"]["modelo"] == ASSISTENTE_MODELO


async def test_o_catalogo_vem_da_base_configurada_com_a_chave(api):
    """Outside OpenRouter (a gateway, a vLLM with a key), the catalog is the
    configured server's, and it requires the same key as the conversation."""
    client, _ = api
    visto: dict = {}

    async def _listar(**kw):
        visto.update(kw)
        return [dict(m) for m in CATALOGO]

    with com_catalogo(), \
            patch("app.services.openrouter.listar_modelos", _listar), \
            patch("app.api.routers.admin_assistente_router.OPENROUTER_BASE_URL", "http://vllm:8000/v1"):
        r = await client.get("/admin/assistente/modelo")

    assert r.status_code == 200
    assert visto == {"base_url": "http://vllm:8000/v1", "chave": "k"}


async def test_trocar_salva_e_a_resposta_ja_reflete(api):
    client, _ = api
    with com_catalogo():
        r = await client.put("/admin/assistente/modelo", json={"modelo": "a/caro"})

    assert r.status_code == 200
    atual = r.json()["atual"]
    assert atual["modelo"] == "a/caro"
    assert atual["origem"] == "banco"
    assert atual["definido_por"] == "admin-test"
    assert atual["definido_em"]


async def test_voltar_ao_padrao_do_ambiente(api):
    client, _ = api
    with com_catalogo():
        await client.put("/admin/assistente/modelo", json={"modelo": "a/caro"})
        r = await client.put("/admin/assistente/modelo", json={"modelo": None})

    assert r.json()["atual"] == {
        "modelo": ASSISTENTE_MODELO, "origem": "ambiente",
        "definido_por": None, "definido_em": None,
        "padrao_do_ambiente": ASSISTENTE_MODELO,
    }


async def test_id_invalido_e_400_e_nao_erro_na_proxima_conversa(api):
    client, _ = api
    with com_catalogo():
        r = await client.put("/admin/assistente/modelo", json={"modelo": "antropic claude"})
        depois = await client.get("/admin/assistente/modelo")

    assert r.status_code == 400
    assert depois.json()["atual"]["modelo"] == ASSISTENTE_MODELO


async def test_campo_desconhecido_e_recusado(api):
    """`extra=forbid`: price and ceiling belong to the server. Silently accepting
    an extra field is the first step toward someone trying to send one of them."""
    client, _ = api
    with com_catalogo():
        r = await client.put("/admin/assistente/modelo",
                             json={"modelo": "a/caro", "preco_centavos": 1})
    assert r.status_code == 422


# ── The panel without extensions, and with one ──────────────────────────────

async def test_sem_extensoes_o_painel_e_o_modelo_e_o_catalogo(api, registro_de_teste):
    """The free distribution: no quota or per-plan cost."""
    client, _ = api
    with com_catalogo():
        r = await client.get("/admin/assistente/modelo")

    assert r.status_code == 200
    assert set(r.json()) == {"atual", "catalogo", "catalogo_indisponivel"}


async def test_uma_extensao_soma_campos_e_recebe_os_parametros_da_url(api, registro_de_teste):
    client, _ = api
    vistos: list[dict] = []

    async def contribuicao(db, *, atual, catalogo, simular, consulta):
        vistos.append({"modelo": atual["modelo"], "catalogo": [m["id"] for m in catalogo],
                       "simular": simular, "consulta": dict(consulta)})
        return {"economia": {"teto": 42}}

    registro_de_teste.painel_do_modelo.append(contribuicao)
    with com_catalogo():
        r = await client.get("/admin/assistente/modelo", params={"simular": "a/caro", "faixa": "7"})
        trocado = await client.put("/admin/assistente/modelo", json={"modelo": "a/barato"})

    assert r.json()["economia"] == {"teto": 42}
    assert vistos[0] == {"modelo": ASSISTENTE_MODELO, "catalogo": ["a/barato", "a/caro"],
                         "simular": "a/caro", "consulta": {"simular": "a/caro", "faixa": "7"}}
    # The PUT response is the whole panel too, with no simulation.
    assert trocado.json()["economia"] == {"teto": 42}
    assert vistos[1]["simular"] is None and vistos[1]["consulta"] == {}


# ── The model probe ──────────────────────────────────────────────────────────
#
# The real production case: an admin chose `deepseek/...:batch` in the panel —
# an id that IS in the provider's catalog but belongs to the batch endpoint.
# The provider answered "cannot be used with the chat/completions endpoint",
# and the assistant started giving "não consegui falar com o modelo" (couldn't
# reach the model) to ALL users, while whoever made the change saw nothing.
#
# The screen offered a choice that could not work. The probe is what moves the
# provider's refusal to the moment of the click, in its own words.

_RECUSA_DO_BATCH = (
    "OpenRouter respondeu 404: deepseek/deepseek-v4-flash-vision-exp:batch cannot be "
    "used with the chat/completions endpoint (adapter FireworksBatchAdapter)."
)


async def test_modelo_que_o_provedor_recusa_nao_e_salvo(api):
    """400 on the click, with the provider's message — and nothing changes."""
    client, _ = api
    from app.services.openrouter import ErroDoOpenRouter

    with com_catalogo(sonda=ErroDoOpenRouter(_RECUSA_DO_BATCH, status=404)):
        r = await client.put("/admin/assistente/modelo", json={"modelo": "a/caro"})
        assert r.status_code == 400
        # The PROVIDER's message arrives in full: it is what says what to do.
        assert "chat/completions" in r.json()["message"]
        assert "não foi salvo" in r.json()["message"]

        depois = await client.get("/admin/assistente/modelo")
    assert depois.json()["atual"]["modelo"] == ASSISTENTE_MODELO, "o modelo velho continua"
    assert depois.json()["atual"]["origem"] == "ambiente"


async def test_sonda_que_nao_responde_tambem_bloqueia(api):
    """The costly error is the other one.

    Letting an unverified model through breaks the product for everyone;
    blocking a legitimate change during instability costs a retry. But the
    message tells the two cases apart — "refused" and "could not check" call
    for different actions from whoever is on the screen.
    """
    client, _ = api
    with com_catalogo(sonda=TimeoutError("estourou")):
        r = await client.put("/admin/assistente/modelo", json={"modelo": "a/caro"})
    assert r.status_code == 400
    assert "Não deu para conferir" in r.json()["message"]
    assert "TimeoutError" in r.json()["message"]


async def test_voltar_ao_padrao_NUNCA_e_sondado(api):
    """The emergency exit cannot depend on the provider.

    If it is down with a bad model saved, probing "back to default" would lock
    the door precisely when it is needed.
    """
    client, _ = api
    with com_catalogo():
        await client.put("/admin/assistente/modelo", json={"modelo": "a/caro"})

    # Now the provider refuses EVERYTHING — and even so the default comes back.
    from app.services.openrouter import ErroDoOpenRouter

    with com_catalogo(sonda=ErroDoOpenRouter("provedor fora do ar", status=503)):
        r = await client.put("/admin/assistente/modelo", json={"modelo": None})

    assert r.status_code == 200
    assert r.json()["atual"]["origem"] == "ambiente"


async def test_a_sonda_manda_a_MESMA_forma_da_conversa():
    """Probing with a shape different from the real one would prove nothing.

    It is the shape that the provider refuses: it is the tools that a model
    without support rejects, and it is the `max_tokens` that a model with a
    low ceiling refuses. A "light" probe would approve models that break on
    the first conversation.
    """
    import httpx

    from app.services import openrouter
    from app.services.assistente_service import ESFORCO_DO_RACIOCINIO, MAX_TOKENS

    visto = {}

    def _responder(pedido: httpx.Request) -> httpx.Response:
        import json as _json

        visto.update(_json.loads(pedido.content))
        # A realistic stream: a piece of text and the end. What the probe wants
        # to know was already answered by the 200.
        return httpx.Response(
            200, headers={"Content-Type": "text/event-stream"},
            content=(
                b'data: {"choices":[{"delta":{"content":"ok"},"finish_reason":null}]}\n\n'
                b'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n'
                b"data: [DONE]\n\n"
            ),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(_responder)) as http:
        await openrouter.sondar_modelo(
            "a/qualquer", chave="k", max_tokens=MAX_TOKENS,
            esforco=ESFORCO_DO_RACIOCINIO, http=http,
        )

    assert visto["model"] == "a/qualquer"
    assert visto["max_tokens"] == MAX_TOKENS, "o teto real, senão um modelo de teto baixo passa"
    assert visto["tools"], "sem ferramentas, um modelo que não as suporta passaria"
    assert visto["reasoning"] == {"effort": ESFORCO_DO_RACIOCINIO}
    assert visto["stream"] is True


async def test_stream_esquisito_NAO_bloqueia_a_troca():
    """The provider accepted — that is all the probe asks.

    A stream that opens with 200 and ends without a useful frame is a
    transmission detail, and the real conversation deals with it. Blocking the
    change because of that would be the probe failing a model that works.
    """
    import httpx

    from app.services import openrouter

    def _vazio(pedido: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"Content-Type": "text/event-stream"},
                              content=b"data: [DONE]\n\n")

    async with httpx.AsyncClient(transport=httpx.MockTransport(_vazio)) as http:
        await openrouter.sondar_modelo(
            "a/qualquer", chave="k", max_tokens=1000, esforco=None, http=http,
        )


async def test_a_sonda_levanta_o_que_o_provedor_respondeu():
    """No translation in between: the provider's message is what helps decide."""
    import httpx

    from app.services import openrouter

    def _recusar(pedido: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": {"message": _RECUSA_DO_BATCH}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(_recusar)) as http:
        with pytest.raises(openrouter.ErroDoOpenRouter) as erro:
            await openrouter.sondar_modelo(
                "d/v:batch", chave="k", max_tokens=1000, esforco=None, http=http,
            )
    assert "chat/completions" in str(erro.value)
    assert erro.value.status == 404
