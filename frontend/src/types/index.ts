export type RiskTier = 'normal' | 'watch' | 'elevated' | 'high' | 'insufficient_data';
export type DataTier = 'tier1_planet' | 'tier2_sen2sr' | 'tier3_sar';
export type UserRole = 'admin' | 'loan_officer';

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
  processing_status?: string | null;
  processing_error?: string | null;
  created_at: string;
}

export interface FieldProcessingStatus {
  field_id: string;
  status: 'idle' | 'processing' | 'ready' | 'failed' | string;
  error: string | null;
  updated_at: string | null;
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
  pipeline?: {
    vegetation_source?: string;
    tier1?: string;
    tier2?: string;
    tier3?: string;
    rainfall_source?: string;
    reading_count?: string;
    ml?: {
      stress_probability?: number;
      predicted_tier?: string;
      model_version?: string;
      class_probabilities?: Record<string, number>;
    };
  } | null;
}

export interface PortfolioSummary {
  total_fields: number;
  risk_counts: Record<string, number>;
  flagged_fields: Field[];
}

export interface Profile {
  id: string;
  institution_id: string;
  role: UserRole;
  full_name: string | null;
  email: string | null;
}

export interface TeamMember {
  id: string;
  role: UserRole;
  full_name: string | null;
  created_at: string;
}

export interface ImageryLayer {
  thumb_url: string;
  tiles: { mapid: string; token: string } | null;
}

export interface ImageryScene {
  date: string;
  cloud_pct: number;
  ndvi_mean: number | null;
  rgb: ImageryLayer;
  ndvi: ImageryLayer;
}

export interface FieldImagery {
  source: string;
  latest: ImageryScene;
  compare: ImageryScene | null;
  ndvi_delta: number | null;
  tile_url_template: string | null;
}
