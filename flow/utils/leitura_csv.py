# flow/utils/leitura_csv.py
"""
CSV reading for the nodes that read one (Entrada de Dados, Ler CSV com
Coordenadas).

`;` with the decimal comma is the CSV of Excel in Portuguese, and the default
of the "Salvar arquivo" node. Read with pandas' default (`,`) it became a
single column holding the whole line — in silence, in Entrada de Dados.
"""
import pandas as pd


def ler_csv(caminho: str) -> pd.DataFrame:
    """Reads a CSV separated by ',' or by ';' (then with the decimal comma),
    told apart by the header line."""
    with open(caminho, encoding="utf-8-sig", errors="replace") as arquivo:
        cabecalho = arquivo.readline()
    if cabecalho.count(";") > cabecalho.count(","):
        return pd.read_csv(caminho, sep=";", decimal=",")
    return pd.read_csv(caminho)
