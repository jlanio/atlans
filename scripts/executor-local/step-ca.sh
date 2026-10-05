#!/bin/sh
# scripts/executor-local/step-ca.sh
#
# Command of the dev step-ca (docker-compose.yml, profile executor-local). The
# image's entrypoint runs first and creates the CA on the first boot; then this
# does, before the CA starts, what scripts/bootstrap-stepca.sh does by hand in
# production:
#
#   - raises the provisioner's certificate lifetime (step-ca is born with 24 h,
#     and each enrollment asks for EXECUTOR_CERT_TTL_DAYS, 90 days by default).
#     Done here, before the server starts, there is no restart to make.
#   - issues the TLS certificate of the dev executors host (EXECUTOR_LOCAL_HOST)
#     into /home/step/dev/, which traefik-dev reads from the same volume. Signed
#     offline with the intermediate, so the CA does not need to be running yet.
#     Issued again when it is missing, when the host changed, or 30 days before
#     it expires.
#
# Idempotent: it runs on every start of the container.
set -eu

PROV="${STEPCA_PROVISIONER_NAME:-atlans-app}"
HOST="${EXECUTOR_LOCAL_HOST:-agents.localhost}"
DEV=/home/step/dev

step ca provisioner update "$PROV" \
    --x509-max-dur=8760h --x509-default-dur=2160h \
    --ca-config "$CONFIGPATH" >/dev/null

mkdir -p "$DEV"
if [ ! -s "$DEV/agents.crt" ] \
    || [ "$(cat "$DEV/host" 2>/dev/null || true)" != "$HOST" ] \
    || step certificate needs-renewal "$DEV/agents.crt" --expires-in 720h >/dev/null 2>&1; then
    # --bundle: the leaf and the intermediate, the chain Traefik has to present.
    step certificate create "$HOST" "$DEV/agents.crt" "$DEV/agents.key" \
        --profile leaf \
        --ca /home/step/certs/intermediate_ca.crt \
        --ca-key /home/step/secrets/intermediate_ca_key \
        --ca-password-file "$PWDPATH" \
        --not-after 8760h --no-password --insecure --bundle --force >/dev/null
    printf '%s' "$HOST" > "$DEV/host"
    echo "[step-ca-dev] certificado de ${HOST} emitido em ${DEV}."
fi

exec /usr/local/bin/step-ca --password-file "$PWDPATH" "$CONFIGPATH"
