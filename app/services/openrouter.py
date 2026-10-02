# app/services/openrouter.py
"""
O cliente do OpenRouter — o ÚNICO módulo que conhece o formato de rede do modelo.

O assistente (`assistente_service.conversar`) fala com o modelo por uma fronteira só:
`ClienteOpenRouter.transmitir(...)`. Ela recebe o transcrito no formato do
projeto e devolve, em stream, os pedaços de texto e de raciocínio (`Delta`) e,
por último, a resposta inteira (`Resposta`) — também no formato do projeto.
Nada fora daqui sabe o que é um `chat.completion.chunk`, um `tool_calls` ou um
`reasoning_details`. Trocar de provedor de novo é reescrever ESTE módulo, e
mais nada: o laço, a cota, o portão de escrita, o replay e a confirmação por
clique não mudam.

**Por que a API nativa do OpenRouter (chat completions) e não uma camada de
compatibilidade.** O OpenRouter é um roteador: o mesmo pedido serve um modelo
da Anthropic, da OpenAI, do Google ou um aberto, e o operador troca de modelo
editando `ASSISTENTE_MODELO`. A API nativa é a que ele documenta, mede e mantém
para todos eles; uma camada de compatibilidade com o formato de outro
fornecedor é um subconjunto que envelhece por fora. O preço é este módulo:
~400 linhas que traduzem o transcrito e remontam o stream.

**O formato do transcrito é do PROJETO, não do provedor.** Ele é o que o
Redis (editor) e o Postgres (Home) guardam, o que o replay lê e o que a
confirmação por clique casa pelo `tool_use_id`:

    {"role": "user", "content": "o que a pessoa escreveu"}
    {"role": "assistant", "content": [
        {"type": "thinking", "thinking": "...", "reasoning_details": [...]},
        {"type": "text", "text": "..."},
        {"type": "tool_use", "id": "call_…", "name": "search_nodes", "input": {...}},
    ]}
    {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "call_…", "content": "...", "is_error": false},
    ]}

Na ida, `montar_mensagens` traduz isso para `system`/`user`/`assistant`
(`tool_calls`)/`tool`; na volta, o acumulador remonta os `chunks` do SSE nos
três blocos acima. O `reasoning_details` viaja VERBATIM nos dois sentidos: é o
que o OpenRouter pede para o modelo continuar o raciocínio de uma volta de
ferramenta para a seguinte (e, nos modelos da Anthropic, é obrigatório na
última mensagem do assistente quando ela pede ferramenta). Um bloco `thinking`
antigo — do tempo em que o transcrito vinha de outra API e carregava uma
`signature` — não tem `reasoning_details` e é simplesmente omitido na ida: o
que já foi pensado em turnos passados não é necessário, e reenviá-lo num
formato que o provedor não reconhece derrubaria a conversa inteira.

**O que o cliente garante ao laço:**

- `Delta("texto")`/`Delta("pensando")` saem na ordem em que chegam, e a
  `Resposta` é sempre o último item — ou uma exceção `ErroDoOpenRouter`, nunca
  uma resposta pela metade. Um stream que morre no meio é exceção, não sucesso
  truncado: o laço não grava o que não chegou inteiro.
- `Resposta.parada` é o `finish_reason` normalizado pelo OpenRouter: `stop`,
  `tool_calls`, `length` (cortada por `max_tokens`) ou `content_filter`
  (recusa). `error` vira exceção.
- Falha de rede, 429 e 5xx ANTES do corpo começar são retentados
  (`TENTATIVAS`); um 400 com `reasoning_details` no pedido é retentado UMA vez
  sem eles — se o provedor recusar o raciocínio guardado, a conversa perde o
  raciocínio antigo, não a conversa.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable
from urllib.parse import urlsplit
from uuid import uuid4

import httpx

from app.core.utils.logger import get_logger

logger = get_logger("app.assistente.openrouter")

URL_PADRAO = "https://openrouter.ai/api/v1"
CAMINHO = "/chat/completions"

# Tentativas de ABRIR a conversa (até os cabeçalhos da resposta). Depois que o
# corpo começou a chegar não há retentativa: o que já saiu no SSE não pode ser
# desdito, e o laço trata a queda como `modelo_indisponivel`.
TENTATIVAS = 3
RETENTAVEIS = frozenset({408, 429, 500, 502, 503, 504})
ESPERA_MAXIMA_S = 10.0

# Streaming com `max_tokens` grande leva minutos; o que vale é o silêncio ENTRE
# dois pedaços (`read`), e o OpenRouter manda comentários `: OPENROUTER PROCESSING`
# enquanto o provedor ainda não começou a responder.
TEMPO_LIMITE = httpx.Timeout(connect=30.0, read=180.0, write=60.0, pool=30.0)

# O que o modelo lê num resultado de ferramenta que falhou. O formato de rede
# não tem a bandeira `is_error`; sem o prefixo, uma recusa de escopo e um
# resultado normal chegariam iguais.
PREFIXO_DE_ERRO = "[erro] "


@dataclass(frozen=True)
class Delta:
    """Um pedaço do stream: `texto` (o que o modelo escreve) ou `pensando` (o raciocínio)."""

    tipo: str
    texto: str


@dataclass(frozen=True)
class Resposta:
    """A resposta inteira, remontada, no formato do projeto."""

    blocos: list[dict[str, Any]]
    parada: str
    uso: dict[str, Any] = field(default_factory=dict)
    modelo: str | None = None
    provedor: str | None = None


class ErroDoOpenRouter(Exception):
    """Falha ao falar com o OpenRouter. A mensagem é para o LOG; o laço mostra à
    pessoa só a classe — o texto do provedor pode carregar URL e cabeçalho."""

    def __init__(self, mensagem: str, *, status: int | None = None, codigo: Any = None) -> None:
        super().__init__(mensagem)
        self.status = status
        self.codigo = codigo


# ── A ida: do transcrito ao pedido ───────────────────────────────────────────


def e_openrouter(base_url: str | None) -> bool:
    """A base é a do OpenRouter?

    `usage`, `reasoning` e `cache_control` são parâmetros DELE. Uma API que só
    segue a da OpenAI pode recusar campo desconhecido (a própria OpenAI
    recusa), e não manda o `usage` no stream sem `stream_options`: a cota de
    tokens não contaria nada. Para essas, o pedido leva só o formato padrão.
    """
    host = (urlsplit(base_url or URL_PADRAO).hostname or "").lower()
    return host == "openrouter.ai" or host.endswith(".openrouter.ai")


def ferramenta(nome: str, descricao: str | None, parametros: dict[str, Any] | None) -> dict[str, Any]:
    """Uma ferramenta no formato de rede (`function`), a partir do `input_schema` do MCP."""
    return {
        "type": "function",
        "function": {
            "name": nome,
            "description": descricao or "",
            "parameters": parametros or {"type": "object", "properties": {}},
        },
    }


def montar_pedido(
    *,
    modelo: str,
    sistema: list[dict[str, Any]],
    conversa: list[dict[str, Any]],
    ferramentas: list[dict[str, Any]],
    max_tokens: int,
    esforco: str | None,
    openrouter: bool = True,
) -> dict[str, Any]:
    """O corpo do POST /chat/completions. Puro: é o que os testes conferem.

    `openrouter=False` (ver `e_openrouter`) tira os parâmetros próprios do
    OpenRouter e pede o `usage` do jeito da API da OpenAI.
    """
    corpo: dict[str, Any] = {
        "model": modelo,
        "messages": montar_mensagens(sistema, conversa, cache=openrouter),
        "max_tokens": max_tokens,
        "stream": True,
    }
    if openrouter:
        # `usage.include` põe a contagem (e o custo em créditos) no último
        # quadro do stream. É a fonte da cota.
        corpo["usage"] = {"include": True}
    else:
        # O mesmo último quadro com o `usage`, no formato da API da OpenAI
        # (e do vLLM, do LiteLLM, do Ollama). Sem ele, a cota não conta nada.
        corpo["stream_options"] = {"include_usage": True}
    if ferramentas:
        corpo["tools"] = list(ferramentas)
    if esforco and openrouter:
        # O raciocínio do modelo, no parâmetro unificado do OpenRouter: ele o
        # traduz para o que cada família aceita (pensamento adaptativo, esforço,
        # orçamento). Modelo sem raciocínio ignora.
        corpo["reasoning"] = {"effort": esforco}
    return corpo


def montar_mensagens(
    sistema: list[dict[str, Any]], conversa: list[dict[str, Any]], *, cache: bool = True,
) -> list[dict[str, Any]]:
    """O transcrito do projeto virando `messages`.

    `cache=False` (fora do OpenRouter) não marca ponto de corte nenhum, e o
    `system` vai como texto simples, que toda API compatível aceita.

    O `system` vai como lista de partes de texto para os pontos de corte de
    cache (`cache_control`) sobreviverem — é assim que o OpenRouter repassa o
    cache de prompt aos provedores que o têm; os outros ignoram o campo.

    O segundo ponto de corte vai na ÚLTIMA mensagem humana (o texto da pessoa,
    ou a sintética de confirmação da Home). Ele fecha um prefixo que é o mesmo
    em TODAS as voltas de ferramenta deste turno: sistema, ferramentas, o
    histórico e a pergunta. O que fica fora são só as chamadas e resultados do
    turno atual.
    """
    mensagens: list[dict[str, Any]] = []
    if sistema and cache:
        mensagens.append({"role": "system", "content": [_parte_de_texto(b) for b in sistema]})
    elif sistema:
        mensagens.append({
            "role": "system",
            "content": "\n\n".join(str(b.get("text") or "") for b in sistema),
        })

    ultima_humana = _indice_da_ultima_mensagem_humana(conversa) if cache else None
    for indice, mensagem in enumerate(conversa):
        papel = mensagem.get("role")
        conteudo = mensagem.get("content")
        if papel == "assistant":
            traduzida = _do_assistente(conteudo)
            if traduzida is not None:
                mensagens.append(traduzida)
        elif papel == "user":
            mensagens.extend(_da_pessoa(conteudo, marcar_cache=(indice == ultima_humana)))
        else:
            logger.warning("Mensagem de papel desconhecido no transcrito (%r); ignorada.", papel)
    return mensagens


def _parte_de_texto(bloco: dict[str, Any]) -> dict[str, Any]:
    parte: dict[str, Any] = {"type": "text", "text": str(bloco.get("text") or "")}
    if bloco.get("cache_control"):
        # Só o tipo: o TTL é decisão do provedor por trás do roteador, e um campo
        # que ele não conhece é risco de recusa a cada conversa.
        parte["cache_control"] = {"type": "ephemeral"}
    return parte


def _e_humana(mensagem: dict[str, Any]) -> bool:
    """Texto de gente (ou a sintética do servidor) — não uma lista de `tool_result`."""
    if mensagem.get("role") != "user":
        return False
    conteudo = mensagem.get("content")
    if isinstance(conteudo, str):
        return True
    return isinstance(conteudo, list) and any(
        isinstance(b, dict) and b.get("type") == "text" for b in conteudo
    )


def _indice_da_ultima_mensagem_humana(conversa: list[dict[str, Any]]) -> int | None:
    for indice in range(len(conversa) - 1, -1, -1):
        if _e_humana(conversa[indice]):
            return indice
    return None


def _da_pessoa(conteudo: Any, *, marcar_cache: bool) -> list[dict[str, Any]]:
    """Uma mensagem `user` do transcrito: texto da pessoa, ou resultados de ferramenta."""
    if isinstance(conteudo, str):
        return [_mensagem_humana(conteudo, marcar_cache)]
    if not isinstance(conteudo, list):
        return [_mensagem_humana(str(conteudo or ""), marcar_cache)]

    saida: list[dict[str, Any]] = []
    textos: list[str] = []
    for bloco in conteudo:
        if not isinstance(bloco, dict):
            continue
        if bloco.get("type") == "tool_result":
            saida.append(
                {
                    "role": "tool",
                    "tool_call_id": str(bloco.get("tool_use_id") or ""),
                    "content": _texto_do_resultado(bloco),
                }
            )
        elif bloco.get("type") == "text" and bloco.get("text"):
            textos.append(str(bloco["text"]))
    if textos:
        saida.append(_mensagem_humana("\n".join(textos), marcar_cache))
    return saida


def _mensagem_humana(texto: str, marcar_cache: bool) -> dict[str, Any]:
    if not marcar_cache:
        return {"role": "user", "content": texto}
    return {
        "role": "user",
        "content": [{"type": "text", "text": texto, "cache_control": {"type": "ephemeral"}}],
    }


def _texto_do_resultado(bloco: dict[str, Any]) -> str:
    conteudo = bloco.get("content")
    if isinstance(conteudo, list):
        texto = "\n".join(
            str(b.get("text")) for b in conteudo if isinstance(b, dict) and b.get("text")
        )
    elif conteudo is None:
        texto = ""
    else:
        texto = str(conteudo)
    if bloco.get("is_error"):
        return PREFIXO_DE_ERRO + texto
    return texto


def _do_assistente(conteudo: Any) -> dict[str, Any] | None:
    """Uma mensagem do modelo: texto + `tool_calls` + `reasoning_details` verbatim.

    `None` quando ela não tem texto nem chamada — só raciocínio, ou nada (um
    corte por `length` ainda pensando; uma recusa sem saída). Mandá-la como
    `content: ""` é recusa certa do provedor, e recusa que o plano B do 400 não
    conserta: a conversa ficaria presa para sempre. O que já foi pensado em
    turnos passados não é necessário, e a omissão não muda nada para o modelo.
    """
    if isinstance(conteudo, str):
        return {"role": "assistant", "content": conteudo} if conteudo.strip() else None

    textos: list[str] = []
    chamadas: list[dict[str, Any]] = []
    detalhes: list[dict[str, Any]] = []
    for bloco in conteudo if isinstance(conteudo, list) else []:
        if not isinstance(bloco, dict):
            continue
        tipo = bloco.get("type")
        if tipo == "text" and bloco.get("text"):
            textos.append(str(bloco["text"]))
        elif tipo == "tool_use":
            chamadas.append(
                {
                    "id": str(bloco.get("id") or ""),
                    "type": "function",
                    "function": {
                        "name": str(bloco.get("name") or ""),
                        "arguments": _argumentos_como_texto(bloco.get("input")),
                    },
                }
            )
        elif tipo == "thinking":
            # Só o que veio do OpenRouter. Um bloco antigo (com `signature` e sem
            # `reasoning_details`) fica no transcrito para o replay e não vai.
            guardados = bloco.get("reasoning_details")
            if isinstance(guardados, list):
                detalhes.extend(d for d in guardados if isinstance(d, dict))

    texto = "".join(textos)
    if not texto.strip() and not chamadas:
        return None
    mensagem: dict[str, Any] = {"role": "assistant", "content": texto if texto else None}
    if chamadas:
        mensagem["tool_calls"] = chamadas
    if detalhes:
        mensagem["reasoning_details"] = detalhes
    return mensagem


def _argumentos_como_texto(argumentos: Any) -> str:
    """O `input` de um `tool_use` como a string JSON de `function.arguments`.

    Só um OBJETO vai como está. O texto cru de uma chamada cortada por
    `max_tokens` (o que `_argumentos` devolve quando o JSON não fecha) fica no
    transcrito para o replay, mas na ida vira `{}`: reenviado como veio, seria
    JSON inválido em toda volta seguinte, e o provedor recusaria a conversa
    inteira. O `tool_result` de erro emparelhado já disse ao modelo que aquela
    chamada não aconteceu.
    """
    if isinstance(argumentos, dict):
        return json.dumps(argumentos, ensure_ascii=False, default=str)
    return "{}"


def _tem_raciocinio(corpo: dict[str, Any]) -> bool:
    return any(
        m.get("role") == "assistant" and m.get("reasoning_details")
        for m in corpo.get("messages") or []
    )


def _sem_raciocinio(corpo: dict[str, Any]) -> dict[str, Any]:
    """O mesmo pedido sem os `reasoning_details` — o plano B do 400."""
    mensagens = [
        {k: v for k, v in m.items() if k != "reasoning_details"} for m in corpo.get("messages") or []
    ]
    return {**corpo, "messages": mensagens}


# ── A volta: do SSE à resposta ───────────────────────────────────────────────


async def _linhas(resposta: httpx.Response) -> AsyncIterator[str]:
    """As linhas do corpo, quebradas SÓ em `\\n`, `\\r\\n` e `\\r` — os três
    terminadores que a especificação do SSE define.

    `aiter_lines()` do httpx não serve: ele quebra como `str.splitlines()`, o
    que inclui U+2028, U+2029 e U+0085 — caracteres válidos SEM escape dentro
    de uma string JSON. Um modelo que os emitisse (ecoando um nome de fluxo,
    um texto vindo da web) teria o quadro cortado no meio, e o turno inteiro
    morreria em `quadro ilegível`. Quebrar nos bytes é seguro: em UTF-8 os
    bytes 0x0A e 0x0D nunca aparecem dentro de um caractere multibyte.
    """
    resto = b""
    async for pedaco in resposta.aiter_bytes():
        resto += pedaco
        while resto:
            i_n = resto.find(b"\n")
            i_r = resto.find(b"\r")
            if i_n < 0 and i_r < 0:
                break
            fim = min(i for i in (i_n, i_r) if i >= 0)
            if resto[fim : fim + 1] == b"\r":
                if fim + 1 >= len(resto):
                    # Pode ser um `\r\n` partido entre dois pedaços: espera o próximo.
                    break
                salto = 2 if resto[fim + 1 : fim + 2] == b"\n" else 1
            else:
                salto = 1
            yield resto[:fim].decode("utf-8", "replace")
            resto = resto[fim + salto :]
    if resto:
        if resto.endswith(b"\r"):
            resto = resto[:-1]
        yield resto.decode("utf-8", "replace")


async def _eventos_sse(resposta: httpx.Response) -> AsyncIterator[dict[str, Any]]:
    """Os quadros `data:` do stream, já decodificados. Para no `[DONE]`.

    Linhas que começam com `:` são comentários — o OpenRouter manda
    `: OPENROUTER PROCESSING` como sinal de vida enquanto espera o provedor.
    Um evento pode ter várias linhas `data:` (juntam-se com `\\n`, como manda a
    especificação) e termina numa linha em branco.
    """
    dados: list[str] = []
    async for linha in _linhas(resposta):
        if linha == "":
            if dados:
                carga = "\n".join(dados)
                dados = []
                if carga.strip() == "[DONE]":
                    return
                yield _decodificar(carga)
            continue
        if linha.startswith(":"):
            continue
        campo, _, valor = linha.partition(":")
        if valor.startswith(" "):
            valor = valor[1:]
        if campo == "data":
            dados.append(valor)
    if dados:
        carga = "\n".join(dados)
        if carga.strip() != "[DONE]":
            yield _decodificar(carga)


def _decodificar(carga: str) -> dict[str, Any]:
    try:
        evento = json.loads(carga)
    except ValueError as exc:
        raise ErroDoOpenRouter("quadro ilegível no stream do OpenRouter") from exc
    if not isinstance(evento, dict):
        raise ErroDoOpenRouter("quadro inesperado no stream do OpenRouter")
    return evento


def _texto_de(valor: Any) -> str:
    """`content`/`reasoning` de um delta: string, ou lista de partes de texto."""
    if isinstance(valor, str):
        return valor
    if isinstance(valor, list):
        return "".join(
            str(p.get("text")) for p in valor if isinstance(p, dict) and isinstance(p.get("text"), str)
        )
    return ""


def _inteiro(valor: Any) -> int:
    try:
        return int(valor or 0)
    except (TypeError, ValueError):
        return 0


def _uso_do_projeto(cru: Any) -> dict[str, Any]:
    """O `usage` do OpenRouter nas chaves do projeto.

    `prompt_tokens` já INCLUI o que veio do cache — `cached_tokens` é um recorte
    dele, informativo. Por isso a cota soma só entrada + saída (ver `Uso` no
    laço). `cost` vem em créditos (dólares) quando `usage.include` está ligado.
    """
    cru = cru if isinstance(cru, dict) else {}
    entrada = cru.get("prompt_tokens_details") or {}
    saida = cru.get("completion_tokens_details") or {}
    try:
        custo = float(cru.get("cost") or 0.0)
    except (TypeError, ValueError):
        custo = 0.0
    return {
        "entrada": _inteiro(cru.get("prompt_tokens")),
        "saida": _inteiro(cru.get("completion_tokens")),
        "cache_leitura": _inteiro(entrada.get("cached_tokens")),
        "cache_escrita": _inteiro(entrada.get("cache_write_tokens") or entrada.get("cache_creation_tokens")),
        "raciocinio": _inteiro(saida.get("reasoning_tokens")),
        "custo": custo,
    }


_avisou_sem_uso = False


def _avisar_sem_uso() -> None:
    """Uma vez por processo: a resposta chegou sem `usage`.

    Sem a contagem, a cota diária do assistente não cobra o turno — o teto
    deixa de valer em silêncio. Acontece com um servidor que ignora o
    `stream_options.include_usage` (versões antigas de alguns servidores
    locais). Uma vez basta: repetir a cada turno afogaria o log.
    """
    global _avisou_sem_uso
    if _avisou_sem_uso:
        return
    _avisou_sem_uso = True
    logger.warning(
        "O provedor do modelo não informou o uso (usage) da resposta: a cota de "
        "tokens do assistente não conta estes turnos. Confira se o servidor aceita "
        "stream_options.include_usage."
    )


class _Acumulador:
    """Remonta os `chunks` de UMA resposta. Cada chamada a `absorver` devolve os
    deltas visíveis daquele quadro; `resposta()` fecha a conta.

    Chamadas de ferramenta chegam por `index`: o `id` e o `name` no primeiro
    pedaço, os `arguments` gota a gota. `reasoning_details` chega do mesmo jeito
    — um item por pedaço, com o `index` do bloco a que pertence e o texto
    parcial; a `signature` (quando o modelo tem) vem no último. Juntar por
    índice reconstrói o que o provedor gerou, e é isso que volta na próxima
    volta.
    """

    def __init__(self) -> None:
        self.texto: list[str] = []
        self.raciocinio: list[str] = []
        self.chamadas: dict[int, dict[str, Any]] = {}
        self.detalhes: dict[tuple[str, Any], dict[str, Any]] = {}
        self.parada: str | None = None
        self.uso: Any = None
        self.modelo: str | None = None
        self.provedor: str | None = None

    def absorver(self, evento: dict[str, Any]) -> list[Delta]:
        erro = evento.get("error")
        if erro:
            mensagem = erro.get("message") if isinstance(erro, dict) else str(erro)
            codigo = erro.get("code") if isinstance(erro, dict) else None
            raise ErroDoOpenRouter(
                f"o provedor devolveu erro no meio do stream: {str(mensagem)[:300]}", codigo=codigo
            )
        if evento.get("usage"):
            self.uso = evento["usage"]
        self.modelo = evento.get("model") or self.modelo
        self.provedor = evento.get("provider") or self.provedor

        deltas: list[Delta] = []
        for escolha in evento.get("choices") or []:
            if not isinstance(escolha, dict):
                continue
            delta = escolha.get("delta") or escolha.get("message") or {}
            conteudo = _texto_de(delta.get("content"))
            if conteudo:
                self.texto.append(conteudo)
                deltas.append(Delta("texto", conteudo))
            pensamento = _texto_de(delta.get("reasoning"))
            if pensamento:
                self.raciocinio.append(pensamento)
                deltas.append(Delta("pensando", pensamento))
            for item in delta.get("reasoning_details") or []:
                self._absorver_detalhe(item)
            for chamada in delta.get("tool_calls") or []:
                self._absorver_chamada(chamada)
            parada = escolha.get("finish_reason")
            if parada:
                self.parada = str(parada)
        return deltas

    def _absorver_chamada(self, chamada: Any) -> None:
        if not isinstance(chamada, dict):
            return
        indice = chamada.get("index")
        if not isinstance(indice, int):
            # Sem índice: um `id` novo abre outra chamada; sem `id`, é a última.
            if chamada.get("id") or not self.chamadas:
                indice = len(self.chamadas)
            else:
                indice = max(self.chamadas)
        atual = self.chamadas.setdefault(indice, {"id": None, "name": None, "argumentos": []})
        if chamada.get("id") and not atual["id"]:
            atual["id"] = str(chamada["id"])
        funcao = chamada.get("function") or {}
        if funcao.get("name") and not atual["name"]:
            atual["name"] = str(funcao["name"])
        argumentos = funcao.get("arguments")
        if isinstance(argumentos, str):
            atual["argumentos"].append(argumentos)
        elif isinstance(argumentos, (dict, list)):
            atual["argumentos"].append(json.dumps(argumentos, ensure_ascii=False))

    def _absorver_detalhe(self, item: Any) -> None:
        if not isinstance(item, dict):
            return
        tipo = str(item.get("type") or "reasoning.text")
        indice = item.get("index")
        if isinstance(indice, int):
            chave: tuple[str, Any] = (tipo, indice)
        elif item.get("id"):
            # Sem índice mas com `id` (o raciocínio criptografado de alguns
            # provedores): itens distintos, nunca fundidos num só.
            chave = (tipo, f"id:{item['id']}")
        else:
            # Sem índice e sem `id`: pedaços do mesmo bloco.
            chave = (tipo, None)
        atual = self.detalhes.get(chave)
        if atual is None:
            atual = {k: v for k, v in item.items() if k not in ("text", "summary", "data")}
            atual["type"] = tipo
            self.detalhes[chave] = atual
        for campo in ("text", "summary", "data"):
            pedaco = item.get(campo)
            if isinstance(pedaco, str):
                atual[campo] = (atual.get(campo) or "") + pedaco
        for campo in ("signature", "id", "format"):
            if item.get(campo):
                atual[campo] = item[campo]

    def resposta(self) -> Resposta:
        detalhes = list(self.detalhes.values())
        raciocinio = "".join(self.raciocinio) or "".join(
            str(d.get("text") or d.get("summary") or "") for d in detalhes
        )
        blocos: list[dict[str, Any]] = []
        if raciocinio or detalhes:
            bloco: dict[str, Any] = {"type": "thinking", "thinking": raciocinio}
            if detalhes:
                bloco["reasoning_details"] = detalhes
            blocos.append(bloco)
        texto = "".join(self.texto)
        if texto:
            blocos.append({"type": "text", "text": texto})
        for indice in sorted(self.chamadas):
            chamada = self.chamadas[indice]
            blocos.append(
                {
                    "type": "tool_use",
                    "id": chamada["id"] or f"call_{uuid4().hex[:16]}",
                    "name": chamada["name"] or "",
                    "input": _argumentos(chamada["argumentos"]),
                }
            )

        # O OpenRouter sempre manda um `finish_reason` antes do `[DONE]`. Sem
        # ele, o que chegou não é uma resposta: é um 200 de gateway com HTML,
        # ou um stream que fechou antes do último quadro. Inferir "stop" aqui
        # gravaria uma mensagem vazia do assistente e emitiria um `fim` ok —
        # exatamente a resposta pela metade que este módulo promete não dar.
        if self.parada is None:
            raise ErroDoOpenRouter("o stream terminou sem finish_reason")
        parada = self.parada
        if parada == "error":
            raise ErroDoOpenRouter("o provedor encerrou o stream com erro")
        if not self.uso:
            _avisar_sem_uso()
        return Resposta(
            blocos=blocos,
            parada=parada,
            uso=_uso_do_projeto(self.uso),
            modelo=self.modelo,
            provedor=self.provedor,
        )


def _argumentos(pedacos: list[str]) -> Any:
    """O argumento da chamada: um objeto quando o JSON fecha; senão, o texto cru.

    O texto cru NÃO é um objeto, e o laço trata isso como erro de chamada — o
    modelo lê "refaça" em vez de a ferramenta receber metade de uma definição.
    """
    texto = "".join(pedacos).strip()
    if not texto:
        return {}
    try:
        return json.loads(texto)
    except ValueError:
        return texto


# ── O cliente ────────────────────────────────────────────────────────────────


def _espera(tentativa: int, retry_after: str | None = None) -> float:
    if retry_after:
        try:
            return min(max(float(retry_after), 0.0), ESPERA_MAXIMA_S)
        except ValueError:
            pass
    return min(0.5 * (2 ** (tentativa - 1)), ESPERA_MAXIMA_S)


async def _ler_erro(resposta: httpx.Response) -> tuple[Any, str]:
    """`(code, message)` do envelope de erro do OpenRouter, ou o corpo cru encurtado."""
    try:
        bruto = await resposta.aread()
    finally:
        await resposta.aclose()
    try:
        corpo = json.loads(bruto)
    except ValueError:
        return None, bruto[:300].decode("utf-8", "replace")
    erro = corpo.get("error") if isinstance(corpo, dict) else None
    if isinstance(erro, dict):
        return erro.get("code"), str(erro.get("message") or "")[:300]
    return None, str(corpo)[:300]


# O pool de conexões do processo, criado na primeira conversa e reaproveitado
# por todas. Abrir um `AsyncClient` por chamada custava um handshake TCP+TLS
# com o openrouter.ai a cada volta de ferramenta — de seis a doze por conversa.
# A API roda num único event loop por worker, então um pool por processo é
# seguro; os testes injetam o próprio `http` e nunca chegam aqui.
_http_compartilhado: httpx.AsyncClient | None = None


def _http_padrao() -> httpx.AsyncClient:
    global _http_compartilhado
    if _http_compartilhado is None or _http_compartilhado.is_closed:
        _http_compartilhado = httpx.AsyncClient(timeout=TEMPO_LIMITE)
    return _http_compartilhado


CAMINHO_DOS_MODELOS = "/models"

# O catálogo é grande e muda devagar. Este limite existe para o pedido não ficar
# pendurado numa tela de admin: ele não é caminho de conversa, e falhar rápido
# ali é melhor que um spinner de três minutos.
TEMPO_LIMITE_DO_CATALOGO = httpx.Timeout(connect=10.0, read=20.0, write=10.0, pool=10.0)


async def listar_modelos(
    *, base_url: str = URL_PADRAO, chave: str | None = None, http: httpx.AsyncClient | None = None,
) -> list[dict[str, Any]]:
    """O catálogo do provedor, com os preços já em dólares por MILHÃO de tokens.

    **Por que um módulo e não um método do cliente:** isto não é uma conversa.
    Não tem esforço de raciocínio nem stream, e quem chama é uma tela de admin —
    amarrá-lo ao cliente por conversa obrigaria a inventar uma conversa para
    listar preços. A `chave` é opcional: o catálogo do OpenRouter é público.

    A API devolve o preço **por token**, em string (`"0.000003"`). Quem lê uma
    tabela de custo pensa em milhão, e converter na borda é o que evita cada
    chamador multiplicar por um milhão do seu jeito — e algum deles esquecer.
    Preço ausente ou ilegível vira `None`, nunca zero: um modelo "de graça" na
    tabela de custo é pior que um modelo sem preço.
    """
    base = (base_url or URL_PADRAO).rstrip("/")
    if base.endswith(CAMINHO):
        base = base[: -len(CAMINHO)]
    cliente = http if http is not None else _http_padrao()
    # Outros servidores compatíveis (um gateway, um vLLM com chave) pedem no
    # catálogo a mesma chave da conversa. Sem preço na resposta (um servidor
    # local), as colunas de custo ficam `None`.
    cabecalhos = {"Accept": "application/json"}
    if chave:
        cabecalhos["Authorization"] = f"Bearer {chave}"
    resposta = await cliente.get(
        base + CAMINHO_DOS_MODELOS,
        headers=cabecalhos,
        timeout=TEMPO_LIMITE_DO_CATALOGO,
    )
    if resposta.status_code >= 400:
        raise ErroDoOpenRouter(
            f"o provedor respondeu {resposta.status_code} ao listar modelos",
            status=resposta.status_code,
        )
    corpo = resposta.json()
    linhas = corpo.get("data") if isinstance(corpo, dict) else None
    if not isinstance(linhas, list):
        raise ErroDoOpenRouter("a lista de modelos do provedor veio num formato inesperado")

    catalogo: list[dict[str, Any]] = []
    for linha in linhas:
        if not isinstance(linha, dict) or not linha.get("id"):
            continue
        precos = linha.get("pricing") if isinstance(linha.get("pricing"), dict) else {}
        catalogo.append({
            "id": str(linha["id"]),
            "nome": str(linha.get("name") or linha["id"]),
            "entrada_por_milhao": _por_milhao(precos.get("prompt")),
            "saida_por_milhao": _por_milhao(precos.get("completion")),
            "contexto": linha.get("context_length"),
        })
    return catalogo


def _por_milhao(valor: Any) -> float | None:
    """Preço por token → por milhão. `None` quando não dá para saber."""
    if valor is None or valor == "":
        return None
    try:
        return round(float(valor) * 1_000_000, 6)
    except (TypeError, ValueError):
        return None


class ClienteOpenRouter:
    """Um cliente por conversa, sobre o pool compartilhado do processo. Com
    `http` injetado (testes), usa o que veio e não toca no pool."""

    def __init__(
        self,
        chave: str,
        *,
        base_url: str = URL_PADRAO,
        http: httpx.AsyncClient | None = None,
        referer: str | None = None,
        titulo: str | None = None,
        tentativas: int = TENTATIVAS,
        dormir: Callable[[float], Any] = asyncio.sleep,
    ) -> None:
        if not chave:
            raise ValueError("LLM_API_KEY vazia: o assistente não pode falar com o modelo.")
        self._chave = chave
        # `base_url` é a BASE (`.../api/v1`); o caminho é daqui. Mas quem
        # configura a URL completa do endpoint não pode ser punido com
        # `/chat/completions/chat/completions` em todo pedido.
        base = (base_url or URL_PADRAO).rstrip("/")
        self._url = base if base.endswith(CAMINHO) else base + CAMINHO
        self._openrouter = e_openrouter(base)
        self._http = http
        self._referer = referer
        self._titulo = titulo
        self._tentativas = max(1, int(tentativas))
        self._dormir = dormir

    def _cabecalhos(self) -> dict[str, str]:
        cabecalhos = {
            "Authorization": f"Bearer {self._chave}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        # Atribuição do app no painel do OpenRouter: só quando a instalação
        # quer (ASSISTENTE_ATRIBUICAO), e quem chama passa título e referer.
        if self._titulo:
            cabecalhos["X-Title"] = self._titulo
        if self._referer:
            cabecalhos["HTTP-Referer"] = self._referer
        return cabecalhos

    async def transmitir(
        self,
        *,
        modelo: str,
        sistema: list[dict[str, Any]],
        conversa: list[dict[str, Any]],
        ferramentas: list[dict[str, Any]],
        max_tokens: int,
        esforco: str | None = "high",
    ) -> AsyncIterator[Delta | Resposta]:
        """Uma chamada ao modelo, em stream. Cede `Delta`s e, por último, a `Resposta`."""
        corpo = montar_pedido(
            modelo=modelo,
            sistema=sistema,
            conversa=conversa,
            ferramentas=ferramentas,
            max_tokens=max_tokens,
            esforco=esforco,
            openrouter=self._openrouter,
        )
        http = self._http if self._http is not None else _http_padrao()
        async for pedaco in self._transmitir_com(http, corpo):
            yield pedaco

    async def _transmitir_com(
        self, http: httpx.AsyncClient, corpo: dict[str, Any]
    ) -> AsyncIterator[Delta | Resposta]:
        resposta = await self._abrir(http, corpo)
        try:
            acumulador = _Acumulador()
            async for evento in _eventos_sse(resposta):
                for delta in acumulador.absorver(evento):
                    yield delta
            yield acumulador.resposta()
        finally:
            await resposta.aclose()

    async def _abrir(self, http: httpx.AsyncClient, corpo: dict[str, Any]) -> httpx.Response:
        """O POST, até os cabeçalhos. Retenta rede/429/5xx; um 400 com raciocínio
        guardado é refeito uma vez sem ele. Devolve a resposta com o corpo ainda
        por ler (stream)."""
        tentativa = 0
        ja_tirou_raciocinio = False
        while True:
            tentativa += 1
            pedido = http.build_request("POST", self._url, json=corpo, headers=self._cabecalhos())
            try:
                resposta = await http.send(pedido, stream=True)
            except httpx.TransportError as exc:
                if tentativa < self._tentativas:
                    await self._dormir(_espera(tentativa))
                    continue
                raise ErroDoOpenRouter(
                    f"falha de rede ao falar com o OpenRouter ({exc.__class__.__name__})"
                ) from exc

            status = resposta.status_code
            if status < 400:
                return resposta

            codigo, mensagem = await _ler_erro(resposta)
            if status in RETENTAVEIS and tentativa < self._tentativas:
                await self._dormir(_espera(tentativa, resposta.headers.get("retry-after")))
                continue
            if status == 400 and not ja_tirou_raciocinio and _tem_raciocinio(corpo):
                logger.warning(
                    "OpenRouter recusou o pedido (400: %s); refazendo sem o raciocínio guardado.",
                    mensagem,
                )
                corpo = _sem_raciocinio(corpo)
                ja_tirou_raciocinio = True
                continue
            raise ErroDoOpenRouter(
                f"OpenRouter respondeu {status}: {mensagem}", status=status, codigo=codigo
            )


# A ferramenta da sonda. Uma basta: a pergunta é «este modelo aceita ferramentas
# de algum jeito?», e a resposta não muda com quantas nem quais. Ela é declarada
# aqui, e não montada do servidor MCP, porque a sonda roda numa tela de admin —
# não há escopo de conversa nem workspace para montar o catálogo real.
_FERRAMENTA_DA_SONDA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "ping",
        "description": "Responde que está tudo bem. Não faz nada.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
}


async def sondar_modelo(
    modelo: str,
    *,
    chave: str,
    max_tokens: int,
    esforco: str | None,
    base_url: str = URL_PADRAO,
    http: httpx.AsyncClient | None = None,
    referer: str | None = None,
    titulo: str | None = None,
) -> None:
    """Este modelo consegue rodar o assistente? Levanta `ErroDoOpenRouter` se não.

    **Existe porque «está no catálogo» não quer dizer «serve».** O catálogo do
    provedor traz algumas centenas de modelos, e entre eles há variantes que o
    endpoint de conversa recusa por completo (as `:batch`, que respondem
    «cannot be used with the chat/completions endpoint»), modelos sem suporte a
    ferramentas — e o assistente manda as 42 em toda chamada — e modelos cujo
    teto de saída é menor que o nosso `max_tokens`. Salvar um deles derrubava o
    assistente para TODOS os usuários, com uma mensagem genérica, enquanto quem
    trocou não via nada.

    **O único teste confiável de «serve» é chamar.** Filtrar por campos do
    catálogo exigiria adivinhar quais campos existem e manter essa adivinhação
    em dia; uma chamada real responde certo sobre todos os casos de uma vez,
    inclusive os que ninguém previu — como a variante de batch, que não estava
    em nenhuma lista de suspeitos.

    O pedido tem a FORMA da conversa de verdade — as mesmas ferramentas,
    o mesmo `max_tokens`, o mesmo esforço de raciocínio — porque é a forma que
    o provedor recusa. Só o conteúdo é mínimo: uma mensagem curta, e a leitura
    para no primeiro pedaço. O custo é de alguns tokens, e `max_tokens` é um
    TETO, não uma meta: pedir 64 k não gasta 64 k.
    """
    cliente = ClienteOpenRouter(chave, base_url=base_url, http=http, referer=referer, titulo=titulo,
                                # Sem retentativas: a sonda é uma pergunta, não
                                # um trabalho. Um 429 aqui é resposta — este
                                # modelo não está disponível para nós agora.
                                tentativas=1)
    fluxo = cliente.transmitir(
        modelo=modelo,
        sistema=[{"type": "text", "text": "Responda apenas: ok."}],
        conversa=[{"role": "user", "content": "ok"}],
        ferramentas=[_FERRAMENTA_DA_SONDA],
        max_tokens=max_tokens,
        esforco=esforco,
    )
    try:
        # O primeiro pedaço basta: se o provedor fosse recusar, teria recusado
        # ao ABRIR o stream. Ler até o fim só gastaria tokens à toa.
        async for _ in fluxo:
            break
    except ErroDoOpenRouter as exc:
        # `status` só existe quando a recusa veio do HTTP — é ela que responde
        # «este modelo serve?». Sem `status`, o provedor ACEITOU o pedido e o
        # stream terminou de um jeito que esta função não tem por que julgar
        # (nenhum quadro, `finish_reason` ausente): a pergunta da sonda é sobre
        # a configuração, não sobre a resposta. Barrar aqui trancaria a troca
        # por um detalhe de transmissão que a conversa real lida sozinha.
        if exc.status is None:
            logger.info(
                "Assistente: sonda de %s aceita — o provedor respondeu, e o stream "
                "terminou sem quadro útil (%s).", modelo, exc,
            )
            return
        raise
    finally:
        await fluxo.aclose()


__all__ = [
    "CAMINHO",
    "ClienteOpenRouter",
    "Delta",
    "ErroDoOpenRouter",
    "PREFIXO_DE_ERRO",
    "RETENTAVEIS",
    "Resposta",
    "TENTATIVAS",
    "sondar_modelo",
    "URL_PADRAO",
    "ferramenta",
    "montar_mensagens",
    "montar_pedido",
]
