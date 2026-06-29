-- Run this AFTER 001 succeeds and 002 fails (Supabase PostGIS fix + remaining grants)
-- Safe to re-run: uses CREATE OR REPLACE

-- ─── Geometry RPCs (extensions schema on Supabase) ───

CREATE OR REPLACE FUNCTION public.create_field_from_geojson(
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
RETURNS SETOF public.fields
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
BEGIN
  RETURN QUERY
  INSERT INTO public.fields (
    institution_id, created_by, name, boundary, area_hectares,
    crop_type, sowing_date, farmer_ref_id, loan_ref_id,
    resolution_warning, pilot_district
  ) VALUES (
    p_institution_id,
    p_created_by,
    p_name,
    extensions.ST_SetSRID(extensions.ST_GeomFromGeoJSON(p_boundary::text), 4326),
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

CREATE OR REPLACE FUNCTION public.field_boundary_geojson(p_field_id UUID)
RETURNS JSONB
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, extensions
AS $$
  SELECT extensions.ST_AsGeoJSON(boundary)::jsonb
  FROM public.fields
  WHERE id = p_field_id;
$$;

CREATE OR REPLACE FUNCTION public.update_field_boundary(
  p_field_id UUID,
  p_boundary JSONB,
  p_area_hectares NUMERIC,
  p_resolution_warning BOOLEAN
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
BEGIN
  UPDATE public.fields
  SET
    boundary = extensions.ST_SetSRID(extensions.ST_GeomFromGeoJSON(p_boundary::text), 4326),
    area_hectares = p_area_hectares,
    resolution_warning = p_resolution_warning,
    updated_at = now()
  WHERE id = p_field_id;
END;
$$;

-- ─── Grants (may not have run if 002 failed mid-file) ───

GRANT EXECUTE ON FUNCTION public.create_field_from_geojson(
  UUID, UUID, TEXT, JSONB, NUMERIC, TEXT, DATE, TEXT, TEXT, BOOLEAN, TEXT
) TO service_role;

GRANT EXECUTE ON FUNCTION public.field_boundary_geojson(UUID) TO service_role;

GRANT EXECUTE ON FUNCTION public.update_field_boundary(UUID, JSONB, NUMERIC, BOOLEAN) TO service_role;

GRANT EXECUTE ON FUNCTION public.register_institution(TEXT, TEXT, UUID, TEXT, TEXT) TO service_role;

GRANT SELECT ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon;
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;

-- ─── Verify ───

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis') THEN
    RAISE EXCEPTION 'Enable PostGIS: Database → Extensions → postgis';
  END IF;
END $$;

SELECT '003 applied — geometry RPCs ready' AS status;
