"""Wait policy between attempts — flow/utils/backoff.py.

The defect these tests lock down is not "the wait grows wrong": it is the wait
growing THE SAME for everyone. Nine of the platform's ten retry points computed
powers of two without dispersion, so the fleet of executors that went down
together came back together, in the same millisecond, against a single-bucket
rate limit.
"""
import httpx
import pytest

from flow.utils.backoff import MIN_JITTER_FACTOR, with_jitter, espera_exponencial


class TestWithJitter:
    def test_stays_within_the_declared_range(self):
        for _ in range(200):
            v = with_jitter(10.0)
            assert MIN_JITTER_FACTOR * 10.0 <= v <= 10.0

    def test_never_exceeds_the_requested_value(self):
        # PROPORTIONAL jitter, not additive: it is what guarantees the caller's ceiling
        # stays a ceiling. A `delay + uniform(0, j)` would overshoot.
        assert all(with_jitter(5.0) <= 5.0 for _ in range(200))

    def test_zero_and_negative_do_not_become_a_wait(self):
        assert with_jitter(0) == 0.0
        assert with_jitter(-3) == 0.0

    def test_actually_spreads(self):
        # The whole point of the module. If this becomes a single value, two executors
        # that failed at the same instant retry at the same instant.
        assert len({with_jitter(10.0) for _ in range(50)}) > 40


class TestExponentialWait:
    def test_grows_with_the_attempt(self):
        # Comparison between ranges, not between samples: with 50-100% jitter
        # a sample from attempt 0 can, by itself, exceed one from attempt 1.
        media = lambda t: sum(espera_exponencial(t, teto=1000) for _ in range(200)) / 200
        assert media(0) < media(1) < media(2) < media(3)

    def test_ceiling_holds_even_with_many_attempts(self):
        assert all(espera_exponencial(40, teto=30) <= 30 for _ in range(100))

    def test_initial_sets_the_first_wait(self):
        # Range of attempt 0 with inicial=4: between 2 and 4.
        for _ in range(100):
            assert 2.0 <= espera_exponencial(0, inicial=4.0, teto=100) <= 4.0

    def test_negative_attempt_does_not_blow_up(self):
        assert 0 < espera_exponencial(-5, inicial=2.0, teto=10) <= 2.0

    @pytest.mark.parametrize("tentativa", [64, 1023, 1024, 5000, 10 ** 6])
    def test_high_counter_saturates_instead_of_overflowing(self, tentativa):
        """Regression: `base ** tentativa` is a float and overflows near 2**1024.

        The INTEGER `2 ** n` this function replaced had arbitrary precision
        and merely saturated at the ceiling. With float, `espera_exponencial(1024, teto=300)`
        raised OverflowError — and the GeoSync cycle's `consecutive_errors` has no
        upper bound: it only resets on a successful cycle. Worse, the call lives
        INSIDE the cycle's `except Exception:`, so the OverflowError escaped the
        handler and the `while True` (which only protects CancelledError),
        silently killing the sync task — exactly the failure that per-cycle
        isolation exists to prevent.
        """
        assert 150.0 <= espera_exponencial(tentativa, teto=300) <= 300.0

    def test_base_that_does_not_grow_is_not_truncated(self):
        # The exponent cap only applies for `base > 1`. With base <= 1 no overflow is
        # possible, and truncating would change the value instead of protecting it.
        assert espera_exponencial(500, inicial=1.0, base=0.5, teto=10) < 1e-9


class TestHttpRetryPreservesTheContract:
    """Changing the wait formula must not touch WHO gets retried.

    `async_request_with_retry` has three behaviors the callers depend on:
    an exhausted transient status returns the last Response (the caller decides
    on `raise_for_status`), an exhausted transport error PROPAGATES, and 4xx is not retried.
    """

    @pytest.fixture(autouse=True)
    def _no_sleep(self, monkeypatch):
        import asyncio
        self.waits: list[float] = []

        async def _fake_sleep(s):
            self.waits.append(s)

        monkeypatch.setattr(asyncio, "sleep", _fake_sleep)

    async def test_exhausted_transient_status_returns_the_last_response(self):
        from flow.utils.http_retry import async_request_with_retry

        chamadas = []

        def _handler(request):
            chamadas.append(request)
            return httpx.Response(503)

        resp = await async_request_with_retry(
            "GET", "https://exemplo.test/x",
            client_kwargs={"transport": httpx.MockTransport(_handler)},
            max_attempts=3,
        )
        assert resp.status_code == 503
        assert len(chamadas) == 3
        # Two waits for three attempts, both dispersed within the range.
        assert len(self.waits) == 2
        assert all(0 < e <= 2.0 for e in self.waits)

    async def test_four_xx_does_not_retry(self):
        from flow.utils.http_retry import async_request_with_retry

        chamadas = []

        def _handler(request):
            chamadas.append(request)
            return httpx.Response(404)

        resp = await async_request_with_retry(
            "GET", "https://exemplo.test/x",
            client_kwargs={"transport": httpx.MockTransport(_handler)},
            max_attempts=3,
        )
        assert resp.status_code == 404
        assert len(chamadas) == 1
        assert self.waits == []

    async def test_exhausted_transport_error_propagates(self):
        from flow.utils.http_retry import async_request_with_retry

        def _handler(request):
            raise httpx.ConnectError("sem rota", request=request)

        with pytest.raises(httpx.ConnectError):
            await async_request_with_retry(
                "GET", "https://exemplo.test/x",
                client_kwargs={"transport": httpx.MockTransport(_handler)},
                max_attempts=2,
            )
        assert len(self.waits) == 1


class TestRetrySyncSpreads:
    def test_two_runs_do_not_sleep_the_same(self, monkeypatch):
        """Dois processos que falham juntos precisam acordar separados."""
        from flow.utils import http_retry

        sleeps: list[float] = []
        monkeypatch.setattr(http_retry.time, "sleep", sleeps.append)

        def _always_fails():
            raise ConnectionError("caiu")

        for _ in range(12):
            with pytest.raises(ConnectionError):
                http_retry.retry_sync(_always_fails, max_attempts=2, label="teste")

        assert len(sleeps) == 12
        assert all(0.5 <= d <= 1.0 for d in sleeps)
        assert len(set(sleeps)) > 8
