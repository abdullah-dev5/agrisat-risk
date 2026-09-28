import { describe, it, expect } from 'vitest';
import { parseGeoJson, parseCoordinateList, parseKml } from './boundaryParser';

describe('parseGeoJson', () => {
  it('parses a bare Polygon and closes an open ring', () => {
    const result = parseGeoJson(
      JSON.stringify({
        type: 'Polygon',
        coordinates: [[[68.4, 25.6], [68.5, 25.6], [68.5, 25.7]]],
      }),
    );
    const ring = result.coordinates[0];
    expect(ring[0]).toEqual(ring[ring.length - 1]);
    expect(ring).toHaveLength(4);
  });

  it('leaves an already-closed ring untouched', () => {
    const closed = [[68.4, 25.6], [68.5, 25.6], [68.5, 25.7], [68.4, 25.6]];
    const result = parseGeoJson(JSON.stringify({ type: 'Polygon', coordinates: [closed] }));
    expect(result.coordinates[0]).toHaveLength(4);
  });

  it('extracts the Polygon from a Feature', () => {
    const result = parseGeoJson(
      JSON.stringify({
        type: 'Feature',
        properties: {},
        geometry: { type: 'Polygon', coordinates: [[[68.4, 25.6], [68.5, 25.6], [68.5, 25.7]]] },
      }),
    );
    expect(result.type).toBe('Polygon');
  });

  it('extracts the first Polygon feature from a FeatureCollection', () => {
    const result = parseGeoJson(
      JSON.stringify({
        type: 'FeatureCollection',
        features: [
          { type: 'Feature', properties: {}, geometry: { type: 'Point', coordinates: [0, 0] } },
          {
            type: 'Feature',
            properties: {},
            geometry: { type: 'Polygon', coordinates: [[[68.4, 25.6], [68.5, 25.6], [68.5, 25.7]]] },
          },
        ],
      }),
    );
    expect(result.type).toBe('Polygon');
  });

  it('rejects a FeatureCollection with no Polygon feature', () => {
    expect(() =>
      parseGeoJson(
        JSON.stringify({
          type: 'FeatureCollection',
          features: [{ type: 'Feature', properties: {}, geometry: { type: 'Point', coordinates: [0, 0] } }],
        }),
      ),
    ).toThrow(/must contain a Polygon/);
  });

  it('rejects a LineString', () => {
    expect(() =>
      parseGeoJson(JSON.stringify({ type: 'LineString', coordinates: [[0, 0], [1, 1]] })),
    ).toThrow();
  });
});

describe('parseCoordinateList', () => {
  it('parses "lat, lng" order using the Pakistan-range heuristic', () => {
    // lat ~25 (< 50) comes first, lng ~68 (> 50) comes second -> heuristic should swap to [lng, lat]
    const result = parseCoordinateList('25.60, 68.40\n25.60, 68.50\n25.70, 68.50');
    expect(result.coordinates[0][0]).toEqual([68.4, 25.6]);
  });

  it('parses "lng, lat" order unchanged', () => {
    const result = parseCoordinateList('68.40, 25.60\n68.50, 25.60\n68.50, 25.70');
    expect(result.coordinates[0][0]).toEqual([68.4, 25.6]);
  });

  it('accepts space-separated values', () => {
    const result = parseCoordinateList('68.40 25.60\n68.50 25.60\n68.50 25.70');
    expect(result.coordinates[0]).toHaveLength(4); // 3 points + closing point
  });

  it('skips blank lines and unparsable rows', () => {
    const result = parseCoordinateList('68.40, 25.60\n\nnot,numbers\n68.50, 25.60\n68.50, 25.70');
    expect(result.coordinates[0]).toHaveLength(4);
  });

  it('rejects fewer than 3 valid points', () => {
    expect(() => parseCoordinateList('68.40, 25.60\n68.50, 25.60')).toThrow(/at least 3 points/);
  });
});

describe('parseKml', () => {
  it('parses coordinates from a Polygon element', () => {
    const kml = `<?xml version="1.0"?>
      <kml><Placemark><Polygon><outerBoundaryIs><LinearRing>
        <coordinates>68.40,25.60,0 68.50,25.60,0 68.50,25.70,0</coordinates>
      </LinearRing></outerBoundaryIs></Polygon></Placemark></kml>`;
    const result = parseKml(kml);
    expect(result.coordinates[0][0]).toEqual([68.4, 25.6]);
    expect(result.coordinates[0][0]).toEqual(result.coordinates[0][result.coordinates[0].length - 1]);
  });

  it('throws on malformed XML', () => {
    expect(() => parseKml('<kml><unclosed>')).toThrow();
  });

  it('throws when there is no Polygon or LinearRing', () => {
    expect(() => parseKml('<kml><Placemark/></kml>')).toThrow(/must contain a Polygon/);
  });
});
