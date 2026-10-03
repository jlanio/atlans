# tests/unit/test_scheduler_timezone.py
"""The schedule's cron has to fire in the configured time zone.

`schedules.timezone` was written by the ScheduleTrigger node and never read:
_compute_next ran on naive UTC, so "0 13 * * *" fired at 13:00 UTC — 9:00 in
America/Cuiaba. Whoever picked the time in the UI never saw the workflow run at
the right time, and the difference (4h) passed for "scheduling does not work".
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
        "timezone": "America/Cuiaba",   # UTC-4, no daylight saving time
    }
    base.update(kwargs)
    return MagicMock(**base)


def test_cron_fires_in_the_schedule_timezone():
    """13:00 in Cuiaba (UTC-4) = 17:00 UTC, which is how next_run_at is stored."""
    # 08-04 at 12:00 UTC = 08:00 in Cuiaba, before the cron time.
    proximo = AsyncScheduler()._compute_next(_sched(), datetime(2026, 8, 4, 12, 0))

    assert proximo == datetime(2026, 8, 4, 17, 0)


def test_cron_in_utc_stays_in_utc():
    """No offset when the schedule is already in UTC — avoids a double 'correction'."""
    proximo = AsyncScheduler()._compute_next(
        _sched(timezone="UTC"), datetime(2026, 8, 4, 12, 0),
    )

    assert proximo == datetime(2026, 8, 4, 13, 0)


def test_cron_advances_to_the_next_day_in_local_timezone():
    """18h UTC = 14h local: o horario local ja passou, proximo e amanha."""
    proximo = AsyncScheduler()._compute_next(_sched(), datetime(2026, 8, 4, 18, 0))

    assert proximo == datetime(2026, 8, 5, 17, 0)


def test_invalid_timezone_falls_back_to_default_without_breaking_the_schedule():
    """The fallback was UTC, and that was not a choice — it was the `datetime` default.

    The whole rest of the product operates in UTC-4 (the `ScheduleTrigger` node
    and the schema), so a schedule without a readable time zone fired FOUR HOURS
    later than the screen said, with nothing to explain the difference. The log
    warning stays: someone typed something there and deserves to know it did not take.
    """
    proximo = AsyncScheduler()._compute_next(
        _sched(timezone="Marte/Olympus"), datetime(2026, 8, 4, 12, 0),
    )

    # 13h no fuso padrao (UTC-4) = 17h UTC.
    assert proximo == datetime(2026, 8, 4, 17, 0)


def test_empty_timezone_falls_back_to_default():
    """The question the fallback answers is a single one — "I don't know this
    schedule's time zone, which one do I use?" — so both of its exits end up in the same place."""
    proximo = AsyncScheduler()._compute_next(
        _sched(timezone=None), datetime(2026, 8, 4, 12, 0),
    )

    assert proximo == datetime(2026, 8, 4, 17, 0)


def test_the_fallback_default_timezone_is_the_products():
    """Ties the fallback to the constant, not to a literal repeated here.

    Without this, changing the constant would leave these two tests asserting a
    time that is no longer the product's — and they would stay green until someone noticed.
    """
    from zoneinfo import ZoneInfo
    from unittest.mock import MagicMock as _M

    tz = AsyncScheduler()._tz_of(_M(timezone=None, job_id="j"))

    assert tz == ZoneInfo(FUSO_PADRAO_DO_AGENDAMENTO)


def test_interval_ignores_timezone():
    """Adding a delta does not depend on the time zone — it must not be shifted."""
    proximo = AsyncScheduler()._compute_next(
        _sched(strategy="interval", cron_expression=None, interval=30, unit="minutes"),
        datetime(2026, 8, 4, 12, 0),
    )

    assert proximo == datetime(2026, 8, 4, 12, 30)


def test_rrule_also_respects_the_timezone():
    """An rrule's BYHOUR is local time too."""
    proximo = AsyncScheduler()._compute_next(
        _sched(
            strategy="rrule",
            cron_expression=None,
            rrule_expression="FREQ=DAILY;BYHOUR=13;BYMINUTE=0;BYSECOND=0",
        ),
        datetime(2026, 8, 4, 12, 0),
    )

    assert proximo == datetime(2026, 8, 4, 17, 0)


def test_invalid_cron_does_not_raise():
    assert AsyncScheduler()._compute_next(
        _sched(cron_expression="nao e um cron"), datetime(2026, 8, 4, 12, 0),
    ) is None
