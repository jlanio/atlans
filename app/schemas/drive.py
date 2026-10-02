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
    # Ultima escrita de CONTEUDO — e por ela que a listagem ordena. `updated_at`
    # muda com qualquer update da linha (renomear, por exemplo), entao exibi-lo
    # como "ultima escrita" nao explicava a ordem que o usuario via.
    content_written_at: Optional[datetime] = None

    # Localidade do conteúdo (LGPD). 'minio' é o caso de sempre; 'executor'
    # significa que os bytes nunca saíram da máquina do executor — o download
    # pela plataforma não existe, e a UI precisa dizer isso ANTES do clique.
    content_location: str = "minio"
    content_executor_id: Optional[str] = None
    # CRS, bbox, feature_count, columns, geometry_type. No modo catálogo é a
    # única coisa que o servidor sabe sobre o conteúdo.
    spatial_metadata: Optional[dict] = None

    class Config:
        from_attributes = True


class WorkspaceFileList(BaseModel):
    items: List[WorkspaceFileOut]
    total: int


# ── Configurações globais ─────────────────────────────────────────────────────

class PlatformFileSettingsOut(BaseModel):
    max_size_mb: int
    updated_at:  Optional[datetime]

    class Config:
        from_attributes = True


class PlatformFileSettingsUpdate(BaseModel):
    max_size_mb: int = Field(..., ge=1, le=10240, description="Tamanho máximo em MB")


# ── Extensões permitidas ──────────────────────────────────────────────────────

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
    """Registro de dataset que PERMANECE no disco do executor (GeoSync catálogo).

    Não há upload: o servidor guarda só o catálogo. Deliberadamente não existe
    campo de caminho de arquivo — o executor reencontra o dataset pelo próprio
    manifesto de sync, e um caminho do sistema de arquivos do usuário não tem
    por que existir no banco do servidor.
    """
    model_config = ConfigDict(extra="forbid")
    filename: str = Field(..., min_length=1, max_length=512)
    workspace_id: Optional[str] = Field(default=None, max_length=128)
    size: int = Field(..., ge=0, le=10 * 1024**3)
    # Nome do dataset no manifesto local do executor. Volta para ele na leitura
    # como pista de diagnóstico; não é usado para montar caminho.
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
