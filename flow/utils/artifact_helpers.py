# flow/utils/artifact_helpers.py
"""
Helper compartilhado para upload de artefatos ao MinIO.

Upload via pre-signed URL obtida do servidor (o executor nao tem credenciais
do MinIO). Fallback: salvar localmente se o upload falhar.

Tambem define a LOCALIDADE DOS DADOS (LGPD) — se o resultado de um no de saida
sai da maquina ou nao. O vocabulario vive aqui, e nao em cada no, porque a
escolha precisa significar a mesma coisa em todos eles: tres nomes para o mesmo
conceito foi exatamente o problema que esta unificacao resolve.
"""
import logging
import os
from typing import BinaryIO

logger = logging.getLogger(__name__)


# ── Localidade dos dados (LGPD) ───────────────────────────────────────────────

HERDAR = "herdar"
SERVIDOR = "servidor"
EXECUTOR = "executor"


class EnvioBloqueadoError(RuntimeError):
    """O executor retem os dados e o no so funciona enviando.

    Excecao propria, e nao um `ValueError`, porque nao e erro de configuracao do
    no: o workflow esta correto e a MAQUINA e que nao permite. Quem le o log
    precisa distinguir "voce montou errado" de "aqui nao pode".
    """


def localidade_padrao() -> str:
    """Politica DESTA maquina: `servidor` ou `executor`.

    Lida de `EXECUTOR_SYNC_MODE == "catalog"`, que e a MESMA variavel que a tela
    de GeoSync do app desktop ja grava sob o rotulo "Localidade dos dados →
    Manter apenas no executor". Reusa-la, em vez de criar outra, e o que faz o
    rotulo passar a valer para tudo que sai daqui — ate agora ele protegia a
    pasta sincronizada e deixava os workflows enviando o que quisessem.

    Lida do ambiente pelo mesmo motivo de `artifacts_root()`: `flow/` roda tanto
    dentro do executor quanto in-process no servidor, e importar
    `executor/config.py` daqui inverteria a dependencia. No servidor a variavel
    nao existe, e a politica e `servidor` — que e o correto: o conteudo ja esta
    la.
    """
    modo = (os.getenv("EXECUTOR_SYNC_MODE") or "").strip().lower()
    return EXECUTOR if modo == "catalog" else SERVIDOR


def resolver_localidade(escolha: str | None) -> tuple[str, str]:
    """Traduz a escolha do no em (localidade efetiva, quem decidiu).

    A politica da maquina e uma PROIBICAO, nao um padrao: o workflow pode
    apertar, nunca afrouxar. Por isso a regra e um `or` — basta um dos dois pedir
    para o conteudo ficar.

    `quem` e 'executor' ou 'nó', para o log dizer a verdade em vez de "herdado"
    quando os dois coincidiram.
    """
    pediu_local = (escolha or HERDAR).strip().lower() == EXECUTOR
    if localidade_padrao() == EXECUTOR:
        return EXECUTOR, "executor"
    return (EXECUTOR, "nó") if pediu_local else (SERVIDOR, "executor")


def descrever_localidade(efetiva: str, quem: str) -> str:
    """Frase para o log do run. E o UNICO lugar onde quem montou o fluxo ve o
    que "Herdar do executor" virou — o editor nao conhece a maquina de destino."""
    onde = "fica apenas neste executor" if efetiva == EXECUTOR else "vai para o servidor"
    return f"Localidade dos dados: o conteúdo {onde} (definido pelo {quem})."


