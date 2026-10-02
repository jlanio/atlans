# flow/nodes/action/attribute_join.py
"""
Join por ATRIBUTO — casa duas camadas por uma coluna-chave, nao pela geometria.

O catalogo nao tinha isso. `Merge` mescla branches do fluxo, `Aggregate` empilha
linhas ou funde geometrias, e `SpatialJoin` casa por geometria. Trazer a
populacao de uma tabela para a malha de setores pelo codigo do setor — a
operacao mais comum de analise — so era possivel escrevendo um `PythonScript`.

As duas entradas sao DECLARADAS (`layerA`/`layerB`). E o que faz o canvas
desenhar dois handles nomeados e o editor preencher o `to_key` da aresta; um no
sem portas declaradas recebe as duas arestas na mesma chave e perde uma delas.
"""
import asyncio
from typing import Any, Dict

import geopandas as gpd
import pandas as pd

from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.logger import get_logger
from flow.utils.parameter_validation import colunas_pedidas

logger = get_logger(__name__)

# O parser tolerante nasceu aqui e virou utilitario compartilhado quando outros
# nos ganharam campos de fichas (a historia esta no docstring de
# `colunas_pedidas`). O nome local fica como alias para o execute() e os testes.
_colunas_pedidas = colunas_pedidas


def _familia(serie: "pd.Series") -> str:
    """Agrupa dtypes no que importa para um merge: numero, texto ou outro.

    `int64` e `float64` casam entre si; `object` (texto) contra qualquer numero
    nao casa NADA — e o pandas nao avisa, devolve a coluna inteira nula.
    """
    if pd.api.types.is_numeric_dtype(serie):
        return "número"
    if pd.api.types.is_string_dtype(serie) or serie.dtype == object:
        return "texto"
    return str(serie.dtype)


@register_node
class AttributeJoin(BaseNode):
    """Traz colunas de B para A casando por uma coluna-chave."""

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

    def _tabela(self, inputs: Dict[str, Any], chave: str) -> "pd.DataFrame":
        """Aceita DataFrame OU GeoDataFrame.

        `get_input_gdf` da classe base exige GeoDataFrame, e o caso normal de B e
        justamente uma TABELA sem geometria — a planilha de populacao, o retorno
        de uma consulta SQL.
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
        se_duplicado = self.get_param("seDuplicado", "falhar")
        colunas = _colunas_pedidas(self.get_param("columns", ""))

        if not key_a:
            raise ValueError("Informe a coluna-chave em A.")

        A = self._tabela(inputs, "layerA")
        B = self._tabela(inputs, "layerB")

        if key_a not in A.columns:
            raise ValueError(
                f"Coluna '{key_a}' não existe em A. Colunas disponíveis: {list(A.columns)}."
            )
        if key_b not in B.columns:
            raise ValueError(
                f"Coluna '{key_b}' não existe em B. Colunas disponíveis: {list(B.columns)}."
            )

        # Tipos incompatíveis não casam NADA e o pandas não reclama: a saída vem
        # com a coluna inteira nula e parece "nenhum registro bateu".
        fam_a, fam_b = _familia(A[key_a]), _familia(B[key_b])
        if fam_a != fam_b:
            raise ValueError(
                f"A chave tem tipos diferentes nos dois lados: '{key_a}' em A é "
                f"{fam_a} e '{key_b}' em B é {fam_b}. Nenhuma linha casaria. "
                "Converta um dos lados antes deste nó."
            )

        # Recorta B ANTES do merge. Sem isso vêm colunas que ninguém pediu, e
        # nomes iguais aos de A viram `_x`/`_y` em silêncio.
        if colunas:
            faltando = [c for c in colunas if c not in B.columns]
            if faltando:
                raise ValueError(
                    f"Colunas não encontradas em B: {faltando}. "
                    f"Disponíveis: {[c for c in B.columns if c != 'geometry']}."
                )
        else:
            colunas = [c for c in B.columns if c not in (key_b, "geometry")]

        # A chave de B nunca entra como coluna trazida. Pedida explicitamente em
        # `columns`, ela aparecia duas vezes no recorte `B[[key_b] + colunas]`, e
        # `b[key_b]` deixava de ser uma Series — a checagem de duplicata quebrava
        # com "'DataFrame' object has no attribute 'unique'", um erro interno que
        # não diz nada a quem só pediu uma coluna. Trazê-la seria redundante de
        # qualquer forma: a chave já está em A, e o merge a descarta no fim.
        colunas = [c for c in colunas if c != key_b]

        colidem = [c for c in colunas if c in A.columns]
        if colidem:
            raise ValueError(
                f"A já tem coluna(s) com este nome: {colidem}. Renomeie antes deste nó "
                "(nó 'Definir Campos'), ou não traga essa coluna."
            )

        b = B[[key_b] + colunas]

        # A duplicata é o defeito silencioso deste nó: ela MULTIPLICA as feições
        # de A, e o run termina em verde com mais feições do que entrou.
        repetidas = b[key_b][b[key_b].duplicated()].unique()
        if len(repetidas) and se_duplicado != "todas":
            if se_duplicado == "falhar":
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

        # `indicator` responde QUEM casou. Antes o "sem correspondência" era
        # inferido de `resultado[colunas[0]].isna()`, o que conta como falta de
        # par toda linha em que a coluna trazida é nula POR SER nula em B —
        # mandando procurar um problema de chave que não existe.
        MARCA = "__origem_do_join__"

        def _juntar() -> "pd.DataFrame":
            # A.merge, e NÃO B.merge: chamado a partir do GeoDataFrame o
            # resultado continua GeoDataFrame, com geometria e CRS. Ao contrário
            # viraria DataFrame comum e os nós espaciais seguintes falhariam.
            return A.merge(b, left_on=key_a, right_on=key_b, how=how, indicator=MARCA)

        resultado = await asyncio.to_thread(_juntar)

        # A chave de B vira coluna duplicada quando tem nome diferente da de A.
        if key_b != key_a and key_b in resultado.columns:
            resultado = resultado.drop(columns=[key_b])

        if isinstance(A, gpd.GeoDataFrame) and not isinstance(resultado, gpd.GeoDataFrame):
            resultado = gpd.GeoDataFrame(resultado, geometry=A.geometry.name, crs=A.crs)

        sem_par = int((resultado[MARCA] == "left_only").sum())
        resultado = resultado.drop(columns=[MARCA])
        self.log(
            f"Join por '{key_a}': {len(A)} feições entraram, {len(resultado)} saíram"
            + (f", {sem_par} sem correspondência em B." if how == "left" else ".")
        )

        return {"output": resultado}
