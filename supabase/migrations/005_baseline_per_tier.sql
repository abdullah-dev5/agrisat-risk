-- Allow separate optical and SAR baselines per growth stage (M7 prep)
ALTER TABLE baseline_stats
  DROP CONSTRAINT IF EXISTS baseline_stats_crop_type_pilot_district_days_since_sowing_key;

ALTER TABLE baseline_stats
  ADD CONSTRAINT baseline_stats_crop_pilot_day_tier_key
  UNIQUE (crop_type, pilot_district, days_since_sowing, primary_tier);
