# flow/nodes/action/attribute_join.py
"""
Join by ATTRIBUTE — matches two layers by a key column, not by geometry.

The catalog did not have this. `Merge` merges workflow branches, `Aggregate` stacks
rows or dissolves geometries, and `SpatialJoin` matches by geometry. Bringing the
population from a table onto the tract grid by tract code — the most common
analysis operation — was only possible by writing a `PythonScript`.

Both inputs are DECLARED (`layerA`/`layerB`). That is what makes the canvas
draw two named handles and the editor fill in the edge's `to_key`; a node
with no declared ports receives both edges on the same key and loses one of them.
"""
import asyncio
from typing import Any, Dict

import geopandas as gpd
import pandas as pd

from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger
from flow.utils.parameter_validation import requested_columns

logger = get_logger(__name__)

# The tolerant parser was born here and became a shared utility when other
# nodes gained chip fields (the history is in the docstring of
# `requested_columns`). The local name stays as an alias for execute() and the tests.
_requested_columns = requested_columns


def _dtype_family(serie: "pd.Series") -> str:
    """Groups dtypes into what matters for a merge: number, text or other.

    `int64` and `float64` match each other; `object` (text) against any number
    matches NOTHING — and pandas does not warn, it returns the whole column as null.
    """
    if pd.api.types.is_numeric_dtype(serie):
        return "número"
    if pd.api.types.is_string_dtype(serie) or serie.dtype == object:
        return "texto"
    return str(serie.dtype)


