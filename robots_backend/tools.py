from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool
import os, requests, time
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("AI_Horde_API_KEY")

class ImageGenInput(BaseModel):
    prompt: str = Field(..., description="The main text prompt describing what the image should show, e.g., 'a futuristic robot walking in Tokyo at night'.")
    model: Optional[str] = Field(default="Realistic Vision Inpainting", description="Image model to use: 'Realistic Vision Inpainting', 'Photon', or 'majicMIX realistic'.")
    width: Optional[int] = Field(default=512, description="Width of the image in pixels. Must be a multiple of 64 (e.g., 512, 768, 1024), you must always use 512 unless the user specify otherwise.")
    height: Optional[int] = Field(default=512, description="Height of the image in pixels. Must be a multiple of 64 (e.g., 512, 768, 1024), you must always use 512 unless the user specify otherwise.")
    steps: Optional[int] = Field(default=25, description="Number of diffusion steps. More steps = better quality, but slower generation, you must always use max value of 30 or less unless the user specify otherwise.")
    cfg_scale: Optional[float] = Field(default=7.5,description="Guidance scale. Higher values make the result stick closer to the prompt.")
    seed: Optional[int] = Field(default=None,description="Seed for reproducible results. Use the same seed to get the same image again.")
    negative_prompt: Optional[str] = Field(default="",description="Optional description of what to avoid in the image, e.g., 'blurry, extra limbs'.")
    sampler: Optional[str] = Field(default="k_euler_a",description="Sampling method. Options include 'k_euler_a', 'k_dpmpp_2m', 'k_dpmpp_sde', 'dpmsolver', you must always use k_euler_a unless the user specify otherwise.")
    source_image: Optional[str] = Field(default="",description="Optional URL of a base image for image-to-image or inpainting tasks.")
    source_processing: Optional[str] = Field(default="img2img",description="Image processing type: 'img2img', 'inpainting', 'outpainting' or 'remix' use img2img for text to image generation.")

@tool("generate_image", args_schema=ImageGenInput, return_direct=True)
def generate_image(
    prompt: str,
    model: str = "Realistic Vision Inpainting",
    width: int = 512,
    height: int = 512,
    steps: int = 25,
    cfg_scale: float = 7.5,
    seed: Optional[int] = None,
    negative_prompt: str = "",
    sampler: str = "k_euler_a",
    source_image: str = "",
    source_processing: str = "img2img",
) -> dict:
    """
    Generate an image using AI Horde. Returns metadata including image URL and seed.
    """
    if not source_image:
        source_processing = "img2img"  # Fallback if no source image

    headers = {"apikey": API_KEY, "Content-Type": "application/json"}
    payload = {
        "prompt": prompt,
        "params": {
            "sampler_name": sampler,
            "cfg_scale": cfg_scale,
            "denoising_strength": 0.75,
            "seed": seed or "",
            "height": height,
            "width": width,
            "steps": steps,
            "post_processing": []
        },
        "nsfw": False,
        "trusted_workers": True,
        "censor_nsfw": False,
        "models": [model],
        "r2": True,
        "source_image": source_image,
        "source_processing": source_processing
    }
    if negative_prompt:
        payload["params"]["negative_prompt"] = negative_prompt

    resp = requests.post("https://stablehorde.net/api/v2/generate/async", headers=headers, json=payload)
    if resp.status_code != 202:
        return {"error": f"Failed to send request: {resp.status_code} - {resp.text}"}

    gen_id = resp.json().get("id")
    if not gen_id:
        return {"error": "No generation ID returned"}

    # Poll for result
    status_url = f"https://stablehorde.net/api/v2/generate/status/{gen_id}"
    start_time = time.time()
    timeout = 120  # seconds

    while True:
        result = requests.get(status_url, headers=headers).json()
        if result.get("done") and result.get("generations"):
            break

    gens = result.get("generations", [])
    if not gens:
        return {"error": "No generation found", "status": result}

    g = gens[0]
    img_url = g.get("img")
    if not img_url:
        return {"error": "No image URL in response", "status": result}

    return {
        "image_url": img_url,
        "seed": g.get("seed"),
        "model": g.get("model"),
        "worker": g.get("worker_name"),
        "prompt": prompt,
        "width": width,
        "height": height,
        "negative_prompt": negative_prompt,
        "sampler": sampler,
        "source_processing": source_processing,
    }
