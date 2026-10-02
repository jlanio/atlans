# Credenciais

**Nunca escreva segredo na definição.** O nó recebe `credential_id` com o UUID
da credencial, e o servidor injeta o valor decifrado no momento do despacho —
`connectionString` para os nós de banco, `http_auth` para o `HttpRequest` e para
o `WFS` — removendo o id antes de executar.

```json
{ "id": "n1", "name": "DatabaseSpatialQuery", "type": "datasource",
  "properties": { "credential_id": "3f2a7c18-5b90-4c2e-9a44-1d6f8e2b7c05",
                  "query": "SELECT id, geom FROM lotes" } }
```

Os UUIDs disponíveis saem de `list_credentials` (que devolve id, tipo, dono e
validade — nunca o valor). `credential_id` que não é UUID é recusado antes de
qualquer consulta ao banco, com o código `invalid_credential_id`.

## WFS protegido

Um GeoServer com o módulo **authkey** pede a chave do usuário em cada
requisição. Ela mora em Credenciais, no tipo `geoserver_authkey` (a chave, o
nome do parâmetro — quase sempre `authkey` — e se vai na URL ou num
cabeçalho); usuário e senha (Basic) moram no tipo `wfs`. No nó `WFS`, passe o
id em `credential_id`, como em qualquer nó — nunca a chave na `url`:

```json
{ "id": "n1", "name": "WFS", "type": "datasource",
  "properties": { "url": "https://geo.exemplo.gov.br/geoserver/ows", "typeName": "ns:camada",
                  "credential_id": "3f2a7c18-5b90-4c2e-9a44-1d6f8e2b7c05" } }
```

O segredo só vai ao endereço do nó: se o GetCapabilities anunciar outro host
para buscar as feições, ou o servidor redirecionar para outro endereço, o nó
recusa em vez de levar a chave para lá — a saída é usar no nó o endereço final.
Credencial recusada pelo servidor (HTTP 401/403) para a execução na hora, sem
novas tentativas: repetir uma senha errada pode bloquear a conta. A chave e a
senha precisam ter ao menos 6 caracteres — abaixo disso não há como redigi-las
nas mensagens de erro e nos logs, e a tela de Credenciais recusa ao gravar.

## A borda recusa segredo

Escrever `connectionString`, `http_auth`, `token`, `password`, `secret`,
`api_key`, `authorization` ou `private_key` preenchidos — inclusive dentro de
`headers` — faz as tools de escrita recusarem a definição com o erro
`secret_in_definition`, listando os caminhos encontrados. A recusa vem **antes**
da validação e antes de gravar qualquer coisa. Expressões (`{{ ... }}`,
`$Alias.campo`) e o esquema de autenticação sozinho (`"Bearer"`) não contam
como segredo.

Isso vale também para o que você lê de volta: toda definition devolvida por
uma tool sai redigida, com essas chaves substituídas por `<REDACTED>`.

## Quem alcança o quê

A credencial precisa pertencer a quem dispara a execução, ou estar
compartilhada com o workspace do fluxo. Se não resolver, os nós de banco, o
`HttpRequest` e o `WFS` recusam antes de enviar.

Na validação há uma sutileza: credencial compartilhada com o workspace só
entra no escopo para quem tem papel `operator` ou superior — o mesmo papel
exigido para executar, porque a simulação do `DatabaseSpatialQuery` abre
conexão real com o banco. Abaixo disso vale só o escopo do próprio usuário, e
`report.hints` avisa.

Alcançável não é usável. A validação também acusa, em `report.errors`, a
credencial que a execução deixaria de fora em silêncio: de um tipo que o nó
não aceita (`credential_type_mismatch` — um `postgresql` num nó `WFS`, por
exemplo) ou vencida (`credential_expired`). Corrija antes de executar: o nó
recusaria por "credencial não resolvida".

O `SaveToS3` usa o `credential_id` para a credencial `s3` (chave, segredo,
região, bucket padrão e endpoint). Com ela escolhida e `registerArtifact`
ligado, a cópia registrada fica sem token de proteção, e `report.warnings`
avisa (`artifact_copy_unprotected`). Um `webhook_token` no mesmo campo protege
a cópia, e o upload usa a cadeia padrão do boto3 no executor.
