# Import Pydantic for schema definition
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from composio import Composio
import os
from composio_langchain import LangchainProvider
from dotenv import load_dotenv
load_dotenv()


# Get Composio tools
composio = Composio(api_key=os.getenv('COMPOSIO_API_KEY'), allow_tracking=False, timeout=60, provider=LangchainProvider())
image_search_tools = composio.tools.get(user_id=os.getenv('COMPOSIO_USER_ID'), tools=["COMPOSIO_SEARCH_IMAGE_SEARCH"])
google_search = composio.tools.get(user_id=os.getenv('COMPOSIO_USER_ID'), tools=["COMPOSIO_SEARCH_SEARCH"])
google_maps_search = composio.tools.get(user_id=os.getenv('COMPOSIO_USER_ID'), tools=["COMPOSIO_SEARCH_GOOGLE_MAPS_SEARCH"])
news_search_tools = composio.tools.get(user_id=os.getenv('COMPOSIO_USER_ID'), tools=["COMPOSIO_SEARCH_NEWS_SEARCH"])
shopping_tools = composio.tools.get(user_id=os.getenv('COMPOSIO_USER_ID'), tools=["COMPOSIO_SEARCH_SHOPPING_SEARCH"])

# -------------------------------------- Google Search Image Tool --------------------------------------

# Input schema for the filtered image search tool
class FilteredImageSearchInput(BaseModel):
    query: str = Field(description="The search query for finding images")
    num_results: int = Field(default=5, description="Number of image results to return (1-100)")

# Custom wrapper for filtered image search
def filtered_image_search(query: str, num_results: int = 5) -> dict:
    """Wrapper that filters COMPOSIO_SEARCH_IMAGE_SEARCH results to reduce token usage"""
    # Get the raw tool
    raw_tool = None
    for tool_item in image_search_tools:
        if tool_item.name == "COMPOSIO_SEARCH_IMAGE_SEARCH":
            raw_tool = tool_item
            break

    if not raw_tool:
        return {"error": "COMPOSIO_SEARCH_IMAGE_SEARCH tool not found", "successful": False}

    try:
        # Call the original tool using the tool's invoke method instead of func
        if hasattr(raw_tool, 'invoke'):
            result = raw_tool.invoke({"query": query})
        else:
            # Fallback to direct function call if invoke doesn't work
            result = raw_tool.func(query)

        # Extract only what we need - much cleaner approach!
        if isinstance(result, dict) and "data" in result:
            data = result["data"]

            # Extract the specified number of image results (default 5, max 100)
            if "results" in data and "images_results" in data["results"]:
                # Ensure num_results is within reasonable bounds (1-100)
                num_results = max(1, min(num_results, 100))
                limited_images = data["results"]["images_results"][:num_results]

                # Filter each image to only include 'link' and 'original' keys
                filtered_images = []
                for image in limited_images:
                    if isinstance(image, dict):
                        # Only keep the essential keys
                        essential_keys = ["link", "original"]
                        filtered_image = {key: image[key] for key in essential_keys if key in image}
                        filtered_images.append(filtered_image)

                # Return ultra-clean structure with only essential data
                return {
                    "data": {
                        "results": {
                            "images_results": filtered_images
                        }
                    },
                    "successful": True
                }
            else:
                return {"error": "No image results found in response", "successful": False}
        else:
            return {"error": "Invalid response structure from tool", "successful": False}

    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}", "successful": False}

# Create the custom tool
@tool("filtered_composio_image_search", args_schema=FilteredImageSearchInput, return_direct=True)
def filtered_composio_image_search(query: str, num_results: int = 5) -> dict:
    """Search for images using Composio with filtered results to reduce token usage.
    Returns the specified number of results (default 5) with only essential data."""
    return filtered_image_search(query, num_results)

# --------------------------------------  Google Search Tool --------------------------------------

# Input schema for the filtered google search tool
class FilteredGoogleSearchInput(BaseModel):
    query: str = Field(description="The search query")
    num_results: int = Field(default=10, description="Number of results to return (1-10)")

