# shellcheck shell=bash
# scripts/lib/ca.sh
# The step-ca password, as bootstrap.sh and up.sh check it.
#
# The internal CA lives in the external volume step-ca-data. It is created on
# the first start with the password of secrets/stepca_password.txt, keeps its
# own copy (secrets/password, in the volume) and encrypts the key of the JWK
# provisioner with it. The API opens that key with STEPCA_PROVISIONER_PASSWORD
# from .env to sign the executors' certificates.
#
# The volume is external on purpose (it survives `down -v`), so it outlives
# a .env or a secrets/ generated again: the CA keeps the old password and every
# enrollment fails with "Falha ao decifrar chave do provisioner JWK" (503).
#
# Sourced, not run. Needs docker; reads the volume through a throwaway
# container of the step-ca image, read-only.

STEPCA_IMAGE="${STEPCA_IMAGE:-smallstep/step-ca:0.27.0}"
STEPCA_VOLUME="step-ca-data"

# Runs a shell snippet in a throwaway step-ca container with the volume
# mounted read-only at /home/step (as root: the secret files are mode 600).
_ca_sh() {  # <snippet> [extra docker run args...]
    local snippet="$1"
    shift
    docker run --rm -u 0 --entrypoint sh "$@" -v "$STEPCA_VOLUME:/home/step:ro" "$STEPCA_IMAGE" -c "$snippet"
}

# Tests the password file at __PASS__ against the provisioner key.
_CA_TEST='[ -f /home/step/config/ca.json ] || { echo none; exit 0; }
[ -f "__PASS__" ] || { echo none; exit 0; }
k=$(sed -n "s/.*\"encryptedKey\": *\"\([^\"]*\)\".*/\1/p" /home/step/config/ca.json | head -1)
[ -n "$k" ] || { echo unknown; exit 0; }
echo "$k" | step crypto jwe decrypt --password-file "__PASS__" >/dev/null 2>&1 && echo ok || echo wrong'

_ca_has_image() {
    docker image inspect "$STEPCA_IMAGE" >/dev/null 2>&1 || docker pull -q "$STEPCA_IMAGE" >/dev/null 2>&1
}

# ca_state <password file>: whether the CA in the volume opens with it.
#   none     no volume, or a volume without a CA yet (created on the first start)
#   ok       the CA opens with this password
#   wrong    it does not
#   unknown  could not test (no image and no network, docker error)
ca_state() {
    local file out abs
    file="$1"
    docker volume inspect "$STEPCA_VOLUME" >/dev/null 2>&1 || { echo none; return; }
    _ca_has_image || { echo unknown; return; }
    abs="$(cd "$(dirname "$file")" && pwd)/$(basename "$file")"
    out="$(_ca_sh "${_CA_TEST//__PASS__//tmp/senha}" -v "$abs:/tmp/senha:ro" 2>/dev/null)" || out="unknown"
    case "$out" in none|ok|wrong) echo "$out" ;; *) echo unknown ;; esac
}

# ca_own_password_opens: whether the CA's own copy of its password (in the
# volume) opens the provisioner key. When it does, that is the password to use.
ca_own_password_opens() {
    [ "$(_ca_sh "${_CA_TEST//__PASS__//home/step/secrets/password}" 2>/dev/null)" = "ok" ]
}

# ca_copy_own_password <destination file>: writes the CA's password there,
# born mode 600. The value never goes through the terminal or a variable.
ca_copy_own_password() {
    ( umask 077 && _ca_sh 'cat /home/step/secrets/password' > "$1" )
}

# ca_password_file_fix_cmd <password file>: the command that leaves it readable
# by step-ca (UID 1000, the owner) and by the user who runs these scripts (the
# group, mode 640), who checks it against the CA.
ca_password_file_fix_cmd() {
    printf 'sudo chown 1000:%s %s && sudo chmod 640 %s' "$(id -g)" "$1" "$1"
}
