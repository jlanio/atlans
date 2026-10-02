# app/mcp/parametros.py
"""
Validação e coerção dos `inputs` contra o `params_schema` do workflow.

Até aqui ninguém validava: a tela de execução apenas COAGIA no navegador
(`Number("")` vira `0`, `Boolean("false")` vira `True`, `object` ia cru) e o
servidor aceitava o que chegasse. Com um cliente do MCP no lugar da tela, esse
silêncio fica caro: quem monta a chamada não vê o formulário, manda tudo como
texto e descobre o erro no meio do run — depois de gastar executor, de escrever
em banco e de produzir artefato errado. Daí a regra estar aqui, ANTES do
despacho, e ser a mesma para todo mundo.

Três decisões que explicam o formato:

- **Coerção só a partir de string.** O JSON já distingue `1` de `"1"`; se o
  chamador mandou `1` onde se declarou `boolean`, isso é engano dele, não
  formato frouxo. O que a coerção resolve é o caso legítimo do texto — a linha
  de comando, o formulário, a variável de ambiente — tudo chega como string.
- **String vazia nunca vira valor.** Era o pior defeito da tela: campo em
  branco virava `0` e o fluxo rodava com um número que ninguém digitou.
  Vazio é ausência, e ausência de obrigatório é erro.
- **`params_schema` malformado não é erro.** Fluxo antigo (ou gerado fora da
  tela) pode ter `params_schema` nulo, lista, ou valores que não descrevem
  tipo. Recusar a execução por causa disso quebraria fluxos que funcionam hoje;
  o certo é passar os inputs adiante e DIZER, num hint, que ninguém os
  conferiu.

Chave não declarada também passa intacta: o gatilho de webhook tem o seu
próprio `payload_schema`, validado no despacho, e reclamar aqui de um campo que
o outro contrato exige seria recusar o fluxo certo.
"""
from __future__ import annotations

import json
import math
import re
from typing import Any

from app.core.utils.logger import scrub_text
from app.mcp.erros import erro

# Os tipos que a tela de parâmetros emite e que o executor sabe receber. Um
# `type` fora desta lista é sinal de schema de outra procedência — e schema que
# não reconhecemos vira "sem contrato", não erro.
TIPOS = ("string", "number", "boolean", "object")

# Inteiro puro: é o que decide entre `int` e `float`. Sem isto, "3" viraria
# `3.0` e um nó que indexa lista ou monta paginação receberia float.
_INTEIRO = re.compile(r"^-?\d+$")

# Grafias aceitas para booleano em texto. Inclui `nao` sem acento porque quem
# escreve na linha de comando raramente acentua, e recusar por causa do til
# seria um erro sem nenhum ganho.
_VERDADEIRO = frozenset({"true", "1", "yes", "sim"})
_FALSO = frozenset({"false", "0", "no", "não", "nao"})

# Teto de aninhamento de um `object`. Parâmetro de fluxo de verdade fica muito
# abaixo — uma FeatureCollection de MultiPolygons dá 8 níveis. Até o Python 3.11 o
# teto era implícito: o `json.loads` levantava `RecursionError` perto de 1000
# níveis. A partir do 3.12 o decodificador conta no limite de recursão do C,
# e 2000 níveis passam — o objeto seguia adiante e estourava a pilha em quem o
# percorresse depois (validação, cópia, o executor), longe desta camada, que
# existe para devolver `validation`. Explícito, vale igual em qualquer versão.
_PROFUNDIDADE_MAXIMA = 100

HINT_SEM_CONTRATO = "params_schema ausente ou malformado: inputs não validados"


def _schema_valido(params_schema: Any) -> bool:
    """O `params_schema` descreve um contrato? (formato da tela de execução)

    Dict não vazio cujos valores são todos dicts com `type` conhecido. O dict
    VAZIO conta como ausente de propósito: "nenhum parâmetro declarado" e
    "schema que não sei ler" levam ao mesmo lugar — nada a conferir.
    """
    if not isinstance(params_schema, dict) or not params_schema:
        return False
    return all(
        isinstance(decl, dict) and decl.get("type") in TIPOS
        for decl in params_schema.values()
    )


