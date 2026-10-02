# tests/unit/test_save_to_s3_credencial.py
"""SaveToS3 usa a credencial `s3` do cofre; o segredo não fica mais na definition.

Antes o tipo `s3` existia no cofre (com teste de conexão) e nenhum nó o usava:
o SaveToS3 pedia `awsSecretAccessKey` digitada no nó, gravada em texto puro. E
como as listas de segredo comparam o NOME exato, o campo escapava do lint, da
redação da leitura e da máscara do log.
"""
from unittest.mock import MagicMock, patch

import geopandas as gpd
import pytest
from shapely.geometry import Point

import flow.nodes.outputs.save_to_s3  # noqa: F401 — registra o nó
from app.core.utils.redacao import definition_contem_segredo, redigir_definition
from app.services.credential_resolver import (
    inject_credentials,
    propriedade_que_recebe,
    s3_auth_da_credencial,
)
from flow.factory import _sem_segredos
from flow.nodes.outputs.save_to_s3 import SaveToS3Node
from flow.utils.definition_lint import lint_definition

CID = "5d1e9a3c-7b24-4f60-8c11-2e9f0a4b6d73"
SEGREDO = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"  # pragma: allowlist secret

_CRED_S3 = {
    "type": "s3", "access_key_id": "AKIAEXEMPLO", "secret_access_key": SEGREDO,
    "region": "sa-east-1", "bucket": "bucket-da-credencial", "endpoint_url": "",
    "expires_at": "2099-01-01T00:00:00Z",
}


def _definicao(**props):
    return {"nodes": [{"id": "n1", "name": "SaveToS3", "type": "output",
                       "properties": {"key": "saida/a.geojson", "credential_id": CID, **props}}]}


# ── Resolução ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_credencial_s3_entra_em_s3_auth_so_com_os_campos_do_catalogo():
    saida = await inject_credentials(_definicao(), pre_resolved={CID: dict(_CRED_S3)})
    props = saida["nodes"][0]["properties"]
    assert props["s3_auth"] == {
        "access_key_id": "AKIAEXEMPLO", "secret_access_key": SEGREDO,
        "region": "sa-east-1", "bucket": "bucket-da-credencial",
    }
    assert "credential_id" not in props


@pytest.mark.asyncio
async def test_webhook_token_do_uso_antigo_deixa_o_id_para_proteger_a_copia():
    saida = await inject_credentials(
        _definicao(registerArtifact=True), pre_resolved={CID: {"type": "webhook_token", "token": "T"}},
    )
    props = saida["nodes"][0]["properties"]
    assert props["credential_id"] == CID and "s3_auth" not in props


def test_propriedade_e_forma_da_credencial_s3():
    assert propriedade_que_recebe("s3") == "s3_auth"
    assert s3_auth_da_credencial({"type": "postgresql", "connectionString": "x"}) is None


# ── Execução ─────────────────────────────────────────────────────────────────


def _gdf():
    return gpd.GeoDataFrame({"id": [1]}, geometry=[Point(0, 0)], crs="EPSG:4326")


def _boto3():
    """`boto3.session.Session` dublado; devolve (patch, `client` da sessão)."""
    sessao = MagicMock()
    return patch("boto3.session.Session", sessao), sessao.return_value.client


async def _executar(**props):
    dublê, fabrica = _boto3()
    cliente = fabrica.return_value
    with dublê:
        no = SaveToS3Node(node_id="n1", parameters={"key": "saida/a.geojson", **props})
        saida = await no.execute({"in": _gdf()})
    return fabrica, cliente, saida


@pytest.mark.asyncio
async def test_execucao_usa_a_credencial_injetada_e_o_bucket_padrao_dela():
    s3_auth = s3_auth_da_credencial(dict(_CRED_S3))
    fabrica, cliente, saida = await _executar(s3_auth=s3_auth)
    fabrica.assert_called_once_with(
        "s3", region_name="sa-east-1", aws_access_key_id="AKIAEXEMPLO", aws_secret_access_key=SEGREDO,
    )
    assert cliente.put_object.call_args.kwargs["Bucket"] == "bucket-da-credencial"
    assert saida["output"]["s3Uri"] == "s3://bucket-da-credencial/saida/a.geojson"


