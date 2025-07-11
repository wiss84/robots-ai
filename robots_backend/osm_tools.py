from langchain_core.tools import tool
from pydantic import BaseModel, Field
import requests
import os
from dotenv import load_dotenv

load_dotenv()
ORS_API_KEY = os.getenv("HeiGIT_API_KEY")

class GeocodeInput(BaseModel):
    address: str = Field(..., description="The address or place name to geocode (e.g., 'Berlin, Germany')")

@tool("osm_geocode", args_schema=GeocodeInput, return_direct=True)
def osm_geocode(address: str) -> dict:
    """
    Geocode an address or place name using OpenStreetMap Nominatim API.
    """
    # Try the original search term first
    url = f'https://nominatim.openstreetmap.org/search?q={address}&format=json&limit=1'
    headers = {"User-Agent": "YourApp/1.0 (your@email.com)"}
    resp = requests.get(url, headers=headers)
    
    if resp.status_code == 200:
        data = resp.json()
        if data:
            result = data[0]
            return {
                "lat": result["lat"],
                "lon": result["lon"],
                "display_name": result["display_name"]
            }
    
    # If original search fails, try with more specific parameters
    url = f'https://nominatim.openstreetmap.org/search?q={address}&format=json&limit=5&addressdetails=1'
    resp = requests.get(url, headers=headers)
    
    if resp.status_code == 200:
        data = resp.json()
        if data:
            # Return the first result
            result = data[0]
            return {
                "lat": result["lat"],
                "lon": result["lon"],
                "display_name": result["display_name"]
            }
    
    return {"error": "No results found"}

class RouteInput(BaseModel):
    start_lat: float = Field(..., description="Start latitude")
    start_lon: float = Field(..., description="Start longitude")
    end_lat: float = Field(..., description="End latitude")
    end_lon: float = Field(..., description="End longitude")
    mode: str = Field('driving', description="Mode of transport: 'driving', 'walking', or 'cycling'")

@tool("osm_route", args_schema=RouteInput, return_direct=True)
def osm_route(start_lat: float, start_lon: float, end_lat: float, end_lon: float, mode: str = 'driving') -> dict:
    """
    Get a route between two points using OSRM (Open Source Routing Machine).
    Use this tool when the user asks to show them the route between two points on the MAP.
    """
    url = f'https://router.project-osrm.org/route/v1/{mode}/{start_lon},{start_lat};{end_lon},{end_lat}?overview=full&geometries=geojson'
    resp = requests.get(url)
    if resp.status_code != 200:
        return {"error": f"OSRM API error: {resp.status_code}"}
    data = resp.json()
    if not data.get('routes'):
        return {"error": "No route found"}
    route = data['routes'][0]
    return {
        "distance_m": route['distance'],
        "duration_s": route['duration'],
        "geometry": route['geometry']
    }

# 1. POI Search Tool
class POISearchInput(BaseModel):
    key: str = Field(..., description="OSM key, e.g., 'amenity', 'tourism', 'shop', 'building', etc.")
    value: str = Field(..., description="OSM value, e.g., 'restaurant', 'hotel', 'supermarket', etc.")
    lat: float = Field(..., description="Latitude of center point")
    lon: float = Field(..., description="Longitude of center point")
    radius: int = Field(1000, description="Search radius in meters")

@tool("osm_poi_search", args_schema=POISearchInput, return_direct=True)
def osm_poi_search(key: str, value: str, lat: float, lon: float, radius: int = 1000) -> dict:
    """
    Search for points of interest (POIs) of a given type within a radius of a point using Overpass API.
    Use this tool when the user asks to show them the nearest restaurants, hotels, etc. on the MAP to a specific location.
    """
    query = f"""
    [out:json][timeout:25];
    node["{key}"="{value}"](around:{radius},{lat},{lon});
    out body;
    """
    url = 'https://overpass-api.de/api/interpreter'
    resp = requests.post(url, data={'data': query})
    if resp.status_code != 200:
        return {"error": f"Overpass API error: {resp.status_code}"}
    data = resp.json()
    pois = [
        {
            "lat": el["lat"],
            "lon": el["lon"],
            "name": el.get("tags", {}).get("name", ""),
            "tags": el.get("tags", {})
        }
        for el in data.get("elements", [])
    ]
    return {"pois": pois}

# 2. Bounding Box/Area Search Tool
class BBoxSearchInput(BaseModel):
    key: str = Field(..., description="OSM key, e.g., 'building', 'amenity', etc.")
    value: str = Field(..., description="OSM value, e.g., 'apartments', 'school', etc.")
    south: float = Field(..., description="South latitude of bounding box (e.g., 54.4464588, use full precision). For center point 54.4474588, use 54.4464588 (center - 0.001)")
    west: float = Field(..., description="West longitude of bounding box (e.g., 18.5673975, use full precision). For center point 18.5683975, use 18.5673975 (center - 0.001)")
    north: float = Field(..., description="North latitude of bounding box (e.g., 54.4484588, use full precision). For center point 54.4474588, use 54.4484588 (center + 0.001)")
    east: float = Field(..., description="East longitude of bounding box (e.g., 18.5693975, use full precision). For center point 18.5683975, use 18.5693975 (center + 0.001)")

@tool("osm_bbox_search", args_schema=BBoxSearchInput, return_direct=True)
def osm_bbox_search(key: str, value: str, south: float, west: float, north: float, east: float) -> dict:
    """
    Search for OSM features of a given type within a bounding box using Overpass API.
    Use this tool when the user asks to show them a specific area on the MAP.
    """
    query = f"""
    [out:json][timeout:25];
    node["{key}"="{value}"]({south},{west},{north},{east});
    out body;
    """
    url = 'https://overpass-api.de/api/interpreter'
    resp = requests.post(url, data={'data': query})
    if resp.status_code != 200:
        return {"error": f"Overpass API error: {resp.status_code}"}
    data = resp.json()
    features = [
        {
            "lat": el["lat"],
            "lon": el["lon"],
            "name": el.get("tags", {}).get("name", ""),
            "tags": el.get("tags", {})
        }
        for el in data.get("elements", [])
    ]
    return {"features": features}

# 3. Custom Overpass Query Tool
class OverpassQueryInput(BaseModel):
    query: str = Field(..., description="Raw Overpass QL query (must return JSON)")

@tool("osm_overpass_query", args_schema=OverpassQueryInput, return_direct=True)
def osm_overpass_query(query: str) -> dict:
    """
    Run a custom Overpass QL query and return the JSON result.
    """
    url = 'https://overpass-api.de/api/interpreter'
    resp = requests.post(url, data={'data': query})
    if resp.status_code != 200:
        return {"error": f"Overpass API error: {resp.status_code}"}
    return resp.json()

# 4. Isochrone Tool (OpenRouteService)
class IsochroneInput(BaseModel):
    lat: float = Field(..., description="Latitude of center point")
    lon: float = Field(..., description="Longitude of center point")
    profile: str = Field('driving-car', description="Profile: 'driving-car', 'cycling-regular', 'foot-walking', etc.")
    range_minutes: int = Field(10, description="Travel time in minutes")

@tool("osm_isochrone", args_schema=IsochroneInput, return_direct=True)
def osm_isochrone(lat: float, lon: float, profile: str = 'driving-car', range_minutes: int = 10) -> dict:
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