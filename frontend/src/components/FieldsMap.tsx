import { CircleMarker, GeoJSON, MapContainer, Polygon, Polyline, useMapEvents, ZoomControl } from 'react-leaflet';
import type { LatLngTuple } from 'leaflet';
import { useCallback, useEffect, useMemo, useState } from 'react';
import type { Field, RiskTier } from '../types';
import { PILOT_MAP_CENTER, RISK_COLORS } from '../lib/constants';
import { DEFAULT_BASEMAP_DRAW, type BasemapId } from '../lib/mapBasemaps';
import { MapBasemapLayers } from './map/MapBasemapLayers';
import { MapFitBounds } from './map/MapFitBounds';
import { MapInspector } from './map/MapInspector';

export const DRAW_COLORS = [
  { id: 'forest', hex: '#1B3D36', label: 'Forest' },
  { id: 'wheat', hex: '#B8954A', label: 'Wheat' },
  { id: 'indigo', hex: '#2E6B9E', label: 'Indigo' },
  { id: 'terracotta', hex: '#C4652E', label: 'Terracotta' },
  { id: 'berry', hex: '#7A3E5C', label: 'Berry' },
] as const;

export type DrawTool = 'pencil' | 'eraser';

interface FieldsMapProps {
  fields: Field[];
  onFieldClick?: (field: Field) => void;
  drawMode?: boolean;
  onPolygonComplete?: (geojson: GeoJSON.Polygon | null) => void;
  committedPolygon?: GeoJSON.Polygon | null;
  className?: string;
  minHeight?: number;
  defaultBasemap?: BasemapId;
  initialZoom?: number;
  showInspector?: boolean;
  fitToFields?: boolean;
  /** e.g. "Latest NDVI · 2025-12-14" */
  dataFreshnessLabel?: string;
}

function verticesToPolygon(vertices: LatLngTuple[]): GeoJSON.Polygon {
  const ring = [...vertices, vertices[0]].map(([lat, lng]) => [lng, lat] as [number, number]);
  return { type: 'Polygon', coordinates: [ring] };
}

function PolygonDrawLayer({
  color,
  tool,
  vertices,
  onAddVertex,
  onRemoveLast,
}: {
  color: string;
  tool: DrawTool;
  vertices: LatLngTuple[];
  onAddVertex: (v: LatLngTuple) => void;
  onRemoveLast: () => void;
}) {
  useMapEvents({
    click(e) {
      if (tool === 'eraser') {
        onRemoveLast();
        return;
      }
      onAddVertex([e.latlng.lat, e.latlng.lng]);
    },
    contextmenu(e) {
      e.originalEvent.preventDefault();
      if (vertices.length > 0) onRemoveLast();
    },
  });

  return (
    <>
      {vertices.map((pos, i) => (
        <CircleMarker
          key={`${pos[0]}-${pos[1]}-${i}`}
          center={pos}
          radius={7}
          pathOptions={{
            color: '#fff',
            weight: 2,
            fillColor: color,
            fillOpacity: 1,
          }}
        />
      ))}
      {vertices.length >= 2 && (
        <Polyline
          positions={vertices}
          pathOptions={{ color, weight: 3, opacity: 0.9, dashArray: tool === 'pencil' ? '6 4' : undefined }}
        />
      )}
      {vertices.length >= 3 && (
        <Polygon
          positions={vertices}
          pathOptions={{
            color,
            weight: 2.5,
            fillColor: color,
            fillOpacity: 0.22,
            opacity: 0.95,
          }}
        />
      )}
    </>
  );
}

interface DrawToolbarProps {
  color: string;
  tool: DrawTool;
  vertexCount: number;
  onColor: (hex: string) => void;
  onTool: (tool: DrawTool) => void;
  onUndo: () => void;
  onClear: () => void;
  onFinish: () => void;
}

function DrawToolbar({
  color,
  tool,
  vertexCount,
  onColor,
  onTool,
  onUndo,
  onClear,
  onFinish,
}: DrawToolbarProps) {
  return (
    <div className="map-draw-toolbar" role="toolbar" aria-label="Boundary drawing tools">
      <div className="map-draw-toolbar-group">
        <button
          type="button"
          className={`map-draw-tool ${tool === 'pencil' ? 'active' : ''}`}
          onClick={() => onTool('pencil')}
          title="Pencil — click map to add vertices"
        >
          <span className="map-draw-tool-icon" aria-hidden>✎</span>
          <span>Pencil</span>
        </button>
        <button
          type="button"
          className={`map-draw-tool ${tool === 'eraser' ? 'active' : ''}`}
          onClick={() => onTool('eraser')}
          title="Eraser — click map to remove last vertex"
        >
          <span className="map-draw-tool-icon" aria-hidden>⌫</span>
          <span>Eraser</span>
        </button>
      </div>

      <div className="map-draw-toolbar-group map-draw-colors" role="group" aria-label="Boundary color">
        {DRAW_COLORS.map((c) => (
          <button
            key={c.id}
            type="button"
            className={`map-draw-swatch ${color === c.hex ? 'active' : ''}`}
            style={{ background: c.hex }}
            onClick={() => onColor(c.hex)}
            title={c.label}
            aria-label={`${c.label} boundary color`}
          />
        ))}
      </div>

      <div className="map-draw-toolbar-group">
        <button type="button" className="map-draw-tool" onClick={onUndo} disabled={vertexCount === 0} title="Undo last point">
          ↶ Undo
        </button>
        <button type="button" className="map-draw-tool" onClick={onClear} disabled={vertexCount === 0} title="Clear sketch">
          Clear
        </button>
        <button
          type="button"
          className="map-draw-tool map-draw-finish"
          onClick={onFinish}
          disabled={vertexCount < 3}
          title="Close polygon (min 3 points)"
        >
          ✓ Finish
        </button>
      </div>
    </div>
  );
}