@pytest.mark.asyncio
async def test_bucket_e_regiao_do_no_sobrepoem_os_da_credencial():
    s3_auth = s3_auth_da_credencial(dict(_CRED_S3))
    fabrica, cliente, _ = await _executar(s3_auth=s3_auth, bucketName="do-no", region="us-west-2")
    assert fabrica.call_args.kwargs["region_name"] == "us-west-2"
    assert cliente.put_object.call_args.kwargs["Bucket"] == "do-no"


@pytest.mark.asyncio
async def test_endpoint_da_credencial_chega_ao_boto3():
    s3_auth = {**s3_auth_da_credencial(dict(_CRED_S3)), "endpoint_url": "https://s3.compativel.exemplo"}
    with patch("flow.utils.geo_helpers.validate_url_ssrf", return_value=("203.0.113.9", "s3.compativel.exemplo")):
        fabrica, _, _ = await _executar(s3_auth=s3_auth)
    assert fabrica.call_args.kwargs["endpoint_url"] == "https://s3.compativel.exemplo"


@pytest.mark.asyncio
async def test_endpoint_interno_e_recusado_como_no_teste_da_credencial():
    s3_auth = {**s3_auth_da_credencial(dict(_CRED_S3)), "endpoint_url": "http://169.254.169.254"}
    dublê, fabrica = _boto3()
    with dublê:
        no = SaveToS3Node(node_id="n1", parameters={"key": "a.geojson", "s3_auth": s3_auth})
        with pytest.raises(ValueError):
            await no.execute({"in": _gdf()})
    fabrica.assert_not_called()


@pytest.mark.asyncio
async def test_fluxo_antigo_com_as_chaves_no_no_segue_com_a_mesma_identidade():
    """Sem credencial S3, os campos antigos continuam lidos: trocar em silêncio
    para a cadeia padrão do executor mudaria QUEM escreve no bucket."""
    fabrica, _, _ = await _executar(
        bucketName="b", awsAccessKeyId="AKIAANTIGA", awsSecretAccessKey="segredo-antigo",  # pragma: allowlist secret
    )
    fabrica.assert_called_once_with(
        "s3", region_name="us-east-1", aws_access_key_id="AKIAANTIGA", aws_secret_access_key="segredo-antigo",
    )


@pytest.mark.asyncio
async def test_sem_credencial_nem_chaves_vale_a_cadeia_padrao():
    fabrica, _, _ = await _executar(bucketName="b")
    fabrica.assert_called_once_with("s3", region_name="us-east-1")


@pytest.mark.asyncio
async def test_sem_bucket_no_no_nem_na_credencial_recusa():
    dublê, _ = _boto3()
    with dublê:
        no = SaveToS3Node(node_id="n1", parameters={"key": "a.geojson"})
        with pytest.raises(ValueError, match="bucketName"):
            await no.execute({"in": _gdf()})


# ── O campo antigo é segredo em todas as listas ─────────────────────────────


def test_chave_secreta_digitada_no_no_e_recusada_ao_gravar():
    caminhos = definition_contem_segredo(_definicao(awsSecretAccessKey=SEGREDO))
    assert any(c.endswith("awsSecretAccessKey") for c in caminhos)


def test_chave_secreta_digitada_no_no_e_acusada_pelo_lint():
    no = {"id": "n1", "name": "SaveToS3", "type": "output",
          "parameters": {"key": "a.geojson", "awsSecretAccessKey": SEGREDO}}
    relatorio = lint_definition([no], [], registry_names={"SaveToS3"})
    diagnosticos = [d for d in relatorio.errors if d.code == "secret_in_definition"]
    assert diagnosticos and "awsSecretAccessKey" in diagnosticos[0].message
    assert SEGREDO not in diagnosticos[0].message


