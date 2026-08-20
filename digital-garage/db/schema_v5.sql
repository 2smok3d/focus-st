-- Digital Garage V5 (Milestone A) — Observation V2, configuration snapshots,
-- environment snapshots, and the generalized machine-event ledger.
-- ADDITIVE + idempotent. Applied by `cli init` after schema_v4.sql.
--
-- Design intent (see docs/DOMAIN-CONSTITUTION.md):
--   * An Observation is a directly-measured/observed fact — never a Finding.
--   * A Measurement is an Observation with a value+unit+method+instrument.
--   * Every observation can point at the configuration snapshot + environment snapshot
--     in effect when it was taken, so a June datalog is never read with August's config.
--   * machine_events is an append-only ledger; current state is a projection of it.

CREATE TABLE IF NOT EXISTS instruments (
    id       SERIAL PRIMARY KEY,
    code     TEXT UNIQUE NOT NULL,                 -- e.g. "DG-TOOL-41"
    name     TEXT NOT NULL,
    kind     TEXT,                                 -- gauge / scan-tool / multimeter / ...
    note     TEXT
);

CREATE TABLE IF NOT EXISTS environment_snapshots (
    id            SERIAL PRIMARY KEY,
    vehicle_id    INTEGER REFERENCES vehicles(id) ON DELETE CASCADE,
    ambient_c     DOUBLE PRECISION,                -- canonical: °C
    humidity_pct  DOUBLE PRECISION,
    baro_kpa      DOUBLE PRECISION,                -- canonical: kPa
    elevation_m   DOUBLE PRECISION,
    weather       TEXT,
    taken_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    note          TEXT
);

CREATE TABLE IF NOT EXISTS configuration_snapshots (
    id          SERIAL PRIMARY KEY,
    vehicle_id  INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    code        TEXT,                               -- human handle, e.g. "snapshot-84"
    config      JSONB NOT NULL,                     -- materialized {components, settings}
    taken_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    note        TEXT
);
CREATE INDEX IF NOT EXISTS idx_config_snap_vehicle ON configuration_snapshots(vehicle_id);

CREATE TABLE IF NOT EXISTS observations (
    id                 SERIAL PRIMARY KEY,
    vehicle_id         INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    subject_kind       TEXT NOT NULL DEFAULT 'component'
        CHECK (subject_kind IN ('component','system','assembly','machine')),
    subject_slug       TEXT,
    obs_type           TEXT NOT NULL DEFAULT 'mechanical'
        CHECK (obs_type IN ('electronic','mechanical','visual','auditory','human')),
    operating_condition TEXT,                       -- idle / cruise / WOT / cold-start / warm ...
    method             TEXT,                        -- e.g. "compression test"
    instrument_id      INTEGER REFERENCES instruments(id) ON DELETE SET NULL,
    -- Measurement payload (an Observation with a value is a Measurement):
    value              DOUBLE PRECISION,
    unit               TEXT,
    result_text        TEXT,                        -- for non-numeric observations
    confidence         DOUBLE PRECISION,
    config_snapshot_id INTEGER REFERENCES configuration_snapshots(id) ON DELETE SET NULL,
    environment_id     INTEGER REFERENCES environment_snapshots(id) ON DELETE SET NULL,
    observed_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    note               TEXT
);
CREATE INDEX IF NOT EXISTS idx_observations_vehicle ON observations(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_observations_subject ON observations(subject_kind, subject_slug);

-- Append-only machine-history ledger. Current state is a projection of these events.
CREATE TABLE IF NOT EXISTS machine_events (
    id             SERIAL PRIMARY KEY,
    vehicle_id     INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    kind           TEXT NOT NULL,                   -- PART_INSTALLED | FLUID_CHANGED | JET_CHANGED | ...
    component_slug TEXT,
    detail         TEXT,
    data           JSONB,
    occurred_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    recorded_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_label   TEXT
);
CREATE INDEX IF NOT EXISTS idx_machine_events_vehicle ON machine_events(vehicle_id, occurred_at);
