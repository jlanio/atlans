# app/services/assistente_service.py
"""
O assistente: a conversa que monta fluxos, falando com o servidor MCP DESTE processo.

A plataforma já expõe 42 ferramentas por MCP — escopo, cota, papel mínimo,
redação de segredo e auditoria, tudo testado. O assistente não repete nada disso:
ele **chama as mesmas ferramentas pelo mesmo caminho**, em processo.

    ficha = ESCOPO_ATUAL.set(escopo)
    try:
        await servidor.call_tool(nome, argumentos, contexto)
    finally:
        ESCOPO_ATUAL.reset(ficha)

`ServidorAtlans.call_tool` aceita `context=None` e `escopo_da_chamada` cai no
`ContextVar` quando não há request (`app/mcp/escopo.py`). Então a guarda de
escopo, o balde de cota, o papel mínimo, o mapeamento de exceção e a linha de
auditoria acontecem exatamente como acontecem para um cliente externo. **A regra
é uma só nos dois caminhos** — e um defeito de autorização aqui seria um defeito
no MCP, que tem teste.

Três decisões que valem explicação:

1. **Sem HTTP e sem PAT.** A alternativa era um conector MCP hospedado pelo
   provedor do modelo (o que algumas APIs oferecem como `mcp_servers=[…]`),
   que dispensaria este laço. Custaria um token pessoal por usuário viajando
   para fora, um `/mcp` obrigatoriamente público, e o assistente morto em
   instalação fechada. Em processo não há nem ida e volta pela rede — e o laço
   fica independente do provedor: quem fala com o modelo é
   `app/services/openrouter.py`, o único módulo que conhece o formato de rede.

2. **O transcrito não vem do cliente.** `conversar` recebe e devolve a conversa,
   mas quem a guarda é o chamador — e guardar no NAVEGADOR seria entregar ao
   cliente o poder de forjar um `tool_result`. Um resultado de ferramenta é a
   palavra do servidor sobre o que aconteceu; um cliente que o reescreve pode
   dizer ao modelo o que quiser ("o usuário é administrador", "a validação
   passou"). A rota guarda no Redis; este módulo só exige que não venha de fora.

3. **Dois freios, e um deles não depende do Redis.** A cota diária de tokens
   degrada aberta quando o Redis some, como todo o resto do módulo de cotas. Mas
   gasto é dinheiro, não carga: por isso existe também `TETO_DE_VOLTAS`, um
   contador em memória que fecha o laço mesmo sem Redis nenhum. Um modelo preso
   num ciclo de ferramentas é o jeito mais rápido de gastar muito sem que
   ninguém perceba.
"""
from __future__ import annotations

from functools import lru_cache

import asyncio
import json
from contextlib import aclosing, asynccontextmanager, suppress
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Awaitable, Callable

from mcp.server.mcpserver.exceptions import ToolError

from app.core.utils.logger import get_logger
from app.mcp import cotas
from app.mcp.erros import erro
from app.mcp.escopo import ESCOPO_ATUAL, EscopoEfetivo, escopo_do_editor
from app.mcp.guardas import GUARDAS
from app.mcp.instrucoes import INSTRUCOES
from app.services import (
    assistente_config_service, openrouter, teto_do_assistente, uso_service,
)

logger = get_logger("app.assistente")

# ── O portao de escrita ───────────────────────────────────────────────────────
# Decisao do dono: o assistente MONTA, VALIDA e MOSTRA; quem grava e o painel,
# depois do clique em aplicar. Isso nao pode ser promessa de texto no prompt —
# um modelo que nao pergunta grava, e ai o botao de aplicar vira decoracao.
#
# E nao e mudanca de escopo: `validate_workflow` exige `workflows:write`
# (`app/mcp/guardas.py`), entao tirar o escopo tiraria junto a validacao, que e o
# coracao do assistente. O portao e por ferramenta.
#
# A regra sai de `GUARDAS` em vez de uma lista escrita a mao, que envelheceria na
# primeira ferramenta nova: tudo que NAO e somente-leitura esta fora, menos as
# duas excecoes abaixo. Ferramenta de escrita nova nasce bloqueada — falha
# fechada, que e a direcao certa para errar.
ESCREVEM_MAS_PASSAM = frozenset(
    {
        # Simula a definicao inteira e nao persiste nada. E o laco que torna o
        # assistente util: montar, ver o relatorio, corrigir, repetir.
        "validate_workflow",
        # Excecao deliberada do dono: o assistente executa. Ele pede aval em texto
        # e roda no turno seguinte — a confirmacao e da conversa, nao do codigo.
        "run_workflow",
        # Guardar no catalogo uma fonte WFS que a sondagem confirmou: barato,
        # reversivel, nao executa nada — e e o que faz o proximo pedido achar a
        # fonte sem sondar de novo. Mesma decisao do dono que a Home aplica.
        "register_source",
        # Sondar um WFS: so metadados, e atualiza o estado de uma fonte ja
        # catalogada. Sem isto o assistente so veria o catalogo, nunca a fonte nova.
        "probe_source",
    }
)


# ── A entrega ────────────────────────────────────────────────────────────────
# A ferramenta que poe o fluxo na tela. Ela NAO existe no MCP: nao entra em
# `GUARDAS`, nao aparece no `/mcp`, e um cliente externo nunca a ve. O canvas e
# do editor, e so faz sentido para quem esta olhando para ele.
#
# Por que ela existe. Antes, por o fluxo na tela era EFEITO COLATERAL de uma
# chamada a `validate_workflow`: o painel lia a definicao do argumento daquela
# ferramenta e desenhava. Funcionava quando o modelo validava — e nao havia nada
# que o obrigasse a validar. Pedindo "lê o shapefile e faz buffer de 500 m", ele
# podia ler o Drive, executar e devolver o GeoJSON: pedido atendido, canvas
# vazio. Nenhuma instrucao conserta isso, porque o modelo nao tinha AFORDANCIA
# de entrega — nao existia nada cujo nome fosse "entregue o fluxo".
#
# Agora existe, e o prompt pode exigi-la pelo nome. Validar volta a ser meio.
NOME_DO_DESENHO = "desenhar_no_canvas"

FERRAMENTA_DO_DESENHO: dict[str, Any] = {
    "name": NOME_DO_DESENHO,
    "description": (
        "Desenha o fluxo no canvas de quem esta conversando, AGORA. E a sua "
        "entrega: enquanto voce nao chamar isto, a pessoa nao ve fluxo nenhum.\n\n"
        "Chame a cada passo do trabalho, nao so no fim — a pessoa acompanha o "
        "fluxo crescer. Mande sempre a definicao INTEIRA como ela esta ate "
        "agora, e nao um pedaco: o canvas e substituido pelo que voce mandar, "
        "preservando a posicao dos nos que continuarem existindo.\n\n"
        "Nao grava nada. O fluxo so e salvo quando a pessoa clica em Salvar."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "definition": {
                "type": "object",
                "description": (
                    "A definicao inteira ate agora: `nodes` e `edges`, no mesmo "
                    "formato que `validate_workflow` recebe."
                ),
            },
            "nota": {
                "type": "string",
                "description": (
                    "Uma linha sobre o que mudou neste desenho, para a pessoa "
                    "acompanhar. Ex.: 'liguei o buffer na leitura do Drive'."
                ),
            },
        },
        "required": ["definition"],
    },
}


def _ja_desenhou(conversa: list[dict[str, Any]]) -> bool:
    """Alguem ja chamou `desenhar_no_canvas` nesta conversa?

    Lido do TRANSCRITO, e nao de uma variavel do laco, porque a conversa e
    retomada entre turnos: a pessoa manda a segunda mensagem e o laco recomeca
    do zero. Um contador em memoria diria "ainda nao desenhou" numa conversa que
    ja tem um fluxo inteiro na tela.
    """
    for mensagem in conversa:
        if mensagem.get("role") != "assistant":
            continue
        conteudo = mensagem.get("content")
        if not isinstance(conteudo, list):
            continue
        for bloco in conteudo:
            if (
                isinstance(bloco, dict)
                and bloco.get("type") == "tool_use"
                and bloco.get("name") == NOME_DO_DESENHO
            ):
                return True
    return False


# A recusa de executar antes de desenhar. E o mesmo caminho que produzia a
# resposta-dado: ler o Drive, rodar, devolver o artefato — pedido atendido sem
# nunca montar nada. Recusar ate existir um fluxo na tela fecha essa porta sem
# tirar a execucao do escopo, e o ciclo que o dono descreve (montar, testar,
# decidir) continua inteiro: desenhe, e ai execute.
EXIGEM_DESENHO_ANTES = frozenset({"run_workflow"})

MENSAGEM_DE_EXECUTAR_ANTES = (
    f"Ainda nao ha fluxo no canvas. Chame `{NOME_DO_DESENHO}` com a definicao "
    "antes de executar — a pessoa precisa ver o que vai rodar. Executar para "
    "responder com o dado nao e o trabalho aqui: o trabalho e montar o fluxo."
)


def bloqueada_no_editor(nome: str) -> bool:
    """True se esta ferramenta nao pode ser usada pelo assistente."""
    guarda = GUARDAS.get(nome)
    if guarda is None:
        # Sem linha em GUARDAS a ferramenta nao existe para o MCP, e `call_tool`
        # a recusaria de qualquer jeito. Recusar aqui tambem mantem a resposta
        # uniforme em vez de deixar vazar o erro do servidor.
        return True
    if guarda.read_only:
        return False
    return nome not in ESCREVEM_MAS_PASSAM


