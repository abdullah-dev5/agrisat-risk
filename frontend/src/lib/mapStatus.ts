import { getBasemap, type BasemapId } from './mapBasemaps';

export type MapQuality = 'loading' | 'overview' | 'native' | 'upscaled';

export interface MapStatusInfo {
  quality: MapQuality;
  headline: string;
  detail: string;
  tip?: string;
}

export function nativeZoomForBasemap(id: BasemapId): number {
  const bm = getBasemap(id);
  return bm.maxNativeZoom ?? bm.maxZoom;
}

export function getMapStatus(
  basemapId: BasemapId,
  zoom: number,
  tilesLoading: boolean,
): MapStatusInfo {
  const bm = getBasemap(basemapId);
  const nativeZoom = nativeZoomForBasemap(basemapId);

  if (tilesLoading) {
    return {
      quality: 'loading',
      headline: `Downloading ${bm.label} tiles…`,
      detail: 'Sharpness may improve as each tile finishes. Wait until the bar reaches 100%.',
    };
  }

  if (zoom < 11) {
    return {
      quality: 'overview',
      headline: `${bm.label} · District view`,
      detail: 'Tiles are loaded. Zoom in closer to draw or inspect individual fields.',
      tip: basemapId === 'sentinel'
        ? 'Sentinel-2 shows crop health context (~10 m). Use Satellite layer for sharp boundaries.'
        : 'Zoom to Z15–17 for parcel-level detail in Matiari.',
    };
  }

  if (zoom > nativeZoom) {
    const upscaled =
      basemapId === 'sentinel'
        ? 'Sentinel-2 is stretched beyond its native zoom — blur is normal, not still loading.'
        : 'Tiles are loaded but stretched beyond native resolution for this area.';
    return {
      quality: 'upscaled',
      headline: `${bm.label} · Loaded (preview stretched)`,
      detail: upscaled,
      tip:
        basemapId === 'sentinel'
          ? 'For drawing: open layers (top-right) → choose Satellite.'
          : `Native detail for this layer ends around Z${nativeZoom}. Zoom out one level for true pixels.`,
    };
  }

  if (basemapId === 'sentinel') {
    return {
      quality: 'native',
      headline: `${bm.label} · Loaded · crop context`,
      detail: 'Full Sentinel-2 mosaic at ~10 m — good for vegetation patterns, not sharp field edges.',
      tip: 'Switch to Satellite layer when tracing parcel boundaries.',
    };
  }

  if (basemapId === 'satellite' || basemapId === 'hybrid') {
    const ideal = zoom >= 15 && zoom <= 17;
    return {
      quality: 'native',
      headline: `${bm.label} · Loaded${ideal ? ' · ideal for drawing' : ''}`,
      detail: ideal
        ? 'Best balance of sharp imagery and coverage for rural Sindh.'
        : `Native tiles to ~Z${nativeZoom}. ${zoom < 15 ? 'Zoom in a bit more for boundary work.' : ''}`,
    };
  }

  return {
    quality: 'native',
    headline: `${bm.label} · Loaded`,
    detail: 'All visible map tiles have finished downloading.',
  };
}

export function getDrawHint(
  vertexCount: number,
  finished: boolean,
  basemapId: BasemapId,
): string | null {
  if (finished) {
    return 'Boundary closed — review on Satellite at Z16–17, then complete the form on the right.';
  }
  if (vertexCount === 0) {
    return 'Click the map to place points · minimum 3 · use Satellite layer for accuracy';
  }
  if (vertexCount < 3) {
    return `${vertexCount} point${vertexCount !== 1 ? 's' : ''} — add ${3 - vertexCount} more, then Finish`;
  }
  if (basemapId === 'sentinel') {
    return `${vertexCount} points — click Finish, or switch to Satellite layer for sharper tracing`;
  }
  return `${vertexCount} points — click Finish when the boundary looks correct`;
}
