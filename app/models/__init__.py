from app.models import models, user, workspace, credential, system_config, workspace_member, artifact, workspace_file, platform_file_settings, executor, workspace_executor, api_token, conversa, fonte_de_dados, uso_do_assistente  # noqa: F401

# The tables of the extensions present (app/extensoes), after the core ones.
from app.extensoes import importar_modelos

importar_modelos()