@register_node
class AttributeJoin(BaseNode):
    """Brings columns from B into A by matching on a key column."""

    @classmethod
    def description(cls) -> Dict[str, Any]:
        return {
            "name": "AttributeJoin",
            "alias": "Join por Atributo",
            "description": (
                "Junta duas entradas por uma coluna-chave (nao pela geometria) e traz "
                "para A as colunas escolhidas de B. A geometria e o CRS de A sao "
                "preservados; B pode ser uma tabela sem geometria."
            ),
            "type": "action",
            "properties": [
                {
                    "name": "keyA",
                    "label": "Chave em A",
                    "type": "string",
                    "suggest_columns": "layerA",
                    "default": "",
                    "description": "Coluna de A usada para casar as linhas.",
                },
                {
                    "name": "keyB",
                    "label": "Chave em B",
                    "type": "string",
                    "suggest_columns": "layerB",
                    "default": "",
                    "description": "Coluna de B. Deixe vazio se tiver o mesmo nome da chave em A.",
                },
                {
                    "name": "columns",
                    "label": "Colunas de B a trazer",
                    "type": "chips",
                    "suggest_columns": "layerB",
                    "default": [],
                    "description": (
                        "Vazio traz todas as colunas de B, menos a chave. "
                        "Colar varios nomes separados por virgula adiciona todos."
                    ),
                },
                {
                    "name": "how",
                    "label": "Feições sem correspondência",
                    "type": "select",
                    "default": "left",
                    "description": (
                        "'Manter' preserva todas as feicoes de A, com as colunas de B "
                        "nulas onde nao houve par. 'Descartar' remove essas feicoes."
                    ),
                    "options": [
                        {"value": "left", "label": "Manter (colunas nulas)"},
                        {"value": "inner", "label": "Descartar"},
                    ],
                },
                {
                    "name": "seDuplicado",
                    "label": "Se a chave repetir em B",
                    "type": "select",
                    "default": "falhar",
                    "description": (
                        "Chave repetida em B MULTIPLICA as feicoes de A. 'Interromper' "
                        "e o padrao porque o resultado sai maior sem nada indicando isso."
                    ),
                    "options": [
                        {"value": "falhar", "label": "Interromper e avisar"},
                        {"value": "primeira", "label": "Usar a primeira de cada chave"},
                        {"value": "todas", "label": "Manter todas (join 1:N)"},
                    ],
                },
            ],
            "inputs": [
                {"name": "layerA", "type": "geodataframe", "description": "Camada que RECEBE as colunas. A geometria e o CRS da saída são os dela."},
                {"name": "layerB", "type": "geodataframe", "description": "Camada ou tabela de onde as colunas vêm. Pode não ter geometria."},
            ],
            "outputs": [
                {"name": "output", "type": "geodataframe", "description": "layerA com as colunas de B anexadas"},
            ],
        }

    def _table(self, inputs: Dict[str, Any], chave: str) -> "pd.DataFrame":
        """Accepts a DataFrame OR a GeoDataFrame.

        The base class's `get_input_gdf` requires a GeoDataFrame, and the normal case
        for B is precisely a TABLE without geometry — the population spreadsheet, the
        result of a SQL query.
        """
        valor = inputs.get(chave)
        if valor is None:
            raise ValueError(
                f"Entrada '{chave}' não conectada. Entradas recebidas: {list(inputs.keys())}."
            )
        if not isinstance(valor, pd.DataFrame):
            raise TypeError(
                f"Entrada '{chave}' não é uma tabela nem uma camada "
                f"(recebido: {type(valor).__name__})."
            )
        if valor.empty:
            raise ValueError(f"Entrada '{chave}' está vazia.")
        return valor

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.validate()

        key_a = self.get_param("keyA", "").strip()
        key_b = self.get_param("keyB", "").strip() or key_a
        how = self.get_param("how", "left")
        on_duplicate = self.get_param("seDuplicado", "falhar")
        colunas = _requested_columns(self.get_param("columns", ""))

        if not key_a:
            raise ValueError("Informe a coluna-chave em A.")

        A = self._table(inputs, "layerA")
        B = self._table(inputs, "layerB")

        if key_a not in A.columns:
            raise ValueError(
                f"Coluna '{key_a}' não existe em A. Colunas disponíveis: {list(A.columns)}."
            )
        if key_b not in B.columns:
            raise ValueError(
                f"Coluna '{key_b}' não existe em B. Colunas disponíveis: {list(B.columns)}."
            )

        # Incompatible types match NOTHING and pandas does not complain: the output comes
        # with the whole column null and looks like "no record matched".
        fam_a, fam_b = _dtype_family(A[key_a]), _dtype_family(B[key_b])
        if fam_a != fam_b:
            raise ValueError(
                f"A chave tem tipos diferentes nos dois lados: '{key_a}' em A é "
                f"{fam_a} e '{key_b}' em B é {fam_b}. Nenhuma linha casaria. "
                "Converta um dos lados antes deste nó."
            )

        # Slices B BEFORE the merge. Without this, columns nobody asked for come along,
        # and names equal to A's silently become `_x`/`_y`.
        if colunas:
            faltando = [c for c in colunas if c not in B.columns]
            if faltando:
                raise ValueError(
                    f"Colunas não encontradas em B: {faltando}. "
                    f"Disponíveis: {[c for c in B.columns if c != 'geometry']}."
                )
        else:
            colunas = [c for c in B.columns if c not in (key_b, "geometry")]

        # B's key never comes in as a brought column. Explicitly requested in
        # `columns`, it showed up twice in the slice `B[[key_b] + colunas]`, and
        # `b[key_b]` stopped being a Series — the duplicate check broke
        # with "'DataFrame' object has no attribute 'unique'", an internal error that
        # tells nothing to someone who just asked for a column. Bringing it would be
        # redundant anyway: the key is already in A, and the merge drops it at the end.
        colunas = [c for c in colunas if c != key_b]

        colliding = [c for c in colunas if c in A.columns]
        if colliding:
            raise ValueError(
                f"A já tem coluna(s) com este nome: {colliding}. Renomeie antes deste nó "
                "(nó 'Definir Campos'), ou não traga essa coluna."
            )

        b = B[[key_b] + colunas]

        # The duplicate is this node's silent defect: it MULTIPLIES A's features,
        # and the run ends green with more features than went in.
        repetidas = b[key_b][b[key_b].duplicated()].unique()
        if len(repetidas) and on_duplicate != "todas":
            if on_duplicate == "falhar":
                amostra = ", ".join(str(v) for v in repetidas[:5])
                extra = f" (e mais {len(repetidas) - 5})" if len(repetidas) > 5 else ""
                raise ValueError(
                    f"A chave '{key_b}' se repete em B: {amostra}{extra}. "
                    f"Isso multiplicaria as {len(A)} feições de A. "
                    "Escolha 'Usar a primeira de cada chave' ou 'Manter todas' "
                    "em 'Se a chave repetir em B', ou agregue B antes deste nó."
                )
            antes = len(b)
            b = b.drop_duplicates(subset=key_b)
            self.log(
                f"Chave '{key_b}' repetida em B: {antes - len(b)} linha(s) descartada(s), "
                f"mantida a primeira de cada uma das {len(repetidas)} chaves."
            )

        # `indicator` answers WHO matched. Previously "no match" was
        # inferred from `resultado[colunas[0]].isna()`, which counts as unmatched
        # every row where the brought column is null BECAUSE it is null in B —
        # sending people to look for a key problem that does not exist.
        MARCA = "__origem_do_join__"

        def _merge() -> "pd.DataFrame":
            # A.merge, and NOT B.merge: called from the GeoDataFrame the
            # result stays a GeoDataFrame, with geometry and CRS. The other way around
            # it would become a plain DataFrame and the following spatial nodes would fail.
            return A.merge(b, left_on=key_a, right_on=key_b, how=how, indicator=MARCA)

        resultado = await asyncio.to_thread(_merge)

        # B's key becomes a duplicate column when its name differs from A's.
        if key_b != key_a and key_b in resultado.columns:
            resultado = resultado.drop(columns=[key_b])

        if isinstance(A, gpd.GeoDataFrame) and not isinstance(resultado, gpd.GeoDataFrame):
            resultado = gpd.GeoDataFrame(resultado, geometry=A.geometry.name, crs=A.crs)

        unmatched = int((resultado[MARCA] == "left_only").sum())
        resultado = resultado.drop(columns=[MARCA])
        self.log(
            f"Join por '{key_a}': {len(A)} feições entraram, {len(resultado)} saíram"
            + (f", {unmatched} sem correspondência em B." if how == "left" else ".")
        )

        return {"output": resultado}
