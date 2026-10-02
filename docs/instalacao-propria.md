# Instalação própria

Como subir o Atlans no seu servidor, do zero. No fim você tem o site (o web e
a API), o S3 (MinIO), a CA interna que identifica os executores (step-ca) e o
Traefik na frente de tudo. Os executores, que rodam os fluxos, ficam em outras
máquinas (ou na mesma) e se conectam por mTLS.

Para operar depois — atualizar, voltar de versão, backup, troubleshooting —,
ver [operations.md](operations.md).

## Antes de começar

- **Um host Linux** com Docker 24+, Docker Compose v2.17 ou mais novo (o
  compose usa `additional_contexts`), `openssl`, `make` e `git`.
- **Um PostgreSQL 15+ com PostGIS 3** e a extensão `uuid-ossp`, fora do
  compose: no mesmo host, em outro ou gerenciado. No mesmo host, a API (num
  container) não o alcança por `localhost`, que ali é o próprio container: use
  `host.docker.internal` no `DATABASE_URL` (o `api-prod` já aponta esse nome
  para o host), e faça o Postgres escutar na interface do Docker
  (`listen_addresses`) e aceitar as redes dele no `pg_hba.conf` (dentro de
  `172.16.0.0/12`, por padrão).
- **Um domínio, com três nomes** apontando para o IP do host. São as variáveis
  `PUBLIC_HOST`, `AGENTS_HOST` e `S3_HOST` do `.env`:

  | Variável | Exemplo | Para quê | CDN na frente |
  |---|---|---|---|
  | `PUBLIC_HOST` | `atlans.example.org` | o site, a API pública, o `/mcp` | pode |
  | `AGENTS_HOST` | `agents.atlans.example.org` | os executores (mTLS) | **nunca** |
  | `S3_HOST` | `s3.atlans.example.org` | downloads e uploads (URLs pré-assinadas) | pode |

  Um CDN termina o TLS e descarta o certificado do cliente: com o
  `AGENTS_HOST` atrás de um (na Cloudflare, *proxied*), nenhum executor
  conecta. Na Cloudflare, ele fica *DNS-only*.

  Use `agents.` + o `PUBLIC_HOST` para o `AGENTS_HOST`, como no exemplo. O
  compose anuncia aos executores o próprio `AGENTS_HOST` (`AGENTS_URL` =
  `https://<AGENTS_HOST>`, a menos que o `.env` defina outro), e o executor
  acha o site tirando o `agents.` do endereço. Com um `AGENTS_HOST` que não
  siga a convenção, defina `EXECUTOR_PUBLIC_SERVER_URL` em cada executor (o
  `install.sh` já o traz). O `make smoke` confere que o `install.sh` servido
  anuncia o `AGENTS_HOST`.
- **Um certificado TLS para o `PUBLIC_HOST` e o `S3_HOST`**: o de origem da
  Cloudflare, um do Let's Encrypt ou outro, com os dois nomes. Um curinga só
  cobre um nível: `*.example.org` vale para `atlans.example.org`, mas não para
  `s3.atlans.example.org`. O do `AGENTS_HOST` sai da CA interna; não precisa
  providenciar.
- **E-mail** (Resend ou qualquer SMTP): o cadastro manda o link de verificação
  por e-mail, e o login exige o e-mail verificado. Sem e-mail, ver
  `EXIGIR_EMAIL_VERIFICADO` no `.env.example` e o risco que ele descreve; e
  sem transporte a redefinição de senha não funciona (o link com o token não
  vai para o log).

Opcionais: o assistente, que monta fluxos por linguagem natural, precisa de
um modelo (`LLM_API_KEY`: o OpenRouter, um gateway ou um servidor local como
o Ollama); o satélite do mapa precisa de um provedor de tiles à sua escolha
(`MAPA_*`).

## 1. Preparar o host

```bash
git clone https://github.com/jlanio/atlans-studio.git atlans
cd atlans
make bootstrap
```

O `make bootstrap` cria o volume `step-ca-data` (a chave da CA), as pastas
`secrets/`, `traefik/atlans-ca/`, `certs/` e `backups/`, a senha do
provisioner da step-ca e o `.env`, copiado do `.env.example` com segredos
fortes no lugar dos vazios. Rodar de novo não apaga nada. O `.env` e a pasta
`secrets/` nunca vão para o git.

