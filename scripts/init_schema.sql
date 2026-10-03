-- =============================================================================
-- Atlas Studio — Full schema, a mirror of the SQLAlchemy models
-- Base zero (F3 of the simplification): this file is the BODY of the only
-- alembic revision (9ed006ca1660 — alembic/versions/20260924_0001_base_zero.py),
-- which reads and executes it. Editing here is editing the migration; the
-- convergence tests (tests/unit/test_init_schema_bootstrap.py) pin the text to
-- the models.
-- Direct use: DROP ALL + CREATE ALL for a clean database
--
-- The tables of an extension (app/extensoes) are NOT here: they live in its
-- `schema.sql`, which base zero runs after this one. On a manual reset of an
-- installation with extensions, also run each of them, after this one:
--
--   psql -U atlans -d atlansdb -f app/extensoes/<nome>/schema.sql
--
-- IMPORTANT: this script creates the tables owned by the user that runs
-- it. If you run it as superuser (e.g. psql -U postgres) and the app
-- connects with a different user (e.g. atlans), uncomment the GRANTs section
-- at the end of the file OR run the script directly as the app user:
--
--   psql -U atlans -d atlansdb -f scripts/init_schema.sql
-- =============================================================================

-- Required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS postgis;

-- =============================================================================
-- DROP everything (reverse dependency order)
-- =============================================================================
DROP TABLE IF EXISTS uso_do_assistente CASCADE;
DROP TABLE IF EXISTS fontes_de_dados CASCADE;
DROP TABLE IF EXISTS mensagens CASCADE;
DROP TABLE IF EXISTS conversas CASCADE;
DROP TABLE IF EXISTS portal_features CASCADE;
DROP TABLE IF EXISTS portal_layers CASCADE;
DROP TABLE IF EXISTS node_run_metrics CASCADE;
DROP TABLE IF EXISTS workflow_run_metrics CASCADE;
-- audit_events was added to the CREATE but left out of here: resetting a
-- database that already had the table aborted at `CREATE TABLE audit_events`
-- (with ON_ERROR_STOP, after EVERYTHING had already been dropped) or, without
-- ON_ERROR_STOP, carried on and stamped the head with the PREVIOUS dataset's
-- audit rows intact.
DROP TABLE IF EXISTS audit_events CASCADE;
DROP TABLE IF EXISTS usage_daily CASCADE;
DROP TABLE IF EXISTS user_executor_assignments CASCADE;
DROP TABLE IF EXISTS workflow_versions CASCADE;
DROP TABLE IF EXISTS workflow_runs CASCADE;
DROP TABLE IF EXISTS schedules CASCADE;
DROP TABLE IF EXISTS workflows CASCADE;
DROP TABLE IF EXISTS workflow_groups CASCADE;
DROP TABLE IF EXISTS workspace_executors CASCADE;
DROP TABLE IF EXISTS workspace_members CASCADE;
DROP TABLE IF EXISTS workspace_files CASCADE;
DROP TABLE IF EXISTS artifacts CASCADE;
DROP TABLE IF EXISTS executors CASCADE;
DROP TABLE IF EXISTS executor_enrollment_otp CASCADE;
DROP TABLE IF EXISTS credentials CASCADE;
DROP TABLE IF EXISTS api_tokens CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS workspaces CASCADE;
DROP TABLE IF EXISTS node_templates CASCADE;
DROP TABLE IF EXISTS system_config CASCADE;
DROP TABLE IF EXISTS platform_file_settings CASCADE;
DROP TABLE IF EXISTS allowed_file_extensions CASCADE;
DROP TABLE IF EXISTS alembic_version CASCADE;

-- =============================================================================
-- 1. Independent tables (no FK)
-- =============================================================================

-- users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    id_hash VARCHAR(36) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    email_verified BOOLEAN NOT NULL DEFAULT false,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    agent_quota INTEGER NOT NULL DEFAULT 0,
    workspace_id VARCHAR(36),
    suspended_at TIMESTAMP,
    deleted_at TIMESTAMP,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX ix_users_id_hash ON users (id_hash);
CREATE INDEX ix_users_username ON users (username);
CREATE INDEX ix_users_email ON users (email);
CREATE INDEX ix_users_status ON users (status);
CREATE INDEX ix_users_workspace_id ON users (workspace_id);

