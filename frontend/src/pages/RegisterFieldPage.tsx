import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import { parseBoundaryFile } from '../lib/boundaryParser';
import { FieldsMap } from '../components/FieldsMap';
import { SubmitOverlay } from '../components/ui/SubmitOverlay';
import { PILOT_CROP, PILOT_DISTRICT, PILOT_DISTRICT_KEY } from '../lib/constants';

type InputMode = 'draw' | 'upload';

const REGISTRATION_STEPS = [
  { id: 1, label: 'Define boundary', hint: 'Draw on map or upload a file' },
  { id: 2, label: 'Field details', hint: 'Name, sowing date, references' },
  { id: 3, label: 'Analyze', hint: 'GEE vegetation + risk score' },
] as const;

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
  const [showLayerHelp, setShowLayerHelp] = useState(false);

  const currentStep = !polygon ? 1 : loading ? 3 : 2;

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
      // The field now exists server-side the moment createField() resolves.
      // Hand off to the field detail page immediately rather than waiting here
      // for satellite processing to finish — that page already polls
      // /fields/{id}/processing and shows in-progress/failed states. Waiting
      // on this page risked a timeout leaving the user stuck on a generic
      // error with no link back to a field that had already been created,
      // inviting an accidental duplicate submission.
      navigate(`/fields/${field.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to register field');
      setLoading(false);
    }
  }

  return (
    <>
      {loading && (
        <SubmitOverlay
          title="Registering field…"
          message="Saving boundary and queuing satellite analysis."
          steps={[
            'Saving field boundary to database',
            'Queued: Sentinel-2 NDVI + Sentinel-1 SAR (Google Earth Engine)',
            'Computing baseline comparison and risk tier',
          ]}
        />
      )}

      <div className="page-header">
        <div>
          <span className="eyebrow">Field registration · {PILOT_DISTRICT}</span>
          <h1>Register a new field</h1>
          <p className="page-intro">
            Step {currentStep} of 3 — draw a boundary on <strong>Satellite</strong> imagery (sharp), then complete the form.
            Sentinel-2 layer is for crop context only (~10 m, slower to load).
          </p>
        </div>
      </div>

      <ol className="register-steps" aria-label="Registration progress">
        {REGISTRATION_STEPS.map((step) => (
          <li
            key={step.id}
            className={`register-step${currentStep === step.id ? ' register-step--active' : ''}${currentStep > step.id ? ' register-step--done' : ''}`}
          >
            <span className="register-step-num">{currentStep > step.id ? '✓' : step.id}</span>
            <span className="register-step-text">
              <strong>{step.label}</strong>
              <span>{step.hint}</span>
            </span>
          </li>
        ))}
      </ol>

      <div className="register-layout">
        <div className="panel">
          <div className="boundary-tabs">
            <button
              type="button"
              className={inputMode === 'draw' ? 'tab active' : 'tab'}
              onClick={() => setInputMode('draw')}
            >
              Draw on map
            </button>
            <button
              type="button"
              className={inputMode === 'upload' ? 'tab active' : 'tab'}
              onClick={() => setInputMode('upload')}
            >
              Upload file
            </button>
          </div>

          {inputMode === 'upload' && (
            <div className="upload-file-row">
              <button type="button" className="btn secondary" onClick={() => fileRef.current?.click()}>
                Choose boundary file
              </button>
              <span className="upload-file-hint">
                {uploadName || '.geojson · .kml · coordinate list (.txt/.csv)'}
              </span>
              <input
                ref={fileRef}
                type="file"
                accept=".geojson,.json,.kml,.txt,.csv"
                hidden
                onChange={handleFileChange}
              />
            </div>
          )}

          <button
            type="button"
            className="map-layer-help-toggle"
            onClick={() => setShowLayerHelp((v) => !v)}
            aria-expanded={showLayerHelp}
          >
            {showLayerHelp ? 'Hide map layer guide' : 'Which map layer should I use?'}
          </button>

          {showLayerHelp && (
            <div className="map-layer-help">
              <p><strong>Satellite (Esri)</strong> — Use for drawing field boundaries. Sharp at Z15–17.</p>
              <p><strong>Sentinel-2 (EOX)</strong> — Crop monitoring context (~10 m). Slow to load; blur above Z15 is normal (not still loading).</p>
              <p><strong>Hybrid</strong> — Satellite plus place names. <strong>Street</strong> — District overview only. <strong>Map</strong> — Standard road map with town/village names, best for figuring out where a field actually is.</p>
              <p className="map-layer-help-note">Switch layers with the stack icon (top-right of map). Watch the status banner at the bottom of the map.</p>
            </div>
          )}

          {inputMode === 'draw' ? (
            <FieldsMap
              fields={[]}
              drawMode
              committedPolygon={polygon}
              onPolygonComplete={setPolygon}
              minHeight={420}
              defaultBasemap="satellite"
              initialZoom={15}
              showInspector
              fitToFields={!!polygon}
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
              defaultBasemap="satellite"
              initialZoom={16}
              fitToFields={!!polygon}
              showInspector
            />
          )}

          <div className={`map-draw-hint ${polygon ? 'success' : ''}`}>
            {polygon
              ? `✓ Boundary ready${uploadName ? ` — ${uploadName}` : ''} — complete the form on the right`
              : inputMode === 'draw'
                ? 'Pencil → place ≥3 points → Finish. Use Satellite layer; zoom to Z16–17 for accuracy.'
                : 'Choose a file above, or switch to Draw on map'}
          </div>
        </div>

        <form className="card-elevated register-form" onSubmit={handleSubmit}>
          <span className="section-title">Step 2 · Field metadata</span>
          <p className="register-form-intro">
            After you register, AgriSat pulls live Sentinel-2 / Sentinel-1 data via Google Earth Engine and assigns a risk tier.
          </p>

          <div className="form-group">
            <label htmlFor="field-name">Field name</label>
            <input id="field-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Optional display name" />
          </div>
          <div className="form-group">
            <label htmlFor="farmer-ref">Farmer reference</label>
            <input id="farmer-ref" value={farmerRef} onChange={(e) => setFarmerRef(e.target.value)} placeholder="Your internal ID" />
          </div>
          <div className="form-group">
            <label htmlFor="loan-ref">Loan / policy reference</label>
            <input id="loan-ref" value={loanRef} onChange={(e) => setLoanRef(e.target.value)} placeholder="Optional" />
          </div>
          <div className="form-group">
            <label htmlFor="sowing-date">Sowing date</label>
            <input id="sowing-date" type="date" value={sowingDate} onChange={(e) => setSowingDate(e.target.value)} required />
          </div>

          <p className="disclaimer">
            Risk scores are decision-support information only — not automated loan or claims decisions.
          </p>

          {error && <p className="error">{error}</p>}
          <button type="submit" disabled={loading || !polygon} className="register-submit">
            {loading ? 'Analyzing…' : polygon ? 'Register & analyze' : 'Draw or upload a boundary first'}
          </button>
        </form>
      </div>
    </>
  );
}
