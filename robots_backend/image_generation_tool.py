import requests
import os
from langchain_core.tools import tool
from pydantic import BaseModel, Field


class ImageGenInput(BaseModel):
    """Input schema for image generation tool."""
    prompt: str = Field(description="Description of the image to generate")
    filename: str = Field(description="Name for the generated image file (without extension)")
    timeout: int = Field(default=60, description="Request timeout in seconds")


@tool("generate_image", args_schema=ImageGenInput, return_direct=True)
def generate_image_tool(prompt: str, filename: str, timeout: int = 60) -> str:
    """
    Generate an image using TraxDinosaur API and save it to uploaded_files directory.

    Args:
        prompt: Description of the image to generate
        filename: Name for the generated image file (without extension)
        timeout: Request timeout in seconds

    Returns:
        str: File path of the saved image or error message
    """
    # API endpoint
    url = "https://apiimagestrax.vercel.app/api/genimage"

    # Request headers
    headers = {
        "Content-Type": "application/json"
    }

    # Request body
    data = {
        "prompt": prompt
    }

    try:
        print(f"🎨 Generating image for: '{prompt}'")
        print("⏳ Please wait, this may take 30-60 seconds...")

        # Send POST request
        response = requests.post(url, json=data, headers=headers, timeout=timeout)

        # Check if request was successful
        if response.status_code == 200:
            # Get raw PNG image bytes from response
            image_bytes = response.content

            # Ensure uploaded_files directory exists in project root
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            upload_dir = os.path.join(project_root, "uploaded_files")
            os.makedirs(upload_dir, exist_ok=True)

            # Create full filename with .png extension
            full_filename = f"{filename}.png"
            file_path = os.path.join(upload_dir, full_filename)

            # Save image to file
            with open(file_path, 'wb') as f:
                f.write(image_bytes)

            print(f"✅ Image saved successfully as '{file_path}'!")
            return file_path

        else:
            error_msg = f"❌ Error: API returned status code {response.status_code}. Response: {response.text}"
            print(error_msg)
            return error_msg

    except requests.exceptions.Timeout:
        error_msg = "⏰ Error: Request timed out. The API might be slow or overloaded."
        print(error_msg)
        return error_msg
    except requests.exceptions.RequestException as e:
        error_msg = f"❌ Error making request: {e}"
        print(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"❌ Error saving image: {e}"
        print(error_msg)
        return error_msg