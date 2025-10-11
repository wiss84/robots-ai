# Import Pydantic for schema definition
from pydantic import BaseModel, Field
from typing import Optional
from langchain_core.tools import tool
from composio import Composio
import time
import shutil
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
flight_search = composio.tools.get(user_id=os.getenv('COMPOSIO_USER_ID'), tools=["COMPOSIO_SEARCH_FLIGHTS"])
hotel_search = composio.tools.get(user_id=os.getenv('COMPOSIO_USER_ID'), tools=["COMPOSIO_SEARCH_HOTELS"])
video_generation_tool = composio.tools.get(user_id=os.getenv('COMPOSIO_USER_ID'), tools=["GEMINI_GENERATE_VIDEOS"])
video_url_pull_tool = composio.tools.get(user_id=os.getenv('COMPOSIO_USER_ID'), tools=["GEMINI_WAIT_FOR_VIDEO"])

# -------------------------------------- Video Generation Tool --------------------------------------

# Input schema for the video generation tool
class VideoGenerationInput(BaseModel):
    prompt: str = Field(description="Text prompt for Veo video generation")
    extras: object = Field(default=None, description="Additional parameters passed through to API")
    model: str = Field(default="veo-3.0-generate-preview", description="Model to use. Examples: 'veo-3.0-generate-preview', 'veo-3.0-fast-generate-preview', 'veo-2.0-generate-001'")
    filename: str = Field(default=None, description="Name for the generated video file (without extension)")

