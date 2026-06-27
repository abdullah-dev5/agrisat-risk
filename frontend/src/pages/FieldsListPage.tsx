import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../lib/api';
import type { Field } from '../types';
import { RiskBadge } from '../components/RiskBadge';

export function FieldsListPage() {
  const [fields, setFields] = useState<Field[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    api.listFields().then(setFields).catch((e) => setError(e.message));
  }, []);

  return (
    <>
      <div className="page-header">
        <h2>Registered Fields</h2>
        <Link to="/fields/new" className="btn">Register Field</Link>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Name / Ref</th>
              <th>Crop</th>
              <th>Sowing</th>
              <th>Area (ha)</th>
              <th>Risk</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {fields.map((f) => (
              <tr key={f.id}>
                <td>{f.name || f.farmer_ref_id || '—'}</td>
                <td>{f.crop_type}</td>
                <td>{f.sowing_date}</td>
                <td>{f.area_hectares?.toFixed(2) ?? '—'}</td>
                <td><RiskBadge tier={f.current_risk_tier} /></td>
                <td><Link to={`/fields/${f.id}`}>View</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
