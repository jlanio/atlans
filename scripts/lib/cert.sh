# shellcheck shell=bash
# scripts/lib/cert.sh
# The site certificate (cert.pem and key.pem in SSL_CERT_DIR, ./certs by
# default), as bootstrap.sh and up.sh check it in production.
#
# traefik-dynamic/dynamic.yml makes it Traefik's DEFAULT certificate. Without
# the files, the default store fails to load and Traefik has no certificate at
# all for PUBLIC_HOST and S3_HOST: the TLS handshake is refused and the browser
# shows nothing, not even a certificate warning. Until the real one is in
# place, a provisional self-signed certificate for both names keeps the site
# reachable, with the browser's warning.
#
# Sourced, not run. Needs openssl 1.1.1 or newer (-addext).

# cert_site_missing <dir>: true when cert.pem or key.pem is missing or empty.
cert_site_missing() {
    [ ! -s "$1/cert.pem" ] || [ ! -s "$1/key.pem" ]
}

# cert_site_absent <dir>: true when neither file exists. Only then is a
# provisional certificate written: a key.pem alone may be the one of a CSR
# waiting for the real certificate, and must not be overwritten.
cert_site_absent() {
    [ ! -e "$1/cert.pem" ] && [ ! -e "$1/key.pem" ]
}

# cert_site_self_signed <dir>: true when cert.pem was issued by itself — the
# provisional one, or any other self-signed certificate.
cert_site_self_signed() {
    local subject issuer
    subject="$(openssl x509 -in "$1/cert.pem" -noout -subject 2>/dev/null | sed 's/^subject= *//')"
    issuer="$(openssl x509 -in "$1/cert.pem" -noout -issuer 2>/dev/null | sed 's/^issuer= *//')"
    [ -n "$subject" ] && [ "$subject" = "$issuer" ]
}

# cert_site_provisional <dir> <host> [host...]: when cert_site_absent, writes
# a self-signed certificate valid for 90 days for the hosts (the first one is
# the CN), with the key born 600. Fails without leaving a file behind.
cert_site_provisional() {
    local dir="$1" san="" host
    shift
    cert_site_absent "$dir" || return 1
    for host in "$@"; do
        if [ -n "$host" ]; then
            san="${san:+$san,}DNS:$host"
        fi
    done
    [ -n "$san" ] || return 1
    mkdir -p "$dir"
    if ! ( umask 077 && openssl req -x509 -newkey rsa:2048 -nodes -days 90 \
            -keyout "$dir/key.pem" -out "$dir/cert.pem" \
            -subj "/CN=$1" -addext "subjectAltName=$san" >/dev/null 2>&1 ); then
        rm -f "$dir/key.pem" "$dir/cert.pem"
        return 1
    fi
}
