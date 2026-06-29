import L from 'leaflet';
import { useEffect } from 'react';
import { useMap } from 'react-leaflet';

interface MapFitBoundsProps {
  polygons: GeoJSON.Polygon[];
  maxZoom?: number;
  enabled?: boolean;
}

export function MapFitBounds({ polygons, maxZoom = 17, enabled = true }: MapFitBoundsProps) {
  const map = useMap();

  useEffect(() => {
    if (!enabled || polygons.length === 0) return;

    const collection: GeoJSON.FeatureCollection = {
      type: 'FeatureCollection',
      features: polygons.map((g) => ({
        type: 'Feature',
        properties: {},
        geometry: g,
      })),
    };
    const layer = L.geoJSON(collection);
    const bounds = layer.getBounds();

    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [48, 48], maxZoom });
    }
  }, [map, polygons, maxZoom, enabled]);

  return null;
}
