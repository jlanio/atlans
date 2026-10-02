"""
drive_resolver: Drive e Artefatos resolvidos sempre via HTTP do executor.

O caminho "servidor" (import de app.core.db + download direto do MinIO com
boto3) foi removido: o motor roda apenas dentro do executor, que nao tem banco
nem credenciais de storage. Autorizacao e escopo de workspace ficam no servidor,
que responde com uma pre-signed URL de TTL curto.
"""
from unittest.mock import patch

import pytest

from flow.utils import drive_resolver


class _Resp:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise AssertionError(f"raise_for_status inesperado: {self.status_code}")


_META = {
    "download_url": "https://minio/objeto?sig=abc",
    "original_name": "x.geojson",
    "extension": "GeoJSON",
}


@pytest.fixture(autouse=True)
def _http_config():
    with patch("flow.utils.executor_http.get_agent_http_config",
               return_value=("https://srv", {}, True)):
        yield


@pytest.mark.parametrize("resolve,file_id,endpoint", [
    (drive_resolver.resolve_drive_file, "file-1", "/drive/executor-download/file-1"),
    (drive_resolver.resolve_artifact_file, "art-1", "/drive/executor-download-artifact/art-1"),
])
def test_resolve_usa_endpoint_do_executor(resolve, file_id, endpoint):
    with patch("httpx.get", return_value=_Resp(200, _META)) as get, \
            patch.object(drive_resolver, "_stream_presigned_to_temp",
                         return_value=("/tmp/x.geojson", "geojson", "x.geojson")) as stream:
        out = resolve(file_id)

    assert get.call_args.args[0] == f"https://srv{endpoint}"
    # extension normalizada para minusculo e repassada ao streaming.
    assert stream.call_args.args[:3] == (_META["download_url"], "geojson", "x.geojson")
    assert out == ("/tmp/x.geojson", "geojson", "x.geojson")


@pytest.mark.parametrize("resolve", [
    drive_resolver.resolve_drive_file,
    drive_resolver.resolve_artifact_file,
])
def test_404_vira_file_not_found(resolve):
    with patch("httpx.get", return_value=_Resp(404)):
        with pytest.raises(FileNotFoundError):
            resolve("inexistente")


@pytest.mark.parametrize("resolve", [
    drive_resolver.resolve_drive_file,
    drive_resolver.resolve_artifact_file,
])
def test_403_vira_permission_error(resolve):
    """Autorizacao e decidida pelo servidor — 403 nao deve virar 'arquivo ausente'."""
    with patch("httpx.get", return_value=_Resp(403)):
        with pytest.raises(PermissionError):
            resolve("de-outro-workspace")


def test_sem_original_name_usa_o_id_como_fallback():
    with patch("httpx.get", return_value=_Resp(200, {"download_url": "https://minio/o"})), \
            patch.object(drive_resolver, "_stream_presigned_to_temp",
                         return_value=("/tmp/o", "", "file-9")) as stream:
        drive_resolver.resolve_drive_file("file-9")

    assert stream.call_args.args[2] == "file-9"
    assert stream.call_args.args[1] == ""


@pytest.mark.asyncio
async def test_read_drive_file_as_remove_o_temp_e_envolve_erro(tmp_path):
    temp = tmp_path / "dados.geojson"
    temp.write_text("{}")

    def _reader_quebrado(_path):
        raise RuntimeError("driver falhou")

    with patch.object(drive_resolver, "resolve_drive_file",
                      return_value=(str(temp), "geojson", "dados.geojson")):
        with pytest.raises(RuntimeError, match="dados.geojson"):
            await drive_resolver.read_drive_file_as(
                "file-1", _reader_quebrado, label="GeoJSON"
            )

    assert not temp.exists(), "temp file deve ser removido mesmo em falha de leitura"
