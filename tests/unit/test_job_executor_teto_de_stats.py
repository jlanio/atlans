# tests/unit/test_job_executor_teto_de_stats.py
"""Degraus do teto de 8 KB por stat de nó (executor/job_executor.py).

`output_columns` alimenta a sugestão de nome de coluna do editor. O corte
antigo o descartava POR INTEIRO no primeiro estouro — quanto mais larga a
tabela, mais certeira a perda, exatamente onde a sugestão mais vale. Os testes
fixam a escada de degradação: mensagem de erro truncada → cada lista de
colunas truncada às primeiras _MAX_STAT_COLUNAS_POR_PORTA → colunas
descartadas → só os campos essenciais. Cada degrau só executa se o anterior
não bastou.
"""
import json

from executor.job_executor import (
    _MAX_NODE_STAT_BYTES,
    _MAX_STAT_COLUNAS_POR_PORTA,
    _MAX_STAT_ERROR_CHARS,
    _STAT_CAMPOS_ESSENCIAIS,
    _limitar_node_stats,
    _reduzir_stat_de_no,
)


def _tamanho(obj) -> int:
    return len(json.dumps(obj, default=str))


def _stat_base(**extras) -> dict:
    stat = {
        "node_name": "No de Teste",
        "duration_ms": 12.5,
        "status": "completed",
        "cache_hit": False,
        "input_features": 10,
        "output_features": 10,
        "error": None,
        "started_at": "2026-01-01T00:00:00",
        "output_keys": ["result"],
    }
    stat.update(extras)
    return stat


def test_colunas_largas_sao_truncadas_e_nao_descartadas():
    """Tabela de censo: o stat estoura só de nomes de coluna.

    O comportamento antigo descartava output_columns inteiro; agora as
    primeiras _MAX_STAT_COLUNAS_POR_PORTA de CADA porta sobrevivem.
    """
    colunas = [f"variavel_censitaria_{i:04d}" for i in range(200)]
    stat = _stat_base(output_columns={"result": list(colunas), "aux": list(colunas)})
    assert _tamanho(stat) > _MAX_NODE_STAT_BYTES, "cenário precisa estourar o teto"

    reduzido = _reduzir_stat_de_no(stat)

    assert _tamanho(reduzido) <= _MAX_NODE_STAT_BYTES
    assert reduzido["__truncated__"] is True, "o corte usa a flag por stat existente"
    assert reduzido["output_columns"]["result"] == colunas[:_MAX_STAT_COLUNAS_POR_PORTA]
    assert reduzido["output_columns"]["aux"] == colunas[:_MAX_STAT_COLUNAS_POR_PORTA]
    # Sem item-marcador dentro da lista: cada entrada vira sugestão clicável.
    assert all(c in colunas for c in reduzido["output_columns"]["result"])
    # O stat original do executor não pode ser mutado pelo corte.
    assert len(stat["output_columns"]["result"]) == 200


def test_erro_gigante_e_truncado_sem_custar_as_colunas():
    """Degrau 1: se truncar a mensagem de erro basta, as colunas ficam intactas."""
    colunas = [f"col_{i}" for i in range(30)]
    stat = _stat_base(error="x" * 20_000, output_columns={"result": list(colunas)})
    assert _tamanho(stat) > _MAX_NODE_STAT_BYTES

    reduzido = _reduzir_stat_de_no(stat)

    assert _tamanho(reduzido) <= _MAX_NODE_STAT_BYTES
    assert reduzido["error"] == "x" * _MAX_STAT_ERROR_CHARS + "…[truncado]"
    assert reduzido["output_columns"] == {"result": colunas}, "colunas não podiam cair aqui"
    assert reduzido["__truncated__"] is True


def test_colunas_caem_por_inteiro_so_quando_nem_truncadas_cabem():
    """Degrau 3: lastro alheio ocupa quase todo o teto — truncar não basta, descartar sim."""
    colunas = [f"col_{i:04d}" for i in range(_MAX_STAT_COLUNAS_POR_PORTA * 2)]
    stat = _stat_base(output_columns={"result": colunas})
    sem_colunas = dict(stat)
    sem_colunas.pop("output_columns")
    # Dimensionado para: sem colunas cabe (com ~200 bytes de folga para a chave
    # do lastro e a flag), mas nem as 50 primeiras colunas (~550 bytes) cabem.
    stat["lastro"] = "z" * (_MAX_NODE_STAT_BYTES - _tamanho(sem_colunas) - 200)
    assert _tamanho(stat) > _MAX_NODE_STAT_BYTES

    reduzido = _reduzir_stat_de_no(stat)

    assert _tamanho(reduzido) <= _MAX_NODE_STAT_BYTES
    assert "output_columns" not in reduzido
    assert reduzido["__truncated__"] is True
    # Parou no degrau do descarte: não colapsou para os campos essenciais.
    assert "lastro" in reduzido


def test_ultimo_recurso_continua_sendo_so_os_campos_essenciais():
    """Degrau 4: nem o pop resolve — sobra o mínimo que desenha a linha no painel."""
    stat = _stat_base(
        lastro="z" * (_MAX_NODE_STAT_BYTES * 2),
        output_columns={"result": [f"col_{i}" for i in range(120)]},
    )

    reduzido = _reduzir_stat_de_no(stat)

    assert _tamanho(reduzido) <= _MAX_NODE_STAT_BYTES
    assert "lastro" not in reduzido and "output_columns" not in reduzido
    assert reduzido["__truncated__"] is True
    esperados = {k for k in _STAT_CAMPOS_ESSENCIAIS if k in stat} | {"__truncated__"}
    assert set(reduzido) == esperados


def test_limitar_node_stats_entrega_as_colunas_truncadas_ao_resultado():
    """O caminho real (job_result → servidor) recebe o stat degradado, não podado."""
    colunas = [f"variavel_censitaria_{i:04d}" for i in range(200)]
    node_stats = {"n1": _stat_base(
        output_columns={"result": list(colunas), "aux": list(colunas)},
    )}
    assert _tamanho(node_stats["n1"]) > _MAX_NODE_STAT_BYTES

    limitado = _limitar_node_stats(node_stats)

    assert limitado["n1"]["output_columns"]["result"] == colunas[:_MAX_STAT_COLUNAS_POR_PORTA]
    assert limitado["n1"]["__truncated__"] is True
