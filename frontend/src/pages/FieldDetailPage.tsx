import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, reportUrl } from '../lib/api';
import { getAccessToken } from '../lib/supabase';
import type { FieldDetail, RiskAssessment } from '../types';
import { FieldsMap } from '../components/FieldsMap';
import { RiskBadge } from '../components/RiskBadge';
import { VegetationChart } from '../components/VegetationChart';
import { LoadingScreen } from '../components/ui/LoadingScreen';
import { TIER_LABELS } from '../lib/constants';

function formatZScore(z: number | null | undefined): string {
  if (z == null) return 'N/A';
  return z.toFixed(2);
}

function formatIndexValue(a: RiskAssessment | null): string {
  if (!a || a.index_value == null) return 'N/A';
  return a.index_value.toFixed(3);
}

function indexLabel(tier: string | null | undefined): string {
  return tier === 'tier3_sar' ? 'Radar index' : 'NDVI';
}

function rainfallLabel(a: RiskAssessment | null): string {
  if (!a) return 'N/A';
  if (a.rainfall_mm == null) {
    return 'Unavailable (GEE CHIRPS fetch failed or not configured)';
  }
  const base = `${a.rainfall_mm.toFixed(1)} mm this month`;
  if (a.rainfall_anomaly_pct != null) {
    return `${base} · ${a.rainfall_anomaly_pct > 0 ? '+' : ''}${a.rainfall_anomaly_pct.toFixed(0)}% vs 5-yr avg`;
  }
  return base;
}

function needsReprocess(a: RiskAssessment | null): boolean {
  if (!a?.z_score) return a?.risk_tier === 'insufficient_data';
  return Math.abs(a.z_score) > 8 || a.risk_tier === 'insufficient_data';
}

