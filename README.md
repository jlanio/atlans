<p align="center">
  <strong>Atlans — plataforma de orquestração de workflows geoespaciais distribuídos</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/License-AGPL--3.0--only-blue.svg" alt="License: AGPL-3.0-only"/>
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python 3.12"/>
  <img src="https://img.shields.io/badge/FastAPI-0.135-009688?logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Next.js-16-000000?logo=next.js&logoColor=white" alt="Next.js 16"/>
  <img src="https://img.shields.io/badge/PostgreSQL-PostGIS-4169E1?logo=postgresql&logoColor=white" alt="PostGIS"/>
  <img src="https://img.shields.io/badge/Valkey-8-DC382D?logo=redis&logoColor=white" alt="Valkey 8 (compatível com Redis)"/>
  <img src="https://img.shields.io/badge/MinIO-S3-C72E49?logo=minio&logoColor=white" alt="MinIO"/>
  <img src="https://img.shields.io/badge/mTLS-step--ca-2496ED?logo=letsencrypt&logoColor=white" alt="mTLS"/>
</p>

---

## Sumário

- [Visão Geral](#visão-geral)
- [Arquitetura](#arquitetura)
- [Pré-requisitos](#pré-requisitos)
- [Início Rápido](#início-rápido)
- [Variáveis de Ambiente](#variáveis-de-ambiente)
- [Serviços Docker](#serviços-docker)
- [Sistema de Executores](#sistema-de-executores)
- [API — Referência de Endpoints](#api--referência-de-endpoints)
- [Autenticação](#autenticação)
- [Servidor MCP](#servidor-mcp-mcp)
- [Motor de Workflows](#motor-de-workflows)
- [Agendamento](#agendamento)
- [Eventos em Tempo Real](#eventos-em-tempo-real)
- [Multi-tenancy](#multi-tenancy)
- [Monitoramento](#monitoramento)
- [Makefile](#makefile)
- [CI/CD](#cicd--github-actions)
- [Licença](#licença)

---

## Visão Geral

O **Atlans** é uma plataforma para criar, executar, agendar e monitorar pipelines de análise geoespacial através de uma interface visual baseada em grafos DAG. Os workflows são compostos por nós conectáveis — leitura de dados, transformações espaciais, filtros, saídas — e executados por **executores distribuídos** que se conectam ao servidor via WebSocket sobre **mTLS**.

É **software livre** ([AGPL-3.0-only](LICENSE)): você pode instalá-lo no seu servidor, estudar e modificar o código e redistribuí-lo nos termos da licença. O roteiro de uma instalação própria está em [docs/self-hosting.md](docs/self-hosting.md).

### Principais Funcionalidades

| Funcionalidade | Descrição |
|---|---|
| **Editor Visual** | Interface drag-and-drop (XYFlow / React Flow) para montar pipelines DAG |
| **63 nós nativos** | trigger, datasource, spatial, action, control e output |
| **Executores distribuídos** | Execução delegada a executores externos via WebSocket + mTLS (sem Celery) |
| **Agendamento** | Cron, intervalo e RRule (RFC 5545), via `AsyncScheduler` embutido na API |
| **Multi-tenancy** | Workspaces isolados, com papéis viewer/editor/owner |
| **Portal de Mapas** | Publicação de camadas com tiles MVT e compartilhamento público |
| **Drive** | Gerenciamento de arquivos no MinIO com URLs pré-assinadas |
| **Observabilidade** | Métricas de execução, séries históricas e telemetria em tempo real |
| **Versionamento** | Histórico de versões dos workflows com restauração |
| **Credenciais seguras** | Criptografia Fernet (com rotação MultiFernet) para as credenciais de datasources |

---

## Arquitetura

```mermaid
graph TB
    subgraph Cliente
        Browser["🌐 Browser"]
    end

    subgraph Frontend
        Next["Next.js 16<br/>(React 19 + XYFlow)"]
    end

    subgraph API["FastAPI Server"]
        REST["REST API"]
        WS_LOG["WebSocket<br/>/ws/workflow/{run_id}"]
        WS_EXEC["WebSocket + mTLS<br/>/ws/executores/{id}"]
        SCHED["AsyncScheduler"]
    end

    subgraph Infra["Infraestrutura"]
        Redis["Redis (Valkey)<br/>pub/sub + cache"]
        MinIO["MinIO<br/>Object Storage (S3)"]
        StepCA["step-ca<br/>CA interna (mTLS)"]
    end

    PG["PostgreSQL + PostGIS<br/>(externo — fora do compose)"]

    subgraph Executores["Executores Externos"]
        EX1["🖥️ Executor default"]
        EX2["🖥️ Executor dedicated"]
    end

    Browser -->|HTTPS| Next
    Next -->|HTTP / WS| REST
    Next -->|WS| WS_LOG
    REST --> PG
    REST --> Redis
    REST --> MinIO
    REST --> StepCA
    SCHED -->|"dispara runs"| REST
    WS_EXEC <-->|"jobs assinados + eventos (mTLS)"| EX1
    WS_EXEC <-->|"jobs assinados + eventos (mTLS)"| EX2
    EX1 -->|"node_events"| Redis
    EX2 -->|"artefatos"| MinIO
    Redis -->|"pub/sub"| WS_LOG

    style API fill:#1a1a2e,color:#fff
    style Executores fill:#16213e,color:#fff
    style Infra fill:#533483,color:#fff
```

O executor embarca o motor (`flow/`) e roda os nós localmente; ele **não** recebe as credenciais em claro — os jobs são cifrados de ponta a ponta (X25519 + AES-256-GCM) e assinados (Ed25519). Veja [Sistema de Executores](#sistema-de-executores).

> **PostgreSQL é externo.** O `docker-compose.yml` **não** sobe um banco — você fornece um PostgreSQL com as extensões `postgis` e `uuid-ossp` e aponta `DATABASE_URL` para ele.

---

## Pré-requisitos

| Ferramenta | Versão mínima |
|---|---|
| Docker | 24+ |
| Docker Compose | v2.17+ (o compose usa `additional_contexts` para a imagem do web) |
| Git | 2.x |
| `make` e `openssl` | os do sistema (o `make bootstrap` gera os segredos com o openssl) |
| PostgreSQL + PostGIS | 15+ / PostGIS 3 (instância **externa**, com `postgis` e `uuid-ossp`) |

> Não é necessário Python ou Node.js localmente — a API e o web rodam via Docker. O PostgreSQL, porém, precisa existir por fora (LAN, host ou serviço gerenciado).

---

## Início Rápido

### Dev (sem TLS, sem mTLS — `localhost`)

```bash
git clone https://github.com/jlanio/atlans-studio.git atlans
cd atlans

make bootstrap          # cria volume step-ca-data, secrets/ e .env com secrets fortes
# Edite .env: aponte DATABASE_URL para o seu Postgres (com postgis e uuid-ossp).
# Postgres no mesmo host: use host.docker.internal, não localhost (que, dentro
# do container, é o próprio container).

make up-dev             # sobe api / web-dev / redis / minio (sem Postgres — é externo)

# Migrações NÃO rodam sozinhas — aplique o schema manualmente (na primeira vez,
# o mesmo comando cria o schema inteiro). A API já está de pé esperando por ele:
# o catálogo de fontes só é importado quando as tabelas existem.
docker compose exec api alembic upgrade head

make smoke              # valida API, Redis, MinIO healthy
docker compose exec api python -m app.cli create-admin   # cria o admin inicial (pede email/senha)
```

> O alvo `make seed-admin` aponta para o serviço `api-prod` (perfil de produção). Em dev, use `docker compose exec api python -m app.cli create-admin` como acima.

Serviços expostos:
- Frontend: http://localhost:3000
- API: http://localhost:8000 (docs em `/docs`)
- MinIO Console: http://localhost:9001

### Prod (Traefik + TLS + mTLS via step-ca interna)

Pré-requisitos no host:
- PostgreSQL + PostGIS acessível (defina em `DATABASE_URL`).
- DNS para os três hosts do `.env`:
  - `PUBLIC_HOST` (o site) — registro A para o IP do host; pode ficar atrás de um CDN
  - `AGENTS_HOST` (os executores) — registro A **direto**, nunca atrás de um CDN (na Cloudflare, *DNS-only*): obrigatório para o mTLS dos executores
  - `S3_HOST` (o S3) — registro A; pode ficar atrás de um CDN
- O certificado do site (para `PUBLIC_HOST` e `S3_HOST`) em `./certs/cert.pem` + `./certs/key.pem`, ou em `SSL_CERT_DIR`: o de origem da Cloudflare, um do Let's Encrypt ou outro.

```bash
git clone https://github.com/jlanio/atlans-studio.git atlans
cd atlans

make bootstrap                    # volume, secrets/, .env
# Edite .env: DATABASE_URL, os três hosts, FRONTEND_URL, ALLOWED_ORIGINS, e-mail etc.

make up-prod                      # sobe a stack; step-ca inicializa a CA interna no 1o boot
docker compose exec api-prod alembic upgrade head         # aplica o schema (manual; a API espera por ele)
make bootstrap-stepca             # fingerprint + intermediate + prazo dos certs + cert do AGENTS_HOST

docker compose --profile prod up -d api-prod      # recria a API: só assim ela lê o .env novo
docker compose --profile prod restart traefik     # carrega os certificados

make backup-stepca                # backup imediato da CA (faça antes que algo dê errado)
make smoke                        # valida API, Redis, MinIO, step-ca, web, instalador dos executores, DNS-only
make seed-admin                   # cria o admin inicial
```

O roteiro completo, passo a passo, está em [docs/self-hosting.md](docs/self-hosting.md); atualizar, voltar de versão, backup/restore e troubleshooting em [docs/operations.md](docs/operations.md); bootstrap do mTLS em [docs/mtls-bootstrap.md](docs/mtls-bootstrap.md).

---

## Variáveis de Ambiente

Copie `.env.example` para `.env` e ajuste os valores. As principais:

### Banco de Dados e Infraestrutura

| Variável | Descrição | Exemplo |
|---|---|---|
| `DATABASE_URL` | URL async do PostgreSQL **externo** (com postgis + uuid-ossp) | `postgresql+asyncpg://user:pass@host:5432/atlansdb` |
| `REDIS_PASSWORD` | Senha do Redis | Gere com `python -c "import secrets; print(secrets.token_hex(32))"` |
| `POOL_SIZE` | Tamanho do pool PostgreSQL, **por worker** (padrão do código: `8`) | `8` |
| `MAX_OVERFLOW` | Conexões extras permitidas, **por worker** (padrão: `5`) | `5` |

> **Teto de conexões.** Os dois valores acima são por processo, e a API de produção roda com 4 workers:
> o total é `workers × (POOL_SIZE + MAX_OVERFLOW)` = **52** com os padrões do código. Confira `SHOW max_connections`
> no seu Postgres e deixe folga para migrations, `psql` e demais clientes.

### Segurança e Autenticação

| Variável | Descrição | Exemplo |
|---|---|---|
| `APP_SECRET` | Segredo para assinar tokens JWT internos | Gere com `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `AUTH_SECRET` | Chave do Auth.js (NextAuth) | Gere com `openssl rand -base64 32` |
| `FERNET_KEY` | Chave Fernet para criptografia de credenciais (rotação via `FERNET_KEYS`) | `Fernet.generate_key()` |
| `EXECUTOR_SIGNING_KEY` | Semente da chave Ed25519 que assina os jobs e que os executores fixam na matrícula (**obrigatória**: vazia, nenhum executor matricula e nenhum job é despachado; o `make bootstrap` a gera) | `openssl rand -base64 32` |
| `EXECUTOR_POLICY_ROUTING` | Liga o roteamento por política de execução por workspace (`on`/`off`) | `off` |
| `ALLOWED_ORIGINS` | Origens CORS separadas por vírgula | `https://app.exemplo.com` |
| `STEPCA_ROOT_FINGERPRINT` / `STEPCA_PROVISIONER_PASSWORD` | Necessárias em prod para a API assinar OTTs no step-ca | — |

### MinIO (Object Storage)

| Variável | Descrição | Exemplo |
|---|---|---|
| `MINIO_ENDPOINT` | URL interna do MinIO (dentro do Docker) | `http://minio:9000` |
| `MINIO_EXTERNAL_ENDPOINT` | URL externa acessível pelo browser | `http://localhost:9000` |
| `MINIO_ROOT_USER` | Usuário root do MinIO (**obrigatório**, sem default) | — |
| `MINIO_ROOT_PASSWORD` | Senha root do MinIO (**obrigatório**, sem default) | — |
| `MINIO_BUCKET` | Bucket padrão para o Drive | `atlans-drive` |
| `MINIO_PRESIGN_EXPIRY` | Validade das URLs pré-assinadas (segundos); sem a variável o compose usa `3600`, o `.env.example` grava `900` | `900` |
| `WEBHOOK_RESPONSE_INLINE_LIMIT` | Body do ResponseNode acima de N bytes vai ao MinIO em vez de trafegar inline. É lida pelo **executor** (`flow/`), no `executor/.env`, não no `.env` do servidor | `1048576` |

### Frontend

| Variável | Descrição | Exemplo |
|---|---|---|
| `API_INTERNA` | URL interna da API (server-side Next.js) | `http://api:8000` |
| `API_PORT` | Porta da API visível pelo browser (o compose a entrega ao web como `NEXT_PUBLIC_API_PORT`) | `8000` |
| `NOME_NA_TELA` | O nome que a tela mostra (barra lateral, entrada, aba); vazio = `Atlans`. A forma com o domínio é marca do titular ([TRADEMARKS.md](TRADEMARKS.md)) | `Minha Instalação` |
| `AUTH_URL` | URL pública do app (redirect do Auth.js) | `https://app.exemplo.com` |

> Todas as variáveis estão documentadas em [`.env.example`](.env.example).

---

## Serviços Docker

O `docker-compose.yml` **não** inclui PostgreSQL — o banco é externo (veja Pré-requisitos).

### Desenvolvimento (`--profile dev`)

| Serviço | Imagem | Porta | Descrição |
|---|---|---|---|
| `redis` | `valkey/valkey:8-alpine` (`REDIS_IMAGE`) | — (interno) | Cache e pub/sub |
| `api` | `Dockerfile.api` | `8000` | FastAPI com hot-reload |
| `web-dev` | `web/Dockerfile.ui` | `3000` | Next.js em modo dev |
| `minio` | `minio/minio` | `9000` / `9001` | Object storage S3 + console |

### Produção (`--profile prod`)

| Serviço | Imagem | Porta | Descrição |
|---|---|---|---|
| `redis` | `valkey/valkey:8-alpine` (`REDIS_IMAGE`) | — (interno) | Cache e pub/sub |
| `api-prod` | `Dockerfile.api` | — (via Traefik) | FastAPI com 4 workers |
| `web-prod` | `web/Dockerfile.ui` | — (via Traefik) | Next.js build otimizado |
| `step-ca` | `smallstep/step-ca:0.27.0` | `9000` (interno) | CA interna que emite os certs mTLS dos executores |
| `traefik` | `traefik:v3.6` | `80` / `443` | Reverse proxy + TLS + terminação mTLS |
| `minio` | `minio/minio` | — (via Traefik) | Object storage S3 |

### Redes Docker

| Rede | Uso |
|---|---|
| `backend` | Comunicação interna entre API, Redis, MinIO e step-ca |
| `dev-net` | Comunicação entre `api` e `web-dev` (desenvolvimento) |
| `proxy-net` | Serviços expostos via Traefik (produção) |

---

## Sistema de Executores

O Atlans delega a execução dos workflows a **executores externos** conectados via WebSocket sobre **mTLS**. Não existe Celery — toda computação acontece nos executores.

### Tipos de Executor

| Tipo | Descrição |
|---|---|
| **`default`** | Faz parte do **pool padrão** da plataforma, acessível a qualquer usuário como fallback. Pode haver **mais de um** (gerenciados por `POST /executores/set-default` / `unset-default`). |
| **`dedicated`** | Atribuído explicitamente a usuários/workspaces. Um workspace pode fixar seu executor via política de roteamento (`EXECUTOR_POLICY_ROUTING`). |

A visibilidade é governada pela flag `is_default` (pool da plataforma) e pelas atribuições por usuário/workspace — não por um enum de três valores.

### Onboarding (OTP + mTLS)

O executor não usa API-key nem JWT. Ele se matricula com uma senha de uso único (OTP) e recebe um **certificado mTLS** emitido pela CA interna (step-ca):

```
┌──────────┐  POST /executores/            ┌──────────┐  POST /executores/{id}/enroll-otp  ┌──────────┐
│ Inexiste │───────────────────────────▶│ pending  │──────────────────────────────────▶│  (OTP)   │
└──────────┘  (cria registro)            └──────────┘  (admin gera OTP de 24h)          └────┬─────┘
                                                                                              │ POST /executores/enroll
                                                                                              │ (CSR → cert mTLS)
                                                                                         ┌────▼─────┐
                                                                                         │  active  │
                                                                                         └────┬─────┘
                                          DELETE /executores/{id}  (revoga)                   │  renova via
                                          ◀───────────────────────────────────────────────── ┘  POST /executores/renew-cert
```

O script de instalação (`GET /executores/install`) fixa o certificado da CA por SHA-256 (pinning) para bloquear troca de CA. Detalhes em [docs/mtls-bootstrap.md](docs/mtls-bootstrap.md).

### Protocolo WebSocket

**Conexão:** `WS /ws/executores/{executor_id}` — autenticada por **certificado mTLS** (validado pelo Traefik contra a CA interna). Não há token na URL.

| Direção | Mensagem | Descrição |
|---|---|---|
| `Servidor → Executor` | `job` | Job cifrado (X25519+AES-GCM) e assinado (Ed25519) |
| `Servidor → Executor` | `control` | Plano de controle: revogação, shutdown, config, purga de artefatos |
| `Servidor → Executor` | `cancel` | Cancela um job em execução |
| `Servidor → Executor` | `drive_event` | Eventos do Drive |
| `Servidor → Executor` | `error` | Recusa de uma mensagem do executor (`reason` e detalhe); o executor registra em WARNING |
| `Executor → Servidor` | `ack` | O job chegou e entrou na fila local |
| `Executor → Servidor` | `heartbeat` | Keepalive (a cada 30s) |
| `Executor → Servidor` | `capacity` | Capacidade atual (running/queued) — a cada 10s |
| `Executor → Servidor` | `node_event` | Progresso de execução por nó |
| `Executor → Servidor` | `job_result` | Resultado final do job |

### Back-pressure

Cada executor reporta sua capacidade via mensagens `capacity`, com base nas variáveis de ambiente do **host** do executor:

- `EXECUTOR_MAX_CONCURRENT` — execuções simultâneas (padrão: `4`).
- `EXECUTOR_MAX_QUEUE_SIZE` — fila local máxima (padrão: `50`).

O servidor consulta a capacidade reportada antes de despachar e devolve **503** quando `(queued + running) ≥ (max_concurrent + max_queue)`. Para alterar os limites efetivos, edite o `.env` do executor e reinicie o container — os campos armazenados no DB são apenas informativos para a UI quando o executor está offline.

---

## API — Referência de Endpoints

> Documentação interativa: `http://localhost:8000/docs` (Swagger UI).
> Rotas de recurso usam o **hash** do id (`{id_hash}`) e são definidas sem barra final (uma barra à direita gera redirect 307).

### Autenticação (`/auth`)

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/auth/register` | Cria uma conta (workspace padrão criado automaticamente) |
| `POST` | `/auth/login` | Autentica e retorna access + refresh tokens |
| `POST` | `/auth/refresh` | Renova o access token |
| `GET` | `/auth/me` | Dados do usuário autenticado |
| `POST` | `/auth/logout` | Encerra a sessão |
| `POST` | `/auth/verify-email` · `/auth/resend-verification` | Verificação de e-mail |
| `POST` | `/auth/forgot-password` · `/auth/reset-password` | Recuperação de senha |

### Workflows (`/workflows`)

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/workflows` | Lista workflows dos workspaces do usuário |
| `POST` | `/workflows` | Cria um workflow |
| `GET` · `PUT` · `DELETE` | `/workflows/{id_hash}` | Detalha / atualiza / remove |
| `POST` | `/workflows/{id_hash}/execute` | Dispara execução (inputs opcionais) |
| `GET` | `/workflows/{id_hash}/versions` | Histórico de versões |
| `POST` | `/workflows/{id_hash}/versions/{n}/restore` | Restaura uma versão |
| `POST` | `/workflows/{id_hash}/runs/{run_id}/retry` | Re-executa um run com falha |
| `POST` | `/workflows/{id_hash}/duplicate` | Duplica o workflow |
| `POST` | `/workflows/{id_hash}/move` · `/move/preview` | Move de workspace (com dry-run) |

### Executores (`/executores`)

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/executores/` | Cria um executor (registro `pending`) |
| `GET` | `/executores/` · `/my` | Lista todos / os acessíveis ao usuário |
| `GET` | `/executores/{id}/status` · `/{id}/workspaces` | Status / workspaces |
| `DELETE` | `/executores/{id}` | Revoga um executor |
| `POST` | `/executores/{id}/enroll-otp` | (Admin) gera OTP de matrícula (24h, uso único) |
| `POST` | `/executores/enroll` | Matrícula: CSR → certificado mTLS |
| `POST` | `/executores/renew-cert` | Renovação do certificado mTLS |
| `GET` | `/executores/ca-bundle` · `/server-public-key` | Root da CA interna / chave pública Ed25519 do servidor |
| `GET` | `/executores/install` · `/install/windows` | Script de onboarding / app desktop (Windows) |
| `POST` | `/executores/set-default` · `/unset-default` | (Admin) gerencia o pool padrão |

### Agendamentos (`/workflows/{id_hash}/schedules`)

| Método | Rota | Descrição |
|---|---|---|
| `PUT` | `/workflows/{id_hash}/schedules/{job_id}` | Atualiza (a Home usa para pausar/retomar) |

Os agendamentos nascem do nó `ScheduleTrigger` ao salvar o workflow (ou pelas tools de
gatilho do MCP); a lista da pessoa, entre todos os workspaces, vem de `GET /me/schedules`.

### Observabilidade (`/observability`)

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/observability/metrics` | Métricas gerais (com filtros por workspace/período) |
| `GET` | `/observability/metrics/workflows` · `/metrics/executores` | Métricas por workflow / por executor |
| `GET` | `/observability/runs-by-day` | Série histórica de runs por dia |
| `GET` | `/observability/runs` · `/runs/{run_id}` | Lista de runs / detalhe de um run |

### Credenciais (`/credentials`) · Portal (`/artifacts`) · Drive (`/drive`)

| Método | Rota | Descrição |
|---|---|---|
| `GET` · `POST` · `DELETE` | `/credentials/`, `/credentials/types`, `/credentials/test`, `/credentials/{id}` | CRUD + teste de conectividade |
| `GET` | `/artifacts/portal/{workflow_hash}` | Dados do portal público de um workflow |
| `GET` | `/artifacts/tiles/{workflow_hash}/{layer_key}/{z}/{x}/{y}.pbf` | Tiles MVT |
| `GET` · `POST` · `DELETE` | `/drive/`, `/drive/upload`, `/drive/{file_id}/download`, `/drive/{file_id}` | Listar / upload / download / remover |

**Teto de tamanho do Drive.** `PlatformFileSettings.max_size_mb` (padrão 200 MB, editável em
`PUT /drive/settings`) vale nas duas pontas do upload por URL pré-assinada: no pedido da URL,
contra o tamanho **declarado**, e na confirmação, contra o tamanho **real** medido no storage —
quem envia mais do que declarou recebe `413` no confirm. Quando o objeto acima do teto é um
upload de Drive ainda não aceito, a recusa também apaga o objeto e o registro pendente, porque
os bytes já estão no storage e a limpeza periódica remove só a linha. Artefatos de execução
(chave sob `artifacts/`) não passam por esse teto — nunca passaram —, e por isso continuam
sendo aceitos independentemente do tamanho.

### Workspaces (`/workspaces`)

| Método | Rota | Descrição |
|---|---|---|
| `GET` · `POST` | `/workspaces/` | Lista / cria |
| `PUT` · `DELETE` | `/workspaces/{id_hash}` | Atualiza / move para a lixeira (soft delete) |

O `DELETE` é soft: a linha permanece com `deleted_at`, os workflows são desativados e seus agendamentos param; os arquivos do Drive, porém, são removidos na hora. Restaurar/descartar em definitivo são ações de admin da plataforma (`/admin/workspaces/{trash,restore,purge}`) — o restore **não** reativa agendamentos.

### Execução, Webhook e Status

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/webhook/execute/{id_hash}` | Dispara execução via webhook externo (autenticado pela credencial do WebhookTrigger) — 202 assíncrono |
| `GET` | `/nodes/` | Lista os nós disponíveis e seus schemas |
| `GET` | `/ping` | Healthcheck (`{"status": "ok"}`) |

### WebSocket

| Endpoint | Autenticação | Descrição |
|---|---|---|
| `/ws/workflow/{run_id}` | JWT no 1º frame | Eventos de execução em tempo real |
| `/ws/executores/{executor_id}` | Certificado **mTLS** | Conexão persistente do executor |
| `/ws/telemetry` | `?token=<JWT>` | Métricas da VM (CPU, RAM, disco) |

### Servidor MCP (`/mcp`)

Rota exata `https://<PUBLIC_HOST>/mcp` (sem barra final), fora do Swagger e do JWT:
fala **MCP** sobre HTTP e autentica por **token pessoal** no header
`Authorization: Bearer atl_pat_…`, criado em Configurações → Tokens de acesso.
Expõe ferramentas de descoberta e leitura (workspaces, fluxos, catálogo de nós,
credenciais e Drive), de fontes de dados (buscar no catálogo de camadas WFS
pré-mapeadas, sondar e registrar uma nova), de construção (validar, criar,
atualizar, ativar e publicar no portal) e de execução (disparar com espera
opcional, acompanhar, ler o log, cancelar e reexecutar), mais resources do guia
de autoria e prompts prontos — tudo dentro do escopo do token, nunca além do que
a conta já alcançava.

URL, escopos, ferramentas, limites, erros e snippets de conexão por cliente:
[docs/mcp.md](docs/mcp.md). O catálogo de fontes (a semente em `catalogo/`, a
regra "catálogo primeiro" do assistente, a verificação por endpoint):
[docs/sources.md](docs/sources.md).

---

## Autenticação

O sistema usa **JWT** com dois tokens e proteção contra brute-force.

| Token | Duração | Uso |
|---|---|---|
| **Access Token** | 30 minutos (fixo) | Header `Authorization: Bearer <token>` |
| **Refresh Token** | 2 dias | Exclusivamente em `POST /auth/refresh` |

### Proteção contra Brute-force

- **Rate limit por IP**: 5 req/min no login (via slowapi).
- **Lockout por username**: 5 tentativas falhas → bloqueio de 15 minutos (via Redis).
- O frontend exibe o tempo restante de bloqueio e desabilita o formulário.

No frontend (NextAuth), o access token fica em `session.user.access_token`.

---

## Motor de Workflows

O executor processa grafos DAG em **ordenação topológica**, respeitando as dependências entre nós. A execução é restrita aos nós **alcançáveis a partir dos triggers** (e seus ancestrais); nós isolados e arestas órfãs são descartados antes do run.

### Categorias de Nós (63 no total)

| Categoria | Qtde | Exemplos (nomes reais do registro) |
|---|---|---|
| 🎯 **trigger** | 5 | `WebhookTrigger`, `ScheduleTrigger`, `FileTrigger`, `GeofenceTrigger`, `SubWorkflowInput` |
| 📥 **datasource** | 8 | `DatabaseQuery`, `DatabaseSpatialQuery`, `ReadGeoJSON`, `ReadShapefile`, `ReadGeoParquet`, `ReadCSVWithCoords`, `WFS`, `DataInput` |
| 🗺️ **spatial** | 21 | `Buffer`, `Clip`, `Dissolve`, `SpatialJoin`, `TransformCRS`, `ComputeArea`, `Simplify`, `ValidateGeometry`, `IntersectionNode`, `UnionNode`, `Heatmap`, … |
| ⚡ **action** | 9 | `HttpRequest`, `SetFields`, `AttributeFilter`, `AttributeJoin`, `OverlapPercentage`, `GeocodeNode`, `PythonScript`, `Sort`, `RemoveDuplicates` |
| 🔀 **control** | 7 | `Conditional`, `Switch`, `JinjaBranch`, `Merge`, `Loop`, `SubWorkflow`, `ChangeDetector` |
| 📤 **output** | 13 | `SaveGeoJSON`, `SaveToPostGIS`, `SaveToShapefile`, `SaveToGeoParquet`, `SaveToS3`, `SendEmail`, `SendWebhook`, `PublishMap`, `CartaImagem`, `Response`, `DataOutput`, `SubWorkflowOutput`, `SaveToPostgres` |

Para criar um nó, veja [docs/creating-nodes.md](docs/creating-nodes.md).

### Reaproveitamento de resultados (pinning)

Não há cache por variável de ambiente. O reaproveitamento é feito por **pinning**: a saída de um nó marcado com `cache: true` é serializada no MinIO (`pin-cache/{workspace}/…`) e reusada em execuções seguintes; o evento do nó vem com `cache_hit: true`. Saídas grandes ainda usam **spill-to-disk** (Parquet) durante o run para poupar memória.

---

## Agendamento

O **AsyncScheduler** substitui o Celery Beat — é um loop `asyncio` nativo dentro do processo da API.

```mermaid
graph TD
    SCHED["AsyncScheduler<br/>(loop a cada 30s)"] -->|"lê schedules ativos"| DB[(PostgreSQL)]
    SCHED -->|"verifica next_run_at"| CHECK{Hora de disparar?}
    CHECK -->|Sim| EXEC["WorkflowService<br/>.start_analysis()"]
    CHECK -->|Não| WAIT["Aguarda próximo ciclo"]
    EXEC -->|"seleciona executor"| AGENT["Executor via WebSocket"]
    EXEC -->|"atualiza last_run_at<br/>e next_run_at"| DB

    style SCHED fill:#ff6f00,color:#fff
    style EXEC fill:#1a237e,color:#fff
```

| Estratégia | Campo | Exemplo |
|---|---|---|
| **cron** | `cron_expression` | `0 8 * * 1-5` (seg–sex às 08:00) |
| **interval** | `interval` + `unit` | `30` + `minutes` |
| **rrule** | `rrule_expression` | `FREQ=WEEKLY;BYDAY=MO,WE,FR` (RFC 5545) |

Os campos `next_run_at` e `last_run_at` são persistidos na tabela `schedules` a cada disparo, para sobreviver a reinicializações.

---

## Eventos em Tempo Real

A plataforma usa **Redis pub/sub** + **WebSocket** para o streaming de eventos:

```mermaid
sequenceDiagram
    participant Executor
    participant API
    participant Redis
    participant Browser

    Executor->>API: node_event (via WS mTLS /ws/executores/{id})
    API->>Redis: PUBLISH workflow:{run_id}:events {event}
    Redis->>API: Subscriber recebe evento
    API->>Browser: WS /ws/workflow/{run_id} → {event}
    Note over Browser: Canvas atualiza o status<br/>dos nós em tempo real
```

Cada evento de nó carrega um `status` (`kind = lifecycle`); há também os kinds `stdout` e `debug`, e um evento de nó sentinela `__workflow_complete__` que sinaliza o fim do workflow.

| Campo `status` | Significado |
|---|---|
| `started` | Nó iniciou execução |
| `completed` | Nó finalizou com sucesso (com `cache_hit: true` quando veio do pin) |
| `failed` | Nó falhou (traz `error`) |

O endpoint `/ws/workflow/{run_id}` exige JWT no **primeiro frame**; o histórico (`workflow:{run_id}:history`) é reproduzido após a inscrição.

---

## Multi-tenancy

O Atlans isola dados por **workspaces**. Cada workspace agrupa workflows, credenciais, executores atribuídos e arquivos.

- Cada usuário pode pertencer a múltiplos workspaces.
- Papéis por membro: **viewer**, **editor**, **owner**.
- Um workspace padrão é criado automaticamente no registro do usuário.
- Executores `default` (pool da plataforma) são acessíveis por todos.

---

## Monitoramento

| Serviço | URL | Descrição |
|---|---|---|
| Swagger UI | `http://localhost:8000/docs` | Documentação interativa da API |
| MinIO Console | `http://localhost:9001` | Gerenciamento de objetos S3 |
| Telemetria WS | `/ws/telemetry?token=<JWT>` | CPU, memória e disco em tempo real |

A API expõe métricas agregadas de execução (gerais, por workflow, por executor e série temporal por dia) — ver a página `/observability` no web e [docs/specs/metrics-history.md](docs/specs/metrics-history.md).

---

## Makefile

| Comando | Descrição |
|---|---|
| `make bootstrap` | Cria volume `step-ca-data`, `secrets/` e `.env` com secrets fortes |
| `make bootstrap-stepca` | Captura fingerprint + intermediate, sobe o prazo dos certificados da step-ca e emite o cert do `AGENTS_HOST` |
| `make up-dev` / `make up-prod` | Sobe a stack em dev (hot-reload) / prod (Traefik + TLS) |
| `make down` | Para e remove os containers |
| `make logs` / `logs-dev` / `logs-prod` | Logs em tempo real (últimas 100 linhas) |
| `make restart` / `restart-prod` | Reinicia a stack de dev / prod |
| `make build-dev` / `build-prod` | Build dos containers |
| `make smoke` | Valida API, Redis, MinIO (e step-ca/DNS-only em prod) |
| `make seed-admin` | Cria o admin inicial (via `api-prod`; em dev use `docker compose exec api …`) |
| `make backup-stepca` | Backup da CA interna (mantém os 14 mais recentes) |

---

## CI/CD — GitHub Actions

| Workflow | Trigger | Saída |
|---|---|---|
| **CI** (`ci.yml`) | push / PR | secrets-scan, backend (`ruff` + `pytest`), backend e frontend sem extensões (o núcleo sozinho), auditoria de dependências (informativa), frontend (`lint` + `vitest` + `build`) e desktop (`typecheck` + `vitest` + lock) |
| **Desktop** (`desktop-windows.yml`) | tag `desktop/v*` | Instalador Windows (NSIS) em GitHub Release |
| **Executor Docker** (`executor-docker.yml`) | tag `executor/v*` | Imagem Docker do executor (`.tar.gz`) em GitHub Release |

**Deploy:** é de cada instalação — atualizar o código, subir as imagens e rodar as migrações ([docs/operations.md](docs/operations.md#atualizar-a-instalação)). As migrações não rodam sozinhas: aplique `alembic upgrade head` depois de uma versão que mude o schema.

---

## Licença

Copyright (C) 2026 Joselanio Ferreira de Morais.

O Atlans é software livre, sob a GNU Affero General Public License, versão 3 (AGPL-3.0-only): o texto está em [LICENSE](LICENSE). Você pode usar, estudar, modificar e redistribuir o código nesses termos; quem oferece uma versão modificada pela rede precisa oferecer o código-fonte dela a quem a usa (seção 13).

- Contribuições: [CONTRIBUTING.md](CONTRIBUTING.md) e o acordo de contribuidor, [CLA.md](CLA.md).
- O nome e os logotipos: [TRADEMARKS.md](TRADEMARKS.md).
- Os componentes de terceiros e as licenças deles: [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
- Vulnerabilidades: [SECURITY.md](SECURITY.md).

---

<p align="center">
  <sub>Feito com FastAPI, Next.js, PostGIS e muito GIS.</sub>
</p>
