-- Digital Garage V9 (Milestone C) — the Workshop Engine: work orders, job readiness,
-- and mandatory post-repair verification.
-- ADDITIVE + idempotent. Applied by `cli init` after schema_v8.sql.
--
-- Lifecycle: ISSUE/FINDING → WORK ORDER → (readiness) → EXECUTION → VERIFICATION →
-- SERVICE EVENT. A work order is never "fixed" on completion — it enters
-- VERIFICATION_REQUIRED, and only a passing post-repair verification (the
-- FINDING → VERIFIED_REPAIR bridge from the Domain Constitution) marks it VERIFIED.

CREATE TABLE IF NOT EXISTS work_orders (
    id             SERIAL PRIMARY KEY,
    vehicle_id     INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    code           TEXT,
    title          TEXT NOT NULL,
    component_slug TEXT,
    from_finding_id INTEGER REFERENCES case_findings(id) ON DELETE SET NULL,
    status         TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft','ready','blocked','in_progress','work_complete',
                          'verification_required','verified','closed','abandoned')),
    repair_state   TEXT NOT NULL DEFAULT 'planned'
        CHECK (repair_state IN ('planned','repair_performed','repair_verified')),
    outcome        TEXT,
    opened_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at      TIMESTAMPTZ,
    note           TEXT
);
CREATE INDEX IF NOT EXISTS idx_work_orders_vehicle ON work_orders(vehicle_id);

CREATE TABLE IF NOT EXISTS work_order_tasks (
    id             SERIAL PRIMARY KEY,
    work_order_id  INTEGER NOT NULL REFERENCES work_orders(id) ON DELETE CASCADE,
    seq            INTEGER NOT NULL DEFAULT 0,
    description    TEXT NOT NULL,
    done           BOOLEAN NOT NULL DEFAULT FALSE,
    note           TEXT
);

CREATE TABLE IF NOT EXISTS work_order_parts (
    id             SERIAL PRIMARY KEY,
    work_order_id  INTEGER NOT NULL REFERENCES work_orders(id) ON DELETE CASCADE,
    name           TEXT NOT NULL,
    part_number    TEXT,
    qty            INTEGER NOT NULL DEFAULT 1,
    available      BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS work_order_tools (
    id             SERIAL PRIMARY KEY,
    work_order_id  INTEGER NOT NULL REFERENCES work_orders(id) ON DELETE CASCADE,
    name           TEXT NOT NULL,
    available      BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS work_order_verifications (
    id             SERIAL PRIMARY KEY,
    work_order_id  INTEGER NOT NULL REFERENCES work_orders(id) ON DELETE CASCADE,
    test           TEXT NOT NULL,
    result         TEXT NOT NULL DEFAULT 'pending'
        CHECK (result IN ('pending','pass','fail')),
    observation_id INTEGER REFERENCES observations(id) ON DELETE SET NULL,
    verified_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    note           TEXT
);
