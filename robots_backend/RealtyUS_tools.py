from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool
import os
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path="robots_backend/.env")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

class RealtyUSSearchBuyInput(BaseModel):
    """
    Input schema for RealtyUSSearchBuyTool.
    """
    location: str = Field(..., description="Search location. Format: 'city:City Name, ST' (e.g., 'city:New York, NY'). Case-sensitive and must match exactly.")
    resultsPerPage: Optional[int] = Field(8, ge=8, le=200, description="Number of results per page (8–200). Default is 8. keep it as 8 always ")
    page: Optional[int] = Field(1, ge=1, description="Page number for pagination. Default is 1. if the user wants to see more results, they can increase the page number.")
    sortBy: Optional[str] = Field('relevance', description="Sort order. One of: 'relevance', 'newest', 'lowest_price', 'highest_price', 'open_house_date', 'price_reduced', 'largest_squarefoot', 'photo_count'. Default is 'relevance'.")
    propertyType: Optional[str] = Field(None, description="Comma-separated property types. E.g., 'condo,co_op'. Options: 'condo', 'co_op', 'cond_op', 'townhome', 'single_family_home', 'multi_family', 'mobile_mfd', 'farm_ranch', 'land'.")
    prices: Optional[str] = Field(None, description="Price range as 'min,max', 'min,', or ',max'.")
    bedrooms: Optional[int] = Field(None, ge=0, le=5, description="Minimum number of bedrooms (0–5).")
    bathrooms: Optional[int] = Field(None, ge=1, le=5, description="Minimum number of bathrooms (1–5).")

@tool("realty_us_search_buy", args_schema=RealtyUSSearchBuyInput, return_direct=True)
def realty_us_search_buy(
    location: str,
    resultsPerPage: int = 8,
    page: int = 1,
    sortBy: str = 'relevance',
    propertyType: Optional[str] = None,
    prices: Optional[str] = None,
    bedrooms: Optional[int] = None,
    bathrooms: Optional[int] = None,
) -> dict:
    """
    Search for properties listed for sale in the US only, using the Realty-US API. Returns a list of properties and their details.
    """
    url = "https://realty-us.p.rapidapi.com/properties/search-buy"
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "realty-us.p.rapidapi.com"
    }
    payload = {
        "location": location,
        "resultsPerPage": resultsPerPage,
        "page": page,
        "sortBy": sortBy,
        "hidePendingContingent": True,
        "hideHomesNotYetBuilt": True,
        "hideForeclosures": True
    }
    if propertyType:
        payload["propertyType"] = propertyType
    if prices:
        payload["prices"] = prices
    if bedrooms is not None:
        payload["bedrooms"] = bedrooms
    if bathrooms is not None:
        payload["bathrooms"] = bathrooms
    response = requests.get(url, headers=headers, params=payload)
    response.raise_for_status()
    data = response.json()
    results = data.get("data", {}).get("results", [])
    simplified = []
    for prop in results:
        address = prop.get("location", {}).get("address", {}).get("line")
        price = prop.get("list_price")
        beds = prop.get("description", {}).get("beds")
        baths = prop.get("description", {}).get("baths")
        main_photo = prop.get("primary_photo", {}).get("href")
        all_photos = [p.get("href") for p in prop.get("photos", []) if p.get("href")]
        listing_url = prop.get("href")
        coordinates = prop.get("location", {}).get("address", {}).get("coordinate")
        list_date = prop.get("list_date")
        simplified.append({
            "address": address,
            "price": price,
            "beds": beds,
            "baths": baths,
            "main_photo": main_photo,
            "all_photos": all_photos,
            "listing_url": listing_url,
            "coordinates": coordinates,
            "list_date": list_date
        })
    return {"results": simplified}

class RealtyUSSearchRentInput(BaseModel):
    """
    Input schema for RealtyUSSearchRentTool.
    """
    location: str = Field(..., description="Search location. Format: 'city:City Name, ST' (e.g., 'city:New York, NY'). Case-sensitive and must match exactly.")
    resultsPerPage: Optional[int] = Field(8, ge=8, le=200, description="Number of results per page (8–200). Default is 8. keep it as 8 always ")
    page: Optional[int] = Field(1, ge=1, description="Page number for pagination. Default is 1. if the user wants to see more results, they can increase the page number.")
    sortBy: Optional[str] = Field('relevance', description="Sort order. One of: 'relevance', 'newest', 'lowest_price', 'highest_price', 'open_house_date', 'price_reduced', 'largest_squarefoot', 'photo_count'. Default is 'relevance'.")
    propertyType: Optional[str] = Field(None, description="Comma-separated property types. E.g., 'condo,co_op'. Options: 'condo', 'co_op', 'cond_op', 'townhome', 'single_family_home', 'multi_family', 'mobile_mfd', 'farm_ranch', 'land'.")
    prices: Optional[str] = Field(None, description="Price range as 'min,max', 'min,', or ',max'.")
    bedrooms: Optional[int] = Field(None, ge=0, le=5, description="Minimum number of bedrooms (0–5).")
    bathrooms: Optional[int] = Field(None, ge=1, le=5, description="Minimum number of bathrooms (1–5).")
    pets: Optional[str] = Field(None, description="Comma-separated pet options. E.g., 'cats,dogs'. Options: 'cats', 'dogs', 'no_pets_allowed'.")

@tool("realty_us_search_rent", args_schema=RealtyUSSearchRentInput, return_direct=True)
def realty_us_search_rent(
    location: str,
    resultsPerPage: int = 8,
    page: int = 1,
    sortBy: str = 'relevance',
    propertyType: Optional[str] = None,
    prices: Optional[str] = None,
    bedrooms: Optional[int] = None,
    bathrooms: Optional[int] = None,
    pets: Optional[str] = None,
) -> dict:
    """
    Search for properties listed for rent in the US only, using the Realty-US API. Returns a list of rental properties and their details.
    """
    url = "https://realty-us.p.rapidapi.com/properties/search-rent"
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "realty-us.p.rapidapi.com"
    }
    payload = {
        "location": location,
        "resultsPerPage": resultsPerPage,
        "page": page,
        "sortBy": sortBy
    }
    if propertyType:
        payload["propertyType"] = propertyType
    if prices:
        payload["prices"] = prices
    if bedrooms is not None:
        payload["bedrooms"] = bedrooms
    if bathrooms is not None:
        payload["bathrooms"] = bathrooms
    if pets:
        payload["pets"] = pets
    response = requests.get(url, headers=headers, params=payload)
    response.raise_for_status()
    data = response.json()
    results = data.get("data", {}).get("results", [])
    simplified = []
    for prop in results:
        address = prop.get("location", {}).get("address", {}).get("line")
        price = prop.get("list_price")
        beds = prop.get("description", {}).get("beds")
        baths = prop.get("description", {}).get("baths")
        main_photo = prop.get("primary_photo", {}).get("href")
        all_photos = [p.get("href") for p in prop.get("photos", []) if p.get("href")]
        listing_url = prop.get("href")
        coordinates = prop.get("location", {}).get("address", {}).get("coordinate")
        list_date = prop.get("list_date")
        simplified.append({
            "address": address,
            "price": price,
            "beds": beds,
            "baths": baths,
            "main_photo": main_photo,
            "all_photos": all_photos,
            "listing_url": listing_url,
            "coordinates": coordinates,
            "list_date": list_date
        })
    return {"results": simplified} 