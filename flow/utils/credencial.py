# flow/utils/credencial.py
#
# Reading of the database credential already resolved in the node's parameters.
#
# The executor never sees the credential: the server swaps `credential_id` for
# the DSN (`connectionString`) when building the job envelope, and removes the
# id. All that is left here is checking whether that swap happened.
#
# The check was repeated in each node, always as "'connectionString' é
# obrigatório (deve ser resolvido antes da execução)". The sentence describes a
# SERVER problem in the shape of a node configuration error — and the two
# possible causes call for opposite actions: picking a credential in the editor,
# or investigating why the server did not inject it. Telling the two apart is
# the reason for this module.
from typing import Any, Dict


def get_connection(parameters: Dict[str, Any]) -> str:
    """The node's connection DSN, or an error saying which of the two things was missing."""
    conn = str(parameters.get("connectionString") or "").strip()
    if conn:
        return conn

    # A present `credential_id` is the trace that the server did NOT do the swap:
    # `inject_credentials` removes the id precisely when injecting the DSN.
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
