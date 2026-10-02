# app/mcp/escopo.py
"""
`EscopoEfetivo` — quem é o dono da chamada e até onde ele alcança.

O middleware de PAT resolve o token UMA vez por request e destila o resultado
neste objeto imutável: usuário, token, escopos concedidos e os workspaces que
ele de fato alcança (já intersectados com os workspaces do usuário). Daí em
diante nenhuma tool volta ao banco para perguntar "esse token pode?" — a
resposta viaja junto.

Dois canais, porque há dois consumidores:
- `request.state.escopo`, lido pelas tools a partir do `ctx` (é o caminho
  normal, e o único que funciona com vários requests concorrentes);
- `ESCOPO_ATUAL`, um `ContextVar`, porque `list_tools()` não recebe `ctx`
  nenhum e ainda assim precisa filtrar o catálogo pelo escopo do token.

`como_usuario()` existe por uma razão de segurança: os services de
observabilidade decidem o que mostrar a partir de um objeto `user`, e alguns
ainda olham `user.role`. Entregar a eles o `User` cru do banco daria ao MCP o
alcance global de um administrador. O substituto carrega só o que eles leem e
é sempre `role="user"`.
"""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from types import SimpleNamespace

from app.core.authorization import pat
from app.mcp.erros import erro


@dataclass(frozen=True)
class EscopoEfetivo:
    """O alcance de uma chamada — congelado no momento da autenticação."""

    user_id: str
    username: str | None
    token_id: str
    token_prefix: str
    scopes: frozenset[str]
    # Já é a interseção "workspaces do usuário ∩ alcance do token".
    workspace_ids: frozenset[str]
    # True quando o token foi emitido com `workspace_ids = NULL` ("todos,
    # inclusive os futuros"). Não amplia nada por si: `workspace_ids` continua
    # sendo a lista real; serve para explicar o alcance e para a documentação.
    todos_os_workspaces: bool

    # Proveniência que os fluxos criados por este principal recebem
    # (`Workflow.origem`). "usuario" para PATs e para o assistente do editor;
    # "assistente" só para o escopo do assistente da Home. É carimbo de origem,
    # NÃO privilégio: não amplia alcance nenhum, só marca quem criou o fluxo
    # para as listagens poderem escondê-lo. Default no fim da classe: os
    # construtores existentes (PAT, assistente, `escopo_falso`) seguem intactos.
    origem_dos_fluxos: str = "usuario"

    def tem(self, escopo: str) -> bool:
        """True se o token carrega este escopo."""
        return escopo in self.scopes

    def como_usuario(self) -> SimpleNamespace:
        """O mínimo que os services pedem como `user` — NUNCA o `User` do banco.

        Sempre `role="user"`: um PAT não confere privilégio de administrador,
        mesmo que o dono seja um.
        """
        return SimpleNamespace(id_hash=self.user_id, username=self.username, role="user")

    def workspace_unico(self) -> str | None:
        """O workspace quando há exatamente um — o que torna `workspace_id` opcional."""
        if len(self.workspace_ids) == 1:
            return next(iter(self.workspace_ids))
        return None


# Preenchido pelo middleware e resetado no fim da request. `list_tools()` é o
# consumidor que não tem outro canal; o handler roda numa task criada dentro da
# request, e `create_task` copia o contexto, então o valor chega lá.
ESCOPO_ATUAL: ContextVar[EscopoEfetivo | None] = ContextVar("ESCOPO_ATUAL", default=None)


# ── Assistente ──────────────────────────────────────────────────────────────────
# O assistente da web chama as mesmas tools, mas quem o autentica é a sessão JWT,
# não um PAT. Ele precisa de um `EscopoEfetivo` mesmo assim — é o formato que
# toda a autorização do MCP consome —, e o `token_id` sintético abaixo tem dois
# efeitos deliberados: os baldes de cota (`ratelimit:mcp:assistente-editor:…`) nascem
# separados dos baldes dos PATs, e a linha de auditoria distingue de imediato o
# que veio da tela do que veio de um cliente externo.

PREFIXO_DO_EDITOR = "assistente-editor"

# NÃO são os seis escopos do PAT. `triggers:manage` e `drive:write` ficaram de
# fora da primeira versão por decisão do dono: apagar um agendamento ou um
# arquivo do Drive destrói dado de outra pessoa do workspace, e a conversa em
# linguagem natural é justamente onde o mal-entendido é mais barato de cometer
# ("limpa os agendamentos antigos" é uma frase que alguém digita sem pensar).
# Ampliar aqui é uma linha — e é uma decisão de produto, não de implementação.
ESCOPOS_DO_EDITOR: frozenset[str] = frozenset(
    {
        "workflows:read",
        "workflows:write",
        "runs:execute",
        "drive:read",
    }
)


