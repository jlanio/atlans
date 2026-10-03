"""Wait policy between attempts — flow/utils/backoff.py.

The defect these tests lock down is not "the wait grows wrong": it is the wait
growing THE SAME for everyone. Nine of the platform's ten retry points computed
powers of two without dispersion, so the fleet of executors that went down
together came back together, in the same millisecond, against a single-bucket
rate limit.
"""
import httpx
import pytest

from flow.utils.backoff import FATOR_JITTER_MIN, com_jitter, espera_exponencial


class TestComJitter:
    def test_fica_dentro_da_faixa_declarada(self):
        for _ in range(200):
            v = com_jitter(10.0)
            assert FATOR_JITTER_MIN * 10.0 <= v <= 10.0

    def test_nunca_excede_o_valor_pedido(self):
        # PROPORTIONAL jitter, not additive: it is what guarantees the caller's ceiling
        # stays a ceiling. A `delay + uniform(0, j)` would overshoot.
        assert all(com_jitter(5.0) <= 5.0 for _ in range(200))

    def test_zero_e_negativo_nao_viram_espera(self):
        assert com_jitter(0) == 0.0
        assert com_jitter(-3) == 0.0

    def test_dispersa_de_fato(self):
        # The whole point of the module. If this becomes a single value, two executors
        # that failed at the same instant retry at the same instant.
        assert len({com_jitter(10.0) for _ in range(50)}) > 40


class TestEsperaExponencial:
    def test_cresce_com_a_tentativa(self):
        # Comparison between ranges, not between samples: with 50-100% jitter
        # a sample from attempt 0 can, by itself, exceed one from attempt 1.
        media = lambda t: sum(espera_exponencial(t, teto=1000) for _ in range(200)) / 200
        assert media(0) < media(1) < media(2) < media(3)

    def test_teto_vale_mesmo_com_muitas_tentativas(self):
        assert all(espera_exponencial(40, teto=30) <= 30 for _ in range(100))

    def test_inicial_define_a_primeira_espera(self):
        # Range of attempt 0 with inicial=4: between 2 and 4.
        for _ in range(100):
            assert 2.0 <= espera_exponencial(0, inicial=4.0, teto=100) <= 4.0

    def test_tentativa_negativa_nao_explode(self):
        assert 0 < espera_exponencial(-5, inicial=2.0, teto=10) <= 2.0

    @pytest.mark.parametrize("tentativa", [64, 1023, 1024, 5000, 10 ** 6])
    def test_contador_alto_satura_em_vez_de_estourar(self, tentativa):
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

    def test_base_que_nao_cresce_nao_e_truncada(self):
        # The exponent cap only applies for `base > 1`. With base <= 1 no overflow is
        # possible, and truncating would change the value instead of protecting it.
        assert espera_exponencial(500, inicial=1.0, base=0.5, teto=10) < 1e-9


class TestHttpRetryPreservaOContrato:
    """Changing the wait formula must not touch WHO gets retried.

    `async_request_with_retry` has three behaviors the callers depend on:
    an exhausted transient status returns the last Response (the caller decides
    on `raise_for_status`), an exhausted transport error PROPAGATES, and 4xx is not retried.
    """

    @pytest.fixture(autouse=True)
    def _sem_dormir(self, monkeypatch):
        import asyncio
        self.esperas: list[float] = []

        async def _fake_sleep(s):
            self.esperas.append(s)

        monkeypatch.setattr(asyncio, "sleep", _fake_sleep)

    async def test_status_transitorio_esgotado_devolve_a_ultima_resposta(self):
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
        assert len(self.esperas) == 2
        assert all(0 < e <= 2.0 for e in self.esperas)

    async def test_quatro_xx_nao_retenta(self):
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
        assert self.esperas == []

    async def test_erro_de_transporte_esgotado_propaga(self):
        from flow.utils.http_retry import async_request_with_retry

        def _handler(request):
            raise httpx.ConnectError("sem rota", request=request)

        with pytest.raises(httpx.ConnectError):
            await async_request_with_retry(
                "GET", "https://exemplo.test/x",
                client_kwargs={"transport": httpx.MockTransport(_handler)},
                max_attempts=2,
            )
        assert len(self.esperas) == 1


class TestRetrySyncDispersa:
    def test_duas_execucoes_nao_dormem_o_mesmo(self, monkeypatch):
        """Dois processos que falham juntos precisam acordar separados."""
        from flow.utils import http_retry

        dormidas: list[float] = []
        monkeypatch.setattr(http_retry.time, "sleep", dormidas.append)

        def _sempre_falha():
            raise ConnectionError("caiu")

        for _ in range(12):
            with pytest.raises(ConnectionError):
                http_retry.retry_sync(_sempre_falha, max_attempts=2, label="teste")

        assert len(dormidas) == 12
        assert all(0.5 <= d <= 1.0 for d in dormidas)
        assert len(set(dormidas)) > 8
