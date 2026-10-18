# tests/unit/test_repo_metrics.py
"""
The public metrics collector (scripts/repo_metrics.py).

What is protected:

- **The first run works with no history** and writes one.
- **Traffic beyond GitHub's 14 days.** The daily series are merged by date with
  the previous history; a repeated date takes the new value and nothing is
  counted twice. Running twice with the first run's history changes nothing.
- **No token is never 0.** Without ATLANS_METRICS_TOKEN, or with 401/403 on the
  traffic, the traffic is "unavailable" in the history and "indisponível" in the
  report, the days already known are kept, and the rest of the report goes on.
  The token never reaches the history, the report or stdout.
- **Pagination** follows the `Link: rel="next"` header to the end.
- **Owner vs. people from outside.** Issues by the owner and PRs by bots do not
  count as outside interest or external contributors.
- **The month cut** is by UTC date, both edges included.

No network: the HTTP layer is swapped for a dictionary of fixtures.
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
FIXTURES = RAIZ / "tests" / "fixtures" / "repo_metrics"
API = "https://api.github.com/repos/jlanio/atlans"
TOKEN = "token-de-teste-nao-vazar"
NOW = dt.datetime(2026, 10, 18, 12, 0, 0, tzinfo=dt.timezone.utc)


@pytest.fixture(scope="module")
def rm():
    spec = importlib.util.spec_from_file_location("repo_metrics", RAIZ / "scripts" / "repo_metrics.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _fx(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _routes(traffic_status: int = 200) -> dict:
    """URL → (status, headers, body). Stargazers and issues come in two pages."""
    page2_stars = f"{API}/stargazers?per_page=100&page=2"
    page2_issues = f"{API}/issues?state=all&per_page=100&page=2"
    nao = (traffic_status, {}, b'{"message": "Must have push access to repository"}')
    return {
        API: (200, {}, _fx("repo.json")),
        f"{API}/stargazers?per_page=100": (200, {"Link": f'<{page2_stars}>; rel="next", <{page2_stars}>; rel="last"'}, _fx("stargazers_p1.json")),
        page2_stars: (200, {"Link": f'<{API}/stargazers?per_page=100&page=1>; rel="prev"'}, _fx("stargazers_p2.json")),
        f"{API}/forks?sort=oldest&per_page=100": (200, {}, _fx("forks.json")),
        f"{API}/issues?state=all&per_page=100": (200, {"link": f'<{page2_issues}>; rel="next"'}, _fx("issues_p1.json")),
        page2_issues: (200, {}, _fx("issues_p2.json")),
        f"{API}/releases?per_page=100": (200, {}, _fx("releases.json")),
        f"{API}/traffic/views?per=day": (200, {}, _fx("views.json")) if traffic_status == 200 else nao,
        f"{API}/traffic/clones?per=day": (200, {}, _fx("clones.json")) if traffic_status == 200 else nao,
        f"{API}/traffic/popular/referrers": (200, {}, _fx("referrers.json")) if traffic_status == 200 else nao,
    }


class FakeHTTP:
    def __init__(self, routes: dict, star_needs_token: bool = False):
        self.routes = routes
        self.star_needs_token = star_needs_token
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, url: str, headers: dict):
        self.calls.append((url, headers))
        if self.star_needs_token and "/stargazers" in url and "Authorization" not in headers:
            return 401, {}, b'{"message": "Requires authentication"}'
        if "/traffic/" in url and "Authorization" not in headers:
            return 401, {}, b'{"message": "Requires authentication"}'
        if url not in self.routes:
            raise AssertionError(f"URL inesperada: {url}")
        return self.routes[url]


def _run(rm, tmp_path, *, token=True, history=None, month=None, http=None, now=NOW, tag="1"):
    http = http or FakeHTTP(_routes())
    out_h = tmp_path / f"hist{tag}.json"
    out_r = tmp_path / f"report{tag}.md"
    argv = ["--repo", "jlanio/atlans", "--out-history", str(out_h), "--out-report", str(out_r)]
    if history:
        argv += ["--history", str(history)]
    if month:
        argv += ["--month", month]
    env = {"ATLANS_METRICS_TOKEN": TOKEN} if token else {}
    assert rm.main(argv, env=env, fetch=http, now=now) == 0
    return json.loads(out_h.read_text(encoding="utf-8")), out_r.read_text(encoding="utf-8"), http


def test_first_run_without_history(rm, tmp_path):
    hist, report, _ = _run(rm, tmp_path, history=tmp_path / "nao-existe.json")

    assert hist["repo"] == "jlanio/atlans"
    assert hist["traffic"]["views"]["status"] == "ok"
    assert hist["traffic"]["views"]["daily"] == {
        "2026-09-30": {"count": 10, "uniques": 4},
        "2026-10-01": {"count": 20, "uniques": 7},
        "2026-10-02": {"count": 30, "uniques": 9},
    }
    assert list(hist["snapshots"]) == ["2026-10-18"]
    assert hist["snapshots"]["2026-10-18"]["downloads"] == 42

    # October only: 7 + 9, the 30th of September is out.
    assert "## Visitantes únicos no mês: **16** (de 2026-10-01 a 2026-10-02, 2 dias com dados)" in report
    assert "limite superior" in report
    assert "Coletado em 2026-10-18T12:00:00Z (UTC)" in report
    assert "| Clones únicos (soma diária, limite superior) | **3**" in report
    assert "| Stars | 3 |" in report
    assert "| Watchers | 1 |" in report
    assert "| Downloads de release | 42 |" in report
    assert "sem snapshot anterior para comparar" in report
    # Referrers sorted by unique visitors.
    assert report.index("news.ycombinator.com") < report.index("github.com |") < report.index("Google")
    # The source of each number.
    for fonte in ("/traffic/views", "/traffic/clones", "/stargazers", "/forks", "/issues?state=all", "/releases"):
        assert f"`GET /repos/jlanio/atlans{fonte}" in report


def test_merge_with_overlapping_dates(rm, tmp_path):
    hist, report, _ = _run(rm, tmp_path, history=FIXTURES / "history_previous.json")

    views = hist["traffic"]["views"]["daily"]
    # The 15th of September only exists in the history: beyond the 14-day window, kept.
    assert views["2026-09-15"] == {"count": 8, "uniques": 3}
    # Dates in both: the new value replaces the old one.
    assert views["2026-09-30"] == {"count": 10, "uniques": 4}
    assert views["2026-10-01"] == {"count": 20, "uniques": 7}
    assert list(views) == sorted(views)
    assert set(hist["traffic"]["clones"]["daily"]) == {"2026-09-15", "2026-10-01", "2026-10-02"}
    assert list(hist["snapshots"]) == ["2026-09-28", "2026-10-18"]
    # Not 7 + 1 + 9: the 1st of October counts once, with the new value.
    assert "no mês: **16**" in report
    assert "| Downloads de release no mês | 12 (snapshots de 2026-09-28 a 2026-10-18) |" in report

    # September from the same history: the old 15th plus the new 30th.
    _, setembro, _ = _run(rm, tmp_path, history=FIXTURES / "history_previous.json", month="2026-09", tag="set")
    assert "no mês: **7** (de 2026-09-15 a 2026-09-30, 2 dias com dados)" in setembro


def test_two_runs_in_a_row_do_not_duplicate(rm, tmp_path):
    first, report1, _ = _run(rm, tmp_path, tag="1")
    second, report2, _ = _run(rm, tmp_path, history=tmp_path / "hist1.json", tag="2")
    assert second == first
    assert report2 == report1

    # A later run on the same day replaces that day's snapshot.
    later = NOW + dt.timedelta(hours=3)
    third, _, _ = _run(rm, tmp_path, history=tmp_path / "hist2.json", now=later, tag="3")
    assert list(third["snapshots"]) == ["2026-10-18"]
    assert third["snapshots"]["2026-10-18"]["collected_at"] == "2026-10-18T15:00:00Z"
    assert third["traffic"]["views"]["daily"] == first["traffic"]["views"]["daily"]


def test_without_token_traffic_is_unavailable_never_zero(rm, tmp_path, capsys):
    http = FakeHTTP(_routes(), star_needs_token=True)
    hist, report, http = _run(rm, tmp_path, token=False, http=http)

    assert not any("/traffic/" in url for url, _ in http.calls), "sem token não há por que pedir tráfego"
    assert all("Authorization" not in h for _, h in http.calls)
    for kind in ("views", "clones", "referrers"):
        assert hist["traffic"][kind]["status"] == "unavailable"
        assert hist["traffic"][kind]["reason"] == "sem token"
    assert "## Visitantes únicos no mês: indisponível (sem token)" in report
    assert "| Clones únicos (soma diária, limite superior) | indisponível (sem token) |" in report
    assert "| Novas stars | indisponível (sem token) |" in report
    assert "Top referrers: indisponível (sem token)" in report
    assert "**0**" not in report
    # The rest of the report goes on.
    assert "| Stars | 3 |" in report
    assert "| Novos forks | 1 |" in report


def test_without_token_keeps_the_known_days(rm, tmp_path):
    hist, report, _ = _run(rm, tmp_path, token=False, history=FIXTURES / "history_previous.json")

    views = hist["traffic"]["views"]
    assert views["status"] == "unavailable"
    assert views["daily"] == json.loads(_fx("history_previous.json"))["traffic"]["views"]["daily"]
    assert hist["traffic"]["referrers"]["items"][0]["referrer"] == "old.example"
    assert hist["traffic"]["referrers"]["status"] == "unavailable"
    assert "só o histórico" in report
    assert "não atualizado nesta coleta (sem token)" in report


@pytest.mark.parametrize("status", [401, 403])
def test_token_without_access_is_unavailable(rm, tmp_path, status, capsys):
    hist, report, http = _run(rm, tmp_path, http=FakeHTTP(_routes(traffic_status=status)))

    assert hist["traffic"]["views"]["status"] == "unavailable"
    assert hist["traffic"]["views"]["reason"] == f"token sem acesso: HTTP {status}"
    assert f"indisponível (token sem acesso: HTTP {status})" in report
    assert "| Novas stars | 2 |" in report

    # The token went in the header and nowhere else.
    assert all(h["Authorization"] == f"Bearer {TOKEN}" for _, h in http.calls)
    saida = capsys.readouterr()
    for texto in (json.dumps(hist), report, saida.out, saida.err):
        assert TOKEN not in texto


def test_pagination_follows_link_next(rm, tmp_path):
    hist, report, http = _run(rm, tmp_path)
    urls = [u for u, _ in http.calls]
    assert f"{API}/stargazers?per_page=100&page=2" in urls
    assert f"{API}/issues?state=all&per_page=100&page=2" in urls
    assert ("Accept", "application/vnd.github.star+json") in next(
        h for u, h in http.calls if "/stargazers" in u
    ).items()
    # Stars on 02/10 and 15/10, one of them on the second page.
    assert "| Novas stars | 2 |" in report


def test_owner_vs_outsiders(rm, tmp_path):
    _, report, _ = _run(rm, tmp_path)
    # October: #2 ana bug, #3 bruno question+bug, #5 carla no label; #4 is the owner's.
    assert (
        "| Issues abertas por pessoas de fora | 3 (`bug` 2, `question` 1, `enhancement` 0, outras/sem label 1) |"
        in report
    )
    assert "| Issues abertas pelo dono (`jlanio`) | 1 |" in report
    # PRs: #6 by the owner, #7 dora, #8 a bot; #9 eva is from September.
    assert "| Contribuidores externos (autores de PR ≠ dono, sem bots) | 1 (dora) |" in report
    assert "| PRs de bots | 1 |" in report


def test_month_cut_is_by_utc_date_with_both_edges(rm, tmp_path):
    _, outubro, _ = _run(rm, tmp_path, month="2026-10")
    # Fork from 2026-09-30T23:59:59Z is out, 2026-10-01T00:00:00Z is in.
    assert "| Novos forks | 1 |" in outubro

    _, setembro, _ = _run(rm, tmp_path, month="2026-09", tag="set")
    assert "# Métricas de jlanio/atlans — 2026-09" in setembro
    assert "Mês: 2026-09-01 a 2026-09-30 (UTC)" in setembro
    assert "| Novos forks | 1 |" in setembro
    assert "| Novas stars | 1 |" in setembro
    assert "| Contribuidores externos (autores de PR ≠ dono, sem bots) | 1 (eva) |" in setembro
    assert "| Issues abertas por pessoas de fora | 1 (`bug` 1," in setembro
    assert "no mês: **4** (de 2026-09-30 a 2026-09-30, 1 dias com dados)" in setembro


def test_month_bounds(rm):
    assert rm.month_bounds("2026-02") == ("2026-02-01", "2026-02-28")
    assert rm.month_bounds("2028-02") == ("2028-02-01", "2028-02-29")
    assert rm.month_bounds("2026-12") == ("2026-12-01", "2026-12-31")


def test_invalid_month_is_rejected(rm, tmp_path):
    with pytest.raises(SystemExit):
        _run(rm, tmp_path, month="2026-13")


def test_history_of_another_repo_is_refused(rm, tmp_path):
    outro = tmp_path / "outro.json"
    outro.write_text(json.dumps({"repo": "fulano/outro"}), encoding="utf-8")
    argv = ["--repo", "jlanio/atlans", "--history", str(outro),
            "--out-history", str(tmp_path / "h.json"), "--out-report", str(tmp_path / "r.md")]
    assert rm.main(argv, env={}, fetch=FakeHTTP(_routes()), now=NOW) == 2
    assert not (tmp_path / "h.json").exists()
