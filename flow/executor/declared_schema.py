# flow/executor/declared_schema.py
"""Saídas de um nó DECLARADAS na própria definição, sem executar nada.

Um nó com `dynamic_output` e sem `simulate()` sumia do /workflows/validate em
silêncio (8 nós do catálogo), e o painel de schema não tinha o que mostrar —
mesmo quando as saídas reais estão escritas no payload: `output_vars` do
PythonScript, `fallback_output` + `rules[].output` do Switch, `ports` do
SubWorkflowInput. Este módulo lê essas declarações e devolve o schema no
formato canônico da simulação: `[{"fields": [{"name", "type"}, ...]}]`.

Puro: só stdlib e flow.utils.workflow_contract (também puro).
"""
from __future__ import annotations

import json
from typing import Any, Optional

from flow.utils.workflow_contract import _parse_ports


def _campos(nomes: list) -> list:
    """Lista de nomes → forma agrupada; o tipo é "any" porque só o run o conhece."""
    return [{"fields": [{"name": nome, "type": "any"} for nome in nomes]}]


def _output_vars(bruto: Any) -> list:
    """`output_vars` exatamente como o run o trata: `validate()` exige string
    e o PythonScript recusa a lista vazia — com as MESMAS frases, para o
    a validação acusar o que o run acusaria. Antes, vazio virava schema `[]`
    com `ok`, e sem saídas conhecidas o diagnóstico de aresta se desligava."""
    if not isinstance(bruto, str):
        raise ValueError("O parâmetro 'output_vars' deve ser uma string.")
    nomes = [item.strip() for item in bruto.split(",") if item.strip()]
    if not nomes:
        raise ValueError("'output_vars' deve conter ao menos um nome de variável.")
    return nomes


def _regras(bruto: Any) -> list:
    """`rules` do Switch: lista nativa ou JSON serializado pelo editor.
    Qualquer coisa ilegível vira lista vazia — o lint, não isto, acusa."""
    if isinstance(bruto, str):
        try:
            bruto = json.loads(bruto)
        except (ValueError, TypeError):
            return []
    if not isinstance(bruto, list):
        return []
    return [regra for regra in bruto if isinstance(regra, dict)]


def _e_saida_utilizavel(campo: Any) -> bool:
    """Chaves internas do protocolo (`__response__`, `__artifact__`) não são
    saídas que uma aresta possa consumir — o executor as remove do que o nó
    entrega. Mesmo filtro do catálogo (app/services/node_service.py)."""
    if not isinstance(campo, dict):
        return False
    nome = campo.get("name")
    return isinstance(nome, str) and bool(nome) and not nome.startswith("__")


def schema_do_catalogo(desc: dict) -> list:
    """`outputs` do descriptor (campos tipados) na forma agrupada da simulação.

    O catálogo declara os campos numa lista plana `[{"name", "type", ...}]`;
    o formato canônico do simulate() continua agrupado, então a conversão mora
    aqui — num lugar só."""
    campos = [c for c in (desc.get("outputs") or []) if _e_saida_utilizavel(c)]
    return [{"fields": campos}]


def schema_declarado(node_def: dict, desc: dict) -> Optional[list]:
    """Schema de saída que a definição + o descriptor permitem afirmar.

    Ordem de precedência, da declaração mais específica para a mais genérica:
      1. `output_vars` (PythonScript): cada variável é uma saída;
      2. `rules` + `fallback_output` (Switch): fallback e as saídas das regras,
         que é exatamente o que o run emite (todas, mesmo vazias);
      3. `outputs_from_ports` (SubWorkflowInput): cada porta é uma saída;
      4. `outputs` do descriptor (os campos tipados do catálogo);
      5. None — nada a afirmar (o chamador decide o que fazer).

    Levanta ValueError, com a frase que o run usaria, quando a declaração é
    inválida (`output_vars` vazio ou não-string, `fallback_output` não-string).

    `parameters` é o formato do corpo da validação; `properties` o da definition
    salva — mesma tolerância do simulate_runner.
    """
    params = node_def.get("parameters") or node_def.get("properties") or {}
    if not isinstance(params, dict):
        params = {}
    props = {
        prop.get("name")
        for prop in (desc.get("properties") or [])
        if isinstance(prop, dict)
    }

    if "output_vars" in props:
        return _campos(_output_vars(params.get("output_vars", "result")))

    if "rules" in props and "fallback_output" in props:
        # Espelha switch.py: `parameters.get("fallback_output", "output_0")` —
        # chave ausente cai no default; presente e vazia emite a porta ''.
        fallback = params.get("fallback_output", "output_0")
        if not isinstance(fallback, str):
            raise ValueError("O parâmetro 'fallback_output' deve ser uma string.")
        saidas = [fallback]
        for regra in _regras(params.get("rules")):
            saida = regra.get("output")
            if isinstance(saida, str) and saida and saida not in saidas:
                saidas.append(saida)
        return _campos(saidas)

    if desc.get("outputs_from_ports"):
        portas = _parse_ports(params.get("ports"))
        if portas:
            return _campos(portas)

    if desc.get("outputs") is not None:
        return schema_do_catalogo(desc)

    return None
