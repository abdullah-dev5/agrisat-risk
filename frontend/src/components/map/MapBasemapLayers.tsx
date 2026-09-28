import { LayerGroup, LayersControl, TileLayer } from 'react-leaflet';
import { BASEMAPS, HYBRID_LABELS_URL, type BasemapId } from '../../lib/mapBasemaps';

interface MapBasemapLayersProps {
  defaultBasemap?: BasemapId;
}

export function MapBasemapLayers({ defaultBasemap = 'satellite' }: MapBasemapLayersProps) {
  return (
    <LayersControl position="topright">
      {BASEMAPS.map((basemap) => {
        const tile = (
          <TileLayer
            url={basemap.url}
            attribution={basemap.attribution}
            maxZoom={basemap.maxZoom}
            {...(basemap.maxNativeZoom != null ? { maxNativeZoom: basemap.maxNativeZoom } : {})}
            {...(basemap.subdomains ? { subdomains: basemap.subdomains } : {})}
          />
        );
        return (
          <LayersControl.BaseLayer
            key={basemap.id}
            name={`${basemap.label} — ${basemap.recommendedForDraw ? 'best for drawing' : basemap.id === 'sentinel' ? 'crop context ~10 m' : 'overview'}`}
            checked={basemap.id === defaultBasemap}
          >
            {basemap.id === 'hybrid' ? (
              // A BaseLayer must wrap exactly one layer to register as a single
              // control entry -- two sibling TileLayers here would register as
              // two separate (duplicate) radio options instead of one combined
              // imagery+labels layer. Group them so they toggle together.
              <LayerGroup>
                {tile}
                <TileLayer
                  url={HYBRID_LABELS_URL}
                  attribution=""
                  maxZoom={20}
                  maxNativeZoom={17}
                  pane="overlayPane"
                />
              </LayerGroup>
            ) : (
              tile
            )}
          </LayersControl.BaseLayer>
        );
      })}
    </LayersControl>
  );
}
