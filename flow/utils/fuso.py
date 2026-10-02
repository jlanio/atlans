# flow/utils/fuso.py
"""
O fuso padrão dos agendamentos: o que vale quando o agendamento não diz o seu.

Vem do ambiente (AGENDAMENTO_FUSO_PADRAO), com UTC quando ninguém o definiu. Mora
em `flow/` porque os dois lados precisam do MESMO valor e só este pacote é
comum aos dois: o nó ScheduleTrigger (o executor empacota `flow/` sem `app/`) e
o servidor (`app/core/constants.py`). Divergir faria o próximo save de cada
workflow agendado recriar o schedule — ver a constante no servidor.

Só a biblioteca padrão: o módulo é importado no arranque dos dois processos.
"""
from __future__ import annotations

import os
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

FUSO_DE_RESERVA = "UTC"

# Arquivos da base de fusos que o zoneinfo abre, mas que não são fuso: o
# navegador não os conhece, e a tela mostraria um fuso que não sabe desenhar.
_NAO_SAO_FUSOS = frozenset({"localtime", "posixrules", "Factory"})


def fuso_padrao_do_agendamento() -> str:
    """AGENDAMENTO_FUSO_PADRAO (um fuso IANA), ou UTC quando vazia.

    Um valor que não é fuso PARA o arranque, em vez de cair em UTC: numa
    instalação com agendamentos, um erro de digitação valendo UTC recriaria, no
    próximo save, cada agendamento sem fuso explícito — horas fora do lugar, sem
    nada que explicasse. Como a origem CORS inválida em `app/core/config.py`.
    """
    valor = os.getenv("AGENDAMENTO_FUSO_PADRAO", "").strip()
    if not valor:
        return FUSO_DE_RESERVA
    erro = ValueError(
        f"AGENDAMENTO_FUSO_PADRAO={valor!r} não é um fuso IANA (ex.: America/Sao_Paulo, Europe/Lisbon, UTC)."
    )
    if valor in _NAO_SAO_FUSOS:
        raise erro
    try:
        ZoneInfo(valor)
    # OSError: um nome de pasta da base ("America") abre um diretório.
    except (ZoneInfoNotFoundError, ValueError, OSError) as exc:
        raise erro from exc
    return valor
