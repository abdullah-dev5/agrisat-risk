import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, reportUrl } from '../lib/api';
import { getAccessToken } from '../lib/supabase';
import type { FieldDetail } from '../types';
import { FieldsMap } from '../components/FieldsMap';
import { RiskBadge } from '../components/RiskBadge';
import { VegetationChart } from '../components/VegetationChart';
import { TIER_LABELS } from '../lib/constants';

export function FieldDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<FieldDetail | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (id) api.getFieldDetail(id).then(setDetail).catch((e) => setError(e.message));
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

  if (!detail) return <p>{error || 'Loading...'}</p>;

  const a = detail.current_assessment;

  return (
    <>
      <div className="page-header">
        <div>
          <Link to="/fields" style={{ fontSize: '0.85rem' }}>← Back to fields</Link>
          <h2>{detail.name || detail.farmer_ref_id || 'Field Detail'}</h2>
          <RiskBadge tier={detail.current_risk_tier} />
        </div>
        <button onClick={downloadPdf}>Export PDF</button>
      </div>

      <p className="disclaimer">
        Decision-support information only — not an automated loan or claims decision.
        {a?.primary_data_tier === 'tier2_sen2sr' && ' Some readings use SEN2SR AI super-resolution (model-based reconstruction).'}
      </p>

      {a && (
        <div className="card" style={{ marginBottom: '1rem' }}>
          <h3 style={{ marginBottom: '0.5rem' }}>Risk Explanation</h3>
          <p>{a.explanation}</p>
          <div style={{ marginTop: '0.75rem', fontSize: '0.85rem', color: 'var(--muted)' }}>
            Z-score: {a.z_score ?? 'N/A'} · Data tier: {a.primary_data_tier ? TIER_LABELS[a.primary_data_tier] : 'N/A'}
            · Rainfall: {a.rainfall_mm ?? 'N/A'} mm ({a.rainfall_anomaly_pct?.toFixed(0) ?? 'N/A'}% vs historical)
          </div>
        </div>
      )}

      <div className="grid-2">
        <div className="card">
          <h3 style={{ marginBottom: '1rem' }}>Field Boundary</h3>
          <FieldsMap fields={[detail]} />
          {detail.resolution_warning && (
            <p className="error" style={{ marginTop: '0.75rem' }}>
              Field area is below 0.2 ha — elevated resolution-related uncertainty (FR-2.5).
            </p>
          )}
        </div>
        <div className="card">
          <h3 style={{ marginBottom: '1rem' }}>Vegetation Index Time Series</h3>
          <VegetationChart readings={detail.vegetation_readings} baseline={detail.baseline} />
        </div>
      </div>
    </>
  );
}
