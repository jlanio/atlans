#!/usr/bin/env python3
"""scripts/repo_metrics.py — the repository's public adoption numbers, without telemetry.

Answers "how many people reached Atlans this month?" with a number and its
source, using only the GitHub REST API. A weekly Paperclip routine runs it; the
history lives in a Paperclip document, not in the repository: the routine
passes the previous history in and keeps the one written out.

    python scripts/repo_metrics.py --repo jlanio/atlans \\
        --history in.json --out-history out.json --out-report report.md \\
        [--month YYYY-MM]

- `--history` is optional (the first run has none).
- The token comes ONLY from the ATLANS_METRICS_TOKEN environment variable. It
  is sent in the Authorization header and never written to a file or a log.
- The traffic endpoints (views, clones, referrers) need a token with push
  access. Without one, or with 401/403, the traffic is "unavailable" — never 0 —
  and the rest of the report goes on. GitHub keeps only 14 days of traffic: the
  daily series are merged by date into the history, the new value replacing the
  old one for a repeated date, so the history goes back further than GitHub.
- The listing of stargazers with their dates also needs a token nowadays (401
  without one): the total stars still come from /repos.

Standard library only; runs on any system.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.github.com"
TOKEN_ENV = "ATLANS_METRICS_TOKEN"
HISTORY_VERSION = 1
PER_PAGE = 100
LABELS = ("bug", "question", "enhancement")
TOP_REFERRERS = 10

UNAVAILABLE = "unavailable"
OK = "ok"

_NEXT = re.compile(r'<([^>]+)>;\s*rel="next"')


class Unavailable(Exception):
    """The endpoint answered 401/403: it needs a token, or a token with more access."""

    def __init__(self, status: int):
        super().__init__(f"HTTP {status}")
        self.status = status


def urllib_fetch(url: str, headers: dict[str, str]) -> tuple[int, dict[str, str], bytes]:
    """GET `url`: `(status, headers, body)`. 4xx/5xx come back as a status, not an exception."""
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, dict(resp.headers.items()), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers.items()) if e.headers else {}, e.read() or b""


class GitHub:
    def __init__(self, token: str | None, fetch=urllib_fetch):
        self._token = token
        self._fetch = fetch

    @property
    def has_token(self) -> bool:
        return bool(self._token)

    def _headers(self, accept: str) -> dict[str, str]:
        h = {
            "Accept": accept,
            "User-Agent": "atlans-repo-metrics",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    def _get(self, url: str, accept: str):
        status, headers, body = self._fetch(url, self._headers(accept))
        if status in (401, 403):
            raise Unavailable(status)
        if status != 200:
            # The URL only: the request headers carry the token.
            raise RuntimeError(f"GitHub respondeu HTTP {status} em {url}")
        link = next((v for k, v in headers.items() if k.lower() == "link"), "")
        return json.loads(body.decode("utf-8")), link

    def get(self, path: str, accept: str = "application/vnd.github+json"):
        data, _ = self._get(f"{API}{path}", accept)
        return data

    def paginate(self, path: str, accept: str = "application/vnd.github+json") -> list:
        sep = "&" if "?" in path else "?"
        url: str | None = f"{API}{path}{sep}per_page={PER_PAGE}"
        items: list = []
        while url:
            data, link = self._get(url, accept)
            items.extend(data)
            m = _NEXT.search(link)
            url = m.group(1) if m else None
        return items


# ── Collection ────────────────────────────────────────────────────────────────


def _day(ts: str) -> str:
    """`2026-10-03T12:00:00Z` → `2026-10-03`."""
    return ts[:10]


def _unavailable(gh: GitHub, e: Unavailable) -> dict:
    reason = "sem token" if not gh.has_token else f"token sem acesso: HTTP {e.status}"
    return {"status": UNAVAILABLE, "reason": reason}


def collect(gh: GitHub, repo: str) -> dict:
    """Everything the API gives now. Nothing here depends on the history."""
    r = f"/repos/{repo}"
    info = gh.get(r)
    owner = info["owner"]["login"]
    out: dict = {
        "owner": owner,
        "totals": {
            "stars": info["stargazers_count"],
            "forks": info["forks_count"],
            # `watchers_count` is the star count again (a legacy name);
            # the people watching the repository are `subscribers_count`.
            "watchers": info.get("subscribers_count", 0),
        },
    }

    try:
        stars = gh.paginate(f"{r}/stargazers", accept="application/vnd.github.star+json")
        out["stars"] = {"status": OK, "dates": sorted(_day(s["starred_at"]) for s in stars)}
    except Unavailable as e:
        out["stars"] = _unavailable(gh, e)

    forks = gh.paginate(f"{r}/forks?sort=oldest")
    out["forks"] = sorted(_day(f["created_at"]) for f in forks)

    issues = gh.paginate(f"{r}/issues?state=all")
    out["issues"] = sorted(
        (
            {
                "number": i["number"],
                "kind": "pr" if "pull_request" in i else "issue",
                "created": _day(i["created_at"]),
                "author": i["user"]["login"],
                "bot": i["user"].get("type") == "Bot",
                "labels": sorted(lbl["name"] for lbl in i.get("labels", [])),
            }
            for i in issues
        ),
        key=lambda i: i["number"],
    )

    releases = gh.paginate(f"{r}/releases")
    out["downloads"] = sum(a.get("download_count", 0) for rel in releases for a in rel.get("assets", []))

    for kind in ("views", "clones"):
        if not gh.has_token:
            out[kind] = {"status": UNAVAILABLE, "reason": "sem token"}
            continue
        try:
            data = gh.get(f"{r}/traffic/{kind}?per=day")
            out[kind] = {
                "status": OK,
                "daily": {
                    _day(d["timestamp"]): {"count": d["count"], "uniques": d["uniques"]}
                    for d in data.get(kind, [])
                },
            }
        except Unavailable as e:
            out[kind] = _unavailable(gh, e)

    if not gh.has_token:
        out["referrers"] = {"status": UNAVAILABLE, "reason": "sem token"}
    else:
        try:
            refs = gh.get(f"{r}/traffic/popular/referrers")
            out["referrers"] = {"status": OK, "items": refs}
        except Unavailable as e:
            out["referrers"] = _unavailable(gh, e)
    return out


# ── History ───────────────────────────────────────────────────────────────────


def empty_history(repo: str) -> dict:
    return {
        "version": HISTORY_VERSION,
        "repo": repo,
        "traffic": {
            "views": {"status": UNAVAILABLE, "daily": {}},
            "clones": {"status": UNAVAILABLE, "daily": {}},
            "referrers": {"status": UNAVAILABLE},
        },
        "snapshots": {},
    }


def merge(history: dict | None, current: dict, repo: str, collected_at: str) -> dict:
    """The new history: the old one with this collection on top.

    The traffic daily series are merged by date (the new value wins), and a
    collection without traffic keeps the days already known — it only marks
    the status as unavailable. The totals go in a snapshot per UTC day, so two
    runs on the same day replace each other instead of piling up."""
    new = empty_history(repo)
    if history:
        old_traffic = history.get("traffic", {})
        for kind in ("views", "clones"):
            new["traffic"][kind]["daily"] = dict(old_traffic.get(kind, {}).get("daily", {}))
        if "referrers" in old_traffic:
            new["traffic"]["referrers"] = dict(old_traffic["referrers"])
        new["snapshots"] = dict(history.get("snapshots", {}))

    for kind in ("views", "clones"):
        series = new["traffic"][kind]
        cur = current[kind]
        series["status"] = cur["status"]
        series["collected_at"] = collected_at
        if cur["status"] == OK:
            series["daily"].update(cur["daily"])
            series.pop("reason", None)
        else:
            series["reason"] = cur["reason"]
        series["daily"] = dict(sorted(series["daily"].items()))

    refs = current["referrers"]
    if refs["status"] == OK:
        new["traffic"]["referrers"] = {"status": OK, "collected_at": collected_at, "items": refs["items"]}
    else:
        # The last good snapshot stays, flagged as not refreshed in this run.
        new["traffic"]["referrers"].update(status=UNAVAILABLE, reason=refs["reason"])

    new["snapshots"][_day(collected_at)] = {
        "collected_at": collected_at,
        **current["totals"],
        "downloads": current["downloads"],
    }
    new["snapshots"] = dict(sorted(new["snapshots"].items()))
    new["updated_at"] = collected_at
    return new


# ── Report ────────────────────────────────────────────────────────────────────


def month_bounds(month: str) -> tuple[str, str]:
    """`2026-10` → (`2026-10-01`, `2026-10-31`)."""
    start = dt.date.fromisoformat(f"{month}-01")
    nxt = (start.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    return start.isoformat(), (nxt - dt.timedelta(days=1)).isoformat()


def _in(day: str, bounds: tuple[str, str]) -> bool:
    return bounds[0] <= day <= bounds[1]


def _traffic_line(series: dict, bounds: tuple[str, str], label: str) -> tuple[str, int | None]:
    days = {d: v for d, v in series.get("daily", {}).items() if _in(d, bounds)}
    if series["status"] != OK and not days:
        return f"indisponível ({series.get('reason', 'sem token')})", None
    if not days:
        return f"nenhum dia com dados de {label} no mês", None
    total = sum(v["uniques"] for v in days.values())
    first, last = min(days), max(days)
    text = f"**{total}** (de {first} a {last}, {len(days)} dias com dados)"
    if series["status"] != OK:
        text += f" — só o histórico: a coleta de agora ficou sem tráfego ({series.get('reason')})"
    return text, total


def _downloads_in_month(history: dict, bounds: tuple[str, str]) -> str:
    """`download_count` is cumulative: the month is the month's last snapshot
    minus the last one before the month (or else the month's first one)."""
    snaps = history["snapshots"]
    before = [d for d in snaps if d < bounds[0]]
    inside = [d for d in snaps if _in(d, bounds)]
    if not inside:
        return "sem snapshot no mês"
    if before:
        base_day = max(before)
    elif len(inside) > 1:
        base_day = min(inside)
    else:
        return "sem snapshot anterior para comparar"
    end_day = max(inside)
    delta = snaps[end_day]["downloads"] - snaps[base_day]["downloads"]
    return f"{delta} (snapshots de {base_day} a {end_day})"


def render_report(repo: str, month: str, current: dict, history: dict, collected_at: str) -> str:
    b = month_bounds(month)
    owner = current["owner"]
    r = f"/repos/{repo}"
    traffic = history["traffic"]

    visitors, _ = _traffic_line(traffic["views"], b, "visitas")
    clones, _ = _traffic_line(traffic["clones"], b, "clones")

    if current["stars"]["status"] == OK:
        new_stars = str(sum(1 for d in current["stars"]["dates"] if _in(d, b)))
    else:
        new_stars = f"indisponível ({current['stars']['reason']})"
    new_forks = sum(1 for d in current["forks"] if _in(d, b))

    month_items = [i for i in current["issues"] if _in(i["created"], b)]
    outsider_issues = [i for i in month_items if i["kind"] == "issue" and i["author"] != owner and not i["bot"]]
    by_label = {lbl: sum(1 for i in outsider_issues if lbl in i["labels"]) for lbl in LABELS}
    other = sum(1 for i in outsider_issues if not set(i["labels"]) & set(LABELS))
    owner_issues = sum(1 for i in month_items if i["kind"] == "issue" and i["author"] == owner)
    prs = [i for i in month_items if i["kind"] == "pr"]
    contributors = sorted({i["author"] for i in prs if i["author"] != owner and not i["bot"]})
    bot_prs = sum(1 for i in prs if i["bot"])

    refs = traffic["referrers"]
    if refs.get("items") is not None:
        top = sorted(refs["items"], key=lambda x: (-x["uniques"], x["referrer"]))[:TOP_REFERRERS]
        ref_note = f"snapshot de {refs['collected_at']}"
        if refs["status"] != OK:
            ref_note += f"; não atualizado nesta coleta ({refs.get('reason')})"
        ref_lines = [f"| {x['referrer']} | {x['count']} | {x['uniques']} |" for x in top] or ["| — | — | — |"]
        ref_block = [f"Top referrers ({ref_note}; janela de 14 dias do GitHub):", "",
                     "| Referrer | Visitas | Únicos |", "|---|---|---|", *ref_lines]
    else:
        ref_block = [f"Top referrers: indisponível ({refs.get('reason', 'sem token')})"]

    labels_text = ", ".join(f"`{k}` {v}" for k, v in by_label.items()) + f", outras/sem label {other}"
    t = current["totals"]
    lines = [
        f"# Métricas de {repo} — {month}",
        "",
        f"Coletado em {collected_at} (UTC). Mês: {b[0]} a {b[1]} (UTC).",
        "",
        f"## Visitantes únicos no mês: {visitors}",
        "",
        "> Soma dos visitantes únicos **diários**: quem voltou em dias diferentes conta "
        "mais de uma vez, então é um **limite superior** de pessoas distintas. "
        f"Fonte: `GET {r}/traffic/views?per=day`, mesclado por data com o histórico.",
        "",
        "## No mês",
        "",
        "| Métrica | Valor | Fonte |",
        "|---|---|---|",
        f"| Clones únicos (soma diária, limite superior) | {clones} | `GET {r}/traffic/clones?per=day` |",
        f"| Novas stars | {new_stars} | `GET {r}/stargazers` (`application/vnd.github.star+json`) |",
        f"| Novos forks | {new_forks} | `GET {r}/forks` (`created_at`) |",
        f"| Issues abertas por pessoas de fora | {len(outsider_issues)} ({labels_text}) | `GET {r}/issues?state=all` |",
        f"| Issues abertas pelo dono (`{owner}`) | {owner_issues} | `GET {r}/issues?state=all` |",
        f"| Contribuidores externos (autores de PR ≠ dono, sem bots) | {len(contributors)}"
        + (f" ({', '.join(contributors)})" if contributors else "")
        + f" | `GET {r}/issues?state=all` (PRs) |",
        f"| PRs de bots | {bot_prs} | `GET {r}/issues?state=all` (PRs) |",
        f"| Downloads de release no mês | {_downloads_in_month(history, b)} "
        f"| `GET {r}/releases` (`download_count`), diferença entre snapshots |",
        "",
        "## Totais acumulados",
        "",
        "| Métrica | Valor | Fonte |",
        "|---|---|---|",
        f"| Stars | {t['stars']} | `GET {r}` (`stargazers_count`) |",
        f"| Forks | {t['forks']} | `GET {r}` (`forks_count`) |",
        f"| Watchers | {t['watchers']} | `GET {r}` (`subscribers_count`) |",
        f"| Downloads de release | {current['downloads']} | `GET {r}/releases` (`download_count` de cada asset) |",
        "",
        *ref_block,
        "",
    ]
    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────


def _month(value: str) -> str:
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value):
        raise argparse.ArgumentTypeError("use YYYY-MM")
    return value


