-- AgriSat Risk — initial schema (SRS v2.0)
-- Supabase: enable PostGIS in Dashboard first, then run this migration

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA extensions;

-- Enums
CREATE TYPE user_role AS ENUM ('admin', 'loan_officer');
CREATE TYPE data_tier AS ENUM ('tier1_planet', 'tier2_sen2sr', 'tier3_sar');
CREATE TYPE risk_tier AS ENUM ('normal', 'watch', 'elevated', 'high', 'insufficient_data');
CREATE TYPE field_status AS ENUM ('active', 'archived');

-- Institutions (FR-1.1)
CREATE TABLE institutions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  contact_email TEXT NOT NULL,
  contact_phone TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- User profiles linked to auth.users (FR-1.2, FR-1.4)
CREATE TABLE profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
  role user_role NOT NULL DEFAULT 'loan_officer',
  full_name TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Registered field boundaries (FR-2.x)
CREATE TABLE fields (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
  created_by UUID REFERENCES profiles(id) ON DELETE SET NULL,
  name TEXT,
  boundary GEOMETRY(Polygon, 4326) NOT NULL,
  area_hectares NUMERIC(10, 4),
  crop_type TEXT NOT NULL,
  sowing_date DATE NOT NULL,
  farmer_ref_id TEXT,
  loan_ref_id TEXT,
  status field_status NOT NULL DEFAULT 'active',
  resolution_warning BOOLEAN NOT NULL DEFAULT false,
  pilot_district TEXT NOT NULL DEFAULT 'faisalabad',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX fields_institution_idx ON fields(institution_id);
CREATE INDEX fields_boundary_gix ON fields USING GIST(boundary);
CREATE INDEX fields_status_idx ON fields(status);

-- Fused vegetation time-series (FR-3.9)
CREATE TABLE vegetation_readings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  field_id UUID NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
  acquisition_date DATE NOT NULL,
  days_since_sowing INTEGER NOT NULL,
  data_tier data_tier NOT NULL,
  ndvi NUMERIC(8, 5),
  evi NUMERIC(8, 5),
  sar_index NUMERIC(8, 5),
  cloud_fraction NUMERIC(5, 4),
  is_fused BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(field_id, acquisition_date, data_tier)
);

CREATE INDEX vegetation_readings_field_date_idx ON vegetation_readings(field_id, acquisition_date);

-- Historical baseline by crop growth stage (FR-4.2)
CREATE TABLE baseline_stats (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  crop_type TEXT NOT NULL,
  pilot_district TEXT NOT NULL,
  days_since_sowing INTEGER NOT NULL,
  mean_index NUMERIC(8, 5) NOT NULL,
  std_index NUMERIC(8, 5) NOT NULL,
  sample_years INTEGER NOT NULL DEFAULT 5,
  primary_tier data_tier NOT NULL DEFAULT 'tier3_sar',
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(crop_type, pilot_district, days_since_sowing)
);

-- Current risk assessments (FR-5.x)
CREATE TABLE risk_assessments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  field_id UUID NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
  assessed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  days_since_sowing INTEGER NOT NULL,
  z_score NUMERIC(8, 4),
  risk_tier risk_tier NOT NULL,
  primary_data_tier data_tier,
  index_value NUMERIC(8, 5),
  baseline_mean NUMERIC(8, 5),
  baseline_std NUMERIC(8, 5),
  rainfall_mm NUMERIC(8, 2),
  rainfall_anomaly_pct NUMERIC(8, 2),
  explanation TEXT NOT NULL,
  is_current BOOLEAN NOT NULL DEFAULT true
);

CREATE INDEX risk_assessments_field_current_idx ON risk_assessments(field_id) WHERE is_current = true;

-- Audit log for risk flags (FR-5.4)
CREATE TABLE risk_audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  field_id UUID NOT NULL REFERENCES fields(id) ON DELETE CASCADE,
  risk_assessment_id UUID REFERENCES risk_assessments(id) ON DELETE SET NULL,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Tier availability tracking (internal admin)
CREATE TABLE tier_status (
  tier data_tier PRIMARY KEY,
  is_available BOOLEAN NOT NULL DEFAULT true,
  quota_remaining_sqkm NUMERIC(12, 2),
  notes TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO tier_status (tier, is_available, notes) VALUES
  ('tier3_sar', true, 'Always available via GEE'),
  ('tier2_sen2sr', true, 'Open-source model'),
  ('tier1_planet', false, 'Pending E&R Program approval');

-- Updated_at trigger
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER institutions_updated_at BEFORE UPDATE ON institutions
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER profiles_updated_at BEFORE UPDATE ON profiles
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER fields_updated_at BEFORE UPDATE ON fields
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- RLS (FR-1.3, NFR-4)
ALTER TABLE institutions ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE fields ENABLE ROW LEVEL SECURITY;
ALTER TABLE vegetation_readings ENABLE ROW LEVEL SECURITY;
ALTER TABLE baseline_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_audit_log ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION auth_institution_id()
RETURNS UUID AS $$
  SELECT institution_id FROM profiles WHERE id = auth.uid()
$$ LANGUAGE sql STABLE SECURITY DEFINER;

CREATE POLICY profiles_select_own ON profiles
  FOR SELECT USING (id = auth.uid() OR institution_id = auth_institution_id());

CREATE POLICY profiles_update_own ON profiles
  FOR UPDATE USING (id = auth.uid());

CREATE POLICY institutions_select_own ON institutions
  FOR SELECT USING (id = auth_institution_id());

CREATE POLICY fields_all_own_institution ON fields
  FOR ALL USING (institution_id = auth_institution_id())
  WITH CHECK (institution_id = auth_institution_id());

CREATE POLICY vegetation_readings_select ON vegetation_readings
  FOR SELECT USING (
    field_id IN (SELECT id FROM fields WHERE institution_id = auth_institution_id())
  );

CREATE POLICY baseline_stats_select ON baseline_stats
  FOR SELECT USING (true);

CREATE POLICY risk_assessments_select ON risk_assessments
  FOR SELECT USING (
    field_id IN (SELECT id FROM fields WHERE institution_id = auth_institution_id())
  );

CREATE POLICY risk_audit_log_select ON risk_audit_log
  FOR SELECT USING (
    field_id IN (SELECT id FROM fields WHERE institution_id = auth_institution_id())
  );

-- Institution registration (called from backend with service role)
CREATE OR REPLACE FUNCTION register_institution(
  p_name TEXT,
  p_contact_email TEXT,
  p_admin_user_id UUID,
  p_admin_name TEXT DEFAULT NULL,
  p_contact_phone TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
  v_institution_id UUID;
BEGIN
  INSERT INTO institutions (name, contact_email, contact_phone)
  VALUES (p_name, p_contact_email, p_contact_phone)
  RETURNING id INTO v_institution_id;

  INSERT INTO profiles (id, institution_id, role, full_name)
  VALUES (p_admin_user_id, v_institution_id, 'admin', p_admin_name);

  RETURN v_institution_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
