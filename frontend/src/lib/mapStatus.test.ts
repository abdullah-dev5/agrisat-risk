import { describe, it, expect } from 'vitest';
import { getMapStatus, getDrawHint, nativeZoomForBasemap } from './mapStatus';

describe('getMapStatus', () => {
  it('reports loading while tiles are in flight, regardless of zoom', () => {
    const status = getMapStatus('satellite', 16, true);
    expect(status.quality).toBe('loading');
  });

  it('reports overview at low zoom', () => {
    const status = getMapStatus('satellite', 8, false);
    expect(status.quality).toBe('overview');
  });

  it('reports upscaled when zoomed past native resolution', () => {
    const nativeZoom = nativeZoomForBasemap('satellite');
    const status = getMapStatus('satellite', nativeZoom + 2, false);
    expect(status.quality).toBe('upscaled');
  });

  it('reports native and flags the ideal drawing range for satellite at Z16', () => {
    const status = getMapStatus('satellite', 16, false);
    expect(status.quality).toBe('native');
    expect(status.headline).toMatch(/ideal for drawing/);
  });

  it('gives sentinel-specific guidance at native zoom', () => {
    const status = getMapStatus('sentinel', 12, false);
    expect(status.quality).toBe('native');
    expect(status.tip).toMatch(/Satellite layer/);
  });
});

describe('getDrawHint', () => {
  it('prompts for the first point when nothing is drawn', () => {
    expect(getDrawHint(0, false, 'satellite')).toMatch(/Click the map/);
  });

  it('asks for more points below the 3-point minimum', () => {
    expect(getDrawHint(1, false, 'satellite')).toMatch(/add 2 more/);
  });

  it('confirms completion once finished', () => {
    expect(getDrawHint(5, true, 'satellite')).toMatch(/Boundary closed/);
  });

  it('suggests switching layers when drawing on the sentinel basemap', () => {
    expect(getDrawHint(4, false, 'sentinel')).toMatch(/switch to Satellite/);
  });
});
