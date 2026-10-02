# tests/unit/test_mcp_parametros.py
"""
A regra de `inputs` × `params_schema` — a que o servidor passou a ser.

Antes deste módulo, o único lugar que olhava para o `params_schema` era o
diálogo da tela, e ele apenas coagia: `Number("")` virava `0`, `Boolean(qualquer
coisa)` virava `True` e `required` era enfeite visual. Quem chama por fora da
tela não tem formulário nenhum, manda tudo como texto e só descobre o engano no
meio do run — depois de gastar executor e escrever em banco.

Os casos aqui são, um a um, o que a tela deixava passar:

- vazio não é zero, e obrigatório sem valor é erro (não `0`, não `""`);
- `"false"`, `"0"` e `"não"` são falsos — a coerção ingênua os tornava `True`;
- coerção SÓ a partir de texto: `1` não é `true`, `true` não é `1`;
- schema que não descreve contrato não recusa nada, mas avisa;
- `null` é ausência dos dois lados: no input e no `default` do schema;
- valor absurdo (JSON fundo demais, inteiro de milhares de dígitos) sai como
  erro de validação, nunca como exceção crua — subir a exceção entregaria
  "erro inesperado" a quem consegue corrigir a entrada sozinho;
- os erros saem todos de uma vez, com caminho, e nunca ecoam o valor — um
  parâmetro pode carregar senha.
"""
from __future__ import annotations

import json

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from app.mcp.parametros import HINT_SEM_CONTRATO, validar_inputs


def _corpo(exc: ToolError) -> dict:
    return json.loads(str(exc))


def _erro(params_schema, inputs) -> dict:
    with pytest.raises(ToolError) as capturado:
        validar_inputs(params_schema, inputs)
    return _corpo(capturado.value)


# ── Sem contrato: não valida, mas avisa ───────────────────────────────────────


@pytest.mark.parametrize(
    "schema",
    [
        None,
        {},
        [],
        "string",
        {"x": "number"},                       # valor não é dict
        {"x": {"type": "array"}},              # tipo fora dos quatro
        {"x": {"type": "string"}, "y": {}},    # um dos campos sem tipo
    ],
)
def test_schema_sem_contrato_deixa_os_inputs_passarem_com_hint(schema):
    """Fluxo antigo continua rodando: o que falta é conferência, não permissão."""
    inputs, hints = validar_inputs(schema, {"x": "3", "y": True})

    assert inputs == {"x": "3", "y": True}
    assert HINT_SEM_CONTRATO in hints


def test_sem_schema_e_sem_inputs_devolve_dicionario_vazio():
    inputs, hints = validar_inputs(None, None)

    assert inputs == {}
    assert hints == [HINT_SEM_CONTRATO]


def test_inputs_que_nao_e_objeto_e_recusado():
    corpo = _erro({"x": {"type": "string"}}, ["x"])

    assert corpo["code"] == "validation"
    assert corpo["errors"] == [{"path": "inputs", "message": "esperado object"}]


# ── Obrigatório, default, ausência ────────────────────────────────────────────


def test_obrigatorio_ausente_e_erro():
    corpo = _erro({"cidade": {"type": "string", "required": True}}, {})

    assert corpo["code"] == "validation"
    assert corpo["errors"] == [{"path": "inputs.cidade", "message": "obrigatório e sem default"}]


def test_obrigatorio_com_default_e_preenchido_sem_erro():
    inputs, hints = validar_inputs(
        {"limite": {"type": "number", "required": True, "default": 10}}, {}
    )

    assert inputs == {"limite": 10}
    assert hints == []


def test_default_em_texto_chega_coagido():
    """`"5"` escrito no schema precisa virar 5, senão omitir difere de digitar."""
    inputs, _ = validar_inputs({"limite": {"type": "number", "default": "5"}}, {})

    assert inputs == {"limite": 5}


def test_default_invalido_e_denunciado_pelo_caminho():
    corpo = _erro({"limite": {"type": "number", "default": "dez"}}, {})

    assert corpo["errors"][0]["path"] == "inputs.limite"
    assert "default do params_schema" in corpo["errors"][0]["message"]


