import { useEffect, useRef, useState } from 'react';
import { api } from '../lib/api';
import type { FieldImagery } from '../types';

interface Props {
  fieldId: string;
}

export function FieldGeeImagery({ fieldId }: Props) {
  const [imagery, setImagery] = useState<FieldImagery | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [view, setView] = useState<'rgb' | 'ndvi'>('rgb');
  const requestId = useRef(0);

  useEffect(() => {
    const id = ++requestId.current;
    setLoading(true);
    setError('');
    api.getFieldImagery(fieldId)
      .then((data) => {
        if (id === requestId.current) setImagery(data);
      })
      .catch((e) => {
        if (id === requestId.current) setError(e.message);
      })
      .finally(() => {
        if (id === requestId.current) setLoading(false);
      });
  }, [fieldId]);

  if (loading) {
    return (
      <div className="card gee-imagery">
        <span className="section-title">Live satellite imagery (GEE)</span>
        <p className="chart-caption">Fetching latest clear Sentinel-2 scene from GEE — this can take up to 2 minutes…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card gee-imagery">
        <span className="section-title">Live satellite imagery (GEE)</span>
        <p className="error">{error}</p>
      </div>
    );
  }

  if (!imagery) return null;

  const { latest, compare, ndvi_delta } = imagery;
  const layer = view === 'rgb' ? 'rgb' : 'ndvi';

  return (
    <div className="card gee-imagery">
      <div className="gee-imagery-header">
        <div>
          <span className="section-title">Live satellite imagery (GEE)</span>
          <p className="chart-caption">
            Latest clear Sentinel-2 · {latest.date} · {latest.cloud_pct}% cloud
            {ndvi_delta != null && compare && (
              <> · NDVI {ndvi_delta >= 0 ? '+' : ''}{ndvi_delta.toFixed(3)} vs {compare.date}</>
            )}
          </p>
        </div>
        <div className="gee-imagery-toggle" role="tablist">
          <button
            type="button"
            role="tab"
            className={view === 'rgb' ? 'active' : ''}
            onClick={() => setView('rgb')}
          >
            True color
          </button>
          <button
            type="button"
            role="tab"
            className={view === 'ndvi' ? 'active' : ''}
            onClick={() => setView('ndvi')}
          >
            NDVI
          </button>
        </div>
      </div>

      <div className="gee-imagery-grid">
        <figure className="gee-imagery-panel">
          <figcaption>Latest · {latest.date}</figcaption>
          <img
            src={latest[layer].thumb_url}
            alt={`${view === 'rgb' ? 'True color' : 'NDVI'} satellite view ${latest.date}`}
            loading="lazy"
          />
          {latest.ndvi_mean != null && view === 'ndvi' && (
            <span className="gee-imagery-stat">Mean NDVI {latest.ndvi_mean.toFixed(3)}</span>
          )}
        </figure>

        {compare && (
          <figure className="gee-imagery-panel">
            <figcaption>Earlier · {compare.date}</figcaption>
            <img
              src={compare[layer].thumb_url}
              alt={`Earlier ${view} view ${compare.date}`}
              loading="lazy"
            />
            {compare.ndvi_mean != null && view === 'ndvi' && (
              <span className="gee-imagery-stat">Mean NDVI {compare.ndvi_mean.toFixed(3)}</span>
            )}
          </figure>
        )}
      </div>

      <p className="disclaimer" style={{ marginTop: '0.75rem' }}>
        Processed on-demand from Google Earth Engine — not a live video feed. Scenes update as new Sentinel-2 passes become available (typically every 5 days).
      </p>
    </div>
  );
}
