"""Politica de espera entre tentativas — flow/utils/backoff.py.

O defeito que estes testes travam nao e "a espera cresce errado": e a espera
crescer IGUAL para todo mundo. Nove dos dez pontos de retry da plataforma
calculavam potencias de dois sem dispersao, entao a frota de executores que caiu
junto voltava junto, no mesmo milissegundo, contra um rate limit de balde unico.
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
        # Jitter PROPORCIONAL, nao aditivo: e o que garante que o teto de quem
        # chama continua sendo teto. Um `delay + uniform(0, j)` estouraria.
        assert all(com_jitter(5.0) <= 5.0 for _ in range(200))

    def test_zero_e_negativo_nao_viram_espera(self):
        assert com_jitter(0) == 0.0
        assert com_jitter(-3) == 0.0

    def test_dispersa_de_fato(self):
        # O ponto inteiro do modulo. Se isto virar um valor so, dois executores
        # que falharam no mesmo instante retentam no mesmo instante.
        assert len({com_jitter(10.0) for _ in range(50)}) > 40


class TestEsperaExponencial:
    def test_cresce_com_a_tentativa(self):
        # Comparacao entre faixas, e nao entre amostras: com jitter de 50-100%
        # uma amostra da tentativa 0 pode, sozinha, superar uma da tentativa 1.
        media = lambda t: sum(espera_exponencial(t, teto=1000) for _ in range(200)) / 200
        assert media(0) < media(1) < media(2) < media(3)

    def test_teto_vale_mesmo_com_muitas_tentativas(self):
        assert all(espera_exponencial(40, teto=30) <= 30 for _ in range(100))

    def test_inicial_define_a_primeira_espera(self):
        # Faixa da tentativa 0 com inicial=4: entre 2 e 4.
        for _ in range(100):
            assert 2.0 <= espera_exponencial(0, inicial=4.0, teto=100) <= 4.0

    def test_tentativa_negativa_nao_explode(self):
        assert 0 < espera_exponencial(-5, inicial=2.0, teto=10) <= 2.0

    @pytest.mark.parametrize("tentativa", [64, 1023, 1024, 5000, 10 ** 6])
    def test_contador_alto_satura_em_vez_de_estourar(self, tentativa):
        """Regressao: `base ** tentativa` e float e estoura perto de 2**1024.

        O `2 ** n` INTEIRO que esta funcao substituiu tinha precisao arbitraria
        e apenas saturava no teto. Com float, `espera_exponencial(1024, teto=300)`
        levantava OverflowError — e o `consecutive_errors` do ciclo do GeoSync
        nao tem limite superior: so zera num ciclo bem-sucedido. Pior, a chamada
        mora DENTRO do `except Exception:` do ciclo, entao o OverflowError
        escapava do handler e do `while True` (que so protege CancelledError),
        matando a task de sincronizacao em silencio — exatamente a falha que o
        isolamento por ciclo existe para impedir.
        """
        assert 150.0 <= espera_exponencial(tentativa, teto=300) <= 300.0

    def test_base_que_nao_cresce_nao_e_truncada(self):
        # O corte do expoente vale so para `base > 1`. Com base <= 1 nao ha
        # estouro possivel, e truncar mudaria o valor em vez de proteger.
        assert espera_exponencial(500, inicial=1.0, base=0.5, teto=10) < 1e-9


class TestHttpRetryPreservaOContrato:
    """A troca da formula de espera nao pode mexer em QUEM e retentado.

    `async_request_with_retry` tem tres comportamentos que os callers dependem:
    status transitorio esgotado devolve o ultimo Response (o caller decide o
    `raise_for_status`), erro de transporte esgotado PROPAGA, e 4xx nao retenta.
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
        # Duas esperas para tres tentativas, ambas dispersas dentro da faixa.
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
