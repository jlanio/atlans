# mTLS bootstrap — internal step-ca

One-time runbook to prepare the internal CA (`step-ca`) that signs the TLS
cert of the executors' host (`AGENTS_HOST`, in `.env`) and the mTLS certs of the
enrolled executors.

It applies to a clean production host, or when recreating the CA from scratch. **Do not
run it against a cluster with executors already in production** — it wipes the old CA and
invalidates every issued cert.

## Fast path (recommended)

Steps 1 to 8 of this document fit into these commands, with 1, 2 and 4 to 6
inside the scripts. On a clean host:

```bash
make bootstrap            # creates the volume, secrets/, .env
make up-prod              # brings up step-ca + the other services
docker compose exec api-prod alembic upgrade head  # the schema, before recreating the API
make bootstrap-stepca     # fingerprint, intermediate, cert lifetime and the AGENTS_HOST cert
docker compose --profile prod up -d api-prod      # recreates the API: only then does it read the new .env
docker compose --profile prod restart traefik     # loads the certificates
make backup-stepca        # immediate backup (do it before something goes wrong)
```

The manual steps below remain as a reference for debugging and
for [disaster recovery](#disaster-recovery), which has no script.

## Prerequisites

- Docker with the Compose v2 plugin (`docker compose`) already installed.
- Access to the host (`ssh`) and permission to create volumes.
- The `AGENTS_HOST` DNS pointing **directly** at the host's IP, with no CDN in
  front (on Cloudflare, *DNS-only*, never *proxied*). A CDN terminates TLS and
  discards the client certificate, and mTLS breaks.

## 1. External CA volume

The CA's private key lives in `step-ca-data`. The volume is declared as
`external: true` in [docker-compose.yml](../docker-compose.yml) so that it
survives an accidental `docker compose down -v`.

```bash
docker volume create step-ca-data
```

## 2. Provisioner password

`step-ca` needs a password to encrypt the private key of the
JWK provisioner. Generate a strong one and persist it:

```bash
mkdir -p secrets
openssl rand -base64 48 > secrets/stepca_password.txt
chmod 600 secrets/stepca_password.txt
sudo chown 1000:1000 secrets/stepca_password.txt   # the container's step user
```

step-ca runs as the `step` user (UID 1000), and compose mounts the file
with the host's owner and mode: with another owner and mode 600, it cannot read it and never
becomes healthy. `make bootstrap` does the `chown` when it runs as root, and warns
when it cannot.

The password must also go into `.env` as `STEPCA_PROVISIONER_PASSWORD` so that
the backend can decrypt the provisioner key when generating OTTs.

## 3. Initialize step-ca

The `smallstep/step-ca` image runs `init` automatically on its first start,
using the env vars already defined in compose (`DOCKER_STEPCA_INIT_*`).

```bash
docker compose --profile prod up -d step-ca
docker compose --profile prod logs -f step-ca
```

Wait for the line `serving HTTPS on :9000`.

On the first start, the image prints the CA's administrative password to the log (the
same as the provisioner's). Do not share that log.

## 4. Capture the root cert fingerprint

```bash
docker compose --profile prod exec step-ca \
    step certificate fingerprint /home/step/certs/root_ca.crt
```

Paste the value into `.env` as `STEPCA_ROOT_FINGERPRINT=...`.

`GET /executores/install` injects that value into the served script, as the default of
`ATLANS_CA_SHA256`. It is verified at two distinct moments:

1. **At installation**, by `install.sh` itself: the freshly downloaded root cert is
   checked against the fingerprint and the installation **aborts** if it does not match. This is
   the check that keeps the wrong CA from getting in.
2. **On every executor boot**, by `executor/_ca_bootstrap.py` — both when
   it downloads the bundle and when it reuses the `atlans-root.crt` already in the
   volume. For that, the installer writes `ATLANS_CA_SHA256` into `executor/.env`,
   where the long-running service reads it from.

   The check on the *reuse* path is what closes the hole of swapping the
   file in the volume and restarting: without it the pin applied only once, on the first
   boot that downloaded the bundle.

   On both sides the rule is **every certificate in the file must be
   among the pinned ones** — it is not enough for one of them to match. The whole file is
   concatenated to the public CAs and becomes the process's trust store, so a CA
   *appended* to the bundle would be as trusted as the legitimate root.

### CA rotation

`ATLANS_CA_SHA256` accepts **several comma-separated fingerprints**. That is what
makes rotation possible without turning pinning off: during the overlap the bundle
legitimately carries both the old and the new root, and both need to be on the list.

```
ATLANS_CA_SHA256=<fp_antigo>,<fp_novo>
```

Once every executor is on the new root, remove the old one from the list.

The ephemeral *enrollment* container is the exception, and for a concrete reason: it
receives `SSL_CERT_FILE` pointing to the cert already verified in step 1, and
`bootstrap_ca()` returns early when that variable exists, without ever reading the
pin. At that step the verification has already happened, in the shell.

Without the variable configured, the `ca-bundle` download keeps working, but
it is *trust on first use*: the installer warns that it verified nothing. Anyone who
managed to answer in the server's place would hand over their own CA. Configure it
in production.

The operator can override it by exporting `ATLANS_CA_SHA256` before running the
installer — useful when the fingerprint is carried over another channel.
It accepts plain hex (the `step certificate fingerprint` format) or with `:`
(the `openssl x509 -fingerprint` format), in upper or lower case.

## 5. Copy the intermediate to Traefik

Traefik validates the executor's client cert against the internal CA's
intermediate. Extract it and place it at the path mounted in compose (the
`traefik/atlans-ca` volume of the `traefik` service, in [docker-compose.yml](../docker-compose.yml)):

```bash
mkdir -p traefik/atlans-ca
docker compose --profile prod exec step-ca \
    cat /home/step/certs/intermediate_ca.crt \
    > traefik/atlans-ca/intermediate.crt
chmod 644 traefik/atlans-ca/intermediate.crt
```

## 6. Generate the TLS cert for the executors' host (`AGENTS_HOST`)

Traefik does **not** get a Let's Encrypt cert for `AGENTS_HOST`: the host
serves the handshake with a client certificate and stays outside the CDN. step-ca
issues its cert.

> This step is automated by `make bootstrap-stepca` (which issues the cert with
> `--provisioner-password-file`/`--force` and deletes the key from the volume after
> copying it). The commands below are the manual reference.

step-ca starts with a 24 h cap per certificate, and this one asks for a year (the
executors' enrollments ask for `EXECUTOR_CERT_TTL_DAYS`, 90 days by default).
Before issuing, raise the provisioner's cap and restart step-ca, which only reads the
new `ca.json` on restart:

```bash
docker compose --profile prod exec step-ca \
    step ca provisioner update atlans-app --x509-max-dur=8760h --x509-default-dur=2160h
docker compose --profile prod restart step-ca
```

Without this, the CA refuses: "requested duration of 8760h1m0s is more than the
authorized maximum certificate duration of 24h1m0s".

```bash
AGENTS_HOST=$(grep -E '^AGENTS_HOST=' .env | tail -1 | cut -d= -f2- | tr -d '"')

docker compose --profile prod exec step-ca \
    step ca certificate "$AGENTS_HOST" \
        /home/step/agents.crt \
        /home/step/agents.key \
        --provisioner atlans-app \
        --provisioner-password-file /run/secrets/stepca_password \
        --not-after 8760h \
        --force

docker compose --profile prod exec step-ca \
    cat /home/step/agents.crt > traefik/atlans-ca/agents.crt
docker compose --profile prod exec step-ca \
    cat /home/step/agents.key > traefik/atlans-ca/agents.key
chmod 600 traefik/atlans-ca/agents.key
chmod 644 traefik/atlans-ca/agents.crt

# Delete the key from the step-ca volume after copying (make bootstrap-stepca already does this):
docker compose --profile prod exec step-ca \
    sh -c 'rm -f /home/step/agents.crt /home/step/agents.key'
```

Renew in ~11 months (or automate with `step ca renew --daemon`).

## 7. Recreate the API and restart Traefik

```bash
docker compose --profile prod up -d api-prod      # the container only reads .env when it is created
docker compose --profile prod restart traefik     # Traefik only reads the certificates on startup
```

Smoke test:

```bash
curl --cacert traefik/atlans-ca/intermediate.crt \
     "https://$AGENTS_HOST/executores/ca-bundle"
```

It should return the PEM of the internal CA's root.

## 8. Periodic volume backup

Losing the `step-ca-data` volume is catastrophic — every enrolled
executor needs a new OTP + enroll.

> Prefer `make backup-stepca`: it writes to `backups/step-ca-YYYY-MM-DD-HHMM.tar.gz`
> and keeps the 14 most recent backups. The block below is the manual equivalent
> (name without the time, no automatic retention) — run it via a daily cron:

```bash
docker run --rm \
    -v step-ca-data:/data \
    -v "$(pwd)/backups:/backup" \
    alpine tar czf /backup/step-ca-$(date +%F).tar.gz -C /data .
```

Keep the tarballs off the host (S3 with KMS, etc.).

## 9. Onboarding a new executor

After the bootstrap, any admin can:

1. Create the executor in the UI (generates an OTP, single-use, TTL 24h).
2. Share the `curl ... | bash` command with the operator over an ephemeral
   channel.
3. The executor runs `install.sh`, does `enroll` → step-ca issues the mTLS cert →
   the executor persists it in `EXECUTOR_CERT_DIR/cert.pem`.

Automatic renewal (`executor/renewal.py`) happens on its own close to
expiry, with an atomic swap of the files.

## Disaster recovery

If `step-ca-data` is lost:

1. Restore the most recent backup, with step-ca and the API down (both
   mount the volume):
   ```bash
   docker compose --profile prod rm -sf step-ca api-prod
   docker run --rm -v step-ca-data:/data -v "$(pwd)/backups:/backup" \
       alpine tar xzf /backup/step-ca-YYYY-MM-DD.tar.gz -C /data
   ```
2. Bring up `step-ca` and `api-prod`, and restart `traefik`.
3. Confirm the fingerprint did not change (same backup → same CA). If it
   did change, update `.env` (`STEPCA_ROOT_FINGERPRINT`) and
   tell every executor to re-enroll (the admin generates new OTPs).
