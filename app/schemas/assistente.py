# app/schemas/assistente.py
"""Schemas for the Home assistant (`home` surface): the globe layer and the API
for persisted conversations (`/assistente`).

What the client SENDS carries `extra="forbid"` — the transcript never comes
from the browser (a `tool_result` is the server's word), and an unknown field
silently accepted is the first step for someone to try forging one. What it
RECEIVES outside the stream (list, detail/replay) are the response models."""
from datetime import datetime
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class GlobeLayer(BaseModel):
    """What Home needs to put a run output on the globe.

    `tipo` decides how the web app loads it:
    - `geojson`: `download_url` (pre-signed, short-lived URL) → the web app
      fetches it and keeps the FeatureCollection in memory (never
      `addSource({data: url})`, since the URL expires).
    - `mvt`: the layer was published (PublishMap) → vector tiles at
      `/assistente/tiles/{workflow_id}/{layer_key}/...`; `mvt` carries the pair.
    - `indisponivel`: no preview (executor-local, no storage, CRS != 4326, or
      a format v1 does not convert). `hint` says why, in pt-BR.

    `bbox`/`crs`/`geometry_type` come from `node_run_metrics` (already
    computed during execution) or from the `PortalLayer`; `bbox` is only
    reliable for framing when `crs` is 4326.
    """
    artifact_id: str
    nome: str
    output_key: Optional[str] = None
    format: Optional[str] = None
    tipo: Literal["geojson", "mvt", "indisponivel"]
    available: bool
    download_url: Optional[str] = None
    url_expires_in: Optional[int] = None
    # {"workflow_id": ..., "layer_key": ...} quando tipo == "mvt".
    mvt: Optional[dict[str, Any]] = None
    bbox: Optional[List[float]] = None
    crs: Optional[str] = None
    geometry_type: Optional[str] = None
    features: Optional[int] = None
    size_bytes: Optional[int] = None
    # The source file can be DOWNLOADED via `GET /artifacts/{id}/download`.
    # It is not the same as `available`, which says whether there is a PREVIEW
    # on the globe: a published layer (MVT) shows up on the globe with its
    # content in PostGIS and may have no file in storage, and the download
    # would refuse (409/404). Consumers show the action only when this is
    # true — a live button that fails is worse than no button.
    baixavel: bool = False
    hint: Optional[str] = None
    workflow_id: Optional[str] = None
    run_id: Optional[str] = None
    # The artifact's retention (days), not the link's lifetime. Null = does not expire.
    expires_at: Optional[datetime] = None


# ── The conversations API ────────────────────────────────────────────────────


class Localizacao(BaseModel):
    """The current position of whoever is on Home, when the person decides to share it.

    It arrives optionally with the turn (`HomeMessage.localizacao`): the
    browser only sends it after the person allows GPS. It serves as a reference
    point for relative requests ("near me", "within N km"); absent/null when
    they did not share it. `extra="forbid"` as in the rest of what the client
    SENDS — an unknown field in here is the same vector as in the outer envelope.
    """

    model_config = ConfigDict(extra="forbid")

    # `allow_inf_nan=False` on all three: FastAPI's JSON parser accepts the
    # Infinity/NaN literals (and 1e999 parses to inf), and "inf >= 0" passes a
    # plain `ge` — the prompt would get a "precisao ~inf m". The 1000 km ceiling
    # on `precisao_m` cuts off the rest of the numeric garbage (accuracy worse
    # than that is not a location, it is noise).
    lat: float = Field(..., ge=-90, le=90, allow_inf_nan=False, description="Latitude em graus decimais (WGS84).")
    lon: float = Field(..., ge=-180, le=180, allow_inf_nan=False, description="Longitude em graus decimais (WGS84).")
    precisao_m: Optional[float] = Field(
        default=None, ge=0, le=1_000_000, allow_inf_nan=False, description="Raio de precisao em metros; opcional."
    )


# The language of the chatting person's SCREEN (the translated Home). The
# assistant answers in it; "pt-BR" (or absent) keeps the installation's default
# language.
ScreenLanguage = Literal["pt-BR", "en", "es"]


class HomeMessage(BaseModel):
    """A message from whoever is using the Home assistant.

    `extra="forbid"` as in the assistant: the transcript does NOT come from the
    client. And the route also refuses (422) a message starting with `[Acao` —
    only the server writes that prefix, in the synthetic confirmation
    messages; here the schema only ensures the format.
    """

    model_config = ConfigDict(extra="forbid")

    mensagem: str = Field(
        ..., min_length=1, max_length=8000, description="O que a pessoa escreveu. O historico fica no servidor."
    )
    conversa_id: Optional[str] = Field(
        default=None, max_length=64, description="A conversa a continuar; nulo cria uma nova."
    )
    workspace_id: Optional[str] = Field(
        default=None, max_length=64, description="Workspace preferido para os fluxos que o assistente criar."
    )
    localizacao: Optional[Localizacao] = Field(
        default=None,
        description=(
            "A posicao atual de quem pergunta, quando ela compartilha o GPS. Serve de "
            "referencia para pedidos relativos; nula/ausente quando ela nao compartilhou."
        ),
    )
    idioma: Optional[ScreenLanguage] = Field(
        default=None,
        description="O idioma da tela de quem pergunta; o assistente responde nele (ausente/pt-BR: o padrao).",
    )


