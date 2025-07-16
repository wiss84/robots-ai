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
 * Robust JSON extraction function that handles various formats
 */
function extractJsonFromResponse(response: string): any[] {
  const results: any[] = [];
  
  try {
    // Method 1: Look for properly wrapped JSON blocks
    const jsonBlockMatches = response.match(/```json\s*([\s\S]*?)\s*```/g);
    if (jsonBlockMatches) {
      for (const match of jsonBlockMatches) {
        try {
          const jsonContent = match.replace(/```json\s*/, '').replace(/\s*```/, '').trim();
          const cleanedJson = extractValidJson(jsonContent);
          if (cleanedJson) {
            const data = JSON.parse(cleanedJson);
            results.push(data);
          }
        } catch (error) {
          console.warn('Failed to parse JSON block:', error);
        }
      }
    }
    
    // Method 2: Look for unwrapped JSON objects (starts with { and ends with })
    const unwrappedJsonMatches = response.match(/\{[^{}]*(\{[^{}]*\}[^{}]*)*\}/g);
    if (unwrappedJsonMatches) {
      for (const match of unwrappedJsonMatches) {
        try {
          const cleanedJson = extractValidJson(match);
          if (cleanedJson) {
            const data = JSON.parse(cleanedJson);
            // Only add if it looks like map data (has relevant properties)
            if (isMapData(data)) {
              results.push(data);
            }
          }
        } catch (error) {
          console.warn('Failed to parse unwrapped JSON:', error);
        }
      }
    }
    
    // Method 3: Look for JSON-like structures that might be malformed
    const potentialJsonMatches = response.match(/\{[^}]*"geometry"[^}]*\}/g);
    if (potentialJsonMatches) {
      for (const match of potentialJsonMatches) {
        try {
          const cleanedJson = extractValidJson(match);
          if (cleanedJson) {
            const data = JSON.parse(cleanedJson);
            if (isMapData(data)) {
              results.push(data);
            }
          }
        } catch (error) {
          console.warn('Failed to parse potential JSON:', error);
        }
      }
    }
    
    // Method 4: Look for JSON with route data patterns
    const routeJsonMatches = response.match(/\{[^}]*"coordinates"[^}]*\}/g);
    if (routeJsonMatches) {
      for (const match of routeJsonMatches) {
        try {
          const cleanedJson = extractValidJson(match);
          if (cleanedJson) {
            const data = JSON.parse(cleanedJson);
            if (isMapData(data)) {
              results.push(data);
            }
          }
        } catch (error) {
          console.warn('Failed to parse route JSON:', error);
        }
      }
    }
    
    // Method 5: Look for JSON with POI data patterns
    const poiJsonMatches = response.match(/\{[^}]*"pois"[^}]*\}/g);
    if (poiJsonMatches) {
      for (const match of poiJsonMatches) {
        try {
          const cleanedJson = extractValidJson(match);
          if (cleanedJson) {
            const data = JSON.parse(cleanedJson);
            if (isMapData(data)) {
              results.push(data);
            }
          }
        } catch (error) {
          console.warn('Failed to parse POI JSON:', error);
        }
      }
    }
    
    // Method 6: Look for any JSON object that might contain map data
    const anyJsonMatches = response.match(/\{[^}]*\}/g);
    if (anyJsonMatches) {
      for (const match of anyJsonMatches) {
        try {
          const cleanedJson = extractValidJson(match);
          if (cleanedJson) {
            const data = JSON.parse(cleanedJson);
            if (isMapData(data)) {
              results.push(data);
            }
          }
        } catch (error) {
          console.warn('Failed to parse any JSON:', error);
        }
      }
    }
    
  } catch (error) {
    console.error('Error in JSON extraction:', error);
  }
  
  return results;
}

/**
 * Extract valid JSON from potentially malformed JSON string
 */