export function FieldDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<FieldDetail | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [reprocessing, setReprocessing] = useState(false);

  function loadDetail(fieldId: string) {
    setLoading(true);
    api.getFieldDetail(fieldId)
      .then(setDetail)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    if (id) loadDetail(id);
  }, [id]);

  async function downloadPdf() {
    const token = await getAccessToken();
    const res = await fetch(reportUrl(`/api/v1/reports/field/${id}/pdf`), {
      headers: { Authorization: `Bearer ${token}` },
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `field-${id}.pdf`;
    a.click();
  }

  async function handleReprocess() {
    if (!id) return;
    setReprocessing(true);
    setError('');
    try {
      await api.reprocessField(id);
      loadDetail(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Re-analysis failed');
    } finally {
      setReprocessing(false);
    }
  }

  if (loading) return <LoadingScreen label="Loading field analysis…" />;
  if (!detail) return <p className="error">{error || 'Field not found'}</p>;

  const a = detail.current_assessment;
  const latestReading = detail.vegetation_readings.length
    ? detail.vegetation_readings[detail.vegetation_readings.length - 1]
    : null;
  const mapDataLabel = latestReading
    ? `Latest acquisition · ${latestReading.acquisition_date} · ${TIER_LABELS[latestReading.data_tier] ?? latestReading.data_tier}`
    : 'Awaiting vegetation time-series';

  const pipelineSource = detail.pipeline?.vegetation_source;
  const pipelineLabel =
    pipelineSource === 'gee_live'
      ? 'Live GEE · Sentinel-1/2'
      : pipelineSource === 'gee_error'
        ? 'GEE unavailable — check backend credentials'
        : undefined;

  const isSar = a?.primary_data_tier === 'tier3_sar';
  const showReprocessHint = needsReprocess(a);

  return (
    <>
      <div className="page-header">
        <div>
          <Link to="/fields" className="back-link">← Portfolio</Link>
          <h1>{detail.name || detail.farmer_ref_id || 'Field analysis'}</h1>
          <div style={{ marginTop: '0.75rem' }}>
            <RiskBadge tier={detail.current_risk_tier} />
          </div>
        </div>
        <div className="page-header-actions">
          {showReprocessHint && (
            <button
              type="button"
              className="btn secondary"
              onClick={handleReprocess}
              disabled={reprocessing}
            >
              {reprocessing ? 'Re-analyzing…' : 'Re-analyze field'}
            </button>
          )}
          <button type="button" className="btn secondary" onClick={downloadPdf}>Export PDF</button>
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      {a && (
        <div className={`risk-brief${a.risk_tier === 'insufficient_data' ? ' risk-brief--insufficient' : ''}`}>
          <span className="eyebrow">Risk assessment</span>
          <p className="risk-brief-text">{a.explanation}</p>

          {isSar && (
            <p className="risk-brief-note">
              <strong>Radar data note:</strong> Sentinel-1 measures surface backscatter, not crop greenness.
              Cloudy seasons often force radar-only readings — compare with NDVI when optical scenes are available.
            </p>
          )}

          {showReprocessHint && (
            <p className="risk-brief-note risk-brief-note--warn">
              This score may be outdated or miscalibrated. Click <strong>Re-analyze field</strong> to refresh
              baselines and recalculate with the latest GEE data.
            </p>
          )}

          <div className="risk-meta-grid">
            <div className="risk-meta-item">
              <div className="meta-label">Z-score</div>
              <div className="meta-value">{formatZScore(a.z_score)}</div>
              <div className="meta-hint">Typical range −3 to +3</div>
            </div>
            <div className="risk-meta-item">
              <div className="meta-label">{indexLabel(a.primary_data_tier)}</div>
              <div className="meta-value">{formatIndexValue(a)}</div>
              <div className="meta-hint">
                Baseline {a.baseline_mean?.toFixed(3) ?? 'N/A'} ± {a.baseline_std?.toFixed(3) ?? 'N/A'}
              </div>
            </div>
            <div className="risk-meta-item">
              <div className="meta-label">Data source</div>
              <div className="meta-value">{a.primary_data_tier ? TIER_LABELS[a.primary_data_tier] : 'N/A'}</div>
            </div>
            <div className="risk-meta-item">
              <div className="meta-label">Rainfall</div>
              <div className="meta-value meta-value--wrap">{rainfallLabel(a)}</div>
            </div>
            <div className="risk-meta-item">
              <div className="meta-label">Area</div>
              <div className="meta-value">{detail.area_hectares?.toFixed(2) ?? 'N/A'} ha</div>
            </div>
            <div className="risk-meta-item">
              <div className="meta-label">Growth stage</div>
              <div className="meta-value">Day {a.days_since_sowing}</div>
            </div>
          </div>
        </div>
      )}

      {pipelineLabel && (
        <p className="disclaimer" style={{ marginTop: '0.5rem' }}>
          Data pipeline: {pipelineLabel}
          {detail.pipeline?.rainfall_source === 'gee_chirps' && ' · CHIRPS rainfall'}
          {detail.pipeline?.rainfall_source === 'gee_error' && ' · rainfall unavailable'}
        </p>
      )}

      <p className="disclaimer">
        Decision-support information only — not an automated loan or claims decision.
        {a?.primary_data_tier === 'tier2_sen2sr' && ' Some readings use SEN2SR AI super-resolution (model-based reconstruction, not direct observation).'}
      </p>

      <div className="grid-2" style={{ marginTop: '1.5rem' }}>
        <div className="panel">
          <div style={{ padding: '1.25rem 1.25rem 0' }}>
            <span className="section-title">Field boundary</span>
          </div>
          <FieldsMap
            fields={[detail]}
            minHeight={360}
            defaultBasemap="satellite"
            initialZoom={16}
            fitToFields
            showInspector
            dataFreshnessLabel={pipelineLabel ? `${mapDataLabel} · ${pipelineLabel}` : mapDataLabel}
          />
          {detail.resolution_warning && (
            <p className="error" style={{ padding: '1rem 1.25rem' }}>
              Area below 0.2 ha — elevated resolution uncertainty for satellite indices.
            </p>
          )}
        </div>
        <div className="card">
          <span className="section-title">
            {isSar ? 'Radar index · season trajectory' : 'Vegetation index · season trajectory'}
          </span>
          <p className="chart-caption">
            {isSar
              ? 'Orange band = 5-year SAR baseline. Shaded area = ±1 standard deviation.'
              : 'Orange line = 5-year NDVI baseline. Shaded area = ±1 standard deviation.'}
          </p>
          <VegetationChart readings={detail.vegetation_readings} baseline={detail.baseline} />
        </div>
      </div>
    </>
  );
}
