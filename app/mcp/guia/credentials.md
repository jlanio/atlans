# Credentials

**Never write a secret into the definition.** The node receives `credential_id` with the
credential's UUID, and the server injects the decrypted value at dispatch time —
`connectionString` for the database nodes, `http_auth` for `HttpRequest` and for
`WFS` — removing the id before executing.

```json
{ "id": "n1", "name": "DatabaseSpatialQuery", "type": "datasource",
  "properties": { "credential_id": "3f2a7c18-5b90-4c2e-9a44-1d6f8e2b7c05",
                  "query": "SELECT id, geom FROM lotes" } }
```

The available UUIDs come from `list_credentials` (which returns id, type, owner and
expiry — never the value). A `credential_id` that is not a UUID is rejected before
any database query, with the code `invalid_credential_id`.

## Protected WFS

A GeoServer with the **authkey** module asks for the user's key on every
request. It lives in Credenciais (Credentials), under the `geoserver_authkey` type (the key, the
parameter name — almost always `authkey` — and whether it goes in the URL or in a
header); username and password (Basic) live under the `wfs` type. In the `WFS` node, pass the
id in `credential_id`, as in any node — never the key in the `url`:

```json
{ "id": "n1", "name": "WFS", "type": "datasource",
  "properties": { "url": "https://geo.exemplo.gov.br/geoserver/ows", "typeName": "ns:camada",
                  "credential_id": "3f2a7c18-5b90-4c2e-9a44-1d6f8e2b7c05" } }
```

The secret only goes to the node's address: if the GetCapabilities announces another host
for fetching the features, or the server redirects to another address, the node
refuses instead of taking the key there — the way out is to use the final address in the node.
A credential rejected by the server (HTTP 401/403) stops the run right away, with no
retries: repeating a wrong password can lock the account. The key and the
password must have at least 6 characters — below that there is no way to redact them
in error messages and logs, and the Credenciais screen rejects them on saving.

## The edge rejects secrets

Writing `connectionString`, `http_auth`, `token`, `password`, `secret`,
`api_key`, `authorization` or `private_key` filled in — including inside
`headers` — makes the write tools reject the definition with the error
`secret_in_definition`, listing the paths found. The rejection comes **before**
validation and before anything is saved. Expressions (`{{ ... }}`,
`$Alias.campo`) and the authentication scheme alone (`"Bearer"`) do not count
as a secret.

This also applies to what you read back: every definition returned by
a tool comes out redacted, with those keys replaced by `<REDACTED>`.

## Who can reach what

The credential must belong to whoever triggers the run, or be
shared with the workflow's workspace. If it does not resolve, the database nodes,
`HttpRequest` and `WFS` refuse before sending.

In validation there is a subtlety: a credential shared with the workspace only
enters the scope for those with the `operator` role or higher — the same role
required to execute, because the simulation of `DatabaseSpatialQuery` opens a
real connection to the database. Below that, only the user's own scope applies, and
`report.hints` warns about it.

Reachable is not usable. Validation also flags, in `report.errors`, the
credential that the run would silently leave out: one of a type the node
does not accept (`credential_type_mismatch` — a `postgresql` one on a `WFS` node, for
example) or an expired one (`credential_expired`). Fix it before executing: the node
would refuse with "credential not resolved".

`SaveToS3` uses `credential_id` for the `s3` credential (key, secret,
region, default bucket and endpoint). With it selected and `registerArtifact`
turned on, the registered copy is left without a protection token, and `report.warnings`
warns about it (`artifact_copy_unprotected`). A `webhook_token` in the same field protects
the copy, and the upload uses boto3's default chain on the executor.
