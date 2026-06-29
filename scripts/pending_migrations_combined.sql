-- Run in Supabase SQL Editor if scripts/apply_pending_migrations.py cannot connect
-- Safe to re-run (005 ignores duplicate constraint errors)

ALTER TABLE public.fields
  ALTER COLUMN pilot_district SET DEFAULT 'matiari';

ALTER TABLE baseline_stats
  DROP CONSTRAINT IF EXISTS baseline_stats_crop_type_pilot_district_days_since_sowing_key;

ALTER TABLE baseline_stats
  DROP CONSTRAINT IF EXISTS baseline_stats_crop_pilot_day_tier_key;

ALTER TABLE baseline_stats
  ADD CONSTRAINT baseline_stats_crop_pilot_day_tier_key
  UNIQUE (crop_type, pilot_district, days_since_sowing, primary_tier);
