/** Parse field boundaries from GeoJSON, KML, or coordinate lists (FR-2.2). */

export type BoundarySource = 'geojson' | 'kml' | 'coordinates';

export function parseBoundaryFile(file: File): Promise<GeoJSON.Polygon> {
  return file.text().then((text) => {
    const name = file.name.toLowerCase();
    if (name.endsWith('.kml')) return parseKml(text);
    if (name.endsWith('.json') || name.endsWith('.geojson')) return parseGeoJson(text);
    if (name.endsWith('.txt') || name.endsWith('.csv')) return parseCoordinateList(text);
    // try geojson first, then kml
    try {
      return parseGeoJson(text);
    } catch {
      return parseKml(text);
    }
  });
}

export function parseGeoJson(text: string): GeoJSON.Polygon {
  const data = JSON.parse(text) as GeoJSON.GeoJSON;
  if (data.type === 'FeatureCollection') {
    const feature = data.features?.find((f) => f.geometry?.type === 'Polygon');
    if (feature?.geometry?.type === 'Polygon') return closeRing(feature.geometry);
    throw new Error('GeoJSON FeatureCollection must contain a Polygon feature');
  }
  if (data.type === 'Feature' && data.geometry?.type === 'Polygon') {
    return closeRing(data.geometry);
  }
  if (data.type === 'Polygon') {
    return closeRing(data as GeoJSON.Polygon);
  }
  throw new Error('GeoJSON must be a Polygon, Feature, or FeatureCollection with a Polygon');
}

export function parseCoordinateList(text: string): GeoJSON.Polygon {
  const lines = text.trim().split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  const coords: [number, number][] = [];

  for (const line of lines) {
    const parts = line.split(/[,\s]+/).map((p) => p.trim()).filter(Boolean);
    if (parts.length < 2) continue;
    const a = parseFloat(parts[0]);
    const b = parseFloat(parts[1]);
    if (Number.isNaN(a) || Number.isNaN(b)) continue;
    // Heuristic: Pakistan lng ~64–78, lat ~23–37
    const lng = Math.abs(a) > 50 ? a : b;
    const lat = Math.abs(a) > 50 ? b : a;
    coords.push([lng, lat]);
  }

  if (coords.length < 3) {
    throw new Error('Coordinate list needs at least 3 points (one per line: lng, lat or lat, lng)');
  }
  return closeRing({ type: 'Polygon', coordinates: [coords] });
}

export function parseKml(text: string): GeoJSON.Polygon {
  const doc = new DOMParser().parseFromString(text, 'text/xml');
  if (doc.querySelector('parsererror')) {
    throw new Error('Invalid KML file');
  }

  const rings = [
    ...doc.querySelectorAll('Polygon coordinates'),
    ...doc.querySelectorAll('LinearRing coordinates'),
  ];

  if (!rings.length) {
    throw new Error('KML must contain a Polygon or LinearRing with coordinates');
  }

  const raw = rings[0].textContent?.trim() ?? '';
  const coords = raw
    .split(/\s+/)
    .map((pair) => {
      const [lng, lat] = pair.split(',').map(Number);
      return [lng, lat] as [number, number];
    })
    .filter(([lng, lat]) => !Number.isNaN(lng) && !Number.isNaN(lat));

  if (coords.length < 3) {
    throw new Error('KML polygon needs at least 3 coordinate pairs');
  }

  return closeRing({ type: 'Polygon', coordinates: [coords] });
}

function closeRing(polygon: GeoJSON.Polygon): GeoJSON.Polygon {
  const ring = polygon.coordinates[0];
  if (!ring?.length) throw new Error('Empty polygon ring');
  const first = ring[0];
  const last = ring[ring.length - 1];
  const closed =
    first[0] === last[0] && first[1] === last[1] ? ring : [...ring, first];
  return { type: 'Polygon', coordinates: [closed] };
}
