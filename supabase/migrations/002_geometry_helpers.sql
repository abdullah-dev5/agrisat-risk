-- M11: PostGIS geometry helpers + grants for backend service role

-- Insert field with GeoJSON boundary (PostgREST geometry insert is unreliable)
CREATE OR REPLACE FUNCTION create_field_from_geojson(
  p_institution_id UUID,
  p_created_by UUID,
  p_name TEXT,
  p_boundary JSONB,
  p_area_hectares NUMERIC,
  p_crop_type TEXT,
  p_sowing_date DATE,
  p_farmer_ref_id TEXT DEFAULT NULL,
  p_loan_ref_id TEXT DEFAULT NULL,
  p_resolution_warning BOOLEAN DEFAULT false,
  p_pilot_district TEXT DEFAULT 'faisalabad'
)
RETURNS SETOF fields
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  RETURN QUERY
  INSERT INTO fields (
    institution_id, created_by, name, boundary, area_hectares,
    crop_type, sowing_date, farmer_ref_id, loan_ref_id,
    resolution_warning, pilot_district
  ) VALUES (
    p_institution_id,
    p_created_by,
    p_name,
    ST_SetSRID(ST_GeomFromGeoJSON(p_boundary::text), 4326),
    p_area_hectares,
    p_crop_type,
    p_sowing_date,
    p_farmer_ref_id,
    p_loan_ref_id,
    p_resolution_warning,
    p_pilot_district
  )
  RETURNING *;
END;
$$;

-- Read boundary as GeoJSON for API responses
CREATE OR REPLACE FUNCTION field_boundary_geojson(p_field_id UUID)
RETURNS JSONB
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT ST_AsGeoJSON(boundary)::jsonb
  FROM fields
  WHERE id = p_field_id;
$$;

-- Update field boundary from GeoJSON
CREATE OR REPLACE FUNCTION update_field_boundary(
  p_field_id UUID,
  p_boundary JSONB,
  p_area_hectares NUMERIC,
  p_resolution_warning BOOLEAN
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  UPDATE fields
  SET
    boundary = ST_SetSRID(ST_GeomFromGeoJSON(p_boundary::text), 4326),
    area_hectares = p_area_hectares,
    resolution_warning = p_resolution_warning,
    updated_at = now()
  WHERE id = p_field_id;
END;
$$;

-- Grants for backend (service role) and registration RPC
GRANT EXECUTE ON FUNCTION create_field_from_geojson TO service_role;
GRANT EXECUTE ON FUNCTION field_boundary_geojson TO service_role;
GRANT EXECUTE ON FUNCTION update_field_boundary TO service_role;
GRANT EXECUTE ON FUNCTION register_institution TO service_role;

-- Allow authenticated users to read their institution via RLS-backed tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon;

-- Service role needs full access for backend pipeline writes
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;

-- Enable PostGIS topology not required; verify extension
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis') THEN
    RAISE EXCEPTION 'PostGIS extension is required. Enable it in Supabase Dashboard > Database > Extensions.';
  END IF;
END $$;