# Custom wrapper for filtered search
def filtered_google_search(query: str, num_results: int = 10) -> dict:
    """Wrapper that filters COMPOSIO_SEARCH_SEARCH results to reduce token usage"""
    # Get the raw tool
    raw_tool = None
    for tool_item in google_search:
        if tool_item.name == "COMPOSIO_SEARCH_SEARCH":
            raw_tool = tool_item
            break

    if not raw_tool:
        return {"error": "COMPOSIO_SEARCH_SEARCH tool not found", "successful": False}

    try:
        # Call the original tool using the tool's invoke method instead of func
        if hasattr(raw_tool, 'invoke'):
            result = raw_tool.invoke({"query": query})
        else:
            # Fallback to direct function call if invoke doesn't work
            result = raw_tool.func(query)

        # Extract only what we need - much cleaner approach!
        if isinstance(result, dict) and "data" in result:
            data = result["data"]

            # Ensure num_results is within reasonable bounds (1-10)
            num_results = max(1, min(num_results, 10))

            filtered_results = {}

            # Filter inline_videos results if they exist
            if "results" in data and "inline_videos" in data["results"]:
                limited_videos = data["results"]["inline_videos"][:num_results]
                filtered_videos = []
                for video in limited_videos:
                    if isinstance(video, dict):
                        # Keep essential keys for videos
                        essential_keys = ["channel", "link", "platform", "title"]
                        filtered_video = {key: video[key] for key in essential_keys if key in video}
                        filtered_videos.append(filtered_video)
                filtered_results["inline_videos"] = filtered_videos

            # Filter organic_results if they exist
            if "results" in data and "organic_results" in data["results"]:
                limited_organic = data["results"]["organic_results"][:num_results]
                filtered_organic = []
                for organic in limited_organic:
                    if isinstance(organic, dict):
                        # Keep essential keys for organic results
                        essential_keys = ["date", "link", "snippet", "source", "title"]
                        filtered_organic_result = {key: organic[key] for key in essential_keys if key in organic}
                        filtered_organic.append(filtered_organic_result)
                filtered_results["organic_results"] = filtered_organic

            if filtered_results:
                # Return ultra-clean structure with only essential data
                return {
                    "data": {
                        "results": filtered_results
                    },
                    "successful": True
                }
            else:
                return {"error": "No inline_videos or organic_results found in response", "successful": False}
        else:
            return {"error": "Invalid response structure from tool", "successful": False}

    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}", "successful": False}

# Create the custom tool
@tool("filtered_composio_google_search", args_schema=FilteredGoogleSearchInput, return_direct=True)
def filtered_composio_google_search(query: str, num_results: int = 10) -> dict:
    """Search for information using Composio with filtered results to reduce token usage.
    Returns the specified number of results (default 10) with only essential data."""
    return filtered_google_search(query, num_results)

# -------------------------------------- Google Maps Search Tool --------------------------------------

# Input schema for the filtered google maps search tool
class FilteredGoogleMapsSearchInput(BaseModel):
    query: str = Field(description="Search query consisting of a specific place name followed by city and country (e.g., 'Eiffel Tower Paris France' or 'Central Park New York USA')")

# Custom wrapper for filtered google maps search
def filtered_google_maps_search(query: str) -> dict:
    """Wrapper that filters COMPOSIO_SEARCH_GOOGLE_MAPS_SEARCH results to reduce token usage"""
    # Get the raw tool
    raw_tool = None
    for tool_item in google_maps_search:
        if tool_item.name == "COMPOSIO_SEARCH_GOOGLE_MAPS_SEARCH":
            raw_tool = tool_item
            break

    if not raw_tool:
        return {"error": "COMPOSIO_SEARCH_GOOGLE_MAPS_SEARCH tool not found", "successful": False}

    try:
        # Call the original tool
        if hasattr(raw_tool, 'invoke'):
            result = raw_tool.invoke({"q": query})
        else:
            result = raw_tool.func(q=query)

        # Navigate to place_results
        if not isinstance(result, dict) or "data" not in result:
            return {"error": "Invalid response structure from tool", "successful": False}

        data = result["data"]
        
        # Handle both response structures
        place_results = None
        if isinstance(data, dict) and "results" in data:
            place_results = data["results"].get("place_results")
        
        if not place_results:
            return {"error": "No place_results found in response", "successful": False}

        # place_results is a dict with the hotel/place info, not a list
        if isinstance(place_results, dict):
            filtered_place = _filter_place(place_results)
            return {
                "data": {
                    "results": {
                        "place_results": filtered_place
                    }
                },
                "successful": True
            }
        else:
            return {"error": "Unexpected place_results structure", "successful": False}

    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}", "successful": False}


