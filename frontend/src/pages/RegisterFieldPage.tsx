import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import { FieldsMap } from '../components/FieldsMap';
import { PILOT_CROP } from '../lib/constants';

export function RegisterFieldPage() {
  const navigate = useNavigate();
  const [polygon, setPolygon] = useState<GeoJSON.Polygon | null>(null);
  const [name, setName] = useState('');
  const [farmerRef, setFarmerRef] = useState('');
  const [loanRef, setLoanRef] = useState('');
  const [sowingDate, setSowingDate] = useState('2025-11-15');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!polygon) {
      setError('Draw a field boundary on the map (click 3+ points).');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const field = await api.createField({
        name: name || null,
        boundary_geojson: polygon,
        crop_type: PILOT_CROP,
        sowing_date: sowingDate,
        farmer_ref_id: farmerRef || null,
        loan_ref_id: loanRef || null,
      });
      navigate(`/fields/${field.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to register field');
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <h2>Register Field</h2>
      </div>

      <p className="disclaimer">
        Click on the map to draw a polygon boundary (minimum 3 clicks). Pilot crop: {PILOT_CROP}.
      </p>

      <div className="grid-2">
        <div className="card">
          <FieldsMap fields={[]} drawMode onPolygonComplete={setPolygon} />
          {polygon && <p style={{ marginTop: '0.5rem', color: 'var(--accent)' }}>Boundary captured ✓</p>}
        </div>

        <form className="card" onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Field name (optional)</label>
            <input value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Farmer reference ID (optional)</label>
            <input value={farmerRef} onChange={(e) => setFarmerRef(e.target.value)} placeholder="Institution internal ID" />
          </div>
          <div className="form-group">
            <label>Loan / policy reference (optional)</label>
            <input value={loanRef} onChange={(e) => setLoanRef(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Sowing date *</label>
            <input type="date" value={sowingDate} onChange={(e) => setSowingDate(e.target.value)} required />
          </div>
          {error && <p className="error">{error}</p>}
          <button type="submit" disabled={loading}>{loading ? 'Processing...' : 'Register & Analyze'}</button>
        </form>
      </div>
    </>
  );
}
