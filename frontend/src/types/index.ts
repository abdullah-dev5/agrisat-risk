export type RiskTier = 'normal' | 'watch' | 'elevated' | 'high' | 'insufficient_data';
export type DataTier = 'tier1_planet' | 'tier2_sen2sr' | 'tier3_sar';

export interface Field {
  id: string;
  institution_id: string;
  name: string | null;
  boundary_geojson: GeoJSON.Polygon;
  area_hectares: number | null;
  crop_type: string;
  sowing_date: string;
  farmer_ref_id: string | null;
  loan_ref_id: string | null;
  status: string;
  resolution_warning: boolean;
  pilot_district: string;
  current_risk_tier: RiskTier | null;
  created_at: string;
}

export interface VegetationReading {
  acquisition_date: string;
  days_since_sowing: number;
  data_tier: DataTier;
  ndvi: number | null;
  evi: number | null;
  sar_index: number | null;
  cloud_fraction: number | null;
  is_fused: boolean;
}

export interface BaselinePoint {
  days_since_sowing: number;
  mean_index: number;
  std_index: number;
}

export interface RiskAssessment {
  id: string;
  field_id: string;
  assessed_at: string;
  days_since_sowing: number;
  z_score: number | null;
  risk_tier: RiskTier;
  primary_data_tier: DataTier | null;
  index_value: number | null;
  baseline_mean: number | null;
  baseline_std: number | null;
  rainfall_mm: number | null;
  rainfall_anomaly_pct: number | null;
  explanation: string;
}

export interface FieldDetail extends Field {
  vegetation_readings: VegetationReading[];
  baseline: BaselinePoint[];
  current_assessment: RiskAssessment | null;
}

export interface PortfolioSummary {
  total_fields: number;
  risk_counts: Record<string, number>;
  flagged_fields: Field[];
}

export interface Profile {
  id: string;
  institution_id: string;
  role: 'admin' | 'loan_officer';
  full_name: string | null;
  email: string | null;
}