# O texto da recusa diz o que fazer em vez disso. Sem isso o modelo tenta de
# novo, gasta volta e termina a conversa sem entregar o fluxo.
MENSAGEM_DO_PORTAO = (
    "Esta ferramenta nao esta disponivel no assistente: quem grava o fluxo e a "
    "pessoa, pelo botao de aplicar no editor. Mostre a definicao final e ofereca "
    "aplicar."
)


# Streaming é obrigatório com `max_tokens` grande: sem ele a requisição estoura o
# tempo limite HTTP antes de o modelo terminar.
MAX_TOKENS = 64_000

# O esforço de raciocínio pedido ao modelo (`reasoning.effort` no OpenRouter, que
# o traduz para o que cada família aceita). Alto porque montar um fluxo é
# planejamento: o modelo lê o catálogo, escolhe nós, casa portas e corrige a
# validação — economizar aqui aparece como fluxo errado, não como resposta lenta.
ESFORCO_DO_RACIOCINIO = "high"

# Quantas ferramentas de uma MESMA volta correm ao mesmo tempo. O teto protege
# o resto do worker: cada task pode abrir a própria sessão de banco (o portão
# da Home lê a origem do fluxo; corpos de tool consultam à vontade) e o pool do
# processo é um só (POOL_SIZE + MAX_OVERFLOW). Quem decide QUANTAS chamadas vêm
# na volta é o modelo; quem decide quantas correm POR VEZ é este teto.
TETO_DO_LOTE_EM_PARALELO = 5

# Uma volta = uma chamada ao modelo. Montar um fluxo de verdade leva de 6 a 12
# (entender, guia, catálogo, `describe_node` de cada nó, validar, corrigir,
# validar de novo). O teto existe para o caso patológico: o modelo que valida,
# corrige e revalida sem convergir. Ao bater, a conversa termina com uma
# explicação em vez de continuar gastando.
TETO_DE_VOLTAS = 24

# Um resultado de ferramenta grande (o índice do catálogo, uma definição inteira)
# entra no histórico e é reenviado a cada volta. Cortar protege o contexto e a
# conta; o corte é anunciado para o modelo saber que houve corte — um truncamento
# silencioso faria o modelo concluir que o dado simplesmente não existe.
MAX_CHARS_POR_RESULTADO = 60_000
AVISO_DE_CORTE = "\n\n[resultado cortado: use um filtro mais estreito para ver o resto]"


@dataclass(frozen=True)
class Uso:
    """O que um turno custou, somado ao longo da conversa.

    As chaves são as que `openrouter._uso_do_projeto` produz. `entrada` já
    INCLUI o que veio do cache (`cache_leitura` e `cache_escrita` são recortes
    dela, informativos), e `raciocinio` é um recorte de `saida`. `custo` vem em
    créditos do OpenRouter (dólares) — é informação para o log e para a pessoa,
    não para a cota, que é em tokens.
    """

    entrada: int = 0
    saida: int = 0
    cache_leitura: int = 0
    cache_escrita: int = 0
    raciocinio: int = 0
    custo: float = 0.0

    @classmethod
    def de(cls, uso: dict[str, Any] | None) -> "Uso":
        uso = uso or {}
        return cls(
            entrada=int(uso.get("entrada") or 0),
            saida=int(uso.get("saida") or 0),
            cache_leitura=int(uso.get("cache_leitura") or 0),
            cache_escrita=int(uso.get("cache_escrita") or 0),
            raciocinio=int(uso.get("raciocinio") or 0),
            custo=float(uso.get("custo") or 0.0),
        )

    def __add__(self, outro: "Uso") -> "Uso":
        return Uso(
            entrada=self.entrada + outro.entrada,
            saida=self.saida + outro.saida,
            cache_leitura=self.cache_leitura + outro.cache_leitura,
            cache_escrita=self.cache_escrita + outro.cache_escrita,
            raciocinio=self.raciocinio + outro.raciocinio,
            custo=self.custo + outro.custo,
        )

    @property
    def cobravel(self) -> int:
        """O total que conta para a cota: tudo o que entrou mais tudo o que saiu.

        A leitura de cache CONTA — custa 10 % do preço de entrada, mas custa, e a
        cota é sobre o que a plataforma paga. Ela já está dentro de `entrada`,
        então não é somada de novo.
        """
        return self.entrada + self.saida

    def como_dict(self) -> dict[str, Any]:
        return {
            "entrada": self.entrada,
            "saida": self.saida,
            "cache_leitura": self.cache_leitura,
            "cache_escrita": self.cache_escrita,
            "raciocinio": self.raciocinio,
            "custo": round(self.custo, 6),
            "total": self.cobravel,
        }


@dataclass(frozen=True)
class Evento:
    """Um quadro do SSE. `tipo` é o contrato com o painel da web."""

    tipo: str
    dados: dict[str, Any] = field(default_factory=dict)


class ContextoLocal:
    """O `ctx` que as ferramentas recebem quando o assistente as chama em processo.

    Existe por causa de UMA ferramenta: `run_workflow` chama
    `ctx.report_progress(...)` para relatar o andamento nó a nó
    (`app/mcp/tools/execucao.py`). Todas as outras só usam o `ctx` para descobrir
    o escopo — e `escopo_da_chamada` procura `ctx.request_context.request.state`,
    não acha (esta classe não tem nada disso, de propósito) e cai no `ContextVar`.

    O gerente de ferramentas do SDK não chama método nenhum deste objeto: ele o
    repassa como argumento para a função da ferramenta e nada mais
    (`Tool.run`). Por isso um substituto desta simplicidade basta.

    E aqui o progresso funciona MELHOR que no caminho MCP: lá
    `report_progress` é silencioso sem um `progressToken` do cliente; aqui cada
    nó concluído vira um quadro no SSE que o navegador está lendo.
    """

    def __init__(self, emitir, ferramenta_id: str | None = None) -> None:
        self._emitir = emitir
        # O `tool_use_id` da chamada dona deste contexto. Com as ferramentas de
        # uma volta rodando em PARALELO, o quadro `progresso` precisa dizer de
        # quem ele é — sem o id, o navegador pinta a barra na ferramenta errada
        # (o reducer casava "a que está correndo", e agora correm várias).
        self._ferramenta_id = ferramenta_id

    async def report_progress(
        self, progress: float, total: float | None = None, message: str | None = None
    ) -> None:
        dados: dict[str, Any] = {
            "concluidos": int(progress),
            "total": int(total) if total is not None else None,
            "mensagem": message,
        }
        if self._ferramenta_id is not None:
            dados["id"] = self._ferramenta_id
        await self._emitir(Evento("progresso", dados))


def criar_cliente() -> openrouter.ClienteOpenRouter:
    """O cliente do modelo, construído a partir da chave da plataforma.

    A configuração é lida AQUI, a cada conversa, e não no import: é o que deixa
    o teste trocá-la com `monkeypatch` e o operador trocá-la com um reinício.
    Com ASSISTENTE_ATRIBUICAO, o nome e o `FRONTEND_URL` vão como atribuição do
    app no painel do OpenRouter; sem ela, nada identifica a instalação.
    """
    from app.core.config import (
        ASSISTENTE_ATRIBUICAO, FRONTEND_URL, OPENROUTER_API_KEY, OPENROUTER_BASE_URL,
    )

    return openrouter.ClienteOpenRouter(
        OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
        referer=(FRONTEND_URL or None) if ASSISTENTE_ATRIBUICAO else None,
        titulo="Atlans" if ASSISTENTE_ATRIBUICAO else None,
    )


def escopo_do_editor_para(usuario, workspace_ids) -> EscopoEfetivo:
    """O escopo desta conversa, a partir do usuário da sessão.

    Ponte de uma linha entre o `User` do banco e o construtor puro de
    `app/mcp/escopo.py`, que não conhece modelo nenhum de propósito. Sem ela a
    rota teria de saber os nomes dos campos do usuário — e passaria a quebrar
    quando eles mudassem.
    """
    return escopo_do_editor(
        user_id=usuario.id_hash,
        username=getattr(usuario, "username", None),
        workspace_ids=workspace_ids,
    )


async def ferramentas_para_o_modelo(
    servidor, escopo: EscopoEfetivo, superficie: "Superficie | None" = None
) -> list[dict[str, Any]]:
    """As ferramentas do MCP no formato que a API do modelo espera.

    `list_tools()` já filtra pelo `ContextVar` — o mesmo mecanismo que serve ao
    cliente externo serve aqui, então o catálogo do assistente é exatamente o que
    o escopo dele alcança, sem uma segunda lista para envelhecer.

    A `superficie` decide DUAS coisas: quais tools do MCP entram (`permitida` —
    no editor, tudo menos o que o portão de escrita barra; na Home, tudo o que
    está em `GUARDAS`) e quais ferramentas LOCAIS abrem a lista
    (`ferramentas_extras` — o desenho no editor, o globo na Home). O default é o
    editor, então o catálogo dele fica byte-a-byte igual.

    O formato é o de rede (`{"type": "function", "function": {...}}`), montado
    por `openrouter.ferramenta` a partir do `input_schema` do MCP — o mesmo
    esquema, sem tradução de conteúdo. O argumento chega em stream, gota a gota,
    e por isso um corte por `max_tokens` pode entregar metade de um argumento
    que ainda parece bem formado; a defesa está no laço (`length`).
    """
    superficie = superficie or EDITOR
    ficha = ESCOPO_ATUAL.set(escopo)
    try:
        tools = await servidor.list_tools()
    finally:
        ESCOPO_ATUAL.reset(ficha)

    do_mcp = [
        openrouter.ferramenta(t.name, t.description or "", t.input_schema)
        for t in tools
        if superficie.permitida(t.name)
    ]
    # As ferramentas da superficie vem PRIMEIRO na lista, e isso nao e estetica:
    # o que abre a lista e o que o modelo le primeiro quando decide o que fazer.
    # A ferramenta que define a entrega nao pode estar enterrada entre 38 outras.
    extras = [
        openrouter.ferramenta(f["name"], f.get("description"), f.get("input_schema"))
        for f in superficie.ferramentas_extras
    ]
    return [*extras, *do_mcp]


