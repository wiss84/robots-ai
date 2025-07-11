// Types for map data parsing
export interface ParsedMapData {
  center?: [number, number];
  zoom?: number;
  markers: MapPoint[];
  routes: MapRoute[];
  polygons: MapPolygon[];
}

export interface MapPoint {
  lat: number;
  lon: number;
  name?: string;
  tags?: Record<string, any>;
}

export interface MapRoute {
  geometry: any;
  distance_m?: number;
  duration_s?: number;
}

export interface MapPolygon {
  coordinates: number[][][];
  properties?: Record<string, any>;
}

/**
 * Calculate optimal zoom level and center for a set of coordinates
 */
function calculateMapBounds(coordinates: number[][]): { center: [number, number]; zoom: number } {
  if (coordinates.length === 0) {
    return { center: [0, 0], zoom: 2 };
  }

  let minLat = Infinity, maxLat = -Infinity;
  let minLon = Infinity, maxLon = -Infinity;

  coordinates.forEach(coord => {
    const lat = coord[1];
    const lon = coord[0];
    minLat = Math.min(minLat, lat);
    maxLat = Math.max(maxLat, lat);
    minLon = Math.min(minLon, lon);
    maxLon = Math.max(maxLon, lon);
  });

  const center: [number, number] = [(minLat + maxLat) / 2, (minLon + maxLon) / 2];
  
  // Calculate zoom level based on the span of coordinates
  const latSpan = maxLat - minLat;
  const lonSpan = maxLon - minLon;
  const maxSpan = Math.max(latSpan, lonSpan);
  
  let zoom = 13; // Default zoom
  if (maxSpan > 10) zoom = 4;
  else if (maxSpan > 5) zoom = 6;
  else if (maxSpan > 2) zoom = 8;
  else if (maxSpan > 1) zoom = 10;
  else if (maxSpan > 0.5) zoom = 12;
  else if (maxSpan > 0.1) zoom = 14;
  else zoom = 16;

  return { center, zoom };
}

/**
 * Parse map data from agent responses
 * This function looks for specific patterns in the response text and extracts map data
 */
export function parseMapDataFromResponse(response: string): ParsedMapData | null {
  const result: ParsedMapData = {
    markers: [],
    routes: [],
    polygons: []
  };

  try {
    // Look for JSON blocks in the response
    const jsonMatches = response.match(/```json\s*([\s\S]*?)\s*```/g);
    if (jsonMatches) {
      for (const match of jsonMatches) {
        if (match.length > 500000) {
          throw new Error('Map data block is too large to parse.');
        }
        const jsonContent = match.replace(/```json\s*/, '').replace(/\s*```/, '');
        
        // Clean the JSON content - remove trailing characters that might cause parsing errors
        let cleanedJson = jsonContent.trim();
        
        // Try to find the end of valid JSON by looking for balanced braces
        let braceCount = 0;
        let validJsonEnd = 0;
        
        for (let i = 0; i < cleanedJson.length; i++) {
          if (cleanedJson[i] === '{') {
            braceCount++;
          } else if (cleanedJson[i] === '}') {
            braceCount--;
            if (braceCount === 0) {
              validJsonEnd = i + 1;
              break;
            }
          }
        }
        
        if (validJsonEnd > 0) {
          cleanedJson = cleanedJson.substring(0, validJsonEnd);
        }
        
        const data = JSON.parse(cleanedJson);
        
        // Parse POI search results
        if (data.pois && Array.isArray(data.pois)) {
          result.markers.push(...data.pois.map((poi: any) => ({
            lat: parseFloat(poi.lat),
            lon: parseFloat(poi.lon),
            name: poi.name || '',
            tags: poi.tags || {}
          })));
        }
        
        // Parse bounding box search results
        if (data.features && Array.isArray(data.features)) {
          result.markers.push(...data.features.map((feature: any) => ({
            lat: parseFloat(feature.lat),
            lon: parseFloat(feature.lon),
            name: feature.name || '',
            tags: feature.tags || {}
          })));
        }
        
        // Parse route data
        if (data.geometry && data.geometry.coordinates) {
          result.routes.push({
            geometry: data.geometry,
            distance_m: data.distance_m,
            duration_s: data.duration_s
          });
          
          // Calculate optimal center and zoom for routes
          const bounds = calculateMapBounds(data.geometry.coordinates);
          result.center = bounds.center;
          result.zoom = bounds.zoom;
        }
        
        // Parse isochrone data
        if (data.features && Array.isArray(data.features)) {
          for (const feature of data.features) {
            if (feature.geometry && feature.geometry.type === 'Polygon') {
              result.polygons.push({
                coordinates: feature.geometry.coordinates,
                properties: feature.properties || {}
              });
            }
          }
        }
      }
    }

    // If we found any data, calculate center point
    if (result.markers.length > 0 || result.routes.length > 0 || result.polygons.length > 0) {
      let totalLat = 0;
      let totalLon = 0;
      let count = 0;

      // Use markers for center calculation
      result.markers.forEach(marker => {
        totalLat += marker.lat;
        totalLon += marker.lon;
        count++;
      });

      // Use route start/end points if no markers
      if (count === 0 && result.routes.length > 0) {
        const route = result.routes[0];
        if (route.geometry.coordinates.length >= 2) {
          const start = route.geometry.coordinates[0];
          const end = route.geometry.coordinates[route.geometry.coordinates.length - 1];
          // OSM coordinates are [lon, lat] format, so start[0] is lon, start[1] is lat
          totalLat = (start[1] + end[1]) / 2;
          totalLon = (start[0] + end[0]) / 2;
          count = 2;
        }
      }

      // Use polygon center if no markers or routes
      if (count === 0 && result.polygons.length > 0) {
        const polygon = result.polygons[0];
        if (polygon.coordinates[0] && polygon.coordinates[0].length > 0) {
          const coords = polygon.coordinates[0];
          let sumLat = 0;
          let sumLon = 0;
          for (const coord of coords) {
            sumLat += coord[1]; // lat
            sumLon += coord[0]; // lon
          }
          totalLat = sumLat / coords.length;
          totalLon = sumLon / coords.length;
          count = 1;
        }
      }

      if (count > 0) {
        result.center = [totalLat / count, totalLon / count];
      }
    }

    // Return null if no data was found
    return (result.markers.length > 0 || result.routes.length > 0 || result.polygons.length > 0) ? result : null;
  } catch (error) {
    console.error('Error parsing map data:', error);
    return null;
  }
}

/**
 * Extract coordinates from geocoding results
 */
export function parseGeocodeResult(response: string): [number, number] | null {
  try {
    const jsonMatches = response.match(/```json\s*([\s\S]*?)\s*```/g);
    if (jsonMatches) {
      for (const match of jsonMatches) {
        const jsonContent = match.replace(/```json\s*/, '').replace(/\s*```/, '');
        const data = JSON.parse(jsonContent);
        
        if (data.lat && data.lon) {
          return [parseFloat(data.lat), parseFloat(data.lon)];
        }
      }
    }
    return null;
  } catch (error) {
    console.error('Error parsing geocode result:', error);
    return null;
  }
} 