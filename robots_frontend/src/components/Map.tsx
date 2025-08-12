import React, { useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, Polygon, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './Map.css';

// Fix for default markers in react-leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

interface MapPoint {
  lat: number;
  lon: number;
  name?: string;
  tags?: Record<string, any>;
}

interface MapRoute {
  geometry: any;
  distance_m?: number;
  duration_s?: number;
}

interface MapPolygon {
  coordinates: number[][][];
  properties?: Record<string, any>;
}

interface MapProps {
  center?: [number, number];
  zoom?: number;
  markers?: MapPoint[];
  routes?: MapRoute[];
  polygons?: MapPolygon[];
  height?: string;
  className?: string;
}

// Component to handle map updates
function MapUpdater({ center, zoom }: { center?: [number, number]; zoom?: number }) {
  const map = useMap();
  
  useEffect(() => {
    if (center) {
      map.setView(center, zoom || 13);
    }
  }, [center, zoom, map]);
  
  return null;
}

// Component to fit map bounds to route geometry
function FitBoundsToRoute({ routes }: { routes: MapRoute[] }) {
  const map = useMap();
  useEffect(() => {
    if (routes && routes.length > 0 && routes[0].geometry && routes[0].geometry.coordinates.length > 0) {
      // Flatten all route coordinates into one array
      const allCoords = routes.flatMap(route => route.geometry.coordinates.map((coord: number[]) => [coord[1], coord[0]]));
      if (allCoords.length > 0) {
        map.fitBounds(allCoords);
      }
    }
  }, [routes, map]);
  return null;
}

const Map: React.FC<MapProps> = ({
  center = [52.5200, 13.4050], // Default to Berlin
  zoom = 13,
  markers = [],
  routes = [],
  polygons = [],
  height = '400px',
  className = ''
}) => {
  const mapRef = useRef<L.Map>(null);

  // Custom marker icon for POIs
  const createCustomIcon = (type: string) => {
    return L.divIcon({
      className: 'custom-marker',
      html: `<div class="custom-marker-dot ${type}"></div>`,
      iconSize: [20, 20],
      iconAnchor: [10, 10]
    });
  };

  const getMarkerType = (tags: Record<string, any> = {}) => {
    if (tags.amenity) return 'amenity';
    if (tags.tourism) return 'tourism';
    if (tags.shop) return 'shop';
    if (tags.restaurant) return 'restaurant';
    if (tags.hotel) return 'hotel';
    return 'default';
  };

  return (
    <div className={`map-container ${className}`} style={{ height }}>
      <MapContainer
        center={center}
        zoom={zoom}
        className="map-leaflet-container"
        ref={mapRef}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        
        {/* Update map view when props change */}
        <MapUpdater center={center} zoom={zoom} />
        {/* Fit map to route bounds if routes are present */}
        {routes.length > 0 && <FitBoundsToRoute routes={routes} />}
        
        {/* Render markers */}
        {markers.map((marker, index) => (
          <Marker
            key={`marker-${index}`}
            position={[marker.lat, marker.lon]}
            icon={createCustomIcon(getMarkerType(marker.tags))}
          >
            <Popup>
              <div>
                <h4>{marker.name || 'Unnamed location'}</h4>
                {marker.tags && Object.keys(marker.tags).length > 0 && (
                  <div>
                    <strong>Tags:</strong>
                    <ul>
                      {Object.entries(marker.tags).map(([key, value]) => (
                        <li key={key}>{key}: {value}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </Popup>
          </Marker>
        ))}
        
        {/* Render routes */}
        {routes.map((route, index) => (
          <Polyline
            key={`route-${index}`}
            positions={route.geometry.coordinates.map((coord: number[]) => [coord[1], coord[0]])}
            pathOptions={{
              color: "#3388ff",
              weight: 4,
              opacity: 0.8
            }}
          >
            <Popup>
              <div>
                {route.distance_m && (
                  <p><strong>Distance:</strong> {(route.distance_m / 1000).toFixed(2)} km</p>
                )}
                {route.duration_s && (
                  <p><strong>Duration:</strong> {Math.round(route.duration_s / 60)} min</p>
                )}
              </div>
            </Popup>
          </Polyline>
        ))}
        
        {/* Render polygons (isochrones, bounding boxes) */}
        {polygons.map((polygon, index) => (
          <Polygon
            key={`polygon-${index}`}
            positions={polygon.coordinates[0].map((coord: number[]) => [coord[1], coord[0]])}
            pathOptions={{
              color: "#ff6b6b",
              fillColor: "#ff6b6b",
              fillOpacity: 0.3,
              weight: 2
            }}
          >
            <Popup>
              <div>
                {polygon.properties && (
                  <div>
                    {Object.entries(polygon.properties).map(([key, value]) => (
                      <p key={key}><strong>{key}:</strong> {value}</p>
                    ))}
                  </div>
                )}
              </div>
            </Popup>
          </Polygon>
        ))}
      </MapContainer>
    </div>
  );
};

export default Map; 