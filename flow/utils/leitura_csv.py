# flow/utils/leitura_csv.py
"""
CSV reading for the nodes that read one (Entrada de Dados, Ler CSV com
Coordenadas).

`;` with the decimal comma is the CSV of Excel in Portuguese, and the default
of the "Salvar arquivo" node. Read with pandas' default (`,`) it became a
single column holding the whole line — in silence, in Entrada de Dados.
"""
import re

import pandas as pd

# A number with the decimal comma, as Excel in Portuguese writes it: "1500,5",
# "-63,9004", "1.500,50". An integer among them ("12") is one too.
_NUMERO_COM_VIRGULA = re.compile(r"[+-]?(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?")


def ler_csv(caminho: str) -> pd.DataFrame:
    """Reads a CSV separated by ',' or by ';', told apart by the header line,
    in UTF-8 or in the Windows-1252 that Excel in Portuguese saves."""
    with open(caminho, "rb") as arquivo:
        cabecalho = arquivo.readline().decode("utf-8-sig", errors="replace")
    separador = ";" if cabecalho.count(";") > cabecalho.count(",") else ","
    try:
        tabela = pd.read_csv(caminho, sep=separador)
    except UnicodeDecodeError:
        # "CSV (separado por vírgulas)" in Excel in Portuguese is not UTF-8.
        tabela = pd.read_csv(caminho, sep=separador, encoding="cp1252")
    return _virgula_decimal(tabela) if separador == ";" else tabela


def _virgula_decimal(tabela: pd.DataFrame) -> pd.DataFrame:
    """With ';' either decimal mark comes: Excel in Portuguese writes '1500,5',
    QGIS and pandas write '1500.5'. Read with '.', the second is already a
    number; a column of decimal commas came as text, and becomes numbers when
    every value is one and at least one has the comma — a code like
    '12.345.678', with no comma anywhere, stays text, as it came before."""
    for coluna in tabela.select_dtypes(include="object").columns:
        valores = tabela[coluna].dropna()
        if valores.empty or not all(
            isinstance(v, str) and _NUMERO_COM_VIRGULA.fullmatch(v.strip()) for v in valores
        ) or not any("," in v for v in valores):
            continue
        tabela[coluna] = pd.to_numeric(
            tabela[coluna].str.strip().str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
        )
    return tabela