# O que muda em relacao a um cliente MCP externo. Curto de proposito: corrige o
# UNICO ponto em que `INSTRUCOES` deixa de valer aqui, que e a frase "so chame
# create_workflow/update_workflow depois de a validacao passar" — essas
# ferramentas nao existem para o assistente. Sem esta correcao o modelo procura
# uma ferramenta que nao esta na lista e termina a conversa sem entregar nada.
INSTRUCOES_DO_EDITOR = """\
Voce esta dentro do editor do Atlans, olhando para o mesmo canvas que a pessoa.
Nao e um cliente externo, e o trabalho aqui e outro.

SUA ENTREGA E O FLUXO NO CANVAS
`desenhar_no_canvas` e a unica coisa que a pessoa ve acontecer. Enquanto voce
nao chamar, a tela dela esta vazia — por mais que voce tenha explicado bem.

- Desenhe CEDO e desenhe VARIAS VEZES. Assim que souber o primeiro no, desenhe.
  Ligou o segundo, desenhe de novo. A pessoa esta acompanhando o fluxo crescer;
  um unico desenho no fim desperdica isso.
- Mande sempre a definicao INTEIRA como ela esta, nunca so a parte nova.
- Use a `nota` para dizer em uma linha o que mudou.

NAO E ENTREGA:
- Responder com o DADO. Se pedirem "lê o shapefile e faz buffer de 500 m", o
  pedido e um FLUXO que faz isso, nao o GeoJSON do resultado. Executar para
  produzir a resposta e o erro mais facil de cometer aqui.
- Mostrar a definicao em texto ou em bloco de codigo. Ela vai no canvas.
- Descrever o que voce faria. Desenhe.

A ORDEM DO TRABALHO
1. Entenda o que a pessoa quer. Pergunte se faltar algo essencial.
2. Dado externo (WFS)? `search_sources` pelo tema e `describe_source` ANTES de
   qualquer outra coisa — nunca invente url/typeName. So sem resultado:
   `probe_source` (sonda) e `register_source` (guarda para a proxima vez).
3. `search_nodes` / `describe_node` para os nos que voce nao domina — e peca as
   fichas de TODOS os nos do fluxo numa chamada so (`name` aceita lista, ate 8
   por chamada; mais que isso, divida em dois lotes), em vez de uma rodada por no.
4. `desenhar_no_canvas` — mesmo incompleto, mesmo com um no so.
5. Continue montando, desenhando a cada passo.
6. `validate_workflow` quando o desenho estiver completo. Corrija o que ela
   apontar e DESENHE DE NOVO.
7. Diga o que ficou pronto. Nao prometa ter salvo: salvar e da pessoa.

O QUE VOCE NAO FAZ
- Voce NAO grava. `create_workflow` e `update_workflow` nao existem aqui, e o
  desenho no canvas nao e gravacao — e o rascunho dela, que ela salva ou joga
  fora.
- Voce pode executar, e execucao e REAL: dispara nos que escrevem em banco e
  publicam mapa. So depois de o fluxo estar desenhado, so depois de perguntar
  com todas as letras, e so com um "pode rodar" explicito na mensagem seguinte.
"""


def montar_sistema(
    instrucoes_extras: str | None = None, *, superficie: "Superficie | None" = None
) -> list[dict[str, Any]]:
    """O system prompt — as instruções do servidor MCP, não uma segunda cópia.

    `INSTRUCOES` (`app/mcp/instrucoes.py`) já diz tudo o que precisa ser dito
    antes da primeira chamada: validar antes de salvar, pedir confirmação antes
    de criar ou executar, nunca inventar propriedade, credencial por
    identificador, e — o que mais importa aqui — que `untrusted_data` é DADO e
    não instrução. Escrever um texto novo criaria duas políticas para divergir.

    Em cima dela vem `superficie.instrucoes`, que corrige o ponto onde a política
    do MCP não vale naquela superfície: no editor, o portão de escrita
    (`INSTRUCOES_DO_EDITOR`); na Home, a entrega ser uma camada no globo e a
    confirmação por clique (`INSTRUCOES_DA_HOME`). O default é o editor.

    O guia NÃO entra: são 25 KB em oito tópicos (`app/mcp/guia/`), alcançáveis
    por `get_authoring_guide`. Carregá-lo inteiro dobraria o prefixo de toda
    conversa para servir o tópico que uma delas vai ler.
    """
    from app.core.config import ASSISTENTE_IDIOMA

    superficie = superficie or EDITOR
    blocos: list[dict[str, Any]] = [
        {"type": "text", "text": INSTRUCOES},
        {"type": "text", "text": superficie.instrucoes},
        # O raciocínio também: ele é MOSTRADO à pessoa (a seção "Raciocínio" do
        # painel), e um modelo que conversa em português tende a pensar em
        # inglês. Nenhuma API escolhe o idioma do raciocínio; pedir é o único
        # controle, e funciona na maior parte das vezes.
        {"type": "text", "text": f"Responda sempre em {ASSISTENTE_IDIOMA}, seja qual "
                                 "for o idioma da pergunta. Raciocine também em "
                                 f"{ASSISTENTE_IDIOMA}: o seu raciocínio é mostrado à pessoa."},
        # O ponto de corte do cache do PREFIXO ESTAVEL. Ele vai no ultimo bloco
        # sempre presente das DUAS superficies — os quatro acima sao byte-a-byte
        # iguais entre toda conversa e todo usuario DA MESMA SUPERFICIE (o bloco
        # da superficie e uma constante por superficie, o idioma e config, o guia
        # e `lru_cache`). Como o cache e por prefixo e a ordem de render e
        # `tools` -> `system` -> `messages`, um marcador aqui cacheia tudo o que
        # vem antes: as ferramentas + estes tres blocos, o prefixo de ~15k tokens.
        # Editor e Home tem prefixos distintos (o bloco [1] difere), entao dois
        # prefixos estaveis, um por superficie — nenhum contamina o outro.
        #
        # O OpenRouter repassa o marcador aos provedores que tem cache de prompt
        # explicito e o ignora nos que cacheiam sozinhos — nos dois casos a
        # segunda conversa de qualquer pessoa (dentro da janela) LE o prefixo
        # em vez de reescreve-lo a preco cheio. O segundo marcador vai na ultima
        # mensagem humana (`openrouter.montar_mensagens`), e fecha o prefixo que
        # e o mesmo em todas as voltas de ferramenta de um turno.
        #
        # So o tipo, sem `ttl`: a duracao do cache e decisao do provedor por
        # tras do roteador, e um campo que ele nao reconhece seria uma recusa a
        # cada conversa.
        {
            "type": "text",
            "text": _guia_do_prefixo(),
            "cache_control": {"type": "ephemeral"},
        },
    ]
    if instrucoes_extras:
        # Fica FORA do cache de proposito: e opcional, hoje nunca passado, e
        # pode ser dinamico. O corte acima ja fechou o prefixo estavel.
        blocos.append({"type": "text", "text": instrucoes_extras})
    return blocos


@lru_cache(maxsize=1)
def _guia_do_prefixo() -> str:
    """Os dois tópicos do guia que entram no prompt, contra os seis que não.

    `recipes` são QUATRO fluxos completos, escritos. É a demonstração de como um
    entregável fica pronto — e era exatamente o que faltava a um modelo que
    respondia com dado. `overview` dá o vocabulário para lê-las.

    Os outros seis (arestas, credenciais, expressões, entradas, SQL, armadilhas)
    continuam sob demanda por `get_authoring_guide`: são referência para dúvida
    pontual, não material que muda a forma do trabalho.

    Custa ~10 KB (~3 k tokens) num prefixo ESTÁVEL, que o cache guarda a 10% —
    é a parte barata de uma conversa. `lru_cache` porque o disco não precisa ser
    lido a cada turno.
    """
    from app.mcp import guia

    partes = [
        "Guia de autoria — o essencial. Os demais tópicos (arestas, credenciais,",
        "expressoes, entradas, SQL, armadilhas) estao em `get_authoring_guide`.",
        "",
        guia.ler_topico("overview"),
        "",
        guia.ler_topico("recipes"),
    ]
    return "\n".join(partes)


# ── Superfícies ───────────────────────────────────────────────────────────────
# O laço é um só; o que muda entre o assistente do editor e o assistente da Home é
# um PACOTE de seis coisas, reunidas aqui. O editor (`EDITOR`) é o default de
# tudo — `conversar`, `montar_sistema` e `ferramentas_para_o_modelo` caem nele
# quando ninguém passa superfície —, então o editor continua byte-a-byte igual e
# os testes atuais passam sem edição. A Home mora em `assistente_superficie.py`, que
# importa este módulo (nunca o contrário) e monta a própria `Superficie`.


