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

# Create the custom tool using the same pattern as generate_image_tool
@tool("filtered_composio_image_search", args_schema=FilteredImageSearchInput, return_direct=True)
def filtered_composio_image_search(query: str, num_results: int = 5) -> dict:
    """Search for images using Composio with filtered results to reduce token usage.
    Returns the specified number of results (default 5) with only essential data."""
    return filtered_image_search(query, num_results)