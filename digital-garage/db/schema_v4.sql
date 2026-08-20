-- Digital Garage V4 — the Diagnostic Workbench (professional diagnostic cases).
-- ADDITIVE + idempotent. Applied by `cli init` after schema_v3.sql.
--
-- A diagnostic case combines symptoms, known data (DTCs / mods / issues / telemetry),
-- a tree of tests (TEST → EXPECTED → ACTUAL → INTERPRETATION → RESULT), ranked
-- hypotheses, and evidence-ledger findings. Hypotheses are ranked by a transparent,
-- documented scoring model — relative support, never presented as a calibrated
-- probability. Everything is auditable: findings record what supports/contradicts them.

CREATE TABLE IF NOT EXISTS diagnostic_cases (
    id           SERIAL PRIMARY KEY,
    vehicle_id   INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    code         TEXT,                                  -- human handle, e.g. "DG-0004"
    title        TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open','investigating','resolved','abandoned')),
    outcome      TEXT,
    opened_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at    TIMESTAMPTZ,
    note         TEXT
);
CREATE INDEX IF NOT EXISTS idx_dx_cases_vehicle ON diagnostic_cases(vehicle_id);

CREATE TABLE IF NOT EXISTS case_symptoms (
    id           SERIAL PRIMARY KEY,
    case_id      INTEGER NOT NULL REFERENCES diagnostic_cases(id) ON DELETE CASCADE,
    description  TEXT NOT NULL,
    observed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Known data pulled into the case (a DTC, a mod, a known issue, a telemetry note).
CREATE TABLE IF NOT EXISTS case_evidence (
    id        SERIAL PRIMARY KEY,
    case_id   INTEGER NOT NULL REFERENCES diagnostic_cases(id) ON DELETE CASCADE,
    kind      TEXT NOT NULL
        CHECK (kind IN ('dtc','mod','known_issue','telemetry','measurement','observation')),
    ref       TEXT,                                     -- code / slug / identifier
    detail    TEXT,
    component_slug TEXT                                  -- component this bears on, if known
);

CREATE TABLE IF NOT EXISTS case_hypotheses (
    id             SERIAL PRIMARY KEY,
    case_id        INTEGER NOT NULL REFERENCES diagnostic_cases(id) ON DELETE CASCADE,
    key            TEXT NOT NULL,                        -- stable slug within the case
    description    TEXT NOT NULL,
    component_slug TEXT,
    status         TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open','supported','refuted','confirmed')),
    note           TEXT,
    UNIQUE (case_id, key)
);

-- The diagnostic tree: each test states what to expect, what was found, and how it
-- bears on a hypothesis (confirms/refutes) with a weight.
CREATE TABLE IF NOT EXISTS case_tests (
    id             SERIAL PRIMARY KEY,
    case_id        INTEGER NOT NULL REFERENCES diagnostic_cases(id) ON DELETE CASCADE,
    name           TEXT NOT NULL,
    expected       TEXT,
    actual         TEXT,
    interpretation TEXT,
    result         TEXT NOT NULL DEFAULT 'pending'
        CHECK (result IN ('pending','pass','fail','inconclusive')),
    bears_on       TEXT,                                 -- hypothesis key this test tests
    polarity       TEXT NOT NULL DEFAULT 'confirms'
        CHECK (polarity IN ('confirms','refutes')),
    weight         DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    component_slug TEXT,
    source_label   TEXT,
    sort           INTEGER NOT NULL DEFAULT 0,
    performed_at   TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_dx_tests_case ON case_tests(case_id);

-- Evidence-ledger findings: conclusions with what supports/contradicts them.
CREATE TABLE IF NOT EXISTS case_findings (
    id             SERIAL PRIMARY KEY,
    case_id        INTEGER NOT NULL REFERENCES diagnostic_cases(id) ON DELETE CASCADE,
    text           TEXT NOT NULL,
    supporting     TEXT,
    contradicting  TEXT,
    derived_by     TEXT,                                 -- rule-set / method / person
    superseded_by  INTEGER REFERENCES case_findings(id) ON DELETE SET NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
