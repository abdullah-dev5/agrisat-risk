import { PILOT_CROP, PILOT_DISTRICT, PILOT_REGION, RISK_LABELS, TIER_LABELS } from '../lib/constants';

export type GuideBlock = {
  heading?: string;
  plain?: string;
  technical?: string;
  bullets?: { plain?: string; technical?: string; label: string }[];
};

export type GuideSection = {
  id: string;
  title: string;
  summary: string;
  blocks: GuideBlock[];
};

export type GlossaryTerm = {
  term: string;
  plain: string;
  technical: string;
};

export const GUIDE_SECTIONS: GuideSection[] = [
  {
    id: 'overview',
    title: 'What AgriSat Risk does',
    summary: 'Decision-support for lenders and insurers — not automated payout.',
    blocks: [
      {
        plain:
          `AgriSat Risk monitors ${PILOT_CROP} fields in ${PILOT_DISTRICT}, ${PILOT_REGION} using satellite imagery. ` +
          'It compares how green and healthy a crop looks today against what is normal for that same growth stage in past seasons. ' +
          'When vegetation falls well below normal — especially if rainfall is also low — the field may be flagged for review.',
        technical:
          'B2B parametric crop-risk platform (SRS v2.0). Ingests AOI polygons, runs a three-tier satellite fusion pipeline via Google Earth Engine, ' +
          'persists vegetation time-series, compares latest index to district/crop baseline using z-scores, and surfaces risk tiers with audit payloads.',
      },
      {
        heading: 'What it is good for',
        bullets: [
          {
            label: 'Early stress signals',
            plain: 'Spot fields that may be underperforming before ground visits.',
            technical: 'Negative z-scores on NDVI/SAR with optional CHIRPS rainfall anomaly cross-check.',
          },
          {
            label: 'Portfolio oversight',
            plain: 'See risk counts across all registered fields on one dashboard.',
            technical: 'Institution-scoped RLS; portfolio summary + CSV/PDF export.',
          },
          {
            label: 'Explainable flags',
            plain: 'Each flag includes a plain-English sentence about how far below or above normal the crop is.',
            technical: 'RiskResult.explanation + risk_audit_log pipeline payload for reproducibility.',
          },
        ],
      },
      {
        heading: 'What it is not',
        plain:
          'This is decision-support only. It does not approve or deny loans, trigger insurance payouts, or replace agronomist inspection. ' +
          'Cloud cover, mixed crops inside a polygon, or bad boundary drawing can all affect readings.',
      },
    ],
  },
  {
    id: 'how-it-works',
    title: 'End-to-end flow',
    summary: 'From field registration to risk flag on your dashboard.',
    blocks: [
      {
        plain:
          'You draw the field boundary on the map and enter crop type and sowing date. The system pulls satellite scenes, ' +
          'builds a vegetation timeline, compares the latest reading to the historical baseline, and assigns a risk level.',
        technical:
          'POST /fields → create_field_from_geojson RPC → process_field() → select_and_fuse(WKT, sowing_date) → ' +
          'ensure_district_baseline() → assess_risk() → risk_assessments + risk_audit_log.',
      },
      {
        heading: 'Pipeline steps',
        bullets: [
          { label: '1 · Register', plain: 'Draw AOI, set sowing date.', technical: 'PostGIS geometry + area validation (0.2–500 ha).' },
          { label: '2 · Acquire', plain: 'Satellite data is fetched for your polygon.', technical: 'GEE: Sentinel-2, Sentinel-1, CHIRPS; optional SEN2SR composite.' },
          { label: '3 · Fuse', plain: 'Best available source is chosen when clouds block the view.', technical: 'Tier priority: Planet → SEN2SR → SAR+optical fusion.' },
          { label: '4 · Baseline', plain: 'Your reading is compared to multi-year district norms.', technical: 'baseline_stats keyed by crop, district, days_since_sowing, index family.' },
          { label: '5 · Score', plain: 'A risk badge (Normal → High) appears on the field.', technical: 'z = (index − μ) / σ; thresholds at |z| ≥ 1.0 / 1.5 / 2.0.' },
        ],
      },
    ],
  },
  {
    id: 'satellite-tiers',
    title: 'Satellite data tiers',
    summary: 'Three layers of imagery — best available wins.',
    blocks: [
      {
        plain:
          'The platform tries higher-resolution optical imagery first. If clouds block the view, it falls back to radar and lower-resolution optical data. ' +
          'Core risk monitoring still works on Tier 3 alone.',
        technical:
          'FR-3.4 tier adapters: tier1_planet (PlanetScope E&R), tier2_sen2sr (weekly cloud-masked S2 composites), tier3_sar (S1 VH/VV + S2 + CHIRPS).',
      },
      {
        heading: 'Tier reference',
        bullets: [
          {
            label: TIER_LABELS.tier1_planet,
            plain: 'Sharpest view (3 m) when licensed — preferred for small plots.',
            technical: 'PlanetScope E&R program; not active in MVP until license confirmed.',
          },
          {
            label: TIER_LABELS.tier2_sen2sr,
            plain: 'Enhanced Sentinel-2 via local super-resolution model on GEE patches; falls back to weekly GEE composites.',
            technical: 'sen2sr_local.py + Sen2srNet (PyTorch); fallback fetch_tier2_composite_from_gee().',
          },
          {
            label: TIER_LABELS.tier3_sar,
            plain: 'Always available — radar sees through clouds; combined with optical when possible.',
            technical: 'Sentinel-1 GRD backscatter index + Sentinel-2 NDVI/EVI + CHIRPS rainfall anomaly.',
          },
        ],
      },
    ],
  },
  {
    id: 'vegetation',
    title: 'Vegetation & greenness',
    summary: 'What we measure and what “healthy” looks like.',
    blocks: [
      {
        plain:
          'For optical satellites, “greenness” is measured with NDVI (Normalized Difference Vegetation Index). ' +
          'Healthy wheat mid-season typically shows moderate-to-high NDVI (roughly 0.35–0.75 depending on stage). ' +
          'Very low values near peak growth often mean bare soil, stress, or harvest — context matters.',
        technical:
          'NDVI = (NIR − Red) / (NIR + Red) from Sentinel-2 B8/B4. EVI computed in parallel. ' +
          'Tier 3 SAR uses VH/VV backscatter-derived index (different scale — not directly comparable to NDVI).',
      },
      {
        heading: 'What a good reading contains',
        bullets: [
          {
            label: 'Acquisition date',
            plain: 'When the satellite passed over — shown on charts and the map inspector.',
            technical: 'vegetation_readings.acquisition_date; fused flag when multiple tiers merged.',
          },
          {
            label: 'Index value',
            plain: 'A single number summarizing crop greenness (or radar response for SAR).',
            technical: 'ndvi / evi / sar_index stored per tier; fusion picks primary_data_tier.',
          },
          {
            label: 'Cloud fraction',
            plain: 'How much of the scene was cloudy — high clouds reduce trust in optical data.',
            technical: 'cloud_fraction from S2 QA60 / scene metadata; drives tier fallback.',
          },
          {
            label: 'Days since sowing',
            plain: 'Growth stage anchor — wheat in week 8 is compared to week 8 in past years, not week 16.',
            technical: '(acquisition_date − sowing_date).days → baseline lookup key.',
          },
        ],
      },
      {
        heading: 'Live imagery panel',
        plain:
          'On the field detail page, RGB and NDVI previews show the latest clear scene and a comparison scene ~2 weeks earlier. ' +
          'Loading can take 15–120 seconds because imagery is computed on demand from Google Earth Engine.',
        technical:
          'GET /fields/{id}/imagery → gee_imagery.py sampleRectangle + Pillow PNG (base64); 10-minute server cache.',
      },
    ],
  },
  {
    id: 'baseline',
    title: 'Historical baseline',
    summary: 'The “normal” curve your field is judged against.',
    blocks: [
      {
        plain:
          'The baseline is the expected vegetation level for wheat at each day after sowing in Matiari District, built from several past growing seasons. ' +
          'If today’s NDVI sits near the baseline line on the chart, the crop is on track. If it sits well below, the system flags stress.',
        technical:
          'District-level baseline_stats: for each days_since_sowing, store mean_index (μ) and std_index (σ) from 5-year GEE historical samples. ' +
          'Tier-specific families (optical vs SAR) kept separate — mixing them yields insufficient_data.',
      },
      {
        heading: 'How the baseline is built',
        plain:
          'Satellite history across the district is sampled for the same crop calendar each year. Values are averaged for each day-after-sowing window.',
        technical:
          'build_gee_baseline() / build_district_baseline.py: iterate sowing_year − 1…−5, fetch tier3 (+ optional tier2 optical), aggregate by days_since_sowing, apply effective_std floor.',
      },
      {
        heading: 'What good baseline coverage looks like',
        bullets: [
          {
            label: 'Enough sample years',
            plain: 'At least several years of history so “normal” is stable.',
            technical: 'BASELINE_MIN_ROWS = 5; sample_years default 5.',
          },
          {
            label: 'Matching index family',
            plain: 'Optical baseline for optical readings; radar baseline for radar readings.',
            technical: 'index_family_for_tier() must match between baseline.primary_tier and reading.data_tier.',
          },
          {
            label: 'Fresh district stats',
            plain: 'Baselines are refreshed periodically so climate shifts are reflected.',
            technical: 'BASELINE_MAX_AGE_DAYS = 30; ensure_district_baseline() on process.',
          },
        ],
      },
      {
        heading: 'Reading the baseline chart',
        plain:
          'The shaded band on the field detail chart is the normal range (mean ± spread). Your actual readings are the line. ' +
          'Persistent readings below the band — not a single cloudy day — are what drive risk flags.',
      },
    ],
  },
  {
    id: 'risk-scoring',
    title: 'Risk scoring & flags',
    summary: 'How Normal, Watch, Elevated, and High are assigned.',
    blocks: [
      {
        plain:
          'The system computes how many standard deviations today’s reading is from the baseline (the z-score). ' +
          'Moderate negative z-scores mean “watch”; larger ones mean “elevated” or “high”. Positive z-scores (unusually lush) are also tracked but rarely trigger lending concern.',
        technical:
          'z = (index_value − mean_index) / effective_std(mean, std). Classify |z| against risk_threshold_watch=1.0, elevated=1.5, high=2.0.',
      },
      {
        heading: 'Risk tiers',
        bullets: [
          { label: RISK_LABELS.normal, plain: 'Within expected range for this growth stage.', technical: '|z| < 1.0' },
          { label: RISK_LABELS.watch, plain: 'Mildly below (or above) normal — monitor.', technical: '1.0 ≤ |z| < 1.5' },
          { label: RISK_LABELS.elevated, plain: 'Clear departure from baseline — review recommended.', technical: '1.5 ≤ |z| < 2.0' },
          { label: RISK_LABELS.high, plain: 'Strong anomaly — priority review.', technical: '|z| ≥ 2.0' },
          { label: RISK_LABELS.insufficient_data, plain: 'Not enough data to score — manual check.', technical: 'No readings, baseline mismatch, or |z| > 8 (data quality guard).' },
        ],
      },
      {
        heading: 'Extreme z-score guard',
        plain:
          'If the math says the crop is impossibly far from normal (|z| > 8), the system shows “No Data” instead of a false alarm — usually a boundary, calibration, or tier mismatch issue.',
        technical:
          'assess_risk() returns INSUFFICIENT_DATA with reason extreme_z_score; user should re-process after baseline refresh.',
      },
    ],
  },
  {
    id: 'ml-layer',
    title: 'ML stress model (M12)',
    summary: 'Gradient-boosted classifier augments z-score rules.',
    blocks: [
      {
        plain:
          'After the z-score assigns a risk tier, a machine-learning model reviews the same field context — growth stage, vegetation level, rainfall, and recent trend. ' +
          'It estimates a crop-stress probability. The z-score tier stays primary for explainability; ML can only elevate the tier when it strongly agrees.',
        technical:
          'sklearn GradientBoostingClassifier on 10 features (days_since_sowing, index, baseline μ/σ, z, rainfall, SAR flag, NDVI trend, reading count). ' +
          'apply_ml_overlay() in ml_risk.py; audit payload key ml.',
      },
      {
        heading: 'Training & deployment',
        bullets: [
          {
            label: 'Bootstrap',
            plain: 'Run the bootstrap script once after clone to create starter models.',
            technical: 'python scripts/bootstrap_ml_models.py → models/ml_risk/model.joblib',
          },
          {
            label: 'Retrain from portfolio',
            plain: 'As you accumulate assessed fields, retrain on real outcomes.',
            technical: 'python scripts/train_ml_risk_model.py --from-db (≥50 assessments)',
          },
          {
            label: 'Health check',
            plain: 'Backend /health/ml shows whether the model is loaded.',
            technical: 'ML_RISK_ENABLED, ML_RISK_ELEVATE_ONLY, ML_RISK_CONFIDENCE_MIN in .env',
          },
        ],
      },
    ],
  },
  {
    id: 'rainfall',
    title: 'Rainfall cross-check',
    summary: 'CHIRPS rainfall adds context to vegetation stress.',
    blocks: [
      {
        plain:
          'Monthly rainfall for the field area is compared to the five-year average. If vegetation is low and rainfall was also well below normal, drought stress is more plausible. ' +
          'If rainfall was high but NDVI is still low, other factors (pest, heat, planting issue) may be involved.',
        technical:
          'CHIRPS via GEE; rainfall_mm and rainfall_anomaly_pct stored on risk_assessments. Narrative appended when anomaly < −20% or > +20%.',
      },
    ],
  },
  {
    id: 'using-the-app',
    title: 'Using the dashboard',
    summary: 'Where to find each piece of information.',
    blocks: [
      {
        heading: 'Overview',
        plain: 'Portfolio map, risk count summary, and quick access to flagged fields.',
        technical: 'GET /fields + GET /reports/portfolio/summary',
      },
      {
        heading: 'Portfolio',
        plain: 'Table or card list of all fields with risk badges; export CSV or PDF.',
      },
      {
        heading: 'Field detail',
        plain: 'Risk explanation, z-score, vegetation chart with baseline band, satellite previews, and re-process button.',
        technical: 'GET /fields/{id}/detail + GET /fields/{id}/imagery',
      },
      {
        heading: 'Register field',
        plain: 'Draw polygon on map; minimum ~0.2 ha recommended; enter sowing date for wheat. Switch basemaps with the stack icon (top-right of the map) — Satellite for sharp boundary tracing, Map for confirming which town/village a field is actually near, Sentinel-2 or Hybrid for crop context, Street for a district overview.',
      },
      {
        heading: 'Team (admins)',
        plain: 'Invite loan officers to your institution.',
        technical: 'POST /auth/invite → Supabase admin.create_user + profiles row',
      },
    ],
  },
  {
    id: 'data-quality',
    title: 'Data quality tips',
    summary: 'Get trustworthy readings from your boundaries.',
    blocks: [
      {
        bullets: [
          {
            label: 'Draw tight boundaries',
            plain: 'Include only the target field — roads, trees, and water inside the polygon dilute the signal.',
            technical: 'Mixed land cover lowers NDVI variance; prefer single-crop AOI.',
          },
          {
            label: 'Correct sowing date',
            plain: 'Wrong date compares your crop to the wrong growth stage baseline.',
            technical: 'days_since_sowing drives baseline row selection via pick_baseline_row().',
          },
          {
            label: 'Re-process after edits',
            plain: 'If you fix the boundary or sowing date, use Re-analyze on the field page.',
            technical: 'PATCH /fields → process_field() or POST /fields/{id}/reprocess',
          },
          {
            label: 'Interpret SAR carefully',
            plain: 'Radar measures moisture and surface roughness — useful in cloudy seasons but not identical to NDVI.',
            technical: 'Tier 3 SAR explanation appended in assess_risk() when primary_data_tier is tier3_sar.',
          },
          {
            label: 'Confirm the location before trusting a flag',
            plain: 'Switch to the Map layer and check the field actually sits where you expect — a boundary accidentally drawn over a river, road, or the wrong parcel will show a real anomaly, just not a crop one.',
            technical: 'Field boundary validation is geometric only (Polygon type + area threshold) — there is no automated land-cover check, so a mis-drawn AOI over non-cropland still produces a statistically valid but agronomically meaningless z-score.',
          },
        ],
      },
    ],
  },
];