Ponha o certificado do site em `certs/cert.pem` (com a cadeia) e
`certs/key.pem`, ou aponte `SSL_CERT_DIR` para uma pasta com esses dois nomes.
Do certbot, copie o `fullchain.pem` como `cert.pem` e o `privkey.pem` como
`key.pem` (cópias, e não os links da pasta `live/`, que apontam para fora do
que o Traefik monta). O Traefik só relê o certificado ao reiniciar: a cada
renovação, `docker compose --profile prod restart traefik`.

## 2. Configurar o `.env`

O `.env.example` explica cada variável. Para produção, o mínimo:

| Variável | Valor |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://<usuário>:<senha>@<host>:5432/<banco>` |
| `PUBLIC_HOST`, `AGENTS_HOST`, `S3_HOST` | os três nomes |
| `FRONTEND_URL`, `AUTH_URL` | `https://<PUBLIC_HOST>` |
| `ALLOWED_ORIGINS` | `https://<PUBLIC_HOST>` |
| `MINIO_EXTERNAL_ENDPOINT` | `https://<S3_HOST>` (com `localhost`, nenhum download abre fora do Docker) |
| `MINIO_API_CORS_ALLOW_ORIGIN` | `https://<PUBLIC_HOST>` |
| `MINIO_ROOT_USER` | troque o padrão |
| `EXECUTOR_REPO_URL` | a URL deste repositório: o instalador do executor clona dele |
| `RESEND_API_KEY` ou `SMTP_*`, e `EMAIL_FROM` | o transporte de e-mail e o remetente |
| `AGENDAMENTO_FUSO_PADRAO` | o fuso da sua região (`America/Sao_Paulo`, `Europe/Lisbon`…), **antes** de criar agendamentos |
| `CODIGO_FONTE_URL` | a URL do repositório de onde vem o código que roda (o oficial, ou o seu fork) |
| `NOME_NA_TELA` | o nome que a tela mostra (barra lateral, entrada, aba); vazio = `Atlans`. Quem distribui uma versão modificada ou a oferece como serviço põe o nome dela ([TRADEMARKS.md](../TRADEMARKS.md)) |

Depende de onde a instalação roda:

- **Atrás da Cloudflare**: `BORDA_MIDDLEWARE=cloudflare-only` e as faixas
  dela em `BORDA_FAIXAS_CONFIAVEIS` (a lista está no `.env.example`). Sem CDN,
  os padrões (`borda-aberta`) já servem. O nome da borda escolhe também de
  onde vem o IP do cliente nos rate limits dos routers públicos
  (`rate-mcp-<borda>` e `rate-download-<borda>` no
  `traefik-dynamic/dynamic.yml`): sem CDN é o da conexão; atrás da Cloudflare
  é o que ela anexa ao `X-Forwarded-For`. Uma borda própria (outro CDN)
  precisa dos dois rate limits dela no `dynamic.yml`.

  A lista de faixas **não autentica a Cloudflare**: ela só diz que a conexão
  saiu de um IP dela — de qualquer conta, um Worker inclusive. Quem souber o
  IP do origin (o `AGENTS_HOST` é DNS-only e o publica) e falar com ele de
  dentro dessas faixas passa pela borda e escolhe o `X-Forwarded-For`. Para a
  borda ser real, ligue na Cloudflare os *Authenticated Origin Pulls* e exija
  o certificado de cliente dela nos hosts públicos: uma `tls.options` no
  `dynamic.yml` com `clientAuth.caFiles` apontando para o certificado da
  Cloudflare e `clientAuthType: RequireAndVerifyClientCert`, referenciada
  pelos routers do `PUBLIC_HOST` e do `S3_HOST` (nunca pelos do
  `AGENTS_HOST`, que têm o mTLS dos executores).
