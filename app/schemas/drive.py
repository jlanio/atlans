from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Optional, List
from datetime import datetime


# ── Arquivo ───────────────────────────────────────────────────────────────────

class WorkspaceFileOut(BaseModel):
    id_hash:       str
    workspace_id:  str
    original_name: str
    extension:     str
    mime_type:     Optional[str]
    size:          Optional[int]
    content_md5:   Optional[str] = None
    uploaded_by:   Optional[str]
    status:        str = "confirmed"
    created_at:    datetime
    updated_at:    Optional[datetime] = None
    # Last CONTENT write — it is what the listing sorts by. `updated_at` changes
    # with any update of the row (renaming, for example), so showing it as
    # "last write" did not explain the order the user saw.
    content_written_at: Optional[datetime] = None

    # Content locality (LGPD). 'minio' is the usual case; 'executor' means the
    # bytes never left the executor's machine — download through the platform
    # does not exist, and the UI needs to say so BEFORE the click.
    content_location: str = "minio"
    content_executor_id: Optional[str] = None
    # CRS, bbox, feature_count, columns, geometry_type. In catalog mode it is the
    # only thing the server knows about the content.
    spatial_metadata: Optional[dict] = None

    class Config:
        from_attributes = True


class WorkspaceFileList(BaseModel):
    items: List[WorkspaceFileOut]
    total: int


# ── Global settings ───────────────────────────────────────────────────────────

class PlatformFileSettingsOut(BaseModel):
    max_size_mb: int
    updated_at:  Optional[datetime]

    class Config:
        from_attributes = True


class PlatformFileSettingsUpdate(BaseModel):
    max_size_mb: int = Field(..., ge=1, le=10240, description="Tamanho máximo em MB")


# ── Allowed extensions ────────────────────────────────────────────────────────

class AllowedExtensionOut(BaseModel):
    extension:  str
    enabled:    bool
    created_at: datetime

    class Config:
        from_attributes = True


class AllowedExtensionCreate(BaseModel):
    extension: str = Field(..., min_length=1, max_length=20)


# ── Executor endpoints (schemas estritos: extra='forbid' bloqueia keys desconhecidos) ──

class ExecutorRegisterRequest(BaseModel):
    """Record of a dataset that STAYS on the executor's disk (GeoSync catalog).

    There is no upload: the server keeps only the catalog. There is
    deliberately no file path field — the executor finds the dataset again
    through its own sync manifest, and a path from the user's file system has
    no reason to exist in the server's database.
    """
    model_config = ConfigDict(extra="forbid")
    filename: str = Field(..., min_length=1, max_length=512)
    workspace_id: Optional[str] = Field(default=None, max_length=128)
    size: int = Field(..., ge=0, le=10 * 1024**3)
    # Dataset name in the executor's local manifest. It goes back to it on read
    # as a diagnostic hint; it is not used to build a path.
    dataset_name: Optional[str] = Field(default=None, max_length=512)
    spatial_metadata: dict = Field(default_factory=dict)


class ExecutorUploadUrlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    filename: str = Field(..., min_length=1, max_length=512)
    size: int = Field(..., ge=0, le=10 * 1024**3)
    workspace_id: Optional[str] = Field(default=None, max_length=128)
    s3_key_override: Optional[str] = Field(default=None, max_length=1024)
    content_type: Optional[str] = Field(default=None, max_length=128)
    overwrite: bool = Field(
        default=False,
        description=(
            "Reaproveita o arquivo de mesmo nome no workspace em vez de criar "
            "outro. Mantém id_hash e s3_key, então referências ao arquivo "
            "continuam válidas e o objeto anterior não vira órfão."
        ),
    )


class ExecutorPresignUploadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    s3_key: str = Field(..., min_length=1, max_length=1024)
    content_type: str = Field(default="application/octet-stream", max_length=128)


class ExecutorPresignDownloadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    s3_key: str = Field(..., min_length=1, max_length=1024)


class ExecutorTriggerWorkflowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workflow_id_hash: str = Field(..., min_length=1, max_length=128)
    inputs: dict[str, Any] = Field(default_factory=dict)