def _filter_place(place: dict) -> dict:
    """Filter a single place dict to keep only essential information"""
    # Essential top-level keys
    essential_keys = [
        "title", "type", "address", "phone", "rating", "reviews",
        "description", "amenities", "gps_coordinates"
    ]
    
    filtered_place = {key: place[key] for key in essential_keys if key in place}
    
    # Add rating_summary (shows breakdown of star ratings)
    if "rating_summary" in place:
        filtered_place["rating_summary"] = place["rating_summary"]
    
    # Filter user_reviews carefully
    if "user_reviews" in place and isinstance(place["user_reviews"], dict):
        user_reviews = place["user_reviews"]
        filtered_user_reviews = {}
        
        # Keep most_relevant reviews but limit to essential fields per review
        if "most_relevant" in user_reviews and isinstance(user_reviews["most_relevant"], list):
            filtered_most_relevant = []
            for review in user_reviews["most_relevant"]:
                if isinstance(review, dict):
                    filtered_review = {
                        key: review[key] 
                        for key in ["date", "description", "rating", "username"]
                        if key in review
                    }
                    if filtered_review:
                        filtered_most_relevant.append(filtered_review)
            
            if filtered_most_relevant:
                filtered_user_reviews["most_relevant"] = filtered_most_relevant
        
        # Keep source info (review platform names)
        if "source" in user_reviews and isinstance(user_reviews["source"], list):
            filtered_source = []
            for source in user_reviews["source"]:
                if isinstance(source, dict) and "name" in source:
                    filtered_source.append({"name": source["name"]})
            
            if filtered_source:
                filtered_user_reviews["source"] = filtered_source
        
        if filtered_user_reviews:
            filtered_place["user_reviews"] = filtered_user_reviews
    
    return filtered_place


# Create the custom tool
@tool("filtered_composio_google_maps_search", args_schema=FilteredGoogleMapsSearchInput, return_direct=True)
def filtered_composio_google_maps_search(query: str) -> dict:
    """Search for places using Google Maps with filtered results to reduce token usage.
    Query should include place name, city, and country for best results."""
    return filtered_google_maps_search(query)

# -------------------------------------- Google News Search Tool --------------------------------------

# Input schema for the filtered news search tool
class FilteredNewsSearchInput(BaseModel):
    query: str = Field(description="The search query for finding news articles")
    num_results: int = Field(default=10, description="Number of news results to return (1-10)")

# Custom wrapper for filtered news search
def filtered_news_search(query: str, num_results: int = 10) -> dict:
    """Wrapper that filters COMPOSIO_SEARCH_NEWS_SEARCH results to reduce token usage"""
    # Get the raw tool
    raw_tool = None
    for tool_item in news_search_tools:
        if tool_item.name == "COMPOSIO_SEARCH_NEWS_SEARCH":
            raw_tool = tool_item
            break
    if not raw_tool:
        return {"error": "COMPOSIO_SEARCH_NEWS_SEARCH tool not found", "successful": False}
    try:
        # Call the original tool using the tool's invoke method instead of func
        if hasattr(raw_tool, 'invoke'):
            result = raw_tool.invoke({"query": query})
        else:
            # Fallback to direct function call if invoke doesn't work
            result = raw_tool.func(query)
        # Extract only what we need - much cleaner approach!
        if isinstance(result, dict) and "data" in result:
            data = result["data"]
            # Extract the specified number of news results (default 10, max 10)
            if "results" in data and "news_results" in data["results"]:
                # Ensure num_results is within reasonable bounds (1-10)
                num_results = max(1, min(num_results, 10))
                limited_news = data["results"]["news_results"][:num_results]
                # Filter each news article to only include essential keys
                filtered_news = []
                for article in limited_news:
                    if isinstance(article, dict):
                        # Only keep the essential keys
                        essential_keys = ["date", "link", "published_at", "snippet", "title"]
                        filtered_article = {key: article[key] for key in essential_keys if key in article}
                        filtered_news.append(filtered_article)
                # Return ultra-clean structure with only essential data
                return {
                    "data": {
                        "results": {
                            "news_results": filtered_news
                        }
                    },
                    "successful": True
                }
            else:
                return {"error": "No news results found in response", "successful": False}
        else:
            return {"error": "Invalid response structure from tool", "successful": False}
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}", "successful": False}

