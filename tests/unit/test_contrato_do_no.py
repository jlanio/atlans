# tests/unit/test_contrato_do_no.py
"""O description() de um nó é validado NA IMPORTAÇÃO (A14).

O campo `type` acumulava três papéis (categoria do nó, tipo de campo de
saída, widget de propriedade) e nenhum era conferido: um typo passava mudo
pelo registro e virava defeito visual longe da causa — nó sem ícone, campo
sem editor, porta sem tipo. Agora `register_node` chama
`validar_description` e o nó malformado morre no CI com a causa exata.
"""
import pytest

from flow.nodes.base import BaseNode
from flow.nodes.contrato import (
    CATEGORIAS,
    CHAVES_DO_DESCRIPTION,
    TIPOS_DE_CAMPO,
    TIPOS_DE_PROPRIEDADE,
    validar_description,
)
from flow.registry import NODE_REGISTRY, register_node


def _desc(**mudancas):
    base = {
        "name": "NoDeTeste",
        "alias": "Nó de Teste",
        "description": "Só para o contrato.",
        "type": "action",
        "properties": [
            {"name": "campo", "type": "string", "default": "", "description": "x"},
        ],
        "outputs": [
            {"name": "output", "type": "geodataframe", "description": "resultado"},
        ],
    }
    base.update(mudancas)
    return base


# ── validar_description (puro) ───────────────────────────────────────────────

def test_description_valido_passa():
    validar_description(_desc())


def test_categoria_fora_do_vocabulario_e_recusada():
    with pytest.raises(ValueError, match="categoria.*'transform'"):
        validar_description(_desc(type="transform"))


def test_chave_desconhecida_no_topo_e_recusada():
    # O typo clássico: 'output' (singular) em vez de 'outputs' — antes o campo
    # simplesmente deixava de existir para o editor.
    with pytest.raises(ValueError, match="chaves desconhecidas.*output"):
        d = _desc()
        d["output"] = d.pop("outputs")
        validar_description(d)


def test_tipo_de_propriedade_invalido_e_recusado():
    with pytest.raises(ValueError, match="propriedade 'campo' com type inválido: 'texto'"):
        validar_description(_desc(properties=[{"name": "campo", "type": "texto"}]))


def test_select_sem_options_e_recusado():
    with pytest.raises(ValueError, match="select sem 'options'"):
        validar_description(_desc(properties=[{"name": "modo", "type": "select"}]))


def test_credential_sem_tipos_e_recusado():
    with pytest.raises(ValueError, match="credential sem 'credential_types'"):
        validar_description(_desc(properties=[{"name": "cred", "type": "credential"}]))


def test_campo_de_saida_sem_type_e_recusado():
    # A regra que o A13 institui: campo de saída SEM tipo não entra mais.
    with pytest.raises(ValueError, match="campo de saída 'output' com type inválido: None"):
        validar_description(_desc(outputs=[{"name": "output"}]))


def test_campo_de_saida_com_chave_estranha_e_recusado():
    with pytest.raises(ValueError, match="campo de saída 'output' com chaves desconhecidas"):
        validar_description(_desc(outputs=[
            {"name": "output", "type": "any", "porta": True},
        ]))


def test_flag_que_nao_e_bool_e_recusada():
    with pytest.raises(ValueError, match="'branches' deve ser bool"):
        validar_description(_desc(branches="true"))


def test_nome_com_espaco_e_recusado():
    with pytest.raises(ValueError, match="sem espaços"):
        validar_description(_desc(name="No De Teste"))


# ── register_node aplica a validação na importação ───────────────────────────

def test_register_node_recusa_no_malformado():
    class NoTorto(BaseNode):
        @classmethod
        def description(cls):
            return _desc(name="NoTorto", type="transform")

        async def execute(self, inputs):  # pragma: no cover
            return {}

    with pytest.raises(ValueError, match="NoTorto.*categoria"):
        register_node(NoTorto)
    assert "NoTorto" not in NODE_REGISTRY


def test_register_node_registra_no_valido():
    class NoReto(BaseNode):
        @classmethod
        def description(cls):
            return _desc(name="NoReto")

        async def execute(self, inputs):  # pragma: no cover
            return {}

    try:
        register_node(NoReto)
        assert NODE_REGISTRY["NoReto"] is NoReto
    finally:
        NODE_REGISTRY.pop("NoReto", None)


# ── O catálogo real inteiro respeita o contrato ──────────────────────────────

def test_os_63_nos_do_catalogo_passam_no_contrato():
    assert len(NODE_REGISTRY) >= 63
    for nome, cls in NODE_REGISTRY.items():
        validar_description(cls.description())


def test_vocabularios_sao_fechados_e_documentados():
    """Os três papéis do antigo 'type', agora com vocabulário próprio."""
    assert CATEGORIAS == {"trigger", "action", "spatial", "datasource", "output", "control"}
    assert "geodataframe" in TIPOS_DE_CAMPO and "select" not in TIPOS_DE_CAMPO
    assert "select" in TIPOS_DE_PROPRIEDADE and "geodataframe" not in TIPOS_DE_PROPRIEDADE
    assert "outputs" in CHAVES_DO_DESCRIPTION and "static_output" not in CHAVES_DO_DESCRIPTION
