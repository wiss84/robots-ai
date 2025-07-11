from langchain_core.tools import tool
from pydantic import BaseModel, Field
import requests
import os
from dotenv import load_dotenv

load_dotenv()
ORS_API_KEY = os.getenv("HeiGIT_API_KEY")

# 1. Geocoding Tool (replaces osm_geocode)
class GeocodeInput(BaseModel):
    address: str = Field(..., description="The address or place name to geocode (e.g., 'Berlin, Germany or a full address')")

@tool("ors_geocode", args_schema=GeocodeInput, return_direct=True)
def ors_geocode(address: str) -> dict:
    """
    Geocode an address or place name using OpenRouteService Geocode Search API.
    """
    if not ORS_API_KEY:
        return {"error": "OpenRouteService API key not set in HeiGIT_API_KEY env variable."}
    
    url = 'https://api.openrouteservice.org/geocode/search'
    headers = {
        'Authorization': ORS_API_KEY,
        'Content-Type': 'application/json'
    }
    params = {
        'api_key': ORS_API_KEY,
        'text': address,
        'size': 1
    }
    
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        return {"error": f"OpenRouteService API error: {resp.status_code} - {resp.text}"}
    
    data = resp.json()
    if data.get('features'):
        feature = data['features'][0]
        coords = feature['geometry']['coordinates']
        return {
            "lat": coords[1],
            "lon": coords[0],
            "display_name": feature['properties'].get('name', address),
            "country": feature['properties'].get('country'),
            "city": feature['properties'].get('city'),
            "street": feature['properties'].get('street')
        }
    
    return {"error": "No results found"}

# 2. Reverse Geocoding Tool
class ReverseGeocodeInput(BaseModel):
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")

@tool("ors_reverse_geocode", args_schema=ReverseGeocodeInput, return_direct=True)
def ors_reverse_geocode(lat: float, lon: float) -> dict:
    """
    Reverse geocode coordinates to get address information using OpenRouteService.
    """
    if not ORS_API_KEY:
        return {"error": "OpenRouteService API key not set in HeiGIT_API_KEY env variable."}
    
    url = 'https://api.openrouteservice.org/geocode/reverse'
    headers = {
        'Authorization': ORS_API_KEY,
        'Content-Type': 'application/json'
    }
    params = {
        'api_key': ORS_API_KEY,
        'point.lon': lon,
        'point.lat': lat,
        'size': 1
    }
    
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        return {"error": f"OpenRouteService API error: {resp.status_code} - {resp.text}"}
    
    data = resp.json()
    if data.get('features'):
        feature = data['features'][0]
        props = feature['properties']
        return {
            "address": props.get('name', ''),
            "country": props.get('country'),
            "city": props.get('city'),
            "street": props.get('street'),
            "postcode": props.get('postcode'),
            "housenumber": props.get('housenumber')
        }
    
    return {"error": "No results found"}

# 3. Routing Tool (replaces osm_route)
class RouteInput(BaseModel):
    start_lat: float = Field(..., description="Start latitude")
    start_lon: float = Field(..., description="Start longitude")
    end_lat: float = Field(..., description="End latitude")
    end_lon: float = Field(..., description="End longitude")
    profile: str = Field('driving-car', description="Profile: 'driving-car', 'cycling-regular', 'foot-walking', 'wheelchair'")

@tool("ors_route", args_schema=RouteInput, return_direct=True)
def ors_route(start_lat: float, start_lon: float, end_lat: float, end_lon: float, profile: str = 'driving-car') -> dict:
    """
    Get a route between two points using OpenRouteService Directions V2 API.
    More reliable than OSRM with better rate limits.
    """
    if not ORS_API_KEY:
        return {"error": "OpenRouteService API key not set in HeiGIT_API_KEY env variable."}
    
    url = f'https://api.openrouteservice.org/v2/directions/{profile}/geojson'
    headers = {
        'Authorization': ORS_API_KEY,
        'Content-Type': 'application/json'
    }
    body = {
        "coordinates": [[start_lon, start_lat], [end_lon, end_lat]],
        "instructions": True,
        "geometry": True
    }
    
    resp = requests.post(url, headers=headers, json=body)
    if resp.status_code != 200:
        return {"error": f"OpenRouteService API error: {resp.status_code} - {resp.text}"}
    
    data = resp.json()
    if data.get('features'):
        feature = data['features'][0]
        properties = feature['properties']
        summary = properties.get('summary', {})
        
        return {
            "distance_m": summary.get('distance', 0),
            "duration_s": summary.get('duration', 0),
            "geometry": feature['geometry'],
            "instructions": properties.get('segments', [])
        }
    
    return {"error": "No route found"}

# 4. POI Search Tool (replaces osm_poi_search)
class POISearchInput(BaseModel):
    lat: float = Field(..., description="Latitude of center point")
    lon: float = Field(..., description="Longitude of center point")
    radius: int = Field(1000, description="Search radius in meters")
    category: str = Field('', description="POI category (e.g., 'restaurant', 'hotel', 'shop', 'school')")

