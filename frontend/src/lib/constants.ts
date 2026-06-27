import type { RiskTier } from '../types';

export const RISK_COLORS: Record<RiskTier, string> = {
  normal: '#22c55e',
  watch: '#eab308',
  elevated: '#f97316',
  high: '#ef4444',
  insufficient_data: '#94a3b8',
};

export const RISK_LABELS: Record<RiskTier, string> = {
  normal: 'Normal',
  watch: 'Watch',
  elevated: 'Elevated Risk',
  high: 'High Risk',
  insufficient_data: 'Insufficient Data',
};

export const TIER_LABELS: Record<string, string> = {
  tier1_planet: 'Tier 1 — PlanetScope',
  tier2_sen2sr: 'Tier 2 — SEN2SR',
  tier3_sar: 'Tier 3 — SAR',
};

export const PILOT_CROP = 'wheat';
export const PILOT_DISTRICT = 'Faisalabad District, Punjab';
