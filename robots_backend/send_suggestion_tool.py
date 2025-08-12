from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import Optional
import httpx
import logging

logger = logging.getLogger(__name__)

# API base URL for internal communication
API_BASE_URL = "http://localhost:8000"

class SendSuggestionInput(BaseModel):
    """Input schema for sending suggestions via WebSocket"""
    file_path: str = Field(..., description="Path to the file being suggested for modification")
    original_content: str = Field(..., description="full content of the file before the change")
    proposed_content: str = Field(..., description="full content of the file after the change")
    description: str = Field(..., description="A concise description of the changes being suggested(e.g. maximum 5-6 words)")

@tool("send_suggestion", args_schema=SendSuggestionInput, return_direct=True)
def send_suggestion_tool(
    file_path: str,
    original_content: str,
    proposed_content: str,
    description: str
) -> dict:
    """Send a code suggestion to connected WebSocket clients for real-time display in the editor.
    Important note: you must include the full file content in both `original_content` and `proposed_content` parameter
    
    This tool broadcasts suggestions to the frontend where users can preview, accept, or reject them.
    The suggestion will be displayed with diff highlighting and interactive controls.
    """
    try:
        # Create the suggestion payload
        suggestion_data = {
            "filePath": file_path,
            "originalContent": original_content,
            "proposedContent": proposed_content,
            "description": description,
            "agent_type": "coding"
        }
        # Send to the WebSocket suggestion endpoint
        with httpx.Client() as client:
            response = client.post(
                f"{API_BASE_URL}/suggestions/send",
                json=suggestion_data,
                params={"agent_type": "coding"}
            )
            response.raise_for_status()
            # Add logging
            logger.info(f"Suggestion sent successfully: {response.json()}")
            return response.json()
        
    except Exception as e:
        logger.error(f"Failed to send suggestion: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to send suggestion: {str(e)}",
            "file_path": file_path
        }