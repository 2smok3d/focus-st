-- Digital Garage schema — the truth store for one vehicle.
-- This file is the canonical DDL; app/models.py mirrors it in SQLAlchemy.
-- It runs automatically on first `docker compose up db` (initdb), and
-- `python -m app.cli init` executes it against an existing database.

-- ---------------------------------------------------------------------------
-- Evidence grading (shared value domains)
-- ---------------------------------------------------------------------------
-- Source authority rank: 1 = OEM/factory … 6 = unknown/anecdotal.
-- Verification state: how mature the evidence for a claim is. Kept as TEXT with
-- a CHECK (not a Postgres ENUM) so the ORM's plain string binds validate without
-- needing an explicit enum cast on every insert.
DO $$ BEGIN
    CREATE DOMAIN verification_state AS TEXT
        CONSTRAINT verification_state_check CHECK (
            VALUE IN ('UNVERIFIED', 'CORROBORATED', 'OEM_VERIFIED', 'VEHICLE_VERIFIED')
        );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE DOMAIN proposal_status AS TEXT
        CONSTRAINT proposal_status_check CHECK (
            VALUE IN ('pending', 'approved', 'rejected')
        );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ---------------------------------------------------------------------------
-- Sources — every fact can point at where it came from, with a rank.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sources (
    id           SERIAL PRIMARY KEY,
    name         TEXT NOT NULL,
    kind         TEXT NOT NULL,            -- oem_manual, tsb, forscan, forum, retailer, measurement...
    authority    SMALLINT NOT NULL CHECK (authority BETWEEN 1 AND 6),
    url          TEXT,
    notes        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- The vehicle. One row in normal use, but modeled as a table anyway.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vehicles (
    id           SERIAL PRIMARY KEY,
    vin          TEXT UNIQUE NOT NULL,
    year         SMALLINT,
    make         TEXT,
    model        TEXT,
    trim         TEXT,
    engine       TEXT,
    transmission TEXT,
    notes        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Specs — graded key/value facts about the vehicle (torque values, capacities,
-- ratios). Each carries a verification state and an optional source.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS specs (
    id           SERIAL PRIMARY KEY,
    vehicle_id   INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    category     TEXT NOT NULL,           -- engine, drivetrain, chassis, fluids, torque...
    name         TEXT NOT NULL,
    value        TEXT NOT NULL,
    unit         TEXT,
    verification verification_state NOT NULL DEFAULT 'UNVERIFIED',
    source_id    INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (vehicle_id, category, name)
);

-- ---------------------------------------------------------------------------
-- Odometer — the mileage timeline everything else is measured against.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS odometer_readings (
    id           SERIAL PRIMARY KEY,
    vehicle_id   INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    miles        INTEGER NOT NULL CHECK (miles >= 0),
    recorded_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_id    INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    note         TEXT
);

-- ---------------------------------------------------------------------------
-- Maintenance intervals + service events (the maintenance-due engine).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS maintenance_intervals (
    id             SERIAL PRIMARY KEY,
    vehicle_id     INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    item           TEXT NOT NULL,          -- "Engine oil & filter", "MMT6 fluid"...
    interval_miles INTEGER,                -- NULL = time-only item
    interval_months INTEGER,               -- NULL = mileage-only item
    verification   verification_state NOT NULL DEFAULT 'UNVERIFIED',
    source_id      INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    note           TEXT,
    UNIQUE (vehicle_id, item)
);

CREATE TABLE IF NOT EXISTS service_events (
    id            SERIAL PRIMARY KEY,
    vehicle_id    INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    interval_id   INTEGER REFERENCES maintenance_intervals(id) ON DELETE SET NULL,
    item          TEXT NOT NULL,
    performed_at  DATE NOT NULL,
    miles         INTEGER CHECK (miles >= 0),
    cost          NUMERIC(10,2),
    vendor        TEXT,
    note          TEXT,
    source_id     INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Mods — parts that diverge from stock (mirrors the PWA's <!-- MOD --> idea).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mods (
    id            SERIAL PRIMARY KEY,
    vehicle_id    INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    slot          TEXT NOT NULL,           -- "Intercooler", "Rear motor mount"...
    part_name     TEXT NOT NULL,
    part_number   TEXT,
    installed_on  DATE,
    installed_miles INTEGER,
    cost          NUMERIC(10,2),
    url           TEXT,
    stage         TEXT,                    -- R1, P1, P2... (see KB 09)
    verification  verification_state NOT NULL DEFAULT 'UNVERIFIED',
    source_id     INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    note          TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Issues — open/closed problems + their DTC linkage.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS issues (
    id            SERIAL PRIMARY KEY,
    vehicle_id    INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    title         TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'open',  -- open, monitoring, resolved
    severity      TEXT,                    -- info, warn, stop
    opened_at     DATE NOT NULL DEFAULT CURRENT_DATE,
    resolved_at   DATE,
    root_cause    TEXT,
    verification  verification_state NOT NULL DEFAULT 'UNVERIFIED',
    note          TEXT
);

-- ---------------------------------------------------------------------------
-- Parts catalog (reference) + generated search links live in domain, not here.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS parts (
    id            SERIAL PRIMARY KEY,
    vehicle_id    INTEGER REFERENCES vehicles(id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    part_number   TEXT,
    category      TEXT,
    oem           BOOLEAN NOT NULL DEFAULT FALSE,
    approx_price  NUMERIC(10,2),
    url           TEXT,
    source_id     INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    note          TEXT
);

-- ---------------------------------------------------------------------------
-- Diagnostic ingest — raw-preserving. Every artifact keeps its bytes + hash.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS diagnostic_sessions (
    id             SERIAL PRIMARY KEY,
    vehicle_id     INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    kind           TEXT NOT NULL,          -- forscan, candump, obdlink...
    captured_at    TIMESTAMPTZ,
    ingested_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    miles          INTEGER,
    sha256         CHAR(64) NOT NULL UNIQUE,  -- integrity + dedupe
    raw_path       TEXT NOT NULL,          -- byte-for-byte original on disk
    source_id      INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    note           TEXT
);

CREATE TABLE IF NOT EXISTS dtcs (
    id            SERIAL PRIMARY KEY,
    session_id    INTEGER NOT NULL REFERENCES diagnostic_sessions(id) ON DELETE CASCADE,
    code          TEXT NOT NULL,           -- P0299, U0100...
    module        TEXT,                    -- PCM, ABS, BCM...
    status        TEXT,                    -- current, pending, permanent, history
    description   TEXT
);
CREATE INDEX IF NOT EXISTS idx_dtcs_code ON dtcs(code);

CREATE TABLE IF NOT EXISTS measurements (
    id            SERIAL PRIMARY KEY,
    session_id    INTEGER NOT NULL REFERENCES diagnostic_sessions(id) ON DELETE CASCADE,
    pid           TEXT NOT NULL,           -- channel/PID name
    value         DOUBLE PRECISION,
    unit          TEXT,
    t_offset_s    DOUBLE PRECISION         -- seconds from session start
);
CREATE INDEX IF NOT EXISTS idx_meas_session_pid ON measurements(session_id, pid);

CREATE TABLE IF NOT EXISTS can_frames (
    id            SERIAL PRIMARY KEY,
    session_id    INTEGER NOT NULL REFERENCES diagnostic_sessions(id) ON DELETE CASCADE,
    t_offset_s    DOUBLE PRECISION,
    can_id        TEXT NOT NULL,           -- hex arbitration id
    dlc           SMALLINT,
    data_hex      TEXT
);
CREATE INDEX IF NOT EXISTS idx_can_session_id ON can_frames(session_id, can_id);

-- ---------------------------------------------------------------------------
-- Recalls / safety campaigns. Seeded with the known Focus ST campaigns and
-- refreshable from the NHTSA recallsByVehicle API. Per-VIN completion is not in
-- the free API, so `status` defaults to 'unknown' until confirmed at a dealer.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS recalls (
    id              SERIAL PRIMARY KEY,
    vehicle_id      INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    campaign_number TEXT NOT NULL,          -- NHTSA campaign or Ford program (e.g. 18S32)
    origin          TEXT NOT NULL DEFAULT 'nhtsa',  -- nhtsa | ford-known
    component       TEXT,
    summary         TEXT,
    consequence     TEXT,
    remedy          TEXT,
    report_date     DATE,
    status          TEXT NOT NULL DEFAULT 'unknown',  -- unknown | open | completed
    verification    verification_state NOT NULL DEFAULT 'CORROBORATED',
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    note            TEXT,
    UNIQUE (vehicle_id, campaign_number)
);

-- ---------------------------------------------------------------------------
-- The approval boundary. Agents write here; humans approve; only then does
-- the target table change. entity/entity_id/patch describe the intended write.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS change_proposals (
    id            SERIAL PRIMARY KEY,
    vehicle_id    INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    entity        TEXT NOT NULL,           -- 'mod', 'issue', 'spec', 'service_event'...
    op            TEXT NOT NULL DEFAULT 'insert',  -- insert | update
    entity_id     INTEGER,                 -- target row for updates
    patch         JSONB NOT NULL,          -- proposed columns/values
    rationale     TEXT,
    proposed_by   TEXT NOT NULL DEFAULT 'agent',
    status        proposal_status NOT NULL DEFAULT 'pending',
    approved_by   TEXT,
    decided_at    TIMESTAMPTZ,
    applied_id    INTEGER,                 -- id of the row created/updated on approval
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_proposals_status ON change_proposals(status);
