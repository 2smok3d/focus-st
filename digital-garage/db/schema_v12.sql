-- Digital Garage V12 (Milestone F) — Knowledge Operations: research queue + entity aliases.
-- ADDITIVE + idempotent. Applied by `cli init` after schema_v11.sql.
--
-- The knowledge-quality dashboard is a pure projection over the existing `claims`
-- table (no new storage). This file adds the research queue (gaps → prioritized tasks)
-- and an alias table for entity resolution ("22R-E" / "22RE" / "22R E" → one identity).

CREATE TABLE IF NOT EXISTS research_tasks (
    id           SERIAL PRIMARY KEY,
    kind         TEXT NOT NULL,                 -- conflict | unverified | missing_unit | missing_applicability
    priority     TEXT NOT NULL DEFAULT 'medium'
        CHECK (priority IN ('low','medium','high','critical')),
    subject      TEXT NOT NULL,                 -- what the task is about (claim key etc.)
    detail       TEXT,
    status       TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open','in_progress','resolved','wont_fix')),
    dedupe_key   TEXT UNIQUE,                   -- keeps generation idempotent
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_research_tasks_status ON research_tasks(status, priority);

CREATE TABLE IF NOT EXISTS entity_aliases (
    id         SERIAL PRIMARY KEY,
    alias      TEXT NOT NULL,
    canonical  TEXT NOT NULL,
    kind       TEXT,                            -- engine | part | platform | ...
    note       TEXT,
    UNIQUE (alias, canonical)
);
