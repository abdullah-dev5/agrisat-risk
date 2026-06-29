import { useMap, useMapEvents } from 'react-leaflet';
import { useEffect, useState } from 'react';
import { BASEMAPS, formatScale, type BasemapId } from '../../lib/mapBasemaps';
import { getMapStatus, nativeZoomForBasemap } from '../../lib/mapStatus';

interface MapInspectorProps {
  dataLabel?: string;
  defaultBasemap?: BasemapId;
}

const QUALITY_LABELS = {
  loading: 'Loading',
  overview: 'Overview',
  native: 'Ready',
  upscaled: 'Stretched',
} as const;

export function MapInspector({ dataLabel, defaultBasemap = 'satellite' }: MapInspectorProps) {
  const map = useMap();
  const [cursor, setCursor] = useState<{ lat: number; lng: number } | null>(null);
  const [zoom, setZoom] = useState(() => map.getZoom());
  const [activeBasemap, setActiveBasemap] = useState<BasemapId>(defaultBasemap);

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

  useMapEvents({
    mousemove(e) {
      setCursor({ lat: e.latlng.lat, lng: e.latlng.lng });
    },
    mouseout() {
      setCursor(null);
    },
  });

  const lat = cursor?.lat ?? 25.6;
  const scale = formatScale(lat, zoom);
  const status = getMapStatus(activeBasemap, zoom, false);
  const bm = BASEMAPS.find((b) => b.id === activeBasemap);
  const nativeZ = nativeZoomForBasemap(activeBasemap);

  return (
    <div className="map-inspector" aria-live="polite">
      <span className="map-inspector-item map-inspector-layer" title={bm?.description}>
        {bm?.label ?? 'Map'}
      </span>
      <span
        className={`map-inspector-item map-inspector-quality map-inspector-quality--${status.quality}`}
        title={status.detail}
      >
        {QUALITY_LABELS[status.quality]}
      </span>
      <span className="map-inspector-item" title={`Native tiles to ~Z${nativeZ}`}>
        Z{zoom}
      </span>
      <span className="map-inspector-item">{scale}</span>
      {cursor && (
        <span className="map-inspector-item map-inspector-coords">
          {cursor.lat.toFixed(5)}°, {cursor.lng.toFixed(5)}°
        </span>
      )}
      {dataLabel && <span className="map-inspector-data">{dataLabel}</span>}
    </div>
  );
}