def _para_numero(valor: Any) -> tuple[Any, str | None]:
    # `bool` é subclasse de `int` em Python: sem esta linha, `True` passaria
    # como número 1 e o fluxo receberia um booleano onde espera quantidade.
    if isinstance(valor, bool):
        return None, "esperado number; booleano não é número"
    if isinstance(valor, (int, float)):
        if isinstance(valor, float) and not math.isfinite(valor):
            return None, "esperado number finito"
        return valor, None
    if not isinstance(valor, str):
        return None, "esperado number"
    texto = valor.strip()
    if not texto:
        return None, "esperado number; string vazia não é zero"
    if _INTEIRO.match(texto):
        # O `try` não é supérfluo: desde o 3.10.7 o interpretador impõe um teto
        # de 4300 dígitos (`sys.set_int_max_str_digits`) para converter texto em
        # int, e acima dele `int()` levanta `ValueError`. Deixá-lo subir cru
        # entregaria "erro inesperado" ao cliente — o decorador `ferramenta` só
        # traduz `ToolError`, `AtlasBaseError` e `HTTPException` — num caso que
        # é erro de entrada como qualquer outro e que ele corrige sozinho.
        try:
            return int(texto), None
        except ValueError:
            return None, "esperado number; inteiro com dígitos demais"
    try:
        numero = float(texto)
    except ValueError:
        return None, "esperado number; o texto enviado não é numérico"
    if not math.isfinite(numero):
        return None, "esperado number finito"
    return numero, None


def _para_booleano(valor: Any) -> tuple[Any, str | None]:
    if isinstance(valor, bool):
        return valor, None
    if not isinstance(valor, str):
        # Inclusive `1`/`0`: em JSON, número é número. Quem quer booleano
        # escreve `true` ou manda a string "1".
        return None, "esperado boolean"
    texto = valor.strip().lower()
    if texto in _VERDADEIRO:
        return True, None
    if texto in _FALSO:
        return False, None
    return None, "esperado boolean (true/false, 1/0, yes/no, sim/não)"


def _para_texto(valor: Any) -> tuple[Any, str | None]:
    if isinstance(valor, str):
        return valor, None
    if isinstance(valor, bool):
        # "true"/"false", não "True"/"False": o valor veio de JSON e segue para
        # uma expressão do fluxo, onde a grafia em minúsculas é a reconhecida.
        return ("true" if valor else "false"), None
    if isinstance(valor, (int, float)):
        return str(valor), None
    return None, "esperado string"


def _fundo_demais(valor: Any) -> bool:
    """O `object` passa de `_PROFUNDIDADE_MAXIMA` níveis? (a raiz é o nível 1)

    Iterativo de propósito — medir recursivamente estouraria a pilha no mesmo
    caso que a medida existe para recusar — e um nível por volta, com os
    contêineres do nível seguinte coletados numa compreensão: roda no event
    loop, e um GeoJSON de 200 mil pontos passado como `object` custava centenas
    de milissegundos no laço item a item.
    """
    nivel = [valor]
    for _ in range(_PROFUNDIDADE_MAXIMA):
        nivel = [
            filho
            for conteiner in nivel
            for filho in (conteiner.values() if isinstance(conteiner, dict) else conteiner)
            if isinstance(filho, (dict, list))
        ]
        if not nivel:
            return False
    return True


def _para_objeto(valor: Any) -> tuple[Any, str | None]:
    if isinstance(valor, (dict, list)):
        decodificado = valor
    elif not isinstance(valor, str):
        return None, "esperado object (objeto ou lista JSON)"
    else:
        try:
            decodificado = json.loads(valor)
        except (ValueError, RecursionError):
            # `RecursionError` entra junto de `ValueError` — e não é limpeza a
            # fazer: o decodificador do CPython é recursivo e, com aninhamento
            # fundo o bastante (`"[[[[..."`), estoura a pilha ANTES de decidir
            # se o texto é JSON válido. Como ele herda de `RuntimeError`,
            # escaparia do decorador `ferramenta` e viraria "erro inesperado"
            # para o cliente, em vez do `validation` que esta camada existe
            # para produzir. Do ponto de vista de quem chamou é a mesma falha
            # das outras: o texto não é JSON que o servidor consiga ler.
            return None, "esperado object; o texto enviado não é JSON válido"
        if not isinstance(decodificado, (dict, list)):
            return None, "esperado object; o JSON enviado não é objeto nem lista"
    if _fundo_demais(decodificado):
        return None, f"esperado object; aninhamento acima de {_PROFUNDIDADE_MAXIMA} níveis"
    return decodificado, None