export function FieldsMap({
  fields,
  onFieldClick,
  drawMode,
  onPolygonComplete,
  committedPolygon,
  className = 'map-container',
  minHeight = 420,
  defaultBasemap = DEFAULT_BASEMAP_DRAW,
  initialZoom = 13,
  showInspector = false,
  fitToFields = false,
  dataFreshnessLabel,
}: FieldsMapProps) {
  const [drawColor, setDrawColor] = useState<string>(DRAW_COLORS[0].hex);
  const [drawTool, setDrawTool] = useState<DrawTool>('pencil');
  const [vertices, setVertices] = useState<LatLngTuple[]>([]);
  const [finished, setFinished] = useState(false);

  const fitPolygons = useMemo(() => {
    const polys = fields.map((f) => f.boundary_geojson).filter(Boolean);
    if (committedPolygon) polys.push(committedPolygon);
    return polys;
  }, [fields, committedPolygon]);

  useEffect(() => {
    if (!drawMode) {
      setVertices([]);
      setFinished(false);
      setDrawTool('pencil');
    }
  }, [drawMode]);

  useEffect(() => {
    if (committedPolygon && drawMode) {
      setFinished(true);
      setVertices([]);
    }
  }, [committedPolygon, drawMode]);

  const handleAddVertex = useCallback((v: LatLngTuple) => {
    setFinished(false);
    setVertices((prev) => [...prev, v]);
    onPolygonComplete?.(null);
  }, [onPolygonComplete]);

  const handleUndo = useCallback(() => {
    setFinished(false);
    setVertices((prev) => prev.slice(0, -1));
    onPolygonComplete?.(null);
  }, [onPolygonComplete]);

  const handleClear = useCallback(() => {
    setVertices([]);
    setFinished(false);
    onPolygonComplete?.(null);
  }, [onPolygonComplete]);

  const handleFinish = useCallback(() => {
    if (vertices.length < 3) return;
    const poly = verticesToPolygon(vertices);
    setFinished(true);
    onPolygonComplete?.(poly);
  }, [vertices, onPolygonComplete]);

  const showSketch = drawMode && vertices.length > 0 && !finished;
  const showCommitted = committedPolygon && (finished || !showSketch);

  return (
    <div
      className={`${className}${drawMode ? ' map-container--draw' : ''} map-container--layers`}
      style={{ minHeight, position: 'relative' }}
      data-draw-tool={drawMode ? drawTool : undefined}
    >
      {drawMode && (
        <DrawToolbar
          color={drawColor}
          tool={drawTool}
          vertexCount={vertices.length}
          onColor={setDrawColor}
          onTool={setDrawTool}
          onUndo={handleUndo}
          onClear={handleClear}
          onFinish={handleFinish}
        />
      )}

      {drawMode && (
        <div className="map-draw-status">
          {finished && committedPolygon
            ? 'Boundary closed — zoom in on satellite for accuracy, then register'
            : `${vertices.length} point${vertices.length !== 1 ? 's' : ''} · switch to Satellite layer · zoom 16+ for parcels`}
        </div>
      )}

      <MapContainer
        center={PILOT_MAP_CENTER}
        zoom={initialZoom}
        minZoom={5}
        maxZoom={20}
        style={{ height: '100%', width: '100%', minHeight }}
        zoomControl={false}
      >
        <ZoomControl position="bottomright" />
        <MapBasemapLayers defaultBasemap={defaultBasemap} />
        {(showInspector || drawMode) && (
          <MapInspector dataLabel={dataFreshnessLabel} />
        )}
        {fitToFields && fitPolygons.length > 0 && (
          <MapFitBounds polygons={fitPolygons} maxZoom={drawMode ? 18 : 17} />
        )}

        {drawMode && !finished && (
          <PolygonDrawLayer
            color={drawColor}
            tool={drawTool}
            vertices={vertices}
            onAddVertex={handleAddVertex}
            onRemoveLast={handleUndo}
          />
        )}

        {showCommitted && committedPolygon && (
          <GeoJSON
            key="committed-boundary"
            data={committedPolygon}
            style={{
              color: drawColor,
              weight: 3,
              fillColor: drawColor,
              fillOpacity: 0.3,
            }}
          />
        )}

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