-- workspaces
CREATE TABLE workspaces (
    id SERIAL PRIMARY KEY,
    id_hash VARCHAR(36) UNIQUE NOT NULL,
    name VARCHAR NOT NULL,
    description VARCHAR,
    owner_id VARCHAR(36),
    target_executor_id VARCHAR(36),
    -- Execution policy (docs/specs/executor-isolation-routing.md):
    -- terminal when the tier chain runs out, and the platform admin's floor.
    fallback_terminal VARCHAR(8) NOT NULL DEFAULT 'fail',
    isolation_floor VARCHAR(8) NOT NULL DEFAULT 'none',
    is_default BOOLEAN NOT NULL DEFAULT false,
    notification_url_allowlist JSON,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now(),
    deleted_at TIMESTAMP
);
CREATE INDEX ix_workspaces_id_hash ON workspaces (id_hash);
CREATE INDEX ix_workspaces_owner_id ON workspaces (owner_id);
CREATE INDEX ix_workspaces_target_executor_id ON workspaces (target_executor_id);

-- system_config
CREATE TABLE system_config (
    key VARCHAR PRIMARY KEY,
    value JSON,
    updated_at TIMESTAMP DEFAULT now() NOT NULL
);

-- platform_file_settings
CREATE TABLE platform_file_settings (
    id INTEGER PRIMARY KEY DEFAULT 1,
    max_size_mb INTEGER NOT NULL DEFAULT 200,
    updated_at TIMESTAMP
);

