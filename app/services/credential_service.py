# services/credential_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.exceptions import (
    CredentialNotFoundError,
    CredentialAccessDeniedError,
    CredentialValidationError,
)
from app.crud.credential_crud import CredentialCRUD
from app.models.credential import Credential
from app.schemas.credential import CredentialCreate, CredentialUpdate
from app.core.credentials.connection_builder import build_connection_data, validate_required_fields
from app.core.credentials.schemas import CREDENTIAL_TYPE_SCHEMAS
from app.core.utils.encryption import decrypt_credential_data
from flow.utils.credencial_wfs import autenticacao_wfs

# Os tipos que o nó WFS lê: gravar e "Testar" aplicam as regras DELE.
_TIPOS_DO_WFS = ("geoserver_authkey", "wfs")
# Os tipos cuja `connectionString` é DERIVADA dos campos (ver connection_builder).
_TIPOS_DE_BANCO = ("postgresql", "mysql")


def erro_de_validacao(cred_type: str, data: dict) -> str | None:
    """Por que a credencial não pode ser gravada — ou None.

    Campos obrigatórios de um tipo CONHECIDO e, para as do WFS, o que o nó
    recusaria na execução (chave curta demais para ser protegida nos logs,
    nome de parâmetro que é do próprio WFS, cabeçalho reservado...): a tela
    de Credenciais avisa ao gravar e ao Testar, em vez de o fluxo falhar na
    primeira execução. Tipos fora do catálogo seguem livres (o editor de
    props é justamente o fallback deles).
    """
    erro = validate_required_fields(cred_type, data)
    if erro:
        return erro
    if cred_type in _TIPOS_DO_WFS:
        try:
            autenticacao_wfs(None, {**data, "type": cred_type})
        except ValueError as exc:
            return str(exc)
    return None


def _validate_or_raise(cred_type: str, data: dict) -> None:
    """Recusa a gravação se faltarem campos obrigatórios de um tipo CONHECIDO.

    Antes create/update NUNCA validavam: dava para salvar um postgresql sem
    senha, e o build_connection_data preenchia os buracos com defaults, gerando
    `postgresql://:@localhost:5432/` — uma credencial plausível que só falhava
    na execução do workflow.
    """
    erro = erro_de_validacao(cred_type, data)
    if erro:
        raise CredentialValidationError(erro)


async def create_credential(data: CredentialCreate, db: AsyncSession, owner_id: str | None = None) -> Credential:
    _validate_or_raise(data.type, data.data)
    # Enriquece os dados com connectionString e outros campos derivados do tipo
    enriched = build_connection_data(data.type, data.data)
    cred = Credential(
        name=data.name,
        type=data.type,
        owner_id=owner_id,
        workspace_id=data.workspace_id,
        description=data.description,
        tags=data.tags,
    )
    cred.encrypt_and_store(enriched)
    db.add(cred)
    await db.commit()
    await db.refresh(cred)
    return cred


async def get_credential_metadata(db: AsyncSession, cred_id: UUID, owner_id: str | None = None) -> Credential:
    cred = await CredentialCRUD(db).get(cred_id)
    if not cred:
        raise CredentialNotFoundError("Credencial não encontrada")
    # Verifica propriedade, fail-closed: credencial SEM dono é inacessível a todos.
    #
    # Antes a condição exigia `cred.owner_id` verdadeiro, então uma credencial com
    # owner_id NULL curto-circuitava a checagem e era lida, editada e apagada por
    # qualquer usuário autenticado — inclusive de outro tenant, bastando o UUID
    # (que viaja em claro dentro de Workflow.definition, em properties.credential_id).
    # E órfãs existem de fato: credential_loader já loga "Credencial %s não tem dono
    # (owner_id nulo)". Como este é o único ponto de autorização de GET/PUT/DELETE
    # /credentials/{cred_id} e de GET /credentials/{cred_id}/data — que devolve o
    # segredo descriptografado —, negar é o padrão correto.
    #
    # ESCOPO desta checagem: propriedade (owner-only). O compartilhamento por
    # workspace amplia apenas LEITURA de metadados (a listagem) e uso em
    # execução; a edição, a exclusão e a leitura do SEGREDO (/data) continuam
    # restritas ao dono.
    if owner_id and cred.owner_id != owner_id:
        raise CredentialAccessDeniedError("Acesso negado a esta credencial.")
    return cred


