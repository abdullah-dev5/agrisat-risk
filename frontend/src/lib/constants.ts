import type { RiskTier } from '../types';

/** WCAG AA–friendly risk palette on light backgrounds */
export const RISK_COLORS: Record<RiskTier, string> = {
  normal: '#2F5A4A',
  watch: '#7A5C1E',
  elevated: '#9A4518',
  high: '#7A1F1F',
  insufficient_data: '#5C5854',
};

export const RISK_LABELS: Record<RiskTier, string> = {
  normal: 'Normal',
  watch: 'Watch',
  elevated: 'Elevated',
  high: 'High Risk',
  insufficient_data: 'No Data',
};

export const TIER_LABELS: Record<string, string> = {
  tier1_planet: 'PlanetScope · 3m',
  tier2_sen2sr: 'SEN2SR composite · 10m',
  tier3_sar: 'Sentinel-1 SAR',
};

export const PILOT_CROP = 'wheat';
export const PILOT_DISTRICT = 'Matiari District';
export const PILOT_DISTRICT_KEY = 'matiari';
export const PILOT_REGION = 'Sindh, Pakistan';
/** Leaflet [lat, lng] — Matiari District center */
export const PILOT_MAP_CENTER: [number, number] = [25.6, 68.45];