-- allowed_file_extensions
CREATE TABLE allowed_file_extensions (
    id SERIAL PRIMARY KEY,
    extension VARCHAR(20) UNIQUE NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX ix_allowed_file_extensions_extension ON allowed_file_extensions (extension);

-- credentials
CREATE TABLE credentials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_hash VARCHAR(36) UNIQUE NOT NULL,
    name VARCHAR NOT NULL,
    type VARCHAR NOT NULL,
    data JSONB NOT NULL,
    owner_id VARCHAR(36),
    workspace_id VARCHAR(36),
    description VARCHAR,
    tags JSONB,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX ix_credentials_id_hash ON credentials (id_hash);
CREATE INDEX ix_credentials_owner_id ON credentials (owner_id);
CREATE INDEX ix_credentials_workspace_id ON credentials (workspace_id);

-- =============================================================================
-- 2. Tables with simple FKs
-- =============================================================================

-- executors
CREATE TABLE executors (
    id SERIAL PRIMARY KEY,
    id_hash VARCHAR(36) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(255),
    executor_type VARCHAR(20) NOT NULL DEFAULT 'dedicated',
    is_default BOOLEAN NOT NULL DEFAULT false,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    public_key TEXT,
    -- Cert mTLS emitido pela CA interna (step-ca). Nulos enquanto pending.
    cert_serial VARCHAR(64) UNIQUE,
    cert_fingerprint_sha256 VARCHAR(64),
    cert_issued_at TIMESTAMP,
    cert_expires_at TIMESTAMP,
    capabilities JSONB NOT NULL DEFAULT '[]',
    max_concurrent_jobs INTEGER NOT NULL DEFAULT 4,
    max_queue_size INTEGER NOT NULL DEFAULT 50,
    executor_version VARCHAR(20),
    system_info JSONB,
    last_seen_at TIMESTAMP,
    created_by VARCHAR(36),
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now(),
    deleted_at TIMESTAMP
);
CREATE INDEX ix_executors_id_hash ON executors (id_hash);
CREATE INDEX ix_executors_created_by ON executors (created_by);
CREATE INDEX ix_executors_deleted_at ON executors (deleted_at);
-- Default executor pool: multiple is_default=true allowed (no unique index)

-- executor_enrollment_otp: OTPs single-use para bootstrap via mTLS.
CREATE TABLE executor_enrollment_otp (
    id_hash VARCHAR(36) PRIMARY KEY,
    executor_id VARCHAR(36) NOT NULL REFERENCES executors(id_hash) ON DELETE CASCADE,
    otp_hash VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    consumed_at TIMESTAMP,
    consumed_from_ip VARCHAR(45),
    created_by VARCHAR(36) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
-- The table is `executor_enrollment_otp` since 20260716_0001; the old name here
-- made the whole script blow up with "relation agent_enrollment_otp does not
-- exist" right in section 2.
CREATE INDEX ix_otp_unused ON executor_enrollment_otp (otp_hash) WHERE consumed_at IS NULL;

-- api_tokens: personal access tokens (PAT) — the identity of agents.
-- Only the SHA-256 of the secret is stored here (token_hash, unique = lookup
-- key); revoking means setting revoked_at, never deleting. NULL in
-- workspace_ids = all.
CREATE TABLE api_tokens (
    id SERIAL PRIMARY KEY,
    id_hash VARCHAR(36) NOT NULL UNIQUE,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id_hash) ON DELETE CASCADE,
    name VARCHAR(80) NOT NULL,
    token_prefix VARCHAR(16) NOT NULL,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    scopes JSON NOT NULL,
    workspace_ids JSON,
    expires_at TIMESTAMP NOT NULL,
    last_used_at TIMESTAMP,
    revoked_at TIMESTAMP,
    revoked_reason VARCHAR(32),
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX ix_api_tokens_user_id ON api_tokens (user_id);

-- conversas + mensagens (Home assistant; persisted conversation, several per
-- person, no expiry). mensagens.blocos stores the content VERBATIM.
CREATE TABLE conversas (
    id SERIAL PRIMARY KEY,
    id_hash VARCHAR(36) NOT NULL UNIQUE,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id_hash) ON DELETE CASCADE,
    workspace_id VARCHAR(36),
    workflow_id VARCHAR(36),
    titulo VARCHAR(120),
    origem VARCHAR(16) NOT NULL DEFAULT 'home',
    tokens_total INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now(),
    deleted_at TIMESTAMP
);
CREATE INDEX ix_conversas_user_id ON conversas (user_id);
CREATE INDEX ix_conversas_user_updated ON conversas (user_id, updated_at);

CREATE TABLE mensagens (
    id SERIAL PRIMARY KEY,
    conversa_id VARCHAR(36) NOT NULL REFERENCES conversas(id_hash) ON DELETE CASCADE,
    ordem INTEGER NOT NULL,
    papel VARCHAR(16) NOT NULL,
    blocos JSON NOT NULL,
    uso JSON,
    meta JSON,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT uq_mensagens_conversa_ordem UNIQUE (conversa_id, ordem)
);
CREATE INDEX ix_mensagens_conversa_id ON mensagens (conversa_id);

-- fontes_de_dados (catalog of pre-mapped sources: the assistant checks it before
-- prospecting; workspace_id NULL = platform, the catalog/geoservices seed).
-- chave = sha256(workspace|tipo|url|type_name), a plain UNIQUE on purpose —
-- see migration 20260919_0001.
CREATE TABLE fontes_de_dados (
    id SERIAL PRIMARY KEY,
    id_hash VARCHAR(36) NOT NULL UNIQUE,
    workspace_id VARCHAR(36),
    tipo VARCHAR(16) NOT NULL DEFAULT 'wfs',
    no VARCHAR(64) NOT NULL DEFAULT 'WFS',
    url VARCHAR(2048) NOT NULL,
    type_name VARCHAR(255),
    chave VARCHAR(64) NOT NULL UNIQUE,
    propriedades JSON NOT NULL,
    instituicao VARCHAR(120),
    grupo VARCHAR(160),
    titulo TEXT,
    descricao TEXT,
    temas JSON,
    esquema JSON,
    dicas TEXT,
    busca TEXT NOT NULL DEFAULT '',
    prioridade SMALLINT NOT NULL DEFAULT 2,
    origem VARCHAR(16) NOT NULL DEFAULT 'manual',
    estado VARCHAR(16) NOT NULL DEFAULT 'nao_verificada',
    verificada_em TIMESTAMP,
    ultimo_erro TEXT,
    vault_hash VARCHAR(64),
    usos INTEGER NOT NULL DEFAULT 0,
    usada_em TIMESTAMP,
    created_by VARCHAR(36),
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now(),
    deleted_at TIMESTAMP
);
CREATE INDEX ix_fontes_de_dados_workspace_id ON fontes_de_dados (workspace_id);
CREATE INDEX ix_fontes_de_dados_tipo_url ON fontes_de_dados (tipo, url);
CREATE INDEX ix_fontes_de_dados_instituicao ON fontes_de_dados (instituicao);

-- uso_do_assistente (how much each assistant turn consumed and cost). One
-- row per TURN, not per conversation: that is where the quota is already
-- charged, so the two never diverge, and a conversation abandoned midway has
-- already recorded what it spent up to that point. `modelo` is stored, not
-- inferred — without it, comparing before and after a model change becomes
-- impossible on the very first change. No conversation content lives here:
-- only counts, the model and the cost.
CREATE TABLE uso_do_assistente (
    id SERIAL PRIMARY KEY,
    id_hash VARCHAR(36) UNIQUE NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    modelo VARCHAR(120) NOT NULL,
    superficie VARCHAR(24),
    entrada INTEGER NOT NULL DEFAULT 0,
    saida INTEGER NOT NULL DEFAULT 0,
    cache_leitura INTEGER NOT NULL DEFAULT 0,
    raciocinio INTEGER NOT NULL DEFAULT 0,
    custo_usd NUMERIC(12,6) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_uso_do_assistente_user ON uso_do_assistente (user_id, created_at);
CREATE INDEX ix_uso_do_assistente_quando ON uso_do_assistente (created_at);

-- workspace_members
CREATE TABLE workspace_members (
    id SERIAL PRIMARY KEY,
    id_hash VARCHAR(36) UNIQUE NOT NULL,
    workspace_id VARCHAR(36) NOT NULL REFERENCES workspaces(id_hash) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id_hash) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL DEFAULT 'viewer',
    invited_by VARCHAR(36),
    joined_at TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT uq_workspace_member UNIQUE (workspace_id, user_id)
);
CREATE INDEX ix_workspace_members_workspace_id ON workspace_members (workspace_id);
CREATE INDEX ix_workspace_members_user_id ON workspace_members (user_id);

-- user_executor_assignments: N:N assignment of executors to users.
-- The comment that used to be here said the table had been "removed" — it
-- wasn't: `app/models/user_executor_assignment.py` is still alive and is
-- read/written by executor_service.create_executor and by all of
-- user_executor_service. Since the script stamps a head LATER than the
-- migrations that create it (20260324_0001 + rename in 20260716_0001),
-- `alembic upgrade head` never created it and any environment bootstrapped
-- from here returned 500 (UndefinedTableError) when assigning an executor or
-- listing a user's executors.
CREATE TABLE user_executor_assignments (
    id SERIAL PRIMARY KEY,
    id_hash VARCHAR(36) UNIQUE NOT NULL,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id_hash) ON DELETE CASCADE,
    executor_id VARCHAR(36) NOT NULL REFERENCES executors(id_hash) ON DELETE CASCADE,
    assigned_by VARCHAR(36),
    assigned_at TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT uq_user_executor UNIQUE (user_id, executor_id)
);
CREATE INDEX ix_user_executor_assignments_user_id ON user_executor_assignments (user_id);
CREATE INDEX ix_user_executor_assignments_executor_id ON user_executor_assignments (executor_id);

