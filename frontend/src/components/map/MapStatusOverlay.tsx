import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { useMap } from 'react-leaflet';
import { BASEMAPS, type BasemapId } from '../../lib/mapBasemaps';
import { getDrawHint, getMapStatus } from '../../lib/mapStatus';
import { useMapTileLoading } from './useMapTileLoading';

interface MapStatusOverlayProps {
  defaultBasemap: BasemapId;
  drawMode?: boolean;
  vertexCount?: number;
  finished?: boolean;
}

export function MapStatusOverlay({
  defaultBasemap,
  drawMode = false,
  vertexCount = 0,
  finished = false,
}: MapStatusOverlayProps) {
  const map = useMap();
  const [activeBasemap, setActiveBasemap] = useState<BasemapId>(defaultBasemap);
  const [zoom, setZoom] = useState(() => map.getZoom());
  const { loading, percent } = useMapTileLoading(map);

  useEffect(() => {
    const onBase = (e: L.LayersControlEvent) => {
      const match = BASEMAPS.find((b) => e.name.startsWith(b.label));
      if (match) setActiveBasemap(match.id);
    };
    const onZoom = () => setZoom(map.getZoom());

    map.on('baselayerchange', onBase);
    map.on('zoomend', onZoom);
    return () => {
      map.off('baselayerchange', onBase);
      map.off('zoomend', onZoom);
    };
  }, [map]);

  const status = getMapStatus(activeBasemap, zoom, loading);
  const drawHint = drawMode ? getDrawHint(vertexCount, finished, activeBasemap) : null;
  const headline = drawHint ?? (loading ? 'Tiles still downloading — see progress bar above' : status.headline);

  // Dismissible: a user can close this banner if it's in the way. Track
  // dismissal by the exact message shown, not a plain boolean, so a *new*
  // status (e.g. finishing the boundary, switching layers) still shows up
  // rather than staying hidden forever after one dismissal.
  const [dismissed, setDismissed] = useState<string | null>(null);
  const isDismissed = dismissed === headline;

  return createPortal(
    <>
      {loading && (
        <div className="map-tile-loading" role="status" aria-live="polite">
          <div className="map-tile-loading-track" aria-hidden>
            <div className="map-tile-loading-fill" style={{ width: `${percent}%` }} />
          </div>
          <span className="map-tile-loading-label">
            {status.headline} {percent}%
          </span>
        </div>
      )}

      {(!loading || drawMode) && !isDismissed && (
        <div
          className={`map-status-banner map-status-banner--${loading ? 'loading' : status.quality}`}
          role="status"
          aria-live="polite"
        >
          <button
            type="button"
            className="map-status-banner-close"
            aria-label="Dismiss this message"
            onClick={() => setDismissed(headline)}
          >
            ×
          </button>
          <div className="map-status-banner-main">
            <span className="map-status-banner-headline">{headline}</span>
            {!drawHint && !loading && status.detail && (
              <span className="map-status-banner-detail">{status.detail}</span>
            )}
          </div>
          {status.tip && !drawHint && !loading && (
            <span className="map-status-banner-tip">{status.tip}</span>
          )}
        </div>
      )}
    </>,
    map.getContainer(),
  );
}
