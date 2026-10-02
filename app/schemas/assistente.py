# app/schemas/assistente.py
"""Schemas do assistente da Home (superficie `home`): a camada do globo e a API
de conversas persistidas (`/assistente`).

O que o cliente MANDA leva `extra="forbid"` — o transcrito nunca vem do
navegador (um `tool_result` e a palavra do servidor), e um campo desconhecido
aceito em silencio e o primeiro passo para alguem tentar forjar um. O que ele
RECEBE fora do stream (lista, detalhe/replay) sao os modelos de resposta."""
from datetime import datetime
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class CamadaDoGlobo(BaseModel):
    """O que a Home precisa para por uma saida de execucao no globo.

    `tipo` decide como a web a carrega:
    - `geojson`: `download_url` (URL pre-assinada, curta) → a web faz fetch e
      guarda a FeatureCollection em memoria (nunca `addSource({data: url})`,
      que a URL expira).
    - `mvt`: a camada foi publicada (PublishMap) → tiles vetoriais em
      `/assistente/tiles/{workflow_id}/{layer_key}/...`; `mvt` traz o par.
    - `indisponivel`: sem previa (executor-local, sem storage, CRS != 4326,
      ou formato que a v1 nao converte). `hint` diz por que, em pt-BR.

    `bbox`/`crs`/`geometry_type` vem de `node_run_metrics` (ja calculados na
    execucao) ou do `PortalLayer`; `bbox` so e confiavel para enquadrar quando
    `crs` e 4326.
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
    # O arquivo de origem pode ser BAIXADO por `GET /artifacts/{id}/download`.
    # Nao e o mesmo que `available`, que diz se ha PREVIA no globo: uma camada
    # publicada (MVT) aparece no globo com o conteudo no PostGIS e pode nao ter
    # arquivo no storage, e o download recusaria (409/404). Quem consome mostra
    # a acao so quando isto e verdadeiro — botao vivo que falha e pior que
    # botao ausente.
    baixavel: bool = False
    hint: Optional[str] = None
    workflow_id: Optional[str] = None
    run_id: Optional[str] = None
    # Retencao do artefato (dias), nao o prazo do link. Null = nao expira.
    expires_at: Optional[datetime] = None


# ── A API de conversas ───────────────────────────────────────────────────────


class Localizacao(BaseModel):
    """A posicao atual de quem esta na Home, quando a pessoa resolve compartilha-la.

    Chega opcional no turno (`MensagemDaHome.localizacao`): o navegador so a manda
    depois de a pessoa liberar o GPS. Serve de ponto de referencia para pedidos
    relativos ("perto de mim", "num raio de N km"); ausente/nula quando ela nao
    compartilhou. `extra="forbid"` como no resto do que o cliente MANDA — um campo
    desconhecido aqui dentro e o mesmo vetor que o do envelope de fora.
    """

    model_config = ConfigDict(extra="forbid")

    # `allow_inf_nan=False` nos tres: o parser de JSON do FastAPI aceita os
    # literais Infinity/NaN (e 1e999 parseia para inf), e "inf >= 0" passa num
    # `ge` puro — o prompt ganharia um "precisao ~inf m". O teto de 1000 km em
    # `precisao_m` corta o resto do lixo numerico (precisao pior que isso nao
    # e localizacao, e ruido).
    lat: float = Field(..., ge=-90, le=90, allow_inf_nan=False, description="Latitude em graus decimais (WGS84).")
    lon: float = Field(..., ge=-180, le=180, allow_inf_nan=False, description="Longitude em graus decimais (WGS84).")
    precisao_m: Optional[float] = Field(
        default=None, ge=0, le=1_000_000, allow_inf_nan=False, description="Raio de precisao em metros; opcional."
    )


# O idioma da TELA de quem conversa (a Home traduzida). O assistente responde
# nele; "pt-BR" (ou ausente) mantém o idioma padrão da instalação.
IdiomaDaTela = Literal["pt-BR", "en", "es"]


class MensagemDaHome(BaseModel):
    """Uma mensagem de quem esta usando o assistente da Home.

    `extra="forbid"` como no assistente: o transcrito NAO vem do cliente. E a rota
    ainda recusa (422) a mensagem que comeca com `[Acao` — so o servidor escreve
    esse prefixo, nas mensagens sinteticas de confirmacao; aqui o schema so
    garante o formato.
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
    idioma: Optional[IdiomaDaTela] = Field(
        default=None,
        description="O idioma da tela de quem pergunta; o assistente responde nele (ausente/pt-BR: o padrao).",
    )


