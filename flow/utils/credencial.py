# flow/utils/credencial.py
#
# Leitura da credencial de banco já resolvida nos parâmetros do nó.
#
# O executor nunca vê a credencial: o servidor troca `credential_id` pelo DSN
# (`connectionString`) ao montar o envelope do job, e remove o id. Aqui só
# sobra checar se essa troca aconteceu.
#
# A checagem existia repetida em cada nó, sempre como "'connectionString' é
# obrigatório (deve ser resolvido antes da execução)". A frase descreve um
# problema do SERVIDOR com a forma de um erro de configuração do nó — e as duas
# causas possíveis pedem ações opostas: escolher uma credencial no editor, ou
# investigar por que o servidor não a injetou. Distinguir as duas é o motivo
# deste módulo.
from typing import Any, Dict


def obter_conexao(parameters: Dict[str, Any]) -> str:
    """DSN de conexão do nó, ou erro dizendo qual das duas coisas faltou."""
    conn = str(parameters.get("connectionString") or "").strip()
    if conn:
        return conn

    # `credential_id` presente é o rastro de que o servidor NÃO fez a troca:
    # `inject_credentials` remove o id justamente ao injetar o DSN.
    if str(parameters.get("credential_id") or "").strip():
        raise ValueError(
            "A credencial está selecionada no nó, mas o servidor não a resolveu "
            "antes de despachar a execução — chegou aqui só o id, sem a conexão. "
            "Confira se a credencial ainda existe e pertence ao workspace deste "
            "workflow."
        )

    raise ValueError(
        "Nenhuma credencial de banco selecionada neste nó. Escolha uma no campo "
        "'Credencial' da configuração do nó."
    )