def test_opcional_ausente_nao_entra_como_nulo():
    """Nada de `{"cidade": None}`: o nó veria a chave e trataria o nulo como valor."""
    inputs, hints = validar_inputs({"cidade": {"type": "string"}}, {})

    assert inputs == {}
    assert hints == []


def test_nulo_explicito_conta_como_ausencia():
    corpo = _erro({"cidade": {"type": "string", "required": True}}, {"cidade": None})

    assert corpo["errors"][0]["message"] == "obrigatório e sem default"


def test_default_nulo_em_opcional_conta_como_ausencia_e_o_campo_nao_sai():
    """`default: null` não pode tornar o workflow inexecutável pelo MCP.

    É a mesma regra do input nulo, aplicada do outro lado do contrato: nulo é
    ausência de valor. Coagi-lo produzia sempre `problema` (nenhum dos quatro
    tipos aceita nulo) e o erro acusava o `params_schema` DO FLUXO — que quem
    chama não escreveu e não conserta com input nenhum. E `null` para um campo
    opcional em branco é exatamente o que um serializador JSON comum emite.
    """
    inputs, hints = validar_inputs({"bairro": {"type": "string", "default": None}}, {})

    assert inputs == {}
    assert hints == []


def test_default_nulo_em_obrigatorio_acusa_o_obrigatorio_e_nao_o_default():
    """Sem valor e sem default é falta de input — esse é o diagnóstico que serve."""
    corpo = _erro({"bairro": {"type": "string", "default": None, "required": True}}, {})

    assert corpo["errors"] == [{"path": "inputs.bairro", "message": "obrigatório e sem default"}]


# ── number ────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "enviado,esperado",
    [
        ("42", 42),
        ("-7", -7),
        (" 42 ", 42),
        ("3.5", 3.5),
        ("-0.5", -0.5),
        ("1e3", 1000.0),
        (42, 42),
        (3.5, 3.5),
    ],
)
def test_number_aceita_numero_e_texto_numerico(enviado, esperado):
    inputs, _ = validar_inputs({"n": {"type": "number"}}, {"n": enviado})

    assert inputs == {"n": esperado}
    assert type(inputs["n"]) is type(esperado)


def test_number_com_string_vazia_e_erro_e_nunca_zero():
    """O defeito original da tela: campo em branco virava `0` e o fluxo rodava."""
    corpo = _erro({"n": {"type": "number"}}, {"n": ""})

    assert corpo["errors"] == [{"path": "inputs.n", "message": "esperado number; string vazia não é zero"}]


@pytest.mark.parametrize("enviado", ["  ", "dez", "1,5", "12abc", True, False, [], {}])
def test_number_recusa_o_que_nao_e_numero(enviado):
    corpo = _erro({"n": {"type": "number"}}, {"n": enviado})

    assert corpo["errors"][0]["path"] == "inputs.n"
    assert corpo["errors"][0]["message"].startswith("esperado number")


@pytest.mark.parametrize("enviado", ["inf", "-inf", "nan", float("inf")])
def test_number_recusa_infinito_e_nan(enviado):
    """`json.dumps(float("inf"))` produz `Infinity`, que não é JSON válido."""
    corpo = _erro({"n": {"type": "number"}}, {"n": enviado})

    assert corpo["errors"][0]["message"] == "esperado number finito"


def test_number_com_inteiro_de_digitos_demais_e_recusado_sem_derrubar_a_chamada():
    """O interpretador tem teto de 4300 dígitos para converter texto em int.

    Acima dele `int()` levanta `ValueError` — que não é `ToolError`,
    `AtlasBaseError` nem `HTTPException` e portanto escapava do decorador
    `ferramenta`: o cliente recebia "erro inesperado" no lugar do `validation`
    com `errors[]`. O caminho é alcançável porque o valor chega como STRING
    JSON; um número JSON cru com 5000 dígitos já morreria no parser do SDK.
    """
    corpo = _erro({"n": {"type": "number", "required": True}}, {"n": "1" * 5000})

    assert corpo["code"] == "validation"
    assert corpo["errors"][0]["path"] == "inputs.n"
    assert corpo["errors"][0]["message"].startswith("esperado number")


