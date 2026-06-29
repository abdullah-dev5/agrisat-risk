import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import { parseBoundaryFile } from '../lib/boundaryParser';
import { FieldsMap } from '../components/FieldsMap';
import { PILOT_CROP, PILOT_DISTRICT_KEY } from '../lib/constants';

type InputMode = 'draw' | 'upload';

export function RegisterFieldPage() {
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const [inputMode, setInputMode] = useState<InputMode>('draw');
  const [polygon, setPolygon] = useState<GeoJSON.Polygon | null>(null);
  const [uploadName, setUploadName] = useState('');
  const [name, setName] = useState('');
  const [farmerRef, setFarmerRef] = useState('');
  const [loanRef, setLoanRef] = useState('');
  const [sowingDate, setSowingDate] = useState('2025-11-15');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError('');
    try {
      const parsed = await parseBoundaryFile(file);
      setPolygon(parsed);
      setUploadName(file.name);
      setInputMode('upload');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not parse boundary file');
      setPolygon(null);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!polygon) {
      setError('Draw on the map or upload a GeoJSON / KML / coordinate file.');
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
            Draw on the map or upload a boundary file (GeoJSON, KML, or coordinate list). Pilot crop: {PILOT_CROP}.
          </p>
        </div>
      </div>

      <div className="register-layout">
        <div className="panel">
          <div className="boundary-tabs">
            <button
              type="button"
              className={inputMode === 'draw' ? 'tab active' : 'tab'}
              onClick={() => { setInputMode('draw'); setPolygon(null); setUploadName(''); }}
            >
              Draw on map
            </button>
            <button
              type="button"
              className={inputMode === 'upload' ? 'tab active' : 'tab'}
              onClick={() => fileRef.current?.click()}
            >
              Upload file
            </button>
            <input
              ref={fileRef}
              type="file"
              accept=".geojson,.json,.kml,.txt,.csv"
              hidden
              onChange={handleFileChange}
            />
          </div>

          {inputMode === 'draw' ? (
            <FieldsMap
              fields={[]}
              drawMode
              committedPolygon={polygon}
              onPolygonComplete={setPolygon}
              minHeight={420}
            />
          ) : (
            <FieldsMap
              fields={polygon ? [{
                id: 'preview',
                institution_id: '',
                name: 'Preview',
                boundary_geojson: polygon,
                area_hectares: null,
                crop_type: PILOT_CROP,
                sowing_date: sowingDate,
                farmer_ref_id: null,
                loan_ref_id: null,
                status: 'active',
                resolution_warning: false,
                pilot_district: PILOT_DISTRICT_KEY,
                current_risk_tier: 'normal',
                created_at: '',
              }] : []}
              minHeight={420}
            />
          )}

          <div className={`map-draw-hint ${polygon ? 'success' : ''}`}>
            {polygon
              ? `✓ Boundary ready${uploadName ? ` — ${uploadName}` : ''}`
              : inputMode === 'draw'
                ? 'Use the pencil tool, place at least 3 points, then click Finish'
                : 'Upload .geojson, .kml, or .txt coordinate list (lng, lat per line)'}
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
