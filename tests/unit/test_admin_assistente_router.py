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
from tests.unit._painel_do_modelo import CATALOGO, api_with_db, with_catalog

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def api(client, mock_current_user):
    async with api_with_db(client, mock_current_user) as par:
        yield par


async def test_regular_user_cannot_enter(client, mock_current_user):
    mock_current_user.role = "user"
    r = await client.get("/admin/assistente/modelo")
    assert r.status_code in (401, 403)


async def test_provider_down_does_not_break_the_screen(api):
    """Without a catalog the admin still needs to see what is in use and be able
    to go back to the default — answering 500 here would lock the only exit."""
    client, _ = api
    with with_catalog(erro=openrouter.ErroDoOpenRouter("fora do ar", status=503)):
        r = await client.get("/admin/assistente/modelo")

    assert r.status_code == 200
    corpo = r.json()
    assert corpo["catalogo"] == []
    assert corpo["catalogo_indisponivel"] == "ErroDoOpenRouter"
    assert corpo["atual"]["modelo"] == ASSISTENTE_MODELO


async def test_catalog_comes_from_the_configured_base_with_the_key(api):
    """Outside OpenRouter (a gateway, a vLLM with a key), the catalog is the
    configured server's, and it requires the same key as the conversation."""
    client, _ = api
    visto: dict = {}

    async def _list_schedules(**kw):
        visto.update(kw)
        return [dict(m) for m in CATALOGO]

    with with_catalog(), \
            patch("app.services.openrouter.listar_modelos", _list_schedules), \
            patch("app.api.routers.admin_assistente_router.OPENROUTER_BASE_URL", "http://vllm:8000/v1"):
        r = await client.get("/admin/assistente/modelo")

    assert r.status_code == 200
    assert visto == {"base_url": "http://vllm:8000/v1", "chave": "k"}


async def test_switching_saves_and_the_response_already_reflects_it(api):
    client, _ = api
    with with_catalog():
        r = await client.put("/admin/assistente/modelo", json={"modelo": "a/caro"})

    assert r.status_code == 200
    atual = r.json()["atual"]
    assert atual["modelo"] == "a/caro"
    assert atual["origem"] == "banco"
    assert atual["definido_por"] == "admin-test"
    assert atual["definido_em"]


async def test_revert_to_environment_default(api):
    client, _ = api
    with with_catalog():
        await client.put("/admin/assistente/modelo", json={"modelo": "a/caro"})
        r = await client.put("/admin/assistente/modelo", json={"modelo": None})

    assert r.json()["atual"] == {
        "modelo": ASSISTENTE_MODELO, "origem": "ambiente",
        "definido_por": None, "definido_em": None,
        "padrao_do_ambiente": ASSISTENTE_MODELO,
    }


async def test_invalid_id_is_400_and_not_an_error_in_the_next_conversation(api):
    client, _ = api
    with with_catalog():
        r = await client.put("/admin/assistente/modelo", json={"modelo": "antropic claude"})
        depois = await client.get("/admin/assistente/modelo")

    assert r.status_code == 400
    assert depois.json()["atual"]["modelo"] == ASSISTENTE_MODELO


async def test_unknown_field_is_rejected(api):
    """`extra=forbid`: price and ceiling belong to the server. Silently accepting
    an extra field is the first step toward someone trying to send one of them."""
    client, _ = api
    with with_catalog():
        r = await client.put("/admin/assistente/modelo",
                             json={"modelo": "a/caro", "preco_centavos": 1})
    assert r.status_code == 422


# ── The panel without extensions, and with one ──────────────────────────────

async def test_without_extensions_the_panel_is_model_and_catalog(api, empty_registry):
    """The free distribution: no quota or per-plan cost."""
    client, _ = api
    with with_catalog():
        r = await client.get("/admin/assistente/modelo")

    assert r.status_code == 200
    assert set(r.json()) == {"atual", "catalogo", "catalogo_indisponivel"}


async def test_an_extension_adds_fields_and_receives_the_url_parameters(api, empty_registry):
    client, _ = api
    vistos: list[dict] = []

    async def contribution(db, *, atual, catalogo, simular, consulta):
        vistos.append({"modelo": atual["modelo"], "catalogo": [m["id"] for m in catalogo],
                       "simular": simular, "consulta": dict(consulta)})
        return {"economia": {"teto": 42}}

    empty_registry.painel_do_modelo.append(contribution)
    with with_catalog():
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