# Create the custom tool
@tool("filtered_composio_news_search", args_schema=FilteredNewsSearchInput, return_direct=True)
def filtered_composio_news_search(query: str, num_results: int = 10) -> dict:
    """Search for news using Composio with filtered results to reduce token usage.
    Returns the specified number of results (default 10) with only essential data."""
    return filtered_news_search(query, num_results)

# -------------------------------------- Google shopping Search Tool --------------------------------------

# Input schema for the filtered shopping search tool
class FilteredShoppingSearchInput(BaseModel):
    query: str = Field(description="The search query for finding shopping products")
    num_results: int = Field(default=10, description="Number of shopping results to return (1-50)")

# Custom wrapper for filtered shopping search
def filtered_shopping_search(query: str, num_results: int = 10) -> dict:
    """Wrapper that filters COMPOSIO_SEARCH_SHOPPING_SEARCH results to reduce token usage"""
    # Get the raw tool
    raw_tool = None
    for tool_item in shopping_tools:
        if tool_item.name == "COMPOSIO_SEARCH_SHOPPING_SEARCH":
            raw_tool = tool_item
            break
    if not raw_tool:
        return {"error": "COMPOSIO_SEARCH_SHOPPING_SEARCH tool not found", "successful": False}
    try:
        # Call the original tool using the tool's invoke method instead of func
        if hasattr(raw_tool, 'invoke'):
            result = raw_tool.invoke({"query": query})
        else:
            # Fallback to direct function call if invoke doesn't work
            result = raw_tool.func(query)
        # Extract only what we need
        if isinstance(result, dict) and "data" in result:
            data = result["data"]
            
            # Define essential keys for shopping results
            essential_keys = ["old_price", "price", "rating", "tag", "thumbnail", "title"]
            optional_keys = ["delivery"]
            
            # Helper function to filter shopping items
            def filter_shopping_item(item):
                if isinstance(item, dict):
                    filtered_item = {key: item[key] for key in essential_keys if key in item}
                    # Add optional keys if they exist
                    for opt_key in optional_keys:
                        if opt_key in item:
                            filtered_item[opt_key] = item[opt_key]
                    return filtered_item
                return item
            
            # Collect all shopping results
            all_shopping_results = []
            
            # First, add shopping_results from categorized_shopping_results
            if "results" in data and "categorized_shopping_results" in data["results"]:
                categorized_results = data["results"]["categorized_shopping_results"]
                if isinstance(categorized_results, list):
                    for category_item in categorized_results:
                        if isinstance(category_item, dict) and "shopping_results" in category_item:
                            for item in category_item["shopping_results"]:
                                if isinstance(item, dict):
                                    all_shopping_results.append(filter_shopping_item(item))
            
            # Then, add shopping_results from direct shopping_results
            if "results" in data and "shopping_results" in data["results"]:
                shopping_results = data["results"]["shopping_results"]
                if isinstance(shopping_results, list):
                    for item in shopping_results:
                        if isinstance(item, dict):
                            all_shopping_results.append(filter_shopping_item(item))
            
            # Remove duplicates based on "title"
            seen_titles = set()
            unique_shopping_results = []
            for item in all_shopping_results:
                if isinstance(item, dict) and "title" in item:
                    title = item["title"]
                    if title not in seen_titles:
                        seen_titles.add(title)
                        unique_shopping_results.append(item)
            
            # Limit to num_results
            num_results = max(1, min(num_results, 50))
            limited_results = unique_shopping_results[:num_results]
            
            # Return clean structure with all results under shopping_results
            return {
                "data": {
                    "results": {
                        "shopping_results": limited_results
                    }
                },
                "successful": True
            }
        else:
            return {"error": "Invalid response structure from tool", "successful": False}
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}", "successful": False}

# Create the custom tool
@tool("filtered_composio_shopping_search", args_schema=FilteredShoppingSearchInput, return_direct=True)
def filtered_composio_shopping_search(query: str, num_results: int = 10) -> dict:
    """Search for shopping products using Composio with filtered results to reduce token usage.
    Merges categorized and direct results, removes duplicates by title, and returns unique products
    with only essential data: old_price, price, rating, tag, thumbnail, title, and delivery (if available)."""
    return filtered_shopping_search(query, num_results)