async def delete_credential(db: AsyncSession, cred_id: UUID, owner_id: str | None = None):
    cred = await get_credential_metadata(db, cred_id, owner_id=owner_id)
    await db.delete(cred)
    await db.commit()


async def update_credential(cred_id: UUID, update_data: CredentialUpdate, db: AsyncSession, owner_id: str | None = None) -> Credential:
    cred = await get_credential_metadata(db, cred_id, owner_id=owner_id)

    # Semântica PATCH-like para os metadados: só toca no que o cliente ENVIOU.
    # `model_fields_set` distingue "campo omitido" de "campo enviado como null".
    # Sem isso, um PUT sem `description` (o frontend legado manda só name/type/
    # data) zeraria description/tags/workspace_id já gravados. Com isso, omitir
    # preserva e enviar null limpa — de propósito.
    enviados = update_data.model_fields_set
    tipo_anterior = cred.type
    cred.name = update_data.name
    cred.type = update_data.type
    if "description" in enviados:
        cred.description = update_data.description
    if "tags" in enviados:
        cred.tags = update_data.tags
    if "workspace_id" in enviados:
        cred.workspace_id = update_data.workspace_id

    # Rotação/edição write-only de segredos.
    #
    # `data` ausente/vazio ⇒ mantém os segredos atuais intactos (o caso comum de
    # editar só o nome ou o compartilhamento). `data` presente ⇒ MERGE sobre os
    # segredos existentes descriptografados: o cliente envia apenas os campos que
    # mudaram, e o que ele não mandou é preservado.
    #
    # Isto elimina o antigo caminho destrutivo: encrypt_and_store faz
    # `self.data = {...}` (substitui o blob inteiro), então um `data` PARCIAL
    # antes apagava todos os outros segredos. Agora parcial é seguro e vira o
    # mecanismo de rotação — trocar só a senha manda só a senha.
    #
    # Trocado o TIPO, o `data` é reescrito mesmo sem `data` no pedido: os
    # campos do tipo antigo (a DSN de quando era de banco, o `token` de quando
    # era Bearer) não ficam cifrados no blob de uma credencial de outro tipo —
    # e o novo tipo precisa ter os obrigatórios dele, senão a troca gravaria
    # uma credencial que nenhum nó consegue usar.
    mudou_de_tipo = update_data.type != tipo_anterior
    if update_data.data or mudou_de_tipo:
        atuais = decrypt_credential_data(cred.data or {})
        # Para tipos de banco a connectionString é DERIVADA (recomputada de
        # host/user/... pelo build_connection_data adiante), então a antiga não
        # fica — nem numa credencial que DEIXOU de ser de banco, onde a DSN com
        # a senha de antes seguiria sendo injetada num nó de banco. Para um
        # tipo livre que sempre foi livre, "connectionString" pode ser um campo
        # legítimo do usuário: aí NÃO se mexe.
        if update_data.type in _TIPOS_DE_BANCO or tipo_anterior in _TIPOS_DE_BANCO:
            atuais.pop("connectionString", None)
        mesclado = {**atuais, **(update_data.data or {})}
        esquema = CREDENTIAL_TYPE_SCHEMAS.get(update_data.type)
        if mudou_de_tipo and esquema is not None:
            permitidas = {f.key for f in esquema.fields} | {"expires_at"}
            mesclado = {k: v for k, v in mesclado.items() if k in permitidas}
        _validate_or_raise(update_data.type, mesclado)
        enriched = build_connection_data(update_data.type, mesclado)
        cred.encrypt_and_store(enriched)

    await db.commit()
    await db.refresh(cred)
    return cred


async def list_credential_metadata(
    db: AsyncSession,
    owner_id: str | None = None,
    type: str | None = None,
    workspace_ids: list[str] | None = None,
) -> list[Credential]:
    return await CredentialCRUD(db).list(owner_id=owner_id, type=type, workspace_ids=workspace_ids)
