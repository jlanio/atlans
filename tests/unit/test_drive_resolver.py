"""
drive_resolver: Drive and Artifacts always resolved via the executor's HTTP.

The "server" path (importing app.core.db + downloading directly from MinIO with
boto3) was removed: the engine runs only inside the executor, which has no
database or storage credentials. Authorization and workspace scope stay on the
server, which responds with a short-TTL pre-signed URL.
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
def test_resolve_uses_executor_endpoint(resolve, file_id, endpoint):
    with patch("httpx.get", return_value=_Resp(200, _META)) as get, \
            patch.object(drive_resolver, "_stream_presigned_to_temp",
                         return_value=("/tmp/x.geojson", "geojson", "x.geojson")) as stream:
        out = resolve(file_id)

    assert get.call_args.args[0] == f"https://srv{endpoint}"
    # extension normalized to lowercase and passed on to the streaming.
    assert stream.call_args.args[:3] == (_META["download_url"], "geojson", "x.geojson")
    assert out == ("/tmp/x.geojson", "geojson", "x.geojson")


@pytest.mark.parametrize("resolve", [
    drive_resolver.resolve_drive_file,
    drive_resolver.resolve_artifact_file,
])
def test_404_becomes_file_not_found(resolve):
    with patch("httpx.get", return_value=_Resp(404)):
        with pytest.raises(FileNotFoundError):
            resolve("inexistente")


@pytest.mark.parametrize("resolve", [
    drive_resolver.resolve_drive_file,
    drive_resolver.resolve_artifact_file,
])
def test_403_becomes_permission_error(resolve):
    """Authorization is decided by the server — a 403 must not become 'missing file'."""
    with patch("httpx.get", return_value=_Resp(403)):
        with pytest.raises(PermissionError):
            resolve("de-outro-workspace")


def test_without_original_name_uses_the_id_as_fallback():
    with patch("httpx.get", return_value=_Resp(200, {"download_url": "https://minio/o"})), \
            patch.object(drive_resolver, "_stream_presigned_to_temp",
                         return_value=("/tmp/o", "", "file-9")) as stream:
        drive_resolver.resolve_drive_file("file-9")

    assert stream.call_args.args[2] == "file-9"
    assert stream.call_args.args[1] == ""


@pytest.mark.asyncio
async def test_read_drive_file_as_removes_the_temp_and_wraps_error(tmp_path):
    temp = tmp_path / "dados.geojson"
    temp.write_text("{}")

    def _broken_reader(_path):
        raise RuntimeError("driver falhou")

    with patch.object(drive_resolver, "resolve_drive_file",
                      return_value=(str(temp), "geojson", "dados.geojson")):
        with pytest.raises(RuntimeError, match="dados.geojson"):
            await drive_resolver.read_drive_file_as(
                "file-1", _broken_reader, label="GeoJSON"
            )

    assert not temp.exists(), "temp file deve ser removido mesmo em falha de leitura"
