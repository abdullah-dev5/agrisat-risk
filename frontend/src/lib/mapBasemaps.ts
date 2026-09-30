/** Basemap tile layers for field registration and portfolio maps. */

export type BasemapId = 'street' | 'satellite' | 'hybrid' | 'sentinel' | 'roadmap';

export interface BasemapConfig {
  id: BasemapId;
  label: string;
  description: string;
  url: string;
  attribution: string;
  maxZoom: number;
  maxNativeZoom?: number;
  subdomains?: string;
  /** Recommended for drawing field boundaries */
  recommendedForDraw?: boolean;
}

export const BASEMAPS: BasemapConfig[] = [
  {
    id: 'satellite',
    label: 'Satellite',
    description: 'Esri World Imagery — high-res aerial for parcel mapping',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution:
      'Tiles &copy; Esri — Source: Esri, Maxar, Earthstar Geographics, USDA FSA, USGS, AeroGRID, IGN, IGP',
    maxZoom: 20,
    /** Rural Sindh often has no native tiles above ~17; Leaflet upscales above this */
    maxNativeZoom: 17,
    recommendedForDraw: true,
  },
  {
    id: 'hybrid',
    label: 'Hybrid',
    description: 'Satellite imagery with roads and place labels',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Imagery &copy; Esri · Labels &copy; Esri, OpenStreetMap',
    maxZoom: 20,
    maxNativeZoom: 17,
  },
  {
    id: 'sentinel',
    label: 'Sentinel-2',
    description: 'Cloudless Sentinel-2 mosaic — crop monitoring context (~10 m)',
    url: 'https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2021_3857/default/GoogleMapsCompatible/{z}/{y}/{x}.jpg',
    attribution: 'Sentinel-2 cloudless &copy; <a href="https://s2maps.eu">EOX</a> / ESA',
    maxZoom: 17,
    maxNativeZoom: 15,
  },
  {
    id: 'street',
    label: 'Street',
    description: 'Light minimal map for district overview',
    url: 'https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri — Source: Esri, HERE, Garmin, (c) OpenStreetMap contributors, and the GIS user community',
    maxZoom: 16,
  },
  {
    id: 'roadmap',
    label: 'Map',
    description: 'Standard road map with town/village names, roads and landmarks — best for figuring out where you are',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri — Source: Esri, HERE, Garmin, USGS, Intermap, INCREMENT P, NRCan, Esri Japan, METI, Esri China (Hong Kong), Esri Korea, Esri (Thailand), NGCC, (c) OpenStreetMap contributors, GIS User Community',
    maxZoom: 19,
  },
];

export const HYBRID_LABELS_URL =
  'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}';

export const DEFAULT_BASEMAP: BasemapId = 'satellite';
export const DEFAULT_BASEMAP_DRAW: BasemapId = 'satellite';

export function getBasemap(id: BasemapId): BasemapConfig {
  return BASEMAPS.find((b) => b.id === id) ?? BASEMAPS[0];
}

/** ~meters per pixel at equator for zoom level (rough scale bar). */
export function metersPerPixel(lat: number, zoom: number): number {
  return (156543.03392 * Math.cos((lat * Math.PI) / 180)) / 2 ** zoom;
}

export function formatScale(lat: number, zoom: number): string {
  const m = metersPerPixel(lat, zoom);
  if (m >= 1000) return `~${(m / 1000).toFixed(1)} km/px`;
  if (m >= 1) return `~${Math.round(m)} m/px`;
  return `~${(m * 100).toFixed(0)} cm/px`;
}
