-- Pilot district: Matiari (Sindh)
-- Safe to re-run

ALTER TABLE public.fields
  ALTER COLUMN pilot_district SET DEFAULT 'matiari';

SELECT '004 applied — pilot district default is matiari' AS status;