def test_default_com_inteiro_de_digitos_demais_e_denunciado_como_default():
    """O default passa pela MESMA coerção — e caía pela mesma exceção crua."""
    corpo = _erro({"n": {"type": "number", "default": "1" * 5000}}, {})

    assert corpo["code"] == "validation"
    assert corpo["errors"][0]["path"] == "inputs.n"
    assert "default do params_schema" in corpo["errors"][0]["message"]


# ── boolean ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "enviado,esperado",
    [
        ("true", True), ("TRUE", True), ("True", True),
        ("1", True), ("yes", True), ("sim", True), (" Sim ", True),
        ("false", False), ("FALSE", False),
        ("0", False), ("no", False), ("não", False), ("NÃO", False), ("nao", False),
        (True, True), (False, False),
    ],
)
def test_boolean_entende_as_grafias_de_texto(enviado, esperado):
    inputs, _ = validar_inputs({"b": {"type": "boolean"}}, {"b": enviado})

    assert inputs == {"b": esperado}


@pytest.mark.parametrize("enviado", [1, 0, 2, "talvez", "", [], {}])
def test_boolean_recusa_numero_e_texto_desconhecido(enviado):
    """Em JSON, número é número: quem quer booleano escreve `true` ou `"1"`."""
    corpo = _erro({"b": {"type": "boolean"}}, {"b": enviado})

    assert corpo["errors"][0]["path"] == "inputs.b"
    assert corpo["errors"][0]["message"].startswith("esperado boolean")


# ── string ────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "enviado,esperado",
    [("oi", "oi"), ("", ""), (42, "42"), (3.5, "3.5"), (True, "true"), (False, "false")],
)
def test_string_aceita_texto_e_converte_escalares(enviado, esperado):
    inputs, _ = validar_inputs({"s": {"type": "string"}}, {"s": enviado})

    assert inputs == {"s": esperado}


@pytest.mark.parametrize("enviado", [{"a": 1}, [1, 2]])
def test_string_recusa_estrutura(enviado):
    corpo = _erro({"s": {"type": "string"}}, {"s": enviado})

    assert corpo["errors"] == [{"path": "inputs.s", "message": "esperado string"}]


# ── object ────────────────────────────────────────────────────────────────────


def test_object_aceita_dicionario_e_lista():
    inputs, _ = validar_inputs(
        {"o": {"type": "object"}, "l": {"type": "object"}},
        {"o": {"a": 1}, "l": [1, 2]},
    )

    assert inputs == {"o": {"a": 1}, "l": [1, 2]}


def test_object_decodifica_json_em_texto():
    inputs, _ = validar_inputs({"o": {"type": "object"}}, {"o": '{"a": 1}'})

    assert inputs == {"o": {"a": 1}}


def test_object_aceita_json_que_da_lista():
    inputs, _ = validar_inputs({"o": {"type": "object"}}, {"o": "[1, 2]"})

    assert inputs == {"o": [1, 2]}


@pytest.mark.parametrize(
    "enviado,trecho",
    [
        ("{a: 1}", "não é JSON válido"),
        ("", "não é JSON válido"),
        ('"texto"', "não é objeto nem lista"),
        ("42", "não é objeto nem lista"),
        ("null", "não é objeto nem lista"),
        (42, "esperado object"),
    ],
)
def test_object_recusa_json_invalido_ou_escalar(enviado, trecho):
    corpo = _erro({"o": {"type": "object"}}, {"o": enviado})

    assert trecho in corpo["errors"][0]["message"]


def test_object_com_json_aninhado_demais_vira_erro_de_validacao():
    """Aninhamento fundo estourava a pilha em vez de virar erro de entrada.

    O decodificador do CPython é recursivo e levanta `RecursionError` ANTES de
    decidir se o texto é JSON válido. Como ele herda de `RuntimeError`, escapava
    do `except ValueError` e do decorador `ferramenta`, e o cliente recebia
    "erro inesperado" — num caso que ele corrige sozinho — com a pilha no limite
    dentro do handler da request. 100 mil níveis estouram em qualquer versão.
    """
    corpo = _erro({"cfg": {"type": "object"}}, {"cfg": "[" * 100_000 + "]" * 100_000})

    assert corpo["code"] == "validation"
    assert corpo["errors"] == [
        {"path": "inputs.cfg", "message": "esperado object; o texto enviado não é JSON válido"}
    ]


