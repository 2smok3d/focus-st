-- Digital Garage V6 (Milestone A ontology) — assemblies + typed graph overlays.
-- ADDITIVE + idempotent. Applied by `cli init` after schema_v5.sql.
--
-- Two additions:
--   1. An Assembly level between System and Component (Machine → System → Assembly →
--      Component), optional so existing components are unaffected.
--   2. Domain/medium/direction on component relationships, so the SAME components can be
--      traversed as multiple graph *overlays* — mechanical, airflow, coolant, lubrication,
--      electrical — instead of one generic tree.

CREATE TABLE IF NOT EXISTS assemblies (
    id           SERIAL PRIMARY KEY,
    system_id    INTEGER NOT NULL REFERENCES systems(id) ON DELETE CASCADE,
    slug         TEXT NOT NULL,
    name         TEXT NOT NULL,
    description  TEXT,
    UNIQUE (system_id, slug)
);

ALTER TABLE components ADD COLUMN IF NOT EXISTS assembly_id
    INTEGER REFERENCES assemblies(id) ON DELETE SET NULL;

-- Overlay metadata on the existing typed edges.
ALTER TABLE component_relationships ADD COLUMN IF NOT EXISTS domain TEXT NOT NULL DEFAULT 'function';
ALTER TABLE component_relationships ADD COLUMN IF NOT EXISTS medium TEXT;      -- air | coolant | oil | electrical | mechanical
ALTER TABLE component_relationships ADD COLUMN IF NOT EXISTS direction TEXT NOT NULL DEFAULT 'forward';  -- forward | bidirectional
CREATE INDEX IF NOT EXISTS idx_comp_rel_domain ON component_relationships(domain);
