# flow/executor/edge_resolver.py
"""
Resolvedor único da aresta: dada UMA aresta e a saída do nó de origem, decide o
que entra no nó destino.

Fonte ÚNICA da semântica da aresta. Antes essa lógica vivia duplicada em dois
pontos de flow/executor/core.py — a montagem de input do run e a simulação de
schema — que divergiam no caso "sem chaves" (run espalhava tudo; a simulação
nomeava por parent_id). Centralizar aqui mata a divergência run × preview.
Ver docs/specs/edge-data-contract.md (PR 1).

Modos (strict — sem palpite cego):
  - from_key presente → {to_key or from_key: valor} se a chave existe no output;
    se NÃO existe, a aresta não contribui ({}) — nunca o "primeiro valor"
    (que cruzava dados de balde errado no Switch e injetava None em merge).
  - só to_key         → {to_key: 1º valor} (rename; pai vazio → não contribui)
  - nenhum            → espalha todos os outputs do pai (dict inteiro)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Mapping


@dataclass(frozen=True)
class Edge:
    """Visão tipada de uma aresta. `condition` é o roteamento de ramo dos nós
    de controle — ortogonal ao mapeamento de dado."""
    source: str
    target: str
    from_key: str | None = None
    to_key: str | None = None
    condition: bool | None = None

    @property
    def is_branch(self) -> bool:
        return self.condition is not None

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Edge":
        cond = d.get("condition")
        # `or None` normaliza "" (falsy, tratado como ausente pelo run) para None,
        # preservando a semântica de truthiness do código original.
        return cls(
            source=d["source"],
            target=d["target"],
            from_key=d.get("from_key") or None,
            to_key=d.get("to_key") or None,
            condition=cond if isinstance(cond, bool) else None,
        )


def _first_value(parent_outputs: Mapping[str, Any]) -> Any:
    return next(iter(parent_outputs.values()), None)


def resolve_edge_inputs(
    edge: "Mapping[str, Any] | Edge",
    parent_outputs: Mapping[str, Any],
    *,
    logger: Any = None,
    node_id: str | None = None,
    parent_id: str | None = None,
) -> dict:
    """Entradas que ESTA aresta injeta no nó destino.

    Retorna sempre um dict — modo mapeado: {porta: valor}; modo spread: cópia
    rasa da saída do pai. O chamador aplica com `inputs.update(resultado)`, o
    que é idêntico ao `inputs[k] = v` / `inputs.update(parent_outputs)` de antes.
    """
    e = edge if isinstance(edge, Edge) else Edge.from_dict(edge)

    if e.from_key:
        if e.from_key in parent_outputs:
            return {e.to_key or e.from_key: parent_outputs[e.from_key]}
        # from_key não está no output do pai. NÃO cai mais no "primeiro valor"
        # (o palpite cego que fazia o Switch com balde vazio cruzar dados do
        # balde errado — F5, e o pai skipado injetar None no merge — F14). A
        # aresta simplesmente NÃO contribui. A sinalização de from_key defasado
        # (typo) é papel da validação estática (`validate_service`), não do run.
        if logger is not None:
            logger.warning(
                "[%s] from_key '%s' não encontrado no output de '%s' "
                "(keys: %s). A aresta não contribui.",
                node_id, e.from_key, parent_id, list(parent_outputs.keys()),
            )
        return {}

    if e.to_key:
        # to_key sem from_key: rename do output do pai. Contrato de sub-fluxo
        # (origem sem candidatos → nó multi-porta). Pai vazio → não contribui.
        return {e.to_key: _first_value(parent_outputs)} if parent_outputs else {}

    return dict(parent_outputs)


def resolve_edge_schema_inputs(
    edge: "Mapping[str, Any] | Edge",
    parent_fields: List[Mapping[str, Any]],
) -> dict:
    """Espelho de `resolve_edge_inputs` no plano de SCHEMA (simulação/preview).

    `parent_fields`: lista de {name, type} da saída declarada/simulada do pai.
    Devolve {porta: "<type>"} nas MESMAS portas que o run produziria — mesma
    semântica strict, mantendo a paridade run × preview:
      - from_key que É campo declarado → {porta: <tipo>};
      - from_key que NÃO é campo declarado → a aresta não contribui ({}), igual
        ao run que não encontra a chave no output. (A validação estática
        sinaliza o from_key defasado a partir daqui.)
    """
    e = edge if isinstance(edge, Edge) else Edge.from_dict(edge)

    def _typed(f: Mapping[str, Any]) -> str:
        return f"<{f.get('type')}>"

    if e.from_key:
        match = next((f for f in parent_fields if f.get("name") == e.from_key), None)
        return {e.to_key or e.from_key: _typed(match)} if match is not None else {}

    if e.to_key:
        return {e.to_key: _typed(parent_fields[0])} if parent_fields else {}

    return {f["name"]: _typed(f) for f in parent_fields if f.get("name")}