@dataclass
class EstadoDoLaco:
    """O estado MUTÁVEL de uma conversa, que o pacote da superfície lê e escreve.

    Vive uma vez por chamada de `conversar`, fora do laço de voltas: `desenhou`
    sobrevive entre os turnos (um fluxo desenhado no turno anterior continua na
    tela). O que é DE UMA CHAMADA (o `tool_use_id`) não mora aqui de propósito:
    as ferramentas de uma volta rodam em paralelo, e um campo compartilhado
    "chamada atual" seria uma corrida — o id viaja como argumento do portão.
    """

    escopo: EscopoEfetivo
    redis: Any
    conversa_id: str | None
    # Canal de saída das ferramentas e dos portões: enfileira um `Evento` que o
    # laço drena e cede no SSE. É o mesmo `emitir` que o `ContextoLocal` usa.
    emitir: Callable[["Evento"], Any]
    desenhou: bool = False


@dataclass(frozen=True)
class Superficie:
    """O pacote que distingue uma superfície da outra. Congelado: é configuração.

    - `instrucoes`: o bloco [1] do system prompt (corrige onde a política do MCP
      não vale ali).
    - `ferramentas_extras`: as ferramentas LOCAIS que abrem a lista do modelo (o
      desenho, o globo) — não existem no MCP.
    - `executores_locais`: nome → corrotina `(argumentos, estado) -> (texto,
      erro)`, para as ferramentas que NÃO vão ao servidor.
    - `permitida`: `(nome) -> bool`, quais tools do MCP entram na lista.
    - `portao`: corrotina `(estado, nome, argumentos, tool_use_id) -> (texto,
      erro) | None`, chamada antes de despachar ao servidor. `None` = pode
      seguir. O `tool_use_id` identifica a chamada exata (a confirmação da Home
      casa o clique por ele) e viaja como argumento porque as ferramentas de
      uma volta rodam em paralelo — estado compartilhado aqui seria corrida.
      A anotação do campo declara os quatro argumentos de propósito: um portão
      novo escrito com três typecheckaria e quebraria em TODA chamada.
    - `quadros_extras`: `(estado, nome, argumentos, resultado, erro) ->
      list[Evento]`, os quadros que aquela superfície emite depois de uma
      ferramenta (a `proposta` no editor; `fluxo`/`camada` na Home).
    """

    nome: str
    instrucoes: str
    ferramentas_extras: tuple[dict[str, Any], ...]
    executores_locais: dict[str, Callable[[Any, EstadoDoLaco], Any]]
    permitida: Callable[[str], bool]
    portao: Callable[[EstadoDoLaco, str, Any, str | None], Any]
    quadros_extras: Callable[[EstadoDoLaco, str, Any, str, bool], list["Evento"]]


async def _desenhar(argumentos: Any, estado: EstadoDoLaco) -> tuple[str, bool]:
    """A entrega do editor: põe o fluxo no canvas. Não vai ao servidor.

    O efeito visível é o quadro `proposta` (emitido por `_quadros_do_editor`); o
    que volta ao modelo é a confirmação de que a pessoa está vendo. Marca
    `estado.desenhou` no sucesso — é o que libera `run_workflow` depois.
    """
    definicao = argumentos.get("definition") if isinstance(argumentos, dict) else None
    if not isinstance(definicao, dict):
        return ("`definition` precisa ser um objeto com `nodes` e `edges`.", True)
    nos = len(definicao.get("nodes") or [])
    arestas = len(definicao.get("edges") or [])
    estado.desenhou = True
    return (
        f"Desenhado no canvas: {nos} nó(s) e {arestas} aresta(s). A pessoa está "
        "vendo agora. Continue montando e chame de novo a cada mudança; valide "
        "com `validate_workflow` quando o desenho estiver completo.",
        False,
    )


async def _portao_do_editor(
    estado: EstadoDoLaco, nome: str, argumentos: Any, tool_use_id: str | None = None
) -> tuple[str, bool] | None:
    """O portão do editor: ordem (desenhe antes de executar) + bloqueio de escrita.

    É o corpo que antes vivia inline em `_executar_ferramenta`. `None` quando a
    ferramenta pode seguir para o servidor.
    """
    if nome in EXIGEM_DESENHO_ANTES and not estado.desenhou:
        logger.info("Assistente barrou %s antes do desenho (usuário %s).", nome, estado.escopo.user_id)
        return (MENSAGEM_DE_EXECUTAR_ANTES, True)
    if bloqueada_no_editor(nome):
        # A GARANTIA do portão, e não o conforto. Esconder a ferramenta da lista
        # evita que o modelo a queira; recusar aqui impede que ela rode quando
        # ele a nomeia assim mesmo — porque leu num exemplo, alucinou, ou alguém
        # mandou no texto de um fluxo. É a mesma separação que o MCP faz entre
        # `list_tools` e `call_tool`.
        logger.info("Assistente barrou %s (usuário %s).", nome, estado.escopo.user_id)
        return (MENSAGEM_DO_PORTAO, True)
    return None


def _quadros_do_editor(
    estado: EstadoDoLaco, nome: str, argumentos: Any, resultado: str, deu_erro: bool
) -> list["Evento"]:
    """O quadro `proposta` — a definição que o botão Aplicar recebe."""
    proposta = _proposta_de(nome, argumentos, resultado, deu_erro)
    return [Evento("proposta", proposta)] if proposta is not None else []


EDITOR = Superficie(
    nome="editor",
    instrucoes=INSTRUCOES_DO_EDITOR,
    ferramentas_extras=(FERRAMENTA_DO_DESENHO,),
    executores_locais={NOME_DO_DESENHO: _desenhar},
    permitida=lambda nome: not bloqueada_no_editor(nome),
    portao=_portao_do_editor,
    quadros_extras=_quadros_do_editor,
)


async def conversar(
    *,
    escopo: EscopoEfetivo,
    transcrito: list[dict[str, Any]],
    servidor,
    cliente,
    redis=None,
    instrucoes_extras: str | None = None,
    superficie: "Superficie | None" = None,
    conversa_id: str | None = None,
    ao_fechar_turno: Callable[[list[dict[str, Any]]], Any] | None = None,
) -> AsyncIterator[Evento]:
    """Roda a conversa até o modelo parar de pedir ferramenta.

    `transcrito` entra com o histórico (incluindo a mensagem nova de quem está
    usando) e o último evento devolve o histórico atualizado, para o chamador
    guardar. Ver a nota 2 do módulo: esse histórico **não pode** vir do
    navegador.

    Emite, nesta ordem e quantas vezes forem necessárias:
      `pensando` · `texto` · `cota` · `ferramenta` · `progresso` · `ferramenta_fim`
    (`cota` sai depois de cada resposta do modelo, com o acumulado da janela —
    só quando há Redis para contar; não entra no transcrito nem no replay.)

    O último quadro é SEMPRE `fim`, mesmo quando a conversa acabou mal — é ele
    que carrega o transcrito, e perder o transcrito porque o modelo tropeçou na
    oitava volta faria a pessoa recomeçar do zero. Quando houve falha, um quadro
    `erro` vem antes e o `fim` traz `ok=False`.

    O laço em si mora em `LacoDaConversa`.
    """
    laco = LacoDaConversa(
        escopo=escopo,
        transcrito=transcrito,
        servidor=servidor,
        cliente=cliente,
        redis=redis,
        superficie=superficie or EDITOR,
        conversa_id=conversa_id,
        ao_fechar_turno=ao_fechar_turno,
    )
    async with aclosing(laco.rodar(instrucoes_extras)) as eventos:
        async for evento in eventos:
            yield evento


