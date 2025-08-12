"""
Backend summarization endpoint
Uses gemini-2.0-flash to summarize conversation history
"""

from fastapi import APIRouter, Body, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/summarize", tags=["summarize"])
security = HTTPBearer()

# Import dynamic model configuration
from dynamic_model_config import get_current_gemini_model

# Initialize summarization LLM with dynamic model selection
def get_summarize_llm():
    return get_current_gemini_model(temperature=0.1)

summarize_llm = get_summarize_llm()

class RollingSummarizeRequest(BaseModel):
    previous_summary: str
    new_messages: List[dict]

class SummarizeResponse(BaseModel):
    summary: str

# Helper to format messages for prompt
def format_messages(messages: List[dict]) -> str:
    formatted = ""
    for msg in messages:
        role = msg.get('role', 'user')
        content = msg.get('content', '')
        formatted += f"{role.upper()}: {content}\n\n"
    return formatted

@router.post("/rolling", response_model=SummarizeResponse)
async def rolling_summarize(
    request: RollingSummarizeRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Update the conversation summary using the previous summary and new messages.
    Returns the updated summary only. Frontend is responsible for storing it.
    """
    try:
        summary_prompt = f"""
        You are updating a conversation summary. Your task is to create a comprehensive yet concise summary that captures the essential context for an AI agent to continue the conversation naturally.

        IMPORTANT GUIDELINES:
        1. PRESERVE CODE: If code is discussed, include the FINAL/COMPLETE version of any code solutions, not intermediate attempts.
        2. KEEP KEY DETAILS: Include specific names, numbers, dates, preferences, and important decisions.
        3. MAINTAIN CONTEXT: Preserve the user's goals, preferences, and current status of any tasks.
        4. BE CONCISE: Remove redundant information and conversational fluff while keeping essential information.
        5. STRUCTURE WELL: Organize information logically (user preferences, current tasks, completed work, etc.)

        Previous summary:
        {request.previous_summary}

        New messages to incorporate:
        {format_messages(request.new_messages)}

        Create an updated summary that:
        - Incorporates the new information into the existing summary
        - Preserves all important technical details, code, and decisions
        - Maintains the user's context and preferences
        - Is well-structured and easy for an AI agent to understand
        - Focuses on what the AI agent needs to know to continue the conversation effectively

        Updated summary:
        """
        # Get current LLM instance (may have changed due to rate limiting)
        current_summarize_llm = get_summarize_llm()
        summary_response = current_summarize_llm.invoke(summary_prompt)
        summary = summary_response.content
        return SummarizeResponse(summary=summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rolling summarization failed: {str(e)}") 