CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS vehicles (
  vehicle_id text PRIMARY KEY,
  vin text,
  year integer NOT NULL,
  make text NOT NULL,
  model text NOT NULL,
  trim text,
  engine text,
  transmission text,
  timezone text NOT NULL DEFAULT 'America/Phoenix',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sources (
  source_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text NOT NULL,
  authority text NOT NULL CHECK (authority IN ('oem','government','component_manufacturer','technical_reference','community_consensus','individual_anecdote','user_record','raw_telemetry')),
  publisher text,
  url text,
  published_at timestamptz,
  retrieved_at timestamptz NOT NULL DEFAULT now(),
  local_reference text,
  sha256 text,
  notes text
);

CREATE TABLE IF NOT EXISTS claims (
  claim_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  vehicle_id text REFERENCES vehicles(vehicle_id),
  subject text NOT NULL,
  predicate text NOT NULL,
  value_json jsonb NOT NULL,
  unit text,
  confidence numeric(5,4) CHECK (confidence BETWEEN 0 AND 1),
  canonical boolean NOT NULL DEFAULT false,
  conflict_group text,
  verified_at timestamptz,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS claim_sources (
  claim_id uuid NOT NULL REFERENCES claims(claim_id) ON DELETE CASCADE,
  source_id uuid NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE,
  PRIMARY KEY (claim_id, source_id)
);

CREATE TABLE IF NOT EXISTS evidence_objects (
  evidence_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  vehicle_id text NOT NULL REFERENCES vehicles(vehicle_id),
  original_name text NOT NULL,
  media_type text,
  source_format text NOT NULL,
  sha256 text NOT NULL,
  byte_size bigint NOT NULL,
  captured_at timestamptz,
  imported_at timestamptz NOT NULL DEFAULT now(),
  mileage_mi integer CHECK (mileage_mi >= 0),
  timezone text,
  raw_path text NOT NULL,
  normalized_path text,
  parser text,
  parser_version text,
  warnings jsonb NOT NULL DEFAULT '[]'::jsonb,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE(vehicle_id, sha256)
);

CREATE TABLE IF NOT EXISTS diagnostic_sessions (
  session_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  vehicle_id text NOT NULL REFERENCES vehicles(vehicle_id),
  started_at timestamptz,
  ended_at timestamptz,
  mileage_mi integer,
  tool_name text,
  adapter text,
  interface text,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS session_evidence (
  session_id uuid REFERENCES diagnostic_sessions(session_id) ON DELETE CASCADE,
  evidence_id uuid REFERENCES evidence_objects(evidence_id) ON DELETE CASCADE,
  PRIMARY KEY(session_id, evidence_id)
);

CREATE TABLE IF NOT EXISTS dtcs (
  dtc_id bigserial PRIMARY KEY,
  session_id uuid REFERENCES diagnostic_sessions(session_id) ON DELETE CASCADE,
  evidence_id uuid REFERENCES evidence_objects(evidence_id),
  module text,
  code text NOT NULL,
  status text NOT NULL DEFAULT 'unknown',
  description text,
  occurred_at timestamptz,
  mileage_mi integer,
  freeze_frame jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_dtcs_code ON dtcs(code);
CREATE INDEX IF NOT EXISTS idx_dtcs_module ON dtcs(module);

CREATE TABLE IF NOT EXISTS pid_measurements (
  measurement_id bigserial PRIMARY KEY,
  session_id uuid REFERENCES diagnostic_sessions(session_id) ON DELETE CASCADE,
  evidence_id uuid REFERENCES evidence_objects(evidence_id),
  ts timestamptz,
  elapsed_seconds double precision,
  module text,
  pid text NOT NULL,
  numeric_value double precision,
  text_value text,
  unit text,
  raw_value text
);
CREATE INDEX IF NOT EXISTS idx_pid_session_pid ON pid_measurements(session_id,pid);
CREATE INDEX IF NOT EXISTS idx_pid_ts ON pid_measurements(ts);

CREATE TABLE IF NOT EXISTS can_frames (
  frame_id bigserial PRIMARY KEY,
  session_id uuid REFERENCES diagnostic_sessions(session_id) ON DELETE CASCADE,
  evidence_id uuid REFERENCES evidence_objects(evidence_id),
  elapsed_seconds double precision,
  ts timestamptz,
  channel text,
  arbitration_id bigint NOT NULL,
  is_extended_id boolean NOT NULL DEFAULT false,
  is_fd boolean NOT NULL DEFAULT false,
  is_rx boolean,
  dlc integer,
  data_hex text NOT NULL,
  decoded_signals jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_can_session_id ON can_frames(session_id,arbitration_id);

CREATE TABLE IF NOT EXISTS component_events (
  event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  vehicle_id text NOT NULL REFERENCES vehicles(vehicle_id),
  component_id text NOT NULL,
  event_type text NOT NULL,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  recorded_at timestamptz NOT NULL DEFAULT now(),
  mileage_mi integer,
  manufacturer text,
  part_name text,
  part_number text,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  supersedes_event_id uuid REFERENCES component_events(event_id),
  voided boolean NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS idx_component_events_current ON component_events(vehicle_id,component_id,occurred_at DESC);

CREATE TABLE IF NOT EXISTS service_records (
  service_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  vehicle_id text NOT NULL REFERENCES vehicles(vehicle_id),
  task_id text,
  service_date date NOT NULL,
  mileage_mi integer NOT NULL,
  description text NOT NULL,
  fluid_spec text,
  parts jsonb NOT NULL DEFAULT '[]'::jsonb,
  cost_parts numeric(12,2),
  cost_labor numeric(12,2),
  vendor text,
  verification text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS maintenance_tasks (
  task_id text PRIMARY KEY,
  name text NOT NULL,
  system text NOT NULL,
  interval_miles integer,
  interval_months integer,
  severe_interval_miles integer,
  severe_interval_months integer,
  oem_required boolean NOT NULL DEFAULT false,
  notes text
);

CREATE TABLE IF NOT EXISTS part_options (
  part_option_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  vehicle_id text REFERENCES vehicles(vehicle_id),
  slot text NOT NULL,
  category text NOT NULL,
  manufacturer text NOT NULL,
  part_name text NOT NULL,
  part_number text,
  fitment_status text NOT NULL DEFAULT 'unverified',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS diagnostic_cases (
  case_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  vehicle_id text NOT NULL REFERENCES vehicles(vehicle_id),
  title text NOT NULL,
  status text NOT NULL DEFAULT 'open',
  severity text NOT NULL DEFAULT 'normal',
  symptom text,
  opened_at timestamptz NOT NULL DEFAULT now(),
  closed_at timestamptz,
  hypothesis_log jsonb NOT NULL DEFAULT '[]'::jsonb,
  test_log jsonb NOT NULL DEFAULT '[]'::jsonb,
  resolution text,
  verification text
);

CREATE TABLE IF NOT EXISTS approval_intents (
  approval_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  vehicle_id text REFERENCES vehicles(vehicle_id),
  capability text NOT NULL,
  reason text NOT NULL,
  target text,
  payload_digest text,
  requested_at timestamptz NOT NULL DEFAULT now(),
  approved boolean NOT NULL DEFAULT false,
  approved_at timestamptz,
  expires_at timestamptz
);

INSERT INTO vehicles(vehicle_id,year,make,model,trim,engine,transmission)
VALUES ('focus-st-2017',2017,'Ford','Focus ST','ST1','2.0L GTDI EcoBoost I4','Getrag-Ford MMT6 6-speed manual')
ON CONFLICT(vehicle_id) DO NOTHING;