- **Num host com systemd**: `LOG_DRIVER=journald`, para o log da API e do web
  sobreviver à troca de container ([operations.md](operations.md#logs-que-sobrevivem-ao-deploy)).
- **Engine do Docker antigo**: `DOCKER_API_VERSION` (ex.: `1.41`), se o Traefik
  não conseguir falar com ele.

Os segredos (`APP_SECRET`, `FERNET_KEY`, `AUTH_SECRET`, `OTP_PEPPER`,
`EXECUTOR_SIGNING_KEY`, as senhas do Redis, do MinIO e da step-ca) o
bootstrap já gerou. Guarde uma cópia do `.env` fora do host: sem a
`FERNET_KEY`, as credenciais salvas no banco não abrem mais.

## 3. Subir

```bash
make up-prod                # constrói as imagens e sobe a stack; a step-ca cria a CA no 1º boot
docker compose exec api-prod alembic upgrade head        # cria o schema (a API já está de pé, esperando por ele)
make bootstrap-stepca       # fingerprint da CA no .env, prazo dos certificados e o cert do AGENTS_HOST
docker compose --profile prod up -d api-prod      # recria a API: só assim ela lê o .env novo
docker compose --profile prod restart traefik     # carrega os certificados

make backup-stepca          # o primeiro backup da CA, antes de qualquer outra coisa
make smoke                  # confere API, schema, Redis, MinIO, step-ca, web, o instalador dos executores e o AGENTS_HOST
make seed-admin             # cria o admin (pede e-mail e senha)
```

Um container lê o `.env` só quando é criado: depois de mudar o `.env`, é
`docker compose --profile prod up -d <serviço>`, e não `restart`.

O catálogo de fontes (`catalogo/geoservicos`, [fontes.md](fontes.md)) é
importado pela API na subida, assim que as tabelas existem: com o schema
criado antes de recriá-la, a recriação acima já o importa.

Se o `make up-prod` parar em «Pool overlaps with other one on this address
space», outra rede do Docker já usa a faixa da rede do Traefik: ver
`PROXY_NET_SUBNET` no `.env.example`.

As migrações nunca rodam sozinhas: o `alembic upgrade head` volta a cada
versão que mude o schema. O roteiro manual da CA, passo a passo, está em
[mtls-bootstrap.md](mtls-bootstrap.md).

Abra `https://<PUBLIC_HOST>` e entre com o admin.

## 4. Os executores

Todo fluxo roda num executor. Para matricular um:

1. No painel, em **Executores**, crie o executor e gere o código de matrícula
   (um OTP de uso único, que vale 24 horas).
2. Na máquina dele, siga [executor/README.md](../executor/README.md): o
   instalador, a matrícula (`python -m executor enroll`) e a execução. Com
   Docker, o [docker-compose.executor.yml](../docker-compose.executor.yml);
   no Windows, o app desktop ([desktop/](../desktop/)), que precisa ser
   construído apontando para a sua instalação (`ATLANS_DESKTOP_SERVIDOR` e
   `ATLANS_DESKTOP_UI_URL`, ver o `desktop-windows.yml`).

O executor fala com o `AGENTS_HOST`. Se ele não conecta, comece por
[operations.md, "Agent não conecta"](operations.md#agent-não-conecta).

## 5. Depois de subir

- **Backup.** O volume da CA (`make backup-stepca`, num cron diário), o banco
  (`pg_dump`) e o volume do MinIO. Perder a CA invalida todos os executores
  matriculados. Ver [operations.md](operations.md#backup-e-restore).
- **Atualizar.** `git pull`, `docker compose --profile prod up -d --build` e
  as migrações; antes, compare o `.env.example` novo com o seu `.env`. Ver
  [operations.md](operations.md#atualizar-a-instalação).
- **Segurança.** As correções chegam pelo repositório; aplicá-las é de cada
  instalação ([SECURITY.md](../SECURITY.md)).
- **Modificou o código?** A AGPL pede que quem usa a sua instalação pela rede
  possa obter o código-fonte da versão que roda nela (seção 13 da
  [LICENSE](../LICENSE)): publique o seu fork e aponte `CODIGO_FONTE_URL`, no
  `.env`, para ele. O link aparece na tela de entrada e no menu da conta.

## O que a instalação não traz

- **Cobrança.** O núcleo não cobra nada de ninguém: cada pessoa tem a cota
  diária do assistente (`ASSISTENTE_TETO_DE_TOKENS_POR_DIA`), e só. Recursos à
  parte entram como extensões (`app/extensoes/` e `web/extensoes/`, ver
  [architecture.md](architecture.md)).
- **Satélite.** O código não traz servidor de tiles de satélite: sem os
  `MAPA_*`, o mapa mostra as ruas do OpenStreetMap.
- **A marca.** O código é livre; o nome e os logotipos têm regras próprias
  ([TRADEMARKS.md](../TRADEMARKS.md)).
