-- Digital Garage V7 (Milestone A ontology) — physical-component lifecycle tracking.
-- ADDITIVE + idempotent. Applied by `cli init` after schema_v6.sql.
--
-- A *physical component* is a specific real part (e.g. "TZ250 right piston #P-0042")
-- with its own identity, usage accumulators, install history, and inspections —
-- independent of any machine. Removing it from a machine does NOT delete it; its
-- lifecycle continues (in inventory, rebuilt, or scrapped).

CREATE TABLE IF NOT EXISTS physical_components (
    id                SERIAL PRIMARY KEY,
    code              TEXT UNIQUE NOT NULL,               -- e.g. "P-0042"
    name              TEXT NOT NULL,
    component_slug    TEXT,                               -- the kind of component it is
    manufacturer      TEXT,
    part_number       TEXT,
    status            TEXT NOT NULL DEFAULT 'in_inventory'
        CHECK (status IN ('in_service','removed','in_inventory','rebuilding','scrapped')),
    condition         TEXT NOT NULL DEFAULT 'unknown'
        CHECK (condition IN ('unknown','healthy','degraded','suspect','failed')),
    hours             DOUBLE PRECISION NOT NULL DEFAULT 0,
    sessions          INTEGER NOT NULL DEFAULT 0,
    miles             INTEGER NOT NULL DEFAULT 0,
    cycles            INTEGER NOT NULL DEFAULT 0,
    note              TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS component_installations (
    id                    SERIAL PRIMARY KEY,
    physical_component_id INTEGER NOT NULL REFERENCES physical_components(id) ON DELETE CASCADE,
    vehicle_id            INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    slot_slug             TEXT,                           -- which component slot on the machine
    installed_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    removed_at            TIMESTAMPTZ,                    -- NULL = currently installed
    note                  TEXT
);
CREATE INDEX IF NOT EXISTS idx_installs_pc ON component_installations(physical_component_id);
CREATE INDEX IF NOT EXISTS idx_installs_current
    ON component_installations(vehicle_id, slot_slug) WHERE removed_at IS NULL;

CREATE TABLE IF NOT EXISTS component_inspections (
    id                    SERIAL PRIMARY KEY,
    physical_component_id INTEGER NOT NULL REFERENCES physical_components(id) ON DELETE CASCADE,
    result                TEXT NOT NULL DEFAULT 'healthy'
        CHECK (result IN ('healthy','degraded','suspect','failed')),
    value                 DOUBLE PRECISION,
    unit                  TEXT,
    method                TEXT,
    inspected_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    note                  TEXT
);
CREATE INDEX IF NOT EXISTS idx_inspections_pc ON component_inspections(physical_component_id);
