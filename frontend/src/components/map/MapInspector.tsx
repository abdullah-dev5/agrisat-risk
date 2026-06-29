import { useMap, useMapEvents } from 'react-leaflet';
import { useEffect, useState } from 'react';
import { formatScale } from '../../lib/mapBasemaps';

interface MapInspectorProps {
  dataLabel?: string;
}

export function MapInspector({ dataLabel }: MapInspectorProps) {
  const map = useMap();
  const [cursor, setCursor] = useState<{ lat: number; lng: number } | null>(null);
  const [zoom, setZoom] = useState(() => map.getZoom());

  useEffect(() => {
    const syncZoom = () => setZoom(map.getZoom());
    map.on('zoomend', syncZoom);
    return () => {
      map.off('zoomend', syncZoom);
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

  return (
    <div className="map-inspector" aria-live="polite">
      <span className="map-inspector-item" title="Zoom level — use satellite + zoom 16+ for parcel detail">
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
