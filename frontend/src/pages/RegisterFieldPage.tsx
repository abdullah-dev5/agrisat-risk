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
      setError('Draw a field boundary on the map — click at least three points.');
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
        <div>
          <span className="eyebrow">Field registration</span>
          <h1>Register a new field</h1>
          <p className="page-intro">
            Draw the AOI boundary on the map, then attach crop metadata. Pilot crop: {PILOT_CROP}.
          </p>
        </div>
      </div>

      <div className="register-layout">
        <div className="panel">
          <FieldsMap fields={[]} drawMode onPolygonComplete={setPolygon} minHeight={460} />
          <div className={`map-draw-hint ${polygon ? 'success' : ''}`}>
            {polygon
              ? '✓ Boundary captured — review and submit the form'
              : 'Click the map to place polygon vertices (minimum 3 points)'}
          </div>
        </div>

        <form className="card-elevated" onSubmit={handleSubmit} style={{ padding: '2rem' }}>
          <span className="section-title">Field metadata</span>

          <div className="form-group">
            <label>Field name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Optional display name" />
          </div>
          <div className="form-group">
            <label>Farmer reference</label>
            <input value={farmerRef} onChange={(e) => setFarmerRef(e.target.value)} placeholder="Your internal ID" />
          </div>
          <div className="form-group">
            <label>Loan / policy reference</label>
            <input value={loanRef} onChange={(e) => setLoanRef(e.target.value)} placeholder="Optional" />
          </div>
          <div className="form-group">
            <label>Sowing date</label>
            <input type="date" value={sowingDate} onChange={(e) => setSowingDate(e.target.value)} required />
          </div>

          <p className="disclaimer" style={{ marginBottom: '1.25rem' }}>
            Risk scores are decision-support information only — not automated loan or claims decisions.
          </p>

          {error && <p className="error">{error}</p>}
          <button type="submit" disabled={loading || !polygon} style={{ width: '100%' }}>
            {loading ? 'Analyzing vegetation…' : 'Register & analyze'}
          </button>
        </form>
      </div>
    </>
  );
}