export const GLOSSARY: GlossaryTerm[] = [
  {
    term: 'NDVI',
    plain: 'Vegetation greenness index from 0 to 1 — higher usually means more active crop canopy.',
    technical: '(NIR − Red) / (NIR + Red); Sentinel-2 bands B8 and B4.',
  },
  {
    term: 'EVI',
    plain: 'Alternative greenness index that handles bright soil better in sparse crops.',
    technical: 'Enhanced Vegetation Index; stored alongside NDVI in vegetation_readings.',
  },
  {
    term: 'Z-score',
    plain: 'How far today’s reading is from “normal”, in standard-deviation units. −2 means notably below normal.',
    technical: '(x − μ) / σ using baseline mean_index and effective_std-adjusted std_index.',
  },
  {
    term: 'Baseline',
    plain: 'Historical average vegetation curve for wheat at each day after sowing in the pilot district.',
    technical: 'baseline_stats table; district + crop + days_since_sowing + tier family.',
  },
  {
    term: 'AOI',
    plain: 'Area of interest — the field polygon you draw on the map.',
    technical: 'GeoJSON Polygon stored as PostGIS geometry via create_field_from_geojson RPC.',
  },
  {
    term: 'SAR',
    plain: 'Satellite radar that works through clouds — measures surface moisture and structure.',
    technical: 'Sentinel-1 C-band VH/VV backscatter; tier3_sar index family.',
  },
  {
    term: 'CHIRPS',
    plain: 'Global rainfall dataset used to check if dry weather supports a vegetation stress flag.',
    technical: 'Climate Hazards Group InfraRed Precipitation with Station data; monthly sum vs 5-yr mean.',
  },
  {
    term: 'Fusion',
    plain: 'Combining the best available satellite sources into one timeline.',
    technical: 'select_and_fuse() tier priority with FusedReading records and pipeline audit payload.',
  },
  {
    term: 'SEN2SR',
    plain: 'AI-enhanced Sentinel-2 imagery — local PyTorch model super-resolves GEE reflectance patches for sharper NDVI.',
    technical: 'Sen2srNet 2× upscale; weights at models/sen2sr/model.pt; train via scripts/train_sen2sr_local.py.',
  },
  {
    term: 'GEE',
    plain: 'Google Earth Engine — cloud platform where satellite analysis runs.',
    technical: 'earthengine-api service account; required for live processing and imagery previews.',
  },
  {
    term: 'RLS',
    plain: 'Row-level security — your institution only sees its own fields.',
    technical: 'Supabase RLS + API institution_id filter on all field queries.',
  },
];
