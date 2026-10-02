# tests/test_workflow_happy_paths.py
"""
Testes de happy path para execução de workflow via executor direto.
Sem dependência de banco de dados, Redis ou Celery.
"""
import asyncio
from unittest.mock import MagicMock


def test_execute_workflow_via_executor():
    """
    Happy path: execução direta de um workflow mínimo via WorkflowExecutor.
    Usa um nó Merge que retorna dados simples — sem dependência de banco ou Celery.
    Nota: teste SÍNCRONO — roda `run()` com asyncio.run, como o executor faz no loop.
    """
    from flow.executor import WorkflowExecutor

    definition = {
        "nodes": [
            {
                "id": "merge-1",
                "type": "control",
                "name": "Merge",
                "properties": {
                    "strategy": "first",
                },
            }
        ],
        "edges": [],
    }

    publisher = MagicMock()
    publisher.publish_event = MagicMock()

    executor = WorkflowExecutor(definition, task_id="unit-test-task-001", publisher=publisher)
    asyncio.run(executor.run(initial_inputs={}))

    # Deve haver estatísticas do nó executado
    assert executor.node_stats["merge-1"]["status"] == "completed"
    # Publisher deve ter sido chamado ao menos uma vez (evento de início ou fim)
    assert publisher.publish_event.called
