import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import type { Field, PortfolioSummary, RiskTier } from '../types';
import { FieldsMap } from '../components/FieldsMap';
import { RiskBadge } from '../components/RiskBadge';
import { LoadingScreen } from '../components/ui/LoadingScreen';
import { PILOT_CROP, PILOT_DISTRICT, RISK_COLORS } from '../lib/constants';

export function DashboardPage() {
  const navigate = useNavigate();
  const [fields, setFields] = useState<Field[]>([]);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.listFields(), api.portfolioSummary()])
      .then(([f, s]) => { setFields(f); setSummary(s); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingScreen label="Loading portfolio overview…" />;

  const tiers: RiskTier[] = ['normal', 'watch', 'elevated', 'high'];

  return (
    <>
      <div className="page-header">
        <div>
          <span className="eyebrow">Portfolio overview</span>
          <h1>{PILOT_CROP} · {PILOT_DISTRICT}</h1>
          <p className="page-intro">
            Satellite-derived crop risk for your registered portfolio. Use the map layers icon for Satellite (sharp) vs Sentinel-2 (crop context). Decision-support only.
          </p>
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      <section className="dashboard-hero">
        <div className="map-hero">
          <div className="map-hero-overlay">
            <span className="eyebrow">Live map</span>
            <p style={{ fontSize: '0.875rem', marginTop: '0.35rem', color: 'var(--ink-muted)' }}>
              {fields.length} field{fields.length !== 1 ? 's' : ''} · satellite basemap · zoom for parcel detail
            </p>
          </div>
          <FieldsMap
            fields={fields}
            onFieldClick={(f) => navigate(`/fields/${f.id}`)}
            className="map-container"
            minHeight={480}
            defaultBasemap="satellite"
            initialZoom={12}
            fitToFields={fields.length > 0}
            showInspector
          />
        </div>

        {summary && (
          <div className="stats-rail">
            <div className="stat-tile">
              <div className="value" style={{ color: 'var(--forest)' }}>{summary.total_fields}</div>
              <div className="label">Total fields</div>
            </div>
            {tiers.map((tier) => (
              <div className="stat-tile" key={tier}>
                <div className="value" style={{ color: RISK_COLORS[tier] }}>
                  {summary.risk_counts[tier] ?? 0}
                </div>
                <div className="label">{tier.replace('_', ' ')}</div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="flagged-section">
        <h3>Priority review</h3>
        {!summary?.flagged_fields.length ? (
          <div className="empty-state panel">
            <p style={{ fontFamily: 'var(--font-display)', fontSize: '1.125rem', color: 'var(--ink-muted)' }}>
              All clear
            </p>
            <p>No fields at elevated or high risk in the current assessment window.</p>
          </div>
        ) : (
          <div className="flagged-list">
            {summary.flagged_fields.map((f) => (
              <Link key={f.id} to={`/fields/${f.id}`} className="flagged-row" style={{ textDecoration: 'none' }}>
                <div className="flagged-row-main">
                  <div className="flagged-row-title">{f.name || f.farmer_ref_id || `Field ${f.id.slice(0, 8)}`}</div>
                  <div className="flagged-row-meta">{f.crop_type} · {f.area_hectares?.toFixed(1) ?? '—'} ha · sown {f.sowing_date}</div>
                </div>
                <RiskBadge tier={f.current_risk_tier} />
              </Link>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
