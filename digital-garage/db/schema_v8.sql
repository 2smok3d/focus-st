-- Digital Garage V8 (Milestone B) — Diagnostic Core: failure-mode library +
-- reusable diagnostic-test library.
-- ADDITIVE + idempotent. Applied by `cli init` after schema_v7.sql.
--
-- Failure modes are defined ONCE, independent of any specific case: what fails, on
-- which components, what you'd observe, the confirming test, the disconfirming
-- evidence, the consequence. Diagnostic tests are reusable and carry an information
-- value + cost/risk so the workbench can recommend the single best next test.

CREATE TABLE IF NOT EXISTS failure_modes (
    id                    SERIAL PRIMARY KEY,
    slug                  TEXT UNIQUE NOT NULL,
    name                  TEXT NOT NULL,
    system_slug           TEXT,
    description           TEXT,
    expected_observations TEXT,
    disconfirming_evidence TEXT,
    consequences          TEXT,
    severity              TEXT NOT NULL DEFAULT 'moderate'
        CHECK (severity IN ('low','moderate','high','critical'))
);

CREATE TABLE IF NOT EXISTS failure_mode_components (
    id               SERIAL PRIMARY KEY,
    failure_mode_id  INTEGER NOT NULL REFERENCES failure_modes(id) ON DELETE CASCADE,
    component_slug   TEXT NOT NULL,
    UNIQUE (failure_mode_id, component_slug)
);

CREATE TABLE IF NOT EXISTS failure_mode_symptoms (
    id               SERIAL PRIMARY KEY,
    failure_mode_id  INTEGER NOT NULL REFERENCES failure_modes(id) ON DELETE CASCADE,
    symptom          TEXT NOT NULL,
    keywords         TEXT                       -- space-separated match keywords
);

CREATE TABLE IF NOT EXISTS diagnostic_tests (
    id             SERIAL PRIMARY KEY,
    slug           TEXT UNIQUE NOT NULL,
    name           TEXT NOT NULL,
    purpose        TEXT,
    procedure      TEXT,
    discriminates  TEXT,                        -- failure_mode slug this test bears on
    effect         TEXT NOT NULL DEFAULT 'confirms'   -- confirms | refutes
        CHECK (effect IN ('confirms','refutes')),
    info_gain      DOUBLE PRECISION NOT NULL DEFAULT 0.5,   -- 0..1 discriminating power
    cost           SMALLINT NOT NULL DEFAULT 2 CHECK (cost BETWEEN 1 AND 5),
    time_min       INTEGER,
    difficulty     SMALLINT NOT NULL DEFAULT 2 CHECK (difficulty BETWEEN 1 AND 5),
    risk           SMALLINT NOT NULL DEFAULT 1 CHECK (risk BETWEEN 1 AND 5),
    required_tools TEXT,
    required_state TEXT
);
CREATE INDEX IF NOT EXISTS idx_dtests_discriminates ON diagnostic_tests(discriminates);
