import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../lib/api';
import type { Field } from '../types';
import { RiskBadge } from '../components/RiskBadge';
import { LoadingScreen } from '../components/ui/LoadingScreen';

export function FieldsListPage() {
  const [fields, setFields] = useState<Field[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listFields()
      .then(setFields)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingScreen label="Loading field portfolio…" />;

  return (
    <>
      <div className="page-header">
        <div>
          <span className="eyebrow">Portfolio</span>
          <h1>Registered fields</h1>
          <p className="page-intro">{fields.length} active field{fields.length !== 1 ? 's' : ''} under monitoring</p>
        </div>
        <Link to="/fields/new" className="btn">+ Register field</Link>
      </div>

      {error && <p className="error">{error}</p>}

      {fields.length === 0 ? (
        <div className="empty-state panel">
          <p style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', color: 'var(--ink-muted)' }}>No fields yet</p>
          <p>Register your first field boundary to begin satellite risk monitoring.</p>
          <Link to="/fields/new" className="btn" style={{ marginTop: '1.5rem' }}>Register field</Link>
        </div>
      ) : (
        <div className="panel data-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Field</th>
                <th>Crop</th>
                <th>Sowing</th>
                <th>Area</th>
                <th>Risk status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {fields.map((f) => (
                <tr key={f.id}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{f.name || f.farmer_ref_id || '—'}</div>
                    {f.loan_ref_id && <div className="text-faint" style={{ fontSize: '0.8125rem' }}>{f.loan_ref_id}</div>}
                  </td>
                  <td style={{ textTransform: 'capitalize' }}>{f.crop_type}</td>
                  <td>{f.sowing_date}</td>
                  <td>{f.area_hectares != null ? `${f.area_hectares.toFixed(2)} ha` : '—'}</td>
                  <td><RiskBadge tier={f.current_risk_tier} /></td>
                  <td className="link-cell"><Link to={`/fields/${f.id}`}>Open →</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
