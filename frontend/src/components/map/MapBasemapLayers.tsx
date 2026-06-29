import { LayersControl, TileLayer } from 'react-leaflet';
import { BASEMAPS, HYBRID_LABELS_URL, type BasemapId } from '../../lib/mapBasemaps';

interface MapBasemapLayersProps {
  defaultBasemap?: BasemapId;
}

export function MapBasemapLayers({ defaultBasemap = 'satellite' }: MapBasemapLayersProps) {
  return (
    <LayersControl position="topright">
      {BASEMAPS.map((basemap) => (
        <LayersControl.BaseLayer
          key={basemap.id}
          name={basemap.label}
          checked={basemap.id === defaultBasemap}
        >
          <TileLayer
            url={basemap.url}
            attribution={basemap.attribution}
            maxZoom={basemap.maxZoom}
            maxNativeZoom={basemap.maxNativeZoom}
            subdomains={basemap.subdomains}
          />
          {basemap.id === 'hybrid' && (
            <TileLayer
              url={HYBRID_LABELS_URL}
              attribution=""
              maxZoom={20}
              maxNativeZoom={19}
              pane="overlayPane"
            />
          )}
        </LayersControl.BaseLayer>
      ))}
    </LayersControl>
  );
}
