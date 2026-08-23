-- Digital Garage V13 — scope research tasks to a machine (fleet-wide intel).
-- ADDITIVE + idempotent. Applied by `cli init` after schema_v12.sql.
--
-- The research queue was global; with a per-machine intelligence dashboard, a
-- Focus ST claim gap should not surface on the ZZR600's page. Tag each task with
-- the variant its underlying claim is scoped to (NULL = fleet-wide / unscoped).

ALTER TABLE research_tasks ADD COLUMN IF NOT EXISTS variant TEXT;
CREATE INDEX IF NOT EXISTS idx_research_tasks_variant ON research_tasks(variant);