def test_leitura_redige_a_chave_secreta_e_o_s3_auth():
    saida = redigir_definition(_definicao(awsSecretAccessKey=SEGREDO, s3_auth={"secret_access_key": SEGREDO}))
    assert SEGREDO not in str(saida)


def test_log_da_fabrica_mascara_a_chave_secreta_e_o_s3_auth():
    mascarado = _sem_segredos({"awsSecretAccessKey": SEGREDO, "s3_auth": {"secret_access_key": SEGREDO}, "key": "k"})
    assert mascarado == {"awsSecretAccessKey": "***", "s3_auth": "***", "key": "k"}


# ── Validação: severidade conforme o uso da credencial ──────────────────────


def _conferir(tipo: str):
    from app.services.validate_service import _conferir_credenciais
    from flow.utils.definition_lint import RelatorioLint

    rel = RelatorioLint()
    nos = [{"id": "n1", "name": "SaveToS3", "parameters": {"credential_id": CID}}]
    descriptors = {"SaveToS3": SaveToS3Node.description()}
    _conferir_credenciais(rel, nos, descriptors, {CID: (tipo, "expirada", "2020-01-01T00:00:00Z")})
    return rel


def test_credencial_s3_vencida_e_erro_porque_o_no_a_consome():
    rel = _conferir("s3")
    assert [d.code for d in rel.errors] == ["credential_expired"]


def test_webhook_token_vencido_do_uso_antigo_segue_como_aviso():
    rel = _conferir("webhook_token")
    assert not rel.errors
    assert [d.code for d in rel.warnings] == ["credential_expired"]


def _conferir_com(tipo: str, register_artifact):
    from app.services.validate_service import _conferir_credenciais
    from flow.utils.definition_lint import RelatorioLint

    rel = RelatorioLint()
    nos = [{"id": "n1", "name": "SaveToS3",
            "parameters": {"credential_id": CID, "registerArtifact": register_artifact}}]
    _conferir_credenciais(rel, nos, {"SaveToS3": SaveToS3Node.description()}, {CID: (tipo, "valida", None)})
    return rel


@pytest.mark.parametrize("ligado", [True, "true"])
def test_credencial_s3_com_copia_registrada_avisa_que_a_copia_fica_sem_protecao(ligado):
    """O mesmo campo serve às duas coisas: escolher a S3 tira o Webhook Token da cópia."""
    rel = _conferir_com("s3", ligado)
    assert [d.code for d in rel.warnings] == ["artifact_copy_unprotected"]
    assert not rel.errors


def test_sem_copia_registrada_ou_com_token_nao_ha_aviso():
    assert not _conferir_com("s3", False).warnings
    assert not _conferir_com("webhook_token", True).warnings


# ── Credencial que não resolveu ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_credencial_s3_nao_resolvida_sem_copia_recusa_em_vez_de_trocar_de_identidade():
    """Sem `s3_auth` e com o id no lugar, o upload saía com a cadeia padrão do
    executor — outra identidade, em silêncio. Agora recusa, como o HttpRequest."""
    dublê, fabrica = _boto3()
    with dublê:
        no = SaveToS3Node(node_id="n1", parameters={"key": "a.geojson", "bucketName": "b", "credential_id": CID})
        with pytest.raises(ValueError, match="não pôde ser resolvida"):
            await no.execute({"in": _gdf()})
    fabrica.assert_not_called()


@pytest.mark.asyncio
async def test_token_antigo_sem_copia_registrada_sai_na_resolucao_e_o_fluxo_segue():
    """Um Webhook Token que sobrou no nó com a cópia desligada não protege nada:
    o servidor o tira, e o nó não confunde isso com credencial S3 não resolvida."""
    saida = await inject_credentials(
        _definicao(registerArtifact=False), pre_resolved={CID: {"type": "webhook_token", "token": "T"}},
    )
    props = saida["nodes"][0]["properties"]
    assert "credential_id" not in props and "s3_auth" not in props
    fabrica, _, _ = await _executar(bucketName="b", **{k: v for k, v in props.items() if k != "key"})
    fabrica.assert_called_once()