class LacoDaConversa:
    """Uma chamada de `conversar`: o que atravessa as voltas e as fases de cada uma.

    Cada volta é uma chamada ao modelo (`_chamar_modelo`), a cobrança dela
    (`_cobrar`), a resposta entrando na conversa (`_anexar_resposta`) e, se o
    modelo pediu, as ferramentas (`_executar_chamadas`); o `fim` sai de
    `_encerrar`. O gancho de fechar o turno, que era uma closure do gerador,
    virou método; o canal das ferramentas e dos portões é o `put` da fila.

    Continua sendo um gerador PUXADO pelo SSE: as fases que emitem quadros são
    geradores também, e cada efeito (a cobrança, o gancho, a ferramenta) só
    acontece quando quem consome pede o quadro seguinte. Cada fase aninhada é
    aberta com `aclosing`: se quem consome fecha o gerador no meio, ela fecha
    junto, na hora — como fechava quando o laço era um corpo só.
    """

    def __init__(
        self,
        *,
        escopo: EscopoEfetivo,
        transcrito: list[dict[str, Any]],
        servidor,
        cliente,
        redis,
        superficie: "Superficie",
        conversa_id: str | None,
        ao_fechar_turno: Callable[[list[dict[str, Any]]], Any] | None,
    ) -> None:
        self.escopo = escopo
        self.servidor = servidor
        self.cliente = cliente
        self.redis = redis
        self.superficie = superficie
        self.ao_fechar_turno = ao_fechar_turno
        self.conversa = list(transcrito)
        self.uso_total = Uso()
        self.voltas = 0
        self.falhou = False

        # Fila ASSINCRONA (nao uma list): a ferramenta roda numa task e o laco drena
        # esta fila EM PARALELO, cedendo cada quadro assim que chega. Com a list
        # drenada so depois do `await` da ferramenta, o `report_progress` de um run
        # longo ficava em buffer e chegava tudo de uma vez, no fim da execucao.
        #
        # O `put` dela e o canal de saida das ferramentas e dos portoes (o
        # `report_progress`, o quadro de confirmacao da Home): enfileira em vez de
        # ceder direto porque um gerador assincrono so pode ceder de dentro do
        # proprio corpo. E o `put` da fila, e nao um metodo do laco: um metodo
        # ligado, guardado no estado e no contexto das ferramentas, prenderia o
        # laco inteiro (a conversa, o catalogo, o cliente) num ciclo de
        # referencia que so o coletor ciclico desfaz, bem depois do fim.
        self.fila: asyncio.Queue = asyncio.Queue()
        # Sentinela posto quando a ferramenta termina (padrao do `com_batimento`): o
        # laco drena ate ve-lo, sem NUNCA cancelar `fila.get()` — assim nenhum quadro
        # enfileirado se perde numa corrida de cancelamento.
        self._fim_da_ferramenta = object()

        self.conversa_id = conversa_id

        # Resolvidos UMA vez por conversa, em `_preparar`; o estado das
        # ferramentas (`EstadoDoLaco`) tambem nasce la, por ultimo.
        self.teto_de_tokens: int | None = None
        self.modelo: str | None = None
        self.ferramentas: list[dict[str, Any]] = []
        self.sistema: list[dict[str, Any]] = []

    async def _fechar_turno(self) -> None:
        """Gancho chamado após cada mensagem entrar na conversa, para o chamador
        persistir de forma incremental (o PR do assistente usa; o editor não
        passa nada). Sempre em try/except: falhar ao persistir não pode derrubar
        a conversa que já está no ar."""
        if self.ao_fechar_turno is None:
            return
        try:
            await self.ao_fechar_turno(self.conversa)
        except Exception:
            logger.exception("Falha no gancho ao_fechar_turno (usuário %s).", self.escopo.user_id)

    async def rodar(self, instrucoes_extras: str | None) -> AsyncIterator[Evento]:
        """O laço: uma volta por resposta do modelo, até ele parar de pedir
        ferramenta — ou até uma saída por erro, que ainda termina em `fim`."""
        await self._preparar(instrucoes_extras)
        while True:
            self.voltas += 1
            if self.voltas > TETO_DE_VOLTAS:
                self.falhou = True
                yield self._erro_do_teto()
                break

            resposta: openrouter.Resposta | None = None
            async with aclosing(self._chamar_modelo()) as pedacos:
                async for pedaco in pedacos:
                    if isinstance(pedaco, openrouter.Resposta):
                        resposta = pedaco
                    else:
                        yield pedaco
            if resposta is None:
                break  # o modelo falhou, e o quadro `erro` já saiu

            cota = await self._cobrar(resposta)
            if cota is not None:
                yield cota
            await self._anexar_resposta(resposta)

            erro = self._erro_da_parada(resposta.parada)
            if erro is not None:
                self.falhou = True
                yield erro
                break
            if resposta.parada != "tool_calls":
                break
            chamadas = [b for b in resposta.blocos if b.get("type") == "tool_use"]
            if not chamadas:
                break

            async with aclosing(self._executar_chamadas(chamadas)) as quadros:
                async for quadro in quadros:
                    yield quadro

        yield self._encerrar()

    async def _preparar(self, instrucoes_extras: str | None) -> None:
        """A cota, o modelo, as ferramentas e o sistema — uma vez por conversa."""
        # O teto pode vir do PLANO, e e resolvido UMA vez por conversa: a verificacao
        # de agora e o quadro `cota` de cada volta usam o MESMO valor. Resolver de
        # novo no meio do turno faria o donut oscilar se o plano mudasse entre as
        # voltas, e custaria uma consulta por resposta do modelo.
        #
        # Aqui nao ha sessao de banco — este laco roda dentro de um gerador SSE, e
        # a do handler ja morreu. `teto_de` abre a propria quando precisa.
        self.teto_de_tokens = await teto_do_assistente.teto_de(self.escopo.user_id, redis=self.redis)
        await cotas.verificar_tokens_do_assistente(
            self.redis, self.escopo.user_id, teto=self.teto_de_tokens
        )
        # UMA vez por conversa, e não a cada volta: o admin pode trocar o modelo no
        # meio de uma conversa em curso, e trocar de modelo entre duas voltas do
        # MESMO raciocínio muda o comportamento no meio do caminho. Quem já começou
        # termina no modelo em que começou — é o que a tela promete.
        self.modelo = await assistente_config_service.modelo_em_uso(redis=self.redis)

        self.ferramentas = await ferramentas_para_o_modelo(self.servidor, self.escopo, self.superficie)
        self.sistema = montar_sistema(instrucoes_extras, superficie=self.superficie)
        # Por ultimo, como antes: `_ja_desenhou` le o transcrito, e o que der
        # errado nele vem depois da cota (a recusa que a rota sabe mostrar).
        self.estado = EstadoDoLaco(
            escopo=self.escopo,
            redis=self.redis,
            conversa_id=self.conversa_id,
            emitir=self.fila.put,
            # Do TRANSCRITO, nao de zero: a conversa e retomada entre turnos, e um
            # fluxo desenhado na mensagem anterior continua na tela. A Home nunca
            # desenha, entao para ela isto e sempre False (e ninguem le).
            desenhou=_ja_desenhou(self.conversa),
        )

    def _erro_do_teto(self) -> Evento:
        """O `erro` de quando a conversa passa de `TETO_DE_VOLTAS`."""
        logger.warning(
            "Assistente interrompido no teto de voltas (usuário %s, %d tokens).",
            self.escopo.user_id,
            self.uso_total.cobravel,
        )
        return Evento(
            "erro",
            {
                "code": "loop_limit",
                "message": (
                    f"A conversa passou de {TETO_DE_VOLTAS} rodadas de ferramenta "
                    "sem concluir."
                ),
                "hint": "descreva o fluxo em partes menores, ou diga o que ficou faltando",
                # O número à parte: a Home traduz a frase e precisa citá-lo.
                "teto": TETO_DE_VOLTAS,
            },
        )

    async def _chamar_modelo(self) -> AsyncIterator[Evento | openrouter.Resposta]:
        """Uma chamada ao modelo: cede `pensando` e `texto` conforme chegam e,
        por último, a `Resposta` inteira. Uma falha vira o quadro `erro` — e aí
        a `Resposta` não vem."""
        resposta: openrouter.Resposta | None = None
        try:
            # O cliente cede os pedaços visíveis conforme chegam e, por último,
            # a resposta inteira já no formato do projeto. Um stream que morre
            # no meio é exceção — nunca uma resposta pela metade.
            async for pedaco in self.cliente.transmitir(
                modelo=self.modelo,
                sistema=self.sistema,
                conversa=self.conversa,
                ferramentas=self.ferramentas,
                max_tokens=MAX_TOKENS,
                esforco=ESFORCO_DO_RACIOCINIO,
            ):
                if isinstance(pedaco, openrouter.Resposta):
                    resposta = pedaco
                elif pedaco.tipo == "texto":
                    yield Evento("texto", {"texto": pedaco.texto})
                elif pedaco.tipo == "pensando":
                    yield Evento("pensando", {"texto": pedaco.texto})
            if resposta is None:
                raise openrouter.ErroDoOpenRouter("o stream terminou sem a resposta final")
        except Exception as exc:
            logger.exception("Falha ao falar com o modelo (usuário %s).", self.escopo.user_id)
            self.falhou = True
            yield Evento(
                "erro",
                {
                    "code": "modelo_indisponivel",
                    "message": "Não consegui falar com o modelo agora.",
                    "hint": "tente de novo em alguns instantes",
                    "detalhe": exc.__class__.__name__,
                },
            )
            return
        yield resposta

    async def _cobrar(self, resposta: openrouter.Resposta) -> Evento | None:
        """Soma o uso da volta, registra-o e cobra a cota. Devolve o quadro
        `cota` com o acumulado da janela, ou `None` sem Redis para contar."""
        uso_da_volta = Uso.de(resposta.uso)
        self.uso_total = self.uso_total + uso_da_volta
        # No MESMO ponto da cobrança da cota, e não no fim da conversa: os dois
        # passam a contar a mesma coisa e não podem divergir, e uma conversa
        # abandonada no meio (aba fechada, stream morto) já deixou registrado o
        # que gastou até aqui. Somar só no fim perderia essas — e perderia para
        # BAIXO, o lado errado de errar num dado que vira decisão de preço.
        await uso_service.registrar_volta(
            user_id=self.escopo.user_id,
            modelo=self.modelo,
            superficie=self.superficie.nome,
            entrada=uso_da_volta.entrada,
            saida=uso_da_volta.saida,
            cache_leitura=uso_da_volta.cache_leitura,
            raciocinio=uso_da_volta.raciocinio,
            custo_usd=uso_da_volta.custo,
        )
        acumulado = await cotas.cobrar_tokens_do_assistente(
            self.redis, self.escopo.user_id, uso_da_volta.cobravel
        )
        if acumulado is None:
            return None
        # O donut da cota sobe DURANTE o turno, a cada resposta do modelo,
        # sem GET: o acumulado que o INCRBY devolveu vai à tela agora. Sem
        # Redis não há contador — e não há quadro.
        return Evento("cota", {"gasto": acumulado, "teto": self.teto_de_tokens})

    async def _anexar_resposta(self, resposta: openrouter.Resposta) -> None:
        """A resposta do modelo entra na conversa, e o turno fecha."""
        # Os blocos já vêm no formato do projeto (dicionários puros): é o que o
        # Redis e o banco guardam e o que volta ao modelo na próxima volta.
        # Uma resposta SEM bloco nenhum (recusa sem saída, `stop` sem texto) não
        # entra: uma mensagem vazia do assistente é recusada pelo provedor em
        # toda retomada, e não há nada nela para a pessoa ver.
        if resposta.blocos:
            self.conversa.append({"role": "assistant", "content": list(resposta.blocos)})
            await self._fechar_turno()
        else:
            logger.warning(
                "Modelo devolveu uma resposta sem conteúdo (parada=%s, usuário %s).",
                resposta.parada,
                self.escopo.user_id,
            )

    def _erro_da_parada(self, parada: str) -> Evento | None:
        """O `erro` das paradas que encerram a conversa mal — a recusa do
        modelo e o corte por `max_tokens`. `None` para as outras."""
        if parada == "content_filter":
            return Evento(
                "erro",
                {
                    "code": "recusado",
                    "message": "O modelo recusou este pedido.",
                },
            )
        if parada == "length":
            # NÃO rodar ferramenta aqui, mesmo havendo blocos `tool_use` na
            # resposta. O argumento chega em stream, então um corte no meio da
            # geração entrega um argumento PELA METADE que ainda pode parecer
            # bem formado — uma definição com metade dos nós, por exemplo.
            # Gravar isso seria destruir o fluxo de alguém em nome de uma
            # resposta truncada.
            logger.warning("Assistente cortado por max_tokens (usuário %s).", self.escopo.user_id)
            return Evento(
                "erro",
                {
                    "code": "resposta_truncada",
                    "message": "A resposta foi cortada no meio e não é segura de aplicar.",
                    "hint": "peça o fluxo em partes menores",
                },
            )
        return None

    async def _executar_chamadas(self, chamadas: list[dict[str, Any]]) -> AsyncIterator[Evento]:
        """As ferramentas que o modelo pediu numa volta, com os quadros de cada
        uma; os resultados voltam à conversa, e o turno fecha."""
        resultados: list[dict[str, Any]] = []
        # Duas pistas. Uma chamada LOCAL (o desenho no editor, o globo na Home)
        # muta o `estado` e a ORDEM entre as chamadas importa — o modelo desenha
        # e executa na MESMA volta, e o portão de `run_workflow` lê o `desenhou`
        # que o desenho acabou de escrever. Com qualquer local no lote, a volta
        # roda como sempre rodou: em fila. Sem local, as chamadas são
        # independentes (portão + servidor, sem escrever no estado) e rodam
        # JUNTAS — a volta custa a ferramenta mais lenta, não a soma.
        tem_local = any(
            self.superficie.executores_locais.get(str(c.get("name") or "")) is not None
            for c in chamadas
        )
        pista = self._em_fila if tem_local else self._em_paralelo
        async with aclosing(pista(chamadas, resultados)) as quadros:
            async for quadro in quadros:
                yield quadro

        # Todos os resultados numa ÚNICA mensagem. Dividir em várias ensina o
        # modelo, em silêncio, a parar de pedir ferramentas em paralelo.
        self.conversa.append({"role": "user", "content": resultados})
        await self._fechar_turno()

    def _executar(self, chamada: dict[str, Any]) -> Awaitable[tuple[str, bool]]:
        """O despacho de UMA chamada (`_executar_ferramenta`), com o
        `ContextoLocal` que carimba o id dela nos quadros de `progresso`."""
        ident = chamada.get("id")
        return _executar_ferramenta(
            servidor=self.servidor,
            escopo=self.escopo,
            nome=chamada.get("name"),
            argumentos=chamada.get("input"),
            contexto=ContextoLocal(self.fila.put, ferramenta_id=ident),
            superficie=self.superficie,
            estado=self.estado,
            tool_use_id=ident,
        )

    async def _em_fila(
        self, chamadas: list[dict[str, Any]], resultados: list[dict[str, Any]]
    ) -> AsyncIterator[Evento]:
        """A pista em fila: cada chamada é anunciada, roda e fecha antes da seguinte."""
        for chamada in chamadas:
            ident, nome, argumentos = chamada.get("id"), chamada.get("name"), chamada.get("input")
            yield Evento(
                "ferramenta",
                {"id": ident, "nome": nome, "argumentos": _resumo(argumentos)},
            )
            # A ferramenta roda numa task e o laco cede o que ela enfileira
            # ENQUANTO ela ainda corre — e isto que faz o `report_progress` de um
            # run longo chegar ao vivo, em vez de tudo de uma vez no fim. O
            # sentinela (posto quando a task termina) fecha o dreno; o resultado
            # vem do `await` da task, que ja concluiu.
            tarefa = asyncio.ensure_future(self._executar(chamada))
            tarefa.add_done_callback(lambda _: self.fila.put_nowait(self._fim_da_ferramenta))
            while True:
                enfileirado = await self.fila.get()
                if enfileirado is self._fim_da_ferramenta:
                    break
                yield enfileirado
            resultado, deu_erro = await tarefa
            evento_fim, quadros, bloco = _fecho_da_chamada(
                self.superficie, self.estado, chamada, resultado, deu_erro
            )
            yield evento_fim
            for quadro in quadros:
                yield quadro
            resultados.append(bloco)

    async def _em_paralelo(
        self, chamadas: list[dict[str, Any]], resultados: list[dict[str, Any]]
    ) -> AsyncIterator[Evento]:
        """A pista paralela: o lote é anunciado inteiro, roda junto (até
        `TETO_DO_LOTE_EM_PARALELO` por vez) e fecha na ordem das chamadas."""
        # Anuncia todas ANTES de disparar: o navegador vê o lote inteiro
        # "correndo", e cada `progresso` acha o card certo pelo `id` que o
        # `ContextoLocal` da chamada carimba.
        for chamada in chamadas:
            yield Evento(
                "ferramenta",
                {
                    "id": chamada.get("id"),
                    "nome": chamada.get("name"),
                    "argumentos": _resumo(chamada.get("input")),
                },
            )
        # O teto de simultaneidade protege o resto do worker: N vem do
        # modelo, e cada task pode abrir a própria sessão de banco — sem a
        # vaga, uma volta com 13+ chamadas esgotaria o pool do processo e
        # travaria requisições que nem são desta conversa.
        vaga = asyncio.Semaphore(TETO_DO_LOTE_EM_PARALELO)
        tarefas = [asyncio.ensure_future(self._executar_com_vaga(vaga, chamada)) for chamada in chamadas]
        # Um sentinela POR task (objetos distintos, comparados por
        # identidade): o dreno sabe QUAL terminou, e cada `ferramenta_fim`
        # sai NA ORDEM das chamadas mas assim que a sua task (e as
        # anteriores) acabaram — o fim do rápido não espera o lento que
        # veio depois. Os `tool_result` seguem casando com os `tool_use`.
        fims = [object() for _ in tarefas]
        for tarefa, marca in zip(tarefas, fims):
            tarefa.add_done_callback(lambda _t, marca=marca: self.fila.put_nowait(marca))
        # Identidade (`is`), nunca hash: um `Evento` é frozen-dataclass com
        # um dict dentro — inhashable — e um `in set` estouraria no
        # primeiro quadro de progresso drenado.
        vistos: list[object] = []
        for chamada, tarefa, marca in zip(chamadas, tarefas, fims):
            # Drena a fila (progresso ao vivo, intercalado) até a marca
            # DESTA task aparecer; marcas de tasks posteriores que chegarem
            # antes ficam lembradas. `fila.get()` nunca é cancelado no meio
            # (mesma razão do sentinela na pista em fila).
            while not any(marca is v for v in vistos):
                enfileirado = await self.fila.get()
                if any(enfileirado is m for m in fims):
                    vistos.append(enfileirado)
                    continue
                yield enfileirado
            resultado, deu_erro = await tarefa
            evento_fim, quadros, bloco = _fecho_da_chamada(
                self.superficie, self.estado, chamada, resultado, deu_erro
            )
            yield evento_fim
            for quadro in quadros:
                yield quadro
            resultados.append(bloco)

    async def _executar_com_vaga(self, vaga: asyncio.Semaphore, chamada: dict[str, Any]) -> tuple[str, bool]:
        async with vaga:
            return await self._executar(chamada)

    def _encerrar(self) -> Evento:
        """O quadro `fim`: o transcrito (com as pendências fechadas), o uso
        somado, as voltas e se a conversa terminou bem."""
        logger.info(
            "Assistente: %d volta(s), %d tokens, US$ %.4f (usuário %s, superfície %s).",
            self.voltas,
            self.uso_total.cobravel,
            self.uso_total.custo,
            self.escopo.user_id,
            self.superficie.nome,
        )
        return Evento(
            "fim",
            {
                "transcrito": _fechar_pendencias(self.conversa),
                "uso": self.uso_total.como_dict(),
                "voltas": self.voltas,
                "ok": not self.falhou,
            },
        )


