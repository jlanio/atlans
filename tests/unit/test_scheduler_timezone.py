# tests/unit/test_scheduler_timezone.py
"""O cron do agendamento tem de disparar no fuso configurado.

`schedules.timezone` era gravado pelo nó ScheduleTrigger e nunca lido: o
_compute_next rodava sobre UTC naive, entao "0 13 * * *" disparava as 13h UTC —
9h em America/Cuiaba. Quem escolhia o horario na UI nunca via o workflow rodar
na hora certa, e a diferenca (4h) passava por "o agendamento nao funciona".
"""
from datetime import datetime
from unittest.mock import MagicMock

from app.core.async_scheduler import AsyncScheduler
from app.core.constants import FUSO_PADRAO_DO_AGENDAMENTO


def _sched(**kwargs) -> MagicMock:
    base = {
        "job_id": "job-1",
        "strategy": "cron",
        "cron_expression": "0 13 * * *",
        "interval": None,
        "unit": None,
        "rrule_expression": None,
        "timezone": "America/Cuiaba",   # UTC-4, sem horario de verao
    }
    base.update(kwargs)
    return MagicMock(**base)


def test_cron_dispara_no_fuso_do_schedule():
    """13h em Cuiaba (UTC-4) = 17h UTC, que e como o next_run_at e gravado."""
    # 04/08 as 12:00 UTC = 08:00 em Cuiaba, antes do horario do cron.
    proximo = AsyncScheduler()._compute_next(_sched(), datetime(2026, 8, 4, 12, 0))

    assert proximo == datetime(2026, 8, 4, 17, 0)


def test_cron_em_utc_permanece_em_utc():
    """Sem deslocamento quando o schedule ja esta em UTC — evita 'correcao' dupla."""
    proximo = AsyncScheduler()._compute_next(
        _sched(timezone="UTC"), datetime(2026, 8, 4, 12, 0),
    )

    assert proximo == datetime(2026, 8, 4, 13, 0)


def test_cron_avanca_para_o_dia_seguinte_no_fuso_local():
    """18h UTC = 14h local: o horario local ja passou, proximo e amanha."""
    proximo = AsyncScheduler()._compute_next(_sched(), datetime(2026, 8, 4, 18, 0))

    assert proximo == datetime(2026, 8, 5, 17, 0)


def test_timezone_invalido_cai_no_padrao_sem_derrubar_o_agendamento():
    """O fallback era UTC, e isso nao era escolha — era o default do `datetime`.

    Todo o resto do produto opera em UTC-4 (o no `ScheduleTrigger` e o schema),
    entao um schedule sem fuso legivel disparava QUATRO HORAS depois do que a
    tela dizia, sem nada que explicasse a diferenca. O aviso no log continua:
    ali alguem digitou algo e merece saber que nao pegou.
    """
    proximo = AsyncScheduler()._compute_next(
        _sched(timezone="Marte/Olympus"), datetime(2026, 8, 4, 12, 0),
    )

    # 13h no fuso padrao (UTC-4) = 17h UTC.
    assert proximo == datetime(2026, 8, 4, 17, 0)


def test_timezone_vazio_cai_no_padrao():
    """A pergunta que o fallback responde e uma so — "nao sei o fuso deste
    agendamento, qual uso?" — entao as duas saidas dela dao no mesmo lugar."""
    proximo = AsyncScheduler()._compute_next(
        _sched(timezone=None), datetime(2026, 8, 4, 12, 0),
    )

    assert proximo == datetime(2026, 8, 4, 17, 0)


def test_o_fuso_padrao_do_fallback_e_o_do_produto():
    """Prende o fallback a constante, e nao a um literal repetido aqui.

    Sem isto, mudar a constante deixaria estes dois testes afirmando um horario
    que nao e mais o do produto — e eles continuariam verdes ate alguem reparar.
    """
    from zoneinfo import ZoneInfo
    from unittest.mock import MagicMock as _M

    tz = AsyncScheduler()._tz_of(_M(timezone=None, job_id="j"))

    assert tz == ZoneInfo(FUSO_PADRAO_DO_AGENDAMENTO)


def test_intervalo_ignora_fuso():
    """Soma de delta nao depende de fuso — nao pode ser deslocada."""
    proximo = AsyncScheduler()._compute_next(
        _sched(strategy="interval", cron_expression=None, interval=30, unit="minutes"),
        datetime(2026, 8, 4, 12, 0),
    )

    assert proximo == datetime(2026, 8, 4, 12, 30)


def test_rrule_tambem_respeita_o_fuso():
    """BYHOUR de uma rrule tambem e hora local."""
    proximo = AsyncScheduler()._compute_next(
        _sched(
            strategy="rrule",
            cron_expression=None,
            rrule_expression="FREQ=DAILY;BYHOUR=13;BYMINUTE=0;BYSECOND=0",
        ),
        datetime(2026, 8, 4, 12, 0),
    )

    assert proximo == datetime(2026, 8, 4, 17, 0)


def test_cron_invalido_nao_levanta():
    assert AsyncScheduler()._compute_next(
        _sched(cron_expression="nao e um cron"), datetime(2026, 8, 4, 12, 0),
    ) is None
