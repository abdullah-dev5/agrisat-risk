import type { RiskTier } from '../types';

/** Refined risk palette — institutional, not neon dashboard defaults */
export const RISK_COLORS: Record<RiskTier, string> = {
  normal: '#3D6B5A',
  watch: '#B8954A',
  elevated: '#C4652E',
  high: '#9B2C2C',
  insufficient_data: '#8A8580',
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
  tier2_sen2sr: 'SEN2SR · 2.5m',
  tier3_sar: 'Sentinel-1 SAR',
};

export const PILOT_CROP = 'wheat';
export const PILOT_DISTRICT = 'Matiari District';
export const PILOT_DISTRICT_KEY = 'matiari';
export const PILOT_REGION = 'Sindh, Pakistan';
/** Leaflet [lat, lng] — Matiari District center */
export const PILOT_MAP_CENTER: [number, number] = [25.6, 68.45];

export const MAP_TILE_URL = 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png';
export const MAP_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>';