function extractValidJson(jsonString: string): string | null {
  let cleanedJson = jsonString.trim();
  
  // Remove any leading/trailing non-JSON characters
  cleanedJson = cleanedJson.replace(/^[^{]*/, '');
  cleanedJson = cleanedJson.replace(/[^}]*$/, '');
  
  // Try to find balanced braces
  let braceCount = 0;
  let validJsonEnd = 0;
  let inString = false;
  let escapeNext = false;
  
  for (let i = 0; i < cleanedJson.length; i++) {
    const char = cleanedJson[i];
    
    if (escapeNext) {
      escapeNext = false;
      continue;
    }
    
    if (char === '\\') {
      escapeNext = true;
      continue;
    }
    
    if (char === '"' && !escapeNext) {
      inString = !inString;
      continue;
    }
    
    if (!inString) {
      if (char === '{') {
        braceCount++;
      } else if (char === '}') {
        braceCount--;
        if (braceCount === 0) {
          validJsonEnd = i + 1;
          break;
        }
      }
    }
  }
  
  if (validJsonEnd > 0) {
    cleanedJson = cleanedJson.substring(0, validJsonEnd);
  }
  
  // Basic validation
  if (cleanedJson.startsWith('{') && cleanedJson.endsWith('}')) {
    return cleanedJson;
  }
  
  return null;
}

/**
 * Check if the parsed data looks like map data
 */
function isMapData(data: any): boolean {
  return (
    (data.geometry && data.geometry.coordinates) ||
    (data.pois && Array.isArray(data.pois)) ||
    (data.features && Array.isArray(data.features)) ||
    (data.lat && data.lon) ||
    (data.coordinates && Array.isArray(data.coordinates))
  );
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
    console.log('Parsing map data from response:', response.substring(0, 200) + '...');
    
    const jsonData = extractJsonFromResponse(response);
    console.log('Extracted JSON data count:', jsonData.length);

    for (const data of jsonData) {
      console.log('Processing JSON data:', Object.keys(data));
      
      // Parse POI search results
      if (data.pois && Array.isArray(data.pois)) {
        console.log('Found POI data with', data.pois.length, 'points');
        result.markers.push(...data.pois.map((poi: any) => ({
          lat: parseFloat(poi.lat),
          lon: parseFloat(poi.lon),
          name: poi.name || '',
          tags: poi.tags || {}
        })));
      }
      
      // Parse markers (newly supported)
      if (data.markers && Array.isArray(data.markers)) {
        console.log('Found markers data with', data.markers.length, 'points');
        result.markers.push(...data.markers.map((marker: any) => ({
          lat: parseFloat(marker.lat),
          lon: parseFloat(marker.lon),
          name: marker.name || '',
          tags: marker.tags || {}
        })));
      }
      
      // Parse bounding box search results
      if (data.features && Array.isArray(data.features)) {
        console.log('Found features data with', data.features.length, 'features');
        result.markers.push(...data.features.map((feature: any) => ({
          lat: parseFloat(feature.lat),
          lon: parseFloat(feature.lon),
          name: feature.name || '',
          tags: feature.tags || {}
        })));
      }
      
      // Parse route data
      if (data.geometry && data.geometry.coordinates) {
        console.log('Found route data with', data.geometry.coordinates.length, 'coordinates');
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
            console.log('Found polygon data');
            result.polygons.push({
              coordinates: feature.geometry.coordinates,
              properties: feature.properties || {}
            });
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
    const jsonData = extractJsonFromResponse(response);
    
    for (const data of jsonData) {
      if (data.lat && data.lon) {
        return [parseFloat(data.lat), parseFloat(data.lon)];
      }
    }
    
    return null;
  } catch (error) {
    console.error('Error parsing geocode result:', error);
    return null;
  }
} 

/**
 * Auto-wrap unwrapped JSON responses in proper format
 */
export function autoWrapJsonResponse(response: string): string {
  // If response already has proper JSON blocks, return as is
  if (response.includes('```json')) {
    return response;
  }
  
  // Look for unwrapped JSON objects
  const jsonMatches = response.match(/\{[^{}]*(\{[^{}]*\}[^{}]*)*\}/g);
  if (jsonMatches) {
    let modifiedResponse = response;
    
    for (const match of jsonMatches) {
      try {
        const cleanedJson = extractValidJson(match);
        if (cleanedJson) {
          const data = JSON.parse(cleanedJson);
          if (isMapData(data)) {
            // Replace the unwrapped JSON with properly wrapped JSON
            const wrappedJson = `\n\`\`\`json\n${cleanedJson}\n\`\`\`\n`;
            modifiedResponse = modifiedResponse.replace(match, wrappedJson);
          }
        }
      } catch (error) {
        console.warn('Failed to wrap JSON:', error);
      }
    }
    
    return modifiedResponse;
  }
  
  return response;
} 