def _aninhado(niveis: int) -> list:
    """Lista com `niveis` níveis, montada sem recursão."""
    valor: list = []
    for _ in range(niveis - 1):
        valor = [valor]
    return valor


@pytest.mark.parametrize("como", ["texto", "nativo"])
def test_object_fundo_demais_e_recusado_mesmo_quando_o_json_decodifica(como):
    """Do 3.12 em diante o `json.loads` aceita 2000 níveis (o decodificador conta
    no limite de recursão do C): sem o teto explícito, o objeto passava daqui e
    estourava a pilha de quem o percorresse depois. Nativo também — o corpo da
    chamada chega já decodificado. 150 níveis decodificam em qualquer versão, e
    o resultado é o mesmo em todas."""
    fundo = _aninhado(150)
    enviado = json.dumps(fundo) if como == "texto" else fundo
    corpo = _erro({"cfg": {"type": "object"}}, {"cfg": enviado})

    assert corpo["code"] == "validation"
    assert corpo["errors"] == [
        {"path": "inputs.cfg", "message": "esperado object; aninhamento acima de 100 níveis"}
    ]


def test_object_no_teto_de_aninhamento_passa():
    no_teto = _aninhado(100)
    inputs, _ = validar_inputs({"cfg": {"type": "object"}}, {"cfg": json.dumps(no_teto)})
    assert inputs == {"cfg": no_teto}

    corpo = _erro({"cfg": {"type": "object"}}, {"cfg": json.dumps(_aninhado(101))})
    assert corpo["errors"][0]["message"] == "esperado object; aninhamento acima de 100 níveis"


# ── Chaves não declaradas ─────────────────────────────────────────────────────


def test_chave_nao_declarada_passa_intacta_e_vira_hint():
    """O gatilho de webhook tem o seu próprio `payload_schema`, conferido depois."""
    inputs, hints = validar_inputs(
        {"cidade": {"type": "string"}},
        {"cidade": "Recife", "payload": {"id": 9}, "extra": "1"},
    )

    assert inputs == {"cidade": "Recife", "payload": {"id": 9}, "extra": "1"}
    assert len(hints) == 1
    assert "extra" in hints[0] and "payload" in hints[0]


# ── Agregação e segurança da mensagem ─────────────────────────────────────────


def test_os_erros_saem_todos_de_uma_vez():
    """Um problema por tentativa faria quem chama descobrir o schema a golpes."""
    corpo = _erro(
        {
            "n": {"type": "number"},
            "b": {"type": "boolean"},
            "s": {"type": "string", "required": True},
        },
        {"n": "", "b": "talvez"},
    )

    caminhos = [item["path"] for item in corpo["errors"]]
    assert caminhos == ["inputs.n", "inputs.b", "inputs.s"]
    assert corpo["code"] == "validation"
    assert corpo["hint"]


def test_a_mensagem_de_erro_nao_ecoa_o_valor_enviado():
    """Um parâmetro pode carregar senha; o erro é a rota mais fácil até o log."""
    corpo = _erro(
        {"dsn": {"type": "number"}},
        {"dsn": "postgresql://ana:sup3rs3cr3t@db.local:5432/geo"},  # pragma: allowlist secret
    )

    texto = json.dumps(corpo, ensure_ascii=False)
    assert "sup3rs3cr3t" not in texto
    assert "db.local" not in texto


def test_o_dicionario_de_entrada_nao_e_alterado():
    """Quem chamou ainda precisa do que mandou (auditoria, nova tentativa)."""
    originais = {"n": "42", "extra": 1}
    inputs, _ = validar_inputs({"n": {"type": "number"}}, originais)

    assert originais == {"n": "42", "extra": 1}
    assert inputs == {"n": 42, "extra": 1}
