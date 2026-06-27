import { MapContainer, TileLayer, GeoJSON, useMapEvents, ZoomControl } from 'react-leaflet';
import type { LatLngTuple } from 'leaflet';
import { useRef } from 'react';
import type { Field, RiskTier } from '../types';
import { MAP_ATTRIBUTION, MAP_TILE_URL, RISK_COLORS } from '../lib/constants';

const FAISALABAD_CENTER: LatLngTuple = [31.418, 73.079];

interface FieldsMapProps {
  fields: Field[];
  onFieldClick?: (field: Field) => void;
  drawMode?: boolean;
  onPolygonComplete?: (geojson: GeoJSON.Polygon) => void;
  className?: string;
  minHeight?: number;
}

function DrawHandler({ onPolygonComplete }: { onPolygonComplete?: (g: GeoJSON.Polygon) => void }) {
  const points = useRef<LatLngTuple[]>([]);

  useMapEvents({
    click(e) {
      if (!onPolygonComplete) return;
      points.current.push([e.latlng.lat, e.latlng.lng]);
      if (points.current.length >= 3) {
        const ring = [...points.current, points.current[0]];
        onPolygonComplete({ type: 'Polygon', coordinates: [ring.map(([lat, lng]) => [lng, lat])] });
        points.current = [];
      }
    },
  });
  return null;
}

export function FieldsMap({
  fields,
  onFieldClick,
  drawMode,
  onPolygonComplete,
  className = 'map-container',
  minHeight = 420,
}: FieldsMapProps) {
  return (
    <div className={className} style={{ minHeight }}>
      <MapContainer center={FAISALABAD_CENTER} zoom={11} style={{ height: '100%', width: '100%', minHeight }} zoomControl={false}>
        <ZoomControl position="bottomright" />
        <TileLayer attribution={MAP_ATTRIBUTION} url={MAP_TILE_URL} />
        {drawMode && <DrawHandler onPolygonComplete={onPolygonComplete} />}
        {fields.map((field) => {
          const tier = (field.current_risk_tier ?? 'normal') as RiskTier;
          const color = RISK_COLORS[tier];
          return (
            <GeoJSON
              key={field.id}
              data={field.boundary_geojson}
              style={{
                color,
                weight: 2.5,
                fillColor: color,
                fillOpacity: 0.28,
              }}
              eventHandlers={{
                click: () => onFieldClick?.(field),
              }}
            />
          );
        })}
      </MapContainer>
    </div>
  );
}