def _fecho_da_chamada(
    superficie: "Superficie",
    estado: EstadoDoLaco,
    chamada: dict[str, Any],
    resultado: str,
    deu_erro: bool,
) -> tuple[Evento, list[Evento], dict[str, Any]]:
    """O epílogo ÚNICO de uma chamada, compartilhado pelas duas pistas do laço.

    Devolve o evento `ferramenta_fim`, os quadros extras da superfície e o
    bloco `tool_result` que volta ao modelo. Existir uma vez só é o que impede
    o contrato de saída de bifurcar entre a pista em fila e a paralela.
    """
    ident, nome, argumentos = chamada.get("id"), chamada.get("name"), chamada.get("input")
    evento_fim = Evento("ferramenta_fim", {"id": ident, "nome": nome, "erro": deu_erro})
    quadros = list(superficie.quadros_extras(estado, nome, argumentos, resultado, deu_erro))
    bloco = {
        "type": "tool_result",
        "tool_use_id": ident,
        "content": resultado,
        "is_error": deu_erro,
    }
    return evento_fim, quadros, bloco


async def _executar_ferramenta(
    *,
    servidor,
    escopo: EscopoEfetivo,
    nome: str,
    argumentos: Any,
    contexto: ContextoLocal,
    superficie: "Superficie",
    estado: EstadoDoLaco,
    tool_use_id: str | None = None,
) -> tuple[str, bool]:
    """Despacha uma chamada de ferramenta, sob o pacote da superfície.

    Três estágios, e a superfície decide os dois primeiros:
    1. ferramenta LOCAL (desenho no editor, globo na Home) — não vai ao servidor;
    2. o PORTÃO da superfície (ordem+bloqueio no editor; confirmação na Home) —
       quando ele devolve algo, é o resultado, e o servidor nem é tocado;
    3. a chamada de verdade, por `chamar_no_servidor`.

    Argumento malformado não precisa de validação nossa: `Tool.run` valida
    contra o `input_schema` antes de rodar a função e levanta `ToolError`. Vira
    resultado de erro, o modelo lê e corrige — que é o que deve acontecer.

    Os estágios 1 e 2 correm sob a MESMA rede que o estágio 3 já tinha em
    `chamar_no_servidor`: exceção vira resultado de erro, nunca exceção que sobe.
    Sem isso, um defeito no portão ou no executor local derrubava a conversa
    INTEIRA — e pior que a queda era o rastro: o `tool_use` do modelo já fora
    anexado ao transcrito e o `tool_result` nunca chegava, então a próxima
    mensagem batia numa recusa da API (chamada de ferramenta sem resultado).
    Um erro num portão é informação para o modelo corrigir o rumo, do mesmo
    jeito que uma recusa de escopo.
    """
    try:
        executor_local = superficie.executores_locais.get(nome)
        if executor_local is not None:
            return await executor_local(argumentos, estado)

        veredito = await superficie.portao(estado, nome, argumentos, tool_use_id)
    except ToolError as exc:
        return (str(exc), True)
    except Exception as exc:
        logger.exception(
            "Portao da superficie %s quebrou em %s (usuário %s).",
            superficie.nome, nome, escopo.user_id,
        )
        return (f"A ferramenta {nome} falhou de forma inesperada ({exc.__class__.__name__}).", True)

    if veredito is not None:
        return veredito

    if not isinstance(argumentos, dict):
        # O argumento chega em stream; quando o JSON não fecha, o cliente
        # devolve o texto cru em vez de um objeto (`openrouter._argumentos`).
        return ("O argumento não chegou como objeto JSON. Refaça a chamada.", True)

    return await chamar_no_servidor(servidor, escopo, nome, argumentos, contexto)


