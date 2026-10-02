# tests/unit/test_catalogo_cabe_nas_colunas.py
"""O catálogo versionado cabe nas colunas do banco — conferido no CI.

**Este é o teste que faltava, e a razão de ele faltar é instrutiva.** O resto da
suíte roda em SQLite, e o SQLite **ignora o tamanho declarado de `VARCHAR`**:
`VARCHAR(255)` aceita 10 mil caracteres sem reclamar. O PostgreSQL não. Então o
estouro que derrubou a importação em produção era, por construção, invisível
para todos os testes de importação que existem — eles passavam com o mesmo dado
que o Postgres recusava.

O que aconteceu: 48 dos 25.492 registros de `catalogo/geoservicos` tinham
`titulo` acima de 255 caracteres (o maior, um indicador do IBGE, com 276). Como
`importar_pasta` commita de 500 em 500, o lote que continha o primeiro deles
(posição 6.779) levantava `StringDataRightTruncationError` e abortava o resto:
6.500 registros no banco, 18.992 perdidos, e nada além de um ERROR no log. O
assistente ficou sem três quartos das camadas que deveria saber encontrar.

Este teste não dubla nada e não toca em banco: lê o catálogo REAL do repositório
e compara cada campo com o limite da COLUNA, tirado do modelo. Ele falha no CI
no dia em que alguém acrescentar ao catálogo um registro que o Postgres
recusaria — que é exatamente o dia em que se quer saber.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.models.fonte_de_dados import FonteDeDados
from app.services import fontes_service as fs
from app.services import fontes_vault

CATALOGO = Path(__file__).resolve().parents[2] / "catalogo" / "geoservicos"

# Tudo o que o Vault preenche. Quais deles o banco LIMITA é pergunta para o
# modelo, não para esta lista: escrever «titulo está fora porque virou TEXT»
# aqui faria o teste parar de enxergar justamente o campo que causou o estouro,
# no dia em que alguém revertesse a coluna.
DO_VAULT = ("instituicao", "grupo", "titulo", "type_name", "url")


def _registros():
    if not CATALOGO.is_dir():
        pytest.skip(f"catálogo não está neste checkout ({CATALOGO})")
    return [r for r in fontes_vault.ler_pasta(CATALOGO) if not isinstance(r, fontes_vault.Ignorada)]


def test_o_catalogo_versionado_cabe_nas_colunas():
    """Nenhum campo LIMITADO do catálogo real passa do que o Postgres aceita."""
    registros = _registros()
    assert len(registros) > 1000, "o catálogo veio vazio — o teste não estaria conferindo nada"

    # Só os que a COLUNA limita. `titulo`, `descricao` e `dicas` são TEXT e
    # devolvem `None` aqui — se um deles voltar a ser VARCHAR, entra sozinho.
    limitados = {c: fs._limite(c) for c in DO_VAULT if fs._limite(c) is not None}
    assert limitados, "nenhum campo limitado — o teste não estaria conferindo nada"

    estouros: list[str] = []
    for registro in registros:
        for campo, limite in limitados.items():
            valor = getattr(registro, campo, None)
            if limite is not None and valor is not None and len(str(valor)) > limite:
                estouros.append(
                    f"{registro.instituicao}/{registro.type_name}: `{campo}` tem "
                    f"{len(str(valor))} caracteres, a coluna aceita {limite}"
                )

    assert not estouros, (
        f"{len(estouros)} registro(s) do catálogo não cabem no banco. O SQLite dos outros "
        f"testes aceita e o PostgreSQL recusa, abortando o LOTE inteiro da importação — foi "
        f"assim que 75 % do catálogo sumiu de produção. Primeiros casos:\n  "
        + "\n  ".join(estouros[:5])
    )


def test_o_titulo_de_fato_precisa_de_TEXT():
    """A premissa do `titulo` TEXT (scripts/init_schema.sql; a migração
    histórica `a3c81d7e2f46` fez a troca), presa contra o dado real.

    Se um dia o catálogo não tiver mais títulos longos, este teste cai — e aí a
    pergunta «ainda precisamos de TEXT?» merece ser feita de novo, em vez de a
    resposta continuar valendo por inércia.
    """
    registros = _registros()
    longos = [r for r in registros if r.titulo and len(r.titulo) > 255]
    assert longos, "nenhum título passa de 255 — reveja se TEXT ainda se justifica"
    assert FonteDeDados.__table__.c["titulo"].type.__class__.__name__ == "Text"
