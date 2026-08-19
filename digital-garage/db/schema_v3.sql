-- Digital Garage V3 — the Machine State Engine (temporal digital twin).
-- ADDITIVE + idempotent. Applied by `cli init` after schema_v2.sql.
--
-- A machine is not "a set of current records" — it is a state that changes over time.
-- Each component of an actual vehicle gets a *condition* (physical/config) and a
-- *knowledge_state* (how we know it), recorded at a point in time. A new observation
-- supersedes the prior one instead of overwriting it, so MachineState(T) is
-- reconstructable for any T: the rows whose [observed_at, superseded_at) span T.

CREATE TABLE IF NOT EXISTS component_states (
    id              SERIAL PRIMARY KEY,
    vehicle_id      INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    -- Link to the reference component when one exists; keep the slug regardless so
    -- machines without a full reference model (older bikes) still get state tracking.
    component_id    INTEGER REFERENCES components(id) ON DELETE SET NULL,
    component_slug  TEXT NOT NULL,

    -- Physical / configuration condition of the component on THIS machine.
    condition       TEXT NOT NULL DEFAULT 'stock'
        CHECK (condition IN ('unknown','stock','healthy','degraded','suspect',
                             'failed','removed','modified','planned')),
    -- Epistemic state: WHY we believe the above (keeps inference distinct from fact).
    knowledge_state TEXT NOT NULL DEFAULT 'UNKNOWN'
        CHECK (knowledge_state IN ('KNOWN','DIRECTLY_OBSERVED','OEM_ASSERTED',
                                  'CORROBORATED','INFERRED','ESTIMATED','DISPUTED','UNKNOWN')),

    installed_part  TEXT,                       -- what is actually fitted (if not stock)
    confidence      DOUBLE PRECISION NOT NULL DEFAULT 0.0,

    -- Usage accumulators feed later degradation / remaining-life models.
    hours           DOUBLE PRECISION,
    miles           INTEGER,
    cycles          INTEGER,

    observed_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    superseded_at   TIMESTAMPTZ,                -- NULL = current state
    note            TEXT,
    source_label    TEXT
);
CREATE INDEX IF NOT EXISTS idx_component_states_vehicle ON component_states(vehicle_id);
-- Fast "current state per component" lookup.
CREATE INDEX IF NOT EXISTS idx_component_states_current
    ON component_states(vehicle_id, component_slug) WHERE superseded_at IS NULL;

-- Per-machine capability profile — the UI/agents adapt to what a machine supports
-- (no "Scan DTC" on a carbureted two-stroke). Vehicle-agnostic, additive.
CREATE TABLE IF NOT EXISTS machine_capabilities (
    id          SERIAL PRIMARY KEY,
    vehicle_id  INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    capability  TEXT NOT NULL,                  -- can_bus | obd | dtc | ecu_telemetry | carb | ...
    supported   BOOLEAN NOT NULL DEFAULT TRUE,
    note        TEXT,
    UNIQUE (vehicle_id, capability)
);