async def chamar_no_servidor(
    servidor, escopo: EscopoEfetivo, nome: str, argumentos: dict[str, Any], contexto
) -> tuple[str, bool]:
    """Chama a ferramenta pelo caminho do MCP e devolve `(texto, deu_erro)`.

    Público porque a Home o reusa no clique de confirmação: quando a pessoa
    confirma, o servidor é chamado com os argumentos ARMAZENADOS, pelo mesmo
    caminho e sob o mesmo escopo, sem passar de novo pelo laço do modelo.

    O `set`/`reset` do `ContextVar` é estreito de propósito — em volta da chamada
    e não da conversa inteira. Um escopo que sobrevive à chamada é um escopo que
    pode ser lido pela PRÓXIMA tarefa do mesmo worker, e o efeito seria um
    usuário enxergando o workspace de outro. O `finally` aqui é a única coisa
    entre esse defeito e a produção.
    """
    ficha = ESCOPO_ATUAL.set(escopo)
    try:
        resultado = await servidor.call_tool(nome, argumentos, contexto)
    except ToolError as exc:
        # Recusa de escopo, de cota, de papel, ou falha declarada pela própria
        # ferramenta. Tudo isso é informação que o modelo usa para corrigir o
        # rumo — vai como resultado de erro, nunca como exceção que derruba a
        # conversa.
        return (str(exc), True)
    except Exception as exc:
        logger.exception("Ferramenta %s quebrou no assistente (usuário %s).", nome, escopo.user_id)
        return (f"A ferramenta {nome} falhou de forma inesperada ({exc.__class__.__name__}).", True)
    finally:
        ESCOPO_ATUAL.reset(ficha)

    return (_texto_do_resultado(resultado), bool(getattr(resultado, "is_error", False)))