@tool("ors_poi_search", args_schema=POISearchInput, return_direct=True)
def ors_poi_search(lat: float, lon: float, radius: int = 1000, category: str = '') -> dict:
    """
    Search for points of interest (POIs) near a location using OpenRouteService POIs API.
    """
    if not ORS_API_KEY:
        return {"error": "OpenRouteService API key not set in HeiGIT_API_KEY env variable."}
    
    url = 'https://api.openrouteservice.org/pois'
    headers = {
        'Authorization': ORS_API_KEY,
        'Content-Type': 'application/json'
    }
    params = {
        'api_key': ORS_API_KEY,
        'request': 'pois',
        'geometry': f'point({lon} {lat})',
        'radius': radius,
        'limit': 50
    }
    
    if category:
        params['category_group_ids'] = category
    
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        return {"error": f"OpenRouteService API error: {resp.status_code} - {resp.text}"}
    
    data = resp.json()
    pois = []
    for feature in data.get('features', []):
        props = feature['properties']
        pois.append({
            "lat": feature['geometry']['coordinates'][1],
            "lon": feature['geometry']['coordinates'][0],
            "name": props.get('name', ''),
            "category": props.get('category', ''),
            "type": props.get('type', ''),
            "address": props.get('address', {})
        })
    
    return {"pois": pois}

# 5. Matrix Tool (distance/time between multiple points)
class MatrixInput(BaseModel):
    locations: str = Field(..., description="List of coordinates as 'lat1,lon1;lat2,lon2;lat3,lon3'")
    profile: str = Field('driving-car', description="Profile: 'driving-car', 'cycling-regular', 'foot-walking'")

@tool("ors_matrix", args_schema=MatrixInput, return_direct=True)
def ors_matrix(locations: str, profile: str = 'driving-car') -> dict:
    """
    Calculate distance/time matrix between multiple points using OpenRouteService Matrix V2 API.
    Useful for finding nearest locations or optimizing routes.
    """
    if not ORS_API_KEY:
        return {"error": "OpenRouteService API key not set in HeiGIT_API_KEY env variable."}
    
    # Parse locations string
    try:
        coords = []
        for loc in locations.split(';'):
            lat, lon = loc.strip().split(',')
            coords.append([float(lon), float(lat)])  # ORS expects [lon, lat]
    except:
        return {"error": "Invalid locations format. Use 'lat1,lon1;lat2,lon2;lat3,lon3'"}
    
    url = f'https://api.openrouteservice.org/v2/matrix/{profile}'
    headers = {
        'Authorization': ORS_API_KEY,
        'Content-Type': 'application/json'
    }
    body = {
        "locations": coords,
        "metrics": ["distance", "duration"]
    }
    
    resp = requests.post(url, headers=headers, json=body)
    if resp.status_code != 200:
        return {"error": f"OpenRouteService API error: {resp.status_code} - {resp.text}"}
    
    data = resp.json()
    return {
        "distances": data.get('distances', []),
        "durations": data.get('durations', [])
    }

class IsochroneInput(BaseModel):
    lat: float = Field(..., description="Latitude of center point")
    lon: float = Field(..., description="Longitude of center point")
    profile: str = Field('driving-car', description="Profile: 'driving-car', 'cycling-regular', 'foot-walking', etc.")
    range_minutes: int = Field(10, description="Travel time in minutes")

@tool("ors_isochrone", args_schema=IsochroneInput, return_direct=True)
def ors_isochrone(lat: float, lon: float, profile: str = 'driving-car', range_minutes: int = 10) -> dict:
    """
    Get an isochrone (area reachable within X minutes) from a point using OpenRouteService.
    """
    if not ORS_API_KEY:
        return {"error": "OpenRouteService API key not set in HeiGIT_API_KEY env variable."}
    url = 'https://api.openrouteservice.org/v2/isochrones/' + profile
    headers = {
        'Authorization': ORS_API_KEY,
        'Content-Type': 'application/json'
    }
    body = {
        "locations": [[lon, lat]],
        "range": [range_minutes * 60],
        "units": "m"
    }
    resp = requests.post(url, headers=headers, json=body)
    if resp.status_code != 200:
        return {"error": f"OpenRouteService API error: {resp.status_code} - {resp.text}"}
    return resp.json()

# 7. Elevation Tool
class ElevationInput(BaseModel):
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")

@tool("ors_elevation", args_schema=ElevationInput, return_direct=True)
def ors_elevation(lat: float, lon: float) -> dict:
    """
    Get elevation data for a point using OpenRouteService Elevation Point API.
    """
    if not ORS_API_KEY:
        return {"error": "OpenRouteService API key not set in HeiGIT_API_KEY env variable."}
    
    url = 'https://api.openrouteservice.org/elevation/point'
    headers = {
        'Authorization': ORS_API_KEY,
        'Content-Type': 'application/json'
    }
    params = {
        'api_key': ORS_API_KEY,
        'format_in': 'point',
        'format_out': 'point',
        'dataset': 'srtm',
        'point': f'{lon},{lat}'
    }
    
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        return {"error": f"OpenRouteService API error: {resp.status_code} - {resp.text}"}
    
    data = resp.json()
    if data.get('geometry', {}).get('coordinates'):
        coords = data['geometry']['coordinates']
        return {
            "lat": coords[1],
            "lon": coords[0],
            "elevation_m": coords[2]
        }
    
    return {"error": "No elevation data found"} 