# Custom wrapper for video generation and pulling
def generate_and_pull_video(prompt: str, filename: str = None, model: str = "veo-3.0-generate-preview", extras: object = None) -> str:
    """Wrapper that handles video generation, waiting, pulling, and file management"""
    # Get the raw tools
    raw_gen_tool = None
    raw_pull_tool = None
    
    for tool_item in video_generation_tool:
        if tool_item.name == "GEMINI_GENERATE_VIDEOS":
            raw_gen_tool = tool_item
            break
            
    for tool_item in video_url_pull_tool:
        if tool_item.name == "GEMINI_WAIT_FOR_VIDEO":
            raw_pull_tool = tool_item
            break
            
    if not raw_gen_tool or not raw_pull_tool:
        error_msg = "Required video tools not found"
        print(f"❌ Error: {error_msg}")
        return error_msg
        
    try:
        print(f"🎬 Generating video for: '{prompt}'")
        print("⏳ Please wait, this may take a few minutes...")
        
        # Step 1: Generate video and get operation_name
        gen_input = {
            "prompt": prompt,
            "model": model
        }
        if extras:
            gen_input["extras"] = extras
            
        if hasattr(raw_gen_tool, 'invoke'):
            gen_result = raw_gen_tool.invoke(gen_input)
        else:
            gen_result = raw_gen_tool.func(**gen_input)
            
        if not isinstance(gen_result, dict) or "data" not in gen_result or "operation_name" not in gen_result["data"]:
            error_msg = "Invalid response from video generation"
            print(f"❌ Error: {error_msg}")
            print(f"Received response: {gen_result}")
            return error_msg
            
        operation_id = gen_result["data"]["operation_name"]
        print("🎥 Video generation started...")
        
        time.sleep(12)  # Wait 12 seconds for the video to be ready before pulling it

        # Step 2: Pull video with retries
        max_retries = 6  # Maximum 6 retries (total 60 seconds)
        for attempt in range(max_retries):
            try:
                if hasattr(raw_pull_tool, 'invoke'):
                    pull_result = raw_pull_tool.invoke({"operation_name": operation_id})
                else:
                    pull_result = raw_pull_tool.func(operation_name=operation_id)
                
                if isinstance(pull_result, dict) and "data" in pull_result and "video_file" in pull_result["data"]:
                    original_path = pull_result["data"]["video_file"]
                    print(f"✅ Video pulled successfully: {original_path}")
                    
                    # Step 3: Move to uploaded_files with custom filename
                    base_filename = filename if filename else f"video_{int(time.time())}"
                    final_filename = f"{base_filename}.mp4"
                    
                    # Ensure uploaded_files directory exists in project root
                    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    upload_dir = os.path.join(project_root, "uploaded_files")
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    # Create full file path
                    file_path = os.path.join(upload_dir, final_filename)
                    
                    # Copy the file to uploaded_files
                    shutil.copy2(original_path, file_path)
                    
                    print(f"✅ Video saved successfully as '{file_path}'!")
                    return file_path
                
                # If we get here, the video isn't ready yet
                if attempt < max_retries - 1:  # Don't sleep on the last attempt
                    print(f"⏳ Video not ready yet, waiting... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(10)  # Wait 10 seconds before next attempt
                    
            except Exception as e:
                if attempt < max_retries - 1:  # Don't sleep on the last attempt
                    print(f"⚠️ Attempt {attempt + 1} failed, retrying...")
                    time.sleep(10)  # Wait 10 seconds before next attempt
                else:
                    error_msg = f"Failed to pull video after multiple attempts: {str(e)}"
                    print(f"❌ Error: {error_msg}")
                    return error_msg
                    
        error_msg = "Failed to pull video after maximum retries"
        print(f"❌ Error: {error_msg}")
        return error_msg
        
    except Exception as e:
        error_msg = f"Tool execution failed: {str(e)}"
        print(f"❌ Error: {error_msg}")
        return error_msg

# Create the custom tool
@tool("generate_video", args_schema=VideoGenerationInput, return_direct=True)
def generate_video(prompt: str, filename: str = None, model: str = "veo-3.0-generate-preview", extras: object = None) -> str:
    """Generates videos from text prompts using Google's Veo models. Creates high-quality video content."""
    return generate_and_pull_video(prompt=prompt, filename=filename, model=model, extras=extras)


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
    """Search for images."""
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
    """Search for any general information."""
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
    """Search for places using Google Maps. Return information and reviews.
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
    """Search for latest news."""
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
    """Search for shopping products."""
    return filtered_shopping_search(query, num_results)

# -------------------------------------- Composio Flight Search Tool --------------------------------------

# Input schema for the filtered flight search tool
class FilteredFlightSearchInput(BaseModel):
    arrival_id: str = Field(description="Destination airport IATA code (3-letter uppercase code). Must be a valid airport code.")
    departure_id: str = Field(description="Origin airport IATA code (3-letter uppercase code). Must be a valid airport code.")
    outbound_date: str = Field(description="Departure date in YYYY-MM-DD format. Must be a future date.")
    adults: Optional[int] = Field(default=1, description="Number of adult passengers (18+ years old).")
    children: Optional[int] = Field(default=0, description="Number of child passengers (2-11 years old).")
    infants: Optional[int] = Field(default=0, description="Number of infant passengers (under 2 years old).")
    currency: Optional[str] = Field(default=None, description="Currency for pricing (3-letter currency code).")
    gl: Optional[str] = Field(default=None, description="Country code for results (ISO 3166-1 alpha-2).")
    hl: Optional[str] = Field(default=None, description="Language code for results (ISO 639-1).")
    return_date: Optional[str] = Field(default=None, description="Return date in YYYY-MM-DD format. Must be after outbound_date. Leave empty for one-way flights.")
    travel_class: Optional[int] = Field(default=1, description="Travel class preference. 1 = Economy, 2 = Premium Economy, 3 = Business, 4 = First Class.")
    flight_type: Optional[int] = Field(default=None, description="Flight type filter. 1 = Connecting flights (with layovers), 2 = Direct flights (no layovers). Leave empty for all flights.")

# Custom wrapper for filtered flight search
def filtered_flight_search(
    arrival_id: str,
    departure_id: str,
    outbound_date: str,
    adults: int = 1,
    children: int = 0,
    infants: int = 0,
    currency: Optional[str] = None,
    gl: Optional[str] = None,
    hl: Optional[str] = None,
    return_date: Optional[str] = None,
    travel_class: int = 1,
    flight_type: Optional[int] = None
) -> dict:
    """Wrapper that filters COMPOSIO_SEARCH_FLIGHTS results to reduce token usage"""
    # Get the raw tool
    raw_tool = None
    for tool_item in flight_search:
        if tool_item.name == "COMPOSIO_SEARCH_FLIGHTS":
            raw_tool = tool_item
            break
    if not raw_tool:
        return {"error": "COMPOSIO_SEARCH_FLIGHTS tool not found", "successful": False}
    try:
        # Build the input dictionary with provided parameters
        tool_input = {
            "arrival_id": arrival_id,
            "departure_id": departure_id,
            "outbound_date": outbound_date,
            "adults": adults,
            "children": children,
            "infants": infants,
        }
        
        # Add optional parameters if provided
        if currency:
            tool_input["currency"] = currency
        if gl:
            tool_input["gl"] = gl
        if hl:
            tool_input["hl"] = hl
        if return_date:
            tool_input["return_date"] = return_date
        if travel_class:
            tool_input["travel_class"] = travel_class
        
        # Call the original tool
        if hasattr(raw_tool, 'invoke'):
            result = raw_tool.invoke(tool_input)
        else:
            result = raw_tool.func(**tool_input)
        
        # Extract only what we need
        if isinstance(result, dict) and "data" in result:
            data = result["data"]
            filtered_result = {
                "data": {
                    "results": {}
                },
                "successful": True
            }
            
            # Process airports
            if "results" in data and "airports" in data["results"]:
                airports = data["results"]["airports"]
                filtered_airports = {}
                
                # Process arrival airports
                if isinstance(airports, dict) and "arrival" in airports:
                    arrival_list = airports["arrival"]
                    if isinstance(arrival_list, list):
                        filtered_airports["arrival"] = [
                            {key: airport[key] for key in ["airport", "city", "country", "country_code"] if key in airport}
                            for airport in arrival_list
                            if isinstance(airport, dict)
                        ]
                
                # Process departure airports
                if isinstance(airports, dict) and "departure" in airports:
                    departure_list = airports["departure"]
                    if isinstance(departure_list, list):
                        filtered_airports["departure"] = [
                            {key: airport[key] for key in ["airport", "city", "country", "country_code"] if key in airport}
                            for airport in departure_list
                            if isinstance(airport, dict)
                        ]
                
                if filtered_airports:
                    filtered_result["data"]["results"]["airports"] = filtered_airports
            
            # Helper function to filter flight item
            def filter_flight_item(flight):
                if isinstance(flight, dict):
                    filtered_flight = {key: flight[key] for key in ["flights", "price", "total_duration", "type"] if key in flight}
                    # Add layovers if available
                    if "layovers" in flight:
                        filtered_flight["layovers"] = flight["layovers"]
                    return filtered_flight
                return flight
            
            # Helper function to check if flight is direct or has layovers
            def is_direct_flight(flight):
                """Returns True if flight is direct (no layovers)"""
                if isinstance(flight, dict):
                    # If layovers key doesn't exist or is empty, it's direct
                    layovers = flight.get("layovers")
                    if layovers is None or (isinstance(layovers, list) and len(layovers) == 0):
                        return True
                return False
            
            # Collect all available flights from best_flights and other_flights
            all_flights = []
            
            # Add best_flights
            if "results" in data and "best_flights" in data["results"]:
                best_flights = data["results"]["best_flights"]
                if isinstance(best_flights, list):
                    for flight in best_flights:
                        if isinstance(flight, dict):
                            all_flights.append(filter_flight_item(flight))
            
            # Add other_flights
            if "results" in data and "other_flights" in data["results"]:
                other_flights = data["results"]["other_flights"]
                if isinstance(other_flights, list):
                    for flight in other_flights:
                        if isinstance(flight, dict):
                            all_flights.append(filter_flight_item(flight))
            
            # Filter flights based on flight_type
            if flight_type == 1:  # Connecting flights (with layovers)
                available_flights = [f for f in all_flights if not is_direct_flight(f)]
            elif flight_type == 2:  # Direct flights (no layovers)
                available_flights = [f for f in all_flights if is_direct_flight(f)]
            else:  # No filter (all flights)
                available_flights = all_flights
            
            if available_flights:
                filtered_result["data"]["results"]["available_flights"] = available_flights
            
            return filtered_result
        else:
            return {"error": "Invalid response structure from tool", "successful": False}
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}", "successful": False}

# Create the custom tool
@tool("filtered_composio_flight_search", args_schema=FilteredFlightSearchInput, return_direct=True)
def filtered_composio_flight_search(
    arrival_id: str,
    departure_id: str,
    outbound_date: str,
    adults: int = 1,
    children: int = 0,
    infants: int = 0,
    currency: Optional[str] = None,
    gl: Optional[str] = None,
    hl: Optional[str] = None,
    return_date: Optional[str] = None,
    travel_class: int = 1,
    flight_type: Optional[int] = None
) -> dict:
    """Search for flights with comprehensive pricing, schedule, and airline information. 
    this tool finds available flights between cities/airports with detailed pricing, multiple airlines, departure/arrival times, flight duration.
    supports round-trip and one-way searches, multiple passenger types (adults, children, infants), different travel classes, direct and with layover flights, and international pricing in various currencies
    perfect for travel planning, and price comparison."""
    return filtered_flight_search(
        arrival_id=arrival_id,
        departure_id=departure_id,
        outbound_date=outbound_date,
        adults=adults,
        children=children,
        infants=infants,
        currency=currency,
        gl=gl,
        hl=hl,
        return_date=return_date,
        travel_class=travel_class,
        flight_type=flight_type
    )

# -------------------------------------- Composio Hotel Search Tool --------------------------------------

# Input schema for the filtered Hotel search tool
class FilteredHotelSearchInput(BaseModel):
    check_in_date: str = Field(description="Check-in date in YYYY-MM-DD format. Must be a future date.")
    check_out_date: str = Field(description="Check-out date in YYYY-MM-DD format. Must be after check-in date.")
    q: str = Field(description="Location for hotel search. Can be city, neighborhood, landmark, or specific hotel name + city.")
    adults: Optional[int] = Field(default=1, description="Number of adult passengers (18+ years old).")
    children: Optional[int] = Field(default=0, description="Number of child passengers (2-11 years old).")
    currency: Optional[str] = Field(default=None, description="Currency for pricing (3-letter currency code).")
    free_cancellation: Optional[bool] = Field(default=None, description="Filter for hotels with free cancellation.")
    gl: Optional[str] = Field(default=None, description="Country code for results (ISO 3166-1 alpha-2).")
    hl: Optional[str] = Field(default=None, description="Language code for results (ISO 639-1).")
    hotel_class: Optional[str] = Field(default=None, description="Filter by hotel star rating. Use comma-separated values for multiple ratings, e.g., '3,4' for 3 and 4-star hotels.")
    max_price: Optional[int] = Field(default=None, description="Maximum price per night filter.")
    min_price: Optional[int] = Field(default=None, description="Minimum price per night filter.")
    include_images: Optional[bool] = Field(default=None, description="If True, Include 'images' in hotel results.")
    include_nearby_places: Optional[bool] = Field(default=None, description="If True, Include 'nearby_places' in hotel results.")
    num_results: Optional[int] = Field(default=5, description="Number of hotel results to return (1-10).")
    include_ratings_and_reviews: Optional[bool] = Field(default=None, description="If True, Include rating and review information (location_rating, overall_rating, ratings, reviews, reviews_breakdown).")

# Custom wrapper for filtered hotel search
def filtered_hotel_search(
    check_in_date: str,
    check_out_date: str,
    q: str,
    adults: int = 1,
    children: int = 0,
    currency: Optional[str] = None,
    free_cancellation: Optional[bool] = None,
    gl: Optional[str] = None,
    hl: Optional[str] = None,
    hotel_class: Optional[str] = None,
    max_price: Optional[int] = None,
    min_price: Optional[int] = None,
    include_images: Optional[bool] = None,
    include_nearby_places: Optional[bool] = None,
    num_results: int = 5,
    include_ratings_and_reviews: Optional[bool] = None
) -> dict:
    """Wrapper that filters COMPOSIO_SEARCH_HOTELS results to reduce token usage"""
    # Get the raw tool
    raw_tool = None
    for tool_item in hotel_search:
        if tool_item.name == "COMPOSIO_SEARCH_HOTELS":
            raw_tool = tool_item
            break
    if not raw_tool:
        return {"error": "COMPOSIO_SEARCH_HOTELS tool not found", "successful": False}
    try:
        # Build the input dictionary with provided parameters
        tool_input = {
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "q": q,
            "adults": adults,
            "children": children,
        }
        
        # Add optional parameters if provided
        if currency:
            tool_input["currency"] = currency
        if free_cancellation is not None:
            tool_input["free_cancellation"] = free_cancellation
        if gl:
            tool_input["gl"] = gl
        if hl:
            tool_input["hl"] = hl
        if hotel_class:
            tool_input["hotel_class"] = hotel_class
        if max_price is not None:
            tool_input["max_price"] = max_price
        if min_price is not None:
            tool_input["min_price"] = min_price
        
        # Call the original tool
        if hasattr(raw_tool, 'invoke'):
            result = raw_tool.invoke(tool_input)
        else:
            result = raw_tool.func(**tool_input)
        
        # Extract only what we need
        if isinstance(result, dict) and "data" in result:
            data = result["data"]
            filtered_result = {
                "data": {
                    "results": {}
                },
                "successful": True
            }
            
            # Ensure num_results is within bounds (1-10)
            num_results = max(1, min(num_results, 10))
            
            # Process hotels/properties
            if "results" in data and "properties" in data["results"]:
                properties = data["results"]["properties"]
                if isinstance(properties, list):
                    filtered_properties = []
                    
                    for prop in properties[:num_results]:
                        if isinstance(prop, dict):
                            filtered_prop = {}
                            
                            # Always include these keys
                            essential_keys = ["amenities", "check_in_time", "check_out_time", 
                                            "description", "gps_coordinates", "hotel_class", 
                                            "name", "rate_per_night", "link", "type"]
                            
                            for key in essential_keys:
                                if key in prop:
                                    filtered_prop[key] = prop[key]
                            
                            # Add deal if available
                            if "deal" in prop:
                                filtered_prop["deal"] = prop["deal"]
                            
                            # Add images if requested
                            if include_images and "images" in prop:
                                filtered_prop["images"] = prop["images"]
                            
                            # Add nearby_places if requested
                            if include_nearby_places and "nearby_places" in prop:
                                filtered_prop["nearby_places"] = prop["nearby_places"]
                            
                            # Add ratings and reviews if requested
                            if include_ratings_and_reviews:
                                rating_keys = ["location_rating", "overall_rating", "ratings", 
                                             "reviews", "reviews_breakdown"]
                                for key in rating_keys:
                                    if key in prop:
                                        filtered_prop[key] = prop[key]
                            
                            filtered_properties.append(filtered_prop)
                    
                    filtered_result["data"]["results"]["properties"] = filtered_properties
            
            return filtered_result
        else:
            return {"error": "Invalid response structure from tool", "successful": False}
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}", "successful": False}

# Create the custom tool
@tool("filtered_composio_hotel_search", args_schema=FilteredHotelSearchInput, return_direct=True)
def filtered_composio_hotel_search(
    check_in_date: str,
    check_out_date: str,
    q: str,
    adults: int = 1,
    children: int = 0,
    currency: Optional[str] = None,
    free_cancellation: Optional[bool] = None,
    gl: Optional[str] = None,
    hl: Optional[str] = None,
    hotel_class: Optional[str] = None,
    max_price: Optional[int] = None,
    min_price: Optional[int] = None,
    include_images: Optional[bool] = None,
    include_nearby_places: Optional[bool] = None,
    num_results: int = 5,
    include_ratings_and_reviews: Optional[bool] = None
) -> dict:
    """Search for hotels with comprehensive filtering and pricing. 
    this tool finds available accommodations with detailed information including:
      pricing, ratings, amenities and photos. supports price range filtering, star rating selection and free cancellation options. 
      perfect for travel planning, accommodation comparison, and finding the best lodging options for any destination. ."""
    return filtered_hotel_search(
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        q=q,
        adults=adults,
        children=children,
        currency=currency,
        free_cancellation=free_cancellation,
        gl=gl,
        hl=hl,
        hotel_class=hotel_class,
        max_price=max_price,
        min_price=min_price,
        include_images=include_images,
        include_nearby_places=include_nearby_places,
        num_results=num_results,
        include_ratings_and_reviews=include_ratings_and_reviews
    )