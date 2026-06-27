import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import type { Field, PortfolioSummary } from '../types';
import { FieldsMap } from '../components/FieldsMap';
import { RiskBadge } from '../components/RiskBadge';
import { RISK_COLORS } from '../lib/constants';

export function DashboardPage() {
  const navigate = useNavigate();
  const [fields, setFields] = useState<Field[]>([]);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([api.listFields(), api.portfolioSummary()])
      .then(([f, s]) => { setFields(f); setSummary(s); })
      .catch((e) => setError(e.message));
  }, []);

  return (
    <>
      <div className="page-header">
        <div>
          <h2>Portfolio Dashboard</h2>
          <p style={{ color: 'var(--muted)' }}>Decision-support only — not automated loan or claims decisions.</p>
        </div>
        <Link to="/fields/new" className="btn">Register Field</Link>
      </div>

      {error && <p className="error">{error}</p>}

      {summary && (
        <div className="stat-grid">
          <div className="card stat-card"><div className="value">{summary.total_fields}</div><div className="label">Total Fields</div></div>
          {(['normal', 'watch', 'elevated', 'high'] as const).map((tier) => (
            <div className="card stat-card" key={tier}>
              <div className="value" style={{ color: RISK_COLORS[tier] }}>{summary.risk_counts[tier] ?? 0}</div>
              <div className="label">{tier}</div>
            </div>
          ))}
        </div>
      )}

      <div className="grid-2">
        <div className="card">
          <h3 style={{ marginBottom: '1rem' }}>Field Map</h3>
          <FieldsMap fields={fields} onFieldClick={(f) => navigate(`/fields/${f.id}`)} />
        </div>
        <div className="card">
          <h3 style={{ marginBottom: '1rem' }}>Flagged Fields</h3>
          {summary?.flagged_fields.length === 0 && <p style={{ color: 'var(--muted)' }}>No elevated or high-risk fields.</p>}
          <table>
            <thead><tr><th>Field</th><th>Crop</th><th>Risk</th></tr></thead>
            <tbody>
              {summary?.flagged_fields.map((f) => (
                <tr key={f.id}>
                  <td><Link to={`/fields/${f.id}`}>{f.name || f.farmer_ref_id || f.id.slice(0, 8)}</Link></td>
                  <td>{f.crop_type}</td>
                  <td><RiskBadge tier={f.current_risk_tier} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