class RenomearConversa(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo: str = Field(..., min_length=1, max_length=120)


class DecisaoDeConfirmacao(BaseModel):
    """O clique no cartao de confirmacao: o token que o servidor emitiu e a decisao.

    NAO leva argumentos — o que roda sao os args ARMAZENADOS no Redis pelo portao
    da Home. `extra="forbid"` fecha a porta para o cliente tentar mandar argumentos
    por aqui, que seria justamente burlar a confirmacao verificada no servidor.

    `localizacao` NAO e argumento da acao: e o mesmo contexto opcional do turno
    (MensagemDaHome.localizacao), reenviado porque a confirmacao RETOMA o laco do
    modelo e o servidor nao guarda a coordenada (ela vive so no prompt do stream).
    Sem o reenvio, um fluxo "perto de mim" que pede confirmacao retomava sem
    saber onde a pessoa esta.
    """

    model_config = ConfigDict(extra="forbid")

    token: str = Field(..., min_length=1, max_length=128)
    decisao: Literal["confirmar", "recusar"]
    localizacao: Optional[Localizacao] = Field(
        default=None,
        description="A posicao atual de quem confirma, quando compartilhada — a retomada continua sabendo o 'perto de mim'.",
    )
    idioma: Optional[IdiomaDaTela] = Field(
        default=None,
        description="O idioma da tela de quem confirma — a retomada continua respondendo nele.",
    )


class ConversaResumo(BaseModel):
    """Uma linha da lista de conversas da pessoa."""

    id: str
    titulo: Optional[str] = None
    workflow_id: Optional[str] = None
    tokens_total: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ConversaLista(BaseModel):
    itens: List[ConversaResumo]
    total: int


class QuadroDoReplay(BaseModel):
    """Um quadro do replay — o MESMO vocabulario do SSE, para o painel reaplicar
    pelo mesmo caminho de um quadro ao vivo. `tool_result` nunca sai aqui."""

    tipo: str
    dados: dict[str, Any] = Field(default_factory=dict)


class ConversaDetalhe(BaseModel):
    id: str
    titulo: Optional[str] = None
    workflow_id: Optional[str] = None
    quadros: List[QuadroDoReplay]


# ── Superfície do editor (o painel do canvas) ────────────────────────────────
class MensagemDoEditor(BaseModel):
    """Uma mensagem de quem está usando.

    `extra="forbid"` de propósito: o transcrito NÃO vem do cliente (ver
    `app/services/assistente_service.py`), e um campo desconhecido aceito em
    silêncio é o primeiro passo para alguém tentar mandar um junto.
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


class CotaDoAssistente(BaseModel):
    gasto: int = Field(..., description="Tokens consumidos na janela atual")
    teto: int = Field(..., description="Tokens permitidos por janela")
    reabre_em_segundos: Optional[int] = Field(
        default=None, description="Quanto falta para a janela reabrir; nulo se ainda não começou"
    )


class EstadoDoAssistente(BaseModel):
    """O que o painel precisa saber antes de aparecer na tela."""

    ativo: bool = Field(..., description="Falso quando a instalação não configurou a chave")
    motivo: Optional[str] = Field(
        default=None, description="Por que está desligado, quando está"
    )
    cota: Optional[CotaDoAssistente] = None
    # O plano de quem pergunta, quando uma extensão de planos está instalada
    # ("free" | "pro" | "max", na dos planos pagos). Opcional porque o payload
    # existia antes dos planos: um cliente antigo (ou uma instalação sem a
    # extensão) continua lendo `cota.teto`, que já traz o teto correto. Serve
    # para a tela dizer QUAL plano dá aquele teto, não para calcular nada.
    plano: Optional[str] = Field(
        default=None, description="O plano que define o teto desta pessoa"
    )
    # Sem isto, a oferta que aparece quando a cota estoura vira um beco: numa
    # instalação sem provedor de pagamento, «Ver planos» levaria a pessoa a uma
    # tela que só diz «não disponível nesta instalação». Oferecer o que não se
    # pode vender é pior que não oferecer.
    assinaturas_ativas: bool = Field(
        default=False, description="Há provedor de pagamento configurado nesta instalação"
    )