class RenameConversation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(..., min_length=1, max_length=120)


class ConfirmationDecision(BaseModel):
    """The click on the confirmation card: the token the server issued and the decision.

    It carries NO arguments — what runs are the args STORED in Redis by Home's
    gate. `extra="forbid"` shuts the door on the client trying to send
    arguments through here, which would be precisely bypassing the
    confirmation verified on the server.

    `localizacao` is NOT an argument of the action: it is the same optional
    context as the turn (HomeMessage.localizacao), resent because the
    confirmation RESUMES the model's loop and the server does not keep the
    coordinate (it lives only in the stream's prompt). Without resending it, a
    "near me" workflow that asks for confirmation resumed without knowing where
    the person is.
    """

    model_config = ConfigDict(extra="forbid")

    token: str = Field(..., min_length=1, max_length=128)
    decisao: Literal["confirmar", "recusar"]
    localizacao: Optional[Localizacao] = Field(
        default=None,
        description="A posicao atual de quem confirma, quando compartilhada — a retomada continua sabendo o 'perto de mim'.",
    )
    idioma: Optional[ScreenLanguage] = Field(
        default=None,
        description="O idioma da tela de quem confirma — a retomada continua respondendo nele.",
    )


class ConversationSummary(BaseModel):
    """One row of the person's conversation list."""

    id: str
    titulo: Optional[str] = None
    workflow_id: Optional[str] = None
    tokens_total: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ConversationList(BaseModel):
    itens: List[ConversationSummary]
    total: int


class ReplayFrame(BaseModel):
    """A replay frame — the SAME vocabulary as the SSE, so the panel reapplies it
    through the same path as a live frame. `tool_result` never goes out here."""

    tipo: str
    dados: dict[str, Any] = Field(default_factory=dict)


class ConversationDetail(BaseModel):
    id: str
    titulo: Optional[str] = None
    workflow_id: Optional[str] = None
    quadros: List[ReplayFrame]


# ── Editor surface (the canvas panel) ────────────────────────────────────────
class EditorMessage(BaseModel):
    """A message from whoever is using it.

    `extra="forbid"` on purpose: the transcript does NOT come from the client
    (see `app/services/assistente_service.py`), and an unknown field silently
    accepted is the first step for someone to try sending one along.
    """

    model_config = ConfigDict(extra="forbid")

    mensagem: str = Field(
        ...,
        min_length=1,
        max_length=8000,
        description="O que a pessoa escreveu. O histórico fica no servidor.",
    )
    workflow_id: Optional[str] = Field(
        default=None,
        max_length=64,
        description=(
            "O fluxo aberto no editor. Cada fluxo tem sua própria conversa; "
            "sem ele a conversa é a da tela de criar."
        ),
    )


class AssistantQuota(BaseModel):
    gasto: int = Field(..., description="Tokens consumidos na janela atual")
    teto: int = Field(..., description="Tokens permitidos por janela")
    reabre_em_segundos: Optional[int] = Field(
        default=None, description="Quanto falta para a janela reabrir; nulo se ainda não começou"
    )


class AssistantState(BaseModel):
    """What the panel needs to know before appearing on screen."""

    ativo: bool = Field(..., description="Falso quando a instalação não configurou a chave")
    motivo: Optional[str] = Field(
        default=None, description="Por que está desligado, quando está"
    )
    cota: Optional[AssistantQuota] = None
    # The plan of whoever asks, when a plans extension is installed ("free" |
    # "pro" | "max", in the paid-plans one). Optional because the payload
    # existed before plans: an old client (or an installation without the
    # extension) keeps reading `cota.teto`, which already carries the correct
    # ceiling. It is for the screen to say WHICH plan gives that ceiling, not
    # to compute anything.
    plano: Optional[str] = Field(
        default=None, description="O plano que define o teto desta pessoa"
    )
    # Without this, the offer that shows up when the quota runs out becomes a
    # dead end: on an installation without a payment provider, "Ver planos"
    # (see plans) would take the person to a screen that only says "não
    # disponível nesta instalação" (not available on this installation).
    # Offering what cannot be sold is worse than not offering.
    assinaturas_ativas: bool = Field(
        default=False, description="Há provedor de pagamento configurado nesta instalação"
    )