def main(argv: list[str] | None = None, env=os.environ, fetch=urllib_fetch, now: dt.datetime | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", required=True, help="dono/nome, ex.: jlanio/atlans")
    ap.add_argument("--history", type=Path, help="histórico anterior (JSON); omita na primeira execução")
    ap.add_argument("--out-history", type=Path, required=True)
    ap.add_argument("--out-report", type=Path, required=True)
    ap.add_argument("--month", type=_month, help="YYYY-MM; padrão: o mês corrente em UTC")
    args = ap.parse_args(argv)

    now = now or dt.datetime.now(dt.timezone.utc)
    collected_at = now.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    month = args.month or collected_at[:7]

    history = None
    if args.history and args.history.exists():
        history = json.loads(args.history.read_text(encoding="utf-8"))
        if history.get("repo") not in (None, args.repo):
            print(f"histórico é de {history.get('repo')}, não de {args.repo}", file=sys.stderr)
            return 2

    gh = GitHub(env.get(TOKEN_ENV) or None, fetch=fetch)
    current = collect(gh, args.repo)
    new_history = merge(history, current, args.repo, collected_at)

    args.out_history.write_text(json.dumps(new_history, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.out_report.write_text(render_report(args.repo, month, current, new_history, collected_at), encoding="utf-8")
    print(f"histórico: {args.out_history}  relatório: {args.out_report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