def _fechar_pendencias(conversa: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Responde as chamadas de ferramenta que o laço deixou sem resposta.

    Toda saída anormal do laço — resposta truncada, recusa do modelo, teto de
    voltas, falha de rede — acontece DEPOIS de a mensagem do modelo já ter
    entrado na conversa. Se essa mensagem pedia ferramenta, o transcrito fica
    com um `tool_use` órfão, e uma chamada de ferramenta sem o resultado
    correspondente é recusada pelo provedor na próxima vez que a conversa for
    retomada: a pessoa perderia tudo ao mandar a mensagem seguinte.

    Fechar com um resultado de erro é melhor que descartar a mensagem do modelo,
    por dois motivos: o que ele já escreveu continua na tela, e ele lê na
    retomada por que aquela chamada não aconteceu — em vez de achar que rodou.
    """
    if not conversa:
        return conversa
    ultima = conversa[-1]
    if ultima.get("role") != "assistant":
        return conversa

    pendentes = [
        b
        for b in (ultima.get("content") or [])
        if isinstance(b, dict) and b.get("type") == "tool_use"
    ]
    if not pendentes:
        return conversa

    return conversa + [
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": b["id"],
                    "content": "A chamada não chegou a acontecer: a conversa foi interrompida.",
                    "is_error": True,
                }
                for b in pendentes
            ],
        }
    ]


def _texto_do_resultado(resultado) -> str:
    """O `CallToolResult` do SDK virando o texto que o modelo lê."""
    pedacos: list[str] = []
    for bloco in getattr(resultado, "content", None) or []:
        texto = getattr(bloco, "text", None)
        if texto:
            pedacos.append(texto)
    if not pedacos:
        estruturado = getattr(resultado, "structured_content", None)
        if estruturado is not None:
            pedacos.append(json.dumps(estruturado, ensure_ascii=False, default=str))
    junto = "\n".join(pedacos) if pedacos else "(sem conteúdo)"
    if len(junto) > MAX_CHARS_POR_RESULTADO:
        return junto[:MAX_CHARS_POR_RESULTADO] + AVISO_DE_CORTE
    return junto


# A validação continua no laço — mas como MEIO, não como entrega. Quem põe no
# canvas é `desenhar_no_canvas`; esta constante sobrou para o veredito, que o
# painel mostra ao lado do fluxo desenhado.
NOME_DA_VALIDACAO = "validate_workflow"


def _proposta_de(
    nome: str, argumentos: Any, resultado: str, deu_erro: bool
) -> dict[str, Any] | None:
    """A definição que vai para o canvas. `None` quando não há.

    Nasce de DUAS ferramentas, com papéis diferentes: `desenhar_no_canvas` manda
    desenhar agora (`desenhar: true`), e `validate_workflow` manda o veredito do
    que já está desenhado. Antes só a segunda existia, e por isso pôr algo na
    tela dependia de o modelo ter resolvido validar.

    **Exceção deliberada e estreita ao `_resumo`.** Toda outra chamada vai para o
    SSE com chaves e tamanhos, nunca conteúdo — o stream é log de alguém em algum
    momento. Aqui a definição vai INTEIRA, porque sem ela o botão "Aplicar" não
    tem o que aplicar, e o portão de escrita fez desse botão a única ponte entre
    a conversa e o fluxo. Só desta ferramenta, e só quando ela não falhou.

    A definição sai do ARGUMENTO, e não do resultado: é o que o modelo pediu para
    validar, é o que o servidor validou, e é exatamente o que será aplicado. Ler
    do resultado abriria espaço para os dois divergirem.
    """
    if deu_erro or nome not in (NOME_DO_DESENHO, NOME_DA_VALIDACAO):
        return None
    definicao = argumentos.get("definition") if isinstance(argumentos, dict) else None
    if not isinstance(definicao, dict):
        return None

    proposta: dict[str, Any] = {
        "definicao": definicao,
        "nos": len(definicao.get("nodes") or []),
        "arestas": len(definicao.get("edges") or []),
        # O painel desenha SOZINHO o que vem do desenho, e só mostra o veredito
        # do que vem da validação. Sem esta marca ele não teria como distinguir
        # "põe isto na tela agora" de "eis o que a validação achou".
        "desenhar": nome == NOME_DO_DESENHO,
    }
    if nome == NOME_DO_DESENHO:
        nota = argumentos.get("nota")
        if isinstance(nota, str) and nota.strip():
            proposta["nota"] = nota.strip()[:200]
        return proposta

    proposta.update(_veredito(resultado))
    return proposta


def _veredito(resultado: str) -> dict[str, Any]:
    """`ok`, `erros` e `avisos` do relatório — tolerante ao que não parsear.

    O formato vem de `_resumo_da_validacao` (`app/mcp/tools/construcao.py`). Se um
    dia mudar, o painel perde a contagem e continua funcionando: `None` vira
    "não sei", e o botão fica habilitado pelo que a pessoa vê na explicação. Uma
    exceção aqui derrubaria a conversa inteira por causa de um rótulo.
    """
    try:
        corpo = json.loads(resultado)
    except (TypeError, ValueError):
        return {"ok": None, "erros": None, "avisos": None}
    if not isinstance(corpo, dict):
        return {"ok": None, "erros": None, "avisos": None}
    return {
        "ok": corpo.get("ok"),
        "erros": corpo.get("error_count"),
        "avisos": corpo.get("warning_count"),
    }


def _resumo(argumentos: Any) -> dict[str, Any]:
    """O que o painel mostra da chamada — chaves e tamanhos, nunca o conteúdo.

    Um argumento carrega definição de fluxo e texto de quem está usando. O painel
    quer dizer "está validando um fluxo de 7 nós", não despejar o JSON; e o
    resumo também vai para o SSE, que é log de alguém em algum momento.
    """
    if not isinstance(argumentos, dict):
        return {}
    resumo: dict[str, Any] = {}
    for chave, valor in argumentos.items():
        if isinstance(valor, (str, int, float, bool)) or valor is None:
            texto = str(valor)
            resumo[chave] = texto if len(texto) <= 120 else f"{texto[:117]}…"
        elif isinstance(valor, dict):
            resumo[chave] = {"__campos__": len(valor)}
        elif isinstance(valor, (list, tuple)):
            resumo[chave] = {"__itens__": len(valor)}
        else:
            resumo[chave] = {"__tipo__": type(valor).__name__}
    return resumo


# ── O transcrito, no Redis ────────────────────────────────────────────────────
# Chave por (usuário, fluxo): reabrir o editor retoma a conversa daquele fluxo,
# que é o que a pessoa espera de um painel que vive ao lado do canvas. A tela de
# criar usa `novo`.
#
# Nunca no navegador — ver a nota 2 do topo deste módulo. Um cliente que guarda o
# transcrito pode reescrever um `tool_result`, e um `tool_result` é a palavra do
# SERVIDOR sobre o que aconteceu.

TTL_DA_CONVERSA_S = 24 * 60 * 60
FLUXO_NOVO = "novo"

# Curta de propósito: ela protege contra duas abas no mesmo fluxo, não contra um
# worker que morreu. Uma conversa abandonada solta sozinha em minutos, em vez de
# deixar o fluxo travado até alguém perceber.
TTL_DA_TRAVA_S = 300


def chave_da_conversa(user_id: str, workflow_id: str | None) -> str:
    return f"assistente:conversa:{user_id}:{workflow_id or FLUXO_NOVO}"


def chave_da_trava(user_id: str, workflow_id: str | None) -> str:
    return f"assistente:trava:{user_id}:{workflow_id or FLUXO_NOVO}"


async def carregar_conversa(redis, user_id: str, workflow_id: str | None) -> list[dict[str, Any]]:
    """O histórico daquele fluxo, ou vazio. Nunca levanta.

    Sem Redis a conversa não tem memória: cada mensagem começa do zero. É pior
    que o normal e melhor que recusar — a mesma política de degradação do módulo
    de cotas.
    """
    if redis is None:
        return []
    try:
        cru = await redis.get(chave_da_conversa(user_id, workflow_id))
    except Exception as exc:  # pragma: no cover - depende do Redis
        logger.warning("Falha ao ler a conversa: %s", exc.__class__.__name__)
        return []
    if not cru:
        return []
    try:
        carregado = json.loads(cru)
    except (TypeError, ValueError):
        # Valor corrompido ou de um formato anterior: recomeçar limpo é melhor
        # que derrubar a conversa de alguém para sempre.
        logger.warning("Conversa ilegível para %s; recomeçando.", user_id)
        return []
    return carregado if isinstance(carregado, list) else []


async def salvar_conversa(
    redis, user_id: str, workflow_id: str | None, transcrito: list[dict[str, Any]]
) -> None:
    """Guarda o histórico. Nunca levanta — falhar aqui não pode perder a resposta."""
    if redis is None or not transcrito:
        return
    try:
        await redis.set(
            chave_da_conversa(user_id, workflow_id),
            json.dumps(transcrito, ensure_ascii=False),
            ex=TTL_DA_CONVERSA_S,
        )
    except Exception as exc:  # pragma: no cover - depende do Redis
        logger.warning("Falha ao salvar a conversa: %s", exc.__class__.__name__)


async def esquecer_conversa(redis, user_id: str, workflow_id: str | None) -> None:
    """Recomeça do zero. Usado pelo botão de limpar do painel."""
    if redis is None:
        return
    try:
        await redis.delete(chave_da_conversa(user_id, workflow_id))
    except Exception as exc:  # pragma: no cover - depende do Redis
        logger.warning("Falha ao esquecer a conversa: %s", exc.__class__.__name__)


# Renova em TTL/3: margem de sobra para uma renovacao falhar e a proxima ainda
# pegar antes do vencimento.
_INTERVALO_DE_RENOVACAO_DA_TRAVA_S = TTL_DA_TRAVA_S / 3


async def _renovar_trava(redis, chave: str) -> None:
    """Reemite o EXPIRE da trava enquanto a secao corre.

    A trava vence em `TTL_DA_TRAVA_S` (300 s), mas um turno pode passar disso —
    `TETO_DE_VOLTAS` voltas de modelo em `high` levam minutos. Sem renovar, a
    trava venceria no meio e uma 2a aba entraria no MESMO transcrito, salvando
    por cima. Roda ate ser cancelado no fim da secao; como vive no event loop do
    worker, morre com ele — uma trava ABANDONADA (worker que caiu) ainda expira
    sozinha pelo TTL, que e o ponto de a trava ser curta de proposito."""
    while True:
        await asyncio.sleep(_INTERVALO_DE_RENOVACAO_DA_TRAVA_S)
        try:
            await redis.expire(chave, TTL_DA_TRAVA_S)
        except Exception as exc:  # pragma: no cover - depende do Redis
            logger.warning("Falha ao renovar a trava: %s", exc.__class__.__name__)
            return


@asynccontextmanager
async def trava_exclusiva(redis, chave: str) -> AsyncIterator[None]:
    """Uma seção por vez, por chave — e solta sempre. `SET NX` é a trava mais
    barata que resolve.

    Genérica de propósito: o editor tranca por (usuário, fluxo) e o assistente da
    Home por (usuário, conversa), mas a mecânica é a mesma — duas abas na mesma
    conversa escreveriam no mesmo transcrito e o embaralhariam, a segunda salvando
    por cima da primeira.

    Sem Redis não há trava — mesma degradação do resto. O estrago possível é um
    transcrito embaralhado, não um vazamento.
    """
    if redis is None:
        yield
        return
    try:
        peguei = await redis.set(chave, "1", nx=True, ex=TTL_DA_TRAVA_S)
    except Exception as exc:  # pragma: no cover - depende do Redis
        logger.warning("Falha ao travar a conversa: %s", exc.__class__.__name__)
        yield
        return
    if not peguei:
        raise erro(
            "conversa_em_andamento",
            "Já há uma conversa em andamento para este fluxo.",
            "espere a resposta terminar, ou recarregue a aba que ficou aberta",
        )
    # Mantem a trava viva enquanto o turno corre — sem renovar, ela venceria no
    # meio de uma conversa longa e uma 2a aba entraria no mesmo transcrito.
    renovador = asyncio.create_task(_renovar_trava(redis, chave))
    try:
        yield
    finally:
        renovador.cancel()
        with suppress(asyncio.CancelledError):
            await renovador
        try:
            await redis.delete(chave)
        except Exception as exc:  # pragma: no cover - depende do Redis
            logger.warning("Falha ao soltar a trava: %s", exc.__class__.__name__)


def conversa_exclusiva(redis, user_id: str, workflow_id: str | None):
    """A trava do editor, pela chave de hoje. Alias fino de `trava_exclusiva`."""
    return trava_exclusiva(redis, chave_da_trava(user_id, workflow_id))


__all__ = [
    "ContextoLocal",
    "EDITOR",
    "ESCREVEM_MAS_PASSAM",
    "ESFORCO_DO_RACIOCINIO",
    "EXIGEM_DESENHO_ANTES",
    "EstadoDoLaco",
    "FERRAMENTA_DO_DESENHO",
    "NOME_DO_DESENHO",
    "MENSAGEM_DE_EXECUTAR_ANTES",
    "Evento",
    "INSTRUCOES_DO_EDITOR",
    "MENSAGEM_DO_PORTAO",
    "Superficie",
    "Uso",
    "bloqueada_no_editor",
    "carregar_conversa",
    "chamar_no_servidor",
    "conversa_exclusiva",
    "conversar",
    "criar_cliente",
    "escopo_do_editor_para",
    "ferramentas_para_o_modelo",
    "esquecer_conversa",
    "montar_sistema",
    "salvar_conversa",
    "trava_exclusiva",
    "TETO_DE_VOLTAS",
]
