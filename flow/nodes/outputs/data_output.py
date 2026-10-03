import asyncio
import json

import geopandas as gpd
import pandas as pd

from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.artifact_helpers import (
    EXECUTOR,
    describe_locality,
    persistir_artefato,
    locality_property,
    resolve_locality,
    save_to_geosync_folder,
    upload_artifact_to_minio,
)
from flow.utils.executor_http import slugify
from flow.utils.geo_helpers import gdf_para_geojson


@register_node
class DataOutput(BaseNode):
    @classmethod
    def description(cls) -> dict:
        return {
            "name":        "DataOutput",
            "alias":       "Saída de Dados",
            "description": (
                "Persiste o resultado de um nó no Drive do Workspace ou como Artefato "
                "para download via API. Suporta GeoDataFrame (salvo como GeoJSON) e "
                "dict/list (salvo como JSON). Conforme a localidade dos dados, envia "
                "ao armazenamento na nuvem ou grava apenas no disco do executor."
            ),
            "type": "output",
            "dynamic_output": False,
            "outputs": [
                {"name": "artifact_filename", "type": "string", "description": "Nome do arquivo salvo"},
                {"name": "artifact_format", "type": "string", "description": "Formato: geojson ou json"},
                {"name": "artifact_features", "type": "number", "description": "Numero de features (apenas GeoDataFrame)"},
                {"name": "artifact_s3_key", "type": "string", "description": "S3 key no MinIO, ou o caminho local quando o conteúdo fica no executor"},
            ],
            "properties": [
                # Visual layout symmetric to DataInput:
                # 1) Destination/Source (context)  2) content/identity (label)
                # 3) specific options (isPublic, credential_id)  4) crs last.
                {
                    "name":        "context",
                    "label":       "Destino",
                    "type":        "select",
                    "default":     "artifacts",
                    "description": "Onde os dados serão salvos.",
                    "options": [
                        {"value": "artifacts", "label": "Artefatos (download via API)"},
                        {"value": "drive",     "label": "Drive do Workspace"},
                    ],
                },
                {
                    "name":        "label", "required": True,
                    "label":       "Nome do arquivo",
                    "type":        "string",
                    "default":     "",
                    "description": "Nome do arquivo salvo. Ex: 'resultado_buffer'.",
                },
                {
                    "name":        "overwrite",
                    "label":       "Sobrescrever se já existir",
                    "type":        "boolean",
                    "default":     False,
                    "description": (
                        "Se ligado e já houver um arquivo com este nome no Drive, "
                        "ele é substituído em vez de gerar uma cópia. O arquivo mantém "
                        "o mesmo id, então nós que o utilizam passam a ler a versão nova."
                    ),
                    "visibleWhen": {"field": "context", "in": ["drive"]},
                },
                {
                    "name":        "isPublic",
                    "label":       "Público",
                    "type":        "boolean",
                    "default":     True,
                    "description": (
                        "Se ligado, o artefato tem link de download público (sem autenticação). "
                        "Se desligado, exige uma credencial Bearer para o download."
                    ),
                    # A local artifact has no download to protect, so offering
                    # access control there would promise a decision that
                    # does not exist.
                    "visibleWhen": [
                        {"field": "context", "in": ["artifacts"]},
                        {"field": "localidade", "in": ["herdar"]},
                    ],
                },
                {
                    "name":             "credential_id",
                    "label":            "Credencial de download",
                    "type":             "credential",
                    "default":          "",
                    "description":      "Token Bearer que protege o download do artefato.",
                    "credential_types": ["webhook_token"],
                    "visibleWhen": [
                        {"field": "context", "in": ["artifacts"]},
                        {"field": "isPublic", "in": [False, "false"]},
                        {"field": "localidade", "in": ["herdar"]},
                    ],
                },
                # Applies to BOTH destinations: a Drive file can also stay only
                # on the executor, cataloged — the same outcome as GeoSync in
                # catalog mode, for a file the workflow has just produced.
                locality_property(),
                {
                    "name":        "crs",
                    "label":       "CRS de destino",
                    "type":        "string",
                    "default":     "EPSG:4326",
                    "description": "CRS de saida para GeoDataFrame (ignorado para outros tipos).",
                },
            ],
        }

    async def execute(self, inputs: dict) -> dict:
        self.validate()
        label       = self.get_param("label", "").strip()
        crs         = self.get_param("crs", "EPSG:4326").strip() or "EPSG:4326"
        context     = self.get_param("context", "artifacts")
        is_public   = self.get_param("isPublic", True)
        # `validate()` above already guarantees a bool for type=boolean properties
        # (parameter_validation rejects strings), so there is no coercion here.
        overwrite   = self.get_param("overwrite", False)
        localidade, quem = resolve_locality(self.get_param("localidade", None))
        manter_local = localidade == EXECUTOR

        if not label:
            raise ValueError("Parametro 'label' e obrigatorio no no DataOutput.")

        workspace_id, task_id = self.require_execution_context()

        safe_label   = slugify(label)

        # Access control: only makes sense for the Artifacts context.
        # Public → no credential; non-public → requires a Bearer credential.
        create_drive_entry = (context == "drive")
        if create_drive_entry or manter_local:
            # Local content has no download through the platform — there is nothing a
            # credential would protect, and requiring one would block the node
            # over a promise it does not make.
            credential_id = None
        elif is_public:
            credential_id = None
        else:
            credential_id = self.get_param("credential_id", "") or None
            if not credential_id:
                raise ValueError(
                    "Artefato não-público exige uma credencial (webhook_token) para proteger o download."
                )

        # Looks for a value in the inputs (GeoDataFrame > DataFrame > dict/list).
        # GeoDataFrame is a subclass of DataFrame, so test it first.
        value = None
        for v in inputs.values():
            if isinstance(v, gpd.GeoDataFrame):
                value = v
                break
            if isinstance(v, pd.DataFrame):
                value = v
                break
            if isinstance(v, (dict, list)):
                value = v
                break

        if value is None:
            raise ValueError(
                f"DataOutput '{label}': nenhum GeoDataFrame, DataFrame, dict ou list encontrado. "
                f"Inputs: {list(inputs.keys())}"
            )

        # Serializa conforme tipo
        if isinstance(value, gpd.GeoDataFrame):
            filename = f"{safe_label}.geojson"
            content = await asyncio.to_thread(gdf_para_geojson, value, crs)
            features = len(value)
            fmt = "geojson"
            content_type = "application/geo+json"
        else:
            # A plain DataFrame becomes a list of records before serializing.
            if isinstance(value, pd.DataFrame):
                value = value.to_dict(orient="records")
            filename = f"{safe_label}.json"
            content = json.dumps(value, default=str, ensure_ascii=False)
            features = None
            fmt = "json"
            content_type = "application/json"

        # Before any destination message: this is the only place where whoever
        # built the workflow sees what "Herdar do executor" became on this machine.
        self.log(describe_locality(localidade, quem))

        if manter_local and create_drive_entry:
            # Writes to the synced folder and lets GeoSync catalog it on the next
            # cycle. Does NOT emit `__artifact__`: GeoSync is what creates the
            # Drive row, and emitting would make the server derive an s3_key for
            # an object that never existed — the UI would offer a 404 download.
            destino = await asyncio.to_thread(
                save_to_geosync_folder,
                content.encode("utf-8"), filename, workspace_id, overwrite,
            )
            self.log(
                f"Arquivo gravado na pasta do GeoSync: {destino} ({fmt}). "
                "Ele aparece no Drive do workspace em até 10 s, catalogado — "
                "os bytes não saem desta máquina."
            )
            return {
                "output": {
                    "artifact_filename": filename,
                    "artifact_format":   fmt,
                    "artifact_features": features,
                    # The NAME, not the absolute path that was just logged:
                    # this value travels through the workflow and is stored in the
                    # run, and an absolute path would leak the directory structure
                    # of the user's machine — the same reason
                    # `local_relative_path` is relative.
                    "artifact_s3_key":   filename,
                },
            }

        if manter_local:
            s3_key, artifact_meta = await asyncio.to_thread(
                persistir_artefato,
                localidade=localidade,
                content=content.encode("utf-8"),
                filename=filename,
                workspace_id=workspace_id,
                task_id=task_id,
                label=label,
                fmt=fmt,
                features=features,
                credential_id=credential_id,
            )
        else:
            # Upload to MinIO (with local fallback on the executor)
            s3_key, artifact_meta = await asyncio.to_thread(
                upload_artifact_to_minio,
                content=content.encode("utf-8"),
                filename=filename,
                content_type=content_type,
                workspace_id=workspace_id,
                task_id=task_id,
                label=label,
                fmt=fmt,
                features=features,
                credential_id=credential_id,
                create_drive_entry=create_drive_entry,
                # Overwrite only exists in Drive: in Artifacts each run already has
                # its own s3_key (includes the task_id), so there is no collision.
                overwrite=overwrite and create_drive_entry,
            )
        artifact_meta["context"] = context

        if artifact_meta.get("content_location") == "executor":
            self.log(
                f"Dados mantidos apenas neste executor: {filename} ({fmt}). "
                "Nada foi enviado para a nuvem."
            )
        elif artifact_meta.get("local_fallback"):
            self.log(f"Dados salvos localmente (executor fallback): {filename} ({fmt})")
        elif create_drive_entry:
            # `drive_reused` comes from the server and says what actually happened. The
            # previous message announced the overwrite whenever the option was
            # on, even when the server created a new row — which is exactly
            # the case one needs to see.
            if artifact_meta.get("drive_reused"):
                self.log(f"Arquivo sobrescrito no Drive: {filename} ({fmt})")
            elif overwrite:
                self.log(
                    f"Salvo no Drive como arquivo novo: {filename} ({fmt}). "
                    "Não havia arquivo confirmado com este nome para sobrescrever."
                )
            else:
                self.log(f"Dados salvos no Drive: {filename} ({fmt})")
        else:
            self.log(f"Dados salvos no MinIO: {s3_key} ({fmt})")

        return {
            "output": {
                "artifact_filename": filename,
                "artifact_format":   fmt,
                "artifact_features": features,
                "artifact_s3_key":   s3_key,
            },
            "__artifact__": artifact_meta,
        }
