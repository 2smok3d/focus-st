-- Digital Garage V11 (Milestone D) — Engineering: build scenarios + constraint solver,
-- and the experiment engine (controlled before/after comparisons).
-- ADDITIVE + idempotent. Applied by `cli init` after schema_v10.sql.
--
-- Builds are *computed*, not hard-coded shopping lists: a scenario lists what you want,
-- and the constraint rules (REQUIRES / RECOMMENDS / CONFLICTS / …) determine what else
-- is needed and what clashes. Experiments compare a baseline vs a changed arm and warn
-- when the comparison is poorly controlled (e.g. ambient temperature differs).

CREATE TABLE IF NOT EXISTS build_scenarios (
    id          SERIAL PRIMARY KEY,
    vehicle_id  INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    code        TEXT,
    name        TEXT NOT NULL,
    goal        TEXT,
    note        TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_build_scenarios_vehicle ON build_scenarios(vehicle_id);

CREATE TABLE IF NOT EXISTS build_items (
    id             SERIAL PRIMARY KEY,
    scenario_id    INTEGER NOT NULL REFERENCES build_scenarios(id) ON DELETE CASCADE,
    tag            TEXT NOT NULL,             -- constraint key, e.g. "big-turbo"
    name           TEXT NOT NULL,
    component_slug TEXT,
    est_cost       NUMERIC(10, 2),
    note           TEXT
);

CREATE TABLE IF NOT EXISTS constraint_rules (
    id          SERIAL PRIMARY KEY,
    subject_tag TEXT NOT NULL,
    relation    TEXT NOT NULL
        CHECK (relation IN ('requires','recommends','conflicts','incompatible',
                            'supersedes','alternative')),
    object_tag  TEXT NOT NULL,
    note        TEXT,
    UNIQUE (subject_tag, relation, object_tag)
);

CREATE TABLE IF NOT EXISTS experiments (
    id          SERIAL PRIMARY KEY,
    vehicle_id  INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    code        TEXT,
    question    TEXT NOT NULL,
    metric      TEXT,
    unit        TEXT,
    note        TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS experiment_runs (
    id             SERIAL PRIMARY KEY,
    experiment_id  INTEGER NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    arm            TEXT NOT NULL CHECK (arm IN ('baseline','changed')),
    value          DOUBLE PRECISION,
    unit           TEXT,
    environment_id INTEGER REFERENCES environment_snapshots(id) ON DELETE SET NULL,
    session_id     INTEGER REFERENCES diagnostic_sessions(id) ON DELETE SET NULL,
    note           TEXT
);
CREATE INDEX IF NOT EXISTS idx_experiment_runs_exp ON experiment_runs(experiment_id);
