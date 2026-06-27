import { MapContainer, TileLayer, GeoJSON, useMapEvents } from 'react-leaflet';
import type { LatLngTuple } from 'leaflet';
import { useRef } from 'react';
import type { Field, RiskTier } from '../types';
import { RISK_COLORS } from '../lib/constants';

const FAISALABAD_CENTER: LatLngTuple = [31.418, 73.079];

interface FieldsMapProps {
  fields: Field[];
  onFieldClick?: (field: Field) => void;
  drawMode?: boolean;
  onPolygonComplete?: (geojson: GeoJSON.Polygon) => void;
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

export function FieldsMap({ fields, onFieldClick, drawMode, onPolygonComplete }: FieldsMapProps) {
  return (
    <div className="map-container">
      <MapContainer center={FAISALABAD_CENTER} zoom={11} style={{ height: '100%', width: '100%' }}>
        <TileLayer
          attribution='&copy; OpenStreetMap'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {drawMode && <DrawHandler onPolygonComplete={onPolygonComplete} />}
        {fields.map((field) => {
          const tier = (field.current_risk_tier ?? 'normal') as RiskTier;
          return (
            <GeoJSON
              key={field.id}
              data={field.boundary_geojson}
              style={{ color: RISK_COLORS[tier], weight: 2, fillOpacity: 0.35 }}
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