_BATCH_REFUSAL = (
    "OpenRouter respondeu 404: deepseek/deepseek-v4-flash-vision-exp:batch cannot be "
    "used with the chat/completions endpoint (adapter FireworksBatchAdapter)."
)


async def test_model_the_provider_refuses_is_not_saved(api):
    """400 on the click, with the provider's message — and nothing changes."""
    client, _ = api
    from app.services.openrouter import ErroDoOpenRouter

    with with_catalog(sonda=ErroDoOpenRouter(_BATCH_REFUSAL, status=404)):
        r = await client.put("/admin/assistente/modelo", json={"modelo": "a/caro"})
        assert r.status_code == 400
        # The PROVIDER's message arrives in full: it is what says what to do.
        assert "chat/completions" in r.json()["message"]
        assert "não foi salvo" in r.json()["message"]

        depois = await client.get("/admin/assistente/modelo")
    assert depois.json()["atual"]["modelo"] == ASSISTENTE_MODELO, "o modelo velho continua"
    assert depois.json()["atual"]["origem"] == "ambiente"


async def test_probe_that_does_not_respond_also_blocks(api):
    """The costly error is the other one.

    Letting an unverified model through breaks the product for everyone;
    blocking a legitimate change during instability costs a retry. But the
    message tells the two cases apart — "refused" and "could not check" call
    for different actions from whoever is on the screen.
    """
    client, _ = api
    with with_catalog(sonda=TimeoutError("estourou")):
        r = await client.put("/admin/assistente/modelo", json={"modelo": "a/caro"})
    assert r.status_code == 400
    assert "Não deu para conferir" in r.json()["message"]
    assert "TimeoutError" in r.json()["message"]


async def test_reverting_to_default_is_NEVER_probed(api):
    """The emergency exit cannot depend on the provider.

    If it is down with a bad model saved, probing "back to default" would lock
    the door precisely when it is needed.
    """
    client, _ = api
    with with_catalog():
        await client.put("/admin/assistente/modelo", json={"modelo": "a/caro"})

    # Now the provider refuses EVERYTHING — and even so the default comes back.
    from app.services.openrouter import ErroDoOpenRouter

    with with_catalog(sonda=ErroDoOpenRouter("provedor fora do ar", status=503)):
        r = await client.put("/admin/assistente/modelo", json={"modelo": None})

    assert r.status_code == 200
    assert r.json()["atual"]["origem"] == "ambiente"


async def test_probe_sends_the_SAME_shape_as_the_conversation():
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

    def _respond(pedido: httpx.Request) -> httpx.Response:
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

    async with httpx.AsyncClient(transport=httpx.MockTransport(_respond)) as http:
        await openrouter.sondar_modelo(
            "a/qualquer", chave="k", max_tokens=MAX_TOKENS,
            esforco=ESFORCO_DO_RACIOCINIO, http=http,
        )

    assert visto["model"] == "a/qualquer"
    assert visto["max_tokens"] == MAX_TOKENS, "o teto real, senão um modelo de teto baixo passa"
    assert visto["tools"], "sem ferramentas, um modelo que não as suporta passaria"
    assert visto["reasoning"] == {"effort": ESFORCO_DO_RACIOCINIO}
    assert visto["stream"] is True


async def test_odd_stream_does_NOT_block_the_switch():
    """The provider accepted — that is all the probe asks.

    A stream that opens with 200 and ends without a useful frame is a
    transmission detail, and the real conversation deals with it. Blocking the
    change because of that would be the probe failing a model that works.
    """
    import httpx

    from app.services import openrouter

    def _empty(pedido: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"Content-Type": "text/event-stream"},
                              content=b"data: [DONE]\n\n")

    async with httpx.AsyncClient(transport=httpx.MockTransport(_empty)) as http:
        await openrouter.sondar_modelo(
            "a/qualquer", chave="k", max_tokens=1000, esforco=None, http=http,
        )


async def test_probe_raises_what_the_provider_answered():
    """No translation in between: the provider's message is what helps decide."""
    import httpx

    from app.services import openrouter

    def _refuse(pedido: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": {"message": _BATCH_REFUSAL}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(_refuse)) as http:
        with pytest.raises(openrouter.ErroDoOpenRouter) as erro:
            await openrouter.sondar_modelo(
                "d/v:batch", chave="k", max_tokens=1000, esforco=None, http=http,
            )
    assert "chat/completions" in str(erro.value)
    assert erro.value.status == 404