def exigir_envio_permitido(no: str, o_que_exige: str) -> None:
    """Barra um no que SO funciona enviando, quando a maquina retem os dados.

    Ponto unico da recusa: a mensagem mora aqui, e um no novo que dependa de
    enviar tem uma linha para chamar em vez de reescrever a explicacao.

    Falha em vez de pular. Um no que se omite deixa o run verde e ninguem
    descobre que a camada nunca foi publicada nem que o e-mail saiu sem anexo —
    e o pior dos desfechos, porque nao produz nenhum sinal.
    """
    if localidade_padrao() != EXECUTOR:
        return
    # Sem seta (U+2192) nem qualquer caractere fora do latin-1: esta mensagem
    # atravessa o log do executor, que pode acabar num console cp1252 — e um
    # UnicodeEncodeError ao EXPLICAR uma recusa trocaria a explicacao por um
    # traceback.
    raise EnvioBloqueadoError(
        f"{no} não foi executado.\n\n"
        "Este executor está configurado para manter os dados apenas nele "
        '(app do executor: GeoSync > Localidade dos dados > "Manter apenas no '
        f'executor"), e {o_que_exige}.\n\n'
        f"O que fazer: remova o nó {no} deste workflow, ou execute-o num "
        "executor que possa enviar dados ao servidor."
    )


def propriedade_localidade(visible_when=None) -> dict:
    """Fragmento de schema do campo `localidade`, identico em todo no de saida.

    Copiar o dict em cada no faria os rotulos divergirem com o tempo.

    SEM `description`: o painel de configuracao a renderiza como um paragrafo
    logo abaixo do campo, e o texto que explicava a politica inteira ocupava
    mais espaco que todos os outros campos do no somados. Os dois rotulos ja
    dizem o que cada opcao faz, e o log do run informa a localidade efetiva a
    cada execucao — que e onde a informacao importa de fato, porque so ali se
    sabe em que maquina o fluxo rodou.

    NAO existe a opcao "enviar para o servidor". Seria a unica escolha capaz de
    contrariar a politica da maquina, e uma opcao que o executor ignora em
    silencio e pior que opcao nenhuma: a pessoa marca, acredita, e o
    comportamento e outro.
    """
    prop = {
        "name":    "localidade",
        "label":   "Localidade dos dados",
        "type":    "select",
        "default": HERDAR,
        "options": [
            {"value": HERDAR,   "label": "Herdar do executor"},
            {"value": EXECUTOR, "label": "Manter apenas no executor"},
        ],
    }
    if visible_when is not None:
        prop["visibleWhen"] = visible_when
    return prop


