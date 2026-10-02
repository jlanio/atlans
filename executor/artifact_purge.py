# executor/artifact_purge.py
"""
Remocao de artefatos locais por ordem do servidor (retencao).

Artefatos marcados com `keepLocal` moram apenas no disco do executor — o
servidor guarda so o catalogo. Quando a retencao expira, quem tem de apagar o
arquivo e esta maquina, porque o servidor nao tem acesso a ele.

## Modelo de ameaca

A ordem chega pela rede, num `control` que o `connection.py` so aceita com
assinatura Ed25519 valida do servidor. Ainda assim, o caminho de cada arquivo e
tratado como entrada HOSTIL:

  - o caminho e montado a partir da raiz LOCAL (`artifacts_root()`), nunca de um
    valor recebido;
  - o resultado e confinado a essa raiz com `resolve()` + `is_relative_to`;
  - `..`, caminho absoluto e letra de unidade sao recusados antes de qualquer
    coisa.

Sem isso, `local_path = "../../../../Windows/System32/config/SAM"` transformaria
a limpeza por retencao num apagador de arquivos arbitrarios — e o servidor
comprometido, ou qualquer bug de derivacao no lado dele, viraria perda de dados
na maquina do cliente.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger("executor.artifact_purge")


def _seguro(bruto: str) -> bool:
    """Rejeita o que nem deveria chegar ate a resolucao de caminho."""
    if not bruto or not isinstance(bruto, str):
        return False
    normalizado = bruto.replace("\\", "/")
    if normalizado.startswith("/"):
        return False                      # absoluto POSIX
    if len(bruto) >= 2 and bruto[1] == ":":
        return False                      # 'C:\...' — absoluto Windows
    if ".." in normalizado.split("/"):
        return False                      # travessia explicita
    return True


def _sob_a_raiz(local_path: str, raiz: Path) -> Path | None:
    """Resolve `local_path` sob uma raiz JA resolvida, ou None se escapar dela."""
    if not _seguro(local_path):
        return None

    alvo = (raiz / local_path).resolve()
    # Segunda barreira, depois do resolve(): cobre symlink apontando para fora,
    # que a checagem textual acima nao pega.
    if not alvo.is_relative_to(raiz):
        return None
    return alvo


def _limpar_diretorios_vazios(caminho: Path, raiz: Path) -> None:
    """Sobe removendo diretorios que ficaram vazios, sem passar da raiz.

    Sem isto, `artifacts/` acumula uma arvore `<workspace>/<run>/` vazia por
    execucao, para sempre.
    """
    pai = caminho.parent
    while pai != raiz and pai.is_relative_to(raiz):
        try:
            pai.rmdir()          # so remove se estiver vazio
        except OSError:
            return
        pai = pai.parent


def purgar(itens: list) -> int:
    """Apaga os artefatos pedidos. Devolve quantos foram removidos.

    Nunca levanta: uma falha de limpeza nao pode derrubar a conexao com o
    servidor nem interromper jobs em andamento.
    """
    from flow.utils.artifact_helpers import artifacts_root

    if not isinstance(itens, list):
        return 0

    raiz = Path(artifacts_root()).resolve()
    removidos = 0

    for item in itens:
        if not isinstance(item, dict):
            continue
        local_path = item.get("local_path") or ""
        id_hash = item.get("id_hash") or "?"

        # A raiz e resolvida UMA vez para o lote inteiro: `purgar` roda no laco
        # de recepcao do WebSocket, e uma ordem de retencao com centenas de
        # artefatos pagava um `resolve()` da raiz por item — syscall repetida
        # segurando o loop que tambem entrega os jobs.
        alvo = _sob_a_raiz(local_path, raiz)
        if alvo is None:
            # Recusa RUIDOSA: se isto acontece, ou o servidor esta com um bug de
            # derivacao de caminho, ou alguem esta tentando algo.
            logger.error(
                "Ordem de remocao RECUSADA para o artefato %s: caminho %r sai do "
                "diretorio de artefatos.", id_hash, local_path,
            )
            continue

        try:
            if alvo.is_file():
                os.unlink(alvo)
                removidos += 1
                _limpar_diretorios_vazios(alvo, raiz)
            # Arquivo ausente nao e erro: ja foi apagado a mao, ou a ordem
            # anterior chegou e o servidor nao registrou a confirmacao.
        except OSError as exc:
            logger.warning("Falha ao remover o artefato local %s (%s): %s", id_hash, alvo, exc)

    return removidos
