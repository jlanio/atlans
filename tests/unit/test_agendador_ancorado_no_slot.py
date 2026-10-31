"""
Next run computed from the slot that fired (app/core/async_scheduler.py):
no drift for intervals, one firing per wall-clock time when DST ends.
"""
from datetime import datetime, timedelta
from types import SimpleNamespace

from app.core.async_scheduler import AsyncScheduler


def _sched(**campos):
    base = dict(strategy="cron", cron_expression=None, interval=None, unit=None,
                rrule_expression=None, timezone="UTC", job_id="s1")
    base.update(campos)
    return SimpleNamespace(**base)


def test_an_interval_keeps_its_cadence_when_the_tick_is_late():
    s = _sched(strategy="interval", interval=1, unit="minutes")
    slot = datetime(2026, 11, 1, 10, 0, 0)
    tick = slot + timedelta(seconds=29)          # the loop runs every 30 s
    assert AsyncScheduler()._next_after_fire(s, slot, tick) == datetime(2026, 11, 1, 10, 1, 0)


def test_missed_interval_slots_collapse_into_one_future_run():
    s = _sched(strategy="interval", interval=10, unit="minutes")
    slot = datetime(2026, 11, 1, 10, 0, 0)
    agora = datetime(2026, 11, 1, 13, 7, 0)      # the API was down for 3 h
    proximo = AsyncScheduler()._next_after_fire(s, slot, agora)
    assert proximo == datetime(2026, 11, 1, 13, 10, 0)


def test_cron_fires_once_when_the_clocks_go_back():
    # 2026-11-01 01:30 happens twice in New York (EDT 05:30 UTC, then EST 06:30 UTC).
    s = _sched(cron_expression="30 1 * * *", timezone="America/New_York")
    slot = datetime(2026, 11, 1, 5, 30)          # the first 01:30 (EDT)
    proximo = AsyncScheduler()._next_after_fire(s, slot, slot + timedelta(seconds=20))
    assert proximo == datetime(2026, 11, 2, 6, 30)   # next day 01:30 EST, not 06:30 today


def test_cron_that_missed_slots_does_not_fire_in_the_past():
    s = _sched(cron_expression="0 * * * *")
    slot = datetime(2026, 11, 1, 1, 0)
    agora = datetime(2026, 11, 1, 5, 20)
    assert AsyncScheduler()._next_after_fire(s, slot, agora) == datetime(2026, 11, 1, 6, 0)


def test_an_hourly_cron_fires_in_the_repeated_hour_too():
    # 2026-11-01 01:00 happens twice in New York (05:00 and 06:00 UTC). An hourly
    # schedule fires in both, like cron: skipping the second left a 2-hour gap.
    s = _sched(cron_expression="0 * * * *", timezone="America/New_York")
    slot = datetime(2026, 11, 1, 5, 0)           # the first 01:00 (EDT)
    proximo = AsyncScheduler()._next_after_fire(s, slot, slot + timedelta(seconds=20))
    assert proximo == datetime(2026, 11, 1, 6, 0)   # the second 01:00 (EST)


def test_which_schedules_name_their_hour():
    fixo = AsyncScheduler._fires_at_a_fixed_hour
    assert fixo(_sched(cron_expression="30 1 * * *")) is True
    assert fixo(_sched(cron_expression="0 1,13 * * *")) is True
    assert fixo(_sched(cron_expression="0 * * * *")) is False
    assert fixo(_sched(cron_expression="*/5 */2 * * *")) is False
    assert fixo(_sched(cron_expression="0 9-17 * * 1-5")) is False
    assert fixo(_sched(strategy="rrule", rrule_expression="FREQ=DAILY;BYHOUR=1")) is True
    assert fixo(_sched(strategy="rrule", rrule_expression="FREQ=HOURLY")) is False
