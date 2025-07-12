import React, { useState } from 'react';
import Map from './Map';
import { parseMapDataFromResponse } from '../utils/mapDataParser';
import type { ParsedMapData } from '../utils/mapDataParser';
import './MapMessage.css';

interface MapMessageProps {
  message: string;
  className?: string;
}

const MapMessage: React.FC<MapMessageProps> = ({ message, className = '' }) => {
  const [isMinimized, setIsMinimized] = useState(false);
  let mapData: ParsedMapData | null = null;
  let mapError: string | null = null;
  
  console.log('MapMessage received message:', message.substring(0, 200) + '...');
  
  try {
    mapData = parseMapDataFromResponse(message);
    console.log('Parsed map data:', mapData);
    
    if (mapData && JSON.stringify(mapData).length > 500000) {
      mapError = 'Map data is too large to display. Please refine your request.';
      mapData = null;
    }
  } catch (e) {
    console.error('Error parsing map data:', e);
    mapError = 'There was an error displaying the map. Please try again or rephrase your request.';
    mapData = null;
  }

  if (mapError) {
    console.log('Map error:', mapError);
    return <div className={`map-message map-error ${className}`}>{mapError}</div>;
  }

  if (!mapData) {
    console.log('No map data found in message');
    return null; // Don't render anything if no map data found
  }

  const toggleMinimize = () => {
    setIsMinimized(!isMinimized);
  };

  return (
    <div className={`map-message ${className} ${isMinimized ? 'minimized' : ''}`}>
      <div className="map-header">
        <div className="map-header-content">
          <h4>📍 Interactive Map</h4>
          <p>Showing results from your query</p>
        </div>
        <div className="map-controls">
          <button 
            className="map-control-btn minimize-btn"
            onClick={toggleMinimize}
            title={isMinimized ? "Restore" : "Minimize"}
          >
            {isMinimized ? (
              // Restore icon (square with arrow)
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            ) : (
              // Minimize icon (minus)
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            )}
          </button>
        </div>
      </div>
      
      <div className="map-content">
        <Map
          center={mapData.center}
          zoom={mapData.zoom || (mapData.markers.length > 0 ? 14 : 12)}
          markers={mapData.markers}
          routes={mapData.routes}
          polygons={mapData.polygons}
          height={isMinimized ? "60px" : "400px"}
          className="map-message-container"
        />
      </div>
      
      {!isMinimized && (
        <div className="map-summary">
          {mapData.markers.length > 0 && (
            <span className="map-stat">
              📍 {mapData.markers.length} location{mapData.markers.length !== 1 ? 's' : ''}
            </span>
          )}
          {mapData.routes.length > 0 && (
            <span className="map-stat">
              🛣️ {mapData.routes.length} route{mapData.routes.length !== 1 ? 's' : ''}
            </span>
          )}
          {mapData.polygons.length > 0 && (
            <span className="map-stat">
              🗺️ {mapData.polygons.length} area{mapData.polygons.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      )}
    </div>
  );
};

export default MapMessage; 