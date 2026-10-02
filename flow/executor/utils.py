# flow/executor/utils.py
"""Helpers de inspeção e debug de outputs."""
from flow.utils.logger import get_logger

logger = get_logger(__name__)


def _count_gdf_features(data: dict) -> "int | None":
    """Conta total de features em GeoDataFrames presentes em um dict de outputs/inputs."""
    try:
        import geopandas as gpd
        total = sum(len(v) for v in data.values() if isinstance(v, gpd.GeoDataFrame))
        return total if total > 0 else None
    except Exception as exc:
        logger.debug("Falha ao contar features: %s", exc)
        return None


# Teto por saida. Uma tabela larga (censo, dados brutos de sensor) passa de mil
# colunas; a lista vai para o node_stats, que e persistido em JSON e devolvido
# na observabilidade. O que interessa e alimentar sugestao de nome de coluna, e
# ninguem escolhe entre mil — truncar aqui evita inchar o registro de todo run.
#
# Publico porque a UI avisa que a lista foi cortada quando ela vem no limite.
MAX_COLUNAS = 200


def _coluna_de_geometria(valor) -> "str | None":
    """Nome da coluna de geometria ATIVA, quando ha uma.

    Perguntar ao GeoDataFrame em vez de adivinhar por nome: o padrao do
    geopandas e "geometry", mas os nos de banco usam "geom", e um atributo
    chamado "geom" num DataFrame comum nao e geometria nenhuma.
    """
    nome = getattr(valor, "_geometry_column_name", None)
    return str(nome) if nome else None


def _colunas_das_saidas(data: dict) -> "dict | None":
    """Colunas de ATRIBUTO de cada saida tabular de um no.

    Existe para o editor parar de exigir adivinhacao: quem configura um Join ou
    um filtro precisa saber quais colunas chegam ali, e a unica forma era
    executar e olhar o resultado. Gravado por execucao, cobre QUALQUER no —
    inclusive PythonScript, cuja saida nenhuma analise estatica prediz.

    A coluna de geometria fica DE FORA. A lista alimenta campos que pedem nome
    de coluna de atributo, e a geometria nao serve para nenhum deles: no Join,
    traze-la de B colide com a de A e o no falha; no filtro, comparar geometria
    com um valor tambem falha. Sugerir o que sempre da errado e pior que nao
    sugerir.

    Devolve None quando nao ha nada tabular: `node_stats` e por no e por run, e
    uma chave a mais em cada um deles se paga em bytes no banco.
    """
    try:
        import pandas as pd

        achadas = {}
        for chave, valor in (data or {}).items():
            if not isinstance(valor, pd.DataFrame):
                continue
            geometria = _coluna_de_geometria(valor)
            nomes = [str(c) for c in valor.columns if str(c) != geometria]
            # Truncar sem inventar item na lista: o marcador de corte que havia
            # aqui ("… (+312)") ia junto das colunas, e a UI renderiza CADA item
            # como sugestao clicavel — dava para inserir o marcador como se
            # fosse nome de coluna. Quem exibe deduz o corte pelo tamanho.
            achadas[str(chave)] = nomes[:MAX_COLUNAS]
        return achadas or None
    except Exception as exc:
        logger.debug("Falha ao listar colunas das saidas: %s", exc)
        return None


def _build_debug_summary(data: dict, with_bounds: bool = True) -> dict:
    """Constrói resumo legível de inputs/outputs para eventos de debug automático.

    `with_bounds=False` omite o `total_bounds` do GeoDataFrame: ele varre TODAS
    as geometrias (O(n) — 13,6 ms num GDF de 300k feições) e isso só se paga no
    evento de debug, que é opt-in por `debug_mode`. O caminho de log por nó
    (`_LazySummary`) passa False.
    """
    import json
    resumo: dict = {}
    for key, value in data.items():
        try:
            # GeoDataFrame tem total_bounds e crs; DataFrame puro nao.
            # Discrimina os dois para nao cair no except generico.
            if hasattr(value, "total_bounds") and hasattr(value, "crs"):
                colunas = list(value.columns)
                crs = str(value.crs) if value.crs else "N/A"
                resumo[key] = (
                    f"GeoDataFrame | {len(value)} registros | "
                    f"CRS: {crs} | colunas: {colunas}"
                )
                if with_bounds:
                    resumo[key] += f" | bounds: {value.total_bounds.tolist()}"
            elif hasattr(value, "to_json") and hasattr(value, "columns"):
                resumo[key] = (
                    f"DataFrame | {len(value)} registros | "
                    f"colunas: {list(value.columns)}"
                )
            elif isinstance(value, dict):
                resumo[key] = f"dict | {len(value)} chaves: {list(value.keys())}"
            elif isinstance(value, list):
                resumo[key] = f"list | {len(value)} itens"
            elif isinstance(value, (str, bytes)):
                # Fatia ANTES de serializar. `json.dumps` de um corpo de 20 MB
                # (http_request devolve o response cru) materializava os 20 MB
                # inteiros só para descartar tudo menos 300 chars — medido:
                # 20 MB de pico para produzir 313 caracteres.
                trecho = value[:300]
                if isinstance(trecho, bytes):
                    trecho = trecho.decode("utf-8", "replace")
                resumo[key] = trecho + ("…" if len(value) > 300 else "")
            else:
                val_str = json.dumps(value, default=str)
                resumo[key] = val_str[:300] + ("…" if len(val_str) > 300 else "")
        except Exception as e:
            resumo[key] = f"[Erro ao inspecionar]: {e}"
    return resumo