def escopo_do_editor(
    *,
    user_id: str,
    username: str | None,
    workspace_ids: frozenset[str] | set[str] | list[str],
) -> EscopoEfetivo:
    """O escopo de uma conversa do assistente — o usuário da sessão, sem PAT.

    Puro de propósito: `workspace_ids` chega resolvido por quem chamou (com
    `listar_workspace_ids`), e não por uma consulta daqui. Este módulo é
    importado por `erros`, pelas tools e pelo middleware; uma dependência de
    banco nele arrastaria os modelos para dentro de todo esse caminho — e
    tornaria impossível testar a montagem do escopo sem subir um banco.

    `todos_os_workspaces=True` porque não há token restringindo nada: o alcance
    é exatamente o do usuário, hoje e quando ele entrar num workspace novo.
    """
    return EscopoEfetivo(
        user_id=user_id,
        username=username,
        token_id=f"{PREFIXO_DO_EDITOR}:{user_id}",
        token_prefix=PREFIXO_DO_EDITOR,
        scopes=ESCOPOS_DO_EDITOR,
        workspace_ids=frozenset(workspace_ids),
        todos_os_workspaces=True,
    )


# ── Assistente da Home ────────────────────────────────────────────────────────
# O assistente da Home é o assistente de OUTRA superfície: mesma sessão JWT, mas
# alcance COMPLETO. Diferente do assistente do editor, ele cria e roda os PRÓPRIOS
# fluxos e mexe no que já existia — e o que segura o que ele pode destruir é a
# CONFIRMAÇÃO POR CLIQUE verificada no servidor (`app/services/assistente_superficie.py`),
# não a ausência de escopo. A diferença de alcance mora aqui, na IDENTIDADE, e
# não numa lista espalhada pelo laço.

PREFIXO_DO_ASSISTENTE = "assistente"

# Os SEIS escopos do PAT, `pat.ESCOPOS` — inclusive `triggers:manage` e
# `drive:write`, que o assistente do editor NÃO carrega. Aqui eles entram porque
# apagar um agendamento ou um arquivo do Drive é uma ação que o assistente pode
# fazer, desde que a pessoa clique para confirmar; tirar o escopo tornaria a
# confirmação inútil (não haveria o que confirmar).
ESCOPOS_DO_ASSISTENTE: frozenset[str] = frozenset(pat.ESCOPOS)


def escopo_do_assistente(
    *,
    user_id: str,
    username: str | None,
    workspace_ids: frozenset[str] | set[str] | list[str],
) -> EscopoEfetivo:
    """O escopo de uma conversa do assistente da Home — o usuário da sessão, alcance completo.

    Molde de `escopo_do_assistente`, com três diferenças deliberadas:

    - `token_id`/`token_prefix` "assistente:…": os baldes de cota
      (`ratelimit:mcp:assistente:{user}`) e a linha de auditoria nascem separados
      dos do PAT e dos do assistente do editor, de graça — tudo chaveia por
      `token_id`;
    - os SEIS escopos (`ESCOPOS_DO_ASSISTENTE`), não os quatro do editor;
    - `origem_dos_fluxos="assistente"`: todo fluxo que ele criar nasce marcado, e
      as listagens o escondem por padrão. É carimbo de origem, não privilégio —
      não amplia alcance nenhum.

    A cota de TOKENS do modelo continua na chave `assistente:tokens:{user}`
    (`cotas.chave_de_tokens`), COMPARTILHADA com o editor: o modelo é o mesmo e o
    orçamento por pessoa é um só.
    """
    return EscopoEfetivo(
        user_id=user_id,
        username=username,
        token_id=f"{PREFIXO_DO_ASSISTENTE}:{user_id}",
        token_prefix=PREFIXO_DO_ASSISTENTE,
        scopes=ESCOPOS_DO_ASSISTENTE,
        workspace_ids=frozenset(workspace_ids),
        todos_os_workspaces=True,
        origem_dos_fluxos="assistente",
    )


def escopo_da_chamada(ctx) -> EscopoEfetivo:
    """O escopo desta chamada, pelo `ctx` da tool ou pelo `ContextVar`.

    A ordem importa: `request.state` é por request e não se confunde entre
    chamadas concorrentes; o `ContextVar` é o reserva (e o único caminho em
    testes que chamam a função da tool direto). Sem nenhum dos dois a chamada
    não está autenticada — e aí não há o que responder além de "proibido".
    """
    requisicao = getattr(getattr(ctx, "request_context", None), "request", None)
    escopo = getattr(getattr(requisicao, "state", None), "escopo", None)
    if isinstance(escopo, EscopoEfetivo):
        return escopo
    do_contexto = ESCOPO_ATUAL.get()
    if do_contexto is not None:
        return do_contexto
    raise erro(
        "forbidden",
        "Chamada sem identidade: nenhum token pessoal de acesso foi resolvido.",
        "conecte-se com Authorization: Bearer atl_pat_…",
    )


def exigir_escopo(escopo: EscopoEfetivo, *necessarios: str) -> None:
    """Recusa a chamada nomeando o escopo que falta.

    Nomear é deliberado: quem chama não tem como adivinhar qual caixa marcar na
    tela de tokens, e o nome do escopo não revela nada sobre os dados. O hint
    diz QUEM marca: a tela de tokens só abre para o administrador do sistema
    (`web/proxy.ts` devolve `/` a quem não é admin).
    """
    faltando = [e for e in necessarios if not escopo.tem(e)]
    if not faltando:
        return
    raise erro(
        "forbidden_scope",
        "Este token não tem o escopo necessário: " + ", ".join(faltando) + ".",
        "crie um token com esse escopo em /settings/tokens "
        "(hoje, página só de administradores do sistema)",
        missing_scope=faltando if len(faltando) > 1 else faltando[0],
    )