-- workflow_groups
CREATE TABLE workflow_groups (
    id SERIAL PRIMARY KEY,
    id_hash VARCHAR(36) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    workspace_id VARCHAR(36),
    position INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX ix_workflow_groups_id_hash ON workflow_groups (id_hash);
CREATE INDEX ix_workflow_groups_workspace_id ON workflow_groups (workspace_id);

-- workspace_files
CREATE TABLE workspace_files (
    id SERIAL PRIMARY KEY,
    id_hash VARCHAR(36) UNIQUE NOT NULL,
    workspace_id VARCHAR(36) NOT NULL,
    -- Nullable since 20260818_0002: a cataloged file that lives on an
    -- executor's disk has no object in MinIO.
    s3_key VARCHAR(1024),
    original_name VARCHAR(512) NOT NULL,
    extension VARCHAR(20) NOT NULL,
    mime_type VARCHAR(120),
    size BIGINT,
    content_md5 VARCHAR(32),
    uploaded_by VARCHAR(36),
    status VARCHAR(16) NOT NULL DEFAULT 'confirmed',
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP,
    -- Last CONTENT write. Distinct from updated_at, which any update of the
    -- row triggers (renaming) and which does NOT fire when the overwrite
    -- changes no field. This is what the Drive listing sorts by.
    content_written_at TIMESTAMP,
    content_location VARCHAR(16) NOT NULL DEFAULT 'minio',
    content_executor_id VARCHAR(36),
    spatial_metadata JSONB
);
CREATE INDEX ix_workspace_files_id_hash ON workspace_files (id_hash);
CREATE INDEX ix_workspace_files_workspace_id ON workspace_files (workspace_id);
CREATE INDEX ix_workspace_files_created_at ON workspace_files (created_at);
CREATE INDEX ix_workspace_file_workspace_created ON workspace_files (workspace_id, created_at);
CREATE INDEX ix_workspace_file_workspace_written ON workspace_files (workspace_id, content_written_at);
CREATE INDEX ix_workspace_files_content_md5 ON workspace_files (content_md5);
CREATE INDEX ix_workspace_files_s3_key ON workspace_files (s3_key);
-- The Drive listing and cleanup find an executor's cataloged files without
-- scanning the table.
CREATE INDEX ix_workspace_files_catalogo_por_executor ON workspace_files (content_executor_id)
    WHERE content_location = 'executor';

-- artifacts
CREATE TABLE artifacts (
    id SERIAL PRIMARY KEY,
    id_hash VARCHAR(36) UNIQUE NOT NULL,
    workspace_id VARCHAR(36) NOT NULL,
    workflow_hash VARCHAR(36),
    run_id VARCHAR(36),
    node_id VARCHAR(255),
    output_key VARCHAR(255) NOT NULL,
    filename VARCHAR(512) NOT NULL,
    format VARCHAR(32),
    size_bytes BIGINT,
    features INTEGER,
    s3_key VARCHAR(1024),
    executor_id VARCHAR(36),
    credential_id VARCHAR(36),
    is_published BOOLEAN NOT NULL DEFAULT false,
    publish_config JSON,
    is_pinned BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    expires_at TIMESTAMP,
    content_location VARCHAR(16) NOT NULL DEFAULT 'minio',
    local_path VARCHAR(1024)
);
CREATE INDEX ix_artifacts_id_hash ON artifacts (id_hash);
CREATE INDEX ix_artifacts_workspace_id ON artifacts (workspace_id);
CREATE INDEX ix_artifacts_workflow_hash ON artifacts (workflow_hash);
CREATE INDEX ix_artifacts_created_at ON artifacts (created_at);
CREATE INDEX ix_artifact_run_id ON artifacts (run_id);
CREATE INDEX ix_artifact_workspace_created ON artifacts (workspace_id, created_at);
-- Artifact lookup by workspace + node + workflow
CREATE INDEX ix_artifacts_workspace_node_wf ON artifacts (workspace_id, node_id, workflow_hash);
-- FK credential_id — usado em CASCADE e JOINs
CREATE INDEX ix_artifacts_credential_id ON artifacts (credential_id);
CREATE INDEX ix_artifacts_s3_key ON artifacts (s3_key);
-- Retention cleanup finds an executor's local artifacts without scanning the
-- table on every cycle.
CREATE INDEX ix_artifacts_local_por_executor ON artifacts (executor_id)
    WHERE content_location = 'executor';
-- One pin-cache per (workflow, node). Without it, two runs of the same
-- workflow finishing together created two rows and every later read found
-- two. The consumer still collapses whatever it finds, for databases that
-- have not migrated.
CREATE UNIQUE INDEX uq_artifact_pin_por_no ON artifacts (workflow_hash, node_id)
    WHERE is_pinned;

-- =============================================================================
-- 3. Tables with composite FKs (depend on the previous ones)
-- =============================================================================

-- workflows
CREATE TABLE workflows (
    id SERIAL PRIMARY KEY,
    id_hash VARCHAR(36) UNIQUE NOT NULL,
    flag_ative BOOLEAN NOT NULL DEFAULT true,
    name VARCHAR NOT NULL,
    description TEXT,
    version VARCHAR,
    priority INTEGER DEFAULT 0,
    -- NOT NULL since 20260828_0001: while the column accepted NULL, the tenant
    -- filters needed an `OR workspace_id IS NULL` that handed every legacy
    -- workflow to any authenticated user.
    workspace_id VARCHAR(36) NOT NULL,
    group_id VARCHAR(36) REFERENCES workflow_groups(id_hash) ON DELETE SET NULL,
    params_schema JSON,
    notification_url VARCHAR,
    definition JSON NOT NULL,
    pinned_outputs JSON,
    pin_metadata JSON,
    portal_access VARCHAR(16) NOT NULL DEFAULT 'disabled',
    portal_shared_with JSON,
    deleted_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now(),
    created_by_id VARCHAR(36),
    updated_by_id VARCHAR(36),
    -- Workflow provenance (20260918_0001): "usuario" (default) or "assistente"
    -- (created by the Home assistant, hidden from listings by default).
    origem VARCHAR(16) NOT NULL DEFAULT 'usuario'
);
-- Name unique only among the LIVE ones. Workflow delete is soft (sets
-- deleted_at and keeps the row): with a full constraint, the name of
-- everything deleted stayed taken forever — and invisible, since no listing
-- shows soft-deleted ones. Duplicate, create and rename all ran into this.
-- It must be an INDEX, not a CONSTRAINT: a constraint does not accept a predicate.
-- Keeps the old constraint's name because workflow_service and
-- workflow_move_service identify the collision via
-- `"uq_workflow_name_workspace" in str(exc.orig)`.
CREATE UNIQUE INDEX uq_workflow_name_workspace
    ON workflows (name, workspace_id) WHERE deleted_at IS NULL;
CREATE INDEX ix_workflows_id_hash ON workflows (id_hash);
CREATE INDEX ix_workflows_workspace_id ON workflows (workspace_id);
-- FK group_id: without an index, the SET NULL from deleting a group scans the table
CREATE INDEX ix_workflows_group_id ON workflows (group_id);
CREATE INDEX ix_workflow_workspace_active ON workflows (workspace_id, flag_ative);

-- schedules
CREATE TABLE schedules (
    id SERIAL PRIMARY KEY,
    id_hash VARCHAR(36) UNIQUE NOT NULL,
    workflow_hash VARCHAR(36) NOT NULL REFERENCES workflows(id_hash) ON DELETE CASCADE,
    strategy VARCHAR NOT NULL,
    "interval" INTEGER,
    unit VARCHAR,
    cron_expression VARCHAR,
    rrule_expression VARCHAR,
    timezone VARCHAR,
    workspace_id VARCHAR(36),
    next_run_at TIMESTAMP,
    last_run_at TIMESTAMP,
    retry_count INTEGER NOT NULL DEFAULT 0,
    job_id VARCHAR UNIQUE NOT NULL,
    active BOOLEAN NOT NULL DEFAULT true
);
CREATE INDEX ix_schedules_id_hash ON schedules (id_hash);
CREATE INDEX ix_schedules_workflow_hash ON schedules (workflow_hash);
CREATE INDEX ix_schedules_workspace_id ON schedules (workspace_id);
-- Scheduler poll (every 30s): active=true + next_run_at <= now()
CREATE INDEX ix_schedules_active_nextrun ON schedules (active, next_run_at ASC);
CREATE INDEX ix_schedules_workspace_nextrun ON schedules (workspace_id, next_run_at ASC);

-- workflow_runs
-- workspace_executors — dedicated executor tiers of the execution policy
-- (tier 1 = primary, 2 = fallback). Migration 20260907_0002.
CREATE TABLE workspace_executors (
    id SERIAL PRIMARY KEY,
    workspace_id VARCHAR(36) NOT NULL REFERENCES workspaces(id_hash) ON DELETE CASCADE,
    executor_id VARCHAR(36) NOT NULL REFERENCES executors(id_hash) ON DELETE CASCADE,
    tier SMALLINT NOT NULL,
    added_by VARCHAR(36),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_workspace_executor UNIQUE (workspace_id, executor_id),
    CONSTRAINT ck_workspace_executor_tier CHECK (tier IN (1, 2))
);
CREATE INDEX ix_workspace_executors_ws_tier ON workspace_executors (workspace_id, tier);
CREATE INDEX ix_workspace_executors_executor ON workspace_executors (executor_id);

CREATE TABLE workflow_runs (
    id SERIAL PRIMARY KEY,
    id_hash VARCHAR(36) UNIQUE NOT NULL,
    flag_ative BOOLEAN NOT NULL DEFAULT true,
    task_id VARCHAR(36) UNIQUE NOT NULL,
    workflow_hash VARCHAR(36) NOT NULL REFERENCES workflows(id_hash) ON DELETE CASCADE,
    -- NOT NULL desde 20260828_0001 — mesma razao de workflows.workspace_id.
    workspace_id VARCHAR(36) NOT NULL,
    schedule_id INTEGER REFERENCES schedules(id) ON DELETE SET NULL,
    status VARCHAR NOT NULL DEFAULT 'running',
    exit_code INTEGER,
    host VARCHAR,
    dispatch_tier VARCHAR(8),
    trigger_source VARCHAR(16),
    triggered_by VARCHAR(36),
    error_category VARCHAR(16),
    start_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    end_time TIMESTAMP WITH TIME ZONE,
    duration_seconds FLOAT,
    error_message TEXT,
    node_stats JSON
);
CREATE INDEX ix_workflow_runs_id_hash ON workflow_runs (id_hash);
CREATE INDEX ix_workflow_runs_task_id ON workflow_runs (task_id);
CREATE INDEX ix_workflow_runs_workflow_hash ON workflow_runs (workflow_hash);
CREATE INDEX ix_workflow_runs_workspace_id ON workflow_runs (workspace_id);
CREATE INDEX ix_workflow_runs_status ON workflow_runs (status);
CREATE INDEX ix_workflow_runs_start_time ON workflow_runs (start_time);
CREATE INDEX ix_wfrun_hash_status_time ON workflow_runs (workflow_hash, status, start_time);
-- Polling of status=running per workspace
CREATE INDEX ix_wfrun_workspace_status_time ON workflow_runs (workspace_id, status, start_time DESC);
-- History without a status filter: without this prefix Postgres reads every
-- row of the workspace and sorts before applying the LIMIT.
CREATE INDEX ix_wfrun_workspace_time ON workflow_runs (workspace_id, start_time DESC);
-- Per-executor panel (?worker_host=) and the metrics' GROUP BY host
CREATE INDEX ix_wfrun_host_time ON workflow_runs (host, start_time DESC);
-- CASCADE DELETE on schedules needs an index on the FK
CREATE INDEX ix_wfrun_schedule_id ON workflow_runs (schedule_id);

-- workflow_versions
CREATE TABLE workflow_versions (
    id SERIAL PRIMARY KEY,
    workflow_hash VARCHAR(36) NOT NULL REFERENCES workflows(id_hash) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    definition JSON NOT NULL,
    change_note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT uq_workflow_version UNIQUE (workflow_hash, version_number)
);
CREATE INDEX ix_workflow_versions_workflow_hash ON workflow_versions (workflow_hash);

-- =============================================================================
-- 4. Portal (PostGIS)
-- =============================================================================

-- portal_layers
CREATE TABLE portal_layers (
    id SERIAL PRIMARY KEY,
    id_hash VARCHAR(36) UNIQUE NOT NULL,
    workflow_hash VARCHAR(36) NOT NULL,
    layer_key VARCHAR(255) NOT NULL,
    geojson_data JSON NOT NULL,
    features INTEGER,
    title VARCHAR(255) NOT NULL DEFAULT 'Camada',
    color VARCHAR(16) NOT NULL DEFAULT '#3b82f6',
    opacity FLOAT NOT NULL DEFAULT 0.5,
    description VARCHAR(1024),
    visible_fields JSON,
    bbox JSON,
    geometry_type VARCHAR(32),
    run_id VARCHAR(36),
    updated_at TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT ix_portal_layer_workflow_key UNIQUE (workflow_hash, layer_key)
);
CREATE INDEX ix_portal_layers_id_hash ON portal_layers (id_hash);
CREATE INDEX ix_portal_layers_workflow_hash ON portal_layers (workflow_hash);

-- portal_features
CREATE TABLE portal_features (
    id SERIAL PRIMARY KEY,
    layer_id INTEGER NOT NULL REFERENCES portal_layers(id) ON DELETE CASCADE,
    properties JSON,
    geom geometry(GEOMETRY, 4326) NOT NULL,
    min_x FLOAT,
    min_y FLOAT,
    max_x FLOAT,
    max_y FLOAT
);
CREATE INDEX ix_portal_features_layer_id ON portal_features (layer_id);
CREATE INDEX ix_portal_feature_layer_bbox ON portal_features (layer_id, min_x, min_y, max_x, max_y);
CREATE INDEX ix_portal_features_geom ON portal_features USING gist (geom);

-- =============================================================================
-- 5. Metrics and billing
-- =============================================================================

-- workflow_run_metrics
CREATE TABLE workflow_run_metrics (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(36) UNIQUE NOT NULL,
    workflow_hash VARCHAR(36) NOT NULL,
    workspace_id VARCHAR(36) NOT NULL,
    executor_id VARCHAR(36),
    executor_name VARCHAR(100),
    executor_ip VARCHAR(45),
    user_id VARCHAR(36),
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ended_at TIMESTAMP WITH TIME ZONE,
    duration_ms FLOAT,
    cpu_avg_pct FLOAT,
    cpu_peak_pct FLOAT,
    mem_avg_mb FLOAT,
    mem_peak_mb FLOAT,
    input_bytes BIGINT DEFAULT 0,
    output_bytes BIGINT DEFAULT 0,
    transfer_bytes BIGINT DEFAULT 0,
    total_features INTEGER DEFAULT 0,
    nodes_executed INTEGER DEFAULT 0,
    nodes_failed INTEGER DEFAULT 0,
    nodes_cached INTEGER DEFAULT 0,
    operation_types JSON,
    spatial_summary JSON,
    status VARCHAR(16) NOT NULL,
    error_type VARCHAR(64),
    error_node_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
CREATE INDEX ix_run_metrics_run_id ON workflow_run_metrics (run_id);
CREATE INDEX ix_run_metrics_workspace ON workflow_run_metrics (workspace_id, started_at);
CREATE INDEX ix_run_metrics_workflow ON workflow_run_metrics (workflow_hash, started_at);
CREATE INDEX ix_run_metrics_executor ON workflow_run_metrics (executor_id, started_at);

-- node_run_metrics
CREATE TABLE node_run_metrics (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(36) NOT NULL,
    node_id VARCHAR(255) NOT NULL,
    node_name VARCHAR(255) NOT NULL,
    node_type VARCHAR(32),
    started_at TIMESTAMP WITH TIME ZONE,
    duration_ms FLOAT,
    cpu_avg_pct FLOAT,
    mem_peak_mb FLOAT,
    input_bytes BIGINT DEFAULT 0,
    output_bytes BIGINT DEFAULT 0,
    input_features INTEGER,
    output_features INTEGER,
    geometry_type VARCHAR(32),
    crs VARCHAR(32),
    bbox JSON,
    vertex_count INTEGER,
    status VARCHAR(16) NOT NULL,
    cache_hit BOOLEAN DEFAULT false,
    error_message TEXT
);
CREATE INDEX ix_node_metrics_run ON node_run_metrics (run_id);
CREATE INDEX ix_node_metrics_name ON node_run_metrics (node_name, started_at);
-- Aggregation of the per-node summary in /observability/metrics/workflow/{id}
CREATE INDEX ix_node_metrics_run_node ON node_run_metrics (run_id, node_id);

-- usage_daily
CREATE TABLE usage_daily (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    workspace_id VARCHAR(36) NOT NULL,
    total_runs INTEGER DEFAULT 0,
    successful_runs INTEGER DEFAULT 0,
    failed_runs INTEGER DEFAULT 0,
    total_cpu_seconds FLOAT DEFAULT 0,
    total_mem_mb_seconds FLOAT DEFAULT 0,
    total_duration_ms FLOAT DEFAULT 0,
    total_input_bytes BIGINT DEFAULT 0,
    total_output_bytes BIGINT DEFAULT 0,
    total_transfer_bytes BIGINT DEFAULT 0,
    total_features BIGINT DEFAULT 0,
    total_nodes_executed INTEGER DEFAULT 0,
    operation_breakdown JSON,
    CONSTRAINT uq_usage_daily UNIQUE (date, workspace_id)
);
CREATE INDEX ix_usage_daily_ws ON usage_daily (workspace_id, date);

-- audit_events
-- Retention: 90 days. Future partitioning: RANGE by monthly timestamp
-- once it passes 10M rows (see 20260324_1500_optimize_audit_events).
CREATE TABLE audit_events (
    id SERIAL PRIMARY KEY,
    workspace_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36),
    action VARCHAR(64) NOT NULL,
    resource_type VARCHAR(64),
    resource_id VARCHAR(255),
    details JSON,
    ip_address VARCHAR(45),
    user_agent TEXT,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
CREATE INDEX ix_audit_events_workspace_id ON audit_events (workspace_id);
CREATE INDEX ix_audit_timestamp ON audit_events (timestamp);
CREATE INDEX ix_audit_workspace_timestamp ON audit_events (workspace_id, timestamp DESC);

-- =============================================================================
-- 6. Alembic version tracking
-- =============================================================================
CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Stamps the ONLY alembic revision (base zero). The id must be the same as
-- `revision` in alembic/versions/20260924_0001_base_zero.py — the migration
-- executes this file, so a database created by psql and one created by
-- `alembic upgrade head` are the same database, stamped the same way. The test
-- test_carimbo_do_alembic_e_a_head_real pins the two ids together.
--
-- Checked against `Base.metadata`: the 28 tables of the core models are
-- here. Those of an extension live in its `schema.sql` (app/extensoes/<nome>),
-- which base zero runs after this one. When adding a new model, also add
-- the CREATE here AND the DROP up above, otherwise the next environment
-- bootstrapped by this script is born broken in the same way.
INSERT INTO alembic_version (version_num) VALUES ('9ed006ca1660');  -- pragma: allowlist secret


-- =============================================================================
-- 7. GRANTs for the application user (optional)
-- =============================================================================
-- If you ran this script as superuser (postgres) and the application
-- connects with a different user (e.g. atlans), UNCOMMENT the lines below
-- replacing `:app_user` with the real name (or run with `-v app_user=atlans`).
--
-- Without this, the app user gets errors like:
--   permission denied for table executor_enrollment_otp
-- when trying to INSERT/SELECT on tables created by postgres.
--
-- \set app_user atlans
--
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO :app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO :app_user;
--
-- -- Future tables/sequences created by postgres inherit the permissions:
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public
--     GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :app_user;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public
--     GRANT USAGE, SELECT ON SEQUENCES TO :app_user;
