import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, reportUrl } from '../lib/api';
import { getAccessToken } from '../lib/supabase';
import type { FieldDetail } from '../types';
import { FieldsMap } from '../components/FieldsMap';
import { RiskBadge } from '../components/RiskBadge';
import { VegetationChart } from '../components/VegetationChart';
import { LoadingScreen } from '../components/ui/LoadingScreen';
import { TIER_LABELS } from '../lib/constants';

export function FieldDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<FieldDetail | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) {
      api.getFieldDetail(id)
        .then(setDetail)
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false));
    }
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
      : pipelineSource === 'demo_fallback'
        ? 'Demo pipeline (configure GEE for live data)'
        : undefined;

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
        <button type="button" className="btn secondary" onClick={downloadPdf}>Export PDF</button>
      </div>

      {a && (
        <div className="risk-brief">
          <span className="eyebrow">Risk assessment</span>
          <p className="risk-brief-text">{a.explanation}</p>
          <div className="risk-meta-grid">
            <div className="risk-meta-item">
              <div className="meta-label">Z-score</div>
              <div className="meta-value">{a.z_score ?? 'N/A'}</div>
            </div>
            <div className="risk-meta-item">
              <div className="meta-label">Data source</div>
              <div className="meta-value">{a.primary_data_tier ? TIER_LABELS[a.primary_data_tier] : 'N/A'}</div>
            </div>
            <div className="risk-meta-item">
              <div className="meta-label">Rainfall</div>
              <div className="meta-value">
                {a.rainfall_mm ?? 'N/A'} mm
                {a.rainfall_anomaly_pct != null && ` (${a.rainfall_anomaly_pct.toFixed(0)}% vs avg)`}
              </div>
            </div>
            <div className="risk-meta-item">
              <div className="meta-label">Area</div>
              <div className="meta-value">{detail.area_hectares?.toFixed(2) ?? 'N/A'} ha</div>
            </div>
          </div>
        </div>
      )}

      {pipelineLabel && (
        <p className="disclaimer" style={{ marginTop: '0.5rem' }}>
          Data pipeline: {pipelineLabel}
          {detail.pipeline?.rainfall_source === 'gee_chirps' && ' · CHIRPS rainfall'}
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
          <span className="section-title">Vegetation index · season trajectory</span>
          <VegetationChart readings={detail.vegetation_readings} baseline={detail.baseline} />
        </div>
      </div>
    </>
  );
}
