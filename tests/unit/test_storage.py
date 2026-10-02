# tests/unit/test_storage.py
"""Testes unitarios para o modulo de storage (MinIO)."""
import os
import pytest
from unittest.mock import patch, MagicMock


class TestStorageModule:

    @patch.dict(os.environ, {"MINIO_ROOT_USER": "test-user", "MINIO_ROOT_PASSWORD": "test-pass"})
    @patch("app.core.storage.boto3")
    def test_get_client_creates_singleton(self, mock_boto3):
        """Deve criar cliente S3 apenas uma vez (singleton)."""
        import app.core.storage as storage
        storage._client = None  # Reset singleton

        mock_boto3.client.return_value = MagicMock()
        client1 = storage._get_client()
        client2 = storage._get_client()

        assert client1 is client2
        mock_boto3.client.assert_called_once()

    @patch("app.core.storage._get_client")
    def test_upload_returns_md5(self, mock_get_client):
        """Deve retornar MD5 hex do conteudo enviado."""
        import app.core.storage as storage

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        content = b"test file content"
        md5 = storage.upload("test/key.txt", content)

        assert len(md5) == 32  # MD5 hex
        mock_client.put_object.assert_called_once()

    @patch("app.core.storage._get_client")
    def test_delete_returns_true_on_success(self, mock_get_client):
        """Deve retornar True ao deletar com sucesso."""
        import app.core.storage as storage

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        result = storage.delete("test/key.txt")
        assert result is True

    @patch("app.core.storage._get_client")
    def test_head_returns_metadata(self, mock_get_client):
        """Deve retornar size e etag do objeto."""
        import app.core.storage as storage

        mock_client = MagicMock()
        mock_client.head_object.return_value = {
            "ContentLength": 1024,
            "ETag": '"abc123"',
            "ContentType": "application/json",
        }
        mock_get_client.return_value = mock_client

        result = storage.head("test/key.txt")
        assert result["size"] == 1024
        assert result["etag"] == "abc123"

    @patch("app.core.storage._get_client")
    def test_head_returns_none_on_not_found(self, mock_get_client):
        """Deve retornar None quando objeto nao existe."""
        import app.core.storage as storage
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        mock_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadObject"
        )
        mock_get_client.return_value = mock_client

        result = storage.head("inexistente/key.txt")
        assert result is None

    @patch("app.core.storage._get_external_client")
    def test_presigned_get_generates_url(self, mock_get_ext):
        """Deve gerar URL pre-assinada para download."""
        import app.core.storage as storage

        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = "https://minio/presigned"
        mock_get_ext.return_value = mock_client

        url = storage.presigned_get("test/key.txt", filename="test.txt")
        assert url == "https://minio/presigned"
        mock_client.generate_presigned_url.assert_called_once()

    @patch("app.core.storage._get_external_client")
    def test_presigned_put_generates_url(self, mock_get_ext):
        """Deve gerar URL pre-assinada para upload."""
        import app.core.storage as storage

        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = "https://minio/upload"
        mock_get_ext.return_value = mock_client

        url = storage.presigned_put("test/key.txt")
        assert url == "https://minio/upload"


# ── delete_strict + list_objects + multipart helpers ─────────────────────────

class TestDeleteStrict:
    """Atomicidade do delete (Bug 3): falha real do S3 levanta excecao —
    callers nao apagam o registro do DB, evitando orfaos no MinIO."""

    @patch("app.core.storage._get_client")
    def test_delete_strict_success(self, mock_get_client):
        import app.core.storage as storage
        mock_get_client.return_value = MagicMock()

        # Nao levanta
        storage.delete_strict("k", allow_missing=True)

    @patch("app.core.storage._get_client")
    def test_delete_strict_swallows_no_such_key(self, mock_get_client):
        """allow_missing=True: 'not found' e tratado como sucesso (idempotente)."""
        from botocore.exceptions import ClientError
        import app.core.storage as storage

        mock_client = MagicMock()
        mock_client.delete_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "x"}}, "DeleteObject"
        )
        mock_get_client.return_value = mock_client

        storage.delete_strict("k", allow_missing=True)  # nao levanta

    @patch("app.core.storage._get_client")
    def test_delete_strict_raises_on_real_error(self, mock_get_client):
        from botocore.exceptions import ClientError
        import app.core.storage as storage

        mock_client = MagicMock()
        mock_client.delete_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "x"}}, "DeleteObject"
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(ClientError):
            storage.delete_strict("k", allow_missing=True)

    @patch("app.core.storage._get_client")
    def test_delete_strict_raises_on_missing_when_disabled(self, mock_get_client):
        """allow_missing=False: NoSuchKey tambem levanta."""
        from botocore.exceptions import ClientError
        import app.core.storage as storage

        mock_client = MagicMock()
        mock_client.delete_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "x"}}, "DeleteObject"
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(ClientError):
            storage.delete_strict("k", allow_missing=False)


class TestListObjects:

    @patch("app.core.storage._get_client")
    def test_list_objects_paginated(self, mock_get_client):
        """list_objects deve iterar paginas e produzir dicts com key/size."""
        import app.core.storage as storage

        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = iter([
            {"Contents": [{"Key": "a", "Size": 100}, {"Key": "b", "Size": 200}]},
            {"Contents": [{"Key": "c", "Size": 50}]},
        ])
        mock_client.get_paginator.return_value = mock_paginator
        mock_get_client.return_value = mock_client

        items = list(storage.list_objects(prefix="drive/"))
        assert len(items) == 3
        assert items[0]["key"] == "a" and items[0]["size"] == 100
        assert items[2]["size"] == 50

    @patch("app.core.storage._get_client")
    def test_list_objects_empty_page(self, mock_get_client):
        import app.core.storage as storage

        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = iter([{}])
        mock_client.get_paginator.return_value = mock_paginator
        mock_get_client.return_value = mock_client

        assert list(storage.list_objects()) == []


class TestMultipartHelpers:

    @patch("app.core.storage._get_client")
    def test_list_incomplete_multipart_uploads(self, mock_get_client):
        import app.core.storage as storage

        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = iter([
            {"Uploads": [
                {"Key": "k1", "UploadId": "u1", "Initiated": "2026-01-01"},
                {"Key": "k2", "UploadId": "u2", "Initiated": "2026-01-02"},
            ]}
        ])
        mock_client.get_paginator.return_value = mock_paginator
        mock_get_client.return_value = mock_client

        items = list(storage.list_incomplete_multipart_uploads(prefix=""))
        assert len(items) == 2
        assert items[0] == {"key": "k1", "upload_id": "u1", "initiated": "2026-01-01"}

    @patch("app.core.storage._get_client")
    def test_abort_multipart_upload_success(self, mock_get_client):
        import app.core.storage as storage
        mock_get_client.return_value = MagicMock()

        assert storage.abort_multipart_upload("k", "u") is True

    @patch("app.core.storage._get_client")
    def test_abort_multipart_upload_failure_returns_false(self, mock_get_client):
        import app.core.storage as storage

        mock_client = MagicMock()
        mock_client.abort_multipart_upload.side_effect = Exception("boom")
        mock_get_client.return_value = mock_client

        assert storage.abort_multipart_upload("k", "u") is False
