-- Digital Garage V10 (Milestone E) — Telemetry V2: canonical channel registry +
-- detected-event ledger.
-- ADDITIVE + idempotent. Applied by `cli init` after schema_v9.sql.
--
-- Layers: RAW (diagnostic_sessions + measurements, already present) → normalized
-- channels (this registry) → derived signals (computed) → EVENTS (detected, stored
-- here) → observations/case evidence. Raw is never mutated.

CREATE TABLE IF NOT EXISTS telemetry_channels (
    id             SERIAL PRIMARY KEY,
    canonical_name TEXT UNIQUE NOT NULL,        -- e.g. "boost_actual"
    unit           TEXT,
    description    TEXT,
    normal_min     DOUBLE PRECISION,
    normal_max     DOUBLE PRECISION,
    warn_min       DOUBLE PRECISION,
    warn_max       DOUBLE PRECISION,
    derived        BOOLEAN NOT NULL DEFAULT FALSE,  -- computed vs measured
    formula        TEXT
);

CREATE TABLE IF NOT EXISTS telemetry_events (
    id             SERIAL PRIMARY KEY,
    session_id     INTEGER REFERENCES diagnostic_sessions(id) ON DELETE CASCADE,
    kind           TEXT NOT NULL,                -- WOT_PULL | KNOCK_EVENT | OVER_TEMP | ...
    t_start        DOUBLE PRECISION,
    t_end          DOUBLE PRECISION,
    severity       TEXT NOT NULL DEFAULT 'info'
        CHECK (severity IN ('info','warn','critical')),
    channel        TEXT,
    detail         TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_telemetry_events_session ON telemetry_events(session_id);