_COERCOES = {
    "string": _para_texto,
    "number": _para_numero,
    "boolean": _para_booleano,
    "object": _para_objeto,
}


def validar_inputs(params_schema: Any, inputs: dict | None) -> tuple[dict, list[str]]:
    """Confere `inputs` contra `params_schema` e devolve `(inputs, hints)`.

    Os erros são AGREGADOS num único `ToolError` `validation` com
    `errors=[{path, message}]`: quem chama corrige tudo de uma vez em vez de
    descobrir um problema por tentativa. A mensagem nomeia o campo e o tipo
    esperado e nunca ecoa o valor recebido — um parâmetro pode carregar senha,
    e o erro é a rota mais fácil de um segredo para o log.

    `hints` é aviso, não recusa: schema sem contrato e chave não declarada
    entram aí para que quem chama saiba o que NÃO foi conferido.
    """
    hints: list[str] = []

    if inputs is None:
        recebidos: dict[str, Any] = {}
    elif isinstance(inputs, dict):
        recebidos = dict(inputs)
    else:
        raise erro(
            "validation",
            "inputs precisa ser um objeto com um campo por parâmetro.",
            "consulte params_schema em get_workflow(workflow_id)",
            errors=[{"path": "inputs", "message": "esperado object"}],
        )

    if not _schema_valido(params_schema):
        hints.append(HINT_SEM_CONTRATO)
        return recebidos, hints

    saida: dict[str, Any] = {}
    erros: list[dict[str, str]] = []

    for nome, decl in params_schema.items():
        caminho = f"inputs.{nome}"
        coagir = _COERCOES[decl["type"]]
        # `None` explícito conta como ausência: nenhum dos quatro tipos aceita
        # nulo, então tratá-lo como valor só produziria um erro pior ("esperado
        # string") no lugar do certo ("obrigatório").
        presente = nome in recebidos and recebidos[nome] is not None

        if not presente:
            # `default: None` é a MESMA regra do input nulo, aplicada do outro
            # lado do contrato: nulo é ausência de valor, não valor. Vale pelo
            # mesmo motivo — nenhum dos quatro tipos aceita nulo, então coagi-lo
            # só produziria erro. Só que aqui o erro seria PIOR que o do input:
            # acusaria o `params_schema` do fluxo, que quem chama não escreveu e
            # não conserta com input nenhum, deixando o workflow inexecutável
            # pelo MCP. E `null` para campo opcional é o que um serializador
            # JSON comum emite, inclusive nos fluxos criados por `create_workflow`.
            padrao = decl.get("default")
            if padrao is not None:
                # O default também é coagido: `"5"` escrito no schema precisa
                # chegar ao executor como 5, senão o valor omitido se comporta
                # diferente do valor digitado.
                valor, problema = coagir(padrao)
                if problema:
                    erros.append({"path": caminho, "message": f"default do params_schema inválido: {problema}"})
                else:
                    saida[nome] = valor
            elif decl.get("required"):
                erros.append({"path": caminho, "message": "obrigatório e sem default"})
            continue

        valor, problema = coagir(recebidos[nome])
        if problema:
            erros.append({"path": caminho, "message": problema})
        else:
            saida[nome] = valor

    nao_declaradas = [nome for nome in recebidos if nome not in params_schema]
    for nome in nao_declaradas:
        saida[nome] = recebidos[nome]
    if nao_declaradas:
        hints.append(
            "chaves fora do params_schema, enviadas sem conferência: "
            + ", ".join(sorted(nao_declaradas))
        )

    if erros:
        raise erro(
            "validation",
            "Alguns inputs não batem com o params_schema do workflow.",
            "veja errors, corrija e chame de novo; get_workflow mostra o params_schema",
            errors=[
                {"path": scrub_text(item["path"]), "message": scrub_text(item["message"])}
                for item in erros
            ],
        )

    return saida, hints