def _upload_via_presigned_url(content: bytes, filename: str, content_type: str,
                               workspace_id: str, task_id: str,
                               create_drive_entry: bool = False,
                               overwrite: bool = False) -> tuple[str, str | None, bool]:
    """
    Upload via pre-signed URL (fluxo do executor).

    create_drive_entry=True  → POST /drive/executor-upload-url (cria WorkspaceFile no Drive)
    create_drive_entry=False → POST /drive/executor-presign-upload (apenas sobe ao MinIO)

    `overwrite` so tem efeito no fluxo do Drive: o servidor reaproveita o
    arquivo de mesmo nome em vez de criar outro.

    Retorna (s3_key, drive_file_id | None, reused). `reused` e o que o SERVIDOR
    fez — nao o que se pediu. Um servidor antigo nao devolve o campo; nesse caso
    fica False e o chamador nao afirma o que nao pode verificar.
    """
    import httpx
    from flow.utils.executor_http import get_agent_http_config
    from flow.utils.http_retry import retry_sync

    base_url, headers, verify = get_agent_http_config()

    s3_key = f"artifacts/{workspace_id}/{task_id}/{filename}"

    if create_drive_entry:
        # Fluxo completo: cria WorkspaceFile + upload + confirmação.
        # NAO envolvemos o POST executor-upload-url em retry — ele cria um
        # WorkspaceFile e re-tentar poderia duplicar a entrada no Drive.
        # Só o PUT (upload ao MinIO) é idempotente (sobrescreve o objeto).
        resp = httpx.post(
            f"{base_url}/drive/executor-upload-url",
            json={"filename": filename, "size": len(content), "workspace_id": workspace_id, "s3_key_override": s3_key, "content_type": content_type, "overwrite": overwrite},
            headers=headers, verify=verify, follow_redirects=True, timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        upload_url = data["upload_url"]
        file_id = data["id_hash"]
        s3_key = data.get("s3_key", s3_key)
        reused = bool(data.get("reused", False))

        def _put() -> None:
            put_resp = httpx.put(
                upload_url, content=content,
                headers={"Content-Type": content_type}, timeout=120, verify=verify,
            )
            put_resp.raise_for_status()
        retry_sync(_put, label=f"artifact upload {s3_key}")

        confirm_resp = httpx.post(
            f"{base_url}/drive/executor-confirm-upload/{file_id}",
            headers=headers, verify=verify, follow_redirects=True, timeout=15,
        )
        confirm_resp.raise_for_status()

        logger.info(
            "Artefato enviado ao MinIO + Drive via pre-signed URL: %s (%s)",
            s3_key, "sobrescreveu arquivo existente" if reused else "arquivo novo",
        )
        return s3_key, file_id, reused
    else:
        # Fluxo simples: apenas sobe ao MinIO (sem WorkspaceFile). Presign + PUT
        # sao idempotentes (s3_key fixo) → retry do bloco inteiro é seguro;
        # re-obtem a presign URL a cada tentativa (TTL curto).
        def _presign_and_put() -> None:
            resp = httpx.post(
                f"{base_url}/drive/executor-presign-upload",
                json={"s3_key": s3_key, "content_type": content_type},
                headers=headers, verify=verify, follow_redirects=True, timeout=30,
            )
            resp.raise_for_status()
            upload_url = resp.json()["upload_url"]
            put_resp = httpx.put(
                upload_url, content=content,
                headers={"Content-Type": content_type}, timeout=120, verify=verify,
            )
            put_resp.raise_for_status()
        retry_sync(_presign_and_put, label=f"artifact upload {s3_key}")

        logger.info("Artefato enviado ao MinIO via pre-signed URL: %s", s3_key)
        return s3_key, None, False


def artifacts_root() -> str:
    """Raiz dos artefatos no disco do executor.

    Ponto unico: a resolucao de um artefato local (flow/utils/drive_resolver.py)
    e a limpeza por retencao (executor/artifact_purge.py) precisam chegar
    exatamente ao mesmo diretorio que a escrita usou.
    """
    return os.getenv("EXECUTOR_ARTIFACTS_DIR", os.getenv("ARTIFACT_DIR", "./artifacts"))


def local_relative_path(workspace_id: str, task_id: str, filename: str) -> str:
    """Caminho do artefato RELATIVO a `artifacts_root()`, com barras normais.

    Relativo, e nao absoluto, porque este valor viaja ate o servidor e volta: um
    caminho absoluto vazaria a estrutura de diretorios da maquina do usuario e
    quebraria se o `EXECUTOR_ARTIFACTS_DIR` mudasse entre execucoes.
    """
    return f"{workspace_id}/{task_id}/{filename}"


def _write_local(content: bytes, workspace_id: str, task_id: str, filename: str) -> str:
    """Grava o artefato no disco do executor. Retorna o caminho absoluto."""
    task_dir = os.path.join(artifacts_root(), workspace_id, task_id)
    os.makedirs(task_dir, exist_ok=True)
    file_path = os.path.join(task_dir, filename)

    with open(file_path, "wb") as fh:
        fh.write(content)
    return file_path


def _save_local_fallback(
    content: bytes,
    workspace_id: str,
    task_id: str,
    filename: str,
) -> str:
    """Salva o artefato localmente porque o UPLOAD FALHOU. Retorna o caminho.

    Nao confundir com `save_artifact_local`: aqui o local e degradacao, la e
    politica. Os dois gravam no mesmo lugar, mas significam coisas opostas para
    quem le o log e para o registro no servidor.
    """
    file_path = _write_local(content, workspace_id, task_id, filename)
    logger.info("Artefato salvo localmente (fallback): %s", file_path)
    return file_path


def save_artifact_local(
    content: bytes | None = None,
    fileobj: BinaryIO | None = None,
    filename: str = "",
    workspace_id: str = "",
    task_id: str = "",
    label: str = "",
    fmt: str = "",
    features: int | None = None,
    credential_id: str | None = None,
) -> tuple[str, dict]:
    """
    Grava o artefato APENAS no disco do executor. Nenhum byte sai da maquina.

    Existe para dado pessoal (LGPD): o servidor recebe so o catalogo — nome,
    formato, tamanho, contagem de feicoes — e o registro de qual executor tem o
    arquivo. O conteudo nunca chega ao MinIO nem trafega pela rede.

    Mesma assinatura e mesmo retorno de `upload_artifact_to_minio`, para que o
    no de saida escolha entre os dois sem tratar cada um de um jeito.

    NAO ha fallback aqui, e isso e deliberado: se a gravacao local falhar, a
    excecao sobe e o no falha. Cair para o upload seria enviar para a nuvem
    justamente o dado que foi marcado para nao sair.
    """
    if not filename:
        raise ValueError("filename é obrigatório para salvar artefato.")
    if not workspace_id or not task_id:
        raise ValueError("workspace_id e task_id são obrigatórios.")

    if content is None and fileobj is not None:
        pos = fileobj.tell()
        content = fileobj.read()
        fileobj.seek(pos)
    if content is None:
        raise ValueError("Deve fornecer content (bytes) ou fileobj.")

    file_path = _write_local(content, workspace_id, task_id, filename)
    rel = local_relative_path(workspace_id, task_id, filename)
    logger.info("Artefato mantido no executor (não enviado ao MinIO): %s", file_path)

    return rel, {
        "output_key": label or filename,
        "format": fmt,
        "features": features,
        "filename": filename,
        "credential_id": credential_id,
        # Sem s3_key: nao ha objeto. O servidor NAO deve derivar uma — ver
        # _register_artifacts em app/core/run_result_consumer.py.
        "s3_key": None,
        "content_location": "executor",
        "local_path": rel,
        "size_bytes": len(content),
        # Distinto de `local_fallback`: aqui o local foi pedido, nao foi falha.
        "local_fallback": False,
        "drive_file_id": None,
        "drive_reused": False,
    }


def persistir_artefato(
    localidade: str,
    content: bytes | None = None,
    fileobj: BinaryIO | None = None,
    filename: str = "",
    content_type: str = "application/octet-stream",
    workspace_id: str = "",
    task_id: str = "",
    label: str = "",
    fmt: str = "",
    features: int | None = None,
    credential_id: str | None = None,
) -> tuple[str, dict]:
    """Grava o artefato onde a localidade JA RESOLVIDA mandar.

    Existe para que os nos de saida nao repitam o `if` — que e o ponto exato
    onde dado pessoal vaza se alguem esquecer de copia-lo num no novo.
    `save_artifact_local` e `upload_artifact_to_minio` tem assinatura e retorno
    identicos justamente para isto.

    Recebe a localidade ja resolvida, e nao a escolha crua, porque quem chama
    precisa dela de todo jeito para logar (ver `descrever_localidade`) —
    resolver duas vezes abriria espaco para as duas divergirem.
    """
    if localidade == EXECUTOR:
        return save_artifact_local(
            content=content, fileobj=fileobj, filename=filename,
            workspace_id=workspace_id, task_id=task_id, label=label,
            fmt=fmt, features=features, credential_id=credential_id,
        )
    return upload_artifact_to_minio(
        content=content, fileobj=fileobj, filename=filename,
        content_type=content_type, workspace_id=workspace_id, task_id=task_id,
        label=label, fmt=fmt, features=features, credential_id=credential_id,
    )


def pasta_do_geosync() -> str | None:
    """Primeira pasta de `EXECUTOR_SYNC_DIRS`, ou None.

    So a primeira: o GeoSync sincroniza tudo contra UM workspace, e o app
    desktop ja restringe a configuracao a uma pasta.
    """
    pastas = [p.strip() for p in (os.getenv("EXECUTOR_SYNC_DIRS") or "").split(",") if p.strip()]
    return pastas[0] if pastas else None


def _publicar_com_retry(temporario: str, destino: str, tentativas: int = 4) -> None:
    """`os.replace` com retry curto, por causa do Windows.

    O scanner do GeoSync roda numa THREAD deste mesmo processo e abre os
    arquivos da pasta para calcular MD5. No Windows, `os.replace` sobre um
    arquivo que outro handle mantem aberto falha com PermissionError — o POSIX
    permite, o Windows nao. A janela e pequena, mas a colisao acontece
    exatamente no caso comum: um workflow recorrente reescrevendo o mesmo
    arquivo numa pasta varrida a cada 10 s.

    Sem isto, o sintoma seria o run falhando com "[WinError 5] Acesso negado",
    que nao diz nada a quem le. Quatro tentativas cobrem de sobra o tempo de um
    hash; se ainda assim falhar, a excecao sobe — o problema nao e transitorio.
    """
    import time

    for tentativa in range(tentativas):
        try:
            os.replace(temporario, destino)
            return
        except PermissionError:
            if tentativa == tentativas - 1:
                raise
            logger.debug(
                "Arquivo '%s' em uso (provavelmente o scanner do GeoSync); "
                "tentando de novo.", destino,
            )
            time.sleep(0.25 * (tentativa + 1))


def salvar_na_pasta_do_geosync(
    content: bytes, filename: str, workspace_id: str, overwrite: bool = False,
) -> str:
    """Grava um arquivo do Drive na pasta sincronizada. Retorna o caminho.

    O GeoSync o cataloga na varredura seguinte (`uploader.register` →
    `POST /drive/executor-register`), e a partir dai ele e um arquivo do Drive
    como qualquer outro catalogado: aparece com o selo, nao tem download, e e
    resolvido pelo manifesto de sync. Nada disso precisou ser escrito — ja
    existia para o modo catalogo, e reusar foi o que dispensou coluna nova,
    migration e endpoint.

    ⚠️ Escrita ATOMICA. O scanner varre a pasta a cada 10 s e reconhece o
    arquivo por tamanho e mtime; pego no meio da escrita, ele seria catalogado
    pela metade. Grava-se num nome iniciado por ponto — que o scanner ignora
    (`executor/sync/scanner.py`) — e faz-se `os.replace`, que e atomico no mesmo
    sistema de arquivos.
    """
    import uuid

    # ⚠️ SÓ em modo catálogo. Esta e a guarda que impede o oposto exato do que a
    # opcao promete: em `upload` ou `bidirectional`, o GeoSync varre a pasta a
    # cada 10 s e ENVIA os bytes de tudo que encontra (`_upload_dataset` so
    # chama `register` quando o modo e `catalog`). Gravar aqui numa maquina
    # assim publicaria no MinIO, em segundos, o arquivo que alguem acabou de
    # marcar para nao sair — e sem nenhum sinal de que isso aconteceu.
    if localidade_padrao() != EXECUTOR:
        raise ValueError(
            "Não é possível manter um arquivo do Drive apenas neste executor "
            "enquanto ele estiver sincronizando a pasta com o servidor: o "
            "GeoSync enviaria o arquivo na varredura seguinte.\n\n"
            "O que fazer: configure a máquina para reter os dados (app do "
            'executor: GeoSync > Localidade dos dados > "Manter apenas no '
            'executor"), ou troque o destino deste nó para Artefatos, que '
            "aceita conteúdo local em qualquer modo de sincronização."
        )

    pasta = pasta_do_geosync()
    if not pasta:
        raise ValueError(
            "Este executor não tem nenhuma pasta do GeoSync configurada, e é ela "
            "que recebe os arquivos do Drive mantidos localmente. Configure uma "
            "no app do executor (GeoSync → Pasta), ou envie este arquivo para o "
            "servidor."
        )
    if not os.path.isdir(pasta):
        raise ValueError(f"A pasta do GeoSync não existe mais neste computador: {pasta}")

    # O GeoSync sincroniza contra UM workspace. Se ele foi fixado no `.env` e nao
    # e o do run, gravar aqui publicaria o arquivo no Drive ERRADO — de outro
    # cliente, possivelmente. Vazio significa auto-deteccao, que so acontece
    # quando ha um workspace acessivel (executor/main.py) e portanto coincide.
    ws_sync = (os.getenv("EXECUTOR_WORKSPACE_ID") or "").strip()
    if ws_sync and ws_sync != workspace_id:
        raise ValueError(
            f"A pasta do GeoSync deste executor sincroniza com o workspace "
            f"'{ws_sync}', mas este workflow roda no workspace '{workspace_id}'. "
            "O arquivo iria para o Drive errado."
        )

    destino = os.path.join(pasta, filename)
    if os.path.exists(destino) and not overwrite:
        raise ValueError(
            f"Já existe um arquivo chamado '{filename}' na pasta do GeoSync "
            f"({pasta}). Ligue 'Sobrescrever se já existir' para substituí-lo, "
            "ou mude o nome do arquivo neste nó."
        )

    temporario = os.path.join(pasta, f".atlans-tmp-{uuid.uuid4().hex}")
    try:
        with open(temporario, "wb") as fh:
            fh.write(content)
        _publicar_com_retry(temporario, destino)
    except BaseException:
        # Um temporario orfao seria invisivel ao usuario (comeca com ponto) e ao
        # scanner, e ficaria ocupando disco para sempre.
        try:
            os.unlink(temporario)
        except OSError:
            pass
        raise

    logger.info("Arquivo do Drive gravado na pasta do GeoSync: %s", destino)
    return destino


def upload_artifact_to_minio(
    content: bytes | None = None,
    fileobj: BinaryIO | None = None,
    filename: str = "",
    content_type: str = "application/octet-stream",
    workspace_id: str = "",
    task_id: str = "",
    label: str = "",
    fmt: str = "",
    features: int | None = None,
    credential_id: str | None = None,
    create_drive_entry: bool = False,
    overwrite: bool = False,
) -> tuple[str, dict]:
    """
    Upload de artefato para o MinIO via pre-signed URL obtida do servidor.
    Se o upload falhar, salva localmente (disco do executor) como fallback.

    `overwrite` so vale com create_drive_entry=True — ver _upload_via_presigned_url.
    """
    if not filename:
        raise ValueError("filename é obrigatório para upload de artefato.")
    if not workspace_id or not task_id:
        raise ValueError("workspace_id e task_id são obrigatórios.")

    # Converter fileobj para bytes se necessário. Validado antes do try para que
    # erro de programacao (nenhum conteudo) nao caia no fallback local gravando
    # arquivo vazio.
    if content is None and fileobj is not None:
        pos = fileobj.tell()
        content = fileobj.read()
        fileobj.seek(pos)
    if content is None:
        raise ValueError("Deve fornecer content (bytes) ou fileobj para upload.")

    s3_key = f"artifacts/{workspace_id}/{task_id}/{filename}"
    local_fallback = False
    drive_file_id: str | None = None
    drive_reused = False

    try:
        s3_key, drive_file_id, drive_reused = _upload_via_presigned_url(
            content, filename, content_type, workspace_id, task_id,
            create_drive_entry=create_drive_entry,
            overwrite=overwrite,
        )
    except Exception as exc:
        logger.warning("Upload via pre-signed URL falhou — salvando localmente: %s (%s)", filename, exc)
        _save_local_fallback(content, workspace_id, task_id, filename)
        local_fallback = True

    artifact_meta = {
        "output_key": label or filename,
        "format": fmt,
        "features": features,
        "filename": filename,
        "credential_id": credential_id,
        "s3_key": s3_key,
        # Sempre 'minio' nesta rota, INCLUSIVE quando o upload falhou e o
        # conteudo ficou em disco: o fallback e um estado a corrigir, nao uma
        # politica de localidade. Tratar os dois como iguais faria uma queda de
        # rede virar "dado protegido" no registro do servidor.
        "content_location": "minio",
        "local_fallback": local_fallback,
        # Tamanho do conteudo, ja em maos. So e usado pelo servidor quando o
        # artefato acaba registrado como local (keepLocal OU fallback) — la nao
        # ha objeto para um HEAD medir. Sem isto, um artefato que caiu no
        # fallback aparecia no Drive/Artefatos com tamanho desconhecido.
        "size_bytes": len(content),
        "drive_file_id": drive_file_id,
        # True quando o servidor reaproveitou o WorkspaceFile existente. Sempre
        # False fora do fluxo do Drive e quando o upload caiu no fallback local.
        "drive_reused": drive_reused,
    }

    return s3_key, artifact_meta
