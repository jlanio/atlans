import asyncio
import json

import geopandas as gpd
import pandas as pd

from flow.registry import register_node
from flow.nodes.base import BaseNode
from flow.utils.artifact_helpers import (
    EXECUTOR,
    descrever_localidade,
    persistir_artefato,
    propriedade_localidade,
    resolver_localidade,
    salvar_na_pasta_do_geosync,
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
                # Padrao visual simetrico ao DataInput:
                # 1) Destino/Origem (context)  2) conteudo/identidade (label)
                # 3) opcoes especificas (isPublic, credential_id)  4) crs por ultimo.
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
                    # Um artefato local nao tem download para proteger, entao
                    # oferecer o controle de acesso ali prometeria uma decisao
                    # que nao existe.
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
                # Vale nos DOIS destinos: um arquivo do Drive tambem pode ficar
                # so no executor, catalogado — e o mesmo desfecho do GeoSync em
                # modo catalogo, para um arquivo que o workflow acabou de gerar.
                propriedade_localidade(),
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
        # `validate()` acima ja garante bool para propriedades type=boolean
        # (parameter_validation rejeita string), entao nao ha coercao aqui.
        overwrite   = self.get_param("overwrite", False)
        localidade, quem = resolver_localidade(self.get_param("localidade", None))
        manter_local = localidade == EXECUTOR

        if not label:
            raise ValueError("Parametro 'label' e obrigatorio no no DataOutput.")

        workspace_id, task_id = self.require_execution_context()

        safe_label   = slugify(label)

        # Controle de acesso: so faz sentido para o contexto Artefatos.
        # Publico → sem credencial; nao-publico → exige credencial Bearer.
        create_drive_entry = (context == "drive")
        if create_drive_entry or manter_local:
            # Conteudo local nao tem download pela plataforma — nao ha o que uma
            # credencial protegesse, e exigi-la barraria o no por uma promessa
            # que ele nao faz.
            credential_id = None
        elif is_public:
            credential_id = None
        else:
            credential_id = self.get_param("credential_id", "") or None
            if not credential_id:
                raise ValueError(
                    "Artefato não-público exige uma credencial (webhook_token) para proteger o download."
                )

        # Busca valor nos inputs (GeoDataFrame > DataFrame > dict/list).
        # GeoDataFrame eh subclasse de DataFrame, entao testa primeiro.
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
            # DataFrame puro vira lista de records antes de serializar.
            if isinstance(value, pd.DataFrame):
                value = value.to_dict(orient="records")
            filename = f"{safe_label}.json"
            content = json.dumps(value, default=str, ensure_ascii=False)
            features = None
            fmt = "json"
            content_type = "application/json"

        # Antes de qualquer mensagem de destino: e o unico lugar onde quem
        # montou o fluxo ve o que "Herdar do executor" virou nesta maquina.
        self.log(descrever_localidade(localidade, quem))

        if manter_local and create_drive_entry:
            # Grava na pasta sincronizada e deixa o GeoSync catalogar no ciclo
            # seguinte. NAO emite `__artifact__`: quem cria a linha no Drive e o
            # GeoSync, e emitir faria o servidor derivar uma s3_key para um
            # objeto que nunca existiu — a UI ofereceria um download 404.
            destino = await asyncio.to_thread(
                salvar_na_pasta_do_geosync,
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
                    # O NOME, e nao o caminho absoluto que acabou de ser logado:
                    # este valor circula pelo workflow e fica gravado no run,
                    # e um caminho absoluto vazaria a estrutura de diretorios da
                    # maquina do usuario — mesma razao pela qual
                    # `local_relative_path` e relativo.
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
            # Upload para MinIO (com fallback local no executor)
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
                # Sobrescrever so existe no Drive: em Artefatos cada execucao ja tem
                # a sua propria s3_key (inclui o task_id), entao nao ha colisao.
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
            # `drive_reused` vem do servidor e diz o que aconteceu de fato. A
            # mensagem anterior anunciava a sobrescrita sempre que a opcao
            # estivesse ligada, mesmo quando o servidor criou linha nova — que e
            # exatamente o caso que se precisa enxergar.
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
