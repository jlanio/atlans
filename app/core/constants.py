# app/core/constants.py
"""
Global constants of Atlas Studio.
Centralizes magic strings and fixed values used across multiple modules.
"""
from flow.utils.fuso import default_schedule_timezone

# ── node_stats ────────────────────────────────────────────────────────────────
# Reserved key inside the node_stats JSON for run-wide metadata.
# Format: WorkflowRun.node_stats["__run_meta__"] = {"retry_count": int, ...}
NODE_STATS_RUN_META_KEY = "__run_meta__"

# Internal node published at the end of each run to signal completion to the WebSocket.
WORKFLOW_COMPLETE_NODE = "__workflow_complete__"

# ── Redis TTLs (em segundos) ──────────────────────────────────────────────────
REDIS_TTL_1H  = 3_600       # 1 hour — workflow cache, tokens
REDIS_TTL_24H = 86_400      # 24 hours — run idempotency, refresh tokens

# ── Security headers ──────────────────────────────────────────────────────────
HSTS_MAX_AGE = 31_536_000   # 1 ano — Strict-Transport-Security max-age


# ── Scheduling ────────────────────────────────────────────────────────────────
# The timezone that applies when the schedule does not say which one is its own.
#
# There were THREE answers to that question, and they disagreed: the
# `ScheduleTrigger` node sent a fixed timezone, the `ScheduleBase` schema used another
# (same offset, different name) and the null column fell back to
# **UTC** inside the scheduler — four hours of difference, silently, between
# what the screen showed and the time the cron fired.
#
# Now it is a single value, and all three places import it. It comes from the environment
# (AGENDAMENTO_FUSO_PADRAO, read in `flow/utils/fuso.py`, which the node also uses),
# with UTC when the installation does not set it.
#
# Changing the value on an installation that already has schedules is NOT a detail:
# `timezone` is part of `_same_configuration` (`app/core/scheduling/hooks.py`),
# so the next save of each scheduled workflow without an explicit timezone recreates the
# schedule — which resets `next_run_at` and skips that day's occurrence. That is why the
# value is set before creating schedules, and a deploy can check that
# it is in the .env before starting up.
FUSO_PADRAO_DO_AGENDAMENTO = default_schedule_timezone()

# Ceiling on events kept in a run's history (`workflow:{run}:history`).
# The rpush was unbounded: a compromised (or buggy) executor could push
# messages of up to 16 MB in a loop and blow up Redis's memory — which also
# holds presence, the token blacklist and rate limit counters. The frontend only
# rebuilds the canvas from the recent events, so truncating the start is safe.
MAX_EVENTS_IN_HISTORY = 5000
