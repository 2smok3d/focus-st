-- Digital Garage V2 — canonical reference model + claim/evidence provenance.
-- ADDITIVE: this file only adds tables/columns; it never drops or rewrites the V1
-- schema. Applied by `python -m app.cli init` after db/schema.sql. Idempotent.

-- ── Reference model: Manufacturer → Platform → Variant → {Engine, Transmission, Systems → Components}
CREATE TABLE IF NOT EXISTS manufacturers (
    id       SERIAL PRIMARY KEY,
    name     TEXT UNIQUE NOT NULL,
    country  TEXT
);

CREATE TABLE IF NOT EXISTS vehicle_platforms (
    id               SERIAL PRIMARY KEY,
    manufacturer_id  INTEGER NOT NULL REFERENCES manufacturers(id) ON DELETE CASCADE,
    name             TEXT NOT NULL,
    code             TEXT,
    years            TEXT,
    notes            TEXT,
    UNIQUE (manufacturer_id, name)
);

CREATE TABLE IF NOT EXISTS vehicle_variants (
    id           SERIAL PRIMARY KEY,
    platform_id  INTEGER NOT NULL REFERENCES vehicle_platforms(id) ON DELETE CASCADE,
    slug         TEXT UNIQUE NOT NULL,
    name         TEXT NOT NULL,
    trim         TEXT,
    market       TEXT,
    years        TEXT,
    notes        TEXT
);

CREATE TABLE IF NOT EXISTS engines (
    id               SERIAL PRIMARY KEY,
    variant_id       INTEGER NOT NULL REFERENCES vehicle_variants(id) ON DELETE CASCADE,
    code             TEXT NOT NULL,
    displacement_cc  INTEGER,
    config           TEXT,
    aspiration       TEXT,
    fuel             TEXT,
    power            TEXT,
    torque           TEXT,
    notes            TEXT
);

CREATE TABLE IF NOT EXISTS transmissions (
    id          SERIAL PRIMARY KEY,
    variant_id  INTEGER NOT NULL REFERENCES vehicle_variants(id) ON DELETE CASCADE,
    code        TEXT NOT NULL,
    type        TEXT,
    gears       SMALLINT,
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS systems (
    id           SERIAL PRIMARY KEY,
    variant_id   INTEGER NOT NULL REFERENCES vehicle_variants(id) ON DELETE CASCADE,
    parent_id    INTEGER REFERENCES systems(id) ON DELETE CASCADE,
    slug         TEXT NOT NULL,
    name         TEXT NOT NULL,
    description  TEXT,
    sort         INTEGER DEFAULT 0,
    UNIQUE (variant_id, slug)
);

CREATE TABLE IF NOT EXISTS components (
    id           SERIAL PRIMARY KEY,
    system_id    INTEGER NOT NULL REFERENCES systems(id) ON DELETE CASCADE,
    slug         TEXT NOT NULL,
    name         TEXT NOT NULL,
    description  TEXT,
    oem_hint     TEXT,
    UNIQUE (system_id, slug)
);

CREATE TABLE IF NOT EXISTS component_relationships (
    id                 SERIAL PRIMARY KEY,
    from_component_id  INTEGER NOT NULL REFERENCES components(id) ON DELETE CASCADE,
    to_component_id    INTEGER NOT NULL REFERENCES components(id) ON DELETE CASCADE,
    relation           TEXT NOT NULL,
    note               TEXT
);
CREATE INDEX IF NOT EXISTS idx_comp_rel_from ON component_relationships(from_component_id);

-- ── Provenance: source documents + claims + claim evidence
CREATE TABLE IF NOT EXISTS source_documents (
    id            SERIAL PRIMARY KEY,
    source_id     INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    title         TEXT NOT NULL,
    doc_id        TEXT,
    revision      TEXT,
    url           TEXT,
    retrieved_at  TIMESTAMPTZ,
    notes         TEXT
);

CREATE TABLE IF NOT EXISTS claims (
    id            SERIAL PRIMARY KEY,
    subject_type  TEXT NOT NULL,               -- component | variant | engine | system | spec
    subject_key   TEXT NOT NULL,               -- slug/identifier of the subject
    property      TEXT NOT NULL,
    value         TEXT NOT NULL,
    unit          TEXT,
    applicability JSONB,                        -- {variant, years, market}
    verification  verification_state NOT NULL DEFAULT 'UNVERIFIED',  -- resolved verdict
    confidence    DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    conflict      BOOLEAN NOT NULL DEFAULT FALSE,
    notes         TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_claims_subject ON claims(subject_type, subject_key);
CREATE INDEX IF NOT EXISTS idx_claims_property ON claims(property);

CREATE TABLE IF NOT EXISTS claim_evidence (
    id                  SERIAL PRIMARY KEY,
    claim_id            INTEGER NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    source_document_id  INTEGER REFERENCES source_documents(id) ON DELETE SET NULL,
    authority           SMALLINT NOT NULL CHECK (authority BETWEEN 1 AND 6),
    stance              TEXT NOT NULL DEFAULT 'supports',
    on_vehicle          BOOLEAN NOT NULL DEFAULT FALSE,
    page                TEXT,
    section             TEXT,
    excerpt             TEXT,
    source_label        TEXT,
    retrieved_at        TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_claim_evidence_claim ON claim_evidence(claim_id);

-- ── Digital-twin link: the actual vehicle references its reference variant.
ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS variant_id
    INTEGER REFERENCES vehicle_variants(id) ON DELETE SET NULL;
