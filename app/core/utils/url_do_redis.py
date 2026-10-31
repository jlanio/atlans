# app/core/utils/url_do_redis.py
"""The Redis URL with REDIS_PASSWORD percent-encoded in it.

docker-compose.yml builds `REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0` by
plain interpolation, and compose cannot encode: a password with `/`, `?`, `#`,
`[` or `%` broke the URL — after a `/` the rest of the password became the path
(and the database number), and redis-py's unquote turned a `%41` into an `A`.
`make bootstrap` generates hex, but nothing stopped a password chosen by hand.

Only that shape is touched: a URL whose userinfo is exactly `:<REDIS_PASSWORD>@`.
A URL with other credentials, already encoded, or without a password is
returned as it is — an explicit REDIS_URL keeps working.

Standard library only: app/core/config.py and app/core/rate_limiter.py import it.
"""
from urllib.parse import quote


def redis_url_with_encoded_password(url: str, senha: str | None) -> str:
    if not url or not senha:
        return url
    esquema, separador, resto = url.partition("://")
    cru = f":{senha}@"
    if not separador or not resto.startswith(cru):
        return url
    return f"{esquema}://:{quote(senha, safe='')}@{resto[len(cru):]}"
